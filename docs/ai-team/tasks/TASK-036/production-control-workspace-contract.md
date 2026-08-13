# TASK-036 — Production Control Workspace Contract Ver.1.0

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / READ_ONLY_PROJECTION_IMPLEMENTED`
- Depends on: TASK-027/TASK-037..041 Production Dashboard projection

## UI role

Production Control must not turn BAI Video Production into a generic SaaS dashboard. In the Owner-approved Vrew × Premiere Pro × DaVinci Resolve direction, Viewer and Timeline remain the primary editing canvas.

Production Control state is displayed as a dedicated workspace and/or docked side panel containing Plan, budget, Scene status, Slot/Candidate progress and structured attention reasons.

## Authority boundary

This projection intentionally exposes no mutation commands. Human Candidate decisions, regeneration, Continuity resolution, Audio placement acceptance and paid generation continue through their owning Application Service and explicit Authority/Gate contracts.

## Data source

The workspace accepts only a validated `ProductionDashboardReport`, which already proves:

- Human-approved Plan trace;
- exact Plan-scoped budget binding;
- TASK-037..041 cross-store consistency.

The shell does not reconstruct these truths from loose UI state.

## Native acceptance later

TASK-036 Windows native acceptance must verify that the Production Control panel can coexist with the Viewer/Timeline at supported resolutions/scaling without hiding primary editing controls.
