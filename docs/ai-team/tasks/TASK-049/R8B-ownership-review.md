# TASK-049 R8B — Existing BVP Adoption Ownership Review

## Result

`PARKED / NO_SAFE_UNIFIED_ADOPTION_CONTRACT_YET`

## Reviewed paths

Bounded review only:

- `production_control.py`
- `production_control_application.py`
- `production_proposal.py`
- `audio_placement.py`
- `audio_placement_application.py`
- `subtitle_workspace.py`

## Finding

R8A produces a cross-domain **proposal bundle**, not a generated media Asset.
The currently reviewed BVP adoption contracts are intentionally more specific:

- `ProductionControlApplicationService.register_candidate(...)` requires an existing Slot plus an `asset_id` and `asset_sha256`;
- Candidate ACCEPT/LOCK already has Human authority and must not be duplicated;
- Narration placement requires a generated narration Asset before `AudioPlacement` can be constructed;
- Subtitle Workspace owns subtitle editing/review state and should not be bypassed;
- highlight/cut adoption is not represented by the reviewed AssetCandidate contract.

Therefore a generic R8B adapter that converts all R8A Highlight/Narration/Subtitle proposals directly into Production state would either invent a second authority or fabricate Assets/Slots that do not yet exist.

## Decision

Do **not** implement a broad R8B mutation adapter yet.

Preserve R8A as the canonical side-effect-free handoff and split future adoption by the existing owning domain after the exact Product flow is decided:

1. Highlight proposal -> existing cut/edit proposal authority;
2. Narration proposal -> existing Voice/Narration generation -> Asset -> Production candidate/placement authority;
3. Subtitle proposal -> existing Subtitle Workspace review/adoption authority.

Each adapter must retain `bundle_id`, `event_id@revision`, Event hash, Commentary candidate hash, Evidence refs and Knowledge-ref hashes.

This parked state is safer than creating a new shared edit/adoption authority while TASK-036 P-UX-2 owns the shared V6 functional-flow lane.
