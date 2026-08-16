# P-UX-1C Scenes screen closure — design, Critic, and Evidence

Date: 2026-08-16
Task: TASK-036 / P-UX-1C
Atomic unit: `SCENE_CONTRACT_BROWSER_SURFACE_R0`

## Source and boundary

This unit projects the immutable Blueprint Scene Contract already returned by
TASK-027 `planning_snapshot`. It adds no Scene revision, Timeline finalization,
Provider or media authority. Shared integration files remain unchanged.

## Design

1. Render exact Scene rows from `workspace.blueprint.scenes` with selection,
   frame range, source strategy, generation risk, camera, references and Audio
   requirements.
2. Render exact Blueprint title, rate, total frames and derived display counts.
   Counts are UI projections only; the Blueprint remains Python-owned.
3. Scene selection is ephemeral presentation state and creates no durable
   browser record.
4. Keep Add, Remove, Update and Timeline finalization visible but disabled with
   the exact missing dependency: no typed Blueprint Scene revision service is
   connected.
5. Empty/unavailable Planning states render no sample Scene and no inferred
   Timeline Contract PASS.

## Builder Critic

- High: mock inputs could mutate only browser state and masquerade as a Scene
  revision. Correction: no editable fields; exact snapshot facts only.
- High: the Blueprint's existence could be treated as an independently
  finalized Timeline Contract. Correction: display GO/install state separately
  and do not emit a finalize action.
- Medium: derived counts could become canonical state. Correction: they are
  recomputed from each snapshot and never sent to the bridge.

Residual Builder C/H/M: `0/0/0`.

## Security / Completeness Critic

- No fabricated Scene IDs, demo records, Provider results or elapsed time.
- Every displayed Scene is a constituent of the current exact Blueprint.
- Disabled actions explain the missing typed service and cannot be enabled by
  local selection.

Residual Security/Completeness C/H/M: `0/0/0`.

## Post-change Evidence

Implementation result:

- `renderScenes(...)` now renders every current Blueprint Scene as an exact
  selectable read-only row;
- `renderSceneDetail(...)` projects frame range, source/risk/camera/reference
  and Audio requirements without writing browser-owned Product state;
- the summary is re-derived from the same Blueprint snapshot and retains the
  independent GO/install states;
- Add, Remove, Update and Timeline finalization are visible but disabled with
  exact typed-service dependencies.

Verification:

- `git diff --check`: PASS;
- Python `compileall`: PASS;
- embedded JavaScript syntax: PASS (`scripts=1`);
- focused TASK-027/TASK-036 tests: `55 passed`;
- Windows full regression: `1234 passed, 1 skipped` in `58.78s`;
- Provider/paid/native/release/deploy/shared-file effects: `0`.

Independent-ready provisional Judge:

`P_UX_1C_SCENE_CONTRACT_BROWSER_SURFACE_R0=PASS_LOCAL_IMPLEMENTATION`

Residual design/implementation C/H/M: `0/0/0`.

This closes the truthful Blueprint Scene browser portion only. Scene mutation
and independent Timeline Contract finalization remain blocked on absent typed
Application Services; whole-surface parity is not claimed.
