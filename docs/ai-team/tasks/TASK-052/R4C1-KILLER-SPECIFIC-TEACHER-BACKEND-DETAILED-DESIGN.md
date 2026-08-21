# TASK-052 R4C1 Killer-specific Teacher Backend Detailed Design

Status: IMPLEMENTATION BOUND

Governance: DEV-3 HIGH ASSURANCE

## Responsibility

R4C1 extends the existing canonical Visual Training manifest and reference-index path with Killer-specific HUD Teacher contracts. It does not create a parallel sample store, mutate real Owner data, add GUI controls, call a Provider or claim production detector accuracy.

## Manifest extension

`KILLER_SPECIFIC_HUD` samples retain the existing image/source/review fields and add:

- exact target `killer_id + effect_id`;
- exact observed `label_namespace`;
- `POSITIVE` or `HARD_NEGATIVE` Teacher role;
- bounded match and Survivor slot identity;
- structured active/stage/progress state.

Positive samples must use the target capability namespace and carry known active state. Hard negatives must use a different namespace and carry no positive state. Other domains reject all Killer-specific fields. New CSV fields are appended; manifests that predate R4C remain readable with empty defaults.

## Capability-bound index

The generic reference-index builder cannot build `KILLER_SPECIFIC_HUD` without an exact R4A Capability Registry. Before any index write it verifies:

- every target is registered;
- every hard-negative namespace is registered for that target;
- stage does not exceed the capability maximum;
- every represented target has at least one positive and one hard-negative sample.

Reference labels use a versioned `KST1` codec containing role, namespace and structured state. Match/source paths remain existing private index provenance; runtime output exposes only the R4B body-free slice Evidence.

## Starter reference detector

`KillerSpecificReferenceDetector` is a deterministic reference/dHash baseline implementing the R4A detector protocol. Low-confidence or ambiguous results remain UNKNOWN. A matched foreign hard-negative namespace is returned unchanged so R4A rejects it before temporal state. This is a testable starter adapter, not a held-out accuracy claim.

## Acceptance

- positive and hard-negative labels round-trip canonically;
- old manifests without new columns remain readable;
- Killer-specific rows round-trip exact namespace, subject and state;
- namespace/scope/role drift is rejected;
- index construction requires Registry binding and safe role coverage;
- positive fixture produces exact structured observation;
- cross-Killer fixture produces `HARD_NEGATIVE_NAMESPACE` UNKNOWN;
- relevant Training Studio/manifest/TASK-052 regression remains green.

## Next boundary

R4C2 wires these fields through Safe Visual Learning preview/confirm, Training Studio controls and Human review. Real-media Gold and packaged Acceptance remain R8/R9 gates.
