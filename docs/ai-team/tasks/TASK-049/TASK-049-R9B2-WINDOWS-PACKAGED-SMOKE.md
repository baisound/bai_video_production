# TASK-049 R9B2 — Windows Packaged Game Intelligence Smoke

- Status: `READY_FOR_WINDOWS_EXECUTION / NOT_EXECUTED_ON_CURRENT_LINUX_HOST`
- Date: `2026-08-18`
- Scope: packaged `BAI Video Production.exe` Game Intelligence read/review/restart smoke
- Public release / tag / deploy: `NOT AUTHORIZED`

## Purpose

Close the native Windows packaging/read-back gate without overstating evidence from the current Linux development host.

The implementation is ready to execute on a Windows host. This repository session cannot truthfully mark R9B2 PASS because `build-windows-exe.bat`, PyInstaller Windows output, UIAutomation, and the packaged `.exe` require Windows.

## Harness

The bounded harness is:

```text
tools/windows/run-task049-r9b2-packaged-smoke.ps1
```

It uses:

```text
tools/windows/create-task049-game-intelligence-fixture.py
```

The fixture is synthetic and is explicitly not native-media accuracy evidence.

## Windows command

From the BAI VIDEO PRODUCTION repository root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task049-r9b2-packaged-smoke.ps1 `
  -EvidenceDirectory .\evidence\task049-r9b2
```

## What the harness verifies

1. Existing `build-windows-exe.bat` builds the packaged Windows product.
2. `builds\BAI Video Production\BAI Video Production.exe` exists.
3. The EXE SHA-256 is captured.
4. A bounded TASK-049 synthetic Game Intelligence project fixture is created.
5. The packaged app launches using the trusted TASK-036 launch configuration.
6. The additive `G Game Intelligence` workspace is reachable through the packaged UI.
7. A seeded `WINDOW_VAULT · NEEDS_REVIEW` event is visible.
8. Human `Approve / Confirm` changes the canonical event to `CONFIRMED` through the real packaged UI path.
9. The application is closed and restarted.
10. `CONFIRMED` survives restart and is read back from the packaged product.
11. A machine-readable smoke receipt is written.

## Explicit non-effects

The harness does not authorize or perform:

- paid provider execution;
- Production Timeline mutation;
- Resolve mutation;
- public release / tag / deploy;
- native-media accuracy claims.

## Expected evidence

The evidence directory must contain:

```text
task049-r9b2-packaged-smoke.json
```

The receipt records the executable hash, bounded smoke observations, restart/read-back result, and explicit non-effect flags.

## Acceptance

R9B2 becomes `PASS` only after the Windows command is actually executed and the produced receipt is inspected.

Until then:

```text
Execution Status: NOT_EXECUTED
Observation Status: NOT_OBSERVED
Result: NOT_CONFIRMED
```
