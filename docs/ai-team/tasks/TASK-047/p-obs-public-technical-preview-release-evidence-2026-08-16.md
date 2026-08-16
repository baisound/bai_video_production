# TASK-047 P-OBS public Technical Preview Release Evidence

Date: 2026-08-16

## Result

The OBS Voice Capture Plugin installer was published as a public GitHub
Pre-release. This is a Technical Preview for Windows x64 and OBS Studio 32.2.1;
it is not the stable BAI Video Production release and does not establish Owner
voice, Production recording, Dataset, Training or Production admission.

- Release:
  `https://github.com/baisound/bai_video_production/releases/tag/obs-voice-capture-v0.1.0-dev.8-installer.4`
- tag: `obs-voice-capture-v0.1.0-dev.8-installer.4`
- annotated tag target:
  `5f78b6ca06511d5ce7e7442176bf002cfc6e0a4c`
- state: `draft=false / prerelease=true`
- published assets: `4 / 4 uploaded`

## Published assets

| Asset | Bytes | SHA-256 |
|---|---:|---|
| `bai-voice-capture-0.1.0-dev.8-installer.4-windows-x64-setup.exe` | 2136413 | `7f1dff48059f3eb292bae32185080d26a50303313e1128ee1286666bc9faabd6` |
| `bai-voice-capture-0.1.0-dev.8-windows-x64.zip` | 36357 | `4e8fcdf6f697da059ef3aa9ae703a400d0f85e9ed89d77ace9f624dc2783e20f` |
| `bai-voice-capture-0.1.0-dev.8-source.zip` | 41065 | `4dcd50f3aadaf95798a4d82ad511a66b14ad5a1e81a131a3bd65c0c5f933b0a4` |
| `SHA256SUMS` | 352 | `e2a3c5141b226dd4dd97d8569703e21e7c5e6bc856859f4dcd37831c5e5a9a2f` |

GitHub-reported asset digests matched the checked-in artifacts. All four
assets were downloaded again into an isolated read-back directory; file sizes,
SHA-256 values and every entry in `SHA256SUMS` matched.

## Validation and boundaries

- TASK-047 focused Release contract: `4 passed`;
- source worktree before publication: clean and equal to `origin/main`;
- duplicate local tag, remote tag and GitHub Release before publication: `0`;
- public manual contains no private absolute path or Credential;
- installer is unsigned and the Release notes state that Windows may warn;
- stable BAI Video Production Release remains `v0.21.0`;
- Owner voice/formal RecordingSession: `NOT_STARTED`;
- stable Release, Production Deploy, Dataset adoption and Training: `NOT_STARTED`.

Critic pass 1 found the public manual still described the package as
unpublished. The documentation-sync change replaces those stale claims with
the exact public Release URL and keeps the unsigned/Pre-release boundary.

Critic pass 2 checked Japanese/English navigation, filename and digest parity,
stable-versus-preview wording, false-completion language and private-path
leakage. Residual Critical/High: `0 / 0`.
