[CmdletBinding()]
param(
  [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
  [string]$EvidenceRoot = 'C:\home\baisound\evidence\bai-video-production',
  [string]$RunId = '',
  [string]$PythonExe = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-FullPath([string]$Path) {
  return [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
}

function Assert-NotDriveRootChild([string]$Path, [string]$Label) {
  $full = Get-FullPath $Path
  $drive = [System.IO.Path]::GetPathRoot($full).TrimEnd('\', '/')
  $parent = [System.IO.Path]::GetDirectoryName($full).TrimEnd('\', '/')
  if ($full -eq $drive -or $parent -eq $drive) {
    throw "$Label must not be a drive root or its direct child: $full"
  }
  return $full
}

function Assert-Descendant([string]$Path, [string]$Root, [string]$Label) {
  $full = Get-FullPath $Path
  $rootFull = Get-FullPath $Root
  $prefix = $rootFull + [System.IO.Path]::DirectorySeparatorChar
  if (-not $full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "$Label must stay inside $rootFull`: $full"
  }
  return $full
}

function Wait-NativeWindow([System.Diagnostics.Process]$Process, [string]$ExpectedTitle) {
  $deadline = [DateTime]::UtcNow.AddSeconds(90)
  do {
    Start-Sleep -Milliseconds 300
    $Process.Refresh()
    if ($Process.HasExited) {
      throw "$ExpectedTitle exited before exposing a native window (exit $($Process.ExitCode))."
    }
  } while ($Process.MainWindowHandle -eq [IntPtr]::Zero -and [DateTime]::UtcNow -lt $deadline)
  if ($Process.MainWindowHandle -eq [IntPtr]::Zero) {
    throw "$ExpectedTitle did not expose a native window within 90 seconds."
  }
  if (-not $Process.MainWindowTitle.Contains($ExpectedTitle)) {
    throw "Unexpected native window title: $($Process.MainWindowTitle)"
  }
  return $Process.MainWindowHandle
}

function Test-AutomationNameContains([IntPtr]$Handle, [string]$ExpectedText) {
  $root = [System.Windows.Automation.AutomationElement]::FromHandle($Handle)
  $elements = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition
  )
  foreach ($element in $elements) {
    if ($element.Current.Name -and $element.Current.Name.Contains($ExpectedText)) { return $true }
  }
  return $false
}

function Close-OwnedProcess([System.Diagnostics.Process]$Process, [string]$Label) {
  if ($Process.HasExited) { return }
  [void]$Process.CloseMainWindow()
  if (-not $Process.WaitForExit(15000)) {
    Stop-Process -Id $Process.Id -Force
    $Process.WaitForExit(10000)
    throw "$Label did not close normally; the exact operation-owned process was terminated."
  }
}

function Start-Utility([string]$Executable, [string[]]$Arguments, [string]$Title) {
  $quoted = @($Arguments | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' })
  $process = Start-Process -FilePath $Executable -ArgumentList ($quoted -join ' ') -WorkingDirectory (Split-Path -Parent $Executable) -PassThru
  $handle = Wait-NativeWindow $process $Title
  return [ordered]@{ process = $process; handle = $handle }
}

if ($env:OS -ne 'Windows_NT') { throw 'TASK-049 Consumer Gate must run on Windows.' }
if (-not $RunId) { $RunId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8) }
if ($RunId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$') { throw "RunId is invalid: $RunId" }

$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$canonicalEvidenceRoot = Get-FullPath 'C:\home\baisound\evidence\bai-video-production'
$requestedEvidenceRoot = Get-FullPath $EvidenceRoot
if ($requestedEvidenceRoot -ne $canonicalEvidenceRoot) {
  throw "EvidenceRoot must be the canonical BAI VIDEO PRODUCTION Evidence root: $canonicalEvidenceRoot"
}
$evidenceRun = Assert-NotDriveRootChild (Join-Path $requestedEvidenceRoot "TASK-049\windows-consumer-gate\$RunId") 'Evidence run root'
$evidenceRun = Assert-Descendant $evidenceRun $requestedEvidenceRoot 'Evidence run root'

$tempRoot = Get-FullPath $env:TEMP
$runtimeRun = Assert-NotDriveRootChild (Join-Path $tempRoot "bai-video-production\TASK-049\windows-consumer-gate\$RunId") 'Runtime run root'
$runtimeRun = Assert-Descendant $runtimeRun $tempRoot 'Runtime run root'
$worktreeBuildRun = Assert-NotDriveRootChild (Join-Path $repo "builds\task049-consumer-gate\$RunId") 'Worktree build run root'
$worktreeBuildRun = Assert-Descendant $worktreeBuildRun $repo 'Worktree build run root'
if (Test-Path -LiteralPath $evidenceRun) { throw "Evidence run root already exists: $evidenceRun" }
if (Test-Path -LiteralPath $runtimeRun) { throw "Runtime run root already exists: $runtimeRun" }
if (Test-Path -LiteralPath $worktreeBuildRun) { throw "Worktree build run root already exists: $worktreeBuildRun" }

if (-not $PythonExe) {
  if ($env:BVP_BUILD_PYTHON) { $PythonExe = $env:BVP_BUILD_PYTHON }
  else {
    $candidate = Join-Path $repo '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $PythonExe = $candidate }
    else { throw 'Set -PythonExe or BVP_BUILD_PYTHON to an existing Windows Python 3.12 build environment.' }
  }
}
if (-not [System.IO.Path]::IsPathRooted($PythonExe) -or -not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
  throw "PythonExe must be an existing absolute file: $PythonExe"
}
$python = (Resolve-Path -LiteralPath $PythonExe).Path

$branch = (& git -C $repo branch --show-current).Trim()
$head = (& git -C $repo rev-parse HEAD).Trim()
$baseMain = (& git -C $repo rev-parse origin/main).Trim()
$dirty = @(& git -C $repo status --porcelain=v1 --untracked-files=all)
if (-not $branch) { throw 'Consumer Gate requires a named task branch.' }
if ($dirty.Count -gt 0) { throw 'Consumer Gate requires a clean source worktree.' }
& $python -c 'import PyInstaller, webview, faster_whisper; assert PyInstaller.__version__ == "6.22.2"'
if ($LASTEXITCODE -ne 0) { throw 'Pinned Windows packaging dependencies are unavailable.' }

New-Item -ItemType Directory -Path $evidenceRun | Out-Null
New-Item -ItemType Directory -Path $runtimeRun | Out-Null
$transcript = Join-Path $evidenceRun 'native-run.log'
$transcriptStarted = $false
$oldBuildPython = $env:BVP_BUILD_PYTHON
$oldTrainingRoot = $env:BVP_TASK049_TRAINING_BUILD_ROOT
$oldTriviaRoot = $env:BVP_TASK049_TRIVIA_BUILD_ROOT
$oldSettingsRoot = $env:BVP_DBD_TRAINING_SETTINGS_ROOT
$oldPythonPath = $env:PYTHONPATH
$triviaRuns = @()
$trainingRuns = @()
try {
  Start-Transcript -LiteralPath $transcript | Out-Null
  $transcriptStarted = $true
  Write-Host "[INFO] TASK-049 Windows Consumer Gate: $RunId"
  Write-Host "[INFO] Source: $head ($branch); origin/main: $baseMain"
  Write-Host "[INFO] Runtime root: $runtimeRun"
  Write-Host "[INFO] Worktree build root: $worktreeBuildRun"
  Write-Host "[INFO] Evidence root: $evidenceRun"

  $env:BVP_BUILD_PYTHON = $python
  # The existing TASK-048 controller intentionally admits its output only
  # beneath the exact repository root. Keep only that main-package build in a
  # unique ignored worktree run directory; utility builds and fixtures remain
  # beneath the system temporary run root.
  $mainBuildRoot = Join-Path $worktreeBuildRun 'main-build'
  $mainEvidence = Join-Path $evidenceRun 'main-bvp'
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repo 'tools\windows\run-task049-r9b2-packaged-smoke.ps1') -RepositoryRoot $repo -EvidenceDirectory $mainEvidence -BuildRoot $mainBuildRoot -PythonExe $python
  if ($LASTEXITCODE -ne 0) { throw "Main BVP packaged smoke failed with exit code $LASTEXITCODE" }
  $mainExe = Join-Path $mainBuildRoot 'BAI Video Production\BAI Video Production.exe'
  if (-not (Test-Path -LiteralPath $mainExe -PathType Leaf)) { throw "Expected packaged EXE is missing: $mainExe" }

  $trainingBuildRoot = Join-Path $runtimeRun 'training-build'
  $env:BVP_TASK049_TRAINING_BUILD_ROOT = $trainingBuildRoot
  & cmd.exe /d /c (Join-Path $repo 'build-dbd-training-studio-exe.bat')
  if ($LASTEXITCODE -ne 0) { throw "Training Studio build failed with exit code $LASTEXITCODE" }

  $triviaBuildRoot = Join-Path $runtimeRun 'trivia-build'
  $env:BVP_TASK049_TRIVIA_BUILD_ROOT = $triviaBuildRoot
  & cmd.exe /d /c (Join-Path $repo 'build-dbd-trivia-editor-exe.bat')
  if ($LASTEXITCODE -ne 0) { throw "Trivia Editor build failed with exit code $LASTEXITCODE" }

  $fixtureRoot = Join-Path $runtimeRun 'rights-safe-fixture'
  $env:PYTHONPATH = Join-Path $repo 'src'
  & $python (Join-Path $repo 'tools\windows\create-task049-consumer-gate-fixture.py') --root $fixtureRoot | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Consumer Gate fixture creation failed with exit code $LASTEXITCODE" }
  $fixture = Get-Content -LiteralPath (Join-Path $fixtureRoot 'task049-consumer-gate-fixture.json') -Raw -Encoding UTF8 | ConvertFrom-Json

  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  $triviaExe = Join-Path $triviaBuildRoot 'BAI DbD Trivia Editor\BAI DbD Trivia Editor.exe'
  $trainingExe = Join-Path $trainingBuildRoot 'BAI DbD Training Studio\BAI DbD Training Studio.exe'
  foreach ($exe in @($triviaExe, $trainingExe)) {
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Expected packaged EXE is missing: $exe" }
  }

  foreach ($attempt in 1..2) {
    $triviaRun = Start-Utility $triviaExe @('--database', [string]$fixture.trivia_database) 'BAI DbD Trivia Editor'
    $triviaRuns += $triviaRun
    Start-Sleep -Milliseconds 800
    if (-not (Test-AutomationNameContains $triviaRun.handle ([string]$fixture.trivia_title))) {
      throw "Trivia Editor attempt $attempt did not expose the synthetic CANDIDATE fixture through UI Automation."
    }
    Close-OwnedProcess $triviaRun.process "Trivia Editor attempt $attempt"
  }

  $env:BVP_DBD_TRAINING_SETTINGS_ROOT = [string]$fixture.training_settings_root
  foreach ($attempt in 1..2) {
    $trainingRun = Start-Utility $trainingExe @('--workspace', [string]$fixture.training_workspace) 'BAI DbD Training Studio'
    $trainingRuns += $trainingRun
    Start-Sleep -Milliseconds 1000
    Close-OwnedProcess $trainingRun.process "Training Studio attempt $attempt"
  }
  $templateRoot = Join-Path ([string]$fixture.training_workspace) 'templates'
  $expectedTemplates = @('visual-training-template.csv', 'upper-right-ocr-vocabulary-template.csv', 'commentary-trivia-template.csv', 'video-training-ranges-template.csv')
  foreach ($name in $expectedTemplates) {
    if (-not (Test-Path -LiteralPath (Join-Path $templateRoot $name) -PathType Leaf)) {
      throw "Training Studio packaged startup did not materialize/read back template: $name"
    }
  }

  $mainReceipt = Get-Content -LiteralPath (Join-Path $mainEvidence 'task049-r9b2-packaged-smoke.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($mainReceipt.result -ne 'PASS') { throw 'Main BVP sub-receipt read-back failed.' }
  $receipt = [ordered]@{
    receipt_version = '1.0.0'
    task = 'TASK-049'
    atomic_unit = 'WINDOWS_CONSUMER_GATE'
    run_id = $RunId
    result = 'PASS'
    source = [ordered]@{ branch = $branch; head = $head; origin_main = $baseMain; dirty = $false }
    paths = [ordered]@{ worktree = $repo; worktree_build_root = $worktreeBuildRun; runtime_root = $runtimeRun; evidence_root = $evidenceRun }
    packages = [ordered]@{
      main_bvp = [ordered]@{ result = 'PASS'; exe_sha256 = $mainReceipt.exe_sha256; restart_readback = 'PASS' }
      trivia_editor = [ordered]@{ result = 'PASS'; exe_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $triviaExe).Hash.ToLowerInvariant(); launch_count = 2; candidate_readback = 'PASS' }
      training_studio = [ordered]@{ result = 'PASS'; exe_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $trainingExe).Hash.ToLowerInvariant(); launch_count = 2; workspace_template_readback = 'PASS' }
    }
    fixture = [ordered]@{
      rights_basis = $fixture.rights_basis
      real_media_used = $false
      private_media_used = $false
      human_gold_labels_created = $false
      trivia_status = $fixture.trivia_status
    }
    calibration = [ordered]@{
      preparation_result = 'PASS'
      real_media_roi_calibration = 'NOT_CONFIRMED'
      human_gold_kpi = 'NOT_CONFIRMED'
      reason = 'Real rights-confirmed DbD media and new Human labels were not supplied.'
    }
    prohibited_effects = [ordered]@{
      provider_execution_started = $false
      model_or_runtime_acquired = $false
      production_timeline_mutated = $false
      resolve_write_performed = $false
      release_or_deploy_performed = $false
    }
    intentional_residual_artifacts = @($worktreeBuildRun, $runtimeRun, $evidenceRun)
  }
  $receiptPath = Join-Path $evidenceRun 'task049-windows-consumer-gate.json'
  $receipt | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
  $readback = Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($readback.run_id -ne $RunId -or $readback.result -ne 'PASS') { throw 'Final receipt read-back failed.' }
  $receiptHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $receiptPath).Hash.ToLowerInvariant()
  Set-Content -LiteralPath (Join-Path $evidenceRun 'task049-windows-consumer-gate.sha256') -Value "$receiptHash  task049-windows-consumer-gate.json" -Encoding ASCII
  Write-Host '[PASS] TASK-049 Windows Consumer Gate passed.'
  Write-Host "[PASS] Receipt: $receiptPath"
} finally {
  foreach ($run in @($triviaRuns + $trainingRuns)) {
    if ($run -and $run.process -and -not $run.process.HasExited) {
      try { Stop-Process -Id $run.process.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
  }
  $env:BVP_BUILD_PYTHON = $oldBuildPython
  $env:BVP_TASK049_TRAINING_BUILD_ROOT = $oldTrainingRoot
  $env:BVP_TASK049_TRIVIA_BUILD_ROOT = $oldTriviaRoot
  $env:BVP_DBD_TRAINING_SETTINGS_ROOT = $oldSettingsRoot
  $env:PYTHONPATH = $oldPythonPath
  if ($transcriptStarted) { try { Stop-Transcript | Out-Null } catch {} }
}
