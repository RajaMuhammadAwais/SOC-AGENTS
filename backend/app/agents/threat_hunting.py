from typing import TypedDict


class HuntEvent(TypedDict, total=False):
    event_id: str
    event_type: str
    occurred_at: str
    actor: str
    target: str
    source_ip: str
    destination_ip: str
    summary: str
    mitre_technique: str


class HuntMatch(TypedDict):
    event: HuntEvent
    matched_terms: list[str]
    score: int


class ThreatHuntState(TypedDict, total=False):
    hunt_id: str
    hypothesis: str
    seed_indicators: list[str]
    events: list[HuntEvent]
    available_data_sources: list[str]
    query_terms: list[str]
    required_data_sources: list[str]
    technique_hints: list[str]
    matched_events: list[HuntMatch]
    similar_entities: dict[str, list[str]]
    coverage_gaps: list[str]
    findings: list[str]
    review_reasons: list[str]
    confidence: float
    next_action: str


def build_hunt_query(state: ThreatHuntState) -> ThreatHuntState:
    terms = {_normalize_term(value) for value in state.get("seed_indicators", []) if value.strip()}
    hypothesis = state.get("hypothesis", "")
    terms.update(_keyword_terms(hypothesis))
    technique_hints = _technique_hints(hypothesis, terms)

    return {
        "query_terms": sorted(terms),
        "required_data_sources": _required_data_sources(terms, technique_hints),
        "technique_hints": technique_hints,
    }


def find_similar_events(state: ThreatHuntState) -> ThreatHuntState:
    query_terms = state.get("query_terms") or build_hunt_query(state).get("query_terms", [])
    matches: list[HuntMatch] = []

    for event in state.get("events", []):
        text = _event_text(event)
        matched_terms = [term for term in query_terms if term and term in text]
        if matched_terms:
            matches.append(
                {
                    "event": event,
                    "matched_terms": matched_terms,
                    "score": len(matched_terms),
                }
            )

    matches.sort(
        key=lambda match: (
            -match["score"],
            match["event"].get("occurred_at", ""),
            match["event"].get("event_id", ""),
        )
    )
    return {"matched_events": matches}


def summarize_hunt_results(state: ThreatHuntState) -> ThreatHuntState:
    matches = state.get("matched_events", [])
    required_sources = state.get("required_data_sources", [])
    available_sources = state.get("available_data_sources", [])
    coverage_gaps = _coverage_gaps(required_sources, available_sources)
    similar_entities = _similar_entities(matches)

    findings = [f"Matched {len(matches)} event(s) against the hunt query."]
    if similar_entities["actors"]:
        findings.append(f"Observed actors: {', '.join(similar_entities['actors'])}.")
    if similar_entities["targets"]:
        findings.append(f"Observed targets: {', '.join(similar_entities['targets'])}.")
    if coverage_gaps:
        findings.append(f"Missing telemetry: {', '.join(coverage_gaps)}.")

    return {
        "similar_entities": similar_entities,
        "coverage_gaps": coverage_gaps,
        "findings": findings,
        "review_reasons": _hunt_review_reasons(matches, coverage_gaps, state.get("query_terms", [])),
        "confidence": _confidence_score(matches, coverage_gaps),
    }


def choose_hunt_next_action(state: ThreatHuntState) -> ThreatHuntState:
    if not state.get("query_terms"):
        return {"next_action": "refine_hunt_hypothesis"}
    if state.get("coverage_gaps"):
        return {"next_action": "collect_missing_telemetry"}
    if state.get("matched_events"):
        return {"next_action": "open_investigation_for_matched_activity"}
    return {"next_action": "broaden_hunt_hypothesis"}


def run_threat_hunt(state: ThreatHuntState) -> ThreatHuntState:
    current: ThreatHuntState = {**state}
    current.update(build_hunt_query(current))
    current.update(find_similar_events(current))
    current.update(summarize_hunt_results(current))
    current.update(choose_hunt_next_action(current))
    return current


def _keyword_terms(value: str) -> set[str]:
    text = value.lower()
    terms: set[str] = set()
    for keyword in (
        "rdp",
        "winrm",
        "smb",
        "powershell",
        "phishing",
        "mfa",
        "vpn",
        "cve",
        "exploit",
        "lateral",
        "command",
        "credential",
    ):
        if keyword in text:
            terms.add(keyword)
    return terms


def _technique_hints(hypothesis: str, terms: set[str]) -> list[str]:
    text = hypothesis.lower()
    hints: set[str] = set()
    if {"rdp", "winrm", "smb", "lateral"} & terms:
        hints.add("Lateral Movement")
    if {"phishing", "vpn", "mfa"} & terms:
        hints.add("Initial Access")
    if {"powershell", "command"} & terms:
        hints.add("Execution")
    if {"credential"} & terms or "password" in text:
        hints.add("Credential Access")
    if {"cve", "exploit"} & terms:
        hints.add("Initial Access")
    return sorted(hints)


def _required_data_sources(terms: set[str], technique_hints: list[str]) -> list[str]:
    sources: set[str] = set()
    if {"rdp", "winrm", "smb", "vpn", "mfa", "credential"} & terms:
        sources.add("Logon Session")
        sources.add("User Account")
    if {"rdp", "winrm", "smb", "exploit", "cve"} & terms:
        sources.add("Network Traffic")
    if {"powershell", "command"} & terms or "Execution" in technique_hints:
        sources.add("Process")
        sources.add("Script")
    if "phishing" in terms:
        sources.add("Application Log")
    return sorted(sources)


def _coverage_gaps(required_sources: list[str], available_sources: list[str]) -> list[str]:
    available = {source.lower() for source in available_sources}
    return [source for source in required_sources if source.lower() not in available]


def _similar_entities(matches: list[HuntMatch]) -> dict[str, list[str]]:
    actors: set[str] = set()
    targets: set[str] = set()
    source_ips: set[str] = set()
    destination_ips: set[str] = set()

    for match in matches:
        event = match["event"]
        _add_if_present(actors, event.get("actor"))
        _add_if_present(targets, event.get("target"))
        _add_if_present(source_ips, event.get("source_ip"))
        _add_if_present(destination_ips, event.get("destination_ip"))

    return {
        "actors": sorted(actors),
        "targets": sorted(targets),
        "source_ips": sorted(source_ips),
        "destination_ips": sorted(destination_ips),
    }


def _confidence_score(matches: list[HuntMatch], coverage_gaps: list[str]) -> float:
    if not matches:
        return 0.2
    score = 0.45 + min(len(matches), 5) * 0.08
    if not coverage_gaps:
        score += 0.15
    return round(min(score, 0.9), 2)


def _hunt_review_reasons(
    matches: list[HuntMatch],
    coverage_gaps: list[str],
    query_terms: list[str],
) -> list[str]:
    reasons: list[str] = []
    if not query_terms:
        reasons.append("missing_query_terms")
    if coverage_gaps:
        reasons.append("missing_required_telemetry")
    if not matches:
        reasons.append("no_matching_activity")
    return reasons


def _event_text(event: HuntEvent) -> str:
    return " ".join(
        [
            event.get("event_type", ""),
            event.get("actor", ""),
            event.get("target", ""),
            event.get("source_ip", ""),
            event.get("destination_ip", ""),
            event.get("summary", ""),
            event.get("mitre_technique", ""),
        ]
    ).lower()


def _normalize_term(value: str) -> str:
    return value.strip().lower()


def _add_if_present(values: set[str], value: str | None) -> None:
    if value:
        values.add(value)
