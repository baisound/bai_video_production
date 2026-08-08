# TASK-002 — Attempt 02 Follow-up Implementation Evidence

## Package

`ai-video-production 0.2.2`

## Added after accepted Attempt 02

- `resolve_sandbox_probe.py`: minimal fail-closed behavioral sequence for isolated Resolve sandbox Projects.
- `run-resolve-sandbox-mutation-probe.ps1`: explicit user-side mutation runner requiring acknowledgement.
- `wsl-http-probe-server.py`: temporary authenticated Windows probe endpoint.
- `tools/wsl/http-ipc-client.py`: WSL2 topology client with loopback/default-gateway/resolver candidate discovery.
- `wsl_ipc_report.py`: schema-valid two-phase WSL2 report builder.
- `resolve-wsl-ipc-probe-report.schema.json`: canonical Evidence schema.
- regression tests for sandbox protection, behavior promotion and WSL same-endpoint restart contract.

## Deliberately excluded

- Project deletion
- Render start/cancel
- Resolve process termination
- writes to non-sandbox Projects
- media relink
- automated subtitle mutation

These exclusions preserve the TASK-002 Safety Floor and defer wider write behavior to later implementation Tasks.
