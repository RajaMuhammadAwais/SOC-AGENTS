# Alert Triage Agent

Date: 2026-06-11

## Scope

The alert triage agent performs the first SOC decision layer:

- Deduplicate related alerts with a stable source/context fingerprint.
- Categorize common alert classes from alert context.
- Prioritize with severity, risk score, MITRE context, and duplicate status.
- Choose the next action: monitor, queue for review, attach to existing case, or open investigation.

## Implementation

The backend uses LangGraph `StateGraph` with small idempotent nodes:

1. `deduplicate_alert`
2. `classify_alert`
3. `prioritize_alert`
4. `choose_next_action`

The graph is compiled through `compile_triage_graph` before execution. Deterministic logic provides a reliable baseline, while the existing LLM preview helper can generate analyst-facing rationale when configured.

## Sources

- LangGraph Graph API docs: https://docs.langchain.com/oss/python/langgraph/graph-api
- NIST incident-response guidance and NVD/NIST source practices: https://csrc.nist.gov

