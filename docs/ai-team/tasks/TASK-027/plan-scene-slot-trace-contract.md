# TASK-027 / TASK-037 — Plan -> Scene -> Slot Trace Contract

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`

`BlueprintProductionControlCompiler` now compiles graph edges together with Scene Asset Slots:

`PLAN(Blueprint) -> SCENE -> SLOT`

The Blueprint SHA is bound to the PLAN->SCENE dependency edge. Installing a plan registers both Slots and dependency edges in TASK-037. A PLAN stale root therefore propagates through Scene references to dependent Slots, but does not start regeneration automatically.

This closes the upstream half of the R2 traceability target while preserving Human resolution for stale production state.
