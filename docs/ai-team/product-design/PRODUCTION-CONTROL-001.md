# PRODUCT-CONTROL-001 — Production Control Plane Architecture
## Planning / Asset / Generation / Audit / Human Approval / Knowledge

- Version: 1.0
- Date: 2026-08-12
- Status: DESIGN_REGISTERED / ROADMAP_INPUT
- Application architecture: PRODUCT-ARCH-001
- Runtime implementation authorization: not granted by this document

## 1. Purpose

BAI Video Production requires a persistent control plane that connects creative intent to actual production Assets and preserves why each result was generated, accepted, rejected, regenerated, reused or superseded.

## 2. Canonical traceability

The control plane is not considered ready until the Product can trace:

`Plan -> Scene -> Asset Slot -> Generation Job -> Candidate -> Audit -> Human Decision -> Locked Asset`

and can trace the reverse path from a locked Asset back to the production intent and Evidence that justified it.

## 3. Human authority

Final creative/product acceptance is Human authority.

AI may detect, score, compare, propose Failure Codes, draft Improvement Prompts, recommend regeneration and identify alternate use.

AI may not silently convert a Human reject into accept, clear a Human override, unlock an Asset, replace a locked Asset after upstream change, authorize high-cost generation, or mutate an external NLE without its separate authorization gate.

## 4. Core invariants

1. regeneration creates a new Candidate;
2. accepted/locked bytes are immutable;
3. upstream changes mark affected dependents STALE;
4. STALE does not silently regenerate or replace;
5. REJECT does not imply immediate physical delete;
6. DIRECT_CONTINUATION reuses exact previous End Asset identity/hash;
7. VFX visual/audio evaluation is separable;
8. Prompt bodies are not duplicated into general Evidence by default;
9. Human Final Authority outranks AI review;
10. the final Product remains one unified Desktop Application.
