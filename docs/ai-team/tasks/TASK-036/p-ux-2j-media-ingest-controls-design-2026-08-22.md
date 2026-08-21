# TASK-036 P-UX-2J media ingest controls design

Date: `2026-08-22`
Status: `IMPLEMENTED / VERIFIED / COMMIT_READY / DEV-2 STANDARD`
Atomic unit: `P-UX-2J_MEDIA_INGEST_CONTROLS_R0`

## 1. Goal

Connect the V6.1.1 Home `既存動画を編集する` action and File menu
`動画を読み込む...` action to the existing trusted
`choose_and_ingest_media` boundary. A user-selected local video becomes one
canonical TASK-003 Asset and the current Editing Session reads back its exact
Asset ID and SHA-256.

The existing native picker, TASK-003 ingest service, source-root policy,
content idempotency and single-source Editing Session stage remain the owners.
TASK-036 does not accept a JavaScript path or create another ingest/store
implementation.

## 2. Interaction contract

- Both visible media controls call one `chooseAndIngestMedia` function.
- The function re-reads `workflow_status` and proceeds only when the exact
  next action is `media.choose_and_ingest`.
- The native picker selection is the explicit user action. Picker cancel
  returns `CANCELLED`, creates no Asset and is projected as no-effect.
- The Python bridge converts its private workflow result to a closed envelope.
  A successful envelope contains only status, bounded logical Asset ID,
  lowercase canonical SHA-256 and explicit no-host-path metadata. The private
  receipt, Editing Session body, source filename and host path never cross into
  JavaScript.
- The entire bridge call is protected by the trusted launch operation lifetime.
  Close rejects new picker calls and waits for an admitted ingest before closing
  the Product store. Pre-Manifest launch keeps an in-process lifetime guard but
  creates no manifest-scoped OS lock file.
- Media choose-and-ingest is single-flight per trusted runtime. A competing
  Home/File/recommended-action call fails before opening another picker. Stage
  admission is checked before the picker and repeated by Shell dispatch after
  selection, so picker-time drift cannot reach the ingest port.
- After the source stage advances, both direct media controls are disabled
  with a truthful reason. The backend stage policy remains authoritative.
- The generic `次の工程` action uses the same function, so the direct and
  recommended paths cannot diverge.

## 3. Authority and effects

This unit exposes an already-existing local filesystem ingest effect only
after the user selects a file in the native picker. It grants no Provider,
paid, cloud, Audio, model download, Resolve, Export, publication, Release or
Deploy authority. It does not launch the Product or execute an ingest during
development verification.

## 4. Allowed scope

May modify:

- `src/ai_video_production/task036_shell_v611.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/desktop_media_workflow.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- direct V6.1.1, Shell, pre-edit, media-workflow and launcher tests
- this design document

The source scope expansion from the initial UI-only slice is the bounded closure
for independent Acceptance findings: transport privacy, launch-close lifetime
and parallel exact-one admission. It does not change TASK-003 ingest logic.

Must not modify TASK-003 ingest logic, Asset/Project schemas, Audio, Provider,
Resolve/Export, CHANGELOG, release files or user-owned `tmp/`.

## 5. Verification

- exact direct-button and recommended-action routing;
- current workflow admission and post-ingest disabled state;
- cancel/no-effect and safe Asset ID/SHA-only result projection markers;
- actual bridge response key closure with no filename/private receipt;
- parallel exact-one picker/ingest and picker-time stage drift rejection;
- after-close picker zero and in-flight close wait before Product store close;
- existing bridge/pre-edit/media-workflow tests;
- V6.1.1 interaction/visual and element contracts;
- embedded JavaScript syntax, Python compilation where changed, focused
  regression and `git diff --check`.

## 6. Completion boundary

The unit is complete when both mock-absolute media entry controls reach the
existing canonical ingest route and truthfully read back or reject the result.
Transcription, Cut Candidate generation, Timeline playback, Provider work and
Export remain separate subsequent stages.

## 7. Verification evidence

- Direct review-fix suite: 90 passed.
- Related TASK-003/TASK-036 regression: 188 passed.
- Changed Python modules: `py_compile` passed.
- `git diff --check`: passed; line-ending conversion warnings only.
- Independent Tester final direct/dependency audit: 202 passed, changed Python
  compilation and diff check passed, C/H/M/L 0/0/0/0.
- Independent Critic found transport privacy, launch lifetime and parallel
  admission gaps; the bounded fix was reapplied to the latest bytes.
- Critic re-Acceptance: PASS, C/H/M/L 0/0/0/0, no residual findings.
- No Product launch, native picker, real ingest, Provider, Resolve, Export,
  publication, release or deployment side effect was executed for this unit.
