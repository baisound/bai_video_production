param(
  [string]$BvpWorktree = "C:\home\baisound\worktrees\bai-video-production\task-056-chase-keyword-cue-skill-integration",
  [string]$SkillWorktree = "C:\home\baisound\worktrees\bai-davinci-montage-skills\task-056-skill-integration",
  [switch]$Commit
)
$ErrorActionPreference = "Stop"

Push-Location $BvpWorktree
$env:PYTHONPATH = Join-Path $BvpWorktree "src"
python -m pytest -q tests/test_speech_cue_keyword_detection.py
python -m pytest -q `
  tests/test_speech_cue_keyword_detection.py `
  tests/test_task006_faster_whisper.py tests/test_task006_subtitles.py `
  tests/test_large_media_transcription.py tests/test_faster_whisper_model_reuse.py `
  tests/test_task023_faster_whisper_reconciliation.py tests/test_task004_timebase_normalization.py `
  tests/test_task022_timeline_mapping.py tests/test_task036_pre_edit_runtime.py tests/test_task036_media_workflow.py
git diff --check
Pop-Location

Push-Location $SkillWorktree
$env:PYTHONPATH = Join-Path $SkillWorktree "src"
$env:BVP_TASK056_SOURCE_ROOT = $BvpWorktree
python -m pytest -q
git diff --check
Pop-Location

if ($Commit) {
  git -C $BvpWorktree add -A
  git -C $BvpWorktree commit -m "feat(task-056): add deterministic speech cue bridge for montage"
  git -C $SkillWorktree add -A
  git -C $SkillWorktree commit -m "feat: integrate BVP TASK-056 speech cues into montage runtime"
  Write-Host "Committed both worktrees."
} else {
  Write-Host "Tests PASS. Re-run with -Commit to commit both worktrees."
}
