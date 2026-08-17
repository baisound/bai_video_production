param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath,
    [Parameter(Mandatory = $true)]
    [string]$PayloadDirectory,
    [Parameter(Mandatory = $true)]
    [string]$AcceptanceRoot
)

$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $AcceptanceRoot) { throw "AcceptanceRoot must not already exist: $AcceptanceRoot" }
$installRoot = Join-Path $AcceptanceRoot 'installed'
$userDataRoot = Join-Path $AcceptanceRoot 'user-data-must-survive-uninstall'
New-Item -ItemType Directory -Path $AcceptanceRoot, $userDataRoot -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $userDataRoot 'owner-data-sentinel.txt'), 'DO_NOT_DELETE', [Text.UTF8Encoding]::new($false))

function Invoke-Installer([string[]]$Arguments, [string]$Label, [bool]$ExpectSuccess) {
    $process = Start-Process -FilePath $InstallerPath -ArgumentList $Arguments -Wait -PassThru
    if ($ExpectSuccess -and $process.ExitCode -ne 0) { throw "$Label failed with exit code $($process.ExitCode)" }
    if ((-not $ExpectSuccess) -and $process.ExitCode -eq 0) { throw "$Label unexpectedly succeeded" }
}

$silentArgs = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "/DIR=$installRoot")
Invoke-Installer $silentArgs 'clean install' $true

$manifest = Get-Content -Raw -LiteralPath (Join-Path $PayloadDirectory 'package-manifest.json') | ConvertFrom-Json
foreach ($item in $manifest.payload) {
    $relative = switch ($item.path) {
        'application/bai-voice-model-builder.exe' { 'bai-voice-model-builder.exe' }
        'docs/VOICE-MODEL-BUILDER.md' { 'docs\VOICE-MODEL-BUILDER.md' }
        'LICENSE.md' { 'LICENSE.md' }
        'THIRD-PARTY-NOTICES.txt' { 'THIRD-PARTY-NOTICES.txt' }
        default { throw "Unexpected manifest path: $($item.path)" }
    }
    $installed = Join-Path $installRoot $relative
    if (-not (Test-Path -LiteralPath $installed -PathType Leaf)) { throw "Missing installed file: $relative" }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $installed).Hash.ToLowerInvariant()
    if ($actual -ne $item.sha256) { throw "Installed hash mismatch: $relative" }
}
$selfCheck = Start-Process -FilePath (Join-Path $installRoot 'bai-voice-model-builder.exe') -ArgumentList @('--self-check', '--locale', 'ja') -PassThru
if (-not $selfCheck.WaitForExit(30000)) {
    $selfCheck.Kill()
    throw 'Contained self-check exceeded the 30-second bound'
}
if ($selfCheck.ExitCode -ne 0) { throw "Contained self-check failed: $($selfCheck.ExitCode)" }

Invoke-Installer $silentArgs 'exact repair' $true
$target = Join-Path $installRoot 'bai-voice-model-builder.exe'
$original = [IO.File]::ReadAllBytes($target)
[IO.File]::WriteAllBytes($target, [byte[]]@(0x42, 0x41, 0x49))
Invoke-Installer $silentArgs 'collision install' $false
[IO.File]::WriteAllBytes($target, $original)

$uninstaller = Join-Path $installRoot 'unins000.exe'
if (-not (Test-Path -LiteralPath $uninstaller -PathType Leaf)) { throw 'Uninstaller was not created' }
$uninstall = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru
if ($uninstall.ExitCode -ne 0) { throw "Uninstall failed: $($uninstall.ExitCode)" }
if (Test-Path -LiteralPath (Join-Path $installRoot 'bai-voice-model-builder.exe')) { throw 'Application remained after uninstall' }
if ((Get-Content -Raw -LiteralPath (Join-Path $userDataRoot 'owner-data-sentinel.txt')) -ne 'DO_NOT_DELETE') {
    throw 'User data sentinel was changed or removed'
}

[ordered]@{
    schema_version = 1
    task = 'TASK-046/P-VS-4B-BEGINNER-CLIENT-RELEASE-R2'
    clean_install = 'PASS'
    exact_repair = 'PASS'
    collision_fail_closed = 'PASS'
    contained_self_check = 'PASS'
    uninstall = 'PASS'
    user_data_preserved = 'PASS'
    third_party_notices = 'PASS'
    model_download_started = $false
    training_started = $false
    audio_access_started = $false
    recording_started = $false
} | ConvertTo-Json -Depth 4
