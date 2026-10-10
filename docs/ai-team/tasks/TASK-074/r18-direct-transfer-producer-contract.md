# TASK-074 R18 Direct-Transfer Producer Contract

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-10`

Owner: `TASK-074`

Contract identity: `TASK074_DIRECT_TRANSFER_V2_PRODUCER_CONTRACT_R18_V1`

Bound sequencing design: `TASK074-R18-STABLE-ACCEPTANCE-SPLIT-GATES-V1`

## Contract boundary

1. TASK-074 owns exactly two private roles, in order:
   `REFERENCE_AUDIO_READ_HANDLE` then
   `REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`.
2. Both roles are read-only, non-inheritable, non-exportable, one-use and bound
   to one shared TASK-074 V2 lease.
3. Transfer occurs only after the exact TASK-072 attachment begin, selected
   TASK-076 V3 `IN_FLIGHT`, bootstrap child creation and exact child/process/Job
   custody readbacks defined by R18.
4. `CHILD_PAIR_READY` requires both roles accepted by the exact child-local
   broker, both parent originals closed with exact readback and
   `parent_sensitive_handle_count=0`.
5. Partial transfer preserves per-role accepted/closed truth and cannot retry,
   reorder, replace a role or create another child.
6. Missing or unknown parent close, reply loss or terminal ambiguity permits
   only same-operation recovery and never fabricated success.
7. TASK-074 lease unknown truth remains `FAILED_CLOSED / NOT_CONFIRMED` and
   non-retireable under R13. It is never renamed `BURNED_UNKNOWN`.
8. Effect-zero implementation uses fake/non-biometric ports and cannot open a
   process, private object or sensitive handle.
9. TASK-074 `OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_V1` is implemented only
   over the TASK-043-owned
   `TASK043_OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_PORT_V1` and consumes its
   exact `TASK043_OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_READBACK_V1`.
   TASK-043 never mints the TASK-074 domain transaction.

## Acceptance mechanism

This file is an immutable contract body. Review or acceptance must never edit
it. After exact-byte R18 Tester/Critic/Judge PASS, a separately allocated
TASK-074 owner writer may issue only:

`docs/ai-team/tasks/TASK-074/r18-owner-acceptance.json`

The envelope format, digest rule, predecessor binding and readback sequence are
defined by R18 section 4. Until that distinct envelope exists and verifies, no
TASK-074 R18 source unit may consume this contract.

## Authority ceiling

- contract acceptance: `not issued`;
- source allocation: `false`;
- live broker/native/private handle/body authority: `false`;
- model/audio/WAV/publication authority: `false`;
- cross-owner mutation authority: `false`;
- Release/Deploy/Production authority: `false`.
