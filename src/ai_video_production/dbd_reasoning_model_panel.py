"""TASK-054 R5C read-only model status and execution preflight projection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .ai_connections import AiConnectionProfile, ConnectionAvailability
from .dbd_reasoning_contracts import CONTEXT_SCHEMA_VERSION, PROPOSAL_SCHEMA_VERSION
from .dbd_reasoning_routing import (
    DbDReasoningRouteCapabilityResolver, DbDReasoningRouteDecision,
    EXECUTION_AUTHORITY_STATE,
)
from .dbd_tuned_model_registry import DbDTunedModelRegistry, admit_tuned_model_registry_record
from .errors import ProductError


class ModelPanelPreflightStatus(str, Enum):
    ROUTE_CONFIGURED_EXECUTION_GATE_REQUIRED = "ROUTE_CONFIGURED_EXECUTION_GATE_REQUIRED"
    NO_APPROVED_MODEL = "NO_APPROVED_MODEL"
    ROUTE_UNAVAILABLE = "ROUTE_UNAVAILABLE"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"


@dataclass(frozen=True, slots=True)
class ModelPanelRow:
    binding_id: str
    revision: int
    state: str
    japanese_support: bool
    json_compatible: bool
    rights_evidence_available: bool
    evaluation_evidence_available: bool
    required_gpu: str = "未確認"
    role: str = "DbD実況・解説"

    def __post_init__(self) -> None:
        if not isinstance(self.binding_id, str) or not self.binding_id.strip() or len(self.binding_id) > 128:
            raise ValueError("binding_id is invalid")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be positive")
        if self.state not in {"DRAFT", "EVALUATED", "APPROVED", "SUSPENDED", "REVOKED", "REJECTED"}:
            raise ValueError("state is invalid")
        for name in (
            "japanese_support", "json_compatible", "rights_evidence_available",
            "evaluation_evidence_available",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be bool")
        if self.required_gpu != "未確認":
            raise ValueError("GPU requirement needs a separate runtime Evidence source")
        if self.role != "DbD実況・解説":
            raise ValueError("role is fixed for this panel")


@dataclass(frozen=True, slots=True)
class ModelPanelSnapshot:
    rows: tuple[ModelPanelRow, ...]
    status: ModelPanelPreflightStatus
    status_code: str
    status_message_ja: str
    route_decision: DbDReasoningRouteDecision | None
    preflight_passed: bool
    execution_enabled: bool
    execution_block_reason: str
    review_enabled: bool
    pending_review_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.rows, tuple) or any(not isinstance(item, ModelPanelRow) for item in self.rows):
            raise ValueError("rows must contain ModelPanelRow values")
        keys = tuple((item.binding_id, item.revision) for item in self.rows)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("rows must be unique and canonically ordered")
        if not isinstance(self.status, ModelPanelPreflightStatus):
            raise ValueError("status must be ModelPanelPreflightStatus")
        if not isinstance(self.status_code, str) or not self.status_code or len(self.status_code) > 128:
            raise ValueError("status_code is invalid")
        if not isinstance(self.status_message_ja, str) or not self.status_message_ja or len(self.status_message_ja) > 500:
            raise ValueError("status_message_ja is invalid")
        if not isinstance(self.preflight_passed, bool) or not isinstance(self.execution_enabled, bool):
            raise ValueError("preflight/execution flags must be bool")
        if self.execution_enabled:
            raise ValueError("R5C cannot enable execution before an R3D authority boundary exists")
        if self.route_decision is not None and self.route_decision.execution_authority_state != EXECUTION_AUTHORITY_STATE:
            raise ValueError("route decision authority state is invalid")
        if self.preflight_passed != (self.route_decision is not None):
            raise ValueError("preflight_passed must match route decision presence")
        configured = self.status is ModelPanelPreflightStatus.ROUTE_CONFIGURED_EXECUTION_GATE_REQUIRED
        if configured != self.preflight_passed:
            raise ValueError("configured status must match successful preflight")
        if self.execution_block_reason != "R3D_EXECUTION_AUTHORITY_REQUIRED":
            raise ValueError("execution block reason is fixed until R3D exists")
        if isinstance(self.pending_review_count, bool) or not isinstance(self.pending_review_count, int) or self.pending_review_count < 0:
            raise ValueError("pending_review_count must be non-negative")
        if self.review_enabled != (self.pending_review_count > 0):
            raise ValueError("review_enabled must match pending review count")


def _rows(registry: DbDTunedModelRegistry) -> tuple[ModelPanelRow, ...]:
    if not isinstance(registry, DbDTunedModelRegistry):
        raise ValueError("registry must be DbDTunedModelRegistry")
    admitted = tuple(admit_tuned_model_registry_record(item.to_dict()) for item in registry.records)
    latest = {item.binding.binding_id: item.binding for item in admitted}
    return tuple(
        ModelPanelRow(
            binding_id=binding.binding_id,
            revision=binding.revision,
            state=binding.status.value,
            japanese_support="ja-JP" in binding.supported_locales,
            json_compatible=(
                binding.to_dict()["context_schema"] == CONTEXT_SCHEMA_VERSION
                and binding.to_dict()["output_schema"] == PROPOSAL_SCHEMA_VERSION
            ),
            rights_evidence_available=binding.rights_manifest_sha256 is not None,
            evaluation_evidence_available=binding.evaluation_report_sha256 is not None,
        )
        for binding in sorted(latest.values(), key=lambda item: (item.binding_id, item.revision))
    )


def build_model_panel_snapshot(
    registry: DbDTunedModelRegistry,
    profile: AiConnectionProfile,
    availability: ConnectionAvailability,
    *,
    locale: str = "ja-JP",
    binding_id: str | None = None,
    pending_review_count: int = 0,
) -> ModelPanelSnapshot:
    rows = _rows(registry)
    decision = None
    try:
        decision = DbDReasoningRouteCapabilityResolver.resolve(
            registry, profile, availability, locale=locale, binding_id=binding_id,
        )
        status = ModelPanelPreflightStatus.ROUTE_CONFIGURED_EXECUTION_GATE_REQUIRED
        code = EXECUTION_AUTHORITY_STATE
        message = "モデルと経路の事前チェックは完了しました。実行にはR3Dの別承認が必要です。"
    except ProductError as exc:
        code = exc.code
        if exc.code == "ERR_DBD_TUNED_BINDING_UNAVAILABLE":
            status = ModelPanelPreflightStatus.NO_APPROVED_MODEL
            message = "承認済みのDbD解説モデルがありません。baselineまたは承認手続きを確認してください。"
        else:
            status = ModelPanelPreflightStatus.ROUTE_UNAVAILABLE
            message = "解説モデルの経路を利用できません。接続設定とモデル状態を確認してください。"
    except (TypeError, ValueError) as exc:
        status = ModelPanelPreflightStatus.INVALID_CONFIGURATION
        code = "ERR_DBD_MODEL_PANEL_CONFIGURATION_INVALID"
        message = "モデル設定の整合性を確認できません。安全のため実行を停止しています。"
    return ModelPanelSnapshot(
        rows=rows,
        status=status,
        status_code=code,
        status_message_ja=message,
        route_decision=decision,
        preflight_passed=decision is not None,
        execution_enabled=False,
        execution_block_reason="R3D_EXECUTION_AUTHORITY_REQUIRED",
        review_enabled=pending_review_count > 0,
        pending_review_count=pending_review_count,
    )


__all__ = [
    "ModelPanelPreflightStatus", "ModelPanelRow", "ModelPanelSnapshot",
    "build_model_panel_snapshot",
]
