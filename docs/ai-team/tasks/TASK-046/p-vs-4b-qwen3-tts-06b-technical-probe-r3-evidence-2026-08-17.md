# TASK-046 / P-VS-4B Gate 4 R3 — Qwen3-TTS 0.6B Technical Probe Evidence

## Outcome

The existing isolated Qwen3-TTS environment and pinned 0.6B Base model load
successfully on the target RTX 4070 SUPER without inference, audio generation,
or training.  The exact official `main` fine-tuning recipe is not admitted for
the pinned 0.6B model: its current text-embedding path produces 2048-wide
embeddings while the 0.6B talker consumes 1024-wide codec embeddings.  The
official repository has an open, unmerged pull request that adds the missing
projection.  A pending change is Evidence of a known incompatibility, not an
approved recipe revision.

R3 therefore records `PACKAGE_VERIFY=PASS` and `MODEL_LOAD=PASS` only.
Representative-step, optimizer/checkpoint, OOM recovery, thermal-duration and
mode-specific 12 GB feasibility remain blocked or unknown.  No Owner audio was
read and no Dataset, Job, checkpoint, model artifact, or narration WAV was
created.

## Exact source and runtime binding

### Official source

- repository: `https://github.com/QwenLM/Qwen3-TTS`;
- audited branch/revision: `main@022e286b98fbec7e1e916cb940cdf532cd9f488e`;
- official fine-tuning script Git blob:
  `c1f3f4684f3f53927a660f06e58beb6a4107f89a`;
- official open fix: pull request `#336`, head
  `701938bb6bdf22c091ec0a0952990bf9b7ae457d`;
- proposed fixed script Git blob:
  `89f98640983b0933cd92d873bc439be0aedb7e02`;
- proposed change: project the text embedding from 2048 to 1024 before adding
  it to the codec embedding, then restore the padding mask;
- source/model license declarations observed: Apache-2.0.

The fix head is not substituted into the runtime and is not treated as an
official admitted release.  R3 modifies neither upstream source nor the
installed package.

### Isolated local runtime

- Python: `3.12.4`;
- `qwen-tts`: `0.1.1`;
- qwen wheel: 113,529 bytes, SHA-256
  `11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d`;
- PyTorch: `2.11.0+cu130`;
- torchaudio: `2.11.0+cu130`;
- Transformers: `4.57.3`;
- Accelerate: `1.12.0`;
- `flash-attn`: not installed;
- `tensorboard`: not installed;
- `peft`: not installed;
- SoX executable: not found by the runtime process.

Missing packages are recorded facts.  R3 does not install them and does not
infer that installation would make the recipe compatible or feasible.

### Pinned model

- model: `Qwen/Qwen3-TTS-12Hz-0.6B-Base`;
- revision: `5d83992436eae1d760afd27aff78a71d676296fc`;
- `config.json`: 4,494 bytes, SHA-256
  `2e714c787c8edb98b05432685cddb634add2de4d4e645f653d68251ef72ba011`;
- model weights: 1,829,344,272 bytes, SHA-256
  `180b3b10eb1c9f1b4db7806d5475bae3071c0243c299d49926bab1da3b6946f6`;
- speech-tokenizer weights: 682,293,092 bytes, SHA-256
  `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258`;
- model type: `base`;
- talker hidden size: `1024`;
- text hidden size: `2048`.

Absolute runtime and model paths are private operation coordinates and are not
part of public projection.

## Target-machine load-only measurement

- GPU: NVIDIA GeForce RTX 4070 SUPER;
- NVIDIA driver: `610.62`;
- reported VRAM: `12,282 MiB`;
- PyTorch CUDA runtime: `13.0`;
- attention implementation used by this probe: PyTorch SDPA;
- model-load duration: `2.678 seconds`;
- peak CUDA allocated bytes: `2,175,147,520`;
- peak CUDA reserved bytes: `2,306,867,200`;
- current allocated bytes immediately after load: `2,173,340,672`;
- result: `PASS_MODEL_LOAD_ONLY`.

Execution flags were fixed as follows:

- `execution_started=false`;
- `inference_started=false`;
- `training_started=false`;
- `owner_audio_used=false`;
- `dataset_effect_started=false`;
- `checkpoint_write_started=false`;
- `model_artifact_write_started=false`;
- `publication_started=false`.

The runtime emitted warnings that SoX and `flash-attn` were unavailable.  The
load-only probe used SDPA and did not suppress or reinterpret those warnings.

## Recipe compatibility finding

The audited official script directly adds
`model.talker.model.text_embedding(input_text_ids)` to the codec embedding.
For the pinned 0.6B configuration those tensors are 2048 and 1024 wide.  The
open official fix inserts `model.talker.text_projection` before the addition.
Because that fix is not in the audited official `main`, the exact current
0.6B representative-step recipe is `FAILED_KNOWN / BLOCKED` before any Owner
Dataset or training attempt.

The result does not generalize to another engine/model/revision or mode:

| Mode | Exact recipe state | R3 decision |
| --- | --- | --- |
| `FULL_FINE_TUNE` | official main recipe present, 0.6B incompatibility known | representative step blocked; feasibility `UNKNOWN` |
| `PARAMETER_EFFICIENT_FINE_TUNE` | no exact official admitted recipe Evidence | `UNKNOWN / PROBE_REQUIRED` |
| `ADAPTER_OR_LORA` | no exact official admitted recipe Evidence; `peft` absent | `UNKNOWN / PROBE_REQUIRED` |

Model load is not training admission.  A later probe needs an exact official
compatible revision, an independently pinned dependency set and a synthetic
representative batch/sequence.  It must measure peak VRAM/RAM, optimizer and
checkpoint overhead, disk floor, OOM-safe failure/reconciliation,
thermal-duration behavior and exact output/checkpoint integrity separately for
each mode.

## Process and replay boundary

The pre-probe GPU snapshot showed no identified training process, but several
graphics/compute process names were unavailable due operating-system access
limits.  That observation is not sufficient to prove a fully reconciled
durable Training Job.  R3 therefore cannot authorize dispatch, retry, resume,
or a duplicate run.  A future training probe requires a fresh authoritative
Job/process/checkpoint reconciliation receipt.

## Critic passes

### Critic pass 1 — Builder and compatibility

- exact upstream main and proposed-fix heads are separated;
- source blobs, installed wheel, model revision and weight hashes are pinned;
- local load Evidence is not promoted to representative-step Evidence;
- the 2048/1024 mismatch is derived from the pinned configuration and the
  audited official source;
- a pending pull request is not treated as an admitted implementation.

Finding corrected during the pass: the first draft needed to distinguish a
known failure of the exact current recipe from the still-unknown feasibility of
a future compatible recipe.  The final matrix records both states explicitly.

### Critic pass 2 — Security and authority

- no audio or text body was accessed;
- no absolute private path is intended for public projection;
- no download, dependency installation, inference, training or artifact write
  occurred in the load-only operation;
- process-observation gaps remain `UNKNOWN` and cannot enable replay;
- license declarations are Evidence, not commercial/publication authority.

Residual Critical/High/Medium: `0 / 0 / 0`.

## Judge

- EXISTING PACKAGE/MODEL IDENTITY: `PASS_VERIFIED`.
- TARGET GPU MODEL LOAD: `PASS_LOAD_ONLY`.
- OFFICIAL MAIN 0.6B REPRESENTATIVE STEP: `FAILED_KNOWN / BLOCKED`.
- FULL 12 GB TRAINING FEASIBILITY: `UNKNOWN / PROBE_REQUIRED`.
- PEFT/LORA TRAINING FEASIBILITY: `UNKNOWN / PROBE_REQUIRED`.
- DATASET/JOB/TRAINING/CHECKPOINT/MODEL EFFECT: `NOT_STARTED`.
- OWNER AUDIO/NARRATION/PRODUCTION/PUBLICATION: `NOT_STARTED`.

R3 is complete as technical Evidence.  The next runnable engine step is an
exact-revision synthetic compatibility probe after an official fix is merged,
or a separately reviewed alternative engine/model/mode probe.  Owner recording
is not needed for that step.
