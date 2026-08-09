from __future__ import annotations

from importlib import resources
from pathlib import Path, PureWindowsPath

import pytest

from ai_video_production import (
    AssetRecord, AssetType, DerivedAssetPublisher, DerivedAssetSpec, LogicalPathResolver, PathMapping,
    ProfileSnapshot, RightsStatus, SQLiteProductStore,
)
from ai_video_production.derived_assets import sha256_file
from ai_video_production.serialization import sha256_bytes


def make(tmp_path):
    a=tmp_path/"assets"; j=tmp_path/"jobs"; a.mkdir(); j.mkdir()
    store=SQLiteProductStore(tmp_path/"db.sqlite3"); ps=ProfileSnapshot.create("x","1.0.0",{}); job=store.create_job(ps.profile_snapshot_id)
    resolver=LogicalPathResolver([PathMapping("asset://",a,PureWindowsPath("D:/a")),PathMapping("job://",j,PureWindowsPath("D:/j"))])
    return store,resolver,job


def test_derived_publisher_checksum_addressed_read_only(tmp_path):
    store,resolver,job=make(tmp_path); source=tmp_path/"x.bin"; source.write_bytes(b"abc")
    op=store.reserve_operation(job.job_id,"X","x")[0]
    asset=DerivedAssetPublisher(store=store,resolver=resolver).publish(source,DerivedAssetSpec(job.job_id,"test",AssetType.OTHER,"SYSTEM"),operation_id=op.operation_id)
    assert asset.checksum == sha256_bytes(b"abc")
    assert asset.logical_uri.startswith(f"asset://{job.job_id}/derived/test/")
    target=resolver.resolve(asset.logical_uri); assert isinstance(target,Path) and target.read_bytes()==b"abc"
    assert target.stat().st_mode & 0o200 == 0


def test_derived_publisher_symlink_source_denied(tmp_path):
    store,resolver,job=make(tmp_path); real=tmp_path/"r.bin"; real.write_bytes(b"x"); link=tmp_path/"l.bin"
    try: link.symlink_to(real)
    except OSError: pytest.skip("symlink unavailable")
    op=store.reserve_operation(job.job_id,"X","x")[0]
    with pytest.raises(Exception): DerivedAssetPublisher(store=store,resolver=resolver).publish(link,DerivedAssetSpec(job.job_id,"test",AssetType.OTHER,"SYSTEM"),operation_id=op.operation_id)


def test_find_manifest_by_operation_contract(tmp_path):
    store,_resolver,job=make(tmp_path); op=store.reserve_operation(job.job_id,"X","x")[0]
    m=store.reserve_manifest(job_id=job.job_id,manifest_type="x-manifest",schema_version="1.0.0",operation_id=op.operation_id,uri_pattern=f"job://{job.job_id}/m/v{{version:06d}}.json")
    assert store.find_manifest_by_operation(op.operation_id,"x-manifest") is None
    store.finalize_manifest(m.manifest_id,"sha256:"+"a"*64)
    assert store.find_manifest_by_operation(op.operation_id,"x-manifest").manifest_id == m.manifest_id


def test_task004_packaged_schema_matches_canonical():
    name="task004-operation-manifest-payload.schema.json"
    canonical=(Path(__file__).parents[1]/"schemas"/name).read_text(encoding="utf-8")
    packaged=resources.files("ai_video_production").joinpath("schema_resources",name).read_text(encoding="utf-8")
    assert canonical == packaged


def test_package_version_is_046():
    import ai_video_production
    assert ai_video_production.__version__ == "0.4.6"


def test_task004_manifest_replay_repairs_missing_evidence_index_without_duplicate_jsonl(tmp_path):
    import sqlite3
    from ai_video_production.task004_manifest import Task004ManifestWriter

    store, resolver, job = make(tmp_path)
    source = tmp_path / "derived.bin"
    source.write_bytes(b"task004-evidence")
    op = store.reserve_operation(job.job_id, "TASK004_TEST", "evidence-repair")[0]
    asset = DerivedAssetPublisher(store=store, resolver=resolver).publish(
        source,
        DerivedAssetSpec(job.job_id, "test", AssetType.OTHER, "SYSTEM"),
        operation_id=op.operation_id,
    )
    writer = Task004ManifestWriter(store=store, resolver=resolver)
    first = writer.write(
        job_id=job.job_id,
        operation_id=op.operation_id,
        manifest_type="task004-test-manifest",
        schema_id="ai-video.task004-test-manifest",
        lane="TIMEBASE_NORMALIZATION",
        operation_kind="EVIDENCE_REPAIR_TEST",
        source_refs=(),
        input_checksums=(),
        output_assets=(asset,),
        details={"test": True},
        evidence_category="TASK004_TEST",
        producer_component="task004-test",
    )
    evidence_path = resolver.resolve(first.evidence_uri)
    assert isinstance(evidence_path, Path)
    before = evidence_path.read_text(encoding="utf-8").splitlines()
    assert len(before) == 1
    with sqlite3.connect(store.path) as conn:
        conn.execute("DELETE FROM evidence WHERE operation_id=?", (op.operation_id,))
        conn.commit()
    assert not store.has_evidence_for_operation(op.operation_id, "TASK004_TEST")

    second = writer.write(
        job_id=job.job_id,
        operation_id=op.operation_id,
        manifest_type="task004-test-manifest",
        schema_id="ai-video.task004-test-manifest",
        lane="TIMEBASE_NORMALIZATION",
        operation_kind="EVIDENCE_REPAIR_TEST",
        source_refs=(),
        input_checksums=(),
        output_assets=(asset,),
        details={"test": True},
        evidence_category="TASK004_TEST",
        producer_component="task004-test",
    )
    after = evidence_path.read_text(encoding="utf-8").splitlines()
    assert second.manifest.manifest_id == first.manifest.manifest_id
    assert after == before
    assert store.has_evidence_for_operation(op.operation_id, "TASK004_TEST")


@pytest.mark.parametrize("name", [
    "h3-production-brief-plan.schema.json",
    "h3-single-frame-contract.schema.json",
    "h3-foley-profile.schema.json",
    "h3-acceleration-contract.schema.json",
])
def test_task004_h3_packaged_schemas_match_canonical(name):
    canonical=(Path(__file__).parents[1]/"schemas"/name).read_text(encoding="utf-8")
    packaged=resources.files("ai_video_production").joinpath("schema_resources",name).read_text(encoding="utf-8")
    assert canonical == packaged
