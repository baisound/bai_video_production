# TASK-043 Summary

- Name: Unified Product Project / Migration / Recovery Foundation
- Priority: `OWNER_MAXIMUM / MAJOR_REFACTOR_FOUNDATION`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Current Phase: `CURRENT-MAIN AUDIT / ROADMAP REBUILD / FULL DESIGN`
- Current Gate: `DESIGN_REVIEW`
- Implementation: `NOT_STARTED`
- Current main baseline: `6784a44e6831daa2b3db8ff85e2abe7b197ba3de`
- Stable release: `v0.20.1`
- Release candidate: `UNDECIDED`; foundation-only checkpoints are not releases
- TASK-013 Native H3: `PARKED / NO_REPLAY`
- TASK-014 paid narration: `PARKED / NO_PAID_EXECUTION`

TASK-043 is the first runnable unit created by the 2026-08-15
`AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE` Owner Directive. It precedes the
remaining Timeline Audio and full Unified Editor work because the current Product
does not yet have a unified versioned Project envelope, general migration path,
durable background-job recovery or generic edit history.

The old P-V6-4 implementation checkout is not implementation truth. Its two
untracked files are protected as `UNVERIFIED` WIP and remain outside this clean
current-main checkout:

- `D:/BAI/bvp-task042-p-v6-4-autonomy/src/ai_video_production/timeline_audio.py`
- `D:/BAI/bvp-task042-p-v6-4-autonomy/src/ai_video_production/timeline_audio_store.py`

They may be salvaged only after the new Project contract is accepted and focused
tests prove compatibility. They must not be deleted or committed implicitly.

