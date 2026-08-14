# TASK-042 — P-V6-4 Critic, Judge and Implementation Authorization

## Reviewed baseline

- Exact fresh-main baseline:
  `c6a5cb108032709615ab99856890d0a3709d7d5d`
- Selected Queue unit: `BVP-TASK-042-P-V6-4-DESIGN / DESIGN_ONLY`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Builder design:
  `p-v6-4-autonomy-current-main-audit-and-builder-design-2026-08-15.md`
- Stable release: `v0.20.1`

## Critic cycle 1 — authority and duplicate-truth review

1. `CRITICAL / CLOSED`: editable SRT could become a second Timeline authority.
   Blueprint v2 frames remain authoritative; SRT imports are proposals with
   explicit conflict/revision flow and never move Scene boundaries.
2. `HIGH / CLOSED`: a Timeline plan could duplicate TASK-041 placement truth.
   It owns intent/ranges and immutable revision history only. Candidate-bound
   placement and Human decisions remain in the one TASK-041 workspace.
3. `HIGH / CLOSED`: ambience could be mislabeled as SE/OTHER and later routed to
   the wrong lifecycle. It receives an additive first-class role through the
   existing TASK-037/041/026 path.
4. `HIGH / CLOSED`: P-V6-4 could implicitly authorize paid narration or audio
   generation. It reuses hashes/planning only; Provider, credential, budget,
   media and Candidate operations remain outside Allowed Files.
5. `HIGH / CLOSED`: plan readiness could be mistaken for Resolve/Cubase write
   authority. Projection and TASK-026 results explicitly keep all external/native
   mutation false.
6. `MEDIUM / CLOSED`: Timeline audio might be made Scene-child-only. Whole/range
   BGM and ambience remain Project Timeline lanes independent of Scene borders;
   narration may be absent and SE remains cue-based.

## Critic cycle 2 — compatibility, recovery and executable-path review

1. `HIGH / CLOSED`: an accepted old review could compile after Blueprint or plan
   drift. Timeline-bound decisions and TASK-026 compilation require exact current
   plan/item/Blueprint/Candidate proof; absent or stale proof fails closed.
2. `HIGH / CLOSED`: extending PlacementReview could rewrite legacy snapshots.
   Timeline binding is optional and omitted for legacy records; load/no-op save
   compatibility is a required gate.
3. `HIGH / CLOSED`: a crash between multi-store writes could create partial
   authority. Plan revision writes only the Timeline store after read-only
   cross-snapshot validation. TASK-041 registration uses its existing single
   durable transaction; no combined partial write is introduced.
4. `HIGH / CLOSED`: millisecond SRT/TASK-014 alignment could accumulate floating
   drift. Canonical data remains integer rational frames; deterministic conversion
   and recorded rounding/conflicts are mandatory.
5. `HIGH / CLOSED`: stretch/crossfade or TASK-010 fade/gain gaps could be silently
   discarded. They remain explicit `EXECUTION_FEATURE_GAP` blockers and cannot
   compile through an incompatible path.
6. `HIGH / CLOSED`: raw narration text, local paths or voice credentials could
   leak into Timeline persistence. Durable records contain typed refs/hashes only
   and security tests inspect snapshots/errors/projections.
7. `MEDIUM / CLOSED`: design completion could imply Product/native release.
   Stable release remains `v0.20.1`; P-V6-5/6, native execution and release work
   remain outside this claim.

Result: `CRITIC_PASS_AFTER_TWO_FIX_CYCLES`; unresolved Critical/High `0 / 0`.

## Final plan

1. Implement exact frame-authoritative Timeline Audio and SRT conflict models.
2. Add first-class AMBIENCE through existing lifecycle roles compatibly.
3. Implement append-only crash-safe Timeline plan history and CAS/restart.
4. Implement application projection and one-shot plan revision commands.
5. Bind current plan items to the one TASK-041 placement review path.
6. Require current binding before TASK-026 compilation; surface feature gaps.
7. Integrate TASK-014 narration proposals without Provider execution.
8. Run focused/full/cross-platform/schema gates and implementation Critic.
9. Synchronize local truth and publish only through a dedicated PR.

## Implementation Allowed Files

The exact Allowed Files in the Builder design section 7 are authorized. No file
outside that list is authorized without a new Builder/Critic decision.

In particular, no Desktop Shell/UI, Provider adapter, Credential vault,
generated-media writer, Resolve/Cubase/native runtime, package/version, Tag,
Release or Deploy change is authorized.

## Judge

`P_V6_4_DESIGN_LOCAL_PASS / HOSTED_DESIGN_PR_AUTHORIZED`

This exact design branch becomes cadence merge `2 / 2` only after hosted `9 / 9`,
exact main verification and cleanup. Control then returns to AUTONOMY.
Implementation remains `NOT_STARTED` until a fresh-main Queue selects
`BVP-TASK-042-P-V6-4-IMPLEMENTATION / IMPLEMENTATION`.
