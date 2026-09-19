# TASK-098 A2-R2c Shell / Human Pre-Mutation Review

## 1. Identity, authority and development depth

- Active Project / Task: `BAI VIDEO PRODUCTION / TASK-098`.
- Proposed Atomic Unit: `A2-R2c — trusted application/Shell projection and Human control`.
- Base: R2b2 commit `01de550f665a000cf70b8cbfb38556fc517020f8`.
- Branch: `codex/task-098-universal-wav-review-integration`.
- Governance: `DEV-3 HIGH ASSURANCE`.
- Authority: Owner AUTONOMY continuation on `2026-09-20`, bounded by the
  accepted A2-R2 design and every existing Human/native/private/Provider/model/
  release gate.
- Current effect authority: `ACCEPT / IMPLEMENTATION_ALLOCATED`. Judge allocates
  only the exact four-source/five-test ceiling in section 6 plus bounded docs.

R2c is the reserved next continuation of TASK-098/A2, not a new Task and not a
revision of a completed responsibility. R2a owns the immutable public control
contract and pure reducer. R2b1/R2b2 own durable coordination and Provider/
engine checkpoints. R2c may only expose those existing facts and invoke those
existing actions through the trusted TASK-036 application/Shell boundary.

## 2. Canonical boundary and non-goals

Canonical ownership remains:

- TASK-023 owns FasterWhisper construction/transcription semantics.
- TASK-036 owns Product operation lifecycle, fixed output slot, Transcript
  binding, trusted confirmation state and Shell presentation.
- TASK-041 owns canonical 48 kHz media/review metadata.
- TASK-046/TASK-097 own Voice Dataset, Training, ModelCandidate and the local
  second GPT-SoVITS run.
- TASK-048 owns voice-quality and Dataset-eligibility decisions.

R2c adds no store/schema migration, second queue, Transcript/media store,
Timeline, retry/reset/replay route, quality score, training authority or native
adapter. It does not modify serialized launch-config versions `1.0.0` through
`1.3.0`, first-run, CLI, packaged Shell, or the Product entrypoint. The existing
Python-only `build_runtime_managed_trusted_launch_for_tests` remains the sole v2
composition route.

Real Provider/model execution, runtime/model download, private audio, recording,
Dataset adoption, voice learning/selection, installation, Release, Deploy and
Production Activation remain prohibited.

## 3. Development responsibility split

### 3.1 Durable projection reader

`RuntimeTranscriptionCoordinatorV1` may add one read-only control-chain reader.
It reads the exact deterministic control row plus hash-addressed R2a Evidence
for the supplied trusted source coordinates. It validates row identity, status,
attempt, typed refs, record digests, predecessor chain and coordinates, then
returns only a frozen private chain to the trusted TASK-036 port. It does not
classify R1b recovery or call the pure reducer itself.

The reader never reserves a control row, writes Evidence, changes a status,
reconciles publication, releases a slot, infers a missing digest or repairs a
chain. Only a fact required by the selected durable row is mandatory. An absent
control is normal for no-request active and adjudication-ready work; no operation
plus no lease/control/slot is valid reducer row 19. A foreign, malformed,
unreadable, oversized, symlinked, impossible or required-but-missing fact is
invalid and later yields fixed `BLOCKED` without exposing its value or exception.

The closed presence matrix is:

- no operation: no lease, slot, control or Evidence;
- PENDING admission: exact lease, no slot/control/Evidence;
- active no-request: exact lease/main/slot and either absent control or exact
  `PENDING / null`, with no Evidence;
- cancel requested/outcome: exact `IN_PROGRESS` control and its typed request or
  outcome chain;
- adjudication-ready: exact lease/main/slot and absent control or exact
  `PENDING / null`;
- terminal closure in progress/completed: the exact barrier/closure/observation/
  commit chain required by that current control/main boundary;
- publication recovery/verification: the exact R2b2 publication control/barrier
  state required by the current main boundary; and
- ordinary FAILED without an accepted terminal chain: no Evidence is inferred;
  reducer row 20 remains blocked.

Publication-bound `RECOVERABLE_PUBLICATION` and `VERIFICATION_ONLY` are a
special impedance boundary. R2b2's exact publication control/barrier chain must
be validated read-only first. The already accepted R2a rows 10/11 intentionally
project only the validated R1b recovery state and expose no A2-R2 action, so the
publication record itself is not passed as an active cancel/Human record to the
pure reducer after validation. This is not omission of validation and cannot
authorize RECOVER/VERIFY; R1c remains the sole selector for those actions.

The authoritative recovery-state input comes only from the existing TASK-036
validated recovery path: exact bounded immutable-publication decode plus
`_classify_validated_runtime_recovery` for publication states, or the existing
typed-admission classifier for nonpublication states. R2c does not reimplement
or weaken that logic in the coordinator. Missing/tampered/mismatched immutable
publication bytes, or disagreement between canonical recovery classification
and the validated control chain, yields BLOCKED. The trusted port combines that
canonical recovery fact with the coordinator chain, exact main/lease/slot rows
and exact-coordinate live observation, constructs
`RuntimeTranscriptionReducerFactsV1`, and calls the unchanged reducer.

### 3.2 TASK-036 runtime-managed port

`Task036RuntimeManagedLocalTranscriptionPortV2` may add closed Python-only
methods that:

- retain the current in-process phase from the existing R2b2 phase observer only
  as a frozen observation bound to the exact production job, project, source
  ID/SHA, operation ID, admission ref, attempt and fresh in-process invocation
  epoch under a lock, while still forwarding the optional existing observer;
- retain a separate exact-coordinate active-worker marker from immediately
  before the R2b2 lifecycle call until its synchronous return/finally;
- capture a frozen private server-only snapshot containing the exact current
  main/lease/slot/control row identities, statuses, attempts and refs, recovery
  state, typed Evidence identities, exact phase observation coordinate and
  active-worker marker, together with the copied public projection;
- return the exact copied twelve-key R2a public projection;
- request cancellation only for an exact current projection whose action is
  `REQUEST_CANCEL`; and
- create the fixed Human decision internally and call the existing coordinator
  closure only for an exact current projection whose action is
  `CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY`.

No caller supplies operation/slot IDs, source hash, attempt, admission ref,
phase, decision text, stop evidence, record digest or terminal ref. The port
reconstructs every coordinate from its trusted settings/store and the source
binding. The Human decision is exactly
`CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY`, uses a server-generated ID
and trusted clock, sets `provider_stop_attested = true`,
`stop_evidence = HUMAN_ATTESTATION`, and never claims technical Provider stop.

The retained phase is process-local observation only and exists only while its
exact synchronous lifecycle call is active. The phase and active-worker marker
are cleared together in that call's `finally`; a new process/port or completed/
disconnected call has no phase and therefore projects
`UNKNOWN_AFTER_DISCONNECT` unless durable state selects a stronger row. Phase
observation is never persisted and never becomes authority. An out-of-order
observer call or a phase/active-worker marker whose complete coordinate differs
from the current operation is rejected/ignored for display and blocks mutation
if present ambiguously. Human prepare/apply is unavailable while the exact
active-worker marker exists; absence after return/restart is not proof of stop
and still requires the fixed Human attestation.

The private snapshot is a frozen Python value, not a new serialized contract or
store. It is never returned to JavaScript, logged or persisted. Apply receives
the prepared private snapshot back from the trusted application, captures a
fresh private snapshot and requires full exact equality before any coordinator
mutation. Thus an ABA-like change of attempt/admission/control/slot/Evidence
that happens to preserve the same public label/projection is stale and rejected.

No recovery-state string supplied by Shell/application can stand in for the
canonical fact. The port captures it internally through the existing TASK-036
validators in the same bounded read that constructs the private snapshot.

### 3.3 TASK-036 pre-edit application

`Task036PreEditRuntime` owns a bounded server-held confirmation registry for
R2c control actions. A confirmation binds:

- opaque random confirmation ID;
- project/session/context revision;
- source asset ID/SHA and exact in-memory source path object;
- exact selected action;
- a defensive copy of the exact twelve-key public projection; and
- the opaque frozen private full-durable snapshot returned by the trusted port;
- monotonic expiry, fixed to five minutes.

The registry is capped at 256 entries. Expired entries are removed before
capacity admission. Prepare, apply and cancel are serialized by the existing
confirmation lock. Apply pops the entry before revalidation/effect, so it is
single-use on success and failure. Confirmation cancellation removes only that
entry and performs zero store/Evidence/Provider/slot effect.

The runtime may add one Python-only `confirmation_clock: Callable[[], float]`
dependency whose default is `time.monotonic`. It is not configurable through
serialized config, environment or JavaScript. Every reading must be an exact
finite non-negative `float`/`int` but not `bool`; invalid or regressing time
fails closed. Expiry is `now - prepared_at >= 300.0`, so exactly 300 seconds is
expired. Tests inject a deterministic fake monotonic clock directly into the
Python application object without changing launcher/config authority.

Prepare is available only when the trusted source is bound, the Product remains
at `transcription.start`, and the exact projection exposes one of the two R2c
actions. Human prepare is additionally unavailable while the exact active-
worker marker exists. Apply revalidates every source/project/context coordinate
and requires the current private full-durable snapshot, twelve-key projection
and action to exactly match the prepared values before invoking the port.
Expiry, duplicate use, stale context, changed private/public snapshot/action,
missing port method or malformed port result fails closed.

The Human prepare response uses fixed Japanese warning copy stating that the
action does not recover audio, does not declare transcription successful, and
permanently closes the operation without replay. A cancel-request prepare
states that a request is not proof of cancellation and the UI will remain in
stop-confirmation status until a cooperative boundary responds.

### 3.4 Shell bridge and JavaScript

The trusted bridge may expose exactly three R2c endpoints:

- `prepare_runtime_transcription_control` with an empty request;
- `apply_runtime_transcription_control` with only `confirmation_id`; and
- `cancel_runtime_transcription_control` with only `confirmation_id`.

JavaScript renders the exact public status label/action, calls prepare, shows
the server-supplied fixed warning in an explicit Human confirmation, and sends
only the opaque confirmation ID to apply/cancel. It never sends or receives
operation/slot IDs, source hash/path, attempt, admission/barrier/digest,
decision payload, transcript body, percentage or ETA.

The bridge validates exact request/result key sets and copies the exact
twelve-key projection. Unknown/extra/private keys fail before a response is
returned. Existing START/RECOVER/VERIFY routes and all v1 behavior remain
unchanged. R2c control never shadows R1c RECOVER/VERIFY.

The exact route priority is:

| R1c top-level action | R2c nested action | Route |
|---|---|---|
| `START`, `RECOVER`, or `VERIFY` | `NONE` | existing R1c workflow button and label only |
| `NONE` | `REQUEST_CANCEL` or `CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY` | separate R2c affordance and nested label only |
| `NONE` | `NONE` | no action |
| any other combination, including both layers non-`NONE` | any | BLOCKED; no endpoint call |

The nested R2c label never replaces the R1c workflow label. Tests assert this
table and reject an injected state where both layers expose actions.

## 4. Public response boundary

`workflow_status` adds one field in Python-only v2 mode:

```text
transcription_control: <exact twelve-key R2a projection>
```

The nested projection is exactly:

- `control_mode`
- `phase`
- `cancel_state`
- `adjudication_state`
- `available_action`
- `status_label`
- `provider_execution_started`
- `provider_execution_known`
- `provider_stop_confirmed`
- `stop_evidence`
- `slot_release_allowed`
- `no_replay`

No alias, count, progress, timestamp, path, ID, digest, exception or body is
added. Existing R1c `transcription_recovery_state`,
`transcription_available_action` (`START/RECOVER/VERIFY/NONE`) and status label
remain authoritative for operation recovery. The R2c nested action is distinct
and limited to `NONE`, `REQUEST_CANCEL`, or the fixed Human decision.

Prepare may additionally return only the opaque confirmation ID, fixed
operation label, selected public action, public status/warning labels and
`expires_in_seconds = 300`. It returns no expiry timestamp or durable/private
coordinate. Apply/cancel return fixed status plus the exact post-action public
projection; they return no Transcript or recovery result.

## 5. Ordering, concurrency and crash semantics

1. Status and prepare are read-only and never reserve control.
2. Two prepares may exist, but only the first apply whose exact durable snapshot
   remains current can win the shared R2b control-row CAS. Every loser fails
   closed without repair or alternate action.
3. Cancel request versus publication barrier and Human closure versus
   publication barrier retain the existing R2b winner ordering.
4. A cancel request is never reported as cancellation. Only R2b's exact
   cooperative closure can expose a confirmed cancelled state.
5. A Human decision never sets technical `provider_stop_confirmed`; it only
   exposes `HUMAN_ATTESTATION` after exact terminal commit.
6. Crash/failure after terminal barrier keeps that barrier and slot. R2c never
   rolls back, deletes or silently resumes with a different Human decision.
7. A stale worker that loses to terminal closure performs zero later immutable
   or fixed publication writes, as already enforced by R2b2.
8. Publication-bound PARTIAL/COMPLETED exposes no R2c mutation. RECOVER/VERIFY
   remains the separate R1c path.

## 6. Proposed exact implementation allocation

Source ceiling:

1. `src/ai_video_production/task098_runtime_transcription_coordination.py`
   - read-only exact fact/Evidence projection only.
2. `src/ai_video_production/task036_product_ports.py`
   - process-local phase retention and closed trusted control methods.
3. `src/ai_video_production/task036_pre_edit_runtime.py`
   - expiring single-use server confirmation and exact action revalidation.
4. `src/ai_video_production/task036_shell_ui.py`
   - three bridge endpoints and fake-only v2 presentation.

Focused test ceiling:

5. `tests/test_task098_runtime_transcription_coordination.py`
6. `tests/test_task098_task036_runtime_managed_transcription.py`
7. `tests/test_task036_pre_edit_runtime.py`
8. `tests/test_task036_shell_ui.py`
9. `tests/test_task036_trusted_launcher.py`

Bounded documentation may update only `docs/ai-team/current-state.md`,
`docs/ai-team/task-index.md`, `docs/ai-team/tasks/TASK-098/**` and canonical
TASK-098 Evidence.

The R2a control/schema/reducer, store, Provider, launcher, first-run, CLI,
packaged Shell/native source, dependencies and every other Task are read-only.
If the matrix below cannot be proven within this ceiling, implementation stops
and returns to review rather than expanding implicitly.

## 7. Required deterministic acceptance matrix

1. A parameterized golden table covers every R2a priority row 1 through 20
   individually. Each row asserts all twelve output keys and values, its exact
   competing facts, the priority winner, and unchanged R1c recovery fields.
   Separate priority-collision cases include rows 7/8, terminal commit/barrier,
   publication states and corrupt/foreign facts; representative families alone
   are insufficient.
2. Missing/foreign/wrong-attempt lease, main, slot or control; malformed typed
   ref; missing/mixed/tampered/unreadable Evidence; and symlink/file replacement
   all project fixed BLOCKED only when the closed presence matrix requires that
   fact, and perform zero mutation. Expected absent control/no-operation cases
   prove NOT_STARTED or REQUEST_CANCEL without reserving control.
3. Publication PARTIAL and COMPLETED validate the exact R2b2 publication
   control/barrier chain read-only, expose no R2c action, and retain the R1c
   RECOVER/VERIFY action unchanged. Missing/tampered immutable publication or
   disagreement with the existing TASK-036 validated recovery classifier is
   BLOCKED; R2c contains no duplicate recovery classifier.
4. Live phase/active-worker observation is accepted only for an exact matching
   job/project/source/operation/admission/attempt/invocation-epoch coordinate. A foreign/stale
   phase cannot affect another operation; lifecycle return/finally and restart/
   disconnect clear it and cannot claim Provider state. Source-switch, two-
   operation reuse and out-of-order observer negatives prove no phase reuse.
   Exact active-worker evidence blocks Human prepare/apply before barrier
   acquisition with zero durable effect.
5. Prepare is effect-zero, body-free, exact-key, capacity-bounded and uses an
   opaque 256-character-bounded token with an injectable fake monotonic clock.
   Boundary tests cover `<300`, `==300` and `>300` seconds, invalid/regressing
   clock values, 256 live entries, capacity refusal, expiry purge and re-entry.
6. Expiry, cancel, duplicate apply, changed project/session/context/source/path,
   changed projection/action and malformed port return have zero new durable or
   Provider effect.
7. The confirmation binds a frozen private full-durable snapshot as well as the
   public projection. Same-public-projection changes to attempt, admission,
   lease, slot, control ref/status, Evidence identity, phase coordinate or
   active-worker marker are stale and rejected before mutation.
8. Confirmed apply sends no caller decision/coordinates. Cancel request binds
   only the exact request; Human apply constructs only the fixed decision and
   preserves the technical-stop false/Human-attestation distinction.
9. Publication-versus-cancel and publication-versus-Human races cover both
   winner orders under threads and spawn processes; exactly one durable path
   wins and the loser cannot write/repair/release.
10. Two confirmations prepared from one snapshot are applied concurrently in
    threads: exactly one port/durable effect wins, the other is stale/single-use,
    and no additional Evidence/slot/Provider effect occurs. A token prepared in
    one application/process is rejected by another because confirmation state
    is server-local and non-durable.
11. Crash/fault injection at Human decision Evidence, terminal barrier,
   generation observation, main CAS, terminal commit, control commit and slot
   release yields only the accepted conservative states with no replay.
12. Complete/partial/symlink/unreadable/unknown generation presence blocks Human
    closure and retains the slot.
13. Each bridge endpoint has direct request-boundary tests: empty-only prepare;
    confirmation-ID-only apply/cancel; missing, empty, extra, wrong-type and
    over-256-character token rejection; exact result-key sets; and proof that
    unknown endpoints are not exported. JavaScript contains no private
    coordinate and uses explicit confirmation/cancel routing.
14. The exact R1c/R2c routing table is golden-tested: top-level
    START/RECOVER/VERIFY always retains its existing button/label, R2c is
    available only when top-level is NONE, nested labels never overwrite R1c,
    and dual non-NONE action injection is BLOCKED/effect-zero.
15. Existing v1 START and v2 START/RECOVER/VERIFY golden behavior remains green;
    first-run/CLI/serialized versions remain unchanged.
16. Direct R2a/R2b1/R2b2/R1c and TASK-036 focused regression passes.
17. Independent Critic, Tester and Judge report zero unresolved Critical/High;
    external Evidence is persisted and read back before commit.

## 8. Context scope

`MUST READ`:

- `docs/ai-team/current-state.md`;
- `docs/ai-team/tasks/TASK-098/task.md`;
- A2-R2 sections 3, 5.5, 6, 7, 8 and 10;
- R2b2 implementation outcome and the four proposed source files;
- the five proposed focused tests.

`READ IF REQUIRED`: exact R2a reducer branches, R2b typed Evidence loader,
R1c confirmation/bridge golden tests and store CAS implementation.

`DO NOT READ BY DEFAULT`: archive, full roadmap/Architecture, unrelated Tasks,
providers, schemas, native/package/release files and the secondary OS repo.

## 9. Human gates and stop conditions

Implementation requires fresh independent DEV-3 Critic/Tester review and Judge
allocation of the exact section 6 ceiling. Any unresolved Critical/High blocks
source mutation.

Stop and return to review if implementation needs a schema/store/reducer change,
launcher/CLI/first-run/native change, serialized v2 activation, a caller-supplied
coordinate/decision, new retry/replay semantics, a second state store, private
body exposure or any file outside the exact allocation.

Design acceptance cannot authorize real Provider/model/private media, recording,
voice learning, installation, Release, Deploy or Production Activation.

## 10. Review outcome

- Independent Critic: initial `REJECT / 0/3/1/0`; final
  `ACCEPT / 0/0/0/0` after the closed presence matrix, canonical TASK-036
  recovery fact, exact invocation-epoch phase binding and R1c/R2c route table
  were fixed.
- Independent Tester: initial `FAIL / 0/2/2/0`; final
  `PASS / 0/0/0/0` after the twenty-row golden matrix, deterministic expiry,
  full private snapshot, concurrent confirmation and bridge-boundary coverage
  were fixed. Dynamic execution is `NOT_CONFIRMED` because this is design review.
- Independent Judge: `ACCEPT / IMPLEMENTATION_ALLOCATED / 0/0/0/0`.
- Allocation: exactly the four source and five test files in section 6 plus
  bounded TASK-098/current-state/task-index documentation.
- Required implementation gate: section 7, independent implementation review,
  maximum two bounded fix cycles, external Evidence persistence/read-back.
- Store/schema/reducer, Provider, launcher/CLI/first-run, serialized/native v2,
  real Provider/private media/model/training/release effects remain read-only,
  unallocated or gated.
