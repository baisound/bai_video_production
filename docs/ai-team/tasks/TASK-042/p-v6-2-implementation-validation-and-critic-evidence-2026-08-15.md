# TASK-042 — P-V6-2 Implementation Validation and Critic Evidence

## Authority and Source of Truth

- Product Authority: `BAI VIDEO PRODUCTION`
- Design PR: `#55`, exact head `0b17e7b632c8326dc0882cb03082d1c2620139d5`
- Design hosted checks: `9 / 9 PASS`
- Design exact main merge: `6a4a6a5e28705950d0ba6457c38d9b8d119fe944`
- Design remote branch and dedicated clone: removed
- Fresh implementation baseline: `6a4a6a5e28705950d0ba6457c38d9b8d119fe944`
- Handoff Bootstrap: `HANDOFF_STALE`; current clean main selected as Source of Truth
- Bootstrap checksum: `sha256:f65f162bef2dfc44e29f92b9d5d08656a5ae16ea4c82aee6575896950db21e4c`
- Bootstrap manifest checksum: `sha256:9681e75bc640c0fe6ff9bc783613af011bdbdcd7574859d9fcbc90d2df50de02`
- Queue selected: `BVP-TASK-042-P-V6-2-IMPLEMENTATION / IMPLEMENTATION`
- Queue checksum: `sha256:9f3d976fa7b1f2379e4ecdfb07d00549ad323734d523fc4cae144875f937bebf`
- TASK-013 Native H3 and OS TASK-017 remained task-locally parked

## Implemented scope

1. Added the explicit additive Slot roles `CHARACTER_REFERENCE`,
   `SPACE_REFERENCE` and `COMPOSITION_REFERENCE`; historical Slot values and v1
   snapshots remain unchanged and unknown values still fail closed.
2. Added a stateless Blueprint v2 WORLD LOCK projection over the exact Approved
   Plan and current TASK-037 registry. It verifies deterministic frame path,
   project, role, Slot, locked Candidate, lifecycle, Asset ID/checksum and
   CURRENT state without creating a second store or inferring Lock from GO.
3. Enabled v2 Production Control compilation/installation only after WORLD LOCK
   PASS. Reference Slots are reused; only Scene output Slots and deterministic
   dependency edges are added.
4. Added Candidate -> Scene edges so existing Slot -> Candidate and Scene ->
   output relationships propagate STALE transitively without regeneration.
5. Preflighted complete install on an isolated registry copy. Any collision or
   cycle leaves the caller-visible/persisted registry unchanged.
6. Extended Planning prepare/apply/restart and Approved Plan Trace for v2 while
   keeping v1 report shape compatible. Confirmations remain one-shot and bind
   exact Proposal plus Production snapshot checksums.
7. Added restart-visible `WORLD_LOCK_REQUIRED` and `WORLD_LOCK_STALE` states;
   they expose recovery/Human resolution instead of crashing or silently fixing.
8. Enabled Approved Plan generation admission only after exact current WORLD
   LOCK and automatically included every v2 reference Slot in required inputs.
9. Changed v2 Queue proof from GO-only/hash selection to exact deterministic
   frame path + role + Slot + Candidate + Asset/checksum proof. Repeated hashes,
   role mismatch, missing/stale/unlocked state and extra/missing GO paths fail
   closed. V1 Queue behavior remains compatible.
10. Reused TASK-039 non-overridable DIRECT exact identity and existing recovery
    interlocks. No Provider, paid, credential, native, media or release operation
    was started.

## Validation

- Slot enum / WORLD LOCK foundation: `21 / 21 PASS`
- v2 Plan / Trace / Planning and v1 compatibility: `39 / 39 PASS`
- v2 Generation / Queue and v1 generation compatibility: `27 / 27 PASS`
- DIRECT continuity / STALE / restart / cross-store regression: `49 / 49 PASS`
- post-Critic compatibility/recovery/role focused gate: `29 / 29 PASS`
- Windows full regression before Critic hardening: `958 / 958 PASS`; one intentional skip
- Windows full regression after Critic hardening: `960 / 960 PASS`; one intentional skip
- Provider execution, paid authorization, automatic regeneration, media write,
  native mutation, physical delete, Tag, Release and Deploy: all `false`

## Implementation Critic cycle 1

1. `HIGH / CLOSED`: adding `world_lock_binding_count: 0` to every v1 Trace would
   change its historical output. The field is emitted only for v2; v1 output
   shape/checksum behavior remains unchanged.
2. `HIGH / CLOSED`: a stale installed WORLD LOCK initially caused strict Trace
   validation to abort the whole Planning snapshot. Planning now reports
   `WORLD_LOCK_STALE`, exact blockers and `recovery_required=true` without
   mutating or inventing recovery.
3. `HIGH / CLOSED`: Queue verified Slot/Candidate/Asset state but initially
   relied on upstream projection for role correctness. It now independently
   requires the exact `CHARACTER/SPACE/COMPOSITION_REFERENCE` Slot role.

## Implementation Critic cycle 2

1. `HIGH / CLOSED`: an install collision could partially mutate a caller-owned
   in-memory registry even when no snapshot was saved. The complete graph is
   built and validated on a deep isolated copy, then atomically adopted only
   after every operation passes.
2. `HIGH / CLOSED`: a caller could pass an empty v2 required-input list to the
   Approved Plan admission service. The service now adds every exact WORLD LOCK
   reference Slot itself, so callers cannot omit them.
3. `MEDIUM / CLOSED`: equal Asset hashes on two frame paths could be resolved by
   ordering. V2 Queue instead returns an explicit ambiguity failure and defers
   typed Prompt-role selection to P-V6-3.
4. `MEDIUM / CLOSED`: implementation success could imply release/native
   completion. Stable release remains `v0.20.1`; no P-V6-3, Provider/native,
   Tag, Release or Deploy claim is made.

Result: `CRITIC_PASS_AFTER_TWO_FIX_CYCLES`; unresolved Critical/High `0 / 0`.

## Local Judge and next Gate

`P_V6_2_IMPLEMENTATION_LOCAL_PASS / HOSTED_IMPLEMENTATION_PR_AUTHORIZED`

The implementation PR is the first merge of the next two-merge cadence. P-V6-2
is not hosted-closed until this exact head passes all GitHub checks, merges to
main, the exact merge SHA is verified, and branch/clone cleanup completes. A
fresh-main bounded Closure Sync may then record hosted truth as cadence merge
`2 / 2`; after its cleanup, control returns to AUTONOMY before P-V6-3 or another
unit is selected.
