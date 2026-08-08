# TASK-001 — Implementation Report

## Result

`IMPLEMENTED`

TASK-001 implemented only the authorized Product Foundation / Domain Model. BAI Development OS Core, OS-internal TASK-016, media-processing engines, NLE operations and external side effects were not modified or introduced.

## Implemented modules

| Module | Contract implemented |
|---|---|
| `ids.py` | ULID-shaped product IDs, project/schema ID validation |
| `serialization.py` | canonical JSON, SHA-256, UTC timestamp and checksum validation |
| `errors.py` | Product Error Envelope and error categories |
| `manifest.py` | immutable Canonical Manifest Envelope, payload checksum binding, raw-path/secret guards |
| `schema_contracts.py` | Draft 2020-12 validation, format checking, SemVer compatibility helpers |
| `assets.py` | Asset Registry minimum record, exact checksum, rights gate, same-Job Logical URI scope |
| `paths.py` | allowlisted `asset://` / `job://` resolution, traversal and symlink escape defense, WSL/Windows ownership split |
| `atomic.py` | target-local temp write, fsync, validation, checksum, atomic replace and rollback-on-failure |
| `profile.py` | immutable checksum-bound Profile Snapshot, guarded overrides and Product Plugin capability boundary |
| `ownership.py` | automation/human/shared Timeline ownership and optimistic revision guard |
| `checkpoint.py` | immutable checkpoint hash map and exact resume compatibility contract |
| `evidence.py` | append-only JSONL Product Evidence with secret masking and forward supersession link |
| `state.py` | Product Job State Machine, expected-version mutation, checkpoint-only resume API |
| `store.py` | SQLite WAL foundation tables, state persistence, atomic resume bridge, asset/checkpoint persistence and operation idempotency |
| `external_skill.py` | SHA-256 + static reference archive inspection; no execution or source adoption |

## Schemas

Created schemas for:

- Canonical Manifest Envelope
- Asset Record
- Error Envelope
- Checkpoint
- Profile Snapshot
- Evidence Record

Checksums are canonical `sha256:<64 lowercase hex>` where integrity hashes are required.

## Implementation Critic corrections incorporated

The implementation review found and corrected several foundation-level defects before closure:

1. Logical URI root segment was not initially required to be a valid Production Job ID.
2. Asset checksum validation was initially too permissive.
3. Profile Snapshot exposed a mutable nested config despite a frozen dataclass.
4. Generic state transition initially allowed a possible `RESUMING` bypass.
5. JSON Schema date-time formats were not initially checked by `FormatChecker`.
6. Generic SQLite `IntegrityError` handling could misclassify a foreign-key failure as an idempotent duplicate.
7. Two-transaction resume could strand a job in durable `RESUMING` after a crash.
8. Manifest payload could be mutated after checksum creation, creating checksum/content drift.
9. Resume caller could initially substitute a different Profile Snapshot unless the Job-bound Profile was checked.
10. Asset Logical URI could initially point at another valid Job ID.
11. Manifest constructor did not initially fail early on invalid SemVer/checksum/raw source references.
12. Original external reference archive path scanner initially missed `/Users/...` personal-path syntax.

All listed findings were fixed and regression tests were added where applicable.

## Deliberately deferred

- FFmpeg / VFR-CFR normalization
- scene/VAD/ASR/WhisperX processing
- Candidate Clip Graph
- DaVinci Resolve API and Capability Matrix
- Premiere XML generation
- AI media / TTS generation
- Product UI and publishing
- real Windows-host path/symlink validation evidence
- cross-filesystem asset ingest fallback
- PostgreSQL adapter

These require later Consumer TASK authorization.
