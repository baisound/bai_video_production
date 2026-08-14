# TASK-042 — P-V6-1B Implementation Validation and Critic Evidence

## Baseline and authority

- Product Authority: `BAI VIDEO PRODUCTION`
- Fresh implementation baseline: `cbf27b29ddab08050df4804c160501ff4586bb11`
- Branch: `codex/task-042-p-v6-1b-implementation`
- BAI Development OS Queue: `BVP-TASK-042-P-V6-1B / IMPLEMENTATION`
- Queue checksum: `sha256:6a44e3fee803b247d899278c8ad137a024a8f5aebd3b090022b4333eb4cc2f95`
- Design closure: PR #52 head `f3d99fe07a74974d0e95a925f1c72b67054e86f3`, hosted `9 / 9`, exact main above

## Implemented result

1. `ProductionProposalRevision` accepts only the exact Blueprint v1/v2 union.
2. Snapshot rehydration uses the public closed-schema/checksum parser and round-trips v1/v2 records and Approved Plans.
3. v2 Human GO derives deterministic Scene/frame/role paths and requires exact Asset ID/checksum identity for every path.
4. Approved Plan identity verification accepts v2, while Production Control and Generation admission fail closed with `ERR_BLUEPRINT_V2_PRODUCTION_CONTROL_NOT_INTEGRATED` until P-V6-2.
5. `build-windows-exe.bat` reuses `packaging/task036_shell.spec`, chooses `BVP_BUILD_PYTHON`/`.venv`/PATH in order, validates dependencies and never installs them silently.
6. `builds/.gitkeep` preserves the requested output directory while generated content stays ignored.
7. `docs/windows/BUILDING-WINDOWS-EXE.md` and the Installation-adjacent README section document setup, output, verification, cleanup and boundaries.
8. README explains AUTONOMY in plain language from Repository open through Queue exhaustion, minimal Context loading, non-bypassable Gates, Session Rotation and the standard start prompt. Ten examples cover ordinary two-merge, Human Gate parking, Windows build, continue-all, Design-Ahead, single-Task, non-system blocking, conversation-free handoff, new-requirement roadmap intake and overnight checkpoints.

## Validation

- Focused v1/v2 Proposal/GO/snapshot/build/orchestration: `26 / 26 PASS`
- Full Windows regression: `946 / 946 PASS`, one intentional non-Windows-contract skip
- Existing v1 focused Proposal/Approved Plan/snapshot behavior: included in focused PASS
- Batch `--help`: side-effect-free PASS on Windows
- Actual one-dir build: `PASS` on Windows 11 / Python `3.12.4` / PyInstaller `6.22.0`
- Expected EXE: present, `10,600,412` bytes, SHA-256 `85a127c3e390b99bb896fd6f3ed7271b38c39beeeeb7c3ae5caf011334449f23`
- Generated EXE/work files: `git check-ignore` PASS; no build output is staged
- Hosted CI: pending
- Exact main merge/cleanup: pending

## Critic review

### Cycle 1

1. `CRITICAL / CLOSED`: v2 Human GO could be read as current Candidate LOCK. Production Control and Generation remain explicitly P-V6-2-blocked.
2. `HIGH / CLOSED`: v1 snapshot reconstruction could drift after parser replacement. Existing v1 focused tests and full regression pass unchanged.
3. `HIGH / CLOSED`: repeated frame references could collide. Deterministic Scene/frame/role/index paths and exact identity comparison are tested.
4. `HIGH / CLOSED`: build convenience could mutate the environment silently. The batch only diagnoses missing modules and prints the explicit operator command.

### Cycle 2

1. `HIGH / CLOSED`: generated EXE files might be staged. `/builds/*` is ignored while only `.gitkeep` is retained.
2. `HIGH / CLOSED`: AUTONOMY could be mistaken for Product runtime self-operation. README states it is development governance and grants no external authority.
3. `MEDIUM / CLOSED`: build success could imply release readiness. Documentation states that local unsigned build is not Tag, Release or Deploy.
4. `MEDIUM / CLOSED`: cadence could continue directly into P-V6-2. Canonicals require AUTONOMY reselection after this second exact main merge and cleanup.

Result: `CRITIC_PASS_AFTER_TWO_FIX_CYCLES`; unresolved Critical/High `0 / 0`.

## Current claim boundary

`P_V6_1B_IMPLEMENTATION_LOCAL_PASS / HOSTED_PENDING`

No Blueprint v2 WORLD LOCK/Candidate current-state verification, v2 Production Control installation, Provider dispatch, native generation, paid operation, Resolve/Cubase write, Production Activation, package version, Tag, Release or Deploy is claimed.
