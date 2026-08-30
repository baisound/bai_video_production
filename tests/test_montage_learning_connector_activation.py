from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.montage_learning_bridge_migration import (
    execute_legacy_bridge_migration,
    read_legacy_bridge_migration,
)
from ai_video_production.montage_learning_connector_activation import (
    MontageLearningConnectorActivationError,
    execute_connector_source_binding,
    plan_connector_source_binding,
)
from ai_video_production.montage_learning_connector_readiness import (
    production_readiness_evidence,
)
from test_montage_learning_bridge_migration import (
    SecureBackend,
    SharedWriterBackend,
    _plan as migration_plan,
)
from test_montage_preference_promotion_store import _second
from test_montage_preference_source_integration import _source as preference_source


def _fixture(tmp_path: Path):
    migration_root = tmp_path / "migration"
    migration_root.mkdir(parents=True)
    _legacy, target, migration = migration_plan(migration_root)
    execute_legacy_bridge_migration(
        migration,
        confirmation=migration.confirmation(),
        security_backend=SecureBackend(),
    )
    migration_readback = read_legacy_bridge_migration(
        target,
        migration_id=migration.migration_id,
    )
    promotion_root = tmp_path / "promotion"
    promotion_root.mkdir()
    store, saved, source = preference_source(promotion_root / "current.json")
    readiness = production_readiness_evidence(
        bridge_state="AVAILABLE",
        import_state="OBSERVATION_RECORDED",
        adapter_state="LOAD_PROFILE_PASS",
        adapter_contract_e2e_pass=True,
        default_skill_config_unchanged=True,
    )
    return target, migration_readback, store, saved, source, readiness


def _binding_plan(tmp_path: Path):
    target, migration_readback, store, saved, source, readiness = _fixture(tmp_path)
    plan = plan_connector_source_binding(
        target,
        migration_readback=migration_readback,
        preference_source=source,
        task058_public_readiness=readiness,
        security_attestation_id="task061-cab-source-binding",
        security_backend=SecureBackend(),
    )
    return target, migration_readback, store, saved, source, readiness, plan


def test_exact_ppc_source_is_published_and_activation_remains_blocked(tmp_path: Path) -> None:
    target, migration, _store, _saved, source, readiness, plan = _binding_plan(tmp_path)
    assert not target.layout.current_profile.exists()
    result = execute_connector_source_binding(
        plan,
        target,
        migration_readback=migration,
        preference_source=source,
        task058_public_readiness=readiness,
        confirmation=plan.confirmation(),
        security_backend=SecureBackend(),
    )
    value = result.to_dict()
    assert value["state"] == "SOURCE_BOUND_ACTIVATION_BLOCKED"
    assert value["production_profile_source_bound"] is True
    assert value["profile_view_readback_verified"] is True
    assert value["profile_publish_status"] == "CURRENT_EXACT_PROFILE"
    assert json.loads(target.layout.current_profile.read_text(encoding="utf-8")) == source.read_current().envelope
    for field in (
        "real_adapter_e2e_verified", "connector_config_modified", "connector_enabled",
        "activation_authorized", "learning_adoption_authorized",
        "automatic_promotion_authorized", "timeline_mutation_authorized",
        "resolve_write_authorized", "external_effect_authorized",
    ):
        assert value[field] is False


def test_source_binding_schema_is_closed_and_mirrored(tmp_path: Path) -> None:
    target, migration, _store, _saved, source, readiness, plan = _binding_plan(tmp_path)
    result = execute_connector_source_binding(
        plan, target,
        migration_readback=migration,
        preference_source=source,
        task058_public_readiness=readiness,
        confirmation=plan.confirmation(),
        security_backend=SecureBackend(),
    ).to_dict()
    root = Path(__file__).resolve().parents[1]
    public = root / "schemas" / "montage-learning-connector-activation.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / public.name
    assert public.read_bytes() == mirror.read_bytes()
    Draft202012Validator(json.loads(public.read_text(encoding="utf-8"))).validate(result)
    unknown = dict(result)
    unknown["enabled"] = True
    assert not Draft202012Validator(json.loads(public.read_text(encoding="utf-8"))).is_valid(unknown)


def test_duplicate_exact_binding_returns_identical_readback(tmp_path: Path) -> None:
    target, migration, _store, _saved, source, readiness, plan = _binding_plan(tmp_path)
    first = execute_connector_source_binding(
        plan, target, migration_readback=migration, preference_source=source,
        task058_public_readiness=readiness, confirmation=plan.confirmation(),
        security_backend=SecureBackend(),
    ).to_dict()
    second = execute_connector_source_binding(
        plan, target, migration_readback=migration, preference_source=source,
        task058_public_readiness=readiness, confirmation=plan.confirmation(),
        security_backend=SecureBackend(),
    ).to_dict()
    assert second == first


def test_exact_confirmation_is_required_before_profile_write(tmp_path: Path) -> None:
    target, migration, _store, _saved, source, readiness, plan = _binding_plan(tmp_path)
    with pytest.raises(MontageLearningConnectorActivationError, match="exact source binding confirmation"):
        execute_connector_source_binding(
            plan, target, migration_readback=migration, preference_source=source,
            task058_public_readiness=readiness, confirmation="yes",
            security_backend=SecureBackend(),
        )
    assert not target.layout.current_profile.exists()


def test_stale_ppc_source_fails_before_profile_write(tmp_path: Path) -> None:
    target, migration, store, saved, source, readiness, plan = _binding_plan(tmp_path)
    _second(store, saved.history)
    with pytest.raises(MontageLearningConnectorActivationError, match="source read-back failed"):
        execute_connector_source_binding(
            plan, target, migration_readback=migration, preference_source=source,
            task058_public_readiness=readiness, confirmation=plan.confirmation(),
            security_backend=SecureBackend(),
        )
    assert not target.layout.current_profile.exists()


def test_source_drift_after_publish_yields_no_activation_receipt(tmp_path: Path) -> None:
    target, migration, store, saved, source, readiness, plan = _binding_plan(tmp_path)
    changed = False

    def drift(phase: str, _path: Path) -> None:
        nonlocal changed
        if phase == "after_source_read" and not changed:
            changed = True
            _second(store, saved.history)

    with pytest.raises(MontageLearningConnectorActivationError, match="after publication"):
        execute_connector_source_binding(
            plan, target, migration_readback=migration, preference_source=source,
            task058_public_readiness=readiness, confirmation=plan.confirmation(),
            security_backend=SecureBackend(), hook=drift,
        )
    assert target.layout.current_profile.is_file()


def test_profile_view_tamper_after_publish_fails_readback(tmp_path: Path) -> None:
    target, migration, _store, _saved, source, readiness, plan = _binding_plan(tmp_path)

    def tamper(phase: str, path: Path) -> None:
        if phase == "after_profile_publish":
            path.write_bytes(b'{"tampered":true}\n')

    with pytest.raises(Exception):
        execute_connector_source_binding(
            plan, target, migration_readback=migration, preference_source=source,
            task058_public_readiness=readiness, confirmation=plan.confirmation(),
            security_backend=SecureBackend(), hook=tamper,
        )


def test_secure_dacl_drift_after_profile_publish_blocks_binding(tmp_path: Path) -> None:
    target, migration, _store, _saved, source, readiness, _plan = _binding_plan(tmp_path)
    backend = SecureBackend()
    plan = plan_connector_source_binding(
        target,
        migration_readback=migration,
        preference_source=source,
        task058_public_readiness=readiness,
        security_attestation_id="task061-cab-dacl-drift",
        security_backend=backend,
    )

    def drift(phase: str, _path: Path) -> None:
        if phase == "after_profile_publish":
            backend.access_mask = 0x1200A9

    with pytest.raises(MontageLearningConnectorActivationError, match="security identity drifted"):
        execute_connector_source_binding(
            plan,
            target,
            migration_readback=migration,
            preference_source=source,
            task058_public_readiness=readiness,
            confirmation=plan.confirmation(),
            security_backend=backend,
            hook=drift,
        )


def test_non_secure_target_and_non_exact_public_v1_are_rejected(tmp_path: Path) -> None:
    target, migration, _store, _saved, source, _readiness = _fixture(tmp_path)
    good = production_readiness_evidence(
        bridge_state="AVAILABLE", import_state="OBSERVATION_RECORDED",
        adapter_state="LOAD_PROFILE_PASS", adapter_contract_e2e_pass=True,
        default_skill_config_unchanged=True,
    )
    with pytest.raises(MontageLearningConnectorActivationError, match="not SECURE"):
        plan_connector_source_binding(
            target, migration_readback=migration, preference_source=source,
            task058_public_readiness=good, security_attestation_id="unsafe",
            security_backend=SharedWriterBackend(),
        )
    weak = production_readiness_evidence(
        bridge_state="AVAILABLE", import_state="OBSERVATION_RECORDED",
        adapter_state="LOAD_PROFILE_PASS", adapter_contract_e2e_pass=False,
        default_skill_config_unchanged=True,
    )
    with pytest.raises(MontageLearningConnectorActivationError, match="public v1 baseline"):
        plan_connector_source_binding(
            target, migration_readback=migration, preference_source=source,
            task058_public_readiness=weak, security_attestation_id="weak",
            security_backend=SecureBackend(),
        )


def test_migration_readback_cannot_be_reused_for_another_install(tmp_path: Path) -> None:
    _first_target, migration, _store, _saved, _source, _readiness = _fixture(tmp_path / "first")
    second_target, _second_migration, _store2, _saved2, second_source, readiness2 = _fixture(tmp_path / "second")
    with pytest.raises(MontageLearningConnectorActivationError, match="migration read-back target mismatch"):
        plan_connector_source_binding(
            second_target,
            migration_readback=migration,
            preference_source=second_source,
            task058_public_readiness=readiness2,
            security_attestation_id="cross-install",
            security_backend=SecureBackend(),
        )
