# AI Video Production — Current State

## Canonical project state

- Project: `ai-video-production`
- Mode: `BAI Development OS CONSUMER_PROJECT_MODE`
- Project Status: `RESOLVE_SPIKE_FINAL_LIVE_EVIDENCE_PENDING`
- Last Completed Task: `TASK-001 — Project Foundation / Domain Model`
- Active Consumer Task: `TASK-002 — Resolve Capability Spike`
- TASK-002 Profile: `DEV-4 FOUNDATION CRITICAL` / score `22`
- TASK-002 Authorization: `AUTHORIZED_FOR_IMPLEMENTATION` by explicit Owner instruction on 2026-08-09
- TASK-002 Stage: `IMPLEMENTED_AWAITING_FINAL_LIVE_EVIDENCE`
- Next Consumer Task: `NONE AUTHORIZED`

## TASK-002 live evidence state

Attempt 02 is accepted as target read-only Resolve Evidence:

- Windows 11 / Python 3.12.4
- `DaVinci Resolve Studio 21.0.2.4`
- scripting connection: connected via `WINDOWS_PROGRAMDATA`
- canonical rows: `7 SUPPORTED / 16 PROBE_REQUIRED / 0 UNSUPPORTED`
- Windows-local HTTP/JSON: authentication + same-endpoint restart measured
- Windows Named Pipe: authentication + same-endpoint restart measured

Package 0.2.3 is the corrective live-evidence checkpoint. It fixes the Windows→WSL path bridge by replacing direct `wslpath` argument conversion with temporary `WSLENV /p` translation, validates phase output before reading `host_kind`, and surfaces structured sandbox `mutation_error` / `connection_error` details directly in PowerShell on failure.

## Completion gate

TASK-002 is **not COMPLETED**. Remaining gates:

1. minimal sandbox behavioral Evidence on the target Resolve installation;
2. WSL2-to-Windows IPC topology Evidence;
3. Final IPC ADR;
4. final DEV-4 Critic/Judge and completion record.

## Project roadmap

Project-level roadmap canonical: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` (Ver.1.1 editing-first).

The historical Ver.0.6 external-SKILL task-number collision is resolved prospectively by keeping existing TASK-020/021 and assigning external-SKILL additions to TASK-022 through TASK-026. Historical design documents are not rewritten.

## Safety boundaries

- Default Resolve probe remains read-only.
- Sandbox probe fails closed when a non-sandbox Project is current.
- Sandbox probe does not delete Projects, start/cancel render, relink media, terminate Resolve, or write to human/non-sandbox Projects.
- BAI Development OS Core and OS-internal TASK-016 remain untouched.
- DistributedOS remains disabled.

## Current local verification

- `pytest`: 79 / 79 PASS
- `compileall`: PASS
- package 0.2.3 wheel + installed-package schema verification: PASS
- Windows Runner runtime verification: pending Owner rerun on target Windows/WSL2 after corrective patch
