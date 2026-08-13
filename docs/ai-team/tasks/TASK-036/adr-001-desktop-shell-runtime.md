# ADR-036-001 — Desktop Shell Runtime for Minimum Editing MVP

- Date: 2026-08-13
- Status: `ACCEPTED_FOR_IMPLEMENTATION_PREPARATION / R0_NATIVE_GATE_REQUIRED_BEFORE_PRODUCT_WIRING`
- Owner task: `TASK-036`
- Parent: `PRODUCT-ARCH-001 Unified Desktop Application`
- Milestone: `MINIMUM_EDITING_PRODUCT_MVP_PASS`
- Runtime implementation authorization created by this ADR: `NONE`
- Decision scope: Windows desktop shell runtime / UI hosting / packaging direction

## 1. Decision

For the first TASK-036 Minimum Editing Product MVP, use a **single Windows desktop shell that hosts the existing HTML/CSS/JavaScript workspaces in an embedded native WebView** and invokes Python Application Services directly through a bounded bridge.

The preferred implementation candidate is:

`Python product process -> pywebview native window -> Windows EdgeChromium/WebView2 renderer -> Shell-owned UI -> Application Service bridge`.

This is a **preferred architecture decision, not permission to add the dependency yet**. Before the first implementation commit, Builder must execute the Windows packaging/runtime spike defined in this ADR and Critic must accept the Evidence.

PySide6 remains the explicit fallback if the Windows spike reveals unacceptable focus, accessibility, dialog ownership, packaging, renderer, or lifecycle behavior.

## 2. Why this direction is preferred

The current Product already contains tested operator-facing HTML workspaces:

- `connection_settings_web.py`;
- `subtitle_workspace_web.py`.

Those workspaces already use Application Service classes rather than making the browser the business-logic owner. They also already implement loopback host validation, CSRF protection, revision/state handling, and Windows-native file selection through a backend-owned dialog service.

Rewriting those surfaces immediately in a widget toolkit would add UI migration risk before the minimum editing E2E is even integrated. An embedded WebView allows TASK-036 to first solve the higher-value product problem: **one application, one project context, one worker lifecycle, one navigation model, one error/recovery model and no user-managed localhost/browser workflow**.

The WebView is therefore a presentation host, not the Product Core.

## 3. Options considered

### Option A — PySide6 native widgets

Architecture:

`Python -> PySide6/Qt Widgets -> Application Services`.

Strengths:

- fully native widget tree and mature desktop controls;
- direct Python event model;
- Qt provides an official Python binding and an official deployment path;
- `pyside6-deploy` can produce a Windows `.exe` through a Nuitka-based deployment flow.

Costs / risks for this Product now:

- the existing Subtitle and Connection Settings HTML surfaces would need substantial rewrite or a second Qt WebEngine layer;
- duplicate UI implementations are likely during migration;
- Qt runtime/plugins increase packaging complexity and footprint;
- Qt licensing/distribution review is required for the selected packaging model;
- the minimum editing E2E would spend significant effort on toolkit migration instead of integration semantics.

Verdict: **valid fallback / potential later native migration, not preferred for the first shell MVP**.

### Option B — pywebview + EdgeChromium/WebView2

Architecture:

`Python -> pywebview native window -> EdgeChromium/WebView2 -> HTML UI -> bounded Python bridge`.

Strengths:

- reuses current HTML/CSS/JS investment;
- keeps Product logic in Python services;
- removes the user's manual browser/localhost launch even if an internal loopback transport is temporarily retained;
- supports a native top-level window, JS<->Python communication and native dialogs/window lifecycle;
- on Windows it can use the modern EdgeChromium renderer;
- pywebview is BSD-3-Clause licensed;
- WebView2 uses the Windows WebView2 runtime rather than requiring a bundled full browser in the normal Evergreen model.

Costs / risks:

- WebView2 Runtime availability/distribution must be handled explicitly;
- embedded-browser focus, keyboard and accessibility require native testing;
- JS bridge is an authority boundary and must not expose arbitrary Python methods;
- HTML UI quality still needs desktop-grade navigation, sizing and state management;
- freezing/one-file packaging must be validated on the exact Windows matrix.

Verdict: **preferred for TASK-036 Phase 1, contingent on native spike**.

### Option C — Continue external browser + loopback server

Strengths:

- smallest immediate code change.

Reject reason:

- fails the canonical product requirement that normal users launch and operate one `BAI Video Production.exe` without browser URL/manual localhost process management;
- focus/lifecycle/recovery remains fragmented;
- cannot close `MINIMUM_EDITING_PRODUCT_MVP_PASS`.

Verdict: **diagnostic fallback only**.

## 4. External technical facts used by this ADR

This ADR deliberately relies on vendor/project documentation only for toolkit/runtime facts.

- Qt documents PySide6 as its official Python binding and `pyside6-deploy` as a deployment tool that wraps Nuitka and emits `.exe` on Windows.
- Microsoft documents WebView2 as the native-app host for HTML/CSS/JavaScript and provides Evergreen and Fixed Version runtime distribution models. Microsoft recommends handling runtime distribution even when Evergreen is expected, to cover machines where the runtime is missing.
- pywebview documents a native top-level window, a built-in HTTP server, native dialogs/window features and JS/Python communication. The project is BSD-3-Clause licensed and its Windows renderer options include EdgeChromium.

These facts do **not** prove BAI Video Production native acceptance. The required Windows spike remains authoritative.

## 5. Shell architecture

```text
BAI Video Production.exe
|
+-- DesktopWindowHost (pywebview candidate)
|   |
|   +-- Shell UI
|   |   +-- Project
|   |   +-- Media
|   |   +-- Subtitle
|   |   +-- Edit
|   |   +-- Review / QA
|   |   +-- Export / Handoff
|   |   `-- Settings / Diagnostics
|   |
|   `-- Narrow ShellBridge
|       +-- query_state
|       +-- dispatch_command
|       +-- choose_file/folder
|       `-- subscribe/poll job state
|
+-- ShellApplicationService
|   +-- ProjectContext
|   +-- StageReducer
|   +-- CommandAuthorization
|   +-- BackgroundJobRegistry
|   `-- Error/Recovery Mapping
|
+-- Existing Product Services
    +-- TASK-003 ingest
    +-- TASK-006 transcription/subtitle
    +-- TASK-024 cut candidates
    +-- TASK-007 edit plan
    +-- TASK-010 Resolve assembly
    +-- TASK-011 native render + QA
    `-- TASK-012 handoff
```

The WebView must never receive direct filesystem, subprocess, credential-vault, Resolve scripting, or release authority.

## 6. Bridge security contract

The bridge is allowlisted and typed. It is **not** `eval`, arbitrary module invocation, arbitrary Python attribute exposure, arbitrary shell execution, or generic file access.

Initial bridge surface:

```text
shell.get_snapshot() -> ShellSnapshot
shell.dispatch(command: ShellCommand) -> CommandReceipt
shell.get_job(job_id) -> JobSnapshot
shell.choose_path(dialog_request) -> DialogResult
```

Commands map to Application Service capabilities. Each command is validated against:

- Project context;
- current stage;
- human approval requirements;
- external-write authorization;
- expected upstream hashes;
- operation idempotency/recovery semantics.

The UI is never the authority source.

## 7. Internal HTTP decision

The final user experience must not expose localhost, but TASK-036 may initially reuse existing loopback services behind the Shell if that materially reduces migration risk.

Preference order:

1. direct in-process ShellBridge/Application Service for new integrated workflow;
2. temporary Shell-owned loopback adapter for an existing workspace where direct migration would increase risk;
3. external browser launch only under explicit Diagnostics mode.

If loopback is retained internally:

- bind only `127.0.0.1`;
- random/ephemeral port preferred;
- host/origin validation;
- per-process nonce/CSRF;
- no remote bind;
- Shell owns start/readiness/shutdown;
- no normal-user URL display;
- lifecycle Evidence and tests required.

## 8. Native file dialog decision

The Product already has a Windows-native SRT dialog abstraction. TASK-036 must not create competing file-dialog ownership paths per workspace.

Introduce a shell-level `FileDialogService` abstraction supporting:

- open project/folder;
- open media file(s);
- open/save SRT;
- choose EDITOR_WORK destination;
- future generative asset selection.

The Windows implementation may initially adapt the existing tested native dialog behavior, but should not leave PowerShell as an architectural requirement if the selected desktop runtime offers a reliable in-process native dialog API. Migration requires parity tests for foreground ownership, cancellation, Unicode and long paths.

## 9. WebView2 runtime policy

Default release intent: **Evergreen WebView2**, with a bootstrap/runtime check that gives a clear recovery path when missing.

Do not assume every supported Windows installation contains a usable runtime. The packaging spike must test:

- runtime present;
- runtime missing;
- runtime update/restart edge case;
- restricted/offline environment behavior.

A Fixed Version runtime is a fallback decision only if Evergreen operational behavior fails product requirements. Bundling a Fixed Version increases artifact size and update/security responsibilities and therefore requires a separate ADR revision.

## 10. Packaging policy

TASK-036 must not promise literal one-file packaging before the spike.

Product requirement is one **normal user entrypoint** named `BAI Video Production.exe`. Installer-internal support files are acceptable if invisible to the normal workflow and correctly installed/uninstalled.

Evaluate at least:

- PyInstaller one-dir;
- PyInstaller one-file if viable;
- Windows installer around a one-dir payload;
- code signing readiness;
- AV false-positive behavior;
- startup latency;
- WebView2 runtime bootstrap;
- FFmpeg/ffprobe distribution/licensing boundary;
- Resolve scripting module discovery;
- FasterWhisper/native dependency behavior.

Do not optimize for “one physical file” at the cost of reliability, startup time, antivirus trust or maintainability.

## 11. Required Windows packaging/runtime spike

Run only after R0 (`TASK-011` and `TASK-012`) is native-closed and TASK-036 implementation is formally authorized.

Spike acceptance:

1. pywebview candidate launches a native window on supported Windows.
2. EdgeChromium/WebView2 renderer identity is observable in diagnostics.
3. Existing Subtitle Workspace renders correctly in the embedded host.
4. Existing Connection Settings UI renders correctly in the embedded host.
5. keyboard focus works across navigation, text fields and modal/native dialogs.
6. file/folder chooser foreground behavior is correct on multi-monitor Windows.
7. app close owns server/worker shutdown.
8. no user-visible console window is required in release mode.
9. packaged application launches on a clean test account.
10. WebView2 missing-runtime behavior is understandable and recoverable.
11. Unicode project/media/SRT paths work.
12. long Windows paths are characterized.
13. packaged app can discover ffmpeg/ffprobe according to Product policy.
14. Resolve diagnostic connection remains possible without changing human projects.
15. dependency/license inventory is generated.

If any critical UI/focus/accessibility/package criterion fails and cannot be corrected without high complexity, reopen this ADR and execute the PySide6 fallback spike.

## 12. Accessibility requirement

An embedded WebView does not reduce the accessibility requirement.

Acceptance includes:

- keyboard-only primary flow;
- deterministic focus after navigation;
- focus return after native dialogs;
- visible focus indicator;
- semantic headings/form labels/status regions;
- no color-only stage state;
- zoom/scaling at Windows display scaling settings;
- screen-reader smoke test on the final Windows acceptance matrix.

## 13. UI migration rule

Do not copy existing HTML into a second independent implementation.

Refactor toward reusable view assets/components only when implementation begins. During migration:

- existing diagnostic web CLIs remain available;
- Shell uses the same underlying Application Services;
- a screen is not declared migrated until normal-user browser launch is unnecessary;
- old diagnostic routes are not removed until native E2E proves replacement.

## 14. Testing strategy

Before native spike:

- Shell service/state reducer tests;
- bridge allowlist tests;
- untrusted/unknown command rejection;
- upstream-hash conflict tests;
- worker lifecycle tests;
- HTML/static UI tests where practical;
- no business logic in JS tests.

Native spike:

- Windows 11 primary;
- supported Windows 10 matrix where release support is claimed;
- DPI/multi-monitor;
- runtime present/missing;
- normal and failure flows.

Final product acceptance remains the complete TASK-036 E2E, not toolkit launch alone.

## 15. Critic challenge record

The selected candidate must be rejected if Critic finds any of these to be true:

- pywebview merely hides the browser while retaining fragile user-visible localhost lifecycle;
- arbitrary Python methods become callable from JS;
- the Shell duplicates backend business logic;
- native dialogs regress from the already-proven Windows UX;
- packaging requires unsupported/manual prerequisites without recovery UX;
- WebView2 runtime absence becomes an opaque crash;
- accessibility is substantially worse than a native-widget implementation;
- the implementation creates a second independent Settings/Subtitle data model;
- one-EXE branding is used to hide multiple user-managed helper processes.

## 16. Decision summary

**Preferred:** pywebview + EdgeChromium/WebView2 for TASK-036 Minimum Editing MVP.

**Reason:** maximum reuse of existing tested HTML operator surfaces while moving lifecycle, context, authorization, file UX and recovery into one desktop shell.

**Fallback:** PySide6 native widgets if the required Windows spike exposes critical WebView/packaging/accessibility defects.

**Not acceptable as final:** external system browser + manually managed localhost services.
