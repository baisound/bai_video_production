# Build BAI Voice Capture OBS Installer on Windows

This is the dedicated source-build guide for the `BAI Voice Capture` OBS plugin/runtime/installer chain.

The current development candidate targets the OBS version and toolchain recorded in the repository. Do not substitute newer toolchains silently: if the recorded build graph cannot be reproduced, stop and resolve the compatibility difference explicitly.

## 1. Validated toolchain contract

The repository documentation currently records:

- OBS Studio source `32.2.1` with submodules;
- Visual Studio Build Tools 2026;
- Windows SDK `10.0.26100.0`;
- CMake `3.30.5`;
- Inno Setup `7.1.0`.

Use explicit paths instead of relying on an unknown `cmake`, compiler, or Inno Setup instance from `PATH`.

## 2. Prepare paths

Example:

```powershell
$ObsSource = 'C:\src\obs-studio-32.2.1'
$PluginSource = Join-Path $ObsSource 'plugins\bai-voice-capture'
$Cmake = 'C:\Tools\CMake\3.30.5\bin\cmake.exe'
$Ctest = 'C:\Tools\CMake\3.30.5\bin\ctest.exe'
$Csc = 'C:\Program Files\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
$Iscc = 'C:\Program Files (x86)\Inno Setup 7\ISCC.exe'
```

## 3. Obtain the matching OBS source and plugin source

```powershell
git clone --recursive --branch 32.2.1 https://github.com/obsproject/obs-studio.git $ObsSource
New-Item -ItemType Directory -Path $PluginSource | Out-Null
Expand-Archive .\packaging\release-assets\task047\bai-voice-capture-0.1.0-dev.10-source.zip -DestinationPath $PluginSource
```

## 4. Configure, build, test, and package

```powershell
& "$PluginSource\scripts\configure.ps1" -CMakeExecutable $Cmake
& "$PluginSource\scripts\build-controller.ps1" -Compiler $Csc
& "$PluginSource\scripts\build.ps1" -CMakeExecutable $Cmake -Configuration Release
& "$PluginSource\scripts\test.ps1" -CMakeExecutable $Cmake -CtestExecutable $Ctest -Configuration Release
& "$PluginSource\scripts\package.ps1" -Configuration Release
```

## 5. Build the installer

```powershell
$Artifacts = Join-Path (Split-Path $ObsSource -Parent) 'artifacts'
$RuntimeZip = Join-Path $Artifacts 'bai-voice-capture-0.1.0-dev.10-windows-x64.zip'
$InstallerWork = Join-Path $env:TEMP 'bai-task047-installer-build-work'
$InstallerOut = Join-Path $env:TEMP 'bai-task047-installer-build-output'

powershell -ExecutionPolicy Bypass -File .\tools\windows\build-task047-obs-installer.ps1 `
  -RuntimeZip $RuntimeZip `
  -InnoCompiler $Iscc `
  -WorkRoot $InstallerWork `
  -OutputDirectory $InstallerOut
```

The installer builder refuses to overwrite an existing work/output path. Use new empty paths for a new build candidate.

## 6. Known compatibility note

The recorded development evidence notes that the validated CMake version may not recognize the Visual Studio 18 generator during a completely fresh configure. Do **not** silently fall back to an unrelated toolchain. Resolve the toolchain mismatch, then repeat the build with explicit paths.

## 7. What this does not do

The procedure does not automatically sign, publish, install into OBS, load the plugin, or begin recording.

For installation, recording, recovery, and normal operation continue with [OBS-VOICE-CAPTURE-PLUGIN.md](../user/OBS-VOICE-CAPTURE-PLUGIN.md).
