# TASK-073 D4-R1 Mechanical ABI Closure

## 1. Identity and precedence

- Base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`
- Parent packet SHA-256:
  `975A5ABBB4471FA3E618C47A35E5EFED02960A1524657AC910290C25CA5739A1`
- State: `DESIGN_REVIEW_PENDING / SOURCE_START0`

This addendum is read with the frozen D4 packet.  It supersedes only D4
sections 1 sentence 2, 4.1 field order, 6 nullability, and 9.1 through 9.4.
All other D4 clauses remain unchanged.  D4's phrase `three completion results`
is corrected to `four exact result classes`.

## 2. Call-profile field closure

`LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2` inserts these two required fields
immediately after `profile_revision`, in this exact order:

```text
route_mode
intended_usage
```

`route_mode` is exactly `ZERO_SHOT_LOCAL`; `intended_usage` is exactly
`PREVIEW`.  They are included in `profile_sha256` at that position.  Missing,
null, additional, reordered or different values reject the profile.  A V1
record cannot be relabelled or rehashed as V2.

## 3. Execution-result terminal-stage matrix

`TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1` inserts required non-null
`terminal_stage` immediately before `outcome`.  Its closed enum is:

```text
PRE_SPAWN
CHILD_CREATED
GENERATION_DISPATCHED
WAVEFORM_OBSERVED
SINK_WRITE_ATTEMPTED
SINK_WRITE_COMMITTED
RESULT_VERIFIED
```

The identity/binding fields from `schema` through `sandbox_profile_sha256`,
the planned `engine_revision_sha256`, `model_artifact_sha256`,
`runtime_sha256`, `effective_backend`, both count fields, `terminal_stage`,
`outcome`, flags and `result_sha256` are always non-null.  Counts are integers,
never null.  `completed_at` is the trusted observation time even for failure.

The remaining fields use this exact matrix.  `R` means required non-null and
`N` means required null.

| terminal_stage | network receipt | child | attempts | waveform count | format/frame/wave hash | sink result | output handle |
|---|---:|---:|---:|---:|---|---|---|
| PRE_SPAWN | N | 0 | 0 | 0 | N | N | N |
| CHILD_CREATED | R | 1 | 0 | 0 | N | N | N |
| GENERATION_DISPATCHED | R | 1 | 1 | 0 | N | N | N |
| WAVEFORM_OBSERVED | R | 1 | 1 | 1 | R | N | N |
| SINK_WRITE_ATTEMPTED | R | 1 | 1 | 1 | R | N | N |
| SINK_WRITE_COMMITTED | R | 1 | 1 | 1 | R | R | R |
| RESULT_VERIFIED | R | 1 | 1 | 1 | R | R | R |

`format/frame/wave hash` is the tuple `sample_rate_hz, channels,
sample_format, frame_count, waveform_sha256`; it is all-R or all-N.
`waveform_count` is always `0|1`.  A count greater than one rejects the result.

- `SUCCESS` is legal only at `RESULT_VERIFIED`, with the D4 success format and
  empty reasons.
- `FAILED_KNOWN` is legal at any stage, requires at least one closed reason and
  may not claim a field marked N.
- `UNKNOWN` is legal only at `GENERATION_DISPATCHED` or
  `SINK_WRITE_ATTEMPTED`; it requires `EXECUTION_OUTCOME_UNKNOWN` or
  `SINK_COMMIT_OUTCOME_UNKNOWN` respectively and forbids automatic retry.
- `SINK_WRITE_COMMITTED` followed by a verification error is
  `FAILED_KNOWN`, not `UNKNOWN`; exact sink reconciliation is required.

No range wording from D4 section 6 overrides this matrix.

## 4. Composition wrapper V4-R1

### 4.1 Top-level nullability

The D4 top-level field order is unchanged.  `project_id`,
`project_manifest_revision` and `project_manifest_sha256` are always required.
`installed_session_sha256` is null only in `SETUP_REQUIRED` and required in
every later state.  `operation_plan_sha256` is null through
`MODEL_SELECTION_REQUIRED` and required from `READY_TO_RENDER` onward.
All other top-level fields are required.  `composition_revision` is positive;
`parent_composition_sha256` is null only at revision 1.

### 4.2 ReceiptRef field delta and fixed state vocabulary

`ReceiptRefV1` inserts required `producer_state` immediately after
`producer_build_sha256`.  It is included in the composition preimage.  The
allowed value is fixed by slot:

| slot | producer_state enum |
|---|---|
| installed_session | READY, BLOCKED, UNKNOWN |
| quick_clone | ACTIVE, RETEST_REQUIRED, ACCEPTED, REJECTED, BLOCKED, UNKNOWN |
| selection | SELECTED, BLOCKED, UNKNOWN |
| reference | PREPARED_VERIFIED, BLOCKED, UNKNOWN |
| call_profile | READY_FOR_TASK075_DISPATCH, BLOCKED, UNKNOWN |
| compute_admission | ADMITTED, BLOCKED, UNKNOWN |
| human_plan | CONFIRMATION_REQUIRED, CONFIRMED, BLOCKED, UNKNOWN |
| operation_ticket | ISSUED, CONSUMED, BURNED, BLOCKED, UNKNOWN |
| durable_job | QUEUED, DISPATCHING, RUNNING, RECOVERY_REQUIRED, SUCCEEDED, FAILED_KNOWN, UNKNOWN |
| inference | SUCCESS, FAILED_KNOWN, UNKNOWN |
| wav | PUBLISHED_READBACK_VERIFIED, FAILED_KNOWN, UNKNOWN |
| qa | PASS, FAIL, UNKNOWN |
| playback | READY, PLAYING, COMPLETED, STOPPED, FAILED_KNOWN, UNKNOWN |
| listening_join | ACCEPTED, REJECTED, RETEST_REQUIRED, BLOCKED, UNKNOWN |

### 4.3 Slot coordinate applicability

For the table below, P/M/I/O/Q/X mean `project_id`,
`project_manifest_sha256`, `installed_session_sha256`,
`operation_plan_sha256`, `quick_clone_flow_sha256`, and `expires_at`.
`R` is required non-null and exact-match; `N` is required null.  `revision`,
`head_sha256`, `observed_at`, `current` and the three fixture/authority flags
are required for every non-null slot.

| slot | P | M | I | O | Q | X |
|---|---:|---:|---:|---:|---:|---:|
| installed_session | R | R | R | N | N | N |
| quick_clone | R | R | R | N | R | N |
| selection | R | R | R | N | R | N |
| reference | R | R | R | N | R | R |
| call_profile | R | R | R | R | R | R |
| compute_admission | R | R | R | R | R | R |
| human_plan | R | R | R | R | R | R |
| operation_ticket | R | R | R | R | R | R |
| durable_job | R | R | R | R | R | R |
| inference | R | R | R | R | R | N |
| wav | R | R | R | R | R | N |
| qa | R | R | R | R | R | N |
| playback | R | R | R | R | R | N |
| listening_join | R | R | R | R | R | N |

All R values match the top-level coordinate or, for Q, the current
`quick_clone` head.  All non-null slots have `current=true`; an X value is
checked against trusted time.  No field is inferred from another slot.

## 5. Deterministic progression and state function

Non-null receipts must form this prefix.  The two members of G4 are atomic and
G12 requires the already-current quick-clone slot to carry the same decision.

```text
G0 installed_session
G1 quick_clone
G2 reference
G3 selection
G4 call_profile + compute_admission
G5 human_plan
G6 operation_ticket
G7 durable_job
G8 inference
G9 wav
G10 qa
G11 playback
G12 listening_join + matching quick_clone decision
```

A later group present while an earlier group is absent, one half of G4, or a
non-matching G12 is `BLOCKED/MISSING_REQUIRED_RECEIPT`; it is never skipped or
filled from caller data.

After schema, coordinate, currentness, conflict and prefix validation, derive
exactly one state using the first matching rule below:

1. Any producer `BLOCKED|BURNED|FAILED_KNOWN|FAIL`, invalid wrapper, mismatch,
   expiry or multiple-current condition -> `BLOCKED`.
2. Matching G12 `ACCEPTED|REJECTED` and quick-clone terminal state ->
   `WAV_ACCEPTED|WAV_REJECTED`.
3. Either quick-clone or listening-join `RETEST_REQUIRED`, with candidate
   bindings exact -> `WAV_RETEST_REQUIRED`.
4. Any required producer `UNKNOWN` -> `UNKNOWN`.
5. Durable job `RECOVERY_REQUIRED` -> `RECOVERY_REQUIRED`.
6. G10 `qa=PASS` and G12 absent -> `LISTENING_REQUIRED`; playback may be
   absent, READY, PLAYING, STOPPED or COMPLETED.
7. G9 present and G10 absent -> `QA_REQUIRED`.
8. G8 `inference=SUCCESS` and G9 absent -> `RUNNING` for bounded TASK-014 POST
   finalization.
9. Durable job `DISPATCHING|RUNNING` -> `RUNNING`.
10. G6 present and G7 absent, or durable job `QUEUED` -> `QUEUED`.
11. G4 present and G6 absent -> `CONFIRMATION_REQUIRED`; G5 may be absent or
    `CONFIRMATION_REQUIRED|CONFIRMED`, but a confirmed plan without a ticket
    remains confirmation-required and cannot execute.
12. G0 through G3 present and G4 absent -> `READY_TO_RENDER`.
13. G0 through G2 present and G3 absent -> `MODEL_SELECTION_REQUIRED`.
14. G0 present and either G1 or G2 absent -> `REFERENCE_REQUIRED`.
15. G0 absent -> `SETUP_REQUIRED`.

`durable_job=SUCCEEDED` requires G8; `operation_ticket=CONSUMED` requires G7;
contradictory terminal/prefix combinations are BLOCKED.  No newest, retry,
fallback or inferred producer state exists.

## 6. Fixture-lineage total function

For all compositions, `authority_created=false` because TASK-073 is a
non-authoritative read model.

- `fixture_only` is true iff any non-null slot has `fixture_only=true`.
- `producer_fixture_count` counts every non-null slot where any of
  `fixture_only=true`, `authority_created=false`, or
  `production_eligible=false`.
- `fixture_set_sha256` is SHA-256 of canonical JSON array entries
  `[slot, receipt_sha256]` for those slots in the fixed 14-slot order.  With no
  such slot it is the SHA-256 of canonical UTF-8 JSON `[]`; it is never null.
- `production_eligible=true` only for `WAV_ACCEPTED|WAV_REJECTED` when all 14
  slots are present, current, real, individually production-eligible and no
  reason code exists.  Every empty or partial composition is false.

This total function is applied before `composition_sha256`; marker removal,
mixing and relabelling remain blocked.

## 7. Review and source gate

The frozen D4 mock already closes terminal decision replay and Stop reset and
is unchanged by this ABI addendum.  Product source remains `SOURCE_START0`
until the exact task, D4, this addendum, mock and manifest identities receive
independent DEV-4 `Critical=0 / High=0` and Judge `PASS`.
