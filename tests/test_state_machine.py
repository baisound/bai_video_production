import pytest
from ai_video_production import CheckpointRecord, JobStateService, ProductionJobState, ProfileSnapshot, ResumeContext, SQLiteProductStore
from ai_video_production.errors import ProductError

def make(tmp_path):
    snap = ProfileSnapshot.create("default", "1.0.0", {"purpose":"test"})
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    job = store.create_job(snap.profile_snapshot_id)
    return store, JobStateService(store), job

def test_forward_transition_and_optimistic_revision(tmp_path):
    store, svc, job = make(tmp_path)
    job = svc.transition(job.job_id, ProductionJobState.INGESTING, expected_version=1)
    assert job.state is ProductionJobState.INGESTING and job.state_version == 2
    with pytest.raises(ProductError) as exc:
        svc.transition(job.job_id, ProductionJobState.NORMALIZING, expected_version=1)
    assert exc.value.code == "ERR_STATE_STALE_REVISION"

def test_illegal_transition_fails_closed(tmp_path):
    _, svc, job = make(tmp_path)
    with pytest.raises(ProductError) as exc:
        svc.transition(job.job_id, ProductionJobState.RENDERING, expected_version=1)
    assert exc.value.code == "ERR_STATE_INVALID_TRANSITION"

def test_pause_resume_preserves_resume_target(tmp_path):
    store, svc, job = make(tmp_path)
    job = svc.transition(job.job_id, "INGESTING", expected_version=1)
    job = svc.transition(job.job_id, "PAUSED", expected_version=2)
    assert job.resume_to_state is ProductionJobState.INGESTING
    # Profile snapshot ID is obtained from the setup snapshot in production; here
    # create a matching checkpoint using the DB value for the test fixture.
    import sqlite3
    with sqlite3.connect(store.path) as conn:
        profile_snapshot_id=conn.execute("SELECT profile_snapshot_id FROM production_jobs WHERE job_id=?",(job.job_id,)).fetchone()[0]
    cp=CheckpointRecord(job.job_id,"INGESTING","sha256:" + "a"*64,"sha256:" + "b"*64,"INGESTING",profile_snapshot_id,{"source":"sha256:" + "e"*64})
    current=ResumeContext("sha256:" + "a"*64,profile_snapshot_id,{"source":"sha256:" + "e"*64})
    job = svc.resume_from_checkpoint(job.job_id, expected_version=3, checkpoint=cp, current=current)
    assert job.state is ProductionJobState.INGESTING and job.resume_to_state is None
    assert job.state_version == 5  # side -> RESUMING -> target consumes two revisions atomically

def test_terminal_job_cannot_reopen(tmp_path):
    # Drive a job through the canonical happy path.
    _, svc, job = make(tmp_path)
    path = ["INGESTING","NORMALIZING","ANALYZING","CANDIDATES_READY","PLAN_REVIEW","PLAN_APPROVED",
            "ASSET_PREPARING","RESOLVE_ASSEMBLING","AUTO_QA","READY_FOR_MANUAL_EDIT","MANUAL_EDITING",
            "READY_FOR_RENDER","RENDERING","RENDER_QA","COMPLETED"]
    for state in path:
        job = svc.transition(job.job_id, state, expected_version=job.state_version)
    assert job.state is ProductionJobState.COMPLETED
    with pytest.raises(ProductError):
        svc.transition(job.job_id, "RESUMING", expected_version=job.state_version)

def test_failed_requires_error_code(tmp_path):
    _, svc, job = make(tmp_path)
    with pytest.raises(ProductError) as exc:
        svc.transition(job.job_id, "FAILED", expected_version=1)
    assert exc.value.code == "ERR_STATE_FAILURE_CODE_REQUIRED"


def test_direct_resuming_transition_is_rejected(tmp_path):
    store, svc, job = make(tmp_path)
    job=svc.transition(job.job_id,"INGESTING",expected_version=1)
    job=svc.transition(job.job_id,"PAUSED",expected_version=2)
    with pytest.raises(ProductError) as exc:
        svc.transition(job.job_id,"RESUMING",expected_version=3)
    assert exc.value.code=="ERR_STATE_RESUME_API_REQUIRED"


def test_resume_checkpoint_mismatch_leaves_job_paused(tmp_path):
    store, svc, job = make(tmp_path)
    job = svc.transition(job.job_id, "INGESTING", expected_version=1)
    job = svc.transition(job.job_id, "PAUSED", expected_version=2)
    import sqlite3
    with sqlite3.connect(store.path) as conn:
        profile_snapshot_id = conn.execute(
            "SELECT profile_snapshot_id FROM production_jobs WHERE job_id=?", (job.job_id,)
        ).fetchone()[0]
    checkpoint = CheckpointRecord(
        job.job_id, "INGESTING", "sha256:" + "c"*64, "sha256:" + "b"*64, "INGESTING",
        profile_snapshot_id, {"source": "sha256:" + "e"*64}
    )
    current = ResumeContext("sha256:" + "d"*64, profile_snapshot_id, {"source": "sha256:" + "e"*64})
    with pytest.raises(ProductError) as exc:
        svc.resume_from_checkpoint(
            job.job_id, expected_version=3, checkpoint=checkpoint, current=current
        )
    assert exc.value.code == "ERR_INTEGRITY_CHECKPOINT_MISMATCH"
    after = store.get_job_state(job.job_id)
    assert after.state is ProductionJobState.PAUSED
    assert after.state_version == 3
    assert after.resume_to_state is ProductionJobState.INGESTING


def test_resume_cannot_substitute_a_different_profile_snapshot(tmp_path):
    store, svc, job = make(tmp_path)
    job = svc.transition(job.job_id, "INGESTING", expected_version=1)
    job = svc.transition(job.job_id, "PAUSED", expected_version=2)
    other = ProfileSnapshot.create("other", "1.0.0", {})
    checkpoint = CheckpointRecord(
        job.job_id, "INGESTING", "sha256:" + "a"*64, "sha256:" + "b"*64,
        "INGESTING", other.profile_snapshot_id, {"source": "sha256:" + "e"*64}
    )
    current = ResumeContext(
        "sha256:" + "a"*64, other.profile_snapshot_id, {"source": "sha256:" + "e"*64}
    )
    with pytest.raises(ProductError) as exc:
        svc.resume_from_checkpoint(job.job_id, expected_version=3, checkpoint=checkpoint, current=current)
    assert exc.value.code == "ERR_INTEGRITY_CHECKPOINT_PROFILE_MISMATCH"
    after = store.get_job_state(job.job_id)
    assert after.state is ProductionJobState.PAUSED and after.state_version == 3


def test_concurrent_state_mutations_allow_only_one_winner(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    store, svc, job = make(tmp_path)

    def advance(_):
        try:
            return svc.transition(job.job_id, "INGESTING", expected_version=1).state.value
        except ProductError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(advance, range(2)))
    assert results.count("INGESTING") == 1
    assert any(code == "ERR_STATE_STALE_REVISION" for code in results)
    final = store.get_job_state(job.job_id)
    assert final.state is ProductionJobState.INGESTING and final.state_version == 2
