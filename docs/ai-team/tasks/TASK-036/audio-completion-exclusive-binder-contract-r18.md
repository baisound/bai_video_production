# TASK-036 Exclusive AUDIO_COMPLETION Binder Contract R18

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-10`

Owner: `TASK-036`

Contract identity: `TASK036_AUDIO_COMPLETION_EXCLUSIVE_BINDER_CONTRACT_R18_V1`

Bound sequencing design: `TASK074-R18-STABLE-ACCEPTANCE-SPLIT-GATES-V1`

## Contract boundary

1. `bind_audio_completion_gate_receipt` accepts only the exact private nominal
   `Task041AudioCompletionVerifiedCurrentPassV1`.
2. The binder reparses the canonical TASK-041 owner state through the TASK-041
   reader and verifies Project, timeline, ledger head, policy and currentness.
3. Public or direct `FinalReviewExternalGateReceipt` construction for
   `AUDIO_COMPLETION` is rejected.
4. Generic external-gate providers, shell/runtime providers and stored legacy
   receipts cannot inject `AUDIO_COMPLETION`.
5. The canonical gate owner becomes `TASK-041`. Legacy owner `DEVELOPER2` is
   historical read-only data and is never accepted or migrated into current
   PASS. Gate registry, schema and readiness projections must move together.
6. The binder may be implemented and negative-tested after the TASK-041
   contract-only nominal type surface exists. It cannot fabricate a positive
   instance for tests. Positive integration waits for the later TASK-041 owner
   reader to mint a real current PASS.
7. The wrapper does not reissue TASK-041 authority and cannot outlive or detach
   from the exact canonical TASK-041 readback.

## Acceptance mechanism

This immutable body is accepted only through the separate future envelope:

`docs/ai-team/tasks/TASK-036/audio-completion-r18-owner-acceptance.json`

The envelope follows R18 section 4 and cannot edit this file. Until it verifies,
the binder source unit is not eligible.

## Authority ceiling

- contract acceptance: `not issued`;
- source allocation: `false`;
- generic or typed AUDIO_COMPLETION PASS: `false`;
- audio/native/provider/Release/Deploy/Production authority: `false`.
