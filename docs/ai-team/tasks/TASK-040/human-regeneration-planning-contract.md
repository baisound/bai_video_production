# TASK-040 — Human Regeneration Planning Contract Ver.1.0

- Date: 2026-08-13
- Status: `AUTOMATED_FOUNDATION_PASS / PROVIDER_EXECUTION_NOT_AUTHORIZED`

## Purpose

A Provider may technically return PASS while the resulting image/video fails Visual Compliance or Human review. TASK-040 therefore treats generation transport success separately from production acceptance.

## Admission

A regeneration plan requires:

- exact Production Candidate;
- exact Candidate Asset SHA-256;
- exactly one Human `NEEDS_REGENERATION` decision;
- all decision Audit references present and bound to the same Candidate bytes;
- explicit Failure Codes/reasons;
- Candidate `generation_job_id` mapped to Prompt Registry Attempt;
- exact Prompt version/hash;
- mutable target Slot.

## Escalation

The current audited failure counts as one failure occurrence even if the Provider Attempt itself returned PASS.

If preceding Slot attempts contain the same Failure Class consecutively and the configured threshold is reached, control strategy escalates one level:

```text
TEXT_PROMPT
→ PROMPT_RESTRUCTURE
→ LAYOUT_REFERENCE
→ CONTROL_GUIDANCE
→ REGION_REPAIR
→ PROVIDER_SWITCH
→ HUMAN_COMPOSITION_FIX
```

No Provider call is made by planning.

The plan explicitly records:

- `provider_execution_started=false`
- `paid_execution_authorized=false`
- `automatic_candidate_creation=false`
- `requires_new_prompt_version=true`

This prevents a Human regeneration request from silently becoming paid execution.
