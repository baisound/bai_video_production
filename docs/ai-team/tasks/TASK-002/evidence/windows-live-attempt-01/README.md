# TASK-002 Windows Live Evidence — Attempt 01 Review

## Evidence status

`REVIEWED / PARTIALLY_VALID / RESOLVE_RETRY_REQUIRED`

The returned JSON files are preserved verbatim in this directory. `SHA256SUMS.txt` records their intake hashes.

## Source evidence facts

Resolve report:

- Host: Windows 11 / AMD64 / Python 3.12.4.
- Probe mode: `READ_ONLY`.
- `resolve.connected=false`.
- Connection error: `ERR_RESOLVE_NOT_AVAILABLE`.
- 23/23 capability rows remained `PROBE_REQUIRED`.
- No mutation probe executed.

IPC report:

- `LOCALHOST_HTTP_JSON`: `MEASURED`, authentication verified, same-endpoint restart verified, 8 round trips, p50 1.211 ms, p95 24.604 ms.
- `WINDOWS_NAMED_PIPE`: `MEASURED`, authentication verified, same-endpoint restart verified, 2 round trips, p50/p95 0.597 ms.
- gRPC and ZeroMQ remain `PROBE_REQUIRED`; optional packages were not installed solely for comparison.
- ADR remains `PROVISIONAL`, selected reference `LOCALHOST_HTTP_JSON`.
- WSL2 reachability remains unverified.

## Historical report defect discovered by this evidence

The Attempt 01 Resolve JSON records `module_source_kind=NOT_FOUND`, but the exact error is `ERR_RESOLVE_NOT_AVAILABLE`.

At commit `d63a84d`, that error is raised only after `ResolveModuleLoader.discover()` has already returned a scripting module and callable `scriptapp("Resolve")` returned `None`. The CLI nevertheless replaced the module source with the hard-coded string `NOT_FOUND` for every `ProductError`.

Therefore:

- the Attempt 01 JSON **does prove that a scripting Python bridge module was discovered**;
- it **does not identify which discovery source supplied it**;
- it does **not prove Resolve scripting support is unavailable**;
- it does **not satisfy the live-Resolve completion gate**.

The defect is corrected in package `0.2.1`: connection errors now preserve the discovered module source and the root capability row records the exact loader/connection error.

## Required retry

Run the updated Windows runner while DaVinci Resolve is fully started. If the scripting bridge still cannot obtain the Resolve root object, verify the installed Resolve version's local external-scripting configuration and rerun. The runner remains read-only and does not alter projects, timelines, media, or renders.
