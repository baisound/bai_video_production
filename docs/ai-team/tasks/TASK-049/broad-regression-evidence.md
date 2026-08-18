# TASK-049 — Broad Regression Evidence

## Result

`PASS / ONE_WINDOWS_ONLY_SKIP`

## Scope

All `232` repository `tests/test_*.py` files were covered with no deselection.

A single monolithic pytest invocation progressed without failures but exceeded the bounded runner timeout before completion. To obtain complete evidence without changing the test set, the exact sorted file list was partitioned into four non-overlapping groups; the two larger remaining groups were further divided only for execution-time bounding. Every test file appears exactly once in the completed grouped run.

## Result

- `2082 PASS`
- `1 SKIP` — `tests/test_task047_obs_installer_contract.py:133`, Inno Setup acceptance is Windows-only
- `0 FAIL`
- `0 DESELECT`

No TASK-049-caused regression was observed.

The former README-link mismatch is no longer excluded: documentation filenames were normalized to English and references were updated, and the readiness link test now participates normally in the broad PASS result.

## Group evidence

```text
Chunk 00: 77 PASS
Chunk 01: 208 PASS
Chunk 02: 205 PASS
Chunk 03A: 88 PASS
Chunk 03B: 128 PASS
Chunk 04: 213 PASS
Chunk 05: 146 PASS
Chunk 06: 106 PASS
Chunk 07: 205 PASS
Chunk 08: 116 PASS
Chunk 09: 177 PASS
Chunk 10: 335 PASS / 1 Windows-only SKIP
Chunk 11: 78 PASS
--------------------------------
Total:    2082 PASS / 1 SKIP
```

## Additional verification

- TASK-049/TASK-036/packaging focused regression after R10B0: `181 PASS`
- TASK-049 R1-R10B0 + TASK-009 focused regression: `129 PASS`
- R10B0 + R10A + Human Gold/preflight focused: `18 PASS`
- TASK-036 P-UX-2 current-source revalidation: `102 PASS`
- `python -m compileall -q src`: required before final handoff
- `git diff --check`: required before final handoff

## Platform gate

R9B2 actual packaged Windows execution is not represented by this Linux broad regression. Its Windows-only harness is implemented separately and remains `NOT_EXECUTED` on the current host.

## 2026-08-18 — R10B5B HUD Calibration / Data Migration

Repository-wide `tests/test_*.py` were partitioned into four non-overlapping groups after the final HUD Calibration / Backup-Restore implementation state.

- Group 1: `511 PASS`
- Group 2: `597 PASS`
- Group 3: `454 PASS / 1 Windows-only SKIP`
- Group 4: `566 PASS`
- Total: **`2128 PASS / 1 Windows-only SKIP / 0 FAIL`**

The skip remains the pre-existing Inno Setup acceptance test which requires a Windows host. TASK-049 focused suite is `164 PASS`.


## 2026-08-18 Kamigame Knowledge Candidate Import

After adding the bounded Kamigame Community Reference collector, Training Studio Knowledge Import tab, CLI and documentation, all `tests/test_*.py` files were partitioned into four disjoint groups because a monolithic invocation exceeded the host command timeout.

Results:

- group 0: `521 PASS`
- group 1: `589 PASS`
- group 2: `454 PASS / 1 Windows-only SKIP`
- group 3: `576 PASS`
- aggregate: **`2140 PASS / 1 Windows-only SKIP / 0 FAIL / 0 DESELECT`**

The skip is the existing TASK-047 Inno Setup acceptance gate and is unrelated to TASK-049. Live Kamigame network collection is not claimed as executed on the sandboxed development host; parser/pagination/detail/bundle/GUI/CLI behavior is fixture-tested.
