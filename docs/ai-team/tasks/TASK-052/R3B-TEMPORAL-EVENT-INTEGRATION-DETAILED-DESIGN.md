# TASK-052 R3B Temporal Event Integration Detailed Design

Status: IMPLEMENTATION BOUND

Governance: DEV-3 HIGH ASSURANCE

## Boundary

R3B bridges R3A temporal truth into existing CGEL candidates and the admitted-Evidence Resolver. It does not perform detection, create Evidence, accept real media, or mutate the Production Timeline.

## Admission

- Only `TemporalDecisionStatus.CONFIRMED` may produce a candidate.
- Every produced candidate carries non-empty Evidence references and a source range containing the decision frame.
- Survivor events require `match_id + survivor_slot`; subjectless Survivor decisions fail closed.
- Candidate auto-confirmation still requires the existing Resolver checks for admitted direct Evidence, lineage, temporal overlap, confidence and valid transition.

## Taxonomy

- generator remaining decrease: `GENERATOR_COMPLETE`
- chase active/not-active confirmation: `CHASE_START` / `CHASE_END`
- Survivor transitions: `INJURY`, `DOWN`, `HOOK`, `UNHOOK`, `KILL`, `ESCAPE`
- recovery and hook-count changes remain state Evidence and do not create duplicate CGEL events.

`GENERATOR_COMPLETE` is synchronized across the canonical enum, source/runtime schema copies, review/benchmark schemas, training labels, editing intelligence and commentary priority.

## Resolver state

Known Survivor candidates use a sorted per-slot state collection. Chase and hook state for one slot cannot block or advance another slot. Legacy candidates without a subject retain the previous global state path for backward compatibility. Resolver output exposes both legacy global state and the per-slot states for audit.

## Acceptance

- confirmed temporal transitions map to the intended taxonomy;
- candidate/abstained/review decisions cannot emit candidates;
- missing subject or non-containing source range fails closed;
- simultaneous chase/hook states across distinct slots confirm independently;
- duplicate transitions for the same slot require review;
- Generator completion requires admitted direct Evidence;
- TASK-049 and TASK-052 affected regression remains green.
