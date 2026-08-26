# TASK-058 P1A Admission Receipt and Idempotency Contract

Date: `2026-08-26`
Profile: `DEV-4 FOUNDATION CRITICAL`
Atomic Unit: `P1A / pure receipt reader and identity contract`
Execution class: `NO_EXTERNAL_OR_MUTABLE_I/O`

## 1. Decision

P1A defines the strict public shape of
`BvpMontageLearningAdmissionReceipt/v2` and a deterministic idempotency digest.
It provides a parser for already supplied receipt data. It does not provide a
receipt builder, writer, store, importer, queue, filesystem layout, or origin
authority lookup.

Parsing proves only that a body is structurally and cryptographically
self-consistent. It does not prove that BVP issued the body, that a canonical
store exists, or that a referenced store commit is current. Future P1B/P1C
code must bind the parsed body to the BVP-owned append-only store and trusted
writer before treating any claim as Product truth.

## 2. Public identity

| Field | Rule |
|---|---|
| `schema_version` | exact `2.0.0` |
| `message_type` | exact `BvpMontageLearningAdmissionReceipt` |
| `contract_profile` | exact `bvp-task058-montage-learning-admission-receipt-v2` |
| `receipt_id` | file-safe stable identifier, 1..192 characters |
| `admission_class` | `EXACT_EVIDENCE` or `GENERIC_OBSERVATION` |
| `source_contract_profile` | exact P0 lane profile matching `admission_class` |
| `source_record_id` | file-safe stable identifier |
| `source_sha256` | lowercase `sha256:<64 hex>` |
| `owner_scope_hash` | lowercase `sha256:<64 hex>` |
| `idempotency_key_sha256` | recomputed from the four source identity fields |
| `status` | `ACCEPTED`, `DUPLICATE`, `REJECTED`, or `REVIEW_REQUIRED` |
| `canonical_store_written` | strict JSON boolean |
| `canonical_evidence_id` / `canonical_evidence_sha256` | both set or both null |
| `canonical_store_commit_sha256` | required exactly when store-written is true |
| `duplicate_of_receipt_sha256` | structurally required for `DUPLICATE`; lineage remains unverified in P1A |
| `reason_codes` | closed, unique, deterministically ordered code list |
| `attempt` | positive integer, boolean rejected |
| `processed_at` | UTC `Z` timestamp |
| `bridge_instance_id` | file-safe stable identifier |
| `receipt_sha256` | canonical self-hash over every other field |

The idempotency preimage is canonical JSON with exactly:

```json
{
  "contract_profile": "<source_contract_profile>",
  "owner_scope_hash": "<owner_scope_hash>",
  "record_id": "<source_record_id>",
  "source_sha256": "<source_sha256>"
}
```

Canonical bytes are exactly
`ASCII(domain-label) || 0x00 || canonical-json-utf8`. The delimiter is one NUL
byte with hex `00`; it is not the two printable characters backslash and zero.
Canonical JSON uses UTF-8, sorted keys, separators `,` and `:`, no
insignificant whitespace, and `allow_nan=false`. The fixed domain labels are:

- idempotency: `TASK058_MONTAGE_LEARNING_IDEMPOTENCY_V1`;
- receipt: `TASK058_MONTAGE_LEARNING_ADMISSION_RECEIPT_V2`.

The receipt canonical JSON omits `receipt_sha256`. All identity-bearing strings
are ASCII-closed, so Unicode normalization cannot change these preimages. Hash
results use lowercase `sha256:<64 hex>`. Same key means the same source
identity. Same record ID with a different hash is not a duplicate; the later
importer must classify it as `REJECTED / ID_COLLISION`.

### Fixed digest vectors

The idempotency vector uses the canonical JSON shown above with `record-001`,
Owner scope `sha256:` plus 64 `a` characters, and source `sha256:` plus 64
`b` characters. Preimage hex is line-concatenated with no whitespace:

```text
5441534b3035385f4d4f4e544147455f4c4541524e494e475f4944454d504f54454e43595f5631007b22636f6e747261
63745f70726f66696c65223a226276702d7461736b3035382d6d6f6e746167652d65786163742d65766964656e63652d
7631222c226f776e65725f73636f70655f68617368223a227368613235363a6161616161616161616161616161616161
616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616122
2c227265636f72645f6964223a227265636f72642d303031222c22736f757263655f736861323536223a227368613235
363a62626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262
626262626262626262626262626262626262227d
```

Expected idempotency digest:

```text
sha256:9dc68f81fe5961526acea445b27f58b58db733e2a5f679f6099952108661d686
```

The receipt vector is Exact `ACCEPTED`, store-written false, all canonical and
duplicate references null, receipt `receipt-001`, attempt 1, bridge
`bridge-001`, and time `2026-08-26T00:00:00Z`. It uses the expected
idempotency digest above. Preimage hex is line-concatenated with no whitespace:

```text
5441534b3035385f4d4f4e544147455f4c4541524e494e475f41444d495353494f4e5f524543454950545f5632007b22
61646d697373696f6e5f636c617373223a2245584143545f45564944454e4345222c22617474656d7074223a312c2262
72696467655f696e7374616e63655f6964223a226272696467652d303031222c2263616e6f6e6963616c5f6576696465
6e63655f6964223a6e756c6c2c2263616e6f6e6963616c5f65766964656e63655f736861323536223a6e756c6c2c2263
616e6f6e6963616c5f73746f72655f636f6d6d69745f736861323536223a6e756c6c2c2263616e6f6e6963616c5f7374
6f72655f7772697474656e223a66616c73652c22636f6e74726163745f70726f66696c65223a226276702d7461736b30
35382d6d6f6e746167652d6c6561726e696e672d61646d697373696f6e2d726563656970742d7632222c226475706c69
636174655f6f665f726563656970745f736861323536223a6e756c6c2c226964656d706f74656e63795f6b65795f7368
61323536223a227368613235363a39646336386638316665353936313532366163656134343562323766353862353864
623733336532613566363739663630393939353231303836363164363836222c226d6573736167655f74797065223a22
4276704d6f6e746167654c6561726e696e6741646d697373696f6e52656365697074222c226f776e65725f73636f7065
5f68617368223a227368613235363a616161616161616161616161616161616161616161616161616161616161616161
61616161616161616161616161616161616161616161616161616161616161222c2270726f6365737365645f6174223a
22323032362d30382d32365430303a30303a30305a222c22726561736f6e5f636f646573223a5b5d2c22726563656970
745f6964223a22726563656970742d303031222c22736368656d615f76657273696f6e223a22322e302e30222c22736f
757263655f636f6e74726163745f70726f66696c65223a226276702d7461736b3035382d6d6f6e746167652d65786163
742d65766964656e63652d7631222c22736f757263655f7265636f72645f6964223a227265636f72642d303031222c22
736f757263655f736861323536223a227368613235363a62626262626262626262626262626262626262626262626262
626262626262626262626262626262626262626262626262626262626262626262626262626262222c22737461747573
223a224143434550544544227d
```

Expected receipt digest:

```text
sha256:f31513b7318ba49a51348dc4c858391988eec2ef2feaf0c0c2b04eb17fb1468e
```

## 3. Closed reason codes

P1A admits only:

- `SCHEMA_INVALID`
- `HASH_MISMATCH`
- `OWNER_SCOPE_MISMATCH`
- `ID_COLLISION`
- `LINEAGE_NOT_FOUND`
- `LINEAGE_MISMATCH`
- `REVIEW_BINDING_REQUIRED`
- `FORBIDDEN_DATA_PRESENT`
- `PATH_UNSAFE`
- `FILE_UNSTABLE`
- `STORE_COMMIT_FAILED`
- `DUPLICATE_IDEMPOTENCY_KEY`

Codes must be lexicographically sorted and unique. Status fixes the exact
reason shape: `ACCEPTED=[]`,
`REVIEW_REQUIRED=[REVIEW_BINDING_REQUIRED]`, and
`DUPLICATE=[DUPLICATE_IDEMPOTENCY_KEY]`. `REJECTED` requires one or more
terminal rejection codes and cannot contain either state-specific code.

## 4. State matrix

| State | Required | Forbidden |
|---|---|---|
| Generic `REVIEW_REQUIRED` | exact reason list `REVIEW_BINDING_REQUIRED`; store-written false | canonical refs, store commit, duplicate ref |
| Generic `REJECTED` | one or more terminal rejection codes; store-written false | canonical refs, store commit, duplicate ref |
| Exact `REJECTED` | one or more terminal rejection codes; store-written false | canonical refs, store commit, duplicate ref |
| Exact `ACCEPTED` | exact empty reason list; duplicate ref null | duplicate/review reason |
| Exact `DUPLICATE` | exact duplicate reason; duplicate receipt hash | review/rejection reason |

Generic observations can only be `REVIEW_REQUIRED` or `REJECTED` and can never
set `canonical_store_written=true`. Human adoption must first rebuild and
revalidate exact BVP-owned Evidence, after which any receipt is classified as
Exact. Exact receipts may claim a store write only for `ACCEPTED` or
`DUPLICATE`. A true store-written claim requires canonical evidence ID/hash and
canonical store commit hash. On `DUPLICATE`, true means only that the body
claims an already committed prior result; it never means the duplicate attempt
wrote the store. A false claim requires all three fields to be null.

The design deliberately permits Exact `ACCEPTED` with
`canonical_store_written=false` for compatibility with the proposal document.
Consumers must not display or use that state as canonical learning admission.

## 5. Origin authority and public projection

`parse_montage_learning_admission_receipt()` returns an immutable typed value
only after every closed-field, hash, time, state, and lane invariant passes.
Its public projection is body-free and has exactly this whitelist:

- `receipt_id`;
- `admission_class`;
- `source_record_id`;
- `source_sha256`;
- `status`;
- `reason_codes`;
- `receipt_sha256`;
- `canonical_store_commit_claimed`;
- `receipt_structure_valid=true`;
- `origin_authority_verified=false`;
- `duplicate_lineage_verified=false`;
- `canonical_store_commit_verified=false`;
- `canonical_admission_authority_created=false`;
- `receipt_minted=false`;
- no additional fields and no Owner plaintext, bridge instance, Owner-scope
  hash, idempotency key, canonical references, path, proposal, transcript,
  media, or private rationale.

`canonical_store_commit_claimed` is a strict JSON boolean and equals the parsed
receipt's `canonical_store_written` value exactly; the commit digest itself is
never exposed. `reason_codes` is emitted as a fresh JSON array from the sealed
typed tuple, so caller mutation cannot change the receipt.

Even when the parsed body claims a canonical store commit, P1A reports it only
as `canonical_store_commit_claimed`. `duplicate_of_receipt_sha256` is likewise
only `STRUCTURALLY_REFERENCED_UNVERIFIED`; P1A has no trusted ledger reader with
which to resolve it. A later BVP-owned reader must verify receipt origin,
same-key/source/Owner/class lineage, prior status/store commit, and currentness.

## 6. Failure modes

Missing or extra fields, false-like integers, unknown status/reason/profile,
malformed IDs/digests/time, noncanonical reason ordering, lane/profile
mismatch, idempotency mismatch, self-hash mismatch, impossible state fields,
generic acceptance/duplicate/store-write claims, impossible duplicate shape,
or mutable/non-JSON data fail closed with
`MontageLearningReceiptContractError`.

The parser never repairs input, guesses Owner scope, changes status, writes a
receipt, or returns partial success.

## 7. P1A API

```text
derive_montage_learning_idempotency_key_sha256(...)
compute_montage_learning_receipt_sha256(mapping_without_or_with_hash)
parse_montage_learning_admission_receipt(mapping)
MontageLearningAdmissionReceipt.to_public_projection()
```

No `build_*`, `mint_*`, `write_*`, `save_*`, `get_latest`, or filesystem API is
authorized in P1A.

## 8. Exact scope and acceptance

Exact six paths:

1. `docs/ai-team/tasks/TASK-058/task.md`
2. this design
3. `schemas/montage-learning-admission-receipt.schema.json`
4. byte-identical packaged schema mirror
5. `src/ai_video_production/montage_learning_receipt_contracts.py`
6. `tests/test_task058_montage_learning_receipt_contracts.py`

Acceptance requires schema Draft 2020-12 validity and mirror parity; positive
exact/generic states; every negative matrix edge; domain-separated idempotency
and self-hash tamper rejection; deterministic immutable results; exact
body-free projection; duplicate lineage down-scoped as unverified; no
filesystem/network/database/subprocess/importer/store surface; focused and
related regressions; and independent Critic/Tester/Judge C/H zero.
