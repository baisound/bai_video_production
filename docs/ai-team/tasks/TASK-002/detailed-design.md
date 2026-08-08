# TASK-002 — Detailed Design

## 1. Design authority

Product Design Baseline: `AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`.

Impacted contracts:

- Resolve Gateway is the only intended Resolve integration boundary.
- Readiness is probed in stages rather than by fixed startup sleep.
- Gateway endpoints are design contracts, not proof that the installed Resolve version supports the operation.
- Capability status must be one of `SUPPORTED / LIMITED / UNSUPPORTED / PROBE_REQUIRED` and retain return/timeout/Studio/fallback evidence.
- WSL2 ↔ Windows transport remains replaceable; localhost HTTP/JSON is a reference path, not an already-final ADR.
- Existing human Timeline and non-sandbox Project mutation is prohibited.

## 2. Probe architecture

`ResolveModuleLoader` discovers the scripting module from an already configured Python import path, an explicit environment module directory, or conservative platform candidates. It never downloads code.

`ResolveCapabilityProbe` accepts a connected Resolve object and performs only a strict safe-call allowlist in read-only mode. It records method presence for mutating capabilities but does not execute them. Presence without behavioral execution remains `PROBE_REQUIRED`.

`ResolveCapabilityReport` is canonical JSON evidence for this task. It stores product/version and normalized observations, but strips secret-looking keys and avoids recording arbitrary full user paths.


## 2.1 Connection Evidence semantics

Module discovery and Resolve process/API connection are distinct evidence stages. A discovered `DaVinciResolveScript` module does not prove that `scriptapp("Resolve")` can obtain the live Resolve root object.

The report must preserve the exact discovery source across post-discovery failures. `module_source_kind=MODULE_NOT_FOUND` is reserved for an actual bridge-module discovery miss; it must not be used for `ERR_RESOLVE_NOT_AVAILABLE`, `ERR_RESOLVE_CONNECT_FAILED`, or `ERR_RESOLVE_SCRIPTAPP_MISSING` after a module was already discovered. The `resolve.connection` capability row records the exact loader/connection error code and category.

The Windows live-evidence runner treats `live_resolve_connected=false` as a failed completion-evidence run while retaining the generated JSON for diagnosis and historical Evidence.

## 3. Capability classification rules

- `SUPPORTED`: the exact safe read call was executed successfully, or an authorized sandbox mutation test completed and verified its expected result.
- `LIMITED`: behavior exists but a condition/restriction was observed and the Gateway must expose that restriction.
- `UNSUPPORTED`: explicit target-version behavioral evidence or authoritative target documentation proves the operation unavailable. Candidate-method absence by itself remains `PROBE_REQUIRED` because candidate lists are not semantic proof.
- `PROBE_REQUIRED`: execution evidence is missing, parent object is unavailable, the method is mutation-gated, or the environment differs from the target Windows/Resolve topology.

Method presence alone is never enough to promote a mutation capability to `SUPPORTED`.

## 4. Safety modes

### READ_ONLY (default)

May call only approved zero-argument query/accessor methods needed to establish readiness. No Project, Timeline, media or Render mutation.

### SANDBOX_MUTATION

Requires all of:

1. explicit runtime `--allow-mutation-probes`;
2. sandbox Project name beginning `BAI_CAPABILITY_PROBE_`;
3. current Project is absent or already a sandbox Project;
4. no automatic deletion or forced Resolve termination.

The first implementation delivers the gating contract and test seam. Live sandbox execution is a separate evidence action on the user's Windows machine.

## 5. Readiness stages

1. Scripting module import/discovery.
2. `scriptapp("Resolve")` connection.
3. version/product query.
4. Project Manager access.
5. Current Project query.
6. Media Pool access when a Project is available.
7. Current Timeline query when a Project is available.

A missing current Project is a valid runtime state, not evidence that the Project Manager API is unsupported.

## 6. Initial capability set

The matrix covers the Product Baseline Gateway contract: health/connection, current version, Project Manager, Project open/create/save/snapshot, media import/relink, Bin ensure, Timeline create/build/markers/subtitles/handoff prerequisites, Render submit/status/cancel, plus current Project/Media Pool/Timeline readiness.

Where the public design has no guaranteed single Scripting API method, the probe stores candidate methods and keeps the capability `PROBE_REQUIRED` until live behavior establishes a safe implementation path.

## 7. IPC comparison

`IpcCapabilityProbe` produces evidence for four candidates:

- `LOCALHOST_HTTP_JSON`
- `WINDOWS_NAMED_PIPE`
- `GRPC`
- `ZEROMQ`

Localhost HTTP can be exercised with Python stdlib, including loopback bind, bearer-token rejection/acceptance and restart on the exact same endpoint. Windows Named Pipe is measured only on Windows. gRPC/ZeroMQ remain optional-dependency candidates and are not installed merely to force a favorable result.

The ADR selector refuses a `FINAL` transport decision unless target Windows evidence and required WSL2 reachability evidence are supplied. Before that, localhost HTTP/JSON remains only the Product Baseline's provisional reference path.

## 8. Failure modes

| Failure | Required behavior |
|---|---|
| Resolve module missing | Report disconnected; do not crash into false support |
| Resolve process/API unavailable | `connected=false`; capabilities unresolved |
| Safe query raises | record normalized error and `PROBE_REQUIRED`/`LIMITED`; continue other independent probes |
| Mutation requested without opt-in | fail closed with `ERR_RESOLVE_MUTATION_NOT_AUTHORIZED` |
| Non-sandbox Project mutation | fail closed with `ERR_RESOLVE_SANDBOX_REQUIRED` |
| Probe worker hangs | outer supervisor timeout terminates the worker and writes a Schema-valid supervision-failure Evidence report |
| Secret-like value in evidence | redact before JSON serialization |
| Target-only IPC not tested | `PROBE_REQUIRED`, never inferred from another OS |

## 9. Test strategy

DEV-4 requirements map to:

- Unit: status/report/loader/IPC scoring.
- Boundary negative: mutation gate, unsafe project, missing module, bad Schema payload.
- Integration: fake Resolve object graph and localhost HTTP transport.
- Regression: all TASK-001 tests.
- Contract: report Schemas and Product Baseline capability IDs.
- Fault/recovery: HTTP server restart, failing Resolve method, disconnected scripting root.
- Consumer fixture: deterministic fake target matrix.

## 10. Completion gate

Repository implementation can reach `IMPLEMENTED_AWAITING_LIVE_EVIDENCE` in this environment. `TASK-002 COMPLETED` requires target-machine output from the Windows/Resolve probe and IPC evidence sufficient to close the Capability Matrix and IPC ADR without invention.

## 11. Distribution contract

The CLI report schemas are packaged as Python package resources in addition to the repository-level canonical copies. A contract test requires both copies to remain byte-semantically equivalent, and installed-wheel execution is verified from outside the source checkout.

Supervised timeout/worker-failure paths must emit reports that validate against the same canonical report schemas; failure Evidence is never a one-off ad-hoc JSON shape.
