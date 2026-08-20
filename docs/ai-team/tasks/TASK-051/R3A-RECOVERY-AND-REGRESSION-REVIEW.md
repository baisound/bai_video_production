# TASK-051 R3A — Recovery / Stale R2 Regression Fix

Governance: `DEV-3 HIGH ASSURANCE`
Status: `BOUNDED_FIX_RETEST`

## Failure classification

The R3 implementation source passed its own focused tests (`7 passed`), then the inherited
R2 integration test failed because it required the literal UI text `Cropプレビュー`.

R3 intentionally renamed that section to `複数Cropプレビュー` to support the accepted
multi-slot design. This is a stale regression assertion, not a Product implementation defect.

## Corrective action

Update only `tests/test_task051_r2_training_studio_transport_integration.py` so that:
- `動画プレビュー` remains mandatory;
- either the historical single-crop label or the new multi-crop label is accepted.

No Product source is changed by R3A.

## Retest gate

The installer:
1. verifies the exact partially-applied R3 source hashes;
2. verifies the exact old R2 test hash before replacement;
3. replaces only the stale test;
4. reruns R3, R2, R1, TASK-050 focused regressions;
5. runs `py_compile` and `git diff --check`.

No unresolved HIGH finding remains.
