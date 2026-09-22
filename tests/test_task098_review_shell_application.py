from __future__ import annotations

from io import BytesIO
import math
from pathlib import Path
import struct
import threading
import wave

import pytest

from ai_video_production import audio_workspace_media_review as review
from ai_video_production.assets import AssetRecord, AssetType, RightsStatus
from ai_video_production.derived_assets import sha256_file
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.paths import LogicalPathResolver, PathMapping
from ai_video_production.store import SQLiteProductStore
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task098_review_media_runtime_windows import (
    RegistryBoundReviewMediaRuntimePort,
)
from ai_video_production.task098_review_shell_application import (
    MAX_SHELL_WAVEFORM_POINTS,
    Task098ReviewShellApplication,
    Task098ReviewShellBinding,
)
from ai_video_production.task098_review_workspace_contract import ReviewViewport
from ai_video_production.task098_review_workspace_coordinator import ReviewWorkspaceViewModel


NOW = "2026-09-22T00:00:00Z"
JOB_ID = "JOB-" + "0" * 26
PROFILE_ID = "PSN-" + "0" * 26
ASSET_ID = "ASSET-" + "1" * 26
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64


class CapturingPlayback:
    def __init__(self) -> None:
        self.play_calls = 0
        self.stop_calls = 0

    def play(self, wav_body: bytes, cancel_event: threading.Event) -> None:
        assert not cancel_event.is_set()
        with wave.open(BytesIO(wav_body), "rb") as source:
            assert source.getframerate() == 48_000
            assert source.getnframes() == 4_800
        self.play_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for index in range(9_600):
        sample = int(12_000 * math.sin(2 * math.pi * 440 * index / 48_000))
        frames.extend(struct.pack("<h", sample))
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(48_000)
        target.writeframes(frames)


def _binding(checksum: str, *, revision: int = 1) -> Task098ReviewShellBinding:
    policy = review.AudioMediaReviewPolicyRevision.create(
        policy_id="policy:task098:a6-r1", revision=1,
        parent_record_sha256=None, required_sample_rate_hz=48_000,
        max_review_duration_samples=9_600, max_observation_age_seconds=3600,
        official_policy_ref="policy:official:1", official_policy_sha256=H1,
        effective_at=NOW, expires_at=None, audio_read_started=False,
        media_mutation_started=False,
    )
    source = review.AudioMediaSourceBinding.create(
        source_id="source:task098:a6-r1", media_kind="AUDIO_ASSET",
        contract_state="BOUND_VERIFIED", canonical_ref=f"asset-revision:{revision}",
        canonical_sha256=checksum, canonical_revision=revision,
        candidate_id="candidate:1", asset_id=ASSET_ID, rights_state="PASS",
        sample_rate_hz=48_000, channel_count=1, duration_samples=9_600,
        observed_at=NOW, body_included=False, absolute_path_included=False,
    )
    capability = review.PlaybackWaveformCapabilityBinding.create(
        capability_id="capability:task098:a6-r1", contract_state="BOUND_VERIFIED",
        player_state="SUPPORTED", waveform_state="SUPPORTED", decode_state="SUPPORTED",
        sample_accurate_range_state="SUPPORTED", capability_profile_ref="profile:a6-r1",
        capability_profile_sha256=H1, app_identity_sha256=H2, observed_at=NOW,
        body_included=False, absolute_path_included=False,
    )
    intent = review.AudioMediaReviewIntent.create(
        intent_id=f"intent:task098:a6-r1:{revision}", revision=1,
        parent_record_sha256=None, project_id="project:1",
        policy_sha256=policy.record_sha256, source_binding_sha256=source.record_sha256,
        capability_binding_sha256=capability.record_sha256,
        audio_workspace_snapshot_sha256=H2,
        requested_operations=["AUDITION", "WAVEFORM_VIEW"],
        range_start_sample=2_400, range_end_sample=7_200, requested_at=NOW,
        body_included=False, absolute_path_included=False,
        playback_started=False, waveform_render_started=False, media_mutation_started=False,
    )
    view = ReviewWorkspaceViewModel(
        source_binding_sha256=source.record_sha256, source_asset_id=ASSET_ID,
        source_candidate_id="candidate:1", intent_sha256=intent.record_sha256,
        intent_id=f"intent:task098:a6-r1:{revision}", transcript_manifest_sha256=H1,
        workspace_id="workspace.a6-r1", workspace_revision=revision,
        workspace_snapshot_sha256=H2, transcript_rows=(), subtitle_rows=(),
        viewport=ReviewViewport(9_600, 2_400, 4_800, 0, 0, 1),
    )
    return Task098ReviewShellBinding(policy, source, capability, intent, view, NOW)


def _application(tmp_path: Path):
    asset_root = tmp_path / "assets"
    source_path = asset_root / JOB_ID / "source" / "review.wav"
    _write_wav(source_path)
    checksum = sha256_file(source_path)
    store = SQLiteProductStore(tmp_path / "product.sqlite3")
    store.create_job(PROFILE_ID, job_id=JOB_ID)
    store.register_asset(
        AssetRecord(
            production_job_id=JOB_ID, asset_type=AssetType.AUDIO,
            logical_uri=f"asset://{JOB_ID}/source/review.wav", checksum=checksum,
            rights_status=RightsStatus.OWNED, owner="task098-test-owner", asset_id=ASSET_ID,
        )
    )
    playback = CapturingPlayback()
    current = [_binding(checksum)]
    tokens = iter(("confirmation-a", "confirmation-b", "confirmation-c"))
    app = Task098ReviewShellApplication(
        binding_provider=lambda: current[0],
        runtime=RegistryBoundReviewMediaRuntimePort(
            assets=store,
            resolver=LogicalPathResolver([PathMapping("asset://", asset_root)]),
            playback=playback,
        ),
        monotonic=lambda: 100.0,
        identity=lambda: next(tokens),
    )
    return app, playback, current, store


def test_prepare_is_effect_zero_and_apply_returns_only_bounded_ephemeral_envelope(tmp_path) -> None:
    app, playback, _current, store = _application(tmp_path)
    try:
        prepared = app.prepare()
        assert playback.play_calls == 0
        assert set(prepared) == {
            "task_owner", "confirmation_id", "status_label", "warning",
            "expires_in_seconds",
        }
        result = app.apply(prepared["confirmation_id"])
        assert playback.play_calls == 1
        assert result["runtime_state"] == "SUCCEEDED"
        assert result["playback_observed"] is True
        assert result["waveform_observed"] is True
        assert 0 < len(result["waveform_envelope_milli"]) <= MAX_SHELL_WAVEFORM_POINTS
        assert all(0 <= value <= 1_000 for value in result["waveform_envelope_milli"])
        for flag in (
            "canonical_receipt_created", "review_completion_claimed",
            "review_state_persisted", "human_decision_authorized",
            "media_mutation_started", "audio_body_exposed", "private_identity_exposed",
        ):
            assert result[flag] is False
        serialized = repr(result).lower()
        for forbidden in (ASSET_ID.lower(), "sha256:", "review.wav", "asset://"):
            assert forbidden not in serialized
    finally:
        store.close()


def test_confirmation_is_cancelable_one_use_and_stale_binding_fails_closed(tmp_path) -> None:
    app, playback, current, store = _application(tmp_path)
    try:
        cancelled = app.prepare()
        assert app.cancel(cancelled["confirmation_id"])["media_effect_started"] is False
        with pytest.raises(ProductError) as reused:
            app.apply(cancelled["confirmation_id"])
        assert reused.value.code == "ERR_TASK098_REVIEW_CONFIRMATION_EXPIRED"

        stale = app.prepare()
        current[0] = _binding(current[0].source.to_dict()["canonical_sha256"], revision=2)
        with pytest.raises(ProductError) as changed:
            app.apply(stale["confirmation_id"])
        assert changed.value.code == "ERR_TASK098_REVIEW_BINDING_STALE"
        assert playback.play_calls == 0
        with pytest.raises(ProductError):
            app.apply(stale["confirmation_id"])
    finally:
        store.close()


def test_shell_binds_runtime_capabilities_and_exact_human_routes(tmp_path) -> None:
    app, playback, _current, store = _application(tmp_path)
    shell = ShellApplicationService(product_version="0.24.3")
    bridge = Task036ShellBridge(shell, review_workspace_application=app)
    try:
        model = bridge.view_model()
        assert playback.play_calls == 0
        assert model["universal_wav_review"]["capabilities"]["audition"] is True
        assert model["universal_wav_review"]["capabilities"]["waveform_render"] is True
        prepared = bridge.universal_wav_review_prepare({})
        result = bridge.universal_wav_review_apply(
            {"confirmation_id": prepared["confirmation_id"]}
        )
        assert result["runtime_state"] == "SUCCEEDED"
        for invalid in ({}, {"confirmation_id": "x", "path": "C:/private.wav"}):
            with pytest.raises(ProductError) as rejected:
                bridge.universal_wav_review_apply(invalid)
            assert rejected.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    finally:
        store.close()


def test_close_invalidates_pending_confirmation_before_store_lifetime_ends(tmp_path) -> None:
    app, playback, _current, store = _application(tmp_path)
    try:
        prepared = app.prepare()
        app.close()
        with pytest.raises(ProductError) as rejected:
            app.apply(prepared["confirmation_id"])
        assert rejected.value.code == "ERR_TASK098_REVIEW_RUNTIME_CLOSED"
        with pytest.raises(ProductError) as view_rejected:
            app.view_model()
        assert view_rejected.value.code == "ERR_TASK098_REVIEW_RUNTIME_CLOSED"
        assert playback.play_calls == 0
    finally:
        store.close()


def test_confirmation_identity_failure_and_malformed_tokens_are_closed(tmp_path) -> None:
    app, _playback, current, store = _application(tmp_path)
    broken = Task098ReviewShellApplication(
        binding_provider=lambda: current[0],
        runtime=app._runtime,
        identity=lambda: (_ for _ in ()).throw(RuntimeError("private detail")),
    )
    try:
        with pytest.raises(ProductError) as identity_error:
            broken.prepare()
        assert identity_error.value.code == "ERR_TASK098_REVIEW_CONFIRMATION_INVALID"
        assert "private detail" not in str(identity_error.value)
        for invalid in ("", " ", "../private", "x" * 129):
            with pytest.raises(ProductError) as malformed:
                app.apply(invalid)
            assert malformed.value.code == "ERR_TASK098_REVIEW_CONFIRMATION_INVALID"
    finally:
        store.close()
