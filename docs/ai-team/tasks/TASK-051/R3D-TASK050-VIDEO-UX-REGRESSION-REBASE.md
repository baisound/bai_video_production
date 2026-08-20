# TASK-051 R3D — TASK-050 Video-learning UX Regression Rebase

Governance: `DEV-3 HIGH ASSURANCE`
Status: `BOUNDED_FIX_RETEST`

## Why R3B/R3C were insufficient

The historical TASK-050 test function contained several literal assertions from the former
single-slot workflow. Updating them one by one created repeated false regressions even though
R3's Product behavior and its own focused tests remained green.

## Corrective approach

Rebase the entire historical function
`test_video_learning_ui_explains_required_game_element_before_preview`
onto the accepted R3 semantic contract instead of chasing individual wording.

The rebased test verifies:
- multi-slot required-answer guidance;
- Knowledge/Alias assisted selection;
- Human two-stage Crop preview -> batch registration;
- missing-selection and missing-preview guards;
- active HUD profile visibility;
- multi-Crop geometry visibility.

No Product source is changed by R3D.

## Retest

R3D reruns R3, R2, R1, TASK-050 focused regressions, `py_compile`, and `git diff --check`.

No unresolved HIGH finding remains in R3D scope.
