# TASK-061 — CA-A/B/C Limited Partition Amendment Design

Status: `DESIGN_REVIEW_READY_R5 / DEV-4 / DEPENDENCY_NC / INDEPENDENT_REVIEW_PENDING_R5 / SOURCE_START0 / NATIVE0`

Amendment identity: `TASK061-CAABC-LIMITED-PARTITION-V5`

Canonical Task: `TASK-061 / BVP-MONTAGE-CONNECTOR-ACTIVATION-001`

Design base: `origin/main@19c37245a1444f6f3ed5f3b707eeea94e68602b0`

## 1. Decision

This is a limited partition of the existing TASK-061 responsibility. It does
not replace, renumber, reopen, or transfer CA-A, CA-B, or CA-C ownership.

The original responsibility remains:

```text
CA-A security/migration
    -> CA-B source/Profile binding
    -> CA-C explicit Human-bound connector transition
```

The completion workflow is partitioned only to remove the dependency cycle
between preactivation preparation, facade compilation, and real installed E2E:

```text
TASK-061-A PREACTIVATION PREPARE
    -> CA-A corrected terminal
    -> CA-B corrected terminal
    -> CA-C disabled candidate/challenge contract
    -> proposed enabled:false public dependency receipt

TASK-061-B FINAL CA-C IMPLEMENTATION COMPLETION
    -> begins only after TASK-036 real installed E2E
    -> verifies the final CA-C algorithm and Product composition
    -> emits an all-false development completion receipt
    -> performs no Production Activation

PRODUCTION ACTIVATION OPERATION
    -> separate fresh Human Gate and runtime authority
    -> outside this amendment and outside any design/implementation receipt
```

TASK-061-A is not a new Task that owns CA-A/CA-B. TASK-061-B is not a new Task
that owns activation. They are bounded completion partitions inside the already
allocated TASK-061 CA-A -> CA-B -> CA-C responsibility.

## 2. Non-effects and authority state

This Design Unit has exactly zero source, schema, test, config, history,
installed bridge, Profile, native, Provider, Release, Deploy, and Production
Activation effect.

Every public design, dependency, and development-completion receipt in this
partition is evidence only and carries:

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

No receipt, hash, status, dataclass, module sentinel, copied mapping, serialized
body, test fixture, or hosted PASS can be converted into a private capability or
an activation invocation.

## 3. Historical compatibility and amendment limit

The following canonical TASK-061 facts remain unchanged:

- TASK-061 owns only bridge security/migration orchestration, source binding,
  BVP connector config/history, and the explicit activation/deactivation
  transaction boundary;
- repository and distribution defaults remain `enabled:false`;
- TASK-058/TASK-069 own File Bridge, readiness, privacy, Profile publication,
  and currentness;
- TASK-060 owns promoted Preference source completion;
- TASK-063 owns its installation readback; TASK-070 and TASK-072 retain their
  exact upstream pair/broker responsibilities;
- TASK-036 owns the packaged real installed command/E2E operation;
- TASK-075 R6 is the design-only TASK-036/voice integration boundary at exact
  SHA-256 `6F6F52F9294B1838C7A282EB830635743FB3F5FF5A727B3DABE119513B9DF279`;
  it creates no producer, native-runtime, or Human-Gate authority;
- TASK-067 owns facade compilation/current-coordinate completion;
- TASK-065 is a downstream completion-receipt consumer only; and
- Release, Deploy, and Production Activation remain separately gated.

Ordinary DEACTIVATE remains inside the existing explicit Human-bound CA-C
runtime responsibility; this partition neither removes it nor converts it into
an emergency authority. Any emergency fail-closed disable remains a separately
designed Product safety path and never ACTIVATE authority.

`preactivation-prepare-complete-design-packet.md` remains the detailed draft for
TASK-061-A physical I/O, race, recovery, and negative contracts. This amendment
controls only the A/B completion boundary and producer/consumer direction. It
does not resolve that draft's outstanding independent-review findings or turn
either draft into implementation authority.

Artifact SHA-256
`9C6C7D95DAE9B767E0240A6C5ECF8A973A6FBA4237BC4D553A03647DBBC04A78`
received independent DEV-4 `C/H/M/L=0/0/0/0` and Judge `PASS_DESIGN_ONLY` for
the H1/M1/M2 correction identity. The TASK-069 M2 addition below creates a new
artifact identity, so that verdict is retained as historical review evidence
but cannot be replayed onto the current bytes. It canonicalizes no contract,
grants no implementation authority, and leaves current review/source start
gated until the new exact SHA receives independent review.

If this amendment conflicts with historical prose only about whether TASK-061
completion is one piece or two pieces, this amendment controls that partition
question. It does not modify any other historical acceptance, ownership, or
effect boundary.

## 4. One-way dependency graph

The proposed one-way graph is:

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

TASK-036 packaged real installed operation
    -> TASK-036 own executed-operation receipt chain

TASK-036 own executed-operation receipt chain -> TASK-061-B

all canonical completion receipts -> TASK-065
```

There is no D2S -> TASK-060 direct edge and no D2S -> TASK-061-A direct edge.
TASK-061-A reads neither SKILL source nor a D2S receipt. It accepts TASK-069's
own closed identity envelope and TASK-060's own completion receipt as distinct,
non-substitutable inputs.

Neither SKILL-D2S nor TASK-069 may produce installed-instance, installed-runtime,
executed-operation, or real-E2E evidence. SKILL source/tree hashes, copied or
installed SKILL hashes, and SKILL-side receipts remain audit inputs to TASK-069
only. Presenting any of them to TASK-061-A, TASK-036, or TASK-061-B as installed,
runtime, broker, or E2E authority is `REJECTED_EFFECT0`.

Until each named canonical receipt exists and is current, the dependent entry
is `DEPENDENCY_NC_EFFECT0`. A fixture never fills a missing edge.

## 5. TASK-061-A responsibility

TASK-061-A contains three ordered slices of the existing Task:

1. corrected CA-A secure migration and authoritative terminal readback;
2. corrected CA-B source/Profile binding and authoritative terminal readback;
3. CA-C preactivation request, disabled predecessor proof, random challenge
   reservation contract, immutable disabled config candidate, and exact terminal
   readback.

It never:

- consumes real installed E2E;
- applies ACTIVATE or DEACTIVATE;
- writes a steady-state connector config;
- changes config/history revision;
- writes `enabled:true`;
- consumes a Human activation decision; or
- creates an activation/apply capability usable by TASK-061-B or Production
  Activation. The evidence-only `Task061APreactivationCurrentnessPortV2`
  described below is the sole exception: A produces it only for B's fresh
  currentness read, it has no activation/apply authority, and its one-use
  budget cannot be forwarded or converted into such authority.

Its intended future positive public result is described by the proposed
`TASK061_PREACTIVATION_PREPARE_RECEIPT_V2` contract. This name is not a current
canonical schema, closed receipt contract, or implementation authority. Until
that exact contract is separately canonicalized and its trusted producer is
available, the only contract result is `CONTRACT_NOT_CANONICAL_EFFECT0`:
publication count, consumer acceptance count, and every effect remain zero.
The proposed terminal invariants are:

```text
state=PREACTIVATION_READY_ENABLED_FALSE
enabled=false
config_history_mutated=false
activation_applied=false
fixture_only=false
real_binding=true
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

`real_binding=true` means only that the admitted CA-A/CA-B dependency identities
were real rather than fixtures. It does not mean real installed E2E, Human
approval, activation authority, or an enabled connector.

The receipt is an immutable public dependency/audit projection. TASK-067 and
TASK-036 may pin its exact identity as input. They cannot deserialize it into a
capability, invoke TASK-061 effects, or refresh a stale plan automatically.

## 6. TASK-061-A producer/consumer contract

### Producer

After the exact receipt contract becomes canonical, only the trusted TASK-061-A
Product operation may publish the receipt after exact no-replace
candidate/receipt publication, durability, and pinned readback.
The operation binds the exact CA-A/CA-B terminals, TASK-063/TASK-072 instance,
TASK-069 envelope, TASK-060 completion, disabled predecessor, config candidate,
challenge reservation, backend/build/session/clock policy, and operation plan.
Its durable record and proposed public projection must also bind the exact
TASK-071 broker identity/currentness evidence defined by TASK-071, including
the current broker implementation/build coordinate, operation/session
coordinate, and opened evidence identity/bytes hash. Public TASK-071 fields do
not create broker authority. Missing, stale, substituted, or differently bound
TASK-071 evidence is `DEPENDENCY_NC_EFFECT0`.

### Consumers

Only after the exact proposed receipt contract becomes canonical may TASK-067
consume it to bind the Generic-only facade/current-coordinate contract, and may
TASK-036 consume it as one prerequisite for the packaged real installed E2E
operation. Before then both consumers return
`CONTRACT_NOT_CANONICAL_EFFECT0`. Neither consumer gains config, history, Human,
E2E, broker, or activation authority.

Same body at another physical identity, same public fields with another
dependency generation, stale TASK-069/TASK-060/TASK-063/TASK-072 state, or a
relabelled D2S receipt rejects with every effect zero and requires a fresh plan.

## 7. TASK-061-B responsibility

TASK-061-B begins only after canonical TASK-036 real installed E2E completion.
It owns the final CA-C implementation-completion gate, not a Production
Activation invocation.

The trusted final verifier must freshly and jointly revalidate:

- the exact TASK-061-A receipt plus its durable candidate, challenge subject,
  CA-A terminal, CA-B terminal, and disabled predecessor currentness;
- current TASK-063 installed instance and TASK-072 instance binding;
- the TASK-071 broker identity/currentness durably bound by A, plus a fresh
  TASK-071 verifier/completion read proving the same current broker
  implementation/build, operation/session coordinate, evidence bytes, and
  physical identity at B entry and final readback;
- TASK-069 closed identity/currentness envelope;
- TASK-060 independent completion/current source identity;
- TASK-067 facade completion/current coordinate;
- TASK-036 executed real installed command receipt, public receipt, hidden
  Generic correlation, Profile readback, adapter build/config projection, exact
  request/result digests, operation ID, timestamp/expiry, instance binding, the
  exact TASK-075 R6 design SHA above, and distinct current non-fixture TASK-075
  producer/native/Human-Gate receipt identities;
- native trusted backend, Product build/image, clock, owner user/session, and
  security currentness; and
- config/history still at the exact disabled predecessor expected by A.

Status-only, code-presence, synthetic, fixture, public-hash-only, adapter
`canonical_store_written`, receipt-only, or caller-constructed E2E evidence is
never a substitute.

TASK-061 does not interpret voice payloads or own TASK-075 producer/native/Human
work. The producer, native-runtime, and Human-Gate receipts are pairwise
distinct by exact role tag, closed body, physical identity, producer identity,
and operation binding. One receipt cannot occupy two roles, and swapping any
two role-tagged receipts is not normalization: it is
`DEPENDENCY_NC_EFFECT0`. A correct R6 design SHA without all three separately
current receipts is `DEPENDENCY_NC_EFFECT0`; the design SHA cannot populate any
receipt role and can never be promoted to B PASS by design evidence.

TASK-061-B freezes and validates the algorithm that a later separately
authorized Production operation would use to enter the still-current bound
challenge, consume a private one-use capability, project steady-state config,
and perform post-transition readback. This Design/implementation completion does
not invoke that algorithm against Production and does not consume the real
Production Human Gate.

### 7.1 Future implementation boundary and exact Allowed Files

TASK-061-B is a sequential follow-on slice, not a concurrent owner. Before its
source start it requires a fresh main/worktree/dirty/overlap/lock bind and exact
canonical dependency receipts. Its future mutation boundary is limited to:

```text
src/ai_video_production/montage_learning_connector_activation.py
src/ai_video_production/montage_learning_preactivation_operation.py
tests/test_montage_learning_connector_activation.py
tests/test_task061_montage_learning_preactivation_operation.py
schemas/montage-learning-connector-activation.schema.json
src/ai_video_production/schema_resources/montage-learning-connector-activation.schema.json
docs/ai-team/tasks/TASK-061/ca-a-b-c-limited-partition-amendment-design.md
docs/ai-team/tasks/TASK-061/preactivation-prepare-complete-design-packet.md
```

The symbols owned by B are the private final-verifier composition, the
development-only one-use verification lease, its strict durable phase/receipt
reader-writer, the closed B receipt projection, and the legacy public apply
fail-closed gate. B does not own CA-A migration symbols, TASK-060/063/067/069/
071/072 readers or schemas, TASK-036 execution, SKILL source, common atomic
helpers, Release/Deploy, or Production Activation. TASK-072 is consumed only by
its canonical trusted port; source/schema/test edit count there is zero.

### 7.2 Private verifier ABI and one-use lifecycle

The only B entry is an internally composed Product call. It accepts live
trusted ports, never paths, mappings, public dataclasses, caller-selected
backends, clocks, hooks, or serialized capabilities:

```text
verify_final_ca_c_for_development(
    admitted_b_ticket: Task061FinalCaCVerificationLeaseV1,
    task061_a: Task061APreactivationCurrentnessPortV2,
    task036_e2e: Task036InstalledE2ECurrentnessPortV1,
    task067_facade: Task067FacadeCurrentnessPortV1,
    task063_installation: Task063InstallationCurrentnessPortV2,
    task072_binding: Task072InstalledBindingCurrentnessPortV1,
    task071_broker: Task071BrokerCurrentnessPortV1,
    task069_envelope: Task069IdentityEnvelopeCurrentnessPortV1,
    task060_completion: Task060CompletionCurrentnessPortV2,
) -> Task061FinalCaCDevelopmentPortV1
```

`task061_a` is produced only by TASK-061-A's
`read_preactivation_currentness_for_task061b(admitted_b_operation_binding)`.
`task060_completion` is produced only by TASK-060's distinct
`read_completion_currentness_for_task061b(admitted_task061b_operation_binding)`.
Both producer slots are B-operation/consumer-bound and one-use; the earlier
TASK-061-A reader port, TASK-067/TASK-036 ports, and TASK-069 live-session port
cannot be forwarded or reused. The Product composition acquires these two fresh
B-specific ports after resolving the same B operation and before lease entry;
failure to acquire either leaves the B lease unentered and every DB delta zero.

The Product composition creates `Task061FinalCaCVerificationLeaseV1` only after
an exact B operation has been resolved. The lease binds action, operation and
plan identities, all dependency receipt identities and generations, disabled
predecessor bytes/physical identity/revision, Product build/image, native
security backend implementation/version, trusted clock policy, owner SID,
session/boot coordinate, expiry, and invocation budget one. Its private state is
`ISSUED -> IN_FLIGHT -> COMMITTED_BURNED`,
`ISSUED -> IN_FLIGHT -> REJECTED_BURNED`, or
`ISSUED -> IN_FLIGHT -> BURNED_UNKNOWN`. Method entry performs the atomic
`IN_FLIGHT` transition. Exact success uses `COMMITTED_BURNED`; a deterministic
post-entry rejection before any namespace effect uses `REJECTED_BURNED` and
`REJECTED_EFFECT0`; exception, timeout, crash, response loss, or any possible
effect uses `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`. Every terminal burns the
budget. Recovery is through the
durable operation state and exact broker-authenticated owner only. Module
sentinels, constructors, copy/replace, pickle, deserialization, subclassing,
duck types, recomputed hashes, and public receipt bodies create zero leases.

`Task061FinalCaCDevelopmentPortV1` exposes only the pinned completion receipt
identity/currentness needed by TASK-065. It exposes no capability, config path,
challenge secret, backend, clock, mutable mapping, or callable and cannot be
passed to an activation apply surface.

### 7.3 Fixed composition, strict reads, and currentness

Production-eligible composition fixes the native TASK-068 security/I/O backend,
trusted clock, Product image/build, and owner/session attestation internally.
Test doubles exist only in a non-Production composition with
`production_eligible=false`. Backend, clock, SID, session, build, or verifier
implementation drift between entry, dependency pinning, receipt publication,
and final readback fails closed; drift after a namespace effect is
`COMPLETION_UNKNOWN` and never automatic retry.

Every durable dependency and B record is read beneath one pinned, attested
ancestor chain by `lstat -> nofollow open -> fstat -> bounded read -> post-fstat`
from the same non-inheritable handle. It must be regular, `nlink=1`,
non-reparse, and physically unchanged. Strict UTF-8 JSON rejects duplicate keys
at every depth, non-finite numbers, BOM, trailing data, invalid UTF-8, controls,
NUL, non-built-in JSON types, unknown fields, and byte/depth/member/item/string
ceilings before canonicalization or hashing. Raw opened bytes hash, canonical
parsed hash, physical identity, ancestor/security snapshot, and semantic
currentness are one sealed private snapshot. Same bytes at another inode are
not equivalent. Errors are stable and body/path/OS-detail free; ambiguous bytes
are preserved and never repaired, rewritten, or deleted.

B uses a dedicated secure existing/initial operation lock and a bounded
operation root under admitted Bridge state. Initial lock creation is
`CREATE_NEW`/nofollow with one byte and same-handle locking; existing lock
requires exact physical/security classification before the same handle is
locked. The operation root, phase records, owned temp, and receipt follow the
TASK-068 secure no-replace/CAS/durability contract. Generic `AtomicJsonWriter`
is not authority proof. Cleanup is limited to the exact current-operation temp
identity; foreign or unknown replacements are preserved.

### 7.4 B durable phase and recovery protocol

The exact monotonic chain is:

```text
0 FINAL_VERIFY_PREPARED
1 B_TICKET_IN_FLIGHT
2 DEPENDENCY_BUNDLE_PINNED
3 REAL_E2E_CORRELATION_VERIFIED
4 DISABLED_PREDECESSOR_VERIFIED
5 COMPLETION_RECEIPT_PENDING
6 COMPLETION_RECEIPT_READBACK_VERIFIED
7 FINAL_CA_C_TERMINAL_COMMITTED
```

The positive linearization order is literal: verification-lease reservation at
phase 1; materialization of one pinned dependency/E2E/predecessor snapshot at
phases 2-4 and of the exact completion-receipt bytes/temp/absence lease at phase
5; completion-receipt no-replace publication, file flush, parent-directory
durability, pinned no-follow exact readback, close, and security currentness
before phase 6; then and only then phase 7. Phase 7 performs no receipt, config,
history, Human, activation, dependency-port, TASK-036, or other authority write.
It records only the already-proven phase-6 receipt identity/body and all-false
completion state.

The B writer accepts only three complete closed schemas:

| Closed schema | Exact required fields |
|---|---|
| `TASK061_FINAL_CA_C_EFFECTS_V1` | `schema_version,message_type,completion_receipt_count,phase_record_count,config_count,history_count,human_consume_count,activation_apply_count,unrelated_overwrite_count,unrelated_delete_count,effects_sha256` |
| `TASK061_FINAL_CA_C_PHASE_V1` | `schema_version,message_type,operation_commitment_sha256,action,ordinal,state,previous_phase_raw_sha256_or_genesis,previous_phase_canonical_sha256_or_genesis,previous_phase_physical_identity_sha256_or_genesis,previous_phase_sha256_or_genesis,verification_lease_sha256,task061_a_currentness_sha256,task036_e2e_currentness_sha256,task067_facade_currentness_sha256,task063_installation_currentness_sha256,task072_binding_currentness_sha256,task071_broker_currentness_sha256,task069_envelope_currentness_sha256,task060_completion_currentness_sha256,disabled_predecessor_sha256,completion_receipt_sha256_or_none,completion_receipt_coordinate_sha256_or_none,completion_receipt_temp_identity_sha256_or_none,completion_receipt_parent_identity_sha256_or_none,completion_receipt_parent_security_sha256_or_none,completion_receipt_absence_lease_sha256_or_none,cumulative_effects,cumulative_effects_sha256,phase_sha256` |
| `TASK061_FINAL_CA_C_COMPLETION_RECEIPT_V1` | `schema_version,message_type,task061_a_receipt_sha256,task061_a_challenge_reservation_sha256,task036_real_e2e_receipt_sha256,task036_operation_sha256,task036_request_sha256,task036_result_sha256,task036_public_receipt_sha256,task036_generic_correlation_sha256,task036_profile_readback_sha256,task036_adapter_build_config_sha256,task036_time_window_sha256,task075_voice_integration_design_sha256,task075_producer_receipt_sha256,task075_native_runtime_receipt_sha256,task075_human_gate_receipt_sha256,task067_facade_receipt_sha256,task063_installation_readback_sha256,task072_instance_binding_sha256,task071_broker_identity_sha256,task071_broker_completion_sha256,task069_identity_envelope_sha256,task060_completion_receipt_sha256,config_predecessor_sha256_or_genesis,expected_config_revision,product_build_sha256,backend_contract_sha256,trusted_clock_policy_sha256,state,real_installed_e2e_verified,generic_correlation_verified,profile_readback_verified,enabled,config_mutated,history_mutated,human_activation_consumed,activation_applied,authority_created,migration_authority,profile_write_authority,human_authority,e2e_authority,config_write_authority,activation_authority,production_activation_authorized,release_authority,deploy_authority,receipt_sha256` |

All fields are required; unknown/duplicate fields reject. Every
`*_sha256_or_none` is a lower-case SHA-256 digest or literal `NONE`; every
`*_or_genesis` is a digest or literal `GENESIS`. The nested
effects object uses the exact DB coordinate order and bounded non-negative
built-in integers. Its `effects_sha256` is also the outer
`cumulative_effects_sha256`; a digest without the exact body rejects.

The constants are exact: `TASK061_FINAL_CA_C_EFFECTS_V1` has
`schema_version=1.0.0` and `message_type=BvpTask061FinalCaCEffects`; and
`TASK061_FINAL_CA_C_PHASE_V1` has `schema_version=1.0.0`,
`message_type=BvpTask061FinalCaCPhase`, and `action=VERIFY_FINAL_CA_C`. The
effects schema and completion receipt have no action field. The completion
receipt constants are `schema_version=1.0.0`,
`message_type=BvpMontageLearningFinalCaCCompletionReceipt`, and
`state=FINAL_CA_C_IMPLEMENTATION_VERIFIED_ENABLED_FALSE`.
For every phase, all fixed dependency/predecessor digests are lower-case 64-hex
and remain byte-identical. Ordinal zero requires `GENESIS` in all four previous-
phase fields; every later ordinal requires the raw/canonical/physical/self-hash
digests of the immediately preceding same-operation phase. `H` below means a
64-hex digest and `N` means literal `NONE`. The six receipt-pending columns are
`receipt_sha256/coordinate/temp_identity/parent_identity/parent_security/absence_lease`.
The `DB` value is cumulative from a fresh B operation.

| ordinal | exact `state` | six receipt-pending fields | cumulative `DB` | exact lease state |
|---:|---|---|---|---|
| 0 | `FINAL_VERIFY_PREPARED` | `N/N/N/N/N/N` | `(0,1,0,0,0,0,0,0)` | `ISSUED` |
| 1 | `B_TICKET_IN_FLIGHT` | `N/N/N/N/N/N` | `(0,2,0,0,0,0,0,0)` | `IN_FLIGHT` |
| 2 | `DEPENDENCY_BUNDLE_PINNED` | `N/N/N/N/N/N` | `(0,3,0,0,0,0,0,0)` | `IN_FLIGHT` |
| 3 | `REAL_E2E_CORRELATION_VERIFIED` | `N/N/N/N/N/N` | `(0,4,0,0,0,0,0,0)` | `IN_FLIGHT` |
| 4 | `DISABLED_PREDECESSOR_VERIFIED` | `N/N/N/N/N/N` | `(0,5,0,0,0,0,0,0)` | `IN_FLIGHT` |
| 5 | `COMPLETION_RECEIPT_PENDING` | `H/H/H/H/H/H` | `(0,6,0,0,0,0,0,0)` | `IN_FLIGHT` |
| 6 | `COMPLETION_RECEIPT_READBACK_VERIFIED` | `H/H/H/H/H/H` | `(1,7,0,0,0,0,0,0)` | `IN_FLIGHT` |
| 7 | `FINAL_CA_C_TERMINAL_COMMITTED` | `H/H/H/H/H/H` | `(1,8,0,0,0,0,0,0)` | `COMMITTED_BURNED` |

Both schemas and the completion receipt use RFC 8785 JCS after strict parsing,
closed-schema/type checks, and resource ceilings. Their nonrecursive terminal
self-hash preimage is exactly:

```text
ASCII("BVP:TASK061:" + CLOSED_SCHEMA_NAME + ":" + schema_version + "\0")
|| UTF8(JCS(object with only phase_sha256, effects_sha256, or receipt_sha256
            omitted for that schema))
```

Only the one terminal self-hash field named by the schema is absent; it is not
empty, zero, or `null`, and every nested body remains present. Wrong domain,
schema/version, omission set, JCS bytes, nested body/hash, or predecessor raw/
canonical/identity/self-hash rejects before the next phase.

`FINAL_VERIFY_PREPARED` is immutable no-replace. Every later phase is immutable
no-replace and binds the exact previous opened bytes, physical identity,
self-hash, ordinal, and full operation vector. Phase 5 binds the canonical
receipt bytes, exact contained coordinate, expected absent target and absence
lease, operation-owned temp identity, parent physical identity, and parent
security before publication. Immediately before no-replace, all five namespace
commitments (coordinate, temp, absence lease, parent identity, parent security)
and every dependency/backend/session input are revalidated from the same pinned
operation. Recovery at phase 5 may classify once: absent publishes that exact
temp no-replace; present at the same bound physical identity and exact bytes
continues to durability/readback; present with another identity/body is
`COLLISION_STOP`, while an ambiguous classification is `COMPLETION_UNKNOWN`.
File flush, directory durability, pinned
reopen, exact readback, close, and security currentness must all succeed before
phase 6. Failure after the namespace becomes visible is
`COMPLETION_UNKNOWN`; it never republishes. Phase 7 is strictly read-only and
may return only the exact same committed event/body/physical identity as
`DUPLICATE_COMMITTED_EVENT`. Different body/identity is collision STOP.

Each row below is one exact collected pytest node. The first authenticated
owner query and the repeated query both execute and are asserted inside that
single listed node; there is no `[case]` alias or dynamically discovered
variant. For ordinals 0..6, the first query consumes one durable
recovery-winner slot, returns the listed outcome, and permits only `next`; the
repeat is read-only, returns the same classification, creates no handle, and
has added `DB=ZB`. Ordinal 7 returns only the exact duplicate. No dependency
port, lease, receipt, or phase is reissued.

| exact pytest node | durable state | cumulative `DB` | lease | first outcome | `next` |
|---|---|---|---|---|---|
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_every_phase_crash_is_exact[B61-J01-p0]` | `FINAL_VERIFY_PREPARED` | `(0,1,0,0,0,0,0,0)` | `ISSUED` | `BROKER_RECOVERY_REQUIRED` | `B_TICKET_IN_FLIGHT` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_every_phase_crash_is_exact[B61-J01-p1]` | `B_TICKET_IN_FLIGHT` | `(0,2,0,0,0,0,0,0)` | `IN_FLIGHT` | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN` | `DEPENDENCY_BUNDLE_PINNED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_every_phase_crash_is_exact[B61-J01-p2]` | `DEPENDENCY_BUNDLE_PINNED` | `(0,3,0,0,0,0,0,0)` | `IN_FLIGHT` | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN` | `REAL_E2E_CORRELATION_VERIFIED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_every_phase_crash_is_exact[B61-J01-p3]` | `REAL_E2E_CORRELATION_VERIFIED` | `(0,4,0,0,0,0,0,0)` | `IN_FLIGHT` | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN` | `DISABLED_PREDECESSOR_VERIFIED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_every_phase_crash_is_exact[B61-J01-p4]` | `DISABLED_PREDECESSOR_VERIFIED` | `(0,5,0,0,0,0,0,0)` | `IN_FLIGHT` | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN` | `COMPLETION_RECEIPT_PENDING` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_every_phase_crash_is_exact[B61-J01-p5]` | `COMPLETION_RECEIPT_PENDING` | `(0,6,0,0,0,0,0,0)` | `IN_FLIGHT` | `BROKER_RECOVERY_REQUIRED -> COMPLETION_UNKNOWN` | phase-5 exact target classification only |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_every_phase_crash_is_exact[B61-J01-p6]` | `COMPLETION_RECEIPT_READBACK_VERIFIED` | `(1,7,0,0,0,0,0,0)` | `IN_FLIGHT` | `BROKER_RECOVERY_REQUIRED` | `FINAL_CA_C_TERMINAL_COMMITTED` |
| `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_every_phase_crash_is_exact[B61-J01-p7]` | `FINAL_CA_C_TERMINAL_COMMITTED` | `(1,8,0,0,0,0,0,0)` | `COMMITTED_BURNED` | `DUPLICATE_COMMITTED_EVENT` | none; winner delta zero |

No phase consumes the A challenge, mutates config/history, applies activation,
writes `enabled:true`, or calls TASK-036 again. A stale dependency or expired B
lease requires a fresh resolver/plan; it is not refreshed in place.

### 7.5 Exact B negative and delta ledger

For B, `DB=(completion-receipt, phase-record, config, history, Human-consume,
activation-apply, unrelated-overwrite, unrelated-delete)` and
`ZB=(0,0,0,0,0,0,0,0)`. Every node below is a separately collected fresh
fixture; aliases, shared mutated fixtures, or omitted cases fail collection.

For the cross-owner consumer-family rows, upstream TASK-060 retains its exact
twelve-coordinate `D=(revision,head,Profile,Human-consume,source-reservation,
source-materialization,completion-receipt,owned-temp,owned-orphan,phase-record,
unrelated-overwrite,unrelated-delete)` and `Z=(0,0,0,0,0,0,0,0,0,0,0,0)`.
`RP=(R61A,R61B,R69)` is the exact triple of TASK-060 producer-owned A receipt-
reader, B receipt-reader, and TASK-069 live-session return-slot budgets. A
cross-family pre-entry rejection requires `D=Z`, `RP=(U,U,U)`, `DB=ZB`, and
zero entry/return/consume/forward/exposure delta; the three budgets are not
interchangeable and no B lease is entered.

Every ledger node also runs the literal leakage oracle over public return,
status, error, exception cause/context, stdout, stderr, Product log, audit log,
operation temp, phase journal, and completion receipt. It asserts zero raw
dependency bytes, payload/body text, absolute/UNC path, account/SID text, token,
secret, OS error detail, or offending value. The only public failure material is
the node's stable outcome token and opaque operation digest. Failure of any one
channel fails that node even when `DB=ZB`.

| Vector | Exact test node | Frozen seam | Outcome / exact delta |
|---|---|---|---|
| B61-Z01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_success_is_exact[B61-Z01]` | exact fresh admitted B operation before phase 0 | `FINAL_CA_C_IMPLEMENTATION_VERIFIED_ENABLED_FALSE`; `DB=(1,8,0,0,0,0,0,0)`; lease `COMMITTED_BURNED` |
| B61-Z02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_terminal_duplicate_matrix[B61-Z02]` | exact terminal event/body/physical identity | `DUPLICATE_COMMITTED_EVENT`; added `DB=ZB`; no port call or lease issue |
| B61-B01 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_dependency_bundle_matrix[B61-B01]` | any required canonical port missing/stale/wrong generation | `DEPENDENCY_NC_EFFECT0`; `DB=ZB`; lease unentered |
| B61-B02 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_public_forgery_matrix[B61-B02]` | direct/copy/replace/pickle/deserialized/public receipt or module sentinel | `REJECTED_EFFECT0`; `DB=ZB`; lease zero |
| B61-B03 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_operation_vector_matrix[B61-B03]` | wrong operation/plan/action/instance/build/backend/user/session/clock | `REJECTED_EFFECT0`; `DB=ZB`; victim lease preserved |
| B61-B04 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_real_e2e_matrix[B61-B04]` | status/code/synthetic/fixture/receipt-only/missing executed request/result/correlation/Profile evidence or TASK-075 role alias/swap/design-SHA substitution | `DEPENDENCY_NC_EFFECT0`; `DB=ZB`; B lease unentered; TASK-036 calls zero; authority zero |
| B61-B05 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_broker_matrix[B61-B05]` | TASK-071 identity/build/session/evidence differs from A or B fresh read | `REJECTED_EFFECT0`; `DB=ZB`; no receipt |
| B61-B06 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_predecessor_matrix[B61-B06]` | disabled predecessor stat-open/read-post swap or same bytes/different inode | `COLLISION_STOP`; `DB=ZB`; config/history preserved |
| B61-B07 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_ticket_matrix[B61-B07]` | missing/expired/replayed/cross-action lease | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `DB=ZB` |
| B61-B08 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_ticket_matrix[B61-B08]` | double/concurrent loser after winner entry | `REJECTED_EFFECT0`; `DB=ZB`; loser budget already zero |
| B61-B09 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_ticket_matrix[B61-B09]` | exception immediately after matched entry | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `DB=(0,1,0,0,0,0,0,0)`; broker recovery only |
| B61-B10-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_recovery_matrix[B61-B10-a]` | phase 5 target absent | `FINAL_CA_C_IMPLEMENTATION_VERIFIED_ENABLED_FALSE`; exact receipt publishes once; added `DB=(1,2,0,0,0,0,0,0)` for phases 6-7; no second publish |
| B61-B10-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_recovery_matrix[B61-B10-b]` | phase 5 exact bound target already present | `FINAL_CA_C_IMPLEMENTATION_VERIFIED_ENABLED_FALSE`; readback-only recovery; added `DB=(0,2,0,0,0,0,0,0)` |
| B61-B10-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_recovery_matrix[B61-B10-c]` | phase 5 different receipt body | `COLLISION_STOP`; `DB=ZB`; foreign target preserved |
| B61-B10-d | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_recovery_matrix[B61-B10-d]` | phase 5 same receipt bytes on a different physical identity | `COLLISION_STOP`; `DB=ZB`; foreign target preserved |
| B61-B10-e | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_recovery_matrix[B61-B10-e]` | phase 5 target classification ambiguous | `COMPLETION_UNKNOWN`; `DB=ZB`; preserve; no publish or retry |
| B61-B11-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_durability_matrix[B61-B11-a-temp]` | temp create/write/flush/identity/close failure before receipt namespace | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; added `DB=ZB`; exact owned cleanup only |
| B61-B11-b0 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_publication_crash_seams_are_literal[B61-B11-b0-prepublish]` | phase 5 exact; coordinate/temp/absence/parent/security currentness fails immediately before no-replace | `COLLISION_STOP`; added `DB=ZB`; receipt/cleanup zero |
| B61-B11-b1 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_publication_crash_seams_are_literal[B61-B11-b1-postpublish-pre-file-fsync]` | receipt namespace visible; file flush not proved | `COMPLETION_UNKNOWN`; added `DB=(1,0,0,0,0,0,0,0)`; no republish |
| B61-B11-b2 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_publication_crash_seams_are_literal[B61-B11-b2-post-file-fsync-pre-directory-fsync]` | receipt file flushed; parent durability not proved | `COMPLETION_UNKNOWN`; added `DB=(1,0,0,0,0,0,0,0)`; no republish |
| B61-B11-b3 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_publication_crash_seams_are_literal[B61-B11-b3-post-directory-fsync-pre-reopen]` | receipt namespace durable; pinned no-follow reopen not proved | `COMPLETION_UNKNOWN`; added `DB=(1,0,0,0,0,0,0,0)`; classify only |
| B61-B11-b4 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_publication_crash_seams_are_literal[B61-B11-b4-post-reopen-pre-readback]` | receipt reopened at bound identity; exact bytes/security not proved | `COMPLETION_UNKNOWN`; added `DB=(1,0,0,0,0,0,0,0)`; preserve |
| B61-B11-b5 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_publication_crash_seams_are_literal[B61-B11-b5-post-readback-pre-phase6]` | receipt exact readback proved; phase 6 absent | `BROKER_RECOVERY_REQUIRED`; added `DB=(1,0,0,0,0,0,0,0)`; append phase 6 only |
| B61-B11-b6 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_publication_crash_seams_are_literal[B61-B11-b6-post-phase6-process-loss]` | exact phase 6 durable; response/process lost | `BROKER_RECOVERY_REQUIRED`; added `DB=(1,1,0,0,0,0,0,0)`; exact phase/bytes/inode/currentness recovery only |
| B61-B11-b7 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_publication_crash_seams_are_literal[B61-B11-b7-post-terminal-process-loss]` | exact phase 7 terminal durable; response/process lost | `DUPLICATE_COMMITTED_EVENT`; added `DB=(1,2,0,0,0,0,0,0)` from phase 5; lease `COMMITTED_BURNED`; strictly read-only |
| B61-B12-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_composition_drift_matrix[B61-B12-a]` | backend/clock/build/user/session drift before lease entry | `REJECTED_EFFECT0`; `DB=ZB`; victim lease remains issued |
| B61-B12-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_composition_drift_matrix[B61-B12-b]` | drift immediately after phase 1 lease entry and before phase 2 | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `DB=(0,1,0,0,0,0,0,0)`; recovery only |
| B61-B12-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_composition_drift_matrix[B61-B12-c]` | drift after receipt namespace becomes visible from phase 5 and before phase 6 | `COMPLETION_UNKNOWN`; `DB=(1,0,0,0,0,0,0,0)`; no republish |
| B61-B13-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_terminal_duplicate_matrix[B61-B13-a]` | exact terminal event/body/physical identity | `DUPLICATE_COMMITTED_EVENT`; added `DB=ZB`; strictly read-only |
| B61-B13-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_terminal_duplicate_matrix[B61-B13-b]` | same terminal event with different body | `COLLISION_STOP`; `DB=ZB`; foreign/current terminal preserved |
| B61-B13-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_terminal_duplicate_matrix[B61-B13-c]` | same terminal event/body on a different physical identity | `COLLISION_STOP`; `DB=ZB`; foreign/current terminal preserved |
| B61-B14 | `tests/test_task061_montage_learning_connector_activation.py::test_task061_b_public_receipt_never_activates[B61-B14]` | B receipt supplied to ACTIVATE/DEACTIVATE/public apply | `PRODUCTION_AUTHORITY_REQUIRED_EFFECT0`; `DB=ZB`; config/history zero |
| B61-B15-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_phase_schema_and_self_hash_are_exact[B61-B15-a]` | exact closed phase/effects body and domain-separated JCS hashes | `PHASE_VALIDATED_EFFECT0`; `DB=ZB`; no next-phase publication in validator fixture |
| B61-B15-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_phase_schema_and_self_hash_are_exact[B61-B15-b]` | malformed/unknown/mismatched phase or effects hash preimage | `STRICT_JSON_REJECTED`; `DB=ZB`; bytes preserved |
| B61-B16-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_self_hash_is_exact[B61-B16-a]` | exact complete receipt and domain-separated JCS self-hash | `RECEIPT_VALIDATED_EFFECT0`; `DB=ZB`; publication zero in validator fixture |
| B61-B16-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_self_hash_is_exact[B61-B16-b]` | exact B effect vector or common ten-field authority tail is missing, extra, defaulted, duplicated, shortened, wrong-type, `null`, true, or has a mismatched receipt hash preimage | `STRICT_JSON_REJECTED`; `DB=ZB`; `EB=(false,false,false,false,false)` and all ten authority fields false; receipt publication/acceptance zero; TASK-065 budget unchanged; bytes preserved |
| B61-B17-a | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_dependency_reader_slots_are_distinct[B61-B17-a]` | exact fresh A-currentness and TASK-060 B-currentness producer slots | `DEPENDENCIES_PINNED_EFFECT0`; `DB=ZB`; each B-bound port returned exact 1; lease unentered |
| B61-B17-b | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_dependency_reader_slots_are_distinct[B61-B17-b]` | double/concurrent loser after either exact producer-slot winner | `REJECTED_EFFECT0`; `DB=ZB`; second port return zero; no forwarding |
| B61-B17-c | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_dependency_reader_slots_are_distinct[B61-B17-c]` | exception/timeout/process-loss/response-loss after either producer-slot entry | `BURNED_UNKNOWN -> COMPLETION_UNKNOWN`; `DB=ZB`; replacement port zero |
| B61-B17-d | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_dependency_reader_slots_are_distinct[B61-B17-d]` | one exact independently parameterized A/B/069 cross-family, receipt-only/live-session, wrong-operation/method, copy, serialize, or deserialize attempt before every victim slot entry | `REJECTED_EFFECT0`; upstream `D=Z`; `RP=(U,U,U)`; `DB=ZB`; all consumer budgets and B lease unchanged; entry/return/consume/forward/exposure delta zero |
| B61-B18 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_post_entry_rejection_burns_deterministically[B61-B18]` | deterministic operation-vector/currentness rejection after atomic lease entry and before any namespace effect | `REJECTED_EFFECT0`; `DB=ZB`; lease `REJECTED_BURNED`; retry/recovery-handle zero |
| B61-B19 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_failure_channels_are_body_free[B61-B19]` | one frozen rejected body containing path/account/token/OS-detail sentinels | stable outcome token only; every named leakage channel zero; `DB=ZB`; bytes preserved only in admitted private dependency evidence |
| B61-B20 | `tests/test_task061_montage_learning_preactivation_operation.py::test_task061_b_receipt_prepublish_bindings_are_current[B61-B20]` | phase 5 wrong coordinate, stale absence lease, foreign temp, parent identity drift, or parent security drift immediately prepublish | `COLLISION_STOP`; `DB=ZB`; receipt namespace/cleanup zero; foreign/current state preserved |

Mandatory in-node case IDs include all dependency names; direct/copy/replace/
pickle/deserialize/module-sentinel/recomputed-hash; wrong operation/plan/action/
instance/build/backend/user/session/clock; status-only/synthetic/receipt-only/
missing-executed/wrong-request/wrong-result/wrong-correlation/wrong-Profile;
broker identity/build/session/evidence drift; stat-open/read-post/ancestor/DACL/
same-bytes-different-inode predecessor drift; missing/expired/replayed/
cross-action/double/concurrent/exception reuse; absent/exact/different/ambiguous
receipt target; temp/write/flush/namespace/directory-durability/reopen/readback/
close/security faults; and pre-entry/post-entry/post-namespace composition drift.

| Umbrella vector | Exact mandatory case IDs |
|---|---|
| B61-B01 | `task061_a`, `task036_e2e`, `task067_facade`, `task063_installation`, `task072_binding`, `task071_broker`, `task069_envelope`, `task060_completion`, `stale`, `wrong_generation`, `cross_instance` |
| B61-B02 | `direct`, `copy`, `replace`, `pickle`, `deserialize`, `mapping`, `module_sentinel`, `recomputed_hash`, `subclass`, `duck_type` |
| B61-B03 | `wrong_operation`, `wrong_plan`, `cross_action`, `wrong_instance`, `wrong_build`, `fake_backend`, `wrong_user`, `wrong_session`, `test_clock`, `phase_clock` |
| B61-B04 | `status_only`, `code_presence`, `synthetic`, `fixture`, `receipt_only`, `missing_executed`, `wrong_request`, `wrong_result`, `wrong_correlation`, `wrong_profile`, `wrong_adapter_build`, `wrong_config_projection`, `wrong_task075_r6_design`, `design_sha_as_producer`, `design_sha_as_native_runtime`, `design_sha_as_human_gate`, `missing_task075_producer`, `missing_task075_native_runtime`, `missing_task075_human_gate`, `same_receipt_cross_role`, `same_receipt_all_three_roles`, `producer_native_swap`, `producer_human_swap`, `native_human_swap`, `wrong_producer_role_tag`, `wrong_native_role_tag`, `wrong_human_role_tag`, `wrong_producer_role_body`, `wrong_native_role_body`, `wrong_human_role_body`, `fixture_task075_gate`, `stale_task075_gate`, `stale`, `expired`, `cross_operation` |
| B61-B05 | `a_broker_identity`, `a_broker_build`, `b_broker_build`, `operation_session`, `evidence_bytes`, `physical_identity`, `same_body_different_inode` |
| B61-B06 | `stat_open_swap`, `read_post_swap`, `same_bytes_different_inode`, `ancestor_swap`, `dacl_drift`, `reparse`, `hardlink`, `revision_drift` |
| B61-B07 | `missing`, `expired`, `replayed`, `cross_action`, `wrong_subject`, `wrong_vector`, `caller_timestamp` |
| B61-B08 | `double_call`, `concurrent_loser`, `same_fields_new_object` |
| B61-B09 | `exception_after_entry`, `timeout_after_entry`, `response_loss_after_entry`, `restart_after_entry` |
| B61-B10-a | `absent` |
| B61-B10-b | `exact_identity_exact_bytes` |
| B61-B10-c | `different_body` |
| B61-B10-d | `same_bytes_different_inode` |
| B61-B10-e | `ambiguous` |
| B61-B11-a | `temp_create`, `temp_write`, `temp_flush`, `temp_identity`, `temp_close` |
| B61-B12-a | `backend_pre_entry`, `clock_pre_entry`, `session_pre_entry`, `build_pre_entry`, `user_pre_entry` |
| B61-B12-b | `backend_post_entry`, `clock_post_entry`, `session_post_entry`, `build_post_entry`, `user_post_entry` |
| B61-B12-c | `backend_post_namespace`, `clock_post_namespace`, `session_post_namespace`, `build_post_namespace`, `user_post_namespace` |
| B61-B13-a | `same_event_same_body_same_identity` |
| B61-B13-b | `same_event_different_body` |
| B61-B13-c | `same_event_different_identity` |
| B61-B14 | `activate`, `deactivate`, `public_apply`, `serialize_then_apply` |
| B61-B15-a | `exact_phase`, `exact_effects_body` |
| B61-B15-b | `missing_field`, `unknown_field`, `duplicate_equal`, `duplicate_different`, `wrong_previous_raw`, `wrong_previous_canonical`, `wrong_previous_identity`, `wrong_previous_self_hash`, `wrong_domain`, `wrong_schema`, `wrong_version`, `wrong_message_type`, `wrong_action`, `wrong_ordinal_state`, `wrong_sentinel`, `wrong_cumulative_db`, `wrong_lease_state`, `wrong_jcs`, `effects_body_mismatch`, `effects_hash_mismatch` |
| B61-B16-a | `exact_receipt` |
| B61-B16-b | `missing_enabled`, `true_enabled`, `missing_config_mutated`, `true_config_mutated`, `missing_history_mutated`, `true_history_mutated`, `missing_human_activation_consumed`, `true_human_activation_consumed`, `missing_activation_applied`, `true_activation_applied`, `missing_authority_created`, `true_authority_created`, `missing_migration_authority`, `true_migration_authority`, `missing_profile_write_authority`, `true_profile_write_authority`, `missing_human_authority`, `true_human_authority`, `missing_e2e_authority`, `true_e2e_authority`, `missing_config_write_authority`, `true_config_write_authority`, `missing_activation_authority`, `true_activation_authority`, `missing_production_activation_authorized`, `true_production_activation_authorized`, `missing_release_authority`, `true_release_authority`, `missing_deploy_authority`, `true_deploy_authority`, `string_false_each_false_field`, `numeric_zero_each_false_field`, `null_each_false_field`, `short_effect_vector`, `short_authority_tail`, `default_inference_attempt`, `unknown_effect_field`, `unknown_authority_field`, `duplicate_equal`, `duplicate_different`, `wrong_domain`, `wrong_schema`, `wrong_version`, `wrong_jcs`, `recursive_self_hash`, `wrong_self_hash` |
| B61-B17-a | `exact_a_and_task060_b_ports` |
| B61-B17-b | `a_double_call`, `a_concurrent_loser`, `task060_double_call`, `task060_concurrent_loser` |
| B61-B17-c | `a_exception`, `a_timeout`, `a_process_loss`, `a_response_loss`, `task060_exception`, `task060_timeout`, `task060_process_loss`, `task060_response_loss` |
| B61-B17-d | `a_to_b_forward`, `b_to_a_forward`, `a_to_069_forward`, `b_to_069_forward`, `069_to_a_forward`, `069_to_b_forward`, `public_receipt_to_a_reader`, `public_receipt_to_b_reader`, `public_receipt_to_069_live_session`, `a_receipt_port_to_069_live_session`, `b_receipt_port_to_069_live_session`, `069_live_session_to_a_reader`, `069_live_session_to_b_reader`, `a_wrong_operation`, `a_wrong_method`, `b_wrong_operation`, `b_wrong_method`, `069_wrong_operation`, `069_wrong_method`, `a_copy`, `a_serialize`, `a_deserialize`, `b_copy`, `b_serialize`, `b_deserialize`, `069_copy`, `069_serialize`, `069_deserialize` |
| B61-B18 | `dependency_drift_post_entry`, `vector_drift_post_entry`, `expired_post_entry` |
| B61-B19 | `public_return`, `status`, `error`, `exception_cause`, `exception_context`, `stdout`, `stderr`, `product_log`, `audit_log`, `temp`, `journal`, `receipt` |
| B61-B20 | `wrong_coordinate`, `stale_absence_lease`, `foreign_temp`, `wrong_parent_identity`, `parent_security_drift` |

The eight full `B61-J01-p0` through `B61-J01-p7` pytest node strings above are
not an umbrella range: collection must contain each literal node exactly once.
Each node itself executes both the first-winner and repeat-query assertions.
Missing one ordinal, splitting either assertion into an unlisted dynamic
variant, sharing a mutated fixture, accepting another `next`, or changing its
cumulative `DB`/lease/outcome fails collection.

`B61-B11-b0` through `B61-B11-b7` are already literal separately collected
pytest nodes in the normative ledger, not umbrella cases. Each node executes one
frozen seam, one first authenticated classification, and one repeat query.
Recovery requires the exact expected phase raw/canonical bytes, phase self-hash,
phase physical identity, receipt bytes and inode, ancestor/security currentness,
dependency vector, and operation binding. Exact terminal state is read-only
duplicate, different body/identity is `COLLISION_STOP`, ambiguous state is
`COMPLETION_UNKNOWN`, and automatic retry, republish, replacement, deletion,
port reissue, lease refund, or TASK-036 reinvocation is zero.

## 8. TASK-061-B development completion receipt

TASK-061-B may publish one immutable, no-replace development completion receipt
only after its exact implementation, focused/fault tests, real installed E2E
dependency verification, and independent DEV-4 gate pass:

```text
TASK061_FINAL_CA_C_COMPLETION_RECEIPT_V1(
  schema_version=1.0.0,
  message_type=BvpMontageLearningFinalCaCCompletionReceipt,
  task061_a_receipt_sha256,
  task061_a_challenge_reservation_sha256,
  task036_real_e2e_receipt_sha256,
  task036_operation_sha256,
  task036_request_sha256,
  task036_result_sha256,
  task036_public_receipt_sha256,
  task036_generic_correlation_sha256,
  task036_profile_readback_sha256,
  task036_adapter_build_config_sha256,
  task036_time_window_sha256,
  task075_voice_integration_design_sha256,
  task075_producer_receipt_sha256,
  task075_native_runtime_receipt_sha256,
  task075_human_gate_receipt_sha256,
  task067_facade_receipt_sha256,
  task063_installation_readback_sha256,
  task072_instance_binding_sha256,
  task071_broker_identity_sha256,
  task071_broker_completion_sha256,
  task069_identity_envelope_sha256,
  task060_completion_receipt_sha256,
  config_predecessor_sha256_or_genesis,
  expected_config_revision,
  product_build_sha256,
  backend_contract_sha256,
  trusted_clock_policy_sha256,
  state=FINAL_CA_C_IMPLEMENTATION_VERIFIED_ENABLED_FALSE,
  real_installed_e2e_verified=true,
  generic_correlation_verified=true,
  profile_readback_verified=true,
  enabled=false,
  config_mutated=false,
  history_mutated=false,
  human_activation_consumed=false,
  activation_applied=false,
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

The fields shown above are the complete required field set: no field is
optional, unknown fields are rejected, and duplicate keys are rejected even
when values are equal. Its `receipt_sha256` uses section 7.4's exact domain-
separated JCS preimage for closed schema
`TASK061_FINAL_CA_C_COMPLETION_RECEIPT_V1`, version `1.0.0`, omitting only
`receipt_sha256`; the final JCS document then includes that lower-case digest.
Every Boolean is a built-in JSON Boolean, every
digest is exactly 64 lowercase hexadecimal characters, and the full ten-field
authority tail is present and false. A shorter transport wrapper, a mapping
with equal values, or a reserialized body is not this receipt.

The independently closed B effect vector is exactly
`EB=(enabled,config_mutated,history_mutated,human_activation_consumed,activation_applied)`
`=(false,false,false,false,false)`. Immediately after it, the ordered authority
tail is exactly:

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

This is the same ten-field tail, names, order, built-in Boolean types, and fixed
values as `TASK061_PREACTIVATION_PREPARE_RECEIPT_V2`. There is no alias,
optional member, default inference, shorter wrapper, or authority-bearing
variant. Missing/extra/duplicate fields, `null`, numeric zero, string `"false"`,
a shortened tail, or any `true` effect/authority member is
`STRICT_JSON_REJECTED` before receipt publication or acceptance.

For `REJECTED_EFFECT0`, `DEPENDENCY_NC_EFFECT0`, `COLLISION_STOP`, or
`COMPLETION_UNKNOWN`, no hostile receipt body is projected as a result. The
exact already-durable seam is preserved, but `EB` and the ten-field authority
tail remain all false; Profile/config/history/Human/activation and unrelated-
file deltas are zero; and every downstream TASK-065 consumer budget remains
unchanged. A B verification lease already entered at the named seam may remain
burned exactly as the ledger states; it is not a downstream consumer budget and
is never refunded, forwarded, or converted into authority.

The twelve TASK-036 component digests must equal the corresponding fields inside
the same pinned `task036_real_e2e_receipt_sha256` body; they cannot be supplied
from separate public objects or normalized to agree. The time-window commitment
binds executed/observed/expiry plus trusted boot/session clock coordinates, and
the challenge-reservation digest must equal the reservation pinned through the
same TASK-061-A currentness port. Any mismatch is dependency N.C. or collision
according to the frozen physical state, never a partially verified receipt.

`task075_voice_integration_design_sha256` is the lower-case normalization of
binary digest
`6F6F52F9294B1838C7A282EB830635743FB3F5FF5A727B3DABE119513B9DF279`.
The producer, native-runtime, and Human-Gate receipt digests must identify three
separate current non-fixture receipts inside the same TASK-036 opened snapshot.
The R6 design digest alone satisfies none of them.

The three `*_verified=true` fields are bounded evidence facts, not authority.
They may be true only because the trusted verifier re-read the canonical
receipts and durable state; a caller cannot set them. Every authority/effect
field remains false.

This receipt may feed TASK-065 completion accounting. It cannot feed an
activation apply surface, mint a Human receipt, issue a ticket, or select a
security backend/clock/config path.

### 8.1 Closed B receipt validator fixture

`TASK061_FINAL_CA_C_COMPLETION_RECEIPT_VALIDATOR_FIXTURE_V1` contains every
field from the section 7.4 closed receipt schema exactly once and in that
declared construction order. Its positive body is exactly the receipt block in
section 8: the three evidence predicates are literal `true`, `EB` is five
literal `false` values, and the common ten-field authority tail is ten literal
`false` values in the same order as A. It is validation-only and creates no
receipt, lease, port, consumer budget, or authority.

Each negative fixture changes one field or one closed-schema property only. It
includes missing/true/string/numeric/null variants for every `EB` and authority-
tail member, duplicate-equal/different, unknown effect/authority fields, short
effect vector, short authority tail, default-inference attempt, wrong
schema/message/state, and wrong self-hash/JCS cases. An omitted case, field-list
length mismatch, changed declared order in fixture construction, shared mutated
fixture, or umbrella default is not an equivalent oracle.

## 9. Separate Production Activation Human Gate

Actual Production Activation is a new runtime operation and requires fresh
authority after TASK-061-B completion. The Gate is outside this amendment and
must independently bind:

- a fresh Product-authored operation request and random challenge;
- current owner/user/session/process and trusted clock;
- exact current installed instance, source/Profile/facade/E2E state;
- exact current disabled config/history predecessor;
- current Product build and native backend identity; and
- one explicit Human-visible decision for that exact event.

The A challenge reservation is not itself a Human decision. A future operation
may enter it only when the exact challenge is still current and a new explicit
Human event is bound by the separate Gate; expiry or drift requires a fresh A
plan rather than reissue or time extension. The operation cannot reuse the A
receipt, the B completion receipt, a development/native test event, or a
previous Human decision as Production authority. It must consume its private
capability at entry and burn it on success, rejection, exception, timeout,
crash, or unknown completion.

This amendment does not define permission to run that operation. Production
Activation remains effect zero until its separate Human Gate and explicit
runtime authority are satisfied.

## 10. Closed outcome partition

TASK-061-A current pre-canonical contract outcome:

```text
CONTRACT_NOT_CANONICAL_EFFECT0
```

TASK-061-A proposed future public outcomes after separate contract
canonicalization:

```text
DEPENDENCY_NC_EFFECT0
STALE_FRESH_PLAN_REQUIRED_EFFECT0
REJECTED_EFFECT0
COLLISION_STOP
PREACTIVATION_READY_ENABLED_FALSE
COMPLETION_UNKNOWN
```

TASK-061-B development outcomes:

```text
DEPENDENCY_NC_EFFECT0
STALE_FRESH_PLAN_REQUIRED_EFFECT0
REJECTED_EFFECT0
COLLISION_STOP
FINAL_CA_C_IMPLEMENTATION_VERIFIED_ENABLED_FALSE
COMPLETION_UNKNOWN
```

Neither outcome set contains `ACTIVATED`, `ENABLED`, `AUTHORIZED`, or a
Production-success value.

## 11. Fault, replay, and negative contract

The partition cannot pass without focused negatives for:

- direct/relabelled/copied D2S receipt presented to TASK-061-A or TASK-060;
- copied or installed SKILL hash/source/tree/receipt presented as installed
  instance, runtime, broker, executed-operation, or real-E2E evidence;
- missing/wrong/stale TASK-069 envelope or TASK-060 completion receipt;
- TASK-070/TASK-063/TASK-072 chain substitution or cross-instance replay;
- missing/wrong/stale TASK-071 durable A binding, broker implementation/build
  drift, operation/session mismatch, or B fresh verifier/completion mismatch;
- proposed `TASK061_PREACTIVATION_PREPARE_RECEIPT_V2` accepted, published, or
  consumed before its exact contract becomes canonical;
- any A/B all-false authority/effect member omitted, set true, given a wrong
  built-in type, duplicated, or hidden behind a shorter wrapper;
- direct/copy/replace/pickle/deserialized A or B receipt;
- A receipt same body at a different physical identity;
- A candidate or challenge swap, replay, expiry, backend/session/clock drift;
- B receipt wrong A/036/067/063/072/069/060 identity or generation;
- TASK-036 status-only, synthetic, receipt-only, missing execution, wrong
  request/result, wrong correlation, wrong Profile, wrong build/config/instance,
  stale/expired, or cross-operation evidence;
- config/history predecessor changed between A, TASK-036, and B;
- B verifier exception before/after each durable read and receipt publication;
- B public receipt supplied to any activation surface;
- Production Activation attempted without a new exact Human Gate; and
- concurrent/replayed A, B, or future activation calls.

### TASK-069 M2: application-composition identity at READY-03

This is a non-effect cross-contract design delta for the TASK-069 owner before
its U6 readiness compiler work. It neither transfers TASK-069 ownership to
TASK-061 nor changes either Task's Allowed Files. TASK-069 source/schema/test
mutation remains outside this packet.

The compiler must obtain one pinned, sealed `APPLICATION_COMPOSITION_V2`
receipt, denoted `C`, through the Product application-composition owner. These
three values must be byte-for-byte equal lower-case SHA-256 digests:

```text
TASK058_BASELINE_READBACK_V2.application_gate_receipt_sha256
    == C.receipt_sha256
    == ConnectorReadinessV2.application_composition_sha256
```

Both public fields represent that same sealed `C.receipt_sha256`; neither is a
second body hash, caller coordinate, independently recomputable authority, or
permission to reopen a path. The readiness compiler verifies the baseline,
live sealed composition, and readiness projection in one private composition.
It never normalizes, copies, substitutes, or rewrites one digest to make the
three values equal.

READY-03 must include an exact `cross_composition_mismatch` case in which every
other dependency and applicability field is valid, but the baseline references
sealed composition `C1` and the readiness input references `C2`. Its fixed
classification is exactly:

```text
overall_state=BLOCKED
reason_codes=[ACTION_DEPENDENCY_BINDING_MISMATCH]
```

The reason array remains ASCII-sorted and unique. A genuinely absent live
composition continues to use `APPLICATION_COMPOSITION_MISSING`; it is not the
cross-composition mismatch case. Same public body at another sealed receipt
identity, copied/rehashed composition evidence, baseline/readiness cross-swap,
or phase drift is the mismatch case and cannot reach `AUDIT_READY`.

Every READY-03 mismatch has compiler publication, owner calls, bridge import,
Profile, config/history, enabled, activation, native, and unrelated-file deltas
exactly zero. This paragraph closes the R10 Medium design specification only;
U6 implementation, tests, canonical publication, and Production effects remain
separately gated.

Every rejection asserts:

```text
migration_delta=0 unless the exact CA-A terminal was already committed
profile_delta=0
config_delta=0
history_delta=0
enabled_true_count=0
human_activation_consume_count=0
activation_apply_count=0
unrelated_overwrite_count=0
unrelated_delete_count=0
```

An already committed exact A/B public receipt may be returned read-only only for
the same event/body/physical identity. Different body or identity is collision
STOP. Unknown completion never triggers automatic retry or fresh execution.

## 12. Critic severity Gates

The following are Critical findings:

- a public A/B receipt can mint or substitute for a private capability;
- D2S bypass reaches TASK-060 or TASK-061 effects;
- SKILL-D2S or TASK-069 is treated as a producer of installed/runtime/broker/
  executed-operation/real-E2E evidence;
- TASK-061-B or its receipt can activate Production without the separate Human
  Gate;
- any route writes `enabled:true` during A/B design or completion execution;
- fixture/status/code-presence evidence is promoted to real E2E; or
- stale/cross-instance evidence can mutate config/history.

The following are at least High findings:

- missing direct producer/consumer identity or physical-currentness binding;
- conflation of TASK-069 envelope and TASK-060 completion;
- A/B receipt omits any all-false authority/effect field;
- the A and B receipt schemas, constructor-shaped text, validators, ledgers, or
  fixtures disagree in any false-vector field name, count, order, built-in type,
  fixed value, or rejection outcome;
- `P60-R06` and `B61-B17-d` omit either direction of an A/B/069 forward, permit
  receipt-only/live-session substitution, or do not preserve exact upstream
  `D=Z`, `RP=(U,U,U)`, B `DB=ZB`, and every victim budget/delta;
- A or B reaches terminal before its completion receipt has durable no-replace
  publication and exact pinned readback, a terminal phase performs any authority
  write, or any pre/post publish/file-fsync/directory-fsync/readback/process-loss
  seam is hidden in an umbrella rather than one literal crash node with exact
  recovery identity/currentness;
- the proposed A receipt is described or consumed as canonical before the exact
  contract and trusted producer are canonical;
- A omits durable TASK-071 broker identity/currentness binding, or B omits its
  fresh TASK-071 verifier/completion and exact equality to A;
- TASK-036 receipt lacks executed operation/correlation/Profile/build/config/
  instance binding;
- B completion is claimed before exact real E2E currentness; or
- Production Activation is described as an implicit continuation of B.

Independent Critic and Judge require Critical/High `0/0` on one frozen identity.

## 13. Acceptance

This limited partition design is complete only when:

1. CA-A/CA-B/CA-C ownership remains exactly TASK-061 and historical records are
   not rewritten.
2. A owns corrected CA-A, corrected CA-B, and CA-C disabled preactivation only.
3. `TASK061_PREACTIVATION_PREPARE_RECEIPT_V2` remains a proposed future
   contract with `CONTRACT_NOT_CANONICAL_EFFECT0` until separately canonical;
   after canonicalization, A's only positive state may be
   `PREACTIVATION_READY_ENABLED_FALSE` with all authority/effect fields false.
4. D2S terminates at TASK-069; TASK-069 envelope and TASK-060 completion are
   separate canonical Gates.
5. Before contract canonicalization, A receipt publication and consumer
   acceptance are zero. Afterwards, A receipt consumers are limited to
   dependency/audit use by TASK-067/TASK-036.
6. A durably binds exact TASK-071 broker identity/currentness, and B starts only
   after exact TASK-036 own executed-operation real installed E2E receipt chain
   and freshly revalidates TASK-071 completion plus every other listed
   dependency/currentness coordinate.
7. B's only positive development state is
   `FINAL_CA_C_IMPLEMENTATION_VERIFIED_ENABLED_FALSE` with every authority and
   activation effect false.
8. B receipt is TASK-065 completion evidence only and is never an activation
   capability.
9. Production Activation is a separate fresh Human Gate and remains unexecuted.
10. Config/history revision delta and `enabled:true` count are zero for all A/B
    design, test, review, and completion-receipt work.
11. Dependency N.C. is never converted to PASS by a fixture or public receipt.
12. Required focused/fault/replay tests pass on one frozen source/test identity.
13. Independent DEV-4 Critic/Tester/Judge return PASS with unresolved C/H `0/0`.
14. Allowed Files, ownership, dirty/overlap, and main currentness are freshly
    rebound before any future source/test mutation.
15. No Release, Deploy, installed mutation, Provider, native Production effect,
    or Production Activation occurs.
16. TASK-069 READY-03 binds baseline and readiness composition fields to the
    same sealed `APPLICATION_COMPOSITION_V2.receipt_sha256`; the isolated
    cross-composition case is `BLOCKED` with only
    `ACTION_DEPENDENCY_BINDING_MISMATCH` and every effect zero.
17. B accepts only the exact private one-use verification lease and live trusted
    ports; entry burns the lease and public/copy/serialized evidence creates no
    lease.
18. B uses the exact eight-record phase chain, publishes its development receipt
    before terminal, treats terminal as read-only, and has a literal recovery
    oracle for every pre/post namespace fault seam.
19. Every B ledger node independently asserts config/history/Human-consume/
    activation/unrelated overwrite/unrelated delete delta zero.
20. TASK-036/voice composition binds exact TASK-075 R6 design SHA plus distinct
    current producer/native/Human receipts; design-only evidence leaves B
    dependency N.C. and creates no authority.
21. A and B carry the same ordered ten-field all-false authority tail. Their
    separate effect vectors, closed schema rows, receipt text, validator
    fixtures, negative ledgers, and case lists agree exactly; missing, extra,
    defaulted, shortened, wrong-type, `null`, or true fields reject with receipt
    publication/acceptance zero and downstream consumer budgets unchanged.
22. `P60-R06` and `B61-B17-d` execute the identical closed set of bidirectional
    A/B/069 forward, receipt-only/live-session, wrong-operation/method, copy,
    serialize, and deserialize cases. Every case is `REJECTED_EFFECT0` with
    upstream twelve-coordinate `D=Z`, `RP=(U,U,U)`, B `DB=ZB`, unchanged victim
    budgets, and Profile/config/history/Human/activation/unrelated-file deltas
    zero.
23. A and B preserve the literal reservation -> materialization -> completion-
    receipt durable publish/readback -> terminal order. Terminal authority writes
    are zero. Every named publication/durability/readback/process-loss seam is a
    separately collected literal node; recovery accepts only exact phase bytes,
    self-hash, inode, target bytes/identity, ancestor/security currentness, and
    operation binding, with duplicate read-only, collision STOP, and automatic
    retry zero.

## 14. Design receipt template

```text
task: TASK-061
unit: CA_A_B_C_LIMITED_PARTITION_AMENDMENT_DESIGN
amendment_identity: TASK061-CAABC-LIMITED-PARTITION-V5
base: origin/main@19c37245a1444f6f3ed5f3b707eeea94e68602b0
allowed_file: docs/ai-team/tasks/TASK-061/ca-a-b-c-limited-partition-amendment-design.md
historical_task_overwrite: false
task061_a_state: CONTRACT_NOT_CANONICAL_EFFECT0
proposed_future_task061_a_state: PREACTIVATION_READY_ENABLED_FALSE
task061_b_state: FINAL_CA_C_IMPLEMENTATION_VERIFIED_ENABLED_FALSE
preactivation_receipt_contract_status: CONTRACT_NOT_CANONICAL_EFFECT0
task071_broker_status: DEPENDENCY_NC_EFFECT0
task069_dependency_status: CANONICAL_RECEIPT_MISSING_EFFECT0
task069_m2_ready03_design_delta: SPECIFIED_U6_SOURCE_START0
task036_real_e2e_status: DEPENDENCY_NC_EFFECT0
production_activation_gate: SEPARATE_NOT_AUTHORIZED
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
source_effect: 0
schema_effect: 0
test_effect: 0
native_effect: 0
config_history_effect: 0
activation_effect: 0
release_deploy_production_effect: 0
review_target_range: bytes[0,72292)
review_target_sha256: 0b4575b4f9584abeae085659dcad248e4926c03a3fa9406208eb5cd3d9974f2b
review_target_lines: 1090
review_target_lf_count: 1090
review_target_bytes: 72292
review_manifest: docs/ai-team/tasks/TASK-061/l2-coordinated-corrective-design-review-manifest.md
review_tuple_sha256: 2429ef29d7a2c3eb484b78c026c3365f38963d03b6ab7d1f534544bb3ee23160
critic: PASS_L_R2_V7_C_H_M_L_0_0_0_0_task061_l2_r3_sol_critic
tester: PASS_L_R2_V7_C_H_M_L_0_0_0_0_task060_r4_sol_tester
judge: PASS_L_R2_V7_C_H_M_L_0_0_0_0_task060_061_v7_independent_judge
design_frozen: true
technical_prefix_frozen: true
receipt_admin_only_mutable: true
```

No source/test/schema/native work or implementation PR may begin from this
draft. After the exact coordinated L2 document set has independent Critical/
High `0/0` and Judge PASS, one docs-only Draft PR may carry that reviewed set;
it creates no implementation authority. A later implementation start requires
canonical dependency receipts, exact Allowed Files, fresh main/worktree/dirty/
overlap/lock proof, and its own DEV-4 review.
