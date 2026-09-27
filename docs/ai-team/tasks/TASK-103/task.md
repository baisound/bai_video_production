# TASK-103 — GPT-SoVITS Functional Master WAV MVP

- Status: `FMVP_N1_TECHNICAL_PASS / HUMAN_LISTENING_PENDING`.
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

## Atomic Unit FMVP-N1 — authorized 2026-09-27

The Owner answered `つぎへ` directly to the explicit FMVP-N1 gate. This authorizes one contained native validation run: read TASK-097's existing accepted Dataset, select and privately stage two expression-reference candidates, start/use the existing loopback GPT-SoVITS runtime when required, load only the selected V2_FRESH e4 SoVITS + e15 GPT pair, generate one two-expression Master WAV, perform bounded technical validation and present the exact output for Human audition.

Native output is limited to one unique run directory beneath `%LOCALAPPDATA%\BAI Video Production\owner-voice\jobs\`. Public-safe Evidence may contain opaque candidate IDs, digests, format facts and results, but no transcript body, reference audio, generated private WAV, or private absolute path. Temporary analysis files must remain inside the task worktree and be removed after use.

Excluded: new recording, training, model download, ACL/service installation, real Project or Asset mutation, Release, Deploy and Production use. Human listening acceptance remains a result gate, not something the tool may infer.

## FMVP-N1 result

- Run identity: `task103-fmvp-n1-20260927-r1`; the private run is retained beneath the authorized `%LOCALAPPDATA%\BAI Video Production\owner-voice\jobs\<run-id>\` root for Human audition and bounded reproduction.
- Two existing TASK-097 Dataset references were staged under opaque IDs `TASK097_NEUTRAL_B015` and `TASK097_EXCITED_C020`. Transcript bodies and audio remain private and are not committed.
- The runtime explicitly loaded `BAISOUND_TASK097_V2_FRESH_e4_s192.pth` (SHA-256 `76a492931f97cd349c6d7d6f04bab4f2442fa9890a5a40708a1d49f919f8e0ff`) and `BAISOUND_TASK097_V2_FRESH-e15.ckpt` (SHA-256 `4dd990db49d56bdaff6c4988635c46b58f73e1d719297570f0d361184fd60745`).
- One two-expression Master WAV was generated and technically validated as `48 kHz / mono / PCM24`, `14.5 s`, `696000` samples, non-silent, with zero clipped samples. Its SHA-256 is `d43ced220c301a850d44093d6c8e6b4cb17340f7d3f70f814a72c4b298b20e3f`.
- Both Cue outputs are non-silent and non-clipped and have different measured RMS/peak values. The native technical result is `PASS`; Human listening quality remains `NOT_CONFIRMED` until the Owner auditions the exact Master WAV.
- The loopback server was stopped after generation. Intentional private residuals are the staged references, input SRT/overrides, Cue WAVs, Master WAV and technical reports inside the unique run directory. No Project/Asset mutation, model download/training, Release, Deploy or Production use occurred.
