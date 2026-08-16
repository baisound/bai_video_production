# P-UX-1C Audio Workspace closure

Date: 2026-08-16
Atomic unit: `AUDIO_WORKSPACE_CLOSURE_R0`

## Design and Critic

The V6.1.1 Audio page previously rendered the TASK-041 Audio Workspace as
generic JSON and did not load the separate TASK-026 Placement Application.
The existing Applications already separate Candidate discovery, Human
Placement Review, and an immutable Placement Plan from every external audio or
NLE effect.

This slice connects accepted/locked audio Candidates to a Placement Review,
projects the exact Human decisions exposed by the Application, and offers a
TASK-026 Placement Plan only for a review whose independently computed
`runnable` predicate is true. The Plan prepare operation binds the Project,
Production, Audio, Timeline, and Placement History snapshots.

Builder Critic: a single page-level Placement button could silently select the
first review. Correction: the common button remains reasoned-disabled and each
eligible review owns its exact Plan action. Security Critic: saving a Plan
could be read as audio generation or Resolve/Cubase execution. Correction: the
UI displays blocker/currentness state, requires the existing prepare/apply
confirmation, and declares external execution `NO` at the row and page
boundaries.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- TASK-041 Candidate rows preserve exact Candidate, Asset digest, Slot, Scene,
  role, lifecycle, and registration state.
- Placement Review prepare/apply binds current Production and Audio snapshots.
- Human actions come only from each review's `available_human_actions`.
- TASK-026 Plan prepare/apply is exposed only for `runnable` reviews and binds
  exact Project, Production, Audio, Timeline, and History snapshots.
- Current and stale compiled Plans remain visible with reason codes and
  TASK-010 structural compatibility.
- The ambiguous common Plan action remains disabled.
- Provider, paid, audio generation, derived Media, TASK-010 execution,
  Resolve, and Cubase operations remain unstarted.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `183 passed`.
- Full regression: `1252 passed, 1 skipped`.
- An unrelated TASK-027 Windows lock test raised one transient
  `PermissionError` on the first full run; the exact test then passed `5/5`
  consecutive reruns and the complete clean rerun produced the result above.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
