# TASK-040 — Prompt Registry / Generation Evidence & Regeneration Routing
## Pre-implementation Detailed Design Ver.0.9

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / IMPLEMENTATION_NOT_AUTHORIZED_BY_THIS_DOCUMENT`
- Depends on: TASK-028, TASK-037, TASK-038

## Objective

Version prompts and generation decisions so every Candidate can be traced to exact inputs/provider profile while repeated failures change strategy rather than causing endless prompt micro-tuning.

## Prompt entity

- prompt_id
- prompt_version
- purpose/scene/slot
- body_ref (project-private storage)
- body_sha256
- negative/body adjunct refs
- provider_profile_id/version
- input_candidate/asset refs[]
- keep_conditions[]
- created_by
- created_at

General Evidence should store prompt identity/hash by default, not duplicate full prompt bodies.

## GenerationAttempt

- generation_job_id
- slot_id
- prompt_id/version/hash
- provider/model/profile version
- seed/config where applicable
- input asset hashes
- output candidate_id
- cost/latency if available
- result
- failure_codes[]
- parent_attempt_id
- strategy_level

## Adaptive regeneration

Same structural Failure Code repeated >= configured threshold (initial roadmap rule: 2) stops text-only micro-tuning and routes to a higher strategy:

0 text prompt
1 prompt restructure/negative
2 final-shot/layout reference
3 pose/depth/edge/segmentation control
4 I2I/inpainting/region repair
5 provider/model switch
6 Human composition fix

Provider-specific controls remain Provider Profile data, not Product Core enum assumptions.

## High-cost admission

Generation request is executable only when:

`PLAN_APPROVED + FEASIBILITY_PASS + REQUIRED_INPUT_LOCKED`

and budget/authority permits the provider cost.

## Acceptance draft

- exact prompt identity per Candidate;
- prompt body privacy/retention separated from general Evidence;
- repeated structural failure escalates strategy;
- parent Candidate/attempt trace intact;
- provider switch recorded rather than hidden;
- no expensive generation on STALE/unlocked required input;
- no auto-promotion of a successful prompt to global Knowledge.
