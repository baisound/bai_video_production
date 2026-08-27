# TASK-058 FAST-BATCH-1 Bridge and Transport Design

Date: 2026-08-27
Profile: DEV-4
Scope: PR2 subunits B and C

## Frozen responsibility

Subunit B owns the BVP-created file-bridge layout, one-shot intake, independent
delivery revalidation, delegation to the canonical admission transaction owned
by subunit A, and durable matching receipt publication.  Subunit C owns only
transport of an upstream-produced, already-approved SKILL v1 advisory profile
envelope and machine-readable readiness evidence.

For a generic observation, `canonical_store_written=true`, `ACCEPTED`, and
`DUPLICATE` mean only that the exact generic payload identity was durably and
idempotently recorded in BVP's canonical review-observation intake ledger.
They do not mean learning adoption, Profile generation, promotion, Timeline
mutation, Resolve mutation, or Owner-scope authentication.  The existing
public v2 exact-profile receipt remains unchanged.  A new internal generic
receipt is projected separately to the SKILL v1 transport receipt.

TASK-058 never derives a SKILL projection from TASK-055 timing preferences.  It
accepts only a complete prebuilt `BvpMontagePreferenceProfileDelivery` and
revalidates and copies it without field transformation.

## Dependency order and files

1. Subunit A canonical transaction APIs are the only canonical store boundary.
2. Subunit B adds `montage_learning_file_bridge.py` and
   `montage_learning_bridge_application.py`, with focused fault tests.
3. Subunit C adds `montage_learning_connector_readiness.py`, a public/package
   readiness Schema mirror, and isolated adapter E2E tests.

No SKILL file/config, Product Timeline/Resolve source, shared CHANGELOG,
Registry, current-state, or TASK-019/029/054/055/059 file is changed.

## B: bridge and importer

Production uses exactly
`C:\ProgramData\BAI Video Production\montage-learning-bridge` with
`learning-inbox`, `learning-receipts`, and `preference/current-profile.json`.
An owner manifest binds the root path, bridge instance ID, contract profile,
and production-layout flag.  Production construction cannot accept an
alternate root; isolated test construction can never claim production.

Provision and every operation reject symlinks, non-directories, and Windows
reparse points.  The importer is bounded and one-shot.  It opens a delivery
once, snapshots bytes through that handle, compares pre/post file identity,
enforces a byte limit, parses built-in JSON with duplicate-key rejection, and
checks filename record/digest binding before selecting the exact or generic
validator.  Mixed or unknown profiles fail closed.

The application delegates only typed, independently validated inputs to A.
Returned exact v2 or internal generic receipts are reparsed and matched to the
snapshot coordinates before an atomic new-or-identical receipt publication.
On a durable A commit followed by publication failure, a later one-shot import
reruns A idempotently and publishes the recovered matching receipt.  Inbox
deliveries are not moved or deleted.

## C: immutable profile transport and readiness

Profile publication requires an explicit source-binding capability.  The
production source is not connected in this Batch, so production reports
`production_profile_source_bound=false` and `SOURCE_NOT_BOUND` and performs no
profile write.  Isolated tests may use a fixture binding solely to prove
transport compatibility.

The publisher strictly validates the SKILL v1 envelope, payload hash, bounded
projection shape, authority flags, and CAS expectation, then writes the exact
snapshot atomically to `preference/current-profile.json`.  It does not create,
rank, aggregate, or alter any preference.

Readiness keeps bridge, import, profile, adapter, and activation states
independent.  `adapter_contract_e2e_pass=true` cannot imply a production source
binding.  `connector_enabled` and `activation_authorized` are always false in
Batch evidence.  Therefore activation remains `BLOCKED` until a later exact
Owner gate binds a producer and changes the real SKILL config.

## Acceptance and risks

Focused tests cover idempotent provision; alternate-root production-claim
rejection; symlink/reparse/unstable/oversize/malformed/filename-digest failures;
exact/generic separation; receipt binding/collision and retry; prebuilt Profile
strictness/hash/CAS/source binding; schema mirror identity; and unchanged-SKILL
isolated connector-status, publish/receipt, and load-profile E2E.

Critical/High risks are generic/exact receipt confusion, commit/publication
crash, unsafe path replacement, false producer readiness, Profile semantic
generation, and accidental `enabled:true`.  The boundaries above are mandatory
fail-closed controls; any residual instance stops only the affected subunit.
