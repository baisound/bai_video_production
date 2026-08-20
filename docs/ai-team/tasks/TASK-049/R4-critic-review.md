# TASK-049 R4 — Critic Review

- Result: `PASS_WITH_R5_KNOWLEDGE_BOUNDARY_REQUIRED`

## Findings

1. **Producer mistaken for detector:** blocked. `BoundedDBDEventProducer` accepts already-observed typed transitions/markers and performs no media or model inference.
2. **Candidate mistaken for canonical truth:** blocked. Candidate and resolver are separate; CGEL Event creation requires admitted Evidence and policy evaluation.
3. **False certainty from low confidence:** blocked. Below review threshold becomes `UNKNOWN_EVENT / UNKNOWN`; intermediate confidence becomes `NEEDS_REVIEW`.
4. **ASR/LLM hallucination authority:** blocked. ASR-only lacks direct Evidence and `LLM_INFERENCE` origin is never auto-confirm eligible.
5. **Evidence lineage:** missing, cross-Match, source-lineage mismatch, or non-overlapping Evidence fails closed.
6. **Impossible state transition:** duplicate Chase start and invalid Unhook examples remain `NEEDS_REVIEW` and do not advance state.
7. **Confidence inflation:** candidate confidence is capped by admitted Evidence mean.
8. **TASK-009 scope creep:** none. TASK-009 remains data-only and unchanged.
9. **Accuracy overclaim:** none. R4 explicitly owns policy/contract behavior only; real-media accuracy remains R10.

## R5 risks to control

- Perk/Game Knowledge must be a revisioned canonical fact store, not copied mutable text inside CGEL Events.
- LIVE and PTB revisions must never be silently mixed.
- `VERIFIED` knowledge must always retain Source Provenance.
- Alias matching must resolve to stable IDs and fail closed on ambiguity.
- Patch compatibility must be deterministic and must not rely on lexical version ordering that breaks semantic game versions.
- Knowledge lookup is allowed to enrich/explain Event context; it must not retroactively manufacture Event Evidence.
