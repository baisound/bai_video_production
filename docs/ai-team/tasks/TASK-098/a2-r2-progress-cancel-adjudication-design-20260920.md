# TASK-098 A2-R2 Progress, Cancel and Human Adjudication Design

## 1. Identity, authority and development depth

- Active Project / Task: `BAI VIDEO PRODUCTION / TASK-098`.
- Design unit: `A2-R2 — truthful progress, cooperative cancellation and Human adjudication`.
- Base: R1c commit `1cad644c43f8b3edaf98c81356c471ca1ef4c19b`.
- Branch: `codex/task-098-universal-wav-review-integration`.
- Governance: `DEV-3 HIGH ASSURANCE`.
- Authority: Owner AUTONOMY continuation on `2026-09-20`, subject to all existing Human, native, private-media, Provider/model, Release and Production gates.
- Current effect authority: design is accepted. Judge allocates only the exact R2a four-file pure contract/schema/reducer slice in section 9; R2b/R2c remain unallocated.

A2-R2 is the reserved completion of TASK-098/A2. It does not create a new
Product or reuse a completed Task ID. R1a owns runtime admission, R1b owns the
durable v2 execution/publication boundary, and R1c owns trusted Python
composition plus public recovery presentation. A2-R2 adds only control and
truthful observation around that existing boundary.

## 2. Canonical ownership and non-goals

Canonical ownership remains unchanged:

- TASK-023 `FasterWhisperProvider` owns FasterWhisper model construction and transcription behavior.
- TASK-036 owns Product operation lifecycle, fixed output-slot serialization, Transcript binding and Shell presentation.
- TASK-041 owns canonical 48 kHz media/review metadata.
- TASK-046/097 own Voice Dataset, Training, ModelCandidate and the local second GPT-SoVITS run.
- TASK-048 owns voice-quality calibration and Dataset eligibility.

A2-R2 does not add a second queue, transcript store, media store, Provider,
Timeline, quality score or training authority. It does not activate serialized
v2 launch config, a native adapter, real FasterWhisper, private audio, model
download, Dataset adoption, training, release or deployment.

## 3. Safety invariants

The following are normative:

1. Progress is phase-only. No percentage, ETA, processed-audio fraction or fake segment total is emitted.
2. A cancel request is not a cancel outcome. `CANCEL_REQUESTED` remains visible until a cooperative boundary confirms that Provider work has stopped.
3. A blocked or disconnected worker is never described as cancelled.
4. No cancellation or Human adjudication returns the v2 operation to `PENDING`, changes the permanent v2 source lease, or permits Provider replay.
5. The output slot is released only after an exact compare-and-set closes the owning v2 operation as terminal failed/no-replay and proves the slot still belongs to that operation.
6. A publication-set digest already bound to the operation is never replaced by a cancel/adjudication receipt. Such work follows R1b recovery/verification only.
7. Direct JavaScript supplies only an opaque single-use confirmation identifier. It never supplies operation IDs, slot IDs, admission refs, source hashes, phases, stop evidence or durable decisions.
8. Unknown status, stale attempt, foreign ref, mismatched source/slot, malformed control ref or failed iterator close is `BLOCKED`, keeps the slot, and has zero replay/release effect.
9. Existing v1 behavior and serialized launch-config versions `1.0.0` through `1.3.0` remain unchanged.
10. Real/native acceptance remains a later Human Gate even after fake-only A2-R2 tests pass.

## 4. Staged Atomic Units

A2-R2 is divided by responsibility:

### R2a — pure control contract and reducer

Define immutable typed records, canonical JSON/schema validation, typed durable
reference grammar and a pure state reducer. R2a performs no store, filesystem,
thread, Provider, model, UI or native effect.

### R2b — durable coordination and cooperative Provider checkpoints

Integrate the accepted R2a contract with the existing SQLite operation CAS,
R1b v2 engine and TASK-023 segment iterator. Use fake Providers only. R2b owns
durable cancel request/acknowledgement, exact closure ordering, phase callbacks
and safe slot release. It does not own Shell/Human presentation.

### R2c — trusted application/Shell presentation and Human adjudication

Expose the exact body-free public projection through the R1c runtime mode, add
explicit prepare/confirm/apply/cancel actions, and bind adjudication to the
server-held operation snapshot. R2c remains fake-only and cannot activate a
serialized/native v2 route.

Each sub-unit requires a fresh pre-mutation review. Acceptance of this design
allocates only R2a, not R2b or R2c.

## 5. R2a canonical contracts

R2a defines closed enums and exact-key records in
`task098_runtime_transcription_control.py` with matching root and packaged JSON
Schema mirrors.

### 5.1 Phase

`RuntimeTranscriptionPhaseV1` is exactly:

- `NOT_STARTED`
- `ADMISSION`
- `PROVIDER_STARTING`
- `PROVIDER_RUNNING`
- `PUBLICATION_VALIDATING`
- `PUBLICATION_COMMITTING`
- `COMPLETED`
- `UNKNOWN_AFTER_DISCONNECT`
- `BLOCKED`

The phases are ordinal observations, not progress quantities. A phase can stay
unchanged for an arbitrary duration. The public contract contains no percent,
ETA, frame count, byte count, segment count or remaining-work field.

### 5.2 Cancel state

`RuntimeTranscriptionCancelStateV1` is exactly:

- `NOT_REQUESTED`
- `CANCEL_REQUESTED`
- `CANCELLED_BEFORE_PROVIDER_EFFECT`
- `CANCELLED_AFTER_COOPERATIVE_BOUNDARY`
- `STOP_NOT_CONFIRMED`

Only the two `CANCELLED_*` states are terminal confirmed cancellation outcomes.
`STOP_NOT_CONFIRMED` is blocked and retains the output slot.

### 5.3 Adjudication state and decision

`RuntimeTranscriptionAdjudicationStateV1` is exactly:

- `NOT_REQUIRED`
- `REQUIRED`
- `CLOSED_FAILED_NO_REPLAY`

The only mutating Human decision is
`CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY`. `KEEP_BLOCKED` is a no-effect
decision and is never persisted as proof of stop. There is no retry, reset,
discard, mark-success or force-release decision.

### 5.4 Durable bindings

All JSON records use canonical JSON, `additionalProperties = false`, a
lower-case `sha256:<64 hex>` record digest calculated with `record_sha256`
omitted, and canonical second-precision `YYYY-MM-DDTHH:MM:SSZ` timestamps.
Identifiers must pass their existing Product ID validators. `expected_attempt`
is an integer of at least one; cancellation is unavailable before durable v2
admission. The admission ref must full-match
`task098-runtime-admission:v2:<source 64 hex>:<decision 64 hex>` and its two
digests must equal the record's source and decision coordinates.

R2a defines exactly six immutable record types:

1. `RuntimeTranscriptionCancelRequestV1`, exact keys:
   `contract_version`, `cancel_request_id`, `runtime_operation_id`,
   `slot_operation_id`, `source_asset_sha256`, `runtime_admission_ref`,
   `runtime_request_sha256`, `runtime_decision_sha256`, `expected_attempt`,
   `requested_at`, `no_replay`, `record_sha256`. `contract_version` is `1.0.0`
   and `no_replay` is true.
2. `RuntimeTranscriptionCancelOutcomeV1`, exact keys:
   `contract_version`, `cancel_request_sha256`, `runtime_operation_id`,
   `slot_operation_id`, `source_asset_sha256`, `runtime_admission_ref`,
   `runtime_request_sha256`, `runtime_decision_sha256`, `expected_attempt`,
   `outcome`, `provider_execution_started`, `provider_stop_confirmed`,
   `stop_evidence`, `acknowledged_at`, `no_replay`, `record_sha256`. `outcome`
   is exactly `CANCELLED_BEFORE_PROVIDER_EFFECT`,
   `CANCELLED_AFTER_COOPERATIVE_BOUNDARY`, or `STOP_NOT_CONFIRMED`.
   `stop_evidence` is respectively `PRE_PROVIDER`, `COOPERATIVE_CHECKPOINT`, or
   `NONE`; only the first two require `provider_stop_confirmed = true`.
3. `RuntimeTranscriptionAdjudicationDecisionV1`, exact keys:
   `contract_version`, `adjudication_id`, `runtime_operation_id`,
   `slot_operation_id`, `source_asset_sha256`, `runtime_admission_ref`,
   `runtime_request_sha256`, `runtime_decision_sha256`, `expected_attempt`,
   `decision`, `provider_stop_attested`, `stop_evidence`, `decided_at`,
   `no_replay`, `record_sha256`. `decision` is exactly
   `CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY`; `provider_stop_attested`
   is true and `stop_evidence` is `HUMAN_ATTESTATION`. `KEEP_BLOCKED` creates no
   durable record.
4. `RuntimeTranscriptionTerminalClosureCommitV1`, exact keys:
   `contract_version`, `runtime_operation_id`, `slot_operation_id`,
   `source_asset_sha256`, `prior_runtime_admission_ref`, `expected_attempt`,
   `closure_kind`, `closure_record_sha256`, `commit_barrier_sha256`,
   `generation_absence_observation_sha256`, `terminal_status`,
   `terminal_result_ref`, `operation_cas_committed`, `slot_owner_verified`,
   `committed_at`, `no_replay`, `record_sha256`. `closure_kind` is exactly
   `CONFIRMED_CANCEL` or `HUMAN_ADJUDICATED_FAILED`; `terminal_status` is
   `FAILED`; both booleans are true. This record is the only pure input fact
   that can make `slot_release_allowed = true`; it proves the exact main
   operation CAS has committed but does not itself release the slot.
5. `RuntimeTranscriptionCommitBarrierV1`, exact keys:
   `contract_version`, `runtime_operation_id`, `slot_operation_id`,
   `source_asset_sha256`, `runtime_admission_ref`, `expected_attempt`,
   `barrier_owner`, `closure_record_sha256`, `acquired_at`, `record_sha256`.
   `barrier_owner` is exactly `PUBLICATION` or `TERMINAL_CLOSURE`.
   `closure_record_sha256` is null for `PUBLICATION` and is the exact cancel
   outcome/Human decision digest for `TERMINAL_CLOSURE`.
6. `RuntimeTranscriptionGenerationAbsenceObservationV1`, exact keys:
   `contract_version`, `runtime_operation_id`, `slot_operation_id`,
   `source_asset_sha256`, `runtime_admission_ref`, `expected_attempt`,
   `commit_barrier_sha256`, `observation`, `observed_at`, `record_sha256`.
   `observation` is exactly `EXACT_GENERATION_ABSENT` or
   `PRESENT_PARTIAL_OR_UNKNOWN`. Only the former can support terminal closure.

Every outcome/decision/barrier/observation/commit repeats and must exactly equal
the coordinates of its predecessor. A terminal commit's closure, barrier,
absence-observation digests and `terminal_result_ref` must identify the exact
cancel outcome or Human decision.
Records cannot be mixed between attempts, operations, slots, sources or
admission decisions.

Typed durable refs are exactly:

- cancel request: `task098-runtime-cancel-request:v1:<cancel-request record 64 hex>`;
- cancel outcome on the control row: `task098-runtime-cancel-outcome:v1:<cancel-outcome record 64 hex>`;
- confirmed cancel closure: `task098-runtime-cancelled:v1:<cancel-outcome record 64 hex>`;
- adjudicated failed closure: `task098-runtime-adjudicated-failed:v1:<decision record 64 hex>`.
- publication/terminal barrier: `task098-runtime-commit-barrier:v1:<barrier record 64 hex>`.
- terminal commit on the control row: `task098-runtime-terminal-commit:v1:<commit record 64 hex>`.

Parsing uses full-match and exact lower-case round-trip. A
`STOP_NOT_CONFIRMED` outcome has no terminal closure ref and cannot produce a
terminal commit. Unknown versions/fields/enums, booleans encoded as integers,
noncanonical timestamps, digest mismatch or altered coordinates fail closed.

R2a additionally defines one immutable, non-durable reducer input type,
`RuntimeTranscriptionLeaseFactV1`, with exact fields `production_job_id`,
`project_id`, `source_asset_id`, `source_asset_sha256`, `operation_id`,
`command_type`, `idempotency_key`, `status`, `attempt` and `result_ref`. The
reducer derives the neutral guard key and expected v2 owner ref from the
concrete Product/source coordinates. A lease is valid only when command type is
`task036.local_transcription.cross_version_guard.v1`, idempotency key equals the
derived guard key, status is `IN_PROGRESS`, attempt is zero, and result ref is
`task098-runtime-owner:v2:<derived guard digest>`. No caller-supplied
`lease_valid` boolean is accepted. The fact is a read-only store projection; it
has no record SHA and is never persisted by R2a.

### 5.5 Pure reducer input and output

The reducer consumes only immutable typed facts:

- current v2 operation status/attempt/ref;
- current slot status/owner;
- optional exact `RuntimeTranscriptionLeaseFactV1` plus its concrete coordinates;
- R1b recovery classification;
- optional in-process phase observation;
- optional typed cancel request/outcome;
- optional typed Human adjudication decision;
- optional exact commit-barrier and generation-absence records;
- optional exact `RuntimeTranscriptionTerminalClosureCommitV1`.

It returns one exact public-safe projection with keys:

- `control_mode = PHASE_ONLY_V1`
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

The public projection contains no operation/slot ID, source hash, digest,
timestamp, path, private body, exception, stack, thread identity, model locator,
percentage or ETA. `slot_release_allowed` is explanatory only; it cannot cause a
release and is true only for an exact terminal-closure commit record. The public
projection therefore has exactly twelve keys. When
`provider_execution_known = false`, `provider_execution_started` is always
false and means "not positively known", not "proved never started".

`available_action` is exactly `NONE`, `REQUEST_CANCEL`, or
`CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY`. `status_label` is exactly one
of the labels in the table below. The reducer applies rows from top to bottom;
the first match wins. Any record supplied in a row must validate and bind every
coordinate above, otherwise row 1 wins.

| Priority | Normalized durable/observed facts | Phase | Cancel | Adjudication | Action | Status label | Started | Known | Stop confirmed | Stop evidence | Release | No replay |
|---:|---|---|---|---|---|---|---:|---:|---:|---|---:|---:|
| 1 | unknown/corrupt/foreign fact, coordinate mismatch, impossible record combination, or slot not exactly owned where ownership is required | `BLOCKED` | `STOP_NOT_CONFIRMED` | `REQUIRED` only for a valid typed-admission PARTIAL; otherwise `NOT_REQUIRED` | `NONE` | `状態が不正なため操作できません` | false | false | false | `NONE` | false | true |
| 2 | exact `PUBLICATION` barrier acquired while the main operation still has its typed admission ref | `PUBLICATION_COMMITTING` | `NOT_REQUESTED` | `NOT_REQUIRED` | `NONE` | `結果の確定処理が開始されています` | true | true | false | `NONE` | false | true |
| 3a | exact cancel-owned `TERMINAL_CLOSURE` barrier without an exact terminal commit, including generation present/partial/unknown | `BLOCKED` | `STOP_NOT_CONFIRMED` | `NOT_REQUIRED` | `NONE` | `キャンセル終了処理を安全に確定できません` | false | false | false | `NONE` | false | true |
| 3b | exact Human-owned `TERMINAL_CLOSURE` barrier without an exact terminal commit, including generation present/partial/unknown | `BLOCKED` | `STOP_NOT_CONFIRMED` | `REQUIRED` | `NONE` | `Human終了処理を安全に確定できません` | false | false | false | `HUMAN_ATTESTATION` | false | true |
| 4 | exact terminal commit for confirmed cancel before Provider effect | `BLOCKED` | `CANCELLED_BEFORE_PROVIDER_EFFECT` | `NOT_REQUIRED` | `NONE` | `Provider開始前にキャンセルしました` | false | true | true | `PRE_PROVIDER` | true | true |
| 5 | exact terminal commit for confirmed cooperative cancel | `BLOCKED` | `CANCELLED_AFTER_COOPERATIVE_BOUNDARY` | `NOT_REQUIRED` | `NONE` | `協調停止を確認してキャンセルしました` | true | true | true | `COOPERATIVE_CHECKPOINT` | true | true |
| 6 | exact terminal commit for Human-adjudicated failed closure | `BLOCKED` | `STOP_NOT_CONFIRMED` | `CLOSED_FAILED_NO_REPLAY` | `NONE` | `Human確認により失敗終了しました（再実行なし）` | false | false | false | `HUMAN_ATTESTATION` | true | true |
| 7 | valid cancel request with no cancel outcome and no terminal commit | current observed phase or `UNKNOWN_AFTER_DISCONNECT` | `CANCEL_REQUESTED` | `NOT_REQUIRED` | `NONE` | `キャンセルを要求しました。停止確認中です` | true only for observed `PROVIDER_RUNNING` or `PUBLICATION_VALIDATING`; otherwise false | false only for `UNKNOWN_AFTER_DISCONNECT`; otherwise true | false | `NONE` | false | true |
| 8 | valid cancel request plus its exact `STOP_NOT_CONFIRMED` outcome, without terminal commit | `UNKNOWN_AFTER_DISCONNECT` | `STOP_NOT_CONFIRMED` | `NOT_REQUIRED` | `NONE` | `Provider停止を確認できません` | exact outcome value | true | false | `NONE` | false | true |
| 9 | v2 PARTIAL + typed admission ref + exact slot owner + no acquired barrier; generation absence is rechecked only after apply wins the barrier | `UNKNOWN_AFTER_DISCONNECT` | `STOP_NOT_CONFIRMED` | `REQUIRED` | `CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY` | `Provider停止のHuman確認が必要です` | false | false | false | `NONE` | false | true |
| 10 | publication-bound PARTIAL classified `RECOVERABLE_PUBLICATION` | `PUBLICATION_COMMITTING` | `NOT_REQUESTED` | `NOT_REQUIRED` | `NONE` | `既存結果の復旧が必要です` | true | true | false | `NONE` | false | true |
| 11 | publication-bound COMPLETED classified `VERIFICATION_ONLY` | `COMPLETED` | `NOT_REQUESTED` | `NOT_REQUIRED` | `NONE` | `音声認識は完了しています` | true | true | false | `NONE` | false | true |
| 12 | IN_PROGRESS, no cancel request/barrier, phase `ADMISSION` | `ADMISSION` | `NOT_REQUESTED` | `NOT_REQUIRED` | `REQUEST_CANCEL` | `実行許可を確認中です` | false | true | false | `NONE` | false | true |
| 13 | IN_PROGRESS, no cancel request/barrier, phase `PROVIDER_STARTING` | `PROVIDER_STARTING` | `NOT_REQUESTED` | `NOT_REQUIRED` | `REQUEST_CANCEL` | `音声認識を開始しています` | false | true | false | `NONE` | false | true |
| 14 | IN_PROGRESS, no cancel request/barrier, phase `PROVIDER_RUNNING` | `PROVIDER_RUNNING` | `NOT_REQUESTED` | `NOT_REQUIRED` | `REQUEST_CANCEL` | `音声認識を実行中です` | true | true | false | `NONE` | false | true |
| 15 | IN_PROGRESS, no cancel request/barrier, phase `PUBLICATION_VALIDATING` | `PUBLICATION_VALIDATING` | `NOT_REQUESTED` | `NOT_REQUIRED` | `REQUEST_CANCEL` | `結果を検証中です` | true | true | false | `NONE` | false | true |
| 16 | IN_PROGRESS, phase `PUBLICATION_COMMITTING` without a durable publication barrier | `BLOCKED` | `STOP_NOT_CONFIRMED` | `NOT_REQUIRED` | `NONE` | `結果確定の排他状態を確認できません` | true | true | false | `NONE` | false | true |
| 17 | IN_PROGRESS after disconnect, no trustworthy phase | `UNKNOWN_AFTER_DISCONNECT` | `STOP_NOT_CONFIRMED` | `NOT_REQUIRED` | `NONE` | `実行状態を確認できません` | false | false | false | `NONE` | false | true |
| 18 | PENDING operation before durable admission | `NOT_STARTED` | `NOT_REQUESTED` | `NOT_REQUIRED` | `NONE` | `開始待ちです` | false | true | false | `NONE` | false | true |
| 19 | no v2 operation and no v2 permanent lease | `NOT_STARTED` | `NOT_REQUESTED` | `NOT_REQUIRED` | `NONE` | `音声認識は開始されていません` | false | true | false | `NONE` | false | true |
| 20 | FAILED without an exact accepted terminal commit | `BLOCKED` | `STOP_NOT_CONFIRMED` | `NOT_REQUIRED` | `NONE` | `失敗状態を確認してください` | false | false | false | `NONE` | false | true |

Rows 10 and 11 deliberately expose no A2-R2 action; the separate R1b/R1c action
selector remains authoritative. A2-R2 never shadows RECOVER or VERIFY.
`provider_stop_confirmed` is true only in rows 4 and 5. Human attestation in row
6 remains distinguishable and does not become a technical Provider-stop claim.
Every other row is false. `provider_execution_started` and its knowledge bit are
fixed per row above; no absent or Human-only evidence can prove Provider entry.
`no_replay` is true in every row for this control mode.
Every row representing an existing v2 operation also requires an exact valid
lease fact; a missing/invalid/foreign lease, or a lease without its expected v2
operation, is row 1. Row 19 alone permits lease absence.

## 6. R2b lifecycle design

R2b must use the existing `operations` table and compare-and-set primitives; it
must not migrate the database or add a second state store. Publication and
terminal closure share one deterministic control row. Before the first
immutable generation/publication write, the worker and closure path race one
CAS from the same expected control status/ref: the worker binds a
`PUBLICATION` barrier and the closure path binds a `TERMINAL_CLOSURE` barrier.
Exactly one wins. A publication winner makes cancel/adjudication unavailable; a
closure winner makes every later worker publication write fail closed.

The control-row transitions are closed:

- reserve: `PENDING / null`;
- cancel request: `PENDING / null -> IN_PROGRESS / cancel-request-ref`;
- publication barrier: `PENDING / null -> IN_PROGRESS / publication-barrier-ref`;
- cancel-owned closure barrier: `IN_PROGRESS / cancel-request-or-outcome-ref -> PARTIAL / terminal-barrier-ref`;
- Human-owned closure barrier: `PENDING / null -> PARTIAL / terminal-barrier-ref`;
- terminal commit: `PARTIAL / exact-terminal-barrier-ref -> COMPLETED / terminal-commit-ref`;
- publication completion: the main operation binds its publication SHA first, then the control row moves `IN_PROGRESS / exact-publication-barrier-ref -> COMPLETED / same-publication-barrier-ref`.

No other status/ref transition is accepted. Both barrier contenders use the
same initial row and exact expected ref, so a cancel request that wins also
prevents a later publication barrier. A `STOP_NOT_CONFIRMED` outcome may replace
only the matching cancel-request ref on the still-`IN_PROGRESS` row; it grants
neither terminal closure nor publication authority.

1. The worker reserves one deterministic control operation bound to the v2 operation. Preparing or reading status performs no cancellation.
2. A confirmed user request CASes that control row to `IN_PROGRESS` with the exact cancel-request ref. Duplicate requests converge on the same row.
3. Before Provider factory/model/transcribe entry, the worker may acknowledge `CANCELLED_BEFORE_PROVIDER_EFFECT`.
4. After Provider entry, the request remains `CANCEL_REQUESTED` until the lazy segment iterator yields control. The consumer checks the request between segments, closes the iterator, and acknowledges only after `close()` returns successfully and no owned worker remains active.
5. Missing/throwing close, process loss, foreign worker or inability to prove stop yields `STOP_NOT_CONFIRMED`, not cancelled.
6. Cancellation may be acknowledged through `PUBLICATION_VALIDATING` only if terminal closure first wins the shared durable barrier. A worker must win `PUBLICATION` before calling the first immutable-generation writer. An in-process `PUBLICATION_COMMITTING` phase without that barrier is corrupt/blocked.
7. After terminal closure wins the barrier, a trusted bounded reader checks the exact operation generation location. Only complete absence of the directory and every expected child produces `EXACT_GENERATION_ABSENT`. Any directory/file/symlink, partial set, unreadable state, oversized/foreign entry or observation failure produces `PRESENT_PARTIAL_OR_UNKNOWN`; no deletion, overwrite, digest inference or slot release follows.
8. Confirmed closure writes no Transcript/publication. Only an exact closure barrier plus exact generation absence may CAS-close the exact v2 operation as `FAILED` with the typed no-replay closure ref. A terminal commit record is then bound to the control row, after which only the exact slot still owned by that operation may move from `IN_PROGRESS` to reusable `PENDING`. The permanent v2 lease remains unchanged.
9. Any CAS mismatch keeps the slot and reports Human review required. No compensating replay or blind repair occurs. A crash after either barrier is conservative: publication barrier follows R1b evidence/recovery rules; incomplete terminal closure remains BLOCKED with the slot retained.

No existing v1 Provider call shape changes. Any optional checkpoint/cancel hook is
v2-only, defaults to absent, and preserves the legacy `transcribe(request)` path
byte/behavior identity.

## 7. R2c Human adjudication design

Human adjudication is offered only when R1b classifies the exact v2 operation as
`ADJUDICATION_REQUIRED_NO_PUBLICATION`. That classifier is one input, not
authority for lease, slot ownership or filesystem absence. Conditions are
stage-specific:

- reducer/prepare and apply before barrier acquisition require operation
  `PARTIAL` with the exact typed admission ref/attempt, the concrete valid v2
  lease fact, slot `IN_PROGRESS` with `result_ref == runtime_operation_id`, and
  control row `PENDING / null` with no prior barrier;
- after terminal-barrier acquisition, generation observation and main-operation
  CAS require the same PARTIAL/admission/lease/slot facts plus control row
  `PARTIAL / exact-terminal-barrier-ref`;
- binding the terminal commit requires main operation `FAILED` with the exact
  adjudicated closure ref, unchanged valid lease, exact slot ownership, and
  control row `PARTIAL / exact-terminal-barrier-ref`;
- final slot release requires main operation `FAILED` with that exact closure
  ref, unchanged valid lease, control row
  `COMPLETED / exact-terminal-commit-ref`, and slot `IN_PROGRESS` with
  `result_ref == runtime_operation_id`. It does not require the former
  PARTIAL/admission ref or absence of a barrier.

The application prepares a server-held, expiring, single-use confirmation bound
to the full durable snapshot. The UI states that the decision does not recover
audio, does not declare transcription successful, and permanently closes this
operation without replay. Apply revalidates every coordinate and requires the
explicit decision `CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY`.

On successful revalidation, the application records the typed Human decision,
wins the shared terminal-closure barrier, proves exact generation absence,
CAS-closes the v2 operation to `FAILED` with the adjudicated no-replay ref, binds
the terminal commit, and then releases the exact slot. JavaScript sends only
the server-held single-use confirmation ID; all coordinates and the selected
decision remain server-held. `KEEP_BLOCKED`, cancellation of the confirmation,
expiry, duplicate use, stale snapshot or active-worker evidence detected before
barrier acquisition has zero operation/slot/Provider effect. A mismatch or
unsafe generation observation detected after terminal-barrier acquisition keeps
that barrier durably bound and reports BLOCKED; it performs no further main
operation CAS, control commit, slot release or Provider effect and never rolls
the barrier back.

## 8. Failure and recovery semantics

- Confirmed cancellation: terminal failed/no-replay, slot safely released, no Transcript.
- Cancel requested but not acknowledged: active/unknown, slot retained.
- Typed-admission PARTIAL after restart: Human adjudication required, slot retained.
- Human-confirmed stopped closure: terminal failed/no-replay, slot safely released.
- Publication digest bound: R1b recover/verify only; cancellation/adjudication unavailable.
- Publication barrier bound without a publication digest: blocked, slot retained; no Human override.
- Any unbound generation directory/file, partial set or unreadable generation state: blocked, slot retained; no deletion or digest inference.
- Corrupt/foreign/unknown state: blocked, slot retained, no repair.

The source's permanent v2 lease means a closed operation cannot be crossed into
v1. The existing operation key means the same v2 request cannot re-enter
Provider. A future user-requested retry would require a separate, newly designed
Task and must not be inferred from A2-R2.

## 9. R2a implementation allocation proposed for Judge

Only after design acceptance, R2a may modify:

- `src/ai_video_production/task098_runtime_transcription_control.py` (new)
- `schemas/task098-runtime-transcription-control.schema.json` (new)
- `src/ai_video_production/schema_resources/task098-runtime-transcription-control.schema.json` (new mirror)
- `tests/test_task098_runtime_transcription_control.py` (new)
- bounded `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md`, `docs/ai-team/tasks/TASK-098/**`

R2a must not modify the store, TASK-023 Provider, TASK-036 engine, launcher,
pre-edit runtime, Shell UI, first-run, CLI, packaging or dependency files.

## 10. R2a acceptance matrix

1. Runtime/schema/mirror canonical equality, exact keys, hash, round-trip, unknown-field and tamper tests pass.
2. Every enum value and every invalid/unknown value is covered.
3. Reducer covers no operation, PENDING, IN_PROGRESS, typed-admission PARTIAL, publication PARTIAL, COMPLETED, FAILED, corrupt and foreign facts.
4. `CANCEL_REQUESTED` never sets `provider_stop_confirmed` or `slot_release_allowed` true.
5. Only cross-validated `CANCELLED_*` or `CLOSED_FAILED_NO_REPLAY` may set `slot_release_allowed` true.
6. `STOP_NOT_CONFIRMED`, stale attempt, wrong slot owner, changed ref and malformed coordinates are BLOCKED with no action.
7. Publication-bound PARTIAL/COMPLETED exposes only R1b recovery/verification, never cancel/adjudicate.
8. Publication/terminal barriers, generation-absence observations and terminal commits require exact predecessor digests and coordinates; missing/mixed records are BLOCKED.
9. A terminal barrier with `PRESENT_PARTIAL_OR_UNKNOWN` never creates a terminal commit or release permission.
10. A cancel request without outcome maps row 7; the same request plus its exact `STOP_NOT_CONFIRMED` outcome maps row 8 and cannot be shadowed by row 7.
11. Lease facts validate only from concrete coordinates; missing, wrong-version, wrong-key, wrong-owner, nonzero-attempt or lease-without-operation cases map row 1.
12. Public projection has the exact twelve keys, exact action/label mapping and contains none of the prohibited fields.
13. Every priority row asserts exact `provider_execution_started`, `provider_execution_known`, `provider_stop_confirmed`, `slot_release_allowed` and `no_replay` values; only rows 4/5 confirm technical Provider stop.
14. No percentage/ETA/count field exists anywhere in the schema or projection.
15. No store/filesystem/thread/Provider/model/network/native/private-media effect occurs in R2a tests.
16. R1a/R1b/R1c focused contract and presentation regression remains green.
17. Independent Critic, Tester and Judge report zero unresolved Critical/High.
18. Durable external Evidence is persisted and read back before commit.

Future R2b/R2c reviews must additionally require deterministic concurrency
tests in both winner orders for publication barrier versus cancel request and
Human closure; crash at every barrier/main-CAS/control-commit/slot-release
boundary; exact absence, complete presence, partial presence, symlink,
unreadable and observation-failure generation cases; duplicate/stale Human
confirmation; and proof that a losing old worker performs zero immutable/fixed
publication writes after terminal barrier acquisition.

## 11. Context scope

`MUST READ` for R2a:

- `docs/ai-team/current-state.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- this design
- R1b recovery classifier and typed admission-ref section in `task036_product_ports.py`
- A2-R0/R1a runtime contract/schema style
- focused TASK-098 runtime contract/control tests

`READ IF REQUIRED`: exact store CAS signature and R1c public projection tests.

`DO NOT READ BY DEFAULT`: archive/history, unrelated Tasks/subsystems, full BAI
Development OS, native/package/release code, private media and TASK-097 training
artifacts.

## 12. Review gate

This document is not implementation authority. Independent DEV-3 Critic and
Tester must inspect state truthfulness, no-replay, slot-release ordering,
schema/public-data minimization and the exact R2a file ceiling. Judge may accept,
reject or narrow R2a allocation. R2b/R2c remain unallocated regardless of R2a
acceptance.

## 13. Review outcome

- Independent Critic final: `ACCEPT / 0 Critical / 0 High / 0 Medium / 0 Low`.
- Independent Tester final: `PASS / 0 Critical / 0 High / 0 Medium / 0 Low`.
- Independent Judge final: `ACCEPT / R2a LIMITED IMPLEMENTATION ALLOCATED / 0 Critical / 0 High / 0 Medium / 0 Low`.
- Allocation: only the four R2a implementation/test/schema files in section 9 plus bounded TASK-098/current-state/task-index documentation.
- R2b/R2c, store, TASK-023 Provider, TASK-036 engine/Shell, serialized v2/native, private media and external effects remain unallocated.
