# TASK-059 P1C-J4 Windows Product Launch Operation Procedure

Date: `2026-08-27`

Identity: `TASK-059-P1CJ4-WINDOWS-PRODUCT-LAUNCH-OPERATION-PROCEDURE-20260827-V1`

Document class: `PRE_EXECUTION_WORK_PROCEDURE`

Status: `READY_TO_EXECUTE`

## Purpose

Rebuild the exact current TASK-059 head and verify that the unified
`BAI Video Production.exe` opens without the prior frozen-entry unhandled
exception. This unit observes only the unconfigured Main Product window and
then closes it normally.

## Preconditions

1. Use only the dedicated TASK-059 worktree at commit
   `0813c057eb7214e8308e9d156da9252c258ad964`.
2. Use the existing Windows Python 3.12 runtime and installed build
   dependencies.
3. Do not install or download dependencies.
4. Do not read `C:\key`, a real PPK, public-key file, passphrase, private seed
   or DPAPI custody file.
5. Do not write or apply a real launch configuration version `1.3.0`.
6. Do not open or automate the Owner signing-key Credential UI.
7. Do not sign, publish, promote, Release, Deploy or activate Production.

## Procedure

1. Read back the dedicated branch, exact HEAD and clean worktree state apart
   from this procedure document.
2. Run the canonical repository `build-windows-exe.bat` with the existing
   Windows Python 3.12 interpreter selected through process-local
   `BVP_BUILD_PYTHON`.
3. Confirm the canonical build, helper identity and secret-free helper smokes
   pass.
4. Confirm no existing `BAI Video Production` target window is open.
5. Launch the exact generated
   `builds/BAI Video Production/BAI Video Production.exe` through Computer Use.
6. Refresh the returned app/window inventory and require exactly one matching
   Main Product window.
7. Capture the current window screenshot and accessibility text.
8. Confirm no `Unhandled exception in script` or immediate process exit is
   observed and record the visible unconfigured Product state.
9. Do not click or type into any signing-key, credential, authentication,
   security, privacy or permission control.
10. Close the Main Product window with the normal `Alt+F4` application action.
11. Refresh the window inventory and confirm the target window is closed.

## Expected result

- Exact current-head canonical package build: `PASS`.
- Main Product window launch: `PASS`.
- Prior frozen-entry unhandled exception: `NOT_OBSERVED`.
- Normal close: `PASS`.
- Real key/config/Credential UI/custody/signing effect: `NO`.
- Install/download/settings mutation: `NO`.
- Release/Deploy/Production effect: `NO`.

## Stop conditions

Stop without interaction if a Windows authentication, credential, security,
privacy or permission dialog appears; if the desktop is locked; if more than
one matching target window exists; or if Computer Use cannot establish a
fresh exact window binding.

## Rollback

No Product data or configuration mutation is planned. If the Product remains
running after normal close, stop this unit and record `NOT_CONFIRMED`; do not
force-kill an ambiguously identified process or delete Owner data.
