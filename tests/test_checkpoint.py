import pytest
from ai_video_production import CheckpointRecord, ProfileSnapshot, ResumeContext, assert_resume_compatible
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.errors import ProductError

def test_checkpoint_resume_requires_exact_canonical_inputs():
    job=generate_id(IdKind.JOB); ps=ProfileSnapshot.create("default","1",{})
    cp=CheckpointRecord(job,"ANALYZING","sha256:" + "a"*64,"sha256:" + "b"*64,"ANALYZING",ps.profile_snapshot_id,{"analysis":"sha256:" + "e"*64})
    assert_resume_compatible(cp,ResumeContext("sha256:" + "a"*64,ps.profile_snapshot_id,{"analysis":"sha256:" + "e"*64}))
    with pytest.raises(ProductError) as exc:
        assert_resume_compatible(cp,ResumeContext("sha256:" + "d"*64,ps.profile_snapshot_id,{"analysis":"sha256:" + "e"*64}))
    assert exc.value.code == "ERR_INTEGRITY_CHECKPOINT_MISMATCH"


def test_checkpoint_rejects_noncanonical_hashes():
    from ai_video_production import ProfileSnapshot
    ps = ProfileSnapshot.create("x", "1.0.0", {})
    job = generate_id(IdKind.JOB)
    with pytest.raises(ValueError):
        CheckpointRecord(job, "INGESTING", "sha256:bad", "sha256:" + "b"*64, "INGESTING", ps.profile_snapshot_id, {})


def test_store_rejects_checkpoint_bound_to_other_profile(tmp_path):
    from ai_video_production import SQLiteProductStore
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    job_profile = ProfileSnapshot.create("job", "1.0.0", {})
    other_profile = ProfileSnapshot.create("other", "1.0.0", {})
    job = store.create_job(job_profile.profile_snapshot_id)
    checkpoint = CheckpointRecord(
        job.job_id, "CREATED", "sha256:" + "a"*64, "sha256:" + "b"*64,
        "CREATED", other_profile.profile_snapshot_id, {}
    )
    with pytest.raises(ProductError) as exc:
        store.save_checkpoint(checkpoint)
    assert exc.value.code == "ERR_INTEGRITY_CHECKPOINT_PROFILE_MISMATCH"
