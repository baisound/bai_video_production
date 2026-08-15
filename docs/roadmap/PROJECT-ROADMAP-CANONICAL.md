# AI動画制作自動化システム — Project Roadmap Canonical Ver.1.68
- Project: `ai-video-production`
- Date: 2026-08-15
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
- TASK-004 `Media Normalization + Local Visual/Audio AI Runtime Foundation`: **COMPLETED**
  - package `0.4.10`; exact timebase/VFR inspection, CFR proxy, 48 kHz analysis audio
  - ComfyUI local image/video runtime boundary, Character Identity, MiniMax H3 Production Brief / SingleFrame / Spectrum / Foley contracts
  - Audacity/OpenVINO external local Audio AI boundary; Noise Suppression + verified-runtime 2-stem Music Separation executable, 4-stem fail-closed until scriptable mode exists
  - local regression baseline `250/250 PASS`; ComfyUI + Audacity/OpenVINO capability Evidence accepted; final Windows behavioral Evidence passed Noise Suppression and verified-runtime 2-stem Music Separation with canonical derived Assets and committed Manifests
- TASK-006 Slice D: **v0.17.0 RELEASED** — resumable large-media transcription + Resolve subtitle handoff
- TASK-024 Slice A: **v0.18.0 RELEASED** — review-only silence/filler/disfluency Cut Candidate Worker
- TASK-022: **COMPLETED** — native-Windows `263 / 263 PASS`
- TASK-007/010/011/012 + TASK-036: **SHELL_INTEGRATED / NATIVE_VALIDATED / MINIMUM_EDITING_PRODUCT_MVP_PASS**; stable Release `v0.20.1`
- R2: **COMPLETED** — TASK-037、TASK-038、TASK-027 Planning Workspace minimum
- R3: **COMPLETED** — TASK-013 Generation Safety、TASK-039、TASK-040、TASK-027 Generation Queue
- R4 current boundary: TASK-013 local/free ComfyUI readiness and TASK-041 Audio Workspace Product promotion are **HOSTED_CLOSED**; native H3 completion is **PARKED_TO_SAFE_RUNTIME_REVIEW**
- Current insertion: TASK-044 P-NLE-3 is hosted-closed through PR #71 at exact main `c23083e6fa1f8513b14010ece1c2a92c51c47916`. P-NLE-4 Unified Shell/UI and bounded Windows native acceptance are local PASS and hosted-pending; compatibility/release closure remains TASK-045. Stable Product release remains `v0.20.1`.

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
| P4A Optional Audio Finishing | REAPERで音声Sessionを再現し、mix/stemをQA後にResolveへ戻す | 035 | Auditable audio round-trip |
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
| 004 | Media Normalization + Local Visual/Audio AI Runtime Foundation | exact timebase/proxy/48k, ComfyUI image/H3, Character Identity, SingleFrame/Spectrum/Foley, Audacity OpenVINO, minimum admission/Evidence | 003 | DEV-4 / score 25 | COMPLETED |
| 005 | Scene Boundary | Scene Manifest, detector adapter, fixtures | 004 | DEV-3候補 | NOT STARTED |
| 006 | ASR / Subtitle | Transcript/SRT、VAD、非重複SRT Corrective、不変Raw Transcript、優先辞書、GUI人間Review、既定OFFのAI誤字・脱字候補、承認Gate、Resolve字幕配置用canonical subtitle plan | 004,028（外部AI補正時） | DEV-3/4候補 | SLICE D RELEASED v0.17.0 |
| 007 | Candidate Clip Graph / Cut Plan | DAG/score/target-duration Edit Plan。基本Cut統合sliceは006/024で先行可、Scene-aware完全版は005も利用 | 006,024; full版は005 | DEV-3 | IMPLEMENTED / AUTOMATED VALIDATED / SHELL INTEGRATED |
| 008 | Multimodal Scoring | audio/visual/OCR feature fusion | 007 | DEV-3候補 | NOT STARTED |
| 009 | DBDProfilePlugin | DBD HUD/chase/event profile | 008 | DEV-3候補 | NOT STARTED |
| 010 | Resolve Assembly MVP | 元動画Cut、Subtitle Track/SRT配置、Audio asset配置を含むGateway/Controller, AUTO_ASSEMBLY, idempotency。字幕配置/basic assembly sliceは007前に先行可 | 002,003,022; Cut plan反映は007 | DEV-4 | NATIVE VALIDATED / SHELL INTEGRATED |
| 011 | Render QA / Loudness | render queue adapter, QA, loudness/true-peak | 010 | DEV-3/4 | NATIVE VALIDATED / SHELL INTEGRATED |
| 012 | Manual Handoff / Cubase | EDITOR_WORK handoff, audio round-trip | 010,011 | DEV-3 | NATIVE VALIDATED / SHELL INTEGRATED |
| 013 | AI SE / BGM / Video Orchestration | TASK-004 local-runtime基盤を利用したSE/BGM/Video生成のProvider選択・創作制御・rights/cost/evidence。内容連動選定は007依存 | 004; 007は内容連動時 | DEV-4 | R3 PROMOTION COMPLETE / R4 ADAPTER HOSTED CLOSED / NATIVE RUNTIME PARKED |
| 014 | Voice TTS / Owner Narration | ElevenLabsの既存Owner Voice Profile、read-only capability/ownership probe、timed TTS、dictionary、consent/retention、48 kHz canonical narration。ユーザー指定原稿からの生成は003後に前倒し可 | 003,028; 自動原稿生成は006/007; 配置は026 | DEV-4 | DESIGN RECORDED / ADAPTER FOUNDATION EXISTS |
| 015 | YouTube Feedback | performance ingest, feedback features | 008 | DEV-3候補 | NOT STARTED |
| 016 | Privacy Guard | PII/notification/NG detection + redaction plan | 003,006 | DEV-4 | NOT STARTED |
| 017 | Storage Lifecycle / GC | archive, retention, legal hold, staged delete | 003,018 | DEV-4 | NOT STARTED |
| 018 | Smart Reframe / Remotion | canonical reframe plan, vertical outputs | 007,010 | DEV-3/4候補 | NOT STARTED |
| 019 | Profile Auto-Tuner | holdout evaluation, rollback, promotion gate | 008,015 | DEV-3/4候補 | NOT STARTED |
| 020 | Resource Admission / Monitoring | VRAM/CPU/disk/network admission + metrics | 001,004 | DEV-4候補 | NOT STARTED |
| 021 | Integrated Dashboard / Operations | job/evidence/alerts/ops UI | Evidence contracts | DEV-3候補 | NOT STARTED |
| 022 | Timeline Mapping Service | exact frame/time mapping, schema, golden fixtures | 001,003,004 | DEV-4 | COMPLETED / NATIVE WINDOWS 263 OF 263 PASS |
| 023 | FasterWhisper Fast Local Provider | local ASR provider/cache/evidence | 001,004,006 | DEV-3候補 | COMPLETE |
| 024 | Silence / Filler / Disfluency Cut Candidate Worker | 無音、フィラー、言い直し、反復、長ポーズ、噛み候補、keep blocks、cut evidence | 003,004,022; ASR連動は006 | DEV-3 | RELEASED v0.18.0 |
| 025 | Premiere FCP7 XML Adapter Spike | XML adapter, import report, frame-rate matrix | 001,022 | DEV-3候補 | NOT STARTED |
| 026 | Audio Placement & Bed Worker | SE/BGM/ナレーション placement plan、bounded snap、loop/fade、preview/full BGM bed、Resolve audio-track placement plan | 002,003,022; 013/014は生成asset利用時; 007は内容連動時 | DEV-3/4候補 | NOT STARTED |
| 027 | AI Video Creation Studio / New Production Orchestrator | GUI入力、AI制作設計提案・補正、GO承認、画像/動画/SE/BGM/ナレーション生成、Asset差し替え、Resolve自動配置 | 001-004; Slice Aは先行可、完全版は010,013,014,022,026 | DEV-4 | R2 PLANNING MINIMUM + R3 GENERATION QUEUE COMPLETE / FUTURE SLICES REMAIN |
| 035 | REAPER Audio Finishing Bridge / DaVinci Round-trip | deterministic DAW Session Plan、track/route/FX/render、iZotope capability probe、mix/stem QA、Resolve再配置 | 003,010,011,022,026 | DEV-4候補 | PROPOSED / DESIGN RECORDED |
| 036 | Unified Desktop Editing Shell / Minimum Editing Workflow Integration | W0/W1 Windows shell acceptance + W2 packaged editing E2E | 003,006,007,010,011,012,024 | DEV-4 | COMPLETE / M3B PASS / RELEASED v0.20.1 |
| 037 | Asset Registry 2 / Scene Asset Slot & Dependency Graph | Slot/Candidate/LOCK/STALE/dependency Product control | 003,027 | DEV-4 | COMPLETE R2 PRODUCT PROMOTION |
| 038 | Audit Workspace / Candidate Quality Loop | Human decision/history/recovery | 037 | DEV-4 | COMPLETE R2 PRODUCT PROMOTION |
| 039 | Continuity Map / Boundary Integrity & Stale Propagation | Continuity Edge/Human approval/STALE propagation | 037,038 | DEV-4 | COMPLETE R3 PRODUCT PROMOTION |
| 040 | Prompt Registry / Generation Evidence & Regeneration Routing | Prompt/Attempt lineage and Human regeneration planning | 037,038,039 | DEV-4 | COMPLETE R3 PRODUCT PROMOTION |
| 041 | Audio Workspace / Embedded Audio Separation & Placement UX | review/lock lanes and TASK-026 placement UX | 004,026 | DEV-4 | PRODUCT PROMOTION HOSTED CLOSED / FUTURE SLICES REMAIN |
| 042 | Product Workflow V6 Integration / Frame-bound Reference & Production UX | Blueprint v2, frame binding, WORLD LOCK projection, Prompt compilation, Timeline audio, Quick Generate | 027,036..041,013,014,026,028,032..034,043 | DEV-4 | P-V6-4 HOSTED CLOSED / PR #67 / MAIN 19f1a94f |
| 043 | Unified Product Project / Migration / Recovery Foundation | Project Manifest, compatibility/migration, atomic save recovery, Undo/Redo, Autosave/Backup, durable Product jobs | 001,003,027,036..042 | DEV-4 | HOSTED CLOSED / PR #66 / MAIN 10eae32b |
| 044 | Interactive Timeline / Unified NLE / Export Queue | dynamic tracks, seek, viewport, trim/snap, IN/OUT, durable Export Queue | 010..012,022,036,042,043 | DEV-4 | P-NLE-3 HOSTED CLOSED / P-NLE-4 LOCAL NATIVE PASS / HOSTED PENDING |
| 045 | V6 Native Acceptance / Compatibility / Release Closure | migration corpus, recovery, native UX, full regression, exact SemVer/Tag/Release | 042..044 | DEV-4 | ALLOCATED / DEPENDENCY WAIT |

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

### Wave 1 — Foundation完了

1. TASK-001〜004: **COMPLETED**。
2. TASK-004 target local-runtime behavioral Evidence: **PASS**。
3. TASK-022 Timeline Mapping: **COMPLETED / native-Windows 263 / 263 PASS**。

### Wave 2 — Editing Analysis主要slice完了

- TASK-006 ASR/SRT + canonical subtitle plan: **v0.17.0 RELEASED / SHELL INTEGRATED**
- TASK-023 FasterWhisper Provider: **COMPLETE / SHELL INTEGRATED**
- TASK-024 Silence/Filler/Disfluency Cut Candidate: **v0.18.0 RELEASED / SHELL INTEGRATED**
- TASK-010 Subtitle Track / basic Cut assembly vertical slice: **NATIVE VALIDATED / SHELL INTEGRATED**
- TASK-005 Scene Boundary: **NOT STARTED**; completed Editing Analysis routes do not depend on falsely claiming this later enhancement

### Wave 3 — Cut PlanとResolve編集統合完了

- TASK-007 Candidate Clip Graph / Cut Plan: **SHELL INTEGRATED**
- TASK-010 Resolve Assembly MVP: **NATIVE VALIDATED / SHELL INTEGRATED**
- TASK-011 Render QA/Loudness: **NATIVE VALIDATED / SHELL INTEGRATED**
- TASK-012 Manual Handoff/Cubase: **NATIVE VALIDATED / SHELL INTEGRATED**
- TASK-036 W0/W1/W2: **MINIMUM_EDITING_PRODUCT_MVP_PASS / v0.20.1 RELEASED**
- TASK-035 REAPER Audio Finishing Bridge: **PROPOSED / DESIGN RECORDED**; Technical MVP完了条件ではない

ここを最初の明確な**「動画を投入して、Cut済み・字幕付きの自動編集Timelineを得る」完成点**とする。

### Wave 4 — Generative/Audio現在位置

- TASK-013 R3 Generation Safety: **COMPLETE**
- TASK-013 R4 execution control + exact local/free ComfyUI adapter: **HOSTED CLOSED**
- TASK-013 native H3 completion: **PARKED_TO_SAFE_RUNTIME_REVIEW**; automatic replay prohibited
- TASK-014 ElevenLabs Owner Voice narration: **DESIGN RECORDED / ADAPTER FOUNDATION EXISTS**
- TASK-026 SE/BGM/ナレーション配置、BGM loop/fade、Audio Bed: **NOT STARTED / NOT AUTHORIZED**
- TASK-041 Audio Workspace: **PRODUCT PROMOTION HOSTED CLOSED / FUTURE SLICES REMAIN**
- TASK-042 V6 Product Workflow: **P-V6-4 HOSTED CLOSED**
- TASK-043 Product Project / Migration / Recovery: **P-FND-3 HOSTED CLOSED / P-FND-4 LOCAL PASS HOSTED PENDING**
- TASK-044 Interactive Timeline / Unified NLE / Export Queue: **P-NLE-3 HOSTED CLOSED / P-NLE-4 LOCAL NATIVE PASS / HOSTED PENDING**
- TASK-045 V6 Native Acceptance / Release Closure: **ALLOCATED / DEPENDENCY WAIT**

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

### Parallel Product Route — 新規動画の一気通貫制作

- TASK-028: 企画・動画・画像・音声・音楽ごとのAI/free/offline方針と、OpenAI/Anthropic/Google/local/otherの具体的Provider・Model・reasoning設定を統一するConnection Provider基盤
- TASK-027 Slice A: GUIのNew Videoフォーム、AI制作設計提案、修正・比較、Storyboard、Cost/Rights Preflight、明示的`GO`承認
- TASK-027 Slice B: TASK-004/013を使う画像・動画素材生成、ユーザー素材の採用、Asset Slot単位の差し替えと影響範囲限定再生成
- TASK-027 Slice C: TASK-013/014/026を使うSE・BGM・ナレーション生成と配置
- TASK-027 Slice D: TASK-022/010を使うAutomation-owned Resolve Timelineへの一括組立、QA、手動編集Handoff

このルートは既存動画編集を置き換えない。`EDIT_EXISTING_VIDEO`と`NEW_VIDEO_CREATION`は入口を分離し、Canonical Asset/Edit Plan/Timeline Mapping/Resolve QAを共有する。Slice AはTASK-022設計と並行着手可能だが、外部生成とResolve書込は依存TASKおよび明示的な人間承認を満たすまで実行しない。

Production PilotではTASK-016/017/021を必須Gate候補とする。

### Wave 7 — 学習・外部拡張

- TASK-015 YouTube Feedback
- TASK-019 Profile Auto-Tuner
- TASK-029 Human Edit Learning / Federated Knowledge Evolution（Owner-local適応、任意Cloud集約、署名付きKnowledge PackのGit release）
- TASK-025 Premiere Adapter（必要時のみ）

### Optional Professional Audio Route — REAPER / iZotope

- TASK-035 Slice A–B: REAPER実機Capability Probe、deterministic DAW Session Plan、dry-run diff
- Slice C–D: track/item/route/FX構築、48 kHz mix/stem render、loudness/true-peak/silence QA
- Slice E: canonical Audio Assetとして登録し、TASK-010 Gateway経由でResolveへ明示配置
- Slice F: Ozone/Nectar/Neutronを検出→挿入→parameter/preset→Assistantの段階で個別検証
- Slice G: 必要な場合のみ、同じallowlisted commandを公開するlocal MCP facadeを追加

CubaseはTASK-012のmanual handoff候補として残す。REAPERを自動化基盤に採用してもCubase Projectを自動変換するとは約束しない。第三者MCPのツール数やCubase対応範囲は固定仕様にせず、実装・version・license・securityを個別に検証する。

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

## Ver.1.7 Addendum — Scene-Compatible Reference Design Knowledge

### Decision

`BVP-KNOWLEDGE-REFIMG-001` is registered as reusable Product design knowledge. Character identity and Room identity may both look correct while the requested shot remains physically contradictory, causing generative models to invent desks, move furniture or reinterpret subject placement.

### Ownership

- TASK-004 remains completed Runtime Foundation and is not reopened.
- TASK-013 owns future `SHOT FEASIBILITY / SCENE-COMPATIBLE REFERENCE GATE` implementation and generation-request orchestration.
- TASK-003 remains Asset/checksum/rights authority.
- TASK-007 may provide content/Edit Plan context where creative selection is context-dependent.
- Timeline mutation remains outside this design.

### Required future TASK-013 scope

1. Provider-neutral Scene Reference Metadata.
2. Separate Character Identity, Room Master, Scene Shot Composition and Style Tone roles.
3. Fail-closed Shot Feasibility assessment.
4. Scene Asset Matrix lifecycle.
5. Start Frame Gate before provider execution.
6. End Frame only after Start approval.
7. `DIRECT_CONTINUATION` exact previous-End Asset/checksum reuse.
8. No editorial overlay text baked into generation assets.
9. Structured/hash Evidence by default; no raw prompt body by default.
10. Human-reviewed physical-feasibility floor until an automatic evaluator is separately proven.

### Sequence impact

No immediate execution-wave change. Editing-first remains prioritized. This addendum prevents the design from being lost before TASK-013 starts; it does not authorize TASK-013 implementation.

Detailed design:
`docs/ai-team/tasks/TASK-013/scene-compatible-reference-gate-detailed-design.md`

## Ver.1.8 Addendum — Unified Desktop Application Architecture

### Decision

`PRODUCT-ARCH-001` is now canonical.

BAI Video Production is not a final collection of independent feature tools. The target Product is one unified Desktop Application with a single user-facing entrypoint.

### Mandatory interpretation of existing TASKs

Service/Provider/Worker/CLI completion is backend capability completion. It is not automatically final Product UX completion.

Examples:

- TASK-006 FasterWhisper / Subtitle services -> final user workflow belongs in unified Subtitle Workspace.
- TASK-024 Cut Candidate Worker -> final user workflow belongs in unified Edit Workspace.
- TASK-013 Generative providers -> final user workflow belongs in unified Generative Workspace / Settings.
- TASK-010 Resolve execution -> final invocation/status/error UX belongs in the unified Application Shell.

### Design Gate

Every future user-facing/operator-facing detailed design must define `Unified Application Integration`.

Required minimum:

1. User Entry Point
2. Shell / Workspace Location
3. Project / Asset / Timeline context
4. Primary workflow
5. Running / success / failure UX
6. review / approval
7. file Open / Save / Import / Export UX
8. settings/provider configuration
9. background worker lifecycle
10. recovery/retry
11. external NLE interaction
12. native Windows acceptance
13. CLI / localhost fallback role
14. integration state at Task exit

### Integration lifecycle

`BACKEND_CAPABILITY_ONLY -> INTEGRATION_DESIGNED -> SHELL_INTEGRATED -> NATIVE_VALIDATED`

### Sequence impact

No current TASK dependency is removed or reordered by this architecture-only insertion.

TASK-023 remains next after this documentation merge, but its design/implementation record must comply with PRODUCT-ARCH-001.

The previously prepared pre-architecture TASK-023 applier is superseded and must not be applied after this merge; regenerate/rebase it against Roadmap Ver.1.8.

## Ver.1.9 Addendum — TASK-023 FasterWhisper Provider Reconciliation

### Decision

TASK-023 is implemented as a reconciliation slice over the existing TASK-006 FasterWhisper provider. No duplicate provider or second Transcript contract is introduced.

### Reused capability

- local FasterWhisper inference;
- explicit model-download gate;
- optional model cache directory;
- process-local loaded-model reuse;
- one-shot transcription;
- resumable large-media private checkpoint/chunk state;
- atomic Transcript/SRT/report publication;
- text-free operational report.

### TASK-023 additions

- deterministic source/config execution identity;
- path-minimized provider reconciliation evidence;
- model-free/network-free `ai-video-faster-whisper-evidence` diagnostic CLI;
- explicit deferral of word-level timestamp schema, final transcript result cache and recognition-semantic retuning.

### Unified Application Integration

- Canonical architecture: `PRODUCT-ARCH-001`.
- Final user entrypoint: `BAI Video Production.exe`.
- Final workspace: `Subtitle Workspace`.
- Diagnostic CLI classification: `DEVELOPER_DIAGNOSTIC_INTERFACE`.
- This slice exits no higher than `INTEGRATION_DESIGNED`.
- A future Shell integration slice is still required before `SHELL_INTEGRATED` / `NATIVE_VALIDATED`.

### Ownership

TASK-006 remains Transcript/SRT and actual-ASR contract owner. TASK-023 owns formal local-provider reconciliation/evidence only. TASK-007 remains the next editing-intelligence route after reconciliation validation.

### Status

`COMPLETE / INTEGRATION_DESIGNED`

Validation evidence: `444 passed, 1 intentional skip`; compileall/diff-check PASS; Windows real-media diagnostic evidence PASS. This completes TASK-023 without claiming `SHELL_INTEGRATED` or desktop `NATIVE_VALIDATED`.


## Ver.1.10 Addendum — Editing Technical MVP TASK-007/010/011/012

Owner instruction on 2026-08-12 authorizes a contiguous implementation wave for TASK-007 -> TASK-010 -> TASK-011 -> TASK-012. The bounded implementation establishes the first code-level Technical MVP pipeline from review-only Cut Candidates to an approved Edit Plan, Automation-owned Resolve assembly, rendered-artifact QA and deterministic EDITOR_WORK handoff.

Canonical safety decisions:

- TASK-007 candidate scores are proposal strength only and never authorize destructive cuts; per-candidate human review plus plan-level approval remains mandatory.
- TASK-010 mutates only deterministic `BAI_AUTO_*` Timelines after explicit external-write authorization. A matching assembly marker makes replay a no-op; partial/conflicting deterministic state fails closed.
- Source/normalized media frame rate is an independent binding and may not be replaced by Timeline FPS when translating source time ranges to Resolve source frames.
- TASK-011 implements rendered-artifact QA with configurable loudness/true-peak profiles; the default profile is not a universal delivery standard.
- TASK-012 creates QA-gated `EDITOR_WORK_*` packages and a bounded 48 kHz PCM Cubase round-trip; it does not claim automatic Cubase project conversion.
- All four tasks exit this automated development slice at `INTEGRATION_DESIGNED`. `SHELL_INTEGRATED` and `NATIVE_VALIDATED` require later Unified Desktop and real Windows/Resolve/Cubase Evidence.
- TASK-026 retains ownership of advanced/creative audio placement and bed-generation logic; TASK-010 only executes a supplied generic placement contract.

## Ver.1.11 Addendum — Promotion Knowledge Intake / Production Control Plane

### Decision

The 2026-08-12 Promotion Team handoff establishes a Product-level `Production Control Plane` requirement.

This is not an optional management feature. Planning contracts, Asset-to-Scene traceability, Candidate audit, Human final authority, LOCK/STALE propagation, Continuity and regeneration Evidence are now canonical Product design concerns.

`PRODUCT-ARCH-001` remains the Unified Desktop Application architecture.
`PRODUCT-CONTROL-001` becomes the cross-cutting production-control architecture inside that application.

### Canonical principles

1. `HUMAN_FINAL_AUTHORITY`
2. `PLAN_TO_ASSET_TRACEABILITY`
3. `EVIDENCE_BY_DEFAULT`
4. `GENERATE_AFTER_FEASIBILITY`
5. `VERSION_DO_NOT_OVERWRITE`
6. `REJECT_IS_NOT_DELETE`
7. `AUDIO_VISUAL_SEPARATION`
8. `LOCK_AND_STALE`
9. `NO_SILENT_AUTO_FIX`

### Existing TASK ownership refinement

- TASK-003 remains immutable ingest/checksum/rights authority and is not reopened.
- TASK-013 keeps Shot Feasibility / Scene-Compatible Reference admission ownership.
- TASK-027 expands its next Planning slice to Master Brief, Message/Claims, Scene Contract, Asset Matrix and Feasibility review orchestration.
- TASK-026 remains Audio placement/bed execution-plan owner.
- TASK-021 remains full Dashboard/Operations owner.
- TASK-029 becomes the downstream Good/Bad/Human-Override knowledge-evolution owner after structured Audit Evidence exists.
- TASK-017 remains physical retention/purge authority, so `REJECT != DELETE` does not mean indefinite storage.

### New TASK reservations

| TASK | Name | Primary output | Depends on | Initial status |
|---|---|---|---|---|
| 036 | Unified Desktop Editing Shell / Minimum Editing Workflow Integration | one-EXE editing E2E, workspace integration, native Windows acceptance | 006,007,010,011,012,022,024 | PROPOSED / OWNER PRIORITY AFTER NATIVE BACKEND GATE |
| 037 | Asset Registry 2 / Scene Asset Slot & Dependency Graph | Asset Slot, Candidate Version, lifecycle, Lock/Stale, dependency graph | 003,027 foundation | PROPOSED |
| 038 | Audit Workspace / Candidate Quality Loop | AI/Human audit, scores/findings, alternate use, regen, compare, lock | 037 | PROPOSED |
| 039 | Continuity Map / Boundary Integrity & Stale Propagation | exact End->Start continuity, impact graph, Human resolution | 037,013 contracts | PROPOSED |
| 040 | Prompt Registry / Generation Evidence & Regeneration Routing | Prompt Version, provider profile, parent Candidate, Keep Conditions, failure routing | 028,037,038 | PROPOSED |
| 041 | Audio Workspace / Embedded Audio Separation & Placement UX | audio lanes, candidate review/lock, non-destructive strip policy, TASK-026 UX | 003,026,037 | PROPOSED |

### Re-based execution order

This addendum supersedes Section 7 execution-wave order where the two conflict. Existing TASK IDs and safety ownership remain unchanged.

#### R0 — Current: Editing Native Gate

1. TASK-010 native Assembly semantics
2. source A/V preservation
3. subtitle native semantics
4. TASK-011 real Render QA/native gate
5. TASK-012 native EDITOR_WORK/Cubase gate

Exit: `BACKEND_NATIVE_EDITING_MVP_PASS`

#### R1 — Minimum user-facing Editing MVP

- TASK-036

Required final E2E:

`Open Project -> Media -> Transcribe -> Subtitle -> Cut Review -> Approve -> Resolve Apply -> QA -> EDITOR_WORK`

No PowerShell/JSON is required for the final user acceptance route.

Exit: `MINIMUM_EDITING_PRODUCT_MVP_PASS`

#### R2 — Production Control Plane Foundation

1. TASK-037 Asset Registry 2 / Scene Asset Slot
2. TASK-038 Audit Workspace / Candidate Quality Loop
3. TASK-027 Planning Workspace minimum / Scene Contract

Exit requires traceability:

`Plan -> Scene -> Asset Slot -> Candidate -> Audit -> Human Decision -> Locked Asset`

#### R3 — Generation-safe control loop

Parallelizable after R2 contracts stabilize:

- TASK-013 Shot Feasibility / Scene-Compatible Reference Gate
- TASK-039 Continuity Map / Stale propagation
- TASK-040 Prompt Registry / Generation Evidence
- TASK-027 Generation Queue integration

High-cost generation admission requires:

`PLAN_APPROVED + FEASIBILITY_PASS + REQUIRED_INPUT_LOCKED`

Repeated identical structural Failure Code >= 2 must stop Prompt micro-tuning and route back to Task Axis / Camera / Reference design.

#### R4 — Audio and generative production

- TASK-013 SE/BGM/Video orchestration
- TASK-014 Owner Narration
- TASK-026 placement/bed
- TASK-041 Audio Workspace
- TASK-010 execution integration

VFX visual and audio policy must remain separable. Strip operations are non-destructive derived-Asset operations.

#### R5 — Production Pilot Safety

- TASK-016
- TASK-017
- TASK-020 completion
- TASK-021
- TASK-018

#### R6 — Knowledge / Learning

- TASK-029 consumes Human Override, Failure Pattern, Prompt Fix, alternate-use and continuity Evidence.
- Automatic policy promotion remains gated by evaluation/rollback/Human authorization.

#### R7 — Optional expansion

- TASK-008,009,015,019,025,035 as needed.

### Milestone correction

#### M3A Backend Editing Technical MVP

Canonical Edit Plan -> real Resolve Assembly -> real Render QA -> Human Handoff is native validated.

#### M3B Minimum Editing Product MVP

M3A plus TASK-036 unified Desktop E2E.

Product-facing claims that “minimum editing is complete” require M3B, not backend service completion alone.

#### M4 Production Control Plane Ready

Planning, Asset Slot, Audit, Human decision, Continuity and Prompt/Generation Evidence are traceable and recoverable.

### Source-intake normalization decisions

- Promotion score thresholds are initial configurable policy, not hard authority.
- Provider-specific Midjourney weights/parameters remain Provider Profile data, not Product Core rules.
- The supplied Audit CSV is a seed/import-export contract; TASK-038 should normalize persistence instead of adopting one 51-column database table.
- Prompt bodies may exist in a project-private Prompt Registry under retention/privacy policy; general Evidence should store Prompt IDs/versions/hashes by default.
- Rejected/alternate Assets remain logically traceable; physical purge is governed by TASK-017.
- Proposed screens are workspaces/subviews inside `BAI Video Production.exe`, not separate final applications.

Detailed cross-cutting design:

`docs/ai-team/product-design/PRODUCTION-CONTROL-001.md`

## Ver.1.12 Addendum — Phase G Native Consumer Pilot Checkpoint

This addendum supersedes stale native-pending statements in earlier sections without changing TASK identities or safety ownership.

### Current position

- M3A `Backend Editing Technical MVP`: **NATIVE EVIDENCE PASS / RELEASE INTEGRATION PENDING**.
- TASK-010: real Resolve assembly, linked A/V, source-rate conversion, idempotency/conflict handling and edit-aware subtitle semantics PASS.
- TASK-011: real Resolve Render Queue and artifact video/audio/duration/loudness/true-peak QA PASS.
- TASK-012: real deterministic EDITOR_WORK and Cubase 13 stereo 48 kHz 24-bit PCM return PASS.
- TASK-036 W0/W1: **PARTIAL**. Native WebView2 window/layout, reachable native dialogs, focus return and packaged one-dir launch pass; clean-profile, missing-runtime recovery, full DPI/accessibility and install-path policy remain.
- TASK-036 W2: **APPLICATION_SERVICES_COMPOSED / PACKAGED_FULL_E2E_PENDING**. Trusted TASK-003/006/024 pre-edit ports now promote into Human Cut Review and the approved review reaches fixed TASK-010/011/012 runtime bindings. Trusted packaged-launcher binding, real integrated render-to-QA execution and packaged full E2E remain. `MINIMUM_EDITING_PRODUCT_MVP_PASS` remains unclaimed.

### Phase G continuation order

1. preserve the accepted TASK-010/011/012 Evidence and complete Consumer regression/CI;
2. close or explicitly park remaining TASK-036 W0/W1 cases with bounded recovery;
3. wire and run TASK-036 W2 conversation-free minimum-editing E2E;
4. capture conversation-free restart and Pilot Context Cost Evidence;
5. make the exact release-version decision from repository state;
6. finalize release metadata on the work branch, rerun regression/CI and open a PR;
7. merge only after all required checks are green, verify the exact main merge SHA, then create the annotated tag and GitHub Release.

No direct main push, force push, paid Provider execution, ambiguous human-owned Project mutation or release claim beyond accepted Evidence is permitted.

## Ver.1.13 Addendum — TASK-036 W2 Packaged Native E2E Checkpoint

This addendum supersedes the W2-pending statement in Ver.1.12 without changing TASK identities, release authority or remaining W0/W1 gates.

### Accepted W2 position

- the private trusted launcher configuration is read only by the Python host and cannot be supplied or replaced by WebView JavaScript;
- the Windows package includes the local FasterWhisper runtime and completed cached, network-free inference with model download disabled;
- one packaged session completed `Media -> Transcribe -> Subtitle -> Cut Review -> Approve -> Resolve Apply -> Native Render QA -> EDITOR_WORK`;
- Resolve mutation was limited to sandbox Project `BAI_CAPABILITY_PROBE_PHASEG_TASK010_FIX4_20260813` and Automation-owned Timeline `BAI_AUTO_A9AD30E48C30` after exact one-shot confirmation;
- TASK-011 native Render QA passed video, audio, duration, LUFS and true-peak checks;
- TASK-012 published `EDITOR_WORK_4E36CD0D60C6` atomically with a relative-path/checksum manifest and final Shell action `NONE`;
- WSL2 Ubuntu full regression passed `805 / 805`.

### Remaining Phase G boundary

W2 is `PACKAGED_NATIVE_E2E_PASS`, but TASK-036 as a whole remains active. Clean-profile startup, missing-WebView2 recovery, the full DPI/accessibility matrix and supported install-path policy remain W0/W1 gates. Conversation-free restart Evidence, Pilot Context Cost and the exact release decision also remain. Therefore overall TASK-036 `NATIVE_VALIDATED` and `MINIMUM_EDITING_PRODUCT_MVP_PASS` are not yet claimed.

Continuation order is now:

1. complete or formally park the bounded W0/W1 remainder;
2. capture conversation-free restart and Pilot Context Cost Evidence;
3. make the exact release decision from repository state;
4. finalize release metadata only if that decision authorizes it;
5. rerun regression/CI, merge through PR, verify exact main SHA, then tag and publish a GitHub Release.

### Ver.1.13 Addendum II — TASK-036 W0/W1 Formal Parking

This addendum completes the first continuation item above without promoting the parked cases to PASS.

- W0 remains `PARTIAL`; clean-profile startup, missing-WebView2 recovery and long-path mitigation are `PARKED_TO_PHASE_H2`.
- W1 remains `PARTIAL`; the full DPI/mixed-monitor and screen-reader matrix is `PARKED_TO_PHASE_H2`.
- the bounded release environment requires an installed WebView2 Runtime and a normal local install path; executable path length `166` passed and `245` failed;
- evidenced single-monitor viewports are `1600x900` and `1366x768`; wider accessibility/display claims are prohibited;
- W2 remains `PACKAGED_NATIVE_E2E_PASS`.

TASK-036 overall `NATIVE_VALIDATED`, `DESKTOP_SHELL_NATIVE_UX_PASS` and `MINIMUM_EDITING_PRODUCT_MVP_PASS` remain unclaimed. The next Phase G unit is the post-W2 conversation-free restart, followed by final Pilot Context Cost and the exact release decision.

### Ver.1.13 Addendum III — Phase G Release Decision

The independent post-W2 conversation-free restart passed at Consumer HEAD `b30da2298a47cad49d650133b6ab2ccf78f11c29`. Final Pilot Context Cost is `11,888` estimated input tokens, a reduction of `12,327` / `50.91%` from the W2 checkpoint; provider/cached/output/billed values are unavailable and remain `null`.

The exact release decision is `0.20.0 / v0.20.0 / stable`. Release metadata may now be finalized on the feature branch. The remaining order is regression and hosted CI, PR #20 merge, exact main merge SHA verification, annotated tag on that SHA, GitHub Release and branch cleanup.

The release must retain the W0/W1 limitations. Overall TASK-036 `NATIVE_VALIDATED`, `DESKTOP_SHELL_NATIVE_UX_PASS`, `MINIMUM_EDITING_PRODUCT_MVP_PASS` and M3B completion remain unclaimed.

### Ver.1.13 Addendum IV — v0.20.0 Release Publication

The bounded Phase G release integration is complete:

- PR #20 exact head `3e43b550ad3eb1db9c6b51843c0051d692c1732c` passed `9 / 9` hosted checks and merged at exact main SHA `1fc8bae6ee5bf0c63c1c7d92e21e1eb6dd966c88`;
- isolated WSL2 regression passed `805 / 805`;
- annotated tag `v0.20.0` dereferences to that exact main SHA;
- stable GitHub Release `BAI Video Production v0.20.0` and the formal Release workflow published verified wheel/source assets;
- the release branch was deleted locally/remotely while raw local `evidence/` remained preserved and untracked.

TASK-036 W0/W1 remains `PARTIAL / PARKED_TO_PHASE_H2`. Overall TASK-036 `NATIVE_VALIDATED`, `DESKTOP_SHELL_NATIVE_UX_PASS`, `MINIMUM_EDITING_PRODUCT_MVP_PASS` and M3B completion remain unclaimed. H2 may resume only when the exact clean-profile, missing-WebView2, long-path, DPI/mixed-monitor or screen-reader condition in the parking decision is available; otherwise the next Product route requires an Owner roadmap decision.

### Ver.1.14 Addendum V — TASK-036 H2 Closure and v0.20.1 Candidate

TASK-036 H2 resumed the five parked W0/W1 cases. The v0.20.1 candidate now provides fail-closed packaged startup diagnostics, native missing-WebView2 recovery, an enforced long-path support limit, explicit EdgeChromium selection, accessibility semantics and a high-scale responsive layout. Native Evidence passes clean-profile launch, actual three-monitor movement, Windows UI Automation/Narrator semantics, isolated missing-WebView2 recovery and safe owned-process exit. Full regression is `810 / 810 PASS`.

W0 is `DESKTOP_RUNTIME_SPIKE_PASS`, W1 is `DESKTOP_SHELL_NATIVE_UX_PASS` and W2 remains `W2_PACKAGED_NATIVE_E2E_PASS`. TASK-036 and M3B therefore reach `MINIMUM_EDITING_PRODUCT_MVP_PASS`. The exact patch release decision is `0.20.1 / v0.20.1 / stable`; publication still requires PR all-green, exact main merge SHA verification, annotated tag and GitHub Release.

### Ver.1.15 Addendum VI — TASK-036 v0.20.1 Release Publication

TASK-036 release finalization is complete. PR #22 exact head `916609467b2c4fc28e8e4a80ccdfbb8f6b62ff1d` passed `9 / 9` hosted checks and merged at exact release-code main SHA `c2e12d59f869a6b612848aab7ba8319e9cb8a4b4`. Annotated tag `v0.20.1` dereferences to that SHA. The stable GitHub Release and its formal workflow passed and published verified wheel/source assets. TASK-036 and M3B remain `MINIMUM_EDITING_PRODUCT_MVP_PASS`; the next Product task requires Owner roadmap routing on a new dedicated branch.

### Ver.1.16 Addendum VII — R2 Existing Foundation Product Promotion

The Owner-routed post-TASK-036 continuation activates R2 in canonical order:

1. TASK-037 Asset Registry 2 / Scene Asset Slot;
2. TASK-038 Audit Workspace / Candidate Quality Loop;
3. TASK-027 Planning Workspace minimum / Scene Contract.

This is not a greenfield restart. Current `main` already contains the domain, persistence and cross-store Foundation for Asset Slot/Candidate, LOCK/STALE, Audit, Continuity, Prompt Registry, Production Dashboard and crash-safe recovery. R2 promotes that Foundation into the user-facing Production Control Plane.

TASK-037 is the only active implementation unit at this checkpoint. It must add a durable project-scoped Application Service and bounded Desktop Production Control commands while preserving TASK-003 media ownership and TASK-038 Human decision ownership. Paid generation, automatic regeneration, physical delete and Resolve/Cubase mutation remain outside this unit. TASK-038 and TASK-027 minimum each require their own subsequent branch and Gate.

### Ver.1.17 Addendum VIII — TASK-037 Local Product Promotion Gate

TASK-037's local implementation gate passes. The existing Asset Slot/Candidate/LOCK/STALE Foundation now has a durable project-scoped Application Service and a `制作管理` workspace in the unified Desktop Shell. Slot installation is restricted to an existing Human-approved Plan. Candidate history is append-only, TASK-038 retains ACCEPT/REJECT authority, and Human LOCK is bound to the exact snapshot, Slot revision, Candidate and Asset checksum through a one-shot confirmation.

Windows full regression passes `825 / 825` executed tests with one intentional non-Windows skip. Cross-process CAS serialization, stale-confirmation rejection, tamper rejection and exact project scope are covered. No paid Provider, automatic regeneration, physical delete or Resolve/Cubase mutation is introduced.

Formal closure remains conditional on hosted PR checks, exact `main` merge verification and branch cleanup. No package, Tag or Release change is selected at this TASK-037 checkpoint. After closure, TASK-038 starts on its own branch and promotes the existing Audit Foundation into user-facing Candidate Quality decisions.

### Ver.1.18 Addendum IX — TASK-037 Hosted Closure

TASK-037 is complete. PR #24 exact head `fa71e046bf9d377d52b1845f70f2c38e21ee373f` passed `9 / 9` hosted checks and merged at exact main SHA `045bd7ed53293fd195a4993586d965bc1094ddac`. The implementation branch was deleted remotely and locally. The stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is created at this R2 checkpoint.

The next Owner-routed unit is TASK-038 Audit Workspace / Candidate Quality Loop. It starts from the exact TASK-037 closure SHA on a new dedicated branch and promotes the existing Candidate Audit Foundation into user-facing Human decisions. TASK-027 Planning Workspace minimum follows only after the TASK-038 Gate.

### Ver.1.19 Addendum X — TASK-038 Audit Product Promotion Kickoff

TASK-038 is active from exact closure main SHA `66446cf01ad5210ce196bc2803a5ffb18a37139c` on `codex/task-038-audit-product-promotion`. The accepted immutable Audit, AI/Human separation, Human decision and Production lifecycle Foundation will be promoted rather than recreated.

The critical implementation unit adds a project-scoped durable two-store Application Service, explicit interrupted-decision recovery and user-facing Candidate Audit history/actions inside the existing `制作管理` drawer. ACCEPT/REJECT/ALTERNATE_USE/NEEDS_REGENERATION remain explicit Human decisions; Reject is not Delete, regeneration does not start automatically, and Candidate decision remains separate from TASK-037 LOCK.

### Ver.1.20 Addendum XI — TASK-038 Local Product Promotion Gate

TASK-038's local implementation gate passes. The unified `制作管理` workspace now exposes immutable Audit identity/history, AI/Human separation, scores, findings, Failure Codes, Critical state, alternate-use proposals and explicit Human Candidate decisions.

Human decisions are persisted through an exact prepared two-store transaction. Restart after interruption requires an explicit exact completion/abandon/finalize action; unknown mixed state remains blocked. Reject does not Delete, NEEDS_REGENERATION does not start a Provider, and ACCEPT remains separate from TASK-037 LOCK.

Windows full regression passes `833 / 833` executed tests with one intentional non-Windows skip. Windows and WSL2 compile gates and diff check pass. Formal closure remains conditional on hosted PR checks, exact `main` merge verification and branch cleanup. No package, Tag or Release is selected at this TASK-038 checkpoint. TASK-027 Planning Workspace minimum follows after closure on a new dedicated branch.

### Ver.1.21 Addendum XII — TASK-038 Hosted Closure

TASK-038 is complete. PR #26 exact head `d756bdb80c7d0a3cee20f432abc99c390c902077` passed all `9 / 9` hosted checks and merged at exact main SHA `9a999645f36a55595eeca89347162aaba3a730a0`. The implementation branch was deleted remotely and locally.

The stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is created at this R2 checkpoint. The next Owner-routed unit is TASK-027 Planning Workspace minimum / Scene Contract, starting from the exact TASK-038 closure main on a new dedicated branch.

### Ver.1.22 Addendum XIII — TASK-027 Planning Workspace Minimum Kickoff

TASK-027 Planning Workspace minimum is active from exact TASK-038 closure main `12aa9a790e9c60705deaa13d0dcaf6b4e919c68c` on `codex/task-027-planning-workspace-minimum`. The existing Creation Intent, Proposal revision, Scene Ledger, Human GO, Approved Plan and Plan -> Scene -> Slot foundations will be promoted rather than recreated.

The bounded Product unit adds a durable project-scoped Planning Application and `企画` workspace for persisted Proposal/Scene review, exact Human GO and a separate exact Approved Plan -> TASK-037 Production Control installation. It does not call a Provider, authorize paid execution, reserve Budget, mutate Resolve/Cubase, create Candidates, make Audit decisions or LOCK Assets.

### Ver.1.23 Addendum XIV — TASK-027 Planning Workspace Minimum Local Gate

TASK-027's bounded R2 Planning Workspace minimum local gate passes. The unified Desktop `企画` workspace now displays persisted Creation Intent, Proposal revision/history, cost/rights/provider policy and complete Scene Contract cards. Exact Human GO persists the immutable Approved Production Plan. A second confirmation installs only that exact Plan into TASK-037 Production Control, preserving Plan -> Scene -> Asset Slot trace.

Windows full regression passes `842 / 842` executed tests with one intentional non-Windows skip. Concurrent Proposal publication, stale/replayed confirmation, restart and project-scope controls pass. Windows and WSL2 compile gates and diff check pass. Formal closure remains conditional on hosted PR checks, exact `main` merge and branch cleanup. No package, Tag or Release is selected at this checkpoint, and the full multi-slice TASK-027 product is not claimed complete.

### Ver.1.24 Addendum XV — TASK-027 Planning Workspace Minimum Hosted Closure

The bounded TASK-027 R2 Planning Workspace minimum is complete. PR #28 exact head `52df9ecbf426a65a853c2d0d4da84fa5dd08a58e` passed all `9 / 9` hosted checks and merged at exact main SHA `91d76febeaa3588b6c07914c32d9da151278004a`. The implementation branch was deleted remotely and locally.

This closes the R2 Product-promotion sequence: TASK-037 Asset Registry 2, TASK-038 Audit Workspace and the TASK-027 Planning Workspace minimum are now user-facing through the unified Desktop Shell. The full multi-slice TASK-027 is not claimed complete. Provider/paid execution, Generation Queue integration and external NLE mutation remain outside this closure.

The stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is created at this R2 checkpoint. R3 begins with a current-state audit and TASK-013 Shot Feasibility / Visual Compliance on a new dedicated branch. The routed R3 sequence then continues through TASK-039 Continuity Map / STALE propagation, TASK-040 Prompt Registry / Generation Evidence and the TASK-027 Generation Queue integration slice. Generation admission must ultimately require `PLAN_APPROVED + FEASIBILITY_PASS + REQUIRED_INPUT_LOCKED`.

### Ver.1.25 Addendum XVI — TASK-013 R3 Product Promotion Kickoff

TASK-013 R3 Product promotion is active from exact R2 closure main `cc893ee064f8935334dc0c5202a17d244577540a` on `codex/task-013-r3-feasibility-product-promotion`. The current checkout already contains the fail-closed Shot Feasibility, Visual Compliance, adaptive structural-failure escalation and TASK-038 Audit binding foundations; this unit promotes them rather than recreating them.

The bounded Product unit adds the Promotion hard checks, deterministic assessment identity, durable exact Approved-Plan-bound Human review and a user-facing Generation Safety workspace. It executes no Provider, paid call, Budget reservation, Candidate generation, Resolve/Cubase mutation or publishing. TASK-038 retains Human Candidate decision authority, and the complete high-cost admission conjunction remains incomplete until later R3 owners supply locked-input and queue integration Evidence.

### Ver.1.26 Addendum XVII — TASK-013 R3 Local Product Gate

TASK-013 Generation Safety passes its local Product gate. The unified Desktop `生成安全` workspace now records the complete structured Human feasibility review only against the exact current Approved Plan, Blueprint, Planning snapshot and Scene. Promotion hard checks, deterministic nested identities, append-only atomic persistence, one-shot confirmation, restart, stale/tamper/project-scope and concurrent-writer controls pass.

The existing structured Visual Compliance path is now bound to durable TASK-038 Audit persistence. Visual PASS remains Evidence rather than Human ACCEPT, critical FAIL does not automatically REJECT, and no regeneration starts. Windows full regression passes `854 / 854` executed tests with one intentional non-Windows skip. Windows/WSL2 compile, UI JavaScript syntax and diff checks pass. Formal closure remains conditional on hosted PR checks, exact `main` merge and branch cleanup.

The stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is selected at this checkpoint. After hosted closure, TASK-039 Continuity Map / STALE propagation begins on its own branch. The final `PLAN_APPROVED + FEASIBILITY_PASS + REQUIRED_INPUT_LOCKED` Product admission is not yet claimed.

### Ver.1.27 Addendum XVIII — TASK-013 R3 Hosted Closure

TASK-013 R3 Generation Safety Product promotion is complete. PR #30 exact head `b2ba2306f7511d725520adc0ae5ebdcb742ab180` passed all `9 / 9` hosted checks and merged at exact main SHA `be8ea573fde1c3d4f7abe1a73887b6633d73ef32`. The implementation branch was deleted remotely and locally.

The stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is created at this R3 checkpoint. The next Owner-routed unit is TASK-039 Continuity Map / STALE propagation, starting from exact TASK-013 closure main on a new dedicated branch. It promotes the existing Continuity Registry, crash-safe Store, Production dependency binding and Human soft-continuity review rather than recreating them.

### Ver.1.28 Addendum XIX — TASK-039 R3 Product Promotion Kickoff

TASK-039 R3 Product promotion is active from exact TASK-013 closure main `0ef7bfde85783f3f73c502c03ab5fce72c2a52c9` on `codex/task-039-r3-continuity-product-promotion`. The existing Continuity Edge/Registry/Store/Workspace, exact DIRECT_CONTINUATION identity, Human SOFT_CONTINUITY approval and TASK-037 STALE graph foundations will be promoted rather than recreated.

The bounded Product unit adds serialized CAS, recoverable exact two-store Edge registration, production-derived target inspection, restart-safe Human soft approval and a user-facing `連続性` workspace. It does not call a Provider, regenerate, delete media, clear prior Human decisions, mutate Resolve/Cubase or publish output.

### Ver.1.29 Addendum XX — TASK-039 R3 Local Product Gate

TASK-039 Continuity Product promotion passes its local Product gate. The unified Desktop `連続性` workspace now registers exact locked END_FRAME -> START_FRAME Edges through a one-shot Human confirmation, inspects only the exact current locked target Candidate, preserves non-overridable DIRECT_CONTINUATION identity and exposes separate SOFT_CONTINUITY Human approval.

Edge registration is a prepared, checksum-bound two-store transaction across `continuity-registry.json` and TASK-037 `production-control.json`. Restart classifies exact OLD/NEW combinations and exposes only bounded COMPLETE/ABANDON/FINALIZE recovery; unknown mixtures remain blocked. Continuity and Production CAS publication are locally serialized, confirmation tokens are consumed before stale revalidation, and changed roots plus downstream dependencies become STALE without deleting Evidence or starting regeneration.

The final local regression passes `869 / 869`. Focused TASK-039/TASK-037/TASK-036 integration passes `88 / 88`; Windows and WSL2 compile, Desktop JavaScript syntax and diff checks pass. Hosted PR checks, exact main merge verification and branch cleanup remain before formal TASK-039 closure. Stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is selected at this checkpoint. TASK-040 starts only after hosted closure on a new branch.

### Ver.1.30 Addendum XXI — TASK-039 R3 Hosted Closure

TASK-039 Continuity Product promotion is complete. PR #32 exact head `b40443ee24812ef8c3cef7e51b7c5e4500b33f08` passed all `9 / 9` hosted checks and merged at exact main SHA `a0bd5fb54c97dd13f4c20d059be327dc5b8d6e5b`. The implementation branch was deleted remotely and locally.

The stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is created at this R3 checkpoint. The next Owner-routed unit is TASK-040 Prompt Registry / Generation Evidence, beginning with current-checkout audit and formal DEV-4 re-decision on a new dedicated branch. It must promote the existing Prompt Entity/version, Candidate lineage, failure-driven regeneration planning and immutable next-version draft foundations rather than recreate them. TASK-027 Generation Queue integration and the complete high-cost admission conjunction remain later work.

### Ver.1.31 Addendum XXII — TASK-040 R3 Product Promotion Kickoff

TASK-040 R3 Product promotion is active from exact TASK-039 closure main `90998626642cd179c73027a9c4c1f8370a623c43` on `codex/task-040-r3-prompt-evidence-product-promotion`. The current checkout already contains Prompt Entity/version, Prompt/Attempt persistence, PASS output -> TASK-037 Candidate binding, Human NEEDS_REGENERATION planning and immutable next-Prompt draft foundations; this unit promotes them rather than recreating them.

The bounded Product unit adds strict durable parsing and serialized CAS, exact parent-lineage escalation, recoverable Prompt/Production publication for PASS output Evidence, project-scoped one-shot Prompt/Attempt/regeneration operations and a user-facing Prompt Evidence workspace. It imports or records metadata only; it does not call a Provider, spend credits, create media/Candidates, mutate Resolve/Cubase or authorize the later TASK-027 Generation Queue.

### Ver.1.32 Addendum XXIII — TASK-040 R3 Local Product Gate

TASK-040 Prompt Evidence Product promotion passes its local Product Gate. The unified Desktop Prompt Evidence workspace now registers immutable body-free Prompt metadata, imports completed Generation Attempt Evidence, binds one PASS Attempt to one existing TASK-037 Candidate through a recoverable Prompt/Production transaction and registers the next Prompt version only after a durable TASK-038 Human `NEEDS_REGENERATION` decision.

Strict restart parsing, domain reserialization, cross-process CAS, exact project/Slot/Profile/input scope, unique output ownership, non-regressing parent lineage, exact Audit recovery interlock and bounded two-store recovery pass. Full WSL2 regression is `885 / 885`; focused TASK-040/TASK-036 integration is `84 / 84`; Windows/WSL2 compile, Desktop JavaScript syntax and diff gates pass.

Hosted PR checks, exact main merge verification and branch cleanup remain before formal TASK-040 closure. Stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is selected at this checkpoint. TASK-027 Generation Queue integration remains a separate later branch and no Provider or paid execution authority is granted here.

### Ver.1.33 Addendum XXIV — TASK-040 R3 Hosted Closure

TASK-040 Prompt Evidence Product promotion is complete. PR #34 exact head `8a42aef661b6ae8a9aa80ba68591c424d7b8781a` passed all `9 / 9` hosted checks and merged at exact main SHA `87619fabe8c9ad7c8db0f5823176fd54cf7a7ae2`. The implementation branch was deleted remotely and locally.

The stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is created at this R3 checkpoint. The next Owner-routed unit is the TASK-027 Generation Queue integration slice, beginning with current-checkout audit and formal DEV Profile re-decision on a new dedicated branch. It must promote existing queue/admission foundations rather than recreate them and must not treat Prompt Evidence, configured credentials or enabled Providers as paid execution authority.

### Ver.1.34 Addendum XXV — TASK-027 R3 Generation Queue Integration Kickoff

TASK-027 Generation Queue Product promotion is active from exact TASK-040 closure main `57fc224560c567a71b405c3c59bce3cd881c65d7` on `codex/task-027-r3-generation-queue-integration`. Existing Approved Plan, durable Feasibility, LOCK/STALE, Continuity, Prompt Evidence and provider-neutral admission foundations are the implementation Source of Truth.

The bounded unit derives queue admission only from exact durable Product Evidence, uniquely proves every Prompt input through Human-GO references or LOCKED/CURRENT Candidates, persists a restart-safe one-shot-confirmed queue record and exposes it in the unified Desktop Shell. The result is `ADMISSION_READY / EXECUTION_NOT_AUTHORIZED`; no Provider call, paid authorization, Budget reservation, Candidate creation, Resolve/Cubase mutation or publishing is added.

### Ver.1.35 Addendum XXVI — TASK-027 R3 Generation Queue Local Product Gate

TASK-027 Generation Queue integration passes its local Product Gate. Exact Approved Plan, current durable Feasibility PASS, Production target, Prompt/Profile, every required input hash and non-CUT Continuity resolution are re-derived from Product stores at preparation and apply. The append-only queue record is restart-safe and remains `ADMISSION_READY / EXECUTION_NOT_AUTHORIZED`.

The unified Desktop `生成Queue` workspace exposes admission candidates, blockers and immutable Evidence without any dispatch command. Full WSL2 regression passes `893 / 893`; focused TASK-027/TASK-036 integration passes `71 / 71`; Windows/WSL2 compile, JavaScript and diff gates pass. Hosted checks, exact main merge and branch cleanup remain. Stable release stays `v0.20.1`; no package, Tag or Release is selected.

### Ver.1.36 Addendum XXVII — TASK-027 R3 Generation Queue Hosted Closure

The bounded TASK-027 Generation Queue integration is complete. PR #36 exact head `7ede711f3cb42150f38b48c8b6c2210d861b8c20` passed all `9 / 9` hosted checks and merged at exact main SHA `ac9524c9016fae1fb422619c6e16fc7ae15e42f3`. The implementation branch was deleted remotely and locally.

This closes the routed R3 control-loop promotion sequence across TASK-013, TASK-039, TASK-040 and TASK-027 Queue admission. Provider execution remains unimplemented in this Queue Product layer and separately authorized. Stable release remains `v0.20.1`; no package, Tag or Release is created. R4 Audio & Generative Production starts only after a new-branch current-state audit and formal exact owner/profile decision.

### Ver.1.37 Addendum XXVIII — TASK-013 R4 Local Generation Execution Control Kickoff

TASK-013 R4 execution-control development is active from exact R3 closure main `3c4dd8d283d9c2c68740db93c89fed6e4880d5a2` on `codex/task-013-r4-local-generation-execution`. The current checkout already contains exact Queue admission, private Prompt references, Provider routing and local ComfyUI/H3 foundations; this unit connects their authority boundaries rather than recreating them.

The bounded unit adds a body-private, restart-safe and no-replay execution controller for an explicitly injected local/free Provider port. It persists `DISPATCHING` before side effects and never converts an interrupted dispatch into an automatic retry. Paid/credential-bearing routes, live adapter composition, Candidate creation, Audit acceptance, Resolve/Cubase mutation and publishing remain prohibited or separately authorized. Stable release remains `v0.20.1`; no package, Tag or Release is selected at kickoff.

### Ver.1.38 Addendum XXIX — TASK-013 R4 Local Execution Control Local Gate

The bounded TASK-013 execution-control Product gate passes locally. Every stored Queue entry is re-derived from current Product Evidence before use; private Prompt bytes are project-contained and checksum-verified; the exact Human-approved Profile selects only a credential-free `LOCAL_FREE_AI` route. One-shot apply persists `DISPATCHING` before the injected port call, terminally records known completion/failure and leaves uncertain interruption as `RECOVERY_REQUIRED` without automatic replay.

Focused TASK-013/TASK-027/TASK-036 regression passes `58 / 58`; full WSL2 regression passes `904 / 904`; Windows/WSL2 compile, embedded JavaScript and diff gates pass. Validation uses a fake injected port and does not claim live ComfyUI/H3 execution or generated-media quality. Hosted checks, exact main merge and branch cleanup remain before formal closure. Stable release stays `v0.20.1`; no package, Tag or Release is selected.

### Ver.1.39 Addendum XXX — TASK-013 R4 Local Execution Control Hosted Closure

The bounded TASK-013 R4 execution-control foundation is complete. PR #38 exact final head `ff1cbeda707dd40f77f23ccae2c535aafe357b55` passed all `9 / 9` hosted checks and merged at exact main SHA `1614832b52183278ec403623c4a4c6c0d1e96ddc`. Its implementation branch was deleted remotely and locally.

This closure does not claim a live local generation. The next TASK-013 unit begins with a renewed target audit for exact local Provider family, endpoint, workflow, input staging and output containment before trusted-launch composition. Candidate/Audit/Prompt Attempt binding follows only after contained native output exists. Stable release remains `v0.20.1`; no package, Tag or Release is created at this checkpoint.

### Ver.1.40 Addendum XXXI — TASK-013 R4 Local ComfyUI Native Target Audit

The renewed target audit selects the installed free/local MiniMax H3 native graph behind loopback ComfyUI `0.31.0` as the exact next adapter. The target exposes `837` node classes and the required diffusion model, text encoder, video/audio VAEs and native H3 graph on an RTX 4070 SUPER. A contained capability probe used only repository-ignored `runtime/` input/output/user/temp roots and did not queue a generation.

The operator workflow is valid and establishes the technical topology, but its Prompt and notes remain private and the file will not be copied into the Product. Installed cloud/API Hailuo templates are explicitly rejected for the `LOCAL_FREE_AI` route. The authorized implementation will ship a new body-free API workflow, accept only exact local/free `TEXT_TO_VIDEO`, preserve no-replay recovery, publish only to a project-contained `project-output://` root and keep trusted-launch composition opt-in/fail-closed. Candidate/Audit/Prompt Attempt binding remains a separate post-native slice. Stable release remains `v0.20.1`; no Tag or Release is selected.

### Ver.1.41 Addendum XXXII — TASK-013 Local Comfy Native Adapter Local Gate / Native Runtime Parking

The bounded TASK-013 concrete adapter passes its local Product gate. It ships a checksum-bound body-free MiniMax H3 API workflow, accepts only the exact credential-free `LOCAL_FREE_AI / TEXT_TO_VIDEO` route, validates loopback endpoint, installed nodes/models, resource floors and exact Product-owned Comfy runtime roots, durably records the Comfy prompt identity and publishes only one verified video below `project-output://generated/<execution-id>/`. Trusted-launch composition is explicit in launch configuration `1.1.0`; legacy `1.0.0` remains fail-closed. Post-dispatch uncertainty remains recovery-required and cannot be replayed automatically.

Final exact adapter/controller/launcher regression passes `35 / 35`; full WSL2 regression passes `919 / 919`. A contained real H3 attempt reached the GPU and native model path but attempt 01 failed at `SamplerCustomAdvanced` with `hostbuf_file_reader_read failed`. Attempt 02 used legacy low-VRAM flags, was externally interrupted by the Owner-confirmed Windows force restart after the host froze and remains durably `QUEUED / RECOVERY_REQUIRED`; it is not rewritten as Product failure or replayed. No generated output, Candidate, Audit acceptance, paid call, Tag or Release is claimed.

The Product now rejects legacy `--disable-dynamic-vram`, `--lowvram`, `--highvram`, `--novram`, `--gpu-only` and `--cpu` modes before dispatch. Contained native H3 completion is therefore `PARKED_TO_SAFE_RUNTIME_REVIEW`. This parking does not block hosted review of the fail-closed adapter implementation, but Candidate/TASK-040 Attempt binding remains blocked until a separately reviewed safe native run produces verified contained output. Stable release remains `v0.20.1`.

### Ver.1.42 Addendum XXXIII — TASK-013 Local Comfy Native Adapter Hosted Closure

The bounded fail-closed adapter implementation is hosted-closed. PR #41 exact head `ff481147080518f44865c88ad0a8caffadd96947` passed all `9 / 9` GitHub checks and merged at exact main SHA `74d6b5af0c6de66168f5ab6ab63a6a049b11acd4`. The implementation branch was deleted remotely and locally.

The append-only hosted-closure documentation PR #42 exact head `a6858de5b617abfc591af866e17096b7fb0d4159` also passed all `9 / 9` checks and produced current main `7d6486059c468009042e4c186d54b566d6e1477e`. This later documentation merge does not change the implementation merge identity or create a newer Product release.

This closure confirms the reviewed adapter code and packaging, not a successful native H3 generation. Attempt 01 remains a known sampler/runtime failure and attempt 02 remains an Owner-confirmed external force-restart boundary with durable `QUEUED / RECOVERY_REQUIRED`; neither may be replayed automatically. Candidate/TASK-040 Attempt binding remains blocked until a separately reviewed safe native runtime produces a contained, media-verified output. Stable release remains `v0.20.1`; no package version, Tag or GitHub Release is created for this bounded closure.

## Addendum XXXIV — TASK-013 Safe Runtime Launch-Flag Hardening

BAI Development OS Autonomous Queue parks the exact native H3 execution behind `HG-BVP-TASK013-NATIVE-003` while selecting the independent repository-only `TASK-013-SAFE-RUNTIME-HARDENING` unit. The adapter now rejects all four memory-related flags observed in the Owner-confirmed force-restart attempt: `--disable-dynamic-vram`, `--disable-async-offload`, `--disable-pinned-memory` and `--lowvram`. Assignment-form variants are also rejected before journal reservation and before queue side effects.

The bounded local gate passes focused `39 / 39`, full WSL2 `923 / 923` and compileall. This does not authorize or claim a third native attempt. The prior uncertain prompt remains non-replayable, native H3 remains `PARKED_TO_SAFE_RUNTIME_REVIEW`, and stable release remains `v0.20.1`.

## Addendum XXXV — TASK-013 Safe Runtime Readiness Preflight Local Gate

BAI Development OS Autonomous Queue selected the independent
`TASK-013-SAFE-RUNTIME-READINESS-PREFLIGHT` unit and continued to park exact
native H3 execution behind `HG-BVP-TASK013-NATIVE-003`. The Product now exposes
an explicit application/Shell preflight that uses a body-free sentinel and the
same node/model, resource-admission and exact runtime-identity checks as the
real dispatch path.

The bounded local gate passes focused `55 / 55` and full WSL2 `926 / 926`.
The preflight queues no workflow, creates no dispatch journal or generated
output, grants no execution Authority and does not satisfy the Native Gate. It
is called only by an explicit bridge operation, never by snapshot/UI refresh.
Hosted closure remains pending. The previous uncertain prompt remains
non-replayable, native H3 remains `PARKED_TO_SAFE_RUNTIME_REVIEW`, and stable
release remains `v0.20.1`.

## Addendum XXXVI — TASK-013 Safe Runtime Readiness Preflight Hosted Closure

The bounded read-only readiness capability is hosted-closed. PR #45 exact head
`f0d3a95cd5f582f9a695ce46ecebf6955f52b046` passed all `9 / 9` GitHub checks
and merged at exact main SHA
`fac1a2fb53c3c5c439c3b1cf6c55f10d4bbf3f57`. The implementation branch was
deleted remotely, a clean fresh clone at the merge SHA was verified, and the
prior cycle clone was removed.

This hosted closure confirms only explicit read-only runtime inspection. It
does not authorize or claim generation dispatch, a journal/output, host/GPU
stability under generation load, a third native attempt, Candidate/Audit
binding, TASK-013 completion or R4 completion. The previous uncertain prompt
remains non-replayable, native H3 remains `PARKED_TO_SAFE_RUNTIME_REVIEW`, and
stable release remains `v0.20.1`.

## Addendum XXXVII — TASK-041 Audio Workspace Product Promotion Local Gate

BAI Development OS Autonomous Queue parked TASK-013 native H3 and TASK-014 paid
Owner Narration while selecting the independent TASK-041 Product promotion.
The existing Audio domain, crash-safe Store, Human placement-decision service
and TASK-026 binding were promoted rather than recreated.

The Product now has a project-scoped Audio Workspace application, exact
Production/audio snapshot binding, serialized CAS, one-shot placement and Human
decision confirmation, LOCK-only ACCEPT and a unified Desktop `音声` workspace
composed by the trusted launcher. Only accepted/locked SE/BGM/NARRATION
Candidates can enter placement review and Slot role mismatches fail closed.

Focused TASK-041/TASK-036 regression passes `64 / 64`; full WSL2 regression
passes `932 / 932`; compileall and embedded JavaScript syntax pass. No Provider,
paid request, derived-media byte write, TASK-026 compile, Resolve/Cubase
mutation, Tag or Release occurred. Hosted checks, exact main merge and branch
cleanup remain before formal closure. Stable release remains `v0.20.1`.

## Addendum XXXVIII — TASK-041 Audio Workspace Product Promotion Hosted Closure

The bounded TASK-041 Audio Workspace Product promotion is hosted-closed. PR #47
exact head `3785e44a211b8c4d81005060bc8a1faff161870d` passed all `9 / 9`
GitHub checks and merged at exact main SHA
`8dd6434a65115d88641d0942b08788a9eceda279`. The implementation branch was
deleted remotely, a clean fresh clone at the merge SHA was verified and the
prior cycle clone was removed.

This closure confirms only durable Audio placement review and exact Human
decision UX for accepted/locked SE/BGM/NARRATION Candidates. It does not call a
Provider, spend credits, create or strip media bytes, compile TASK-026, write
Resolve, open or mutate Cubase, execute TASK-014 narration, satisfy Native H3,
complete all future TASK-041 slices or close R4 overall. Stable release remains
`v0.20.1`; no package, Tag or GitHub Release is created at this checkpoint.

## Addendum XXXIX — TASK-042 V6 Product Workflow Reconciliation and Integration

The Owner inserts TASK-042 as the current maximum-priority Product route before
any TASK-013 Native H3 resumption decision. A fresh clone verified live main
`8d055773f3966e301badff28e565ffcf26578721`, package `0.20.1`, no active prior
Consumer Task, TASK-041 hosted closure and the preserved TASK-013 uncertain
execution/no-replay boundary. The older TASK007 checkout and its untracked
native Evidence remain untouched.

TASK-042 is a new cross-cutting requirement set and does not reopen historical
TASK-036..041 completion. It reuses Planning, Candidate/LOCK/STALE, Audit,
Continuity, Prompt/Attempt, Provider/Model, credential, Audio Placement Review,
Background Job and Unified Shell foundations. The required major migration is
Production Blueprint v2 with independently bound Start/End Character 0..N,
Space 0..1 and Composition 0..1 references. Legacy v1 semantics remain readable
and are never silently copied into both frames or rebound to an Approved Plan.

The historical TASK-042-only ordered route was:

```text
P-V6-0 current-main reconciliation / roadmap / full design
  -> P-V6-1 versioned Blueprint and frame-binding migration
  -> P-V6-2 WORLD LOCK / scene-compatible reference integration
  -> P-V6-3 Visual Prompt / generation / Quick authority
  -> P-V6-4 Project Timeline audio / narration / BGM / SE / ambience
  -> P-V6-5 Unified Desktop NLE / navigation / Export Queue
  -> P-V6-6 native UX / migration / recovery / full regression
  -> separate Owner decision for TASK-013 Native H3 resume
```

P-V6-0 changes design and Product Canonicals only. After its all-green PR is
merged and exact main is verified, P-V6-1A is authorized only for a standalone
closed Blueprint v2 contract and read-only migration preview. It may not change
v1 meaning, write a legacy Project, integrate Proposal/GO, add UI, call a
Provider, resume native generation, perform paid/external operations or select
a release. Later slices require the previous Gate and new exact Allowed Files.

## Addendum XL — TASK-042 P-V6-1A Blueprint v2 Contract Local Gate

P-V6-0 passed all nine hosted checks and PR #49 merged at exact main
`7be3de1a8b75dc6d88ec985ab49a2cd373f4549a`. Its remote/local branch and clean
dedicated clone were removed, then P-V6-1A started from a fresh clone of that
exact main.

P-V6-1A adds a separate closed `ProductionBlueprint 2.0.0` contract with
independent Start/End Character 0..N, Space 0..1 and Composition 0..1 identity
bindings. Existing v1 source and schema remain unchanged/readable. The new
public parser accepts exactly v1 or v2, rejects unknown versions/fields and
verifies the document checksum. Migration is deterministic read-only Evidence:
every legacy Scene remains `NEEDS_FRAME_BINDING_REVIEW`, preserves legacy IDs,
binds the exact source checksum and grants no write, GO, Provider or native
authority. Apply/store/Proposal/GO/UI integration is absent and remains P-V6-1B.

Focused tests pass `8 / 8`; full Windows regression passes `939 / 939` with one
documented platform skip. Windows and WSL2 compileall, canonical/package schema
byte equality and diff validation pass. Two Critic cycles close direct-constructor
type safety and preview-forgery resistance; unresolved Critical/High are `0 / 0`.
The hosted Gate and exact main merge remain pending. Package/release stays
`0.20.1` / `v0.20.1`; no external execution occurred.

## Addendum XLI — TASK-042 P-V6-1A Hosted Closure

PR #50 exact head `cd983bbab34258b81b61807a224a331ad8cb961f` passed all
nine required checks and merged at exact main
`694e9933d93c2d0e320486d1afa81f85e7574940`. The remote/local implementation
branch and clean dedicated clone were removed. P-V6-1A is therefore
`HOSTED_CLOSED`.

This closure does not widen claims: v1 remains unchanged/readable, migration is
preview-only, and store/Proposal/GO/UI/Provider/native/paid integration remains
unstarted. P-V6-1B is the next bounded review from fresh exact main. TASK-013
Native H3 remains parked with automatic replay prohibited. Package/release
remains `0.20.1` / `v0.20.1`.

## Addendum XLII — P-V6-1B AUTONOMY Selection, v2 Approval Integration and Windows Build

After exact main merges PR #50 and #51, the Owner-required two-merge cadence
returned control to BAI Development OS AUTONOMY. Its checksum-bound queue selected
`BVP-TASK-042-P-V6-1B / DESIGN_ONLY`; no Human Gate, paid, native, destructive,
release or credential requirement was introduced. This design PR becomes merge
`1 / 2` only after all hosted checks pass and exact main is verified.

P-V6-1B implementation has two independently testable work packages. The first
allows existing Proposal and crash-safe snapshot services to round-trip an exact
Blueprint v2 and lets one-shot Human GO bind every frame path to the exact
Asset/checksum already present in v2. Existing v1 bytes and behavior stay
compatible. Approved v2 remains blocked from Production Control compilation and
Generation admission until P-V6-2 verifies Candidate LOCK/CURRENT state; GO alone
does not create execution authority.

The second work package reuses `packaging/task036_shell.spec` and adds one root
Windows build batch. Generated output belongs under tracked-placeholder/ignored
`builds/`; canonical source is never written there. A root `docs/windows/`
build guide and a concise README Installation-adjacent section explain dependency
setup, command, output, verification, cleanup and troubleshooting. README also
explains AUTONOMY as development governance, the two-merge switch, fresh-clone
rule, Human Gate parking and multiple operator examples. BVP runtime does not
import BAI Development OS.

## Addendum XLIII — P-V6-1B Implementation Local Gate

Design PR #52 exact head `f3d99fe07a74974d0e95a925f1c72b67054e86f3`
passed all `9 / 9` hosted checks and merged at exact main
`cbf27b29ddab08050df4804c160501ff4586bb11`. Its remote/local branch and
dedicated design clone were removed. BAI Development OS Queue then selected
`BVP-TASK-042-P-V6-1B / IMPLEMENTATION` with checksum
`sha256:6a44e3fee803b247d899278c8ad137a024a8f5aebd3b090022b4333eb4cc2f95`,
and implementation began from a fresh clone of that exact main.

Existing Proposal and crash-safe snapshot records now accept the exact
`ProductionBlueprint | ProductionBlueprintV2` union. Human GO for v2 requires
every deterministic Scene/START-or-END/role path and the exact Asset ID plus
checksum already protected by the Blueprint hash. Missing, extra or changed
bindings fail closed. Approved Plan identity verification accepts v2, but
Production Control compile/install and Generation admission reject it with an
explicit P-V6-2 integration error. Candidate LOCK/CURRENT is therefore not
inferred from Human GO.

The existing TASK-036 one-dir package definition is exposed through
`build-windows-exe.bat`. The batch chooses an explicit Python, validates but
never silently installs dependencies, and writes only ignored output beneath
`builds/`. The tracked placeholder, pinned Windows build extras, root Windows
guide and README Installation section make the workflow reproducible. README's
AUTONOMY section explains startup through Queue exhaustion, minimal Context
loading, the two-main-merge cadence, cleanup/fresh-clone rule, Human Gate
parking, Session Rotation, a standard prompt and ten copyable examples without
creating Product runtime dependency or external execution authority.

Focused v1/v2 and build-contract regression passes `26 / 26`; full Windows
regression passes `946 / 946` with one intentional platform skip. An isolated
Windows 11 / Python 3.12.4 / PyInstaller 6.22.0 run produced the expected
one-dir EXE, and Git ignore checks exclude its EXE and work files. No Provider,
paid execution, Resolve/Cubase mutation, production activation, Tag or Release
occurred. Hosted implementation checks, exact main merge and cleanup remain.
That merge is cadence merge `2 / 2`; after it, control must return to AUTONOMY
before P-V6-2 or any other Product unit is selected.

## Addendum XLIV — P-V6-1B Hosted Closure and AUTONOMY Reselection

P-V6-1B implementation PR #53 exact head
`c0df2e24eccf4ba4e854b73bbb3d711509199f35` passed all `9 / 9` hosted
checks and merged at exact main `5413a85bcbb0c66599a2650b281cb9f57b19d6a2`.
The remote implementation branch and dedicated clone, including local derived
EXE/build environment, were removed. Stable release remains `v0.20.1`; no Tag,
Release, Deploy, Provider, paid, Resolve/Cubase or Production Activation action
occurred.

Because PR #52 and PR #53 complete the configured two-merge cadence, control
returned to BAI Development OS AUTONOMY. Handoff Bootstrap classified the prior
handoff as stale and current clean main as Source of Truth. Autonomous Queue
selected `BVP-TASK-042-P-V6-1B-CLOSURE-SYNC / IMPLEMENTATION`, checksum
`sha256:28c69ac969a9cf820ea4bdd570e8b67e8d38b4ebb03ad269c2ab93bd1f7e9f7c`.
TASK-013 Native H3 remains parked at its safe-runtime Human Gate and OS TASK-017
remains unauthorized, so neither blocks this documentation-only closure.

This Closure Sync is the first merge of the next two-merge cadence. After its
all-green PR, exact main verification and branch/clone cleanup, a fresh-main
Bootstrap/Queue evaluation may select `BVP-TASK-042-P-V6-2-DESIGN` in
`DESIGN_ONLY` mode. It must audit current WORLD LOCK/Candidate/Scene foundations
before designing and cannot implement P-V6-2 without a later exact authorization.

## Addendum XLV — P-V6-2 WORLD LOCK Design Gate

Closure Sync PR #54 exact head
`89ce567503b22a5e851ad66407e0a57598e79d05` passed all `9 / 9` hosted checks
and merged at exact main `f5ad4cdfa564285e9fe7a5fcf4516f1b92cae0a4`.
Its remote branch and dedicated clone were removed. A fresh clone from that
exact main passed Handoff Bootstrap with current checkout as Source of Truth,
and Autonomous Queue selected `BVP-TASK-042-P-V6-2-DESIGN / DESIGN_ONLY`,
checksum `sha256:3308c13fe176ee8b3a590912f73f26aaa75a4656786f40a9c63ec1061dc7c063`.
Native H3 remains parked at its task-local Human Gate and OS TASK-017 remains
unauthorized; neither blocks this design.

The current implementation already has the necessary canonical truth: Blueprint
v2 contains exact START/END Slot/Candidate/Asset bindings; TASK-037 owns official
Candidate LOCK/CURRENT/STALE; TASK-038 owns Human decisions; TASK-039 owns exact
DIRECT continuity; and existing stores own CAS/recovery. P-V6-2 therefore adds no
second WORLD LOCK store. It defines a deterministic read-only projection that
cross-checks every Human-GO frame path against the current project-scoped Slot,
role, locked Candidate and exact Asset checksum before Production Control or
generation admission can proceed.

The implementation design adds only three reference Slot roles, enables v2 Plan
installation after exact WORLD LOCK PASS, connects bound Candidates to Scenes so
existing stale propagation reaches downstream outputs, and makes v2 Queue input
proof require the exact Blueprint Slot/Candidate rather than GO-only hash
identity. V1 behavior remains compatible. Planning confirmations bind Proposal
and Production snapshot checksums, installation is preflighted without partial
publication, restart derives the same projection from canonical stores, and
ambiguous repeated hashes fail closed until P-V6-3 typed Prompt integration.

Two Critic cycles close duplicate-truth, partial-mutation, stale-confirmation,
hash-ambiguity, enum-compatibility and authority-consistency risks with unresolved
Critical/High `0 / 0`. The exact Allowed Files exclude Shell UI, Provider/native
runtime, media output, schema/version metadata, release and deploy changes.
P-V6-2 implementation remains `NOT_STARTED` until this design PR passes all
hosted checks, merges and completes cleanup. This design merge is cadence merge
`2 / 2`; control then returns to AUTONOMY before a fresh implementation checkout.

## Addendum XLVI — P-V6-2 WORLD LOCK Implementation Local Gate

P-V6-2 Design PR #55 exact head
`0b17e7b632c8326dc0882cb03082d1c2620139d5` passed all `9 / 9` hosted checks
and merged at exact main `6a4a6a5e28705950d0ba6457c38d9b8d119fe944`.
Its remote branch and dedicated clone were removed. Because that merge completed
cadence `2 / 2`, control returned to AUTONOMY. Fresh-main Handoff Bootstrap and
Queue selected `BVP-TASK-042-P-V6-2-IMPLEMENTATION / IMPLEMENTATION`, checksum
`sha256:9f3d976fa7b1f2379e4ecdfb07d00549ad323734d523fc4cae144875f937bebf`.

Implementation adds only the three explicit reference Slot roles and a stateless
WORLD LOCK projection over the immutable v2 Blueprint/Approved Plan and current
TASK-037 registry. Every deterministic START/END frame path must resolve to the
exact project-scoped role, Slot, official locked Candidate, Asset ID/checksum and
CURRENT lifecycle. Human GO remains separate and never creates Lock. No second
Candidate/Lock store exists.

After exact WORLD LOCK PASS, v2 installs its existing Scene output Slots and
Approved Plan/Blueprint trace. Candidate -> Scene edges connect the existing
Slot -> Candidate and Scene -> output graph, so a changed reference stales all
dependent outputs without deletion or regeneration. Complete installation is
preflighted on an isolated registry copy; Proposal and Production checksums bind
one-shot Planning confirmations. Restart reports WORLD_LOCK_REQUIRED or
WORLD_LOCK_STALE rather than crashing or silently repairing state.

Approved generation admission automatically requires all exact v2 reference
Slots. Queue proof for v2 requires deterministic frame path, role, Slot,
Candidate, Asset and checksum; GO-only references, stale/unlocked state, wrong
roles and repeated-hash ambiguity fail closed. V1 Queue and Trace output remain
compatible. TASK-039 DIRECT continuity stays exact and non-overridable.

Focused gates pass `21 / 21`, `39 / 39`, `27 / 27`, `49 / 49` and post-Critic
`29 / 29`. Final Windows full regression passes `960 / 960` with one intentional
platform skip. Two implementation Critic cycles close v1 Trace output drift,
stale restart visibility, Queue role revalidation, partial mutation and caller-
omitted input risks with unresolved Critical/High `0 / 0`. Provider, paid,
credential, native, media, physical-delete, Tag, Release and Deploy actions are
all absent.

This implementation is local PASS/hosted pending and becomes cadence merge
`1 / 2` only after all hosted checks, exact main verification and cleanup. A
fresh-main bounded hosted Closure Sync then records exact truth as merge `2 / 2`;
after its cleanup, control returns to AUTONOMY before P-V6-3 selection.

## Addendum XLVII — P-V6-2 Hosted Closure and AUTONOMY Sync

P-V6-2 implementation PR #56 exact head
`e3ab3dc3f32bfbad42f72a8d65c0d43b896f5fd3` passed all `9 / 9` hosted checks
and merged at exact main `4c77ad08172de05cf07ba3374a879fafca4bf2fd`.
The remote implementation branch and dedicated clone were removed. The merged
WORLD LOCK, v2 Production Control/Planning/Trace, transitive STALE/restart
recovery and Queue proof remain bounded to the local Product control plane. No
Provider, paid, native, media, package, Tag, Release or Deploy claim is added.

Fresh-main Handoff Bootstrap selected the clean current checkout over the stale
implementation handoff with checksum
`sha256:cbfa97e448ba9416c2f9220e5a8df89f4052aab95f3e2deeb60d142930b5b58b`.
Autonomous Queue selected `BVP-TASK-042-P-V6-2-CLOSURE-SYNC / IMPLEMENTATION`
with checksum
`sha256:c51a8f1be61128b054a2204c95faf33e66674250d29d5c0b1232e11fbdeb9614`.
P-V6-3 remains `DEPENDENCY_WAIT`; Native H3 and OS TASK-017 are task-locally
parked with `system_blocked=false`.

The documentation-only Closure Sync passes the unchanged Windows `960 / 960`
regression, Windows/WSL2 compileall, Context Cost checksum and diff gates. Critic
unresolved Critical/High is `0 / 0`. Its hosted merge completes cadence `2 / 2`.
After exact main verification and branch/clone cleanup, control returns to
AUTONOMY before any P-V6-3 design or implementation selection. Stable release
remains `v0.20.1`.

## Addendum XLVIII — P-V6-3 Prompt / Provider / Quick Design Gate

P-V6-2 Closure Sync PR #57 exact head
`34bedb48591e713475b438f4b5074d581cd73fd2` passed all `9 / 9` hosted checks
and merged at exact main `92ff6938b9def12161d8635048ad3714315ed9d4`.
Its remote branch and dedicated clone were removed. Because that merge completed
cadence `2 / 2`, control returned to AUTONOMY. Fresh-main Handoff Bootstrap and
Queue selected `BVP-TASK-042-P-V6-3-DESIGN / DESIGN_ONLY`, checksum
`sha256:9791617d02cf79ba4f0b9d4c61113edd68ce129988fd477cb39e3311b83c006a`.

The exact current-main audit confirms that TASK-040 remains the only Prompt and
Attempt truth, TASK-028/032/033/034 remain Provider/Model/Credential truth, and
TASK-037/038 remain Candidate/Audit/Lock truth. P-V6-3 adds no replacement
registry. It designs a typed immutable JA/normalized-JA/runtime-EN compilation
binding inside the existing Prompt record, a secret-free Provider -> compatible
Model readiness projection, and a versioned Quick Intent authority that never
forges Approved Plan or Human GO.

Quick Intent binds an exact existing or explicitly created target Scene Slot,
compiled Prompt, Provider route/capability, typed reference Asset identities,
rights, cost ceiling and one-shot Human decision. It records intent only. An
already-produced output becomes production-adopted only through the existing
Attempt -> Candidate -> Human Audit ACCEPT -> LOCKED/CURRENT path. Provider,
paid, credential, native, media and Candidate mutations remain outside this
design branch.

The audit also finds one exact P-V6-2 integration defect: v2 Queue derives
`WORLD_LOCKED_CURRENT_CANDIDATE`, while durable validation currently permits
only legacy proof kinds. P-V6-3 Implementation Order begins with the bounded
validator corrective and a real enqueue/persist/restart/reload test before new
Prompt or Quick code.

Two Critic cycles close duplicate-truth, plan-forgery, Prompt-body leakage,
Provider-readiness overclaim, partial mutation, legacy compatibility and
paid/native authority risks with unresolved Critical/High `0 / 0`. Exact
Allowed Files exclude Product schema/package/version, Shell UI, Provider
adapters, Credential vault, native runtime, media output, Release and Deploy.
P-V6-3 implementation remains `NOT_STARTED` until this design passes hosted
checks, merges, completes cleanup and fresh-main AUTONOMY selects it. This design
becomes cadence merge `1 / 2` after hosted closure. Stable release remains
`v0.20.1`.

## Addendum XLIX — P-V6-3 Prompt / Provider / Quick Implementation Gate

P-V6-3 Design PR #58 exact head
`0067fcc8e306a1799ccc7afeeae2638b9bb19e3b` passed hosted `9 / 9`, merged at
exact main `c78ed0141b0849b3a5d1b2229b87c320697b4980`, and completed remote
branch/dedicated clone cleanup as cadence merge `1 / 2`. Fresh-main BAI
Development OS Handoff Bootstrap selected the current checkout over the stale
handoff and Autonomous Queue selected
`BVP-TASK-042-P-V6-3-IMPLEMENTATION / IMPLEMENTATION`.

Implementation now corrects the real Blueprint v2 Queue persist/restart defect,
adds immutable private-body-free Visual Prompt compilation through the existing
TASK-040 transaction, projects every Provider/Model readiness predicate without
secrets or probes, and records append-only `QUICK_INTENT` authority with exact
Prompt/Production/Quick CAS and restart behavior. Quick never claims Approved
Plan or Human GO, never dispatches a Provider and never creates Candidate/Audit/
Lock state. Output adoption remains a read-only projection over TASK-040/037/038
truth. Uningested FILE authority and mismatched Prompt/reference hashes fail
closed.

Local focused and full gates pass and two implementation Critic cycles have
unresolved Critical/High `0 / 0`. P-V6-3 becomes hosted-closed only after the
exact implementation head passes hosted `9 / 9`, merges to main, the exact
merge SHA is verified and remote branch/dedicated clone cleanup completes as
cadence merge `2 / 2`. Fresh-main AUTONOMY must then reselect the next bounded
unit. P-V6-4 remains dependency-waiting until that closure. Native H3 and OS
TASK-017 remain task-locally parked. Stable release remains `v0.20.1`.

## Addendum L — P-V6-3 Hosted Closure and AUTONOMY Sync

P-V6-3 Implementation PR #59 exact head
`d33807287c7ccc86b5055bd6b4575c88b7e9d41b` passed hosted `9 / 9` and merged
at exact main `7ac291f1a572b5513ecb681d9c3e87ccc0e52f38`. The remote branch and
dedicated implementation clone were removed. This completed cadence merge
`2 / 2` and returned control to AUTONOMY. Stable release remains `v0.20.1`;
there was no Tag, Release or Deploy.

Fresh-main Handoff Bootstrap selected current clean main over the stale
implementation handoff with checksum
`sha256:06013802d64a0bd9a29806f7ecd1660239e79013ef975843bf868814e1d3c520`.
Autonomous Queue selected `BVP-TASK-042-P-V6-3-CLOSURE-SYNC / IMPLEMENTATION`
with checksum
`sha256:0c5f78b3c564dc896805de5fb53ebdf0172093fc504cdbb62167d1af4493b17c`.
P-V6-4 Design remains dependency-waiting; Native H3 and OS TASK-017 remain
task-locally parked with `system_blocked=false`.

This branch changes hosted/current-state documentation only. P-V6-3 remains
bounded to Queue persistence, Prompt compilation/TASK-040 integration,
secret-free Provider/Model readiness, Quick intent CAS/restart and read-only
adoption. It adds no Provider/native/media/Candidate/Audit/Lock authority. The
Closure Sync becomes cadence merge `1 / 2` only after hosted green, exact main
verification and cleanup; a fresh main clone then continues P-V6-4 Design.

## Addendum LI — P-V6-4 Timeline Audio Design Gate

P-V6-3 Closure Sync PR #60 merged at exact main
`c6a5cb108032709615ab99856890d0a3709d7d5d`. Its remote branch and dedicated
clone were removed, completing cadence merge `1 / 2`. Fresh-main Handoff
Bootstrap selected the current checkout with checksum
`sha256:b1c1709c4b00fbac5887de9fe1f3ae5deab816d13277575ac1816ba6b4342cdc`.
Autonomous Queue selected `BVP-TASK-042-P-V6-4-DESIGN / DESIGN_ONLY` with
checksum
`sha256:23e42b59c3a95ceb41e2f92af06f128d7ded8ff5b847458d4438419cbc114015`.

Current-main audit confirms that Blueprint v2 exact frames remain the Project
Timeline authority; TASK-037 remains Candidate/LOCK/STALE truth; TASK-041
remains Audio placement review/Human-decision truth; TASK-026 remains placement
compiler; TASK-014 remains narration planning and separately gated paid
execution. P-V6-4 creates no second Audio Asset, Candidate, placement, Provider
or job registry.

The design resolves the previously open SRT authority question: Master SRT is a
derived/editable proposal over canonical frame cues. It never moves Scene
boundaries. Import or edit produces a new proposal with deterministic rational
frame conversion and explicit conflicts. Blueprint checksum/rate/range changes
make the current Timeline plan stale and require a new append-only plan revision.

Timeline Audio supports whole/range BGM, cue-based SE, range ambience and
optional Scene narration across explicit parallel lanes. AMBIENCE is added as a
first-class compatible role through the existing TASK-037/041/026 lifecycle.
Each TASK-041 review created from the Timeline binds exact plan/revision/item/
Blueprint identity. Human decision and TASK-026 compilation fail closed after
any binding or Candidate drift. Unsupported stretch/crossfade/fade/gain remains
a visible feature gap and is never silently dropped.

Two Critic cycles close SRT dual-authority, duplicate placement truth,
ambience-role ambiguity, stale-review replay, partial multi-store mutation,
frame/ms drift, private narration leakage and paid/native overclaim risks with
unresolved Critical/High `0 / 0`. Exact Allowed Files exclude Desktop Shell/UI,
Provider adapters, credentials, generated-media writes, TASK-010/Resolve/Cubase
mutation, package/version, Tag, Release and Deploy.

P-V6-4 implementation remains `NOT_STARTED` until this exact design passes
hosted checks, merges to main, exact SHA and branch/clone cleanup are verified,
and fresh-main AUTONOMY selects the implementation unit. That hosted design
closure completes cadence merge `2 / 2` and returns control to AUTONOMY. Stable
release remains `v0.20.1`.

## Addendum LII — Major Refactor / Product Project Foundation Rebuild

P-V6-4 Design PR #61 merged at exact main
`6784a44e6831daa2b3db8ff85e2abe7b197ba3de`; its earlier `HOSTED_PENDING`
status is closed. The 2026-08-15 replacement Owner Directive
`AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE` supersedes earlier Owner cadence and
implementation-order instructions while preserving repository safety, Human
Authority and completed Evidence.

A zero-based current-main audit confirms that the Product has strong independent
domain stores, CAS/atomic writes and task-local recovery, but lacks one versioned
reopenable Product Project envelope, general child-format migration, coordinated
crash recovery, generic Undo/Redo, Autosave/Backup and durable Product
background/Export jobs. The released TASK-036 minimum Shell also does not yet
provide dynamic tracks, general clip seek, zoom/Fit/scroll, trim/snap/IN-OUT or a
durable Export Queue. Visible static UI is not capability Evidence.

The canonical dependency order is rebuilt as:

```text
TASK-043 Product Project / Migration / Recovery Foundation
    -> TASK-042 P-V6-4 Timeline Audio implementation
    -> TASK-044 Interactive Timeline / Unified NLE / Export Queue
    -> TASK-045 V6 Native Acceptance / Compatibility / Release Closure
    -> separate TASK-013 Native H3 re-evaluation
```

Addendum LII supersedes the post-P-V6-4 portion of this historical sequence by
inserting TASK-043 and splitting P-V6-5/6 into TASK-044/045. Completed history
and P-V6-4 design are not rewritten.

TASK-042 P-V6-1..3 and P-V6-4 design remain valid history. P-V6-5 is split into
TASK-044 and P-V6-6 into TASK-045 instead of being silently rewritten as already
complete. TASK-043 references existing domain truth by version/hash and creates
no second Candidate, Audit, LOCK/STALE, Prompt, Audio placement, Provider or
Generation Queue registry.

Two design Critic rounds close duplicate aggregate truth, destructive/in-place
migration, Evidence-erasing Undo, sensitive Autosave, duplicate Generation Queue,
child-save race, unknown external replay, restore overwrite and false UI/release
claim risks with unresolved Critical/High `0 / 0`. TASK-043 implementation is
authorized within its exact Allowed Files after hosted design closure. TASK-042
P-V6-4, TASK-044 and TASK-045 remain dependency-waiting and must be re-audited
against actual upstream Evidence.

Foundation-only checkpoints are not releases. Exact SemVer is decided from the
first meaningful integrated user-facing slice and compatibility/native Evidence.
Release and annotated Tag are Owner-authorized after required gates; Production
Deploy, paid Provider, new credential input, destructive migration and the
unknown-state Native H3 replay remain Human Gates. Stable release remains
`v0.20.1`.

## Addendum LIII — TASK-043 P-FND-1 Project Contract Implementation Gate

Roadmap/design PR #62 passed hosted `9 / 9` and merged at exact main
`b7500fa4f7cb4339ddde6aa4800d56c9bcb4d94e`; remote/local design branch cleanup
passed. A clean-main implementation branch then added the closed versioned
Product Project Manifest, exact child-store path/version/checksum bindings, atomic
CAS persistence, supported-format inspection and deterministic read-only migration
path/plan.

The Project contract embeds no domain payload, secret, media or execution
authority. It rejects traversal, drive/absolute paths, the reserved control
directory, case-colliding children, symlinks, checksum drift and unsupported newer
formats. Migration planning remains read-only and distinguishes lossless local
plans from Human-Gated or blocked paths; apply is absent.

WSL2 Python 3.12 compile/schema/smoke passes. Local pytest is unavailable without
changing the host; hosted full regression/compile/security is required before
closure. Implementation Critic unresolved Critical/High is `0 / 0`. P-FND-2 save
journal and crash recovery remain not started. No package version, Tag, Release,
Provider/native/media/Resolve/Cubase or Deploy operation is performed.

## Addendum LIV — TASK-043 P-FND-2 Coordinated Save/Recovery Gate

P-FND-1 PR #63 passed hosted `9 / 9`, merged at exact main
`e2930baa2cd66e92514e538e2834e89a8119d19f`, and completed branch cleanup. The
next clean-main unit adds Project-scoped save locking, deterministic transaction
identity, staged children/backups, source revalidation, child-first/manifest-last
commit and a checksummed recovery journal.

Failure injection proves typed COMPLETE and ROLLBACK before Manifest commit and
FINALIZE after Manifest commit. A pending transaction blocks a new save; binding
removal remains a migration/Human Gate; no external operation is replayed.
Transaction-scoped internal paths and exact target-child validation prevent a
tampered journal from redirecting recovery or falsely finalizing changed data.

Local compile/schema/failure-injection smoke passes and implementation Critic has
unresolved Critical/High `0 / 0`. Hosted full regression/compile/security remains
required. P-FND-3 Undo/Redo, Autosave and Backup retention is next. Stable release
remains `v0.20.1`; this foundation checkpoint creates no Tag or Release.

## Addendum LV — TASK-043 P-FND-3 History/Autosave/Backup Gate

P-FND-2 PR #64 passed all hosted `9 / 9` checks, merged at exact main
`3ba4df947ab2939ef7daed030a3ee69a3c31f07a`, and completed remote/local branch
cleanup. The next clean-main unit adds an append-only Project command history in
which Undo/Redo are new compensating records. History stores identities, Manifest
hashes and explicit STALE targets only; it stores no command payload, credential,
private Prompt body, external replay authority or Evidence-deletion authority.

Autosave uses the accepted coordinated save path only after bounded debounce and
quiescence gates, then retains bounded Manifest checkpoints. Backup creation
copies only checksum-bound Project children into a contained snapshot, validates
closed metadata and size/path bounds, and rotates an explicit bounded set. Restore
requires an exact previewed current Manifest checksum and creates a new revision
through the normal CAS save transaction; binding-set changes and newer-state
conflicts become Human review instead of destructive overwrite.

Focused TASK-043 tests pass `55 / 55`; full Windows Python 3.12 regression passes
`1042 passed, 1 skipped`; compileall passes. Critic findings for metadata/path/size
tamper boundaries are closed with unresolved Critical/High `0 / 0`. Hosted full
regression/security remains required. P-FND-4 durable Product jobs / Export Queue
foundation is next after hosted closure. Stable release remains `v0.20.1`; this
foundation checkpoint creates no Tag or Release.

## Addendum LVI — TASK-043 P-FND-4 Durable Product Job Gate

P-FND-3 PR #65 passed all hosted `9 / 9` checks, merged at exact main
`19febe3e00de92b18948e93740a0e3080b63d1b1`, and completed remote/local branch
cleanup. The final TASK-043 implementation unit adds closed, checksummed
`.bai-project/jobs.json` truth for Product-local background and Export work.
Operation identity is deterministic over allowlisted local kind, public target
identity and exact input hashes; repeated enqueue returns the existing record.

The CAS state machine covers QUEUED/PREFLIGHT/READY/DISPATCHING/RUNNING and typed
terminal/Human states. A restart while DISPATCHING or RUNNING produces UNKNOWN
with explicit reconcile actions and never returns to READY or dispatches again
automatically. UNKNOWN success requires externally proven result identity plus
the exact `ACCEPT_PROVEN_SUCCESS` action. Cost values remain nullable truth with
explicit currency/source when known; null is never rewritten as zero.

Job kinds are restricted to Product-local EXPORT/analysis/transcode/index/
maintenance work. The store explicitly states that it does not replace TASK-027
Generation Queue and does not authorize Provider, paid or external replay. Shell
`job.enqueue`, `job.cancel` and `job.reconcile` have explicit authority categories;
the durable-to-Shell projection is read-only and UNKNOWN becomes WAITING_HUMAN.

Focused P-FND-4/TASK-043/Shell tests pass `90 / 90`; full Windows Python 3.12
regression passes `1061 passed, 1 skipped`; compileall passes. Critic corrections
for cross-Project store substitution, Provider-job ownership and Shell authority
close with unresolved Critical/High `0 / 0`. Hosted CI remains required. After
hosted merge and cleanup, TASK-043 reaches hosted foundation closure and TASK-042
P-V6-4 implementation re-audit becomes next. Stable release remains `v0.20.1`;
this backend foundation checkpoint creates no Tag or Release.

## Addendum LVII — TASK-042 P-V6-4 Timeline Audio Implementation Gate

P-FND-4 PR #66 passed hosted `9 / 9`, merged at exact main
`10eae32b2e6a2f9ad7080961fed7b3d2b39f423b` and completed remote/local branch
cleanup. Fresh-main AUTONOMY selected
`BVP-TASK-042-P-V6-4-IMPLEMENTATION / IMPLEMENTATION` after re-auditing the
hosted Design against TASK-043.

The implementation establishes an append-only, frame-authoritative Timeline
Audio history for BGM, SE, NARRATION and AMBIENCE. SRT remains proposal-only and
reports deterministic frame conversion deltas and explicit Scene, Timeline and
narration-lane conflicts. Whole-Timeline music covers the exact Timeline, parallel
lanes are explicit, and crossfade overlap requires one transition group.

Timeline Audio is stored as a TASK-043 Product Project child. Plan and Project
Manifest commit together through coordinated save/recovery. Every command
revalidates Project identity, Manifest, timebase, Blueprint checksum, exact
TASK-037 SlotKind, locked Candidate and Asset checksum. An accepted TASK-041
placement may carry exact current Timeline proof into TASK-026; stale revisions
and unsupported STRETCH fail closed instead of silently changing output.

Focused Timeline/Audio compatibility tests pass `32 / 32`; full Windows Python
3.12 regression passes `1070 passed, 1 skipped`; compile validation passes.
Unresolved Critical/High findings are `0 / 0`. Hosted CI remains required before
P-V6-4 closure. This foundation unit adds no interactive NLE claim, Provider,
paid, native, media, TASK-010, Resolve or Cubase execution and creates no version,
Tag or Release. After hosted merge and cleanup, TASK-044 current-main audit/design
is next.

## Addendum LVIII — TASK-044 Practical NLE and Export Queue Design Gate

P-V6-4 PR #67 passed hosted `9 / 9`, merged at exact main
`19f1a94f11a783f475141af015351f64aff1b7d8` and completed remote branch and
dedicated checkout cleanup. TASK-043 and TASK-042 P-V6-4 prerequisites are now
hosted-closed. Fresh-main AUTONOMY selects TASK-044 design as the current maximum
runnable unit.

Current audit confirms that the Product has one Shell, static Timeline blocks,
Cut Candidate review, exact frame contracts, Timeline Audio, aggregate Project
save/recovery and durable Product jobs. It does not yet have dynamic track truth,
generic clip selection/seek separation, a shared frame viewport, trim/snap/IN-OUT,
a closed Export preparation contract, virtualized large-Timeline UI or complete
NLE keyboard/Narrator semantics.

Implementation is split into four hosted Atomic Units:

1. P-NLE-1 frame-authoritative semantic projection, interaction reducer and
   deterministic 10,000-item windowing;
2. P-NLE-2 trim/snap/IN-OUT and track edits through append-only Project history;
3. P-NLE-3 Project/Timeline/Assembly/preset-bound durable Export Queue with
   stale/UNKNOWN/no-replay recovery;
4. P-NLE-4 one existing Shell/UI integration and sandboxed Windows interaction
   acceptance.

Generic clip click selects; seek is a distinct ruler/lane/playhead command and
Cut Candidate click retains TASK-007 review meaning. Export enqueue grants no
external authority. Execute All iterates exact per-job authorization, durable
records contain no host output path, and interrupted external dispatch is UNKNOWN
without automatic replay. Provider/paid/new credential/Production Deploy remain
unauthorized. Version, Tag and Release remain TASK-045 ownership.

Two Critic cycles close two Critical and ten High findings with unresolved
Critical/High `0 / 0`. P-NLE-1 implementation becomes runnable only after this
design passes hosted checks, merges to main, exact SHA and branch/checkout cleanup
are verified, and a fresh main checkout reselects it.

## Addendum LIX — TASK-044 P-NLE-1 Timeline Projection Gate

TASK-044 Design PR #68 passed hosted `9 / 9`, merged at exact main
`f8b901c143f6a4987cacb46429cf0caf85aa2ab7` and completed remote branch and
dedicated checkout cleanup. Fresh-main AUTONOMY selected
`BVP-TASK-044-P-NLE-1 / IMPLEMENTATION`.

P-NLE-1 adds a transport-neutral frame-authoritative Timeline read model with
dynamic semantic tracks, exact source lineage, generic clip selection, distinct
Cut Candidate review identity and separate seek commands. One rational
pixels-per-second transform drives frame-to-pixel projection. Horizontal frame
and vertical track windows return deterministic pages capped at 2,000 clips; a
10,000-clip/two-hour-class fixture cannot become one unbounded DOM payload.

Released TASK-036 microsecond blocks adapt through explicit floor/ceil conversion,
and TASK-042 Audio Plan lanes adapt as dynamic audio tracks without becoming a
second truth. New Shell commands are read-only or local reversible. No trim,
Product-semantic edit, Project save, Export job, JavaScript UI, Provider, paid,
media, TASK-010, Resolve or Cubase mutation is included.

Focused P-NLE-1/TASK-036/TASK-042 compatibility passes `42 / 42`; full Windows
Python 3.12 regression passes `1083 passed, 1 skipped`. Critic closes selection,
seek, enum/frame validation, paging and compatibility risks with unresolved
Critical/High `0 / 0`. Hosted CI remains required. After merge and cleanup,
fresh-main P-NLE-2 semantic editing/history becomes next.

## Addendum LX — TASK-044 P-NLE-2 Timeline Edit and History Gate

P-NLE-1 PR #69 passed hosted `9 / 9`, merged at exact main
`ab41b2105914488d1d96ca3b3f8997a09d53337a`, and completed remote branch and
dedicated checkout cleanup. Fresh-main AUTONOMY selected
`BVP-TASK-044-P-NLE-2 / IMPLEMENTATION`.

P-NLE-2 adds exact-frame trim-start, trim-end and move proposals with deterministic
labeled snap candidates. Track add/remove is checked against exact topology;
required, missing and non-empty tracks fail closed. Every accepted semantic edit
appends a checksum-linked Timeline revision bound to the exact upstream Timeline
hash and commits its child state with the next Product Manifest through the
TASK-043 coordinated save path.

Undo and Redo append explicit inverse/replay Timeline revisions and compensating
TASK-043 Project command records; no prior record is rewritten. Because the
Project command store is deliberately outside the Manifest checksum graph, a
checksum-closed recovery intent bridges the post-Manifest finalization window.
Reopen completes only the exact expected result state, discards only an exact
uncommitted source state, and parks any third-state conflict for Human review.

Shell edit/track prepare operations are read-only and apply operations require
Human final authority. IN/OUT remains local reversible session state until a
future export/edit explicitly applies it. No Provider, paid, media, native,
TASK-010, Resolve, Cubase, Production Deploy, version, Tag or Release operation
is introduced.

Focused P-NLE-2/P-NLE-1/TASK-043 compatibility passes `50 / 50`; full Windows
Python 3.12 regression passes `1090 passed, 1 skipped`. Critic closes track
topology, strict frame typing, stale-CAS and split-finalization recovery risks with
unresolved Critical/High `0 / 0`. Hosted CI remains required. After merge and
cleanup, fresh-main P-NLE-3 durable Export Queue composition becomes next.

## Addendum LXI — TASK-044 P-NLE-3 Durable Export Queue Gate

P-NLE-2 PR #70 passed hosted `9 / 9`, merged at exact main
`a6bb252f36f4d3a8aca0175eb35c0ab44a7b91e8`, and completed remote branch and
dedicated checkout cleanup. Fresh-main AUTONOMY selected
`BVP-TASK-044-P-NLE-3 / IMPLEMENTATION`.

P-NLE-3 adds a checksum-closed Export preparation binding the exact Project
Manifest/product version, Timeline revision/hash, Edit/Assembly plan hashes,
preset and frame/audio output contract. Public and durable records carry only a
logical output identity. The launcher-private host destination exists only at
apply time and is never persisted.

TASK-043 durable jobs provide deterministic idempotent enqueue and CAS state.
Preflight revalidates all exact inputs; changed truth parks as reprepare-required.
Each job requires its own one-shot confirmation. DISPATCHING is durable before
the callback that can mutate Resolve/render state; restart becomes UNKNOWN and
never automatically replays. Success requires an exact result identity plus a
passing Render QA checksum. Execute All produces separate confirmation work
items and grants no blanket authority. Cancel remains limited to side-effect-free
states.

Focused P-NLE-3/TASK-043 tests pass `43 / 43`; full Windows Python 3.12 passes
`1097 passed, 1 skipped`; compileall and diff validation pass. Critic findings for
Windows path leakage, stale preflight, dispatch ordering, QA-unproven success and
blanket authority close with unresolved Critical/High `0 / 0`. No real external
execution or release operation occurred. Hosted CI remains required. After merge
and cleanup, fresh-main P-NLE-4 Shell/UI and sandboxed Windows acceptance becomes
next.

## Addendum LXII — TASK-044 P-NLE-4 Unified Shell and Native Acceptance Gate

P-NLE-3 PR #71 passed hosted `9 / 9`, merged at exact main
`c23083e6fa1f8513b14010ece1c2a92c51c47916`, and completed remote branch and
dedicated checkout cleanup. Fresh-main AUTONOMY selected
`BVP-TASK-044-P-NLE-4 / IMPLEMENTATION`.

P-NLE-4 composes the accepted frame-authoritative Timeline, append-only edit
history and durable Export Queue into the one existing TASK-036 Shell. Python
owns all durable and interaction truth. JavaScript receives at most 500 visible
clips and calls only typed bridge operations for selection, seek, Fit, IN/OUT,
trim prepare/apply and per-job Export decisions. Review Candidate styling and
selection remain distinct. No host path or blanket Execute All authority is
exposed.

The trusted launcher lazily derives the Timeline from its current editing
projection. Product Projects bind the TASK-044 edit and Export applications;
legacy projects remain read-only. UNKNOWN Export recovery requires an explicit
per-job Human action, and proven success additionally requires exact result and
passing Render QA identities. The rich controller graph is private to Python so
pywebview cannot expose it through recursive API discovery.

Focused Windows and WSL2 tests pass `60 / 60`; full Windows Python 3.12 passes
`1109 passed, 1 skipped`; full WSL2 Ubuntu passes `1110 / 1110`. Current-checkout
and final packaged Windows UI Automation confirm dynamic VIDEO/AUDIO/TEXT names,
keyboard seek, zoom/scroll, roving focus, bounded clip/track pages, narrow scroll
behavior and three-monitor movement. A READY/UNKNOWN sandbox confirms per-job
confirmation, safe cancel, typed recovery actions and zero Execute All buttons.
The final ignored one-dir EXE builds and launches with SHA-256
`BA96D3A5C06BC0CA299A24DDFA9EFA5048A212F345222E321B03013285EBC1A2`.

The in-app Browser adapter was unavailable and is not claimed as PASS. Direct
monitor-DPI querying stalled and is also not claimed; CSS dppx contracts,
mixed-monitor movement and packaged native behavior are the bounded Evidence.
Critic closes minimum-width, user-entered checksum, missing Export actions and
public controller exposure with unresolved Critical/High `0 / 0`. Hosted CI
remains required. After merge and cleanup, TASK-045 compatibility/native/release
audit and exact release decision becomes runnable.
