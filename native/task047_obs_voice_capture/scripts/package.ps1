param(
  [ValidateSet('Release','RelWithDebInfo','Debug','MinSizeRel')]
  [string]$Configuration = 'Release',
  [string]$BuildDirectory = '',
  [string]$ControllerPath = '',
  [string]$StageDirectory = '',
  [string]$ArtifactDirectory = '',
  [switch]$SourceOnly
)

$ErrorActionPreference = 'Stop'
$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$obsSource = (Resolve-Path (Join-Path $pluginRoot '..\..')).Path
$operationRoot = (Resolve-Path (Join-Path $obsSource '..')).Path
$buildDir = if ([string]::IsNullOrWhiteSpace($BuildDirectory)) {
  Join-Path $obsSource 'build_x64'
} else {
  (Resolve-Path -LiteralPath $BuildDirectory).Path
}
$stageRoot = if ([string]::IsNullOrWhiteSpace($StageDirectory)) {
  Join-Path $operationRoot 'staging-install'
} else {
  [IO.Path]::GetFullPath($StageDirectory)
}
$artifactRoot = if ([string]::IsNullOrWhiteSpace($ArtifactDirectory)) {
  Join-Path $operationRoot 'artifacts'
} else {
  [IO.Path]::GetFullPath($ArtifactDirectory)
}
$operationPrefix = $operationRoot.TrimEnd('\') + '\'
foreach ($outputRoot in @($stageRoot,$artifactRoot)) {
  if (!$outputRoot.StartsWith($operationPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Package output escapes the operation root: $outputRoot"
  }
}
$version = (Get-Content -LiteralPath (Join-Path $pluginRoot 'VERSION') -Raw).Trim()

New-Item -ItemType Directory -Force -Path $stageRoot,$artifactRoot | Out-Null

$sourceFiles = @(
  'CMakeLists.txt','VERSION','README.md','LICENSE','NOTICE.md','cmake\verify-package.cmake',
  'include\bai_obs_capture\bounded_spsc_queue.hpp','include\bai_obs_capture\capture_protocol.hpp',
  'include\bai_obs_capture\capture_core.hpp','include\bai_obs_capture\ipc_client.hpp',
  'src\capture_core.cpp','src\ipc_client.cpp','src\obs_plugin.cpp',
  'tests\queue_tests.cpp','tests\capture_core_tests.cpp','tests\security_tests.cpp',
  'tests\obs-stubs\obs-module.h','scripts\configure.ps1','scripts\build.ps1','scripts\test.ps1',
  'scripts\build-controller.ps1','scripts\generate-manifest.ps1','scripts\package.ps1',
  'controller\BaiVoiceCaptureController.cs','package-manifest.schema.json',
  'resources\locale\en-US.ini','resources\locale\ja-JP.ini'
)

$sourceStage = Join-Path $stageRoot "bai-voice-capture-$version-source"
if (Test-Path -LiteralPath $sourceStage) { throw "Source stage already exists: $sourceStage" }
foreach ($relative in $sourceFiles) {
  $from = Join-Path $pluginRoot $relative
  if (!(Test-Path -LiteralPath $from)) { throw "Missing frozen source file: $relative" }
  $to = Join-Path $sourceStage $relative
  New-Item -ItemType Directory -Force -Path (Split-Path $to -Parent) | Out-Null
  Copy-Item -LiteralPath $from -Destination $to
}
$obsCopying = Join-Path $obsSource 'COPYING'
if (!(Test-Path -LiteralPath $obsCopying)) {
  $obsCopying = Join-Path $pluginRoot 'UPSTREAM-OBS-COPYING.txt'
}
if (!(Test-Path -LiteralPath $obsCopying)) { throw 'OBS COPYING file missing' }
Copy-Item -LiteralPath $obsCopying -Destination (Join-Path $sourceStage 'UPSTREAM-OBS-COPYING.txt')
& (Join-Path $PSScriptRoot 'generate-manifest.ps1') -InputRoot $sourceStage `
  -OutputPath (Join-Path $sourceStage 'package-manifest.json') -PackageKind SOURCE -Version $version
$sourceZip = Join-Path $artifactRoot "bai-voice-capture-$version-source.zip"
if (Test-Path -LiteralPath $sourceZip) { throw "Source artifact already exists: $sourceZip" }
Compress-Archive -Path (Join-Path $sourceStage '*') -DestinationPath $sourceZip -CompressionLevel Optimal

if (!$SourceOnly) {
  $dll = Join-Path $buildDir "plugins\bai-voice-capture\$Configuration\bai-voice-capture.dll"
  if (!(Test-Path -LiteralPath $dll -PathType Leaf)) {
    throw "Runtime packaging requires the exact configured plugin DLL: $dll"
  }
  $runtimeStage = Join-Path $stageRoot "bai-voice-capture-$version-windows-x64"
  if (Test-Path -LiteralPath $runtimeStage) { throw "Runtime stage already exists: $runtimeStage" }
  $binDir = Join-Path $runtimeStage 'obs-plugins\64bit'
  $dataDir = Join-Path $runtimeStage 'data\obs-plugins\bai-voice-capture\locale'
  New-Item -ItemType Directory -Force -Path $binDir,$dataDir | Out-Null
  Copy-Item -LiteralPath $dll -Destination (Join-Path $binDir 'bai-voice-capture.dll')
  Copy-Item -Path (Join-Path $pluginRoot 'resources\locale\*.ini') -Destination $dataDir
  Copy-Item -LiteralPath (Join-Path $pluginRoot 'LICENSE') -Destination $runtimeStage
  Copy-Item -LiteralPath (Join-Path $pluginRoot 'NOTICE.md') -Destination $runtimeStage
  Copy-Item -LiteralPath $obsCopying -Destination (Join-Path $runtimeStage 'UPSTREAM-OBS-COPYING.txt')
  $controller = if ([string]::IsNullOrWhiteSpace($ControllerPath)) {
    Join-Path $pluginRoot 'controller\build\bai-voice-capture-controller.exe'
  } else {
    (Resolve-Path -LiteralPath $ControllerPath).Path
  }
  if (!(Test-Path -LiteralPath $controller)) { throw 'Runtime packaging requires the tested recording controller' }
  $controllerDir = Join-Path $runtimeStage 'controller'
  New-Item -ItemType Directory -Force -Path $controllerDir | Out-Null
  Copy-Item -LiteralPath $controller -Destination $controllerDir
  & (Join-Path $PSScriptRoot 'generate-manifest.ps1') -InputRoot $runtimeStage `
    -OutputPath (Join-Path $runtimeStage 'package-manifest.json') -PackageKind RUNTIME -Version $version
  $runtimeZip = Join-Path $artifactRoot "bai-voice-capture-$version-windows-x64.zip"
  if (Test-Path -LiteralPath $runtimeZip) { throw "Runtime artifact already exists: $runtimeZip" }
  Compress-Archive -Path (Join-Path $runtimeStage '*') -DestinationPath $runtimeZip -CompressionLevel Optimal
}

$artifactFiles = @(Get-ChildItem -LiteralPath $artifactRoot -File | Sort-Object Name | ForEach-Object {
  [ordered]@{ name=$_.Name; bytes=$_.Length; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
})
[ordered]@{
  schema='TASK047_ARTIFACT_SET_V1'; module='bai-voice-capture'; version=$version;
  runtime_included=(!$SourceOnly); artifacts=$artifactFiles
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $artifactRoot 'package-manifest.json') -Encoding UTF8
Write-Output "PACKAGE_PASS source=$sourceZip runtime=$(!$SourceOnly)"
