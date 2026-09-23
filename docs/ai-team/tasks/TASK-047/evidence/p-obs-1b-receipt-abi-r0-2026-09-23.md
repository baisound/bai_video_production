# TASK-047 P-OBS-1B receipt ABI R0 implementation checkpoint

- Project / Task / Unit: BAI VIDEO PRODUCTION / TASK-047 /
  `P-OBS-1B-RECEIPT-ABI-R0`.
- Operation: `20260923-source-transport-abi-r0-a6`.
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-047-receipt-abi-r0`.
- Branch: `codex/task-047-receipt-abi-r0`; base/current main at allocation:
  `d74cda06f8ee1a6d4a98d0507c29441a9de87ffd`.
- Exact implementation SHA: pending commit/hosting. This evidence describes the
  staged seven-file candidate plus this checkpoint, not a merged ABI.

## Scope and verification

The candidate adds body-free `CaptureSourceCurrentnessReceiptV1` and
`CaptureTransportIntegrityReceiptV2` JSON Schema, packaged mirror, strict
digest/shape/parser and pair validation. The only result is
`STRUCTURAL_VALID_ONLY`; it does not authenticate a producer or admit audio.
No OBS operation, recording, private-audio read, Asset/Job/custody write,
Dataset/Training, Release, Deploy or Production activation was performed.

- Changed paths: this Evidence, the R0 design, canonical/mirrored schema,
  parser, tests, `docs/ai-team/current-state.md`, and
  `docs/ai-team/task-index.md`. All are inside the R0 declared Allowed Files.
- Focused `tests/test_task047_capture_source_transport_receipts.py`:
  `41 PASS`.
- Direct regression `tests/test_task047_readiness_receipt_contract.py` and
  `tests/test_task098_review_workspace_contract.py`: `46 PASS`.
- Final combined command with Windows Python 3.13.14 and real
  `jsonschema==4.25.1`: `87 PASS`, `0 FAIL`, `0 SKIP`.
- Canonical/packaged schema byte equality and Draft 2020-12 validity: `PASS`
  within focused tests. `git diff --cached --check`: `PASS` before this
  checkpoint was added; final diff check must be repeated.
- WSL test route: `NOT_EXECUTED`, because WSL service returned
  `Wsl/Service/E_ACCESSDENIED`; the Windows route above is the executed proof.

## Output placement and residuals

- Build, installer, runtime and native output roots: none; those effects were
  not run.
- Test/dependency root: `C:\Users\user\AppData\Local\Temp\bvp-task047-receipt-abi-r0-20260923-a1`, an OS-temp-contained unique root with
  `TASK047-RECEIPT-ABI-R0.marker` owner marker.
- Intentional residuals under that exact root: `deps/` with test-only
  `jsonschema==4.25.1`, and `pytest-a2/` through `pytest-a6/` test artifacts.
  `pytest-a2` was an initial test-harness failure (overlong parametrized test
  ID and one invalid time fixture), not a parser regression. No recursive
  cleanup or ACL ownership change was attempted.
- No task artifact was created directly under a drive root.

## Review, dependencies and next action

DEV-4 independent Critic/Tester/Judge review and hosted CI are pending;
technical completion is therefore `NOT_CONFIRMED`. The full terminal receipt
chain depends on exact TASK-046 OwnerSubject/Consent, trusted time, TASK-043
current capture Job readback, TASK-003 Asset adoption and TASK-082 V2 custody
contracts. The unmerged TASK-047 OwnerSubject amendment is not assumed to be
main authority. TASK-098 A5 remains blocked on the full chain and fresh
DEV-4 review. Next: commit the bounded candidate, obtain independent/hosted
review, resolve findings, then continue the next authorized receipt unit
without starting native or private-voice effects.
