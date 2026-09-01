# TASK-073 D4-R3 Final Mechanical Closure

## 1. Identity and precedence

- Base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`
- Parent D4 hash:
  `975A5ABBB4471FA3E618C47A35E5EFED02960A1524657AC910290C25CA5739A1`
- Parent D4-R1 hash:
  `A764C4DC49F51C198DFAAF6C038C0C7644BDB9B7B6AD1286326E49E3E5B409AA`
- Parent D4-R2 hash:
  `ED96216F3CF91B0AC10AC26D14A081268D02E233C1871A87B104716600C26020`
- State: `DESIGN_REVIEW_PENDING / SOURCE_START0`

This addendum supersedes only the inherited D4 section 9.1 top-level field
list, D4-R1 section 4.1 sentence that kept the field order unchanged, D4-R2
section 3 terminal-stage wording, D4-R2 section 5 bundle membership, and the
final Gate paragraph in the mock manifest.  Every other D4, D4-R1 and D4-R2
clause remains in force.  The parent files and the mock/manifest stay byte
unchanged historical review inputs.

## 2. Closed composition field for the accepted design bundle

The V4 composition inserts required non-null `design_bundle_sha256`
immediately after `operation_plan_sha256` and immediately before `receipts`.
The resulting exact top-level order is:

```text
schema
record_type
task_owner
composition_id
composition_revision
parent_composition_sha256
observed_at
project_id
project_manifest_revision
project_manifest_sha256
installed_session_sha256
operation_plan_sha256
design_bundle_sha256
receipts
derived_state
reason_codes
fixture_lineage
composition_sha256
```

`design_bundle_sha256` is required in every derived state, including
`SETUP_REQUIRED` and `BLOCKED`.  It is exactly the accepted D4-R3 bundle hash
recorded by the independent review receipt and later reproduced from canonical
main.  It is never caller-provided, nullable, inferred from a subset, or
recalculated from an open PR.

`composition_sha256` includes `design_bundle_sha256` at the position above.
Its preimage is canonical UTF-8 JSON of every preceding top-level field in
that exact order.  Therefore a composition carrying a different or missing
bundle digest is rejected before derived-state or production-eligibility
evaluation.

The accepted design bundle is the canonical compact UTF-8 JSON array, in this
order:

```text
[
  ["task073_d4", "975A5ABBB4471FA3E618C47A35E5EFED02960A1524657AC910290C25CA5739A1"],
  ["task073_d4_r1", "A764C4DC49F51C198DFAAF6C038C0C7644BDB9B7B6AD1286326E49E3E5B409AA"],
  ["task073_d4_r2", "ED96216F3CF91B0AC10AC26D14A081268D02E233C1871A87B104716600C26020"],
  ["task073_d4_r3", "SELF_SHA256_EXCLUDED_FROM_PREIMAGE"],
  ["voice_studio_mock", "DAD0C3BDD4325693EB198F9C59EE520643CE9111C3527B96E2969FC868BA50FA"],
  ["voice_studio_manifest", "84FE88BD6C2448B35820B8BB19BB3B47B2353E65858C40609ECF0527DA7DA1C8"]
]
```

At freeze, the R3 row is replaced by this file's exact SHA-256 and the full
array hash is recorded in `design-review-receipt.md`.  The literal placeholder
above is never a schema, runtime, completion or handoff value.

## 3. Immutable manifest and separate Owner-check receipt

The reviewed mock manifest remains immutable with `Owner check: PENDING`.
It is not edited to record a later decision and is not rehashed after the
design review.  This section supersedes the manifest Gate sentence requiring
that same file to record `OWNER_CHECK_PASS`.

The TASK-036 P0-V Gate instead consumes a separate
`TASK073_OWNER_MOCK_CHECK_RECEIPT_V1`.  Its exact ordered fields are:

```text
schema
record_type
task_id
mock_revision
mock_sha256
manifest_sha256
design_bundle_sha256
decision
owner_action_ref
checked_at
receipt_revision
receipt_sha256
```

Closed values and rules:

- `schema=task073-owner-mock-check-receipt-v1`;
- `record_type=TASK073_OWNER_MOCK_CHECK_RECEIPT_V1`;
- `task_id=TASK-073`;
- `mock_revision=VOICE_STUDIO_SUCCESSOR_MOCK_D4_R0`;
- mock, manifest and design-bundle digests exactly match this accepted bundle;
- `decision=OWNER_CHECK_PASS|OWNER_CHECK_REJECTED`;
- `owner_action_ref` is an opaque trusted Owner-action coordinate, never raw
  identity, prompt text, UI text, path or caller-selected confirmation;
- `checked_at` is a trusted observation time and `receipt_revision` is a
  positive monotonic revision;
- `receipt_sha256` hashes canonical UTF-8 JSON of every preceding field in the
  listed order.

The serialized receipt and its self-hash are Evidence, not self-minting Human
authority.  TASK-036 must resolve the referenced Owner action through its
authorized governance/Product boundary, re-read the exact canonical mock,
manifest and bundle bytes, and require `OWNER_CHECK_PASS`.  Missing,
rehashed, copied, stale, rejected, cross-revision or caller-constructed
receipts keep only the TASK-036 P0-V integration effect at `START0`.
TASK-073 design and TASK-073-owned source are not blocked by a still-pending
Owner mock check.

The separate receipt path and writer are allocated by the future TASK-036
P0-V Atomic Unit.  This design creates no receipt, claims no Owner decision and
does not add a mutable decision file to the TASK-073 design bundle.

## 4. Exact execution reason-to-stage table

For `TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1`, the following table is the
complete legal mapping.  A listed set is exact, not a range.  Every reason in
a multi-reason tuple must allow the one declared `terminal_stage`; otherwise
the result is rejected.

| reason code | outcome | exact legal terminal stage(s) |
|---|---|---|
| `PRE_SPAWN_ADMISSION_REJECTED` | `FAILED_KNOWN` | `PRE_SPAWN` |
| `SANDBOX_START_FAILED` | `FAILED_KNOWN` | `PRE_SPAWN` |
| `NETWORK_ISOLATION_FAILED` | `FAILED_KNOWN` | `CHILD_CREATED` |
| `WORKER_PROTOCOL_FAILED` | `FAILED_KNOWN` | `CHILD_CREATED`, `GENERATION_DISPATCHED` |
| `MODEL_LOAD_FAILED` | `FAILED_KNOWN` | `CHILD_CREATED` |
| `RESOURCE_LIMIT_EXCEEDED` | `FAILED_KNOWN` | `CHILD_CREATED`, `GENERATION_DISPATCHED` |
| `INFERENCE_FAILED` | `FAILED_KNOWN` | `GENERATION_DISPATCHED` |
| `INVALID_WAVEFORM` | `FAILED_KNOWN` | `WAVEFORM_OBSERVED` |
| `SINK_WRITE_FAILED` | `FAILED_KNOWN` | `SINK_WRITE_ATTEMPTED` |
| `SINK_VERIFY_FAILED` | `FAILED_KNOWN` | `SINK_WRITE_COMMITTED` |
| `EXECUTION_OUTCOME_UNKNOWN` | `UNKNOWN` | `GENERATION_DISPATCHED` |
| `SINK_COMMIT_OUTCOME_UNKNOWN` | `UNKNOWN` | `SINK_WRITE_ATTEMPTED` |

`UNKNOWN` has exactly one reason: the matching `*_UNKNOWN` value in the table.
It cannot be combined with a `FAILED_KNOWN` reason.  `FAILED_KNOWN` has one to
four sorted unique reasons whose legal-stage sets all contain the declared
stage.  `SUCCESS` is legal only at `RESULT_VERIFIED` and has an empty tuple.
No failure or unknown reason is legal at `RESULT_VERIFIED`.

This mapping is evaluated together with the D4-R1 field-nullability matrix.
A reason cannot be used to claim an effect whose required fields are absent,
and a later observed effect cannot be relabelled as an earlier stage.

## 5. Completion and review Gate

`TASK073_IMPLEMENTATION_PR_READY` and `TASK073_IMPLEMENTATION_COMPLETE` bind
the accepted D4, D4-R1, D4-R2 and D4-R3 bundle.  The separate TASK-036 P0-V
integration binds that same bundle, `TASK073_IMPLEMENTATION_COMPLETE`, the
separate verified Owner-check PASS receipt and packaged synthetic readback.

Product and TASK-036 P0-V source remain `SOURCE_START0` until this exact R3
input receives independent DEV-4 `Critical=0 / High=0` and Judge `PASS`.
After that result, TASK-073-owned source may start without waiting for the
Owner mock check; TASK-036 P0-V remains gated on its separate Owner-check
receipt and its own Allowed Files/lock.

This design authorizes no real Owner audio, model/runtime download, paid or
cloud provider, Asset adoption, Export, Release, Deploy or Production
Activation.
