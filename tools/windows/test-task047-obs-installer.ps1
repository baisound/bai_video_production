param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath,
    [Parameter(Mandatory = $true)]
    [string]$ObsExe,
    [string]$PayloadDirectory = '',
    [string]$AcceptanceRoot = ''
)

$ErrorActionPreference = 'Stop'
$root = if ($AcceptanceRoot) { [IO.Path]::GetFullPath($AcceptanceRoot) } else { Join-Path ([IO.Path]::GetTempPath()) 'bai-task047-installer-acceptance' }
if ([IO.Path]::GetFileName($root) -ne 'bai-task047-installer-acceptance') {
    throw "AcceptanceRoot leaf must be bai-task047-installer-acceptance: $root"
}
$payloadRoot = if ($PayloadDirectory) { $PayloadDirectory } else { Join-Path $PSScriptRoot 'payload' }
$obsRoot = Join-Path $root 'fake-obs'
$appRoot = Join-Path $root 'app'
$logRoot = Join-Path $root 'logs'

function Get-FileSha256([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $digest = $hasher.ComputeHash($stream)
        return ([BitConverter]::ToString($digest) -replace '-', '').ToLowerInvariant()
    }
    finally {
        $hasher.Dispose()
        $stream.Dispose()
    }
}

if (Test-Path -LiteralPath $root) {
    Remove-Item -LiteralPath $root -Recurse -Force
}
New-Item -ItemType Directory -Path (Join-Path $obsRoot 'bin\64bit'), $appRoot, $logRoot -Force | Out-Null
Copy-Item -LiteralPath $ObsExe -Destination (Join-Path $obsRoot 'bin\64bit\obs64.exe')

$targets = @(
    @{ Path = Join-Path $obsRoot 'obs-plugins\64bit\bai-voice-capture.dll'; Source = Join-Path $payloadRoot 'obs-plugins\64bit\bai-voice-capture.dll'; Sha = '9b8a603d6515c0735f776867c7079c0600990ebebaf8b9609d81d0f0f265bcdb' },
    @{ Path = Join-Path $obsRoot 'data\obs-plugins\bai-voice-capture\locale\en-US.ini'; Source = Join-Path $payloadRoot 'data\obs-plugins\bai-voice-capture\locale\en-US.ini'; Sha = '066718cb394b9af07319f4bb4a0f6eb7cc50e45e73ffc76662c588ccbaa8ae8d' },
    @{ Path = Join-Path $obsRoot 'data\obs-plugins\bai-voice-capture\locale\ja-JP.ini'; Source = Join-Path $payloadRoot 'data\obs-plugins\bai-voice-capture\locale\ja-JP.ini'; Sha = 'c55315f3973893bfe9303766df7ab824751e93a84a0a607224a3b465fbf63f4e' }
)

function Invoke-Setup([string]$LogName) {
    $arguments = @(
        '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER',
        "/DIR=$appRoot", "/OBSROOT=$obsRoot", "/LOG=$(Join-Path $logRoot $LogName)"
    )
    $process = Start-Process -FilePath $InstallerPath -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "Installer failed: exit=$($process.ExitCode), log=$LogName"
    }
}

function Assert-Targets {
    foreach ($target in $targets) {
        if (-not (Test-Path -LiteralPath $target.Path)) { throw "Missing target: $($target.Path)" }
        $actual = Get-FileSha256 $target.Path
        if ($actual -ne $target.Sha) { throw "Hash mismatch: $($target.Path) $actual" }
    }
}

function Get-Sha256HexFromUtf8([string]$Value) {
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $digest = $hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value))
        return ([BitConverter]::ToString($digest) -replace '-', '').ToLowerInvariant()
    }
    finally {
        $hasher.Dispose()
    }
}

function Assert-Journal {
    $journalPath = Join-Path $appRoot 'install-journal-v2.jsonl'
    $lines = @(Get-Content -LiteralPath $journalPath)
    if ($lines.Count -ne 6) { throw "Expected six append-only journal entries after install+repair, got $($lines.Count)" }
    $previous = ''
    $sequence = 0
    foreach ($line in $lines) {
        $entry = $line | ConvertFrom-Json
        $sequence++
        $calculated = Get-Sha256HexFromUtf8 ([string]$entry.body)
        if ($calculated -ne $entry.entry_sha256) { throw "Journal hash mismatch at sequence $sequence" }
        if ($entry.body -notmatch "sequence=$sequence;") { throw "Journal sequence mismatch at $sequence" }
        if (-not $entry.body.EndsWith("prev_sha256=$previous")) { throw "Journal predecessor mismatch at $sequence" }
        $previous = $entry.entry_sha256
    }
}

Invoke-Setup 'clean-install.log'
Assert-Targets
Invoke-Setup 'repair.log'
Assert-Targets
Assert-Journal

$uninstaller = Join-Path $appRoot 'unins000.exe'
if (-not (Test-Path -LiteralPath $uninstaller)) { throw 'Uninstaller missing' }
$uninstall = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru -WindowStyle Hidden
if ($uninstall.ExitCode -ne 0) { throw "Uninstall failed: $($uninstall.ExitCode)" }
foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target.Path) { throw "Target remained after uninstall: $($target.Path)" }
}

$collisionTarget = $targets[0].Path
New-Item -ItemType Directory -Path (Split-Path -Parent $collisionTarget) -Force | Out-Null
[System.IO.File]::WriteAllText($collisionTarget, 'foreign-plugin')
$before = Get-FileSha256 $collisionTarget
$collisionLog = Join-Path $logRoot 'collision.log'
$collisionArgs = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', "/DIR=$appRoot", "/OBSROOT=$obsRoot", "/LOG=$collisionLog")
$collision = Start-Process -FilePath $InstallerPath -ArgumentList $collisionArgs -Wait -PassThru -WindowStyle Hidden
$after = Get-FileSha256 $collisionTarget
if ($collision.ExitCode -eq 0) { throw 'Collision install unexpectedly succeeded' }
if ($before -ne $after) { throw 'Collision target was modified' }

Remove-Item -LiteralPath $collisionTarget -Force
foreach ($target in $targets) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $target.Path) -Force | Out-Null
    Copy-Item -LiteralPath $target.Source -Destination $target.Path
}
Invoke-Setup 'adopt-existing-exact3.log'
Assert-Targets
$adoptUninstaller = Join-Path $appRoot 'unins000.exe'
$adoptUninstall = Start-Process -FilePath $adoptUninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru -WindowStyle Hidden
if ($adoptUninstall.ExitCode -ne 0) { throw "Adoption uninstall failed: $($adoptUninstall.ExitCode)" }
Assert-Targets

$receipt = [ordered]@{
    schema_version = 1
    installer_sha256 = Get-FileSha256 $InstallerPath
    clean_install = 'PASS'
    repair = 'PASS'
    uninstall = 'PASS'
    collision_refusal = 'PASS'
    collision_target_unchanged = 'PASS'
    existing_exact3_adoption = 'PASS'
    existing_exact3_restore_on_uninstall = 'PASS'
    append_only_journal_hash_chain = 'PASS'
    real_obs_mutated = $false
    owner_voice_recorded = $false
} | ConvertTo-Json -Depth 4
[IO.File]::WriteAllText(
    (Join-Path $root 'acceptance-receipt.json'),
    $receipt,
    (New-Object Text.UTF8Encoding($false))
)

Write-Output 'INSTALLER_ACCEPTANCE_PASS'
Get-Content -LiteralPath (Join-Path $root 'acceptance-receipt.json')
