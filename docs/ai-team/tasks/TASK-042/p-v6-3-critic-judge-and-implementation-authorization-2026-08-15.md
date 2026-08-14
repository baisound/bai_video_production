# TASK-042 — P-V6-3 Critic, Judge and Implementation Authorization

## Reviewed baseline

- Exact fresh-main baseline:
  `92ff6938b9def12161d8635048ad3714315ed9d4`
- Selected Queue unit: `BVP-TASK-042-P-V6-3-DESIGN / DESIGN_ONLY`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Builder design:
  `p-v6-3-autonomy-current-main-audit-and-builder-design-2026-08-15.md`
- Stable release: `v0.20.1`

## Critic cycle 1 — authority and duplicate-truth review

1. `CRITICAL / CLOSED`: Quick Generate could reuse the approved planner by
   passing `plan_approved=true`. The design prohibits this and defines a distinct
   `QUICK_INTENT` authority with no Approved Plan/Human GO claim.
2. `HIGH / CLOSED`: compiled Prompt metadata could become a second Prompt
   registry. It is an optional typed binding inside the existing TASK-040
   `PromptEntity`; the Quick store owns intent authority only.
3. `HIGH / CLOSED`: Quick outputs could create a parallel Candidate lifecycle.
   Every intent binds an exact TASK-037 target Slot and adoption is a read-only
   projection over existing TASK-040/037/038 truth.
4. `HIGH / CLOSED`: raw JA/normalized/EN/negative bodies could leak through
   serialization, Evidence or exception details. Durable/public objects carry
   references and hashes only, with explicit body-absence tests.
5. `HIGH / CLOSED`: Provider/Model listing could equate catalog or credential
   presence with runtime readiness. Readiness is a conjunction of enabled,
   workload/capability, catalog, adapter, availability and credential predicates,
   with blockers exposed and sensitive fields omitted.
6. `MEDIUM / CLOSED`: Quick mode scope could absorb Timeline audio or Shell UI.
   P-V6-3 defines backend Audio Quick intent only; P-V6-4 owns Timeline audio and
   P-V6-5 owns presentation.
7. `HIGH / CLOSED`: a Quick reference labeled as a Lock could bypass current
   WORLD LOCK truth. Lock roles require exact TASK-037 role/Slot/Candidate/Asset/
   checksum `LOCKED/CURRENT`; host-file inputs require prior Asset ingest.

## Critic cycle 2 — compatibility, recovery and executable-path review

1. `HIGH / CLOSED`: P-V6-2 v2 Queue proof passes helper tests but cannot survive
   durable validation. The corrective is Implementation Order step 1 and must
   add actual enqueue/apply/restart/reload coverage.
2. `HIGH / CLOSED`: extending Prompt serialization could rewrite legacy
   snapshots. Optional compilation fields are omitted for legacy records and old
   load/no-op save shape is explicitly gated.
3. `HIGH / CLOSED`: Quick apply could partially mutate Prompt, Production and
   intent stores. Prompt and Production are read-only inputs; apply writes only
   the Quick store after exact three-snapshot revalidation.
4. `HIGH / CLOSED`: a one-shot Quick decision could be mistaken for paid/native
   dispatch authorization. P-V6-3 records intent only and fixes all execution,
   Candidate creation and media-write flags false; actual adapters remain outside
   Allowed Files.
5. `MEDIUM / CLOSED`: same-hash references could resolve to the wrong typed role.
   Quick references bind explicit identity/role/source; duplicates or ambiguous
   frame paths fail closed rather than matching by hash alone.
6. `MEDIUM / CLOSED`: design completion could imply Product/native release.
   Stable release remains `v0.20.1`; no version, Tag, Release, Deploy or native
   acceptance claim is allowed.

Result: `CRITIC_PASS_AFTER_TWO_FIX_CYCLES`; unresolved Critical/High `0 / 0`.

## Final plan

1. Fix and fully persist/reload the exact v2 WORLD LOCK Queue proof.
2. Implement immutable structured JA/JA/EN Prompt compilation.
3. Bind compilation metadata into the one TASK-040 Prompt registry compatibly.
4. Implement Provider -> compatible Model readiness projection without secrets.
5. Implement versioned Quick intent, store and one-shot CAS/restart application.
6. Implement read-only Quick output adoption status over canonical stores.
7. Run focused/full/cross-platform gates and implementation Critic.
8. Synchronize local truth and publish only through a dedicated PR.

## Implementation Allowed Files

- `src/ai_video_production/visual_prompt_compilation.py` (new)
- `src/ai_video_production/generation_route_projection.py` (new)
- `src/ai_video_production/quick_generation.py` (new)
- `src/ai_video_production/quick_generation_store.py` (new)
- `src/ai_video_production/quick_generation_application.py` (new)
- `src/ai_video_production/prompt_registry.py`
- `src/ai_video_production/prompt_registry_store.py`
- `src/ai_video_production/prompt_evidence_application.py`
- `src/ai_video_production/generation_queue_application.py`
- the six exact TASK-042 tests named in the Builder design
- existing TASK-027/037/038/040 Prompt/Queue/store tests only for explicit
  compatibility and end-to-end persistence coverage
- `docs/ai-team/tasks/TASK-042/**`
- bounded status synchronization in `PROJECT.md`, `CHANGELOG.md`,
  `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md` and
  `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`

No other file is authorized. No Product schema/package/version, Shell UI,
Provider adapter, Credential vault, native runtime, media output, Tag, Release
or Deploy change is authorized.

## Judge

`P_V6_3_DESIGN_LOCAL_PASS / HOSTED_DESIGN_PR_AUTHORIZED`

This exact design branch is cadence merge `1 / 2` only after hosted `9 / 9`,
exact main verification and cleanup. Implementation remains `NOT_STARTED` until
that hosted closure and a fresh-main AUTONOMY evaluation selects
`BVP-TASK-042-P-V6-3-IMPLEMENTATION / IMPLEMENTATION`.
