from app.agents.investigation import (
    analyze_attack_chain,
    build_timeline,
    choose_investigation_next_action,
    identify_affected_assets,
    run_investigation,
)


def test_build_timeline_orders_events_by_timestamp() -> None:
    result = build_timeline(
        {
            "events": [
                {"event_id": "2", "occurred_at": "2026-06-11T10:05:00Z"},
                {"event_id": "1", "occurred_at": "2026-06-11T10:00:00Z"},
            ]
        }
    )

    assert [event["event_id"] for event in result["timeline"]] == ["1", "2"]


def test_identify_affected_assets_uses_targets_and_destination_ips() -> None:
    result = identify_affected_assets(
        {
            "timeline": [
                {"target": "host-1", "destination_ip": "10.0.0.10"},
                {"target": "host-2", "destination_ip": "10.0.0.10"},
            ]
        }
    )

    assert result["affected_assets"] == ["10.0.0.10", "host-1", "host-2"]


def test_analyze_attack_chain_detects_initial_access_and_lateral_movement() -> None:
    result = analyze_attack_chain(
        {
            "timeline": [
                {
                    "occurred_at": "2026-06-11T10:00:00Z",
                    "event_type": "login_success",
                    "actor": "alice",
                    "target": "vpn",
                    "summary": "Successful login after repeated failures",
                },
                {
                    "occurred_at": "2026-06-11T10:05:00Z",
                    "event_type": "rdp_session",
                    "actor": "alice",
                    "target": "server-1",
                    "summary": "RDP remote login observed",
                },
            ],
            "affected_assets": ["vpn", "server-1"],
        }
    )

    assert result["initial_access"] == "valid_accounts"
    assert result["lateral_movement"] == "suspected"
    assert result["findings"]["event_count"] == 2
    assert result["evidence_gaps"] == []
    assert result["containment_required"] is True
    assert result["scope_complete"] is True
    assert result["confidence"] == 0.75


def test_analyze_attack_chain_records_evidence_gaps() -> None:
    result = analyze_attack_chain(
        {
            "timeline": [
                {
                    "occurred_at": "2026-06-11T10:00:00Z",
                    "event_type": "network_alert",
                    "summary": "Suspicious outbound connection",
                }
            ],
            "affected_assets": [],
        }
    )

    assert result["evidence_gaps"] == [
        "missing_actor_context",
        "missing_affected_assets",
        "initial_access_not_identified",
    ]
    assert result["scope_complete"] is False


def test_choose_next_action_closes_low_confidence_evidence_gaps() -> None:
    result = choose_investigation_next_action(
        {
            "timeline": [{"event_id": "1"}],
            "evidence_gaps": ["missing_actor_context"],
            "confidence": 0.55,
            "initial_access": "unknown",
            "lateral_movement": "not_observed",
        }
    )

    assert result["next_action"] == "close_evidence_gaps"


def test_choose_next_action_contains_lateral_movement() -> None:
    result = choose_investigation_next_action(
        {
            "initial_access": "valid_accounts",
            "lateral_movement": "suspected",
        }
    )

    assert result["next_action"] == "contain_and_expand_scope"


def test_run_investigation_returns_complete_findings() -> None:
    result = run_investigation(
        {
            "incident_id": "incident-1",
            "events": [
                {
                    "occurred_at": "2026-06-11T10:00:00Z",
                    "event_type": "phishing_email",
                    "actor": "attacker@example.net",
                    "target": "user@example.com",
                    "summary": "Phishing message delivered",
                }
            ],
        }
    )

    assert result["initial_access"] == "phishing"
    assert result["affected_assets"] == ["user@example.com"]
    assert result["attack_chain"] == [
        "2026-06-11T10:00:00Z: phishing_email by attacker@example.net against user@example.com"
    ]
    assert result["next_action"] == "collect_endpoint_and_identity_evidence"
