# TASK-002 — Live Evidence Instructions

> Current note (2026-08-09): Attempt 02 read-only Evidence has been accepted. This file documents the earlier read-only retry path. For the **current final live gates**, use `attempt-02-next-evidence-instructions.md`.

## Purpose

Capture the target-machine facts required to finish TASK-002 without changing a real Project or human Timeline.

## Windows read-only run

From the repository root on the Windows workstation that has the intended DaVinci Resolve installation:

1. Start DaVinci Resolve and wait until it is fully loaded.
2. Keep the target installation available for local scripting.
3. Run:

```powershell
python -m pip install -e .
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-resolve-capability-spike.ps1
```

The updated runner intentionally exits non-zero when `live_resolve_connected=false`, while still leaving the JSON Evidence in place. A non-zero exit in that case is a retry signal, not loss of Evidence.

Expected files under `resolve-spike-evidence/`:

- `resolve-capability-report.json`
- `resolve-ipc-probe-report.json`

Return both files to the TASK-002 review. Do not edit the JSON manually.

## Safety

The runner uses read-only mode. It does not request Project creation/deletion, Timeline/media/render mutation, forced Resolve termination, or writes to a human-owned Timeline.

## WSL2 gate

The Windows-local HTTP result is not proof that the actual WSL2 process can reach/recover the intended Windows Gateway endpoint. Final IPC ADR review requires a separate target-topology reachability/authentication/restart test. See `tools/wsl/README.md`.

## Mutation rows

Rows for Project/media/Timeline/render mutations remain `PROBE_REQUIRED` after a read-only run. They may only be tested later through a separately reviewed sandbox sequence using a Project whose name begins `BAI_CAPABILITY_PROBE_`. This instruction does not authorize destructive actions.

## Attempt 01 note

Attempt 01 on Windows 11 measured both Windows-local IPC core candidates successfully, but the Resolve root object was unavailable. It also exposed and triggered correction of a historical Evidence bug that mislabeled post-discovery connection failures as `module_source_kind=NOT_FOUND`. Do not reuse the old runner for Attempt 02.
