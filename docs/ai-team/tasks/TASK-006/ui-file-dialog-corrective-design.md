# TASK-006 — Subtitle Workspace Native File Dialog Corrective Design

- Date: 2026-08-11
- Candidate package: `0.16.2`
- Scope: Slice C usability corrective only
- Governance: `DEV-2 STANDARD` focused corrective
- Native Windows verification: `PENDING`

## Problem

The `0.16.0/0.16.1` Subtitle Workspace required the operator to type complete local filesystem paths for SRT import and export. That contract is technically executable but fails the intended end-user usability floor: normal Windows operation expects a file chooser for input and a Save As dialog for destination selection.

## UX contract

1. Import exposes a primary `ファイルを選択…` action that opens a Windows-native Open dialog filtered to SRT.
2. Export exposes `保存先を選択…` and opens a Windows-native Save As dialog where folder and filename are selected together.
3. Manual path fields remain available for advanced users and automation troubleshooting.
4. Pressing import/export with an empty path automatically opens the corresponding dialog, so path typing is never mandatory.
5. Importing over a non-empty Workspace requires an explicit replacement confirmation.
6. Cancelling a dialog makes no Workspace mutation.

## Architecture

Browser filesystem APIs cannot safely return arbitrary local absolute paths and cannot provide a host save-folder contract. The loopback application therefore invokes a fixed Windows PowerShell STA script using `System.Windows.Forms.OpenFileDialog` / `SaveFileDialog` after an explicit CSRF-protected operator request.

The script body is fixed and base64-encoded as UTF-16LE for PowerShell `-EncodedCommand`; operator paths are never interpolated into executable script text. Selected paths are returned only to the local loopback page. No file contents are uploaded and no AI Provider is executed.

## Safety / failure behavior

- Native dialogs are Windows-only and fail closed elsewhere with a visible error.
- Host-header and CSRF checks remain mandatory for `/api/dialog`.
- Dialog requests are serialized to avoid stacked native windows.
- Cancel returns `{cancelled: true}` and does not change Revision.
- Import retains existing SRT validation and Revision persistence.
- Export retains atomic temporary-file replacement.

## Verification

- fake-dialog tests prove open/save/cancel are explicit and non-mutating;
- PowerShell runner tests prove a fixed encoded script is used and selected paths are not interpolated;
- existing Subtitle Workspace import/export/revision tests remain regression gates;
- native Windows acceptance must confirm that Open and Save As dialogs appear and selected paths round-trip correctly before a `v0.16.2` tag is created.