# TASK-054 R6B-D WSL Test Dependency Refresh (Pre-execution)

Date: `2026-08-27`
Status: `PRE_EXECUTION`
Task: `TASK-054 / R6B-D`

## Purpose

Run the fresh-main TASK-054/TASK-049 regression in an isolated WSL virtual
environment after the unchanged global WSL Python environment failed collection
because its `cryptography` package does not provide
`cryptography.hazmat.primitives.kdf.argon2.Argon2id`.

## Boundaries

- Use the current repository dependency contract from `pyproject.toml`.
- Create only `/tmp/bvp-task054-r6bd-venv-20260827`.
- Install the editable current worktree with the `dev` extra only inside that
  temporary venv.
- Do not modify system Python packages, Windows applications, Product settings,
  Dataset contents, model/runtime assets, credentials or private media.
- Do not run Dataset adoption, training, Provider execution, signing, Knowledge
  Pack promotion, Release, Deploy or Production operations.
- Do not record private keys, passphrases, tokens, secrets or Dataset bodies.

## Procedure

1. Confirm the dedicated TASK-054 R6B-D worktree and exact fresh-main base.
2. Read the dependency bound from `pyproject.toml`; require the current
   `cryptography` and `pytest` ranges without changing the Product contract.
3. Create the isolated WSL venv at
   `/tmp/bvp-task054-r6bd-venv-20260827`.
4. Upgrade pip only inside the temporary venv.
5. Install the current worktree as editable with `.[dev]` into the venv.
6. Read back Python, cryptography and pytest versions without printing any
   secret or environment credential.
7. Run R6B-D focused/direct dependency tests, TASK-054/TASK-049 regression,
   compileall, schema mirror and diff/scope checks.
8. Record versions, results, side-effect read-back and rollback state in a
   separate execution-result document.

## Rollback

The temporary venv is isolated from system Python and Product state. If setup or
tests fail, stop using it and preserve only bounded non-secret diagnostics. Its
removal is a separate exact cleanup action after required Evidence is recorded.
