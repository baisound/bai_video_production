# TASK-013 — R4 Local Comfy Native Adapter Local Closure Evidence

- Date: `2026-08-14`
- Branch: `codex/task-013-r4-local-comfy-native-adapter`
- Base main: `191cfa2922f0479e800ef497096a39cc3732a8ed`
- DEV Profile: `DEV-4`
- Local implementation gate: `PASS`
- Contained native completion gate: `PARKED_TO_SAFE_RUNTIME_REVIEW`

## Implemented bounded unit

- package-owned, checksum-bound, body-free MiniMax H3 text-to-video API workflow;
- exact `COMFYUI / LOCAL_FREE_AI / TEXT_TO_VIDEO` route authorization with no credential-bearing or paid fallback;
- exact loopback endpoint, workflow, node, model, resource and live runtime-argument checks before queueing;
- durable per-execution `PREPARED -> QUEUED -> COMPLETED|FAILED` journal with immediate Comfy prompt-id persistence and no automatic replay;
- post-dispatch timeout/transport/history uncertainty propagated to the parent as recovery-required without adding a false terminal failure;
- exactly one execution-scoped Comfy output, path/symlink/ambiguity rejection, media probe, atomic project-contained copy and SHA-256 verification;
- opt-in trusted-launch `1.1.0` composition while existing `1.0.0` behavior remains unavailable/fail-closed;
- package-data registration for the workflow resource.

## Critic review result

Critical/High controls are resolved in code for Prompt leakage, paid/cloud route drift, duplicate dispatch, shared-output ingestion, endpoint/workflow/model drift, false media success and silent launcher enablement. Final Critic review tightened the adapter configuration itself from the common local/LAN policy to the exact bare `http://127.0.0.1:<port>` origin, in addition to checking live process arguments. The force-restart boundary found one additional High risk: legacy low-VRAM runtime flags can destabilize the host. The implementation now rejects those modes before dispatch.

Unresolved implementation Critical/High findings: `0 / 0`.

The runtime limitation itself is not disguised as resolved. Native H3 completion remains parked and is tracked by the paired failure/recovery Evidence.

## Validation

- final exact adapter/controller/launcher regression: `35 / 35 PASS`;
- final full WSL2 Ubuntu regression: `919 / 919 PASS` in `56.60s`;
- WSL2 `compileall`: PASS;
- wheel and source distribution build: PASS; the wheel contains both `local_comfy_generation_port.py` and `workflow_resources/minimax_h3_native_t2v_api.json`;
- no existing raw `evidence/native/**` directory was staged, deleted or changed by this unit;
- no private Prompt body or operator workflow is included;
- no paid Provider execution occurred.

Hosted PR checks, exact main merge verification and branch cleanup remain pending. Stable release remains `v0.20.1`; no package version change, Tag or GitHub Release is selected for this bounded unit.
