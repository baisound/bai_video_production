# TASK-073 D4-R2 Final Gate Closure

## 1. Identity and precedence

- Base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`
- Parent D4 hash:
  `975A5ABBB4471FA3E618C47A35E5EFED02960A1524657AC910290C25CA5739A1`
- Parent D4-R1 hash:
  `A764C4DC49F51C198DFAAF6C038C0C7644BDB9B7B6AD1286326E49E3E5B409AA`
- State: `DESIGN_REVIEW_PENDING / SOURCE_START0`

This addendum supersedes only D4-R1 sections 4.1 and 6 and augments D4-R1
section 3 reason codes and the D4/task TASK-036 Gate.  Every other D4 and
D4-R1 clause remains in force.

## 2. Operation-plan coordinate timing

Top-level `operation_plan_sha256` is required null through
`READY_TO_RENDER`.  It becomes required non-null at
`CONFIRMATION_REQUIRED`, where it is obtained from the current G4
`call_profile` and `compute_admission` pair.  Both G4 ReceiptRefs carry the
same required O coordinate.  It remains required and exact for all later
states.

No G0 through G3 receipt supplies or implies an operation plan.  A non-null
top-level operation plan before G4, a G4 pair with unequal operation plans, or
any later receipt with a different plan is
`BLOCKED/OPERATION_MISMATCH`.  Raw caller text cannot supply this coordinate.

## 3. Closed execution reason codes

`TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1.reason_codes` is a sorted unique tuple
of one to four values for non-success and empty for success.  Its complete
closed enum is:

```text
PRE_SPAWN_ADMISSION_REJECTED
SANDBOX_START_FAILED
NETWORK_ISOLATION_FAILED
WORKER_PROTOCOL_FAILED
MODEL_LOAD_FAILED
RESOURCE_LIMIT_EXCEEDED
INFERENCE_FAILED
INVALID_WAVEFORM
SINK_WRITE_FAILED
SINK_VERIFY_FAILED
EXECUTION_OUTCOME_UNKNOWN
SINK_COMMIT_OUTCOME_UNKNOWN
```

The two `*_UNKNOWN` values are legal only with the exact UNKNOWN stages fixed
by D4-R1.  They are illegal for `FAILED_KNOWN`.  Every other code is legal only
for `FAILED_KNOWN` at the earliest compatible terminal stage; a code that
claims an effect later than `terminal_stage` is rejected.  Unknown, additional,
duplicate or unsorted values reject the result.

## 4. Fixture and production eligibility

D4-R1's fixture total function is unchanged except for this exact rule:

`production_eligible=true` is possible only for `WAV_ACCEPTED`.  It requires
all 14 receipts present/current/real/individually production-eligible, matching
G12 `ACCEPTED`, and an empty reason tuple.  `WAV_REJECTED`,
`WAV_RETEST_REQUIRED`, all incomplete states and every failure state always
have `production_eligible=false`.  A verified rejection remains valid Evidence
through `derived_state=WAV_REJECTED`; it never makes the WAV usable.

## 5. TASK-036 and canonical handoff identity

The accepted design bundle is the canonical UTF-8 JSON array, in this order:

```text
[
  ["task073_d4", "975A5ABBB4471FA3E618C47A35E5EFED02960A1524657AC910290C25CA5739A1"],
  ["task073_d4_r1", "A764C4DC49F51C198DFAAF6C038C0C7644BDB9B7B6AD1286326E49E3E5B409AA"],
  ["task073_d4_r2", "SELF_SHA256_EXCLUDED_FROM_PREIMAGE"],
  ["voice_studio_mock", "DAD0C3BDD4325693EB198F9C59EE520643CE9111C3527B96E2969FC868BA50FA"],
  ["voice_studio_manifest", "84FE88BD6C2448B35820B8BB19BB3B47B2353E65858C40609ECF0527DA7DA1C8"]
]
```

At freeze, the R2 row is replaced by this file's exact SHA-256 and the full
array hash is recorded in the review receipt.  The literal placeholder above
is not an accepted runtime or handoff value.

`TASK073_IMPLEMENTATION_COMPLETE` and the versioned composition fixture carry
that exact `design_bundle_sha256`.  The separate TASK-036 P0-V Atomic Unit may
start only after the task, D4, R1, R2, mock and manifest are merged to
canonical main, hosted checks pass, fresh-main bytes reproduce every hash, the
Owner check binds the same mock/manifest, and its Allowed Files/lock is current.

`TASK036_P0V_INTEGRATION_COMPLETE` must bind the same design bundle,
`TASK073_IMPLEMENTATION_COMPLETE` receipt and packaged synthetic readback.
Failed D4-R0 or D4-R1 alone, an open PR, caller-provided hashes or a rehashed
subset cannot satisfy the Gate.

## 6. Review gate

Product and TASK-036 P0-V source remain `SOURCE_START0` until the exact task,
D4, R1, R2, mock and manifest inputs receive independent DEV-4
`Critical=0 / High=0` and Judge `PASS`.  This design does not authorize real
Owner audio, model download, Asset adoption, Export, Release, Deploy or
Production Activation.
