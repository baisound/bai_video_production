# TASK-026 — Audio Placement & Bed Worker

- Status: `FOUNDATION_IMPLEMENTED / P_AUDIO_1_PRODUCT_PROMOTION_DESIGN_LOCAL_PASS / HOSTED_DESIGN_PENDING`
- Current authority: `OWNER_DIRECTED_PRODUCT_PROMOTION_DESIGN`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`

## Current implementation truth

- deterministic exact-frame placement, bounded snap, loop/bed, fade/gain and
  Plan hashing are implemented;
- Human-accepted TASK-041 placement plus LOCKED TASK-037 Candidate can compile
  through the existing binding;
- the V6 binding verifies an exact current TASK-042 Timeline Audio item;
- TASK-010 structural incompatibility remains explicit and no Resolve mutation
  occurs.

## Current missing Product surface

There is no durable Project-bound placement-plan history, restart/currentness
projection or explicit unified Shell prepare/apply action. P-AUDIO-1 is the
bounded promotion of the existing foundation into that Product surface. It
does not generate audio or execute TASK-010, Resolve or Cubase.

## Next gate

Design PR -> hosted `9 / 9` -> exact main merge -> branch/checkout cleanup ->
fresh-main implementation reselection.
