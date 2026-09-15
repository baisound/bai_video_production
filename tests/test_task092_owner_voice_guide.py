from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "user" / "SRT-OWNER-VOICE-WAV.md"


def test_owner_voice_srt_guide_is_separate_and_readme_linked() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/user/SRT-OWNER-VOICE-WAV.md" in readme
    for token in (
        "make-owner-voice-wav.ps1",
        "-Srt",
        "-ReferenceManifest",
        "-ReferenceWav",
        "-ReferenceText",
        "-ConfirmOwnerApproved",
        "BUILDING-OWNER-VOICE-RUNTIME-INSTALLER.md",
        "本人が全編を試聴",
        "48 kHz・mono・PCM 24-bit",
    ):
        assert token in text
    assert "Read-Host" not in text


def test_guide_never_places_job_data_directly_below_a_drive_root() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    assert "<選択した本人声データフォルダー>\\jobs\\job-YYYYMMDD-HHMMSS-xxxxxxxx" in text
    assert "$JobRoot = 'D:\\owner-voice" not in text
