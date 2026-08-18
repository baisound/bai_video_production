# TASK-049 — Codex Development Handoff

## Mission

Implement the approved/authorized portions of `TASK-049 Game Intelligence / Dead by Daylight Integration` inside BAI VIDEO PRODUCTION without creating a separate standalone product.

## Read order

1. `README.md` -> `AUTONOMY` -> adaptive model/governance/context example.
2. `docs/ai-team/current-state.md`.
3. `docs/ai-team/tasks/TASK-049/task.md`.
4. `docs/ai-team/tasks/TASK-009/TASK-049-GAME-INTELLIGENCE-INTEGRATION-DESIGN.md`.
5. `docs/ai-team/tasks/TASK-009/TASK-049-ATOMIC-IMPLEMENTATION-PLAN.md`.
6. Current R-unit direct dependencies only.

The long Ver.2.2 source design is Input Evidence, not a replacement for current BVP authority:

`docs/ai-team/tasks/TASK-009/input-evidence/Dead_by_Daylight_Video_Intelligence_Platform_Ver2.2_Game_Knowledge_Integrated.md`

## Non-negotiable decisions

- One Product entrypoint: `BAI Video Production.exe`.
- No `BAI DbD Intelligence.exe` in this program.
- Analysis-only workflow inside BVP is mandatory.
- Canonical Game Event Timeline and BVP Production Timeline remain separate.
- Exact rational/frame time is canonical; floating seconds are display only.
- Existing TASK-003/004/006/008/009/022 capabilities are reused.
- Detector/LLM output is Evidence/Candidate, not unreviewed canonical truth.
- Production bridge is proposal/adoption, never direct mutation authority.
- UNKNOWN/NEEDS_REVIEW are preferred over unsupported confident claims.

## AUTONOMY execution rule

For each R-unit:

```text
Design check
 -> Implement
 -> Focused tests
 -> required full regression
 -> Evidence / git diff review
 -> Commit-ready checkpoint
```

Do not start the next unit with the current unit half-complete.

## Model/cost guidance

Use capability classes rather than a single expensive model for every action.

- High-Reasoning: architecture, canonical boundaries, important schemas, Critic, difficult defects, final integration review.
- Implementation: Python/services/adapters/UI/tests/refactors.
- Bulk/Mechanical: fixtures, repetitive tests, boilerplate schema/doc/rename/static audit.

If GPT-5.6 Sol/Terra/Luna are available, the README contains the current concrete mapping example. Treat that mapping as an example, not permanent model identity.

## First unit

Start at `R1 — Canonical Game Event Contract Foundation` only after Current State / Authority / branch / worktree are revalidated.

Do not add detector code in R1.

## Branch safety

- do not work on protected main;
- do not `git add .` without reviewing paths;
- no force push;
- no `reset --hard` over unknown user work;
- preserve unknown local changes;
- commits should correspond to one Atomic Unit or one bounded corrective unit.

## When to park

Park only the affected unit for Human Gate. Apply `TASK_BLOCKED != SYSTEM_BLOCKED` if a different already-authorized independent unit exists.

## Completion report per unit

Report:

```text
R-unit
HEAD / branch
changed files
contracts added/changed
focused tests
full regression status
known limitations
Human Gates
next R-unit
estimated context/cost concern
```
