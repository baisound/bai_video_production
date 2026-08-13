# AI動画制作自動化システム — Project Roadmap Canonical Ver.1.12
- Project: `ai-video-production`
- Date: 2026-08-13
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
- TASK-005,007以降の未着手TASK: **NOT_STARTED / NOT_AUTHORIZED**（個別にOwner認可する）
- TASK-006 Slice D: **v0.17.0 RELEASED** — resumable large-media transcription + Resolve subtitle handoff
- TASK-024 Slice A: **v0.18.0 RELEASED** — review-only silence/filler/disfluency Cut Candidate Worker
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
| 007 | Candidate Clip Graph / Cut Plan | DAG/score/target-duration Edit Plan。基本Cut統合sliceは006/024で先行可、Scene-aware完全版は005も利用 | 006,024; full版は005 | DEV-3 | IMPLEMENTED / AUTOMATED VALIDATED / INTEGRATION_DESIGNED |
| 008 | Multimodal Scoring | audio/visual/OCR feature fusion | 007 | DEV-3候補 | NOT STARTED |
| 009 | DBDProfilePlugin | DBD HUD/chase/event profile | 008 | DEV-3候補 | NOT STARTED |
| 010 | Resolve Assembly MVP | 元動画Cut、Subtitle Track/SRT配置、Audio asset配置を含むGateway/Controller, AUTO_ASSEMBLY, idempotency。字幕配置/basic assembly sliceは007前に先行可 | 002,003,022; Cut plan反映は007 | DEV-4 | IMPLEMENTED / NATIVE RESOLVE VALIDATION PENDING / INTEGRATION_DESIGNED |
| 011 | Render QA / Loudness | render queue adapter, QA, loudness/true-peak | 010 | DEV-3/4 | ARTIFACT QA IMPLEMENTED / NATIVE RENDER VALIDATION PENDING / INTEGRATION_DESIGNED |
| 012 | Manual Handoff / Cubase | EDITOR_WORK handoff, audio round-trip | 010,011 | DEV-3 | IMPLEMENTED / NATIVE HANDOFF VALIDATION PENDING / INTEGRATION_DESIGNED |
| 013 | AI SE / BGM / Video Orchestration | TASK-004 local-runtime基盤を利用したSE/BGM/Video生成のProvider選択・創作制御・rights/cost/evidence。内容連動選定は007依存 | 004; 007は内容連動時 | DEV-4候補 | NOT STARTED |
| 014 | Voice TTS / Owner Narration | ElevenLabsの既存Owner Voice Profile、read-only capability/ownership probe、timed TTS、dictionary、consent/retention、48 kHz canonical narration。ユーザー指定原稿からの生成は003後に前倒し可 | 003,028; 自動原稿生成は006/007; 配置は026 | DEV-4 | DESIGN RECORDED / ADAPTER FOUNDATION EXISTS |
| 015 | YouTube Feedback | performance ingest, feedback features | 008 | DEV-3候補 | NOT STARTED |
| 016 | Privacy Guard | PII/notification/NG detection + redaction plan | 003,006 | DEV-4 | NOT STARTED |
| 017 | Storage Lifecycle / GC | archive, retention, legal hold, staged delete | 003,018 | DEV-4 | NOT STARTED |
| 018 | Smart Reframe / Remotion | canonical reframe plan, vertical outputs | 007,010 | DEV-3/4候補 | NOT STARTED |
| 019 | Profile Auto-Tuner | holdout evaluation, rollback, promotion gate | 008,015 | DEV-3/4候補 | NOT STARTED |
| 020 | Resource Admission / Monitoring | VRAM/CPU/disk/network admission + metrics | 001,004 | DEV-4候補 | NOT STARTED |
| 021 | Integrated Dashboard / Operations | job/evidence/alerts/ops UI | Evidence contracts | DEV-3候補 | NOT STARTED |
| 022 | Timeline Mapping Service | exact frame/time mapping, schema, golden fixtures | 001,003,004 | DEV-4 | IMPLEMENTED / WINDOWS REGRESSION PENDING |
| 023 | FasterWhisper Fast Local Provider | local ASR provider/cache/evidence | 001,004,006 | DEV-3候補 | COMPLETE |
| 024 | Silence / Filler / Disfluency Cut Candidate Worker | 無音、フィラー、言い直し、反復、長ポーズ、噛み候補、keep blocks、cut evidence | 003,004,022; ASR連動は006 | DEV-3 | RELEASED v0.18.0 |
| 025 | Premiere FCP7 XML Adapter Spike | XML adapter, import report, frame-rate matrix | 001,022 | DEV-3候補 | NOT STARTED |
| 026 | Audio Placement & Bed Worker | SE/BGM/ナレーション placement plan、bounded snap、loop/fade、preview/full BGM bed、Resolve audio-track placement plan | 002,003,022; 013/014は生成asset利用時; 007は内容連動時 | DEV-3/4候補 | NOT STARTED |
| 027 | AI Video Creation Studio / New Production Orchestrator | GUI入力、AI制作設計提案・補正、GO承認、画像/動画/SE/BGM/ナレーション生成、Asset差し替え、Resolve自動配置 | 001-004; Slice Aは先行可、完全版は010,013,014,022,026 | DEV-4候補 | SLICE A1 PRODUCTION BLUEPRINT FOUNDATION IMPLEMENTED |
| 035 | REAPER Audio Finishing Bridge / DaVinci Round-trip | deterministic DAW Session Plan、track/route/FX/render、iZotope capability probe、mix/stem QA、Resolve再配置 | 003,010,011,022,026 | DEV-4候補 | PROPOSED / DESIGN RECORDED |

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
- TASK-035 REAPER Audio Finishing Bridgeはこの時点から任意導入可能。Technical MVPを阻害せず、音響仕上げとResolve round-tripを高度化する

ここを最初の明確な**「動画を投入して、Cut済み・字幕付きの自動編集Timelineを得る」完成点**とする。

### Wave 4 — 音声演出を前倒し

- TASK-013 SE/BGM/Video orchestration（TASK-004で生成Runtime基盤は先行済み。TASK-007完了を待たず、ユーザー指定Prompt/Assetによる生成sliceは前倒し可）
- TASK-014 ElevenLabs Owner Voice narration（既存の本人学習済み音声を利用。read-only probe→有料Preview→timed full render→48 kHz Assetの順で前倒し可）
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
