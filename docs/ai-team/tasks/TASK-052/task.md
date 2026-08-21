# TASK-052 — DbD Design-to-Implementation Gap Audit / Recognition Completion Roadmap

Status: `IMPLEMENTATION_ACTIVE / R7_COMPLETE / R8_NEXT`
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
- R3C Killer/status temporal state: complete; exact Killer/effect registry routing,
  profile-bound stage/progress monotonicity, positive/negative effect namespace
  isolation, appearance/disappearance hysteresis and contradiction recovery are
  implemented as state Evidence only. R3A-R3C focused regression `33 PASS`;
  TASK-049/TASK-052 affected regression `252 PASS`; unresolved Critical/High `0 / 0`.
- R4A Killer Capability Registry: complete; exact Killer/effect/ROI/detector/teacher
  namespace contracts, Ghost Face/Onryo/Doctor starter fixtures, identity-first
  detector selection, four-slot Survivor routing and runtime cross-Killer hard
  negatives fail closed to UNKNOWN. Focused R4A/R3C regression `18 PASS`;
  tkinter-independent TASK-052/Killer/recorded-video affected regression `80 PASS`.
  The lightweight WSL test environment lacks tkinter, so the packaged-startup
  module was not rerun in this unit; its prior Windows native PASS remains unchanged.
- R4B recorded-video routing: complete; the resolved/aligned HUD Profile maps
  existing Survivor slots and Killer-power ROI into R4A, reuses common Survivor
  slices, requires bounded match identity and persists body-free digest Evidence.
  Unknown/power-only identity requests no specific overlays. Focused R3C-R4B,
  recorded-video and profile compatibility regression `31 PASS`; tkinter-independent
  TASK-052/Killer/recorded-video/profile/vision-slice affected regression `95 PASS`.
- R4C1 Killer-specific Teacher backend: complete; the canonical Visual Training
  manifest backward-reads old CSV while storing exact target/observed namespace,
  role, subject and structured state. Capability-bound index construction requires
  positive + registered hard-negative coverage, and the deterministic starter
  reference detector preserves foreign namespaces for R4A rejection. Focused
  backend/manifest regression `42 PASS`; affected Training Studio/TASK-052
  regression `123 PASS`.
- R4C2 Killer-specific Teacher Training Studio: complete; existing Safe Visual
  Learning now preserves the exact target/observed namespace, role, subject and
  structured state through preview receipt, Human confirmation and capability-bound
  index rebuild. The UI reuses the four Survivor ROIs, admits only registered
  capability/namespace pairs and blocks generic editing of Killer-specific rows.
  Focused regression `30 PASS`; TASK-050/TASK-052 dependency regression `161 PASS`;
  TASK-051/package-source affected regression `125 PASS`; unresolved Critical/High
  `0 / 0`.
- R5A bottom-right status-icon segmentation: complete; HUD Profile schema `2.3.0`
  adds backward-readable optional positive/negative regions, Training Studio can
  calibrate both, and recorded-video recognition emits zero/one/multiple body-free
  component candidates or explicit unavailable/overflow states. Polarity/region
  namespace crossing and unbounded input/candidate counts fail closed. Focused
  regression `29 PASS`; TASK-049 DbD + TASK-050/051/052 affected regression
  `370 PASS`; unresolved Critical/High `0 / 0`.
- R5B status-effect identity/polarity/source/visibility: complete; canonical
  positive/negative label namespaces resolve only registered R3C definitions,
  source kind comes from that registry, and visibility-only, Perk hard-negative,
  polarity contradiction and ambiguous matches never claim identity. Recorded
  recognition revalidates the exact crop digest and keeps recognition keys bound
  to R5A candidates. R5A/R5B focused regression `14 PASS`; TASK-049 DbD/TASK-052
  affected regression `192 PASS`; TASK-050/TASK-051 compatibility regression
  `186 PASS`; unresolved Critical/High `0 / 0`.
- R5C1 Status Effect Teacher backend: complete; canonical Visual Training domains
  preserve R5B positive/negative/visibility/Perk hard-negative labels, reject
  polarity/group/subject/registry crossings during preview and confirmation, and
  require identity plus hard-negative coverage before an R5B-valid index is
  published. Hierarchical segment ROI IDs are normalized into safe preview
  filenames. Focused regression `16 PASS`; TASK-050/TASK-052 affected regression
  `179 PASS`; TASK-051 compatibility regression `118 PASS`; unresolved
  Critical/High `0 / 0`.
- R5C2A Status Effect Gold/review/temporal bridge: complete; exact held-out Gold
  coordinates report status/identity/polarity/source/visibility/abstention
  separately, immutable Human corrections retain original/corrected identity and
  provenance, and only registry/scope-complete IDENTIFIED observations enter the
  existing R3C state machines. UNKNOWN, contradiction, incomplete segmentation or
  missing exact region Evidence cannot infer disappearance. Focused R3C/R5B/R5C2A
  regression `26 PASS`; TASK-049 DbD/TASK-052 affected regression `205 PASS`;
  TASK-050/TASK-051 compatibility regression `186 PASS`; unresolved Critical/High
  `0 / 0`.
- R5C2B Status Effect Teacher operator UI: complete; workspace-scoped atomic and
  revisioned definition registry binds effect identity/polarity/source/scope,
  Training Studio exposes both calibrated positive/negative regions and canonical
  Perk hard-negatives, and whole-region batch intake requires explicit single-icon
  Human confirmation. Focused regression `17 PASS`; TASK-050/TASK-052 affected
  regression `193 PASS`; TASK-051 compatibility/source gate `118 PASS`; unresolved
  Critical/High `0 / 0`.
- R6 Tier 3 object/scene baseline: complete; canonical definitions keep pallets
  and windows under MECHANIC, map features/main buildings under MAP and tiles
  under TILE, while deterministic reference-crop classification requires identity
  plus hard-negative coverage and fails closed on ambiguity, foreign map namespace
  or unregistered labels. Object visibility cannot claim PALLET_DROP/WINDOW_VAULT.
  Focused regression `18 PASS`; TASK-049 DbD/TASK-052 affected regression
  `214 PASS`; unresolved Critical/High `0 / 0`.
- R7 selective Vision escalation: complete; high-value/contradictory exact source
  windows and bounded ROIs route only through the canonical Product IMAGE Provider
  resolver, and missing explicit authority, cost ceiling, capability or available
  route fails closed before request construction/dispatch. Plans retain Evidence
  references, require abstention and can never claim a CGEL event. R7 + canonical
  Provider/fusion focused regression `30 PASS`; external Provider calls `0`;
  unresolved Critical/High `0 / 0`.
- Overall Windows packaged real-media TASK-052 acceptance: `NOT_CONFIRMED`.
- Next dependency-ordered unit: R8 Gold / correction / KPI closure.
