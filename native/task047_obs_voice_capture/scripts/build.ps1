param(
  [string]$CMakeExecutable = 'cmake',
  [ValidateSet('Debug','Release','RelWithDebInfo','MinSizeRel')]
  [string]$Configuration = 'Release'
)

$ErrorActionPreference = 'Stop'
$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$obsSource = (Resolve-Path (Join-Path $pluginRoot '..\..')).Path
$buildDir = Join-Path $obsSource 'build_x64'
if (!(Test-Path -LiteralPath (Join-Path $buildDir 'CMakeCache.txt'))) { throw 'Configure barrier is not open' }

& $CMakeExecutable --build $buildDir --config $Configuration --target bai-voice-capture bai-voice-capture-core-test --parallel
if ($LASTEXITCODE -ne 0) { throw "Build failed with exit code $LASTEXITCODE" }

$dlls = @(Get-ChildItem -LiteralPath $buildDir -Recurse -File -Filter 'bai-voice-capture.dll')
$tests = @(Get-ChildItem -LiteralPath $buildDir -Recurse -File -Filter 'bai-voice-capture-core-test.exe')
if ($dlls.Count -ne 1) { throw "Expected exactly one real plugin DLL; found $($dlls.Count)" }
if ($tests.Count -ne 1) { throw "Expected exactly one core test executable; found $($tests.Count)" }
Write-Output "BUILD_PASS dll=$($dlls[0].FullName) test=$($tests[0].FullName)"
