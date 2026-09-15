<#
.SYNOPSIS
SRTから本人声のMaster WAVを対話式で生成します。

.DESCRIPTION
引数なしで実行すると、SRTと既存voice-dataset（または3～15秒の見本WAV）を
順番に質問します。manifest作成、生成前チェック、SRT計画、本人声生成を自動実行し、
最後にmaster-owner-voice.wavの保存先を表示します。

.EXAMPLE
.\tools\windows\make-owner-voice-wav.ps1

.EXAMPLE
.\tools\windows\make-owner-voice-wav.ps1 -Srt "E:\BAI_AI\jobs\input.srt" -ReferenceManifest "E:\BAI_AI\private\owner-voice\voice-dataset\dataset\reference-manifest.json"

.NOTES
詳しい説明は docs/user/SRT-OWNER-VOICE-WAV.md を参照してください。
本人音声は、Ownerが承認した暗号化保存領域だけに保存してください。
#>
[CmdletBinding()]
param(
    [string]$Srt,
    [string]$ReferenceManifest,
    [string]$ReferenceWav,
    [string]$ReferenceText,
    [string]$Python,
    [string]$ModelRoot,
    [string]$JobsRoot
)

$ErrorActionPreference = 'Stop'

function Resolve-InputFile([string]$Value, [string]$Prompt, [string]$Extension) {
    while ([string]::IsNullOrWhiteSpace($Value)) {
        $Value = Read-Host $Prompt
    }
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

$Srt = Resolve-InputFile $Srt 'SRTファイルを画面からここへドラッグして Enter' '.srt'

if ([string]::IsNullOrWhiteSpace($ReferenceManifest)) {
    $defaultManifest = Join-Path (Get-Location) 'voice-dataset\dataset\reference-manifest.json'
    if (Test-Path -LiteralPath $defaultManifest -PathType Leaf) {
        $ReferenceManifest = $defaultManifest
        Write-Host "既存のvoice-datasetを使用します: $ReferenceManifest" -ForegroundColor Cyan
    } elseif ([string]::IsNullOrWhiteSpace($ReferenceWav)) {
        $datasetAnswer = Read-Host '以前作ったvoice-datasetフォルダーがあればドラッグして Enter（なければ空のままEnter）'
        if (-not [string]::IsNullOrWhiteSpace($datasetAnswer)) {
            $datasetAnswer = $datasetAnswer.Trim().Trim('"')
            if (Test-Path -LiteralPath $datasetAnswer -PathType Container) {
                $ReferenceManifest = Join-Path $datasetAnswer 'dataset\reference-manifest.json'
            } else {
                $ReferenceManifest = $datasetAnswer
            }
        }
    }
}

if (-not [string]::IsNullOrWhiteSpace($ReferenceManifest)) {
    $ReferenceManifest = Resolve-InputFile $ReferenceManifest 'reference-manifest.jsonの場所を入力して Enter' '.json'
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
    $ReferenceWav = Resolve-InputFile $ReferenceWav 'あなたの見本WAVを画面からここへドラッグして Enter' '.wav'
    while ([string]::IsNullOrWhiteSpace($ReferenceText)) {
        $ReferenceText = Read-Host '見本WAVで実際に話している文章を入力して Enter'
    }
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$sourceRoot = Join-Path $repoRoot 'src'

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
        $JobsRoot = Read-Host '本人声データを保存するOwner承認済みフォルダーを指定して Enter'
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

Write-Host ''
Write-Host '確認してください:' -ForegroundColor Yellow
Write-Host '  1. 見本WAVはあなた自身の声で、使用する権利があります。'
Write-Host '  2. 入力した文章は見本WAVの発話と完全に一致します。'
Write-Host '  3. 見本WAVの音質を確認しました。'
$confirmation = Read-Host 'すべて正しければ YES と入力'
if ($confirmation -cne 'YES') {
    throw '確認されなかったため、音声生成を開始しませんでした。'
}

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($previousPythonPath)) { $sourceRoot } else { "$sourceRoot;$previousPythonPath" }
    & $Python -m ai_video_production.task014_srt_owner_voice_wav preflight --model-root $ModelRoot --reference-wav $ReferenceWav --reference-text $referenceTextFile --output $preflightFile
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
    & $Python -m ai_video_production.task014_srt_owner_voice_wav render --srt $Srt --model-root $ModelRoot --references $referencesFile --work-dir $workRoot --output $outputFile --report $reportFile
    if ($LASTEXITCODE -ne 0) { throw 'WAV生成に失敗しました。reportと直前のエラーを確認してください。' }
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

Write-Host ''
Write-Host '完了しました。Master WAV:' -ForegroundColor Green
Write-Host $outputFile
Write-Host '公開や動画利用の前に、必ず全編を試聴してください。' -ForegroundColor Yellow
