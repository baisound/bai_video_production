# AI Video Production — Current State

## Canonical project state

- Project: `ai-video-production`
- Mode: `BAI Development OS CONSUMER_PROJECT_MODE`
- Project Status: `TASK-033_PROVIDER_MODEL_CATALOG_IMPLEMENTED_AWAITING_NATIVE_EVIDENCE`
- Last Completed Task: `TASK-022 — Timeline Mapping Service`
- Active Consumer Task: `TASK-033 — Provider and Model Catalog Editor`
- TASK-004 Profile: `DEV-4 FOUNDATION CRITICAL` / score `25`
- TASK-004 Status: `COMPLETED`
- Package: `0.11.0`
- Next Consumer Task: `TASK-033 native Windows Catalog Evidence (due 2026-08-24)`

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

Canonical roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` Ver.1.4. Owner-directed editing-first priority remains in force. TASK-004 moved local image/video/audio generation foundations forward while preserving TASK-022/010/026 ownership of exact Timeline placement.

TASK-022 is now implemented with exact rational source/normalized-to-Timeline mapping, deterministic Plan hashing and canonical/package schemas. Native-Windows full regression is the remaining completion gate.

## Safety boundaries

- BAI Development OS Core and OS-internal TASK-016 remain untouched.
- DistributedOS remains disabled.
- no third-party runtime/model/custom-node is auto-installed or auto-updated;
- external GPL custom/runtime source is not copied into Product Core;
- generated/processed media is not canonically published until Product-side containment/media/checksum QA passes;
- downstream public-use/licensing decisions remain explicit policy gates;
- Character Identity / SingleFrame / Spectrum / H3 Foley are bounded capabilities, not claims of guaranteed identity fidelity or quality.
