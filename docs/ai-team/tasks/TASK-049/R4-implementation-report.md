# TASK-049 R4 — Implementation Report

- Unit: `R4 Bounded DbD Feature Producers / Event Resolver`
- Status: `IMPLEMENTED / FOCUSED+DEPENDENCY TEST PASS`
- Development depth: `DEV-2 STANDARD` with high-reasoning Critic boundary review
- Accuracy claim: `NONE`; this unit validates contracts/policy/state behavior, not production detector accuracy

## Implemented

- `DBDEventCandidate` as an ephemeral, non-canonical candidate contract;
- `BoundedDBDEventProducer` that compiles already-observed bounded TASK-009 signals or explicit visual markers into candidates without performing media/Vision inference itself;
- bounded TASK-009 mappings:
  - `CHASE_INTENSITY false -> true` -> `CHASE_START`;
  - `CHASE_INTENSITY true -> false` -> `CHASE_END`;
  - `EVENT_HOOK false -> true` -> `HOOK`;
  - `EVENT_RESCUE false -> true` -> `UNHOOK`;
  - `HUD_SURVIVOR_HEALTH HEALTHY -> INJURED` -> `INJURY`;
- bounded visual marker mappings for `MATCH_START`, `WINDOW_VAULT`, and `PALLET_DROP`;
- explicit rejection of TASK-009 signal kinds that are not admitted as R4 event producers;
- `DBDEventResolver` that validates Evidence lineage, Match ownership, temporal overlap, candidate/evidence confidence, and origin policy before creating a CGEL Event;
- conservative effective confidence bounded by both candidate confidence and admitted Evidence mean;
- automatic confirmation only for admitted deterministic origins with direct Evidence and policy threshold pass;
- ASR-only and LLM-origin candidates cannot auto-confirm;
- low confidence becomes `UNKNOWN_EVENT / UNKNOWN`;
- medium confidence and policy/state conflicts become `NEEDS_REVIEW`;
- deterministic bounded state machine for Match start, Chase start/end, Hook/Unhook;
- impossible duplicate/contradictory transitions do not mutate resolver state and remain reviewable rather than being silently repaired;
- resolver reason codes and before/after state are preserved inside Event state for auditability.

## Explicit non-ownership

R4 does not:

- implement production-grade Vision/HUD detection;
- call an LLM or Provider;
- access the game process;
- claim detector accuracy;
- mutate TASK-009 `DBDProfilePlugin R0`;
- mutate BVP Production Timeline / Resolve;
- bypass Human Review for uncertain observations.

## Verification

```text
TASK-049 R1-R4 + direct TASK-003/004/006/009/022 dependency regression:
150 PASS

R4 focused tests:
11 PASS

compileall: PASS
git diff --check: PASS
```
