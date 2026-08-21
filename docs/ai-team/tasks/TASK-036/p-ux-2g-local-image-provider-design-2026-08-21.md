# TASK-036 P-UX-2G local image Provider vertical design

Status: `UNITS_D-A_D-B_D-C_CODE_COMPLETE / NATIVE_HUMAN_GATE_PENDING`
Date: 2026-08-21
Development depth: `DEV-3 HIGH ASSURANCE`

## Goal

Connect a current Human-approved TASK-027 scene to a free local ComfyUI image
Provider and return exactly one verified output through the existing canonical
flow:

```text
Approved Plan / Production Slot
-> Prompt Evidence
-> Generation Queue admission
-> explicit per-entry Human execution confirmation
-> local-free ComfyUI execution
-> contained project-output
-> Output Adoption
-> canonical IMAGE Asset + TASK-037 Candidate
-> TASK-038 review / V6.1.1 Image workspace
```

The old direct `LocalImageGenerationService` is not the integration boundary.
It publishes a TASK-004 Asset directly and would bypass the current TASK-027
Queue, TASK-013 execution journal and TASK-027 Output Adoption. P-UX-2G must use
the latter canonical flow and must not create a second Candidate path.

## Current state and dependency boundary

- TASK-027 Queue, TASK-013 execution events, output adoption, Production
  Candidate and Audit projection already exist.
- `Task013CreativeGenerationExecutionApplication` derives `TEXT_TO_IMAGE` for
  START_FRAME/END_FRAME Slots and already rejects paid/credentialed routes.
- The trusted launcher currently injects one T2V-only
  `LocalComfyTextToVideoPort`. One global port cannot safely serve both IMAGE
  and VIDEO routes.
- V6.1.1 displays Queue/Execution lineage but does not currently render the
  existing explicit execution action for an eligible Queue entry.
- A previous ComfyUI installation was absent at fresh audit. The installation
  runbook restored official ComfyUI `0.33.1` and official Apache-2.0 FLUX.1
  Schnell FP8. Exact loopback/runtime/model/core-node readiness passed with
  Provider dispatch count zero.
- Audio Slots and Narration remain outside this lane. Narration continues to
  fail closed to the audio owner.

## Canonical execution-port selection

Extend the TASK-013 application with a backwards-compatible port selector:

```text
LocalGenerationExecutionPortSelector(
  route: ModelRoute,
  capability: str,
) -> LocalGenerationExecutionPort
```

The existing `execution_port=` constructor remains supported as a fixed-port
adapter for old callers/tests. The trusted launcher uses the selector only when
more than one local visual port is configured. Selection is exact on current
route identity and capability; no fallback to another Provider/model is
allowed.

Runtime preflight becomes Queue-entry scoped. The Shell request supplies one
`queue_entry_id`; the application re-derives the exact current route/capability
from canonical Queue/Prompt/Profile state and invokes only its selected port.
No Prompt body is returned. The old argument-free preflight remains available
only for a fixed-port composition and must fail closed as ambiguous when a
selector owns multiple ports.

Before issuing a confirmation the application selects the port, performs its
read-only preflight, validates readiness route/provider/model against the
canonical route and binds route, capability, provider, model, workflow hash,
class count and runtime policy in the private pending confirmation. Apply
re-resolves Queue/Prompt/Profile, reselects the port and repeats the exact
readiness comparison. After preflight it enters the execution-store lock and
re-derives Queue/Prompt/Profile once more; that exact comparison is the
admission linearization point immediately before the `DISPATCHING` CAS write.
Unsupported or ambiguous
selection, including the first-slice `IMAGE_TO_IMAGE`, leaves execution history
unchanged.

## FLUX.1 Schnell image port

Add a separate `LocalComfyTextToImagePort`; do not weaken or branch inside the
verified MiniMax H3 T2V port.

Exact admitted route:

- workload `IMAGE`;
- provider family `COMFYUI`;
- provider ID fixed by trusted configuration;
- model ID fixed by trusted configuration;
- cost class `LOCAL_FREE_AI`;
- capability `TEXT_TO_IMAGE`;
- credential, endpoint override and arbitrary route settings absent.

The package-owned API workflow has an exact checksum and the exact core class
set:

- `CheckpointLoaderSimple`;
- `CLIPTextEncode`;
- `EmptyLatentImage`;
- `KSampler`;
- `VAEDecode`;
- `SaveImage`.

Only `PROMPT`, deterministic `SEED`, bounded `WIDTH`, `HEIGHT`, `STEPS` and an
operation-owned `OUTPUT_PREFIX` are placeholders. The checkpoint is the exact
`flux1-schnell-fp8.safetensors`; sampler/scheduler/CFG/denoise are package-owned
constants. Prompt text is private and is never written to the dispatch journal,
public Shell result or Evidence document.

Before dispatch the port verifies:

- exact bare `http://127.0.0.1:8188` endpoint;
- package workflow checksum/class/placeholder closure;
- current object-info class and checkpoint inventory;
- exact runtime listen/port/output-root identity;
- prohibited memory flags absent;
- resource floors and regular non-symlink roots;
- Prompt checksum and no input binding for the initial T2I slice.

## State, output and recovery

Use the same state semantics as the current T2V port but a distinct versioned
image journal root/identity:

```text
PREPARED -> QUEUED -> COMPLETED | FAILED
```

Persist the Comfy `prompt_id` immediately after a known queue response. A
timeout, transport loss or missing history after dispatch is uncertain and
must never be replayed automatically.

TASK-013 gains a separate explicit Human recovery action; normal execute is
never reused for recovery. It loads the exact outer `DISPATCHING` event and the
operation-owned image journal under the project execution lock, verifies
execution/Queue/route/model/workflow/prompt identity and then calls a port
`recover` operation which is forbidden to queue a prompt. `PREPARED` without a
`prompt_id`, missing history, mismatched/tampered journal and still-running
Provider state remain blocked without an outer transition. A verified existing
Provider failure appends `FAILED`; a verified existing completed output appends
`COMPLETED`. The outer event CAS is rechecked before the terminal append. This
is the only restart route from outer `DISPATCHING`; no blind replay or second
Comfy prompt is allowed.

Exactly one image descriptor below
`<comfy-output>/bai-task013-image/<execution_id>` is required. Resolve it with
the existing traversal/symlink/type containment helper, require a supported
image suffix and non-zero bounded size, then structurally decode/probe the
actual image stream before terminal completion. The probe must confirm the
format matches the suffix, positive bounded dimensions and configured output
dimensions, and reject corrupt/truncated/polyglot/wrong-media bytes. Copy it to
the operation-owned
`project-output://generated/<execution_id>/result.<suffix>`, and verify source
and copied SHA-256, then probe the copied bytes again so post-copy tamper cannot
be terminalized. Return media kind `IMAGE`; do not create an Asset or
Candidate in the port. Existing Output Adoption remains their sole owner.

## V6.1.1 interaction

For each Queue entry that is admission-ready and has no execution history:

1. show Scene, Slot, route/model, local-free cost and media kind;
2. offer `Runtime確認` using Queue-entry-scoped preflight;
3. offer `この1件を生成` only after readiness passes;
4. call existing prepare execution;
5. show an explicit Human confirmation stating that DISPATCHING is durable and
   automatic retry is forbidden;
6. apply once, or call the explicit cancellation API when Human rejects, and
   refresh Queue/Image lineage;
7. after COMPLETED, keep Output Adoption as a separate explicit confirmation;
8. after adoption, navigate to Asset Review; Human ACCEPT/LOCK remains separate.

The Image workspace may filter IMAGE rows, but the underlying execution and
adoption methods remain shared canonical services. No bulk `Execute All` is
introduced.

All public Queue/execution/adoption snapshot, readiness, preparation, apply,
cancellation and recovery calls run for their full duration under the trusted
launcher runtime lease. Closing the launch first rejects a retained old bridge;
closing during an admitted operation waits for that operation before releasing
the OS lock, so a successor runtime cannot overlap Provider or canonical store
mutation. D-C must include after-close and in-flight-close barrier negatives
with Provider/store/Asset state unchanged for rejected calls.

## Atomic units

### Unit D-A — Port selection contract

- add backwards-compatible route/capability port selector;
- add Queue-entry-scoped preflight and exact Shell schema;
- add explicit confirmation cancellation and bounded pending-token admission;
- guard the visual generation public bridge for the full launcher operation;
- preserve fixed T2V callers;
- concurrency, stale Queue/Profile and unsupported-route negatives;
- no native dispatch.

### Unit D-B — FLUX image port

- package-owned body-free workflow resource and checksum;
- image config/port/journal/containment;
- exhaustive fake-client dispatch/recovery/failure tests;
- trusted launcher optional image composition;
- read-only real runtime preflight only.

### Unit D-C — Shell/UI and canonical adoption vertical

- V6.1.1 individual execution/preflight controls;
- bound fake vertical through IMAGE output adoption and Candidate projection;
- actual local generation only under the existing explicit Human confirmation;
- real generated bytes/hash and read-back Evidence;
- no automatic Human ACCEPT/LOCK/Timeline/Export.

## Gates and acceptance

- No paid/cloud Provider, credentials, custom-node install or model pull by the
  Product.
- Runtime/model installation is separately documented and was sent to the BAI
  DEVELOPMENT OS Secretary route.
- Human GO and per-entry execution confirmation remain mandatory.
- Model/license/profile/resource/currentness drift fails before dispatch.
- One Queue entry owns at most one execution identity and one provider journal.
- Same-entry retry/restart never blindly queues a second prompt.
- Output containment/checksum/structural image identity must pass before the
  TASK-013 terminal completion and again before adoption.
- Output Adoption is the only Asset/Candidate minting boundary.
- Human Audit decision, WORLD LOCK, Timeline mutation, Final Review and Export
  are not inferred from generation success.
- Required independent Critic/Tester/Judge findings: `C/H/M = 0/0/0`.

## Initial allowed files

- `src/ai_video_production/creative_generation_execution_application.py`
- `src/ai_video_production/local_comfy_image_generation_port.py` (new)
- `src/ai_video_production/workflow_resources/flux1_schnell_fp8_t2i_api.json` (new)
- `src/ai_video_production/task036_trusted_launcher.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- direct tests for these files and impacted element/visual contracts
- this design and the installation runbook

`tmp/`, operator workflows/prompts, generated media, shared runtime settings,
BAI Development OS source, audio owner source, CHANGELOG and release metadata
must not be modified by these units without a separate applicable gate.

## D-C implementation evidence

- The trusted launcher accepts image-only or dual image/video `1.2.0`
  configuration while preserving the `1.1.0` video-only contract. One external
  Comfy output root may be shared, but project output, staging and journals stay
  inside the Product project.
- Route selection closes enabled/workload/cost/credential/endpoint/settings and
  exact capability before durable `DISPATCHING` admission.
- Output Adoption derives and verifies the canonical Slot from the exact Queue
  entry without changing the existing TASK-013 `1.0.0` event schema. TASK-013
  exposes an explicit Human recovery operation for ports that support durable
  reconciliation. Recovery
  calls only the port journal/history reconciliation method and never execute or
  queue; pending/unknown/tampered state remains `DISPATCHING`.
- V6.1.1 stores readiness only for the exact Queue and execution snapshot
  coordinate. The execution button is disabled until that entry passes current
  runtime preflight, and every refresh invalidates the UI readiness cache.
- A bound Shell fake vertical writes one structurally verified PNG, preserves
  the exact output SHA through TASK-013 and TASK-003 ingestion, and ends with one
  TASK-037 IMAGE Candidate in `READY_FOR_AUDIT`. It does not ACCEPT, LOCK,
  publish, mutate Timeline/NLE, or start Export.
- The launcher lease barrier rejects new execution/adoption calls after close
  begins, waits for an already admitted operation, and prevents a successor
  runtime from overlapping Provider/store/Asset mutation.
- Final verification on the latest bytes: focused integration `192 passed`;
  risk-proportional repository regression `2406 passed, 1 skipped` after
  excluding two unrelated WSL collection modules that require `tkinter`;
  changed Python compile, embedded JavaScript syntax and diff checks passed.
- Independent Tester, Judge and Acceptance reviews passed. Final unresolved
  findings are `C/H/M/L = 0/0/0/0`. Actual Comfy execution and packaged UI
  read-back remain a separate native Human Gate and are not claimed here.
