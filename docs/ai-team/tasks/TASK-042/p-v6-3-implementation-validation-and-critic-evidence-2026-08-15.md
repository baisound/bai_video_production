# TASK-042 — P-V6-3 Implementation Validation and Critic Evidence

## Authority and Source of Truth

- Product Authority: `BAI VIDEO PRODUCTION`
- Design PR: `#58`, exact head `0067fcc8e306a1799ccc7afeeae2638b9bb19e3b`
- Design hosted checks: `9 / 9 PASS`
- Design exact main merge: `c78ed0141b0849b3a5d1b2229b87c320697b4980`
- Design remote branch and dedicated clone: removed
- Fresh implementation baseline: `c78ed0141b0849b3a5d1b2229b87c320697b4980`
- Handoff status: `HANDOFF_STALE`; current clean checkout selected as Source of Truth
- Handoff manifest checksum: `sha256:4673aac75ef94e6ed26ba3b5d61a82e71e4b1d447904c40b24c20d058be45329`
- Bootstrap checksum: `sha256:372f3851e24630d6a8873ab9d131b8ec37ed817c2abbfcd7f5dd0d6b6aaebf2c`
- Queue selected: `BVP-TASK-042-P-V6-3-IMPLEMENTATION / IMPLEMENTATION`
- Queue checksum: `sha256:7632d2bbe88c9549f066ea6f3e1b039ba7c6a80c53144a9480ab0e30e8be894e`
- P-V6-4 remained dependency-waiting; Native H3 and OS TASK-017 remained task-locally parked
- System blocked: `false`

## Implemented scope

1. Corrected the durable TASK-027 Queue validator to accept the exact Blueprint
   v2 `WORLD_LOCKED_CURRENT_CANDIDATE` proof with non-null reference, Slot,
   Candidate and Asset identities. A real v2 prepare/apply/persist/restart/reload
   test now covers the formerly broken path.
2. Added immutable Visual Prompt compilation for structured WORLD/BEFORE/NOW/
   TRACE/PHYSICS/PLACE/OWNER and visual intent, three private JA/JA/EN body
   layers, optional negative Prompt, audio intents, generation flags, WORLD LOCK,
   Provider profile/route/capability and input Asset identities.
3. Public/durable compilation contains refs and hashes only. Raw bodies remain
   in the in-memory result and are absent from Prompt Registry, Queue, Evidence,
   status and exceptions.
4. Extended the one TASK-040 `PromptEntity` with an optional typed compilation
   binding. Legacy Prompt output shape is unchanged; compiled Prompt requires
   exact runtime-English, input-Asset, Provider and Scene/Slot identity. Existing
   prepare/apply/CAS/restart is reused.
5. Added deterministic, read-only Provider -> compatible Model projection. It
   lists every configured route and exact readiness blockers without credential
   refs, endpoints, settings, secrets or Provider probes.
6. Added append-only `QUICK_INTENT` authority with IMAGE, START_END, VIDEO and
   AUDIO cardinality, exact compiled Prompt/route/decision/cost/rights/snapshot
   binding and typed references. It contains no Approved Plan or Human GO claim.
7. Added strict bounded Quick snapshot persistence with checksum, append chain,
   serialized CAS, one-shot confirmation, restart status and foreign-project/
   unknown-field rejection. Apply writes only the Quick intent store.
8. Quick target/reference validation reuses exact TASK-037 Slot/Candidate/
   LOCK/CURRENT truth. FILE authority is rejected until secure ingest has
   converted it to an internal Asset reference.
9. Added read-only adoption projection over exact TASK-040 Attempt, TASK-037
   Candidate/Slot and TASK-038 Audit/Human decision truth. It progresses only
   through `OUTPUT_NOT_REGISTERED`, `AUDIT_REQUIRED`, `ACCEPT_REQUIRED`,
   `LOCK_REQUIRED` and `PRODUCTION_ADOPTED`.
10. Provider execution, credential resolution, paid authorization, media write,
    Candidate/Audit/LOCK mutation, native operation, Tag, Release and Deploy are
    not implemented or started by this slice.

## Validation

- Final P-V6-3 focused gate: `31 / 31 PASS`
- Prompt/Queue legacy compatibility and focused recovery gate: `53 / 53 PASS`
- Final Windows full regression: `987 / 987 PASS`; one intentional non-Windows skip
- Windows compileall: `PASS`
- WSL2 Ubuntu compileall through `/mnt/d`: `PASS`
- Context Cost checksum: `PASS`
- `git diff --check`: `PASS`
- Provider/paid/native/media/Candidate/Audit/Lock/Release operations: all `false`

## Implementation Critic cycle 1

1. `HIGH / CLOSED`: a compiled binding initially trusted a shape-valid manifest
   without recomputing its compilation checksum. `from_manifest` now verifies
   the canonical checksum before accepting any binding.
2. `HIGH / CLOSED`: Quick references could initially differ from the immutable
   Prompt compilation input hashes. Application validation now requires exact
   ordered Asset checksum equality.
3. `HIGH / CLOSED`: a `FILE` row could carry an Asset label without canonical
   ingest proof. Quick Application rejects `FILE` authority and requires prior
   secure ingest/internal Asset representation.
4. `MEDIUM / CLOSED`: START_END could contain repeated START or END roles under
   different row IDs. Duplicate frame roles now fail closed.

## Implementation Critic cycle 2

1. `HIGH / CLOSED`: compiled Prompt integration had store coverage but not the
   real TASK-040 prepare/apply/restart path. The final focused gate now exercises
   that exact Application transaction.
2. `HIGH / CLOSED`: route readiness could be inferred from credential or catalog
   presence alone. READY is the conjunction of enabled/mode, declared and
   catalog capability, adapter, availability and credential predicates.
3. `HIGH / CLOSED`: Quick could accidentally reuse Approved Plan/Human GO
   fields. Strict intent/store shapes require `authority_kind=QUICK_INTENT` and
   fix both claims false; unknown fields fail closed.
4. `HIGH / CLOSED`: adoption could mutate canonical stores. The projection takes
   registries read-only and exposes explicit all-false mutation flags.
5. `MEDIUM / CLOSED`: implementation success could imply Provider/native or
   Product release completion. Stable release remains `v0.20.1`; P-V6-4..6 and
   Native H3 remain outside this claim.

Result: `CRITIC_PASS_AFTER_TWO_FIX_CYCLES`; unresolved Critical/High `0 / 0`.

## Local Judge and next Gate

`P_V6_3_IMPLEMENTATION_LOCAL_PASS / HOSTED_IMPLEMENTATION_PR_AUTHORIZED`

This implementation is cadence merge `2 / 2` only after its exact head passes
all GitHub checks, merges to main, exact merge SHA is verified and remote branch
plus dedicated clone cleanup completes. Control then returns to fresh-main
AUTONOMY before a closure sync or P-V6-4 selection. Stable release remains
`v0.20.1`.
