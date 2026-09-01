# SKILL-D2S-001 completion and Platform Trust handoff design

Date: 2026-09-01

State: `DESIGN_ONLY / D2S_SOURCE_START0 / REAL_STAGE0 / EFFECT0`

## Scope and authority

This packet is the implementation-ready design for the Canonical SKILL owner.
It is not a source change, installed-copy synchronization, release, broker
implementation, BVP mutation, TASK-036 change, native launch or Production
Activation. The TASK-065 owner consumes only the final body-free completion
handoff described below.

The dirty eight-file worktree is exactly
`D:\BAI\BAI Davinci Resolve DRFX\skill_work\worktrees\installer-relative-learning-bridge`
on `codex/installer-relative-learning-bridge` at
`c86ec8c11724a3170d37e0fdc5a516979fcca703`, tracking `origin/main` with PR0.
Its dirty paths are `BVP_IMPLEMENTATION_WORK_ORDERS.md`,
`BVP_SIDE_REQUIRED_FEATURES_DETAILED_PROPOSAL.md`,
`examples/current-managed-skill-inventory.json`, and these five adapter paths:
`config/bvp-learning-connector.json`, `references/connector-ready-bridge.md`,
`schemas/connector-file-bridge.schema.json`, `scripts/bvp_adapter.py`, and
`tests/test_bvp_adapter.py`. They are read-only historical input: preserve-only,
no rebase/copy/commit and no authority. A fresh owner disposition is required
before any concept can be reimplemented from a clean canonical `origin/main`
worktree in one coherent D2S PR.

### Source-start currentness checkpoint

Read-only preflight on 2026-09-01 found the canonical SKILL checkout at
`5573a186ea296ca3626e0ef9c0e5d37c98a3576e` on
`codex/v0.7.0-governance-knowledge-skills`, not a fresh canonical `main`, with
an unrelated dirty `AGENTS.md`. Therefore `D2S_SOURCE_START0` remains
`N.C. / EFFECT0`: this checkout cannot be used to start, copy, commit or test
the D2S implementation. The separate eight-file worktree above remains
preserve-only.

Exact source-start resume condition: a D2S owner must create or select a clean
worktree from a freshly verified `origin/main` commit, record that commit and
branch, receive an explicit Allowed Files/overlap/lock disposition, then
rebind the source/release/install contract. Until all four are current, this
packet is design evidence only and no adapter/config/install/native/activation
effect is authorized.

### Proposed D2S Allowed Files

The D2S owner may change only these implementation paths after its fresh
overlap/lock check: `skills/bvp-montage-learning-adapter/SKILL.md`,
`scripts/bvp_adapter.py`, `tests/test_bvp_adapter.py`,
`config/bvp-learning-connector.json`, `schemas/adapter-messages.schema.json`,
`schemas/connector-file-bridge.schema.json`, `schemas/operation-config-v2.schema.json`,
`references/interface-spec.md`, `references/connector-ready-bridge.md`,
`references/operation-config-v2.md`, `examples/feedback.json`, and
`examples/learning-record.json` below that skill root. Shared
`examples/current-managed-skill-inventory.json`, `README.md`, `CHANGELOG.md`
and release evidence are not ordinary Allowed Files: each needs the repository
owner's short lock and final-diff disposition. BVP source, TASK-036 source,
installed copies, shared BVP docs, Timeline, product config and all private
paths are outside this scope.

## D2S_PUBLISH_LEARNING transport state machine

```text
DISABLED_SENTINEL
  -> PRODUCT_PLAN_BOUND
  -> RECORD_RESERVED
  -> BROKER_REDEEMED_IN_FLIGHT
  -> STAGE_EXACT1
  -> TASK036_IMPORT_EXACT1
  -> BVP_TERMINAL_QUERY
  -> TASK069_CANONICAL_AND_PROFILE_READBACK
  -> COMPLETION_HANDOFF

any reject/crash/expiry/cancel/restart -> FAILED_CLOSED
```

This is the publish-only state machine. `D2S_LOAD_PROFILE` and the broker-only
`D2S_TERMINAL_QUERY_V1` have the separate, mutually exclusive action branches
defined in the broker closure below; neither may enter stage/import states.

Only the trusted Product broker may enter `BROKER_REDEEMED_IN_FLIGHT`. The
adapter cannot mint, deserialize, reconstruct or extend that state. A ticket
is atomically consumed before the first D2S effect and burns on success,
rejection, exception, timeout, cancellation, channel close, child exit or
restart. A new operation requires a new plan, ticket, nonce and immutable
config coordinate. The distribution config is a byte-stable `enabled:false`,
`bridge_root:null` sentinel and is never an active-root fallback or an
operation config.

### Broker redemption, crash and replay closure

The trusted broker owns an operation ledger that is private to the selected
Product installation. A ledger entry binds the one-use ticket digest and nonce,
action, operation ID, exact plan/config snapshots, expected command digest,
selected instance/owner, Product/adapter/broker build identities, trusted
time-domain/session, expiry and invocation budget. It contains no reusable
ticket, raw bridge/config path, delivery/Profile body or caller clock. The
entry is created or advanced only by an identity-CAS transaction over the same
opened ledger snapshot; public self-hashes, serialized maps and copied config
bytes cannot create or advance it.

Before consuming a publish ticket, the broker identity-CAS creates one durable
active record reservation at the selected-instance key
`(instance physical identity, D2S_PUBLISH_LEARNING, record_id)`. The
reservation binds the record digest, delivery digest, immutable config identity,
expected command and prospective operation/ticket identities. It is not a
caller object and has no path/name discovery surface. A second valid publish
operation with exactly the same binding observes `RECORD_RESERVED / EFFECT0`;
a record ID with any different digest, delivery or config identity is
`RECORD_ID_COLLISION / STOP_PRESERVE / EFFECT0`. Only the reservation owner can
atomically consume its bound ticket and advance to `IN_FLIGHT`.

| Durable broker phase | Required precondition and permitted next work | Crash/replay result |
| --- | --- | --- |
| `ARMED` | a current exact plan resolves one immutable config snapshot; no operation entry exists | a failed validation creates no entry and no D2S effect; replay requires the still-current trusted resolver, never a caller retry parameter |
| `RESERVED` | one exact publish record reservation is durable before ticket consumption and binds the prospective operation snapshot | non-owner or different operation cannot consume/stage/import; crash before consume burns the pending ticket and remains `FAILED_CLOSED / EFFECT0` until a trusted no-effect resolver closes it |
| `IN_FLIGHT` | broker has atomically consumed the exact ticket and durably recorded the bound snapshot before child launch | second/concurrent/replayed ticket is `TICKET_CONSUMED / EFFECT0`; a crash before launch burns this entry and requires a fresh plan/ticket, with no implicit retry |
| `LAUNCH_ATTEMPTED` | broker has a durable child-launch intent while retaining the broker lease and pinned config identity | crash/child-channel loss is `FAILED_CLOSED / EFFECT_UNKNOWN`; no second child, stage or import may be attempted from this entry |
| `STAGE_REPORTED` | exactly one adapter stage result is captured against the same operation and command digest | broker may only identity-CAS this exact entry to `IMPORT_ATTEMPTED`; later publish reuse, copied receipt or self-reported status is `EXACT_ONE_VIOLATION / EFFECT0` |
| `IMPORT_ATTEMPTED` | before dispatch, the broker has durably bound the exact TASK-036 operation/ticket/import coordinate and expected result to the same opened entry snapshot | crash/channel loss or concurrent resolver is `IMPORT_EFFECT_UNKNOWN / FAILED_CLOSED`; second import dispatch is zero and only pinned read-only resolution of that exact committed event is allowed |
| `IMPORT_REPORTED` | exactly one TASK-036 import result is captured by advancing the same opened `IMPORT_ATTEMPTED` snapshot; the original publish ticket remains burned | a new broker-only terminal-query operation may read state; it must not inherit publish or load authority and cannot stage/import |
| `TERMINAL_READBACK` | TASK-069 has pinned matching receipt, correlation, canonical and Profile producer state; the active record reservation is converted to an immutable exact terminal binding | a fresh same-record/same-binding request returns typed `DUPLICATE / EFFECT0`; different binding remains collision STOP; this evidence cannot reopen any prior effect entry or enable connector activation |
| `FAILED_CLOSED` | any reject, expiry, cancellation, exception, crash or currentness ambiguity | preserve all producer state, emit body-free code and require a fresh authoritative resolver; cleanup/retry by path or stale ticket is forbidden |

Action transitions are closed and mutually exclusive. `D2S_PUBLISH_LEARNING`
alone follows `RESERVED -> IN_FLIGHT -> LAUNCH_ATTEMPTED -> STAGE_REPORTED ->
IMPORT_ATTEMPTED -> IMPORT_REPORTED`. `D2S_LOAD_PROFILE` instead follows
`IN_FLIGHT -> LOAD_ATTEMPTED -> LOAD_REPORTED` using its own ticket and
expected Profile result; it can never stage, import, read an admission receipt
or enter the correlation/terminal chain. `D2S_TERMINAL_QUERY_V1` consumes a
separate terminal-only ticket, follows `IN_FLIGHT -> TERMINAL_READBACK` or
`FAILED_CLOSED`, and is read-only: it cannot stage, load, import or enable.
Every action burns on success, exception, expiry, channel loss and restart.

The broker holds its lease from `IN_FLIGHT` through pinned child result capture.
It never downgrades an entry to `ARMED`, even after a known no-effect failure.
Where a crash leaves effect presence unknown, recovery may perform a separate
read-only terminal query using a new terminal-only authorization, but may not
launch, stage, import, delete or repair. This preserves `ticket 1 -> exact
command effect 0/1`; it does not turn an uncertain first effect into permission
for a second effect.

## Strict input and physical-I/O contract

Every security-relevant config, receipt, delivery or Profile read starts from
one nofollow, handle-pinned root/ancestor/file snapshot. Each ancestor is kept
open and verified for type, DACL, no-reparse and physical identity; children
are opened/published handle-relatively, or by an equivalently held broker
handle. Path/stat sampling, path reopen, parent scans, fixed ProgramData,
default config omission, mutable pointer and newest/timestamp selection are
not substitutes.

The strict UTF-8 parser rejects BOM, duplicate keys at every depth, non-finite
numbers, trailing non-whitespace, invalid controls/UTF-8 and non-built-in JSON
values before schema work, privacy scan, canonicalization or logging. It
enforces document bytes, depth, object-member, array-item and string bounds.
One snapshot binds raw bytes/hash, canonical bytes/hash and physical identity.
Ambiguous input is preserved and produces body-free `EFFECT0`.

Output publication is operation-owned only: unique no-replace temp, exact
identity/durability validation, no-replace target publication and pinned
post-read. Unknown or foreign replacement is never cleaned up. Directory
durability must be observed through a Windows-native port; no-op, swallowed or
unsupported durability is `FAIL / RECEIPT0`. A failure before publication has
delta zero. A failure after publication is `STOP_PRESERVE / EFFECT_UNKNOWN`:
the target is never removed or overwritten merely to recreate a zero-delta
state, and retry requires a fresh exact resolver.

## Closed operation-config v2 and broker contract

`BvpOperationSpecificConfig` is a data projection, never a bearer token. Its
closed fields bind exactly one action, command, operation ID, ticket nonce,
TASK-061-A prepare receipt, TASK-063 instance/descriptor/owner, product and
adapter build, plan, privacy projection, argv, installed-package receipt,
record/delivery/result or Profile/result identities, expiry and budget one.
It carries no raw root/path/handle/secret/payload/receipt body/backend selector
or clock selector.

The schema and validator must enforce an action-specific exact null/non-null
matrix:

| Action | Required non-null identities | Required null identities |
| --- | --- | --- |
| `D2S_PUBLISH_LEARNING` | record, record digest, delivery digest, expected stage result | Profile identity/result |
| `D2S_LOAD_PROFILE` | Profile identity/digest, expected profile result | record, delivery and publish result |
| broker-only `D2S_TERMINAL_QUERY_V1` | prior operation, public receipt digest, correlation digest, canonical and Profile readback digests | publish/load effect input identities |

The Product broker verifies the same pinned config physical identity and every
bound value before atomic redemption. The legacy v1 CLI may remain only as a
safe local compatibility mode; it is structurally ineligible for a packaged
or installed Product operation. Direct CLI, copied config, deserialized map,
wrong subcommand and any caller-selected `--config`, `--learning` or `--output`
cannot enter the broker path.

Before TASK-061-A or TASK-036 may consume D2S, the D2S owner issues
`D2S_001_INTERFACE_COMPLETION_READBACK_V1`. It is a versioned, body-free
source/release/install readback for the corrected interface only: canonical
source/schema/test and installed-byte identities, disabled-sentinel identity,
strict-I/O/privacy/broker-interface/native-durability contract versions and
their focused static results. It has `executed:false`, no operation/ticket/
stage/import/receipt/correlation/Profile fields, and `authority_created:false`.
It proves neither a real command nor an E2E outcome; it is the only D2S receipt
eligible before TASK-061-A/TASK-036 and therefore cannot create a cycle.

### Read-only implementation entry map

At the clean D2S design baseline, the following symbols delimit the later
one-PR source change. This table is a source map, not a claim that the current
implementation is operation-authorized or completion-ready.

| Current symbol | Existing bounded behavior | Required Product boundary | Fault rows |
| --- | --- | --- | --- |
| `_load_json_document` / `_parse_json_bytes` | parses one pinned file with strict duplicate/non-finite/UTF-8/tree checks | preserve the same opened snapshot through broker-owned identity binding; do not use a later path reopen as equivalence proof | D2S-I01 |
| `load_operation_config_v2` / `validate_operation_config_v2` | validates a v2 document and returns an audit-only pinned-read receipt | broker must resolve an immutable v2 snapshot internally and bind it to a live one-use operation; v2 bytes alone remain authority zero | D2S-A01, D2S-C01 |
| `build_parser` / `main` | legacy connector commands route through `load_connector_config` and invoke direct publish/load functions | packaged Product entry accepts only an opaque operation coordinate; raw CLI config/learning/output stays legacy-local and cannot enter broker dispatch | D2S-A01, D2S-S01 |
| `publish_learning_export` | performs the current direct staging behavior after v1 flag checks | only a redeemed publish action may call it once under a held broker lease; it cannot confirm terminal state by a second publish | D2S-A02, D2S-S01, D2S-T01 |
| `load_preference_profile` | performs the current advisory profile read after v1 flag checks | only a redeemed load action may call it, with no record/delivery input and no activation authority | D2S-A01, D2S-C01 |
| `atomic_write_new_or_identical` | owns current immutable-output publication mechanics | operation publisher must add pinned-ancestor/operation-root/lease/durability semantics and retain postpublish ambiguity as `EFFECT_UNKNOWN` | D2S-I02, D2S-I03 |
| `validate_admission_receipt` | validates a public receipt shape | terminal broker query must additionally bind trusted correlation plus canonical and Profile readbacks; receipt shape/status alone is non-authoritative | D2S-T01 |
| `feedback_to_learning` / `validate_learning_export` / `_validate_post_build_privacy_projection` / `redact_sensitive` | supplies current adapter privacy projection and validation handling | closed per-contract projection must precede canonical bytes/hash/staging, with value grammar and body-free rejection | D2S-P01, D2S-O01 |

No symbol in this map is a substitute for the Product broker. In particular,
calling a function directly, importing it in-process, passing its v2 config or
copying its read receipt cannot enter `BROKER_REDEEMED_IN_FLIGHT`.

## Privacy-before-hash and public projection

Before canonical hash or stage, the adapter performs a closed per-contract
privacy projection. It accepts only bounded reason codes, IDs, actor roles,
style/context/tag grammars and typed provenance allowlists. It rejects raw
drive/UNC/home/repository/URI paths, email/account/SID, secret/token-like
values, control/NUL, transcript-like content, unknown nested values and
normalization/homoglyph evasions. Free-form Human rationale remains local
private evidence. `safe_export:true`, a public redaction report or a key name
never makes an unsafe value safe.

All public status/result/error/receipt projections are body-free stable codes
plus opaque IDs and hashes. `connector-status`, including transport-available
status, explicitly records `authority_created:false`, terminal/correlation/
Profile verification false and cannot be used as stage, canonical, activation
or Profile authority.

### Outcome L UI status projection ABI

The future UI receives only `BVP_LEARNING_LINKAGE_UI_STATUS_V1`, a closed
display projection built by a trusted read-only status resolver. It is never a
broker request, ticket, command, retry handle or activation control. Rendering,
refreshing, copying or deserializing the projection has no adapter, TASK-036,
Profile, config/history or activation effect.

| Closed UI field group | Allowed value | Forbidden interpretation/value |
| --- | --- | --- |
| identity | fixed message type/schema version and an opaque display correlation | raw operation/ticket/receipt/correlation/Profile IDs or bodies |
| display state | exactly `DISABLED_LEGACY_SAFE`, `NOT_CONFIRMED`, `PREACTIVATION_CHAIN_OBSERVED_NO_ACTIVATION` or `FAILED_CLOSED` | `READY`, activation enabled, canonical admission or Profile-write success |
| evidence flags | `authority_created:false`, `activation_authorized:false`, `activation_executed:false`, `ui_adapter_call_count:0`, `ui_task036_call_count:0` | any currentness/capability/command flag true because the UI rendered it |
| optional outcome | one stable body-free reason code and opaque source/build digest only | filesystem/root/config path, account/SID, OS exception, secret, delivery/receipt/Profile content |

The resolver applies this total, mutually exclusive precedence: (1) a trusted
selected-instance `FAILED_CLOSED` outcome maps to `FAILED_CLOSED`; otherwise
(2) an exact current pinned TASK-036/TASK-069/TASK-061-B historical chain maps
to `PREACTIVATION_CHAIN_OBSERVED_NO_ACTIVATION`; otherwise (3) any expected or
attempted chain that is missing, stale, ambiguous or incomplete maps to
`NOT_CONFIRMED`; otherwise (4) only a current disabled sentinel with no
producer-chain attempt or evidence maps to `DISABLED_LEGACY_SAFE`. Thus the
sentinel cannot mask a verified, stale or failed-closed producer state. No UI
state can replace the producer receipts or authorize a retry.
`PREACTIVATION_CHAIN_OBSERVED_NO_ACTIVATION` describes historical evidence
only: it does not set `enabled:true` or satisfy the separate Human Activation
Gate.

## Exact-one stage, TASK-036 and TASK-069 handoffs

The broker-issued `TASK036_D2S_EXECUTION_HANDOFF_V1` is private to the bounded
Product operation. It resolves the immutable delivery coordinate internally;
TASK-036 receives no raw path or reusable config. It binds action, operation,
ticket-consume result, selected installation, config snapshot, record/delivery
digest, privacy projection, expected command and expiry. It permits exactly
one adapter stage then exactly one selected `import_path`, not inbox scan or
`import_once`.

After stage/import, a different read-only
`TASK069_D2S_TERMINAL_READBACK_V1` requires the exact public receipt digest,
hidden BVP correlation digest, canonical Generic/Project readback digest and
advisory Profile readback digest, all current to the same operation/instance/
config/build. It must never rerun `publish-learning` merely to check a receipt;
`canonical_store_written` is false/non-authoritative. Terminal query produces
no delivery, import, Profile, config or activation delta.

### TASK-069 terminal-readback consumer ABI

`TASK069_D2S_TERMINAL_READBACK_V1` is a closed, durable, body-free readback
record, not an operation ticket or a substitute for producer state. TASK-069
obtains every input from the same broker-held, strict, handle-pinned snapshots;
it does not accept a caller mapping, path, status string, config object,
receipt body, correlation body or Profile body. A public projection contains
only opaque IDs, digests, typed outcome codes and `authority_created:false`.
The private snapshot is retained under the producer lifecycle policy for later
fresh reads by TASK-061-B/TASK-065.

TASK-069 implementation completion remains upstream of TASK-036 in the
canonical dependency graph. This section specifies a runtime invocation of
that already-completed read-only component after TASK-036, not a new dependency
on TASK-069 task completion and not an edge back into the implementation graph.

The record has exactly the following closed field groups. Each digest is an
algorithm-tagged digest of one already-opened canonical bytes/identity
snapshot, never a value recomputed after reopening a path.

| Closed group | Required bindings | Reject if absent, mixed or stale |
| --- | --- | --- |
| identity/version | message type, schema version, operation ID, terminal action, Product/broker/adapter build identities | unknown fields/version, non-terminal action, caller-selected mode |
| operation/install | consumed-operation digest, selected TASK-063 instance/descriptor/owner identities, v2 config raw/canonical/physical digests, source/release/install currentness | operation/action/instance/config/build mismatch, copied config or cross-install record |
| exact-one history | stage result digest, TASK-036 import result digest, stage count `1`, import count `1`, no TASK-069 adapter/import invocation counters `0` | count other than one, missing result, local republish/import, `import_once` or scan evidence |
| terminal receipt/correlation | public receipt canonical digest plus exact allowed terminal status, hidden BVP correlation digest, correlation operation/record/delivery binding | receipt-only, extra receipt fields, wrong/missing correlation, `REJECTED`, receipt/correlation from another operation |
| canonical/Profile readback | pinned canonical Generic/Project readback digest, pinned advisory Profile readback digest, respective physical/currentness identities | missing Profile, receipt-only/status-only, stale or same-bytes/different-identity readback |
| trusted time/result | broker trusted-time domain/build, terminal query time, expiry/currentness decision and typed strict/privacy/durability results | caller clock, expired/unknown time, non-PASS prerequisite, body-bearing error |
| public projection | `authority_created:false`, stable terminal code, opaque IDs/digests only | raw path/body/secret/account/SID/OS detail, READY/activation implication |

`ACCEPTED` and `DUPLICATE` are terminal observations only when every group
above refers to the same exact operation and current producer state. A
`DUPLICATE` never repairs, republishes, imports, advances a Profile or creates
a new capability. On an ambiguous/missing/stale group, TASK-069 returns the
typed `TERMINAL_READBACK_N.C. / EFFECT0`, preserves producer state and requires
a fresh full resolver; it does not retry adapter staging or TASK-036 import.

TASK-065 PL-C01a consumes this record by pinned-reading and joining it with the
already-completed TASK-036/TASK-061-B producer records. It invokes neither the
adapter nor TASK-036 and therefore has Project, Bridge, Profile, config/history
and activation delta `0`. The stage/import values above are historical producer
facts only, not TASK-065 commands or completion authority by themselves.

After the bounded TASK-036 operation, the body-free, versioned
`D2S_001_OPERATION_TERMINAL_HANDOFF_V1` issued to Design B / Platform Trust
binds contract/version, the exact
`D2S_001_INTERFACE_COMPLETION_READBACK_V1` identity, canonical source/release
and installed-byte currentness, exact TASK-072/Platform Trust implementation
completion receipt, broker protocol/version/build, native backend/host/session
identity, operation/phase digests, stage/import counters, public receipt/
correlation/canonical/Profile readback digests, strict/privacy/durability result
codes, trusted time/expiry, and `authority_created:false`. It is issued only
after the full chain passes and is consumed only by TASK-061-B/TASK-065.
TASK-069, TASK-061-B and TASK-065 independently pinned-read the real producer
state; this public handoff is not an effect capability.

## Mandatory negative and fault matrix

| ID | Source symbol | Precondition | Fault seam | Expected typed result | Project delta | Bridge delta | Profile delta | Config/history delta | Public leakage | Evidence receipt |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| D2S-A01 | broker entry | v2 config offered | direct v1/v2 CLI, copied/deserialized config, caller raw path, wrong/cross command | `BROKER_AUTHORITY_INVALID / EFFECT0` | 0 | 0 | 0 | 0 | path/ticket/body 0 | no consume receipt |
| D2S-A02 | broker redemption | exact ticket is current | second/concurrent/replay/expired ticket, crash before/after redeem/stage, restart | first command 0/1; later `FAILED_CLOSED / EFFECT0` | 0 | 0/1 | 0 | 0 | ticket/config 0 | atomic consume + burn state |
| D2S-A03 | broker action gate | action-specific ticket is current | publish ticket enters load/terminal, load ticket stages/imports, terminal ticket has an effect | `ACTION_TRANSITION_INVALID / FAILED_CLOSED / EFFECT0` | 0 | 0 | 0 | 0 | ticket/body 0 | action-bound burn state |
| D2S-A04 | publish record reservation | two valid publish plans target one selected instance and record ID | concurrent A/B same binding; B different delivery/config/record digest; restart while A reserved/staged/import-unknown; fresh request after exact terminal | same active -> `RECORD_RESERVED / EFFECT0`; different -> `RECORD_ID_COLLISION / STOP_PRESERVE / EFFECT0`; terminal same -> `DUPLICATE / EFFECT0`; A bridge delta 0/1, B dispatch 0 | 0 | A 0/1; B 0 | 0 | 0 | record/delivery/config/ticket body 0 | durable reservation or exact immutable terminal binding |
| D2S-I01 | strict pinned reader | authority document offered | duplicate/nonfinite/BOM/trailing/control/deep/oversize; config/receipt/Profile ancestor ABA/reparse swap | `AMBIGUOUS_INPUT / STOP_PRESERVE / EFFECT0` | 0 | 0 | 0 | 0 | body/path/OS 0 | no completion receipt |
| D2S-I02 | owned publisher | stage target absent/current | parent swap, foreign temp, target appears or prepublish file-fsync failure | `PUBLISH_CURRENTNESS_FAILED / STOP_PRESERVE / EFFECT0` | 0 | 0 | 0 | 0 | path/OS 0 | no stage receipt |
| D2S-I03 | owned publisher durability | target may already be no-replace published | postpublish directory durability failure or unsupported native port | `STOP_PRESERVE / RECEIPT0 / EFFECT_UNKNOWN`; fresh exact resolver required before retry | 0 | 0/1 | 0 | 0 | path/OS 0 | no completion receipt |
| D2S-P01 | privacy projection | generic learning input offered | benign-key path/email/token/transcript, free reason, unknown nested field, oversize/homoglyph | `PRIVACY_REJECTED / EFFECT0` | 0 | 0 | 0 | 0 | raw bytes 0 | body-free reject |
| D2S-S01 | stage dispatcher | valid broker operation | stage count not one, `import_once`/scan, receipt arrives after preflight, second publish/import | `EXACT_ONE_VIOLATION / FAILED_CLOSED / EFFECT0` | 0 | 0/1 | 0 | 0 | delivery/receipt body 0 | one stage + one import only |
| D2S-S02 | import attempt ledger | exact stage is reported and `IMPORT_ATTEMPTED` is durable | TASK-036 import effect then crash/channel loss before `IMPORT_REPORTED`; restart/concurrent resolver | `IMPORT_EFFECT_UNKNOWN / FAILED_CLOSED`; import count 0/1 and second dispatch 0 | 0 | 0/1 | 0 | 0 | import/body 0 | exact attempt snapshot; no terminal handoff |
| D2S-T01 | terminal query | stage/import historical facts exist | receipt-only, missing/wrong correlation/canonical/Profile, status-only or `canonical_store_written` | `TERMINAL_READBACK_N.C. / EFFECT0` | 0 | 0 | 0 | 0 | correlation/body 0 | no completion handoff |
| D2S-C01 | v2 action validator | action document offered | publish Profile bind, load record bind, null/mixed result or cross-action identity | `ACTION_BINDING_INVALID / EFFECT0` | 0 | 0 | 0 | 0 | body 0 | no read receipt |
| D2S-O01 | public projector | any outcome emitted | READY/status/handoff leaks path/body/secret/account/SID or implies authority | `PUBLIC_PROJECTION_REJECTED / EFFECT0` | 0 | 0 | 0 | 0 | raw value 0 | body-free only |
| D2S-U01 | UI status resolver | display projection requested | copied/deserialized UI status, forged verified state, stale producer chain, render/refresh callback, path/body/error injection | `NOT_CONFIRMED` or `FAILED_CLOSED / EFFECT0`; UI adapter/TASK-036 calls 0 and activation false | 0 | 0 | 0 | 0 | path/body/account/SID/OS 0 | no capability or completion receipt |
| D2S-U02 | UI status precedence | disabled sentinel is present with producer-state combination | sentinel plus current verified chain, stale/incomplete chain or selected-instance failed-closed outcome | verified -> `PREACTIVATION_CHAIN_OBSERVED_NO_ACTIVATION`; stale -> `NOT_CONFIRMED`; failed -> `FAILED_CLOSED`; UI local effect 0 | 0 | 0 | 0 | 0 | body/path/producer details 0 | display projection only; no capability or completion receipt |

`D2S-A03` is limited to invalid pre-effect cross-action transitions. No row may
map a post-dispatch publish, TASK-036 import or durability crash to `EFFECT0`:
their effect certainty and 0/1 delta remain solely under D2S-A02, D2S-S02 and
D2S-I03.

## Design completion and implementation start Gate

Before the D2S owner starts source work, this packet requires independent
Critic `C=0 / H=0`, Judge PASS, a fresh canonical-main worktree, explicit
owner/Allowed Files disposition and a conflict-free one-PR plan. Before
TASK-061-A/TASK-036 can consume the interface, the source PR must land and
`D2S_001_INTERFACE_COMPLETION_READBACK_V1` must prove current release/install
bytes and the static contract. Broker/native-durability evidence must execute
before a real stage. Only after TASK-036 can
`D2S_001_OPERATION_TERMINAL_HANDOFF_V1` exist for TASK-061-B/TASK-065. Until
the relevant receipt exists, each downstream real-effect cell is
`N.C. / START0 / EFFECT0`.

## Public-safe synthetic contract fixture

`d2s-001-completion-handoff-fixture-v1.json` is a task-local, static
shape-and-separation fixture. It exercises public-safe field presence,
action separation and the expected historical-cardinality assertions without
creating a ticket, broker capability, completion receipt, currentness proof or
effect. Every execution/currentness/completion predicate in the fixture is
explicitly `false`; every local delta is the string `"0"`.

The fixture keeps `D2S_PUBLISH_LEARNING` record coordinates and
`D2S_LOAD_PROFILE` profile coordinates in separate objects. Its one stage and
one import values are observations expected of the historical TASK-036
operation, never commands that TASK-065 may run. In particular, the fixture
does not invoke the adapter, TASK-036, terminal query, installed config,
native backend or activation path. It cannot satisfy either
`D2S_001_INTERFACE_COMPLETION_READBACK_V1` or
`D2S_001_OPERATION_TERMINAL_HANDOFF_V1`.

Fixture validation is limited to static parsing, exact expected field values
and body-free public projection assertions. Replay, expiry, crash, swap and
durability rows remain source-owner negative tests in the fault matrix above;
the synthetic fixture is not evidence that those source paths are fixed. Its
recovery fields model the mutually exclusive publish/load/terminal state
shapes and the `IMPORT_EFFECT_UNKNOWN` no-second-dispatch expectation only;
they create no broker ledger, consume no ticket and launch no child.
The reservation expectation is similarly shape-only: it models same-binding
reservation, different-binding collision and terminal duplicate codes without
reserving a record or dispatching a conflicting publish operation.
Its UI fields are likewise a static `NOT_CONFIRMED` display expectation, never
a currentness proof, retry handle or Activation Gate outcome.
