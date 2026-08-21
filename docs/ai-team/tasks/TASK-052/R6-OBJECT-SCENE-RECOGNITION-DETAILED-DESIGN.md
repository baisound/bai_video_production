# TASK-052 R6 — Tier 3 Object / Scene Recognition

## Boundary

R6 introduces a deterministic, fail-closed classifier for caller-provided bounded
scene crops. It covers pallets, windows, map features, main buildings and tiles as
objects/scenes. It does not treat object visibility as an action event: recognizing
a pallet never means `PALLET_DROP`, and recognizing a window never means
`WINDOW_VAULT`.

Full-frame localization, expensive selective Vision escalation and held-out
real-media accuracy remain R7/R8. Provider execution, Production Timeline,
Release and Deploy are not authorized.

## Canonical ownership

| Object/scene kind | Canonical knowledge owner | Map binding |
|---|---|---|
| `PALLET` | `MECHANIC` | optional |
| `WINDOW` | `MECHANIC` | optional |
| `MAP_FEATURE` | `MAP` | required |
| `MAIN_BUILDING` | `MAP` | required |
| `TILE` | `TILE` | optional |

Kind/owner disagreement, missing required map identity, duplicate object identity,
unregistered reference labels and malformed hard-negatives fail closed.

## Recognition contract

- labels use `OBJECT_SCENE/<KIND>/<object_id>`;
- hard-negatives use `OBJECT_SCENE/HARD_NEGATIVE/<negative_id>`;
- an admitted index requires both identity and hard-negative coverage;
- low-confidence or ambiguous matches return `ABSTAINED`;
- exact hard-negative matches return `HARD_NEGATIVE`;
- map-bound identity observed under another/unknown map returns `CONTRADICTION`;
- output persists frame, ROI, candidate list, crop digest and Evidence reference;
- `event_claim_allowed` is permanently false in this layer.

## Verification and remaining truth

- Object/scene + shared classifier/R5B focused regression: `18 PASS`;
- TASK-049 DbD/TASK-052 affected regression: `214 PASS`;
- compileall and diff-check: `PASS`;
- unresolved Critical/High findings: `0 / 0`.

Synthetic references establish contract behavior only. Pallet/window/map/scene rows
remain `PARTIAL` until R7 supplies a bounded proposal/escalation route where useful
and R8 supplies held-out Human Gold metrics or an explicit Owner defer decision.
