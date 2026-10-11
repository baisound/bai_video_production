# TASK-036 Human-operated model-to-export execution order

Date: `2026-09-29 JST`
State: `OWNER_DIRECTED_CONTINUATION / ORDER_FIXED / HUMAN_END_TO_END_NOT_CONFIRMED`

## Goal and authority

The Owner requested sequential implementation of missing functionality, a fresh
Task audit, and a fixed processing order in this conversation. Acceptance means
a person operates the ordinary unified application from model selection to a
verified exported video. Source implementation, synthetic fixtures, CI, and a
browser preview alone do not meet that acceptance condition.

TASK-036 is still active for P-UX-2. This continues its original presentation,
bridge composition and cross-screen responsibilities. Completed Task history is
not reopened: other Task numbers below identify canonical dependency owners,
not blanket authorization to change their domains or replay native effects.

## Fixed order

| Order | TASK-036 stage | Canonical dependency Tasks | Exit required before this stage is called complete |
|---|---|---|---|
| 0 | Fresh Task/source/authority audit | TASK-036 | Current Git, main, locks, PR overlap, exact supported flow and remaining contracts recorded; do not use historical audit gaps as current implementation truth |
| 1 | A: central settings and model selection | TASK-028/032/033/034 | Human can choose a supported model, see unavailable reasons and retain the exact choice after reopen; selection never grants generation authority |
| 2 | B: intake, planning and scenes | TASK-043/003, TASK-027/042, TASK-005/022 | One Project, approved Plan and finalized Scene/Blueprint lineage survive reopen; no replacement canonical store |
| 3 | C: generation, audio and Asset adoption | TASK-013/014/040, TASK-037/038/041; TASK-046..048 only when the selected flow needs their audio/voice capability | Required outputs are verified adopted Assets or explicit blockers. Before execution consume TASK-003/027 rights, TASK-020 resource and applicable TASK-016 privacy decisions. No fixture or configured credential substitutes for those decisions |
| 4 | D: editing and typed final approval | TASK-044/043, TASK-041, TASK-016, TASK-020, TASK-003/027 | Human edit/save/reopen and exact Final Review approval work together; fresh EDIT_PERSISTENCE, AUDIO_COMPLETION, PRIVACY, RESOURCE and RIGHTS_LICENSE owner sources are bound, not manufactured |
| 5 | E1: Export preparation, dispatch and output read-back | TASK-044, TASK-010/011/012 | Exact preset/destination and one durable Job; individual confirmation; existing renderer/QA; matching output bytes/hash/media properties; recovery to UNKNOWN without replay |
| 6 | E2/E3: ordinary packaged application human acceptance | TASK-063/066 prerequisites, then TASK-036 | Exact rebuilt package/entry identity, human F0..F10 operation, boundary restart, keyboard/accessibility and output playback/read-back; only then evaluate whole-flow completion |
| 7 | Deferred polish and additional hardening | TASK-036 and explicitly allocated dependency follow-ups | Additional security hardening, exhaustive fault/recovery scenarios, performance tuning, broader compatibility and visual polish after the ordinary supported flow is usable |

## Completion-first implementation method

The Owner's subsequent directive moves optional security/detail work to the end
of this roadmap. Prioritize one supported human-operated happy path, minimal
existing-owner integration and small end-to-end checkpoints. Do not expand a
slice with speculative threat models, unrelated compatibility, new abstraction
layers or exhaustive new fault matrices before connecting that path. Do not
confuse disabled-with-reason controls or additional unit tests with functional
completion.

This scheduling change does not waive the repository safety floor, change the
DEV-4 classification, invent Gate PASS, remove existing safeguards or authorize
paid/private/native effects. Preserve user data, one-shot confirmation, exact
Project/Job binding, consent/rights checks and truthful output verification
while implementing. Keep required focused regression and independent review
proportional to the changed boundary; defer additional hardening to order 7.

Process gaps in this order. An already implemented stage is revalidated rather
than rewritten. A stage with a blocked effect is not completed or skipped; park
that exact effect and identify its resumption condition. Independent, already
authorized no-effect contract/testing work may continue in order. No other Task,
unrelated feature or alternative UI becomes a priority implicitly. Change this
ordering only on an explicit Owner directive.

## Fresh audit and first bounded correction

- Worktree: dedicated TASK-036 `130a` checkout.
- Branch: `codex/task-036-pux2e-export-journey`.
- Audited HEAD: `03e2e18b57503d630dbd5260183c96891e498adb`, clean at intake.
- Fresh `origin/main`: `b12a98e00b14b59a8f0173201a28dac2419c474a`.
- PR #569: OPEN, MERGEABLE/CLEAN, nine checks PASS; no review/comments.
- Lock registry revision 143: zero active locks; HEAD/main registry blobs match.
- Other open PRs #561/#548/#538 do not overlap the implementation paths below.
- A..D source is not all missing. Current-model selectors and bounded application
  services already exist; human packaged end-to-end Evidence is still missing.
- Normal-launch Export is deliberately fail-closed under the E1 design. Its
  private preparation is not automatically bound because canonical external
  owner readers are missing. EDIT_PERSISTENCE is bound to TASK-044; the remaining
  AUDIO_COMPLETION, PRIVACY, RESOURCE and RIGHTS_LICENSE sources are dependencies.
- A self-checksummed audio ledger or hand-authored PASS tuple is not an
  authenticated/current owner decision. Do not wire these as default PASS.

The first audit-derived correction is truthful Export binding availability and
disabled-with-reason actions. Existing UI incorrectly offered preflight/dispatch
with unbound private providers and described preparation-unbound as merely
waiting for final approval. Correcting this does not advance stage 5 to complete,
start rendering, or change the fixed A-through-E processing order.

Bounded scope: `task044_nle_shell.py`, `task036_shell_v611.py`,
`test_task036_pux2e_export_dispatch.py`, and
`test_task036_v611_interaction_contract.py`, all within the existing PR's eleven
paths, plus this Owner-requested order record. No shared current-state, roadmap,
task-index or CHANGELOG edits. DEV-4 independent Critic/Tester review applies to
the implementation. Snapshot projection must not invoke providers, create
confirmation tokens, resolve private output paths or grant authority. Cancellation
and UNKNOWN reconciliation remain independently available.

## Gates and next action

After the bounded correction, start stage 1's ordinary-entry/reopen integration
audit and tests, using the central settings authority already present. Do not
infer that the old no-model-selector audit describes current source.

Cross-owner source writes or additional implementation paths must be bound and
authorized before mutation. Paid/Provider execution, model/runtime acquisition,
Owner Voice/private media, Resolve/native mutation, installer effects, Release,
Deploy, Production Activation and PR merge retain their separate gates. Do not
use TASK-049 packages or other Tasks' residual packages as this Task's native
Evidence. Keep the Owner-established heartbeat ACTIVE.

External operation checkpoint and test/review receipts record exact resulting
HEAD, dirty paths, resolved QA roots and residuals. No packaged-native completion
token is issued by this document or the first correction.

## First correction verification

- Builder focused Export/UI/Queue/element regression: `134 PASS in 16.87s`.
- Independent Tester focused and adjacent regression: `75 PASS in 15.27s`.
- Independent Critic fix-delta: `PASS`, unresolved `0/0/0/0`; bounded-scope Judge
  acceptance only, not Product/native completion.
- Python compilation and diff whitespace checks: `PASS`.
- Ordinary packaged EXE, Provider generation, native Export and output playback:
  `NOT_EXECUTED / NOT_CONFIRMED`.
- Stage 1 source read-back confirms existing launch-time settings bootstrap and
  central settings binding are already present. Next work must identify actual
  ordinary-entry/reopen gaps, not reimplement that completed source capability.
- No commit, push, PR merge or native effect is performed by this checkpoint.

## Stage A bounded model-settings correction

Atomic Unit: `human-operated-model-settings-r0` (2026-09-29 JST).
Allowed implementation delta: `task036_shell_v611.py` and
`test_task036_v611_interaction_contract.py`, both within the existing eleven
paths. This order record remains Owner-requested scope. Previous Export changes
and all shared owner files are preserved.

Ordinary settings controls now identify each model by its public model ID,
update availability when the user changes the selection, keep an unavailable
saved preference visible until explicitly changed, and preserve the user's input
when saving fails. Only a successful canonical settings update triggers reread.
Existing TASK-028 persistence, revision checking and execution gates are reused;
no model execution, download or second settings store was added.

- Builder focused UI/settings/Export regression: `141 PASS in 7.33s`.
- Independent Tester settings/UI and exact launch/reopen regression:
  `61 PASS in 6.27s`; launcher dependencies were injected stubs, not real runtimes.
- Independent Critic: `PASS`, unresolved C/H/M/L `0/0/0/0`.
- Diff whitespace check: `PASS`.
- Judge: accept this bounded source/test delta only; stage A human acceptance
  and the complete Product flow remain `NOT_EXECUTED / NOT_CONFIRMED`.
- External checkpoint: `TASK-036/human-operated-model-settings-r0/20260929T110318+0900/checkpoint.md`
  beneath the canonical external Evidence root. No commit/push or native effect.

Stage A source-contract correction is verified, not a claim that a person has
completed stage A in a rebuilt package. That exact human/native effect remains
parked until a TASK-036-owned package/entry and bounded native authority are
available; do not reuse another Task's residual package. Continue the fixed
order with the B intake/planning/scene source integration audit where it is an
independent, authorized no-effect unit. Before modifying launcher or Project
owners, recheck PR #591 and bind any additional path/cross-owner authority.

## Stage A required local-runtime warnings

Atomic Unit: `human-operated-runtime-warning-r0` (2026-09-29 JST).
Owner requested visible warnings when a selected model requires ComfyUI or
Ollama but that runtime is not running. This is a stage A usability correction,
not a change to the fixed processing order or an auto-start/generation grant.

Bounded implementation: `task036_shell_ui.py`, `task036_shell_v611.py`,
`test_task036_v611_interaction_contract.py` and
`test_task036_v611_visual_contract.py`, all within the existing eleven paths,
plus this order record. Earlier owned Export/settings changes are preserved.

Settings and feature readiness now show an alert only for the selected route's
required local runtime. READY has no runtime warning; NO_MODEL remains a model
availability issue. Unreachable means stopped or unable to connect, not proof
that a process is stopped. UNKNOWN explicitly means status could not be checked.
Selection changes clear obsolete alerts; the old saved-route-only central
Ollama card was removed to avoid stale warnings after switching to Cloud/Auto.

The ComfyUI bridge exposes a closed read-only state projection without endpoints,
private diagnostics or execution authority. Its actual trusted-launcher binding
is still absent: unbound ComfyUI reports UNKNOWN, not confirmed downtime.
Additional allowed-file approval for `task036_trusted_launcher.py` was requested
and remains pending. Park only that binding; before modifying it recheck PR #591
and Project-owner overlap. No real runtime probe/start, Provider generation,
download, package/build or native effect was executed in this unit.

- Builder final focused regression: `214 PASS in 7.39s`.
- Independent Tester final five-module regression: `158 PASS in 2.87s`.
- Independent Critic: `PASS`, unresolved C/H/M/L `0/0/0/0` after bounded repair.
- Intermediate regression exposed one obsolete visual marker (213 PASS/1 FAIL);
  synchronized that existing-path contract to route-scoped warnings and reran.
- Diff whitespace check: `PASS`; original element inventory is unchanged.
- Judge accepts only this bounded source/test checkpoint. Actual Product
  connection and packaged human operation remain `NOT_EXECUTED / NOT_CONFIRMED`.
- External checkpoint:
  `TASK-036/human-operated-runtime-warning-r0/20260929T112230+0900/checkpoint.md`.
- Seven dirty paths are now conversation-owned: the original four source/test
  paths, this order record, the Shell bridge and the visual-contract test.
  HEAD/PR CI remains distinct from these uncommitted changes; no push or CI rerun.

Next: obtain the one-path binding approval, then validate the existing configured
ComfyUI read-only health connection without auto-start/queueing. If approval is
not given, keep that effect parked and continue the independently authorized
stage B source audit in the existing fixed order. Human/native acceptance gates
and the ACTIVE quiet heartbeat remain unchanged.

Final source re-audit observed `origin/main` advancing to
`23f4e307212bf7d165b5e8feb75b2b438b602ddf` through PR #591. Its changed paths
do not directly overlap the eleven PR #569 paths, but include the future
trusted-launcher and canonical Project/planning owners. Branch/HEAD and known
dirty ownership remain unchanged. PR #569 is still OPEN, MERGEABLE/CLEAN with
9/9 CI PASS and zero reviews/comments; those checks cover HEAD, not this delta.
No unnecessary main merge/push was performed while PR #569 is clean. Any next
launcher/Project-owner work must reconcile the newly merged PMST boundary first.

## Stage A approved ComfyUI connection binding

Atomic Unit: `human-operated-comfy-binding-r0` (2026-09-29 JST).
Owner explicitly approved Gate 1 in this conversation: add exactly
`src/ai_video_production/task036_trusted_launcher.py` for read-only ComfyUI
connection observation. Earlier pending-approval notes are historical and
superseded for this one binding only. No build/package, auto-start, generation,
download, private/native Product operation or other path authority follows.

Fresh main `7125f1261e763fb3b681e5b8c7a6dff9f11a95dc` was audited. PR #591's
launcher changes affect the PMST bootstrap signature/save guard, disjoint from
this health helper and bridge composition. Those owner changes were not edited
or reverted. No unnecessary main merge/push was done; eventual integration must
retain both changes. Existing seven owned dirty paths remain preserved; the
launcher is the eighth owned dirty path.

The configured image/video local ComfyUI endpoint now supplies the existing
warning bridge with a separate read-only client. Only an explicit snapshot call
performs `GET /system_stats`, with a two-second timeout and 64 KiB response cap.
No connection observation runs while constructing the app. A structurally valid
response yields READY (connection only, not generation admission); known
transport failure yields UNREACHABLE; malformed/HTTP/unknown results remain
UNKNOWN. The existing lifetime guard prevents probes after app closure. No
endpoint, private device detail or execution authority enters the public state.
No configured runtime still means UNKNOWN/NOT_BOUND.

- Final Builder focused regression: `226 PASS / 1 deselected in 23.13s`.
- Independent Tester: `109 PASS / 1 deselected in 16.78s`, exit 0.
- Independent design/implementation/final Critic: `PASS`, C/H/M/L `0/0/0/0`.
- Early test-only failures were repaired: Windows live lease denies byte reads;
  inventory remains checked with only that exact lease excluded from byte reads.
  Invalid bridge args correctly raise ProductError, not ValueError.
- An incorrect test filename caused one collection-only attempt (zero tests).
- Earlier Builder runs included the existing synthetic ffmpeg fixture under
  unique pytest temporary roots; fake ASR/Resolve only, no real Provider/native
  Product action. Final Builder and independent runs exclude that fixture test.
- Judge accepts only this bounded source/test binding. Real ComfyUI observation,
  human GUI and packaged model-to-export remain `NOT_EXECUTED / NOT_CONFIRMED`.
- No commit/push or CI restart; HEAD CI does not cover this uncommitted delta.
- External checkpoint: `TASK-036/human-operated-comfy-binding-r0/20260929T125628+0900/checkpoint.md`.

Gate 1 is no longer awaiting approval. Next is the independent authorized B
planning/scene source audit in the fixed order. Package/native human acceptance,
cross-owner writes and all other existing Gates remain unchanged. Keep the
quiet ACTIVE heartbeat; do not ask again for the granted one-path approval.

## Stage B exact Planning selection correction

Atomic Unit: `human-operated-planning-selection-r0` (2026-09-29 JST).
The independent no-effect source audit found a Medium UI mismatch: after a
second Proposal was generated, an ID-less reread selected the lexicographically
first old Proposal and its Scenes instead of the exact generated result.
Audit checkpoint: `TASK-036/human-operated-planning-scene-audit-r0/20260929T131201+0900/checkpoint.md`.

This correction is bound to the Owner's existing sequential implementation
lane and existing allowed UI/test paths: `task036_shell_v611.py` and
`test_task036_v611_interaction_contract.py`, plus this order record. No canonical
Planning/Project owner or general launcher change is included. Fresh main is
`7125f1261e763fb3b681e5b8c7a6dff9f11a95dc`; PR #569 remains CLEAN with HEAD CI
9/9 PASS and no reviews/comments. New PR #593 changes TASK-041 current audio
review owner reads, not these B paths; it is a future audio dependency candidate,
not current Export gate admission or authority.

Generation success now rereads the exact returned Proposal ID. Ordinary refresh
keeps the current session selection. When multiple canonical Proposals exist,
an accessible selector lets the user reopen a saved Proposal and its Scenes.
Selection uses the existing ID-selecting read-only bridge and creates neither
another canonical store nor browser-side persisted authority. GO/revision and
Scene actions use that same snapshot. Cancellation and failed prepare/apply
retain input and selection; selection itself does not invoke generation.

- Builder new Node fake-bridge test: `1 PASS / 39 deselected in 1.17s`.
- Builder seven-module UI/Export/canonical Planning regression: `186 PASS in 15.29s`.
- Independent Tester six-module UI/canonical Planning regression: `165 PASS in 14.02s`;
  no warnings/skips. Stub adapters only, no real Provider/native/ffmpeg execution.
- Independent design and implementation Critic: `ACCEPT`, C/H/M/L `0/0/0/0`;
  original Medium resolved in source.
- One initial test invocation had a PowerShell pytest-cache argument parsing
  error and collected no tests. A new unique contained root was used after repair.
- Diff whitespace and scope checks: `PASS`; existing element/visual contracts pass.
- Judge accepts this bounded source/test unit only. Reopen tests use canonical
  fixtures/fake bridge, not a person operating a rebuilt Product package.
- External checkpoint: `TASK-036/human-operated-planning-selection-r0/20260929T132342+0900/checkpoint.md`.
- Eight dirty paths remain owned; no commit, push, main merge or CI restart.

B as a complete Human stage is still `NOT_EXECUTED / NOT_CONFIRMED`. Keep the
ordinary package/native effect parked, preserve the fixed order, and continue
remaining independently authorized no-effect B dependency checks before routing
to C. Do not substitute TASK-049 packages, replay Provider calls, bypass rights/
consent, or manufacture an Export owner PASS from PR #593 or source tests.

## Stage C queue runtime-check interaction correction

Atomic Unit: `human-operated-generation-readiness-r0` (2026-09-29 JST).
Owner explicitly requested continued implementation after monitoring stalled.
Fresh main is `6a2991a6ad4df55c299faa467ea7dadc8f1c5b55`; PR #569 is CLEAN,
HEAD CI 9/9 PASS, with no review/comments or active locks. The eight owned dirty
paths and earlier Evidence hashes remain unchanged at intake. Main PR #594 adds
TASK-026 current placement reads without directly overlapping this unit. Those
owner changes do not mint Audio Completion or authorize cross-owner writes.

B's existing exact Proposal/GO/install/Scene finalization bindings were reread;
its human/package effect stays parked, not completed. Continue the next
independent no-effect C interaction unit in the fixed order. Allowed delta:
`task036_shell_v611.py`, `test_task036_v611_interaction_contract.py`, and this
order record only. Preserve all previous dirty changes and canonical owners.

Independent source Critic confirmed one Medium: a repeated Runtime check clears
session readiness but only redraws on PASS, leaving a previously enabled
generation control visible after failure. The existing execution guard prevents
dispatch, but the ordinary operation presents stale availability.

DEV-4 design review accepts immediate invalidation/redraw, per-entry busy and
single-flight state, refresh-invalidated request tokens, and truthful failure
copy. Reuse the existing queue-scoped TASK-013 read-only preflight and separate
Human prepare/apply confirmation. No new generation permission, store or owner
reader is added. Required verification is fake-bridge Node operation coverage,
focused existing UI/queue regression, independent Tester and implementation
Critic, diff/scope check and external checkpoint read-back. Real runtime,
Provider, media, ffmpeg, native/package/build, Release and Deploy are not run.
Design residual findings C/H/M/L: `0/0/0/0`. This is source/UI work only;
human model-to-export completion remains `NOT_EXECUTED / NOT_CONFIRMED`.

### Stage C readiness verification

- Before implementation, the new fake-bridge Node test reproduced stale enabled
  controls: `1 FAIL / 40 deselected in 3.12s` (expected red).
- New test after the first implementation: `1 PASS / 40 deselected in 2.45s`.
- Builder first seven-module regression: `170 PASS in 19.29s`.
- Independent Tester first five-module regression: `139 PASS in 16.07s`.
- Implementation Critic found one additional Medium during Queue refresh await;
  the bounded fix removes old controls immediately and invalidates both session
  maps again before drawing the fresh snapshot. The Node test covers that order.
- Builder final seven-module regression: `170 PASS in 17.44s`, exit 0.
- Independent Tester final five-module regression: `139 PASS in 13.91s`, exit 0,
  no warning/skip. All runtime/dispatch dependencies are fakes.
- Final independent Critic fix-delta: `ACCEPT`, C/H/M/L `0/0/0/0`.
- Diff/scope check: PASS; only the three bound paths changed in this unit.
- Judge accepts this source/UI checkpoint, not C whole-stage or native closure.
- No real Provider/runtime/network/native/ffmpeg/build/package, commit, push,
  main merge or CI restart. HEAD CI remains separate from this dirty delta.
- External checkpoint: `TASK-036/human-operated-generation-readiness-r0/20260929T175150+0900/checkpoint.md`.

Next independent C unit: refresh Visual lineage after output adoption/recovery
so the current page reflects the new canonical receipt and offers the existing
Asset Review navigation. Inspect the exact existing apply result and preserve
separate Human ACCEPT/LOCK; do not reexecute a Provider or write another owner's
source. Bind the minimal allowed UI/test delta and use fake-bridge verification
plus required independent review. Do not fall back to monitoring-only while
this authorized candidate remains safely actionable. Human/package gates stay
parked; further path/effect authority still requires Owner approval.

## Stage C output adoption to existing Asset Review

Atomic Unit: `human-operated-adoption-handoff-r0` (2026-09-29 JST).
Bound to the standing Owner sequential lane and the existing three paths:
`task036_shell_v611.py`, `test_task036_v611_interaction_contract.py`, this record.
Fresh main `1d9f4a471ea8540a9fb2df19a0e2cd933e8374e2`; HEAD remains `03e2e18`,
PR569 CLEAN 9/9, reviews/comments and active locks zero. Eight owned dirty paths
are preserved. No main merge, push or CI restart is required.

Existing adoption/recovery returns its canonical snapshot and latest_adoptions.
The page previously reread only the Queue, leaving Visual lineage and its
existing Asset Review navigation stale until revisit. After the existing
explicit confirmation and apply/recovery, the Queue still reloads (including
partial-failure recovery). Only an exact READY_FOR_AUDIT execution/candidate,
and exact adoption ID for recovery, triggers one read-only Visual projection
read and renders its same snapshot to Image/Video panels. Existing navigation
still requires a Human click; READY_FOR_AUDIT never implies ACCEPT/LOCK.

DEV-4 independent design Critic accepts C/H/M/L `0/0/0/0`. Verification requires
Node fake-bridge happy-path/navigation, cancellation/failure/non-READY/mismatched
ID coverage, focused regression, independent Tester/implementation Critic,
scope check and external Evidence readback before this unit is complete.
No new canonical store, source owner write or general launcher change. No real
Provider/runtime/network/media/ffmpeg/native/build/package effects. Human GUI
and model-to-export packaged completion remain NOT_EXECUTED / NOT_CONFIRMED.

### Stage C adoption handoff verification

- Builder extracted-function Node contract: `1 PASS / 41 deselected in 2.88s`.
- Builder seven-module focused regression: `160 PASS in 21.21s`, exit 0.
- Independent Tester five-module UI/Adoption/Visual regression: `129 PASS in
  17.24s`, exit 0, no warnings/skips; fake ports/synthetic bytes only.
- Independent design and implementation Critic: ACCEPT, C/H/M/L `0/0/0/0`.
- Diff/scope check: PASS. Judge accepts this bounded source/UI unit only.
- Initial sandbox Temp-root creation was denied; zero tests and no output root
  created. A new unique contained root was approved before any test process ran.
- Read-only worktree policy was preserved: apply_patch edited exact copies in
  the authorized visualization run; approved transfer checked prior owned hashes,
  HEAD and exact target containment, then read back matching resulting hashes.
- External checkpoint: `TASK-036/human-operated-adoption-handoff-r0/20260929T181000+0900/checkpoint.md`.
- No commit/push/main merge/CI restart or real Provider/runtime/native/ffmpeg.
  Existing eight dirty paths remain owned. HEAD CI is not dirty-delta CI.

Next independent C slice is the existing Asset Review Human decision and
save/reopen binding source audit. Inspect exact current Candidate/Audit owner
contracts and normal UI identity handling; use no-effect fake-port tests if a
bounded allowed UI correction is needed. Do not perform an actual Human decision
or canonical owner write, and do not claim Human/package completion from tests.
Then evaluate remaining C audio dependencies with fresh current owner reads;
only independently authorized safe work may proceed. Keep all other Gates.

## Stage C Asset Review immutable Audit dependency

Atomic Unit: `human-operated-asset-review-audit-r0` (2026-09-29 JST).
Standing Owner lane; allowed v611 Shell, interaction test and this record only.
DEV-4 independent design Critic ACCEPT, C/H/M/L 0/0/0/0.

Independent no-effect source audit found one functional Medium: newly adopted
READY_FOR_AUDIT Candidates have no immutable Audit yet. TASK-038 deliberately
requires that Audit before exposing Human decision actions. The canonical
`record_audit` and TASK-013 `record_visual_compliance` APIs exist, but the ordinary
Shell has no Audit input bridge. Adoption itself must not fabricate that record.
This is conditional source evidence, not a GUI reproduction. The finding remains
OPEN / effect PARKED, not fixed by a status message or tests.

This bounded UI correction explicitly explains the missing Audit/input binding
for READY_FOR_AUDIT candidates with Audit count zero outside recovery. No action,
bridge, default score, bypass, auto-ACCEPT/LOCK or canonical store is added.
Existing audited candidates retain exact Candidate/hash confirmation and separate
Human decision/save/reopen. Fake-port validation and independent review follow.

Owner admission needed only for the immutable Audit input write effect: connect
the existing TASK-038 API through `task036_shell_ui.py` and the ordinary v611 UI,
with explicit Human input/confirmation, exact Candidate/asset and both snapshot
hashes. No canonical owner modification or Provider/native execution is implied.
Pending admission, continue remaining C current audio dependency source reads.
Human GUI/package/model-to-export completion remains NOT_EXECUTED/NOT_CONFIRMED.

### Remaining C audio dependency routing (current source, no effects)

At main `1d9f4a47`, TASK-041 media review now has the sealed owner
`AudioMediaReviewHistoryStore.read_current`, and TASK-026 has sealed
`Task026AudioPlacementApplication.read_current_compilation`. These supersede
the two corresponding missing-read claims in the earlier R2 readiness record;
their existence alone is neither AUDIO_COMPLETION nor an Export Gate PASS.
PR596 was pending at initial audit, then merged during verification. Recovery
fresh checks confirm main `a51d3b625d2106702f35b56e80751352f09e0659` now supplies
the sealed TASK-035 round-trip current read. Its eight paths do not directly
overlap this unit. Keep that owner source intact; do not merge/push just for CI.
TASK-014 NarrationPublicationReceipt and the TASK-036 typed audio-completion
wrapper remain missing in current main. Do not manufacture either from schemas,
public receipt constructors, stale evidence or tests. These owner dependencies
and any additional path/effect must be separately admitted before binding.
The exact immutable Audit input effect is the immediate ordinary-flow blocker;
this audit does not skip C or start D/E, Provider, Voice or native effects.

### Asset Review audit verification checkpoint

- Existing-source independent Node audit: 16 fake scenarios PASS.
- Persistent extracted-function regression: independent Tester 1 pytest PASS,
  19 fake scenarios PASS in 1.26s; one harmless cache-disabled/config warning.
- Builder actual-worktree four-module UI regression: 123 PASS in 27.57s, exit 0.
- Independent design/source/test Critic: ACCEPT, C/H/M/L 0/0/0/0 for this
  explanation-and-test unit; functional Audit input Medium remains OPEN/PARKED.
- Original interaction test content was proved fully preserved after removing
  only the new 155-line insertion; additions 155, deletions zero. Transfer was
  initially refused on a removal concern, then approved with that additional
  read-only proof and exact HEAD/owned hash/containment/readback checks.
- Judge accepts the bounded UI unit, not Human save/reopen or C completion.
- External checkpoint: `TASK-036/human-operated-asset-review-audit-r0/20260929T183000+0900/checkpoint.md`.
- Eight owned dirty paths stay uncommitted. No main merge/push/CI restart,
  Provider/runtime/network/native/media/ffmpeg/build/package execution.
- During verification PR569 received issue comment 5887352544; its actual body
  is incomplete (`PR統合監査（exact head: `). It provides no actionable exact-head
  review or new authority. Fresh PR remains OPEN/CLEAN, 9/9 PASS, reviews zero,
  issue comments one, review comments zero. PR597 changes only two TASK-100 docs.

Next admitted implementation must connect immutable Audit input, not relax the
Audit prerequisite. Ask once for that specific existing Shell/bridge write effect.
No new canonical owner file or Provider/native effect is implied. While waiting,
reassess only independently authorized C candidates/current owner dependency
changes; do not describe this source checkpoint as integrated-app completion.

## 2026-10-10 current-main rebind continuation

The Owner directed independent existing changes to proceed beyond an audit-only
checkpoint. Original worktree 130a and its eight owned dirty files remain intact.
A separate managed candidate, `codex/task-036-comfy-main-rebind-r0`, starts at
main `53e4f0ea8e219b773a2976ba40b956830ff2e1df` and preserves its PMST-R011
bootstrap guard and routed save. No merged PR was reopened or pushed.

Serial source-only checkpoints, each externally persisted and read back:

- Comfy read-only binding: Builder18 PASS, independent140 PASS, Critic0/0/0/0.
- A settings/runtime-warning UI: Builder3 PASS, independent106 PASS, Critic0/0/0/0.
- B exact Proposal selection: Builder1 PASS, independent107 PASS, Critic0/0/0/0.
- C readiness/adoption/Audit explanation: Builder3 PASS, independent125 PASS /
  1 explicit symlink-case deselection, Critic0/0/0/0.
- Existing Export availability truthfulness: Builder26 PASS; final aggregate
  independent159 PASS in38.48s (four baseline plus three PMST modules), no exclusions.
  Independent aggregate source/document review C/H/M/L0/0/0/0; commit-ready only,
  without new Export execution authority. Initial missing-helper failure was an
  unapplied UI patch, recorded separately and corrected before the final run.

These are rebindings of previously owned changes, not new canonical owner APIs.
Source unit PASS never means Human model-to-export, actual Comfy connectivity or
packaged completion. Immutable Audit input remains OPEN/PARKED; TASK-014 narration
receipt and the typed audio wrapper remain unbound. Provider/native/build/package,
Voice/private media, Resolve, Release/Deploy/Production and Human decisions remain
outside this work. Commit/push/new PR are not performed by this continuation.

External checkpoints are under the canonical TASK-036 Evidence root, respectively
`human-operated-comfy-main-rebind-r0/20261010T091000+0900`,
`human-operated-settings-main-rebind-r0/20261010T092000+0900`,
`human-operated-planning-main-rebind-r0/20261010T093000+0900`, and
`human-operated-c-main-rebind-r0/20261010T094000+0900`. Final aggregate Evidence:
`human-operated-export-main-rebind-r0/20261010T095000+0900`.
Original snapshots are in the first checkpoint's `original-130a/`; each later unit
retains its candidate file snapshots. No cleanup/archive is authorized or performed.

## 2026-10-11 post-TASK-110 exact8 publication continuation

The Owner's recommended-order execution instruction admits this existing eight-path
source-only reconciliation, focused tests, independent review, external Evidence,
normal commit/push and a Japanese PR. This supersedes only the previous publication
hold, not the Human/native/Provider or canonical-owner gates. Main integration is
handed to the existing serial integration owner after PR checks.

- Bound base/main: `d88866b3343db7f748cc058fdc3c3b9f1e1d501e`; eight current-main
  CI checks PASS, zero open PRs and zero active work locks at pre-publication read.
- Original 130a remains at `03e2e18b57503d630dbd5260183c96891e498adb`; all eight
  original file hashes still match the preserved snapshots. Pre-reconcile candidate
  copies and the safety stash are retained; no reset, cleanup or discard occurred.
- Existing candidate was advanced by fast-forward and its exact eight changes
  reapplied. The two conflicts preserve main's Planning single-flight, public-safe
  errors and final refresh; modal scrolling, dialog and scoped settings-save fixes;
  and the candidate's exact Proposal selection, runtime warnings and handoff.
- Raw model-ID supplementation is ASCII-only and filtered; non-ASCII or unsafe IDs
  use the public display label. This preserves TASK-110's protection, including the
  Unicode casefold edge (`long-s` secret spelling) found by independent Critic.
- Builder: 228 PASS in 28.01s before the final Unicode guard tightening. Final
  independent Tester: 264 PASS, zero skips/failures, in 65.87s across nine modules
  (the four UI/Export modules, three PMST modules, Shell UI and Planning generation).
  Final source Critic: PASS, C/H/M/L 0/0/0/0. Diff/scope checks PASS.
- A first four-module run had 127 PASS / 1 FAIL because the extracted-function
  fixture lacked runtime-warning helpers; the fixture was repaired without dropping
  assertions. A later execution was denied before launch until the actual newer
  Owner instruction was read back and presented for re-review. These are not PASS
  runs. Final tests use fake ports/Node and isolated OS-temp roots only.
- Judge accepts source-only publication readiness, not Human model-to-export
  completion. Immutable Audit input is still absent and requires its separately
  allocated new Task; narration receipt/typed audio completion remains a dependency.

External Evidence: `TASK-036/human-operated-post110-reconcile-r0/20261011T134000+0900/`.
Its checkpoint records exact hashes, independent Role outcomes, output roots and
readback. No actual Provider, Comfy runtime, private media, native Product, build,
package, model acquisition, Human ACCEPT/LOCK, Release/Deploy/Production or cleanup
was executed. TASK-036 overall and packaged/Human acceptance remain incomplete.
