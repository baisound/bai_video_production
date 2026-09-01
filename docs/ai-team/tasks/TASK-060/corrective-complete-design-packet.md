# TASK-060 — Promotion Authority and Secure Source Corrective Design

Status: `DESIGN_REVIEW_READY_R6 / DEV-4 / DEPENDENCY_NC / INDEPENDENT_REVIEW_PENDING_R6 / SOURCE_START0 / NATIVE0`

Design identity: `TASK060-PTD-PROMOTION-AUTHORITY-SECURE-SOURCE-V6`

Canonical design base: `origin/main@19c37245a1444f6f3ed5f3b707eeea94e68602b0`

Owner allocation: `2026-09-01 / Platform Trust & Delivery / Design B`

## 1. Decision

TASK-060 remains the owner of Human-approved Preference promotion and rollback,
the encrypted promotion history, and the exact read-only promoted source. The
historical PP-A/PP-B/PP-C evidence remains evidence. It does not create current
Production authority because the current implementation permits caller-minted
Human confirmations, caller-injected ciphers and coordinates, path-reopened
authority reads, generic mutable replacement, and public-object authority
laundering.

This corrective design replaces those authority assumptions with one Product-
owned operation. The operation binds a trusted Human challenge, a native DPAPI
  source/store snapshot, exact immutable revision/claim CAS, and one private
  two-stage source session. Public projection,
confirmation, history, source-read, binding, result, hash, and receipt objects
remain audit data with `authority_created=false`.

The design changes no source, test, schema, native state, installed data,
Release, Deploy, or Production state. Real promotion and rollback remain
separate Human-gated effects and are not executed by this design Unit.

The earlier R3 artifact at SHA-256
`C432D07F248E88F3C37989A9BEE3A327122C11F3B41D1D0B777EA2E9371FAE45`
received conflicting independent evidence. One review returned TASK-060
`C/H/M/L=0/0/0/0`, while the independent claim/recovery and executable-ledger
reviews found open High/Medium defects. Those verdicts are retained only as
historical review evidence. R4 changes the authority chain, adds the durable
claim-pending recovery phase, fixes resource and directory-durability
contracts, and replaces the ledger. No R3 verdict may be replayed onto R4;
only a review naming the exact frozen R4 SHA covers the current bytes.

## 2. Source-backed gap

Canonical `montage_preference_promotion_store.py` currently:

- exports `confirm_preference_promotion` and `confirm_preference_rollback`;
- accepts caller-selected confirmation IDs, timestamps, and
  `human_confirmed=True`;
- accepts `PreferencePromotionConfirmation.from_dict` plus recomputable hashes;
- accepts a caller-provided `PreferencePromotionCipher` and uses
  `SyntheticCipher` throughout ordinary tests;
- opens the outer document through `Path.read_text` and `json.loads`;
- parses decrypted history through `json.loads`;
- uses generic `exclusive_file_update_lock` and `AtomicJsonWriter` for one
  mutable store path;
- checks logical revision/head but does not bind the opened target bytes and
  physical identity at the publication seam; and
- treats equality of public confirmation/candidate fields as duplicate proof.

Canonical `montage_preference_source.py` currently:

- accepts caller-supplied path, cipher, and
  `PromotedPreferenceSourceCoordinates`;
- verifies some lstat/open/fstat and post-read identity properties but does not
  bind a Product-owned registry/manifest coordinate, native backend identity,
  Windows user/session/key scope, and store currentness into one trusted
  operation;
- decodes through ordinary `json.loads`;
- exports caller-constructible `PromotedPreferenceSourceRead` and
  `coordinates_from_verified_history`; and
- lets downstream code treat an in-process sealed public object as a source
  binding even though module tokens, copying, deserialization, and equal fields
  are not authority boundaries.

Existing tests are regression inputs. They cover projection integrity,
confirmation shape, logical stale CAS, basic encrypted round trip, symlink and
hardlink rejection, a source substitution hook, and synthetic DPAPI smoke.
They do not prove trusted Human presence, secure existing/initial lock
acquisition, strict JSON at every authority layer, opened-byte/inode CAS,
native-backend fixation, user/session/key-scope continuity, directory
durability, foreign-replacement preservation, or single-use source authority.

## 3. Responsibility boundary

TASK-060 owns:

- the Product-facing request/status projection for promotion and rollback;
- the exact action-specific Human challenge subject;
- exact consumption of the canonical candidate/evaluation receipt without
  redefining TASK-029 or TASK-019 semantics;
- the TASK-060 consumer of a trusted Windows Human broker;
- the encrypted promotion-history semantic schema and revision/head rules;
- the private task-specific secure store lock and immutable revision/claim CAS;
- the Production DPAPI backend profile and entropy-domain version;
- the exact promoted-source registry coordinate and pinned source snapshot;
- one private single-use promoted-source capability;
- public audit-only promotion/source projections;
- fault, recovery, replay, collision, and lifecycle classification; and
- versioned fixture contracts for TASK-061-A and TASK-069 consumers.

TASK-060 does not own:

- generic filesystem authority primitives (TASK-068);
- installed bridge pair/instance publication or discovery (TASK-063/TASK-070);
- the Windows Human broker implementation or OS UI (TASK-071);
- Product operation-ticket issuance or child launch (TASK-072);
- File Bridge/Profile publication or canonical learning admission (TASK-069 and
  TASK-067);
- connector activation (TASK-061-A/TASK-061-B);
- the canonical Profile currentness index;
- TASK-029 source semantics or TASK-019 evaluation semantics;
- Timeline, Resolve, media, Provider, native-model, Release, Deploy, or
  Production Activation effects; or
- repair, rewrite, deletion, or adoption of ambiguous/foreign authority files.

## 4. Exact design and future implementation scope

This coherent Platform Trust & Delivery design line may add exactly this file
for TASK-060:

```text
docs/ai-team/tasks/TASK-060/corrective-complete-design-packet.md
```

A future separately authorized TASK-060 implementation Unit may modify exactly:

```text
src/ai_video_production/montage_preference_promotion_store.py
src/ai_video_production/montage_preference_source.py
src/ai_video_production/montage_preference_authority_operation.py
tests/test_montage_preference_promotion_store.py
tests/test_montage_preference_source_integration.py
tests/test_task060_montage_preference_authority_operation.py
docs/ai-team/tasks/TASK-060/corrective-complete-design-packet.md
```

The private operation module/test pair is mandatory as a pair. Every literal
node in section 17.1 is collected from the named private test file, so an
implementation may not inline the private operation into existing modules and
silently move those node IDs. No directory name grants another file.

Existing root and packaged schemas are frozen. Changing either
`montage-preference-projection-promotion.schema.json` mirror requires a separate
exact paired-schema amendment; a one-sided schema edit is forbidden.

Explicitly forbidden without another owner amendment:

- `atomic.py`, TASK-019, TASK-029, TASK-058, TASK-061, TASK-063, TASK-067,
  TASK-068, TASK-069, TASK-070, TASK-071, or TASK-072 source/tests;
- connector, installation, canonical-admission, File Bridge, or SKILL files;
- shared current-state, task-index, roadmap, CHANGELOG, registry, build, release,
  installer, or workflow files;
- installed or Owner data; and
- real promotion, rollback, DPAPI migration, Profile write, native UI, Release,
  Deploy, or Production Activation.

## 5. One-way dependency and direct-handoff graph

```text
TASK-068 IMMUTABLE_SECURE_IO_V1 fixture
TASK-070 INSTALLATION_PAIR_READBACK_V2 fixture
    -> TASK-063 INSTALLATION_READBACK_V2 fixture
    -> TASK-072 INSTALLED_INSTANCE_PROFILE_BINDING_V1 fixture
TASK-069 PROFILE_SOURCE_CONSUMER_CONTRACT_V2 fixture
TASK-071 HUMAN_DECISION_BROKER_V1 fixture
canonical TASK-029 candidate and TASK-019 eligibility fixtures
trusted Product composition/build/clock profile
    -> TASK-060-A versioned fixture adapters and effect-zero status

TASK-068 canonical immutable read/publish and secure lock primitives
TASK-070 private one-use INSTALLATION_PAIR_READBACK_V2
    -> TASK-063 consumes it into canonical INSTALLATION_READBACK_V2
    -> TASK-072 consumes that readback into
       INSTALLED_INSTANCE_PROFILE_BINDING_V1
    -> TASK-060 exact installed instance/Profile/broker binding
TASK-071 canonical trusted Human challenge/decision broker
canonical TASK029_PROFILE_CANDIDATE_V2 plus TASK-019 eligibility readback
Product-owned promotion registry coordinate
    -> TASK-060-B issue PROMOTE or ROLLBACK challenge
    -> TASK-060-C immutable revision/claim transition
    -> TASK-060-D pinned DPAPI promoted-source readback
    -> PROFILE_SOURCE_BINDING_V2 source session

PROFILE_SOURCE_BINDING_V2 source session
    -> authenticated direct move-only handoff to TASK-069 only
TASK-061-A TASK061_PROFILE_CONSUMER_V2 plus consumption port
    -> authenticated direct move-only handoff to TASK-069 only
TASK-069 PROFILE_CONSUMER_BUNDLE_V2
    -> owns the combined Profile operation and narrowed borrows

TASK-060 canonical completion receipt
    -> TASK-061-A source-currentness dependency eligibility
    -> TASK-069 source-session producer eligibility
```

The canonical completion order is exactly:

```text
TASK-068 -> {TASK-069, TASK-063}
TASK-070 PAIR_TERMINAL_V2
    -> TASK-063 INSTALLATION_READBACK_V2
    -> TASK-072 INSTALLED_INSTANCE_PROFILE_BINDING_V1
    -> {TASK-060, TASK-069, TASK-061-A}
SKILL-D2S canonical source -> TASK-069 closed effect-zero identity envelope
TASK-063 + TASK-072 binding -> TASK-060 independent completion receipt
{TASK-069, TASK-060, TASK-063, TASK-072, TASK-071} -> TASK-061-A
```

TASK-060 does not depend on TASK-069 completion to close its own source/store
design. It does depend on the exact frozen candidate interface for compatibility
review, and a live adapter remains `DEPENDENCY_NC_EFFECT0` until the canonical
TASK-069 contract identity arrives. The runtime arrow from TASK-060 to TASK-069
is a direct producer-to-consumer handle transfer, not a Task-completion arrow.
TASK-061 never receives, opens, copies, or forwards the source bytes/session; it
supplies its distinct consumption port directly to TASK-069. Parent/orchestrator
aliases have authority zero. TASK-069 alone atomically reserves the exact source
session, TASK-061 port, consumer bundle, and broker operation before any Profile
effect. A partial handoff, lost response, or process loss burns every entered
handle and becomes `BROKER_RECOVERY_REQUIRED`; no participant reissues or retries.

Fixtures unblock consumer parser, adapter, negative, and effect-zero work only.
Every fixture sets `fixture_only=true`, `real_binding=false`, and
`authority_created=false`. A fixture, copied receipt, public hash, status, or
same-valued object can never be promoted into a live operation.

If TASK-068 remains `IMMUTABLE_ONLY_V1`, TASK-060 uses it for pinned strict
reads and immutable operation/challenge/terminal records. The TASK-060-specific
revision plus deterministic predecessor-claim protocol remains a private bounded
logical CAS owned by TASK-060; TASK-068 does not falsely claim store currentness
authority.

### TASK-069 U1a/U1b/U1c boundary in the coordinated L2 packet

TASK-060 implements none of TASK-069 U1a, U1b, or U1c. It produces only the
private move-only Profile source session and its own independent completion
receipt described here. TASK-069 alone owns its bounds/privacy/projection
contracts, application-composition receipt, baseline compiler, readiness
compiler, and their tests. No TASK-069 model, validator, compiler, or fallback
copy may be added to the TASK-060 Allowed Files.

The coordinated L2 integration consumer treats U1a/U1b outputs as opaque exact
dependency identities. For U1c it performs only this lower-case digest equality:

```text
TASK058_BASELINE_READBACK_V2.application_gate_receipt_sha256
    == APPLICATION_COMPOSITION_V2.receipt_sha256
    == ConnectorReadinessV2.application_composition_sha256
```

Each value must independently satisfy the frozen lower-case SHA grammar. The L2
consumer never reconstructs any of the three receipts and TASK-060 never emits,
normalizes, or substitutes any of these fields. Missing, upper-case, malformed,
or unequal values are `DEPENDENCY_NC_EFFECT0` for TASK-060/061 entry; TASK-069
retains sole ownership of its READY-03 `BLOCKED` reason classification. This
compatibility predicate adds no TASK-069 completion edge back into TASK-060 and
therefore creates no producer cycle.

## 6. Trusted Production composition

Production fixes all authority-bearing dependencies internally:

- native `WindowsDpapiPreferencePromotionCipher` implementation;
- exact cipher implementation/build digest and entropy-domain version;
- trusted Product image/build and packaged operation implementation version;
- trusted Human broker identity and UI/process/session policy;
- trusted UTC plus monotonic/boot/session clock implementation;
- exact TASK-072 `INSTALLED_INSTANCE_PROFILE_BINDING_V1`, created only from the
  TASK-070 private one-use pair readback consumed by TASK-063 into
  `INSTALLATION_READBACK_V2`, plus the selected current owner SID;
- canonical TASK-029 candidate/TASK-019 eligibility readers and exact producer
  contract digests;
- Product-owned promotion registry/manifest coordinate;
- TASK-068 authority instance and receipt verifiers; and
- TASK-060 private store writer and capability registry.

Production accepts none of those from argv, environment, config, serialized
receipt, public object, caller callback, injected hook, monkeypatchable module
global, or dependency-injection parameter. Test composition is a separate
non-Production entry point whose results always carry
`production_eligible=false`.

Production treats extension/caller-accessible Python introspection as an attack
vector. Module-private sentinels, closures, object identity, and hidden class
constructors are never sufficient. The live Human decision, apply invocation,
and source-consumer budget terminate in a trusted Product/broker process and are
represented only by opaque authenticated handles over an inherited or
OS-protected channel. A package/composition that loads arbitrary caller code
inside that trust boundary is `PRODUCTION_INELIGIBLE_EFFECT0`.

## 7. Authority JSON and physical snapshot

Every authority JSON read follows this order:

1. resolve only the Product-owned relative coordinate beneath a pinned root;
2. pin the complete root/ancestor chain and security state;
3. lstat/classify the target without following a link;
4. no-follow open a non-inheritable handle;
5. require regular file, `nlink==1`, and no reparse point;
6. fstat and bind exact physical identity;
7. bounded-read raw bytes from the same handle;
8. recheck handle identity and ancestor currentness;
9. strict UTF-8 decode and bounded JSON parse;
10. validate exact closed semantic schema;
11. compute raw-byte and canonical parsed-document hashes; and
12. retain bytes, hashes, parsed value, physical identity, and security
    commitment in one private sealed snapshot without reopening for proof.

Strict parsing rejects at every nesting level:

- duplicate keys, whether values are equal or different;
- NaN, Infinity, and -Infinity;
- UTF-8 BOM, invalid UTF-8, any decoded control/NUL whether escaped or raw, and
  trailing non-whitespace;
- non-built-in mappings/sequences/scalars and boolean-as-integer coercion;
- excessive raw bytes, nesting depth, object members, array items, nodes, or
  string bytes/code points; and
- unknown fields or versions.

The minimum hard ceilings are fixed by Production and cannot be raised by a
caller: outer document 1 MiB, decrypted document 4 MiB, depth 64, nodes 100,000,
members/items 10,000 per container, and strings 262,144 UTF-8 bytes **and**
262,144 Unicode code points. Smaller schema-specific ceilings remain mandatory.
All ceilings are inclusive. The bounded reader reads at most `byte_cap + 1` and
rejects before decode when the extra byte exists. The root JSON value has depth
1; every object member value or array item increments depth by one. Node count
counts every JSON value exactly once (object, array, string, number, boolean, or
null); object member names are not nodes but are strings and consume both string
ceilings. Object-member and array-item limits are per container. No rejected
`cap + 1` value is canonicalized or hashed. Exact `cap - 1`, `cap`, and `cap + 1`
fixtures for bytes, depth, nodes, members, items, UTF-8 string bytes, and Unicode
code points are mandatory executable nodes in section 17.

Every TASK-060 authority schema also applies this closed field-class table; a
schema may lower but never raise a ceiling:

| Field class | Exact admitted value |
|---|---|
| schema/message/action/state/suite | one listed ASCII enum token, 1..64 bytes |
| SHA-256 commitment | exactly 64 lower-case hexadecimal ASCII characters |
| opaque public ID/reference | 1..128 ASCII bytes, regex `[a-z0-9][a-z0-9._-]{0,127}` |
| build/release/profile reference | 1..128 ASCII bytes, same safe grammar; no path separator or URI colon |
| UTC audit timestamp | exactly `YYYY-MM-DDTHH:MM:SS.ffffffZ`; never authority time |
| revision/version/count/budget | built-in integer, not bool; `0..2^63-1`, with budget exactly `0|1` |
| boolean | built-in JSON `true|false` only; integer/string truthiness rejects |
| optional field | omitted only when its exact versioned schema says optional; `null` never substitutes for omission |
| ciphertext/base64 | canonical RFC 4648 ASCII with required padding, decoded-byte cap enforced before decrypt, no whitespace/alternate alphabet |
| audit object | at most 64 members; no arrays unless its schema names one |
| Profile V2 preferences | `0..1000` closed entries; each closed token/list uses at most 32 items and 128-byte tokens |

Revision, successor-claim, phase, terminal, source-session reservation,
source-session materialization, completion-receipt, encrypted outer, and
decrypted-history bodies use named versioned closed schemas with exact required
fields and unknown-field rejection. Section 10.1 freezes those shapes.

### 10.1 Closed authority schemas

Every listed field below is required and no field is optional. Nested objects or
arrays are admitted only where the row names another closed schema; all leaves
use the scalar classes above. Every unknown or duplicate field rejects. There is
no generic Mapping extension point.

| Closed schema | Exact required fields |
|---|---|
| `TASK060_IMMUTABLE_REVISION_V2` | `schema_version,message_type,operation_commitment_sha256,action,predecessor_raw_sha256_or_genesis,predecessor_canonical_sha256_or_genesis,predecessor_physical_identity_sha256_or_genesis,predecessor_revision,predecessor_head_sha256_or_genesis,revision,encrypted_outer_document,outer_document_sha256,decrypted_history_document_sha256,profile_candidate_sha256,human_decision_terminal_sha256,dpapi_backend_sha256,owner_user_session_sha256,owner_scope_hash,product_build_sha256,record_sha256`; `encrypted_outer_document` is exact `TASK060_ENCRYPTED_PROMOTION_OUTER_V2` |
| `TASK060_SUCCESSOR_CLAIM_V2` | `schema_version,message_type,operation_commitment_sha256,predecessor_head_sha256_or_genesis,revision_record_sha256,revision_record_identity_sha256,successor_head_sha256,claim_sha256` |
| `TASK060_OPERATION_PHASE_V2` | `schema_version,message_type,operation_commitment_sha256,action,ordinal,state,previous_phase_sha256_or_genesis,previous_phase_identity_sha256_or_genesis,revision_record_sha256_or_none,successor_claim_sha256_or_none,source_reservation_sha256_or_none,source_materialization_sha256_or_none,completion_receipt_sha256_or_none,completion_receipt_coordinate_sha256_or_none,completion_receipt_temp_identity_sha256_or_none,completion_receipt_parent_identity_sha256_or_none,completion_receipt_parent_security_sha256_or_none,completion_receipt_absence_lease_sha256_or_none,cumulative_effects,cumulative_effects_sha256,phase_sha256`; `cumulative_effects` is exact `TASK060_CUMULATIVE_EFFECTS_V2` |
| `TASK060_TERMINAL_PHASE_V2` | `schema_version,message_type,operation_commitment_sha256,action,ordinal,previous_phase_sha256,previous_phase_identity_sha256,revision_record_sha256,successor_claim_sha256,source_reservation_sha256,source_materialization_sha256,completion_receipt_sha256,completion_receipt_identity_sha256,completion_receipt_coordinate_sha256,completion_receipt_parent_identity_sha256,completion_receipt_parent_security_sha256,cumulative_effects,cumulative_effects_sha256,state,phase_sha256`; `cumulative_effects` is exact `TASK060_CUMULATIVE_EFFECTS_V2` |
| `SOURCE_SESSION_RESERVATION_V2` | `schema_version,message_type,operation_commitment_sha256,terminal_head_sha256,source_binding_sha256,consumer_contract_sha256,reservation_identity_sha256,state,reservation_sha256` |
| `SOURCE_SESSION_MATERIALIZATION_V2` | `schema_version,message_type,operation_commitment_sha256,reservation_sha256,reservation_identity_sha256,source_session_identity_sha256,source_snapshot_sha256,state,materialization_sha256` |
| `TASK060_PREFERENCE_PROMOTION_COMPLETION_RECEIPT_V2` | the exact field list in section 13.1; no additional field |
| `TASK060_ENCRYPTED_PROMOTION_OUTER_V2` | `schema_version,message_type,cipher_suite,ciphertext_b64,ciphertext_sha256,entropy_domain_version,owner_scope_hash,product_build_sha256,document_sha256`; `ciphertext_b64` is canonical padded RFC 4648 base64 ASCII and decodes within the outer/decrypted byte caps |
| `TASK060_PROMOTION_HISTORY_RECORD_V2` | `schema_version,message_type,revision,action,predecessor_head_sha256_or_genesis,prior_history_record_sha256_or_genesis,profile_candidate,profile_candidate_sha256,human_decision_terminal_sha256,owner_scope_hash,product_build_sha256,record_sha256`; `profile_candidate` is exact closed `TASK029_PROFILE_CANDIDATE_V2` |
| `TASK060_DECRYPTED_PROMOTION_HISTORY_V2` | `schema_version,message_type,revision,predecessor_head_sha256_or_genesis,active_envelope,active_envelope_sha256,records,record_count,records_sha256,owner_scope_hash,product_build_sha256,document_sha256`; `active_envelope` is exact closed `TASK029_PROFILE_CANDIDATE_V2` and `records` is an ordered array of exact `TASK060_PROMOTION_HISTORY_RECORD_V2` objects |
| `TASK060_CUMULATIVE_EFFECTS_V2` | `schema_version,message_type,revision_count,successor_claim_count,profile_count,human_consume_count,source_reservation_count,source_materialization_count,completion_receipt_count,owned_temp_count,owned_orphan_count,phase_record_count,unrelated_overwrite_count,unrelated_delete_count,effects_sha256`; every count is a bounded non-negative built-in integer |

Every `*_sha256_or_none` field admits either the lower-case SHA-256 grammar or
the literal ASCII enum `NONE`; every `*_or_genesis` field admits either that hash
grammar or the literal `GENESIS`. `state` and `action` admit only the exact
state/action enumerations frozen in this packet. The global field-class table
never substitutes for any of these shapes.

### 10.2 Canonical self-hash and nested-body preimages

Every terminal `record_sha256`, `claim_sha256`, `phase_sha256`,
`reservation_sha256`, `materialization_sha256`, `receipt_sha256`,
`document_sha256`, `effects_sha256`, and nested history `record_sha256` uses one
nonrecursive rule. Its preimage is:

```text
ASCII("BVP:TASK060:" + CLOSED_SCHEMA_NAME + ":" + schema_version + "\0")
|| UTF8(canonical_json(object with only that terminal self-hash field omitted))
```

The self-hash field is absent, not empty, zeroed, or `null`, in the preimage;
every other required field and nested body remains present. The final canonical
document then adds the resulting 64-lowercase-hex digest as that field. A hash
computed with another omission, key order, normalization, domain, version, or
serialization rejects. `ciphertext_sha256`, `records_sha256`,
`active_envelope_sha256`, `outer_document_sha256`,
`decrypted_history_document_sha256`, and `profile_candidate_sha256` hash the
exact bounded bytes/body named by the field and are not self-hashes.

`cumulative_effects_sha256` must equal the `effects_sha256` of the exact nested
`TASK060_CUMULATIVE_EFFECTS_V2` object. That nested object contains all twelve
signed-ledger coordinates as non-negative cumulative counts, so a phase never
persists an unverifiable digest without its body. The immutable revision embeds
the complete encrypted outer document, and decrypting that exact ciphertext
produces the complete bounded active envelope and ordered history-record bodies;
hash-only summaries cannot substitute for either body or authorize rollback/
Profile projection.

The encrypted outer document contains no free-form user strings. Decrypted
Profile V2 content must match the exact closed TASK-069 vocabulary and privacy
projection; legacy V1/free-string payloads remain audit-only and cannot enter a
live source session.

No unbounded or rejected tree is canonicalized, hashed, logged, persisted, or
passed to semantic code. Parser/resource errors map to stable body-free codes.
Ambiguous current/predecessor files are preserved; repair, rewrite, rollback,
delete, or equality-based adoption is zero.

The private snapshot type is:

```text
TASK060_AUTHORITY_JSON_SNAPSHOT_V1(
  coordinate_commitment,
  raw_bytes_sha256,
  canonical_document_sha256,
  byte_count,
  physical_identity_commitment,
  security_commitment,
  root_ancestor_commitment,
  opened_document,
  captured_at_clock_coordinate
)
```

Its public projection omits coordinate, identity, opened document, raw bytes,
security material, SID, session, and OS detail.

PROMOTE additionally requires one private candidate snapshot created by the
trusted Product reader from the canonical TASK-029 candidate and TASK-019
eligibility receipt. It binds their raw/canonical hashes, physical identities,
producer contract/build digests, project/owner scope, eligibility decision, and
currentness coordinate. A public candidate mapping, self-hash, caller path, or
same-valued reconstructed object is audit-only. ROLLBACK instead binds the exact
target revision from the same opened promotion-history snapshot; it cannot use
a caller-supplied historical body.

## 8. Human challenge and one-shot decision

`confirm_preference_promotion`, `confirm_preference_rollback`,
`PreferencePromotionConfirmation`, `from_dict`, confirmation hashes, caller
booleans, IDs, and timestamps become audit/test data only. They create no
Production authority.

Production issues one action-specific challenge:

```text
TASK060_HUMAN_CHALLENGE_V1(
  challenge_handle,
  random_nonce_commitment,
  action=PROMOTE|ROLLBACK,
  install_instance_commitment,
  owner_sid_commitment,
  project_scope_commitment,
  candidate_sha256_or_absent,
  candidate_snapshot_commitment_or_absent,
  eligibility_receipt_commitment_or_absent,
  expected_store_revision,
  expected_store_head_sha256_or_genesis,
  rollback_target_revision_or_absent,
  rollback_target_sha256_or_absent,
  expected_active_payload_sha256,
  registry_coordinate_commitment,
  issued_clock_coordinate,
  expiry_policy,
  product_build_digest,
  broker_implementation_digest,
  invocation_budget=1
)
```

The Product generates at least 256 random bits. The caller selects none of the
nonce, challenge ID, action, issue time, expiry, session, user, or operation ID.
PROMOTE and ROLLBACK challenges are distinct actions and cannot cross-redeem.
The action subject is a closed tagged union: PROMOTE requires exactly one
trusted candidate/eligibility snapshot and no rollback target; ROLLBACK requires
no candidate/eligibility snapshot and exactly one existing historical target.
Initial-store creation is PROMOTE-only. Both, neither, zero, unknown action, or
a rollback target outside the pinned history fails before challenge issuance.

Only the trusted Human-visible Product/broker UI can return
`TASK060_HUMAN_DECISION_HANDLE_V1`. It binds the exact challenge, UI process,
Windows logon session, current user SID, Product operation, visible event,
trusted clock coordinate, and exact accepted body. Raw confirmation strings,
copying, direct construction, mapping conversion, pickle, deserialization,
module-global tokens, subclassing, and valid hash recomputation cannot create
the handle.

Challenge lifecycle:

```text
ABSENT -> ISSUED -> IN_FLIGHT -> COMMITTED
                          |----> REJECTED_BURNED
                          |----> BURNED_UNKNOWN
```

At the first trusted apply entry the invocation budget is consumed and state is
durably `IN_FLIGHT`. Success, rejection, exception, crash, timeout, and unknown
terminal state all burn the capability. A fresh operation is required after a
failed or ambiguous attempt. Authenticated reconciliation of the same committed
event may return the same read-only `DUPLICATE` projection repeatedly, including
third and concurrent queries, only after exact terminal identity/body readback.
Every query has state-transition/effect/budget delta zero. Different body or
identity under the same challenge is always `COLLISION_STOP`.

## 9. Trusted clock, user, session, and backend

Production has no caller-supplied `now`, clock, SID, session, cipher, entropy,
backend, hook, or failure injector.

Challenge issue, Human event, apply entry, durable consume, DPAPI decrypt,
store publication, source readback, and terminal receipt use one trusted time
domain. Expiry cannot be extended by wall-clock rollback, forward jump,
timezone change, suspend/resume, process restart, or boot/session change. The
operation uses a persisted monotonic/boot/session coordinate with bounded UTC
for audit display. An unavailable or discontinuous trusted clock fails closed.

The selected TASK-063 install owner/current user SID, Windows logon session,
DPAPI Current User scope, Product process identity, and backend implementation
must remain identical from prepare through final readback. Drift burns the
operation with effect zero if pre-effect, otherwise `COMPLETION_UNKNOWN` and no
retry.

## 10. Native DPAPI document

Production internally constructs exactly
`WindowsDpapiPreferencePromotionCipher`. `PreferencePromotionCipher`,
`SyntheticCipher`, custom Protocol implementations, same-suite fake ciphers,
monkeypatched decryptors, and caller-selected cipher suite are test-only.

The Product registry resolves the encrypted source; callers cannot supply its
path or `coordinates_from_verified_history` output as authority. The outer
document and decrypted plaintext are parsed with section 7's strict parser.

The private decrypt snapshot binds:

```text
TASK060_DPAPI_SOURCE_SNAPSHOT_V1(
  outer_raw_sha256,
  outer_canonical_sha256,
  outer_physical_identity_commitment,
  ciphertext_sha256,
  decrypted_canonical_sha256,
  parsed_history_head_sha256,
  parsed_history_revision,
  active_envelope_sha256,
  cipher_suite,
  cipher_implementation_digest,
  entropy_domain_version,
  current_user_sid_commitment,
  logon_session_commitment,
  product_build_digest,
  registry_coordinate_commitment
)
```

Plaintext is never written to disk, public receipt, error, log, stdout, temp,
challenge, or journal. DPAPI/native failure exposes only a stable code.

## 11. Secure promotion store transition

The store operation holds a dedicated TASK-060 operation lock beneath the
pinned Product root. Lock acquisition has disjoint initial and existing modes.
The lock is a persistent authority object; success, failure, recovery, and
uninstall do not delete or recreate it as cleanup.

Initial mode:

- pins the admitted root/ancestors/security;
- creates the one-byte lock with CREATE_NEW/no-follow through a live handle;
- requires regular, `nlink==1`, no reparse, non-inheritable handle;
- performs lock and final identity/security checks on that same physical
  handle; and
- on collision burns the attempt, performs one fresh classification, and never
  silently retries as existing mode.

Existing mode:

- pins root/ancestors and opens the existing regular one-link lock no-follow;
- binds its opened identity/security before locking;
- locks the same handle; and
- rechecks the same physical object and security before each authority step and
  release.

TASK-060 V2 never replaces a current authority file. It is an immutable linear
revision chain with one deterministic no-replace successor claim per predecessor:

```text
revisions/rev-<revision>-<document-sha256>.json
claims/<predecessor-head-sha256-or-GENESIS>.json
```

The revision record contains the encrypted canonical document and binds the
exact opened predecessor raw/canonical bytes, physical identity, revision/head,
owner scope, challenge/decision, backend/user/session/build, and operation. The
claim contains only the predecessor commitment, revision-record bytes/identity,
new revision/head, and operation commitment. Currentness is resolved from the
pinned immutable genesis anchor by following exactly one deterministic claim per
head with exact `MAX_PROMOTION_REVISION_CHAIN_LENGTH=4096`; directory
enumeration, highest/latest selection, and mutable pointer files are forbidden.
The cap is inclusive: a valid chain of length 4095 may admit one successor whose
resulting length is exactly 4096; a valid chain already at 4096 rejects every
successor before revision publication; an observed chain of 4097 or greater is
invalid authority and is preserved without repair. Rejection is private
`RESOURCE_LIMIT_REJECTED` projected publicly as `REJECTED_EFFECT0`, with
claim/revision/Profile effects zero. Chain rollover, compaction, or a new
genesis is a separate lifecycle/Human Gate.

Genesis and existing transitions use the same logical CAS:

1. retain the admitted predecessor handle snapshot, or the exact genesis
   absence plus a live pinned-parent negative-lookup lease;
2. validate Human/backend/source/currentness while the TASK-060 lock is held;
3. create, write and file-flush one operation-owned exclusive revision temp;
4. revalidate the predecessor handle bytes/identity or genesis lease, ancestors,
   lock, challenge/decision, backend/clock, and expected revision/head;
5. publish the immutable revision no-replace, make the parent durable, and reopen
   exact bytes/identity;
6. create and flush the deterministic predecessor claim temp, repeat the same
   currentness validation, then durably append `CLAIM_PUBLISH_PENDING` with the
   exact claim bytes/hash, temp identity, target negative-lookup lease,
   predecessor and referenced revision;
7. publish the journal-bound claim no-replace, make the parent durable, and
   pinned-read the exact claim plus referenced revision; and
8. resolve the chain from genesis and require the new revision/head to be the
   sole successor before terminal commit.

The claim publication is the linearization point. If another operation already
claimed the predecessor, equal bytes are `DUPLICATE` only when the same trusted
operation terminal binds the same revision and both physical identities;
otherwise it is `COLLISION_STOP`. An unclaimed revision is an inert preserved
orphan and never current. No foreign or older object is overwritten or deleted,
so a same-user writer cannot win an unchecked pathname-replace race. Existing
legacy mutable documents are pinned migration inputs only; this Unit never
rewrites them and a separately authorized migration must create the V2 genesis.

Generic `AtomicJsonWriter` and `exclusive_file_update_lock` are not authority
proof. The future private TASK-060 operation module owns this bounded writer if
the existing owner modules cannot hold it without obscuring the contract.

The operation journal is an append-only immutable phase chain, not another
mutable JSON target. Its closed order is:

```text
0 PREPARED
1 DECISION_CONSUMED
2 REVISION_PUBLISHED
3 CLAIM_PUBLISH_PENDING
4 SUCCESSOR_CLAIM_PUBLISHED
5 HEAD_READBACK_VERIFIED
6 SOURCE_SESSION_RESERVED
7 SOURCE_SESSION_MATERIALIZED
8 COMPLETION_RECEIPT_PENDING
9 TERMINAL_COMMITTED
```

`PREPARED` is no-replace and binds operation, action, challenge, predecessor
snapshot/genesis lease, candidate/rollback target, expected result digest,
backend/user/session/build, and lock identity. `DECISION_CONSUMED` is durable
before the first revision namespace effect. Every later phase is a new
no-replace record that binds the exact previous phase canonical bytes, physical
identity, self-hash, ordinal, relevant revision/claim identities, and cumulative
effect counts. Publication uses an operation-owned live temp, file flush,
prepublication identity/security validation, no-replace namespace commit,
directory durability, and pinned exact readback.

Initial lock creation itself is file-flushed, parent-durable, reopened and
identity/security verified before it may protect an operation; response loss or
failure at any of those seams permits only fresh classification of the persistent
lock and never deletion/recreation. A missing phase, duplicate/fork/gap, swapped
predecessor, or non-monotonic ordinal is STOP+preserve. No phase is rewritten or
inferred from revision/claim bytes alone.

## 12. Recovery and cleanup

The durable operation journal binds challenge, exact predecessor snapshot,
candidate/rollback target, new document digest, temp identity, publication
state, and terminal readback.

Recovery classifications are total and phase-derived:

- absent journal: `NOT_STARTED`, namespace effect zero; challenge is explicitly
  cancelled/burned;
- `PREPARED|DECISION_CONSUMED`: head/claim effect zero; an owned uncommitted temp
  or revision orphan is preserved or cleaned only by exact handle/identity;
- `REVISION_PUBLISHED`: no claim-pending record exists, so the revision is an
  inert preserved orphan, head delta zero, and claim publish/retry is forbidden
  after process/session loss;
- `CLAIM_PUBLISH_PENDING`: only broker-owned
  `recover_transition(operation_binding, predecessor_binding)` may take the
  durable recovery-winner slot, pin the same parent and predecessor, and inspect
  the deterministic claim coordinate. Proven absence permits exactly one
  no-replace publish of the journal-bound claim bytes; exact presence permits
  readback classification; different presence is `COLLISION_STOP`; ambiguous
  lookup/publication is `BURNED_UNKNOWN`. No caller retry or second publish is
  permitted;
- `SUCCESSOR_CLAIM_PUBLISHED`: logical head may have advanced; all writes stop and
  only broker-owned `recover_transition(operation_binding, predecessor_binding)`
  may pinned-read the same claim/revision and classify it;
- `HEAD_READBACK_VERIFIED`: head delta is exactly one. The broker recovery
  winner may advance only the already-bound source-session step for the same
  operation. Proven reservation absence permits exactly one no-replace
  `SOURCE_SESSION_RESERVATION_V2` and phase 6; exact presence permits pinned
  readback; different presence is `COLLISION_STOP`; ambiguous lookup/publication
  is `COMPLETION_UNKNOWN`. No live handle is returned in this phase;
- `SOURCE_SESSION_RESERVED`: only the authenticated recovery winner may create
  the exact broker-owned session and publish one no-replace
  `SOURCE_SESSION_MATERIALIZATION_V2` plus phase 7. A crash before publication
  leaves `RESERVED`; proven absence permits that one materialization. Exact
  presence returns the same opaque session identity. Different body or physical
  identity is `COLLISION_STOP`; only an ambiguous lookup is
  `COMPLETION_UNKNOWN`; replacement-session minting is zero;
- `SOURCE_SESSION_MATERIALIZED`: the source session is recoverable only as that
  same opaque broker session and is non-reissuable. The recovery winner computes
  the completion receipt once from the still-pinned chain/session snapshots and
  publishes phase 8 `COMPLETION_RECEIPT_PENDING`, which binds the receipt's exact
  canonical bytes, deterministic contained coordinate, operation-owned temp
  physical identity, pinned parent physical identity/security commitment, and
  live negative-lookup lease. No receipt namespace effect is allowed before
  phase 8 is durable;
- `COMPLETION_RECEIPT_PENDING`: proven target absence permits exactly one
  no-replace publication of the phase-bound receipt. Immediately before that
  publication, recovery must revalidate the same coordinate, owned temp
  identity, parent identity/security, and still-current absence lease frozen in
  phase 8. Exact target bytes and physical identity permit readback; different
  presence is `COLLISION_STOP`;
  ambiguous lookup/publication/durability/readback is `COMPLETION_UNKNOWN`.
  After exact receipt durability and pinned readback, the winner appends phase 9
  `TERMINAL_COMMITTED` once. Caller retry and every revision/head/source effect
  remain zero;
- `TERMINAL_COMMITTED`: this phase already binds the exact durable completion
  receipt identity. Authenticated reconciliation is strictly read-only and may
  return the identical terminal any number of times with every delta zero;
- `BURNED_UNKNOWN`: preserve all evidence, head effect is unknown, issue/apply/
  claim/source-session retry zero; and
- `COLLISION_STOP`: preserve current and foreign state; no effect beyond a
  separately proven immutable revision orphan.

`recover_transition` is a trusted owner-only broker ABI, not a fresh Human
challenge or caller retry. It derives the original operation key, authenticates
the frozen phase chain plus the source-session reservation/materialization
record, and has one durable recovery-winner slot. Repeated calls
after that slot resolves are read-only. It never changes action, predecessor,
candidate, revision/head, backend/user/session/build, or budget.

Temp cleanup deletes only the exact name/handle/identity created by this
operation. A foreign replacement, hardlink, reparse point, unknown identity, or
ambiguous close/delete outcome is preserved and reported as cleanup unknown.
No deterministic foreign temp is unlinked.

Rollback never reparses and republishes an ambiguous predecessor. A rollback is
a new immutable revision and predecessor claim that points to the exact pinned
historical payload; it never restores/replaces/deletes a pathname. Unknown
publication/readback, foreign state, or ambiguous history produces STOP+preserve
and no new claim.

No operation automatically deletes old promotion data. Retention/uninstall/GC
is a separate lifecycle/Human Gate.

## 13. Promoted source and private capability

`PromotedPreferenceSourceCoordinates`, `PromotedPreferenceSourceRead`,
`coordinates_from_verified_history`, public bindings, self-hashes, and receipt
documents are audit evidence only. They expose `authority_created=false` and
cannot enter a Production Profile write.

The trusted Product operation reads the promoted source using the same pinned
outer/decrypted snapshot and exact current immutable revision/head. A live
source is eligible only when promotion stored an exact canonical
`TASK029_PROFILE_CANDIDATE_V2` whose payload already matches the closed TASK-069
Profile V2 envelope. Current legacy V1 envelopes are historical audit inputs;
TASK-060 does not translate/adapt them and cannot create a live Profile source
until that upstream V2 producer dependency is canonical.

The only Production source authority is the exact two-stage nonserializable
`PROFILE_SOURCE_BINDING_V2` session. Its body-free audit projection fields are:

```text
schema_version, message_type, source_binding_sha256, source_session_sha256,
source_preflight_seed_sha256, source_identity_commitment_sha256,
profile_projection_contract_sha256, profile_payload_contract_sha256,
profile_ref, profile_version, owner_scope_hash, source_record_count,
source_profile_sha256, opaque_reference_set_sha256,
system_vocabulary_sha256, application_composition_sha256,
preflight_binding_sha256, installation_pair_terminal_sha256,
installed_instance_id, release_id, build_id, state, single_use,
fixture_only, authority_created, receipt_sha256
```

Constants are `schema_version=2.0.0`, the frozen TASK-069 message type,
`single_use=true`, `fixture_only=false`, and `authority_created=false`. Fields
bind the immutable chain revision/head, exact source physical/security snapshot,
owner/session/DPAPI/build, registry coordinate, and frozen Profile V2 bytes even
where the public audit projection exposes only commitments.

The live state machine and method ABI are exact:

```text
PINNED
  -- prepare_preflight(authenticated_request_binding) --> SEED_MOVED
  -- bind_preflight(exact_returned_preflight) ----------> PREFLIGHT_BOUND
  -- project() -----------------------------------------> PROJECTED
  -- any response loss/process loss/unknown entry ------> BURNED_UNKNOWN
```

`prepare_preflight` moves the pinned bytes/identity into one nonserializable
`ProfileSourcePreflightSeedV2`; TASK-072 consumes that seed in the single Profile
preflight transaction. `bind_preflight` accepts only the returned preflight with
the same seed/source/opaque-reference/vocabulary/install/build commitments and
never rereads a path. `project` consumes the already-frozen bytes exactly once.
Second/mixed seed, bind or project, copy, serialization, public bytes, legacy V1,
same fields on another physical source, self-hash, or audit projection cannot
mint or advance the session.

Before durable budget entry, the trusted endpoint matches method, authenticated
request, exact consumer contract digest, operation vector, install/build/source,
and expected state. A mismatch returns effect zero with the victim session budget
unchanged. After entry, return, rejection, exception, cancellation, timeout,
response loss, channel close, or process crash permanently burns the entered
session/seed. Owner recovery may only return the identical sealed projection or
`BROKER_RECOVERY_REQUIRED`; it never produces a new live source or repeats a
method.

The broker transfers this session directly to TASK-069. TASK-061 receives only
the source audit/currentness commitment and supplies its own distinct
`Task061ProfileConsumptionPortV2` directly to the same TASK-069 operation.
TASK-069 reserves all handles before Profile allocation/effect. Parent aliases,
later hashes, mappings, paths, and forwarded envelopes have authority zero.

### 13.1 Canonical TASK-060 completion/current-source receipt

TASK-060 produces exactly one immutable, no-replace, directory-durable
`TASK060_PREFERENCE_PROMOTION_COMPLETION_RECEIPT_V2` during
`COMPLETION_RECEIPT_PENDING`, after pinned exact source-session
reservation/materialization readback and before `TERMINAL_COMMITTED`. Phase 8
binds the receipt's exact canonical bytes, deterministic contained coordinate,
and required absence lease; recovery can therefore publish or classify only
that one receipt and never reconstruct it from public fields. Phase 9 can be
published only after exact receipt durability and pinned readback. Its closed
fields are:

```text
schema_version, message_type, operation_commitment_sha256,
action, task070_installation_pair_readback_v2_sha256,
task063_installation_readback_v2_sha256,
task072_installed_instance_profile_binding_v1_sha256,
human_decision_terminal_sha256, immutable_revision_sha256,
successor_claim_sha256, revision, head_sha256,
source_raw_bytes_sha256, source_canonical_sha256,
source_physical_identity_sha256, source_security_commitment_sha256,
source_session_reservation_sha256, source_session_identity_sha256,
profile_source_binding_v2_sha256, dpapi_backend_sha256,
owner_user_session_sha256, product_build_sha256,
source_session_materialized_phase_sha256, state, fixture_only,
authority_created, receipt_sha256
```

Constants are `schema_version=2.0.0`, message type
`BvpPreferencePromotionCompletionReceipt`,
`state=PROMOTED_SOURCE_CURRENT_READBACK_VERIFIED`, `fixture_only=false`, and
`authority_created=false`. The record is a public dependency/audit projection;
its bytes never recreate the private source session. Two distinct trusted
reader ABIs pin its strict bytes/physical identity/security under the same
secure operation root. The receipt binds phase 7
`SOURCE_SESSION_MATERIALIZED`; phase 8 binds the receipt hash, and phase 9 binds
the published receipt identity. This one-way chain avoids a receipt/phase
self-reference and prevents a terminal phase from being named before it exists.
The trusted readers verify phase 9, immutable revision/claim chain,
current TASK-070 -> TASK-063 -> TASK-072 instance binding, DPAPI/user/session/
build, and exact durable source-session identity in one private readback:

```text
read_completion_currentness_for_task061a(
  admitted_task061a_operation_binding,
) -> Task060CompletionCurrentnessPortV2

read_completion_currentness_for_task061b(
  admitted_task061b_operation_binding,
) -> Task060CompletionCurrentnessPortV2

take_profile_source_session_for_task069(
  admitted_task069_operation_binding,
) -> (Task060CompletionCurrentnessPortV2, ProfileSourceBindingSessionV2)
```

The first two ABIs are receipt/currentness-only: neither returns source bytes,
seed, handle, or live source session. They have distinct A-consumer and
B-consumer slots; A cannot forward its port to B, and B must freshly invoke the
B-specific reader with its exact admitted final-verification operation. The
third ABI alone transfers the still-live
move-only session to TASK-069. Each private reader/transfer slot and each
returned port is method/consumer/operation bound and one-use. The trusted broker
persists `UNENTERED -> IN_FLIGHT` before entering either ABI; exact completion
resolves that slot to `SPENT`, while exception, timeout, process loss, or
response loss resolves it to `BURNED_UNKNOWN`. A concurrent loser, second call,
wrong method/operation, copied or serialized object, and cross-consumer forward
return no port and do not enter the victim slot. A burned slot can be reconciled
only by the same broker from its durable phase/receipt chain and can never mint
a replacement port or replay a transfer. Neither ABI nor returned port can be
serialized, copied, reconstructed from the public receipt, or forwarded to the
other consumer. TASK-061-A cannot invoke or receive the TASK-069 ABI.

Missing, stale, changed, copied, rehashed, same bytes on another inode,
cross-instance/build/session, terminal mismatch, or source-session identity
mismatch is `DEPENDENCY_NC_EFFECT0`. Same receipt key plus exact body and exact
physical identity may be read-only `DUPLICATE`; a different body or identity is
`COLLISION_STOP`. The receipt/currentness identity is the shared dependency
fact, while the two private ABIs above preserve distinct authority. Section 21's
design-review receipt is never that Product dependency.

## 14. Public request/status/result boundary

Public APIs support request, prepare-status, terminal-status, and audit display.
They never expose a live challenge, decision handle, source capability, raw
path, SID, session, registry coordinate, physical identity, ciphertext,
plaintext, envelope body, OS error, or stack/cause/context.

Stable public outcomes:

```text
REQUEST_ACCEPTED_EFFECT0
HUMAN_DECISION_REQUIRED_EFFECT0
DEPENDENCY_NC_EFFECT0
STALE_EFFECT0
REJECTED_EFFECT0
COLLISION_STOP
COMMITTED
DUPLICATE_COMMITTED_EVENT
COMPLETION_UNKNOWN
```

Ledger and recovery classifiers are private implementation states. Their exact
public projection is frozen as follows; an implementation may not expose a
private name or invent another public status:

| Private classifier | Public outcome |
|---|---|
| `STRICT_JSON_REJECTED` | `REJECTED_EFFECT0` |
| `RESOURCE_LIMIT_REJECTED` | `REJECTED_EFFECT0` |
| `BURNED_UNKNOWN` | `COMPLETION_UNKNOWN` |
| `BROKER_RECOVERY_REQUIRED` | `COMPLETION_UNKNOWN` |
| `CLEANUP_UNKNOWN` | `COMPLETION_UNKNOWN` |
| `DIRECTORY_DURABILITY_NOT_CONFIRMED` before namespace effect | `DEPENDENCY_NC_EFFECT0` |
| `DIRECTORY_DURABILITY_UNKNOWN` after namespace effect | `COMPLETION_UNKNOWN` |
| `PROJECTED` | `COMMITTED` |
| `CURRENT_SOURCE_VERIFIED` | `COMMITTED` |
| `REJECTED_EFFECT0`, `DEPENDENCY_NC_EFFECT0`, `COLLISION_STOP`, `COMMITTED`, `DUPLICATE_COMMITTED_EVENT`, `COMPLETION_UNKNOWN` | identical public outcome |

Only the right-hand value appears in public result/status/error output. Private
classification and native details remain in bounded owner evidence.

All error and status records contain only schema/version, opaque operation
commitment, action, stable code, constant authority/effect flags, and bounded
opaque hashes. Public exceptions are detached from private causes and contexts.

## 15. Versioned fixtures

TASK-060 publishes these fixture shapes before real dependency binding:

### `TASK060_HUMAN_DECISION_FIXTURE_V1`

Closed public-safe fields:

```text
version, fixture_id, action, subject_sha256, expected_revision,
expected_head_sha256_or_genesis, terminal_status, fixture_only,
real_binding, authority_created
```

### `TASK060_PROMOTED_SOURCE_AUDIT_FIXTURE_V1`

Closed public-safe fields:

```text
version, fixture_id, install_instance_sha256, owner_scope_sha256,
store_revision, store_head_sha256, active_envelope_sha256,
profile_id, profile_revision, production_backend_required,
fixture_only, real_binding, authority_created
```

This is the TASK-061-A source-audit/parser fixture. It is not a TASK-069 port.

### `TASK060_TO_TASK069_PROFILE_SOURCE_PORT_FIXTURE_V2`

The authority-false fixture mirrors the exact candidate TASK-069
`PROFILE_SOURCE_BINDING_V2` audit projection:

```text
schema_version, message_type, source_binding_sha256, source_session_sha256,
source_preflight_seed_sha256, source_identity_commitment_sha256,
profile_projection_contract_sha256, profile_payload_contract_sha256,
profile_ref, profile_version, owner_scope_hash, source_record_count,
source_profile_sha256, opaque_reference_set_sha256,
system_vocabulary_sha256, application_composition_sha256,
preflight_binding_sha256, installation_pair_terminal_sha256,
installed_instance_id, release_id, build_id, state, single_use,
fixture_only, authority_created, receipt_sha256
```

Constants are `schema_version=2.0.0`, the frozen TASK-069 message type,
`state=PINNED|SEED_MOVED|PREFLIGHT_BOUND|PROJECTED|BURNED_UNKNOWN`,
`single_use=true`, `fixture_only=true`, and `authority_created=false`.
Fixture state changes model parser/test transitions only and never represent a
live seed/session. Before runtime eligibility, this list, methods, transitions,
constants, and contract digest must be byte-for-byte rebound to canonical
TASK-069. Drift keeps the fixture only as a rejected test vector.

All three fixtures require exact built-in JSON types, closed fields, strict
bounds, and
constant `fixture_only=true`, `real_binding=false`,
`authority_created=false` where `real_binding` is a field. Their IDs and hashes
are advisory and cannot be redeemed.

The live port is not JSON and has no public constructor or `from_dict`.

## 16. Future source/test traceability

The future implementation keeps current public APIs only as audit/test
compatibility surfaces and adds no second Product store. Exact ownership is:

| Matrix | Owner symbols | Required focused test in the allowed test set |
|---|---|---|
| P60-H | `confirm_preference_promotion`, `confirm_preference_rollback`, `PreferencePromotionConfirmation`; private request/prepare/apply operation | `test_task060_public_confirmation_objects_never_authorize`; `test_task060_human_challenge_is_action_specific_single_use_and_burned` |
| P60-S | `PreferencePromotionStore.load/promote/rollback`, `_current`, `_duplicate`, `_write`; private lock, immutable revision/claim chain, phase chain and recovery owner | `test_task060_store_secure_lock_cas_and_fault_matrix`; `test_task060_immutable_revision_claim_phase_and_recovery_matrix`; `test_task060_recovery_preserves_foreign_and_ambiguous_state` |
| P60-C | `WindowsDpapiPreferencePromotionCipher`, `PreferencePromotionStore.__init__`, `PromotedPreferenceSource.__init__`; private Production composition | `test_task060_production_dpapi_backend_and_user_session_are_fixed` |
| P60-J | `_parse_envelope`, `_verify_envelope`, `_verify_candidate_payload`, `_verify_history`, `PreferencePromotionStore.parse_encrypted_document`, `PromotedPreferenceSource.read_current` | `test_task060_strict_outer_and_decrypted_json_matrix`; `test_task060_public_failures_are_body_free` |
| P60-P | `PromotedPreferenceSourceRead`, `PromotedPreferenceSource.read_current`, `_open_pinned`, `verify_current`, `coordinates_from_verified_history`; private `PROFILE_SOURCE_BINDING_V2.prepare_preflight/bind_preflight/project/recover` | `test_task060_profile_source_v2_two_stage_session_and_direct_handoff`; `test_task060_promoted_source_capability_is_private_single_use` |
| P60-R | private `TASK060_PREFERENCE_PROMOTION_COMPLETION_RECEIPT_V2` producer, receipt-only TASK-061-A reader and disjoint TASK-069 source-session transfer ABI | `test_task060_completion_current_source_receipt_is_exact`; `test_task060_completion_consumer_abis_are_disjoint` |

The first listed current symbols remain in their existing owner modules. Every
private operation symbol and every new exact node in section 17 lives in the
mandatory paired authority module/test from section 4. All named new tests are
created in `tests/test_task060_montage_preference_authority_operation.py`;
integration into either existing test file is not an alternative because it
would change the frozen node IDs. Historical test names remain unchanged and
their expectations are never weakened. The implementation receipt maps every
P60 ID below to an exact test node ID and one frozen source/test hash set.

## 17. Negative and fault matrix

Every row separately asserts store revision/head delta, Profile/source delta,
challenge consumption, temp/journal delta, and unrelated-file delta.

### P60-H — Human authority

- `P60-H01`: caller `human_confirmed=True` creates authority zero;
- `P60-H02`: predictable confirmation string creates authority zero;
- `P60-H03`: direct/copy/replace/pickle/deserialized confirmation rejected;
- `P60-H04`: `from_dict` plus recomputed hash rejected;
- `P60-H05`: caller-selected new ID or timestamp replay rejected;
- `P60-H06`: PROMOTE challenge used for ROLLBACK and reverse rejected;
- `P60-H07`: wrong candidate, target, revision, head, owner, project, install,
  user, session, process, broker, or build rejected;
- `P60-H08`: challenge file stat-open/read-post swap, hardlink, reparse, or
  ancestor/security drift rejected;
- `P60-H09`: expired challenge, rollback/forward clock jump, suspend, restart,
  or phase clock swap rejected;
- `P60-H10`: double, concurrent, exception-after-entry, and crash reuse rejected;
- `P60-H11`: same committed event returns one duplicate; different body/identity
  under the same challenge is collision STOP; and
- `P60-H12`: Production test-clock/backend/hook injection rejected; and
- `P60-H13`: public/reconstructed TASK-029 candidate, copied/self-hashed
  TASK-019 eligibility, wrong producer/build/project/currentness, or candidate
  stat-open/read-post/identity swap creates authority zero.

### P60-S — Store currentness and publication

- `P60-S01`: initial/existing lock race and late initial collision;
- `P60-S02`: lock symlink/reparse/hardlink/nlink/security/ancestor drift;
- `P60-S03`: absent initial store appears identical or different before publish;
- `P60-S04`: store stat-open, open-read, read-post, and same-bytes/different-inode
  swaps;
- `P60-S05`: concurrent promote/rollback with expected revision/head mismatch;
- `P60-S06`: predecessor/genesis lease drift immediately before successor-claim
  publication;
- `P60-S07`: revision/claim identity swap immediately after no-replace
  publication and before readback;
- `P60-S08`: temp close/path replacement, hardlink, or foreign temp collision;
- `P60-S09`: file flush, temp identity, native publish, directory durability,
  reopen, exact readback, close, or final security failure;
- `P60-S10`: ambiguous one-sided journal/current/predecessor state preserves all
  data and performs repair/delete zero;
- `P60-S11`: rollback sees foreign current target and performs restore/delete
  zero; and
- `P60-S12`: operation-owned cleanup identity becomes unknown and foreign file
  remains preserved; and
- `P60-S13`: PREPARED collision, phase predecessor bytes/inode/self-hash swap,
  duplicate/fork/gap/non-monotonic phase, or phase durability/readback failure
  stops with store retry/repair/delete zero;
- `P60-S14`: genesis PROMOTE, existing PROMOTE, and ROLLBACK each produce the
  exact ten-phase terminal vector once;
- `P60-S15`: claim-pending and completion-receipt-pending recovery have one
  authenticated winner and exact absent/present/different/ambiguous branches;
- `P60-S18`: initial-lock, challenge, and owned-temp create/flush/durability/
  readback/close seams are separate literal nodes;
- `P60-S19`: source reservation and materialization each have separate
  create/namespace/durability/readback/collision/ambiguity/repeat nodes; and
- `P60-S20`: completion receipt publication and phase-9 terminalization have
  separate absent/namespace/durability/readback/present/collision/repeat nodes.

### P60-C — cipher/backend/user boundary

- `P60-C01`: `SyntheticCipher`, custom Protocol, fake same-suite cipher, or
  monkeypatched decryptor in Production creates effect zero;
- `P60-C02`: caller cipher suite, entropy, path, coordinates, history, SID,
  session, or registry coordinate rejected;
- `P60-C03`: wrong DPAPI Current User, logon session, install owner, key scope,
  build, implementation digest, or entropy version rejected;
- `P60-C04`: backend/user/session/cipher drift between prepare, decrypt, publish,
  and readback burns the operation;
- `P60-C05`: same history on a different ciphertext inode rejected; and
- `P60-C06`: plaintext/fixture source on a Production layout rejected before
  store/Profile effect.

### P60-J — strict JSON and resources

- `P60-J01`: duplicate outer `cipher_suite`, `ciphertext_b64`, document hash,
  or version, equal and different values;
- `P60-J02`: duplicate decrypted revision, predecessor head, active envelope,
  ordered records, records hash, or nested history-record action/candidate/
  predecessor, equal and different values;
- `P60-J03`: NaN, Infinity, -Infinity, BOM, trailing data, invalid UTF-8, control,
  and NUL;
- `P60-J04`: deep/wide containers, huge strings, excessive members/items/nodes,
  recursion boundary, and file-size boundary;
- `P60-J05`: custom Mapping/Sequence/scalar, bool-as-int, and caller pre-parsed
  Mapping;
- `P60-J06`: malformed body-free failure does not echo input/path/OS detail and
  service remains available; and
- `P60-J07`: ambiguous current/preimage is preserved with mutation zero;
- `P60-J08`: omitted/null/empty/zero/recursive self-hash, wrong schema/version/
  domain/canonicalization, mismatched nested record hash, or mismatched
  cumulative-effects body/hash rejects before effect; and
- `P60-J09`: immutable revision without the complete embedded encrypted outer,
  decrypted history without complete active/history bodies, hash-only rollback,
  or hash-only Profile projection rejects before operation entry.

### P60-P — promoted-source capability

- `P60-P01`: direct/copy/serialized/rehashed public source read or binding has
  authority zero;
- `P60-P02`: module token/sentinel access cannot mint a live capability;
- `P60-P03`: same coordinates/bytes on a different inode rejected;
- `P60-P04`: source close/path swap, ancestor replacement, reparse, hardlink,
  or security drift rejected;
- `P60-P05`: forged envelope, stale revision/head/history, wrong registry or
  wrong install/owner/build rejected;
- `P60-P06`: wrong consumer operation/Profile or missing TASK-069/TASK-061-A
  live binding rejected;
- `P60-P07`: double/concurrent/exception/crash reuse rejected;
- `P60-P08`: fixture capability on Production layout rejected; and
- `P60-P09`: wrong method/operation/vector is rejected before source-session
  budget entry and leaves the victim budget unchanged; uncertainty after a
  matched durable entry burns before any later consumer retry; and
- `P60-P10`: missing, stale, changed, or noncanonical TASK-069
  `PROFILE_SOURCE_BINDING_V2` consumer-contract digest keeps Profile operation
  calls and mutations zero; and
- `P60-P11`: the exact successful source route proves
  `PINNED -> SEED_MOVED -> PREFLIGHT_BOUND -> PROJECTED` once with direct
  TASK-069 handoff and no TASK-061/source-byte exposure.

### P60-R — completion/current-source dependency

- `P60-R01`: exact terminal plus exact receipt/source-session readback succeeds;
- `P60-R02`: missing, copied, rehashed, malformed, or wrong-version receipt is
  dependency-N.C.;
- `P60-R03`: stale/cross-instance/build/session/DPAPI/chain binding rejects;
- `P60-R04`: receipt stat-open/read-post, same-bytes-different-inode, ancestor,
  reparse, hardlink, or security drift rejects; and
- `P60-R05`: same key/body/identity is read-only duplicate while different body
  or identity is collision STOP; and
- `P60-R06`: TASK-061-A receipt-only currentness, TASK-061-B receipt-only
  currentness, and TASK-069 live-session ABIs are three disjoint one-use
  families. A-to-B, B-to-A, A-to-069, B-to-069, 069-to-A, and 069-to-B
  forwarding each reject independently. Public receipt-only bodies cannot enter
  the live-session ABI; a live session cannot enter either receipt/currentness
  reader. Wrong operation, wrong method, copy, serialization, and
  deserialization are independently rejected for every family before entry;
- `P60-R07`: TASK-061-A reader double/concurrent entry permits one winner and
  returns exactly one port; every loser returns zero;
- `P60-R08`: TASK-061-A reader exception, timeout, process loss, or response loss
  burns the entered slot and replacement-port minting is zero;
- `P60-R09`: TASK-061-A replay, wrong operation/method, copy, or deserialization
  rejects before entry and preserves the victim slot; and
- `P60-R10`: TASK-069 live-session transfer has the same exact single-winner,
  exception-burn, replay, and zero-replacement rules independently of TASK-061-A;
  and
- `P60-R11` through `P60-R14`: TASK-061-B uses a distinct B-bound reader slot
  with exact success, double/concurrent loser, exception/loss burn, and
  replay/wrong/copy rejection; A-port forwarding and reuse remain zero.

### 17.1 Executable vector ledger

The matrix is normative executable test data. Every row names one literal future
pytest node ID; parameter IDs must be supplied explicitly with `ids=[...]` so
collection produces that exact node. No alias, family name, range, `default`,
`same as`, union, or prose placeholder is an oracle.

`D=(revision, head, Profile, Human-consume, source-reservation,
source-materialization, completion-receipt, owned-temp, owned-orphan,
phase-record, unrelated-overwrite, unrelated-delete)` is the signed numeric
delta after the row's exact frozen pre-seam fixture.
`Z=(0,0,0,0,0,0,0,0,0,0,0,0)`. Reservation and materialization count their
separate immutable no-replace records; completion-receipt counts its immutable
namespace object; owned-temp counts a still-live operation-created temp at the
observation seam. `HB` and `SB` are
separate Human-decision and source-session budgets: `N=not issued/applicable`,
`U=one unentered budget preserved`, `B=entered and burned by this node`, and
`A=already zero in the frozen pre-seam fixture`. Every row also asserts public
body/path/OS-detail leakage zero.

`RP=(R61A,R61B,R69)` is the triple of durable private ABI return-slot budgets for
the TASK-061-A receipt/currentness reader, TASK-061-B receipt/currentness reader,
and TASK-069 live-session transfer:
`N=not issued/applicable`, `U=one unentered slot preserved`, `B=entered and
burned/resolved by this node`, and `A=already zero in the frozen pre-seam
fixture`. A row that emits a port states the exact return count; every other row
states return zero.

For recovery-only nodes, `RW` is the signed durable recovery-winner-slot delta
after the frozen pre-seam fixture. Every recovery row below states `RW=0|1`
literally; `RW=1` never grants a second effect and a repeated recovery query has
`RW=0` and `D=Z`.

| Vector | Exact pytest node ID | Frozen seam | Private -> public outcome; exact D | HB/SB | Recovery |
|---|---|---|---|---|---|
| P60-H01 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_public_confirmation_objects_never_authorize[P60-H01]` | before challenge issue | `REJECTED_EFFECT0`; `D=Z` | N/N | fresh plan |
| P60-H02 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_public_confirmation_objects_never_authorize[P60-H02]` | before challenge issue | `REJECTED_EFFECT0`; `D=Z` | N/N | fresh plan |
| P60-H03 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_public_confirmation_objects_never_authorize[P60-H03]` | before handle match | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh plan |
| P60-H04 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_public_confirmation_objects_never_authorize[P60-H04]` | before handle match | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh plan |
| P60-H05 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H05]` | before handle match | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh plan |
| P60-H06 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H06]` | before action match | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh plan |
| P60-H07 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H07]` | before vector match | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh plan |
| P60-H08 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H08]` | before challenge entry | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh plan |
| P60-H09 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H09]` | before challenge entry | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh plan |
| P60-H10-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H10-a]` | concurrent loser before durable entry | `REJECTED_EFFECT0`; `D=Z` | U/N | winner only; loser retry zero |
| P60-H10-b | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H10-b]` | exception after entry before store effect | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,1,0,0,0,0,0,2,0,0)` | B/N | broker recovery only |
| P60-H10-c | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H10-c]` | process loss after entry | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,1,0,0,0,0,0,2,0,0)` | B/N | issue/apply retry zero |
| P60-H11-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H11-a]` | exact committed terminal query after the source-session consumer already entered | `DUPLICATE_COMMITTED_EVENT`; `D=Z` | A/A | repeatable read-only |
| P60-H11-b1 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H11-b1]` | same key, different body | `COLLISION_STOP`; `D=Z` | A/A | preserve |
| P60-H11-b2 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H11-b2]` | same key/body, different physical identity | `COLLISION_STOP`; `D=Z` | A/A | preserve |
| P60-H12 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H12]` | Production composition preflight | `REJECTED_EFFECT0`; `D=Z` | U/N | Product operation call zero |
| P60-H13 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H13]` | candidate/eligibility preflight | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh trusted read only |
| P60-S01 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_store_secure_lock_cas_and_fault_matrix[P60-S01]` | lock/genesis classification before entry | `COLLISION_STOP`; `D=Z` | U/N | one classification; retry zero |
| P60-S02 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_store_secure_lock_cas_and_fault_matrix[P60-S02]` | lock security preflight | `REJECTED_EFFECT0`; `D=Z` | U/N | preserve lock |
| P60-S03 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_store_secure_lock_cas_and_fault_matrix[P60-S03]` | genesis lease before revision publish | `COLLISION_STOP`; `D=Z` | A/N | preserve appeared target |
| P60-S04 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_store_secure_lock_cas_and_fault_matrix[P60-S04]` | predecessor snapshot/currentness read | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh plan |
| P60-S05 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_store_secure_lock_cas_and_fault_matrix[P60-S05]` | predecessor claim preflight | `COLLISION_STOP`; `D=Z` | A/N | winner only |
| P60-S06 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S06]` | before durable `CLAIM_PUBLISH_PENDING` | `COLLISION_STOP`; `D=Z` | A/N | existing revision orphan preserved |
| P60-S07 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S07]` | claim visible before readback | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(1,1,0,0,0,0,0,0,-1,0,0,0)` | A/N | `recover_transition` readback only |
| P60-S08 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_store_secure_lock_cas_and_fault_matrix[P60-S08]` | temp cleanup identity check | `COLLISION_STOP`; `D=Z` | A/N | foreign temp preserved |
| P60-S09-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_store_secure_lock_cas_and_fault_matrix[P60-S09-a]` | revision temp write/flush/identity | `REJECTED_EFFECT0`; `D=Z` | A/N | exact owned temp cleanup only |
| P60-S09-b1 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-b1]` | revision publish call rejected before namespace effect | `REJECTED_EFFECT0`; `D=Z` | A/N | exact owned temp only |
| P60-S09-b2 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-b2]` | revision namespace visible before directory durability | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,1,0,0,0)` | A/N | orphan preserve/readback only |
| P60-S09-b3 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-b3]` | revision directory durability failure | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,1,0,0,0)` | A/N | orphan preserve/readback only |
| P60-S09-b4 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-b4]` | revision reopen/readback/close/security failure | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,1,0,0,0)` | A/N | orphan preserve/readback only |
| P60-S09-c | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-c]` | claim temp write/flush/identity with existing orphan fixture | `REJECTED_EFFECT0`; `D=Z` | A/N | existing orphan preserved |
| P60-S09-d1 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-d1]` | durable pending; claim publish rejected before namespace effect with exact absence | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | A/N | caller publish retry zero; one authenticated recovery winner may execute P60-S15-a |
| P60-S09-d2 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-d2]` | phase-3 fixture; claim namespace visible before directory durability | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,1,0,0,0,0,0,0,-1,0,0,0)` | A/N | `recover_transition` only |
| P60-S09-d3 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-d3]` | phase-3 fixture; claim directory durability failure | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,1,0,0,0,0,0,0,-1,0,0,0)` | A/N | `recover_transition` only |
| P60-S09-d4 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-d4]` | phase-3 fixture; post-claim reopen/readback/close/security failure | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,1,0,0,0,0,0,0,-1,0,0,0)` | A/N | `recover_transition` only |
| P60-S10 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_recovery_preserves_foreign_and_ambiguous_state[P60-S10]` | recovery classifier entry | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | A/N | repair/delete zero |
| P60-S11 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_recovery_preserves_foreign_and_ambiguous_state[P60-S11]` | rollback current-target preflight | `COLLISION_STOP`; `D=Z` | U/N | restore/delete zero |
| P60-S12 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_recovery_preserves_foreign_and_ambiguous_state[P60-S12]` | cleanup identity recheck | `CLEANUP_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | A/N | foreign preserved |
| P60-S13-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-a]` | PREPARED no-replace collision | `COLLISION_STOP`; `D=Z` | U/N | preserve |
| P60-S13-b | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-b]` | phase predecessor/fork/gap/ordinal validation | `COLLISION_STOP`; `D=Z` | A/N | preserve chain |
| P60-S14-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_successful_promotion_and_rollback_are_exact[P60-S14-a]` | valid genesis PROMOTE before operation entry | `COMMITTED`; `D=(1,1,0,1,1,1,1,0,0,10,0,0)` | B/U | exact terminal plus one unentered source session |
| P60-S14-b | `tests/test_task060_montage_preference_authority_operation.py::test_task060_successful_promotion_and_rollback_are_exact[P60-S14-b]` | valid existing-head PROMOTE before operation entry | `COMMITTED`; `D=(1,1,0,1,1,1,1,0,0,10,0,0)` | B/U | exact terminal plus one unentered source session |
| P60-S14-c | `tests/test_task060_montage_preference_authority_operation.py::test_task060_successful_promotion_and_rollback_are_exact[P60-S14-c]` | valid existing-head ROLLBACK before operation entry | `COMMITTED`; `D=(1,1,0,1,1,1,1,0,0,10,0,0)` | B/U | exact terminal plus one unentered source session |
| P60-S14-d | `tests/test_task060_montage_preference_authority_operation.py::test_task060_successful_promotion_and_rollback_are_exact[P60-S14-d]` | immediate exact committed terminal replay before source-session consumer entry | `DUPLICATE_COMMITTED_EVENT`; `D=Z` | A/U | read-only; no second revision/head/session |
| P60-S15-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-a]` | phase 3, exact claim absence, one revision orphan | `COMMITTED`; `D=(0,1,0,0,1,1,1,0,-1,6,0,0)`; `RW=1` | A/U | winner publishes bound claim once and completes |
| P60-S15-b | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-b]` | phase 3, exact bound claim already present | `COMMITTED`; `D=(0,0,0,0,1,1,1,0,0,6,0,0)`; `RW=1` | A/U | pinned classify then complete; publish delta zero |
| P60-S15-c | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-c]` | phase 3, different claim present | `COLLISION_STOP`; `D=Z`; `RW=1` | A/N | preserve both; no source session |
| P60-S15-d | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-d]` | phase 3, claim lookup ambiguous | `COMPLETION_UNKNOWN`; `D=Z`; `RW=1` | A/N | preserve; caller retry zero |
| P60-S15-e | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-e]` | resolved recovery-winner slot queried again | `DUPLICATE_COMMITTED_EVENT`; `D=Z`; `RW=0` | A/U | read-only reconciliation |
| P60-S15-f | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-f]` | phase 8, exact completion-receipt absence | `COMMITTED`; `D=(0,0,0,0,0,0,1,0,0,1,0,0)`; `RW=1` | A/U | publish exact bound receipt once, verify it, append phase 9 |
| P60-S15-g | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-g]` | phase 8, exact bound receipt already present | `COMMITTED`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)`; `RW=1` | A/U | pinned receipt readback then append phase 9; receipt publish zero |
| P60-S15-h1 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-h1]` | phase 8, different receipt body present | `COLLISION_STOP`; `D=Z`; `RW=1` | A/U | preserve different receipt; terminal phase zero |
| P60-S15-h2 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-h2]` | phase 8, same receipt body on a different physical identity | `COLLISION_STOP`; `D=Z`; `RW=1` | A/U | preserve different identity; terminal phase zero |
| P60-S15-i | `tests/test_task060_montage_preference_authority_operation.py::test_task060_claim_pending_and_late_phase_recovery_are_exact[P60-S15-i]` | phase 8, receipt lookup ambiguous | `COMPLETION_UNKNOWN`; `D=Z`; `RW=1` | A/U | preserve; receipt/terminal/source retry zero |
| P60-S17-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_chain_length_boundary_is_inclusive[P60-S17-a]` | valid chain length 4095 | `COMMITTED`; `D=(1,1,0,1,1,1,1,0,0,10,0,0)` | B/U | resulting chain length exactly 4096 |
| P60-S17-b | `tests/test_task060_montage_preference_authority_operation.py::test_task060_chain_length_boundary_is_inclusive[P60-S17-b]` | valid chain length 4096 | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | no revision temp/publication |
| P60-S17-c | `tests/test_task060_montage_preference_authority_operation.py::test_task060_chain_length_boundary_is_inclusive[P60-S17-c]` | observed chain length 4097 | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | preserve invalid chain; repair zero |
| P60-C01 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C01]` | Production composition preflight | `REJECTED_EFFECT0`; `D=Z` | U/N | decrypt call zero |
| P60-C02 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C02]` | request/coordinate preflight | `REJECTED_EFFECT0`; `D=Z` | U/N | decrypt call zero |
| P60-C03 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C03]` | DPAPI owner/session preflight | `REJECTED_EFFECT0`; `D=Z` | U/N | decrypt call zero |
| P60-C04-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C04-a]` | prepare/decrypt drift before entry | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh trusted read |
| P60-C04-b | `tests/test_task060_montage_preference_authority_operation.py::test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C04-b]` | drift after entry before revision | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | A/N | broker recovery only |
| P60-C04-c | `tests/test_task060_montage_preference_authority_operation.py::test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C04-c]` | drift with revision orphan fixture | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | A/N | existing orphan preserved |
| P60-C04-d | `tests/test_task060_montage_preference_authority_operation.py::test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C04-d]` | drift after claim before final readback | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | A/N | existing head recovery only |
| P60-C05 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C05]` | source physical snapshot preflight | `REJECTED_EFFECT0`; `D=Z` | U/N | fresh plan |
| P60-C06 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C06]` | layout/source-profile preflight | `REJECTED_EFFECT0`; `D=Z` | U/N | audit only |
| P60-J01 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_outer_and_decrypted_json_matrix[P60-J01]` | outer strict decode | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | ambiguous bytes preserved |
| P60-J02 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_outer_and_decrypted_json_matrix[P60-J02]` | decrypted strict decode | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | ambiguous bytes preserved |
| P60-J03 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_outer_and_decrypted_json_matrix[P60-J03]` | strict byte/decode gate | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | service available |
| P60-J04 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_outer_and_decrypted_json_matrix[P60-J04]` | bounded parser gate | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | service available |
| P60-J05 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_outer_and_decrypted_json_matrix[P60-J05]` | built-in-type gate | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | canonicalization zero |
| P60-J06 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_public_failures_are_body_free[P60-J06]` | public failure projection | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | body-free code only |
| P60-J07 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_recovery_preserves_foreign_and_ambiguous_state[P60-J07]` | recovery/preimage reader | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | A/N | preserve; mutation zero |
| P60-J08 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_self_hash_and_nested_body_preimages_are_exact[P60-J08]` | canonical self-hash/nested-effect preflight | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | canonicalization/operation entry zero |
| P60-J09 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_authority_documents_embed_exact_recoverable_bodies[P60-J09]` | immutable revision/decrypted-history semantic preflight | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z` | U/N | rollback/Profile projection zero |
| P60-P01 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_promoted_source_capability_is_private_single_use[P60-P01]` | public audit-object preflight with victim source session issued | `REJECTED_EFFECT0`; `D=Z` | A/U | session call zero; victim budget preserved |
| P60-P02 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_promoted_source_capability_is_private_single_use[P60-P02]` | public/module-token preflight with victim source session issued | `REJECTED_EFFECT0`; `D=Z` | A/U | session call zero; victim budget preserved |
| P60-P03 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P03]` | source physical match with victim source session issued | `REJECTED_EFFECT0`; `D=Z` | A/U | session call zero; victim budget preserved |
| P60-P04 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P04]` | source/ancestor lease preflight with victim source session issued | `REJECTED_EFFECT0`; `D=Z` | A/U | session call zero; victim budget preserved |
| P60-P05 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P05]` | source/currentness vector match with victim source session issued | `REJECTED_EFFECT0`; `D=Z` | A/U | session call zero; victim budget preserved |
| P60-P06 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P06]` | consumer-contract match with victim source session issued | `DEPENDENCY_NC_EFFECT0`; `D=Z` | A/U | handoff zero; victim budget preserved |
| P60-P07-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_promoted_source_capability_is_private_single_use[P60-P07-a]` | concurrent loser before source entry | `REJECTED_EFFECT0`; `D=Z` | A/U | winner only |
| P60-P07-b | `tests/test_task060_montage_preference_authority_operation.py::test_task060_promoted_source_capability_is_private_single_use[P60-P07-b]` | exception after matched source entry | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | A/B | source recovery only |
| P60-P07-c | `tests/test_task060_montage_preference_authority_operation.py::test_task060_promoted_source_capability_is_private_single_use[P60-P07-c]` | process/response loss after matched source entry | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | A/B | seed/session reissue zero |
| P60-P08 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_promoted_source_capability_is_private_single_use[P60-P08]` | Production-layout fixture gate | `REJECTED_EFFECT0`; `D=Z` | N/N | fixture audit only |
| P60-P09-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P09-a]` | wrong method/operation/vector before source entry | `REJECTED_EFFECT0`; `D=Z` | A/U | victim source budget preserved |
| P60-P09-b | `tests/test_task060_montage_preference_authority_operation.py::test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P09-b]` | unknown result after matched source entry | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | A/B | consumer retry zero |
| P60-P10 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P10]` | canonical contract-digest preflight | `DEPENDENCY_NC_EFFECT0`; `D=Z` | A/U | adapter/session entry zero |
| P60-P11 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P11]` | exact session materialized before direct TASK-069 handoff | `PROJECTED -> COMMITTED`; `D=Z` | A/B | seed/preflight/bind/project calls exact 1/1/1/1; TASK-069 receives one projection; TASK-061/source-byte exposure zero |
| P60-R01 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_current_source_receipt_is_exact[P60-R01]` | exact phase-9 terminal and exact pinned receipt/session | `CURRENT_SOURCE_VERIFIED -> COMMITTED`; `D=Z` | A/U | `RP=(B,N,N)`; TASK-061-A port return exact 1; other returns zero |
| P60-R02 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_current_source_receipt_is_exact[P60-R02]` | receipt strict/identity preflight | `DEPENDENCY_NC_EFFECT0`; `D=Z` | A/U | `RP=(U,N,N)`; port return zero |
| P60-R03 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_current_source_receipt_is_exact[P60-R03]` | receipt/current chain vector match | `DEPENDENCY_NC_EFFECT0`; `D=Z` | A/U | `RP=(U,N,N)`; port return zero; fresh trusted read required |
| P60-R04 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_current_source_receipt_is_exact[P60-R04]` | receipt physical snapshot/currentness | `DEPENDENCY_NC_EFFECT0`; `D=Z` | A/U | `RP=(U,N,N)`; port return zero; ambiguous bytes preserved |
| P60-R05-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_current_source_receipt_is_exact[P60-R05-a]` | same key/body/physical identity after A-reader slot resolved | `DUPLICATE_COMMITTED_EVENT`; `D=Z` | A/U | `RP=(A,N,N)`; port return zero; read-only |
| P60-R05-b1 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_current_source_receipt_is_exact[P60-R05-b1]` | same key, different body | `COLLISION_STOP`; `D=Z` | A/U | `RP=(U,N,N)`; preserve; port return zero |
| P60-R05-b2 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_current_source_receipt_is_exact[P60-R05-b2]` | same key/body, different physical identity | `COLLISION_STOP`; `D=Z` | A/U | `RP=(U,N,N)`; preserve; port return zero |
| P60-R06 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_consumer_abis_are_disjoint[P60-R06]` | one exact independently parameterized A/B/069 cross-family, receipt-only/live-session, wrong-operation/method, copy, serialize, or deserialize attempt before every victim slot entry | `REJECTED_EFFECT0`; `D=Z` | A/U | `RP=(U,U,U)`; all three victim budgets unchanged; entry/return/consume/forward/exposure delta zero |
| P60-R07 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_consumer_port_budgets_are_single_use[P60-R07]` | TASK-061-A concurrent loser after one exact winner | `REJECTED_EFFECT0`; `D=Z` | A/U | `RP=(A,N,N)`; loser/second-call port return zero |
| P60-R08 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_consumer_port_budgets_are_single_use[P60-R08]` | TASK-061-A exception/timeout/process-loss/response-loss after entry | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | A/U | `RP=(B,N,N)`; replacement-port return zero |
| P60-R09 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_consumer_port_budgets_are_single_use[P60-R09]` | TASK-061-A replay/wrong operation/copy/deserialization before entry | `REJECTED_EFFECT0`; `D=Z` | A/U | `RP=(U,N,N)`; victim preserved; port return zero |
| P60-R10-a | `tests/test_task060_montage_preference_authority_operation.py::test_task060_consumer_port_budgets_are_single_use[P60-R10-a]` | exact TASK-069 live-session transfer | `PROJECTED -> COMMITTED`; `D=Z` | A/B | `RP=(N,N,B)`; live transfer exact 1; other returns zero |
| P60-R10-b | `tests/test_task060_montage_preference_authority_operation.py::test_task060_consumer_port_budgets_are_single_use[P60-R10-b]` | TASK-069 double/concurrent loser after exact winner | `REJECTED_EFFECT0`; `D=Z` | A/A | `RP=(N,N,A)`; live transfer return zero |
| P60-R10-c | `tests/test_task060_montage_preference_authority_operation.py::test_task060_consumer_port_budgets_are_single_use[P60-R10-c]` | TASK-069 exception/timeout/process-loss/response-loss after entry | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | A/B | `RP=(N,N,B)`; replacement session/port zero |
| P60-R10-d | `tests/test_task060_montage_preference_authority_operation.py::test_task060_consumer_port_budgets_are_single_use[P60-R10-d]` | TASK-069 replay/wrong operation/copy/deserialization before entry | `REJECTED_EFFECT0`; `D=Z` | A/U | `RP=(N,N,U)`; victim preserved; transfer return zero |
| P60-R11 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_task061b_reader_budget_is_distinct[P60-R11]` | exact TASK-061-B admitted operation and fresh terminal/currentness | `CURRENT_SOURCE_VERIFIED -> COMMITTED`; `D=Z` | A/U | `RP=(N,B,N)`; B-bound port exact 1; A/069 returns zero |
| P60-R12 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_task061b_reader_budget_is_distinct[P60-R12]` | TASK-061-B double/concurrent loser after one exact winner | `REJECTED_EFFECT0`; `D=Z` | A/U | `RP=(N,A,N)`; loser/second-call return zero |
| P60-R13 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_task061b_reader_budget_is_distinct[P60-R13]` | TASK-061-B exception/timeout/process-loss/response-loss after entry | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | A/U | `RP=(N,B,N)`; replacement-port return zero |
| P60-R14 | `tests/test_task060_montage_preference_authority_operation.py::test_task060_task061b_reader_budget_is_distinct[P60-R14]` | TASK-061-B replay/wrong operation/A-port forward/copy/deserialization before entry | `REJECTED_EFFECT0`; `D=Z` | A/U | `RP=(N,U,N)`; B victim preserved; port return zero |

Phase publication has a separate literal ledger. For phase ordinal `p`, `temp`
means failure before namespace publication and has `D=Z`; `namespace`,
`durability`, and `readback` each have exact `D=(0,0,0,0,0,0,0,0,0,1,0,0)`. Each row
below is one collected pytest node and one closed oracle; no shortened parameter
ID, grouped seam, range, or inherited outcome is permitted.

| Phase | Seam | Exact pytest node ID | HB/SB | Private -> public outcome; exact D | Recovery |
|---|---|---|---|---|---|
| 0 `PREPARED` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c0-temp]` | U/N | `REJECTED_EFFECT0`; `D=Z` | discard only exact operation-owned temp; phase absent |
| 0 `PREPARED` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c0-namespace]` | U/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | classify exact PREPARED; no effect retry |
| 0 `PREPARED` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c0-durability]` | U/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | classify exact PREPARED; no effect retry |
| 0 `PREPARED` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c0-readback]` | U/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | pinned PREPARED reconciliation only |
| 1 `DECISION_CONSUMED` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c1-temp]` | A/N | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | frozen fixture already consumed Human budget; retry zero |
| 1 `DECISION_CONSUMED` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c1-namespace]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | classify exact DECISION_CONSUMED; Human retry zero |
| 1 `DECISION_CONSUMED` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c1-durability]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | classify exact DECISION_CONSUMED; Human retry zero |
| 1 `DECISION_CONSUMED` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c1-readback]` | A/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | pinned DECISION_CONSUMED reconciliation only |
| 2 `REVISION_PUBLISHED` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c2-temp]` | A/N | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | existing orphan preserved; claim zero |
| 2 `REVISION_PUBLISHED` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c2-namespace]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | existing orphan preserved; claim zero |
| 2 `REVISION_PUBLISHED` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c2-durability]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | existing orphan preserved; claim zero |
| 2 `REVISION_PUBLISHED` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c2-readback]` | A/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | exact phase reconciliation; claim zero |
| 3 `CLAIM_PUBLISH_PENDING` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c3-temp]` | A/N | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z` | recovery-winner only; caller retry zero |
| 3 `CLAIM_PUBLISH_PENDING` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c3-namespace]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | recovery-winner only; caller retry zero |
| 3 `CLAIM_PUBLISH_PENDING` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c3-durability]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | recovery-winner only; caller retry zero |
| 3 `CLAIM_PUBLISH_PENDING` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c3-readback]` | A/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | recovery-winner exact pending reconciliation only |
| 4 `SUCCESSOR_CLAIM_PUBLISHED` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c4-temp]` | A/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | claim retry zero; pinned claim/revision readback only |
| 4 `SUCCESSOR_CLAIM_PUBLISHED` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c4-namespace]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | claim retry zero; pinned claim/revision readback only |
| 4 `SUCCESSOR_CLAIM_PUBLISHED` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c4-durability]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | claim retry zero; pinned claim/revision readback only |
| 4 `SUCCESSOR_CLAIM_PUBLISHED` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c4-readback]` | A/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | pinned claim/revision reconciliation only |
| 5 `HEAD_READBACK_VERIFIED` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c5-temp]` | A/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | append later identical phase only |
| 5 `HEAD_READBACK_VERIFIED` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c5-namespace]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | append later identical phase only |
| 5 `HEAD_READBACK_VERIFIED` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c5-durability]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | append later identical phase only |
| 5 `HEAD_READBACK_VERIFIED` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c5-readback]` | A/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | exact phase reconciliation only |
| 6 `SOURCE_SESSION_RESERVED` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c6-temp]` | A/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | reservation is already durable; exact phase recovery only |
| 6 `SOURCE_SESSION_RESERVED` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c6-namespace]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | reservation reissue zero; exact phase recovery only |
| 6 `SOURCE_SESSION_RESERVED` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c6-durability]` | A/N | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | reservation reissue zero; exact phase recovery only |
| 6 `SOURCE_SESSION_RESERVED` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c6-readback]` | A/N | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | exact phase reconciliation only |
| 7 `SOURCE_SESSION_MATERIALIZED` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c7-temp]` | A/U | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | materialization is already durable; same session only |
| 7 `SOURCE_SESSION_MATERIALIZED` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c7-namespace]` | A/U | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | session reissue zero; exact phase recovery only |
| 7 `SOURCE_SESSION_MATERIALIZED` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c7-durability]` | A/U | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | session reissue zero; exact phase recovery only |
| 7 `SOURCE_SESSION_MATERIALIZED` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c7-readback]` | A/U | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | exact phase reconciliation only |
| 8 `COMPLETION_RECEIPT_PENDING` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c8-temp]` | A/U | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | receipt namespace effect zero; exact pending recovery only |
| 8 `COMPLETION_RECEIPT_PENDING` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c8-namespace]` | A/U | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | exact pending recovery only |
| 8 `COMPLETION_RECEIPT_PENDING` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c8-durability]` | A/U | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | exact pending recovery only |
| 8 `COMPLETION_RECEIPT_PENDING` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c8-readback]` | A/U | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | exact pending reconciliation only |
| 9 `TERMINAL_COMMITTED` | temp | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c9-temp]` | A/U | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z` | receipt is already exact/durable; terminal recovery only |
| 9 `TERMINAL_COMMITTED` | namespace | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c9-namespace]` | A/U | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | no receipt/source republish; terminal reconciliation only |
| 9 `TERMINAL_COMMITTED` | durability | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c9-durability]` | A/U | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | no receipt/source republish; terminal reconciliation only |
| 9 `TERMINAL_COMMITTED` | readback | `tests/test_task060_montage_preference_authority_operation.py::test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-c9-readback]` | A/U | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)` | exact terminal readback only; no second effect |

### 17.2 Closed in-node case inventory

Each exact umbrella pytest node below must execute **every** named case against a
fresh fixture. The listed case set is closed; omission, dynamic discovery,
range generation, an unlisted default, or reusing a mutated fixture is a test
failure. Each case independently asserts the literal common oracle in its row,
including exact `D`, `HB/SB`, body/path/OS-detail leakage zero, and service
availability where stated.

| Exact umbrella node | Mandatory exact case IDs | Literal oracle for each named case |
|---|---|---|
| `test_task060_public_confirmation_objects_never_authorize[P60-H03]` | `direct_dataclass`, `copy`, `replace`, `pickle`, `deserialize` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_public_confirmation_objects_never_authorize[P60-H04]` | `from_dict`, `recomputed_self_hash` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H05]` | `caller_new_id`, `caller_timestamp`, `replay_new_id` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H06]` | `promote_ticket_for_rollback`, `rollback_ticket_for_promote` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H07]` | `wrong_candidate`, `wrong_target`, `wrong_revision`, `wrong_head`, `wrong_owner`, `wrong_project`, `wrong_install`, `wrong_user`, `wrong_session`, `wrong_process`, `wrong_broker`, `wrong_build` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H08]` | `stat_open_swap`, `read_post_swap`, `hardlink`, `reparse`, `ancestor_drift`, `security_drift` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H09]` | `expired`, `wall_clock_rollback`, `large_forward_jump`, `suspend_resume`, `boot_restart`, `phase_clock_swap` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H12]` | `production_test_clock`, `caller_backend`, `caller_hook`, `caller_failure_injector` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; Product operation calls zero |
| `test_task060_human_challenge_is_action_specific_single_use_and_burned[P60-H13]` | `public_candidate`, `copied_eligibility`, `rehashed_eligibility`, `wrong_producer`, `wrong_build`, `wrong_project`, `stale_currentness`, `candidate_stat_open_swap`, `candidate_read_post_swap`, `candidate_identity_swap` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_store_secure_lock_cas_and_fault_matrix[P60-S01]` | `initial_race_loser`, `existing_race`, `late_initial_collision` | `COLLISION_STOP`; `D=Z`; HB/SB U/N |
| `test_task060_store_secure_lock_cas_and_fault_matrix[P60-S02]` | `symlink`, `reparse`, `hardlink`, `nlink_gt_1`, `dacl_drift`, `ancestor_drift` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_store_secure_lock_cas_and_fault_matrix[P60-S03]` | `appeared_identical_bytes`, `appeared_different_bytes` | `COLLISION_STOP`; `D=Z`; HB/SB A/N; appeared target preserved |
| `test_task060_store_secure_lock_cas_and_fault_matrix[P60-S04]` | `stat_open_swap`, `open_read_swap`, `read_post_swap`, `same_bytes_different_inode` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_store_secure_lock_cas_and_fault_matrix[P60-S05]` | `concurrent_promote`, `concurrent_promote_rollback`, `revision_mismatch`, `head_mismatch` | `COLLISION_STOP`; `D=Z`; HB/SB A/N |
| `test_task060_store_secure_lock_cas_and_fault_matrix[P60-S08]` | `temp_close_swap`, `temp_hardlink`, `foreign_temp_collision` | `COLLISION_STOP`; `D=Z`; HB/SB A/N; foreign temp preserved |
| `test_task060_store_secure_lock_cas_and_fault_matrix[P60-S09-a]` | `revision_temp_write`, `revision_temp_flush`, `revision_temp_identity` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/N; exact owned temp cleanup only |
| `test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-b4]` | `revision_reopen_failure`, `revision_readback_failure`, `revision_close_failure`, `revision_security_failure` | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,1,0,0,0)`; HB/SB A/N; orphan preserved |
| `test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S09-d4]` | `claim_reopen_failure`, `claim_readback_failure`, `claim_close_failure`, `claim_security_failure` | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,1,0,0,0,0,0,0,-1,0,0,0)`; HB/SB A/N; recovery only |
| `test_task060_recovery_preserves_foreign_and_ambiguous_state[P60-S10]` | `one_sided_revision`, `one_sided_claim`, `unknown_phase`, `ambiguous_predecessor` | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/N; repair/delete zero |
| `test_task060_immutable_revision_claim_phase_and_recovery_matrix[P60-S13-b]` | `predecessor_bytes_swap`, `predecessor_inode_swap`, `predecessor_self_hash_swap`, `duplicate_phase`, `forked_phase`, `phase_gap`, `non_monotonic_ordinal` | `COLLISION_STOP`; `D=Z`; HB/SB A/N; chain preserved |
| `test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C01]` | `synthetic_cipher`, `custom_protocol`, `same_suite_fake`, `monkeypatched_decryptor` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; decrypt calls zero |
| `test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C02]` | `caller_suite`, `caller_entropy`, `caller_path`, `caller_coordinates`, `caller_history`, `caller_sid`, `caller_session`, `caller_registry_coordinate` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; decrypt calls zero |
| `test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C03]` | `wrong_current_user`, `wrong_logon_session`, `wrong_install_owner`, `wrong_key_scope`, `wrong_build`, `wrong_implementation_digest`, `wrong_entropy_version` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C04-a]` | `prepare_backend_drift`, `decrypt_backend_drift` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; fresh trusted read |
| `test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C05]` | `same_history_different_ciphertext_inode`, `same_ciphertext_different_inode` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_production_dpapi_backend_and_user_session_are_fixed[P60-C06]` | `plaintext_production_source`, `fixture_production_source` | `REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_strict_outer_and_decrypted_json_matrix[P60-J01]` | `duplicate_cipher_suite_equal`, `duplicate_cipher_suite_different`, `duplicate_ciphertext_equal`, `duplicate_ciphertext_different`, `duplicate_document_hash_equal`, `duplicate_document_hash_different`, `duplicate_version_equal`, `duplicate_version_different` | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; canonicalization zero |
| `test_task060_strict_outer_and_decrypted_json_matrix[P60-J02]` | `duplicate_revision_equal`, `duplicate_revision_different`, `duplicate_predecessor_head_equal`, `duplicate_predecessor_head_different`, `duplicate_active_envelope_equal`, `duplicate_active_envelope_different`, `duplicate_records_equal`, `duplicate_records_different`, `duplicate_records_hash_equal`, `duplicate_records_hash_different`, `nested_duplicate_action_equal`, `nested_duplicate_action_different`, `nested_duplicate_profile_candidate_equal`, `nested_duplicate_profile_candidate_different`, `nested_duplicate_prior_history_record_equal`, `nested_duplicate_prior_history_record_different` | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; canonicalization zero |
| `test_task060_self_hash_and_nested_body_preimages_are_exact[P60-J08]` | `self_hash_omitted`, `self_hash_null`, `self_hash_empty`, `self_hash_zero`, `self_hash_recursive`, `wrong_domain`, `wrong_schema_name`, `wrong_schema_version`, `wrong_canonicalization`, `nested_record_hash_mismatch`, `cumulative_effects_body_mismatch`, `cumulative_effects_hash_mismatch` | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; canonicalization/operation entry zero |
| `test_task060_authority_documents_embed_exact_recoverable_bodies[P60-J09]` | `revision_outer_missing`, `revision_outer_hash_only`, `decrypted_active_body_missing`, `decrypted_records_missing`, `decrypted_records_hash_only`, `rollback_body_unavailable`, `profile_projection_body_unavailable` | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; rollback/Profile projection zero |
| `test_task060_strict_outer_and_decrypted_json_matrix[P60-J03]` | `nan`, `positive_infinity`, `negative_infinity`, `bom`, `trailing_data`, `invalid_utf8`, `escaped_control`, `raw_control`, `nul` | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; service available |
| `test_task060_strict_outer_and_decrypted_json_matrix[P60-J04]` | `deep_recursion_boundary`, `wide_object`, `wide_array`, `huge_string`, `raw_outer_size`, `decrypted_size` | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; parse/hash zero and service available |
| `test_task060_strict_outer_and_decrypted_json_matrix[P60-J05]` | `custom_mapping`, `custom_sequence`, `custom_scalar`, `bool_as_int`, `caller_preparsed_mapping` | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; canonicalization zero |
| `test_task060_public_failures_are_body_free[P60-J06]` | `path_body`, `os_detail_body`, `offending_value_body`, `raw_exception_body` | `STRICT_JSON_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; response contains stable code only |
| `test_task060_promoted_source_capability_is_private_single_use[P60-P01]` | `direct`, `copy`, `serialize`, `rehashed_public_binding` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; victim source budget preserved |
| `test_task060_promoted_source_capability_is_private_single_use[P60-P02]` | `module_token`, `module_sentinel` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; victim source budget preserved |
| `test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P03]` | `same_coordinates_different_inode`, `same_bytes_different_inode` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; victim source budget preserved |
| `test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P04]` | `close_then_swap`, `ancestor_replacement`, `reparse`, `hardlink`, `security_drift` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; victim source budget preserved |
| `test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P05]` | `forged_envelope`, `stale_revision`, `stale_head`, `stale_history`, `wrong_registry`, `wrong_install`, `wrong_owner`, `wrong_build` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; victim source budget preserved |
| `test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P06]` | `wrong_consumer_operation`, `wrong_profile`, `missing_task069_contract`, `missing_task061a_binding` | `DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB A/U; handoff zero |
| `test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P09-a]` | `wrong_method`, `wrong_operation`, `wrong_vector` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; victim source budget preserved |
| `test_task060_profile_source_v2_two_stage_session_and_direct_handoff[P60-P10]` | `missing_contract`, `stale_contract`, `changed_contract`, `noncanonical_contract_digest` | `DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB A/U; adapter/session entry zero |
| `test_task060_directory_durability_evidence_is_closed[P60-S16-b]` | `evidence_hash_mismatch`, `version_mismatch`, `implementation_mismatch`, `build_mismatch` | `DIRECTORY_DURABILITY_NOT_CONFIRMED -> DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_directory_durability_evidence_is_closed[P60-S16-d]` | `directory_identity_mismatch`, `security_mismatch`, `namespace_mismatch` | `DIRECTORY_DURABILITY_NOT_CONFIRMED -> DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB U/N |
| `test_task060_directory_durability_evidence_is_closed[P60-S16-e]` | `unsupported_after_revision_namespace`, `native_failure_after_revision_namespace` | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,1,0,0,0)`; HB/SB A/N; orphan preserved |
| `test_task060_completion_current_source_receipt_is_exact[P60-R02]` | `missing_receipt`, `copied_receipt`, `rehashed_mapping`, `malformed_receipt`, `wrong_schema_version` | `DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB A/U; port return zero |
| `test_task060_completion_current_source_receipt_is_exact[P60-R03]` | `stale_terminal`, `cross_instance`, `wrong_build`, `wrong_session`, `wrong_dpapi_backend`, `wrong_revision_claim_chain`, `wrong_source_reservation`, `wrong_source_materialization` | `DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB A/U; fresh trusted read required |
| `test_task060_completion_current_source_receipt_is_exact[P60-R04]` | `stat_open_swap`, `read_post_swap`, `same_bytes_different_inode`, `ancestor_drift`, `reparse`, `hardlink`, `security_drift` | `DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB A/U; ambiguous bytes preserved |
| `test_task060_completion_current_source_receipt_is_exact[P60-R05-b1]` | `different_body` | `COLLISION_STOP`; `D=Z`; HB/SB A/U; `RP=(U,N,N)`; preserve, port return zero |
| `test_task060_completion_current_source_receipt_is_exact[P60-R05-b2]` | `different_physical_identity` | `COLLISION_STOP`; `D=Z`; HB/SB A/U; `RP=(U,N,N)`; preserve, port return zero |
| `test_task060_completion_consumer_abis_are_disjoint[P60-R06]` | `a_to_b_forward`, `b_to_a_forward`, `a_to_069_forward`, `b_to_069_forward`, `069_to_a_forward`, `069_to_b_forward`, `public_receipt_to_a_reader`, `public_receipt_to_b_reader`, `public_receipt_to_069_live_session`, `a_receipt_port_to_069_live_session`, `b_receipt_port_to_069_live_session`, `069_live_session_to_a_reader`, `069_live_session_to_b_reader`, `a_wrong_operation`, `a_wrong_method`, `b_wrong_operation`, `b_wrong_method`, `069_wrong_operation`, `069_wrong_method`, `a_copy`, `a_serialize`, `a_deserialize`, `b_copy`, `b_serialize`, `b_deserialize`, `069_copy`, `069_serialize`, `069_deserialize` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; `RP=(U,U,U)`; all victim budgets unchanged; entry/return/consume/forward/exposure delta zero |
| `test_task060_consumer_port_budgets_are_single_use[P60-R07]` | `task061a_double_call`, `task061a_concurrent_loser` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; `RP=(A,N,N)`; loser return zero |
| `test_task060_consumer_port_budgets_are_single_use[P60-R08]` | `task061a_exception`, `task061a_timeout`, `task061a_process_loss`, `task061a_response_loss` | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/U; `RP=(B,N,N)`; replacement zero |
| `test_task060_consumer_port_budgets_are_single_use[P60-R09]` | `task061a_replay`, `task061a_wrong_operation`, `task061a_wrong_method`, `task061a_copy`, `task061a_deserialization` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; `RP=(U,N,N)`; victim preserved |
| `test_task060_consumer_port_budgets_are_single_use[P60-R10-a]` | `task069_exact_live_transfer` | `PROJECTED -> COMMITTED`; `D=Z`; HB/SB A/B; `RP=(N,N,B)`; transfer exact 1 |
| `test_task060_consumer_port_budgets_are_single_use[P60-R10-b]` | `task069_double_call`, `task069_concurrent_loser` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/A; `RP=(N,N,A)`; return zero |
| `test_task060_consumer_port_budgets_are_single_use[P60-R10-c]` | `task069_exception`, `task069_timeout`, `task069_process_loss`, `task069_response_loss` | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/B; `RP=(N,N,B)`; replacement zero |
| `test_task060_consumer_port_budgets_are_single_use[P60-R10-d]` | `task069_replay`, `task069_wrong_operation`, `task069_wrong_method`, `task069_copy`, `task069_deserialization` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; `RP=(N,N,U)`; victim preserved |
| `test_task060_task061b_reader_budget_is_distinct[P60-R11]` | `task061b_exact_currentness` | `CURRENT_SOURCE_VERIFIED -> COMMITTED`; `D=Z`; HB/SB A/U; `RP=(N,B,N)`; B port exact 1 |
| `test_task060_task061b_reader_budget_is_distinct[P60-R12]` | `task061b_double_call`, `task061b_concurrent_loser` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; `RP=(N,A,N)`; loser return zero |
| `test_task060_task061b_reader_budget_is_distinct[P60-R13]` | `task061b_exception`, `task061b_timeout`, `task061b_process_loss`, `task061b_response_loss` | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/U; `RP=(N,B,N)`; replacement zero |
| `test_task060_task061b_reader_budget_is_distinct[P60-R14]` | `task061b_replay`, `task061b_wrong_operation`, `task061a_port_forward`, `task061b_copy`, `task061b_deserialization` | `REJECTED_EFFECT0`; `D=Z`; HB/SB A/U; `RP=(N,U,N)`; victim preserved |

### 17.3 Literal parser-boundary and directory-durability nodes

The following nodes supplement the umbrella cases with exact boundary and
native-evidence oracles. Each is a separately collected literal node.

| Exact pytest node ID | Frozen seam | Exact oracle |
|---|---|---|
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-outer-bytes-minus]` | outer raw bytes 1 MiB - 1 | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-outer-bytes-at]` | outer raw bytes exactly 1 MiB | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-outer-bytes-plus]` | outer raw bytes 1 MiB + 1 | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; decode/hash zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-decrypted-bytes-minus]` | decrypted bytes 4 MiB - 1 | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-decrypted-bytes-at]` | decrypted bytes exactly 4 MiB | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-decrypted-bytes-plus]` | decrypted bytes 4 MiB + 1 | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N; parse/hash zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-depth-minus]` | root-ordinal depth 63 | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-depth-at]` | root-ordinal depth 64 | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-depth-plus]` | root-ordinal depth 65 | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-nodes-minus]` | 99,999 JSON value nodes | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-nodes-at]` | 100,000 JSON value nodes | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-nodes-plus]` | 100,001 JSON value nodes | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-members-minus]` | 9,999 object members | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-members-at]` | 10,000 object members | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-members-plus]` | 10,001 object members | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-items-minus]` | 9,999 array items | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-items-at]` | 10,000 array items | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-items-plus]` | 10,001 array items | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-string-bytes-minus]` | string UTF-8 bytes 262,143 | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-string-bytes-at]` | string UTF-8 bytes 262,144 | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-string-bytes-plus]` | string UTF-8 bytes 262,145 | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-codepoints-minus]` | string code points 262,143 | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-codepoints-at]` | string code points 262,144 | admitted to strict semantic validation; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_strict_resource_boundaries_are_exact[P60-J04-codepoints-plus]` | string code points 262,145 | `RESOURCE_LIMIT_REJECTED -> REJECTED_EFFECT0`; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_directory_durability_evidence_is_closed[P60-S16-a]` | exact retained directory handle and fully matching evidence | private `DURABLE`; `D=Z`; HB/SB N/N; verifier PASS |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_directory_durability_evidence_is_closed[P60-S16-b]` | evidence hash, version, implementation, or build mismatch before effect | `DIRECTORY_DURABILITY_NOT_CONFIRMED -> DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_directory_durability_evidence_is_closed[P60-S16-c]` | boolean/classification inconsistency before effect | `DIRECTORY_DURABILITY_NOT_CONFIRMED -> DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_directory_durability_evidence_is_closed[P60-S16-d]` | directory identity, security, or namespace mismatch before effect | `DIRECTORY_DURABILITY_NOT_CONFIRMED -> DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB U/N |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_directory_durability_evidence_is_closed[P60-S16-e]` | native unavailable/failure after revision namespace effect | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,1,0,0,0)`; HB/SB A/N; orphan preserved |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_directory_durability_evidence_is_closed[P60-S16-f]` | phase-3 fixture; evidence mismatch after claim namespace effect | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,1,0,0,0,0,0,0,-1,0,0,0)`; HB/SB A/N; recovery only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-a0-create-rejected]` | initial lock CREATE_NEW rejected before namespace effect | `DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB U/N; operation entry zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-a1-namespace]` | initial lock namespace visible before file flush | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB U/N; lock preserved, fresh classify only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-a2-file-flush]` | initial lock file flush fails after namespace effect | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB U/N; lock preserved, fresh classify only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-a3-directory-durability]` | initial lock file flushed; parent durability fails | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB U/N; lock preserved, fresh classify only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-a4-reopen]` | initial lock durable; no-follow reopen fails | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB U/N; lock preserved, operation entry zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-a5-readback]` | initial lock durable; exact readback fails | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB U/N; lock preserved, operation entry zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-a6-close]` | initial lock durable; handle close result is ambiguous | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB U/N; lock preserved, operation entry zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-a7-security]` | initial lock durable; post-readback security currentness fails | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB U/N; lock preserved, operation entry zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-b0-create-rejected]` | challenge CREATE_NEW rejected before namespace effect | `DEPENDENCY_NC_EFFECT0`; `D=Z`; HB/SB N/N; challenge issuance zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-b1-namespace]` | challenge namespace visible before file flush | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB N/N; challenge preserved, issuance zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-b2-file-flush]` | challenge file flush fails after namespace effect | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB N/N; challenge preserved, issuance zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-b3-directory-durability]` | challenge file flushed; parent durability fails | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB N/N; challenge preserved, issuance zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-b4-reopen]` | challenge durable; no-follow reopen fails | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB N/N; challenge preserved, decision/store effect zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-b5-readback]` | challenge durable; exact readback fails | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB N/N; challenge preserved, decision/store effect zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-b6-close]` | challenge durable; handle close result is ambiguous | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB N/N; challenge preserved, decision/store effect zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-b7-security]` | challenge durable; post-readback security currentness fails | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB N/N; challenge preserved, decision/store effect zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_initial_lock_challenge_and_close_seams_are_literal[P60-S18-c-temp-close-ambiguous]` | operation-owned temp exists in frozen fixture; close becomes ambiguous before namespace effect | `CLEANUP_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/N; foreign/current path preserved |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r0-create-rejected]` | phase 5; reservation CREATE_NEW rejected before namespace effect | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/N; `RW=1`; exact absence may be classified once |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r1-namespace]` | phase 5; reservation namespace visible before file flush | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,1,0,0,0,0,0,0,0)`; HB/SB A/N; `RW=1`; replacement mint zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r2-durability]` | phase 5; reservation flushed; parent durability fails | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,1,0,0,0,0,0,0,0)`; HB/SB A/N; `RW=1`; replacement mint zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r3a-reopen]` | phase 5; reservation durable; no-follow reopen fails | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,1,0,0,0,0,0,0,0)`; HB/SB A/N; `RW=1`; pinned reconciliation only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r3b-readback]` | phase 5; reservation durable; exact readback fails | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,1,0,0,0,0,0,0,0)`; HB/SB A/N; `RW=1`; pinned reconciliation only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r3c-close]` | phase 5; reservation durable; handle close result is ambiguous | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,1,0,0,0,0,0,0,0)`; HB/SB A/N; `RW=1`; pinned reconciliation only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r3d-security]` | phase 5; reservation durable; post-readback security currentness fails | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,1,0,0,0,0,0,0,0)`; HB/SB A/N; `RW=1`; pinned reconciliation only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r4-exact-present]` | phase 5; exact reservation already present and phase 6 absent | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)`; HB/SB A/N; `RW=1`; append phase 6 only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r5-different]` | phase 5; different reservation body or identity present | `COLLISION_STOP`; `D=Z`; HB/SB A/N; `RW=1`; preserve, session mint zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_reservation_recovery_is_literal[P60-S19-r6-ambiguous]` | phase 5; reservation lookup ambiguous | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/N; `RW=1`; preserve, session mint zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m0-create-rejected]` | phase 6; materialization CREATE_NEW rejected before namespace effect | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/N; `RW=1`; same reservation only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m1-namespace]` | phase 6; materialization namespace visible before file flush | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,1,0,0,0,0,0,0)`; HB/SB A/U; `RW=1`; replacement session zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m2-durability]` | phase 6; materialization flushed; parent durability fails | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,1,0,0,0,0,0,0)`; HB/SB A/U; `RW=1`; replacement session zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m3a-reopen]` | phase 6; materialization durable; no-follow reopen fails | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,1,0,0,0,0,0,0)`; HB/SB A/U; `RW=1`; same session recovery only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m3b-readback]` | phase 6; materialization durable; exact readback fails | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,1,0,0,0,0,0,0)`; HB/SB A/U; `RW=1`; same session recovery only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m3c-close]` | phase 6; materialization durable; handle close result is ambiguous | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,1,0,0,0,0,0,0)`; HB/SB A/U; `RW=1`; same session recovery only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m3d-security]` | phase 6; materialization durable; post-readback security currentness fails | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,1,0,0,0,0,0,0)`; HB/SB A/U; `RW=1`; same session recovery only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m4-exact-present]` | phase 6; exact materialization already present and phase 7 absent | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)`; HB/SB A/U; `RW=1`; append phase 7 only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m5-different]` | phase 6; different materialization body or identity present | `COLLISION_STOP`; `D=Z`; HB/SB A/N; `RW=1`; preserve, session return zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-m6-ambiguous]` | phase 6; materialization lookup ambiguous | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/N; `RW=1`; preserve, session return zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-zr4-repeat]` | prior `r4-exact-present` recovery-winner slot queried again | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/N; `RW=0`; classification read-only, no materialization |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-zr5-repeat]` | prior `r5-different` recovery-winner slot queried again | `COLLISION_STOP`; `D=Z`; HB/SB A/N; `RW=0`; preserve, session mint zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-zr6-repeat]` | prior `r6-ambiguous` recovery-winner slot queried again | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/N; `RW=0`; preserve, session mint zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-zm4-repeat]` | prior `m4-exact-present` recovery-winner slot queried again | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/U; `RW=0`; classification read-only, no new session |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-zm5-repeat]` | prior `m5-different` recovery-winner slot queried again | `COLLISION_STOP`; `D=Z`; HB/SB A/N; `RW=0`; preserve, session return zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_source_session_materialization_recovery_is_literal[P60-S19-zm6-repeat]` | prior `m6-ambiguous` recovery-winner slot queried again | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/N; `RW=0`; preserve, session return zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p0-create-rejected]` | phase 8; receipt CREATE_NEW rejected before namespace effect | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/U; `RW=1`; exact absence may be classified once |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p0a-wrong-coordinate]` | phase 8; recovery coordinate differs from the phase-bound contained coordinate | `COLLISION_STOP`; `D=Z`; HB/SB A/U; `RW=1`; receipt publication zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p0b-stale-absence-lease]` | phase 8; negative-lookup lease is no longer current immediately before publish | `COLLISION_STOP`; `D=Z`; HB/SB A/U; `RW=1`; receipt publication zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p0c-wrong-temp-identity]` | phase 8; current temp identity differs from the phase-bound operation-owned identity | `COLLISION_STOP`; `D=Z`; HB/SB A/U; `RW=1`; foreign/current path preserved |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p0d-cross-parent]` | phase 8; parent identity or security differs from the phase-bound commitments | `COLLISION_STOP`; `D=Z`; HB/SB A/U; `RW=1`; receipt publication zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p1-namespace]` | phase 8; receipt namespace visible before file flush | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,0,0,0,0)`; HB/SB A/U; `RW=1`; no second receipt |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p2-durability]` | phase 8; receipt flushed; parent durability fails | `DIRECTORY_DURABILITY_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,0,0,0,0)`; HB/SB A/U; `RW=1`; no second receipt |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p3a-reopen]` | phase 8; receipt durable; no-follow reopen fails | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,0,0,0,0)`; HB/SB A/U; `RW=1`; pinned reconciliation only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p3b-readback]` | phase 8; receipt durable; exact readback fails | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,0,0,0,0)`; HB/SB A/U; `RW=1`; pinned reconciliation only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p3c-close]` | phase 8; receipt durable; handle close result is ambiguous | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,0,0,0,0)`; HB/SB A/U; `RW=1`; pinned reconciliation only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p3d-security]` | phase 8; receipt durable; post-readback security currentness fails | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,0,0,0,0)`; HB/SB A/U; `RW=1`; pinned reconciliation only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p4-exact-present]` | phase 8; exact receipt already present and phase 9 absent | `COMMITTED`; `D=(0,0,0,0,0,0,0,0,0,1,0,0)`; HB/SB A/U; `RW=1`; append phase 9 only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p5-different]` | phase 8; different receipt body or identity present | `COLLISION_STOP`; `D=Z`; HB/SB A/U; `RW=1`; preserve, phase 9 zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p6-ambiguous]` | phase 8; receipt lookup ambiguous | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/U; `RW=1`; preserve, phase 9 zero |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p7-terminal-repeat]` | exact phase 9 terminal queried after recovery completion | `DUPLICATE_COMMITTED_EVENT`; `D=Z`; HB/SB A/U; `RW=0`; strictly read-only |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p8-different-repeat]` | prior `p5-different` recovery-winner slot queried again | `COLLISION_STOP`; `D=Z`; HB/SB A/U; `RW=0`; strictly read-only, foreign receipt preserved |
| `tests/test_task060_montage_preference_authority_operation.py::test_task060_completion_receipt_publication_recovery_is_literal[P60-S20-p9-ambiguous-repeat]` | prior `p6-ambiguous` recovery-winner slot queried again | `COMPLETION_UNKNOWN`; `D=Z`; HB/SB A/U; `RW=0`; strictly read-only, ambiguous receipt preserved |

## 18. Fault injection and recovery evidence

Test-only fault seams are private non-Production composition and cover:

- after challenge immutable record flush and before directory durability;
- after Human decision durable consume and before store lock;
- after lock acquisition, current snapshot, decrypt, semantic validation, temp
  create, temp write, temp flush, and prepublish revalidation;
- immediately before/after immutable revision publication and predecessor-claim
  publication;
- after each revision/claim directory durability and before/after exact chain
  readback;
- before/after source reservation and source materialization publication;
- before/after completion-receipt pending phase, receipt namespace publication,
  receipt directory durability/readback, and terminal phase commit;
- source capability `ISSUED -> IN_FLIGHT`, consumer return, exception, timeout,
  and final burn; and
- every owned-handle close/cleanup failure.

Each seam has a closed expected classification and restart rule. No fault seam
is selected from Production argv/config/receipt or caller hooks.

### 18.1 L-R2 consumer-isolation severity Gate

The coordinated L-R2 review records at least High and cannot pass if any one of
the following is true: the `P60-R06` text, executable ledger, mandatory fixture
IDs, or downstream TASK-061-B mirror omits one direction; any A/B receipt-only
port enters the TASK-069 live-session family; the TASK-069 live session enters
either receipt/currentness reader; copy/serialization/deserialization or a wrong
operation/method changes a victim slot; or the exact rejection oracle differs
from `REJECTED_EFFECT0`, `D=Z`, `RP=(U,U,U)`, and zero entry/return/consume/
forward/exposure delta. Any route that converts such a mismatch into source,
Profile, config, history, Human, activation, release, deploy, or Production
authority is Critical. Critical/High must be `0/0` on one freshly frozen tuple;
an earlier V6 review is not replayable.

## 19. Acceptance

TASK-060 corrective implementation cannot pass unless all are true:

1. Without one exact trusted Human event, promotion/rollback revision delta is
   zero and no Profile/source authority exists.
2. One event produces exactly one revision/head transition; concurrent and
   replayed calls produce no second effect.
3. PROMOTE and ROLLBACK action authorities cannot substitute for each other.
4. Production uses only the internally fixed Windows DPAPI backend and exact
   user/session/key scope.
5. PROMOTE consumes one pinned canonical TASK-029 candidate plus TASK-019
   eligibility snapshot; public mappings/hashes and reconstructed equal values
   create authority zero.
6. Outer and decrypted JSON are strict, bounded, and parsed only from the same
   pinned opened snapshots.
7. Genesis and existing transitions publish immutable revision plus deterministic
   predecessor claim no-replace; the claim is the logical opened-byte/identity/
   revision/head CAS, and no current authority file is replaced.
8. The immutable journal follows the exact ten-phase order in section 11 and
   every phase binds exact previous bytes, identity, self-hash, ordinal and
   cumulative effect counts.
9. File and directory durability plus exact post-publication readback are
   required for `COMMITTED`.
10. Unknown/foreign/preimage/temp state is preserved; unrelated overwrite and
   delete counts are exactly zero.
11. Public confirmations, history, source reads, bindings, receipts, hashes, and
   fixtures create authority zero.
12. A live source is the exact two-stage `PROFILE_SOURCE_BINDING_V2`, with
    source->seed->same-preflight bind->one projection, direct TASK-069 handoff,
    pre-entry victim-budget preservation and post-entry permanent burn.
13. No exact native DPAPI/current-store proof means Profile publication delta
    zero.
14. Errors/status/log/stdout/temp/journal expose no plaintext, ciphertext,
    path, SID, account, token, OS detail, or offending value.
15. Focused P60-H/S/C/J/P/R, Windows race/reparse/hardlink, fault/restart, and
    relevant PP-A/TASK-019/TASK-029/TASK-058 regression pass on one frozen source
    and test identity.
16. The exact frozen TASK-069 Profile-source contract fields, methods and state
    machine are bound without legacy adaptation; missing canonical
    `TASK029_PROFILE_CANDIDATE_V2` or unavailable/drifting TASK-069 keeps every
    live source/Profile effect zero.
17. Independent Tester passes; independent Critic returns Critical/High `0/0`;
    Judge returns PASS.
18. Native Production promotion/rollback remains separately Human-gated and is
    not inferred from fixture, synthetic, static, hosted, or design evidence.
19. Installed-instance authority follows only TASK-070 private pair readback ->
    TASK-063 `INSTALLATION_READBACK_V2` -> TASK-072
    `INSTALLED_INSTANCE_PROFILE_BINDING_V1`; a public TASK-063/pair projection
    has authority zero.
20. `P60-R06` executes every exact A/B/069 bidirectional forward, receipt-only/
    live-session substitution, wrong-operation/method, copy, serialize, and
    deserialize case from the closed fixture list. Each returns
    `REJECTED_EFFECT0` with the twelve-coordinate `D=Z`, `RP=(U,U,U)`, all three
    consumer budgets unchanged, and every consumer/effect delta zero.

## 20. Native QA contract

Windows-native QA requires an isolated test root and synthetic public-safe data.
It may exercise real Current User DPAPI only in the bounded test profile and
must not read or modify installed/Owner promotion data. The sole positive file
profile is approved local NTFS, same-volume long-path publication, file-ID/
volume-ID plus DACL/SID inspection, operation-owned
`CreateFileW(CREATE_NEW)` temp handles, `SetFileInformationByHandle`
(`FileRenameInfoEx`) without replace, file `FlushFileBuffers`, parent-directory
durability port success, and no-follow exact readback. Unsupported filesystem,
API, privilege, directory durability, or lease semantics is
`DEPENDENCY_NC_EFFECT0` before any namespace effect and
`COMPLETION_UNKNOWN` after a namespace effect, without emulation/fallback. It
verifies:

The internally fixed private `Task060DirectoryDurabilityPortV1` ABI is:

```text
flush_parent(
  retained_directory_handle,
  expected_directory_identity_sha256,
  expected_security_commitment_sha256,
  namespace_commitment_sha256,
) -> Task060DirectoryDurabilityEvidenceV1
```

The retained handle is the same no-follow pinned parent used for publication;
the port never reopens a pathname. The Windows implementation retains a handle
opened with `CreateFileW(OPEN_EXISTING)` using
`GENERIC_WRITE|FILE_LIST_DIRECTORY|FILE_READ_ATTRIBUTES|SYNCHRONIZE`,
share-read/write/delete,
and `FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT`; it revalidates the
handle identity/security, calls `FlushFileBuffers` on that exact handle, and
revalidates the same handle again. If this primitive or required access is not
supported, the port returns `UNSUPPORTED`; it never substitutes close-only,
path reopen, sleep, enumeration, or swallowed failure as durability. Its sealed
evidence has exactly
`contract_version`, `implementation_sha256`, `product_build_sha256`,
`directory_identity_sha256`, `security_commitment_sha256`,
`namespace_commitment_sha256`, `native_call_started`, `native_call_succeeded`,
`post_identity_matched`, `post_security_matched`, `classification`, and
`evidence_sha256`. The only positive classification is `DURABLE`, requiring all
four booleans true and exact expected digest equality. In addition,
`native_call_succeeded=true` requires `native_call_started=true`, and any false
boolean, digest mismatch, unknown/extra field, classification mismatch, or
noncanonical evidence hash invalidates the evidence. `UNSUPPORTED`,
`NATIVE_CALL_FAILED`, `IDENTITY_DRIFT`, and `SECURITY_DRIFT` are failures.
Before a namespace effect they project as `DEPENDENCY_NC_EFFECT0`; after one
they become private `DIRECTORY_DURABILITY_UNKNOWN` and public
`COMPLETION_UNKNOWN`, with preserve/recovery only. Native error values are never
public. The Production port implementation/build is internally fixed and cannot
be selected by argv/config/receipt/hook or test composition.

- DPAPI round trip under one user/session and wrong-scope rejection;
- secure existing/initial lock behavior;
- reparse/junction/symlink/hardlink and ancestor/security drift;
- same-bytes/different-file identity;
- immutable revision/predecessor-claim no-replace race classifications;
- file/directory durability failure mapping;
- foreign temp/current-target preservation;
- clock/session/backend drift and one-shot burn; and
- body/path/OS-detail-free failures.

Unavailable native UI, trusted broker, DPAPI scope, or directory durability is
`NOT_CONFIRMED`, never PASS. Test seam PASS cannot be promoted to Production
authority or Human-event proof.

## 21. Design completion receipt template

```text
task: TASK-060
unit: PROMOTION_AUTHORITY_SECURE_SOURCE_CORRECTIVE_DESIGN
design_identity: TASK060-PTD-PROMOTION-AUTHORITY-SECURE-SOURCE-V6
base: origin/main@19c37245a1444f6f3ed5f3b707eeea94e68602b0
allowed_file: docs/ai-team/tasks/TASK-060/corrective-complete-design-packet.md
sole_writer: PLATFORM_TRUST_AND_DELIVERY_DESIGN_B
task068_dependency_sha256: PENDING_R2
task070_installation_pair_readback_v2_sha256: PENDING_R1
task063_dependency_sha256: PENDING_R2
task072_installed_instance_profile_binding_v1_sha256: PENDING_R1
task029_profile_candidate_v2_sha256: PENDING_R3
task069_profile_consumer_contract_sha256: PENDING_R2
task071_human_broker_contract_sha256: PENDING_R2
review_target_range: bytes[0,163141)
review_target_sha256: 43efab15620f0280e55cdd14da5cb9547487d382fd7d6c99569c844ceea94a7a
review_target_lines: 1727
review_target_lf_count: 1727
review_target_bytes: 163141
review_manifest: docs/ai-team/tasks/TASK-061/l2-coordinated-corrective-design-review-manifest.md
review_tuple_sha256: 2429ef29d7a2c3eb484b78c026c3365f38963d03b6ab7d1f534544bb3ee23160
critic: PASS_L_R2_V7_C_H_M_L_0_0_0_0_task061_l2_r3_sol_critic
tester: PASS_L_R2_V7_C_H_M_L_0_0_0_0_task060_r4_sol_tester
judge: PASS_L_R2_V7_C_H_M_L_0_0_0_0_task060_061_v7_independent_judge
design_frozen: true
technical_prefix_frozen: true
receipt_admin_only_mutable: true
source_effect: 0
test_effect: 0
schema_effect: 0
native_effect: 0
installed_data_effect: 0
release_deploy_production_effect: 0
authority_created: false
```

This packet creates design and versioned-fixture shape only. Future source/test
mutation requires a fresh implementation start receipt, exact dependency and
main currentness, clean dedicated worktree, no active path overlap, exact
Allowed Files, and its own DEV-4 review.
