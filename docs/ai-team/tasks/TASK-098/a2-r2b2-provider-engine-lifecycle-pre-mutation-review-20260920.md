# TASK-098 A2-R2b2 Provider / Engine Lifecycle Pre-mutation Review

## 1. Identity, authority and decision requested

- Active Project / Task: `BAI VIDEO PRODUCTION / TASK-098`.
- Candidate Atomic Unit: `A2-R2b2 — fake-only Provider / engine lifecycle integration`.
- Current HEAD: `19a03783f97509af602e881b5a447398762a1032`.
- Base / current local main: `28ba61e5f01047a716c681a3584be22500fe53fc`.
- Branch: `codex/task-098-universal-wav-review-integration`.
- Governance: `DEV-3 HIGH ASSURANCE`.
- Authority: Owner-directed autonomous staged Universal WAV Review integration.
- Requested decision: accept, reject or narrow only the exact fake-only source /
  test allocation in section 9. No implementation mutation is authorized by
  this draft before independent Critic, Tester and Judge acceptance.

R2b1 is committed at the current HEAD with final independent
`ACCEPT / PASS / ACCEPT`, unresolved `0/0/0/0`, external checkpoint and
post-commit receipt read-back `PASS`. R2b2 is the reserved second half of the
already-designed R2b responsibility; it is not a new Product or a reuse of
completed Task history.

## 2. Current implementation facts and gap

The current source has four precise gaps against the accepted A2-R2 lifecycle:

1. TASK-036 v2 calls `_preflight_generation_target` before admission and
   Provider entry. That method creates
   `.task036-publications/<runtime-operation-id>`, so R2b1 cannot later prove
   exact generation absence for a pre-publication terminal closure.
2. The shared engine calls `LocalTranscriptionService.run`, which calls
   `provider.transcribe(request)` and consumes the FasterWhisper lazy segment
   iterable internally. There is no v2-only cooperative checkpoint before the
   first `next()` or between segment pulls, and no exact iterator-close result.
3. The v2 immutable publication writer runs before any R2b1 `PUBLICATION`
   barrier. A losing or stale worker therefore is not yet prevented from making
   its first immutable write after a terminal-closure winner.
4. R2b1 has the barrier and terminal-closure primitives but intentionally has
   no worker-facing exact cancel observation/acknowledgement or publication-
   completion transition.

These are integration gaps only. R2b2 must not replace TASK-023 transcription,
TASK-036 operation/publication ownership or R2b1 SQLite/Evidence authority.

## 3. Responsibility and non-goals

R2b2 owns only:

- v2-only in-process phase observations;
- exact cancel observation before Provider factory/model/transcribe entry;
- cooperative cancel observation before the first lazy segment pull and
  between later pulls;
- exact iterator-close confirmation or conservative stop-not-confirmed result;
- R2b1 publication-barrier use before the first immutable generation write;
- publication main-row binding before control-row completion;
- fake-only concurrency, crash, negative and v1-regression proof.

Canonical ownership remains:

- TASK-023: FasterWhisper construction and transcription semantics;
- TASK-036: v2 operation, permanent lease, fixed slot, Transcript and immutable /
  fixed publication;
- R2a: immutable cancel/barrier/terminal records and public reducer;
- R2b1: deterministic control row, Evidence, generation-exclusion lock,
  terminal main -> control -> slot order;
- R2c: Product/Shell actions, phase presentation and Human confirmation;
- TASK-046/TASK-097: Voice Dataset, GPT-SoVITS learning, ModelCandidate and
  final voice-pair approval.

R2b2 does not add a queue, worker process, background thread, state store,
schema, migration, Transcript store, retry/replay path, Shell/JavaScript action,
serialized launch-config version, native adapter, real Provider/model execution,
private media, model download, voice training, install, release or deploy.

## 4. Closed v2-only lifecycle contract

### 4.1 Trusted coordinates and phase observation

After exact v2 admission and fixed-slot acquisition, the engine constructs one
`RuntimeTranscriptionCoordinatesV1` from the already-validated project, source,
request, decision, admission ref, operation/slot IDs and admitted attempt.
No caller supplies or rewrites those coordinates.

An optional trusted Python observer may receive only the phase string.
The phase must be one of the R2a closed values used here:
`ADMISSION`, `PROVIDER_STARTING`, `PROVIDER_RUNNING`,
`PUBLICATION_VALIDATING`, `PUBLICATION_COMMITTING`, `COMPLETED`, or `BLOCKED`.
It is in-process observation, not durable truth after disconnect, not included
in operation identity and not exposed to JavaScript in R2b2. An observer
failure is fail-closed after admission: no replay or slot release.

The injected fake-only seam also exposes a closed set of internal lifecycle
boundaries needed for deterministic thread/process and crash tests:
`AFTER_PUBLICATION_BARRIER`, `AFTER_IMMUTABLE_WRITE`,
`AFTER_MAIN_PUBLICATION_CAS`, `AFTER_CONTROL_PUBLICATION_COMPLETION`,
`AFTER_FIXED_PROMOTION`, and `AFTER_MAIN_COMPLETION`. It is default-absent,
non-serialized, excluded from every operation/config/publication identity and
never routed to Shell/JavaScript. Unknown event names fail closed.

Required ordering is:

1. `ADMISSION` after exact admission plus slot ownership;
2. `PROVIDER_STARTING` immediately before Provider factory entry;
3. `PROVIDER_RUNNING` immediately before `provider.transcribe` entry;
4. `PUBLICATION_VALIDATING` after Provider return and before canonical
   temporary publication validation;
5. `PUBLICATION_COMMITTING` only inside the winning `PUBLICATION` barrier's
   first-generation-writer callback, before its first immutable write;
6. `COMPLETED` only after the main operation is `COMPLETED` with the exact
   publication digest. It does not release the TASK-036 slot.

### 4.2 Exact cancel observation and acknowledgement

R2b1 may add closed worker-facing methods that:

- read an absent control row as no request without reserving it;
- return only an exact request bound to the current coordinates;
- reject malformed, foreign, wrong-attempt, outcome/barrier/commit or otherwise
  impossible control state instead of interpreting it as cancellation;
- construct the R2a outcome internally from the exact request and booleans;
- bind `STOP_NOT_CONFIRMED` without terminal closure; or
- for confirmed stop, bind the exact outcome and call the existing terminal
  closure path. Callers cannot supply outcome names, evidence strings, record
  digests or terminal refs.

Before Provider factory entry, an exact request produces
`CANCELLED_BEFORE_PROVIDER_EFFECT / PRE_PROVIDER`, then the existing R2b1
terminal path proves generation absence, closes main/control and releases only
the exact slot. The outward engine result is a body-free Product error; no
Transcript/publication is returned.

After Provider entry, cancellation is never claimed until a cooperative
boundary confirms stop. A request without that proof remains
`CANCEL_REQUESTED`. Failure to prove stop binds `STOP_NOT_CONFIRMED / NONE`,
keeps the slot and permits no terminal closure.

### 4.3 TASK-023 lazy iterator checkpoint

The concrete `FasterWhisperProvider` retains the exact existing
`transcribe(request)` signature and implementation path. R2b2 may add one
separate, explicitly named cooperative v2 method accepting the request and stop
probe. `LocalTranscriptionService.run` must call the exact legacy
`provider.transcribe(request)` form unless the v2 cooperative method is
explicitly selected. Existing v1, third-party fake and generic `AsrProvider`
contracts therefore retain their call and byte behavior.

When the v2 probe is present, the Provider must explicitly obtain the lazy
iterator, check the probe before the first `next()` and before every later
`next()`, and consume segments with existing canonical filtering unchanged.
When the probe first returns true:

1. obtain `close` from the exact owned iterator;
2. require it to be callable;
3. invoke it exactly once;
4. report confirmed cooperative stop only after it returns successfully; and
5. return control synchronously so no owned worker remains active.

Missing `close` or throwing `close` is not confirmed cancellation. When the
exact request is still authoritative, the dedicated stop handler binds
`STOP_NOT_CONFIRMED / NONE`, keeps main exactly
`IN_PROGRESS / admission ref / admitted attempt`, retains the slot and writes
no immutable or fixed publication. Non-boolean probe output, probe failure or
foreign/corrupt control cannot create even that outcome; they fail closed with
main nonterminal and slot retained. No hard interruption or background
cancellation is added.

Confirmed pre-Provider and cooperative-stop signals have dedicated catches
outside the shared generic exception-to-`PARTIAL` handler. They must first
complete the exact R2b1 terminal chain and then return a stable body-free
cancelled Product error. The generic handler must not relabel or overwrite a
confirmed terminal cancellation. Exact stop-not-confirmed has its own catch and
keeps the admission state above; other unknown failures may use the existing
conservative `PARTIAL` path with the slot retained.

### 4.4 Validation-window cancellation

The engine rechecks the exact request after Provider return and again after
temporary publication validation but before publication-barrier acquisition.
At either point Provider work has synchronously returned, so a request may be
acknowledged as `CANCELLED_AFTER_COOPERATIVE_BOUNDARY` and must win terminal
closure before any immutable write. A request racing after the final recheck is
resolved only by the shared control-row CAS. If publication-barrier acquisition
loses, the worker bypasses the generic exception-to-`PARTIAL` path, re-reads the
exact request, acknowledges confirmed cooperative stop and invokes terminal
closure. Success leaves main `FAILED` with its typed no-replay ref. Any stale,
foreign or changed state keeps its exact current state and slot; the generic
handler never blindly rewrites it. If publication wins, later cancellation is
unavailable and the publication path proceeds.

TemporaryDirectory output is not canonical publication and is discarded. It
must never be promoted, hashed as durable result or used to infer stop truth
after a terminal winner.

### 4.5 Publication ordering

The v2 path no longer creates the per-operation generation directory during
preflight. It retains the existing pinned output-root and optional existing
publication-parent validation. The parent and operation child may be created
only by the winning first-generation writer.

The v2 immutable writer is invoked only as the callback of
`RuntimeTranscriptionCoordinatorV1.acquire_publication_barrier`. The
generation-exclusion lock is therefore held from barrier competition through
the complete first immutable publication-set write. A terminal winner prevents
the callback from running; an old losing worker performs zero immutable/fixed
writes.

After immutable bytes exist, ordering is exact:

1. main operation CASes `IN_PROGRESS / admission / expected attempt` to
   `PARTIAL / publication-set SHA`;
2. a new coordinator publication-completion method validates the exact lease,
   main digest/attempt, slot owner, publication barrier Evidence and control
   `IN_PROGRESS / exact typed barrier / attempt 0`, then CASes only the control
   row to `COMPLETED / same typed barrier`;
3. existing fixed-output promotion runs;
4. existing main `PARTIAL -> COMPLETED` CAS runs;
5. phase `COMPLETED` may be observed; slot finalization remains TASK-036's
   existing separate responsibility.

A crash or mismatch at any boundary keeps the slot. No control rollback,
barrier replacement, deletion, retry, replay or digest inference is performed.
An acquired publication barrier follows R1b recovery/verification only.

The Provider-zero R1b recovery route must also reconcile the publication
control row after it has validated the exact immutable publication, lease,
operation attempt and slot owner. If main is already `PARTIAL / publication
SHA` and control remains `IN_PROGRESS / exact publication barrier / attempt 0`,
the v2 decode context supplies the already-validated barrier/decision and the
shared recovery engine invokes the same idempotent coordinator completion
between decode and fixed promotion, before its existing main-completion CAS.
Missing/foreign/non-publication control never gets reserved,
repaired or skipped; recovery fails closed and retains the slot. Thus a crash
between main publication binding and control completion cannot leave the
control row permanently open or bypass the ordering contract.

## 5. Failure matrix

| Boundary | Durable result | Immutable/fixed writes | Slot |
|---|---|---|---|
| exact cancel before Provider factory | confirmed pre-Provider terminal closure | none / none | released only by R2b1 exact closure |
| request during blocking factory/model/transcribe | request remains pending until a checkpoint; disconnect is unknown | none unless publication later wins | retained |
| request at lazy segment checkpoint + successful exact iterator close | confirmed cooperative terminal closure | none / none | released only by R2b1 exact closure |
| missing/throwing iterator close | `STOP_NOT_CONFIRMED`; main remains exact `IN_PROGRESS / admission / attempt` | none / none | retained |
| request during validation before barrier | confirmed cooperative terminal closure | none / none | released only by R2b1 exact closure |
| terminal barrier wins CAS race | terminal closure path only | losing worker zero / zero | exact closure decides |
| publication barrier wins CAS race | cancel unavailable; R1b publication path | writer may write / promote after validation | retained until normal finalize |
| crash after publication barrier before first write | publication barrier remains authoritative | none / none | retained |
| crash after immutable write before main bind | blocked/uncertain publication | present / none | retained |
| crash after main PARTIAL before control completion | R1b recoverable publication | present / none | retained |
| crash after control completion or fixed promotion | R1b recover/verify only | present / maybe present | retained |
| stale attempt, foreign ref/coordinates, observer/probe failure | blocked; no blind repair | no new write | retained |

## 6. Compatibility constraints

- V1 still calls `_preflight_generation_target`,
  `provider.transcribe(request)` and its existing publication writer exactly as
  before. V1 golden operation key, publication bytes and existing tests remain
  unchanged.
- The generic `AsrProvider` Protocol does not gain a required callback.
- V2 operation/admission keys and publication-set bytes remain unchanged.
- R2b2 adds no serialized field, schema or public body.
- Callback/control exceptions contain only stable Product codes/messages and no
  transcript, source path, model/cache locator, raw Provider exception or body.

## 7. Required deterministic tests

1. Legacy Provider/LocalTranscriptionService path calls exact one-argument
   `transcribe(request)` and existing v1 key/publication byte goldens pass.
2. V2 cancel present before Provider factory: factory/model/iterator and all
   immutable/fixed writers have zero calls; exact terminal records exist.
3. Request immediately after lazy iterator return and before the first pull:
   `next_calls == 0`; successful `close()` is called exactly once and permits
   only confirmed cooperative closure. Separate missing-close and throwing-
   close cases produce exact `STOP_NOT_CONFIRMED`, publication zero and the
   required main/control/slot retention.
4. Missing and throwing iterator close each bind exact `STOP_NOT_CONFIRMED`,
   never claim technical stop, retain slot and write no publication.
5. Request between later lazy segments: `close()` is called exactly once;
   later segment pulls and all publication writers have zero calls; terminal
   closure and slot release are exact.
6. Probe/control corruption and callback failure fail closed with body-free
   errors, no terminal claim and no publication.
7. Request after Provider return and after validation can each win before the
   publication barrier with zero immutable/fixed writes. A request that wins
   the final CAS race is re-read and closed by the dedicated cancel path before
   generic failure handling.
8. Publication-versus-request and publication-versus-Human terminal closure
   run in both deterministic winner orders; exactly one barrier wins.
9. A terminal winner proves an old/stale worker never enters the immutable
   writer callback.
10. Publication barrier is present before the first immutable child/write and
   is held through that first writer.
11. Main publication digest binds before control completion; fixed promotion
    and main completion occur afterward. Changed attempt/ref/slot/control at
    each revalidation boundary fails closed.
12. Crash injection after barrier, immutable write, main PARTIAL, control
    completion, fixed promotion and main completion yields only the closed
    recovery states above and never re-enters Provider. Provider-zero recovery
    must idempotently complete the exact publication control row after a crash
    in the main-PARTIAL/control-open window.
13. Thread and process tests cover request/publication races; duplicate worker
    observations converge without a second terminal or publication write.
14. Phase order is exact, has no percentage/ETA/count/body, and never emits
    `PUBLICATION_COMMITTING` without an exact publication barrier.
15. Direct TASK-006/023/036/098 regression remains green.

## 8. Context scope

`MUST READ`:

- `docs/ai-team/current-state.md`;
- `docs/ai-team/tasks/TASK-098/task.md`;
- A2-R2 design sections 3, 4, 6, 8 and 10;
- R2b1 pre-mutation review and committed coordinator public methods;
- exact v2 lifecycle in `task036_product_ports.py`;
- exact Provider lazy iterator and `LocalTranscriptionService.run` in
  `faster_whisper_asr.py`;
- the four directly allocated test files in section 9.

`READ IF REQUIRED`: exact store CAS, R2a record validators, TASK-036 recovery
classifier and existing v1 golden tests. `DO NOT READ BY DEFAULT`: archive,
full roadmaps/Architecture, unrelated Tasks/providers/UI, native/release and the
secondary OS repository.

## 9. Proposed exact implementation allocation

Source files:

1. `src/ai_video_production/task098_runtime_transcription_coordination.py`
   - exact worker cancel observation/acknowledgement;
   - exact publication control completion only.
2. `src/ai_video_production/faster_whisper_asr.py`
   - separate v2-only lazy-segment cooperative method and closed internal stop
     signals; the legacy `transcribe(request)` path is unchanged.
3. `src/ai_video_production/task036_product_ports.py`
   - v2-only coordinates/phases, parent-only preflight, cancel checkpoints,
     shared publication barrier and main-before-control publication ordering.

Test files:

4. `tests/test_task006_faster_whisper.py`
   - direct iterator/close/legacy-call behavior.
5. `tests/test_task098_runtime_transcription_coordination.py`
   - worker observation/acknowledgement and publication-completion CAS.
6. `tests/test_task098_task036_runtime_managed_transcription.py`
   - fake-only v2 lifecycle, phase, race, crash and zero-write integration.
7. `tests/test_task036_local_transcription_operation.py`
   - explicit legacy v1 call-shape, preflight and publication-byte regression.

Bounded documentation may update only `docs/ai-team/current-state.md`,
`docs/ai-team/task-index.md`, `docs/ai-team/tasks/TASK-098/**` and its canonical
Evidence. No schema, store, Shell, launcher, CLI, packaging, dependency or other
source/test file is allocated. If the accepted matrix cannot be proved within
this ceiling, implementation stops and returns for a narrowed/new review.

## 10. Acceptance and review gate

Implementation is eligible only if independent DEV-3 Critic and Tester find the
canonical boundaries, failure matrix, v1 compatibility and seven-file ceiling
sufficient, and Judge explicitly allocates the unit. Any unresolved Critical or
High blocks mutation.

Acceptance authorizes only fake Providers and temporary/private test fixtures
under unique OS temporary roots. It does not authorize real model creation,
FasterWhisper execution, private user audio, model/runtime download, Shell/UI,
serialized v2/native activation, installation, release, deploy, Production or
TASK-046/097 voice-learning work.

## 11. Review outcome

- Independent Critic: initial `0/4/1/0`; final `ACCEPT / 0/0/0/0` after the
  separate cooperative API, dedicated cancel signals, recovery reconciliation,
  string-only phase seam and exact seven-file authority were fixed.
- Independent Tester: initial `0/3/1/0`; final `PASS / 0/0/0/0` after the
  first-`next()`-before-pull matrix and exact allocation were fixed.
- Independent Judge: `ACCEPT / R2b2 LIMITED IMPLEMENTATION ALLOCATED / 0/0/0/0`.
- Allocation: only the seven source/test paths in section 9 plus bounded docs.
- R2c, store/schema, Shell/launcher/CLI, real/native/private/model/training,
  serialized activation, release, deploy and Production remain unallocated.
