# TASK-002 — Attempt 02 Accepted / Final Live Evidence Instructions

Attempt 02 read-only Resolve Evidence is accepted. Two live evidence actions remain.

## A. Resolve sandbox behavioral evidence

1. Keep DaVinci Resolve Studio running.
2. Close any real/client Project. Do not leave a non-sandbox Project current.
3. From repository root:

```powershell
python -m pip install -e .
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-resolve-sandbox-mutation-probe.ps1 -IUnderstandThisCreatesSandboxProject
```

Expected output:

`resolve-spike-evidence/resolve-sandbox-mutation-report.json`

The sequence is deliberately limited to an isolated `BAI_CAPABILITY_PROBE_*` Project.

## B. WSL2 -> Windows IPC evidence

From Windows PowerShell at repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-wsl2-ipc-probe.ps1
```

Expected output:

`resolve-spike-evidence/resolve-wsl-ipc-probe-report.json`

The script starts a temporary authenticated HTTP probe server on Windows, calls it from WSL2, stops/restarts the temporary server on the same port, and calls it again. It does not terminate or modify DaVinci Resolve.

## Return evidence

ZIP the `resolve-spike-evidence/` folder and return it without manually editing the JSON files.
