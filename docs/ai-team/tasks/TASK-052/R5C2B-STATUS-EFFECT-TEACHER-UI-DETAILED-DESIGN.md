# TASK-052 R5C2B — Status Effect Teacher Operator UI

## Boundary

R5C2B exposes the R5C1 Status Effect Teacher backend through the existing DbD
Training Studio. It adds one workspace-scoped canonical definition registry; it
does not introduce a second visual manifest, recognition index or timeline.
Provider execution, Production Timeline mutation, Release and Deploy remain out
of scope.

## Contract

- each workspace owns `knowledge/status-effect-definitions.json` with schema
  version, monotonic revision and atomic replacement;
- stale writers, duplicate identity, invalid enum/scope/value contracts and
  tampered schema fail closed;
- Training Studio can explicitly register effect ID, polarity, source kind and
  Survivor scope, then selects only registry-backed identity labels;
- positive and negative domains use the exact calibrated HUD Profile regions;
- Perk hard-negatives use the canonical `PERK_ICON/<perk_id>` label and remain
  distinct from Status Effect identity;
- whole-region batch extraction requires an explicit Human confirmation that
  every selected frame contains exactly one target icon; otherwise preview is
  blocked to prevent multi-icon label contamination;
- Safe Visual Learning receives the current registry snapshot and retains its
  preview/receipt/confirm/index validation from R5C1.

## Verification

- R4C2/R5C1/R5C2B/startup focused regression: `17 PASS`;
- TASK-050/TASK-052 affected regression: `193 PASS`;
- TASK-051 compatibility/source gate: `118 PASS`;
- compileall and diff-check: `PASS`;
- unresolved Critical/High findings: `0 / 0`.

No production accuracy is claimed. Held-out real-media Gold/KPI and packaged
acceptance remain R8/R9.
