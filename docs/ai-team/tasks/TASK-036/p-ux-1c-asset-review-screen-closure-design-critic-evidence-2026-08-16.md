# P-UX-1C Asset Review screen closure — design, Critic, and Evidence

Date: 2026-08-16
Task: TASK-036 / P-UX-1C
Atomic unit: `ASSET_REVIEW_HUMAN_DECISION_SURFACE_R0`

## Source of Truth and authority

- Initial Code Source of Truth was the clean worktree at `origin/main` commit
  `8271d51479571b1754f8358f074cf3245f5587b7`. Before publication, remote main
  advanced only by PR110's TASK-047 public-manual file; the changed-path sets
  are disjoint. This unit was rebased without conflict onto current main
  `404476acbf8397bd33af1ee9fd6655e6669d23b5`.
- Current Owner instruction activates BAI Development OS AUTONOMY for the
  original non-OBS lane and requires safe runnable work to proceed without a
  routine design receipt gate.
- This unit stays inside the existing TASK-036 P-UX-1C file boundary. It does
  not modify shared registries, workflows, roadmaps, TASK-047, PR110, or any
  OBS worktree.
- The old Track correction is already closed and is not replayed. The open
  whole-surface follow-up is advanced by one screen only.

## Current gap

The V6.1.1 Asset Review page renders the complete `audit_snapshot` as generic
key/value text. The canonical mock has a Human review action, while the real
Product already exposes exact TASK-038 Candidate Audit operations. The missing
piece is a truthful screen projection and binding; no new domain authority is
needed.

## Detailed design

The V6.1.1 runtime shall:

1. Render each `audit.workspace.candidates` row with exact Candidate, Slot,
   Scene, Asset ID/SHA, lifecycle, Audit counts, critical/failure facts,
   immutable Audit history, and any recorded Human decision.
2. Render action buttons only from `available_human_actions` supplied by the
   Python-owned TASK-038 projection.
3. Require a non-empty Human actor ID and explicit confirmation. Bind prepare
   to `candidate_id`, `decision`, `production_snapshot_sha256`, and
   `audit_snapshot_sha256`; bind apply only to the returned one-shot
   `confirmation_id`, actor, and optional notes.
4. Show the prepared Candidate SHA, Audit refs, critical state, and decision in
   the confirmation. A button label, AI score, or front-end object is never the
   confirmation authority.
5. When Audit recovery is required, show the exact recovery state and render no
   decision controls. Recovery remains in the existing Product Control surface.
6. Preserve these boundaries in the page: Human decision is not LOCK; no
   Provider call, paid execution, regeneration, rough-edit construction,
   physical deletion, Resolve operation, or durable JavaScript state occurs.

Changed implementation scope:

- `src/ai_video_production/task036_shell_v611.py`
- `tests/test_task036_v611_visual_contract.py`
- this task-local design/Evidence record

## Builder Critic

Finding B1 (High): copying the mock `buildRoughBtn` would create an action for
which no authorized Application Service exists. Correction: omit it and state
the unavailable boundary explicitly.

Finding B2 (High): using a Candidate ID alone would permit a stale decision.
Correction: consume both exact TASK-038 snapshot hashes at prepare and use the
one-shot confirmation token at apply.

Finding B3 (High): rendering decision controls during partial durable recovery
would compete with the recovery transaction. Correction: actions are sourced
from the Python projection and additionally suppressed whenever recovery is
required.

Residual Builder C/H/M after correction: `0/0/0`.

## Security / Completeness Critic

Finding S1 (High): AI dimension scores could be mistaken for acceptance.
Correction: the page states that AI scores are evidence only and the Human
decision record remains a separately rendered fact.

Finding S2 (Medium): a UI-only decision could drift from TASK-038 state.
Correction: no decision is stored in JavaScript; successful apply refreshes the
Python-owned snapshots.

Finding S3 (Medium): decision acceptance could be confused with Production
LOCK. Correction: confirmation and page boundary explicitly state that LOCK is
a separate operation.

Residual Security/Completeness C/H/M after correction: `0/0/0`.

## Evidence checklist

Evidence is complete only when the post-change section records:

- focused V6.1.1 visual/interaction contract tests;
- TASK-038 workspace/application tests;
- TASK-036 shell bridge tests;
- relevant or full regression result;
- changed-file diff check and final commit identity;
- no native execution, Provider, paid operation, release, deploy, or shared
  registry mutation.

## Post-change Evidence

Implementation result:

- the generic Asset Review dump was replaced by `renderAssetReview(audit)`;
- decision controls are derived only from
  `candidate.available_human_actions`;
- `decideAssetReview(...)` binds both current snapshot hashes at prepare and
  uses the returned one-shot confirmation at apply;
- recovery, unavailable Application, empty Candidate set, recorded Human
  decision, immutable Audit history, critical/failure evidence, and the
  no-effect boundary are explicitly rendered;
- the unsupported mock rough-edit action was not implemented.

Verification:

- `git diff --check`: PASS;
- Python `compileall` for the modified runtime module: PASS;
- embedded JavaScript extraction and `new Function(...)` syntax check under
  bundled Node.js `v24.19.0`: PASS (`scripts=1`);
- focused TASK-036 V6.1.1, Shell bridge, and TASK-038 Audit tests:
  `57 passed`;
- Windows full regression at current Source of Truth: `1230 passed, 1 skipped`
  in `66.85s`; the skip is the pre-existing non-Windows credential-vault
  contract;
- Provider/paid/native/release/deploy/shared-registry effects: `0`.

Independent-ready provisional Judge:

`P_UX_1C_ASSET_REVIEW_HUMAN_DECISION_SURFACE_R0=PASS_LOCAL_IMPLEMENTATION`

Residual design/implementation C/H/M: `0/0/0`.

This closes only the Asset Review Human-decision screen slice. It does not
claim whole-surface V6.1.1 parity and grants no authority for the remaining
screen gaps or native acceptance.
