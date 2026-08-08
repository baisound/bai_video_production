# TASK-001 — Final Plan

## Implementation authority scope

Implement the product-domain foundation defined by TASK-001 and `detailed-design.md` only.

## Files to create/modify

- `src/ai_video_production/**`
- `schemas/**`
- `tests/**`
- `pyproject.toml`
- TASK-001 evidence/review/completion artifacts
- `PROJECT.md`, `.bai-os/project.json`, project current-state/summary/index documents

## Protected / out-of-scope

- BAI Development OS Core and internal TASKs
- Resolve/FFmpeg/ASR/AI-provider operational code
- publishing, email, webhook or paid external API effects
- DistributedOS
- production media files

## Implementation order

1. ID and serialization primitives.
2. Error and schema contracts.
3. Manifest and Profile Snapshot safety boundaries.
4. Logical URI/Path Resolver.
5. Product State Machine + SQLite state persistence.
6. Asset Registry and operation idempotency.
7. Atomic writer, Evidence and Checkpoint recovery contracts.
8. Timeline ownership and Product Plugin boundary.
9. JSON Schemas.
10. DEV-4 unit/boundary/contract/integration/fault/recovery/consumer-fixture tests.
11. Critic implementation review, fix/retest if needed.
12. Project documentation synchronization and Git validation.

## Rollback

TASK-001 introduces no irreversible external side effect or production migration. Rollback is a Git revert of the TASK-001 implementation commit. Runtime SQLite files are ignored and are test/generated state, not shipped canonical data.

## Completion criteria

- All required DEV-4 tests pass.
- Blocking implementation Critic findings = 0.
- Product and BAI OS boundaries remain unchanged.
- Internal project docs reflect the implemented contract.
- Git diff/checks pass and repository is commit-ready.
