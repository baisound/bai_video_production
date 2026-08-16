# P-UX-1C Home project-open action closure

Date: 2026-08-16
Atomic unit: `HOME_PROJECT_OPEN_ACTION_R0`

## Design and Critic

The element audit reports one missing Home action. The current Project row
disables its only Project button when no Project is open, leaving Home without
a direct open route even though the released Shell already owns the trusted
`choose_project_folder` boundary.

Add one `別のProjectを開く` button and bind it to the same existing
`chooseAndReport('choose_project_folder', 'プロジェクト')` flow as File/Open.
Do not implement Recent demo entries, browser paths, automatic picker launch or
Project mutation in JavaScript.

Builder Critic: duplicating File/Open behavior could diverge. Correction: both
buttons call the same helper and exact bridge method. Security Critic: a Home
render must not launch a native picker. Correction: the bridge is called only
from the explicit click handler.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- Home renders one explicit `homeOpenProjectButton` labelled
  `別のProjectを開く` independently of the current Project state.
- The button reuses the released `choose_project_folder` bridge through
  `chooseAndReport`; it does not expose paths or auto-launch a picker.
- No fabricated Recent Project entry was introduced.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `63 passed`.
- Full regression: `1235 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
