# TASK-052 — DbD Design-to-Implementation Gap Audit / Recognition Completion Roadmap

Status: `IMPLEMENTATION_ACTIVE / R3B_COMPLETE / R3C_NEXT`
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
- R2A Survivor-subject observation/teacher identity: complete; focused `36 PASS`,
  dependency-driven affected regression `206 PASS`, unresolved Critical/High `0 / 0`.
- R2B batch visual registration transaction/progress/cancel/no-console: complete;
  focused `20 PASS`, dependency-driven affected regression `212 PASS`, unresolved
  Critical/High `0 / 0`.
- R2B-F1 packaged startup failure fix: complete; nested JSON-like Knowledge details
  no longer cause `TypeError: unhashable type: 'dict'` during initial inventory
  refresh. Rebuilt Windows EXE passed Owner-workspace startup, inventory search,
  Survivor HUD four-slot switching, registered-image listing and unified review
  display (`13` focused / `38` TASK-052 / `161` affected PASS).
- Windows packaged startup and bounded non-destructive interaction: `PASS`.
- R3A temporal state-machine core: complete; profile-bound generator temporal
  majority/impossible-increase handling, exact-subject chase hysteresis, Survivor
  transition validation and same-subject hook-count reconciliation are implemented
  as a pure deterministic layer. Focused/affected regression `35 PASS`; all current
  TASK-052 tests `43 PASS`; broad DbD/TASK-052 regression `128 PASS`; unresolved
  Critical/High `0 / 0`.
- R3B admitted Evidence / CGEL integration: complete; confirmed temporal decisions
  map to synchronized generator/chase/Survivor taxonomy, while subject-bound
  Resolver chase/hook state prevents cross-slot contamination and legacy
  subjectless candidates retain their global compatibility path. Focused regression
  `42 PASS`; TASK-049/TASK-052 affected regression `243 PASS`; unresolved
  Critical/High `0 / 0`.
- Overall Windows packaged real-media TASK-052 acceptance: `NOT_CONFIRMED`.
- Next dependency-ordered unit: R3C killer-specific progress/stage and status-effect temporal state.
