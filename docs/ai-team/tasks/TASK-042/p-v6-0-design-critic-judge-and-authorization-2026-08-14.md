# TASK-042 — P-V6-0 Design, Critic, Judge and Authorization

## Owner decision

The Owner directs the attached V6 Product Integration handoff to become the current highest-priority BAI VIDEO PRODUCTION route after completion/cleanup of the prior BAI Development OS task. Roadmap reorganization is authorized and implementation is to proceed only after the roadmap PR merges.

## DEV Profile

`DEV-4 FOUNDATION CRITICAL`

Reasons: incompatible serialized-contract evolution, existing Approved Plan/hash authority, cross-store dependencies, paid/provider/native boundaries, Human Lock/GO, recovery, long-lived Project files and user-facing Windows interaction.

## Builder decision

- Allocate the next independently verified unused identity as `TASK-042`.
- Use one cross-cutting Task with sequential P-V6 slices.
- Keep completed TASK-036..041 history closed and reuse their current services.
- Make Production Timeline the timing authority; treat Master SRT as projection/import proposal.
- Keep TASK-013 Native H3 parked through P-V6-6.
- Implement a standalone v2/migration-preview contract first, without modifying v1 or integrating UI.

## Critic review

### Cycle 1 findings and closures

1. `CRITICAL / CLOSED`: copying legacy Scene references into both Start and End would invent semantics. Migration preview now requires per-frame Human resolution and has no apply/GO authority.
2. `HIGH / CLOSED`: replacing Blueprint 1.0.0 in place would break old Projects and Approved Plan hashes. v1 remains unchanged/readable; v2 is a new major contract and downstream plans become stale.
3. `HIGH / CLOSED`: WORLD LOCK could duplicate Candidate/Lock truth. It is explicitly a projection over TASK-037/038/040 and uses identity references only.
4. `HIGH / CLOSED`: Audio ownership could conflict with the newly hosted-closed TASK-041. TASK-042 owns the Project Timeline contract; TASK-041 remains the Human placement-review foundation and TASK-026 remains compile ownership.
5. `HIGH / CLOSED`: Quick Generate could forge GO. It uses a separate Quick intent and requires normal Candidate/Audit/Lock adoption.

### Cycle 2 findings and closures

1. `HIGH / CLOSED`: a monolithic Gate A would require modifying established v1/store/GO code before the new contract proved stable. P-V6-1 is split: A implements standalone v2 plus migration preview; B integrates Proposal/GO/store only after A passes.
2. `HIGH / CLOSED`: Export Execute All might grant blanket authority. Each job retains individual prepare/apply and stale validation.
3. `MEDIUM / CLOSED`: the handoff lacked a timing conflict choice. Timeline is authoritative; SRT edits create a conflict-checked proposal.
4. `MEDIUM / CLOSED`: structural generation failures could loop through prompt micro-edits. Two identical structural codes require strategy escalation.
5. `MEDIUM / CLOSED`: hosted/static UI could overclaim completion. Native interaction Evidence remains mandatory at P-V6-6.

`CRITIC_PASS_AFTER_TWO_FIX_CYCLES`; unresolved Critical/High `0 / 0`.

## Judge decision

`TASK_042_ROADMAP_PROMOTION_AUTHORIZED / P_V6_1A_IMPLEMENTATION_AUTHORIZED_AFTER_EXACT_ROADMAP_MAIN_MERGE`

The full V6 Product scope is designed, but implementation authority is intentionally sliced. Only P-V6-1A receives immediate post-merge code authorization. Later slices require the prior slice Gate, exact current-main audit and their own bounded Allowed Files.

## Roadmap-promotion Allowed Files

- `PROJECT.md`
- `CHANGELOG.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`
- `docs/ai-team/tasks/TASK-042/**`
- `docs/ai-team/product-design/v6-integration/**`

No source, schema, package version, release, provider, native or external Product mutation is authorized in the roadmap PR.

## P-V6-1A implementation binding

- Baseline: exact main produced by the all-green roadmap PR.
- Allowed Files: the exact list in section 20 of the full detailed design.
- Required gates: focused v2/migration tests, full regression, compileall, schema equality/parse, diff check, Critic 0/0, GitHub matrix all-green.
- Forbidden: v1 semantic change, legacy Project write, Proposal/GO integration, UI, Provider/native execution, paid operation, Release/Tag/Deploy.

This authorization is valid only after verifying the roadmap merge SHA and creating a new dedicated branch/checkout from that exact main.
