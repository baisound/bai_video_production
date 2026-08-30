# TASK-059 P1C-J3 - Current Windows Package Build Evidence

Date: `2026-08-27`

Identity: `TASK-059-P1CJ3-CURRENT-WINDOWS-PACKAGE-BUILD-EVIDENCE-V1`

Status: `PASS_NATIVE_MANUAL_GATE_REMAINS`

## Scope

P1C-J3 builds the exact P1C-J2 commit through the canonical Windows packaging
entrypoint. It verifies that the trusted runtime binding and adjacent
single-attempt helper are present in the unified Product package without
applying real Owner coordinates or opening a secret UI.

## Build evidence

- Source commit: `fd539054fa70706eece166d59358b2a1e9cfef78`.
- Python: `3.12.4`.
- PyInstaller: `6.22.0`.
- Canonical Main one-directory build: `PASS`.
- Canonical helper one-file build: `PASS`.
- Main EXE: `16426395` bytes,
  SHA-256 `b6d4936959e48b0e52931dd823ce64732147181c35413c8cc106f17268bd5d39`.
- Bundled helper: `17229174` bytes,
  SHA-256 `5aefebf7a53806a7d8555206d1f805c3dae1f14c8f36521edc58b6b63a574ca0`.
- Staging helper: exact same size and SHA-256 as the bundled helper.
- Script-owned three-way helper identity verification: `PASS`.
- Secret-free helper protocol v1 empty-input smoke: `PASS / EXIT 0`.
- Invalid protocol refusal: `PASS / EXIT 64`.

## Archive inspection

Recursive Main archive inspection found exactly these four required entries:

- `_bvp_task059_packaged_helper_identity`
- `ai_video_production.owner_signing_key_ppk_native_adapter`
- `ai_video_production.owner_signing_key_ppk_shell_service`
- `ai_video_production.owner_signing_key_ppk_windows_dialog`

Result: `PASS / EXACT 4`.

## Review

The package contains the intended P1C-J2 trusted composition and no alternate
helper path or digest input. Generated output remains Git-ignored. Non-blocking
PyInstaller warnings concerned unavailable Android webview support, optional
pycparser parser tables and the upstream `pkg_resources` deprecation; none
invalidated the Windows package, identity checks or native helper smokes.

Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

The Main Product UI and Windows Credential UI were not launched. No real
launch configuration, PPK, public key, passphrase, DPAPI custody, signing,
installer, publication, promotion, Release, Deploy or Production operation was
performed. Native manual UI QA and real Owner-value configuration remain
separate Human Gates.
