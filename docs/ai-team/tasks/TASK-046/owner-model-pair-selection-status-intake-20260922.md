# TASK-046 Owner Model-Pair Selection Status Intake

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-046 P-VS-4A / OWNER MODEL-PAIR SELECTION STATUS INTAKE`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Starting HEAD: `6e14ba4ea5962a164ebc450ffa2dd06eff35e63d`
- Owner decision: V2_FRESH e4 SoVITS plus V2_FRESH e15 GPT was selected
- Result: `OWNER_SELECTED / PUBLIC_RELEASE_CONTRACT_PENDING / PRODUCT_USE_GATED`

## Selected pair

- SoVITS source filename: `BAISOUND_TASK097_V2_FRESH_e4_s192.pth`
- SoVITS SHA-256:
  `76a492931f97cd349c6d7d6f04bab4f2442fa9890a5a40708a1d49f919f8e0ff`
- GPT source filename: `BAISOUND_TASK097_V2_FRESH-e15.ckpt`
- GPT SHA-256:
  `4dd990db49d56bdaff6c4988635c46b58f73e1d719297570f0d361184fd60745`

The Owner confirmed that selection was already completed and that the supplied
BAISOUND_VOICE_MODEL information pack records that decision. The model files
and hashes were independently observed during the preceding TASK-097
public-safe completion intake.

## Boundary

- This records the TASK-046 P-VS-4A Owner selection decision.
- It does not claim that BAISOUND_VOICE_MODEL `v2.0.0` modernization or public
  release is complete; the shared pack says that work remains `IN_PROGRESS`.
- Planned public filenames remain informational until the Public Repository's
  completion commit/release contract fixes them.
- It does not install, load, infer with, promote into BVP runtime, or publish the
  selected pair.
- TASK-014 narration generation, TASK-041 audio review, Asset adoption, Product
  Provider/Model integration, Release, Deploy and Production remain separate.

## Review

- High: treating the information pack alone as authority would violate its
  information-only boundary. Closed by binding the status change to the Owner's
  direct confirmation in this thread.
- High: selection could be confused with public release or Product activation.
  Closed by separate `PUBLIC_RELEASE_CONTRACT_PENDING` and
  `PRODUCT_USE_GATED` states.
- Medium: public renamed files could be mistaken for finalized identities.
  Closed by retaining the exact selected internal filenames and verified hashes
  until the external release contract is final.
- Final findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Judge: `ACCEPT / OWNER_SELECTION_STATUS_SYNC_ALLOCATED`.

## Allowed files

- this document and its bounded Evidence;
- `docs/ai-team/tasks/TASK-046/task.md`;
- `docs/ai-team/tasks/TASK-097/task.md`;
- bounded TASK-046/TASK-097 lines in `docs/ai-team/current-state.md` and
  `docs/ai-team/task-index.md`.

No Product source/schema/test, model, media, runtime, package, installer,
Product version or unrelated Task file may change.
