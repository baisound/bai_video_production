from __future__ import annotations

import os
from pathlib import Path
import shutil
import wave

import pytest

from ai_video_production import audio_workspace_media_review as review
from ai_video_production.assets import AssetRecord, AssetType, RightsStatus
from ai_video_production.derived_assets import sha256_file
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.paths import LogicalPathResolver, PathMapping
from ai_video_production.store import SQLiteProductStore
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task098_review_media_runtime_windows import (
    RegistryBoundReviewMediaRuntimePort,
    WindowsWavePlaybackBackend,
)
from ai_video_production.task098_review_shell_application import (
    Task098ReviewShellApplication,
    Task098ReviewShellBinding,
)
from ai_video_production.task098_review_workspace_contract import ReviewViewport
from ai_video_production.task098_review_workspace_coordinator import ReviewWorkspaceViewModel


EXPECTED_SOURCE_SHA256 = (
    "sha256:c356ff98f7e7ec6b574da03af8cf4b812a200fef35f75bde30f0128d2ff84899"
)
JOB_ID = "JOB-" + "0" * 26
PROFILE_ID = "PSN-" + "0" * 26
ASSET_ID = "ASSET-" + "1" * 26
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
NOW = "2026-09-22T00:00:00Z"


def _binding() -> Task098ReviewShellBinding:
    policy = review.AudioMediaReviewPolicyRevision.create(
        policy_id="policy:task098:a6-native", revision=1,
        parent_record_sha256=None, required_sample_rate_hz=48_000,
        max_review_duration_samples=48_000, max_observation_age_seconds=3600,
        official_policy_ref="policy:official:1", official_policy_sha256=H1,
        effective_at=NOW, expires_at=None, audio_read_started=False,
        media_mutation_started=False,
    )
    source = review.AudioMediaSourceBinding.create(
        source_id="source:task098:a6-native", media_kind="AUDIO_ASSET",
        contract_state="BOUND_VERIFIED", canonical_ref="asset-revision:1",
        canonical_sha256=EXPECTED_SOURCE_SHA256, canonical_revision=1,
        candidate_id="candidate:1", asset_id=ASSET_ID, rights_state="PASS",
        sample_rate_hz=48_000, channel_count=1, duration_samples=290_159,
        observed_at=NOW, body_included=False, absolute_path_included=False,
    )
    capability = review.PlaybackWaveformCapabilityBinding.create(
        capability_id="capability:task098:a6-native",
        contract_state="BOUND_VERIFIED", player_state="SUPPORTED",
        waveform_state="SUPPORTED", decode_state="SUPPORTED",
        sample_accurate_range_state="SUPPORTED",
        capability_profile_ref="profile:a6-native",
        capability_profile_sha256=H1, app_identity_sha256=H2,
        observed_at=NOW, body_included=False, absolute_path_included=False,
    )
    intent = review.AudioMediaReviewIntent.create(
        intent_id="intent:task098:a6-native", revision=1,
        parent_record_sha256=None, project_id="project:a6-native",
        policy_sha256=policy.record_sha256,
        source_binding_sha256=source.record_sha256,
        capability_binding_sha256=capability.record_sha256,
        audio_workspace_snapshot_sha256=H2,
        requested_operations=["AUDITION", "WAVEFORM_VIEW"],
        range_start_sample=0, range_end_sample=48_000, requested_at=NOW,
        body_included=False, absolute_path_included=False,
        playback_started=False, waveform_render_started=False,
        media_mutation_started=False,
    )
    view = ReviewWorkspaceViewModel(
        source_binding_sha256=source.record_sha256, source_asset_id=ASSET_ID,
        source_candidate_id="candidate:1", intent_sha256=intent.record_sha256,
        intent_id="intent:task098:a6-native", transcript_manifest_sha256=H1,
        workspace_id="workspace.a6-native", workspace_revision=1,
        workspace_snapshot_sha256=H2, transcript_rows=(), subtitle_rows=(),
        viewport=ReviewViewport(290_159, 0, 48_000, 0, 0, 1),
    )
    return Task098ReviewShellBinding(policy, source, capability, intent, view, NOW)


@pytest.mark.skipif(os.name != "nt", reason="Windows-native audio device acceptance")
def test_a6_human_shell_route_plays_private_canonical_asset_and_returns_ephemeral_waveform(
    tmp_path: Path,
) -> None:
    source_value = os.environ.get("BVP_TASK098_PRIVATE_WAV")
    if not source_value:
        pytest.skip("BVP_TASK098_PRIVATE_WAV is not supplied")
    source = Path(source_value)
    assert source.is_file() and not source.is_symlink()
    assert sha256_file(source) == EXPECTED_SOURCE_SHA256
    with wave.open(str(source), "rb") as handle:
        assert (
            handle.getframerate(), handle.getnchannels(), handle.getsampwidth(),
            handle.getnframes(), handle.getcomptype(),
        ) == (48_000, 1, 3, 290_159, "NONE")

    asset_root = tmp_path / "task098-a6-native" / "assets"
    canonical_copy = asset_root / JOB_ID / "source" / "reference.wav"
    canonical_copy.parent.mkdir(parents=True)
    shutil.copyfile(source, canonical_copy)
    assert sha256_file(canonical_copy) == EXPECTED_SOURCE_SHA256

    store = SQLiteProductStore(tmp_path / "task098-a6-native" / "product.sqlite3")
    store.create_job(PROFILE_ID, job_id=JOB_ID)
    store.register_asset(
        AssetRecord(
            production_job_id=JOB_ID, asset_type=AssetType.AUDIO,
            logical_uri=f"asset://{JOB_ID}/source/reference.wav",
            checksum=EXPECTED_SOURCE_SHA256, rights_status=RightsStatus.OWNED,
            owner="task098-a6-native", asset_id=ASSET_ID,
        )
    )
    app = Task098ReviewShellApplication(
        binding_provider=_binding,
        runtime=RegistryBoundReviewMediaRuntimePort(
            assets=store,
            resolver=LogicalPathResolver([PathMapping("asset://", asset_root)]),
            playback=WindowsWavePlaybackBackend(),
        ),
        identity=lambda: "a6-native-human-confirmation",
    )
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.24.3"),
        review_workspace_application=app,
    )
    try:
        view = bridge.view_model()
        assert view["universal_wav_review"]["capabilities"]["audition"] is True
        prepared = bridge.universal_wav_review_prepare({})
        result = bridge.universal_wav_review_apply(
            {"confirmation_id": prepared["confirmation_id"]}
        )
        assert result["runtime_state"] == "SUCCEEDED"
        assert result["playback_observed"] is True
        assert result["waveform_observed"] is True
        assert len(result["waveform_envelope_milli"]) == 2_048
        assert result["canonical_receipt_created"] is False
        assert result["review_completion_claimed"] is False
        assert result["review_state_persisted"] is False
        assert result["human_decision_authorized"] is False
        assert result["media_mutation_started"] is False
    finally:
        store.close()
