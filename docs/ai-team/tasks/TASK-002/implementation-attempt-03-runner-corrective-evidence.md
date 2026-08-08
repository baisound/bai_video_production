# TASK-002 — Attempt 03 Runner Corrective Implementation Evidence

- Date: 2026-08-09
- Trigger: Owner target-machine execution of package 0.2.2 final-live-gate scripts
- Status: IMPLEMENTED / LIVE RERUN REQUIRED

## Observed target failures

### Sandbox wrapper

The underlying supervised probe returned non-zero and the PowerShell wrapper threw only a generic message. The worker contract already preserves structured `mutation_error`/`connection_error` Evidence, so operator diagnosis was unnecessarily hidden.

### WSL2 wrapper

The target log showed a corrupted path at the `wslpath` boundary (`D\:DataProjects...`). The following null-method failure was secondary to the failed path conversion / absent usable phase object.

## Corrective implementation

- sandbox runner prints structured failure code/category/message/retryability/details and exact Evidence path before throwing;
- WSL runner removes direct `wslpath` conversion;
- Windows client/output paths cross the Windows→WSL boundary through temporary `WSLENV /p` variables;
- phase 1 output file and `host_kind` are validated before phase 2;
- WSL `python3` availability is checked explicitly;
- all temporary WSL bridge variables, `WSLENV` and bearer token are restored in `finally`;
- package advanced from 0.2.2 to 0.2.3.

## Safety statement

No Resolve mutation scope was broadened. No Project deletion, render start/cancel, relink, Resolve termination, or non-sandbox write was added. IPC still requires unauthenticated rejection and authenticated round trips.
