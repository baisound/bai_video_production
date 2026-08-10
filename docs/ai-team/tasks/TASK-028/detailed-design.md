# TASK-028 Detailed Design

`AiConnectionProfile` is the versioned settings snapshot. Each `ModelRoute` binds one workload to a provider family, exact provider/model identifier, cost class, priority, optional planning reasoning effort, capability set and indirect connection references.

Resolution order is deterministic: workload match → enabled/available → credential available → capability match → mode policy → ascending priority and route ID. `FREE` permits cloud free tier, local free AI and non-AI free libraries. `OFFLINE_ONLY` excludes every cloud class. `AI` excludes non-AI libraries. `AUTO` permits all configured classes. `DISABLED` fails before selection.

Settings forbid common secret keys recursively. Credentials are supplied at runtime through a credential store and represented canonically only by `credential://...`. Endpoint configuration follows the same indirection. Persisted documents carry a canonical SHA-256 checksum and reject unsupported schema versions or modifications.

The GUI should expose a global default and per-workload overrides, then provider/model/reasoning/priority. It must show paid/free and cloud/local badges, validate adapter availability before GO, and never display or serialize secret values.
