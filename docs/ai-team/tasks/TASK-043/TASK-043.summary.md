# TASK-043 Summary

- Name: Unified Product Project / Migration / Recovery Foundation
- Priority: `OWNER_MAXIMUM / MAJOR_REFACTOR_FOUNDATION`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Current Phase: `P-FND-1 PROJECT MANIFEST / COMPATIBILITY / MIGRATION PLAN`
- Current Gate: `LOCAL_SMOKE_PASS / HOSTED_PENDING`
- Implementation: `P-FND-1 LOCAL COMPLETE / P-FND-2..4 NOT STARTED`
- Current main baseline: `b7500fa4f7cb4339ddde6aa4800d56c9bcb4d94e`
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

Roadmap/design PR #62 passed hosted `9 / 9` and merged at exact main
`b7500fa4f7cb4339ddde6aa4800d56c9bcb4d94e`; its remote/local design branch
cleanup passed. Fresh-main implementation added P-FND-1 Project Manifest,
compatibility inspection and read-only migration planning. WSL2 compile/schema/
smoke passed; hosted full regression is pending. No migration apply, Project data
mutation outside the new manifest fixture, Provider/native operation or release
was performed.

