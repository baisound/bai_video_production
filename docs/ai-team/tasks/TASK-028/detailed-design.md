# TASK-028 Detailed Design

`AiConnectionProfile` is the versioned settings snapshot. Each `ModelRoute` binds one workload to a provider family, exact provider/model identifier, cost class, priority, optional planning reasoning effort, capability set and indirect connection references.

Resolution order is deterministic: workload match → enabled/available → credential available → capability match → mode policy → ascending priority and route ID. `FREE` permits cloud free tier, local free AI and non-AI free libraries. `OFFLINE_ONLY` excludes every cloud class. `AI` excludes non-AI libraries. `AUTO` permits all configured classes. `DISABLED` fails before selection.

Settings forbid common secret keys recursively. Credentials are supplied at runtime through a credential store and represented canonically only by `credential://...`. Endpoint configuration follows the same indirection. Persisted documents carry a canonical SHA-256 checksum and reject unsupported schema versions or modifications.

The GUI should expose a global default and per-workload overrides, then provider/model/reasoning/priority. It must show paid/free and cloud/local badges, validate adapter availability before GO, and never display or serialize secret values.

## Provider execution slice

`AiProviderExecutionService` resolves a `PLANNING` route requiring `TEXT_GENERATION`, selects exactly one registered family adapter, resolves its credential only at execution time, and returns a provider-neutral text result. OpenAI uses the Responses endpoint, Anthropic uses Messages, and Google uses Gemini Interactions. Model identifiers are never silently substituted.

The production transport accepts only the three compiled HTTPS origins, bounds response size and timeout, normalizes HTTP/network/JSON failures, and never places response bodies or credentials in Product errors. Repository tests inject a fake transport, so they cannot make billable calls. Route diagnostics distinguish disabled, unavailable, missing-credential, missing-adapter and ready states for GUI preflight.

## External media providers

ElevenLabs supports `AUDIO/TTS`, `AUDIO/SFX` and `MUSIC/MUSIC_GENERATION` through exact configured model and voice IDs. Binary output is bounded and returned for the canonical Asset publication layer; it is not silently written to arbitrary paths. SunoAPI submits `MUSIC/MUSIC_GENERATION` as an external asynchronous task and returns a normalized provider task ID for later callback/poll reconciliation. Callback origins must be HTTPS.

The owner's existing ElevenLabs trained voice is represented by a private local `VoiceProfile` owned by TASK-014. The route chooses provider/model/capability; it does not embed the raw private `voice_id`, consent record or training media in the shared model catalog. A future read-only adapter may enumerate owned/verified voices and subscription capability, but it must allowlist fields and must never persist a raw account response or returned credential material.

External media calls require `authorization://...` rights approval in addition to credentials. Automated tests use injected transports and cannot reach a paid endpoint. Provider catalog status is an explicit contract: `IMPLEMENTED`, `LOCAL_RUNTIME` or `PLANNED_ADAPTER`.

## Capability-first correction

Provider family is an authentication/API grouping, not a purpose classification. The exact model descriptor owns supported capabilities and workloads. A Google model may be configured for planning, image or video; an OpenAI model may be configured for text, image, video or audio; another family follows the same rule. Availability requires all four conditions: the route declares the capability, the model catalog confirms it, an adapter binding exists for `(provider family, capability)`, and runtime/credential availability passes.

The generic request/result envelope is media-neutral and rejects embedded credentials. Adapter output must match the selected route, model, workload and capability or the registry raises a data-integrity error. Existing planning text execution remains compatible through `TextCapabilityAdapter` while future media adapters use the same registry.
