# AI Video Production — Current State

## Canonical project state

- Project: `ai-video-production`
- Mode: `BAI Development OS CONSUMER_PROJECT_MODE`
- Project Status: `TASK-004_CAPABILITY_VERIFIED_AWAITING_LIVE_BEHAVIORAL_EVIDENCE`
- Last Completed Task: `TASK-003 — Asset Registry / Ingest / Path Resolver`
- Active Consumer Task: `TASK-004 — Media Normalization + Local Visual/Audio AI Runtime Foundation`
- TASK-004 Profile: `DEV-4 FOUNDATION CRITICAL` / score `25`
- TASK-004 Status: `CAPABILITY_VERIFIED_AWAITING_LIVE_BEHAVIORAL_EVIDENCE`
- Package: `0.4.6`
- Next Consumer Task: `NONE AUTHORIZED`

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

- `pytest`: `249 / 249 PASS`
- `compileall`: PASS
- `git diff --check`: PASS
- package `0.4.6` wheel build: PASS
- installed-wheel packaged schemas: PASS
- installed-wheel real ffmpeg/ffprobe golden normalization: PASS
- absent ComfyUI/Audacity runtimes: structured fail-closed diagnostics PASS
- wheel SHA-256: `e580b4fe17699d2e6b987edd05ee0f6bbfd1906c86dafbb2a47ed405ad773d37`

## Remaining TASK-004 gate

Target-machine **capability Evidence is now accepted** for both ComfyUI and Audacity/OpenVINO. Audacity Attempt 05 proved all five targeted OpenVINO effects live-reachable with an empty project and completed worker execution.

Formal completion still requires bounded behavioral Evidence for the two TASK-004 executable audio targets: OpenVINO Noise Suppression and the provable 2-stem Music Separation path. Attempt 06 reached the Product ingest boundary but stopped **before any Audacity mutation** with `ERR_INPUT_SOURCE_CHANGED_DURING_INGEST`; the returned database contains no Asset publication and no audio-AI operation. Package 0.4.6 corrects this Windows timestamp-only false positive by revalidating the already-open source bytes when only `mtime_ns` drifts, while preserving fail-closed behavior for size/content changes. Rerun `tools/windows/run-task004-audacity-openvino-behavior-probe.ps1` on package 0.4.6 with Audacity open on an empty project.

4-stem Music Separation is now explicitly `NOT_SCRIPTABLE_ON_VERIFIED_RUNTIME` rather than falsely claimed: the live descriptor exposes no separation-mode parameter, so 0.4.6 fails closed for `4_STEM` until a future runtime/provider exposes a scriptable mode.

## Roadmap

Canonical roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` Ver.1.4. Owner-directed editing-first priority remains in force. TASK-004 moved local image/video/audio generation foundations forward while preserving TASK-022/010/026 ownership of exact Timeline placement.

## Safety boundaries

- BAI Development OS Core and OS-internal TASK-016 remain untouched.
- DistributedOS remains disabled.
- no third-party runtime/model/custom-node is auto-installed or auto-updated;
- external GPL custom/runtime source is not copied into Product Core;
- generated/processed media is not canonically published until Product-side containment/media/checksum QA passes;
- downstream public-use/licensing decisions remain explicit policy gates;
- Character Identity / SingleFrame / Spectrum / H3 Foley are bounded capabilities, not claims of guaranteed identity fidelity or quality.
