# AI動画制作自動化システム

BAI Development OS **Consumer Project Mode** 上で開発する `ai-video-production` のConsumer Repositoryです。

## Current baseline

- Product design baseline: `AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`
- BAI Development OS baseline: package `1.0.0` / Architecture `Ver.2.27 CURRENT_CANONICAL`
- Last completed Consumer TASK: `TASK-004 — Media Normalization + Local Visual/Audio AI Runtime Foundation`
- Active Consumer TASK: `NONE`
- TASK-004 stage: `COMPLETED` / package `0.4.9`
- TASK-004 governance: `DEV-4 FOUNDATION CRITICAL` / score `25`
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

TASK-002 is **COMPLETED**. Target-machine live evidence was collected from **DaVinci Resolve Studio 21.0.2.4** through the Windows PROGRAMDATA scripting bridge. The final isolated sandbox run measured `15 SUPPORTED / 1 LIMITED / 7 PROBE_REQUIRED / 0 UNSUPPORTED`, including Project save/export, Media Pool/Bin access, generated WAV import, Timeline creation/append and marker placement.

WSL2-to-Windows authenticated HTTP/JSON also passed the required topology checks: unauthenticated rejection, authenticated roundtrip and same-endpoint restart/reconnect. The measured WSL2 result was p50 `1.255 ms` / p95 `1.699 ms` across 16 round trips. The Final IPC ADR therefore selects authenticated HTTP/JSON as the primary WSL2→Windows transport. Windows Named Pipe remains a Windows-local optimization candidate.

Package `0.2.4` retains the generated probe WAV and `.drp` under the Evidence directory instead of deleting them at process exit, and restricts Sandbox Project names to a path-safe grammar. The Owner explicitly waived another live run solely to confirm the post-run visual online state; this is not a TASK-002 completion gate.

The default capability runner remains read-only. Historical Attempt 01/02/03 Evidence is preserved under `docs/ai-team/tasks/TASK-002/evidence/`. Subtitle mutation, relink and render mutations remain `PROBE_REQUIRED` until the later owning TASK actually needs those capabilities.

Final local verification: `81 / 81` tests PASS, compileall PASS, wheel/installed-package verification PASS.

## Project Roadmap

- Canonical design roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` (Ver.1.4 editing-first priority)
- Design-level DOCX: `docs/design/roadmap/AI動画制作自動化システム_全体開発ロードマップ_設計レベル版_Ver1.2.docx`
- External-facing overview: `docs/design/public/AI動画制作自動化システム_外向けプロジェクト概要_ロードマップ_Ver1.2.docx`

TASK-003 is complete. TASK-004 ComfyUI and Audacity/OpenVINO capability Evidence is accepted; only bounded OpenVINO Noise Suppression + verified 2-stem Music Separation behavioral Evidence remains before final closure. After TASK-004 closes, TASK-022 remains the default editing-first recommendation unless the Owner reprioritizes; later TASKs remain not authorized until explicit Owner instruction.


## TASK-003 Secure Asset Ingest

TASK-003 is **COMPLETED** in package `0.3.0`. It implements explicit source-root authorization, symlink/path escape refusal, fixed-argv ffprobe inspection, streamed SHA-256, Job-local dedupe/rights conflict review, deterministic `asset://` targets, atomic target-local promotion, read-only canonical source assets, extended rights metadata, additive SQLite schema v2, concurrency-safe versioned source manifests, append-only Evidence and idempotent/partial/hard-crash recovery.

Raw machine source paths are intentionally boundary-only and are not written to successful canonical Asset/Manifest/Evidence output. Normalization/proxy/time-map processing remains TASK-004.

Final verification: `110 / 110` tests PASS, compileall PASS, wheel build PASS and a repository-external installed-wheel ingest using a real generated WAV + ffprobe PASS.


## TASK-004 Media + Local AI Runtime Foundation

TASK-004 package `0.4.9` implements exact rational timebase/VFR inspection, CFR proxy + 48 kHz analysis-audio normalization, shared derived-Asset publication, local ComfyUI image/video adapters, Character Identity, MiniMax H3 Production Brief/SingleFrame/Spectrum/Foley contracts, and an external Audacity/OpenVINO boundary for Noise Suppression and verified-runtime 2-stem Music Separation; 4-stem fails closed until a scriptable mode is exposed. Third-party runtimes/models/custom nodes are not bundled or automatically installed.

Package 0.4.9 completed the target-Windows behavioral run. OpenVINO Noise Suppression and the provable Intel-default 2-stem Music Separation path both passed with canonical derived Assets, committed Manifests and verified checksums. TASK-004 is complete.
