# Building the Owner Voice Runtime Installer

This is the developer guide for the Windows installer that provisions the complete
SRT-to-Owner-Voice-WAV runtime. End users should read
[SRT-OWNER-VOICE-WAV.md](../user/SRT-OWNER-VOICE-WAV.md) instead.

## Delivered behavior

The installer is per-user and keeps application files separate from Owner data. It:

1. asks for a safe local data root with at least 12 GB free;
2. reuses an installed Python 3.12 base or installs the official PSF-signed Python 3.12.10 base,
   then creates a dedicated venv below the selected root;
3. installs pinned PyTorch/Torchaudio 2.11.0 CUDA 13.0, Qwen-TTS 0.1.1,
   imageio-ffmpeg 0.6.0, and the exact BAI Video Production wheel;
4. reuses an exact verified model or downloads Qwen3-TTS 0.6B Base revision
   `5d83992436eae1d760afd27aff78a71d676296fc`;
5. verifies three large model files, CUDA, ffmpeg, package dependencies, and a GPU
   model load without generating audio;
6. publishes `runtime-config.json` and a stable per-user command copy only after PASS. WAV generation
   remains an explicit PowerShell command.

The official Qwen package recommends a fresh isolated Python 3.12 environment. The model is
Apache-2.0 and its official model card describes the 0.6B Base checkpoint as voice-cloning capable:
[Qwen3-TTS source](https://github.com/QwenLM/Qwen3-TTS),
[Qwen model card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base).
Hugging Face supports full commit hashes for `revision` and a fixed `local_dir`:
[download API](https://huggingface.co/docs/huggingface_hub/package_reference/file_download).

## Pinned inputs

| Input | Pin / digest |
|---|---|
| Python installer | 3.12.10 x64, SHA-256 `67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb`, valid Python Software Foundation Authenticode |
| Inno Setup | 7.1.0 compiler SHA-256 `d06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a` |
| PyTorch / Torchaudio | `2.11.0+cu130` |
| Qwen-TTS | `0.1.1` |
| imageio-ffmpeg | `0.6.0` |
| Qwen model revision | `5d83992436eae1d760afd27aff78a71d676296fc` |

Python.org states that 3.12.10 was the final 3.12 release with Windows binary installers:
[Python 3.12.10 release](https://www.python.org/downloads/release/python-31210/).

## Source files

- `packaging/task093_owner_voice_runtime_installer.iss`
- `tools/windows/build-task093-owner-voice-runtime-installer.ps1`
- `tools/windows/install-owner-voice-runtime.ps1`
- `tools/windows/make-owner-voice-wav.ps1`
- `src/ai_video_production/owner_voice_runtime.py`
- `src/ai_video_production/task014_srt_owner_voice_wav.py`

## Build

Use a clean TASK-093 worktree. Every output path must be a fresh nested directory in that worktree.
Do not use a drive root or direct child. The build Python needs `pip`; it is not the runtime Python.

```powershell
$Repo = 'C:\home\baisound\projects\bai-video-production\.worktrees\task093-owner-voice-runtime-installer'
$BuildPython = 'C:\home\baisound\projects\bai-video-production\.worktrees\release-20260916\.release-runtime\py31314\Scripts\python.exe'
$PythonInstaller = Join-Path $Repo '.task093-build-inputs\python-3.12.10-amd64-r01\python-3.12.10-amd64.exe'
$Iscc = 'E:\BAI_AI\runtimes\InnoSetup\7.1.0\ISCC.exe'
$Work = Join-Path $Repo '.task093-build\owner-voice-runtime-r01'
$Output = Join-Path $Repo '.task093-build\owner-voice-installer-r01'

& (Join-Path $Repo 'tools\windows\build-task093-owner-voice-runtime-installer.ps1') `
  -BuildPython $BuildPython `
  -PythonInstaller $PythonInstaller `
  -IsccPath $Iscc `
  -WorkRoot $Work `
  -OutputDirectory $Output `
  -Version '0.24.2'
```

The builder verifies the PSF signature and exact Python/Inno hashes, builds the exact-version wheel,
generates `runtime-manifest.json`, and compiles the installer. It performs no runtime/model download.

## Verification

Run the effect-zero contract and Python tests first:

```powershell
.\tools\windows\test-task093-owner-voice-runtime-installer.ps1
python -m pytest -q tests/test_owner_voice_runtime.py tests/test_task014_srt_owner_voice_wav.py
python -m compileall -q src tests
```

For a real fresh installer probe, allocate a unique nested temporary directory and pass it in silent mode:

```powershell
$Probe = Join-Path ([IO.Path]::GetTempPath()) ('bvp-task093-native-' + [guid]::NewGuid().ToString('N'))
$App = Join-Path $Probe 'installed\app'
$Data = Join-Path $Probe 'data\owner-voice'
& .\bai-owner-voice-runtime-0.24.2-windows-x64-setup.exe `
  /VERYSILENT /SUPPRESSMSGBOXES /NORESTART "/DIR=$App" "/DataRoot=$Data" "/LOG=$Probe\installer.log"
```

PASS requires installer exit 0, `runtime-config.json` status `READY`, exact package versions,
all three model hashes, CUDA true, ffmpeg execution, model load-only true, and generation false.
Do not use an Owner recording for installer verification. Preserve required Evidence before any exact
probe directory cleanup.

## Repair, uninstall, and release

Repair means rerunning the same downloaded installer. It executes the same pinned provisioning script;
a correct existing model is reused and partial or wrong files never become READY. Uninstall removes
`{app}` only. Runtime, model, receipts, datasets, recordings, generated WAV files, and the stable command
copy remain outside `{app}`.

After hosted checks are green and the PR is merged, create an annotated version tag from exact main,
build from that tag, publish the installer with the other v0.24.2 assets, upload a complete SHA256SUMS,
and read back each GitHub asset digest. Building does not itself authorize publishing.

## Training boundary

This installer completes zero-shot SRT-to-Owner-Voice-WAV. It deliberately does not install FlashAttention,
the CUDA compiler, TensorBoard, a training recipe, or claim 0.6B fine-tuning. Keep the separate training
investigation guides and Evidence for that developer-only lane.
