# PRODUCT-ARCH-001 — Unified Desktop Application Architecture Ver.1.0

- Product: `BAI Video Production`
- Date: `2026-08-12`
- Status: `CANONICAL_PRODUCT_ARCHITECTURE_CONTRACT`
- Scope: Cross-cutting / all Product TASKs
- Runtime implementation authorization created by this document: `NONE`
- Package version change: `NONE`
- Canonical invariants:
  - `STANDALONE_APPLICATION_REQUIRED`
  - `UNIFIED_DESKTOP_APPLICATION_REQUIRED`
  - `SINGLE_USER_FACING_ENTRYPOINT_REQUIRED`
  - `CAPABILITY_UI_INTEGRATION_REQUIRED`

## 1. Product Goal

BAI Video Production の最終Productは、機能ごとに独立したツールを並べた集合体ではない。

最終形は、ユーザーが **BAI Video Production.exe** を1つ起動し、Project、Media、Edit、Subtitle、Audio、Generative AI、Review、QA、Export、External NLE Integration を横断して扱う統合デスクトップアプリケーションである。

各TASKで実装される Service、Worker、Provider、CLI、localhost Web UI は、機能を安全に独立検証するための内部Capabilityまたは開発・診断Interfaceであり、それ自体を最終ユーザー体験としてはならない。

## 2. 「1つのEXE」の定義

`SINGLE_USER_FACING_ENTRYPOINT_REQUIRED` は「OS processが必ず1個だけ」という意味ではない。

許可される内部構成:

- managed background worker;
- local helper process;
- media worker;
- AI runtime process;
- local HTTP service;
- embedded WebView;
- GPU worker;
- external NLE adapter process.

ただし、ユーザーから見た起動・終了・状態監視・復旧・設定は **BAI Video Production.exe** が所有する。

最終ユーザーに以下を要求してはならない。

- PowerShell / cmd から通常機能を起動する;
- localhost server を別途手動起動する;
- browser URL を手入力する;
- worker process を手動管理する;
- featureごとに別アプリを探して起動する;
- internal port / PID / Python environment を通常操作で意識する.

## 3. Target Product Shell

```text
BAI Video Production.exe
|
+-- Project / Home
|   +-- New / Open / Recent
|   +-- Project Settings
|   `-- Production Status
|
+-- Media
|   +-- Ingest
|   +-- Normalize / Proxy
|   `-- Asset Browser
|
+-- Edit
|   +-- Timeline / Edit Plan
|   +-- Cut Candidates
|   +-- Silence / Filler Review
|   `-- Human Approval
|
+-- Subtitle
|   +-- Transcription
|   +-- Subtitle Workspace
|   +-- SRT Import / Export
|   `-- Timeline Placement
|
+-- Audio
|   +-- BGM
|   +-- SE / Foley
|   +-- Narration / TTS
|   `-- Audio Placement
|
+-- Generative AI
|   +-- Image
|   +-- Video
|   +-- Voice
|   `-- Provider / Model Settings
|
+-- Review / QA
|   +-- Validation
|   +-- Evidence
|   `-- Approval
|
+-- Export / Render
|
`-- External Integration
    +-- DaVinci Resolve
    +-- Adobe Premiere Pro
    `-- Adobe After Effects
```

DaVinci Resolve / Premiere Pro / After Effects は統合Targetであり、現在すべてが実装済みという意味ではない。各adapterの実装状態は個別TASKが決定する。

## 4. Architectural Layers

### 4.1 Desktop Application Shell

Responsibilities:

- single user-facing launch;
- project selection;
- global navigation;
- workspace layout;
- application lifecycle;
- helper-service lifecycle;
- global notifications;
- progress/status;
- crash/recovery entry;
- settings;
- update/diagnostics entry;
- cross-feature context.

### 4.2 Workspace Layer

Capabilityをユーザーの作業文脈へ編成する。

Examples:

- Edit Workspace
- Subtitle Workspace
- Audio Workspace
- Generative Workspace
- Review Workspace
- Export Workspace

Workspaceは独立アプリではなく、同じProduct Shell内の画面/領域である。

### 4.3 Application Service Layer

Cross-feature orchestration:

- current Project;
- current ProductionJob;
- selected Asset;
- current Timeline/Edit Plan;
- background job state;
- review/approval state;
- external NLE connection state.

### 4.4 Capability Service Layer

既存TASKのHeadless Serviceを保持する。

Examples:

- FasterWhisper Provider
- Resumable Transcription
- Cut Candidate Worker
- Timeline Mapping
- Asset Registry
- Generation Provider
- QA Worker

この層は単体テスト可能でなければならない。

### 4.5 Adapter Layer

External integration:

- DaVinci Resolve
- Premiere Pro
- After Effects
- FFmpeg
- local/cloud AI providers
- OS-native file/dialog integration

Adapter failureはShellへ構造化エラーとして返し、silent failureにしない。

## 5. Transitional Interfaces

既存の以下は、完成Product UXではなく `TRANSITIONAL_INTERNAL_UI` または `DEVELOPER_DIAGNOSTIC_INTERFACE` として扱う。

- standalone CLI commands;
- loopback / localhost browser UI;
- developer evidence commands;
- direct JSON plan generation;
- internal worker scripts.

これらを削除する必要はない。テスト、automation、diagnostics、support用途として残せる。

ただし、end-user workflowとして必要なCapabilityはProduct completionまでに統合Shellから到達可能でなければならない。

## 6. Capability Integration Status

User-facing Capabilityは以下のintegration stateを持つ。

- `BACKEND_CAPABILITY_ONLY`
- `INTEGRATION_DESIGNED`
- `SHELL_INTEGRATED`
- `NATIVE_VALIDATED`

Task単体でBackendが完成しても `SHELL_INTEGRATED` ではない。

Release note / Current State では、Backend capability completionとUnified App integration completionを混同してはならない。

## 7. Mandatory Detailed Design Section

今後、User-facingまたはOperator-facing機能の詳細設計には必ず `Unified Application Integration` セクションを設ける。

最低限:

1. `User Entry Point`
2. `Shell / Workspace Location`
3. `Primary User Flow`
4. `Project / Asset / Timeline Context`
5. `Progress / Running / Success / Failure State`
6. `Human Review / Approval`
7. `File Open / Save / Import / Export UX`
8. `Settings / Provider Configuration`
9. `Background Worker Lifecycle`
10. `Error / Recovery UX`
11. `External NLE Interaction`
12. `Keyboard / Accessibility / Focus considerations` where applicable
13. `Native Windows Acceptance`
14. `CLI / localhost fallback role`
15. `Integration State on Task Exit`

UIを伴わない内部Taskは `NOT_USER_FACING` と理由を明記してよい。

## 8. UI-First Design Rule

User-facing Taskでは実装前に最低限の画面導線を決める。

「Backendを先に作り、後で画面へ繋ぐ」こと自体は許容されるが、詳細設計時点で最終Shellへの接続点を未定のままにしてはならない。

Criticは以下を必ず問う。

- ユーザーはどこから機能を開始するか。
- source / destination はファイル選択可能か。
- typed pathだけを要求していないか。
- running / completed / failed が見えるか。
- cancel / retry / recovery が必要か。
- feature間で同じProject/Assetを再選択させていないか。
- browser / terminalを通常操作へ漏らしていないか。
- native dialog focus/foregroundが成立するか。
- destructive/external write前に適切なapprovalがあるか。

## 9. Project-Centric Cross-Feature Context

統合ProductではCapability間でProject contextを引き継ぐ。

例:

```text
Project
 -> Media Asset
 -> Transcript
 -> Cut Candidates
 -> Edit Plan
 -> Subtitle Review
 -> Audio Assets
 -> Generative Assets
 -> Timeline Assembly
 -> QA
 -> Export
```

ユーザーに同じmedia pathやAssetを各機能で毎回入力させる構造を最終UXとしては採用しない。

Canonical identity / checksum / Project state を内部で引き継ぐ。

## 10. External NLE Policy

BAI Video Productionは、DaVinci Resolve / Premiere Pro / After Effectsの全機能を再実装することを必須目標としない。

Productは以下を統合Shellから扱えることを目標とする。

- connection / capability check;
- project/timeline handoff;
- approved plan execution;
- import/export;
- status/result;
- actionable errors;
- safe retry;
- provenance/evidence.

NLE固有の高度な編集・grading・compositingは外部アプリ側へ委譲してよい。

## 11. Internal Service Lifecycle

Shell-integrated local servicesはApplication lifecycleの一部として管理する。

- start;
- readiness check;
- health;
- reconnect;
- stop;
- stale-process handling;
- port conflict handling;
- user-visible failure.

「localhostへ接続できないのでボタンが反応しない」は完成UXとして禁止する。

## 12. Packaging Boundary

最終distributionは一つのBAI Video Production製品として提供する。

Installer/runtime内部に複数componentが含まれてもよいが、Productとして:

- one install concept;
- one primary application entry;
- one project model;
- one settings surface;
- one update concept;
- one diagnostics entry;
- one uninstall concept;

を維持する。

## 13. Migration of Existing Capabilities

既存機能は削除せず、段階的にShellへ統合する。

### Subtitle Workspace

Current localhost/browser functionality is a working capability. Future integration shall place it in the unified Subtitle Workspace and preserve:

- native Open/Save;
- cue review;
- disconnected-server feedback;
- explicit approval behavior.

### FasterWhisper / TASK-023

CLI/evidence interfaces remain diagnostic. Final transcription initiation/status/review belongs in Subtitle Workspace.

### Cut Candidates / TASK-024

Worker/CLI remains headless engine. Final operator workflow belongs in Edit Workspace with review-only candidate visualization and approval.

### Generative AI

Provider settings and generation jobs belong in unified Generative / Settings surfaces, while Provider adapters remain headless/testable.

## 14. Release and Completion Semantics

A Task may release a Backend capability before Shell integration if dependency/order requires it.

However:

- docs must mark `BACKEND_CAPABILITY_ONLY` or equivalent;
- it must name the planned Shell integration point;
- Product-wide “feature complete” must not be claimed until `SHELL_INTEGRATED`;
- final desktop acceptance requires `NATIVE_VALIDATED`.

## 15. Architecture Safety Floor

The following are non-negotiable:

1. `STANDALONE_APPLICATION_REQUIRED`
2. `UNIFIED_DESKTOP_APPLICATION_REQUIRED`
3. `SINGLE_USER_FACING_ENTRYPOINT_REQUIRED`
4. `CAPABILITY_UI_INTEGRATION_REQUIRED`
5. Headless services remain testable.
6. CLI / localhost UI may remain diagnostic but not be the only final workflow.
7. External applications are optional adapters, not required to start the core Product.
8. Shell owns local helper lifecycle.
9. User-facing errors are actionable and visible.
10. Detailed design must include integration before user-facing implementation begins.

## 16. Critic Findings

### C-UDA-001 — “one EXE” could be interpreted as one OS process
Resolved. One **user-facing entrypoint** is required; managed helper processes are allowed.

### C-UDA-002 — Unified UI could destroy modular/testable architecture
Resolved. Capability services remain headless and independently testable behind the Shell.

### C-UDA-003 — Existing CLI/Web UI could be mistaken for final Product UX
Resolved. They are explicitly classified as transitional/diagnostic interfaces.

### C-UDA-004 — Forcing all UI integration immediately could stall editing-first development
Resolved. Backend capability releases remain allowed, but integration state must be explicit and integration design is mandatory.

### C-UDA-005 — External NLE integration could accidentally make Product non-standalone
Resolved. External NLEs are adapters; core Product launch and primary internal workflows remain standalone.

## 17. Judge Decision

`PASS FOR CANONICAL ARCHITECTURE REGISTRATION`

This documentation change creates a cross-cutting Product invariant. It does not implement the desktop Shell itself and does not allocate a new Product TASK number.

All future relevant Task designs must comply.
