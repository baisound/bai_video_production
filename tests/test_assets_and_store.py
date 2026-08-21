import pytest
from ai_video_production import AssetRecord, AssetType, ProfileSnapshot, RightsStatus, SQLiteProductStore
from ai_video_production.errors import ProductError
import os
import sqlite3
import ai_video_production.store as store_module
from threading import Barrier, Thread

def test_asset_registry_and_rights_gate(tmp_path):
    ps=ProfileSnapshot.create("default","1",{})
    store=SQLiteProductStore(tmp_path/"db.sqlite3")
    job=store.create_job(ps.profile_snapshot_id)
    owned=AssetRecord(job.job_id,AssetType.VIDEO,f"asset://{job.job_id}/source/a.mp4","sha256:"+"a"*64,RightsStatus.OWNED,"USER")
    store.register_asset(owned)
    assert owned.auto_use_allowed
    unknown=AssetRecord(job.job_id,AssetType.VIDEO,f"asset://{job.job_id}/source/b.mp4","sha256:"+"b"*64,RightsStatus.UNKNOWN,"USER")
    assert not unknown.auto_use_allowed

def test_mvp_tables_exist(tmp_path):
    store=SQLiteProductStore(tmp_path/"db.sqlite3")
    expected={"production_jobs","assets","asset_versions","manifests","operations","checkpoints","approvals","evidence","cost_ledger","profiles","decisions","schema_migrations"}
    assert expected <= store.table_names()


def test_store_initialization_closes_its_sqlite_connection(tmp_path, monkeypatch):
    opened = []
    real_connect = sqlite3.connect

    def tracked_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", tracked_connect)
    SQLiteProductStore(tmp_path / "db.sqlite3")

    assert opened
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


def test_asset_checksum_must_be_exact_sha256(tmp_path):
    ps=ProfileSnapshot.create("default","1",{})
    store=SQLiteProductStore(tmp_path/"db.sqlite3")
    job=store.create_job(ps.profile_snapshot_id)
    import pytest
    with pytest.raises(ValueError):
        AssetRecord(job.job_id,AssetType.VIDEO,f"asset://{job.job_id}/source/a.mp4","sha256:bad",RightsStatus.OWNED,"USER")


def test_asset_logical_uri_cannot_cross_job_scope(tmp_path):
    ps = ProfileSnapshot.create("x", "1.0.0", {})
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    job_a = store.create_job(ps.profile_snapshot_id)
    job_b = store.create_job(ps.profile_snapshot_id)
    with pytest.raises(ValueError):
        AssetRecord(
            job_a.job_id, AssetType.VIDEO, f"asset://{job_b.job_id}/source/a.mp4",
            "sha256:" + "a"*64, RightsStatus.OWNED, "USER"
        )


def test_existing_store_rejects_exact_name_but_wrong_index_semantics(tmp_path):
    path = tmp_path / "db.sqlite3"
    store = SQLiteProductStore(path)
    job = store.create_job(ProfileSnapshot.create("x", "1.0.0", {}).profile_snapshot_id)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP INDEX idx_assets_job_asset_id")
        conn.execute("CREATE INDEX idx_assets_job_asset_id ON assets(checksum)")
    with pytest.raises(ProductError) as rejected:
        SQLiteProductStore(path, require_existing=True, required_job_id=job.job_id)
    assert rejected.value.code == "ERR_STORE_EXISTING_DATABASE_INVALID"


def test_existing_store_rejects_database_identity_swap_after_admission(tmp_path):
    profile = ProfileSnapshot.create("x", "1.0.0", {})
    path = tmp_path / "db.sqlite3"
    original = SQLiteProductStore(path)
    job = original.create_job(profile.profile_snapshot_id)
    strict = SQLiteProductStore(path, require_existing=True, required_job_id=job.job_id)

    replacement_path = tmp_path / "replacement.sqlite3"
    replacement = SQLiteProductStore(replacement_path)
    replacement.create_job(profile.profile_snapshot_id, job_id=job.job_id)
    backup = tmp_path / "original.sqlite3"
    if os.name == "nt":
        with pytest.raises(PermissionError):
            path.replace(backup)
        strict.close()
        return
    path.replace(backup)
    replacement_path.replace(path)

    with pytest.raises(ProductError) as rejected:
        strict.get_job_state(job.job_id)
    assert rejected.value.code == "ERR_STORE_EXISTING_DATABASE_IDENTITY"


@pytest.mark.skipif(os.name != "posix", reason="POSIX inode swap-back regression")
def test_existing_store_connects_to_pinned_inode_during_path_swap_back(tmp_path, monkeypatch):
    profile = ProfileSnapshot.create("x", "1.0.0", {})
    path = tmp_path / "db.sqlite3"
    original = SQLiteProductStore(path)
    job = original.create_job(profile.profile_snapshot_id)
    strict = SQLiteProductStore(path, require_existing=True, required_job_id=job.job_id)

    replacement_path = tmp_path / "replacement.sqlite3"
    replacement = SQLiteProductStore(replacement_path)
    replacement.create_job(profile.profile_snapshot_id)
    original_path = tmp_path / "original.sqlite3"
    foreign_path = tmp_path / "foreign.sqlite3"
    real_connect = sqlite3.connect
    swapped = False

    def connect_with_swap_back(database, *args, **kwargs):
        nonlocal swapped
        if not swapped and isinstance(database, str) and "mode=rw" in database:
            swapped = True
            path.replace(original_path)
            replacement_path.replace(path)
            try:
                return real_connect(database, *args, **kwargs)
            finally:
                path.replace(foreign_path)
                original_path.replace(path)
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connect_with_swap_back)
    with pytest.raises(ProductError) as rejected:
        strict.get_job_state(job.job_id)
    assert rejected.value.code == "ERR_STORE_EXISTING_DATABASE_IDENTITY"
    assert swapped is True


def test_existing_store_rejects_database_above_admission_size_bound(tmp_path, monkeypatch):
    profile = ProfileSnapshot.create("x", "1.0.0", {})
    path = tmp_path / "db.sqlite3"
    store = SQLiteProductStore(path)
    job = store.create_job(profile.profile_snapshot_id)
    monkeypatch.setattr(store_module, "_MAX_EXISTING_DATABASE_BYTES", path.stat().st_size - 1)
    with pytest.raises(ProductError) as rejected:
        SQLiteProductStore(path, require_existing=True, required_job_id=job.job_id)
    assert rejected.value.code == "ERR_STORE_EXISTING_DATABASE_INVALID"


def test_operation_status_compare_and_set_admits_exactly_one_concurrent_caller(tmp_path):
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    profile = ProfileSnapshot.create("x", "1.0.0", {})
    job = store.create_job(profile.profile_snapshot_id)
    operation, created = store.reserve_operation(job.job_id, "test.command", "same-key")
    assert created is True
    assert store.find_operation(job.job_id, "same-key") == operation

    barrier = Barrier(3)
    observations = []

    def claim() -> None:
        barrier.wait()
        observations.append(
            store.compare_and_set_operation_status(
                operation.operation_id,
                expected_statuses=("PENDING",),
                status="IN_PROGRESS",
                increment_attempt=True,
            )
        )

    threads = [Thread(target=claim) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(5)
        assert not thread.is_alive()

    assert sorted(changed for _record, changed in observations) == [False, True]
    current = store.get_operation(operation.operation_id)
    assert current.status == "IN_PROGRESS"
    assert current.attempt == 1


def test_operation_read_and_compare_and_set_close_all_sqlite_connections(tmp_path, monkeypatch):
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    profile = ProfileSnapshot.create("x", "1.0.0", {})
    job = store.create_job(profile.profile_snapshot_id)
    operation, _created = store.reserve_operation(job.job_id, "test.command", "closed-key")
    opened = []
    real_connect = sqlite3.connect

    def tracked_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", tracked_connect)
    assert store.find_operation(job.job_id, "closed-key") == operation
    _current, changed = store.compare_and_set_operation_status(
        operation.operation_id,
        expected_statuses=("PENDING",),
        expected_result_refs=(None,),
        status="IN_PROGRESS",
        result_ref="lease-1",
        replace_result_ref=True,
    )
    assert changed is True
    assert opened
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


@pytest.mark.parametrize("invalid", ["", "bad\x00ref", "\ud800", 7])
def test_operation_compare_and_set_rejects_invalid_result_ref(tmp_path, invalid):
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    profile = ProfileSnapshot.create("x", "1.0.0", {})
    job = store.create_job(profile.profile_snapshot_id)
    operation, _created = store.reserve_operation(job.job_id, "test.command", "invalid-ref")
    with pytest.raises(ValueError, match="result_ref"):
        store.compare_and_set_operation_status(
            operation.operation_id,
            expected_statuses=("PENDING",),
            status="IN_PROGRESS",
            result_ref=invalid,
            replace_result_ref=True,
        )
