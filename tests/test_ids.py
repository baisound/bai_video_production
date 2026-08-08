import pytest
from ai_video_production.ids import IdKind, generate_id, validate_id, validate_project_id, validate_schema_id

def test_all_generated_ids_validate_and_are_unique():
    for kind in IdKind:
        values = {generate_id(kind) for _ in range(20)}
        assert len(values) == 20
        for value in values:
            assert validate_id(value, kind) == value

def test_invalid_identifiers_rejected():
    with pytest.raises(ValueError): validate_id("JOB-0001", IdKind.JOB)
    with pytest.raises(ValueError): validate_project_id("AI Video")
    with pytest.raises(ValueError): validate_schema_id("Manifest")
