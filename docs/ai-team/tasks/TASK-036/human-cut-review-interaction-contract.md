# TASK-036 — Human Cut Review Interaction Contract Ver.1.0

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`
- Owner UI direction: Vrew × Premiere Pro × DaVinci Resolve
- External mutation: none

## 1. Objective

Make TASK-024 cut candidates actually reviewable from the professional desktop editing surface without turning a human CUT/KEEP gesture into a burdensome modal loop.

## 2. Human authority semantics

A click on `KEEP` or `CUT` is the explicit human decision for one candidate. The Product still creates and consumes a one-shot intent token inside that exact gesture, binding the decision to:

- current Project context revision;
- exact Candidate Manifest identity;
- exact prior review-state hash;
- candidate ID;
- CUT/KEEP decision;
- optional bounded CUT override.

This gives authorization binding without requiring a second generic “Are you sure?” modal for every candidate.

Final **Edit Plan approval is different**. It remains a separate summary + confirmation action after every candidate has an explicit CUT/KEEP decision.

## 3. Interaction synchronization

Selecting a cut candidate:

- selects the candidate in the Inspector;
- seeks the logical playhead to the candidate start;
- highlights the matching Timeline cut-overlay block;
- exposes evidence kind/strength/state;
- enables KEEP/CUT only for a valid selection.

A review-state mutation invalidates any previously prepared Edit Plan approval confirmation.

## 4. UI requirements

The Edit Workspace contains a dedicated `C1 Cut Candidates` overlay lane. Candidate blocks are not destructive Timeline edits. They represent review-only proposals until the approved TASK-007 Edit Plan exists.

Inspector shows:

- candidate identity;
- reason/kind;
- strength;
- affected time range;
- current human review state;
- KEEP/CUT controls;
- reviewed/unresolved counts;
- plan approval control only when unresolved count is zero.

## 5. Safety

- no automatic CUT;
- no bulk implicit approval;
- no Resolve mutation;
- no plan approval while unresolved candidates remain;
- range overrides must remain inside the source candidate range;
- plan approval token is one-shot and context-bound;
- a review change after approval-summary preparation makes that summary stale.

## 6. Automated acceptance

Covered by:

- `tests/test_task036_editing_review.py`
- `tests/test_task036_shell_ui.py`

Status: `AUTOMATED_VALIDATED`.
