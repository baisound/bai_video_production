# TASK-103 — GPT-SoVITS Functional Master WAV MVP

- Status: `FMVP_I1_IMPLEMENTED_TESTED / NATIVE_EXPRESSION_MASTER_WAV_PENDING`.
- Governance: `DEV-3 HIGH ASSURANCE` (private local voice data and cross-runtime adapter).
- Owner intent: 2026-09-27 instruction to finish the usable feature first and defer non-blocking Production hardening.
- Coordinator: TASK-073 expression Master WAV outcome.
- Dependency: reuse the existing TASK-014 SRT planning, reference selection, PCM normalization and Master WAV assembly path. TASK-102 remains the later Production Project-manifest hardening dependency and is not weakened or represented as complete here.

## Goal

Make the existing local Owner Voice command capable of using the already-running loopback GPT-SoVITS v2 API, explicitly loading the Owner-selected V2_FRESH e4 SoVITS and e15 GPT weights, selecting an approved reference per Cue expression, and producing one `48 kHz / mono / PCM24` private-staging Master WAV.

This is a local single-user functional MVP. It may establish that the feature works, but it does not establish Production security, packaged-runtime identity, canonical Project currentness, model promotion, release or deployment.

## Atomic Unit FMVP-I1

Allowed files:

- `docs/ai-team/tasks/TASK-103/task.md`
- `src/ai_video_production/task014_srt_owner_voice_wav.py`
- `tools/windows/make-owner-voice-wav.ps1`
- `tests/test_task014_srt_owner_voice_wav.py`
- `docs/user/SRT-OWNER-VOICE-WAV.md`
- completion-only synchronization in `docs/ai-team/current-state.md` and `docs/ai-team/task-index.md`
- bounded Evidence under `docs/ai-team/tasks/TASK-103/evidence/` or the canonical external TASK-103 Evidence root

Acceptance:

1. HTTP traffic is restricted to loopback and uses the GPT-SoVITS `api_v2.py` POST `/tts` contract.
2. The selected GPT and SoVITS weight paths are set once before synthesis, with a failure stopping generation.
3. Cue override JSON can choose `style_id`, `emotion_id` and speaking rate per Cue; neutral fallback remains opt-in.
4. Reference paths are translated explicitly for a WSL-hosted server without exposing them in public reports.
5. Returned audio is size-bounded, normalized through the existing ffmpeg path, validated as canonical PCM WAV and assembled by the existing implementation.
6. Focused tests cover success, model-configuration failure, non-loopback rejection, response bounds, expression routing and CLI wiring.

Prohibited in this unit: starting/stopping or installing the server, model download/training, ACL or Windows service mutation, real Project manifest mutation, Asset adoption, Release, Deploy and Production use. Real private audio/model inference remains a separate explicit native run after implementation acceptance.

## FMVP-I1 result

- Focused and direct regression: `230 PASS` on 2026-09-27.
- PowerShell parser and `git diff --check`: `PASS`.
- No server start/stop, weight load, inference, private audio read or Master WAV write was performed by this implementation unit.
- Next shortest unit: one explicitly authorized native run with at least two approved expression references, followed by Human audition of the exact Master WAV. TASK-102 security hardening remains later and does not block this local MVP run.
