from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
import struct
import threading
import wave

import pytest

from ai_video_production.assets import AssetRecord, AssetType, RightsStatus
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.paths import LogicalPathResolver, PathMapping
from ai_video_production.store import SQLiteProductStore
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task098_product_review_binding import (
    Task098ProductReviewBindingSelector,
)
from ai_video_production.task098_review_media_runtime_windows import (
    RegistryBoundReviewMediaRuntimePort,
)
from ai_video_production.task098_review_shell_application import (
    Task098ReviewShellApplication,
)


JOB_ID = "JOB-" + "1" * 26
PROFILE_ID = "PSN-" + "2" * 26
ASSET_ID = "ASSET-" + "3" * 26
CANDIDATE_ID = "candidate-4"
H1 = "sha256:" + "a" * 64
H2 = "sha256:" + "b" * 64
NOW = "2026-09-23T00:00:00Z"


def _write_wav(path: Path, *, sample_rate: int = 48_000) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for index in range(96_000):
        frames.extend(struct.pack("<h", (index % 2_000) - 1_000))
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(frames)
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(
    tmp_path: Path,
    *,
    rights: RightsStatus = RightsStatus.OWNED,
    sample_rate: int = 48_000,
):
    asset_root = tmp_path / "assets"
    source = asset_root / JOB_ID / "source" / "review.wav"
    checksum = _write_wav(source, sample_rate=sample_rate)
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
    snapshot = {
        "project_id": "project-1",
        "production_snapshot_sha256": H1,
        "audio_snapshot_sha256": H2,
        "available_audio_candidates": [
            {
                "candidate_id": CANDIDATE_ID,
                "asset_id": ASSET_ID,
                "asset_sha256": checksum,
                "lifecycle_state": "ACCEPTED",
            }
        ],
    }
    selector = Task098ProductReviewBindingSelector(
        assets=store,
        resolver=LogicalPathResolver([PathMapping("asset://", asset_root)]),
        candidate_snapshot_provider=lambda: snapshot,
        project_id="project-1",
        production_job_id=JOB_ID,
        clock=lambda: NOW,
    )
    return selector, store, snapshot


def test_human_selection_builds_exact_body_free_binding_without_media_effect(tmp_path: Path):
    selector, store, _snapshot = _fixture(tmp_path)
    try:
        with pytest.raises(ProductError) as absent:
            selector()
        assert absent.value.code == "ERR_TASK098_REVIEW_CANDIDATE_NOT_SELECTED"

        result = selector.select(CANDIDATE_ID)
        binding = selector()
        request = binding.request()

        assert result == {
            "task_owner": "TASK-098",
            "selected": True,
            "candidate_id": CANDIDATE_ID,
            "canonical_state_changed": False,
            "wav_header_read": True,
            "audio_body_read": False,
            "playback_started": False,
            "waveform_render_started": False,
        }
        assert request.source_asset_id == ASSET_ID
        assert request.source_content_sha256 == store.get_asset(ASSET_ID).checksum
        assert request.source_duration_samples == 96_000
        assert request.range_start_sample == 0
        assert request.range_end_sample_exclusive == 96_000
        assert binding.view_model.transcript_rows == ()
        assert binding.view_model.subtitle_rows == ()
        assert selector.is_ready() is True
    finally:
        selector.close()
        store.close()


def test_refresh_currentness_does_not_reopen_or_decode_selected_wav(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    selector, store, _snapshot = _fixture(tmp_path)
    calls = 0
    original = selector._inspect_wav_header

    def counted(asset: AssetRecord):
        nonlocal calls
        calls += 1
        return original(asset)

    monkeypatch.setattr(selector, "_inspect_wav_header", counted)
    try:
        selector.select(CANDIDATE_ID)
        assert calls == 1
        assert selector.is_ready() is True
        assert selector().request() == selector().request()
        assert calls == 1
    finally:
        selector.close()
        store.close()


def test_candidate_or_workspace_change_makes_process_local_selection_stale(tmp_path: Path):
    selector, store, snapshot = _fixture(tmp_path)
    try:
        selector.select(CANDIDATE_ID)
        snapshot["audio_snapshot_sha256"] = "sha256:" + "c" * 64

        assert selector.is_ready() is False
        with pytest.raises(ProductError) as stale:
            selector()
        assert stale.value.code == "ERR_TASK098_REVIEW_SELECTION_STALE"
    finally:
        selector.close()
        store.close()


def test_selection_rejects_forged_candidate_and_non_reviewable_rights(tmp_path: Path):
    selector, store, _snapshot = _fixture(tmp_path / "owned")
    blocked, blocked_store, _blocked_snapshot = _fixture(
        tmp_path / "blocked", rights=RightsStatus.BLOCKED
    )
    wrong_rate, wrong_rate_store, _wrong_rate_snapshot = _fixture(
        tmp_path / "wrong-rate", sample_rate=44_100
    )
    try:
        with pytest.raises(ProductError) as forged:
            selector.select("candidate-5")
        assert forged.value.code == "ERR_TASK098_REVIEW_CANDIDATE_NOT_CURRENT"

        with pytest.raises(ProductError) as denied:
            blocked.select(CANDIDATE_ID)
        assert denied.value.code == "ERR_TASK098_REVIEW_ASSET_NOT_CURRENT"

        with pytest.raises(ProductError) as unsupported:
            wrong_rate.select(CANDIDATE_ID)
        assert unsupported.value.code == "ERR_TASK098_REVIEW_WAV_NOT_SUPPORTED"
    finally:
        selector.close()
        blocked.close()
        wrong_rate.close()
        store.close()
        blocked_store.close()
        wrong_rate_store.close()


def test_shell_selection_enables_existing_confirmed_runtime_without_auto_execution(
    tmp_path: Path,
):
    selector, store, snapshot = _fixture(tmp_path)

    class Playback:
        def __init__(self) -> None:
            self.play_calls = 0

        def play(self, wav_body: bytes, cancel_event: threading.Event) -> None:
            assert not cancel_event.is_set()
            with wave.open(BytesIO(wav_body), "rb") as source:
                assert source.getframerate() == 48_000
                assert source.getnframes() == 96_000
            self.play_calls += 1

        def stop(self) -> None:
            pass

    playback = Playback()
    application = Task098ReviewShellApplication(
        binding_provider=selector,
        runtime=RegistryBoundReviewMediaRuntimePort(
            assets=store,
            resolver=selector._resolver,
            playback=playback,
        ),
        monotonic=lambda: 100.0,
        identity=lambda: "selection-confirmation",
    )
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.24.3"),
        review_workspace_application=application,
        review_workspace_selector=selector,
    )
    try:
        assert "universal_wav_review" not in bridge.view_model()
        selected = bridge.universal_wav_review_select({"candidate_id": CANDIDATE_ID})
        assert selected["selected"] is True
        assert playback.play_calls == 0
        assert bridge.view_model()["universal_wav_review"]["capabilities"]["audition"] is True

        prepared = bridge.universal_wav_review_prepare({})
        assert playback.play_calls == 0
        result = bridge.universal_wav_review_apply(
            {"confirmation_id": prepared["confirmation_id"]}
        )
        assert result["runtime_state"] == "SUCCEEDED"
        assert result["canonical_receipt_created"] is False
        assert result["review_completion_claimed"] is False
        assert playback.play_calls == 1

        # Simulate the narrow race where currentness changes after the first
        # readiness check but before projection.  Only the optional review
        # surface disappears; the Product ViewModel remains available.
        snapshot["audio_snapshot_sha256"] = "sha256:" + "c" * 64
        selector.is_ready = lambda: True
        assert "universal_wav_review" not in bridge.view_model()
    finally:
        application.close()
        selector.close()
        store.close()
