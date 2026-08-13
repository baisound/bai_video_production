# TASK-038 — Audit Workspace Application Service Contract Ver.1.0

- Date: 2026-08-13
- Status: `APPLICATION_SERVICE_FOUNDATION_PASS / USER_WORKSPACE_NATIVE_PENDING`
- UI direction: Vrew/Premiere/Resolve-class NLE workspace, not a generic AI dashboard.

## Canonical layout

```text
Left                  Center                     Right
Scene / Slot /        Candidate Viewer /         Audit Inspector
Candidate browser     Compare / History          Scores / Findings
                                                 Human Decision

Bottom: Candidate lineage / version history / Continuity / Prompt Attempt history
```

## Projection

The Audit Workspace projects exact TASK-037 Production Candidate identity with TASK-038 immutable Audit records.

Each Candidate row exposes:

- Scene / Slot / Candidate / Asset identity;
- lifecycle / Slot state;
- AI and Human audit counts;
- latest dimension scores;
- Critical violation flag;
- Failure Codes;
- existing Human decision;
- available Human actions.

A high AI score never becomes a Human decision.

## Human decision boundary

`ACCEPT / REJECT / ALTERNATE_USE / NEEDS_REGENERATION` use an exact one-shot confirmation bound to:

- Candidate ID;
- exact Candidate Asset SHA-256;
- exact immutable Audit ID set;
- exact Audit record hash set;
- requested Human decision.

If a new Audit is added or Candidate bytes/state change after confirmation preview, apply fails closed.

`NEEDS_REGENERATION` records Human intent only. It does not start a Provider.

`REJECT` does not physically delete media.

## Native/UI acceptance later

- Candidate compare and history remain visible while Human decides;
- Critical finding is visually prominent but does not disable Human override policy unless separate governance says so;
- decision confirmation summarizes exact Candidate/Audit state;
- screen does not rely on color alone;
- selected Candidate synchronizes with Generative AI / Scene / Continuity workspaces through canonical IDs.
