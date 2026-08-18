# Build BAI Voice Model Builder Installer on Windows

This guide extracts the developer build procedure from the general Voice Model Builder user guide so every Windows executable / installer has a dedicated build document.

The current Voice Model Builder artifact is a Technical Preview. Building it does **not** start model downloads, dataset training, speech generation, publication, or release creation.

## 1. Required tools

The validated packaging recipe currently uses:

- a Windows Python runtime compatible with the Task-046 packaging contract;
- project runtime dependency `jsonschema`;
- `PyInstaller == 6.22.0`;
- Inno Setup `7.1.0` compiler (`ISCC.exe`).

The previously validated absolute-path example uses the `E:\BAI_AI` layout. You may use another path, but pass explicit executable paths and do not silently fall back to an unexpected Python or Inno Setup installation.

## 2. Create the packaging environment

From the repository root, using the validated example layout:

```powershell
E:\BAI_AI\runtimes\Python31314\python.exe -m venv E:\BAI_AI\envs\task046-voice-model-builder-package-py31314
E:\BAI_AI\envs\task046-voice-model-builder-package-py31314\Scripts\python.exe -m pip install --upgrade pip
E:\BAI_AI\envs\task046-voice-model-builder-package-py31314\Scripts\python.exe -m pip install "jsonschema>=4.20,<5" pyinstaller==6.22.0
```

## 3. Build the installer

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows\build-task046-voice-model-builder-installer.ps1 `
  -PythonExe E:\BAI_AI\envs\task046-voice-model-builder-package-py31314\Scripts\python.exe `
  -InnoCompiler E:\BAI_AI\runtimes\InnoSetup\7.1.0\ISCC.exe `
  -WorkRoot E:\BAI_AI\build\task046-voice-model-builder-installer `
  -OutputDirectory E:\BAI_AI\artifacts\task046-voice-model-builder-installer
```

Use a clean work/output directory for a fresh candidate.

## 4. What the build script verifies

The build path verifies the selected Python/tool identities, packages the client, and includes the required guide, license, manifest, hashes, and third-party notices. Missing or ambiguous license material is fail-closed.

## 5. What the build does not authorize

A local build does not automatically:

- publish a GitHub Release;
- sign the installer;
- download a voice model;
- start dataset training;
- generate or publish synthesized audio.

## 6. Usage

After producing or downloading an installer candidate, continue with [VOICE-MODEL-BUILDER.md](../user/VOICE-MODEL-BUILDER.md).
