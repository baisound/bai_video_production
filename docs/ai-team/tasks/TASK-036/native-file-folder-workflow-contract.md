# TASK-036 — Native File / Folder Workflow Contract Ver.1.0

- Date: 2026-08-13
- Status: `AUTOMATED_FOUNDATION_PASS / WINDOWS_NATIVE_DIALOG_GATE_PENDING`
- Owner UX authority: normal workflow must use native file/folder pickers; typed-path-only UX is not acceptable.

## 1. Scope

TASK-036 now has a dedicated native chooser boundary for:

- local media source selection;
- Project folder selection;
- EDITOR_WORK destination selection.

The chooser is **selection only**. Selection does not imply ingest, Project open, handoff creation or external mutation.

## 2. Host-path privacy

A selected host path is ephemeral runtime data.

```text
Windows Native Dialog
→ local TASK-036 chooser boundary
→ local Application Service call
→ underlying Product capability
```

General Evidence stores only purpose/result/path kind. It does not persist the absolute host path.

## 3. Security

- fixed PowerShell scripts; selected paths are never interpolated into script source;
- one selected media file only;
- media result must be an existing regular non-symlink file;
- folder result must be an existing regular non-symlink directory;
- off-Windows usage fails closed;
- arbitrary bridge fields are rejected;
- a browser/WebView receives no generic filesystem execution primitive.

## 4. Media workflow integration

`Task036MediaWorkflowFacade` joins:

```text
Native media chooser
→ ephemeral host path
→ stage-aware Shell command authorization
→ injected TASK-003 ingest port
→ canonical Asset ID + SHA-256
→ EditingSession bind_source
```

The Shell receipt persists the source **file name** and canonical Asset identity, not the absolute host path.

A second ingest request is rejected when the current stage no longer exposes `media.choose_and_ingest`.

## 5. Native acceptance

Windows acceptance must prove:

- OpenFileDialog foreground/focus behavior;
- Japanese and spaces in paths;
- long-path behavior where Windows/application support it;
- cancellation without state mutation;
- folder chooser focus;
- 125% / 150% / 200% display scaling;
- fullscreen/multi-monitor foreground behavior;
- chooser result does not appear in persisted checkpoint/Evidence as an absolute path.

No automated Linux test is Native Evidence.
