# TASK-004 — Media Normalization + Local Visual/Audio AI Runtime Foundation

- Status: `IMPLEMENTATION_COMPLETE_AWAITING_LIVE_CAPABILITY_EVIDENCE`
- Authorization: `OWNER_AUTHORIZED_IMPLEMENTATION`
- Historical alias: `VIDEO-TASK-004`
- Package target: `0.4.0`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Adaptive score: `25`
- Scope amendments: `OWNER_AUTHORIZED` — Local Image AI (Stable Diffusion / FLUX), Character Identity, H3 Production Brief, H3 Single-Frame Transform, Spectrum optional acceleration and H3 Foley/SFX experimental provider are included before TASK completion.

## Objective

Establish the exact media-time foundation required by subtitles, filler/cut planning and Resolve assembly, while also delivering replaceable local Image/Video/Audio AI runtime foundations on top of TASK-003 Asset Registry.

## Character Identity / H3 production foundation

- TASK-004 establishes a bounded Character Identity foundation for later AI video consistency work.
- Character identity is represented by a Product-native profile plus a same-Job reference bundle of canonical IMAGE Assets.
- Validation proves same-Job scope, IMAGE-only references, derivative-rights eligibility and optional production-lock approval.
- H3 Production Brief compilation preserves reference order/roles and explicit retention policy without bundling third-party system-prompt text.
- MiniMax H3 Single-Frame Transform is an optional external-node capability for character/pose/reference refinement, not a replacement for ordinary image generation.
- Spectrum is optional and approximate; Native remains the quality-first default and competing acceleration wrappers are mutually exclusive.
- H3 Foley/SFX adds a local generation engine only; automatic SE decision/placement remains TASK-013/TASK-026.

TASK-004 has four bounded execution lanes plus one cross-cutting admission/evidence layer. They share Asset/Evidence contracts but do not collapse downstream creative or timeline responsibilities into this task.

## Lane A — Timebase / Proxy / Normalization

- exact rational frame-rate representation (including 30000/1001 and 24000/1001);
- bounded ffprobe timing inspection and VFR/CFR classification;
- source-checksum revalidation before transformation;
- 48 kHz PCM analysis-audio derivation;
- CFR proxy derivation when VFR/policy requires it;
- structural/duration/timebase QA before canonical registration;
- normalization manifest and Evidence;
- affine whole-file source→normalized handoff for TASK-022.

## Lane B — Local Image AI / ComfyUI / FLUX + Stable Diffusion

- reuse the same ComfyUI local Server API trust boundary as video generation;
- T2I and I2I executable Product contracts using API-format workflow JSON;
- FLUX.1 Schnell is the preferred fast built-in model profile because its official model card declares Apache-2.0 and 1–4 step generation;
- FLUX.1 Dev is registered as a restricted/conditional runtime profile and is not auto-selected for commercial runtime use without explicit license authorization;
- SDXL 1.0 is supported as an OpenRAIL++ compatibility profile;
- SD3/SD3.5 is capability/provider-ready with explicit conditional-license Evidence;
- SD1.5 is retained as a legacy/LoRA/ControlNet compatibility family rather than the preferred default;
- output-root containment/symlink/traversal defense;
- generated-image structural/checksum validation and canonical IMAGE Asset registration;
- model/workflow/prompt/seed/device/license provenance and conservative rights defaults;
- Inpainting/ControlNet/LoRA contracts remain capability/profile-ready unless a low-cost implementation falls naturally inside this TASK.

## Lane C — Local Video AI / ComfyUI / MiniMax H3

- ComfyUI local Server API adapter (`/system_stats`, `/object_info`, `/prompt`, `/history/{prompt_id}`);
- loopback/private/explicit-local endpoint policy; public endpoints denied by default;
- workflow API-JSON validation and typed placeholder substitution without eval;
- minimum GPU/VRAM Resource Admission before queue submission;
- MiniMax H3 Native workflow profile as first intended provider, with conditional Community-License acknowledgement/territory-review Evidence before execution;
- Product-owned H3 Production Brief Builder with immutable reference ordering/roles and reserved-tag injection protection;
- optional H3 Single-Frame Transform provider requiring independently installed custom nodes and explicit external-node authorization;
- optional Spectrum acceleration (`NATIVE` default; quality/fast approximate modes) with class detection, mutual-exclusion validation and Native fallback;
- optional MiniMaxH3-Easy compatibility profile without hard dependency;
- T2V/I2V/First-Last/Reference request contract with same-Job canonical reference-Asset staging into Product-owned ComfyUI input subdirectories;
- output-root containment/symlink/traversal defense;
- generated-video media/checksum validation and canonical GENERATED_VIDEO Asset registration;
- model/workflow/prompt/seed/device provenance and conservative rights defaults.

## Lane D — Local Audio AI / Audacity OpenVINO Boundary

- GPL-3.0 Intel OpenVINO Audacity plugin code is NOT copied into BAI Core;
- Audacity `mod-script-pipe` is treated as an external local runtime boundary;
- runtime capability discovery is performed through Audacity scripting commands rather than assuming effect IDs/parameters;
- Noise Suppression and Music Separation (2-stem/4-stem) are executable provider operations;
- provider runs only against an empty/sandbox Audacity project and fails closed if existing tracks are detected;
- outputs are exported to a Product-owned staging directory, media/checksum validated, and registered as canonical derived AUDIO Assets;
- OpenVINO device/model/effect-command provenance and Evidence are retained;
- Whisper, MusicGen and Audio Super Resolution are capability-discovered/provider-ready in TASK-004, while their product workflows remain owned by TASK-006/023 and TASK-013;
- H3 Foley/SFX provider with standard 1–15 s generation plus separately acknowledged experimental FAST_32 and 16–45 s profiles;
- no automatic installation/download of Audacity, plugins or model weights.

## Cross-cutting — Resource Admission / Provider Evidence

TASK-004 implements only the minimum admission floor needed before expensive local generation/inference: runtime availability, device visibility, verified free VRAM where applicable, disk-space floor, model/workflow capability validation and explicit execution authorization. Full monitoring/admission remains TASK-020.

Every generated/processed Asset retains provider/model/workflow/version/license/provenance checksums without storing raw prompts in canonical Evidence. Commercial-runtime suitability is a separate policy gate from rights to generated output; unknown/conditional provider licenses fail closed when a caller explicitly requests commercial runtime authorization.

## Out of scope

- exact edit/cut/subtitle/SE/BGM/narration/image/video placement on a Resolve timeline (`TASK-022`, `TASK-010`, `TASK-026`);
- automatic creative decision of where generated media belongs (`TASK-007/008`);
- full Resource Admission/Monitoring system (`TASK-020`);
- automatic download/install/update of ComfyUI, model weights, Audacity, OpenVINO plugins or third-party custom nodes;
- public/remote ComfyUI endpoints by default;
- copying/linking GPL Audacity OpenVINO implementation into Product Core;
- falsely declaring MiniMax H3, FLUX/Stable Diffusion or OpenVINO model performance PASS without live user-runtime Evidence.

## Acceptance criteria

1. NTSC-style rates are exact rational values and canonical timing never depends on approximate 29.97/23.976 floats.
2. Timing inspection is bounded and clear VFR signals are detected without unbounded packet reads.
3. Source bytes remain unchanged; normalized/proxy/audio/generated/AI-processed outputs are separate Assets.
4. ffmpeg/ffprobe execution uses fixed argv, `shell=False`, bounded timeout and sanitized diagnostics.
5. 48 kHz analysis WAV is generated and validated when source audio exists.
6. CFR proxy is generated only when policy/inspection requires it and passes timing QA before registration.
7. ComfyUI public/untrusted endpoints are denied before network execution; configured resource floors fail closed before `/prompt`.
8. ComfyUI workflow classes are checked against `/object_info`; placeholder substitution is data-only.
9. Image generation supports canonical T2I/I2I requests and only publishes a single unambiguous image under the configured output root after structural/checksum validation.
10. FLUX/Stable Diffusion provider profiles retain explicit model/license policy Evidence; commercial-runtime requests fail closed for `RESTRICTED`, `CONDITIONAL` or `UNKNOWN` profiles unless explicitly authorized by caller-supplied license Evidence.
11. Video generation output must remain under the configured local output root and pass video/checksum validation before GENERATED_VIDEO registration; MiniMax H3 execution requires explicit conditional-license acknowledgement Evidence and reference modes accept only validated same-Job canonical Assets.
12. Audacity OpenVINO Adapter discovers commands dynamically, refuses non-empty projects and uses only Product-owned input/output paths.
13. Noise Suppression output and Music Separation stems are media/checksum validated as a complete batch before canonical publication and registered as derived AUDIO Assets with per-operation provider/role provenance in the manifest.
14. Whisper/MusicGen/AudioSR capability presence can be reported without falsely claiming task-level execution support.
15. Unit, boundary-negative, integration, regression, contract and fault tests pass; package/docs/Git are synchronized.
16. H3 Production Brief reference order/role invariants, Single-Frame frame-count normalization/custom-node authorization, Spectrum mutual exclusion and H3 Foley experimental acknowledgements are enforced before queue submission.
17. ComfyUI external `prompt_id` is persisted before result processing; replay must reconcile or fail closed and cannot blindly duplicate an already-dispatched generation.
18. Missing user local runtimes may leave live-performance Evidence pending, but must never be fabricated.
