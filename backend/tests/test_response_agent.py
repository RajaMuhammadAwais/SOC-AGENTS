from app.agents.response import execute_response_actions, recommend_response_actions, run_response


def test_recommend_response_actions_for_high_risk_incident() -> None:
    result = recommend_response_actions(
        {
            "risk_level": "high",
            "observable_type": "ip",
            "observable_value": "203.0.113.10",
            "actor": "alice",
            "affected_assets": ["host-1"],
            "target": "vpn",
        }
    )

    action_types = [action["action_type"] for action in result["recommended_actions"]]

    assert action_types == [
        "block_ip",
        "disable_account",
        "reset_password",
        "isolate_host",
        "collect_forensics",
        "notify_owner",
    ]
    assert result["recommended_actions"][0]["requires_approval"] is True


def test_execute_response_blocks_approval_required_actions_until_approved() -> None:
    result = execute_response_actions(
        {
            "recommended_actions": [
                {
                    "action_type": "disable_account",
                    "target": "alice",
                    "reason": "Suspicious activity",
                    "requires_approval": True,
                }
            ]
        }
    )

    assert result["executed_actions"] == []
    assert result["blocked_actions"][0]["target"] == "alice"
    assert (
        result["approval_summary"]
        == "Human approval required for 1 action(s): disable_account:alice."
    )
    assert result["next_action"] == "request_human_approval"


def test_execute_response_runs_safe_actions_while_waiting_for_approval() -> None:
    result = execute_response_actions(
        {
            "execution_mode": "execute",
            "recommended_actions": [
                {
                    "action_type": "disable_account",
                    "target": "alice",
                    "reason": "Suspicious activity",
                    "requires_approval": True,
                },
                {
                    "action_type": "collect_forensics",
                    "target": "host-1",
                    "reason": "Preserve evidence",
                    "requires_approval": False,
                },
            ],
        }
    )

    assert [action["action_type"] for action in result["blocked_actions"]] == ["disable_account"]
    assert [action["action_type"] for action in result["executed_actions"]] == ["collect_forensics"]
    assert result["next_action"] == "request_human_approval"


def test_execute_response_presents_recommendations_when_not_in_execute_mode() -> None:
    result = execute_response_actions(
        {
            "approved": True,
            "execution_mode": "recommend",
            "recommended_actions": [
                {
                    "action_type": "collect_forensics",
                    "target": "host-1",
                    "reason": "Preserve evidence",
                    "requires_approval": False,
                }
            ],
        }
    )

    assert result["executed_actions"] == []
    assert result["next_action"] == "present_recommendations"


def test_run_response_executes_only_when_approved_and_execute_mode() -> None:
    result = run_response(
        {
            "risk_level": "low",
            "actor": "alice",
            "approved": True,
            "execution_mode": "execute",
        }
    )

    assert [action["action_type"] for action in result["executed_actions"]] == [
        "disable_account",
        "reset_password",
    ]
    assert result["next_action"] == "verify_response_effectiveness"
