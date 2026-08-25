from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile, AiWorkload, ConnectionAvailability, CostClass, ModelRoute,
    ProviderFamily, ReasoningEffort, SelectionMode,
)
from ai_video_production.dbd_reasoning_contracts import TunedModelBinding, TunedModelBindingStatus
from ai_video_production.dbd_reasoning_model_panel import (
    ModelPanelPreflightStatus, ModelPanelRow, ModelPanelSnapshot, build_model_panel_snapshot,
)
from ai_video_production.dbd_reasoning_model_panel_ui import ReasoningModelPanel
from ai_video_production.dbd_reasoning_routing import EXECUTION_AUTHORITY_STATE, ROUTE_CAPABILITY
from ai_video_production.dbd_tuned_model_registry import (
    BindingLifecycleTransition, DbDTunedModelRegistry, DbDTunedModelRegistryRecord,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64


def _binding(revision: int, status: TunedModelBindingStatus) -> TunedModelBinding:
    complete = status is not TunedModelBindingStatus.DRAFT
    approved = status is TunedModelBindingStatus.APPROVED
    return TunedModelBinding(
        binding_id="dbd-ja", revision=revision, status=status,
        base_model_ref="model://registry/base/v1", base_model_sha256=SHA_A,
        adapter_ref="model-adapter://registry/dbd/a", adapter_sha256=SHA_A,
        training_dataset_sha256=SHA_B if complete else None,
        training_recipe_sha256=SHA_C if complete else None,
        evaluation_report_sha256=SHA_D if complete else None,
        rights_manifest_sha256=SHA_E if complete else None,
        supported_locales=("ja-JP",),
        approved_at="2026-08-22T00:03:00Z" if approved else None,
        approved_by_ref="human://operator/approval-1" if approved else None,
    )


def _record(binding, transition, previous=None):
    human = transition is BindingLifecycleTransition.APPROVE
    return DbDTunedModelRegistryRecord(
        binding=binding, transition=transition,
        previous_record_sha256=None if previous is None else previous.registry_record_sha256,
        decision_evidence_ref=(
            "human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FA3" if human
            else "evaluation://sha256/" + "d" * 64
            if transition is BindingLifecycleTransition.EVALUATE
            else "registry-intake://sha256/" + "a" * 64
        ),
        decision_evidence_sha256=SHA_D if transition is BindingLifecycleTransition.EVALUATE else SHA_A,
        recorded_at=f"2026-08-22T00:0{binding.revision}:00Z",
    )


def _inputs(*, approved: bool = True, available: bool = True, capability: bool = True):
    draft = _record(_binding(1, TunedModelBindingStatus.DRAFT), BindingLifecycleTransition.REGISTER)
    evaluated = _record(_binding(2, TunedModelBindingStatus.EVALUATED), BindingLifecycleTransition.EVALUATE, draft)
    records = [draft, evaluated]
    selected = evaluated
    if approved:
        selected = _record(_binding(3, TunedModelBindingStatus.APPROVED), BindingLifecycleTransition.APPROVE, evaluated)
        records.append(selected)
    binding = selected.binding
    route = ModelRoute(
        route_id="dbd-tuned", workload=AiWorkload.PLANNING,
        provider_family=ProviderFamily.LOCAL_OPEN_SOURCE, provider_id="local-runtime",
        model_id="dbd-base:v1", cost_class=CostClass.LOCAL_FREE_AI, priority=10,
        reasoning_effort=ReasoningEffort.HIGH,
        capabilities=(ROUTE_CAPABILITY,) if capability else ("TEXT_GENERATION",),
        settings={
            "dbd_tuned_binding_id": binding.binding_id,
            "dbd_tuned_binding_revision": binding.revision,
            "dbd_tuned_binding_sha256": binding.to_dict()["binding_sha256"],
        },
    )
    return (
        DbDTunedModelRegistry(tuple(records)),
        AiConnectionProfile("dbd-profile", "1.0.0", SelectionMode.AUTO, (route,)),
        ConnectionAvailability(frozenset({route.route_id}) if available else frozenset()),
    )


def test_configured_route_is_preflight_only_and_execution_stays_disabled() -> None:
    snapshot = build_model_panel_snapshot(*_inputs(), pending_review_count=2)

    assert snapshot.status is ModelPanelPreflightStatus.ROUTE_CONFIGURED_EXECUTION_GATE_REQUIRED
    assert snapshot.status_code == EXECUTION_AUTHORITY_STATE
    assert snapshot.preflight_passed is True
    assert snapshot.execution_enabled is False
    assert snapshot.execution_block_reason == "R3D_EXECUTION_AUTHORITY_REQUIRED"
    assert snapshot.review_enabled is True
    assert snapshot.pending_review_count == 2
    assert snapshot.rows[0].state == "APPROVED"
    assert snapshot.rows[0].japanese_support is True
    assert snapshot.rows[0].json_compatible is True
    assert snapshot.rows[0].rights_evidence_available is True


def test_no_approved_binding_and_unavailable_route_are_actionable_states() -> None:
    no_model = build_model_panel_snapshot(*_inputs(approved=False))
    unavailable = build_model_panel_snapshot(*_inputs(available=False))

    assert no_model.status is ModelPanelPreflightStatus.NO_APPROVED_MODEL
    assert no_model.preflight_passed is False
    assert unavailable.status is ModelPanelPreflightStatus.ROUTE_UNAVAILABLE
    assert unavailable.execution_enabled is False


def test_missing_route_capability_fails_preflight_without_fallback() -> None:
    snapshot = build_model_panel_snapshot(*_inputs(capability=False))
    assert snapshot.status is ModelPanelPreflightStatus.ROUTE_UNAVAILABLE
    assert snapshot.status_code == "ERR_PROVIDER_ROUTE_UNAVAILABLE"
    assert snapshot.route_decision is None


def test_review_button_only_follows_pending_review_count() -> None:
    without_review = build_model_panel_snapshot(*_inputs(), pending_review_count=0)
    assert without_review.review_enabled is False

    with pytest.raises(ValueError, match="review_enabled"):
        replace(without_review, review_enabled=True)


def test_r5c_snapshot_cannot_be_forged_to_enable_execution() -> None:
    snapshot = build_model_panel_snapshot(*_inputs())
    with pytest.raises(ValueError, match="cannot enable execution"):
        replace(snapshot, execution_enabled=True)


def test_panel_row_cannot_invent_gpu_evidence_or_configured_state() -> None:
    snapshot = build_model_panel_snapshot(*_inputs())
    with pytest.raises(ValueError, match="GPU requirement"):
        replace(snapshot.rows[0], required_gpu="24 GB")
    with pytest.raises(ValueError, match="configured status"):
        replace(
            snapshot,
            status=ModelPanelPreflightStatus.ROUTE_UNAVAILABLE,
        )
    with pytest.raises(ValueError, match="block reason"):
        replace(snapshot, execution_block_reason="READY")


def test_japanese_ui_contains_unambiguous_actions() -> None:
    source = __import__("pathlib").Path(
        "src/ai_video_production/dbd_reasoning_model_panel_ui.py"
    ).read_text(encoding="utf-8")
    assert "事前チェック" in source
    assert "現在の実況・解説を確認" in source
    assert "生成結果をレビュー" in source
    assert "実行可能: いいえ" in source
    assert "エラーコード: {error_code}" in source
    assert "ERR_TASK054_PREFLIGHT_FAILED" in source
    assert ReasoningModelPanel.__name__ == "ReasoningModelPanel"
