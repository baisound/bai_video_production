from ai_video_production import ProfileSnapshot, SQLiteProductStore

def test_duplicate_idempotency_key_returns_same_operation(tmp_path):
    ps=ProfileSnapshot.create("default","1",{})
    store=SQLiteProductStore(tmp_path/"db.sqlite3")
    job=store.create_job(ps.profile_snapshot_id)
    first, created1=store.reserve_operation(job.job_id,"BUILD_TIMELINE","job-build-v1")
    second, created2=store.reserve_operation(job.job_id,"BUILD_TIMELINE","job-build-v1")
    assert created1 is True and created2 is False
    assert first.operation_id == second.operation_id


def test_unknown_job_idempotency_reservation_fails(tmp_path):
    from ai_video_production.ids import IdKind, generate_id
    import sqlite3, pytest
    store=SQLiteProductStore(tmp_path/"db.sqlite3")
    with pytest.raises(sqlite3.IntegrityError):
        store.reserve_operation(generate_id(IdKind.JOB),"X","key")


def test_concurrent_duplicate_reservations_converge_to_one_operation(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    ps = ProfileSnapshot.create("x", "1.0.0", {})
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    job = store.create_job(ps.profile_snapshot_id)

    def reserve(_):
        return store.reserve_operation(job.job_id, "ANALYZE", "same-key")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve, range(8)))
    ids = {record.operation_id for record, _created in results}
    created_count = sum(1 for _record, created in results if created)
    assert len(ids) == 1
    assert created_count == 1
