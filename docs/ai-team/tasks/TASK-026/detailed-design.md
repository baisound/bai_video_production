# TASK-026 — Audio Placement & Bed Worker Detailed Design Ver.1.0

- Date: 2026-08-13
- Status: `OWNER_DIRECTED_FOUNDATION_IMPLEMENTATION / NO_EXTERNAL_WRITE`
- Governance candidate: `DEV-3/4`
- Depends on: TASK-002, TASK-003, TASK-022; generated assets may come from TASK-013/TASK-014; content-aware decisions may consume TASK-007
- Resolve execution owner: TASK-010
- User review surface: TASK-041 / TASK-036

## 1. Objective

Compile reviewed SE/BGM/Narration intent into an exact frame-based, bounded Audio Placement Plan without mutating Resolve.

The plan owns:

- target track role/index;
- bounded snapping;
- requested/effective start;
- requested bed duration;
- deterministic loop segmentation;
- fade metadata;
- gain metadata;
- Preview/Full bed mode;
- TASK-010 compatibility classification.

TASK-010 remains the actual Resolve mutation owner. TASK-026 never calls Resolve directly.

## 2. Bounded snap

A placement request may provide candidate anchors. The worker selects only anchors whose absolute delta is within `snap_tolerance_frames`.

Tie break:

1. smallest absolute delta;
2. lower Timeline frame.

If no candidate is within the tolerance, the requested start is retained. The worker does not drift an effect arbitrarily to reach an anchor.

## 3. Loop / bed semantics

If target duration exceeds source duration:

- `loop=false` -> fail closed;
- `loop=true` -> create repeated source-from-zero segments;
- final segment is truncated to remaining duration;
- no segment exceeds the source Asset duration.

Narration is not loopable in the initial contract.

## 4. Fade / gain

Fade and gain belong to the TASK-026 plan even though the current TASK-010 generic `AudioPlacement` contract cannot apply them.

Therefore:

- a plan with non-zero fade or non-zero gain is valid TASK-026 output;
- it is **not** silently downgraded to a TASK-010 placement;
- `to_task010_audio_placements()` fails closed until the Resolve execution contract supports the requested metadata.

This prevents losing creative audio decisions during integration.

## 5. Preview / Full bed

`PREVIEW` and `FULL` are plan metadata, not separate Asset identities. Provider generation/reuse is upstream. A preview plan can use a shorter desired bed duration; promotion to full creates a new placement plan/version rather than mutating the old plan.

## 6. Human authority

TASK-026 calculates a placement plan. TASK-041/TASK-036 Human review decides whether the placement is accepted. A plan does not authorize Resolve write.

## 7. Acceptance

- exact frame arithmetic;
- snap never exceeds tolerance;
- deterministic tie break;
- loop splits are deterministic and cover exact requested duration;
- narration loop rejected;
- invalid fades rejected;
- gain/fade never silently disappear in TASK-010 conversion;
- no external mutation/provider execution;
- same input produces same plan hash.
