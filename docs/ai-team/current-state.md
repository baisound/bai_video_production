# AI Video Production — Current State

## Canonical project state

- Project: `ai-video-production`
- Mode: `BAI Development OS CONSUMER_PROJECT_MODE`
- Project Status: `TASK-004_IMPLEMENTATION_COMPLETE_AWAITING_LIVE_CAPABILITY_EVIDENCE`
- Last Completed Task: `TASK-003 — Asset Registry / Ingest / Path Resolver`
- Active Consumer Task: `TASK-004 — Media Normalization + Local Visual/Audio AI Runtime Foundation`
- TASK-004 Profile: `DEV-4 FOUNDATION CRITICAL` / score `25`
- TASK-004 Status: `IMPLEMENTATION_COMPLETE_AWAITING_LIVE_CAPABILITY_EVIDENCE`
- Package: `0.4.0`
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
- Noise Suppression and 2/4-stem Music Separation contracts;
- output containment, complete sibling QA before publication and derived AUDIO Asset registration;
- ambiguous external state fails closed instead of automatically replaying Audacity work.

## Current verification

- `pytest`: `229 / 229 PASS`
- `compileall`: PASS
- `git diff --check`: PASS
- package `0.4.0` wheel build: PASS
- installed-wheel packaged schemas: PASS
- installed-wheel real ffmpeg/ffprobe golden normalization: PASS
- absent ComfyUI/Audacity runtimes: structured fail-closed diagnostics PASS
- wheel SHA-256: `69ccf086b2346c6e0e79f6fe8adcd7a1f0658abded50cd80beef6e1f28855009`

## Remaining TASK-004 gate

Target-machine live capability Evidence is still required before formal completion. The current build environment does not contain the Owner's ComfyUI/MiniMax/FLUX/SD/Audacity/OpenVINO installation, therefore no live provider-support or performance claim is fabricated.

Run `tools/windows/run-task004-local-ai-capability-probes.ps1` on the target Windows machine and return `task004-live-evidence/` for final DEV-4 review.

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
