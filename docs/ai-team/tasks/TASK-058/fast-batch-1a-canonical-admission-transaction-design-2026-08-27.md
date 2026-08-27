# TASK-058 FAST-BATCH-1A Canonical Admission Transaction Design

Status: `IMPLEMENTED_LOCAL / REVIEW_PENDING`

## Goal and authority

FAST-BATCH-1A implements the BVP-owned exact learning-admission transaction and
a separately named generic review-observation ledger. Owner approval covers
canonical writer/store, external monotonic coordinate, CAS, persistence,
recovery, durable read-back, public v2 `ACCEPTED`/`DUPLICATE` receipt minting,
and immutable generic observation intake. It does not authorize learning
adoption, Profile generation, Timeline/Resolve mutation, Release, Deploy, or
Production.

## Exact paths

The Unit changes exactly this task record, this design, one public Schema and
its byte-identical package mirror, one source module, and one focused test
module. It does not modify P1A/P1B/P1C-A/B/C/D contracts, CHANGELOG, active
locks, current state, task index, TASK-029, TASK-054, TASK-059, bridge runtime,
or Profile transport.

## Exact admission transaction

The writer snapshots an exact built-in JSON delivery once. Under the Product
Project lock and external-anchor guard it reruns P1C-B from raw delivery and
the durable staging ledger. P1C-C and P1C-D are executed in-process; serialized
candidate documents are never authority inputs. The resulting canonical child
is committed through `ProductProjectSaveCoordinator` with an anchor participant.

Lock order is Product Project then external anchor. The participant keeps a
private recovery record, performs exact expected-anchor CAS, writes the target
anchor only for ProjectSave COMPLETE, and requires exact read-back. ProjectSave
binds the canonical child in the Product manifest. A private transaction
journal fixes the public receipt body before side effects so recovery republishes
the same receipt bytes. The public receipt is written only after ProjectSave is
COMMITTED, current-child integrity passes, and canonical child, manifest,
anchor, and receipt registry all read back exactly.

`DUPLICATE` requires the exact current anchored entry and exactly one durable
original `ACCEPTED` receipt for the same idempotency key and current commit. It
does not advance the canonical ledger or anchor. Any same ID/different digest,
partial scope, stale CAS, split brain, missing recovery evidence, tamper, or
unexpected Project/anchor coordinate fails closed.

The trusted reader rejects public JSON as origin authority. It returns a sealed
wrapper only after ProjectSave has no pending recovery, manifest child integrity
passes, the exact canonical bytes match the binding, the external anchor binds
the historical commit-time manifest revision and canonical commit, the current
manifest revision is not older than that historical revision, and the selected
receipt binds the current canonical commit. Unrelated later child additions,
including the generic observation ledger, are allowed; changing or removing the
exact canonical child remains fail-closed.

## External coordinate claim

The anchor root must be outside the Product Project root. This reduces a shared
snapshot failure domain but does not authenticate origin and does not create
anti-rollback authority. Machine-readable fields fix
`external_snapshot_coordinate_only=true`, while origin authentication,
rollback-detection authority, directory-durability confirmation, and hostile
path-race protection remain false.

## Generic review-observation namespace

Generic SKILL observations use
`state/montage-learning-generic-review-observations.json`, a separate format,
hash domain, semantic identity, and internal receipt. `ACCEPTED` and
`DUPLICATE` mean only immutable/idempotent durable observation storage.
Same-record/different-learning-digest is a collision. Generic delivery cannot
enter the exact admission writer and exact delivery cannot enter the generic
ledger. The body-free `to_skill_v1_receipt()` projection is an outbound seam;
bridge transport remains FAST-BATCH-1B/1C responsibility.

## Recovery and failure model

Supported recovery is the existing ProductSave state machine plus the exact
anchor participant and private receipt journal. Source-manifest state resumes
the exact save; a target-manifest state validates all children and completes
receipt publication. Anchor values outside the expected-old/target pair,
unbound manifest state, changed staging read-back, journal mismatch, registry
fork, or canonical/anchor mismatch is `RECOVERY_REQUIRED` by exception and no
positive receipt is returned.

The implementation claims exact replace/read-back durability provided by the
current ProductSave/AtomicJsonWriter substrate. It explicitly does not claim
directory fsync confirmation or power-loss rollback prevention on every host.

## Acceptance

- raw P1C-B/C/D rerun under fixed lock order;
- ProductSave participant commit/recovery and exact read-back;
- public v2 `ACCEPTED` then exact `DUPLICATE` lineage;
- sealed trusted-reader currentness verification;
- crash-after-commit byte-identical receipt republish;
- crash after anchor write but before participant-result journal persistence;
- exact admission followed by unrelated generic child commit preserves trusted
  exact-receipt currentness;
- actual generic/exact concurrent ProjectSave serialization;
- stale CAS, collision, tamper, forged wrapper, custom Mapping, scalar subclass,
  and exact/generic cross-lane replay fail closed;
- generic separate-ledger `ACCEPTED`/`DUPLICATE` and collision coverage;
- schema mirror, focused/direct regression, diff scope, independent DEV-4
  Critic/Tester/Judge.
