"""TASK-054 R5A immutable Operator mode-selection boundary.

Selecting a mode records intent only.  It never adopts Dataset material,
starts training, calls a Provider, or changes an active model binding.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping
from uuid import uuid4

from .dbd_reasoning_contracts import ReasoningSessionMode
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


MODE_SELECTION_SCHEMA_VERSION = "1.0.0"
_RECEIPT_ID_RE = re.compile(r"dbd-mode-selection-[0-9a-f]{32}")
_UTC_RFC3339_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")

_RECEIPT_FIELDS = {
    "schema_version", "receipt_id", "workspace_id", "previous_mode", "selected_mode",
    "selected_at", "effect", "training_eligible", "training_authorized",
    "provider_execution_authorized", "dataset_mutation_authorized",
    "binding_mutation_authorized", "receipt_sha256",
}

class ModeSelectionEffect(str, Enum):
    PREVIEW_ISOLATED = "PREVIEW_ISOLATED"
    LEARNING_PREPARATION_ONLY = "LEARNING_PREPARATION_ONLY"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _text(value: str, *, name: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be a non-empty string up to {maximum} characters")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{name} contains a control character")
    return value


@dataclass(frozen=True, slots=True)
class ReasoningModeSelectionReceipt:
    receipt_id: str
    workspace_id: str
    previous_mode: ReasoningSessionMode | None
    selected_mode: ReasoningSessionMode
    selected_at: str
    effect: ModeSelectionEffect
    training_eligible: bool
    training_authorized: bool = False
    provider_execution_authorized: bool = False
    dataset_mutation_authorized: bool = False
    binding_mutation_authorized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_id, str) or not _RECEIPT_ID_RE.fullmatch(self.receipt_id):
            raise ValueError("receipt_id must use the dbd-mode-selection UUID form")
        _text(self.workspace_id, name="workspace_id", maximum=128)
        if self.previous_mode is not None and not isinstance(self.previous_mode, ReasoningSessionMode):
            raise ValueError("previous_mode must be ReasoningSessionMode or null")
        if not isinstance(self.selected_mode, ReasoningSessionMode):
            raise ValueError("selected_mode must be ReasoningSessionMode")
        if not isinstance(self.effect, ModeSelectionEffect):
            raise ValueError("effect must be ModeSelectionEffect")
        if not isinstance(self.selected_at, str) or not _UTC_RFC3339_RE.fullmatch(self.selected_at):
            raise ValueError("selected_at must be an RFC3339 UTC timestamp")
        datetime.fromisoformat(self.selected_at.replace("Z", "+00:00"))
        for name in (
            "training_eligible", "training_authorized", "provider_execution_authorized",
            "dataset_mutation_authorized", "binding_mutation_authorized",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be bool")
        if self.training_eligible is not self.selected_mode.training_eligible:
            raise ValueError("training_eligible must match selected_mode")
        expected_effect = (
            ModeSelectionEffect.PREVIEW_ISOLATED
            if self.selected_mode is ReasoningSessionMode.PREVIEW_NO_LEARNING
            else ModeSelectionEffect.LEARNING_PREPARATION_ONLY
        )
        if self.effect is not expected_effect:
            raise ValueError("effect must match selected_mode")
        if any((
            self.training_authorized, self.provider_execution_authorized,
            self.dataset_mutation_authorized, self.binding_mutation_authorized,
        )):
            raise ValueError("mode selection must not grant execution or mutation authority")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": MODE_SELECTION_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "workspace_id": self.workspace_id,
            "previous_mode": self.previous_mode.value if self.previous_mode is not None else None,
            "selected_mode": self.selected_mode.value,
            "selected_at": self.selected_at,
            "effect": self.effect.value,
            "training_eligible": self.training_eligible,
            "training_authorized": self.training_authorized,
            "provider_execution_authorized": self.provider_execution_authorized,
            "dataset_mutation_authorized": self.dataset_mutation_authorized,
            "binding_mutation_authorized": self.binding_mutation_authorized,
        }
        return {**body, "receipt_sha256": sha256_bytes(canonical_json_bytes(body))}

    @classmethod
    def from_dict(cls, record: Mapping[str, Any]) -> "ReasoningModeSelectionReceipt":
        if not isinstance(record, Mapping):
            raise ValueError("mode-selection receipt must be a mapping")
        if set(record) != _RECEIPT_FIELDS or record.get("schema_version") != MODE_SELECTION_SCHEMA_VERSION:
            raise ValueError("unsupported mode-selection receipt schema_version")
        supplied = record.get("receipt_sha256")
        if not isinstance(supplied, str):
            raise ValueError("receipt_sha256 is required")
        validate_sha256(supplied, field_name="receipt_sha256")
        body = {key: value for key, value in record.items() if key != "receipt_sha256"}
        if sha256_bytes(canonical_json_bytes(body)) != supplied:
            raise ValueError("receipt_sha256 does not match canonical content")
        try:
            previous = record.get("previous_mode")
            return cls(
                receipt_id=record["receipt_id"],
                workspace_id=record["workspace_id"],
                previous_mode=ReasoningSessionMode(previous) if previous is not None else None,
                selected_mode=ReasoningSessionMode(record["selected_mode"]),
                selected_at=record["selected_at"],
                effect=ModeSelectionEffect(record["effect"]),
                training_eligible=record["training_eligible"],
                training_authorized=record["training_authorized"],
                provider_execution_authorized=record["provider_execution_authorized"],
                dataset_mutation_authorized=record["dataset_mutation_authorized"],
                binding_mutation_authorized=record["binding_mutation_authorized"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid mode-selection receipt") from exc


class ReasoningModeSelectionStore:
    """Append-only receipt store; an existing receipt file is never replaced."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.directory = Path(workspace_root) / "control" / "dbd-reasoning-mode-receipts"

    def list_receipts(self, *, workspace_id: str) -> tuple[ReasoningModeSelectionReceipt, ...]:
        _text(workspace_id, name="workspace_id", maximum=128)
        if not self.directory.exists():
            return ()
        receipts: list[ReasoningModeSelectionReceipt] = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                receipt = ReasoningModeSelectionReceipt.from_dict(record)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"mode-selection receipt cannot be admitted: {path.name}") from exc
            if path.name != f"{receipt.receipt_id}.json":
                raise ValueError("mode-selection receipt filename does not match its identity")
            if receipt.workspace_id != workspace_id:
                raise ValueError("mode-selection receipt belongs to another workspace")
            receipts.append(receipt)
        keys = tuple((item.selected_at, item.receipt_id) for item in receipts)
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate mode-selection receipt ordering key")
        ordered = tuple(sorted(receipts, key=lambda item: (item.selected_at, item.receipt_id)))
        for index, receipt in enumerate(ordered):
            expected = None if index == 0 else ordered[index - 1].selected_mode
            if receipt.previous_mode is not expected:
                raise ValueError("mode-selection receipt chain is discontinuous")
        return ordered

    def latest(self, *, workspace_id: str) -> ReasoningModeSelectionReceipt | None:
        receipts = self.list_receipts(workspace_id=workspace_id)
        return receipts[-1] if receipts else None

    def append(self, receipt: ReasoningModeSelectionReceipt) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{receipt.receipt_id}.json"
        data = canonical_json_bytes(receipt.to_dict())
        try:
            with path.open("xb") as stream:
                stream.write(data)
                stream.flush()
        except FileExistsError as exc:
            raise ValueError("mode-selection receipt already exists") from exc
        return path


class ReasoningModeSelectionService:
    def __init__(
        self,
        *,
        workspace_id: str,
        store: ReasoningModeSelectionStore,
        clock: Callable[[], str] = _utc_now,
        id_factory: Callable[[], str] = lambda: f"dbd-mode-selection-{uuid4().hex}",
    ) -> None:
        self.workspace_id = _text(workspace_id, name="workspace_id", maximum=128)
        self.store = store
        self.clock = clock
        self.id_factory = id_factory

    def current_mode(self) -> ReasoningSessionMode:
        latest = self.store.latest(workspace_id=self.workspace_id)
        return latest.selected_mode if latest is not None else ReasoningSessionMode.PREVIEW_NO_LEARNING

    def select(self, mode: ReasoningSessionMode, *, operation_active: bool) -> ReasoningModeSelectionReceipt:
        if operation_active:
            raise RuntimeError("mode cannot change while an operation is running")
        if not isinstance(mode, ReasoningSessionMode):
            raise ValueError("mode must be ReasoningSessionMode")
        previous = self.store.latest(workspace_id=self.workspace_id)
        selected_at = self.clock()
        if previous is not None and selected_at <= previous.selected_at:
            raise ValueError("selected_at must advance beyond the latest receipt")

        receipt = ReasoningModeSelectionReceipt(
            receipt_id=self.id_factory(),
            workspace_id=self.workspace_id,
            previous_mode=previous.selected_mode if previous is not None else None,
            selected_mode=mode,
            selected_at=selected_at,
            effect=(
                ModeSelectionEffect.PREVIEW_ISOLATED
                if mode is ReasoningSessionMode.PREVIEW_NO_LEARNING
                else ModeSelectionEffect.LEARNING_PREPARATION_ONLY
            ),
            training_eligible=mode.training_eligible,
        )
        self.store.append(receipt)
        return receipt


__all__ = [
    "MODE_SELECTION_SCHEMA_VERSION", "ModeSelectionEffect",
    "ReasoningModeSelectionReceipt", "ReasoningModeSelectionService",
    "ReasoningModeSelectionStore",
]
