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
It does not edit or synchronize the canonical/installed SKILL distribution
config. The historical fixed-ProgramData default remains disabled and is never
an active production fallback.

## Dependency order

1. `D0`: TASK-063 installer-relative source (`20f5360`), read-back boundary fix
   (`0b95e40`) and publication race/path-safety closure (`8fd17ed`) are
   canonical. D0 still requires fresh post-main hosted/Windows completion plus
   an exact re-provisioned installed read-back covering DACL, reparse, hardlink,
   descriptor, owner and discovery currentness. Older fixture/hash Evidence is
   not reusable as current PASS. Completion additionally requires pinned
   descriptor/owner discovery snapshots, secure provision/readback locking and
   identity-CAS/no-replace publication/rollback; current path-based replace and
   unlink behavior cannot prove race-safe installed currentness.
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
   cipher/coordinates are test-only and cannot mint source authority.
3. `D2`: TASK-061 corrects its public-v1/private-v2 readiness dependency and
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
   cleanup before D2 may complete. Human activation must be issued from a
   Product-owned trusted UI/process one-shot challenge; the current public
   predictable-string factory is self-mintable and cannot authorize ACTIVATE.
   Independently, public `InstalledAdapterE2EReadback` plus a module-visible
   sentinel is forgeable; ACTIVATE must consume a non-caller-constructible,
   one-use trusted Product-operation capability instead of public hashes/flags.
   The same applies to public CA-B readiness: readiness, Human and E2E objects
   are audit data only, while a trusted native-backend-fixed operation binds all
   three into the private apply capability.
4. `D2S`: the released SKILL adapter remains valid historical TASK-058 release
   Evidence, but its current transport writer/config/receipt/Profile readers do
   not meet Production race, physical-identity and privacy requirements, and
   its AdmissionReceipt schema/runtime validator still accepts extra fields
   that PL-C must reject. Independently, its closed config v1 has no operation,
   ticket, projection-receipt, expiry, nonce, invocation-budget or TASK-063
   instance binding, and the adapter does not atomically redeem any BVP one-shot
   authority. An `enabled:true` pre-activation config is therefore
   indistinguishable from reusable steady-state authority to the current
   adapter and cannot produce an activation-eligible PL-C0 receipt. Its current
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
   Profile publication and identity-safe pending/temp cleanup. The limited
   TASK-067 amendment does not include this work; TASK-061/065/067 cannot make
   the correction directly.
6. `D2C`: the unapproved TASK-067 follow-up candidate would supply a public
   sealed read-only current-coordinate receipt for the Generic review store
   only after a canonical metadata allocation and implementation Gate. It binds
   the current ledger revision to the Project manifest/binding, ledger head,
   recovery/journal currentness with no-create/read-only semantics. It exposes
   only the fixed Generic three-method admission surface; exact APIs remain
   sealed. TASK-065 grants no TASK-067 implementation authority. Until that
   allocation and completion receipt exist, this dependency is `N.C.`.
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
8. `D3`: only after the D2S operation-authority correction, TASK-065 proceeds
   through `PL-A`, then the cycle-safe sequence
   `CA-C prepare (apply0) -> PL-B0 -> PL-C0 -> CA-C apply -> PL-B steady-state
   -> PL-C steady-state -> PL-D`.

Under the corrected route, `PL-B0` is a sealed, explicit-path, one-use
pre-activation E2E operation and `PL-C0` is public-safe synthetic transport E2E
against the exact real installed instance. Current SKILL config v1 cannot
enforce that boundary. Without a canonical SKILL v2/trusted-broker correction,
PL-B0 is only a BVP-internal synthetic Bridge probe and PL-C0 is not real SKILL
E2E or an activation prerequisite. Neither route is Production activation.
CA-C alone consumes an eligible corrected PL-C0 receipt and owns activation/
history mutation. TASK-065 never changes TASK-061 or SKILL source or mints Human
authority.

TASK-059 signing is `NOT_REQUIRED` under the current contract. A future
explicit Release/Pack signing requirement is a separate Gate.

## Atomic Units

### PL-A — production linkage admission/projection

Pure, public-safe, effect-zero validation of the exact TASK-058, TASK-060,
TASK-061, and TASK-063 inputs. Missing, stale, tampered, ambiguous,
multi-instance, unknown-version, unknown-authority, or fixed-ProgramData
coordinates remain disabled and authorize no later effect.

### PL-B — BVP-owned instance-bound runtime config projection

Eligible only after current PL-A PASS and a separate Human/config Gate. It may
publish only a revisioned BVP-owned runtime config projection beneath the exact
TASK-063 installer-relative Bridge state. It binds the exact install instance,
descriptor/owner identities and current TASK-061 config/history receipt. The
adapter is always invoked with the exact read-back operation config path through
`--config`; default discovery and fixed-ProgramData fallback are forbidden.

Steady-state `enabled` is derived only from the current TASK-061 activation
receipt/history. PL-B cannot edit that history, mint Human evidence, or infer
enabled state. PL-B0 requires the separately authorized TASK-061 pre-activation
E2E ticket plus the D2S adapter-side one-shot redemption contract and never
publishes a steady-state runtime config. Each invocation uses an immutable,
noreplace operation-specific config/receipt coordinate; a mutable current
pointer, if needed, is BVP-only and never adapter authority. Every
pre-activation and steady-state runtime config fixes
`require_admission_receipt:true`; publish/read feature flags are operation-
scoped minimum authority and are never assumed both true. Feature flags alone
never prove operation authority.

### PL-C — real connector E2E/read-back

PL-C0 runs the bounded pre-activation public-safe synthetic transport flow only
after the corrected adapter has atomically redeemed the exact PL-B0 one-shot
operation and after the TASK-061 operation-plan/admission receipt plus the
TASK-067 Generic current-coordinate/facade receipt and TASK-036 packaged-
entrypoint completion receipt are current. Adapter `publish-learning` stages
the exact delivery once and may return PENDING. TASK-036 then invokes exact
`import_path`; the trusted BVP runner separately pinned-reads the strict public
receipt, hidden Generic correlation, canonical state and Profile read-back.
It never calls `publish-learning` again to confirm admission and never treats
adapter `canonical_store_written` as authority. PL-C0 binds those separate
layers into its E2E receipt, returns it to TASK-061 and claims no Production
activation. After CA-C
apply and steady-state PL-B projection, PL-C runs
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

TASK-061's sealed pre-activation real-E2E receipt is a distinct activation
prerequisite. TASK-065's later PL-C post-activation E2E receipt has a different
phase, issuer and binding; neither may substitute for the other. The current
TASK-061 synthetic factory and any unapproved TASK-067 diff are ineligible.
Public receipt alone, missing hidden/canonical proof, mismatched DUPLICATE,
FAILED_CLOSED facade, or stale instance/config/Profile currentness remains
effect zero.

### PL-D — lifecycle, rollback, and closure

Verify custom roots, upgrade, multiple installations, uninstall data
preservation, stale descriptor/config rejection, and disabled rollback. Final
closure requires independent DEV-4 Critic/Tester/Judge, focused/fault/relevant
regression, exact scope, canonical merge, and post-main read-back.

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
- Do not create a pre-activation enabled config without a separately authorized
  TASK-061 one-shot E2E ticket, canonical D2S adapter-side redemption contract
  and bounded PL-C0 Gate. A separate BVP receipt or config self-hash does not
  substitute for adapter-side consume.
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

Its historical missing-source classifications are superseded, but not promoted
to PASS, by `dependency-currentness-reconciliation-2026-08-31.md`: D0 source
corrections are canonical but installed completion is N.C.; D1/D2 candidate
sources are present but their completion receipts are missing; D2.5 TASK-067
and TASK-036 completion receipts are missing. TASK-067 freeze and future
allocation criteria are in
`task067-candidate-allocation-and-freeze-packet-2026-08-31.md`.
