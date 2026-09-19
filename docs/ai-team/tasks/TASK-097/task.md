# TASK-097 — TASK-046 P-VS-3B/4A Local GPT-SoVITS Iteration Status Unit

- Status: `DATASET_V2_RECORDED_VERIFY_PASS / INDEPENDENT_REVERIFY_PENDING / FIRST_RUN_REPORTED_COMPLETE_NOT_INDEPENDENTLY_VERIFIED / SECOND_RUN_NOT_STARTED`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Owner routing: `2026-09-19` — the second GPT-SoVITS learning run continues with local ChatGPT
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
12 candidate pairs. That run is not independently reverified by this repository.
Final pair selection remains a Human decision. The second learning run has not
started and is routed to local ChatGPT outside the TASK-098 Codex integration lane.

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

Local ChatGPT and the Owner perform the second learning run. A later bounded
status intake may independently reverify public-safe manifest identity and record
Human-selected results without importing private bodies into this repository.
