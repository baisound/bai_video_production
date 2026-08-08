# TASK-004 — Media Normalization + Local AI Runtime Foundation

- Status: `IN_PROGRESS`
- Authorization: `OWNER_AUTHORIZED_IMPLEMENTATION`
- Historical alias: `VIDEO-TASK-004`
- Package target: `0.4.0`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Adaptive score: `25`

## Objective

Establish the exact media-time foundation required by subtitles, filler/cut planning and Resolve assembly, while also delivering the first replaceable local Video/Audio AI runtime foundation on top of TASK-003 Asset Registry.

TASK-004 has three bounded lanes. They share Asset/Evidence/Resource-Admission contracts but do not collapse downstream creative or timeline responsibilities into this task.

## Lane A — Timebase / Proxy / Normalization

- exact rational frame-rate representation (including 30000/1001 and 24000/1001);
- bounded ffprobe timing inspection and VFR/CFR classification;
- source-checksum revalidation before transformation;
- 48 kHz PCM analysis-audio derivation;
- CFR proxy derivation when VFR/policy requires it;
- structural/duration/timebase QA before canonical registration;
- normalization manifest and Evidence;
- affine whole-file source→normalized handoff for TASK-022.

## Lane B — Local Video AI / ComfyUI / MiniMax H3

- ComfyUI local Server API adapter (`/system_stats`, `/object_info`, `/prompt`, `/history/{prompt_id}`);
- loopback/private/explicit-local endpoint policy; public endpoints denied by default;
- workflow API-JSON validation and typed placeholder substitution without eval;
- minimum GPU/VRAM Resource Admission before queue submission;
- MiniMax H3 Native workflow profile as first intended provider;
- optional MiniMaxH3-Easy compatibility profile without hard dependency;
- T2V/I2V/First-Last/Reference request contract;
- output-root containment/symlink/traversal defense;
- generated-video media/checksum validation and canonical GENERATED_VIDEO Asset registration;
- model/workflow/prompt/seed/device provenance and conservative rights defaults.

## Lane C — Local Audio AI / Audacity OpenVINO Boundary

- GPL-3.0 Intel OpenVINO Audacity plugin code is NOT copied into BAI Core;
- Audacity `mod-script-pipe` is treated as an external local runtime boundary;
- runtime capability discovery is performed through Audacity scripting commands rather than assuming effect IDs/parameters;
- Noise Suppression and Music Separation (2-stem/4-stem) are executable provider operations;
- provider runs only against an empty/sandbox Audacity project and fails closed if existing tracks are detected;
- outputs are exported to a Product-owned staging directory, media/checksum validated, and registered as canonical derived AUDIO Assets;
- OpenVINO device/model/effect-command provenance and Evidence are retained;
- Whisper, MusicGen and Audio Super Resolution are capability-discovered/provider-ready in TASK-004, while their product workflows remain owned by TASK-006/023 and TASK-013;
- no automatic installation/download of Audacity, plugins or model weights.

## Cross-cutting Resource Admission

TASK-004 implements only the minimum admission floor needed before expensive local generation/inference: runtime availability, device visibility, verified free VRAM where applicable, disk-space floor and explicit execution authorization. Full monitoring/admission remains TASK-020.

## Out of scope

- exact edit/cut/subtitle/SE/BGM/narration placement on a Resolve timeline (`TASK-022`, `TASK-010`, `TASK-026`);
- automatic creative decision of where generated media belongs (`TASK-007/008`);
- full Resource Admission/Monitoring system (`TASK-020`);
- automatic download/install/update of ComfyUI, MiniMax weights, Audacity, OpenVINO plugins or third-party custom nodes;
- public/remote ComfyUI endpoints by default;
- copying/linking GPL Audacity OpenVINO implementation into Product Core;
- falsely declaring MiniMax H3 or OpenVINO model performance PASS without live user-runtime Evidence.

## Acceptance criteria

1. NTSC-style rates are exact rational values and canonical timing never depends on approximate 29.97/23.976 floats.
2. Timing inspection is bounded and clear VFR signals are detected without unbounded packet reads.
3. Source bytes remain unchanged; normalized/proxy/audio/generated/AI-processed outputs are separate Assets.
4. ffmpeg/ffprobe execution uses fixed argv, `shell=False`, bounded timeout and sanitized diagnostics.
5. 48 kHz analysis WAV is generated and validated when source audio exists.
6. CFR proxy is generated only when policy/inspection requires it and passes timing QA before registration.
7. ComfyUI public/untrusted endpoints are denied before network execution; configured resource floors fail closed before `/prompt`.
8. ComfyUI workflow classes are checked against `/object_info`; placeholder substitution is data-only.
9. ComfyUI history output must remain under the configured local output root and pass video/checksum validation before GENERATED_VIDEO registration.
10. Audacity OpenVINO Adapter discovers commands dynamically, refuses non-empty projects and uses only Product-owned input/output paths.
11. Noise Suppression output and Music Separation stems are media/checksum validated and registered as canonical derived AUDIO Assets with provider provenance.
12. Whisper/MusicGen/AudioSR capability presence can be reported without falsely claiming task-level execution support.
13. Unit, boundary-negative, integration, regression, contract and fault tests pass; package/docs/Git are synchronized.
14. Missing user local runtimes may leave live-performance Evidence pending, but must never be fabricated.
