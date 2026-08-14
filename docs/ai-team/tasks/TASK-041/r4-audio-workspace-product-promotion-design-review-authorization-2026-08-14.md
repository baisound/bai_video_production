# TASK-041 — R4 Audio Workspace Product Promotion Design / Review / Authorization

- Date: `2026-08-14`
- Owner route: continue BAI VIDEO PRODUCTION autonomously under BAI Development OS
- Queue result: `TASK-041-AUDIO-WORKSPACE-PRODUCT-PROMOTION / IMPLEMENTATION`
- Base main: `8df313fec57d9913639e81a006faa016749ebb8f`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`

## Current OS audit

The fourth-cycle checkout is a clean fresh clone of exact main after PR #46.
TASK-013 native H3 remains parked behind `HG-BVP-TASK013-NATIVE-003`, and
TASK-014 paid narration remains parked behind `HG-BVP-TASK014-PAID-001`.
BAI Development OS selected independent TASK-041 Product promotion.

Current checkout already contains the TASK-041 domain registry, checksum/CAS
snapshot store, Human placement-decision service and TASK-041 -> TASK-026
binding. TASK-026 deterministic placement foundation and TASK-037 Production
Control are present. The missing Product delta is durable project-scoped
orchestration and Unified Desktop/trusted-launch composition.

## Registry and DEV Profile decision

This is an existing TASK-041 promotion, not a new Task number. Owner direction
authorizes the safe Product promotion while paid/native/external-write gates
remain parked. It owns Human decisions tied to immutable Candidate hashes and
future NLE placement intent, so DEV-4 remains appropriate.

## Allowed files

- `src/ai_video_production/audio_workspace_application.py`
- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- corresponding TASK-041/TASK-036 tests
- `PROJECT.md`, `CHANGELOG.md`
- Product current-state, summary, Task index and canonical roadmap
- TASK-041 design and closure Evidence

Provider adapters, credentials, `owner_narration.py`, raw media, derived media
bytes, TASK-010 Resolve mutation, TASK-012/Cubase, `evidence/native/**`, package
version, Tag and Release are outside Allowed Files.

## Builder design

1. Add `Task041AudioWorkspaceApplication` bound to an existing project root,
   exact project ID and TASK-037 Production Control application.
2. Reload Production and Audio snapshots for every command, expose their exact
   hashes, and serialize audio writes with local snapshot locks plus CAS.
3. Derive placement candidates only from Product audio Slots (`SE`, `BGM`,
   `NARRATION`) and current `ACCEPTED`/`LOCKED` Candidates. Never persist host
   paths or media bytes.
4. Add one-shot, hash-bound prepare/apply placement registration. The operation
   records review intent only and starts no TASK-026 compile or Resolve write.
5. Reuse the existing one-shot Human placement-decision service, rehydrate it
   against current durable state, and persist the result. ACCEPT remains
   impossible unless the exact Candidate is LOCKED.
6. Add `AUDIO_WORKSPACE` to the unified Shell, an accessible drawer showing
   available audio Candidates, placement timing/gain/decision and explicit
   Human actions, plus allowlisted bridge methods.
7. Compose the application in the trusted launcher by default without any
   Provider, DAW or NLE connection.

## Critic review

1. **Critical — placement ACCEPT could become Resolve authority.** Resolution:
   every response fixes `task026_compile_started` and
   `resolve_mutation_started` false; compilation remains a later explicit unit.
2. **Critical — UI promotion could silently call paid narration/generation.**
   Resolution: no Provider/credential port is injected or imported.
3. **High — an unlocked or changed Candidate could receive ACCEPT.**
   Resolution: prepare/apply bind exact Production checksum, Candidate ID/hash
   and LOCKED lifecycle; stale state fails closed.
4. **High — concurrent Audio decisions could overwrite each other.**
   Resolution: reload under a local exclusive snapshot lock and publish through
   the existing CAS store.
5. **High — arbitrary Candidate kinds could be mislabeled as audio.**
   Resolution: placement registration derives role from SE/BGM/NARRATION Slot
   ownership and requires exact role agreement.
6. **High — UI refresh could mutate state.** Resolution: snapshots are read-only;
   all durable commands require separate one-shot prepare/apply confirmation.
7. **High — non-destructive policy could be overclaimed as media processing.**
   Resolution: this unit stores metadata only and creates no derived bytes.

Unresolved design Critical/High findings: `0 / 0`.

## Final plan and authorization

The bounded Product promotion is authorized in the Allowed Files above.
Acceptance requires focused TASK-041/TASK-036 tests, full regression,
`compileall`, embedded JavaScript syntax and `git diff --check` PASS. Product
claims stop at durable Audio placement review and Human decision UX; paid TTS,
audio generation, derived-media production, TASK-026 compilation, Resolve/
Cubase mutation, Native Gate, overall TASK-041/R4 completion and Release remain
unclaimed.
