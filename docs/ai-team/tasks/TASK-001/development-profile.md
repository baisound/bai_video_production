# TASK-001 Development Profile Selection

## Selected Profile

`DEV-3 HIGH ASSURANCE`

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
| touches_state_machine | true — Product Production Job state machine |
| data_migration | false |
| cross_project_contract | false |
| external_side_effects | false in TASK-001 |

## Safety Floor Evaluation

- CORE → minimum DEV-3
- state machine → minimum DEV-3
- security boundary contract → minimum DEV-3
- System Scale is not FOUNDATION
- Failure Impact is HIGH, not CRITICAL

Therefore DEV-3 is the minimum sufficient profile.

## Escalate to DEV-4 if

- BAI Development OS Core/Foundation change becomes necessary
- Failure Impact becomes CRITICAL
- Multi-project contract becomes part of scope
- irreversible migration enters scope

## Rework Budget

DEV-3 maximum design/implementation rework cycles: 2 before blocker/Owner escalation.
