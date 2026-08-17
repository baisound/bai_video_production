# TASK-046 / P-VS-4B Gate 4 R5 — Qwen3-TTS open-PR compatibility probe

## Outcome

The exact projection proposed by upstream Qwen3-TTS pull request 336 was
tested against the pinned 0.6B Base model with a synthetic 16-token batch on
the target RTX 4070 SUPER.  Text embeddings changed from width 2048 to 1024,
matched the codec embedding width, and completed the talker and sub-talker
forward/backward path with finite loss and gradients.

This result is `PASS_OPEN_PR_TECHNICAL_PROBE_ONLY`.  Pull request 336 remains
open and unmerged, so it is not an admitted official recipe revision.  R5 did
not create an optimizer, execute an optimizer step, use a Dataset or Owner
audio, write a checkpoint/model artifact, or grant training admission.

## Exact source and model binding

- upstream repository: `https://github.com/QwenLM/Qwen3-TTS`;
- upstream pull request: `#336`, state `OPEN`, mergeable `MERGEABLE/CLEAN` at
  the operation-time read-back;
- proposed source head:
  `701938bb6bdf22c091ec0a0952990bf9b7ae457d`;
- proposed `finetuning/sft_12hz.py` blob:
  `89f98640983b0933cd92d873bc439be0aedb7e02`;
- model: `Qwen/Qwen3-TTS-12Hz-0.6B-Base`;
- model revision: `5d83992436eae1d760afd27aff78a71d676296fc`;
- `config.json` SHA-256:
  `2e714c787c8edb98b05432685cddb634add2de4d4e645f653d68251ef72ba011`;
- model weights SHA-256:
  `180b3b10eb1c9f1b4db7806d5475bae3071c0243c299d49926bab1da3b6946f6`;
- speech-tokenizer weights SHA-256:
  `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258`.

The probe used the isolated Windows environment documented by R4:
PyTorch `2.11.0+cu130`, FlashAttention `2.8.3.post1`, Python 3.12 and a
process-local SoX path.  Absolute environment/model/receipt paths remain
private operation coordinates and are not part of public metadata.

## Synthetic forward/backward result

- GPU: NVIDIA GeForce RTX 4070 SUPER, compute capability 8.9;
- attention implementation: `flash_attention_2`;
- batch/sequence: `1 / 16`;
- raw text embedding: `[1, 16, 2048]`;
- projected text embedding: `[1, 16, 1024]`;
- codec embedding: `[1, 16, 1024]`;
- combined embedding: `[1, 16, 1024]`;
- combined talker/sub-talker loss: `14.46825885772705`, finite;
- parameter tensors with gradients: `402`;
- all observed gradients finite: true;
- peak CUDA allocated bytes: `5,563,923,456`;
- peak CUDA reserved bytes: `5,697,961,984`;
- measured model-load plus bounded probe duration: `3.1062832000025082`
  seconds;
- private receipt bytes: `1,836`;
- private receipt SHA-256:
  `9c9694a3c633cc30fd8a0930da2c9aec98fbee89a72d30a7cc6f7c1a8c8232bb`.

The synthetic IDs exercise the proposed embedding projection and the same
talker/sub-talker loss path used by the reviewed script.  They do not represent
real text/audio distribution, Dataset preparation, speaker-encoder input,
optimizer/checkpoint overhead, expected duration, OOM recovery or thermal
feasibility.

## Effect boundary

The operation fixed these facts:

- `optimizer_created=false`;
- `optimizer_step_started=false`;
- `checkpoint_write_started=false`;
- `model_artifact_write_started=false`;
- `owner_audio_used=false`;
- `dataset_used=false`;
- `training_admission_granted=false`;
- `publication_started=false`.

Therefore this PASS cannot enable the beginner client training button, create
a TrainingRun receipt, register a ModelCandidate, bind a VoiceProfile, render
narration, or publish a model/audio artifact.

## Remaining gates

1. The compatible recipe must exist at an admitted official exact revision;
   an open pull request is insufficient.
2. A synthetic representative batch must include the official Dataset and
   speaker-encoder preparation without Owner audio.
3. FULL, PEFT and LoRA modes require separate recipe and resource admission.
4. Optimizer, checkpoint persistence/read-back, peak VRAM/RAM, disk,
   OOM-safe reconciliation, thermal duration and expected run time remain
   `UNKNOWN / PROBE_REQUIRED`.
5. Dataset adoption, training dispatch, model approval, narration and Master
   WAV acceptance remain separate Owner/Human gates.

## Critic

### Builder/compatibility

- exact proposed source head/blob and pinned model hashes were verified;
- actual FlashAttention talker/sub-talker forward/backward was run;
- the finite bounded result was not promoted to optimizer or training
  feasibility Evidence;
- upstream open state remains visible and fail-closed.

### Security/authority

- only synthetic token IDs were used;
- no Owner audio, Dataset body, private path or credential is published;
- no checkpoint/model/audio artifact or network listener was created;
- a pending upstream proposal was not represented as an official release.

Residual Critical/High/Medium: `0 / 0 / 0`.

## Repository validation

- changed paths: exact two documentation files;
- `git diff --check`: PASS;
- Windows full regression: `1,894 passed / 1 skipped` in 91.29 seconds;
- the single skip is the existing non-Windows credential-vault contract;
- hosted Ubuntu/Windows and Security checks remain required before merge.

## Judge

- PROPOSED 2048 TO 1024 PROJECTION: `PASS_TECHNICAL_PROBE`.
- TALKER/SUB-TALKER FORWARD/BACKWARD: `PASS_BOUNDED_SYNTHETIC`.
- OFFICIAL RECIPE ADMISSION: `BLOCKED_UPSTREAM_PR_OPEN`.
- OPTIMIZER/CHECKPOINT/12 GB TRAINING FEASIBILITY: `UNKNOWN`.
- DATASET/TRAINING/MODEL/NARRATION/PUBLICATION EFFECT: `NOT_STARTED`.
- unresolved Critical/High/Medium: `0 / 0 / 0`.
