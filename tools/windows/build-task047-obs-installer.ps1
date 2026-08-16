param(
    [Parameter(Mandatory = $true)]
    [string]$RuntimeZip,
    [Parameter(Mandatory = $true)]
    [string]$InnoCompiler,
    [Parameter(Mandatory = $true)]
    [string]$WorkRoot,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [string]$ExpectedRuntimeSha256 = '4e8fcdf6f697da059ef3aa9ae703a400d0f85e9ed89d77ace9f624dc2783e20f',
    [string]$ExpectedCompilerSha256 = 'd06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a'
)

$ErrorActionPreference = 'Stop'

function Assert-AbsoluteFile([string]$Path, [string]$Label) {
    if (-not [IO.Path]::IsPathRooted($Path)) { throw "$Label must be an absolute path: $Path" }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "$Label was not found: $Path" }
}

Assert-AbsoluteFile $RuntimeZip 'RuntimeZip'
Assert-AbsoluteFile $InnoCompiler 'InnoCompiler'
if (-not [IO.Path]::IsPathRooted($WorkRoot)) { throw "WorkRoot must be absolute: $WorkRoot" }
if (-not [IO.Path]::IsPathRooted($OutputDirectory)) { throw "OutputDirectory must be absolute: $OutputDirectory" }
if (Test-Path -LiteralPath $WorkRoot) { throw "WorkRoot must not already exist: $WorkRoot" }
if (Test-Path -LiteralPath $OutputDirectory) { throw "OutputDirectory must not already exist: $OutputDirectory" }

$runtimeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $RuntimeZip).Hash.ToLowerInvariant()
if ($runtimeHash -ne $ExpectedRuntimeSha256.ToLowerInvariant()) {
    throw "Runtime ZIP hash mismatch: $runtimeHash"
}
$compilerHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $InnoCompiler).Hash.ToLowerInvariant()
if ($compilerHash -ne $ExpectedCompilerSha256.ToLowerInvariant()) {
    throw "ISCC hash mismatch: $compilerHash"
}

$payloadRoot = Join-Path $WorkRoot 'payload'
New-Item -ItemType Directory -Path $payloadRoot, $OutputDirectory -Force | Out-Null
Expand-Archive -LiteralPath $RuntimeZip -DestinationPath $payloadRoot

$requiredPayload = [ordered]@{
    'controller\bai-voice-capture-controller.exe' = '273fe96a952b1120b422785ee4c70a9612ba6f44c6d95f06447497abb52afb3f'
    'obs-plugins\64bit\bai-voice-capture.dll' = '14839bcad60fe47583a97729e3dc41c23b9f6c06012d5a83a38d8fc04b435b38'
    'data\obs-plugins\bai-voice-capture\locale\en-US.ini' = '066718cb394b9af07319f4bb4a0f6eb7cc50e45e73ffc76662c588ccbaa8ae8d'
    'data\obs-plugins\bai-voice-capture\locale\ja-JP.ini' = 'c55315f3973893bfe9303766df7ab824751e93a84a0a607224a3b465fbf63f4e'
}
foreach ($entry in $requiredPayload.GetEnumerator()) {
    $payloadPath = Join-Path $payloadRoot $entry.Key
    Assert-AbsoluteFile $payloadPath "Payload $($entry.Key)"
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $payloadPath).Hash.ToLowerInvariant()
    if ($actual -ne $entry.Value) { throw "Payload hash mismatch: $($entry.Key) $actual" }
}

$scriptPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\packaging\task047_obs_voice_capture_installer.iss'))
Assert-AbsoluteFile $scriptPath 'Installer script'
$compileOutput = & $InnoCompiler "/DPayloadRoot=$payloadRoot" "/O$OutputDirectory" $scriptPath 2>&1
if ($LASTEXITCODE -ne 0) {
    $compileOutput | ForEach-Object { Write-Error $_ }
    throw "ISCC failed with exit code $LASTEXITCODE"
}

$installerPath = Join-Path $OutputDirectory 'bai-voice-capture-0.1.0-dev.8-installer.4-windows-x64-setup.exe'
Assert-AbsoluteFile $installerPath 'Compiled installer'
$installer = Get-Item -LiteralPath $installerPath
$result = [ordered]@{
    schema_version = 1
    task = 'TASK-047/P-OBS'
    runtime_zip_sha256 = $runtimeHash
    iscc_sha256 = $compilerHash
    installer_path = $installer.FullName
    installer_bytes = $installer.Length
    installer_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer.FullName).Hash.ToLowerInvariant()
    installer_authenticode = [string](Get-AuthenticodeSignature -LiteralPath $installer.FullName).Status
    external_download_performed = $false
    obs_mutated = $false
    recording_started = $false
}
$result | ConvertTo-Json -Depth 4
