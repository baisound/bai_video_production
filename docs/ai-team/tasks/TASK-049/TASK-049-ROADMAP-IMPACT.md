# TASK-049 — Roadmap Impact

## Decision

`TASK-009` remains the completed `DBDProfilePlugin R0` responsibility. The new DbD Video Intelligence / Canonical Game Event Timeline scope is materially broader and therefore receives a new top-level task: `TASK-049`.

```text
TASK-008 Multimodal Scoring
  -> TASK-009 DBDProfilePlugin R0 (COMPLETE)
  -> TASK-049 DbD Game Intelligence / CGEL (NEW)
```

TASK-049 reuses TASK-009 taxonomy/profile contracts but MUST NOT rewrite the R0 `data-only` promise.

## Planned Atomic Units

```text
TASK-049 R1  Canonical Game Event contract foundation
TASK-049 R2  Store / revisions / resume
TASK-049 R3  BVP Asset / Media / ASR / Timebase adapters
TASK-049 R4  bounded DbD feature producers / event resolver
TASK-049 R5  DbD Game Knowledge / Perk baseline
TASK-049 R6  Human Review workspace
TASK-049 R7  RAG / Commentary / Fact Validator
TASK-049 R8  GameEventToProductionBridge
TASK-049 R9  Independent Analysis Workflow / packaged test EXE
TASK-049 R10 Native pilot / Gold Dataset / KPI
```

## Concurrency

R1-R5 are backend/schema-first and should avoid shared UI ownership. R6/R9 MUST re-check the active TASK-036 P-UX lane and current work locks before modifying shared Shell/UI files.

## Release

This development campaign targets local implementation, tests, and eventually a packaged **test BVP EXE**. It does not authorize tag/release/publication/production activation.
