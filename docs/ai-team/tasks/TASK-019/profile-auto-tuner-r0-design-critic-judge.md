# TASK-019 R0 Profile Auto-Tuner — Design / Critic / Judge

## Decision

`IMPLEMENT_HUMAN_REVIEWED_BOUNDED_TUNING_PROPOSAL`

## Design

- Baseline and proposed profiles are real TASK-008 `ScoringProfile` values; proposed rows may change only declared weights and version.
- TASK-015 feedback is bound by exact snapshot SHA and serialized source state. Non-COMPLETE feedback cannot produce a review-ready proposal.
- `TuningPolicy` closes changed-rule count, absolute delta, minimum holdout samples/improvement and per-holdout regression cap.
- Holdout rows preserve exact manifest, sample count, baseline/proposed fixed-point quality and current-valid state.
- Weighted improvement uses integer arithmetic. Missing/UNKNOWN/stale/revoked Evidence is never defaulted.
- Baseline profile digest is the rollback coordinate, but rollback execution remains false.
- `READY_FOR_HUMAN_REVIEW` is advisory only; profile write/promotion/Edit Plan/external effects remain false.

## Negative matrix

- same/invalid proposed version
- unknown, duplicate, unchanged or cap+1 adjustment
- weight total not exact 1000 or non-weight rule drift
- empty/duplicate holdout rows or reused manifest
- total sample cap+1, insufficient sample or no measured improvement
- one holdout regression hidden by aggregate improvement
- incomplete feedback, UNKNOWN, STALE or REVOKED Evidence promoted ready
- manual state/profile projection laundering
- nested profile/policy, rollback or outer digest tamper
- API/Credential/filesystem/network/media/provider/subprocess access
- review-ready treated automatic write/promotion/rollback/Edit Plan authority

## Builder / Completeness Critic

Finding: an averaged improvement alone can hide a severe regression on one holdout partition.

Correction: every holdout retains an exact row and a policy-bounded regression check; any excessive row blocks review readiness even when aggregate improvement is positive.

Residual C/H/M: `0/0/0`.

## Security / Authority Critic

Finding: the name “Auto-Tuner” could be interpreted as permission to persist or promote a profile.

Correction: the only output is an immutable proposal with Human review required and all write/promotion/rollback/Edit Plan/external-effect flags false.

Residual C/H/M: `0/0/0`.

## Operations / Compatibility Critic

Finding: free-form feature changes or floats would break TASK-008 compatibility and cross-platform determinism.

Correction: feature/rule identity is projected from TASK-008, only integer weights change, and all evaluation arithmetic/canonical serialization is integer-based.

Residual C/H/M: `0/0/0`.

## Independent Judge

- TASK-008/015 exact reuse and no duplicate scoring/feedback logic: PASS
- adjustment/policy/holdout/rollback closure: PASS
- lifecycle states and no-effect authority boundary: PASS
- deterministic canonical hash/schema mirror: PASS
- focused/full regression and hosted checks: PENDING EVIDENCE
- residual C/H/M: `0/0/0`

`JUDGE=PASS_LOCAL_PENDING_HOSTED_EVIDENCE`
