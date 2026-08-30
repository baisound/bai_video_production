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
`MontageLearningBridgeApplication.import_once/import_path`; the facade is
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

No current TASK-061 operation-plan/admission completion receipt means PL-B/PL-C
config, adapter and native effect zero.

### 7.2 TASK-058 Generic current-coordinate prerequisite

The trusted TASK-036 launch config already closes Project ID/root selection.
The Generic store ID is the Product constant
`task058-generic-review-observations`, and the formal review-only unbound Owner
scope is the zero digest. TASK-065 and TASK-036 must not replace these closed
coordinates with caller text.

The missing coordinate is a public sealed read-only TASK-058 receipt for the
current Generic ledger revision, including the empty-store revision zero case.
A separately authorized TASK-058 owner amendment or successor must bind that
revision to the exact Project manifest/binding, Generic ledger head,
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

Until the TASK-058 owner allocation and current-coordinate implementation plus
focused-verification completion receipt are canonical and current, the
dependency is `N.C.` and PL-C remains effect zero.

### 7.3 TASK-036 packaged Product-operation prerequisite

`MontageLearningBridgeApplication` already owns exact `import_once/import_path`
and receipt/correlation publication semantics. TASK-036/Development 2 owns the
separately allocated bounded private entrypoint in the unified packaged EXE;
TASK-065 consumes only its completion receipt. TASK-036 must also consume the
public sealed TASK-058 current-coordinate receipt from section 7.2.

The TASK-036 entrypoint contract and focused verification must prove:

- one explicit import-once for the exact installed instance and approved
  public-safe fixture, with no watcher, automatic import or implicit scan;
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
  console-free; process exit zero alone is not PASS;
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

If the required TASK-058 receipt or another canonical coordinate provider is
absent, that dependency is `N.C.` and must be assigned to its owner. The
packaged entrypoint must not replace it with CLI arguments.

Until the TASK-036 implementation plus focused-verification completion receipt
is current, PL-C classifies the transport as
`PRODUCT_IMPORT_ENTRYPOINT_MISSING / EFFECT0`.

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
- missing TASK-058 current-coordinate completion receipt, private Generic-store
  loader use, raw-ledger parsing, missing recovery/journal/manifest/binding/head
  correlation, status/readback directory creation, shared Bridge-state dummy
  anchor, exposed exact API, Project/external-root containment, or
  caller-supplied revision;
- missing TASK-036 packaged-entrypoint completion receipt, caller-supplied
  Project/anchor paths, revision/store/scope coordinates, unknown/zero/multiple
  active Project, exact-evidence lane, stale-revision auto-retry,
  watcher/implicit scan, wrong installed payload identity, console exposure or
  exit-code-only success;
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
- the separately authorized TASK-058 public sealed Generic current-coordinate
  receipt and focused-verification completion receipt are canonical and current;
- the TASK-036/Development 2 bounded private packaged entrypoint and its focused-
  verification completion receipt are canonical and current;
- this correction receives required independent DEV-4 Critic/Judge acceptance;
- fresh main, exact Allowed Files, branch/worktree, dirty state, open-PR overlap
  and work-lock checks pass; and
- the separate config/native effects have explicit current Gates.

This packet changes design only. It does not claim implementation authority,
connector activation, adapter E2E, learning admission, runtime PASS, Release,
Deploy or Production.
