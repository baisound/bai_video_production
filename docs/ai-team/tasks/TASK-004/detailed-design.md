# TASK-004 — Detailed Design

## 1. Three-lane architecture

TASK-004 contains three independently bounded lanes sharing TASK-003 Asset/Evidence contracts.

- **Lane A:** source Asset → timing inspection → normalization decision → derived CFR proxy / 48 kHz analysis audio → normalization manifest/Evidence.
- **Lane B:** ComfyUI local runtime → resource admission → workflow validation/submission → generated output → canonical GENERATED_VIDEO Asset → generation manifest/Evidence.
- **Lane C:** Audacity sandbox + mod-script-pipe → OpenVINO effect discovery/execution → processed WAV/stems → canonical AUDIO Assets → audio-AI manifest/Evidence.

Timeline placement and creative selection remain downstream contracts.

## 2. Exact timebase

`FrameRate` stores numerator/denominator as `Fraction`. Frame/time conversion uses rational/integer arithmetic with explicit FLOOR/CEIL/NEAREST policy. Common NTSC rates therefore remain exact and no canonical timing contract stores `29.97` as an approximate float.

`FFprobeTimingProbe` performs a normal structural probe plus a bounded packet sample. VFR classification considers exact avg/rate disagreement and materially variable positive PTS deltas. Sampling is capped by a configured packet/time window.

## 3. Normalization policy

A profile selects target frame rate and whether a proxy must be forced. CFR source video can remain the canonical source Asset when no video transform is necessary. VFR/forced material is transformed to a separate CFR proxy Asset. Audio is extracted to a separate 48 kHz PCM WAV when present.

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

Requests use bounded connect/read timeouts. No browser automation is required. Secrets are excluded from canonical manifests/Evidence.

## 8. ComfyUI workflow contract

A workflow is supplied in API-format JSON. Recursive substitution replaces exact typed placeholders such as `{{PROMPT}}`, `{{SEED}}`, `{{WIDTH}}`, `{{HEIGHT}}`, `{{LENGTH_FRAMES}}`. There is no Python `eval` or expression engine.

Every `class_type` is checked against `/object_info` before `/prompt`. MiniMax H3 Native is the preferred first profile. MiniMaxH3-Easy is optional compatibility only.

## 9. ComfyUI Resource Admission

Before queue submission the adapter reads `/system_stats`. If configured, it requires GPU visibility and a minimum *verified* free-VRAM floor. Unknown or insufficient free VRAM fails closed. Disk free-space is also checked for Product staging/output roots.

This is a narrow TASK-004 safety slice; TASK-020 remains the owner of full admission/monitoring.

## 10. Generated output ownership

ComfyUI history is untrusted external-runtime data. Returned filename/subfolder/type metadata is normalized and must resolve under the configured ComfyUI output root. Absolute-path injection, traversal and symlink escape are rejected. The selected file must contain a video stream.

The file is copied into Product staging, hashed and published as `GENERATED_VIDEO`. Provenance records runtime/profile/model family, workflow checksum, prompt checksum, seed, mode, requested dimensions/frame count and safe device/runtime metadata.

## 11. Audacity/OpenVINO license and process boundary

Intel `openvino-plugins-ai-audacity` is GPL-3.0 and is implemented as an Audacity module. TASK-004 does not copy its source, link it into Product Core, or claim it as Product code. The Product drives an installed user-local Audacity runtime via Audacity's documented `mod-script-pipe` automation boundary.

This process separation also reflects Audacity's own security warning: scripting can read/write files and should not be exposed as a web service. The Adapter therefore supports local pipes only and does not expose a network listener.

## 12. Audacity sandbox policy

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

## 13. Dynamic OpenVINO effect discovery

Audacity command IDs and plugin parameters may change between versions. The provider therefore does not assume one permanent scripting ID. `GetInfo: Type=Commands` is parsed and matched by normalized action/name strings for:

- OpenVINO Noise Suppression;
- OpenVINO Music Separation;
- OpenVINO Whisper Transcription;
- OpenVINO Music Generation;
- OpenVINO Super Resolution.

The discovered command descriptor and parameter schema are retained in capability Evidence. Executable Noise Suppression / Music Separation calls use either caller-supplied parameters validated against discovered names or conservative discovered defaults. Unknown requested parameters are rejected before effect execution.

## 14. Noise Suppression operation

Noise Suppression imports one source track into the empty sandbox, applies the discovered OpenVINO Noise Suppression effect and exports lossless WAV to Product staging. The result is ffprobe-validated and published as a derived AUDIO Asset. Device/model/effect descriptor, input/output checksums and runtime result are recorded.

## 15. Music Separation operation

Music Separation imports one source track and invokes OpenVINO Music Separation in caller-selected `2_STEM` or `4_STEM` mode. After execution, `GetInfo: Type=Tracks` identifies newly generated tracks. Expected stem roles are mapped by normalized track-name suffixes (Vocals/Instrumental or Drums/Bass/Other/Vocals), not by blind positional assumptions. Each stem is individually selected/exported as WAV, validated and published as a canonical AUDIO Asset.

If expected stems cannot be proved, no stem set is declared complete; the operation fails with diagnostic Evidence.

## 16. Capability-only OpenVINO features

Whisper, MusicGen and Audio Super Resolution are discovered and exposed in the capability report during TASK-004, but their end-to-end Product workflows remain downstream:

- Whisper → TASK-006 / TASK-023;
- MusicGen → TASK-013;
- Audio Super Resolution → later audio enhancement slice/TASK-013-family decision.

TASK-004 does not fake execution Evidence for these features.

## 17. Idempotency and failure handling

Normalization, local-video generation and local-audio processing reserve Job-scoped operations. COMPLETED replay returns canonical prior results. No Asset/manifest becomes canonical until bytes pass structural/checksum QA.

Timeout/resource/runtime errors are explicit Product errors. Staging is never exposed as a canonical Asset. A process crash after Asset publication is repaired from producer-operation binding when the canonical checksum still matches; mismatched/missing canonical output fails closed rather than recreating truth from untrusted bytes.
