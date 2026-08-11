# AI Video Production — Current State

## Canonical project state

- Project: `ai-video-production`
- Mode: `BAI Development OS CONSUMER_PROJECT_MODE`
- Project Status: `TASK_024_SLICE_A_RELEASE_CANDIDATE_VALIDATED`
- Last Completed Task: `TASK-006 Slice D — Resumable ASR / Resolve Subtitle Handoff (v0.17.0)`
- Active Consumer Task: `TASK-024 — Silence / Filler / Disfluency Cut Candidate Worker`
- TASK-004 Profile: `DEV-4 FOUNDATION CRITICAL` / score `25`
- TASK-004 Status: `COMPLETED`
- Package: `0.17.0` (FORMAL RELEASE COMPLETE; PR #12 / merge `edb12f1cfd6c6912c030f62e4c685801f7d15084`)
- Development Candidate: `0.18.0` (TASK-024 Slice A Windows release-candidate validation PASS)
- Next Consumer Task: `TASK-024 Slice A commit / PR / CI / merge / v0.18.0 tag`

## TASK-004 implemented scope

### Media foundation

- exact rational timebase including NTSC rates;
- bounded ffprobe timing/VFR inspection;
- fixed-argv ffmpeg normalization;
- 48 kHz PCM analysis audio;
- CFR proxy generation and complete-batch QA;
- source-checksum revalidation and derived-Asset publication;
- normalization manifest/Evidence and TASK-022 affine handoff.

### Local Visual AI

- local/private ComfyUI API boundary, class/resource admission and safe output containment;
- FLUX/Stable Diffusion family image runtime/license profiles;
- MiniMax H3 T2V/I2V/First-Last/Reference provider contracts;
- Character Identity profile + same-Job canonical reference bundle;
- H3 Production Brief structured compiler;
- H3 SingleFrame optional external-node provider;
- Spectrum optional approximate acceleration with Native default and cache-wrapper conflict prevention;
- H3 Foley/SFX standard and explicitly experimental FAST_32/extended-duration contracts;
- persisted ComfyUI `prompt_id` reconciliation to prevent blind duplicate generation after timeout/crash.

### Local Audio AI

- Audacity `mod-script-pipe` external Runtime boundary;
- Intel OpenVINO capability discovery without copying GPL plugin code;
- Noise Suppression and verified-runtime 2-stem Music Separation contract; 4-stem is fail-closed until scriptable mode is available;
- output containment, complete sibling QA before publication and derived AUDIO Asset registration;
- ambiguous external state fails closed instead of automatically replaying Audacity work.
- worker phase Evidence distinguishes pre-dispatch timeout from post-dispatch ambiguity; post-dispatch timeout is persisted as `PARTIAL` and blocks blind replay.

## Current verification

- TASK-006 Slice D package `0.17.0`: formal release complete; Windows full regression `415 passed, 1 intentional skip`, compileall/diff-check/fsck PASS, GitHub Actions all green. No Resolve mutation is implemented in TASK-006.
- TASK-024 Slice A package `0.18.0` candidate: Windows release-candidate validation PASS — `433 passed, 1 intentional skip`, compileall/diff-check/fsck PASS, real-WAV CLI/FFmpeg candidate generation PASS, Subtitle Workspace/Open-dialog/Cancel PASS, AI Connection Settings launch PASS. Formal release still requires protected-branch PR/CI/merge/tag.
- TASK-006 v0.16.4 formal release: `402 / 402 PASS`; `compileall` PASS; `git diff --check` PASS; `git fsck --full` PASS; native Windows Subtitle Workspace/Open/Save validation PASS.
- v0.17.0 development-governance baseline: BAI Development OS `1.0.0` / Architecture `Ver.2.28 CURRENT_CANONICAL`, Level A Governance Only, with no Product runtime dependency. Migration baseline is completed before TASK-006 Slice D feature code.
- TASK-006 Windows interaction corrective `0.16.4`: native SRT dialog failure/CLIXML leakage corrected, strict relative insertion timing and visible export/server-disconnect feedback accepted on Windows
- TASK-006 corrective package `0.16.1`: Windows CRLF fixture writes exact bytes; production SRT behavior unchanged
- TASK-006 Slice C package `0.16.0`: planned narration/ASR/SRT intake, revisioned local review GUI, row editing and atomic SRT export implemented

- TASK-006 Slice A package `0.13.0`: Transcript/Subtitle schemas, cut-aware exact mapping and deterministic NTSC SRT tests PASS
- TASK-006 Slice B package `0.14.0`: optional FasterWhisper local ASR, explicit model-download gate, Transcript/SRT publication and text-free report tests PASS
- TASK-006 native Windows Evidence: `small` Japanese CPU/int8 produced 10 Segments locally; Native ASR PASS. One mistranscription and adjacent SRT 1 ms render overlaps require Slice C corrective/review work. Correction order is dictionary, GUI human review, default-off opt-in AI typo/omission proposal, then human approval.
- TASK-027 Slice A1 package `0.15.0`: real-production-evidence-derived Production Blueprint, Scene Ledger, Reference Registry, source-priority and dense-text generation gates implemented
- TASK-035 design intake: optional REAPER audio-finishing/Resolve round-trip recorded; native ReaScript Plan/QA bridge precedes any third-party MCP or iZotope Assistant automation
- TASK-014 design intake: owner's existing ElevenLabs Pro trained voice will be used through a private Voice Profile and timed TTS path; no retraining/upload or paid call is authorized by configuration alone
- TASK-034 native Windows package `0.12.2`: Catalog/Credential lifecycle and per-row Password Manager behavior PASS
- TASK-034 package `0.12.2`: Catalog lifecycle linkage, retained-key cleanup, OS vault, per-Route password-manager lookup and secret-exclusion tests PASS
- TASK-033 native Windows: add `demo-video-route`, edit to `demo-model-v2`, disable and truthful adapter status display PASS
- TASK-033 package `0.11.0`: Catalog add/edit/disable, implementation status, API mutation and secret-exclusion tests PASS
- TASK-032 native Windows: save/reload PASS; stale revision 3 rejected after revision 4 save PASS; 2–3-person usability review pending
- TASK-032 package `0.10.0`: local GUI/API, CSRF, Host, conflict and secret-exclusion tests PASS
- TASK-032 package `0.9.0`: `330 / 330 PASS`, compileall PASS, diff-check PASS
- Settings persistence: atomic rollback, stale-write conflict, checksum tamper, 0.8 migration and secret-free bilingual form PASS
- `pytest`: `250 / 250 PASS`
- `compileall`: PASS
- `git diff --check`: PASS
- package `0.4.7` wheel build: PASS
- installed-wheel packaged schemas: PASS
- installed-wheel real ffmpeg/ffprobe golden normalization: PASS
- absent ComfyUI/Audacity runtimes: structured fail-closed diagnostics PASS
- wheel SHA-256: `a87beed109e0ac6641fefb25d519b625eea1fa6507bfea04552edfe0e1e48366`

## Final TASK-004 Evidence

Target-machine capability Evidence is accepted for ComfyUI and Audacity/OpenVINO. The final package 0.4.9 behavioral run completed Noise Suppression and the provable Intel-default 2-stem Music Separation path. It published one noise-suppressed Asset and the complete `instrumental`/`vocals` pair with committed Manifests and verified checksums. All four probe database operations completed without error.

The first full native-Windows regression returned `251 passed, 2 failed`. Package 0.4.10 corrected the Windows-only test double so it preserves the real CRT `O_BINARY` bit, and normalized equivalent Win32/extended-length canonical paths before containment comparison. The final rerun passed `255 / 255` tests in 41.26 seconds; compileall also passed with no output.

4-stem Music Separation remains explicitly `NOT_SCRIPTABLE_ON_VERIFIED_RUNTIME`: the live descriptor exposes no separation-mode parameter, so the Product fails closed until a future runtime/provider exposes a scriptable mode.

## Roadmap

Canonical roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` Ver.1.6. Owner-directed editing-first priority remains in force. TASK-004 moved local image/video/audio generation foundations forward while preserving TASK-022/010/026 ownership of exact Timeline placement.

TASK-022 is now implemented with exact rational source/normalized-to-Timeline mapping, deterministic Plan hashing and canonical/package schemas. Native-Windows full regression is the remaining completion gate.

## Safety boundaries

- BAI Development OS Core and OS-internal TASK-016 remain untouched.
- DistributedOS remains disabled.
- no third-party runtime/model/custom-node is auto-installed or auto-updated;
- external GPL custom/runtime source is not copied into Product Core;
- generated/processed media is not canonically published until Product-side containment/media/checksum QA passes;
- downstream public-use/licensing decisions remain explicit policy gates;
- Character Identity / SingleFrame / Spectrum / H3 Foley are bounded capabilities, not claims of guaranteed identity fidelity or quality.
