# P-UX-1C Start / End feasibility closure

Date: 2026-08-16
Atomic unit: `START_END_FEASIBILITY_R0`

## Design and Critic

The V6.1.1 Start / End page currently renders the Generation Safety snapshot
as generic JSON, while the released Shell already owns the exact structured
Human review interaction for `Task013GenerationSafetyApplication`.

Reuse the approved implementation: expose review only for a current
Human-approved Plan, collect the exact reference specification and twelve Human
checks, and prepare/apply the immutable Feasibility record against both current
Planning and Safety checksums. A current record may be re-reviewed append-only;
stale records remain counted.

Builder Critic: a simplified PASS button would omit reference roles and
geometry constraints. Correction: collect the exact schema field set and all
Human checks. Security Critic: the page name could imply image generation.
Correction: the operation persists Feasibility only and explicitly starts no
Provider, paid operation, Candidate generation, Human ACCEPT or NLE mutation.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- Review actions appear only for a current Human-approved Plan.
- The exact reference-spec fields, twelve Human checks, blocking reasons and
  reviewer are prepared against current Planning/Safety checksums.
- Apply consumes only the one-shot confirmation returned by the Application.
- Current and stale records remain separately visible per Scene.
- No Provider, paid, Candidate, Human ACCEPT or NLE execution path was added.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `177 passed`.
- Full regression: `1246 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
