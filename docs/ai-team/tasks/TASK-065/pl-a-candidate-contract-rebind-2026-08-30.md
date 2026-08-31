# TASK-065 PL-A Candidate Contract Rebind

Date: 2026-08-30
Atomic Unit: PL-A admission preparation
State: `DEPENDENCY_CANDIDATES_INTEGRATED / CANONICAL_GATES_OPEN / EFFECT0`

## Purpose and effect ceiling

This checkpoint replaced only the PP-C and CA-C placeholders in the earlier
PL-A design freeze with source-backed candidate field mappings. It did not
declare D0, D1, or D2 complete. At this rebind checkpoint, the candidates
remained stacked Draft PRs and remote `main` was
`160c9569673fbf65a28b0f95eeb44c5b0111584f`. Current dependency state is
recorded separately in `dependency-currentness-reconciliation-2026-08-31.md`.

No TASK-065 source, schema, test, installed SKILL config, native config,
adapter, learning, Timeline, Resolve, Release, Deploy, or Production effect is
authorized or performed by this rebind.

## Exact candidate heads and hosted state

| Gate | Candidate | Exact current PR head | Fresh state at 2026-08-31 read-back |
|---|---|---|---|
| D0 | TASK-063 safety closure PR #451 | `8fd17ed23242d34102908a0ce19fe8ce68b7cc9f` | PR closed/unmerged; exact commit is nevertheless an ancestor of current `main` |
| D1 | PP-A PR #452 | `0c00676e2da055b3b4b0ee00ea67ef1246ea49dc` | merged; exact head is an ancestor of current `main` |
| D1 | PP-B PR #456 | `d75851c12faee8c9abe263a21a36ad1aaf33f302` | merged; exact head is an ancestor of current `main` |
| D1 | PP-C PR #457 | `78b462b4d52f0728a20cfd4951ac15f97033c8a1` | merged; exact head is an ancestor of current `main` |
| D2 | readiness wording PR #454 | `0549feaa162e75d26264e38cd91fa234dfb96c31` | merged; exact head is an ancestor of current `main` |
| D2 | CA-A security PR #458 | `fa2f056bae6927889b5710c6eb63e26b792a92af` | merged; exact head is an ancestor of current `main` |
| D2 | CA-A migration PR #459 | `75ef138cd5b9361f9016d926a4db51f585b6fd29` | merged; exact head is an ancestor of current `main` |
| D2 | CA-B PR #460 | `fdacaf90fddc47c2675716223bb023f66c5313af` | merged; exact head is an ancestor of current `main` |
| D2 | CA-C PR #461 | `64b780cc567e98252bb9d3ba526153158a757e3a` | merged; exact head is an ancestor of current `main` |

**SUPERSEDED historical CI note:** the original shared `changelog-and-version`
failure was not waived or reported as pass, but it no longer describes these
PR states. Fresh remote `main` is
`35cdf1ad475633dcf035e0616e979b5a8fde0c88`, and every exact head above is its
ancestor. This proves source integration only; it does not satisfy the new
authority/currentness corrective Gates or completion receipts. TASK-065 does
not own the shared changelog. A hosted temporary directory whose
owner differs from the current Windows user remains fail-closed as
`WRONG_OWNER`; the real fixture now records that host as environment-N.C.
rather than weakening the production ownership rule.

A subsequent DEV-4 boundary review found that owner/current-user/count equality
alone did not detect a different still-secure DACL or root identity between
plan and write read-back. CA-A migration now pins the complete initial
attestation hash, CA-B carries the same hash in its sealed plan, and CA-C
compares complete before/after attestation hashes. Focused negative tests change
only the secure DACL and prove rejection; owner policy was not relaxed.
CA-C pinned JSON read-back also compares mode, reparse attributes, and link
count before/after/path and rejects a second hardlink name.

## D0 TASK-063 discovery mapping

**SUPERSEDED CURRENT RULE:** the public discovery fields below are necessary
audit coordinates only. They do not prove the current installed Product,
unique current registration, lifecycle continuity or matching config/history.
Packaged installer CLI `discover` is effectful and prohibited from PL-A
admission. Current private fields, results and PLA-I01-I17 are in
[`pl-a-current-installation-field-delta-2026-08-31.md`](pl-a-current-installation-field-delta-2026-08-31.md).

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

The TASK-063 source corrections are now canonical on `main`, including the
publication race/path-safety closure. D0 nevertheless remains N.C. until a new
post-correction installed provision/repair/upgrade read-back proves one pinned
descriptor/owner generation, secure operation locking, identity-safe
publication/rollback, focused Windows negatives, and a canonical completion
receipt. The future receipt must also come from strict bounded parsing of the
same pinned descriptor/owner/readback/journal/rollback-preimage bytes, with raw
hash, canonical parsed hash and physical identity bound together. Duplicate or
ambiguous JSON is preserved with provision/repair/rollback effect zero.
Pre-correction fixture hashes are not reusable as current PASS.

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
activation, learning-admission, or Production Profile-write authority. The
candidate source is present on `main`, but D1 remains N.C. pending independent
DEV-4 completion and a trusted same-open-snapshot source operation. Public
`PromotedPreferenceSourceRead`/`ProfileSourceBinding` tokens and self-hashes are
audit data only and cannot mint the private one-use Production publish
capability required by the current acceptance contract. D1 also requires a
strict bounded parser for both encrypted outer document and decrypted history,
binding outer/ciphertext/decrypted hashes, physical identity, native DPAPI
backend/user/session and parsed revision/head in one private snapshot. Caller
pre-parsed mappings and ambiguous JSON create no source/Profile authority.

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

The public persistent migration read-back carries `record_version`, `record_type`,
`migration_id`, the closed migration `receipt`, `manifest_sha256`,
`exact_snapshot_verified`, the fixed false active-view/Profile/activation/
Timeline/Resolve fields, and `snapshot_readback_sha256`. Its nested receipt
also binds the initial and final security attestation hashes, exact install
instance/descriptor/owner coordinates, counts, manifest, source identity,
preservation flags, and terminal receipt hash. It is audit projection only:
`BridgeMigrationReadback` is publicly constructible using the module-global
`_READBACK_SEAL` and recomputable hash, while TASK-061 currently checks only
those fields and target values. PL-A accepts it only as non-admitting archival
display evidence. Currentness requires the trusted TASK-061 Product operation
to resolve the plan-bound migration ID and pinned-read the exact terminal CA-A
journal plus snapshot manifest/tree/physical identities into a private one-use
capability. It never treats the public object or migration itself as learning
or Profile/config authority. `BridgeMigrationPlan.confirmation()` is likewise
deterministic display text, not migration authority. CA-A execution requires a
trusted durable single-use `MIGRATE` ticket bound to exact plan, instance,
source/expected target state, user/session/build, expiry and budget; entry burns
it IN_FLIGHT. Terminal journal/manifest/receipt reads use the strict same-
snapshot authority JSON parser rather than permissive `json.loads`.

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

The serialized candidate state is `SOURCE_BOUND_ACTIVATION_BLOCKED`.
**SUPERSEDED:** public TASK-058 readiness v1 must not be used as an admitting
source-not-bound baseline, and private V2/hash-shaped readiness is not a
persistent Product receipt. The public factory accepts caller state strings and
E2E/default-config booleans, while TASK-061 validates only their serialized
values. Both versions are audit/display projection with
`authority_created:false`. PL-A instead requires a durable
`TASK058_BASELINE_READBACK` minted by a trusted Product reader from exact
canonical release/package and installed bytes plus executed operation receipts,
freshly bound to TASK-063 instance, TASK-060 source and the operation plan.
`ConnectorSourceBindingReadiness` remains publicly constructible with a
module-visible sentinel and computable hash. A trusted native-backend-fixed
Product operation must pinned-read the actual baseline/CA-B/Profile receipts and
bind them with Human and real-E2E currentness into a private single-use apply
capability. Until those corrections complete, every config, enablement,
activation, learning, promotion, Timeline, Resolve and external effect remains
false. `ConnectorSourceBindingPlan.confirmation()` is deterministic display
text only. CA-B publication separately consumes a trusted one-shot `BIND`
ticket with the same exact instance/plan/source/target/user/session/build/
expiry/budget binding; CA-A tickets cannot be reused for CA-B. Trusted baseline
and Profile durable reads must pass the same strict authority JSON boundary.

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

The candidate exercises synthetic-temp disabled-history semantics only.
Repository default remains false and the installed SKILL config is not changed.
Its intended one-shot Human/CAS/hash-chain checks do not close Production
authority: Human evidence, CA-B readiness, and E2E readback are public
dataclasses backed by module-visible sentinels and computable hashes, and the
activation lock/config publication still has physical-identity races. The
public synthetic admission function rejects real observations, but direct
construction can recreate a non-synthetic-looking object; that closed function
therefore is not an authority boundary.

Production apply also cannot accept caller `now`, timestamp or selectable clock.
Challenge issuance, Human receipt, apply entry, atomic consume and final read-
back share a Product/OS-owned time domain bound into the one-use capability.
Persisted monotonic/boot/session currentness plus bounded UTC must prevent
rollback, forward jump, suspend/resume, timezone change or restart from extending
expiry, and `occurred_at` is Product-authored. CA-C config/history/challenge/
consume records use strict bounded same-snapshot JSON; ambiguity causes no
rewrite, repair, deletion, config or history effect.

PL-A must classify this candidate as
`CA_B_READINESS_HUMAN_E2E_AUTHORITY_FORGEABLE`,
`CA_C_REAL_E2E_GATE_PENDING`,
`CA_C_SECURE_ACTIVATION_WRITER_PENDING`, and
`DEPENDENCY_COMPLETION_N.C.`. It accepts none of the three public objects as
apply authority and cannot promote any disabled/synthetic receipt into
activation evidence.

## Independent gate checklist

Each gate is re-evaluated independently from an exact immutable identity:

1. **D0** — corrected TASK-063 source is reachable from current canonical
   `main`; a new post-correction hosted/Windows completion receipt proves secure
   provision/readback locking, one pinned descriptor/owner generation,
   identity-safe rollback/publication, and current ancestor/hardlink/DACL
   evidence for exactly one installed instance.
2. **D1** — PP-A, PP-B, and PP-C are reachable from canonical `main`; exactly
   one current promoted source read-back validates byte-for-byte against the
   closed schema and no second source/revision is current.
3. **D2** — corrected readiness wording and CA-A/B/C are reachable from
   canonical `main`; CA-A migration and CA-C config writers satisfy the secure
   physical-identity fault matrix; a trusted native-backend-fixed operation
   consumes non-forgeable CA-B, Human-challenge, and real-installed E2E
   capabilities; all exact receipts remain current for the same instance,
   source binding, config revision, Profile and operation plan.
4. **PL-A admission** — only after all three gates pass, re-read TASK-058
   exact3 and the installed config identity, reject fixed ProgramData and
   multi-install ambiguity, and compile a public-safe readiness result.

Any missing, stale, tampered, unknown-version/issuer, duplicate-current,
cross-instance, cross-revision, reparse/hardlink, unsafe-DACL, or body/hash
mismatch yields `BLOCKED`, sorted reason codes, and all effect authorities
false. No dependency candidate or CI pass alone can yield
`READY_FOR_CONFIG_SYNC`. **SUPERSEDED CURRENT RESULT:** a coherent installation
read returns only audit-state `CANDIDATE_CURRENT_INSTANCE`; it is not config
authority. See the current field-delta document above.

## Current conclusion

The actual candidate field map is now closed enough for deterministic PL-A
fixture design, but the implementation gate is not open. Current overall state
is `BLOCKED`; config sync, adapter execution, connector activation, learning,
Timeline, Resolve, Release, Deploy, and Production authorization are all false.

## Focused integration evidence

- Windows Python 3.12, TASK-063 installation/main-installer contract plus PP-C
  and CA-A through CA-C: `99 passed / 1 non-Windows skip`.
- WSL2 Ubuntu, PP-C and CA-A through CA-C: `63 passed / 5 Windows-only skips`.
- WSL2 discovery of `powershell.exe` made the TASK-063 Windows-only acceptance
  harness attempt to pass a Linux-form `.ps1` path to Windows PowerShell. Its
  seven parameter cases ended in CP932/UTF-8 decode errors. This hybrid harness
  is recorded as environment-N.C., not pass; the same TASK-063 contract passes
  in the native Windows run and all six hosted Ubuntu/Windows jobs at PR #451.
