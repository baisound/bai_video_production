# AI動画制作自動化システム — Project Roadmap Canonical Ver.1.4

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
- TASK-002 `Resolve Capability Spike`: **COMPLETED**
  - DaVinci Resolve Studio `21.0.2.4` へ実接続済み
  - Final sandbox Capability Matrix: 23項目中 15 `SUPPORTED` / 1 `LIMITED` / 7 `PROBE_REQUIRED` / 0 `UNSUPPORTED`
  - Windows-local IPC: HTTP/JSON・Named Pipeとも認証/再起動を実測済み
  - WSL2→Windows HTTP/JSON: 認証拒否、認証付きRoundtrip、同一Endpoint再起動を実測PASS。p50 `1.255 ms` / p95 `1.699 ms`
  - Final IPC ADR: WSL2→Windows primary = authenticated HTTP/JSON。Windows Named PipeはWindows-local optimization candidateとして保持
- TASK-003 `Asset Registry / Ingest / Path Resolver`: **COMPLETED**
  - package `0.3.0`; secure allowlisted source ingest, SHA-256/dedupe, rights metadata, immutable `asset://` promotion, SQLite v2, concurrency-safe `source-manifest`, recovery/Evidence PASS
- TASK-004 `Media Normalization + Local Visual/Audio AI Runtime Foundation`: **CAPABILITY VERIFIED / LIVE BEHAVIORAL EVIDENCE PENDING**
  - package `0.4.6`; exact timebase/VFR inspection, CFR proxy, 48 kHz analysis audio
  - ComfyUI local image/video runtime boundary, Character Identity, MiniMax H3 Production Brief / SingleFrame / Spectrum / Foley contracts
  - Audacity/OpenVINO external local Audio AI boundary; Noise Suppression + verified-runtime 2-stem Music Separation executable, 4-stem fail-closed until scriptable mode exists
  - local regression `249/249 PASS`; ComfyUI + Audacity/OpenVINO capability Evidence accepted; Attempt 06 stopped before Audacity mutation on a Product-side Windows timestamp-only ingest false positive now corrected in 0.4.6; bounded OpenVINO behavioral Evidence rerun remains before formal completion
- TASK-005以降: **NOT_STARTED / NOT_AUTHORIZED**
- TASK-004完了後の標準推奨次ルート: `TASK-022` を早期確立し、その後SRT/字幕・フィラー/無音Cut・SE/BGM/ナレーション生成配置をediting-firstで前倒し。Owner判断による再優先化を許容する

## 3. MVP定義

### 3.1 Technical MVP

素材を壊さず取り込み、時間軸を正規化し、字幕・Cut候補・Scene情報を生成し、Canonical Edit PlanからDaVinci ResolveのAutomation-owned Timelineへ安全に配置し、Render QAとHuman Handoffまで到達する。

**Editing-first Critical Path:**

`001 → 002 → 003 → 004 → 022 → (006 + 023 + 024) → 007 → 010 → 011 → 012`

`005 Scene Boundary`は編集品質向上の重要機能だが、SRT/フィラー/無音Cutの最初のVertical Sliceを阻害しない場合は並列または後追い可能とする。`020 Resource Admission`は高負荷処理導入前のSafety Gateとして必要時点までに組み込む。 TASK-004ではOwner優先判断によりLocal Image/Video/Audio AI Runtimeの最低限の実行基盤とResource Admission sliceを前倒ししたが、生成素材のTimeline配置や自動創作判断は後続TASKの責務を維持する。

### 3.2 Production Pilot

Technical MVPに加え、Privacy Guard、Storage Lifecycle、運用Dashboardを有効化し、実案件で監査可能に運用できる状態。

### 3.3 Enhanced Product

Multimodal/DBD最適化、AI SE/BGM/Video/TTS、Smart Reframe/Remotion、YouTube Feedback、Profile Auto-Tuner、Premiere Adapter等を追加した拡張版。

## 4. Phase Roadmap

| Phase | 目的 | Canonical TASK | Exit Gate |
|---|---|---|---|
| P0 Foundation & Capability | 正本・State・Resolve実機能力を確定 | 001, 002 | Foundation PASS + Resolve/IPC ADR |
| P1 Media + Local AI Foundation | 素材・Path・Timebase・Local AI Runtime・最小資源Admission・Timeline Mapping確立 | 003, 004, 020, 022 | Golden ingest/normalize + local runtime capability Gate |
| P2 Editing Analysis MVP | ASR・SRT・字幕・無音/フィラー/言い直しCut候補を優先生成。Scene解析は並列化可能 | 006, 023, 024, 005 | Editing Analysis Manifest再現性 PASS |
| P3 Edit Intelligence | Candidate Graph、Multimodal、DBD Profile | 007, 008, 009 | Edit Plan品質/再現性 Gate |
| P4 Resolve Editing MVP | 元動画Cut、SRT/字幕Track、SE/BGM/ナレーションをResolveへ配置し、Render QA、人間Handoff | 010, 011, 012, 026 | **Technical MVP** |
| P5 Generative Enhancement | TASK-004で確立したLocal AI Runtime上にAI SE/BGM/ナレーション/生成映像の創作判断・高度化を追加 | 013, 014 | Rights/Cost/QA Gate |
| P6 Safety & Variants | Privacy、Storage GC、縦動画/Remotion | 016, 017, 018 | **Production Pilot** |
| P7 Learning & Operations | YouTube Feedback、自動調整、統合Dashboard | 015, 019, 021 | Operable learning loop |
| PX Optional NLE Expansion | Premiere互換出力 | 025 | Import Golden Fixture PASS |

## 5. Canonical TASK Registry

> DEV ProfileはKickoff前の予備評価。正式Profileは各TASK開始時にBAI Development OSで再判定する。

| TASK | 名称 | 主成果物 | 主要依存 | 予備Governance | 現在状態 |
|---|---|---|---|---|---|
| 001 | Project Foundation / Domain Model | ID, State, Manifest, Evidence, Checkpoint, DB | - | DEV-4 | COMPLETED |
| 002 | Resolve Capability Spike | Capability Matrix, IPC ADR, live Evidence | 001 | DEV-4 | COMPLETED |
| 003 | Asset Registry / Ingest / Path Resolver | Ingest API, rights, checksum, path mapping | 001 | DEV-4 / score 33 | COMPLETED |
| 004 | Media Normalization + Local Visual/Audio AI Runtime Foundation | exact timebase/proxy/48k, ComfyUI image/H3, Character Identity, SingleFrame/Spectrum/Foley, Audacity OpenVINO, minimum admission/Evidence | 003 | DEV-4 / score 25 | CAPABILITY VERIFIED / LIVE BEHAVIORAL EVIDENCE PENDING |
| 005 | Scene Boundary | Scene Manifest, detector adapter, fixtures | 004 | DEV-3候補 | NOT STARTED |
| 006 | ASR / Subtitle | Transcript/SRT, VAD, dictionary, review gate; Resolve字幕配置用canonical subtitle plan | 004 | DEV-3/4候補 | NOT STARTED |
| 007 | Candidate Clip Graph / Cut Plan | DAG/score/target-duration Edit Plan。基本Cut統合sliceは006/024で先行可、Scene-aware完全版は005も利用 | 006,024; full版は005 | DEV-3候補 | NOT STARTED |
| 008 | Multimodal Scoring | audio/visual/OCR feature fusion | 007 | DEV-3候補 | NOT STARTED |
| 009 | DBDProfilePlugin | DBD HUD/chase/event profile | 008 | DEV-3候補 | NOT STARTED |
| 010 | Resolve Assembly MVP | 元動画Cut、Subtitle Track/SRT配置、Audio asset配置を含むGateway/Controller, AUTO_ASSEMBLY, idempotency。字幕配置/basic assembly sliceは007前に先行可 | 002,003,022; Cut plan反映は007 | DEV-4 | NOT STARTED |
| 011 | Render QA / Loudness | render queue adapter, QA, loudness/true-peak | 010 | DEV-3/4候補 | NOT STARTED |
| 012 | Manual Handoff / Cubase | EDITOR_WORK handoff, audio round-trip | 010,011 | DEV-3候補 | NOT STARTED |
| 013 | AI SE / BGM / Video Orchestration | TASK-004 local-runtime基盤を利用したSE/BGM/Video生成のProvider選択・創作制御・rights/cost/evidence。内容連動選定は007依存 | 004; 007は内容連動時 | DEV-4候補 | NOT STARTED |
| 014 | Voice TTS / Narration | ナレーション/自声TTS asset、dictionary、consent/retention。ユーザー指定原稿からの生成は003後に前倒し可 | 003; 自動原稿生成は006/007 | DEV-4 | NOT STARTED |
| 015 | YouTube Feedback | performance ingest, feedback features | 008 | DEV-3候補 | NOT STARTED |
| 016 | Privacy Guard | PII/notification/NG detection + redaction plan | 003,006 | DEV-4 | NOT STARTED |
| 017 | Storage Lifecycle / GC | archive, retention, legal hold, staged delete | 003,018 | DEV-4 | NOT STARTED |
| 018 | Smart Reframe / Remotion | canonical reframe plan, vertical outputs | 007,010 | DEV-3/4候補 | NOT STARTED |
| 019 | Profile Auto-Tuner | holdout evaluation, rollback, promotion gate | 008,015 | DEV-3/4候補 | NOT STARTED |
| 020 | Resource Admission / Monitoring | VRAM/CPU/disk/network admission + metrics | 001,004 | DEV-4候補 | NOT STARTED |
| 021 | Integrated Dashboard / Operations | job/evidence/alerts/ops UI | Evidence contracts | DEV-3候補 | NOT STARTED |
| 022 | Timeline Mapping Service | exact frame/time mapping, schema, golden fixtures | 001,003,004 | DEV-3/4候補 | NOT STARTED |
| 023 | FasterWhisper Fast Local Provider | local ASR provider/cache/evidence | 001,004,006 | DEV-3候補 | NOT STARTED |
| 024 | Silence / Filler / Disfluency Cut Candidate Worker | 無音、フィラー、言い直し、反復、長ポーズ、噛み候補、keep blocks、cut evidence | 003,004,022; ASR連動は006 | DEV-3候補 | NOT STARTED |
| 025 | Premiere FCP7 XML Adapter Spike | XML adapter, import report, frame-rate matrix | 001,022 | DEV-3候補 | NOT STARTED |
| 026 | Audio Placement & Bed Worker | SE/BGM/ナレーション placement plan、bounded snap、loop/fade、preview/full BGM bed、Resolve audio-track placement plan | 002,003,022; 013/014は生成asset利用時; 007は内容連動時 | DEV-3/4候補 | NOT STARTED |

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

### 7.1 Owner priority rule — Editing-first

Owner判断により、**動画編集そのものと直結する補助機能を原則として前倒し**する。対象には元動画Cut、無音/フィラー/言い直しCut、SRT生成、字幕Timeline配置、SE生成/配置、BGM生成/配置、ナレーション生成/配置を含む。TASK番号は変更せず、依存関係を満たす範囲でExecution Waveを前倒しする。

前倒し要求時は次の4区分で判定する。

1. `DIRECT_FORWARD` — そのまま前倒し可能。
2. `PARTIAL_FORWARD` — 生成等の独立sliceだけ先行可能。
3. `PREREQUISITE_FIRST` — 最小の依存TASK/contractだけ先行すれば前倒し可能。
4. `BLOCKED` — Safety Floorまたは未確定contractにより現時点では前倒し不可。

### Wave 1 — 現在

1. TASK-001〜003: **COMPLETED**。
2. TASK-004: **実装完了・target local-runtime Evidence待ち**。Timebase/Normalizationに加えLocal Image/Video/Audio AI foundationを前倒し済み。
3. TASK-004 final live capability Gate完了後、TASK-022: Timeline Mappingを早期確立。

### Wave 2 — 編集価値を最短で出す

- TASK-006 ASR/SRT + canonical subtitle plan
- TASK-023 FasterWhisper Provider
- TASK-024 Silence/Filler/Disfluency Cut Candidate
- TASK-010のSubtitle Track / basic Cut assembly vertical slice
- TASK-005 Scene Boundaryは上記と並列化し、SRT/フィラーCutの初回価値提供を待たせない

### Wave 3 — Cut PlanとResolve編集統合

- TASK-007 Candidate Clip Graph / Cut Plan
- TASK-010 Resolve Assembly MVPを拡張し、元動画Cut + SRT/字幕配置をE2E化
- TASK-011 Render QA/Loudness
- TASK-012 Manual Handoff/Cubase

ここを最初の明確な**「動画を投入して、Cut済み・字幕付きの自動編集Timelineを得る」完成点**とする。

### Wave 4 — 音声演出を前倒し

- TASK-013 SE/BGM/Video orchestration（TASK-004で生成Runtime基盤は先行済み。TASK-007完了を待たず、ユーザー指定Prompt/Assetによる生成sliceは前倒し可）
- TASK-014 ナレーション/TTS生成slice（ユーザー指定原稿は早期実装可）
- TASK-026 SE/BGM/ナレーション配置、BGM loop/fade、Audio Bed
- TASK-010へAudio placementを統合

内容に応じた自動SE/BGM選定や自動ナレーション構成はTASK-007/008等の解析結果へ後から接続する。

### Wave 5 — 精度向上

- TASK-005 Scene Boundaryの高度化
- TASK-008 Multimodal
- TASK-009 DBD Profile
- TASK-020 Resource Admission（TASK-004で最低限のruntime/VRAM/disk admission floorを先行実装済み。全体監視・schedulerはTASK-020で完成）

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
- Ownerが編集系機能の前倒しを指定した場合は、依存関係・Safety Floor・先行contractを確認し、可能なら最小prerequisiteまたは部分sliceで前倒しする。前倒し不可の場合は理由と解除条件を開始前に明示する。
