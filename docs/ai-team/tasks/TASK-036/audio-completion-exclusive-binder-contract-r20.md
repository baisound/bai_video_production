# TASK-036 Exclusive AUDIO_COMPLETION Binder Contract R20

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-036`

Contract identity: `TASK036_AUDIO_COMPLETION_EXCLUSIVE_BINDER_CONTRACT_R20_V1`

Bound design: `TASK074-R20-RESERVATION-AND-TAGGED-TERMINAL-CLOSURE-V1`

## Binder boundary

1. `bind_audio_completion_gate_receipt` accepts only the exact private nominal
   `Task041AudioCompletionVerifiedCurrentPassV1`.
2. It rereads canonical TASK-041 owner state and verifies Project, timeline,
   policy, ledger head, owner chain and currentness before creating one bounded
   wrapper.
3. Direct/public `FinalReviewExternalGateReceipt` construction, its generic
   validator, shell/runtime providers, stored legacy receipts, mappings and
   self-hashes cannot inject `AUDIO_COMPLETION`.
4. Canonical gate owner is `TASK-041`. Legacy `DEVELOPER2` remains historical
   read-only data and always noncurrent/non-PASS; no conversion exists.
5. Registry, schema, readiness projection and tests migrate in one separately
   allocated source unit.
6. The binder may be implemented and negative-tested only after the TASK-041
   contract-only class surface. It cannot construct or deserialize a positive
   instance; positive integration waits for the TASK-041 owner reader.
7. The wrapper never reissues, extends or converts TASK-041 authority.

## Acceptance mechanism

This file is immutable. After exact R20 review PASS, only a separately allocated
TASK-036 owner writer may issue
`docs/ai-team/tasks/TASK-036/audio-completion-r20-owner-acceptance.json` under
R20's exact envelope rules.

Until that envelope verifies, contract acceptance, source, generic or typed
`AUDIO_COMPLETION` PASS and every audio/native/provider/Release/Deploy/
Production authority are `false`.
