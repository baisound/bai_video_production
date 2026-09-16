[CmdletBinding()]
param(
    [string]$OutputRoot = '',
    [string]$RunId = '',
    [string]$BuildPython = '',
    [string]$IsccPath = '',
    [string]$PythonInstaller = '',
    [string]$VoiceCaptureRuntimeZip = '',
    [switch]$AllowDirtySource,
    [switch]$PreflightOnly,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$script:ExpectedIsccSha256 = 'd06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a'
$script:ExpectedPythonInstallerSha256 = '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb'
$script:ExpectedVoiceCaptureRuntimeSha256 = '03286e9efbf5dd5af38230dcf7fee4bf53eb3fcc7d7a6d014833b9996bc1f558'
$script:ExpectedVoiceCaptureSourceSha256 = '0ad4c83a957b37b455b38829f842f8318116c522cb542de0a9c5849567b29e72'
$script:VoiceModelBuilderVersion = '0.1.0-dev.1-installer.2'
$script:VoiceCaptureVersion = '0.1.0-dev.10'

function Show-Usage {
    @'
Usage:
  .\tools\windows\build-all-windows-release.ps1

Optional overrides:
  -OutputRoot <absolute path inside this worktree>
  -RunId <new unique name>
  -BuildPython <python.exe>
  -IsccPath <ISCC.exe>
  -PythonInstaller <python-3.12.10-amd64.exe>
  -VoiceCaptureRuntimeZip <tracked runtime ZIP>
  -AllowDirtySource
  -PreflightOnly

Default prerequisite discovery:
  Python: BVP_BUILD_PYTHON, .venv\Scripts\python.exe, then python.exe on PATH
  ISCC: BVP_ISCC_PATH, Inno Setup 7 Program Files, then ISCC.exe on PATH
  Python installer: BVP_PYTHON_INSTALLER, then
    .build-prerequisites\windows\python-3.12.10-amd64.exe

The command only builds and packages local artifacts. It never installs a Product,
changes OBS, downloads a model/runtime, signs, tags, pushes, publishes, or deploys.
'@ | Write-Output
}

if ($Help) {
    Show-Usage
    exit 0
}

function Throw-OrchestratorError([string]$Message, [int]$ExitCode) {
    $exception = [InvalidOperationException]::new($Message)
    $exception.Data['ExitCode'] = $ExitCode
    throw $exception
}

function Get-AbsolutePath([string]$Path, [string]$Base) {
    if ([IO.Path]::IsPathRooted($Path)) {
        return [IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    }
    return [IO.Path]::GetFullPath((Join-Path $Base $Path)).TrimEnd('\', '/')
}

function Resolve-ExistingFile([string]$Candidate, [string]$Label) {
    if (-not $Candidate -or -not [IO.Path]::IsPathRooted($Candidate) -or
        -not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
        Throw-OrchestratorError "$Label must be an existing absolute file: $Candidate" 3
    }
    return (Resolve-Path -LiteralPath $Candidate).Path
}

function Resolve-BuildPython([string]$Requested, [string]$RepoRoot) {
    $candidates = @()
    if ($Requested) { $candidates += $Requested }
    elseif ($env:BVP_BUILD_PYTHON) { $candidates += $env:BVP_BUILD_PYTHON }
    else {
        $candidates += (Join-Path $RepoRoot '.venv\Scripts\python.exe')
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    Throw-OrchestratorError 'Build Python was not found. Configure BVP_BUILD_PYTHON or -BuildPython.' 3
}

function Resolve-Iscc([string]$Requested) {
    $candidates = @()
    if ($Requested) { $candidates += $Requested }
    elseif ($env:BVP_ISCC_PATH) { $candidates += $env:BVP_ISCC_PATH }
    else {
        $programFilesX86 = [Environment]::GetFolderPath('ProgramFilesX86')
        if ($programFilesX86) {
            $candidates += (Join-Path $programFilesX86 'Inno Setup 7\ISCC.exe')
        }
        $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    Throw-OrchestratorError 'Inno Setup 7 ISCC.exe was not found. Configure BVP_ISCC_PATH or -IsccPath.' 3
}

function Assert-ContainedOutputRoot([string]$Candidate, [string]$RepoRoot) {
    $full = Get-AbsolutePath $Candidate $RepoRoot
    $repo = [IO.Path]::GetFullPath($RepoRoot).TrimEnd('\', '/')
    $repoPrefix = $repo + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        Throw-OrchestratorError "OutputRoot must stay inside this exact worktree: $full" 2
    }
    $driveRoot = [IO.Path]::GetPathRoot($full).TrimEnd('\', '/')
    $parent = [IO.Path]::GetDirectoryName($full).TrimEnd('\', '/')
    if ($full -eq $driveRoot -or $parent -eq $driveRoot) {
        Throw-OrchestratorError "OutputRoot must not be a drive root or its direct child: $full" 2
    }
    if (Test-Path -LiteralPath $full -PathType Leaf) {
        Throw-OrchestratorError "OutputRoot resolves to an existing file: $full" 2
    }

    $cursor = $repo
    $relative = $full.Substring($repoPrefix.Length)
    foreach ($segment in ($relative -split '[\\/]')) {
        if (-not $segment) { continue }
        $cursor = Join-Path $cursor $segment
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                Throw-OrchestratorError "OutputRoot crosses a reparse point: $cursor" 2
            }
        }
    }
    return $full
}

function Get-ProjectVersion([string]$RepoRoot) {
    $pyproject = Get-Content -LiteralPath (Join-Path $RepoRoot 'pyproject.toml') -Raw
    $packageInit = Get-Content -LiteralPath (Join-Path $RepoRoot 'src\ai_video_production\__init__.py') -Raw
    $pyprojectMatch = [regex]::Match($pyproject, '(?m)^version\s*=\s*"([^"]+)"')
    $packageMatch = [regex]::Match($packageInit, '(?m)^__version__\s*=\s*"([^"]+)"')
    if (-not $pyprojectMatch.Success -or -not $packageMatch.Success -or
        $pyprojectMatch.Groups[1].Value -ne $packageMatch.Groups[1].Value) {
        Throw-OrchestratorError 'Product version metadata is missing or inconsistent.' 3
    }
    return $pyprojectMatch.Groups[1].Value
}

function Assert-Sha256([string]$Path, [string]$Expected, [string]$Label) {
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    if ($actual -ne $Expected.ToLowerInvariant()) {
        Throw-OrchestratorError "$Label SHA-256 mismatch: $actual" 3
    }
    return $actual
}

function Invoke-ChildPowerShell([string]$ScriptPath, [string[]]$Arguments) {
    & $script:WindowsPowerShell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $ScriptPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Child PowerShell failed with exit code $LASTEXITCODE`: $ScriptPath"
    }
}

function Invoke-BuildStage([string]$Name, [int]$ExitCode, [scriptblock]$Action) {
    $started = [DateTimeOffset]::UtcNow
    Write-Host "[STAGE] $Name"
    try {
        & $Action
        $script:StageResults.Add([ordered]@{
            name = $Name
            result = 'PASS'
            started_at = $started.ToString('o')
            completed_at = [DateTimeOffset]::UtcNow.ToString('o')
        })
        Write-Host "[PASS] $Name"
    } catch {
        $script:StageResults.Add([ordered]@{
            name = $Name
            result = 'FAIL'
            started_at = $started.ToString('o')
            completed_at = [DateTimeOffset]::UtcNow.ToString('o')
            detail = $_.Exception.Message
        })
        $exception = [InvalidOperationException]::new("$Name failed: $($_.Exception.Message)", $_.Exception)
        $exception.Data['ExitCode'] = $ExitCode
        $exception.Data['Stage'] = $Name
        throw $exception
    }
}

function Copy-NewArtifact([string]$Source, [string]$ArtifactsRoot) {
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "Expected artifact is missing: $Source"
    }
    $destination = Join-Path $ArtifactsRoot ([IO.Path]::GetFileName($Source))
    if (Test-Path -LiteralPath $destination) {
        throw "Artifact destination already exists: $destination"
    }
    Copy-Item -LiteralPath $Source -Destination $destination
    return $destination
}

function New-DirectoryZip([string]$SourceDirectory, [string]$Destination) {
    if (-not (Test-Path -LiteralPath $SourceDirectory -PathType Container)) {
        throw "ZIP source directory is missing: $SourceDirectory"
    }
    if (Test-Path -LiteralPath $Destination) {
        throw "ZIP destination already exists: $Destination"
    }
    Compress-Archive -LiteralPath $SourceDirectory -DestinationPath $Destination -CompressionLevel Optimal
    if (-not (Test-Path -LiteralPath $Destination -PathType Leaf)) {
        throw "ZIP was not created: $Destination"
    }
}

function Write-RunSummary(
    [string]$Path,
    [string]$Result,
    [string]$RunDirectory,
    [string]$FailedStage,
    [int]$ExitCode,
    [int]$ArtifactCount
) {
    $lines = @(
        "result=$Result",
        "exit_code=$ExitCode",
        "run_directory=$RunDirectory",
        "artifact_count=$ArtifactCount",
        "artifacts=$RunDirectory\artifacts",
        "checksums=$RunDirectory\SHA256SUMS.txt",
        "manifest=$RunDirectory\build-manifest.json",
        "log=$RunDirectory\logs\build.log"
    )
    if ($FailedStage) { $lines += "failed_stage=$FailedStage" }
    [IO.File]::WriteAllText($Path, (($lines -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($false))
}

$script:StageResults = [Collections.Generic.List[object]]::new()
$script:ArtifactCount = 0
$script:ComponentRecords = @()
$script:WindowsPowerShell = $null
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$outputParent = $null
$runDirectory = $null
$transcriptStarted = $false
$exitCode = 99
$failedStage = ''
$artifactCount = 0
$originalEnvironment = @{
    BVP_BUILD_PYTHON = $env:BVP_BUILD_PYTHON
    BVP_TASK048_BUILD_ROOT = $env:BVP_TASK048_BUILD_ROOT
    BVP_TASK049_TRAINING_BUILD_ROOT = $env:BVP_TASK049_TRAINING_BUILD_ROOT
    BVP_TASK049_TRIVIA_BUILD_ROOT = $env:BVP_TASK049_TRIVIA_BUILD_ROOT
}

try {
    if ($env:OS -ne 'Windows_NT') {
        Throw-OrchestratorError 'This release build must run on Windows.' 3
    }
    if (-not $RunId) {
        $RunId = 'windows-release-{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 8))
    }
    if ($RunId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$') {
        Throw-OrchestratorError 'RunId must be 1-80 ASCII letters, digits, dots, underscores, or hyphens.' 2
    }
    if (-not $OutputRoot) { $OutputRoot = Join-Path $repoRoot '.artifacts\windows-release' }
    $outputParent = Assert-ContainedOutputRoot $OutputRoot $repoRoot
    $runDirectory = Join-Path $outputParent $RunId
    if (Test-Path -LiteralPath $runDirectory) {
        Throw-OrchestratorError "Run directory already exists; choose a new RunId: $runDirectory" 2
    }

    $python = Resolve-BuildPython $BuildPython $repoRoot
    $iscc = Resolve-Iscc $IsccPath
    if (-not $PythonInstaller) {
        if ($env:BVP_PYTHON_INSTALLER) { $PythonInstaller = $env:BVP_PYTHON_INSTALLER }
        else { $PythonInstaller = Join-Path $repoRoot '.build-prerequisites\windows\python-3.12.10-amd64.exe' }
    }
    $pythonInstallerFile = Resolve-ExistingFile $PythonInstaller 'PythonInstaller'
    if (-not $VoiceCaptureRuntimeZip) {
        $VoiceCaptureRuntimeZip = Join-Path $repoRoot 'packaging\release-assets\task047\bai-voice-capture-0.1.0-dev.10-windows-x64.zip'
    }
    $voiceCaptureRuntime = Resolve-ExistingFile $VoiceCaptureRuntimeZip 'VoiceCaptureRuntimeZip'
    $voiceCaptureSource = Resolve-ExistingFile (Join-Path $repoRoot 'packaging\release-assets\task047\bai-voice-capture-0.1.0-dev.10-source.zip') 'VoiceCaptureSourceZip'
    $script:WindowsPowerShell = (Get-Command powershell.exe -ErrorAction Stop).Source
    if (-not (Get-Command cmd.exe -ErrorAction SilentlyContinue) -or
        -not (Get-Command git.exe -ErrorAction SilentlyContinue) -or
        -not (Get-Command Compress-Archive -ErrorAction SilentlyContinue)) {
        Throw-OrchestratorError 'Required Windows shell, Git, or Compress-Archive command is missing.' 3
    }
    $controllerCompiler = Resolve-ExistingFile (Join-Path $env:ProgramFiles 'Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe') 'Voice Capture Controller C# compiler'

    $version = Get-ProjectVersion $repoRoot
    $isccSha = Assert-Sha256 $iscc $script:ExpectedIsccSha256 'Inno Setup compiler'
    $pythonInstallerSha = Assert-Sha256 $pythonInstallerFile $script:ExpectedPythonInstallerSha256 'Python installer'
    $pythonInstallerSignature = Get-AuthenticodeSignature -LiteralPath $pythonInstallerFile
    if ($pythonInstallerSignature.Status -ne 'Valid' -or
        $pythonInstallerSignature.SignerCertificate.Subject -notlike '*Python Software Foundation*') {
        Throw-OrchestratorError 'Python installer Authenticode signature is invalid.' 3
    }
    $voiceCaptureRuntimeSha = Assert-Sha256 $voiceCaptureRuntime $script:ExpectedVoiceCaptureRuntimeSha256 'Voice Capture runtime ZIP'
    $voiceCaptureSourceSha = Assert-Sha256 $voiceCaptureSource $script:ExpectedVoiceCaptureSourceSha256 'Voice Capture source ZIP'
    $controllerCompilerSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $controllerCompiler).Hash.ToLowerInvariant()

    $pythonVersion = (& $python -c 'import sys; print(sys.version.split()[0])').Trim()
    if ($LASTEXITCODE -ne 0 -or -not $pythonVersion) {
        Throw-OrchestratorError 'Build Python could not execute.' 3
    }
    $moduleVersions = (& $python -c "from importlib.metadata import version; import build, PyInstaller, webview, faster_whisper; print('|'.join([PyInstaller.__version__, version('build'), version('pywebview'), version('faster-whisper')]))").Trim()
    if ($LASTEXITCODE -ne 0) {
        Throw-OrchestratorError 'Windows build dependencies are missing. Install the repository windows-build and build extras explicitly.' 3
    }
    $parts = $moduleVersions -split '\|'
    if ($parts.Count -ne 4 -or $parts[0] -ne '6.22.2') {
        Throw-OrchestratorError "PyInstaller 6.22.2 is required; observed dependency tuple: $moduleVersions" 3
    }

    $sourceCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $sourceCommit -notmatch '^[0-9a-f]{40}$') {
        Throw-OrchestratorError 'Could not resolve the source Git commit.' 3
    }
    $sourceBranch = (& git -C $repoRoot branch --show-current).Trim()
    if (-not $sourceBranch) { $sourceBranch = 'DETACHED' }
    $dirtyLines = @(& git -C $repoRoot status --porcelain=v1 --untracked-files=all)
    $isDirty = $dirtyLines.Count -gt 0
    if ($isDirty -and -not $AllowDirtySource) {
        Throw-OrchestratorError 'Source worktree is dirty. Commit/stash changes or explicitly pass -AllowDirtySource.' 3
    }

    if ($PreflightOnly) {
        [ordered]@{
            result = 'PASS'
            effect = 'NONE'
            version = $version
            source_commit = $sourceCommit
            source_branch = $sourceBranch
            source_dirty = $isDirty
            python_version = $pythonVersion
            dependency_versions = $moduleVersions
            output_parent_valid = $true
        } | ConvertTo-Json -Depth 4
        exit 0
    }

    if (-not (Test-Path -LiteralPath $outputParent -PathType Container)) {
        New-Item -ItemType Directory -Path $outputParent -Force | Out-Null
    }
    $outputParent = Assert-ContainedOutputRoot $outputParent $repoRoot
    if (Test-Path -LiteralPath $runDirectory) {
        Throw-OrchestratorError "Run directory appeared after preflight; choose a new RunId: $runDirectory" 2
    }
    New-Item -ItemType Directory -Path $runDirectory | Out-Null
    $logsRoot = New-Item -ItemType Directory -Path (Join-Path $runDirectory 'logs')
    $workRoot = New-Item -ItemType Directory -Path (Join-Path $runDirectory 'work')
    $artifactsRoot = New-Item -ItemType Directory -Path (Join-Path $runDirectory 'artifacts')
    $transcriptPath = Join-Path $logsRoot.FullName 'build.log'
    Start-Transcript -LiteralPath $transcriptPath | Out-Null
    $transcriptStarted = $true
    Write-Host "[INFO] TASK-096 operation: $RunId"
    Write-Host "[INFO] Source: $sourceCommit ($sourceBranch), version $version, dirty=$isDirty"
    Write-Host "[INFO] Output root: $runDirectory"

    $env:BVP_BUILD_PYTHON = $python
    $mainBuildRoot = Join-Path $workRoot.FullName 'main-build'
    Invoke-BuildStage 'main-exe' 10 {
        $env:BVP_TASK048_BUILD_ROOT = $mainBuildRoot
        & cmd.exe /d /c (Join-Path $repoRoot 'build-windows-exe.bat')
        if ($LASTEXITCODE -ne 0) { throw "build-windows-exe.bat exited $LASTEXITCODE" }
    }

    $trainingBuildRoot = Join-Path $workRoot.FullName 'training-build'
    Invoke-BuildStage 'dbd-training-studio-exe' 11 {
        $env:BVP_TASK049_TRAINING_BUILD_ROOT = $trainingBuildRoot
        & cmd.exe /d /c (Join-Path $repoRoot 'build-dbd-training-studio-exe.bat')
        if ($LASTEXITCODE -ne 0) { throw "build-dbd-training-studio-exe.bat exited $LASTEXITCODE" }
    }

    $triviaBuildRoot = Join-Path $workRoot.FullName 'trivia-build'
    Invoke-BuildStage 'dbd-trivia-editor-exe' 12 {
        $env:BVP_TASK049_TRIVIA_BUILD_ROOT = $triviaBuildRoot
        & cmd.exe /d /c (Join-Path $repoRoot 'build-dbd-trivia-editor-exe.bat')
        if ($LASTEXITCODE -ne 0) { throw "build-dbd-trivia-editor-exe.bat exited $LASTEXITCODE" }
    }

    $pythonDistRoot = Join-Path $workRoot.FullName 'python-dist'
    Invoke-BuildStage 'python-distributions' 13 {
        New-Item -ItemType Directory -Path $pythonDistRoot | Out-Null
        & $python -m build --outdir $pythonDistRoot $repoRoot
        if ($LASTEXITCODE -ne 0) { throw "python -m build exited $LASTEXITCODE" }
        $pythonPackages = @(Get-ChildItem -LiteralPath $pythonDistRoot -File)
        if ($pythonPackages.Count -ne 2) { throw "Expected wheel and sdist; found $($pythonPackages.Count) files." }
    }

    $mainInstallerOutput = Join-Path $workRoot.FullName 'main-installer-output'
    Invoke-BuildStage 'main-installer' 20 {
        Invoke-ChildPowerShell (Join-Path $repoRoot 'tools\windows\build-task063-main-installer.ps1') @(
            '-IsccPath', $iscc,
            '-Version', $version,
            '-PayloadRoot', (Join-Path $mainBuildRoot 'BAI Video Production'),
            '-OutputDirectory', $mainInstallerOutput
        )
    }

    $dbdInstallerOutput = Join-Path $workRoot.FullName 'dbd-installer-output'
    Invoke-BuildStage 'dbd-installers' 21 {
        Invoke-ChildPowerShell (Join-Path $repoRoot 'tools\windows\build-task092-dbd-utility-installers.ps1') @(
            '-IsccPath', $iscc,
            '-TrainingPayloadRoot', (Join-Path $trainingBuildRoot 'BAI DbD Training Studio'),
            '-TriviaPayloadRoot', (Join-Path $triviaBuildRoot 'BAI DbD Trivia Editor'),
            '-OutputDirectory', $dbdInstallerOutput,
            '-Version', $version
        )
    }

    $voiceBuilderWork = Join-Path $workRoot.FullName 'voice-model-builder-work'
    $voiceBuilderOutput = Join-Path $workRoot.FullName 'voice-model-builder-output'
    Invoke-BuildStage 'voice-model-builder' 22 {
        Invoke-ChildPowerShell (Join-Path $repoRoot 'tools\windows\build-task046-voice-model-builder-installer.ps1') @(
            '-PythonExe', $python,
            '-InnoCompiler', $iscc,
            '-WorkRoot', $voiceBuilderWork,
            '-OutputDirectory', $voiceBuilderOutput,
            '-AppVersion', $script:VoiceModelBuilderVersion
        )
    }

    $voiceCaptureWork = Join-Path $workRoot.FullName 'voice-capture-work'
    $voiceCaptureOutput = Join-Path $workRoot.FullName 'voice-capture-output'
    Invoke-BuildStage 'voice-capture-installer' 23 {
        Invoke-ChildPowerShell (Join-Path $repoRoot 'tools\windows\build-task047-obs-installer.ps1') @(
            '-RuntimeZip', $voiceCaptureRuntime,
            '-InnoCompiler', $iscc,
            '-WorkRoot', $voiceCaptureWork,
            '-OutputDirectory', $voiceCaptureOutput
        )
    }

    $ownerVoiceWork = Join-Path $workRoot.FullName 'owner-voice-runtime-work'
    $ownerVoiceOutput = Join-Path $workRoot.FullName 'owner-voice-runtime-output'
    Invoke-BuildStage 'owner-voice-runtime-installer' 24 {
        Invoke-ChildPowerShell (Join-Path $repoRoot 'tools\windows\build-task093-owner-voice-runtime-installer.ps1') @(
            '-BuildPython', $python,
            '-PythonInstaller', $pythonInstallerFile,
            '-IsccPath', $iscc,
            '-WorkRoot', $ownerVoiceWork,
            '-OutputDirectory', $ownerVoiceOutput,
            '-Version', $version
        )
    }

    $artifactMetadata = [Collections.Generic.List[object]]::new()
    Invoke-BuildStage 'distribution-packaging' 30 {
        $zipDefinitions = @(
            [ordered]@{ source = (Join-Path $mainBuildRoot 'BAI Video Production'); name = "bai-video-production-$version-windows-x64.zip"; product = 'BAI Video Production' },
            [ordered]@{ source = (Join-Path $trainingBuildRoot 'BAI DbD Training Studio'); name = "bai-dbd-training-studio-$version-windows-x64.zip"; product = 'BAI DbD Training Studio' },
            [ordered]@{ source = (Join-Path $triviaBuildRoot 'BAI DbD Trivia Editor'); name = "bai-dbd-trivia-editor-$version-windows-x64.zip"; product = 'BAI DbD Trivia Editor' },
            [ordered]@{ source = (Join-Path $voiceBuilderWork 'payload'); name = "bai-voice-model-builder-$($script:VoiceModelBuilderVersion)-windows-x64.zip"; product = 'BAI Voice Model Builder' }
        )
        foreach ($definition in $zipDefinitions) {
            $destination = Join-Path $artifactsRoot.FullName $definition.name
            New-DirectoryZip $definition.source $destination
            $artifactMetadata.Add([ordered]@{ path = $destination; kind = 'distribution-zip'; product = $definition.product })
        }

        $filesToStage = @(
            [ordered]@{ path = (Join-Path $mainInstallerOutput "bai-video-production-$version-windows-x64-setup.exe"); kind = 'installer'; product = 'BAI Video Production' },
            [ordered]@{ path = (Join-Path $dbdInstallerOutput "bai-dbd-training-studio-$version-windows-x64-setup.exe"); kind = 'installer'; product = 'BAI DbD Training Studio' },
            [ordered]@{ path = (Join-Path $dbdInstallerOutput "bai-dbd-trivia-editor-$version-windows-x64-setup.exe"); kind = 'installer'; product = 'BAI DbD Trivia Editor' },
            [ordered]@{ path = (Join-Path $voiceBuilderOutput "bai-voice-model-builder-$($script:VoiceModelBuilderVersion)-windows-x64-setup.exe"); kind = 'installer'; product = 'BAI Voice Model Builder' },
            [ordered]@{ path = (Join-Path $voiceCaptureOutput "bai-voice-capture-$($script:VoiceCaptureVersion)-installer.2-windows-x64-setup.exe"); kind = 'installer'; product = 'BAI Voice Capture' },
            [ordered]@{ path = $voiceCaptureRuntime; kind = 'distribution-zip'; product = 'BAI Voice Capture' },
            [ordered]@{ path = $voiceCaptureSource; kind = 'source-zip'; product = 'BAI Voice Capture' },
            [ordered]@{ path = (Join-Path $ownerVoiceOutput "bai-owner-voice-runtime-$version-windows-x64-setup.exe"); kind = 'installer'; product = 'BAI Owner Voice Runtime' }
        )
        foreach ($definition in $filesToStage) {
            $destination = Copy-NewArtifact $definition.path $artifactsRoot.FullName
            $artifactMetadata.Add([ordered]@{ path = $destination; kind = $definition.kind; product = $definition.product })
        }
        foreach ($package in (Get-ChildItem -LiteralPath $pythonDistRoot -File | Sort-Object Name)) {
            $destination = Copy-NewArtifact $package.FullName $artifactsRoot.FullName
            $kind = 'python-sdist'
            if ($package.Extension -eq '.whl') { $kind = 'python-wheel' }
            $artifactMetadata.Add([ordered]@{ path = $destination; kind = $kind; product = 'BAI Video Production Python package' })
        }

        $bundlePath = Join-Path $artifactsRoot.FullName "bai-windows-release-$version.zip"
        $bundleInputs = @($artifactMetadata | ForEach-Object { $_.path })
        Compress-Archive -LiteralPath $bundleInputs -DestinationPath $bundlePath -CompressionLevel Optimal
        if (-not (Test-Path -LiteralPath $bundlePath -PathType Leaf)) { throw 'Release bundle ZIP was not created.' }
        $artifactMetadata.Add([ordered]@{ path = $bundlePath; kind = 'release-bundle-zip'; product = 'BAI Windows Release Bundle' })

        $componentDefinitions = @(
            [ordered]@{ path = (Join-Path $mainBuildRoot 'BAI Video Production\BAI Video Production.exe'); product = 'BAI Video Production'; role = 'user-entrypoint'; artifact = "artifacts/bai-video-production-$version-windows-x64.zip"; archive_path = 'BAI Video Production/BAI Video Production.exe' },
            [ordered]@{ path = (Join-Path $mainBuildRoot 'BAI Video Production\BAI Video Production Key Helper.exe'); product = 'BAI Video Production'; role = 'internal-key-helper'; artifact = "artifacts/bai-video-production-$version-windows-x64.zip"; archive_path = 'BAI Video Production/BAI Video Production Key Helper.exe' },
            [ordered]@{ path = (Join-Path $mainBuildRoot 'BAI Video Production\_internal\_meter\bai-voice-capture-controller.exe'); product = 'BAI Video Production'; role = 'internal-meter-controller'; artifact = "artifacts/bai-video-production-$version-windows-x64.zip"; archive_path = 'BAI Video Production/_internal/_meter/bai-voice-capture-controller.exe' },
            [ordered]@{ path = (Join-Path $mainBuildRoot 'BAI Video Production\_internal\_meter\worker\BAI Meter Worker.exe'); product = 'BAI Video Production'; role = 'internal-meter-worker'; artifact = "artifacts/bai-video-production-$version-windows-x64.zip"; archive_path = 'BAI Video Production/_internal/_meter/worker/BAI Meter Worker.exe' },
            [ordered]@{ path = (Join-Path $trainingBuildRoot 'BAI DbD Training Studio\BAI DbD Training Studio.exe'); product = 'BAI DbD Training Studio'; role = 'user-entrypoint'; artifact = "artifacts/bai-dbd-training-studio-$version-windows-x64.zip"; archive_path = 'BAI DbD Training Studio/BAI DbD Training Studio.exe' },
            [ordered]@{ path = (Join-Path $triviaBuildRoot 'BAI DbD Trivia Editor\BAI DbD Trivia Editor.exe'); product = 'BAI DbD Trivia Editor'; role = 'user-entrypoint'; artifact = "artifacts/bai-dbd-trivia-editor-$version-windows-x64.zip"; archive_path = 'BAI DbD Trivia Editor/BAI DbD Trivia Editor.exe' },
            [ordered]@{ path = (Join-Path $voiceBuilderWork 'payload\application\bai-voice-model-builder.exe'); product = 'BAI Voice Model Builder'; role = 'user-entrypoint'; artifact = "artifacts/bai-voice-model-builder-$($script:VoiceModelBuilderVersion)-windows-x64.zip"; archive_path = 'payload/application/bai-voice-model-builder.exe' },
            [ordered]@{ path = (Join-Path $voiceCaptureWork 'payload\controller\bai-voice-capture-controller.exe'); product = 'BAI Voice Capture'; role = 'controller'; artifact = "artifacts/bai-voice-capture-$($script:VoiceCaptureVersion)-windows-x64.zip"; archive_path = 'controller/bai-voice-capture-controller.exe' }
        )
        $components = @()
        foreach ($component in $componentDefinitions) {
            if (-not (Test-Path -LiteralPath $component.path -PathType Leaf)) {
                throw "Required EXE component is missing: $($component.role)"
            }
            $file = Get-Item -LiteralPath $component.path
            $components += [ordered]@{
                product = $component.product
                role = $component.role
                artifact = $component.artifact
                archive_path = $component.archive_path
                bytes = $file.Length
                sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
            }
        }
        $script:ComponentRecords = $components
    }

    Invoke-BuildStage 'manifest-and-checksums' 31 {
        $artifactRecords = @()
        $checksumLines = @()
        foreach ($entry in ($artifactMetadata | Sort-Object { [IO.Path]::GetFileName($_.path) })) {
            $file = Get-Item -LiteralPath $entry.path
            $sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
            $relative = 'artifacts/' + $file.Name
            $checksumLines += "$sha256  $relative"
            $artifactRecords += [ordered]@{
                path = $relative
                bytes = $file.Length
                sha256 = $sha256
                kind = $entry.kind
                product = $entry.product
            }
        }
        if ($artifactRecords.Count -ne 15) {
            throw "Expected 15 release artifacts; observed $($artifactRecords.Count)."
        }
        $checksumsPath = Join-Path $runDirectory 'SHA256SUMS.txt'
        [IO.File]::WriteAllText($checksumsPath, (($checksumLines -join "`n") + "`n"), [Text.UTF8Encoding]::new($false))
        $manifest = [ordered]@{
            schema_version = 1
            task = 'TASK-096/A1'
            operation_id = $RunId
            result = 'PASS'
            started_at = $script:StageResults[0].started_at
            completed_at = [DateTimeOffset]::UtcNow.ToString('o')
            source = [ordered]@{
                commit = $sourceCommit
                branch = $sourceBranch
                version = $version
                dirty = $isDirty
            }
            tools = [ordered]@{
                python_version = $pythonVersion
                dependency_versions = $moduleVersions
                python_executable_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $python).Hash.ToLowerInvariant()
                iscc_sha256 = $isccSha
                python_installer_sha256 = $pythonInstallerSha
                controller_compiler_sha256 = $controllerCompilerSha
                voice_capture_runtime_sha256 = $voiceCaptureRuntimeSha
                voice_capture_source_sha256 = $voiceCaptureSourceSha
            }
            prohibited_effects = [ordered]@{
                product_install = $false
                product_launch = $false
                obs_mutation = $false
                model_or_runtime_download = $false
                owner_audio_access = $false
                signing = $false
                tag_or_publish = $false
            }
            stages = @($script:StageResults) + @([ordered]@{
                name = 'manifest-and-checksums'
                result = 'PASS'
                started_at = [DateTimeOffset]::UtcNow.ToString('o')
                completed_at = [DateTimeOffset]::UtcNow.ToString('o')
            })
            artifacts = $artifactRecords
            executable_components = $script:ComponentRecords
        }
        $manifestPath = Join-Path $runDirectory 'build-manifest.json'
        [IO.File]::WriteAllText($manifestPath, (($manifest | ConvertTo-Json -Depth 10) + "`n"), [Text.UTF8Encoding]::new($false))
        $roundTrip = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        if ($roundTrip.operation_id -ne $RunId -or @($roundTrip.artifacts).Count -ne 15 -or
            @($roundTrip.executable_components).Count -ne 8) {
            throw 'Manifest read-back verification failed.'
        }
        $script:ArtifactCount = $artifactRecords.Count
    }

    $exitCode = 0
    $artifactCount = $script:ArtifactCount
    Write-RunSummary (Join-Path $runDirectory 'SUMMARY.txt') 'PASS' $runDirectory '' 0 $artifactCount
    Write-Host "[PASS] All Windows release artifacts completed."
    Write-Host "[INFO] Summary: $runDirectory\SUMMARY.txt"
    Write-Host "[INFO] Artifacts: $runDirectory\artifacts"
} catch {
    if ($_.Exception.Data.Contains('ExitCode')) { $exitCode = [int]$_.Exception.Data['ExitCode'] }
    if ($_.Exception.Data.Contains('Stage')) { $failedStage = [string]$_.Exception.Data['Stage'] }
    [Console]::Error.WriteLine("[ERROR] $($_.Exception.Message)")
    if ($runDirectory -and (Test-Path -LiteralPath $runDirectory -PathType Container)) {
        Write-RunSummary (Join-Path $runDirectory 'SUMMARY.txt') 'FAIL' $runDirectory $failedStage $exitCode $artifactCount
    }
} finally {
    $env:BVP_BUILD_PYTHON = $originalEnvironment.BVP_BUILD_PYTHON
    $env:BVP_TASK048_BUILD_ROOT = $originalEnvironment.BVP_TASK048_BUILD_ROOT
    $env:BVP_TASK049_TRAINING_BUILD_ROOT = $originalEnvironment.BVP_TASK049_TRAINING_BUILD_ROOT
    $env:BVP_TASK049_TRIVIA_BUILD_ROOT = $originalEnvironment.BVP_TASK049_TRIVIA_BUILD_ROOT
    if ($transcriptStarted) {
        try { Stop-Transcript | Out-Null } catch { }
    }
}

exit $exitCode
