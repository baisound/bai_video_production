# TASK-041 Audio Completion PASS Contract R22

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-041`

Contract identity: `TASK041_AUDIO_COMPLETION_VERIFIED_CURRENT_PASS_CONTRACT_R22_V1`

Bound design: `TASK074-R22-RESTART-SPLIT-AND-REACHABLE-CONTAINMENT-V1`

## PASS boundary

The sole positive type is `Task041AudioCompletionVerifiedCurrentPassV1`. A
class-only private surface precedes the TASK-036 binder and exposes no issuer or
positive fixture. A later TASK-041 owner reader may mint only from one atomic
currentness snapshot for the same Project, timeline, policy and latest ledger
head containing:

- selected TASK-041 `AudioMediaReviewCurrentRead` plus exact
  `ExternalAudioReviewReceiptBinding`;
- selected TASK-026 `AudioPlacementCurrentRead`;
- TASK-014 `Task014NarrationPublicationCurrentReadV1` for every narration item,
  or an exact empty set only for a current no-narration plan;
- one exact TASK-035 finishing branch;
- TASK-041 `AudioCompletionLatestObservation` plus an owner-store readback that
  proves the latest intact, unforked, predecessor-correct entry.

Every narration current read must transitively prove the exact TASK-075 success
predicate: `outcome=SUCCESS`, `terminal_stage=RESULT_VERIFIED`, empty reasons,
48000/mono/PCM_S24LE, positive frame count, one child/generation/waveform,
exact non-null waveform/sink/output identities, exact Job terminal and TASK-074
retirement. A containment/partial-truth publication read is always non-PASS.

Finishing uses only canonical `FinishingRequirement`:

- `REQUIRED`: current owner-authenticated TASK-035 `AudioRoundTripCurrentRead`;
- `OPTIONAL`: that read or sealed owner-issued
  `Task035OptionalFinishingSkipCurrentV1` for the exact Project/item/policy;
- `NOT_APPLICABLE`: exact null and no finishing/skip coordinate.

The optional skip is issued only from an owner-selected SKIP decision and exact
store snapshot proving no current selected manifest. It binds semantic manifest
key, store revision/snapshot, decision revision and latest head. Its closed
non-PASS outcomes include each of `missing`, `stale`, `revoked`, `foreign`,
`forked`, `ambiguous` and `broken-chain`; none aliases another.

Candidate/R0/R1, mapping, boolean, absence, NOT_FOUND, public projection, caller
self-hash, equal fields/hash and any noncurrent input remain non-PASS. The exact
private PASS is consumed only by the TASK-036 exclusive binder.

## Acceptance mechanism

This file is immutable. After exact R22 review PASS, only a separately allocated
TASK-041 owner writer may issue
`docs/ai-team/tasks/TASK-041/audio-completion-r22-owner-acceptance.json` under
R22's exact envelope rules.

Until that envelope verifies, contract acceptance, source, ledger PASS,
TASK-036 Gate PASS and every audio/native/provider/Release/Deploy/Production
authority are false.
