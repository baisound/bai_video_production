# TASK-052 R7 — Selective Vision AI / Contradiction Escalation

## Boundary

R7 adds a side-effect-free planning boundary for expensive Tier 4 Vision analysis.
It reuses the Product's canonical `AiConnectionResolver`, `ModelRoute` and
`CapabilityExecutionRequest` contracts. It does not add a DbD provider stack,
invoke an adapter, read credentials, dispatch a request or create a canonical game
event.

Paid/cloud/local Provider execution remains a Human Gate. This unit exercises only
deterministic plan construction with synthetic profiles; no external call is made.

## Eligibility and bounds

A candidate is limited to one exact source interval of at most 300 frames, one to
eight unique normalized ROIs, unique provenance references and one or more of the
legacy high-value triggers:

- chase boundary ambiguity;
- pre-down moment;
- rescue moment;
- generator completion;
- major tactical decision;
- contradiction between Tier 1–3 evidence.

High-confidence non-contradictory Tier 1–3 Evidence is not escalated. A Tier
contradiction remains eligible even when a detector reports high confidence.

## Authority and canonical provider route

The planner returns `AUTHORIZATION_REQUIRED` before provider resolution when exact
execution authority is absent. Authority requires both an `authorization://`
reference and a positive bounded cost ceiling. Evidence references cannot use
authority, credential or secret schemes.

After authority is present, the existing IMAGE workload resolver must select an
available route declaring `DBD_SELECTIVE_VISION_ANALYSIS`. Missing/disabled routes
return `ROUTE_UNAVAILABLE`. A `READY` result contains an immutable execution
request proposal but still performs no dispatch.

Every proposal requires abstention and provenance in the response contract and
sets `event_claim_allowed=false`. Provider output is therefore analysis Evidence
for downstream validation/Human review, never direct CGEL truth.

## Verification and remaining truth

- R7 + canonical Provider/fusion focused regression: `30 PASS`;
- no Provider adapter was constructed or executed;
- unresolved Critical/High findings: `0 / 0`.

R8 remains responsible for held-out Human Gold, per-domain KPIs, UNKNOWN/FP/FN
analysis and correction feedback. R9 remains responsible for packaged real-media
acceptance.
