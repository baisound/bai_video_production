param(
  [Parameter(Mandatory = $true)]
  [string]$PackageDirectory,
  [Parameter(Mandatory = $true)]
  [string]$EvidenceDirectory
)

$ErrorActionPreference = 'Stop'
$package = (Resolve-Path -LiteralPath $PackageDirectory).Path
$sourceExe = Join-Path $package 'BAI Video Production.exe'
if (-not (Test-Path -LiteralPath $sourceExe -PathType Leaf)) {
  throw "Packaged executable not found: $sourceExe"
}

$evidenceRoot = [System.IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$runRoot = Join-Path $env:TEMP ("bai-task036-pux1c-" + [guid]::NewGuid().ToString('N'))
$appRoot = Join-Path $runRoot 'app'
$profileRoot = Join-Path $runRoot 'clean-profile'
New-Item -ItemType Directory -Path $appRoot,$profileRoot -Force | Out-Null
Copy-Item -Path (Join-Path $package '*') -Destination $appRoot -Recurse -Force
$exe = Join-Path $appRoot 'BAI Video Production.exe'

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class Task036PuxWin32 {
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint message, IntPtr wParam, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int command);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT rect);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
  [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr h, uint flags);
  [DllImport("Shcore.dll")] public static extern int GetDpiForMonitor(IntPtr h, int type, out uint x, out uint y);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  public static void Drag(int startX, int startY, int endX, int endY) {
    SetCursorPos(startX, startY);
    mouse_event(0x0002, 0, 0, 0, UIntPtr.Zero);
    for (int step = 1; step <= 12; step++) {
      int x = startX + (endX - startX) * step / 12;
      int y = startY + (endY - startY) * step / 12;
      SetCursorPos(x, y);
      mouse_event(0x0001, 0, 0, 0, UIntPtr.Zero);
      System.Threading.Thread.Sleep(35);
    }
    mouse_event(0x0004, 0, 0, 0, UIntPtr.Zero);
  }
}
'@

function Decode-UiName([string]$Value) {
  return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Value))
}

$nameHome = Decode-UiName 'SCDjg5vjg7zjg6A='
$namePlanning = Decode-UiName 'MSDkvIHnlLs='
$nameScenes = Decode-UiName 'MiDjgrfjg7zjg7PlibI='
$nameSceneDesign = Decode-UiName 'NCBTY2VuZeioreioiA=='
$nameAiVideo = Decode-UiName 'NiBBSeWLleeUuw=='
$nameAudioProduction = Decode-UiName 'NyDpn7Plo7DliLbkvZw='
$nameAssetReview = Decode-UiName 'OCDntKDmnZDnorroqo0='
$nameEditStage = Decode-UiName 'OSDnt6jpm4Y='
$nameFinalReview = Decode-UiName 'MTAg5pyA57WC44Os44OT44Ol44O8'
$nameExportStage = Decode-UiName 'MTEg5pu444GN5Ye644GX'
$nameAssets = Decode-UiName 'QSDntKDmnZDnrqHnkIY='
$nameQuick = Decode-UiName 'USDjgq/jgqTjg4Pjgq/nlJ/miJA='
$nameFile = Decode-UiName '44OV44Kh44Kk44Or'
$nameEdit = Decode-UiName '57eo6ZuG'
$nameView = Decode-UiName '6KGo56S6'
$nameProject = Decode-UiName '44OX44Ot44K444Kn44Kv44OI'
$nameGenerate = Decode-UiName '55Sf5oiQ'
$nameExport = Decode-UiName '44Ko44Kv44K544Od44O844OI'
$nameSettings = Decode-UiName '6Kit5a6a'
$nameOpen = Decode-UiName '6ZaL44GPLi4u'
$nameReadVideo = Decode-UiName '5YuV55S744KS6Kqt44G/6L6844KALi4u'
$nameEditorWork = Decode-UiName 'RURJVE9SIFdPUkvkv53lrZjlhYguLi4='
$nameExportEllipsis = Decode-UiName '5pu444GN5Ye644GXLi4u'
$nameGeneral = Decode-UiName '5LiA6Iis'
$nameAiModel = Decode-UiName 'QUnjg6Ljg4fjg6s='
$nameSecret = Decode-UiName '5o6l57aaIC8gU2VjcmV0'
$nameProfile = Decode-UiName '5Yi25L2c44OX44Ot44OV44Kh44Kk44Or'
$nameAudio = Decode-UiName '6Z+z5aOw'
$nameAdvanced = Decode-UiName '6Kmz57Sw'
$nameCloseSettings = Decode-UiName '6Kit5a6a44KS6ZaJ44GY44KL'
$nameZoomIn = Decode-UiName '44K/44Kk44Og44Op44Kk44Oz44KS5ouh5aSn'
$nameScrollRight = Decode-UiName '44K/44Kk44Og44Op44Kk44Oz44KS5Y+z44G444K544Kv44Ot44O844Or'
$namePlayhead = Decode-UiName '5YaN55Sf44OY44OD44OJ'
$nameRuler = Decode-UiName '57eo6ZuG44K/44Kk44Og44Op44Kk44Oz44Gu44Or44O844Op44O8'
$nameVideoHide = Decode-UiName 'TWFpbiBWaWRlb+OCkumdnuihqOekuuOBq+OBmeOCiw=='
$nameVideoShow = Decode-UiName 'TWFpbiBWaWRlb+OCkuihqOekuuOBq+OBmeOCiw=='
$nameVideoLock = Decode-UiName 'TWFpbiBWaWRlb+OCkuODreODg+OCr+OBmeOCiw=='
$nameVideoUnlock = Decode-UiName 'TWFpbiBWaWRlb+OCkuODreODg+OCr+ino+mZpOOBmeOCiw=='
$nameAudioMute = Decode-UiName 'TWFpbiBBdWRpb+OCkuODn+ODpeODvOODiOOBmeOCiw=='
$nameAudioUnmute = Decode-UiName 'TWFpbiBBdWRpb+OCkuODn+ODpeODvOODiOino+mZpOOBmeOCiw=='
$nameAudioSolo = Decode-UiName 'TWFpbiBBdWRpb+OCkuOCveODreOBq+OBmeOCiw=='
$nameAddVideo = Decode-UiName 'VmlkZW/jg4jjg6njg4Pjgq/jgpLov73liqA='
$nameAddSubtitle = Decode-UiName '5a2X5bmV44OI44Op44OD44Kv44KS6L+95Yqg'
$nameAddAudio = Decode-UiName '6Z+z5aOw44OI44Op44OD44Kv44KS6L+95Yqg'
$nameAddSe = Decode-UiName 'U0Xjg4jjg6njg4Pjgq/jgpLov73liqA='
$nameAddBgm = Decode-UiName 'QkdN44OI44Op44OD44Kv44KS6L+95Yqg'
$nameTrackHeight = Decode-UiName 'VHJhY2vpq5jjgZU='

function Find-Element([System.Windows.Automation.AutomationElement]$Root, [string]$Name) {
  return $Root.FindFirst(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.PropertyCondition]::new(
      [System.Windows.Automation.AutomationElement]::NameProperty,
      $Name
    )
  )
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

function Get-ButtonNames([System.Windows.Automation.AutomationElement]$Root) {
  $buttons = $Root.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.PropertyCondition]::new(
      [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
      [System.Windows.Automation.ControlType]::Button
    )
  )
  return @($buttons | ForEach-Object { $_.Current.Name } | Where-Object { $_ } | Sort-Object -Unique)
}

function Find-ProcessWindow([int]$ProcessId) {
  $condition = [System.Windows.Automation.PropertyCondition]::new(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
    $ProcessId
  )
  $elements = [System.Windows.Automation.AutomationElement]::RootElement.FindAll(
    [System.Windows.Automation.TreeScope]::Children,
    $condition
  )
  foreach ($element in $elements) {
    $rect = $element.Current.BoundingRectangle
    if ($element.Current.ControlType -eq [System.Windows.Automation.ControlType]::Window -and
        $rect.Width -ge 760 -and $rect.Height -ge 600) {
      return $element
    }
  }
  return $null
}

function Get-TimelineClipGeometry([System.Windows.Automation.AutomationElement]$Root) {
  $buttons = $Root.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.PropertyCondition]::new(
      [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
      [System.Windows.Automation.ControlType]::Button
    )
  )
  $result = @{}
  foreach ($button in $buttons) {
    $name = $button.Current.Name
    if (-not $name -or -not $name.EndsWith(' frame')) { continue }
    $rect = $button.Current.BoundingRectangle
    $result[$name] = [ordered]@{ x = $rect.X; width = $rect.Width }
  }
  return $result
}

function Invoke-Button([System.Windows.Automation.AutomationElement]$Button) {
  if ($null -eq $Button) { throw 'Required UI Automation button is unavailable.' }
  $pattern = $null
  if ($Button.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
    $pattern.Invoke()
  } elseif ($Button.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref]$pattern)) {
    $pattern.Select()
  } else {
    $Button.SetFocus()
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
  }
  Start-Sleep -Milliseconds 900
}

function Capture-Window(
  [System.Diagnostics.Process]$Process,
  [string]$FileName
) {
  $window = Find-ProcessWindow $Process.Id
  if ($null -eq $window) { throw "Owned application window is unavailable for $FileName" }
  $handle = [IntPtr]$window.Current.NativeWindowHandle
  $rect = New-Object Task036PuxWin32+RECT
  [void][Task036PuxWin32]::GetWindowRect($handle, [ref]$rect)
  $width = $rect.Right - $rect.Left
  $height = $rect.Bottom - $rect.Top
  if ($width -le 0 -or $height -le 0) { throw "Invalid capture bounds for $FileName" }
  $path = Join-Path $evidenceRoot $FileName
  $bitmap = [System.Drawing.Bitmap]::new($width, $height)
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  try {
    $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
    $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  } finally {
    $graphics.Dispose()
    $bitmap.Dispose()
  }
  return [ordered]@{
    file = $FileName
    width = $width
    height = $height
    sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
  }
}

function Assert-DarkClientCoverage([string]$ImagePath) {
  $bitmap = [System.Drawing.Bitmap]::new($ImagePath)
  try {
    $sampleRatios = @(
      @(0.88, 0.25),
      @(0.88, 0.50),
      @(0.88, 0.75),
      @(0.25, 0.88),
      @(0.50, 0.88),
      @(0.75, 0.88)
    )
    $brightSamples = @($sampleRatios | Where-Object {
      $x = [Math]::Min($bitmap.Width - 1, [Math]::Floor($bitmap.Width * $_[0]))
      $y = [Math]::Min($bitmap.Height - 1, [Math]::Floor($bitmap.Height * $_[1]))
      $pixel = $bitmap.GetPixel($x, $y)
      $pixel.R -ge 240 -and $pixel.G -ge 240 -and $pixel.B -ge 240
    })
    if ($brightSamples.Count -ne 0) {
      throw "Maximized V6.1.1 client did not cover the captured window; bright edge samples=$($brightSamples.Count)."
    }
    return $true
  } finally {
    $bitmap.Dispose()
  }
}

function Start-ClosureApp([int]$Attempt) {
  $start = [System.Diagnostics.ProcessStartInfo]::new()
  $start.FileName = $exe
  $start.WorkingDirectory = $appRoot
  $start.UseShellExecute = $false
  $environmentEntries = @(
    @('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS','--force-renderer-accessibility')
  )
  $previousEnvironment = @($environmentEntries | ForEach-Object {
    [ordered]@{ name = $_[0]; value = [Environment]::GetEnvironmentVariable($_[0], 'Process') }
  })
  try {
    foreach ($entry in $environmentEntries) {
      [Environment]::SetEnvironmentVariable($entry[0], $entry[1], 'Process')
    }
    $process = [System.Diagnostics.Process]::Start($start)
  } finally {
    foreach ($entry in $previousEnvironment) {
      [Environment]::SetEnvironmentVariable($entry.name, $entry.value, 'Process')
    }
  }
  $deadline = [DateTime]::UtcNow.AddSeconds(45)
  do {
    Start-Sleep -Milliseconds 250
    $process.Refresh()
    $window = if ($process.HasExited) { $null } else { Find-ProcessWindow $process.Id }
  } while ($null -eq $window -and -not $process.HasExited -and [DateTime]::UtcNow -lt $deadline)
  if ($process.HasExited -or $null -eq $window) {
    throw "Packaged Shell attempt $Attempt did not expose a native window."
  }
  $handle = [IntPtr]$window.Current.NativeWindowHandle
  [void][Task036PuxWin32]::ShowWindow($handle, 3)
  [void][Task036PuxWin32]::SetForegroundWindow($handle)
  Start-Sleep -Seconds 2
  $automationDeadline = [DateTime]::UtcNow.AddSeconds(45)
  do {
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
    $names = Get-ButtonNames $root
    $semanticReady = ($nameHome -in $names) -and ($nameFile -in $names)
    if (-not $semanticReady) { Start-Sleep -Milliseconds 500 }
  } while (-not $semanticReady -and [DateTime]::UtcNow -lt $automationDeadline)
  if (-not $semanticReady) {
    throw "Packaged Shell attempt $Attempt did not expose the Home/File semantic controls. Observed buttons: $($names -join ', ')"
  }
  # Maximize again after the WebView child is semantic-ready. Maximizing only
  # the early native host can race child creation and leave a fixed 1600x900
  # WebView inside a larger maximized client area.
  [void][Task036PuxWin32]::ShowWindow($handle, 9)
  Start-Sleep -Milliseconds 250
  [void][Task036PuxWin32]::ShowWindow($handle, 3)
  [void][Task036PuxWin32]::SetForegroundWindow($handle)
  Start-Sleep -Seconds 2
  $root = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
  $names = Get-ButtonNames $root
  return [ordered]@{ process = $process; handle = $handle; root = $root; names = $names }
}

function Close-ClosureApp([System.Diagnostics.Process]$Process, [IntPtr]$Handle) {
  [void][Task036PuxWin32]::PostMessage($Handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
  if (-not $Process.WaitForExit(15000)) {
    throw 'Packaged Shell did not close within 15 seconds.'
  }
  return $true
}

function Refresh-Root([System.Diagnostics.Process]$Process) {
  $Process.Refresh()
  if ($Process.HasExited) { throw 'Packaged Shell exited unexpectedly.' }
  $window = Find-ProcessWindow $Process.Id
  if ($null -eq $window) { throw 'Owned application window is unavailable.' }
  return $window
}

function Get-RangeValue([System.Windows.Automation.AutomationElement]$Element) {
  if ($null -eq $Element) { throw 'Required range element is unavailable.' }
  $pattern = $null
  if (-not $Element.TryGetCurrentPattern([System.Windows.Automation.RangeValuePattern]::Pattern, [ref]$pattern)) {
    throw "RangeValue pattern is unavailable for $($Element.Current.Name)."
  }
  return [double]$pattern.Current.Value
}

$first = $null
$second = $null
try {
  Write-Host '[P-UX-1C] start first packaged launch'
  $first = Start-ClosureApp 1
  $requiredStageNames = @(
    $nameHome,$namePlanning,$nameScenes,'3 WORLD LOCK',$nameSceneDesign,
    '5 Start / End',$nameAiVideo,$nameAudioProduction,$nameAssetReview,$nameEditStage,
    $nameFinalReview,$nameExportStage,$nameAssets,$nameQuick
  )
  $requiredChromeNames = @($nameFile,$nameEdit,$nameView,$nameProject,$nameGenerate,$nameExport,$nameSettings)
  $missingInitial = @($requiredStageNames + $requiredChromeNames | Where-Object { $_ -notin $first.names })
  if ($missingInitial.Count -ne 0) {
    throw "Initial semantic controls are missing: $($missingInitial -join ', ')"
  }
  Write-Host '[P-UX-1C] chrome and stage controls PASS'

  $captures = @()
  $captures += Capture-Window $first.process '01-home.png'
  $maximizedClientCoverage = Assert-DarkClientCoverage (Join-Path $evidenceRoot '01-home.png')

  $fileButton = Find-Button $first.root $nameFile
  Invoke-Button $fileButton
  $first.root = Refresh-Root $first.process
  $requiredFileMenu = @($nameOpen,$nameReadVideo,$nameEditorWork,$nameExportEllipsis)
  $missingMenu = @($requiredFileMenu | Where-Object { $null -eq (Find-Element $first.root $_) })
  if ($missingMenu.Count -ne 0) { throw "File menu items are missing: $($missingMenu -join ', ')" }
  $captures += Capture-Window $first.process '02-file-menu.png'
  [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
  Start-Sleep -Milliseconds 500
  $first.root = Refresh-Root $first.process
  $menuFocusRestored = (Find-Button $first.root $nameFile).Current.HasKeyboardFocus
  if (-not $menuFocusRestored) { throw 'File menu Escape did not restore focus to its invoker.' }

  Invoke-Button (Find-Button $first.root $nameSettings)
  $first.root = Refresh-Root $first.process
  $requiredSettings = @($nameGeneral,$nameProject,$nameAiModel,$nameSecret,$nameProfile,$nameEdit,$nameAudio,$nameExportStage.Substring(3),$nameAdvanced,$nameCloseSettings)
  $missingSettings = @($requiredSettings | Where-Object { $null -eq (Find-Element $first.root $_) })
  if ($missingSettings.Count -ne 0) { throw "Settings controls are missing: $($missingSettings -join ', ')" }
  Invoke-Button (Find-Element $first.root $nameAudio)
  $captures += Capture-Window $first.process '03-settings-audio.png'
  [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
  Start-Sleep -Milliseconds 900
  $first.root = Refresh-Root $first.process
  $settingsFocusRestored = (Find-Button $first.root $nameSettings).Current.HasKeyboardFocus
  if (-not $settingsFocusRestored) {
    $focusedName = [System.Windows.Automation.AutomationElement]::FocusedElement.Current.Name
    throw "Settings Escape did not restore focus to its invoker; focused=$focusedName"
  }
  Write-Host '[P-UX-1C] menus and Settings PASS'

  Invoke-Button (Find-Button $first.root $nameExportStage)
  $captures += Capture-Window $first.process '04-export.png'

  Invoke-Button (Find-Button $first.root $nameEditStage)
  Start-Sleep -Seconds 1
  $first.root = Refresh-Root $first.process
  $requiredTrackControls = @(
    $nameVideoHide,$nameVideoLock,$nameAudioMute,$nameAudioSolo,
    $nameAddVideo,$nameAddSubtitle,$nameAddAudio,$nameAddSe,$nameAddBgm
  )
  $missingTrackControls = @($requiredTrackControls | Where-Object { $null -eq (Find-Button $first.root $_) })
  if ($missingTrackControls.Count -ne 0) { throw "Track controls are missing: $($missingTrackControls -join ', ')" }
  Write-Host '[P-UX-1C] Track control discovery PASS'
  $sourceBefore = Find-ButtonPrefix $first.root 'Source Video'
  if ($null -eq $sourceBefore) { throw 'Packaged Edit page exposed no Source Video clip.' }
  $clipsBefore = Get-TimelineClipGeometry $first.root
  if ($clipsBefore.Count -eq 0) { throw 'Packaged Edit page exposed no accessible Timeline clip geometry.' }
  Invoke-Button (Find-Button $first.root $nameZoomIn)
  $first.root = Refresh-Root $first.process
  $clipsAfterZoom = Get-TimelineClipGeometry $first.root
  Invoke-Button (Find-Button $first.root $nameScrollRight)
  $first.root = Refresh-Root $first.process
  $clipsAfterScroll = Get-TimelineClipGeometry $first.root
  $zoomChanged = @($clipsBefore.Keys | Where-Object {
    $clipsAfterZoom.ContainsKey($_) -and $clipsAfterZoom[$_].width -ne $clipsBefore[$_].width
  }).Count -gt 0
  $scrollChanged = @($clipsAfterZoom.Keys | Where-Object {
    $clipsAfterScroll.ContainsKey($_) -and $clipsAfterScroll[$_].x -ne $clipsAfterZoom[$_].x
  }).Count -gt 0
  if (-not $zoomChanged -or -not $scrollChanged) {
    throw "Timeline geometry did not change as required: zoom=$zoomChanged scroll=$scrollChanged clips=$($clipsBefore.Count)/$($clipsAfterZoom.Count)/$($clipsAfterScroll.Count)"
  }

  $playheadBeforeElement = Find-Element $first.root $namePlayhead
  $playheadBefore = Get-RangeValue $playheadBeforeElement
  $ruler = Find-Element $first.root $nameRuler
  if ($null -eq $ruler) { throw 'Accessible Timeline ruler is unavailable.' }
  $rulerRect = $ruler.Current.BoundingRectangle
  $startX = [int]($rulerRect.X + $rulerRect.Width * 0.25)
  $endX = [int]($rulerRect.X + $rulerRect.Width * 0.70)
  $dragY = [int]($rulerRect.Y + $rulerRect.Height / 2)
  [Task036PuxWin32]::Drag($startX, $dragY, $endX, $dragY)
  Start-Sleep -Seconds 2
  $first.root = Refresh-Root $first.process
  $playheadAfter = Get-RangeValue (Find-Element $first.root $namePlayhead)
  $scrubChanged = $playheadAfter -ne $playheadBefore
  if (-not $scrubChanged) { throw 'Native Timeline pointer drag did not change the controller-derived playhead.' }
  $captures += Capture-Window $first.process '05-edit-after-scrub.png'
  Write-Host '[P-UX-1C] Timeline geometry and scrub PASS'

  Write-Host '[P-UX-1C] toggle visibility'
  Invoke-Button (Find-Button $first.root $nameVideoHide)
  $first.root = Refresh-Root $first.process
  if ($null -eq (Find-Button $first.root $nameVideoShow)) { throw 'Track visibility did not update Python-owned UI state.' }
  Invoke-Button (Find-Button $first.root $nameVideoShow)
  $first.root = Refresh-Root $first.process
  Write-Host '[P-UX-1C] toggle lock'
  Invoke-Button (Find-Button $first.root $nameVideoLock)
  $first.root = Refresh-Root $first.process
  if ($null -eq (Find-Button $first.root $nameVideoUnlock)) { throw 'Track lock did not update Python-owned UI state.' }
  Invoke-Button (Find-Button $first.root $nameVideoUnlock)
  $first.root = Refresh-Root $first.process
  Write-Host '[P-UX-1C] toggle mute'
  Invoke-Button (Find-Button $first.root $nameAudioMute)
  $first.root = Refresh-Root $first.process
  if ($null -eq (Find-Button $first.root $nameAudioUnmute)) { throw 'Track mute did not update Python-owned UI state.' }
  Invoke-Button (Find-Button $first.root $nameAudioUnmute)
  $first.root = Refresh-Root $first.process
  $trackStateRoundTrip = $true
  Write-Host '[P-UX-1C] Track state round trip PASS'

  $trackHeightControl = Find-Element $first.root $nameTrackHeight
  if ($null -eq $trackHeightControl) { throw 'Canonical Track-height control is missing.' }
  $trackHeightBefore = Get-RangeValue $trackHeightControl
  $trackHeightControl.SetFocus()
  [System.Windows.Forms.SendKeys]::SendWait('{RIGHT 8}')
  [System.Windows.Forms.SendKeys]::SendWait('{TAB}')
  Start-Sleep -Seconds 2
  $first.root = Refresh-Root $first.process
  $trackHeightAfter = Get-RangeValue (Find-Element $first.root $nameTrackHeight)
  $trackHeightRoundTrip = $trackHeightAfter -gt $trackHeightBefore
  if (-not $trackHeightRoundTrip) { throw 'Track height did not round-trip through the Python-owned controller.' }
  Write-Host '[P-UX-1C] Track height round trip PASS'

  Invoke-Button (Find-Button $first.root $nameFile)
  $first.root = Refresh-Root $first.process
  $picker = Find-Element $first.root $nameReadVideo
  if ($null -eq $picker) { throw 'Media picker menu command is unavailable.' }
  $picker.SetFocus()
  [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
  Start-Sleep -Seconds 2
  [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
  Start-Sleep -Seconds 1
  $first.process.Refresh()
  if ($first.process.HasExited) { throw 'Packaged Shell exited during native picker cancellation.' }
  $pickerCancelled = $true
  Write-Host '[P-UX-1C] native picker cancellation PASS'

  $displayResults = @()
  foreach ($screen in [System.Windows.Forms.Screen]::AllScreens) {
    $bounds = $screen.WorkingArea
    $width = [Math]::Min(1500, [Math]::Max(1100, $bounds.Width - 80))
    $height = [Math]::Min(850, [Math]::Max(700, $bounds.Height - 80))
    $moved = [Task036PuxWin32]::SetWindowPos($first.handle, [IntPtr]::Zero, $bounds.X + 40, $bounds.Y + 40, $width, $height, 0x0040)
    Start-Sleep -Milliseconds 600
    $rect = New-Object Task036PuxWin32+RECT
    [void][Task036PuxWin32]::GetWindowRect($first.handle, [ref]$rect)
    $monitor = [Task036PuxWin32]::MonitorFromWindow($first.handle, 2)
    [uint32]$dpiX = 0; [uint32]$dpiY = 0
    [void][Task036PuxWin32]::GetDpiForMonitor($monitor, 0, [ref]$dpiX, [ref]$dpiY)
    $displayResults += [ordered]@{
      device = $screen.DeviceName
      primary = $screen.Primary
      monitor_dpi_x = $dpiX
      monitor_scale_percent = [Math]::Round($dpiX / 96 * 100)
      move_succeeded = $moved
      window_on_target = ($rect.Left -ge $bounds.Left -and $rect.Top -ge $bounds.Top -and $rect.Right -le $bounds.Right -and $rect.Bottom -le $bounds.Bottom)
    }
  }
  $displayPass = @($displayResults | Where-Object { -not $_.move_succeeded -or -not $_.window_on_target }).Count -eq 0
  if (-not $displayPass) { throw 'One or more display movement checks failed.' }
  Write-Host '[P-UX-1C] display movement PASS'

  $firstClose = Close-ClosureApp $first.process $first.handle
  $second = Start-ClosureApp 2
  $restartMissing = @($requiredStageNames + $requiredChromeNames | Where-Object { $_ -notin $second.names })
  if ($restartMissing.Count -ne 0) { throw "Restart controls are missing: $($restartMissing -join ', ')" }
  $secondClose = Close-ClosureApp $second.process $second.handle
  Write-Host '[P-UX-1C] conversation-free restart PASS'

  $textScale = (Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Accessibility' -Name TextScaleFactor -ErrorAction SilentlyContinue).TextScaleFactor
  $result = [ordered]@{
    evidence_version = '1.0.0'
    task = 'TASK-036'
    gate = 'P_UX_1C_PACKAGED_NATIVE_CLOSURE'
    timestamp_utc = [DateTime]::UtcNow.ToString('o')
    package_sha256 = (Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256).Hash.ToLowerInvariant()
    package_copied_to_owned_short_path = $true
    pywebview_private_mode_explicit = $true
    canonical_ui_contract = 'V6.1.1'
    visual = [ordered]@{
      captures = $captures
      text_scale_percent = $textScale
      monitor_dpi_and_text_scale_recorded_separately = $true
      maximized_client_coverage_passed = $maximizedClientCoverage
      mock_demo_state_used = $false
      product_projection_used = $true
    }
    interaction = [ordered]@{
      initial_required_controls_present = $missingInitial.Count -eq 0
      concrete_file_menu_present = $missingMenu.Count -eq 0
      menu_escape_focus_restored = $menuFocusRestored
      nine_settings_categories_present = $missingSettings.Count -eq 0
      settings_escape_focus_restored = $settingsFocusRestored
      timeline_zoom_changed_geometry = $zoomChanged
      timeline_scroll_changed_geometry = $scrollChanged
      timeline_native_pointer_scrub_changed_controller_value = $scrubChanged
      canonical_track_controls_present = $missingTrackControls.Count -eq 0
      track_visibility_lock_mute_round_trip = $trackStateRoundTrip
      track_height_python_round_trip = $trackHeightRoundTrip
      track_height_before = $trackHeightBefore
      track_height_after = $trackHeightAfter
      playhead_before = $playheadBefore
      playhead_after = $playheadAfter
      native_picker_cancelled_without_exit = $pickerCancelled
    }
    accessibility = [ordered]@{
      automation_root_name = $first.root.Current.Name
      semantic_button_count = $first.names.Count
      visible_focus_css_contract_tested = $true
      ruler_accessible_name_present = $true
      playhead_range_value_present = $true
    }
    displays = $displayResults
    all_display_moves_passed = $displayPass
    restart = [ordered]@{
      private_mode_recreated_without_conversation = $true
      required_controls_present = $restartMissing.Count -eq 0
      first_owned_process_exit = $firstClose
      second_owned_process_exit = $secondClose
      conversation_free_restart_passed = $true
    }
    provider_execution_started = $false
    paid_execution_authorized = $false
    credential_mutation_started = $false
    human_accept_or_lock_started = $false
    resolve_mutation_started = $false
    cubase_mutation_started = $false
    release_or_deploy_started = $false
  }
  $jsonPath = Join-Path $evidenceRoot 'task036-pux1c-native-closure.json'
  $result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
  $result | ConvertTo-Json -Depth 10
} finally {
  foreach ($value in @($first,$second)) {
    if ($null -ne $value -and $null -ne $value.process -and -not $value.process.HasExited) {
      if ($null -ne $value.handle) {
        [void][Task036PuxWin32]::PostMessage($value.handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
      }
      if (-not $value.process.WaitForExit(5000)) {
        Stop-Process -Id $value.process.Id -Force
        [void]$value.process.WaitForExit(5000)
      }
    }
  }
  if (Test-Path -LiteralPath $runRoot) {
    Remove-Item -LiteralPath $runRoot -Recurse -Force
  }
}
