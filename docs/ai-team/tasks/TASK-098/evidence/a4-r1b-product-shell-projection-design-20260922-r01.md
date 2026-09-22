# TASK-098 A4-R1b Product/Shell Projection Design Evidence R01

- Recorded: `2026-09-22`
- Project / Task / Atomic Unit: `BAI VIDEO PRODUCTION / TASK-098 / A4-R1b DESIGN`
- Run identity: `a4-r1b-product-shell-projection-design-20260922-r01`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`
- Branch: `codex/task-098-a4-review-workspace`
- Starting HEAD: `a2689bf507d9821a4ba5a991a192943bff30767b`
- Base/current-main identity: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Result: `DESIGN_ACCEPTED / A4-R1B_IMPLEMENTATION_ALLOCATED`

## Decision

- Add a separate allowlisted public projection rather than serializing the private A4-R1a ViewModel.
- Bind it through one optional trusted provider read once per Shell view-model request.
- Preserve the exact legacy response when the provider is absent.
- Merge through one helper after either the integrated-application or projection-only Task036 path.
- Add no Shell action, HTML/JavaScript renderer, playback, waveform, persistence or mutation effect.

## Review and scope

- Initial design findings corrected: `High 4 / Medium 3`.
- Final unresolved findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Tester: `PASS / IMPLEMENTATION_TEST_PLAN_ACCEPTED`.
- Judge: `ACCEPT / A4-R1B_IMPLEMENTATION_ALLOCATED`.
- Allowed Files: bounded projector, Task036 Shell bridge, focused tests and TASK-098 documents only.
- Build / QA / runtime / temporary output roots: `NONE`.
- Native/paid/provider/model/media/UI/runtime/release/deploy/Production effects: `NONE`.
- Next action: implement the accepted A4-R1b projection and provider wiring, then run focused and relevant TASK-098/TASK-036 regression.
