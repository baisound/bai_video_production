# TASK-042 — P-V6-1B AUTONOMY, Current-main Audit and Builder Design

## Current-main and AUTONOMY decision

- Product Authority: `BAI VIDEO PRODUCTION`
- Fresh baseline: `99d21a5542b0ab10b8ce4f1e5a0eea879cffc2eb`
- Open Pull Requests at start: `0`
- P-V6-1A: `HOSTED_CLOSED`
- Owner cadence trigger: exact main merges PR #50 and PR #51
- BAI Development OS Queue result: `RUNNABLE_TASK_SELECTED`
- Selected: `BVP-TASK-042-P-V6-1B / DESIGN_ONLY`
- Queue checksum: `sha256:864c16ec84daa711e2c9c28d2bb7b236415f727435bbbf550425b8c2379ffce5`
- TASK-013 Native H3: `PARKED / NO_REPLAY`

AUTONOMY is development governance, not a BVP runtime dependency and not permission to invoke Provider/native/paid operations. After this design PR merges it counts as merge `1 / 2`. The following implementation PR counts as merge `2 / 2`; after its cleanup, control returns to AUTONOMY before selecting P-V6-2.

## Audit findings

1. `ProductionProposalRevision` and `ProductionProposalSnapshotStore` currently reconstruct only `ProductionBlueprint 1.0.0` even though P-V6-1A provides an exact v1/v2 parser.
2. `ProductionGoApprovalService` currently derives required GO bindings from the v1 top-level reference registry.
3. `ApprovedPlanVerifier` accepts only v1 types, and downstream Production Control compilation understands v1 Scene-level references only.
4. Existing Proposal and Approved Plan records already bind exact Proposal/Blueprint hashes and retain provider/Resolve/publish false boundaries.
5. Existing `packaging/task036_shell.spec` is the authoritative, previously native-validated one-dir Windows package definition. A second spec or application must not be created.
6. Root `.gitignore` ignores `build/` and `dist/` but not the Owner-requested `builds/` output.
7. No general root build batch or Windows client build guide exists. README Installation has no EXE build instructions.

## Work package A — Blueprint v2 Proposal/GO/snapshot

- Widen Proposal type annotations to the exact union `ProductionBlueprint | ProductionBlueprintV2` without changing v1 serialization.
- Replace the private v1-only snapshot parser with `parse_production_blueprint_document()`. Both versions receive closed-schema and checksum validation.
- For v1, preserve current GO binding semantics byte-for-byte.
- For v2, derive deterministic binding paths from Scene order and frame role:
  - `{scene_id}:START:CHARACTER:{index}`
  - `{scene_id}:START:SPACE`
  - `{scene_id}:START:COMPOSITION`
  - equivalent END paths.
- Human GO must provide exactly those paths and exact Asset ID/checksum pairs. Candidate/Slot identities remain inside the immutable Blueprint hash; P-V6-2 later verifies their current LOCK state.
- Approved Plan continues to bind Proposal and Blueprint hashes and never grants Provider/Resolve/publish authority.
- `ApprovedPlanVerifier.require_current()` may verify v1 or v2 identity.
- Production Control compile/install and Generation admission reject v2 with an explicit P-V6-2-not-integrated ProductError. This prevents a valid Human GO from bypassing WORLD LOCK/Candidate validation.
- Snapshot save/load/CAS remains crash-safe and must round-trip mixed historical v1 plus new v2 proposals/plans.

## Work package B — Windows EXE build contract

- Reuse `packaging/task036_shell.spec`; do not create another spec or entry point.
- Add root `build-windows-exe.bat`.
- Add optional dependency group `windows-build` with pinned native-validated PyInstaller/pywebview versions and the existing supported FasterWhisper range.
- The batch uses `BVP_BUILD_PYTHON` when set, otherwise repository `.venv`, otherwise `python`; it validates Windows and required modules before building.
- The batch creates `builds/`, uses `builds/work/` for temporary files and `builds/BAI Video Production/` for the one-dir application.
- `.gitignore` ignores generated `builds/*` but retains `builds/.gitkeep`, so the requested directory exists in source.
- The batch never installs packages silently. README/docs provide the explicit installation command and warn that it may use network access.
- Add `docs/windows/BUILDING-WINDOWS-EXE.md` for prerequisites, exact commands, output, EXE smoke verification, safe cleanup and common errors.
- Add a concise `Windows EXE build` section directly after README Installation.

## README AUTONOMY section

Near Governance/Contributing, explain in plain language:

1. AUTONOMY chooses development work; it does not run BVP production operations.
2. Required flow: all-green PR -> main merge -> exact SHA -> branch/clone cleanup -> count merge.
3. After two merges, return to OS Queue, then fresh-clone the selected target.
4. A Human Gate parks only the blocked operation when independent safe work remains.
5. Provide at least three examples: ordinary design/implementation pair, Human Gate parking, and Windows build-contract work.
6. Provide copyable Japanese Codex request examples.

## Recovery and security

- A changed Proposal/Blueprint/snapshot checksum fails closed.
- A v2 binding path with the wrong Asset/checksum or any missing/extra path blocks GO preparation.
- Old v1 snapshots remain readable and byte-stable.
- Build output is local/reproducible Derived data, never Canonical/Evidence and never staged.
- Build does not sign, release, publish, contact a media Provider or mutate a user Project.
- Package install is explicit; no credential is needed or embedded.
