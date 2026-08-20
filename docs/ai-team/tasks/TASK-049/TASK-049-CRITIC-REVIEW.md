# TASK-049 — Pre-Implementation Critic Review

- Review state: `PASS WITH CONTROLLED RISKS`
- Scope: integration architecture and Atomic implementation plan

## Findings resolved by the design

### C1 — Separate EXE without demonstrated product need

**Risk:** duplicate installer/runtime/settings/store/release train and split project lineage.

**Resolution:** no standalone product. Require analysis-only workflow in BVP and preserve a future extraction seam.

### C2 — Confusing game timeline with editing timeline

**Risk:** game recognition could become accidental edit authority and BVP production state could become false game truth.

**Resolution:** separate Canonical Game Event Timeline and Production Timeline; bridge is proposal/adoption only.

### C3 — Floating timestamp drift

**Risk:** `331.42` style timestamps are insufficient for exact NTSC/VFR-normalized BVP workflows.

**Resolution:** reuse TASK-022 rational/end-exclusive semantics; frames are canonical and seconds are derived.

### C4 — Reimplementing existing BVP capabilities

**Risk:** second ASR, Asset identity, media mapper, credential store, export/runtime stack.

**Resolution:** explicit reuse matrix and per-unit dependency loading.

### C5 — Existing TASK-009 R0 scope laundering

**Risk:** existing `DBDProfilePluginSnapshot` currently promises no detector/media/timeline mutation. Silently adding those behaviors to the same contract would break R0 guarantees.

**Resolution:** TASK-049 adds new `game_intelligence` contracts/services while preserving R0 compatibility surface.

### C6 — LLM claims as events

**Risk:** hallucinated chase/perk/event facts become canonical.

**Resolution:** confirmed events require admitted Evidence; UNKNOWN/NEEDS_REVIEW are first class; Commentary is downstream and validated.

### C7 — Knowledge/event duplication

**Risk:** patch changes make copied perk effect text stale in old events.

**Resolution:** events store stable knowledge/revision refs, not mutable fact bodies.

### C8 — Development cost blow-up

**Risk:** every Atomic Unit re-reads entire repo/Ver.2.2 and uses highest-cost reasoning for mechanical work.

**Resolution:** README AUTONOMY adaptive model/depth/context guidance + R1..R10 direct dependency context sets.

## Remaining controlled risks

### RISK-A — Vision accuracy is unknown

Mitigation: R4 proves contract/UNKNOWN behavior first; R10 owns real-media Gold Dataset and acceptance metrics.

### RISK-B — UI work can conflict with ongoing TASK-036 UX lane

Mitigation: R1-R5 are backend-first. R6/R9 UI integration must re-check current TASK-036 ownership/allowed files before touching shared shell/view resources.

### RISK-C — Schema count / migration complexity

Mitigation: R1 defines minimal closed schemas; R2 introduces persistence/migration only after R1 Critic and tests are green.

### RISK-D — Game patch drift

Mitigation: version/environment/source provenance is mandatory, PTB/LIVE are separate, unknown patch can fail closed.

## Critic verdict

The design is suitable to begin R1 after repository authority is revalidated. Do not authorize broad detector accuracy, production release, paid Provider use, external NLE mutation, or standalone product creation from this document alone.
