# TASK-004 — Judge Record

## Decision

`CAPABILITY_EVIDENCE_ACCEPTED / APPROVED_FOR_BOUNDED_BEHAVIORAL_EVIDENCE / NOT_COMPLETED`

## Basis

- Owner explicitly authorized the expanded TASK-004 implementation scope.
- Internal detailed design and failure-mode design existed before the corresponding implementation changes.
- DEV-4 Critic blocking findings are resolved.
- Local regression is 247/247 PASS; compileall/diff-check and prior installed-wheel golden normalization remain PASS.
- External-runtime absence is represented as fail-closed diagnostic Evidence rather than a fabricated capability PASS.

## Accepted live capability Evidence

1. target Windows ComfyUI capability Evidence: **ACCEPTED**;
2. target Audacity/OpenVINO capability Evidence: **ACCEPTED** on Attempt 05; all five bounded OpenVINO effects are live-reachable and current track count is zero;
3. live runtime descriptors expose no OpenVINO script parameters, which narrows rather than expands the executable claim.

## Remaining completion gates

1. bounded synthetic behavioral Evidence for OpenVINO Noise Suppression;
2. bounded synthetic behavioral Evidence for the verified-runtime 2-stem Music Separation default;
3. DEV-4 review of returned outputs/manifests/Evidence;
4. final canonical document synchronization and final `COMPLETED` Judge decision.

Verified-runtime 4-stem Music Separation is not a completion blocker because it is now explicitly classified `NOT_SCRIPTABLE_ON_VERIFIED_RUNTIME`; TASK-004 must not claim it as live-supported.

Optional provider absence (for example Spectrum or H3 SingleFrame) may remain `NOT_VERIFIED` and does not by itself invalidate the core Adapter implementation. Any provider-specific capability claimed as available must be supported by target-machine Evidence.
