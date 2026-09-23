from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
import os
from pathlib import Path
import struct
import threading
import wave

import pytest

from ai_video_production import audio_workspace_media_review as review
from ai_video_production.assets import AssetRecord, AssetType, RightsStatus
from ai_video_production.derived_assets import sha256_file
from ai_video_production.paths import LogicalPathResolver, PathMapping
from ai_video_production.store import SQLiteProductStore
from ai_video_production.task098_review_media_runtime_contract import (
    ReviewMediaRuntimeRequest,
    ReviewMediaRuntimeState,
    build_review_media_runtime_request,
    reduce_review_media_runtime,
)
from ai_video_production.task098_review_media_runtime_windows import (
    RegistryBoundReviewMediaRuntimePort,
    ReviewRuntimeCancelled,
    ReviewRuntimeDisconnected,
    ReviewRuntimeKnownFailure,
    WindowsWavePlaybackBackend,
)
from ai_video_production.task098_review_workspace_contract import ReviewViewport
from ai_video_production.task098_review_workspace_coordinator import (
    ReviewWorkspaceViewModel,
)


NOW = "2026-09-22T00:00:00Z"
JOB_ID = "JOB-" + "0" * 26
PROFILE_ID = "PSN-" + "0" * 26
ASSET_ID = "ASSET-" + "1" * 26
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64


class CapturingPlayback:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int, int]] = []
        self.stop_calls = 0

    def play(self, wav_body: bytes, cancel_event: threading.Event) -> None:
        assert not cancel_event.is_set()
        with wave.open(BytesIO(wav_body), "rb") as source:
            self.calls.append(
                (
                    source.getframerate(),
                    source.getnchannels(),
                    source.getsampwidth(),
                    source.getnframes(),
                )
            )

    def stop(self) -> None:
        self.stop_calls += 1


class TerminalPlayback(CapturingPlayback):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error

    def play(self, wav_body: bytes, cancel_event: threading.Event) -> None:
        del wav_body, cancel_event
        raise self.error


class BlockingPlayback(CapturingPlayback):
    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()

    def play(self, wav_body: bytes, cancel_event: threading.Event) -> None:
        del wav_body
        self.started.set()
        if not cancel_event.wait(2):
            raise ReviewRuntimeDisconnected()
        raise ReviewRuntimeCancelled()


class CleanupFailurePlayback(CapturingPlayback):
    def stop(self) -> None:
        raise RuntimeError("synthetic cleanup failure")


@dataclass(slots=True)
class RuntimeFixture:
    store: SQLiteProductStore
    resolver: LogicalPathResolver
    request: ReviewMediaRuntimeRequest
    source_path: Path


def _write_wav(
    path: Path,
    *,
    sample_rate_hz: int = 48_000,
    frame_count: int = 4_800,
    channels: int = 2,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for index in range(frame_count):
        sample = int(800 * math.sin(2 * math.pi * 440 * index / sample_rate_hz))
        for _ in range(channels):
            frames.extend(struct.pack("<h", sample))
    with wave.open(str(path), "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(2)
        target.setframerate(sample_rate_hz)
        target.writeframes(frames)


def _policy() -> review.AudioMediaReviewPolicyRevision:
    return review.AudioMediaReviewPolicyRevision.create(
        policy_id="policy:task098:a4-r2b",
        revision=1,
        parent_record_sha256=None,
        required_sample_rate_hz=48_000,
        max_review_duration_samples=4_800,
        max_observation_age_seconds=3600,
        official_policy_ref="policy:official:1",
        official_policy_sha256=H1,
        effective_at=NOW,
        expires_at=None,
        audio_read_started=False,
        media_mutation_started=False,
    )


def _source(checksum: str) -> review.AudioMediaSourceBinding:
    return review.AudioMediaSourceBinding.create(
        source_id="source:task098:a4-r2b",
        media_kind="AUDIO_ASSET",
        contract_state="BOUND_VERIFIED",
        canonical_ref="asset-revision:1",
        canonical_sha256=checksum,
        canonical_revision=1,
        candidate_id="candidate:1",
        asset_id=ASSET_ID,
        rights_state="PASS",
        sample_rate_hz=48_000,
        channel_count=2,
        duration_samples=4_800,
        observed_at=NOW,
        body_included=False,
        absolute_path_included=False,
    )


def _capability() -> review.PlaybackWaveformCapabilityBinding:
    return review.PlaybackWaveformCapabilityBinding.create(
        capability_id="capability:task098:a4-r2b",
        contract_state="BOUND_VERIFIED",
        player_state="SUPPORTED",
        waveform_state="SUPPORTED",
        decode_state="SUPPORTED",
        sample_accurate_range_state="SUPPORTED",
        capability_profile_ref="profile:a4-r2b",
        capability_profile_sha256=H1,
        app_identity_sha256=H2,
        observed_at=NOW,
        body_included=False,
        absolute_path_included=False,
    )


def _request(
    checksum: str,
    *,
    operations: list[str] | None = None,
) -> ReviewMediaRuntimeRequest:
    policy = _policy()
    source = _source(checksum)
    capability = _capability()
    intent = review.AudioMediaReviewIntent.create(
        intent_id="intent:task098:a4-r2b",
        revision=1,
        parent_record_sha256=None,
        project_id="project:1",
        policy_sha256=policy.record_sha256,
        source_binding_sha256=source.record_sha256,
        capability_binding_sha256=capability.record_sha256,
        audio_workspace_snapshot_sha256=H2,
        requested_operations=operations or ["AUDITION", "WAVEFORM_VIEW"],
        range_start_sample=480,
        range_end_sample=2_400,
        requested_at=NOW,
        body_included=False,
        absolute_path_included=False,
        playback_started=False,
        waveform_render_started=False,
        media_mutation_started=False,
    )
    view = ReviewWorkspaceViewModel(
        source_binding_sha256=source.record_sha256,
        source_asset_id=ASSET_ID,
        source_candidate_id="candidate:1",
        intent_sha256=intent.record_sha256,
        intent_id="intent:task098:a4-r2b",
        transcript_manifest_sha256=H1,
        workspace_id="workspace.a4-r2b",
        workspace_revision=1,
        workspace_snapshot_sha256=H2,
        transcript_rows=(),
        subtitle_rows=(),
        viewport=ReviewViewport(4_800, 480, 1_920, 0, 0, 1),
    )
    return build_review_media_runtime_request(
        policy=policy,
        source=source,
        capability=capability,
        intent=intent,
        view_model=view,
        evaluated_at=NOW,
    )


def _fixture(
    tmp_path: Path,
    *,
    actual_rate_hz: int = 48_000,
    rights: RightsStatus = RightsStatus.OWNED,
    declared_checksum: str | None = None,
    operations: list[str] | None = None,
) -> RuntimeFixture:
    asset_root = tmp_path / "assets"
    source_path = asset_root / JOB_ID / "source" / "review.wav"
    _write_wav(source_path, sample_rate_hz=actual_rate_hz)
    actual_checksum = sha256_file(source_path)
    checksum = actual_checksum if declared_checksum is None else declared_checksum
    store = SQLiteProductStore(tmp_path / "product.sqlite3")
    store.create_job(PROFILE_ID, job_id=JOB_ID)
    store.register_asset(
        AssetRecord(
            production_job_id=JOB_ID,
            asset_type=AssetType.AUDIO,
            logical_uri=f"asset://{JOB_ID}/source/review.wav",
            checksum=checksum,
            rights_status=rights,
            owner="task098-test-owner",
            asset_id=ASSET_ID,
        )
    )
    return RuntimeFixture(
        store=store,
        resolver=LogicalPathResolver([PathMapping("asset://", asset_root)]),
        request=_request(checksum, operations=operations),
        source_path=source_path,
    )


def test_concrete_port_resolves_exact_asset_range_and_process_local_waveform(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    playback = CapturingPlayback()
    port = RegistryBoundReviewMediaRuntimePort(
        assets=fixture.store,
        resolver=fixture.resolver,
        playback=playback,
    )
    observation = port.execute(fixture.request)
    status = reduce_review_media_runtime(fixture.request, observation)
    assert status.state is ReviewMediaRuntimeState.SUCCEEDED
    assert status.playback_observed is True
    assert status.waveform_observed is True
    assert status.waveform_point_count == 1_920
    assert playback.calls == [(48_000, 2, 2, 1_920)]
    public = status.to_public_dict()
    serialized = repr(public).lower()
    assert "path" not in serialized
    assert "sha256" not in serialized
    assert fixture.request.source_content_sha256 not in serialized
    fixture.store.close()


def test_waveform_only_does_not_allocate_playback(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, operations=["WAVEFORM_VIEW"])
    playback = CapturingPlayback()
    port = RegistryBoundReviewMediaRuntimePort(
        assets=fixture.store,
        resolver=fixture.resolver,
        playback=playback,
    )
    observation = port.execute(fixture.request)
    assert observation.state is ReviewMediaRuntimeState.SUCCEEDED
    assert observation.playback_observed is False
    assert observation.waveform_observed is True
    assert playback.calls == []
    fixture.store.close()


@pytest.mark.parametrize(
    ("rights", "declared_checksum", "actual_rate_hz"),
    [
        (RightsStatus.BLOCKED, None, 48_000),
        (RightsStatus.OWNED, H1, 48_000),
        (RightsStatus.OWNED, None, 44_100),
    ],
)
def test_registry_rights_checksum_and_wav_rate_drift_fail_before_playback(
    tmp_path: Path,
    rights: RightsStatus,
    declared_checksum: str | None,
    actual_rate_hz: int,
) -> None:
    fixture = _fixture(
        tmp_path,
        rights=rights,
        declared_checksum=declared_checksum,
        actual_rate_hz=actual_rate_hz,
    )
    playback = CapturingPlayback()
    result = RegistryBoundReviewMediaRuntimePort(
        assets=fixture.store,
        resolver=fixture.resolver,
        playback=playback,
    ).execute(fixture.request)
    assert result.state is ReviewMediaRuntimeState.FAILED_KNOWN
    assert result.reason_codes == ("RUNTIME_FAILED",)
    assert playback.calls == []
    fixture.store.close()


def test_decoded_range_cap_fails_closed(monkeypatch, tmp_path: Path) -> None:
    from ai_video_production import task098_review_media_runtime_windows as runtime

    fixture = _fixture(tmp_path)
    monkeypatch.setattr(runtime, "MAX_DECODED_RANGE_BYTES", 16)
    playback = CapturingPlayback()
    result = RegistryBoundReviewMediaRuntimePort(
        assets=fixture.store,
        resolver=fixture.resolver,
        playback=playback,
    ).execute(fixture.request)
    assert result.state is ReviewMediaRuntimeState.FAILED_KNOWN
    assert playback.calls == []
    fixture.store.close()


@pytest.mark.parametrize(
    ("error", "state", "reason"),
    [
        (
            ReviewRuntimeCancelled(),
            ReviewMediaRuntimeState.CANCELLED_SAFE,
            "CANCELLED_BY_RUNTIME",
        ),
        (
            ReviewRuntimeDisconnected(),
            ReviewMediaRuntimeState.UNKNOWN_AFTER_DISCONNECT,
            "RUNTIME_DISCONNECTED",
        ),
        (
            ReviewRuntimeKnownFailure(),
            ReviewMediaRuntimeState.FAILED_KNOWN,
            "RUNTIME_FAILED",
        ),
    ],
)
def test_playback_terminal_outcomes_never_become_success(
    tmp_path: Path,
    error: Exception,
    state: ReviewMediaRuntimeState,
    reason: str,
) -> None:
    fixture = _fixture(tmp_path, operations=["AUDITION"])
    result = RegistryBoundReviewMediaRuntimePort(
        assets=fixture.store,
        resolver=fixture.resolver,
        playback=TerminalPlayback(error),
    ).execute(fixture.request)
    assert result.state is state
    assert result.reason_codes == (reason,)
    assert result.playback_observed is False
    assert result.waveform_observed is False
    fixture.store.close()


def test_cancel_owns_stop_and_returns_cancelled_safe(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, operations=["AUDITION"])
    playback = BlockingPlayback()
    port = RegistryBoundReviewMediaRuntimePort(
        assets=fixture.store,
        resolver=fixture.resolver,
        playback=playback,
    )
    results = []
    worker = threading.Thread(target=lambda: results.append(port.execute(fixture.request)))
    worker.start()
    assert playback.started.wait(2)
    assert port.cancel() is True
    worker.join(2)
    assert not worker.is_alive()
    assert len(results) == 1
    assert results[0].state is ReviewMediaRuntimeState.CANCELLED_SAFE
    assert playback.stop_calls >= 2
    assert port.cancel() is False
    fixture.store.close()


def test_cleanup_failure_is_unknown_not_success(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, operations=["AUDITION"])
    result = RegistryBoundReviewMediaRuntimePort(
        assets=fixture.store,
        resolver=fixture.resolver,
        playback=CleanupFailurePlayback(),
    ).execute(fixture.request)
    assert result.state is ReviewMediaRuntimeState.UNKNOWN_AFTER_DISCONNECT
    assert result.reason_codes == ("RUNTIME_DISCONNECTED",)
    fixture.store.close()


def test_windows_backend_collects_non_os_worker_exception(monkeypatch) -> None:
    class BrokenWinsound:
        SND_MEMORY = 1
        SND_NODEFAULT = 4

        @staticmethod
        def PlaySound(body, flags):
            del body, flags
            raise ValueError("synthetic worker failure")

    monkeypatch.setattr(
        WindowsWavePlaybackBackend,
        "_winsound",
        staticmethod(lambda: BrokenWinsound),
    )
    with pytest.raises(ReviewRuntimeKnownFailure, match="native playback failed"):
        WindowsWavePlaybackBackend().play(b"not-empty", threading.Event())


def test_port_and_request_accept_no_host_path(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    assert not any("path" in name for name in fixture.request.__dataclass_fields__)
    assert fixture.request.source_content_sha256 == sha256_file(fixture.source_path)
    assert not hasattr(RegistryBoundReviewMediaRuntimePort, "execute_path")
    fixture.store.close()


@pytest.mark.skipif(
    os.name != "nt" or os.environ.get("BVP_TASK098_NATIVE_AUDIO") != "1",
    reason="explicit Windows-native audio device acceptance",
)
def test_windows_native_backend_plays_bounded_synthetic_canonical_asset(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path, operations=["AUDITION", "WAVEFORM_VIEW"])
    result = RegistryBoundReviewMediaRuntimePort(
        assets=fixture.store,
        resolver=fixture.resolver,
        playback=WindowsWavePlaybackBackend(),
    ).execute(fixture.request)
    assert result.state is ReviewMediaRuntimeState.SUCCEEDED
    assert result.playback_observed is True
    assert result.waveform_observed is True
    fixture.store.close()
