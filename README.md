# AI動画制作自動化システム

BAI Development OS **Consumer Project Mode** 上で開発する `ai-video-production` のConsumer Repositoryです。

## Current baseline

- Product design baseline: `AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`
- BAI Development OS baseline: package `1.0.0` / Architecture `Ver.2.27 CURRENT_CANONICAL`
- Last completed Consumer TASK: `TASK-001 — Project Foundation / Domain Model`
- Active Consumer TASK: `TASK-002 — Resolve Capability Spike`
- TASK-002 stage: `IMPLEMENTED_AWAITING_LIVE_EVIDENCE / ATTEMPT_01_REVIEWED / RESOLVE_RETRY_REQUIRED`
- TASK-002 governance: `DEV-4 FOUNDATION CRITICAL` / score `22`
- BAI Development OS Core: external / not copied into this repository
- DistributedOS: disabled

## TASK-001 implementation

TASK-001 establishes the product-domain foundation used by later video-processing tasks:

- immutable product IDs
- Production Job State Machine with optimistic concurrency and checkpoint-gated resume
- Canonical Manifest Envelope and JSON Schema contracts
- Asset Registry minimum contract and rights gating
- Logical URI / Path Resolver boundary
- atomic canonical JSON writer
- Product Error Envelope
- append-only Evidence and Checkpoint contracts
- Profile Snapshot / Product Plugin boundary
- Timeline ownership conflict guard
- SQLite WAL foundation store and operation idempotency
- external reference-code static inspection boundary

Media processing, Resolve control, FFmpeg, ASR, AI generation and publishing are intentionally outside TASK-001.

## Local verification

```bash
python -m pytest -q
python -m compileall -q src tests
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir /tmp/ai-video-wheel
```

The isolated wheel build may require network access for build dependencies. The verified offline/container route uses `--no-build-isolation` and the already-installed build backend.

## Repository layout

```text
.bai-os/project.json          Consumer adapter only
PROJECT.md                    Project canonical overview
src/ai_video_production/      Product foundation source
schemas/                      Product JSON Schemas
profiles/                     Product profile fixtures
tests/                       Product tests
docs/design/                 Product design documents
docs/ai-team/tasks/          Project-local TASK / Evidence
references/external-skill/   Owner-provided reference-only code archives
```

## Governance boundary

BAI Development OS internal TASK numbering is independent from this repository. OS-internal `TASK-016` is not implemented or authorized by this project. A recommended next Consumer task is not started until Owner instruction is given.


## TASK-002 Resolve Capability Spike

TASK-002 is implemented to the local-verification boundary and remains open as `IMPLEMENTED_AWAITING_LIVE_EVIDENCE`. Windows Attempt 01 measured HTTP/JSON and Windows Named Pipe successfully, but Resolve returned no live root object. Attempt 01 also exposed an Evidence-labeling defect that is fixed in package `0.2.1`; a Resolve live-evidence retry is required. The capability probe is read-only by default, never promotes mutation behavior from method presence alone, emits Schema-valid failure Evidence on supervisor timeout/worker failure, and packages its report Schemas so the installed wheel works outside the repository checkout.

### Target Windows evidence run

The PowerShell runner prepends this repository's `src/` to `PYTHONPATH`; the declared runtime dependency `jsonschema` must still be available. The recommended command below installs the project and dependency into the active Python environment before the live run. From the repository root on the target Windows workstation:

```powershell
python -m pip install -e .
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-resolve-capability-spike.ps1
```

The runner writes `resolve-capability-report.json` and `resolve-ipc-probe-report.json`. It requests no mutation, deletion, forced Resolve termination, or write to a human-owned Timeline. In package `0.2.1`, the runner exits non-zero when a live Resolve root object is not obtained while preserving the diagnostic JSON. The Windows-local IPC result does **not** prove WSL2-to-Windows reachability; that remains a separate completion-gate item documented under `tools/wsl/README.md`.

### Optional mutation authorization boundary

`--allow-mutation-probes` only opens the explicit sandbox authorization gate and requires a Project name beginning `BAI_CAPABILITY_PROBE_`. The current TASK-002 implementation deliberately does not auto-run mutation sequences even after that gate is authorized. Actual sandbox behavior must be separately reviewed and executed on the target workstation before any mutation capability can become `SUPPORTED`.
