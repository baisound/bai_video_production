# TASK-004 — Failure Mode Design

| Failure | Required behavior |
|---|---|
| source checksum drift/tamper | fail before ffmpeg/AI runtime; no derived registration |
| malformed/zero frame-rate metadata | fail-safe unknown/explicit target; no float guess |
| ffprobe/ffmpeg missing | `EXTERNAL_DEPENDENCY` |
| ffprobe/ffmpeg timeout/nonzero | `TIMEOUT`/`EXTERNAL_DEPENDENCY`; staging not canonical |
| CFR-required output remains VFR | `DATA_INTEGRITY`; no registration |
| duration drift exceeds profile tolerance | QA failure; when proxy+audio are requested, validate the whole output batch before any registration |
| ComfyUI public/untrusted endpoint | `SECURITY` before request |
| ComfyUI stats cannot prove configured VRAM floor | `RESOURCE_EXHAUSTED`; `/prompt` not sent |
| workflow references unavailable class | `NOT_SUPPORTED` before queue |
| ComfyUI queue/history timeout | `TIMEOUT`; no canonical asset |
| ComfyUI history traversal/absolute/symlink output | `SECURITY` |
| generated image history contains zero/multiple canonical image candidates | `DATA_INTEGRITY` / `HUMAN_REVIEW_REQUIRED`; do not guess output |
| generated image output is missing/non-visual | `DATA_INTEGRITY`; no registration |
| image model profile has restricted/conditional/unknown commercial runtime policy and commercial execution is requested without authorization Evidence | `AUTHORIZATION`; `/prompt` not sent |
| caller supplies a custom model profile without model/license identifiers | `VALIDATION`; `/prompt` not sent |
| ComfyUI video output missing/non-video | `DATA_INTEGRITY`/`EXTERNAL_DEPENDENCY` |
| MiniMax H3 conditional license not explicitly acknowledged/authorized | `AUTHORIZATION`; `/prompt` not sent |
| video reference Asset cross-Job/tampered/rights-denied or staged outside Comfy input root | `SECURITY`/`DATA_INTEGRITY`/`AUTHORIZATION`; `/prompt` not sent |
| stale Product-owned Comfy reference staging from prior crash | safely replace only the deterministic operation-owned directory; never delete arbitrary Comfy input files |
| Audacity script pipe missing | `EXTERNAL_DEPENDENCY`; no project mutation |
| Audacity current project has tracks | `SECURITY`; fail closed before import/effect |
| OpenVINO effect not discoverable | `NOT_SUPPORTED`; no effect invocation |
| requested effect parameter not present in discovered contract | `VALIDATION`; no effect invocation |
| Audacity effect reports failure/timeout | `EXTERNAL_DEPENDENCY`/`TIMEOUT`; staging not canonical |
| Music Separation expected stem roles cannot be proven | `DATA_INTEGRITY`; validate complete set before publication so no partial stem subset is published |
| Audio export escapes Product staging | `SECURITY`; reject before publication |
| generated/processed media rights unknown | register conservatively and require review; never mark commercial-safe implicitly |
| crash after bytes promotion but before metadata completion | replay repairs metadata only if producer-bound canonical checksum still matches |
| canonical derived output missing/tampered during repair | `DATA_INTEGRITY`; do not recreate canonical truth silently |
| byte-identical derived output already exists in Job Registry | reuse Asset byte identity; keep per-operation producer/source/role lineage in TASK-004 Manifest/Evidence rather than rewriting historical Asset provenance |
| H3 Production Brief free text injects reserved `<Picture N>`/`<Video N>`/`<Audio N>` tags or invalid First/Last role topology | `VALIDATION`; no workflow compilation/queue |
| H3 Single-Frame external custom node license/authorization is not explicitly acknowledged | `AUTHORIZATION`; `/prompt` not sent |
| H3 Single-Frame requested frame count is incompatible | normalize to Product contract (`>=5`, `%17==5`) and record requested/actual; never silently omit Evidence |
| Spectrum requested but `SpectrumApplyMiniMaxH3` is unavailable | `NOT_SUPPORTED`; fall back only when policy explicitly permits Native, otherwise no queue |
| Spectrum and competing cache/forecast accelerator appear on the same model branch/workflow | `VALIDATION`; `/prompt` not sent |
| H3 Foley FAST_32 requested without experimental acknowledgement | `AUTHORIZATION`; `/prompt` not sent |
| H3 Foley duration 16..45 s requested without long-duration experimental acknowledgement or duration >45 s | `AUTHORIZATION`/`VALIDATION`; `/prompt` not sent |
| replay sees ComfyUI operation already dispatched with persisted `prompt_id` | reconcile `/history/{prompt_id}` or fail closed; never blindly submit another prompt |
| same idempotency key is reused with a materially different local-AI request | `DATA_INTEGRITY`; no external execution |
