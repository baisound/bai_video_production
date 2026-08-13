# TASK-036 — Unified Desktop Editing Shell
# UI Layout / Visual Interaction Contract Ver.1.0

- Date: 2026-08-13
- Status: `OWNER_VISUAL_DIRECTION_RECORDED / DESIGN_AHEAD`
- Owner visual direction: **Vrew × Adobe Premiere Pro × DaVinci Resolve 系のプロ動画編集UI**
- Product: `BAI Video Production.exe`
- Applies to: TASK-036 and all later user-facing editing workspaces
- Important: 既存製品の商標・アイコン・アセットを複製する設計ではなく、NLEとして確立された情報設計・操作パターンを採用する。

---

## 1. Owner Direction

BAI Video Production のDesktop UIは、一般的なWeb管理画面やAIチャット画面を主役にしない。

基準イメージは以下。

1. **Vrew**
   - 文字起こし / 字幕 / セリフ単位で編集対象を追いやすい。
   - 非専門家でも理解しやすい。
   - AI処理を動画編集UIの中へ自然に埋め込む。
2. **Adobe Premiere Pro**
   - Project / Source / Program / Timeline / Inspector系のプロNLE情報構造。
   - ドッキングされた複数Panel。
   - Timelineを編集作業の中心として扱う。
3. **DaVinci Resolve**
   - Dark professional UI。
   - Workspace/Page概念。
   - Viewer、Media/Effects、Inspector、Timelineの明確な役割分担。
   - 編集・字幕・音・Deliveryまで同一Application内で連続する。

最終デザインは「Vrewをそのままコピー」でも「Premiere/Resolveクローン」でもない。

**BAI独自のAI-native NLE** として、これらの強い操作パターンを統合する。

---

## 2. Canonical Window Layout

基本レイアウトは4領域 + Top Navigationとする。

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ App Menu / Project / Workspace Tabs / Job Status / Export                  │
├───────────────┬───────────────────────────────────────┬─────────────────────┤
│               │                                       │                     │
│ LEFT PANEL    │            CENTER VIEWER              │    RIGHT PANEL      │
│               │                                       │                     │
│ Project/Media │          Program / Preview            │ Inspector / AI      │
│ Transcript    │                                       │ Properties / QA     │
│ Subtitle      │                                       │                     │
│ Assets        │                                       │                     │
│               │                                       │                     │
├───────────────┴───────────────────────────────────────┴─────────────────────┤
│                                                                             │
│                              TIMELINE                                       │
│ Track Headers | Ruler | Playhead | Video / Subtitle / Audio / BGM / SE      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Priority

画面占有優先順位:

1. Timeline
2. Viewer
3. Current task side panel
4. Auxiliary browser/panel
5. AI detail/log

AIチャットやAgent LogがViewer/Timelineを押しのけて主役になってはならない。

---

## 3. Top Application Bar

含める:

- App identity: `BAI Video Production`
- Current Project
- Save state / autosave state
- Undo / Redo
- Workspace/Page selector
- Background jobs indicator
- Provider/connection health indicator
- Review/approval pending indicator
- Export button
- Global Settings

推奨Workspace:

```text
Project
Media
Edit
Subtitle
Audio
Generative AI
Review
Export
External Integration
```

ただしTASK-036 Minimum Editing MVPでは最初から全Workspaceを有効化しない。

MVP Active:

```text
Project
Media
Edit
Subtitle
Review
Export
```

Future workspaceは disabled/hidden contractで扱う。

---

## 4. Left Panel

Left PanelはVrew的な「素材/文字ベース編集の分かりやすさ」とNLEのProject Binを統合する。

### 4.1 Tabs

- Project
- Media
- Transcript
- Subtitle
- Edit Candidates
- Assets

### 4.2 Project / Media

表示:

- folder/tree
- imported source
- proxies
- generated derivatives
- duration
- resolution
- frame rate
- audio presence
- status badge

Drag & Drop可能。

Native file/folder pickerを必須とする。
typed-path-onlyを通常UXにしない。

### 4.3 Transcript

Vrew型の重要領域。

- セグメント単位の文字起こし
- timecode
- speaker
- confidence
- silence/filler candidate
- cut/keep state
- subtitle state
- search

Transcript row click:
→ Viewer seek
→ Timeline playhead sync
→ corresponding clip/segment select

### 4.4 Edit Candidates

TASK-024 / TASK-007との接続。

表示例:

```text
[KEEP] 00:00:12.000 - 00:00:18.100
[CUT ] 00:00:18.100 - 00:00:19.300  Silence
[CUT?] 00:00:24.200 - 00:00:26.000  Filler
```

Human Final AuthorityをUI上で明確にする。

AI候補とHuman確定を視覚的に区別するが、色だけには依存しない。

---

## 5. Center Viewer

ViewerはPremiere/Resolve型。

### Must Have

- Current frame
- playback
- play/pause
- step frame forward/back
- timecode
- current/total duration
- viewer zoom
- fit
- safe area optional
- subtitle overlay
- selected edit range visualization
- audio mute toggle

### Timeline Sync

Viewer、Transcript、Timelineは同じPlayheadを共有。

どこか1つを操作すると全領域が同期する。

### Before / After

Review Workspaceでは:

- Source
- Edited
- Optional split view

を切替可能。

---

## 6. Right Panel — Inspector / AI / QA

Premiere/ResolveのInspector構造を採用。

### 6.1 Context Sensitive

何を選択したかで内容を変える。

Video clip:
- asset info
- trim range
- speed
- transform (future)
- linked audio state

Subtitle:
- text
- start/end
- style
- review status

Audio:
- gain
- track
- loudness/QA status

Generated asset:
- provider
- model
- generation status
- candidate/locked state
- evidence shortcut

### 6.2 AI Panel

AIは独立チャットを主役にしない。

Inspector内で、

```text
Suggestion
Reason
Confidence
Impact
Accept
Reject
Regenerate / Re-analyze
```

を構造化表示。

### 6.3 QA

TASK-011:

- Render status
- duration check
- video stream
- audio stream
- LUFS
- true peak
- PASS / FAIL
- Evidence ID

絶対パスを通常UIへ露出しすぎない。

---

## 7. Timeline — Product Core Surface

TimelineはBAI Video Productionの主要操作面。

### 7.1 Track Order MVP

推奨:

```text
V1  Source / Main Video
S1  Subtitle
A1  Linked Source Audio
A2  Narration
A3  SE
A4  BGM
```

MVPで未対応Trackは表示を簡略化またはdisabled。

### 7.2 Timeline Must Have

- horizontal ruler
- exact playhead
- zoom in/out
- scroll
- track headers
- video clips
- audio waveforms
- subtitle blocks
- selected segment
- CUT candidate overlays
- KEEP ranges
- snap
- linked A/V indication
- lock/mute/solo where applicable
- clip labels
- current timecode

### 7.3 Edit Plan Overlay

TASK-007 Cut PlanをTimeline上へ表示。

状態:

- AI Candidate
- Human KEEP
- Human CUT
- Review required
- Applied to Resolve
- Stale

Apply前とApply後を区別する。

---

## 8. Workspace Modes

### 8.1 Media

```text
Left: Project/Media
Center: Source Viewer
Right: Asset Inspector
Bottom: optional compact timeline / metadata
```

### 8.2 Edit

```text
Left: Transcript / Candidates
Center: Program Viewer
Right: Inspector / AI suggestion
Bottom: Full Timeline
```

TASK-036の最重要Workspace。

### 8.3 Subtitle

```text
Left: Subtitle list
Center: Viewer with subtitle
Right: Text/Style/Review Inspector
Bottom: Timeline
```

### 8.4 Review

```text
Left: QA / Findings
Center: Edited preview / Before-After
Right: Render QA + Evidence
Bottom: Timeline read/review
```

### 8.5 Export

Premiere/Resolve Deliver Pageの考え方。

- preset
- target path picker
- file name
- codec/container
- frame rate
- audio
- estimated output
- render status
- QA result

Export mutationは明示実行。

---

## 9. Visual Style

### 9.1 Overall

- Dark professional theme
- low-glare
- flat panels
- subtle separators
- high information density
- no excessive cards
- no giant rounded SaaS dashboard blocks
- no marketing-style gradients as primary editing surface

### 9.2 Density

Professional modeを標準。

Target:

- 1080p displayでViewer + usable timeline + 2 side panelsが同時表示可能。
- 1440p/4Kではadditional panel/detailを活用。

### 9.3 Accent

Accent colorは状態/selection用。
大量の虹色装飾をしない。

StateはIcon/Text/shape併用。

### 9.4 Typography

- UI: compact sans-serif
- Timecode: tabular/monospace-compatible digits
- Transcript: readable Japanese
- small metadata: high contrast minimum

---

## 10. Panel Behavior

すべての主要Panelはresizable。

### MVP

- Left width resizable
- Right width resizable
- Timeline height resizable
- Viewer auto fit
- collapse left/right
- restore default layout

### Later

- docking
- floating panel
- custom workspace save

TASK-036 MVPで完全なPremiere級Docking Systemを作らない。
Minimum Editing Workflowを優先する。

---

## 11. Canonical Minimum Screen Sizes

Initial target:

```text
Minimum supported: 1366 × 768
Recommended:       1920 × 1080
Professional:      2560 × 1440+
```

1366×768では:

- either side panel collapsible
- bottom timeline minimum usable height
- critical action remains visible

UI要件を満たせない場合はhorizontal/vertical scrollで誤魔化さず、panel collapseを使う。

---

## 12. Keyboard / Professional Editing UX

MVP candidates:

- Space: Play/Pause
- Left/Right: frame/seek depending focus
- Ctrl+S: Save
- Ctrl+Z / Ctrl+Shift+Z: Undo/Redo
- +/-: Timeline zoom
- Home: timeline start
- End: timeline end
- Delete: only selected locally-owned edit object; confirmation/rules by ownership
- J/K/L: later professional playback candidate

Text editing focus中にGlobal Shortcutを誤発火させない。

---

## 13. Human Authority UX

重要。

AIが編集を提案していても:

```text
AI Suggestion
≠
Approved Edit
≠
Applied Resolve Timeline
≠
Rendered Artifact
≠
Released Output
```

これらの状態をUI上で別々に表示する。

Apply/Render/Exportなど外部Mutation前は、

- target
- affected timeline/project
- changes
- Evidence identity
- authority state

を確認可能にする。

---

## 14. Background Jobs

ASR、analysis、render等はUIをブロックしない。

Job Center:

- queued
- running
- waiting human
- failed
- completed

Cancel:
External mutation前なら安全にcancel。
Mutation後unknown stateなら勝手にRetryせずinspection required。

---

## 15. Error UX

ErrorはToastだけで終わらせない。

必須:

- short human explanation
- error code
- affected stage
- retry allowed?
- recovery action
- Evidence shortcut

例:

```text
Render could not be confirmed.
ERR_TASK011_NATIVE_RENDER_STATUS_INVALID

Resolve may have already received the job.
Automatic retry has been stopped to prevent duplicate rendering.

[Inspect Resolve] [Open Evidence] [Dismiss]
```

---

## 16. UI Architecture Boundary

UIから直接:

- Git
- Resolve scripting
- ffmpeg
- Provider API
- Database

を呼ばない。

```text
UI
 ↓
Shell/Application Service
 ↓
Capability/Use Case
 ↓
Authority/Safety
 ↓
Backend Adapter
```

TASK-036は既存Backend CapabilityをShellへ統合する。

---

## 17. TASK-036 Minimum Editing E2E

Canonical user flow:

```text
Open Project
→ Import Media
→ Transcribe
→ Review Transcript
→ Subtitle
→ Detect Silence/Filler
→ Review Cut Candidates
→ Approve Edit Plan
→ Apply to Resolve
→ Preview / QA
→ Render
→ EDITOR_WORK Handoff
```

Normal user acceptance routeでPowerShell/JSONを要求しない。

---

## 18. Native Acceptance — UI

Windows実機で必須:

- one application entrypoint
- real file picker
- real folder picker
- Japanese path
- long path where supported
- 1366×768
- 1920×1080
- 150% Windows display scaling
- keyboard navigation
- focus recovery after native dialog
- panel resizing
- timeline horizontal scroll
- transcript/timeline/viewer sync
- error recovery
- background task progress
- Resolve mutation confirmation
- native render gate integration
- external app handoff

---

## 19. Anti-patterns

禁止:

- AI chat windowを画面中央の主役にする。
- Timelineを小さな補助Widget扱いする。
- SaaS Dashboard風カードを大量配置する。
- 各機能が別Window/別localhost UIになる。
- Import/Exportをtyped pathだけで済ませる。
- UI設計なしでbackend機能をボタン化する。
- Errorをconsoleだけに出す。
- colorだけでCUT/KEEP状態を区別する。
- Apply/Render/Exportの状態を同一「完了」で表現する。
- Premiere/Resolve級の全機能DockingをMVPで作って本質を遅らせる。

---

## 20. Design Priority

TASK-036 implementation priority:

```text
P0  One-window shell
P0  Edit workspace canonical layout
P0  Timeline
P0  Viewer
P0  Transcript/Cut review
P0  Inspector
P0  Native file/folder UX
P0  Backend workflow integration

P1  Subtitle specialized workspace
P1  Review/QA workspace
P1  Export page

P2  advanced docking
P2  custom layouts
P2  multi-monitor
```

---

## 21. Owner Acceptance Visual Test

Owner should be able to look at the app and immediately say:

> 「これは動画編集ソフトだ」

before reading any documentation.

Additional acceptance:

- Vrew的に文字/字幕から編集へ入れる。
- Premiere/Resolve的にTimeline/Viewer/Inspectorが自然に存在する。
- AIは編集を補助するが画面構造を支配しない。
- Backend capabilityの寄せ集めではなく1つの編集Applicationとして見える。

---

## 22. Status

This contract is now a TASK-036 visual design authority input.

It does not authorize TASK-036 runtime implementation before the existing R0 native backend gate is closed unless Owner separately changes that dependency.

Status:

`OWNER_VISUAL_DIRECTION_RECORDED`
`TASK036_UI_CONTRACT_READY`
