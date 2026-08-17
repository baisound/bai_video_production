# TASK-046 / P-VS-4B Workflow Import Preflight R3 — Evidence

## Outcome

`PASS_FOR_DRAFT_PR_AND_TECHNICAL_PREVIEW_INSTALLER_CANDIDATE`

- Base: `main@da834ccbd370b527c1cc6c4ba03806ea4a6ac669`
- Branch: `codex/task-046-p-vs-4b-workflow-import-preflight-r3`
- Product state: validation preview only
- Dataset, training, model inference, GPU, audio, recording and publication effects: `false`
- Residual Critical / High / Medium: `0 / 0 / 0`

## Implemented boundary

- The beginner client accepts one user-selected `VerticalSliceWorkflowRevision` JSON document.
- Input is limited to 1–1,048,576 bytes and strict UTF-8 without BOM.
- Duplicate JSON keys, malformed/deep input, non-object roots, unknown fields, invalid revisions, digest tamper and forged effect flags fail closed.
- The validated workflow is projected into the existing twelve-step `BeginnerClientSnapshot`; the source JSON is not modified.
- The file path and JSON body are not added to public projection or receipt metadata.
- File selection and the `--workflow-json` CLI are read-only. They do not dispatch Dataset, Job, training, rendering or publication operations.
- Installer version advances to `0.1.0-dev.1-installer.2`; installer.1 remains an immutable prior Technical Preview.

## Exact source composition

1. `CHANGELOG.md`
2. `docs/ai-team/tasks/TASK-046/p-vs-4b-workflow-import-preflight-r3-evidence-2026-08-17.md`
3. `docs/user/VOICE-MODEL-BUILDER.md`
4. `packaging/task046_voice_model_builder_installer.iss`
5. `src/ai_video_production/voice_model_builder_beginner_client.py`
6. `tests/test_task046_voice_model_builder_beginner_client.py`
7. `tests/test_task046_voice_model_builder_installer.py`
8. `tools/windows/build-task046-voice-model-builder-installer.ps1`
9. `tools/windows/task046_voice_model_builder_launcher.py`
10. `tools/windows/test-task046-voice-model-builder-installer.ps1`

## Build identity

- CPython executable SHA-256: `b70275ad94210fce7548761143be5e177769721045e287bb6c80aac3f928c65b`
- PyInstaller: `6.22.0`
- jsonschema: `4.26.0`
- Inno Setup compiler SHA-256: `d06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a`
- Bundled executable: 14,361,554 bytes; SHA-256 `d704ac8f6dc8ecbd62d98bf9bcf4d3e4556e53004f4fd910ddf9a1a09f446f7b`
- Package manifest SHA-256: `ae9ff7ea0d54ff93c7f357afa9ba81676152edddc05914b85285d84a821d4186`
- Third-party notices: 75,546 bytes; SHA-256 `f0f3abab51258c9941190312d298e286b873e8da5b9356d1d0920b0d6db17a6a`
- Installer: `bai-voice-model-builder-0.1.0-dev.1-installer.2-windows-x64-setup.exe`
- Installer: 16,156,881 bytes; SHA-256 `975d2e38dbe7d3d283ee4cf918f918392dc64591d7233e7ef606fdd0925a3d01`
- Authenticode: `NotSigned`
- Third-party component/license set: exact 8, unchanged from the verified installer.1 release composition

## Validation

- Focused beginner-client and installer contract tests: `31 passed`
- Windows full regression: `1925 passed, 1 skipped`
- Ubuntu WSL full regression: `1925 passed, 1 skipped`
- Windows and WSL compileall: `PASS`
- Clean install: `PASS`
- Exact same-version repair: `PASS`
- Different-content collision: `FAIL_CLOSED / PASS`
- Contained installed executable self-check: `PASS`
- Uninstall: `PASS`
- User-data sentinel preserved: `PASS`
- Third-party notices installed and exact: `PASS`

## Critic pass 1 — Builder / compatibility

- Existing `BeginnerClientSnapshot` schema and twelve-step state mapping remain compatible.
- The new parser delegates all domain validation to the canonical workflow validator rather than duplicating workflow truth.
- Default launch remains a synthetic demo; `--self-check` remains non-interactive and deterministic.
- Finding: the first build receipt still named R2. Corrected both build and acceptance receipt task identities to R3, rebuilt in a fresh root and reran acceptance.
- Residual Critical / High / Medium: `0 / 0 / 0`.

## Critic pass 2 — Security / privacy / false completion

- Strict byte cap, UTF-8 decoding, duplicate-key rejection and exact contract digest validation prevent ambiguous input admission.
- The launcher rejects symlink files, non-files and size changes during read. It exposes no network, subprocess, model, GPU, audio or write surface.
- GUI failures use a generic message and do not disclose a selected local path or JSON body.
- No imported workflow can forge `training_started`, `render_started`, audio access or publication success.
- Installer remains unsigned and is described as a Technical Preview; that state is not promoted to trusted/stable release status.
- Residual Critical / High / Medium: `0 / 0 / 0`.

## Judge

- Source exact10: `PASS`
- Workflow import preflight: `PASS_FAIL_CLOSED`
- Installer build and lifecycle acceptance: `PASS`
- Technical Preview candidate: `PASS`
- Real Dataset adoption / training / model / audio / publication: `NOT_AUTHORIZED_BY_THIS_UNIT`
- Final Critical / High / Medium: `0 / 0 / 0`
