# TASK-076 — Durable Product Job Secure Artifact

Status: `DESIGN_COMPLETE / DEV-4 / SOURCE_START0`

Design identity: `TASK076-PTD-DURABLE-PRODUCT-JOB-SECURE-ARTIFACT-V5`

Canonical design base: `origin/main@efdcd77729732e3c50abb9e4a7e89ae2b7b37aa0`

Owner allocation: `2026-09-01 / Platform Trust & Delivery / Design B`

## 1. Decision

TASK-076 owns a v2 append-only Product-local durable Job and secure single-file
artifact protocol. Its authority chain is exactly:

```text
TASK-068 immutable secure I/O
    + TASK-043 exact Project/Job currentness
    + TASK-072 exact child redemption/terminal receipt
    -> TASK-076 immutable Job events and secure Artifact binding
```

TASK-068 proves pinned strict bytes, physical identity and immutable no-replace
publication. It never chooses current/head/latest. TASK-043 alone binds the
current Job event into the current Project revision. TASK-072 alone proves that
the exact authorized child entered and completed or became unknown. TASK-076
combines those three independent proofs; none substitutes for another.

The existing mutable `jobs.json` store remains a legacy read-only projection.
Its dataclasses, self-hashes, state versions, generic file lock and CAS result do
not authorize a v2 transition, artifact adoption, native child, replay or
currentness. V2 performs no in-place Job mutation and no scan-selected recovery.

## 2. Fresh source-backed gap

Canonical `durable_product_job.py` currently:

- resolves Project/control/store through `Path` operations and path reopens;
- checks `is_symlink/is_file/stat` and later uses `read_text`, leaving
  stat-open/read-post and same-bytes/different-inode seams;
- uses `json.loads` without duplicate-key rejection, finite-number policy or
  bounded tree/depth/string validation before object construction;
- reuses `_exclusive_project_lock`, whose initial/existing path is not a secure
  pinned physical lease and can race with hardlink/reparse/ancestor changes;
- rewrites one mutable `jobs.json` through generic `AtomicJsonWriter`;
- compares public `state_version` and self-hash but not opened bytes plus inode
  identity at the final publication seam;
- can return an existing equal operation from a collection scan, so a copied or
  ambiguous store can appear idempotent without an exact event/identity proof;
- automatically scans all `DISPATCHING/RUNNING` rows on restart and rewrites
  them to `UNKNOWN`;
- lets public `result_ref` and caller-driven `recovery_action` describe
  reconciliation without an exact native child terminal/artifact readback;
- binds Project identity only by separately reading the current manifest; and
- inherits TASK-043 `product_project_store.py`, which also uses path stat/read,
  the generic lock and generic atomic replacement for Project currentness.

Current tests cover deterministic IDs, state transitions, checksum tamper,
symlink rejection, Project conflict and no-blind-retry intent. They do not close
physical identity races, strict JSON ambiguity, append-only currentness,
operation-owned artifact handles, Task068 trusted-plan binding, Task072 child
identity, crash seams or foreign-cleanup preservation.

TASK-068 candidate `IMMUTABLE_ONLY_V1` can publish/read exact immutable records
but explicitly cannot perform mutable CAS, select currentness, create parent
directories, commit directory trees or delete published artifacts. TASK-076
must compose within that boundary rather than treating an audit receipt as Job
state authority.

## 3. Responsibility boundary

TASK-076 owns:

- the v2 Product-local Job kind/profile registry;
- stable semantic Job keys and immutable issue reservations;
- immutable Job event schemas, predecessor rules and transition validation;
- the private `TASK076_JOB_AUTHORIZATION_V1` consumer port;
- exact integration with TASK-068 immutable plans and receipts;
- exact integration with TASK-043 Project/Job currentness readbacks;
- exact integration with TASK-072 child redemption/terminal receipts;
- secure single-regular-file Artifact preparation, handle, manifest and readback;
- result/currentness correlation without mutable Job-file replacement;
- restart/recovery/fork/collision classification with no scan-selected winner;
- public body/path-free Job status projections;
- versioned fixture contracts for downstream Product Jobs;
- focused, fault, recovery, concurrency and Windows-native QA contracts.

TASK-076 does not own:

- Product Project semantics, manifest schema, Project save or current-head
  selection (TASK-043);
- generic strict I/O, secure lock or immutable namespace implementation
  (TASK-068);
- operation ticket/config, native child authorization or child terminal
  semantics (TASK-072);
- any consumer's command, Provider, media, export, analysis, render, model,
  training, Timeline, Resolve, audio or narration semantics;
- multi-file/directory-tree artifact commit in v1;
- legacy `jobs.json` migration, rewrite, repair or deletion;
- physical GC, retention deletion or uninstall cleanup;
- TASK-074 Product semantics;
- Release, Deploy, Production Activation, paid/provider execution, secret use,
  model/runtime download, private-media upload or external-account mutation.

TASK-074 is Design A-owned. TASK-076 may review a future TASK-074 Job port for
authority correctness but may not define or modify its Product behavior.

## 4. One-way artifact/phase dependency graph

```text
TASK-068 IMMUTABLE_SECURE_IO_V1 fixture
TASK-043 PROJECT_JOB_CURRENTNESS_ABI_V2 fixture
TASK-072 JOB_CHILD_ARM_START_AND_TERMINAL_ABI_V2 fixture
    -> TASK-076-A JOB_SECURE_ARTIFACT_FIXTURE_V1

TASK-068 canonical immutable secure I/O completion
TASK-043 canonical PROJECT_JOB_CURRENTNESS_READBACK_V2
consumer TASK076_JOB_PLAN_V1
    -> TASK-076-B immutable reservation no-replace
    -> RESERVED candidate
    -> TASK-043 ABSENT_JOB_HEAD -> RESERVED CAS/readback
    -> PREPARED candidate -> TASK-043 CAS/readback
    -> READY candidate -> TASK-043 CAS/readback

TASK-076-B exact current READY
consumer TASK072 action authorization
TASK-072 private non-authoritative JOB_DISPATCH_PLAN_V2
    -> DISPATCHING candidate -> TASK-043 CAS/readback
    -> TASK-072 issue_and_arm_job_child_v2 durable ticket burn/ARMED
    -> TASK-076-C IN_FLIGHT candidate -> TASK-043 CAS/readback
    -> Artifact handle create -> TASK-072 attach_and_start_job_child_v2 -> child effect

TASK-072 exact child terminal
consumer exact artifact validator/readback
TASK-068 exact immutable publication/readback
    -> TASK-076-D RESULT/ARTIFACT terminal candidate
    -> TASK-043 terminal CAS/readback
    -> TASK-076 current public projection / next transition

Sensitive-input consumer profile only:
TASK-072 JOB_CHILD_BOOTSTRAP_BIND_RELEASE_ABI_V3 fixture
consumer-owned typed external-binding ABI fixture
    -> issue_and_arm_job_child_v3 after selected DISPATCHING
    -> selected TASK-076 IN_FLIGHT
    -> create_bootstrap_job_child_v3 (broker bootstrap only; model/artifact zero)
    -> consumer owner binds sensitive handles directly to exact child broker
    -> child preflight validates those handles with model/artifact-body zero
    -> release-budget Artifact-prepare claim -> handle create -> truth commit
    -> release claim -> child model/effect
       | abort claim -> owner close -> child termination -> proven terminal
```

TASK-076-A can freeze fixture shape before producer implementation. B/C/D remain
`DEPENDENCY_NC` until their exact canonical producer receipts exist. An
immutable event without TASK-043 currentness is historical/unselected evidence.
A TASK-043 binding without TASK-068 pinned bytes/identity is not a valid event.
A terminal result without TASK-072 child receipt is not a native effect proof.
The V3 sensitive-input path is a fixture/consumer contract until TASK-072 and
the named sensitive-input producer each publish exact accepted ABIs. V2 remains
the ordinary single-phase path. No caller hook, generic callback or arbitrary
producer can enter V3.

This graph is acyclic because TASK-076 publishes a candidate immutable event,
TASK-043 independently advances Project currentness to that exact event, and a
later transition consumes the new TASK-043 readback. TASK-076 never writes the
Project manifest itself.

## 5. Design PR and future implementation scope

This design PR may change exactly:

- `docs/ai-team/tasks/TASK-076/complete-design-packet.md`

After independent Critic `C/H=0`, Judge `PASS`, canonical producer receipts,
fresh overlap/lock checks and a separate implementation start receipt, a future
TASK-076 implementation may change exactly:

- `src/ai_video_production/durable_product_job_secure_artifact.py`
- `schemas/durable-product-job-reservation-v2.schema.json`
- `schemas/durable-product-job-event-v2.schema.json`
- `schemas/durable-product-job-artifact-v2.schema.json`
- `schemas/durable-product-job-public-status-v2.schema.json`
- `src/ai_video_production/schema_resources/durable-product-job-reservation-v2.schema.json`
- `src/ai_video_production/schema_resources/durable-product-job-event-v2.schema.json`
- `src/ai_video_production/schema_resources/durable-product-job-artifact-v2.schema.json`
- `src/ai_video_production/schema_resources/durable-product-job-public-status-v2.schema.json`
- `tests/test_task076_durable_product_job_secure_artifact.py`
- `tests/test_task076_durable_product_job_faults.py`
- `tests/test_task076_durable_product_job_windows.py`
- `tests/fixtures/task076/job-secure-artifact-fixture-v1.json`
- `tests/fixtures/task076/job-immutable-event-chain-fixture-v1.json`
- `tests/fixtures/task076/job-strict-json-negative-fixture-v1.json`
- `tests/fixtures/task076/job-child-bootstrap-bind-release-fixture-v3.json`
- `docs/ai-team/tasks/TASK-076/complete-design-packet.md`

No executable helper, alternate event format, supplemental Evidence document or
other file is authorized by a directory name. A new filename requires a
separately reviewed Atomic Unit allocation receipt before it may be written.

Changes to `durable_product_job.py`, `product_project.py`,
`product_project_store.py`, TASK-043 tests/schemas, TASK-068, TASK-072, consumer
modules, installer/build specs, `pyproject.toml`, shared current-state/task-index/
roadmap, CHANGELOG or another Task require that owner's separate exact amendment
and fresh lock/overlap.

## 6. Trust and threat boundary

### 6.1 Trusted Production components

Production fixes and attests:

- the packaged BVP Product parent process/image/build;
- the consumer-owned Job-plan verifier and exact action profile version;
- the TASK-068 `SecureAuthorityIO` instance, authority-instance verifier and
  exact immutable-plan aggregate verifier;
- the TASK-043 Project/current-Job reader and Project manifest verifier;
- the TASK-072 broker/child terminal reader and process/build/session verifier;
- the TASK-072 dedicated Windows Job Object sole-containment-handle and named
  producer recovery-revoke adapter;
- the consumer-owned Artifact class validator;
- the Windows handle/file/ancestor/security currentness implementation;
- the trusted broker monotonic/boot/session clock.

No public dataclass, JSON, self-hash, state string, result reference, request ID,
caller path, environment, current directory, filename scan, timestamp, hook,
backend or injected test provider creates Production authority.

### 6.2 Protected attackers

V1 protects against:

- public Job/collection/receipt construction, copying, deserialization and hash
  recomputation;
- new request IDs for the same semantic effect;
- duplicate, concurrent, cross-Project and cross-install Job creation;
- store/event/artifact stat-open/read-post and same-bytes/different-inode swaps;
- ancestor, reparse, hardlink, DACL, lock and operation-parent drift;
- mutable fixed-file overwrite and scan-highest/latest selection;
- forged, stale, wrong-action or receipt-only TASK-072 child terminals;
- broker/channel crash after partial sensitive-role transfer, including leaked
  bootstrap-process and child-local handle containment;
- unknown/foreign output adoption or deletion;
- crash at each reservation/event/child/artifact/currentness seam;
- ambiguous JSON and resource-exhaustion input;
- path, payload, secret, command, child output and OS-detail leakage.

### 6.3 Explicit non-goals

V1 does not resist administrator/kernel compromise, injection/debugging of a
trusted process, compromised release signing, malicious content that passes the
consumer's own validator, or unavailable filesystem durability guarantees.
Multi-file/directory tree commit and physical artifact GC are unsupported v1
effects, not partially implemented features.

## 7. Versioned contracts

### 7.1 `TASK076_JOB_PLAN_V1`

The consumer supplies a private, nonserializable, already-current plan over the
trusted Product channel. It binds:

- consumer Task/action/profile/verifier implementation digest;
- Project/install identity and TASK-043 current Project revision/readback;
- closed Job kind and exact target identity;
- sorted typed input receipt set with schema/version/hash/physical identity;
- stable `semantic_job_key` and expected predecessor Job event or null;
- exact TASK-072 action profile/command/argument-vector digest;
- expected Artifact class/count/limits/validator identity;
- expected result profile and consumer terminal verifier;
- Product/broker/child/build/backend identities;
- trusted expiry/boot/session and invocation budget one;
- exact TASK-068 operation parent, authority instance and plan-set digest;
- public privacy projection digest.

The consumer verifier derives the semantic key from the complete intended
effect. UI request ID, reservation ID, ticket ID, process ID, random nonce and
timestamps are excluded. The same intended effect under a new request therefore
collides with its prior reservation.

A later semantic attempt is a different key only when an authorized consumer
changes a real semantic input and binds the exact prior terminal or a trusted
no-effect reconciliation. A new random ID, time or syntactically new plan cannot
change it. `BURNED_UNKNOWN` can never be the predecessor of a replay-capable
attempt; only a consumer-specific durable proof that the original effect was
zero may support a distinct compensation plan whose action is itself different.

Public `DurableProductJob`, `DurableProductJobCollection`, hashes, mappings and
legacy `operation_identity` are compatibility evidence with
`authority_created=false`; they cannot satisfy this port.

### 7.2 Closed Job kinds

V1 profiles are versioned registrations, not free-form strings:

| Job kind | Consumer action owner | Artifact class |
|---|---|---|
| `EXPORT` | exact TASK-036/TASK-011 export action profile | one validated final package/file or receipt-only external artifact |
| `LOCAL_ANALYSIS` | exact analysis consumer | one bounded analysis artifact or receipt-only result |
| `LOCAL_TRANSCODE` | exact media consumer | one validated media file |
| `MEDIA_INDEX` | exact indexing consumer | one bounded canonical index file |
| `PROJECT_MAINTENANCE` | exact Project maintenance consumer | receipt-only by default; no destructive cleanup |

Each row requires its own frozen consumer verifier and TASK-072 action profile.
Registration does not authorize the effect. Unknown kinds, a generic command or
an extra/missing producer receipt fail before reservation publication.

The existing v1 enum is descriptive only. A real consumer profile must be
separately allocated before that kind is Production eligible.

### 7.3 `JOB_ISSUANCE_RESERVATION_V2`

Before any Job event or child issuance, TASK-076 publishes one immutable
no-replace reservation through TASK-068 at an exact coordinate derived from:

- TASK-076 namespace/version;
- Project/install identity;
- opaque SHA-256 of `semantic_job_key`.

The body binds the full verified plan fingerprint, expected first-event plan,
random display/reservation IDs, trusted build/session/clock identity and exact
TASK-043 currentness predecessor. Random values never affect the coordinate.

An existing reservation is never adopted as new authority. Same/different body,
same bytes/different identity or unknown collision is STOP+preserve. Only the
same exact already current committed terminal may be reported as public audit
`DUPLICATE`; a reservation or unselected terminal alone cannot.

### 7.4 `DURABLE_PRODUCT_JOB_EVENT_V2`

Every state is a separate immutable strict document with:

- schema/message/profile version;
- Project/install/Job/semantic-key opaque commitments;
- exact event kind and bounded monotonic sequence;
- exact predecessor event coordinate, hash and physical identity;
- complete plan/input/action/currentness fingerprints;
- TASK-068 plan/receipt/authority-instance identities;
- TASK-043 predecessor Project revision/readback;
- TASK-072 ticket/config/child identities when applicable;
- Artifact manifest/readback identities when applicable;
- stable result/reason and completion-unknown flags;
- Product/broker/child/backend/session/clock identities;
- canonical body self-hash and `authority_created=false` public projection.

The event coordinate is supplied by the trusted plan and exact predecessor. No
directory scan, filename order, mtime, lexicographic maximum or mutable pointer
selects it. Event numbers cannot skip or fork. Identical competing events at the
same slot are collision, not automatic duplicate.

### 7.5 State and event kinds

```text
RESERVED
 -> PREPARED
 -> READY
 -> DISPATCHING
 -> IN_FLIGHT
      -> SUCCEEDED
      -> FAILED_KNOWN
      -> BURNED_UNKNOWN

RESERVED/PREPARED/READY
 -> CANCELLED_SAFE

READY
 -> FAILED_KNOWN
      only from exact TASK-072 dispatch-plan validation REJECTED readback

DISPATCHING
 -> FAILED_KNOWN
      only from exact TASK-072 pre-effect REJECTED readback
 -> BURNED_UNKNOWN
      only from exact TASK-072 burned/IN_FLIGHT readback plus proof that no
      TASK-076 IN_FLIGHT event became TASK-043-current

PREPARED/READY
 -> HUMAN_REQUIRED
 -> PREPARED only through a fresh predecessor-bound consumer plan
```

Rules:

1. `PREPARED` requires a current TASK-043 readback and complete consumer plan.
2. `READY` requires every non-Human prerequisite; it grants no child authority.
3. `DISPATCHING` binds a TASK-072 `JOB_DISPATCH_PLAN_V2` that is not a ticket,
   channel or redeemable authority.
4. `IN_FLIGHT` is durable before the consumer effect and burns the invocation.
5. `SUCCEEDED` requires exact child terminal and all required Artifact readbacks.
6. `FAILED_KNOWN` requires a trusted no-success terminal with stable reason.
7. Any post-entry state not proven known is `BURNED_UNKNOWN`.
8. Restart does not rewrite prior states. It classifies from exact coordinates.
9. No terminal permits a transition to READY/DISPATCHING/RUNNING.
10. A new semantic attempt requires a new consumer plan revision bound to the
    exact predecessor terminal/reconciliation receipt.
11. Every terminal edge is an immutable candidate followed by TASK-043 CAS
    selection and fresh currentness readback; classification alone is not state.

### 7.6 TASK-068 composition

TASK-076 uses only canonical effect-bearing TASK-068 v1 surfaces:

- strict pinned `read_immutable_json` for exact records;
- secure existing/initial operation lease where required;
- `publish_immutable_json` for reservation, events and Artifact manifests;
- exact-coordinate `inspect_immutable_graph` for a consumer-supplied allow-list.

TASK-076 never calls or emulates TASK-068 unavailable mutable CAS, directory
commit, phase advance or cleanup. The trusted immutable plan is itself audit
data; the private TASK-076 verifier binds every semantic field before TASK-068
is allowed to publish.

TASK-068 graph success proves only the supplied set is consistent. TASK-043
currentness remains mandatory. An orphan valid event is preserved and not
selected, repaired, relinked or deleted by TASK-076.

### 7.7 `PROJECT_JOB_CURRENTNESS_READBACK_V2`

TASK-043 must provide a separate cross-owner private currentness port. It binds:

- exact Project root/manifest opened identity and canonical bytes;
- Project ID, revision, predecessor and manifest physical identity;
- one exact Job semantic key and a typed Job-head variant:
  `ABSENT_JOB_HEAD` bound to the opened manifest bytes/revision and proof that
  the semantic key has no selected entry, or `SELECTED_JOB_HEAD` with exact
  event coordinate/hash/physical identity;
- exact TASK-068 namespace/plan-set digest;
- exact consumer/save operation identity;
- Product/install/build/security/currentness reader identity;
- a trusted monotonic Project-currentness coordinate.

TASK-043 updates Project currentness through its own separately corrected secure
transaction. Current `ProductProjectManifestStore.load/save`, generic lock and
`AtomicJsonWriter` cannot satisfy V2. TASK-076 cannot write the Project manifest
or infer currentness from equal IDs/hashes.

For an event to become current:

1. TASK-076 publishes and pins the candidate immutable event. The first
   `RESERVED` candidate requires `ABSENT_JOB_HEAD`; later candidates require the
   exact selected predecessor.
2. TASK-043 verifies the exact candidate and prior Project/Job head.
3. TASK-043 commits one next Project revision binding that event.
4. TASK-043 returns a fresh exact V2 readback.
5. TASK-076 may project or advance only from that readback.

Failure after step 1 leaves an unselected orphan. It is harmless historical
evidence and must be preserved.

### 7.8 TASK-072 child binding

Before selected `DISPATCHING`, TASK-076 accepts only private
`JOB_DISPATCH_PLAN_V2`. It binds the exact fixed action/config/command/argument
and handle-role digests, consumer/build/session and expected READY readback, but
has `authority_created=false`, no live channel, no ticket and no invocation
budget. It is safe to discard and deterministically reconstruct while READY is
still current.

Only after TASK-043 selects the exact DISPATCHING event may TASK-076 call:

```text
issue_and_arm_job_child_v2(
    EXACT_CURRENT_DISPATCHING_READBACK,
    JOB_DISPATCH_PLAN_V2,
    exact_private_consumer_inputs
) -> JOB_CHILD_ARMED_READBACK_V2
   | JOB_CHILD_REJECTED_READBACK_V2
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V2
```

TASK-072 performs issue, channel creation and invocation-budget burn in one
serialized broker entry; it never returns a redeemable pre-DISPATCHING ticket.
`JOB_CHILD_ARMED_READBACK_V2` proves child process/start/effect zero and binds:

- ticket, config, consumer/session/image/build and private channel identity;
- exact command/argv and input/output handle-role digest;
- durable broker state `ARMED` and start budget one;
- trusted time/boot/session and predecessor event;
- `COMMITTED`, `REJECTED` or `BURNED_UNKNOWN`.

After TASK-043 selects the exact TASK-076 IN_FLIGHT event and the Product creates
the operation-owned Artifact handle, TASK-076 may call exactly once:

```text
attach_and_start_job_child_v2(
    EXACT_CURRENT_TASK076_IN_FLIGHT_READBACK,
    JOB_CHILD_ARMED_READBACK_V2,
    exact_private_input_and_artifact_handles
) -> JOB_CHILD_STARTED_READBACK_V2
   | JOB_CHILD_START_REJECTED_READBACK_V2
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V2

abort_armed_job_child_v2(
    EXACT_CURRENT_TASK076_IN_FLIGHT_READBACK,
    JOB_CHILD_ARMED_READBACK_V2,
    closed_stable_no_effect_reason
) -> JOB_CHILD_ABORTED_READBACK_V2
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V2

abort_armed_orphan_job_child_v2(
    EXACT_CURRENT_DISPATCHING_READBACK,
    EXACT_UNSELECTED_TASK076_IN_FLIGHT_CANDIDATE,
    JOB_CHILD_ARMED_READBACK_V2,
    closed_stable_recovery_reason
) -> JOB_CHILD_ORPHAN_ABORTED_READBACK_V2
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V2
```

TASK-072 owns this serialized boundary. It revalidates the current Job/Project,
armed operation, channel, command and exact handle-role/identity set; consumes
the one start budget; duplicates only the restricted declared handles; creates
the fixed child suspended; durably records child `IN_FLIGHT` with exact
process/token/session/image/build identity; then resumes that child once. No
caller-visible handle, ticket, boolean or process object can perform the start.
An exact pre-create rejection proves child effect zero but remains terminal and
non-retryable because the arm/start budget is burned. Any uncertainty after
start-budget entry is `BURNED_UNKNOWN`. Product/broker restart invalidates ARMED
and permits only exact durable query/classification, never reattachment/start.
The separately versioned `JOB_CHILD_TERMINAL_READBACK_V2` binds the started
readback, child result digest and terminal state.

`abort_armed_job_child_v2` is the only same-session no-effect close path after
TASK076 IN_FLIGHT selection. TASK-072 serializes it against attach-and-start;
exactly one may consume the ARMED start budget. An abort winner durably records
process/create/start/effect zero and makes every delayed start reject. A start
winner makes abort return only the exact started/unknown classification and does
not fabricate no-effect. Artifact create/collision, handle validation, cancel or
consumer exception must obtain the exact ABORTED readback before a FAILED_KNOWN
terminal candidate; abort crash/unknown requires exact broker query and a
BURNED_UNKNOWN candidate. A local reason string or TASK076 terminal candidate
cannot consume the broker budget.

`abort_armed_orphan_job_child_v2` is the only recovery path that may close an
ARMED operation while its exact TASK076 IN_FLIGHT candidate is published but not
TASK043-selected. TASK-072 verifies the current DISPATCHING readback, exact
predecessor/slot/body/physical identity of the orphan and unchanged ARMED state,
then durably consumes the start budget with process/create/start/effect zero.
Only its exact ORPHAN_ABORTED readback may authorize TASK043 selection of that
orphan. It serializes with normal abort/start and is idempotent only as an exact
same-operation query. Unknown, changed Project/head, candidate collision or a
concurrent selection produces no claimed no-effect and no publish/select.

Public receipts, command output, process exit code alone, config equality or an
in-process consumer boolean cannot prove a child effect. `BURNED_UNKNOWN` is not
success and never authorizes replay.

#### 7.8.1 Sensitive-input bootstrap/bind/release V3

Some consumers cannot lawfully give a sensitive producer capability to the
parent and cannot bind it before an exact worker process exists. Those consumers
use the separate closed
`TASK076_JOB_CHILD_BOOTSTRAP_BIND_RELEASE_V3` profile. V2 is not upgraded or
aliased. V3 is available only when the consumer fixture declares exactly one
allowlisted `TASK076_EXTERNAL_BINDING_SLOT_V1` containing:

- producer Task and exact bind/preflight/recovery-revoke ABI plus
  acceptance-receipt versions;
- exact expected child-broker protocol/build/image and consumer operation key;
- closed sensitive role-set digest and shared-lease policy digest;
- exact body-free producer preflight result contract;
- `parent_sensitive_handle_count=0` and `caller_hook_allowed=false`;
- fixed process-create, external-bind, preflight, release and abort budgets one;
- fixed false flags for model load/call, Artifact body write and consumer effect
  before release; `artifact_handle_created` is a separate physical fact and is
  false until external preflight is `VALIDATED`.

The slot is metadata and authority-free. It never contains a callback, module,
PID, process object, handle, body, path, URI, command or serialized capability.
An unknown producer, ABI, role set, validator or extra slot is rejected before
arming.

`JOB_CHILD_ARMED_READBACK_V3` owns one durable state vector. Every transition is
a one-winner CAS over that exact vector; no phase readback is a free-standing
capability. The five budgets have these closed lifecycles:

| budget | initial | legal winner | terminal outcomes |
|---|---|---|---|
| process-create | `OPEN` | bootstrap create, pre-bootstrap abort, or orphan abort | `CONSUMED_CREATED`, `CONSUMED_REJECTED`, `CONSUMED_ABORTED`, `BURNED_UNKNOWN` |
| external-bind | `LOCKED` until `BOOTSTRAP_WAITING`, then `OPEN` | owner bind record or abort claim | `CONSUMED_BOUND`, `CONSUMED_FAILED`, `CONSUMED_ABORTED`, `CLOSED_REJECTED`, `BURNED_UNKNOWN` |
| preflight | `LOCKED` until `BOUND`, then `OPEN` | child preflight or abort claim | `CONSUMED_VALIDATED`, `CONSUMED_FAILED`, `CONSUMED_ABORTED`, `CLOSED_REJECTED`, `BURNED_UNKNOWN` |
| release | `LOCKED` until `VALIDATED`; then `ARTIFACT_PREPARE_OPEN -> ARTIFACT_PREPARE_PENDING -> ARTIFACT_PREPARED | ARTIFACT_PREPARE_FAILED`; finally release claim or abort claim | Artifact-prepare claim/commit, release claim or abort claim | `CONSUMED_STARTED`, `CONSUMED_REJECTED`, `CONSUMED_ABORTED`, `CLOSED_REJECTED`, `BURNED_UNKNOWN` |
| abort | `OPEN` while no release winner exists; `ABORT_WAITING_ARTIFACT_TRUTH` when it wins during Artifact prepare | orphan/pre-bootstrap abort or bootstrap abort claim | `CONSUMED_ABORTED`, `CLOSED_RELEASE_WON`, `CLOSED_REJECTED`, `BURNED_UNKNOWN` |

Arm-level `JOB_CHILD_REJECTED_READBACK_V3` is a pre-vector effect-zero result and
proves `budget_vector_created=false`. Create-level
`JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3` is legal only when the same durable
transaction proves no process was created and closes all five issued budgets.
Any uncertain create, owner close,
termination, release or resume goes to a vector-wide `BURNED_UNKNOWN`; no budget
remains reusable. A result query may return the same terminal vector but cannot
consume a second budget.

The exact bootstrap-rejected terminal vector is:
`process-create=CONSUMED_REJECTED`, `external-bind=CLOSED_REJECTED`,
`preflight=CLOSED_REJECTED`, `release=CLOSED_REJECTED` and
`abort=CLOSED_REJECTED`. The same tokens are frozen in fixture/schema/fault
oracles; an implementation may not invent another terminal spelling.

Every budget method first authenticates its private channel and matches the
exact operation/vector identity without mutation. Unknown, forged, stale or
cross-operation input is effect zero and cannot burn another operation. After
the method durably enters the matching budget, success consumes it and every
exception/uncertainty burns it; caller retry never does. Thus fail-closed budget
consumption cannot be used as a public denial-of-service primitive.

After selected DISPATCHING, TASK-072 issues and burns the V3 operation exactly
once:

```text
issue_and_arm_job_child_v3(
    EXACT_CURRENT_DISPATCHING_READBACK,
    JOB_DISPATCH_PLAN_V3,
    exact_private_consumer_inputs,
    TASK076_EXTERNAL_BINDING_SLOT_V1
) -> JOB_CHILD_ARMED_READBACK_V3
   | JOB_CHILD_REJECTED_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

`ARMED_V3` proves process/model/Artifact-handle/Artifact-body/consumer-effect
zero and binds the complete five-budget vector. If the planned TASK-076
IN_FLIGHT candidate is published but remains unselected while DISPATCHING is
still current, only this V3 recovery call may close it:

```text
abort_armed_orphan_job_child_v3(
    EXACT_CURRENT_DISPATCHING_READBACK,
    JOB_CHILD_ARMED_READBACK_V3,
    EXACT_UNSELECTED_TASK076_IN_FLIGHT_CANDIDATE_READBACK
) -> JOB_CHILD_ORPHAN_ABORTED_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

It atomically consumes process-create, external-bind, preflight, release and
abort, proves `child_process_created=false`, `artifact_handle_created=false` and
effect zero, and alone permits TASK-043 to select that exact orphan before the
predecessor-correct FAILED_KNOWN terminal. It serializes with selection and every
create/release path. V2 `ORPHAN_ABORTED` cannot substitute.

After the exact TASK-076 IN_FLIGHT candidate becomes TASK-043-current, a cancel
or local failure before bootstrap creation uses:

```text
abort_armed_prebootstrap_job_child_v3(
    EXACT_CURRENT_TASK076_IN_FLIGHT_READBACK,
    JOB_CHILD_ARMED_READBACK_V3,
    closed_stable_reason
) -> JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

This CAS wins against bootstrap creation, consumes all five budgets and proves
process/Artifact/model/consumer effect zero. A create winner makes this call
return the exact later phase or `BURNED_UNKNOWN`, never a false no-effect result.
Only while neither abort path has won may TASK-072 consume process-create:

```text
create_bootstrap_job_child_v3(
    EXACT_CURRENT_TASK076_IN_FLIGHT_READBACK,
    JOB_CHILD_ARMED_READBACK_V3,
    FIXED_BOOTSTRAP_DECLARATION_V3
) -> JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3
   | JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

TASK-072 creates the fixed child suspended, applies the restricted token,
network/dump/loader policy and closed inherited bootstrap channel, records the
exact process/token/session/image/build identity durably, then releases only the
attested broker-bootstrap entry point. No script/model/input/output/Artifact
handle is present and the bootstrap binary cannot enter consumer code. The
readback truthfully records `child_process_created=true` while
`model_loaded=false`, `model_called=false`, `artifact_handle_created=false`,
`artifact_body_write_started=false` and
`consumer_effect_started=false`.

Before any bootstrap entry, TASK-072 assigns the child to a dedicated Windows
Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. The sole containment handle
is non-inheritable and remains inside the exact TASK-072 broker process; parent,
consumer, producer and child handle counts are zero. It is never duplicated or
serialized. Broker termination therefore kills the contained child and closes
its child-local sensitive duplicates even when durable classification is unknown.

`BOOTSTRAP_REJECTED` is emitted only by an atomic known-no-process rejection that
closes every remaining budget as `CLOSED_REJECTED`. If a process may exist, if
its identity commit is uncertain, or if rejection durability is uncertain, the
only result is vector-wide `BURNED_UNKNOWN`. `BOOTSTRAP_REJECTED` never needs or
permits a later abort/release.

TASK-076 then exposes the private body-free binding coordinate only to the named
producer broker. The producer, not TASK-076 or the parent, transfers its exact
opened handles directly into that exact child-local broker and returns one
nonserializable `OWNER_EXTERNAL_INPUT_BOUND_READBACK_V1`. TASK-072 accepts it
only through the fixed owner adapter and records:

```text
record_job_child_external_binding_v3(
    JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3,
    OWNER_EXTERNAL_INPUT_BOUND_READBACK_V1
      | OWNER_EXTERNAL_INPUT_BINDING_FAILED_READBACK_V1,
    exact_owner_acceptance_receipt
) -> JOB_CHILD_EXTERNAL_INPUT_BOUND_READBACK_V3
   | JOB_CHILD_EXTERNAL_BINDING_FAILED_CLOSED_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

The readback binds the exact child process/broker, role set, owner operation,
shared lease, producer/currentness and `parent_sensitive_handle_count=0`; it
contains no handle/body/path. Partial transfer, process drift, duplicate role,
wrong owner or broker loss consumes the external-bind budget as failed and
returns an exact failure readback binding owner/lease identity, attempted and
accepted role-set digests, `owner_close_required=true | false` and a stable code,
but no handle/body/path. The producer quiesces the lease but must not
independently close it: close is serialized by the abort claim below. Unknown
transfer state is vector-wide `BURNED_UNKNOWN`, never failed-known.

The child bootstrap validates the bound roles under the owner lease before any
model/output access and returns exactly one authenticated body-free preflight:

```text
validate_job_child_external_input_v3(
    JOB_CHILD_EXTERNAL_INPUT_BOUND_READBACK_V3,
    FIXED_OWNER_PREFLIGHT_PROFILE_V1
) -> JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3
   | JOB_CHILD_EXTERNAL_INPUT_FAILED_CLOSED_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

Only `VALIDATED` permits the consumer to create its operation-owned Artifact.
Failure consumes preflight as failed, keeps Artifact handle/body, model and
consumer effect zero, and requires the serialized abort claim. Artifact creation
is not an out-of-vector consumer action. After VALIDATED the release budget must
first win this Task-072-owned CAS against abort:

```text
claim_job_child_artifact_prepare_v3(
    EXACT_CURRENT_TASK076_IN_FLIGHT_READBACK,
    JOB_CHILD_ARMED_READBACK_V3,
    JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3,
    JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3,
    FIXED_ARTIFACT_DECLARATION_V1 | FIXED_RECEIPT_ONLY_DECLARATION_V1
) -> JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3
   | JOB_CHILD_ABORT_PENDING_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3

commit_job_child_artifact_prepare_v3(
    JOB_CHILD_ARTIFACT_PREPARE_COMMIT_CONTEXT_V3 :=
        PREPARE_ONLY {
            JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3
        }
      | PREPARE_WITH_ABORT_WAIT {
            JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3,
            JOB_CHILD_ARTIFACT_ABORT_WAIT_READBACK_V3
        },
    JOB_ARTIFACT_HANDLE_PREPARED_READBACK_V1
      | JOB_ARTIFACT_KNOWN_NO_CREATE_READBACK_V1
      | JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1
) -> JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3
   | JOB_CHILD_ARTIFACT_PREPARE_FAILED_ABORT_REQUIRED_READBACK_V3
   | JOB_CHILD_ABORT_PENDING_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

Only the nonserializable `ARTIFACT_PREPARE_PENDING` lease authorizes exactly one
exclusive handle create. The commit binds exact physical identity and
`artifact_handle_created=true` while `artifact_body_write_started=false`,
`artifact_body_written=false` and `artifact_adopted=false`; or it binds a durable
known-no-create/collision/receipt-only result. Creation is a physical fact, not
an effect-zero claim. Collision creates nothing and preserves the foreign target.
`JOB_ARTIFACT_KNOWN_NO_CREATE_READBACK_V1` is issued only by the exact retained
exclusive-create operation with pinned ancestor/currentness and no opened handle;
a caller boolean, absence check or path reopen cannot mint it.
The commit context is selected by the exact durable vector, not by the caller.
`PREPARE_ONLY` is rejected without mutation once abort-wait is current;
`PREPARE_WITH_ABORT_WAIT` requires the exact same-vector pending lease and
abort-wait readback. `ARTIFACT_PREPARED` leaves release open for exactly release or abort;
`ARTIFACT_PREPARE_FAILED_ABORT_REQUIRED` consumes release as rejected and leaves
abort open; and a commit under `ABORT_WAITING_ARTIFACT_TRUTH` atomically consumes
release/abort as aborted and returns ABORT_PENDING. No outcome is retryable.

Abort cannot return `ABORT_PENDING` while Artifact prepare is `PENDING`. The
typed `PREPARE_IN_PROGRESS` abort request below supplies the exact pending
readback without claiming Artifact truth. It
atomically moves abort to `ABORT_WAITING_ARTIFACT_TRUTH`, blocks any release, and
returns `JOB_CHILD_ARTIFACT_ABORT_WAIT_READBACK_V3`. The same prepare commit then
binds exact truth and atomically returns `ABORT_PENDING`; no second abort claim is
needed or permitted. A caller
exception after Artifact-prepare entry must commit the exact observed result or
become vector-wide BURNED_UNKNOWN; it cannot omit the handle. `NONE` is never
accepted as Artifact truth. Before prepare entry, TASK-072 can issue only
`JOB_CHILD_ARTIFACT_NEVER_ENTERED_READBACK_V3`, derived from the exact release
budget state, and the prepare CAS cannot later win after abort.

Release is a two-step durable transition hidden behind one private operation.
Its first Task-072 CAS validates current IN_FLIGHT, the full lineage, a live
producer lease and `JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3`, then wins
`RELEASE_PENDING` against
`ABORT_PENDING`. That CAS consumes release and closes abort. Only the winner may
attach non-sensitive/Artifact handles, record RUNNING, and send one resume:

```text
attach_artifact_and_release_job_child_v3(
    EXACT_CURRENT_TASK076_IN_FLIGHT_READBACK,
    JOB_CHILD_ARMED_READBACK_V3,
    JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3,
    JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3,
    JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3,
    exact_private_non_sensitive_input_and_artifact_handles
) -> JOB_CHILD_STARTED_READBACK_V3
   | JOB_CHILD_RELEASE_REJECTED_ABORT_REQUIRED_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

An input rejected before exact operation/vector match has effect zero. A release
precondition rejection after durable entry consumes release as rejected and
leaves only abort open; it cannot be retried. Uncertainty after `RELEASE_PENDING` is
`BURNED_UNKNOWN`, because consumer entry may have occurred. Before release wins,
the producer lease cannot close without an earlier abort claim; after STARTED it
closes only through the exact child-terminal protocol. Release atomically rejects
an abort claim or non-live lease.

Every known bootstrap-phase cancellation/failure uses this claim/commit pair.
Its Artifact phase is a closed tagged union; fields from different variants
cannot be combined:

```text
JOB_CHILD_ABORT_ARTIFACT_PHASE_V3 :=
    BEFORE_PREPARE {
        current_phase:
            JOB_CHILD_EXTERNAL_INPUT_BOUND_READBACK_V3
              | JOB_CHILD_EXTERNAL_BINDING_FAILED_CLOSED_READBACK_V3
              | JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3
              | JOB_CHILD_EXTERNAL_INPUT_FAILED_CLOSED_READBACK_V3
              | NONE_IF_NEVER_BOUND,
        artifact_truth: JOB_CHILD_ARTIFACT_NEVER_ENTERED_READBACK_V3
    }
  | PREPARE_IN_PROGRESS {
        artifact_prepare_pending:
            JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3
    }
  | AFTER_PREPARE {
        current_phase:
            JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3
              | JOB_CHILD_ARTIFACT_PREPARE_FAILED_ABORT_REQUIRED_READBACK_V3
    }
  | AFTER_RELEASE_REJECTED {
        current_phase:
            JOB_CHILD_RELEASE_REJECTED_ABORT_REQUIRED_READBACK_V3
    }

claim_job_child_abort_v3(
    EXACT_CURRENT_TASK076_IN_FLIGHT_READBACK,
    JOB_CHILD_ARMED_READBACK_V3,
    JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3,
    JOB_CHILD_ABORT_ARTIFACT_PHASE_V3,
    closed_stable_reason
) -> JOB_CHILD_ABORT_PENDING_READBACK_V3
   | JOB_CHILD_ARTIFACT_ABORT_WAIT_READBACK_V3
   | JOB_CHILD_STARTED_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3

commit_job_child_abort_v3(
    JOB_CHILD_ABORT_PENDING_READBACK_V3,
    OWNER_EXTERNAL_INPUT_CLOSED_READBACK_V1 | NONE_IF_NO_ROLE_TRANSFER,
    JOB_CHILD_TERMINATED_WAITED_READBACK_V3
) -> JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

`PREPARE_IN_PROGRESS` is the only claim variant that can return
`JOB_CHILD_ARTIFACT_ABORT_WAIT_READBACK_V3`; its one-winner CAS closes the release
winner path, binds the pending lease, and asserts no Artifact truth. BEFORE_PREPARE
requires exact NEVER_ENTERED. AFTER_PREPARE and AFTER_RELEASE_REJECTED derive
truth only from their exact transitively bound phase readback. `ABORT_PENDING` is
the only instruction authorizing the named producer to close
or burn transferred roles. The ordinary abort claim—or the Artifact-prepare
commit when abort is waiting—atomically consumes abort, closes every still-open
bind/preflight/release budget, and wins against `RELEASE_PENDING`.
Every `JOB_CHILD_ABORT_PENDING_READBACK_V3` embeds a mandatory
`JOB_CHILD_ARTIFACT_ABORT_TRUTH_READBACK_V3`, derived only from the exact
NEVER_ENTERED, PREPARED or PREPARE_FAILED state already bound by the winning
claim or matching prepare commit. The abort commit consumes that embedded truth;
it accepts no caller-supplied reconstruction and never accepts `NONE`.
After producer close, TASK-072 terminates and waits the exact child before commit.
`BOOTSTRAP_ABORTED` records `consumer_effect_started=false`, model/body-write
zero, the truthful `child_process_created=true`, and the truthful
`artifact_handle_created=true | false` plus exact retained Artifact identity when
created. It never labels an existing handle as no Artifact. The operation-owned
file remains preserved/quarantined for its separate lifecycle; TASK-076 does not
delete it during abort. Owner close, terminate/wait or Artifact-truth uncertainty
is vector-wide `BURNED_UNKNOWN`.

`BURNED_UNKNOWN` closes effect authority but never disables containment. TASK-072
exposes one idempotent recovery-only operation:

```text
contain_burned_unknown_job_child_v3(
    EXACT_JOB_CHILD_BURNED_UNKNOWN_READBACK_V3,
    exact_original_project_job_operation_coordinate,
    TASK076_RECOVERY_CONTAINMENT_PROFILE_V1
) -> JOB_CHILD_UNKNOWN_CONTAINMENT_READBACK_V3
```

The operation can exact-query the named producer lease and child Job Object,
issue `OWNER_EXTERNAL_INPUT_RECOVERY_REVOKE_V1` for every attempted/accepted
role, close the sole containment handle or terminate the exact Job Object, and
wait for the child. It can run after Product/broker restart and after any bind,
preflight, Artifact-prepare, release or abort uncertainty. It can never bind,
preflight, attach, release, resume, read a body, delete an Artifact, or return
FAILED_KNOWN/SUCCEEDED. The readback records owner roles as
`REVOKED_CONFIRMED | UNKNOWN`, child as
`TERMINATED_WAITED | KILL_ON_CLOSE_CONFIRMED | UNKNOWN`, and exact retained
Artifact truth when available. The Job outcome remains BURNED_UNKNOWN even when
containment is confirmed. Same-operation replay is an idempotent query; a wrong
operation/vector has effect zero. Project/Job-head advancement cannot authorize
effect but does not block containment of the exact original process/lease.
Unknown containment is retried only as the same
idempotent safety action under explicit recovery policy, never automatically and
never as child execution or state repair.

Failure to publish local state, Artifact collision, cancellation or exception
at any bootstrap/pre-release seam must use the applicable abort path. Product,
broker or worker restart invalidates every nonterminal V3 live channel. Recovery
may exact-query and finish an already durable `ABORT_PENDING` claim; it may never
begin a new bind, preflight, release or owner close. A delayed bind/release after
ABORTED is rejected and any presented handles are closed/burned by their owner.

Effect-bearing completion requires a distinct non-aliased terminal ABI:

```text
read_job_child_terminal_v3(
    JOB_CHILD_STARTED_READBACK_V3,
    exact_child_exit_and_result_coordinate,
    exact_owner_lease_terminal_readback,
    exact_artifact_validation_readback | exact_receipt_only_result
) -> JOB_CHILD_TERMINAL_READBACK_V3
   | JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

`JOB_CHILD_TERMINAL_READBACK_V3` binds the exact ARMED, BOOTSTRAP_WAITING,
BOUND, VALIDATED, ARTIFACT_PREPARED and STARTED identities; all five terminal
budget states; child process/token/session/image/build and exit/result; owner
lease close/terminal;
Artifact handle/body/validator/durability truth; and consumer result digest. It
contains no sensitive handle/body/path. Missing lineage, owner terminal,
Artifact truth or semantic result is `BURNED_UNKNOWN`, not V2 and not success.

### 7.9 `SECURE_JOB_ARTIFACT_V1`

V1 supports exactly zero or one regular single-file Artifact per Job terminal.
Directory trees, multiple files, symlinks, reparse points and hardlinks are
unsupported.

Before child start the consumer supplies a private Artifact declaration:

- opaque artifact role/class and exact validator/version;
- pre-existing trusted parent binding;
- operation-owned no-replace relative coordinate;
- maximum/minimum byte size and expected content/media profile;
- expected child write/read handle roles;
- retention/privacy policy digest;
- whether a receipt-only external artifact is required instead of a local file.

For a local file the Product creates one exclusive, non-inheritable handle,
pins ancestor/security/identity, and gives the child only a restricted duplicate
through TASK-072. The child never chooses a path. After child exit the parent
retains the handle, flushes it, performs the fixed consumer validator, computes
exact bytes/hash, and revalidates identity/currentness. Directory durability is
required. Reopening by path is not the authority proof.

TASK-076 then publishes `JOB_ARTIFACT_MANIFEST_V1` through TASK-068. It binds:

- Job/event/child/action identities;
- Artifact role/class/validator and content profile;
- exact bytes/hash/physical identity;
- parent/ancestor/security and durability receipts;
- retention/privacy and Product/consumer/build identities;
- `asset_published=false`, `timeline_mutated=false`,
  `provider_authorized=false`, `authority_created=false`.

The manifest cannot publish or promote a Product Asset. A consumer-specific
owner performs any later adoption under its own authority.

For receipt-only external artifacts, no local file is invented. The exact
external owner receipt and validator result are bound instead.

### 7.10 `JOB_TERMINAL_BINDING_V2`

`SUCCEEDED` requires:

- exact current `IN_FLIGHT` event;
- exactly one version-discriminated TASK-072 committed child terminal:
  `JOB_CHILD_TERMINAL_READBACK_V2` for the ordinary path or
  `JOB_CHILD_TERMINAL_READBACK_V3` for the sensitive-input path; neither may be
  converted, aliased or accepted by equal public fields;
- zero-or-one exact Artifact manifest/readback according to the profile;
- consumer semantic result validator PASS;
- final Project/input/security/build currentness;
- immutable terminal event publication/readback;
- later TASK-043 current-head binding.

If the effect may have occurred but any proof is missing, the terminal is
`BURNED_UNKNOWN`, not `FAILED` or `SUCCEEDED`. A later exact consumer-owned
readback may append a reconciliation event, but cannot rewrite the old terminal
or replay the child.

### 7.11 `DURABLE_PRODUCT_JOB_PUBLIC_STATUS_V2`

The public projection is derived only from a fresh TASK-043 currentness readback
plus exact TASK-068 event readback. Closed fields are:

- schema/version, opaque Job ID and kind;
- bounded state, progress/count and stable reason code;
- safe-cancel and recovery-policy enum;
- Artifact-present/count/validated booleans;
- opaque event/result digests;
- `authority_created=false`, `effect_authorized=false`,
  `currentness_selected=false` for the projection itself.

It contains no path, input/output body, command, argv, environment, child output,
OS error, user/account, SID, secret/token, Provider/model detail or Artifact
content. A public status object is never accepted by a transition API.

### 7.12 Early fixture contract

The four exact fixture files in section 5 supply static positive and negative
vectors for each registered Job kind. The V3 child fixture freezes every legal
V3 state/receipt shape, the named-owner slot, no-hook rules and every
create/bind/preflight/Artifact-prepare/release/abort rejection code, the exact
BOOTSTRAP_REJECTED five-budget token vector and containment-only results. Every
fixture declares:

- `fixture_only=true`;
- `authority_created=false`;
- `task068_real_io=false`;
- `task043_project_currentness=false`;
- `task072_child_executed=false`;
- `bootstrap_child_created=false` and a separate closed
  `simulated_expected_bootstrap_state` field;
- `external_sensitive_body_read=false`;
- `artifact_body_written=false`;
- `production_eligible=false`;
- fixed fake identities/builds/bytes/hashes and expected deltas.

Consumers may compile against the fixture. Fixture PASS cannot satisfy Product
currentness, child execution, Artifact, installed/native or Production gates.

## 8. Strict schema and resource limits

Every authority document is canonical strict UTF-8 JSON and is decoded before
canonicalization/hash/semantic validation. It rejects:

- duplicate keys at every depth, equal or different;
- NaN, Infinity and negative Infinity;
- BOM, trailing non-whitespace, invalid UTF-8 and disallowed controls;
- non-built-in JSON values;
- unknown/missing fields;
- strings over 1024 code points unless a smaller field limit applies;
- depth over 12, objects over 128 members, arrays over 4096 items;
- total nodes over 65,536;
- reservation/event/manifest documents over 256 KiB;
- aggregate exact-coordinate graph plans over 4096 records or 16 MiB.

The decoder never canonicalizes/hashes/logs an unbounded or rejected tree first.
All parse/resource failures become stable body-free effect-zero codes. Ambiguous
documents are preserved and are never repaired, rewritten or deleted.

Artifact ceilings are consumer-profile specific and are checked before child
start and during/after write. Size/quota breach burns the child operation and
cannot publish a success terminal.

## 9. Transaction and lock order

Every state transition is a two-owner publish/select sequence:

1. consume the exact private consumer Job plan or the prior transition lease;
2. obtain and pin a fresh TASK-043 Project/current-Job readback;
3. validate the exact TASK-068 predecessor/event graph and namespace allow-list;
4. acquire the TASK-076 operation lease through TASK-068 secure existing/initial
   semantics; a create-race loser is freshly classified and not auto-retried;
5. revalidate the pinned Project/input/security currentness;
6. publish/read back exactly one next immutable candidate event;
7. release the TASK-076 operation lease without releasing pinned input handles;
8. ask TASK-043 to CAS-bind that exact candidate against the expected prior
   Project bytes, physical identity, revision and Job head;
9. obtain a fresh `PROJECT_JOB_CURRENTNESS_READBACK_V2` selecting the candidate;
10. only that selected readback can authorize preparation of the next event.

Failure after step 6 leaves an unselected orphan and grants no next effect.
TASK-076 never reports the candidate as current, republishes it, or chooses it by
scan. TASK-043 may later bind only that exact candidate through its own recovery
policy and unchanged expected predecessor; otherwise it appends a separately
authorized compensation in a later Project revision.

For a child effect the phase order is stricter:

```text
READY selected by TASK-043
 -> TASK-072 non-authoritative JOB_DISPATCH_PLAN_V2 built for exact READY
 -> DISPATCHING event published and selected by TASK-043
 -> TASK-072 issue_and_arm atomically issues/burns and records child ARMED
 -> TASK-076 IN_FLIGHT event published and selected by TASK-043
 -> operation-owned Artifact handle created exclusively (when required)
 -> TASK-072 attach_and_start atomically validates/attaches restricted handles,
    records child IN_FLIGHT and starts the fixed child once
 -> Artifact/child terminal validated
 -> terminal event published and selected by TASK-043
```

The sensitive-input V3 profile replaces only the final attach/start segment:

```text
selected TASK-076 IN_FLIGHT + TASK-072 ARMED_V3
 -> create fixed broker-bootstrap child (consumer/model/Artifact-handle/body zero)
 -> durable BOOTSTRAP_WAITING readback with exact process identity
 -> named producer transfers sensitive roles directly to exact child broker
 -> durable EXTERNAL_INPUT_BOUND readback; parent handle count zero
 -> child broker validates complete role set under producer lease
 -> durable EXTERNAL_INPUT_VALIDATED readback; model/Artifact-handle/body zero
 -> release-budget ARTIFACT_PREPARE_PENDING wins against abort
 -> abort request during PENDING uses PREPARE_IN_PROGRESS(PENDING) and either
    loses, or durably returns ABORT_WAITING_ARTIFACT_TRUTH with release blocked
 -> operation-owned Artifact handle created exclusively
 -> the same pending lease commits exact created/no-create physical truth;
    PREPARE_WITH_ABORT_WAIT returns truth-embedded ABORT_PENDING, otherwise
    ARTIFACT_PREPARED leaves release open
 -> release CAS wins against abort, consumes release, records RUNNING,
    attaches only non-sensitive/Artifact handles and releases consumer code once
 -> JOB_CHILD_TERMINAL_READBACK_V3 binds the complete V3 lineage
 -> Artifact/child terminal validated
```

Before bootstrap creation, exact pre-bootstrap or orphan abort consumes every V3
budget and proves process/Artifact/model/consumer effect zero. After bootstrap
creation, an abort claim must win or lose against release under TASK-072 CAS.
During Artifact prepare, abort first enters ABORT_WAITING_ARTIFACT_TRUTH and
cannot claim completion until the prepare lease commits exact truth.
Exact BOOTSTRAP_ABORTED proves consumer/model/body-write effect zero and
truthfully preserves both `child_process_created=true` and the separate
`artifact_handle_created=true | false` fact. Unknown owner-close, terminate,
Artifact-handle truth or release state is BURNED_UNKNOWN. Empty/missing content
is never used as proof of no Artifact-handle creation.

If TASK-072 arm/burn succeeds but TASK-076 `IN_FLIGHT` cannot become current, child
and Artifact creation stay zero and recovery classifies
`BURNED_UNKNOWN_CANDIDATE_REQUIRED`; it is not yet current. Exact broker query
is allowed but replay is not. If Artifact creation/validation fails after
selected TASK-076 IN_FLIGHT, V2 must call its serialized `abort_armed` ABI; V3
must use pre-bootstrap abort or the bootstrap abort claim/commit matching its
exact current phase. Exact profile-matching ABORTED permits an IN_FLIGHT ->
FAILED_KNOWN candidate with consumer effect zero and truthful Artifact-handle
facts; abort crash/unknown permits only an IN_FLIGHT -> BURNED_UNKNOWN candidate
after exact broker query. No terminal candidate may race ahead of
consuming/classifying every profile budget.

`BURNED_UNKNOWN` is not current merely because the broker burned. Recovery pins
the still-current `DISPATCHING` readback, exact TASK-072 burned/ARMED broker
readback and the planned TASK-076 `IN_FLIGHT` coordinate:

- if the planned `IN_FLIGHT` candidate is absent, publish a predecessor-bound
  `BURNED_UNKNOWN` candidate and ask TASK-043 to CAS-select it;
- if the exact planned `IN_FLIGHT` candidate exists, first obtain the exact
  profile-matching `JOB_CHILD_ORPHAN_ABORTED_READBACK_V2` or
  `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3` while DISPATCHING remains current. The
  V3 readback atomically closes all five budgets and proves process/Artifact zero.
  Only then may TASK-043 CAS-select that exact orphan against unchanged
  DISPATCHING, followed by an `IN_FLIGHT -> FAILED_KNOWN` candidate/readback. If
  orphan abort is unknown, currentness changes or another actor selects the
  orphan, stop and exact-query; never precompute/select a terminal or claim
  child/artifact zero;
- if another body/identity occupies the slot, or Project/head changed, STOP and
  preserve. A competing terminal is never published into the orphan slot.

A known TASK-072 pre-effect `REJECTED` readback uses the legal
`DISPATCHING -> FAILED_KNOWN` sequence. TASK-072 issuance failure while `READY`
cannot occur because `JOB_DISPATCH_PLAN_V2` has no ticket/channel/budget. A plan
validation rejection may use `READY -> FAILED_KNOWN`; plan construction loss or
DISPATCHING publish/CAS failure discards the non-authoritative plan and leaves
READY current. Every terminal case is immutable candidate then TASK-043
CAS/readback; a TASK-072 classification alone is never current Job state.

No mutable cross-owner writer locks are nested. TASK-043 owns and releases each
Project CAS transaction; TASK-076 owns and releases each immutable publish
lease; TASK-072 owns its live broker transaction; the consumer owns the retained
Artifact handle. Pinned read handles/identity snapshots may span phases, but a
writer lock never spans a Human wait, child execution or another owner's writer
transaction. Before every phase the ordered logical currentness is revalidated:

```text
TASK-043 selected Project/Job head
 -> TASK-076 immutable predecessor/current candidate
 -> TASK-072 ticket/child state
 -> named owner external-binding/preflight state (V3 only)
 -> consumer Artifact handle state
```

Any reverse dependency request, stale readback or phase drift fails closed.

## 10. Recovery and restart

- Restart performs no directory scan and mutates no event.
- Recovery begins from an exact Project/Job head supplied by TASK-043.
- `RESERVED/PREPARED/READY` from another broker session is expired/burned; no
  child effect is inferred.
- `DISPATCHING/IN_FLIGHT` without an exact known terminal is classified
  `BURNED_UNKNOWN_CANDIDATE_REQUIRED`; restart itself appends/selects nothing.
  Only the legal predecessor-specific recovery sequence in section 9 can make
  `BURNED_UNKNOWN` current; no replay.
- V3 restart never starts bind, preflight, release or a fresh normal owner-close/
  abort transition. Recovery-only `contain_burned_unknown_job_child_v3` remains
  available and cannot release/resume or change the BURNED_UNKNOWN outcome. An
  exact already-durable `ABORT_PENDING` may finish the same claim using its
  embedded Artifact truth plus bound owner-close and terminate/wait coordinates;
  missing/changed evidence is BURNED_UNKNOWN. A trusted Task-072 same-vector
  continuation query may return an already-live private continuation for durable
  `ARTIFACT_PREPARE_PENDING` or `ABORT_WAITING_ARTIFACT_TRUTH` only while the
  original broker session and exact retained operation/handle remain live. It
  never reissues a lease, creates a budget or changes the tagged variant. After a
  broker/Product restart there is no live continuation and the vector becomes
  BURNED_UNKNOWN plus containment. `ABORT_WAITING_ARTIFACT_TRUTH` may advance only
  through `PREPARE_WITH_ABORT_WAIT` using the same pending lease and exact
  retained-operation created/no-create readback. A lost handle, uncommitted
  truth, different vector or changed Artifact identity likewise becomes
  BURNED_UNKNOWN plus containment and the observed file is preserved. A
  DISPATCHING-current exact unselected orphan may use only
  `abort_armed_orphan_job_child_v3`, whose CAS proves process-create was never
  entered and closes all five budgets. Every other pre-bootstrap or
  `BOOTSTRAP_WAITING/BOUND/VALIDATED` state without a pre-crash abort claim is
  BURNED_UNKNOWN, invokes recovery containment, and is never rebound or released.
- V3 known `BOOTSTRAP_REJECTED`, `PREBOOTSTRAP_ABORTED`, `ORPHAN_ABORTED` and
  `BOOTSTRAP_ABORTED` are terminal five-budget vectors. Recovery only queries
  their exact same-operation readback; it does not invoke another abort.
- V3 `RELEASED/RUNNING` is never reattached or resumed. Missing terminal is
  BURNED_UNKNOWN until exact `JOB_CHILD_TERMINAL_READBACK_V3` or a separately
  authorized child/Artifact reconciliation proves otherwise.
- A committed TASK-072 terminal plus exact Artifact may be reconciled only by a
  consumer-specific semantic verifier and a new immutable reconciliation event.
- A terminal event not yet selected by TASK-043 remains an orphan until TASK-043
  either binds that exact planned event or binds a separately authorized
  compensation/reconciliation event. TASK-076 never chooses it by scan.
- Missing event, fork, cycle, duplicate coordinate, wrong physical identity,
  ambiguous JSON or unknown file is STOP+preserve.
- Legacy `jobs.json` is not imported or repaired automatically. A migration
  requires a separate Task with an exact source snapshot and no-delete policy.
- Cleanup is not recovery. Published records and Artifacts remain until a
  separately allocated retention/GC Task and Human Gate.

## 11. Fault matrix

| Seam | Required result | Effect/recovery rule |
|---|---|---|
| invalid plan/currentness | `REJECTED` | reservation/event/child/artifact delta zero |
| secure lease race/link/DACL drift | `SECURITY_STOP` | preserve all; retry zero |
| reservation collision | `JOB_OPERATION_COLLISION` | winner preserved; child zero |
| PREPARED event publish/readback failure | completion unknown | child zero; exact records preserved |
| TASK043 currentness bind failure | unselected orphan | candidate grants no next effect; preserve |
| dispatch-plan validation exact REJECTED at READY | `FAILED_KNOWN` candidate | current only after publish + TASK043 CAS; child zero |
| dispatch-plan construction loss or DISPATCHING CAS failure | READY current / orphan candidate | no authority exists; reconstruct same plan or bind exact orphan only |
| TASK072 arm/burn succeeds, planned TASK076 IN_FLIGHT absent | `BURNED_UNKNOWN_CANDIDATE_REQUIRED` | child/artifact zero; DISPATCHING -> terminal candidate + TASK043 CAS |
| TASK072 arm/burn succeeds, exact TASK076 IN_FLIGHT orphan exists | recovery abort required | ORPHAN_ABORTED while DISPATCHING current -> select exact orphan -> FAILED_KNOWN; unknown/currentness race claims no child/artifact-zero |
| TASK072 arm/burn succeeds, TASK076 IN_FLIGHT slot collision | `JOB_RECEIPT_COLLISION` | STOP+preserve; publish/select/delete zero |
| TASK072 exact pre-effect REJECTED at DISPATCHING | `FAILED_KNOWN` candidate | current only after publish + TASK043 CAS; child/artifact zero |
| V2 Artifact create/validation/collision fails after selected TASK076 IN_FLIGHT while broker ARMED; abort wins | `FAILED_KNOWN` candidate | exact V2 ABORTED proves child/create/start/effect zero; preserve foreign target |
| abort_armed crashes/returns unknown, or attach_and_start wins its race | `BURNED_UNKNOWN` candidate | exact broker query/classification; never claim no-effect or retry |
| attach_and_start exact pre-create rejection | Job `FAILED_KNOWN` candidate | predecessor is current TASK076 IN_FLIGHT; child effect zero; publish + TASK043 CAS required |
| attach_and_start uncertainty after start-budget entry | `BURNED_UNKNOWN` candidate | predecessor is current TASK076 IN_FLIGHT; exact broker query only; no reattach/start |
| V3 exact IN_FLIGHT candidate remains orphan | `ORPHAN_ABORTED_V3 | BURNED_UNKNOWN` | while DISPATCHING current, V3 orphan abort consumes all five budgets and proves process/Artifact/effect zero before selection; V2 cannot substitute |
| V3 selected IN_FLIGHT cancellation before create | `PREBOOTSTRAP_ABORTED_V3 | BURNED_UNKNOWN` | CAS wins against create, consumes all five budgets and proves process/Artifact/effect zero |
| V3 bootstrap child create/attestation fails before process identity commit | `BOOTSTRAP_REJECTED | BURNED_UNKNOWN` | REJECTED only from known no-process atomic closure of all five budgets; any possible process is BURNED_UNKNOWN |
| V3 known-no-process BOOTSTRAP_REJECTED | exact terminal vector | create=`CONSUMED_REJECTED`; bind/preflight/release/abort=`CLOSED_REJECTED`; no other token is valid |
| V3 owner transfer is partial, wrong-process or broker-lost | `EXTERNAL_BINDING_FAILED_CLOSED` then abort claim | owner quiesces but closes only after ABORT_PENDING wins against release; parent handle zero; unknown transfer is BURNED_UNKNOWN |
| V3 external preflight fails | `EXTERNAL_INPUT_FAILED_CLOSED` then abort claim | Artifact handle/body/model/consumer effect zero; owner close and child termination occur only under ABORT_PENDING |
| V3 abort races Artifact prepare | exact typed prepare/abort substate winner | PREPARE_IN_PROGRESS(PENDING) can alone produce ABORT_WAITING_ARTIFACT_TRUTH and block release; same-lease PREPARE_WITH_ABORT_WAIT commits created/no-create and returns truth-embedded ABORT_PENDING; NONE is invalid |
| V3 Artifact handle create/collision/local state fails after validated preflight | prepare commit then abort claim/commit | BOOTSTRAP_ABORTED truthfully binds handle-created true/false and body-write/effect zero; foreign target preserved; unknown is BURNED_UNKNOWN plus containment |
| V3 release precondition rejects | `RELEASE_REJECTED_ABORT_REQUIRED` | release cannot retry; abort remains the sole known closure |
| V3 abort claim races release | exact `ABORT_PENDING` or `RELEASE_PENDING` winner | loser cannot close owner lease, attach, resume or claim no-effect |
| V3 crash during owner close or child terminate/wait after ABORT_PENDING | exact same-claim completion or `BURNED_UNKNOWN` | no new bind/preflight/release/abort; created Artifact truth preserved |
| V3 release receipt or terminal lineage is lost | `BURNED_UNKNOWN` until exact V3 terminal | no second bind/release/resume and no V2 terminal substitution |
| V3 any vector-wide BURNED_UNKNOWN with possible child/role | recovery containment | producer recovery revoke + Job-object kill/terminate/wait; outcome remains BURNED_UNKNOWN; release/resume/delete zero |
| wrong/cross-operation vector before any V3 method entry | stable effect-zero reject | victim vector bytes/revision unchanged |
| exact matching V3 method throws after durable budget entry | exact budget/vector BURNED_UNKNOWN | only matched operation changes; recovery containment as required |
| child failure after entry | `BURNED_UNKNOWN` | preserve; no retry |
| Artifact create collision while broker ARMED | `ARTIFACT_COLLISION_STOP` reason + exact abort classification | foreign winner preserved; FAILED_KNOWN only from ABORTED, otherwise BURNED_UNKNOWN |
| Artifact flush/validate/readback failure | `BURNED_UNKNOWN` | success terminal zero |
| terminal event failure after effect | `BURNED_UNKNOWN` | no replay; exact readback reconciliation only |
| same exact current committed query | audit `DUPLICATE` | all deltas zero |
| different terminal/body/identity | `JOB_RECEIPT_COLLISION` | STOP+preserve |
| restart | exact-state classification | scan/write/delete zero |
| cleanup failure | stable warning only | correctness/currentness unchanged |

## 12. Negative matrix

Each negative independently asserts reservation/event count, TASK-043 revision
delta, TASK-072 child count, exact TASK-072 budget-vector bytes/revision delta,
Artifact delta and unrelated overwrite/delete.

### T76-AUTH

- direct/copy/replace/pickle/deserialized/subclass/duck public Job/collection;
- module token/sentinel and recomputed valid self-hash;
- public request/status/legacy `operation_identity` used for issuance;
- caller-selected Project/root/path/Job/event/ticket/time/backend;
- fake TASK-068/TASK-043/TASK-072 verifier or test clock in Production;
- caller callback/generic hook/fake owner adapter used as a V3 external-binding
  producer, or caller-selected PID/process/handle/role set;
- extra/missing/wrong producer/action/profile/version;
- same semantic effect with new request/reservation/ticket IDs.

Expected: reservation/event/child/artifact/Project mutation zero.

### T76-IO-JSON

- Job root/lock/event/artifact manifest reparse/hardlink/ancestor/DACL drift;
- stat-open/read-post and same-bytes/different-inode swaps;
- absent target appears identical/different;
- temp/target prepublish/postpublish swap;
- file/directory fsync and pinned readback failure;
- top/nested duplicate keys equal/different;
- NaN/Infinity, BOM, trailing, invalid UTF-8/control;
- deep/wide/huge/node/string/document ceiling breach;
- foreign temp/artifact replacement and cleanup attempt.

Expected: ambiguous input preserved; unrelated overwrite/delete zero.

### T76-CURRENTNESS

- stale/cross-Project/cross-install TASK-043 readback;
- first reservation with forged/stale/cross-Project `ABSENT_JOB_HEAD`, or
  concurrent null-head-to-RESERVED CAS;
- equal Project ID/hash with different physical manifest identity;
- event published but not selected by TASK-043;
- forged Project revision/head or scan-highest/latest event;
- missing predecessor, fork, cycle, duplicate sequence, unknown event;
- Project advances between prepare, ticket, child, Artifact and terminal;
- candidate event published but TASK-043 CAS bind loses a Project/Job-head race;
- DISPATCHING selected but TASK-072 burn fails, or TASK-072 burn succeeds while
  TASK-076 IN_FLIGHT remains orphan/unselected;
- exact orphan IN_FLIGHT exists but recovery publishes a competing
  BURNED_UNKNOWN at the same predecessor/slot instead of selecting the orphan;
- forged/replayed `JOB_DISPATCH_PLAN_V2`, or a plan carrying a live ticket,
  channel, budget or serialized effect authority;
- direct `issue_and_arm_job_child_v2` from READY, or with a stale/noncurrent
  DISPATCHING readback;
- plan validation rejection without the matching READY -> FAILED_KNOWN
  candidate and TASK-043 CAS;
- direct DISPATCHING-to-terminal without exact TASK-072 REJECTED/burned readback,
  or public `BURNED_UNKNOWN` before terminal candidate TASK-043 selection;
- old TASK-043 generic load/save result treated as V2 readback.

Expected: next effect/current status zero; orphan preserved.

### T76-CHILD

- public/receipt-only TASK-072 result;
- any redeemable ticket/channel before exact DISPATCHING selection;
- forged/replayed/copied `JOB_DISPATCH_PLAN_V2`, or a plan treated as
  effect-bearing authority;
- direct arm from READY, or `issue_and_arm_job_child_v2` with a
  stale/cross-Job/cross-Project DISPATCHING readback;
- `attach_and_start_job_child_v2` before selected TASK076 IN_FLIGHT, without an
  exact ARMED readback, with stale/cross-operation handles, or called twice;
- V3 create-bootstrap before selected IN_FLIGHT, with a V2 ARMED readback, or
  with extra script/model/input/output/Artifact handles;
- for each V3 create/bind/preflight/Artifact-prepare/release/abort method: wrong,
  stale or cross-operation vector presented before identity match; victim vector
  bytes/revision must remain exact unchanged;
- for each same method: authenticated exact-vector durable entry followed by
  injected exception/uncertainty; exactly that vector/budget becomes
  BURNED_UNKNOWN and no other operation changes;
- V3 orphan selected before exact `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3`, V2
  orphan receipt substituted, or orphan abort after selection/create entry;
- V3 cancel before bootstrap without exact `PREBOOTSTRAP_ABORTED`, create and
  pre-bootstrap abort both winning, or any of five budgets remaining open after
  orphan/pre-bootstrap/rejected terminal;
- forged/copied/wrong-process `BOOTSTRAP_WAITING`, owner-bound or validated
  readback; equal fields/hashes without the live child broker;
- V3 owner binding missing/wrong ABI/acceptance, wrong producer, partial role
  set, parent handle possession, duplicate/cross-operation lease or process swap;
- V3 child preflight skipped, run after Artifact creation, or validation receipt
  forged from public metadata;
- V3 Artifact created before external input VALIDATED, or release called without
  exact Artifact handle/currentness and all prior readbacks;
- V3 Artifact create without `ARTIFACT_PREPARE_PENDING`, abort reports NONE after
  prepare entry, BEFORE_PREPARE used during PENDING, PREPARE_IN_PROGRESS with a
  wrong/cross-vector pending readback, delayed create after abort, abort during
  PENDING returns final ABORTED before exact same-lease prepare commit, a
  PREPARE_ONLY commit bypasses current abort-wait, or release bypasses PREPARED;
- V3 producer close before `ABORT_PENDING`, abort claim omitting a partial/failed
  binding outcome, close crash then new claim, or release accepting a stale/
  closing owner lease;
- delayed bind/release after ABORTED, release and abort both winning, or restart
  followed by a new bind/preflight/release/abort rather than exact-querying an
  existing abort claim;
- BURNED_UNKNOWN containment accepts a public/wrong operation, binds/releases/
  resumes, returns FAILED_KNOWN/SUCCEEDED, deletes an Artifact, or fails to revoke
  owner roles and terminate/wait the exact Job Object where available;
- local terminal publication after Artifact failure without exact
  profile-matching V2 ABORTED or V3 PREBOOTSTRAP/BOOTSTRAP_ABORTED readback, or
  without exact broker unknown classification;
- delayed/concurrent attach-and-start racing `abort_armed_job_child_v2`, both
  reporting winner, or attach succeeding after ABORTED;
- wrong/cross command, action, config, child, process, build, user/session;
- child terminal without durable IN_FLIGHT;
- direct child invocation or copied handle/config;
- double/concurrent dispatch, exception/cancel/timeout then reuse;
- crash before/after dispatch-plan construction, DISPATCHING selection, atomic
  issue-and-arm, TASK076 IN_FLIGHT candidate publication/selection, Artifact
  create, attach-and-start,
  child start, effect and terminal;
- V3 crash before/after bootstrap process identity commit, owner transfer first/
  second role, binding readback, child preflight, abort claim, owner close,
  terminate/wait, abort commit, Artifact-handle create, release claim, RUNNING
  readback and consumer-code release;
- atomic issue-and-arm burn with planned IN_FLIGHT absent, exact orphan
  present, or a colliding event at the expected predecessor/slot;
- exact orphan selected before the profile-matching V2/V3 ORPHAN_ABORTED,
  profile-crossed abort, orphan abort attempted after selection, or delayed
  create/attach/start winning the gap;
- Product/broker restart with ARMED state followed by reattachment/start;
- abort crash followed by retry, public/local reason treated as abort proof, or
  FAILED_KNOWN selected before ARMED budget classification;
- child start attempted before both TASK-072 and TASK-043-selected TASK-076
  IN_FLIGHT readbacks;
- exact effect-zero child-process start failure whose terminal candidate does
  not name the current selected IN_FLIGHT predecessor;
- success exit code with missing/wrong consumer result digest;
- V3 child result promoted without exact `JOB_CHILD_TERMINAL_READBACK_V3`, with
  missing/wrong ARMED/BOOTSTRAP/BOUND/VALIDATED/STARTED/owner-lease/Artifact
  lineage, or by converting a V2 terminal;
- BURNED_UNKNOWN reclassified as FAIL/SUCCESS or replayed;
- TASK-072 REJECTED/BURNED classification returned publicly as current Job state
  before the matching immutable terminal is TASK-043-selected.

Expected: child effect exact 0/1; no blind retry.

### T76-ARTIFACT

- undeclared, extra, multi-file or directory-tree output;
- symlink/reparse/hardlink/nonregular/zero-link Artifact;
- target race identical/different and same bytes/different inode;
- child closes then path/foreign replacement;
- wrong class/validator/profile/size/content digest;
- flush/durability/readback failure;
- manifest without child terminal or child terminal without Artifact;
- receipt-only profile given a local file or local profile given receipt-only;
- V3 pre-release abort reports Artifact zero after a handle was created, omits
  exact handle identity, or deletes/rewrites the retained operation-owned file;
- Artifact manifest treated as Asset/Timeline/provider authority;
- failure/unknown followed by delete/restore/overwrite.

Expected: success/current Project binding zero; foreign artifacts preserved.

### T76-RECOVERY-PRIVACY

- restart scan and automatic `UNKNOWN` rewrite;
- caller `ACCEPT_PROVEN_SUCCESS` without exact semantic readback;
- old jobs.json equality/adoption/migration;
- terminal receipt loss then child replay;
- random-ID retry after unresolved reservation/event;
- path/input/output/command/argv/env/OS error/secret in public status/log/stdout;
- malformed raw exception or offending value echo;
- fixture result promoted to real/native/current status.

Expected: service remains available, state preserved, body-free stable result.

## 13. Product UX contract

Public Japanese states are derived from exact currentness only:

- `待機中`
- `事前確認中`
- `実行準備完了`
- `開始しています`
- `実行中`
- `完了`
- `失敗しました`
- `安全にキャンセルしました`
- `結果を確認できないため再実行できません`
- `利用者の確認が必要です`

`再実行` is never offered for `DISPATCHING`, `IN_FLIGHT` or
`BURNED_UNKNOWN`. A safe fresh preparation action is shown only after the
consumer supplies an exact predecessor-bound no-effect reconciliation.

The UI never exposes a path, raw Job/event ID suitable for replay, hash body,
ticket, command, process, backend, environment, OS error, user identity, secret
or Artifact content.

## 14. Verification plan

### Static and focused

- strict schema/mirror exact hash and canonical bytes;
- closed Job/action/artifact profile registries;
- stable semantic keys and random-ID collision tests;
- immutable predecessor/fork/cycle/sequence property tests;
- ABSENT_JOB_HEAD -> RESERVED and DISPATCHING terminal edge property tests;
- READY dispatch-plan validation terminal edge, atomic post-DISPATCHING
  issue-and-arm, ARMED restart invalidation, one-winner abort-vs-attach/start, and
  orphan-abort-before-select-before-terminal property tests;
- V3 process-create/external-bind/preflight/release/abort budget exhaustive
  state-machine tests, including Artifact-prepare substates, exact
  BOOTSTRAP_REJECTED token vector and terminal-vector no-open-budget invariants;
- per-method wrong/cross-vector victim byte/revision unchanged tests and exact
  matching post-entry exception single-vector burn tests;
- V3 orphan and pre-bootstrap abort one-winner property tests against candidate
  selection and process creation;
- exact allowlisted owner-slot adapter tests with generic hook/callback/PID/
  handle injection rejected before arm;
- direct owner-to-child broker all-or-none binding, parent sensitive-handle
  count zero and external preflight-before-Artifact property tests;
- V3 ABORT_PENDING claim -> owner close -> terminate/wait -> abort commit versus
  RELEASE_PENDING one-winner tests, including partial binding at every seam;
- V3 Artifact-handle-created versus body-write/effect truth property tests;
- typed BEFORE_PREPARE/PREPARE_IN_PROGRESS/AFTER_PREPARE/AFTER_RELEASE_REJECTED
  union construction and non-interchangeability tests;
- Artifact-prepare pending/commit versus abort-request one-winner property tests,
  including PENDING -> ABORT_WAIT -> same-lease truth commit -> ABORT_PENDING,
  release blocking, wrong-context effect zero, caller-crash continuation while
  the original broker remains live, and broker/Product-restart containment;
- BURNED_UNKNOWN recovery containment never-release/resume/state-reclassify
  property tests;
- exact V3 terminal lineage and V2/V3 non-alias property tests;
- TASK-068/TASK-043/TASK-072 fixture adapters;
- state/fault/recovery table exhaustive transition tests;
- strict JSON/resource-boundary tests before hash/canonicalization;
- Artifact handle/class/validator/durability tests;
- public privacy and body-free exception tests;
- legacy `durable_product_job.py` read-only compatibility regression;
- diff/scope/secret scan and compile checks.

### Windows native

- NTFS root/lock/event/artifact hardlink/reparse/ancestor/DACL race matrix;
- same bytes/different file identity at every read/publish seam;
- operation-owned handle publication and directory durability failure injection;
- concurrent two-process reservation/transition/dispatch exact one;
- candidate-publish/TASK-043-CAS race and orphan-preservation at every phase;
- broker-arm/TASK-076-IN_FLIGHT-selection partial-commit yields child/artifact0;
- exact Task072 V2 ARMED/ABORTED/ORPHAN_ABORTED/STARTED/process/config/handle/
  terminal readback;
- V3 BOOTSTRAP_WAITING/EXTERNAL_INPUT_BOUND/VALIDATED/BOOTSTRAP_ABORTED/
  PREBOOTSTRAP_ABORTED/ORPHAN_ABORTED/ARTIFACT_PREPARE_PENDING/PREPARED/
  ABORT_WAITING_ARTIFACT_TRUTH/ABORT_PENDING/RELEASE_PENDING/STARTED/TERMINAL
  exact readback and process/currentness tests;
- real two-process PENDING abort request proves only PREPARE_IN_PROGRESS can win,
  release remains blocked, the original prepare lease alone supplies truth, and
  caller crash with the live broker may finish that exact continuation while a
  broker/Product restart cannot recreate it and enters containment;
- harmless two-role owner fixture proving partial transfer/preflight failure
  enters ABORT_PENDING before owner close, burns both roles, records truthful
  Artifact-handle state, model/body-write/consumer effect zero and parent handle
  zero;
- Artifact failure/cancel/exception abort race and abort-crash exact-query tests;
- dedicated Job Object sole-handle/non-inheritance and
  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` broker-crash proof;
- BURNED_UNKNOWN at every owner-transfer/preflight/Artifact/release seam proves
  recovery revoke plus terminate/wait containment while outcome stays unknown;
- crash injection at every event/child/artifact/Task043 bind seam;
- restart proves scan0/mutation0/replay0;
- foreign output replacement remains preserved;
- public UI/log/stdout path/body/secret leakage zero.

Native tests use harmless bounded fixture children only unless a separate
consumer/native effect Gate exists. No Provider, private media, model, render,
export, Timeline or external effect is authorized by this design.

### Package/install

- clean packaged Product operation without Codex/ChatGPT/OpenAI key/internet;
- exact schema/module/build manifests and installed hashes;
- multiple Projects/installs cannot cross-bind Job/event/artifact;
- repair/upgrade preserves immutable evidence and invalidates live tickets;
- legacy jobs.json remains untouched;
- installer/Project-store integration changes are separate-owner amendments;
- uninstall/retention/GC is not a TASK-076 effect.

## 15. Acceptance criteria

Design acceptance requires:

1. Owner, exact Allowed Files, prohibited paths and cross-owner amendments are
   fixed.
2. The only authority chain is TASK-068 immutable I/O + TASK-043 currentness +
   TASK-072 child receipt; no single public receipt substitutes.
3. Existing mutable jobs.json and public Job objects are audit-only.
4. Every Job transition is a separate immutable no-replace predecessor-bound
   event; TASK-076 performs no mutable store update.
5. Stable semantic reservation prevents reissue by new request/ticket/random ID.
6. TASK-043 alone selects current Job head through a fresh exact Project
   revision/readback; scan/equality/mtime/filename cannot.
7. TASK-072 exact durable IN_FLIGHT and child terminal are mandatory for an
   effect-bearing terminal.
8. V1 Artifact is zero-or-one regular single file or an explicitly receipt-only
   external result; multi-file/directory commit fails closed.
9. Artifact creation/readback uses retained operation-owned handles, exact
   physical identity, no-replace, durability and consumer validator.
10. Unknown/crash/orphan state is preserved and never replayed, repaired or
    deleted automatically.
11. Strict bounded JSON validation occurs before canonicalization/hash and
    ambiguous input remains unchanged.
12. Public status/errors/logs are body/path/secret free and never accepted as
    authority.
13. Early fixtures are useful but cannot satisfy current/native/Product gates.
14. Focused/fault/concurrency/Windows/package tests assert unrelated
    overwrite/delete zero.
15. Every immutable candidate must be selected by an exact TASK-043 next
    revision before it authorizes a following phase or child/Artifact effect.
16. READY holds only a non-authoritative dispatch plan. Exact TASK-043-selected
    DISPATCHING currentness is required by atomic TASK-072 issue-and-arm. For V2,
    exact TASK-076/TASK-043 IN_FLIGHT selection and Artifact handle creation then
    precede one-use attach-and-start. No child process/effect exists while ARMED,
    and there is no live credential gap before DISPATCHING.
17. Initial Job creation is reservation -> RESERVED candidate -> TASK-043
    ABSENT_JOB_HEAD CAS; concurrent/cross-Project null-head proof fails closed.
18. DISPATCHING terminals require exact TASK-072 REJECTED or burned/IN_FLIGHT
    readback and become current only after immutable publish + TASK-043 CAS.
19. A published orphan IN_FLIGHT is selected before its terminal; a competing
    terminal at the same predecessor/slot is collision and never published.
20. READY plan-validation rejection has the sole READY -> FAILED_KNOWN edge.
    Post-DISPATCHING issue-and-arm and post-IN_FLIGHT attach-and-start have exact
    REJECTED versus burned/orphan branches; TASK-072 classification alone is not
    current Job state.
21. After selected TASK076 IN_FLIGHT, V2 permits only serialized
    attach-and-start or abort-armed to consume the ARMED start budget. Exact
    ABORTED is mandatory for a no-effect FAILED_KNOWN terminal; abort unknown is
    BURNED_UNKNOWN and no delayed/retried start is allowed.
22. A published unselected IN_FLIGHT orphan becomes TASK043-current only after
    exact profile-matching V2/V3 ORPHAN_ABORTED consumes every remaining profile
    budget while DISPATCHING is still current; unknown/race never claims
    child/artifact zero.
23. V3 assigns durable one-winner lifecycles to process-create, external-bind,
    preflight, release and abort. Every known terminal closes all five; any
    uncertain phase burns the vector and leaves no reusable budget. The release
    budget contains the Artifact-prepare claim/commit substates and serializes
    them against abort. Bootstrap child creation is truthfully reported but
    cannot load a model, create an Artifact handle/body or enter consumer code.
24. V3 sensitive handles move only from the named producer into the exact
    child-local broker; admission requires the complete role set,
    TASK-076/parent handle count is zero, partial transfer enters failed binding,
    and no generic hook/callback/caller PID can substitute.
25. V3 external preflight is current before Artifact-handle creation. Artifact
    create requires exact ARTIFACT_PREPARE_PENDING. The closed abort phase union
    accepts BEFORE_PREPARE only with NEVER_ENTERED, PREPARE_IN_PROGRESS only with
    the exact pending readback, and AFTER_PREPARE/AFTER_RELEASE_REJECTED only with
    their exact terminal phase. Abort during prepare becomes
    ABORT_WAITING_ARTIFACT_TRUTH, blocks release, and cannot reach truth-embedded
    ABORT_PENDING until the same prepare lease commits created/no-create truth.
    `NONE` and caller-reconstructed truth are never authority.
    After that, abort first wins ABORT_PENDING against release, then authorizes
    exact producer close, child terminate/wait and abort commit. Release first
    wins RELEASE_PENDING, validates a live owner lease and forbids close/abort.
26. V3 distinguishes Artifact-handle creation from body write and consumer
    effect. Every abort/terminal records the truthful handle identity/state;
    created files are preserved and never erased to manufacture effect zero.
27. V3 effect-bearing completion requires exact
    `JOB_CHILD_TERMINAL_READBACK_V3` binding the entire V3 lineage and all five
    terminal budgets. V2 public/equal-field evidence cannot substitute.
28. Every vector-wide BURNED_UNKNOWN retains an idempotent containment-only ABI.
    Producer roles are recovery-revoked and the sole-handle kill-on-close Job
    Object is closed or terminated/waited; release/resume/state reclassification
    and Artifact deletion remain zero even when containment stays unknown.
29. Wrong/cross-operation input before exact vector match leaves the victim
    bytes/revision unchanged. An exception after authenticated durable entry
    burns only the exact matched budget/vector; focused/fault/native tests assert
    both outcomes for every V3 method.
30. Independent Critic returns `Critical=0 / High=0` and Judge returns `PASS`.

## 16. Completion receipt template

This section is administrative only until the complete technical payload is
frozen and independently reviewed.

```text
task: TASK-076
design_identity: TASK076-PTD-DURABLE-PRODUCT-JOB-SECURE-ARTIFACT-V5
base: origin/main@efdcd77729732e3c50abb9e4a7e89ae2b7b37aa0
allowed_files: docs/ai-team/tasks/TASK-076/complete-design-packet.md
review_target_sha256: 95157212CD98435B0516310B07B88E35886BC403F53161E15CA2E74A85B458FA
review_target_lines: 1706
review_target_bytes: 92817
critic: INDEPENDENT_EUCLID_PASS_CRITICAL0_HIGH0_MEDIUM0_LOW0
judge: INDEPENDENT_PARFIT_PASS_CRITICAL0_HIGH0_MEDIUM0_LOW0
design_frozen: true
superseded_r4_review_target_sha256: 445D6D52945054F5EA2D6E2E8007DF9B70C902E7D4AFCD0819441C1424C0373A
superseded_r4_critic: INDEPENDENT_EUCLID_REVISE_CRITICAL0_HIGH1_MEDIUM0
superseded_r4_judge: INDEPENDENT_PARFIT_FAIL_CRITICAL0_HIGH1
superseded_r3_review_target_sha256: 0022C2C7A5427DCDFA4E5D14DB758AB5225BD01E6C098C5CC73845674615468E
superseded_r3_critic: INDEPENDENT_EUCLID_REVISE_CRITICAL0_HIGH2_MEDIUM1
superseded_r3_judge: INDEPENDENT_PARFIT_FAIL_CRITICAL0_HIGH1
superseded_r2_review_target_sha256: E00B33C8034C5F9C23FEE93AD91680BD25C8A775868E06472CCB18255183181D
superseded_r2_critic: INDEPENDENT_EUCLID_REVISE_CRITICAL0_HIGH3_MEDIUM1
superseded_r2_judge: INDEPENDENT_PARFIT_FAIL_CRITICAL0_HIGH2
superseded_v1_review_target_sha256: 9C6EF3A5334C6FFFAC7EAA90BE49190A725DA25FBEFB491174F7408C7DAC38F5
superseded_v1_critic: INDEPENDENT_EUCLID_CRITICAL0_HIGH0
superseded_v1_judge: INDEPENDENT_PARFIT_PASS
source_effect: 0
schema_effect: 0
test_effect: 0
native_effect: 0
release_deploy_production_effect: 0
authority_created: false
```

The completed design creates no implementation, child, Artifact, Project,
native, Human, Release, Deploy or Production authority. Technical changes after
a PASS receipt require a new exact hash and independent review.
