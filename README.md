# AI動画制作自動化システム

BAI Development OS **Consumer Project Mode** 上で開発する `ai-video-production` のConsumer Repositoryです。

## Current baseline

- Product design baseline: `AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`
- BAI Development OS baseline: package `1.0.0` / Architecture `Ver.2.27 CURRENT_CANONICAL`
- Last completed Consumer TASK: `TASK-001 — Project Foundation / Domain Model`
- TASK-001 governance: `DEV-4 FOUNDATION CRITICAL`
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
