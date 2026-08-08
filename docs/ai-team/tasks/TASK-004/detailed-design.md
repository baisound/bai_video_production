# TASK-004 — Detailed Design

## 1. Four-lane architecture

TASK-004 contains four independently bounded execution lanes sharing TASK-003 Asset/Evidence contracts.

- **Lane A — Media Foundation:** source Asset → timing inspection → normalization decision → derived CFR proxy / 48 kHz analysis audio → normalization manifest/Evidence.
- **Lane B — Local Image AI:** ComfyUI local runtime → license/resource admission → workflow validation/submission → generated image → canonical IMAGE Asset → generation manifest/Evidence.
- **Lane C — Local Video AI:** ComfyUI local runtime → resource admission → workflow validation/submission → generated video → canonical GENERATED_VIDEO Asset → generation manifest/Evidence.
- **Lane D — Local Audio AI:** Audacity sandbox + mod-script-pipe → OpenVINO effect discovery/execution → processed WAV/stems → canonical AUDIO Assets → audio-AI manifest/Evidence.

A shared **Lane E policy layer** owns minimum Resource Admission, provider/license Evidence and Derived Asset publication. Timeline placement and creative selection remain downstream contracts.

## 2. Exact timebase

`FrameRate` stores numerator/denominator as `Fraction`. Frame/time conversion uses rational/integer arithmetic with explicit FLOOR/CEIL/NEAREST policy. Common NTSC rates therefore remain exact and no canonical timing contract stores `29.97` as an approximate float.

`FFprobeTimingProbe` performs a normal structural probe plus a bounded packet sample. VFR classification considers exact avg/rate disagreement and materially variable positive PTS deltas. Sampling is capped by a configured packet/time window.

## 3. Normalization policy

A profile selects target frame rate and whether a proxy must be forced. CFR source video can remain the canonical source Asset when no video transform is necessary. VFR/forced material is transformed to a separate CFR proxy Asset. Audio is extracted to a separate 48 kHz PCM WAV when present. When both proxy and analysis-audio outputs are required, both are generated and QA-validated in staging before either is canonically published.

The source Asset path is resolved from its Job-scoped logical URI and its registered checksum is reverified before ffmpeg/ffprobe reads it.

## 4. FFmpeg execution and QA

ffmpeg/ffprobe run with fixed argv, `shell=False`, `-nostdin`, bounded timeout and explicit return-code handling. Derived bytes are written into Product-owned staging, fsynced/probed/checksummed and atomically promoted to checksum-addressed logical URIs. Source bytes are never replaced.

Evidence stores sanitized command templates and stderr hash/tail with raw paths removed, executable version and QA results.

## 5. Time mapping handoff

TASK-004 emits a whole-file affine mapping (`source_start_us`, `normalized_start_us`, source/normalized durations and exact rates). It proves normalization provenance but does not implement edit/cut mapping. TASK-022 owns exact timeline/edit mapping.

## 6. Shared Derived Asset Publisher

All derived local outputs use one publisher that:

1. accepts only a caller-validated regular file;
2. hashes bytes before canonical registration;
3. stages beneath the configured Product Asset root;
4. atomically promotes to a deterministic checksum-addressed logical URI;
5. handles same-Job checksum races idempotently;
6. never overwrites a different checksum;
7. sets conservative rights/provenance unless stronger facts are explicitly supplied.

This prevents each local AI runtime from inventing a second Asset-write path.

## 7. ComfyUI trust boundary

The Product communicates with ComfyUI through the documented local Server API. Endpoint policy permits loopback/private addresses and optionally explicit allowlisted local hostnames. Public hosts, URL credentials, query/fragment confusion and unsupported schemes are denied.

Requests use bounded connect/read timeouts. No browser automation is required. Secrets and raw prompts are excluded from canonical manifests/Evidence; prompt hashes are retained.

## 8. Shared ComfyUI workflow contract

A workflow is supplied in API-format JSON. Recursive substitution replaces exact typed placeholders such as `{{PROMPT}}`, `{{NEGATIVE_PROMPT}}`, `{{SEED}}`, `{{WIDTH}}`, `{{HEIGHT}}`, `{{LENGTH_FRAMES}}` and caller-declared reference inputs. There is no Python `eval` or expression engine.

Every `class_type` is checked against `/object_info` before `/prompt`. Workflow bytes and rendered-contract metadata are checksummed. The Product does not hard-code a private/custom node implementation as a foundation dependency.

## 9. ComfyUI Resource Admission

Before queue submission the adapter reads `/system_stats`. If configured, it requires GPU visibility and a minimum *verified* free-VRAM floor. Unknown or insufficient free VRAM fails closed. Disk free-space is also checked for Product staging/output roots.

This is a narrow TASK-004 safety slice; TASK-020 remains the owner of full admission/monitoring.

## 10. Local Image AI model/profile contract

Image generation is modeled by a Product request independent of ComfyUI node names. Initial model-family profiles are:

- `FLUX_1_SCHNELL` — preferred fast local image profile. Official model card declares Apache-2.0 and 1–4 inference steps. Built-in policy: commercial runtime allowed subject to ordinary Product rights review.
- `FLUX_1_DEV` — high-quality compatibility profile. Official model license is non-commercial for model/runtime use unless separate authorization exists. Built-in policy: commercial runtime restricted; output rights are not conflated with model-runtime rights.
- `SDXL_1_0` — compatibility profile under CreativeML Open RAIL++-M. Built-in policy records the license and requires policy review rather than silently claiming unrestricted use.
- `SD3_5` — capability profile under Stability Community License. Because commercial terms depend on current license conditions/user circumstances, built-in policy is conditional and commercial runtime requires explicit authorization Evidence.
- `SD1_5` — legacy compatibility family for ecosystem assets such as checkpoints/LoRA/ControlNet. Built-in policy remains review-required unless a concrete model/checkpoint license is supplied.
- `CUSTOM` — always requires caller-supplied model identifier and license policy.

Provider profile selection is separate from workflow selection. A caller can use a supported custom workflow while still producing canonical provenance.

## 11. Image generation modes

TASK-004 executes:

- `TEXT_TO_IMAGE` — prompt/negative prompt/seed/dimensions via API workflow placeholders;
- `IMAGE_TO_IMAGE` — same request plus one Product Asset input/reference mapping handled by caller workflow substitutions.

Inpainting, ControlNet and LoRA are represented as capability/profile metadata during TASK-004; they may be executable if a supplied workflow needs no new Core contract, but they are not completion gates.

## 12. Generated image output ownership

ComfyUI history is untrusted external-runtime data. Image descriptors are collected from `outputs.*.images` and known image extensions. Exactly one canonical output is required for the initial Product API; multiple candidate images fail to Human Review rather than silently selecting one.

Filename/subfolder/type metadata is normalized and must resolve under the configured ComfyUI output root. Absolute-path injection, traversal, non-output descriptors and symlink escape are rejected. The selected file is ffprobe-validated as a visual/image stream, checksummed, copied into Product staging and published as Asset type `IMAGE` with generation provenance.

## 13. Image generation provenance and license gate

Canonical provenance records:

- provider/runtime = `COMFYUI_LOCAL`;
- model family + explicit model identifier;
- model license identifier and runtime policy state;
- workflow checksum;
- prompt and negative-prompt checksums (not raw text);
- seed, mode, requested width/height;
- source/reference Asset IDs where supplied;
- safe device/resource summary;
- capability/profile name.

When `commercial_runtime_requested=true`, built-in profiles in `RESTRICTED`, `CONDITIONAL` or `UNKNOWN` state fail closed unless the request carries explicit `license_authorization_ref`. This is an execution gate only; it does not assert copyright/ownership of generated output.

## 14. Generated video ownership

ComfyUI history is untrusted external-runtime data. Returned filename/subfolder/type metadata is normalized and must resolve under the configured ComfyUI output root. Absolute-path injection, traversal and symlink escape are rejected. The selected file must contain a video stream.

The file is copied into Product staging, hashed and published as `GENERATED_VIDEO`. Provenance records runtime/profile/model family, model-license policy, workflow checksum, prompt checksum, seed, mode, reference Asset bindings and safe device/runtime metadata.

Video reference inputs are not accepted as arbitrary host paths. Caller-declared workflow placeholders are bound to same-Job canonical Assets, re-checksummed, derivative-rights gated and copied into an operation-owned subdirectory below the configured ComfyUI input root. `TEXT_TO_VIDEO` accepts no reference Assets; I2V/First-Last/Reference modes enforce bounded compatible Asset sets. Staged references are deleted after the operation and stale Product-owned operation staging is safely replaced on retry.

## 15. MiniMax H3 profile and license gate

MiniMax H3 Native is the preferred first video profile. Product request modes map to ComfyUI native T2V/I2V/First-Last/Reference workflows without embedding browser/UI automation. MiniMaxH3-Easy remains an optional workflow compatibility profile rather than a Core dependency.

MiniMax H3 is not treated as an unrestricted open-source runtime. Its current Community License contains territory, use, redistribution and commercial-product conditions. The built-in profile is therefore `CONDITIONAL`; execution requires an explicit caller-supplied license authorization/acknowledgement reference, stored only as a checksum. Generated assets retain `MODEL_LICENSE_REVIEW_REQUIRED`/territory-review publication restrictions. This execution gate does not claim that an Output is legally publishable in every territory or use case.

Live performance, exact VRAM requirements and model-specific generation quality are Evidence from the user's runtime, not facts invented by unit tests.

## 16. Audacity/OpenVINO license and process boundary

Intel `openvino-plugins-ai-audacity` is GPL-3.0 and is implemented as an Audacity module. TASK-004 does not copy its source, link it into Product Core, or claim it as Product code. The Product drives an installed user-local Audacity runtime via Audacity's documented `mod-script-pipe` automation boundary.

This process separation also reflects Audacity's own security warning: scripting can read/write files and should not be exposed as a web service. The Adapter therefore supports local pipes only and does not expose a network listener.

## 17. Audacity sandbox policy

Before any effect:

1. connect to the local script pipe;
2. execute `GetInfo: Type=Tracks Format=JSON`;
3. require zero existing tracks; otherwise fail `ERR_AUDIO_RUNTIME_EXISTING_PROJECT_PROTECTED`;
4. import only a Product-controlled WAV/source file;
5. select the imported track/time range;
6. invoke an effect command discovered from `GetInfo: Type=Commands Format=JSON`;
7. export only to Product-owned staging;
8. remove the sandbox tracks on completion/failure where safely possible.

No real/client Audacity project is modified by an authorized BAI operation.

## 18. Dynamic OpenVINO effect discovery

Audacity command IDs and plugin parameters may change between versions. The provider therefore does not assume one permanent scripting ID. `GetInfo: Type=Commands` is parsed and matched by normalized action/name strings for:

- OpenVINO Noise Suppression;
- OpenVINO Music Separation;
- OpenVINO Whisper Transcription;
- OpenVINO Music Generation;
- OpenVINO Super Resolution.

The discovered command descriptor and parameter schema are retained in capability Evidence. Executable Noise Suppression / Music Separation calls use either caller-supplied parameters validated against discovered names or conservative discovered defaults. Unknown requested parameters are rejected before effect execution.

## 19. Noise Suppression operation

Noise Suppression imports one source track into the empty sandbox, applies the discovered OpenVINO Noise Suppression effect and exports lossless WAV to Product staging. The result is ffprobe-validated and published as a derived AUDIO Asset. Device/model/effect descriptor, input/output checksums and runtime result are recorded.

## 20. Music Separation operation

Music Separation imports one source track and invokes OpenVINO Music Separation in caller-selected `2_STEM` or `4_STEM` mode. After execution, `GetInfo: Type=Tracks` identifies newly generated tracks. Expected stem roles are mapped by normalized track-name suffixes (Vocals/Instrumental or Drums/Bass/Other/Vocals), not by blind positional assumptions. Each stem is individually selected/exported as WAV, validated and published as a canonical AUDIO Asset.

If expected stems cannot be proved, no stem set is declared complete. All reported stem descriptors, containment, media structure, checksums and the complete expected role set are validated as a batch **before any stem is published**; this prevents a failed partial separation from leaving a subset of stems as producer outputs.

## 21. Capability-only OpenVINO features

Whisper, MusicGen and Audio Super Resolution are discovered and exposed in the capability report during TASK-004, but their end-to-end Product workflows remain downstream:

- Whisper → TASK-006 / TASK-023;
- MusicGen → TASK-013;
- Audio Super Resolution → later audio enhancement slice/TASK-013-family decision.

TASK-004 does not fake execution Evidence for these features.

## 22. Idempotency, batch publication and failure handling

Normalization, local-image generation, local-video generation and local-audio processing reserve Job-scoped operations. COMPLETED replay returns canonical prior results. For multi-output operations, every output is produced and structurally/checksum validated first; only then does canonical Asset publication begin. This avoids predictable partial publication caused by a later sibling-output QA failure.

The TASK-003 registry intentionally deduplicates byte-identical Assets by Job checksum. Therefore canonical **Asset identity describes bytes**, while TASK-004 operation Manifest/Evidence describes each processing/generation event. If an output deduplicates to an already-existing Asset, the operation Manifest still retains provider/model/workflow/source/role provenance and an explicit output binding; the Product does not mutate the historical Asset merely to attach a second producer story.

Timeout/resource/runtime errors are explicit Product errors. Staging is never exposed as a canonical Asset. A process crash after Asset publication but before Manifest completion can leave valid checksum-addressed Assets; replay may reuse them only when the canonical checksum still matches and then completes the producer Manifest. Mismatched/missing canonical output fails closed rather than recreating truth from untrusted bytes.

## 23. Completion Evidence policy

Unit/integration tests may emulate local runtimes to prove Product contracts, containment, state/idempotency and failure behavior. They do not prove that the user's installed ComfyUI models or Audacity OpenVINO plugins exist or perform well.

TASK-004 can reach implementation-complete/checkpoint state without downloading third-party runtimes. If live runtime Evidence is unavailable, the final Judge must clearly distinguish `IMPLEMENTATION_COMPLETE` from provider-specific `LIVE_CAPABILITY_VERIFIED` rather than fabricating support.
