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

Future IMC-I may define the following strict body-free record family. Exact schemas and canonical preimages must be frozen before implementation.

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

## 5. Capability separation

### 5.1 `INSTALLED_IDENTITY_OBSERVATION`

TASK-101 is the custody issuer for a non-serializable, one-operation observation capability consumed by future TASK-100 C2-N. It is bound to the exact custody readback, pair, native operation, consumer and short validity window. It is read-only, one-shot, non-replayable, non-load and non-executing. It yields only bounded private handles needed to verify installed identity.

The capability is not a path token, receipt, TASK-071/072 action/ticket or inference load lease. Missing/crossed/expired/already-opened capability blocks before body access. After any open attempt it is burned; close or identity ambiguity yields `COMPLETION_UNKNOWN` and no automatic retry.

### 5.2 `LOCAL_NARRATION_INFERENCE`

Inference uses a separate non-serializable one-operation load lease. Issuance requires current sealed custody readback, exact TASK-046 ModelArtifactBinding and H4, current Consent/rights/license, admitted TASK-100 catalog/C2 assessment, exact TASK-014 FineTunedModelBinding, TASK-075 operation/admission and applicable TASK-066/TASK-071/TASK-072 evidence.

The load lease is purpose-specific, one-shot, non-replayable and operation-bound. It may provide trusted private handles only to the accepted TASK-075 child. TASK-101 neither loads the model nor infers audio. Observation and inference capabilities cannot substitute for, wrap or derive from one another.

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

## 7. Canonical encoding and parser limits

Future JSON records require strict UTF-8, duplicate-key rejection, no BOM/trailing bytes, no non-finite numbers, bounded total bytes/depth/nodes/array counts/string lengths and exact keys. Integers reject booleans. Timestamps are UTC and require `issued_at <= evaluated_at < expires_at`; native completion/readback timestamps must be monotonic within their trusted-time contract.

Every digest uses `sha256:` plus 64 lowercase hex and a unique domain-separated canonical JSON preimage containing contract version and record type. Different record types, variants or revisions cannot share a digest domain. Unknown versions and fields are rejected.

## 8. Atomic units and start gates

### IMC-I — pure contract and fake backend

May start only after this design is independently accepted and an implementation owner is allocated. Its exact future files are proposed as:

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
