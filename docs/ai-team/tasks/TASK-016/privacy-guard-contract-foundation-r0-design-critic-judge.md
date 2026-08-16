# TASK-016 Privacy Guard Contract Foundation R0 — Design / Critic / Judge Evidence

- Date: 2026-08-17
- Authority: `BVP-AUTH-20260817-TASK016-PRIVACY-GUARD-CONTRACT-R0-01`
- Base: `main@98d6eac5a977b141568cbf2fad7fe154032236c3`
- Branch: `codex/task-016-privacy-guard-contract-r0`
- Scope: pure, body-free metadata validation and classification only
- Effect authority: none

## 1. Authority and ownership boundary

This unit owns the TASK-016 metadata contract, schema, mirror, pure evaluator and focused synthetic tests. It does not own or reproduce Asset, Transcript/SRT, Narration, resource monitoring, audit, retention/delete or production truth.

| Canonical dependency | Exact source blob at start | Use in TASK-016 |
|---|---|---|
| TASK-003 Asset module | `7fd5340923c4844bed6eeef8c8e92ef409ef49ff` | immutable reference only |
| TASK-003 Asset schema | `d6016ed2eec9e00c3bd828f7466fa3ea55c78f61` | coordinate compatibility evidence |
| TASK-006 subtitle module | `422567c16b7c6c3b76c0b655b393eddd1ce823d6` | immutable Transcript/SRT reference only |
| TASK-006 transcript-manifest schema | `cb0db145a77e34abd48259da2146a789c0ed5ff0` | coordinate compatibility evidence |
| TASK-014 narration module | `336d93a95325b768eb4c56488033921383f42666` | body-free narration revision reference only |
| TASK-014 narration schema | `14caaffb0c8b2efa022219110344c6be557de9a8` | dependency evidence |
| TASK-020 resource module | `1e1c70e078c322f5d2fb59ddbd921bd6f5a7585b` | admission Evidence reference only |
| TASK-020 resource schema | `1e900f4480d08fe598f5ea1ce76e3a325f1bc5e0` | dependency evidence |
| TASK-037 candidate audit | `794222871bd970714b823f7a44ca2962ebe4fd73` | audit coordinate reference only |
| TASK-038 audit application | `41a6f7a560e6d1701cb293c59dbb67b73d2efa0a` | audit coordinate reference only |
| TASK-037 trace Evidence | `dcb91968fad2bb0f5e8cd63754ff192be9c56840` | append-only trace reference only |
| shared Evidence helper | `1fde6a38e7b22062aeabf9c4a761e0639047a703` | no mutation or duplication |

TASK-017 remains the owner of retention/delete decisions and effects. TASK-021 may consume the future public projection; it cannot infer private coordinates or a publication approval. Human consent, rights, license and publication authority remain external Gates.

## 2. Contract model

The canonical root types are:

1. `PrivacyPolicyRevision`
2. `PrivacyInputBinding`
3. `PrivacyDetectorProfileBinding`
4. `PrivacyEvidenceClaim`
5. `PrivacyEvaluationReceipt`
6. `RedactionPlanRevision`
7. `HumanPrivacyReviewBinding`
8. `NotificationDecision`
9. `PrivacyInvalidationReceipt`
10. `PrivacyPublicationGateBinding`

The ordering boundary is acyclic:

`Policy + Input + Detector -> Claim -> Evaluation -> Redaction proposal -> Human review -> Notification/Publication metadata`

Invalidation references an issued record and never deletes or rewrites it. Detection fact is not policy decision; policy decision is not redaction; redaction proposal is not mutation; Human review is not notification sending or publication; invalidation is not deletion.

## 3. Fail-closed rules

- Only exact BOUND external rights/Consent bindings with current decisions can support a non-UNKNOWN result.
- Every policy-enabled finding kind requires exactly one current claim for every exact coordinate.
- `NOT_SUPPORTED`, `INSUFFICIENT_INPUT`, `ERROR`, `UNKNOWN`, partial coverage, stale claims, unadmitted detector, missing claim or unresolved reference never becomes PASS or zero.
- Blocking facts take precedence over UNKNOWN; UNKNOWN over review; review over PASS.
- Canonical hashes cover each whole record body. Unknown fields and tampered hashes are rejected.
- Revision 1 has a null parent; later revisions require an exact parent digest.
- Ordered arrays are unique and capped: coordinates 128, claims/operations 512, reason codes 64.
- Input and Claim records require `body_persisted=false`; body, absolute path and credential-like references are rejected.
- `RedactionPlanRevision` is proposal-only with every mutation flag false.
- Human review accepts `reviewer_kind=HUMAN` only and exact policy/input/evaluation/plan bindings.
- Notification cannot carry a body, authorize sending or report sent.
- Publication output is only `READY_FOR_EXTERNAL_HUMAN_GATE`, never publication authority; effect flags remain false.
- Invalidation blocks or stales future use without physical deletion.
- Public projection suppresses coordinates, Asset/private Evidence/model refs, matched-content hashes and low-count details.

## 4. Pure API surface

Allowed operations are parse, canonical hash, validation, deterministic policy classification, invalidation-aware publication classification and public/private projection. The static effect map fixes filesystem I/O, detector execution, canonical mutation, redaction, notification, publication, retention/delete, provider/model runtime and Release/Deploy/Production to `false`.

There is no body reader, detector/analyzer, filesystem adapter, sender, publisher, delete API, provider/network client, scheduler or runtime entry point.

## 5. Synthetic acceptance inventory

| Acceptance | Focused test |
|---|---|
| schema/mirror equality and all 10 roots | `test_schema_mirror_is_byte_exact_and_accepts_every_root_type` |
| deterministic hash/tamper | `test_canonical_hash_is_deterministic_and_tamper_fails` |
| complete negative Evidence PASS | `test_complete_not_detected_evidence_is_pass` |
| unsupported/error/unknown fail closed | `test_unknown_or_unsupported_fact_never_becomes_zero_or_pass` |
| missing/stale Evidence UNKNOWN | `test_missing_claim_coverage_and_stale_claim_fail_closed` |
| severity classification | `test_detected_finding_is_policy_classified` |
| rights/Consent/detector admission | `test_rights_consent_and_detector_admission_are_fail_closed` |
| exact input/coordinate/profile lineage | `test_claim_must_bind_exact_input_coordinate_and_detector` |
| proposal-only redaction | `test_redaction_plan_is_proposal_only_and_never_mutates` |
| Human reviewer/plan binding | `test_human_review_is_exact_and_ai_cannot_issue_it` |
| notification/publication metadata only | `test_notification_and_publication_are_metadata_gates_only` |
| invalidation without delete | `test_invalidation_blocks_publication_without_deleting` |
| public privacy suppression | `test_public_projection_suppresses_private_coordinates_hashes_and_counts` |
| path/credential refs rejected | `test_body_path_or_credential_like_reference_is_rejected` |
| caps/duplicates/unknown fields | `test_caps_duplicates_and_unknown_fields_are_rejected` |
| no I/O/analyzer/effect surface | `test_static_surface_has_no_io_detector_or_effect_capability` |

## 6. Validation record

- Python compile: PASS
- Public schema / packaged mirror byte equality: PASS
- Focused tests: 23 PASS
- Windows full regression: 1495 PASS / 1 platform skip
- WSL full regression: 1495 PASS / 1 platform skip
- Hosted checks: pending Draft PR

## 7. Critic pass 1 — Builder / compatibility

- Canonical roots, enums and hashes are mirrored between schema and runtime validators.
- Existing dependencies are referenced, not modified or reimplemented.
- Coordinates bind immutable Asset/checksum/revision and optional Transcript/range coordinates.
- Schema/runtime reject extra fields and state-dependent fabricated bindings.
- Initial finding: Human `APPROVE_AS_IS` and `APPROVE_REDACTION_PLAN` needed explicit plan-digest nullability. Corrected and covered by tests.
- Residual Critical / High / Medium: 0 / 0 / 0.

## 8. Critic pass 2 — Security / privacy compatibility

- Public output excludes coordinates, source identities, matched-content digests, detector/model refs and counts.
- Credential-like refs, absolute paths, traversal and body fields are rejected.
- UNKNOWN and unsupported facts cannot become numeric zero or PASS.
- No execution authorization, sender, body access, storage, provider/network or destructive API exists.
- Invalidation is append-only Evidence and cannot delete retained data.
- Residual Critical / High / Medium: 0 / 0 / 0.

## 9. Judge

Result: `READY_FOR_DRAFT_PR_HOSTED_VALIDATION`.

The pure contract passed local Windows/WSL regression and is ready for exact6 Draft PR hosted validation. It does not authorize or claim PII detection, redaction, notification, publication, retention/deletion, Release/Deploy or Production. Canonical merge requires exact6 path scope, all hosted checks terminal SUCCESS, dependency drift 0 and residual Critical/High/Medium 0/0/0.
