from __future__ import annotations

import json
from pathlib import Path, PureWindowsPath
import subprocess
import wave

import pytest

from ai_video_production import (
    AssetIngestRequest, AssetIngestService, AssetType, AudioRightsStatus, FrameRate, FrameRounding,
    JobStateService, LogicalPathResolver, MediaNormalizationService, NormalizationProfile, NormalizationRequest,
    PathMapping, PermissionState, ProductError, ProductionJobState, ProfileSnapshot, RightsStatus,
    SQLiteProductStore, SourcePathPolicy, TimingKind,
)
from ai_video_production.timebase import FFprobeTimingProbe


def make_env(tmp_path: Path):
    source_root = tmp_path / "incoming"; source_root.mkdir()
    asset_root = tmp_path / "assets"; asset_root.mkdir()
    job_root = tmp_path / "jobs"; job_root.mkdir()
    store = SQLiteProductStore(tmp_path / "product.sqlite3")
    profile = ProfileSnapshot.create("task004", "1.0.0", {})
    job = store.create_job(profile.profile_snapshot_id)
    resolver = LogicalPathResolver([
        PathMapping("asset://", asset_root, PureWindowsPath("D:/AI/assets")),
        PathMapping("job://", job_root, PureWindowsPath("D:/AI/jobs")),
    ])
    ingest = AssetIngestService(store=store, resolver=resolver, source_policy=SourcePathPolicy((source_root,)))
    return store, resolver, ingest, source_root, job


def write_wav(path: Path, rate: int = 8000, frames: int = 8000):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate); out.writeframes(b"\x00\x00" * frames)


def ingest_audio(tmp_path: Path):
    store, resolver, ingest, source_root, job = make_env(tmp_path)
    source = source_root / "voice.wav"; write_wav(source)
    result = ingest.ingest(AssetIngestRequest(
        job.job_id, source, AssetType.AUDIO, RightsStatus.OWNED, "USER", "ingest-a",
        commercial_use=PermissionState.ALLOWED, derivative_allowed=PermissionState.ALLOWED,
        reuse_allowed=PermissionState.ALLOWED, audio_rights_status=AudioRightsStatus.SAFE,
    ))
    return store, resolver, source, job, result.asset


@pytest.mark.parametrize("rate,expected", [("30000/1001", (30000,1001)), ("24000/1001", (24000,1001)), ("25",(25,1)), ("60/2",(30,1))])
def test_frame_rate_parse_is_exact(rate, expected):
    r = FrameRate.parse(rate)
    assert (r.numerator, r.denominator) == expected


def test_ntsc_frame_time_roundtrip_uses_rational_math():
    rate = FrameRate(30000, 1001)
    us = rate.frame_to_us(1001, rounding=FrameRounding.NEAREST)
    assert us == 33_400_033
    assert rate.us_to_frame(us, rounding=FrameRounding.NEAREST) == 1001


def test_rounding_modes_are_explicit():
    rate = FrameRate(3, 1)
    assert rate.frame_to_us(1, rounding=FrameRounding.FLOOR) == 333_333
    assert rate.frame_to_us(1, rounding=FrameRounding.CEIL) == 333_334
    assert rate.frame_to_us(1, rounding=FrameRounding.NEAREST) == 333_333


@pytest.mark.parametrize("value", ["0/1", "1/0", "0/0", "abc", "29.97"])
def test_invalid_or_float_frame_rate_is_not_silently_accepted(value):
    with pytest.raises(ValueError):
        FrameRate.parse(value)


def test_timing_probe_classifies_audio_only(tmp_path):
    path = tmp_path / "a.wav"; write_wav(path)
    result = FFprobeTimingProbe().inspect(path)
    assert result.kind is TimingKind.AUDIO_ONLY
    assert result.sampled_packet_count == 0


def test_timing_probe_uses_bounded_packet_read(monkeypatch, tmp_path):
    seen = []
    class P:
        returncode=0; stderr=""
        def __init__(self, stdout): self.stdout=stdout
    def fake_run(argv, **kwargs):
        seen.append(argv)
        if "-show_packets" in argv:
            return P(json.dumps({"packets": [{"pts_time": f"{i/30:.6f}"} for i in range(500)]}))
        return P(json.dumps({"streams":[{"avg_frame_rate":"30/1","r_frame_rate":"30/1","time_base":"1/90000"}],"format":{"duration":"20"}}))
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = FFprobeTimingProbe(max_packets=20, sample_seconds=3).inspect(tmp_path / "does-not-matter.mp4")
    assert result.sampled_packet_count == 20
    assert any("%+3" in call for argv in seen for call in argv)
    assert all(kwargs is not None for kwargs in [seen])


def test_timing_probe_marks_avg_nominal_disagreement_vfr(monkeypatch, tmp_path):
    class P:
        returncode=0; stderr=""
        def __init__(self, stdout): self.stdout=stdout
    docs = iter([
        {"streams":[{"avg_frame_rate":"30000/1001","r_frame_rate":"30/1","time_base":"1/90000"}],"format":{"duration":"1"}},
        {"packets":[{"pts_time":"0"},{"pts_time":"0.033367"}]},
    ])
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: P(json.dumps(next(docs))))
    result = FFprobeTimingProbe().inspect(tmp_path / "x.mp4")
    assert result.kind is TimingKind.VFR
    assert "differs" in result.reason


def test_timing_probe_marks_variable_pts_vfr(monkeypatch, tmp_path):
    class P:
        returncode=0; stderr=""
        def __init__(self, stdout): self.stdout=stdout
    docs = iter([
        {"streams":[{"avg_frame_rate":"30/1","r_frame_rate":"30/1","time_base":"1/90000"}],"format":{"duration":"1"}},
        {"packets":[{"pts_time":"0"},{"pts_time":"0.033333"},{"pts_time":"0.100000"}]},
    ])
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: P(json.dumps(next(docs))))
    assert FFprobeTimingProbe(delta_tolerance_us=1000).inspect(tmp_path / "x.mp4").kind is TimingKind.VFR


def test_normalize_audio_creates_48k_asset_manifest_and_state(tmp_path):
    store, resolver, source, job, asset = ingest_audio(tmp_path)
    before = source.read_bytes()
    result = MediaNormalizationService(store=store, resolver=resolver).normalize(NormalizationRequest(job.job_id, asset.asset_id, "norm-1"))
    assert result.operation.status == "COMPLETED"
    assert result.analysis_audio_asset is not None
    assert result.proxy_asset is None and result.video_reference_asset is None
    assert result.analysis_audio_asset.media_metadata["streams"][0]["sample_rate"] == 48000
    assert store.get_job_state(job.job_id).state is ProductionJobState.NORMALIZING
    assert source.read_bytes() == before
    manifest = resolver.resolve(result.manifest_uri); assert isinstance(manifest, Path)
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc["payload"]["lane"] == "TIMEBASE_NORMALIZATION"
    assert doc["payload"]["details"]["analysis_audio_asset_id"] == result.analysis_audio_asset.asset_id


def test_normalization_idempotent_replay_does_not_create_revision(tmp_path):
    store, resolver, _source, job, asset = ingest_audio(tmp_path)
    service = MediaNormalizationService(store=store, resolver=resolver)
    first = service.normalize(NormalizationRequest(job.job_id, asset.asset_id, "same"))
    second = service.normalize(NormalizationRequest(job.job_id, asset.asset_id, "same"))
    assert second.operation.operation_id == first.operation.operation_id
    assert second.analysis_audio_asset.asset_id == first.analysis_audio_asset.asset_id
    assert store.latest_manifest(job.job_id, "normalization-manifest").version == 1


def test_normalization_rejects_source_checksum_tamper(tmp_path):
    store, resolver, _source, job, asset = ingest_audio(tmp_path)
    target = resolver.resolve(asset.logical_uri); assert isinstance(target, Path)
    target.chmod(0o600); target.write_bytes(b"tampered")
    with pytest.raises(ProductError) as exc:
        MediaNormalizationService(store=store, resolver=resolver).normalize(NormalizationRequest(job.job_id, asset.asset_id, "tamper"))
    assert exc.value.code == "ERR_INTEGRITY_SOURCE_ASSET_CHECKSUM_MISMATCH"


def test_denied_derivative_is_rejected_before_state_transition(tmp_path):
    store, resolver, ingest, source_root, job = make_env(tmp_path)
    source = source_root / "voice.wav"; write_wav(source)
    asset = ingest.ingest(AssetIngestRequest(job.job_id, source, AssetType.AUDIO, RightsStatus.LICENSED, "VENDOR", "i",
        derivative_allowed=PermissionState.DENIED)).asset
    assert store.get_job_state(job.job_id).state is ProductionJobState.INGESTING
    with pytest.raises(ProductError) as exc:
        MediaNormalizationService(store=store, resolver=resolver).normalize(NormalizationRequest(job.job_id, asset.asset_id, "n"))
    assert exc.value.code == "ERR_POLICY_DERIVATIVE_DENIED"
    assert store.get_job_state(job.job_id).state is ProductionJobState.INGESTING


def test_forced_proxy_real_ffmpeg_is_cfr_and_48k(tmp_path):
    store, resolver, ingest, source_root, job = make_env(tmp_path)
    source = source_root / "clip.mp4"
    subprocess.run([
        "ffmpeg","-nostdin","-hide_banner","-loglevel","error","-f","lavfi","-i","testsrc=size=160x90:rate=24:duration=1",
        "-f","lavfi","-i","sine=frequency=440:sample_rate=44100:duration=1","-c:v","mpeg4","-c:a","aac","-shortest","-y",str(source)
    ], check=True)
    asset = ingest.ingest(AssetIngestRequest(job.job_id, source, AssetType.VIDEO, RightsStatus.OWNED, "USER", "v",
        commercial_use=PermissionState.ALLOWED, derivative_allowed=PermissionState.ALLOWED, audio_rights_status=AudioRightsStatus.SAFE)).asset
    result = MediaNormalizationService(store=store, resolver=resolver).normalize(NormalizationRequest(
        job.job_id, asset.asset_id, "proxy", NormalizationProfile(target_frame_rate=FrameRate(30000,1001), force_cfr_proxy=True, max_duration_drift_us=200_000)
    ))
    assert result.proxy_asset is not None
    assert result.analysis_audio_asset is not None
    timing = FFprobeTimingProbe().inspect(resolver.resolve(result.proxy_asset.logical_uri))
    assert timing.kind is TimingKind.CFR
    assert (timing.avg_frame_rate or timing.nominal_frame_rate) == FrameRate(30000,1001)


def test_normalization_cli_contract_has_no_raw_source_path(tmp_path, capsys):
    from ai_video_production.normalization_cli import main
    store, resolver, _source, job, asset = ingest_audio(tmp_path)
    # resolver roots from helper are deterministic child directories
    rc = main(["--db", str(store.path), "--job-id", job.job_id, "--source-asset-id", asset.asset_id,
               "--asset-root", str(tmp_path/"assets"), "--job-root", str(tmp_path/"jobs"), "--idempotency-key", "cli"])
    assert rc == 0
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "COMPLETED"
    assert "incoming" not in json.dumps(body)


def test_proxy_qa_failure_does_not_publish_analysis_audio_partial_batch(tmp_path):
    from ai_video_production.timebase import TimingInspection
    store, resolver, ingest, source_root, job = make_env(tmp_path)
    source = source_root / "clip-batch.mp4"
    subprocess.run([
        "ffmpeg","-nostdin","-hide_banner","-loglevel","error","-f","lavfi","-i","testsrc=size=160x90:rate=24:duration=1",
        "-f","lavfi","-i","sine=frequency=440:sample_rate=44100:duration=1","-c:v","mpeg4","-c:a","aac","-shortest","-y",str(source)
    ], check=True)
    asset = ingest.ingest(AssetIngestRequest(
        job.job_id, source, AssetType.VIDEO, RightsStatus.OWNED, "USER", "batch-v",
        commercial_use=PermissionState.ALLOWED, derivative_allowed=PermissionState.ALLOWED,
        reuse_allowed=PermissionState.ALLOWED, audio_rights_status=AudioRightsStatus.SAFE,
    )).asset
    real = FFprobeTimingProbe()
    class FailingProxyTiming:
        def __init__(self): self.calls = 0
        def inspect(self, path):
            self.calls += 1
            if self.calls == 1:
                return real.inspect(path)
            return TimingInspection(TimingKind.VFR, 1_000_000, FrameRate(30,1), FrameRate(30,1), "1/90000", 2, 1, 1, 33333, 66666, "forced test failure")
    service = MediaNormalizationService(store=store, resolver=resolver, timing_probe=FailingProxyTiming())
    with pytest.raises(ProductError) as exc:
        service.normalize(NormalizationRequest(
            job.job_id, asset.asset_id, "batch-fail",
            NormalizationProfile(target_frame_rate=FrameRate(30000,1001), force_cfr_proxy=True, max_duration_drift_us=200_000),
        ))
    assert exc.value.code == "ERR_INTEGRITY_NORMALIZED_PROXY_NOT_CFR"
    assert [a.asset_id for a in store.list_assets(job.job_id)] == [asset.asset_id]


def test_completed_normalization_replay_rejects_tampered_manifest(tmp_path):
    store, resolver, _source, job, asset = ingest_audio(tmp_path)
    service = MediaNormalizationService(store=store, resolver=resolver)
    result = service.normalize(NormalizationRequest(job.job_id, asset.asset_id, "manifest-tamper"))
    path = resolver.resolve(result.manifest_uri); assert isinstance(path, Path)
    path.chmod(0o600)
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        service.normalize(NormalizationRequest(job.job_id, asset.asset_id, "manifest-tamper"))
    assert exc.value.code == "ERR_INTEGRITY_TASK004_MANIFEST_CHECKSUM"
