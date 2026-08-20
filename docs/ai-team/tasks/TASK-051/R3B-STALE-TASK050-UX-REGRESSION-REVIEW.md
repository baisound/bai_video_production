# TASK-051 R3B — Stale TASK-050 UX Regression Review

Governance: `DEV-3 HIGH ASSURANCE`
Status: `BOUNDED_FIX_RETEST`

## Failure classification

R3A successfully corrected the stale R2 `Cropプレビュー` assertion. The next failure is an
older TASK-050 UX assertion requiring the literal text `学習するゲーム要素（必須）`.

R3 intentionally replaced the single-label/single-slot workflow with the accepted multi-slot
contract:
- `学習スロットと正解ゲーム要素（候補はKnowledge/Aliasから表示）`
- registration is blocked until at least one slot has a selected game element.

Therefore the old literal-string assertion no longer describes the Product contract.

## Corrective action

Update only the stale TASK-050 test assertion so it verifies the new semantic contract:
1. the multi-slot UI explicitly identifies `正解ゲーム要素`;
2. the UI blocks preview/registration when no slot game element is selected.

No Product source is changed by R3B.

## Retest

R3B reruns:
- R3 functional/UI tests;
- R2 transport/integration;
- R1 presentation;
- TASK-050 UX follow-up;
- py_compile;
- git diff --check.

No unresolved HIGH finding remains in R3B scope.
