# TASK-027 / TASK-037 — Generation Target Admission Hardening

Before any generation route is considered ready, the target Scene Asset Slot must now:

- exist in Production Control
- belong to the requested Scene
- remain mutable (not LOCKED / STALE)

These checks happen before Provider execution and complement the existing PLAN_APPROVED + FEASIBILITY_PASS + REQUIRED_INPUT_LOCKED + COST_AUTHORIZED admission contract.
