# TASK-052 R4A Killer Capability Registry Detailed Design

Status: IMPLEMENTATION BOUND

Governance: DEV-3 HIGH ASSURANCE

## Responsibility

R4A owns the pure, detector-independent routing boundary between an observed Killer identity and Killer-specific HUD observations. It does not crop recorded video, implement a production image classifier, mutate Teacher Data, emit CGEL, call a Provider or claim current-game catalog completeness or real-media accuracy.

## Canonical capability contract

Each capability binds one exact `killer_id + effect_id` to:

- effect family and required ROI family;
- detector type and Survivor/global scope;
- stage/progress semantics;
- one exact `KILLER_SPECIFIC_HUD/<killer>/<effect>` training namespace;
- sorted cross-Killer hard-negative namespaces;
- state-Evidence or future CGEL projection.

The initial design fixtures cover Ghost Face mark progress, Onryo Condemn and Doctor Madness around Survivor portraits. They are bounded contract fixtures, not an assertion that the live Killer/effect catalog or detector accuracy is complete.

## Fail-closed routing

- Killer identity must be a `KILLER` observation at or above the registry threshold. Unknown, low-confidence and power-only identity observations invoke no Killer-specific detector.
- A recognized Killer routes only its exact registered capabilities. Common detectors remain outside this registry and continue independently.
- Missing ROI, missing ROI Evidence, missing detector, detector failure, low-confidence output, impossible stage and runtime label-namespace mismatch produce explicit UNKNOWN observations.
- Detector output must repeat the exact capability training namespace. Another Killer/effect namespace is a hard negative and can never fall through as a generic circular-progress positive.
- Survivor-scoped capabilities preserve slots `0..3`; records retain match, frame, Evidence reference, selected capability and deterministic reason code.

## Temporal boundary

Accepted route observations use the R3C `KillerSpecificObservation` contract. R3C remains responsible for hysteresis, contradiction recovery and stable effect state. R4A does not bypass that temporal layer and does not emit gameplay events directly.

## Acceptance

- unknown, low-confidence and power-only identity invoke zero Killer-specific detectors;
- an exact Killer invokes only its own registered detector across exact Survivor slots;
- unregistered Killer and unavailable inputs remain explicit UNKNOWN;
- cross-Killer runtime namespace and impossible stage abstain;
- exact ROI Evidence is mandatory;
- routed observations pass R3C temporal confirmation without cross-namespace fallback;
- relevant TASK-052 regression remains green.

## Next boundary

R4B may add profile-bound ROI slicing and recorded-video orchestration over this contract. It must preserve common-detector independence, exact Evidence references and the same fail-closed routing rules.
