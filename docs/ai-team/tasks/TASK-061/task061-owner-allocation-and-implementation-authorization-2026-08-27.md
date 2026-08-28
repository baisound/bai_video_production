# TASK-061 Owner Allocation and Implementation Authorization Boundary

## Decision and coordinates

- Task: `TASK-061`
- Capability: `BVP-MONTAGE-CONNECTOR-ACTIVATION-001`
- State: `DEPENDENCY_BLOCKED / IMPLEMENTATION_NOT_AUTHORIZED`
- Profile: `DEV_4_FOUNDATION_CRITICAL`; maximum review/fix cycles: `2`
- Design commit: `0ac8971174ab227a6f62b8b797307bbc31b70145`
- Design SHA-256: `sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`
- BVP base: `e78699bc14f23abce995a46a9b059f826f9c2ef1`; Registry: `128`
- Reservation: `BVP-INTEGRATION-LOCK-TASK060-TASK062-AUTHORIZATION-METADATA-20260827`
- Target branch: `codex/task-060-task062-authorization-metadata`
- Preflight collision/overlap: `0/0`

This candidate defines a future boundary only. It does not authorize current
TASK-058 changes, production bridge mutation, or connector activation.

Current metadata effect is exactly: task-index `0`, Registry `0`, source `0`,
schema `0`, test `0`, connector activation `0`, runtime/native/paid/external
execution `0`, and Release/Deploy/Production `0`.

## Dependency and Atomic Units

Hard prerequisites: canonically released TASK-058 A/B+C, released TASK-058
readiness v2, and TASK-060 `PP-C` production source.

| Unit | Goal | Mandatory gate |
|---|---|---|
| `CA-A` | Windows bridge security attestation and migration executor | real temporary Windows DACL/migration PASS |
| `CA-B` | production migration/source binding and released TASK-058 readiness validation | fault/expiry/drift PASS |
| `CA-C` | BVP config plus explicit Human activation/deactivation transaction | real adapter E2E and rollback PASS |

Order: TASK-058 release + `PP-C -> CA-A -> CA-B -> CA-C`.

## Closed future implementation Allowed Files

```text
src/ai_video_production/montage_learning_bridge_security.py
src/ai_video_production/montage_learning_bridge_migration.py
src/ai_video_production/montage_learning_connector_activation.py
src/ai_video_production/__init__.py
schemas/montage-learning-bridge-security-attestation.schema.json
schemas/montage-learning-bridge-migration.schema.json
schemas/montage-learning-connector-activation.schema.json
src/ai_video_production/schema_resources/montage-learning-bridge-security-attestation.schema.json
src/ai_video_production/schema_resources/montage-learning-bridge-migration.schema.json
src/ai_video_production/schema_resources/montage-learning-connector-activation.schema.json
tests/test_montage_learning_bridge_security_windows.py
tests/test_montage_learning_bridge_migration.py
tests/test_montage_learning_connector_activation.py
docs/ai-team/tasks/TASK-061/task.md
docs/ai-team/tasks/TASK-061/task061-owner-allocation-and-implementation-authorization-2026-08-27.md
```

Released TASK-058 `montage_learning_connector_readiness.py`, its v2 schema and
focused tests are immutable dependencies and outside this list. A required
change routes to a separately authorized TASK-058 compatibility Unit.

## Responsibility non-overlap

- TASK-058 owns root/inbox/importer/receipts/Profile transport/readiness composition.
- TASK-060 owns the promoted advisory production source.
- TASK-055 and existing Timeline/Human Gates remain unchanged.
- The SKILL connector config remains disabled by default and is not BVP authority.
- This Task owns only security attestation, migration orchestration, BVP config,
  and explicit activation/deactivation history.

## Acceptance and validation

- real temporary-Windows-directory owner/DACL/ACE parsing;
- inherited Everyone/Users write, unknown ACE, wrong owner, symlink, junction,
  reparse, and ancestor-replacement rejection;
- missing privilege returns `BRIDGE_REPAIR_REQUIRED` without partial repair;
- all migration discovery and crash phases, preserving unknown files;
- current/stale/tampered/source-unbound Profile migration cases;
- six readiness components remain independent and do not imply PASS;
- activation Evidence 24-hour expiry and every identity invalidation;
- intake-only and full config exact bytes;
- stale, replayed, wrong-mode Human confirmation rejection;
- crash before/after config replace and before status/history;
- failed post-switch status restores and reads back exact disabled config;
- receipt requirement false under enabled config auto-deactivates;
- every production call uses explicit BVP-owned config;
- repository default remains `enabled:false`;
- forged public receipt without canonical ledger blocks readiness;
- released TASK-058 High regression remains green;
- Timeline/Resolve/automatic learning/promotion effect `0`;
- packaged Windows fixture and final full regression PASS.

Command families:

```text
python -m pytest -q -p no:cacheprovider tests/test_montage_learning_bridge_security_windows.py tests/test_montage_learning_bridge_migration.py tests/test_montage_learning_connector_activation.py
python -m pytest -q -p no:cacheprovider tests/test_task058_montage_learning_admission_store.py tests/test_task058_montage_learning_bridge_contracts.py tests/test_task058_montage_learning_canonical_preflight.py tests/test_task058_montage_learning_canonical_promotion_ledger_contract.py tests/test_task058_montage_learning_durable_staging_readback.py tests/test_task058_montage_learning_receipt_contracts.py
python -m compileall -q src tests
python -m pytest -q -p no:cacheprovider
git diff --check
```

Native Windows DACL and real adapter E2E cannot be replaced by mocks or Linux
permission tests. Future paths are run only after their Unit creates them.

## DEV-4 responsibilities

- Builder: one CA Unit and exact-head Evidence only.
- Critic: independent security, migration, readiness, and authority review.
- Tester: independent native/fault/dependency/regression execution.
- Judge: exact immutable Evidence and unresolved Critical/High `0/0` only.

## Prohibited and stop conditions

Prohibited: current TASK-058 source/test/schema changes; SKILL repository config;
TASK-055, Timeline, or Resolve code; real Owner data; provider credentials;
paid/external calls; Release/Deploy; Production activation during implementation;
automatic retry/rollback; installer expansion not separately authorized.

Stop on dependency not released, different production root, unknown user SID,
uninspectable DACL, shared-writer ACE, unsafe ancestor, unresolved migration or
TASK-058 recovery, receipt/ledger mismatch, source Profile drift, config/schema
or SKILL major drift, active lock overlap, Allowed Files expansion, or any
attempt to set the repository default to true.

## Expiry and later activation

Design/main/Registry/task/branch/PR/blob drift, dependency revocation, C/H
finding, Owner revocation, or forbidden effect expires this boundary. Later
activation must bind the exact metadata PR HEAD and six blob hashes, Hosted
checks, independent DEV-4 `0/0`, Owner Ready/merge, and canonical main read-back.
