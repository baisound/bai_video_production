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

$bridge = Join-Path $root "data\montage-learning-bridge"
$required = @(
    "bridge-instance.json",
    "bridge-owner.json",
    "learning-inbox",
    "learning-processing",
    "learning-quarantine",
    "learning-receipts",
    "preference",
    "preference\profiles",
    "state",
    "migration",
    "migration\installer-readback.json"
)
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $bridge $relative))) {
        throw "Installed bridge read-back missing: $relative"
    }
}
$descriptor = Get-Content -Raw -LiteralPath (Join-Path $bridge "bridge-instance.json") | ConvertFrom-Json
$receipt = Get-Content -Raw -LiteralPath (Join-Path $bridge "migration\installer-readback.json") | ConvertFrom-Json
if ($descriptor.bridge_relative_path -ne "data/montage-learning-bridge") {
    throw "Descriptor relative path mismatch"
}
if ($receipt.install_instance_id -ne $descriptor.install_instance_id) {
    throw "Discovery receipt instance mismatch"
}
if ($receipt.connector_enabled -ne $false -or $receipt.activation_authorized -ne $false) {
    throw "Installer illegally activated the production connector"
}

[pscustomobject]@{
    result = "PASS"
    install_root = $root
    bridge_root = $bridge
    install_instance_id = $descriptor.install_instance_id
    descriptor_sha256 = $descriptor.descriptor_sha256
    discovery_status = $receipt.status
    connector_enabled = $receipt.connector_enabled
} | ConvertTo-Json
