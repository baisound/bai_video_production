# TASK-001 Development Profile Selection

## Selected Profile

`DEV-4 FOUNDATION CRITICAL`

## Classification

| Dimension | Value |
|---|---|
| System Scale | PROJECT |
| Feature Scale | LARGE |
| Criticality | CORE |
| Failure Impact | HIGH |
| Reversibility | MODERATE |
| Novelty | NEW_ARCHITECTURE |
| Change Kind | ARCHITECTURE |
| touches_security | true — product data/security boundary contract |
| touches_authorization | false — BAI Owner Authority itself is not modified |
| touches_state_machine | true — Product Production Job State Machine |
| data_migration | false |
| cross_project_contract | false |
| external_side_effects | false in TASK-001 |

## Current Safety Floor Evaluation

Current BAI Development OS `selectDevelopmentProfile()` returns:

- Profile: `DEV_4_FOUNDATION_CRITICAL`
- Score: `25`
- Required Roles: Builder / Critic / Tester / Judge
- Required Tests: UNIT / BOUNDARY_NEGATIVE / INTEGRATION / REGRESSION / CONTRACT / FAULT_INJECTION_OR_RECOVERY / CONSUMER_FIXTURE_WHEN_APPLICABLE
- Revalidation: impacted + core regression
- Evidence Level: CRITICAL

The old rebaseline handoff selected DEV-3, but the current OS implementation includes the `LARGE + HIGH → DEV-4` Safety Floor. TASK-001 therefore executes and closes at DEV-4. The imported pre-implementation DEV-3 state remains preserved in Git commit `fdeec55` rather than being erased from history.

## Machine Evidence

Exact machine output is stored in:

`evidence/profile-selection.json`

## Rework Budget

DEV-4 review cycle cap: `2`. Local Critic corrections were handled within the task and final blocking findings are zero.
