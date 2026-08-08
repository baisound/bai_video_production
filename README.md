# AI動画制作自動化システム

BAI Development OS **Consumer Project Mode** 上で開発する `ai-video-production` のConsumer Repositoryです。

## Current baseline

- Product design baseline: `AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`
- BAI Development OS baseline: package `1.0.0` / Architecture `Ver.2.27 CURRENT_CANONICAL`
- Last completed Consumer TASK: `TASK-001 — Project Foundation / Domain Model`
- Active Consumer TASK: `TASK-002 — Resolve Capability Spike`
- TASK-002 stage: `IMPLEMENTED_AWAITING_FINAL_LIVE_EVIDENCE / ATTEMPT_02_READ_ONLY_ACCEPTED`
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

TASK-002 has accepted target-machine read-only evidence from **DaVinci Resolve Studio 21.0.2.4**. Attempt 02 connected through the Windows PROGRAMDATA scripting bridge and measured 7 safe read capabilities as `SUPPORTED`; 16 mutation/behavior-dependent capabilities remain `PROBE_REQUIRED` rather than being inferred from method presence.

Package `0.2.2` adds the two final live-evidence tools required before the TASK can close:

1. a minimal, explicit, fail-closed sandbox behavioral probe;
2. a WSL2-to-Windows authenticated HTTP topology/restart probe.

The default capability runner remains read-only. Historical Attempt 01/02 evidence is preserved under the TASK evidence directory.

### Final target evidence runs

Install the current checkout on the Windows target first:

```powershell
python -m pip install -e .
```

With Resolve Studio running and **no real/client Project left current**, execute the sandbox probe:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-resolve-sandbox-mutation-probe.ps1 -IUnderstandThisCreatesSandboxProject
```

The runner creates/uses only a Project named `BAI_CAPABILITY_PROBE_*`. It may create/save/export that sandbox, create a Bin/Timeline, import a generated one-second silent WAV, append it and add one marker. It does **not** delete Projects, start/cancel rendering, relink media, terminate Resolve, or write to a non-sandbox Project. Project identity must be positively verified before further mutation.

Then measure the actual WSL2→Windows topology:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-wsl2-ipc-probe.ps1
```

This starts only a temporary token-authenticated HTTP probe server on Windows, verifies HTTP 401 without credentials, verifies authenticated WSL2 round trips, restarts the temporary server on the same endpoint and repeats the measurement. The bearer token is ephemeral and is not stored in Evidence.

Return the generated `resolve-spike-evidence/` folder as a ZIP. TASK-002 remains open until these live outputs are reviewed, the Final IPC ADR is recorded and the DEV-4 final completion review passes.

## Project Roadmap

- Canonical design roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`
- Design-level DOCX: `docs/design/roadmap/AI動画制作自動化システム_全体開発ロードマップ_設計レベル版_Ver1.0.docx`
- External-facing overview: `docs/design/public/AI動画制作自動化システム_外向けプロジェクト概要_ロードマップ_Ver1.0.docx`

TASK-002 Attempt 02 has established live read-only scripting connectivity to DaVinci Resolve Studio 21.0.2.4. Final live gates are the isolated sandbox behavioral probe and WSL2-to-Windows IPC topology probe.
