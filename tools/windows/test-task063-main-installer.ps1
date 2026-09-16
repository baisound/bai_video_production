param(
    [string]$InstallerPath = "",
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot,
    [switch]$ValidateRootOnly
)

$ErrorActionPreference = "Stop"

function ConvertTo-NormalizedAbsolutePath {
    param([Parameter(Mandatory = $true)][string]$PathValue)
    if ([string]::IsNullOrWhiteSpace($PathValue) -or
        -not [IO.Path]::IsPathRooted($PathValue) -or
        $PathValue -match '^[A-Za-z]:[^\\/]') {
        throw "Acceptance install root must be an absolute path"
    }
    $full = [IO.Path]::GetFullPath($PathValue)
    $volumeRoot = [IO.Path]::GetPathRoot($full)
    if ($full.Length -gt $volumeRoot.Length) {
        $full = $full.TrimEnd([char[]]@('\', '/'))
    }
    return $full
}

function Test-IsBoundedInstallRoot {
    param(
        [Parameter(Mandatory = $true)][string]$Candidate,
        [Parameter(Mandatory = $true)][string]$ExpectedRoot
    )
    if ($Candidate.Equals($ExpectedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }
    $prefix = $ExpectedRoot + [IO.Path]::DirectorySeparatorChar
    return $Candidate.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)
}

function Get-SafeAncestorSnapshot {
    param([Parameter(Mandatory = $true)][string]$PathValue)
    $observations = [Collections.Generic.List[string]]::new()
    $current = ConvertTo-NormalizedAbsolutePath $PathValue
    while ($true) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -Force -LiteralPath $current
            if (-not $item.PSIsContainer) {
                throw "Acceptance install ancestor must be a directory"
            }
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
                -not [string]::IsNullOrEmpty([string]$item.LinkType)) {
                throw "Acceptance install ancestor must not be a reparse point"
            }
            $observations.Add(
                $item.FullName.ToLowerInvariant() + "|" +
                [string]$item.CreationTimeUtc.Ticks + "|" +
                [string][int64]$item.Attributes
            )
        }
        $parent = [IO.Path]::GetDirectoryName($current)
        if ([string]::IsNullOrEmpty($parent) -or
            $parent.Equals($current, [StringComparison]::OrdinalIgnoreCase)) {
            break
        }
        $current = $parent
    }
    return ($observations -join "`n")
}

$root = ConvertTo-NormalizedAbsolutePath $InstallRoot
$expectedRoot = ConvertTo-NormalizedAbsolutePath "D:\BAI\BAI VIDEO PRODUCTION FOR DRFX\test-install"
if (-not (Test-IsBoundedInstallRoot -Candidate $root -ExpectedRoot $expectedRoot)) {
    throw "Acceptance install root escaped the bounded test-install directory"
}
Get-SafeAncestorSnapshot $root | Out-Null
if ($ValidateRootOnly) {
    [pscustomobject]@{
        result = "BOUNDED_ROOT_VALID"
        effect = "NONE"
    } | ConvertTo-Json -Compress
    return
}
if ([string]::IsNullOrWhiteSpace($InstallerPath)) {
    throw "InstallerPath is required for installer acceptance"
}
$installer = (Resolve-Path -LiteralPath $InstallerPath).Path
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $root) | Out-Null
$ancestorSnapshot = Get-SafeAncestorSnapshot $root
if ((Get-SafeAncestorSnapshot $root) -ne $ancestorSnapshot) {
    throw "Acceptance install ancestor identity changed before launch"
}

$logPath = Join-Path (Split-Path -Parent $root) "task063-installer-acceptance.log"
$process = Start-Process -FilePath $installer -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
    "/DIR=`"$root`"", "/LOG=`"$logPath`""
) -Wait -PassThru -WindowStyle Hidden
if ($process.ExitCode -ne 0) { throw "Installer failed: $($process.ExitCode)" }

$mainExecutable = Join-Path $root "BAI Video Production.exe"
if (-not (Test-Path -LiteralPath $mainExecutable -PathType Leaf)) {
    throw "Installed main executable is missing"
}
$bridgeReadback = Join-Path $root "data\montage-learning-bridge\migration\installer-readback.json"
if (Test-Path -LiteralPath $bridgeReadback) {
    throw "TASK-063 private bridge composition was not invoked"
}

[pscustomobject]@{
    result = "PASS"
    install_root = $root
    main_executable = $mainExecutable
    bridge_invoked = $false
} | ConvertTo-Json
