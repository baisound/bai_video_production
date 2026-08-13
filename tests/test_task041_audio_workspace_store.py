from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.audio_workspace import (
    AudioCandidateDecision,
    AudioDecisionKind,
    AudioDerivationType,
    AudioDerivedAsset,
    AudioSlotKind,
    AudioWorkspaceRegistry,
    PlacementDecision,
    PlacementReview,
)
from ai_video_production.audio_workspace_store import AudioWorkspaceSnapshotStore
from ai_video_production.errors import ProductError
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SHA1 = "sha256:" + "1" * 64
SHA2 = "sha256:" + "2" * 64


def registry() -> AudioWorkspaceRegistry:
    value = AudioWorkspaceRegistry()
    value.add_decision(AudioCandidateDecision("decision-1", "candidate-1", AudioSlotKind.VFX_EMBEDDED_AUDIO, AudioDecisionKind.STRIP_AUDIO, "owner"))
    value.add_derived_asset(AudioDerivedAsset("asset-no-audio", "asset-original", SHA1, SHA2, AudioDerivationType.AUDIO_STRIPPED_VIDEO))
    value.add_placement(PlacementReview("review-1", "candidate-1", 100, 48, "SE", PlacementDecision.ACCEPT, -6.0))
    return value


def test_audio_snapshot_round_trip_preserves_non_destructive_policy(tmp_path: Path):
    path = tmp_path / "audio.json"
    AudioWorkspaceSnapshotStore.save(path, registry())
    loaded = AudioWorkspaceSnapshotStore.load(path)
    assert loaded.decisions["decision-1"].decision is AudioDecisionKind.STRIP_AUDIO
    assert loaded.derived_assets["asset-no-audio"].source_asset_id == "asset-original"
    assert loaded.accepted_placements()[0].gain_db == -6.0


def test_audio_snapshot_boundary_flags_are_fail_closed(tmp_path: Path):
    path = tmp_path / "audio.json"
    doc = AudioWorkspaceSnapshotStore.snapshot(registry())
    doc["destructive_source_write_authority"] = True
    body = {k: v for k, v in doc.items() if k != "snapshot_sha256"}
    doc["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        AudioWorkspaceSnapshotStore.load(path)
    assert exc.value.code == "ERR_AUDIO_SNAPSHOT_BOUNDARY"


def test_existing_audio_snapshot_requires_compare_and_swap(tmp_path: Path):
    path = tmp_path / "audio.json"
    value = registry()
    AudioWorkspaceSnapshotStore.save(path, value)
    with pytest.raises(ProductError) as exc:
        AudioWorkspaceSnapshotStore.save(path, value)
    assert exc.value.code == "ERR_AUDIO_SNAPSHOT_CAS_REQUIRED"


def test_audio_snapshot_tamper_checksum_is_detected(tmp_path: Path):
    path = tmp_path / "audio.json"
    AudioWorkspaceSnapshotStore.save(path, registry())
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["placements"][0]["gain_db"] = 3.0
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        AudioWorkspaceSnapshotStore.load(path)
    assert exc.value.code == "ERR_AUDIO_SNAPSHOT_CHECKSUM"
