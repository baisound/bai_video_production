# TASK-056 — Chase Keyword Cue / Semantic Audio Cue Bridge

- Status: `R0_CORE_AND_R2_SKILL_INTEGRATION_COMPLETE / R1A_PRODUCT_GENERATION_AND_REVIEW_QUEUE_IMPLEMENTED_LOCAL / R1B_HUMAN_DECISION_NEXT`
- Priority: `OWNER_PRIORITY_CREATOR_WORKFLOW_INSERTION`
- Governance: `DEV-3 HIGH ASSURANCE`
- Base main: `6050c4764dff9bdca0c8f6d4f175f74e8b0442c0`
- Branch: `codex/task-056-r1-product-integration`
- Intake: `BVP_Chase_Keyword_Cue_Handoff_v1_2026-08-23`

## Owner goal

Raise the practical content-production baseline before the full BAI VIDEO PRODUCTION montage workflow is complete. BVP must locally detect user-configured spoken keywords such as Japanese `チェイス`, preserve exact word timing as canonical BVP evidence, and expose a text-free non-canonical sidecar that the Montage SKILL can use immediately.

The feature must remain usable without Codex, ChatGPT, paid AI subscriptions or cloud APIs. Codex may assist development only.

## Why this is a new Task

TASK-006 owns canonical ASR/Transcript/Subtitle foundations, TASK-023 owns the existing FasterWhisper reconciliation/provider identity, TASK-036 owns Product Shell integration, TASK-022 owns canonical Timeline Mapping, and TASK-055 owns Montage proposal/learning integration with source committed on external `bai-davinci-montage-skills` main. Keyword-to-semantic-edit-cue ownership is a new cross-cutting responsibility and must not rewrite those historical boundaries.

`TASK-056` is intentionally separate from `TASK-055`: TASK-055 owns Montage proposal/Human-edit interchange and BVP admission, while TASK-056 owns the keyword-to-semantic-audio-cue bridge.

## R0 — Core contract and local sidecar

R0 owns:

- opt-in word timestamps on the existing `AsrRequest` / `FasterWhisperProvider` route;
- backward-compatible Transcript `1.0.0` and explicit word-timed `1.1.0` serialization;
- resumable/chunked word-timing preservation;
- bounded local `KeywordProfile` with deterministic normalization;
- deterministic `SpeechCueManifest` with exact rational source-frame projection;
- `CONFIRMED / REVIEW / REJECTED` state contract, with segment fallback never auto-confirmed;
- text-free, path-free Montage sidecar projection;
- zero-hit success/fallback semantics;
- deterministic ID/hash binding to Transcript + Profile + source frame rate;
- local CLI for support/advanced use;
- direct and bounded/resumable Creator Application Service routes for immediate local production use;
- publication-set commit marker plus cross-bound integrity reader;
- canonical/public Schema mirrors and focused regression.

R0 does **not** own:

- BVP Product UI/Shell integration;
- changes to TASK-036 P-UX-2K shared ports while PR #269 is open;
- a second ASR provider;
- model download, network/provider execution outside the existing local FasterWhisper gate;
- video CHASE semantic proof;
- Montage placement decisions;
- canonical Timeline mutation;
- Resolve mutation/render;
- learning/policy promotion;
- Release/Deploy.

## R0 allowed files

- `pyproject.toml`
- `src/ai_video_production/__init__.py`
- `src/ai_video_production/subtitles.py`
- `src/ai_video_production/faster_whisper_asr.py`
- `src/ai_video_production/large_media_transcription.py`
- `src/ai_video_production/cut_candidates.py`
- `src/ai_video_production/semantic_audio_cues.py`
- `src/ai_video_production/speech_cue_cli.py`
- `src/ai_video_production/speech_cue_application.py`
- `src/ai_video_production/profile_resources/**`
- `schemas/*speech-cue*`
- `schemas/keyword-profile.schema.json`
- `schemas/montage-semantic-audio-cues.schema.json`
- `schemas/transcript-manifest-v1.1.schema.json`
- matching `src/ai_video_production/schema_resources/**`
- `tests/test_speech_cue_keyword_detection.py`
- TASK-056 documentation and additive Project status/index/roadmap entries.

## Explicit overlap restrictions

During R0, PR #269 (`TASK-036 P-UX-2K`) was open and changed local transcription Product-control files. R0 therefore did not modify:

- `src/ai_video_production/task036_product_ports.py`
- `src/ai_video_production/task036_pre_edit_runtime.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- PR #269 tests/evidence/CHANGELOG paths.

`faster_whisper_asr.py` is an unavoidable semantic dependency. TASK-056 changes there must stay narrowly limited to opt-in word timestamp capture and be re-audited against PR #269 head before merge.

## R1 — Product integration after overlap re-audit

PR #269 is merged and the overlap was re-audited. R1A now implements the Product generation/read side:

- the durable P-UX-2K operation requests word timestamps and remains the only Product transcription job;
- a Project-bound Application Service derives one fixed private semantic-cue publication under the configured transcription output;
- the Shell exposes only no-argument snapshot/generate operations and never accepts a path, profile or Provider from JavaScript;
- the Edit GUI shows confirmed/review/rejected counts plus text-free frame metadata for REVIEW items;
- REVIEW items remain excluded from the Montage projection and receive no Timeline/apply authority;
- focused Product/Core/Shell/Launcher verification is `121 PASS; full regression `3625 PASS / 5 SKIP``.

R1B remains next and owns explicit Human review decisions plus durable canonical Project persistence. Its original requirements remain:

- reuse the durable P-UX-2K local transcription operation rather than creating a competing Product job;
- expose a GUI action in the appropriate Subtitle/Montage workflow;
- show confirmed/review counts without leaking transcript text to public diagnostics;
- allow Human review of low-confidence/segment-fallback cues;
- persist only through the canonical BVP Project/Application-Service route;
- keep the local CLI as support/QA, not the primary consumer UX.

## R2 — Montage integration — COMPLETE

Implemented in the external BAI DaVinci Montage SKILL Suite v0.6.0 without changing the existing TASK-055 proposal schema:

- BVP emits `montage-semantic-audio-cues.json` as a hashed text-free sidecar;
- SKILL validates the exact TASK-056 sidecar contract and `projection_sha256`;
- zero confirmed cues preserves the legacy beat/highlight proposal byte-for-byte;
- nonzero `CHASE_CALL` cues are usable only after independent video evidence (`CHASE`, `CHASE_START`, `PALLET_DROP`, `WINDOW_VAULT`, `ESCAPE`, etc.) passes;
- verified Cue/Candidate pairs may bias candidate ranking and count-based central music-anchor placement, but never create Timeline authority;
- SKILL emits `MONTAGE_SPEECH_CUE_BINDING` preserving `projection_sha256 -> cue_id -> candidate_id -> placement_id`;
- Proposal remains TASK-055-compatible, untrusted and Human-review-only.

Cross-repository E2E: BVP Transcript 1.1 -> SpeechCueManifest -> semantic sidecar -> SKILL Consumer Runtime -> Montage Proposal + Speech Cue Binding = PASS.


## Completion truth

Static/fake/provider unit PASS does not imply native FasterWhisper/Windows/Resolve runtime PASS. Real model execution remains `NOT_RUN` unless explicitly executed under the existing runtime/model gate.
