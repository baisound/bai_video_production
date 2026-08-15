from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.audio_placement import AudioPlacementRequest, AudioPlacementRole, AudioPlacementService, BedMode
from ai_video_production.audio_placement_store import (
    AudioPlacementCompilationRecord,
    AudioPlacementHistory,
    AudioPlacementHistoryStore,
)
from ai_video_production.errors import ProductError
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SHA = "sha256:" + "a" * 64


def record(*, project_id: str = "project-1") -> AudioPlacementCompilationRecord:
    plan = AudioPlacementService.compile(AudioPlacementRequest(
        asset_id="asset-1", role=AudioPlacementRole.BGM, track_index=2,
        source_duration_frames=100, desired_start_frame=0, desired_duration_frames=200,
        loop=True, bed_mode=BedMode.FULL,
    ))
    body = {
        "project_id": project_id, "review_id": "review-1",
        "audio_snapshot_sha256": SHA, "production_snapshot_sha256": SHA,
        "timeline_snapshot_sha256": SHA, "slot_id": "slot-1",
        "candidate_id": "candidate-1", "asset_id": "asset-1", "asset_sha256": SHA,
        "timeline_plan_id": "timeline-1", "timeline_revision": 1,
        "timeline_plan_sha256": SHA, "timeline_item_id": "music-1",
        "timeline_item_sha256": SHA, "track_index": 2, "bed_mode": "FULL",
        "task026_plan_sha256": plan.to_dict()["plan_sha256"],
    }
    return AudioPlacementCompilationRecord(
        compilation_id=AudioPlacementCompilationRecord.derive_compilation_id(body),
        project_id=project_id, source_project_revision=3,
        source_project_manifest_sha256=SHA, review_id="review-1",
        placement_decision="ACCEPT", audio_snapshot_sha256=SHA,
        production_snapshot_sha256=SHA, timeline_snapshot_sha256=SHA,
        slot_id="slot-1", candidate_id="candidate-1", asset_id="asset-1",
        asset_sha256=SHA, timeline_plan_id="timeline-1", timeline_revision=1,
        timeline_plan_sha256=SHA, timeline_item_id="music-1",
        timeline_item_sha256=SHA, track_index=2, bed_mode=BedMode.FULL, plan=plan,
    )


def test_history_round_trip_and_exact_idempotency() -> None:
    history = AudioPlacementHistory("project-1")
    value = record()
    assert history.append(value) is True
    assert history.append(value) is False
    loaded = AudioPlacementHistoryStore.parse_bytes(
        AudioPlacementHistoryStore.serialize(history), expected_project_id="project-1"
    )
    assert loaded.store_revision == 1
    assert loaded.records == {value.compilation_id: value}


def test_history_rejects_checksum_authority_and_unknown_fields() -> None:
    history = AudioPlacementHistory("project-1"); history.append(record())
    document = AudioPlacementHistoryStore.snapshot(history)
    for mutate in (
        lambda value: value.update({"unknown": True}),
        lambda value: value.update({"provider_execution_authority": True}),
        lambda value: value["records"][0].update({"task010_execution_started": True}),
    ):
        changed = json.loads(json.dumps(document)); mutate(changed)
        body = {key: value for key, value in changed.items() if key != "snapshot_sha256"}
        changed["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
        with pytest.raises(ProductError):
            AudioPlacementHistoryStore.parse(changed)


def test_history_rejects_project_mismatch_and_noncanonical_plan() -> None:
    history = AudioPlacementHistory("project-1"); history.append(record())
    with pytest.raises(ProductError, match="another Project"):
        AudioPlacementHistoryStore.parse_bytes(
            AudioPlacementHistoryStore.serialize(history), expected_project_id="project-2"
        )
    document = AudioPlacementHistoryStore.snapshot(history)
    document["records"][0]["task026_plan"]["track_index"] = 3
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    document["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ProductError, match="invalid compilation"):
        AudioPlacementHistoryStore.parse(document)


def test_history_rejects_duplicate_identity_and_boolean_integer_fields() -> None:
    history = AudioPlacementHistory("project-1"); history.append(record())
    document = AudioPlacementHistoryStore.snapshot(history)
    document["records"].append(json.loads(json.dumps(document["records"][0])))
    document["store_revision"] = 1
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    document["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ProductError, match="invalid compilation"):
        AudioPlacementHistoryStore.parse(document)

    document = AudioPlacementHistoryStore.snapshot(history)
    document["records"][0]["task026_plan"]["track_index"] = True
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    document["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ProductError, match="invalid compilation"):
        AudioPlacementHistoryStore.parse(document)


def test_schema_is_valid_and_packaged_copy_is_equivalent() -> None:
    public = Path(__file__).parents[1] / "schemas/audio-placement-history.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", public.name)
    public_document = json.loads(public.read_text(encoding="utf-8"))
    assert public_document == json.loads(packaged.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(public_document)
    history = AudioPlacementHistory("project-1"); history.append(record())
    Draft202012Validator(public_document).validate(AudioPlacementHistoryStore.snapshot(history))
