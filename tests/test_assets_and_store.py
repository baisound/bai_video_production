import pytest
from ai_video_production import AssetRecord, AssetType, ProfileSnapshot, RightsStatus, SQLiteProductStore

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
