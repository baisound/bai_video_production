# TASK-013 — R4 Safe Runtime Readiness Preflight Design / Review / Authorization

- Date: `2026-08-14`
- Owner route: continue BAI VIDEO PRODUCTION under BAI Development OS governance
- BAI Development OS queue result: `TASK-013-SAFE-RUNTIME-READINESS-PREFLIGHT / IMPLEMENTATION`
- Parked unit: `TASK-013-NATIVE-H3-GATE / HG-BVP-TASK013-NATIVE-003`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Scope: explicit read-only ComfyUI readiness inspection; no generation dispatch

## Current OS audit

The implementation Source of Truth is current BAI VIDEO PRODUCTION main
`e0cacacb5f360f715f874ed6086f4fd4a323b07a`, freshly cloned after PR #44
merged. The checkout was clean before this unit and has no inherited native
Evidence. BAI Development OS v1.1.0 remains external development governance,
not a Product runtime dependency.

The hosted TASK-013 adapter and incident-derived launch-flag guard are closed.
Native H3 completion remains parked because the previous external execution is
uncertain and the host was force-restarted. The current adapter can validate
ComfyUI only as part of `execute()`, after which it reserves a durable journal
and queues the workflow. Operators therefore lack an explicit way to prove the
current runtime is safe enough for review without entering the dispatch path.

## Registry and DEV Profile decision

This is an existing TASK-013 corrective/hardening unit. It inspects a native
external runtime and protects the boundary immediately before a potentially
expensive GPU operation, so `DEV-4 FOUNDATION CRITICAL` remains required.

The Autonomous Queue selected this repository-only unit and separately parked
`TASK-013-NATIVE-H3-GATE`. A successful preflight is diagnostic Evidence only:
it is not Product execution authorization, Human approval, Native validation,
or permission to replay an uncertain operation.

## Allowed files

- `src/ai_video_production/local_comfy_generation_port.py`
- `src/ai_video_production/creative_generation_execution_application.py`
- `src/ai_video_production/task036_shell_ui.py`
- `tests/test_task013_local_comfy_generation_port.py`
- `tests/test_task013_creative_generation_execution_application.py`
- `tests/test_task036_shell_ui.py`
- `PROJECT.md`
- `CHANGELOG.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/project-summary.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/knowledge-evolution-detailed-roadmap.md`
- this design/review/authorization record and its paired closure Evidence

Raw `evidence/native/**`, private Prompt content, existing dispatch journals,
generated media, runtime launch configuration, package/version metadata and
operator-owned Resolve/Cubase projects are outside Allowed Files.

## Builder design

1. Add an immutable, sanitized readiness result owned by TASK-013. It reports
   exact configured route identities, the workflow checksum, PASS state and
   explicit false claims for dispatch, journal creation, execution
   authorization and Native Gate satisfaction.
2. Add `LocalComfyTextToVideoPort.preflight()` using a fixed body-free sentinel
   Prompt and non-output execution identity. It performs only existing
   `object_info`, workflow class/input, `system_stats`, resource-admission and
   runtime identity checks.
3. Extract the common provider/runtime inspection into one internal method used
   by both `preflight()` and `execute()` so the diagnostic path cannot drift
   from the real pre-dispatch gate.
4. Expose an explicit application and allowlisted Shell bridge method. It is
   manually invoked and is never called by `snapshot()` or UI refresh, avoiding
   surprise network activity.
5. Prove the preflight makes no queue call, writes no journal or generated
   output, contains no Prompt body, rejects unsafe runtime/model/resource drift
   fail-closed, and leaves the existing confirmed execution flow unchanged.

## Critic review

1. **Critical — PASS could be mistaken for execution Authority or Native
   validation.** Resolution: the schema names the result
   `SAFE_RUNTIME_PREFLIGHT_PASS_EXECUTION_PARKED` and fixes
   `execution_authorized`, `native_gate_satisfied`, `dispatch_performed` and
   `journal_created` to false.
2. **Critical — diagnostic inspection could accidentally reserve or queue.**
   Resolution: preflight calls only read-only Comfy endpoints and never receives
   an execution request, confirmation token or journal identity.
3. **High — a real/private Prompt could leak into a probe or log.** Resolution:
   use a fixed body-free sentinel known only to the adapter and return no
   rendered workflow or Prompt field.
4. **High — preflight and execute checks could diverge.** Resolution: both call
   the same internal workflow/runtime inspection function.
5. **High — shell snapshots could cause repeated live calls.** Resolution: add a
   separate explicit bridge command; snapshots remain local and side-effect
   free.
6. **High — raw argv or absolute host paths could leak machine identity.**
   Resolution: return only sanitized booleans, configured logical identities,
   counts and checksum-bound policy identity.
7. **High — previous uncertain operation could be mutated or replayed.**
   Resolution: no existing journal/evidence path is read or written and no
   dispatch/recovery method is called.

Unresolved design Critical/High findings after corrections: `0 / 0`.

## Final plan and implementation authorization

This bounded read-only preflight is authorized. Acceptance requires:

- focused TASK-013 and Shell bridge tests PASS;
- full repository regression PASS;
- `compileall` and `git diff --check` PASS;
- explicit proof of zero queue calls, journal files and generated outputs;
- no native/paid/production execution and no mutation under
  `evidence/native/**`;
- truthful closure retaining `TASK-013-NATIVE-H3-GATE` as parked.

Critic/fix work is capped at two cycles. Mandatory gates and unresolved
Critical/High `0 / 0` close only this readiness capability; they do not close
TASK-013 or R4.
