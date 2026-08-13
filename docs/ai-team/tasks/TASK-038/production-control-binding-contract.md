# TASK-038 — Audit Workspace -> TASK-037 Production Control Binding Contract

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`
- Scope: Human audit decision lifecycle binding only
- External generation: NOT EXECUTED
- Physical delete: NOT AUTHORIZED

## Purpose

TASK-038 Audit Workspace previously preserved immutable AI/Human audit records while TASK-037 independently preserved Candidate lifecycle. This binding closes the domain gap without allowing AI score to become Human acceptance.

## Rules

1. An AuditRecord may be registered against a Production Candidate only when `candidate_id` and exact `asset_sha256` match.
2. First valid Audit registration advances `CREATED -> READY_FOR_AUDIT` only. Audit content never auto-accepts/rejects the Candidate.
3. HumanDecision is the only input in this binding that may drive lifecycle to `ACCEPTED`, `REJECTED`, or `ALTERNATE_USE`.
4. `NEEDS_REGENERATION` records Human intent but leaves the current Candidate `READY_FOR_AUDIT`; no generation job starts automatically.
5. A lifecycle-driving decision must reference existing audits belonging to the same Candidate and exact Asset checksum.
6. This foundation allows only one Human lifecycle decision per Candidate to prevent ambiguous replay/conflicting final state.
7. Reject != Delete. No physical purge request is generated.
8. AI critical findings remain findings; they may block automated approval paths but do not silently override Human Final Authority in this binding.

## Safety

Known validation errors are preflighted before cross-registry mutation. Existing Candidate terminal state is fail-closed. Generation, retention/purge, Provider execution and UI approval are separate owners.

## Acceptance

- exact checksum binding
- no partial mutation on hash mismatch
- ACCEPT/REJECT/ALTERNATE_USE lifecycle mapping
- NEEDS_REGENERATION remains non-generating
- critical AI finding alone does not choose Candidate
- duplicate Human lifecycle decision rejected
- stale audit hash rejected before decision persistence
