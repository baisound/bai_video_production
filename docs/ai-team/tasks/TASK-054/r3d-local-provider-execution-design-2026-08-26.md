# TASK-054 R3D Local Provider Execution Design

Date: `2026-08-26`

Status: `BOUND_FOR_IMPLEMENTATION`

Development depth: `DEV-3 HIGH ASSURANCE`

## Goal

Execute one explicitly authorized, current R3B DbD tuned-commentary route through the existing canonical Provider stack and strict R2A parser. The first bounded integration supports a local, free, credential-free runtime only. It creates body-free attempt Evidence and never approves, promotes, trains, adopts a Dataset row, or activates a Binding.

## Canonical ownership

- R3A remains tuned Binding lifecycle/latest/revocation owner.
- R3B remains current Binding/Profile/route resolution owner.
- `AiConnectionResolver` remains the only route selector.
- `AiProviderExecutionService` and `TextProviderAdapter` remain the Provider execution boundary.
- `DbDReasoningProposalParser` remains raw-output structural admission owner.
- `DbDReasoningExecutionReceipt` remains the body-free attempt Evidence owner.
- R3D owns only exact execution authorization admission, local-runtime artifact attestation, one bounded dispatch, and receipt construction.

No second Provider resolver, credential store, Binding registry, Candidate Store, Dataset Store, validator, or Product entrypoint is introduced.

## Execution authorization

`DbDReasoningExecutionAuthorization` is a body-free, checksum-protected record that binds:

- one authorization ID and non-secret authority Evidence digest;
- one exact R3B route-decision digest;
- one binding ID/revision/checksum;
- `PREVIEW_NO_LEARNING` only for this slice;
- a UTC validity interval;
- one attempt maximum, zero cost, and a bounded output-token ceiling;
- fixed state `ALLOWED_SINGLE_LOCAL_PREVIEW`.

The authorization is Evidence, not a credential. A required verifier must trust its authority Evidence digest. Every execution exact-admits the record, verifies the current time window, re-runs R3B validate_current, and checks all coordinates again. A required authorization-use Store must atomically claim the authorization digest immediately before dispatch; a missing Store or repeated claim fails closed. The service exposes no fallback or retry.

## Local adapter contract

The canonical `TextProviderAdapter` implementation accepts only:

- `ProviderFamily.LOCAL_OPEN_SOURCE`;
- Provider ID `local-runtime`;
- planning workload and `DBD_TUNED_COMMENTARY_REASONING` capability;
- local-free cost, no credential, and no endpoint;
- exact R3A binding pin plus base-model and adapter SHA-256 pins in route settings.

The injected local runtime returns text/token metrics and the base-model/adapter digests actually loaded. The adapter rejects digest crossing before returning output. Host paths, model bodies, adapter bodies, secrets and raw runtime logs never enter the public result.

## Dispatch and receipt

1. Exact-admit authorization and current UTC time.
2. Revalidate the R3B decision against current Registry/Profile/availability.
3. Resolve the same route through `AiProviderExecutionService` using the exact DbD capability.
4. Require an APPROVED binding and exact route artifact pins.
5. Dispatch one bounded request; no fallback or retry.
6. Verify returned route/provider/model and artifact attestation.
7. Pass raw UTF-8 bytes directly to R2A; retain only digest and parsed quarantine.
8. Recheck preview snapshot equality.
9. Create a `DbDReasoningExecutionReceipt` with zero cost, no learning, no state mutation, no fact/policy approval and fail-closed final disposition.

## Failure behavior

- forged, stale, expired, not-yet-valid or crossed authorization: reject before runtime;
- revoked/suspended/stale binding or changed Profile/availability: reject before runtime;
- cloud/paid/credentialed/endpoint route: reject in this local slice;
- missing/mismatched base or adapter digest attestation: reject output;
- malformed/oversized output: R2A quarantine failure, not retry;
- Dataset/Binding/training-count drift: reject receipt and output;
- runtime error, cancellation, timeout or resource limit: no fabricated PASS or fallback.

## Allowed files

- `src/ai_video_production/provider_execution.py`
- `src/ai_video_production/dbd_reasoning_execution.py`
- execution-authorization schema and packaged mirror
- `tests/test_task054_dbd_reasoning_execution.py`
- `tests/test_task028_provider_execution.py` only if canonical service coverage requires it
- this design and bounded TASK-054 state/evidence at completion

Must not modify credentials, Registry lifecycle, R3B resolver semantics, Dataset/training, Candidate/Human review, Timeline/TTS, release, deployment, or Product activation.

## Acceptance

- current route is resolved only by existing canonical services;
- exact one-shot local preview authorization is checksum/time/binding/route bound;
- real artifact digest attestation is enforced;
- raw output is not retained outside the existing structural quarantine;
- receipt proves preview Dataset/Binding/training state is unchanged;
- stale/revoked/crossed/paid/credentialed/malformed cases fail closed;
- no fallback, retry, training, promotion, activation or secret surface exists;
- focused R3D/R3B/R2A/Provider and TASK-054 direct regressions pass;
- unresolved Critical/High findings are `0 / 0`.
