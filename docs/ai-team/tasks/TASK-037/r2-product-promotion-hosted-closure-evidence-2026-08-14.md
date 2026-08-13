# TASK-037 — R2 Product Promotion Hosted Closure Evidence

- Date: `2026-08-14`
- Final decision: `COMPLETE`
- Pull request: `#24` — `https://github.com/baisound/bai_video_production/pull/24`
- Exact PR head: `fa71e046bf9d377d52b1845f70f2c38e21ee373f`
- Hosted checks: `9 / 9 PASS`
- Exact main merge SHA: `045bd7ed53293fd195a4993586d965bc1094ddac`
- Stable release retained: `v0.20.1`
- TASK-037 Tag / Release: `NOT_CREATED_BY_EXACT_DECISION`

## Hosted Gate

The accepted head passed:

- Ubuntu Python 3.11, 3.12 and 3.13;
- Windows Python 3.11, 3.12 and 3.13;
- dependency audit;
- secret scan;
- changelog and version consistency.

The Windows matrix reached and passed Product tests after the CI supply path was corrected to the immutable FFmpeg 8.1.2 package-object URL with exact SHA-256 verification. The final workflow run was `31750493878 / PASS`.

## Completion boundary

TASK-037 is complete. The Product now exposes the accepted Asset Slot/Candidate/LOCK/STALE Foundation through a durable project-scoped Application Service and the unified Desktop `制作管理` workspace. TASK-038 remains the owner of Human ACCEPT/REJECT decisions.

The implementation branch was deleted remotely and locally after exact merge verification. Existing untracked native Evidence was preserved. No package version, annotated Tag or GitHub Release was created because TASK-037 is an R2 checkpoint rather than the selected Product release boundary.

The next Owner-routed unit is TASK-038 Audit Workspace / Candidate Quality Loop. It must start from exact `main` SHA `045bd7ed53293fd195a4993586d965bc1094ddac` on a new dedicated branch and promote the existing Audit Foundation rather than duplicate it.
