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
|-- connector-runtime-config.transaction.json
|-- connector-runtime-config.json
|-- connector-runtime-config.receipt.json
`-- preactivation/
    `-- <e2e_ticket_id>/
        |-- connector-status/
        |   |-- connector-runtime-config.json
        |   `-- connector-runtime-config.receipt.json
        |-- publish-learning/
        |   |-- connector-runtime-config.json
        |   `-- connector-runtime-config.receipt.json
        `-- load-profile/
            |-- connector-runtime-config.json
            `-- connector-runtime-config.receipt.json
```

- `<bridge_root>` is derived only from the exact current TASK-063 discovery and
  is never read from the SKILL distribution default.
- `e2e_ticket_id` is supplied and sealed only by the separately authorized
  TASK-061 pre-activation E2E contract.
- `connector-runtime-config.json` is the exact steady-state adapter-facing
  filename. It is reprojected from fresh TASK-063 discovery after a portable
  move, repair or upgrade; its embedded absolute root is never reused as
  currentness evidence.
- PL-B0 never creates or replaces the steady-state config/receipt/transaction.
- The adapter receives only the absolute, reopened operation-specific config
  path via `--config`. It never receives the distribution config or an inferred
  default.

## 5. Adapter-facing config and BVP receipts

### 5.1 Adapter-facing config

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
accepts only its closed transport shape. BVP therefore binds the config through
a separate closed projection receipt. The absolute `bridge_root` is
private local state and must never appear in public Evidence, logs or exception
text.

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

### 5.3 Transaction journal

`connector-runtime-config.transaction.json` is a durable self-hashed
`BvpMontageLearningRuntimeConfigProjectionTransaction` v1 journal. It binds the
operation ID/phase, exact predecessor receipt/config identities, intended
config/receipt hashes, TASK-063/TASK-060/TASK-061 coordinates, expiry and
currentness. It is atomically published, flushed and exactly read back before
the steady-state config is changed. No missing, foreign, stale or mismatched
journal authorizes recovery.

### 5.4 Pre-activation receipt

`preactivation-receipt.json` is a self-hashed
`BvpMontageLearningPreactivationConfigReceipt` v1 closed object. It binds the
exact TASK-061 one-shot E2E ticket/Human candidate, apply-effect-zero state,
instance and source identities, operation, operation-scoped feature flags,
config hash, allowed synthetic record identity, expiry, single invocation
budget, cleanup receipt identity, and authority fields fixed false. It is not a
TASK-061 activation receipt and cannot update the steady-state config.

## 6. Writer, CAS and publication

PL-B is the sole writer under `connector-runtime-config.lock`. The lock is
instance-scoped, regular-file-only, non-reparse, non-hardlinked and protected by
the admitted Bridge DACL. It is held across read, validation, publication and
read-back. Every allowed
writer must participate in this lock; unresolved or broad writable principals
fail closed.

Steady-state publication requires an exact expected tuple:

```text
(install_instance_id,
 descriptor_sha256,
 owner_manifest_sha256,
 task061_revision,
 task061_history_sha256,
 task061_config_readback_sha256,
 previous_config_sha256,
 previous_receipt_sha256)
```

The writer reopens and revalidates the complete ancestor chain, DACL, file type,
link count, target identities and source receipts before and after each publish.
It first publishes/flushes/reads back the exact transaction journal. It then
writes the fixed config and receipt through same-directory `CREATE_NEW`
temporaries, flushes file data and the containing directory, atomically renames,
and reopens by name for exact bytes/identity read-back.

Atomic receipt publication plus exact read-back is the sole commit point after
config read-back. A committed consumer accepts only a config whose bytes and
physical identity match that receipt. Failure before commit may remove only
exact current-operation temporary/pending artifacts. Exact journal recovery may
roll forward only the bound intended operation; it never fabricates from
ambient files, changes TASK-061 history, edits SKILL distribution data, or
deletes learning inbox/receipts/Profile state. An unjournaled one-sided config,
receipt/config mismatch or unrecoverable journal remains effect zero.

Every consumer reopens receipt and config and revalidates the TASK-063/TASK-061
identities and operation immediately before launching the adapter. A prior
successful read-back or config existence is not permanent authority.

## 7. D2 to PL-C cycle closure

The current TASK-061 candidate cannot close the cycle:

- its public `admit_adapter_e2e_observation` accepts only
  `synthetic_fixture:true` and explicitly rejects a real-installed observation;
- ACTIVATE requires `real_installed_verified:true`; and
- the released SKILL performs no transport write or Profile load while its
  config is disabled.

TASK-065 must not patch TASK-061 or weaken those checks. A separately authorized
TASK-061 amendment or successor must define and seal a one-shot pre-activation
E2E ticket/Human candidate without applying activation. After that authority is
canonical, the only admissible sequence is:

1. CA-C prepares the exact Human one-shot candidate and E2E ticket with apply0.
2. PL-B0 creates three non-steady-state operation candidates beneath
   `preactivation/<ticket>/`, each explicit `--config` only and each carrying
   only the single operation's minimum feature flag.
3. PL-C0 executes `connector-status`, `publish-learning` and `load-profile`
   with their separately sealed configs against the exact real installed
   Bridge. It verifies request, strict BVP admission receipt and correlation,
   and Profile read-back as separate identities before returning a sealed
   receipt. It claims no Production activation.
4. CA-C consumes that exact receipt and applies activation/history under its own
   Gate.
5. PL-B publishes the steady-state config/receipt revision whose enabled value
   is derived from that current TASK-061 receipt.
6. PL-C reopens the steady-state pointer/config and performs the exact runtime
   read-back. PL-D then owns lifecycle closure.

The PL-B0 candidates never replace the steady-state config and are never
discoverable through the SKILL default. The future authorized runner must
expire them after one matching command and remove only their exact current-
operation files after cleanup read-back is sealed; crash recovery requires the
same ticket and identities. A missing, replayed, expired or mismatched ticket
leaves effect zero.

### 7.1 TASK-061 operation-plan/admission prerequisite

TASK-065 consumes only a public TASK-061 factory added by a separately
authorized source correction. It never calls a private constructor, obtains a
private seal, monkey-patches validation or converts its own hash record into
`InstalledAdapterE2EReadback`.

The TASK-061 completion receipt and focused acceptance tests must prove that the
public factory:

1. accepts one current, unexpired, one-shot operation plan bound to the exact
   install instance, descriptor/owner hashes, PP-C source, Human candidate and
   all three operation-specific config receipt hashes;
2. admits only the exact public-safe synthetic request identity permitted by
   that plan;
3. validates the SKILL public receipt as the exact closed seven-field v1 object
   with `ACCEPTED` or `DUPLICATE`, then validates the BVP generic correlation as
   a separate identity;
4. independently binds the Profile read-back to the exact PP-C source and
   requires `learning_adopted:false`, `profile_promoted:false` and
   `timeline_mutated:false`;
5. requires exact pre-activation config expiry/cleanup read-back before minting
   `real_installed_verified:true`; and
6. rejects missing/REJECTED/extra-field receipts, missing or mismatched
   correlation, request/instance/source/config/Profile drift, replay, expiry,
   cleanup failure and every private-constructor attempt.

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
Immediately before ACTIVATE, TASK-061 reopens the exact instance, config
candidate, E2E and Profile currentness. The pre-activation receipt and later
TASK-065 steady-state/post-activation receipt are distinct phases and cannot
substitute for one another.

No current TASK-061 operation-plan/admission completion receipt means PL-B/PL-C
config, adapter and native effect zero.

TASK-061 activation completion also requires a separately authorized P0
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

TASK-061 migration completion therefore requires a secure existing/initial
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
data deletion remains zero. TASK-065 consumes the TASK-061 completion receipt
only and does not change migration source.

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

This is a separate SKILL-owner dependency. TASK-061/065/067 must not edit the
canonical or installed adapter. A future authorized canonical SKILL change must
provide:

- full-ancestor plus lstat/no-follow-open/fstat/bounded-read/post-identity reads
  for config, existing delivery, receipt and Profile, requiring regular,
  single-link, non-reparse files and closed JSON;
- pinned identical existing delivery as ALREADY and different content as a
  collision;
- same-directory exclusive private temporary creation, write/file fsync,
  no-replace publication, exact owned-temp cleanup, directory durability and
  post-publish reopen/read-back. `os.replace` overwrite is prohibited; if the
  target races into existence, only a pinned identical reread may return
  ALREADY;
- private raw exceptions/absolute coordinates and Product-facing bounded reason
  codes plus opaque hashes only; and
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
Profile link or race, and absolute-path leakage. Every case is no-overwrite,
no-partial-effect and fail closed.

The required order is canonical SKILL Task/PR/main/release, installed-copy exact
sync/read-back, TASK-065 PL-A baseline hash rebind, TASK-061 pre-activation E2E,
then TASK-065 PL-C. Version, release and installation are separate Human/
Release Gates; BVP Task authority cannot create them. Until that chain completes,
Production linkage is `N.C.` even if the existing release remains historically
valid.

The currently available SKILL checkout is non-main and dirty; it is not an
authoring start point. Future implementation requires an exact owner/Task/
Allowed Files allocation and a fresh dedicated worktree from verified main.

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
`ImportResult.status:DUPLICATE`, one compatible public-v1 receipt, unchanged
Project ledger/manifest revision, zero second Product commit and closed exact
pending state. S5 and receipt-to-cleanup restart must select VERIFIED_READBACK
when the matching correlation already exists.

Evidence keeps these layers separate instead of coercing them into one status:

| Layer | Required observation |
| --- | --- |
| canonical typed result | exact class plus `ACCEPTED` or terminal `DUPLICATE` |
| Bridge import | exact `ImportResult.status`, including `DUPLICATE` at seams 2-4 |
| public SKILL v1 receipt | current contract-compatible public status and exact fields |
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

### 7.6 TASK-067 candidate security blockers and implementation-start Gate

TASK-067 remains design-only and unallocated. Its preserved uncommitted
candidate is not reviewed as completion and must not be committed, pushed,
tested further or consumed. Before any future implementation may become
commit-ready, independent DEV-4 review must close at least:

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

Canonical metadata allocation, exact Allowed Files, clean worktree/current
main, dirty/overlap/work-lock/sole-writer PASS, accepted design, independent
Critic/Judge plan and explicit implementation authority are all required before
source or test mutation may resume.

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
  instances, config/history drift or missing pointer produces no adapter launch
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
- missing TASK-061 operation-plan/admission completion receipt, private
  `InstalledAdapterE2EReadback` constructor/seal use, or factory output not
  bound to cleanup read-back;
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
- PL-B0 candidate replacing the steady-state config/receipt;
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
- the TASK-061 amendment/successor for the pre-activation E2E ticket is accepted
  and canonical, including a public factory that alone may admit exact
  request/BVP receipt/Profile read-back evidence as real installed E2E;
- TASK-067 has a canonical allocation and explicit implementation authority,
  and its public sealed Generic current-coordinate/facade focused-verification
  completion receipt is canonical and current;
- the TASK-036/Development 2 bounded private packaged entrypoint and its focused-
  verification completion receipt are canonical and current;
- this correction receives required independent DEV-4 Critic/Judge acceptance;
- fresh main, exact Allowed Files, branch/worktree, dirty state, open-PR overlap
  and work-lock checks pass; and
- the separate config/native effects have explicit current Gates.

This packet changes design only. It does not claim implementation authority,
connector activation, adapter E2E, learning admission, runtime PASS, Release,
Deploy or Production.
