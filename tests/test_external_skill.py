from pathlib import Path
from ai_video_production.external_skill import inspect_zip

ROOT=Path(__file__).parents[1]

def test_corrected_external_skill_is_reference_scannable():
    result=inspect_zip(ROOT/"references/external-skill/premiere-auto-edit-v2-corrected.zip")
    assert result.sha256 and result.member_count>0
    assert result.dangerous_findings == ()

def test_original_reference_preserves_personal_path_finding():
    result=inspect_zip(ROOT/"references/external-skill/premiere-auto-edit.zip")
    assert result.personal_path_findings
