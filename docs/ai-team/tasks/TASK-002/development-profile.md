# TASK-002 — Development Profile

- Task: `TASK-002 — Resolve Capability Spike`
- Historical Alias: `VIDEO-TASK-002`
- Profile: `DEV-4 FOUNDATION CRITICAL`
- Score: `22`
- Selection Authority: BAI Development OS package `1.0.0` machine policy

## Change classification

| Field | Value |
|---|---|
| system_scale | PROJECT |
| feature_scale | MEDIUM |
| criticality | CORE |
| failure_impact | HIGH |
| reversibility | EASY |
| novelty | NEW_ARCHITECTURE |
| change_kind | ARCHITECTURE |
| touches_security | true |
| touches_authorization | false |
| touches_state_machine | false |
| data_migration | false |
| cross_project_contract | false |
| external_side_effects | true |

## Why DEV-4

This task establishes the capability truth boundary between the Consumer Project and DaVinci Resolve, plus the IPC decision that future Resolve Gateway work will inherit. Incorrect capability assumptions can later cause writes to the wrong Project/Timeline, silent partial edits, or unsafe recovery behavior. The spike therefore uses architecture/failure-mode design, independent testing, Critic review and Judge gate.

## Context economy

Only TASK-001 completion state, Product Design Baseline sections 15/19/29/30/36/38, the current BAI adaptive profile selector, and impacted source/tests are in scope. Full OS Architecture and unrelated product chapters are not loaded.
