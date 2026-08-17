# TASK-046 / P-VS-4B Beginner Client Release R2 Evidence

## Objective

Prepare the unsigned Windows technical-preview installer for distribution without omitting the licenses of the exact Python components bundled into the executable. Actual Tag and GitHub Release publication remain a postmerge operation and must use the exact accepted artifact hashes.

## Closed component set

- CPython 3.13.14 / PSF-2.0
- Tcl/Tk 8.6 / Tcl license terms
- PyInstaller 6.22.0 / GPL-2.0-or-later with bootloader exception
- jsonschema 4.26.0 / MIT
- attrs 26.1.0 / MIT
- jsonschema-specifications 2025.9.1 / MIT
- referencing 0.37.0 / MIT
- rpds-py 2026.6.3 / MIT

The collector requires exactly one installed license file for each Python distribution, exact CPython and Tcl/Tk license coordinates under `sys.base_prefix`, UTF-8 input, a new absolute output, deterministic section order and a path-free JSON receipt. Missing, duplicate or unreadable license input blocks the build.

## Release boundary

- The installer remains unsigned and must be labelled as a development technical preview.
- It may contain only the contained synthetic twelve-step client, bilingual guide, project license, third-party notice and package manifest.
- No Owner recording, Dataset, checkpoint, Model, generated WAV, Credential or private absolute path may enter an asset.
- Model download, training, audio access, provider call and publication are all false in the package manifest.

## Exact R2 artifact receipt

- Executable: `14,338,811` bytes / SHA-256 `fb3adbb83bae83f6569463108669afea0ea38f186154f3e922ffc0f2e705ee3e`.
- Package manifest SHA-256: `87a617a2fe7126e1c62d299eb10245af5fe140ae38131e1721c830b78d35a4a8`.
- Third-party notice: `75,546` bytes / SHA-256 `f0f3abab51258c9941190312d298e286b873e8da5b9356d1d0920b0d6db17a6a` / exact component count `8`.
- Installer: `bai-voice-model-builder-0.1.0-dev.1-installer.1-windows-x64-setup.exe`, `16,133,836` bytes / SHA-256 `a83b5e122537e41b2300864327347b31dfbcd00ad9eccb05733864ef898b21ca`.
- Authenticode: `NotSigned`; this must remain visible in technical-preview release notes.

## Validation

- Focused beginner-client/installer/notice contract: `23 passed`.
- Fresh local build: PASS with CPython 3.13.14, PyInstaller 6.22.0, jsonschema 4.26.0 and Inno Setup 7.1.0 exact identity bindings.
- Installer acceptance: clean install, exact repair, collision refusal, contained self-check, uninstall, user-data preservation and installed third-party-notice hash all PASS.
- Windows full regression: `1917 passed, 1 skipped` in `120.35s`; declared non-Windows credential-vault contract skipped.
- WSL2 full regression: `1917 passed, 1 skipped` in `89.13s`; declared Windows-only Inno acceptance skipped.
- Windows and WSL2 compileall: PASS.
- Model download, training, audio access, recording and publication flags: all `false`.
- Hosted checks and postmerge read-back remain pending until the source PR exists.

## Critic 1 — Build and composition

- R1 omitted third-party license texts from the installed payload. R2 corrects this before any public release.
- The notice source set is closed and each source license is hashed.
- unresolved Critical/High/Medium after correction: `0/0/0`.

## Critic 2 — Security and user truth

- Receipt and notice exclude absolute source paths, environment values and credentials.
- Adding notices does not add a runtime effect or turn the synthetic demo into a working trainer.
- unresolved Critical/High/Medium: `0/0/0`.

## Local Judge

- `LICENSE_COMPOSITION_CONTRACT=PASS`
- `R2_ARTIFACT=PASS_UNSIGNED_DEVELOPMENT_CANDIDATE`
- `INSTALLER_ACCEPTANCE=PASS`
- `WINDOWS_WSL_REGRESSION=PASS`
- `PUBLIC_RELEASE=UNKNOWN_PENDING_POSTMERGE_GATE`
- unresolved Critical/High/Medium: `0/0/0`
