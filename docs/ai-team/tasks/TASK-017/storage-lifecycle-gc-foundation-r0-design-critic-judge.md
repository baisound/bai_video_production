# TASK-017 Storage Lifecycle / GC Foundation R0

Date: 2026-08-17
Owner: Developer 2
Authority: pure metadata contract implementation only
Initial implementation base: `809e9a13a622ba68054f6faadb5ca194345d27af`
Fresh recomposition base: `caa2380767d57bee963657874ed1a198877c0481`

## 1. Outcome and boundary

This unit defines a body-free, deterministic contract for retention policy,
external inventory observations, lifecycle proposals, Human effect authority
and externally issued effect receipts.  It does not enumerate a directory,
read media, move/archive/delete bytes, modify an Asset, schedule a Job, or
issue a canonical storage-effect success receipt.

The module may return that an exact external effect is admissible only when an
unchanged policy, observation, decision and one-shot Human authorization are
all current and exact.  That report is not a dispatcher or an effect receipt.

## 2. Authority and no-duplicate matrix

| Truth / effect | Canonical owner | TASK-017 R0 use |
|---|---|---|
| Asset identity, checksum, rights, owner and `RetentionClass` | TASK-003 / `AssetRecord` | Exact digest/reference; imports the existing enum and never recreates Asset truth |
| Privacy findings, review, publication gate and invalidation | TASK-016 | Read-only external dependency; privacy hold is an observed state, not a TASK-017 privacy decision |
| Durable Job/checkpoint/store execution | TASK-043 and storage substrate | External; no Job/store/queue API is present |
| Inventory collection and canonical persistence | Future storage/inventory adapter | Exact profile reference and digest; `observation_performed_by_module=false` |
| Retention policy and deterministic disposition proposal | TASK-017 metadata contract | Owned by this unit |
| Archive/delete Human authorization | Owner Human Gate | Structured binding only; raw `execution_authorized` boolean is forbidden |
| Archive/delete bytes and read-back | Future authorized storage effect adapter | Not performed here |
| Canonical external effect receipt | Future authorized storage effect owner | `StorageEffectReceiptBinding` validates the external receipt; this module does not issue one |
| Release, Deploy and Production | Separate owner/Gate | Not authorized |

This Product TASK-017 contract is not BAI Development OS TASK-017 and does not
change OS task state or deployment authority.

## 3. Canonical records

1. `RetentionRule`
2. `StorageRetentionPolicyRevision`
3. `StorageObjectObservationReceipt`
4. `StorageDispositionDecisionReceipt`
5. `StorageEffectAuthorizationBinding`
6. `StorageEffectReceiptBinding`
7. `StorageDispositionPublicProjection`
8. `StorageEffectPublicProjection`

Policy revisions are append-only.  Revision 1 has no parent; later revisions
require the exact parent digest.  Rules contain all existing Asset retention
classes exactly once and in canonical enum order.  `LEGAL_HOLD` has no archive
or delete threshold.

Observation receipts bind the exact logical object/revision, Asset record,
retention class, observation time, last-use time, byte count, active and
pending-Job references, legal/privacy holds and inventory profile.  They
persist no path or media body and do not claim that this module measured the
facts.  UNKNOWN facts remain null; UNKNOWN is never converted to zero.

## 4. Decision semantics

`KEEP`, `ARCHIVE_PROPOSED`, `DELETE_PROPOSED`,
`NO_ACTION_ALREADY_ABSENT`, `BLOCKED` and `UNKNOWN` are distinct.  A proposal
does not authorize an effect.  Current references keep an object.  Any active
hold blocks it.  Unknown hold/inventory state and stale/future observations
produce UNKNOWN.  An already absent object is not presented as a successful
new deletion.

The evaluator uses integer seconds and exact UTC timestamps.  It never infers
a retention policy from age or file location.

## 5. Effect Gate and external receipt boundary

`StorageEffectAuthorizationBinding` has the closed states
`CANONICAL_REF_NOT_PROVIDED`, `BOUND_VERIFIED`, `MISMATCH`, and `UNKNOWN`.
Only `BOUND_VERIFIED` contains canonical fields.  It binds exact project,
object/revision, decision, effect, issuer kind, issue/expiry window, one-shot
policy and Evidence.  Unresolved states require every decision field to be
null.  A raw or caller-forged boolean cannot grant authority.

`classify_effect_gate` re-verifies policy, observation and decision hashes,
their exact cross-bindings, current observation age, authorization issue and
expiry time, object revision and proposed effect.  Mismatch/expiry/tamper is
BLOCKED; unavailable canonical authority is UNKNOWN.  The function performs
no effect and does not consume the one-shot authorization.

`StorageEffectReceiptBinding` represents an authoritative external receipt.
The pure module has no `compile_effect_receipt` API.  BOUND_VERIFIED requires
the canonical receipt reference/hash plus exact decision, authorization,
before-observation and read-back fields.  UNKNOWN needs the reason
`EXTERNAL_STATE_UNKNOWN`; no automatic retry follows.  Verified archive and
delete results require the matching effect and an authoritative after-state
observation digest.  Failed, partial or unknown results cannot claim a
verified after-state.

## 6. Privacy and projections

IDs are logical coordinates and reject absolute paths, traversal, Windows
path separators and credential-like identifiers.  General records contain no
body, raw path, credential or key.  Public projections suppress object, Asset,
inventory, policy, authorization and receipt coordinates/digests.  They expose
only lifecycle/result state, bounded reason codes and explicit false effect
flags.

## 7. API and static effect surface

Allowed APIs are parse/validation, canonical JSON/hash, deterministic policy
classification, exact effect admissibility classification, external receipt
binding validation, hash verification and public projection.  The module does
not import filesystem, process, network or application-control packages and
does not call open/remove/unlink/rmdir/rename/replace.

The following remain `false` in canonical records:

- `automatic_effect_authorized`
- `observation_performed_by_module`
- `effect_started`
- `automatic_delete_authorized`
- `effect_performed_by_module`
- `automatic_retry_authorized`

## 8. Acceptance inventory

Positive cases:

- deterministic policy revision/hash and exact parent lineage;
- known present observation and exact body-free Asset/inventory binding;
- keep, archive proposal, delete proposal, held and already-absent decisions;
- exact current one-shot Human binding yields an external-effect admissibility report;
- externally bound verified archive receipt and privacy-safe public projection.

Negative/fail-closed cases:

- missing or reordered retention class, illegal threshold or forged revision parent;
- absolute/traversal/private path-like coordinate;
- UNKNOWN fact represented as zero or with invented hold state;
- stale/future observation, unknown hold, active reference or active hold;
- changed policy, mismatched observation/decision/object/effect, tampered digest;
- raw `execution_authorized=true`, incomplete authority, replay-capable authority;
- future-issued, expired or wrong-scope authority;
- verified result without authoritative after-observation or wrong effect kind;
- UNKNOWN external receipt without an explicit unknown reason;
- extra body/path property, schema cross-field mismatch or public coordinate leak;
- any filesystem/process/network/effect API in the pure module.

## 9. Validation plan and result

Focused validation covers schema Draft 2020-12, schema/runtime cross-fields,
mirror byte equality, deterministic hashes, policy and hold branches,
authorization forgery/expiry, external receipt state, tamper, privacy and a
static no-effect scan.  Repository full regression is required after fresh
main integration on Windows and WSL2.

Validation result:

- focused TASK-017: `13 passed`;
- Windows full: `1653 passed, 1 skipped` (the non-Windows credential-vault contract);
- WSL2 full: `1653 passed, 1 skipped` (the Windows-only OBS installer acceptance);
- public schema/mirror: byte-identical;
- final branch diff: exact six paths (five TASK-017 files plus one CHANGELOG line).

## 10. Critic pass 1 — Builder / compatibility

Finding (Medium): Windows path input failed as a generic invalid ID before the
body-free boundary was classified.  Fixed by applying the explicit path/body
guard before the identifier grammar.  Focused regression passed.

Finding (Medium): runtime state-dependent decision/result constraints were
stronger than the initial schema.  Fixed with revision-parent, canonical rule
order, proposed-effect and verified-result conditions in the public schema and
byte-identical mirror.

Residual Builder/Compatibility Critical/High/Medium: `0 / 0 / 0`.

## 11. Critic pass 2 — Security / authority

Initial finding (High): the first draft exposed a constructor that could issue
a locally hashed `VERIFIED_DELETED` or `VERIFIED_ARCHIVED` receipt without an
authoritative storage owner.  Fixed by removing canonical effect-receipt
issuance and replacing it with `StorageEffectReceiptBinding`, whose exact
external receipt reference/hash is mandatory only in `BOUND_VERIFIED`.

Initial finding (High): effect admission did not re-check current policy,
decision-to-observation digest inclusion or observation freshness.  Fixed by
requiring the current policy input and re-verifying all three record hashes,
cross-bindings and freshness at operation time.

Finding (Medium): observations did not explicitly declare that collection was
external.  Fixed with schema-constant `observation_performed_by_module=false`.

Residual Security/Authority Critical/High/Medium: `0 / 0 / 0`.

## 12. Judge

- `DOMAIN_CONTRACT_READINESS=PASS`
- `BODY_FREE_AND_PUBLIC_PROJECTION=PASS`
- `PURE_METADATA_IMPLEMENTATION=PASS`
- `STORAGE_INVENTORY_COLLECTION=NOT_AUTHORIZED`
- `ARCHIVE_DELETE_EFFECT=NOT_AUTHORIZED`
- `ASSET_JOB_PRIVACY_MUTATION=NOT_AUTHORIZED`
- `RELEASE_DEPLOY_PRODUCTION=NOT_AUTHORIZED`
- unresolved Critical/High/Medium: `0 / 0 / 0`

The unit may proceed through exact-file validation and repository integration.
It cannot claim runtime GC, archive, delete, Asset mutation or Production.
