# Security Policy

## Supported versions

The `main` branch is the only actively supported line. Security fixes are backported to tagged releases when a release exists; until the first release, fix against `main`.

## Reporting a vulnerability

Do **not** open a public issue for a security vulnerability. Email the maintainers or open a draft advisory through GitHub's [private vulnerability reporting](https://github.com/RajaMuhammadAwais/SOC-AGENTS/security/advisories) feature, and include:

- A concise description of the vulnerability and affected component
- Concrete reproduction steps (payloads, API calls, environment details)
- The potential impact (confidentiality, integrity, availability, or autonomy-boundary violation)

You will receive an acknowledgment within 3 business days, an initial assessment within 10 business days, and coordinated disclosure once a fix ships.

## Scope of this policy

This policy covers the code in this repository and the official deployment manifests. Third-party dependencies are governed by their own upstream advisories; report dependency issues to the responsible upstream project. Demo data and test fixtures are explicitly out of scope — the demo seed account is documented as demo-only and is not a vulnerability.

## What we treat seriously

Beyond classic web vulnerabilities (injection, XSS, CSRF, broken authorization), SOC-AGENTS treats **autonomy-boundary violations** as first-class security issues: any way to make a skill execute outside its declared policy, escape a decision lane, bypass the tenant scope, or inject instructions that alter an agent's permissions is considered a critical vulnerability regardless of the technical vector.

## Secrets posture

The repository is maintained secret-free: all secrets flow through environment variables, defaults are explicit placeholders rejected in production, and a heuristic entropy scan is run before releases. If you discover a committed secret, report it through the channel above — it will be rotated and history rewritten, not patched over.
