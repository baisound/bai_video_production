# TASK-076 — Durable Product Job Secure Artifact

Status: `DESIGN_COMPLETE / DEV-4 / SOURCE_START0`

Design identity: `TASK076-PTD-DURABLE-PRODUCT-JOB-SECURE-ARTIFACT-V1`

Canonical design base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`

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
```

TASK-076-A can freeze fixture shape before producer implementation. B/C/D remain
`DEPENDENCY_NC` until their exact canonical producer receipts exist. An
immutable event without TASK-043 currentness is historical/unselected evidence.
A TASK-043 binding without TASK-068 pinned bytes/identity is not a valid event.
A terminal result without TASK-072 child receipt is not a native effect proof.

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
- exact TASK-072 committed child terminal;
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

The three exact fixture files in section 5 supply static positive and negative
vectors for each registered Job kind. Every fixture declares:

- `fixture_only=true`;
- `authority_created=false`;
- `task068_real_io=false`;
- `task043_project_currentness=false`;
- `task072_child_executed=false`;
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

If TASK-072 arm/burn succeeds but TASK-076 `IN_FLIGHT` cannot become current, child
and Artifact creation stay zero and recovery classifies
`BURNED_UNKNOWN_CANDIDATE_REQUIRED`; it is not yet current. Exact broker query
is allowed but replay is not. If Artifact creation/validation fails after
selected TASK-076 IN_FLIGHT while broker state is ARMED, TASK-076 must call the
serialized abort ABI. Exact ABORTED readback permits an IN_FLIGHT -> FAILED_KNOWN
candidate with child effect zero; abort crash/unknown permits only an
IN_FLIGHT -> BURNED_UNKNOWN candidate after exact broker query. No terminal
candidate may race ahead of consuming/classifying the ARMED start budget.

`BURNED_UNKNOWN` is not current merely because the broker burned. Recovery pins
the still-current `DISPATCHING` readback, exact TASK-072 burned/ARMED broker
readback and the planned TASK-076 `IN_FLIGHT` coordinate:

- if the planned `IN_FLIGHT` candidate is absent, publish a predecessor-bound
  `BURNED_UNKNOWN` candidate and ask TASK-043 to CAS-select it;
- if the exact planned `IN_FLIGHT` candidate exists, first obtain exact
  `JOB_CHILD_ORPHAN_ABORTED_READBACK_V2` while DISPATCHING remains current. Only
  then may TASK-043 CAS-select that exact orphan against unchanged DISPATCHING,
  followed by an `IN_FLIGHT -> FAILED_KNOWN` candidate/readback. If orphan abort
  is unknown, currentness changes or another actor selects the orphan, stop and
  exact-query; never precompute/select a terminal or claim child/artifact zero;
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
| Artifact create/validation/collision fails after selected TASK076 IN_FLIGHT while broker ARMED; abort wins | `FAILED_KNOWN` candidate | exact ABORTED proves child/create/start/effect zero; preserve foreign target |
| abort_armed crashes/returns unknown, or attach_and_start wins its race | `BURNED_UNKNOWN` candidate | exact broker query/classification; never claim no-effect or retry |
| attach_and_start exact pre-create rejection | Job `FAILED_KNOWN` candidate | predecessor is current TASK076 IN_FLIGHT; child effect zero; publish + TASK043 CAS required |
| attach_and_start uncertainty after start-budget entry | `BURNED_UNKNOWN` candidate | predecessor is current TASK076 IN_FLIGHT; exact broker query only; no reattach/start |
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
delta, TASK-072 child count, Artifact delta and unrelated overwrite/delete.

### T76-AUTH

- direct/copy/replace/pickle/deserialized/subclass/duck public Job/collection;
- module token/sentinel and recomputed valid self-hash;
- public request/status/legacy `operation_identity` used for issuance;
- caller-selected Project/root/path/Job/event/ticket/time/backend;
- fake TASK-068/TASK-043/TASK-072 verifier or test clock in Production;
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
- local terminal publication after Artifact failure without exact
  `JOB_CHILD_ABORTED_READBACK_V2` or exact broker unknown classification;
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
- atomic issue-and-arm burn with planned IN_FLIGHT absent, exact orphan
  present, or a colliding event at the expected predecessor/slot;
- exact orphan selected before `JOB_CHILD_ORPHAN_ABORTED_READBACK_V2`, orphan
  abort attempted after selection, or delayed attach/start winning the gap;
- Product/broker restart with ARMED state followed by reattachment/start;
- abort crash followed by retry, public/local reason treated as abort proof, or
  FAILED_KNOWN selected before ARMED budget classification;
- child start attempted before both TASK-072 and TASK-043-selected TASK-076
  IN_FLIGHT readbacks;
- exact effect-zero child-process start failure whose terminal candidate does
  not name the current selected IN_FLIGHT predecessor;
- success exit code with missing/wrong consumer result digest;
- BURNED_UNKNOWN reclassified as FAIL/SUCCESS or replayed.
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
- exact Task072 ARMED/ABORTED/ORPHAN_ABORTED/STARTED/process/config/handle/
  terminal readback;
- Artifact failure/cancel/exception abort race and abort-crash exact-query tests;
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
    DISPATCHING currentness is required by atomic TASK-072 issue-and-arm. Exact
    TASK-076/TASK-043 IN_FLIGHT selection and Artifact handle creation then
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
21. After selected TASK076 IN_FLIGHT, only serialized attach-and-start or
    abort-armed may consume the ARMED start budget. Exact ABORTED is mandatory for
    a no-effect FAILED_KNOWN terminal; abort unknown is BURNED_UNKNOWN and no
    delayed/retried start is allowed.
22. A published unselected IN_FLIGHT orphan becomes TASK043-current only after
    exact broker ORPHAN_ABORTED consumes the ARMED start budget while DISPATCHING
    is still current; unknown/race never claims child/artifact zero.
23. Independent Critic returns `Critical=0 / High=0` and Judge returns `PASS`.

## 16. Completion receipt template

This section is administrative only until the complete technical payload is
frozen and independently reviewed.

```text
task: TASK-076
design_identity: TASK076-PTD-DURABLE-PRODUCT-JOB-SECURE-ARTIFACT-V1
base: origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38
allowed_files: docs/ai-team/tasks/TASK-076/complete-design-packet.md
review_target_sha256: 9C6EF3A5334C6FFFAC7EAA90BE49190A725DA25FBEFB491174F7408C7DAC38F5
review_target_lines: 1054
review_target_bytes: 52946
critic: INDEPENDENT_EUCLID_CRITICAL0_HIGH0
judge: INDEPENDENT_PARFIT_PASS
design_frozen: true
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
