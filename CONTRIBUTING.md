# Contributing to SOC-AGENTS

Thank you for considering a contribution. This project ships security-critical code, so contributions follow a slightly heavier process than a typical open-source project. The extra friction exists to keep detections auditable, autonomy governed, and tenant isolation airtight.

## Ground rules

Three architectural invariants are non-negotiable and every pull request is judged against them. First, **evidence-based detection**: new detections must be expressible as Sigma rules (or pipeline stages) that an analyst can read and contest; do not introduce opaque ML detectors into the alert path. Second, **auditable autonomy**: agents may never self-assign permissions; new skills must declare a risk class and execution policy, and policy evaluation must remain deterministic code. Third, **tenant isolation**: every new query path must be tenant-scoped; there is no legitimate unscoped read.

## Development workflow

1. Fork the repository and create a feature branch from `main`.
2. Set up the local environment per [`README.md`](README.md) — migration and seed scripts are idempotent, so feel free to re-run them.
3. Write tests alongside code. Backend changes need unit tests (`backend/tests/`); changes touching pipeline stages or policy logic additionally need an integration test (`@pytest.mark.integration`).
4. Run the full local gate before pushing: `ruff check .`, `mypy app scripts --ignore-missing-imports`, and `pytest -m "not integration and not slow"`.
5. Open a pull request against `main` and describe the change, the invariants it touches, and the test evidence.

## What makes a good PR

Small, focused diffs with tests and documentation. New detection rules go through `seed_detection_rules.py` conventions and MITRE ATT&CK metadata. New agents register through the supervisor and ship a skill entry in the autonomy registry. Frontend changes use the shared shadcn/ui component set and the existing API client.

## Code of conduct

Be rigorous but kind. Security debates get heated; keep them technical. Threat models and failure modes are always fair game, tone policing is not.

## License

Contributions are licensed under the project's Apache-2.0 license.
