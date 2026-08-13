# TASK-013 — Visual Compliance Gate Detailed Design Ver.1.0

- Date: 2026-08-13
- Status: `STRUCTURED_GATE_FOUNDATION_IMPLEMENTED / VISION_PROVIDER_NOT_EXECUTED`
- Source intake: BAI WebMCP / Agent Interface / Visual Compliance Architecture Ver.1.1

## Purpose

Separate the generation Prompt from the acceptance contract. A beautiful candidate is not acceptable when required spatial, orientation, identity or continuity conditions fail.

## Foundation contract

`VisualComplianceContract` stores versioned, explicit checks and identifies critical checks. Left/right-sensitive designs must explicitly declare a coordinate convention rather than relying on ambiguous natural-language "left".

`VisualComplianceGate` consumes **already observed structured inspection facts**. It does not claim to perform object detection, segmentation, depth, pose or Vision-LLM inference itself.

Decision states:

- `ELIGIBLE_FOR_HUMAN_APPROVAL`
- `REJECT`
- `HUMAN_REVIEW_REQUIRED`

There is intentionally no `AUTO_APPROVED` state. Human asset acceptance remains a separate production-control decision.

## Scoring

The report carries the proposed weighting:

- Contract Compliance 50%
- Character Consistency 20%
- Composition 20%
- Aesthetic 10%

The score is diagnostic/ranking metadata only. Any required FAIL rejects the candidate, and a critical FAIL is explicitly marked `critical_pass=false`. Aesthetic score can never override a contract violation.

## Adaptive regeneration

Failure codes are retained in the inspection report. Repeated identical structural failures trigger an escalation recommendation through the existing TASK-040 strategy ladder rather than unlimited text-only Prompt micro-tuning.

This foundation still does not execute a Provider, perform image analysis, regenerate, switch Provider, or approve an Asset.
