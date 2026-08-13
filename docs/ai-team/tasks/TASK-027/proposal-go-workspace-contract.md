# TASK-027 — Proposal Revision / Planning Workspace / Human GO Contract

- Date: 2026-08-13
- Status: `R2_PLANNING_WORKSPACE_MINIMUM_LOCAL_GATE_PASS / HOSTED_PR_PENDING`
- External provider execution: NOT STARTED
- Resolve mutation: NOT STARTED
- Publish authority: NOT GRANTED

## Scope

TASK-027 now has a provider-neutral Slice A2 foundation for the user-facing New Video proposal flow:

`Creation Intent -> Proposal Revision -> Planning Workspace -> Human GO -> Approved Production Plan`

This work does not call an AI provider. Proposal content may be created by a later provider adapter or by a Human; the revision/approval contract remains the same.

## Creation Intent

`CreationIntent` is versioned and deterministic. It records purpose, audience, platform, aspect ratio, target duration, tone, story/message, language, optional free text, budget ceiling and rights constraints. Credential values are explicitly outside the contract.

Intent revisions append sequentially. Existing revisions are immutable.

## Production Proposal revisions

A `ProductionProposalRevision` binds:

- exact Creation Intent SHA-256;
- exact validated `ProductionBlueprint`;
- editable proposal sections;
- exact provider-policy identity/version/SHA;
- estimated cost range;
- rights warnings;
- exact previous Proposal SHA for revisions after revision 1.

No revision silently overwrites another. A broken parent hash or unknown Intent fails closed.

## Planning Workspace

`Task027PlanningWorkspaceProjection` exposes the latest proposal, sections, Blueprint, cost range, rights warnings, Provider Policy and GO state. It also identifies section changes from the previous revision.

If a proposal is changed after an earlier GO, the new latest revision returns `GO_REQUIRED`; the previous approval is historical Evidence and cannot authorize the new revision.

## Human GO

`ProductionGoApprovalService` is a one-shot Human Final Authority boundary.

Preparing GO requires:

1. latest Proposal revision only;
2. exact canonical bindings for every existing `AVAILABLE`/`LOCKED` Blueprint reference;
3. no undeclared reference bindings;
4. cost ceiling at or above the Proposal estimated maximum;
5. explicit Human acknowledgement when rights warnings exist.

The confirmation is bound to exact Proposal SHA, reference Asset IDs/SHA values and cost ceiling. If a newer Proposal revision appears before approval, the confirmation becomes stale.

Approving GO creates an immutable `ApprovedProductionPlan` that binds Proposal, Intent, Blueprint, Provider Policy, exact reference Assets, cost ceiling and Human approver. It explicitly does **not** start provider execution, Resolve mutation or publishing.

## Crash-safe persistence

`ProductionProposalSnapshotStore` persists Intent/Proposal/Approved Plan state using:

- canonical JSON;
- SHA-256 self identity;
- atomic replace;
- exact compare-and-swap for replacement;
- symlink rejection;
- maximum snapshot size;
- round-trip identity validation.

The snapshot does not grant provider execution, Resolve mutation or publishing authority and contains no credential values or host paths.

## Approved-plan orchestration

`ApprovedPlanProductionControlInstaller` refuses to install Production Control state from a raw `plan_approved=True` flag. It verifies a registered immutable Approved Production Plan against the exact Blueprint before compiling TASK-037 Slots/Dependencies.

`ApprovedPlanGenerationAdmissionService` derives Plan approval from that same immutable GO evidence. It additionally requires the Prompt/Route Provider Policy SHA to equal the Human-approved policy. Paid execution remains a separate explicit runtime gate; local/free work can be admitted without inventing paid authorization.

## Safety invariants

- proposal != approved plan;
- previous approved revision != current approved revision;
- GO != provider execution;
- GO != Resolve write;
- GO != publish;
- planned future references do not masquerade as existing canonical Assets;
- paid execution remains explicitly authorized at execution time;
- no automatic release/publication.

## Native/UI status

The persisted Proposal/Scene review, exact Human GO and separate Approved Plan -> Production Control installation minimum is now integrated into the unified Desktop `企画` workspace. AI proposal generation/edit authoring and later execution slices remain future Product work. Local validation passes; hosted PR closure remains pending.
