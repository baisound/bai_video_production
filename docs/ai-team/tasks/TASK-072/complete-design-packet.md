# TASK-072 — One-shot Product Operation Ticket and Config Resolver

Status: `DESIGN_COMPLETE / DEV-4 / SOURCE_START0`

Design identity: `TASK072-PTD-OPERATION-BROKER-V1`

Canonical design base: `origin/main@35cdf1ad475633dcf035e0616e979b5a8fde0c88`

Owner allocation: `2026-09-01 / Platform Trust & Delivery / Design B`

## 1. Decision

TASK-072 owns one Product-private Windows operation broker and one immutable,
operation-specific config resolver. The broker is the only Production boundary
that may create or redeem a one-shot non-Human operation capability. A public
dataclass, JSON document, hash, module token, environment variable, CLI option,
fixed config file, caller-selected clock, or Python-private sentinel never
creates authority.

The fixed Canonical SKILL distribution config remains the immutable disabled
sentinel. TASK-072 does not replace, enable, repair, or delete it. When a
specific operation is authorized, the trusted Product runner publishes an
immutable config v2 at an operation-specific coordinate, starts the exact child
with `--config`, and transfers an opaque broker channel handle only to that
child. The adapter must redeem the live handle before one exact command. A
copied config without the live broker handle has effect zero.

TASK-072 creates non-Human operation authority only. It never manufactures a
Human decision. Actions that require explicit Human approval additionally need
a fresh TASK-071 receipt; the TASK-072 ticket only authorizes the bounded
machine step after that independent Human gate.

## 2. Responsibility and non-responsibility

TASK-072 owns:

- Product-private broker process composition and its authenticated local IPC;
- server-generated random operation and ticket identities;
- one-use action, command, instance, build, receipt and expiry binding;
- immutable operation-config v2 construction and publication;
- exact child-process binding, first-redemption burn and terminal projection;
- restart/crash behavior that never reactivates an issued ticket;
- a versioned fixture port so downstream Tasks may develop before native broker
  packaging is available;
- body-free public status and receipt projections.

TASK-072 does not own:

- TASK-068 file-I/O primitives or current/head selection;
- TASK-070 installer authority pair semantics;
- TASK-071 Human-visible consent or Windows Hello semantics;
- TASK-060 promotion/rollback policy, cipher, source or store;
- TASK-061 migration, Profile binding, activation plan or activation history;
- TASK-067 canonical admission semantics;
- TASK-036 installed connector command semantics or UI workflow;
- TASK-065 PL-A/B/C/D orchestration semantics;
- TASK-066 probe interpretation, GPU ranking or workload policy;
- Canonical SKILL schemas, privacy projection, delivery staging or profile
  interpretation;
- BVP File Bridge private claim, journal, pending, canonical or Profile stores;
- any Release, Deploy, Production Activation, paid Provider, model download,
  native user-data effect, external account mutation, or physical garbage
  collection.

## 3. One-way artifact/phase dependency graph

Task names alone are too coarse because TASK-072 supplies an early core port and
later binds installed producer receipts. Completion is therefore expressed as
acyclic artifact/phase edges:

```text
TASK-068 IMMUTABLE_SECURE_IO_V1
    -> TASK-072-A BROKER_CORE_AND_FIXTURE_V1

TASK-072-A OP_TICKET_CORE_V1
TASK-063 PRETERMINAL_SELECTED_INSTALL_PLAN_ABI_V1
    -> TASK-070 PAIR_EFFECT_V2

TASK-070 PAIR_TERMINAL_V2
TASK-063 INSTALLATION_READBACK_V2
    -> TASK-072-B INSTALLED_INSTANCE_PROFILE_BINDING_V1

TASK-060 PROMOTION_ACTION_ABI_V1
TASK-071 HUMAN_ACTION_ABI_V1
    -> TASK-072-C ACTION_REGISTRY_V1
    -> TASK-060 PROMOTION/ROLLBACK_EFFECT

TASK-061-A CA_A_CA_B_ACTION_ABI_V1
TASK-072-A OP_TICKET_CORE_V1
TASK-060 SOURCE_READBACK_V2
TASK-063 INSTALLATION_READBACK_V2
TASK-070 PAIR_TERMINAL_V2
    -> TASK-061-A CA_A_CA_B_EFFECT

TASK-066 GPU_ACTION_ABI_V1
TASK-072-A OP_TICKET_CORE_V1
    -> TASK-066 GPU_REQUIRED_EFFECT

Canonical SKILL D2S ACTION_ABI_V2 + INSTALLED_PACKAGE_RECEIPT_V2
TASK-036 D2S_OPERATION_PLAN_ABI_V1
TASK-063 INSTALLATION_READBACK_V2
TASK-070 PAIR_TERMINAL_V2
    -> TASK-072-D-PURE PACKAGED_GENERIC_CLI_BINDING_V1
    -> TASK-036 PACKAGED PURE COMMAND EFFECTS

Canonical SKILL D2S ACTION_ABI_V2 + INSTALLED_PACKAGE_RECEIPT_V2
TASK-065 D2S_STATUS_OPERATION_PLAN_ABI_V1
TASK-063 INSTALLATION_READBACK_V2
TASK-070 PAIR_TERMINAL_V2
    -> TASK-072-D-STATUS CONNECTOR_STATUS_BINDING_V1
    -> TASK-065 CONNECTOR STATUS EFFECT

Canonical SKILL D2S PRIVACY_PROJECTION_RECEIPT_V2
TASK-061-A ENABLED_FALSE_PREACTIVATION_RECEIPT_V1
TASK-063 INSTALLATION_READBACK_V2
TASK-070 PAIR_TERMINAL_V2
TASK-069 STAGING_ACTION_ABI_V1
    -> TASK-072-D-STAGE PUBLISH_STAGE_BINDING_V1
    -> TASK-065 ONE-SHOT STAGING EFFECT

Canonical SKILL D2S INSTALLED_PACKAGE_RECEIPT_V2
TASK-063 INSTALLATION_READBACK_V2
TASK-070 PAIR_TERMINAL_V2
TASK-069 TERMINAL_CORRELATION_PROFILE_ABI_V1
TASK-067 SEALED_CURRENT_COORDINATE_RECEIPT_V1
TASK-065 PRIOR_OPERATION_TERMINAL_PLAN_ABI_V1
    -> TASK-072-D-TERMINAL-PROFILE BINDING_V1
    -> PRODUCT BROKER TERMINAL QUERY / D2S LOAD-PROFILE EFFECT

TASK-036 STAGE_RECEIPT_CORRELATION_PROFILE_READBACK_V1
TASK-072-D-PURE / D-STATUS / D-STAGE / D-TERMINAL-PROFILE receipts
    -> TASK-072-D-ROUNDTRIP-E2E COMPLETION_BINDING_V1
    -> TASK-036 REAL INSTALLED E2E RECEIPT_V2

TASK-061-B ACTIVATION_ACTION_ABI_V1
TASK-071 HUMAN_AUTHORIZATION_RECEIPT_V1
TASK-036 REAL_INSTALLED_E2E_RECEIPT_V2
TASK-067 SEALED_CURRENT_COORDINATE_RECEIPT_V1
    -> TASK-072-C ACTIVATION REGISTRY PROFILE
    -> TASK-061-B FINAL EFFECT

All exact completion receipts
    -> TASK-065 PL-A/B/C/D
```

Producer `*_ACTION_ABI_*` documents are versioned design/fixture contracts, not
effect receipts. They can freeze before producer source completion. TASK-072-A
therefore unblocks fixture, protocol and packaging work without waiting for
TASK-070 or TASK-071. TASK-072-D-PURE and D-STATUS do not wait for Profile
terminal/current-coordinate receipts. D-STAGE waits only for its privacy,
enabled-false, install/pair and staging-ABI inputs. D-TERMINAL-PROFILE and
D-ROUNDTRIP-E2E alone wait for the later terminal/correlation/Profile evidence.
TASK-072-B/C and each D subphase cannot claim its own action profile complete
until that subphase's exact producer receipts are canonical.
This removes task-level `TASK-072 <-> TASK-070` and
`TASK-072 <-> TASK-060/TASK-071` cycles.

TASK-068 Draft PR `#472` is a design/source input only until its exact completion
receipt is canonical on `main`. TASK-072 source may compile against a versioned
fixture adapter before then, but Production binding and any effect-bearing
native result remain `DEPENDENCY_NC`.

## 4. Design PR scope

This design PR may change exactly:

- `docs/ai-team/tasks/TASK-072/complete-design-packet.md`

It must not change source, schema, tests, fixtures, packaging, shared current
state, roadmap, task index, registry, CHANGELOG, another Task document, or any
existing Draft PR.

## 5. Future implementation ownership

After this packet reaches independent Critic `C/H=0` and Judge `PASS`, the
TASK-072 implementation Task may change exactly:

- `src/ai_video_production/product_operation_broker.py`
- `src/ai_video_production/product_operation_config.py`
- `packaging/task072_product_operation_broker_windows_entry.py`
- `schemas/product-operation-ticket.schema.json`
- `schemas/product-operation-config.schema.json`
- `schemas/product-operation-receipt.schema.json`
- `src/ai_video_production/schema_resources/product-operation-ticket.schema.json`
- `src/ai_video_production/schema_resources/product-operation-config.schema.json`
- `src/ai_video_production/schema_resources/product-operation-receipt.schema.json`
- `tests/test_task072_product_operation_broker.py`
- `tests/test_task072_product_operation_config.py`
- `tests/test_task072_product_operation_broker_windows.py`
- `tests/test_task072_product_operation_packaging.py`
- `tests/fixtures/task072/**`
- `docs/ai-team/tasks/TASK-072/**`

Any change to `pyproject.toml`, installer scripts, TASK-036 Shell, TASK-058 File
Bridge, TASK-060, TASK-061, TASK-063, TASK-065, TASK-066, TASK-067, TASK-068,
TASK-070, TASK-071, Canonical SKILL source/config, shared docs or CHANGELOG
requires the owning Task's separate exact amendment and overlap check.

## 6. Production boundary

### 6.1 Broker process

The Production broker is a separate packaged Product helper process. Python
module privacy is not an authority boundary. Importing a module, reaching an
underscore name, reconstructing a class, monkeypatching a verifier, or knowing
every public field must not create a usable capability.

The parent Product process creates a private duplex channel and starts the
broker with a Windows restricted inherited-handle list. There is no public TCP
listener, discoverable localhost API, filesystem socket, user-selectable pipe
name, or argv token. The broker accepts requests only over the inherited handle
and authenticates the parent/child process tuple using native process identity,
Windows access token SID/session/logon LUID, packaged image identity, build
digest and launch nonce.

For an adapter child, the broker duplicates a new operation channel handle only
into the exact child process. The child receives no reusable bearer secret in
argv, environment, config or stdout. The handle is non-inheritable by default;
the exact child handle list is the sole exception. Grandchildren receive no
broker handle.

The Production composition fixes internally:

- native Windows process/token/security backend;
- trusted clock implementation and boot/session coordinate;
- TASK-068 implementation identity and version;
- Product build and packaged-helper digests;
- action-profile registry version;
- IPC protocol version.

No argv, config, JSON, public plan, serialized receipt, environment variable,
dependency injection, monkeypatch, hook or failure injector may select or
replace those implementations. Test backends exist only in a non-Production
composition not shipped or reachable from packaged Product entrypoints.

### 6.2 Threat boundary

The broker protects against public API callers, direct CLI replay, copied files,
deserialization, module introspection and a separately launched same-user
process that possesses no inherited operation handle and does not compromise a
trusted process.

TASK-072 v1 does **not** claim resistance to an arbitrary same-user process that
can obtain `PROCESS_DUP_HANDLE`, `PROCESS_VM_READ`, `PROCESS_VM_WRITE`, code
injection, debugger or equivalent access to the trusted Product/broker/child.
No native test may promote that unsupported attacker model to PASS. A stronger
service-SID/AppContainer process-isolation boundary would require a separate
Task with installer/service DACL, process mitigation, job-object and package
ownership authority. Administrator compromise and replacement of a trusted
packaged image are likewise outside v1. Direct invocation/copy/replay remains
effect zero; arbitrary process compromise is explicitly `NOT_SUPPORTED_V1`.

### 6.3 Authenticated IPC protocol

The Product launches the exact packaged child and transfers one restricted,
non-named operation channel handle. The wire protocol is closed and framed:

- each frame is a 4-byte little-endian unsigned length followed by one strict
  canonical UTF-8 JSON message;
- one frame is at most 64 KiB and one complete transcript is at most 256 KiB;
- every message binds protocol magic/version, a closed message-kind enum,
  broker-generated nonce, opaque operation/ticket IDs, monotonically exact
  sequence number, predecessor transcript hash and current transcript hash;
- messages carry only bounded hashes/coordinates required by the selected
  action profile; raw payloads, paths, argv, secrets and native handle values
  are forbidden;
- the challenge/response transcript is bound to the live server record and the
  inherited channel object, not merely to copied nonce text.

The broker rejects oversized or truncated frames, duplicate/non-finite JSON,
unknown message kinds/fields, wrong sequence, replayed frames, challenge or
transcript mismatch and trailing bytes. Before accepting authentication and
again before `IN_FLIGHT`, it revalidates the exact child image/build, process
token, SID/session/logon LUID, parent relationship and channel-handle identity.
The parent revalidates the exact child plus pinned config identity after launch
and before accepting terminal output. An unauthenticated peer receives only a
generic close and cannot query, identify or burn another operation. Once an
authenticated child presents its first redemption frame, every semantic
failure burns that ticket.

## 7. Versioned ports

### 7.1 `OPERATION_REQUEST_V1`

Public request/status data only; `authority_created=false`. Closed fields:

- `message_type = BvpProductOperationRequest`
- `schema_version = 1.0.0`
- `request_id` generated by Product UI/controller, display correlation only;
- `action_profile` from the frozen enum;
- opaque hashes of required upstream receipts;
- `requested_state = REQUESTED`;
- `authority_created = false`.

It contains no ticket, nonce, clock value, filesystem path, raw command, secret,
document body or backend selector.

### 7.2 `CONSUMER_OPERATION_AUTHORIZATION_V1`

This is a consumer-owned private issuance port. The broker issues nothing from
`OPERATION_REQUEST_V1`, public receipt hashes or UI state. The owning trusted
Product operation supplies a live authorization verified by an internally fixed
consumer-specific verifier. It binds:

- stable `consumer_operation_key`, derived from the complete intended-effect
  fingerprint and unchanged by UI/request ID;
- exact consumer Task/action/profile/version;
- exact durable plan identity, revision, predecessor and currentness receipt;
- exact issuer Product process/build/backend identity;
- exact install instance or preterminal selected-install plan;
- complete action-specific producer receipt set and schema versions;
- expected config parent resolver identity;
- expiry, boot/session and invocation budget one;
- authorization self-fingerprint verified by the owning consumer, not by a
  caller-computable hash alone.

The Production verifier/factory is neither public nor replaceable through a
Python module, constructor, mapping, argv, config or serialized receipt. Because
Python introspection is not an authority boundary, the live authorization is
delivered over the authenticated Product-to-broker handle and correlated with
server-observed process/build/session state. Public representations are audit
only and declare `authority_created=false`.

If the authorization, exact producer set, plan currentness or verifier identity
is absent/mismatched, issuance stops before reservation/ticket/config/child
effect. A public request can never ask the broker to mint an unbound ticket.

### 7.3 `ISSUANCE_RESERVATION_V1`

Before generating or returning a ticket, the broker publishes a durable
no-replace reservation at an exact coordinate derived from the opaque SHA-256
of `consumer_operation_key` under the consumer's trusted operation parent. It
binds the full authorization fingerprint, random ticket/operation identities,
broker boot/session/build and the expected first event coordinate.

The stable key fences semantic duplicate issuance across new request IDs,
processes, broker restarts and random ticket IDs. A reservation collision is
STOP+preserve, including identical bytes or same body/different inode. The
broker may securely read the exact reservation for diagnosis, but it does not
issue again from it.

If an owning consumer proves through an exact durable reconciliation receipt
that the prior operation had no effect and is safe to retry, it creates a fresh
plan revision and therefore a new `consumer_operation_key` that binds the old
reservation and reconciliation receipt as predecessor. `IN_FLIGHT`,
`BURNED_UNKNOWN`, missing terminal, ambiguous state or receipt-only evidence
never permits fresh issuance.

### 7.4 `OP_TICKET_V1`

This is a broker-private server record, never JSON-constructible by callers. It
binds:

- cryptographically random `operation_id` and `ticket_id`, each at least 128
  bits of entropy;
- exact action profile and one exact command/subcommand;
- exact argument-vector digest, with no shell interpretation;
- invocation budget `1`;
- install instance and TASK-070 terminal identity when applicable;
- expected config canonical hash and physical identity;
- source, profile, record, delivery and expected-result digests required by the
  selected profile;
- Product build, broker build, adapter/helper build and backend identities;
- Windows user SID, session ID, logon LUID, parent process and exact child
  process identity;
- broker boot/session coordinate, monotonic issue/deadline values and bounded
  UTC audit time;
- required upstream receipt type/version/hash/identity tuples;
- optional TASK-071 Human receipt identity for Human-gated actions;
- state revision and predecessor event identity.

The public audit projection exposes only opaque hashes and state; it always
states `authority_created=false`. The live broker-side state plus the exact OS
channel handle is the capability.

### 7.5 `OPERATION_CONFIG_V2`

The immutable operation-specific config has a closed strict schema:

- `message_type = BvpOperationSpecificConfig`
- `schema_version = 2.0.0`
- `contract_profile` and exact command/subcommand;
- operation/ticket opaque identifiers;
- install instance and bound upstream receipt hashes;
- expected input record/profile/delivery/result digests;
- Product/adapter/config-projection build digests;
- monotonic/UTC expiry projection;
- `invocation_budget = 1`;
- `distribution_config_mutated = false`;
- `authority_created = false`;
- document self-hash.

The config contains no absolute root, delivery, receipt, profile or executable
path; no broker endpoint; no secret; no native handle value; no raw private
payload; and no caller-selectable backend, clock, hook or failure mode.

It is canonical UTF-8 JSON, published once through TASK-068 at a bounded
operation-specific relative coordinate. Existing target, same-body/different-
inode target, or unknown collision is STOP. Content equality never authorizes
adoption or `DUPLICATE`.

### 7.6 `BROKER_REDEMPTION_RECEIPT_V1`

The private terminal binds:

- ticket and state-event identity;
- action/command and argv digest;
- config raw/canonical hash and physical identity;
- child process/token/build identity;
- redemption monotonic coordinate;
- consumer result digest and exact upstream/downstream receipt identities;
- state `COMMITTED`, `REJECTED`, or `BURNED_UNKNOWN`;
- predecessor event identity and self-hash.

The public projection contains only stable codes, opaque IDs/hashes, count and
boolean fields. It never contains paths, command bodies, configuration bodies,
OS error text, SIDs, process command lines, sensitive values or raw adapter
output. Public projection remains evidence, not a capability.

### 7.7 `OP_TICKET_EVENT_V1`

Every broker state transition has an immutable, no-replace event at an exact
operation coordinate. `ISSUED` is durable before the live handle is returned;
`IN_FLIGHT` is durable before the consumer effect; and a terminal event is
durable after result capture. Each event binds its exact predecessor digest and
identity, broker boot/session, action, config and child identity.

TASK-072 never scans a directory to select current/highest/latest. The live
broker keeps the exact next coordinate; consumer recovery supplies the exact
operation/event coordinate from its trusted operation plan. An event chain is
audit/recovery evidence only and cannot recreate a live OS handle. After a
broker restart, a prior `ISSUED`, `CONFIG_READY` or `CHILD_BOUND` event is
classified `BURNED_BY_SESSION_MISMATCH` when read at its exact coordinate.

If durable `IN_FLIGHT` publication fails, the ticket is burned and the child
effect does not start. If the effect succeeds but terminal publication or final
readback fails, the result is `BURNED_UNKNOWN`; only the owning consumer's exact
durable readback may reconcile it, and the operation command is not replayed.

### 7.8 `BROKER_TERMINAL_STATUS_V1`

A read-only terminal query may report a state already known by the broker or by
a separately pinned Product receipt. It performs no adapter delivery creation,
canonical admission, Profile publication or replay. It cannot convert a
receipt-only observation into `COMMITTED`.

### 7.9 `CONFIG_PARENT_BINDING_V1`

TASK-072 accepts no caller path. The owning consumer supplies a private trusted
resolver capability that binds one pre-existing operation directory to its
install instance, Task/operation key, ancestor/security snapshot and expected
Task-068 root identity. TASK-072 revalidates that binding before config
publication, child launch, child pinned read and final readback.

For installed D2S operations this resolver is produced from exact TASK-070
`PAIR_TERMINAL_V2`, TASK-063 `INSTALLATION_READBACK_V2` and the TASK-065
operation-root plan. For install bootstrap it is produced from the TASK-063
preterminal selected-install plan. For GPU operations it is a Product-private
TASK-066 operation root. A public path, raw external root, fixed ProgramData
fallback, current working directory or environment variable creates no binding.

### 7.10 Early fixture contract

`tests/fixtures/task072/operation-port-v1/**` will contain versioned, static,
non-authoritative fixtures for each action profile. Every fixture declares:

- `fixture_only=true`;
- `authority_created=false`;
- `native_broker_executed=false`;
- fixed fake build/instance/hash coordinates;
- the expected public request/config/receipt shape;
- negative vectors for wrong action, command, receipt and state.

Downstream L1/L2/L3 work may compile and test against these fixtures. A fixture
PASS cannot satisfy Production, native, installed, E2E or activation gates.
Final binding requires the canonical TASK-072 implementation receipt plus exact
packaged/native readback.

## 8. Frozen action profiles

The v1 registry contains only:

| Action profile | Consumer | Additional prerequisites | Authorized effect |
|---|---|---|---|
| `INSTALL_AUTHORITY_PAIR_WRITE` | TASK-070 | TASK-068 real binding; trusted selected install operation | One exact TASK-070 pair operation |
| `MIGRATION_CA_A_EXECUTE` | TASK-061-A | TASK-063 instance; exact migration plan | One exact CA-A execution |
| `PROFILE_BIND_CA_B_EXECUTE` | TASK-061-A | TASK-060 source; TASK-063 instance; exact CA-B plan | One exact CA-B publication operation |
| `GPU_REQUIRED_LAUNCH` | TASK-066 | private trusted probe capability; exact workload/profile/build | One exact GPU-required worker launch |
| `D2S_VALIDATE` | Canonical SKILL/TASK-036 | exact generic input/profile/schema digests | One exact `validate` command |
| `D2S_EMIT_PROPOSAL` | Canonical SKILL/TASK-036 | exact input/Manifest/profile digests | One exact proposal command |
| `D2S_FEEDBACK_TO_LEARNING` | Canonical SKILL/TASK-036 | exact proposal/feedback/privacy-projection digests | One exact learning-export command |
| `D2S_ROUND_TRIP` | Canonical SKILL/TASK-036 | exact input/feedback/Manifest digests | One exact round-trip command |
| `D2S_CONVERT_FRAME` | Canonical SKILL/TASK-036 | exact source/target rational FPS and frame | One exact frame-conversion command |
| `D2S_VALIDATE_TASK056_SIDECAR` | Canonical SKILL/TASK-036 | exact installed TASK-056 schema, projection hash and Asset binding | One exact `validate-task056-sidecar` command |
| `D2S_CONNECTOR_STATUS` | Canonical SKILL/TASK-065 | installed D2S receipt; TASK-070 instance | Read-only connector status |
| `D2S_PUBLISH_LEARNING` | Canonical SKILL/TASK-065 | installed D2S receipt; TASK-070 instance; exact privacy-safe payload digest | One exact staging command |
| `PRODUCT_BROKER_TERMINAL_QUERY` | TASK-065 Product runner | prior operation identity and Product terminal/correlation binding | Broker-only read-only query; child/config/adapter/delivery delta zero |
| `D2S_LOAD_PROFILE` | Canonical SKILL/TASK-065 | TASK-067 sealed current coordinate | One exact advisory Profile read |
| `PRODUCT_D2S_ROUNDTRIP_E2E_VERIFY` | TASK-036 Product runner | exact stage/public receipt/correlation/Profile readback set | Broker-only completion verification; adapter/delivery/Profile mutation zero |
| `ACTIVATION_CONFIG_FINALIZE` | TASK-061-B | TASK-071 Human receipt; TASK-036 real E2E; TASK-067 receipt | One exact final config transaction |

Promotion and rollback actions are not in v1 until TASK-060 and TASK-071 freeze
their joint profile. Adding one is a versioned registry change, not a free-form
action string.

TASK-072 never treats `MIGRATION_CA_A_EXECUTE` or
`PROFILE_BIND_CA_B_EXECUTE` as Human actions. They use non-Human Product tickets.
`ACTIVATION_CONFIG_FINALIZE` additionally requires a separate TASK-071 Human
receipt. A migration/profile ticket cannot be used for activation.

The `D2S_*` action rows mirror the currently installed generic adapter
commands; `PRODUCT_BROKER_TERMINAL_QUERY` is intentionally a Product broker
operation and starts no adapter child or config. The registry does not invent
`task055-bridge` as a generic CLI command. Exact TASK-055
`BVP_MONTAGE_SKILL_INPUT` / `MONTAGE_PROPOSAL_BUNDLE` validation remains a
separate BVP-owned contract profile and must use the authoritative BVP schemas
and canonical hashes. If its Product operation later needs broker authority, it
receives a separately allocated versioned action profile; it is never routed
through `D2S_VALIDATE` or silently reinterpreted as the generic schema.

### 8.1 Exact issuance-authority producer matrix

Every row is closed. Unknown producer type/version or an extra/missing receipt
fails before `ISSUANCE_RESERVATION_V1`.

| Action family | Private authorization producer/version | Exact required producer evidence |
|---|---|---|
| `INSTALL_AUTHORITY_PAIR_WRITE` | TASK-063 `PRETERMINAL_SELECTED_INSTALL_PLAN_ABI_V1` | selected-root handle/identity; intended instance; package/build manifest; Task-068 binding; config-parent binding; no TASK-070 terminal is required for first install |
| `MIGRATION_CA_A_EXECUTE` | TASK-061-A `CA_A_OPERATION_AUTHORIZATION_V1` | exact migration plan/revision; TASK-063 installation readback; TASK-070 pair terminal; TASK-069 bridge-security readback; source/snapshot currentness |
| `PROFILE_BIND_CA_B_EXECUTE` | TASK-061-A `CA_B_OPERATION_AUTHORIZATION_V1` | exact CA-B plan/revision; TASK-060 promoted-source readback; TASK-063 installation readback; TASK-070 pair terminal; TASK-069 Profile publication/security ABI |
| `GPU_REQUIRED_LAUNCH` | TASK-066 `GPU_OPERATION_AUTHORIZATION_V1` | live private trusted probe capability; exact run/helper/backend/layout/profile/workload/build; Product operation root |
| Generic D2S pure commands | TASK-036 `D2S_OPERATION_AUTHORIZATION_V1` | exact packaged Product operation plan; installed SKILL/package/schema receipt; exact input/Manifest/feedback/sidecar hashes required by the selected command; TASK-063/TASK-070 installed instance for Production routes |
| `D2S_CONNECTOR_STATUS` | TASK-065 `D2S_STATUS_OPERATION_AUTHORIZATION_V1` | exact installed SKILL receipt; TASK-063 installation readback; TASK-070 pair terminal; operation config parent |
| `D2S_PUBLISH_LEARNING` | TASK-065 `D2S_PUBLISH_OPERATION_AUTHORIZATION_V1` | exact privacy-safe export projection receipt; installed SKILL receipt; TASK-063/TASK-070 instance; TASK-061-A enabled-false preactivation receipt; TASK-069 staging action ABI; exact record/delivery digest |
| `PRODUCT_BROKER_TERMINAL_QUERY` | TASK-065 `PRODUCT_TERMINAL_QUERY_AUTHORIZATION_V1` | installed SKILL receipt; TASK-063 installation readback; TASK-070 pair terminal; TASK-069 terminal/correlation ABI; TASK-067 sealed current coordinate; exact prior reservation/ticket/event coordinates and pinned Product terminal/correlation readback; no adapter/config/delivery body |
| `D2S_LOAD_PROFILE` | TASK-065 `D2S_PROFILE_READ_AUTHORIZATION_V1` | TASK-069 exact Profile terminal; TASK-067 sealed current coordinate; TASK-063 installation readback; TASK-070 pair terminal; installed SKILL receipt |
| `PRODUCT_D2S_ROUNDTRIP_E2E_VERIFY` | TASK-036 `D2S_E2E_VERIFICATION_AUTHORIZATION_V1` | exact adapter-stage receipt; BVP import receipt; public receipt; hidden Generic correlation; Profile terminal/readback; TASK-072 D-PURE/D-STATUS/D-STAGE/D-TERMINAL-PROFILE receipts; no adapter rerun |
| `ACTIVATION_CONFIG_FINALIZE` | TASK-061-B `ACTIVATION_OPERATION_AUTHORIZATION_V1` | TASK-061-A exact activation plan and expected current config revision; TASK-071 fresh Human receipt; TASK-036 real installed E2E receipt; TASK-063 installation readback; TASK-069 Profile terminal; TASK-070 pair terminal; installed D2S receipt; TASK-067 sealed current coordinate |

Promotion/rollback registry additions require TASK-060
`PROMOTION_ACTION_ABI_V1` / `ROLLBACK_ACTION_ABI_V1` plus TASK-071
`HUMAN_ACTION_ABI_V1` to freeze first. The registry version is then advanced
before TASK-060 effect implementation. TASK-060 effect completion is not a
prerequisite for registry design, so no cycle exists.

Each private producer must bind a stable `consumer_operation_key`; public
receipt hashes in the table are lookup/display projections only. The broker
uses internally fixed producer verifiers and exact durable plan/currentness
readers. Equality of caller-provided fields never substitutes for a producer.

## 9. State machine

```text
REQUESTED (audit only)
  -> AUTHORIZED (exact private consumer authorization verified)
  -> RESERVED (durable no-replace semantic-effect fence)
  -> ISSUED (durable event + live server record + private channel)
  -> CONFIG_READY (immutable config exact readback)
  -> CHILD_BOUND (exact process/token/build)
  -> IN_FLIGHT (first valid redemption; budget consumed immediately)
       -> COMMITTED
       -> REJECTED
       -> BURNED_UNKNOWN

ISSUED / CONFIG_READY / CHILD_BOUND
  -> BURNED on expiry, channel close, child exit, broker stop or restart
```

Rules:

1. A public request cannot advance state. `AUTHORIZED` requires the exact live
   private producer and all profile-specific durable plan/currentness readers.
2. Before issuing a ticket, the broker publishes `ISSUANCE_RESERVATION_V1`
   with no-replace at the stable `consumer_operation_key`. A target that
   already exists is a collision STOP, including identical bytes.
3. The broker generates ticket ID, operation ID, issue time and deadline. The
   caller cannot choose, backdate, extend or deserialize them.
4. First authenticated redemption durably changes state to `IN_FLIGHT` before
   the child effect.
5. Success, rejection, exception, timeout, cancellation, handle-close failure or
   broker/child crash consumes the invocation budget permanently.
6. Concurrent redemptions serialize at the server record. Exactly one can enter
   `IN_FLIGHT`; every other call receives a stable body-free rejection.
7. Broker restart invalidates all nonterminal live capabilities. Immutable audit
   records may be read but never reconstruct authority.
8. A new request ID, random ticket or process restart for the same stable
   consumer operation key cannot bypass an existing reservation. Retry requires
   the owning consumer's exact durable no-effect reconciliation receipt, a new
   plan revision/key bound to the predecessor and fresh upstream currentness.
   The broker never blindly replays a prior effect.
9. `DUPLICATE` is valid only when a consumer-specific trusted terminal proves
   the same event, same body and same physical identities. Config equality,
   ticket ID equality or a public receipt alone is insufficient.

For burn timing, "entry" means the first redemption frame received over the
already authenticated, exact child channel. The broker atomically records
`IN_FLIGHT` before validating command/config semantics. Wrong command, wrong
config, an exception or any later validation failure therefore burns that
ticket. Traffic from an unauthenticated process/handle cannot identify or burn
another operation's ticket.

## 10. Config publication and child launch

1. Resolve exact install instance, config parent and required upstream receipts
   through the profile's internally fixed trusted producers; public mappings
   are display evidence only. TASK-072 does not create an install/bridge/
   operation directory and accepts no caller-selected root.
2. The owning consumer creates the live private
   `CONSUMER_OPERATION_AUTHORIZATION_V1` from its exact durable plan and
   currentness readers.
3. The broker verifies the frozen producer/version matrix, derives the stable
   `consumer_operation_key` and durably publishes its no-replace issuance
   reservation.
4. The broker durably publishes `ISSUED`, then returns one live action-specific
   ticket/channel to the trusted Product process.
5. Build the closed config projection from broker-supplied fields and strictly
   bound/canonicalize it before hashing.
6. Acquire the TASK-072 operation lease using TASK-068 secure existing/initial
   lock semantics. A create-race loser is freshly classified and fails; it is
   never auto-retried as existing.
7. Publish config with operation-owned live handle, file durability, no-replace,
   directory durability and exact pinned readback.
8. Bind the config hash/identity to the live ticket.
9. Start exactly one child with a fixed argv vector and explicit `--config`.
   Shell invocation is forbidden.
10. Transfer one restricted operation channel handle to that exact child.
11. Hold broker ticket state and the Product operation lease through the
    adapter's pinned config read, redemption, result capture and terminal
    projection.
12. The adapter validates config strict JSON, exact command, config identity,
    process binding and broker challenge, then redeems before effect.
13. Close the channel and burn the ticket on every exit path.

The operation config and terminal evidence are preserved. Correctness never
depends on deleting an old config. A later launch cannot redeem an expired or
consumed ticket even while the immutable config remains present.

## 11. Canonical SKILL D2S integration

The Canonical SKILL remains a proposal/learning adapter and never owns BVP's
canonical Timeline, File Bridge, store or Profile.

TASK-072 applies these fixed rules:

- distribution `config/bvp-learning-connector.json` remains `enabled:false`;
- no mutable fixed runtime config replacement;
- connector status remains read-only and creates no directories;
- every command invoked from the packaged Production route uses its exact
  action-profile ticket and immutable config v2; the standalone generic CLI may
  remain available for non-Production fixture/advisory use, but its result can
  never satisfy an installed, E2E, activation or canonical completion receipt;
- `publish-learning` may run exactly once for one ticket and only stages a
  privacy-validated immutable delivery;
- `PENDING` is a valid intermediate BVP state;
- a second `publish-learning` call for receipt confirmation is forbidden;
- terminal confirmation uses `PRODUCT_BROKER_TERMINAL_QUERY`, which is not a
  Canonical SKILL CLI action and creates no config, child or delivery;
- adapter `canonical_store_written` and `safe_export` are advisory booleans and
  never Product authority;
- BVP canonical admission, hidden Generic correlation and Profile readback are
  verified by their Product owners, not by the SKILL;
- the SKILL does not parse or repair BVP private claim, journal, pending,
  canonical or Profile stores;
- public output uses relative/opaque IDs, hashes and stable reason codes only;
- runtime PASS requires an executed operation receipt, never static presence.

TASK-068 strict parsing and pinned I/O prove only the BVP-side config/event
boundary. Every Canonical SKILL child action must independently use the
D2S-owner strict bounded no-follow reader, retain the opened config identity
through semantic validation/redemption and emit its versioned pinned-read
completion receipt. That reader and receipt require the exact Canonical SKILL
owner amendment; TASK-072 cannot implement or infer them. A BVP-side TASK-068
readback without the matching child receipt leaves the D2S effect
`NOT_CONFIRMED` and cannot satisfy installed/E2E/activation completion.

Before config canonicalization or hashing, the D2S producer must have completed
its own closed privacy projection: bounded strict JSON, exact schema and type
ceilings, controlled reason codes, bounded token grammars, value scanning and
unknown-field rejection. TASK-072 binds the resulting accepted projection hash;
it never hashes/logs a privacy-rejected raw tree and never substitutes for the
SKILL or TASK-058 privacy validator.

## 12. GPU-required integration

Public TASK-066 `ProbeResult`, `ProbeCommand`, `RuntimeModuleEvidence`, module
tokens, hashes and `capability_from_probe_result` results are audit data only.
`GPU_REQUIRED_LAUNCH` requires a private trusted probe capability from the
Product process/broker boundary, bound to:

- actual probe run/process evidence;
- runtime attestation and InstallLayout;
- exact DesktopCompute profile revision and workload;
- helper/build/backend identities;
- selected adapter identity and resource constraints.

The public fixture path remains effect zero: helper-unsealed or public-only
evidence yields `Popen=0`, save delta zero and no GPU launch. The ticket is
burned on launch entry and cannot be reused after an exception.

## 13. Human-gated integration

TASK-072 validates only the opaque identity/currentness of a TASK-071 receipt
through the trusted internal port. It cannot issue, copy, deserialize, renew or
replace that receipt. The Human action, challenge, user/session event and
trusted time come from TASK-071.

The following never count as Human authority:

- a confirmation string or boolean;
- a public evidence dataclass or self-hash;
- caller-selected ID, time, action or expiry;
- a module sentinel/private Python token;
- an OP_TICKET_V1 without the required TASK-071 live/durable binding.

## 14. Clock, expiry and restart

Production time comes from the broker's fixed native clock. A ticket binds a
boot/session coordinate plus monotonic issue/deadline values and bounded UTC for
audit. UTC, timezone, caller `now`, filesystem mtime or a test clock cannot
extend validity.

- wall-clock rollback: no extension;
- large forward jump: fail closed if policy cannot prove currentness;
- suspend/resume: monotonic deadline still applies;
- timezone change: audit-only, no authority change;
- broker/Product restart: every nonterminal ticket is burned;
- expiry-boundary concurrent redemption: server serialization decides once;
- phase clock/backend swap: effect zero and stable rejection.

## 15. Strict parsing, privacy and logging

BVP-side authority JSON uses TASK-068 strict bounded UTF-8 parsing before
semantic validation or hashing. Canonical SKILL child-side authority JSON uses
the separately owned D2S pinned strict-reader port described in section 11.
Both reject duplicate keys at every depth, NaN and infinities, BOM, trailing
data, invalid UTF-8/control characters, non-built-in JSON values and
byte/depth/node/member/item/string limit violations.

Logs, exceptions, public receipts, stdout and UI status may contain only:

- stable error/status code;
- opaque operation/request ID;
- action-profile token;
- non-sensitive digest/count booleans;
- `authority_created=false` for public projections.

They must not expose absolute paths, argv, config bodies, delivery bodies,
receipt bodies, SIDs, account names, emails, command output, environment, OS
error text, tokens, secrets or offending values.

## 16. UI and operation flow

TASK-072 has no standalone end-user settings page. Product surfaces may display
read-only Japanese operation status:

- `準備中`
- `実行待ち`
- `実行中`
- `完了`
- `安全のため停止`
- `期限切れのため再準備が必要`

No UI displays or allows editing of a ticket, nonce, timestamp, config path,
backend, clock, build digest or process identity. Human-gated actions show the
TASK-071 confirmation UI; TASK-072 itself adds no second consent prompt.

On failure the UI offers a fresh Product re-prepare action only after the
owning consumer has reconciled prior durable state. It never offers blind
`再実行` for `IN_FLIGHT`, `BURNED_UNKNOWN` or completion-unknown states.

## 17. Fault and recovery table

| Seam | Required result | Effect/recovery rule |
|---|---|---|
| Before ticket issue | `REJECTED` | Config/child/effect delta zero |
| Ticket issued, before config | Ticket burned on close/expiry/restart | No authority reconstructed from audit record |
| During config write/fsync | Fail or completion-unknown | No child start; preserve exact owned/foreign artifacts according to TASK-068 |
| Config target race | `COLLISION_STOP` | Winner preserved; overwrite/delete zero |
| After config, before child | Ticket eventually burned | Immutable config may remain harmless |
| Child start failure | `BURNED` | No second start under same ticket |
| Child starts, before redeem | Burn on child exit/channel close | Effect zero; no retry under same ticket |
| Concurrent/double redeem | One `IN_FLIGHT`; others rejected | Invocation exact 0/1 |
| During consumer effect | `IN_FLIGHT` already durable/in-memory | Exception burns; owning Task reconciles exact terminal state |
| Effect committed, receipt lost | `BURNED_UNKNOWN` until trusted readback | Status query only; effect command is not replayed |
| Broker crash/restart | All nonterminal tickets invalid | Fresh plan/currentness required |
| Result capture/readback failure | Completion unknown | Preserve evidence; do not claim PASS or delete |
| Cleanup failure | Non-authoritative warning/code | Old config/evidence retention cannot re-enable ticket |

## 18. Negative matrix

Every test separately asserts requested consumer effect, config delta, child
process delta, distribution-config delta and unrelated-file delta.

### T72-AUTH

- direct construction of public request/config/receipt objects;
- module-private token/sentinel access;
- copy, `dataclasses.replace`, subclass, duck type, pickle or deserialization;
- recomputed valid hash with modified authority fields;
- public factory or same fields without broker process;
- fake broker/backend, monkeypatched attestation or test clock in Production;
- action profile added through argv/config/Mapping;
- wrong/cross action, command, instance, build, backend or session;
- copied handle value without the OS handle;
- handle inherited by grandchild or different child.

Expected: capability/effect/config mutation zero unless the exact trusted broker
operation exists.

### T72-ISSUE

- public request or receipt hash without the private consumer authorization;
- wrong/missing producer version, durable plan, predecessor or currentness;
- same semantic consumer effect with a new request ID, random ticket or process;
- reservation target collision, including identical bytes and different inode;
- crash before/after authorization, reservation, issue, config, `IN_FLIGHT` and
  terminal publication;
- restart or cross-build issue against a prior reservation;
- prior `IN_FLIGHT`, `BURNED_UNKNOWN`, missing/ambiguous terminal or receipt-only
  evidence followed by a new issue attempt;
- forged, public, stale or wrong-body no-effect reconciliation receipt.

Expected: ticket/config/child/consumer effect zero for every rejected issue;
existing reservation/evidence and unrelated files remain byte/identity exact.

### T72-IPC

- oversized, truncated, trailing, reordered, duplicated or replayed frames;
- unknown message kind/field, wrong protocol version, sequence or transcript;
- copied nonce/challenge without the inherited channel object;
- wrong child image/build/token/SID/session/LUID/parent/handle;
- handle inheritance by a grandchild or unrelated same-user process;
- post-launch image/config/handle swap;
- unauthenticated traffic attempting to identify or burn another ticket.

Expected: unauthenticated traffic has no lookup/burn oracle and effect zero;
an authenticated first redemption either enters `IN_FLIGHT` exactly once or
burns, with body-free output and no unrelated mutation.

### T72-STATE

- double and concurrent redemption;
- caller-selected ticket ID/time/expiry;
- backdated/future time, clock rollback, suspend/resume and restart;
- exception, cancellation or timeout then reuse;
- broker/child crash at every state transition;
- stale request and stale upstream receipt;
- same public receipt with different private state event.

Expected: ticket 1 -> exact command at most 1; success or exception burns;
restart never revives a ticket.

### T72-CONFIG

- strict JSON duplicate keys equal/different at top and nested levels;
- NaN/Infinity, BOM, trailing data, invalid UTF-8/control, deep/wide/huge input;
- config target absent then appears identical/different;
- same bytes/different inode;
- ancestor/reparse/hardlink/DACL drift;
- temp/target prepublish and postpublish swaps;
- file or directory fsync and post-readback failures;
- wrong config profile, command, receipt, expiry or self-hash;
- caller-selected absolute/relative root, environment/CWD root and fixed
  ProgramData fallback;
- wrong/stale `CONFIG_PARENT_BINDING_V1` producer or operation parent;
- fixed distribution config mutation attempt.

Expected: child/effect zero; foreign/ambiguous artifacts preserved;
distribution config byte delta zero.

### T72-D2S

- direct CLI replay/copy with operation config;
- wrong/cross command or operation A/B startup race;
- precheck-open/config read-post swap;
- receipt swap and receipt-only canonical claim;
- publish accepted/pending/processing then second publish;
- concurrent second publish and cleanup-before/after retry;
- missing/wrong Generic correlation or Profile readback;
- broker terminal query that starts an adapter/config or creates a delivery;
- extra/unknown receipt fields;
- BVP TASK-068 readback without the D2S-owner pinned child-read receipt;
- D2S child stat-open/read-post swap or same bytes/different inode;
- path/email/account/token/transcript payload already rejected by privacy gate.

Expected: one ticket creates at most one staging delivery; the Product broker
terminal query creates zero configs/children/deliveries; BVP canonical/Profile
authority remains zero without its own
trusted receipts; sensitive raw bytes appear in no config/log/receipt/temp.

### T72-GPU

- direct public ProbeResult/capability factory/module token;
- copied/pickled probe or same fields without actual process;
- wrong run/helper/backend/layout/profile/workload;
- helper-unsealed public receipt;
- double/concurrent launch and exception reuse.

Expected: `Popen=0`, save delta zero and no GPU-required effect unless the exact
private trusted probe capability and ticket are both live.

### T72-HUMAN

- missing TASK-071 receipt for a Human-gated profile;
- confirmation boolean/string/public dataclass;
- wrong action/user/session/process/challenge;
- copied, expired, consumed or forged Human receipt;
- non-Human migration/profile ticket reused for activation.

Expected: Human-gated consumer mutation zero.

## 19. Acceptance criteria

Design acceptance requires:

1. Owner, responsibility, exact Allowed Files and prohibited paths are fixed.
2. The artifact/phase dependency graph contains no effect-completion cycle;
   early ABI/fixture freeze is never represented as terminal effect completion.
3. A ticket requires the exact private consumer authorization and frozen
   producer/version matrix; public request/receipt equality cannot mint it.
4. Durable no-replace reservation by stable semantic consumer operation key
   prevents new request IDs, restarts or random tickets from reissuing an
   unresolved effect.
5. Public objects, hashes and serialized configs are evidence only.
6. Production capability exists only as live broker state plus an exact OS
   channel handle bound to process/user/session/build/currentness.
7. Invocation budget is exactly one and burns at authenticated entry on success
   or exception; unauthenticated traffic cannot identify or burn a ticket.
8. Fixed SKILL config stays byte-identical disabled; config v2 is immutable,
   operation-specific and explicitly selected.
9. Config parent/root comes only from its fixed private resolver, while config
   publication is TASK-068-bound, no-replace, durable and exact readback.
10. Broker restart cannot reactivate any nonterminal ticket.
11. D2S publish is exact once; receipt confirmation never republishes delivery,
    and installed PASS requires the D2S-owner pinned child-read receipt.
12. Public GPU probe/capability cannot authorize launch.
13. TASK-071 remains the only Human authorization producer.
14. Stable public errors/logs are body-free and path-free.
15. Fixture PASS is never promoted to Production/native/E2E PASS.
16. IPC framing, transcript, image/token/handle binding and size ceilings are
    closed and testable at both launch and redemption boundaries.
17. Focused, negative, fault, packaging and native Windows tests defined here
    pass with unrelated overwrite/delete zero.
18. Independent Critic has `Critical=0 / High=0` and Judge returns `PASS`.

## 20. Verification plan

### Static/focused

- strict schemas and package mirrors exact hash;
- closed action registry and exhaustive profile mapping;
- compileall for changed source/tests;
- focused broker/config/fixture tests;
- TASK-068 binding tests with an exact fixture adapter;
- relevant TASK-063/061/065/066/D2S contract-only regressions;
- diff/scope and secret scan.

### Windows native

- packaged broker/helper exact image and build readback;
- restricted handle inheritance and grandchild denial;
- same-user unrelated process cannot redeem;
- SID/session/logon-LUID and child-process mismatch rejection;
- monotonic expiry across suspend, wall-clock/timezone changes and restart;
- NTFS reparse/hardlink/ancestor/target/temp race matrix;
- concurrent two-process redemption exact 1;
- crash injection at every state/config/launch/result seam;
- directory durability failure is FAIL or completion-unknown, never PASS;
- public UI/log/stdout path/body/secret leakage zero;
- installed D2S command exact once with distribution config unchanged;
- real GPU launch remains `NOT_EXECUTED` unless its separate native gate exists.

### Package/install

- clean packaged startup without Codex, ChatGPT, OpenAI key or internet;
- broker binary/helper/config schema exact installed hashes;
- repair/upgrade retain compatible audit evidence but invalidate live tickets;
- uninstall and physical cleanup are not TASK-072 effects;
- multiple installs cannot cross-redeem tickets or configs;
- portable/fixed-ProgramData fallback remains effect zero unless separately
  designed by TASK-063.

## 21. Independent design freeze receipt

The independent Montage Critic/Judge reviewed the complete technical payload at
SHA-256 `5bc1d4721b510330dee334e3e3c3d827ccf5a5d273f3e5bf88422610ac0e0bd7`
(1004 lines before this administrative receipt finalization) and returned
`Critical=0 / High=0 / Judge=PASS`. The receipt identity is
`TASK072-DESIGN-COMPLETE-20260901-001`.

```text
task: TASK-072
design_identity: TASK072-PTD-OPERATION-BROKER-V1
base: origin/main@35cdf1ad475633dcf035e0616e979b5a8fde0c88
allowed_files: docs/ai-team/tasks/TASK-072/complete-design-packet.md
review_target_sha256: 5bc1d4721b510330dee334e3e3c3d827ccf5a5d273f3e5bf88422610ac0e0bd7
critic: C0/H0
judge: PASS
design_frozen: true
source_effect: 0
schema_effect: 0
test_effect: 0
native_effect: 0
release_deploy_production_effect: 0
authority_created: false
next: source implementation in a fresh compliant worktree after dependency and overlap gates
```

This freeze creates no implementation, native, Human, Release, Deploy or
Production authority. The final file hash and exact commit are recorded by the
design PR; any later technical content change requires a new Critic/Judge
review and a new versioned receipt.
