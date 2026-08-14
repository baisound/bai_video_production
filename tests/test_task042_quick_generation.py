from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.quick_generation import (
    QuickGenerationIntent, QuickGenerationMode, QuickGenerationRegistry,
    QuickReferenceInput, QuickReferenceRole, QuickReferenceSource,
)
from ai_video_production.quick_generation_store import QuickGenerationSnapshotStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


H = lambda ch: "sha256:" + ch * 64


def reference(role=QuickReferenceRole.GENERAL, source=QuickReferenceSource.ASSET_LIBRARY, *, suffix="1"):
    locked = role in {QuickReferenceRole.CHARACTER_LOCK, QuickReferenceRole.SPACE_LOCK, QuickReferenceRole.COMPOSITION_LOCK}
    return QuickReferenceInput(
        f"ref-{suffix}", source, role, f"asset-{suffix}", H(suffix),
        f"slot-{suffix}" if locked or source is QuickReferenceSource.GENERATION_RESULT else None,
        f"candidate-{suffix}" if locked or source is QuickReferenceSource.GENERATION_RESULT else None,
    )


def intent(*, expected_quick=H("3"), mode=QuickGenerationMode.IMAGE, refs=()):
    capabilities = ("AUDIO_REFERENCE", "GENERATE") if mode is QuickGenerationMode.AUDIO and refs else ("GENERATE",)
    return QuickGenerationIntent(
        "quick-1", 1, "project-1", "scene-1", mode, "slot-target",
        "prompt-1", 1, H("a"), H("b"), "profile-1", "v1", H("c"),
        "route-1", "GENERATE", capabilities, tuple(refs), "rights://owner/1",
        "USD", "0", "decision-1", H("d"), H("1"), H("2"), expected_quick,
    )


def test_quick_intent_never_claims_plan_go_execution_or_candidate_authority() -> None:
    row = intent(refs=(reference(),)).to_dict()
    assert row["authority_kind"] == "QUICK_INTENT"
    for key in ("approved_plan_used", "human_go_used", "provider_execution_started", "candidate_created", "media_write_started"):
        assert row[key] is False
    assert "plan_id" not in row
    assert row["references"][0]["host_path_embedded"] is False
    assert "C:/" not in json.dumps(row)


def test_mode_cardinality_and_file_ingest_boundaries_fail_closed() -> None:
    with pytest.raises(ValueError):
        intent(mode=QuickGenerationMode.VIDEO, refs=())
    with pytest.raises(ValueError):
        intent(mode=QuickGenerationMode.AUDIO, refs=(reference(QuickReferenceRole.AUDIO_REFERENCE), reference(QuickReferenceRole.AUDIO_REFERENCE, suffix="2")))
    with pytest.raises(ValueError):
        QuickReferenceInput("r", QuickReferenceSource.FILE, QuickReferenceRole.GENERAL, "asset", H("a"), "slot", "candidate")
    with pytest.raises(ValueError):
        reference(QuickReferenceRole.CHARACTER_LOCK, QuickReferenceSource.FILE)
    with pytest.raises(ValueError):
        intent(mode=QuickGenerationMode.START_END, refs=(
            reference(QuickReferenceRole.START, suffix="1"),
            reference(QuickReferenceRole.START, suffix="2"),
        ))


def test_quick_snapshot_append_chain_round_trips_and_unknown_fields_fail(tmp_path: Path) -> None:
    path = tmp_path / "quick.json"
    registry = QuickGenerationRegistry("project-1")
    empty_sha = QuickGenerationSnapshotStore.snapshot(registry)["snapshot_sha256"]
    registry.add_intent(intent(expected_quick=empty_sha))
    QuickGenerationSnapshotStore.save(path, registry)
    assert QuickGenerationSnapshotStore.load(path, project_id="project-1").intents == registry.intents

    document = json.loads(path.read_text(encoding="utf-8"))
    document["intents"][0]["unknown"] = True
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    document["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        QuickGenerationSnapshotStore.load(path, project_id="project-1")
    assert exc.value.code == "ERR_QUICK_SNAPSHOT_INVALID"


def test_quick_snapshot_foreign_project_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "quick.json"
    registry = QuickGenerationRegistry("project-1")
    QuickGenerationSnapshotStore.save(path, registry)
    with pytest.raises(ProductError) as exc:
        QuickGenerationSnapshotStore.load(path, project_id="project-2")
    assert exc.value.code == "ERR_QUICK_SNAPSHOT_INVALID"
