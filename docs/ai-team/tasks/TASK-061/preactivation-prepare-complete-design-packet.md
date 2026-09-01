# TASK-061-A — Preactivation Prepare Corrective Design

Status: `DESIGN_REVIEW_READY_R7 / DEV-4 / DEPENDENCY_NC / INDEPENDENT_REVIEW_PENDING_R7 / SOURCE_START0 / NATIVE0`

Design identity: `TASK061A-PTD-PREACTIVATION-PREPARE-V7`

Canonical design base: `origin/main@19c37245a1444f6f3ed5f3b707eeea94e68602b0`

Owner allocation: `2026-09-01 / Platform Trust & Delivery / Design B`

## 1. Decision

The former one-piece TASK-061 completion model is superseded. TASK-061 is split
into two acyclic completion units:

```text
TASK-061-A PREACTIVATION PREPARE
    -> enabled:false sealed preparation receipt
    -> TASK-067 and TASK-036 consumers

TASK-036 real installed E2E completion
    -> TASK-061-B FINAL CA-C
```

TASK-061-A owns corrected CA-A migration, corrected CA-B source/Profile binding,
and CA-C challenge/plan/config-candidate preparation. It never applies an
ACTIVATE transition, never consumes a real installed E2E receipt, and never
writes `enabled:true`. `TASK061_PREACTIVATION_PREPARE_RECEIPT_V2` remains a
proposed contract until a separate exact canonicalization receipt is present.
Before that gate the only public result is `CONTRACT_NOT_CANONICAL_EFFECT0`, and
receipt publication/consumer acceptance are exactly zero. After that gate, the
only positive terminal is one exact durable receipt whose constant state is
`PREACTIVATION_READY_ENABLED_FALSE` and whose authority/effect flags are false.

The existing public plans, confirmations, readbacks, readiness objects, Human
evidence, E2E readbacks, transaction receipts, self-hashes, and module sentinels
remain audit/test data. They create no migration, Profile, Human, E2E, config,
history, or activation authority.

This Design Unit changes no source, test, schema, installed bridge, Profile,
config/history, migration snapshot, SKILL, native state, Release, Deploy, or
Production state.

## 2. Fresh source-backed gap

Canonical `montage_learning_bridge_migration.py` currently:

- exposes caller-constructible `BridgeMigrationPlan` and
  `BridgeMigrationReadback` guarded only by module-global sentinels/self-hashes;
- authorizes execution with the deterministic public `plan.confirmation()`
  string;
- accepts caller-selected `security_backend` and `hook` seams;
- uses generic `exclusive_file_update_lock` on the journal path;
- rewrites one mutable journal through `AtomicJsonWriter` without opened-byte,
  physical-identity, and expected-phase CAS at every advance;
- writes the manifest through generic replacement and treats same parsed body as
  duplicate without one pinned terminal identity;
- commits staging to snapshot with `os.replace`, so an appeared target can be
  overwritten and directory no-replace is not established;
- uses deterministic temp paths and may unlink a foreign replacement;
- reads JSON with ordinary `json.loads`, allowing duplicate-key and resource
  ambiguity;
- reopens journal, manifest, source, and snapshot paths between proofs; and
- can return a public readback without a private one-use trusted Product
  operation capability.

Canonical `montage_learning_connector_activation.py` currently:

- exposes public `ConnectorSourceBindingPlan`,
  `ConnectorSourceBindingReadiness`, `HumanActivationEvidence`,
  `InstalledAdapterE2EReadback`, and transaction receipt dataclasses;
- uses module-global `_PLAN_SEAL`, `_RESULT_SEAL`, `_HUMAN_EVIDENCE_SEAL`,
  `_ADAPTER_E2E_SEAL`, and `_TRANSACTION_SEAL` as authority checks;
- lets a caller directly construct readiness and non-synthetic E2E objects with
  those accessible sentinels and recomputable hashes;
- authorizes CA-B with deterministic `plan.confirmation()`;
- exports `issue_human_activation_evidence`, accepting predictable text plus
  caller-selected ID and timestamps;
- accepts caller-selected `security_backend`, `hook`, and `now`;
- consumes public migration/source/readiness objects rather than exact durable
  private operation ports;
- imports TASK-058 Profile writers/recovery helpers directly and treats public
  source/readiness hashes as authority;
- uses generic lock/replacement for mutable activation config/history and does
  not bind the initially opened config bytes/physical identity to final CAS; and
- may infer installed E2E from public object type, boolean, seal, and hash rather
  than one executed Product operation.

Existing tests are historical regression inputs. They verify synthetic success,
logical stale checks, some DACL/path drift, crash hooks, disabled defaults,
hardlink rejection, and self-hash/schema shape. They do not close public-object
authority laundering, trusted one-shot Product tickets, strict authority JSON,
secure initial/existing lock creation, directory no-replace, complete physical
identity CAS, trusted clock/backend fixation, private capability burn, or the
TASK-061-A/TASK-061-B split.

## 3. Responsibility boundary

TASK-061-A owns:

- CA-A migration request, plan subject, exact private action ticket consumer,
  secure snapshot commit, terminal authoritative readback, and audit projection;
- CA-B binding request, separate private action ticket, dependency composition,
  TASK-069 Profile-source/currentness handshake, and exact readback;
- CA-C preactivation request, random action-specific Human challenge subject,
  immutable disabled config candidate, and preparation receipt;
- strict authority parsing for TASK-061-owned journals, manifests, receipts,
  candidates, and readbacks;
- TASK-061-specific secure operation locks, append-only phase records, directory
  no-replace port, and recovery classification when TASK-068 V1 does not own the
  required mutable/tree primitive;
- private one-use CA-A, CA-B, and preactivation capability registries;
- Production security backend/time/build composition for these operations;
- public body/path-free request/status/audit projections;
- versioned authority-false fixtures for downstream design/test work; and
- focused, negative, concurrency, crash/restart, and Windows-native QA contracts.

TASK-061-A does not own:

- generic immutable secure I/O (TASK-068);
- canonical File Bridge/privacy/Profile publication/currentness (TASK-069 and
  TASK-067);
- installer descriptor/owner pair or selected instance (TASK-063/TASK-070);
- promoted Preference source/store/Human promotion (TASK-060);
- the Windows Human broker implementation (TASK-071);
- generic Product operation-ticket or child-launch issuance (TASK-072);
- Canonical SKILL D2S source/config or adapter command authority;
- TASK-036 real installed command/E2E/correlation/Profile receipt;
- TASK-075 voice-integration producer, native runtime, or Human Gate; TASK-075
  R6 is design-only and its exact SHA-256
  `6F6F52F9294B1838C7A282EB830635743FB3F5FF5A727B3DABE119513B9DF279`
  is only a frozen TASK-036 integration-contract identity;
- TASK-061-B Human challenge consumption or final activation apply;
- TASK-058 private parser, caller revision/store/scope, dummy anchor, raw
  external root, or exact-lane internals;
- config/history `enabled:true`, emergency disable semantics, or steady-state
  SKILL config mutation;
- ordinary DEACTIVATE apply; it must use the same trusted Human boundary in a
  separately frozen final contract, while any emergency fail-closed disable is
  a distinct Product safety path and never ACTIVATE authority;
- legacy source deletion, automatic repair, cleanup/GC, or uninstall deletion;
- Timeline, Resolve, learning admission/adoption, Provider, model/runtime,
  Release, Deploy, or Production Activation.

## 4. Design and future implementation scope

This coherent Design B line may add exactly:

```text
docs/ai-team/tasks/TASK-061/preactivation-prepare-complete-design-packet.md
```

A future separately authorized TASK-061-A implementation may modify exactly:

```text
src/ai_video_production/montage_learning_bridge_migration.py
src/ai_video_production/montage_learning_connector_activation.py
src/ai_video_production/montage_learning_preactivation_operation.py
tests/test_montage_learning_bridge_migration.py
tests/test_montage_learning_connector_activation.py
tests/test_task061_montage_learning_preactivation_operation.py
schemas/montage-learning-connector-activation.schema.json
src/ai_video_production/schema_resources/montage-learning-connector-activation.schema.json
docs/ai-team/tasks/TASK-061/preactivation-prepare-complete-design-packet.md
```

The private module/test pair is mandatory and must be created as a pair because
the executable ledger in section 17 binds literal nodes in that test. The two
connector-activation schema mirrors are optional and must change together with
exact byte equality. The migration schema, `__init__.py`, security module,
`atomic.py`, another Task, shared metadata, or any directory-implied file is not
authorized by this packet.

Explicitly forbidden without a separate owner amendment:

- TASK-058, TASK-060, TASK-063, TASK-067, TASK-068, TASK-069, TASK-070,
  TASK-071, TASK-072, TASK-036, TASK-065, or SKILL source/tests;
- File Bridge, canonical admission, installer, promotion, or generic atomic
  files;
- shared current-state, task-index, roadmap, CHANGELOG, registry, workflow,
  build, installer, package, or release files;
- real legacy source, installed state, Owner data, native adapter, or config;
  and
- migration, Profile publication, ACTIVATE/DEACTIVATE apply, Release, Deploy, or
  Production Activation during design/review.

### 4.1 Coordinated L2 design packet

The L2 review/PR unit is one exact three-artifact set, not three independent
small PRs and not a physical merge of ownership:

1. `TASK-060/corrective-complete-design-packet.md` — TASK-060 producer/store/
   source/current-receipt contract;
2. `TASK-061/ca-a-b-c-limited-partition-amendment-design.md` — R3 partition,
   one-way graph, and A/B all-false authority envelope; its exact SHA-256 is
   frozen with this three-artifact review set;
3. this TASK-061-A detailed migration/binding/preactivation contract.

The final independent Critic, Tester, and Judge review the exact byte identities
of all three in one review set. Any later byte change invalidates that set. The
current artifacts remain drafts and authorize no PR. Critical/High `0/0` plus
Judge PASS transitions the exact coordinated set to a reviewed docs-only carrier;
only then may the Builder create its one docs-only Draft PR candidate. No Task
source Writer, shared metadata, TASK-069 U1 implementation, or native effect is
part of the L2 packet.

## 5. One-way completion and operation graph

Canonical completion order:

```text
TASK-068 -> {TASK-069, TASK-063}
TASK-070 PAIR_TERMINAL_V2
    -> TASK-063 INSTALLATION_READBACK_V2
    -> TASK-072 INSTALLED_INSTANCE_PROFILE_BINDING_V1
    -> {TASK-060, TASK-069, TASK-061-A}

SKILL-D2S canonical source
    -> TASK-069 closed effect-zero identity envelope

TASK-063 + TASK-072 binding -> TASK-060 independent completion receipt

{
  TASK-069 closed effect-zero identity envelope,
  TASK-060 independent completion receipt,
  TASK-063 installation readback,
  TASK-072 installed-instance binding,
  TASK-071 broker identity/currentness contract
} -> TASK-061-A

TASK-061-A proposed future public receipt
    -> separate contract-canonicalization Gate
    -> TASK-067

{
  TASK-061-A public receipt,
  TASK-063 current installed instance,
  TASK-072 BVP-owned installed-instance/Profile/broker binding,
  TASK-067 facade completion
} -> TASK-036 packaged real installed operation

TASK-036 own executed-operation receipt chain -> TASK-061-B
all canonical completion receipts -> TASK-065
```

Canonical SKILL-D2S source completion is now pinned as follows:

| Field | Exact value | Authority use |
|---|---|---|
| status | `CANONICAL_SKILL_MAIN_MERGED_ONLY` | state classification only |
| `canonical_main_head` | `1646a2e9f3f0cb0a468dd52e564093bde04f49de` | TASK-069 source input only; never direct TASK-061-A authority |
| `skill_tree_sha256` | `4c3269e00bb934edc15cd58b73eca06c8846b2ed7104e3fa8573e6441ad47dc2` | TASK-069 source input only; never direct TASK-061-A authority |
| merged PR/head | `#8` / `9f0388a0de6f8e2201c27fbfbfebb54aff6bc349` | audit metadata only |
| tree inventory | `23 files / 259890 bytes` | audit metadata only |
| source-to-main diff | `NONE` | audit metadata only |

The closed D2S source tuple is exactly
`(canonical_main_head, skill_tree_sha256)`. PR number/head, inventory counts,
source-to-main comparison, public hashes, copied config, and serialized receipts
cannot enlarge it. This tuple terminates at TASK-069; TASK-061-A never consumes,
parses, or revalidates it directly. This completion proves canonical source identity only. It does
not prove installed-copy synchronization, TASK-058 baseline, real installed E2E,
Product broker execution, Activation, Release, or Deploy. Those facets remain
independently `DEPENDENCY_NC_EFFECT0` until their own canonical receipts arrive.
The distribution default remains disabled; a copied standalone config fails
closed; operation-config-v2 is data-only; and the native broker remains owned by
TASK-072.

TASK-069 remains an independent completion Gate. Its canonical identity and
completion receipt are currently missing. TASK-061-A requires two distinct,
non-substitutable inputs: the closed TASK-069 effect-zero identity envelope and
TASK-060's own canonical completion receipt. The SKILL-D2S canonical-source tuple
above proves neither input and cannot be adapted, relabelled, passed directly to
TASK-061-A, routed directly into TASK-060, or combined with a fixture to do so.
Until both exact receipts are independently pinned and revalidated, every
TASK-061-A consumer entry is `DEPENDENCY_NC_EFFECT0`: TASK-069/TASK-060 port
calls, Profile publication, config/history changes, and downstream authority
creation are all exactly zero.

Independent dependency review treats any D2S-to-TASK-060 direct edge, direct
TASK-061-A D2S consumption, or relabelled D2S receipt as at least High. If such a
bypass can create a capability, mutate Profile/config/history, or advance a
completion state, it is Critical. C/H must be zero before this Gate can pass.

Fixture-only early route:

```text
TASK068 / TASK069 / TASK063 / TASK060 / TASK070 / TASK071 / TASK072 fixtures
TASK071 Human-broker fixture
TASK072 operation-ticket fixture
    -> TASK061A fixture adapters
    -> parser / negative / recovery / effect-zero tests only
```

Live TASK-061-A operation route:

```text
CA-A MIGRATE ticket
    -> pinned source + installed pair + security currentness
    -> secure immutable snapshot transaction
    -> private terminal migration readback capability

CA-B BIND_PROFILE ticket
    -> exact CA-A capability + TASK060 source capability
    -> TASK069 Profile source/currentness/consumer bundle
    -> per-operation pinned Profile consumption readback
    -> private CA-B terminal capability

CA-C PREPARE_ACTIVATION ticket
    -> exact CA-B terminal + disabled current-config snapshot
    -> random Human challenge reservation
    -> immutable enabled:false config candidate
    -> TASK061_PREACTIVATION_PREPARE_RECEIPT_V2
```

TASK-069 may call back one exact TASK-061 Profile-consumption port during the
same CA-B operation. This is a live handshake into an already frozen TASK-069
contract, not a Task-completion cycle. No static receipt, public hash, or later
path reopen substitutes for that port call.

An unavailable live dependency yields `DEPENDENCY_NC_EFFECT0`; it does not
convert a complete fixture into real authority. Stale dependencies require a
fresh plan and are never automatically re-executed.

## 6. Threat and Production composition

Production internally fixes and attests:

- packaged Product parent process/image/build and operation implementation;
- TASK-068 secure I/O authority instance and exact verifier versions;
- TASK-069 closed effect-zero identity envelope plus Profile/privacy/currentness
  consumer bundle identity;
- TASK-063 selected installation pair and owner/current-user scope;
- TASK-060 promoted-source live port and its independent canonical completion
  receipt, never derived from or carrying D2S authority;
- TASK-071 Human broker and trusted clock/session policy;
- TASK-072 action-ticket broker and invocation-budget registry;
- native Windows bridge security backend and attestation version;
- TASK-061 secure migration/config-candidate ports and capability registry; and
- no direct SKILL-D2S input. Only TASK-069 may bind the source tuple from section
  5 into its own closed effect-zero identity envelope; TASK-061 reads no SKILL
  path, receipt, tuple, or private parser.

TASK-069 alone owns U1a source contract compilation, U1b closed projection, and
U1c Product application composition/readiness compilation. TASK-061-A/B and
TASK-060 implement none of those compilers, models, parsers, or receipts and do
not copy their implementation into a private authority module. They consume
only the canonical owner-produced receipt identity at the edge allocated by the
graph above. U1c must enforce byte-for-byte lower-case digest equality:

```text
TASK058_BASELINE_READBACK_V2.application_gate_receipt_sha256
    == APPLICATION_COMPOSITION_V2.receipt_sha256
    == ConnectorReadinessV2.application_composition_sha256
```

All three fields denote the same sealed application-composition receipt. Missing,
malformed, uppercase, noncanonical, stale, physically substituted, or unequal
values are `DEPENDENCY_NC_EFFECT0`; TASK-061 performs no case normalization,
recomputation, relabelling, or path reopen to make them equal. In particular,
this L2 packet does not reimplement TASK-069 U1a/U1b/U1c and creates no
completion edge back from TASK-061-A to TASK-060 or TASK-069.

Production accepts none from argv, environment, config, plan, public receipt,
serialized object, dependency injection, callback, hook, monkeypatchable module
global, or caller-selected `security_backend`, clock, SID, session, path, failure
injector, or mode.

Caller-accessible Python introspection is an attack vector. Module-global
sentinels, closures, hidden constructors, and object identity cannot be the
authority boundary. Live tickets/capabilities terminate in a trusted Product or
OS-backed broker process and cross only as opaque authenticated, nonserializable
handles over a protected channel. A composition loading arbitrary caller code
inside that boundary is `PRODUCTION_INELIGIBLE_EFFECT0`.

Test composition is separate and always marks
`production_eligible=false`, `fixture_only=true`, and
`authority_created=false`. A test seam PASS is not Production attestation.

## 7. Common strict authority snapshot

Every TASK-061 authority JSON read uses the same sequence:

1. resolve one Product-owned bounded relative coordinate below a pinned root;
2. pin every ancestor and DACL/security commitment;
3. lstat/classify without following links;
4. no-follow open a non-inheritable handle;
5. require regular file, `nlink==1`, and no reparse point;
6. fstat and retain exact physical identity;
7. bounded-read raw bytes from that handle;
8. recheck handle and ancestor/security currentness;
9. strict UTF-8 decode and bounded JSON parse;
10. validate an exact closed versioned schema;
11. hash raw bytes and the canonical parsed document; and
12. retain bytes, parsed value, hashes, identity, and security in one private
    snapshot without reopening for proof.

The parser rejects at every nesting level:

- duplicate keys with equal or different values;
- NaN, Infinity, and -Infinity;
- UTF-8 BOM, invalid UTF-8, trailing non-whitespace, and any decoded control or
  NUL whether escaped or raw;
- non-built-in mappings/sequences/scalars and boolean-as-integer coercion;
- unknown fields or versions; and
- excessive bytes, depth, nodes, members, items, string UTF-8 bytes, or code
  points.

Production ceilings are caller-invariant: authority document 4 MiB, depth 64,
nodes 100,000, 10,000 members/items per container, and 262,144 UTF-8 bytes per
string plus 262,144 Unicode code points per string. All caps are inclusive and
the bounded reader reads at most `byte_cap + 1`. Root depth is one; each object
member value or array item increments depth by one. Node count includes each
JSON value exactly once but not object member names; member names still consume
both string ceilings. Members/items are counted per container. Exact
`cap - 1`, `cap`, and `cap + 1` fixtures are required for every ceiling, and no
`cap + 1` tree is canonicalized or hashed. Smaller schema-specific ceilings are
mandatory. An unbounded/rejected tree is never canonicalized, hashed, logged,
persisted, repaired, deleted, or passed to semantic code. Public failure is a
stable body-free code.

Every TASK-061 journal/manifest/receipt/challenge/candidate schema additionally
uses this exact field-class table:

| Field class | Exact admitted value |
|---|---|
| schema/message/action/phase/state | one listed ASCII enum token, 1..64 bytes |
| SHA-256 commitment | exactly 64 lower-case hexadecimal ASCII characters |
| operation/migration/profile/public ID | 1..128 ASCII bytes, regex `[a-z0-9][a-z0-9._-]{0,127}`; no path/URI colon |
| UTC audit timestamp | exactly `YYYY-MM-DDTHH:MM:SS.ffffffZ`; audit only |
| revision/ordinal/version/count/budget | built-in integer, not bool; `0..2^63-1`, with budget exactly `0|1` |
| authority/audit object | at most 96 members; no arrays unless explicitly named |
| manifest entry | at most 4096 entries; contained relative ASCII role plus 64-hex digest, never a caller path |
| fixture/dependency collection | at most 32 closed role entries; duplicates and unknown roles reject |

These limits are part of each fixture/schema digest. A generic parser PASS cannot
substitute for a schema-specific bound.

The private snapshot type is:

```text
TASK061_AUTHORITY_JSON_SNAPSHOT_V1(
  authority_role,
  coordinate_commitment,
  raw_bytes_sha256,
  canonical_document_sha256,
  byte_count,
  physical_identity_commitment,
  security_commitment,
  ancestor_commitment,
  opened_document,
  captured_clock_coordinate
)
```

## 8. Common one-shot action ticket

CA-A, CA-B, and CA-C prepare each require a distinct action ticket from the
trusted Product broker:

```text
TASK061_ACTION_TICKET_V1(
  opaque_ticket_handle,
  action=MIGRATE_LEGACY_BRIDGE|BIND_PROFILE_SOURCE|PREPARE_ACTIVATION,
  operation_identity,
  install_instance_commitment,
  installation_pair_terminal_commitment,
  plan_sha256,
  source_subject_commitment,
  expected_target_state_commitment,
  expected_revision_or_absent,
  owner_user_session_commitment,
  product_build_digest,
  backend_implementation_digest,
  issued_clock_coordinate,
  expiry_policy,
  invocation_budget=1
)
```

The caller chooses none of ticket ID, operation ID, action, issue/expiry time,
user/session, or budget. MIGRATE, BIND, and PREPARE are mutually
non-substitutable. Public `plan.confirmation()` strings are display text only.

Before durable entry, the broker matches endpoint method, action, authenticated
handle, operation vector, instance/pair, plan/source/target/revision, build,
backend, session and expiry. Wrong/cross-operation/cross-action input rejects
with the victim budget unchanged and cannot be used as a denial-of-service burn.

For MIGRATE and PREPARE, after that match the trusted executor entry atomically
consumes the action-ticket budget and changes `ISSUED -> IN_FLIGHT`. For BIND,
the action-ticket budget remains `ISSUED` through the read-only dependency
snapshot and TASK-060 move-only seed/preflight handshake; the exact TASK-072
`begin` is the BIND executor entry and atomically consumes the matched BIND
ticket plus the matched CA-A terminal, source-session, and consumer-bundle
budgets. No Profile or TASK-061 namespace effect occurs before that `begin`.
Return, rejection, exception, timeout, crash, channel close, or unknown terminal
burns every budget that actually entered. An earlier source-seed movement burns
only that source seed and is recoverable only by its original Product operation;
it does not silently consume or refund the still-unentered BIND ticket. Only an
exact terminal
same-event/body/identity readback may project `DUPLICATE`; a differing collision
is STOP.

The ledger therefore tracks six independent budgets: `TB` action ticket, `MB`
CA-A terminal, `SB` TASK-060 source session/seed, `CB` TASK-069 consumer bundle,
`PB` CA-B terminal used by PREPARE, and `HB` the Human challenge reserved by
PREPARE for a later separately authorized Production Activation operation.
TASK-061-B may verify its currentness but cannot enter or consume it. `U` means
issued and unentered, `B` means entered/burned
by the named node, `A` means already zero in the frozen fixture, and `N` means
not issued/applicable. A row never inherits one budget state from another row.

The broker also exposes an owner-only, nonserializable
`recover_in_flight(operation_binding, last_phase_binding)` ABI. It derives the
original operation key, authenticates one still-`IN_FLIGHT` journal and has one
durable recovery-winner slot. It can return the already-sealed terminal or issue
one narrowed same-operation recovery handle for the exact admitted next phase;
it never mints a ticket, changes the vector, refunds budget, or repeats an
already-committed effect. Repeated queries after classification are read-only.
Unknown/foreign/one-sided phase state is `BROKER_RECOVERY_REQUIRED` and no handle
is returned. Thus process-loss resume is possible only through the broker-owned
winner, never a public journal or fresh random ticket.

### 8.1 Closed phase schemas and self-hash preimages

TASK-061-A has no generic phase Mapping. The following field lists are complete;
every field is required, every unknown/duplicate field rejects, and every
`*_sha256_or_none` field is either one lower-case SHA-256 digest or the literal
ASCII enum `NONE`. Every `*_or_genesis` field is a digest or literal `GENESIS`,
and `*_or_absent` is a digest or literal `ABSENT`. Every phase embeds one exact
`TASK061_CUMULATIVE_EFFECTS_V2` object:

| Closed schema | Exact required fields |
|---|---|
| `TASK061_CUMULATIVE_EFFECTS_V2` | `schema_version,message_type,migration_tree_count,profile_index_count,profile_phase_count,config_count,history_count,challenge_reservation_count,ticket_consume_count,owned_namespace_count,journal_phase_count,unrelated_overwrite_count,unrelated_delete_count,effects_sha256` |
| `TASK061_CA_A_PHASE_V2` | `schema_version,message_type,operation_commitment_sha256,action,ordinal,state,previous_phase_raw_sha256_or_genesis,previous_phase_canonical_sha256_or_genesis,previous_phase_physical_identity_sha256_or_genesis,previous_phase_sha256_or_genesis,migrate_ticket_sha256,install_instance_sha256,installation_pair_terminal_sha256,plan_sha256,source_snapshot_sha256,target_state_sha256,security_currentness_sha256,staged_payload_sha256_or_none,manifest_sha256_or_none,snapshot_tree_sha256_or_none,cumulative_effects,cumulative_effects_sha256,phase_sha256` |
| `TASK061_CA_B_PHASE_V2` | `schema_version,message_type,operation_commitment_sha256,action,ordinal,state,previous_phase_raw_sha256_or_genesis,previous_phase_canonical_sha256_or_genesis,previous_phase_physical_identity_sha256_or_genesis,previous_phase_sha256_or_genesis,bind_ticket_sha256,ca_a_terminal_sha256,task063_installation_sha256,task072_binding_sha256,task060_completion_sha256,task060_source_session_sha256_or_none,task069_consumer_bundle_sha256_or_none,task069_profile_graph_sha256_or_none,profile_currentness_sha256_or_none,application_composition_sha256,backend_session_build_sha256,cumulative_effects,cumulative_effects_sha256,phase_sha256` |
| `TASK061_CA_C_PREPARE_PHASE_V2` | `schema_version,message_type,operation_commitment_sha256,action,ordinal,state,previous_phase_raw_sha256_or_genesis,previous_phase_canonical_sha256_or_genesis,previous_phase_physical_identity_sha256_or_genesis,previous_phase_sha256_or_genesis,prepare_ticket_sha256,ca_b_terminal_sha256,config_predecessor_sha256_or_genesis,config_predecessor_physical_identity_sha256_or_absent,challenge_reservation_sha256_or_none,challenge_reservation_physical_identity_sha256_or_none,config_candidate_sha256_or_none,config_candidate_coordinate_sha256_or_none,config_candidate_temp_identity_sha256_or_none,config_candidate_physical_identity_sha256_or_none,config_candidate_parent_identity_sha256_or_none,config_candidate_parent_security_sha256_or_none,config_candidate_absence_lease_sha256_or_none,preactivation_receipt_sha256_or_none,preactivation_receipt_coordinate_sha256_or_none,preactivation_receipt_temp_identity_sha256_or_none,preactivation_receipt_physical_identity_sha256_or_none,preactivation_receipt_parent_identity_sha256_or_none,preactivation_receipt_parent_security_sha256_or_none,preactivation_receipt_absence_lease_sha256_or_none,task071_broker_binding_sha256,backend_clock_session_build_sha256,cumulative_effects,cumulative_effects_sha256,phase_sha256` |
| `TASK061_PREACTIVATION_CONFIG_CANDIDATE_V2` | `schema_version,message_type,operation_commitment_sha256,install_instance_sha256,installation_pair_terminal_sha256,ca_a_terminal_sha256,ca_b_terminal_sha256,source_binding_sha256,profile_currentness_sha256,config_predecessor_sha256_or_genesis,config_predecessor_physical_identity_sha256_or_absent,expected_config_revision,challenge_reservation_sha256,requested_action,product_build_sha256,backend_contract_sha256,trusted_clock_policy_sha256,task036_required_roles_sha256,state,enabled,fixture_only,authority_created,config_write_authority,activation_authority,production_activation_authorized,candidate_sha256` |
| `TASK061_PREACTIVATION_PREPARE_RECEIPT_V2` | `schema_version,message_type,receipt_contract_sha256,receipt_contract_canonicalization_sha256,operation_commitment_sha256,install_instance_sha256,installation_pair_terminal_sha256,ca_a_terminal_sha256,ca_b_terminal_sha256,source_binding_sha256,profile_currentness_sha256,config_candidate_sha256,config_predecessor_sha256_or_genesis,expected_config_revision,challenge_reservation_sha256,task071_broker_identity_sha256,task071_broker_implementation_build_sha256,task071_operation_session_sha256,task071_evidence_raw_sha256,task071_evidence_physical_identity_sha256,task071_evidence_security_sha256,requested_action,product_build_sha256,backend_contract_sha256,trusted_clock_policy_sha256,state,enabled,config_history_mutated,activation_applied,fixture_only,real_binding,authority_created,migration_authority,profile_write_authority,human_authority,e2e_authority,config_write_authority,activation_authority,production_activation_authorized,release_authority,deploy_authority,receipt_sha256` |

Every count is a bounded non-negative built-in integer and uses the exact D
coordinate order in section 17.2. `cumulative_effects_sha256` must equal the
embedded object's `effects_sha256`; a digest without the body is invalid.

The schema constants are literal and are not implementation choices:

| Closed schema | `schema_version` | `message_type` | fixed action field |
|---|---|---|---|
| `TASK061_CUMULATIVE_EFFECTS_V2` | `2.0.0` | `BvpTask061CumulativeEffects` | not present |
| `TASK061_CA_A_PHASE_V2` | `2.0.0` | `BvpTask061CaAPhase` | `action=MIGRATE_LEGACY_BRIDGE` |
| `TASK061_CA_B_PHASE_V2` | `2.0.0` | `BvpTask061CaBPhase` | `action=BIND_PROFILE_SOURCE` |
| `TASK061_CA_C_PREPARE_PHASE_V2` | `2.0.0` | `BvpTask061CaCPreparePhase` | `action=PREPARE_ACTIVATION` |
| `TASK061_PREACTIVATION_CONFIG_CANDIDATE_V2` | `2.0.0` | `BvpMontageLearningPreactivationConfigCandidate` | `requested_action=ACTIVATE` |
| `TASK061_PREACTIVATION_PREPARE_RECEIPT_V2` | `2.0.0` | `BvpMontageLearningPreactivationPrepareReceipt` | `requested_action=ACTIVATE`; `state=PREACTIVATION_READY_ENABLED_FALSE` |

For all phase tables below, ordinal zero requires literal `GENESIS` in all four
`previous_phase_*_or_genesis` fields and every later ordinal requires the four
lower-case digests of the immediately preceding same-operation phase. `H` means
one lower-case 64-hex digest, `N` means literal `NONE`, and no other sentinel is
permitted. The `D` and `Q` values are cumulative from a fresh operation, not
added deltas. They therefore close both the parsed values and the nested effects
body at every ordinal.

| CA-A ordinal | exact `state` | staged / manifest / snapshot | cumulative `D` | exact `Q` |
|---:|---|---|---|---|
| 0 | `PREPARED` | `N/N/N` | `(0,0,0,0,0,0,1,0,1,0,0)` | `(B,N,N,N,N,N)` |
| 1 | `PAYLOAD_STAGED` | `H/N/N` | `(0,0,0,0,0,0,1,1,2,0,0)` | `(B,N,N,N,N,N)` |
| 2 | `MANIFEST_PUBLISHED` | `H/H/N` | `(0,0,0,0,0,0,1,1,3,0,0)` | `(B,N,N,N,N,N)` |
| 3 | `SNAPSHOT_COMMITTED` | `H/H/H` | `(1,0,0,0,0,0,1,0,4,0,0)` | `(B,N,N,N,N,N)` |
| 4 | `TERMINAL_READBACK_VERIFIED` | `H/H/H` | `(1,0,0,0,0,0,1,0,5,0,0)` | `(B,N,N,N,N,N)` |

| CA-B ordinal | exact `state` | source-session / bundle / graph / currentness | cumulative `D` | exact `Q` |
|---:|---|---|---|---|
| 0 | `CA_B_PREPARED` | `N/N/N/N` | `(0,0,0,0,0,0,0,0,1,0,0)` | `(U,U,U,U,N,N)` |
| 1 | `SOURCE_SEED_MOVED` | `H/N/N/N` | `(0,0,0,0,0,0,0,0,2,0,0)` | `(U,U,B,U,N,N)` |
| 2 | `PREFLIGHT_BOUND` | `H/N/N/N` | `(0,0,0,0,0,0,0,0,3,0,0)` | `(U,U,B,U,N,N)` |
| 3 | `CONSUMER_BUNDLE_BOUND` | `H/H/N/N` | `(0,0,0,0,0,0,0,0,4,0,0)` | `(U,U,B,U,N,N)` |
| 4 | `BROKER_IN_FLIGHT` | `H/H/N/N` | `(0,0,0,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` |
| 5 | `TASK061_CONSUMPTION_OBSERVED` | `H/H/H/N` | `(0,0,8,0,0,0,1,0,6,0,0)` | `(B,B,B,B,N,N)` |
| 6 | `BROKER_COMMITTED` | `H/H/H/N` | `(0,0,10,0,0,0,1,0,7,0,0)` | `(B,B,B,B,N,N)` |
| 7 | `FINAL_CURRENTNESS_VERIFIED` | `H/H/H/H` | `(0,1,10,0,0,0,1,0,8,0,0)` | `(B,B,B,B,N,N)` |
| 8 | `CA_B_TERMINAL_COMMITTED` | `H/H/H/H` | `(0,1,10,0,0,0,1,0,9,0,0)` | `(B,B,B,B,N,N)` |

For CA-C, `C` is the seven-field candidate tuple
`(sha256,coordinate,temp_identity,physical_identity,parent_identity,parent_security,absence_lease)`
and `R` is the corresponding seven-field preactivation-receipt tuple. Each
position is independently `H` or `N`; a tuple abbreviation cannot be stored.
The config predecessor commitment is either one digest plus physical identity,
or literal `GENESIS` plus `ABSENT`, and remains identical across all ordinals.

| CA-C ordinal | exact `state` | challenge sha / physical | `C` | `R` | cumulative `D` | exact `Q` |
|---:|---|---|---|---|---|---|
| 0 | `CA_C_PREPARED` | `N/N` | `N/N/N/N/N/N/N` | `N/N/N/N/N/N/N` | `(0,0,0,0,0,0,0,0,1,0,0)` | `(U,N,N,N,U,N)` |
| 1 | `PREPARE_TICKET_IN_FLIGHT` | `N/N` | `N/N/N/N/N/N/N` | `N/N/N/N/N/N/N` | `(0,0,0,0,0,0,1,0,2,0,0)` | `(B,N,N,N,B,N)` |
| 2 | `CONFIG_PREDECESSOR_LEASED` | `N/N` | `N/N/N/N/N/N/N` | `N/N/N/N/N/N/N` | `(0,0,0,0,0,0,1,0,3,0,0)` | `(B,N,N,N,B,N)` |
| 3 | `CHALLENGE_RESERVED` | `H/H` | `H/H/H/N/H/H/H` | `N/N/N/N/N/N/N` | `(0,0,0,0,0,1,1,0,4,0,0)` | `(B,N,N,N,B,U)` |
| 4 | `CONFIG_CANDIDATE_PUBLISHED` | `H/H` | `H/H/H/H/H/H/H` | `N/N/N/N/N/N/N` | `(0,0,0,0,0,1,1,1,5,0,0)` | `(B,N,N,N,B,U)` |
| 5 | `CONFIG_CANDIDATE_READBACK_VERIFIED` | `H/H` | `H/H/H/H/H/H/H` | `H/H/H/N/H/H/H` | `(0,0,0,0,0,1,1,1,6,0,0)` | `(B,N,N,N,B,U)` |
| 6 | `PREACTIVATION_RECEIPT_READBACK_VERIFIED` | `H/H` | `H/H/H/H/H/H/H` | `H/H/H/H/H/H/H` | `(0,0,0,0,0,1,1,2,7,0,0)` | `(B,N,N,N,B,U)` |
| 7 | `PREACTIVATION_TERMINAL_COMMITTED` | `H/H` | `H/H/H/H/H/H/H` | `H/H/H/H/H/H/H` | `(0,0,0,0,0,1,1,2,8,0,0)` | `(B,N,N,N,B,U)` |

Authority JSON canonicalization is RFC 8785 JCS after the strict parser and
closed-schema/type/ceiling checks. Numbers in authority documents are bounded
integers within the interoperable JCS range; floating point is forbidden. Each
terminal `phase_sha256` or `effects_sha256` is computed as:

```text
ASCII("BVP:TASK061:" + CLOSED_SCHEMA_NAME + ":" + schema_version + "\0")
|| UTF8(JCS(object with only that terminal self-hash field omitted))
```

The omitted self-hash field is absent, never empty, zero, or `null`; every other
required field and nested body remains present. Raw predecessor bytes,
canonical predecessor bytes, physical identity, and predecessor `phase_sha256`
are independently compared before accepting the next phase. Wrong domain,
exact schema/message/action constant, sentinel state, ordinal/state pair,
omission set, canonicalization, nested effect body/hash, cumulative `D`/`Q`,
fork, or gap rejects with no next-phase publication.

The candidate is scalar-only: it contains no nested object or array. Its
`candidate_sha256` uses the same domain-separated rule with exact schema name
`TASK061_PREACTIVATION_CONFIG_CANDIDATE_V2` and version `2.0.0`, omitting only
`candidate_sha256`. Its fixed values are
`state=PREACTIVATION_CANDIDATE_ENABLED_FALSE`, `enabled=false`,
`fixture_only=false`, `authority_created=false`,
`config_write_authority=false`, `activation_authority=false`, and
`production_activation_authorized=false`. These are six fixed Boolean fields.
Any `true`, numeric Boolean,
omission, `null`, or extra field rejects before temp creation or publication.

## 9. CA-A secure migration transaction

### 9.1 Secure lock and operation root

CA-A holds a dedicated persistent migration-operation lock beneath the admitted
Bridge state root. Initial mode uses CREATE_NEW/no-follow, a one-byte regular
file, `nlink==1`, no reparse, non-inheritable live handle, and lock/security
checks on that same physical handle. Existing mode no-follow opens, pins, locks,
and revalidates the same handle. A race loser performs one fresh classification,
never automatic mode retry. The lock is not deleted as cleanup.

The operation root is a contained join of one bounded broker-issued operation ID
and migration ID. Directories are exclusive-create plus immediate and
pre/post-use identity/DACL readback. An existing root resumes only when the exact
same operation/plan journal proves the allowed phase and every existing entry is
accounted for. Safe-empty inference, nonempty unknown, case collision, reparse,
foreign ownership, or mixed identity is STOP+preserve.

### 9.2 Immutable phase chain

`PREPARED` is an immutable no-replace phase record. Every later record is also
no-replace and binds exact previous phase bytes, physical identity, self-hash,
ordinal, source/target/security currentness, and operation ticket. The closed
phase order is:

```text
PREPARED
-> PAYLOAD_STAGED
-> MANIFEST_PUBLISHED
-> SNAPSHOT_COMMITTED
-> TERMINAL_READBACK_VERIFIED
```

Fork, gap, duplicate ordinal, previous-body/identity mismatch, unknown field,
or same phase with a different body is STOP. No mutable generic writer or
scan-selected latest phase exists.

### 9.3 Payload, manifest, and directory commit

Each file uses an operation-owned exclusive live temp handle, bounded copy,
content and source-identity revalidation, file flush, temp identity
revalidation, no-replace publish, directory durability, and pinned exact
readback. The manifest is canonical exact bytes and no-replace. An appeared
manifest/target is a duplicate only when the same operation phase chain binds
the exact physical identity and bytes; same bytes on another inode is collision.

Staging-to-snapshot directory commit uses a TASK-061 private native no-replace
directory port because TASK-068 V1 does not claim tree commit. The port binds
live pinned parent/staging handles, rejects an appeared target whether empty,
nonempty, identical, or different, performs the no-replace namespace commit,
requires parent directory durability, and reopens the exact committed tree for
manifest/tree/identity readback. `os.replace` is forbidden.

Source, installed pair, DACL/security, operation/ticket, phase predecessor,
staging tree, and target absence/currentness are revalidated immediately before
and after each commit seam.

### 9.4 Recovery and cleanup

Recovery accepts only the same journal/plan/operation identity through section
8's broker-owned `recover_in_flight`; an existing operation root or public phase
record alone grants resume authority zero. The one recovery winner may continue
only the exact next no-replace phase after re-pinning every source/target/
security/instance dependency and proving all earlier effects/readbacks exact.
Unknown one-sided state is never repaired, adopted, rolled back, overwritten, or
deleted. The legacy source is always retained; automatic old-data deletion is
zero.

Temp cleanup is allowed only through the still-live operation handle or after
re-proving exact operation-created name plus physical identity. Foreign
replacement, deterministic foreign temp, hardlink, reparse, unknown identity,
or ambiguous close/delete result is preserved. Published phase, manifest,
snapshot, and terminal evidence remain until a separate lifecycle policy.

## 10. CA-A authoritative terminal readback

Public `BridgeMigrationReadback`, its module seal, nested receipt, and hash are
audit evidence with `authority_created=false`.

The trusted Product reader resolves migration ID from the live operation, then
pins and strictly reads the exact terminal phase, manifest, and complete
snapshot tree below the selected TASK-063 instance. It binds terminal
phase/receipt, manifest/tree digests, opened physical identities, source/target
currentness, security backend/build, and operation plan into:

```text
TASK061_CA_A_TERMINAL_CAPABILITY_V1(
  opaque_live_handle,
  operation_identity,
  migration_id,
  plan_sha256,
  install_instance_commitment,
  installation_pair_terminal_commitment,
  source_tree_commitment,
  terminal_phase_identity_commitment,
  manifest_identity_commitment,
  snapshot_tree_identity_commitment,
  security_backend_digest,
  product_build_digest,
  issued_clock_coordinate,
  invocation_budget=1
)
```

Entry burns on return and every failure. Public/copy/replace/pickle/mapping/hash,
wrong journal/snapshot/instance/build, stale readback, or same bytes on another
physical object cannot create it.

## 11. CA-B exact Profile V2 operation

CA-B never opens a TASK-060 envelope and never exposes its live source session
to TASK-061 code. While the exact `BIND_PROFILE_SOURCE` ticket is still issued,
the trusted Product broker performs read-only dependency matching and the
move-only source preflight described below. Only TASK-072 `begin` enters the BIND
ticket and the matched subordinate budgets. The broker composes direct
producer-to-consumer transfers from:

- one live CA-A terminal capability;
- one current TASK-063 installation-pair terminal/read port;
- one TASK-060 two-stage `PROFILE_SOURCE_BINDING_V2` session transferred directly
  to TASK-069;
- one exact TASK-069 `PROFILE_CONSUMER_BUNDLE_V2` containing the canonical
  Profile-currentness port and the TASK-061 consumption port;
- one exact TASK-069 U1c owner-produced application-composition/readiness
  receipt whose three lower-case SHA-256 fields satisfy section 6 equality;
- the post-correction TASK-058 dependency admitted through TASK-069 only;
- one exact closed TASK-069 effect-zero identity envelope that may internally
  bind the section 5 D2S tuple, without exposing that tuple as TASK-061 authority;
- one separate exact TASK-060 canonical completion receipt; and
- one exact static `TASK061_PROFILE_CONSUMER_V2` corrective receipt.

Public `ConnectorSourceBindingPlan`, `ConnectorSourceBindingReadiness`,
`PromotedPreferenceSourceRead`, `ProfileSourceBinding`,
`ConnectorReadinessEvidence`, hashes, paths, mappings, caller callables, fixed
views, and private TASK-058 parser objects are audit-only.

### 11.1 Static and per-operation TASK-061 ports

`TASK061_PROFILE_CONSUMER_V2` is a sealed static corrective receipt with exactly:

```text
schema_version, message_type, consumer_source_sha256,
package_inventory_sha256, profile_terminal_contract_sha256,
fixed_path_currentness_disabled, directory_scan_currentness_disabled,
sealed_terminal_required, release_id, build_id, observed_at_utc,
expires_at_utc, fixture_only, authority_created, receipt_sha256
```

Constants are version `2.0.0`, the exact message type, all three behavior
booleans true, and fixture/authority false. It proves code/package behavior only;
it is never per-operation consumption evidence.

The private nonserializable `Task061ProfileConsumptionPortV2` is bound into the
consumer bundle before broker `begin`. Its only effect method is:

```text
consume(task061_borrow, reservation, candidate_terminal)
  -> TASK061_PROFILE_CONSUMPTION_READBACK_V2
```

The readback fields are exactly:

```text
schema_version, message_type, consumer_source_sha256, profile_subject,
profile_subject_key_sha256, profile_id, profile_version,
candidate_operation_id, candidate_terminal_sha256,
selection_reservation_sha256, subject_binding_sha256,
profile_consumer_bundle_sha256, broker_operation_binding_sha256,
installation_pair_terminal_sha256, installed_instance_id, release_id,
build_id, pinned_profile_readback_sha256, consumed, fixed_path_used,
directory_scan_used, observed_at_utc, expires_at_utc, fixture_only,
authority_created, receipt_sha256
```

Constants are version `2.0.0`, the exact message type, `consumed=true`, both
fixed-view booleans false, and fixture/authority false. The pinned readback is the
immutable candidate terminal under the exact non-current reservation. Every
subject/bundle/operation/pair/install/build/Profile coordinate must match.
`recover_consumption(authenticated_operation_binding, bundle_binding)` is
owner-only and returns only the already-sealed identical receipt or
`BROKER_RECOVERY_REQUIRED`; it never invokes `consume` or issues a port.

### 11.2 Exact source, bundle, and broker order

TASK-061-A binds the exact candidate TASK-069 V2 interface; runtime remains
dependency-N.C. until that interface is canonical. The source session is:

```text
PINNED -> SEED_MOVED -> PREFLIGHT_BOUND -> PROJECTED | BURNED_UNKNOWN
prepare_preflight -> TASK-072 preflight -> bind_preflight -> project
```

The exact `PROFILE_CONSUMER_BUNDLE_V2` audit fields are:

```text
schema_version, message_type, bundle_binding_sha256,
profile_currentness_port_binding_sha256,
task061_consumption_port_binding_sha256, task061_profile_consumer_sha256,
application_composition_receipt_sha256,
task058_baseline_application_gate_receipt_sha256,
connector_readiness_application_composition_sha256,
profile_source_binding_sha256,
subject_binding_sha256, subject_key_sha256, consumer_operation_key_sha256,
preflight_binding_sha256, pre_operation_subject_sha256,
accepted_projection_sha256, profile_selection_predecessor_sha256,
installation_pair_terminal_sha256, installed_instance_id, release_id,
build_id, single_use, fixture_only, authority_created, receipt_sha256
```

It is version `2.0.0`, single-use, fixture/authority false. The stable binding is
created before `begin` and excludes only the later broker operation. TASK-072
`begin` validates source, candidate, subject, predecessor, the exact three-way
lower-case composition digest equality already proven by TASK-069 U1c, both
ports, CA-A/install/pair/build, static correction and the exact CA-B ticket
operation before atomically entering all matched budgets. TASK-061 compares the
three sealed fields byte-for-byte and does not compile, normalize, parse, or
recreate U1c. Parent aliases have authority zero; a pre-entry mismatch preserves
every victim budget.

The positive order is exactly:

```text
TASK060 source PINNED
-> prepare_preflight(authenticated request) -> move-only seed
-> TASK072 preflight consumes seed
-> bind_preflight(exact returned preflight), no source reread
-> project frozen closed Profile V2 bytes
-> TASK069 candidate + subject + exact predecessor + bundle
-> TASK072 begin -> one promoted Profile session
-> TASK069 PREPARED -> PAYLOAD_PUBLISHED -> CANDIDATE_INTENT
   -> CANDIDATE_PUBLISHED -> CANDIDATE_READBACK -> CANDIDATE_TERMINAL
-> ProfileCurrentnessPortV2.reserve(...) -> non-current reservation
-> TASK069 CURRENTNESS_RESERVED
-> Task061ProfileConsumptionPortV2.consume(...) -> pinned readback
-> TASK069 CONSUMPTION_READBACK
-> ProfileCurrentnessPortV2.prepare(...) -> non-current prepared receipt
-> TASK069 CURRENTNESS_PREPARED
-> promoted session finish_profile(...) -> exact OPERATION/COMMITTED
-> TASK069 PRECOMMIT_TERMINAL
-> ProfileCurrentnessPortV2.finalize(...) -> PROFILE_CURRENTNESS_V2
-> TASK061_CA_B_TERMINAL_CAPABILITY_V2
```

Only `finalize` advances the global and per-ID indexes once. The broker terminal
binds prepared+consumption and fixed-zero final currentness to avoid a cycle; the
final currentness then binds that terminal. TASK-061 never calls legacy
`publish_prebuilt_advisory_profile`, `recover_current_profile`, fixed path,
directory scan, pointer, or marker in Production.

### 11.3 CA-B durable observation and recovery

TASK-061's own immutable no-replace observation phases are:

```text
0 CA_B_PREPARED
1 SOURCE_SEED_MOVED
2 PREFLIGHT_BOUND
3 CONSUMER_BUNDLE_BOUND
4 BROKER_IN_FLIGHT
5 TASK061_CONSUMPTION_OBSERVED
6 BROKER_COMMITTED
7 FINAL_CURRENTNESS_VERIFIED
8 CA_B_TERMINAL_COMMITTED
```

Each record binds exact previous bytes/identity/hash/ordinal and the relevant
external sealed terminal. It never substitutes for TASK-069 or broker state.
Response loss/process death/lost handle after seed, reserve, consume, prepare,
finish or finalize reissues no seed/preflight/begin/borrow/port/effect. Recovery
uses only TASK-072 broker recovery, `recover_consumption`, TASK-069 currentness
owner recovery, and section 8's same-operation winner. Unresolved or one-sided
state is `BROKER_RECOVERY_REQUIRED`, preserves all artifacts, and blocks CA-C.

Each CA-B row below is one exact collected pytest node. The first authenticated
owner query and repeated query both execute inside that one listed node; there
is no `[case]` alias or dynamic variant. Every row starts from a fresh operation
immediately after the named phase is durable. For ordinals 0..7, the first
query consumes the one recovery-winner slot and returns
`BROKER_RECOVERY_REQUIRED` with a narrowed handle for only `next`; the repeat
returns the same classification read-only, creates no handle, and has added
`D=Z`. No seed, preflight, bundle, begin, borrow, port, Profile effect, or phase
is reissued.

| exact pytest node | durable state | cumulative `D` | exact `Q` | `next` |
|---|---|---|---|---|
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_every_phase_crash_is_exact[A61-J07-b0]` | `CA_B_PREPARED` | `(0,0,0,0,0,0,0,0,1,0,0)` | `(U,U,U,U,N,N)` | `SOURCE_SEED_MOVED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_every_phase_crash_is_exact[A61-J07-b1]` | `SOURCE_SEED_MOVED` | `(0,0,0,0,0,0,0,0,2,0,0)` | `(U,U,B,U,N,N)` | `PREFLIGHT_BOUND` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_every_phase_crash_is_exact[A61-J07-b2]` | `PREFLIGHT_BOUND` | `(0,0,0,0,0,0,0,0,3,0,0)` | `(U,U,B,U,N,N)` | `CONSUMER_BUNDLE_BOUND` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_every_phase_crash_is_exact[A61-J07-b3]` | `CONSUMER_BUNDLE_BOUND` | `(0,0,0,0,0,0,0,0,4,0,0)` | `(U,U,B,U,N,N)` | `BROKER_IN_FLIGHT` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_every_phase_crash_is_exact[A61-J07-b4]` | `BROKER_IN_FLIGHT` | `(0,0,0,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` | TASK-069 `PREPARED` through its owner recovery only |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_every_phase_crash_is_exact[A61-J07-b5]` | `TASK061_CONSUMPTION_OBSERVED` | `(0,0,8,0,0,0,1,0,6,0,0)` | `(B,B,B,B,N,N)` | `ProfileCurrentnessPortV2.prepare`, then TASK-069 `CURRENTNESS_PREPARED` through its owner recovery only |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_every_phase_crash_is_exact[A61-J07-b6]` | `BROKER_COMMITTED` | `(0,0,10,0,0,0,1,0,7,0,0)` | `(B,B,B,B,N,N)` | `ProfileCurrentnessPortV2.finalize`, then `FINAL_CURRENTNESS_VERIFIED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_every_phase_crash_is_exact[A61-J07-b7]` | `FINAL_CURRENTNESS_VERIFIED` | `(0,1,10,0,0,0,1,0,8,0,0)` | `(B,B,B,B,N,N)` | `CA_B_TERMINAL_COMMITTED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_every_phase_crash_is_exact[A61-J07-b8]` | `CA_B_TERMINAL_COMMITTED` | `(0,1,10,0,0,0,1,0,9,0,0)` | `(B,B,B,B,N,N)` | none; `DUPLICATE_COMMITTED_EVENT`, winner delta zero |

The TASK-069 internal Profile-phase seams are a separate, literal cross-contract
matrix. Nodes p0..p7 begin after the named TASK-069 phase is durable while the
TASK-061 observation remains `BROKER_IN_FLIGHT`; p7's only next action is the
same-operation TASK-061 observation handoff that durably writes
`TASK061_CONSUMPTION_OBSERVED`. Nodes p8..p9 begin with that B5 observation
already durable. The p9 handoff may only durably write `BROKER_COMMITTED` and
cannot finalize. B6's separately listed recovery node is the only route that
may finalize and then write `FINAL_CURRENTNESS_VERIFIED`.

For p0..p6 and p8, the node calls only the TASK-069 owner recovery port for the
exact operation. For p7 and p9, the TASK-061 recovery winner first performs an
authenticated pinned readback from that owner and then writes only the named
TASK-061 observation phase. Its first authenticated query consumes exactly one
recovery-winner slot, returns `BROKER_RECOVERY_REQUIRED`, and may advance only
the listed next action. The repeat query runs inside the same node, returns the
same classification read-only, creates no handle, and adds `D=Z`. TASK-061
never recreates candidate/subject/bundle, re-enters TASK-072, or directly writes
a TASK-069 phase.

| exact pytest node | durable TASK-069 phase | cumulative `D` | exact `Q` | first outcome / only `next` |
|---|---|---|---|---|
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p0]` | `PREPARED` | `(0,0,1,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; `PAYLOAD_PUBLISHED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p1]` | `PAYLOAD_PUBLISHED` | `(0,0,2,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; `CANDIDATE_INTENT` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p2]` | `CANDIDATE_INTENT` | `(0,0,3,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; `CANDIDATE_PUBLISHED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p3]` | `CANDIDATE_PUBLISHED` | `(0,0,4,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; `CANDIDATE_READBACK` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p4]` | `CANDIDATE_READBACK` | `(0,0,5,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; `CANDIDATE_TERMINAL` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p5]` | `CANDIDATE_TERMINAL` | `(0,0,6,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; `ProfileCurrentnessPortV2.reserve` then exact `CURRENTNESS_RESERVED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p6]` | `CURRENTNESS_RESERVED` | `(0,0,7,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; `Task061ProfileConsumptionPortV2.consume` then exact `CONSUMPTION_READBACK` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p7]` | `CONSUMPTION_READBACK`, B still `BROKER_IN_FLIGHT` | `(0,0,8,0,0,0,1,0,5,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; write only `TASK061_CONSUMPTION_OBSERVED` with cumulative journal 6 |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p8]` | `CURRENTNESS_PREPARED`, B5 durable | `(0,0,9,0,0,0,1,0,6,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; promoted-session `finish_profile` then exact `PRECOMMIT_TERMINAL` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_task069_every_profile_phase_crash_is_exact[A61-J07-t069-p9]` | `PRECOMMIT_TERMINAL`, B5 durable | `(0,0,10,0,0,0,1,0,6,0,0)` | `(B,B,B,B,N,N)` | `BROKER_RECOVERY_REQUIRED`; write only `BROKER_COMMITTED` with cumulative journal 7 and Profile index 0 |

The p7 handoff result is exactly B5 with
`D=(0,0,8,0,0,0,1,0,6,0,0)`. The p9 handoff result is exactly B6 with
`D=(0,0,10,0,0,0,1,0,7,0,0)`. Only B6 recovery may invoke `finalize`; an exact
successful finalize must durably produce B7 with
`D=(0,1,10,0,0,0,1,0,8,0,0)` before any terminal phase. Response loss after
any of those three handoffs is resolved inside its listed node from the exact
durable successor; it never repeats the handoff, Profile call, or index effect.

The CA-B terminal binds operation, CA-A, selected instance/pair, TASK-060 source
revision/head/identity/session, TASK-069 source/candidate/subject/predecessor/
bundle/reservation/consumption/prepared/broker/final-currentness graph, the
exact U1c application-composition receipt and its three equal lower-case digest
fields, TASK-058 admitted through TASK-069, backend/build/session, and budget
zero. It binds neither raw SKILL input nor TASK-067, which is downstream of
TASK-061-A. It is private, one-use, and burns on every consumer return/failure.

## 12. CA-C preactivation prepare only

TASK-061-A never calls `apply_connector_activation_transaction` in Production.
It first pre-matches and durably enters one exact `PREPARE_ACTIVATION` ticket,
then prepares one immutable action subject from the live CA-B terminal and the
current disabled config snapshot. Missing, wrong, replayed, cross-action,
concurrent-loser, expired, or stale PREPARE ticket produces config/history/
challenge/candidate/receipt delta zero and leaves an unmatched victim budget
unchanged.

### 12.1 Disabled current state

The repository/installed distribution default remains `enabled:false`.
TASK-061-A strictly reads any BVP-owned current config/history through section 7
and requires disabled state. An absent state is an explicit genesis predecessor,
not a file created by read. An existing state binds opened bytes, physical
identity, revision, history head, source binding, instance/pair, DACL/security,
and ancestor currentness.

An existing enabled state, ambiguous JSON, identity swap, different instance,
stale binding, or unknown predecessor is STOP. TASK-061-A does not deactivate,
repair, rewrite, or delete it.

The predecessor remains protected through receipt linearization by one native
`TASK061_CONFIG_PREDECESSOR_LEASE_V1`. Existing mode keeps the same no-follow
target handle open with write/delete sharing denied and re-reads exact bytes/
identity/security from that handle immediately before candidate and receipt
commit. Genesis mode holds a pinned parent directory change/oplock plus an exact
negative-lookup reservation for the current-config coordinate. Any in-place
write, rename/delete, create, ancestor/DACL/backend change, or lease break is
observed before receipt publication and becomes STOP/BURN; no weaker stat loop is
allowed. The immutable candidate and receipt are published while this lease and
the secure TASK-061 operation lock remain live. If the supported native lease is
unavailable, the positive route is `DEPENDENCY_NC_EFFECT0`.

### 12.2 Random Human challenge

The trusted Product/broker issues at least 256 random bits and creates:

```text
TASK061_ACTIVATION_CHALLENGE_V2(
  opaque_challenge_handle,
  random_nonce_commitment,
  requested_action=ACTIVATE,
  install_instance_commitment,
  installation_pair_terminal_commitment,
  ca_a_terminal_commitment,
  ca_b_terminal_commitment,
  source_binding_commitment,
  operation_plan_sha256,
  expected_config_revision,
  expected_history_head_or_genesis,
  expected_config_identity_or_absent,
  product_build_digest,
  backend_implementation_digest,
  owner_user_session_commitment,
  issued_clock_coordinate,
  expiry_policy,
  invocation_budget=1
)
```

The caller chooses none of action, nonce, challenge/operation ID, time, expiry,
session, or evidence ID. This preactivation route is ACTIVATE-only; a DEACTIVATE
request cannot reuse it. Predictable confirmation text, a public dataclass,
self-hash, module sentinel, raw string, deserialization, or copied mapping cannot
mint the challenge or later Human decision. Only the trusted Human-visible
TASK-071 boundary may confirm it. The challenge is issued but not consumed by
TASK-061-A or TASK-061-B. B may verify that the same reservation remains current
after TASK-036 completion; only a later separately authorized Production
Activation operation may enter/consume it under its fresh Human Gate.

### 12.3 Separate receipt-contract canonicalization Gate

TASK-061-A cannot self-canonicalize its proposed public receipt. A separately
owned canonical contract operation must first publish one strict immutable:

```text
TASK061_PREACTIVATION_RECEIPT_CONTRACT_CANONICALIZATION_V1(
  schema_version=1.0.0,
  message_type=BvpMontageLearningPreactivationReceiptContractCanonicalization,
  receipt_contract_sha256,
  trusted_producer_abi_sha256,
  schema_file_sha256,
  schema_resource_sha256,
  allowed_consumer_set_sha256,
  canonical_owner_build_sha256,
  canonicalized_at_utc,
  authority_created=false,
  migration_authority=false,
  profile_write_authority=false,
  human_authority=false,
  e2e_authority=false,
  config_write_authority=false,
  activation_authority=false,
  production_activation_authorized=false,
  release_authority=false,
  deploy_authority=false,
  receipt_sha256
)
```

All fields are required and unknown/duplicate fields reject. The consumer set
is the exact closed `{TASK-067,TASK-036}` set; it grants no TASK-061 effect and
no activation authority. TASK-061-A obtains it only through:

```text
read_preactivation_receipt_contract_currentness(
  admitted_prepare_operation_binding,
) -> Task061PreactivationReceiptContractCurrentnessPortV1
```

The trusted port pins and strictly reads the exact canonical-owner artifact,
binds its opened bytes and physical/security identity, proves the two schema
mirrors and trusted-producer ABI are the exact reviewed contract, verifies the
canonical owner/build/currentness, and returns no path, mapping, callable, or
write capability. Missing, stale, wrong producer, wrong contract, wrong schema
mirror, wrong consumer set, copied/rehashed body, or same bytes at another inode
returns `CONTRACT_NOT_CANONICAL_EFFECT0`; PREPARE ticket entry, challenge,
candidate, phase, receipt, and consumer-call deltas are all zero. This packet
does not allocate or mutate the separate canonical owner/shared metadata.

### 12.4 Immutable config candidate and receipt

After the exact V2 receipt contract and trusted-producer ABI have a separate
canonicalization receipt, TASK-061-A may publish an operation-specific immutable
config candidate no-replace
under TASK-068. Its constant state is `enabled:false`; it binds the exact
disabled predecessor, CA-A/CA-B terminals, challenge reservation, instance/pair,
plan, source/Profile currentness, backend/build/session/clock policy, and the
future TASK-036 receipt roles. It is not the steady-state connector config and
is never discovered by the SKILL adapter.

The candidate is exactly the closed
`TASK061_PREACTIVATION_CONFIG_CANDIDATE_V2` schema in section 8.1. Every digest
is 64 lower-case hexadecimal, `expected_config_revision` is a non-Boolean
built-in integer in `0..2^63-1`, and every enum/fixed Boolean is literal. The
`task036_required_roles_sha256` binds the separately canonicalized closed role
set; it is not a caller list. No shorter mapping, nested extension, public
dataclass, reserialization, or equal-values body is equivalent. The exact
role set includes the TASK-075 R6 design identity above plus distinct future
producer, native-runtime, and Human-Gate receipt roles. The design identity does
not satisfy any of those three roles; missing current non-fixture evidence keeps
TASK-036/TASK-061-B dependency N.C. and cannot be normalized to PASS by A.
The exact
candidate bytes, contained coordinate, operation-owned temp identity, expected
target absence lease, parent identity, and parent security are committed in
phase 3 before namespace publication. Phase 4 additionally commits the target
physical identity, which must equal the held temp identity after no-replace.

After file and directory durability plus pinned exact readback, TASK-061-A
publishes one immutable no-replace completion receipt. With no exact
canonicalization receipt, this step is not entered and returns
`CONTRACT_NOT_CANONICAL_EFFECT0`:

```text
TASK061_PREACTIVATION_PREPARE_RECEIPT_V2(
  schema_version=2.0.0,
  message_type=BvpMontageLearningPreactivationPrepareReceipt,
  receipt_contract_sha256,
  receipt_contract_canonicalization_sha256,
  operation_commitment_sha256,
  install_instance_sha256,
  installation_pair_terminal_sha256,
  ca_a_terminal_sha256,
  ca_b_terminal_sha256,
  source_binding_sha256,
  profile_currentness_sha256,
  config_candidate_sha256,
  config_predecessor_sha256_or_genesis,
  expected_config_revision,
  challenge_reservation_sha256,
  task071_broker_identity_sha256,
  task071_broker_implementation_build_sha256,
  task071_operation_session_sha256,
  task071_evidence_raw_sha256,
  task071_evidence_physical_identity_sha256,
  task071_evidence_security_sha256,
  requested_action=ACTIVATE,
  product_build_sha256,
  backend_contract_sha256,
  trusted_clock_policy_sha256,
  state=PREACTIVATION_READY_ENABLED_FALSE,
  enabled=false,
  config_history_mutated=false,
  activation_applied=false,
  fixture_only=false,
  real_binding=true,
  authority_created=false,
  migration_authority=false,
  profile_write_authority=false,
  human_authority=false,
  e2e_authority=false,
  config_write_authority=false,
  activation_authority=false,
  production_activation_authorized=false,
  release_authority=false,
  deploy_authority=false,
  receipt_sha256
)
```

`TASK061_PREACTIVATION_PREPARE_RECEIPT_V2.receipt_sha256` is the lower-case
SHA-256 of
`ASCII("BVP:TASK061:TASK061_PREACTIVATION_PREPARE_RECEIPT_V2:2.0.0\0") ||
UTF8(JCS(receipt with only receipt_sha256 omitted))`. The canonicalization
receipt uses the same rule with its own exact closed schema name and version
`TASK061_PREACTIVATION_RECEIPT_CONTRACT_CANONICALIZATION_V1:1.0.0`.
The omitted field is absent, never empty/zero/`null`; unknown fields, wrong JCS,
wrong domain/version, recursive self-hash, or any nested identity mismatch is
strict rejection before consumer or publication entry.

The full ten-field all-false tail is mandatory for this receipt and for
`TASK061_FINAL_CA_C_COMPLETION_RECEIPT_V1`; omission, `true`, wrong built-in type,
duplicate, or unknown field is strict rejection. The limited amendment's tuple
and this section together are the one closed A/B receipt contract; neither may
be implemented as a shorter payload or an authority-bearing wrapper.

The ordered tail is exactly, with no alias or default inference:

```text
authority_created=false
migration_authority=false
profile_write_authority=false
human_authority=false
e2e_authority=false
config_write_authority=false
activation_authority=false
production_activation_authorized=false
release_authority=false
deploy_authority=false
```

For A, the independently closed effect vector is exactly
`EA=(enabled,config_history_mutated,activation_applied)=(false,false,false)`.
The schema row in section 8.1, the constructor-shaped text above, the real and
fixture validators in section 15, `A61-C14`, and the coordinated amendment must
use the same field names, field count, declared order, built-in Boolean types,
and outcome. Missing/extra/duplicate fields, `null`, numeric zero, string
`"false"`, a shorter tail, or an omitted field that a caller expects to default
is `STRICT_JSON_REJECTED`; no receipt is published or accepted.

For `REJECTED_EFFECT0`, `DEPENDENCY_NC_EFFECT0`, `COLLISION_STOP`, or
`COMPLETION_UNKNOWN`, no hostile receipt body is projected as a result. The
operation's exact already-durable seam is preserved, but `EA` and the ten-field
authority tail remain all false, config/Profile/history/Human/activation and
unrelated-file deltas are zero, and every downstream TASK-067/TASK-036/
TASK-061-B consumer budget remains unchanged. An already-entered local PREPARE
ticket or recovery-winner budget may remain burned exactly as its seam ledger
states; it is not a downstream consumer budget and is never refunded or
forwarded.

The public receipt is durable audit/dependency evidence, not an activation
capability. Only after the separate contract canonicalization Gate may TASK-067
and TASK-036 use it as a pinned dependency input. Later TASK-061-B must re-read
all durable state and consume a fresh private capability; it cannot activate
from receipt bytes alone.

The six TASK-071 fields are copied only from the same pinned broker-evidence
snapshot that the prepare operation used. Together they bind broker identity,
implementation/build, exact operation/session, opened raw bytes, physical
identity, and security currentness. Omitting one, sourcing fields from different
opens, reserializing public evidence, or finding different TASK-071 currentness
at final candidate/receipt readback is `DEPENDENCY_NC_EFFECT0` before namespace
effect or `COMPLETION_UNKNOWN` after one; config/history remain unchanged.

TASK-061-A owns one B-consumer-only currentness reader:

```text
read_preactivation_currentness_for_task061b(
  admitted_task061b_operation_binding,
) -> Task061APreactivationCurrentnessPortV2
```

The producer pins and strictly reads the exact phase-7 terminal, public receipt,
config candidate, challenge reservation, CA-A/CA-B terminals, disabled
predecessor, TASK-063/TASK-072 instance binding, TASK-060/TASK-069 source/Profile
currentness, all six TASK-071 commitments, backend/build, clock policy, and
owner/session currentness in one B-bound private snapshot. The sealed port binds
the admitted B operation/plan/action, every opened raw/canonical hash, physical
and security identity, expected config revision/history head, expiry/boot
coordinate, producer implementation/build, and invocation budget one. It
returns no path, mapping, challenge secret, source bytes, backend, or callable.

Its durable producer slot is `UNENTERED -> IN_FLIGHT -> SPENT` on exact return,
or `UNENTERED -> IN_FLIGHT -> BURNED_UNKNOWN` on exception, timeout, crash, or
response loss. Double/concurrent loser, replay, wrong operation/method, A-port
forward, copy, serialization, deserialization, subclass, duck type, and public
receipt construction return zero ports without entering the matched victim.
An entered unknown slot may be reconciled only read-only from the exact phase-7
terminal and never mints a replacement port. Consumption of TASK-061-A
currentness by TASK-067, TASK-036, and TASK-061-B uses three distinct
producer-owned slots; no consumer forwards or reuses another consumer's port.

TASK-061-A uses this closed no-replace phase order:

```text
0 CA_C_PREPARED
1 PREPARE_TICKET_IN_FLIGHT
2 CONFIG_PREDECESSOR_LEASED
3 CHALLENGE_RESERVED
4 CONFIG_CANDIDATE_PUBLISHED
5 CONFIG_CANDIDATE_READBACK_VERIFIED
6 PREACTIVATION_RECEIPT_READBACK_VERIFIED
7 PREACTIVATION_TERMINAL_COMMITTED
```

The positive linearization order is literal: reservation at phase 3;
operation-owned candidate materialization plus pinned readback at phases 4-5;
completion-receipt no-replace publication, file flush, parent-directory
durability, pinned no-follow exact readback, close, and security currentness
before phase 6; then and only then the phase-7 terminal. Phase 7 performs no
candidate, receipt, config, history, Human, activation, consumer-port, or other
authority write. A terminal record can report only the already-proven phase-6
identity/body and all-false receipt state.

Every phase binds exact previous canonical bytes/identity/hash/ordinal, ticket,
CA-B terminal, predecessor lease/snapshot or genesis reservation, challenge,
candidate/receipt identities, backend/clock/session/build and cumulative effect
counts. Challenge reservation is one effect but not Human consumption; config
and history deltas remain zero throughout. Candidate/receipt are operation-owned
immutable files and never replace current config/history.

Immediately before candidate or receipt publication, the operation revalidates
the corresponding contained coordinate, exact held temp identity, current
absence lease, parent physical identity, parent security, backend/session/build,
and every dependency used to build the bytes. No-replace may use only that held
temp. Immediately after publication, the target must reopen no-follow with the
same temp/target physical identity and exact canonical bytes before the next
phase. A wrong coordinate, stale absence lease, foreign temp, parent drift,
security drift, or same bytes at another identity is never repaired, replaced,
or deleted.

A crash before `CHALLENGE_RESERVED` burns the PREPARE ticket with candidate/
receipt zero. After challenge reservation, no new challenge is issued. After
candidate publication, owner recovery may only pinned-return the identical
candidate and append the exact missing later observation/terminal through the
section 8 recovery winner. Any response loss, predecessor-lease loss, one-sided
phase, changed identity/body, or durability ambiguity is
`BROKER_RECOVERY_REQUIRED|COMPLETION_UNKNOWN`; it never publishes a second
candidate/receipt or reports ready. Exact terminal readback alone permits a
repeatable read-only duplicate with every transition/effect count zero.

Each CA-C row below is one exact collected pytest node. Both the first
authenticated query and repeated query execute inside that one listed node;
there is no `[case]` alias or dynamic variant. Every row starts immediately
after the named phase is durable and separately asserts candidate/receipt
target bytes and identities. For ordinals 0..6, the first query consumes the
same-operation recovery-winner slot and returns `BROKER_RECOVERY_REQUIRED` with
only the listed `next`; the repeat is read-only with added `D=Z`, winner delta
zero, and no ticket, challenge, temp, candidate, or receipt reissue. Ordinal 7
returns only the exact duplicate.

| exact pytest node | durable state | cumulative `D` | exact `Q` | `next` |
|---|---|---|---|---|
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_c_every_phase_crash_is_exact[A61-J07-c0]` | `CA_C_PREPARED` | `(0,0,0,0,0,0,0,0,1,0,0)` | `(U,N,N,N,U,N)` | `PREPARE_TICKET_IN_FLIGHT` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_c_every_phase_crash_is_exact[A61-J07-c1]` | `PREPARE_TICKET_IN_FLIGHT` | `(0,0,0,0,0,0,1,0,2,0,0)` | `(B,N,N,N,B,N)` | `CONFIG_PREDECESSOR_LEASED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_c_every_phase_crash_is_exact[A61-J07-c2]` | `CONFIG_PREDECESSOR_LEASED` | `(0,0,0,0,0,0,1,0,3,0,0)` | `(B,N,N,N,B,N)` | `CHALLENGE_RESERVED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_c_every_phase_crash_is_exact[A61-J07-c3]` | `CHALLENGE_RESERVED` | `(0,0,0,0,0,1,1,0,4,0,0)` | `(B,N,N,N,B,U)` | `CONFIG_CANDIDATE_PUBLISHED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_c_every_phase_crash_is_exact[A61-J07-c4]` | `CONFIG_CANDIDATE_PUBLISHED` | `(0,0,0,0,0,1,1,1,5,0,0)` | `(B,N,N,N,B,U)` | `CONFIG_CANDIDATE_READBACK_VERIFIED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_c_every_phase_crash_is_exact[A61-J07-c5]` | `CONFIG_CANDIDATE_READBACK_VERIFIED` | `(0,0,0,0,0,1,1,1,6,0,0)` | `(B,N,N,N,B,U)` | `PREACTIVATION_RECEIPT_READBACK_VERIFIED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_c_every_phase_crash_is_exact[A61-J07-c6]` | `PREACTIVATION_RECEIPT_READBACK_VERIFIED` | `(0,0,0,0,0,1,1,2,7,0,0)` | `(B,N,N,N,B,U)` | `PREACTIVATION_TERMINAL_COMMITTED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_c_every_phase_crash_is_exact[A61-J07-c7]` | `PREACTIVATION_TERMINAL_COMMITTED` | `(0,0,0,0,0,1,1,2,8,0,0)` | `(B,N,N,N,B,U)` | none; `DUPLICATE_COMMITTED_EVENT`, winner delta zero |

## 13. Trusted clock and backend currentness

Production exposes no caller `now` or test clock. Challenge issue, ticket entry,
phase commit, Profile readback, config-candidate publication, and terminal
readback use one trusted Product/OS time domain. Wall-clock rollback/forward
jump, timezone change, suspend/resume, process restart, or boot/session change
never extends expiry. A persisted boot/session/monotonic coordinate governs
eligibility; bounded UTC is audit display only. Discontinuity fails closed.

The native security backend, attestation implementation/build digest, Product
image/build, current user/owner SID, and logon session remain identical from
prepare through final readback. Fake backend, caller hook, monkeypatched
attestation, phase backend swap, or Production test clock produces effect zero
before effect; possible post-effect uncertainty becomes `COMPLETION_UNKNOWN`
with retry zero and evidence preservation.

## 14. Public boundary and capability states

Public APIs are request, prepare-status, terminal-status, and audit display only.
They expose no live ticket/challenge/capability, path, root, physical identity,
SID/session, DACL/ACE, private receipt body, raw Profile, correlation, SKILL
config, OS error, stack, cause, or context.

The existing `apply_connector_activation_transaction` is explicitly a legacy
test/audit compatibility surface until TASK-061-B replaces its Production
composition. Packaged Production routing cannot import/call it, cannot accept its
public readiness/Human/E2E objects, and returns
`PRODUCTION_AUTHORITY_REQUIRED_EFFECT0` for direct ACTIVATE or DEACTIVATE calls.
Such calls have config/history/activation/challenge delta exactly zero. This
TASK-061-A Unit does not design a replacement activation apply and does not turn
DEACTIVATE into an emergency safety authority.

Stable public outcomes:

```text
REQUEST_ACCEPTED_EFFECT0
HUMAN_DECISION_REQUIRED_EFFECT0
CONTRACT_NOT_CANONICAL_EFFECT0
DEPENDENCY_NC_EFFECT0
STALE_FRESH_PLAN_REQUIRED_EFFECT0
REJECTED_EFFECT0
COLLISION_STOP
PREACTIVATION_READY_ENABLED_FALSE
COMMITTED
DUPLICATE_COMMITTED_EVENT
COMPLETION_UNKNOWN
```

Live capability lifecycle is:

```text
ABSENT -> ISSUED -> IN_FLIGHT -> COMMITTED_BURNED
                           |----> REJECTED_BURNED
                           |----> BURNED_UNKNOWN
```

No capability has `from_dict`, pickle/reduce, public constructor, copy/replace,
hash-only validation, subclass/duck acceptance, reset, replay, or reissue.

## 15. Versioned fixture contracts

### `TASK061_CA_A_TERMINAL_FIXTURE_V1`

```text
version, fixture_id, migration_id, plan_sha256,
install_instance_sha256, terminal_phase_sha256, manifest_sha256,
snapshot_tree_sha256, fixture_only, real_binding, authority_created
```

### `TASK061_CA_B_TERMINAL_FIXTURE_V1`

```text
version, fixture_id, operation_sha256, install_instance_sha256,
ca_a_terminal_sha256, task060_source_sha256, task069_terminal_sha256,
profile_currentness_sha256, profile_readback_sha256,
fixture_only, real_binding, authority_created
```

### `TASK061_PREACTIVATION_PREPARE_FIXTURE_V2`

It uses exactly the public receipt fields in section 12.4, with
`fixture_only=true`, `real_binding=false`, `authority_created=false`,
`enabled=false`, and `activation_applied=false`.

Its effect and authority suffix is field-for-field:

```text
enabled=false
config_history_mutated=false
activation_applied=false
fixture_only=true
real_binding=false
authority_created=false
migration_authority=false
profile_write_authority=false
human_authority=false
e2e_authority=false
config_write_authority=false
activation_authority=false
production_activation_authorized=false
release_authority=false
deploy_authority=false
```

The positive validator fixture contains all fields from the section 8.1 schema
row exactly once. Each negative fixture changes exactly one listed member or one
closed-schema property; missing/extra/defaulted/reordered fixture construction,
or a fixture with a different field-list length, is not accepted as an
equivalent test oracle.

The real and fixture receipts form a closed tagged union: real is exactly
`fixture_only=false,real_binding=true,authority_created=false`; fixture is exactly
`true,false,false`. `false,false`, `true,true`, missing flags, non-bool values,
flag relabel, or a hash recomputed across another tag profile always rejects.

All fixture shapes are closed, strict, bounded, and built-in JSON only. A valid
fixture remains `FIXTURE_VALID_DEPENDENCY_NC_EFFECT0`; relabelling its flags,
copying, rehashing, or supplying every real-looking field cannot mint a live
handle.

## 16. Recovery classifications

Every operation has one total classification:

- `NOT_STARTED`: effect zero; ticket may be cancelled/burned;
- `PREPARED`: immutable reservation exists, namespace/Profile/config effect zero;
- `IN_FLIGHT_PREPUBLISH`: own live temp may be identity-bound cleaned only while
  the same recovery winner and exact handle remain live;
- `PUBLISHED_READBACK_PENDING`: a migration/Profile candidate or immutable config
  candidate may exist; no retry/rollback/delete;
- `COMMITTED`: exact terminal identity/body may project read-only duplicate;
- `BURNED_UNKNOWN`: preserve exact evidence and require owner recovery;
- `COLLISION_STOP`: preserve current and foreign state; and
- `DEPENDENCY_NC`: no live operation was created.

Recovery uses exact operation ID plus journal/phase/plan identity and section
8's authenticated broker winner. CA-B additionally requires exact TASK-072,
TASK-069 currentness-owner and TASK-061 consumption recovery; CA-C additionally
requires the still-current predecessor lease or pinned proof that the terminal
already committed before lease loss. It never scans for a winner, recreates a
source seed/preflight/borrow/port/challenge/candidate, repairs unknown one-sided
state, retries a stale receipt, deletes foreign state, or reuses an old Human
challenge. Ambiguous public status never becomes PASS.

## 17. Negative and fault matrix

Each row separately asserts migration source delta, migration snapshot delta,
Profile/currentness delta, config/history delta, challenge/ticket consumption,
temp/phase delta, unrelated overwrite/delete delta, and public leakage.

### M61-T — common action authority

- `M61-T01`: public `plan.confirmation()` authorizes migration zero;
- `M61-T02`: direct/copy/replace/pickle/mapping/rehashed plan or module seal
  access rejected;
- `M61-T03`: cross-action, wrong instance/source/plan/revision, expired, replayed,
  double, concurrent, or exception-reused ticket rejected;
- `M61-T04`: caller ticket/operation ID/time/backend/hook rejected; and
- `M61-T05`: direct public executor call outside trusted composition has
  migration/Profile/config/history delta zero; and
- `M61-T06`: wrong method/operation/vector is rejected before durable entry with
  victim budget unchanged; unknown result after matched entry burns only that
  operation.

### A61-T — CA-B/CA-C distinct ticket authority

- `A61-T01`: missing BIND ticket leaves source/Profile/phase delta zero;
- `A61-T02`: missing PREPARE ticket leaves challenge/candidate/receipt delta zero;
- `A61-T03`: MIGRATE/BIND/PREPARE cross-action substitution rejects pre-entry
  with every victim budget unchanged;
- `A61-T04`: replay/double/concurrent BIND or PREPARE has one winner and every
  loser effect zero;
- `A61-T05`: exception/timeout/channel/process loss after matched BIND/PREPARE
  entry burns the exact operation and permits only owner recovery; and
- `A61-T06`: caller ID/time/session/build/backend/expiry or a public ticket
  projection creates authority zero.

### M61-L — lock/root/namespace

- `M61-L01`: initial/existing lock race and late collision;
- `M61-L02`: lock symlink/reparse/hardlink/nlink/DACL/ancestor drift;
- `M61-L03`: ticket directory race, case collision, reparse, foreign nonempty,
  and falsely safe-empty root;
- `M61-L04`: staging/snapshot target appears empty, nonempty, identical, or
  different before directory commit; and
- `M61-L05`: unsupported native no-replace/durability semantics has no weaker
  fallback.

### M61-J — phase/manifest/publication

- `M61-J01`: PREPARED collision and same ID different plan/body;
- `M61-J02`: phase previous bytes/inode/self-hash swap, fork, gap, duplicate, or
  non-monotonic transition;
- `M61-J03`: manifest target identical/different/same-bytes-different-inode race;
- `M61-J04`: temp close/replacement, hardlink/reparse, or foreign deterministic
  temp;
- `M61-J05`: source/target/security drift immediately before/after each commit;
- `M61-J06`: file flush, phase publish, directory commit/durability, reopen,
  readback, close, or terminal failure; and
- `M61-J07`: crash after every phase has exact restart classification and no
  second namespace effect; and
- `M61-J08`: process-loss resume without the exact broker recovery winner, or a
  winner for another operation/phase, has migration delta zero.

### M61-R — authoritative readback and strict JSON

- `M61-R01`: direct/module-sealed/copied/rehashed/deserialized public
  `BridgeMigrationReadback` creates authority zero;
- `M61-R02`: journal absent/nonterminal, wrong receipt, manifest/tree tampered,
  cross-instance/build/revision, or stale terminal rejected;
- `M61-R03`: stat-open/open-read/read-post/ancestor/security swap and same bytes
  on another inode rejected;
- `M61-R04`: duplicate nested phase/revision/hash/receipt fields with equal or
  different values rejected;
- `M61-R05`: NaN/Infinity/BOM/trailing/invalid UTF-8/control/NUL/deep/wide/huge
  input rejected before canonicalization; and
- `M61-R06`: ambiguous input is preserved with repair/delete/rewrite zero and
  body-free failure.

### A61-B — CA-B dependency and source authority

- `A61-B01`: public readiness/source/Profile/migration objects, hashes, status,
  or caller true fields create authority zero;
- `A61-B02`: copied/relabelled/rehashed fixture/public durable receipts never
  mint live ports;
- `A61-B03`: missing/wrong/stale/cross-build/cross-instance TASK-063, TASK-072,
  TASK-060, TASK-069, TASK-058-through-TASK-069, or TASK-071 dependency rejects;
- `A61-B04`: same source/Profile coordinates or bytes on another physical object
  are a physical-identity mismatch and reject;
- `A61-B05`: wrong CA-A terminal, source revision/head/envelope, Profile
  predecessor/currentness/correlation, installed pair, or build rejects;
- `A61-B06`: arbitrary callable/mapping/path/fixed view substituted for a live
  consumer port has Profile delta zero;
- `A61-B07`: legacy TASK-058 private parser/raw root/exact-lane/dummy anchor or
  caller revision/store/scope use is forbidden; and
- `A61-B08`: double/concurrent/exception/crash capability reuse rejects;
- `A61-B09`: source second/mixed seed, preflight bind, project, response loss, or
  legacy V1 adaptation never creates a Profile candidate;
- `A61-B10`: bundle missing/wrong U1c application-composition receipt, unequal
  or non-lower-case three-way composition digest, static TASK-061 receipt,
  consumption port, source, predecessor, subject, pair/install/build rejects
  before broker begin and preserves every victim budget;
- `A61-B11`: method order other than
  preflight/bind/project/begin/reserve/consume/prepare/finish/finalize rejects;
- `A61-B12`: response loss/crash after reserve, consume, prepare, finish, or
  finalize reissues every method/borrow/port zero and enters owner recovery;
- `A61-B13`: `recover_consumption` returns only the identical committed receipt
  or recovery; public/wrong operation/bundle never invokes `consume`; and
- `A61-B14`: static `TASK061_PROFILE_CONSUMER_V2` cannot substitute for the
  per-operation consumption readback or final currentness.

### A61-H — challenge/clock/session

- `A61-H01`: predictable confirmation string or current public Human factory
  creates authority zero;
- `A61-H02`: copied dataclass, module sentinel, direct construction,
  deserialization, new ID, caller timestamp, or valid hash forge rejected;
- `A61-H03`: wrong action, operation, instance, source, config revision/head,
  user/session/process/backend/build rejected;
- `A61-H04`: challenge record stat-open/read-post swap, hardlink, reparse,
  ancestor/DACL drift rejected;
- `A61-H05`: expiry, caller now, wall-clock rollback/forward jump, suspend,
  restart, timezone, boot/session or phase-clock swap rejected; and
- `A61-H06`: TASK-061-A cannot consume the challenge or write an activation
  history event.

### A61-E — public readiness/Human/E2E laundering

- `A61-E01`: direct public `InstalledAdapterE2EReadback` with module sentinel,
  `synthetic_fixture=false`, and recomputed hash creates E2E authority zero;
- `A61-E02`: direct public `ConnectorSourceBindingReadiness` with module sentinel
  and recomputed hash creates CA-B authority zero;
- `A61-E03`: copy/replace/pickle/deserialization/subclass/duck/synthetic-to-false
  recreation rejected;
- `A61-E04`: status-only, synthetic, fixture, missing execution report, or public
  receipt never becomes real installed E2E; and
- `A61-E05`: TASK-061-A never accepts any E2E input or creates a final ACTIVATE
  capability; and
- `A61-E06`: direct legacy `apply_connector_activation_transaction` ACTIVATE or
  DEACTIVATE from packaged Production returns authority-required with config,
  history, challenge, and activation delta zero.

### A61-C — disabled config candidate

- `A61-C01`: current config absent-then-appears, read swap, same bytes different
  inode, ancestor/DACL/backend drift rejected;
- `A61-C02`: immutable candidate target appears identical/different or on another
  inode; only exact same-operation terminal identity is duplicate;
- `A61-C03`: operation temp/phase/candidate fsync, publish, directory durability,
  or pinned readback failure emits no prepare receipt;
- `A61-C04`: foreign temp/candidate replacement cleanup preserves foreign state;
- `A61-C05`: existing enabled, ambiguous, stale, wrong-instance, or mixed-source
  config is STOP with config/history mutation zero;
- `A61-C06`: public fixture/receipt/direct constructor/recomputed hash creates no
  live TASK-061-B capability; and
- `A61-C07`: every TASK-061-A terminal asserts `enabled=false`,
  `config_history_mutated=false`, and `activation_applied=false`;
- `A61-C08`: missing/replayed/cross-action PREPARE ticket has challenge/candidate/
  receipt delta zero;
- `A61-C09`: existing predecessor in-place write/rename/delete or genesis create
  breaks the native lease before candidate/receipt readiness;
- `A61-C10`: crash after challenge reservation reissues challenge zero;
- `A61-C11`: crash after candidate publication reissues candidate zero and only
  exact same-operation recovery may observe/finish; and
- `A61-C12`: real receipt requires `fixture_only=false,real_binding=true`; fixture
  requires `true,false`; missing/relabelled/other combinations reject;
- `A61-C13`: missing, stale, wrong-contract, wrong-producer, or same-body/
  different-identity contract-canonicalization evidence returns
  `CONTRACT_NOT_CANONICAL_EFFECT0` before PREPARE entry, with challenge,
  candidate, phase, and receipt delta zero; and
- `A61-C14`: omission, `true`, wrong built-in type, duplicate key, or unknown
  field in any mandatory all-false authority/effect member is strict rejection;
  no shorter wrapper or projection is accepted;
- `A61-C15`: missing/mixed/stale TASK-071 receipt commitments or post-namespace
  TASK-071 drift rejects without config/history mutation; and
- `A61-C16`: the B-consumer currentness reader has literal success,
  double/concurrent loser, exception/loss burn, and replay/forgery cases;
- `A61-C17`: the config candidate closed schema, constants, scalar-only body,
  fixed false fields, and self-hash preimage have literal positive/negative
  validator fixtures;
- `A61-C18`: candidate pending recovery distinguishes absent, exact
  temp-identity target, different body, different identity, ambiguous state, and
  every prepublish binding drift; and
- `A61-C19`: receipt pending recovery makes the same distinctions and never
  publishes a second receipt.

### A61-X — Production composition

- `A61-X01`: fake/injected security backend, hook, failure injector, clock, SID,
  session, coordinate, or mode in Production rejects before effect;
- `A61-X02`: backend/attestation/build/user/session changes between prepare and
  final readback fail closed or become completion unknown with retry zero;
- `A61-X03`: module introspection cannot recreate broker-backed capability; and
- `A61-X04`: same-process arbitrary extension composition is Production
  ineligible.

### 17.1 Historical V2 ledger (superseded; non-normative)

This subsection is retained only as the exact independent-review input that
caused R3. It is not an implementation, test, budget, delta, or recovery
contract. In particular its `default`, `same as`, union outcomes, family-node
aliases, and cumulative prose must not be copied into tests or completion
evidence. Section 17.2 is the sole normative R3 executable ledger.

Each row below is one exact parameterized test node. `D=(migration-tree,
Profile-index, Profile-phase, config, history, challenge-reservation,
ticket-consume, owned-namespace, journal-phase, unrelated-overwrite,
unrelated-delete)` measures additions from the named frozen seam fixture.
`Z=(0,0,0,0,0,0,0,0,0,0,0)`. `U` means victim budget remains one; `B` means
the matched budget is durably zero; `A` means it was already zero at the seam.
Unless stated otherwise: outcome `REJECTED_EFFECT0`, `D=Z`, budget `U`, fresh
plan only, body/path/OS-detail leakage zero.

Exact node syntax is `<family-node>[<vector>]`: `T_AUTH`, `M_LOCK`, `M_PHASE`,
`M_READ`, `B_PROFILE`, `H_CHAL`, `E_PUBLIC`, `C_PREP`, and `X_COMP` map to the
focused tests in section 19. Enumerated spellings inside one original bullet are
separate fixture values for that parameter. Stage-dependent variants are split
and never share an oracle.

| Vector | Frozen seam fixture | Outcome / cumulative truth and exact added delta | Budget | Recovery / restart |
|---|---|---|---|---|
| M61-T01 | before ticket match | default | U | fresh plan |
| M61-T02 | before ticket match | default | U | fresh plan |
| M61-T03.a | wrong/cross vector pre-entry | default | U | victim preserved |
| M61-T03.b | replay/double/concurrent loser | `REJECTED_EFFECT0`; `D=Z` | A | winner only |
| M61-T03.c | exception after matched entry | `BURNED_UNKNOWN`; ticket-consume one, all effects zero | B | broker recovery only |
| M61-T04 | Production composition preflight | default | U | no operation |
| M61-T05 | direct public executor | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z` | U | no operation |
| M61-T06.a | method/vector mismatch | default | U | victim unchanged |
| M61-T06.b | unknown matched entry | `BURNED_UNKNOWN`; only ticket-consume one | B | broker recovery only |
| A61-T01 | CA-B before BIND entry | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z` | U | no handoff |
| A61-T02 | CA-C before PREPARE entry | same as T01 | U | no challenge |
| A61-T03 | cross-action pre-entry | default | U | all three victims unchanged |
| A61-T04 | BIND/PREPARE concurrent loser | `REJECTED_EFFECT0`; `D=Z` | A | one winner |
| A61-T05.a | BIND matched-entry loss | `BROKER_RECOVERY_REQUIRED`; only ticket-consume one | B | same operation only |
| A61-T05.b | PREPARE matched-entry loss | same as T05.a | B | same operation only |
| A61-T06 | caller/public ticket preflight | default | U | no operation |
| M61-L01 | lock classification | `COLLISION_STOP`; `D=Z` | U | one classification |
| M61-L02 | lock security preflight | default | U | preserve lock |
| M61-L03 | operation-root classification | `COLLISION_STOP`; `D=Z` | A | preserve root |
| M61-L04 | before directory no-replace | `COLLISION_STOP`; prior staging only, added `D=Z` | A | preserve both trees |
| M61-L05 | native port eligibility | `NOT_CONFIRMED_EFFECT0`; `D=Z` | U | no weaker fallback |
| M61-J01 | PREPARED no-replace | `COLLISION_STOP`; `D=Z` | U | preserve |
| M61-J02 | phase predecessor validation | `COLLISION_STOP`; `D=Z` | A | preserve chain |
| M61-J03 | manifest no-replace/readback | `COLLISION_STOP`; `D=Z` | A | preserve target |
| M61-J04 | temp identity/cleanup | `COLLISION_STOP`; `D=Z` | A | foreign preserved |
| M61-J05 | each commit currentness gate | `BURNED_UNKNOWN`; added `D=Z` | A | recovery only |
| M61-J06.a | prepublish file flush/identity | `REJECTED_EFFECT0`; added `D=Z` | A | exact temp cleanup only |
| M61-J06.b | phase/manifest publish or durability | `COMPLETION_UNKNOWN`; named owned object/phase may be one, unrelated zero | A | exact pinned readback only |
| M61-J06.c | directory commit/durability | `COMPLETION_UNKNOWN`; snapshot namespace may be one, durable state unknown | A | no recommit |
| M61-J06.d | postpublish reopen/readback/close/terminal | `COMPLETION_UNKNOWN`; committed namespace retained, added `D=Z` | A | broker recovery only |
| M61-J07 | each exact CA-A ordinal crash fixture | cumulative state equals named ordinal; every later call delta zero | A | one recovery winner |
| M61-J08 | recovery-owner authentication | `BROKER_RECOVERY_REQUIRED`; `D=Z` | A | no resume handle |
| M61-R01 | public readback object gate | default | U | no terminal capability |
| M61-R02 | terminal graph reader | `BROKER_RECOVERY_REQUIRED`; `D=Z` | A | preserve |
| M61-R03 | pinned physical read | default | U | fresh trusted read only |
| M61-R04 | strict duplicate-key fixture | `STRICT_JSON_REJECTED`; `D=Z` | U | preserve bytes |
| M61-R05 | strict/resource fixture | `STRICT_JSON_REJECTED|RESOURCE_LIMIT_REJECTED`; `D=Z` per exact case | U | service available |
| M61-R06 | ambiguous reader | `BROKER_RECOVERY_REQUIRED`; `D=Z` | A | repair/delete zero |
| A61-B01 | public dependency gate | default | U | no CA-B |
| A61-B02 | fixture/public receipt gate | default | U | no port |
| A61-B03 | dependency digest/currentness gate | `DEPENDENCY_NC_EFFECT0`; `D=Z` | U | fresh plan |
| A61-B04 | source/Profile physical mismatch | default | U | no begin |
| A61-B05 | bundle vector mismatch | default | U | no begin |
| A61-B06 | live-port type/binding match | default | U | no begin |
| A61-B07 | forbidden dependency surface | default | U | no import/call |
| A61-B08.a | concurrent/double loser before entry | `REJECTED_EFFECT0`; `D=Z` | U/A | winner only |
| A61-B08.b | exception/crash after entry | `BROKER_RECOVERY_REQUIRED`; ticket-consume one, later calls zero | B | recovery only |
| A61-B09.a | second/mixed seed/bind/project | `REJECTED_EFFECT0`; Profile phase/index zero | A | source burned/preserved |
| A61-B09.b | preflight response loss | `BROKER_RECOVERY_REQUIRED`; seed moved, candidate/index zero | B | recover_preflight only |
| A61-B09.c | legacy V1 source | `DEPENDENCY_NC_EFFECT0`; `D=Z` | U | audit only |
| A61-B10 | bundle/U1c pre-begin missing or mismatch | default | U | every victim budget unchanged |
| A61-B11 | method-order gate | `REJECTED_EFFECT0`; no method after offending order | A | recovery/abort per broker state |
| A61-B12.a | after reserve response loss | reservation exists; Profile-index zero; every added call/effect `D=Z` | B | owner recovery only |
| A61-B12.b | after consume response loss | reservation+consumption exist; index zero; added `D=Z` | B | recover_consumption only |
| A61-B12.c | after prepare response loss | prepared exists; index zero; added `D=Z` | B | currentness recovery only |
| A61-B12.d | after broker finish response loss | broker COMMITTED exists; index zero until owner finalize; added `D=Z` | B | finalize same prepared only |
| A61-B12.e | after finalize response loss | Profile-index exactly one; added `D=Z` | B | return identical currentness |
| A61-B13 | consumption recovery authentication | `BROKER_RECOVERY_REQUIRED|identical receipt`; consume-call delta zero | A | read-only repeat |
| A61-B14 | static/per-operation distinction | default | U | no finish/finalize |
| A61-H01 | public Human factory gate | default | U | no challenge |
| A61-H02 | construction/serialization gate | default | U | no challenge |
| A61-H03 | challenge vector match | default | U | preserve reservation |
| A61-H04 | challenge physical read | default | U | preserve bytes |
| A61-H05 | trusted-clock eligibility | default | U | expired; no extension |
| A61-H06 | TASK-061-A boundary | `REJECTED_EFFECT0`; config/history/Human-consume zero | A | separate Production Activation only |
| A61-E01 | public E2E forge | default | U | no E2E authority |
| A61-E02 | public readiness forge | default | U | no CA-B authority |
| A61-E03 | public object recreation | default | U | no capability |
| A61-E04 | evidence-quality gate | `DEPENDENCY_NC_EFFECT0`; `D=Z` | U | no final apply |
| A61-E05 | TASK-061-A boundary | `REJECTED_EFFECT0`; activation/config/history zero | U | TASK-061-B only |
| A61-E06.a | legacy direct ACTIVATE | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z` | U | no apply |
| A61-E06.b | legacy direct DEACTIVATE | same as E06.a | U | no apply |
| A61-C01 | predecessor lease/currentness | `COLLISION_STOP`; `D=Z` | B/A | candidate/receipt zero |
| A61-C02 | candidate no-replace | `COLLISION_STOP|DUPLICATE_COMMITTED_EVENT`; exact operation decides; added `D=Z` | A | preserve/read-only |
| A61-C03.a | candidate temp/flush/publish/durability | `COMPLETION_UNKNOWN`; config/history zero; candidate may be one; receipt zero | A | no republish |
| A61-C03.b | candidate readback | same cumulative truth as C03.a | A | recovery only |
| A61-C03.c | receipt publish/durability/readback | `COMPLETION_UNKNOWN`; config/history zero; candidate one; receipt namespace may be one | A | no second receipt |
| A61-C04 | cleanup identity | `CLEANUP_UNKNOWN`; added `D=Z` | A | foreign preserved |
| A61-C05 | disabled predecessor semantics | `COLLISION_STOP`; `D=Z` | U | no repair/deactivate |
| A61-C06 | public receipt/capability gate | default | U | TASK-061-B handle zero |
| A61-C07 | every positive prepare terminal | `PREACTIVATION_READY_ENABLED_FALSE`; config/history zero, challenge reservation one, ticket consume one, candidate/receipt exactly one | B | read-only duplicate |
| A61-C08 | PREPARE ticket gate | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z` | U/A | no challenge |
| A61-C09 | predecessor lease break | `COLLISION_STOP`; config/history zero, receipt zero | B/A | preserve candidate if any |
| A61-C10 | after challenge reservation crash | `BROKER_RECOVERY_REQUIRED`; challenge exactly one, candidate/receipt zero | B | no challenge reissue |
| A61-C11 | after candidate publish crash | `BROKER_RECOVERY_REQUIRED`; candidate exactly one, config/history/receipt zero | B | same-operation recovery only |
| A61-C12 | receipt tag parser | `STRICT_JSON_REJECTED`; `D=Z` | U | preserve receipt bytes |
| A61-X01 | Production composition preflight | default | U | no operation |
| A61-X02.a | drift before any entered effect | `REJECTED_EFFECT0`; `D=Z` | U | fresh trusted plan |
| A61-X02.b | drift after entry, before namespace/Profile effect | `BURNED_UNKNOWN`; only exact ticket budget consumed | B | broker recovery |
| A61-X02.c-profile | drift after a CA-B Profile namespace seam | `COMPLETION_UNKNOWN`; cumulative named seam truth retained, added `D=Z` | `(A,A,A,A,N,N)` | no retry |
| A61-X02.d-candidate | drift after a PREPARE candidate namespace seam | `COMPLETION_UNKNOWN`; cumulative named seam truth retained, added `D=Z` | `(A,N,N,N,A,U)` | no retry |
| A61-X03 | capability introspection gate | default | U | no handle |
| A61-X04 | composition eligibility | `PRODUCTION_INELIGIBLE_EFFECT0`; `D=Z` | U | no Product operation |

For `M61-J06`, `M61-J07`, `A61-B12`, and `A61-C03`, the parameter ID includes
the exact phase/method suffix shown above. A fixture records cumulative truth at
that seam and asserts every post-fault transition count numerically zero; no test
may collapse namespace-visible, durable, and semantic currentness into one bool.

### 17.2 R3 normative executable ledger

This is the sole executable ledger. Every row names a literal pytest node in
the mandatory allowed test file. `D=(migration-tree, Profile-index,
Profile-phase, config, history, challenge-reservation, ticket-consume,
owned-namespace, TASK061-journal-phase, unrelated-overwrite,
unrelated-delete)` is the signed delta after that row's exact frozen fixture;
`Z=(0,0,0,0,0,0,0,0,0,0,0)`. `Q=(TB,MB,SB,CB,PB,HB)` gives the six independent
budget states defined in section 8. Every row also asserts legacy-source
preservation, body/path/OS-detail leakage zero, and no unlisted call/effect.
For the B-consumer currentness-reader rows only, `AB` records its distinct
producer slot as `U=unentered`, `B=entered and resolved/burned`, or `A=already
zero`; no other lane budget can substitute for it.

#### Primary success, duplicate, and recovery outcomes

| Exact pytest node ID | Frozen fixture | Exact outcome, D, Q, and recovery |
|---|---|---|
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_primary_success_and_duplicate_are_exact[M61-Z01-ca-a-success]` | fresh admitted MIGRATE operation before entry | `CA_A_TERMINAL_COMMITTED`; `D=(1,0,0,0,0,0,1,0,5,0,0)`; `Q=(B,N,N,N,N,N)`; one snapshot terminal |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_primary_success_and_duplicate_are_exact[M61-Z02-ca-a-duplicate]` | exact committed CA-A event/body/identities | `DUPLICATE_COMMITTED_EVENT`; `D=Z`; `Q=(A,N,N,N,N,N)`; read-only |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_primary_success_and_duplicate_are_exact[A61-Z03-ca-b-success]` | exact matched BIND operation before source preflight | `CA_B_TERMINAL_COMMITTED`; `D=(0,1,10,0,0,0,1,0,9,0,0)`; `Q=(B,B,B,B,N,N)`; Profile final index exact one |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_primary_success_and_duplicate_are_exact[A61-Z04-ca-b-duplicate]` | exact committed CA-B event/body/identities | `DUPLICATE_COMMITTED_EVENT`; `D=Z`; `Q=(A,A,A,A,N,N)`; read-only |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_primary_success_and_duplicate_are_exact[A61-Z05-prepare-success]` | exact post-canonicalization matched PREPARE operation before entry | `PREACTIVATION_READY_ENABLED_FALSE`; `D=(0,0,0,0,0,1,1,2,8,0,0)`; `Q=(B,N,N,N,B,U)`; candidate/receipt exact one each, config/history zero |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_primary_success_and_duplicate_are_exact[A61-Z06-prepare-duplicate]` | exact committed prepare event/body/identities | `DUPLICATE_COMMITTED_EVENT`; `D=Z`; `Q=(A,N,N,N,A,U)`; read-only, challenge unconsumed |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_recovery_winner_is_exact[M61-Z07-ca-a-recovery-winner]` | exact authenticated nonterminal CA-A phase, winner slot absent | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,N,N,N,N,N)`; recovery-winner delta one; only exact next phase allowed |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_recovery_winner_is_exact[A61-Z08-ca-b-recovery-winner]` | exact authenticated nonterminal CA-B phase, all entered budgets already zero | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,A,A,A,N,N)`; recovery-winner delta one; no source/begin/port reissue |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_recovery_winner_is_exact[A61-Z09-prepare-recovery-winner]` | exact authenticated nonterminal PREPARE phase | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,N,N,N,A,U)`; recovery-winner delta one; no challenge/candidate reissue |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_recovery_winner_is_exact[M61-Z10a-ca-a-repeat]` | resolved CA-A recovery-winner slot, exact same nonterminal phase still current | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,N,N,N,N,N)`; recovery-winner delta zero; read-only |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_recovery_winner_is_exact[A61-Z10b-ca-b-repeat]` | resolved CA-B recovery-winner slot, exact same nonterminal phase still current | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,A,A,A,N,N)`; recovery-winner delta zero; read-only |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_recovery_winner_is_exact[A61-Z10c-prepare-repeat]` | resolved PREPARE recovery-winner slot, exact same nonterminal phase still current | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,N,N,N,A,U)`; recovery-winner delta zero; read-only, challenge unconsumed |

#### Ticket, migration, dependency, and public-authority negatives

| Vector | Exact pytest node ID | Frozen fixture | Exact outcome, D, Q, and recovery |
|---|---|---|---|
| M61-T01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_action_ticket_authority_matrix[M61-T01]` | MIGRATE ticket issued before method match | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; fresh plan |
| M61-T02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_action_ticket_authority_matrix[M61-T02]` | MIGRATE ticket issued before public-object match | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; fresh plan |
| M61-T03-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_action_ticket_authority_matrix[M61-T03-a]` | wrong/cross/expired MIGRATE vector before entry | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; victim preserved |
| M61-T03-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_action_ticket_authority_matrix[M61-T03-b]` | replay/double/concurrent loser after winner entry | `REJECTED_EFFECT0`; `D=Z`; `Q=(A,N,N,N,N,N)`; winner only |
| M61-T03-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_action_ticket_authority_matrix[M61-T03-c]` | exception immediately after matched MIGRATE entry and PREPARED durability | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,1,0,0)`; `Q=(B,N,N,N,N,N)`; broker recovery only |
| M61-T04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_action_ticket_authority_matrix[M61-T04]` | caller-selected ticket/ID/time/backend/hook preflight | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; Product operation calls zero |
| M61-T05 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_action_ticket_authority_matrix[M61-T05]` | direct public executor outside Production composition | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; operation zero |
| M61-T06-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_action_ticket_authority_matrix[M61-T06-a]` | method/operation/vector mismatch before entry | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; victim preserved |
| M61-T06-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_action_ticket_authority_matrix[M61-T06-b]` | response unknown after matched MIGRATE entry and PREPARED durability | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,1,0,0)`; `Q=(B,N,N,N,N,N)`; broker recovery only |
| A61-T01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T01]` | BIND ticket missing; subordinate victims issued | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z`; `Q=(N,U,U,U,N,N)`; all subordinate victims preserved |
| A61-T02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T02]` | PREPARE ticket missing; CA-B victim issued | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z`; `Q=(N,N,N,N,U,N)`; no challenge |
| A61-T03-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T03-a]` | MIGRATE ticket presented to BIND | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; every victim preserved |
| A61-T03-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T03-b]` | BIND ticket presented to PREPARE | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; every victim preserved |
| A61-T03-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T03-c]` | PREPARE ticket presented to MIGRATE | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; victim preserved |
| A61-T04-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T04-a]` | BIND concurrent loser | `REJECTED_EFFECT0`; `D=Z`; `Q=(A,A,A,A,N,N)`; winner only |
| A61-T04-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T04-b]` | PREPARE concurrent loser | `REJECTED_EFFECT0`; `D=Z`; `Q=(A,N,N,N,A,U)`; winner only |
| A61-T05-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T05-a]` | loss immediately after TASK-072 BIND begin, before Profile effect | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,1,0,0)`; `Q=(B,B,B,B,N,N)`; no budget reissue |
| A61-T05-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T05-b]` | loss immediately after PREPARE entry, before challenge reservation | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,2,0,0)`; `Q=(B,N,N,N,B,N)`; no ticket/CA-B reissue |
| A61-T06 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_distinct_bind_prepare_ticket_matrix[A61-T06]` | caller/public ticket field preflight | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; no Product operation |
| M61-L01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_lock_root_and_namespace_matrix[M61-L01]` | lock initial/existing classification before entry | `COLLISION_STOP`; `D=Z`; `Q=(U,N,N,N,N,N)`; one fresh classification |
| M61-L02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_lock_root_and_namespace_matrix[M61-L02]` | lock physical/security preflight | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; lock preserved |
| M61-L03 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_lock_root_and_namespace_matrix[M61-L03]` | operation-root classification after entry | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,N,N)`; root preserved |
| M61-L04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_lock_root_and_namespace_matrix[M61-L04]` | before directory no-replace with staging fixture | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,N,N)`; both trees preserved |
| M61-L05 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_lock_root_and_namespace_matrix[M61-L05]` | native no-replace/durability eligibility before entry | `DEPENDENCY_NC_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; fallback zero |
| M61-J01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_phase_manifest_and_commit_matrix[M61-J01]` | PREPARED target collision | `COLLISION_STOP`; `D=Z`; `Q=(U,N,N,N,N,N)`; preserve |
| M61-J02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_phase_manifest_and_commit_matrix[M61-J02]` | phase predecessor validation after entry | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,N,N)`; preserve chain |
| M61-J03 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_phase_manifest_and_commit_matrix[M61-J03]` | manifest no-replace/readback after entry | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,N,N)`; target preserved |
| M61-J04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_phase_manifest_and_commit_matrix[M61-J04]` | temp identity cleanup after entry | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,N,N)`; foreign temp preserved |
| M61-J05 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_phase_manifest_and_commit_matrix[M61-J05]` | source/target/security commit currentness after entry | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,N,N,N,N,N)`; recovery only |
| M61-J06-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_phase_manifest_and_commit_matrix[M61-J06-a]` | operation-owned temp failure before namespace effect, entered fixture | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,N,N,N,N,N)`; exact owned cleanup only |
| M61-J06-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_phase_manifest_and_commit_matrix[M61-J06-b]` | immutable file/phase namespace visible before durability/readback | `COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,0,1,1,0,0)`; `Q=(A,N,N,N,N,N)`; no republish |
| M61-J06-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_phase_manifest_and_commit_matrix[M61-J06-c]` | snapshot directory namespace visible before durability/readback | `COMPLETION_UNKNOWN`; `D=(1,0,0,0,0,0,0,0,0,0,0)`; `Q=(A,N,N,N,N,N)`; no recommit |
| M61-J06-d | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_phase_manifest_and_commit_matrix[M61-J06-d]` | postpublication close/security/terminal readback failure | `COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,N,N,N,N,N)`; authenticated recovery only |
| M61-J08 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_recovery_authentication_is_exact[M61-J08]` | wrong operation/plan/phase recovery owner | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,N,N,N,N,N)`; recovery handle zero |
| M61-R01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_terminal_readback_is_authoritative[M61-R01]` | public readback object before private reader | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; capability zero |
| M61-R02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_terminal_readback_is_authoritative[M61-R02]` | nonterminal/wrong terminal graph | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,N,N,N,N,N)`; preserve |
| M61-R03 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_terminal_readback_is_authoritative[M61-R03]` | physical/currentness mismatch before capability issue | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,N,N)`; fresh trusted read |
| M61-R04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_terminal_readback_is_authoritative[M61-R04]` | strict duplicate-key input | `STRICT_JSON_REJECTED`; `D=Z`; `Q=(U,N,N,N,N,N)`; bytes preserved |
| M61-R05-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_terminal_readback_is_authoritative[M61-R05-a]` | strict malformed input | `STRICT_JSON_REJECTED`; `D=Z`; `Q=(U,N,N,N,N,N)`; service available |
| M61-R05-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_terminal_readback_is_authoritative[M61-R05-b]` | resource cap exceeded | `RESOURCE_LIMIT_REJECTED`; `D=Z`; `Q=(U,N,N,N,N,N)`; service available |
| M61-R06 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_terminal_readback_is_authoritative[M61-R06]` | ambiguous current/preimage | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,N,N,N,N,N)`; repair/delete zero |

#### CA-B, Human/E2E laundering, preactivation, and composition negatives

| Vector | Exact pytest node ID | Frozen fixture | Exact outcome, D, Q, and recovery |
|---|---|---|---|
| A61-B01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_dependency_and_source_matrix[A61-B01]` | public dependency object preflight | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; no CA-B |
| A61-B02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_dependency_and_source_matrix[A61-B02]` | fixture/copied/relabelled receipt preflight | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; port calls zero |
| A61-B03 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_dependency_and_source_matrix[A61-B03]` | canonical dependency missing/wrong/stale/cross-generation before source seed | `DEPENDENCY_NC_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; fresh plan |
| A61-B04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_dependency_and_source_matrix[A61-B04]` | source/Profile bytes or coordinates match but physical identity/currentness mismatches before source seed | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; no begin |
| A61-B05 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_dependency_and_source_matrix[A61-B05]` | CA-A/source/Profile/pair/install/build bundle vector mismatch before source seed | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; no begin |
| A61-B06 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_dependency_and_source_matrix[A61-B06]` | callable/path/mapping substituted for live port | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; port calls zero |
| A61-B07 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_dependency_and_source_matrix[A61-B07]` | forbidden TASK-058/SKILL/TASK-067/private surface | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; forbidden import/call zero |
| A61-B08-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B08-a]` | concurrent/double loser before TASK-072 begin | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; winner only |
| A61-B08-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B08-b]` | exception/crash after TASK-072 begin before Profile effect | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,1,0,0)`; `Q=(B,B,B,B,N,N)`; reissue zero |
| A61-B09-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B09-a]` | second/mixed seed/bind/project before begin | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,A,U,N,N)`; source reissue zero |
| A61-B09-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B09-b]` | source preflight response loss before begin | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(U,U,B,U,N,N)`; original source recovery only |
| A61-B09-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B09-c]` | legacy V1 source | `DEPENDENCY_NC_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; audit only |
| A61-B10 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_dependency_and_source_matrix[A61-B10]` | U1c/bundle field missing, malformed, unequal, or wrong before begin | `DEPENDENCY_NC_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; all victim budgets preserved |
| A61-B11 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B11]` | wrong method order before offending call | `REJECTED_EFFECT0`; `D=Z`; `Q=(A,A,A,A,N,N)`; later calls zero |
| A61-B12-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B12-a]` | reserve response loss | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,A,A,A,N,N)`; owner readback only |
| A61-B12-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B12-b]` | consume response loss | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,A,A,A,N,N)`; `recover_consumption` only |
| A61-B12-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B12-c]` | prepare response loss | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,A,A,A,N,N)`; currentness recovery only |
| A61-B12-d | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B12-d]` | broker-finish response loss before finalize | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,A,A,A,N,N)`; same prepared finalize only |
| A61-B12-e | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B12-e]` | finalize response loss with exact index already advanced | `DUPLICATE_COMMITTED_EVENT`; `D=Z`; `Q=(A,A,A,A,N,N)`; identical currentness only |
| A61-B13-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B13-a]` | exact consumption recovery authentication | identical consumption receipt; `D=Z`; `Q=(A,A,A,A,N,N)`; consume calls zero |
| A61-B13-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_order_and_recovery_matrix[A61-B13-b]` | wrong consumption recovery authentication | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,A,A,A,N,N)`; receipt/call zero |
| A61-B14 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_b_dependency_and_source_matrix[A61-B14]` | static receipt substituted for per-operation readback | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; finish/finalize zero |
| A61-H01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_human_and_public_evidence_never_authorize[A61-H01]` | predictable/public Human factory | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; challenge zero |
| A61-H02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_human_and_public_evidence_never_authorize[A61-H02]` | direct/copy/serialization/module-sentinel evidence | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; challenge zero |
| A61-H03 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_human_and_public_evidence_never_authorize[A61-H03]` | wrong challenge vector before reservation | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; no reservation |
| A61-H04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_human_and_public_evidence_never_authorize[A61-H04]` | challenge physical/strict read mismatch | `REJECTED_EFFECT0`; `D=Z`; `Q=(A,N,N,N,A,U)`; bytes preserved |
| A61-H05 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_human_and_public_evidence_never_authorize[A61-H05]` | trusted-clock expiry/currentness failure | `REJECTED_EFFECT0`; `D=Z`; `Q=(A,N,N,N,A,U)`; expiry not extended |
| A61-H06 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_human_and_public_evidence_never_authorize[A61-H06]` | attempted Human consume inside TASK-061-A | `REJECTED_EFFECT0`; `D=Z`; `Q=(A,N,N,N,A,U)`; consume zero, separate Production Activation only |
| A61-E01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_public_readiness_and_e2e_are_audit_only[A61-E01]` | forged public E2E object | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; E2E authority zero |
| A61-E02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_public_readiness_and_e2e_are_audit_only[A61-E02]` | forged public readiness object | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,U,U,U,N,N)`; CA-B authority zero |
| A61-E03 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_public_readiness_and_e2e_are_audit_only[A61-E03]` | copy/replace/pickle/deserialization/recomputed hash | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; capability zero |
| A61-E04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_public_readiness_and_e2e_are_audit_only[A61-E04]` | status/code/synthetic evidence offered as real | `DEPENDENCY_NC_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; final apply zero |
| A61-E05 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_public_readiness_and_e2e_are_audit_only[A61-E05]` | real-E2E input offered to TASK-061-A | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; TASK-061-B only |
| A61-E06-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_public_readiness_and_e2e_are_audit_only[A61-E06-a]` | legacy direct ACTIVATE | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; config/history zero |
| A61-E06-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_public_readiness_and_e2e_are_audit_only[A61-E06-b]` | legacy direct DEACTIVATE | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; config/history zero |
| A61-C01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C01]` | predecessor lease/currentness after PREPARE entry | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,A,N)`; candidate/receipt zero |
| A61-C02-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C02-a]` | same operation/body/physical candidate already present | `DUPLICATE_COMMITTED_EVENT`; `D=Z`; `Q=(A,N,N,N,A,U)`; read-only |
| A61-C02-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C02-b]` | candidate different body or identity present | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve |
| A61-C03-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C03-a]` | candidate temp create/write/flush/identity/close failure before namespace | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; added `D=Z`; `Q=(A,N,N,N,A,U)`; exact temp cleanup only |
| A61-C03-b0 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_publication_crash_seams_are_literal[A61-C03-b0-prepublish]` | phase 3 exact; candidate currentness fails immediately before no-replace | `COLLISION_STOP`; added `D=Z`; `Q=(A,N,N,N,A,U)`; publish/cleanup zero |
| A61-C03-b1 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_publication_crash_seams_are_literal[A61-C03-b1-postpublish-pre-file-fsync]` | candidate namespace visible; file flush not proved | `COMPLETION_UNKNOWN`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; no republish |
| A61-C03-b2 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_publication_crash_seams_are_literal[A61-C03-b2-post-file-fsync-pre-directory-fsync]` | candidate file flushed; parent durability not proved | `COMPLETION_UNKNOWN`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; no republish |
| A61-C03-b3 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_publication_crash_seams_are_literal[A61-C03-b3-post-directory-fsync-pre-reopen]` | candidate namespace durable; pinned no-follow reopen not proved | `COMPLETION_UNKNOWN`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; classify only |
| A61-C03-b4 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_publication_crash_seams_are_literal[A61-C03-b4-post-reopen-pre-readback]` | candidate reopened at bound identity; exact bytes/security not proved | `COMPLETION_UNKNOWN`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; preserve |
| A61-C03-b5 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_publication_crash_seams_are_literal[A61-C03-b5-post-readback-pre-phase4]` | candidate exact readback proved; phase 4 absent | `BROKER_RECOVERY_REQUIRED`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; append phase 4 only |
| A61-C03-b6 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_publication_crash_seams_are_literal[A61-C03-b6-post-phase4-process-loss]` | exact phase 4 durable; response/process lost | `BROKER_RECOVERY_REQUIRED`; added `D=(0,0,0,0,0,0,0,1,1,0,0)`; `Q=(A,N,N,N,A,U)`; exact phase/bytes/inode/currentness recovery only |
| A61-C03-c0 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_publication_crash_seams_are_literal[A61-C03-c0-prepublish]` | phase 5 exact; receipt currentness fails immediately before no-replace | `COLLISION_STOP`; added `D=Z`; `Q=(A,N,N,N,A,U)`; receipt/cleanup zero |
| A61-C03-c1 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_publication_crash_seams_are_literal[A61-C03-c1-postpublish-pre-file-fsync]` | receipt namespace visible; file flush not proved | `COMPLETION_UNKNOWN`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; no second receipt |
| A61-C03-c2 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_publication_crash_seams_are_literal[A61-C03-c2-post-file-fsync-pre-directory-fsync]` | receipt file flushed; parent durability not proved | `COMPLETION_UNKNOWN`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; no second receipt |
| A61-C03-c3 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_publication_crash_seams_are_literal[A61-C03-c3-post-directory-fsync-pre-reopen]` | receipt namespace durable; pinned no-follow reopen not proved | `COMPLETION_UNKNOWN`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; classify only |
| A61-C03-c4 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_publication_crash_seams_are_literal[A61-C03-c4-post-reopen-pre-readback]` | receipt reopened at bound identity; exact bytes/security not proved | `COMPLETION_UNKNOWN`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; preserve |
| A61-C03-c5 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_publication_crash_seams_are_literal[A61-C03-c5-post-readback-pre-phase6]` | receipt exact readback proved; phase 6 absent | `BROKER_RECOVERY_REQUIRED`; added `D=(0,0,0,0,0,0,0,1,0,0,0)`; `Q=(A,N,N,N,A,U)`; append phase 6 only |
| A61-C03-c6 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_publication_crash_seams_are_literal[A61-C03-c6-post-phase6-process-loss]` | exact phase 6 durable; response/process lost | `BROKER_RECOVERY_REQUIRED`; added `D=(0,0,0,0,0,0,0,1,1,0,0)`; `Q=(A,N,N,N,A,U)`; exact phase/bytes/inode/currentness recovery only |
| A61-C04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C04]` | cleanup identity becomes unknown | `CLEANUP_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,N,N,N,A,U)`; foreign preserved |
| A61-C05 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C05]` | disabled predecessor semantics mismatch | `COLLISION_STOP`; `D=Z`; `Q=(U,N,N,N,U,N)`; repair/deactivate zero |
| A61-C06 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C06]` | public receipt/capability offered to final apply | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; TASK-061-B handle zero |
| A61-C07 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C07]` | exact post-canonicalization positive PREPARE terminal | `PREACTIVATION_READY_ENABLED_FALSE`; `D=(0,0,0,0,0,1,1,2,8,0,0)`; `Q=(B,N,N,N,B,U)`; config/history/ACTIVATE zero |
| A61-C08-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C08-a]` | missing/wrong/replayed PREPARE ticket before entry | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; no challenge |
| A61-C08-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C08-b]` | replay after exact prepare terminal | `DUPLICATE_COMMITTED_EVENT`; `D=Z`; `Q=(A,N,N,N,A,U)`; read-only |
| A61-C09 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C09]` | predecessor lease breaks after candidate fixture | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,A,U)`; candidate preserved, receipt zero |
| A61-C10 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C10]` | crash after challenge reservation | `BROKER_RECOVERY_REQUIRED`; `D=(0,0,0,0,0,1,0,0,0,0,0)`; `Q=(A,N,N,N,A,U)`; challenge reissue zero |
| A61-C11 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C11]` | crash after candidate exact publication/readback | `BROKER_RECOVERY_REQUIRED`; `D=Z`; `Q=(A,N,N,N,A,U)`; same-operation recovery only |
| A61-C12 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_candidate_receipt_and_recovery_matrix[A61-C12]` | receipt tag/strict parser input | `STRICT_JSON_REJECTED`; `D=Z`; `Q=(U,N,N,N,U,N)`; bytes preserved |
| A61-C13 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_contract_gate_matrix[A61-C13]` | contract-canonicalization evidence absent or not exact/current | `CONTRACT_NOT_CANONICAL_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; PREPARE not entered, candidate/challenge/receipt zero |
| A61-C14 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_authority_tail_matrix[A61-C14]` | exact A effect vector or mandatory ten-field all-false authority tail is missing, extra, defaulted, duplicated, shortened, wrong-type, `null`, or true | `STRICT_JSON_REJECTED`; `D=Z`; `Q=(U,N,N,N,U,N)` unchanged; `EA=(false,false,false)` and all ten authority fields false; receipt publication/acceptance and every downstream consumer budget/call delta zero |
| A61-C15-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_broker_binding_is_closed[A61-C15-a]` | TASK-071 receipt field/mixed-snapshot mismatch before PREPARE namespace effect | `DEPENDENCY_NC_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; challenge/candidate/receipt zero |
| A61-C15-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_preactivation_broker_binding_is_closed[A61-C15-b]` | TASK-071 currentness drift after candidate or receipt namespace fixture | `COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve; config/history zero |
| A61-C16-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_task061b_currentness_port_is_private_single_use[A61-C16-a]` | exact phase-7 A terminal and exact admitted B operation | `CURRENTNESS_VERIFIED`; `D=Z`; `Q=(A,N,N,N,A,U)`; `AB=B`; B-bound port exact 1 |
| A61-C16-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_task061b_currentness_port_is_private_single_use[A61-C16-b]` | double/concurrent loser after exact A-to-B reader winner | `REJECTED_EFFECT0`; `D=Z`; `Q=(A,N,N,N,A,U)`; `AB=A`; port return zero |
| A61-C16-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_task061b_currentness_port_is_private_single_use[A61-C16-c]` | exception/timeout/process-loss/response-loss after A-to-B reader entry | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,N,N,N,A,U)`; `AB=B`; replacement zero |
| A61-C16-d | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_task061b_currentness_port_is_private_single_use[A61-C16-d]` | wrong B operation/method, public receipt, A-port forward, copy, serialization, or deserialization before entry | `REJECTED_EFFECT0`; `D=Z`; `Q=(A,N,N,N,A,U)`; `AB=U`; victim preserved, return zero |
| A61-C17-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_config_candidate_schema_is_exact[A61-C17-a]` | exact complete scalar candidate and domain-separated JCS self-hash | `CANDIDATE_VALIDATED_EFFECT0`; `D=Z`; `Q=(A,N,N,N,A,U)`; publication zero in validator fixture |
| A61-C17-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_config_candidate_schema_is_exact[A61-C17-b]` | malformed/unknown/nested/wrong-constant/wrong-hash candidate | `STRICT_JSON_REJECTED`; `D=Z`; `Q=(A,N,N,N,A,U)`; bytes preserved, temp/publication zero |
| A61-C18-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_pending_recovery_is_exact[A61-C18-a]` | phase 3, exact coordinate/temp/parent/security/current absence lease, target absent | `PREACTIVATION_READY_ENABLED_FALSE`; added `D=(0,0,0,0,0,0,0,2,4,0,0)`; `Q=(A,N,N,N,A,U)`; exact candidate and receipt publish once |
| A61-C18-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_pending_recovery_is_exact[A61-C18-b]` | phase 3, target already exact candidate bytes and physical identity equals bound temp | `PREACTIVATION_READY_ENABLED_FALSE`; added `D=(0,0,0,0,0,0,0,1,4,0,0)`; `Q=(A,N,N,N,A,U)`; candidate readback only, receipt once |
| A61-C18-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_pending_recovery_is_exact[A61-C18-c]` | phase 3 target has different candidate body | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve, publish zero |
| A61-C18-d | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_pending_recovery_is_exact[A61-C18-d]` | phase 3 target has exact bytes at a different physical identity | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve, publish zero |
| A61-C18-e | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_pending_recovery_is_exact[A61-C18-e]` | phase 3 target classification ambiguous | `COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve, publish/retry zero |
| A61-C18-f | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_candidate_pending_recovery_is_exact[A61-C18-f]` | wrong coordinate, stale absence lease, foreign temp, parent identity drift, or parent security drift immediately prepublish | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve, publish/cleanup zero |
| A61-C19-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_pending_recovery_is_exact[A61-C19-a]` | phase 5, exact coordinate/temp/parent/security/current absence lease, target absent | `PREACTIVATION_READY_ENABLED_FALSE`; added `D=(0,0,0,0,0,0,0,1,2,0,0)`; `Q=(A,N,N,N,A,U)`; receipt publishes once |
| A61-C19-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_pending_recovery_is_exact[A61-C19-b]` | phase 5, target already exact receipt bytes and physical identity equals bound temp | `PREACTIVATION_READY_ENABLED_FALSE`; added `D=(0,0,0,0,0,0,0,0,2,0,0)`; `Q=(A,N,N,N,A,U)`; readback only |
| A61-C19-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_pending_recovery_is_exact[A61-C19-c]` | phase 5 target has different receipt body | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve, publish zero |
| A61-C19-d | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_pending_recovery_is_exact[A61-C19-d]` | phase 5 target has exact bytes at a different physical identity | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve, publish zero |
| A61-C19-e | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_pending_recovery_is_exact[A61-C19-e]` | phase 5 target classification ambiguous | `COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve, publish/retry zero |
| A61-C19-f | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_receipt_pending_recovery_is_exact[A61-C19-f]` | wrong coordinate, stale absence lease, foreign temp, parent identity drift, or parent security drift immediately prepublish | `COLLISION_STOP`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve, publish/cleanup zero |
| A61-X01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_production_composition_is_fixed[A61-X01]` | injected backend/hook/clock/SID/session/mode preflight | `PRODUCTION_INELIGIBLE_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; Product operation zero |
| A61-X02-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_production_composition_is_fixed[A61-X02-a]` | backend/build/session drift before entry | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; fresh trusted plan |
| A61-X02-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_production_composition_is_fixed[A61-X02-b]` | drift after matched entry before namespace/Profile effect | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `D=(0,0,0,0,0,0,1,0,1,0,0)`; `Q=(B,N,N,N,B,N)`; recovery only |
| A61-X02-c-profile | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_production_composition_is_fixed[A61-X02-c-profile]` | drift after the named CA-B Profile namespace seam | `COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,A,A,A,N,N)`; preserve and no retry |
| A61-X02-d-candidate | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_production_composition_is_fixed[A61-X02-d-candidate]` | drift after the named PREPARE candidate namespace seam | `COMPLETION_UNKNOWN`; `D=Z`; `Q=(A,N,N,N,A,U)`; preserve and no retry |
| A61-X03 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_production_composition_is_fixed[A61-X03]` | module introspection/copy/serialization | `REJECTED_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; private handle zero |
| A61-X04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_production_composition_is_fixed[A61-X04]` | arbitrary same-process extension composition | `PRODUCTION_INELIGIBLE_EFFECT0`; `D=Z`; `Q=(U,N,N,N,U,N)`; Product operation zero |

#### Closed fresh-fixture subcases and phase ordinals

Every umbrella row with several threats executes every exact ID below against a
fresh fixture and applies that row's literal oracle; dynamic discovery, omitted
cases, range/default aliases, and shared mutated fixtures fail collection:

| Umbrella vector | Exact mandatory in-node case IDs |
|---|---|
| M61-T02 | `direct_plan`, `copy_plan`, `replace_plan`, `pickle_plan`, `mapping_plan`, `rehashed_plan`, `module_seal` |
| M61-T03-a | `cross_action`, `wrong_instance`, `wrong_source`, `wrong_plan`, `wrong_revision`, `expired`, `replayed` |
| M61-L01 | `initial_race_loser`, `existing_race`, `late_initial_collision` |
| M61-L02 | `symlink`, `reparse`, `hardlink`, `nlink_gt_1`, `dacl_drift`, `ancestor_drift` |
| M61-L03 | `ticket_dir_race`, `case_collision`, `reparse`, `foreign_nonempty`, `false_safe_empty` |
| M61-L04 | `appeared_empty`, `appeared_nonempty`, `appeared_identical`, `appeared_different` |
| M61-J02 | `previous_bytes_swap`, `previous_inode_swap`, `previous_self_hash_swap`, `wrong_self_hash_domain`, `wrong_schema_name`, `wrong_schema_version`, `wrong_message_type`, `wrong_action`, `wrong_ordinal_state`, `wrong_sentinel`, `wrong_cumulative_d`, `wrong_budget_q`, `wrong_jcs_bytes`, `nested_effect_body_mismatch`, `nested_effect_hash_mismatch`, `fork`, `gap`, `duplicate`, `non_monotonic` |
| M61-J03 | `target_identical`, `target_different`, `same_bytes_different_inode` |
| M61-J04 | `temp_close_swap`, `hardlink`, `reparse`, `foreign_deterministic_temp` |
| M61-J05 | `source_precommit_drift`, `target_precommit_drift`, `security_precommit_drift`, `source_postcommit_drift`, `target_postcommit_drift`, `security_postcommit_drift` |
| M61-R04 | `duplicate_equal_top`, `duplicate_different_top`, `duplicate_equal_nested`, `duplicate_different_nested` |
| M61-R05-a | `nan`, `positive_infinity`, `negative_infinity`, `bom`, `trailing`, `invalid_utf8`, `control`, `nul` |
| M61-R05-b | `raw_bytes`, `depth`, `nodes`, `members`, `items`, `string_bytes`, `string_codepoints` |
| A61-B01 | `public_readiness`, `public_source_read`, `public_profile_binding`, `public_migration_readback`, `caller_true`, `status_string`, `recomputed_hash` |
| A61-B03 | `task063_missing`, `task072_missing`, `task060_missing`, `task069_missing`, `task071_missing`, `stale`, `cross_build`, `cross_instance` |
| A61-B04 | `same_source_bytes_different_inode`, `same_profile_bytes_different_inode`, `source_read_post_swap`, `profile_read_post_swap` |
| A61-B05 | `wrong_ca_a`, `wrong_revision`, `wrong_head`, `wrong_envelope`, `wrong_predecessor`, `wrong_currentness`, `wrong_correlation`, `wrong_pair`, `wrong_install`, `wrong_build` |
| A61-B07 | `task058_private_parser`, `raw_root`, `exact_lane`, `dummy_anchor`, `caller_revision`, `caller_store`, `caller_scope`, `skill_receipt`, `task067_input` |
| A61-B10 | `u1c_receipt_missing`, `baseline_digest_missing`, `composition_digest_missing`, `readiness_digest_missing`, `uppercase_digest`, `malformed_digest`, `three_way_mismatch`, `static_receipt_wrong`, `consumption_port_wrong`, `source_wrong`, `predecessor_wrong`, `subject_wrong`, `pair_wrong`, `install_wrong`, `build_wrong` |
| A61-H02 | `direct`, `copy`, `replace`, `pickle`, `deserialize`, `raw_string`, `module_sentinel`, `recomputed_hash` |
| A61-H03 | `wrong_action`, `wrong_instance`, `wrong_pair`, `wrong_ca_a`, `wrong_ca_b`, `wrong_source`, `wrong_plan`, `wrong_revision`, `wrong_history`, `wrong_backend`, `wrong_build`, `wrong_user`, `wrong_session` |
| A61-H04 | `stat_open_swap`, `read_post_swap`, `same_bytes_different_inode`, `hardlink`, `reparse`, `ancestor_drift`, `security_drift` |
| A61-H05 | `expired`, `wall_clock_rollback`, `forward_jump`, `suspend_resume`, `boot_restart`, `timezone_change`, `phase_clock_swap` |
| A61-E01 | `direct_e2e`, `module_e2e_seal`, `synthetic_false_recreation`, `valid_hash_forge`, `subclass`, `duck_type` |
| A61-E02 | `direct_readiness`, `module_result_seal`, `valid_hash_forge`, `ca_b_not_executed` |
| A61-C03-a | `temp_create`, `temp_write`, `temp_flush`, `temp_identity`, `temp_close` |
| A61-C13 | `canonicalization_missing`, `canonicalization_stale`, `canonicalization_wrong_contract`, `canonicalization_wrong_producer`, `canonicalization_wrong_schema_file`, `canonicalization_wrong_schema_resource`, `canonicalization_wrong_consumer_set`, `canonicalization_wrong_owner_build`, `canonicalization_copy`, `canonicalization_rehash`, `canonicalization_same_body_different_inode` |
| A61-C14 | `missing_enabled`, `true_enabled`, `missing_config_history_mutated`, `true_config_history_mutated`, `missing_activation_applied`, `true_activation_applied`, `missing_authority_created`, `true_authority_created`, `missing_migration_authority`, `true_migration_authority`, `missing_profile_write_authority`, `true_profile_write_authority`, `missing_human_authority`, `true_human_authority`, `missing_e2e_authority`, `true_e2e_authority`, `missing_config_write_authority`, `true_config_write_authority`, `missing_activation_authority`, `true_activation_authority`, `missing_production_activation_authorized`, `true_production_activation_authorized`, `missing_release_authority`, `true_release_authority`, `missing_deploy_authority`, `true_deploy_authority`, `string_false_each_false_field`, `numeric_zero_each_false_field`, `null_each_false_field`, `duplicate_equal`, `duplicate_different`, `unknown_authority_field`, `unknown_effect_field`, `short_authority_tail`, `short_effect_vector`, `default_inference_attempt` |
| A61-C15-a | `missing_broker_identity`, `missing_broker_build`, `missing_operation_session`, `missing_evidence_raw`, `missing_evidence_identity`, `missing_evidence_security`, `mixed_generation`, `same_bytes_different_inode`, `wrong_build`, `wrong_session` |
| A61-C15-b | `broker_identity_post_namespace`, `broker_build_post_namespace`, `operation_session_post_namespace`, `evidence_raw_post_namespace`, `evidence_identity_post_namespace`, `evidence_security_post_namespace` |
| A61-C16-a | `exact_b_currentness_port` |
| A61-C16-b | `double_call`, `concurrent_loser` |
| A61-C16-c | `exception`, `timeout`, `process_loss`, `response_loss` |
| A61-C16-d | `wrong_operation`, `wrong_method`, `public_receipt`, `a_port_forward`, `copy`, `serialize`, `deserialize`, `subclass`, `duck_type` |
| A61-C17-a | `exact_candidate`, `exact_self_hash` |
| A61-C17-b | `missing_field`, `unknown_field`, `nested_object`, `array`, `wrong_schema`, `wrong_version`, `wrong_message`, `wrong_state`, `wrong_action`, `true_enabled`, `numeric_false`, `null`, `wrong_domain`, `wrong_jcs`, `wrong_self_hash` |
| A61-C18-a | `absent` |
| A61-C18-b | `exact_identity_exact_bytes` |
| A61-C18-c | `different_body` |
| A61-C18-d | `same_bytes_different_identity` |
| A61-C18-e | `ambiguous` |
| A61-C18-f | `wrong_coordinate`, `stale_absence_lease`, `foreign_temp`, `wrong_parent_identity`, `parent_security_drift` |
| A61-C19-a | `absent` |
| A61-C19-b | `exact_identity_exact_bytes` |
| A61-C19-c | `different_body` |
| A61-C19-d | `same_bytes_different_identity` |
| A61-C19-e | `ambiguous` |
| A61-C19-f | `wrong_coordinate`, `stale_absence_lease`, `foreign_temp`, `wrong_parent_identity`, `parent_security_drift` |

`A61-C03-b0` through `A61-C03-b6` and `A61-C03-c0` through
`A61-C03-c6` are already literal separately collected pytest nodes in the
normative ledger, not umbrella cases. Each node executes one frozen seam, one
first authenticated classification, and one repeat query. Recovery requires the
exact expected phase raw/canonical bytes, phase self-hash, phase physical
identity, target bytes and inode, ancestor/security currentness, and operation
binding. Exact committed state is read-only duplicate, different body/identity
is `COLLISION_STOP`, ambiguous state is `COMPLETION_UNKNOWN`, and automatic
retry, republish, replacement, deletion, or budget refund is zero.

Each CA-A row below is one exact collected pytest node. For ordinals 0..3, the
first authenticated recovery query consumes the same-operation recovery-winner
slot, returns `BROKER_RECOVERY_REQUIRED`, and permits only the listed `next`;
the repeat query executes inside the same node, returns the same classification
read-only, and adds `D=Z`. Ordinal 4 permits only exact terminal readback as
`DUPLICATE_COMMITTED_EVENT`, with both first and repeat calls read-only.

| Exact pytest node | Cumulative truth from fresh operation | Q | only `next` |
|---|---|---|---|
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_every_phase_crash_is_exact[M61-J07-a0]` | `PREPARED`; `D=(0,0,0,0,0,0,1,0,1,0,0)` | `(B,N,N,N,N,N)` | `PAYLOAD_STAGED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_every_phase_crash_is_exact[M61-J07-a1]` | `PAYLOAD_STAGED`; `D=(0,0,0,0,0,0,1,1,2,0,0)` | `(B,N,N,N,N,N)` | `MANIFEST_PUBLISHED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_every_phase_crash_is_exact[M61-J07-a2]` | `MANIFEST_PUBLISHED`; `D=(0,0,0,0,0,0,1,1,3,0,0)` | `(B,N,N,N,N,N)` | `SNAPSHOT_COMMITTED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_every_phase_crash_is_exact[M61-J07-a3]` | `SNAPSHOT_COMMITTED`; `D=(1,0,0,0,0,0,1,0,4,0,0)` | `(B,N,N,N,N,N)` | `TERMINAL_READBACK_VERIFIED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_ca_a_every_phase_crash_is_exact[M61-J07-a4]` | `TERMINAL_READBACK_VERIFIED`; `D=(1,0,0,0,0,0,1,0,5,0,0)` | `(B,N,N,N,N,N)` | none; exact duplicate only |

## 18. Fault/restart seam contract

Private test composition injects faults after:

- ticket durable issue and before/after executor entry;
- secure lock create/open/lock/currentness;
- operation-root and PREPARED publication;
- each source open/read/post-read and payload temp create/write/flush;
- manifest publish and readback;
- immediately before/after directory no-replace commit and durability;
- each immutable phase publication/readback;
- CA-A terminal capability issue/entry/burn;
- source seed move/preflight delivery/bind/project, consumer-bundle bind, broker
  begin, every TASK-069 candidate phase, reserve, TASK-061 consume, prepare,
  broker finish, finalization, and each CA-B observation phase;
- PREPARE ticket match/entry and existing/genesis config predecessor lease;
- disabled config predecessor initial and final same-handle/absence read;
- challenge reservation publication;
- every CA-C immutable phase plus config-candidate and completion-receipt
  publication/durability;
- terminal response loss; and
- every owned-handle close/cleanup seam.

Each seam has an exact classification, first-call count, subsequent-call count,
effect delta, preservation oracle, and restart rule. Production cannot select a
fault seam through argv/config/receipt/hook.

## 19. Future source/test traceability

| Matrix | Owner symbols | Required focused test in allowed test set |
|---|---|---|
| M61-T/L/J | `plan_legacy_bridge_migration`, `execute_legacy_bridge_migration`, `_write_journal`, `_write_manifest`, `_write_new_file`; private operation/lock/tree/recovery port and journal-schema nodes | `test_task061_ca_a_requires_live_action_ticket`; `test_task061_ca_a_lock_phase_manifest_and_directory_race_matrix`; `test_task061_ca_a_recovery_winner_is_same_operation_only` |
| M61-R | `read_legacy_bridge_migration`, `BridgeMigrationReadback`, `_read_json`, `_verify_persisted_snapshot`; private terminal reader | `test_task061_ca_a_terminal_readback_is_pinned_strict_and_private` |
| A61-B | `plan_connector_source_binding`, `execute_connector_source_binding`, exact `PROFILE_SOURCE_BINDING_V2` adapter, `Task061ProfileConsumptionPortV2.consume/recover_consumption`, `TASK061_PROFILE_CONSUMER_V2`, CA-B phase/schema validators and recovery owner | `test_task061_ca_b_requires_live_dependency_ports_and_exact_profile_readback`; `test_task061_ca_b_exact_profile_v2_order_and_crash_recovery` |
| A61-H/E | `issue_human_activation_evidence`, `admit_adapter_e2e_observation`, public dataclasses; private broker adapters | `test_task061_public_readiness_human_and_e2e_objects_are_audit_only`; `test_task061_preactivation_challenge_is_random_broker_backed_and_unconsumed` |
| A61-C/X | exact config/history/challenge/candidate/receipt schema nodes, `apply_connector_activation_transaction`, Production composition, private predecessor lease, config-candidate/receipt publisher and recovery owner | `test_task061_preactivation_requires_distinct_prepare_ticket_and_predecessor_lease`; `test_task061_preactivation_candidate_is_immutable_disabled_and_backend_fixed`; `test_task061_legacy_apply_activate_and_deactivate_are_production_effect_zero`; `test_task061_preactivation_fault_recovery_and_body_free_errors` |

New names live in the optional paired private module/test from section 4 or are
integrated into the two existing allowed owner modules/tests. Historical tests
remain unchanged unless a safety expectation is strengthened. No fixture test
may assert real authority or enabled state.

### 19.1 L-R2 receipt and consumer severity Gate

The coordinated L-R2 review records at least High and cannot pass if the A
receipt schema row, constructor-shaped text, all-false suffix, fixture, `A61-C14`
ledger oracle, mandatory case list, or limited amendment differs in field name,
count, declared order, built-in type, fixed value, or rejection outcome. It is
also High if any A/B/TASK-069 consumer family can be forwarded, copied,
serialized, deserialized, invoked by wrong operation/method, or crossed between
receipt-only and live-session ABIs while changing a victim budget. Any such
route that creates migration/Profile/config/history/Human/E2E/activation,
release, deploy, or Production authority is Critical. Critical/High must be
`0/0` on one freshly frozen coordinated tuple; all V6 reviews are historical
only and cannot be replayed.

It is also High if PREPARE terminal precedes exact completion-receipt durability
and pinned readback, terminal performs an authority write, a publish/file-fsync/
directory-fsync/readback/process-loss seam remains an umbrella instead of one
literal crash node, or recovery accepts anything other than exact phase bytes,
self-hash, physical identity, target bytes/inode, ancestor/security currentness,
and operation binding.

## 20. Acceptance

TASK-061-A corrective implementation cannot pass unless all are true:

1. The canonical completion graph is the split TASK-061-A/TASK-061-B graph in
   section 5; old one-piece completion text grants no authority.
2. CA-A, CA-B, and CA-C prepare each require distinct MIGRATE, BIND, and PREPARE
   broker-backed one-shot tickets; pre-entry mismatch preserves victim budget and
   public confirmation/ticket objects create effect zero.
3. CA-A lock, phase, manifest, payload, snapshot commit, terminal readback, and
   cleanup satisfy physical identity, no-replace, durability, and preservation
   contracts.
4. Legacy source and unrelated files have overwrite/delete count zero; one
   operation creates at most one exact snapshot terminal.
5. All TASK-061 authority JSON is strict/bounded and bound to one opened physical
   snapshot; ambiguous input remains preserved.
6. Public migration/readiness/source/Human/E2E/config/receipt dataclasses and
   hashes are audit-only with authority zero.
7. CA-B binds only exact live TASK-063/TASK-072/TASK-060/TASK-069/TASK-071
   contracts and the TASK-069 U1c owner-produced application-composition receipt,
   one closed TASK-069 effect-zero identity envelope, TASK-060's distinct
   canonical completion receipt, and one private CA-A terminal. TASK-061-A
   consumes no TASK-067 input, D2S receipt, or
   tuple directly; D2S terminates at TASK-069 and has no direct edge to TASK-060.
   TASK-060 source and TASK-061 consumption handles transfer directly to
   TASK-069 and legacy TASK-058 internals are not imported as authority.
8. Profile V2 follows the exact two-stage source plus preflight/begin/reserve/
   consume/prepare/finish/finalize graph; indexes advance only once after broker
   COMMITTED, and arbitrary callable/path/hash/fixed-view substitution has
   Profile delta zero.
9. CA-C prepare enters one exact PREPARE ticket, holds an exact existing/genesis
   predecessor lease through receipt linearization, and issues one random
   broker-backed challenge plus one immutable ACTIVATE-only disabled candidate
   without consuming the challenge; DEACTIVATE/emergency disable cannot
   substitute.
10. Before separate V2 receipt-contract canonicalization, receipt publication and
     consumer acceptance are zero with `CONTRACT_NOT_CANONICAL_EFFECT0`. After
     that Gate, the only positive TASK-061-A receipt is
     `PREACTIVATION_READY_ENABLED_FALSE`; config/history revision delta is zero,
     `enabled=true` count is zero, and activation apply call count is zero.
11. Production fixes backend/clock/user/session/build internally; test seams,
    module sentinels, and same-process caller objects never become authority.
12. Matched entry/return/exception/timeout/crash burns every entered ticket/
    capability; pre-entry vector mismatch preserves victim budget, different-body
    collision stops, and only exact committed identity projects duplicate.
13. Directory durability/readback failure emits receipt zero; unknown or foreign
    state is preserved and never automatically repaired/deleted/retried.
14. Errors/status/log/stdout/temp/journal expose no path, body, Profile,
    correlation, SID/account, DACL/ACE, OS detail, secret, or offending value.
15. Every M61/A61 matrix row/subvector maps to an exact test node, effect-count oracle,
    recovery rule, and one frozen source/test identity.
16. Focused, relevant historical CA-A/CA-B/CA-C, TASK-063/TASK-072/TASK-060,
    TASK-069 closed-envelope/U1c fixture, TASK-071 broker fixture, strict JSON,
    concurrency, crash/restart, and Windows-native regression pass without
    expectation weakening. No direct SKILL-D2S fixture enters TASK-061 tests.
17. Independent Tester passes; independent Critic returns Critical/High `0/0`;
    Judge returns PASS on one frozen design/source/test identity.
18. TASK-061-B, real installed E2E, Human challenge consumption, final config
    projection, ACTIVATE execution, Release, Deploy, and Production Activation
    remain separate and unclaimed.
19. TASK-069 canonical identity/envelope and TASK-060's own completion receipt
    are separate independent Gates. The SKILL-D2S canonical main/tree tuple
    terminates at TASK-069 and alone never satisfies either Gate or TASK-061
    completion. Missing either receipt keeps TASK-061-A consumer call count,
    Profile/config/history delta, and authority-created count exactly zero.
    D2S relabel/bypass or a D2S-to-TASK-060 direct edge is a mandatory C/H review
    finding, and this acceptance requires Critical/High `0/0`.
20. The exact A effect vector and ten-field authority tail are present in the
    section 8.1 schema, receipt text, real/fixture validators, negative ledger,
    mandatory cases, and limited amendment with identical names, count, order,
    values, and outcomes. Every malformed/short/defaulted form rejects with
    receipt publication/acceptance zero, downstream consumer budgets unchanged,
    and Profile/config/history/Human/activation/unrelated-file deltas zero.
21. CA-C PREPARE preserves reservation -> candidate materialization/readback ->
    completion-receipt durable publication/readback -> terminal order; terminal
    authority writes are zero. `A61-C03-b0..b6` and `A61-C03-c0..c6` are literal
    separately collected nodes with exact recovery identity/currentness,
    duplicate read-only, collision STOP, and automatic retry zero.

## 21. Windows-native QA contract

Native QA uses an isolated synthetic test root and never installed/Owner data.
The positive Windows profile is an approved local NTFS volume under the test
root, native long-path mode, same-volume publication, and a Product process able
to request DACL/SID/file-ID plus directory handles. Immutable file/directory
publication uses an operation-owned `CreateFileW(CREATE_NEW)` temp handle and
`SetFileInformationByHandle(FileRenameInfoEx)` without the replace flag while the
pinned parent handle remains live. Success requires file `FlushFileBuffers`,
no-replace namespace result, parent-directory durability port success, no-follow
reopen, exact file-ID/volume-ID/body/security readback, and supported-filesystem
attestation. Config existing leases deny write/delete sharing; genesis uses an
exclusive directory change/oplock and negative-lookup reservation. Any API,
filesystem, privilege, oplock, or directory-durability unsupported result is
`DEPENDENCY_NC_EFFECT0`, never emulation or PASS.

The TASK-061-owned parent-directory handle is opened literally with
`CreateFileW(path, GENERIC_READ|GENERIC_WRITE|DELETE|SYNCHRONIZE,
FILE_SHARE_READ, NULL, OPEN_EXISTING,
FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT, NULL)`. The staging
directory handle includes `DELETE|SYNCHRONIZE`, denies write/delete sharing,
and uses the same two flags. Any successful open is immediately checked for
directory type, no reparse, volume/file ID, owner SID, DACL, and non-inheritance
expectations on that handle. `SetFileInformationByHandle(FileRenameInfoEx)` uses
`FILE_RENAME_FLAG_POSIX_SEMANTICS` only; the replace flag is zero and the target
name is the exact contained UTF-16 component bound by the operation.

Literal result mapping is: a target observed or `ERROR_FILE_EXISTS`/
`ERROR_ALREADY_EXISTS` is `COLLISION_STOP`; `ERROR_NOT_SUPPORTED`,
`ERROR_INVALID_PARAMETER`, `ERROR_PRIVILEGE_NOT_HELD`, unsupported filesystem,
or inability to obtain the exact access/share mode before namespace effect is
`DEPENDENCY_NC_EFFECT0`; every other pre-namespace failure is
`REJECTED_EFFECT0`. After the rename call can have made the namespace visible,
any false/unknown return, `FlushFileBuffers(parent)==FALSE`, lost handle,
identity/security mismatch, reopen/readback/close uncertainty, or unmapped
Win32 result is `COMPLETION_UNKNOWN` and preserve-only. Success requires rename
TRUE, parent `FlushFileBuffers` TRUE, exact no-follow reopen/readback and
identity/security match. No weaker share/access mask or path reopen may claim
the positive native evidence.

It verifies:

- secure initial/existing lock behavior and race loser classification;
- junction/symlink/reparse/hardlink, ancestor/DACL, case/short-name, and
  same-bytes/different-file identity vectors;
- operation-root and directory no-replace behavior with empty/nonempty/identical
  appeared targets;
- source stat-open/read-post and manifest/journal/phase swap matrices;
- file and directory durability failure mapping;
- foreign temp/staging/snapshot preservation;
- trusted broker ticket/challenge user/session/process and burn behavior;
- backend/clock/build drift;
- config candidate remains disabled and activation/history calls remain zero;
  and
- body/path/SID/DACL/OS-detail-free public failures.

Unavailable native DACL, directory no-replace/durability, trusted broker, or
clock/session evidence is `NOT_CONFIRMED`, never PASS. Fixture, Linux permission,
synthetic adapter, static source, or hosted test evidence cannot be promoted to
native or Production proof.

## 22. Design completion receipt template

```text
task: TASK-061-A
unit: PREACTIVATION_PREPARE_CORRECTIVE_DESIGN
design_identity: TASK061A-PTD-PREACTIVATION-PREPARE-V7
base: origin/main@19c37245a1444f6f3ed5f3b707eeea94e68602b0
allowed_file: docs/ai-team/tasks/TASK-061/preactivation-prepare-complete-design-packet.md
sole_writer: PLATFORM_TRUST_AND_DELIVERY_DESIGN_B
task068_dependency_sha256: PENDING_R1
task069_dependency_status: CANONICAL_RECEIPT_MISSING_EFFECT0
task069_dependency_sha256: PENDING_R1
task063_dependency_sha256: PENDING_R1
task060_dependency_sha256: PENDING_R1
skill_d2s_audit_status: CANONICAL_SKILL_MAIN_MERGED_ONLY
skill_d2s_audit_canonical_main_head: 1646a2e9f3f0cb0a468dd52e564093bde04f49de
skill_d2s_audit_skill_tree_sha256: 4c3269e00bb934edc15cd58b73eca06c8846b2ed7104e3fa8573e6441ad47dc2
skill_d2s_installed_sync: DEPENDENCY_NC_EFFECT0
skill_d2s_task058_baseline: DEPENDENCY_NC_EFFECT0
skill_d2s_real_installed_e2e: DEPENDENCY_NC_EFFECT0
task071_broker_contract_sha256: PENDING_R1
task072_ticket_contract_sha256: PENDING_R1
review_target_range: bytes[0,170124)
review_target_sha256: 3fcc4599b40f82cf5a06098bd94da153970ca4586632068bfff2d63e1c7a8472
review_target_lines: 2258
review_target_lf_count: 2258
review_target_bytes: 170124
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
profile_effect: 0
config_history_effect: 0
activation_effect: 0
release_deploy_production_effect: 0
authority_created: false
migration_authority: false
profile_write_authority: false
human_authority: false
e2e_authority: false
config_write_authority: false
activation_authority: false
production_activation_authorized: false
release_authority: false
deploy_authority: false
```

Future source/test mutation requires a fresh implementation start receipt,
canonical dependency identities, fresh main/worktree/dirty/overlap/lock checks,
exact Allowed Files, and its own DEV-4 review. TASK-061-A design or fixture
Evidence never authorizes TASK-061-B or a Production activation.
