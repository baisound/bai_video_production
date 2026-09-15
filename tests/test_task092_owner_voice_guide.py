from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "user" / "SRT-OWNER-VOICE-WAV.md"


def test_owner_voice_srt_guide_is_separate_and_readme_linked() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/user/SRT-OWNER-VOICE-WAV.md" in readme
    for token in (
        "ai_video_production.task014_srt_owner_voice_wav preflight",
        "ai_video_production.task014_srt_owner_voice_wav plan",
        "ai_video_production.task014_srt_owner_voice_wav render",
        "--reference-wav",
        "--reference-text",
        "--references",
        "--work-dir",
        "--report",
        "read_pcm_wav_info",
        "本人が全編を試聴",
        "48 kHz・mono・PCM 24-bit",
    ):
        assert token in text


def test_guide_never_places_job_data_directly_below_a_drive_root() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    assert "D:\\BAI\\BAI_VIDEO_PRODUCTION_20260914\\owner-voice-jobs\\job-001" in text
    assert "$JobRoot = 'D:\\owner-voice" not in text
