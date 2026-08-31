# TASK-065 PL-B Option B Runtime Config Design Correction

Date: `2026-08-31`
Task: `TASK-065`
Atomic Unit: task-local design correction only
State: `CANDIDATE / CRITIC_JUDGE_PENDING / IMPLEMENTATION_START0 / EFFECT0`

## 1. Authority and current gate

This packet records the Owner-selected Option B at BVP canonical main
`35cdf1ad475633dcf035e0616e979b5a8fde0c88`. It does not grant source, schema,
test, installed-config, adapter-execution, native, Release, Deploy or Production
authority.

D0, D1 and D2 canonical completion remain unproven. In particular, TASK-063
post-repair native install/read-back terminal evidence is absent, TASK-060 PP-C
remains an independently pending implementation candidate, and TASK-061 CA-C
remains a disabled-history candidate with the real installed E2E gate open.
Current main also has no installed Product-operation caller for
`MontageLearningBridgeApplication.import_path`; the facade is
exercised only by tests, so a staged delivery cannot currently advance to a
BVP admission receipt.
Only this TASK-065-local design/test-plan correction may change before those
gates and the required DEV-4 Critic/Judge decision close.

## 2. Canonical correction

PL-B does not edit the canonical SKILL source config or its installed
distribution copy. Both remain byte-unchanged, `enabled:false`, and retain the
historical fixed-ProgramData default as inactive distribution evidence. No
production invocation may omit `--config`, use that default, or fall back to
fixed ProgramData.

PL-B instead projects a BVP-owned, instance-bound adapter config beneath the
exact TASK-063 installer-relative Bridge. TASK-061 remains the sole owner of
Human activation/deactivation and its append-only config history. TASK-065 owns
only coordinate projection and exact adapter invocation. The SKILL consumes the
explicit config and has authority zero.

## 3. Ownership matrix

| Object/effect | Sole owner | TASK-065 permission |
|---|---|---|
| canonical/installed SKILL config | SKILL release/distribution process | read-only; mutation zero |
| TASK-063 descriptor, owner manifest and Bridge discovery | TASK-063 | exact read-only admission |
| promoted Preference source | TASK-060 PP-C | exact read-only admission |
| Human evidence, activation/deactivation and history | TASK-061 CA-C or authorized successor | consume exact receipt only |
| runtime adapter config projection | TASK-065 PL-B | project coordinates; no authority expansion |
| connector transport E2E | TASK-065 PL-C | separately gated public-safe execution |
| learning admission/promotion and Timeline/Resolve | existing owners/Human gates | mutation zero |

This packet supersedes the earlier PL-B statements that only `bridge_root` may
change or that the distribution receipt policy must be preserved. Option B is
a separate closed runtime projection policy; it requires an admission receipt
without mutating the distribution default.

## 4. Exact BVP-owned coordinates

All serialized relative paths use `/`; Windows runtime joins them below the
already admitted private absolute Bridge root.

```text
<bridge_root>/state/
|-- connector-runtime-config.lock
`-- connector-operations/
    `-- <operation_id>/
        `-- <exact-command>/
            |-- connector-runtime-config.plan.json    # exact trusted selector input
            |-- connector-runtime-config.json         # immutable invocation input
            |-- connector-runtime-config.receipt.json # immutable binding
            |-- connector-runtime-config.consume.json # one-shot terminal state
            |-- connector-runtime-config.tombstone.json # immutable retirement
            `-- transitions/
                |-- 0000-prepared.json
                |-- 0001-config-published.json
                |-- 0002-receipt-published.json
                `-- 0003-terminal.json
```

- `<bridge_root>` is derived only from the exact current TASK-063 discovery and
  is never read from the SKILL distribution default.
- `<operation_id>` is a bounded opaque coordinate bound inside the separately
  authorized TASK-061-A PREACTIVATION PREPARE receipt; neither identifier, path nor hash
  creates authority by itself.
- There is no shared mutable adapter-facing steady-state config or BVP current
  pointer. Each launch receives one immutable operation-specific config path.
  The exact current generation is selected only by a consumer-owned trusted
  plan/durable receipt that binds the operation coordinate, predecessor and
  terminal-transition digest. Directory enumeration, scan-highest/newest and
  a caller-selected unbound coordinate never select authority.
  A portable move, repair or upgrade requires a new operation coordinate from
  fresh TASK-063 discovery; an embedded absolute root is never reused as
  currentness evidence.
- Fresh BVP `main=35cdf1ad475633dcf035e0616e979b5a8fde0c88` collision audit found
  the existing `state/` authorities named `importer-journal.json`,
  `profile-promotion-journal.json`, `profile-promotion-commit-marker.json`, and
  `connector-activation-history.json`; none collides with the frozen lock,
  transition or operation-directory namespaces above. Any newly
  current file or case-folded name collision
  before implementation invalidates this freeze and yields effect zero pending
  a fresh owner review.
- The historical `PL-B0` label below denotes only the TASK-036 preactivation
  config candidate; it is SUPERSEDED as a TASK-065 phase name. That candidate
  never creates or replaces shared steady-state projection state.
- The adapter receives only the absolute, reopened operation-specific config
  path via `--config`. It never receives the distribution config or an inferred
  default.

## 5. Adapter-facing config and BVP receipts

### 5.1 Adapter-facing config and required operation authority

`connector-runtime-config.json` is a closed SKILL v1 config body with
exactly these fields:

```text
schema_version = "1.0.0"
message_type = "BvpMontageLearningConnectorConfig"
enabled = <derived state>
contract_profile = "bvp-task029-file-bridge-v1"
bridge_root = <exact private absolute TASK-063-derived Bridge root>
learning_publish_enabled = <operation policy>
preference_read_enabled = <operation policy>
require_admission_receipt = true
legacy_behavior_when_unavailable = true
```

The config has no extra BVP authority fields because the current SKILL parser
accepts only its closed transport shape. A separate BVP projection receipt can
bind audit data for BVP, but the current adapter never verifies or consumes that
receipt. The absolute `bridge_root` is private local state and must never appear
in public Evidence, logs or exception text.

This v1 shape cannot enforce the TASK-036 preactivation operation or per-
invocation steady-state authority. It
contains no operation/operation ID, TASK-063 instance/descriptor/owner binding,
projection-receipt digest, TASK-061 one-shot ticket, expiry, invocation nonce or
budget, or expected input record/Profile identity. The adapter gates publish and
load only on `enabled` plus their feature flags. Consequently an enabled config
can be replayed directly, copied, cross-used with another command or raced after
a BVP precheck; the adapter cannot distinguish preactivation from steady state.

Production linkage therefore requires a separately owned canonical SKILL
config v2 or trusted broker/handle route. It must bind those coordinates and
atomically redeem a BVP-owned one-shot authority before exactly one command.
Direct CLI replay/copy/deserialization, wrong command, second/concurrent call,
expiry and crash restart fail closed. The disabled distribution config remains
v1. If the adapter is not corrected, the TASK-036 attempt is only a
BVP-internal synthetic Bridge probe and cannot mint real SKILL E2E for CA-C.

For steady state, `enabled` must equal the exact current TASK-061 activation
transaction/config-history projection. Missing, stale, future, replayed,
cross-instance, unbound or ambiguous history yields no config publication and no
committed projection.

Every config is bound to exactly one adapter operation. The closed minimum-
authority table is:

| Operation | `learning_publish_enabled` | `preference_read_enabled` |
|---|---:|---:|
| `CONNECTOR_STATUS` | `false` | `false` |
| `PUBLISH_LEARNING` | `true` | `false` |
| `LOAD_PROFILE` | `false` | `true` |

Canonical adapter `origin/main=c86ec8c11724a3170d37e0fdc5a516979fcca703`
confirms the semantic split: `publish_learning_export()` checks only
`enabled && learning_publish_enabled`, `load_preference_profile()` checks only
`enabled && preference_read_enabled`, and `connector_status()` reports the two
effective flags independently. This supports the least-privilege table as a
design mapping only; it does not satisfy the separate reader/writer safety or
release/install gates.

The PL-C runner must reject a config/receipt operation mismatch. Steady-state
does not imply that both feature flags are true; a new config projection and
receipt are required when the operation changes.

### 5.2 Projection receipt

`connector-runtime-config.receipt.json` is a self-hashed
`BvpMontageLearningRuntimeConfigProjectionReceipt` v1 closed object containing:

- `task_owner:TASK-065`, `projection_id`, `projection_revision`, exact
  `operation` and `previous_receipt_sha256`;
- TASK-063 `install_instance_id`, descriptor hash, owner-manifest hash, Bridge
  relative coordinate and private-root identity hash;
- **CURRENT FIELD-SET CORRECTION:** the BVP-private receipt/journal also binds
  `task063_current_installation_receipt_sha256`, Product build and payload-tree
  digests, registration-set and selected-registration receipt digests,
  lifecycle receipt digest, exact cardinality one and installation-reader
  currentness digest. These fields are not added to SKILL v1 config and only
  opaque hashes/cardinality may enter public Evidence. See
  `pl-a-pl-b-installation-binding-matrix-2026-08-31.md`;
- TASK-060 PP-C source read-back hash and promoted envelope hash;
- TASK-061 transaction hash, config-readback hash, history hash, revision,
  action and derived enabled value;
- config relative path, byte length, SHA-256 and physical identity;
- `default_config_used:false`, `fixed_programdata_fallback_used:false`,
  `explicit_config_required:true`, `require_admission_receipt:true`, and the
  exact operation-scoped publish/read flags;
- currentness expiry/revocation coordinates and the required BVP admission
  receipt/correlation policy;
- all learning adoption, automatic promotion, Timeline, Resolve, Release,
  Deploy and Production authority fields fixed false; and
- `projection_sha256`, computed over the canonical body without that field.

It contains no private absolute root, username, SID text, media, transcript,
credential, token or free-form Human rationale.

### 5.3 Immutable transition chain

Each file below `transitions/` is a durable self-hashed
`BvpMontageLearningRuntimeConfigProjectionTransition` v1 immutable generation.
Every transition binds the operation ID, unique phase coordinate, exact
predecessor transition/config/receipt identities, intended artifact hashes,
TASK-063/TASK-060/TASK-061 coordinates, expiry and currentness. PREPARED and
every successor are published no-replace, flushed and exactly read back. No
same-path phase update, mutable current pointer or replacement is permitted.

TASK-068 supplies only strict/pinned read, secure lock, immutable no-replace
publish and durability primitives. Its receipt fixes `authority_created:false`
and `currentness_selected:false`. It does not choose the terminal generation.
Recovery receives the exact generation and expected predecessor from a trusted
consumer plan/durable receipt; missing, multiple, stale, caller-selected,
foreign or mismatched coordinates stop with effect zero. Scanning transition
files for the highest/newest phase is prohibited.

### 5.4 Pre-activation prepare receipt

`preactivation-receipt.json` is a self-hashed
`BvpMontageLearningPreactivationConfigReceipt` v1 closed object. It binds the
exact TASK-061-A PREACTIVATION PREPARE receipt/Human challenge candidate,
`enabled:false` and apply-effect-zero state,
instance and source identities, operation, operation-scoped feature flags,
config hash, expected public-safe record identity, expiry, single invocation
budget, immutable retirement/tombstone identity, and authority fields fixed
false. It is not a
TASK-061-B final or Production Activation receipt and cannot advance BVP
steady-state projection.

Under current SKILL v1 this receipt is audit data only: the adapter does not
read, validate or consume it, so expiry and single-invocation budget are not
enforced. The TASK-036 preactivation operation remains N.C. until the D2S
operation-authority correction binds and atomically redeems this exact receipt/
ticket or replaces it with an equivalent trusted broker capability.

## 6. Writer, immutable transitions and publication

PL-B is the sole writer under `connector-runtime-config.lock`. The lock is
instance-scoped, regular-file-only, non-reparse, non-hardlinked and protected by
the admitted Bridge DACL. It is held across read, validation, publication and
read-back. Every allowed
writer must participate in this lock; unresolved or broad writable principals
fail closed.

Lock and operation namespace establishment are transaction steps:

- existing and initial lock paths use separate protocols beneath the pinned
  Bridge-state ancestor/DACL. Initial creation is `CREATE_NEW`/no-follow,
  one-byte, regular, single-link and non-reparse; locking is on that same
  physical handle. A race loser performs one fresh existing-object
  classification and never auto-retries;
- bounded ticket/operation/command IDs are contained joins. Each operation
  directory is created with new-object semantics and receives post-create
  handle/lstat identity plus DACL read-back. Only an exact prior-operation
  safe-empty namespace may resume; unknown/nonempty/reparse/case-colliding state
  stops without repair;
- transition `PREPARED` publication is no-replace. Every later phase uses a
  unique operation-bound immutable path and binds the expected predecessor
  opened bytes, identity and self-hash under the same lock, then requires
  prepublish currentness and pinned post-readback; no phase overwrites another;
- immutable invocation config and receipt artifacts are no-replace. Existing
  state is DUPLICATE only for the same operation/receipt chain with exact bytes
  and identity; any difference is collision/STOP;
- current selection is the exact plan-bound terminal transition/config/receipt
  tuple. Neither adapter nor BVP scans the directory, follows a mutable pointer,
  accepts a caller-selected generation or infers a winner from timestamps; and
- directory durability failure is FAIL with receipt zero. Windows uses an
  explicit native durability port/Evidence when directory fsync is unsupported;
  failure is never suppressed.

**Current-source P0:** this acceptance is not implemented by the present BVP
helpers. TASK-058 `_directory_fsync()` returns unconditionally on Windows, and
its platform-honesty fixture expressly accepts a missing directory without an
error. TASK-063 `_directory_fsync()` returns on directory-open failure and
suppresses `fsync` failure; its tests inject only `after_temp_fsync`, not a
directory durability failure. `MoveFileExW(...WRITE_THROUGH)` is rename-seam
precedent only and does not prove parent-directory creation or mkdir durability.
Until owner Tasks provide a Windows native durability port and durable receipt,
mkdir, owner/descriptor/readback, pending/receipt/Profile and PL-B config/
transition/tombstone commits remain `DURABILITY_UNOBSERVABLE / START0 / EFFECT0`. The current
Windows no-op test is historical regression input, never Production PASS.

Steady-state publication requires the current corrected immutable predecessor
tuple below.
The former instance/descriptor/owner/TASK-061-only tuple is SUPERSEDED because
it did not preserve installed Product, registration, lifecycle or reader
currentness:

```text
(task063_current_installation_receipt_sha256,
 install_instance_id,
 descriptor_sha256,
 owner_manifest_sha256,
 installed_product_build_sha256,
 installed_payload_tree_sha256,
 installer_registration_set_sha256,
 selected_registration_receipt_sha256,
 installation_lifecycle_receipt_sha256,
 installation_selection_cardinality,
 installation_reader_currentness_sha256,
 task061_revision,
 task061_history_sha256,
 task061_config_readback_sha256,
 previous_config_sha256,
 previous_receipt_sha256)
```

The writer reopens and revalidates the complete ancestor chain, DACL, file type,
link count, target identities and source receipts before and after each publish.
It first publishes/flushes/reads back the exact immutable PREPARED transition.
It then writes immutable operation config and receipt with operation-owned
exclusive handles, flushes file data and the containing directory, publishes
no-replace, and reopens by name for exact bytes/identity read-back. Every later
transition and terminal/tombstone artifact is another unique no-replace
generation. Expected-target replace and same-path mutable CAS are unavailable
and prohibited.

Atomic terminal-transition publication plus exact receipt/config read-back is
the sole commit point. A committed consumer accepts only the exact plan-bound
terminal generation whose config bytes and physical identity match its receipt.
Failure before commit preserves unfinished artifacts; it neither deletes nor
replaces them automatically. A later unique immutable tombstone may mark the
exact operation generation ineligible, but physical presence is non-authority
and retention/cleanup is a separate lifecycle Gate. Foreign replacement,
unknown child or cleanup-time swap is preserved and stops. Exact transition
recovery may roll forward only the plan-bound intended next generation; it never fabricates from
ambient files, changes TASK-061 history, edits SKILL distribution data, or
deletes learning inbox/receipts/Profile state. An unjournaled one-sided config,
receipt/config mismatch or unrecoverable journal remains effect zero.

Every consumer reopens receipt and config and revalidates the TASK-063/TASK-061
identities and operation immediately before launching the adapter. A prior
successful read-back or config existence is not permanent authority.
The trusted lock/plan/transition/config/receipt capability is the operation-bound
handle/snapshot, never a public path or self-hash. Its lease/state transition
continues through child launch, adapter pinned config read and result capture.
Each crash seam defines exact resume or revoke from that journal; a second
effect remains zero.

### 6.1 TASK-063 installed-coordinate Production-safety prerequisite

The canonical installer-relative corrections remain valid source progress, but
TASK-063 is not a Production-current coordinate provider until its descriptor,
owner, installer-readback publication and rollback physical races are closed.
Current descriptor/read paths do not bind no-follow opened bytes to identity;
descriptor and owner are read separately; provision/update and readback rewrite
fixed targets with generic create/replace primitives; fixed-path rollback may
restore predecessor bytes or unlink targets; directory-fsync failure may be
suppressed. These overwrite/restore/delete semantics are incompatible with the
TASK-068 `IMMUTABLE_ONLY_V1` primitive boundary and remain legacy-only.

The TASK-063 owner correction must:

- pin install-root through data, Bridge, descriptor, owner and migration
  ancestors and bind descriptor plus owner bytes/identities/currentness into one
  sealed discovery snapshot;
- use a secure existing/initial installer-operation lock and publish each
  operation/install-instance-bound descriptor and installer-readback generation
  no-replace, binding filename/body to instance, manifest digest and predecessor
  generation/hash, followed by pinned post-readback;
- make repair, upgrade, revoke and rollback append immutable generations while
  retaining predecessors; fixed-target overwrite/CAS, preimage restore and
  physical delete are zero;
- accept the exact current generation only from a trusted installer/launcher
  receipt. Mutable pointers, caller coordinates, timestamps, lexical/newest and
  scan-highest selection are prohibited;
- treat directory fsync failure as FAIL with receipt zero;
- replace the Windows no-op/suppressed helper with an explicit native durability
  port whose unsupported and failure states fail closed and are receipt-bound;
- preserve a published-but-unselected generation as a journal-bound orphan/
  tombstone; only the same operation may resume/revoke it, while unknown,
  collision and foreign state STOP and remain preserved; and
- retain temp/unselected artifacts as non-authoritative operation-bound state;
  automatic cleanup is zero under `EXACT_DELETE_UNAVAILABLE`, and any later
  lifecycle reclamation needs separate authority. Discovery receipts are built
  from the same opened exact selected descriptor/owner snapshots, never equal
  fields from separate reads.

Descriptor, owner manifest, installer/migration read-back and rollback preimage
also use one strict bounded UTF-8 parser over bytes obtained from the same
pinned nofollow handle. The snapshot binds raw bytes hash, canonical parsed
hash and physical identity. Nested duplicate keys, NaN/Infinity, BOM/trailing
data, invalid UTF-8/control or exceeded byte/depth/member/item/string ceilings
STOP and preserve the ambiguous document. Rollback never plain-parses or
republishes an ambiguous preimage; its predecessor canonical bytes and identity
are journal-bound.

Focused negatives cover concurrent first provision, descriptor stat/open and
post-read swaps, same bytes on a different inode, mixed descriptor/owner
generations, install/data ancestor swap, lock hardlink/reparse, temp-to-publish
swap, immutable-generation collision, publish-before-selector crash, stale/
forged/multiple/wrong-instance selector, directory-fsync failure, forbidden
fixed-target restore/delete, and failure at each descriptor/receipt generation
and selector seam. Assertions require predecessor A unchanged, successor B
exactly one or a preserved orphan, unrelated overwrite/delete zero, one exact
install instance, coherent selected descriptor/owner generation, receipt delta
zero-or-one, exact-instance-only repair and fixed-ProgramData fallback zero.
Add mkdir, owner, descriptor, installer-readback and rollback directory-
durability failures; each must yield receipt zero, preserve unknown state and
leave unrelated objects unchanged.

TASK-065 consumes only a new TASK-063 corrective completion receipt and freshly
provisioned installed Evidence. TASK-061/065/067 do not modify installer source.

### 6.2 TASK-060 promotion, cipher and TASK-058 Profile authority prerequisite

Current public `PromotedPreferenceSourceRead` and `ProfileSourceBinding` objects
use module-visible tokens plus computable hashes. Object-level
`verify_current()` repeats shape/hash validation but does not pin and reopen the
actual encrypted promotion source. A caller can therefore construct advisory-
looking source/binding data and reach the public prebuilt Profile publisher
without authoritative TASK-060 history/current-file readback. Although the
Profile remains advisory and cannot mutate Timeline automatically, corrupting
the Production current Profile changes downstream SKILL guidance and is an
independent P0.

TASK-060 promotion and rollback authority is independently open. The public
confirmation functions accept caller `human_confirmed:true`, caller-selected
ID/time and reconstructible self-hashed confirmation data without a trusted UI,
OS user/session event or durable one-shot issuance record. PP-B store load uses
path checks followed by an unpinned read; promotion/rollback uses the generic
create-capable lock and replace writer without expected physical-identity CAS.
Automation can therefore self-confirm, race or overwrite the store unless a
separate TASK-060 owner correction closes both Human authority and physical
publication.

Promotion/rollback `DUPLICATE` is also audit-only. Current source calls
`_duplicate()` immediately after loading the store and returns the current
history before `_check_cas()` and before candidate source/policy/confirmation
currentness verification. The positive fixture intentionally resubmits
`expected_revision=0` after revision 1 and accepts duplicate no-op; crash
recovery relies on the same path. This safely acknowledges only that the exact
historical event is already committed. It proves neither current store revision
nor current source, policy, native DPAPI backend/user or physical file identity,
and it cannot issue PP-C/Profile capability. Before any PP-C/Profile step, the
trusted Product operation must freshly pinned-read those current coordinates.
Exact duplicate with revoked/drifted source, policy drift, later promotion or
rollback, same bytes on a new inode, backend/user drift or stale expected
revision remains no-write audit Evidence but returns
`DUPLICATE_CURRENTNESS_UNPROVEN / PROFILE_CAPABILITY0`.

That correction issues a Product-owned random one-shot challenge bound to exact
candidate/history/action/owner scope, expected revision/head, rollback target,
expiry, install/Project/user/session and build identity. A trusted Human-visible
boundary alone returns the receipt. Apply revalidates the challenge, current
candidate/history and pinned store identity in one secure transaction, atomically
consumes it and burns the capability on entry/success/exception. Initial store
publication is no-replace; existing append/rollback uses expected opened bytes,
inode, revision and head CAS, an operation-owned fsynced temp, prepublish
currentness, directory durability and pinned post-readback. Unknown targets are
never restored/deleted and only an exact owned temp inode may be cleaned.

Production source composition must also fix
`WindowsDpapiPreferencePromotionCipher` internally. Caller cipher Protocol,
`cipher_suite`, path, coordinates or `coordinates_from_verified_history` output
is test data, not authority. Product registry/manifest/current-promotion receipt
selects the encrypted source; pinned ciphertext identity, document cipher suite,
promotion history, Owner scope and registry coordinate are verified in one
operation. DPAPI Current User is bound to the selected TASK-061/TASK-063 owner/
current-user attestation, and backend/build/entropy-domain/version remains fixed
through ordered Profile readback. Synthetic/custom cipher or same-suite fake is
non-Production only.

This is current positive test behavior, not a theoretical substitute path:
`test_montage_preference_source_integration.py` constructs
`PromotedPreferenceSource` with `SyntheticCipher`, calls
`ProfileSourceBinding.bound_verified_production()` and successfully publishes
through `publish_prebuilt_advisory_profile()`. The same suite proves some pinned
read path/link defenses, but its caller-mint rejection uses a fresh wrong token;
it does not turn the module-visible token, public factory or synthetic cipher
path into Production authority. CI PASS therefore preserves historical source
progress while leaving this D1 correction N.C.

Public source reads, bindings and receipts are evidence only with
`authority_created:false`. A trusted TASK-060/TASK-058 Product operation must
verify the encrypted source through one pinned opened snapshot, binding file
identity, current revision, history and exact envelope, then mint a private
single-use Production publish capability. Fixture/unbound public publication is
restricted to a non-Production layout. Production entry late-binds the actual
envelope against expected hash/source revision/Profile coordinates, burns the
capability IN_FLIGHT at entry and on every success/exception, and retains the
    operation binding through exact trusted Profile control-generation and
    payload readback. Fixed pointer/current/marker files are compatibility
    Evidence only. The File Bridge physical-race correction remains a
    prerequisite.

Module-token access, direct/copy/replace/deserialized source objects, valid-hash
forgery, same coordinates from a different source inode, close-then-swap,
arbitrary envelope matching a forged hash, fixture binding against Production,
    and double/concurrent/exception reuse all produce zero Profile payload/control-
    generation/current-view mutation. If same-process Python introspection is inside the
threat boundary, authority moves to a trusted process/OS-backed broker rather
than another module sentinel. This correction crosses released TASK-058 and
TASK-060 ownership and needs an exact owner/amendment allocation; TASK-061/065/
067 do not implement it.

Additional negatives cover direct boolean confirmation, new-ID/timestamp replay,
confirmation deserialization, wrong user/session, challenge copy/swap/link,
concurrent promote/rollback, lock link, store stat-open/post-read or pre/post
replace swap, same bytes on another inode, fsync/readback failure, exception
reuse, synthetic/custom/same-suite cipher, monkeypatched decrypt, caller
coordinates, ciphertext inode substitution, DPAPI scope drift, phase backend
switch and plaintext fixture at a Production path. Duplicate-specific cases add
revoked/drifted source, policy drift, advanced/rolled-back store, same bytes on
a new inode and DPAPI backend/user drift. Duplicate may remain a no-write audit
ack, but without a fresh exact Human/native-DPAPI/current-source/current-store
read-back, promotion/Profile capability and revision delta are zero and
unrelated overwrite/delete is zero.

Both the encrypted outer promotion document and decrypted plaintext history
must cross a strict bounded UTF-8 authority parser. One private snapshot binds
outer raw/canonical bytes and physical identity, ciphertext bytes/hash,
decrypted canonical bytes/hash, fixed native DPAPI backend/user/session and the
parsed revision/head/history. Production decrypt output flows directly to that
parser; a caller Mapping or separately parsed plaintext cannot create
authority. Duplicate cipher/revision/head/envelope/hash fields, non-finite
numbers, BOM/trailing/control/invalid UTF-8 and exceeded bounds preserve the
source/store and leave PP-B revision and Profile publication unchanged.

### 6.3 TASK-058 readiness baseline and TASK-061 consumer prerequisite

The current public readiness baseline is caller-asserted rather than executed
Evidence. `production_readiness_evidence()` constructs public
`ConnectorReadinessEvidence` directly from caller state strings and
`adapter_contract_e2e_pass`/`default_skill_config_unchanged` booleans. The
dataclass has no trusted issuance seal. TASK-061 `_validate_public_readiness()`
accepts exact type plus field equality, and its positive activation fixture
passes the good states and both booleans directly. No executed session, report
ID, adapter/package bytes, installed instance/config or Profile receipt is
required. Private V2 predicate hashes do not repair that authority boundary.

The TASK-058/TASK-061 cross-owner correction marks public v1/factory/V2/
self-hash documents as historical audit/display projections with
`authority_created:false`; none is a CA-B or Profile-write prerequisite. A
trusted Product reader instead publishes durable `TASK058_BASELINE_READBACK`
from pinned canonical release manifest, code, schema, tests and package hashes,
installed exact bytes and executed operation receipts. Runtime/E2E PASS binds
`executed:true`, operation ID, exact adapter build and config projection,
request/result digests, BVP receipt/correlation/Profile read-back, timestamp and
expiry. Disabled default is a separate predicate over canonical/installed exact
bytes and sentinel semantics, never a caller boolean.

TASK-061's trusted operation freshly reads that durable receipt and binds it to
the exact TASK-063 instance, TASK-060 source and operation plan. Synthetic
fixture, status-only, code presence or a public readiness document cannot be
promoted to real E2E. Direct dataclass/factory construction, caller passing good
states/true booleans, rehashed mapping, copy/deserialization/subclass, fixture
replay, missing executed/report identity, wrong build/config/instance,
status-only, stale/cross-build/cross-instance receipt and canonical/installed
byte drift all leave Profile mutation zero. TASK-065 consumes only the future
durable completion receipt and does not implement either owner correction.

### 6.4 CA-A directory commit and immutable phase-journal prerequisite

Current CA-A stores PREPARED, COPIED, SNAPSHOT_COMMITTED and READBACK_VERIFIED
successively in one fixed `<migration_id>.json` using the same-path writer. It
also builds a staging directory with a fixed `manifest.json` and commits the
whole directory through `os.replace(staging_root, snapshot_root)` after an
absence check. Existing recovery tests validate the legacy phase sequence and
tree exactness, but do not prove a directory rename-noreplace race closure or an
immutable phase-generation selector.

TASK-068 `IMMUTABLE_ONLY_V1` is a strict/pinned single-file primitive receipt.
It establishes neither `DIRECTORY_TREE_COMMIT_AUTHORITY` nor mutable phase
advance. Substituting only its writer makes COPIED and later fixed-journal writes
collide and cannot make the directory commit authoritative. TASK-061-A owns two
independent High corrective Gates:

- `A61A-IMMUTABLE-PHASE-JOURNAL`: publish PREPARED and each successor as an
  operation-bound immutable generation with predecessor hash and pinned durable
  readback. The exact phase coordinate comes only from the trusted operation
  plan/recovery receipt; caller selection, mutable pointer, timestamp/newest and
  scan-highest are zero.
- `A61A-DIRECTORY-NOREPLACE-COMMIT`: pin and verify the exact operation staging
  tree, then use a Windows native directory no-replace commit or publish an
  immutable container manifest binding every payload object coordinate. A
  single-file manifest without bound payload identities is insufficient.

A snapshot or phase generation published before its trusted selector transition
is preserved as an operation-bound orphan. Only that exact operation may resume
or revoke it. Identical/different/empty/nonempty target appearance, junction or
reparse, manifest/payload swap, phase-generation collision, crash at every
generation/transition/durability seam and concurrent publish all fail closed.
Foreign staging, snapshot and phase generations are preserved; overwrite and
delete are zero. Required assertions are legacy-source delta zero, snapshot
exact zero-or-one, monotonic phases, and unrelated overwrite/delete zero.

Until both canonical TASK-061-A receipts exist, D2, TASK-067, TASK-036 and
TASK-065 PL-C admission remain PASS0. A TASK-068 completion receipt alone is
explicitly ineligible.

### 6.5 CA-A migration terminal-readback authority prerequisite

`BridgeMigrationReadback` is a public dataclass guarded only by module-global
`_READBACK_SEAL`, caller-provided receipt/manifest hashes and a recomputable
self-hash. TASK-061 `_validate_migration_readback()` re-runs those object checks
and compares public target instance/descriptor/owner fields plus
`exact_snapshot_verified:true`; it does not independently pinned-read the CA-A
terminal journal or snapshot tree. The public object/receipt/hash/seal is
therefore audit Evidence with `authority_created:false`, independently of the
separate CA-A publication-race P0.

The TASK-061 trusted Product operation resolves migration ID from its exact
plan, then reads the terminal CA-A journal and snapshot manifest/tree beneath
the selected TASK-063 instance through pinned current handles. One private
single-use capability binds terminal phase/receipt, manifest/tree digests,
opened physical identities, source/target instance currentness, security
backend identity and operation plan. Entry is IN_FLIGHT; success and exception
burn it, and failure requires a fresh authoritative reread. CA-B/apply consumes
only that capability identity/currentness and may compare the public document
for display, never use it as effect authority.

Direct dataclass construction, module-sentinel access, copy/replace/pickle/
deserialization, recomputed hash, public discovery replay, absent or
PREPARED/COPIED/nonterminal journal, wrong/tampered snapshot, same bytes on a
different inode, cross-instance/revision, stale terminal receipt and double/
concurrent/exception reuse all leave Profile/config/history mutation zero.
TASK-065 consumes only the future canonical durable completion receipt and does
not modify CA-A or TASK-061 source.

### 6.6 CA-A/CA-B effect-entry authority prerequisite

`BridgeMigrationPlan.confirmation()` and
`ConnectorSourceBindingPlan.confirmation()` are deterministic values derivable
from public plans, and both public executors compare only the caller string to
that value. They are UI/display challenge text with `authority_created:false`,
not proof of an independent operation event.

Production CA-A and CA-B enter only through a trusted Product operation that
atomically consumes a durable action-specific one-shot ticket bound to the
selected TASK-063 instance, exact plan and source identity, expected target
state/revision, user/session/build, expiry and invocation budget. Migration and
Profile-binding tickets are different actions and cannot cross-use. Entry is
IN_FLIGHT; success and exception burn authority. Recovery requires a fresh
authoritative resolver and exact durable phase state. Public plan/executor APIs
remain test/audit-only or are unreachable from Product composition.

Direct `plan.confirmation()` use, copied/rehashed plan or module seal, serialized
ticket/direct public executor, cross-action or wrong instance/source/revision,
expiry/replay/concurrent/double invocation and exception reuse all leave
migration/Profile/config/history mutation zero. CA-C Human activation remains a
separate Gate; neither ticket authorizes enablement.

### 6.7 Post-061B Production Activation trusted clock and strict authority JSON prerequisite

This apply path is not TASK-061-B final CA-C; it remains behind the later
separate Production Activation Human Gate. Production CA-C apply accepts no
caller `now`, timestamp or clock
implementation. Challenge issue, Human receipt, apply entry, durable consume
and final read-back share a trusted Product/OS time domain whose implementation,
build and session are bound to the one-use capability. Persisted monotonic/boot/
session coordinates plus bounded UTC prevent wall-clock rollback, large forward
jump, suspend/resume, timezone changes or restart from extending expiry.
`occurred_at` is generated by the trusted apply event, never copied from a
caller. Test clocks remain isolated from Production composition.

CA-A journal/manifest/receipt, trusted CA-B durable reads and CA-C config/
history/challenge/consume use one strict bounded UTF-8 parser rejecting duplicate
keys at every nesting level, non-finite numbers, BOM/trailing/control/invalid
UTF-8, non-built-in values and exceeded bounds. Raw opened hash, canonical
parsed bytes/hash and physical identity form one snapshot; no reopen proves
equivalence. Parser failure is body-free effect zero and never repairs,
rewrites or deletes the ambiguous document.

Backdated/future time, issue/apply clock swap, rollback/restart/suspend expiry,
Production test clock, concurrent expiry-boundary consume, duplicate/equal or
different phase/revision/enabled/receipt/hash fields, NaN/Infinity, BOM/trailing,
deep/wide/huge/control input all leave migration/Profile/config/history mutation
zero and preserve unrelated files.

## 7. D2 to PL-C cycle closure

The current TASK-061 candidate cannot close the cycle through a trusted
authority boundary:

- its public `admit_adapter_e2e_observation` accepts only
  `synthetic_fixture:true` and explicitly rejects a real-installed observation;
- ACTIVATE requires `real_installed_verified:true`, but the public E2E dataclass
  and module-visible sentinel allow caller reconstruction, so a
  non-synthetic-looking object is forgery rather than real E2E Evidence; and
- the released SKILL performs no transport write or Profile load while its
  config is disabled.

TASK-065 must not patch TASK-061 or weaken those checks. TASK-061-A replaces
public-object authorization only for CA-A/B correction plus the sealed CA-C
plan/config candidate/challenge contract at `enabled:false`; it does not mint
real-E2E authority. Setting `synthetic_fixture:false`, recomputing hashes or
accessing module sentinels is explicitly ineligible. The only admissible
sequence is:

1. TASK-061-A emits the exact PREACTIVATION PREPARE receipt with apply/effect0.
2. TASK-067 completes its Generic facade using only that prepare receipt.
3. TASK-036 consumes TASK-061-A, TASK-063, SKILL-D2S-001 and TASK-067, opens
   immutable non-steady-state operation coordinates by explicit `--config`, and
   invokes adapter `publish-learning` exactly once. PENDING is valid and publish
   is never called again for confirmation.
4. TASK-036 invokes exact plan-bound `import_path` once, then pinned-reads and
   binds the strict public receipt, hidden Generic correlation, canonical state
   and Profile read-back. Adapter `canonical_store_written` remains audit data
   with `authority_created:false`.
5. TASK-036 binds adapter stage, BVP import, receipt, correlation and Profile as
   separate identities into the real-installed E2E receipt.
6. TASK-061-B consumes that exact receipt and closes final CA-C while retaining
   `enabled:false`; it does not execute Production Activation.
7. All completion receipts flow to TASK-065 PL-A/B/C/D. PL-B may derive an
   `enabled:true` steady-state projection only from a later, separate Production
   Activation Human-Gate receipt. Only PL65-C01b then uses a fresh immutable
   operation config; PL-D owns lifecycle closure.

The TASK-065 phase split is mandatory:

- `PL65-C01a PREACTIVATION CHAIN ADMISSION` performs pinned read/join of the
  already completed TASK-036 durable receipt, observed stage count 1, import
  count 1, strict public receipt, hidden correlation and Profile read-back.
  TASK-065 calls the adapter and TASK-036 zero times. The observed stage/import
  deltas belong to historical TASK-036 execution; TASK-065 local Project,
  Bridge, Profile, config and history deltas are all zero.
- `PL65-C01b STEADY-STATE/POST-ACTIVATION` remains `START0` under current
  authority. It becomes eligible only after a separate Production Activation
  Human receipt and with a new operation ID, new one-shot ticket and fresh
  immutable operation config. It never reuses a preactivation delivery,
  receipt, ticket or operation ID and never performs a confirmation second
  publish.
- `PL65-C02` rejects either phase's receipt as a substitute for the other and
  rejects receipt-only, status-only or adapter `canonical_store_written`
  evidence as authority.

The historical TASK-036 preactivation config candidates never replace shared projection state and are never
discoverable through the SKILL default. The future authorized runner must
expire them after one matching command by publishing an immutable operation-
bound terminal consume/tombstone. It does not auto-delete operation files;
physical remnants are non-authority and lifecycle retention is separate. Crash
recovery requires the exact plan-bound transition, ticket and identities rather
than scan-highest discovery. A missing, replayed, expired or mismatched ticket
leaves effect zero.

### 7.1 TASK-061-A prepare, TASK-036 E2E and TASK-061-B final prerequisites

TASK-067 consumes only TASK-061-A PREACTIVATION PREPARE. That receipt closes
CA-A/B corrections and binds the CA-C sealed operation plan, immutable config
candidate and Human challenge contract at `enabled:false`; it contains no real
E2E or final-CA-C claim. TASK-036 then consumes TASK-061-A, TASK-063,
SKILL-D2S-001 and TASK-067 to produce the public-safe real-installed E2E
receipt. TASK-061-B alone consumes that exact TASK-036 receipt to close final
CA-C. Production Activation remains a separate Human Gate.

TASK-065 never receives or
calls its private capability factory, calls a private constructor, obtains a
private seal, monkey-patches validation or converts its own hash record into
`InstalledAdapterE2EReadback`.

TASK-061-A focused acceptance proves item 1 below. TASK-036 real-installed E2E
and TASK-061-B final acceptance prove items 2-6 without feeding back into
TASK-067's start Gate. Together the trusted Product operations:

1. accepts one current, unexpired, one-shot operation plan bound to the exact
   install instance, descriptor/owner hashes, PP-C source, Human candidate and
   all three operation-specific config receipt hashes;
2. admits only the exact public-safe request/payload identity permitted by that
   plan; public-safe constrains privacy content while the corrected execution
   mode remains real-installed and operation-ticket-bound, not synthetic;
3. validates the SKILL public receipt as the exact closed seven-field v1 object
   with `ACCEPTED` or `DUPLICATE`, then validates the BVP generic correlation as
   a separate identity;
4. independently binds the Profile read-back to the exact PP-C source and
   requires `learning_adopted:false`, `profile_promoted:false` and
   `timeline_mutated:false`;
5. requires exact pre-activation config expiry/terminal-tombstone read-back before minting
   `real_installed_verified:true`; and
6. rejects missing/REJECTED/extra-field receipts, missing or mismatched
   correlation, request/instance/source/config/Profile drift, replay, expiry,
   terminal/tombstone failure and every private-constructor attempt.

The real-installed route cannot be a relaxation from
`synthetic_fixture:true` to false over caller-supplied connector/publish/Profile
digests. It accepts only the future typed TASK-036 packaged Product-operation
receipt and binds, in one sealed factory operation:

- exact install instance plus TASK-063 discovery, descriptor and owner-manifest
  digests;
- pre-activation runtime-config candidate digest and revision;
- TASK-061 operation plan and Human evidence;
- canonical TASK-067 facade completion identity;
- plan-bound record ID and learning digest;
- BVP canonical admission/public receipt status, record and digest, with hidden
  correlation/canonical proof separate from the public receipt;
- independently read Profile envelope/hash;
- executed-at/currentness/expiry; and
- `owner_private_data_used:false`, `secret_used:false`,
  `timeline_mutated:false`, `resolve_written:false`.

The resulting real E2E capability is private factory-only. A module token,
dataclass constructor, serialized JSON or raw hashes cannot mint it. Missing
TASK-067/TASK-036 completion, FAILED_CLOSED facade, DUPLICATE binding drift,
public receipt without hidden/canonical proof, stale/replayed/expired/multiple
identity or apply-time instance/config/Profile drift remains effect zero.
At TASK-061-B final closure, TASK-061 reopens the exact instance, config
candidate, E2E and Profile currentness while retaining `enabled:false`.
Production Activation later requires its own Human Gate and fresh currentness.
The TASK-061-A prepare, TASK-036 E2E, TASK-061-B final and any later TASK-065
steady-state/post-activation receipts are distinct phases and cannot substitute
for one another.

Missing TASK-061-A PREACTIVATION PREPARE blocks TASK-067 and every later phase.
Missing TASK-067 blocks TASK-036; missing TASK-036 real-installed E2E blocks
TASK-061-B; missing TASK-061-B final CA-C blocks TASK-065 PL-C/PL-D. No phase
may substitute a later receipt to satisfy an earlier Gate.

TASK-061-B final CA-C also requires a separately authorized P0
correction for its config lock and writer. The current create-capable generic
lock does not bind no-follow lstat/open/fstat/post identities, single-link and
reparse-safe ancestors; the generic atomic JSON writer uses `os.replace`
without binding the earlier CAS target identity to pre-publish state. Bytes
self-hash/history CAS and directory DACL attestation do not prevent a
non-cooperating lock/config substitution or undo an overwritten target.

The future TASK-061 owner must establish initial and existing activation locks
securely under pinned admitted Bridge-state ancestors, bind existing config
bytes and physical identity into the CAS snapshot, use an operation-owned
exclusive durable temp, revalidate the expected target identity/current bytes
immediately before an identity-aware publish, use no-replace for an absent
target, and reopen/read back the exact published identity. It must not delete
or clean up the config/lock target. If the shared atomic helper is outside
Allowed Files, TASK-061 needs a bounded local writer or an explicit cross-owner
correction rather than treating the helper as authority proof.

Negative tests cover lock symlink/reparse/hardlink and absent-to-appears race;
config swap after read/before publish, same bytes on a different inode,
ancestor or post-publish swap, writer DACL drift, and faults at temp fsync,
validation, prepublish, postpublish and readback. Assertions require unrelated
overwrite zero, exact history revision delta zero-or-one, no false enabled PASS,
and preserved one-shot Human-evidence identity semantics. TASK-065 consumes only
the eventual completion receipt and never changes TASK-061 or shared atomic
source.

CA-A legacy migration has a separate P0 over the same weak primitives. Its
journal phase writes and initial Manifest use replace-capable atomic JSON; its
staging-to-snapshot directory commit does not prove no-replace against a raced
target; and deterministic-temp cleanup can unlink an artifact not proven to be
created by the current operation. Final DACL/hash attestation cannot undo an
unrelated overwrite or deletion.

TASK-061-A migration prepare therefore requires a secure existing/initial
migration lock; each journal phase bound by expected previous phase, bytes and
physical identity CAS with PREPARED no-replace and post-publish pinned readback;
Manifest exclusive durable no-replace publication with pinned-identical-only
resume; no-replace snapshot directory commit with exact tree/Manifest/identity
readback before any identical-resume decision; and cleanup only of a CREATE_NEW
temp whose handle/name/identity belongs to this operation. Source, target and
security currentness are rechecked immediately around every commit. Crash
restart uses the same journal/plan identity and never repairs/deletes unknown
one-sided state.

Focused negatives include migration-lock link/race, journal phase swap,
identical/different Manifest target appearance, empty/nonempty/identical/
tampered snapshot target appearance, foreign temp, ancestor reparse, DACL drift
and a crash after each fsync, file publish and directory commit. The legacy
source remains preserved, unrelated migration overwrite/delete is zero,
snapshot commit is exact-once, receipt phases are monotonic and automatic old-
data deletion remains zero. TASK-067 consumes only the resulting TASK-061-A
PREACTIVATION PREPARE receipt and does not change migration source.

CA-C Human authority has a further independent P0. The current exported
`issue_human_activation_evidence` can mint sealed-looking evidence from a
predictable confirmation string while letting automation choose evidence ID and
times. Its module seal and self-hash prove object consistency, not a Human
event; changing ID/time can evade history-only replay checks. Opening the real
E2E gate without correcting this would let an automated caller activate.

The TASK-061 owner must replace Production minting with an operation-specific
cryptographically random challenge durably bound to install instance, source
binding, plan, requested action, expiry, current config revision and issuer/
build identity. A Human-visible trusted Product UI/installer boundary confirms
it and returns a one-shot receipt binding challenge, trusted process/user/
session event coordinate/currentness and exact body. Automation cannot select
action, time or evidence ID; raw strings, copied/deserialized objects, public
dataclass construction and module-private sentinels cannot create authority.

Apply revalidates challenge/receipt, config revision, source/discovery/security
and exact E2E in one transaction and atomically consumes the capability. Call
entry burns it; exception or mismatch is FAILED_CLOSED. Replay may return
DUPLICATE only for the exact already committed Human event; a changed body is a
collision. DEACTIVATE uses the same Human boundary when required; any separate
emergency fail-closed disable must be an explicitly allocated safety path and
cannot confer ACTIVATE authority. Public APIs expose request/prepare/status,
not an activation capability, private factory or caller-selected mode.

Negatives cover the predictable string, copied dataclass or sentinel access,
new-ID/timestamp replay, wrong OS user/session/process, challenge swap/hardlink/
reparse, expiry and stale config/source/instance/E2E, double/concurrent call,
exception then reuse, and serialized receipt forgery. Activation history/config
remain unchanged without the exact Human event, challenge consumption is
exactly once, unrelated files remain unchanged and public failure is body-free.

Real-installed E2E authority has its own independent P0. The current exported
`InstalledAdapterE2EReadback` dataclass can be constructed with the module-
visible `_ADAPTER_E2E_SEAL`; an external caller can set
`synthetic_fixture:false` and recompute the public body hash. Python underscore
names are not access control. The current apply checks exact type, body
consistency, instance/source binding and the derived real flag, not the actual
connector command, file identities, correlation or Profile evidence. Combined
with self-mintable Human evidence, the current candidate may admit ACTIVATE and
must not be classified as safe merely because its public factory rejects real
input.

The public E2E object is therefore data-only/test observation and cannot be an
ACTIVATE capability. A trusted TASK-036/TASK-061 Product-operation boundary must
execute the real installed command and verify pinned config/discovery/plan/
delivery, strict public receipt, Generic correlation and independent Profile
readback in the same operation, then mint a private one-use capability that
cannot be caller-constructed, copied, deserialized or recreated by module
attribute introspection. If an in-process Python caller is inside the adversary
boundary, use an explicit trusted process/OS-backed broker receipt rather than a
module sentinel. Apply consumes only exact capability identity plus current
operation bindings, never public hashes, booleans or dataclass type checks.
Entry transitions to IN_FLIGHT and both success and exception burn authority;
only a fresh trusted execution may mint another capability. Synthetic fixture
admission remains test-only and is a different Production input type.

Negatives cover direct construction, sentinel access, copy/replace/pickle/
deserialization, subclass/duck type, recreating synthetic as false, valid-hash
forgery, wrong operation/instance/source/Profile/correlation and double/
concurrent/exception reuse. Without the real command and exact readback,
capability count and activation config/history mutation are zero.

`ConnectorSourceBindingReadiness` has the same authority flaw: it is a public
dataclass whose module `_RESULT_SEAL` and computable body hash can be reproduced.
Shape/self-hash validation cannot prove actual CA-B plan execution, migration
receipt, promoted Preference source or Profile publication/readback. Therefore
the effect-bearing apply inputs—readiness, Human evidence and E2E readback—are
all audit evidence with `authority_created:false`; none is accepted directly as
authorization.

A trusted TASK-061/TASK-036 operation must pinned-read the durable CA-B/Profile
currentness, consume the exact Human challenge receipt, verify the real E2E
correlation/Profile evidence and bind them in one current operation before
minting the private one-use apply capability. Public readiness constructors,
module sentinels, copies and serialized objects cannot substitute. Without this
trusted composition, apply changes neither config nor history.

Production composition also fixes the native security backend internally.
Caller-selected `security_backend`, hooks or failure injectors remain test seams
only and cannot be selected through packaged argv, config, plan or serialized
receipt. The Production capability binds backend identity, build digest and
attestation implementation version. Fake/monkeypatched backends, hook-induced
file swaps and backend changes between prepare, apply and final readback all
fail effect zero. Public test APIs and the private Production operation type are
separate surfaces.

### 7.1a SKILL adapter Production-safety prerequisite

The released SKILL adapter remains valid historical TASK-058 release Evidence,
and its distribution default remains disabled. It is not, however, eligible as
the Production transport baseline while the canonical script uses
exists-then-read for config/delivery/receipt/Profile inputs and replace-capable
publication for a supposedly new-or-identical delivery. Those operations do not
pin full ancestors, no-follow opened-file identity, hardlink count, reparse
state or post-read/publish currentness, and raw errors/results may expose
absolute paths. A BVP-owned safe Bridge/config cannot close a race inside the
SKILL consumer.

The canonical AdmissionReceipt contract is also open where TASK-065 requires a
closed public receipt: `connector-file-bridge.schema.json` declares
`additionalProperties:true`, and `validate_admission_receipt()` checks required
fields and binding/status but never requires the exact field set. An
extra-field receipt can therefore pass the current SKILL even though it is
ineligible for PL-C/activation Evidence.

The same canonical adapter always calls `atomic_write_new_or_identical()` for
the original inbox delivery before reading a public receipt. Once Bridge claim
has moved that original into processing, a confirmation retry sees the inbox
path absent, recreates the delivery, and only then reports the terminal receipt.
Therefore adapter publish is an exact-one staging operation and PENDING is an
eligible intermediate result; PL-C must never call publish again to confirm
admission. `canonical_store_written` derives only from public receipt status and
has `authority_created:false` because it proves neither hidden correlation nor
current canonical state. Current publish output also exposes absolute delivery
and receipt paths and is ineligible as public Product Evidence.

Learning-export privacy is also not yet a Production proof. Current
`redact_sensitive()` keys off sensitive key-name substrings, while free-form
feedback reason, style Profile, actor role, context event/section/phrase/tags,
reason codes and broad IDs can carry a path, account/player name, email, token or
transcript-like body under a benign key. Provenance is recursively redacted
rather than built from a typed allowlist, and `safe_export:true` is fixed during
construction instead of earned by an independent validator.

The shared JSON and CLI I/O boundary is independently open. Plain `json.load`
does not reject duplicate keys or non-finite constants, and security-relevant
documents are not bound as one parsed-tree/canonical-bytes/physical-identity
snapshot. Caller-selected output paths may create parents and overwrite. A
Production runner therefore accepts only opaque plan/record identities, resolves
contained config/input/output coordinates internally and uses a body-free safe
stdout result or operation-owned private handle/pipe/temp. Direct legacy
`--output`, if retained, is isolated from Product composition.

BVP `main=35cdf1ad475633dcf035e0616e979b5a8fde0c88` already publishes exactly
the same seven v1 fields (`schema_version`, `message_type`, `record_id`,
`learning_sha256`, `status`, `receipt_id`, `timestamp`) and its
`_parse_skill_v1_receipt()` requires exact set equality. Closing the SKILL
schema/runtime validator therefore does not require a BVP public-receipt shape
change. The separate TASK-058 physical publication/readback correction remains
required and is not absorbed into this schema fix.

This is a separate SKILL-owner dependency. TASK-061/065/067 must not edit the
canonical or installed adapter. A future authorized canonical SKILL change must
provide:

- full-ancestor plus lstat/no-follow-open/fstat/bounded-read/post-identity reads
  for config, existing delivery, receipt and Profile, requiring regular,
  single-link, non-reparse files and closed JSON; AdmissionReceipt must set
  `additionalProperties:false` and runtime validation must enforce the exact
  v1 field set before status/binding can count;
- pinned identical existing delivery as ALREADY and different content as a
  collision;
- same-directory exclusive private temporary creation, write/file fsync,
  no-replace publication, exact owned-temp cleanup, directory durability and
  post-publish reopen/read-back. `os.replace` overwrite is prohibited; if the
  target races into existence, only a pinned identical reread may return
  ALREADY;
- private raw exceptions/absolute coordinates and Product-facing bounded reason
  codes plus opaque hashes only;
- either an exact record/digest/ticket-bound read-only terminal-status command
  that creates no delivery and validates a trusted BVP broker projection, or a
  publish duplicate preflight that returns no-delta only after the Product
  broker has proven terminal receipt plus correlation. Receipt-only state never
  creates canonical authority, and SKILL never parses or repairs BVP private
  claim/journal/pending state;
- a closed privacy schema per TASK-055, TASK-056 and generic contract profile:
  free-form Human rationale stays local and only controlled reason codes cross
  the boundary; style/actor/context/tags/reasons/IDs use bounded token/enum
  grammar and source identities are opaque projections; provenance is a typed
  allowlist; every string has byte/codepoint/control/path/URI/email/account/
  secret/transcript-like validation; depth/items/document bytes, NaN/Infinity
  and non-built-in JSON are bounded/rejected; `safe_export:true` is set only
  after an independent post-build validator whose report contains redacted
  field paths/reason codes/counts and no raw sample;
- strict UTF-8 JSON rejects duplicate keys, NaN/Infinity, BOM/trailing bytes,
  invalid controls and excessive bytes/depth/items. Config/delivery/receipt/
  Profile parsing returns one sealed result binding parsed tree, canonical bytes
  and pinned physical identity; the trusted operation verifies that exact digest
  against the projection receipt. Output never performs caller-directed parent
  creation/overwrite and any file publish uses no-replace or expected-identity
  CAS; public errors contain stable codes only; and
- an unchanged disabled distribution default while the Product runner requires
  the explicit exact `--config` path.

Canonical SKILL `origin/main=c86ec8c11724a3170d37e0fdc5a516979fcca703`
also still documents the historical fixed ProgramData root, changing the
top-level distribution config from disabled to enabled, and commands that may
omit `--config` as the activation procedure. The separate SKILL-owner change
must align `connector-ready-bridge.md`, the SKILL required workflow, interface/
contract references and tests, inventory and release Evidence with Option B:

- the canonical default is a distribution-only immutable disabled sentinel and
  must never be edited to `enabled:true`;
- Production connector operations consume a BVP-issued operation-specific
  runtime config only after current projection-receipt validation and always
  pass its exact explicit `--config` path;
- fixed ProgramData is never selected as an active Product-runner fallback;
- direct adapter invocation that omits `--config` may still reach only the
  disabled legacy-safe sentinel, while the Product runner independently rejects
  omission; and
- documentation/contract changes alone do not establish runtime PASS or
  activation.

Negative coverage includes existing symlink/reparse/hardlink, parent/ancestor
swap, identical and different target-appearance races, temp collision,
post-publish swap, config swap between BVP read-back and adapter read, receipt/
Profile link or race, AdmissionReceipt extra/unknown fields, and absolute-path
leakage. It also covers accepted-record rerun after claim, receipt-only forgery,
missing/wrong correlation, pending/processing rerun, concurrent second publish,
and confirms terminal rerun delivery delta zero with unrelated inbox unchanged.
Privacy/strict-I/O negatives include a path under `note`, transcript in reason,
email in phrase, player/token in tags, path in style object, UNC/URI in an ID,
benign-key secret, homoglyph path, unknown nesting, oversized/control text,
sibling-value leak, error echo, duplicate enabled/Bridge-root keys, non-finite
numbers, BOM/trailing/deep/huge JSON, config swap after BVP check and output
ancestor/foreign-target/hardlink/raw-absolute-path attacks. Sensitive raw bytes
remain absent from export/stdout/error/receipt/temp, rejected export never
reports privacy PASS, adapter parsed digest equals the projection digest, and
private local Evidence remains preserved. Every case is no-overwrite,
no-partial-effect and fail closed.

The required order is canonical SKILL Task/PR/main/release, installed-copy exact
sync/read-back, TASK-061-A prepare, TASK-067, TASK-036 real-installed E2E,
TASK-061-B final CA-C, then TASK-065 PL-A/B/C/D. Version, release and installation are separate Human/
Release Gates; BVP Task authority cannot create them. Until that chain completes,
Production linkage is `N.C.` even if the existing release remains historically
valid.

The currently available SKILL checkout is non-main and dirty; it is not an
authoring start point. Future implementation requires an exact owner/Task/
Allowed Files allocation and a fresh dedicated worktree from verified main.

### 7.1b TASK-058 File Bridge Production-safety prerequisite

Released TASK-058 Evidence remains historically valid, but its File Bridge is
not yet eligible for Production linkage. Its new-or-identical helper closes an
exclusive temp handle and later links by path without proving the temp path is
still the operation-owned inode; raced-target identical reads and general
    security reads are not one pinned lstat/no-follow-open/fstat/post-identity
    snapshot. Unconditional temp cleanup can unlink a foreign replacement. The same
    read helper serves owner Manifest, public receipt, Generic correlation, pending
    and Profile state. The content-addressed Profile payload path plus
    new-or-identical publication is a candidate immutable-payload PASS. It does
    not close transaction control: PREPARED through READBACK_VERIFIED rewrite one
    fixed Profile journal; pointer/current-view/marker are fixed mutable targets;
    terminal unlinks the journal; recovery treats journal absence and the fixed
    pointer as currentness. Import control has analogous mutable state. Pending
    cleanup rereads then unlinks by path without proving the same inode.

The BVP generic admission boundary has a separate privacy/resource P0. Its
current sensitive-value rejection is keyed mainly by field names and treats
caller `safe_export:true` as sufficient; benign `note`/reason/context/tag/
style/ID/provenance values can retain private data. It also computes canonical
learning hash before bounded schema/privacy validation, allowing a deep or wide
attacker tree to reach recursive canonicalization first.

The TASK-058 correction therefore performs, in order: (1) bounded strict JSON
decode/tree snapshot; (2) exact schema, type, collection and string ceilings;
(3) closed per-contract privacy projection and every-string value scan; (4)
canonical bytes/hash only for the accepted bounded projection; (5) semantic/
lineage validation; and (6) pending/canonical effect. Controlled reason codes
replace free-form public rationale; style/context/tags/roles/IDs use typed
bounded grammars. Path/email/account/secret/token/control/transcript and
normalization/homoglyph evasions are rejected. Unknown provenance is rejected
or replaced without raw bytes. `safe_export` is advisory only; BVP alone emits
privacy PASS. Stable body-free rejection precedes all pending/canonical/Profile
mutation and leaves no raw payload in temp/journal/receipt/stdout/log.

This needs a separate TASK-058-owner corrective Unit with exact paths/symbols
and any required cross-owner amendment. It is not part of the limited TASK-067
Generic-facade amendment, and TASK-061/065/067 must not change it. Required
correction includes:

- all security reads bound to one full-ancestor, lstat, no-follow-open, fstat,
  bounded-read, post-identity snapshot with regular/single-link/non-reparse and
  non-inheritable handle requirements; parse/hash/identity share that snapshot;
- immutable publish through an operation-owned exclusive open temp handle,
  fsync and retained identity, no-replace publication, pinned-identical-only
  raced duplicate handling, directory durability and post-publish pinned
  readback;
- immutable operation-bound journal generation per phase with predecessor hash,
  pinned readback and a trusted exact BVP plan/recovery coordinate; same-path
  phase CAS, timestamp/newest and scan-highest are zero;
- immutable Profile pointer-transition and marker generations bound to the
  exact payload and phase. The fixed current-profile v1 view, if retained, is a
  derived compatibility projection with `authority_created:false` and is never
  currentness authority;
- immutable terminal/tombstone generation instead of journal unlink. Resolver
  precedence is exact trusted terminal > exact trusted phase > fresh; physical
  old phases and payload-before-head orphan remain, while recovery after
  terminal is zero;
- pending/temp physical retention with operation-bound tombstones; automatic
  unlink/cleanup is zero under TASK-068 `EXACT_DELETE_UNAVAILABLE`, and foreign
  replacement cleanup is always zero; and
- stable body-free public errors/receipts with absolute path and OS detail
  leakage zero.

Focused negatives cover temp-close-to-link swap, identical/different target
appearance, hardlink/ancestor/reparse/stat-open/read-post swaps, every immutable
Profile phase-generation seam, pointer/marker generation collision, old pointer/
current-view replay, journal/tombstone mismatch, payload-before-head orphan,
terminal with physical journal retained, pending/temp retention and fsync faults.
Assertions require unrelated overwrite/delete zero, exact zero-or-one revision
transition, exact terminal recovery zero, all foreign state retained and trusted-
coordinate-only restart.

Privacy/resource negatives cover benign-key path/email/account/token/transcript,
style/ID/provenance leaks, homoglyph/normalization and sibling leakage, deep or
wide trees below the file-size cap, huge strings, recursion boundary, controls
and raw parser exceptions. Assertions require the process remains available,
stable body-free rejection, raw sensitive bytes zero across every artifact and
pending/canonical/Profile delta zero.

The completion order is TASK-058 corrective canonical main/release/install
exact read-back, TASK-063/TASK-065 baseline rebind where affected, TASK-061
pre-activation real E2E, then TASK-065 PL-C. Release/install remain separate
Gates and no existing TASK-058 release claim is retroactively invalidated.

### 7.2 TASK-058 Generic current-coordinate prerequisite

`Task036LaunchConfiguration` is a public coordinate input that can be loaded,
constructed or copied by a caller. Its exact Python type, Project ID, root or
matching caller-supplied hashes are not an authority seal and do not by
themselves close Project selection. The future TASK-036 private Product-
operation composition must bind the TASK-061 plan, TASK-063 installed-instance
discovery, exact record/delivery identity, pinned launch-config bytes and the
selected Project root/control/manifest/lock physical identities and currentness
before minting any private in-process bound-Project capability for TASK-067.
The Generic store ID is the Product constant
`task058-generic-review-observations`, and the formal review-only unbound Owner
scope is the zero digest. TASK-065 and TASK-036 must not replace these closed
coordinates with caller text.

The missing coordinate is the proposed TASK-067 public sealed read-only receipt
for the current Generic ledger revision, including the empty-store revision
zero case. TASK-067 is an unapproved follow-up candidate: this TASK-065 packet
does not allocate its source implementation. Only a later canonical metadata
allocation and implementation Gate may authorize it. The future owner must
bind the revision to the exact Project manifest/binding, Generic ledger head,
recovery/journal currentness and physical store identity.

The preferred contract is a sealed Generic-only facade/factory with a no-create
current-coordinate read and fixed Generic admission surface; exact APIs remain
private. It must not instantiate the current broad transaction constructor or
create Project authority directories merely to answer connector status/readback.
The current Generic readback has `anchor_coordinate:null`, so Bridge state must
not be repurposed as a shared dummy anchor across Projects. If the TASK-058
owner instead retains an external coordinate, its sealed receipt must separate
it by exact install instance plus Project digest, prove mutual non-containment
with the Project root, and keep exact methods inaccessible to the caller.

TASK-065 and TASK-036 must not call private `_generic_load_current_v1`, parse raw
ledger JSON, derive a revision from ambient files or accept revision/store/scope
coordinates from the CLI. The TASK-061 operation plan and TASK-036 packaged
entrypoint may consume only the exact current TASK-058 receipt. A stale CAS
fails effect zero and requires a fresh plan; it is never recalculated and
automatically retried.

Until TASK-067 allocation, implementation, independent DEV-4 acceptance and a
canonical focused-verification completion receipt are all current, the
dependency is `N.C.` and PL-C remains effect zero. An uncommitted local source
or test candidate is not a receipt and cannot satisfy this Gate.

### 7.3 TASK-036 packaged Product-operation prerequisite

`MontageLearningBridgeApplication` already owns exact `import_path` and
receipt/correlation publication semantics. TASK-036/Development 2 owns the
separately allocated bounded private entrypoint in the unified packaged EXE;
TASK-065 consumes only its completion receipt. TASK-036 must also consume the
TASK-067 Generic current-coordinate/facade receipt from section 7.2.

The TASK-036 entrypoint contract and focused verification must prove:

- `packaged_main` uses a closed exact private dispatch distinct from the
  installer dispatch and selects it before WebView2 probing, the Desktop
  `Task036SingleInstanceGuard`, `shell_main` or presenter construction. Mixed,
  duplicate or unknown arguments are rejected without a UI, shell or presenter
  fallback;
- the headless dispatch bypasses Desktop-only startup requirements, not Product
  authority: current TASK-063 installed-payload/instance discovery, the Bridge
  importer guard and the existing Project lock remain mandatory;
- it does not reuse `task036_native_image_vertical_cli` or
  `build_trusted_launch`. A Montage-specific composition constructs only the
  TASK-061 plan, TASK-063 discovery, pinned Project registry/manifest/lock
  read-back, TASK-067 sealed Generic facade and unmodified
  `MontageLearningBridgeApplication`; full Shell, DB, Ollama, Provider,
  bootstrap and native UI lifecycles have call count zero;
- public arguments contain only an opaque operation-plan identity and the exact
  record/delivery identity. Raw install/Bridge/Project roots, launch-config or
  Manifest hashes, expected revision, store/scope, mode, commit SHA and receipt
  output path are rejected;
- `Task036LaunchConfiguration` is at most a pinned coordinate candidate. The
  private resolver independently binds plan identity, config-byte identity,
  Project root/control/manifest/lock physical identities and current revision,
  record/source digest, and installer descriptor/owner/discovery currentness.
  A direct, `from_dict` or copied configuration, caller-matching hashes, a
  different physical Manifest with the same Project ID, root/Manifest/lock
  swap, hardlink or reparse target cannot mint authority;
- the resolver, not the caller, selects the sealed mode using matching
  correlation before pending-only recovery before an exact fresh plan;
- one explicit `import_path` for exactly one plan-bound Generic delivery in the
  exact installed instance and approved public-safe fixture; inbox-wide
  `import_once`, watcher, automatic import and implicit scan are prohibited and
  unrelated inbox entries remain unchanged;
- TASK-036 derives only the fixed original inbox filename from the plan-bound
  record ID and source digest through a contained join, then passes that Path to
  one `import_path` call. It does not pre-read JSON, scan the inbox, parse the
  private import journal, search processing, call `claim_delivery`, or reject
  original-file absence when an exact restart journal may own the processing
  claim. Directory listing is not an authority source;
- after unmodified Bridge claim, snapshot and lane validation, TASK-067 validates
  the actual delivery mapping exactly once at admit/recover entry and late-binds
  it to the ARMED capability. Plan record ID, source digest and canonical
  delivery hash mismatch burns the capability FAILED_CLOSED before canonical
  effect. PRECOMMIT_RESUME uses this same recover-entry snapshot;
  VERIFIED_READBACK binds Bridge-provided record/digest/commit to plan/
  correlation and
  requires no raw delivery pre-read;
- install root and Bridge instance come only from the exact current TASK-063
  discovery receipt;
- Project root is resolved by Project ID through the BVP canonical Project
  selection/registry and existing safe-root/ProjectManifest lock; raw Project
  path input is prohibited;
- the preferred Generic-only current-coordinate read is no-create and requires
  no anchor; if the TASK-058 owner retains an external coordinate, it is sealed,
  instance-plus-Project-digest separated, mutually non-containing with the
  Project root and never caller-supplied;
- `generic_store_id` is the Product-controlled constant
  `task058-generic-review-observations`; the unbound review-only
  `owner_scope_hash` is the formal zero digest;
- `expected_revision` comes only from the exact current public sealed TASK-058
  receipt while the owning locks are held, never from caller text, a private
  loader or raw ledger JSON;
- the request contains only the public-safe fixture identity and operation-plan
  ID; unknown, zero or multiple active Projects fail effect zero;
- the installed Product payload/EXE identity is exact and the private command is
  console-free; command presence, stdout or process exit zero alone is not
  PASS;
- request, strict public receipt, BVP correlation and Profile read-back remain
  separate identities, and the canonical store read-back, Project Manifest and
  ledger head are rechecked independently;
- only the generic review-observation lane is permitted; exact-evidence lane is
  rejected and learning adoption, Profile promotion and Timeline mutation stay
  false;
- retry is allowed only for the same plan/idempotency identity. A stale revision
  fails closed and requires a fresh plan; it is never recalculated and rerun
  automatically; and
- real Owner data, private factory bypass, Timeline/Resolve mutation, Release,
  Deploy and Production expansion remain prohibited.

Focused acceptance also proves that a failing WebView2 probe or held Desktop
single-instance guard does not prevent the dedicated Product-operation path,
while `shell_main` and presenter calls remain zero. Unknown, stale, tampered,
ambiguous or multiple plan/Project/delivery state returns a stable body-free
error with Project and Bridge effect zero; it never opens a popup or falls back
to the Desktop shell. A test that replaces only
`ProductProjectManifestStore.load` with a fake cannot establish PASS: the
pinned physical root/ancestor/Manifest/lock identity and currentness proof is
asserted independently.

The completion receipt requires invocation through the actual installed
packaged payload and exact read-back of the strict public receipt, separate
Generic correlation and Profile evidence, followed by TASK-061 sealed
admission. Source presence, a packaged command smoke test or mocked-only
composition is insufficient runtime Evidence.

If the required TASK-058 receipt or another canonical coordinate provider is
absent, that dependency is `N.C.` and must be assigned to its owner. The
packaged entrypoint must not replace it with CLI arguments.

Until the TASK-036 implementation plus focused-verification completion receipt
is current, PL-C classifies the transport as
`PRODUCT_IMPORT_ENTRYPOINT_MISSING / EFFECT0`.

### 7.4 Fixed Generic port, mode resolver and Bridge call sequence

The future TASK-067 facade is acceptable only when its public runtime surface
contains exactly these Generic methods and no exact-lane lookup/call surface:

1. `admit_generic_observation`;
2. `recover_generic_observation`; and
3. `get_verified_generic_observation`.

The sealed state machines must match the unmodified Bridge application rather
than a one-method approximation:

- `FRESH_READY -> admit(exact delivery) -> COMMITTED_RESULT_BOUND ->
  get_verified(same record/digest/commit) -> CLOSED`;
- `RECOVERY_READY -> recover(exact journal/terminal delivery) ->
  RECOVERED_RESULT_BOUND -> get_verified(same record/digest/commit) -> CLOSED`;
- `VERIFIED_READBACK_READY -> get_verified(exact correlation-bound
  coordinates) -> CLOSED`.

Closing immediately after admit/recover, get-before-result, mismatched get,
second admit/recover/get, use-after-close or mode switching after error is
ineligible. FRESH/RECOVERY immediate get returns the already bound typed result
with no additional filesystem effect. Restart VERIFIED_READBACK uses a
noncreating existing-lock A2 lookup; it must not call the create-capable writer
constructor or `exclusive_file_update_lock`.

RECOVERY has three sealed internal subtypes while preserving the single public
Bridge-compatible `recover_generic_observation` method:

1. Generic journal present and exactly plan/delivery-bound selects
   `JOURNAL_RECOVERY`;
2. journal absent plus an exact terminal committed entry selects
   `TERMINAL_A2_DUPLICATE`;
3. journal and terminal entry absent, with the canonical current coordinate
   exactly equal to the pending expected revision and plan-bound Manifest/head/
   store/scope, selects `PRECOMMIT_RESUME`.

`PRECOMMIT_RESUME` closes the crash after Bridge pending publication but before
canonical admit/journal creation. The outer unmodified Bridge still calls
`recover_generic_observation`; the sealed facade internally delegates the fixed
delivery once to the canonical admit path, using only pending + TASK-061 plan +
sealed TASK-067 current coordinates. Initial empty authority uses the secure
first-Generic-lock protocol. Its typed outcome is ACCEPTED, followed by the
normal same-bound-result verify, correlation/public receipt publication and
pending cleanup. Record collision, different digest, revision/head/Manifest
drift, ambiguity or unknown artifacts are STOP/effect zero. No CAS recompute,
fallback-to-fresh resolver or automatic retry is permitted.

The external mode resolver follows the real Bridge precedence exactly:

1. published receipt plus matching trusted correlation selects
   VERIFIED_READBACK; matching pending may coexist and the unmodified Bridge
   owns its cleanup;
2. published receipt without matching correlation is STOP/effect zero and must
   not be promoted to VERIFIED_READBACK;
3. no receipt plus matching correlation selects VERIFIED_READBACK;
4. correlation absent plus exact matching pending selects RECOVERY;
5. receipt, correlation and pending all absent plus an exact current fresh plan
   and delivery selects FRESH.

Multiple matches, tamper, foreign identity or any record/digest disagreement
remains STOP/effect zero. The file-Bridge published-receipt, pending and
correlation readers are state hints, not authorization proofs: their current
exists-then-read behavior does not independently pin lstat/open/fstat/reopen,
hardlink or ancestor identity. TASK-067 must separately prove Project canonical
authority/currentness; TASK-036/067 receive no authority to change those Bridge
helpers.

The resolver snapshot is sealed currentness input, not authority by itself.
TASK-036 must not acquire the create-capable Bridge publisher guard around a
nested `import_path`; that risks reentrancy/deadlock and changes the lock
contract. If Bridge state races after resolution and the unmodified Bridge calls
a port method inconsistent with the sealed facade mode, that facade burns to
FAILED_CLOSED and the operation stops. It does not retry or recalculate mode.
A retry resolves a fresh authoritative object, and a stale plan requires a
fresh plan. TASK-036 neither repairs nor cleans up a Bridge mutation already
started; the normal bounded recovery state remains for the next authorized
operation. Project inventory is asserted fully unchanged only across intervals
where no authorized Project mutation began.

### 7.5 Critical crash seams and status-layer Evidence

Focused integration must bind injections to these exact real call boundaries:

1. `S0a` — Bridge pending is durably published/read back and the process stops
   before the canonical call;
2. `S0b` — restart resolves RECOVERY and stops before facade recovery entry;
3. `S0c` — PRECOMMIT_RESUME stops immediately before or after secure initial
   Generic-lock establishment;
4. `S0d` — an unrelated canonical revision advances after pending publication;
5. `S0e` — the same record identity has a terminal different-digest collision;
6. `S1a` — Product commit immediately after the existing
   `failure_hook("after_generic_project_commit", generic_observation_path)`;
7. `S1b` — terminal readback verified immediately before cleanup at the
   existing `failure_hook("before_generic_journal_cleanup",
   generic_journal_path)`;
8. `S2` — Generic journal unlink succeeds but the canonical method has not
   returned. Main has no hook at this exact boundary; a future authorized
   TASK-067 change may add a production-default-effect-zero hook immediately
   after unlink within its Allowed source;
9. `S3` — canonical facade admit/recover returns but Bridge has not called
   `_trusted_generic_from_result`/`get_verified`. TASK-067 must not change
   Bridge source; use a test canonical-port wrapper or TASK-036 integration
   fixture that delegates, captures the typed result and then injects failure;
10. `S4` — facade `get_verified` returns but hidden correlation is not yet
   published, using an equivalent stateful test port wrapper; and
11. `S5` — hidden correlation is published but public receipt is not, at the
   existing Bridge `failure_hook("after_canonical_commit_before_receipt")`,
   plus the public-receipt-to-matching-pending-cleanup boundary.

S0a/S0b nominal restart uses PRECOMMIT_RESUME and makes exactly one canonical
commit with `ImportResult.status:ACCEPTED`, one matching correlation/public
receipt and pending removal. S0c re-enters only through secure safe-empty/lock
classification and still commits once. S0d/S0e remain effect zero, preserve the
pending record and unrelated Project/Bridge state, and require manual/fresh-plan
resolution. S0 is not covered by S1a-S5.

S1a and S1b use exact journal-bound recovery and permit only its authorized
Project delta. S2 through S4 require sealed A2 terminal recovery: no fresh
admission fallback, no raw ledger exposure, one
typed canonical result with `operation_outcome:DUPLICATE`, and the immediate
Bridge verify returns that same bound result. Restart must yield
`ImportResult.status:DUPLICATE`, one public-v1 receipt whose current contract
status remains `ACCEPTED`, unchanged
Project ledger/manifest revision, zero second Product commit and closed exact
pending state. S5 and receipt-to-cleanup restart must select VERIFIED_READBACK
when the matching correlation already exists.

Evidence keeps these layers separate instead of coercing them into one status:

| Layer | Required observation |
| --- | --- |
| canonical typed result | exact class plus `ACCEPTED` or terminal `DUPLICATE` |
| Bridge import | exact `ImportResult.status`, including `DUPLICATE` at seams 2-4 |
| public SKILL v1 receipt | exact seven fields and current v1 `status:ACCEPTED`; never coerce canonical/Bridge `DUPLICATE` into this layer |
| Product currentness | ledger/manifest revision and hashes before/after |

Inventory assertions are root-scoped. For direct facade readback/A2 duplicate,
the Project root is byte/inventory/revision unchanged and Bridge effect is N.A.
For unmodified Bridge restart, the Project canonical root remains unchanged,
while the Bridge root may add/read back only the exact namespace's hidden
correlation/public receipt and remove only its matching pending record.
Unrelated inbox entries, receipts, correlations, quarantine, config, state and
every other record/digest namespace remain unchanged; duplicate publication is
zero. Fresh admission and journal-bound recovery instead assert their exact
authorized Project path/revision delta separately from Bridge publication, with
unrelated delta zero and immediate-verify additional delta zero.

### 7.6 TASK-067 formal scope, security blockers and implementation-start Gate

TASK-067 now has an Owner-approved task-local formal scope for the Generic
Review Operation Facade. This supersedes the older `unallocated` wording, but
does not approve the preserved uncommitted candidate or authorize source/test
start, commit, push, PR or consumption. Allowed implementation paths are only
the Generic operation module, its focused TASK-067 test and TASK-067-local
docs. The released TASK-058 canonical-admission path is conditional on an exact
owner-preserving amendment limited to the private Generic factory, the three
Generic methods and directly required Generic manifest/journal snapshot
helpers. Exact lane, public receipt/Profile/Timeline/Release semantics, File
Bridge, activation, installation, TASK-036, SKILL, `atomic`, shared docs and
caller-selected mode/Project/root/revision authority remain prohibited.

Before any future implementation may become commit-ready, TASK-068, TASK-069,
the required TASK-060/063 receipts and TASK-061-A PREACTIVATION PREPARE,
canonical amendment and fresh overlap/work-lock PASS must all be current;
TASK-061-B is not a TASK-067 prerequisite. Independent DEV-4 review must close at
least:

- **P0 secure first Generic-lock establishment** — Product-lock-held absence
  checks must lead to no-follow exclusive creation, regular one-byte content,
  exact identity/read-back and pinned ancestors before switching to the normal
  Generic-lock then Product-lock order. The global create-capable atomic helper
  is not assumed sufficient. Broken link, reparse, hardlink, appeared-between-
  check, ancestor drift and case-collision all fail closed.
- **P0 terminal A2 same-snapshot proof** — journal absence, Product recovery
  none, exact ledger/manifest/binding/target marker, and exact object/marker
  inventories must be proven in one Generic-existing-lock then Product-lock
  snapshot. Capability body and cached typed result bind that same snapshot;
  Product journal appearance, orphan/unknown authority and ancestor swap fail.
- **P0 Manifest/journal same-snapshot physical proof** — parsed Manifest and
  Product-save-journal bytes, Project ID/hash/revision and reported physical
  identities must come from the same pinned no-follow opened-file snapshots
  under the existing Product lock. A later path probe,
  `ProductProjectManifestStore.load` alone or a monkeypatched loader is not
  authority proof. Hardlink/reparse, inode swap, post-read replacement,
  ancestor drift and the equivalent journal races fail effect zero in every
  facade mode; exact symbol scope must be named by the future TASK-058 cross-
  owner amendment or remain N.C.
- **P0 claimed-delivery restart late binding** — TASK-036 creates an ARMED
  capability from expected plan/record/digest identity without pre-reading the
  raw delivery. The unmodified Bridge may resume an already-renamed processing
  claim from the fixed original inbox Path; the facade validates and seals the
  actual Bridge mapping exactly once at method entry. Pre-read validation,
  inbox scan, private-journal parsing, processing search or a second claim is
  prohibited. Forged journal filenames, processing identity swaps and same-name
  different body/digest fail before canonical mutation.
- **P1 capability forgery resistance** — the production factory accepts only
  a private in-process bound-Project capability minted by the TASK-036
  packaged composition after fresh plan/instance/record/Manifest physical
  binding. Public `Task036LaunchConfiguration`, caller-visible module tokens,
  bound-project values, subclasses, mappings, duck-typed configs, serialized
  projections and rehashed JSON cannot construct authority. Tests must not
  obtain production authority through a module-private token shortcut.
- **P0 burn-after-call** — every admit/recover/get burns the capability into an
  in-flight state before validation or effects. Success alone reaches the next
  bound state; every exception reaches FAILED_CLOSED. FAILED_CLOSED, CLOSED and
  in-flight objects reject all methods before effect. State/result/commit/bound
  slots and factory/capability state resist normal or mangled assignment,
  subclass/duck type, serialization, copy and concurrent double-call. A fault
  after canonical commit cannot reuse the old FRESH object; restart obtains a
  newly resolved authoritative capability.
- **coverage floor** — the exact S0a-S0e plus S1a-S5 matrix, resolver
  precedence, root-split
  deltas, Windows reparse/hardlink, stale capability/races, mode misuse and the
  unmodified Bridge application sequences must pass.

Canonical metadata materialization, exact Allowed Files, clean worktree/current
main, dirty/overlap/work-lock/sole-writer PASS, accepted design, independent
Critic/Judge plan and explicit post-dependency implementation-start authority
are all required before source or test mutation may resume.

## 8. Lifecycle, privacy and multi-install rules

- Multiple valid/current install candidates are
  `MULTI_INSTALL_AMBIGUOUS / EFFECT0`; no registry order, newest timestamp,
  remembered Inno path or SKILL default selects a winner.
- Same-instance upgrade/repair re-derives the absolute Bridge root from fresh
  TASK-063 discovery and publishes a new config/receipt revision after
  validating the predecessor chain. It never trusts the prior absolute
  `bridge_root` merely because the old config exists.
- Normal uninstall does not invoke PL-B, delete the projection config/receipt,
  Bridge
  data, learning receipts or Profiles. Preserved state is not current authority
  after Product payload/currentness disappears.
- Reinstall/read-back may reuse preserved state only when TASK-063 proves exact
  same-instance continuity and TASK-061 history/receipt remains current; else it
  is stale and disabled.
- Cross-instance, stale descriptor, stale Product payload, zero/multiple current
  instances, config/history drift or missing exact plan-bound terminal
  generation produces no adapter launch
  and preserves all data.
- Public Evidence records only opaque IDs, hashes, revisions, relative paths and
  reason codes. Absolute roots, SID text, account names, private media and
  transcripts remain local and redacted.

## 9. Negative and boundary matrix

Focused tests must reject at least:

- omitted `--config`, distribution-default use and fixed ProgramData fallback;
- config extra/missing field, wrong version/type/profile or receipt policy;
- enabled value not equal to the bound TASK-061 steady-state receipt;
- missing/replayed/expired/cross-instance pre-activation ticket;
- preactivation enabled-config direct replay/copy, wrong or cross-command use,
  runner-precheck-to-adapter-open swap, receipt swap, cleanup-before/after retry,
  crash before consume/after consume/after adapter start, same-user direct CLI,
  and operation A/B startup race;
- initial lock race/link/reparse/hardlink, ticket-directory race/case collision,
  safe-empty versus unknown child, transition/config/receipt/tombstone target
  appearance or inode swap, same-path replace/CAS attempt, scan-highest/newest,
  unbound caller generation, foreign temp, auto-cleanup attempt, directory durability
  failure and concurrent operation A/B. Assertions require unrelated overwrite/
  delete zero, operation effect exact zero-or-one, one ticket to one command,
  coherent config/receipt and activation-history delta zero;
- second `publish-learning` used as admission confirmation, accepted terminal
  rerun that recreates the original inbox delivery, receipt-only canonical
  claim, missing/wrong correlation, retained processing claim or concurrent
  second publish;
- missing TASK-061-A PREACTIVATION PREPARE, TASK-036 real-installed E2E or
  TASK-061-B final CA-C receipt at its respective phase, any private
  `InstalledAdapterE2EReadback` constructor/seal attempt, or any public factory
  output used as Production authority (with or without cleanup read-back);
- caller-asserted TASK-058 readiness good-state strings/true booleans, direct
  readiness dataclass/factory/rehashed mapping/copy/deserialization/subclass,
  fixture/status-only replay, missing executed/report identity, wrong adapter
  build/config/instance, stale/cross-build/cross-instance baseline or canonical-
  installed byte drift;
- public CA-A `BridgeMigrationReadback` direct construction, module sentinel,
  copy/replace/pickle/deserialization/recomputed hash, public discovery replay,
  missing/nonterminal journal, tampered/same-bytes-new-inode snapshot, cross-
  instance/revision/stale receipt or capability double/concurrent/exception
  reuse;
- direct CA-A/CA-B `plan.confirmation()` execution, copied/rehashed plan,
  serialized/cross-action/wrong-instance/source/revision/expired ticket, direct
  public executor, concurrent/double/exception reuse;
- caller backdated/future `now`, clock rollback/swap, restart/suspend expiry
  extension, Production test clock, expiry-boundary concurrent consume, or any
  caller-authored history timestamp;
- duplicate equal/different nested authority keys, NaN/Infinity, BOM/trailing,
  deep/wide/huge/control/invalid UTF-8 in TASK-063 descriptor/rollback,
  TASK-060 encrypted/decrypted history, or TASK-061 CA-A/B/C durable state;
- BVP benign-key path/email/account/token/transcript/style/ID/provenance leak,
  homoglyph/sibling evasion, deep/wide/recursion/huge-string input, canonical
  hash before bounds/privacy, or raw error/artifact echo;
- missing TASK-067 Generic current-coordinate/facade completion receipt,
  private Generic-store loader use, raw-ledger parsing, missing
  recovery/journal/manifest/binding/head
  correlation, status/readback directory creation, shared Bridge-state dummy
  anchor, exposed exact API, Project/external-root containment, or
  caller-supplied revision;
- missing TASK-036 packaged-entrypoint completion receipt, caller-supplied
  Project/anchor paths, revision/store/scope coordinates, unknown/zero/multiple
  active Project, exact-evidence lane, stale-revision auto-retry,
  watcher/implicit scan, inbox-wide `import_once`, wrong installed payload
  identity, console exposure or exit-code-only success;
- Generic facade missing any fixed three-method port member, exposing an exact
  method, closing before the mandatory immediate get, get-before-result,
  mismatched/second call, use-after-close, error mode switching or use of the
  create-capable writer constructor/update lock for readback;
- resolver selection that ignores matching correlation precedence, selects
  pending over matching correlation, accepts receipt-only/tampered/ambiguous
  state or silently refreshes a stale plan;
- terminal A2 returning `ACCEPTED`, incrementing ledger/manifest revision,
  creating a second Project commit, publishing a second public receipt, leaving
  matching pending open, falling back to fresh admission or exposing raw
  lookup/storage internals;
- secure-first-lock race, broken link/reparse/hardlink/case collision, Product
  recovery appearing between phases, orphan/unknown object or marker, ancestor
  swap, caller-created seal/token/capability, subclass/mapping/duck-typed launch
  config, forged or rehashed serialized receipt and stale sealed object;
- TASK-036 preactivation candidate replacing shared projection state or reusing another
  operation's immutable config/receipt;
- zero or multiple current TASK-063 instances;
- descriptor/owner/PP-C/TASK-061/config receipt revision or digest drift;
- target/ancestor reparse, nonregular file, hardlink, broad/unresolved DACL or
  writable-principal drift;
- conflicting projection identity, unjournaled config/receipt one-sided state,
  receipt CAS loss, post-rename identity substitution and crash at every
  journal/config/receipt phase;
- `require_admission_receipt:false`, both operation flags true, wrong
  operation/flag combination, receipt missing or `REJECTED`, public receipt
  extra fields, or correlation/instance/source/config hash mismatch;
- upgrade without predecessor continuity, stale preserved state after uninstall,
  cross-instance reinstall and implicit winner selection; and
- public Evidence containing an absolute path, SID/account name, media,
  transcript, token or secret.

Positive tests remain synthetic and effect-bounded until the separate native
Gates open. Unexecuted adapter/native behavior is `NOT_CONFIRMED`, never PASS.

## 10. Re-entry and acceptance

Implementation remains START0 until all of the following are true:

- D0, D1 and D2 canonical completion receipts exist and are freshly read back;
- the cross-owner TASK-058/TASK-061 durable `TASK058_BASELINE_READBACK`
  correction is canonical and current, including exact release/package/
  installed bytes, executed receipts and the separate disabled-default
  predicate; no public v1/V2 readiness object is an admitting input;
- the CA-A/TASK-061 terminal-readback correction is canonical and current, and
  the private one-use capability binds the pinned terminal journal plus exact
  snapshot manifest/tree identities; public `BridgeMigrationReadback` is never
  an admitting input;
- CA-A and CA-B consume separate durable Product one-shot action tickets;
  deterministic confirmations and public executors remain audit/test-only;
- TASK-061 uses a trusted Product/OS time domain with Product-authored event
  timestamps and strict bounded same-snapshot authority JSON across CA-A/B/C;
- TASK-063 descriptor/owner/readback/rollback and TASK-060 encrypted/decrypted
  promotion source have canonical strict-parser completion receipts;
- TASK-061-A PREACTIVATION PREPARE is canonical at `enabled:false`, TASK-067 is
  completed from that receipt, TASK-036 alone publishes the public-safe exact
  request/BVP receipt/correlation/Profile real-installed E2E Evidence, and
  TASK-061-B consumes it to close final CA-C without Production Activation;
- the canonical SKILL operation-authority and publish-confirmation corrections
  plus strict JSON/closed Product I/O and the independent closed privacy-
  projection completion receipt are released, installed exactly, freshly read
  back and rebound by PL-A. A fixed `safe_export:true` flag is never a PASS
  input;
- the separate TASK-058 BVP admission correction validates bounded closed
  privacy before canonical hashing or pending/canonical/Profile effect, with no
  raw sensitive bytes in artifacts or public output;
- TASK-067's Owner-approved formal scope is materialized canonically without
  widening, TASK-068/TASK-069 and required TASK-060/063 plus TASK-061-A
  PREACTIVATION PREPARE receipts plus the
  exact TASK-058 amendment and fresh overlap/work-lock PASS have admitted its
  explicit implementation start, and its public sealed Generic current-
  coordinate/facade focused-verification completion receipt is canonical and
  current;
- the TASK-036/Development 2 bounded private packaged entrypoint and its focused-
  verification completion receipt are canonical and current;
- this correction receives required independent DEV-4 Critic/Judge acceptance;
- fresh main, exact Allowed Files, branch/worktree, dirty state, open-PR overlap
  and work-lock checks pass; and
- the separate config/native effects have explicit current Gates.

This packet changes design only. It does not claim implementation authority,
connector activation, adapter E2E, learning admission, runtime PASS, Release,
Deploy or Production.
