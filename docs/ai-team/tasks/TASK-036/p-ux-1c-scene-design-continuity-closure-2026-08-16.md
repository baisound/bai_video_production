# P-UX-1C Scene Design continuity closure

Date: 2026-08-16
Atomic unit: `SCENE_DESIGN_CONTINUITY_R0`

## Design and Critic

The V6.1.1 Scene Design page currently renders Continuity as generic JSON even
though the released Shell and `Task039ContinuityApplication` already expose the
complete exact bridge contract. Reuse that contract without changing Product
schemas.

Connect Edge registration, locked Start inspection, Soft Continuity Human
approval, STALE propagation and append-only recovery. Every operation consumes
the current Production and Continuity checksums where required; durable and
Human-final steps retain explicit confirmation. DIRECT_CONTINUATION never gains
a Human override.

Builder Critic: porting only the happy path could hide an interrupted
cross-store transaction. Correction: recovery state suppresses new actions and
projects only the application-provided recovery actions. Security Critic:
Continuity repair could be confused with regeneration or deletion. Correction:
the UI states and enforces that neither is started, and no such bridge method is
introduced.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- Edge creation uses exact END→START inputs and both current source checksums.
- Durable registration, inspection, Soft approval, STALE propagation and
  recovery call only the existing allowlisted bridge methods.
- Recovery-required state suppresses new Edge/review actions.
- DIRECT override, Provider execution, regeneration and deletion remain absent.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `175 passed`.
- Full regression: `1244 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
