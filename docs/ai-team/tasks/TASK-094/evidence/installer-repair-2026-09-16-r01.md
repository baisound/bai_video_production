# TASK-094 Installer Repair Evidence — 2026-09-16 R01

## Identity and scope

- Project: `ai-video-production`
- Task / Atomic Unit: `TASK-094 / installer-repair`
- Run ID: `20260916-r01`
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task094-owner-voice-location`
- Branch: `codex/task-094-owner-voice-location`
- Base and observed current `origin/main`: `0ea538899044c60582cbc25a2a6b401cfb815811`
- Exact implementation commit: `581b2e74714a71cba626a50195ecf01f6bb03308`
- Development profile: `DEV-3 HIGH ASSURANCE`

The unit repairs all five Inno Setup definitions that produce six Windows
installers. It does not tag, publish a Release, activate the TASK-063 private
Bridge, download a model, read private audio, or modify the Owner's real OBS or
existing Product installations.

## Changed paths and ownership

All committed paths are within the TASK-094 Allowed Files:

- `packaging/task094_existing_install_choice.iss`
- `packaging/task063_main_installer.iss`
- `packaging/task092_dbd_utility_installer.iss`
- `packaging/task046_voice_model_builder_installer.iss`
- `packaging/task047_obs_voice_capture_installer.iss`
- `packaging/task093_owner_voice_runtime_installer.iss`
- `tools/windows/install-owner-voice-runtime.ps1`
- `tools/windows/test-task063-main-installer.ps1`
- six targeted test files under `tests/`
- `docs/ai-team/tasks/TASK-094/**`
- `docs/ai-team/current-state.md` at the integration checkpoint

## Verification

| Gate | Result |
| --- | --- |
| Focused pytest and canonical-state contracts | `PASS — 41 passed, 1 deselected, 0 failed` |
| Owner Voice PlanOnly/root-policy script | `PASS` |
| `git diff --check` before implementation commit | `PASS` |
| Inno Setup 7.1.0 production-shaped compilation | `PASS — 6 / 6` |
| Inno Setup isolated-AppId QA compilation | `PASS — 6 / 6` |
| Main install / same-root repair / uninstall | `PASS` |
| Training Studio install / same-root repair / uninstall | `PASS` |
| Trivia Editor install / same-root repair / uninstall | `PASS` |
| Voice Model Builder install / same-root repair / uninstall | `PASS` |
| Voice Capture fake-OBS acceptance | `PASS` |
| Exact observed prior locale update and uninstall restore | `PASS` |

The one deselected pytest case executes the previously published v0.24.2 Voice
Capture installer with its production AppId. It was replaced for this unit by
the stronger isolated-AppId candidate acceptance so no current uninstall
registration could be overwritten.

Voice Capture native acceptance covered clean install, repair, unknown collision
refusal, unchanged collision target, exact3 adoption, uninstall restoration and
append-only journal hash-chain validation. A separate native run placed the
exact prior locale revisions reported by the Owner (`en-US.ini`
`c93279484a993fb6543fb898bfb2625fb1f8c717b545649729954ff2ff5ff031`,
`ja-JP.ini` `0d4b5e7c5f23cfe0264f124f05b64d554b4a6dd044fe2ab7ce5ec8228d07073c`)
under fake OBS and confirmed update plus exact restoration on uninstall.

## Production-shaped installer artifacts

These are local compile evidence, not published Release assets:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `bai-video-production-0.24.2-task094-windows-x64-setup.exe` | 104454388 | `8ba940df0ebe45fdd87e56a341dcc0ad9a9cf3c99822e068b3fc8ffb2395a11a` |
| `bai-dbd-training-studio-0.24.2-windows-x64-setup.exe` | 75548455 | `f8c80f7891281dc0c96cf38141518178ea2470caf8b1baa2bd87faa3ff277170` |
| `bai-dbd-trivia-editor-0.24.2-windows-x64-setup.exe` | 13923605 | `7c8b9c41afa63fd5034d84aadd7c313cb66917d27dc1d013d62040e5a66449d5` |
| `bai-voice-model-builder-0.1.0-dev.1-installer.2-windows-x64-setup.exe` | 17663105 | `bc92020ed776aa86a2869cfe0c4bea80064533c6aceec44ed479629c8dfd3cd6` |
| `bai-voice-capture-0.1.0-dev.10-installer.2-windows-x64-setup.exe` | 2141895 | `1bf2dd9015b9375d40daaf791b22055061718ca41660d0904c9ad709f4621d5c` |
| `bai-owner-voice-runtime-0.24.2-windows-x64-setup.exe` | 31374595 | `b93f7822a46ba6ac43325ee5f8ca3097f9eab9d9c668506c2260e54f4a432515` |

## Resolved roots and residuals

- Production-shaped build root:
  `.task094-build\production-r02`
- Isolated-AppId compile root: `.task094-build\qa-r01`
- Native QA roots: `.task094-native\run-r01`, `.task094-native\run-r02`,
  `.task094-native\run-r03`
- Focused test roots: `.task094-test-output\focused-r02` and
  `.task094-test-output\focused-r03`
- Intentional residuals: local installers, logs, fake OBS files and test output
  remain under this exact worktree for review. They are untracked and excluded
  from the commit.
- No task-owned artifact was created at a drive root or as a direct child of a
  drive root.

## Not confirmed and next action

- Owner Voice full runtime bootstrap is `NOT_CONFIRMED` in this unit because it
  may install Python packages and download the pinned Qwen model. Compilation,
  source contracts and PlanOnly validation passed.
- Interactive mouse selection of the three existing-install choices is covered
  by shared source contract plus successful Inno compilation; native unattended
  QA confirms the in-place update path but does not simulate clicks.
- Required next action: push the branch, open a Japanese PR, require hosted green
  checks, then request the separate merge/release gate. No tag or Release is
  authorized by this checkpoint.
