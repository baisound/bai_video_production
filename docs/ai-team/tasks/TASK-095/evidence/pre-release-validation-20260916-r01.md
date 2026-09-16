# TASK-095 Pre-release Validation — 2026-09-16 r01

- Project: BAI VIDEO PRODUCTION
- Task / atomic unit: `TASK-095 / version-bump-and-release-preparation`
- Run identity: `pre-release-validation-20260916-r01`
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task095-v0243-release`
- Branch: `codex/task-095-v0243-release`
- Base / pre-commit HEAD: `61d73644d7834fe156a7c2560ab529f75338bee1`
- Current main identity at task start: `61d73644d7834fe156a7c2560ab529f75338bee1`
- Dirty state: expected TASK-095 version, documentation, release-asset and exact-test changes only; temporary run directories are untracked and excluded from commit.
- Allowed-files result: `PASS`; all changed paths are within TASK-095's declared version/release scope.

## Native build evidence

- Resolved build work root: `C:\home\baisound\projects\bai-video-production\.worktrees\task095-v0243-release\.task095-obs-build\work-r01`
- Resolved build output root: `C:\home\baisound\projects\bai-video-production\.worktrees\task095-v0243-release\.task095-obs-build\output-r01`
- Inno Setup compiler SHA-256: `d06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a`
- Runtime ZIP SHA-256: `03286e9efbf5dd5af38230dcf7fee4bf53eb3fcc7d7a6d014833b9996bc1f558`
- Rebuilt installer bytes: `2141895`
- Rebuilt installer SHA-256: `1bf2dd9015b9375d40daaf791b22055061718ca41660d0904c9ad709f4621d5c`
- Authenticode: `NotSigned`
- External download: `false`
- OBS mutation / recording: `false / false`
- Intentional repository residual: rebuilt installer under `packaging/release-assets/task047/` plus synchronized checksum and contract-test identity.

## Verification

- Release metadata tests: `PASS` — 13/13.
- Focused release/installer regression: `PASS` — 61 passed, 1 deselected.
- Deselected case: legacy native TASK-047 test that runs the production AppId against the owner's existing installation. TASK-094 isolated-AppId native QA remains the admitted native lifecycle proof.
- Python compileall (`src`, `tests`): `PASS`.
- TASK-093 Owner Voice Runtime installer contract script: `PASS`.
- OBS tracked release asset checksum contract after rebuild: `PASS`.
- Overall pre-release result: `PASS`.

## Gates and next action

- Prohibited effects remain: no v0.24.2 mutation, no real installation/OBS mutation, no voice training/generation, and no paid/provider execution.
- Next: commit, hosted PR checks, exact-head merge, annotated `v0.24.3` tag, exact-tag Windows builds, GitHub Release publication, and remote asset readback.
