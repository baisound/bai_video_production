# TASK-002 — Live Evidence Review Attempt 02

## Decision

`ACCEPTED_READ_ONLY_LIVE_EVIDENCE / TASK_REMAINS_OPEN`

## Intake integrity

Attempt 02 originals are preserved under `evidence/windows-live-attempt-02/original/` and hashed in `SHA256SUMS.txt`. Historical Evidence is not rewritten.

## Target environment observed

- Host: Windows 11 / AMD64 / Python 3.12.4
- Resolve: `DaVinci Resolve Studio 21.0.2.4`
- Resolve scripting connection: **CONNECTED**
- Module discovery: `WINDOWS_PROGRAMDATA`
- Probe mode: `READ_ONLY`

## Capability result

23 canonical capability rows:

- `SUPPORTED`: 7
- `LIMITED`: 0
- `UNSUPPORTED`: 0
- `PROBE_REQUIRED`: 16

Supported read-only rows are:

1. `resolve.connection`
2. `resolve.version`
3. `resolve.product_name`
4. `project_manager.access`
5. `project.current`
6. `media_pool.access`
7. `timeline.current`

Mutation rows remain unresolved by design. Method presence is accepted only as method-presence evidence and is not promoted to behavioral support.

## Windows-local IPC result

- `LOCALHOST_HTTP_JSON`: MEASURED, authentication verified, same-endpoint restart verified, p50 `7.498 ms`, p95 `15.688 ms`.
- `WINDOWS_NAMED_PIPE`: MEASURED, authentication verified, same-endpoint restart verified, p50/p95 `0.447 ms`.
- gRPC / ZeroMQ: `PROBE_REQUIRED`; optional packages were not installed solely for the spike.

## Resulting implementation action

Attempt 02 closes the live read-only Resolve connection gate. The remaining TASK-002 evidence actions are narrowed to:

1. minimal sandbox behavioral probe for the Resolve Assembly MVP critical operations;
2. WSL2-to-Windows authenticated HTTP reachability + same-endpoint restart evidence;
3. Final IPC ADR and DEV-4 Critic/Judge.

Package `0.2.2` adds separately invoked tooling for those two evidence actions. The live sandbox action itself is not executed by the build environment and remains an explicit user-side action.

## Safety decision

Sandbox behavioral probe may create/save/export only a Project whose name begins `BAI_CAPABILITY_PROBE_`, create a Bin/Timeline, import a generated temporary 1-second silent WAV, append it, and add one marker. It must fail closed if a non-sandbox Project is current.

It does **not** delete Projects, start/cancel rendering, relink media, terminate Resolve, or write to a non-sandbox Project.
