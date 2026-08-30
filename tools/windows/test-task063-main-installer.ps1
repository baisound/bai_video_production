param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath,
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot
)

$ErrorActionPreference = "Stop"
$installer = (Resolve-Path -LiteralPath $InstallerPath).Path
$root = [IO.Path]::GetFullPath($InstallRoot)
$expectedPrefix = [IO.Path]::GetFullPath("D:\BAI\BAI VIDEO PRODUCTION FOR DRFX\test-install")
if (-not $root.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Acceptance install root escaped the bounded test-install directory"
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $root) | Out-Null

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
