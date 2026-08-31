# TASK-065 PL-A to PL-B installation binding matrix

State: `TASK_LOCAL_SOURCE_BACKED_REFINEMENT / SOURCE_START0 / EFFECT0`

Source baseline: BVP `origin/main`
`35cdf1ad475633dcf035e0616e979b5a8fde0c88`.

The external checkpoint is read-only design input, not completion Evidence.
This matrix closes the prose-to-transaction field gap without modifying BVP,
SKILL v1 config, adapter, installer or Production.

## Cross-stage gap

PL-B prose already stops stale payload, zero/multiple instance and lifecycle
mismatch. Its concrete receipt/CAS tuple previously bound mainly instance,
descriptor, owner, TASK-061 and predecessor config/receipt. It did not
explicitly carry Product EXE/payload-tree proof, the trusted registration set,
lifecycle predecessor/successor or reader currentness.

SKILL v1 config remains unchanged and transport-only. Adding BVP authority
fields to that closed schema would not make the adapter consume them. The
future operation-ticket config v2 or trusted broker and BVP-private receipts
must bind the missing authority.

The build-input `installer_manifest_sha256` and current TASK-063 acceptance
PASS/console JSON are audit-only. Neither proves a same-open rehash of the
installed payload, and the acceptance JSON exposes absolute roots. PL-B must
bind the future path-free TASK-063 installed-payload completion receipt instead.

## Required propagation

| PL-A proof | PL-B private binding | Public ceiling | Launch requirement |
| --- | --- | --- | --- |
| coherent snapshot | `task063_current_installation_receipt_sha256` | opaque hash | trusted reread matches |
| Product EXE/build | opened-identity and build digests | build/receipt hash, no path | verify before launch |
| payload tree | payload-tree and package receipt digests | opaque digest | missing/mismatch launch 0 |
| registration set | set and selected receipt hashes plus cardinality | cardinality/opaque hashes | cardinality exactly 1 |
| descriptor/owner generation | same-open snapshot receipt | opaque hashes | reject mixed/new inode |
| lifecycle | action and predecessor/successor receipt hashes | opaque action/revision/hash | exact successor required |
| lifecycle causality | trusted journal revision, predecessor/successor registration+payload and Product clock/session receipt | opaque revision/currentness hash; descriptor timestamps audit-only | timestamp order never authorizes config/launch |
| config/history | TASK-061 revision and current-installation hash | bounded revision/hash | names same successor |
| reader/backend/time | currentness/expiry receipt hash | opaque evidence/expiry state | drift burns ticket |
| effect proof | discover CLI 0, installer-readback write 0, root scan 0 | stable reason codes | prohibited call blocks commit/launch |

## Concrete private contract

The future BVP projection receipt and PREPARED journal bind:

- `task063_current_installation_receipt_sha256`;
- `installed_product_build_sha256`;
- `installed_payload_tree_sha256`;
- `installer_registration_set_sha256`;
- `selected_registration_receipt_sha256`;
- `installation_lifecycle_receipt_sha256`;
- `installation_lifecycle_revision`;
- `installation_clock_currentness_sha256`;
- `installation_selection_cardinality:1`; and
- `installation_reader_currentness_sha256`.

Every immutable transition and recovery retains the same ten fields. No
recovery scans roots, generations or recomputes a winner. TASK-068 creates no
current-head authority; the consumer-owned trusted plan/durable receipt binds
the exact generation, predecessor and terminal digest. The immutable
publication predecessor tuple is:

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
 installation_lifecycle_revision,
 installation_clock_currentness_sha256,
 installation_selection_cardinality,
 installation_reader_currentness_sha256,
 task061_revision,
 task061_history_sha256,
 task061_config_readback_sha256,
 previous_config_sha256,
 previous_receipt_sha256)
```

Any drift is a predecessor/currentness failure with config/receipt/adapter
effect zero. Same-path mutable CAS and exact delete are unavailable. The runner
holds its lease across final Product-currentness read, pinned adapter config
read and result capture. A lifecycle change after start never authorizes a
second command; fresh snapshot/ticket is required.

## PLB-I01-I19

| ID | Fault | Required result |
| --- | --- | --- |
| `PLB-I01` | receipt omits current-installation hash | config/launch 0 |
| `PLB-I02` | same descriptor/owner, different Product build | CAS reject; preserve current artifacts |
| `PLB-I03` | payload claim same but file/ancestor identity changed | launch 0; ticket closed per phase |
| `PLB-I04` | registration one to zero | launch 0; preserve Bridge |
| `PLB-I05` | registration one to two | `MULTI_INSTALL_AMBIGUOUS`; no winner |
| `PLB-I06` | selected registration belongs elsewhere | config/receipt commit 0 |
| `PLB-I07` | successor payload with predecessor lifecycle receipt | transition/projection delta 0 |
| `PLB-I08` | config/history names predecessor | launch 0; no history rewrite |
| `PLB-I09` | recovery sees different installation snapshot | `STOP_PRESERVE`; no advance/foreign cleanup |
| `PLB-I10` | old immutable config replayed after repair/reinstall | ticket redemption fails; command 0 |
| `PLB-I11` | Product changes between precheck and adapter open | final check fails; command 0 |
| `PLB-I12` | packaged `discover` invoked to refresh | prohibited call 0; readback write 0 |
| `PLB-I13` | root scan/remembered installer path supplies candidate | reject; registration receipt required |
| `PLB-I14` | installation receipt stale/expired/replayed/wrong reader | config/launch 0; fresh operation |
| `PLB-I15` | public output leaks path/account/SID/body/OS detail | public receipt 0 |
| `PLB-I16` | SKILL v1 config treated as installation authority | reject; transport-only/replayable |
| `PLB-I17` | descriptor time rolls back/equal/future/cross-session or newest timestamp is used for successor/selection/expiry | CAS/config/launch 0; require trusted journal revision, registration+payload chain and Product clock receipt |
| `PLB-I18` | mutable pointer, same-path replace/CAS or automatic deletion is requested from TASK-068 | stable `UNAVAILABLE`; filesystem/config/launch delta 0 |
| `PLB-I19` | exact generation absent/multiple/stale, caller-selected, scan-highest/newest or valid old tombstone replay | `CURRENT_HEAD_AUTHORITY_NOT_CREATED / STOP_PRESERVE`; command 0 |

Each case asserts Project/unrelated Bridge/distribution config/activation/
history delta zero, installer-readback write zero, exact phase-owned projection
delta only when already durably committed, command count 0 or exact one by
crash seam, and public leakage zero.

TASK-063 produces installation/lifecycle receipts, TASK-061-B binds config/
history, SKILL-D2S supplies operation authority, and TASK-065 PL-B only composes
current receipts. PL-B remains `START0 / EFFECT0` until the receipt, journal,
immutable transition, trusted head coordinate, ticket and launch-time readback
carry the same installation identity.
