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

## Non-negotiable transport state machine

```text
DISABLED_SENTINEL
  -> PRODUCT_PLAN_BOUND
  -> BROKER_REDEEMED_IN_FLIGHT
  -> STAGE_EXACT1
  -> TASK036_IMPORT_EXACT1
  -> BVP_TERMINAL_QUERY
  -> TASK069_CANONICAL_AND_PROFILE_READBACK
  -> COMPLETION_HANDOFF

any reject/crash/expiry/cancel/restart -> FAILED_CLOSED
```

Only the trusted Product broker may enter `BROKER_REDEEMED_IN_FLIGHT`. The
adapter cannot mint, deserialize, reconstruct or extend that state. A ticket
is atomically consumed before the first D2S effect and burns on success,
rejection, exception, timeout, cancellation, channel close, child exit or
restart. A new operation requires a new plan, ticket, nonce and immutable
config coordinate. The distribution config is a byte-stable `enabled:false`,
`bridge_root:null` sentinel and is never an active-root fallback or an
operation config.

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
| D2S-I01 | strict pinned reader | authority document offered | duplicate/nonfinite/BOM/trailing/control/deep/oversize; config/receipt/Profile ancestor ABA/reparse swap | `AMBIGUOUS_INPUT / STOP_PRESERVE / EFFECT0` | 0 | 0 | 0 | 0 | body/path/OS 0 | no completion receipt |
| D2S-I02 | owned publisher | stage target absent/current | parent swap, foreign temp, target appears or prepublish file-fsync failure | `PUBLISH_CURRENTNESS_FAILED / STOP_PRESERVE / EFFECT0` | 0 | 0 | 0 | 0 | path/OS 0 | no stage receipt |
| D2S-I03 | owned publisher durability | target may already be no-replace published | postpublish directory durability failure or unsupported native port | `STOP_PRESERVE / RECEIPT0 / EFFECT_UNKNOWN`; fresh exact resolver required before retry | 0 | 0/1 | 0 | 0 | path/OS 0 | no completion receipt |
| D2S-P01 | privacy projection | generic learning input offered | benign-key path/email/token/transcript, free reason, unknown nested field, oversize/homoglyph | `PRIVACY_REJECTED / EFFECT0` | 0 | 0 | 0 | 0 | raw bytes 0 | body-free reject |
| D2S-S01 | stage dispatcher | valid broker operation | stage count not one, `import_once`/scan, receipt arrives after preflight, second publish/import | `EXACT_ONE_VIOLATION / FAILED_CLOSED / EFFECT0` | 0 | 0/1 | 0 | 0 | delivery/receipt body 0 | one stage + one import only |
| D2S-T01 | terminal query | stage/import historical facts exist | receipt-only, missing/wrong correlation/canonical/Profile, status-only or `canonical_store_written` | `TERMINAL_READBACK_N.C. / EFFECT0` | 0 | 0 | 0 | 0 | correlation/body 0 | no completion handoff |
| D2S-C01 | v2 action validator | action document offered | publish Profile bind, load record bind, null/mixed result or cross-action identity | `ACTION_BINDING_INVALID / EFFECT0` | 0 | 0 | 0 | 0 | body 0 | no read receipt |
| D2S-O01 | public projector | any outcome emitted | READY/status/handoff leaks path/body/secret/account/SID or implies authority | `PUBLIC_PROJECTION_REJECTED / EFFECT0` | 0 | 0 | 0 | 0 | raw value 0 | body-free only |

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
the synthetic fixture is not evidence that those source paths are fixed.
