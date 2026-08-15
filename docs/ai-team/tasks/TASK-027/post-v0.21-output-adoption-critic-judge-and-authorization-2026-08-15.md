# TASK-027 Post-v0.21 Output Adoption Critic, Judge and Authorization

Date: `2026-08-15`
Reviewed baseline: exact main
`1956f6e04b0c6206f64333d719f41c567def0590`
Builder design:
`post-v0.21-current-main-audit-and-output-adoption-builder-design-2026-08-15.md`
DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`

## Critic round 1 — authority and duplicate-truth review

1. `CRITICAL / CLOSED`: a completed Provider result could be treated as a
   canonical/published Asset. Completion is only contained Evidence; canonical
   ingest and Human Audit remain mandatory.
2. `CRITICAL / CLOSED`: Candidate creation could bypass TASK-038. The unit ends
   at `READY_FOR_AUDIT`; ACCEPT/REJECT/ALTERNATE/REGENERATE and LOCK remain the
   existing TASK-038/TASK-037 Human paths.
3. `HIGH / CLOSED`: caller-supplied output/Candidate identities could forge
   lineage. All identities derive from the current execution, Queue, Prompt,
   Slot and canonical ingest result; callers provide only an existing execution
   selection and exact snapshot hashes.
4. `HIGH / CLOSED`: adoption could replay paid or uncertain work. It performs no
   execution and accepts only terminal `COMPLETED`; `DISPATCHING`/unknown/failed
   records are ineligible.
5. `HIGH / CLOSED`: direct Production candidate registration could remain a
   parallel truth. P-ORCH-1 reuses the one TASK-037 store and the one TASK-040
   Prompt registry; it adds only an orchestration transaction.
6. `HIGH / CLOSED`: generated rights could be overstated. Canonical ingest uses
   conservative rights/publication fields and exact generation provenance;
   completion never grants publication authority.

## Critic round 2 — crash, security and compatibility review

1. `CRITICAL / CLOSED`: a crash across SQLite Asset, Production and Prompt
   stores could produce partial authority. A checksum-closed phase transaction
   records exact expected/produced identities; recovery permits only the exact
   missing suffix and parks any third state.
2. `HIGH / CLOSED`: automatic retry after an uncertain write could duplicate
   state. Every phase is inspected idempotently before continuation; no external
   Provider call is part of recovery.
3. `HIGH / CLOSED`: `project-output://` could escape or follow a symlink. Only a
   launcher-private resolver below the configured root is allowed, with every
   segment and final regular file checked before streaming ingest.
4. `HIGH / CLOSED`: bytes might change between execution and ingest. Exact
   execution SHA is checked before and by the ingest path; source drift fails
   closed.
5. `HIGH / CLOSED`: Prompt body, credential or host path might leak through
   Evidence/UI. Durable/public surfaces contain logical refs and hashes only;
   security tests inspect JSON, errors and view models.
6. `HIGH / CLOSED`: legacy projects could be made unreadable. Missing adoption
   state is empty-compatible and existing stores retain their versions/shapes.
7. `HIGH / CLOSED`: a Candidate could be marked ready without Prompt lineage.
   `READY_FOR_AUDIT` is the final phase only after exact PASS Attempt and
   GENERATED_FROM binding succeed.
8. `MEDIUM / CLOSED`: this design could be mistaken for Native H3 completion or
   a new Release. Both claims remain false; version remains unselected.

Unresolved Critical/High after two correction rounds: `0 / 0`.

## Final plan

1. Implement the strict transaction and exact restart recovery.
2. Revalidate contained output and reuse canonical TASK-003 ingest.
3. Register one exact TASK-037 Candidate idempotently.
4. Register the exact TASK-040 PASS Attempt and Prompt dependency idempotently.
5. Move only to `READY_FOR_AUDIT` and expose the bounded Human-confirmed Shell
   action.
6. Run all required focused/full/static/security/recovery gates.
7. Synchronize Evidence and publish only through a dedicated implementation PR.

## Judge

`P_ORCH_1_DESIGN_LOCAL_PASS / HOSTED_DESIGN_PR_AUTHORIZED`

Implementation is conditionally authorized only after this exact design passes
hosted checks, merges to main, branch/checkout cleanup completes and fresh-main
reselection confirms no newer conflicting Source of Truth. Production Deploy,
paid Provider, Credential input, TASK-013 Native H3 replay, automatic Audit,
Candidate ACCEPT/LOCK and Release/Tag are not authorized by this design.
