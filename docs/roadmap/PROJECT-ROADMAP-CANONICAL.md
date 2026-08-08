# AI動画制作自動化システム — Project Roadmap Canonical Ver.1.0

- Project: `ai-video-production`
- Date: 2026-08-09
- Status: `CURRENT_CANONICAL_PROJECT_ROADMAP`
- Product Design Baseline: `AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`
- Governance: BAI Development OS Consumer Project Mode

## 1. 目的

本ロードマップは、AI動画制作自動化システムを「安全に再現できる基盤」から「実用的な編集MVP」「公開可能なProduction Pilot」「生成AI・学習を含む拡張版」へ段階的に到達させるためのProject正本である。

本書は将来TASKを**推奨・配置**するが、Owner Authorizationを代替しない。各TASKは開始時に実ファイルと最新Evidenceを基にDEV Profileを再判定し、明示的に起票・認可する。

## 2. 現在地点

- TASK-001 `Project Foundation / Domain Model`: **COMPLETED**
- TASK-002 `Resolve Capability Spike`: **IN PROGRESS**
  - DaVinci Resolve Studio `21.0.2.4` へ実接続済み
  - Resolve read-only Capability Matrix: 23項目中 7 `SUPPORTED` / 16 `PROBE_REQUIRED`
  - Windows-local IPC: HTTP/JSON・Named Pipeとも認証/再起動を実測済み
  - 残Gate: Sandbox Mutation Behavioral Evidence、WSL2→Windows IPC Evidence、Final ADR
- TASK-003以降: **NOT_STARTED / NOT_AUTHORIZED**

## 3. MVP定義

### 3.1 Technical MVP

素材を壊さず取り込み、時間軸を正規化し、字幕・Scene・候補区間を生成し、Canonical Edit PlanからDaVinci ResolveのAutomation-owned Timelineへ安全に配置し、Render QAとHuman Handoffまで到達する。

**Technical MVP Critical Path:**

`001 → 002 → 003 → 004 → (005 + 006) → 007 → 010 → 011 → 012`

補助基盤として `020 Resource Admission` と `022 Timeline Mapping` をMVP途中へ組み込む。

### 3.2 Production Pilot

Technical MVPに加え、Privacy Guard、Storage Lifecycle、運用Dashboardを有効化し、実案件で監査可能に運用できる状態。

### 3.3 Enhanced Product

Multimodal/DBD最適化、AI SE/BGM/Video/TTS、Smart Reframe/Remotion、YouTube Feedback、Profile Auto-Tuner、Premiere Adapter等を追加した拡張版。

## 4. Phase Roadmap

| Phase | 目的 | Canonical TASK | Exit Gate |
|---|---|---|---|
| P0 Foundation & Capability | 正本・State・Resolve実機能力を確定 | 001, 002 | Foundation PASS + Resolve/IPC ADR |
| P1 Media Foundation | 素材・Path・Timebase・資源・Timeline Mapping確立 | 003, 004, 020, 022 | Golden ingest/normalize fixture PASS |
| P2 Analysis MVP | Scene・ASR・字幕・基本Cut候補を生成 | 005, 006, 023, 024 | Analysis Manifest再現性 PASS |
| P3 Edit Intelligence | Candidate Graph、Multimodal、DBD Profile | 007, 008, 009 | Edit Plan品質/再現性 Gate |
| P4 Resolve Editing MVP | Resolve自動配置、Render QA、人間Handoff | 010, 011, 012 | **Technical MVP** |
| P5 Generative Enhancement | AI素材生成、自声、SE/BGM配置 | 013, 014, 026 | Rights/Cost/QA Gate |
| P6 Safety & Variants | Privacy、Storage GC、縦動画/Remotion | 016, 017, 018 | **Production Pilot** |
| P7 Learning & Operations | YouTube Feedback、自動調整、統合Dashboard | 015, 019, 021 | Operable learning loop |
| PX Optional NLE Expansion | Premiere互換出力 | 025 | Import Golden Fixture PASS |

## 5. Canonical TASK Registry

> DEV ProfileはKickoff前の予備評価。正式Profileは各TASK開始時にBAI Development OSで再判定する。

| TASK | 名称 | 主成果物 | 主要依存 | 予備Governance | 現在状態 |
|---|---|---|---|---|---|
| 001 | Project Foundation / Domain Model | ID, State, Manifest, Evidence, Checkpoint, DB | - | DEV-4 | COMPLETED |
| 002 | Resolve Capability Spike | Capability Matrix, IPC ADR, live Evidence | 001 | DEV-4 | IN PROGRESS |
| 003 | Asset Registry / Ingest / Path Resolver | Ingest API, rights, checksum, path mapping | 001 | DEV-4候補 | NOT STARTED |
| 004 | Timebase / Proxy / Normalization | ffprobe contract, VFR/CFR, time-map, proxy | 003 | DEV-4候補 | NOT STARTED |
| 005 | Scene Boundary | Scene Manifest, detector adapter, fixtures | 004 | DEV-3候補 | NOT STARTED |
| 006 | ASR / Subtitle | Transcript/SRT, VAD, dictionary, review gate | 004 | DEV-3/4候補 | NOT STARTED |
| 007 | Candidate Clip Graph / Cut Plan | DAG/score/target-duration Edit Plan | 005,006 | DEV-3候補 | NOT STARTED |
| 008 | Multimodal Scoring | audio/visual/OCR feature fusion | 007 | DEV-3候補 | NOT STARTED |
| 009 | DBDProfilePlugin | DBD HUD/chase/event profile | 008 | DEV-3候補 | NOT STARTED |
| 010 | Resolve Assembly MVP | Gateway/Controller, AUTO_ASSEMBLY, idempotency | 002,003,007,022 | DEV-4 | NOT STARTED |
| 011 | Render QA / Loudness | render queue adapter, QA, loudness/true-peak | 010 | DEV-3/4候補 | NOT STARTED |
| 012 | Manual Handoff / Cubase | EDITOR_WORK handoff, audio round-trip | 010,011 | DEV-3候補 | NOT STARTED |
| 013 | AI SE / BGM / Video Adapters | provider adapters, rights/cost/evidence | 003,007 | DEV-4候補 | NOT STARTED |
| 014 | Voice TTS | voice assets, dictionary, consent/retention | 003,006 | DEV-4 | NOT STARTED |
| 015 | YouTube Feedback | performance ingest, feedback features | 008 | DEV-3候補 | NOT STARTED |
| 016 | Privacy Guard | PII/notification/NG detection + redaction plan | 003,006 | DEV-4 | NOT STARTED |
| 017 | Storage Lifecycle / GC | archive, retention, legal hold, staged delete | 003,018 | DEV-4 | NOT STARTED |
| 018 | Smart Reframe / Remotion | canonical reframe plan, vertical outputs | 007,010 | DEV-3/4候補 | NOT STARTED |
| 019 | Profile Auto-Tuner | holdout evaluation, rollback, promotion gate | 008,015 | DEV-3/4候補 | NOT STARTED |
| 020 | Resource Admission / Monitoring | VRAM/CPU/disk/network admission + metrics | 001,004 | DEV-4候補 | NOT STARTED |
| 021 | Integrated Dashboard / Operations | job/evidence/alerts/ops UI | Evidence contracts | DEV-3候補 | NOT STARTED |
| 022 | Timeline Mapping Service | exact frame/time mapping, schema, golden fixtures | 001,003,004 | DEV-3/4候補 | NOT STARTED |
| 023 | FasterWhisper Fast Local Provider | local ASR provider/cache/evidence | 001,004,006 | DEV-3候補 | NOT STARTED |
| 024 | Silence Cut Candidate Worker | silence profile, keep blocks, cut evidence | 003,004,022 | DEV-3候補 | NOT STARTED |
| 025 | Premiere FCP7 XML Adapter Spike | XML adapter, import report, frame-rate matrix | 001,022 | DEV-3候補 | NOT STARTED |
| 026 | SE Placement / Preview BGM Worker | placement plan, bounded snap, preview bed | 002,022,025 | DEV-3候補 | NOT STARTED |

## 6. Namespace Collision Resolution

Ver.0.6の外部SKILL追補には、既存の`VIDEO-TASK-020/021`と別内容の`020/021`が再利用される番号衝突が存在する。

Historical Designは書き換えない。本ロードマップでは次のようにCanonical再採番する。

| Historical external-skill ID | Historical名称 | New Canonical TASK |
|---|---|---|
| VIDEO-TASK-020 (collision) | Timeline Mapping Service | TASK-022 |
| VIDEO-TASK-021 (collision) | FasterWhisper Fast Local Provider | TASK-023 |
| VIDEO-TASK-022 | Silence Cut Candidate Worker | TASK-024 |
| VIDEO-TASK-023 | Premiere FCP7 XML Adapter Spike | TASK-025 |
| VIDEO-TASK-024 | SE Placement / Preview BGM Worker | TASK-026 |

既存`TASK-020=Resource Admission / Monitoring`および`TASK-021=Integrated Dashboard / Operations`を維持する。

## 7. Recommended Execution Order

### Wave 1 — 現在

1. TASK-002を完了: sandbox behavior + WSL2 IPC + Final ADR。
2. TASK-003: Asset/Ingest。
3. TASK-004: Timebase/Normalization。

### Wave 2 — 基礎を並列化

- TASK-020 Resource Admission
- TASK-022 Timeline Mapping
- TASK-005 Scene Boundary
- TASK-006 ASR/Subtitle

TASK-005/006はTASK-004完了後に並列化可能。

### Wave 3 — 候補編集

- TASK-007 Candidate Clip Graph
- TASK-023 FasterWhisper Provider（TASK-006 contract確定後）
- TASK-024 Silence Cut Candidate

### Wave 4 — Technical MVP

- TASK-010 Resolve Assembly MVP
- TASK-011 Render QA/Loudness
- TASK-012 Manual Handoff/Cubase

ここを最初の明確な**「動画を投入して、人間が仕上げられる自動編集Timelineを得る」完成点**とする。

### Wave 5 — 精度と生成

- TASK-008 Multimodal
- TASK-009 DBD Profile
- TASK-013 AI generation adapters
- TASK-014 Voice TTS
- TASK-026 SE/BGM placement

### Wave 6 — 公開運用

- TASK-016 Privacy Guard
- TASK-017 Storage Lifecycle/GC
- TASK-018 Smart Reframe/Remotion
- TASK-021 Integrated Dashboard

Production PilotではTASK-016/017/021を必須Gate候補とする。

### Wave 7 — 学習・外部拡張

- TASK-015 YouTube Feedback
- TASK-019 Profile Auto-Tuner
- TASK-025 Premiere Adapter（必要時のみ）

## 8. Cross-cutting Safety Floors

以下は小変更扱いへ落とさない。

- Resolveへの書込・Timeline ownership
- Path/Asset rights/PII/Voice data
- External provider egress/cost/credentials
- Storage deletion/GC/legal hold
- State machine/migration/idempotency
- Human-owned artifact保護

## 9. Project-wide Acceptance Milestones

### M1 Foundation Ready
TASK-001/002完了。Resolve能力・IPC境界が実測で確定。

### M2 Analysis Ready
素材→正規化→Scene/ASR→Candidate生成がManifestとEvidenceから再現可能。

### M3 Technical MVP
Canonical Edit Plan→Resolve AUTO_ASSEMBLY→Render QA→Human HandoffがE2E PASS。

### M4 Production Pilot
Privacy/Retention/Monitoringを含め、実案件を安全に処理できる。

### M5 Enhanced Automation
DBD/Multimodal/AI生成/縦動画がProfileで交換可能。

### M6 Learning Loop
公開後Feedbackを収集し、Holdout/人間承認付きでProfile改善できる。

## 10. Roadmap Change Control

- 本書をProject-level roadmap正本とする。
- Historical設計書は変更しない。
- 新TASK追加時は空き番号を使用し、既存IDを再利用しない。
- TASK依存変更は`docs/ai-team/task-index.md`と本書を同時更新する。
- TASK開始はOwner指示を必要とし、ロードマップ掲載だけでは認可されない。
