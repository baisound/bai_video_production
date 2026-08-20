# TASK-014 — Qwen3-TTS Retained Artifact Availability Audit R0 Evidence

Date: `2026-08-21`
Status: `JUDGE_ACCEPTED / FRESH_MAIN_VALIDATED / ARTIFACT_CLOSURE_NOT_BOUND / EXECUTION_BLOCKED / COMMIT_READY / UNCOMMITTED`
Development depth: `DEV-4 FOUNDATION CRITICAL`
Base: `main@59f930c3a7ebbff0161986dfa8fe49abdf0fecdc`

## Purpose and authority

This read-only Atomic Unit performs a bounded feasibility audit for the merged
`bai.task014.qwen3-tts-runtime-artifact-manifest.v1` contract. It does not
claim a complete retained-artifact inventory or determine artifact absence.

The audit uses only the already authorized bounded read of explicit public
TASK-014/runtime candidates and public package metadata. It creates no durable
network, download, install or execution authority for this or a later unit. It
does not read model bodies or Owner media, run target Python, import a package,
resolve or download a dependency, install or modify a runtime, invoke a native
media tool, load a model or start inference.

Absolute runtime/model paths are private operation coordinates and are not
persisted here. Logical labels below are body-free public Evidence only.

## Bounded observation

The audit read:

1. the public `E:\BAI_AI` responsibility README;
2. only the first level of the public `downloads`, `envs`, `runtimes` and
   `lib` responsibilities;
3. two explicit Qwen runtime candidates identified by that bounded listing;
4. `Scripts/python.exe` version metadata for those candidates;
5. only direct `*.dist-info/METADATA` identity and `Requires-Dist` lines under
   the selected R0 candidate, with a maximum of 256 distributions and 2 MiB
   per metadata file; and
6. the two explicit retained artifact files listed below.

There was no recursive drive search, cache search, provider access or private
media access.

## Selected observed runtime candidate

The R0 candidate is the existing public TASK-014 Windows environment whose
installed metadata matches the frozen runbook matrix:

- CPython file version/product version: `3.12.4`;
- installed `qwen-tts`: `0.1.1`;
- installed `torch` / `torchaudio`: `2.11.0+cu130`;
- installed `transformers`: `4.57.3`;
- installed `accelerate`: `1.12.0`;
- installed `huggingface-hub`: `0.36.2`;
- installed `soundfile`: `0.14.0`;
- FlashAttention installed: `false`;
- intended attention path: `SDPA`.

No installed executable hash, installed-tree fingerprint or full environment
inventory is projected into this public Evidence. Installed metadata is a
point-in-time discovery observation, not a retained-artifact trust anchor and
not execution authority.

The installed `qwen-tts 0.1.1` metadata declares these direct requirements:

```text
transformers==4.57.3
accelerate==1.12.0
gradio
librosa
torchaudio
soundfile
sox
onnxruntime
einops
```

## Retained public artifacts

| Artifact | Bytes | Observed SHA-256 | Current admission |
| --- | ---: | --- | --- |
| `qwen_tts-0.1.1-py3-none-any.whl` | 113,529 | `11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d` | `MATCHES_MERGED_PIN` |
| `python-3.12.4-amd64.exe` | 26,772,456 | `da5809df5cb05200b3a528a186f39b7d6186376ce051b0a393f1ddf67c995258` | `CANDIDATE / OFFICIAL_COORDINATE_NOT_YET_BOUND` |

Of the two explicitly inspected artifact candidates, the Qwen wheel is already
admitted by a merged exact pin. This bounded observation does not prove that it
is the only retained distribution artifact elsewhere. The Python installer
requires a later official-source coordinate/digest comparison before it can
become an accepted artifact entry.

## Installed distribution observation

The bounded metadata read confirmed that the candidate contains the required
runbook matrix and additional installed distributions. The exact inventory,
versions outside the required matrix and installed-file fingerprints remain a
private observation and are not a canonical input. A later compiler must
derive the active closure from accepted retained artifact metadata; it must
not copy the installed set or silently treat extras as requirements.

## Gate result

The complete runtime artifact manifest cannot yet be accepted:

- exact retained-artifact inventory and active closure: `NOT_BOUND`;
- retained artifact absence: `NOT_CONFIRMED`;
- explicitly observed Qwen wheel: `MATCHES_MERGED_PIN`;
- Python installer: retained candidate, but official source coordinate and
  upstream digest are `NOT_BOUND`;
- ffmpeg/ffprobe same-archive pair: `NOT_BOUND`;
- SoX executable/archive: `NOT_BOUND`;
- SoundFile-to-libsndfile native ownership: `NOT_BOUND`;
- PyTorch/Torchaudio CUDA wheel artifact coordinates and native ownership:
  `NOT_BOUND`;
- direct/transitive active dependency graph compiled from retained artifact
  metadata: `NOT_BOUND`.

Decision: `ACCEPTED_ARTIFACT_CLOSURE_NOT_BOUND /
RETAINED_ARTIFACT_AVAILABILITY_NOT_CONFIRMED`.

This result does not authorize downloading or installing anything. It parks
runtime reuse, target Python execution, import, load-only probing, Owner audio
read and inference. It also prevents an installed-tree self-hash, package
version, pip report or `pip check` result from being substituted for retained
artifact provenance.

## No-effect record

- repository source/schema/test mutation: `false`;
- E: file creation/modification/deletion: `false`;
- recursive filesystem or cache search: `false`;
- target Python/package/native executable launch: `false`;
- network/provider access: `false`;
- dependency resolution/download/install: `false`;
- model body read/load/inference: `false`;
- Owner audio/private media access: `false`;
- REAPER/iZotope/native audio effect: `false`.

Independent DEV-4 acceptance after the bounded public-projection correction is
`Critical 0 / High 0 / Medium 0` from both Tester and Critic/Judge.

## Next safe Atomic Unit

`AU2C2B — Runtime Artifact Closure Intake R0` must first bind the active
dependency closure and an exact bounded retained-artifact inventory/coordinate
match. Only an entry confirmed absent by that accepted procedure may become
`RETAINED_ARTIFACT_MISSING`. Official metadata can then freeze the exact
Python installer, distribution wheels, ffmpeg/ffprobe pair and SoX artifact
coordinates needed by one Windows/cp312/cu130 closure. The unit must
distinguish the active dependency closure from installed extras, bind every
filename/byte count/SHA-256/source and set deterministic byte/time limits.

AU2C2B begins with design and official-coordinate intake only. Network access,
download, install and execution authority must be rebound explicitly in that
unit after its DEV-4 acceptance. Any confirmed missing or unavailable official
artifact remains `BLOCKED`; there is no automatic fallback to a different
Python/PyTorch/CUDA matrix, a community wheel, the pip cache or the installed
environment.
