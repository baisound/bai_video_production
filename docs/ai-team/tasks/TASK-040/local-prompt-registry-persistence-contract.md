# TASK-040 — Local Prompt Registry Persistence Contract Ver.1.0

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`
- Provider execution: not started by this persistence layer

The Prompt Registry can now persist Prompt Version and Generation Attempt metadata durably while keeping Prompt body and Credential values outside the general snapshot.

Persisted:

- Prompt identity/version;
- purpose/Scene/Slot;
- body SHA/ref only;
- Provider Profile identity/version;
- input Asset hashes;
- Keep Conditions;
- Generation Attempt lineage;
- strategy/result/failure codes;
- output Candidate identity;
- cost/latency metadata when supplied.

Never granted by snapshot:

- Provider execution authorization;
- paid execution authorization;
- Credential value;
- Prompt body embedding.

Parent Attempt graph is revalidated during load and missing/cyclic parent graphs fail closed.

Implementation: `prompt_registry_store.py`.
