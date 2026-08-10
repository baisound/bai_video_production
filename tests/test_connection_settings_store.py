from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production import (
    AiConnectionProfile,
    AiConnectionSettingsService,
    AiWorkload,
    ConnectionAvailability,
    ConnectionCatalogEditor, ConnectionSettingsFormBuilder,
    ConnectionSettingsStore,
    CostClass,
    ModelRoute,
    ProductError,
    ProviderFamily,
    ReasoningEffort,
    SelectionMode,
)
from ai_video_production.schema_contracts import validate_instance


def profile() -> AiConnectionProfile:
    return AiConnectionProfile(
        "desktop-default",
        "1.0.0",
        SelectionMode.AUTO,
        (
            ModelRoute(
                "openai-plan", AiWorkload.PLANNING, ProviderFamily.OPENAI,
                "openai", "gpt-5-demo", CostClass.CLOUD_PAID_AI,
                reasoning_effort=ReasoningEffort.MEDIUM,
                credential_ref="credential://openai/default",
                capabilities=("TEXT_GENERATION",),
            ),
            ModelRoute(
                "local-image", AiWorkload.IMAGE, ProviderFamily.COMFYUI,
                "comfyui", "flux-demo", CostClass.LOCAL_FREE_AI,
                capabilities=("IMAGE_GENERATION",),
            ),
        ),
        {
            AiWorkload.VIDEO: SelectionMode.DISABLED,
            AiWorkload.AUDIO: SelectionMode.DISABLED,
            AiWorkload.MUSIC: SelectionMode.DISABLED,
        },
    )


def test_store_round_trip_increments_revision_and_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "connections.json"
    first = ConnectionSettingsStore.save(path, profile())
    assert first.record.revision == 1
    loaded = ConnectionSettingsStore.load(path)
    assert loaded.record.profile.to_dict() == profile().to_dict()
    second = ConnectionSettingsStore.save(path, profile(), expected_revision=1)
    assert second.record.revision == 2
    assert ConnectionSettingsStore.load(path).record.revision == 2


def test_store_rejects_stale_or_unspecified_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "connections.json"
    ConnectionSettingsStore.save(path, profile())
    for expected in (None, 0):
        with pytest.raises(ProductError) as exc:
            ConnectionSettingsStore.save(path, profile(), expected_revision=expected)
        assert exc.value.code == "ERR_CONNECTION_SETTINGS_CONFLICT"
    assert ConnectionSettingsStore.load(path).record.revision == 1


def test_atomic_failure_preserves_previous_settings(tmp_path: Path) -> None:
    path = tmp_path / "connections.json"
    ConnectionSettingsStore.save(path, profile())
    before = path.read_bytes()

    def fail(stage: str, _path: Path) -> None:
        if stage == "before_replace":
            raise RuntimeError("simulated power loss")

    with pytest.raises(RuntimeError, match="power loss"):
        ConnectionSettingsStore.save(
            path, profile(), expected_revision=1, failure_injector=fail
        )
    assert path.read_bytes() == before
    assert ConnectionSettingsStore.load(path).record.revision == 1


def test_store_fails_closed_on_checksum_tampering(tmp_path: Path) -> None:
    path = tmp_path / "connections.json"
    ConnectionSettingsStore.save(path, profile())
    document = json.loads(path.read_text(encoding="utf-8"))
    document["revision"] = 99
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ConnectionSettingsStore.load(path)
    assert exc.value.code == "ERR_CONNECTION_SETTINGS_INTEGRITY"


def test_legacy_raw_profile_is_loaded_then_migrated_on_explicit_save(tmp_path: Path) -> None:
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(profile().to_dict()), encoding="utf-8")
    loaded = ConnectionSettingsStore.load(path)
    assert loaded.migrated_from == "ai-connection-profile/1.0.0"
    assert loaded.record.revision == 0
    saved = ConnectionSettingsStore.save(path, loaded.record.profile, expected_revision=0)
    assert saved.record.revision == 1
    assert ConnectionSettingsStore.load(path).migrated_from is None


def test_form_is_bilingual_complete_and_secret_free() -> None:
    value = profile()
    availability = ConnectionAvailability(
        frozenset({"openai-plan", "local-image"}),
        frozenset({"credential://openai/default"}),
    )
    preflight = AiConnectionSettingsService.preflight(value, availability)
    form = ConnectionSettingsFormBuilder.build(value, preflight, revision=4)
    assert len(form["workloads"]) == 5
    assert form["save_does_not_authorize_generation"] is True
    planning = form["workloads"][0]
    assert planning["label"] == {"ja": "企画・台本", "en": "Planning & script"}
    assert planning["status_message"]["ja"] == "準備できています"
    assert planning["mode_help"]["OFFLINE_ONLY"]["en"].startswith("Use options")
    assert planning["routes"][0]["model_id"] == "gpt-5-demo"
    assert planning["preferred_route_id"] == "openai-plan"
    serialized = json.dumps(form, ensure_ascii=False)
    assert "credential://" not in serialized
    assert "api_key" not in serialized
    assert "endpoint_ref" not in serialized


def test_form_rejects_profile_preflight_mismatch() -> None:
    value = profile()
    other = AiConnectionProfile("other", "1.0.0", SelectionMode.DISABLED, ())
    preflight = AiConnectionSettingsService.preflight(
        other, ConnectionAvailability(frozenset())
    )
    with pytest.raises(ValueError, match="do not match"):
        ConnectionSettingsFormBuilder.build(value, preflight)


def catalog_entry(**overrides) -> dict:
    value = {
        "route_id": "luma-video",
        "workload": "VIDEO",
        "provider_family": "LUMA",
        "provider_id": "luma",
        "model_id": "configured-video-model",
        "cost_class": "CLOUD_PAID_AI",
        "reasoning_effort": "none",
        "capabilities": ["TEXT_TO_VIDEO"],
        "credential_required": True,
        "enabled": True,
    }
    value.update(overrides)
    return value


def test_catalog_adds_safe_planned_route_without_secret_value() -> None:
    edited = ConnectionCatalogEditor.upsert(profile(), catalog_entry())
    route = next(item for item in edited.routes if item.route_id == "luma-video")
    assert route.credential_ref == "credential://catalog/luma-video"
    preflight = AiConnectionSettingsService.preflight(
        edited, ConnectionAvailability(frozenset(item.route_id for item in edited.routes))
    )
    form = ConnectionSettingsFormBuilder.build(edited, preflight)
    video = next(item for item in form["workloads"] if item["workload"] == "VIDEO")
    assert video["routes"][0]["implementation_status"] == "PLANNED_ADAPTER"
    assert "credential://" not in json.dumps(form)


def test_catalog_updates_metadata_and_disables_without_deleting_route() -> None:
    added = ConnectionCatalogEditor.upsert(profile(), catalog_entry())
    edited = ConnectionCatalogEditor.upsert(
        added, catalog_entry(model_id="new-model", enabled=False)
    )
    route = next(item for item in edited.routes if item.route_id == "luma-video")
    assert route.model_id == "new-model"
    assert route.enabled is False
    assert route.credential_ref == "credential://catalog/luma-video"


def test_catalog_rejects_workload_change_and_embedded_secret_fields() -> None:
    added = ConnectionCatalogEditor.upsert(profile(), catalog_entry())
    with pytest.raises(ValueError, match="workload cannot change"):
        ConnectionCatalogEditor.upsert(added, catalog_entry(workload="IMAGE"))
    entry = catalog_entry()
    entry["api_key"] = "secret"
    with pytest.raises(ValueError, match="incomplete or unknown"):
        ConnectionCatalogEditor.upsert(profile(), entry)


def test_store_schema_is_packaged_and_matches_canonical(tmp_path: Path) -> None:
    canonical = Path(__file__).parents[1] / "schemas" / "connection-settings-store.schema.json"
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "connection-settings-store.schema.json"
    ).read_text(encoding="utf-8")
    assert json.loads(canonical.read_text(encoding="utf-8")) == json.loads(packaged)
    validate_instance(
        ConnectionSettingsStore.save(tmp_path / "connections.json", profile()).record.to_dict(),
        canonical,
    )
