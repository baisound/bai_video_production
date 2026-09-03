# TASK-072-A OP_TICKET_CORE_V1 Detailed Design

Status: `DESIGN_CANDIDATE / DEV-4 / SOURCE_EFFECT_0 / TASK068_DEPENDENCY_NC`

Design identity: `TASK072-A-OP-TICKET-CORE-V1-R0`

Binding:

- repository: `baisound/bai_video_production`;
- base: `origin/main@4d233c8c77c7328f5b221642040faf06c0a6a15c`;
- parent design: `TASK072-PTD-OPERATION-BROKER-V1` at remote design
  commit `52203bc9962340016f4b7ac494ea02d25202484d`;
- owner: `Platform Trust & Delivery / TASK-072`;
- allocated unit: `TASK-072-A BROKER_CORE_AND_FIXTURE_V1`;
- current authority ceiling: task-local design only;
- source, schema, test, native, package, Release, Deploy and Production
  effects: `0`.

## 1. Decision

TASK-072-A defines the Product-private one-shot operation-ticket core required
before TASK-063 may issue a real preterminal installation plan. Public Python
objects and JSON documents remain audit data. Authority exists only as the
conjunction of:

1. a live consumer authorization received over the trusted Product-to-broker
   channel;
2. an exact broker-side server record;
3. a durable no-replace issuance reservation and event chain;
4. one authenticated inherited OS channel handle bound to the exact process,
   user, session, build and broker boot;
5. an invocation budget of one that is consumed at authenticated entry.

A module-global sentinel, constructor, class identity, object hash, public
factory, Mapping, copied handle integer or serialized receipt is never part of
the authority proof.

TASK-072-A does not implement TASK-072-B installed-instance profile binding,
TASK-072-C Human/action profiles, D2S execution, GPU launch, installer pair
publication, native installation, Release, Deploy or Production Activation.

## 2. Exact Allowed Files

This design unit may change only:

- `docs/ai-team/tasks/TASK-072/op-ticket-core-v1-detailed-design.md`.

A later separately allocated TASK-072-A implementation may change only:

- `src/ai_video_production/product_operation_broker.py`;
- `src/ai_video_production/product_operation_config.py`;
- `schemas/product-operation-ticket.schema.json`;
- `schemas/product-operation-config.schema.json`;
- `schemas/product-operation-receipt.schema.json`;
- `src/ai_video_production/schema_resources/product-operation-ticket.schema.json`;
- `src/ai_video_production/schema_resources/product-operation-config.schema.json`;
- `src/ai_video_production/schema_resources/product-operation-receipt.schema.json`;
- `tests/test_task072_product_operation_broker.py`;
- `tests/test_task072_product_operation_config.py`;
- `tests/fixtures/task072/**`;
- `docs/ai-team/tasks/TASK-072/**`.

The packaged Windows entry and Windows/package test files allowed by the
parent design are deliberately excluded from this first source unit. Adding
them requires a later exact TASK-072-A native/package allocation.

## 3. Prohibited Files and Effects

- TASK-036, TASK-058, TASK-060, TASK-061, TASK-063, TASK-065, TASK-066,
  TASK-067, TASK-068, TASK-070 and TASK-071 owner files;
- Canonical SKILL source or configuration;
- `src/ai_video_production/atomic.py`;
- installer scripts, shared current-state/task-index/roadmap and `CHANGELOG.md`;
- real child launch, real installer operation, adapter command, Provider,
  model download, private-media read, external-account mutation, Release,
  Deploy or Production Activation;
- cleanup, rollback or deletion of an unknown, foreign or published artifact.

The fixed distribution connector configuration remains byte-identical and
disabled.

## 4. Frozen Modules and Symbols

### 4.1 `product_operation_broker.py`

Public audit-only symbols:

- `ProductOperationRequestV1`;
- `ProductOperationAuthorizationResolutionV1`;
- `ProductOperationAuditReceiptV1`;
- `ProductOperationTerminalStatusV1`;
- `create_product_operation_request`;
- `read_product_operation_status`.

Every public value is immutable data, has `authority_created=False`, is safe
to copy/serialize, and cannot be passed to an effect-bearing broker method.
No public function returns a live ticket, channel or consumer authorization.

Private Product-composition symbols:

- `_TrustedProductOperationBrokerV1`;
- `_ConsumerOperationAuthorizationV1`;
- `_BrokerTicketRecordV1`;
- `_LiveOperationTicketV1`;
- `_BrokerChannelBindingV1`;
- `_TicketCapabilityState`;
- `_DurableTicketState`;
- `_issue_operation_ticket_v1`;
- `_redeem_operation_ticket_v1`;
- `_record_ticket_terminal_v1`;
- `_reconcile_no_effect_predecessor_v1`.

Private names are not themselves a security control. Each effect-bearing call
must find the object identity in broker-owned live state and prove the exact
native channel/process binding. Direct construction or introspection therefore
finds no live registered record and fails before reservation, event, config or
consumer effect.

`_BrokerTicketRecordV1` is the sole retained semantic authority record. Before
the live ticket leaves `READY`, it holds one privately snapshotted tuple of:

- random `operation_id` and `ticket_id`;
- `consumer_operation_key`, authorization fingerprint and exact consumer
  Task/action/profile/version;
- exact command/subcommand and fixed argv digest;
- invocation budget and current live/durable state revision;
- durable plan identity, revision, predecessor and currentness receipt;
- install instance or preterminal selected-install plan, plus TASK-070
  terminal identity when applicable;
- issuance-reservation body fingerprint, TASK-068 receipt and physical
  identity;
- expected config canonical hash, physical identity and config-parent binding;
- source, Profile, record, delivery and expected-result digests selected by
  the frozen action profile;
- every required upstream receipt type/version/hash/physical-identity tuple;
- Product, broker, adapter/helper and backend implementation/build identities;
- Windows user SID, session ID, logon LUID, parent process identity and exact
  child process identity once bound;
- broker boot/session identity, monotonic issue/deadline and bounded UTC audit
  coordinate;
- optional TASK-071 Human receipt identity for later Human-gated profiles;
- predecessor and next durable event identity/coordinate;
- registered native channel-object identity and live registry object identity.

The record does not reread semantic fields from a public request, config or
receipt. State transitions replace only the state revision, next event,
config/child binding and terminal result slots under the broker record lock;
all immutable authorization fields must remain byte-for-byte equal to the
initial private snapshot.

### 4.2 `product_operation_config.py`

Public audit-only symbols:

- `OperationConfigAuditV2`;
- `validate_operation_config_audit`.

Private Product-composition symbols:

- `_ConfigParentBindingV1`;
- `_OperationConfigSnapshotV2`;
- `_build_operation_config_v2`;
- `_publish_operation_config_v2`;
- `_readback_operation_config_v2`.

The builder accepts only an internal immutable snapshot of broker-authored
fields. It accepts no arbitrary Mapping, caller path, backend, clock, hook or
failure injector in Production composition.

### 4.3 Export boundary

`__all__` may expose only the public audit symbols above. It must not expose a
broker constructor, authorization factory, live ticket type, native handle,
registry, state transition function or test backend.

## 5. Frozen Schema Identities

The repository schema filename plus closed `message_type` and
`schema_version` form the schema identity. The schemas use JSON Schema draft
2020-12, closed objects and no caller-extensible extension map.

`product-operation-ticket.schema.json` contains these closed documents:

- `OPERATION_REQUEST_V1`:
  `message_type=BvpProductOperationRequest`, `schema_version=1.0.0`;
- `ISSUANCE_RESERVATION_V1`:
  `message_type=BvpProductOperationIssuanceReservation`,
  `schema_version=1.0.0`;
- `OP_TICKET_EVENT_V1`:
  `message_type=BvpProductOperationTicketEvent`, `schema_version=1.0.0`.

`product-operation-config.schema.json` contains:

- `OPERATION_CONFIG_V2`:
  `message_type=BvpOperationSpecificConfig`, `schema_version=2.0.0`.
  For the admitted Generic D2S subset, `command` is the logical,
  non-executable registry identity `SKILL_D2S_ADAPTER_V1`; each action profile
  maps to exactly one reviewed D2S subcommand. The executable/image coordinate
  and argv remain private broker bindings committed by digest in later units.

The admitted A1 logical command registry is closed to these exact triples:

| Action profile | Logical command | Exact subcommand |
|---|---|---|
| `D2S_VALIDATE` | `SKILL_D2S_ADAPTER_V1` | `validate` |
| `D2S_EMIT_PROPOSAL` | `SKILL_D2S_ADAPTER_V1` | `emit-proposal` |
| `D2S_FEEDBACK_TO_LEARNING` | `SKILL_D2S_ADAPTER_V1` | `feedback-to-learning` |
| `D2S_ROUND_TRIP` | `SKILL_D2S_ADAPTER_V1` | `round-trip` |
| `D2S_CONVERT_FRAME` | `SKILL_D2S_ADAPTER_V1` | `convert-frame` |
| `D2S_VALIDATE_TASK056_SIDECAR` | `SKILL_D2S_ADAPTER_V1` | `validate-task056-sidecar` |
| `D2S_CONNECTOR_STATUS` | `SKILL_D2S_ADAPTER_V1` | `connector-status` |
| `D2S_PUBLISH_LEARNING` | `SKILL_D2S_ADAPTER_V1` | `publish-learning` |
| `D2S_LOAD_PROFILE` | `SKILL_D2S_ADAPTER_V1` | `load-profile` |

Every other action profile has no A1 config or command-bearing event binding
and must reject those documents with `TASK072_CONFIG_REJECTED` or schema
rejection. Public request and reservation audit shapes may still name all 16
closed action profiles without creating authority. Adding or changing a triple
requires a reviewed design revision and fixture/schema/runtime parity update.

`product-operation-receipt.schema.json` contains only public audit documents:

- `PUBLIC_AUDIT_RECEIPT_V1`:
  `message_type=BvpProductOperationAuditReceipt`,
  `schema_version=1.0.0`;
- `BROKER_TERMINAL_STATUS_V1`:
  `message_type=BvpProductOperationTerminalStatus`,
  `schema_version=1.0.0`;
- `AUTHORIZATION_RESOLUTION_V1`:
  `message_type=BvpProductOperationAuthorizationResolution`,
  `schema_version=1.0.0`.

`BROKER_REDEMPTION_RECEIPT_V1` is a private retained broker record and has no
public JSON schema or public message type. The root and packaged
schema-resource copies must be byte-identical. A schema name or message type
change requires a new versioned design and fixture set.

## 6. Identifier and Input Policy

- `operation_id`: broker-generated lowercase 32-hex value from at least
  128 bits of cryptographic randomness;
- `ticket_id`: independent broker-generated lowercase 32-hex value from at
  least 128 bits of cryptographic randomness;
- `request_id`: Product UI display correlation only; never an authority key;
- `consumer_operation_key`: lowercase `sha256:<64 hex>` over the complete
  intended-effect fingerprint and exact plan revision;
- all content commitments: lowercase `sha256:<64 hex>`;
- `invocation_budget`: exact integer `1`, never a caller value;
- action, command and subcommand: members of the frozen registry only;
- argv: fixed tuple selected by the action profile; shell strings are
  forbidden;
- expiry: broker-authored monotonic issue/deadline plus bounded UTC audit;
- public opaque tokens: ASCII, 1..192 code points, with no path separators,
  drive/UNC/URI syntax, control characters or whitespace.
- event semantic coordinates: exact
  `task072/operations/<32-lower-hex-operation-id>/events/<8-digit-revision>.v1.json`;
  `first_event_coordinate` requires revision `00000001`. These relative names
  are audit coordinates only and never filesystem authority.

Every authority JSON read is strict UTF-8 and rejects duplicate keys at every
depth, BOM, trailing data, NaN/Infinity, invalid control characters, unknown
fields and non-built-in JSON values before canonicalization or hashing.

TASK-072-A ceilings:

- one document/frame: 64 KiB raw;
- one IPC transcript: 256 KiB raw;
- maximum nesting depth: 8;
- maximum object members: 64;
- maximum array items: 64;
- maximum total nodes: 512;
- maximum ordinary string: 4096 UTF-8 bytes and 4096 code points.

Limit or parse failure is a stable body-free rejection and retains no parsed
document, raw bytes, path or OS exception through cause/context.

## 7. Consumer Authorization Snapshot

`_ConsumerOperationAuthorizationV1` is delivered only over the authenticated
Product-to-broker channel. Before reservation it binds and revalidates:

- exact consumer Task, action profile and producer versions;
- stable consumer operation key;
- durable plan identity, revision, predecessor and currentness receipt;
- install instance or TASK-063 preterminal plan identity;
- action-specific producer receipt type/version/hash/physical identity set;
- expected config-parent binding;
- Product issuer process/build/backend;
- trusted user SID, session, logon LUID and broker boot;
- trusted issue/deadline coordinates and budget one;
- authorization fingerprint verified by an internally fixed consumer
  verifier.

The broker snapshots every field before calling any verifier. A verifier
receives a separate canonical copy, cannot mutate retained state, and cannot
be selected by argv/config/Mapping. Any exception becomes a stable rejection
before reservation.

## 8. Durable Reservation and Coordinates

Before generating a usable ticket, the broker publishes exactly one immutable
reservation through a consumer-admitted TASK-068 plan at:

```text
task072/reservations/<consumer-operation-key-hex>.v1.json
```

After reservation, events use exact coordinates supplied by the retained
broker record:

```text
task072/operations/<operation-id>/events/<8-digit-revision>.v1.json
task072/operations/<operation-id>/config.v2.json
task072/operations/<operation-id>/terminal.v1.json
```

The consumer supplies the trusted operation parent capability; the strings
above are relative semantic coordinates, never public filesystem authority.
No directory scan, highest/latest selection, mtime, filename ordering,
content equality or mutable pointer selects an operation.

A reservation collision is STOP+preserve even when bytes are identical. It
never returns a new ticket or `DUPLICATE`. Retry requires a consumer-owned
durable exact no-effect reconciliation receipt and a new plan revision/key
that binds the prior reservation as predecessor.

### 8.1 `ISSUANCE_RESERVATION_V1` exact body

The strict canonical reservation document contains only:

- message type/version;
- `consumer_operation_key` and complete authorization fingerprint;
- random operation and ticket identifiers;
- exact consumer Task/action/profile/version;
- durable plan revision, predecessor and currentness receipt commitments;
- config-parent binding commitment;
- Product/broker build, backend, boot and session commitments;
- monotonic issue/deadline and bounded UTC audit projection;
- invocation budget one;
- expected first-event relative coordinate;
- `authority_created=false` and document self-hash.

The TASK-068 immutable publication receipt is stored separately in the private
broker record and binds the reservation body/count, exact physical identity,
predecessor and root/ancestor/target security commitment. Neither body nor
TASK-068 public receipt alone recreates the broker record.

### 8.2 `OP_TICKET_EVENT_V1` exact body

Every event document contains only:

- message type/version, operation/ticket IDs and consumer operation key;
- exact event revision and one durable-state enum value;
- action/profile, command and fixed argv digest;
- predecessor event coordinate, body digest and TASK-068 physical-identity
  commitment, or exact null values for the first event;
- issuance-reservation fingerprint and physical-identity commitment;
- broker build/backend/boot/session commitments;
- config canonical hash/physical-identity commitment, null until bound;
- child process/token/build/channel commitment, null until bound;
- consumer result digest and terminal receipt commitments, null before a
  terminal state;
- monotonic event coordinate, bounded UTC audit projection;
- next expected event coordinate, `authority_created=false` and self-hash.

The private broker record retains the corresponding TASK-068 receipt for every
event. State, predecessor, reservation, config and child commitments are
validated against that retained record before the next event is published.
An event chain is audit/recovery evidence only and cannot recreate a channel or
live ticket after restart.

## 9. State Machines

### 9.1 Broker lifecycle and durable state

```text
REQUESTED          public audit only; no durable authority event
  -> AUTHORIZED    live pre-reservation broker state; no authority event
  -> [reservation published and pinned read back]
  -> RESERVED      first durable event; semantic-effect fence bound
  -> ISSUED        durable event plus server record and channel
  -> CONFIG_READY  immutable config exact readback
  -> CHILD_BOUND   exact process/token/build/channel
  -> IN_FLIGHT     budget consumed before semantic validation/effect
       -> COMMITTED
       -> REJECTED
       -> BURNED_UNKNOWN

ISSUED | CONFIG_READY | CHILD_BOUND
  -> BURNED
```

`REQUESTED` and `AUTHORIZED` never publish `OP_TICKET_EVENT_V1`; they cannot
carry or recreate durable authority. After the immutable reservation is
published and pinned read back, the broker constructs the first event at the
coordinate committed by the reservation. That `RESERVED` event binds the now
known reservation fingerprint and physical identity and uses the exact null
predecessor values defined by section 8.2. Every transition beginning at
`RESERVED` publishes an exact immutable predecessor-bound event. If first-event
publication fails after reservation, the reservation is preserved, no usable
ticket/channel/config/child is created and the operation is
`BURNED_UNKNOWN`; only the consumer-owned no-effect reconciliation route in
section 12 can authorize a new plan revision/key. A failed later event before
consumer effect is rejection or completion-unknown, never PASS. No nonterminal
state survives broker restart as authority.

### 9.2 Live capability state

```text
READY -> IN_FLIGHT -> BURNED
```

`READY -> IN_FLIGHT` occurs atomically at the first redemption frame received
over the already authenticated exact child channel. It precedes command,
config and result semantic validation. Success, mismatch, exception, timeout,
cancellation, channel close, child exit, broker stop, restart or finalization
failure all end in `BURNED`. There is no transition back to `READY`.

Concurrent calls serialize on the broker record. Exactly one call can enter
`IN_FLIGHT`; all later calls receive a body-free consumed result without
learning another ticket's existence.

## 10. Config V2

The closed config binds:

- contract profile and exact command/subcommand;
- operation/ticket opaque identifiers;
- install instance and upstream receipt commitments;
- expected input, record, Profile, delivery and result digests required by
  that profile;
- Product, adapter and config-projection build digests;
- monotonic/UTC expiry projection;
- `invocation_budget=1`;
- `distribution_config_mutated=false`;
- `authority_created=false`;
- document self-hash.

It contains no absolute or relative filesystem root, executable path, broker
endpoint, native handle value, secret, raw payload, backend selector, clock,
hook or failure mode.

The broker acquires a TASK-068 secure operation lease, publishes the config
with immutable no-replace semantics, proves file and directory durability and
performs exact pinned readback. Existing target or completion ambiguity does
not start a child. TASK-068 current accepted completion is therefore a hard
source-effect dependency.

The same lease and config-parent capability remain live continuously from
before config publication through config pinned read, child binding, first
redemption, consumer result capture, terminal publication and exact terminal
readback. The broker revalidates the config-parent root/ancestor/security
commitment and lease identity immediately before publication, child launch,
`IN_FLIGHT` and terminal publication, and once more after terminal readback.
No publication follows that final currentness check. Early release, namespace
drift, DACL drift or any close/lifetime ambiguity yields a body-free
completion-unknown result and never consumer PASS.

## 11. IPC Protocol

Each frame is a 4-byte little-endian unsigned length followed by one canonical
strict UTF-8 JSON message. The closed message-kind sequence is:

```text
BROKER_CHALLENGE_V1
CHILD_REDEEM_V1
BROKER_REDEEMED_V1
CHILD_RESULT_V1
BROKER_CLOSE_V1
```

Every message binds protocol magic/version, kind, broker nonce, operation and
ticket opaque IDs, exact sequence, predecessor transcript hash and current
transcript hash. The challenge is bound to the server record and inherited
channel object, not only to nonce text.

The common frame is a closed object containing exactly the common fields above
plus one message-specific closed object:

- `BROKER_CHALLENGE_V1`: fresh challenge nonce, broker boot/session/build
  commitments and expected config commitment;
- `CHILD_REDEEM_V1`: challenge-response digest, action/command commitment,
  config canonical hash/physical-identity commitment and child
  image/token/channel commitment;
- `BROKER_REDEEMED_V1`: accepted state-event digest and exact
  `IN_FLIGHT` revision;
- `CHILD_RESULT_V1`: closed result-state enum, result digest and exact
  downstream receipt type/version/hash commitments;
- `BROKER_CLOSE_V1`: terminal state, terminal event/receipt commitments and
  final transcript hash.

IPC messages may carry only bounded opaque identifiers, enums, booleans,
integers, non-secret challenge data and hashes/currentness coordinates. Raw
payloads, source/config/result bodies, filesystem paths, argv strings, command
output, secrets, tokens, SIDs/account data, PID/native handle values and OS
errors are forbidden in every frame. Unknown or extra common/message-specific
fields reject before state lookup or burn.

The broker revalidates child image/build, PID plus creation identity, parent
relationship, token SID/session/logon LUID and channel-handle identity before
challenge and immediately before `IN_FLIGHT`. The parent revalidates child and
pinned config identity before accepting terminal output. Unauthenticated
traffic is closed without ticket lookup or burn information.

The supported v1 boundary does not claim resistance to an arbitrary same-user
process that has `PROCESS_DUP_HANDLE`, VM read/write, debugger, code-injection
or equivalent compromise of the trusted Product, broker or child. It also does
not cover administrator compromise or replacement of a trusted packaged image.
Those cases are `NOT_SUPPORTED_V1` and cannot be counted as native PASS. The v1
claim is limited to public callers and separate same-user processes that do not
possess the inherited channel and have not compromised a trusted process.

## 12. Terminal and Recovery

`BROKER_REDEMPTION_RECEIPT_V1` binds the exact ticket/event, action/command,
argv digest, config bytes/hash/physical identity, child process/token/build,
redemption monotonic coordinate, result digest, upstream/downstream receipt
identities, predecessor event and self-hash.

That is a private terminal retained by the broker and owning consumer. It may
contain native identity material needed for final currentness verification but
is never serialized through a public API.

`ProductOperationAuditReceiptV1` is a separate closed public projection. It
contains only message/schema version, action/status enums, opaque commitment
hashes, event revision, bounded UTC audit time, count/boolean fields,
`authority_created=false` and a projection self-hash. Process, token, SID,
session/LUID, config identity, native handle, paths, argv and receipt bodies are
represented only by one-way opaque commitments or omitted. A public projection
cannot be passed back to reconciliation or terminal APIs.

The public projection uses
`message_type=BvpProductOperationAuditReceipt`; it never uses the private
redemption-record identity. Its state relation is exact: `COMMITTED` requires
`stable_code=null` and `consumer_effect_observed=true`; `REJECTED` and
`BURNED_UNKNOWN` require a closed stable code and
`consumer_effect_observed=false`. Terminal-status and authorization-resolution
documents encode the same exact state/code/boolean correlations in both
runtime validation and JSON Schema. UTC audit strings use exactly
`YYYY-MM-DDTHH:MM:SSZ` plus calendar-valid date-time validation.
The public audit receipt names its two event coordinates exactly
`event_revision` (integer `1..2147483647`) and `event_utc` (the bounded UTC
string above); both are included in its canonical self-hash body.

Terminal states are:

- `COMMITTED`: exact consumer result and terminal readback are proven;
- `REJECTED`: the authenticated ticket burned before consumer effect, with a
  consumer-specific exact no-effect proof where required;
- `BURNED_UNKNOWN`: the effect or terminal durability/currentness cannot be
  proven.

Only the owning consumer's exact durable readback may reconcile
`BURNED_UNKNOWN`; the broker never replays the command. A public receipt or
receipt hash cannot reconcile, retry or recreate a live ticket.

`DUPLICATE` is outside TASK-072-A ticket issuance. A later consumer may report
it only for the same committed event, body and physical identities.

## 13. Stable Public Failures

Public failures contain only one stable code and booleans required for
completion classification. The initial closed set is:

- `TASK072_AUTHORIZATION_REJECTED`;
- `TASK072_AUTHORIZATION_NC`;
- `TASK072_RESERVATION_COLLISION`;
- `TASK072_RESERVATION_UNKNOWN`;
- `TASK072_TICKET_CONSUMED`;
- `TASK072_TICKET_EXPIRED`;
- `TASK072_SESSION_MISMATCH`;
- `TASK072_CHANNEL_REJECTED`;
- `TASK072_CONFIG_REJECTED`;
- `TASK072_COMPLETION_UNKNOWN`.

No error, log, stdout, schema report or receipt contains an absolute path,
document/config body, argv, SID/account/email, PID/native handle, OS error,
secret, nonce or offending value.

## 14. Focused and Negative Acceptance

### T72-AUTH

- direct public object, Mapping, module sentinel and valid-hash reconstruction;
- copy/deepcopy/replace/subclass/duck type/pickle/deserialization;
- direct private-class construction without registered broker record;
- fake backend, verifier, clock or action profile in Production;
- wrong action, command, instance, revision, plan, build, backend or session;
- copied handle integer, wrong child and inherited grandchild handle.

Expected: reservation/ticket/config/child/consumer effect `0`.

### T72-ISSUE

- missing/wrong producer version/currentness/predecessor;
- same semantic effect with new request ID/ticket/process;
- reservation identical/different target collision and same bytes/different
  inode;
- crash before/after authorization, reservation and ISSUED event;
- restart/cross-build against prior reservation;
- IN_FLIGHT, BURNED_UNKNOWN, missing terminal or public receipt followed by a
  new issue attempt;
- forged/stale/wrong-body no-effect reconciliation.

Expected: ticket/config/child/consumer effect `0`; existing and foreign state
preserved; retry `0`.

### T72-IPC

- oversized/truncated/trailing/reordered/replayed frames;
- duplicate keys, unknown kind/field, wrong version/sequence/transcript;
- copied nonce without channel, wrong image/token/session/parent/handle;
- post-launch image/config/handle swap;
- unauthenticated lookup/burn attempt.

Expected: no lookup oracle; exactly one authenticated entry may reach
`IN_FLIGHT`; all output body-free.

### T72-STATE

- double/concurrent redemption;
- caller ticket ID/time/expiry;
- backdated/future clock, rollback, suspend/resume and restart;
- exception/cancel/timeout/channel-close then reuse;
- crash at every durable/live transition;
- stale upstream receipt or same public receipt with different private event.

Expected: one ticket permits at most one command; every entry/exception burns;
restart revival `0`.

### T72-CONFIG

- nested duplicate equal/different, NaN/Infinity, BOM/trailing/control,
  invalid UTF-8, deep/wide/huge;
- absent target appears identical/different, same bytes/different inode;
- ancestor/reparse/hardlink/DACL and temp/target pre/post-publish swap;
- file/directory fsync or readback failure;
- wrong profile/command/receipt/expiry/self-hash;
- caller root/environment/CWD/ProgramData fallback;
- wrong config-parent binding and distribution-config mutation.

Expected: child/consumer effect `0`; foreign/ambiguous artifacts preserved;
distribution config byte delta `0`.

Every case separately asserts reservation, event, config, child, requested
consumer and unrelated-file deltas. Unknown publication state is never
reported as confirmed effect zero.

## 15. Test and Regression Plan

Initial source unit:

1. root/resource schema byte identity and closed-field validation;
2. public audit-object authority-zero tests;
3. private registry plus READY/IN_FLIGHT/BURNED state tests;
4. reservation and event predecessor model tests using a versioned TASK-068
   fixture adapter only;
5. strict config build/parse/readback tests with no child launch;
6. IPC frame/parser/transcript pure tests with fake numeric identities that
   create no native handle;
7. all T72-AUTH/ISSUE/IPC/STATE/CONFIG negatives;
8. TASK-063 U3/U4 fixture-contract regression and TASK-070 fixture ABI
   compatibility tests once those fixtures are canonical;
9. compileall, schema validation, diff/scope and secret/path leakage scans.

The A1 fixture set independently freezes the accepted design SHA-256, all
action profiles, the admitted D2S logical-command/subcommand pairs, public
request/audit-receipt identities, valid reservation/event coordinates, and
invalid coordinate/cross-command/state vectors. Tests compare implementation
and schema behavior to those fixture literals rather than deriving expected
values from implementation globals.

No test-only backend may be selectable from packaged or public source. Tests
may use local private harness objects but cannot label them Production or
native evidence.

## 16. Implementation Units after Dependency Gate

1. `A1 SCHEMA_AND_PUBLIC_AUDIT`: schemas, mirrors, audit objects and strict
   validators; authority/effect zero.
2. `A2 PRIVATE_RESERVATION_CORE`: consumer authorization snapshot, stable key,
   reservation/event model and restart recovery. The pure model and a
   versioned authority-zero TASK-068 fixture adapter may precede TASK-068
   completion; real immutable publication is gated.
3. `A3 LIVE_TICKET_CORE`: broker registry, authenticated-channel abstraction,
   READY/IN_FLIGHT/BURNED and exact-one concurrency tests; no real child.
4. `A4 CONFIG_V2_CORE`: internal config build/parser and strict negatives may
   precede TASK-068 completion; real immutable publish/read integration is
   gated; no real child.
5. `A5 IPC_PROTOCOL_CORE`: framing/transcript and process-binding port with
   pure/fake-handle tests only.
6. `A6 PHASE_COMPLETION`: focused/regression, independent Critic/Tester/Judge,
   exact completion receipt and handoff to TASK-063 U6-A.

A1, the pure/fixture part of A2, A3, the pure builder/parser part of A4 and A5
may begin after a fresh exact source allocation while declaring
`fixture_only=true`, `authority_created=false` and filesystem/child effect
zero. TASK-068 completion is required only for A2 reservation publication, A4
config publication/readback and A6 phase completion/handoff. None authorizes
the separate packaged Windows/native unit.

## 17. Completion Receipt

TASK-072-A completion requires one immutable task-local receipt binding:

- design identity and exact accepted design SHA-256;
- base, branch and head commit;
- exact changed paths and Git blob/raw SHA-256 for every source/schema/test;
- root/resource schema byte equality;
- TASK-068 accepted implementation/API/version and completion receipt;
- closed action subset and producer-version matrix implemented by A;
- focused commands and exact pass/skip/fail counts;
- T72-AUTH/ISSUE/IPC/STATE/CONFIG per-effect delta results;
- relevant TASK-063/TASK-070 regressions;
- diff/scope and body/path/secret scans;
- independent Tester and Critic with Critical/High `0/0`;
- Judge `PASS`;
- Windows-native/package status separately `NOT_EXECUTED` unless a later
  native allocation ran it;
- source/native/Release/Deploy/Production effect accounting.

The receipt is `TASK072_A_OP_TICKET_CORE_V1_COMPLETE` only. It cannot be
relabeled as TASK-072-B/C/D, installed, E2E, Human, Release, Deploy or
Production completion.

## 18. Current Stop and Resume Conditions

Current stop:

- TASK-068 source is present on main, but the completion documents are stale
  and do not yet provide a current accepted downstream binding.

Resume A1 source only after:

1. this exact detailed design receives independent Critic Critical/High
   `0/0` and Judge `PASS`;
2. exact source/schema/test Allowed Files and sole writer are allocated;
3. fresh origin/main/worktree/dirty/open-PR/lock checks pass.

Resume A2 real reservation publication, A4 real config publication/readback
and A6 completion/handoff only after TASK-068 publishes a current canonical
completion receipt naming the exact API/version consumed here. A1,
fixture-only A2, A3, pure A4 and A5 remain eligible after their separate exact
source allocation. Any dependency drift requires a fresh rebind and review.

Real child launch, packaged broker, Windows-native evidence, installer effect,
Release, Deploy and Production Activation remain separate explicit gates.
