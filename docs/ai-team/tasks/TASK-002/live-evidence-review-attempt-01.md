# TASK-002 — Live Evidence Review Attempt 01

## Decision

`RETRY_REQUIRED / TASK_REMAINS_OPEN`

## Accepted evidence

The Windows-local IPC measurements are accepted as target-platform evidence. HTTP/JSON and Windows Named Pipe both demonstrated authentication and same-endpoint restart behavior on Windows 11.

## Evidence not sufficient for completion

The Resolve capability report did not establish a live Resolve root object. All 23 capabilities therefore remain unresolved. Mutation capabilities were intentionally not exercised.

The returned report also exposed a probe Evidence defect: all connection/discovery exceptions were serialized with `module_source_kind=NOT_FOUND`, even when the module had already been discovered. The exact `ERR_RESOLVE_NOT_AVAILABLE` path proves Attempt 01 reached `scriptapp("Resolve")` and received `None`.

## Corrective implementation

Package `0.2.1`:

1. preserves `module_source_kind` after module discovery when connection fails;
2. records the exact `ProductError` code/category on the `resolve.connection` capability row;
3. enhances the Windows runner preflight with Resolve-process and standard bridge-module checks;
4. treats `live_resolve_connected=false` as a failed live-evidence run while retaining the generated diagnostic JSON.

## Remaining TASK-002 completion gates

- successful read-only connection to the target Resolve installation;
- version/product/readiness capability observations;
- separately authorized sandbox behavioral evidence for mutation rows that must be promoted beyond `PROBE_REQUIRED`;
- WSL2-to-Windows IPC reachability/authentication/recovery evidence;
- final IPC ADR review;
- final DEV-4 Critic/Judge and completion record.
