# TASK-100 LVC-D — Local Voice Catalog Admission Contract R0

## Decision and boundaries

- Baseline: `17feeb5c8314df25d8993696ceb7db71c66bb0fb`; parent main `e41110c85ba4ab098c591378cb1b2eaae3cc3cb7`.
- Profile: DEV-4. This document is design-only and authorizes no model/audio/private I/O, runtime probe/load, download, inference or external mutation.
- Canonical inventory remains `local_audio_model_inventory.py`. TASK-100 owns only strict provenance admission and deterministic conversion to one existing `LocalAudioModelObservation`.
- Narration conversion is fixed: `purpose=NARRATION`, `workload=None`, `route_id=None`, `provider_family=LOCAL_OPEN_SOURCE`. It never enters SFX/MUSIC `ModelRoute` or TASK-028 generic capability execution.
- `profile_selectable` and `generation_ready` from the existing public projection mean catalog eligibility only. Every output keeps `execution_authorized=false`; TASK-100 cannot issue a load lease or inference permission.

## Canonical record

`LocalVoiceCatalogCandidateV1` uses `contract_version=LOCAL_VOICE_CATALOG_CANDIDATE_V1` and a strict closed object. Its candidate digest is:

```text
sha256(b"BAI:TASK-100:LOCAL-VOICE-CATALOG-CANDIDATE:V1\0" + canonical_json(body_without_candidate_sha256))
```

Required top-level fields:

| Field | Constraint |
|---|---|
| `contract_version`, `record_type` | exact constants; record type `LocalVoiceCatalogCandidateV1` |
| `candidate_id`, `provider_id`, `engine_id`, `execution_port_id` | existing-inventory-compatible public-ID regex `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`; additionally reject URI/path/backslash/parent components |
| `model_id` | model-ID regex `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`; additionally reject drive prefix, URI/path/backslash/parent components |
| `revision` | integer 1..2147483647; Boolean rejected |
| `predecessor_sha256` | null only at revision1; required digest after revision1 |
| `runtime_build_sha256`, `model_pair_sha256`, `sovits_sha256`, `gpt_sha256` | exact lower-case SHA-256; pair digest is producer-owned evidence, not recomputed from concatenated strings |
| `voice_profile_revision_sha256`, `model_candidate_revision_sha256`, `consent_currentness_sha256`, `h4_approval_sha256`, `license_evidence_sha256` | exact producer digests |
| `installed_binding_sha256`, `capability_map_sha256`, `producer_readback_set_sha256` | exact producer digests |
| `custody_provenance` | strict tagged union below |
| `observation_source` | `VERIFIED_PRODUCER_READBACK` or `FIXTURE_ONLY` |
| `observed_at`, `expires_at` | TASK-084 calendar-valid UTC grammar (seconds plus optional 1–6 fractional digits, exact `Z`); observed < expires |
| `candidate_sha256` | domain-separated digest above |

There is no host path, endpoint, private reference/transcript, model body, credential, load handle, Consent body, free-form log/message, or mutable settings field.

The frozen fixture vector below is one canonical UTF-8 preimage. It uses the proposed TASK-101 branch and therefore can never become live admission until that producer contract is accepted:

```json
{"candidate_id":"baisound-c04-stable-v2-0-1","capability_map_sha256":"sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","consent_currentness_sha256":"sha256:9999999999999999999999999999999999999999999999999999999999999999","contract_version":"LOCAL_VOICE_CATALOG_CANDIDATE_V1","custody_provenance":{"producer_task":"TASK-101","readback_sha256":"sha256:8888888888888888888888888888888888888888888888888888888888888888","readback_type":"ExistingModelImportCustodyReadbackV1","receipt_sha256":"sha256:7777777777777777777777777777777777777777777777777777777777777777","receipt_type":"ExistingModelImportCustodyReceiptV1","variant":"EXISTING_MODEL_IMPORT"},"engine_id":"gpt-sovits-v2pro","execution_port_id":"task075-c04-local","expires_at":"2026-09-27T00:05:00Z","gpt_sha256":"sha256:4444444444444444444444444444444444444444444444444444444444444444","h4_approval_sha256":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","installed_binding_sha256":"sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","license_evidence_sha256":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","model_candidate_revision_sha256":"sha256:6666666666666666666666666666666666666666666666666666666666666666","model_id":"baisound-c04-stable-v2.0.1","model_pair_sha256":"sha256:2222222222222222222222222222222222222222222222222222222222222222","observation_source":"FIXTURE_ONLY","observed_at":"2026-09-27T00:00:00Z","predecessor_sha256":null,"producer_readback_set_sha256":"sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee","provider_id":"baisound-local","record_type":"LocalVoiceCatalogCandidateV1","revision":1,"runtime_build_sha256":"sha256:1111111111111111111111111111111111111111111111111111111111111111","sovits_sha256":"sha256:3333333333333333333333333333333333333333333333333333333333333333","voice_profile_revision_sha256":"sha256:5555555555555555555555555555555555555555555555555555555555555555"}
```

Expected `candidate_sha256` is `sha256:587ca3aeecd17700695a1cffeeba8b5a7cb671cd2225e5a79a72fd3552acb2eb`. `canonical_json_bytes` from `serialization.py` is the only encoding algorithm; no whitespace, BOM, alternate key order, float conversion or Unicode normalization is introduced by TASK-100.

## Custody tagged union

`custody_provenance` always contains exactly `variant`, `producer_task`, `receipt_type`, `receipt_sha256`, `readback_type`, `readback_sha256`.

- `EXISTING_MODEL_IMPORT`: producer `TASK-101`; **proposed** receipt `ExistingModelImportCustodyReceiptV1`; **proposed** readback `ExistingModelImportCustodyReadbackV1`. They are fixture-only until TASK-101 IMC-D independently accepts that exact producer identity/version.
- `TRAINING_TERMINAL`: producer `TASK-084`; receipt `Task084ModelArtifactCustodyReceiptV1`; readback `Task084CustodyReadbackV1`.

No alternate producer/type, cross-variant field, generic custody hash, alias, copied self-hash or issuer erasure. The current C04 route uses `EXISTING_MODEL_IMPORT`; the training branch is reserved only to prevent future consumers from inventing an alias.

## Admission input and deterministic result

The pure compiler receives the canonical candidate plus explicit typed producer states:

- installed: `INSTALLED | NOT_INSTALLED | UNKNOWN`;
- runtime: `READY | STOPPED | UNKNOWN`, with runtime instance ID required only for READY;
- currentness: `CURRENT | STALE | UNKNOWN`;
- license: `CONFIRMED | UNKNOWN`;
- automation: `SCRIPTABLE | DISPLAY_ONLY | UNSUPPORTED`, with the candidate execution port used only for SCRIPTABLE;
- producer authenticity: `VERIFIED | NOT_VERIFIED`;
- custody contract state: `ACCEPTED | PROPOSED_FIXTURE_ONLY`;
- required producer currentness: a strict mapping with exactly `LINEAGE`, `CUSTODY`, `CONSENT`, `H4_APPROVAL`, `INSTALLED_BINDING`, `CAPABILITY_MAP`, `EXECUTION_PORT`; every value is `CURRENT | STALE | REVOKED | UNKNOWN`.

These fields form the strict `LocalVoiceCatalogAssessmentV1` with exactly these snake-case keys: `assessment_version=LOCAL_VOICE_CATALOG_ASSESSMENT_V1`, `candidate_sha256`, `producer_readback_set_sha256`, `evaluated_at`, `installed_state`, `runtime_readiness`, `runtime_instance_id`, `inventory_currentness`, `license_state`, `automation_readiness`, `producer_authenticity`, `custody_contract_state`, `required_producer_currentness`, `assessment_sha256`. `runtime_instance_id` is null unless readiness is READY; READY requires the public-ID grammar used by existing inventory. The currentness object has exactly the seven uppercase keys listed above. Unknown/missing assessment/currentness keys, booleans, unrecognized enum values and invalid timestamps/IDs are rejected. `assessment_sha256` is the domain-separated structural digest of the exact canonical body without itself under `BAI:TASK-100:LOCAL-VOICE-CATALOG-ASSESSMENT:V1\0`; it provides correlation, not authority. Both candidate/readback-set digests must equal the candidate exactly and the compiler requires `candidate.observed_at <= assessment.evaluated_at < candidate.expires_at`. A mismatched/expired/unrelated assessment is rejected structurally, not converted to a blocked result. Every required producer currentness value must be `CURRENT` for admission. These are caller-supplied results from future trusted ports; pure code validates and binds them but does not authenticate an OS/runtime by itself. `VERIFIED` means the caller's future trusted port verified that exact readback set, not that TASK-100 authenticated a self-hashed JSON document.

The adapter never exposes an all-ready inventory row for fixture or unverified input. It first computes the requested admission state. Only `ADMITTED_CATALOG_CANDIDATE` maps the supplied states to an observation with `source=PINNED_CONTRACT`, runtime instance and execution port. This is an admitted pinned producer-readback contract, not falsely labelled as a TASK-100 runtime probe. For `FIXTURE_ONLY_CANDIDATE` and `BLOCKED_CATALOG_CANDIDATE`, the observation is fail-closed normalized to `installed=UNKNOWN`, `runtime=UNKNOWN`, `currentness=UNKNOWN`, `license=UNKNOWN`, `automation=UNSUPPORTED`, `runtime_instance_id=None`, `execution_port_id=None`, `source=HISTORICAL_EVIDENCE`. It therefore remains nonselectable even if a consumer ignores the TASK-100 admission wrapper and sees only the existing inventory.

It returns `LocalVoiceCatalogAdmissionV1` with exactly:

`contract_version=LOCAL_VOICE_CATALOG_ADMISSION_V1`, `record_type=LocalVoiceCatalogAdmissionV1`, `candidate_sha256`, `producer_readback_set_sha256`, `assessment_sha256`, `candidate_observed_at`, `evaluated_at`, `candidate_expires_at`, `admission_state`, ordered unique `reason_codes` (0..16 uppercase identifiers), `inventory_candidate_sha256`, `inventory_sha256`, `consumer_live_eligible=false`, `consumer_currentness_required=true`, `replayable_authority=false`, `execution_authorized=false`, `load_lease_created=false`, `runtime_started=false`, `model_downloaded=false`, `host_path_persisted=false`, `private_body_persisted=false`, `resource_effect_count=0`, and `admission_sha256` under domain `BAI:TASK-100:LOCAL-VOICE-CATALOG-ADMISSION:V1\0`. Its digest preimage is canonical JSON of the exact body without `admission_sha256`. ADMITTED requires exactly `[]`; each non-admitted state requires at least one reason.

Admission state:

- `FIXTURE_ONLY_CANDIDATE` when source is fixture; never admitted even when all reported states look ready.
- `ADMITTED_CATALOG_CANDIDATE` only for verified producer authenticity + accepted custody producer contract + all seven required producers CURRENT + current installed/ready/confirmed/scriptable evidence and zero inventory disabled reasons.
- otherwise `BLOCKED_CATALOG_CANDIDATE`.

Closed reason order is deterministic and is **not alphabetical sorting**. It preserves primary cause before the fixed producer-owner order and existing inventory order:

1. `FIXTURE_ONLY_SOURCE`
2. `PRODUCER_AUTHENTICITY_NOT_VERIFIED`
3. `CUSTODY_CONTRACT_NOT_ACCEPTED`
4. required-producer failures in exact key order above, one of `*_STALE`, `*_REVOKED`, `*_UNKNOWN`
5. disabled reasons derived from the **supplied** observation states in existing inventory canonical order (`STALE_INVENTORY`, `INVENTORY_CURRENTNESS_UNKNOWN`, `MODEL_NOT_INSTALLED`, `MODEL_INSTALLATION_UNKNOWN`, `RUNTIME_STOPPED`, `RUNTIME_READINESS_UNKNOWN`, `LICENSE_NOT_CONFIRMED`, `AUTOMATION_API_NOT_SCRIPTABLE`, `UNSUPPORTED_CAPABILITY`, `EXECUTION_PORT_NOT_BOUND`, `EVIDENCE_NOT_BOUND`). The candidate digest always supplies evidence, so `EVIDENCE_NOT_BOUND` is reserved compatibility and is not normally emitted.

The compiler then emits the admitted or fail-closed normalized inventory observation described above. `reason_codes` describe submitted evidence; the existing inventory digests describe the actual safe observation handed to legacy consumers. Both are bound into the admission digest. Duplicate reasons are impossible and consumer order is fixed.

LVC-I outputs are pure candidate Evidence and are never by themselves replayable Product eligibility. It exposes the inventory only inside the compiled result paired with its admission. No LVC-I code persists it, injects it into the Product catalog/UI or calls `project_public_voice_profile_models`. LVC-C must add a TASK-074-owned consumer currentness check that verifies the exact admission/candidate/assessment digests, exact current producer-readback-set digest and trusted `evaluated_at <= trusted_now < candidate_expires_at`, plus then-current producer states. Until that separately reviewed consumer returns current, `consumer_live_eligible` remains false even for `ADMITTED_CATALOG_CANDIDATE`. A bare legacy inventory snapshot or `generation_ready` projection is explicitly insufficient and must not be persisted/replayed as TASK-100 admission.

The adapter passes `candidate_sha256` as the existing observation's `evidence_sha256`. The resulting existing inventory owns `inventory_candidate_sha256` and `inventory_sha256`; TASK-100 does not reproduce their hash algorithms. Candidate model ID must match the TASK-046 profile's exact model identity in the later TASK-074 consumer unit; LVC-I tests only structural binding because live TASK-046/H4 evidence is unavailable.

## Parser and schema

- `parse_local_voice_catalog_candidate_json(bytes)` accepts UTF-8 JSON from 1 through 131072 bytes, rejects BOM/invalid UTF-8, duplicate keys at any depth, non-object root, non-finite numbers, trailing data, nesting depth above 12, unknown/missing fields, booleans as integers and invalid digest/timestamp/ID forms, then verifies the domain digest.
- Mapping parsing performs the same semantic validation. Candidate/assessment objects are deep-copied before validation; caller mutation cannot change the returned immutable records. JSON Schema draft 2020-12 is a mirror/interchange check, not the sole security parser.
- Schema has closed `additionalProperties=false`, strict custody `oneOf`, anchored regexes, integer bounds, assessment/admission time fields, and `const` false for all authority/body/path/live-eligibility flags in the admission record.
- Canonical schema and package mirror must be byte-identical. Schema self-validation and positive/negative vectors are mandatory.

## LVC-I exact allocation and acceptance

After independent LVC-D acceptance, LVC-I may modify exactly:

1. `src/ai_video_production/task100_local_voice_catalog_admission.py`
2. `schemas/task100-local-voice-catalog-admission.schema.json`
3. `src/ai_video_production/schema_resources/task100-local-voice-catalog-admission.schema.json`
4. `tests/test_task100_local_voice_catalog_admission.py`
5. `docs/ai-team/tasks/TASK-100/task.md` only for completion Evidence/status

The design's “exact4” means implementation payload; the Task record is its required status/Evidence carrier and is an explicitly allowed fifth documentation path. No existing inventory/074/073 source change.

Acceptance tests: both custody variants and cross-variant rejection; deterministic hashes; revision/predecessor; strict parser including nested duplicate keys; timestamp ordering; unsafe IDs/private path leakage; fixture cannot admit; every negative producer state; existing narration observation shape; inventory digest binding; schema/mirror equality and JSON Schema vectors; public result flags; no file/network/process/runtime APIs. Focused TASK100 plus existing TASK013 inventory regression, compile and diff scope must pass. Independent Tester/Critic/Judge required; C/H findings zero.

Assessment/admission tests must prove changing only `evaluated_at` changes both assessment and admission digests, expired/boundary evaluations reject, all three times survive round-trip, and no result can set `consumer_live_eligible`, `replayable_authority` or `execution_authorized` true. LVC-I contains no public function that returns the inventory without its paired admission.

The fixture/unverified/bad-currentness bypass test is mandatory: supply every positive installed/runtime/license/automation field together with `FIXTURE_ONLY`, `NOT_VERIFIED`, proposed TASK-101 custody, or any one `STALE/REVOKED/UNKNOWN` producer, then assert both the TASK-100 admission and the underlying existing `LocalAudioModelCandidate.selectable` are false, runtime/execution IDs are absent, and `project_public_voice_profile_models` cannot report `generation_ready=true` from that row. Also reject candidate/readback-set mismatch and evaluated times before observation or at/after expiry.

## Deferred work

LVC-C owns actual trusted producer authentication/currentness, TASK-046 identity match, TASK-074/014/073 consumers and native installed readback. No synthetic candidate becomes live evidence. Any need to modify the existing catalog or producer owner requires a fresh exact scope; LVC-I fails closed instead of expanding itself.
