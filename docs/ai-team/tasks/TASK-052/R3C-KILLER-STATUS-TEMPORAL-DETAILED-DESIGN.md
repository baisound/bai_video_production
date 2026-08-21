# TASK-052 R3C Killer and Status Temporal Detailed Design

Status: IMPLEMENTATION BOUND

Governance: DEV-3 HIGH ASSURANCE

## Responsibility

R3C reconciles already-observed killer-specific HUD effects and positive/negative status effects into stable state Evidence. It performs no image segmentation, classification, teacher-data mutation, CGEL emission or Production Timeline mutation.

## Profile routing

- Killer effects are registered by exact `killer_id + effect_id`.
- Unknown killers abstain and run no killer-specific positive route.
- An effect registered to another killer is a namespace contradiction requiring review.
- Status effects are registered with canonical polarity, source kind and scope.
- Polarity/source mismatch is a hard-negative contradiction, not an alternate positive label.
- Monotonic stage/progress and maximum ranges are configured per effect; decay is allowed only when the effect profile permits it.

## Temporal behavior

Appearance, disappearance and value changes have separate profile thresholds. Low-confidence and unknown observations abstain. Out-of-order input, inactive observations carrying active values, range violations and configured monotonic regressions require review and never mutate stable state. Any contradiction clears incomplete candidate Evidence before recovery.

State is keyed by domain, match, optional Survivor slot and effect identity. Multiple positive and negative effects can therefore remain active independently in one frame. A visible-region detector must provide explicit inactive observations for disappearance; missing/unreadable regions must provide unknown Evidence and cannot imply disappearance.

## Output boundary

Decisions retain before/after state, confidence, frame, exact scope, Evidence references and deterministic reason codes. Status-effect decisions remain state Evidence. No new CGEL event type is introduced by R3C.

## Acceptance

- unknown Killer and unregistered effects abstain;
- Killer namespace, status polarity/source and scope mismatches require review;
- appearance/value/disappearance thresholds are independently enforced;
- configured monotonic regression cannot advance state;
- contradiction clears incomplete candidate history;
- multiple effect identities and polarities do not contaminate each other;
- TASK-049/TASK-052 affected regression remains green.
