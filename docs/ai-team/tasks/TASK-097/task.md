# TASK-097 — TASK-046 P-VS-3B/4A Local GPT-SoVITS Iteration Status Unit

- Status: `DATASET_V2_RECORDED_VERIFY_PASS / INDEPENDENT_REVERIFY_PENDING / FIRST_RUN_REPORTED_COMPLETE_NOT_INDEPENDENTLY_VERIFIED / SECOND_RUN_COMPLETE_PUBLIC_SAFE_VERIFIED / OWNER_SELECTED_V2_FRESH_E4_E15 / PUBLIC_RELEASE_CONTRACT_PENDING`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Owner routing: `2026-09-19` local-ChatGPT second run; Owner completion notification and formal Receipt received by `2026-09-22`
- Canonical owner: `TASK-046 P-VS-3B Dataset revision / P-VS-4A Training and ModelCandidate`
- Relationship to TASK-098: `SEPARATE_LANE / SUBORDINATE_STATUS_EXECUTION_UNIT / STATUS_DEPENDENCY_ONLY`

TASK-097 does not create a second Voice Dataset, Training job, ModelCandidate or
approval authority. TASK-046 remains canonical for every such revision and
decision. This unit records public-safe local execution status so the separate
TASK-098 integration lane does not misreport or repeat private voice work.

## Current public-safe state

- Dataset ID: `task097-baisound-signature-streaming-gptsovits-v2-20260919`
- Schema: `bvp.task097.gpt-sovits-signature-training-dataset.v1`
- Accepted / rejected: `172 / 18`
- Deterministic split: `train=154 / validation=9 / test=9`
- Accepted duration: `1203.70327 seconds`
- Recorded build QC: `PASS / 0 errors / 0 warnings`
- Recorded verification: `PASS`
- Manifest SHA-256: `96c21753c789e20536ce7a190f7c69c7740fda604b9dad643c06678f7300ce51`
- Training flag: `false`

The recorded verification belongs to the supplied local handoff Evidence. It is
not relabelled as a fresh independent repository verification. Private source
paths, transcript bodies and audio are intentionally absent from this record.

## Model optimization state

The supplied handoff reports the first GPT-SoVITS learning run complete with 206
clips, 1965.79 seconds, four SoVITS candidates and three GPT candidates, yielding
12 candidate pairs. That earlier run remains not independently reverified by
this repository.

The separately authorized second dual-V2 run is complete. Its formal completion
Receipt and final run-state agree on `DUAL_V2_TRAINING_COMPLETE`, all four
sequential WARM/FRESH SoVITS/GPT phases are `COMPLETE`, and the test set was not
accessed. Independent public-safe intake observed 14 exported checkpoint files:
V2_WARM and V2_FRESH each contain four SoVITS plus three GPT candidates. Their
filenames, sizes and SHA-256 identities are recorded in the bounded Evidence.
The Owner clarified on `2026-09-22` that validation/selection was already
completed and selected V2_FRESH e4 SoVITS plus V2_FRESH e15 GPT. TASK-046 records
that Owner decision. Public Repository release finalization, BVP runtime
admission and model promotion remain separate; selection does not activate the
model.

No BAISOUND-specific FasterWhisper fine-tuning is complete. GPT-SoVITS voice
generation tuning, FasterWhisper inference integration and any future Whisper
training are separate responsibilities and must not be reported as one activity.

## Gates and prohibitions

- no Codex-started training or GPU run under TASK-098;
- no automatic final voice-pair selection or model promotion;
- no new Dataset/Training/ModelCandidate authority outside TASK-046;
- no Dataset adoption beyond the exact Human-authorized TASK-046 local lane;
- no private audio, transcript body, secret, or private absolute path in public Evidence;
- no model/runtime download, paid execution, Release, Deploy or Production activation
  without its exact gate.

## Next action

Wait for the BAISOUND_VOICE_MODEL Public Repository modernization to finalize
the `v2.0.0` release contract and public filenames. BVP consumer integration,
installation and runtime use require their own later bounded review.
