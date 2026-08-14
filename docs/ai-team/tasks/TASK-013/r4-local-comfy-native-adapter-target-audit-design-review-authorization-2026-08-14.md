# TASK-013 — R4 Local ComfyUI Native Adapter Target Audit / Design Review / Authorization

- Date: `2026-08-14`
- Branch: `codex/task-013-r4-local-adapter-target-audit`
- Base main: `b47b4b722e387af906ce80b06b72b03f28d1ba7f`
- Owner route: `R4 TASK-013 local execution control -> exact free/local adapter -> contained native Evidence`
- Task identity: `TASK-013` (unchanged)
- DEV Profile: `DEV-4`

## Current-checkout audit

The current checkout is newer than the historical handoff and remains the implementation Source of Truth. TASK-013's bounded execution controller is already hosted-closed, but its trusted launcher deliberately injects no concrete Provider port. The missing unit is therefore an exact local adapter and contained native proof, not a new orchestration system.

The local target was inspected without changing any production project and without reading a Prompt body into Product Evidence:

- ComfyUI installation: `BAI VIDEO COMFY`, ComfyUI `0.31.0`, frontend `1.48.7`, Python `3.13.12`, PyTorch `2.12.1+cu130`;
- endpoint: `http://127.0.0.1:8188`, bare loopback origin only;
- runtime: Windows local desktop standalone;
- device: NVIDIA GeForce RTX 4070 SUPER, `12,878,086,144` total VRAM and `11,606,687,744` free bytes at the capability probe;
- node inventory: `837` classes;
- isolated probe roots: repository-ignored `runtime/task013-comfy-audit/{input,output,user,temp}`;
- shared model configuration is read-only and points to the installed Comfy Desktop shared model store.

The exact installed native H3 profile is present:

- diffusion model `minimax_h3_fl2va_pruned_int8_convrot.safetensors`;
- text encoder `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` with CLIP type `minimax`;
- video VAE `minimax_h3_video_vae_fp16.safetensors`;
- audio VAE `minimax_h3_audio_vae_fp32.safetensors`;
- native classes `MiniMaxH3ImageToVideo`, `UNETLoader`, `CLIPLoader`, `VAELoader`, `BasicGuider`, `BasicScheduler`, `SamplerCustomAdvanced`, `VAEDecode`, `VAEDecodeAudio`, `CreateVideo` and `SaveVideo` are available;
- native sampler/schedule is `res_multistep` / `simple`, `20` steps, denoise `1`;
- H3's verified frame contract accepts `5 + 17k` frames, with `5` as the minimum capability-probe length.

The operator workflow `video_minimax_h3_t2v.json` is valid UTF-8 JSON with SHA-256 `9eab39add6bb37e647b34235854569bd247cb265ff1db1f207f70555761228a9`. It contains a 15-node native subgraph and a top-level `SaveVideo`. Its Prompt and note strings are private operator content. The file is therefore capability/design Evidence only and must not be copied, committed, logged or used directly by the Product adapter.

The installed `api_minimax_h3_*` template files use cloud/API Hailuo node families. They are not the selected `LOCAL_FREE_AI` target and must not be substituted for the native local graph.

## Registry and owner decision

Existing owner `TASK-013` is correct. No new TASK is allocated and TASK-004 is not reopened. TASK-004's ComfyUI transport and containment helpers may be reused, while TASK-013 owns the Queue-to-creative-execution Product boundary.

The next implementation slice is authorized as `TASK-013 / DEV-4` with this exact target:

1. a package-owned, body-free MiniMax H3 text-to-video API workflow resource derived only from the reviewed technical topology;
2. a concrete `LocalGenerationExecutionPort` for `LOCAL / LOCAL_FREE_AI / TEXT_TO_VIDEO` only;
3. exact loopback endpoint, workflow checksum, model choice, node availability and resource admission checks before queueing;
4. Product-owned input, staging, Comfy output and canonical `project-output://` roots, with traversal/symlink/ambiguous-output rejection;
5. persisted Comfy `prompt_id`, bounded polling, a single canonical video, media/checksum verification and no automatic replay after uncertain dispatch;
6. optional trusted-launch composition only when an explicit local-adapter configuration is present; default launch remains unavailable/fail-closed;
7. a contained native capability run using a non-production test Prompt, minimum bounded duration and no paid Provider.

## Allowed files

- `src/ai_video_production/` for the concrete adapter, trusted composition and package resource;
- `tests/` for adapter, launcher, failure/recovery and package-resource gates;
- `pyproject.toml` only if package-data registration is required;
- `CHANGELOG.md` for the Product change;
- `PROJECT.md`, canonical roadmap, current state and task index;
- TASK-013 design and Evidence documents.

Raw generated media, runtime logs, private Prompt bodies, shared Comfy settings and operator workflows are prohibited from staging.

## Builder design

The adapter receives only the already-authorized route and body-private execution request. It does not select a different Provider or infer paid authority. Before side effects it verifies route identity, exact capability, configured roots, workflow checksum, required node/model choices and resource floors. It substitutes only typed `PROMPT`, `SEED` and a Product-owned output prefix.

The parent controller already writes `DISPATCHING` before the port call. The port therefore never retries or requeues. A known Comfy validation/execution failure becomes a terminal structured failure. Timeout, transport loss or missing history after dispatch remains an uncertain recovery condition and cannot be converted into a second queue request.

On success the adapter resolves exactly one video below the configured Comfy output root, probes it as video, copies it atomically into a project-contained canonical output directory, verifies the copied SHA-256 and returns a `project-output://` reference. It does not create a TASK-037 Candidate, a TASK-040 Attempt or a TASK-038 decision in this slice.

## Critic review

1. **Critical — operator Prompt leakage through workflow reuse.** Resolution: reject direct use of the operator workflow; ship a new body-free API resource and inject only the current private Prompt at runtime.
2. **Critical — cloud/API template could violate free/local authority.** Resolution: require the exact local Provider family/cost class and native node/model allowlist; installed Hailuo API templates are explicitly excluded.
3. **Critical — ambiguous external state could duplicate a generation.** Resolution: retain parent pre-dispatch persistence, persist/return the Comfy prompt identity, never retry in the port and surface uncertain post-dispatch state for Human recovery.
4. **High — shared output could mutate or ingest unrelated files.** Resolution: launch and resolve only explicit Product-owned roots and a unique execution prefix; require exactly one output descriptor.
5. **High — malicious workflow or endpoint drift.** Resolution: package-owned checksum, bare loopback policy, node/model enum validation, no symlinks and exact class allowlist.
6. **High — apparent media success without playable video.** Resolution: bounded media probe plus source/canonical-copy checksum verification before returning success.
7. **High — trusted launcher silently enabling generation.** Resolution: concrete composition is opt-in through explicit validated configuration; default behavior remains unavailable.
8. **Medium — native probe overclaims quality or R4 completion.** Resolution: claim only contained native execution/transport Evidence; Candidate/Audit/Prompt Attempt integration and production-quality Human judgment remain later gates.

Unresolved Critical/High findings: `0 / 0` after the above design controls.

## Final plan and authorization

Implementation Authorization is `APPROVED` for the bounded exact target above. Implementation order is:

1. package-owned API workflow and schema/checksum tests;
2. fail-closed concrete port and exhaustive fake-client tests;
3. optional trusted-launch composition and UI availability tests;
4. focused and full regression plus Windows/WSL2 compile/diff/package gates;
5. contained native H3 run with non-production input;
6. Critic review, local closure, hosted PR checks, exact main merge and hosted closure;
7. only after native contained output, design the separate Candidate/TASK-040 Attempt binding slice.

No paid Provider, credit purchase, production project mutation, Candidate acceptance/LOCK, Resolve/Cubase mutation, package version change, Tag or Release is authorized by this audit.
