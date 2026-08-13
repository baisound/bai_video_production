# TASK-036 — Unified Desktop Editing Shell / Minimum Editing Workflow Integration
## Pre-implementation Detailed Design Ver.0.9

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / IMPLEMENTATION_DEPENDS_ON_R0_NATIVE_GATE`
- Priority: R1 immediately after `BACKEND_NATIVE_EDITING_MVP_PASS`
- Parent architecture: `PRODUCT-ARCH-001`
- Integration contract: `UNIFIED-APPLICATION-INTEGRATION-CONTRACT`
- Runtime implementation authorization created by this document: `NONE`
- Exit milestone: `MINIMUM_EDITING_PRODUCT_MVP_PASS`

## 1. Objective

Turn the already-separated editing backend capabilities into one normal-user Windows flow inside a single `BAI Video Production.exe` entrypoint:

`Open Project -> Media -> Transcribe -> Subtitle -> Cut Review -> Approve -> Resolve Apply -> QA -> EDITOR_WORK`.

The final acceptance route must not require PowerShell, command prompt, typed JSON, manual localhost startup, or browser URL entry.

## 2. Product boundary

TASK-036 does not reimplement TASK-006/007/010/011/012/022/024 business logic. It integrates their stable services into a desktop application shell and owns user-visible lifecycle/state/recovery.

Backend services remain independently testable and callable by diagnostic interfaces.

## 3. UI-first shell map

```text
BAI Video Production.exe
|
+-- Project / Home
|   +-- New Project
|   +-- Open Project
|   +-- Recent Projects
|   `-- Production Status
|
+-- Media
|   +-- Add Media
|   +-- Asset Summary
|   `-- Normalize / Proxy status
|
+-- Subtitle
|   +-- Transcribe
|   +-- Transcript status
|   +-- Subtitle Workspace
|   `-- SRT Import / Export
|
+-- Edit
|   +-- Cut Candidate Review
|   +-- Silence / Filler evidence
|   +-- CUT / KEEP decisions
|   +-- Timeline preview summary
|   `-- Final Plan Approval
|
+-- Review / QA
|   +-- Resolve Apply status
|   +-- Render status
|   +-- Structural QA
|   +-- Loudness QA
|   `-- Evidence summary
|
+-- Export / Handoff
|   +-- Render Master
|   +-- EDITOR_WORK
|   `-- Open containing folder
|
`-- Settings / Diagnostics
    +-- Provider settings
    +-- Resolve connection
    `-- Diagnostic interfaces
```

## 4. Workspace design

### 4.1 Global top bar

Always visible:

- current Project name;
- selected Media Asset;
- unsaved/review state;
- background job indicator;
- Resolve connection state;
- global notification/error entry;
- Settings.

Changing workspace must not lose Project/Asset/Plan context.

### 4.2 Left navigation

Primary flow order is reflected in navigation. Completed stages show a non-color-only state token (`Complete`, `Needs review`, `Blocked`, `Failed`).

A later stage may be inspectable while blocked, but mutation actions remain disabled with an explanation of the missing prerequisite.

### 4.3 Main content

Each workspace uses the same status language:

- `Not started`
- `Ready`
- `Running`
- `Needs review`
- `Approved`
- `Blocked`
- `Failed`
- `Complete`

No silent state transitions.

## 5. Project Context model

Shell state points to canonical identities, not repeated raw paths:

```text
ProjectContext
- project_id
- project_root
- selected_asset_id
- selected_asset_sha256
- transcript_id/hash
- subtitle_workspace_id/revision
- cut_candidate_manifest_sha256
- edit_plan_sha256
- resolve_assembly_sha256
- render_qa_report_sha256
- editor_handoff_manifest_sha256
- current_stage
- background_job_ids[]
```

Persisted shell state must be recoverable after app restart. Absolute host paths are stored only where project/path contracts explicitly require them and are never copied into general Evidence unnecessarily.

## 6. Primary user flow

### Step A — Open Project

- Native folder/file chooser.
- Validate Product project identity/version.
- Show recovery action when a project is stale/incomplete.
- Never create a second project implicitly because loading failed.

### Step B — Media

- `Add Media` opens native chooser.
- Reuse TASK-003 ingest/asset registry.
- Show filename, duration, stream summary and ingest result.
- User does not re-enter the same path in later workspaces.

### Step C — Transcribe

- Choose language/model/profile from settings-backed selectors.
- Show estimate/capability warning before model download.
- Start TASK-006/FasterWhisper worker.
- Running UI includes elapsed state and cancel/recovery semantics appropriate to the worker.
- Output binds to current Asset.

### Step D — Subtitle

- Existing Subtitle Workspace capability becomes a Shell workspace/subview.
- Native Open/Save remains available.
- AI typo-check enablement must not imply paid/network execution without its separate authorization.
- Save conflict/revision errors are user-visible.

### Step E — Cut Review

- Generate TASK-024 candidates.
- Present timeline/list view with reason, time range, confidence/strength and source evidence.
- Default state is review-only.
- Every candidate requires explicit `CUT` or `KEEP` before plan approval.
- Bulk actions, if later added, must remain explicit and reversible before approval.

### Step F — Approve Edit Plan

- Show projected retained duration and number of cuts.
- `Approve Edit Plan` is a separate human action.
- After approval, editing changes require creating a new plan/revision rather than silently mutating the approved identity.

### Step G — Resolve Apply

- Preflight: Resolve available, current target Project verified, source bindings valid, plan approved.
- UI explicitly displays the target Automation Timeline name.
- External-write button must be distinct from read-only connection check.
- TASK-010 idempotency result (`APPLIED` / `ALREADY_APPLIED`) is visible.
- Human-owned Timeline is never the implicit target.

### Step H — Render + QA

- Render is an explicit action after successful assembly.
- Show queued/running/completed/failed.
- TASK-011 report displayed as individual checks, not only one green/red badge.
- Loudness target/profile is visible.
- QA FAIL enables inspect/retry but not silent policy loosening.

### Step I — EDITOR_WORK

- Destination selected with native folder chooser.
- Prepare TASK-012 package only after QA PASS.
- Show final location and `Open folder` action.
- Cubase round-trip remains optional/bounded and does not claim automatic project conversion.

## 7. External-write confirmation model

Read-only actions require no destructive confirmation.

External mutations require stage-specific confirmation:

- Resolve assembly apply;
- Resolve render queue submit/start;
- handoff package creation if destination will be populated.

Confirmation shows:

- target application/project;
- target Automation Timeline;
- plan/report identity;
- affected destination;
- whether operation is idempotent/replay-safe.

No generic `Are you sure?` without target context.

## 8. Background worker lifecycle

Shell owns worker lifecycle:

```text
CREATED -> STARTING -> READY/RUNNING -> SUCCEEDED
                             |-> FAILED
                             |-> CANCELLING -> CANCELLED
                             `-> RECOVERY_REQUIRED
```

Requirements:

- helper ports/PIDs hidden from normal users;
- stale process detection;
- readiness timeout;
- structured ProductError mapping;
- app close prompts if unsafe work is active;
- restart recovery from durable project/checkpoint state.

## 9. Transitional localhost UI migration

Existing localhost Subtitle/Settings UI is not discarded.

Allowed migration strategies:

A. embed the existing UI inside Shell-owned WebView while Shell owns server lifecycle;
B. progressively port workspace UX to native widgets while retaining the same Application Service;
C. retain localhost server as diagnostic fallback only.

Toolkit selection is a separate implementation decision. It must be evaluated on Windows packaging, accessibility, focus/native dialogs, WebView availability, installer size, maintenance and license impact. This design does not silently add a large GUI dependency.

## 10. File UX

Normal workflow requirements:

- native Open/Save/Folder dialogs;
- remembered last valid project-relative location where safe;
- typed path field may exist for advanced users but cannot be the only route;
- cancelled dialog is not an error;
- native dialog must foreground correctly;
- Unicode and long Windows paths in acceptance tests.

## 11. Error UX

Every failure surface includes:

- human-readable summary;
- stable ProductError code in expandable details;
- affected stage;
- safe next action;
- retry eligibility;
- Evidence/report reference when available.

Examples:

- Resolve not running -> `Open Resolve / Retry connection`;
- wrong Resolve Project -> name both expected and observed, no mutation;
- QA loudness fail -> show measured/target values, do not auto-change profile;
- stale Project artifact -> offer inspect/rebuild route, not overwrite.

## 12. Recovery

App restart reconstructs stage state from canonical artifacts/checksums, not in-memory flags alone.

Recovery must distinguish:

- backend job never started;
- backend job completed but Shell closed;
- external mutation known complete;
- external mutation state unknown;
- evidence missing;
- artifact changed after approval/QA.

Unknown external state fails closed and requires inspection/status probe.

## 13. Accessibility / keyboard

- navigation and primary actions keyboard reachable;
- focus does not disappear into an embedded browser/native dialog;
- status is text/icon + color, never color only;
- destructive/external confirmation default focus is the safe/non-mutating action;
- long-running status is announced visually without modal blocking.

## 14. Packaging decision gate

Before implementation commit that introduces a GUI runtime, Builder must create a short ADR comparing at least:

- native-widget framework option;
- embedded-WebView option;
- packaging/installer path;
- Windows 11 compatibility;
- source distribution / license impact;
- binary size;
- testability;
- reuse of existing localhost workspaces.

Critic must challenge whether the selected toolkit increases complexity more than the shell MVP needs.

## 15. Service interfaces required from R0

TASK-036 should consume stable interfaces rather than CLI text:

- transcription service/job status;
- Subtitle Workspace load/save service;
- Cut Candidate generation;
- Edit Plan review/approval;
- Resolve assembly compile/execute;
- Render QA service + native render adapter;
- EDITOR_WORK prepare/verify.

CLI modules are not parsed as integration APIs.

## 16. Test strategy

### Unit

- Shell stage reducer/state machine;
- stage prerequisites;
- navigation gating;
- ProductError -> UX mapping;
- external-write confirmation payload;
- project context persistence/recovery.

### Integration

Use fake adapters to run:

`Open -> Ingest -> Transcript -> Subtitle -> Candidates -> Review -> Approve -> Resolve Apply -> QA -> Handoff`.

Pin failure/recovery at every boundary.

### Native Windows

Final acceptance must prove:

1. install/launch `BAI Video Production.exe`;
2. open project through native UI;
3. select media through native chooser;
4. complete transcription/subtitle/cut review;
5. approve plan;
6. apply to real Resolve sandbox;
7. real render + QA;
8. create EDITOR_WORK through native chooser;
9. close/reopen app and retain state;
10. no terminal/browser/manual localhost interaction used.

## 17. Completion semantics

- Design complete: `INTEGRATION_DESIGNED`
- Shell wired with automated integration tests: `SHELL_INTEGRATED`
- Windows full E2E PASS: `NATIVE_VALIDATED`
- Milestone after native E2E: `MINIMUM_EDITING_PRODUCT_MVP_PASS`

Backend R0 native validation alone must never be presented as TASK-036 completion.
