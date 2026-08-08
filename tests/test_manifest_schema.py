from pathlib import Path
import pytest
from ai_video_production import ProfileSnapshot
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.manifest import ManifestEnvelope, Producer
from ai_video_production.schema_contracts import reader_compatible, requires_migration, validate_instance

SCHEMA = Path(__file__).parents[1] / "schemas" / "canonical-manifest-envelope.schema.json"

def test_manifest_validates_against_json_schema():
    job = generate_id(IdKind.JOB)
    ps = ProfileSnapshot.create("default", "1.0.0", {"quality":"draft"})
    man = ManifestEnvelope.create(schema_id="ai-video.edit-plan", schema_version="1.0.0", production_job_id=job,
        revision=1, producer=Producer("edit-plan-service","0.1.0"), profile_snapshot_id=ps.profile_snapshot_id,
        payload={"timeline":{"clips":[]}}, source_refs=("asset://x/source/a",))
    validate_instance(man.to_dict(), SCHEMA)
    assert man.content_checksum.startswith("sha256:")

def test_manifest_rejects_secret_and_raw_path():
    job = generate_id(IdKind.JOB); ps = ProfileSnapshot.create("default","1",{})
    with pytest.raises(ValueError):
        ManifestEnvelope.create(schema_id="ai-video.edit-plan", schema_version="1.0.0", production_job_id=job, revision=1,
            producer=Producer("x","1"), profile_snapshot_id=ps.profile_snapshot_id, payload={"api_key":"secret"})
    with pytest.raises(ValueError):
        ManifestEnvelope.create(schema_id="ai-video.edit-plan", schema_version="1.0.0", production_job_id=job, revision=1,
            producer=Producer("x","1"), profile_snapshot_id=ps.profile_snapshot_id, payload={"file_path":"/mnt/d/a.mp4"})

def test_schema_compatibility_policy():
    assert reader_compatible("1.0.0", "1.7.2")
    assert not reader_compatible("1.9.0", "2.0.0")
    assert requires_migration("1.9.0", "2.0.0")


def test_all_project_schemas_are_valid_json_schemas():
    from jsonschema import Draft202012Validator
    for path in (Path(__file__).parents[1]/"schemas").glob("*.schema.json"):
        import json
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_manifest_constructor_enforces_version_hash_and_raw_source_contracts():
    job = generate_id(IdKind.JOB)
    ps = ProfileSnapshot.create("default", "1.0.0", {})
    common = dict(
        schema_id="ai-video.edit-plan", production_job_id=job, revision=1,
        producer=Producer("test", "1.0.0"), profile_snapshot_id=ps.profile_snapshot_id,
        payload={"ok": True},
    )
    with pytest.raises(ValueError):
        ManifestEnvelope.create(schema_version="1", **common)
    with pytest.raises(ValueError):
        ManifestEnvelope.create(schema_version="1.0.0", input_checksums=("sha256:not-a-digest",), **common)
    with pytest.raises(ValueError):
        ManifestEnvelope.create(schema_version="1.0.0", source_refs=(r"C:\Users\name\secret.mp4",), **common)


def test_manifest_payload_is_immutable_after_checksum_creation():
    job = generate_id(IdKind.JOB)
    ps = ProfileSnapshot.create("default", "1.0.0", {})
    source = {"timeline": {"clips": []}}
    man = ManifestEnvelope.create(
        schema_id="ai-video.edit-plan", schema_version="1.0.0", production_job_id=job, revision=1,
        producer=Producer("test", "1.0.0"), profile_snapshot_id=ps.profile_snapshot_id, payload=source,
    )
    before = man.to_dict()
    source["timeline"]["clips"].append({"id": "mutated-outside"})
    returned = man.payload
    returned["timeline"]["clips"].append({"id": "mutated-copy"})
    after = man.to_dict()
    assert after == before
    assert after["content_checksum"] == man.content_checksum
