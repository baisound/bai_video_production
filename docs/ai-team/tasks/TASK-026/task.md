# TASK-026 — Audio Placement & Bed Worker

- Status: `FOUNDATION_IMPLEMENTED / P_AUDIO_1_PRODUCT_PROMOTION_HOSTED_CLOSED`
- Current authority: `HOSTED_CLOSED / FUTURE_SLICE_REQUIRES_FRESH_AUTHORITY`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`

## Current implementation truth

- deterministic exact-frame placement, bounded snap, loop/bed, fade/gain and
  Plan hashing are implemented;
- Human-accepted TASK-041 placement plus LOCKED TASK-037 Candidate can compile
  through the existing binding;
- the V6 binding verifies an exact current TASK-042 Timeline Audio item;
- TASK-010 structural incompatibility remains explicit and no Resolve mutation
  occurs.

## P-AUDIO-1 implemented Product surface

- append-only, checksum-bound `state/audio-placement-history.json` is a
  TASK-043-coordinated Product Project child;
- strict restart parsing and exact Project binding reject unbound, symlinked,
  oversized, duplicate, non-canonical and authority-bearing content;
- Product snapshot derives `CURRENT` / `STALE` from the exact TASK-037,
  TASK-041 and TASK-042 state while retaining prior Evidence;
- prepare/apply accepts only review ID, track intent, bed mode and five exact
  snapshot expectations; Candidate, Asset, Timeline range and Plan are
  re-derived;
- the existing Audio Workspace exposes one explicit `Placement Planを作成`
  action and visible TASK-010 compatibility without starting execution.

P-AUDIO-1 does not generate audio or execute TASK-010, Resolve or Cubase.

## Hosted closure and successor boundary

PR #86 exact head `a907d199a0f70cf05dc24361f512d84cd71163f6`
passed all hosted `9 / 9` checks and merged at exact main
`0e457e697a8099eac885d7edb88d5e77b0eca431`; branch/checkout cleanup and a clean
fresh-main read-back were recorded in the canonical Task Index. The successor
TASK-036 P-UX-1 visual-convergence route is independently governed and is not
reopened by this TASK-026 closure.

## Next gate

Any additional TASK-026 placement or bed capability requires a fresh bounded
Atomic Unit. P-AUDIO-1 closure grants no Provider, paid, audio-generation,
media-write, TASK-010, Resolve or Cubase execution authority.
