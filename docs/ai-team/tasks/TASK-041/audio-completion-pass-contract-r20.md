# TASK-041 Audio Completion PASS Contract R20

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-041`

Contract identity: `TASK041_AUDIO_COMPLETION_VERIFIED_CURRENT_PASS_CONTRACT_R20_V1`

Bound design: `TASK074-R20-RESERVATION-AND-TAGGED-TERMINAL-CLOSURE-V1`

## PASS boundary

The sole positive type is `Task041AudioCompletionVerifiedCurrentPassV1`. A
contract-only private class surface precedes the TASK-036 binder and exposes no
issuer or positive fixture. The later TASK-041 owner reader may mint only after
one atomic currentness snapshot closes all of the following for the same
Project, timeline, policy and latest ledger head:

- TASK-041 `AudioMediaReviewCurrentRead` for the selected review decision plus
  exact `ExternalAudioReviewReceiptBinding`;
- TASK-026 `AudioPlacementCurrentRead` for the selected placement compilation;
- TASK-014 `Task014NarrationPublicationCurrentReadV1` for every narration item,
  or an exact empty narration set only when the current plan contains none;
- the exact TASK-035 finishing branch below;
- TASK-041 `AudioCompletionLatestObservation` plus an owner-store readback that
  proves the latest intact, unforked, predecessor-correct entry.

Finishing uses only canonical `FinishingRequirement` values:

- `REQUIRED`: TASK-035 `AudioRoundTripCurrentRead` must be `CURRENT`, owner
  authenticated and currentness verified for the exact manifest/session plan;
- `OPTIONAL`: either that same current read or sealed owner-issued
  `Task035OptionalFinishingSkipCurrentV1` for the exact Project/item/policy;
- `NOT_APPLICABLE`: finishing coordinate is exact null and no finishing receipt
  or skip type is accepted.

The optional skip is issued only by a TASK-035 owner reader from an
owner-selected `SKIP` decision plus an exact store snapshot proving no current
selected manifest. It binds semantic manifest key, store revision/snapshot,
decision revision and latest head. It is private, sealed, nonserializable and
returns distinct missing/stale/revoked/foreign/ambiguous/broken-chain outcomes.

Candidate/R0/R1, mapping, boolean, absence, NOT_FOUND, public projection, caller
self-hash, equal fields/hash and any noncurrent input remain non-PASS. The
private PASS is consumed only by the TASK-036 exclusive binder.

## Acceptance mechanism

This file is immutable. After exact R20 review PASS, only a separately allocated
TASK-041 owner writer may issue
`docs/ai-team/tasks/TASK-041/audio-completion-r20-owner-acceptance.json` under
R20's exact envelope rules.

Until that envelope verifies, contract acceptance, source, ledger PASS,
TASK-036 Gate PASS and every audio/native/provider/Release/Deploy/Production
authority are `false`.
