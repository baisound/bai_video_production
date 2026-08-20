# TASK-052 — DbD Design-to-Implementation Gap Audit / Recognition Completion Roadmap

Status: `IMPLEMENTATION_ACTIVE / R1C_COMPLETE / R2A_NEXT`
Profile: `DEV-3 HIGH ASSURANCE`
Depends on: `TASK-049`, `TASK-050`, `TASK-051`
Owner intent: explicit inventory/design/remediation request in conversation on 2026-08-21
Implementation authority: explicit Owner TASK-052 AUTONOMY authorization on 2026-08-21

## Purpose

Audit the original DbD vision/commentary designs against the current BAI VIDEO PRODUCTION implementation, classify every requirement by implementation truth, and then close the validated gaps without reopening completed historical Tasks or duplicating canonical stores.

TASK-052 is not a rewrite of TASK-049/050/051. It is the successor integration Task that turns legacy design intent, current source reality, Human Acceptance findings and production-oriented recognition needs into one traceable completion roadmap.

## Responsibility boundary

TASK-052 owns:

- design-to-source traceability inventory;
- HUD / OCR recognition gap classification;
- Temporal State Machine gap classification and remediation;
- Survivor HUD, killer-specific Survivor overlays and status-effect HUD taxonomy;
- Killer Capability Registry for killer-conditioned HUD recognition;
- positive/negative status-effect icon recognition around the bottom-right perk HUD;
- selective Tier 3 / Tier 4 vision-gap routing where still relevant;
- Gold Dataset / Human correction feedback-loop gap verification;
- explicit routing of superseded requirements to their current canonical Product owner;
- implementation of validated in-scope gaps after the TASK-051 release checkpoint.

TASK-052 does not silently absorb:

- Production Timeline / Resolve ownership;
- Voice/recording/Consent responsibilities owned by TASK-014/046/047/048;
- paid/cloud Provider execution authority;
- external application mutation;
- public release/deploy authority;
- legacy design items that are already superseded by a newer canonical owner.

## Acceptance

See `TASK-052-DESIGN-TO-IMPLEMENTATION-GAP-AUDIT-DETAILED-DESIGN.md`.

## Current checkpoint

- R0 corpus and 74-row traceability matrix: complete.
- R0A Owner defect/source/current-data baseline: complete.
- Focused pre-remediation source regression: `70 PASS`.
- R1A taxonomy/detail-root/migration dry-run: complete; affected regression
  `105 PASS`, current catalog dry-run `4` proposed CHARACTER→SURVIVOR changes,
  `apply=false`, unresolved Critical/High `0 / 0`.
- R1B Human-first detail and safe delete/tombstone: complete; dependency-driven
  regression `146 PASS`, unresolved Critical/High `0 / 0`.
- R1C map asset byte-sniff/rotation preview hardening: complete; affected regression
  `141 PASS`, existing opaque inventory `SVG 60 / inspection OK 60`, packaged visual
  acceptance still `NOT_CONFIRMED`.
- Windows packaged TASK-052 acceptance: `NOT_CONFIRMED`.
- Next dependency-ordered unit: R2A Survivor-scoped HUD/teacher contract for hook and
  chase state.
