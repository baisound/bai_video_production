# TASK-004 Live Behavioral Evidence — Final Accepted Run

- Date: 2026-08-09
- Package: `0.4.9`
- Result: `PASS / ACCEPTED_FOR_TASK_COMPLETION`
- Returned archive: `task004-live-evidence-behavior(6).zip`

The bounded synthetic probe completed on the target Windows Audacity/OpenVINO runtime. Noise Suppression produced one validated derived AUDIO Asset. Music Separation used the verified Intel no-parameter 2-stem default and produced the complete `instrumental` and `vocals` set. All four database operations completed on their first attempt, all four Manifests are committed, and no failed operation is present.

The run used synthetic inputs only, retained the empty-project safety boundary, and published outputs only after Product-side media/checksum validation. The verified runtime still exposes no scriptable 4-stem selector. That mode remains fail-closed and is not a TASK-004 completion requirement.

Package 0.4.9 corrected the Windows Audacity file argument boundary by using forward-slash paths and by rejecting legacy-Windows-length paths before dispatch. No Audacity/OpenVINO reinstall was required.
