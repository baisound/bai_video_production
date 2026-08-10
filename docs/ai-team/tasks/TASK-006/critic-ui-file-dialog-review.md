# TASK-006 — Critic Review: Native File Dialog Corrective

- Date: 2026-08-11
- Scope: `0.16.2` candidate
- Result: `ACCEPT WITH NATIVE WINDOWS GATE`

## Critic challenge

The first Subtitle Workspace design optimized implementation safety but under-designed the operator workflow. A raw path textbox is not an acceptable substitute for a file-selection workflow on a Windows desktop product. The corrective must not merely add decorative `参照` buttons; selecting, cancelling, replacing existing edits, choosing the output folder, and failure behavior all need defined contracts.

## Rejected weaker alternatives

- Browser `<input type=file>` alone: rejected because browsers do not provide the required arbitrary host path / Save As destination contract and would turn import into an upload-style flow.
- Folder chooser only for export: rejected because the operator would still need a separate filename interaction; Save As solves folder and filename together.
- Automatic replacement immediately after choosing an input file: rejected because it can destroy the currently edited Workspace without an explicit operator decision.
- Passing selected paths inside dynamically composed PowerShell source: rejected because quoting mistakes would create an avoidable command-injection boundary.

## Accepted design

Use fixed Windows Forms Open/Save dialogs triggered only through the existing loopback + CSRF UI. Keep manual paths as an advanced fallback, automatically open the dialog when an action has no path, and require replacement confirmation for a non-empty Workspace.

## Remaining gate

Automated tests cannot prove Windows shell integration from the Linux development environment. `0.16.2` remains a candidate until the Owner runs the native Windows acceptance steps and confirms both dialogs and actual SRT import/export behavior.