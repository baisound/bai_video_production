# TASK-059 P1C-J2 Trusted Runtime Configuration Operation Procedure

Date: `2026-08-27`

Identity: `TASK-059-P1CJ2-TRUSTED-RUNTIME-CONFIGURATION-OPERATION-PROCEDURE-20260827-V1`

Document class: `WORK_PROCEDURE`

## Purpose

Verify the synthetic-only launch configuration, canonical service factory and
pre-secret custody-destination gate without applying real configuration or
opening native dialogs.

## Preconditions

1. Use only the dedicated TASK-059 worktree and branch.
2. Set `PYTHONPATH` to the worktree `src` directory.
3. Use synthetic temporary project roots and placeholder public coordinates.
4. Do not read or write `C:\key` or any real Owner key location.
5. Do not supply a real PPK, public-key file, fingerprint, Owner-scope digest,
   custody destination or passphrase.
6. Do not launch the Product EXE, packaged helper, file picker or Credential UI.
7. Do not change `CHANGELOG.md` or the shared lock registry.

## Procedure

1. Parse a synthetic version `1.3.0` launch configuration with exact
   signing-key coordinates and null local-generation sections.
2. Verify strict rejection of invalid fingerprint, Owner-scope and relative
   custody destination values.
3. Build the trusted launcher and verify one canonical
   `OwnerSigningKeyPpkShellService` instance is shared by the bridge and
   lifetime owner without opening UI.
4. Place a synthetic occupied destination in a temporary directory.
5. Advance a synthetic candidate through public confirmation.
6. Verify native secret input is not called and the fixed one-shot destination
   error is returned.
7. Run focused configuration/factory/lifetime/destination tests.
8. Run complete trusted launcher plus P1C-I Shell bridge/service tests.
9. Run TASK-036 Shell/launcher plus all direct TASK-059 tests, separating only
   the known Windows Pytest oversized-parameter-ID function.
10. Run the exact five separated cases under WSL.
11. Compile changed Python files, run `git diff --check` and inspect changed
    paths.

## Expected result

All functional tests pass. No real value, native UI, custody write or signing
effect occurs. Legacy launch versions remain unbound.

## Rollback

Before commit, revert only the exact P1C-J2 source, test and documentation
changes in the dedicated worktree. Do not reset or clean unrelated work.
