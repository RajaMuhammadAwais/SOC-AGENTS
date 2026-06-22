import ipaddress
import re
from hashlib import sha256
from typing import TypedDict


class ThreatIntelState(TypedDict, total=False):
    observable_type: str
    observable_value: str
    normalized_type: str
    normalized_value: str
    value_hash: str
    reputation: str
    confidence: float
    source_url: str
    mitre_tactic: str
    mitre_technique: str
    enrichment_tasks: list[str]
    rationale: str
    next_action: str


CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
DOMAIN_PATTERN = re.compile(r"^(?=.{1,253}$)(?!-)[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)
HEX_PATTERN = re.compile(r"^[a-f0-9]+$", re.IGNORECASE)


def enrich_observable(state: ThreatIntelState) -> ThreatIntelState:
    normalized_type = normalize_observable_type(
        state.get("observable_type", ""),
        state.get("observable_value", ""),
    )
    normalized_value = normalize_observable_value(
        normalized_type,
        state.get("observable_value", ""),
    )
    reputation, confidence, rationale = assess_reputation(normalized_type, normalized_value)
    mitre = map_mitre(normalized_type)
    enrichment_tasks = build_enrichment_tasks(normalized_type, reputation)
    return {
        "normalized_type": normalized_type,
        "normalized_value": normalized_value,
        "value_hash": sha256(normalized_value.encode()).hexdigest(),
        "reputation": reputation,
        "confidence": confidence,
        "source_url": build_source_url(normalized_type, normalized_value),
        "mitre_tactic": mitre["tactic"],
        "mitre_technique": mitre["technique"],
        "enrichment_tasks": enrichment_tasks,
        "rationale": rationale,
        "next_action": choose_threat_intel_next_action(
            normalized_type,
            reputation,
            confidence,
            enrichment_tasks,
        ),
    }


def normalize_observable_type(observable_type: str, value: str) -> str:
    candidate = observable_type.strip().lower().replace("-", "_")
    if candidate in {"ip", "ipv4", "ipv6", "domain", "url", "hash", "cve"}:
        if candidate in {"ipv4", "ipv6"}:
            return "ip"
        return candidate
    stripped = value.strip()
    if CVE_PATTERN.match(stripped):
        return "cve"
    if _is_ip(stripped):
        return "ip"
    if _is_hash(stripped):
        return "hash"
    if DOMAIN_PATTERN.match(stripped):
        return "domain"
    return "unknown"


def normalize_observable_value(observable_type: str, value: str) -> str:
    stripped = value.strip()
    if observable_type in {"domain", "cve", "hash"}:
        return stripped.lower() if observable_type != "cve" else stripped.upper()
    return stripped


def assess_reputation(observable_type: str, value: str) -> tuple[str, float, str]:
    if observable_type == "ip":
        try:
            ip_address = ipaddress.ip_address(value)
        except ValueError:
            return "unknown", 0.2, "IP observable could not be parsed."
        if ip_address.is_private or ip_address.is_loopback:
            return "internal", 0.8, "IP address is private or loopback; treat as internal context."
        return "unknown", 0.4, "Public IP requires external reputation provider confirmation."
    if observable_type == "cve":
        return "known_vulnerability", 0.7, "CVE format is valid; enrich with NVD CVE API details."
    if observable_type == "hash":
        return "unknown", 0.4, "File hash requires malware reputation provider confirmation."
    if observable_type in {"domain", "url"}:
        return "unknown", 0.4, "Domain or URL requires reputation and passive DNS confirmation."
    return "unknown", 0.2, "Observable type is not recognized."


def map_mitre(observable_type: str) -> dict[str, str]:
    if observable_type == "cve":
        return {"tactic": "Initial Access", "technique": "T1190 Exploit Public-Facing Application"}
    if observable_type in {"domain", "ip", "url"}:
        return {"tactic": "Command and Control", "technique": "T1071 Application Layer Protocol"}
    if observable_type == "hash":
        return {"tactic": "Execution", "technique": "T1204 User Execution"}
    return {"tactic": "Unknown", "technique": "Unknown"}


def build_source_url(observable_type: str, value: str) -> str:
    if observable_type == "cve":
        return f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveIds={value}"
    if observable_type in {"domain", "ip", "url", "hash"}:
        return "provider://configure-reputation-source"
    return ""


def build_enrichment_tasks(observable_type: str, reputation: str) -> list[str]:
    if observable_type == "unknown":
        return ["validate_observable_format"]
    if observable_type == "ip" and reputation == "internal":
        return ["resolve_asset_owner", "correlate_internal_network_activity"]
    if observable_type == "cve":
        return ["retrieve_cvss_and_cwe", "map_affected_assets", "check_exploit_availability"]
    if observable_type in {"domain", "url"}:
        return ["query_domain_reputation", "check_passive_dns", "search_proxy_logs"]
    if observable_type == "hash":
        return ["query_malware_reputation", "search_edr_file_events"]
    return ["query_reputation_provider"]


def choose_threat_intel_next_action(
    observable_type: str,
    reputation: str,
    confidence: float,
    enrichment_tasks: list[str],
) -> str:
    if observable_type == "unknown" or confidence < 0.3:
        return "request_valid_observable"
    if reputation == "internal":
        return "correlate_internal_asset_activity"
    if observable_type == "cve":
        return "assess_asset_exposure"
    if enrichment_tasks:
        return "run_external_enrichment"
    return "attach_enrichment_to_case"


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _is_hash(value: str) -> bool:
    return len(value) in {32, 40, 64} and bool(HEX_PATTERN.match(value))
