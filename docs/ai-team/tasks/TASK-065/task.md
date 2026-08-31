# TASK-065 — Production Montage Learning Linkage Closure

- Status: `ALLOCATED / PRE_IMPLEMENTATION_DEPENDENCY_GATED`
- Capability: `BVP-PRODUCTION-MONTAGE-LEARNING-LINKAGE-001`
- Development profile: `DEV-4 FOUNDATION CRITICAL`
- Canonical audit base: `35cdf1ad475633dcf035e0616e979b5a8fde0c88`
- Owner request: establish the production SKILL-to-BVP linkage under the canonical rules without interrupting or reassigning the three active development lanes.
- Owner design correction: `2026-08-31` — Option B; the canonical and installed
  SKILL distribution config remains unchanged. Runtime selection uses only a
  BVP-owned, instance-bound config projection passed through explicit
  `--config`.

## Objective

Consume, without taking ownership from them:

- TASK-058 released SKILL interchange and Bridge transport;
- TASK-060 PP-C exact promoted advisory Preference source;
- TASK-061 CA-C Human activation/deactivation and config history;
- TASK-063 installer-selected-root-relative instance and discovery evidence.

TASK-065 closes production coordinate synchronization and real read-back/E2E.
It does not reimplement Timeline/Resolve ownership, learning admission,
Preference promotion, or connector activation authority.
It is integration-only: it consumes canonical completion receipts from
TASK-058/060/061/063/067, SKILL-D2S-001 and TASK-036 and does not amend those
owners' source to manufacture a missing receipt.
It does not edit or synchronize the canonical/installed SKILL distribution
config. The historical fixed-ProgramData default remains disabled and is never
an active production fallback.

## Dependency order

The one-way dependency graph is authoritative over older whole-task TASK-061
wording:

```text
TASK-068 -> {TASK-069, TASK-063}
TASK-063 -> TASK-060
{TASK-069, TASK-060, TASK-063, SKILL-D2S-001} -> TASK-061-A PREACTIVATION PREPARE (enabled:false)
TASK-061-A -> TASK-067
{TASK-061-A, TASK-063, SKILL-D2S-001, TASK-067} -> TASK-036 real installed E2E
TASK-036 -> TASK-061-B FINAL CA-C
all completion receipts -> TASK-065 PL-A/PL-B/PL-C/PL-D
```

TASK-061-A closes only CA-A/B corrections and the CA-C sealed operation plan,
config candidate and challenge contract at `enabled:false`. It does not claim
real installed E2E or final CA-C. TASK-061-B consumes the TASK-036 E2E receipt
and closes final CA-C contract/currentness while retaining `enabled:false`.
Production Activation execution and any `enabled:true` history/config mutation
are a separate Human Gate. Any older requirement for TASK-067 to wait for whole-task TASK-061
completion is SUPERSEDED.

1. `D0`: TASK-063 installer-relative source (`20f5360`), read-back boundary fix
   (`0b95e40`) and publication race/path-safety closure (`8fd17ed`) are
   canonical. D0 still requires fresh post-main hosted/Windows completion plus
   an exact re-provisioned installed read-back covering DACL, reparse, hardlink,
   descriptor, owner and discovery currentness. Older fixture/hash Evidence is
   not reusable as current PASS. Completion additionally requires pinned
   descriptor/owner discovery snapshots, secure provision/readback locking and
   identity-CAS/no-replace publication/rollback; current path-based replace and
   unlink behavior cannot prove race-safe installed currentness. Descriptor,
   owner manifest, installer/migration read-back and rollback preimages also
   require one strict bounded UTF-8 parser over the same pinned nofollow handle
   bytes, binding raw hash, canonical parsed hash and physical identity.
   Duplicate/nested keys, non-finite numbers, BOM/trailing/control/invalid UTF-8
   or exceeded bounds STOP and preserve the ambiguous current/preimage; repair,
   republish, delete and rollback mutation remain zero.
2. `D1`: TASK-060 PP-A is integrated from fresh `main`, then PP-B and PP-C are
   canonically completed and expose exactly one promoted envelope plus source
   receipt. Production Profile publication additionally requires a trusted
   pinned TASK-060 source-read operation and private one-use publish capability;
   public `PromotedPreferenceSourceRead`/`ProfileSourceBinding` tokens and hashes
   are advisory data, not write authority. D1 also requires a Product-owned
   random one-shot Human challenge for promotion/rollback instead of caller
   `human_confirmed`, IDs, timestamps or deserialized confirmations; and a
   secure pinned PP-B store transaction with initial no-replace, existing
   bytes+inode+revision/head CAS and exact read-back. Production composition
   fixes Windows DPAPI and registry/manifest coordinates internally; custom
   cipher/coordinates are test-only and cannot mint source authority. Both the
   encrypted outer store/source and decrypted history require strict bounded
   parsing from the same native operation snapshot, binding raw/canonical/
   ciphertext/decrypted hashes, physical identity, DPAPI backend/user/session
   and revision/head. Caller mappings or ambiguous JSON preserve state and
   produce zero promotion/Profile effect.
3. `D2A/D2B`: TASK-061-A first corrects its public-v1/private-v2 readiness dependency and
   supplies CA-A/CA-B plus a sealed CA-C prepare/Human one-shot candidate with
   apply effect zero. Its public factory output is audit projection only and
   has no real-installed E2E route, while its public E2E object is caller-
   forgeable; neither can serve as the trusted receipt required by ACTIVATE. A
   separately authorized TASK-061
   amendment or successor is required before the cycle below can execute.
   Completion also requires a secure activation-specific lock and
   identity-bound no-overwrite/expected-target config writer; the current
   generic create-capable lock plus
   `os.replace` writer cannot establish physical race safety. CA-A migration
   separately requires secure migration lock, identity-CAS journal phases,
   no-replace Manifest/snapshot publication and operation-owned-only temp
   cleanup before D2 may complete. Independently, public
   `BridgeMigrationReadback` plus module `_READBACK_SEAL` and recomputable hash
   is not CA-A execution authority; TASK-061 must pinned-read the exact terminal
   migration journal and snapshot manifest/tree into a private one-use
   currentness capability before CA-B/Profile effects. The public CA-A and CA-B
   `plan.confirmation()` strings are deterministic UI/challenge text only and
   create no authority. Each Production executor requires its own durable
   Product-issued one-shot operation ticket bound to action, exact TASK-063
   instance, plan/source/expected target revision, user/session/build, expiry
   and invocation budget; CA-A and CA-B tickets are never cross-usable and are
   burned IN_FLIGHT on success or exception. All CA-A journal/manifest/receipt,
   trusted CA-B durable reads, and CA-C config/history/challenge/consume reads
   also require strict bounded UTF-8 JSON with duplicate-key, non-finite-number,
   BOM/trailing/control rejection and a same-open-snapshot raw/canonical hash
   plus physical identity. Ambiguous authority files remain unchanged and
   produce effect zero. Human activation must be issued from a Product-owned
   trusted UI/process one-shot challenge; the
   current public predictable-string factory is self-mintable and cannot
   authorize ACTIVATE. Production apply accepts no caller `now`, timestamp or
   clock implementation: issue, Human receipt, apply, durable consume and final
   read-back share one trusted Product/OS time domain, with restart/suspend/
   rollback/skew unable to extend expiry, and history timestamps are Product-
   authored. Those corrections and the sealed `enabled:false` plan/config/
   challenge contract form the PREACTIVATION PREPARE receipt consumed by
   TASK-067; real installed E2E and final CA-C are expressly excluded. After
   TASK-067 and TASK-036 complete, TASK-061-B consumes the exact TASK-036 E2E
   receipt and closes final CA-C contract/currentness under the trusted clock
   rules without executing Production Activation.
   Independently, public `InstalledAdapterE2EReadback` plus a module-visible
   sentinel is forgeable; ACTIVATE must consume a non-caller-constructible,
   one-use trusted Product-operation capability instead of public hashes/flags.
   The same applies to public CA-B readiness: readiness, Human and E2E objects
   are audit data only, while a trusted native-backend-fixed operation binds all
   three into the private apply capability. TASK-058 public readiness is also
   caller-asserted: its factory accepts state strings plus E2E/default-config
   booleans and TASK-061 currently validates only the resulting field values.
   It cannot be a CA-B/Profile-write prerequisite. A cross-owner correction
   must replace it with a durable `TASK058_BASELINE_READBACK` pinned by a trusted
   Product reader to exact release/package/installed bytes and executed
   operation receipts; public v1/V2 readiness remains display-only Evidence.
4. `D2S`: the released SKILL adapter remains valid historical TASK-058 release
   Evidence, but its current transport writer/config/receipt/Profile readers do
   not meet Production race, physical-identity and privacy requirements, and
   its AdmissionReceipt schema/runtime validator still accepts extra fields
   that PL-C must reject. Independently, its closed config v1 has no operation,
   ticket, projection-receipt, expiry, nonce, invocation-budget or TASK-063
   instance binding, and the adapter does not atomically redeem any BVP one-shot
   authority. An `enabled:true` pre-activation config is therefore
   indistinguishable from reusable steady-state authority to the current
   adapter and cannot produce a TASK-036 real-installed E2E receipt. Its current
   `publish-learning` also stages the delivery before reading a public receipt;
   a confirmation retry after Bridge claim can recreate the original inbox
   delivery. Adapter `canonical_store_written` is receipt-status data only, not
   hidden-correlation or canonical-currentness authority. Its learning-export
   privacy flag is likewise self-asserted after key-name-based redaction;
   free-form benign-key/ID/reason/style/context values can retain paths,
   accounts, tokens or transcript-like text. Production linkage requires an
   independent closed post-build privacy validator and bounded typed projection.
   Production linkage therefore requires a separately owned canonical SKILL
   correction, PR/main/release and installed-copy exact sync/read-back, followed
   by a PL-A baseline hash rebind. The same correction must replace obsolete
   fixed-ProgramData/default-config activation instructions with the Option B
   explicit runtime-config route while keeping the distribution default an
   immutable disabled sentinel. TASK-061/065/067 cannot modify SKILL source.
5. `D2F`: released TASK-058 File Bridge Evidence also remains historically
   valid, but Production linkage requires a separately owned TASK-058 corrective
   Unit for pinned reads, immutable/mutable publication identity, ordered
   Profile publication and identity-safe pending/temp cleanup. Independently,
   BVP admission must replace key-name-only filtering and caller
   `safe_export:true` with its own closed per-contract privacy validator over
   every bounded string/value before pending/canonical/Profile mutation. Raw
   sensitive content is never written to temp/journal/receipt/log output, and
   only the BVP validator may create privacy PASS. The limited
   TASK-067 amendment does not include this work; TASK-061/065/067 cannot make
   the correction directly.
6. `D2C`: Owner-approved task-local formalization now bounds TASK-067 to the
   Generic Review Operation Facade, but does not approve its preserved diff or
   authorize source/test start. The future receipt binds the Generic store
   revision to Project manifest/binding, ledger head and recovery/journal
   currentness with no-create/read-only semantics and exposes only the fixed
   three-method Generic surface. Source START remains zero until TASK-068,
   TASK-069, required TASK-060/063 plus TASK-061-A PREACTIVATION PREPARE
   receipts, the exact TASK-058 cross-owner amendment and fresh overlap/work-
   lock PASS are all current. TASK-061-B is not a TASK-067 prerequisite.
   TASK-065 grants
   no implementation authority and consumes only the eventual canonical
   completion receipt; until then this dependency is `N.C. / EFFECT0`.
7. `D2P`: TASK-036/Development 2 supplies a bounded private Product-operation
   entrypoint in the unified packaged EXE plus its focused-verification
   completion receipt. It consumes D2C and does not inspect TASK-058 private
   storage helpers or raw ledger JSON. The entrypoint is a closed headless
   dispatch before Desktop WebView2/single-instance/Shell setup, accepts only
   opaque plan plus exact record/delivery identity, uses a Montage-specific
   minimal composition rather than `build_trusted_launch`, resolves Project and
   mode from fresh sealed authority, derives only the fixed original inbox Path
   and invokes one exact `import_path`. It never pre-reads/scans/claims the
   delivery; TASK-067 late-binds the actual Bridge-validated mapping at method
   entry so claimed-delivery restart remains possible.
   `Task036LaunchConfiguration` remains coordinate data, not authority.
   The current distribution chain is
   `task036_shell.spec -> task036_windows_entry.py -> packaged_main()` and the
   spec is one-dir with `console=False`. Existing tests prove that static chain,
   spec reuse and output name only. They do not prove Montage route/module
   inclusion in the frozen payload or real installed execution. The future
   completion therefore also binds T36-P01-P14: internally resolved exact
   installed `BAI Video Production.exe`, frozen build/payload-tree identity,
   private dispatch exact1 before probe/guard/shell/presenter (each call0),
   installer/discover call0 and a durable body-free receipt. stdout and exit0
   remain authority zero. TASK-063's installer already launches and waits for
   an installed private EXE command, but its post-call check is only exit0,
   receipt `FileExists` and ancestor equality. That existence-only precedent
   is not D0/PL-A/TASK-036 Evidence; neither TASK-063 nor TASK-036 may claim
   PASS without strict same-open receipt content plus physical/current identity
   and the operation-specific downstream read-backs.
   Its `installer_manifest_sha256` is likewise a build-input payload claim, not
   installed-byte proof: the current acceptance script does not rehash installed
   Product files or compare build/descriptor/current payload, parses JSON
   permissively and emits absolute roots. That PASS/console JSON is authority0
   and cannot feed PL-A/B/C.
8. `D3`: the older inline cycle shown as CA-C prepare -> PL-B0/PL-C0 -> CA-C
   apply is SUPERSEDED. The canonical graph above completes TASK-061-A,
   TASK-067, TASK-036 real E2E and TASK-061-B before TASK-065 begins PL-A/B/C/D.

**SUPERSEDED phase labels:** earlier text used `PL-B0`/`PL-C0` for the
pre-activation operation. Under the corrected one-way graph that operation is
owned and completed by TASK-036 after TASK-061-A and TASK-067. It is public-safe
(no private Owner data), operation-ticket-bound, real-installed execution and
read-back against the exact instance; `public-safe` describes payload privacy,
not a synthetic execution mode. Current SKILL config v1 cannot enforce that
boundary, so without canonical SKILL v2/trusted-broker correction the only
available probe is BVP-internal synthetic audit Evidence and is ineligible.
TASK-065 PL-A/B/C/D begin only after TASK-061-B and all other completion
receipts are current. None of these phases is Production Activation.
TASK-061-B consumes only the TASK-036 E2E receipt and retains `enabled:false`;
activation/history mutation requires the later separate Human Gate. TASK-065
never changes TASK-061 or SKILL source or mints Human authority.

TASK-059 signing is `NOT_REQUIRED` under the current contract. A future
explicit Release/Pack signing requirement is a separate Gate.

## Atomic Units

### PL-A — production linkage admission/projection

Pure, public-safe, effect-zero validation of the exact TASK-058, TASK-060,
TASK-061, and TASK-063 inputs. Missing, stale, tampered, ambiguous,
multi-instance, unknown-version, unknown-authority, or fixed-ProgramData
coordinates remain disabled and authorize no later effect.

Public discovery/descriptor hashes are necessary audit coordinates, not
current installed Product proof. PL-A also requires a private same-open
descriptor/owner snapshot, verified Product EXE/payload, a trusted
zero/one/multiple registration set, lifecycle continuity and matching
TASK-061 config/history. Packaged `discover` is effectful and its PL-A call
count is zero; root scanning and implicit winners are prohibited. Descriptor-
absent owner-only or owner-plus-receipt state is orphan/ambiguous, not fresh or
current, and may not authorize automatic instance reuse or path-only cleanup.
Fresh rollback can durably leave precisely this `PARTIAL_OWNER_PRESERVED` state
because Bridge directories/owner precede descriptor/receipt publication.
The current field/result/PLA-I01-I18 contract is in
[`pl-a-current-installation-field-delta-2026-08-31.md`](pl-a-current-installation-field-delta-2026-08-31.md).
`CANDIDATE_CURRENT_INSTANCE` is not `READY_FOR_CONFIG_SYNC`; PL-A remains
`START0 / EFFECT0` until every independent receipt is current.

### PL-B — BVP-owned instance-bound runtime config projection

Eligible only after current PL-A PASS and a separate Human/config Gate. It may
publish only a revisioned BVP-owned runtime config projection beneath the exact
TASK-063 installer-relative Bridge state. It binds the exact install instance,
descriptor/owner identities and current TASK-061 config/history receipt. The
adapter is always invoked with the exact read-back operation config path through
`--config`; default discovery and fixed-ProgramData fallback are forbidden.

PL-B source/start also remains zero until the canonical TASK-068 completion
receipt closes temp-handle loss, non-atomic expected-state CAS, path-only unlink
race, Windows ancestor share-delete, lock durability and mutable/unpinned
snapshot P0s. A partial TASK-068 implementation or public hash/status cannot be
promoted into this Gate.

Current TASK-058 Windows directory durability is an unconditional no-op and its
test accepts missing-directory success; TASK-063 suppresses directory-open/
`fsync` failure. These are historical platform behavior, not Production proof.
PL-B/D require an owner-provided Windows native durability port and receipts for
mkdir, owner/descriptor/readback, pending/receipt/Profile and config/journal/
pointer commits. Unsupported/failure is `RECEIPT0 / EFFECT0`.

Steady-state `enabled` is derived only from a separate current Production
Activation receipt/history created after its Human Gate; TASK-061-B final CA-C
alone retains `enabled:false`. PL-B cannot edit that history, mint Human
evidence, or infer enabled state. The preceding TASK-036 pre-activation
operation consumes TASK-061-A PREACTIVATION PREPARE plus the D2S adapter-side
one-shot redemption contract and never publishes a steady-state runtime config.
Each invocation uses an immutable,
noreplace operation-specific config/receipt coordinate; a mutable current
pointer, if needed, is BVP-only and never adapter authority. Every
pre-activation and steady-state runtime config fixes
`require_admission_receipt:true`; publish/read feature flags are operation-
scoped minimum authority and are never assumed both true. Feature flags alone
never prove operation authority.

PL-B propagates the same PL-A installation generation through its private
receipt, journal, publication CAS, operation ticket and launch-time reread.
Product build/payload, trusted registration set/selection, lifecycle and
reader-currentness fields remain outside SKILL v1 config and are bound only by
the future trusted broker/config-v2 route. The exact field/CAS tuple and
PLB-I01-I17 cases are in
[`pl-a-pl-b-installation-binding-matrix-2026-08-31.md`](pl-a-pl-b-installation-binding-matrix-2026-08-31.md).

### PL-C — post-completion connector E2E/read-back

The prerequisite TASK-036 pre-activation real-installed E2E has already staged
the exact delivery once, invoked exact `import_path` once and pinned-read the
strict public receipt, hidden Generic correlation, canonical state and Profile
read-back before TASK-061-B final CA-C. It never calls `publish-learning` again
for confirmation and never treats adapter `canonical_store_written` as
authority. TASK-065 PL-C does not recreate or substitute that receipt.

For this preactivation chain, TASK-065 performs admission only: it pinned-reads
and joins both the canonical TASK-036 T36-A/B/S/M/R/P/E producer completion and
the canonical TASK-061-B A61-E/R/D/Z consumer completion with observed historical
stage-count 1, import-count 1, strict public receipt, hidden correlation and
Profile read-back. Those counts describe the already-completed TASK-036
operation, not a TASK-065 local delta; TASK-065 calls neither the adapter nor
TASK-036 and its Project/Bridge/Profile/config/history delta is zero.

The exact producer/consumer admission cells and non-substitution rules are in
`task036-task061b-producer-consumer-admission-2026-08-31.md`. TASK-036 durable
receipt alone, public readiness/Human/E2E/transaction objects, self-hash/module
seal, exit zero, status, `canonical_store_written` or synthetic fixtures are
authority zero. TASK-065 accepts only the dual canonical completion chain in
which TASK-061-B's trusted Product operation freshly pinned and recomposed the
same TASK-036 operation and dependencies; no private capability is serialized
or transferred to TASK-065.

The single-EXE static/runtime split, T36-P01-P14 negatives and body-free
receipt boundary are in
[`task036-packaged-exe-chain-admission-2026-08-31.md`](task036-packaged-exe-chain-admission-2026-08-31.md).
Static import/spec/package-name PASS, `console=False`, stdout silence, exit0 or
EXE presence never substitute for the real-installed Product-operation receipt.

After every completion receipt is current, PL-A rebinds the baseline and PL-B
publishes the immutable operation config. If the separate Production Activation
Human Gate has not produced a current activation receipt, connector-enabled
runtime effects remain parked at `enabled:false`. After that separate Gate,
PL-C runs
`connector-status`, `publish-learning`, and `load-profile` against the exact
installed instance using explicit `--config`. Runtime PASS requires exact
request, BVP receipt, TASK-061 activation/config identity and independent
Profile read-back evidence; exit zero, endpoint or file presence is
insufficient. The bounded Product operation uses only the generic review-
observation lane; raw Project/anchor paths, revisions, store IDs or Owner scope
from caller text are prohibited. It selects exactly one plan-bound Generic
delivery and calls `import_path`; inbox-wide `import_once` is ineligible.

The D2C facade must structurally provide only
`admit_generic_observation`, `recover_generic_observation` and
`get_verified_generic_observation`. Its sealed modes follow the unmodified
Bridge call sequence: FRESH is `admit -> get_verified`, RECOVERY is
`recover -> get_verified`, and restart read-back is `get_verified` only.
Published receipt plus matching hidden correlation selects VERIFIED_READBACK;
published receipt without correlation is STOP/effect zero. Matching correlation
without receipt also selects VERIFIED_READBACK and takes precedence over a
coexisting pending record; then pending-only selects RECOVERY, and only total
receipt/correlation/pending absence plus an exact fresh plan selects FRESH.
Tampered, ambiguous or mismatched state remains effect zero. A method-mode race
burns the old facade FAILED_CLOSED; it never triggers automatic mode refresh or
retry.

PL-C records canonical typed-result status, Bridge `ImportResult.status`,
public receipt status and ledger/manifest revisions as separate Evidence
layers. Journal-absent terminal recovery must produce canonical and Bridge
`DUPLICATE` while preserving the public-v1 receipt contract; it must not fall
back to fresh admission or create a second Product commit.

TASK-036's sealed pre-activation real-installed E2E receipt is consumed only by
TASK-061-B to close final CA-C. TASK-061-A never claims E2E. Any later TASK-065
PL-C post-activation E2E receipt has a different phase, issuer and binding;
neither may substitute for another phase. The current TASK-061 synthetic
factory and any unapproved TASK-067 diff are ineligible.
Public receipt alone, missing hidden/canonical proof, mismatched DUPLICATE,
FAILED_CLOSED facade, or stale instance/config/Profile currentness remains
effect zero.

The same current-installation/lifecycle identity must survive TASK-036 E2E,
PL65-C01a, TASK-061-B, any separately authorized PL65-C01b operation and PL-D.
`executed:true` plus an adapter build is insufficient after upgrade, uninstall,
move, replacement or a second current install. C01a freshly joins receipts
with adapter/TASK-036 calls zero; C01b uses a new Human Gate and operation; PL-D
accepts only trusted lifecycle successors. The field/currentness and
PLC-I01-I16 matrix is in
[`pl-c-pl-d-installation-currentness-matrix-2026-08-31.md`](pl-c-pl-d-installation-currentness-matrix-2026-08-31.md).

### PL-D — lifecycle, rollback, and closure

Verify custom roots, upgrade, multiple installations, uninstall data
preservation, stale descriptor/config rejection, and disabled rollback. Final
closure requires independent DEV-4 Critic/Tester/Judge, focused/fault/relevant
regression, exact scope, canonical merge, and post-main read-back.

The packaged installer CLI `discover` is effectful: it calls
`write_installer_readback()` after logical discovery. PL-A/PL-D read-only
admission must not invoke it. Current source also has no authoritative
active-install registry or side-by-side selector, so TASK-065 must not scan
roots or choose an implicit winner. Until a trusted installer/Product
current-registration receipt and corrected noncreating TASK-063 reader are
current, PL-D remains `START0 / EFFECT0`.

The source-backed D01-D12 lifecycle boundary, historical-versus-real fixture
separation, lifecycle receipt fields and producer/consumer ownership are in
[`pl-d-lifecycle-source-matrix-2026-08-31.md`](pl-d-lifecycle-source-matrix-2026-08-31.md).
TASK-063 owns current-registration/lifecycle production, TASK-061-B owns
disable/history semantics, and TASK-065 consumes their receipts without
installer repair, activation/deactivation, preserved-data deletion, config
mutation or authority creation.

## Candidate Allowed Files

Repository-local candidate paths:

```text
docs/ai-team/tasks/TASK-065/**
src/ai_video_production/montage_learning_production_linkage.py
schemas/montage-learning-production-linkage.schema.json
src/ai_video_production/schema_resources/montage-learning-production-linkage.schema.json
tests/test_task065_montage_learning_production_linkage.py
tests/test_task065_montage_learning_production_linkage_windows.py
```

The following shared integration files are excluded from ordinary Units and may
change only at a milestone sole-Builder/LOCK checkpoint:

```text
docs/ai-team/task-index.md
docs/ai-team/current-state.md
docs/roadmap/PROJECT-ROADMAP-CANONICAL.md
CHANGELOG.md
```

The canonical and installed `bvp-montage-learning-adapter` connector configs
are not PL-B targets and remain byte-unchanged. Future PL-B runtime artifacts
are BVP-owned state effects, not repository files, and remain behind separate
Human/config/native gates. Their exact coordinates and transaction contract are
frozen in `pl-b-option-b-runtime-config-design-correction-2026-08-31.md`.

## Explicitly prohibited paths and effects

- `tests/test_task064_montage_learning_production_linkage.py` and
  `tests/test_task064_montage_learning_production_linkage_windows.py` are not
  TASK-065 paths and must not be created, edited, renamed, or copied.
- Do not modify TASK-058/060/061/063 source, schemas, tests, or historical
  Evidence.
- Do not modify TASK-036 Shell, TASK-044 Timeline, Resolve/DRFX source, other
  SKILLs, credentials, private keys, or Owner media.
- Do not modify the canonical or installed SKILL distribution config, including
  its historical disabled fixed-ProgramData default.
- Do not restore a fixed ProgramData production Bridge fallback.
- Do not invoke the adapter without the exact read-back BVP-owned `--config`
  path or let it discover/use the distribution default.
- Do not expose caller-selected raw config, learning-input or output paths from
  the Product runner. Opaque plan/record identity resolves contained paths
  internally; output is body-free public-safe data or an operation-owned private
  handle/pipe/temp, never arbitrary parent creation or overwrite.
- Do not create a pre-activation enabled config without a current TASK-061-A
  PREACTIVATION PREPARE receipt, canonical D2S adapter-side redemption contract
  and the bounded TASK-036 real-installed operation. A separate BVP receipt or
  config self-hash does not substitute for adapter-side consume.
- Do not use existing public `InstalledAdapterE2EReadback` objects or canonical
  public-factory outputs as Production authority, even when exact/sealed. Only
  a private one-use trusted Product-operation capability plus durable pinned
  completion read-back is eligible. Do not add a watcher/automatic importer or
  implement a TASK-036 Product-operation entrypoint from TASK-065.
- Do not call TASK-058 private Generic-store loaders, parse raw ledger JSON, or
  accept a caller/CLI-provided expected revision as a current coordinate.
- Do not use Bridge state as a shared dummy external anchor, create Project
  authority directories during a status/readback operation, or expose TASK-058
  exact APIs through the Generic-only facade.
- Do not accept a missing or `REJECTED` admission receipt, extra public-receipt
  fields, or correlation/instance/source/config hash mismatch as E2E or
  activation evidence.
- Do not set the repository default connector config to enabled.
- Do not admit/promote learning, mutate Timeline/Resolve, Release, Deploy, or
  activate Production.

## Current mutation boundary

While D0 through D2 remain incomplete, only TASK-065-local design and test-plan
documents may change. Source, schema, tests, installed config, native state, and
production state remain mutation zero.

TASK-067 is not currently implementation-authorized. Any local source/test
candidate is non-authoritative, must remain uncommitted/unpushed and cannot be
used as a dependency receipt. Only its TASK-065-local candidate allocation,
Allowed Files, design, Critic/Judge plan and implementation-start Gate may be
prepared.

The frozen PL-A mapping, negative matrix, exact-path overlap audit, dependency
checklist, and focused fixture plan are in
`pl-a-admission-design-freeze-2026-08-30.md`.

The mandatory task-local fault coverage for the formal TASK-067 facade and
future TASK-065 linkage is normalized in
`task067-task065-negative-matrix-v1-2026-08-31.md`. Every future case records
ID, source symbol, precondition, fault seam, expected typed result, separate
Project/Bridge/Profile/config-history deltas, public leakage and Evidence
receipt. Older whole-task TASK-061 completion language is SUPERSEDED there by
the canonical TASK-061-A -> TASK-067 -> TASK-036 -> TASK-061-B ordering.

The source/test-level comparison for those G67 rows is in
`task067-historical-coverage-gap-mapping-2026-08-31.md`. Named origin/main
TASK-058 tests are reusable historical regressions only, while the preserved
TASK-067 tests are candidate diagnostics only. Neither set supplies a
corrective PASS, implementation authority or completion receipt; each row
remains N.C. until its mapped missing fixture executes under the formal
TASK-067 start Gate.

Its historical missing-source classifications are superseded, but not promoted
to PASS, by `dependency-currentness-reconciliation-2026-08-31.md`: D0 source
corrections are canonical but installed completion is N.C.; D1/D2 candidate
sources are present but their completion receipts are missing; D2.5 TASK-067
and TASK-036 completion receipts are missing. TASK-067 freeze and future
allocation criteria are in
`task067-candidate-allocation-and-freeze-packet-2026-08-31.md`.
