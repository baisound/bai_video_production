# TASK-027 — Approved Plan / Total Budget / Production Admission Safety Contract

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`
- Provider execution: NOT performed by this slice
- Account credit purchase / auto-topup: NOT authorized

## Human GO is a real identity, not a boolean

The new-video orchestration path no longer needs to trust a caller-supplied `plan_approved=True` flag.

`ApprovedPlanVerifier` resolves a registered immutable `ApprovedProductionPlan`, proves its exact Proposal/Intent/Blueprint/Provider Policy lineage, and rejects drift.

`ApprovedPlanProductionControlInstaller` installs the validated Blueprint into TASK-037 and also adds a separate:

`Approved Production Plan -> Scene`

dependency bound to the exact Approved Plan SHA-256. The pre-existing Blueprint -> Scene provenance edge remains, so Human approval authority and Blueprint provenance are both traceable instead of being conflated.

## Approved Plan -> Scene -> Slot validation

`ApprovedPlanTraceValidator` verifies:

- Approved Plan still matches exact Proposal/Blueprint;
- every Blueprint-required Slot exists with the same Project/Scene/Kind semantics;
- exact Human-approved Plan -> Scene edge + Plan SHA;
- exact Blueprint -> Scene edge + Blueprint SHA;
- every Scene -> Slot dependency.

It is read-only and performs no repair or generation.

## Total production cost ceiling

`ProductionBudgetLedger` is a provider-neutral reservation ledger bound to the Human-approved Plan cost ceiling/currency.

Operations:

- `reserve(operation_id, estimated_amount)`;
- `commit(operation_id, actual_amount)`;
- `release(operation_id)`;
- `require_reserved(operation_id)`.

The sum of committed cost plus active reservations may never exceed the approved total ceiling. If actual provider cost would cross the ceiling, commit fails closed rather than silently accepting the overrun.

The ledger cannot buy credits, enable automatic top-up or execute a provider.

`ProductionBudgetSnapshotStore` adds atomic/canonical/CAS persistence so concurrent stale writers cannot both safely consume the same budget snapshot.

## Paid generation admission

`BudgetedApprovedPlanGenerationAdmissionService` requires all of:

1. exact immutable Human GO plan;
2. exact approved Blueprint;
3. exact approved Provider Policy SHA;
4. Shot Feasibility PASS;
5. required input Slots locked/current;
6. explicit paid-execution authorization;
7. a budget ledger bound to the same Plan/currency/ceiling;
8. active reservation for the exact operation.

Local/free routes do not invent a paid-execution requirement.

## TASK-013 preferred new-video route

`ApprovedCreativeGenerationPlanner` is the preferred TASK-013 planning boundary for TASK-027 new-video work. It binds the active `AiConnectionProfile` ID/version/SHA to the profile approved at GO and rejects profile drift. Paid cloud routes additionally require an exact active production-budget reservation.

It still only compiles a provider execution plan. The provider call happens later through the existing execution adapter and remains separately bounded/idempotent/evidenced.

## Crash-safe upstream bundle

`PlanningProductionBundleStore` pins the exact three snapshots validated together:

- `production-proposal.json`;
- `production-budget.json`;
- `production-control.json`.

The manifest also pins the exact Approved Plan trace SHA. Recovery rejects a mixed snapshot set and never auto-repairs it.

This complements, rather than replaces, the existing TASK-037..041 production bundle validator.
