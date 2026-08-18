# Windows Environment Setup for DbD Game Intelligence

This guide describes the Windows environment required by the Task-049 DbD Game Intelligence features, `BAI Video Production.exe`, `BAI DbD Training Studio.exe`, and `BAI DbD Trivia Editor.exe`.

It deliberately separates **build-time dependencies**, **runtime media/OCR dependencies**, **ASR model dependencies**, and **LLM Provider configuration** so users do not install unrelated software.

## 1. Quick requirement matrix

| Feature | Required |
|---|---|
| Build BVP / Training Studio / Trivia Editor | Python 3.11+ supported by the project, `pip`, project `windows-build` extra |
| Video normalization / exact-frame extraction / training slices | FFmpeg / ffprobe available to the application |
| Upper-right DbD text recognition | Tesseract executable; Japanese trained data when Japanese OCR is selected |
| Video/transcript learning and local ASR | `faster-whisper` project extra; model files downloaded or pre-cached when explicitly allowed |
| Cloud LLM commentary | Configured BVP Provider route + API credential + network access; **no OpenAI/Anthropic/Google Python SDK is required by the current implementation** |
| Local LLM commentary | **Not wired into TASK-049 at present. Do not install Ollama/LM Studio solely for this feature unless a later implementation explicitly adds a local Provider adapter.** |
| GPU acceleration for Faster-Whisper | Optional; CPU operation remains a valid path. GPU runtime compatibility must be verified separately. |

## 2. Python and project virtual environment

The repository declares Python `>=3.11`. For a predictable local Windows build, use one explicitly selected 64-bit Python and a repository-local virtual environment.

Example using Python 3.12:

```powershell
cd C:\home\baisound\projects\bai-video-production
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,asr,windows-build]"
```

Verification:

```powershell
python --version
python -c "import ai_video_production; print(ai_video_production.__version__)"
python -c "import faster_whisper; print('faster-whisper OK')"
python -c "import PyInstaller; print(PyInstaller.__version__)"
```

If PowerShell blocks activation, you may run `.venv\Scripts\python.exe` directly instead of changing the machine-wide execution policy.

## 3. FFmpeg / ffprobe

Task-049 uses FFmpeg as an external executable for exact-frame extraction, ROI slice generation, normalization and media preflight.

Install a trusted Windows build referenced from the official FFmpeg download page, then either add its `bin` directory to your user PATH or enter an explicit executable path in the Training Studio / command invocation.

Verification:

```powershell
ffmpeg -version
ffprobe -version
Get-Command ffmpeg.exe
Get-Command ffprobe.exe
```

Do not continue video-learning validation if the intended FFmpeg executable cannot be identified.

## 4. Tesseract OCR

Upper-right DbD notification recognition uses the external `tesseract` CLI adapter.

The Tesseract project does not currently publish a first-party modern Windows installer; its official documentation points Windows users to available Windows builds or to building via supported toolchains. Use a trusted Windows installation method and verify the exact executable you intend to use.

For Japanese recognition, ensure the Japanese trained-data file is installed in the active `tessdata` directory.

Verification:

```powershell
tesseract --version
tesseract --list-langs
Get-Command tesseract.exe
```

The language list should contain the language code you intend to use (for example `jpn` when using Japanese OCR).

Training Studio also allows an explicit Tesseract executable value; PATH modification is therefore optional if you provide an absolute executable path.

## 5. Faster-Whisper and speech models

The repository pins the supported package range through the `asr` / `windows-build` extras:

```text
faster-whisper>=1.2.1,<2
```

Install through the project extra rather than an unrelated global Python environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[asr]"
```

The Faster-Whisper model itself is separate from the Python package. A model may be downloaded the first time a workflow explicitly permits model download, or it may be prepared in advance in the local cache. Do not assume that installing the Python package has installed all model weights.

CPU verification is the safest initial check:

```powershell
.\.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; print('faster-whisper import OK')"
```

GPU execution is optional and should only be enabled after confirming the NVIDIA/CTranslate2 runtime compatibility for the machine. If GPU setup is uncertain, begin with CPU for functional validation.

## 6. LLM setup: what actually needs to be installed

### 6.1 Current TASK-049 implementation

The current commentary LLM adapter reuses BVP's Provider execution layer and calls configured cloud APIs over HTTPS. It does not require the OpenAI, Anthropic, or Google Python SDK packages.

Supported Provider families in the current execution layer include:

- OpenAI;
- Anthropic;
- Google.

Therefore **there is no separate LLM model installation step for cloud commentary**.

What you need instead is:

1. a Provider / Model route configured in BVP;
2. the relevant API credential stored through the supported Windows credential flow;
3. network access;
4. explicit execution authorization when the LLM call is actually requested.

The API key must not be committed to the repository or stored in plain-text project JSON.

### 6.2 Open the BVP AI connection settings

From the repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-ai-connection-settings.ps1
```

Use the **Secure credentials** section to store/delete credentials in Windows Credential Manager. Saving a credential does not itself call a Provider or start billing.

### 6.3 Local LLMs

TASK-049 does not currently contain an Ollama, llama.cpp, LM Studio, or other local-LLM text-generation adapter for commentary. Installing one of those runtimes will therefore not make local commentary work automatically.

If local LLM support is added later, it should be implemented as a Provider adapter behind the same `CommentaryLlmService` / Fact Validator boundary instead of bypassing canonical CGEL / Knowledge facts.

## 7. Build the three Task-049 desktop applications

After the common environment is verified:

```powershell
.\build-windows-exe.bat
.\build-dbd-training-studio-exe.bat
.\build-dbd-trivia-editor-exe.bat
```

See [WINDOWS-EXE-BUILD-INDEX.md](WINDOWS-EXE-BUILD-INDEX.md) for the individual guides.

## 8. Recommended verification order

```powershell
# 1. Repository / Python
python -c "import ai_video_production; print(ai_video_production.__version__)"

# 2. Media tools
ffmpeg -version
ffprobe -version

# 3. OCR when needed
tesseract --version
tesseract --list-langs

# 4. ASR import
python -c "import faster_whisper; print('faster-whisper OK')"

# 5. Focused tests
python -m pytest -q tests/test_task049_dbd_training_workspace.py tests/test_task049_dbd_hud_detectors.py tests/test_task049_game_commentary_llm.py

# 6. Build the intended EXE only
```

## 9. External reference sources

- Python for Windows: https://www.python.org/downloads/windows/
- FFmpeg downloads: https://ffmpeg.org/download.html
- Tesseract installation/download documentation: https://tesseract-ocr.github.io/tessdoc/Installation.html
- Faster-Whisper project: https://github.com/SYSTRAN/faster-whisper

Provider-specific credentials and billing remain external-service concerns; use the Provider's current official documentation when creating or rotating credentials.
