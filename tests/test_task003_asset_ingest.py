from __future__ import annotations

import json
import os
from pathlib import Path, PureWindowsPath
import sqlite3
import stat
import wave

import pytest

from ai_video_production import (
    AssetIngestRequest,
    AssetIngestService,
    AssetType,
    AudioRightsStatus,
    LogicalPathResolver,
    PathMapping,
    PermissionState,
    ProductError,
    ProfileSnapshot,
    RightsStatus,
    SQLiteProductStore,
    SourcePathPolicy,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.schema_contracts import validate_instance


def write_wav(path: Path, *, frames: int = 8000, rate: int = 8000) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\0\0" * frames)


def make_service(tmp_path: Path, *, failure_injector=None):
    source_root = tmp_path / "incoming"
    asset_root = tmp_path / "assets"
    job_root = tmp_path / "jobs"
    source_root.mkdir(exist_ok=True)
    asset_root.mkdir(exist_ok=True)
    job_root.mkdir(exist_ok=True)
    store = SQLiteProductStore(tmp_path / "product.sqlite3")
    profile = ProfileSnapshot.create("task003", "1.0.0", {})
    job = store.create_job(profile.profile_snapshot_id)
    resolver = LogicalPathResolver([
        PathMapping("asset://", asset_root, PureWindowsPath("D:/AI-VIDEO/assets"), "s3://bucket/assets"),
        PathMapping("job://", job_root, PureWindowsPath("D:/AI-VIDEO/jobs"), "s3://bucket/jobs"),
    ])
    service = AssetIngestService(
        store=store,
        resolver=resolver,
        source_policy=SourcePathPolicy((source_root,)),
        failure_injector=failure_injector,
    )
    return service, store, resolver, source_root, asset_root, job_root, job


def request(job_id: str, path: Path, key: str = "ingest-1", **overrides):
    values = dict(
        production_job_id=job_id,
        source_path=path,
        asset_type=AssetType.AUDIO,
        rights_status=RightsStatus.OWNED,
        owner="USER",
        idempotency_key=key,
        commercial_use=PermissionState.ALLOWED,
        derivative_allowed=PermissionState.ALLOWED,
        reuse_allowed=PermissionState.ALLOWED,
        audio_rights_status=AudioRightsStatus.SAFE,
    )
    values.update(overrides)
    return AssetIngestRequest(**values)


def test_task003_end_to_end_audio_ingest_registry_manifest_and_evidence(tmp_path):
    service, store, resolver, source_root, _asset_root, _job_root, job = make_service(tmp_path)
    source = source_root / "voice.wav"
    write_wav(source)
    source_before = source.read_bytes()

    result = service.ingest(request(job.job_id, source))

    assert result.operation.status == "COMPLETED"
    assert not result.deduplicated
    assert store.get_job_state(job.job_id).state.value == "INGESTING"
    assert result.asset.original_name == "voice.wav"
    assert result.asset.media_metadata["size_bytes"] == len(source_before)
    assert any(stream["codec_type"] == "audio" for stream in result.asset.media_metadata["streams"])
    target = resolver.resolve(result.asset.logical_uri)
    assert isinstance(target, Path)
    assert target.read_bytes() == source_before
    assert source.read_bytes() == source_before  # source is copied, never moved/destructively edited
    assert target.stat().st_mode & stat.S_IWUSR == 0

    versioned = resolver.resolve(result.source_manifest_uri)
    assert isinstance(versioned, Path) and versioned.exists()
    manifest = json.loads(versioned.read_text(encoding="utf-8"))
    assert manifest["payload"]["asset_count"] == 1
    assert manifest["payload"]["assets"][0]["asset_id"] == result.asset.asset_id
    assert manifest["payload"]["assets"][0]["logical_uri"] == result.asset.logical_uri
    assert str(source) not in versioned.read_text(encoding="utf-8")

    evidence = resolver.resolve(result.evidence_uri)
    assert isinstance(evidence, Path) and evidence.exists()
    text = evidence.read_text(encoding="utf-8")
    assert result.asset.asset_id in text
    assert str(source) not in text


def test_source_manifest_payload_validates_against_schema(tmp_path):
    service, _store, resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "a.wav"; write_wav(source)
    result = service.ingest(request(job.job_id, source))
    manifest = json.loads(resolver.resolve(result.source_manifest_uri).read_text(encoding="utf-8"))
    schema = Path(__file__).parents[1] / "schemas" / "source-manifest-payload.schema.json"
    validate_instance(manifest["payload"], schema)


def test_idempotent_replay_returns_same_asset_without_new_manifest_revision(tmp_path):
    service, store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "a.wav"; write_wav(source)
    first = service.ingest(request(job.job_id, source, "same-key"))
    second = service.ingest(request(job.job_id, source, "same-key"))
    assert second.asset.asset_id == first.asset.asset_id
    assert second.operation.operation_id == first.operation.operation_id
    assert second.deduplicated
    assert len(store.list_assets(job.job_id)) == 1
    assert store.latest_manifest(job.job_id, "source-manifest").version == 1


def test_duplicate_bytes_new_operation_deduplicates_registry(tmp_path):
    service, store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    a = source_root / "a.wav"; b = source_root / "renamed.wav"
    write_wav(a); b.write_bytes(a.read_bytes())
    first = service.ingest(request(job.job_id, a, "k1"))
    second = service.ingest(request(job.job_id, b, "k2"))
    assert second.asset.asset_id == first.asset.asset_id
    assert second.deduplicated
    assert len(store.list_assets(job.job_id)) == 1
    assert store.latest_manifest(job.job_id, "source-manifest").version == 2


def test_duplicate_bytes_with_conflicting_rights_fail_closed_for_human_review(tmp_path):
    service, store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "a.wav"; write_wav(source)
    service.ingest(request(job.job_id, source, "k1"))
    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, source, "k2", rights_status=RightsStatus.UNKNOWN))
    assert exc.value.code == "ERR_POLICY_DUPLICATE_RIGHTS_CONFLICT"
    assert exc.value.category.value == "HUMAN_REVIEW_REQUIRED"
    assert len(store.list_assets(job.job_id)) == 1


def test_source_path_outside_allowlist_is_rejected(tmp_path):
    service, _store, _resolver, _source_root, *_rest, job = make_service(tmp_path)
    outside = tmp_path / "outside.wav"; write_wav(outside)
    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, outside))
    assert exc.value.code == "ERR_SECURITY_PATH_DENIED"


def test_source_symlink_is_rejected(tmp_path):
    service, _store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    real = source_root / "real.wav"; link = source_root / "link.wav"
    write_wav(real)
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, link))
    assert exc.value.code == "ERR_SECURITY_PATH_DENIED"


def test_ffprobe_type_mismatch_is_rejected_before_registry(tmp_path):
    service, store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "audio.wav"; write_wav(source)
    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, source, asset_type=AssetType.VIDEO))
    assert exc.value.code == "ERR_INPUT_MEDIA_TYPE_MISMATCH"
    assert store.list_assets(job.job_id) == ()


def test_corrupt_media_is_rejected_without_leaking_staging_file(tmp_path):
    service, store, _resolver, source_root, asset_root, *_rest, job = make_service(tmp_path)
    source = source_root / "broken.wav"; source.write_bytes(b"not-a-wave")
    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, source))
    assert exc.value.code == "ERR_INPUT_MEDIA_PROBE_FAILED"
    assert store.list_assets(job.job_id) == ()
    assert not list(asset_root.rglob("*.part"))


def test_fault_after_promote_before_registry_rolls_back_promoted_file(tmp_path):
    def fail(stage, _path):
        if stage == "after_promote_before_registry":
            raise RuntimeError("injected")
    service, store, _resolver, source_root, asset_root, *_rest, job = make_service(tmp_path, failure_injector=fail)
    source = source_root / "a.wav"; write_wav(source)
    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, source))
    assert exc.value.code == "ERR_INTERNAL_ASSET_INGEST_FAILED"
    assert store.list_assets(job.job_id) == ()
    assert not [p for p in asset_root.rglob("*") if p.is_file()]


def test_manifest_failure_leaves_registered_asset_and_retry_repairs_without_source(tmp_path):
    def fail(stage, _path):
        if stage == "before_manifest_write":
            raise RuntimeError("manifest fault")
    service, store, resolver, source_root, asset_root, job_root, job = make_service(tmp_path, failure_injector=fail)
    source = source_root / "a.wav"; write_wav(source)
    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, source, "recover-key"))
    assert exc.value.code == "ERR_INTERNAL_ASSET_INGEST_FAILED"
    assets = store.list_assets(job.job_id)
    assert len(assets) == 1
    op = store.reserve_operation(job.job_id, "ASSET_INGEST", "recover-key")[0]
    assert op.status == "PARTIAL" and op.result_ref == assets[0].asset_id
    source.unlink()  # recovery must not require the original source again

    repaired = AssetIngestService(
        store=store,
        resolver=resolver,
        source_policy=SourcePathPolicy((source_root,)),
    ).ingest(request(job.job_id, source, "recover-key"))
    assert repaired.operation.status == "COMPLETED"
    assert repaired.asset.asset_id == assets[0].asset_id
    assert resolver.resolve(repaired.source_manifest_uri).exists()


def test_missing_registered_file_can_be_repaired_by_same_checksum_ingest(tmp_path):
    service, _store, resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "a.wav"; write_wav(source)
    first = service.ingest(request(job.job_id, source, "k1"))
    target = resolver.resolve(first.asset.logical_uri); assert isinstance(target, Path)
    target.chmod(target.stat().st_mode | stat.S_IWUSR)
    target.unlink()
    second = service.ingest(request(job.job_id, source, "k2"))
    assert second.asset.asset_id == first.asset.asset_id
    assert second.repaired_existing_file
    assert target.exists()


def test_source_manifest_versions_are_immutable_history(tmp_path):
    service, store, resolver, source_root, *_rest, job = make_service(tmp_path)
    a = source_root / "a.wav"; b = source_root / "b.wav"
    write_wav(a, frames=100); write_wav(b, frames=200)
    first = service.ingest(request(job.job_id, a, "k1"))
    first_path = resolver.resolve(first.source_manifest_uri); first_bytes = first_path.read_bytes()
    second = service.ingest(request(job.job_id, b, "k2"))
    assert first_path.read_bytes() == first_bytes
    assert json.loads(first_bytes)["payload"]["asset_count"] == 1
    assert json.loads(resolver.resolve(second.source_manifest_uri).read_bytes())["payload"]["asset_count"] == 2
    assert store.latest_manifest(job.job_id, "source-manifest").version == 2


def test_unknown_rights_asset_is_registered_but_flagged_for_review(tmp_path):
    service, _store, resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "unknown.wav"; write_wav(source)
    result = service.ingest(request(
        job.job_id, source, rights_status=RightsStatus.UNKNOWN,
        commercial_use=PermissionState.UNKNOWN,
        derivative_allowed=PermissionState.UNKNOWN,
        reuse_allowed=PermissionState.UNKNOWN,
        audio_rights_status=AudioRightsStatus.REVIEW,
    ))
    assert not result.asset.auto_use_allowed
    manifest = json.loads(resolver.resolve(result.source_manifest_uri).read_text())
    assert result.asset.asset_id in manifest["payload"]["rights_review_asset_ids"]


def test_object_storage_mapping_and_cross_job_scope_guard(tmp_path):
    service, _store, resolver, source_root, *_rest, job = make_service(tmp_path)
    del service, source_root
    uri = f"asset://{job.job_id}/source/x.wav"
    assert resolver.resolve(uri, environment="object") == f"s3://bucket/assets/{job.job_id}/source/x.wav"
    other = generate_id(IdKind.JOB)
    with pytest.raises(ProductError):
        resolver.assert_job_scope(f"asset://{other}/source/x.wav", job.job_id)


def test_v1_database_migrates_additively_and_preserves_legacy_asset(tmp_path):
    db = tmp_path / "legacy.sqlite3"
    job_id = generate_id(IdKind.JOB); ps = generate_id(IdKind.PROFILE_SNAPSHOT); asset_id = generate_id(IdKind.ASSET)
    checksum = "sha256:" + "a" * 64
    with sqlite3.connect(db) as conn:
        conn.executescript("""
        CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
        CREATE TABLE production_jobs(job_id TEXT PRIMARY KEY,state TEXT NOT NULL,state_version INTEGER NOT NULL,profile_snapshot_id TEXT NOT NULL,resume_to_state TEXT,last_error_code TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE assets(asset_id TEXT PRIMARY KEY,job_id TEXT NOT NULL REFERENCES production_jobs(job_id),type TEXT NOT NULL,logical_uri TEXT NOT NULL,checksum TEXT NOT NULL,rights_status TEXT NOT NULL,owner TEXT NOT NULL,retention_class TEXT NOT NULL,human_lock INTEGER NOT NULL,UNIQUE(job_id,logical_uri,checksum));
        CREATE TABLE asset_versions(asset_version_id TEXT PRIMARY KEY,asset_id TEXT NOT NULL REFERENCES assets(asset_id),version INTEGER NOT NULL,checksum TEXT NOT NULL,producer_operation_id TEXT,UNIQUE(asset_id,version));
        """)
        conn.execute("INSERT INTO schema_migrations VALUES(1,'2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO production_jobs VALUES(?,?,?,?,NULL,NULL,?,?)", (job_id,"CREATED",1,ps,"2026-01-01T00:00:00Z","2026-01-01T00:00:00Z"))
        conn.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?)", (asset_id,job_id,"AUDIO",f"asset://{job_id}/source/legacy.wav",checksum,"OWNED","USER","STANDARD",0))
        conn.execute("INSERT INTO asset_versions VALUES(?,?,?,?,NULL)", (generate_id(IdKind.ASSET_VERSION),asset_id,1,checksum))
    store = SQLiteProductStore(db)
    assert store.schema_versions() == (1, 2)
    asset = store.get_asset(asset_id)
    assert asset.asset_id == asset_id
    assert asset.reuse_allowed is PermissionState.ALLOWED
    assert asset.commercial_use is PermissionState.UNKNOWN


def test_idempotency_key_cannot_be_rebound_to_other_command(tmp_path):
    _service, store, _resolver, _source_root, *_rest, job = make_service(tmp_path)
    store.reserve_operation(job.job_id, "ASSET_INGEST", "same")
    with pytest.raises(ProductError) as exc:
        store.reserve_operation(job.job_id, "OTHER_COMMAND", "same")
    assert exc.value.code == "ERR_INTEGRITY_IDEMPOTENCY_COMMAND_CONFLICT"


def test_denied_source_path_does_not_advance_job_state(tmp_path):
    service, store, _resolver, _source_root, *_rest, job = make_service(tmp_path)
    outside = tmp_path / "outside-denied.wav"; write_wav(outside)
    with pytest.raises(ProductError):
        service.ingest(request(job.job_id, outside, "denied"))
    assert store.get_job_state(job.job_id).state.value == "CREATED"


def test_completed_idempotent_replay_is_valid_after_job_advances(tmp_path):
    from ai_video_production import JobStateService, ProductionJobState
    service, store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "a.wav"; write_wav(source)
    first = service.ingest(request(job.job_id, source, "advance-replay"))
    snap = store.get_job_state(job.job_id)
    JobStateService(store).transition(job.job_id, ProductionJobState.NORMALIZING, expected_version=snap.state_version)
    source.unlink()
    replay = service.ingest(request(job.job_id, source, "advance-replay"))
    assert replay.asset.asset_id == first.asset.asset_id
    assert replay.operation.operation_id == first.operation.operation_id




def test_timestamp_only_source_metadata_drift_revalidates_content_and_succeeds(tmp_path, monkeypatch):
    service, store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "fresh-windows-like.wav"
    write_wav(source)

    real_fstat = os.fstat
    calls = 0

    def fstat_with_one_timestamp_drift(fd):
        nonlocal calls
        snapshot = real_fstat(fd)
        calls += 1
        if calls == 2:
            class DriftedStat:
                st_mode = snapshot.st_mode
                st_size = snapshot.st_size
                st_mtime_ns = snapshot.st_mtime_ns + 1
            return DriftedStat()
        return snapshot

    monkeypatch.setattr("ai_video_production.ingest.os.fstat", fstat_with_one_timestamp_drift)
    result = service.ingest(request(job.job_id, source, "timestamp-drift"))

    assert result.operation.status == "COMPLETED"
    assert len(store.list_assets(job.job_id)) == 1
    assert calls >= 4  # before/after plus same-handle content revalidation


def test_timestamp_drift_with_content_revalidation_mismatch_still_fails_closed(tmp_path, monkeypatch):
    service, store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "mutated.wav"
    write_wav(source)

    real_fstat = os.fstat
    calls = 0

    def fstat_with_one_timestamp_drift(fd):
        nonlocal calls
        snapshot = real_fstat(fd)
        calls += 1
        if calls == 2:
            class DriftedStat:
                st_mode = snapshot.st_mode
                st_size = snapshot.st_size
                st_mtime_ns = snapshot.st_mtime_ns + 1
            return DriftedStat()
        return snapshot

    monkeypatch.setattr("ai_video_production.ingest.os.fstat", fstat_with_one_timestamp_drift)
    monkeypatch.setattr(service, "_hash_open_source_fd", lambda _fd: ("sha256:" + "0" * 64, source.stat().st_size))

    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, source, "timestamp-drift-mismatch"))

    assert exc.value.code == "ERR_INPUT_SOURCE_CHANGED_DURING_INGEST"
    assert exc.value.category.value == "DATA_INTEGRITY"
    assert exc.value.details["reason"] == "CONTENT_REVALIDATION_MISMATCH"
    assert store.list_assets(job.job_id) == ()


def test_empty_source_asset_is_rejected(tmp_path):
    service, store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "empty.bin"; source.write_bytes(b"")
    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, source, asset_type=AssetType.OTHER))
    assert exc.value.code == "ERR_INPUT_EMPTY_ASSET"
    assert store.list_assets(job.job_id) == ()


def test_concurrent_ingests_reserve_distinct_manifest_revisions_and_latest_never_rolls_back(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from ai_video_production import JobStateService, ProductionJobState

    service, store, resolver, source_root, *_rest, job = make_service(tmp_path)
    snap = store.get_job_state(job.job_id)
    JobStateService(store).transition(job.job_id, ProductionJobState.INGESTING, expected_version=snap.state_version)
    a = source_root / "a.wav"; b = source_root / "b.wav"
    write_wav(a, frames=111); write_wav(b, frames=222)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: service.ingest(request(job.job_id, pair[0], pair[1])), [(a,"ca"),(b,"cb")]))
    assert len({r.asset.asset_id for r in results}) == 2
    latest = store.latest_manifest(job.job_id, "source-manifest")
    assert latest is not None and latest.version == 2 and latest.status == "COMMITTED"
    latest_path = resolver.resolve(f"job://{job.job_id}/manifests/source-manifest.json")
    latest_doc = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest_doc["revision"] == 2
    assert latest_doc["payload"]["asset_count"] == 2
    with sqlite3.connect(store.path) as conn:
        rows = conn.execute("SELECT version,status FROM manifests WHERE job_id=? AND type='source-manifest' ORDER BY version", (job.job_id,)).fetchall()
    assert rows == [(1,"COMMITTED"),(2,"COMMITTED")]


def test_pending_manifest_reservation_is_not_exposed_as_latest(tmp_path):
    _service, store, _resolver, _source_root, *_rest, job = make_service(tmp_path)
    op = store.reserve_operation(job.job_id, "ASSET_INGEST", "pending-manifest")[0]
    reservation = store.reserve_manifest(
        job_id=job.job_id,
        manifest_type="source-manifest",
        schema_version="1.0.0",
        operation_id=op.operation_id,
        uri_pattern=f"job://{job.job_id}/manifests/source-manifest/v{{version:06d}}.json",
    )
    assert reservation.status == "PENDING"
    assert store.latest_manifest(job.job_id, "source-manifest") is None
    store.fail_manifest(reservation.manifest_id)
    assert store.latest_manifest(job.job_id, "source-manifest") is None


def test_source_manifest_reserves_revision_before_taking_asset_snapshot(tmp_path, monkeypatch):
    service, store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "order.wav"; write_wav(source)
    events = []
    original_reserve = store.reserve_manifest
    original_list = store.list_assets

    def reserve_spy(**kwargs):
        events.append("reserve")
        return original_reserve(**kwargs)

    def list_spy(job_id):
        events.append("list")
        return original_list(job_id)

    monkeypatch.setattr(store, "reserve_manifest", reserve_spy)
    monkeypatch.setattr(store, "list_assets", list_spy)
    service.ingest(request(job.job_id, source, "order"))
    assert events.index("reserve") < events.index("list")


def test_crash_recovery_uses_asset_version_operation_binding_without_original_source(tmp_path):
    from ai_video_production import AssetRecord
    service, store, resolver, source_root, *_rest, job = make_service(tmp_path)
    # Simulate a process dying after Asset Registry commit but before operation
    # status/result_ref and source-manifest completion.
    snap = store.get_job_state(job.job_id)
    from ai_video_production import JobStateService, ProductionJobState
    JobStateService(store).transition(job.job_id, ProductionJobState.INGESTING, expected_version=snap.state_version)
    op = store.reserve_operation(job.job_id, "ASSET_INGEST", "crash-bound")[0]
    store.update_operation_status(op.operation_id, "IN_PROGRESS", increment_attempt=True)
    from ai_video_production.serialization import sha256_bytes
    data = b"persisted"
    checksum = sha256_bytes(data)
    logical = f"asset://{job.job_id}/source/{checksum.removeprefix('sha256:')}.bin"
    target = resolver.resolve(logical); assert isinstance(target, Path)
    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    asset = AssetRecord(job.job_id, AssetType.OTHER, logical, checksum, RightsStatus.OWNED, "USER", original_name="lost.bin")
    store.register_asset(asset, producer_operation_id=op.operation_id)
    missing = source_root / "no-longer-present.bin"

    recovered = service.ingest(request(job.job_id, missing, "crash-bound", asset_type=AssetType.OTHER))
    assert recovered.asset.asset_id == asset.asset_id
    assert recovered.operation.status == "COMPLETED"
    assert resolver.resolve(recovered.source_manifest_uri).exists()


def test_source_free_recovery_refuses_registered_file_checksum_mismatch(tmp_path):
    from ai_video_production import AssetRecord, JobStateService, ProductionJobState
    from ai_video_production.serialization import sha256_bytes
    service, store, resolver, source_root, *_rest, job = make_service(tmp_path)
    snap = store.get_job_state(job.job_id)
    JobStateService(store).transition(job.job_id, ProductionJobState.INGESTING, expected_version=snap.state_version)
    op = store.reserve_operation(job.job_id, "ASSET_INGEST", "crash-bad")[0]
    store.update_operation_status(op.operation_id, "IN_PROGRESS", increment_attempt=True)
    good = b"good"
    checksum = sha256_bytes(good)
    logical = f"asset://{job.job_id}/source/{checksum.removeprefix('sha256:')}.bin"
    target = resolver.resolve(logical); assert isinstance(target, Path)
    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b"tampered")
    asset = AssetRecord(job.job_id, AssetType.OTHER, logical, checksum, RightsStatus.OWNED, "USER", original_name="lost.bin")
    store.register_asset(asset, producer_operation_id=op.operation_id)
    with pytest.raises(ProductError) as exc:
        service.ingest(request(job.job_id, source_root / "missing.bin", "crash-bad", asset_type=AssetType.OTHER))
    assert exc.value.code == "ERR_INTEGRITY_REGISTERED_ASSET_CHECKSUM_MISMATCH"
    failed_repair = store.get_operation(op.operation_id)
    assert failed_repair.status == "PARTIAL"
    assert failed_repair.result_ref == asset.asset_id
    assert failed_repair.last_error_code == "ERR_INTEGRITY_REGISTERED_ASSET_CHECKSUM_MISMATCH"


def test_task003_packaged_schema_resources_match_canonical_files():
    from importlib import resources
    for name in ["asset-record.schema.json", "source-manifest-payload.schema.json", "canonical-manifest-envelope.schema.json"]:
        canonical = (Path(__file__).parents[1] / "schemas" / name).read_text(encoding="utf-8")
        packaged = resources.files("ai_video_production").joinpath("schema_resources", name).read_text(encoding="utf-8")
        assert packaged == canonical


def test_asset_registry_extended_metadata_roundtrips_sqlite(tmp_path):
    from ai_video_production import ApprovedSegment, AssetRecord
    _service, store, _resolver, _source_root, *_rest, job = make_service(tmp_path)
    record = AssetRecord(
        job.job_id,
        AssetType.VIDEO,
        f"asset://{job.job_id}/source/meta.mp4",
        "sha256:" + "d" * 64,
        RightsStatus.LICENSED,
        "LICENSE_VENDOR",
        original_name="meta.mp4",
        commercial_use=PermissionState.ALLOWED,
        derivative_allowed=PermissionState.ALLOWED,
        reuse_allowed=PermissionState.ALLOWED,
        audio_rights_status=AudioRightsStatus.REPLACE,
        source_ref="contract:ABC-1",
        source_project="DBD_EQ_VIDEO",
        attribution="Example attribution",
        territory=("JP", "GLOBAL-WEB"),
        rights_valid_until="2027-12-31",
        publication_restrictions=("NO_PAID_ADS",),
        approved_segments=(ApprovedSegment(1_000_000, 2_000_000),),
        media_metadata={"duration_us": 3_000_000},
        generation_provenance={"kind": "LICENSED_SOURCE"},
        perceptual_hash="phash:abc",
        audio_fingerprint="afp:def",
    )
    store.register_asset(record)
    loaded = store.get_asset(record.asset_id)
    assert loaded.to_dict() == record.to_dict()
    assert not loaded.auto_use_allowed  # audio must be replaced before automatic whole-source reuse


def test_ffprobe_uses_fixed_argv_not_shell_for_metacharacter_filename(tmp_path):
    service, _store, _resolver, source_root, *_rest, job = make_service(tmp_path)
    source = source_root / "voice;touch SHOULD_NOT_EXIST.wav"
    write_wav(source)
    marker = source_root / "SHOULD_NOT_EXIST.wav"
    result = service.ingest(request(job.job_id, source, "shell-safe"))
    assert result.operation.status == "COMPLETED"
    assert not marker.exists()


def test_reference_ingest_cli_emits_logical_result_without_raw_source_path(tmp_path, capsys):
    from ai_video_production.ingest_cli import main
    source_root = tmp_path / "incoming"; asset_root = tmp_path / "assets"; job_root = tmp_path / "jobs"
    source_root.mkdir(); asset_root.mkdir(); job_root.mkdir()
    source = source_root / "cli.wav"; write_wav(source)
    db = tmp_path / "cli.sqlite3"
    store = SQLiteProductStore(db)
    ps = ProfileSnapshot.create("cli", "1.0.0", {})
    job = store.create_job(ps.profile_snapshot_id)
    rc = main([
        "--db", str(db), "--job-id", job.job_id, "--source", str(source),
        "--source-root", str(source_root), "--asset-root", str(asset_root), "--job-root", str(job_root),
        "--asset-type", "AUDIO", "--rights-status", "OWNED", "--owner", "USER", "--idempotency-key", "cli-1",
        "--commercial-use", "ALLOWED", "--derivative-allowed", "ALLOWED", "--audio-rights-status", "SAFE",
    ])
    captured = capsys.readouterr()
    assert rc == 0
    body = json.loads(captured.out)
    assert body["asset"]["logical_uri"].startswith(f"asset://{job.job_id}/source/")
    assert str(source) not in captured.out
