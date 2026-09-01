# TASK-074 Complete Design Packet R14 Addendum

Status: `DESIGN_CANDIDATE_R14_ADDENDUM / DEV-4 / SOURCE_START0 / EFFECT0 / NOT_REVIEWED`

## 1. Frozen parent, source readback and precedence

The effective R14 candidate is the immutable R9-R13 chain plus this limited
TASK-074 owner-side producer amendment. The frozen Git-blob SHA-256 inputs are:

- current authority `task.md`: `838349D63E6A390727BE58EB7B887372C34BFB7AA2A7E733BF8BE6AE3A945CA5`;
- R9 packet: `4F1B127F34C1B61D191F8E17485DCC38F08AC991544C554C0AC3AF346EC95CF0`;
- R10 addendum: `EF9CEA3DF0B4C86ABC0A2198E45F08A368DB0E50A99231744A81BA6014131364`;
- R11 addendum: `CD73E8C6584C96B39D68C3A0D32E635DEC17EFC98145C7344779816400397690`;
- R12 addendum: `38FB784A74C7A51397B3B4243566F62CB87B4CF49AAB7724986061B65DF54687`;
- R13 addendum: `E49E35DBA314EA8D170AE182DA5983D2703DBD9E103BD387AFC32EEE03132FF5`;
- exact design base: `origin/main@354ea2534ad5739a099d9eeaf0f1da9a7210ddb6`.

The cross-owner readback is deliberately asymmetric:

- canonical TASK-076 packet on this base: SHA-256
  `AA86CF218176AD127C1A04BFEC5FD4C7C2A53B33119F0E88F44560109CE616F1`;
- TASK-072 Draft branch `52203bc9962340016f4b7ac494ea02d25202484d`, packet SHA-256
  `4F6F21E97D96AA3FFCA16F57679ABF80D081DE6D85D599347FD955C8899CE3C7`;
- TASK-075 R6 dirty design input at dedicated-worktree HEAD
  `76652c5954e11166f91415d5adb7bb80dd648650`, exact 1865-line packet SHA-256
  `6F6F52F9294B1838C7A282EB830635743FB3F5FF5A727B3DABE119513B9DF279`.
  The packet itself declares `INDEPENDENT_REVIEW_PENDING`,
  `review_target_sha256=PENDING_R6` and `design_frozen=false`. External readback
  confirms that the content-review target exactly matched these bytes and
  reported `PASS_DESIGN_ONLY`, `Critical/High/Medium/Low = 0/0/0/0`, but no
  repository-local immutable verdict receipt binds that result. Thus content
  review is matched while durable review acceptance remains `NOT_CONFIRMED`; the
  dirty file remains read-only preserved input.

TASK-076 defines the generic V3 external-binding slot, but intentionally does
not define TASK-074 producer semantics. The reviewed TASK-072 Draft registry
contains no Owner Voice bind/preflight/recovery profile. TASK-075 R6 remains an
unaccepted design-only consumer input. Its proposed V1 terminal union is useful
contradiction evidence, not an accepted cross-owner contract. Their names,
generic placeholders or equal hashes cannot be treated as TASK-074 owner
acceptance.

R14 supersedes only these earlier inferences:

1. R10 section 4 and R11 section 3 must not infer a TASK-076-owned
   `TASK076_OWNER_VOICE_WORKER_PROCESS_READBACK_V1` or
   `TASK076_EXACT_CHILD_JOB_CUSTODY_READBACK_V1`. In canonical V3, TASK-072 owns
   bootstrap process creation and the sole containment Job handle; TASK-076 owns
   selected Job currentness and the generic external-binding slot.
2. R10/R11 child binding, preflight, normal close and recovery language is
   narrowed to the exact producer ABIs in this addendum.
3. R12 F34 and every R10-R13 close/effect-zero claim consume the exact R14
   readbacks. Generic Task names, public receipts or reconstructed mappings are
   insufficient.
4. R11's "one transaction outcome" is a single caller-visible Task-072 V3
   issue-and-arm operation with a recovery-closed two-owner participant protocol;
   it is not a cross-owner datastore transaction or a lock spanning TASK-072 and
   TASK-074.

R9-R13 lifecycle, joint V1/V2 fence, issue/revoke/expiry arbitration, terminal
retirement and immutable history remain unchanged. This candidate creates no
source, schema, test, process, filesystem, private-audio, model, commit, push,
Release, Deploy or Production authority.

## 2. Decision and responsibility correction

TASK-074 owns the only producer surface that may transfer its prepared reference
roles into an already-created TASK-072 V3 bootstrap child. TASK-072 owns the
live containment Job handle, fixed owner adapter, ticket/abort transaction and
the five-budget V3 vector. TASK-076 owns durable Job/current-generation
selection and custody readback plus the `TASK076_EXTERNAL_BINDING_SLOT_V1`
metadata coordinate; its custody readback never conveys or duplicates the live
Job handle. TASK-075 owns the packaged worker, later consumer admission and
inference.

The exact sequence is:

```text
R12 V2 issue
-> R11 attachment ISSUED (no child/bind effect)
-> TASK-066 exact private compute/network-disabled receipt and capability
-> TASK-072 exact one-use ticket/profile
-> one caller-visible TASK-072 V3 issue-and-arm operation durably reserves the
   ticket/vector, executes the exact TASK-074 begin-arm participant transition,
   then commits the joint R11 begin nonce/V2 parent-delegation outcome
-> TASK-072 JOB_CHILD_ARMED_READBACK_V3
-> TASK-043-selected TASK-076 IN_FLIGHT
-> TASK-072 JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3
-> TASK-074 child-bind delegation and direct two-role transfer
-> TASK-072 record_job_child_external_binding_v3
-> TASK-074 body-free child preflight
-> TASK-072 validate_job_child_external_input_v3
-> TASK-072 Artifact-prepare/release winner
-> TASK-075 execution admission and only then possible BODY_READ_STARTED
```

The compute/launch order is one-way: TASK-066 proves the current bounded compute
and network-disabled policy, TASK-072 consumes that exact producer binding while
issuing/burning the one-use operation, and only the fixed TASK-075 packaged
worker may later enter consumer code. TASK-074 binds those receipt identities in
its operation lineage but cannot mint, consume out of order or replace any of
them.

R11 atomic begin and canonical V3 issue-and-arm are one serialized,
caller-visible TASK-072 operation for this profile, not two ticket consumptions.
Internally it is a recovery-closed coordinator/participant protocol:

1. TASK-072 durably consumes the ticket into one private `ARM_PREPARED`
   coordinate whose process-create and every later budget remain locked;
2. TASK-074 consumes the exact attachment and CASes
   `ISSUED -> IN_FLIGHT_PARENT_DELEGATION` in one owner-domain transaction,
   returning `TASK074_REFERENCE_BEGIN_ARM_READBACK_V1`;
3. TASK-072 commits `JOB_CHILD_ARMED_READBACK_V3` only from that exact owner
   readback and the same prepared vector.

No writer lock spans the two owners. Reply loss queries the exact `BEGIN_ARM`
ledger. If TASK-074 did not enter, TASK-072 closes the reserved vector and the
owner uses only the exact begin-arm containment ABI below. If the
owner commit is proven, TASK-072 may only finish or terminalize that same vector;
it cannot issue another ticket or ask TASK-074 to begin again. If either durable
truth is ambiguous, process creation remains impossible, the vector becomes
`BURNED_UNKNOWN`, and TASK-074 enters same-operation recovery. A pre-arm
standalone begin, a second begin after ARMED or an attachment-only arm is
invalid.

The participant entry is exact and private:

```text
begin_reference_for_task072_arm_v1(
    live TASK074_REFERENCE_BEGIN_ATTACHMENT_V1,
    TASK074_REFERENCE_BEGIN_ARM_REQUEST_V1,
    live OWNER_VOICE_AGGREGATE_CURRENTNESS_LEASE_V1,
    live TASK071 OWNER_VOICE_LOCAL_INFERENCE_V1 | NOT_REQUIRED
) -> TASK074_REFERENCE_BEGIN_ARM_READBACK_V1 | OUTCOME_NOT_CONFIRMED
```

Before the owner CAS, the adapter authenticates the Task-072 prepared-vector
channel, matches attachment/ticket/operation, validates the live Human action
when `human_action_mode=REQUIRED`, and pins the exact G13 lease in `ACTIVE` at
the generation/fingerprint carried by the request. `NOT_REQUIRED` requires
`human_action_state=NOT_REQUIRED` and
`human_action_fingerprint_sha256=ZERO_SHA256`; `REQUIRED` requires
`human_action_state=ISSUED` and forbids the sentinel.
R14 consumes neither live object. The Human action remains one-use for the
existing TASK-075 inference admission, and the aggregate lease remains `ACTIVE`
through TASK-075 authenticated entry and exact input-handle pin, after which its
existing owner releases it. Abort/containment invokes the existing burn/release
path. TASK-074 may only validate their nonextractable broker identities and can
never reconstruct them from the request digests.

The begin readback combinations are closed. `COMMITTED` requires attachment
`CONSUMED`, V2 `IN_FLIGHT_PARENT_DELEGATION`, a nonzero begin nonce,
`stable_reason=NONE` and one `V2_PARENT_DELEGATION_BEGIN` edge from `ISSUED`.
`REJECTED_KNOWN` requires attachment and V2 terminal states both
`BURNED | FAILED_CLOSED`, `begin_nonce_sha256=ZERO_SHA256`, a non-`NONE` stable
reason and the matching single `V2_BURN | V2_FAIL_CLOSED` edge. Any uncertainty
about request entry, attachment consumption or canonical CAS produces no begin
readback and is recovered only through the exact ledger query/containment path.

If Task-072 closes/burns the prepared vector before joint ARMED, the sole
owner-side containment entry is:

```text
contain_reference_begin_arm_v1(
    TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_REQUEST_V1
) -> TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_READBACK_V1
```

It accepts only an exact Task-072 pre-effect, arm-prepared or prebootstrap
terminal proving process create and remote-role transfer never entered. The
request carries one exact predecessor tuple:

- attachment `ABSENT_PROVEN` plus V2 lease `ISSUED` when the owner broker proves
  no attachment was issued; its predecessor-identity union is exactly
  `ABSENT/ZERO_SHA256` because no R11 identity or nonce exists;
- attachment `ISSUED` plus V2 lease `ISSUED` when the begin participant did not
  commit; its predecessor-identity union is `PRESENT/nonzero` and binds the exact
  issued R11 attachment identity; or
- attachment `CONSUMED` plus V2 lease `IN_FLIGHT_PARENT_DELEGATION` when the
  begin participant committed but the final Task-072 arm did not become a usable
  forward vector; its predecessor-identity union is `PRESENT/nonzero` and binds
  that same consumed R11 attachment identity.

An absent attachment identity is never planned, derived from the operation, or
represented by a fabricated nonce. Conversely, `ISSUED | CONSUMED` cannot use
the zero sentinel or a different present identity. The discriminant, predecessor
state, private broker history and canonical lease coordinate must all agree.

`PRE_ARM_REJECTED` requires both `task072_arm_prepared_state` and
`begin_arm_attempt_state` to be `ABSENT_PROVEN`, a `NOT_APPLICABLE`
owner-ledger query and one of the first
two tuples. Every other terminal kind requires a present ARM_PREPARED coordinate,
a `REQUESTED` begin attempt and an exact `NOT_ENTERED | COMMITTED | AMBIGUOUS`
BEGIN_ARM query. `NOT_ENTERED` permits only the first two tuples; `COMMITTED`
requires the consumed/in-flight tuple. `AMBIGUOUS` is not absence: containment
may confirm only if the private attachment broker and canonical
ReferenceDomainSnapshot independently prove one compatible tuple and terminal
edge; otherwise every terminal observation remains `NOT_CONFIRMED`.

The method may close only the two original producer roles. An `ISSUED`
attachment becomes `BURNED | FAILED_CLOSED`; `ABSENT_PROVEN` stays absent and a
`CONSUMED` attachment remains consumed. In the same TASK-074 broker/domain CAS,
the exact V2 lease commits one `V2_BURN | V2_FAIL_CLOSED` edge from the tuple's
canonical predecessor. It cannot bind/preflight/contact a child, synthesize
ARMED, rewrite attachment history or claim an unknown canonical edge.

Generation 1 requires `previous_containment_readback_sha256=ZERO_SHA256`.
A later generation is an explicit same-operation continuation against the exact
previous readback and may touch only parent rows still `UNKNOWN`; confirmed rows
are immutable. It is not a new begin/budget/ticket. `CONTAINMENT_CONFIRMED`
requires both rows closed, parent count zero, the exact predecessor-compatible
attachment terminal observation, lease terminal and a committed canonical
terminal edge. It also requires the echoed nonzero Task-072
no-process/no-transfer proof and both fixed remote-role rows
`ABSENT_PROVEN`; those rows are proven from the terminal/broker lineage without
contacting a child. Otherwise outcome, parent/remote/lease/edge truth and every
unproven attachment observation remain `OUTCOME_NOT_CONFIRMED`/`NOT_CONFIRMED`, and
Task-072 keeps the vector BURNED_UNKNOWN.

TASK-074 never receives the TASK-072 containment Job handle, never selects a
PID/process by caller data and never advances TASK-076 Job currentness. TASK-072
and TASK-076 cannot open, copy, validate semantically or revoke the Owner body by
themselves. The fixed Task-072 adapter validates exact TASK-074 readbacks; it
does not reimplement them.

### 2.1 R13, G01-G14 and domain-transaction crosswalk

R14 does not create a second authority store or transaction owner. Every forward
method revalidates the exact canonical R12/R13
`ReferenceDomainSnapshot.snapshot_sha256`, `fence_sha256`, `fence_revision` and
`committed_event_sha256`; post-arm methods also revalidate the exact
Task-043/Task-076 durable generation. Any method that changes V2 state commits
its producer subledger event and the next canonical ReferenceDomainSnapshot in
one TASK-074 broker/domain CAS. Its readback binds the exact predecessor/result
snapshot/fence/event edge. Before-predecessor reject has canonical and producer
delta zero; there is no second V2 state or owner-only V2 mutation. The
BURNED_UNKNOWN recovery exception is closed in section 8: it binds
the immutable original vector and may contain it after a later current Job-head
advance, but that later head supplies no effect authority. The forward ordering
is:

`TASK074_REFERENCE_DOMAIN_COORDINATE_V1` is a closed body-free projection of
that source object, not another store. Source
`v2_terminal_history_sha256=None` maps only to
`v2_terminal_history_state=ABSENT` plus `ZERO_SHA256`; a non-null source digest
maps only to `PRESENT` plus the exact digest. Every terminal source edge requires
result live-handle count zero and a newly appended non-null V2 terminal history;
the later R13 retirement clears the current V2 identity through its separate
canonical transition without changing that immutable history.

- begin-arm `COMMITTED` records exactly
  `V2_PARENT_DELEGATION_BEGIN: ISSUED -> IN_FLIGHT_PARENT_DELEGATION`;
  `REJECTED_KNOWN` instead records one exact `V2_BURN | V2_FAIL_CLOSED` edge
  and cannot carry a begin nonce usable by Task-072;
- bound success records, in order,
  `V2_CHILD_TRANSFER_BEGIN: IN_FLIGHT_PARENT_DELEGATION -> CHILD_TRANSFER_IN_FLIGHT`
  and `V2_CHILD_PAIR_READY: CHILD_TRANSFER_IN_FLIGHT -> CHILD_PAIR_READY`;
  failed-known bind records only the first edge;
- preflight is read-only over the exact `CHILD_PAIR_READY` coordinate and cannot
  emit a ReferenceDomainSnapshot edge;
- abort close and parent-only close emit exactly one
  `V2_BURN | V2_FAIL_CLOSED` edge; post-STARTED terminal close emits exactly one
  cross-field-compatible `V2_CONSUME | V2_BURN | V2_FAIL_CLOSED` edge; and
- containment emits at most one terminal edge, only when the exact predecessor
  is known. A `NOT_CONFIRMED` union is not a committed edge.

```text
R12/R13 TASK074 reference-domain fence readback
-> TASK-072 V3 ticket/vector transaction
-> TASK-043/TASK-076 durable Job-generation readback
-> TASK-074 bind/preflight ledger transaction
-> TASK-072 V3 phase transaction
```

No writer lock spans another owner's transaction. A canonical snapshot/fence or
post-arm Task-043/TASK-076 generation change between
steps rejects the later step and enters the exact abort/containment branch; it
never retries against a newer generation automatically.

| Existing gate/lineage | R14 admission or output requirement |
|---|---|
| G01 Project bootstrap | exact canonical Project plus Task-043/Task-076 selected Job generation; fixture bootstrap cannot bind |
| G02 installed startup | same installed instance/build/session as Task-072 bootstrap and Task-075 packaged worker |
| G03 VoiceProfile | exact current revision/store digest bound through bind, preflight and close |
| G04 Consent | current reference-use evaluation at bind and preflight; drift freezes the next edge |
| G05 local route | exact current local route, engine/package and offline/network-disabled bindings; no fallback |
| G06 Human action | exact current action receipt where the selected inference operation requires it; R14 mints none |
| G07 operation ticket | exact Task-072 V3 ticket/vector; a public ticket receipt is insufficient |
| G08 private custody | exact prepared pair/capability and producer-private opened handles; Task-072/076 parent handle count remains zero |
| G09 purge | never satisfied or invoked by bind/preflight/close/recovery; physical purge stays a separate Human Gate |
| G10 TASK-046 amendment | exact accepted Profile/reference/transcript producer ABI and current receipt |
| G11 TASK-075 consumer | exact R14 owner acceptance, Task-072 adapter acceptance, Task-076 slot acceptance, Task-075 execution-input acceptance and, for post-release noncurrentness, the durable two-stage V2 compatibility receipt |
| G12 trusted time | same broker/domain trusted-time generation at every lease transition |
| G13 execution currentness | exact R9 `OWNER_VOICE_AGGREGATE_CURRENTNESS_LEASE_V1` across Project, VoiceProfile/Consent, inventory/license/install, optional ModelCandidate and reference lifecycle only; Job/ticket/consumer currentness remains separately bound after those owners exist |
| G14 reference transcript | exact audio/transcript pair and current Task-046 transcript-binding receipt |

At begin, G13 contains no Task-072 Job, Task-043/TASK-076 selected generation or
TASK-075 consumer currentness because those facts do not yet exist. The begin
lineage binds only their accepted planned profiles. The post-arm operation
lineage separately adds the exact selected/created Job and consumer coordinates
in sequence. The live G13 lease itself remains the unchanged R9 lease; R14 does
not extend its producer set or mint a replacement.

R11 `TASK074_REFERENCE_BEGIN_ATTACHMENT_V1` remains the earlier one-use input to
the single Task-072 V3 arm/begin transaction. R14 bind requires its consumed
identity and committed begin nonce but cannot call, recreate or repair it. R13
terminal retirement is later and
separate: a current terminal lease cannot bind, and bind/preflight/close/recovery
cannot retire a lease or issue the next operation. Remote close results are
inputs to the R12/R13 terminal predicates, not substitutes for retirement.

### 2.2 Parent reference-open prohibition

The R11 atomic begin transition to `IN_FLIGHT_PARENT_DELEGATION` permanently
removes every parent reference-open/read method for that operation. Parent
original handles may thereafter be used only as opaque sources for exact direct
duplication into the bound child or for close/revoke. They may not be opened,
read, decoded, hashed from body bytes, mapped, copied to another process or
returned to Task-072/TASK-076/TASK-075.

This prohibition remains active during `CHILD_TRANSFER_IN_FLIGHT`, on every
partial-transfer/failure path and after restart. No compatibility amendment,
preflight, recovery call or equal digest can restore parent read authority.

## 3. Closed producer contract registry

The R14 producer profile is
`TASK074_OWNER_VOICE_EXTERNAL_BINDING_PROFILE_V1`. It contains exactly these
versioned contracts:

| Purpose | Exact TASK-074 contract |
|---|---|
| operation slot profile value | `TASK074_OWNER_VOICE_EXTERNAL_BINDING_PROFILE_V1` |
| ordered sensitive roles | `TASK074_REFERENCE_CHILD_ROLE_SET_V1` |
| shared lease policy | `TASK074_REFERENCE_CHILD_SHARED_LEASE_POLICY_V1` |
| owner participant request for the one V3 arm | `TASK074_REFERENCE_BEGIN_ARM_REQUEST_V1` |
| durable owner begin-arm outcome | `TASK074_REFERENCE_BEGIN_ARM_READBACK_V1` |
| pre-bootstrap arm containment request | `TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_REQUEST_V1` |
| pre-bootstrap arm containment result | `TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_READBACK_V1` |
| live one-use bind delegation | `TASK074_REFERENCE_CHILD_BIND_DELEGATION_V1` |
| bind success | `TASK074_REFERENCE_CHILD_BOUND_READBACK_V1` |
| bind known-failure | `TASK074_REFERENCE_CHILD_BIND_FAILED_READBACK_V1` |
| owner preflight profile | `TASK074_REFERENCE_CHILD_PREFLIGHT_PROFILE_V1` |
| live one-use preflight authority | `TASK074_REFERENCE_CHILD_PREFLIGHT_AUTHORITY_V1` |
| owner preflight result | `TASK074_REFERENCE_CHILD_PREFLIGHT_READBACK_V1` |
| abort-authorized close request | `TASK074_REFERENCE_CHILD_CLOSE_REQUEST_V1` |
| exact close result | `TASK074_REFERENCE_CHILD_CLOSED_READBACK_V1` |
| known-no-transfer parent-only close request | `TASK074_REFERENCE_PARENT_ONLY_CLOSE_REQUEST_V1` |
| parent-only close result | `TASK074_REFERENCE_PARENT_ONLY_CLOSED_READBACK_V1` |
| post-STARTED terminal-close request | `TASK074_REFERENCE_CHILD_TERMINAL_CLOSE_REQUEST_V1` |
| owner lease terminal result | `TASK074_REFERENCE_CHILD_LEASE_TERMINAL_READBACK_V1` |
| BURNED_UNKNOWN recovery request | `TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_REQUEST_V1` |
| recovery result | `TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_READBACK_V1` |
| same-operation phase-ledger query | `TASK074_REFERENCE_CHILD_LEDGER_QUERY_V1` |
| immutable query result | `TASK074_REFERENCE_CHILD_LEDGER_QUERY_READBACK_V1` |
| owner acceptance | `TASK074_TASK076_EXTERNAL_BINDING_OWNER_ACCEPTANCE_V1` |

Every contract has its own exact ABI SHA-256. A version string without its hash,
one hash applied to several contracts, an unknown field, a generic
`OWNER_EXTERNAL_INPUT_*` record or a structurally equal mapping is rejected.

The profile descriptor itself has an exact closed field set: producer/consumer
Tasks, V3 profile, complete ABI version/hash registry, owner-acceptance
version/hash, role-set and lease-policy digests, expected child-broker
protocol/image/build policy, semantic consumer-operation identifier,
`parent_sensitive_handle_count=0`, `caller_hook_allowed=false`, and fixed false
flags for body read, model load/call, Artifact handle/body write and consumer
effect. Its self-hash covers the complete descriptor. Unknown/extra slot,
callback, path, process identity or effect field is rejected before V3 arm.

The profile field `parent_sensitive_handle_count=0` names the Task-072/TASK-076
consumer parent required by canonical V3. It does not claim that the separate
TASK-074 producer broker has already closed its two originals before bind. Those
originals remain producer-private, are never delivered to that parent, and are
truthfully closed by bound, parent-only-close, abort-close or recovery records.

### 3.1 TASK-076 V3 slot mapping

The generic slot fields map one-to-one and without aliasing:

| TASK-076 V3 slot position | Exact field names in the required TASK-074 profile value |
|---|---|
| producer | `producer_task`, `accepted_producer_revision_sha256` |
| producer profile | `profile_abi_version`, `profile_abi_sha256`, `profile_sha256` |
| pre-bind arm lineage | `begin_arm_request_version`, `begin_arm_request_abi_sha256`, `begin_arm_readback_version`, `begin_arm_readback_abi_sha256` |
| pre-bootstrap arm containment | `begin_arm_containment_request_version`, `begin_arm_containment_request_abi_sha256`, `begin_arm_containment_readback_version`, `begin_arm_containment_readback_abi_sha256` |
| bind ABI | `bind_delegation_abi_version`, `bind_delegation_abi_sha256`, `bound_readback_version`, `bound_readback_abi_sha256`, `bind_failed_readback_version`, `bind_failed_readback_abi_sha256` |
| preflight ABI | `preflight_profile_version`, `preflight_profile_abi_sha256`, `preflight_authority_abi_version`, `preflight_authority_abi_sha256`, `preflight_readback_version`, `preflight_readback_abi_sha256` |
| normal close ABI | `close_request_version`, `close_request_abi_sha256`, `closed_readback_version`, `closed_readback_abi_sha256` |
| known-no-transfer close ABI | `parent_only_close_request_version`, `parent_only_close_request_abi_sha256`, `parent_only_closed_readback_version`, `parent_only_closed_readback_abi_sha256` |
| post-STARTED terminal ABI | `terminal_close_request_version`, `terminal_close_request_abi_sha256`, `lease_terminal_readback_version`, `lease_terminal_readback_abi_sha256` |
| recovery-revoke ABI | `recovery_revoke_request_version`, `recovery_revoke_request_abi_sha256`, `recovery_revoke_readback_version`, `recovery_revoke_readback_abi_sha256` |
| reply-loss query ABI | `ledger_query_version`, `ledger_query_abi_sha256`, `ledger_query_readback_version`, `ledger_query_readback_abi_sha256` |
| role-set digest | `role_set_version`, `role_set_abi_sha256`, `role_set_sha256` |
| shared-lease-policy digest | `shared_lease_policy_version`, `shared_lease_policy_abi_sha256`, `shared_lease_policy_sha256` |
| owner acceptance | `owner_acceptance_version`, `owner_acceptance_abi_sha256`, `owner_acceptance_sha256` |
| expected child | `expected_child_broker_protocol_sha256`, `expected_child_image_sha256`, `expected_child_build_sha256` |
| consumer operation | `consumer_operation_key`, `closed_operation_profile_registry_sha256` |
| fixed guards | `parent_sensitive_handle_count`, `caller_hook_allowed`, `effect_zero` |

TASK-076's generic `OWNER_EXTERNAL_INPUT_BOUND_READBACK_V1`,
`OWNER_EXTERNAL_INPUT_BINDING_FAILED_READBACK_V1`,
`FIXED_OWNER_PREFLIGHT_PROFILE_V1`, `OWNER_EXTERNAL_INPUT_CLOSED_READBACK_V1`
and `OWNER_EXTERNAL_INPUT_RECOVERY_REVOKE_V1` are interface positions. They are
not alternative TASK-074 contract names. The fixed Task-072 adapter must retain
the original TASK-074 contract identity, ABI hash and self-hash in every V3
phase readback.

### 3.2 Explicit non-alias table

| Existing TASK-074 contract | Still permits | Never permits under R14 |
|---|---|---|
| `TASK074_REFERENCE_BEGIN_ATTACHMENT_V1` | bind the pre-child attachment/begin lineage and be consumed by the earlier atomic begin | select a child, transfer a role, preflight, close or recovery-revoke |
| `TASK074_TO_TASK075_EXECUTION_INPUT_V2` | body-free post-binding consumer handoff after every producer/consumer gate is current | carry a handle, invoke bind/preflight/close, mint acceptance or repair a V3 vector |
| `TASK074_REFERENCE_V2_ISSUE_OR_REVOKE_CAS_V1` | issue one V2 capability or win the lifecycle revoke/expiry CAS | bind a child, close remote roles, perform containment recovery or classify Task-072 effects |
| `TASK074_REFERENCE_WORKER_DELEGATION_V1` | remain an internal R10 lineage aggregate referenced by the new delegation | substitute for the R14 live bind delegation or any R14 result |

No compatibility adapter may dispatch an R14 method after receiving only one of
these existing artifacts.

### 3.3 Canonical encoding, ABI hashes and record self-hashes

All R14 durable or status-only values use the following one canonical encoding.
There is no implementation-selected JSON mode:

- the top-level value is an object encoded as RFC 8785 JCS, UTF-8 without BOM;
- strings are Unicode NFC before JCS encoding; field names and enum tokens are
  the exact ASCII spellings in this section;
- `ID` is an ASCII logical identifier of at most 128 characters matching
  `^(prj|op|budget|deleg|auth|query|child|consumer)_[A-Za-z0-9](?:[A-Za-z0-9._-]{0,117}[A-Za-z0-9])?$`, with no consecutive `..`;
- the field namespace is closed: `project_id -> prj_`,
  `consumer_operation_key -> consumer_`, `child_bootstrap_id -> child_`,
  `delegation_instance_id -> deleg_`, `authority_instance_id -> auth_`,
  `query_operation_id -> query_`, every other `*_operation_id -> op_`, and
  every `*_budget_id -> budget_`; no field accepts another prefix;
- `VERSION` matches `^[A-Z][A-Z0-9_]{2,127}$` and is used only for named ABI or
  acceptance versions, never an operation/host/path value;
- `SHA256` is exactly 64 lowercase hexadecimal characters; `ZERO_SHA256` is 64
  zeroes and is permitted only in the explicitly tagged sentinel branches
  below, never as a successful digest;
- `U32` is a JSON integer from 0 through 4294967295 and `BOOL` is a JSON boolean;
- arrays retain the defined order; maps with caller-selected keys are forbidden;
- `null`, floating-point numbers, duplicate keys, missing required keys, optional
  keys, unknown keys and unknown enum values are rejected before any budget or
  owner ledger is entered.

The ID lexer rejects before semantic lookup any colon, slash, backslash,
percent-encoded slash/backslash, control, whitespace, leading/trailing dot or
missing/foreign namespace. Required negative vectors include
`C:private_voice.wav`, `file:private_voice.wav`, `https:private_voice.wav`,
`https://host/private_voice.wav`, `C:\private_voice.wav`,
`\\host\share\private_voice.wav`, `/var/private_voice.wav`,
`../private_voice.wav`, `private_voice.wav`, `op_C:private_voice.wav` and
`op_%2fprivate_voice.wav`. Valid examples are `prj_01ABC`,
`op_01ABC-2` and `consumer_task075.owner_voice.local.inference`. IDs are never
passed to a path, URI, DNS, process or OS-object parser.

In the field tables below, fields are required and left-to-right order is the ABI
descriptor order. `LIT[x]`, `ENUM[x|y]`, `OBJ[x]`, `ARRAY[n,x]`, `LIVE[x]` and
`UNION[x|y]` are closed type-spec strings. `OBJ`, `ARRAY` and `UNION` retain
their named type specs in the contract descriptor; the separate compound-registry
digest binds their exact definitions.

For every R14 contract ABI, including a live/nonserializable object descriptor,
`abi_sha256` is derived independently of any record value:

```text
SHA256(
  "TASK074_ABI_DESCRIPTOR_V1\0" ||
  JCS({
    "canonicalization": "RFC8785_JCS_UTF8_NFC_V1",
    "compound_registry_sha256": exact TASK074 compound-registry digest,
    "contract_version": exact version literal,
    "runtime_kind": "STATUS_ONLY" | "PRIVATE_READBACK" | "PRIVATE_REQUEST" |
                    "LIVE_NON_SERIALIZABLE",
    "fields": exact ordered field-descriptor array,
    "projection_excluded_fields": exact ordered field-name array,
    "projection_hash_field": exact field name | "NONE",
    "self_hash_field": exact field name | "NONE"
  })
)
```

Each field descriptor has exactly
`{"ordinal":U32,"name":ASCII field name,"type_spec":ASCII closed type spec}`.
The section 3.4/3.6 left-to-right field order supplies ordinal 0..n-1 and the
literal `name:type_spec` pairs. Whitespace, Markdown and explanatory prose are
not inputs. `ENUM[... reason registry]` expands to the exact token order printed
in section 3.4 before hashing. `OBJ` references remain named references and are
bound by `compound_registry_sha256`; `TASK074_OPERATION_LINEAGE_V1` expands the
inherited begin-lineage fields before its compound descriptor is hashed.

The compound digest is:

```text
SHA256(
  "TASK074_COMPOUND_TYPE_REGISTRY_V1\0" ||
  JCS({
    "canonicalization": "RFC8785_JCS_UTF8_NFC_V1",
    "compounds": section 3.4 table order followed by
                 TASK074_STATUS_RESULT_UNION_V1, each as
                 {"name", "fields": exact ordered field-descriptor array}
  })
)
```

For a serializable contract, `projection_excluded_fields=[]` and
`projection_hash_field="NONE"`. For a live contract,
`self_hash_field="NONE"`; the exact projection field and excluded slot names are
defined below. The string `NONE`, not missing/null, is hashed. The ABI descriptor object keys and field-descriptor keys above are the complete
sets; JCS supplies their key order. A tool that cannot reproduce the compound
digest and every contract digest from these arrays is nonconforming and cannot
publish an implementation receipt.

The lowercase digest is placed in the matching `*_abi_sha256` field. When
section 3.5 names a record self-hash, that distinct hash always uses:

```text
SHA256(
  ASCII(exact contract_version) || 0x00 ||
  JCS(the exact record with only its named self-hash field omitted)
)
```

The bind delegation, bound readback and preflight authority use
`runtime_kind=LIVE_NON_SERIALIZABLE`. Their ABI descriptors are hashed by the
first formula, but the live objects have no record self-hash and are never
serialized. Each named projection digest hashes only the exact body-free slots
remaining after its declared exclusions; a projection is Evidence, never bearer
authority.

Every live projection uses exactly:

```text
SHA256(
  "TASK074_LIVE_PROJECTION_V1\0" ||
  JCS({
    "contract_version": exact version literal,
    "projection": exact object containing every non-excluded slot
  })
)
```

The projection object has the original descriptor order semantically and JCS
key order on the wire. A missing or extra slot, a live slot that was not on the
exact exclusion list, or a projection digest treated as bearer authority is
nonconforming.

### 3.4 Closed compound-type and enum registry

The exact compound field sets are:

| Compound type | Exact required fields and types |
|---|---|
| `EMPTY` | zero fields; its only value is `{}` |
| `TASK074_EFFECT_ZERO_V1` | `receipt_bearer_authority_created:BOOL`, `body_embedded:BOOL`, `body_read_started:BOOL`, `path_embedded:BOOL`, `secret_embedded:BOOL`, `execution_authorized_by_record:BOOL`, `producer_process_created:BOOL`, `producer_process_terminated:BOOL`, `producer_job_handle_received:BOOL`, `model_load_started:BOOL`, `model_call_started:BOOL`, `artifact_handle_created_by_producer:BOOL`, `artifact_body_write_started:BOOL`, `consumer_effect_started:BOOL`; every value is exactly `false` |
| `TASK074_EFFECT_OBSERVATION_V1` | `body_read:ENUM[NOT_STARTED_CONFIRMED|STARTED_CONFIRMED|UNKNOWN]`, `model_load:ENUM[NOT_STARTED_CONFIRMED|STARTED_CONFIRMED|UNKNOWN]`, `model_call:ENUM[NOT_STARTED_CONFIRMED|STARTED_CONFIRMED|UNKNOWN]`, `artifact_body_write:ENUM[NOT_STARTED_CONFIRMED|STARTED_CONFIRMED|UNKNOWN]`, `consumer_effect:ENUM[NOT_STARTED_CONFIRMED|STARTED_CONFIRMED|UNKNOWN]`, `producer_process_created:BOOL`, `producer_process_terminated:BOOL`, `producer_job_handle_received:BOOL`; the three producer booleans are always `false` |
| `TASK074_REFERENCE_DOMAIN_COORDINATE_V1` | `snapshot_sha256:SHA256`, `fence_sha256:SHA256`, `fence_revision:U32`, `committed_event_sha256:SHA256`, `v2_state:ENUM[ISSUED|IN_FLIGHT_PARENT_DELEGATION|CHILD_TRANSFER_IN_FLIGHT|CHILD_PAIR_READY|BODY_READ_STARTED|CONSUMED|BURNED|FAILED_CLOSED]`, `v2_lease_identity_sha256:SHA256`, `v2_live_handle_count:U32`, `v2_terminal_history_state:ENUM[ABSENT|PRESENT]`, `v2_terminal_history_sha256:SHA256`; `ABSENT` requires `ZERO_SHA256`, `PRESENT` forbids it |
| `TASK074_REFERENCE_DOMAIN_EDGE_V1` | `transition:ENUM[V2_PARENT_DELEGATION_BEGIN|V2_CHILD_TRANSFER_BEGIN|V2_CHILD_PAIR_READY|V2_BODY_READ_BEGIN|V2_CONSUME|V2_BURN|V2_FAIL_CLOSED]`, `predecessor:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `result:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `producer_ledger_predecessor_sha256:SHA256`, `producer_ledger_result_sha256:SHA256`, `cas_result:ENUM[COMMITTED]`, `unrelated_delta_count:U32` fixed at zero |
| `TASK074_REFERENCE_DOMAIN_EDGE_UNION_V1` | `state:ENUM[COMMITTED|NOT_CONFIRMED]`, `edge:UNION[OBJ[TASK074_REFERENCE_DOMAIN_EDGE_V1]|OBJ[EMPTY]]`; `COMMITTED` requires the edge-object branch, `NOT_CONFIRMED` requires the empty-object branch `{}` |
| `TASK074_REFERENCE_DOMAIN_COORDINATE_UNION_V1` | `state:ENUM[EXACT|NOT_CONFIRMED]`, `coordinate:UNION[OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]|OBJ[EMPTY]]`; `EXACT` requires the coordinate-object branch, `NOT_CONFIRMED` requires the empty-object branch `{}` |
| `TASK074_ATTACHMENT_PREDECESSOR_IDENTITY_UNION_V1` | `state:ENUM[ABSENT|PRESENT]`, `attachment_identity_sha256:SHA256`; `ABSENT` requires `ZERO_SHA256`, `PRESENT` forbids it |
| `TASK074_TERMINAL_CONSUMER_INPUT_V1` | `kind:ENUM[FINAL_CONSUMER_RESULT|NONCURRENT_PRE_CLOSE_ARM_V2]`, `contract_version:ENUM[TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1|TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2]`, `contract_abi_sha256:SHA256`, `input_sha256:SHA256`; the kind/version pairing is one-to-one, both digests are nonzero and the ABI digest must equal the one bound by the current TASK-075 acceptance receipt |
| `TASK074_BEGIN_LINEAGE_V1` | `project_id:ID`, `owner_operation_id:ID`, `consumer_operation_key:ID`, `installed_instance_sha256:SHA256`, `voice_profile_revision_sha256:SHA256`, `consent_evaluation_sha256:SHA256`, `local_route_sha256:SHA256`, `human_action_mode:ENUM[REQUIRED|NOT_REQUIRED]`, `human_action_state:ENUM[ISSUED|NOT_REQUIRED]`, `human_action_fingerprint_sha256:SHA256`, `aggregate_currentness_lease_fingerprint_sha256:SHA256`, `aggregate_currentness_lease_generation:U32`, `aggregate_currentness_lease_state:ENUM[ACTIVE]`, `task066_compute_receipt_sha256:SHA256`, `capability_lease_v2_sha256:SHA256`, `attachment_identity_sha256:SHA256`, `task072_ticket_vector_sha256:SHA256`, `planned_task076_profile_sha256:SHA256`, `planned_external_binding_slot_sha256:SHA256`, `prepared_pair_sha256:SHA256`, `reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `transcript_binding_receipt_sha256:SHA256`, `trusted_time_generation_sha256:SHA256`, `task075_consumer_profile_sha256:SHA256` |
| `TASK074_OPERATION_LINEAGE_V1` | all fields of `TASK074_BEGIN_LINEAGE_V1`, then `begin_arm_readback_sha256:SHA256`, `task072_armed_readback_sha256:SHA256`, `task072_bootstrap_readback_sha256:SHA256`, `task043_task076_current_generation_sha256:SHA256`, `external_binding_slot_sha256:SHA256`, `owner_acceptance_sha256:SHA256`, `current_reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]` |
| `TASK074_CHILD_BINDING_COORDINATE_V1` | `child_bootstrap_id:ID`, `child_broker_protocol_sha256:SHA256`, `child_image_sha256:SHA256`, `child_build_sha256:SHA256`, `private_channel_binding_sha256:SHA256`, `channel_session_sha256:SHA256`, `channel_token_binding_sha256:SHA256` |
| `TASK074_ROLE_DESCRIPTOR_V1` | `ordinal:U32`, `role:ENUM[REFERENCE_AUDIO_READ_HANDLE|REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE]`, `media_kind:ENUM[AUDIO|UTF8_TRANSCRIPT]`, `access:ENUM[READ_ONLY]`, `inheritable:BOOL`, `exportable:BOOL`, `shared_lease_required:BOOL`; last three values are `false`, `false`, `true` |
| `TASK074_ROLE_TRANSFER_ROW_V1` | `ordinal:U32`, `role:ENUM[REFERENCE_AUDIO_READ_HANDLE|REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE]`, `transfer_state:ENUM[NOT_ATTEMPTED|CHILD_DUPLICATE_CREATED|CHILD_ACCEPTED_GATE_CLOSED|PARENT_CLOSED|CHILD_CLOSE_CONFIRMED]`, `physical_binding_sha256:SHA256`, `parent_close_state:ENUM[OPEN_CONFIRMED|CLOSED_CONFIRMED]`; `ZERO_SHA256` is allowed only with `NOT_ATTEMPTED` |
| `TASK074_PARENT_CLOSE_ROW_V1` | `ordinal:U32`, `role:ENUM[REFERENCE_AUDIO_READ_HANDLE|REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE]`, `parent_close_state:ENUM[CLOSED_CONFIRMED]` |
| `TASK074_PARENT_RECOVERY_ROW_V1` | `ordinal:U32`, `role:ENUM[REFERENCE_AUDIO_READ_HANDLE|REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE]`, `parent_close_state:ENUM[CLOSED_CONFIRMED|UNKNOWN]` |
| `TASK074_REMOTE_ABSENCE_ROW_V1` | `ordinal:U32`, `role:ENUM[REFERENCE_AUDIO_READ_HANDLE|REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE]`, `remote_role_state:ENUM[ABSENT_PROVEN]` |
| `TASK074_ROLE_CLOSE_ROW_V1` | `ordinal:U32`, `role:ENUM[REFERENCE_AUDIO_READ_HANDLE|REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE]`, `close_state:ENUM[ABSENT_PROVEN|CREATED_THEN_CLOSED_VERIFIED|CLOSE_NOT_CONFIRMED]` |
| `TASK074_ROLE_RECOVERY_ROW_V1` | `ordinal:U32`, `role:ENUM[REFERENCE_AUDIO_READ_HANDLE|REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE]`, `recovery_state:ENUM[REVOKED_CONFIRMED|CLOSE_CONFIRMED|ABSENT_PROVEN|UNKNOWN]` |

The only stable reason tokens are:

- begin-arm: `NONE | INPUT_STALE | ATTACHMENT_MISMATCH | LEASE_MISMATCH |
  OWNER_CAS_REJECTED | COORDINATOR_MISMATCH`;
- bind: `NONE | ROLE_POLICY_MISMATCH | ROLE_TRANSFER_FAILED |
  PARENT_CLOSE_FAILED | LEASE_RACE | CHANNEL_FAILED | CURRENTNESS_STALE |
  INTERNAL_EXCEPTION`;
- preflight: `NONE | BOUND_STALE | ROLE_BINDING_STALE |
  PARENT_HANDLE_PRESENT | PAIR_OR_TRANSCRIPT_STALE | CURRENTNESS_STALE |
  CHILD_IDENTITY_STALE | BODY_GATE_NOT_CLOSED | EFFECT_FLAG_NONZERO |
  INTERNAL_EXCEPTION`;
- close: `NONE | ABORT_IDENTITY_STALE | RELEASE_WON | ROLE_CLOSE_FAILED |
  PARENT_CLOSE_FAILED | LEASE_RACE | CHANNEL_FAILED | INTERNAL_EXCEPTION`;
- parent-only close: `NONE | TERMINAL_IDENTITY_STALE | ROLE_TRANSFER_NOT_ZERO |
  PARENT_CLOSE_FAILED | LEASE_RACE | INTERNAL_EXCEPTION`;
- terminal close: `NONE | STARTED_IDENTITY_STALE | CONSUMER_TERMINAL_STALE |
  CHILD_EXIT_STALE | ROLE_CLOSE_FAILED | LEASE_RACE | INTERNAL_EXCEPTION`;
- recovery: `NONE | IDENTITY_MISMATCH | ROLE_REVOKE_FAILED |
  PARENT_TRUTH_UNKNOWN | LEASE_TRUTH_UNKNOWN | CHANNEL_FAILED |
  INTERNAL_EXCEPTION`.

No reason token changes an outcome or supplies authority.

`TASK074_EFFECT_ZERO_V1` describes only receipt/bearer authority, embedded
private content and the forbidden body/model/Artifact/consumer/process effects
named in that object. It does not erase a truthful role-transfer or role-close
state, which is recorded separately. In particular, a bound readback projection
is not bearer authority even though its role rows truthfully prove a gated child
duplicate was created.

The live delegation, channel seal and preflight authority are separately typed
broker objects and are never fields of a serializable effect-zero receipt or
projection. `receipt_bearer_authority_created=false` means the record/projection
cannot mint or reconstruct those objects; it does not deny the separately
authenticated delivery state of an already-authorized live object. None of
those live objects grants body/model/process authority before the exact later
gates.

### 3.5 Exact ABI version/hash register

The operation slot profile contains exactly the following version/hash pairs.
The third column is the record self-hash field, or the named live projection
field when no record self-hash exists:

| Contract | Exact profile version/hash fields | Record self-hash field |
|---|---|---|
| owner profile | `profile_abi_version`, `profile_abi_sha256` | `profile_sha256` |
| role set | `role_set_version`, `role_set_abi_sha256` | `role_set_sha256` |
| shared lease | `shared_lease_policy_version`, `shared_lease_policy_abi_sha256` | `shared_lease_policy_sha256` |
| begin-arm request | `begin_arm_request_version`, `begin_arm_request_abi_sha256` | `begin_arm_request_sha256` |
| begin-arm readback | `begin_arm_readback_version`, `begin_arm_readback_abi_sha256` | `begin_arm_readback_sha256` |
| begin-arm containment request | `begin_arm_containment_request_version`, `begin_arm_containment_request_abi_sha256` | `begin_arm_containment_request_sha256` |
| begin-arm containment readback | `begin_arm_containment_readback_version`, `begin_arm_containment_readback_abi_sha256` | `begin_arm_containment_readback_sha256` |
| bind delegation | `bind_delegation_abi_version`, `bind_delegation_abi_sha256` | none; live projection uses `bind_request_identity_sha256` |
| bound readback | `bound_readback_version`, `bound_readback_abi_sha256` | none; live projection uses `bound_readback_sha256` |
| bind-failed readback | `bind_failed_readback_version`, `bind_failed_readback_abi_sha256` | `bind_failed_readback_sha256` |
| preflight profile | `preflight_profile_version`, `preflight_profile_abi_sha256` | `preflight_profile_sha256` |
| preflight authority | `preflight_authority_abi_version`, `preflight_authority_abi_sha256` | none; live projection uses `preflight_authority_identity_sha256` |
| preflight readback | `preflight_readback_version`, `preflight_readback_abi_sha256` | `preflight_readback_sha256` |
| abort close request | `close_request_version`, `close_request_abi_sha256` | `close_request_sha256` |
| abort close readback | `closed_readback_version`, `closed_readback_abi_sha256` | `closed_readback_sha256` |
| parent-only close request | `parent_only_close_request_version`, `parent_only_close_request_abi_sha256` | `parent_only_close_request_sha256` |
| parent-only close readback | `parent_only_closed_readback_version`, `parent_only_closed_readback_abi_sha256` | `parent_only_closed_readback_sha256` |
| terminal close request | `terminal_close_request_version`, `terminal_close_request_abi_sha256` | `terminal_close_request_sha256` |
| lease terminal readback | `lease_terminal_readback_version`, `lease_terminal_readback_abi_sha256` | `lease_terminal_readback_sha256` |
| recovery request | `recovery_revoke_request_version`, `recovery_revoke_request_abi_sha256` | `recovery_revoke_request_sha256` |
| recovery readback | `recovery_revoke_readback_version`, `recovery_revoke_readback_abi_sha256` | `recovery_revoke_readback_sha256` |
| ledger query | `ledger_query_version`, `ledger_query_abi_sha256` | `ledger_query_sha256` |
| ledger query readback | `ledger_query_readback_version`, `ledger_query_readback_abi_sha256` | `ledger_query_readback_sha256` |
| owner acceptance | `owner_acceptance_version`, `owner_acceptance_abi_sha256` | `owner_acceptance_sha256` |

Every `*_version` value is the exact contract literal in section 3. The profile
ABI descriptor expands the complete pair registry above. A missing pair, reused
hash, value whose derived descriptor hash differs, or extra pair rejects the
slot. Literal digest values are deterministic outputs of the descriptor formula;
they are materialized by the future producer implementation receipt, not chosen
or negotiated by either adapter.

### 3.6 Exact field registries

`TASK074_OWNER_VOICE_EXTERNAL_BINDING_PROFILE_V1` has the exact union of these
fields and no others:

1. `contract_version:LIT[TASK074_OWNER_VOICE_EXTERNAL_BINDING_PROFILE_V1]`,
   `record_type:LIT[OWNER_VOICE_EXTERNAL_BINDING_PROFILE]`,
   `producer_task:LIT[TASK-074]`, `slot_owner_task:LIT[TASK-076]`,
   `downstream_consumer_task:LIT[TASK-075]`,
   `task076_profile:LIT[TASK076_JOB_CHILD_BOOTSTRAP_BIND_RELEASE_V3]`,
   `accepted_producer_revision_sha256:SHA256`;
2. every exact version/hash field in section 3.5, in that table order;
3. `expected_child_broker_protocol_sha256:SHA256`,
   `expected_child_image_sha256:SHA256`,
   `expected_child_build_sha256:SHA256`, `consumer_operation_key:ID`,
   `closed_operation_profile_registry_sha256:SHA256`,
   `parent_sensitive_handle_count:U32` fixed at zero,
   `caller_hook_allowed:BOOL` fixed at false,
   `effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`, `profile_sha256:SHA256`.

The remaining exact record tables are:

| Contract | Exact required fields and types, in ABI descriptor order |
|---|---|
| `TASK074_REFERENCE_CHILD_ROLE_SET_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_ROLE_SET_V1]`, `record_type:LIT[REFERENCE_CHILD_ROLE_SET]`, `role_count:U32` fixed at 2, `roles:ARRAY[2,TASK074_ROLE_DESCRIPTOR_V1]` fixed to audio ordinal 0 then transcript ordinal 1, `role_set_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_SHARED_LEASE_POLICY_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_SHARED_LEASE_POLICY_V1]`, `record_type:LIT[REFERENCE_CHILD_SHARED_LEASE_POLICY]`, `role_set_sha256:SHA256`, `bind_budget_count:U32`, `preflight_budget_count:U32`, `body_start_budget_count:U32` all fixed at 1, `parent_body_entry_after_atomic_begin:ENUM[PERMANENTLY_CLOSED]`, `child_body_gate_during_bind:ENUM[CLOSED]`, `child_body_gate_during_preflight:ENUM[CLOSED]`, `parent_close_required_for_ready:BOOL` true, `shared_terminal:BOOL` true, `normal_close_authority:ENUM[EXACT_TASK072_ABORT_PENDING]`, `recovery_authority:ENUM[EXACT_TASK072_BURNED_UNKNOWN]`, `forward_replay_allowed:BOOL` false, `recovery_continuation_allowed:BOOL` true, `rebind_allowed:BOOL`, `role_retry_allowed:BOOL`, `restart_rehydration_allowed:BOOL` all false, `shared_lease_policy_sha256:SHA256` |
| `TASK074_REFERENCE_BEGIN_ARM_REQUEST_V1` | `contract_version:LIT[TASK074_REFERENCE_BEGIN_ARM_REQUEST_V1]`, `record_type:LIT[REFERENCE_BEGIN_ARM_REQUEST]`, `begin_operation_id:ID`, `begin_budget_id:ID`, `begin_lineage:OBJ[TASK074_BEGIN_LINEAGE_V1]`, `task072_arm_prepared_sha256:SHA256`, `expected_owner_ledger_generation:U32`, `expected_owner_ledger_head_sha256:SHA256`, `owner_acceptance_sha256:SHA256`, `begin_arm_request_sha256:SHA256` |
| `TASK074_REFERENCE_BEGIN_ARM_READBACK_V1` | `contract_version:LIT[TASK074_REFERENCE_BEGIN_ARM_READBACK_V1]`, `record_type:LIT[REFERENCE_BEGIN_ARM_READBACK]`, `owner_operation_id:ID`, `begin_operation_id:ID`, `begin_budget_id:ID`, `begin_arm_request_sha256:SHA256`, `task072_arm_prepared_sha256:SHA256`, `begin_arm_outcome:ENUM[COMMITTED|REJECTED_KNOWN]`, `attachment_terminal_state:ENUM[CONSUMED|BURNED|FAILED_CLOSED]`, `capability_lease_v2_state:ENUM[IN_FLIGHT_PARENT_DELEGATION|BURNED|FAILED_CLOSED]`, `capability_lease_v2_generation:U32`, `begin_nonce_sha256:SHA256`, `reference_domain_edges:ARRAY[1,TASK074_REFERENCE_DOMAIN_EDGE_V1]`, `stable_reason:ENUM[begin-arm reason registry]`, `owner_ledger_generation:U32`, `owner_ledger_head_sha256:SHA256`, `effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`, `begin_arm_readback_sha256:SHA256` |
| `TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_REQUEST_V1` | `contract_version:LIT[TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_REQUEST_V1]`, `record_type:LIT[REFERENCE_BEGIN_ARM_CONTAINMENT_REQUEST]`, `owner_operation_id:ID`, `containment_operation_id:ID`, `containment_generation:U32`, `previous_containment_readback_sha256:SHA256`, `begin_arm_attempt_state:ENUM[ABSENT_PROVEN|REQUESTED]`, `begin_arm_request_sha256:SHA256`, `task072_arm_prepared_state:ENUM[ABSENT_PROVEN|PRESENT]`, `task072_arm_prepared_sha256:SHA256`, `task072_arm_terminal_kind:ENUM[PRE_ARM_REJECTED|ARM_PREPARED_CLOSED|BURNED_UNKNOWN_PREBOOTSTRAP|ARMED_BURNED_UNKNOWN_PREBOOTSTRAP]`, `task072_arm_terminal_sha256:SHA256`, `begin_ledger_query_state:ENUM[NOT_APPLICABLE|NOT_ENTERED|COMMITTED|AMBIGUOUS]`, `begin_ledger_query_readback_sha256:SHA256`, `no_process_or_role_transfer_proof_state:ENUM[CONFIRMED]`, `no_process_or_role_transfer_proof_sha256:SHA256`, `attachment_predecessor_identity:OBJ[TASK074_ATTACHMENT_PREDECESSOR_IDENTITY_UNION_V1]`, `attachment_predecessor_state:ENUM[ABSENT_PROVEN|ISSUED|CONSUMED]`, `capability_lease_v2_sha256:SHA256`, `capability_lease_v2_predecessor_state:ENUM[ISSUED|IN_FLIGHT_PARENT_DELEGATION]`, `confirmed_parent_role_set_sha256:SHA256`, `remaining_parent_role_set_sha256:SHA256`, `last_known_reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `owner_acceptance_sha256:SHA256`, `expected_owner_ledger_generation:U32`, `expected_owner_ledger_head_sha256:SHA256`, `begin_arm_containment_request_sha256:SHA256` |
| `TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_READBACK_V1` | `contract_version:LIT[TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_READBACK_V1]`, `record_type:LIT[REFERENCE_BEGIN_ARM_CONTAINMENT_READBACK]`, `owner_operation_id:ID`, `containment_operation_id:ID`, `containment_generation:U32`, `begin_arm_containment_request_sha256:SHA256`, `task072_arm_terminal_sha256:SHA256`, `no_process_or_role_transfer_proof_sha256:SHA256`, `containment_outcome:ENUM[CONTAINMENT_CONFIRMED|OUTCOME_NOT_CONFIRMED]`, `attachment_predecessor_state:ENUM[ABSENT_PROVEN|ISSUED|CONSUMED]`, `attachment_terminal_observation:ENUM[ABSENT_PROVEN|CONSUMED|BURNED|FAILED_CLOSED|NOT_CONFIRMED]`, `parent_recovery_rows:ARRAY[2,TASK074_PARENT_RECOVERY_ROW_V1]`, `remote_role_absence_rows:ARRAY[2,TASK074_REMOTE_ABSENCE_ROW_V1]`, `parent_count_state:ENUM[ZERO_CONFIRMED|UNKNOWN]`, `lease_predecessor_state:ENUM[ISSUED|IN_FLIGHT_PARENT_DELEGATION]`, `lease_terminal_observation:ENUM[BURNED|FAILED_CLOSED|NOT_CONFIRMED]`, `capability_lease_v2_generation:U32`, `reference_domain_terminal_edge:OBJ[TASK074_REFERENCE_DOMAIN_EDGE_UNION_V1]`, `stable_reason:ENUM[begin-arm reason registry]`, `effect_observation:OBJ[TASK074_EFFECT_OBSERVATION_V1]`, `owner_ledger_generation:U32`, `owner_ledger_head_sha256:SHA256`, `begin_arm_containment_readback_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_BOUND_READBACK_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_BOUND_READBACK_V1]`, `record_type:LIT[REFERENCE_CHILD_BOUND_READBACK]`, `operation_lineage:OBJ[TASK074_OPERATION_LINEAGE_V1]`, `child_binding:OBJ[TASK074_CHILD_BINDING_COORDINATE_V1]`, `delegation_instance_id:ID`, `bind_operation_id:ID`, `bind_budget_id:ID`, `bind_request_identity_sha256:SHA256`, `attempted_role_set_sha256:SHA256`, `accepted_role_set_sha256:SHA256`, `role_transfer_rows:ARRAY[2,TASK074_ROLE_TRANSFER_ROW_V1]`, `parent_sensitive_handle_count:U32` fixed at zero, `capability_lease_v2_state:ENUM[CHILD_PAIR_READY]`, `capability_lease_v2_generation:U32`, `reference_domain_edges:ARRAY[2,TASK074_REFERENCE_DOMAIN_EDGE_V1]`, `child_body_gate_state:ENUM[CLOSED]`, `child_role_body_read_counts:ARRAY[2,U32]` fixed to `[0,0]`, `owner_ledger_generation:U32`, `owner_ledger_head_sha256:SHA256`, `effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`, `private_channel_seal:LIVE[TASK072_FIXED_OWNER_ADAPTER_CHANNEL_SEAL_V1]`, `preflight_authority:LIVE[TASK074_REFERENCE_CHILD_PREFLIGHT_AUTHORITY_V1]`, `delivery_state:ENUM[UNDELIVERED|DELIVERED_ACKNOWLEDGED]`, `bound_readback_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_BIND_FAILED_READBACK_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_BIND_FAILED_READBACK_V1]`, `record_type:LIT[REFERENCE_CHILD_BIND_FAILED_READBACK]`, `operation_lineage:OBJ[TASK074_OPERATION_LINEAGE_V1]`, `child_binding:OBJ[TASK074_CHILD_BINDING_COORDINATE_V1]`, `delegation_instance_id:ID`, `bind_operation_id:ID`, `bind_budget_id:ID`, `bind_request_identity_sha256:SHA256`, `bind_outcome:ENUM[FAILED_KNOWN]`, `attempted_role_set_sha256:SHA256`, `accepted_role_set_sha256:SHA256`, `role_transfer_rows:ARRAY[2,TASK074_ROLE_TRANSFER_ROW_V1]`, `owner_close_required:BOOL` fixed true, `capability_lease_v2_state:ENUM[CHILD_TRANSFER_IN_FLIGHT]`, `capability_lease_v2_generation:U32`, `reference_domain_edges:ARRAY[1,TASK074_REFERENCE_DOMAIN_EDGE_V1]`, `stable_reason:ENUM[bind reason registry excluding NONE]`, `owner_ledger_generation:U32`, `owner_ledger_head_sha256:SHA256`, `effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`, `bind_failed_readback_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_PREFLIGHT_PROFILE_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_PREFLIGHT_PROFILE_V1]`, `record_type:LIT[REFERENCE_CHILD_PREFLIGHT_PROFILE]`, `owner_operation_id:ID`, `preflight_operation_id:ID`, `preflight_budget_id:ID`, `bound_readback_sha256:SHA256`, `operation_lineage_sha256:SHA256`, `role_set_sha256:SHA256`, `shared_lease_policy_sha256:SHA256`, `currentness_bundle_sha256:SHA256`, `observed_reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `expected_owner_ledger_generation:U32`, `expected_owner_ledger_head_sha256:SHA256`, `owner_acceptance_sha256:SHA256`, `effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`, `preflight_profile_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_PREFLIGHT_READBACK_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_PREFLIGHT_READBACK_V1]`, `record_type:LIT[REFERENCE_CHILD_PREFLIGHT_READBACK]`, `owner_operation_id:ID`, `preflight_operation_id:ID`, `preflight_budget_id:ID`, `preflight_profile_sha256:SHA256`, `bound_readback_sha256:SHA256`, `preflight_outcome:ENUM[VALIDATED|FAILED_CLOSED_ABORT_REQUIRED]`, `preflight_gate_state:ENUM[VALIDATED_BODY_GATE_CLOSED|QUIESCED_ABORT_REQUIRED]`, `stable_reason:ENUM[preflight reason registry]`, `currentness_bundle_sha256:SHA256`, `observed_reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `capability_lease_v2_state:ENUM[CHILD_PAIR_READY]`, `capability_lease_v2_generation:U32`, `physical_role_binding_sha256s:ARRAY[2,SHA256]`, `parent_sensitive_handle_count:U32` fixed at zero, `child_body_gate_state:ENUM[CLOSED]`, `child_role_body_read_counts:ARRAY[2,U32]` fixed to `[0,0]`, `owner_ledger_generation:U32`, `owner_ledger_head_sha256:SHA256`, `effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`, `preflight_readback_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_CLOSE_REQUEST_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_CLOSE_REQUEST_V1]`, `record_type:LIT[REFERENCE_CHILD_CLOSE_REQUEST]`, `owner_operation_id:ID`, `close_operation_id:ID`, `close_budget_id:ID`, `task072_abort_pending_readback_sha256:SHA256`, `task072_v3_vector_sha256:SHA256`, `bind_result_sha256:SHA256`, `preflight_result_sha256:SHA256`, `attempted_role_set_sha256:SHA256`, `accepted_role_set_sha256:SHA256`, `capability_lease_v2_sha256:SHA256`, `capability_lease_v2_generation:U32`, `expected_reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `parent_role_truth_sha256:SHA256`, `owner_acceptance_sha256:SHA256`, `expected_owner_ledger_generation:U32`, `expected_owner_ledger_head_sha256:SHA256`, `close_request_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_CLOSED_READBACK_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_CLOSED_READBACK_V1]`, `record_type:LIT[REFERENCE_CHILD_CLOSED_READBACK]`, `owner_operation_id:ID`, `close_operation_id:ID`, `close_budget_id:ID`, `close_request_sha256:SHA256`, `task072_abort_pending_readback_sha256:SHA256`, `close_outcome:ENUM[CLOSED]`, `role_close_rows:ARRAY[2,TASK074_ROLE_CLOSE_ROW_V1]`, `parent_sensitive_handle_count:U32` fixed at zero, `v2_live_handle_count:U32` fixed at zero, `body_gate_state:ENUM[PERMANENTLY_CLOSED]`, `capability_lease_v2_terminal_state:ENUM[BURNED|FAILED_CLOSED]`, `capability_lease_v2_generation:U32`, `reference_domain_edges:ARRAY[1,TASK074_REFERENCE_DOMAIN_EDGE_V1]`, `stable_reason:ENUM[close reason registry]`, `owner_ledger_generation:U32`, `owner_ledger_head_sha256:SHA256`, `effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`, `closed_readback_sha256:SHA256` |
| `TASK074_REFERENCE_PARENT_ONLY_CLOSE_REQUEST_V1` | `contract_version:LIT[TASK074_REFERENCE_PARENT_ONLY_CLOSE_REQUEST_V1]`, `record_type:LIT[REFERENCE_PARENT_ONLY_CLOSE_REQUEST]`, `owner_operation_id:ID`, `parent_close_operation_id:ID`, `parent_close_budget_id:ID`, `begin_arm_readback_sha256:SHA256`, `task072_known_no_transfer_terminal_kind:ENUM[ORPHAN_ABORTED|PREBOOTSTRAP_ABORTED|BOOTSTRAP_REJECTED]`, `task072_known_no_transfer_terminal_sha256:SHA256`, `no_role_transfer_proof_sha256:SHA256`, `capability_lease_v2_sha256:SHA256`, `capability_lease_v2_generation:U32`, `expected_reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `owner_acceptance_sha256:SHA256`, `expected_owner_ledger_generation:U32`, `expected_owner_ledger_head_sha256:SHA256`, `parent_only_close_request_sha256:SHA256` |
| `TASK074_REFERENCE_PARENT_ONLY_CLOSED_READBACK_V1` | `contract_version:LIT[TASK074_REFERENCE_PARENT_ONLY_CLOSED_READBACK_V1]`, `record_type:LIT[REFERENCE_PARENT_ONLY_CLOSED_READBACK]`, `owner_operation_id:ID`, `parent_close_operation_id:ID`, `parent_close_budget_id:ID`, `parent_only_close_request_sha256:SHA256`, `task072_known_no_transfer_terminal_sha256:SHA256`, `parent_close_rows:ARRAY[2,TASK074_PARENT_CLOSE_ROW_V1]`, `parent_sensitive_handle_count:U32` fixed at zero, `v2_live_handle_count:U32` fixed at zero, `body_gate_state:ENUM[PERMANENTLY_CLOSED]`, `role_transfer_state:ENUM[ABSENT_PROVEN]`, `capability_lease_v2_terminal_state:ENUM[BURNED|FAILED_CLOSED]`, `capability_lease_v2_generation:U32`, `reference_domain_edges:ARRAY[1,TASK074_REFERENCE_DOMAIN_EDGE_V1]`, `stable_reason:ENUM[parent-only close reason registry]`, `owner_ledger_generation:U32`, `owner_ledger_head_sha256:SHA256`, `effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`, `parent_only_closed_readback_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_TERMINAL_CLOSE_REQUEST_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_TERMINAL_CLOSE_REQUEST_V1]`, `record_type:LIT[REFERENCE_CHILD_TERMINAL_CLOSE_REQUEST]`, `owner_operation_id:ID`, `terminal_close_operation_id:ID`, `terminal_close_budget_id:ID`, `task072_started_readback_sha256:SHA256`, `task075_terminal_input:OBJ[TASK074_TERMINAL_CONSUMER_INPUT_V1]`, `child_exit_and_result_coordinate_sha256:SHA256`, `bound_readback_sha256:SHA256`, `preflight_readback_sha256:SHA256`, `capability_lease_v2_sha256:SHA256`, `capability_lease_v2_predecessor_state:ENUM[CHILD_PAIR_READY|BODY_READ_STARTED]`, `capability_lease_v2_generation:U32`, `expected_reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `owner_acceptance_sha256:SHA256`, `expected_owner_ledger_generation:U32`, `expected_owner_ledger_head_sha256:SHA256`, `terminal_close_request_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_LEASE_TERMINAL_READBACK_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_LEASE_TERMINAL_READBACK_V1]`, `record_type:LIT[REFERENCE_CHILD_LEASE_TERMINAL_READBACK]`, `owner_operation_id:ID`, `terminal_close_operation_id:ID`, `terminal_close_budget_id:ID`, `terminal_close_request_sha256:SHA256`, `task072_started_readback_sha256:SHA256`, `task075_terminal_input:OBJ[TASK074_TERMINAL_CONSUMER_INPUT_V1]`, `child_exit_and_result_coordinate_sha256:SHA256`, `terminal_kind:ENUM[CONSUMED|BURNED|FAILED_CLOSED]`, `two_role_completion_state:ENUM[CONFIRMED|NOT_APPLICABLE|NOT_CONFIRMED]`, `two_role_completion_sha256:SHA256`, `role_close_rows:ARRAY[2,TASK074_ROLE_CLOSE_ROW_V1]`, `parent_sensitive_handle_count:U32` fixed at zero, `v2_live_handle_count:U32` fixed at zero, `body_gate_state:ENUM[PERMANENTLY_CLOSED]`, `capability_lease_v2_generation:U32`, `reference_domain_edges:ARRAY[1,TASK074_REFERENCE_DOMAIN_EDGE_V1]`, `stable_reason:ENUM[terminal close reason registry]`, `effect_observation:OBJ[TASK074_EFFECT_OBSERVATION_V1]`, `owner_ledger_generation:U32`, `owner_ledger_head_sha256:SHA256`, `lease_terminal_readback_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_REQUEST_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_REQUEST_V1]`, `record_type:LIT[REFERENCE_CHILD_RECOVERY_REVOKE_REQUEST]`, `owner_operation_id:ID`, `recovery_operation_id:ID`, `recovery_generation:U32`, `previous_recovery_readback_sha256:SHA256`, `task072_burned_unknown_readback_sha256:SHA256`, `task072_v3_vector_sha256:SHA256`, `capability_lease_v2_sha256:SHA256`, `attachment_identity_sha256:SHA256`, `task072_bootstrap_readback_sha256:SHA256`, `attempted_role_set_sha256:SHA256`, `accepted_role_set_sha256:SHA256`, `confirmed_role_set_sha256:SHA256`, `remaining_role_set_sha256:SHA256`, `last_known_reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`, `last_producer_ledger_head_sha256:SHA256`, `owner_acceptance_sha256:SHA256`, `expected_owner_ledger_generation:U32`, `expected_owner_ledger_head_sha256:SHA256`, `recovery_revoke_request_sha256:SHA256` |
| `TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_READBACK_V1` | `contract_version:LIT[TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_READBACK_V1]`, `record_type:LIT[REFERENCE_CHILD_RECOVERY_REVOKE_READBACK]`, `owner_operation_id:ID`, `recovery_operation_id:ID`, `recovery_generation:U32`, `recovery_revoke_request_sha256:SHA256`, `task072_burned_unknown_readback_sha256:SHA256`, `recovery_outcome:ENUM[CONTAINMENT_CONFIRMED|OUTCOME_NOT_CONFIRMED]`, `role_recovery_rows:ARRAY[2,TASK074_ROLE_RECOVERY_ROW_V1]`, `parent_count_state:ENUM[ZERO_CONFIRMED|UNKNOWN]`, `lease_terminal_observation:ENUM[BURNED|FAILED_CLOSED|NOT_CONFIRMED]`, `capability_lease_v2_generation:U32`, `reference_domain_terminal_edge:OBJ[TASK074_REFERENCE_DOMAIN_EDGE_UNION_V1]`, `stable_reason:ENUM[recovery reason registry]`, `effect_observation:OBJ[TASK074_EFFECT_OBSERVATION_V1]`, `owner_ledger_generation:U32`, `owner_ledger_head_sha256:SHA256`, `recovery_revoke_readback_sha256:SHA256` |

The begin-arm containment sentinels are closed. `ABSENT_PROVEN` begin-attempt
or ARM_PREPARED state requires its paired SHA-256 to equal `ZERO_SHA256`;
`REQUESTED | PRESENT` forbids the sentinel. `NOT_APPLICABLE` query state
requires a zero query digest, while every other query state requires the exact
nonzero `BEGIN_ARM` query readback. The confirmed no-process/no-transfer proof
digest is always nonzero and must be carried by the exact Task-072 terminal.
The only legal attachment/lease predecessor
tuples are `ABSENT_PROVEN/ISSUED`, `ISSUED/ISSUED` and
`CONSUMED/IN_FLIGHT_PARENT_DELEGATION`. Their confirmed attachment terminal
observations are respectively `ABSENT_PROVEN`, `BURNED | FAILED_CLOSED` and
`CONSUMED`; no other cross-field combination is decodable. The first tuple
requires `attachment_predecessor_identity=ABSENT/ZERO_SHA256`; the latter two
require `PRESENT` plus the exact nonzero R11 identity. A planned identity,
operation-derived digest, nonce for an absent attachment or discriminant/state
mismatch is invalid before any parent-close or canonical-domain mutation.

The live `TASK074_REFERENCE_CHILD_BIND_DELEGATION_V1` object has exactly these
internal slots, in descriptor order:
`contract_version:LIT[TASK074_REFERENCE_CHILD_BIND_DELEGATION_V1]`,
`record_type:LIT[REFERENCE_CHILD_BIND_DELEGATION]`,
`delegation_instance_id:ID`, `bind_operation_id:ID`, `bind_budget_id:ID`,
`producer_revision_sha256:SHA256`,
`operation_lineage:OBJ[TASK074_OPERATION_LINEAGE_V1]`,
`child_binding:OBJ[TASK074_CHILD_BINDING_COORDINATE_V1]`,
`transfer_endpoint:LIVE[NON_EXTRACTABLE_TASK072_ROLE_TRANSFER_ENDPOINT]`,
`aggregate_currentness_validation_endpoint:LIVE[OWNER_VOICE_AGGREGATE_CURRENTNESS_LEASE_VALIDATOR_V1]`,
`human_action_validation_endpoint:UNION[LIVE[TASK071_OWNER_VOICE_LOCAL_INFERENCE_VALIDATOR_V1]|LIT[NOT_REQUIRED]]`,
`role_set_sha256:SHA256`, `shared_lease_policy_sha256:SHA256`,
`owner_acceptance_sha256:SHA256`, `expected_owner_ledger_generation:U32`,
`expected_owner_ledger_head_sha256:SHA256`,
`one_use_state:ENUM[UNCONSUMED|ENTERED|CONSUMED]` and
`bind_request_identity_sha256:SHA256`. The identity digest uses the live
projection formula over the non-excluded slots. The two validators authenticate
the fingerprints in `operation_lineage` at bind and preflight, never cross into
the child, and cannot consume, refresh, release or replace their underlying live
objects.

The bind-delegation projection excludes, in this exact order,
`transfer_endpoint`, `aggregate_currentness_validation_endpoint`,
`human_action_validation_endpoint`, `one_use_state` and
`bind_request_identity_sha256`. No other slot is excluded.

`TASK074_REFERENCE_CHILD_PREFLIGHT_AUTHORITY_V1` has exactly
`contract_version:LIT[TASK074_REFERENCE_CHILD_PREFLIGHT_AUTHORITY_V1]`,
`record_type:LIT[REFERENCE_CHILD_PREFLIGHT_AUTHORITY]`,
`authority_instance_id:ID`, `owner_operation_id:ID`,
`preflight_operation_id:ID`, `preflight_budget_id:ID`,
`bound_readback_sha256:SHA256`,
`operation_lineage:OBJ[TASK074_OPERATION_LINEAGE_V1]`,
`aggregate_currentness_validation_endpoint:LIVE[OWNER_VOICE_AGGREGATE_CURRENTNESS_LEASE_VALIDATOR_V1]`,
`human_action_validation_endpoint:UNION[LIVE[TASK071_OWNER_VOICE_LOCAL_INFERENCE_VALIDATOR_V1]|LIT[NOT_REQUIRED]]`,
`owner_acceptance_sha256:SHA256`,
`expected_reference_domain_coordinate:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_V1]`,
`one_use_state:ENUM[UNCONSUMED|ENTERED|CONSUMED]` and
`preflight_authority_identity_sha256:SHA256`. Its projection excludes, in this
exact order, both validation endpoints, `one_use_state` and
`preflight_authority_identity_sha256`; that field stores the exact live
projection formula result.

The live bound-readback projection excludes, in this exact order,
`private_channel_seal`, `preflight_authority`, `delivery_state` and
`bound_readback_sha256`. Only the original delivered object can convey the seal
and preflight authority. Its projection or query receipt cannot reconstruct
either; `bound_readback_sha256` stores the exact live projection formula result.

The owner acceptance exact field registry is defined in section 9. The ledger
query exact field registry and tagged result union are defined in section 6.1.

## 4. Exact role set and shared lease policy

`TASK074_REFERENCE_CHILD_ROLE_SET_V1` is an ordered exact two-row registry:

1. `REFERENCE_AUDIO_READ_HANDLE`;
2. `REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`.

Both roles are read-only, noninheritable outside the exact child bootstrap
broker, nonexportable, path-free and bound to the same prepared pair, Profile,
Consent, reference-domain snapshot and one V2 lease. Missing, extra, reordered,
duplicated, writable or independently leased roles are invalid. Numeric handles,
paths, bodies, keys and host identities never appear in a slot/readback.

`TASK074_REFERENCE_CHILD_SHARED_LEASE_POLICY_V1` binds:

- the R10/R11 `CapabilityLeaseV2` identity and exact state transition;
- one bind budget, one body-free preflight budget and one body-start budget;
- parent body entry permanently closed after the R11 atomic begin;
- child role body gates closed throughout bind and preflight;
- both child-local roles accepted and both parent originals close-read back
  before `CHILD_PAIR_READY`;
- one shared terminal: partial read, role error, channel loss, revoke or exception
  burns/fails both roles together;
- normal close only after the exact Task-072 V3 `ABORT_PENDING` winner;
- containment-only recovery only from the exact V3 `BURNED_UNKNOWN` vector;
- forward replay, rebind, independent role retry and restart rehydration zero;
- explicit same-operation begin-arm/recovery containment continuation may advance
  only the monotonic containment generation and remaining UNKNOWN rows.

`CHILD_PAIR_READY` is necessary but not sufficient for body access. The only
legal `BODY_READ_STARTED` winner additionally requires all of:

- exact current TASK-074 preflight `VALIDATED`;
- exact TASK-072 `JOB_CHILD_STARTED_READBACK_V3` after V3 release wins;
- the same TASK-043-selected TASK-076 IN_FLIGHT coordinate;
- exact current TASK-075 inference authorization and execution-input V2 lineage;
- current Project/Profile/Consent/reference/trusted-time/selection facts.

Preflight success alone cannot open either body or load/call a model.

R14 does not invent another body-start capability or place it in the Task-076
external-binding slot. The already-accepted R10 child-local broker redemption of
the exact `TASK074_TO_TASK075_EXECUTION_INPUT_V2` remains the sole body-start
entry. R14 narrows that existing entry: the bound child broker must additionally
validate the exact R14 bound object, committed `VALIDATED` preflight readback,
Task-072 `JOB_CHILD_STARTED_READBACK_V3`, current Task-075 inference admission
and the same operation/lease coordinate. Its one canonical result edge is
`V2_BODY_READ_BEGIN: CHILD_PAIR_READY -> BODY_READ_STARTED`. The edge is
committed in the same canonical TASK-074 reference-domain store and consumes the
existing one body-start budget; an external slot field, query projection or
preflight digest alone cannot invoke it. Reply loss is resolved only from the
existing canonical R12/R13 snapshot/fence readback for the same operation and
lease; body start is never repeated and is not misreported as an R14 external
binding ledger phase.

## 5. Live child-bind delegation and bound readback

`TASK074_REFERENCE_CHILD_BIND_DELEGATION_V1` is a broker-live, one-use,
noncopyable, nonserializable, nonpickleable and restart-invalid object. It is
created only after the single exact Task-072 V3 arm/R11 attachment-begin
transaction committed and binds:

- Project, Profile, Consent, selection, reference pair/domain and semantic
  operation;
- V2 capability/lease plus R11 attachment and Task-072 begin identities;
- Task-072 ARMED V3 vector and bootstrap-waiting process/broker identity;
- TASK-043-selected Task-076 IN_FLIGHT and the exact external-binding slot;
- child image/build/protocol/channel/session/token binding digests;
- one Task-072-minted, non-extractable child-broker transfer endpoint restricted
  to the exact two roles and operation;
- exact R14 owner acceptance, role-set and shared-lease-policy digests;
- producer broker/domain/session and one bind budget.

It contains no caller-visible PID, process/Job handle, raw sensitive handle,
path, body, URI, argv, environment, callback or caller-selected hook. The live
transfer endpoint may internally retain the exact child-process duplication
coordinate, but that coordinate and the sole Job handle remain owned and
non-extractable inside TASK-072. TASK-074 can use the endpoint only to transfer,
challenge and later close/revoke the fixed role set; it cannot query, resume,
terminate or wait the process or duplicate any other handle.

The only bind method is:

```text
bind_reference_child_roles_v1(
    TASK074_REFERENCE_CHILD_BIND_DELEGATION_V1,
    exact TASK-072 JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3,
    exact TASK-076 V3 external-binding coordinate
) -> TASK074_REFERENCE_CHILD_BOUND_READBACK_V1
   | TASK074_REFERENCE_CHILD_BIND_FAILED_READBACK_V1
   | OUTCOME_NOT_CONFIRMED
```

Before mutating the exact operation, it authenticates the private channel and
matches the complete operation/vector/slot/acceptance identity. Wrong or
cross-operation input leaves the victim operation byte-for-byte unchanged. Once
the exact bind budget is durably entered, every success, known failure,
exception or uncertainty consumes it; no caller retry exists.

The producer CASes V2 to `CHILD_TRANSFER_IN_FLIGHT`, uses the restricted endpoint
to duplicate roles in the fixed order directly into the exact child-local
broker, challenges each accepted role without reading it, closes both parent
originals and then CASes to `CHILD_PAIR_READY`. TASK-072's endpoint adapter may
validate role/access/operation identity and perform the destination-side OS
transfer, but it cannot open either source body or retain a reusable source
handle.

The bound readback's two `reference_domain_edges` are exactly the ordered
`V2_CHILD_TRANSFER_BEGIN` and `V2_CHILD_PAIR_READY` edges; the second
predecessor equals the first result byte-for-byte. A failed-known readback has
exactly one `V2_CHILD_TRANSFER_BEGIN` edge and its result is
`CHILD_TRANSFER_IN_FLIGHT`. Any missing, reordered, discontinuous or additional
edge is a contract failure, not a partial success.

`TASK074_REFERENCE_CHILD_BOUND_READBACK_V1` is returned only when:

- attempted and accepted role sets both equal the exact two-role digest;
- both child-local physical-role binding digests are current;
- both parent originals have exact close readbacks and
  `parent_sensitive_handle_count=0`;
- child body-read counts are zero and both body gates are closed;
- model load/call, Artifact-handle creation/body write and consumer effect are
  all false;
- the exact delegation, Task-072 vector/bootstrap, Task-076 coordinate, owner
  acceptance, operation and `CHILD_PAIR_READY` lease lineage are bound.

The readback is body-free and private/nonserializable. Its digest may be recorded
by Task-072, but copied fields or the digest cannot recreate the delegation or
open a role.

### 5.1 Partial transfer and bind failure

For each ordered role the bind ledger records exactly one of:

`NOT_ATTEMPTED | CHILD_DUPLICATE_CREATED | CHILD_ACCEPTED_GATE_CLOSED |
PARENT_CLOSED | CHILD_CLOSE_CONFIRMED`. An unknown observation has no enum token
and therefore cannot appear in a failed-known readback.

`TASK074_REFERENCE_CHILD_BIND_FAILED_READBACK_V1` binds attempted/accepted role
set digests, both per-role states, parent-close states, lease/bind generation,
stable reason and `owner_close_required=true`. After R11 atomic begin this
TASK-074 profile always retains either a parent original, a possibly created
child role, or the shared lease terminal obligation until an exact owner-close
readback exists; therefore `false` is not a legal derivation. It never omits a role or
converts unknown transfer/close truth into `NOT_ATTEMPTED`.

Known bind failure quiesces the shared lease and waits for Task-072's exact V3
abort claim. TASK-074 must not independently close transferred roles before
`ABORT_PENDING`; doing so could race release. Unknown transfer, channel or
delivery truth returns `OUTCOME_NOT_CONFIRMED` and forces V3 `BURNED_UNKNOWN`,
never a failed-known or effect-zero result.

The combination rule is closed: `FAILED_KNOWN` is legal only when both fixed
role rows have one exact non-unknown transfer state, both parent-close states are
known, the stable reason is not `NONE`, and the current V2 generation is proven.
Any unknown per-role transfer, physical binding, parent close, delivery or ledger
fact forbids `TASK074_REFERENCE_CHILD_BIND_FAILED_READBACK_V1`; it is
method-level `OUTCOME_NOT_CONFIRMED` and query state `AMBIGUOUS`. Because parent
authority began before bind, every legal failed-known row derives
`owner_close_required=true` until the exact ABORT_PENDING close result exists.

## 6. Body-free child preflight

The child-local fixed owner adapter calls only:

```text
preflight_reference_child_roles_v1(
    live TASK074_REFERENCE_CHILD_PREFLIGHT_AUTHORITY_V1,

    TASK074_REFERENCE_CHILD_PREFLIGHT_PROFILE_V1
) -> TASK074_REFERENCE_CHILD_PREFLIGHT_READBACK_V1
```

The fixed profile verifies, without body reads:

- exact current bound readback and `CHILD_PAIR_READY` lease;
- role count/order/access/noninheritance and child-local physical-role bindings;
- parent sensitive-handle count zero;
- prepared pair/media-policy/transcript-binding and reference-domain digests;
- Project/Profile/Consent/selection/reference/trusted-time currentness;
- Task-072 vector/bootstrap, Task-076 IN_FLIGHT, child build/image/protocol/channel
  and owner acceptance currentness;
- the exact live G06 action when required and the R9 G13 aggregate lease still
  `ACTIVE`, through the nonextractable authority validators;
- body gates closed, role read counts zero and model/Artifact/consumer false
  flags.

Preflight compares its observed coordinate byte-for-byte with the live
authority's expected `CHILD_PAIR_READY` coordinate. It emits no V2 transition;
any coordinate/generation drift rejects before the preflight ledger commit and
forces the already-defined abort/containment path.

The method-level closed outcome is:

`VALIDATED | FAILED_CLOSED_ABORT_REQUIRED | OUTCOME_NOT_CONFIRMED`.

Only `VALIDATED` and `FAILED_CLOSED_ABORT_REQUIRED` produce a committed
`TASK074_REFERENCE_CHILD_PREFLIGHT_READBACK_V1`. `OUTCOME_NOT_CONFIRMED` is the
absence of an acceptable result record and is recovered only as ledger-query
`AMBIGUOUS`; it cannot carry false effect-zero fields. `VALIDATED` is status-only input to Task-072's fixed
`validate_job_child_external_input_v3` adapter. It creates no body or model
authority by itself. A known validation failure consumes the preflight budget
and requires the serialized V3 abort claim. Exception, reply loss or any
ambiguous currentness/effect fact is `OUTCOME_NOT_CONFIRMED` and burns the V3
vector. The preflight never reads audio/transcript bytes, opens a model, creates
an Artifact handle, enters consumer code or emits a path/body/secret.

`VALIDATED` requires `preflight_gate_state=VALIDATED_BODY_GATE_CLOSED` and
`stable_reason=NONE`; `FAILED_CLOSED_ABORT_REQUIRED` requires
`preflight_gate_state=QUIESCED_ABORT_REQUIRED` and a non-`NONE` stable reason.
Both retain V2 at `CHILD_PAIR_READY` until Task-072 release or ABORT_PENDING wins;
preflight itself cannot terminalize the owner lease.

### 6.1 Same-operation reply-loss ledger query

Bind, preflight, abort close, parent-only close, terminal close, begin-arm,
begin-arm containment and recovery-revoke use one producer-private query ABI.
It is read-only and consumes no one-use budget or continuation generation:

```text
query_reference_child_ledger_v1(
    TASK074_REFERENCE_CHILD_LEDGER_QUERY_V1,
    exact authenticated producer-broker channel
) -> TASK074_REFERENCE_CHILD_LEDGER_QUERY_READBACK_V1
```

`TASK074_REFERENCE_CHILD_LEDGER_QUERY_V1` has exactly:

`contract_version:LIT[TASK074_REFERENCE_CHILD_LEDGER_QUERY_V1]`,
`record_type:LIT[REFERENCE_CHILD_LEDGER_QUERY]`, `owner_operation_id:ID`,
`query_operation_id:ID`,
`phase:ENUM[BEGIN_ARM|BEGIN_ARM_CONTAINMENT|BIND|PREFLIGHT|ABORT_CLOSE|PARENT_ONLY_CLOSE|TERMINAL_CLOSE|RECOVERY_REVOKE]`,
`phase_operation_id:ID`,
`phase_guard_kind:ENUM[ONE_USE_BUDGET|MONOTONIC_CONTINUATION]`,
`phase_guard_identity_sha256:SHA256`,
`mutating_request_identity_sha256:SHA256`,
`expected_owner_ledger_generation:U32`,
`expected_owner_ledger_head_sha256:SHA256`,
`pinned_owner_acceptance_sha256:SHA256`,
`private_channel_binding_sha256:SHA256`, `ledger_query_sha256:SHA256`.

`TASK074_REFERENCE_CHILD_LEDGER_QUERY_READBACK_V1` has exactly:

`contract_version:LIT[TASK074_REFERENCE_CHILD_LEDGER_QUERY_READBACK_V1]`,
`record_type:LIT[REFERENCE_CHILD_LEDGER_QUERY_READBACK]`,
`owner_operation_id:ID`, `query_operation_id:ID`,
`ledger_query_sha256:SHA256`,
`phase:ENUM[BEGIN_ARM|BEGIN_ARM_CONTAINMENT|BIND|PREFLIGHT|ABORT_CLOSE|PARENT_ONLY_CLOSE|TERMINAL_CLOSE|RECOVERY_REVOKE]`,
`phase_operation_id:ID`,
`phase_guard_kind:ENUM[ONE_USE_BUDGET|MONOTONIC_CONTINUATION]`,
`phase_guard_identity_sha256:SHA256`,
`mutating_request_identity_sha256:SHA256`,
`query_state:ENUM[NOT_ENTERED|COMMITTED|AMBIGUOUS]`,
`observed_owner_ledger_generation:U32`,
`observed_owner_ledger_head_sha256:SHA256`,
`observed_reference_domain:OBJ[TASK074_REFERENCE_DOMAIN_COORDINATE_UNION_V1]`,
`result_contract_version:ENUM[NONE|TASK074_REFERENCE_BEGIN_ARM_READBACK_V1|TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_READBACK_V1|TASK074_REFERENCE_CHILD_BOUND_READBACK_V1|TASK074_REFERENCE_CHILD_BIND_FAILED_READBACK_V1|TASK074_REFERENCE_CHILD_PREFLIGHT_READBACK_V1|TASK074_REFERENCE_CHILD_CLOSED_READBACK_V1|TASK074_REFERENCE_PARENT_ONLY_CLOSED_READBACK_V1|TASK074_REFERENCE_CHILD_LEASE_TERMINAL_READBACK_V1|TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_READBACK_V1]`,
`result_projection_sha256:SHA256`,
`result_delivery_class:ENUM[NONE|STATUS_REPLAYABLE|LIVE_NOT_REPLAYABLE]`,
`live_delivery_observation:ENUM[NOT_APPLICABLE|UNDELIVERED|DELIVERED_ACKNOWLEDGED|UNKNOWN]`,
`status_result:OBJ[TASK074_STATUS_RESULT_UNION_V1]`,
`effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`,
`ledger_query_readback_sha256:SHA256`.

This `effect_zero` describes only the query call's new delta. It never rewrites
or contradicts the queried operation's role/effect observation embedded in a
status result; in particular, a terminal query can have query delta zero while
the immutable terminal truth records a prior body/model effect.

`TASK074_STATUS_RESULT_UNION_V1` has exactly
`kind:ENUM[NONE|BEGIN_ARM_READBACK|BEGIN_ARM_CONTAINMENT_READBACK|BIND_FAILED_READBACK|PREFLIGHT_READBACK|CLOSED_READBACK|PARENT_ONLY_CLOSED_READBACK|LEASE_TERMINAL_READBACK|RECOVERY_REVOKE_READBACK]`
and
`record:UNION[OBJ[EMPTY]|OBJ[TASK074_REFERENCE_BEGIN_ARM_READBACK_V1]|OBJ[TASK074_REFERENCE_BEGIN_ARM_CONTAINMENT_READBACK_V1]|OBJ[TASK074_REFERENCE_CHILD_BIND_FAILED_READBACK_V1]|OBJ[TASK074_REFERENCE_CHILD_PREFLIGHT_READBACK_V1]|OBJ[TASK074_REFERENCE_CHILD_CLOSED_READBACK_V1]|OBJ[TASK074_REFERENCE_PARENT_ONLY_CLOSED_READBACK_V1]|OBJ[TASK074_REFERENCE_CHILD_LEASE_TERMINAL_READBACK_V1]|OBJ[TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_READBACK_V1]]`.
Each non-`NONE` kind selects its identically ordered exact object branch;
`NONE` selects only `OBJ[EMPTY]`. No structural-equality or untagged object
branch is decodable.

The guard identity is deterministic from the exact mutating request. A
one-use phase uses
`SHA256("TASK074_PHASE_ONE_USE_GUARD_V1\0" || JCS({phase,
phase_operation_id, phase_budget_id}))`; a containment phase uses
`SHA256("TASK074_PHASE_CONTINUATION_GUARD_V1\0" || JCS({phase,
phase_operation_id, continuation_generation,
previous_readback_sha256}))`. The named budget/generation fields are read from
the exact request bound by `mutating_request_identity_sha256`; caller-supplied
digest equality cannot create a guard. The phase mapping is closed:

| Phase | Guard kind | Committed result contract |
|---|---|---|
| `BEGIN_ARM` | `ONE_USE_BUDGET` | begin-arm readback |
| `BEGIN_ARM_CONTAINMENT` | `MONOTONIC_CONTINUATION` | begin-arm containment readback |
| `BIND` | `ONE_USE_BUDGET` | live bound projection or bind-failed readback |
| `PREFLIGHT` | `ONE_USE_BUDGET` | preflight readback |
| `ABORT_CLOSE` | `ONE_USE_BUDGET` | closed readback |
| `PARENT_ONLY_CLOSE` | `ONE_USE_BUDGET` | parent-only closed readback |
| `TERMINAL_CLOSE` | `ONE_USE_BUDGET` | lease-terminal readback |
| `RECOVERY_REVOKE` | `MONOTONIC_CONTINUATION` | recovery-revoke readback |

Its closed branches are:

| `query_state` / result class | Exact value |
|---|---|
| `NOT_ENTERED` | result version/class `NONE`, projection `ZERO_SHA256`, live observation `NOT_APPLICABLE`, status union `NONE/{}`; proves the named guard was never entered |
| `COMMITTED / STATUS_REPLAYABLE` | phase-compatible serializable result version, exact self-hash as projection, live observation `NOT_APPLICABLE`, and the same immutable result embedded in the matching status-union branch |
| `COMMITTED / LIVE_NOT_REPLAYABLE` | permitted only for `TASK074_REFERENCE_CHILD_BOUND_READBACK_V1`; exact body-free projection hash, live delivery observation, and status union `NONE/{}` |
| `AMBIGUOUS` | result version/class `NONE`, projection `ZERO_SHA256`, live observation `UNKNOWN`, status union `NONE/{}`; trusted storage cannot classify entry/commit |

`NOT_ENTERED` requires the observed ledger generation/head and exact canonical
coordinate to equal the request's predecessor with delta zero. `COMMITTED`
requires the recorded result generation/head and a phase-compatible exact
coordinate: a mutating result's final domain-edge coordinate, or the unchanged
coordinate for preflight. `AMBIGUOUS` may carry an exact last trusted coordinate
or `NOT_CONFIRMED/{}`, but neither form classifies the ledger mutation. A query
readback that mixes these coordinate/head rules is invalid, not a fourth state.

`EMPTY` is exactly the zero-key JSON object `{}`; no other empty/sentinel form is
legal. The phase/result mapping is one-to-one. A status replay does not execute
the phase again. A live-bound query never embeds, serializes or recreates the
private bound object, channel seal or preflight authority. If Task-072 lacks its
already-acknowledged live object/phase commit, even a proven projection forces
the V3 vector to `BURNED_UNKNOWN` and containment; it cannot call
`record_job_child_external_binding_v3` with the query.

`NOT_ENTERED` permits only the owning Task-072 state machine to choose its
already-defined fail-closed transition; it never grants a fresh forward retry.
For `MONOTONIC_CONTINUATION` only, it proves the named immutable generation made
no role/domain/ledger delta and permits Task-072 to submit that same generation
under the already-current containment authority. It does not increment the
generation or mint another operation; `COMMITTED` returns the recorded readback
and `AMBIGUOUS` parks that continuation. For `ONE_USE_BUDGET`, `AMBIGUOUS`
forces the exact V3 vector to `BURNED_UNKNOWN`; for containment it leaves that
already-burned vector unchanged. Wrong operation,
phase, request identity, guard, channel or ledger predecessor has effect zero on
the victim operation.

## 7. Abort-authorized close

Normal close is a separate ABI and may begin only from the exact same-operation
`JOB_CHILD_ABORT_PENDING_READBACK_V3` whose embedded Artifact truth is current:

```text
close_reference_child_roles_v1(
    TASK074_REFERENCE_CHILD_CLOSE_REQUEST_V1
) -> TASK074_REFERENCE_CHILD_CLOSED_READBACK_V1
   | OUTCOME_NOT_CONFIRMED
```

The request binds the abort-pending vector, delegation/bind/preflight lineage,
exact attempted and accepted role sets, shared lease, parent-role truth and
owner acceptance. It is neither the R12 lifecycle revoke CAS nor a public
reason string.

The close operation:

1. confirms abort won and release/start did not win;
2. permanently quiesces body entry;
3. closes any remaining parent originals;
4. requests close/revoke of each created/accepted child-local role through the
   exact child broker;
5. records each role as `ABSENT_PROVEN | CREATED_THEN_CLOSED_VERIFIED |
   CLOSE_NOT_CONFIRMED`;
6. burns/fails the shared lease and returns a body-free readback.

`CLOSED` success requires parent count zero, canonical V2 live-handle count zero,
the permanently closed body gate, both roles independently absent or
close-verified, and exactly one `V2_BURN | V2_FAIL_CLOSED` edge whose result
state equals `capability_lease_v2_terminal_state`. Missing acknowledgement,
child/channel loss or stale identity
produces no accepted closed readback and is method-level
`OUTCOME_NOT_CONFIRMED`; ledger query returns `AMBIGUOUS`, never a record with
fabricated effect-zero fields. TASK-074 never kills/waits the process, closes the
Task-072 containment Job handle, deletes an Artifact or claims Task-072 terminal
success. Task-072 alone terminates/waits and commits V3 abort after consuming the
exact owner close readback.

For this producer profile, Task-076 V3's generic
`NONE_IF_NO_ROLE_TRANSFER` branch cannot replace the owner close readback after
the R11 atomic begin. Even when both remote roles are `ABSENT_PROVEN`, TASK-074
must still close both parent originals, terminalize the shared lease and return
`TASK074_REFERENCE_CHILD_CLOSED_READBACK_V1`. The generic NONE branch is valid
only for a profile whose owner never entered and retained no parent authority;
that is not the TASK-074 prepared-reference profile.

### 7.1 Known-no-transfer parent-only close

An R11 begin-arm commit can precede child creation. The exact Task-072 V3
`ORPHAN_ABORTED`, `PREBOOTSTRAP_ABORTED` or known-no-process
`BOOTSTRAP_REJECTED` terminal therefore authorizes a distinct owner operation:

```text
close_reference_parent_roles_without_transfer_v1(
    TASK074_REFERENCE_PARENT_ONLY_CLOSE_REQUEST_V1
) -> TASK074_REFERENCE_PARENT_ONLY_CLOSED_READBACK_V1
   | OUTCOME_NOT_CONFIRMED
```

The request is accepted only when the Task-072 terminal and its
`no_role_transfer_proof_sha256` prove that process/remote-role transfer never
committed, the exact begin-arm readback committed, and the V2 lease is still
`IN_FLIGHT_PARENT_DELEGATION`. In one owner-ledger CAS, TASK-074 permanently
closes the body gate, closes both parent originals, records parent count zero and
terminalizes V2 as `BURNED` or, when semantic truth is incomplete despite proven
handle zero, `FAILED_CLOSED`. It cannot contact a child broker, close a Task-072
Job, perform remote close or use Task-076's generic
`NONE_IF_NO_ROLE_TRANSFER` as the owner result.

The exact request and result fields are in section 3.6. A successful readback
requires both `TASK074_PARENT_CLOSE_ROW_V1` rows, parent and canonical V2
live-handle counts zero, `role_transfer_state=ABSENT_PROVEN`, closed
authority/body gates, exactly one `V2_BURN | V2_FAIL_CLOSED` edge from
`IN_FLIGHT_PARENT_DELEGATION`, and the exact Task-072 terminal identity.
Known-no-process/task/role/body/model effect zero is
accepted only from the transitive Task-072 terminal plus this owner readback; the
owner record alone does not assert Task-072 process truth. Reply loss uses the
same `PARENT_ONLY_CLOSE` ledger query. A second close claim is forbidden.

### 7.2 Post-STARTED owner lease terminal

Release/start forbids abort close but does not leave the owner lease immortal.
After the exact Task-072 V3 `JOB_CHILD_STARTED_READBACK_V3`, an exact eligible
TASK-075 terminal input and exact child exit/result coordinate exist, the owner
terminal protocol uses:

```text
close_reference_child_roles_at_terminal_v1(
    TASK074_REFERENCE_CHILD_TERMINAL_CLOSE_REQUEST_V1
) -> TASK074_REFERENCE_CHILD_LEASE_TERMINAL_READBACK_V1
   | OUTCOME_NOT_CONFIRMED
```

The request accepts only the same ARMED/bootstrap/bound/preflight/STARTED
lineage and V2 predecessor `CHILD_PAIR_READY | BODY_READ_STARTED`. Its
`task075_terminal_input` has exactly two branches:

- `FINAL_CONSUMER_RESULT/TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1` binds an exact
  already-terminal ordinary consumer result whose validity does not depend on a
  TASK-074 role-close result; or
- `NONCURRENT_PRE_CLOSE_ARM_V2/TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2`
  binds the future accepted TASK-075 pre-close arm for post-release compute,
  network or combined noncurrentness.

In both branches `input_sha256` is the exact nonzero self-hash of the named
contract under the TASK-075 compatibility receipt accepted by the current owner
acceptance. For the V2 pre-close branch, its embedded STARTED, operation,
snapshot and child-exit/result coordinates must equal the separately bound
request fields byte-for-byte; equality of only the self-hash is insufficient.
The owner resolves the exact typed record from the accepted TASK-075 durable
ledger/adapter coordinate and recomputes its self-hash; a caller-supplied digest,
structurally equal mapping or receipt absence creates no terminal authority.

The V2 pre-close arm is one-use, private, body-free and pinned to one
result-formation snapshot. It binds the selected complete sorted compute/network
predicate sets, installed session, Project, operation, ticket/vector, selected
Job, child process/build, exact STARTED readback, one child exit/wait coordinate,
truthful body/model/consumer/output observations and the exact already-durable
Task014 close readbacks. It contains no TASK-074 role-close row, owner terminal
readback, R13 retirement coordinate, Task-076 terminal readback or digest derived
from any of them. The current R6
`TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1`, which already requires
TASK-074 role-close proof, is therefore not an eligible owner-close input.

The owner request cannot terminate/wait the child, decide the final consumer
union, read a body or mutate an Artifact. It verifies the already-completed
child/consumer pre-close facts, closes or proves absent each remote role through
the exact broker, preserves the truthful body/model/Artifact/consumer
observation and CASes the owner lease exactly once.

Every accepted readback requires both role-close rows to exclude
`CLOSE_NOT_CONFIRMED`, parent and canonical V2 live-handle counts zero, and the
body gate permanently closed. `two_role_completion_state=CONFIRMED |
NOT_CONFIRMED` requires a nonzero exact proof/observation digest;
`NOT_APPLICABLE` requires `two_role_completion_sha256=ZERO_SHA256`. The terminal
branches are closed:

- `CONSUMED` requires predecessor `BODY_READ_STARTED`, transition `V2_CONSUME`,
  result V2 state `CONSUMED`, the exact successful
  `FINAL_CONSUMER_RESULT` branch,
  `two_role_completion_state=CONFIRMED`, and all five body/model-call/
  Artifact-write/consumer observations `STARTED_CONFIRMED`;
- `BURNED` permits predecessor `CHILD_PAIR_READY | BODY_READ_STARTED`, requires
  transition `V2_BURN`, result V2 state `BURNED`, an exact known failure/revoke
  ordinary result or exact V2 noncurrent pre-close arm,
  `two_role_completion_state=NOT_APPLICABLE` with the zero digest, and forbids
  `UNKNOWN` in every effect observation; and
- `FAILED_CLOSED` permits the same two predecessors, requires transition
  `V2_FAIL_CLOSED`, result V2 state `FAILED_CLOSED`, and uses either
  `NOT_APPLICABLE/ZERO_SHA256` when successful two-role completion is proven
  irrelevant or `NOT_CONFIRMED/nonzero` when completion truth is unknown. Every
  unknown semantic/effect fact stays `UNKNOWN`; it cannot be upgraded to
  `BURNED` or effect zero.

For the noncurrent branch, successful owner close is only the middle step of a
versioned two-stage cross-owner ABI:

```text
TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2
-> TASK074_REFERENCE_CHILD_LEASE_TERMINAL_READBACK_V1
-> TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V2
-> Task-076 read_job_child_terminal_v3
```

The final TASK-075 V2 union is immutable and body-free. It binds the exact
pre-close-arm self-hash, the exact owner lease-terminal readback and its role
close/handle0/canonical-edge truth, the same Task014 terminal set and child-exit
coordinate, and one pre-terminal semantic closure digest. It cannot call
TASK-074, change either predicate set or observation, create another close, or
contain a future Task-076 terminal identity. Task-076 subsequently binds that
final union and the same owner terminal readback in its one semantic terminal;
there is no future-hash cycle.

#### 7.2.1 Required two-stage TASK-075 dependency descriptors

These are cross-owner acceptance requirements, not TASK-075 source authority.
The future TASK-075 amendment must freeze the following exact records before its
S2 compatibility receipt can be current.

`TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2` has exactly, in descriptor
order:

`contract_version:LIT[TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2]`,
`record_type:LIT[NONCURRENT_OPERATION_PRE_CLOSE_ARM]`,
`owner_operation_id:ID`, `terminal_input_operation_id:ID`,
`project_id:ID`, `consumer_operation_key:ID`,
`installed_instance_sha256:SHA256`, `task072_v3_vector_sha256:SHA256`,
`task043_task076_current_generation_sha256:SHA256`,
`selected_job_sha256:SHA256`, `child_bootstrap_id:ID`,
`child_image_sha256:SHA256`, `child_build_sha256:SHA256`,
`branch:ENUM[COMPUTE_ONLY|NETWORK_ONLY|COMPUTE_AND_NETWORK]`,
`compute_arm_version:ENUM[NONE|TASK075_COMPUTE_NONCURRENT_OPERATION_TERMINAL_V1]`,
`compute_arm_abi_sha256:SHA256`, `compute_arm_sha256:SHA256`,
`network_arm_version:ENUM[NONE|TASK075_NETWORK_NONCURRENT_OPERATION_TERMINAL_V1]`,
`network_arm_abi_sha256:SHA256`, `network_arm_sha256:SHA256`,
`task072_started_readback_sha256:SHA256`,
`trusted_result_formation_snapshot_sha256:SHA256`,
`child_exit_and_result_coordinate_sha256:SHA256`,
`task014_terminal_set_sha256:SHA256`,
`effect_observation:OBJ[TASK074_EFFECT_OBSERVATION_V1]`,
`body_embedded:BOOL` fixed false, `path_embedded:BOOL` fixed false,
`authority_created:BOOL` fixed false,
`pre_close_arm_sha256:SHA256`.

`COMPUTE_ONLY` requires the compute version and both compute digests nonzero and
all three network slots `NONE/ZERO_SHA256/ZERO_SHA256`; `NETWORK_ONLY` is the
inverse. `COMPUTE_AND_NETWORK` requires both named versions and all four arm
digests nonzero. Every nonzero arm ABI digest is bound by the same TASK-075
acceptance receipt, both arm self-hashes bind the same trusted snapshot and
operation, and the supplied predicate sets are complete, sorted and unique.

`TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V2` has exactly, in descriptor
order:

`contract_version:LIT[TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V2]`,
`record_type:LIT[NONCURRENT_OPERATION_TERMINAL_UNION]`,
`owner_operation_id:ID`, `terminal_input_operation_id:ID`,
`pre_close_arm_sha256:SHA256`,
`owner_lease_terminal_readback_sha256:SHA256`,
`task014_terminal_set_sha256:SHA256`,
`child_exit_and_result_coordinate_sha256:SHA256`,
`terminal_kind:ENUM[BURNED|FAILED_CLOSED]`,
`effect_observation:OBJ[TASK074_EFFECT_OBSERVATION_V1]`,
`pre_terminal_semantic_closure_sha256:SHA256`,
`body_embedded:BOOL` fixed false, `path_embedded:BOOL` fixed false,
`authority_created:BOOL` fixed false,
`terminal_union_sha256:SHA256`.

Its operation, terminal-input ID, Task014 set, child-exit coordinate and effect
observation must equal the pre-close arm. Its terminal kind and owner-readback
digest must equal the exact committed TASK-074 result. The pre-terminal semantic
closure is exactly:

```text
SHA256(
  "TASK075_NONCURRENT_PRETERMINAL_CLOSURE_V2\0" ||
  JCS({
    pre_close_arm_sha256,
    owner_lease_terminal_readback_sha256,
    task014_terminal_set_sha256,
    child_exit_and_result_coordinate_sha256,
    terminal_kind,
    effect_observation
  })
)
```

It hashes only these already-existing inputs and excludes
`terminal_union_sha256`, every Task-076 terminal identity and R13 retirement.
Both V2 records use the section 3.3 canonical ABI-descriptor and self-hash rules
with their own contract-version literal and named self-hash omitted. Unknown,
extra or reordered descriptor fields, a V1 record, a structural-equality alias
or a digest not bound by the current TASK-075 acceptance receipt is rejected.

When compute and network drift in the same pinned result-formation snapshot,
R14 accepts only one `COMPUTE_AND_NETWORK` V2 pre-close arm with both complete,
sorted predicate sets, one child-exit coordinate and one exact Task014 terminal
set. It performs one owner terminal close and one canonical edge, after which
TASK-075 may seal exactly one V2 final union. Two arm-specific inputs, a V1 final
union as close input, two remote closes, two final unions or a second Task-076
terminal call are forbidden. Exact known effect and close truth may yield
`BURNED`; any unknown body/model/Task014/role/exit fact yields
`FAILED_CLOSED | OUTCOME_NOT_CONFIRMED` as its exact truth permits.

An unconfirmed close produces no terminal readback and enters the existing
same-operation containment path. Reply loss uses the `TERMINAL_CLOSE` ledger
query and never repeats a role close. A V2 final union may be built only after
that query returns the exact committed owner readback; ambiguous owner truth
cannot be promoted to a final union. The exact
`TASK074_REFERENCE_CHILD_LEASE_TERMINAL_READBACK_V1` is the
`exact_owner_lease_terminal_readback` consumed by Task-076
`read_job_child_terminal_v3`. R13 retirement remains a later, separate CAS and
is eligible only from this exact terminal readback with handle count zero; a
generic terminal, Task-075 result, copied self-hash or unknown handle truth
cannot substitute or clear the current lease.

Until TASK-075 durably accepts both V2 contracts and publishes its exact
compatibility receipt in S2, the noncurrent branch is dependency N.C. The owner
must not consume the R6 V1 final union, and Task-076 remains on its existing
`BURNED_UNKNOWN`/containment route rather than constructing a cyclic close.

## 8. BURNED_UNKNOWN recovery revoke

Containment recovery is not normal close and cannot repair the operation:

```text
revoke_reference_child_roles_for_recovery_v1(
    TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_REQUEST_V1
) -> TASK074_REFERENCE_CHILD_RECOVERY_REVOKE_READBACK_V1
```

The request is accepted only from Task-072's exact same-vector
`BURNED_UNKNOWN` containment operation. It binds the original Project/operation,
V2 lease, attachment/begin, bootstrap child, attempted/accepted roles, last
producer ledger head and R14 owner acceptance. A durable body-free recovery
coordinate is lookup Evidence only; the trusted producer broker and exact
Task-072 containment call provide recovery authority.

For each role the readback returns exactly
`REVOKED_CONFIRMED | CLOSE_CONFIRMED | ABSENT_PROVEN | UNKNOWN`. It also binds
parent count `0 | UNKNOWN`, shared-lease terminal observation/generation and the unchanged
V3 BURNED_UNKNOWN identity. The method may close/revoke only the exact operation's
producer roles. It cannot bind, preflight, create a role, read a body, load/call
a model, release/resume a child, change Task-076 currentness, delete an Artifact
or reclassify the Job as failed-known/success.

The read-only ledger query and effect-bearing containment continuation are
distinct. Generation 1 requires
`previous_recovery_readback_sha256=ZERO_SHA256`; a later explicit Task-072
containment call keeps the same `recovery_operation_id`, increments generation
by exactly one and binds the exact previous readback. Its confirmed/remaining
role-set digests form a disjoint complete partition of the two fixed roles. It
may operate only on rows previously `UNKNOWN`; confirmed rows are immutable.
This is the canonical Task-076 same-operation containment retry, not a new
recovery operation, budget, bind or automatic retry. Wrong generation,
predecessor, partition or cross-operation input has effect zero. Unknown remains
`UNKNOWN`; it is never promoted to close proof or body/model effect zero.

Recovery does not require the original Task-043/TASK-076 Job head to remain
current. It authenticates the original immutable BURNED_UNKNOWN vector,
Project/operation and producer ledger lineage plus the exact Task-072
containment call. A later Project/Job-head advance cannot authorize or redirect
recovery, but cannot strand the exact old lease either. The acceptance and ABI
hashes pinned when that vector armed are used for decoding and authentication;
their later expiry or supersession blocks new forward work, not containment.

`CONTAINMENT_CONFIRMED` requires neither role row `UNKNOWN`,
`parent_count_state=ZERO_CONFIRMED` and
`lease_terminal_observation=BURNED|FAILED_CLOSED`, plus one committed canonical
`V2_BURN|V2_FAIL_CLOSED` edge. Any unknown role, parent, canonical edge or
lease truth requires `recovery_outcome=OUTCOME_NOT_CONFIRMED` and
`lease_terminal_observation=NOT_CONFIRMED`; it cannot manufacture an R13
retirement-eligible terminal.

## 9. Owner acceptance version and hash closure

`TASK074_TASK076_EXTERNAL_BINDING_OWNER_ACCEPTANCE_V1` is a public/body-free,
status-only implementation acceptance receipt. Its exact required fields, in ABI
descriptor order, are:

`contract_version:LIT[TASK074_TASK076_EXTERNAL_BINDING_OWNER_ACCEPTANCE_V1]`,
`record_type:LIT[TASK074_TASK076_EXTERNAL_BINDING_OWNER_ACCEPTANCE]`,
`acceptance_state:ENUM[ISSUED]`, `producer_task:LIT[TASK-074]`,
`slot_owner_task:LIT[TASK-076]`,
`downstream_consumer_task:LIT[TASK-075]`,
`task076_profile:LIT[TASK076_JOB_CHILD_BOOTSTRAP_BIND_RELEASE_V3]`,
`producer_implementation_revision_sha256:SHA256`,
`producer_implementation_receipt_sha256:SHA256`,
`producer_tester_receipt_sha256:SHA256`,
`producer_critic_receipt_sha256:SHA256`,
`producer_judge_receipt_sha256:SHA256`, `abi_bundle_sha256:SHA256`,
`role_set_sha256:SHA256`, `shared_lease_policy_sha256:SHA256`,
`task076_slot_mapping_sha256:SHA256`,
`task072_adapter_version:VERSION`, `task072_adapter_abi_sha256:SHA256`,
`task072_compatibility_receipt_sha256:SHA256`,
`task076_slot_version:VERSION`, `task076_slot_abi_sha256:SHA256`,
`task076_compatibility_receipt_sha256:SHA256`,
`task075_consumer_acceptance_version:VERSION`,
`task075_consumer_acceptance_receipt_sha256:SHA256`,
`expected_child_broker_protocol_sha256:SHA256`,
`expected_child_image_policy_sha256:SHA256`,
`expected_child_build_policy_sha256:SHA256`,
`closed_operation_profile_registry_sha256:SHA256`,
`issued_trusted_time_sha256:SHA256`, `expiry_coordinate_sha256:SHA256`,
`acceptance_generation:U32`, `currentness_coordinate_sha256:SHA256`,
`effect_zero:OBJ[TASK074_EFFECT_ZERO_V1]`,
`owner_acceptance_sha256:SHA256`.

The exact TASK-075 acceptance receipt must bind the ABI hashes and review
identities of both
`TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2` and
`TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V2`, their one-way
pre-close/owner-close/final-union order, and explicit rejection of the R6 V1
final union as owner-close input. A generic consumer version, external content
review without its durable receipt, or only one V2 contract keeps S2 and this
owner acceptance unissued.

The ABI bundle hash is:

```text
SHA256(
  "TASK074_TASK076_EXTERNAL_BINDING_ABI_BUNDLE_V1\0" ||
  JCS({
    "canonicalization": "RFC8785_JCS_UTF8_NFC_V1",
    "contracts": exact section 3.5 ordered array of
                 {"contract_version", "abi_sha256"},
    "role_set_sha256": exact role-set value,
    "shared_lease_policy_sha256": exact policy value,
    "task076_slot_mapping_sha256": exact mapping value
  })
)
```

The receipt self-hash is:

```text
SHA256(
  "TASK074_TASK076_EXTERNAL_BINDING_OWNER_ACCEPTANCE_V1\0" ||
  JCS(receipt without owner_acceptance_sha256)
)
```

There is no acceptance cycle. The order is closed:

1. the TASK-074 producer implementation receipt binds the R14 design, source
   revision, deterministic ABI descriptor hashes and fixture/review receipts; it
   does not bind a final owner-acceptance value or claim whole-Task completion;
2. Task-072, Task-076 and Task-075 compatibility receipts bind that producer
   receipt, ABI bundle and `owner_acceptance_abi_sha256`, but not a future
   `owner_acceptance_sha256` value;
3. this final owner acceptance binds those already-issued compatibility
   receipts; an operation-specific profile value then binds this final
   `owner_acceptance_sha256` and computes its own `profile_sha256`.

The acceptance does not include an operation-specific `profile_sha256`, so the
profile-to-acceptance edge is one-way. A later TASK074-C completion receipt may
bind the final acceptance; the final acceptance never takes that completion
receipt as input. The Task-072/076 adapters validate a final acceptance instance
at runtime against the already-accepted ABI and producer implementation.

The receipt's `effect_zero` has every field false. It is accepted by the Task-076
slot only together with current private producer implementation and Task-072
adapter readbacks. It cannot invoke any producer method.

This design addendum does not issue that receipt. Until source implementation,
fixtures, independent review and both cross-owner adapter acceptances exist,
its state is `NOT_ISSUED / NOT_CONFIRMED` and the external slot is ineligible.

## 10. Failure and recovery cross-owner table

| Observed seam | TASK-074 result | TASK-072/TASK-076 consequence |
|---|---|---|
| selected DISPATCHING pre-arm rejection | exact `ABSENT_PROVEN/ISSUED` or `ISSUED/ISSUED` attachment/lease tuple; pre-arm containment closes parents and terminalizes V2 with handle0 | predecessor-correct V3 rejection/terminal only; no arm, child or fabricated attachment absence |
| Task-072 arm prepared, owner begin not entered | exact query `NOT_ENTERED`; attachment/lease fail-closed under the same coordinate | reserved vector closes; process-create stays locked; no second ticket |
| owner begin committed, Task-072 final arm reply/commit lost | exact begin readback/query; no second owner CAS | finish or terminalize only the same prepared vector; ambiguous truth is BURNED_UNKNOWN |
| wrong input before exact bind-vector match | stable reject; victim bytes/revision unchanged | V3 method reject; no victim budget burn |
| bind entered, no child duplicate created, known failure | bind-failed with exact per-role `NOT_ATTEMPTED` | abort claim; no effect-zero claim until exact close/Task-072 terminal proof |
| one/both duplicates may exist | bind-failed or outcome N.C. with truthful role ledger | abort claim if known; otherwise V3 BURNED_UNKNOWN containment |
| bound and owner preflight fails known | preflight failed/abort required | Artifact handle/model/consumer effect zero; V3 abort required |
| bind/preflight reply or currentness unknown | outcome N.C. | vector-wide BURNED_UNKNOWN; never retry |
| V3 abort wins | exact close request/readback | Task-072 terminate/wait then abort commit |
| V3 known no-transfer terminal after begin | exact parent-only close/readback | parent originals close and V2 terminalizes; generic NONE cannot substitute |
| V3 release/start wins | normal close reject | owner lease closes only through exact terminal protocol |
| STARTED plus exact consumer/exit terminal | exact owner lease terminal readback | Task-076 terminal consumes it; R13 retirement may then evaluate |
| STARTED plus same-snapshot compute and network drift | one V2 `COMPUTE_AND_NETWORK` pre-close arm, one owner terminal result/canonical edge, then one V2 final union | Task-076 consumes only the final union plus the same owner readback; handle0 gates later R13 retirement; no V1-as-input, second union or remote close |
| BURNED_UNKNOWN at any phase | recovery-revoke readback with per-role confirmed/unknown | Task-072 containment; Job result remains BURNED_UNKNOWN |
| later Job head advanced before old-vector recovery | immutable original-vector containment only | newer head gives no authority and does not block old role containment |

No row allows TASK-074 to fabricate child, Artifact, body, model or consumer
effect truth owned by TASK-072/TASK-076/TASK-075.

## 11. Acceptance additions

| ID | Acceptance |
|---|---|
| A61 | TASK-074 owns one explicit, versioned producer profile for Task-076 V3; generic slot placeholders do not define Owner Voice semantics. |
| A62 | Every Task-076 slot position maps one-to-one to an exact TASK-074 version/hash and retains the original contract identity through Task-072 V3 readbacks. |
| A63 | The exact ordered two-role set is read-only, same-pair and same-shared-lease; missing/extra/reordered/independent roles are impossible. |
| A64 | `CHILD_PAIR_READY` remains body-gated; owner preflight plus Task-072 V3 release/start plus Task-075 current admission are all required before body start. |
| A65 | The live child-bind delegation is one-use, operation/vector/slot bound and cannot be reconstructed from a receipt, PID, callback, path or old TASK-074 artifact. |
| A66 | Partial transfer records exact per-role attempted/accepted/parent-close truth and never treats unknown as absent or retries a role. |
| A67 | Bound success requires both child-local roles current, both parent originals close-read back, parent count zero and every body/model/Artifact/consumer flag false. |
| A68 | Owner preflight is body-free, status-only and exact-current; VALIDATED alone creates no body/model authority. |
| A69 | Normal owner close is authorized only by the exact V3 ABORT_PENDING winner and yields independent per-role close truth before Task-072 abort commit. |
| A70 | BURNED_UNKNOWN recovery revoke is same-operation, idempotent and containment-only; it never repairs/reclassifies/rebinds the Job. |
| A71 | Owner acceptance binds the complete ABI bundle, policies, implementation/review receipts and cross-owner adapters by version and hash while creating authority zero. |
| A72 | Attachment, execution-input V2, issue/revoke CAS and R10 delegation are lineage inputs only and cannot alias an R14 bind/preflight/close/recovery method. |
| A73 | R14 design/source/native/private-audio/model/Artifact/Product/Release/Deploy/Production effects are all zero. |
| A74 | TASK-072 alone holds the live containment Job handle and owns abort; TASK-076 supplies only durable Job/current-generation/custody readback and never a live handle. |
| A75 | Exact TASK-066 compute/network-disabled evidence precedes the Task-072 ticket/vector, which precedes TASK-075 packaged-worker entry; TASK-074 cannot reorder or substitute this chain. |
| A76 | Parent reference-open/read authority is permanently removed at atomic begin and cannot return during transfer, failure, close, recovery or restart. |
| A77 | Every G01-G14 fact and the R12/R13 reference-domain plus Task-043/TASK-076 generations are exact at the named producer edge; attachment, remote close and retirement remain distinct ordered transactions. |
| A78 | Every R14 value uses one closed RFC 8785/JCS field/type/enum registry, distinct deterministic ABI hash and record self-hash; null, unknown and extra fields are impossible. |
| A79 | BEGIN_ARM, begin-arm containment, bind, preflight, abort close, parent-only close, terminal close and recovery reply loss use one exact query-only ledger ABI with `NOT_ENTERED | COMMITTED | AMBIGUOUS` and no second phase budget. |
| A80 | R11 begin is one caller-visible Task-072 V3 arm with a durable coordinator/owner-participant protocol; no cross-owner lock or second ticket exists. |
| A81 | Exact live G06 Human action and G13 aggregate lease are validated at begin; TASK-074 consumes neither, and G13 remains ACTIVE through TASK-075 authenticated pin. |
| A82 | Known V3 ORPHAN/PREBOOTSTRAP/BOOTSTRAP_REJECTED no-transfer terminals require exact parent-only close and cannot use generic NONE. |
| A83 | After STARTED, the exact TASK-075/child terminal yields the owner lease terminal readback required by Task-076 and R13 retirement. |
| A84 | Producer implementation, cross-owner compatibility, final owner acceptance and operation profile are ordered without a future-hash or completion cycle. |
| A85 | BURNED_UNKNOWN recovery authenticates the immutable original vector and remains available after current Job-head advance; the newer head supplies no effect authority. |
| A86 | A bind-failed readback is known-only, has two fully known role rows and derives `owner_close_required=true`; any unknown is BURNED_UNKNOWN, not failed-known. |
| A87 | Canonical `ReferenceDomainSnapshot` is the sole V2 truth; every mutating producer result binds one continuous predecessor/result edge committed atomically with its producer-ledger event. |
| A88 | Pre-arm containment distinguishes only `ABSENT_PROVEN/ISSUED`, `ISSUED/ISSUED` and `CONSUMED/IN_FLIGHT_PARENT_DELEGATION` attachment/lease tuples; its attachment-identity union is exactly ABSENT/zero for the first and PRESENT/exact-R11 for the latter two. |
| A89 | A committed live bound result is recoverable only as a body-free projection and delivery observation; ledger query cannot serialize or recreate the channel seal, validators or preflight authority. |
| A90 | Post-STARTED `CONSUMED`, `BURNED` and `FAILED_CLOSED` have closed predecessor/transition/result/completion/effect combinations, and every accepted terminal proves body gate closed plus parent/V2 handle0. |
| A91 | Same-snapshot compute-and-network drift uses the versioned order V2 pre-close arm -> one owner terminal close -> V2 final union -> one Task-076 terminal; the R6 V1 final union is never close input, and later R13 retirement requires exact handle0 truth. |
| A92 | Recovery continuation keeps one operation ID, increments generation exactly, binds the prior N.C. readback and may touch only its remaining `UNKNOWN` rows. |
| A93 | R10's child-local execution-input redemption remains the sole body-start entry; R14 preflight/Task-072 STARTED/Task-075 admission are additional exact guards and the only result edge is canonical `V2_BODY_READ_BEGIN`. |

## 12. Negative additions

| ID | Condition | Required result |
|---|---|---|
| N86 | missing/stale/wrong owner acceptance version/hash or implementation/review receipt | slot/bind zero; G11 remains N.C. |
| N87 | attachment, execution-input V2, issue/revoke CAS, R10 delegation or generic OWNER record is dispatched as an R14 method | reject before child/role/body/model; no compatibility fallback |
| N88 | bind before selected Task-076 IN_FLIGHT or exact Task-072 BOOTSTRAP_WAITING | bind/transfer zero |
| N89 | public/copy/deserialized/subclass/duck delegation, receipt/hash-only authority or caller hook/callback | reject; victim operation unchanged |
| N90 | role missing/extra/reordered/duplicate/writable or independent lease/policy digest | bind/preflight zero; exact bind budget classified |
| N91 | parent supplies a sensitive handle to Task-072/TASK-076/Task-075 or parent count is nonzero at bound success | no bound success or preflight VALIDATED |
| N92 | wrong Project/Profile/Consent/reference/operation/vector/slot/child/build/image/protocol/channel/session/token | reject before transfer or fail closed after exact entry |
| N93 | concurrent/second bind, per-role retry or restart rehydration | one bind budget; replay zero |
| N94 | bound success lacks either accepted-role identity, parent-close readback, closed body gate or false effect flag | no bound readback; abort/BURNED_UNKNOWN as truth permits |
| N95 | bind failure omits a role, labels unknown as NOT_ATTEMPTED or closes before V3 abort wins | contract failure; no failed-known/effect-zero claim |
| N96 | preflight reads body bytes, opens a model, creates Artifact handle/body, invokes consumer code or accepts a path/raw handle | fail closed; V3 vector burned/aborted; leak failure |
| N97 | preflight uses stale/equal public currentness, copied bound fields or a different owner acceptance | no VALIDATED result |
| N98 | Task-072 generic adapter drops or rewrites TASK-074 contract/version/hash/self-hash | V3 external binding/preflight reject; vector unchanged or burned only after exact entry |
| N99 | normal close lacks exact ABORT_PENDING, races release/start or uses a public reason/local terminal | close zero; preserve lease/vector truth |
| N100 | close success lacks per-role absent/closed proof or parent count zero | outcome N.C.; no Task-072 abort-success/effect-zero claim |
| N101 | recovery revoke uses wrong operation/vector, creates/rebinds a role, enters body/model, deletes Artifact or returns FAILED_KNOWN/SUCCEEDED | effect zero for wrong input; exact vector remains BURNED_UNKNOWN |
| N102 | TASK-074 closes a Task-072 Job handle, kills/waits by PID/name or advances Task-076 currentness | forbidden cross-owner effect; no success receipt |
| N103 | body/path/PID/raw handle/URI/argv/env/callback/audio/transcript/key/secret appears in slot, readback, log or error | privacy/security failure; authority zero |
| N104 | ABI/policy hash drifts after arm or an extra producer slot/profile appears | no bind/preflight/release; exact abort/containment only |
| N105 | fixture/design acceptance is presented as canonical owner implementation acceptance | reject; source/native/private/model effect zero |
| N106 | TASK-074 or TASK-076 receives/duplicates/closes the TASK-072 live containment Job handle, or TASK-072 delegates abort ownership | reject cross-owner route; no bind/terminal success |
| N107 | Task-072 ticket/child precedes current TASK-066 compute/network-disabled evidence, or Task-075 worker entry precedes the exact Task-072 vector | reject before child/body/model; no fallback launch |
| N108 | parent opens/reads/maps/hashes body bytes or transfers a reference role after atomic begin except exact direct child duplication/close | reject and burn/fail the exact lease; model/Artifact/consumer entry zero |
| N109 | any required G01-G14 fact is N.C./stale or the R12/R13/Task-043/Task-076 generation changes between forward ordered transactions | later forward edge zero; exact abort/containment; no automatic refresh; immutable old-vector recovery remains available |
| N110 | null/missing/extra/duplicate field, unknown enum, non-JCS value, wrong self-hash or ABI descriptor hash | reject before owner ledger/budget entry; no structural-equality fallback |
| N111 | query uses wrong phase/operation/budget/request/channel/head or returns a phase-incompatible committed result | victim ledger unchanged; no accepted result or fresh mutation authority |
| N112 | reply loss triggers a second forward mutation or a recovery mutation without exact query and, for continuation, an exact prior N.C. readback | reject replay; original guard remains the only truth; ambiguity burns vector |
| N113 | parent-only close lacks exact known-no-transfer V3 terminal or any child role may have been created | parent-only close zero; use ABORT_PENDING close or BURNED_UNKNOWN containment as truth permits |
| N114 | terminal close lacks exact STARTED, eligible ordinary result or V2 pre-close arm, child exit/result, same lease or confirmed role closure | no owner terminal readback; Task-076/R13 terminal zero |
| N115 | generic consumer terminal, copied digest, abort-closed readback or Task-076 NONE is used as owner lease terminal | reject; no Task-076 terminal or R13 retirement |
| N116 | Task-072/076/075 compatibility receipt binds a future final acceptance value, or final acceptance binds future TASK074-C completion/profile self-hash | reject circular acceptance; G11 remains N.C. |
| N117 | G06/G13 digest is supplied without the exact live broker object, G13 is not ACTIVE, or TASK-074 consumes/releases either object | begin/bind zero or fail closed after exact entry; no execution admission |
| N118 | old-vector recovery is redirected to a newer current Job head or blocked solely because the head advanced | reject redirect; contain only immutable original vector under Task-072 recovery authority |
| N119 | bind-failed contains unknown role/parent truth, stable reason NONE or `owner_close_required=false` | no failed-known readback; vector BURNED_UNKNOWN |
| N120 | implementation holds a cross-owner lock, exposes ARM_PREPARED publicly or allows process create before joint ARMED | contract failure; process/body/model/consumer entry zero; exact prepared vector closes/contains |
| N121 | pre-arm containment supplies an illegal attachment/lease tuple, mismatched query state, ABSENT/nonzero, PRESENT/zero or wrong present R11 identity | reject before parent close; exact operation remains unchanged or BURNED_UNKNOWN as prior truth requires |
| N122 | missing attachment object, path silence or receipt absence is treated as `ABSENT_PROVEN` | privacy/authority contract failure; no lease terminal or candidate-zero claim |
| N123 | a V2 edge has wrong transition/predecessor/result, discontinuity, extra edge or producer-ledger mismatch | reject before CAS/readback acceptance; unrelated and canonical deltas zero |
| N124 | `CONSUMED` is claimed from `CHILD_PAIR_READY`, without two-role completion, or with a non-`V2_CONSUME` edge | no accepted terminal; exact vector enters containment |
| N125 | `BURNED` carries an `UNKNOWN` effect, nonzero completion digest or non-`V2_BURN` edge | no known terminal/effect-zero claim; use exact `FAILED_CLOSED` or N.C. truth |
| N126 | bound ledger query embeds or reconstructs the live bound object, channel seal, validators or preflight authority | private-body/authority leak failure; object not delivered and vector burns/contains |
| N127 | recovery continuation changes operation ID, repeats/skips generation, omits the prior readback or touches a confirmed row | reject with victim rows and ledger byte-identical; no new recovery authority |
| N128 | same-snapshot compute and network drift uses the R6 V1 final union as owner-close input, splits into two pre-close arms/final unions, repeats owner close/canonical edge, or embeds a future Task-076 terminal | reject every cyclic/split branch; preserve one V2 winner or BURNED_UNKNOWN without D4 result |
| N129 | R13 retirement is attempted from unknown/nonzero handle truth, a generic terminal or before the exact owner terminal readback | retirement/next issue zero; current terminal lease remains canonical |
| N130 | body start is attempted through the external slot/query/projection/preflight digest or without exact bound/preflight/STARTED/Task-075 admission lineage | reject before body/model entry; existing body-start budget and canonical coordinate unchanged |

## 13. Fault additions

| ID | Crash/race seam | Required recovery truth |
|---|---|---|
| F52 | owner acceptance or ABI hash drifts after V3 arm but before bind | bind rejects; exact V3 abort/containment, no fallback version |
| F53 | crash after exact bind-budget entry before first duplicate | budget consumed; truthful no-transfer/unknown classification, then abort or BURNED_UNKNOWN; retry zero |
| F54 | audio duplicate/accept succeeds and transcript duplicate/accept fails | partial ledger preserved; both-role gate closed; abort claim then exact remote close, or BURNED_UNKNOWN |
| F55 | both child roles accept but one/both parent close readbacks fail | no bound success/CHILD_PAIR_READY; abort/containment and N.C. truth preserved |
| F56 | bound readback commits but reply/Task-072 record is lost | exact same-operation query only; no second transfer; unknown vector is BURNED_UNKNOWN |
| F57 | owner preflight commits VALIDATED/FAILED but reply is lost | exact preflight ledger query only; no second preflight/body entry; unresolved is BURNED_UNKNOWN |
| F58 | lifecycle revoke/expiry wins during bind or preflight | freeze next producer edge, quiesce and use V3 abort/close; R12/R13 lifecycle CAS remains distinct |
| F59 | V3 abort races preflight/Artifact release | one Task-072 vector winner; abort winner alone authorizes owner close, release/start winner forbids abort close |
| F60 | owner close commits but reply is lost | exact per-role close ledger readback; no second role close claim or Task-072 abort commit without proof |
| F61 | producer/Product restart after partial transfer or bound state | live delegation invalid; exact V3 BURNED_UNKNOWN recovery coordinate only; no bind/preflight replay |
| F62 | recovery revoke crashes between role results | query the same generation; if its N.C. readback is proven, only the next explicit generation may touch prior `UNKNOWN` rows; Job remains BURNED_UNKNOWN |
| F63 | child/channel dies after bound before preflight, or after VALIDATED before release | no body/model inference; exact abort if claimable, otherwise BURNED_UNKNOWN containment; close truth not inferred |
| F64 | Task-072 adapter throws after authenticating and entering exact owner result | only the matched V3 budget/vector burns; another operation and producer ledger remain byte-identical |
| F65 | Task-043/TASK-076 durable generation advances after Task-072 bootstrap or during owner bind/preflight | stale owner edge rejects; no rebind to the new Job; original vector aborts/contains exactly |
| F66 | TASK-066 compute/network-disabled receipt drifts or becomes unavailable between ticket and packaged-worker entry | Task-072/Task-075 entry stays closed; owner roles close/contain without model call |
| F67 | parent reference-open is attempted during partial transfer, close or recovery | open/read remains impossible; exact lease is burned/failed closed and body-read count zero is asserted only from trusted broker proof |
| F68 | owner begin-arm commits but reply is lost before Task-072 final ARMED commit | query exact BEGIN_ARM; finish/terminalize only same prepared vector; no second ticket/CAS/process create |
| F69 | Task-072 ARM_PREPARED commits but owner ledger proves begin never entered | close reserved vector and burn/fail exact attachment/lease under same coordinate; no child effect |
| F70 | begin-arm participant or coordinator durability is ambiguous | vector BURNED_UNKNOWN, process-create locked, immutable owner recovery only; no effect-zero inference |
| F71 | parent-only close commits after known-no-transfer terminal but reply is lost | query PARENT_ONLY_CLOSE; return same readback; no second parent-close claim |
| F72 | post-STARTED terminal close commits but reply is lost | query TERMINAL_CLOSE; return same lease terminal; no second role close or R13 retirement without proof |
| F73 | child/consumer terminal is known but one role close or effect observation is unknown | no CONSUMED/BURNED success; exact FAILED_CLOSED only with handle0/gates closed, otherwise containment/N.C. |
| F74 | Task-043/TASK-076 Job head advances before containment of an old BURNED_UNKNOWN vector | authenticate and contain only original vector; newer head unchanged and supplies no authority |
| F75 | compatibility review crashes between S1 and final S3 acceptance | preserve issued receipts; query/review exact hashes; never synthesize a final acceptance or cycle |
| F76 | phase ledger read is unavailable/corrupt after reply loss | query `AMBIGUOUS`; no retry; exact V3 vector BURNED_UNKNOWN |
| F77 | G13 lease or live G06 currentness changes between arm, bind and preflight | freeze next forward edge; exact abort/containment; TASK-074 never refreshes or consumes a replacement |
| F78 | pre-arm rejection occurs with attachment `ABSENT_PROVEN` or `ISSUED` while V2 remains `ISSUED` | exact ABSENT/zero or PRESENT/exact-R11 identity tuple closes parents/lease once, proves remote roles absent and records handle0; absence/identity is never inferred |
| F79 | owner begin query is `COMMITTED` but Task-072 final arm fails | require `CONSUMED/IN_FLIGHT_PARENT_DELEGATION`; preserve consumed attachment history and commit one terminal V2 edge |
| F80 | crash after `V2_CHILD_TRANSFER_BEGIN` but before `V2_CHILD_PAIR_READY` | exact query/readback exposes only the first edge and truthful role rows; no second transfer or synthetic pair-ready |
| F81 | terminal role close succeeds but canonical terminal CAS reply is lost | query the exact terminal generation; no second close/edge and no R13 retirement until the same readback is proven |
| F82 | recovery generation returns one confirmed role and one `UNKNOWN` | next explicit generation binds that N.C. readback and touches only the unknown row; query loss never becomes a new operation |
| F83 | compute and network drift simultaneously after STARTED | one V2 same-snapshot pre-close arm, one Task074 terminal/handle0 proof, one V2 final union, then one Task-076 terminal; V1-as-input or any split/second call remains BURNED_UNKNOWN |
| F84 | canonical `V2_BODY_READ_BEGIN` commits but its child reply is lost | exact R12/R13 snapshot/fence query only; no second body-start/model call and unresolved truth remains BURNED_UNKNOWN |

## 14. Verification and source-start gates

The effective matrix is A01-A93, N01-N130 and F01-F84, with R12 F34 still
replacing R11 F34. R14 implementation fixtures must cover every new row using
metadata-only, non-biometric, body-free fakes. Required assertions include:

- exact slot mapping/version/hash and all non-alias negatives;
- two-role order, one-role partial transfer and parent-close failures;
- body/read/model/Artifact/consumer counters zero through preflight;
- begin/bind/preflight/abort-close/parent-only-close/terminal-close/recovery
  reply-loss and exact query-only behavior;
- abort-versus-release and revoke/expiry races;
- wrong-operation victim bytes/revision unchanged;
- path/body/PID/raw-handle/callback/secret leakage zero;
- no TASK-074 process kill, Job-handle close or Task-076 currentness mutation.
- TASK-072-only live Job/abort ownership and TASK-076 durable-readback-only
  behavior;
- TASK-066 -> TASK-072 -> TASK-075 order and parent reference-open prohibition;
- G01-G14/domain-generation drift at every ordered producer edge.
- deterministic ABI/self-hash derivation, null/enum/unknown-field rejection and
  exact Task-076 slot field mapping;
- ARM_PREPARED participant partials with process-create locked;
- pre-arm `ABSENT_PROVEN/ISSUED`, `ISSUED/ISSUED` and committed-begin
  `CONSUMED/IN_FLIGHT_PARENT_DELEGATION` tuple closure;
- known-no-transfer parent close and post-STARTED Task-076/R13 terminal mapping;
- continuous canonical V2 edges, terminal cross-field combinations and handle0
  before R13 retirement;
- exact R10 body-start redemption with every R14/V3/Task-075 guard and
  canonical-snapshot-only reply-loss recovery;
- same-snapshot `COMPUTE_AND_NETWORK` exact V2 pre-close -> owner close -> V2
  final-union -> Task-076 terminal path, with R6 V1/cycle rejection;
- partial recovery readback followed by one same-operation next-generation
  continuation over only `UNKNOWN` rows;
- S1/S2/S3 acceptance non-cycle and old-vector recovery after current-head
  advancement.

R14 design acceptance requires fresh independent DEV-4 Critic, Tester and Judge
over the exact parent hashes and R14 hash, unresolved
`Critical/High/Medium/Low = 0/0/0/0` and Judge `PASS`.

The implementation/acceptance order is staged and non-circular:

1. `S0 DESIGN_ACCEPTED`: R14 is accepted; TASK-043 currentness and R9-R13
   producer receipts are canonical; exact future source/test Allowed Files,
   sole-writer and clean dedicated worktree are separately allocated.
2. `S1 PRODUCER_IMPLEMENTED`: only then may TASK074-C implement these ABIs and
   body-free fixtures. Independent DEV-4 review issues the producer
   implementation receipt binding the deterministic descriptors. It does not
   issue final owner acceptance or claim TASK074-C complete.
3. `S2 CROSS_OWNER_COMPATIBLE`: TASK-072 may implement its fixed V3 adapter,
   TASK-076 its exact slot/coordinate and TASK-075 its consumer fixture plus the
   two-stage noncurrent V2 pre-close/final-union contracts against the S1 receipt
   and owner-acceptance ABI. Each publishes its own compatibility receipt; none
   guesses the final acceptance value or uses the cyclic R6 V1 union as input.
4. `S3 OWNER_ACCEPTED`: TASK-074 verifies those exact receipts and issues the
   final owner acceptance. Only then can an operation profile value be current,
   G11 close and TASK074-C completion be judged.

No stage authorizes a source writer in another Task. An unavailable later stage
parks that dependency without relabeling an earlier stage PASS.

TASK074-D native validation additionally requires the existing bounded
non-biometric Windows fixture gate and explicit native authority. Real Owner
audio, private body access, model load/inference, OBS, Product UI, Release,
Deploy and Production Activation remain separate Human Gates and are not
authorized by R14.
