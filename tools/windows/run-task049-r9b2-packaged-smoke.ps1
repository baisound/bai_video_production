param(
  [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
  [Parameter(Mandatory = $true)]
  [string]$EvidenceDirectory,
  [string]$PythonExe = ''
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'TASK-049 R9B2 packaged smoke must run on Windows.' }

$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$evidence = [System.IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Path $evidence -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
  $venvPython = Join-Path $repo '.venv\Scripts\python.exe'
  $PythonExe = if (Test-Path -LiteralPath $venvPython -PathType Leaf) { $venvPython } else { 'python' }
}

$build = Join-Path $repo 'build-windows-exe.bat'
& $build
if ($LASTEXITCODE -ne 0) { throw "Windows package build failed with exit code $LASTEXITCODE" }

$package = Join-Path $repo 'builds\BAI Video Production'
$exe = Join-Path $package 'BAI Video Production.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Packaged executable is missing: $exe" }
$exeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()

$runRoot = Join-Path $env:TEMP ('bai-task049-r9b2-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
$fixtureTool = Join-Path $repo 'tools\windows\create-task049-game-intelligence-fixture.py'
& $PythonExe $fixtureTool --root $runRoot | Out-Null
if ($LASTEXITCODE -ne 0) { throw "TASK-049 fixture creation failed with exit code $LASTEXITCODE" }
$metadataPath = Join-Path $runRoot 'task049-fixture-metadata.json'
$metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class Task049Win32 {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int command);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint message, IntPtr wParam, IntPtr lParam);
}
'@

function Find-ProcessWindow([int]$ProcessId) {
  $condition = [System.Windows.Automation.PropertyCondition]::new(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $ProcessId)
  $windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll(
    [System.Windows.Automation.TreeScope]::Children, $condition)
  foreach ($window in $windows) {
    if ($window.Current.ControlType -eq [System.Windows.Automation.ControlType]::Window) { return $window }
  }
  return $null
}

function Find-ButtonExact([System.Windows.Automation.AutomationElement]$Root, [string]$Name) {
  $condition = [System.Windows.Automation.AndCondition]::new(
    [System.Windows.Automation.PropertyCondition]::new(
      [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
      [System.Windows.Automation.ControlType]::Button),
    [System.Windows.Automation.PropertyCondition]::new(
      [System.Windows.Automation.AutomationElement]::NameProperty, $Name))
  return $Root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
}

function Find-ButtonPrefix([System.Windows.Automation.AutomationElement]$Root, [string]$Prefix) {
  $condition = [System.Windows.Automation.PropertyCondition]::new(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Button)
  $buttons = $Root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
  foreach ($button in $buttons) {
    if ($button.Current.Name.StartsWith($Prefix, [System.StringComparison]::Ordinal)) { return $button }
  }
  return $null
}

function Invoke-Button([System.Windows.Automation.AutomationElement]$Button) {
  if ($null -eq $Button) { throw 'Required packaged Game Intelligence button is unavailable.' }
  $pattern = $null
  if (-not $Button.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
    throw "InvokePattern unavailable for $($Button.Current.Name)"
  }
  $pattern.Invoke()
}

function Start-App([int]$Attempt) {
  $oldConfig = [Environment]::GetEnvironmentVariable('BAI_TASK036_LAUNCH_CONFIG', 'Process')
  $oldArgs = [Environment]::GetEnvironmentVariable('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', 'Process')
  try {
    [Environment]::SetEnvironmentVariable('BAI_TASK036_LAUNCH_CONFIG', [string]$metadata.launch_config, 'Process')
    [Environment]::SetEnvironmentVariable('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', '--force-renderer-accessibility', 'Process')
    $process = Start-Process -FilePath $exe -WorkingDirectory $package -PassThru
  } finally {
    [Environment]::SetEnvironmentVariable('BAI_TASK036_LAUNCH_CONFIG', $oldConfig, 'Process')
    [Environment]::SetEnvironmentVariable('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', $oldArgs, 'Process')
  }
  $deadline = [DateTime]::UtcNow.AddSeconds(60)
  $window = $null
  do {
    Start-Sleep -Milliseconds 300
    $process.Refresh()
    if (-not $process.HasExited) { $window = Find-ProcessWindow $process.Id }
  } while ($null -eq $window -and -not $process.HasExited -and [DateTime]::UtcNow -lt $deadline)
  if ($process.HasExited -or $null -eq $window) { throw "Packaged launch $Attempt failed to expose a native window." }
  $handle = [IntPtr]$window.Current.NativeWindowHandle
  [void][Task049Win32]::ShowWindow($handle, 3)
  [void][Task049Win32]::SetForegroundWindow($handle)
  $readyDeadline = [DateTime]::UtcNow.AddSeconds(60)
  $root = $null
  do {
    Start-Sleep -Milliseconds 400
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
    $gameButton = Find-ButtonExact $root 'G Game Intelligence'
  } while ($null -eq $gameButton -and [DateTime]::UtcNow -lt $readyDeadline)
  if ($null -eq $gameButton) { throw 'Packaged Shell did not expose the TASK-049 Game Intelligence stage.' }
  return [ordered]@{ process=$process; root=$root; handle=$handle; gameButton=$gameButton }
}

function Close-App($Run) {
  [void][Task049Win32]::PostMessage($Run.handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
  if (-not $Run.process.WaitForExit(15000)) { throw 'Packaged Shell did not close within 15 seconds.' }
}

function Wait-ForEventState([System.Windows.Automation.AutomationElement]$Root, [string]$State) {
  $deadline = [DateTime]::UtcNow.AddSeconds(30)
  do {
    Start-Sleep -Milliseconds 350
    $button = Find-ButtonPrefix $Root ("WINDOW_VAULT · " + $State)
  } while ($null -eq $button -and [DateTime]::UtcNow -lt $deadline)
  return $button
}

$first = $null
$second = $null
try {
  $first = Start-App 1
  Invoke-Button $first.gameButton
  $initialEvent = Wait-ForEventState $first.root 'NEEDS_REVIEW'
  if ($null -eq $initialEvent) { throw 'Initial NEEDS_REVIEW Event was not projected from the packaged Game Intelligence store.' }
  Invoke-Button $initialEvent
  $confirm = Find-ButtonExact $first.root '承認 / Confirm'
  if ($null -eq $confirm -or -not $confirm.Current.IsEnabled) { throw 'Human Confirm control is unavailable for the selected Event.' }
  Invoke-Button $confirm
  $confirmed = Wait-ForEventState $first.root 'CONFIRMED'
  if ($null -eq $confirmed) { throw 'Packaged Human Confirm did not read back as CONFIRMED.' }
  Close-App $first
  $first = $null

  $second = Start-App 2
  Invoke-Button $second.gameButton
  $restartConfirmed = Wait-ForEventState $second.root 'CONFIRMED'
  if ($null -eq $restartConfirmed) { throw 'CONFIRMED Event did not survive packaged restart/read-back.' }
  Close-App $second
  $second = $null

  $receipt = [ordered]@{
    receipt_version = '1.0.0'
    task = 'TASK-049'
    unit = 'R9B2'
    result = 'PASS'
    exe_sha256 = $exeHash
    match_id = [string]$metadata.match_id
    event_id = [string]$metadata.event_id
    initial_confirmation = 'NEEDS_REVIEW'
    human_confirmation_applied = $true
    restart_readback_confirmation = 'CONFIRMED'
    provider_execution_started = $false
    production_timeline_mutated = $false
    resolve_write_performed = $false
    public_release_performed = $false
  }
  $receiptPath = Join-Path $evidence 'task049-r9b2-packaged-smoke.json'
  $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
  Write-Host '[PASS] TASK-049 R9B2 packaged Game Intelligence smoke passed.'
  Write-Host "[PASS] Evidence: $receiptPath"
} finally {
  if ($null -ne $first -and -not $first.process.HasExited) { try { Close-App $first } catch {} }
  if ($null -ne $second -and -not $second.process.HasExited) { try { Close-App $second } catch {} }
}
