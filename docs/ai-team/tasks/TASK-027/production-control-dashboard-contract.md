# TASK-027 / TASK-037..041 — Production Control Dashboard Contract Ver.1.0

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / READ_ONLY_PROJECTION_IMPLEMENTED`
- UI target: Unified Desktop Application Production / Review surfaces

## Purpose

Provide one read-only operator projection over the Human-approved Production Plan, bounded production budget, Scene Asset Slots/Candidates, Audit/Human Decision, Prompt/Generation Attempt, Continuity and Audio Placement state.

The dashboard is not an autonomous repair engine and does not own Provider execution.

## Preconditions

Before any dashboard state is produced:

1. the exact Human-approved TASK-027 Plan -> Blueprint -> Scene -> Slot trace must pass;
2. the TASK-037..041 cross-store Production Bundle validator must pass in strict bound-output mode;
3. the budget ledger must match the exact approved Plan ID, currency and Human-approved ceiling.

A collection of individually valid JSON snapshots is not enough when their cross-store references differ.

## Scene projection

Each Scene exposes concise counts/status for:

- required/locked/empty/stale Slots;
- Candidates and READY_FOR_AUDIT Candidates;
- Audit records and Human decisions;
- Human NEEDS_REGENERATION decisions;
- generation attempts/failures;
- continuity edges/unresolved continuity;
- Audio placement review state.

Attention reasons are structured values, not hidden heuristics. Initial reasons include:

- `REQUIRED_SLOT_EMPTY`
- `STALE_SLOT`
- `HUMAN_AUDIT_DECISION_REQUIRED`
- `HUMAN_REGENERATION_REQUESTED`
- `GENERATION_FAILURE_RECORDED`
- `CONTINUITY_REVIEW_REQUIRED`
- `AUDIO_PLACEMENT_REVIEW_REQUIRED`

## Authority

The dashboard does not convert an AI score or visual PASS/FAIL into Human acceptance. It does not start generation/regeneration, buy credits, change auto-top-up, repair stale state, lock Candidates, write Resolve, render or publish.

Any later UI command must route through its owning Application Service / Authority Gateway rather than mutating these registries from the projection.

## Budget

The visible budget summary is Plan-scoped and includes ceiling, used/reserved, committed and remaining amounts. It explicitly carries no credit-purchase or automatic-top-up authority.

## UI direction

The future TASK-036/Production Control integration should follow the Owner's Vrew × Premiere Pro × DaVinci Resolve NLE direction:

- Scene/Asset/Audit details may occupy left/right panels;
- Viewer/Timeline remain the editing canvas;
- Production status is a structured workspace/panel, not a generic SaaS dashboard replacing the NLE.

## Acceptance

- deterministic projection hash;
- no host path persistence;
- exact Plan and cross-store validation first;
- Human authority preserved;
- no automatic repair/regeneration/provider execution;
- inconsistent budget/Plan binding fails closed.
