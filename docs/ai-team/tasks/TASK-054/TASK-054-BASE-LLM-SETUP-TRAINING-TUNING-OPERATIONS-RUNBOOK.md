# TASK-054 — Base LLM Setup, Training, Tuning and Operations Runbook

Status: `PROCEDURE DESIGN / ALL EXECUTION HUMAN-GATED`

This Runbook is an executable future contract, not proof that commands or model
operations have run. Values under `profiles/` and lockfiles must exist and be
reviewed before use. Never paste credentials into a command, profile or report.

## 1. Base-model policy

The first pilot uses an instruction-tuned, open-weight model in the approximate
`7B–14B` class with:

- strong Japanese and strict JSON performance;
- context capacity at least the admitted TASK-054 envelope budget;
- an explicit commercial-use-compatible license and redistribution decision;
- pinned weights/tokenizer/config digests;
- no arbitrary remote-code execution requirement;
- PEFT/LoRA and bounded local inference support;
- measurable abstention and citation behavior;
- fit within approved GPU/RAM/storage/time/power budgets.

No vendor/model name is permanently canonical. `BaseModelCandidateProfile`
records the exact candidate, revision, license, digests and evaluation. Selection
is evidence-based among baseline candidates; popularity is not admission.

Full-model fine-tuning is not the first pilot. Default progression:

```text
Prompt + RAG baseline
 -> SFT with LoRA/QLoRA
 -> optional preference tuning only with sufficient Human pairs
 -> no full fine-tune unless LoRA limits are proven and separately authorized
```

## 2. Required future files

```text
config/task054/base-model-candidates.yaml
config/task054/training-profile.yaml
config/task054/evaluation-policy.yaml
requirements/task054-training.lock
schemas/task054/*.schema.json
datasets/task054/<dataset-id>/<revision>/manifest.json
artifacts/task054/<binding-id>/<revision>/artifact-manifest.json
reports/task054/<run-id>/
```

All paths in persisted manifests are logical/relative refs. Host absolute paths
exist only in local runtime configuration and are excluded from portable Evidence.

## 3. Environment setup procedure

### Gate A — preflight approval

Before commands:

1. confirm Dataset rights/consent scope;
2. confirm model license and download authority;
3. confirm target WSL2/local runtime, storage root and encryption policy;
4. confirm GPU/RAM/disk/power/time ceilings;
5. confirm no other GPU training/native job owns the device;
6. record Owner authorization receipt for download/training separately.

### Host/WSL probe

```powershell
wsl.exe --status
wsl.exe -d Ubuntu -- bash -lc 'python3 --version'
wsl.exe -d Ubuntu -- bash -lc 'nvidia-smi'
wsl.exe -d Ubuntu -- bash -lc 'df -h /home/baisound'
```

Expected: exact OS/driver/GPU/Python/storage Evidence. Absence is
`BLOCKED_RUNTIME`, not permission to install silently.

### Isolated runtime

Future authorized procedure:

```bash
python3 -m venv /home/baisound/.venvs/bvp-task054-training
source /home/baisound/.venvs/bvp-task054-training/bin/activate
python -m pip install --require-hashes -r requirements/task054-training.lock
python -m pip check
python -m bvp_task054 environment probe --output reports/task054/<run-id>/environment.json
```

Rules:

- dependency versions and hashes come only from reviewed lockfiles;
- never install from an unpinned Git revision or enable model `trust_remote_code`;
- cache/download roots are explicit, bounded and outside Git;
- environment manifest records versions/digests, not secrets;
- failure leaves the existing Product runtime untouched.

### Model acquisition

```bash
python -m bvp_task054 model acquire \
  --candidate config/task054/base-model-candidates.yaml#<candidate-id> \
  --authorization-ref authorization://<receipt-id> \
  --destination-ref model-cache://task054/<candidate-id>

python -m bvp_task054 model verify \
  --candidate <candidate-id> \
  --write-report reports/task054/<run-id>/base-model-verification.json
```

The acquisition command resolves credentials outside arguments/logs, downloads
only admitted files, enforces size/file-count/extension ceilings and verifies every
digest. Failed verification quarantines the candidate.

## 4. Operator setup flow

In `BAI Video Production -> Game Intelligence -> DbD -> 解説AI設定`:

1. choose `安全な初期設定を始める`;
2. confirm environment card (`利用可能 / 要対応 / Gate待ち`);
3. select a reviewed base-model candidate using Japanese capability/rights/
   resource summaries;
4. choose `評価のみ` or `学習を準備`; default is `評価のみ`;
5. select an admitted Dataset revision;
6. run `事前チェック`; no download/training occurs;
7. review time/storage/cost/rights summary;
8. only after the separate Gate, press `承認済み手順を実行`;
9. monitor progress/cancel and open the generated receipt;
10. completed artifacts remain `隔離中` until offline evaluation and Human review.

## 5. Dataset preparation procedure

### Narration/commentary video intake

Here `ナレーション` means both実況 and解説 contained in a source video.
Candidate extraction reuses canonical Product audio/ASR/Evidence owners:

```bash
python -m bvp_task054 narration intake-plan \
  --video-asset-id <asset-id> \
  --rights-ref rights://<receipt> \
  --output reports/task054/<run-id>/narration-intake-plan.json

python -m bvp_task054 narration extract-candidates \
  --plan <plan-ref> \
  --asr-profile <approved-profile-ref> \
  --diarization-profile <approved-profile-ref> \
  --event-timeline <cgel-ref> \
  --output dataset-staging://task054/<run-id>/narration
```

These are future gated commands. Extraction outputs candidates only. Operator
review confirms transcript, speaker separation, source range, aligned Event,
patch, commentary role and training suitability.

Required roles:

```text
PLAY_BY_PLAY / ANALYSIS / TACTICAL / REACTION / TRANSITION / FILLER / UNCERTAIN
```

Admit reviewed play-by-play, analysis, tactical, selected reaction and useful
transition segments. Normally reject filler and hold uncertain segments. Preserve
silence/no-speak windows as negative timing examples so the model learns when not
to talk.

Acceptance requires training rights; Human-corrected ASR where needed;
pseudonymized speaker turns; reviewed role/Event alignment; private/name redaction;
and whole-video/Match source-group isolation. No waveform, timbre or biometric
feature enters the LLM Dataset. Person-specific catchphrases/style require separate
consent instead of implicit generalization.

### Required row fields

```text
example_id
source_group_id
match_id
source_video_asset_id / source_audio_asset_id
source_start_frame / source_end_frame
speaker_ref / speaker_turn_id
asr_revision / diarization_revision
transcript_original / transcript_corrected
commentary_role
context_schema_version
context_sha256
redacted_context_json
target_proposal_json
style_profile_ref
speech_budget_ms
patch_version
killer_id / map_id / event_types
locale
rights_ref / consent_ref / provenance_ref
human_decision
reviewer_ref
review_reason
created_at
```

### Build and validate

```bash
python -m bvp_task054 dataset build \
  --intake <approved-intake-ref> \
  --dataset-id <id> --revision <n> \
  --output datasets/task054/<id>/<n>

python -m bvp_task054 dataset audit \
  --manifest datasets/task054/<id>/<n>/manifest.json \
  --policy config/task054/evaluation-policy.yaml \
  --report reports/task054/<run-id>/dataset-audit.json
```

Audit must fail closed on missing rights/reviewer, secret refs, raw paths,
malformed targets, invalid facts, source-group leakage, near duplicates, phrase
overlap, distribution omissions, uncertain narration alignment and unsafe
personal/style/voice data.

### Split procedure

- group by `source_group_id` and `match_id` before split;
- stratify only within the group constraint by patch/Killer/Map/event/locale;
- freeze test IDs before tuning;
- store deterministic seed and algorithm revision;
- never inspect/relabel held-out outcomes to improve a run; corrections create the
  next Dataset revision.

## 6. Base-model baseline

Before tuning, run the frozen prompt/RAG baseline:

```bash
python -m bvp_task054 evaluate \
  --binding baseline://<base-model-candidate> \
  --dataset <dataset-manifest> \
  --split validation \
  --policy config/task054/evaluation-policy.yaml \
  --output reports/task054/<run-id>/baseline
```

Record schema validity, unsupported facts, citation coverage, abstention,
calibration, latency, tokens, memory and blind Human sample pack. If baseline
already meets need, tuning is optional.

## 7. Tuning methods

### 7.1 SFT + QLoRA default pilot

Reference starting profile, subject to model/runtime validation:

```yaml
method: qlora_sft
seed_set: [104729, 130363, 155921]
sequence_length: 4096
quantization: {bits: 4, type: nf4, double_quant: true}
compute_dtype: bf16
lora:
  rank: 32
  alpha: 64
  dropout: 0.05
  target_modules: [q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj]
optimizer: paged_adamw_8bit
learning_rate: 0.0001
epochs: 1-3
effective_batch_size: 32
warmup_ratio: 0.03
weight_decay: 0.01
gradient_clip: 1.0
eval_strategy: steps
early_stop_on_safety_regression: true
```

Target modules must match the pinned architecture; unsupported names fail before
training. Sweep a small approved grid over rank/learning rate/epochs. Do not tune
on held-out test results.

```bash
python -m bvp_task054 train sft \
  --base-model <verified-model-ref> \
  --dataset <manifest> \
  --profile config/task054/training-profile.yaml \
  --authorization-ref authorization://<receipt-id> \
  --output model-quarantine://task054/<run-id>
```

Training writes checkpoints atomically, supports bounded cancel/resume and never
overwrites an existing artifact revision.

### 7.2 Preference tuning

Use DPO/ORPO-style preference tuning only when the Dataset has independently
reviewed, non-duplicated `chosen/rejected` pairs covering factual safety,
abstention and style—not merely subjective catchphrases. Run after an SFT candidate
passes factual gates. Preference tuning cannot relax Fact/Policy Validators.

### 7.3 Methods excluded from first pilot

- full-parameter fine-tuning;
- online/continuous self-training from generated output;
- reinforcement learning against unreviewed automated reward only;
- training current game facts into weights;
- merging adapters into base weights before evaluation/rollback proof;
- automatic activation of the latest checkpoint.

## 8. Checkpoint and failure operation

Operator controls:

- `一時停止` only at an atomic checkpoint;
- `安全にキャンセル` writes a cancelled receipt and leaves last verified
  checkpoint;
- `再開` requires environment/model/Dataset/profile digest equality;
- NaN/loss explosion/OOM/disk ceiling/device loss stops the job;
- one reduced-resource retry may be proposed, never silently applied;
- cancelled/failed outputs remain quarantined and cannot become a binding.

## 9. Offline evaluation

```bash
python -m bvp_task054 evaluate compare \
  --baseline <baseline-binding> \
  --generic <approved-generic-binding> \
  --candidate model-quarantine://task054/<run-id> \
  --dataset <manifest> --split test \
  --seeds 104729,130363,155921 \
  --policy config/task054/evaluation-policy.yaml \
  --output reports/task054/<run-id>/comparison
```

Hard gates: admitted unsupported fact `0`, patch-incompatible claim `0`, citation
coverage `100%`, secret/PII leak `0`, split leakage `0`. Soft gates compare
abstention, stability, Human preference, latency/cost/resource. A hard-gate failure
cannot be averaged away.

## 10. Human blind review

In `モデル比較`:

1. reviewer sees Context/Evidence and candidates A/B/C without model identity;
2. reviewer scores factual acceptability, uncertainty, usefulness, timing,
   naturalness and density;
3. reviewer selects `A / B / C / すべて不採用`;
4. any correction requires structured original/corrected value, reason and ref;
5. model identity is revealed only after submission;
6. report includes inter-reviewer agreement and per-domain failure clusters.

## 11. Artifact registration and promotion

```bash
python -m bvp_task054 artifact seal \
  --quarantine model-quarantine://task054/<run-id> \
  --evaluation-report <report-ref> \
  --rights-manifest <rights-ref> \
  --output <artifact-manifest>

python -m bvp_task054 binding propose \
  --artifact <artifact-manifest> \
  --status EVALUATED
```

`APPROVED` and Product activation are separate Human actions. Promotion UI shows
all hard gates, baseline delta, rights, resources and rollback target on one page.

## 12. Runtime operation

### Confirmation mode — no learning

```text
確認モード（学習しない）
 -> select an ordinary video
 -> select current approved/baseline model
 -> analyze to CGEL/context
 -> generate time-aligned実況/解説 preview
 -> inspect text, timing, Evidence and validation
 -> close/export evaluation receipt
```

Before and after the run, the system verifies that Dataset revision/digest,
adapter/base-model digest, binding revision/status and Training Job count are
unchanged. The mode cannot expose `学習候補へ追加`, `学習開始` or automatic feedback
mining. Review notes are evaluation-only and `training_eligible=false`.

Future CLI equivalent:

```bash
python -m bvp_task054 preview video \
  --mode PREVIEW_NO_LEARNING \
  --video-asset-id <asset-id> \
  --binding <approved-or-baseline-binding> \
  --output reports/task054/<run-id>/video-preview
```

### Learning mode

```text
学習モード
 -> select rights-admitted video/narration
 -> extract context and existing narration or generate a candidate
 -> Human correct/tag/approve the target
 -> add to Dataset staging
 -> validate and adopt a new Dataset revision
 -> execute separately authorized training job
 -> create a new quarantined adapter revision
 -> evaluate; never overwrite active model
```

Learning uses Human-approved/corrected targets only. The current model's generated
text is not its own ground truth. Selecting Learning mode authorizes the workflow
path, but actual Dataset adoption, training resource use and activation still obey
their displayed Human Gates.

Normal operator flow:

```text
open reviewed Event
 -> 解説候補を作る
 -> choose Approved binding (or baseline)
 -> inspect route/cost/context summary
 -> explicit Execute
 -> observe generation/validation
 -> compare Evidence and separated claim classes
 -> Approve / Correct / Reject
 -> explicit existing adoption flow
```

The default remains baseline/disabled until activation. Missing tuned runtime can
abstain or use an explicitly configured approved fallback; identity is never
hidden.

## 13. Rollback and revocation

1. set binding `SUSPENDED` to stop new resolution;
2. preserve existing receipts/candidates;
3. select the previous approved binding or baseline explicitly;
4. verify new attempts use the selected binding;
5. run regression and packaged restart;
6. use `REVOKED` for rights/security/integrity failures;
7. never delete historical Evidence to simulate rollback.

## 14. Human Gates checklist

- [ ] Dataset rights/consent and encrypted storage
- [ ] model license and download
- [ ] runtime/dependency install
- [ ] local/paid training resource use
- [ ] external Provider inference/upload
- [ ] artifact promotion to `APPROVED`
- [ ] default-route activation
- [ ] Commentary/TTS/Timeline adoption
- [ ] release/deploy/Production Activation

Each checkbox requires its own current authority. Completion of an earlier item
does not imply the next.
