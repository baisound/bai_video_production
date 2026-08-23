# P-UX-2L Subtitle and Cut Controls R0 Detailed Design

Date: 2026-08-24
Task: TASK-036 / P-UX-2L
Governance: DEV-3 HIGH ASSURANCE
Status: REVIEW REMEDIATION VERIFIED / INDEPENDENT RE-REVIEW PENDING

## 1. Goal

Connect the existing deterministic Subtitle Workspace and Cut Candidate stages to the V6.1.1 Product UI without creating a second subtitle/cut implementation. The unit closes four safety gaps: operation lifetime, single-flight admission, apply-time currentness, and privacy-safe WebView results.

## 2. Scope

May modify:

- `desktop_editing_application.py`
- `desktop_editing_coordinator.py`
- `desktop_pre_edit_binding.py`
- `desktop_shell.py`
- `task036_pre_edit_runtime.py`
- `task036_shell_ui.py`
- `task036_shell_v611.py`
- directly focused TASK-036 tests
- this design document

Must not modify:

- Provider/model/download configuration or execution semantics
- TASK-003/TASK-006 canonical stores or schemas
- Audio, Resolve apply, render, export, or handoff authority
- CHANGELOG, shared lock Registry, CI workflow, or release metadata
- Owner media or native application state

## 3. Existing authority and reuse

- `SubtitleWorkspace.from_transcript()` remains the only workspace constructor.
- `CutCandidateGenerationPort.generate_cut_candidates()` remains the only candidate generator.
- `Task036EditingApplication.prepare_from_pre_edit_results()` builds a review application from one captured coordinate without publishing state; the compatibility constructor remains available.
- The Shell stage machine remains authoritative for `subtitle.save` and `cut_candidates.generate` admission.
- These stages are local deterministic operations and do not gain Provider, paid, download, Resolve, or native mutation authority.

## 4. Runtime contract

### 4.1 Shared deterministic-stage single flight

`Task036PreEditRuntime` owns one non-blocking lock shared by Subtitle Workspace creation and Cut Candidate generation. A parallel call fails with `ERR_TASK036_PRE_EDIT_STAGE_IN_PROGRESS` before construction, port execution, binding, or application replacement.

### 4.2 Full coordinate snapshot

Before work starts, the runtime captures:

- Project ID and Shell context revision
- Editing session revision
- source Asset ID and SHA-256
- trusted runtime source path identity
- Transcript manifest SHA-256 and the exact bound Transcript object
- expected next action

Wrong stage or missing inputs fails before the deterministic constructor/port is invoked.

### 4.3 Apply-time atomic state admission

After construction/generation, the binding asks `DesktopEditingCoordinator` to compare the full expected coordinate under its state lock and advance only when still current.

- Subtitle requires exact `subtitle.save`, then binds the computed workspace SHA-256.
- Cut requires `cut_candidates.generate` to be admitted by the canonical state command set, preserving the optional Subtitle route, plus exact source/Transcript binding before the generated manifest SHA-256 is bound.
- Project, revision, source, Transcript, context, or stage drift fails closed with a stable TASK-036 stale-context error.
- A rejected result must not publish `subtitle_workspace`, `application`, or a Cut Candidate state binding.

The generated Cut manifest must independently match the expected source Asset and Transcript identity before promotion.

Cut promotion is prepare/validate/commit: application and optional workflow-runtime factories complete before the final coordinator CAS; only then are state, application, and workflow runtime published. Factory failure or identity mismatch leaves the original coordinate retryable. The same re-entrant lock serializes Shell context mutation with the coordinator CAS.

## 5. Bridge and lifetime contract

Both public bridge methods:

- accept only an empty object (or the existing no-argument compatibility form),
- hold the trusted launch operation guard for the complete call,
- are rejected after launch close begins,
- make launch close wait for an already admitted operation,
- validate the private runtime result,
- return a closed public envelope only.

Subtitle public fields: owner, operation, status, workspace digest, cue count, next action, Provider false, host path false, Transcript text false.

Cut public fields: owner, operation, status, manifest digest, candidate count, next action, Provider false, host path false, candidate details false.

The WebView never receives source paths, Transcript text, cues, candidates, `editing_session`, private receipts, or application objects.

## 6. UI contract

The Home and Edit workflow buttons share one in-process UI gate for the Subtitle/Cut actions. Before the first await, both controls are disabled and marked busy. The UI then re-reads `workflow_status` and executes only when it exactly matches the requested action. It accepts only the closed status/digest envelope, reports failure for malformed results, and refreshes both controls in `finally`.

The Python runtime remains authoritative; the JavaScript gate is defense in depth, not execution authority.

## 7. Failure modes and acceptance

- Parallel Home/Edit activation: at most one Python call.
- Parallel direct bridge activation: exactly one runtime call; the other receives the stable in-progress error.
- Stage/source/Transcript/Project drift during computation: no stale binding or application.
- Launch close during computation: admitted call completes; close waits; new/old bridge calls fail.
- Malformed private result: bridge rejects it without returning private data.
- No Provider/native/paid/download/Resolve call is introduced or executed by focused tests.
- Existing transcription, review promotion, and workflow tests remain green.

## 8. Local verification

- Python compile check: PASS for the six modified Product modules.
- Embedded V6.1.1 JavaScript `node --check`: PASS.
- Focused and targeted regression: 175 passed across eight directly impacted test files.
- Diff whitespace check: PASS.
- Provider/model download, paid Provider, Resolve, render, native GUI, and Owner media execution: not performed.
- Initial independent review at `56ba4a1`: Tester PASS, Judge Technical GO, Critic Technical NO-GO with C0/H2/M2/L1.
- All initial Critic findings have corresponding implementation or behavioral-test remediation; independent re-review is pending, so no final independent PASS is claimed by this checkpoint.
