import pytest

from app.agents.triage import (
    build_duplicate_key,
    choose_next_action,
    classify_alert,
    compile_triage_graph,
    deduplicate_alert,
    generate_ai_triage_findings,
    prioritize_alert,
)
from app.domain.llm import LLMRequest, LLMResponse


def test_triage_classification_defaults_to_review() -> None:
    result = classify_alert({"tenant_id": "tenant-1", "alert_id": "alert-1"})

    assert result["severity"] == "medium"
    assert result["category"] == "needs_review"


def test_triage_critical_alert_opens_investigation() -> None:
    result = choose_next_action({"severity": "critical", "priority_score": 95})

    assert result["next_action"] == "open_investigation"


def test_triage_classifies_credential_access_from_alert_context() -> None:
    result = classify_alert(
        {
            "title": "Repeated failed login followed by success",
            "description": "Possible brute force against privileged account",
        }
    )

    assert result["severity"] == "high"
    assert result["category"] == "credential_access"


def test_deduplicate_alert_builds_stable_key_and_marks_duplicates() -> None:
    state = {
        "title": "Repeated Failed Login",
        "source": "identity",
        "actor": "alice@example.com",
        "source_ip": "10.0.0.5",
        "duplicate_count": 1,
    }

    result = deduplicate_alert(state)

    assert result["duplicate_key"] == build_duplicate_key(state)
    assert result["is_duplicate"] is True


def test_prioritize_alert_uses_risk_score_and_mitre_context() -> None:
    result = prioritize_alert(
        {
            "severity": "medium",
            "risk_score": 72,
            "mitre": {"technique": "T1110"},
        }
    )

    assert result["priority_score"] == 77


def test_prioritize_alert_adds_review_reasons_for_weak_context() -> None:
    result = prioritize_alert(
        {
            "severity": "high",
            "category": "needs_review",
            "confidence": 0.4,
            "risk_score": 75,
        }
    )

    assert result["review_reasons"] == [
        "low_confidence_signal",
        "unclear_attack_category",
        "high_severity_without_key_entities",
        "high_priority_without_mitre_mapping",
    ]
    assert result["escalation_required"] is False


def test_triage_low_confidence_review_reasons_hold_for_analyst_review() -> None:
    result = choose_next_action(
        {
            "severity": "high",
            "priority_score": 75,
            "confidence": 0.4,
            "review_reasons": ["low_confidence_signal"],
        }
    )

    assert result["next_action"] == "analyst_review_required"


def test_triage_escalates_high_confidence_critical_alert() -> None:
    priority = prioritize_alert(
        {
            "severity": "critical",
            "category": "credential_access",
            "confidence": 0.85,
            "actor": "alice@example.com",
            "target": "vpn",
            "mitre": {"technique": "T1110"},
        }
    )

    result = choose_next_action(
        {
            "severity": "critical",
            "confidence": 0.85,
            **priority,
        }
    )

    assert priority["escalation_required"] is True
    assert result["next_action"] == "escalate_to_senior_analyst"


def test_duplicate_alert_attaches_to_existing_case() -> None:
    result = choose_next_action(
        {
            "severity": "critical",
            "priority_score": 95,
            "is_duplicate": True,
        }
    )

    assert result["next_action"] == "attach_to_existing_case"


def test_compiled_triage_graph_runs_all_nodes() -> None:
    graph = compile_triage_graph()

    result = graph.invoke(
        {
            "tenant_id": "tenant-1",
            "alert_id": "alert-1",
            "title": "Encoded PowerShell execution",
            "description": "Encoded command launched from user profile",
            "source": "edr",
            "risk_score": 88,
        }
    )

    assert result["duplicate_key"]
    assert result["category"] == "command_execution"
    assert result["severity"] == "high"
    assert result["priority_score"] == 88
    assert result["next_action"] == "analyst_review_required"


class StubLLMClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            content=self.content,
            model="test-model",
            provider="test",
        )


@pytest.mark.asyncio
async def test_generate_ai_triage_findings_parses_structured_response() -> None:
    client = StubLLMClient(
        '{"severity":"critical","category":"credential_access","confidence":0.91,'
        '"rationale":"Multiple failed logins followed by success."}'
    )

    result = await generate_ai_triage_findings(
        {
            "tenant_id": "tenant-1",
            "alert_id": "alert-1",
            "objective": "triage suspicious login activity",
        },
        client,
    )

    assert result["severity"] == "critical"
    assert result["category"] == "credential_access"
    assert result["confidence"] == 0.91
    assert result["rationale"] == "Multiple failed logins followed by success."
    assert client.requests[0].response_format == {"type": "json_object"}
