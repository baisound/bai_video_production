from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.dbd_reasoning_contracts import ReasoningSessionMode
from ai_video_production.dbd_reasoning_mode_selection import (
    ModeSelectionEffect,
    ReasoningModeSelectionReceipt,
    ReasoningModeSelectionService,
    ReasoningModeSelectionStore,
)
from ai_video_production.dbd_reasoning_mode_selector_ui import (
    MODE_EXPLANATION_JA,
    MODE_LABEL_JA,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


def _service(tmp_path: Path) -> ReasoningModeSelectionService:
    receipt_ids = iter((
        "dbd-mode-selection-00000000000000000000000000000001",
        "dbd-mode-selection-00000000000000000000000000000002",
        "dbd-mode-selection-00000000000000000000000000000003",
    ))
    timestamps = iter((
        "2026-08-25T01:00:00.000Z",
        "2026-08-25T01:00:01.000Z",
        "2026-08-25T01:00:02.000Z",
    ))
    return ReasoningModeSelectionService(
        workspace_id="workspace-054",
        store=ReasoningModeSelectionStore(tmp_path),
        clock=lambda: next(timestamps),
        id_factory=lambda: next(receipt_ids),
    )


def _schema() -> dict:
    return json.loads(
        Path("schemas/dbd-reasoning-mode-selection-receipt.schema.json").read_text(encoding="utf-8")
    )


def test_default_is_non_learning_without_writing_a_receipt(tmp_path: Path) -> None:
    service = _service(tmp_path)

    assert service.current_mode() is ReasoningSessionMode.PREVIEW_NO_LEARNING
    assert not service.store.directory.exists()


def test_preview_selection_is_immutable_non_authorizing_receipt(tmp_path: Path) -> None:
    service = _service(tmp_path)
    receipt = service.select(ReasoningSessionMode.PREVIEW_NO_LEARNING, operation_active=False)
    record = receipt.to_dict()

    assert record["effect"] == ModeSelectionEffect.PREVIEW_ISOLATED.value
    assert record["training_eligible"] is False
    assert record["training_authorized"] is False
    assert record["provider_execution_authorized"] is False
    assert record["dataset_mutation_authorized"] is False
    assert record["binding_mutation_authorized"] is False
    assert not list(Draft202012Validator(_schema()).iter_errors(record))
    assert ReasoningModeSelectionReceipt.from_dict(record) == receipt
    assert service.current_mode() is ReasoningSessionMode.PREVIEW_NO_LEARNING

    with pytest.raises(ValueError, match="already exists"):
        service.store.append(receipt)


def test_learning_selection_records_preparation_only_and_previous_mode(tmp_path: Path) -> None:
    service = _service(tmp_path)
    preview = service.select(ReasoningSessionMode.PREVIEW_NO_LEARNING, operation_active=False)
    learning = service.select(ReasoningSessionMode.LEARNING, operation_active=False)

    assert learning.previous_mode is preview.selected_mode
    assert learning.training_eligible is True
    assert learning.effect is ModeSelectionEffect.LEARNING_PREPARATION_ONLY
    assert learning.training_authorized is False
    assert service.current_mode() is ReasoningSessionMode.LEARNING
    assert len(service.store.list_receipts(workspace_id="workspace-054")) == 2


def test_active_operation_blocks_mode_change_without_receipt(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(RuntimeError, match="operation is running"):
        service.select(ReasoningSessionMode.LEARNING, operation_active=True)

    assert not service.store.directory.exists()


def test_tampered_or_foreign_receipt_fails_closed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    receipt = service.select(ReasoningSessionMode.PREVIEW_NO_LEARNING, operation_active=False)
    path = service.store.directory / f"{receipt.receipt_id}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["selected_mode"] = "LEARNING"
    path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="cannot be admitted"):
        service.current_mode()


def test_constructor_rejects_authority_escalation() -> None:
    with pytest.raises(ValueError, match="must not grant"):
        ReasoningModeSelectionReceipt(
            receipt_id="dbd-mode-selection-00000000000000000000000000000009",
            workspace_id="workspace-054",
            previous_mode=None,
            selected_mode=ReasoningSessionMode.LEARNING,
            selected_at="2026-08-25T01:00:00.000Z",
            effect=ModeSelectionEffect.LEARNING_PREPARATION_ONLY,
            training_eligible=True,
            training_authorized=True,
        )


def test_rehashed_but_discontinuous_history_fails_closed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.select(ReasoningSessionMode.PREVIEW_NO_LEARNING, operation_active=False)
    second = service.select(ReasoningSessionMode.LEARNING, operation_active=False)
    path = service.store.directory / f"{second.receipt_id}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["previous_mode"] = None
    body = {key: value for key, value in record.items() if key != "receipt_sha256"}
    record["receipt_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_bytes(canonical_json_bytes(record))

    with pytest.raises(ValueError, match="chain is discontinuous"):
        service.current_mode()


def test_filename_identity_crossing_fails_closed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    receipt = service.select(ReasoningSessionMode.PREVIEW_NO_LEARNING, operation_active=False)
    original = service.store.directory / f"{receipt.receipt_id}.json"
    original.rename(service.store.directory / "dbd-mode-selection-ffffffffffffffffffffffffffffffff.json")

    with pytest.raises(ValueError, match="filename does not match"):
        service.current_mode()


def test_non_monotonic_selection_time_is_rejected(tmp_path: Path) -> None:
    timestamps = iter(("2026-08-25T01:00:01.000Z", "2026-08-25T01:00:00.000Z"))
    receipt_ids = iter((
        "dbd-mode-selection-00000000000000000000000000000007",
        "dbd-mode-selection-00000000000000000000000000000008",
    ))
    service = ReasoningModeSelectionService(
        workspace_id="workspace-054",
        store=ReasoningModeSelectionStore(tmp_path),
        clock=lambda: next(timestamps),
        id_factory=lambda: next(receipt_ids),
    )
    service.select(ReasoningSessionMode.PREVIEW_NO_LEARNING, operation_active=False)

    with pytest.raises(ValueError, match="must advance"):
        service.select(ReasoningSessionMode.LEARNING, operation_active=False)

    assert len(service.store.list_receipts(workspace_id="workspace-054")) == 1


def test_schema_mirror_and_operator_copy_are_exact() -> None:
    canonical = Path("schemas/dbd-reasoning-mode-selection-receipt.schema.json").read_bytes()
    packaged = Path(
        "src/ai_video_production/schema_resources/dbd-reasoning-mode-selection-receipt.schema.json"
    ).read_bytes()
    source = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")

    assert canonical == packaged
    assert MODE_LABEL_JA[ReasoningSessionMode.PREVIEW_NO_LEARNING] == "確認モード（学習しない）"
    assert MODE_LABEL_JA[ReasoningSessionMode.LEARNING] == "学習モード"
    assert "自動学習もしません" in MODE_EXPLANATION_JA[ReasoningSessionMode.PREVIEW_NO_LEARNING]
    assert "選択だけでは学習・外部送信・モデル変更を実行しません" in MODE_EXPLANATION_JA[ReasoningSessionMode.LEARNING]
    assert "build_reasoning_mode_selector_panel" in source
    assert 'mode_panel.grid(row=1' in source
