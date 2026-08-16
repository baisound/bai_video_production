# P-UX-1C Planning screen closure — design, Critic, and Evidence

Date: 2026-08-16
Task: TASK-036 / P-UX-1C
Atomic unit: `PLANNING_REVIEW_GO_INSTALL_SURFACE_R0`

## Source of Truth and scope

- Base: current `origin/main` at
  `404476acbf8397bd33af1ee9fd6655e6669d23b5`.
- Preceding same-branch unit: Asset Review Human-decision surface, Draft PR
  #111.
- This unit remains inside the existing TASK-036 Shell and focused-test paths.
  Shared registry, CHANGELOG, workflow, version, TASK-047, OBS and PR110 files
  are unchanged.

## Current gap

The V6.1.1 Planning page exposes only a generic snapshot dump and a permanently
disabled GO button. The released TASK-027 Planning Application already owns
durable Proposal review, one-shot Human GO, and a separate one-shot Approved
Plan installation into Production Control. No typed Application Service exists
for the mock's free-form AI Proposal generation form.

## Detailed design

1. Project exact `creation_intent`, Proposal sections/revision, Provider policy,
   estimate, rights warnings, and Blueprint Scene Contract from
   `planning_snapshot`.
2. For `GO_REQUIRED`, collect only required reference bindings, cost ceiling,
   rights acknowledgement and non-empty actor ID. Prepare against the exact
   Proposal snapshot, display the returned immutable confirmation facts, then
   apply only its one-shot confirmation ID.
3. For `APPROVED` plus `NOT_INSTALLED`, prepare Plan installation against both
   exact Proposal and Production snapshot hashes, confirm Plan/Blueprint/Scene
   counts, and apply only its one-shot confirmation ID.
4. Do not combine GO and installation. Do not infer Human approval from an
   existing Proposal or render an install action for a non-approved state.
5. Render AI Proposal creation as truthfully unavailable because there is no
   corresponding typed service; do not collect unbound brief data or simulate
   Provider output.
6. State the effect boundary: no Provider call, paid authorization, Budget
   reservation, Resolve mutation, publication or media generation.

## Builder Critic

- High: copying the mock form would imply an AI proposal-generation authority
  that does not exist. Correction: no editable mock form; the absent service is
  explicitly disabled.
- High: GO and Production installation could collapse into one click.
  Correction: distinct state predicates, prepare/apply methods and confirmations.
- High: stale Proposal or Production bytes could be accepted. Correction: bind
  the exact current snapshot hashes at prepare and consume one-shot tokens.
- Medium: rights warnings could be silently passed as false. Correction: a
  warning set requires explicit acknowledgement; cancel ends the operation.

Residual Builder C/H/M: `0/0/0`.

## Security / Completeness Critic

- Human actor ID is mandatory and trimmed before apply.
- Existing Provider-policy metadata is display evidence, not execution
  authority.
- No Proposal, approval, Plan, Slot or state is stored in JavaScript.
- Empty/unavailable states do not synthesize a Proposal or PASS.

Residual Security/Completeness C/H/M: `0/0/0`.

## Post-change Evidence

Implementation result:

- `planningSummary` now displays the exact selected Proposal revision, GO
  state and separate installation state;
- `renderPlanning(...)` projects persisted Creation Intent, Proposal sections,
  Provider policy metadata, estimate/warnings and the complete Blueprint Scene
  Contract without creating browser-local Product state;
- `approvePlanning(...)` binds exact reference inputs, current Proposal hash,
  rights acknowledgement, cost ceiling and Human actor to the existing
  prepare/approve boundary;
- `installPlanning(...)` remains a separate Approved-only operation bound to
  both current Proposal and Production hashes;
- unimplemented AI Proposal generation is visibly disabled with its exact
  missing typed-service dependency.

Verification:

- `git diff --check`: PASS;
- Python `compileall`: PASS;
- embedded JavaScript syntax under bundled Node.js: PASS (`scripts=1`);
- focused TASK-027/TASK-036 tests: `53 passed`;
- Windows full regression: `1232 passed, 1 skipped` in `58.88s`; the skip is
  the pre-existing non-Windows credential-vault contract;
- Provider/paid/native/release/deploy/shared-file effects: `0`.

Independent-ready provisional Judge:

`P_UX_1C_PLANNING_REVIEW_GO_INSTALL_SURFACE_R0=PASS_LOCAL_IMPLEMENTATION`

Residual design/implementation C/H/M: `0/0/0`.

This closes the real persisted-Proposal review/GO/install portion of Planning.
AI Proposal authoring remains an explicit missing-service boundary, and
whole-surface V6.1.1 parity is not claimed.
