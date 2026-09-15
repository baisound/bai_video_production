<#
.SYNOPSIS
コマンド引数で指定したSRTから本人声のMaster WAVを生成します。

.DESCRIPTION
SRTと既存voice-dataset（または3～15秒の見本WAV）を引数で受け取り、manifest作成、
生成前チェック、SRT計画、本人声生成を実行します。ファイル選択画面や対話式質問は
使用しません。

.EXAMPLE
.\tools\windows\make-owner-voice-wav.ps1 -Srt "E:\BAI_AI\jobs\input.srt" -ReferenceManifest "E:\BAI_AI\private\owner-voice\voice-dataset\dataset\reference-manifest.json" -ConfirmOwnerApproved

.NOTES
詳しい説明は docs/user/SRT-OWNER-VOICE-WAV.md を参照してください。
本人音声は、Ownerが承認した暗号化保存領域だけに保存してください。
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Srt,
    [string]$ReferenceManifest,
    [string]$ReferenceWav,
    [string]$ReferenceText,
    [Parameter(Mandatory = $true)][switch]$ConfirmOwnerApproved,
    [string]$Python,
    [string]$ModelRoot,
    [string]$JobsRoot,
    [string]$ConfigPath
)

$ErrorActionPreference = 'Stop'

function Resolve-InputFile([string]$Value, [string]$Label, [string]$Extension) {
    if ([string]::IsNullOrWhiteSpace($Value)) { throw "$Label を指定してください。" }
    $Value = $Value.Trim().Trim('"')
    if (-not (Test-Path -LiteralPath $Value -PathType Leaf)) {
        throw "ファイルが見つかりません: $Value"
    }
    $resolved = (Resolve-Path -LiteralPath $Value).Path
    if (-not $resolved.EndsWith($Extension, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Extension ファイルを指定してください: $resolved"
    }
    return $resolved
}

function Test-Python([string]$Candidate) {
    if ([string]::IsNullOrWhiteSpace($Candidate) -or -not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
        return $false
    }
    $null = & $Candidate -c "import numpy, soundfile, torch, qwen_tts" 2>$null
    return $LASTEXITCODE -eq 0
}

$Srt = Resolve-InputFile $Srt '-Srt' '.srt'
if (-not $ConfirmOwnerApproved) {
    throw '-ConfirmOwnerApproved が必要です。本人の声であり、使用権と音質・文字起こしを確認してから指定してください。'
}
if (-not [string]::IsNullOrWhiteSpace($ReferenceManifest) -and
    (-not [string]::IsNullOrWhiteSpace($ReferenceWav) -or -not [string]::IsNullOrWhiteSpace($ReferenceText))) {
    throw '-ReferenceManifest と -ReferenceWav/-ReferenceText は同時に指定できません。'
}

if (-not [string]::IsNullOrWhiteSpace($ReferenceManifest)) {
    $ReferenceManifest = Resolve-InputFile $ReferenceManifest '-ReferenceManifest' '.json'
    $manifestData = Get-Content -Raw -LiteralPath $ReferenceManifest | ConvertFrom-Json
    $eligibleReferences = @($manifestData.candidates | Where-Object {
        $_.quality_pass -eq $true -and $_.owner_approved -eq $true -and $_.transcript_verified -eq $true
    })
    if ($eligibleReferences.Count -eq 0) {
        throw 'voice-datasetに承認済みの3～15秒参照音声がありません。'
    }
    $ReferenceWav = [string]$eligibleReferences[0].wav_path
    $referenceTextFile = [string]$eligibleReferences[0].transcript_path
} else {
    $ReferenceWav = Resolve-InputFile $ReferenceWav '-ReferenceWav' '.wav'
    if ([string]::IsNullOrWhiteSpace($ReferenceText)) { throw '-ReferenceText を指定してください。' }
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$sourceRoot = Join-Path $repoRoot 'src'
$Ffmpeg = 'ffmpeg'

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $env:LOCALAPPDATA 'BAI Video Production\owner-voice\runtime-config.json'
}
if (Test-Path -LiteralPath $ConfigPath -PathType Leaf) {
    $runtimeConfig = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
    if ($runtimeConfig.schema_version -ne 1 -or $runtimeConfig.status -ne 'READY' -or
        $runtimeConfig.model_revision -ne '5d83992436eae1d760afd27aff78a71d676296fc') {
        throw "本人声runtime設定が未完了または未対応です。修復インストールしてください: $ConfigPath"
    }
    if ([string]::IsNullOrWhiteSpace($Python)) { $Python = [string]$runtimeConfig.python }
    if ([string]::IsNullOrWhiteSpace($ModelRoot)) { $ModelRoot = [string]$runtimeConfig.model_root }
    if ([string]::IsNullOrWhiteSpace($JobsRoot)) { $JobsRoot = [string]$runtimeConfig.jobs_root }
    if (-not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.ffmpeg)) { $Ffmpeg = [string]$runtimeConfig.ffmpeg }
    Write-Host "インストーラーで準備済みの本人声環境を使用します。" -ForegroundColor Cyan
}

if (-not (Test-Python $Python)) {
    $pythonCandidates = @(
        'E:\BAI_AI\envs\qwen3-tts-06b-base\Scripts\python.exe',
        'E:\BAI_AI\envs\task046-qwen3-tts-windows-native\Scripts\python.exe',
        'E:\BAI_AI\envs\task014-qwen3-tts-probe\Scripts\python.exe'
    )
    $Python = $pythonCandidates | Where-Object { Test-Python $_ } | Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace($Python)) {
    throw '本人声生成用Python環境が見つかりません。初回セットアップが必要です。'
}

if ([string]::IsNullOrWhiteSpace($ModelRoot)) {
    $modelCandidates = @(
        'E:\BAI_AI\models\Qwen3-TTS-12Hz-0.6B-Base\5d83992436eae1d760afd27aff78a71d676296fc',
        'D:\BAI\BAI_VIDEO_PRODUCTION_20260914\models\Qwen3-TTS-12Hz-0.6B-Base'
    )
    $ModelRoot = $modelCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Container } | Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace($ModelRoot)) {
    throw 'Qwen3-TTS 0.6B Baseモデルが見つかりません。初回セットアップが必要です。'
}
$ModelRoot = (Resolve-Path -LiteralPath $ModelRoot).Path

if ([string]::IsNullOrWhiteSpace($JobsRoot)) {
    if (-not [string]::IsNullOrWhiteSpace($ReferenceManifest)) {
        $datasetRoot = Split-Path -Parent (Split-Path -Parent $ReferenceManifest)
        $JobsRoot = Join-Path $datasetRoot 'master-wav-jobs'
        Write-Host "Master WAVの作業先: $JobsRoot" -ForegroundColor Cyan
    } else {
        throw '-JobsRoot を指定するか、本人声runtimeインストーラーを実行してください。'
    }
}
$JobsRoot = [IO.Path]::GetFullPath($JobsRoot.Trim().Trim('"'))
$volumeRoot = [IO.Path]::GetPathRoot($JobsRoot)
if ($JobsRoot.StartsWith('\\') -or $JobsRoot.TrimEnd('\') -eq $volumeRoot.TrimEnd('\') -or
    (Split-Path -Parent $JobsRoot).TrimEnd('\') -eq $volumeRoot.TrimEnd('\')) {
    throw '保存先にはドライブルート／直下／ネットワーク共有を使用できません。'
}
if (-not (Test-Path -LiteralPath $JobsRoot)) {
    New-Item -ItemType Directory -Path $JobsRoot | Out-Null
}
$resolvedJobsRoot = (Resolve-Path -LiteralPath $JobsRoot).Path
if ((Get-Item -LiteralPath $resolvedJobsRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw '保存先にリンク／再解析ポイントは使用できません。'
}

$jobId = 'job-{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 8))
$jobRoot = Join-Path $resolvedJobsRoot $jobId
$privateRoot = Join-Path $jobRoot 'private'
$workRoot = Join-Path $jobRoot 'work'
$outputRoot = Join-Path $jobRoot 'output'
New-Item -ItemType Directory -Path $privateRoot, $workRoot, $outputRoot | Out-Null

$generatedReferenceTextFile = Join-Path $privateRoot 'owner-reference.txt'
$generatedReferencesFile = Join-Path $privateRoot 'references.json'
$preflightFile = Join-Path $jobRoot 'preflight.json'
$planFile = Join-Path $jobRoot 'srt-plan.json'
$outputFile = Join-Path $outputRoot 'master-owner-voice.wav'
$reportFile = Join-Path $outputRoot 'master-owner-voice.report.json'
if ([string]::IsNullOrWhiteSpace($ReferenceManifest)) {
    [IO.File]::WriteAllText($generatedReferenceTextFile, $ReferenceText.Trim(), [Text.UTF8Encoding]::new($false))
    $referenceTextFile = $generatedReferenceTextFile
    $referencesFile = $generatedReferencesFile
} else {
    $referencesFile = $ReferenceManifest
}

$previousPythonPath = $env:PYTHONPATH
try {
    if (Test-Path -LiteralPath $sourceRoot -PathType Container) {
        $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($previousPythonPath)) { $sourceRoot } else { "$sourceRoot;$previousPythonPath" }
    }
    & $Python -m ai_video_production.task014_srt_owner_voice_wav preflight --model-root $ModelRoot --reference-wav $ReferenceWav --reference-text $referenceTextFile --ffmpeg $Ffmpeg --output $preflightFile
    if ($LASTEXITCODE -ne 0) { throw '生成前チェックに失敗しました。preflight.jsonを確認してください。' }
    $preflight = Get-Content -Raw -LiteralPath $preflightFile | ConvertFrom-Json
    if ($preflight.state -ne 'READY') { throw "GPUを含む生成準備が完了していません: $($preflight.state)" }

    & $Python -m ai_video_production.task014_srt_owner_voice_wav plan --srt $Srt --output $planFile
    if ($LASTEXITCODE -ne 0) { throw 'SRTの確認に失敗しました。' }

    if ([string]::IsNullOrWhiteSpace($ReferenceManifest)) {
        & $Python -m ai_video_production.task014_srt_owner_voice_wav prepare-reference --reference-wav $ReferenceWav --reference-text $referenceTextFile --output $referencesFile --confirm-owner-approved --confirm-quality-pass --confirm-transcript-verified
        if ($LASTEXITCODE -ne 0) { throw '見本WAVの確認に失敗しました。3～15秒、48 kHz、mono、PCM 24-bitか確認してください。' }
    }

    Write-Host '本人声WAVを生成しています。字幕数により時間がかかります…' -ForegroundColor Cyan
    & $Python -m ai_video_production.task014_srt_owner_voice_wav render --srt $Srt --model-root $ModelRoot --references $referencesFile --work-dir $workRoot --output $outputFile --ffmpeg $Ffmpeg --report $reportFile
    if ($LASTEXITCODE -ne 0) { throw 'WAV生成に失敗しました。reportと直前のエラーを確認してください。' }
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

Write-Host ''
Write-Host '完了しました。Master WAV:' -ForegroundColor Green
Write-Host $outputFile
Write-Host '公開や動画利用の前に、必ず全編を試聴してください。' -ForegroundColor Yellow
