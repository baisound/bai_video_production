param(
  [string]$CMakeExecutable = 'cmake',
  [string]$CtestExecutable = 'ctest',
  [ValidateSet('Debug','Release','RelWithDebInfo','MinSizeRel')]
  [string]$Configuration = 'Release'
)

$ErrorActionPreference = 'Stop'
$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$obsSource = (Resolve-Path (Join-Path $pluginRoot '..\..')).Path
$operationRoot = (Resolve-Path (Join-Path $obsSource '..')).Path
$buildDir = Join-Path $obsSource 'build_x64\plugins\bai-voice-capture'
$artifactDir = Join-Path $operationRoot 'artifacts'
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

& $CtestExecutable --test-dir $buildDir -C $Configuration --output-on-failure -R '^bai-voice-capture-core-test$'
$testExit = $LASTEXITCODE

$forbidden = @(
  @{ Pattern = 'WinHttp|WinInet|InternetOpen|WSAStartup|socket\s*\('; Name = 'network_api' },
  @{ Pattern = 'fopen|ofstream|CreateFileW?\s*\('; Name = 'callback_file_api' },
  @{ Pattern = 'obs_source_output_audio'; Name = 'audio_mutation_api' }
)
$pluginSource = Get-Content -LiteralPath (Join-Path $pluginRoot 'src\obs_plugin.cpp') -Raw
$staticFailures = @()
foreach ($rule in $forbidden) {
  if ($pluginSource -match $rule.Pattern) { $staticFailures += $rule.Name }
}
if ($pluginSource -notmatch 'return audio;') { $staticFailures += 'original_audio_not_returned' }
if ($pluginSource -match 'blog\s*\([^\)]*SESSION_KEY') { $staticFailures += 'credential_logging' }

$receipt = [ordered]@{
  schema = 'TASK047_BUILD_TEST_RECEIPT_V1'
  operation_id = 'BVP-OP-20260816-POBS-B2-IMPLEMENT-BUILD-PACKAGE-01'
  configuration = $Configuration
  test_target = 'bai-voice-capture-core-test'
  ctest_exit = $testExit
  static_security_failures = $staticFailures
  recording = 'NOT_AUTHORIZED_NOT_PERFORMED'
  audio_device_access = 'NOT_AUTHORIZED_NOT_PERFORMED'
  network = 'DENIED_NOT_USED'
  install_load_obs_launch = 'NOT_AUTHORIZED_NOT_PERFORMED'
  generated_utc = [DateTime]::UtcNow.ToString('o')
  state = if ($testExit -eq 0 -and $staticFailures.Count -eq 0) { 'PASS' } else { 'FAIL' }
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $artifactDir 'build-test-receipt.json') -Encoding UTF8
if ($testExit -ne 0 -or $staticFailures.Count -ne 0) { throw 'Test or static security gate failed' }
Write-Output 'TEST_PASS static_security=PASS'
