# TASK-052 R4B Recorded-video Killer Routing Detailed Design

Status: IMPLEMENTATION BOUND

Governance: DEV-3 HIGH ASSURANCE

## Responsibility

R4B connects the R4A pure Killer Capability Registry to the existing exact-frame recorded-video recognizer. It owns profile-bound ROI slicing, body-free slice Evidence and frame result projection. It does not implement a production classifier, mutate Teacher Data, emit CGEL, call a Provider or claim real-media accuracy.

## Profile and compatibility boundary

The existing calibrated HUD Profile remains canonical:

- `survivor_slots[0..3]` supplies `SURVIVOR_PORTRAIT_OVERLAY` images;
- `killer_power_hud` supplies Killer identity and future global `KILLER_POWER_HUD` capabilities;
- profile resolver and anchor alignment complete before any specific routing.

No parallel ROI store or unnecessary schema version is introduced. When the common Survivor detector already sliced a slot, R4B reuses the exact `GrayImage` and artifact rather than invoking FFmpeg twice.

## Execution order

1. Resolve and align the HUD Profile through the existing path.
2. Run enabled common detectors unchanged.
3. Observe Killer identity from `killer_power_hud` when configured.
4. Ask R4A for the exact required ROI keys. Unknown, low-confidence, power-only and unregistered identities request no Killer-specific overlay slices.
5. Reuse or slice only those admitted keys and bind each to a body-free `recognition://roi-slice/.../sha256:<digest>` Evidence reference.
6. Route through R4A and attach the result to `DBDFrameRecognition.killer_specific`.

Killer-specific routing requires a bounded match identity before any slice. The output remains subject-bound across frames for R3C temporal reconciliation.

## Fail-closed behavior

- missing identity recognizer or identity ROI yields explicit `KILLER_IDENTITY_UNKNOWN` and no specific slice;
- power-only identity never activates a Killer namespace;
- a recognized but unregistered Killer remains explicit UNKNOWN;
- R4A continues to own missing ROI/Evidence, detector failure, namespace mismatch, confidence and semantic validation;
- common Survivor/perk/item/add-on/OCR behavior is independent and backward compatible;
- no local path is persisted in public slice Evidence.

## Acceptance

- known Onryo identity routes four exact Survivor slots;
- common Survivor slices are reused with no duplicate extraction;
- unknown/power-only identity performs only the identity slice and invokes zero specific detectors;
- missing identity capability performs no media read and returns explicit UNKNOWN;
- global Killer-power capability reuses the identity slice;
- legacy recorded-video construction and recognition remain compatible;
- relevant TASK-049/TASK-052 regression remains green.

## Next boundary

R4C connects the namespaced detector/Teacher contract to the Training Studio registration and review route. Real-media calibration, held-out accuracy and packaged Acceptance remain R8/R9 gates.
