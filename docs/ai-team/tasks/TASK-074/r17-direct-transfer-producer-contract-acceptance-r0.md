# TASK-074 R17 Direct-Transfer Producer Contract Acceptance R0

Status: `OWNER_ACCEPTANCE_CANDIDATE / R17_REVIEW_PENDING / SOURCE_START0 / EFFECT0`

Date: `2026-10-10`

Owner: `TASK-074`

Record type: `TASK074_DIRECT_TRANSFER_V2_PRODUCER_CONTRACT_ACCEPTANCE_V1`

Bound R17 identity:
`TASK074-R17-NONCIRCULAR-OWNER-CONTRACT-LIVE-GATE-V1`

## Accepted contract boundary candidate

TASK-074 accepts, subject to exact-byte independent R17 review, only the
producer boundary below.

1. TASK-074 owns exactly two private reference roles:
   `REFERENCE_AUDIO_READ_HANDLE` then
   `REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`.
2. Both roles are read-only, non-inheritable, non-exportable, one-use and bound
   to one shared lease.
3. Direct transfer is only into the exact selected child-local broker after the
   exact TASK-072 begin and TASK-076 custody sequence.
4. `CHILD_PAIR_READY` requires both child roles verified, both parent originals
   closed with exact readback and `parent_sensitive_handle_count=0`.
5. Partial transfer preserves independent per-role truth and cannot retry,
   reorder, replace a role or create another child.
6. Missing/unknown parent close, reply loss or terminal ambiguity uses only the
   same-operation recovery path and never fabricates success.
7. The exact TASK-075 V2 pre-close/terminal union and bound TASK-014 receipt-only
   fourth argument are required after post-release noncurrentness.
8. Effect-zero producer implementation uses fake/non-biometric ports and cannot
   open a process, private object or sensitive handle.

## Precedence candidate

If R17 and both owner acceptance candidates receive independent Tester/Critic
`Critical/High = 0/0` and Judge `PASS`, the accepted record provides the
contract root for R17-S1. It supersedes only R15's circular requirement for an
already completed TASK-014 live implementation before TASK-074 effect-zero
producer contract work.

It does not authorize TASK074-C live producer binding. Every R17 closed live
prerequisite, owner lock, Allowed File and separate source allocation remains
mandatory.

## Candidate acceptance identity

The final accepted body must bind exact SHA-256 values for:

- R17;
- this frozen acceptance body;
- the TASK-014 consumer acceptance body;
- the current TASK-074 task record;
- `TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2`.

Those hashes are inserted only by a body-preserving administrative update after
fresh independent PASS. Until then this record is not accepted and cannot be
consumed by source.

## Effects and authority

- source allocation: `false`;
- implementation completion: `false`;
- live broker/native/private handle authority: `false`;
- body/model/audio/WAV/publication authority: `false`;
- cross-owner mutation authority: `false`;
- Release/Deploy/Production authority: `false`.
