# ADR — TASK-002 Final Resolve IPC Transport

- Status: `ACCEPTED`
- Date: 2026-08-09
- Scope: WSL2 automation worker -> Windows Resolve Gateway boundary

## Context

The production topology requires automation logic running in WSL2 to reach a Windows-side process that can safely integrate with DaVinci Resolve. TASK-002 measured Windows-local HTTP/JSON and Named Pipe behavior and then measured the actual WSL2 -> Windows topology.

## Decision

Use **authenticated HTTP/JSON over the Windows host/default-gateway endpoint** as the primary WSL2 -> Windows IPC transport.

Keep **Windows Named Pipe** as a Windows-local optimization candidate, not as the cross-WSL2 primary transport.

Do not promote gRPC or ZeroMQ at this stage; they remain optional future candidates and do not justify additional runtime dependencies for the current editing-first roadmap.

## Evidence

### WSL2 -> Windows HTTP/JSON

Target live Evidence:

- 401-style unauthenticated rejection path verified by the probe contract
- authenticated roundtrip: PASS
- same endpoint/port restart and reconnect: PASS
- 16 total round trips
- p50 `1.255 ms`
- p95 `1.699 ms`
- ephemeral bearer token not persisted in Evidence

### Windows-local candidates

Attempt 02 measured both HTTP/JSON and Windows Named Pipe with authentication and same-endpoint restart. Named Pipe remains attractive for a purely Windows-local hot path, but it does not remove the cross-boundary requirement and therefore is not selected as the WSL2 primary transport.

## Security and failure requirements

The production Gateway derived from this ADR must:

1. bind only to the intended host interface/port policy;
2. require authentication for every mutating operation;
3. never persist bearer tokens into Evidence or canonical manifests;
4. use bounded timeouts and explicit retry classification;
5. preserve idempotency at the product operation boundary;
6. fail closed on Resolve Project/Timeline ownership ambiguity;
7. expose health/version/capability information separately from mutation authorization;
8. support same-endpoint process restart and reconnect without changing canonical Job state incorrectly.

## Consequences

- WSL2 workers can use standard HTTP clients with minimal platform coupling.
- The Windows Resolve Gateway remains the only component that directly owns Resolve scripting access.
- Named Pipe support can be retained or introduced later for Windows-local internal calls without changing the canonical cross-platform contract.
- HTTP latency observed by the spike is negligible relative to video-editing operations and is not a bottleneck justification for a more complex transport.

## Non-decisions

This ADR does not authorize production Timeline writes, subtitle import semantics, render submission, relink behavior, or production API exposure. Those remain later Consumer TASK responsibilities with their own Safety Floors.
