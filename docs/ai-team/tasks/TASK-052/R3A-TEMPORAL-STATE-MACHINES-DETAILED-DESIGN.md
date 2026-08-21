# TASK-052 R3A Temporal State Machines Detailed Design

Status: IMPLEMENTATION BOUND

Governance: DEV-3 HIGH ASSURANCE

Scope: deterministic temporal reconciliation only

## 1. Responsibility boundary

R3A converts ordered detector observations into stable, subject-bound DbD state. A single-frame classifier remains Evidence and cannot directly become final event truth.

R3A owns:

- profile-bound debounce and hysteresis thresholds;
- generator-remaining temporal majority and impossible-increase detection;
- per-`match_id + survivor_slot` chase phase;
- per-subject Survivor state transition validation;
- per-subject accumulated hook count and HUD/state reconciliation;
- explicit abstention and contradiction results with evidence references.

R3A does not own detector inference, CGEL event emission, Timeline mutation, provider execution, real-media acceptance, or Production activation. Event production and Resolver integration are R3B.

## 2. Canonical identities and inputs

- Generator state is keyed by `match_id`.
- Survivor state is keyed only by `match_id + survivor_slot`, where the slot is `0..3`.
- Survivor inputs are existing `DbDObservationEnvelope` values for `CHASE_STATE`, `SURVIVOR_STATE`, and `HOOK_COUNT`.
- An envelope's `evidence_ref` is retained when present; otherwise its immutable `observation_id` is the trace reference.
- Generator input is a bounded `0..5` integer observation with frame, confidence, and Evidence reference.
- Frames must be strictly increasing within each signal key. Replayed or out-of-order input is a contradiction and never mutates stable state.

## 3. Profile-bound policy

All thresholds belong to `DBDTemporalProfile`; none is an implicit global truth. The profile defines minimum confidence, history window, generator vote count, Survivor state vote count, hook-count vote count, chase-start frames, and chase-end frames.

Unknown or below-threshold input abstains, clears incomplete debounce evidence, and does not erase a previously stable state. Unknown profile/alignment is represented upstream by `UNKNOWN` or below-threshold evidence and therefore cannot confirm state.

## 4. State contracts

### 4.1 Generator remaining

The machine confirms a value only when the latest value wins a unique temporal majority and reaches the configured minimum observations. Confirmed remaining count may stay unchanged or decrease. Any attempted increase is `NEEDS_REVIEW` with stable state unchanged. Values outside `0..5` are contradictions.

### 4.2 Chase

Each Survivor follows:

```text
NOT_CHASE -> CHASE_CANDIDATE -> CHASE_ACTIVE
CHASE_ACTIVE -> CHASE_END_CANDIDATE -> NOT_CHASE
```

Active evidence advances the start side; inactive evidence advances the end side. Opposing evidence cancels only the incomplete candidate phase. No phase or streak is shared across Survivor subjects.

### 4.3 Survivor state

Stable state changes require consecutive admitted observations. The observable transition graph permits normal injury/down/hook/recovery progress and missed-frame skips, while `DEAD` and `ESCAPED` are terminal. Invalid transitions return `NEEDS_REVIEW`, do not advance state, and clear incomplete candidate evidence.

### 4.4 Hook count

Hook count is accumulated independently for every Survivor. Entering `HOOKED` from another confirmed state advances the same subject's accumulated count, capped at two, only when a hook-count baseline is already known. A stream that begins in `HOOKED` cannot guess whether that is the first or second hook and keeps count `UNKNOWN`. HUD hook-count observations may establish an initially unknown count or advance it by exactly one after debounce. Decrease or a jump larger than one is a contradiction. Other Survivor slots cannot affect it.

## 5. Decision semantics

Every consumption returns one of:

- `ABSTAINED`: unknown/low-confidence Evidence;
- `CANDIDATE`: debounce/hysteresis is incomplete;
- `CONFIRMED`: stable state advanced;
- `UNCHANGED`: admitted Evidence agrees with stable state;
- `NEEDS_REVIEW`: invalid value, ordering conflict, impossible increase, or invalid transition.

The result carries signal, exact subject, frame, observed/stable values, effective confidence, Evidence references, and deterministic reason codes. R3B must not turn `ABSTAINED`, `CANDIDATE`, or `NEEDS_REVIEW` into an auto-confirmed event.

## 6. Acceptance

- Generator majority, decrease, invalid value, and impossible increase are tested.
- Chase start/end hysteresis and cross-subject isolation are tested.
- Survivor valid recovery and invalid terminal transitions are tested.
- Hook accumulation and cross-slot isolation are tested.
- Unknown, low-confidence, and out-of-order observations never confirm or mutate stable truth.
- Existing R2A observation and affected detector/Resolver contracts remain green.
