param(
  [Parameter(Mandatory = $true)]
  [string]$PackageDirectory,
  [string]$EvidencePath = "task036-webview2-recovery-evidence.json"
)

$ErrorActionPreference = 'Stop'
$package = (Resolve-Path -LiteralPath $PackageDirectory).Path
$exe = Join-Path $package 'BAI Video Production.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Packaged executable not found: $exe" }

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$process = $null
try {
  $start = [System.Diagnostics.ProcessStartInfo]::new()
  $start.FileName = $exe
  $start.WorkingDirectory = $package
  $start.UseShellExecute = $false
  $start.EnvironmentVariables['WEBVIEW2_BROWSER_EXECUTABLE_FOLDER'] = Join-Path $env:TEMP 'bai-task036-intentionally-missing-webview2'
  $process = [System.Diagnostics.Process]::Start($start)
  $deadline = [DateTime]::UtcNow.AddSeconds(30)
  do {
    Start-Sleep -Milliseconds 250
    $process.Refresh()
  } while ($process.MainWindowHandle -eq 0 -and -not $process.HasExited -and [DateTime]::UtcNow -lt $deadline)
  if ($process.HasExited -or $process.MainWindowHandle -eq 0) { throw 'Missing-WebView2 recovery dialog did not open.' }

  $root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
  $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  $text = @($all | ForEach-Object { $_.Current.Name } | Where-Object { $_ }) -join "\n"
  $required = @(
    'ERR_TASK036_WEBVIEW2_RUNTIME_REQUIRED',
    'Microsoft Edge WebView2 Runtime is required',
    'Install or repair Microsoft Edge WebView2 Runtime and retry',
    'https://developer.microsoft.com/microsoft-edge/webview2/'
  )
  $missing = @($required | Where-Object { -not $text.Contains($_) })

  [void]$process.CloseMainWindow()
  if (-not $process.WaitForExit(10000)) { throw 'Recovery dialog did not close safely.' }
  $result = [ordered]@{
    evidence_version = '1.0.0'
    task = 'TASK-036'
    gate = 'MISSING_WEBVIEW2_NATIVE_RECOVERY'
    timestamp_utc = [DateTime]::UtcNow.ToString('o')
    package_sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    fixed_runtime_override_used = $true
    installed_runtime_changed = $false
    automatic_install_performed = $false
    native_dialog_opened = $true
    required_recovery_content_present = $missing.Count -eq 0
    missing_content = $missing
    owned_process_exit = $true
  }
  $result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8
  $result | ConvertTo-Json -Depth 5
  if ($missing.Count -ne 0) { exit 2 }
} finally {
  if ($null -ne $process -and -not $process.HasExited) {
    [void]$process.CloseMainWindow()
    [void]$process.WaitForExit(5000)
  }
}
