# TASK-046 / P-VS-4B Beginner Client Installer R1 Evidence

## Authority and scope

- Product: `BAI Voice Model Builder`, separate from the TASK-047 OBS Plugin and Controller.
- Source base: `main@bb4f9aa717638712afaa9b9b11f34a55647643fc`.
- Scope: contained Windows executable, bilingual per-user installer, local build/acceptance tooling, beginner guide and README discovery.
- The installed R1 client is the R0 synthetic twelve-step display. It has no Dataset, Job, training, model, audio, provider, recording, publication or Release effect.
- Installer execution never launches the application and never downloads a runtime or model.

## Design decisions

1. The launcher exposes only the existing synthetic preview plus a contained `--self-check`.
2. PyInstaller runs from an isolated absolute Python environment; Inno Setup receives exact payload SHA-256 values.
3. Install is per-user and uses a product-specific AppId and program directory.
4. Existing unexpected application files, reparse destinations, low disk and post-copy hash mismatch fail closed.
5. Uninstall removes application-owned files but has no deletion rule for recordings, Dataset, checkpoints, Models or generated WAV.
6. Japanese and English guides explain current limitations and the intended OBS-to-Master-WAV sequence without claiming unimplemented success.

## Build receipt

- Python launcher SHA-256: `b70275ad94210fce7548761143be5e177769721045e287bb6c80aac3f928c65b` (contained Python 3.13.14 environment).
- PyInstaller: `6.22.0`.
- jsonschema: `4.26.0`.
- Inno Setup compiler SHA-256: `d06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a` (7.1.0).
- Packaged executable: `14,337,963` bytes / SHA-256 `c3f45581309b4aa159c8cd7d17f18dcd21ceccb43bba45fa3ea795b608a9bd5f`.
- Package manifest SHA-256: `c7f14836c8d5ad28070cd1a3b099885ad922b3069f45d5ca64dbc6121385e401`.
- Installer: `bai-voice-model-builder-0.1.0-dev.1-installer.1-windows-x64-setup.exe`, `16,116,984` bytes, SHA-256 `6221719458113ede6df67c6a31dbebd2a7475470c4813993f07dba932a22a666`.
- Authenticode: `NotSigned`. This is a development candidate; the guide requires source/digest verification and does not call it a stable signed release.
- Build receipt flags: application launch, model download, training, audio access and publication all `false`.

Two rejected build attempts were retained outside the repository as diagnostic evidence. The first exposed native stderr handling in Windows PowerShell; the second exposed a missing packaged `jsonschema` dependency. Neither artifact is accepted or eligible for publication. The final candidate was rebuilt in a fresh root after both corrections.

## Validation receipt

- Focused installer plus existing beginner-client tests: `22 passed`.
- Windows 3.13 full regression: `1916 passed, 1 skipped` in `109.19s`; the skip is the declared non-Windows credential-vault contract.
- WSL2 Python 3.12 full regression: `1916 passed, 1 skipped` in `90.48s`; the skip is the Windows-only Inno Setup acceptance.
- Python compileall: PASS on Windows and WSL2.
- Local installer acceptance: clean install PASS; exact repair PASS; altered executable collision blocked; contained `--self-check` PASS; uninstall PASS; task-owned user-data sentinel preserved.
- Installed executable, guide and license were read back against the exact package manifest.
- No OBS, Owner voice, recording, Dataset, Job, model, GPU, training, generated WAV, provider, network or publication effect occurred.

## Critic pass 1 — Builder

- Product identity and target paths do not overlap the OBS Plugin installer.
- The build is reproducible from fixed Python/PyInstaller/Inno identities and emits a payload manifest.
- Finding status: no unresolved Critical/High/Medium after final fresh-root build and exact payload read-back.

## Critic pass 2 — Security and beginner UX

- No credential, private absolute path, model body, audio body or Owner voice enters source or package metadata.
- No install-time app launch, download, training, recording, publication, PATH or registry environment change exists.
- The guide distinguishes installed/displayed from trained/generated/approved and keeps Owner recording at a later explicit gate.
- Finding status: no unresolved Critical/High/Medium after bounded install/repair/collision/self-check/uninstall acceptance.

## Final local Judge

- `SOURCE_AND_CONTRACT_READY=PASS`
- `LOCAL_INSTALLER_ARTIFACT=PASS_UNSIGNED_DEVELOPMENT_CANDIDATE`
- `INSTALL_REPAIR_COLLISION_UNINSTALL_ACCEPTANCE=PASS`
- `WINDOWS_WSL_FULL_REGRESSION=PASS`
- `REAL_TRAINING_OR_AUDIO_GENERATION=NOT_AUTHORIZED_BY_THIS_UNIT`
- `PUBLIC_GITHUB_RELEASE=SEPARATE_POSTMERGE_EFFECT`
- unresolved Critical/High/Medium: `0/0/0`
