# TASK-014 D4 Restricted Consumer Port Contract Acceptance R0

Status: `OWNER_ACCEPTANCE_CANDIDATE / R17_REVIEW_PENDING / SOURCE_START0 / EFFECT0`

Date: `2026-10-10`

Owner: `TASK-014`

Record type: `TASK014_D4_RESTRICTED_CONSUMER_PORT_CONTRACT_ACCEPTANCE_V1`

Bound R17 identity:
`TASK074-R17-NONCIRCULAR-OWNER-CONTRACT-LIVE-GATE-V1`

## Accepted contract boundary candidate

TASK-014 accepts, subject to exact-byte independent R17 review, only the
contract-level consumer boundary below.

1. The cross-owner contract is exactly
   `TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2`.
2. TASK-074 owns the two-role private-reference producer and direct child-local
   transfer.
3. TASK-014 parent sensitive-handle authority is permanently `0`.
4. TASK-014 exposes no reference-open, body-return, map, hash, copy, callback,
   path, URI, serialization or reconstructed-accessor surface.
5. An effect-zero consumer implementation may accept only the nominal current
   `Task074DirectTransferProducerEffectZeroV1` type and cannot invoke a child,
   body read, model or publication effect.
6. A live call/sink implementation may begin only after the exact nominal
   `Task074DirectTransferLiveBoundCurrentV1` plus every R17 closed live
   prerequisite is current.
7. TASK-014 alone owns the POST contract, publication write/readback, append-only
   Project history and latest/current read result.
8. Effect-zero work cannot mint `PUBLISHED_READBACK_VERIFIED`, a real
   `NarrationPublicationReceipt`, Asset authority, TASK-041 PASS or TASK-036
   Gate PASS.

## Precedence candidate

If R17 and both owner acceptance candidates receive independent Tester/Critic
`Critical/High = 0/0` and Judge `PASS`, the accepted record supersedes only the
old TASK-014 D4 source-start requirement that demanded TASK-074 implementation
completion before the restricted consumer/POST effect-zero contract unit.

It does not supersede or weaken the live TASK-074 completion requirement for
real call/sink execution or POST minting. The preserved D4 carrier remains
historical design input and creates no source authority.

## Candidate acceptance identity

The final accepted body must bind exact SHA-256 values for:

- R17;
- this frozen acceptance body;
- the TASK-074 producer acceptance body;
- the current TASK-014 task record;
- `TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2`.

Those hashes are inserted only by a body-preserving administrative update after
fresh independent PASS. Until then this record is not accepted and cannot be
consumed by source.

## Effects and authority

- source allocation: `false`;
- implementation completion: `false`;
- private handle/body authority: `false`;
- process/model/audio/WAV/publication authority: `false`;
- TASK-041/TASK-036 PASS authority: `false`;
- Release/Deploy/Production authority: `false`.
