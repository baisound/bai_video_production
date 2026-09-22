# TASK-098 A3-R3 Cache / Restart Read-Back Pre-Mutation Review

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A3-R3`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Starting HEAD: `bcf3793e4f989fc376c758f0d6bac60387b660d2`
- Base/current-main identity at review: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Parent integration review: `PR #562`
- Status: `DESIGN_ACCEPTED_FOR_BOUNDED_IMPLEMENTATION`

## 1. Goal

Prove that an A3-R2 local model selection survives a process restart through the
existing TASK-036 launch configuration and continues to use the existing private
ASR cache route without constructing a model. Add one path-free read-back
snapshot and fake restart tests; create no new settings store.

## 2. Boundary

- The launch config remains the only persisted settings authority.
- A3-R1 revalidates an absolute local model directory on every snapshot.
- The existing `paths.asr_cache_directory` is checked for contained physical
  directory safety, including symlink/reparse ancestry, but its path/digest is
  never projected.
- A symbolic model name is reported as `LOCAL_MODEL_NOT_CONFIGURED`; it is not
  downloaded, resolved or converted by A3-R3.
- A3-R2 pending confirmations are intentionally process-local and do not survive
  service reconstruction.

## 3. Read-back projection

The caller supplies the exact current launch-config SHA-256. A stable read and
TASK-036 validation occur before any model-directory read. The projection is one
of:

- `READY`: exact config identity, safe existing cache route and A3-R1 READY local
  model;
- `BLOCKED`: closed local/cache reason only, no path or partial private record;
- `LOCAL_MODEL_NOT_CONFIGURED`: current model is symbolic and no local
  directory was inspected.

Every projection fixes settings update, model load, inference, Provider,
network and download effects to false. READY may state only that existing cache
reuse is configured and safe; it does not claim a cache hit or runtime/model
compatibility. Because A3-R2 intentionally adds no persisted model-manifest
field, A3-R3 revalidates the current directory body but explicitly reports
model-manifest continuity as unconfirmed.

## 4. Allowed files

- `src/ai_video_production/task098_faster_whisper_model_settings.py`
- `src/ai_video_production/task036_shell_ui.py`
- `tests/test_task098_faster_whisper_model_settings_restart.py`
- this review
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/evidence/a3-r3-cache-restart-readback-20260922-r01.md`
- bounded `docs/ai-team/current-state.md` and `docs/ai-team/task-index.md` status
  synchronization at completion only

Native dialog code, schema, launch-config shape/version, Provider/runtime,
dependency, package, installer, Product version and private assets must not
change.

## 5. Acceptance tests

- a new service instance reads back an A3-R2 update as the same path-free model
  ID and exact config digest;
- the existing cache value remains unchanged and is reported only as safe reuse
  availability, never as a cache hit;
- stale expected config identity fails before model/cache projection;
- symbolic model, missing/structurally-invalid model and symlink/reparse cache
  ancestry fail closed without settings writes;
- an A3-R2 confirmation cannot be applied through a reconstructed service;
- snapshot and Shell endpoint are exact-request, read-only and path-free;
- focused A3-R3 through A3-R0, settings, Shell and trusted-launch regression
  passes without model construction;
- Allowed Files, diff check and external Evidence read-back pass.

## 6. Critic / Tester / Judge decision

### Critic

- High: calling existing cache presence a cache hit would fabricate execution
  Evidence. Corrected to `cache_reuse_available`, with no hit claim.
- High: TASK-036 leaf-only path checks do not prove cache ancestry is free of
  symlink/reparse aliases. A3-R3 performs an additional physical ancestry check.
- Medium: restoring A3-R2 pending confirmations would turn transient Human
  intent into durable authority. Pending state remains process-local only.
- Medium: READY could be misread as proof that the directory body is identical
  to the pre-restart manifest. Corrected with fixed-false manifest-continuity
  and runtime-compatibility flags.

Final design finding count: `Critical 0 / High 0 / Medium 0 / Low 0`.

### Tester

All restart/config/cache/model scenarios use pytest-owned temporary roots and
fake services. No runtime or native effect is required.

Decision: `PASS / IMPLEMENTATION_TEST_PLAN_ACCEPTED`.

### Judge

The unit is a read-only restart/read-back projection inside existing A3
authority. It does not activate Product composition or model execution.

Decision: `ACCEPT / A3-R3_IMPLEMENTATION_ALLOCATED`.
