# TASK-059 P1C-J1 Trusted Launcher Operation Procedure

Date: `2026-08-27`

Identity: `TASK-059-P1CJ1-TRUSTED-LAUNCHER-OPERATION-PROCEDURE-20260827-V1`

Document class: `WORK_PROCEDURE`

## Purpose

Verify the non-secret trusted-launcher composition seam and resource-lifetime
behavior without opening the application, selecting a key, showing a
Credential UI, importing custody material or starting signing.

## Preconditions

1. Use only the dedicated TASK-059 worktree and branch.
2. Set `PYTHONPATH` to that worktree's `src` directory.
3. Use the installed Windows Python 3.12 interpreter.
4. Do not supply a real PPK, public key, passphrase, fingerprint, Owner-scope
   digest or custody destination.
5. Do not launch the Product EXE or packaged helper.
6. Do not change `CHANGELOG.md` or the shared work-lock registry in this unit.

## Procedure

1. Read back the dedicated worktree branch and dirty-file list.
2. Inspect only the TASK-036 trusted launcher source, its direct test module,
   the P1C-I Shell bridge/service tests and the TASK-059 canonical task record.
3. Inject a synthetic body-free signing-key service stub through
   `build_trusted_launch`.
4. Verify that the canonical bridge receives the same instance.
5. Close the launch twice and verify exactly one service close.
6. Make the synthetic service close fail and verify the local-operation
   lifetime, runtime lease and Product store still close.
7. Re-run the existing concurrent in-flight runtime-lease close test and verify
   its retry semantics remain unchanged.
8. Run the full trusted-launcher test module.
9. Run the trusted launcher plus direct P1C-I Shell bridge/service regression.
10. Run `git diff --check` and inspect the exact diff and changed paths.

## Expected result

- Focused lifetime and concurrent-close tests pass.
- Full trusted-launcher tests pass.
- Direct P1C-I integration regression passes.
- No secret, key path, private body or passphrase appears in output or docs.
- No application/helper launch, file picker, Credential UI, custody write,
  signing, Release, Deploy or Production effect occurs.

## Rollback

Before commit, revert only the exact P1C-J1 source, test and documentation
changes in the dedicated worktree. Do not reset or clean unrelated work.
