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

### Fresh-source ingest stability on Windows

TASK-003 source ingest remains the canonical admission boundary for TASK-004 synthetic/runtime inputs. Size drift during the streaming copy is an immediate `DATA_INTEGRITY` failure. A last-write timestamp drift **without size drift** is treated as a metadata warning rather than standalone proof that bytes changed: the Product rewinds and re-hashes the **same already-open regular-file handle** and requires the second-pass checksum and byte count to exactly equal the staged-copy checksum/size. If that content revalidation disagrees, ingest still fails `ERR_INPUT_SOURCE_CHANGED_DURING_INGEST`. The source path is not reopened, so revalidation cannot silently switch to a replacement path target. This is the package 0.4.6 corrective for Attempt 06 and preserves the source-mutation Safety Floor while tolerating Windows timestamp finalization/approximation behavior.

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

### Windows mod-script-pipe transport framing

The Windows pipe transport MUST follow Audacity's own `pipe_test.py` framing contract exactly: commands written to `\\.\pipe\ToSrvPipe` terminate with `CRLF + NUL` (`\r\n\0`), while POSIX uses LF. The Product must not normalize the Windows terminator to a plain LF. Replies are read from `FromSrvPipe` until the Audacity blank-line response delimiter, under bounded byte/line limits and an external supervisor timeout. This is transport framing only; it does not change effect authorization or execution policy.

This process separation also reflects Audacity's own security warning: scripting can read/write files and should not be exposed as a web service. The Adapter therefore supports local pipes only and does not expose a network listener.

## 17. Audacity sandbox policy

Before any effect:

1. connect to the local script pipe;
2. execute `GetInfo: Type=Tracks Format=JSON`;
3. require zero existing tracks; otherwise fail `ERR_AUDIO_RUNTIME_EXISTING_PROJECT_PROTECTED`;
4. import only a Product-controlled WAV/source file;
5. select the imported track/time range;
6. invoke an effect command discovered through bounded Audacity `Help` lookup for the five TASK-004 OpenVINO command IDs;
7. export only to Product-owned staging;
8. remove the sandbox tracks on completion/failure where safely possible.

No real/client Audacity project is modified by an authorized BAI operation.

## 18. Dynamic OpenVINO effect discovery

Normal discovery is intentionally bounded. Audacity derives script command IDs from effect symbols with its `GetSquashedName` rule, so TASK-004 queries the five OpenVINO command IDs it understands through side-effect-free `Help: Command=... Format=JSON` calls rather than enumerating the user's entire plugin inventory. The bounded targets are:

- `OpenvinoNoiseSuppression`;
- `OpenvinoMusicSeparation`;
- `OpenvinoWhisperTranscription`;
- `OpenvinoMusicGeneration`;
- `OpenvinoSuperResolution`.

The returned descriptor is retained in capability Evidence and its `id` must match the requested command. `GetInfo: Type=Commands` remains diagnostic/fallback code only. Unknown caller-supplied effect parameters are rejected before execution.

Target Attempt 05 proved all five commands live-reachable. The returned Intel OpenVINO descriptors expose empty `params` arrays. Product code therefore distinguishes **scriptable parameters** from **UI-only effect state** and does not pretend that every visible Audacity control can be selected through `mod-script-pipe`.

## 19. Noise Suppression operation

Noise Suppression imports one source track into the empty sandbox, applies the discovered OpenVINO Noise Suppression effect and exports lossless WAV to Product staging. The result is ffprobe-validated and published as a derived AUDIO Asset. Device/model/effect descriptor, input/output checksums and runtime result are recorded.

## 20. Music Separation operation

Music Separation imports one source track and invokes the discovered Intel OpenVINO Music Separation effect. After execution, `GetInfo: Type=Tracks` identifies newly generated tracks. Expected stem roles are mapped by normalized track-name suffixes rather than blind positional assumptions, and `Export2` is used with Audacity's selected-only export path for each selected stem.

The target runtime's live `Help` descriptor contains no scriptable mode parameter. Intel's effect implementation initializes `m_separationModeSelectionChoice = 0`, defines choice 0 as `(2 Stem) Instrumental, Vocals`, and choice 1 as `(4 Stem) Drums, Bass, Vocals, Others`. Therefore Product 0.4.6 allows the exact Intel effect's **no-parameter 2-stem runtime default** and records `parameter_strategy=INTEL_RUNTIME_DEFAULT_2_STEM`. It does **not** silently claim 4-stem automation: when the runtime exposes no scriptable separation-mode parameter, a `4_STEM` request fails `ERR_PROVIDER_OPENVINO_4_STEM_NOT_SCRIPTABLE`. A future plugin/runtime that exposes a provable mode parameter may re-enable 4-stem through the generic discovered-parameter path.

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

## 24. Character Identity foundation

TASK-004 defines a Product-native `CharacterIdentityProfile`; it does not make an external character-skill repository a runtime dependency. A profile owns semantic identity constraints while the binary reference bundle is composed only from canonical same-Job `IMAGE` Assets admitted through TASK-003.

- `face_anchor` is mandatory for a production-locked reference bundle; front/side/back/detail references are optional.
- every reference Asset is checksum revalidated, must belong to the request Job and must allow derivative processing before local AI staging;
- immutable traits, allowed variation and forbidden drift are explicit data, not prose-only prompt conventions;
- profile reuse across Jobs is allowed only as metadata; reference bytes must be re-admitted into the target Job before generation;
- generated reference refinements remain ordinary derived Assets and require human identity QA before becoming a new locked bundle;
- voice-identity fields are metadata handoff for TASK-014 and are not treated as proof of consent or TTS authorization.

The Character Identity layer is intentionally provider-neutral so FLUX/SDXL/H3 or later local providers can consume the same identity contract.

## 25. H3 Production Brief Builder

TASK-004 implements a deterministic Product-owned compiler that turns generation intent plus canonical reference bindings into a structured H3 production brief. The implementation may learn from public prompting examples, but no third-party system prompt text is bundled or executed as a dependency.

Contract rules:

- reference order is immutable and labels are assigned deterministically as `<Picture N>`, `<Video N>`, `<Audio N>`;
- free-text fields may not inject reserved reference labels;
- First/Last Frame roles accept `IMAGE` only, at most one of each, and must appear as a pair;
- reference count is bounded to 9 images, 3 videos, 3 audio items and 15 total;
- each reference records a semantic role and retention policy rather than relying on position alone;
- the brief represents subject definitions, shot timing, camera behavior, visible end state, dialogue/diegetic SFX/soundscape/non-diegetic music as structured fields;
- `1..15 s` is the standard duration tier. `16..45 s` is an explicitly experimental contract tier and is never presented as an official H3 capability guarantee;
- canonical Evidence stores hashes/structured metadata and avoids storing raw user prompts by default.

This compiler is later consumable by TASK-007/008 creative planning without coupling those downstream decisions into TASK-004.

## 26. MiniMax H3 Single-Frame Transform provider

`ComfyUI-MiniMaxH3-SingleFrame` is treated as an independently installed experimental ComfyUI custom-node capability. Its source is not copied into Product Core and execution requires an explicit external-node local-use authorization reference because no repository license was verified at integration-design time.

Product modes:

- `SINGLE_FRAME_EDIT`: one canonical IMAGE reference;
- `START_END_INTERPOLATE`: two canonical IMAGE references;
- optional Temporal RoPE policy for still-image-like transforms.

The Product normalizes requested H3-compatible frame counts to the minimum value `>= 5` satisfying `frame_count % 17 == 5`, records requested and actual counts, bounds selected-frame access, validates required custom-node classes through `/object_info`, and applies the same local endpoint/resource/license/output containment gates as ordinary H3 generation.

This provider is not the default still-image engine. FLUX/SDXL remain normal image-generation routes; H3 Single-Frame is a specialized route for character/pose transformation, reference refinement and start/end interpolation.

## 27. MiniMax H3 Spectrum acceleration policy

Spectrum is an **optional external accelerator**, never a MiniMax H3 dependency and never the Production default. Product Core does not copy the GPL-licensed Spectrum implementation. The independently installed ComfyUI node is detected as class `SpectrumApplyMiniMaxH3` and stays behind the existing ComfyUI runtime boundary.

Acceleration contract:

- `NATIVE` is the default quality-first mode;
- `SPECTRUM_QUALITY` and `SPECTRUM_FAST` are explicit approximate modes and require the Spectrum class in the submitted workflow;
- workflow validation forbids combining Spectrum with competing H3 cache/forecast wrappers on the same model branch; ambiguous combinations fail before `/prompt`;
- Product records the selected acceleration mode, workflow hash, external-node identifier/license state and resource policy in operation provenance;
- Spectrum parameters remain workflow-owned unless the Product has an explicitly versioned preset contract; Product does not guess third-party parameter names/defaults;
- quality-critical output may be routed to Native and benchmark comparisons use same model/prompt/seed/workflow inputs where possible;
- accelerator output remains subject to normal human visual/audio QA because Spectrum is approximate and may alter the generation trajectory.

`history_storage=VRAM` may only be selected when Resource Admission can prove the configured free-VRAM floor. Otherwise a workflow must use system RAM or Native according to policy.

## 28. H3 Foley / SFX experimental provider

TASK-004 adds a bounded local SFX generation engine using H3 audio generation while keeping later automatic SE selection/placement owned by TASK-013/TASK-026.

Profiles:

- `STANDARD`: normal H3 audiovisual workflow and official-length policy (`1..15 s`);
- `FAST_32`: community-derived experimental profile that requests `32x32` video, discards the visual result and extracts the generated audio. It requires a separate experimental acknowledgement and is never described as an official performance capability;
- `16..45 s`: separate experimental duration tier requiring an additional acknowledgement; durations above 45 seconds are rejected by the TASK-004 contract.

Optional reference audio must be a canonical same-Job AUDIO/SFX/BGM Asset with derivative rights and verified checksum before Product-owned ComfyUI staging. The completed H3 container is validated under the configured output root, then audio is extracted with fixed-argv ffmpeg to 48 kHz PCM WAV, QA checked and published as canonical `SFX` through the shared derived-asset publisher.

Evidence records provider/workflow/model/seed/duration/resolution/reference hashes, experimental flags and output checksums. Human audio QA remains required; community speed/quality observations are not converted into a Product PASS claim without user-runtime Evidence.

## 29. External-generation replay and idempotency floor

All local AI executions are expensive external side effects even when they remain on the user's machine. Therefore operation idempotency binds an idempotency key to a canonical request fingerprint, not only to a broad command name.

For ComfyUI-backed operations:

1. reserve operation before queue submission;
2. once `/prompt` returns `prompt_id`, persist that external reference immediately while status remains `IN_PROGRESS`;
3. replay of an operation with a persisted `prompt_id` must reconcile through `/history/{prompt_id}` or fail closed; it must not blindly queue a second generation;
4. only after output validation/publication is the operation marked `COMPLETED` with canonical Asset result reference;
5. changed request payload under the same idempotency key is an integrity conflict.

The same principle applies to Audacity/OpenVINO; where the external runtime lacks a stable resumable job identifier, an ambiguous post-dispatch crash fails closed for reconciliation rather than automatically repeating a destructive/expensive effect. Worker phase Evidence is written before the first project mutation and around import/effect/export/cleanup; a timeout at or after `IMPORTING_SOURCE` persists the Product operation as `PARTIAL`, while a timeout proven to occur before that boundary may remain replayable `FAILED`.
