param(
  [string]$Compiler = 'C:\Program Files\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe',
  [string]$BuildRoot,
  [string]$OutputDirectory,
  [string]$MeterWorkerBundle,
  [string]$RuntimeRoot,
  [string]$OperationId,
  [switch]$ReadinessBuild,
  [switch]$PrepareShellBuild
)
$ErrorActionPreference = 'Stop'

# Replaces the legacy `Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop` contract;
# the unqualified import is intentionally never executed because PSModulePath is inherited.
function Import-ShellOwnedFileHashCommand([string]$ShellHome) {
  if ([string]::IsNullOrWhiteSpace($ShellHome) -or
      ![IO.Path]::IsPathRooted($ShellHome) -or $ShellHome.StartsWith('\\')) {
    throw 'Trusted PowerShell home invalid'
  }
  $resolvedShellHome = [IO.Path]::GetFullPath($ShellHome).TrimEnd('\')
  if (!(Test-Path -LiteralPath $resolvedShellHome -PathType Container)) {
    throw 'Trusted PowerShell home missing'
  }
  $moduleRoot = [IO.Path]::GetFullPath(
    (Join-Path $resolvedShellHome 'Modules\Microsoft.PowerShell.Utility')
  ).TrimEnd('\')
  $manifestPath = [IO.Path]::GetFullPath(
    (Join-Path $moduleRoot 'Microsoft.PowerShell.Utility.psd1')
  )
  if (!(Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw 'Trusted Microsoft.PowerShell.Utility manifest missing'
  }
  foreach ($trustedPath in @($resolvedShellHome, (Join-Path $resolvedShellHome 'Modules'), $moduleRoot, $manifestPath)) {
    $trustedItem = Get-Item -Force -LiteralPath $trustedPath
    if ($trustedItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
      throw 'Trusted Microsoft.PowerShell.Utility path invalid'
    }
  }
  $imported = @(Import-Module -Name $manifestPath -Force -PassThru -ErrorAction Stop)
  $matchingImports = @($imported | Where-Object {
    $_.Name -ceq 'Microsoft.PowerShell.Utility' -and
    [IO.Path]::GetFullPath($_.Path) -eq $manifestPath
  })
  if ($matchingImports.Count -ne 1) {
    throw 'Trusted Microsoft.PowerShell.Utility import identity mismatch'
  }
  $commands = @(Get-Command -Name 'Microsoft.PowerShell.Utility\Get-FileHash' -All -ErrorAction Stop)
  $trustedCommands = @($commands | Where-Object {
    $_.Name -ceq 'Get-FileHash' -and $_.ModuleName -ceq 'Microsoft.PowerShell.Utility' -and
    $null -ne $_.Module -and ![string]::IsNullOrWhiteSpace($_.Module.Path) -and
    [IO.Path]::GetFullPath($_.Module.Path).StartsWith(
      $moduleRoot + '\', [StringComparison]::OrdinalIgnoreCase
    )
  })
  if ($commands.Count -ne 1 -or $trustedCommands.Count -ne 1) {
    throw 'Trusted Microsoft.PowerShell.Utility Get-FileHash command unavailable'
  }
  $commandPath = [IO.Path]::GetFullPath($trustedCommands[0].Module.Path)
  if (!(Test-Path -LiteralPath $commandPath -PathType Leaf)) {
    throw 'Trusted Microsoft.PowerShell.Utility command path invalid'
  }
  $commandPathCursor = $commandPath
  while ($true) {
    $commandPathItem = Get-Item -Force -LiteralPath $commandPathCursor
    if ($commandPathItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
      throw 'Trusted Microsoft.PowerShell.Utility command path invalid'
    }
    $commandPathIdentity = [IO.Path]::GetFullPath($commandPathItem.FullName).TrimEnd('\')
    if (!$commandPathIdentity.Equals($commandPathCursor, [StringComparison]::OrdinalIgnoreCase)) {
      throw 'Trusted Microsoft.PowerShell.Utility command path identity mismatch'
    }
    if ($commandPathCursor.Equals($moduleRoot, [StringComparison]::OrdinalIgnoreCase)) { break }
    $commandPathParent = [IO.Path]::GetDirectoryName($commandPathCursor)
    if ([string]::IsNullOrWhiteSpace($commandPathParent) -or
        (!$commandPathParent.Equals($moduleRoot, [StringComparison]::OrdinalIgnoreCase) -and
         !$commandPathParent.StartsWith($moduleRoot + '\', [StringComparison]::OrdinalIgnoreCase))) {
      throw 'Trusted Microsoft.PowerShell.Utility command escaped module root'
    }
    $commandPathCursor = $commandPathParent.TrimEnd('\')
  }
  return $trustedCommands[0]
}
function Get-TrustedSha256([string]$LiteralPath) {
  if ($null -eq $script:trustedFileHashCommand) { throw 'Trusted SHA-256 command unavailable' }
  $hashResult = & $script:trustedFileHashCommand -LiteralPath $LiteralPath -Algorithm SHA256 -ErrorAction Stop
  if ($null -eq $hashResult -or [string]::IsNullOrWhiteSpace($hashResult.Hash) -or
      $hashResult.Hash -notmatch '^[a-fA-F0-9]{64}$') {
    throw 'Trusted SHA-256 calculation failed'
  }
  return $hashResult.Hash.ToLowerInvariant()
}
$script:trustedFileHashCommand = Import-ShellOwnedFileHashCommand -ShellHome $PSHOME
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
$taskIdentity = 'TASK-048'
$operationPrefix = 'task048-build-'
if ($ReadinessBuild) {
  $taskIdentity = 'TASK-047'
  $operationPrefix = 'task047-readiness-build-'
}
if (!$OperationId) { $OperationId = $operationPrefix + [Guid]::NewGuid().ToString('N') }
if ($OperationId -notmatch ('^' + [regex]::Escape($operationPrefix) + '[a-f0-9]{32}$')) { throw 'Operation identity invalid' }
if (!$BuildRoot) {
  if ($PrepareShellBuild) { $BuildRoot = Join-Path $repositoryRoot 'builds' }
  else {
    $family = 'task048-controller'
    if ($ReadinessBuild) { $family = 'task047-readiness-controller' }
    $BuildRoot = Join-Path $repositoryRoot ('builds\' + $family + '\' + $OperationId)
  }
}
$resolvedBuildRoot = Assert-ContainedPath $BuildRoot $repositoryRoot
if (!$RuntimeRoot) { $RuntimeRoot = Join-Path ([IO.Path]::GetTempPath()) $OperationId }
$resolvedRuntimeRoot = Assert-ContainedPath $RuntimeRoot ([IO.Path]::GetTempPath())
$operationReceiptName = 'task048-build-operation.json'
if ($ReadinessBuild) { $operationReceiptName = 'task047-readiness-build-operation.json' }
$operationReceipt = Join-Path $resolvedBuildRoot $operationReceiptName

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
    task = $taskIdentity; operation = $OperationId; repository = $repositoryRoot
    build_root = $resolvedBuildRoot; runtime_root = $resolvedRuntimeRoot
    residuals = 'Retain build, temporary output and receipts; no implicit cleanup'
  }
} else {
  $record = Get-Content -Raw -LiteralPath $operationReceipt | ConvertFrom-Json
}
if ($record.task -ne $taskIdentity -or $record.operation -ne $OperationId -or
    $record.repository -ne $repositoryRoot -or $record.build_root -ne $resolvedBuildRoot -or
    $record.runtime_root -ne $resolvedRuntimeRoot) { throw 'Build operation receipt mismatch' }
$env:TMP = $resolvedRuntimeRoot
$env:TEMP = $resolvedRuntimeRoot
if ($ReadinessBuild) {
  Write-Output "TASK047_READINESS_OUTPUT_ROOT=$resolvedBuildRoot"
  Write-Output "TASK047_READINESS_RUNTIME_ROOT=$resolvedRuntimeRoot"
} else {
  Write-Output "TASK048_OUTPUT_ROOT=$resolvedBuildRoot"
  Write-Output "TASK048_RUNTIME_ROOT=$resolvedRuntimeRoot"
}
if ($PrepareShellBuild) { exit 0 }

if (!(Test-Path -LiteralPath $Compiler -PathType Leaf)) { throw 'Pinned C# compiler not found' }
if (!$OutputDirectory) { $OutputDirectory = Join-Path $resolvedBuildRoot 'meter-controller' }
$controllerOutputRoot = Assert-ContainedPath $OutputDirectory $resolvedBuildRoot
if (Test-Path -LiteralPath $controllerOutputRoot) { throw 'Existing Controller output denied' }
$source = Join-Path $pluginRoot 'controller\BaiVoiceCaptureController.cs'
$bridgeSource = Join-Path $pluginRoot 'controller\BaiMeterRuntimeBridge.cs'
$operationSource = Join-Path $pluginRoot 'controller\BaiCaptureOperation.cs'
$readinessSource = Join-Path $pluginRoot 'controller\BaiReadinessMonitor.cs'
$receiptSource = Join-Path $pluginRoot 'controller\BaiReadinessReceipt.cs'
$selfTestSource = Join-Path $pluginRoot 'controller\BaiReadinessMonitorSelfTest.cs'
$schemaSource = Join-Path $repositoryRoot 'src\ai_video_production\schema_resources\task047-readiness-monitor-receipt-v1.schema.json'
$readinessSources = @($readinessSource, $receiptSource, $selfTestSource)
if (!(Test-Path -LiteralPath $source) -or !(Test-Path -LiteralPath $bridgeSource) -or
    !(Test-Path -LiteralPath $operationSource -PathType Leaf)) { throw 'Controller sources missing' }
$schemaSha = $null
if ($ReadinessBuild) {
  if (@($readinessSources | Where-Object { !(Test-Path -LiteralPath $_ -PathType Leaf) }).Count -ne 0 -or
      !(Test-Path -LiteralPath $schemaSource -PathType Leaf)) { throw 'Readiness sources missing' }
  $schemaSha = Get-TrustedSha256 -LiteralPath $schemaSource
  if ($schemaSha -ne '61e87d762db8d0fbc28a95dc4c3c7642b83c19bb1a6d197e2fdd1ebc6ff18472') {
    throw 'TASK-047 readiness schema identity mismatch'
  }
}
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
        $workerFiles += [pscustomobject]@{ path = $relative; sha256 = Get-TrustedSha256 -LiteralPath $entry.FullName }
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
  '/reference:System.Drawing.dll', '/reference:System.Windows.Forms.dll', $source, $bridgeSource,
  $operationSource)
if ($ReadinessBuild) {
  $arguments += $readinessSources
  $arguments += '/define:BVP_TASK047_READINESS'
  $arguments += '/resource:' + $schemaSource + ',BVP.Task047.ReadinessMonitorReceiptV1.Schema'
}
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
$selfTestModes = @('--self-test', '--meter-self-test', '--bvp-meter-protocol-self-test',
    '--bvp-meter-scalar-self-test')
if ($ReadinessBuild) { $selfTestModes += '--readiness-self-test' }
foreach ($mode in $selfTestModes) {
  $test = Start-Process -FilePath $output -ArgumentList $mode -WindowStyle Hidden -Wait -PassThru
  if ($test.ExitCode -ne 0) { throw "Controller self-test failed: $mode code=$($test.ExitCode)" }
}
$closureFields = @{
  task = $taskIdentity; operation = $OperationId
  controller_sha256 = Get-TrustedSha256 -LiteralPath $output
  worker_files = $workerFiles; result = 'PASS'; build_root = $resolvedBuildRoot; runtime_root = $resolvedRuntimeRoot
}
if ($ReadinessBuild) { $closureFields.readiness_schema_sha256 = $schemaSha }
$closureReceipt = Write-NewJson (Join-Path $controllerOutputRoot 'meter-build-identity.json') $closureFields
if ($closureReceipt.controller_sha256 -ne (Get-TrustedSha256 -LiteralPath $output)) { throw 'Controller receipt readback failed' }
Write-Output "CONTROLLER_BUILD_TEST_PASS exe=$output"
