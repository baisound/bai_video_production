param(
  [string]$Compiler = 'C:\Program Files\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe',
  [string]$BuildRoot,
  [string]$OutputDirectory,
  [string]$MeterWorkerBundle,
  [string]$RuntimeRoot,
  [string]$OperationId,
  [switch]$PrepareShellBuild
)
$ErrorActionPreference = 'Stop'
$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$repositoryRoot = (Resolve-Path (Join-Path $pluginRoot '..\..')).Path

function Assert-ContainedPath([string]$Candidate, [string]$Allowed) {
  if (![IO.Path]::IsPathRooted($Candidate) -or $Candidate.StartsWith('\\')) { throw 'Absolute local path required' }
  $resolved = [IO.Path]::GetFullPath($Candidate).TrimEnd('\')
  $boundary = [IO.Path]::GetFullPath($Allowed).TrimEnd('\')
  $drive = [IO.Path]::GetPathRoot($resolved)
  if ($resolved -eq $drive.TrimEnd('\') -or [IO.Path]::GetDirectoryName($resolved) -eq $drive) { throw 'Drive-root placement denied' }
  if (!$resolved.StartsWith($boundary + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Output escaped authorized root' }
  $cursor = $resolved
  while ($cursor) {
    if (Test-Path -LiteralPath $cursor) {
      $item = Get-Item -Force -LiteralPath $cursor
      if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse ancestor denied' }
    }
    $next = [IO.Path]::GetDirectoryName($cursor)
    if ($next -eq $cursor) { break }
    $cursor = $next
  }
  return $resolved
}
function Write-NewJson([string]$Path, $Value) {
  if (Test-Path -LiteralPath $Path) { throw 'Existing receipt denied' }
  $Value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
  return (Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json)
}
if (!$OperationId) { $OperationId = 'task048-build-' + [Guid]::NewGuid().ToString('N') }
if ($OperationId -notmatch '^task048-build-[a-f0-9]{32}$') { throw 'Operation identity invalid' }
if (!$BuildRoot) {
  if ($PrepareShellBuild) { $BuildRoot = Join-Path $repositoryRoot 'builds' }
  else { $BuildRoot = Join-Path $repositoryRoot ('builds\task048-controller\' + $OperationId) }
}
$resolvedBuildRoot = Assert-ContainedPath $BuildRoot $repositoryRoot
if (!$RuntimeRoot) { $RuntimeRoot = Join-Path ([IO.Path]::GetTempPath()) $OperationId }
$resolvedRuntimeRoot = Assert-ContainedPath $RuntimeRoot ([IO.Path]::GetTempPath())
$operationReceipt = Join-Path $resolvedBuildRoot 'task048-build-operation.json'

if ($PrepareShellBuild -or !(Test-Path -LiteralPath $operationReceipt)) {
  # The default tracked builds/.gitkeep is the sole permitted pre-existing item.
  if (Test-Path -LiteralPath $resolvedBuildRoot) {
    $items = @(Get-ChildItem -Force -LiteralPath $resolvedBuildRoot)
    if ($resolvedBuildRoot -ne (Join-Path $repositoryRoot 'builds') -or
        @($items | Where-Object { $_.Name -ne '.gitkeep' -or $_.PSIsContainer }).Count -gt 0) {
      throw 'Foreign or previously used build destination denied'
    }
  }
  if (Test-Path -LiteralPath $resolvedRuntimeRoot) { throw 'Existing runtime destination denied' }
  New-Item -ItemType Directory -Path $resolvedBuildRoot -Force | Out-Null
  New-Item -ItemType Directory -Path $resolvedRuntimeRoot | Out-Null
  $record = Write-NewJson $operationReceipt @{
    task = 'TASK-048'; operation = $OperationId; repository = $repositoryRoot
    build_root = $resolvedBuildRoot; runtime_root = $resolvedRuntimeRoot
    residuals = 'Retain build, temporary output and receipts; no implicit cleanup'
  }
} else {
  $record = Get-Content -Raw -LiteralPath $operationReceipt | ConvertFrom-Json
}
if ($record.task -ne 'TASK-048' -or $record.operation -ne $OperationId -or
    $record.repository -ne $repositoryRoot -or $record.build_root -ne $resolvedBuildRoot -or
    $record.runtime_root -ne $resolvedRuntimeRoot) { throw 'Build operation receipt mismatch' }
$env:TMP = $resolvedRuntimeRoot
$env:TEMP = $resolvedRuntimeRoot
Write-Output "TASK048_OUTPUT_ROOT=$resolvedBuildRoot"
Write-Output "TASK048_RUNTIME_ROOT=$resolvedRuntimeRoot"
if ($PrepareShellBuild) { exit 0 }

if (!(Test-Path -LiteralPath $Compiler -PathType Leaf)) { throw 'Pinned C# compiler not found' }
if (!$OutputDirectory) { $OutputDirectory = Join-Path $resolvedBuildRoot 'meter-controller' }
$controllerOutputRoot = Assert-ContainedPath $OutputDirectory $resolvedBuildRoot
if (Test-Path -LiteralPath $controllerOutputRoot) { throw 'Existing Controller output denied' }
$source = Join-Path $pluginRoot 'controller\BaiVoiceCaptureController.cs'
$bridgeSource = Join-Path $pluginRoot 'controller\BaiMeterRuntimeBridge.cs'
if (!(Test-Path -LiteralPath $source) -or !(Test-Path -LiteralPath $bridgeSource)) { throw 'Controller sources missing' }
$workerFiles = @()
if ($MeterWorkerBundle) {
  $workerRoot = Assert-ContainedPath $MeterWorkerBundle $resolvedBuildRoot
  if (!(Test-Path -LiteralPath $workerRoot -PathType Container)) { throw 'Worker bundle missing' }
  $directories = New-Object 'System.Collections.Generic.Stack[string]'
  $directories.Push($workerRoot)
  while ($directories.Count -gt 0) {
    foreach ($entry in Get-ChildItem -Force -LiteralPath $directories.Pop()) {
      if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Worker reparse entry denied' }
      if ($entry.PSIsContainer) { $directories.Push($entry.FullName) }
      else {
        # Empty regular metadata (for example dist-info/REQUESTED) is part of
        # the exact closure and must be hashed, never removed or synthesized.
        if ($entry.Length -lt 0 -or $entry.Length -gt 536870912) { throw 'Worker closure file size limit exceeded' }
        if ($workerFiles.Count -ge 4095) { throw 'Worker closure file count limit exceeded' }
        $relative = 'worker\' + $entry.FullName.Substring($workerRoot.Length + 1)
        if ($relative -notmatch '^[a-zA-Z0-9 _.\-\\]+$') { throw 'Worker path unsupported' }
        if ($relative -ceq 'worker\BAI Meter Worker.exe' -and $entry.Length -eq 0) { throw 'Worker executable empty' }
        $workerFiles += [pscustomobject]@{ path = $relative; sha256 = (Get-FileHash -LiteralPath $entry.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
      }
    }
  }
  $workerFiles = @($workerFiles | Sort-Object path)
  if ($workerFiles.Count -lt 2 -or !($workerFiles.path -ccontains 'worker\BAI Meter Worker.exe')) { throw 'Worker executable closure missing' }
}
New-Item -ItemType Directory -Path $controllerOutputRoot | Out-Null
$output = Join-Path $controllerOutputRoot 'bai-voice-capture-controller.exe'
$arguments = @('/nologo', '/warnaserror+', '/target:winexe', '/platform:x64', '/optimize+',
  "/out:$output", '/reference:System.dll', '/reference:System.Core.dll',
  '/reference:System.Drawing.dll', '/reference:System.Windows.Forms.dll', $source, $bridgeSource)
if ($MeterWorkerBundle) {
  $identitySource = Join-Path $controllerOutputRoot 'BaiMeterBuildIdentity.cs'
  $fileLiterals = @($workerFiles | ForEach-Object { '@"' + $_.path + '"' })
  $digestLiterals = @($workerFiles | ForEach-Object { '"' + $_.sha256 + '"' })
  $identityText = 'internal static class BaiMeterBuildIdentity { internal static readonly string[] Files = new string[] {' +
    ($fileLiterals -join ',') + '}; internal static readonly string[] Digests = new string[] {' +
    ($digestLiterals -join ',') + '}; }'
  Set-Content -LiteralPath $identitySource -Value $identityText -Encoding UTF8
  $arguments += @('/define:BVP_METER_PACKAGED', $identitySource)
}
& $Compiler @arguments
if ($LASTEXITCODE -ne 0) { throw "Controller build failed with exit code $LASTEXITCODE" }
foreach ($mode in @('--self-test', '--meter-self-test', '--bvp-meter-protocol-self-test', '--bvp-meter-scalar-self-test')) {
  $test = Start-Process -FilePath $output -ArgumentList $mode -WindowStyle Hidden -Wait -PassThru
  if ($test.ExitCode -ne 0) { throw "Controller self-test failed: $mode code=$($test.ExitCode)" }
}
$closureReceipt = Write-NewJson (Join-Path $controllerOutputRoot 'meter-build-identity.json') @{
  task = 'TASK-048'; operation = $OperationId
  controller_sha256 = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()
  worker_files = $workerFiles; result = 'PASS'; build_root = $resolvedBuildRoot; runtime_root = $resolvedRuntimeRoot
}
if ($closureReceipt.controller_sha256 -ne (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()) { throw 'Controller receipt readback failed' }
Write-Output "CONTROLLER_BUILD_TEST_PASS exe=$output"
