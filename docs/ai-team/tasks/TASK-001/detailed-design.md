# TASK-001 — Detailed Design / Project Foundation & Domain Model

## 1. Authority and profile

- Consumer Project: `ai-video-production`
- Product design baseline: `AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`
- BAI Development OS: package `1.0.0`, Architecture `Ver.2.27 CURRENT_CANONICAL`
- Revalidated profile: `DEV-4 FOUNDATION CRITICAL`
- Reason: current Adaptive Governance resolves the declared `PROJECT / LARGE / CORE / HIGH / NEW_ARCHITECTURE / ARCHITECTURE` change to DEV-4; state-machine and security-boundary flags reinforce the safety floor.
- DistributedOS: disabled.
- BAI OS runtime dependency: **not introduced**. TASK-001 remains Level A — Governance Only.

## 2. Scope boundary

TASK-001 implements only reusable product-domain foundation contracts. It does not implement media conversion, ASR, candidate selection, NLE automation, external AI generation, publishing, UI, or BAI Development OS Core.

The repository owns product source, tests, schemas, profiles, project Evidence and Git history. BAI Development OS remains an external development-governance foundation.

## 3. Identifier contract

Generated product identities use `<PREFIX>-<26 character Crockford Base32 ULID>` with a 48-bit millisecond time component and 80 bits of cryptographic randomness. IDs are immutable after issuance and globally unique for this product domain.

| Identity | Prefix | Generation owner | Scope |
|---|---|---|---|
| Production Job | `JOB` | Job Service | product-global |
| Asset | `ASSET` | Asset Service | product-global |
| Segment | `SEG` | segmentation owner | product-global |
| Candidate | `CAND` | Candidate Engine | product-global |
| Manifest | `MAN` | producing service | product-global |
| Operation | `OP` | command/operation store | product-global |
| Evidence | `EVD` | Evidence Writer | product-global |
| Checkpoint | `CHK` | stage owner | product-global |
| Profile Snapshot | `PSN` | profile service | product-global |

`project_id` is a stable lowercase slug. `schema_id` is a stable dotted/hyphenated lowercase identifier and is not regenerated during migration. Schema version uses SemVer.

## 4. Production Job State Machine

Only `JobStateService` may request state mutation. The SQLite store exposes the actual mutation primitive as an internal method and enforces expected state + `state_version` in one conditional update.

Happy path:

`CREATED → INGESTING → NORMALIZING → ANALYZING → CANDIDATES_READY → PLAN_REVIEW → PLAN_APPROVED → ASSET_PREPARING → RESOLVE_ASSEMBLING → AUTO_QA → READY_FOR_MANUAL_EDIT → MANUAL_EDITING → READY_FOR_RENDER → RENDERING → RENDER_QA → COMPLETED`

Side states are explicit. Non-terminal active states can fail, pause or cancel. Resource-heavy stages can enter `WAITING_RESOURCE`; human-gated stages can enter `WAITING_HUMAN`. `PAUSED / WAITING_* / FAILED` retain `resume_to_state`. After checkpoint compatibility is proven, `RESUMING` is treated as a logical bridge back to the stored target. Persistence commits the bridge atomically and consumes two state revisions, so a process crash cannot leave a durable job stranded in `RESUMING`. `COMPLETED` and `CANCELLED` are terminal and cannot reopen.

This refines the Ver.0.6 phrase that resume can occur from arbitrary states: direct arbitrary transition to `RESUMING` is rejected; interruption is first represented as an explicit side state so recovery evidence is preserved.

## 5. Canonical Manifest Envelope

Every manifest uses:

- `schema_id`, `schema_version`
- `manifest_id`, `production_job_id`, `revision`
- `created_at`, `producer`
- `profile_snapshot_id`
- `source_refs`, `input_checksums`
- `content_checksum` over canonicalized payload JSON; payload is snapshotted immutably at envelope creation so later caller mutation cannot change canonical content without a new Manifest revision
- optional `operation_id`, `idempotency_key`
- `payload`
- `extensions`

Secret-like keys and environment-dependent raw paths are rejected from canonical payloads. Logical URIs are used instead. Envelope top-level shape is stable; future optional extension data goes under `extensions` or payload schemas.

## 6. Schema compatibility

- PATCH: documentation/constraint clarification with unchanged data shape.
- MINOR: backward-readable optional additions within payload/extension contracts.
- MAJOR: required-field or semantic break; explicit migration/adapter required.
- Manifest regeneration increments `revision`; prior revisions are never overwritten as historical evidence.

## 7. Asset Registry

Minimum Asset contract includes ID, job, type, Logical URI, SHA-256 checksum, rights status, owner, retention class, human lock, generation provenance and Evidence references.

`UNKNOWN`, `BLOCKED`, or human-locked assets are never automatically eligible. Every Asset Logical URI must be scoped to the same `production_job_id`; cross-Job URI substitution is rejected. Rights/consent enforcement in later execution tasks must fail closed.

## 8. Logical URI / Path Resolver

Only `asset://` and `job://` prefixes are initially allowlisted. Relative components containing empty segments, `.`, `..`, backslashes, drive prefixes, UNC syntax or NUL are rejected. On the execution host, the candidate path is canonicalized and must remain under its configured root after symlink resolution.

Windows translation is lexical only from WSL. The Windows execution owner must independently revalidate canonical path and symlink boundaries before I/O. This preserves execution-location ownership and prevents WSL from claiming Windows filesystem evidence it cannot observe.

## 9. Integrity and Atomic Write

Canonical JSON is serialized deterministically, written to a temp file in the target directory, flushed/fsynced, parsed and schema-validated, checksummed, then promoted with `os.replace`. Directory fsync is attempted. Failures before replace remove temp output and do not alter the existing canonical file.

Cross-filesystem asset ingestion is intentionally not implemented in TASK-001. Future Asset Ingest must use staged copy + checksum + target-local atomic promotion.

## 10. Product Error Envelope

Errors are product-domain records and never represent BAI Development authorization. Envelope fields include code, category, message, retryability, optional operation/evidence IDs and details. Categories cover validation, authorization, support, transient/resource/timeout/external dependency, integrity, human review, internal, state and security.

## 11. Evidence and Checkpoint

Product runtime Evidence is append-only JSONL. Common secret-like fields are masked. A correction appends a new record referencing the superseded Evidence rather than rewriting old Evidence.

Checkpoint compatibility requires canonical SHA-256 input/output/Manifest hashes plus exact match of input hash, immutable Profile Snapshot ID and prior Manifest hash map. The checkpoint/current Profile Snapshot must also equal the Profile Snapshot durably bound to the Production Job in SQLite; caller-supplied substitution is rejected. Mismatch blocks resume.

## 12. Ownership and conflict protection

- `AUTO_ASSEMBLY`: automation-owned.
- `EDITOR_WORK` and `FINAL_MASTER`: human-owned.
- explicitly named staging surfaces may be shared.

Automation cannot mutate human-owned timelines. Human editors do not mutate the automation canonical assembly; they edit a human-owned derivative. Every write checks expected revision and fails closed on conflict.

## 13. Profile Snapshot and Product Plugin boundary

Profile Snapshot is immutable and checksum-bound. Job override cannot modify rights, timeline ownership/write policy, legal hold, voice consent or allowed roots.

Product Plugin descriptors declare capabilities and I/O contracts. Capabilities that mutate Job State, Core DB Schema or NLE directly are rejected. BAI ExtensionOS is not embedded into the product runtime by TASK-001.

## 14. Persistence

MVP persistence is SQLite WAL with foreign keys and schema migration record. TASK-001 creates the canonical foundation tables named by Ver.0.6: production jobs, assets, asset versions, manifests, operations, checkpoints, approvals, evidence, cost ledger, profiles and decisions.

Idempotency is enforced by a unique `(job_id, idempotency_key)` constraint for operations. A duplicate request returns the existing Operation ID rather than creating a duplicate effect.

## 15. External Skill intake

Premiere auto-edit archives remain under `references/` only. TASK-001 records Owner-declared license status and provides checksum/static-inspection support. Reference code is not moved into product `src/` in this TASK.

## 16. Level A/B decision

**Decision: remain Level A — Governance Only.** The product foundation has no runtime need for BAI LifecycleStore or other OS APIs. Adding a runtime-assisted dependency now would couple the product to development tooling without a product benefit. A later project TASK may adopt Level B for development automation if concrete lifecycle/tooling value appears.

## 17. Test design

DEV-4 tests cover unit, boundary/negative, integration, regression, contract, fault/recovery and a consumer-style golden fixture. Required high-risk cases include illegal/stale state transitions, path traversal and symlink escape, atomic-write injected failure, schema compatibility, ownership conflict, idempotency duplicate, secret/path manifest rejection, Error serialization and checkpoint mismatch.

## 18. Failure modes

See `failure-mode-design.md`. No test may weaken security or state-machine boundaries merely to obtain PASS.
