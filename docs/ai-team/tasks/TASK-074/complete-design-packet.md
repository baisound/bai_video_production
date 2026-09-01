# TASK-074 Complete Design Packet R9

Status: `DESIGN_CANDIDATE_R9 / DEV-4 / SOURCE_START0 / EFFECT0`

## 1. Decision

TASK-074はOwner Voice routeの「実行前authority boundary」を所有する。具体的には、current VoiceProfileに対するlocal route selectionと、local inferenceへ渡すprivate reference materialの準備・失効境界である。

このTaskは次を新しいcanonical truthにしない。

- VoiceProfile、Consent、recording session、Dataset、ModelCandidate;
- Product Project、SQLite、Job、Asset、Timeline、Export;
- model/runtime installation、live compute admission、inference、WAV、playback;
- Human authorityやone-shot machine ticket;
- absolute path、raw audio/transcript、secret/key/bodyを含むpublic record。

TASK-074のpublic outputはbody-free projection、private outputはsame-processのnon-transferable capabilityだけである。

## 2. Frozen source reconciliation

| Fact | Design-start result |
|---|---|
| repository | `BAI VIDEO PRODUCTION` |
| exact origin/main | `70ba9e369887d3d7ded59e7197d20d133b2b4d38` |
| dedicated worktree | `.worktrees/task-074-owner-voice-authority-selection-design` |
| branch | `codex/task-074-owner-voice-authority-selection-design` |
| branch vs origin/main at design start | exact, clean |
| prior TASK-074 branch/worktree/PR/artifact | none found |
| root checkout | stale and unknown dirty; preserve, mutation zero |
| TASK-071 design | `DESIGN_COMPLETE/SOURCE_START0`, closed V1 registry only; not canonical source |
| TASK-072 design | `DESIGN_COMPLETE/SOURCE_START0`, closed V1 profiles only; not canonical source |
| TASK-073 D2 | non-authoritative composition; allocates TASK-074/075/076 |
| TASK-068 | `IMMUTABLE_ONLY_V1`; mutable CAS/delete unavailable |
| P0-E canonical bootstrap port | required for real persistence, not yet canonical |

TASK-071 packet SHA-256 at reconciliation was `B006D4426F97980AF958F18167EA0CE28C348C879EB00D98B26A6244FD6BB4D8` on design HEAD `91b84c3d...`。TASK-072 packet SHA-256 was `4F6F21E97D96AA3FFCA16F57679ABF80D081DE6D85D599347FD955C8899CE3C7` on design HEAD `52203bc9...`。これらはdependency design evidenceであり、source authorityではない。

## 3. Dependency and authority gates

| Gate | Required private fact | Absent result |
|---|---|---|
| G01 Project bootstrap | terminal `CANONICAL_PROJECT_STORE_BOOTSTRAP_V1` + fresh trusted readback | durable selection unavailable; live one-operation plan remains possible |
| G02 Installed startup | fresh private `INSTALLED_STARTUP_CONTEXT_V1` for same build/instance/session/consumer | installed route binding unavailable |
| G03 VoiceProfile | exact current TASK-046 `VoiceProfileRevision` + store/currentness digest | selection/reference unavailable |
| G04 Consent | current subject/purpose/use-class evaluation, exact evidence digest | private read zero |
| G05 Local route | current TASK-013 catalog item + installed binding + exact license evidence | runnable false |
| G06 Human action | TASK-071 V2 live broker receipt for exact gated action | gated mutation zero |
| G07 operation ticket | TASK-072 V2 one-shot private ticket/profile | mutation/child effect zero |
| G08 private custody | trusted picker/resolver + pinned source handle + approved encryption/DACL custody capability | reference prepare zero |
| G09 purge | revoked prepared-reference head or retained-failure recovery head + exact-owned identity + separate purge authorization | delete zero |
| G10 TASK-046 amendment | `TASK046_VOICE_ROUTE_SELECTION_AMENDMENT_ACCEPTANCE_V1` for exact ABI/hash/owner/writer | no canonical selection record |
| G11 TASK-075 consumer | route-neutral `TASK074_TO_TASK075_EXECUTION_INPUT_V1` exact ABI hash and TASK-075 owner acceptance | inference handoff unavailable |
| G12 trusted time | `OWNER_VOICE_TRUSTED_TIME_RECEIPT_V1` from the fixed TASK-074 Windows broker | expiry/lease transition unavailable; no validity extension |
| G13 execution currentness | live `OWNER_VOICE_AGGREGATE_CURRENTNESS_LEASE_V1` from all named producer ports | TASK-075 executable handoff zero |
| G14 reference transcript | current TASK-046 `TASK046_OWNER_REFERENCE_TRANSCRIPT_BINDING_V1` acceptance for exact body digest、audio binding、Human verification and ABI | reference preparation/private body read zero |

`P0E_PROJECT_BOOTSTRAP_FIXTURE_V1`と`INSTALLED_STARTUP_CONTEXT_FIXTURE_V1`はpure testsだけで使える。closed fields、`fixture_only=true`、`authority_created=false`、`production_eligible=false`、effect falseを要求し、copy/serialize/deserialize/subclass/replay/wrong consumer/currentnessを拒否する。fixtureはG01/G02を満たさない。

## 4. Voice route selection contract

### 4.1 Canonical record

`VOICE_PROFILE_ROUTE_SELECTION_V1`はappend-only logical revisionであり、TASK-046 Voice domainの限定amendmentとしてTASK-074が定義する。

Closed fields:

- `contract_version = VOICE_PROFILE_ROUTE_SELECTION_V1`;
- `project_id`;
- `project_manifest_revision_sha256`;
- `voice_profile_id`;
- `voice_profile_revision`;
- `voice_profile_revision_sha256`;
- `consent_revision_sha256`;
- `consent_current_evaluation_sha256`;
- `consent_evaluated_at` and `consent_expires_at` from the trusted evaluator;
- `selection_revision`;
- `predecessor_selection_sha256` (`null` only at revision 1);
- `route_mode = ZERO_SHOT_LOCAL | FINE_TUNED_LOCAL`;
- `public_route_key` (TASK-013 narration inventory identity only);
- `installed_route_binding_sha256`;
- `local_audio_model_inventory_revision_sha256`;
- `local_audio_model_inventory_entry_sha256`;
- `model_license_evidence_sha256`;
- `source_requirement = PRIVATE_REFERENCE_REQUIRED | MODEL_CANDIDATE_REQUIRED`;
- `model_candidate_revision_sha256` (required only for fine-tuned);
- `model_candidate_currentness_sha256` (required only for fine-tuned);
- `compute_preference_ref = AUTO | CPU | GPU`;
- `saved = true`;
- `created_at` from trusted producer;
- `selection_sha256` over the canonical body;
- fixed false boundary flags: `authority_created`, `runtime_loaded`, `model_downloaded`, `model_probed`, `training_started`, `inference_started`, `audio_body_persisted`, `path_persisted`。

Rules:

- `ZERO_SHOT_LOCAL` requires `PRIVATE_REFERENCE_REQUIRED` and null ModelCandidate;
- `FINE_TUNED_LOCAL` requires `MODEL_CANDIDATE_REQUIRED` and exact current approved ModelCandidate revision;
- durable record always has `saved=true`; fixture and live one-operation plans are different types and never enter this record;
- `compute_preference_ref` is a preference only。effective CPU/GPU/backend successを主張しない;
- `public_route_key` is inventory identity only。installed/runtime authorityを主張しない;
- `public_route_key`はcentral AiConnection `route_id`ではなく、AiConnection storeへ保存しない;
- save、hash、schema validationでdownload/load/probe/train/inferを起こさない。

### 4.2 CAS and readback

Durable saveはTASK-043 canonical Project store ownerが供給する`CANONICAL_PROJECT_TRANSACTION_PORT_V1`上の`VOICE_ROUTE_SELECTION_STORE_PORT_V1` private capabilityを使う。TASK-036/P0-Eはbootstrap/context consumerとProduct integration ownerであり、store authorityは`0`。

```text
read current producer snapshots
→ construct next append-only selection revision
→ atomically compare only expected Project transaction head + selection head
→ one canonical Project/SQLite transaction
→ pinned readback of exact committed revision
→ compare all closed fields/self-hash
→ fresh aggregate evaluation of VoiceProfile/Consent/inventory/license/install
  and ModelCandidate snapshots
→ issue private store receipt with runnable-current=false on any drift
```

The port owns persistence and Project/selection transaction currentness; TASK-074 validators own selection semantics. VoiceProfile、Consent、inventory、license、install and ModelCandidate are immutable snapshot bindings in the saved record, not participants in one false cross-store transaction. A saved selection may immediately become stale and remain `saved=true` while `runnable_current=false`; it is never rolled back or silently refreshed. Caller may not supply a database path, table, connection, transaction, trusted time or current head. TASK-074 creates no JSON settings file and does not reuse `VoiceProfileRevisionStore` as a second route-selection store.

This R9 design does not claim that current `SQLiteProductStore` or `ProductProjectManifestStore` already implements this port. The real adapter stays `NOT_CONFIRMED` until the TASK-043 store owner publishes exact `CANONICAL_PROJECT_STORE_BOOTSTRAP_V1` and `CANONICAL_PROJECT_TRANSACTION_PORT_V1` completion receipts. TASK-036 may consume them but cannot mint them。

The record semantics and canonical owner remain TASK-046. TASK-074 is the Owner-assigned bounded implementation writer for new TASK-074 files only and requires `TASK046_VOICE_ROUTE_SELECTION_AMENDMENT_ACCEPTANCE_V1` binding the exact record/store-port ABI hashes. Existing TASK-046 source stays unchanged unless a future explicit cross-owner Allowed-File amendment says otherwise。

CAS rejects:

- missing expected head;
- stale Project transaction or selection head;
- non-contiguous revision or wrong predecessor;
- first-writer race, duplicate, concurrent write;
- post-commit readback mismatch;
- store/manifest swap or unavailable pinned identity;
- caller path/connection/current-time/current-head injection。

`VOICE_ROUTE_SELECTION_CURRENTNESS_EVALUATION_V1` separately compares every saved snapshot with fresh producer readbacks. Missing、stale、expired or unapproved VoiceProfile/Consent/inventory/license/install/ModelCandidate makes `runnable_current=false` without mutating the saved revision. Actual TASK-075 admission additionally requires live `OWNER_VOICE_AGGREGATE_CURRENTNESS_LEASE_V1` acquired in fixed order `Project → VoiceProfile/Consent → inventory/license/install → ModelCandidate when applicable → reference lifecycle`. `AggregateCurrentnessLease` is exactly `ACQUIRING | ACTIVE | RELEASED | BURNED | FAILED_CLOSED`; partial acquisition releases already-acquired producer leases and ends `FAILED_CLOSED`。`ACTIVE` is held through TASK-075 authenticated entry and exact input-handle pin, after which it becomes `RELEASED`; producer revocation/currentness change waits or marks its own pending state but cannot produce two winners. Each producer must accept the exact lease ABI; otherwise G13 stays open and execution effect is zero。

### 4.3 Unsaved fixtures and live one-operation plan

`VOICE_PROFILE_ROUTE_SELECTION_EPHEMERAL_FIXTURE_V1` is fixture-only、`saved=false`、non-executable and can never satisfy TASK-075 authority。

Separately、`ONE_OPERATION_VOICE_ROUTE_PLAN_V1` is a live private plan that permits exactly one TASK-075 operation even while durable CAS is unavailable. It requires current live TASK-071 authorization、TASK-072 one-shot ticket、Project、VoiceProfile、Consent、TASK-013 inventory、installed route/license and G13 aggregate currentness lease. It binds one Product build/installed instance/process/session/consumer/operation and one route/reference or ModelCandidate. It is nonserializable、noncopyable、nonpickleable、restart-invalid and expires once inside the trusted broker. It never survives Product restart and never claims persistence. Public UI shows `保存済み: いいえ / 今回のみ使用`。

The plan reaches TASK-075 only through private live `TASK074_ONE_OPERATION_EXECUTION_HANDOFF_V1`, never through `TASK074_OWNER_VOICE_AUTHORITY_COMPLETION_RECEIPT_V1`. The handoff binds `saved=false`、the exact plan/lease/ticket/Human/currentness/route-input fingerprints、consumer/build/protocol、one semantic operation key and `RoutePlanLease=ISSUED`。`RoutePlanLease` is exactly `ISSUED | IN_FLIGHT | CONSUMED | BURNED | FAILED_CLOSED`, with edges `ISSUED→IN_FLIGHT|BURNED|FAILED_CLOSED` and `IN_FLIGHT→CONSUMED|BURNED|FAILED_CLOSED`; terminals have no outgoing edge. It is separate from Reference `CapabilityLease` and AggregateCurrentnessLease。The handoff is one-use、nonserializable and non-public. TASK-075's outer durability union admits exactly one of `DURABLE_SELECTION_HANDOFF_V1` or `TASK074_ONE_OPERATION_EXECUTION_HANDOFF_V1`; inside either outer variant, the route-input union independently admits exactly one of `ZERO_SHOT_REFERENCE_INPUT_V1` or `FINE_TUNED_MODEL_INPUT_V1`. Supplying both or neither at either union level is effect zero。

Durable selection CAS has exactly one bounded Product-data mutation. The live one-operation plan and fixture have persistence effect zero. Human authorization is not required merely to change a non-executing selection, but durable CAS still requires TASK-072 one-shot operation admission and canonical transaction currentness。

## 5. Private reference lifecycle

### 5.1 Ownership split

TASK-074 owns inference-reference preparation only. It does not own TASK-046 recording-session/Dataset capture lifecycle or TASK-003 Asset truth.

Source classifications apply to one audio/transcript pair:

- `TASK046_PRIVATE_RECORDING_REFERENCE`: source admitted from the exact current TASK-046 private selected-source/review lineage;
- `TASK003_PRIVATE_ASSET_REFERENCE`: source admitted through an exact private Asset capability and current rights/Consent;
- `TRUSTED_PICKER_EXTERNAL_REFERENCE`: source opened through a trusted picker/resolver for one authorized import operation。

TASK-046 remains the canonical semantic owner of the exact transcript revision、digest、speaker/profile relation and Human assertion that the text matches the selected audio. TASK-074 owns only private transcript-body custody and one-use delivery. `TASK046_OWNER_REFERENCE_TRANSCRIPT_BINDING_V1` is a closed amendment acceptance containing no body/path and must bind exact VoiceProfile、Consent、audio source identity、transcript revision、UTF-8 body sha256、policy sha256 and Human verification receipt. No classification accepts a caller string path, URI, UNC, environment variable, registry text or public hash as audio or transcript authority.

### 5.2 Lifecycle states

`ReferenceLifecycle` is exactly:

```text
UNBOUND
  → PREPARE_PLANNED
  → PREPARING
  → PREPARED | PREPARE_FAILED_NO_DERIVATIVE | PREPARE_FAILED_RETAINED

PREPARED
  → REVOKED                         (revoke wins with no active lease)
  → REVOKE_PENDING → REVOKED        (lease already owns body-read budget)

PREPARE_FAILED_RETAINED
  → PURGE_PENDING
  → PURGED | PURGE_NOT_CONFIRMED    (exact recovery head + new Human purge action)

REVOKED
  → PURGE_PENDING
  → PURGED | PURGE_NOT_CONFIRMED

PURGE_NOT_CONFIRMED + RO=PUBLISHED|KEY_REVOKED|RECOVERABLE_RETAINED
  → PURGE_PENDING                   (new Human purge action + exact recoverable-owned predecessor)

PURGE_NOT_CONFIRMED + RO=FOREIGN_PRESERVED
  → [terminal; no outgoing edge and no re-purge]
```

There is no `AVAILABLE` alias and no generic `RECONCILIATION_REQUIRED` ReferenceLifecycle value. Transitions are monotonic and bind exact operation id、previous lifecycle head、Project、VoiceProfile、Consent、source identity and retained-object ledger digest. Failure never rewinds or silently retries. A new attempt requires a new operation/ticket/Human action where applicable.

### 5.3 Preparation sequence

`OWNER_VOICE_REFERENCE_PREPARE_V1` and `task074.owner_voice.reference.prepare` admit exactly one sequence:

1. revalidate Project/install/VoiceProfile/Consent/current route;
2. trusted resolver opens one no-follow pinned audio source handle and one no-follow pinned transcript source handle from the same accepted pair binding;
3. verify both regular-file identities、audio media facts and transcript encoding/body bounds against exact `OWNER_VOICE_REFERENCE_MEDIA_POLICY_V1`;
4. classify import versus in-place source without exposing its path;
5. open and pin the approved private root, then verify its exact identity、current Windows owner and DACL receipt before creating any child;
6. before any child creation, CAS-persist、flush and read back `OWNER_VOICE_REFERENCE_PRECREATE_RESERVATION_V1` through the TASK-043 domain port; it binds the exact operation、expected lifecycle head、pinned private-root identity/custody generation、the two closed roles and two opaque intended object identities, but no path/body/key;
7. create each role's operation-owned no-replace ciphertext temp relative to the already-pinned root handle, pin its opened identity, and immediately CAS that exact identity into the durable reservation before any plaintext read or encrypted write;
8. stream each plaintext directly from its recorded pinned source into its recorded role-specific ciphertext temp using `AES-256-GCM`; each object gets its own CSPRNG 256-bit key and unique 96-bit nonce, and no plaintext temp or aggregate body materialization is permitted;
9. wrap each object key separately with Windows DPAPI `CurrentUser` using domain-separated entropy derived from fixed Product/Task/schema/role labels plus exact install/project/reference identifiers; raw keys are never persisted or logged;
10. fsync/flush both ciphertext objects and wrapped-key metadata, perform role-specific pinned identity/hash/authentication readback, then atomically publish the pair ledger only after both no-replace objects are published inside the approved private root;
11. verify DACL/current Windows user identity and custody recovery readback;
12. under the shared lease CAS, atomically transfer ownership of both opened/pinned published-derivative handles from the preparation operation to the trusted broker and publish one private in-process broker capability plus body-free public projection; pair transfer is all-or-none;
13. close operation-local source/root/temp handles only and return a terminal preparation receipt; transferred derivative handles are never closed by the preparation operation。
The existing credential vault is not an audio/transcript vault: its bounded generic-credential blob store must not hold audio、transcript、object keys、wrapped keys or host paths. TASK-074 implements a separate bounded streaming custody broker and does not reuse that vault。A one-object success is never `PREPARED`; it is `PREPARE_FAILED_RETAINED` until exact pair recovery or Human-gated purge. A crash after durable reservation but before child creation closes the reservation as `PREPARE_FAILED_NO_DERIVATIVE` after pinned absence readback. An object observed after restart without the exact reservation+created-identity CAS is `FOREIGN_PRESERVED`, is never adopted as task-owned, and has delete/re-purge authority zero. An exact recorded created identity recovers only through `RECONCILIATION_REQUIRED` and the original operation ledger.

### 5.3.1 Frozen media/body policy

`OWNER_VOICE_REFERENCE_MEDIA_POLICY_V1` is closed and its canonical sha256 is bound into the preparation plan、TASK-046 transcript amendment、pair ledger、private capability and TASK-075 handoff:

- audio container signature is RIFF/WAVE, with exactly one audio stream and no video/data stream;
- codec tuple is exactly either `pcm_s16le / signed-integer / 16 bits` or `pcm_s24le / signed-integer / 24 valid bits`; compressed、float and extensible tuples without an exact valid-bit readback are rejected;
- sample rate is one of `16000 | 22050 | 24000 | 32000 | 44100 | 48000` Hz and channel layout is exactly one mono channel;
- duration is inclusive `1_000..60_000` ms, decoded frame count is `1..2_880_000`, and complete container size is `45..8_704_000` bytes;
- transcript is strict UTF-8 without BOM, NFC, LF-only, contains no NUL or control code other than LF, is `1..4_000` Unicode scalar values and `1..16_384` UTF-8 bytes;
- transcript sha256 is over the exact admitted UTF-8 bytes; no trim、case conversion、normalization or line-ending rewrite occurs after admission;
- the transcript amendment must assert exact speaker/profile and exact-audio match; TASK-074 does not infer that semantic fact from length or media metadata。

All numeric bounds are inclusive. The policy version and sha256, probed facts, exact audio sha256, exact transcript sha256 and the TASK-046 transcript-binding receipt sha256 are required positive-oracle inputs; a caller-supplied policy or partial policy is authority zero.

### 5.4 Private capability

`OWNER_VOICE_REFERENCE_CAPABILITY_V1` is not a Python dataclass/hash/module token. It is a paired live object held by a trusted broker instance and coupled to two role-separated opened/pinned OS handles plus private broker state:

- exact build/installed instance/process/session/consumer;
- exact Project/VoiceProfile/Consent/selection/preparation operation;
- exact owned encrypted audio and encrypted transcript handles、pair-ledger identity and custody generation;
- exact reference audio sha256、transcript UTF-8 sha256、TASK-046 transcript-binding receipt sha256 and media-policy sha256;
- admitted media and transcript facts required by TASK-014/TASK-075;
- exactly two broker-only roles, `REFERENCE_AUDIO_READ_HANDLE` and `REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`; the transcript reader is strict UTF-8、bounded by the frozen byte/scalar limits and cannot be opened independently of the pair lease;
- expires once, deny replay, consume-on-success-or-exception;
- `CapabilityLease` is exactly `NONE | ISSUED | IN_FLIGHT | BODY_READ_STARTED | CONSUMED | BURNED | FAILED_CLOSED`;
- allowed edges are `NONE→ISSUED`、`ISSUED→IN_FLIGHT|BURNED|FAILED_CLOSED`、`IN_FLIGHT→BODY_READ_STARTED|BURNED|FAILED_CLOSED`、`BODY_READ_STARTED→CONSUMED|BURNED|FAILED_CLOSED`; terminal states have no outgoing edge;
- copy、deepcopy、pickle、serialization、subclass、reflection-based reconstruction、second/concurrent entry and reuse after exception all fail closed;
- no public constructor or public rehydration path;
- contains no caller-accessible absolute path, raw body, plaintext or key。

Capability publication and handle ownership transfer are one atomic broker transaction: before transfer the preparation operation exclusively owns and closes both derivative handles on every failure; after transfer the broker exclusively owns them. `CONSUMED` closes both handles after both readers close, `BURNED|FAILED_CLOSED` closes both immediately after aborting readers, and revoke/expiry closes both when the winning lease reaches its terminal state. Broker/process restart invalidates the live capability and the broker recovery owner closes any surviving exact-owned handles; no caller、receipt or preparation cleanup may close or reuse a transferred handle. A partial transfer is impossible and publication failure leaves ownership with the preparation operation.

Public mapping/hash/dataclass/schema cannot recreate it. A body-free receipt alone never permits private audio or transcript read. TASK-075 authenticates once and uses the two already-opened/pinned broker-owned role handles, then reads both streams inside the same process and lease; no argv、environment variable、path、URI、base64、public mapping or intermediate plaintext file may carry either body. Opening either stream advances the shared lease to `BODY_READ_STARTED`; exception、digest mismatch or only-one-role read burns the whole pair.

Consume versus revoke uses one TASK-074 broker/domain lease. `ReferenceLifecycle=PREPARED` plus `CapabilityLease=ISSUED` may CAS the lease to `IN_FLIGHT`; a revoke may CAS the lifecycle to `REVOKED` only while the lease is `NONE|ISSUED` and atomically burns `ISSUED`. Both cannot win. Once `IN_FLIGHT` wins, the broker confirms its already-owned pinned handle pair and either advances to `BODY_READ_STARTED` or burns before returning either body reader. A simultaneous revoke changes only ReferenceLifecycle to `REVOKE_PENDING`, blocks every new lease and waits for the already-owned lease terminal, then the broker atomically closes both handles and finalizes `REVOKED`。TASK-074 trusted broker owns CapabilityLease CAS and transferred-handle close; TASK-074 `OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_V1` over the TASK-043 port owns durable ReferenceLifecycle CAS。

### 5.5 Retention, revocation and purge

- retention is a closed enum: `UNTIL_EXPLICIT_REVOKE`、`UNTIL_PROJECT_DELETE_HUMAN_GATED` or `OWNER_SELECTED_EXPIRY`。No default auto-delete;
- every policy has `retention_policy_revision_sha256`; expiry uses trusted producer time and an exact `expires_at` only for `OWNER_SELECTED_EXPIRY`;
- `PREPARED` retains only the encrypted audio/transcript pair、their separately wrapped per-object keys and minimum body-free pair ledger required by that explicit policy;
- source owned by TASK-046/TASK-003/external user is never deleted by TASK-074;
- `OWNER_VOICE_REFERENCE_REVOKE_V1` immediately makes all unconsumed capabilities unusable and appends a revoked head;
- revocation does not claim ciphertext deletion;
- `OWNER_VOICE_REFERENCE_PURGE_V1` is a distinct Human-gated action after terminal revoke readback for a prepared reference, or after an exact `PREPARE_FAILED_RETAINED`/retained-object recovery head for a failed preparation;
- purge may delete only the two operation-owned role objects whose opened identities, custody generation and pair-ledger entries all match;
- reparse/symlink/hardlink/foreign replacement/missing identity/unknown open handle yields `PURGE_NOT_CONFIRMED` and delete zero;
- immutable published receipts and audit records are not deleted;
- purge ordering is fixed: eligible revoked/recovery head readback → deny/burn all capabilities → revoke/delete both role-specific DPAPI-wrapped key records with exact readback → delete both exact-owned ciphertext objects → parent directory durability flush → pair absence/readback receipt;
- if either role key revocation succeeds but either ciphertext deletion does not, remaining ciphertext is retained and state is `PURGE_NOT_CONFIRMED`; no replacement is deleted;
- purge success requires key-revocation and ciphertext absence readbacks for both roles;
- `NOT_EXECUTED` or missing readback remains `NOT_CONFIRMED`, never PASS。

Retained encrypted objects use a separate closed lifecycle:

```text
NONE → ALLOCATED → ENCRYPTED_UNPUBLISHED → PUBLISHED → KEY_REVOKED → PURGED

ALLOCATED | ENCRYPTED_UNPUBLISHED | PUBLISHED
  → RECONCILIATION_REQUIRED
  → RECOVERABLE_RETAINED | FOREIGN_PRESERVED

RECOVERABLE_RETAINED
  → PUBLISHED | KEY_REVOKED
```

`RetainedObject` is the aggregate pair-ledger state, not one role's success bit, and is exactly `NONE | ALLOCATED | ENCRYPTED_UNPUBLISHED | PUBLISHED | RECONCILIATION_REQUIRED | RECOVERABLE_RETAINED | KEY_REVOKED | PURGED | FOREIGN_PRESERVED`。`PUBLISHED` requires both authenticated role objects and the pair ledger; `KEY_REVOKED` and `PURGED` require both roles' readbacks. `FOREIGN_PRESERVED` and `PURGED` are terminal. Any F05-F07/F24 fault with an exact reservation+created-identity CAS moves through `RECONCILIATION_REQUIRED`; missing identity CAS or unknown/foreign identity becomes `FOREIGN_PRESERVED` and delete/re-purge is zero. `RECOVERABLE_RETAINED` may finish pair publish only when every original operation/currentness fact matches, or a separate purge authorization may transition through `KEY_REVOKED → PURGED` without fabricating a `REVOKED` reference head. TASK-074 `OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_V1` owns durable reservation、created-identity and RetainedObject CAS。

Cross-field invariants are the following complete table. `RL`、`CL` and `RO` are typed namespaces. Repeated text such as `NONE` or `PURGED` may exist in different namespaces but is never interchangeable across types。

| ReferenceLifecycle (`RL`) | Allowed CapabilityLease (`CL`) | Allowed RetainedObject (`RO`) | Required predecessor/receipt guard |
|---|---|---|---|
| `UNBOUND` | `NONE` | `NONE` | initial identity; no predecessor |
| `PREPARE_PLANNED` | `NONE` | `NONE` | `UNBOUND` + exact current plan/Human/ticket receipts |
| `PREPARING` | `NONE` | `NONE｜ALLOCATED｜ENCRYPTED_UNPUBLISHED` | `PREPARE_PLANNED` + exact prepare operation/currentness |
| `PREPARED` | `NONE｜ISSUED｜IN_FLIGHT｜BODY_READ_STARTED｜CONSUMED｜BURNED｜FAILED_CLOSED` | `PUBLISHED` | `PREPARING` + custody/DACL/pinned readback completion |
| `PREPARE_FAILED_NO_DERIVATIVE` | `NONE` | `NONE｜PURGED` | `PREPARING` + exact failure/no-retained-object readback |
| `PREPARE_FAILED_RETAINED` | `NONE` | `RECONCILIATION_REQUIRED｜RECOVERABLE_RETAINED｜KEY_REVOKED｜FOREIGN_PRESERVED` | `PREPARING` + exact failed operation and retained ledger |
| `REVOKE_PENDING` | `IN_FLIGHT｜BODY_READ_STARTED｜CONSUMED｜BURNED｜FAILED_CLOSED` | `PUBLISHED` | `PREPARED` + revoke/expiry receipt + exact active/terminal lease pending finalize |
| `REVOKED` | `NONE｜CONSUMED｜BURNED｜FAILED_CLOSED` | `PUBLISHED｜KEY_REVOKED｜PURGED｜FOREIGN_PRESERVED` | `PREPARED｜REVOKE_PENDING` + revoke/expiry terminal readback |
| `PURGE_PENDING` | `NONE｜CONSUMED｜BURNED｜FAILED_CLOSED` | `RECOVERABLE_RETAINED｜PUBLISHED｜KEY_REVOKED` | `REVOKED｜PREPARE_FAILED_RETAINED` or `PURGE_NOT_CONFIRMED` with non-foreign exact-owned RO + new exact Human purge receipt and ownership recovery |
| `PURGED` | `NONE｜CONSUMED｜BURNED｜FAILED_CLOSED` | `PURGED` | `PURGE_PENDING` + key-revocation、ciphertext absence and directory durability readbacks |
| `PURGE_NOT_CONFIRMED` | `NONE｜CONSUMED｜BURNED｜FAILED_CLOSED` | `RECOVERABLE_RETAINED｜PUBLISHED｜KEY_REVOKED｜FOREIGN_PRESERVED` | `PURGE_PENDING` + exact pre-key-revoke/key-revoked/incomplete/foreign-preserve readback; `FOREIGN_PRESERVED` makes this tuple terminal |

Any `RL × CL × RO` tuple or predecessor/receipt guard not present in this table is rejected by N40. A terminal `CL` never gains a new outgoing edge; a later operation uses a new lease identity beginning at typed `CL.NONE`。

### 5.6 Trusted time and expiry

`OWNER_VOICE_TRUSTED_TIME_RECEIPT_V1` is issued only by the fixed TASK-074 Windows broker and binds Product build、installed instance、Windows user/session/logon identity、broker boot/session、monotonic observation/deadline、bounded UTC audit value、`time_floor_revision`、`previous_time_floor_sha256`、retention policy revision and `state = PASS | ROLLBACK_DETECTED | UNAVAILABLE`。The monotonic rollback floor is persisted only through the TASK-043 canonical Project transaction port; caller time、filesystem mtime、timezone、public JSON or a packaged-test clock cannot select Production time。

`PASS` is required to issue a new CapabilityLease or prove `OWNER_SELECTED_EXPIRY`。Wall-clock rollback never extends validity; large forward jump or unavailable floor blocks new leases and returns body-free `TIME_CURRENTNESS_UNAVAILABLE` without deleting material. Same-session active leases retain their monotonic deadline; broker/Product restart burns every nonterminal lease. Proven expiry uses the same lease guard as explicit revoke: CapabilityLease `NONE` CASes `PREPARED→REVOKED`; `ISSUED` is atomically burned and CASes to `REVOKED`; `IN_FLIGHT|BODY_READ_STARTED` CASes `PREPARED→REVOKE_PENDING` and finalizes `REVOKED` after the lease terminal. Expiry never auto-deletes ciphertext or substitutes for purge authorization。

## 6. TASK-071 Human action registry amendment

TASK-074 proposes `HUMAN_ACTION_REGISTRY_V2` after TASK-071 V1 source is canonical and its owner accepts an overlap-free amendment.

| Action code | Purpose | Required exact bindings | Effect ceiling |
|---|---|---|---|
| `OWNER_VOICE_REFERENCE_PREPARE_V1` | private reference pair preparation | Project/install/session, VoiceProfile/Consent, selection, audio/transcript source class and exact identities, TASK-046 transcript binding, media policy, expected lifecycle head, expiry | one prepare operation |
| `OWNER_VOICE_LOCAL_INFERENCE_V1` | TASK-075 local synthesis | prepared audio/transcript pair or ModelCandidate, media policy, narration/admission/operation identities | one inference operation |
| `OWNER_VOICE_LISTENING_DECISION_V1` | TASK-041 accept/reject/retest value | exact WAV/QA/playback/listening coordinates | one decision |
| `OWNER_VOICE_REGENERATE_V1` | new narration attempt | accepted/rejected predecessor and new operation plan | one new attempt |
| `OWNER_VOICE_REFERENCE_REVOKE_V1` | invalidate reference capabilities | exact prepared/current lifecycle head | one revoke transition |
| `OWNER_VOICE_REFERENCE_PURGE_V1` | exact-owned derivative purge | revoked prepared head or retained-failure recovery head, retained ledger, opened identity, custody generation | one bounded purge |

All receipts are live broker state, generated by TASK-071, and bind trusted challenge/event/time. Caller-selected decision、challenge、event、time、ID or copied public receipt creates no authority. Route selection itself is not a Human action。Fixture/live-unsaved selection has persistence effect zero; durable selection CAS is one TASK-072-admitted canonical Product-data mutation。

## 7. TASK-072 consumer profile amendment

TASK-074 proposes `ACTION_REGISTRY_V2` after TASK-072 V1 source is canonical and its owner accepts an overlap-free amendment.

- `task074.owner_voice.reference.prepare`;
- `task074.owner_voice.profile_route.select`;
- `task075.owner_voice.local.inference`;
- `task075.owner_voice.private.playback`;
- `task041.owner_voice.listening.decision`;
- `task014.owner_voice.regenerate`;
- `task074.owner_voice.reference.revoke`;
- `task074.owner_voice.reference.purge`。

Every profile has a closed subcommand、consumer、action code、Product build、installed instance、operation config、budget `1`、expiry and terminal consume/revoke behavior. The zero-shot inference profile additionally binds the exact audio/transcript broker role set、media-policy sha256 and TASK-046 transcript-binding receipt sha256. Ticket state is exactly `ISSUED → ADMITTED → CONSUMED | BURNED_EXCEPTION | BURNED_TIMEOUT | CANCELLED_PRE_EFFECT | FAILED_CLOSED`; every terminal is read back from TASK-072 and is non-reusable. `CANCELLED_PRE_EFFECT` proves only that this ticket did not enter its effect; it cannot be replayed. Private-body access is allowed only for the named same-process consumer capability; argv/env/stdin/log/public receipt receive no body or path. Copy/serialization/wrong subcommand/second/concurrent use/exception reuse fails closed.

## 8. Completion receipt

### 8.1 Private terminal receipt

`TASK074_OWNER_VOICE_AUTHORITY_COMPLETION_RECEIPT_V1` is emitted only after all applicable producers for the stated completion class are current. Closed fields:

- `contract_version`;
- `task_id = TASK-074`;
- `project_id` and `project_manifest_revision_sha256`;
- `installed_startup_context_binding_sha256`;
- `voice_profile_id`, `voice_profile_revision`, `voice_profile_revision_sha256`;
- `consent_current_evaluation_sha256`;
- `route_selection_revision`, `route_selection_sha256`, `route_selection_store_receipt_sha256`;
- `reference_lifecycle_state` or exact `null` for the fine-tuned-only route;
- `reference_preparation_receipt_sha256` or `null` for fine-tuned-only route;
- `reference_capability_binding_sha256` or `null`;
- `reference_media_policy_sha256`、`reference_transcript_binding_receipt_sha256` or null only for fine-tuned-only route;
- `human_action_registry_version = HUMAN_ACTION_REGISTRY_V2`;
- `operation_profile_registry_version = ACTION_REGISTRY_V2`;
- exact registry receipt digests;
- `persistence_state = DURABLE_VERIFIED | EPHEMERAL_NOT_EXECUTABLE`;
- `private_reference_state = PREPARED_VERIFIED | NOT_REQUIRED | REVOKED | NOT_CONFIRMED`;
- `receipt_authority_kind = STATUS_ONLY`;
- fixed booleans `human_authorization_created=false`, `operation_ticket_created=false`, `execution_authorized=false`, `model_downloaded=false`, `model_loaded=false`, `model_probed=false`, `training_started=false`, `inference_started=false`, `playback_started=false`, `wav_created=false`, `asset_adopted=false`, `timeline_mutated=false`, `export_started=false`, `private_body_present=false`, `path_present=false`, `secret_present=false`, `production_eligible=false`;
- `owner_reference_verified`;
- trusted `issued_at`, expiry and `completion_sha256`。

It also carries `completion_class = TASK074_IMPLEMENTATION_COMPLETE | P0V_OWNER_REFERENCE_VERIFIED`。The first class proves reviewed source、schemas、synthetic/non-biometric native contract and canonical adapter readiness without real Owner audio and requires `owner_reference_verified=false`。The second class additionally requires a separately authorized real Owner reference preparation/readback and requires `owner_reference_verified=true`。Neither class implies TASK-075 inference、WAV、listening、Asset or Export。

Cross-field rules: `ZERO_SHOT_LOCAL` requires `private_reference_state=PREPARED_VERIFIED` only for the real-owner class; implementation completion may truthfully report `NOT_CONFIRMED` and is non-executable. `FINE_TUNED_LOCAL` requires `private_reference_state=NOT_REQUIRED` and exact approved ModelCandidate bindings. `REVOKED` is never executable. `EPHEMERAL_NOT_EXECUTABLE` never accompanies `P0V_OWNER_REFERENCE_VERIFIED`。

Terminal executable handoff requires `DURABLE_VERIFIED` and either `PREPARED_VERIFIED` for zero-shot or `NOT_REQUIRED` plus approved ModelCandidate for fine-tuned. `EPHEMERAL_NOT_EXECUTABLE` is a truthful UI fixture/read-model result only。

### 8.2 Public projection

`TASK074_OWNER_VOICE_AUTHORITY_PUBLIC_V1` contains only:

- route label/key, route mode, compute preference;
- saved yes/no;
- reference status enum;
- runnable candidate yes/no plus body-free reason codes;
- profile display alias that TASK-046 already marks public-safe;
- registry version strings;
- fixed `authority_created=false`, `execution_authorized=false`, `private_body_present=false`, `path_present=false`。

The only public digest is `public_projection_sha256`, computed over the allowlisted public projection itself. It excludes completion/selection/reference/content/Consent/registry receipt digests and all raw audio/transcript、prompt、speaker embedding、private Voice ID、Consent subject/evidence ref、absolute/relative host path、URI、file name、account、PID、handle、key、secret、model root and private diagnostic text。

### 8.3 TASK-073/TASK-075 handoff

- TASK-073 consumes only the public projection and cannot invoke reference read or inference;
- TASK-075 receives its own TASK-071/TASK-072 authorities and one exact route-neutral `TASK074_TO_TASK075_EXECUTION_INPUT_V1` envelope;
- the outer durability envelope is a closed one-of: `DURABLE_SELECTION_HANDOFF_V1` carries exact executable TASK-074 completion/selection/currentness hashes, while `TASK074_ONE_OPERATION_EXECUTION_HANDOFF_V1` carries the unsaved live plan/lease/ticket/currentness fingerprints and no completion receipt;
- both outer variants bind route mode、one semantic operation key、G13 aggregate lease and expected TASK-075 consumer/build/protocol, then contain exactly one closed route subvariant whose discriminator must equal the outer `route_mode`;
- `ZERO_SHOT_REFERENCE_INPUT_V1` requires exact prepared lifecycle/pair-ledger/capability binding、media-policy sha256、TASK-046 transcript-binding receipt sha256 and the closed broker role set `{REFERENCE_AUDIO_READ_HANDLE, REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE}`; every ModelCandidate field is exact null/absent;
- `FINE_TUNED_MODEL_INPUT_V1` requires exact approved ModelCandidate revision/currentness、installed route binding and license evidence; lifecycle/preparation/pair-ledger/capability/media-policy/transcript-binding fields are exact null and the reference role set is exactly empty, so reference body/handle read count is zero;
- neither route subvariant contains a handle value/path/body; zero-shot obtains the two live role handles only after authenticated broker entry, while fine-tuned never enters the reference broker;

The route cross-field table is complete and applies identically inside both outer durability variants:

| Route subvariant | Required non-null | Required exact null/empty | Private entry |
|---|---|---|---|
| `ZERO_SHOT_REFERENCE_INPUT_V1` | prepared lifecycle and pair-ledger hashes、reference capability binding、media-policy sha256、TASK-046 transcript-binding receipt sha256、exact two-role set | every ModelCandidate revision/currentness field | authenticate once and enter paired reference broker |
| `FINE_TUNED_MODEL_INPUT_V1` | approved ModelCandidate revision/currentness、installed route binding、license evidence | lifecycle/preparation/pair-ledger/capability/media-policy/transcript-binding fields; empty reference role set | reference broker entry/read count exactly zero |

Any field or behavior outside the selected table row, including a route discriminator disagreement with the outer envelope, is rejected before reference or model access.
- TASK-075 must freeze the envelope ABI hash、closed rejection enum and positive/invalid fixture corpus and issue owner acceptance before G11 closes;
- TASK-075 must independently revalidate Project/installed/profile/Consent/selection/reference currentness at operation admission;
- completion/plan staleness、missing aggregate lease or capability consumption burns the attempted handoff; no automatic refresh/fallback/retry。

## 9. Acceptance matrix

| ID | Acceptance |
|---|---|
| A01 | TASK-074 reuses TASK-046 VoiceProfile/Consent and creates no duplicate identity/store. |
| A02 | Selection revision is closed, checksum-bound, contiguous and predecessor-bound. |
| A03 | Durable CAS is one canonical Project/SQLite transaction with exact pinned readback. |
| A04 | No caller path/database/connection/head/time can become persistence authority. |
| A05 | Saving selection has model/audio/native effect zero. |
| A06 | Fixture selection is non-executable; live one-operation plan is visibly unsaved and permits exactly one current TASK-075 operation. |
| A07 | Zero-shot and fine-tuned source requirements cannot be mixed. |
| A08 | Private reference begins only from trusted private capability and current Consent. |
| A09 | Preparation retains both raw sources immutable and creates distinct role-separated encrypted derivatives with one aggregate pair ledger. |
| A10 | Public contracts contain no body/path/private identity/secret. |
| A11 | Reference capability is same-process, single-use, noncopyable and nonserializable. |
| A12 | Revocation invalidates use without claiming physical deletion. |
| A13 | Purge is a separate Human Gate and deletes only exact-owned derivative identity. |
| A14 | TASK-068 immutable primitives are not treated as mutable CAS or delete authority. |
| A15 | TASK-071 V2 actions and TASK-072 V2 profiles are closed and one-shot. |
| A16 | Completion receipt cannot be emitted executable from fixtures or public mappings. |
| A17 | TASK-073 receives public projection only; TASK-075 revalidates exact private currentness. |
| A18 | No download/load/probe/train/infer/playback/WAV/Asset/Timeline/Export occurs. |
| A19 | Python/schema/mirror agree and every negative/fault vector is focused-tested. |
| A20 | Independent Critic/Tester/Judge satisfy DEV-4 with C/H `0/0` before commit-ready. |
| A21 | TASK036 is only a consumer/integration owner; TASK043 is the sole canonical Project store transaction owner. |
| A22 | Implementation completion and real Owner reference verification are separate completion classes. |
| A23 | TASK-046 remains canonical route-selection semantic owner and accepts the exact TASK-074 amendment ABI. |
| A24 | Saved selection snapshots bind Consent, inventory, license, install and fine-tuned ModelCandidate; fresh evaluation/aggregate lease determine runnable currentness. |
| A25 | Consume/revoke arbitration uses one broker lease/CAS and has one winner. |
| A26 | Retained encrypted failure objects have a complete reconciliation/purge lifecycle. |
| A27 | TASK-075 accepts an exact machine-readable consumer envelope ABI and invalid corpus. |
| A28 | Unsaved live execution uses its own one-operation handoff and never masquerades as a durable completion receipt. |
| A29 | ReferenceLifecycle、CapabilityLease and RetainedObject are separate typed closed enums with complete allowed edges and cross-field tuples. |
| A30 | Trusted-time rollback/unavailability cannot extend retention or issue a new lease. |
| A31 | Failed preparation with retained ciphertext has an explicit Human-gated purge path without fabricating REVOKED. |
| A32 | Zero-shot handoff supplies one paired, same-process, nonserializable audio/transcript capability whose shared one-use lease burns on partial read or failure. |
| A33 | TASK-046 remains transcript semantic owner while TASK-074 owns encrypted transcript-body custody only; exact audio/transcript/profile/Consent binding is current. |
| A34 | `OWNER_VOICE_REFERENCE_MEDIA_POLICY_V1` freezes exact audio and transcript positive allowlists/bounds and is digest-bound end to end. |
| A35 | TASK-075 handoff has independent closed durability and route unions; zero-shot and fine-tuned fields cannot be mixed. |

## 10. Negative matrix

| ID | Condition | Required result |
|---|---|---|
| N01 | missing/unbound Project bootstrap or installed context | durable save unavailable; effect zero |
| N02 | fixture copied/serialized/deserialized/subclassed/replayed | authority zero |
| N03 | stale Project transaction or selection head | CAS zero |
| N41 | stale VoiceProfile/Consent/inventory/license/install/ModelCandidate snapshot | saved revision may remain; runnable/private read zero |
| N04 | missing expected selection head or wrong predecessor/revision | reject |
| N05 | concurrent/duplicate selection writers | one winner; loser conflict, no retry |
| N06 | unsupported route mode/source combination | reject |
| N07 | missing/unlicensed/uninstalled/hash-drifted model route | runnable false |
| N08 | GPU preference asserted as effective backend | reject claim |
| N09 | save attempts download/load/probe/train/infer | hard fail, effect zero |
| N10 | caller raw path/URI/UNC/registry/env/argv source | reject before open |
| N11 | symlink/reparse/hardlink/ancestor/inode swap | prepare/purge zero |
| N12 | wrong speaker/profile or reference transcript binding | reject |
| N13 | revoked/expired/wrong-purpose Consent | private read zero |
| N14 | wrong media/container/codec/sample-rate/channels/bit-depth/duration | no prepared receipt |
| N15 | ciphertext/source/media hash mismatch | no prepared receipt; reconcile |
| N16 | DACL/custody/recovery readback missing or UNKNOWN | no prepared receipt |
| N17 | capability copied/pickled/serialized/wrong process/session/consumer | private read zero |
| N18 | duplicate/replay/operation-id mismatch | effect zero; ticket burned per producer policy |
| N19 | revoke receipt used as purge authority | delete zero |
| N20 | in-place/external/TASK046/TASK003 source selected for purge | delete zero |
| N21 | foreign replacement or unknown owned identity at cleanup | preserve; `PURGE_NOT_CONFIRMED` |
| N22 | public receipt/log/error contains path/body/private ref/key/secret | test fail |
| N23 | public hash/dataclass/schema used to reconstruct private capability | authority zero |
| N24 | completion emitted from ephemeral persistence or missing registry amendment | reject |
| N25 | TASK-073 calls private reference or TASK-075 skips revalidation | test/design fail |
| N26 | reference preparation starts Dataset adoption/training | hard fail |
| N27 | accepted reference/WAV auto-adopts Asset/Timeline/Export | hard fail |
| N28 | credential vault used as audio/key/path store outside its contract | reject |
| N29 | Python token/dataclass/hash/reflection reconstruction used as private capability | authority zero |
| N30 | live one-operation plan reused after restart/exception/concurrent entry | broker state burns; effect zero for loser |
| N31 | DPAPI scope is not CurrentUser or entropy/identity binding mismatches | no custody receipt |
| N32 | plaintext temp or non-streaming unbounded plaintext materialization | hard fail |
| N33 | durable selection omits Consent/inventory/license/install/ModelCandidate currentness | reject |
| N34 | consume and revoke both claim the same reference budget | one CAS winner; loser fail closed |
| N35 | reservation/created-identity CAS or retained ledger/lifecycle head is missing | completion fail; unrecorded object is `FOREIGN_PRESERVED`, delete/re-purge zero |
| N36 | TASK-075 ABI hash/consumer acceptance missing or mismatched | inference handoff zero |
| N37 | public projection exposes any private-derived digest or any digest other than the allowlisted `public_projection_sha256` self-digest | test fail |
| N38 | durable variant carries live-only plan/lease/ticket fields, or live variant carries completion/store fields | TASK-075 handoff zero |
| N39 | live handoff lacks G13 aggregate lease or trusted-time PASS | TASK-075 handoff zero |
| N40 | enum value/edge or `RL × CL × RO × guard` tuple not explicitly listed in section 5.5 | reject |
| N42 | failed-retained purge lacks exact failed operation/recovery head/ledger/Human receipt | delete zero |
| N43 | missing/stale/wrong TASK-046 transcript binding or transcript digest/audio/profile mismatch | preparation/private read zero |
| N44 | only audio or only transcript role supplied/read, role duplicated, or role set not exact | pair lease burned; TASK-075 body/model read zero |
| N45 | transcript is non-UTF-8/BOM/non-NFC, has forbidden control, or exceeds scalar/byte bound | no prepared receipt |
| N46 | media policy version/hash missing, caller-selected, or probed facts exceed exact allowlist/bounds | no prepared receipt |
| N47 | transcript/audio body carried through argv/env/path/URI/base64/public mapping/plaintext temp | hard fail; leak test fail |
| N48 | both/neither outer durability variant or both/neither inner route subvariant, or discriminator mismatch | TASK-075 handoff zero |
| N49 | zero-shot missing/extra/wrong pair fields or any ModelCandidate field; fine-tuned missing/stale/unapproved ModelCandidate or any non-null reference field/non-empty role set | TASK-075 body/model read zero |

## 11. Fault matrix

| ID | Crash/fault seam | Required recovery truth |
|---|---|---|
| F01 | selection transaction before commit | old head remains current |
| F02 | commit before pinned readback | new success unavailable; reconcile exact store state |
| F03 | Project transaction or selection head changes during CAS | transaction aborts; no retry |
| F04 | source open before identity verification | close handle; derivative absent |
| F05 | crash after durable pre-create reservation, after child creation before identity CAS, or after identity CAS before encrypted write | reservation-only + pinned absence closes `PREPARE_FAILED_NO_DERIVATIVE`; unrecorded child is `FOREIGN_PRESERVED`; exact recorded child is ledgered `RECONCILIATION_REQUIRED`; no prepared receipt |
| F06 | encrypted write before fsync/readback | `RECONCILIATION_REQUIRED` |
| F07 | ciphertext readback before lifecycle publish | derivative retained encrypted; resume by exact operation only |
| F08 | lifecycle publish before capability issue | prepared head exists; caller receives no inferred capability |
| F09 | capability issue before consumer admission | expiry/one-shot prevents replay; TASK-075 revalidates |
| F10 | revoke races capability consume/body-read | TASK-074 broker lease/CAS determines one winner and explicit `REVOKE_PENDING` semantics |
| F11 | purge after key revoke before file delete | `PURGE_NOT_CONFIRMED`; exact recovery reads both facts |
| F12 | file delete before parent/readback | no success receipt; reconcile without deleting any replacement |
| F13 | app/Windows closes with open handle | exact producer closes/reconciles owned handle; no broad kill/delete |
| F14 | public projection races lifecycle advance | stale projection discarded; no private action |
| F15 | one-operation plan enters IN_FLIGHT then consumer throws | terminal `BURNED` or `FAILED_CLOSED`; no reuse |
| F16 | wrapped-key revoke succeeds before ciphertext delete fault | retain foreign/remaining ciphertext; `PURGE_NOT_CONFIRMED` |
| F17 | retention expiry races lease acquire | trusted-time transition and lease CAS choose one winner; no auto-delete |
| F18 | retained encrypted role derivative found after crash | exact pair-ledger reconciliation only; publish-pair-or-purge, no broad cleanup |
| F19 | selection commits while external producer advances | saved revision remains; fresh evaluation is stale/runnable false |
| F20 | one-operation handoff issued before Product/broker restart | live plan/lease burned; no reconstruction |
| F21 | aggregate producer lease lost before TASK-075 entry | handoff burned; body/model read zero |
| F22 | clock rollback/unavailable at expiry boundary | no new lease, no auto-delete, body-free N.C. status |
| F23 | failed preparation retained-object purge | exact recovery+Human action yields lifecycle/object PURGED; key-only failure stays PURGE_NOT_CONFIRMED; foreign identity stays FOREIGN_PRESERVED |
| F24 | audio ciphertext publishes but transcript ciphertext or pair-ledger publish fails | never PREPARED; exact-owned objects enter PREPARE_FAILED_RETAINED and require pair recovery/purge |
| F25 | TASK-075 reads one role then second-role decrypt/digest/decode fails | shared lease terminal BURNED/FAILED_CLOSED; no model call and no replay |

## 12. Candidate implementation architecture

### 12.1 Pure modules

- `owner_voice_authority.py`: closed action/profile amendment records, fixture admission and completion/public receipts;
- `voice_profile_route_selection.py`: selection records, ephemeral envelope, CAS request/readback validation and store-port Protocol;
- `owner_voice_private_reference.py`: lifecycle records, preparation/revoke/purge plans, trusted broker interfaces and custody-port Protocol。
- `voice_profile_route_selection_store.py`: exact adapter to the TASK-043-owned canonical transaction port; no database path/connection ownership;
- `owner_voice_private_reference_windows.py`: pinned-handle streaming AES-256-GCM、DPAPI CurrentUser key wrapping、DACL/identity、revocation and exact-owned purge broker;
- `packaging/task074_owner_voice_private_reference_windows_entry.py`: fixed packaged construction only; no caller-selected backend/path/algorithm。

All record constructors validate exact key sets、enum closure、digest shape、version、lineage and false boundary flags. Public serialization is allowlist-based, not redact-by-best-effort. Private capability authority exists only in trusted broker live state plus pinned OS handles and atomic one-use leases; a Python constructor、module token、seal、dataclass or hash provides authority zero。

### 12.2 Schemas and fixtures

Schemas cover public/body-free records only. Private live capabilities and private installed context never have a JSON schema. Canonical package mirrors live under `src/ai_video_production/schema_resources/` and must byte-match source schemas.

`tests/fixtures/task074/` may contain deterministic non-biometric metadata and tiny non-audio byte sentinels only. It must not contain WAV/PCM/voice/transcript/body/path/key/credential. TASK-075 frozen-ABI fixtures include exact public receipt examples and invalid vectors, never a live capability。

### 12.3 Real adapters

Cross-owner real adapters are deferred until their producing owners are canonical:

- TASK-071 V2 registry adapter;
- TASK-072 V2 profile/ticket adapter;
- TASK-043 `CANONICAL_PROJECT_TRANSACTION_PORT_V1` adapter;
- TASK-046 G14 `TASK046_OWNER_REFERENCE_TRANSCRIPT_BINDING_V1` producer acceptance/adapter;
- TASK-075 G11 exact consumer-envelope ABI owner acceptance for executable handoff。

TASK-074 itself owns the bounded Windows trusted picker/private custody/DACL/exact-owned purge broker files listed in `task.md`; real Owner-audio execution remains Human-gated。

Absence of any adapter reports `NOT_CONFIRMED` and cannot be replaced by a fake in Product runtime。

## 13. Verification plan

Order:

1. `python -m compileall` for new modules/tests;
2. schema parse and source/mirror byte equality;
3. focused positive tests for selection、reference lifecycle、registry amendments、completion/public receipts;
4. every N01-N49 negative vector;
5. every F01-F25 fault/recovery seam with in-memory deterministic fakes;
6. TASK-046 VoiceProfile/recording focused regression;
7. TASK-014 local preflight/render-admission/callable focused regression;
8. TASK-071/TASK-072 fixture consumer tests when canonical;
9. TASK-073/TASK-075 frozen-ABI consumer tests;
10. secret/path/body leakage scans and changed-files/Allowed-Files check;
11. independent Tester;
12. implementation Critic and Judge。

Non-biometric Windows custody/DACL/purge contract tests are required for `TASK074_IMPLEMENTATION_COMPLETE`。Real Owner private/native tests remain `NOT_EXECUTED / NOT_CONFIRMED` until the separate Human Gate and are reported only as `P0V_OWNER_REFERENCE_VERIFIED`。

N44/F25 are one mandatory paired-consumer test, not two shallow field checks: a deterministic broker fake opens the first role, injects second-role decrypt/digest/decode failure, proves the shared lease is terminal `BURNED|FAILED_CLOSED`, proves TASK-075 model-call count remains `0`, and proves replay/read count remains `0` after the failed attempt. N43/N45-N49 and F24 likewise require executable table-driven fixtures; N48/N49 fixtures cover both durable and live outer variants and assert reference-broker entry count zero for every fine-tuned case. A matrix row without a focused assertion does not satisfy A19.

## 14. Review and implementation gates

### Design freeze gate

- exact packet hash frozen;
- Design A authority review;
- Design B security/privacy/I/O review;
- independent Montage Critic/Judge;
- unresolved Critical/High `0/0` and Judge `PASS`;
- source change `0`。

### Pure implementation gate

- design freeze gate PASS;
- fresh origin/main/branch/worktree/dirty/PR/lock/Allowed-Files audit;
- only TASK074-B new files;
- no native/private/model effect。

### Canonical binding gate

- TASK-071/TASK-072/P0-E/store producer exact completion receipts canonical;
- TASK-046 owner accepts the exact G14 transcript-binding ABI and publishes a current body-free producer receipt;
- executable TASK-075 handoff additionally requires G11 exact route-neutral envelope ABI hash、closed rejection enum、metadata-only fixture corpus covering both outer variants × both route subvariants and TASK-075 owner acceptance;
- cross-owner locks and sole-writers explicit;
- same Task/PR remains current or the design is re-reviewed;
- no TASK-036/UI mutation。

### Commit-ready gate

- all required implementation tests pass;
- independent Tester/Critic/Judge complete;
- C/H `0/0`;
- diff/scope/schema mirror/leakage checks pass;
- real Gates truthfully separated;
- one TASK-074 branch and one Draft PR;
- Japanese commit/PR text, no force push。

## 15. Exact resume conditions

If mutation is parked, resume only after:

1. dedicated worktree remains clean except owned TASK-074 files;
2. origin/main and dependency heads are freshly reconciled;
3. no active PR/worktree/sole-writer overlaps Allowed Files;
4. exact reviewed design hashes still match;
5. the required producer receipt and Human Gate for that specific effect are current;
6. private paths/bodies/secrets are not present in task-local artifacts。

Unknown dirty ownership、changed dependency ABI、missing private store/custody port、or failed C/H/Judge parks only that effect. It never becomes PASS by inference。
