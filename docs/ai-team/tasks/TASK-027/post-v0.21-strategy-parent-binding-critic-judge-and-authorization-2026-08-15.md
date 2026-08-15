# TASK-027 P-ORCH-2 Strategy/Parent Binding Critic, Judge and Authorization

Date: `2026-08-15`
Reviewed baseline: exact main
`4efb0b92855c4943b66b8670c102e447de915498`
Builder design:
`post-v0.21-strategy-parent-binding-current-main-audit-and-builder-design-2026-08-15.md`
DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`

## Critic round 1 - authority, ownership and duplicate truth

1. `CRITICAL / CLOSED`: Queue or adoption could accept caller-selected Strategy
   and Parent values. They accept none; both derive from the confirmed
   regeneration Plan persisted on the immutable Prompt version.
2. `CRITICAL / CLOSED`: a later Prompt could be treated as regenerated merely
   from `prompt_version > 1`. Version is never evidence. A strict binding is
   required, and ambiguous historical rows remain parked.
3. `HIGH / CLOSED`: storing lineage in Draft, Prompt and Queue could create
   competing truth. Draft is pre-confirmation only; Prompt binding is canonical;
   Queue is an immutable execution-admission proof that copies and continuously
   revalidates the canonical binding.
4. `HIGH / CLOSED`: generic Prompt registration could keep creating unbound
   later versions. The Product Application rejects new later versions outside
   the governed regeneration route.
5. `HIGH / CLOSED`: a Profile switch could bypass escalation. Registration
   revalidates `PROVIDER_SWITCH` or higher before saving the binding.
6. `HIGH / CLOSED`: P-ORCH-2 could silently authorize regeneration. Every new
   durable surface retains false Provider/paid/Candidate authority flags; it
   records lineage only.

## Critic round 2 - migration, restart and cross-store integrity

1. `CRITICAL / CLOSED`: strict new fields could make historical Projects
   unreadable. Prompt and Queue loaders accept exact v1.0 and v1.1 shapes;
   historical ambiguity remains readable but non-runnable.
2. `CRITICAL / CLOSED`: automatically inferring a missing legacy parent could
   falsify canonical Evidence. No inference or automatic migration is allowed.
3. `HIGH / CLOSED`: Prompt save could succeed without its lineage. The binding
   is part of the same immutable Prompt row and atomic CAS file write.
4. `HIGH / CLOSED`: a Queue entry could outlive changed Prompt/Audit/Production
   Evidence. Existing full upstream snapshot binding remains, and current-entry
   validation also compares exact execution lineage.
5. `HIGH / CLOSED`: Queue format migration could rewrite historical entry
   identity. Old v1.0 entries remain byte-logically unchanged; new v1.1 entries
   use a distinct deterministic shape. No silent entry upgrade occurs.
6. `HIGH / CLOSED`: output recovery could attach a new Strategy after a crash.
   Adoption transaction identity/checksum includes the original Queue lineage;
   recovery permits only the exact missing suffix.
7. `HIGH / CLOSED`: parent graph validation might check existence but not semantic
   ownership. Same Prompt, version, Slot, body hash and non-regressing Strategy
   are all revalidated at registration and Attempt creation.
8. `HIGH / CLOSED`: read-only UI could leak private generation material. Only
   logical IDs, Strategy level and bounded status are projected; Prompt body,
   host path, media and credentials stay excluded.
9. `MEDIUM / CLOSED`: format work could be mistaken for a new release. No version,
   Tag or Release is selected.

Unresolved Critical/High after two correction rounds: `0 / 0`.

## Final Plan

1. Add immutable Prompt regeneration binding and strict Prompt store v1.1
   compatibility.
2. Persist it only through current Human-confirmed regeneration registration.
3. Add deterministic Queue v1.1 execution lineage while retaining strict v1.0
   reads.
4. Use that lineage for regenerated-output adoption and exact PASS Attempt
   creation.
5. Run migration, tamper, stale-state, restart, privacy and authority tests.
6. Synchronize Product Evidence and publish through a dedicated implementation
   PR only after all local gates and implementation Critic pass.

## Judge

`P_ORCH_2_DESIGN_LOCAL_PASS / HOSTED_DESIGN_PR_AUTHORIZED`

Implementation is conditionally authorized only after this exact design passes
hosted checks, merges to main, its branch/checkout cleanup completes and a
fresh-main audit confirms no newer conflicting Source of Truth. The later
implementation remains bounded to the Allowed Files and order in the Builder
design. TASK-013 Native H3 replay, Provider/paid execution, Credential input,
automatic Audit, Candidate ACCEPT/LOCK, publication, Resolve/Cubase mutation,
Production Deploy and Release/Tag are not authorized by this decision.
