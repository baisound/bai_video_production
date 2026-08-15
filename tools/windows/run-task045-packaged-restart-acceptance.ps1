param(
  [Parameter(Mandatory = $true)]
  [string]$PackageDirectory,
  [string]$EvidencePath = "task045-packaged-restart-acceptance.json",
  [string]$LaunchConfig = "",
  [switch]$ProjectOpenOnly
)

$ErrorActionPreference = 'Stop'
$package = (Resolve-Path -LiteralPath $PackageDirectory).Path
$sourceExe = Join-Path $package 'BAI Video Production.exe'
if (-not (Test-Path -LiteralPath $sourceExe -PathType Leaf)) {
  throw "Packaged executable not found: $sourceExe"
}

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

function Decode-UiName([string]$Value) {
  return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Value))
}

$nameZoomIn = Decode-UiName '44K/44Kk44Og44Op44Kk44Oz44KS5ouh5aSn'
$nameZoomOut = Decode-UiName '44K/44Kk44Og44Op44Kk44Oz44KS57iu5bCP'
$nameScrollRight = Decode-UiName '44K/44Kk44Og44Op44Kk44Oz44KS5Y+z44G444K544Kv44Ot44O844Or'
$nameScrollLeft = Decode-UiName '44K/44Kk44Og44Op44Kk44Oz44KS5bem44G444K544Kv44Ot44O844Or'
$nameNextTracks = Decode-UiName '5qyh44Gu44OI44Op44OD44Kv44Oa44O844K4'
$namePreviousTracks = Decode-UiName '5YmN44Gu44OI44Op44OD44Kv44Oa44O844K4'
$nameFitAll = Decode-UiName '5YWo5L2T6KGo56S6'
$nameFitSelection = Decode-UiName '6YG45oqe6KGo56S6'
$nameChooseMedia = Decode-UiName '44Oh44OH44Kj44Ki44OV44Kh44Kk44Or44KS6YG45oqe'

$runRoot = Join-Path $env:TEMP ("bai-task045-prc2-" + [guid]::NewGuid().ToString('N'))
$appRoot = Join-Path $runRoot 'app'
$profileRoot = Join-Path $runRoot 'clean-profile'
New-Item -ItemType Directory -Path $appRoot,$profileRoot -Force | Out-Null
Copy-Item -Path (Join-Path $package '*') -Destination $appRoot -Recurse -Force
$exe = Join-Path $appRoot 'BAI Video Production.exe'
$resolvedLaunchConfig = $null
$projectManifest = $null
$projectManifestBefore = $null
if ($ProjectOpenOnly -and -not $LaunchConfig) {
  throw 'ProjectOpenOnly requires an explicit synthetic LaunchConfig.'
}
if ($LaunchConfig) {
  $resolvedLaunchConfig = (Resolve-Path -LiteralPath $LaunchConfig).Path
  $configuration = Get-Content -LiteralPath $resolvedLaunchConfig -Raw -Encoding UTF8 | ConvertFrom-Json
  $projectManifest = Join-Path $configuration.project.project_root '.bai-project\project.json'
  if (-not (Test-Path -LiteralPath $projectManifest -PathType Leaf)) {
    throw "Synthetic Project manifest not found: $projectManifest"
  }
  $projectManifestBefore = (Get-FileHash -LiteralPath $projectManifest -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Find-Button([System.Windows.Automation.AutomationElement]$Root, [string]$Name) {
  $condition = [System.Windows.Automation.AndCondition]::new(
    [System.Windows.Automation.PropertyCondition]::new(
      [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
      [System.Windows.Automation.ControlType]::Button
    ),
    [System.Windows.Automation.PropertyCondition]::new(
      [System.Windows.Automation.AutomationElement]::NameProperty,
      $Name
    )
  )
  return $Root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
}

function Find-ButtonPrefix([System.Windows.Automation.AutomationElement]$Root, [string]$Prefix) {
  $buttons = $Root.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.PropertyCondition]::new(
      [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
      [System.Windows.Automation.ControlType]::Button
    )
  )
  return @($buttons | Where-Object { $_.Current.Name.StartsWith($Prefix) })[0]
}

function Invoke-Button([System.Windows.Automation.AutomationElement]$Button) {
  if ($null -eq $Button) { throw 'Required UI Automation button is unavailable.' }
  $pattern = $Button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
  $pattern.Invoke()
  Start-Sleep -Milliseconds 700
}

function Start-AcceptanceApp([int]$Attempt) {
  $start = [System.Diagnostics.ProcessStartInfo]::new()
  $start.FileName = $exe
  $start.WorkingDirectory = $appRoot
  $start.UseShellExecute = $false
  if ($null -ne $resolvedLaunchConfig) {
    $start.Arguments = '--launch-config "' + $resolvedLaunchConfig.Replace('"', '\"') + '"'
  }
  $start.EnvironmentVariables['USERPROFILE'] = $profileRoot
  $start.EnvironmentVariables['APPDATA'] = (Join-Path $profileRoot 'AppData\Roaming')
  $start.EnvironmentVariables['LOCALAPPDATA'] = (Join-Path $profileRoot 'AppData\Local')
  $start.EnvironmentVariables['TEMP'] = (Join-Path $profileRoot 'Temp')
  $start.EnvironmentVariables['TMP'] = (Join-Path $profileRoot 'Temp')
  $start.EnvironmentVariables['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = '--force-renderer-accessibility'
  New-Item -ItemType Directory -Path $start.EnvironmentVariables['APPDATA'],$start.EnvironmentVariables['LOCALAPPDATA'],$start.EnvironmentVariables['TEMP'] -Force | Out-Null
  $process = [System.Diagnostics.Process]::Start($start)
  $deadline = [DateTime]::UtcNow.AddSeconds(45)
  do {
    Start-Sleep -Milliseconds 250
    $process.Refresh()
  } while ($process.MainWindowHandle -eq 0 -and -not $process.HasExited -and [DateTime]::UtcNow -lt $deadline)
  if ($process.HasExited -or $process.MainWindowHandle -eq 0) {
    throw "Packaged Shell attempt $Attempt did not expose a native window."
  }
  $automationDeadline = [DateTime]::UtcNow.AddSeconds(20)
  do {
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
    $buttons = $root.FindAll(
      [System.Windows.Automation.TreeScope]::Descendants,
      [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Button
      )
    )
    if ($buttons.Count -eq 0) { Start-Sleep -Milliseconds 500 }
  } while ($buttons.Count -eq 0 -and [DateTime]::UtcNow -lt $automationDeadline)
  if ($buttons.Count -eq 0) { throw "Packaged Shell attempt $Attempt exposed no semantic buttons." }
  return [ordered]@{ process = $process; root = $root; buttons = $buttons }
}

function Close-AcceptanceApp([System.Diagnostics.Process]$Process) {
  [void]$Process.CloseMainWindow()
  if (-not $Process.WaitForExit(15000)) {
    throw 'Packaged Shell did not close within 15 seconds.'
  }
  return $true
}

$first = $null
$second = $null
try {
  $first = Start-AcceptanceApp 1
  $firstNames = @($first.buttons | ForEach-Object { $_.Current.Name })
  $requiredNames = @(
    $nameZoomIn, $nameZoomOut, $nameScrollRight, $nameScrollLeft,
    $nameNextTracks, $namePreviousTracks,
    $nameFitAll, $nameFitSelection, 'IN', 'OUT', $nameChooseMedia
  )
  $missing = @($requiredNames | Where-Object { $_ -notin $firstNames })
  if ($missing.Count -ne 0) { throw "Required packaged controls are missing: $($missing -join ', ')" }

  $zoomChanged = $null
  $scrollChanged = $null
  $pickerCancelled = $null
  if (-not $ProjectOpenOnly) {
    $sourceBefore = Find-ButtonPrefix $first.root 'Source Video, VIDEO'
    $widthBefore = $sourceBefore.Current.BoundingRectangle.Width
    $xBefore = $sourceBefore.Current.BoundingRectangle.X
    Invoke-Button (Find-Button $first.root $nameZoomIn)
    $sourceAfterZoom = Find-ButtonPrefix $first.root 'Source Video, VIDEO'
    $widthAfterZoom = $sourceAfterZoom.Current.BoundingRectangle.Width
    Invoke-Button (Find-Button $first.root $nameScrollRight)
    $sourceAfterScroll = Find-ButtonPrefix $first.root 'Source Video, VIDEO'
    $xAfterScroll = $sourceAfterScroll.Current.BoundingRectangle.X
    Invoke-Button (Find-Button $first.root $nameScrollLeft)
    Invoke-Button (Find-Button $first.root $nameZoomOut)
    $zoomChanged = $widthAfterZoom -gt $widthBefore
    $scrollChanged = $xAfterScroll -ne $xBefore

    $picker = Find-Button $first.root $nameChooseMedia
    $picker.SetFocus()
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
    Start-Sleep -Seconds 2
    [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
    Start-Sleep -Seconds 1
    $first.process.Refresh()
    if ($first.process.HasExited) { throw 'Packaged Shell exited during native picker cancellation.' }
    $pickerCancelled = $true
  }

  $firstClose = Close-AcceptanceApp $first.process
  $profileEntriesAfterFirst = (Get-ChildItem -LiteralPath $profileRoot -Recurse -Force | Measure-Object).Count
  if ($profileEntriesAfterFirst -eq 0) { throw 'First launch created no isolated profile state.' }

  $second = Start-AcceptanceApp 2
  $secondNames = @($second.buttons | ForEach-Object { $_.Current.Name })
  $restartMissing = @($requiredNames | Where-Object { $_ -notin $secondNames })
  if ($restartMissing.Count -ne 0) { throw "Restart controls are missing: $($restartMissing -join ', ')" }
  $secondClose = Close-AcceptanceApp $second.process

  $result = [ordered]@{
    evidence_version = '1.0.0'
    task = 'TASK-045'
    gate = 'P_RC_2_PACKAGED_RESTART_ACCEPTANCE'
    timestamp_utc = [DateTime]::UtcNow.ToString('o')
    package_sha256 = (Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256).Hash.ToLowerInvariant()
    package_copied_outside_checkout = $true
    clean_profile_at_start = $true
    launch_config_used = $null -ne $resolvedLaunchConfig
    project_manifest_sha256_before = $projectManifestBefore
    project_manifest_sha256_after = if ($null -eq $projectManifest) { $null } else { (Get-FileHash -LiteralPath $projectManifest -Algorithm SHA256).Hash.ToLowerInvariant() }
    first_launch = [ordered]@{
      native_window_opened = $true
      semantic_button_count = $first.buttons.Count
      unnamed_button_count = @($firstNames | Where-Object { -not $_ }).Count
      required_controls_present = $missing.Count -eq 0
      timeline_geometry_tested = -not $ProjectOpenOnly
      zoom_changed_geometry = $zoomChanged
      horizontal_scroll_changed_geometry = $scrollChanged
      native_picker_cancelled_without_exit = $pickerCancelled
      owned_process_exit = $firstClose
    }
    restart = [ordered]@{
      same_isolated_profile = $true
      prior_profile_entry_count = $profileEntriesAfterFirst
      native_window_opened = $true
      semantic_button_count = $second.buttons.Count
      unnamed_button_count = @($secondNames | Where-Object { -not $_ }).Count
      required_controls_present = $restartMissing.Count -eq 0
      owned_process_exit = $secondClose
      conversation_free_restart_passed = $true
    }
    provider_execution_started = $false
    paid_execution_authorized = $false
    resolve_mutation_started = $false
    cubase_mutation_started = $false
  }
  if (-not $ProjectOpenOnly -and (-not $result.first_launch.zoom_changed_geometry -or -not $result.first_launch.horizontal_scroll_changed_geometry)) {
    throw 'Packaged Timeline zoom/scroll interaction did not change geometry.'
  }
  if ($null -ne $projectManifest -and $result.project_manifest_sha256_before -ne $result.project_manifest_sha256_after) {
    throw 'Supported Project manifest changed during packaged open/reopen acceptance.'
  }
  $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8
  $result | ConvertTo-Json -Depth 8
} finally {
  foreach ($value in @($first,$second)) {
    if ($null -ne $value -and $null -ne $value.process -and -not $value.process.HasExited) {
      [void]$value.process.CloseMainWindow()
      [void]$value.process.WaitForExit(5000)
    }
  }
  if (Test-Path -LiteralPath $runRoot) {
    Remove-Item -LiteralPath $runRoot -Recurse -Force
  }
}
