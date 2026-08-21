# TASK-014 — Local Qwen3-TTS Owner Preview Runtime Runbook R0

Date: `2026-08-21`
Status: `JUDGE_ACCEPTED / FRESH_MAIN_VALIDATED / RUNBOOK_FROZEN / EXECUTION_BLOCKED / UNCOMMITTED`
Development depth: `DEV-4 FOUNDATION CRITICAL`

## 1. Purpose and authority

This runbook is the mandatory procedure before the first bounded local Owner-
voice preview under TASK-014. The Owner has authorized:

- design and implementation;
- download and execution of a free local model;
- use of the Owner's own voice reference;
- creation of the required download/execution procedure.

That authority does not permit a paid or Cloud call, upload of Owner audio,
training/fine-tuning, canonical Asset publication, placement, REAPER/iZotope
processing, Release or Deploy in this Atomic Unit.

The target operation is one `ZERO_SHOT_LOCAL / PREVIEW` generation. It is not
a production recording or a fine-tuning Dataset operation; TASK-047 P-OBS-1 is
therefore not a dependency. The untreated generated preview must be preserved
before any later TASK-035 finishing.

## 2. Exact admitted candidate

| Coordinate | Required value |
| --- | --- |
| Engine package | `qwen-tts==0.1.1` |
| Engine wheel SHA-256 | `11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d` |
| Model | `Qwen/Qwen3-TTS-12Hz-0.6B-Base` |
| Model revision | `5d83992436eae1d760afd27aff78a71d676296fc` |
| Model type | `base` / voice clone |
| License declaration | `Apache-2.0` for observed source/model declarations |
| `config.json` SHA-256 | `2e714c787c8edb98b05432685cddb634add2de4d4e645f653d68251ef72ba011` |
| `model.safetensors` bytes | `1,829,344,272` |
| `model.safetensors` SHA-256 | `180b3b10eb1c9f1b4db7806d5475bae3071c0243c299d49926bab1da3b6946f6` |
| Speech-tokenizer weights bytes | `682,293,092` |
| Speech-tokenizer weights SHA-256 | `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258` |
| Product language | `ja-JP` |
| Engine API language | `Japanese`; capability discovery must contain case-folded `japanese` |
| Intended mode | one-shot ICL voice clone with exact reference transcript |

The official Base API accepts local reference audio plus its transcript. ICL
mode is preferred for the first quality preview; `x_vector_only_mode=True` is
not an automatic fallback because it changes the quality/conditioning contract.

The known 0.6B fine-tuning recipe incompatibility does not block Base-model
inference, but it continues to block training. No pending upstream PR or fork
may be substituted into this run.

## 3. Private operation coordinates

Absolute paths, Owner text, Owner audio, voice embeddings and staging handles
must not be committed or printed in public Evidence. The operator supplies
these values only in the private execution shell:

```text
BVP_TTS_RUNTIME_KIND     exact value `WINDOWS` for this R0
BVP_TTS_RUNTIME_ROOT     isolated Python runtime root
BVP_TTS_MODEL_ROOT       exact pinned model snapshot root
BVP_TTS_QWEN_WHEEL       retained official `qwen-tts` wheel artifact
BVP_TTS_RUNTIME_RECEIPT  accepted private dependency/runtime receipt
BVP_TTS_MODEL_MANIFEST   accepted public pinned-snapshot manifest
BVP_TTS_FFMPEG           exact accepted local `ffmpeg.exe`
BVP_TTS_FFPROBE          exact accepted local `ffprobe.exe`
BVP_OWNER_REF_WAV        exact Owner-approved reference WAV
BVP_OWNER_REF_TEXT_FILE  exact transcript of the reference WAV
BVP_PREVIEW_TEXT_FILE    exact Owner-approved short Japanese preview text
BVP_TTS_STAGING_ROOT     encrypted/private contained output root
```

Do not use `C:` for the model, cache or output. The observed free space on C:
is below the recorded floor. The Owner-designated public AI artifact root is
`E:\BAI_AI`; admitted public model/package/runtime bytes may use its exact
`models/`, `downloads/`, `cache/` and `envs/` responsibilities without an
encryption requirement. Public artifact integrity is enforced by revision,
size, hash and strict file-set verification.

Owner reference audio, transcripts, embeddings, private datasets and generated
voice output are a different confidentiality class. They require a separately
verified encrypted private leaf plus exact Consent, rights, retention and
recovery binding. An unencrypted public model root never inherits authority to
store private media. WSL storage and runtime coordinates are outside R0.

## 4. Required preflight — no download or inference

Run all checks without recursively enumerating private roots.

1. Confirm the TASK-043/TASK-014 bridge exact diff is integrated into the
   execution checkout. A conversation claim or uncommitted diff is not enough.
2. Load the canonical `VoiceProfileRevision`, actual Local Primary Preflight,
   Render Admission and a store-loaded `LOCAL_NARRATION_RENDER` Job.
3. Bind a single-use authorization for `ZERO_SHOT_LOCAL / PREVIEW`; record the
   exact project, script revision, VoiceProfileRevision, engine/model revision,
   destination policy and expiry coordinates.
4. Bind the exact Owner reference WAV checksum and its exact transcript digest.
   Do not infer a file by name, newest timestamp or directory search.
5. Bind the exact short preview text revision. Do not place the text body in
   public logs or Evidence.
6. Confirm the staging destination is private, contained, writable, read-back
   verifiable and has a rollback/removal plan.
7. Confirm no paid Provider credential is selected and network egress will be
   disabled before inference.

Host/resource checks:

```powershell
$BvpGpuRows = @(& nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free,temperature.gpu --format=csv,noheader,nounits)
if ($LASTEXITCODE -ne 0 -or $BvpGpuRows.Count -ne 1) { throw 'GPU query failed' }
$BvpGpuFields = @($BvpGpuRows[0].Split(',') | ForEach-Object { $_.Trim() })
if ($BvpGpuFields.Count -ne 5 -or $BvpGpuFields[0] -ne 'NVIDIA GeForce RTX 4070 SUPER') { throw 'GPU identity mismatch' }
try { $BvpFreeVramMiB = [int]$BvpGpuFields[3]; $BvpGpuTemperatureC = [int]$BvpGpuFields[4] } catch { throw 'GPU numeric result invalid' }
if ($BvpFreeVramMiB -lt 8192 -or $BvpGpuTemperatureC -ge 80) { throw 'GPU resource gate failed' }
$BvpComputeApps = @(& nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv,noheader,nounits)
if ($LASTEXITCODE -ne 0) { throw 'GPU process query failed' }
if ($BvpComputeApps.Count -ne 0) { throw 'unknown GPU compute process present' }
Get-PSDrive -Name D,E | Select-Object Name,Free,Used
Get-BitLockerVolume -MountPoint 'D:','E:' | Select-Object MountPoint,VolumeStatus,ProtectionStatus
```

Required result:

- RTX 4070 SUPER identity remains exact;
- free VRAM is at least `8,192 MiB`, GPU temperature is below `80 C`, and no
  unknown compute process is using the device;
- the public model/runtime volume has at least
  `max(volume size * 15%, 200 GiB)` free;
- the exact private-media/staging leaf is separately proven encrypted at rest;
  failure or inability to observe BitLocker/EFS/equivalent protection blocks
  private audio access but does not invalidate already public model bytes;
- no incompatible GPU workload is displaced automatically;
- runtime/model roots are supplied explicitly and are not discovered by a
  broad filesystem search.

Any mismatch is `STOP / NOT_CONFIRMED`.

## 5. Existing runtime and model verification

First verify only the previously load-tested Windows isolated runtime/model.
Do not redownload merely because it is absent from the default PATH. WSL is not
an execution candidate in R0; it requires its own exact load-only Atomic Unit.

For a supplied Windows runtime, derive its private `Scripts\python.exe` path
but do not execute it yet. Before Sections 5.1 and 5.2 pass, only trusted host
PowerShell may hash explicit artifacts; do not import target packages or run
the target runtime. Do not print the resolved roots:

```powershell
$BvpPython = Join-Path $BvpRuntimeRoot 'Scripts\python.exe'
Get-FileHash -Algorithm SHA256 -LiteralPath $BvpQwenWheel | Select-Object Hash
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $BvpModelRoot 'config.json') | Select-Object Hash
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $BvpModelRoot 'model.safetensors') | Select-Object Hash
```

The exact accepted Windows matrix is Python 3.12.4, `qwen-tts 0.1.1`,
PyTorch/Torchaudio 2.11.0+cu130, Transformers 4.57.3, Accelerate 1.12.0 and
PyTorch SDPA. FlashAttention is not loaded for R0. The retained Qwen wheel and
the two known model prechecks must match Section 2, but these checks alone do
not prove an exact runtime or snapshot.

### 5.1 Installed-distribution and full-runtime trust gate — currently `STOP`

An installed-tree digest calculated from the same installed files is not a
trust anchor. Merged AU2B4/AU2B5 now parse the retained official wheel whose
SHA-256 is fixed in Section 2 and can make a bounded installed-payload read
observation plus a one-shot Windows locked-wheel diagnostic session. For the
`qwen_tts` distribution, those contracts:

1. parse the wheel's `*.dist-info/RECORD` without importing `qwen_tts`;
2. validate every hashed RECORD row's URL-safe SHA-256 and size against the
   installed distribution selected from the explicit isolated runtime;
3. reject absolute/escaping RECORD names, missing files, size/hash mismatches,
   and installed `qwen_tts` code or package-data files not listed in RECORD;
4. account separately for the RECORD self row, the exact four bounded
   pip-generated installation artifacts and the exact 17 untrusted
   `__pycache__/*.pyc` files; none becomes trusted package payload;
5. emit bounded counts, status, non-authority/no-effect fields and redacted
   public diagnostic projections; installed paths, source bodies and private
   fingerprints/digests are excluded from the public projection.

The actual locked-wheel probe completed with every handle released. Both that
receipt and the installed-payload observation are explicitly diagnostic only:
they do not authenticate a complete target runtime, survive as a capability,
or authorize import, reuse or load. A future consumer must revalidate within a
fresh live held session.

Before target launch, one accepted runtime aggregate must still anchor Python,
PyTorch, Torchaudio,
Transformers, Accelerate, Hugging Face Hub, SoundFile and their native
dependencies to retained artifacts plus RECORD/executable verification. A
self-generated digest, package version alone or `pip check` alone is
insufficient. No such complete accepted receipt is currently bound, so
`RUNTIME_REUSE_VERIFIED` cannot yet be issued.

### 5.2 Exact model snapshot gate — diagnostic observation merged; reuse `STOP`

Merged AU2B1 records the official exact model revision in Section 2. Its public
manifest contains all 13 official sibling paths with
bytes/SHA-256, including model weights, root config, generation config,
preprocessor config, text-tokenizer config/vocabulary/merge data and all
speech-tokenizer config/weights. Its semantic manifest digest is
`8ee07dcddf13d95aa225df9167d4695b42e245b431686d8acb26bbd4a5e80935`.

Merged AU2B2 provides the strict bounded verifier that:

- resolve every manifest entry beneath the explicit model root and reject path
  escape, reparse/symlink escape, missing files and hash/size mismatches;
- bind and verify every manifest-declared tokenizer and speech-tokenizer file;
  interpreting those configs into exact runtime inputs remains a later
  adapter/runtime responsibility and cannot be supplied by filename guess;
- requires the exact normalized 13-file set and rejects every extra file;
- bind the manifest digest to revision
  `5d83992436eae1d760afd27aff78a71d676296fc`.

The Owner-designated existing E: source matched size and SHA-256 for all 13
official files, but its 14 Hugging Face `.cache` metadata files correctly block
the strict exact-set observation. It was not deleted or rearranged. AU2B3
records the new task-owned clean leaf containing only the exact 13 files. The
merged verifier freshly observed that leaf as `VERIFIED` at
`2026-08-20T21:09:28.867368Z`, with all bodies hashed and receipt
`sha256:de3cf5ce56637fd088981afe0162b543507cd38ce0f414eaaa283754cf806ab6`.

That receipt is a point-in-time diagnostic, not a capability: model reuse,
model load and post-return state authority are false and consumer revalidation
is required. Re-downloading the same weights is unnecessary unless a fresh
observation finds the clean leaf missing or corrupt.

### 5.3 Load-only gate — not eligible until the full 5.1 aggregate is accepted

After the complete runtime aggregate is accepted, reacquire the fresh live
wheel/model revalidation required by Sections 5.1 and 5.2, apply the exact
temporary process egress block in Section 7, set offline variables, and perform
a current load-only probe from the local directory. The following target-Python
commands replace the execution comment inside the already created and
read-back-verified Firewall `try` block in Section 7. They must not be run as a
standalone block:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
& $BvpPython --version
if ($LASTEXITCODE -ne 0) { throw 'target Python version probe failed' }
& $BvpPython -I -c "import importlib.metadata as m, torch, torchaudio; print(m.version('qwen-tts'),m.version('transformers'),m.version('accelerate')); print(torch.__version__,torchaudio.__version__,torch.version.cuda,torch.cuda.is_available(),torch.cuda.get_device_name(0))"
if ($LASTEXITCODE -ne 0) { throw 'target runtime probe failed' }
& $BvpPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'target dependency check failed' }
& $BvpPython -I -c "import os,torch; from qwen_tts import Qwen3TTSModel; m=Qwen3TTSModel.from_pretrained(os.environ['BVP_TTS_MODEL_ROOT'],device_map='cuda:0',dtype=torch.bfloat16,attn_implementation='sdpa',local_files_only=True); langs={str(x).casefold() for x in m.get_supported_languages()}; assert m.model.tts_model_type=='base' and 'japanese' in langs; print('base',sorted(langs))"
if ($LASTEXITCODE -ne 0) { throw 'Qwen load-only probe failed' }
```

`base` and case-folded `japanese` must be observed. A network attempt, warning
indicating a remote fallback, different model type/language set, OOM or
incomplete terminal receipt is `STOP / NOT_CONFIRMED`. Only the conjunction of
5.1, 5.2 and 5.3 is `REUSE_VERIFIED`; then skip Section 6.

## 6. Conditional acquisition gate — currently `STOP / NOT_CONFIRMED`

This section becomes eligible only when Section 5 proves the runtime/model
missing or corrupt and a separate acquisition Atomic Unit freezes a complete
dependency artifact manifest. Record the missing/corrupt reason first. Never
update System Python, Conda, PATH, ComfyUI/H3 or another task runtime.

TASK-046 records two incompatible successful matrices: Windows
PyTorch/Torchaudio 2.11+cu130 with a locally built Windows FlashAttention
wheel, and WSL PyTorch/Torchaudio 2.8+cu128 with the official Linux
FlashAttention wheel. It does not expose a complete reusable wheel-hash
manifest for every transitive dependency. Therefore this R0 runbook does not
authorize construction of either environment. Do not combine their versions,
reports or artifacts.

The later acquisition unit may allow only these official package/model paths:

- `pypi.org` and `files.pythonhosted.org` for pinned Python artifacts;
- `huggingface.co` and its official LFS/Xet content endpoints for the exact
  public Qwen model revision;
- official Qwen/FlashAttention GitHub release endpoints only if an already
  evidenced exact dependency must be restored.

The future acquisition unit must freeze, before running anything:

- one OS/runtime matrix only;
- Python, PyTorch, Torchaudio, Qwen-TTS, Transformers, Accelerate,
  HuggingFace Hub and every required transitive wheel filename, source,
  version, bytes and SHA-256;
- SoX/ffmpeg/ffprobe source, version and executable hash;
- SoundFile wheel filename, version, bytes, SHA-256 and installed RECORD
  verification, plus the exact native library it loads;
- whether FlashAttention is omitted in favor of the previously successful
  SDPA inference path; if included, its exact ABI-specific artifact;
- expected download and unpacked bytes, rollback root and network allowlist.

Missing any coordinate remains `STOP / NOT_CONFIRMED`. R0 intentionally
contains no runnable acquisition/install command. The later acquisition unit
must additionally prove its runtime/model/temporary roots are absent, resolve
under one approved empty task-owned public-artifact parent beneath
`E:\BAI_AI` and are not shared caches before it creates them. Private
media/staging remains confined to its separately encrypted private parent. It
must use exact-file downloads with expected bytes/hashes, then freeze and
review a load-only checkpoint before Owner audio is read.

Rollback removes only the newly created task-owned runtime, model snapshot and
package-download staging roots after their resolved absolute paths are checked
to be under the approved public-artifact parent beneath `E:\BAI_AI`. Private
media/staging rollback is separate and remains under its encrypted private
parent. Never remove a shared Hugging Face or System cache.

## 7. Owner reference and preview admission

Before reading the audio body:

- `VoiceProfileRevision.consent.state == ACTIVE`;
- `subject_verified == true`;
- `OWNER_NARRATION_LOCAL` is allowed;
- exact model/license/capability is admitted;
- reference Asset/checksum and current rights evaluation are exact;
- preview text and reference transcript revisions are exact;
- preview text is at most 200 Unicode code points and the admitted maximum
  output duration is 60 seconds;
- authorization is unexpired and not previously consumed;
- output destination policy and quota/recovery/retention hashes are exact.

Private media inspection is read-only and suppresses path output:

```powershell
& $BvpFfprobe -v error -show_entries 'format=duration,size:stream=codec_name,sample_rate,channels,sample_fmt' -of json -- $BvpOwnerReferenceWav
if ($LASTEXITCODE -ne 0) { throw 'Owner reference probe failed' }
Get-FileHash -Algorithm SHA256 -LiteralPath $BvpOwnerReferenceWav | Select-Object Hash
Get-FileHash -Algorithm SHA256 -LiteralPath $BvpOwnerReferenceText | Select-Object Hash
Get-FileHash -Algorithm SHA256 -LiteralPath $BvpPreviewText | Select-Object Hash
```

Before running these commands, the accepted private runtime receipt must match
the exact SoundFile distribution and native library, and the supplied
`ffmpeg.exe`/`ffprobe.exe` paths, versions, sizes and SHA-256 values. Resolve
each executable beneath the admitted tools root, reject reparse/path escape,
and compare it with the receipt before Owner audio is opened. These expected
hashes are not present in current canonical Evidence; the next runtime/artifact
aggregate AU must freeze them or this step remains `STOP / NOT_CONFIRMED`.

Reject zero-byte, truncated, multi-speaker, clipped, noisy, untranscribed or
rights/consent-mismatched reference material. ICL requires the reference text
to be the exact transcript of the selected audio.

Environment variables are not an egress boundary. Before load-only or
inference, an Administrator-authorized runner creates a unique temporary
Windows Firewall outbound-block rule scoped only to the exact isolated Python
executable, verifies it, and removes it in `finally`:

```powershell
$ErrorActionPreference = 'Stop'
$BvpFirewallToken = [guid]::NewGuid().ToString('N')
$BvpFirewallRule = 'BVP-TASK014-' + $BvpFirewallToken
$BvpFirewallGroup = 'BAI-VIDEO-PRODUCTION-TASK014'
$BvpFirewallDescription = 'TASK014-EPHEMERAL-' + $BvpFirewallToken
$BvpFirewallCreationAttempted = $false
$BvpNameCollisions = @(Get-NetFirewallRule -ErrorAction Stop | Where-Object { $_.Name -eq $BvpFirewallRule })
if ($BvpNameCollisions.Count -ne 0) { throw 'pre-existing firewall rule collision' }
try {
  $BvpFirewallCreationAttempted = $true
  New-NetFirewallRule -Name $BvpFirewallRule -DisplayName $BvpFirewallRule -Group $BvpFirewallGroup -Description $BvpFirewallDescription -Direction Outbound -Program $BvpPython -Action Block -Profile Any -ErrorAction Stop | Out-Null
  $BvpRule = @(Get-NetFirewallRule -ErrorAction Stop | Where-Object { $_.Name -eq $BvpFirewallRule -and $_.DisplayName -eq $BvpFirewallRule -and $_.Group -eq $BvpFirewallGroup -and $_.Description -eq $BvpFirewallDescription })
  if ($BvpRule.Count -ne 1) { throw 'firewall rule count mismatch' }
  if (@(Get-NetFirewallRule -ErrorAction Stop | Where-Object { $_.Name -eq $BvpFirewallRule }).Count -ne 1) { throw 'foreign firewall collision' }
  $BvpProgram = @(Get-NetFirewallApplicationFilter -AssociatedNetFirewallRule $BvpRule[0] -ErrorAction Stop)
  if ($BvpProgram.Count -ne 1 -or $BvpRule[0].Enabled -ne 'True' -or $BvpRule[0].Direction -ne 'Outbound' -or $BvpRule[0].Action -ne 'Block' -or $BvpProgram[0].Program -ne $BvpPython) { throw 'firewall read-back mismatch' }
  $env:HF_HUB_OFFLINE = '1'
  $env:TRANSFORMERS_OFFLINE = '1'
  # Insert only the exact admitted Section 5.3 probe or one-shot adapter here.
} finally {
  if ($BvpFirewallCreationAttempted) {
    try {
      $BvpRulesToRemove = @(Get-NetFirewallRule -ErrorAction Stop | Where-Object { $_.Name -eq $BvpFirewallRule -and $_.DisplayName -eq $BvpFirewallRule -and $_.Group -eq $BvpFirewallGroup -and $_.Description -eq $BvpFirewallDescription })
      if ($BvpRulesToRemove.Count -gt 0) {
        $BvpRulesToRemove | Remove-NetFirewallRule -ErrorAction Stop
      }
      if (@(Get-NetFirewallRule -ErrorAction Stop | Where-Object { $_.Name -eq $BvpFirewallRule -and $_.DisplayName -eq $BvpFirewallRule -and $_.Group -eq $BvpFirewallGroup -and $_.Description -eq $BvpFirewallDescription }).Count -ne 0) { throw 'task firewall cleanup verification failed' }
      if (@(Get-NetFirewallRule -ErrorAction Stop | Where-Object { $_.Name -eq $BvpFirewallRule }).Count -ne 0) { throw 'foreign firewall collision preserved' }
    } catch {
      throw ('firewall cleanup failed: ' + $_.Exception.GetType().Name)
    }
  }
}
```

If Administrator authority, rule creation, rule read-back or cleanup cannot be
verified, stop. This native firewall mutation is not executed by AU2A.

## 8. One-shot preview execution

Execution must occur through the TASK-043 service transition that atomically
consumes the exact Admission authorization. Directly running an inference
script is not a valid Product execution receipt.

The private inference adapter must:

1. load only the exact local snapshot with offline flags enabled;
2. read the three private files without logging their bodies or paths;
3. call the Base-model voice-clone API with the exact reference audio,
   reference transcript, Product `ja-JP` mapped explicitly to engine
   `Japanese`, and `x_vector_only_mode=False`;
4. generate one preview only; no automatic retry after dispatch ambiguity;
5. write the raw model output inside the admitted staging root;
6. read it back, hash it and record sample rate/frame count;
7. normalize a separate derivative to 48 kHz mono PCM_S24LE;
8. preserve the untreated raw output and normalized untreated WAV;
9. create the content-addressed TASK-014 staged receipt and measured alignment
   Evidence; do not publish an Asset.

The next implementation AU must freeze and test this exact Qwen call surface:

```python
model = Qwen3TTSModel.from_pretrained(
    exact_local_model_root,
    device_map="cuda:0",
    dtype=torch.bfloat16,
    attn_implementation="sdpa",
    local_files_only=True,
)
assert model.model.tts_model_type == "base"
assert "japanese" in {str(value).casefold() for value in model.get_supported_languages()}
reference_waveform, reference_sample_rate = soundfile.read(
    exact_reference_wav, dtype="float32", always_2d=False
)
assert reference_waveform.ndim == 1
wavs, output_sample_rate = model.generate_voice_clone(
    text=approved_preview_text,
    language="Japanese",
    ref_audio=(reference_waveform, reference_sample_rate),
    ref_text=exact_reference_transcript,
    x_vector_only_mode=False,
    max_new_tokens=2048,
)
assert len(wavs) == 1
```

No path/URL/base64 string may be passed as `ref_audio`; only the already loaded
local waveform tuple is accepted. The outer Windows runner starts the adapter
hidden, permits at most 180 seconds, terminates only that child on timeout and
records `UNKNOWN` with no replay. Checkpoint sampling defaults from the pinned
`generation_config.json` remain unchanged. Output over 60 seconds, more than
100 MiB, non-finite samples or more/less than one waveform fails QA.

The private adapter creates a cryptographically unique `BVP_RENDER_ID`, derives
both filenames from it, verifies both are absent and applies a 100 MiB limit to
each file. Normalization uses a fixed command and never overwrites either file:

```powershell
if (-not $BvpRenderId) { throw 'missing render id' }
$BvpRawPreview = Join-Path $BvpStagingRoot ($BvpRenderId + '.raw.wav')
$BvpNormalizedPreview = Join-Path $BvpStagingRoot ($BvpRenderId + '.48k-mono-s24.wav')
if ((Test-Path -LiteralPath $BvpRawPreview) -or (Test-Path -LiteralPath $BvpNormalizedPreview)) { throw 'output collision' }
& $BvpFfmpeg -nostdin -v error -n -i $BvpRawPreview -map 0:a:0 -ac 1 -ar 48000 -c:a pcm_s24le $BvpNormalizedPreview
if ($LASTEXITCODE -ne 0) { throw 'normalization failed' }
& $BvpFfprobe -v error -show_entries 'format=duration,size:stream=codec_name,sample_rate,channels,sample_fmt' -of json -- $BvpNormalizedPreview
if ($LASTEXITCODE -ne 0) { throw 'normalized preview probe failed' }
Get-FileHash -Algorithm SHA256 -LiteralPath $BvpRawPreview,$BvpNormalizedPreview | Select-Object Hash
```

### 8.1 Alignment gate — currently `BLOCKED`

The pinned Qwen wrapper returns waveform/sample-rate, not canonical character
timestamps. TASK-006 FasterWhisper word timestamps are explicitly deferred and
cannot be relabeled as measured code-point alignment. No alignment model,
normalizer/segmenter, policy revision or exact licensed Japanese artifact is
currently admitted for TASK-014. Placeholder, uniform-duration and manually
invented rows are prohibited.

Before dispatch consumption, a separate DEV-4 alignment AU must select an
exact commercially eligible local forced-aligner, pin its model/code/license
hashes, define Japanese normalization/segmentation and code-point projection,
bind the produced timing payload to the exact receipt/artifact hashes, and pass
text substitution, punctuation/newline, overlap/gap/range and low-confidence
tests. Until that AU is Judge-accepted, one-shot Owner preview inference remains
`BLOCKED`; AU2A performs no Owner audio read or model execution.

## 9. Failure and recovery

- Failure before dispatch consumption: no inference occurred; fix preflight and
  use a new eligible Job/authorization as defined by TASK-043.
- Failure after dispatch or unknown terminal state: persist `UNKNOWN`; do not
  replay. Inspect contained output and reconciliation Evidence.
- Proven completed output after an `UNKNOWN`: accept only through
  `ACCEPT_PROVEN_SUCCESS` with the exact content-addressed receipt reference
  and digest.
- CUDA OOM, driver reset, host freeze or incomplete WAV: mark failure/unknown,
  retain evidence, do not lower safety flags or retry automatically.
- Hash, model, license, Consent, rights, path-containment or expiry mismatch:
  stop before audio access or inference.

No failure path may upload Owner audio, switch to ElevenLabs, select another
model revision, use a fork, publish an Asset or invoke REAPER/iZotope.

## 10. Evidence and acceptance

Public Evidence may contain:

- exact code/model versions and approved artifact hashes;
- body-free project/admission/job/receipt digests;
- GPU class, peak VRAM, durations and audio technical properties;
- decision/reason codes and no-effect flags.

It must not contain Owner text, transcript, audio, absolute paths, Voice ID,
voice embedding, private receipt/artifact handles or Consent evidence bodies.

Preview acceptance requires:

- TASK-043 store-loaded terminal Job is `SUCCEEDED` with exact receipt, or an
  exact hash-linked proven-success reconciliation;
- 48 kHz mono PCM_S24LE normalized WAV read-back and checksum PASS;
- alignment/character coverage and range PASS;
- Owner listening result recorded separately as QA Evidence;
- untreated files retained for comparison;
- Asset publication, placement and finishing remain false.

Only after this bounded preview is accepted may a separate Atomic Unit request
TASK-035 REAPER/iZotope finishing. That unit must preserve the untreated source
and record REAPER/license/plugin-chain/native output QA separately.

## 11. Current gate result

At fresh-main synchronization time:

- Owner authority for bounded free local preview and Owner voice use: `YES`;
- mandatory runbook: `JUDGE_ACCEPTED / FRESH_MAIN_VALIDATED / RUNBOOK_FROZEN /
  EXECUTION_BLOCKED / UNCOMMITTED`; independent Tester and Critic/Judge result
  is `C0 / H0 / M0`;
- TASK-043/TASK-014 bridge: `JUDGE_ACCEPTED / UNCOMMITTED` in a separate
  worktree and therefore not yet an execution checkout dependency;
- Owner-designated public AI storage design: recorded in
  `E:\BAI_AI\README.md`; public artifacts and private media are separated;
- public pinned model manifest: `MERGED` via PR #195; canonical digest
  `8ee07dcd...e80935`;
- strict point-in-time snapshot verifier: `MERGED` via PR #197;
- clean exact 13-file model leaf Evidence and fresh diagnostic observation:
  `MERGED` via PR #198; reuse/load/post-return Authority remains false;
- pinned Qwen wheel/installed-payload diagnostic and locked-wheel session:
  `MERGED` via PR #193; complete runtime reuse Authority remains false;
- complete Python/PyTorch/Torchaudio/Transformers/Accelerate/Hugging Face Hub/
  SoundFile/native runtime aggregate and ffmpeg/ffprobe artifact receipts:
  `NOT_BOUND`;
- exact Owner reference WAV/transcript, preview text and private staging
  bindings: `NOT_BOUND`;
- model weight re-download: `OWNER_AUTHORIZED / NOT_NEEDED / NOT_EXECUTED`;
- install/inference/audio access: `NOT_STARTED`.

The next safe action is a DEV-4 complete runtime/artifact aggregate verifier
unit. Only after it is accepted may a fresh held-wheel session plus a fresh
point-in-time model revalidation and offline 12Hz Base load-only probe start.
No acquisition, Owner audio read or inference starts from this document alone.

## 12. References

- `docs/ai-team/tasks/TASK-046/p-vs-4b-qwen3-tts-06b-technical-probe-r3-evidence-2026-08-17.md`
- `docs/ai-team/tasks/TASK-046/p-vs-4b-qwen3-tts-dependency-setup-r4-evidence-2026-08-17.md`
- `docs/ai-team/tasks/TASK-046/voice-studio-runtime-license-capability-probe-plan-2026-08-15.md`
- Official source: `https://github.com/QwenLM/Qwen3-TTS`
- Official pinned model: `https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base`
