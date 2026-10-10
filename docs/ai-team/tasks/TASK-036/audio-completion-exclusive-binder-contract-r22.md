# TASK-036 Exclusive AUDIO_COMPLETION Binder Contract R22

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-036`

Contract identity: `TASK036_AUDIO_COMPLETION_EXCLUSIVE_BINDER_CONTRACT_R22_V1`

Bound design: `TASK074-R22-RESTART-SPLIT-AND-REACHABLE-CONTAINMENT-V1`

## Binder boundary

1. `bind_audio_completion_gate_receipt` accepts only exact private nominal
   `Task041AudioCompletionVerifiedCurrentPassV1`.
2. It rereads canonical TASK-041 owner state and verifies Project, timeline,
   policy, ledger head, owner chain and currentness before one bounded wrapper.
3. Direct/public `FinalReviewExternalGateReceipt` construction, generic
   validator, shell/runtime provider, stored legacy receipt, mapping or
   self-hash cannot inject `AUDIO_COMPLETION`.
4. Canonical gate owner is TASK-041. Legacy `DEVELOPER2` is historical read-only
   and always noncurrent/non-PASS; no conversion exists.
5. Registry, schema, readiness projection and tests migrate together in a
   separately allocated source unit.
6. The binder follows the TASK-041 class-only surface and supports negative
   tests without a positive fixture. It cannot construct or deserialize a
   positive instance; positive integration waits for the owner reader.
7. The wrapper never reissues, extends or converts TASK-041 authority.

## Acceptance mechanism

This file is immutable. After exact R22 review PASS, only a separately allocated
TASK-036 owner writer may issue
`docs/ai-team/tasks/TASK-036/audio-completion-r22-owner-acceptance.json` under
R22's exact envelope rules.

Until that envelope verifies, contract acceptance, source, generic or typed
`AUDIO_COMPLETION` PASS and every audio/native/provider/Release/Deploy/
Production authority are false.
