from app.agents.threat_intelligence import (
    build_enrichment_tasks,
    build_source_url,
    choose_threat_intel_next_action,
    enrich_observable,
    map_mitre,
    normalize_observable_type,
)


def test_enrich_cve_observable_adds_nvd_source_and_mitre_mapping() -> None:
    result = enrich_observable(
        {
            "observable_type": "",
            "observable_value": "cve-2024-3094",
        }
    )

    assert result["normalized_type"] == "cve"
    assert result["normalized_value"] == "CVE-2024-3094"
    assert result["reputation"] == "known_vulnerability"
    assert result["confidence"] == 0.7
    assert result["source_url"].endswith("?cveIds=CVE-2024-3094")
    assert result["mitre_technique"] == "T1190 Exploit Public-Facing Application"
    assert result["enrichment_tasks"] == [
        "retrieve_cvss_and_cwe",
        "map_affected_assets",
        "check_exploit_availability",
    ]
    assert result["next_action"] == "assess_asset_exposure"


def test_enrich_private_ip_marks_internal_context() -> None:
    result = enrich_observable(
        {
            "observable_type": "ip",
            "observable_value": "10.0.0.5",
        }
    )

    assert result["normalized_type"] == "ip"
    assert result["reputation"] == "internal"
    assert result["confidence"] == 0.8
    assert result["mitre_tactic"] == "Command and Control"
    assert result["next_action"] == "correlate_internal_asset_activity"


def test_enrich_hash_detects_hash_and_preserves_provider_placeholder() -> None:
    result = enrich_observable(
        {
            "observable_type": "",
            "observable_value": "a" * 64,
        }
    )

    assert result["normalized_type"] == "hash"
    assert result["source_url"] == "provider://configure-reputation-source"
    assert result["mitre_technique"] == "T1204 User Execution"


def test_normalize_observable_type_detects_domain() -> None:
    assert normalize_observable_type("", "example.com") == "domain"


def test_invalid_explicit_ip_returns_unknown_reputation() -> None:
    result = enrich_observable(
        {
            "observable_type": "ip",
            "observable_value": "not-an-ip",
        }
    )

    assert result["reputation"] == "unknown"
    assert result["confidence"] == 0.2
    assert result["next_action"] == "request_valid_observable"


def test_build_source_url_only_uses_nvd_for_cves() -> None:
    assert build_source_url("cve", "CVE-2024-3094").startswith(
        "https://services.nvd.nist.gov/rest/json/cves/2.0"
    )
    assert build_source_url("unknown", "x") == ""


def test_map_mitre_unknown_fallback() -> None:
    assert map_mitre("unknown") == {"tactic": "Unknown", "technique": "Unknown"}


def test_build_enrichment_tasks_for_domain() -> None:
    assert build_enrichment_tasks("domain", "unknown") == [
        "query_domain_reputation",
        "check_passive_dns",
        "search_proxy_logs",
    ]


def test_choose_threat_intel_next_action_runs_external_enrichment() -> None:
    result = choose_threat_intel_next_action(
        "hash",
        "unknown",
        0.4,
        ["query_malware_reputation"],
    )

    assert result == "run_external_enrichment"
