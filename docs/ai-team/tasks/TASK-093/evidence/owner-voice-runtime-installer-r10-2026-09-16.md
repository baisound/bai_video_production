# TASK-093 Owner Voice Runtime Installer r10 Evidence

- Date: 2026-09-16 JST
- Base main: `af0bbcbab394b363ca77c41bbd87640d8b25d189`
- Branch: `codex/task-093-owner-voice-runtime-installer`
- Candidate version: `0.24.2`
- Governance: `DEV-3 HIGH ASSURANCE`

## Implemented boundary

- The per-user installer selects and validates a nested local data root.
- It verifies the bundled official Python 3.12.10 installer by SHA-256 and Python Software
  Foundation Authenticode, creates a dedicated venv, installs the fixed top-level runtime
  packages, verifies or downloads one exact Qwen model revision, and publishes READY config
  only after package, CUDA, ffmpeg, model-file and model-load checks pass.
- The installed WAV command has a stable per-user path. SRT and reference inputs remain explicit
  PowerShell arguments; no file picker or interactive `Read-Host` flow is present.
- No Owner recording was read. No audio was generated. Fine-tuning remains outside this Task.

## Native installer verification

- Candidate: `bai-owner-voice-runtime-0.24.2-windows-x64-setup.exe`
- Candidate SHA-256: `2e02ce5b1c866c0b17e6547288747123c09292140060a34e8fba0212af5b8110`
- Candidate size: `31,373,274` bytes
- Result: `PASS`
- Installer exit: `0`
- Runtime config: `READY`
- CUDA: `true`, observed GPU: NVIDIA GeForce RTX 4070 SUPER
- Exact Qwen model revision: `5d83992436eae1d760afd27aff78a71d676296fc`
- Model load-only: `true`
- Generation started: `false`
- Stable command interactive prompt scan: `false`
- Failure-path observation: an earlier candidate returned non-zero and wrote a bounded diagnostic
  JSON when Windows PowerShell modules were unavailable. r10 explicitly loads the built-in modules
  from the selected PowerShell installation and removes the failure receipt after PASS.
- The candidate installer is not code-signed. The embedded official Python installer is signed and
  verified; the outer installer is integrity-bound by the published SHA-256.

## Automated verification

- Installer effect-zero/safety contract: `PASS`
- Focused Owner Voice tests: `13 passed`
- Release metadata and revised guide checks: `4 passed`
- Windows DPAPI environment rechecks: `8 passed`
- Short-path WebView2 recheck: `1 passed`
- Final Windows full regression: `7933 passed, 33 skipped, 0 failed, 11 subtests passed`
- `compileall`: `PASS`
- `git diff --check`: `PASS`

The 33 final skips are condition-based platform/native cases reported by the suite, including POSIX-only
contracts and the OBS installer acceptance test while a real `obs64` process is running.

## Resolved defects during native verification

1. Python inline version quoting was made shell-stable.
2. Existing Python 3.12 is used only as the base for a dedicated Owner Voice venv.
3. Inno's PowerShell launch uses the 64-bit system route and explicitly loads built-in modules.
4. Installer failure now returns non-zero and leaves a diagnostic JSON instead of a false success.
5. Existing data roots require a matching ownership marker before repair.
6. Same-version repair force-reinstalls the exact bundled BAI wheel.
7. The stable generation command is copied outside the app directory and remains noninteractive.

## Pending release gates

- Commit and PR exact identity
- Hosted checks all green and merge
- Annotated `v0.24.2` tag at exact main
- Exact-tag Windows builds and GitHub Release asset digest read-back

Native/build working roots and intentional residual artifacts are recorded in the external TASK-093
Evidence checkpoint required by workspace policy.

- External checkpoint identity: `TASK-093/owner-voice-runtime-installer/20260916T0400JST-r10`
- External checkpoint SHA-256: `27f08c13b5f6952f6e2e3a6e6d13cfe8b83813ca37a73165f8b780d9a5173a93`
