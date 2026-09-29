from __future__ import annotations

from dataclasses import replace
from importlib import resources
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver

from ai_video_production.errors import ProductError
from ai_video_production.reaper_audio_finishing import AudioRoundTripManifest
from ai_video_production.reaper_audio_finishing_store import (
    AudioRoundTripCurrentState,
    AudioRoundTripHistory,
    AudioRoundTripHistoryStore,
    RELATIVE_PATH,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64
H4 = "sha256:" + "4" * 64


def manifest(
    *,
    revision: int = 1,
    parent: str | None = None,
    project_id: str = "project:1",
    session_plan_sha256: str = H1,
) -> AudioRoundTripManifest:
    return AudioRoundTripManifest.create(
        manifest_id="roundtrip:1",
        revision=revision,
        parent_record_sha256=parent,
        project_id=project_id,
        session_plan_sha256=session_plan_sha256,
        project_snapshot_sha256=H2,
        execution_receipt_sha256=H3,
        rendered_asset_binding_hashes=[H1],
        qa_receipt_hashes=[],
        human_approval_sha256=None,
        resolve_placement_plan_sha256=None,
        round_trip_state="RENDER_CANDIDATE",
        reason_codes=[],
        untreated_source_preserved=True,
        asset_promotion_started=False,
        resolve_mutation_started=False,
        publication_started=False,
    )


def persisted_project(tmp_path: Path):
    history = AudioRoundTripHistory("project:1")
    first = manifest()
    history.append(first)
    result = AudioRoundTripHistoryStore.save_project(tmp_path, history)
    return history, first, result


def rehash(document: dict) -> None:
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    document["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))


def test_history_round_trip_selects_exact_latest_owner_head() -> None:
    history = AudioRoundTripHistory("project:1")
    first = manifest()
    assert history.append(first) is True
    assert history.append(first) is False
    second = manifest(revision=2, parent=first.record_sha256, session_plan_sha256=H4)
    assert history.append(second) is True
    loaded = AudioRoundTripHistoryStore.parse_bytes(
        AudioRoundTripHistoryStore.serialize(history), expected_project_id="project:1",
    )
    assert loaded.store_revision == 2
    assert loaded.current("roundtrip:1") == second


def test_fixed_project_store_and_current_read_are_effect_zero(tmp_path: Path) -> None:
    _, first, _ = persisted_project(tmp_path)
    assert (tmp_path / RELATIVE_PATH).is_file()
    result = AudioRoundTripHistoryStore.read_current(
        tmp_path,
        project_id="project:1",
        manifest_id="roundtrip:1",
        expected_session_plan_sha256=H1,
        expected_manifest_sha256=first.record_sha256,
    )
    assert result.state is AudioRoundTripCurrentState.CURRENT
    assert result.manifest == first
    assert result.owner_store_read is True
    assert result.owner_origin_authenticated is True
    assert result.currentness_verified is True
    public = result.to_dict()
    assert all(public[key] is False for key in (
        "audio_read_started", "external_execution_started", "reaper_launch_started",
        "audio_render_started", "asset_promotion_started", "resolve_mutation_started",
        "publication_started",
    ))
    assert "session_plan_sha256" not in public
    assert "project_snapshot_sha256" not in public
    assert "execution_receipt_sha256" not in public


def test_current_read_reports_session_and_head_drift(tmp_path: Path) -> None:
    _, _, _ = persisted_project(tmp_path)
    result = AudioRoundTripHistoryStore.read_current(
        tmp_path,
        project_id="project:1",
        manifest_id="roundtrip:1",
        expected_session_plan_sha256=H2,
        expected_manifest_sha256=H4,
    )
    assert result.state is AudioRoundTripCurrentState.STALE
    assert result.currentness_verified is False
    assert result.reason_codes == ("MANIFEST_HEAD_CHANGED", "SESSION_PLAN_CHANGED")


def test_persisted_current_read_selects_only_latest_manifest_revision(tmp_path: Path) -> None:
    history, first, _ = persisted_project(tmp_path)
    previous_snapshot_sha = AudioRoundTripHistoryStore.snapshot(history)["snapshot_sha256"]
    second = manifest(revision=2, parent=first.record_sha256)
    history.append(second)
    AudioRoundTripHistoryStore.save_project(
        tmp_path,
        history,
        expected_previous_snapshot_sha256=previous_snapshot_sha,
    )
    result = AudioRoundTripHistoryStore.read_current(
        tmp_path,
        project_id="project:1",
        manifest_id="roundtrip:1",
        expected_session_plan_sha256=H1,
        expected_manifest_sha256=first.record_sha256,
    )
    assert result.manifest == second
    assert result.state is AudioRoundTripCurrentState.STALE
    assert result.reason_codes == ("MANIFEST_HEAD_CHANGED",)


def test_owner_read_result_rejects_forged_seal_and_effect_claim(tmp_path: Path) -> None:
    _, first, _ = persisted_project(tmp_path)
    result = AudioRoundTripHistoryStore.read_current(
        tmp_path,
        project_id="project:1",
        manifest_id="roundtrip:1",
        expected_session_plan_sha256=H1,
        expected_manifest_sha256=first.record_sha256,
    )
    with pytest.raises(ValueError, match="owner store"):
        replace(result, _issuer_seal=object())
    with pytest.raises(ValueError, match="effect authority"):
        replace(result, reaper_launch_started=True)


def test_current_read_distinguishes_missing_store_and_manifest(tmp_path: Path) -> None:
    missing_store = AudioRoundTripHistoryStore.read_current(
        tmp_path,
        project_id="project:1",
        manifest_id="roundtrip:1",
        expected_session_plan_sha256=H1,
    )
    assert missing_store.state is AudioRoundTripCurrentState.STORE_NOT_FOUND
    assert missing_store.owner_origin_authenticated is False
    history = AudioRoundTripHistory("project:1")
    AudioRoundTripHistoryStore.save_project(tmp_path, history)
    missing_manifest = AudioRoundTripHistoryStore.read_current(
        tmp_path,
        project_id="project:1",
        manifest_id="roundtrip:1",
        expected_session_plan_sha256=H1,
    )
    assert missing_manifest.state is AudioRoundTripCurrentState.NOT_FOUND
    assert missing_manifest.owner_origin_authenticated is True
    assert missing_manifest.currentness_verified is False


def test_history_rejects_revision_gaps_wrong_parent_and_foreign_project() -> None:
    history = AudioRoundTripHistory("project:1")
    first = manifest()
    history.append(first)
    with pytest.raises(ProductError) as gap:
        history.append(manifest(revision=3, parent=first.record_sha256))
    assert gap.value.code == "ERR_AUDIO_ROUND_TRIP_REVISION_CONFLICT"
    with pytest.raises(ProductError) as parent_error:
        history.append(manifest(revision=2, parent=H4))
    assert parent_error.value.code == "ERR_AUDIO_ROUND_TRIP_PARENT_CONFLICT"
    with pytest.raises(ProductError) as project_error:
        history.append(manifest(project_id="project:2"))
    assert project_error.value.code == "ERR_AUDIO_ROUND_TRIP_PROJECT_MISMATCH"


def test_snapshot_tamper_unknown_fields_and_authority_are_fail_closed() -> None:
    history = AudioRoundTripHistory("project:1")
    history.append(manifest())
    original = AudioRoundTripHistoryStore.snapshot(history)
    mutations = (
        lambda value: value.update({"unknown": True}),
        lambda value: value.update({"external_execution_authority": True}),
        lambda value: value["entries"][0].update({"asset_promotion_started": True}),
        lambda value: value["entries"][0].update({"record_sha256": H4}),
    )
    for mutate in mutations:
        changed = json.loads(json.dumps(original))
        mutate(changed)
        rehash(changed)
        with pytest.raises(ProductError):
            AudioRoundTripHistoryStore.parse(changed)

    duplicate = json.loads(json.dumps(original))
    duplicate["entries"].append(json.loads(json.dumps(duplicate["entries"][0])))
    duplicate["store_revision"] = 1
    rehash(duplicate)
    with pytest.raises(ProductError, match="invalid records"):
        AudioRoundTripHistoryStore.parse(duplicate)


def test_project_mismatch_and_compare_and_swap_are_rejected(tmp_path: Path) -> None:
    history, _, _ = persisted_project(tmp_path)
    previous_snapshot_sha = AudioRoundTripHistoryStore.snapshot(history)["snapshot_sha256"]
    with pytest.raises(ProductError) as mismatch:
        AudioRoundTripHistoryStore.load_project(tmp_path, expected_project_id="project:2")
    assert mismatch.value.code == "ERR_AUDIO_ROUND_TRIP_PROJECT_MISMATCH"
    with pytest.raises(ProductError) as missing_cas:
        AudioRoundTripHistoryStore.save_project(tmp_path, history)
    assert missing_cas.value.code == "ERR_AUDIO_ROUND_TRIP_CAS_REQUIRED"
    with pytest.raises(ProductError) as stale_cas:
        AudioRoundTripHistoryStore.save_project(
            tmp_path, history, expected_previous_snapshot_sha256=H1,
        )
    assert stale_cas.value.code == "ERR_AUDIO_ROUND_TRIP_REVISION_CONFLICT"
    AudioRoundTripHistoryStore.save_project(
        tmp_path, history, expected_previous_snapshot_sha256=previous_snapshot_sha,
    )


@pytest.mark.parametrize("field,value", [
    ("manifest_id", "../private"),
    ("project_id", "C:/private"),
    ("expected_session_plan_sha256", "invalid"),
])
def test_current_read_rejects_invalid_identity_or_hash(
    tmp_path: Path, field: str, value: str,
) -> None:
    arguments = {
        "project_id": "project:1",
        "manifest_id": "roundtrip:1",
        "expected_session_plan_sha256": H1,
    }
    arguments[field] = value
    with pytest.raises(ValueError):
        AudioRoundTripHistoryStore.read_current(tmp_path, **arguments)


def test_static_surface_has_no_audio_or_external_effect_primitives() -> None:
    module = Path(__file__).parents[1] / "src/ai_video_production/reaper_audio_finishing_store.py"
    text = module.read_text(encoding="utf-8")
    for forbidden in ("subprocess", "requests", "urllib", "wave.open", "soundfile", "os.system"):
        assert forbidden not in text


def test_schema_is_valid_packaged_and_reuses_exact_round_trip_manifest() -> None:
    root = Path(__file__).parents[1]
    public = root / "schemas/audio-round-trip-history.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", public.name)
    assert public.read_bytes() == packaged.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    finishing_schema = json.loads(
        (root / "schemas/reaper-audio-finishing.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    resolver = RefResolver.from_schema(
        schema, store={finishing_schema["$id"]: finishing_schema},
    )
    history = AudioRoundTripHistory("project:1")
    history.append(manifest())
    Draft202012Validator(schema, resolver=resolver).validate(
        AudioRoundTripHistoryStore.snapshot(history),
    )
