# TASK-065 PL-A Candidate Contract Rebind

Date: 2026-08-30
Atomic Unit: PL-A admission preparation
State: `DEPENDENCY_CANDIDATES_INTEGRATED / CANONICAL_GATES_OPEN / EFFECT0`

## Purpose and effect ceiling

This checkpoint replaces only the PP-C and CA-C placeholders in the earlier
PL-A design freeze with source-backed candidate field mappings. It does not
declare D0, D1, or D2 complete. The candidates remain stacked Draft PRs and
remote `main` remains `160c9569673fbf65a28b0f95eeb44c5b0111584f`.

No TASK-065 source, schema, test, installed SKILL config, native config,
adapter, learning, Timeline, Resolve, Release, Deploy, or Production effect is
authorized or performed by this rebind.

## Exact candidate heads and hosted state

| Gate | Candidate | Exact head | State at rebind |
|---|---|---|---|
| D0 | TASK-063 safety closure PR #451 | `8fd17ed23242d34102908a0ce19fe8ce68b7cc9f` | Draft/open/mergeable; six OS/Python tests, dependency audit and secret scan pass; shared changelog gate fails |
| D1 | PP-A PR #452 | `6e16c3ea040c503137030d51ef965cc11545290b` | Draft/open/mergeable; same hosted result as D0 |
| D1 | PP-B PR #456 | `0e94fca36c90035bd1f090eef420443bf4f2763a` | Draft/open/mergeable; same hosted result as D0 |
| D1 | PP-C PR #457 | `ea5d4954782708e72086d542d318d71fd66598f8` | Draft/open/mergeable; same hosted result as D0 |
| D2 | readiness wording PR #454 | `0549feaa162e75d26264e38cd91fa234dfb96c31` | stacked candidate, not canonical |
| D2 | CA-A security PR #458 | `087c3fed692868f89b69e17e08e60fa6249b22ca` | Draft/open/mergeable; rerun in progress after fail-closed hosted-owner fixture correction |
| D2 | CA-A migration PR #459 | `507e76a40b59ceff3a91ef5eb424f1e8e0d6378c` | Draft/open; rerun after full-attestation pinning |
| D2 | CA-B PR #460 | `74e732067057574990725eb4058bd3712382341e` | Draft/open; rerun after full-attestation pinning |
| D2 | CA-C PR #461 | `675bab5a94538e1966678bf004ba6bb13e42601a` | Draft/open; rerun after full-attestation pinning |

The shared `changelog-and-version` failure is not waived or reported as pass.
TASK-065 does not own the shared changelog. A hosted temporary directory whose
owner differs from the current Windows user remains fail-closed as
`WRONG_OWNER`; the real fixture now records that host as environment-N.C.
rather than weakening the production ownership rule.

A subsequent DEV-4 boundary review found that owner/current-user/count equality
alone did not detect a different still-secure DACL or root identity between
plan and write read-back. CA-A migration now pins the complete initial
attestation hash, CA-B carries the same hash in its sealed plan, and CA-C
compares complete before/after attestation hashes. Focused negative tests change
only the secure DACL and prove rejection; owner policy was not relaxed.

## D0 TASK-063 discovery mapping

`InstalledBridgeDiscovery.public_receipt()` currently exposes exactly:

`schema_version`, `message_type`, `product_id`, `install_instance_id`,
`bridge_relative_path`, `descriptor_sha256`, `owner_manifest_sha256`,
`capability`, `status`, `connector_enabled`, and `activation_authorized`.

PL-A candidate admission requires the message type
`BvpMontageLearningBridgeDiscoveryReceipt`, product
`BAI_VIDEO_PRODUCTION`, capability `INSTALL_RELATIVE_BRIDGE_DISCOVERY`, status
`READY_DISABLED_BY_DEFAULT`, and both authority booleans false. It cross-binds
the opaque instance, relative coordinate, descriptor hash, and owner hash to
the exact corrected installation read-back. It never accepts an absolute path
from this public receipt or supplies a fixed ProgramData fallback.

D0 remains `DEPENDENCY_NOT_CANONICAL` until PR #451 is canonically merged and
the same test/read-back obligations pass at the post-main identity.

## D1 PP-C promoted-source mapping

`PromotedPreferenceSourceRead.to_dict()` currently exposes exactly:

`record_version`, `record_type`, `task_owner`, `source_id`,
`source_file_identity_sha256`, `store_id`, `owner_scope_sha256`,
`promotion_revision`, `promotion_revision_sha256`, `history_sha256`,
`profile_id`, `profile_version`, `active_payload_sha256`, `envelope`,
`envelope_sha256`, `exact_current_source_verified`,
`production_profile_source_bound`, `advisory_profile_only`,
`automatic_promotion_authorized`, `timeline_mutation_authorized`,
`resolve_write_authorized`, `external_effect_authorized`, and
`readback_sha256`.

PL-A must require:

- version `1.0.0`, type
  `MONTAGE_PREFERENCE_PROMOTED_SOURCE_READBACK`, and owner `TASK-060`;
- one pinned regular, non-reparse, non-hardlinked source identity;
- exact revision/history/envelope/profile cross-binding and recomputed hashes;
- `exact_current_source_verified`, `production_profile_source_bound`, and
  `advisory_profile_only` true;
- automatic promotion, Timeline, Resolve, and external effects false;
- unknown fields, stale revision, same revision/different body, tamper,
  revocation, missing receipt, or multiple current sources rejected.

The PP-C candidate supplies exactly one advisory envelope; it does not grant
activation or learning-admission authority. D1 remains
`DEPENDENCY_NOT_CANONICAL` until PP-A, PP-B, and PP-C are each canonically
completed and an exact post-main promoted source read-back is supplied.

## D2 CA-A security and migration mapping

The CA-A security attestation carries:

`schema_version`, `record_type`, `task_owner`, `attestation_id`, `state`,
`root_identity_sha256`, `owner_sid_sha256`, `current_user_sid_sha256`,
`dacl_sha256`, `ancestor_count`, `reason_codes`,
`all_ancestors_revalidated`, `unknown_ace_rejected`,
`shared_writer_ace_rejected`, `repair_performed`, `migration_started`,
`connector_config_write_authorized`, `activation_authorized`,
`timeline_mutation_authorized`, `resolve_write_authorized`,
`external_effect_authorized`, and `attestation_sha256`.

PL-A accepts only `SECURE`, exact owner/current-user equality, a present DACL,
stable root and full ancestor identities, no shared writer/unknown ACE/reparse,
and every effect/repair flag false.

The persistent migration read-back carries `record_version`, `record_type`,
`migration_id`, the closed migration `receipt`, `manifest_sha256`,
`exact_snapshot_verified`, the fixed false active-view/Profile/activation/
Timeline/Resolve fields, and `snapshot_readback_sha256`. Its nested receipt
also binds the initial and final security attestation hashes, exact install
instance/descriptor/owner coordinates, counts, manifest, source identity,
preservation flags, and terminal receipt hash. PL-A accepts it only as
non-admitting archival evidence; it never treats migration as learning.

## D2 CA-B source-binding mapping

`ConnectorSourceBindingReadiness.to_dict()` currently exposes:

`schema_version`, `message_type`, `task_owner`, `binding_id`, `plan_sha256`,
`target_install_instance_id`, `target_descriptor_sha256`,
`target_owner_manifest_sha256`, `security_attestation_sha256`,
`migration_snapshot_readback_sha256`, `preference_source_readback_sha256`,
`preference_envelope_sha256`, `task058_public_readiness_sha256`,
`task058_public_readiness_version`,
`task058_public_v1_source_not_bound_baseline_validated`,
`private_v2_persistent_receipt_accepted`, `profile_id`, `profile_version`,
`profile_sha256`, `profile_publish_status`, `state`,
`production_profile_source_bound`, `profile_view_readback_verified`,
`real_adapter_e2e_verified`, `connector_config_modified`,
`connector_enabled`, `activation_authorized`,
`learning_adoption_authorized`, `automatic_promotion_authorized`,
`timeline_mutation_authorized`, `resolve_write_authorized`,
`external_effect_authorized`, and `binding_sha256`.

The candidate's only admissible state is
`SOURCE_BOUND_ACTIVATION_BLOCKED`. Public TASK-058 readiness v1 is used as an
honest source-not-bound baseline; private v2 is never a persistent receipt.
Profile source/view read-back is true, while real adapter E2E, config change,
enablement, activation, learning, promotion, Timeline, Resolve, and external
effects remain false.

## D2 CA-C Human/config-history mapping

`ConnectorActivationTransactionReceipt.to_dict()` currently exposes:

`schema_version`, `message_type`, `task_owner`, `transaction_id`,
`target_install_instance_id`, `source_binding_sha256`,
`human_evidence_sha256`, `adapter_e2e_sha256`, `revision`, `enabled`, `action`,
`state`, `history_sha256`, `config_readback_sha256`,
`one_shot_human_evidence_consumed`, `repository_default_enabled`,
`external_skill_config_modified`, `learning_adoption_authorized`,
`automatic_promotion_authorized`, `timeline_mutation_authorized`,
`resolve_write_authorized`, and `transaction_sha256`.

The candidate proves only synthetic-temp disabled history. A deactivation uses
an exact <=24-hour Human evidence identity, one-shot consumption, CAS revision,
append-only hash chain, atomic BVP config replace, and exact disabled read-back.
Repository default remains false and the installed SKILL config is not changed.

An activation receipt with `enabled:true` is not currently mintable: synthetic
adapter observations are ineligible and the real installed E2E admission path
is deliberately unavailable. Therefore PL-A must classify the current CA-C
candidate as `CA_C_REAL_E2E_MISSING` plus `DEPENDENCY_NOT_CANONICAL`; it must
not promote a disabled synthetic receipt into activation authority.

## Independent gate checklist

Each gate is re-evaluated independently from an exact immutable identity:

1. **D0** — corrected TASK-063 commit is reachable from current canonical
   `main`; six hosted OS/Python tests and security checks pass at that main;
   descriptor/owner/discovery/receipt and ancestor/hardlink/DACL read-back are
   current for exactly one installed instance.
2. **D1** — PP-A, PP-B, and PP-C are reachable from canonical `main`; exactly
   one current promoted source read-back validates byte-for-byte against the
   closed schema and no second source/revision is current.
3. **D2** — corrected readiness wording and CA-A/B/C are reachable from
   canonical `main`; security, migration, source binding, Human one-shot
   history, disabled rollback, and real installed public-safe adapter E2E have
   exact receipts for the same instance and source binding.
4. **PL-A admission** — only after all three gates pass, re-read TASK-058
   exact3 and the installed config identity, reject fixed ProgramData and
   multi-install ambiguity, and compile a public-safe readiness result.

Any missing, stale, tampered, unknown-version/issuer, duplicate-current,
cross-instance, cross-revision, reparse/hardlink, unsafe-DACL, or body/hash
mismatch yields `BLOCKED`, sorted reason codes, and all effect authorities
false. No dependency candidate or CI pass alone can yield
`READY_FOR_CONFIG_SYNC`.

## Current conclusion

The actual candidate field map is now closed enough for deterministic PL-A
fixture design, but the implementation gate is not open. Current overall state
is `BLOCKED`; config sync, adapter execution, connector activation, learning,
Timeline, Resolve, Release, Deploy, and Production authorization are all false.

## Focused integration evidence

- Windows Python 3.12, TASK-063 installation/main-installer contract plus PP-C
  and CA-A through CA-C: `98 passed / 1 non-Windows skip`.
- WSL2 Ubuntu, PP-C and CA-A through CA-C: `62 passed / 5 Windows-only skips`.
- WSL2 discovery of `powershell.exe` made the TASK-063 Windows-only acceptance
  harness attempt to pass a Linux-form `.ps1` path to Windows PowerShell. Its
  seven parameter cases ended in CP932/UTF-8 decode errors. This hybrid harness
  is recorded as environment-N.C., not pass; the same TASK-063 contract passes
  in the native Windows run and all six hosted Ubuntu/Windows jobs at PR #451.
