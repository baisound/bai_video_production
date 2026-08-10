# TASK-028 Detailed Design

`AiConnectionProfile` is the versioned settings snapshot. Each `ModelRoute` binds one workload to a provider family, exact provider/model identifier, cost class, priority, optional planning reasoning effort, capability set and indirect connection references.

Resolution order is deterministic: workload match → enabled/available → credential available → capability match → mode policy → ascending priority and route ID. `FREE` permits cloud free tier, local free AI and non-AI free libraries. `OFFLINE_ONLY` excludes every cloud class. `AI` excludes non-AI libraries. `AUTO` permits all configured classes. `DISABLED` fails before selection.

Settings forbid common secret keys recursively. Credentials are supplied at runtime through a credential store and represented canonically only by `credential://...`. Endpoint configuration follows the same indirection. Persisted documents carry a canonical SHA-256 checksum and reject unsupported schema versions or modifications.

The GUI should expose a global default and per-workload overrides, then provider/model/reasoning/priority. It must show paid/free and cloud/local badges, validate adapter availability before GO, and never display or serialize secret values.

## Provider execution slice

`AiProviderExecutionService` resolves a `PLANNING` route requiring `TEXT_GENERATION`, selects exactly one registered family adapter, resolves its credential only at execution time, and returns a provider-neutral text result. OpenAI uses the Responses endpoint, Anthropic uses Messages, and Google uses Gemini Interactions. Model identifiers are never silently substituted.

The production transport accepts only the three compiled HTTPS origins, bounds response size and timeout, normalizes HTTP/network/JSON failures, and never places response bodies or credentials in Product errors. Repository tests inject a fake transport, so they cannot make billable calls. Route diagnostics distinguish disabled, unavailable, missing-credential, missing-adapter and ready states for GUI preflight.
