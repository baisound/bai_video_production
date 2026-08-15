# TASK-044 — Current-main Audit, DEV Profile and Builder Design

## 1. Current OS audit and Source of Truth

- Product: `BAI VIDEO PRODUCTION`
- Development foundation: BAI Development OS Consumer Project Mode
- Adapter compatibility: `.bai-os/project.json / 1.0.0`
- Current governance: external BAI Development OS v1.1.0 / Architecture Ver.2.29
- Checkout: fresh single-branch clone from `origin/main`
- Branch: `refactor/task-044-interactive-nle-design`
- Exact baseline: `19f1a94f11a783f475141af015351f64aff1b7d8`
- Worktree at audit start: clean
- PR #67: `MERGED`, exact merge SHA above, all `9 / 9` checks PASS
- Stable release: `v0.20.1`

The current checkout is newer than the handoff/design snapshots and is Source of
Truth. TASK-042 P-V6-4 is now hosted-closed. TASK-043 is hosted-closed. Protected
old WIP under `D:\BAI` remains outside this checkout and is not modified.

## 2. Registry and authority confirmation

TASK-044 is already allocated without renumbering any Task. Its dependency gate
is now satisfied:

```text
TASK-043 Project/Migration/Recovery/Durable Jobs HOSTED_CLOSED
    + TASK-042 P-V6-4 Timeline Audio HOSTED_CLOSED
    -> TASK-044 RUNNABLE
```

TASK-044 owns Product interactive Timeline semantics, practical Unified NLE
presentation and Export Queue composition. Existing authority remains:

| Truth / operation | Existing owner | TASK-044 use |
|---|---|---|
| Blueprint frame ranges | TASK-042 | immutable input proof |
| Audio Timeline plan/history | TASK-042 P-V6-4 | read/current binding and revision input |
| Cut review / approved Edit Plan | TASK-007 | distinct review overlay and immutable input |
| frame mapping | TASK-022 | exact conversion only |
| Audio placement compilation | TASK-026 | composition only |
| Resolve assembly mutation | TASK-010 | external execution adapter and idempotency |
| Render QA | TASK-011 | post-export inspection |
| Editor handoff | TASK-012 | optional output path |
| Desktop authority boundary | TASK-036 | one Shell; no second launcher |
| Product Project/save/history | TASK-043 | aggregate persistence and recovery |
| Durable Product Job | TASK-043 P-FND-4 | Export/background truth |

TASK-044 creates no second Candidate, Audit, LOCK/STALE, Generation Queue,
Timeline Audio, Product Project, durable job, Resolve or Render truth.

## 3. Current Product audit

### Implemented and reusable

- one packaged Windows Shell and allowlisted bridge;
- static Timeline blocks for subtitle, cut overlay and approved Edit Plan;
- Cut Candidate click selects the review Candidate;
- exact Shell command categories and one-shot confirmation;
- frame/timebase, Edit Plan, Assembly Plan, Render QA and Handoff contracts;
- TASK-042 frame-authoritative Audio Timeline;
- TASK-043 Project Manifest, coordinated save/recovery, Undo/Redo,
  Autosave/Backup and durable jobs;
- read-only durable job to Shell JobSnapshot projection.

### Missing or partial

1. Static HTML lanes are hard-coded; track topology is not a closed Product model.
2. Generic clip click has no selection state and cannot seek; candidate click is
   the only bounded Timeline interaction.
3. There is no shared frame viewport transform for ruler, playhead, clips,
   zoom/Fit/scroll or windowing.
4. Trim, snap, IN/OUT and crossfade are text/design only.
5. The Timeline presentation mixes microseconds with the new frame-authoritative
   Audio plan.
6. Durable jobs exist, but no closed Export preparation contract binds Project,
   Timeline, Assembly, preset and logical output target.
7. `Execute All` semantics, stale pending exports and unknown external dispatch
   recovery are not implemented.
8. The UI does not virtualize a two-hour / 10,000-item fixture.
9. Keyboard and Narrator semantics cover the minimum Shell but not dynamic NLE
   tracks, selection, playhead or Export Queue.

No current source supports a claim that practical NLE or Export Queue is complete.

## 4. DEV Profile re-decision

TASK-044 remains `DEV-4 FOUNDATION CRITICAL`.

- system scale: Product-wide Shell + Project persistence + external adapter
- criticality: high; wrong frames can mutate an NLE target
- failure impact: media/export state and Human editing decisions
- reversibility: local planning is reversible, external NLE state may be unknown
- concurrency: Shell session, autosave, durable jobs and external adapter
- compatibility: released v0.20.1 Projects and existing static projection
- security/privacy: host paths, output destinations, private project/media data

Required gates: current-main audit, exact Allowed Files, Builder design, two
Critic cycles, focused tests, full regression, hosted checks and native acceptance.

## 5. Sequential Atomic Units

### P-NLE-1 — Timeline semantic projection and interaction reducer

Create a transport-neutral, frame-authoritative read model:

- `TimelineTrack`: stable ID, ordered role, media kind, minimum-required flag;
- `InteractiveTimelineClip`: stable ID, source owner/ref/hash, frame range,
  track ID, role, state and immutable lineage;
- `TimelineViewport`: frame range, pixels-per-second/rational transform,
  horizontal/vertical window and Fit mode;
- `TimelineInteractionState`: selected clip IDs, focused semantic entity,
  playhead frame and optional IN/OUT proposal;
- deterministic `TimelineWindowProjection` containing only visible/overscan rows.

Rules:

- frames, not CSS pixels or microseconds, are authoritative;
- one rational transform derives ruler, clips, playhead and scroll;
- generic clip click means select only;
- ruler, empty lane, playhead drag or explicit Seek command moves playhead;
- Cut Candidate click retains TASK-007 review behavior and does not become a
  generic seek side effect;
- selection, focus, zoom and scroll are reversible session/user-presentation
  state, not Product Project semantic truth;
- track definitions and clips derive from current TASK-007/022/042 inputs;
- no media, Provider or native mutation is introduced.

P-NLE-1 exit: focused model/reducer/windowing/Shell-spec tests, 10,000-item
deterministic fixture, full regression, Critic 0/0 and hosted closure.

### P-NLE-2 — Trim, snap, IN/OUT and Product command history

Add immutable proposal/application contracts over the current exact Timeline:

- `timeline.seek` and `timeline.selection.update`: `LOCAL_REVERSIBLE`;
- `timeline.viewport.update`: `LOCAL_REVERSIBLE`;
- `timeline.edit.prepare`: `READ_ONLY`;
- `timeline.edit.apply`: `HUMAN_FINAL_AUTHORITY`;
- `timeline.in_out.update`: `LOCAL_REVERSIBLE` until applied to an export/edit;
- `timeline.track.prepare/apply`: minimum-track and dependency checked.

Every semantic edit binds current Product Manifest, Timeline plan/revision/hash,
source clip/item hash, expected track topology and exact before range. Apply creates
a new append-only Timeline revision through the TASK-043 save coordinator and a
compensating Project command-history record. No last-writer-wins is allowed.

Snap candidates are deterministic and labeled: playhead, Scene boundary, clip
edge, narration cue, marker and exact frame grid. One winner uses distance then
stable priority/identity. STRETCH/crossfade remain explicit proposals and cannot
silently compile through an adapter that lacks support.

P-NLE-2 exit: command/CAS/stale/Undo/Redo/autosave/reopen tests, full regression
and hosted closure.

### P-NLE-3 — Durable Export Queue composition

Add `ExportPreparation` and `ExportQueueApplication` over TASK-043 jobs. Each
Export binds:

- Project ID, exact Manifest checksum and Product version;
- Timeline plan ID/revision/hash and current edit/assembly-plan checksum;
- preset ID/version/checksum and frame/audio output contract;
- logical output-target identity only; no host path in public/durable records;
- Resolve Project/Automation Timeline identity where applicable;
- exact expected input hashes, authority class and cost truth;
- deterministic durable operation identity.

Enqueue is local durable planning and is idempotent. It does not authorize
Resolve/render. Before external dispatch, the application revalidates all inputs,
prepares the existing TASK-010/011 one-shot confirmation, writes DISPATCHING before
the side effect and binds the launcher-private destination. A changed input becomes
`STALE_REPREPARE_REQUIRED`. Restart from DISPATCHING/RUNNING becomes UNKNOWN and
is never automatically replayed.

`Execute All` prepares/executes each item separately. One confirmation never grants
blanket external mutation. Safe cancel affects only states with no ambiguous
external side effect. Result identity and Render QA Evidence bind success.

P-NLE-3 exit: prepare/enqueue/idempotency/stale/restart/UNKNOWN/reconcile/cancel
tests, no-host-path tests, full regression and hosted closure.

### P-NLE-4 — Unified Shell/UI, performance and accessibility

Wire the accepted models/applications into the existing TASK-036 bridge and one
Desktop HTML surface:

- dynamic semantic tracks and virtualized clip DOM;
- ruler, playhead, zoom, Fit Entire/Selection and bounded scroll;
- visibly distinct selection vs seek vs Candidate review;
- trim/snap/IN-OUT prepare/apply flow;
- durable Export Queue rows, stale/unknown/recovery actions and per-job authority;
- keyboard parity for every pointer operation;
- semantic track/clip/time/state names, roving focus and live status;
- 100/150/200% DPI, narrow width and mixed-monitor resilience.

No JavaScript durable store is allowed. The bridge returns closed view models and
calls allowlisted typed application methods. All paths and native objects remain
Python-only.

P-NLE-4 exit: browser/bridge regression, 10,000-item bounded DOM fixture, packaged
Windows keyboard/Narrator/zoom/scroll/trim/Export Queue Evidence. TASK-044 closes
only after native interaction acceptance. Version/Tag/Release remains TASK-045.

## 6. Compatibility and migration

- Released v0.20.1 Projects remain readable.
- Projects without TASK-044 child state receive read-only derived defaults.
- Existing `EditingProjection 1.0.0`, TASK-007 Candidate click and TASK-036
  command behavior remain compatible.
- New Product-semantic state is versioned and bound as a TASK-044 Project child;
  UI/session state is not forced into Product history.
- Unknown/newer schemas fail with migration-required; no implicit downgrade.

## 7. Security, failure and recovery

- no `git add .`, force push, main direct push or unknown-change deletion;
- no arbitrary host path, credential, Prompt body or media bytes in public state;
- Project root/child paths remain contained and non-symlink;
- stale confirmation is one-shot consumed;
- external unknown state is Human Gate, not retry;
- Reject is not Delete; cancel is not external rollback;
- paid Provider and new credential work remain separate Human Gates;
- no Production Deploy or release in TASK-044.

## 8. Exact Allowed Files

### Design unit

- `docs/ai-team/tasks/TASK-044/**`
- bounded hosted-status synchronization in `PROJECT.md`, `CHANGELOG.md`,
  `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md`,
  `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`

### P-NLE-1 candidate

- new `src/ai_video_production/interactive_timeline.py`
- new `src/ai_video_production/interactive_timeline_projection.py`
- bounded `desktop_shell.py`, `desktop_shell_projection.py`, `__init__.py`
- focused `tests/test_task044_*timeline*.py`
- TASK-044 Evidence and bounded current-state surfaces

### P-NLE-2 candidate

- new `interactive_timeline_store.py`, `interactive_timeline_application.py`
- bounded `timeline_audio*.py`, `product_project*.py`, `project_history.py`,
  `desktop_shell.py`, matching schemas/exports/tests/docs

### P-NLE-3 candidate

- new `export_queue.py`, `export_queue_application.py`
- bounded `durable_product_job.py`, `desktop_shell.py`, TASK-010/011/012
  composition only, matching schemas/exports/tests/docs

### P-NLE-4 candidate

- bounded `task036_shell_ui.py`, `desktop_editing_application.py`,
  `desktop_shell_projection.py`, launcher composition, focused UI/native gates,
  user documentation and TASK-044 Evidence
- new bounded `task044_nle_shell.py` Python-owned view/controller adapter; it
  stores no second Product truth and exposes only closed view models and typed
  allowlisted commands to the existing TASK-036 bridge
- bounded `interactive_timeline.py` projection-field correction required so
  the Shell accessibility name receives the track-derived media kind rather
  than an undefined JavaScript value
- bounded `export_queue_application.py` recovery composition required so the
  existing typed UNKNOWN recovery contract can be invoked per job by the
  Shell without direct durable-store mutation or blanket authority

Any file outside the exact active unit requires a new audit/Allowed Files update.

