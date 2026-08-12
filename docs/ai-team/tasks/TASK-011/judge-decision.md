# TASK-011 — Judge Decision

- Date: 2026-08-12
- Decision: `PASS_FOR_ARTIFACT_QA_IMPLEMENTATION_NATIVE_RENDER_GATE_REQUIRED`
- Implementation authority: YES, bounded by the Owner instruction and Detailed Design.
- Merge/release authority: NO automatic authority.
- Native validation claim: PROHIBITED until real Windows/external-application Evidence passes.

## Conditions

1. Protected `main` remains untouched directly.
2. Full regression must stay green.
3. New canonical schemas and packaged copies must match.
4. Unified Desktop integration remains explicitly `INTEGRATION_DESIGNED` unless actual Shell wiring is separately implemented and validated.
5. External writes require explicit user authorization and fail closed on ambiguous state.
