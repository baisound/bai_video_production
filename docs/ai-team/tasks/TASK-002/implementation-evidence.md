# TASK-002 — Implementation Evidence

## Canonical stage

`IMPLEMENTED_AWAITING_LIVE_EVIDENCE`

## Source contracts added

- `src/ai_video_production/resolve_loader.py`
- `src/ai_video_production/resolve_capabilities.py`
- `src/ai_video_production/ipc_probe.py`
- `src/ai_video_production/resolve_probe_cli.py`
- packaged report schemas under `src/ai_video_production/schema_resources/`
- canonical report schemas under `schemas/`
- target Windows runner under `tools/windows/`
- WSL2 live-evidence boundary under `tools/wsl/`

## Local generated Evidence

- Resolve report: `evidence/local-resolve-capability-report.json`
  - Probe ID: `EVD-01KZH248RW2369NJACX538CERQ`
  - Target Resolve connected: `false`
  - Classification: `0 SUPPORTED / 0 LIMITED / 0 UNSUPPORTED / 23 PROBE_REQUIRED`
  - Reason: target Resolve scripting module is not installed in the Linux build environment.
- IPC report: `evidence/local-ipc-probe-report.json`
  - Probe ID: `EVD-01KZH24CM0F1DPWX9N1DPGCD5J`
  - HTTP/JSON: locally measured with bearer authentication and same-endpoint restart.
  - Windows Named Pipe: unresolved off-target.
  - ADR: `PROVISIONAL`; WSL2 reachability not verified.

## Verification Evidence

- `evidence/pytest-final.txt` — 63 tests PASS.
- `evidence/compileall-final.txt` — PASS.
- `evidence/wheel-build-final.txt` — wheel build PASS and package schemas present.
- `evidence/installed-wheel-verification.txt` — installed distribution executes outside source checkout and validates both generated reports using installed schema resources.
- Wheel SHA-256 recorded by the verified build: `baa2c0deb3adf180b87039d45f8b32cc3355e518e44e58e88229ef44bb8156fa`.

## Evidence interpretation

Local lack of Resolve is not a failed capability and is not treated as `UNSUPPORTED`. Target-specific facts remain unresolved until the supplied Windows read-only runner is executed on the intended workstation.
