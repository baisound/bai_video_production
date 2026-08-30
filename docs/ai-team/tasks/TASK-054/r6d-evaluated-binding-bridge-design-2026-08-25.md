# TASK-054 R6D EVALUATED Binding Bridge Design

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `BRIDGE_IMPLEMENTED / REAL PROPOSAL NOT ISSUED`

## Responsibility

R6D reuses the R3A tuned-model Registry and converts one exact DRAFT root plus one admitted R6C sealed manifest into the next `EVALUATED` record only. It creates no parallel Registry, schema or activation state.

## Canonical reference boundary

R6C `quarantine_ref` identifies storage/isolation. `base_model_ref` and `adapter_ref` are separately constrained to R3A-compatible `model://registry/...` and `model-adapter://registry/...` coordinates. R6D requires these coordinates and digests to match the DRAFT exactly; it never converts a storage URI implicitly.

## Projection

The next TunedModelBinding carries exact base/adapter, Dataset, recipe, R4D evaluation and rights digests from R6C, retains DRAFT binding identity/locales and clears approval fields. Registry transition is `EVALUATE`; decision Evidence is the exact evaluation digest. Existing R3A chain validation verifies previous digest, revision, immutable coordinates and complete lineage.

## Fail closed

- non-DRAFT input: reject
- artifact/DRAFT model or adapter crossing: reject
- noncanonical/tampered R6C or R3A input: reject
- invalid revision/time/lineage: existing Registry rejects
- resolution attempt while EVALUATED: existing Registry returns no approved binding

The bridge has no APPROVE, route activation or execution function.

## Remaining authority

Fixture tests issue only synthetic records. A real proposal requires actual R6B output and R6C manifest. `APPROVED`, default route, Provider execution and Product activation remain separate Human actions.
