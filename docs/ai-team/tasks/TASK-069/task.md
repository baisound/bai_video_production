# TASK-069 — Montage Learning Production Safety Correction

## Authority and boundary

Owner-assigned follow-on Task.  TASK-068 is the canonical dependency: PR #523
merged at `dca284877dca32c537f04625d046601a5fae964c`.  This Task does not reopen
TASK-058 history and makes no Release, Deploy, Production, native, provider, or
external-account effect.

Development depth is DEV-4.  Completion requires independent Critic, Tester,
and Judge review with Critical/High findings resolved or formally gated.

## Allowed files

- `src/ai_video_production/montage_learning_file_bridge.py`
- `src/ai_video_production/montage_learning_bridge_contracts.py`
- `src/ai_video_production/montage_learning_connector_readiness.py`
- `src/ai_video_production/schema_resources/montage-learning-file-bridge.schema.json`
- `src/ai_video_production/schema_resources/montage-learning-connector-readiness.schema.json`
- `tests/test_task058_montage_learning_file_bridge.py`
- `tests/test_task058_montage_learning_bridge_contracts.py`
- `tests/test_task058_montage_learning_adapter_e2e.py`
- `tests/test_task069_montage_learning_production_safety.py`
- `docs/ai-team/tasks/TASK-069/**`

Do not modify the TASK-067 admission transaction, TASK-060/061/063 modules,
`atomic.py`, shared task/current-state/roadmap/CHANGELOG documents, SKILL
repositories, or any release/install/production surface.

## Atomic Unit FB-R1

Replace bounded owner, import-journal, receipt, pending, and correlation reads
with a root-bound `SecureAuthorityIO.read_json` adapter.  The adapter must use
a Bridge-layout relative path, preserve only exact built-in JSON values in a
detached snapshot, bind public receipt and pending byte comparisons to the
receipt hash, and map authority errors to a body-free Bridge error.  It has no
external effect.  The Bridge's existing 4 MiB delivery and Profile contracts
exceed TASK-068's public 1 MiB ceiling, so those routes remain separately gated
dependencies rather than being silently narrowed or routed through a private
API.  This Unit does not alter publication, cleanup, CAS, or Profile behavior.

Acceptance: read paths cannot consume a stat/open or same-bytes/different-inode
swap; links, non-regular files, duplicate JSON keys, NaN, BOM, trailing data,
depth/node/byte overflow fail closed; public Bridge errors contain no path or
body.  Publication, cleanup, CAS, profile transaction, privacy, and readiness
work remain later Task-069 units.
