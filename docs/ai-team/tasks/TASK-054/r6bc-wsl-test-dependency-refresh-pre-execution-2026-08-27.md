# TASK-054 R6B-C WSL Test Dependency Refresh (Pre-execution)

Date: `2026-08-27`
Status: `PRE_EXECUTION`
Task: `TASK-054 / R6B-C`

## Purpose

Re-run the fresh-main TASK-054/TASK-049 regression in an isolated WSL virtual
environment after the existing global WSL Python environment failed collection
because its `cryptography` package does not provide
`cryptography.hazmat.primitives.kdf.argon2.Argon2id`.

## Boundaries

- Use the current repository dependency contract from `pyproject.toml`.
- Create only `/tmp/bvp-task054-r6bc-venv-20260827`.
- Install the editable project with the `dev` extra into that temporary venv.
- Do not modify system Python packages, Windows applications, Product settings,
  Dataset contents, model/runtime assets, credentials or private media.
- Do not run Dataset adoption, training, Provider execution, signing,
  Knowledge Pack promotion, Release, Deploy or Production operations.
- Do not record private keys, passphrases, tokens, secrets or Dataset bodies.

## Procedure

1. Confirm the dedicated TASK-054 R6B-C worktree is clean except for this
   procedure document and is based on the exact fresh `origin/main` merge.
2. Read the dependency bound from `pyproject.toml`; require
   `cryptography>=46,<51` and `pytest>=8,<10`.
3. Create the isolated WSL venv at
   `/tmp/bvp-task054-r6bc-venv-20260827`.
4. Upgrade `pip` inside the temporary venv.
5. Install the current worktree as editable with `.[dev]` into the venv.
6. Read back Python, cryptography and pytest versions without printing any
   secret or environment credential.
7. Run R6B-C focused tests, TASK-054/TASK-049 regression, compileall, schema
   mirror and diff-scope checks.
8. Record the observed versions, test results, repository diff and rollback
   state in a separate execution-result document.

## Rollback

The temporary venv is isolated from system Python. If installation or tests
fail, stop using it and retain its path only long enough for bounded diagnosis.
Removal is a separate cleanup action after all required evidence is preserved.
