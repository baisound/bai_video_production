[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BuildPython,
    [Parameter(Mandatory = $true)][string]$PythonInstaller,
    [Parameter(Mandatory = $true)][string]$IsccPath,
    [Parameter(Mandatory = $true)][string]$WorkRoot,
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [string]$Version = '0.24.2',
    [string]$ExpectedPythonInstallerSha256 = '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb',
    [string]$ExpectedIsccSha256 = 'd06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Resolve-RequiredFile([string]$Path, [string]$Label) {
    if (-not [IO.Path]::IsPathRooted($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label must be an existing absolute file: $Path"
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$python = Resolve-RequiredFile $BuildPython 'BuildPython'
$pythonInstallerFile = Resolve-RequiredFile $PythonInstaller 'PythonInstaller'
$iscc = Resolve-RequiredFile $IsccPath 'IsccPath'
foreach ($path in @($WorkRoot, $OutputDirectory)) {
    if (-not [IO.Path]::IsPathRooted($path)) { throw "Build output must be absolute: $path" }
    $full = [IO.Path]::GetFullPath($path)
    if (-not $full.StartsWith($repoRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Build output must stay inside this worktree: $full"
    }
    if (Test-Path -LiteralPath $full) { throw "Build output must not already exist: $full" }
}
$pythonInstallerSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $pythonInstallerFile).Hash.ToLowerInvariant()
if ($pythonInstallerSha -ne $ExpectedPythonInstallerSha256.ToLowerInvariant()) { throw 'Python installer checksum mismatch.' }
$pythonSignature = Get-AuthenticodeSignature -LiteralPath $pythonInstallerFile
if ($pythonSignature.Status -ne 'Valid' -or $pythonSignature.SignerCertificate.Subject -notlike '*Python Software Foundation*') {
    throw 'Python installer signature is invalid.'
}
$isccSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $iscc).Hash.ToLowerInvariant()
if ($isccSha -ne $ExpectedIsccSha256.ToLowerInvariant()) { throw 'Inno Setup compiler checksum mismatch.' }

$work = [IO.Path]::GetFullPath($WorkRoot)
$output = [IO.Path]::GetFullPath($OutputDirectory)
$payload = Join-Path $work 'payload'
$bootstrap = Join-Path $payload 'bootstrap'
$tools = Join-Path $payload 'tools'
$docs = Join-Path $payload 'docs'
$wheelOutput = Join-Path $work 'wheel'
New-Item -ItemType Directory -Path $bootstrap, $tools, $docs, $wheelOutput, $output | Out-Null

& $python -m pip wheel --disable-pip-version-check --no-cache-dir --no-build-isolation --no-deps --wheel-dir $wheelOutput $repoRoot
if ($LASTEXITCODE -ne 0) { throw "Wheel build failed: $LASTEXITCODE" }
$wheel = @(Get-ChildItem -LiteralPath $wheelOutput -Filter 'ai_video_production-0.24.2-*.whl' -File)
if ($wheel.Count -ne 1) { throw "Expected one 0.24.2 wheel, found $($wheel.Count)." }
Copy-Item -LiteralPath $pythonInstallerFile -Destination (Join-Path $bootstrap 'python-3.12.10-amd64.exe')
Copy-Item -LiteralPath $wheel[0].FullName -Destination $bootstrap
Copy-Item -LiteralPath (Join-Path $repoRoot 'tools\windows\install-owner-voice-runtime.ps1') -Destination $tools
Copy-Item -LiteralPath (Join-Path $repoRoot 'tools\windows\make-owner-voice-wav.ps1') -Destination $tools
Copy-Item -LiteralPath (Join-Path $repoRoot 'docs\user\SRT-OWNER-VOICE-WAV.md') -Destination $docs
Copy-Item -LiteralPath (Join-Path $repoRoot 'docs\windows\BUILDING-OWNER-VOICE-RUNTIME-INSTALLER.md') -Destination $docs
Copy-Item -LiteralPath (Join-Path $repoRoot 'LICENSE.md') -Destination $payload

$payloadWheel = Join-Path $bootstrap $wheel[0].Name
$manifest = [ordered]@{
    schema_version = 1
    task = 'TASK-093'
    product_version = $Version
    python_version = '3.12.10'
    python_installer = [ordered]@{ file = 'python-3.12.10-amd64.exe'; sha256 = $pythonInstallerSha; authenticode = 'Valid'; signer = $pythonSignature.SignerCertificate.Subject }
    application_wheel = [ordered]@{ file = $wheel[0].Name; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $payloadWheel).Hash.ToLowerInvariant() }
    torch = '2.11.0+cu130'
    torchaudio = '2.11.0+cu130'
    qwen_tts = '0.1.1'
    imageio_ffmpeg = '0.6.0'
    model_repo_id = 'Qwen/Qwen3-TTS-12Hz-0.6B-Base'
    model_revision = '5d83992436eae1d760afd27aff78a71d676296fc'
    model_files = [ordered]@{
        'config.json' = [ordered]@{ bytes = 4494; sha256 = '2e714c787c8edb98b05432685cddb634add2de4d4e645f653d68251ef72ba011' }
        'model.safetensors' = [ordered]@{ bytes = 1829344272; sha256 = '180b3b10eb1c9f1b4db7806d5475bae3071c0243c299d49926bab1da3b6946f6' }
        'speech_tokenizer/model.safetensors' = [ordered]@{ bytes = 682293092; sha256 = '836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258' }
    }
    training_included = $false
    zero_shot_owner_voice_included = $true
}
$manifestPath = Join-Path $payload 'runtime-manifest.json'
[IO.File]::WriteAllText($manifestPath, (($manifest | ConvertTo-Json -Depth 12) + "`n"), [Text.UTF8Encoding]::new($false))

$iss = Join-Path $repoRoot 'packaging\task093_owner_voice_runtime_installer.iss'
& $iscc "/DAppVersion=$Version" "/DPayloadRoot=$payload" "/O$output" $iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed: $LASTEXITCODE" }
$installer = Join-Path $output "bai-owner-voice-runtime-$Version-windows-x64-setup.exe"
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw "Installer missing: $installer" }
[pscustomobject]@{
    task = 'TASK-093'
    version = $Version
    installer = $installer
    installer_bytes = (Get-Item -LiteralPath $installer).Length
    installer_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash.ToLowerInvariant()
    python_installer_sha256 = $pythonInstallerSha
    application_wheel_sha256 = $manifest.application_wheel.sha256
    model_revision = $manifest.model_revision
    external_download_performed = $false
} | ConvertTo-Json -Depth 6
