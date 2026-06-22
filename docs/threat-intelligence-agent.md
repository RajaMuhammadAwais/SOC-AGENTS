# Threat Intelligence Agent

Date: 2026-06-11

## Scope

The threat intelligence agent performs safe first-pass enrichment:

- Normalize observable type and value.
- Generate stable value hashes.
- Build authoritative source lookup URLs for CVEs.
- Assign conservative reputation when no external reputation provider has been queried.
- Add MITRE mapping hints by observable type.

## Implementation

The implementation intentionally avoids claiming live reputation results without a configured provider. It marks public IPs, domains, URLs, and file hashes as `unknown` and points them to a configurable reputation source. CVEs are linked to the official NVD CVE API.

## Verified Sources

- NVD CVE API 2.0 docs: https://nvd.nist.gov/developers/vulnerabilities
- MITRE ATT&CK Data & Tools: https://attack.mitre.org/resources/attack-data-and-tools/
