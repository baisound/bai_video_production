# TASK-013 — R4 Local Generation Execution Control Design / Review / Authorization

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `3c4dd8d283d9c2c68740db93c89fed6e4880d5a2`
- Working branch: `codex/task-013-r4-local-generation-execution`
- Owner route: `R3 control loop complete -> R4 TASK-013 SE/BGM/Video orchestration`
- DEV Profile: `DEV-4 EXTERNAL EXECUTION CRITICAL`
- Authorization: `OWNER_DIRECTED_IMPLEMENTATION_AUTHORIZED`
- Paid Provider execution in this unit: `PROHIBITED`
- Local/free Provider execution in automated validation: `FAKE PORT ONLY`

## Current OS / Product audit

The exact checkout already contains:

- durable Human GO / Approved Plan and exact Provider Policy identity;
- durable TASK-013 Feasibility PASS, TASK-037 LOCK/CURRENT input proof and TASK-039 Continuity proof;
- immutable TASK-040 Prompt metadata / Attempt Evidence and private Prompt body references;
- TASK-027 `ADMISSION_READY / EXECUTION_NOT_AUTHORIZED` Queue Evidence;
- provider-neutral route selection and creative-generation planning;
- local ComfyUI image/video and H3 Foley execution foundations;
- cloud ElevenLabs/Suno media adapters, which remain outside this no-paid unit.

The missing layer is a restart-safe Product execution controller. No current Application consumes one exact Queue entry, resolves its exact private Prompt bytes, selects the exact approved local/free route, records the dispatch boundary before side effects, prevents automatic replay after an uncertain interruption and records a bounded result.

Implementation Source of Truth is the current checkout. Existing local native Evidence remains untracked and untouched.

## Registry / owner / DEV Profile re-decision

TASK-013 remains the existing owner; no new TASK number is allocated. `DEV-4` is required because a false positive can invoke a Provider, disclose Prompt content, duplicate work after restart or convert admission Evidence into broader authority.

This unit is an execution-control foundation, not full R4 closure. It authorizes only an injected, explicitly allowlisted local/free execution port. It does not configure or call a paid route, retrieve a cloud credential, reserve/spend Budget, register a Candidate, import result Evidence into TASK-040, mutate Resolve/Cubase or publish media.

## Allowed Files

- `src/ai_video_production/creative_generation_execution_application.py` (new)
- `src/ai_video_production/generation_queue_application.py`
- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- focused TASK-013/TASK-036 tests;
- TASK-013 Evidence and canonical Project/roadmap/state/index documents.

Trusted-launch composition and real ComfyUI/H3 adapter wiring require a later renewed audit because endpoint, workflow, input staging and output-containment identities are not yet present in the TASK-036 launch contract.

## Builder Design

### 1. Exact derived execution candidate

The Application exposes only current TASK-027 Queue entries. The caller cannot submit a loose `plan_approved`, feasibility result, route ID, Provider identity, cost class or Prompt hash. Preparation reloads the Queue and exact Prompt registry, requires matching project/Prompt/Profile identity and resolves the private Prompt body through a project-contained `project-private://prompts/` reference.

### 2. Prompt privacy and integrity

Prompt text is read only by the trusted Python host from a regular, non-symlink, size-bounded UTF-8 file inside `<project>/private/prompts`. Its SHA-256 must equal the Queue-bound Prompt hash. Prompt text is passed transiently to the execution port and is never stored in general Evidence or returned to the WebView.

### 3. Local/free route only

The exact current `ai-connection-settings.json` Profile must match the Queue / Human-GO Provider Policy. Route resolution must return `LOCAL_FREE_AI`, require no credential and be supported by the injected execution port. Cloud-paid, cloud-free, credential-bearing and unsupported routes fail before dispatch.

### 4. Durable dispatch/restart boundary

`generation-executions.json` is strict, checksum-bound and serialized across processes. A one-shot confirmation is consumed before revalidation. Apply reloads all sources, then appends `DISPATCHING` before invoking the port.

If the process stops after that write, restart exposes `RECOVERY_REQUIRED` and never retries automatically. Success appends `COMPLETED`; a known pre-result exception appends `FAILED`. Unknown/tampered state remains blocked. Completed/failed/dispatching Queue entries cannot be dispatched again.

### 5. Result boundary

The port returns allowlisted identity and output Evidence only: route/provider/model/capability, operation ID, contained output reference/hash/media kind and latency. The controller verifies route and Prompt identities. It creates no Production Candidate and does not claim Visual/Audio PASS.

### 6. Unified Desktop integration

The existing Generation Queue workspace gains an execution-control projection and explicit two-step confirmation only when an execution Application is injected. It displays route/cost, Prompt integrity and recovery state without exposing Prompt body, endpoint, credential or host path. No Application injection means execution remains visibly unavailable.

## Critic Review

1. **Critical — Queue admission could be treated as execution authority.** Correction: separate one-shot Human execution confirmation and re-derive Queue/Profile/Prompt at apply.
2. **Critical — paid or credential-bearing routes could execute under the local slice.** Correction: require exact `LOCAL_FREE_AI` and `credential_ref is None`; all other cost/credential classes fail closed.
3. **Critical — crash after dispatch could duplicate generation.** Correction: persist `DISPATCHING` first and never replay it automatically.
4. **High — raw Prompt could leak into general Evidence/UI/errors.** Correction: contained private-file resolution, hash check, transient port argument and body-free serialization.
5. **High — caller-selected route could bypass Human-approved Profile.** Correction: load current settings, require exact Profile ID/version/checksum and use canonical resolver.
6. **High — changed Queue/Prompt/Profile between prepare/apply could broaden authority.** Correction: bind exact snapshots and fully re-derive after consuming the confirmation.
7. **Critical — an old Queue record could remain syntactically valid after its upstream LOCK/Continuity/Feasibility Evidence becomes stale.** Correction: TASK-027 publicly re-derives the exact stored Queue entry from all current upstream stores immediately before both prepare and apply; any byte-level difference blocks execution.
8. **High — adapter result could claim another route/output.** Correction: exact result identity/hash/reference validation before `COMPLETED`.
9. **High — automatic Candidate creation could skip TASK-038 review.** Correction: result remains contained Evidence; Candidate/Audit binding is a later explicit unit.
10. **High — a local endpoint/workflow could be ambiguously targeted.** Correction: this unit uses an injected port only; real adapter composition is explicitly deferred to a renewed target audit.
11. **High — failures could silently become retryable.** Correction: terminal `FAILED` or manual recovery Evidence; no automatic retry or hidden regeneration.

Unresolved Critical/High after Builder correction: `0 / 0`.

## Final Plan / Judge Decision

`PASS / BOUNDED IMPLEMENTATION AUTHORIZED`

Implementation order:

1. implement strict local execution snapshot, private Prompt resolver and port contract;
2. implement one-shot prepare/apply and no-replay recovery classification;
3. integrate an optional body-free execution-control surface into Generation Queue;
4. run focused/full Windows+WSL2/compile/JavaScript/diff gates;
5. publish PR, require all hosted checks, exact merge and separate closure;
6. renew the target audit before real ComfyUI/H3 composition or Candidate/Audit binding.

No package, Tag or GitHub Release is selected at kickoff.
