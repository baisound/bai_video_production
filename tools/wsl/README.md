# TASK-002 WSL2 live-evidence boundary

The Windows runner measures the Windows-local HTTP and Named Pipe candidates. It deliberately does **not** claim WSL2-to-Windows reachability.

Final IPC ADR promotion requires a separate live test from the actual WSL2 environment to the proposed Windows Gateway bind/address, with the same authentication and restart properties intended for production. Do not infer that result from localhost-only evidence.

TASK-002 remains open until that target-topology evidence is captured and reviewed.
