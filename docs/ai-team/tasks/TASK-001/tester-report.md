# TASK-001 — Independent Tester Report

## Verdict

`PASS`

## Coverage classes required by DEV-4

| Requirement | Evidence |
|---|---|
| UNIT | IDs, schema helpers, assets, profile, ownership, error envelope |
| BOUNDARY_NEGATIVE | traversal/symlink escape, secret/raw path rejection, checksum format, cross-Job URI, illegal state transitions |
| INTEGRATION | SQLite + Job State + Asset + Manifest + Atomic Writer integration |
| REGRESSION | all Critic defects have dedicated or covering regression cases |
| CONTRACT | JSON Schemas, SemVer compatibility, immutable snapshot/manifest contracts |
| FAULT_INJECTION_OR_RECOVERY | atomic-write failure injection, checkpoint mismatch, atomic resume bridge |
| CONSUMER_FIXTURE_WHEN_APPLICABLE | golden foundation fixture from Job creation through manifest write |

## Concurrency checks

- duplicate idempotency reservations from concurrent workers converge to one Operation ID and exactly one creation
- concurrent Job state updates using the same expected revision produce one winner and one stale-revision rejection

## Packaging check

An isolated wheel build could not download its requested build dependency in the sandbox package index. This was an environment dependency-resolution failure, not a source failure. The same repository successfully produced a wheel using the installed build backend with:

```bash
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir /tmp/ai-video-wheel
```

## Final command set

```bash
python -m pytest -q
python -m compileall -q src tests
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir /tmp/ai-video-wheel
git diff --check
```

Exact final outputs are stored under `evidence/`. The final regression executed after documentation rendering was `43 passed in 1.64s`; `compileall` and the no-build-isolation wheel build also exited successfully. The final wheel SHA-256 was `4a0f0dcf5065901feba7bc3c16c707d04a8292d603eca98301e5fff3ca8f2764`.
