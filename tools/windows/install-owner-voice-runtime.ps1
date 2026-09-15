<#
.SYNOPSIS
Provisions the installer-managed Owner Voice Python/Qwen runtime.

.DESCRIPTION
This script is invoked by the installer payload. It installs a private
Python 3.12 runtime, pinned CUDA PyTorch and Qwen-TTS packages, acquires or
reuses the exact Qwen3-TTS 0.6B Base revision, performs a GPU/model load-only
probe, and atomically publishes runtime-config.json only after every check passes.
It never reads an Owner recording and never starts generation or training.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$DataRoot,
    [Parameter(Mandatory = $true)][string]$InstallRoot,
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [string]$ConfigRoot = (Join-Path $env:LOCALAPPDATA 'BAI Video Production\owner-voice'),
    [string]$ExistingModelRoot = '',
    [switch]$SkipModelLoad,
    [switch]$PlanOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$script:BootstrapErrorPath = $null

trap {
    if ($null -ne $script:BootstrapErrorPath) {
        try {
            $detail = [ordered]@{
                timestamp_utc = [DateTime]::UtcNow.ToString('o')
                result = 'FAIL'
                error = $_.Exception.ToString()
            } | ConvertTo-Json -Depth 6
            [IO.File]::WriteAllText($script:BootstrapErrorPath, ($detail + "`n"), [Text.UTF8Encoding]::new($false))
        } catch {
            # Preserve the original provisioning failure even if diagnostics cannot be written.
        }
    }
    exit 1
}

# Inno Setup can launch Windows PowerShell with a reduced module search path.
# Import the two built-in modules from this exact PowerShell installation so
# checksum and Authenticode verification never depend on inherited PSModulePath.
Import-Module -Name (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -ErrorAction Stop
Import-Module -Name (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1') -ErrorAction Stop

function Resolve-SafeRoot([string]$Path, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not [IO.Path]::IsPathRooted($Path)) {
        throw "$Label must be an absolute local path."
    }
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    if ($full.StartsWith('\\')) { throw "$Label cannot be a network path: $full" }
    $volume = [IO.Path]::GetPathRoot($full).TrimEnd('\')
    $parent = Split-Path -Parent $full
    if ($full -eq $volume -or [string]::IsNullOrWhiteSpace($parent) -or $parent.TrimEnd('\') -eq $volume) {
        throw "$Label cannot be a drive root or direct child of a drive root: $full"
    }
    $current = $full
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (-not $item.PSIsContainer) { throw "$Label collides with a file: $current" }
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "$Label contains a reparse point: $current"
            }
        }
        $next = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($next) -or $next -eq $current) { break }
        $current = $next
    }
    return $full
}

function Invoke-Checked([string]$FilePath, [string[]]$Arguments, [string]$Label) {
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE" }
}

function Write-JsonAtomic([string]$Path, [object]$Value) {
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    $temporary = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
    [IO.File]::WriteAllText($temporary, (($Value | ConvertTo-Json -Depth 12) + "`n"), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

$safeDataRoot = Resolve-SafeRoot $DataRoot 'DataRoot'
$safeInstallRoot = Resolve-SafeRoot $InstallRoot 'InstallRoot'
$safeConfigRoot = Resolve-SafeRoot $ConfigRoot 'ConfigRoot'
$script:BootstrapErrorPath = Join-Path $safeConfigRoot 'bootstrap-last-error.json'
if (-not (Test-Path -LiteralPath $safeConfigRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $safeConfigRoot | Out-Null
}
Remove-Item -LiteralPath $script:BootstrapErrorPath -Force -ErrorAction SilentlyContinue
$manifestFile = (Resolve-Path -LiteralPath $ManifestPath).Path
$manifest = Get-Content -Raw -LiteralPath $manifestFile | ConvertFrom-Json
if ($manifest.schema_version -ne 1 -or $manifest.task -ne 'TASK-093' -or $manifest.product_version -ne '0.24.2') {
    throw 'Unsupported Owner Voice runtime manifest.'
}

$pythonRoot = Join-Path $safeDataRoot 'runtime\owner-voice-py312'
$python = Join-Path $pythonRoot 'Scripts\python.exe'
$modelRoot = Join-Path $safeDataRoot "models\Qwen3-TTS-12Hz-0.6B-Base\$($manifest.model_revision)"
$receiptsRoot = Join-Path $safeDataRoot 'receipts\owner-voice-0.24.2'
$jobsRoot = Join-Path $safeDataRoot 'jobs'
$datasetRoot = Join-Path $safeDataRoot 'voice-dataset'
$pythonInstaller = Join-Path $safeInstallRoot "bootstrap\$($manifest.python_installer.file)"
$wheel = Join-Path $safeInstallRoot "bootstrap\$($manifest.application_wheel.file)"
$configPath = Join-Path $safeConfigRoot 'runtime-config.json'
$stableCommandPath = Join-Path $safeConfigRoot 'make-owner-voice-wav.ps1'
$markerPath = Join-Path $safeDataRoot '.bvp-owner-voice-root.json'

$plan = [ordered]@{
    schema_version = 1
    task = 'TASK-093'
    data_root = $safeDataRoot
    install_root = $safeInstallRoot
    config_path = $configPath
    python = $python
    model_root = $modelRoot
    receipts_root = $receiptsRoot
    jobs_root = $jobsRoot
    model_revision = [string]$manifest.model_revision
    model_download_may_be_required = $true
    owner_audio_read = $false
    generation_started = $false
    training_started = $false
}
if ($PlanOnly) {
    $plan | ConvertTo-Json -Depth 8
    exit 0
}

foreach ($input in @(
    @{ Path = $pythonInstaller; Hash = [string]$manifest.python_installer.sha256; Label = 'Python installer' },
    @{ Path = $wheel; Hash = [string]$manifest.application_wheel.sha256; Label = 'BAI Video Production wheel' }
)) {
    if (-not (Test-Path -LiteralPath $input.Path -PathType Leaf)) { throw "$($input.Label) is missing: $($input.Path)" }
    $observed = (Get-FileHash -Algorithm SHA256 -LiteralPath $input.Path).Hash.ToLowerInvariant()
    if ($observed -ne $input.Hash.ToLowerInvariant()) { throw "$($input.Label) checksum mismatch." }
}
$signature = Get-AuthenticodeSignature -LiteralPath $pythonInstaller
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*Python Software Foundation*') {
    throw 'Bundled Python installer signature is invalid.'
}

if (Test-Path -LiteralPath $safeDataRoot -PathType Container) {
    $entries = @(Get-ChildItem -LiteralPath $safeDataRoot -Force)
    if ($entries.Count -gt 0 -and -not (Test-Path -LiteralPath $markerPath -PathType Leaf)) {
        throw "DataRoot is not an existing BAI Owner Voice root: $safeDataRoot"
    }
    if (Test-Path -LiteralPath $markerPath -PathType Leaf) {
        try {
            $existingMarker = Get-Content -Raw -LiteralPath $markerPath | ConvertFrom-Json
        } catch {
            throw "DataRoot ownership marker is invalid: $markerPath"
        }
        if ($existingMarker.schema_version -ne 1 -or
            $existingMarker.owner -ne 'BAI Owner Voice Runtime' -or
            [IO.Path]::GetFullPath([string]$existingMarker.data_root).TrimEnd('\') -ne $safeDataRoot) {
            throw "DataRoot ownership marker does not match the selected root: $safeDataRoot"
        }
    }
}
New-Item -ItemType Directory -Force -Path $safeDataRoot, $safeConfigRoot, $receiptsRoot, $jobsRoot, $datasetRoot | Out-Null
Write-JsonAtomic $markerPath ([ordered]@{
    schema_version = 1
    owner = 'BAI Owner Voice Runtime'
    data_root = $safeDataRoot
    preserve_on_uninstall = $true
})

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $basePython = $null
    $knownPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    if (Test-Path -LiteralPath $knownPython -PathType Leaf) {
        $basePython = $knownPython
    } elseif (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $candidate = (& py.exe -3.12 -c 'import sys; print(sys.executable)' 2>$null).Trim()
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { $basePython = $candidate }
    }
    if ($null -eq $basePython) {
        $arguments = @(
            '/quiet', 'InstallAllUsers=0', 'Include_launcher=0', 'Include_test=0',
            'Include_doc=0', 'Include_pip=1', 'PrependPath=0', 'Shortcuts=0'
        )
        $process = Start-Process -FilePath $pythonInstaller -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
        if ($process.ExitCode -ne 0) { throw "Python installation failed with exit code $($process.ExitCode)" }
        if (Test-Path -LiteralPath $knownPython -PathType Leaf) { $basePython = $knownPython }
    }
    if ($null -eq $basePython) { throw 'Python 3.12 base runtime was not created.' }
    $baseVersion = (& $basePython -c 'import sys; print(sys.version_info.major, sys.version_info.minor, sys.version_info.micro, sep=chr(46))').Trim()
    if ($LASTEXITCODE -ne 0 -or -not $baseVersion.StartsWith('3.12.')) { throw "Unexpected base Python runtime: $baseVersion" }
    Invoke-Checked $basePython @('-m','venv',$pythonRoot) 'Private Python environment creation'
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Private Python environment was not created.' }
$pythonVersion = (& $python -c 'import sys; print(sys.version_info.major, sys.version_info.minor, sys.version_info.micro, sep=chr(46))').Trim()
if ($LASTEXITCODE -ne 0 -or -not $pythonVersion.StartsWith('3.12.')) { throw "Unexpected Python runtime: $pythonVersion" }

Invoke-Checked $python @('-m','pip','install','--disable-pip-version-check','pip==25.2','setuptools==80.9.0','wheel==0.45.1') 'Python packaging tools installation'
Invoke-Checked $python @('-m','pip','install','--disable-pip-version-check','torch==2.11.0','torchaudio==2.11.0','--index-url','https://download.pytorch.org/whl/cu130') 'CUDA PyTorch installation'
Invoke-Checked $python @('-m','pip','install','--disable-pip-version-check','qwen-tts==0.1.1','imageio-ffmpeg==0.6.0') 'Owner Voice dependencies installation'
Invoke-Checked $python @('-m','pip','install','--disable-pip-version-check','--force-reinstall','--no-deps',$wheel) 'BAI Video Production wheel installation'
Invoke-Checked $python @('-m','pip','check') 'Python dependency verification'

$freezePath = Join-Path $receiptsRoot 'pip-freeze.txt'
$freeze = & $python -m pip freeze --all
if ($LASTEXITCODE -ne 0) { throw 'pip freeze failed.' }
[IO.File]::WriteAllLines($freezePath, @($freeze), [Text.UTF8Encoding]::new($false))
$ffmpeg = (& $python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())').Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $ffmpeg -PathType Leaf)) { throw 'Private ffmpeg was not found.' }

$candidateRoots = @()
if (-not [string]::IsNullOrWhiteSpace($ExistingModelRoot)) { $candidateRoots += $ExistingModelRoot }
$candidateRoots += 'E:\BAI_AI\models\Qwen3-TTS-12Hz-0.6B-Base\5d83992436eae1d760afd27aff78a71d676296fc'
$selectedModel = $null
foreach ($candidate in $candidateRoots) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Container)) { continue }
    & $python -m ai_video_production.owner_voice_runtime model --model-root $candidate --report (Join-Path $receiptsRoot 'candidate-model-check.json') | Out-Host
    if ($LASTEXITCODE -eq 0) { $selectedModel = (Resolve-Path -LiteralPath $candidate).Path; break }
}
if ($null -eq $selectedModel) {
    & $python -m ai_video_production.owner_voice_runtime model --model-root $modelRoot --report (Join-Path $receiptsRoot 'model-download-check.json') | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Invoke-Checked $python @('-m','ai_video_production.owner_voice_runtime','model','--model-root',$modelRoot,'--download','--report',(Join-Path $receiptsRoot 'model-download-check.json')) 'Exact Qwen model download'
    }
    $selectedModel = $modelRoot
}

$runtimeReport = Join-Path $receiptsRoot 'runtime-verification.json'
$runtimeArguments = @('-m','ai_video_production.owner_voice_runtime','runtime','--model-root',$selectedModel,'--ffmpeg',$ffmpeg,'--report',$runtimeReport)
if ($SkipModelLoad) { $runtimeArguments += '--skip-model-load' }
Invoke-Checked $python $runtimeArguments 'Owner Voice runtime verification'
$runtimeResult = Get-Content -Raw -LiteralPath $runtimeReport | ConvertFrom-Json
if ($runtimeResult.result -ne 'PASS') { throw 'Owner Voice runtime did not pass verification.' }

$installedCommand = Join-Path $safeInstallRoot 'tools\make-owner-voice-wav.ps1'
if (-not (Test-Path -LiteralPath $installedCommand -PathType Leaf)) {
    throw "Owner Voice command is missing: $installedCommand"
}
Copy-Item -LiteralPath $installedCommand -Destination $stableCommandPath -Force

$config = [ordered]@{
    schema_version = 1
    status = 'READY'
    product_version = '0.24.2'
    data_root = $safeDataRoot
    python = $python
    model_root = $selectedModel
    model_revision = [string]$manifest.model_revision
    ffmpeg = $ffmpeg
    jobs_root = $jobsRoot
    dataset_root = $datasetRoot
    receipts_root = $receiptsRoot
    runtime_report = $runtimeReport
    command_path = $stableCommandPath
    preserve_data_on_uninstall = $true
    training_available = $false
    zero_shot_owner_voice_available = $true
}
Write-JsonAtomic $configPath $config
$readBack = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
if ($readBack.status -ne 'READY' -or $readBack.model_revision -ne $manifest.model_revision -or -not (Test-Path -LiteralPath $readBack.python -PathType Leaf)) {
    throw 'Runtime configuration read-back failed.'
}
Remove-Item -LiteralPath $script:BootstrapErrorPath -Force -ErrorAction SilentlyContinue
$config | ConvertTo-Json -Depth 8
