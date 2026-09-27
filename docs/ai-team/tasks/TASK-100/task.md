# TASK-100 — Local Voice Model / Runtime Catalog Admission successor

- Status: `LVC_D_R0_DESIGN_ACCEPTED / LVC_I_PURE_IMPLEMENTATION_ELIGIBLE / CANONICAL_INTEGRATION_PENDING`.
- Governance: DEV-4 FOUNDATION CRITICAL (cross-owner model/runtime admission).
- Owner intent: 2026-09-27 expression Master WAV remaining-Task/detail-design request.
- Responsibility predecessor: TASK-013 closed creative/catalog foundation; historical Task is not reopened.
- Coordinator: TASK-073 delivery plan. Canonical responsibility: body-free local voice catalog candidate, preserving the existing Product catalog.
- Delivery owner: this voice-integration thread `01a054d9-2cf9-71e2-a486-351727c13150`, by the Owner's explicit two-contract takeover instruction. Own design -> implementation -> tests/review -> canonical handoff; no reassignment gate. Implementation intent is authorized, but exact files/unit and native authority must be bound before effects.
- Allocation serialization: ID100 is unused in bound main `e41110c8`; fresh ID/lock audit before integration. No source/runtime authority is created.
- LVC-D R0 design: `lvc-d-local-voice-catalog-admission-contract-r0.md`.
- Allowed for LVC-D R0: this task definition and the LVC-D design. No source/runtime effect.
- Proposed LVC-I exact4 remains source + canonical schema + byte-identical package mirror + focused test. It becomes implementation-eligible only after independent LVC-D acceptance recorded in this Task.

## Required design

Publish/query one pinned GPT-SoVITS C04 local voice candidate through the existing canonical catalog, not a second model store. The proposed `LocalVoiceCatalogCandidateV1` binds candidate ID/revision/digest, engine/runtime code/build identity, exact model pair identity, model-card/license/rights identity, capability-map version, current installed/runtime admission and producer readback identity. Public projections contain opaque references only; no private path, model body, reference audio/text, secret or load lease. Queryability/selection eligibility is not load/inference permission.

### Exact existing integration surface

At the bound baseline, `local_audio_model_inventory.py` provides `LocalAudioModelObservation`, `compile_local_audio_model_inventory` and `project_public_voice_profile_models`. TASK-100 supplies a strictly validated observation/receipt adapter to these existing functions. For narration use `purpose=NARRATION`, `workload=None`, `route_id=None`; do not create a SFX/MUSIC `ModelRoute` or replace TASK-028's generic capability catalog. TASK-074 already binds `local_audio_model_inventory_revision_sha256` and `local_audio_model_inventory_entry_sha256`; preserve this route-selection seam. The proposed candidate supplements provenance/readback validation, not inventory ownership.

### Proposed closed input/output contract for LVC-D

Input is one private, verified producer-evidence set: exact046 profile/model/Consent/rights/H4,101 imported custody,063/036 installed binding,066 compute/network and075 execution-port availability. Custody is a closed tagged union: `EXISTING_MODEL_IMPORT` requires TASK-101 import/readback version/digest, while the separately reserved `TRAINING_TERMINAL` requires TASK-084 terminal/readback version/digest; incompatible fields/issuer/version are rejected, not aliased. The present outcome uses only the101 branch. Pure code receives only typed metadata/digests, never physical handles or bodies. Trusted evidence authentication/currentness is an injected producer responsibility, not established by JSON self-hash. Fixture evidence must be typed `FIXTURE_ONLY`, remain non-admitted and cannot feed a live selection.

Candidate fields: `contract_version`, `record_type`, `candidate_id`, positive `revision`, nullable `predecessor_sha256`, `provider_id`, `engine_id`, `model_id`, `runtime_build_sha256`, `model_pair_sha256`, exact `sovits_sha256`, `gpt_sha256`, `voice_profile_revision_sha256`, `model_candidate_revision_sha256`, typed `custody_provenance`, `consent_currentness_sha256`, `h4_approval_sha256`, `license_evidence_sha256`, `installed_binding_sha256`, `capability_map_sha256`, `execution_port_id`, `producer_readback_set_sha256`, `observation_source`, `observed_at`, `expires_at`, `candidate_sha256`. `custody_provenance` carries branch-specific receipt/readback fields, not a generic hash that erases the issuer. All digest values use canonical `sha256:` plus 64 lowercase hex; timestamps use UTC with exact parser rules; opaque IDs are bounded ASCII identifiers, not paths/URLs. Unknown fields, duplicate JSON keys, boolean-as-integer, nonfinite values, ambiguous nulls and unrecognized version/source are rejected. Ranges/string limits and canonical JSON domain-separation preimage must be frozen with schema/test vectors in LVC-D, not assumed by a caller.

Output has exactly one of `ADMITTED_CATALOG_CANDIDATE`, `BLOCKED_CATALOG_CANDIDATE`, `FIXTURE_ONLY_CANDIDATE`, with reason-code tuple, existing inventory observation/snapshot digest and candidate digest. `execution_authorized=false` always. `CURRENT/INSTALLED/READY/CONFIRMED/SCRIPTABLE` are projected only from fresh corresponding verified receipts; missing/stale/revoked/unknown observation is blocked, never upgraded because a hash matches. Profile `generation_ready` from the legacy projection denotes eligibility only and must not be presented as live permission by 073/036.

TASK-046 owns lineage/current H4/Consent; TASK-101 owns protected existing-model import custody/load lease on this path; TASK-084 keeps its separate training-terminal custody route. TASK-074 owns selected route/private reference; TASK-066 owns compute; TASK-014 owns narration and capability translation. Catalog consumes their required fresh approved evidence but cannot issue approval, fabricate currentness or silently default to a different model/reference. External Stable v2.0.1 documentation, matching filenames/hashes or C04 server health alone do not satisfy admission.

## Atomic Units / exit

1. LVC-D: read-only fresh catalog audit. If exact current C04 candidate already satisfies the obligation, persist proof and close as no-change; record reduced remaining count in a new delivery revision. Otherwise freeze canonical extension/query schema and private/public split; independent review.
2. LVC-I: proposed exact implementation files are `src/ai_video_production/task100_local_voice_catalog_admission.py`, `schemas/task100-local-voice-catalog-admission.schema.json`, its `src/ai_video_production/schema_resources/` mirror and `tests/test_task100_local_voice_catalog_admission.py`. New pure adapter imports existing inventory functions without modifying them. LVC-D independent acceptance/fresh main audit binds this exact4 before implementation; any discovered need to modify existing catalog/074/073 is a separate owning-unit exact-files amendment.
3. LVC-C: exact TASK-074/014/073 consumer readback, stale/runtime/rights/version/cross-model rejection and separately authorized native installed-identity validation.

Exit: fresh body-free candidate/readback proves exact pair, runtime/license/capability and accepted query contract; no duplicate inventory, no silent fallback, no automatic download/load. No changes to external Voice Lab/model repositories or final TASK-013 history. Training, inference, playback, Asset/Timeline/Export, acquisition, paid/cloud, Release/Deploy/Production remain outside authority.

See [delivery plan](../TASK-073/expression-master-wav-delivery-plan-r0.md) for scope, gates and order.

## LVC-D R0 independent decision

- Accepted exact design SHA-256: `26e39ea2431f2e7b336dad1c467b3b654b2ea0f2395a2fe5e9d5c22e852b0df8`.
- Independent DEV-4 Critic/Judge: `PASS`, final C/H/M/L `0/0/0/0` after two bounded correction cycles.
- Independent design Tester: `PASS`; frozen candidate vector independently reproduced.
- Closed findings: fixture/unverified bypass through the legacy inventory, assessment identity/time/currentness binding, imported-custody proposal separation, strict parser/output/source/reason contract, and replay/currentness boundary.
- This accepts LVC-D and permits only the exact five LVC-I paths named by the design. Implementation/native/live admission remains unverified; LVC-C and all external effects remain separate.
