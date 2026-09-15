[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $repoRoot 'tools\windows\install-owner-voice-runtime.ps1'
$makeCommand = Join-Path $repoRoot 'tools\windows\make-owner-voice-wav.ps1'
$runRoot = Join-Path ([IO.Path]::GetTempPath()) ('bvp-task093-test-' + [guid]::NewGuid().ToString('N'))
$installRoot = Join-Path $runRoot 'installed\app'
$dataRoot = Join-Path $runRoot 'data\owner-voice'
$configRoot = Join-Path $runRoot 'config\owner-voice'
$manifest = Join-Path $runRoot 'fixture\runtime-manifest.json'
try {
    New-Item -ItemType Directory -Path $installRoot, (Split-Path -Parent $manifest) | Out-Null
    [IO.File]::WriteAllText($manifest, (@{
        schema_version = 1
        task = 'TASK-093'
        product_version = '0.24.2'
        model_revision = '5d83992436eae1d760afd27aff78a71d676296fc'
        python_installer = @{ file = 'python-3.12.10-amd64.exe'; sha256 = ('0' * 64) }
        application_wheel = @{ file = 'fixture.whl'; sha256 = ('0' * 64) }
    } | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    $plan = & $script -DataRoot $dataRoot -InstallRoot $installRoot -ManifestPath $manifest -ConfigRoot $configRoot -PlanOnly | ConvertFrom-Json
    if ($plan.task -ne 'TASK-093' -or $plan.model_download_may_be_required -ne $true -or
        $plan.owner_audio_read -ne $false -or $plan.training_started -ne $false) {
        throw 'Safe plan contract failed.'
    }
    $unsafePassed = $false
    & $script -DataRoot 'C:\BVP-TASK093-UNSAFE' -InstallRoot $installRoot -ManifestPath $manifest -ConfigRoot $configRoot -PlanOnly | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $unsafePassed = $true
    }
    if ($unsafePassed) { throw 'Drive-root direct child was not rejected.' }
    if (Test-Path -LiteralPath $dataRoot) { throw 'PlanOnly unexpectedly created the data root.' }
    $makeCommandSource = Get-Content -Raw -LiteralPath $makeCommand
    if ($makeCommandSource -match '\bRead-Host\b') {
        throw 'WAV command must not contain interactive file or confirmation prompts.'
    }
    if ($makeCommandSource -notmatch '\[Parameter\(Mandatory = \$true\)\]\[string\]\$Srt' -or
        $makeCommandSource -notmatch '\[Parameter\(Mandatory = \$true\)\]\[switch\]\$ConfirmOwnerApproved') {
        throw 'WAV command must require explicit SRT and Owner confirmation arguments.'
    }
    Write-Output 'TASK-093_OWNER_VOICE_RUNTIME_INSTALLER_TEST_PASS'
} finally {
    if (Test-Path -LiteralPath $runRoot) {
        $resolved = (Resolve-Path -LiteralPath $runRoot).Path
        $tempPrefix = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
        if (-not $resolved.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing cleanup outside temp root: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
exit 0
