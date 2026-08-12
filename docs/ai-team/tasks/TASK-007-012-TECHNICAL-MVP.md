# TASK-007 -> TASK-010 -> TASK-011 -> TASK-012 Technical MVP Vertical Slice

- Date: 2026-08-12
- Base: v0.19.0
- Status: IMPLEMENTED / 462 OF 462 AUTOMATED PASS / NATIVE GATES REMAIN

```text
TASK-024 review-only candidates
  -> TASK-007 human-approved Edit Plan
  -> TASK-022 exact Timeline mapping
  -> TASK-010 BAI_AUTO Resolve assembly
       + optional TASK-006 reviewed subtitle handoff
       + generic audio placement execution only (TASK-026 owns advanced audio placement logic)
  -> TASK-011 rendered-artifact QA / loudness
  -> TASK-012 EDITOR_WORK / Cubase round-trip
```

## Global invariants

- No score becomes destructive authority.
- No human-owned Timeline is mutated.
- Source FPS and Timeline FPS are distinct contracts.
- External writes require explicit authorization.
- Hash marker makes successful assembly replay idempotent; ambiguous partial state fails closed.
- QA precedes handoff; handoff rechecks the render hash.
- Final Product UX remains one `BAI Video Production.exe`; this slice does not claim Shell integration.
- Native Windows/Resolve/Cubase behavior is a separate Evidence gate, never inferred from unit tests.
