# TASK-051 R4A — Stale R1 Presentation Regression Review

Governance: `DEV-3 HIGH ASSURANCE`
Status: `BOUNDED_FIX_RETEST`

## Failure classification

R4 Product tests passed (`6 passed`), R3 passed (`7 passed`), and R2 passed (`5 passed`).
The inherited R1 presentation test then failed because it asserted the private Python variable
name `ocr_source_mode`.

R4 preserved the R1 user-facing source-provenance contract but renamed the OCR-local variable to
`source_mode` while rebuilding the tab. A private implementation variable name is not a Product UX
contract.

## Corrective action

Rebase only `test_ui_strings()` in the historical R1 test to semantic UI contracts:
- no legacy English Target/Notes/Registered labels;
- source provenance uses Japanese 手入力 / URL参照 constants;
- multiline メモ remains present;
- raw OCR internal-code label is absent;
- Japanese `通知の種類` is present.

No Product source is changed by R4A.

## Retest

The installer reruns R4, R3, R2, R1, TASK-050 focused regressions, `py_compile`, and
`git diff --check`.

No unresolved HIGH finding remains in R4A scope.
