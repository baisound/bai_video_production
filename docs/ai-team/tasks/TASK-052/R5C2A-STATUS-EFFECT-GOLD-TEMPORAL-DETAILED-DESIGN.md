# TASK-052 R5C2A — Status Effect Gold / Review / Temporal Bridge

## Boundary

R5C2A connects R5B Status Effect recognition to held-out Human Gold evaluation,
immutable correction records and the existing R3C temporal state machines. R5C2B
owns the operator-facing Training Studio controls. This unit does not authorize
Provider execution, Production Timeline mutation, Release or Deploy.

## Contract

- Gold coordinates are exact `match/frame/polarity/ordinal` tuples and duplicate
  coordinates or case identities fail closed;
- metrics keep recognition status, identity, polarity, registered source,
  visibility and non-identity abstention separate;
- Human corrections retain original and corrected status/identity together with
  reviewer, reason and provenance instead of overwriting source Evidence;
- the temporal bridge accepts only the exact `StatusEffectDefinition` tuple bound
  to its R3C profile;
- only registry-consistent `IDENTIFIED` observations enter R3C;
- Survivor-scoped effects require an explicit exact slot mapping;
- `UNKNOWN`, hard-negative, contradiction, scope/namespace mismatch, missing exact
  region Evidence, unavailable/overflow segmentation and partially unidentified
  regions never imply disappearance;
- absence is emitted only from an exact, evidenced `EMPTY` region or an evidenced
  segmented region whose every candidate was identity-complete;
- appearance/disappearance confirmation remains owned by the existing R3C profile
  thresholds and state machines.

## Verification

- R3C/R5B/R5C2A focused regression: `26 PASS`;
- TASK-049 DbD/TASK-052 affected regression: `205 PASS`;
- TASK-050/TASK-051 compatibility regression: `186 PASS`;
- compileall and diff-check: `PASS`;
- unresolved Critical/High findings: `0 / 0`.

Synthetic/reference tests do not establish production accuracy. R5C2B retains the
operator UI, while R8/R9 retain held-out real-media and packaged acceptance gates.
