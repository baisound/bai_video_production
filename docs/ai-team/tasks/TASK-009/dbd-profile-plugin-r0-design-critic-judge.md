# TASK-009 R0 DBD Profile Plugin — Design / Critic / Judge

## Decision

`IMPLEMENT_TASK008_BOUND_DBD_PROFILE_PLUGIN_CONTRACT`

## Design

- Reuse `TASK-008 FeatureRule` and `ScoringProfile` directly; duplicate normalization/scoring logic is zero.
- Closed signal families: `HUD_STATE | CHASE | EVENT`.
- Closed signal kinds have a single immutable family mapping.
- A valid snapshot covers all three families, uses canonical-sorted unique rules, and has exact one-to-one projection into the TASK-008 scoring profile.
- TASK-008 continues to enforce 2+ modalities, exact weight total 1000, source selector closure, raw bounds, required/optional semantics and deterministic profile digest.
- TASK-001 `PluginDescriptor` validates that the plugin cannot claim Job/Core DB/NLE mutation.
- Runtime feature producer remains `NOT_SELECTED`; profile membership is not runtime/capability Evidence.
- Snapshot digest uses canonical JSON and independently verifies the nested TASK-008 profile digest.

## Negative matrix

- string substituted for closed signal enum
- signal kind mapped to wrong family
- missing HUD/CHASE/EVENT family
- duplicate/unsorted feature rows
- signal projection differs from TASK-008 rules
- weight total not 1000 or single-modality profile
- invalid/max+1 rules or version
- outer rehash hides invalid nested profile digest
- plugin capability claims Core/Job/NLE mutation
- profile name/selector treated detector installation or current-valid Evidence
- media/HUD/OCR/game process/filesystem/network/subprocess/provider operation
- Human review omitted or profile promoted automatic Edit Plan/Timeline authority

## Builder / Completeness Critic

Finding: a DBD-only scoring implementation would duplicate TASK-008 normalization and missing/UNKNOWN behavior.

Correction: DBD rows own only taxonomy metadata and embed the canonical TASK-008 `FeatureRule`; `ScoringProfile` remains the sole generic scoring contract.

Residual C/H/M: `0/0/0`.

## Security / Authority Critic

Finding: `dbd` plugin identity or an allowed producer selector could be misread as installed detector/runtime Evidence.

Correction: `runtime_feature_producer_state=NOT_SELECTED`, explicit no-effect fields, no effect-capable API, and separate future acquisition/capability Gates.

Residual C/H/M: `0/0/0`.

## Operations / Compatibility Critic

Finding: taxonomy values could drift independently from generic profile rule order.

Correction: canonical `(feature_key, signal_kind)` ordering and exact tuple equality between taxonomy feature rules and `ScoringProfile.rules`.

Residual C/H/M: `0/0/0`.

## Independent Judge

- TASK-001 plugin boundary reuse: PASS
- TASK-008 scoring contract reuse / duplicate logic zero: PASS
- HUD/chase/event taxonomy closure: PASS
- deterministic nested/outer digest: PASS
- no runtime/media/game/edit effect authority: PASS
- focused TASK-009/TASK-008/Profile regression: `30 PASS`
- full WSL2 regression: `1595 PASS / 1 intentional Windows-only skip`
- compileall / schema mirror / git diff check: PASS
- residual C/H/M: `0/0/0`

`JUDGE=PASS_LOCAL_PENDING_HOSTED_EVIDENCE`
