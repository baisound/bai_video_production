# TASK-038 — Audit Workspace / Candidate Quality Loop
## Pre-implementation Detailed Design Ver.0.9

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / IMPLEMENTATION_NOT_AUTHORIZED_BY_THIS_DOCUMENT`
- Depends on: TASK-037 contracts

## Objective

Provide a normalized Candidate audit model and unified Audit Workspace where AI inspection and Human final decision remain distinct.

## Audit model

### AuditRecord

- audit_id
- candidate_id
- asset_sha256
- contract_refs[]
- auditor_kind (`AI`, `HUMAN`)
- auditor/provider version
- dimension_scores[]
- findings[]
- failure_codes[]
- alternate_use_proposals[]
- created_at
- immutable hash

### HumanDecision

- decision_id
- candidate_id
- audit_refs[]
- decision (`ACCEPT`, `REJECT`, `ALTERNATE_USE`, `NEEDS_REGENERATION`)
- reason codes/notes
- actor
- created_at

AI score never equals Human decision.

## Dimensions

Extensible rather than one fixed 51-column table. Typical dimensions:

- contract compliance
- identity consistency
- geometry/spatial relation
- continuity
- artifact/technical defects
- audio correctness
- composition/aesthetic
- policy/license suitability

Critical violations are represented explicitly and may make AI recommendation `REJECT`, but Human remains final authority unless a hard Safety/Policy gate forbids acceptance.

## Failure routing

Audit findings may propose:

- prompt correction;
- layout/reference escalation;
- provider switch;
- manual repair;
- alternate use.

TASK-040 owns Prompt/Regeneration evidence. TASK-038 does not directly launch expensive generation.

## Workspace UX

One Candidate at a time with:

- large preview;
- contract checklist;
- AI findings panel;
- Human findings/decision panel;
- previous/next Candidate;
- compare history;
- regeneration request;
- lock after Human accept;
- rejected/alternate history remains discoverable.

## Acceptance draft

- AI and Human records separately attributable;
- Critical failure cannot be hidden by a high aesthetic score;
- reject does not delete bytes;
- regeneration request never mutates original Candidate;
- audit history remains hash-traceable;
- Human override preserved and visible;
- import/export can represent seed CSV without making that CSV the persistence model.
