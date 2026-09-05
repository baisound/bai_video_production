# TASK-073 D4-R4 Candidate Coordinate ABI Amendment

Status: `DESIGN_REVIEW_PENDING / SOURCE_START0`

Base: `origin/main@6fbf8f7bfdbeaf25ea7348c7362978ce51fa8f49`

This is an additive D4-R4 amendment.  D4, D4-R1, D4-R2 and D4-R3 are
immutable historical design Evidence.  This amendment supersedes only the
composition receipt ABI and candidate-binding rules needed to close the
candidate-coordinate omission identified during the current-main source
review.

## 1. ReceiptRefV2 is a new closed ABI

`ReceiptRefV2` replaces `ReceiptRefV1` for the TASK-073 composition.  V1 is
not silently extended or accepted as V2.  Unknown, missing, reordered, or
additional fields are rejected before any derived state is projected.

The exact V2 field order is:

```text
owner_task
receipt_type
schema_version
opaque_ref
receipt_sha256
producer_build_sha256
producer_state
candidate_id
candidate_sha256
project_id
project_manifest_sha256
installed_session_sha256
operation_plan_sha256
quick_clone_flow_sha256
revision
head_sha256
observed_at
expires_at
current
fixture_only
authority_created
production_eligible
```

`candidate_id` is an opaque logical Product candidate-generation identifier.
It uses the existing logical-ID grammar and must never contain a path, URI,
SID, PID, account value, secret, or media body.  `candidate_sha256` is the
exact `sha256:<64 lowercase hex>` digest for the staged WAV bytes.  These bind
respectively to the existing TASK-046 logical candidate / TASK-014
`staged_wav_ref` and TASK-014 `staged_wav_sha256`; TASK-073 does not open,
rehash, infer, or mint either value.

The canonical TASK-046 producer enforces that re-generating identical bytes
creates a new `candidate_id`; its typed terminal receipt is the only evidence
TASK-073 consumes for that invariant.  Retest retains the same non-null
`(candidate_id, candidate_sha256)` pair.  TASK-073 has no predecessor/history
coordinate and therefore neither persists nor reconstructs historical ID
uniqueness.  A bytes digest alone is never a candidate-generation identity.

## 2. Candidate-coordinate applicability

For the two candidate fields, `N` means both fields are required `null`; `R`
means both are required non-null; and `B` means both are null or both are
non-null.  A one-sided pair is invalid.

| Receipt slot | candidate pair |
|---|---|
| installed_session | N |
| quick_clone | ACTIVE=N; RETEST_REQUIRED/ACCEPTED/REJECTED=R; BLOCKED/UNKNOWN=B |
| selection | N |
| reference | N |
| call_profile | N |
| compute_admission | N |
| human_plan | N |
| operation_ticket | N |
| durable_job | N |
| inference | N |
| wav | R |
| qa | R |
| playback | R |
| listening_join | R |

The D4-R1 `producer_state`, P/M/I/O/Q/X coordinate rules, receipt allowlist,
trusted-time rules, fixed 14-slot order, and fixture markers remain unchanged.

## 3. Candidate matching and derived-state closure

The current `quick_clone` terminal pair is the sole candidate coordinate
anchor.  Every non-null pair in `wav`, `qa`, `playback`, and `listening_join`
must match that exact pair.  The pair is also required to match the existing
TASK-014 POST, TASK-048 QA, and TASK-075 playback/final-join receipt chain.
TASK-073 consumes those opaque typed receipts only; it does not reconstruct
candidate authority from raw TASK-041/TASK-046/public playback data.

`WAV_RETEST_REQUIRED`, `WAV_ACCEPTED`, and `WAV_REJECTED` are legal only when
quick-clone plus WAV, QA, playback, and listening-join all carry the same
non-null pair.  For ACCEPTED/REJECTED, quick-clone must be the corresponding
terminal producer state and listening_join must have the same terminal state.
For RETEST_REQUIRED, quick-clone or listening_join may be RETEST_REQUIRED but
the pair remains identical.

Missing pair, one-sided pair, a late null pair, pair mismatch, same digest with
different ID, same ID with different digest, or RETEST with a new ID is
`BLOCKED` with `CANDIDATE_MISMATCH`.  Re-generation ID uniqueness remains a
TASK-046 producer invariant and cannot be re-evaluated from a current-only
TASK-073 read model.  A
multiple-current receipt conflict remains `MULTIPLE_CURRENT_RECEIPTS` and is
evaluated before candidate selection.  No newest, first, retry, fallback, or
candidate inference exists.

The existing TASK-075 `VOICE_QA_LISTENING_BINDING_V1` remains the sole late
join authority.  This amendment creates neither an authority capability nor
an effect.

## 4. Required negative matrix

The source successor must test each of these failures with no Product, media,
model, provider, process, Asset, Timeline, Export, or authority effect:

1. missing one or both candidate fields and any unknown ReceiptRefV2 field;
2. path-like or otherwise invalid candidate ID;
3. same digest / different ID and same ID / different digest across late slots;
4. RETEST with a new ID; TASK-046 owns REGENERATE reused-ID history testing;
5. quick_clone ACTIVE with a non-null pair and a late candidate-bearing null;
6. each quick-clone/WAV/QA/playback/listening pair mismatch;
7. fixture taint, marker relabel, and deterministic self-hash field reordering.

## 5. Bundle and source gate

The R4 bundle is the ordered canonical UTF-8 JSON array of `[name, sha256]`
pairs for D4, D4-R1, D4-R2, D4-R3, this R4 amendment, the successor mock, and
the immutable mock manifest.  Its exact digest and every input digest are
recorded in `design-review-receipt-r4.md`; the review receipt itself is not a
bundle input and therefore cannot be self-minting.

R4 may supersede the R3 source-start authorization only after independent
DEV-4 Critic and Tester report `Critical=0 / High=0` and the independent Judge
returns `PASS`.  Until then, the preserved four-file source carrier remains
uncommitted.  After acceptance, it must fresh-rebind to canonical main and
replace ReceiptRefV1 with ReceiptRefV2 under its already-allocated exact four
source/schema/test files.  This amendment grants no native audio, model,
provider, Asset, Timeline, Export, Release, Deploy, or Production effect.
