"""Workspace-scoped canonical Status Effect definition registry."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable

from .dbd_killer_status_temporal import (
    EffectPolarity,
    EffectSourceKind,
    StatusEffectDefinition,
)
from .dbd_status_effect_recognition import StatusEffectReferenceKind, StatusEffectReferenceLabel


def status_effect_teacher_label(
    *,
    polarity: EffectPolarity,
    definition: StatusEffectDefinition | None = None,
    hard_negative_perk_id: str = "",
) -> str:
    """Build one canonical R5B label from explicit operator intent."""
    if not isinstance(polarity, EffectPolarity):
        raise ValueError("polarity must be EffectPolarity")
    perk_id = hard_negative_perk_id.strip()
    if perk_id:
        if definition is not None:
            raise ValueError("hard-negative and identity choices are mutually exclusive")
        return StatusEffectReferenceLabel(
            StatusEffectReferenceKind.PERK_HARD_NEGATIVE, perk_id=perk_id,
        ).encode()
    if not isinstance(definition, StatusEffectDefinition):
        raise ValueError("identity Teacher requires a registered definition")
    if definition.polarity is not polarity:
        raise ValueError("definition polarity does not match Teacher domain")
    return StatusEffectReferenceLabel(
        StatusEffectReferenceKind.IDENTITY, polarity, definition.effect_id,
    ).encode()


@dataclass(frozen=True, slots=True)
class StatusEffectRegistrySnapshot:
    revision: int
    definitions: tuple[StatusEffectDefinition, ...]


class StatusEffectRegistry:
    """Atomic, revisioned registry shared by Teacher, recognition and R3C."""

    SCHEMA_VERSION = "1.0.0"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(StatusEffectRegistrySnapshot(0, ()))

    @staticmethod
    def _to_dict(snapshot: StatusEffectRegistrySnapshot) -> dict[str, object]:
        return {
            "schema_version": StatusEffectRegistry.SCHEMA_VERSION,
            "revision": snapshot.revision,
            "definitions": [
                {
                    "effect_id": item.effect_id,
                    "polarity": item.polarity.value,
                    "source_kind": item.source_kind.value,
                    "survivor_scoped": item.survivor_scoped,
                    "max_stack_or_level": item.max_stack_or_level,
                    "progress_monotonic": item.progress_monotonic,
                }
                for item in snapshot.definitions
            ],
        }

    @staticmethod
    def _from_dict(payload: object) -> StatusEffectRegistrySnapshot:
        if not isinstance(payload, dict) or payload.get("schema_version") != StatusEffectRegistry.SCHEMA_VERSION:
            raise ValueError("status effect registry schema is invalid")
        revision = payload.get("revision")
        rows = payload.get("definitions")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0 or not isinstance(rows, list):
            raise ValueError("status effect registry payload is invalid")
        definitions = tuple(
            StatusEffectDefinition(
                effect_id=str(row["effect_id"]),
                polarity=EffectPolarity(str(row["polarity"])),
                source_kind=EffectSourceKind(str(row["source_kind"])),
                survivor_scoped=row["survivor_scoped"],
                max_stack_or_level=row.get("max_stack_or_level"),
                progress_monotonic=row.get("progress_monotonic", False),
            )
            for row in rows
            if isinstance(row, dict)
        )
        if len(definitions) != len(rows) or len({item.effect_id for item in definitions}) != len(definitions):
            raise ValueError("status effect registry definitions are invalid")
        return StatusEffectRegistrySnapshot(
            revision,
            tuple(sorted(definitions, key=lambda item: item.effect_id)),
        )

    def _write(self, snapshot: StatusEffectRegistrySnapshot) -> None:
        fd, raw = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        os.close(fd)
        temp = Path(raw)
        try:
            temp.write_text(
                json.dumps(self._to_dict(snapshot), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(temp, self.path)
        finally:
            temp.unlink(missing_ok=True)

    def snapshot(self) -> StatusEffectRegistrySnapshot:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return self._from_dict(payload)
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("status effect registry is invalid") from exc

    def replace(
        self,
        definitions: Iterable[StatusEffectDefinition],
        *,
        expected_revision: int,
    ) -> StatusEffectRegistrySnapshot:
        current = self.snapshot()
        if expected_revision != current.revision:
            raise ValueError("status effect registry revision conflict")
        rows = tuple(definitions)
        if any(not isinstance(item, StatusEffectDefinition) for item in rows):
            raise ValueError("definitions must contain StatusEffectDefinition values")
        if len({item.effect_id for item in rows}) != len(rows):
            raise ValueError("status effect definitions must be unique")
        updated = StatusEffectRegistrySnapshot(
            current.revision + 1,
            tuple(sorted(rows, key=lambda item: item.effect_id)),
        )
        self._write(updated)
        return updated

    def upsert(
        self,
        definition: StatusEffectDefinition,
        *,
        expected_revision: int,
    ) -> StatusEffectRegistrySnapshot:
        if not isinstance(definition, StatusEffectDefinition):
            raise ValueError("definition must be StatusEffectDefinition")
        current = self.snapshot()
        rows = {item.effect_id: item for item in current.definitions}
        rows[definition.effect_id] = definition
        return self.replace(rows.values(), expected_revision=expected_revision)


__all__ = [
    "StatusEffectRegistry", "StatusEffectRegistrySnapshot", "status_effect_teacher_label",
]
