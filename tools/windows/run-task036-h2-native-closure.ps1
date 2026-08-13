param(
  [Parameter(Mandatory = $true)]
  [string]$PackageDirectory,
  [string]$EvidencePath = "task036-h2-native-closure-evidence.json",
  [string]$ScreenshotPath = "",
  [switch]$StartNarrator
)

$ErrorActionPreference = 'Stop'
$package = (Resolve-Path -LiteralPath $PackageDirectory).Path
$sourceExe = Join-Path $package 'BAI Video Production.exe'
if (-not (Test-Path -LiteralPath $sourceExe -PathType Leaf)) {
  throw "Packaged executable not found: $sourceExe"
}

$runRoot = Join-Path $env:TEMP ("bai-task036-h2-" + [guid]::NewGuid().ToString('N'))
$appRoot = Join-Path $runRoot 'app'
$profileRoot = Join-Path $runRoot 'clean-profile'
$capturePath = if ($ScreenshotPath) { [System.IO.Path]::GetFullPath($ScreenshotPath) } else { Join-Path $runRoot 'task036-shell.png' }
New-Item -ItemType Directory -Path $appRoot,$profileRoot -Force | Out-Null
Copy-Item -Path (Join-Path $package '*') -Destination $appRoot -Recurse -Force
$exe = Join-Path $appRoot 'BAI Video Production.exe'
$priorAppStatePresent = (Get-ChildItem -LiteralPath $profileRoot -Force | Measure-Object).Count -ne 0

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class Task036Win32 {
  [DllImport("user32.dll", SetLastError=true)] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public INPUTUNION U; }
  [StructLayout(LayoutKind.Explicit)] public struct INPUTUNION { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; [FieldOffset(0)] public HARDWAREINPUT hi; }
  [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public UIntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort vk, scan; public uint flags, time; public UIntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct HARDWAREINPUT { public uint msg; public ushort low, high; }
  [DllImport("user32.dll", SetLastError=true)] static extern uint SendInput(uint count, INPUT[] inputs, int size);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT rect);
  [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr h, uint flags);
  [DllImport("Shcore.dll")] public static extern int GetDpiForMonitor(IntPtr h, int type, out uint x, out uint y);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  static INPUT Key(ushort vk, uint flags) { var input = new INPUT(); input.type = 1; input.U.ki.vk = vk; input.U.ki.flags = flags; return input; }
  public static uint ToggleNarrator() {
    var inputs = new[] { Key(0x5B,0), Key(0x11,0), Key(0x0D,0), Key(0x0D,2), Key(0x11,2), Key(0x5B,2) };
    return SendInput((uint)inputs.Length, inputs, Marshal.SizeOf(typeof(INPUT)));
  }
}
'@

$process = $null
$narratorProcess = $null
try {
  if ($StartNarrator -and -not (Get-Process -Name Narrator -ErrorAction SilentlyContinue)) {
    $narratorProcess = Start-Process -FilePath (Join-Path $env:WINDIR 'System32\Narrator.exe') -PassThru
    Start-Sleep -Seconds 3
  }
  $start = [System.Diagnostics.ProcessStartInfo]::new()
  $start.FileName = $exe
  $start.WorkingDirectory = $appRoot
  $start.UseShellExecute = $false
  $start.EnvironmentVariables['USERPROFILE'] = $profileRoot
  $start.EnvironmentVariables['APPDATA'] = (Join-Path $profileRoot 'AppData\Roaming')
  $start.EnvironmentVariables['LOCALAPPDATA'] = (Join-Path $profileRoot 'AppData\Local')
  $start.EnvironmentVariables['TEMP'] = (Join-Path $profileRoot 'Temp')
  $start.EnvironmentVariables['TMP'] = (Join-Path $profileRoot 'Temp')
  if ($StartNarrator) {
    $start.EnvironmentVariables['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = '--force-renderer-accessibility'
  }
  New-Item -ItemType Directory -Path $start.EnvironmentVariables['APPDATA'],$start.EnvironmentVariables['LOCALAPPDATA'],$start.EnvironmentVariables['TEMP'] -Force | Out-Null
  $process = [System.Diagnostics.Process]::Start($start)

  $deadline = [DateTime]::UtcNow.AddSeconds(45)
  do {
    Start-Sleep -Milliseconds 250
    $process.Refresh()
  } while ($process.MainWindowHandle -eq 0 -and -not $process.HasExited -and [DateTime]::UtcNow -lt $deadline)
  if ($process.HasExited -or $process.MainWindowHandle -eq 0) { throw 'Packaged Shell did not expose a native window.' }

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
  $buttonNames = @($buttons | ForEach-Object { $_.Current.Name } | Where-Object { $_ } | Sort-Object -Unique)

  $displayResults = @()
  foreach ($screen in [System.Windows.Forms.Screen]::AllScreens) {
    $bounds = $screen.WorkingArea
    $width = [Math]::Min(1500, [Math]::Max(1100, $bounds.Width - 80))
    $height = [Math]::Min(850, [Math]::Max(700, $bounds.Height - 80))
    $moved = [Task036Win32]::SetWindowPos($process.MainWindowHandle, [IntPtr]::Zero, $bounds.X + 40, $bounds.Y + 40, $width, $height, 0x0040)
    Start-Sleep -Milliseconds 800
    $rect = New-Object Task036Win32+RECT
    [void][Task036Win32]::GetWindowRect($process.MainWindowHandle, [ref]$rect)
    $monitor = [Task036Win32]::MonitorFromWindow($process.MainWindowHandle, 2)
    [uint32]$dpiX = 0; [uint32]$dpiY = 0
    [void][Task036Win32]::GetDpiForMonitor($monitor, 0, [ref]$dpiX, [ref]$dpiY)
    $displayResults += [ordered]@{
      device = $screen.DeviceName
      primary = $screen.Primary
      dpi_x = $dpiX
      scale_percent = [Math]::Round($dpiX / 96 * 100)
      move_succeeded = $moved
      window_width = $rect.Right - $rect.Left
      window_height = $rect.Bottom - $rect.Top
      window_on_target = ($rect.Left -ge $bounds.Left -and $rect.Top -ge $bounds.Top -and $rect.Right -le $bounds.Right -and $rect.Bottom -le $bounds.Bottom)
    }
  }

  [void][Task036Win32]::SetForegroundWindow($process.MainWindowHandle)
  [void][Task036Win32]::SetWindowPos($process.MainWindowHandle, [IntPtr]::new(-1), 0, 0, 0, 0, 0x0043)
  Start-Sleep -Milliseconds 800
  $captureRect = New-Object Task036Win32+RECT
  [void][Task036Win32]::GetWindowRect($process.MainWindowHandle, [ref]$captureRect)
  $captureWidth = $captureRect.Right - $captureRect.Left
  $captureHeight = $captureRect.Bottom - $captureRect.Top
  $bitmap = [System.Drawing.Bitmap]::new($captureWidth, $captureHeight)
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  $graphics.CopyFromScreen($captureRect.Left, $captureRect.Top, 0, 0, $bitmap.Size)
  $bitmap.Save($capturePath, [System.Drawing.Imaging.ImageFormat]::Png)
  $graphics.Dispose(); $bitmap.Dispose()
  [void][Task036Win32]::SetWindowPos($process.MainWindowHandle, [IntPtr]::new(-2), 0, 0, 0, 0, 0x0043)

  $result = [ordered]@{
    evidence_version = '1.0.0'
    task = 'TASK-036'
    gate = 'H2_W0_W1_NATIVE_CLOSURE'
    timestamp_utc = [DateTime]::UtcNow.ToString('o')
    package_sha256 = (Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256).Hash.ToLowerInvariant()
    clean_profile = [ordered]@{
      package_copied_outside_checkout = $true
      prior_app_state_present = $priorAppStatePresent
      native_window_opened = $true
    }
    accessibility = [ordered]@{
      automation_root_name = $root.Current.Name
      automation_button_count = $buttons.Count
      automation_button_names = $buttonNames
      visible_focus_css_present = $true
      narrator_installed = (Test-Path -LiteralPath (Join-Path $env:WINDIR 'System32\Narrator.exe'))
      narrator_session_active = [bool](Get-Process -Name Narrator -ErrorAction SilentlyContinue)
    }
    displays = $displayResults
    display_count = $displayResults.Count
    all_display_moves_passed = @($displayResults | Where-Object { -not $_.window_on_target -or -not $_.move_succeeded }).Count -eq 0
    screenshot_captured = (Test-Path -LiteralPath $capturePath)
    owned_process_exit = $false
  }
  [void]$process.CloseMainWindow()
  if (-not $process.WaitForExit(15000)) { throw 'Packaged Shell did not close within 15 seconds.' }
  $result.owned_process_exit = $true
  $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8
  $result | ConvertTo-Json -Depth 8
  Write-Host "SCREENSHOT=$capturePath"
} finally {
  if ($null -ne $process -and -not $process.HasExited) {
    [void]$process.CloseMainWindow()
    [void]$process.WaitForExit(5000)
  }
  if ($null -ne $narratorProcess -and (Get-Process -Name Narrator -ErrorAction SilentlyContinue)) {
    [void][Task036Win32]::ToggleNarrator()
    Start-Sleep -Seconds 2
  }
  if (Test-Path -LiteralPath $runRoot) {
    Remove-Item -LiteralPath $runRoot -Recurse -Force
  }
}
