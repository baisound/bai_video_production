import pytest
from ai_video_production import AssetRecord, AssetType, ProfileSnapshot, RightsStatus, SQLiteProductStore
from ai_video_production.errors import ProductError
import os
import sqlite3
import ai_video_production.store as store_module

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
