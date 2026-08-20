# Build BAI DbD Trivia Editor EXE on Windows

This builds the small manual DbD trivia registration application. It is separate from the main BAI Video Production EXE but uses the same Python package and Trivia Store contract.

## Prerequisites

- Windows 10/11
- Python 3.11-3.13
- repository checkout

Install build dependencies once:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[windows-build]"
```

## Build

```powershell
.\build-dbd-trivia-editor-exe.bat
```

Output:

```text
builds\
  BAI DbD Trivia Editor\
    BAI DbD Trivia Editor.exe
    _internal\
```

Use the whole directory because this is a PyInstaller one-dir build.

## Custom Python

```powershell
$env:BVP_BUILD_PYTHON = "C:\Python312\python.exe"
.\build-dbd-trivia-editor-exe.bat
```

The build does not publish, sign, upload, or call any AI provider.

Usage: [BAI DbD Trivia Editor Usage](../user/DBD-TRIVIA-EDITOR-USAGE.md)
