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
    admit_adapter_e2e_observation,
    apply_connector_activation_transaction,
    execute_connector_source_binding,
    issue_human_activation_evidence,
    plan_connector_source_binding,
    read_connector_activation_config,
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


def _bound(tmp_path: Path):
    target, migration, store, saved, source, readiness, plan = _binding_plan(tmp_path)
    binding = execute_connector_source_binding(
        plan, target, migration_readback=migration, preference_source=source,
        task058_public_readiness=readiness, confirmation=plan.confirmation(),
        security_backend=SecureBackend(),
    )
    return target, store, saved, source, binding


def _human(binding, *, action: str, evidence_id: str, issued: str = "2026-08-30T00:00:00Z", expires: str = "2026-08-31T00:00:00Z"):
    confirmation = f"{action}_MONTAGE_CONNECTOR:{binding.target_install_instance_id}:{binding.binding_sha256}"
    return issue_human_activation_evidence(
        binding, action=action, evidence_id=evidence_id,
        issued_at=issued, expires_at=expires, confirmation=confirmation,
    )


def _apply(*args, **kwargs):
    return apply_connector_activation_transaction(
        *args,
        security_attestation_id="task061-cac-config",
        security_backend=SecureBackend(),
        **kwargs,
    )


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


def test_repository_default_is_absent_and_disabled(tmp_path: Path) -> None:
    target, _store, _saved, _source, binding = _bound(tmp_path)
    config = read_connector_activation_config(target)
    assert config["revision"] == 0
    assert config["enabled"] is False
    assert config["events"] == []
    assert config["repository_default_enabled"] is False
    assert config["external_skill_config_modified"] is False
    assert not (target.layout.state / "connector-activation-history.json").exists()
    assert binding.to_dict()["connector_enabled"] is False


def test_explicit_human_deactivation_writes_crash_safe_disabled_readback(tmp_path: Path) -> None:
    target, _store, _saved, _source, binding = _bound(tmp_path)
    evidence = _human(binding, action="DEACTIVATE", evidence_id="human-action-disable-001")
    receipt = _apply(
        target, binding, evidence, expected_revision=0,
        now="2026-08-30T00:01:00Z",
    )
    value = receipt.to_dict()
    assert value["action"] == "DEACTIVATE"
    assert value["state"] == "DISABLED"
    assert value["enabled"] is False
    assert value["adapter_e2e_sha256"] is None
    assert value["one_shot_human_evidence_consumed"] is True
    assert value["external_skill_config_modified"] is False
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "montage-learning-connector-activation.schema.json"
    Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(value)
    config = read_connector_activation_config(target)
    assert config["revision"] == 1
    assert config["enabled"] is False
    assert len(config["events"]) == 1


def test_duplicate_exact_deactivation_returns_identical_receipt(tmp_path: Path) -> None:
    target, _store, _saved, _source, binding = _bound(tmp_path)
    evidence = _human(binding, action="DEACTIVATE", evidence_id="human-action-disable-duplicate")
    first = _apply(
        target, binding, evidence, expected_revision=0, now="2026-08-30T00:01:00Z"
    ).to_dict()
    second = _apply(
        target, binding, evidence, expected_revision=0, now="2026-08-30T00:02:00Z"
    ).to_dict()
    assert second == first
    assert read_connector_activation_config(target)["revision"] == 1


def test_human_confirmation_expiry_and_cas_fail_before_write(tmp_path: Path) -> None:
    target, _store, _saved, _source, binding = _bound(tmp_path)
    with pytest.raises(MontageLearningConnectorActivationError, match="exact Human confirmation"):
        issue_human_activation_evidence(
            binding, action="DEACTIVATE", evidence_id="human-action-bad-confirm",
            issued_at="2026-08-30T00:00:00Z", expires_at="2026-08-31T00:00:00Z",
            confirmation="yes",
        )
    expired = _human(binding, action="DEACTIVATE", evidence_id="human-action-expired")
    with pytest.raises(MontageLearningConnectorActivationError, match="expired"):
        _apply(
            target, binding, expired, expected_revision=0, now="2026-08-31T00:00:00Z"
        )
    current = _human(binding, action="DEACTIVATE", evidence_id="human-action-cas")
    with pytest.raises(MontageLearningConnectorActivationError, match="CAS"):
        _apply(
            target, binding, current, expected_revision=1, now="2026-08-30T00:01:00Z"
        )
    assert read_connector_activation_config(target)["revision"] == 0


def test_synthetic_e2e_can_never_enable_connector(tmp_path: Path) -> None:
    target, _store, _saved, _source, binding = _bound(tmp_path)
    evidence = _human(binding, action="ACTIVATE", evidence_id="human-action-activate-synthetic")
    synthetic = admit_adapter_e2e_observation(
        binding,
        connector_status_sha256="sha256:" + "1" * 64,
        publish_learning_receipt_sha256="sha256:" + "2" * 64,
        profile_readback_sha256="sha256:" + "3" * 64,
        synthetic_fixture=True,
    )
    with pytest.raises(MontageLearningConnectorActivationError, match="real installed adapter E2E"):
        _apply(
            target, binding, evidence, expected_revision=0,
            now="2026-08-30T00:01:00Z", adapter_e2e=synthetic,
        )
    with pytest.raises(MontageLearningConnectorActivationError, match="not available"):
        admit_adapter_e2e_observation(
            binding,
            connector_status_sha256="sha256:" + "1" * 64,
            publish_learning_receipt_sha256="sha256:" + "2" * 64,
            profile_readback_sha256="sha256:" + "3" * 64,
            synthetic_fixture=False,
        )
    assert read_connector_activation_config(target)["enabled"] is False


def test_config_write_requires_fresh_secure_bridge(tmp_path: Path) -> None:
    target, _store, _saved, _source, binding = _bound(tmp_path)
    evidence = _human(binding, action="DEACTIVATE", evidence_id="human-action-unsafe-bridge")
    with pytest.raises(MontageLearningConnectorActivationError, match="not SECURE"):
        apply_connector_activation_transaction(
            target, binding, evidence, expected_revision=0,
            now="2026-08-30T00:01:00Z",
            security_attestation_id="task061-cac-unsafe",
            security_backend=SharedWriterBackend(),
        )
    assert read_connector_activation_config(target)["revision"] == 0


@pytest.mark.parametrize("phase", ["before_config_replace", "after_config_replace"])
def test_deactivation_crash_recovery_is_atomic_and_idempotent(tmp_path: Path, phase: str) -> None:
    target, _store, _saved, _source, binding = _bound(tmp_path)
    evidence = _human(binding, action="DEACTIVATE", evidence_id=f"human-action-crash-{phase}")
    raised = False

    def crash(current: str, _path: Path) -> None:
        nonlocal raised
        if current == phase and not raised:
            raised = True
            raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        _apply(
            target, binding, evidence, expected_revision=0,
            now="2026-08-30T00:01:00Z", hook=crash,
        )
    receipt = _apply(
        target, binding, evidence, expected_revision=0,
        now="2026-08-30T00:01:00Z",
    )
    assert receipt.enabled is False
    assert read_connector_activation_config(target)["revision"] == 1


def test_history_tamper_and_nonlatest_evidence_reuse_fail_closed(tmp_path: Path) -> None:
    target, _store, _saved, _source, binding = _bound(tmp_path)
    first = _human(binding, action="DEACTIVATE", evidence_id="human-action-first")
    _apply(
        target, binding, first, expected_revision=0, now="2026-08-30T00:01:00Z"
    )
    second = _human(binding, action="DEACTIVATE", evidence_id="human-action-second")
    _apply(
        target, binding, second, expected_revision=1, now="2026-08-30T00:02:00Z"
    )
    with pytest.raises(MontageLearningConnectorActivationError, match="already consumed"):
        _apply(
            target, binding, first, expected_revision=2, now="2026-08-30T00:03:00Z"
        )
    path = target.layout.state / "connector-activation-history.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["events"][0]["enabled"] = True
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(MontageLearningConnectorActivationError):
        read_connector_activation_config(target)
