# TASK-098 A4-R0 Review Completion / Viewport Contract Pre-Mutation Review

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A4-R0`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Starting HEAD: `c40b3c90ce5ac396b97383080652e8f665f0dd85`
- Direct dependency: `TASK-098 A3-R3 COMPLETE`
- Branch: `codex/task-098-a4-review-workspace`
- Status: `DESIGN_ACCEPTED_FOR_BOUNDED_IMPLEMENTATION`

## 1. Authority and goal

The Owner's `2026-09-19` autonomous staged Universal WAV Review integration
authority reaches A4 through the existing TASK-098 roadmap. A4-R0 is the first
bounded A4 Atomic Unit. It implements only:

1. the completion classifier required by the accepted A1 contract;
2. exact half-open time-to-sample projections at the TASK-041 fixed 48 kHz
   boundary; and
3. immutable independent waveform-horizontal and segment-list scroll state.

It does not open a review workspace, read audio, render a waveform, start
playback, persist a ViewModel, edit a Subtitle Workspace, or connect Product UI.

## 2. Canonical boundary

- TASK-041 remains the owner of policy, source, capability, intent, external
  receipt, Human review decision and Asset/Candidate references.
- TASK-006 remains the owner of canonical Transcript timing and Subtitle
  Workspace revisions/CAS.
- A4-R0 adds no second review store, transcript authority, media source,
  provider, player, waveform engine or durable session.
- `validate_external_review_inclusion()` remains unchanged and continues to
  mean exact inclusion only. A4-R0's classifier is a separate higher-level
  completion proof and never weakens TASK-041.
- Foreign UWR receipt bodies remain unsupported and unread; A5 remains blocked.

## 3. Completion contract

`COMPLETE` requires every condition below:

- TASK-041 inclusion is `ACCEPT_PROVEN_EXTERNAL_REVIEW`;
- receipt `contract_state` is `BOUND_VERIFIED`;
- receipt `external_state` is `COMPLETED`;
- `canonical_persistence_verified` is true;
- requested `AUDITION` implies `audition_completed` is true;
- requested `WAVEFORM_VIEW` implies `waveform_available` is true.

Every failed, cancelled, unknown, null, false, mismatched or missing condition
returns `INCOMPLETE` with closed reason codes. The result never authorizes a
Human decision or claims playback/waveform/media effects.

## 4. Timing and viewport contract

- Microsecond ranges project to covering half-open sample ranges by flooring
  the start and ceiling the exclusive end with integer arithmetic.
- Millisecond ranges use the same rule. At exactly 48 kHz, each millisecond is
  exactly 48 samples.
- Projection is one-way and cannot rewrite Transcript microseconds, Subtitle
  Workspace milliseconds or TASK-041 source sample truth.
- Waveform horizontal offset/span and segment-list vertical index/count are
  distinct immutable fields. Each scroll operation changes only its own axis
  and clamps to its own source bounds.
- No text, audio/media bytes, path, credential or private receipt body is
  present in the A4-R0 contract.

## 5. Atomic decomposition

- `A4-R0` (this Unit): pure completion, time projection and viewport contract.
- `A4-R1` (fresh review required): ephemeral exact-hash coordinator joining one
  TASK-041 source/intent with one Transcript digest and one Subtitle Workspace
  revision; no persistence or media bytes.
- `A4-R2` (fresh review required): unified Product review UI and injected
  external playback/waveform capability; native/runtime effects remain gated.

A4-R0 completion allocates neither A4-R1 nor A4-R2 implementation.

## 6. Allowed files

- `src/ai_video_production/task098_review_workspace_contract.py`
- `tests/test_task098_review_workspace_contract.py`
- this review
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/evidence/a4-r0-review-completion-viewport-20260922-r01.md`
- bounded `docs/ai-team/current-state.md` and `docs/ai-team/task-index.md` status
  synchronization at completion only

TASK-041/TASK-006 source, schema and tests; Shell/UI; providers; dependencies;
package/installer/Product version; media/private assets must not change.

## 7. Acceptance

- exact TASK-041 inclusion can still be `INCOMPLETE` for every missing
  completion condition;
- requested-operation implications are exact and unrequested operations do not
  invent requirements;
- mismatch reasons remain visible and deterministically ordered;
- projection boundary/rounding tests cover 1 microsecond, exact boundaries,
  and non-integral end points without float arithmetic;
- waveform and segment scroll operations preserve the other axis and clamp at
  zero/end under positive and negative deltas;
- booleans and invalid/unbounded integers are rejected as numeric input;
- all effect flags remain false and no path/body field is representable;
- focused TASK-098/TASK-041/TASK-006 regression, compile, diff/scope and durable
  Evidence read-back pass.

## 8. Critic / Tester / Judge decision

### Critic

- High: TASK-041 inclusion alone could be misreported as completed review.
  Corrected by the separate six-condition completion classifier.
- High: a viewport object could become a second durable review session.
  Corrected to a frozen, serialization-free value with no store or filesystem
  dependency.
- High: float conversion could drift half-open boundaries and rewrite timing.
  Corrected to integer floor/ceil projection with no reverse conversion.
- Medium: shared scroll state could couple waveform and segment navigation.
  Corrected to separate immutable axes and axis-specific reducers.
- Medium: adding text/media/path fields would duplicate canonical/private body.
  Corrected by a closed body-free contract surface.

Final design finding count: `Critical 0 / High 0 / Medium 0 / Low 0`.

### Tester

Pure deterministic tests use only in-memory TASK-041 records. No temporary,
native, media, Provider or Product effect is required.

Decision: `PASS / IMPLEMENTATION_TEST_PLAN_ACCEPTED`.

### Judge

The Unit is additive, pure and within the existing A4 roadmap. It preserves
TASK-041/TASK-006 ownership and allocates no runtime/UI effect.

Decision: `ACCEPT / A4-R0_IMPLEMENTATION_ALLOCATED`.
