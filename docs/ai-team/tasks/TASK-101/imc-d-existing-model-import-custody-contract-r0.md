# TASK-101 IMC-D R0 — Existing Model Import Custody Contract

Status: `DESIGN_IN_REVIEW / IMPLEMENTATION_OWNER_UNALLOCATED / NATIVE_BLOCKED`

## 1. Goal

Define the canonical contract for importing one already completed Owner GPT-SoVITS model pair into protected BAI VIDEO PRODUCTION custody without new recording or training. The contract must preserve exact historical model identity while creating current import custody/readback and separately scoped one-operation capabilities for installed-identity observation and later inference.

IMC-D R0 is design-only. It does not read the WSL source files, copy or encrypt model bytes, create a protected destination, alter ACLs/keys, load a model, run inference or connect Product/Shell UI.

## 2. Authority and exact scope

The Owner's `次へ` followed acceptance of TASK-100 LVC-C2-D0, whose next direct dependency is TASK-101 custody/readback and observation-capability ownership. TASK-101 already names this thread as design coordinator. This binds only:

1. `docs/ai-team/tasks/TASK-101/task.md`
2. `docs/ai-team/tasks/TASK-101/imc-d-existing-model-import-custody-contract-r0.md`

External Evidence is limited to `C:\home\baisound\evidence\bai-video-production\TASK-101\imc-d-r0\<run-id>\`.

All source, schema, tests, producer Task records, current-state/index, external voice repositories and private files are read-only or prohibited. Implementation ownership and every native/private effect remain unallocated.

## 3. Canonical responsibility boundary

| Responsibility | Owner | TASK-101 treatment |
|---|---|---|
| Historical Dataset/training/model lineage, ModelArtifactBinding, evaluation, current H4, Consent, rights and license | TASK-046 | required producer evidence; never issued or upgraded here |
| Training-terminal checkpoint/artifact custody | TASK-084 | preserved `TRAINING_TERMINAL` variant; never aliased to import |
| Existing completed model import custody, sealed inventory, current readback, observation capability and import-path load lease | TASK-101 | canonical responsibility |
| Catalog admission and installed-identity assessment | TASK-100 | downstream consumers of accepted TASK-101 evidence |
| Compute/no-network admission | TASK-066 | downstream independent gate |
| Route/private reference | TASK-074 | downstream independent owner |
| Model execution/inference/PCM | TASK-075 | downstream execution owner |
| Narration planning/assembly | TASK-014 | downstream consumer |
| Product composition/Shell | TASK-073 / TASK-036 | separate owning Atomic Units |

TASK-068 supplies security patterns and immutable JSON primitives only. Its current contract does not publish encrypted binary directory trees or mutable custody phases and therefore cannot be treated as the TASK-101 native backend. TASK-063 montage-learning installation and TASK-093 Qwen runtime installation are unrelated to imported GPT-SoVITS custody.

## 4. Closed contract family

Future IMC-I implements the following strict body-free record family. This R0 freezes its fields, nullability, limits and canonical preimages before implementation.

### 4.1 `ExistingModelImportIntentV1`

Required coordinates:

- contract/record version and canonical owner `TASK-101`;
- `import_intent_id`, positive revision and nullable predecessor digest;
- exact Project, VoiceProfile and ModelCandidate revision identities;
- exact TASK-046 ModelArtifactBinding, H4, Consent, rights and license evidence digests;
- provider, engine, model, runtime/build and model-pair identities;
- exact two-entry expected artifact inventory: one SoVITS and one GPT role, each with content digest, positive byte count and bounded opaque source identity;
- protected-destination class, cipher policy, key scope, principal/access policy, retention and revocation-policy digests;
- trusted issue/evaluation/expiry times;
- exact Human import authority identity;
- domain-separated intent digest.

The record contains no reusable source/destination path, key, secret, model bytes or authority capability. A self-hash is not producer authentication.

### 4.2 `ExistingModelImportCustodyReceiptV1`

The native import producer may issue this private receipt only after no-clobber publication and durable seal. It binds:

- the exact validated intent and native operation identity;
- source physical-identity commitment and the expected two-file inventory;
- protected destination instance and sealed inventory commitment;
- per-role content digest, byte count and opened physical-identity digest;
- cipher/backend/key-scope/principal/security-policy digests;
- import event-chain head, seal/flush/readback identities and trusted timestamps;
- `completion_state=SEALED_CURRENT`;
- domain-separated receipt digest.

The public-safe projection contains bounded opaque references, digests, state and timestamps only. It never contains absolute paths, account names, key material or model bodies. `FIXTURE_ONLY` uses a distinct source/type and cannot become live custody.

### 4.3 `ExistingModelImportCustodyReadbackV1`

Readback reparses the exact receipt, reopens the protected sealed inventory through the accepted native backend and binds current physical identities, full pair inventory, custody generation, revocation state and trusted evaluation time. The closed decision set is:

- `CURRENT`;
- `STALE`;
- `REVOKED`;
- `IDENTITY_MISMATCH`;
- `COMPLETION_UNKNOWN`.

Only `CURRENT` is consumable. Missing, partial, stale, revoked, crossed, self-created or merely rehashed evidence fails closed.

### 4.4 Frozen field tables

All tables are exact: no additional keys are permitted and no field is nullable unless marked `nullable`. `Digest` means `sha256:` plus 64 lowercase hexadecimal characters. `Id` uses ASCII `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`. `Timestamp` is a calendar-valid UTC `YYYY-MM-DDTHH:MM:SS[.1-6 digits]Z`. `PositiveInt` is an integer from 1 through 2,147,483,647 and rejects booleans. `ByteCount` is an integer from 1 through 9,007,199,254,740,991 and rejects booleans.

`ExistingModelImportArtifactV1` contains exactly:

| field | type / rule |
|---|---|
| `role` | enum `SOVITS`, `GPT`; an inventory has exactly one of each in this order |
| `content_sha256` | `Digest` |
| `byte_count` | `ByteCount` |
| `opaque_source_identity_sha256` | `Digest`; no path |

`ExistingModelImportIntentV1` contains exactly:

| field | type / rule |
|---|---|
| `contract_version`, `record_type`, `canonical_owner_task` | constants `EXISTING_MODEL_IMPORT_INTENT_V1`, `ExistingModelImportIntentV1`, `TASK-101` |
| `import_intent_id` | `Id` |
| `revision` | `PositiveInt` |
| `predecessor_sha256` | nullable `Digest`; null only at revision 1, non-null otherwise |
| `project_manifest_sha256`, `voice_profile_revision_sha256`, `model_candidate_revision_sha256`, `model_artifact_binding_sha256` | `Digest` |
| `h4_approval_sha256`, `consent_currentness_sha256`, `rights_currentness_sha256`, `license_evidence_sha256` | `Digest` |
| `historical_provenance_reconciliation_sha256` | `Digest`, TASK-046 producer |
| `provider_id`, `engine_id`, `model_id` | `Id` |
| `runtime_build_sha256`, `model_pair_sha256` | `Digest` |
| `artifacts` | exactly two `ExistingModelImportArtifactV1` entries in `SOVITS`, `GPT` order |
| `protected_destination_class` | constant `BVP_OWNER_VOICE_MODEL_CUSTODY_V1` |
| `cipher_policy_sha256`, `key_scope_sha256`, `principal_access_policy_sha256`, `retention_policy_sha256`, `revocation_policy_sha256` | `Digest` |
| `human_import_authority_sha256` | `Digest` |
| `issued_at`, `evaluated_at`, `expires_at` | `Timestamp`; `issued_at <= evaluated_at < expires_at` |
| `intent_sha256` | canonical digest defined in section 7 |

`ExistingModelImportReceiptArtifactV1` contains exactly `role`, `content_sha256`, `plaintext_byte_count`, `source_physical_identity_sha256`, `ciphertext_sha256`, `ciphertext_byte_count` and `destination_physical_identity_sha256`, using the same ordered roles, `Digest` values and `ByteCount` limits.

`ExistingModelImportCustodyReceiptV1` contains exactly:

| field | type / rule |
|---|---|
| `contract_version`, `record_type`, `canonical_owner_task` | constants `EXISTING_MODEL_IMPORT_CUSTODY_RECEIPT_V1`, `ExistingModelImportCustodyReceiptV1`, `TASK-101` |
| `operation_id`, `import_intent_id` | `Id` |
| `intent_sha256`, `project_manifest_sha256`, `voice_profile_revision_sha256`, `model_candidate_revision_sha256`, `model_artifact_binding_sha256`, `model_pair_sha256`, `runtime_build_sha256` | `Digest`; exact intent equality |
| `source_physical_identity_set_sha256`, `destination_instance_sha256`, `sealed_inventory_sha256` | `Digest` |
| `artifacts` | exactly two `ExistingModelImportReceiptArtifactV1` entries in fixed role order |
| `cipher_backend_sha256`, `cipher_policy_sha256`, `key_scope_sha256`, `principal_access_policy_sha256` | `Digest` |
| `import_event_chain_head_sha256`, `seal_receipt_sha256`, `durability_receipt_sha256`, `physical_readback_sha256` | `Digest` |
| `started_at`, `sealed_at`, `read_back_at`, `expires_at` | `Timestamp`; ordered `started_at <= sealed_at <= read_back_at < expires_at` |
| `completion_state` | constant `SEALED_CURRENT` |
| `receipt_sha256` | canonical digest defined in section 7 |

`ExistingModelImportCustodyReadbackV1` contains exactly:

| field | type / rule |
|---|---|
| `contract_version`, `record_type`, `canonical_owner_task` | constants `EXISTING_MODEL_IMPORT_CUSTODY_READBACK_V1`, `ExistingModelImportCustodyReadbackV1`, `TASK-101` |
| `readback_id`, `operation_id`, `import_intent_id` | `Id` |
| `intent_sha256`, `receipt_sha256`, `destination_instance_sha256`, `sealed_inventory_sha256`, `current_inventory_sha256`, `current_physical_identity_set_sha256`, `model_pair_sha256`, `runtime_build_sha256` | `Digest` |
| `custody_generation` | `PositiveInt` |
| `revocation_state` | enum `NOT_REVOKED`, `REVOKED`, `UNKNOWN` |
| `decision` | enum `CURRENT`, `STALE`, `REVOKED`, `IDENTITY_MISMATCH`, `COMPLETION_UNKNOWN` |
| `reason_codes` | array of 1-16 unique ASCII `Id` values in lexicographic order |
| `evaluated_at`, `expires_at` | `Timestamp`; `evaluated_at < expires_at` only for `CURRENT` |
| `readback_sha256` | canonical digest defined in section 7 |

The closed reason-code enum is `CURRENT`, `STALE`, `REVOKED`, `REVOCATION_UNKNOWN`, `INTENT_MISMATCH`, `RECEIPT_MISMATCH`, `INVENTORY_MISMATCH`, `PHYSICAL_IDENTITY_MISMATCH`, `PAIR_IDENTITY_MISMATCH`, `RUNTIME_IDENTITY_MISMATCH` and `COMPLETION_UNKNOWN`. For `CURRENT`, `revocation_state=NOT_REVOKED`, both current inventory/physical identity digests must equal a successful native reread, and `reason_codes` is exactly `["CURRENT"]`. `STALE` requires `STALE`; `REVOKED` requires `REVOKED`; `IDENTITY_MISMATCH` requires at least one `*_MISMATCH`; `COMPLETION_UNKNOWN` requires `COMPLETION_UNKNOWN` or `REVOCATION_UNKNOWN`. No caller text is accepted.

`ExistingModelImportCapabilityAuditV1` is the only serializable capability lifecycle record. The private capability itself is never serializable. The audit contains exactly: constant version/type/owner, `capability_id`, `purpose` (`INSTALLED_IDENTITY_OBSERVATION` or `LOCAL_NARRATION_INFERENCE`), `operation_id`, `consumer_task`, `custody_readback_sha256`, `model_pair_sha256`, `state` (`ISSUED`, `OPEN_STARTED`, `CONSUMED`, `EXPIRED`, `COMPLETION_UNKNOWN`, `FAILED_CLOSED`), nullable `predecessor_sha256`, `issued_at`, `expires_at`, nullable `completed_at`, and `audit_sha256`. `completed_at` is null only for `ISSUED` and `OPEN_STARTED`; terminal states require it. Exact duplicate requests return only the current audit record and never another capability.

## 5. Capability separation

### 5.1 `INSTALLED_IDENTITY_OBSERVATION`

TASK-101 is the custody issuer for a non-serializable, one-operation observation capability consumed by future TASK-100 C2-N. It is bound to the exact custody readback, pair, native operation, consumer and short validity window. It is read-only, one-shot, non-replayable, non-load and non-executing. It yields only bounded private handles needed to verify installed identity.

The capability is not a path token, receipt, TASK-071/072 action/ticket or inference load lease. Missing/crossed/expired/already-opened capability blocks before body access. After any open attempt it is burned; close or identity ambiguity yields `COMPLETION_UNKNOWN` and no automatic retry.

### 5.2 `LOCAL_NARRATION_INFERENCE`

Inference uses a separate non-serializable one-operation load lease. Issuance requires current sealed custody readback, exact TASK-046 ModelArtifactBinding and H4, current Consent/rights/license, admitted TASK-100 catalog/C2 assessment, exact TASK-014 FineTunedModelBinding, TASK-075 operation/admission and applicable TASK-066/TASK-071/TASK-072 evidence.

The load lease is purpose-specific, one-shot, non-replayable and operation-bound. It may provide trusted private handles only to the accepted TASK-075 child. TASK-101 neither loads the model nor infers audio. Observation and inference capabilities cannot substitute for, wrap or derive from one another.

### 5.3 Frozen purpose and lifecycle matrix

| purpose | required at issuance and again immediately before `OPEN_STARTED` | expressly forbidden |
|---|---|---|
| `INSTALLED_IDENTITY_OBSERVATION` | exact `CURRENT` custody readback, pair/runtime/operation/consumer identity, unexpired observation authority and capability | H4/inference admission as substitute, TASK-075 execution, model load, inference, audio, generic path, inference lease |
| `LOCAL_NARRATION_INFERENCE` | exact fresh `CURRENT` custody readback; same pair/runtime; current TASK-046 H4, Consent, rights and license; admitted TASK-100 C2; exact TASK-014 binding; TASK-075 operation/admission; applicable TASK-066/071/072 evidence; unexpired lease | evaluation/resume authority, observation capability, generic path, different consumer/operation |

Issuance-time checks never substitute for consumption-time checks. Immediately before any private handle is opened or transferred, the issuer reparses every required canonical record, uses trusted current time, rereads custody/revocation, and rejects changed, stale, expired or revoked evidence. Consent/rights/H4/custody revocation between issuance and use therefore blocks before body access.

The only capability transitions are:

```text
ISSUED -> OPEN_STARTED | EXPIRED | FAILED_CLOSED
OPEN_STARTED -> CONSUMED | COMPLETION_UNKNOWN | FAILED_CLOSED
CONSUMED | EXPIRED | COMPLETION_UNKNOWN | FAILED_CLOSED -> no transition
```

Before opening or transferring a private handle, TASK-101 durably appends and rereads the exact `OPEN_STARTED` audit transition; that accepted attempt burns the capability even if the consumer later fails. A duplicate/replay receives only the latest body-free audit and never a handle. `FAILED_CLOSED` after `OPEN_STARTED` is allowed only when all transferred handles are proven closed, no consumer effect began, identity remains exact and zeroization/readback pass. Any close, identity, consumer-start, zeroization, persistence or restart uncertainty is `COMPLETION_UNKNOWN`.

`CONSUMED` requires consumer completion plus handle-close identity and zeroization readback. On restart, an `OPEN_STARTED` capability without exact terminal readback becomes `COMPLETION_UNKNOWN`; it is never reopened or reissued. Capability objects are exact private built-in instances: no public constructor, serialization, subclass, reset, copy, derivation or reusable bearer token is accepted.

## 6. Native import state machine

The future native operation uses one immutable operation identity and the following closed states:

```text
PLANNED
-> SOURCE_OPEN_STARTED
-> DESTINATION_PREPARED
-> COPY_ENCRYPT_STARTED
-> INVENTORY_SEALED
-> READBACK_CURRENT
```

Terminal alternatives are `NO_EFFECT`, `FAILED_CLOSED` and `COMPLETION_UNKNOWN`. No state may skip forward, reopen or transition out of a terminal state. Durable state evidence is append-only; mutable same-path phase authority is not inferred from TASK-068.

The native backend must:

- receive private source/destination capabilities from the approved authority boundary, not caller paths;
- pin and revalidate source/destination ancestors and opened objects;
- reject reparse/symlink, hardlink where prohibited, foreign ownership, unexpected files, pair-role crossing, size/hash mismatch, source replacement and destination collision;
- copy/encrypt into operation-owned temporary objects and publish the sealed closed inventory last with no replacement;
- durably flush and physically read back every object before `SEALED_CURRENT`;
- never overwrite, delete, repair or reuse foreign, historical or unknown objects;
- leave ambiguous artifacts preserved and report `COMPLETION_UNKNOWN` without blind retry.

No task-owned path may be a drive root or direct child of a drive root. The exact authorized protected destination and every scratch/Evidence root must pass canonical containment and ownership checks before effects.

### 6.1 Frozen failure classification

| observed boundary | terminal result | required behavior |
|---|---|---|
| parser, authority, currentness, capability, containment or source validation fails before any native create/write | `NO_EFFECT` | open/create/write count zero |
| destination already exists, belongs to another operation or has unknown ownership | `NO_EFFECT` | preserve it; no overwrite/delete/repair |
| source handles opened but destination operation-owned temporary object not created | `FAILED_CLOSED` | close handles; no destination artifact |
| only exact operation-owned temporary objects exist and failure/current-operation ownership is fully proved | `FAILED_CLOSED` | cleanup is optional only under separately authorized exact-identity policy; otherwise preserve and record residual |
| temporary ownership/identity or cleanup completion is uncertain | `COMPLETION_UNKNOWN` | preserve, record, prohibit automatic retry |
| any final namespace entry may have appeared, or no-replace result/flush/directory durability is ambiguous | `COMPLETION_UNKNOWN` | preserve all objects; no retry or alternate target |
| sealed manifest exists but any member, inventory, physical identity, decryptability or reread differs | `COMPLETION_UNKNOWN` | never issue current receipt/readback |
| all two artifacts, sealed inventory, durability and physical reread pass | `READBACK_CURRENT` | issue exact receipt then exact `CURRENT` readback |
| crash/restart finds an incomplete or untrusted operation chain | `COMPLETION_UNKNOWN` | evidence-only recovery classification; no auto-resume |

`FAILED_CLOSED` never means a live custody set exists. Only `READBACK_CURRENT` permits `completion_state=SEALED_CURRENT`; all other native outcomes must not construct a custody receipt. Public errors are body-free and contain stable reason codes only.

## 7. Canonical encoding and parser limits

Future JSON records require strict UTF-8, duplicate-key rejection, no BOM/trailing bytes, no non-finite numbers and exact keys. Parser limits are frozen at: document 131,072 bytes; depth 16; total mapping/list/scalar nodes 4,096; mapping keys 256 per object; arrays 64 entries except the exact-two artifact inventories; strings 512 Unicode scalar values; reason codes 16. Integers reject booleans and use the exact ranges in section 4.4. Timestamps follow the exact UTC grammar above; native completion/readback timestamps obey their table ordering.

Canonical JSON is the existing Product `canonical_json_bytes`: UTF-8 of JSON with Unicode preserved, object keys sorted, and separators `,` and `:` with no added whitespace. For each record, remove only its own final digest field, prepend the exact ASCII domain plus NUL, then SHA-256 the resulting bytes:

| record | domain |
|---|---|
| intent | `bai-video-production/task101/existing-model-import-intent/v1\0` |
| custody receipt | `bai-video-production/task101/existing-model-import-custody-receipt/v1\0` |
| custody readback | `bai-video-production/task101/existing-model-import-custody-readback/v1\0` |
| capability audit | `bai-video-production/task101/existing-model-import-capability-audit/v1\0` |

Every output is `sha256:` plus 64 lowercase hex. Nested artifact order is semantic and fixed; maps remain key-sorted. Different record types, variants or revisions cannot share a domain. Unknown versions, keys, nulls or fields are rejected before digest comparison.

Sections 4.4, 5.3, 6.1 and 7 are the normative JSON Schema semantic source. IMC-I must encode them without adding a semantic choice: `additionalProperties=false` at every object, the exact required sets and constants above, the stated conditional nullability/decision rules, and all numeric/string/array limits. The canonical schema and package mirror must be byte-identical. Any implementation need that would change a key, type, enum, condition, limit, transition, domain or failure classification requires a reviewed design revision before source mutation.

## 8. Atomic units and start gates

### IMC-I — pure contract and fake backend

May start only after this exact design revision, including sections 4.4, 6.1 and 7, is independently accepted, its SHA-256 is recorded in the canonical Task record, and an implementation owner is allocated. No IMC-I implementation may redefine its keys, types, nullability, domains, limits, decisions or failure classifications. Its exact future files are proposed as:

1. `docs/ai-team/tasks/TASK-101/task.md`
2. `src/ai_video_production/task101_existing_model_import_custody.py`
3. `schemas/task101-existing-model-import-custody.schema.json`
4. `src/ai_video_production/schema_resources/task101-existing-model-import-custody.schema.json`
5. `tests/test_task101_existing_model_import_custody.py`

IMC-I remains effect-zero and must keep fixture evidence non-live.

### IMC-N — protected native import/readback

Requires a separate exact Owner gate naming private source reads, destination creation, copy/encryption, key/DACL operations and durable readback. It additionally requires:

- accepted IMC-I and native backend owner;
- current TASK-046 reconciliation/H4/Consent/rights/license evidence;
- approved protected-storage, cipher/key, principal/access, retention and revocation policies;
- exact source and destination capability issuers;
- unique OS-temp scratch plus mandatory public-safe Evidence under `C:\home\baisound\evidence\bai-video-production\TASK-101\imc-n\<run-id>\`, followed by reopen/digest verification;
- recorded resolved roots and intentional residuals;
- native negative/recovery tests and independent DEV-4 review.

### IMC-L — one-operation capability/lease issuer

Requires accepted native current custody readback plus independently bound TASK-100/TASK-014/TASK-075 consumer contracts. Observation and inference are separate purposes with separate capability types and transition/readback evidence.

## 9. Acceptance matrix

Independent design review must verify at least:

- existing-model import never fabricates TASK-084 training terminal/reservation/H3 lineage;
- TASK-046 approval/Consent/rights and TASK-100/TASK-075 execution responsibilities remain external;
- exact two-role pair inventory; no filename-only or server-health admission;
- public records and self-hashes never become capabilities;
- observation capability and inference load lease remain disjoint;
- wrong issuer/type/version/variant/operation/consumer, replay, expiry and double-open fail closed;
- partial pair, pair-role crossing, source/destination swap, reparse/hardlink, collision, changed physical identity, wrong hash/size, flush/readback failure and crash/UNKNOWN fail closed;
- zero foreign overwrite/delete/repair, zero path/key/private-body leakage;
- drive-root placement is rejected before effects;
- every future native run persists and rereads public-safe external Evidence;
- Product/Shell, model load, inference, audio, Release, Deploy and Production remain outside IMC-D.

Critical and High findings must be zero before IMC-D acceptance.
