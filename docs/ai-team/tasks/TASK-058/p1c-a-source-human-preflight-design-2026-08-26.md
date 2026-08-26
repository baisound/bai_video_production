# TASK-058 P1C-A — Source and Human-binding Preflight Detailed Design

Date: 2026-08-26
Profile: DEV-4 FOUNDATION CRITICAL
Execution class: NO_MUTABLE_OR_EXTERNAL_I/O; PACKAGED_IMMUTABLE_SCHEMA_READ_ALLOWED
Base: 563c72be100fb2b7c5bd786693a499d537314cd0

## Decision

P1C is split at the last safe validation boundary. P1C-A revalidates one exact
BVP delivery and cross-checks it against one caller-supplied P1B entry-shaped
candidate. It does not prove ledger membership or store origin and does not
implement the monotonic Project anchor, handle-bound canonical writer, promotion transaction,
recovery journal, duplicate receipt lineage, or public receipt issuer.

This split closes P1B's source/Human-origin gap without pretending that a pure
object creates filesystem or canonical authority.

## Inputs and snapshot boundary

Inputs are caller-supplied JSON-like mappings: one P0
`BvpMontageExactEvidenceDelivery/v1` envelope and one serialized
`MontageLearningAdmissionEntry/v1` from P1B. Both mappings are recursively copied
exactly once using only exact built-in `dict`, `list`, `str`, `bool`, `int`, and
`None` values before semantic access. Subclasses are rejected without invoking their
hooks. Unknown versions, unknown fields, non-JSON values, Generic profile input,
and malformed staging fail closed.

## Exact source revalidation

P1C-A calls P0 `validate_exact_evidence_delivery` with the exact expected
Owner-scope hash. This reruns TASK-055 proposal, approved-plan, and Human Edit
Evidence admission and verifies their hashes, frame relationships, false
authority/effect flags, privacy boundary, and exact lineage. Only
`EXACT_LINEAGE_VERIFIED` is accepted. Generic SKILL observation remains
review-only and cannot be relabelled into this lane.

## Human binding

`canonical_evidence_sha256` is the revalidated TASK-055 `evidence_sha256`.
The stable ID is `task055-evidence-<64 lowercase evidence digest hex>`.

The Human binding digest domain is
`TASK058_MONTAGE_LEARNING_HUMAN_BINDING_V1 || NUL`. Its canonical JSON contains
exactly source contract profile, project ID, source record ID, Owner-scope hash,
proposal SHA-256, approved-plan SHA-256, and Human Edit Evidence SHA-256.

`do_not_learn=true` is terminal. A valid `DELETED` disposition with
`do_not_learn=false` is retained as negative feedback rather than erased or
generalized.

## Staging binding

The P1B parser first verifies entry self-hash, exact false authority flags,
idempotency derivation, timestamp, and shape. This is structural validation only:
a caller can construct the same typed entry, so ledger membership and store origin
remain false until a later handle-bound durable readback. P1C-A then requires exact equality
for project ID, source record ID, source SHA-256, Owner scope, idempotency key,
canonical Evidence ID, canonical Evidence SHA-256, and Human binding SHA-256. It
exposes the revalidated proposal `project_id` for the later Project anchor, binds
that project ID explicitly into the Human binding, and also binds
the verified P1B `entry_sha256`. A mismatch is never repaired.

## Output and authority

The strict body-free result is self-hashed under
`TASK058_MONTAGE_LEARNING_CANONICAL_PREFLIGHT_V1 || NUL`. Its only serialized state
is `NONAUTHORITATIVE_SOURCE_HUMAN_PREFLIGHT_PROJECTION`. The constructor and
parser prove projection self-consistency only: compiler execution, source/Human
origin, staging-entry origin, staging membership, and store origin are all false.
It fixes monotonic Project anchor, rollback
detection, canonical store write/commit, receipt mint, canonical admission,
automatic promotion, Timeline, Resolve, and external-effect flags to false.
The preflight digest is not a canonical store commit.

## Consumer and SKILL boundary

BAI VIDEO PRODUCTION remains the contract and future store owner. The
`bvp-montage-learning-adapter` does not own BVP's timeline, staging ledger,
monotonic anchor, promotion writer, or receipt authority. Runtime status is not
upgraded and no connector folder, watcher, queue, UI, application, network, or
provider is touched.

## Failure modes

- custom JSON subclass, malformed/unstable JSON snapshot: reject without hooks;
- P0/TASK-055 candidate state tuple drift: reject;
- P0/TASK-055 lineage, hash, privacy, or Owner-scope failure: reject;
- Generic or mixed profile: reject;
- do-not-learn: reject;
- invalid/tampered P1B entry: reject;
- any seven-coordinate mismatch: reject;
- preflight tamper, unknown field, or impossible authority flag: reject.

All failures occur in memory and create no partial result or side effect.

## Exact scope

1. `docs/ai-team/tasks/TASK-058/task.md`
2. this design
3. `schemas/montage-learning-canonical-preflight.schema.json`
4. packaged byte-identical Schema mirror
5. `src/ai_video_production/montage_learning_canonical_preflight.py`
6. `tests/test_task058_montage_learning_canonical_preflight.py`

Prohibited: CHANGELOG, Active Work Locks, current state, task index, TASK-029,
P0/P1A/P1B implementation/schema/tests, Product Project files, canonical store,
receipt, Timeline, Resolve, native/provider/network/database, Release, Deploy,
and Production effects.

## Acceptance

- Schema mirror and Draft 2020-12 validation pass;
- deterministic domains, constructor self-consistency, nonauthoritative origin flags, and round-trip parser pass;
- positive, do-not-learn, deleted-negative, Generic, tamper, privacy,
  Owner-scope, and all-coordinate fixtures pass;
- no mutable/external read and no filesystem/network/native/store-write effect;
- P0/P1A/P1B and TASK-055 related regression passes;
- exact6 scope and diff check pass;
- independent Critic, Tester, and Final Judge have no unresolved Critical/High.

## Future P1C-B gate

P1C-B must not admit this serialized projection or `from_dict()` result alone.
It must recompile the raw exact delivery together with a handle-bound durable
staging readback, compare every projection coordinate, then verify ledger membership
and store origin before designing the monotonic Project anchor, rollback model,
canonical promotion/recovery, duplicate lineage, or receipt issuer. P1C-A neither
authorizes nor partially implements those effects.
