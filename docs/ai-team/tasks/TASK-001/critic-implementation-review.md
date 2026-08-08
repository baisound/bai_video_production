# TASK-001 — Independent Critic Implementation Review

## Final verdict

`PASS`

Blocking findings after Builder response: `0`

## Review scope

- Product State Machine / recovery
- integrity/checksum contracts
- Logical URI / Path boundary
- Profile and Manifest immutability
- SQLite idempotency and concurrency
- Evidence/checkpoint historical integrity
- JSON Schema enforcement
- external reference-code intake boundary
- BAI Development OS / Product runtime separation

## Findings and resolution

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| I-001 | HIGH | Path Resolver accepted a syntactically valid URI whose first segment was not a Product Job ID. | Require valid Job ID as root segment. |
| I-002 | HIGH | Asset checksum accepted non-canonical digest text. | Require exact lowercase SHA-256 format. |
| I-003 | HIGH | Frozen Profile Snapshot still exposed a mutable config dict. | Persist canonical JSON internally and return defensive copies. |
| I-004 | CRITICAL | Generic transition API could be interpreted as a direct `RESUMING` path. | Reject direct `RESUMING`; only `resume_from_checkpoint()` is authorized. |
| I-005 | MEDIUM | JSON Schema `format` keywords were not checked. | Use `FormatChecker`. |
| I-006 | HIGH | Any SQLite integrity error could be mistaken for an idempotent duplicate. | Return existing operation only when the `(job_id,idempotency_key)` row actually exists; otherwise re-raise. |
| I-007 | CRITICAL | Separate side→RESUMING and RESUMING→target transactions created a crash-stranding window. | Make resume persistence atomic; consume two state revisions without durable intermediate `RESUMING`. |
| I-008 | CRITICAL | Manifest payload could mutate after checksum calculation. | Store canonical payload/extensions privately and return defensive copies. |
| I-009 | CRITICAL | A caller could provide checkpoint/current Profile IDs not bound to the Job. | Bind Profile Snapshot ID into Job state snapshot and verify both checkpoint and current context against DB-bound Profile. |
| I-010 | HIGH | Asset record could claim Job A while Logical URI targeted Job B. | Enforce Logical URI Job segment equals `production_job_id`. |
| I-011 | MEDIUM | Manifest constructor relied too much on later schema validation. | Fail early for SemVer, checksum, idempotency length and raw source paths. |
| I-012 | MEDIUM | Reference scanner did not initially detect macOS `/Users/...` path leakage. | Expand static personal-path detection and regression-test original archive. |

## Residual risks

No blocking product-foundation risk remains within TASK-001 scope. The following are intentionally unproven until later integration tasks:

- Windows execution-host canonical path/symlink validation
- actual DaVinci Resolve API capability and failure behavior
- cross-filesystem ingest durability
- provider/network side-effect controls
- production-scale SQLite/PostgreSQL performance and migration

These are not represented as PASS for future tasks.
