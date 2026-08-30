# TASK-059 P1C-J4 - Current Windows Product Launch Evidence

Date: `2026-08-27`

Identity: `TASK-059-P1CJ4-CURRENT-WINDOWS-PRODUCT-LAUNCH-EVIDENCE-V1`

Status: `BUILD_PASS_GUI_NOT_CONFIRMED`

## Build evidence

Exact commit `0813c057eb7214e8308e9d156da9252c258ad964` was rebuilt through
the canonical Windows packaging entrypoint with the existing Python `3.12.4`
and PyInstaller `6.22.0` environment.

- Main one-directory build: `PASS`.
- Helper one-file build: `PASS`.
- Packaged helper identity verification: `PASS`.
- Secret-free helper native smoke: `PASS`.
- Main EXE: `16426435` bytes,
  SHA-256 `8f0cb24dcee4d85342a87d060c338834480d36fec9eeca02fc0838613b8d6a67`.
- Bundled helper: `17229588` bytes,
  SHA-256 `b9b8b79353697b785fcc048dc0474773a224327a031d88dee4fd08d91cf4180c`.
- Staging helper: exact same size and SHA-256 as bundled helper.

The prior hosted cross-platform repair and bounded fixture-ID repair are part
of this exact source head. Draft PR #396 on this head has CI `6 / 6 PASS` and
Security `2 / 2 PASS`; CHANGELOG remains the single expected shared-lock wait.

## GUI execution evidence

Computer Use failed before `list_apps` returned a window inventory:

`failed to write kernel assets: 指定されたパスが見つかりません。 (os error 3)`

The required JavaScript session reset and one recovery attempt produced the
same error. In accordance with the Computer Use recovery and non-fallback
rules, the Main Product EXE was not launched and no alternate Windows UI
automation was used.

## Review

Critical/High/Medium/Low in the completed build scope: `0 / 0 / 0 / 0`.

Main Product startup and the prior frozen-entry exception remain
`NOT_CONFIRMED`. Credential UI automation remains prohibited. No real Owner
configuration, key material, DPAPI custody, signing, installer, publication,
promotion, Release, Deploy or Production effect occurred.
