# TASK-036 Exclusive AUDIO_COMPLETION Binder Contract R19

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-036`

Contract identity: `TASK036_AUDIO_COMPLETION_EXCLUSIVE_BINDER_CONTRACT_R19_V1`

Bound design: `TASK074-R19-ACYCLIC-RUNTIME-AND-EXACT-FAILURE-V1`

## Binder boundary

1. `bind_audio_completion_gate_receipt` accepts only the exact private nominal
   `Task041AudioCompletionVerifiedCurrentPassV1`.
2. It rereads canonical TASK-041 owner state and verifies Project, timeline,
   policy, ledger head and currentness before creating a bounded wrapper.
3. Direct/public `FinalReviewExternalGateReceipt` construction, generic
   validators, shell/runtime providers and stored legacy receipts cannot inject
   `AUDIO_COMPLETION`.
4. Canonical gate owner is `TASK-041`. Legacy `DEVELOPER2` remains historical
   read-only data and is always noncurrent/non-PASS; no conversion exists.
5. Registry, schema, readiness projections and tests migrate together.
6. The binder may be implemented and negative-tested after the TASK-041
   contract-only class surface. It cannot fabricate a positive instance;
   positive integration waits for the TASK-041 owner reader.
7. The wrapper never reissues or extends TASK-041 authority.

## Acceptance mechanism

This file is immutable. After exact R19 review PASS, only a separately allocated
TASK-036 owner writer may issue
`docs/ai-team/tasks/TASK-036/audio-completion-r19-owner-acceptance.json` under
R19's stable envelope rules.

Until that envelope verifies: contract acceptance, source, generic or typed
AUDIO_COMPLETION PASS and every audio/native/provider/Release/Deploy/Production
authority are `false`.
