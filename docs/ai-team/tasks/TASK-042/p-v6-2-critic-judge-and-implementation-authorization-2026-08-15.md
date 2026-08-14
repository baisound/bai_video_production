# TASK-042 — P-V6-2 Critic, Judge and Implementation Authorization

## Critic cycle 1

1. `CRITICAL / CLOSED`: Human GO could again be treated as official WORLD LOCK.
   The projection separately proves the exact current TASK-037 Slot, locked
   Candidate, lifecycle, Asset ID/checksum and CURRENT state at use time.
2. `CRITICAL / CLOSED`: a new WORLD LOCK store would create two lock truths.
   The design is a stateless projection over Blueprint/Approved Plan and the
   existing TASK-037 registry; no new canonical store is allowed.
3. `HIGH / CLOSED`: installing a v2 Plan into a registry with reference Slots
   could overwrite or recreate their identities. Reference Slots are read-only
   prerequisites; installation adds only Scene outputs and dependency edges.
4. `HIGH / CLOSED`: an installer failure after adding some Slots could leave an
   in-memory registry partially changed. The complete v2 install is preflighted
   on an isolated copy before the authoritative registry is replaced and saved.
5. `HIGH / CLOSED`: accepting input by checksum alone can bind the wrong role or
   Candidate when hashes repeat. V2 proof uses deterministic frame path plus
   exact Slot/Candidate/Asset identity; ambiguous repeated hashes fail closed.

## Critic cycle 2

1. `HIGH / CLOSED`: adding enum values can make old snapshots unreadable or
   loosen unknown-value handling. Old serialized values/output remain unchanged;
   only the three explicit additions parse and all other values still fail.
2. `HIGH / CLOSED`: stale propagation from a reference could stop at the source
   Candidate. Deterministic Candidate -> Scene edges connect the existing
   Slot -> Candidate and Scene -> output Slot graph, so propagation reaches all
   bound downstream outputs without automatic regeneration.
3. `HIGH / CLOSED`: prepared installation could remain valid after a Human
   changes a lock. The one-shot confirmation binds exact Proposal and Production
   snapshot checksums; any drift consumes and rejects it.
4. `HIGH / CLOSED`: enabling v2 in the low-level admission service while Queue
   still accepts GO-only proof would create inconsistent authority. Installer,
   admission and Queue proof changes ship in the same Allowed Files/Gate.
5. `MEDIUM / CLOSED`: P-V6-2 could absorb P-V6-3 Prompt-role design. This slice
   exposes deterministic frame paths and fails on ambiguity; typed Prompt
   compilation and Quick Generate remain P-V6-3.
6. `MEDIUM / CLOSED`: design completion could imply Product/native release.
   Stable release remains `v0.20.1`; P-V6-2 is a source integration checkpoint
   with no Tag, Release, Deploy or native acceptance claim.

`CRITIC_PASS_AFTER_TWO_FIX_CYCLES`; unresolved Critical/High `0 / 0`.

## Implementation Allowed Files

- `src/ai_video_production/blueprint_v2_world_lock.py` (new)
- `src/ai_video_production/production_control.py`
- `src/ai_video_production/production_control_store.py`
- `src/ai_video_production/production_orchestrator.py`
- `src/ai_video_production/approved_plan_orchestration.py`
- `src/ai_video_production/approved_plan_trace.py`
- `src/ai_video_production/production_control_application.py`
- `src/ai_video_production/planning_application.py`
- `src/ai_video_production/generation_queue_application.py`
- `tests/test_task042_blueprint_v2_world_lock.py` (new)
- `tests/test_task042_blueprint_v2_production_control.py` (new)
- `tests/test_task042_blueprint_v2_generation_admission.py` (new)
- existing TASK-027/037/039/042 tests only when required for explicit v1
  compatibility, application CAS/restart, trace, Queue or stale coverage
- `docs/ai-team/tasks/TASK-042/**`
- bounded status synchronization: `PROJECT.md`, `CHANGELOG.md`,
  `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md`,
  `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`

No schema/version metadata, Product shell UI, second store, Provider adapter,
native runtime, media output, Release or Deploy file is allowed. If
implementation proves a necessary file outside this list, stop and return to
Builder/Critic before editing it.

## Required gates

- old SlotKind/snapshot/v1 compiler/Plan/Queue behavior compatibility;
- exact v2 frame path, role, project, Slot, Candidate, Asset and checksum proof;
- missing/extra/mismatch/STALE/unlocked/ambiguous fail-closed coverage;
- v2 install preflight, one-shot stale confirmation and no partial publication;
- Candidate/Slot -> Scene -> output transitive stale propagation;
- DIRECT exact previous-End identity and non-overridable failure;
- Proposal/Production restart and cross-store checksum/recovery behavior;
- focused tests, full regression, Windows and WSL2 compileall, diff check;
- Critic unresolved Critical/High `0 / 0` and hosted `9 / 9`.

## Judge

`P_V6_2_DESIGN_LOCAL_PASS / HOSTED_DESIGN_PR_AUTHORIZED`

Implementation remains `NOT_STARTED`. After this exact design head passes the
GitHub matrix and merges to main, verify the exact merge SHA, remove its remote
branch and dedicated clone, create a fresh implementation clone from that main,
and run Handoff Bootstrap/Autonomous Queue with the exact `IMPLEMENTATION`
candidate. This design merge is cadence merge `2 / 2`; therefore control must
return to AUTONOMY after cleanup before P-V6-2 implementation begins.
