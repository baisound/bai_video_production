# TASK-046 / P-VS-4B Gate 4 R4 — Qwen3-TTS Dependency Setup Evidence

## Outcome

TensorBoard and FlashAttention are now installed and runtime-verified in
isolated environments on the target machine.

- Windows native environment: TensorBoard 2.21.0, SoX 14.4.2 and a
  FlashAttention 2.8.3.post1 wheel built locally from the official source;
  CUDA compiler smoke and bf16 GPU forward/backward passed.
- WSL2 probe environment: official FlashAttention 2.8.3 Linux wheel installed
  with PyTorch/Torchaudio 2.8.0+cu128; bf16 CUDA forward and backward passed on
  the RTX 4070 SUPER.
- Qwen-TTS 0.1.1 import, SoX 14.4.2 discovery and `pip check` passed in WSL2.

This is dependency compatibility Evidence only.  No model was loaded in R4,
and no inference, audio generation, Dataset access, training, checkpoint or
model artifact operation was started.  The R3 finding that the audited official
0.6B fine-tuning recipe has a 2048/1024 embedding incompatibility remains
unchanged and blocks a representative training step.

## Authority and effect boundary

The Owner authorized setup of `flash-attn` and TensorBoard.  R4 used that
authority for task-owned package acquisition, isolated environment creation,
installation and bounded runtime compatibility tests.

Fixed false effect flags:

- `model_loaded=false`;
- `inference_started=false`;
- `audio_generated=false`;
- `training_started=false`;
- `dataset_effect_started=false`;
- `checkpoint_write_started=false`;
- `model_artifact_write_started=false`;
- `publication_started=false`.

## Target and isolated environment

- host GPU: NVIDIA GeForce RTX 4070 SUPER;
- driver: 610.62;
- reported VRAM: 12,282 MiB;
- WSL distribution: Ubuntu 24.04;
- WSL kernel: `6.18.33.2-microsoft-standard-WSL2`;
- Python: 3.12.3;
- PyTorch: 2.8.0+cu128;
- Torchaudio: 2.8.0+cu128;
- PyTorch CUDA runtime: 12.8;
- PyTorch CXX11 ABI: true;
- Qwen-TTS: 0.1.1;
- Transformers: 4.57.3;
- Accelerate: 1.12.0;
- FlashAttention: 2.8.3;
- TensorBoard: 2.21.0;
- Ninja: 1.13.0;
- psutil: 7.2.2;
- SoX: 14.4.2;
- separately installed toolkit compiler: CUDA 13.0.88.

The successful runtime uses the CUDA 12.8 libraries bound to the PyTorch wheel.
The CUDA 13 toolkit is retained as source-build Evidence but is not represented
as the ABI of the installed FlashAttention wheel.

## Official wheel binding

- upstream release:
  `https://github.com/Dao-AILab/flash-attention/releases/tag/v2.8.3`;
- asset:
  `flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl`;
- asset bytes: 256,040,057;
- asset SHA-256:
  `f25da18657a87fc83dc1bfb8b7751b82246e9db355510226b674fd437c34b5fb`;
- package version after install: 2.8.3;
- install source: exact local copy of the official GitHub release asset;
- third-party wheel used: no.

The wheel is admitted only for the pinned `cp312`, PyTorch 2.8, CUDA 12 major
and CXX11-ABI-true matrix.  It is not reusable Evidence for PyTorch 2.11/cu130,
Windows native Python or another ABI.

## Source-build findings

The official PyPI 2.8.3.post1 source distribution was also examined:

- source archive SHA-256:
  `55d5103ed846da8b56e0797acf4bde07dee4b1c7e8907fcfc6699c203030c348`;
- Windows native official binary result: no matching official Windows wheel
  was supplied;
- Windows native source result: the exact official sdist was compiled with VS
  Build Tools 2026, NVIDIA pip CUDA 13.3/CCCL and PyTorch 2.11+cu130, producing
  a local cp312/win_amd64 wheel; no source file was patched;
- WSL 4-job source build: failed by genuine memory exhaustion with 31 GB RAM
  and 8 GB swap;
- WSL 1-job / one nvcc-thread source build: avoided the observed OOM but the
  WSL VM became unavailable during CUDA compilation and did not produce a
  wheel or a valid terminal receipt.

The interrupted source attempt is not PASS.  It was not blindly retried after
the exact official compatible wheel was found.  No unofficial or fork release
was substituted.

## Windows native source-build and runtime result

- Python: 3.12;
- PyTorch/Torchaudio: 2.11.0+cu130;
- CUDA source compiler: NVIDIA pip `nvcc` 13.3.73;
- CCCL: 13.3.3.4.1;
- MSVC: 19.51.36256 / VS Build Tools 2026 18.9;
- source sdist bytes: 8,451,657;
- source sdist SHA-256:
  `55d5103ed846da8b56e0797acf4bde07dee4b1c7e8907fcfc6699c203030c348`;
- local wheel: `flash_attn-2.8.3.post1-cp312-cp312-win_amd64.whl`;
- local wheel bytes: 57,016,766;
- local wheel SHA-256:
  `9190c93e0a62532ab42f390b0029e9862e277930caef77ef4de39ae4035b453a`;
- CUDA compiler `sm_89` smoke: PASS, result 42;
- FlashAttention bf16 forward/backward: PASS;
- output and q/k/v gradients finite: true;
- Qwen-TTS class import with process-local SoX: PASS;
- `pip check`: no broken requirements.

The generated wheel is a local build artifact, not an upstream-provided or
signed Windows binary.  It is not admitted for reuse on another Python,
PyTorch, CUDA, compiler or machine binding without a new build and runtime
verification.

## Runtime compatibility measurement

The installed official wheel was executed, not merely imported.

- function: `flash_attn_func`;
- device: CUDA device 0, RTX 4070 SUPER, compute capability 8.9;
- dtype: bf16;
- q/k/v shape: `(2, 128, 4, 64)`;
- dropout: 0;
- causal: false;
- output shape: `(2, 128, 4, 64)`;
- scalar loss: `0.020701097324490547`;
- output finite: true;
- q gradient finite: true;
- k gradient finite: true;
- v gradient finite: true;
- result: `PASS_BOUNDED_FORWARD_BACKWARD`.

The test allocated synthetic tensors only.  It loaded no Qwen model and read no
Owner audio or Dataset body.

## TensorBoard and package verification

WSL2 `SummaryWriter` wrote one task-owned event file:

- bytes: 258;
- SHA-256:
  `79ef485270efb7cffdcade647bbc86e60603b21ad8306cfa1cf35fa87052a2f4`.

The Windows TensorBoard pip install report is 25,503 bytes with SHA-256
`9fd306ffd731693368a48a81f2fbfa3b80e3c6edab1dc3eb49ec1315b9f0a0cd`.
The Windows writer smoke also passed.  Neither environment started a network
listener or exposed a log directory.

Final WSL2 verification:

- `qwen_tts.inference.qwen3_tts_model.Qwen3TTSModel` import: PASS;
- model load: false;
- SoX executable: PASS, version 14.4.2;
- `pip check`: `No broken requirements found`;
- free WSL filesystem bytes after setup: 979,615,309,824.

## Receipt hashes

- runtime smoke JSON:
  `6dd1ca27089045aa933135559654f4cf78bcfbdd66477c5c2a34e8097dccea68`;
- bootstrap pip report:
  `b311a77bf2f2c222a34a3dad03366cea80111d2bce7f8ec1eee4957eca796d35`;
- PyTorch/cu128 pip report:
  `55a81ca54a0543c27829032563a79dea542601414d3b193f6e1577553ff6705b`;
- Qwen/TensorBoard pip report:
  `b4c4b65ae6f3af66448d259d368cbd52c4aa0569c9bc4596619abe3574e7e129`;
- official FlashAttention wheel install report:
  `0bcd15128485b1714eaa4f5f0b37e4cc31607b13cec3dd145fc398f5a02aaa6c`;
- final pip-check receipt:
  `9261363b733079a641c2e4cc9bc46ffa1d8336945a87f807b6cf68847dbc9b09`.
- Windows FlashAttention runtime smoke:
  `1f0c7600708b9bbdda3a78a329468f9ec0a1585b1f575090e0be2737533649e7`;
- Windows final dependency report:
  `4e16e41fbc553a38b1d06c153f57fe704900a357565cfc09da00ef84c22612a2`;
- Windows local wheel install report:
  `af6e2c9de639e65bea591a4014907786551a9ddcf833df789294014e477dbd96`;
- Windows CUDA CCCL install report:
  `6aa6bcba78677975426282f86bb5df153963bb8689decf4cca13c281adf65079`.

Private absolute environment and recovery paths are intentionally omitted from
this repository Evidence.

## R3 training blocker revalidation

R4 does not change or patch the Qwen3-TTS recipe.  The admitted source remains
the R3-audited official `main@022e286b98fbec7e1e916cb940cdf532cd9f488e`.
Its 0.6B text/talker hidden sizes remain 2048/1024.  Open upstream pull request
`#336` remains proposal Evidence, not an admitted merged recipe.

Therefore:

| Gate | R4 state |
| --- | --- |
| TensorBoard writer | `PASS_SETUP_COMPATIBILITY` |
| FlashAttention import | `PASS_SETUP_COMPATIBILITY` |
| FlashAttention bf16 forward/backward | `PASS_BOUNDED_COMPATIBILITY` |
| Qwen-TTS import | `PASS_PACKAGE_IMPORT_ONLY` |
| Qwen 0.6B representative training step | `FAILED_KNOWN / BLOCKED` |
| 12 GB full-mode feasibility | `UNKNOWN / PROBE_REQUIRED` |
| PEFT/LoRA feasibility | `UNKNOWN / PROBE_REQUIRED` |
| Dataset/Job/training/checkpoint/model effect | `NOT_STARTED` |

## Critic pass 1 — Builder and compatibility

- classified and corrected the PyTorch OEM decode, missing CCCL and standard
  MSVC preprocessor prerequisites before completing the Windows build;
- selected an official release asset rather than a community wheel;
- matched Python, PyTorch, CUDA-major and CXX11 ABI coordinates;
- tested actual CUDA forward and backward, not import alone;
- preserved the R3 recipe incompatibility instead of promoting dependency PASS
  to training PASS.

Residual Critical/High/Medium: `0 / 0 / 0`.

## Critic pass 2 — Security and authority

- environments and receipts are task-owned and isolated;
- official source domains and package hashes are fixed;
- private absolute paths, credential and body data are absent from public docs;
- no TensorBoard network listener was started;
- no Owner audio, model inference, training or publication effect occurred;
- interrupted builds and WSL unavailability were not converted to PASS.

Residual Critical/High/Medium: `0 / 0 / 0`.

## Judge

- TENSORBOARD SETUP: `PASS`.
- OFFICIAL FLASHATTENTION WHEEL IDENTITY: `PASS_VERIFIED`.
- TARGET GPU FORWARD/BACKWARD: `PASS_BOUNDED_COMPATIBILITY`.
- WINDOWS LOCAL FLASHATTENTION BUILD: `PASS_FROM_OFFICIAL_SOURCE`.
- WINDOWS GPU FORWARD/BACKWARD: `PASS_BOUNDED_COMPATIBILITY`.
- QWEN-TTS PACKAGE IMPORT: `PASS_IMPORT_ONLY`.
- OFFICIAL 0.6B TRAINING RECIPE: `FAILED_KNOWN / BLOCKED`.
- TRAINING RESOURCE ADMISSION: `UNKNOWN / NOT_AUTHORIZED`.
- MODEL/DATASET/AUDIO/PRODUCTION EFFECT: `NOT_STARTED`.
- unresolved Critical/High/Medium: `0 / 0 / 0`.

The next engine step remains an exact official compatible-recipe re-audit and
synthetic representative-step proposal.  R4 does not require Owner recording.
