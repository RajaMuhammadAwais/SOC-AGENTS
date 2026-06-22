# Initial Knowledge Base Loading

Date: 2026-06-11

## Seed Corpus

The backend includes an initial source-attributed JSONL corpus at:

`backend/app/rag/corpus/initial_knowledge_base.jsonl`

It contains starter records for:

- NVD CVE API ingestion
- MITRE ATT&CK STIX/TAXII ingestion
- NIST CSF 2.0
- Internal failed-login triage playbook

## Loader

`load_initial_knowledge_base` reads the corpus, chunks each document, embeds chunks through the configured embedding provider, converts them to Pinecone-compatible vectors, and upserts them through a vector sink.

The loader keeps the implementation deliberately small:

- JSONL input with required `source_id`, `title`, `text`, and `metadata`
- Existing chunking pipeline
- Existing embedding provider contract
- Existing Pinecone vector shape
- Tenant namespace isolation

## Verified Sources

- NVD CVE API 2.0 docs: https://nvd.nist.gov/developers/vulnerabilities
- MITRE ATT&CK data and tools: https://attack.mitre.org/resources/attack-data-and-tools/
- NIST CSF 2.0 resource center: https://www.nist.gov/cyberframework
