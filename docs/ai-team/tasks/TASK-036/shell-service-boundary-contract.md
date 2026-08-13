# TASK-036 — Shell / Application Service Boundary Contract Ver.0.9

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / PREIMPLEMENTATION`
- Implementation authorization created by this document: `NONE`
- Parent: `ADR-036-001`

## 1. Purpose

Define a stable UI-to-Product boundary before choosing concrete view components. The shell owns orchestration and user-visible state; existing TASK services retain their business authority.

## 2. Core rule

`View Event -> ShellCommand -> Authorization/Prerequisite Check -> Application Service -> Durable Artifact/Evidence -> ShellSnapshot`

The view does not call TASK CLIs, parse terminal output, mutate JSON files directly, call Resolve scripting APIs directly, or write credential stores directly.

## 3. ShellSnapshot

Conceptual fields:

```text
ShellSnapshot
- product_version
- project
- selected_asset
- stages[]
- current_workspace
- active_jobs[]
- notifications[]
- resolve_connection
- human_review
- next_recommended_action
```

Each stage includes:

```text
stage_id
state
blocking_reason
artifact_identity
last_operation_id
available_commands[]
```

`available_commands[]` is computed by Product state/authority. The JavaScript/UI layer cannot self-enable a forbidden command.

## 4. ShellCommand

Every mutation has:

```text
command_id
command_type
project_id
expected_context_revision
expected_upstream_hashes
payload
human_confirmation_token?   # only where a Product confirmation flow issued it
```

Unknown fields/commands fail closed.

## 5. Minimum command families

### Project

- `project.open`
- `project.create`
- `project.select_asset`

### Media

- `media.choose_and_ingest`
- `media.normalize` (when required by Product flow)

### Subtitle

- `transcription.start`
- `transcription.cancel`
- `subtitle.import`
- `subtitle.save`
- `subtitle.update_cue`

### Edit

- `cut_candidates.generate`
- `edit_candidate.review`
- `edit_plan.approve`

### Resolve / QA

- `resolve.connection_check` (read-only)
- `resolve.assembly.prepare`
- `resolve.assembly.apply` (external write confirmation required)
- `render.prepare`
- `render.start` (external write confirmation required)
- `render.qa.inspect`

### Handoff

- `handoff.choose_destination`
- `handoff.create`
- `handoff.open_folder`

### Settings

- `settings.read`
- `settings.update`
- credential operations remain behind the existing Credential Vault service and explicit UI interaction.

## 6. Command categories

```text
READ_ONLY
LOCAL_REVERSIBLE
LOCAL_DURABLE
EXTERNAL_MUTATION
HUMAN_FINAL_AUTHORITY
```

The command category is server/Application-Service metadata, never a JS-provided truth.

External mutation commands require a confirmation payload created from the exact current Product state. The payload becomes stale if upstream hashes/project/timeline change before execution.

## 7. External confirmation payload

```text
confirmation_id
command_type
target_application
target_project
target_timeline
destination
upstream_hashes
idempotency_class
expires_when_context_revision_changes
```

A generic reusable “confirmed=true” boolean is prohibited.

## 8. Background jobs

Long work returns a `job_id`; it does not block the UI bridge call until completion.

```text
JobSnapshot
- job_id
- command_id
- stage
- state
- progress_kind
- progress_value?
- started_at
- safe_cancel
- error?
- evidence_ref?
```

Progress can be polled in MVP. Event/push transport may be added only if it simplifies the shell without weakening determinism/testability.

## 9. Error mapping

All backend failures reach the Shell as a structured ProductError envelope:

```text
code
category
message
retryable
details_safe_for_ui
operation_id
evidence_ref
```

Raw stack traces, secrets, command lines and private host paths are Diagnostics-only and must not be blindly copied into normal UI.

## 10. Context revision / stale protection

Every ShellSnapshot has a monotonically changing Project/Shell context revision or equivalent durable identity.

Commands created against an older context fail with a structured stale-state error if execution could affect the wrong Asset, Plan, Resolve Project/Timeline or destination.

This prevents a user changing Project/Asset in one workspace while a stale browser event mutates another context.

## 11. View transport

The contract is transport-neutral.

Permitted implementations:

- in-process pywebview JS API adapter;
- Shell-owned loopback HTTP adapter;
- future native widget direct calls.

All transport implementations must call the same `ShellApplicationService` contract.

## 12. Existing web workspace migration

Existing `ConnectionSettingsWebService` and `SubtitleWorkspaceWebService` are domain-adjacent service/view adapters. TASK-036 should reuse their tested business-facing services/state while progressively moving normal-user hosting into the Shell.

Do not make TASK-036 call `main()` or launch the user's browser.

## 13. Test contract

Mandatory tests before `SHELL_INTEGRATED`:

- command allowlist;
- unknown command rejection;
- stale context rejection;
- confirmation expiry;
- external mutation without confirmation rejected;
- read-only command does not require mutation authority;
- backend ProductError faithfully mapped;
- job restart/recovery;
- shell close with unsafe active job;
- project switch invalidates incompatible pending confirmations;
- no bridge method provides arbitrary shell/file/process execution.
