# TASK-047 P-OBS-1B Source/Transport Receipt ABI R0

## Allocation and authority

- Project: BAI VIDEO PRODUCTION; canonical owner: TASK-047.
- Atomic Unit: `P-OBS-1B-RECEIPT-ABI-R0`.
- Base: `main@d74cda06f8ee1a6d4a98d0507c29441a9de87ffd`.
- Depth: DEV-4. This is a cross-task receipt contract and parser.
- Owner direction on 2026-09-23: take over the unallocated TASK-047 canonical
  receipt ABI/parser work. Current main has no implementation or allocation for
  it, and no open PR owns this exact slice.
- This R0 freezes only `CaptureSourceCurrentnessReceiptV1` and
  `CaptureTransportIntegrityReceiptV2` as body-free, non-admitting records.
  It does not implement Q1 capture, issue a receipt, evaluate current Consent,
  prove custody, register an Asset or select a terminal Job head.

The earlier [capture-truth design](p0v-capture-format-terminal-receipt-r1-design-2026-09-03.md)
is a candidate family. Its full chain still needs the exact TASK-046 subject
and Consent producer, trusted-time, TASK-043 capture currentness, TASK-003
capture Asset adoption and separate TASK-082 custody bindings. The local
OwnerSubject amendment branch is unmerged and is not treated as main authority.
TASK-082 V2 already owns private custody; this unit creates no alternate
custody receipt. The existing TASK-047 readiness monitor receipt has a
different purpose and is not a capture-chain terminal receipt.

## Context and allowed files

MUST READ: current state; TASK-047 task and capture-truth design; TASK-098 A5
dependency; TASK-082 custody receipt fields; target schema/parser/tests.
READ IF REQUIRED: exact TASK-046/043/003 producer contracts. DO NOT READ BY
DEFAULT: historical OBS release packs, unrelated Product subsystems or the
entire Development OS repository.

MAY MODIFY: this design; `docs/ai-team/tasks/TASK-047/task.md`;
`docs/ai-team/current-state.md`; canonical schema and mirrored packaged schema
named `task047-capture-source-transport-receipts.schema.json`;
`src/ai_video_production/task047_capture_source_transport_receipts.py`;
`tests/test_task047_capture_source_transport_receipts.py`; bounded Evidence.
MUST NOT MODIFY: TASK-046/043/003/082/098 owners, OBS Plugin/Controller,
Asset store, packaging, installer, Release, Deploy or Production paths.

## Exact R0 wire grammar

- UTF-8 JSON object, at most 64 KiB. Duplicate keys, non-finite numbers,
  unknown fields and unsupported type/version pairs are rejected. All integer
  fields require a JSON integer token; integral-looking floats such as `1.0`
  are rejected despite JSON Schema's mathematical integer equivalence.
- Both records have the exact common envelope from the capture-truth design:
  `record_type`, `schema_version`, `project_id`, `recording_session_id`,
  `segment_attempt_id`, `operation_id`, `idempotency_key`,
  `owner_subject_binding_sha256`, `consent_evaluation_sha256`,
  `producer_code_sha256`, `runtime_sha256`, `trusted_time_binding_sha256`,
  `capture_job_id`, `capture_job_revision_sha256`,
  `capture_job_predecessor_readback_sha256`, `created_at`, `observed_at`,
  `fresh_until`, `predecessor_receipt_sha256`, `receipt_sha256`.
- SHA-256 values are 64 lowercase hexadecimal characters without a prefix.
  They are opaque references, not proof that an external producer is current.
- Timestamps are UTC RFC 3339 with six fractional digits and `Z`, with
  `created_at <= observed_at < fresh_until`. Parsing them is necessary for
  ordering, but local wall time never establishes currentness.
- IDs are ASCII `[A-Za-z0-9][A-Za-z0-9._:-]{0,99}`. The parser never accepts
  filesystem paths, audio bodies or private source identifiers.
- Canonical digest preimage excludes `receipt_sha256`. Serialize with UTF-8,
  recursively sorted object keys, compact separators, no ASCII escaping and
  no non-finite number. Prefix with the exact domain bytes below, then SHA-256:
  `TASK047_CAPTURE_SOURCE_CURRENTNESS_V1\0INITIAL\0` or
  `TASK047_CAPTURE_TRANSPORT_INTEGRITY_V2\0`.
- The source receipt has null predecessor. The transport receipt's predecessor
  is the exact source receipt digest; its `source_receipt_sha256` equals that
  same digest. All other common lineage identities must match byte for byte.
The transport creation cannot precede source observation, and its freshness
cannot extend beyond source freshness. This remains structural ordering, not
a current-time admission decision.

`CaptureSourceCurrentnessReceiptV1` adds exactly:

| Field | Type / closed value |
|---|---|
| `source_binding_sha256`, `obs_build_sha256`, `obs_process_identity_sha256`, `source_graph_sha256` | SHA-256 digest |
| `source_sample_format` | `FLOAT32_PLANAR` |
| `source_sample_rate_hz` | integer 8,000..384,000 |
| `source_channel_count` | integer 1..32 |
| `measurement_point` | `PRE_FILTER` or `POST_FILTER` |
| `source_classification` | `OWNER_SELECTED_ISOLATED_MIC`, `MIXED_OR_NON_MIC`, `UNKNOWN` |
| `source_currentness_state` | `BOUND_VERIFIED`, `MISMATCH`, `STALE`, `REVOKED`, `UNKNOWN` |

`CaptureTransportIntegrityReceiptV2` adds exactly:

| Field | Type / rule |
|---|---|
| `source_receipt_sha256`, `hmac_key_epoch_sha256` | SHA-256 digest |
| `first_packet_sequence`, `last_packet_sequence` | nonnegative integer; last >= first |
| `observed_packet_count`, `accepted_packet_count` | observed >= 1; accepted >= 0 and <= observed |
| `source_frame_count`, `source_sample_count` | nonnegative integer; sample count = frame count × source channels in paired source receipt |
| `first_source_timestamp_ns`, `last_source_timestamp_ns` | nonnegative integer; last >= first |
| `gap_count`, `duplicate_count`, `reorder_count`, `overrun_count`, `reconnect_count`, `nonfinite_sample_count` | nonnegative integer |
| `transport_verification_state` | `BOUND_VERIFIED`, `MISMATCH`, `UNKNOWN` |

The transport count records observations; it does not silently convert gaps,
overruns, HMAC failures or non-finite samples into a successful capture. The
parser accepts a well-formed non-success state so recovery can preserve it. A
later producer and admission layer must prove HMAC, sequence, callback timing,
source currentness and trusted-time bindings from their own authorities.

## API and result

`parse_source_transport_receipt(raw: bytes | str)` returns an immutable
validated record with a fixed `STRUCTURAL_VALID_ONLY` assessment. It never
reads a receipt/media file or makes an external call; the module loads its
packaged JSON Schema resource once at import. `validate_source_transport_pair` checks
the exact two-record lineage, counters and source channel count. Neither API
returns `BOUND_VERIFIED` admission or a TASK-048 quality decision. Errors carry
closed public-safe codes without echoing input, paths, IDs or private data.

## Tests and review

- Schema mirror byte equality and Draft 2020-12 validity.
- Valid source/transport pair with independent expected digest recomputation.
- Reject duplicate/unknown fields, bad UTF-8, excessive size, NaN/Infinity,
  unsupported versions, malformed digests/IDs/timestamps, digest tampering,
  wrong predecessor, cross-project/session/attempt/job/Consent/subject replay,
  bad packet ordering and sample-count mismatch.
- Verify no file, provider, OBS, custody, Asset or audio operation occurs.
- Focused tests and direct TASK-047/TASK-098 contract regressions, diff review,
  and independent high-assurance review before claiming canonical completion.

R0 parser/schema landing is a necessary early ABI boundary. TASK-098 A5 remains
blocked until the remaining TASK-047 receipt types, external producer bindings,
full terminal parser and fresh DEV-4 review are complete.
