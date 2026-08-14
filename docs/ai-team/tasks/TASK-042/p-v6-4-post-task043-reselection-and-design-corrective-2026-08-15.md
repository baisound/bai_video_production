# TASK-042 — P-V6-4 Post-TASK-043 Reselection and Design Corrective

## Source of Truth and Queue decision

- Owner Directive: `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE`
- Implementation baseline: exact hosted main `10eae32b2e6a2f9ad7080961fed7b3d2b39f423b`
- TASK-043 P-FND-4: PR #66 passed `9 / 9`, merged at the baseline above, and branch cleanup passed
- Queue unit: `BVP-TASK-042-P-V6-4-IMPLEMENTATION / IMPLEMENTATION`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Handoff decision: the current checkout is newer than the P-V6-4 Design PR #61 baseline and is Implementation Source of Truth

The protected checkout `D:\BAI\bvp-task042-p-v6-4-autonomy` contains two
untracked, unverified prototype files. Their SHA-256 values are recorded as
`138f5e3a7d49c792f685df20027a276999664d0427314f347e0ec8b3874eb618` and
`11223aeca3ce8fb1d43d0ac7ccdb5afd33f15a00e9fe02933256fd33a6790cb1`.
They are preserved without modification and are not canonical implementation.

## TASK-043 corrective

The hosted Design remains valid except for standalone Timeline persistence.
TASK-043 now owns the aggregate Product Project save/recovery boundary. Therefore:

1. Timeline Audio is a `TASK-042` child document at
   `state/timeline-audio.json`, identified by
   `bai-video-production.timeline-audio-history / 1.0.0`.
2. Timeline history and its updated Project Manifest commit through
   `ProductProjectSaveCoordinator`; direct independent Timeline save is not a
   second canonical write path.
3. Every open/apply revalidates Project ID, Manifest checksum, child checksum,
   timebase and exact Blueprint dependency checksum.
4. Existing Product children are retained. Removal still requires explicit
   migration authority.

## Corrected Builder design

- Frame ranges are integer, end-exclusive and Blueprint frames remain authority.
- Master SRT is proposal-only. Floor/ceil conversion records rounding delta;
  missing Scene, boundary crossing, Timeline overflow and global narration-lane
  overlap are explicit conflicts.
- BGM, SE, NARRATION and AMBIENCE are first-class roles. Exact TASK-037 SlotKind,
  locked Candidate, Asset ID and Asset checksum are checked at prepare time.
- Whole-Timeline music must exactly cover frame `0..target_duration_frames`.
- Timeline revision history is append-only and exact-hash chained.
- TASK-041 placement can carry an exact current Timeline item proof while old
  serialized placements remain readable without that optional field.
- Current proof compilation reuses TASK-026. STRETCH is fail-closed as unsupported;
  fade/gain remain visible and TASK-010 compatibility reports the gap rather than
  silently dropping it.
- Text bodies, media bytes, Provider dispatch, paid execution, Candidate mutation,
  Resolve and Cubase mutation remain absent/false.

## Allowed Files

- `src/ai_video_production/timeline_audio*.py`
- bounded AMBIENCE and Timeline-binding integration in
  `production_control.py`, `audio_workspace*.py`, `audio_placement.py`, package exports
- public and packaged `timeline-audio.schema.json`
- focused TASK-042 and compatibility tests
- `docs/ai-team/tasks/TASK-042/**`, `docs/ai-team/current-state.md`,
  `docs/ai-team/task-index.md`, `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`,
  `PROJECT.md`, `CHANGELOG.md`

No Shell/UI, Provider adapter, credential, generated media, native application,
version, Tag, Release or Deploy file is allowed in this unit.

## Critic / Judge

Cycle 1 closed one Critical and four High findings: independent child save,
Blueprint/timebase staleness, ambiguous Slot-role inference, arbitrary URI/path
references and global narration overlap. Cycle 2 closed three High findings:
boolean-as-integer acceptance, whole-Timeline under-coverage and silent
STRETCH/fade degradation.

Judge decision: `IMPLEMENTATION_AUTHORIZED`. Unresolved Critical/High: `0 / 0`.

