from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import multiprocessing
import sqlite3

import pytest

from ai_video_production import ProfileSnapshot, SQLiteProductStore
from ai_video_production.errors import ProductError


T0 = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)


def _cas_worker(path, job_id, operation_id, barrier, result_queue):
    store = SQLiteProductStore(
        path,
        require_existing=True,
        required_job_id=job_id,
        clock=lambda: T0,
    )
    barrier.wait(10)
    _record, changed, evaluated = store.compare_and_set_operation_status_with_validity(
        operation_id,
        expected_statuses=("PENDING",),
        status="IN_PROGRESS",
        valid_from="2026-09-19T12:00:00Z",
        valid_until="2026-09-19T12:00:05Z",
        expected_result_refs=(None,),
        result_ref="cas-process-owner",
        replace_result_ref=True,
        increment_attempt=True,
    )
    result_queue.put((changed, evaluated))
    store.close()

def test_duplicate_idempotency_key_returns_same_operation(tmp_path):
    ps=ProfileSnapshot.create("default","1",{})
    store=SQLiteProductStore(tmp_path/"db.sqlite3")
    job=store.create_job(ps.profile_snapshot_id)
    first, created1=store.reserve_operation(job.job_id,"BUILD_TIMELINE","job-build-v1")
    second, created2=store.reserve_operation(job.job_id,"BUILD_TIMELINE","job-build-v1")
    assert created1 is True and created2 is False
    assert first.operation_id == second.operation_id


def test_operation_cas_expected_attempt_blocks_stale_aba_closure(tmp_path):
    store = SQLiteProductStore(tmp_path / "attempt.sqlite3", clock=lambda: T0)
    job = store.create_job(ProfileSnapshot.create("attempt", "1.0.0", {}).profile_snapshot_id)
    operation, _ = store.reserve_operation(job.job_id, "CAS", "attempt-aba")

    first, changed = store.compare_and_set_operation_status(
        operation.operation_id,
        expected_statuses=("PENDING",),
        expected_result_refs=(None,),
        expected_attempt=0,
        status="IN_PROGRESS",
        result_ref="same-owner",
        replace_result_ref=True,
        increment_attempt=True,
    )
    assert changed is True and first.attempt == 1
    returned, changed = store.compare_and_set_operation_status(
        operation.operation_id,
        expected_statuses=("IN_PROGRESS",),
        expected_result_refs=("same-owner",),
        expected_attempt=1,
        status="PENDING",
        result_ref="same-owner",
        replace_result_ref=True,
    )
    assert changed is True and returned.attempt == 1
    second, changed = store.compare_and_set_operation_status(
        operation.operation_id,
        expected_statuses=("PENDING",),
        expected_result_refs=("same-owner",),
        expected_attempt=1,
        status="IN_PROGRESS",
        result_ref="same-owner",
        replace_result_ref=True,
        increment_attempt=True,
    )
    assert changed is True and second.attempt == 2

    unchanged, changed = store.compare_and_set_operation_status(
        operation.operation_id,
        expected_statuses=("IN_PROGRESS",),
        expected_result_refs=("same-owner",),
        expected_attempt=1,
        status="FAILED",
        result_ref="stale-closure",
        replace_result_ref=True,
    )
    assert changed is False
    assert (unchanged.status, unchanged.attempt, unchanged.result_ref) == (
        "IN_PROGRESS", 2, "same-owner",
    )
    with pytest.raises(ValueError, match="expected_attempt"):
        store.compare_and_set_operation_status(
            operation.operation_id,
            expected_statuses=("IN_PROGRESS",),
            expected_attempt=True,
            status="FAILED",
        )


def test_unknown_job_idempotency_reservation_fails(tmp_path):
    from ai_video_production.ids import IdKind, generate_id
    import sqlite3, pytest
    store=SQLiteProductStore(tmp_path/"db.sqlite3")
    with pytest.raises(sqlite3.IntegrityError):
        store.reserve_operation(generate_id(IdKind.JOB),"X","key")


def test_concurrent_duplicate_reservations_converge_to_one_operation(tmp_path):
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


def test_validity_cas_uses_lock_clock_and_preserves_null_ref_and_attempt_semantics(tmp_path):
    store = SQLiteProductStore(tmp_path / "db.sqlite3", clock=lambda: T0 + timedelta(microseconds=123456))
    job = store.create_job(ProfileSnapshot.create("cas", "1.0.0", {}).profile_snapshot_id)
    operation, _ = store.reserve_operation(job.job_id, "CAS", "fresh")

    updated, changed, evaluated = store.compare_and_set_operation_status_with_validity(
        operation.operation_id,
        expected_statuses=("PENDING",),
        status="IN_PROGRESS",
        valid_from="2026-09-19T12:00:00Z",
        valid_until="2026-09-19T12:00:05Z",
        expected_result_refs=(None,),
        result_ref="owner",
        replace_result_ref=True,
        increment_attempt=True,
    )
    assert changed is True
    assert evaluated == "2026-09-19T12:00:00.123456Z"
    assert updated.status == "IN_PROGRESS"
    assert updated.result_ref == "owner"
    assert updated.attempt == 1
    assert updated.updated_at == evaluated

    stale_store = SQLiteProductStore(tmp_path / "stale.sqlite3", clock=lambda: T0 + timedelta(minutes=5))
    stale_job = stale_store.create_job(ProfileSnapshot.create("cas-stale", "1.0.0", {}).profile_snapshot_id)
    stale_operation, _ = stale_store.reserve_operation(stale_job.job_id, "CAS", "stale")
    unchanged, changed, evaluated = stale_store.compare_and_set_operation_status_with_validity(
        stale_operation.operation_id,
        expected_statuses=("PENDING",),
        status="IN_PROGRESS",
        valid_from="2026-09-19T12:00:00Z",
        valid_until="2026-09-19T12:05:00Z",
        expected_result_refs=(None,),
        result_ref="not-written",
        replace_result_ref=True,
        increment_attempt=True,
    )
    assert changed is False
    assert unchanged.status == "PENDING"
    assert unchanged.result_ref is None
    assert unchanged.attempt == 0
    assert evaluated == "2026-09-19T12:05:00Z"


@pytest.mark.parametrize("clock", [lambda: datetime(2026, 9, 19, 12, 0, 5, tzinfo=timezone.utc), lambda: datetime(2026, 9, 19, 12, 0, 5, 1, tzinfo=timezone.utc)])
def test_validity_cas_expiry_equality_and_fractional_clock_are_closed(tmp_path, clock):
    store = SQLiteProductStore(tmp_path / "db.sqlite3", clock=clock)
    job = store.create_job(ProfileSnapshot.create("cas-boundary", "1.0.0", {}).profile_snapshot_id)
    operation, _ = store.reserve_operation(job.job_id, "CAS", "boundary")
    updated, changed, evaluated = store.compare_and_set_operation_status_with_validity(
        operation.operation_id,
        expected_statuses=("PENDING",),
        status="IN_PROGRESS",
        valid_from="2026-09-19T12:00:00Z",
        valid_until="2026-09-19T12:00:05Z",
        expected_result_refs=(None,),
        result_ref="owner",
        replace_result_ref=True,
    )
    assert changed is False
    assert updated.status == "PENDING"
    assert updated.result_ref is None
    assert evaluated.startswith("2026-09-19T12:00:05")


def test_validity_cas_rejects_clock_failure_without_mutation(tmp_path):
    def broken_clock():
        return datetime(2026, 9, 19, 12, 0, 0)  # naive is forbidden

    store = SQLiteProductStore(tmp_path / "db.sqlite3", clock=broken_clock)
    job = store.create_job(ProfileSnapshot.create("cas-clock", "1.0.0", {}).profile_snapshot_id)
    operation, _ = store.reserve_operation(job.job_id, "CAS", "clock")
    with pytest.raises(ValueError, match="aware UTC"):
        store.compare_and_set_operation_status_with_validity(
            operation.operation_id,
            expected_statuses=("PENDING",),
            status="IN_PROGRESS",
            valid_from="2026-09-19T12:00:00Z",
            valid_until="2026-09-19T12:00:05Z",
            expected_result_refs=(None,),
            result_ref="owner",
            replace_result_ref=True,
        )
    unchanged = store.get_operation(operation.operation_id)
    assert unchanged.status == "PENDING" and unchanged.result_ref is None and unchanged.attempt == 0


def test_validity_clock_is_evaluated_after_write_lock_is_acquired(tmp_path):
    database = tmp_path / "db.sqlite3"
    observed_inside_lock = []

    store = SQLiteProductStore(database)
    job = store.create_job(ProfileSnapshot.create("cas-lock", "1.0.0", {}).profile_snapshot_id)
    operation, _ = store.reserve_operation(job.job_id, "CAS", "lock-order")
    store.close()

    def clock_after_lock():
        try:
            with sqlite3.connect(database, timeout=0) as competing:
                competing.execute(
                    "UPDATE operations SET last_error_code=last_error_code WHERE operation_id=?",
                    (operation.operation_id,),
                )
        except sqlite3.OperationalError as exc:
            observed_inside_lock.append("database is locked" in str(exc).lower())
        return T0

    store = SQLiteProductStore(database, clock=clock_after_lock, require_existing=True, required_job_id=job.job_id)
    _updated, changed, evaluated = store.compare_and_set_operation_status_with_validity(
        operation.operation_id,
        expected_statuses=("PENDING",),
        status="IN_PROGRESS",
        valid_from="2026-09-19T12:00:00Z",
        valid_until="2026-09-19T12:00:05Z",
        expected_result_refs=(None,),
        result_ref="lock-owner",
        replace_result_ref=True,
    )
    assert changed is True
    assert evaluated == "2026-09-19T12:00:00Z"
    assert observed_inside_lock == [True]


def test_literal_prefix_query_bounds_statuses_and_overflow(tmp_path):
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    job = store.create_job(ProfileSnapshot.create("prefix", "1.0.0", {}).profile_snapshot_id)
    operations = []
    for index, status in enumerate(("PENDING", "IN_PROGRESS", "PARTIAL", "COMPLETED", "FAILED")):
        operation, _ = store.reserve_operation(job.job_id, "task036.local_transcription.v2" + ("%" if index == 0 else ""), f"prefix-{index}")
        if status != "PENDING":
            operation = store.update_operation_status(operation.operation_id, status)
        operations.append(operation)
    assert {item.status for item in store.list_operations_by_command_prefix(job.job_id, command_type_prefix="task036.local_transcription.v2", limit=10)} == {"PENDING", "IN_PROGRESS", "PARTIAL", "COMPLETED", "FAILED"}
    assert store.list_operations_by_command_prefix(job.job_id, command_type_prefix="task036.local_transcription.v2%", limit=10)[0].command_type.endswith("%")
    with pytest.raises(ProductError) as overflow:
        store.list_operations_by_command_prefix(job.job_id, command_type_prefix="task036.local_transcription.v2", limit=1)
    assert overflow.value.code == "ERR_STORE_OPERATION_QUERY_LIMIT"
    for bad_prefix in ("", "x\x00y", "x" * 129):
        with pytest.raises(ValueError):
            store.list_operations_by_command_prefix(job.job_id, command_type_prefix=bad_prefix, limit=1)
    for bad_limit in (0, 1025, True, 1.0):
        with pytest.raises(ValueError):
            store.list_operations_by_command_prefix(job.job_id, command_type_prefix="x", limit=bad_limit)


def test_validity_cas_wins_once_across_threads_and_processes(tmp_path):
    store = SQLiteProductStore(tmp_path / "db.sqlite3", clock=lambda: T0)
    job = store.create_job(ProfileSnapshot.create("cas-race", "1.0.0", {}).profile_snapshot_id)
    operation, _ = store.reserve_operation(job.job_id, "CAS", "race")

    def cas(_):
        return store.compare_and_set_operation_status_with_validity(
            operation.operation_id,
            expected_statuses=("PENDING",), status="IN_PROGRESS",
            valid_from="2026-09-19T12:00:00Z", valid_until="2026-09-19T12:00:05Z",
            expected_result_refs=(None,), result_ref="thread-owner", replace_result_ref=True,
            increment_attempt=True,
        )[1]

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(cas, range(4))) == 1
    store.close()

    process_store = SQLiteProductStore(tmp_path / "process.sqlite3", clock=lambda: T0)
    process_job = process_store.create_job(ProfileSnapshot.create("cas-process", "1.0.0", {}).profile_snapshot_id)
    process_operation, _ = process_store.reserve_operation(process_job.job_id, "CAS", "process")
    process_store.close()
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    queue = context.Queue()
    processes = [context.Process(target=_cas_worker, args=(str(tmp_path / "process.sqlite3"), process_job.job_id, process_operation.operation_id, barrier, queue)) for _ in range(2)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(30)
        assert process.exitcode == 0
    observed = [queue.get(timeout=2) for _ in processes]
    assert sum(item[0] for item in observed) == 1


def _database_shape(path):
    with sqlite3.connect(path) as conn:
        master = tuple(conn.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        ).fetchall())
        columns = tuple(conn.execute("PRAGMA table_info(operations)").fetchall())
        migrations = tuple(conn.execute(
            "SELECT version, applied_at FROM schema_migrations ORDER BY version"
        ).fetchall())
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    return master, columns, migrations, user_version


def test_runtime_cas_does_not_migrate_schema_or_change_sqlite_user_version(tmp_path):
    database = tmp_path / "db.sqlite3"
    store = SQLiteProductStore(database, clock=lambda: T0)
    job = store.create_job(ProfileSnapshot.create("schema", "1.0.0", {}).profile_snapshot_id)
    operation, _ = store.reserve_operation(job.job_id, "task036.local_transcription.v2", "schema-check")
    before = _database_shape(database)
    assert before[3] == 0
    updated, changed, _evaluated = store.compare_and_set_operation_status_with_validity(
        operation.operation_id,
        expected_statuses=("PENDING",),
        status="IN_PROGRESS",
        valid_from="2026-09-19T12:00:00Z",
        valid_until="2026-09-19T12:00:05Z",
        expected_result_refs=(None,),
        result_ref="schema-check-owner",
        replace_result_ref=True,
    )
    assert changed is True and updated.status == "IN_PROGRESS"
    after = _database_shape(database)
    assert after == before
    store.close()
    reopened = SQLiteProductStore(database, require_existing=True, required_job_id=job.job_id, clock=lambda: T0)
    assert _database_shape(database) == before
    reopened.close()
