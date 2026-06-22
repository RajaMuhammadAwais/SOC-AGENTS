from typing import Any, TypedDict


class InvestigationEvent(TypedDict, total=False):
    event_id: str
    event_type: str
    occurred_at: str
    actor: str
    target: str
    source_ip: str
    destination_ip: str
    summary: str


class InvestigationState(TypedDict, total=False):
    incident_id: str
    objective: str
    events: list[InvestigationEvent]
    timeline: list[InvestigationEvent]
    affected_assets: list[str]
    initial_access: str
    lateral_movement: str
    attack_chain: list[str]
    findings: dict[str, Any]
    evidence_gaps: list[str]
    containment_required: bool
    scope_complete: bool
    confidence: float
    next_action: str


def build_timeline(state: InvestigationState) -> InvestigationState:
    events = sorted(
        state.get("events", []),
        key=lambda event: event.get("occurred_at", ""),
    )
    return {"timeline": events}


def identify_affected_assets(state: InvestigationState) -> InvestigationState:
    assets: set[str] = set()
    for event in state.get("timeline", state.get("events", [])):
        for key in ("target", "destination_ip"):
            value = event.get(key)
            if value:
                assets.add(value)
    return {"affected_assets": sorted(assets)}


def analyze_attack_chain(state: InvestigationState) -> InvestigationState:
    timeline = state.get("timeline", state.get("events", []))
    initial_access = _find_initial_access(timeline)
    lateral_movement = _find_lateral_movement(timeline)
    attack_chain = _build_attack_chain(timeline)
    evidence_gaps = _evidence_gaps(timeline, state.get("affected_assets", []))
    containment_required = lateral_movement != "not_observed"
    return {
        "initial_access": initial_access,
        "lateral_movement": lateral_movement,
        "attack_chain": attack_chain,
        "evidence_gaps": evidence_gaps,
        "containment_required": containment_required,
        "scope_complete": not evidence_gaps and bool(timeline),
        "findings": {
            "initial_access": initial_access,
            "lateral_movement": lateral_movement,
            "event_count": len(timeline),
            "affected_asset_count": len(state.get("affected_assets", [])),
            "evidence_gap_count": len(evidence_gaps),
        },
        "confidence": _confidence_score(timeline, initial_access, lateral_movement),
    }


def choose_investigation_next_action(state: InvestigationState) -> InvestigationState:
    lateral_movement = state.get("lateral_movement", "not_observed")
    initial_access = state.get("initial_access", "unknown")
    if lateral_movement != "not_observed":
        return {"next_action": "contain_and_expand_scope"}
    if not state.get("timeline") and not state.get("events"):
        return {"next_action": "collect_additional_logs"}
    if state.get("evidence_gaps") and state.get("confidence", 0.0) < 0.65:
        return {"next_action": "close_evidence_gaps"}
    if initial_access != "unknown":
        return {"next_action": "collect_endpoint_and_identity_evidence"}
    return {"next_action": "collect_additional_logs"}


def run_investigation(state: InvestigationState) -> InvestigationState:
    current: InvestigationState = {**state}
    current.update(build_timeline(current))
    current.update(identify_affected_assets(current))
    current.update(analyze_attack_chain(current))
    current.update(choose_investigation_next_action(current))
    return current


def _find_initial_access(events: list[InvestigationEvent]) -> str:
    for event in events:
        text = _event_text(event)
        if "phishing" in text:
            return "phishing"
        if "successful login" in text or "login_success" in text:
            return "valid_accounts"
        if "exploit" in text or "cve-" in text:
            return "exploit_public_facing_application"
    return "unknown"


def _find_lateral_movement(events: list[InvestigationEvent]) -> str:
    for event in events:
        text = _event_text(event)
        if any(keyword in text for keyword in ("rdp", "winrm", "smb", "remote login", "lateral")):
            return "suspected"
    return "not_observed"


def _build_attack_chain(events: list[InvestigationEvent]) -> list[str]:
    chain: list[str] = []
    for event in events:
        occurred_at = event.get("occurred_at", "unknown_time")
        event_type = event.get("event_type", "event")
        actor = event.get("actor", "unknown_actor")
        target = event.get("target") or event.get("destination_ip") or "unknown_target"
        chain.append(f"{occurred_at}: {event_type} by {actor} against {target}")
    return chain


def _confidence_score(
    events: list[InvestigationEvent],
    initial_access: str,
    lateral_movement: str,
) -> float:
    score = 0.35 + min(len(events), 5) * 0.1
    if initial_access != "unknown":
        score += 0.1
    if lateral_movement != "not_observed":
        score += 0.1
    return round(min(score, 0.95), 2)


def _evidence_gaps(events: list[InvestigationEvent], affected_assets: list[str]) -> list[str]:
    gaps: list[str] = []
    if not events:
        return ["no_timeline_events"]
    if not any(event.get("actor") for event in events):
        gaps.append("missing_actor_context")
    if not affected_assets:
        gaps.append("missing_affected_assets")
    if not any(_find_initial_access([event]) != "unknown" for event in events):
        gaps.append("initial_access_not_identified")
    return gaps


def _event_text(event: InvestigationEvent) -> str:
    return " ".join(
        [
            event.get("event_type", ""),
            event.get("summary", ""),
            event.get("actor", ""),
            event.get("target", ""),
        ]
    ).lower()
