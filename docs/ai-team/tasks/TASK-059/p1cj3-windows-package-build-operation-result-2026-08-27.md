# TASK-059 P1C-J3 Windows Package Build Operation Result

Date: `2026-08-27`

Identity: `TASK-059-P1CJ3-WINDOWS-PACKAGE-BUILD-OPERATION-RESULT-20260827-V1`

Document class: `WORK_RESULT`

Procedure identity:
`TASK-059-P1CJ3-WINDOWS-PACKAGE-BUILD-OPERATION-PROCEDURE-20260827-V1`

## Result

Technical result: `PASS`

Execution status: `COMPLETED_SECRET_FREE_BUILD_ONLY`

- Source commit built: `fd539054fa70706eece166d59358b2a1e9cfef78`.
- Windows Python: `3.12.4`.
- PyInstaller: `6.22.0`.
- Canonical `build-windows-exe.bat`: `PASS`.
- Main one-directory EXE size: `16426395` bytes.
- Main one-directory EXE SHA-256:
  `b6d4936959e48b0e52931dd823ce64732147181c35413c8cc106f17268bd5d39`.
- Bundled helper size: `17229174` bytes.
- Bundled helper SHA-256:
  `5aefebf7a53806a7d8555206d1f805c3dae1f14c8f36521edc58b6b63a574ca0`.
- Staging helper size and SHA-256: exact match with the bundled helper.
- Packaged helper identity verification: `PASS`.
- Main archive recursive TASK-059 module inspection: `PASS / EXACT 4`.
- Helper protocol v1 empty-input native smoke: `PASS / EXIT 0`.
- Invalid protocol native refusal: `PASS / EXIT 64`.
- Real Owner configuration written: `NO`.
- Real PPK/public key/passphrase read: `NO`.
- Main Product UI/Credential UI launched: `NO`.
- DPAPI custody/signing started: `NO`.
- Install/download/settings mutation performed: `NO`.
- Release/Deploy/Production effect: `NO`.

## Read-back

The canonical build contains one adjacent helper whose bytes match both the
staging helper and the generated embedded identity. The Main archive contains
the identity module, native adapter, Shell service and Windows dialog backend.
Only secret-free helper protocol behavior was executed.

The build emitted non-blocking PyInstaller collection warnings for unavailable
Android webview support, optional pycparser parser tables and the upstream
`pkg_resources` deprecation. They did not change the Windows artifact result.

Rollback status: `NOT_REQUIRED`.
