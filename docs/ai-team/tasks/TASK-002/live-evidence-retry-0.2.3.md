# TASK-002 — Package 0.2.3 Final Live Evidence Retry

## Before running

1. Use the 0.2.3 repository checkpoint.
2. Start DaVinci Resolve Studio and allow it to finish opening.
3. Close any real/client Project. The sandbox probe fails closed if a non-sandbox Project is current.
4. From repository root run `python -m pip install -e .`.

## Sandbox behavioral Evidence

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\tools\windows\run-resolve-sandbox-mutation-probe.ps1 `
  -IUnderstandThisCreatesSandboxProject
```

If it fails, **do not retry blindly**. Package 0.2.3 prints `Failure code`, `Category`, `Message` and the exact `Diagnostic Evidence` path. Preserve that JSON.

## WSL2 IPC Evidence

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\tools\windows\run-wsl2-ipc-probe.ps1
```

The expected startup line is `WSL path bridge: WSLENV /p translation`. There should be no `wslpath: D\:DataProjects...` line.

## Return

ZIP the complete `resolve-spike-evidence/` directory and attach it. Both success and diagnostic failure reports are useful Evidence.
