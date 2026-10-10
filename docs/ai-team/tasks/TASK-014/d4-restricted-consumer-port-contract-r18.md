# TASK-014 D4 Restricted Consumer Port Contract R18

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-10`

Owner: `TASK-014`

Contract identity: `TASK014_D4_RESTRICTED_CONSUMER_PORT_CONTRACT_R18_V1`

Bound sequencing design: `TASK074-R18-STABLE-ACCEPTANCE-SPLIT-GATES-V1`

## Contract boundary

1. The cross-owner contract is
   `TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2`.
2. TASK-074 owns the two-role private-reference producer and direct transfer to
   the selected child-local broker.
3. TASK-014 parent sensitive-handle authority is permanently `0`.
4. TASK-014 exposes no reference-open, body-return, map, hash, copy, callback,
   path, URI, serialization or reconstructed-accessor surface.
5. The effect-zero consumer accepts only the nominal current
   `Task074DirectTransferProducerEffectZeroV1`; it cannot invoke a child, body
   read, model, sink or publication effect.
6. The live call/sink path accepts only
   `Task074DirectTransferLiveBoundCurrentV1` after every R18 live-mint row is
   current for the same Project, operation and child.
7. TASK-014 alone owns the body-free POST contract, append-only Project history,
   publication write/readback and latest/current result.
8. Effect-zero work cannot mint `PUBLISHED_READBACK_VERIFIED`, a real
   `NarrationPublicationReceipt`, Asset authority, TASK-041 PASS or TASK-036
   AUDIO_COMPLETION PASS.

## Acceptance mechanism

This file is an immutable contract body. Review or acceptance must never edit
it. After exact-byte R18 Tester/Critic/Judge PASS, a separately allocated
TASK-014 owner writer may issue only:

`docs/ai-team/tasks/TASK-014/d4-r18-owner-acceptance.json`

The envelope format, digest rule, predecessor binding and readback sequence are
defined by R18 section 4. Until that distinct envelope exists and verifies, no
TASK-014 source unit may consume this contract.

## Authority ceiling

- contract acceptance: `not issued`;
- source allocation: `false`;
- private handle/body/process/model/audio/WAV/publication authority: `false`;
- TASK-041/TASK-036 PASS authority: `false`;
- Release/Deploy/Production authority: `false`.
