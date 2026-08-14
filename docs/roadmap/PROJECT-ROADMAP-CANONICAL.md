# AI動画制作自動化システム — Project Roadmap Canonical Ver.1.42
- Project: `ai-video-production`
- Date: 2026-08-14
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
- R4 current boundary: TASK-013 restart-safe execution control and exact local/free ComfyUI adapter are **HOSTED_CLOSED**; native H3 completion is **PARKED_TO_SAFE_RUNTIME_REVIEW**
- Current main: `7d6486059c468009042e4c186d54b566d6e1477e`; stable Product release remains `v0.20.1`; no active implementation branch

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
| 041 | Audio Workspace / Embedded Audio Separation & Placement UX | review/lock lanes and TASK-026 placement UX | 004,026 | DEV-3/4候補 | PROPOSED / NOT AUTHORIZED |

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
- TASK-041 Audio Workspace: **PROPOSED / NOT AUTHORIZED**

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
