from app.agents.threat_hunting import (
    build_hunt_query,
    choose_hunt_next_action,
    find_similar_events,
    run_threat_hunt,
    summarize_hunt_results,
)


def test_build_hunt_query_infers_terms_sources_and_techniques() -> None:
    result = build_hunt_query(
        {
            "hypothesis": "Hunt for RDP lateral movement from compromised VPN users",
            "seed_indicators": ["10.0.0.5"],
        }
    )

    assert result["query_terms"] == ["10.0.0.5", "lateral", "rdp", "vpn"]
    assert result["required_data_sources"] == [
        "Logon Session",
        "Network Traffic",
        "User Account",
    ]
    assert result["technique_hints"] == ["Initial Access", "Lateral Movement"]


def test_find_similar_events_matches_query_terms_and_sorts_by_score() -> None:
    result = find_similar_events(
        {
            "query_terms": ["rdp", "10.0.0.5"],
            "events": [
                {
                    "event_id": "2",
                    "occurred_at": "2026-06-11T10:05:00Z",
                    "event_type": "rdp_session",
                    "source_ip": "10.0.0.5",
                },
                {
                    "event_id": "1",
                    "occurred_at": "2026-06-11T10:00:00Z",
                    "event_type": "vpn_login",
                    "source_ip": "10.0.0.5",
                },
            ],
        }
    )

    assert [match["event"]["event_id"] for match in result["matched_events"]] == ["2", "1"]
    assert result["matched_events"][0]["matched_terms"] == ["rdp", "10.0.0.5"]


def test_summarize_hunt_results_extracts_entities_and_gaps() -> None:
    result = summarize_hunt_results(
        {
            "required_data_sources": ["Logon Session", "Network Traffic"],
            "available_data_sources": ["Logon Session"],
            "matched_events": [
                {
                    "event": {
                        "actor": "alice",
                        "target": "server-1",
                        "source_ip": "10.0.0.5",
                        "destination_ip": "10.0.0.20",
                    },
                    "matched_terms": ["rdp"],
                    "score": 1,
                }
            ],
        }
    )

    assert result["similar_entities"]["actors"] == ["alice"]
    assert result["similar_entities"]["targets"] == ["server-1"]
    assert result["coverage_gaps"] == ["Network Traffic"]
    assert result["confidence"] == 0.53


def test_choose_next_action_collects_missing_telemetry_first() -> None:
    result = choose_hunt_next_action(
        {
            "coverage_gaps": ["Network Traffic"],
            "matched_events": [{"event": {"event_id": "1"}, "matched_terms": ["rdp"], "score": 1}],
        }
    )

    assert result["next_action"] == "collect_missing_telemetry"


def test_run_threat_hunt_returns_complete_result() -> None:
    result = run_threat_hunt(
        {
            "hypothesis": "Find similar PowerShell command execution",
            "available_data_sources": ["Process", "Script"],
            "events": [
                {
                    "event_id": "evt-1",
                    "occurred_at": "2026-06-11T11:00:00Z",
                    "event_type": "process_start",
                    "actor": "svc-backup",
                    "target": "host-1",
                    "summary": "PowerShell command launched encoded script",
                }
            ],
        }
    )

    assert result["query_terms"] == ["command", "powershell"]
    assert result["matched_events"][0]["event"]["event_id"] == "evt-1"
    assert result["coverage_gaps"] == []
    assert result["next_action"] == "open_investigation_for_matched_activity"
