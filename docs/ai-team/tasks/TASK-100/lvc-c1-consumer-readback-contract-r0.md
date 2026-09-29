# TASK-100 LVC-C1 — Consumer Readback Contract R0

Status: `RECOVERY_R1_IMPLEMENTED / DEV4_REREVIEW_PENDING / NATIVE_IDENTITY_DEFERRED`

## 1. Goal

LVC-C1 closes the pure, body-free consumer-currentness seam between the accepted TASK-100 catalog admission, TASK-074 durable fine-tuned route selection/currentness, and TASK-014 non-executing narration preflight. It emits one deterministic evidence-only readback stating whether the exact pinned identities are current enough to reach the existing Owner Human Gate.

LVC-C1 does not load a model, start a runtime, infer audio, read private model/audio bodies, persist a host path, mutate a Project/Asset/Timeline, or create execution authority. Native installed-model identity remains LVC-C2 and requires a separate exact native gate.

## 2. Authority and exact scope

The Owner's `次へ` on 2026-09-29 followed completion of TASK-102 PMST-I2. TASK-100 already records this thread as the delivery owner with implementation intent. This binds only the source/test unit below:

1. `docs/ai-team/tasks/TASK-100/task.md`
2. `docs/ai-team/tasks/TASK-100/lvc-c1-consumer-readback-contract-r0.md`
3. `src/ai_video_production/task100_local_voice_catalog_consumer.py`
4. `schemas/task100-local-voice-catalog-consumer.schema.json`
5. `src/ai_video_production/schema_resources/task100-local-voice-catalog-consumer.schema.json`
6. `tests/test_task100_local_voice_catalog_consumer.py`
7. bounded Evidence under `C:\home\baisound\evidence\bai-video-production\TASK-100\lvc-c1\<run-id>\`

TASK-014, TASK-074 and existing catalog source are read-only dependencies in C1. Any required modification to those owners is an exact-files amendment in a later unit.

## 3. Input boundary

The compiler accepts only validated typed records:

- `LocalVoiceCatalogCandidateV1`;
- `LocalVoiceCatalogAssessmentV1`;
- `LocalVoiceCatalogAdmissionV1` paired with its compiled inventory;
- `VoiceProfileRouteSelection` in `FINE_TUNED_LOCAL` mode;
- `VoiceRouteSelectionCurrentnessEvaluation` for that exact selection;
- `LocalPrimaryNarrationPreflight` in `FINE_TUNED_LOCAL` mode;
- a strict trusted evaluation timestamp.

Structural crossing is rejected, not downgraded. Exact equality is required for candidate/admission/assessment lineage, inventory revision/entry, voice profile revision, installed binding, license evidence, ModelCandidate revision, Project identity, TASK-014 model artifact/engine identity, and TASK-074 selection/currentness lineage.

The compiler also requires:

- candidate observation through expiry contains every evaluation time;
- TASK-074 currentness is `RUNNABLE` and still current at trusted evaluation time;
- TASK-014 preflight is `READY_FOR_OWNER_HUMAN_GATE`;
- the preflight remains non-executing and body/path free;
- the admitted inventory contains exactly the one bound narration candidate.

## 4. Output contract

`LocalVoiceCatalogConsumerReadbackV1` is a strict, domain-separated, body-free record. It binds exact candidate, assessment, admission, inventory, selection, selection-currentness and preflight digests plus the shared voice/model/install/license identities.

`consumer_live_eligible=true` means only that the exact records are current enough to reach the existing Owner Human Gate. It never means load, inference, replay, Project mutation or execution permission. The following fields are invariantly false/zero:

- `authority_created`
- `execution_authorized`
- `load_lease_created`
- `runtime_started`
- `model_loaded`
- `inference_started`
- `audio_body_persisted`
- `host_path_persisted`
- `resource_effect_count=0`

Non-current operational states return `consumer_live_eligible=false` with closed reason codes. Crossed identity, malformed typed input, expiry-boundary ambiguity or effect claims raise `ValueError`.

## 5. Acceptance

- positive fine-tuned exact-lineage readback;
- every identity-crossing dimension rejects;
- blocked admission, non-runnable TASK-074 currentness and non-ready TASK-014 preflight remain ineligible;
- trusted time before required evidence or at/after expiry rejects;
- schema and package mirror are byte-identical and validate positive/negative vectors;
- TASK-100, direct TASK-074 and TASK-014 focused regression passes;
- no filesystem, process, network, model, audio, Project or Product runtime effect;
- DEV-4 independent Critic and Tester findings end at Critical/High zero before acceptance.
