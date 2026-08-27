# TASK-058 FAST-BATCH-1A Canonical Admission Transaction Design

Status: `IMPLEMENTED_LOCAL / INDEPENDENT_RE-REVIEW_PENDING`

Accepted cross-repository Design binding:
`bai-davinci-montage-skills@9f6c26ac5147b9a881ca037ae02ef020818db50a`
with
`accepted_design_sha256=sha256:c5c17aa92ab5f68daef315e4fc62a1fb7a46e3f80c2c8093adec1f073594db80`.
The Design-only Final Judge result is C/H/M/L=0/0/0/0. This binding does not
authorize the separately reserved TASK-060/061/062 capabilities.

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

Each exact attempt first holds a stable operation-lock inode through proposal,
ProjectSave, receipt read-back, and journal cleanup. Inside that serialization
boundary the fixed state lock order is Product Project then external anchor.
The operation lock is a sibling lock file and is never replaced or removed with
the journal payload. The participant keeps a
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
hash domain, semantic identity, and internal typed read-back. Immutable source
objects use
`state/montage-learning/review-observations/<payload_sha>.json`; body-free
commit markers use
`state/montage-learning/review-observation-markers/<transaction_id>.json`;
and the single A-owned recovery journal is
`state/montage-learning/review-observation-admission-journal.json`.
`ACCEPTED` and `DUPLICATE` mean only immutable/idempotent durable observation
storage. Same-record/different-learning-digest is a collision.

The typed A surface is `admit_generic_observation()`,
`recover_generic_observation()`, and
`get_verified_generic_observation()`, with the explicit
`admit_review_observation` / `recover_review_observation` /
`get_current_review_observation` aliases. It returns a sealed
`ReviewObservationAdmissionResult` containing a sealed stable
`ReviewObservationCanonicalReadback`. The result and read-back both fix
`store_kind=REVIEW_OBSERVATION`; learning adoption, Profile promotion, and
Timeline mutation remain false. A does not mint the public SKILL v1 transport
receipt; receipt projection and correlation remain FAST-BATCH-1B/1C
responsibility.

A duplicate returns the original stable canonical read-back without writing a
payload, ledger, Product manifest, or marker and without increasing any
revision. Trusted current reads validate the current complete ledger chain and
every historical payload, Product child binding, marker, canonical commit, and
internal receipt hash before returning authority. Generic delivery cannot enter
the exact admission writer and exact delivery cannot enter the generic ledger.

## Recovery and failure model

Supported recovery is the existing ProductSave state machine plus the exact
anchor participant/private receipt journal and the Generic A-owned phase
journal. Generic phases are `PREPARED -> PAYLOAD_WRITTEN -> LEDGER_COMMITTED ->
MANIFEST_COMMITTED -> MARKER_COMMITTED -> READBACK_VERIFIED`, with
`ABORTED` reserved as the terminal negative state. Every transition is
self-hashed, CAS-checked, atomically replaced, and read back. An unrelated
Product manifest advance while a Generic journal is still PREPARED is rebased
only when the journal operation identity is unchanged and no matching Generic
ledger entry is already committed. A matching committed entry instead resumes
marker/read-back completion. Source-manifest state resumes the exact save; a
target-manifest state validates all children and completes receipt publication.
Anchor values outside the expected-old/target pair, unbound manifest state,
changed staging read-back, journal mismatch, registry fork, or
canonical/anchor mismatch is `RECOVERY_REQUIRED` by exception and no positive
receipt is returned.

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
- actual same-CAS multiprocess execution has exactly one `ACCEPTED` caller;
- stale CAS, collision, tamper, forged wrapper, custom Mapping, scalar subclass,
  and exact/generic cross-lane replay fail closed;
- generic separate-ledger `ACCEPTED`/`DUPLICATE` and collision coverage;
- Generic duplicate leaves payload/ledger/manifest/marker bytes and revisions
  unchanged;
- pinned non-inheritable reads reject ancestor identity drift and equal-size
  target substitution;
- Generic crash recovery covers PREPARED, Product commit, marker commit, and
  terminal read-back before journal cleanup;
- currentness validates every historical payload and marker, not only the
  requested ledger entry;
- repeated actual Generic same-CAS multiprocess execution has one
  `ACCEPTED`, one fail-closed caller, bounded child/queue cleanup, and no
  private journal left behind;
- schema mirror, focused/direct regression, diff scope, independent DEV-4
  Critic/Tester/Judge.

## Current bounded-rework checkpoint

- prior Work Order implementation review: Technical NO-GO,
  C/H/M/L=0/3/2/0;
- known pinned-read, Generic transaction/recovery, duplicate-idempotency,
  typed-authority, nested-schema, and fault-coverage findings: implemented in
  the same six-file Atomic Unit;
- focused A tests: 23/23 PASS;
- TASK-043 ProductSave + TASK-055 + TASK-058 direct regression:
  345/345 PASS;
- final exact-head full Product regression:
  4528 PASS / 6 platform-condition SKIP / 2 deprecation warnings / 0 FAIL;
- Python compile, Draft 2020-12 schema validation, public/package byte mirror,
  and diff-check: PASS;
- independent implementation re-review and Hosted terminal checks: PENDING;
- CHANGELOG, Registry, shared LOCK, Ready, merge, B+C, TASK-060/061/062,
  enabled:true, Profile meaning generation, Timeline/Resolve, Release, Deploy,
  and Production effects: NOT STARTED / NOT EXECUTED.
