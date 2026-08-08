# TASK-002 — Critic Review: Attempt 01 Corrective Package 0.2.1

## Review result

`APPROVED_WITH_OPEN_LIVE_GATES`

## Finding resolved: inaccurate module-source evidence

### Problem

At commit `d63a84d`, every `ProductError` from `ResolveModuleLoader.connect()` caused the CLI to write `module_source_kind=NOT_FOUND`. Attempt 01 returned `ERR_RESOLVE_NOT_AVAILABLE`, which is a post-discovery failure, so the serialized source label was false.

### Correction

- Post-discovery errors now carry `module_source_kind` in `ProductError.details`.
- The CLI preserves that source kind.
- Actual discovery misses map to `MODULE_NOT_FOUND`.
- The root `resolve.connection` capability row records the exact error code/category instead of a generic disconnected error.
- Regression tests cover both paths.

## Finding resolved: disconnected live runner could appear successful

### Problem

The Windows runner previously returned success when the worker generated a schema-valid report even if `live_resolve_connected=false`. This allowed diagnostic evidence to be mistaken for completion evidence.

### Correction

The updated runner keeps the JSON but returns failure when the live Resolve root object was not obtained. It also performs read-only preflight checks for a running Resolve process and the conventional PROGRAMDATA Python bridge module.

## Safety review

- No mutation flags were added to the live runner.
- No project/timeline/media/render mutation is executed.
- No package is auto-installed by the runner.
- No full host path is added to canonical JSON evidence.
- Attempt 01 evidence remains immutable.

## Blocking findings

Code/documentation blocking findings: `0`.

TASK completion blockers remain environmental/behavioral live Evidence gates and are intentionally not downgraded.
