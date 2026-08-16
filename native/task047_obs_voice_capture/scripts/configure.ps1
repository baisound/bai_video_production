param(
  [string]$CMakeExecutable = 'cmake',
  [string]$Generator = 'Visual Studio 18 2026',
  [string]$Toolset = 'v145',
  [string]$WindowsSdk = '10.0.26100.0'
)

$ErrorActionPreference = 'Stop'
$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$obsSource = (Resolve-Path (Join-Path $pluginRoot '..\..')).Path
$buildDir = Join-Path $obsSource 'build_x64'
$expectedPlugin = [IO.Path]::GetFullPath((Join-Path $obsSource 'plugins\bai-voice-capture'))
if ([IO.Path]::GetFullPath($pluginRoot) -ne $expectedPlugin) { throw 'Plugin path containment mismatch' }

$cmakeVersion = (& $CMakeExecutable --version | Select-Object -First 1)
if ($LASTEXITCODE -ne 0) { throw 'CMake version probe failed' }
$env:CMAKE_GENERATOR = $Generator
$env:CMAKE_GENERATOR_TOOLSET = $Toolset
$env:CMAKE_GENERATOR_PLATFORM = "x64,version=$WindowsSdk"
$env:BAI_TASK047_OFFLINE = '1'

& $CMakeExecutable -S $obsSource -B $buildDir --fresh `
  -G $Generator -A "x64,version=$WindowsSdk" -T $Toolset `
  -DOBS_VERSION_OVERRIDE:STRING=32.2.1 `
  -DENABLE_FRONTEND:BOOL=OFF `
  -DENABLE_PLUGINS:BOOL=OFF `
  -DENABLE_SCRIPTING:BOOL=OFF `
  -DENABLE_BROWSER:BOOL=OFF `
  -DENABLE_WEBSOCKET:BOOL=OFF `
  -DCMAKE_COMPILE_WARNING_AS_ERROR:BOOL=ON `
  "-DBAI_VOICE_CAPTURE_PLUGIN_DIR:PATH=$pluginRoot" `
  "-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES:FILEPATH=$pluginRoot\cmake\verify-package.cmake"
if ($LASTEXITCODE -ne 0) { throw "Configure failed with exit code $LASTEXITCODE" }

$cache = Join-Path $buildDir 'CMakeCache.txt'
if (!(Test-Path -LiteralPath $cache)) { throw 'CMake cache was not generated' }
$cacheText = Get-Content -LiteralPath $cache -Raw
foreach ($required in @(
  'BAI_VOICE_CAPTURE_REGISTRATION_STATE:INTERNAL=REGISTERED_EXACT1',
  'OBS_VERSION_OVERRIDE:STRING=32.2.1',
  'ENABLE_PLUGINS:BOOL=OFF'
)) {
  if (!$cacheText.Contains($required)) { throw "Configure binding missing: $required" }
}
Write-Output "CONFIGURE_PASS cmake=$cmakeVersion generator=$Generator toolset=$Toolset sdk=$WindowsSdk"
