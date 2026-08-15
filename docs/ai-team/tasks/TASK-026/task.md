# TASK-026 — Audio Placement & Bed Worker

- Status: `FOUNDATION_IMPLEMENTED / P_AUDIO_1_PRODUCT_PROMOTION_IMPLEMENTATION_LOCAL_PASS / HOSTED_IMPLEMENTATION_PENDING`
- Current authority: `OWNER_DIRECTED_PRODUCT_PROMOTION_IMPLEMENTATION`
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

## Owner P0 immediately after hosted closure

The V6.1.1 HTML mock is the canonical visual and interaction design authority.
Deviation between that mock and the packaged EXE is an absolute NG. After this
implementation reaches all-green `main` and branch/checkout cleanup, the next
unit is `TASK-036 P-UX-1 / V6.1.1 MOCK-TO-EXE VISUAL CONVERGENCE`, before any
further user-facing feature surface is added. This TASK-026 unit does not claim
that visual convergence.

## Next gate

Implementation PR -> hosted `9 / 9` -> exact main merge -> branch/checkout
cleanup -> fresh-main TASK-036 P-UX-1 Builder/Critic and implementation.
