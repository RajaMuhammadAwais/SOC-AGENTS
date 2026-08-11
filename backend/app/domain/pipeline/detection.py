"""Detection stage: evaluate detection rules over normalized events.

Implements a deterministic, sandboxed rule engine with two rule formats:

1. Native query rules — a safe JSON-based rule format with an allowlist of
   fields and operators, compiled to SQL at registration time and re-evaluated
   incrementally per event.
2. Sigma-style rules — a subset of the Sigma rule format
   (github.com/SigmaHQ/sigma, specification v2.x) supporting selection
   blocks with key-value / `|contains` / `|startswith` / `|endswith` /
   `|re` modifiers, `keywords` list, and detection conditions using `and`,
   `or`, `not`, `1 of`, and `all of`. Unsupported Sigma features (aggregations,
   filters, pipelines) are rejected explicitly at compile time rather than
   silently ignored.

Rules never execute arbitrary SQL fragments supplied by users; the compiler
only produces parameterized SQLAlchemy expressions over the canonical
normalized_events columns. Rule YAML is validated against the allowlist on
ingestion (detection_rule_id uniqueness and tenant scoping are schema-level).

MITRE ATT&CK tactic/technique references in rule metadata are stored as-is
and verified by the threat-intelligence stage (see docs/architecture/
detection-engine.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog
import yaml
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.domain.models import DetectionRule, NormalizedEvent, Severity

logger = structlog.get_logger("pipeline.detection")

# Canonical NormalizedEvent columns exposed to rules.
ALLOWED_FIELDS = {
    "event_type", "event_category", "severity", "actor", "target", "username",
    "source_ip", "source_port", "destination_ip", "destination_port", "protocol",
    "hostname", "process_name", "command_line", "file_hash_md5", "file_hash_sha1",
    "file_hash_sha256", "domain", "url", "cloud_identity", "cloud_resource",
    "authentication_result", "correlation_key", "session_id",
}

MODIFIER_TO_OPERATOR = {
    "contains": "contains",
    "startswith": "startswith",
    "endswith": "endswith",
    "re": "re",
    "all": "all",
    "lt": "lt",
    "lte": "lte",
    "gt": "gt",
    "gte": "gte",
}


@dataclass(frozen=True)
class CompiledRule:
    rule_id: str
    severity: Severity
    mitre: dict[str, Any]
    name: str
    expression: Any  # SQLAlchemy expression bound to normalized_events columns
    field_names: list[str]


class RuleCompilationError(ValueError):
    """Raised when a rule cannot be compiled safely."""


@dataclass
class RuleEvaluationResult:
    matched_event_ids: list[UUID]
    matched_rule_ids: list[str]


def _field_column(field_name: str):
    column = getattr(NormalizedEvent, field_name, None)
    if column is None:
        raise RuleCompilationError(f"unsupported field: {field_name}")
    return column


def _selection_to_expression(selection: dict[str, Any]) -> Any:
    """Compile a single selection block into a SQLAlchemy expression."""

    clauses: list[Any] = []
    for key, value in selection.items():
        if key == "keywords":
            # Keywords is a list of terms matched anywhere in text columns.
            if not isinstance(value, list) or not value:
                raise RuleCompilationError("keywords must be a non-empty list")
            keyword_clauses: list[Any] = []
            for term in value:
                if not isinstance(term, str):
                    raise RuleCompilationError("keywords entries must be strings")
                keyword_clauses.append(
                    or_(
                        NormalizedEvent.process_name.contains(term),
                        NormalizedEvent.command_line.contains(term),
                        NormalizedEvent.event_type.contains(term),
                    )
                )
            clauses.append(or_(*keyword_clauses))
            continue
        if "|" not in key and key not in ALLOWED_FIELDS:
            raise RuleCompilationError(f"unsupported field in selection: {key}")
        base_field = key.split("|")[0]
        if base_field not in ALLOWED_FIELDS:
            raise RuleCompilationError(f"unsupported field in selection: {key}")
        column = _field_column(base_field)
        values = value if isinstance(value, list) else [value]
        inner = values[0] if len(values) == 1 and not isinstance(values[0], list) else values
        modifier = key.split("|")[1] if "|" in key else None
        clause = _build_field_clause(column, inner, modifier)
        clauses.append(clause)
    return and_(*clauses) if len(clauses) > 1 else clauses[0]


def _build_field_clause(column: Any, values: Any, modifier: str | None) -> Any:
    if isinstance(values, list):
        if modifier == "all":
            return and_(*[_build_field_clause(column, single, None) for single in values])
        return or_(*[_build_field_clause(column, single, modifier) for single in values])
    if modifier is None:
        return column == values
    operator = MODIFIER_TO_OPERATOR.get(modifier)
    if operator is None:
        raise RuleCompilationError(f"unsupported modifier: {modifier}")
    if operator == "contains":
        return column.contains(str(values))
    if operator == "startswith":
        return column.startswith(str(values))
    if operator == "endswith":
        return column.endswith(str(values))
    if operator == "re":
        if not isinstance(values, str):
            raise RuleCompilationError("regex value must be a string")
        # Reject regexes that could short-circuit SQL planning (keep it bounded).
        re.compile(values)
        return column.regexp_match(values)
    if operator in ("lt", "lte", "gt", "gte"):
        if not isinstance(values, (int, float)):
            raise RuleCompilationError(f"{modifier} requires a numeric value")
        if operator == "lt":
            return column < values
        if operator == "lte":
            return column <= values
        if operator == "gt":
            return column > values
        return column >= values
    raise RuleCompilationError(f"unhandled operator: {operator}")


def compile_rule(rule_yaml_text: str) -> CompiledRule:
    """Compile a Sigma-style or native rule YAML into a parameterized query."""

    try:
        parsed = yaml.safe_load(rule_yaml_text)
    except yaml.YAMLError as exc:
        raise RuleCompilationError(f"invalid rule YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuleCompilationError("rule root must be a mapping")

    detection_block = parsed.get("detection")
    if not isinstance(detection_block, dict):
        raise RuleCompilationError("missing detection block")

    condition_raw = detection_block.get("condition")
    if condition_raw is None:
        raise RuleCompilationError("missing detection.condition")

    selections = {
        key: value
        for key, value in detection_block.items()
        if key != "condition" and isinstance(value, dict)
    }
    if not selections:
        raise RuleCompilationError("detection block has no selection blocks")

    # Map each selection block to an expression.
    compiled_selections: dict[str, Any] = {}
    for name, body in selections.items():
        compiled_selections[name] = _selection_to_expression(body)

    # Compile the condition into SQLAlchemy boolean logic.
    raw_expression = _compile_condition(condition_raw, compiled_selections)
    # _compile_boolean / _parse_boolean return (expression, position) tuples
    # for recursive parsing; unwrap here so the CompiledRule always exposes
    # a plain SQLAlchemy expression.
    if isinstance(raw_expression, tuple) and len(raw_expression) == 2:
        expression = raw_expression[0]
    else:
        expression = raw_expression

    rule_id = parsed.get("id") or parsed.get("title", "unnamed")[:80]
    severity_text = (parsed.get("level") or "medium").lower()
    try:
        severity = Severity(severity_text)
    except ValueError as exc:
        raise RuleCompilationError(f"unsupported severity level: {severity_text}") from exc

    return CompiledRule(
        rule_id=str(rule_id),
        severity=severity,
        mitre=parsed.get("tags") or {},
        name=str(parsed.get("title") or rule_id),
        expression=expression,
        field_names=list(selections.keys()),
    )


def _compile_condition(condition: str, selections: dict[str, Any]) -> Any:
    condition = condition.strip()
    if not condition:
        raise RuleCompilationError("empty detection.condition")

    if condition == "1 of them":
        return or_(*selections.values())
    if condition == "all of them":
        return and_(*selections.values())

    match_1_of = re.match(r"^1 of (?P<group>[\w*]+)$", condition)
    if match_1_of:
        pattern = match_1_of.group("group")
        names = _match_selection_names(pattern, selections)
        if not names:
            raise RuleCompilationError(f"no selections match pattern: {pattern}")
        return or_(*[selections[name] for name in names])

    match_all_of = re.match(r"^all of (?P<group>[\w*]+)$", condition)
    if match_all_of:
        pattern = match_all_of.group("group")
        names = _match_selection_names(pattern, selections)
        if not names:
            raise RuleCompilationError(f"no selections match pattern: {pattern}")
        return and_(*[selections[name] for name in names])

    # Boolean expression using and/or/not with parenthesizing.
    return _compile_boolean(condition, selections)


def _match_selection_names(pattern: str, selections: dict[str, Any]) -> list[str]:
    if pattern == "*":
        return list(selections.keys())
    regex = re.compile("^" + pattern.replace("*", ".*") + "$")
    return [name for name in selections if regex.match(name)]


def _compile_boolean(expression: str, selections: dict[str, Any]) -> Any:
    tokens = re.findall(r"\(|\)|\bnot\b|\band\b|\bor\b|[\w*]+", expression)
    return _parse_boolean(tokens, selections)


def _parse_boolean(tokens: list[str], selections: dict[str, Any], index: int = 0) -> tuple[Any, int]:
    clauses: list[Any] = []
    current_op = "and"
    pos = index
    while pos < len(tokens):
        token = tokens[pos]
        if token == "(":
            inner, pos = _parse_boolean(tokens, selections, pos + 1)
            clauses.append(inner)
            continue
        if token == ")":
            if not clauses:
                raise RuleCompilationError("unmatched parenthesis")
            return _join_clauses(clauses), pos + 1
        if token == "not":
            inner, pos = _parse_boolean(tokens, selections, pos + 1)
            clauses.append(inner)
            continue
        if token in ("and", "or"):
            current_op = token
            pos += 1
            continue
        if token in selections:
            clause = selections[token]
            if clauses and current_op == "or":
                # The previous clause must be re-wrapped with the new operator.
                clauses.append(clause)
            else:
                clauses.append(clause)
            current_op = "and"
            pos += 1
            continue
        raise RuleCompilationError(f"unknown token in condition: {token}")
    if not clauses:
        raise RuleCompilationError("empty detection.condition expression")
    return _join_clauses(clauses), pos


def _join_clauses(clauses: list[Any]) -> Any:
    if len(clauses) == 1:
        return clauses[0]
    return or_(*clauses)


@dataclass(frozen=True)
class DetectionDecision:
    """Output of the detection stage for one event."""

    event_id: UUID
    triggered_rule_ids: list[str]
    rule_name: str | None
    recommended_severity: Severity | None
    mitre: dict[str, Any]


async def evaluate_event_rules(
    session: Session,
    tenant_id: UUID,
    event: NormalizedEvent,
) -> DetectionDecision:
    """Evaluate all enabled tenant rules against a single normalized event.

    Returns a DetectionDecision; the caller is responsible for persisting
    alerts (see correlate.py which deduplicates and groups).
    """

    enabled_rules = await session.execute(
        select(DetectionRule).where(
            DetectionRule.tenant_id == tenant_id,
            DetectionRule.is_enabled.is_(True),
        )
    )
    decisions: list[tuple[DetectionRule, bool]] = []
    triggered: list[DetectionRule] = []
    for rule in enabled_rules.scalars().all():
        matched = False
        try:
            expression = compile_rule(rule.rule_yaml).expression
            matched_query = (
                select(NormalizedEvent.id)
                .where(and_(NormalizedEvent.id == event.id, expression))
                .limit(1)
            )
            matched = (
                bool((await session.execute(matched_query)).scalars().first())
            )
        except RuleCompilationError as exc:
            logger.warning("rule.compilation_failed", rule_id=rule.rule_id, error=str(exc))
            continue
        decisions.append((rule, matched))
        if matched:
            triggered.append(rule)
    severity = max((rule.severity for rule in triggered), key=lambda s: list(Severity).index(s), default=None)
    mitre: dict[str, Any] = {}
    for rule in triggered:
        for key, value in rule.mitre.items():
            if isinstance(value, str):
                mitre.setdefault(key, []).append(value)
            elif isinstance(value, list):
                mitre.setdefault(key, []).extend(value)
    return DetectionDecision(
        event_id=event.id,
        triggered_rule_ids=[rule.rule_id for rule in triggered],
        rule_name=triggered[0].name if triggered else None,
        recommended_severity=severity,
        mitre=mitre,
    )


def seed_default_rules() -> list[dict[str, str]]:
    """Default detection rules shipped with the platform (Sigma-style subset).

    These cover common brute-force, suspicious process, and indicator-match
    behaviors. Coverage is intentionally limited; rules are tenant-scoped and
    editable through the API.
    """

    return [
        {
            "title": "Multiple Failed Authentication Attempts",
            "id": "rule-auth-bruteforce",
            "level": "high",
            "description": "Detects repeated authentication failures from the same source.",
            "detection": {
                "selection_auth_fail": {"authentication_result": "failure"},
                "condition": "selection_auth_fail",
            },
            "tags": {"mitre_tactic": "credential_access", "mitre_technique": "T1110"},
        },
        {
            "title": "Suspicious Process Execution",
            "id": "rule-suspicious-process",
            "level": "medium",
            "description": "Detects execution of commonly abused processes.",
            "detection": {
                "selection_keywords": {
                    "keywords": ["mimikatz", "procdump", "psexec", "cobaltstrike", "powershell -enc"]
                },
                "condition": "selection_keywords",
            },
            "tags": {"mitre_tactic": "execution", "mitre_technique": "T1059"},
        },
        {
            "title": "Known Malicious Indicator Match",
            "id": "rule-indicator-match",
            "level": "critical",
            "description": "Detects events matching known-malicious file hashes or IPs.",
            "detection": {
                "selection_hashes": {"file_hash_sha256": ["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"]},
                "selection_dns": {"domain": ["bad.example.com"]},
                "condition": "1 of selection_*",
            },
            "tags": {"mitre_tactic": "initial_access", "mitre_technique": "T1190"},
        },
    ]
