# TASK-098 A4-R1 Ephemeral Exact-Hash Coordinator Design

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A4-R1 DESIGN`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Starting HEAD: `080986c7d1a258c64d527aeece0101b6ea660be3`
- Base/current-main identity: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Branch: `codex/task-098-a4-review-workspace`
- Result: `DESIGN_ACCEPTED / A4-R1A_IMPLEMENTATION_ALLOCATED`

## Capability routing

- High-Reasoning: canonical TASK-041/TASK-006 ownership, exact-hash boundary,
  timing/lineage non-claims, Critic and final integration review.
- Implementation: immutable coordinator and focused deterministic tests.
- Bulk/Mechanical: additional negative fixtures, documentation synchronization,
  Evidence and diff/scope checks.

Cost/context optimization may not weaken DEV-3 tests or the no-body/no-effect
boundary.

## Goal and ownership

A4-R1a may create one in-memory Review ViewModel that binds:

- one exact TASK-041 policy/source/capability/intent set;
- one canonical `TranscriptManifest` digest;
- one exact `SubtitleWorkspace` ID/revision/snapshot digest; and
- the A4-R0 immutable viewport and time projections.

TASK-041 keeps Asset/Candidate/source/capability/intent ownership. TASK-006
keeps Transcript timing and Subtitle Workspace text/revision/CAS ownership.
TASK-098 owns only the ephemeral join and body-free timing references.

## Admission and exact identity

Opening succeeds only when:

1. TASK-041 admission is exactly `READY_FOR_HUMAN_REVIEW`;
2. source is `BOUND_VERIFIED`, rights `PASS`, sample rate exactly 48 kHz and
   duration/range valid;
3. Transcript `source_asset_id` equals the TASK-041 `asset_id`;
4. caller-supplied Transcript digest equals `TranscriptManifest.to_dict()`;
5. caller-supplied Subtitle Workspace snapshot digest equals canonical JSON of
   its exact ID, revision and cues;
6. projected Transcript/Subtitle ranges fit the TASK-041 source duration; and
7. row counts are bounded before materialization.

Failure exposes closed reason codes only. It returns no partial ViewModel,
private identifiers, text, path, media bytes or exception body.

## ViewModel boundary

The frozen ViewModel may retain exact private digests/IDs and body-free rows:

- transcript segment ID plus original microsecond range and projected samples;
- subtitle cue ID plus original millisecond range and projected samples;
- source/intent/transcript/workspace identities;
- immutable A4-R0 viewport.

It must not retain segment/cue text, raw text, media/audio bytes, a source path,
receipt body, credentials, Provider/model objects, file handles or store/service
objects. It has no serializer or persistence method.

`SubtitleWorkspace` currently has no canonical persisted field that proves it
was derived from the supplied Transcript. A4-R1a therefore fixes
`workspace_transcript_lineage_confirmed=false`. The exact session join is not a
canonical provenance claim. A later owner Task may add such lineage; A4-R1a
must not invent it.

## Effects and later units

A4-R1a performs no filesystem/media read, playback, waveform render, Provider,
model, network, text mutation, Subtitle Workspace save/CAS, Human decision,
Asset/placement mutation or Product UI action.

- A4-R1a: pure in-memory coordinator and tests.
- A4-R1b: fresh review for unified Product/Shell projection.
- A4-R2: fresh review for injected external playback/waveform runtime and native
  acceptance. Selection of the Owner voice model does not authorize these
  review-workspace effects.

## A4-R1a Allowed Files

- `src/ai_video_production/task098_review_workspace_coordinator.py`
- `tests/test_task098_review_workspace_coordinator.py`
- bounded TASK-098 design/task/Evidence/current-state/task-index documentation

TASK-006/TASK-041 source/schema/test, Shell/UI, stores, providers, dependencies,
models, media, package/installer and Product version must not change.

## Acceptance

- exact ready inputs produce an immutable body-free ViewModel;
- every hash/source/rate/right/admission/range/count mismatch fails closed;
- no partial rows appear on failure;
- transcript and subtitle timing retain original units and use A4-R0 projection;
- exact workspace revision/snapshot drift is rejected;
- no text/path/body field is present and lineage-confirmed is fixed false;
- waveform and segment scrolling remain independent after coordinator wrapping;
- direct A4/TASK-041/TASK-006 plus relevant TASK-098 regression passes;
- compile, diff/scope, privacy scan and durable Evidence read-back pass.

## Critic / Tester / Judge

- High: hashing a Subtitle Workspace snapshot could be misreported as canonical
  Transcript lineage. Corrected with a fixed-false lineage claim.
- High: admission-ready could be misread as completed playback/waveform review.
  Corrected by keeping A4-R0 completion separate and adding no receipt result.
- High: retaining canonical objects would retain text bodies indirectly.
  Corrected to body-free copied IDs/ranges/digests only.
- High: errors or partial rows could expose private coordinates. Corrected to
  closed codes and all-or-nothing construction.
- Medium: unbounded segment/cue materialization could exhaust memory. Corrected
  by pre-materialization count limits.
- Medium: time projection could rewrite canonical timing. Corrected by retaining
  source units and using one-way A4-R0 projection.
- Final findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Tester: `PASS / IMPLEMENTATION_TEST_PLAN_ACCEPTED`.
- Judge: `ACCEPT / A4-R1A_IMPLEMENTATION_ALLOCATED`.
