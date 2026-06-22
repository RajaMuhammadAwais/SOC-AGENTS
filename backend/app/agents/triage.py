import json
from hashlib import sha256
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.domain.llm import LLMClient, LLMMessage, LLMRequest


class TriageState(TypedDict, total=False):
    tenant_id: str
    alert_id: str
    objective: str
    title: str
    description: str
    source: str
    actor: str
    target: str
    source_ip: str
    risk_score: int
    mitre: dict[str, object]
    duplicate_count: int
    duplicate_of: str
    duplicate_key: str
    is_duplicate: bool
    severity: str
    category: str
    confidence: float
    rationale: str
    priority_score: int
    review_reasons: list[str]
    escalation_required: bool
    next_action: str


SEVERITY_BASE_SCORE = {
    "informational": 10,
    "low": 25,
    "medium": 50,
    "high": 75,
    "critical": 95,
}

CATEGORY_KEYWORDS = {
    "credential_access": ("failed login", "brute force", "mfa", "password", "credential"),
    "malware": ("malware", "ransomware", "trojan", "payload", "suspicious hash"),
    "command_execution": ("powershell", "encoded command", "cmd.exe", "shell", "script"),
    "network_reconnaissance": ("port scan", "scan", "probe", "dns", "firewall"),
    "privilege_escalation": ("privilege", "administrator", "admin", "sudo", "escalation"),
    "data_exfiltration": ("exfil", "upload", "large transfer", "data transfer"),
}


def deduplicate_alert(state: TriageState) -> TriageState:
    duplicate_key = build_duplicate_key(state)
    is_duplicate = bool(state.get("duplicate_of")) or int(state.get("duplicate_count", 0)) > 0
    return {
        "duplicate_key": duplicate_key,
        "is_duplicate": is_duplicate,
    }


def build_duplicate_key(state: TriageState) -> str:
    parts = [
        state.get("source", ""),
        state.get("title", ""),
        state.get("actor", ""),
        state.get("target", ""),
        state.get("source_ip", ""),
    ]
    raw = "|".join(_normalize_part(part) for part in parts)
    if not raw.replace("|", ""):
        raw = state.get("alert_id", "")
    return sha256(raw.encode()).hexdigest()[:32]


def classify_alert(state: TriageState) -> TriageState:
    category = state.get("category") or _infer_category(state)
    severity = state.get("severity") or _infer_severity(state)
    return {
        "severity": severity,
        "category": category,
        "confidence": state.get("confidence", 0.5),
        "rationale": state.get("rationale", _build_classification_rationale(severity, category)),
    }


def prioritize_alert(state: TriageState) -> TriageState:
    severity = state.get("severity", "medium")
    priority_score = SEVERITY_BASE_SCORE.get(severity, 50)
    if state.get("risk_score") is not None:
        priority_score = max(priority_score, int(state["risk_score"]))
    if state.get("mitre"):
        priority_score += 5
    if state.get("is_duplicate"):
        priority_score -= 20
    priority_score = min(max(priority_score, 0), 100)
    review_reasons = _review_reasons(state, priority_score)
    return {
        "priority_score": priority_score,
        "review_reasons": review_reasons,
        "escalation_required": _requires_escalation(state, priority_score, review_reasons),
    }


def choose_next_action(state: TriageState) -> TriageState:
    if state.get("is_duplicate"):
        return {"next_action": "attach_to_existing_case"}
    severity = state.get("severity", "medium")
    priority_score = state.get("priority_score", SEVERITY_BASE_SCORE.get(severity, 50))
    confidence = state.get("confidence", 0.5)
    if state.get("review_reasons") and confidence < 0.55:
        return {"next_action": "analyst_review_required"}
    if state.get("escalation_required"):
        return {"next_action": "escalate_to_senior_analyst"}
    if severity in {"high", "critical"} or priority_score >= 70:
        return {"next_action": "open_investigation"}
    if severity in {"informational", "low"} and priority_score < 40:
        return {"next_action": "monitor"}
    return {"next_action": "queue_for_review"}


async def generate_ai_triage_findings(
    state: TriageState,
    llm_client: LLMClient,
) -> TriageState:
    response = await llm_client.complete(
        LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are an enterprise SOC alert triage agent. "
                        "Classify alerts conservatively and return only JSON with keys "
                        "severity, category, confidence, and rationale."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"Objective: {state.get('objective', 'triage alert')}\n"
                        f"Current severity: {state.get('severity', 'unknown')}\n"
                        f"Current category: {state.get('category', 'unknown')}"
                    ),
                ),
            ],
            temperature=0,
            max_tokens=512,
            response_format={"type": "json_object"},
            metadata={
                "agent": "alert_triage",
                "tenant_id": state.get("tenant_id", ""),
                "alert_id": state.get("alert_id", ""),
            },
        )
    )
    parsed = _parse_triage_json(response.content)
    return {
        "severity": _coerce_text(parsed.get("severity"), state.get("severity", "medium")),
        "category": _coerce_text(parsed.get("category"), state.get("category", "needs_review")),
        "confidence": _coerce_confidence(parsed.get("confidence"), state.get("confidence", 0.5)),
        "rationale": _coerce_text(parsed.get("rationale"), response.content),
    }


def _parse_triage_json(content: str) -> dict[str, object]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"rationale": content}
    if not isinstance(parsed, dict):
        return {"rationale": content}
    return parsed


def _coerce_text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default.strip()


def _coerce_confidence(value: object, default: float) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(confidence, 0.0), 1.0)


def _infer_category(state: TriageState) -> str:
    text = _state_text(state)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "needs_review"


def _infer_severity(state: TriageState) -> str:
    risk_score = state.get("risk_score")
    if risk_score is not None:
        score = int(risk_score)
        if score >= 90:
            return "critical"
        if score >= 70:
            return "high"
        if score >= 40:
            return "medium"
        if score >= 20:
            return "low"
        return "informational"

    text = _state_text(state)
    if any(keyword in text for keyword in ("ransomware", "exfil", "domain admin")):
        return "critical"
    if any(keyword in text for keyword in ("brute force", "malware", "encoded command")):
        return "high"
    return "medium"


def _build_classification_rationale(severity: str, category: str) -> str:
    return f"Classified as {severity} severity and {category} category from alert context."


def _review_reasons(state: TriageState, priority_score: int) -> list[str]:
    reasons: list[str] = []
    confidence = state.get("confidence", 0.5)
    category = state.get("category", "needs_review")
    severity = state.get("severity", "medium")

    if confidence < 0.55:
        reasons.append("low_confidence_signal")
    if category == "needs_review":
        reasons.append("unclear_attack_category")
    if severity in {"high", "critical"} and not any(
        state.get(field) for field in ("actor", "target", "source_ip")
    ):
        reasons.append("high_severity_without_key_entities")
    if priority_score >= 70 and not state.get("mitre"):
        reasons.append("high_priority_without_mitre_mapping")
    return reasons


def _requires_escalation(
    state: TriageState,
    priority_score: int,
    review_reasons: list[str],
) -> bool:
    if state.get("is_duplicate"):
        return False
    severity = state.get("severity", "medium")
    confidence = state.get("confidence", 0.5)
    if severity == "critical" and confidence >= 0.7:
        return True
    return priority_score >= 85 and "low_confidence_signal" not in review_reasons


def _state_text(state: TriageState) -> str:
    return " ".join(
        [
            state.get("objective", ""),
            state.get("title", ""),
            state.get("description", ""),
            state.get("source", ""),
        ]
    ).lower()


def _normalize_part(value: str) -> str:
    return " ".join(value.lower().strip().split())


def create_triage_graph() -> StateGraph:
    graph = StateGraph(TriageState)
    graph.add_node("deduplicate_alert", deduplicate_alert)
    graph.add_node("classify_alert", classify_alert)
    graph.add_node("prioritize_alert", prioritize_alert)
    graph.add_node("choose_next_action", choose_next_action)
    graph.add_edge(START, "deduplicate_alert")
    graph.add_edge("deduplicate_alert", "classify_alert")
    graph.add_edge("classify_alert", "prioritize_alert")
    graph.add_edge("prioritize_alert", "choose_next_action")
    graph.add_edge("choose_next_action", END)
    return graph


def compile_triage_graph():
    return create_triage_graph().compile()
