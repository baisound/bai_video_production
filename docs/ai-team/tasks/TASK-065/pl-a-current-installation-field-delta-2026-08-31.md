# TASK-065 PL-A current-installation field delta

State: `TASK_LOCAL_SOURCE_BACKED_REFINEMENT / SOURCE_START0 / EFFECT0`

Source baseline: BVP `origin/main`
`35cdf1ad475633dcf035e0616e979b5a8fde0c88`.

The external checkpoint with the same date/topic is read-only design input,
not canonical Evidence or a completion receipt. This document refines PL-A
admission only; source, schema, tests, shared metadata, installer state,
SKILL/config/adapter state and Production remain unchanged.

## Finding

`InstalledBridgeDiscovery.public_receipt()` exposes the instance ID, relative
Bridge coordinate, descriptor hash, owner-manifest hash and disabled status.
Those are necessary audit coordinates, but do not prove current Product EXE/
payload bytes, a uniquely current trusted registration, valid lifecycle
continuity, or matching TASK-061 config/history.

The descriptor's `installer_manifest_sha256` is a claimed coordinate, not
proof of present installed bytes. Source confirms
`build-task063-main-installer.ps1` computes it from build-input payload files
sorted by `FullName`, with relative path plus per-file SHA-256 lines. Inno
passes that build-input tree digest to the private EXE for descriptor storage,
but neither Inno nor `test-task063-main-installer.ps1` regenerates the manifest
from installed files or compares installed bytes, descriptor digest and build
output in one current snapshot. `AppId`/`UsePreviousAppDir=yes` are static
installer behavior, not a current-instance registry; absent
`[UninstallDelete]` is preservation intent, not proof that preserved data is
still installed/current. Packaged `discover` is ineligible because it calls
`write_installer_readback()`; PL-A admission call count must remain zero.

The current acceptance script reads descriptor and receipt using `Get-Content`
plus `ConvertFrom-Json`, checks relative Bridge, instance equality and disabled
flags, then emits absolute `install_root` and `bridge_root`. It has no strict
duplicate/non-finite/BOM/trailing bounds or opened physical-identity proof.
Its PASS/console JSON is historical acceptance output only and is ineligible
for PL-A, PL-B or PL-C authority and for a public path-free projection.

Descriptor `created_at`/`updated_at` are also audit/display data only. Repair
preserves the previous `created_at` and writes caller/internal `now` directly
to `updated_at`; validation proves only string, trailing `Z` and datetime
parseability. It does not prove `created_at <= updated_at`, monotonic repair,
trusted clock/boot/session or predecessor causality. PL-A must never use these
fields for current/newest selection, lifecycle successor, expiry/currentness
or multi-install tie-breaking. Only the trusted registration set and a
journal-bound predecessor/successor revision plus Product payload identities
can establish current lifecycle state.

Descriptor absence is not a fresh-install proof. Current TASK-063 source enters
the fresh publication branch whenever the descriptor path is absent, reuses an
existing owner manifest's `bridge_instance_id`, and may recreate the descriptor
without a journal or predecessor receipt. If a prior installer readback remains
and publication then fails, fresh rollback unlinks that receipt based only on
its path/type before proving that the current operation created its exact
identity. PL-A therefore classifies descriptor-absent owner-only or owner-plus-
receipt state as orphan/ambiguous, never current or fresh. Exact recovery needs
a journal-bound predecessor and operation-owned descriptor/receipt identities;
otherwise the result is `STOP_PRESERVE / EFFECT0` and every preexisting object
is retained.

## Private trusted snapshot

The public receipt is audit-only (`authority_created:false`). A future
TASK-063/Product-owned noncreating reader must bind one private operation
snapshot:

| Group | Required proof | Current gap |
| --- | --- | --- |
| instance | Product, opaque instance, relative Bridge, operation/plan | one caller root does not prove selection/currentness |
| descriptor | schema, raw/canonical digest, opened identity, link/reparse, ancestors, creation/update | public hash is replayable from preserved data |
| owner | raw/canonical digest, same-open identity, instance/owner/DACL/current-user/ancestors | public hash does not bind one generation |
| Product | EXE/build identity, full payload-tree digest, installer/package build and ancestors | recorded manifest hash is not installed-byte proof |
| registration | receipt identity, exact instance/state/Product/build/payload, issuer/backend, expiry/currentness | no authoritative active-install set exists |
| lifecycle | action/operation and predecessor/successor registration/payload/descriptor/owner receipts | UUID/timestamp continuity is insufficient |
| cardinality | trusted set identity, zero/one/multiple count and selected member | root scan and implicit winner are prohibited |
| connector | TASK-061 config/history revision, instance and Product/lifecycle binding | config presence cannot establish authority |
| reader | Product reader/build/backend, one-use capability and trusted time | caller paths/hashes/objects/booleans are ineligible |
| effect | packaged `discover` 0, installer-readback writes 0, root scans 0, Project/Bridge/config/Profile delta 0 | current packaged command writes |

TASK-063 retains strict bounded JSON, nofollow, same-open, pre/post identity,
nlink-one, no-reparse, DACL and rollback ownership. TASK-065 consumes its
durable receipt and does not repair it.

## Public ceiling and results

The public projection may expose only version, opaque result/instance IDs,
relative Bridge, opaque descriptor/owner/Product/build/registration/lifecycle
hashes, cardinality (`0`, `1`, `MULTIPLE`), stable reason codes, execution
observation, disabled authority flags and `authority_created:false`. Absolute
paths, account/SID, raw DACL, EXE path, command line, OS details and private
bodies are prohibited.

| Condition | Result | Effect |
| --- | --- | --- |
| one coherent current Product/registration/lifecycle/config snapshot | `CANDIDATE_CURRENT_INSTANCE` | audit candidate only; no sync/run/activation/learning |
| zero registrations | `NO_CURRENT_INSTALLATION` | `EFFECT0`; preserve data |
| multiple registrations | `MULTI_INSTALL_AMBIGUOUS` | `EFFECT0`; no winner |
| uninstall-preserved Bridge | `UNINSTALLED_DATA_PRESERVED` | `EFFECT0`; disabled/not current |
| descriptor/owner without current payload/registration | `PRODUCT_INSTALLATION_INCOMPLETE` | `EFFECT0`; no repair |
| descriptor absent with owner and/or prior receipt | `INSTALLATION_ORPHAN_AMBIGUOUS` | `STOP_PRESERVE / EFFECT0`; no reuse/delete |
| Product generation differs from descriptor/readback | `INSTALLATION_GENERATION_MISMATCH` | `EFFECT0`; upstream repair |
| lifecycle or config/history mismatch | `INSTALLATION_LIFECYCLE_STALE` | `EFFECT0`; no history rewrite |
| identity/security/parser/currentness failure | stable `*_INVALID`/`*_STALE` | `EFFECT0`; preserve ambiguity |

`CANDIDATE_CURRENT_INSTANCE` is not `READY_FOR_CONFIG_SYNC` and creates no
effect authority.

## PLA-I01-I18

| ID | Fault | Required assertion |
| --- | --- | --- |
| `PLA-I01` | PL-A invokes packaged `discover` | call 0; installer-readback/inventory delta 0 |
| `PLA-I02` | preserved root lacks Product payload | `UNINSTALLED_DATA_PRESERVED`; no delete/repair |
| `PLA-I03` | EXE/payload-tree mismatch | incomplete/generation mismatch; effect0 |
| `PLA-I04` | descriptor installer hash differs from installed bytes | reject claimed digest as proof |
| `PLA-I05` | same descriptor/owner bytes, different inode/ancestor | reject physical drift |
| `PLA-I06` | registration names other root/instance/build/payload | cross-install admission 0 |
| `PLA-I07` | payload advanced, descriptor/readback stale | reject mixed generation; no repair |
| `PLA-I08` | two current registrations | `MULTI_INSTALL_AMBIGUOUS`; no scan/winner |
| `PLA-I09` | zero registration with preserved roots | `NO_CURRENT_INSTALLATION`; preserve roots |
| `PLA-I10` | config/history names predecessor/other instance | reject; config/history delta 0 |
| `PLA-I11` | lifecycle/registration receipt stale/expired/replayed | body-free reject; fresh read required |
| `PLA-I12` | descriptor/owner/payload/registration mixed generations | reject; coherent snapshot required |
| `PLA-I13` | move/portable copy reuses old coordinate | reject; trusted rebind; preserve old data |
| `PLA-I14` | public result leaks root/account/SID/OS/command/body | privacy failure; public receipt 0 |
| `PLA-I15` | reader/backend/build/time drifts during operation | burn capability; blocked/effect0 |
| `PLA-I16` | build-input `installer_manifest_sha256` or current acceptance PASS/console JSON is substituted for installed payload proof | `BUILD_INPUT_CLAIM_ONLY / INSTALLED_PAYLOAD.N.C. / EFFECT0`; reject absolute-root projection; no PL-B/C promotion |
| `PLA-I17` | descriptor timestamp rolls back, equals predecessor, is future-dated, crosses boot/session, or chooses the newest of multiple installs | timestamp authority0; require trusted registration-set and exact journal predecessor/successor revision; no winner/effect |
| `PLA-I18` | descriptor absent while owner manifest and/or old installer receipt remains; receipt is identical/different/foreign-swapped or its inode changes before fresh rollback | owner-only is not fresh/current; automatic instance reuse0; require exact journal/predecessor recovery proof and operation-owned cleanup identity; preserve owner/receipt/data, delete0, `INSTALLATION_ORPHAN_AMBIGUOUS / STOP_PRESERVE / EFFECT0` |

Every case separately asserts Project inventory unchanged, unrelated Bridge
data unchanged, installer-readback write zero, config/history/Profile mutation
zero, adapter execution zero, activation history zero and public leakage zero.

## Ownership and Gate

TASK-063 owns Product installation/current-registration/lifecycle proof;
TASK-061-B owns config/history semantics. TASK-065 PL-A only consumes exact
receipts and emits a blocked/candidate audit projection. It does not scan,
discover effectfully, repair/register, mutate config/history, run the adapter,
activate, or delete preserved data.

PL-A remains `START0 / EFFECT0` under
`TASK-068 -> {TASK-069,TASK-063} -> TASK-060 -> TASK-061-A -> TASK-067 -> TASK-036 -> TASK-061-B -> TASK-065`
plus SKILL-D2S and installed exact Windows readback.
