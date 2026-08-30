# TASK-059 P1C-I Shell API and UI Operation Procedure

Date: `2026-08-27`

Identity: `TASK-059-P1CI-OPERATION-PROCEDURE-V1`

Status: `RECORDED`

## Purpose

Safely verify the body-free Owner signing-key Shell API and the canonical
`Connection / Secret` UI source without opening a real authentication dialog
or touching an Owner key.

## Preconditions

1. Use the dedicated TASK-059 worktree and confirm its exact branch and HEAD.
2. Confirm the worktree is free of unknown dirty paths.
3. Use only synthetic test fixtures.
4. Do not read `C:\\key`, a real PPK, a real public-key file, a passphrase,
   a private seed or a DPAPI custody file.
5. Do not launch or automate Windows Credential UI.
6. Do not install or download software and do not change Product or OS settings.

## Procedure

1. Run the focused P1C-I/H1/H2/native-dialog tests with the project Python 3.12
   runtime and `PYTHONPATH=src`.
2. Run the existing TASK-036 Shell Settings tests together with direct
   TASK-059 tests.
3. Keep the known Windows Pytest oversized parameter-ID setup limitation
   separate from Product results; do not label an unexecuted case PASS.
4. Extract only the embedded canonical Settings JavaScript and run Node
   `--check`.
5. Run `git diff --check`, inspect the exact changed paths and audit for real
   key paths, key bodies, private seed fields and WebView passphrase transport.
6. Do not start real custody import, signing, publish, promotion, Release,
   Deploy or Production.

## Rollback

Before commit, use the dedicated task branch diff to revert only the exact
P1C-I files if verification fails. Never reset or discard unrelated work.
