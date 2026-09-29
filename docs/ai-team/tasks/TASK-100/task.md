# TASK-100 — Local Voice Model / Runtime Catalog Admission successor

- Status: `LVC_D_R0_DESIGN_ACCEPTED / LVC_I_R0_PURE_IMPLEMENTATION_ACCEPTED / LVC_C1_SOURCE_ACCEPTED / LVC_C2_D0_DESIGN_IN_REVIEW / LVC_C2_NATIVE_BLOCKED / CANONICAL_INTEGRATION_PENDING`.
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

## LVC-I R0 implementation decision

- Pure implementation payload: `src/ai_video_production/task100_local_voice_catalog_admission.py`, canonical schema and byte-identical package mirror, plus `tests/test_task100_local_voice_catalog_admission.py`. This Task record is the allowed fifth completion carrier; no existing inventory, TASK-074, TASK-073 or runtime source was modified.
- Implementation SHA-256: `6685d21fed499682331aee81c19de68ddecdf6dc47443a0fe3e685667ac02f84`.
- Canonical/package schema SHA-256: `639404a8650c9285413a623c5065d70a8ccbdf502b3a52f0d8a515fc817e6d5b` (byte-identical).
- Focused test source SHA-256: `2badfb10968fbe97b793fb1be8541d6c3d8c0a869241c44fcfa3962f69232860`.
- Primary focused + direct dependency regression: `PASS`, 120 tests. Independent Tester: `PASS`, 63 tests plus 61 in-memory adversarial assertions; schema self-validation/mirror, five ECMAScript patterns and nine calendar vectors also passed.
- Independent DEV-4 Critic/Judge after one bounded correction cycle: `ACCEPT`, final C/H/M/L `0/0/0/0`. Closed findings were typed-record constructor/compiler validation bypass, missing cross-field schema conditions/calendar grammar, and excessive-depth `RecursionError` normalization.
- The implementation is deterministic, body-free and effect-free. It creates no file/model/runtime/network/process/audio effect and grants no load, inference, replay or consumer-live authority. Native installed-model identity, private audio, LVC-C consumer currentness/readback and canonical Product integration remain `NOT_CONFIRMED` and outside this unit.

## LVC-C1 source consumer-readback authority — 2026-09-29

After TASK-102 PMST-I2 merge closure, the Owner instructed `次へ`. Together with the existing TASK-100 delivery-owner/implementation intent, this binds the source-only LVC-C1 Atomic Unit in [the C1 contract](lvc-c1-consumer-readback-contract-r0.md). C1 may add only the exact Task record, contract, source, canonical/package schema, focused test and external Evidence paths listed there.

C1 must bind accepted TASK-100 admission to exact TASK-074 fine-tuned selection/currentness and TASK-014 non-executing preflight. It may return evidence-only `consumer_live_eligible` for the existing Owner Human Gate, but must keep execution/load/runtime/inference/body/path/resource effects false or zero. Existing TASK-014/TASK-074/catalog sources are read-only dependencies. Native installed identity, TASK-101 private import/load lease, real model access, inference, private audio, Project/Asset/Timeline mutation, Release, Deploy and Production remain outside this authority.

## LVC-C1 Builder checkpoint — 2026-09-29

- Added one pure consumer compiler/readback, a strict canonical schema with byte-identical package mirror, and focused adversarial tests. Existing TASK-014, TASK-074 and TASK-013 catalog source remain unchanged.
- Positive eligibility requires exact TASK-100 candidate/assessment/admission/inventory lineage, fine-tuned TASK-074 selection plus runnable currentness, and a READY non-executing TASK-014 preflight. Exact Project, voice-profile, model-candidate, installed-binding, license, model-pair, engine, producer-readback and validity-time coordinates are rebound at the consumer boundary.
- `consumer_live_eligible=true` is evidence-only eligibility for the existing Owner Human Gate. Authority/load/runtime/model/inference/body/path flags remain false and `resource_effect_count=0`.
- TASK-014's publicly constructible historical preflight dataclass is always reparsed through its producer parser, closing hand-built decision/classification bypass.
- Initial focused execution was `24 PASS / 1 FAIL`; the sole failure was an invalid schema file caused by a patch-marker generation error, not a compiler assertion. The schema and mirror were replaced before further verification.
- Final C1 focused execution: `25 PASS`. TASK-100 admission/C1 plus direct TASK-074 and TASK-014 regression after constructor-bypass hardening: `130 PASS`.
- Resolved OS-temp roots: `C:\Users\user\AppData\Local\Temp\bvp-task100-lvc-c1-20260929-001` through `-004`. No task-owned path was created at a drive root.
- Filesystem/model/runtime/process/network/audio/Project/Product effects: none. Native installed identity, TASK-101 private import/load lease, inference, private audio, Release, Deploy and Production remain prohibited.
- DEV-4 independent Critic and Tester review is required before C1 acceptance.

## LVC-C1 Recovery R1 checkpoint — 2026-09-29

The frozen Builder commit `436b9c1279768fe7047d6bc3ca58b975957b94d9` received independent `REVISE`: Critic C/H/M/L `0/3/1/0`; Tester `FAIL / REVISE` C/H/M/L `0/2/0/1`. The accepted correction scope remains inside the exact C1 source/test/docs files.

Recovery R1 closes the confirmed findings:

- final trusted evaluation now rechecks TASK-074 Consent expiry and rejects the exact boundary and later values;
- TASK-100 Consent is rebound to TASK-074 selection, and every selection/currentness duplicated coordinate is compared exactly, including Project manifest, Consent, ModelCandidate currentness and timestamps;
- the public compiled-admission wrapper must contain canonical nested types and must equal a fresh candidate/assessment recompilation, preventing forged admission/inventory dictionaries;
- TASK-014 capability probe is rebound to the TASK-100 capability-map digest;
- new EOF blank-line warnings are removed.

The Critic's Medium schema-escape candidate was not reproduced: JSON decode produces the intended `\.` regex, an ordinary `.123Z` timestamp passes, and a backslash form is rejected. The package mirror remains byte-identical. This candidate is closed by direct and independent test evidence without changing the correct regex.

Post-Recovery verification is C1 `35 PASS`, C1 plus direct TASK-100/TASK-074/TASK-014 regression `139 PASS`, and broader TASK-100/TASK-074/TASK-014 owner regression `421 PASS`. Full C1 diff-check and compile are `PASS`. Resolved OS-temp roots are `C:\Users\user\AppData\Local\Temp\bvp-task100-lvc-c1-20260929-006` through `-008`. No dependency installation or Product/native/private/model/audio effect occurred.

## LVC-C1 independent acceptance — 2026-09-29

- Frozen Recovery HEAD: `358263fec0b6d8272db01564e95b5ac60010b647` on `codex/task-100-lvc-c-source`; exact six changed repository paths and clean worktree confirmed.
- Independent DEV-4 Critic: `ACCEPT`, C/H/M/L `0/0/0/0`; all prior Consent-expiry, canonical-coordinate and compiled-wrapper findings are closed. The prior schema-escape candidate was withdrawn after direct decoded-regex verification.
- Independent DEV-4 Tester: `PASS / ACCEPT`, C/H/M/L `0/0/0/0`; direct dependency regression `139 PASS` and independent adversarial checks `29 PASS`.
- Tester confirmed Consent expiry just-before/boundary behavior, all 13 duplicated selection/currentness coordinates, forged admission/inventory wrapper rejection, TASK-014 probe-hash binding, schema fractional timestamp positive/negative vectors, byte-identical schema mirror, exact-six scope and clean frozen HEAD.
- Independent output root `C:\Users\user\AppData\Local\Temp\bvp-task100-lvc-c1-tester-r1-20260929-001` remained uncreated with no residual artifact. No install, native/private/model/runtime, filesystem Product, Project, audio or network effect occurred.

LVC-C1 source acceptance closes only the deterministic body-free consumer-readback Atomic Unit. It does not authorize Product integration or LVC-C2 native installed-identity validation; both remain unstarted and require separately bound authority.

## LVC-C2-D0 native installed-identity boundary design — 2026-09-29

After PR #595 merged LVC-C1 into main `1d9f4a471ea8540a9fb2df19a0e2cd933e8374e2`, the Owner instructed this delivery thread to continue. The existing end-to-end TASK-100 implementation intent binds only the design-only `LVC-C2-D0` Atomic Unit in [the C2 design](lvc-c2-native-installed-identity-design-r0.md).

Allowed repository files are exactly this Task record and the new C2 design. No source, schema, test, producer Task, current-state/index, private model/audio, native runtime, Project, Release, Deploy or Production effect is authorized.

The design resolves a canonical-owner collision before implementation: current TASK-063 owns the installer-relative montage-learning Bridge and cannot issue GPT-SoVITS model installation identity. TASK-046 retains ModelArtifactBinding/H4/Consent/rights, TASK-101 must own protected existing-model import custody/readback and one-operation load lease, TASK-066 retains compute/no-network proof, TASK-075 retains inference execution, and TASK-100 may consume only their reviewed body-free identities. TASK-093's Qwen Owner Voice Runtime installation is not evidence that the selected GPT-SoVITS pair is installed.

LVC-C2 pure or native implementation remains blocked until an owning producer, exact ABI/version, Allowed Files and effect-specific Human Gate are separately bound. Product/Shell integration remains outside TASK-100 and must be allocated to its owning TASK-036/073/014/074 unit.
