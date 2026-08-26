# TASK-059 P1C-J3 Windows Package Build Operation Procedure

Date: `2026-08-27`

Identity: `TASK-059-P1CJ3-WINDOWS-PACKAGE-BUILD-OPERATION-PROCEDURE-20260827-V1`

Document class: `PRE_EXECUTION_WORK_PROCEDURE`

Status: `READY_TO_EXECUTE`

## Purpose

Build the current TASK-059 head into the canonical one-directory
`BAI Video Production.exe` package and statically/native-smoke verify the
adjacent one-attempt key helper without any real Owner configuration or secret.

## Preconditions

1. Use only the dedicated TASK-059 worktree at commit
   `fd539054fa70706eece166d59358b2a1e9cfef78`.
2. Use the existing Windows Python 3.12 runtime and already installed
   PyInstaller/webview/faster-whisper dependencies.
3. Run the canonical repository `build-windows-exe.bat` only.
4. Do not install or download dependencies.
5. Do not read `C:\key`, a real PPK, public-key file, passphrase, private seed
   or DPAPI custody file.
6. Do not write or apply a real launch configuration version `1.3.0`.
7. Do not launch the Main Product UI or Credential UI in this build unit.
8. Do not sign, publish, promote, Release, Deploy or activate Production.

## Procedure

1. Read back branch, exact HEAD and clean worktree state.
2. Read back Windows Python and PyInstaller versions without installation.
3. Run `build-windows-exe.bat --help` and confirm the command performs no
   install, signing, tag, Release or Deploy.
4. Set process-local `BVP_BUILD_PYTHON` to the existing Python 3.12
   interpreter.
5. Run `build-windows-exe.bat`.
6. The canonical script builds the internal helper first, then the Main
   one-directory Product.
7. Verify staging helper, bundled helper and generated identity module agree.
8. Run the script-owned secret-free helper protocol v1 empty-input smoke and
   invalid-version refusal.
9. Compute only non-secret file sizes and SHA-256 digests for the Main EXE and
   bundled helper.
10. Confirm the source worktree remains clean.

## Expected result

- Canonical Main one-directory build: `PASS`.
- Adjacent helper identity verification: `PASS`.
- Helper empty-input protocol smoke: exit `0`.
- Invalid protocol refusal: exit `64`.
- Source mutation: `NO`.
- Secret/key/config/native UI/custody/signing effect: `NO`.

## Generated targets

- `builds/BAI Video Production`
- `builds/work/task036_shell`
- `builds/work/task059-helper-dist`
- `builds/work/task059-helper-work`

These targets are generated and Git-ignored. Existing files inside the exact
targets may be replaced by the canonical clean build.

## Rollback

If rollback is required, first ensure both generated EXEs are not running, then
remove only the four exact generated targets above. Do not reset source, delete
Owner data or touch any path outside the dedicated worktree.
