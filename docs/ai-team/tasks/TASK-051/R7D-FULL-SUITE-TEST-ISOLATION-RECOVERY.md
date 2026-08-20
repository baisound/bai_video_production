# TASK-051 R7D — Full-suite Test Isolation / Stale Contract Recovery

Governance: `DEV-3 HIGH ASSURANCE`
Status: `BOUNDED_FIX_RETEST`

## Root cause

The R7 focused lineage gate passed, but the complete pytest run failed massively.

The primary cascade was test-process contamination: historical helper tests replaced
`sys.modules["ai_video_production"]` with a synthetic `ModuleType` and never restored it.
Once that happened, `importlib.resources.files("ai_video_production")` saw a package whose
`__spec__` was `None`, causing schema/resource and downstream imports to fail across unrelated tasks.

Three generated tests are corrected to use the real package instead of synthetic parent-package
injection:
- `tests/test_current_source_validated.py`
- `tests/test_task050_sqlite_windows_lock_fix.py`
- `tests/test_task051_r1_training_presentation.py`

Historical literal UI contracts are also rebased for the accepted TASK-051 UI in:
- TASK-049 Training Studio packaging test;
- TASK-049 Kamigame collector test;
- TASK-050 HUD two-column/scroll test.

The R7 accepted-source test is rewritten to hash the actual Product source directly.

No Product source is changed by R7D.

## Gates

Installer runs:
1. R7D isolation/stale-contract focused tests;
2. schema-resource regression immediately after the former polluting tests;
3. complete repository pytest;
4. py_compile;
5. git diff --check.

It reports PASS only if the complete repository pytest is green.
