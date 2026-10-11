# TASK-014 R24-S3 Coordinated Prearm Allocation

Status: `OWNER_ALLOCATED / DEV-4 / SOURCE_START0 / EFFECT0`

Date: `2026-10-12`

Allocation identity: `TASK014-R24-S3-COORDINATED-PREARM-ALLOCATION-V1`

Owner direction: `all Human Gates approved; execute the bounded source-only R24-S3 Atomic Unit plus coordinated TASK-014/TASK-036/TASK-041/TASK-074 amendments`

Fresh base: `origin/main@9fb74ff88b07597f8d9b06eb7289ef0c2b05d9c1`

## Dependency readback

- R24-S0/S0A/S1/S2 are hosted-closed. R24-S2 merged through PR `#614` as
  `5748203d4e61a6b8c3c3695af0ea4a78e5e1aa04`; its post-main CI and Security
  and external Evidence readback passed.
- TASK-036 exact8 merged through PR `#616` as
  `8063f8037d3757efa4086af929283c91818696bf`.
- TASK-111 merged through PR `#617`; its source commit is
  `24061bd009b0411049ce1fe2d099df1e272740ba`, exact merge/current main is the
  fresh base above, DEV-4 findings are `0/0/0/0`, post-main CI is `6/6
  SUCCESS`, Security is `2/2 SUCCESS`, attempt `1`, rerun `0`, and external
  Evidence was read back.
- Fresh overlap audit: open PR count `0`; non-closed authoritative work-lock
  overlap with the paths below `0`; worktree clean.

TASK-036 exact8 and TASK-111 are serialization predecessors only. Their source,
native/Product surfaces and audit data are not inputs to this effect-zero unit.

## Atomic unit

This allocation selects exactly R24 section 6 stage `R24-S3`: the independent
four-owner coordinated-prearm amendment and effect-zero adapter for runtime
owners `TASK-014`, `TASK-072`, `TASK-075` and `TASK-076`.

The source may model only body-free synthetic metadata and in-memory fake owner
stores. It freezes the accepted amendment identity
`TASK014_TASK072_TASK075_TASK076_COORDINATED_PREARM_RESERVATION_AMENDMENT_V1`,
the TASK-014 reservation machine, the TASK-072 coordinator microstates, the
TASK-076 owner-query variants and the exact terminal join. It does not call or
impersonate a canonical arm, broker, execution consumer or custody owner.

The requested TASK-014/TASK-036/TASK-041/TASK-074 documents are separate
design-owner status amendments. They record the same allocation, exact source
ceiling and later-gate boundary only. They are not runtime-owner receipts and
must never substitute for the exact runtime-owner set
`TASK-014/TASK-072/TASK-075/TASK-076`.

R24-S4, receipt-only prepare/terminal coordination, continuity recovery,
external owner implementations, runtime source and all effects remain outside
this allocation.

## Exact input bindings

- R24 design checkout-byte SHA-256:
  `80A8D48BDF4D7A29D11DF07780CEDDB4D707135D47A8833F616D76BF8B18FFB5`
- R24-S0A review receipt checkout-byte SHA-256:
  `128024E0EF509BA857F5B882363886BFF19BE79FCD569569B48FFFAB292EA9F2`
- TASK-014 acceptance record digest:
  `A398A9FE13F886DC6A4783B2AB3EEAB61721598F20F27ABAC2C0EB2811CBB06B`
- TASK-074 acceptance record digest:
  `8EDDD5E86CD21A779ADBCF889A9478E67520F4E0E48748983D7ABE6F2D710BB0`
- TASK-041 acceptance record digest:
  `AFDDFDF428BB0A98272F20E68CFBE906266218C40D2BFA1955F7ED23480A6853`
- TASK-036 acceptance record digest:
  `78A998DDD65209EBF108755599A1AD755843F022B692277CADD18DD099BE5BAB`
- R24-S1 source checkout-byte SHA-256:
  `B2450071427D2752C4FF381746EE680E1025C8E8BB89AD6FAB1C81EDA4CC2BD3`
- R24-S2 source checkout-byte SHA-256:
  `9F3462E2FDE7CAE5B330888EEAA2A88FA87FFF439B31BC5CB1FDBB3D4204A880`

These hashes are source-eligibility bindings, never runtime values or effect
authority. Equal public mappings, copied objects, historical types and
caller-shaped capabilities are not substitutes for exact issued S3 values.

## Exact Allowed Files

1. `docs/ai-team/tasks/TASK-014/task.md`
2. `docs/ai-team/tasks/TASK-074/task.md`
3. `docs/ai-team/tasks/TASK-014/r24-s3-coordinated-prearm-allocation.md`
4. `docs/ai-team/tasks/TASK-014/r24-s3-coordinated-prearm-design-owner-status-amendment.md`
5. `docs/ai-team/tasks/TASK-036/r24-s3-coordinated-prearm-design-owner-status-amendment.md`
6. `docs/ai-team/tasks/TASK-041/r24-s3-coordinated-prearm-design-owner-status-amendment.md`
7. `docs/ai-team/tasks/TASK-074/r24-s3-coordinated-prearm-design-owner-status-amendment.md`
8. `src/ai_video_production/task014_r24_prearm_adapter.py`
9. `tests/test_task014_r24_prearm_adapter.py`
10. `docs/ai-team/tasks/TASK-014/r24-s3-coordinated-prearm-completion-receipt.md`

No schema is allocated because every positive capability/read is private,
sealed and nonserializable. No existing R24 contract, owner-acceptance envelope,
S1/S2 source, shared registry, CHANGELOG or workflow file may change.

## Required invariants

1. Runtime-owner acceptance is conjunctive across exact closed owner roles
   `TASK-014/072/075/076`; duplicates, missing roles, alternate enums, mappings,
   copied objects and wrong acceptance coordinates fail before mutation.
2. Reservation states are exactly `RESERVED -> CANCEL_PENDING ->
   CANCELLED_KNOWN|CANCEL_UNKNOWN` or `RESERVED -> ARMING -> JOIN_PENDING ->
   ARMED_CONSUMED|ARM_REJECTED|ARM_UNKNOWN`. No other transition exists.
3. Coordinator microstates are exactly `CLAIM_INTENT -> TASK014_CLAIMED ->
   ARM_CALL_ENTERING -> TASK076_RESULT_OBSERVED -> JOINED`. `CLAIM_INTENT`
   exists before the TASK-014 claim.
4. Failure before the TASK-014 claim leaves `RESERVED`; failure after the claim
   but before `ARM_CALL_ENTERING` is exact `NOT_ENTERED_KNOWN`; after call entry,
   missing result is `ATTEMPT_TRUTH_UNKNOWN`, never not-entered.
5. Exact owner-query variants are `NOT_ENTERED_KNOWN`,
   `JOB_CHILD_ARMED_READBACK_V3`, `JOB_CHILD_REJECTED_READBACK_V3`,
   `JOB_CHILD_BURNED_UNKNOWN_READBACK_V3` and `ATTEMPT_TRUTH_UNKNOWN`.
6. Terminal join is one-winner and exact: armed/rejected/burned-unknown map only
   to `ARMED_CONSUMED`/`ARM_REJECTED`/`ARM_UNKNOWN`; cancel known/unknown map
   only to `CANCELLED_KNOWN`/`CANCEL_UNKNOWN`. No terminal is written before its
   sealed owner-query partner exists.
7. The adapter is one-use and burns on first entry, including rejected input;
   concurrent callers have at most one winner. No second arm attempt is
   representable.
8. Exact current reads join the immutable coordinator and fake owner stores.
   Missing, foreign, stale, forked, ambiguous or broken truth is a distinct
   noncurrent result with no retry or authority edge.
9. Every result remains fixture-only with `source_authority=false`,
   `effect_authority=false`, `canonical_runtime_type_minted=false` and zero
   filesystem, Project-store, network, process, private-body, model, Provider,
   audio/WAV, Asset, publication and downstream PASS effects.
10. R24-S3 does not implement R24-S4 prepare continuity, call/sink dispatch,
    real TASK-072/075/076 owner source, runtime issuer or canonical arm/query.

## Acceptance

- focused state-machine, pre/post-entry failure, cancel, query, terminal join,
  replay, concurrency, sealing and current-read tests PASS;
- direct TASK-014 R24 and TASK-074 authority regression PASS;
- `git diff --check` PASS and exact Allowed Files only;
- independent DEV-4 Tester, Critic and Judge review the exact final bytes and
  return PASS with unresolved `Critical/High/Medium/Low = 0/0/0/0`;
- completion receipt and external Evidence are saved, read back and hash
  verified;
- exact commit is normally pushed, Japanese PR checks pass, PR is normally
  merged, and exact post-main checks/Evidence pass.

Until every condition passes, status remains `SOURCE_START0 / EFFECT0`. This
allocation grants no private/native/model/provider/audio/WAV operation,
canonical child/vector/result/publication type, TASK-041 PASS, TASK-036 Gate
PASS, Final Review, Release, Deploy or Production Activation.
