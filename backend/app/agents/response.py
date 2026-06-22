from typing import Literal, TypedDict

ResponseActionType = Literal[
    "block_ip",
    "disable_account",
    "isolate_host",
    "reset_password",
    "collect_forensics",
    "notify_owner",
]


class ResponseAction(TypedDict):
    action_type: ResponseActionType
    target: str
    reason: str
    requires_approval: bool


class ResponseState(TypedDict, total=False):
    incident_id: str
    risk_level: str
    observable_type: str
    observable_value: str
    actor: str
    target: str
    affected_assets: list[str]
    approved: bool
    execution_mode: str
    recommended_actions: list[ResponseAction]
    blocked_actions: list[ResponseAction]
    executed_actions: list[ResponseAction]
    approval_summary: str
    next_action: str


def recommend_response_actions(state: ResponseState) -> ResponseState:
    actions: list[ResponseAction] = []
    risk_level = state.get("risk_level", "medium").lower()

    if state.get("observable_type") == "ip" and state.get("observable_value"):
        actions.append(
            _action(
                "block_ip",
                state["observable_value"],
                "Malicious or suspicious IP observed in incident context.",
                risk_level in {"critical", "high"},
            )
        )

    if state.get("actor"):
        actions.append(
            _action(
                "disable_account",
                state["actor"],
                "Account is associated with suspicious incident activity.",
                True,
            )
        )
        actions.append(
            _action(
                "reset_password",
                state["actor"],
                "Credential exposure or misuse may require password reset.",
                risk_level != "low",
            )
        )

    for asset in state.get("affected_assets", []):
        if risk_level in {"critical", "high"}:
            actions.append(
                _action(
                    "isolate_host",
                    asset,
                    "High-risk affected asset should be contained.",
                    True,
                )
            )
        actions.append(
            _action(
                "collect_forensics",
                asset,
                "Preserve evidence before recovery or eradication steps.",
                False,
            )
        )

    if state.get("target"):
        actions.append(
            _action(
                "notify_owner",
                state["target"],
                "System or service owner should be notified.",
                False,
            )
        )

    return {"recommended_actions": _deduplicate_actions(actions)}


def execute_response_actions(state: ResponseState) -> ResponseState:
    actions = state.get("recommended_actions", [])
    requires_approval = [action for action in actions if action["requires_approval"]]
    safe_actions = [action for action in actions if not action["requires_approval"]]

    if requires_approval and not state.get("approved", False):
        executed_actions = (
            safe_actions if state.get("execution_mode", "recommend") == "execute" else []
        )
        return {
            "blocked_actions": requires_approval,
            "executed_actions": executed_actions,
            "approval_summary": _approval_summary(requires_approval),
            "next_action": "request_human_approval",
        }

    if state.get("execution_mode", "recommend") != "execute":
        return {
            "blocked_actions": [],
            "executed_actions": [],
            "next_action": "present_recommendations",
        }

    return {
        "blocked_actions": [],
        "executed_actions": actions,
        "approval_summary": "",
        "next_action": "verify_response_effectiveness",
    }


def run_response(state: ResponseState) -> ResponseState:
    current: ResponseState = {**state}
    current.update(recommend_response_actions(current))
    current.update(execute_response_actions(current))
    return current


def _action(
    action_type: ResponseActionType,
    target: str,
    reason: str,
    requires_approval: bool,
) -> ResponseAction:
    return {
        "action_type": action_type,
        "target": target,
        "reason": reason,
        "requires_approval": requires_approval,
    }


def _deduplicate_actions(actions: list[ResponseAction]) -> list[ResponseAction]:
    seen: set[tuple[str, str]] = set()
    unique_actions: list[ResponseAction] = []
    for action in actions:
        key = (action["action_type"], action["target"])
        if key not in seen:
            seen.add(key)
            unique_actions.append(action)
    return unique_actions


def _approval_summary(actions: list[ResponseAction]) -> str:
    targets = ", ".join(f"{action['action_type']}:{action['target']}" for action in actions)
    return f"Human approval required for {len(actions)} action(s): {targets}."
