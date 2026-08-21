"""Workspace-local DbD game-knowledge review catalog.

External/community data remains a candidate until a Human explicitly verifies it.
Manual edits are preserved as overrides and are never silently replaced by a later fetch.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable

from .canonical_game_event import GameKnowledgeKind
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


_REVIEW_VALUES = {"CANDIDATE", "VERIFIED", "NEEDS_REVIEW", "UPDATE_AVAILABLE", "REJECTED", "DISABLED"}


@dataclass(frozen=True, slots=True)
class GameKnowledgeCandidate:
    candidate_id: str
    knowledge_kind: GameKnowledgeKind
    name_ja: str
    name_en: str = ""
    aliases_ja: tuple[str, ...] = ()
    image_urls: tuple[str, ...] = ()
    source_page_url: str = ""
    review_status: str = "CANDIDATE"
    enabled: bool = True
    details: dict[str, Any] = field(default_factory=dict)
    manual_name_ja: str = ""
    manual_name_en: str = ""
    manual_aliases_ja: tuple[str, ...] = ()
    manual_image_path: str = ""
    source_revision_sha256: str = ""
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or len(self.candidate_id) > 256:
            raise ValueError("candidate_id must be bounded non-empty text")
        if not isinstance(self.knowledge_kind, GameKnowledgeKind):
            raise ValueError("knowledge_kind must be GameKnowledgeKind")
        if not self.name_ja.strip() or len(self.name_ja) > 256:
            raise ValueError("name_ja must be bounded non-empty text")
        if self.review_status not in _REVIEW_VALUES:
            raise ValueError("unsupported review_status")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be bool")
        if len(self.manual_image_path) > 2048:
            raise ValueError("manual_image_path is too long")

    @property
    def effective_name_ja(self) -> str:
        return self.manual_name_ja.strip() or self.name_ja.strip()

    @property
    def effective_name_en(self) -> str:
        return self.manual_name_en.strip() or self.name_en.strip()

    @property
    def effective_aliases_ja(self) -> tuple[str, ...]:
        raw = self.manual_aliases_ja or self.aliases_ja
        return tuple(dict.fromkeys(x.strip() for x in raw if x.strip()))

    @property
    def effective_image(self) -> str:
        if self.manual_image_path.strip():
            return self.manual_image_path.strip()
        local = str(self.details.get("local_image_path") or "").strip()
        return local

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "knowledge_kind": self.knowledge_kind.value,
            "name_ja": self.name_ja,
            "name_en": self.name_en,
            "aliases_ja": list(self.aliases_ja),
            "image_urls": list(self.image_urls),
            "source_page_url": self.source_page_url,
            "review_status": self.review_status,
            "enabled": self.enabled,
            "details": self.details,
            "manual_name_ja": self.manual_name_ja,
            "manual_name_en": self.manual_name_en,
            "manual_aliases_ja": list(self.manual_aliases_ja),
            "manual_image_path": self.manual_image_path,
            "source_revision_sha256": self.source_revision_sha256,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GameKnowledgeCandidate":
        return cls(
            candidate_id=str(payload["candidate_id"]),
            knowledge_kind=GameKnowledgeKind(str(payload["knowledge_kind"])),
            name_ja=str(payload["name_ja"]),
            name_en=str(payload.get("name_en", "")),
            aliases_ja=tuple(str(x) for x in payload.get("aliases_ja", ())),
            image_urls=tuple(str(x) for x in payload.get("image_urls", ())),
            source_page_url=str(payload.get("source_page_url", "")),
            review_status=str(payload.get("review_status", "CANDIDATE")),
            enabled=bool(payload.get("enabled", True)),
            details=dict(payload.get("details", {})),
            manual_name_ja=str(payload.get("manual_name_ja", "")),
            manual_name_en=str(payload.get("manual_name_en", "")),
            manual_aliases_ja=tuple(str(x) for x in payload.get("manual_aliases_ja", ())),
            manual_image_path=str(payload.get("manual_image_path", "")),
            source_revision_sha256=str(payload.get("source_revision_sha256", "")),
            updated_at=str(payload.get("updated_at", utc_now_iso())),
        )


@dataclass(frozen=True, slots=True)
class KnowledgeDependencyReference:
    kind: str
    reference_id: str
    description: str
    protected: bool = True


@dataclass(frozen=True, slots=True)
class KnowledgeDeleteImpact:
    candidate_id: str
    action: str
    review_status: str
    human_touched: bool
    dependencies: tuple[KnowledgeDependencyReference, ...]
    protected_count: int
    rebuildable_count: int
    fingerprint: str


@dataclass(frozen=True, slots=True)
class KnowledgeDeleteResult:
    candidate_id: str
    action: str
    retained_catalog_row: bool
    tombstone_recorded: bool


class GameKnowledgeReviewCatalog:
    """Version-light review catalog for imported game-information candidates."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(())

    def _read_payload(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("game knowledge review catalog is invalid") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("records", []), list):
            raise ValueError("game knowledge review catalog is invalid")
        if not isinstance(payload.get("tombstones", []), list):
            raise ValueError("game knowledge tombstone ledger is invalid")
        return payload

    def _tombstones(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        return {
            str(row.get("candidate_id")): dict(row)
            for row in self._read_payload().get("tombstones", ())
            if isinstance(row, dict) and str(row.get("candidate_id") or "").strip()
        }

    @staticmethod
    def _source_hash(row: dict[str, Any]) -> str:
        source = {
            k: v for k, v in row.items()
            if k not in {"review_status", "canonical_write_performed"}
        }
        return sha256_bytes(canonical_json_bytes(source))

    def _write(
        self,
        rows: Iterable[GameKnowledgeCandidate],
        *,
        tombstones: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        if tombstones is None:
            tombstones = self._tombstones()
        payload = {
            "schema_version": "1.0.0",
            "records": [row.to_dict() for row in sorted(rows, key=lambda x: (x.knowledge_kind.value, x.effective_name_ja, x.candidate_id))],
            "tombstones": [tombstones[key] for key in sorted(tombstones)],
        }
        fd, raw = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        os.close(fd)
        temp = Path(raw)
        try:
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(temp, self.path)
        finally:
            temp.unlink(missing_ok=True)

    def list(self, *, kind: GameKnowledgeKind | None = None) -> tuple[GameKnowledgeCandidate, ...]:
        payload = self._read_payload()
        rows = tuple(GameKnowledgeCandidate.from_dict(row) for row in payload.get("records", ()))
        return tuple(row for row in rows if kind is None or row.knowledge_kind is kind)

    def get(self, candidate_id: str) -> GameKnowledgeCandidate:
        for row in self.list():
            if row.candidate_id == candidate_id:
                return row
        raise KeyError(candidate_id)

    def upsert_external(self, rows: Iterable[GameKnowledgeCandidate]) -> int:
        current = {row.candidate_id: row for row in self.list()}
        tombstones = self._tombstones()
        changed = 0
        for incoming in rows:
            old = current.get(incoming.candidate_id)
            if old is None:
                tombstone = tombstones.get(incoming.candidate_id)
                if tombstone and str(tombstone.get("source_revision_sha256") or "") == incoming.source_revision_sha256:
                    continue
                if tombstone:
                    current[incoming.candidate_id] = replace(
                        incoming,
                        details={**incoming.details, "_previous_tombstone": tombstone},
                        review_status="CANDIDATE",
                    )
                    tombstones.pop(incoming.candidate_id, None)
                    changed += 1
                    continue
                current[incoming.candidate_id] = incoming
                changed += 1
                continue
            if old.source_revision_sha256 == incoming.source_revision_sha256:
                continue
            status = old.review_status
            if status == "DISABLED" and isinstance(old.details.get("_tombstone"), dict):
                details = dict(old.details)
                details["_pending_external_update"] = incoming.to_dict()
                current[incoming.candidate_id] = replace(
                    old, details=details, updated_at=utc_now_iso(),
                )
            elif status in {"VERIFIED", "UPDATE_AVAILABLE"}:
                # Keep the last Human-verified source record active. A newer external
                # snapshot is review evidence only until the owner explicitly accepts it.
                pending = incoming.to_dict()
                details = dict(old.details)
                details["_pending_external_update"] = pending
                current[incoming.candidate_id] = replace(
                    old, review_status="UPDATE_AVAILABLE", details=details, updated_at=utc_now_iso(),
                )
            else:
                if status not in {"REJECTED", "DISABLED"}:
                    status = "CANDIDATE"
                current[incoming.candidate_id] = replace(
                    incoming,
                    review_status=status,
                    enabled=old.enabled,
                    manual_name_ja=old.manual_name_ja,
                    manual_name_en=old.manual_name_en,
                    manual_aliases_ja=old.manual_aliases_ja,
                    manual_image_path=old.manual_image_path,
                    updated_at=utc_now_iso(),
                )
            changed += 1
        self._write(current.values(), tombstones=tombstones)
        return changed

    def edit(
        self,
        candidate_id: str,
        *,
        name_ja: str | None = None,
        name_en: str | None = None,
        aliases_ja: Iterable[str] | None = None,
        image_path: str | None = None,
        enabled: bool | None = None,
    ) -> GameKnowledgeCandidate:
        rows = {row.candidate_id: row for row in self.list()}
        row = rows[candidate_id]
        new_status = "NEEDS_REVIEW" if row.review_status in {"VERIFIED", "UPDATE_AVAILABLE"} else row.review_status
        if enabled is False:
            new_status = "DISABLED"
        elif enabled is True and row.review_status == "DISABLED":
            new_status = "NEEDS_REVIEW"
        details = dict(row.details)
        if enabled is True:
            details.pop("_tombstone", None)
        updated = replace(
            row,
            manual_name_ja=row.manual_name_ja if name_ja is None else name_ja.strip(),
            manual_name_en=row.manual_name_en if name_en is None else name_en.strip(),
            manual_aliases_ja=row.manual_aliases_ja if aliases_ja is None else tuple(dict.fromkeys(x.strip() for x in aliases_ja if x.strip())),
            manual_image_path=row.manual_image_path if image_path is None else image_path.strip(),
            enabled=row.enabled if enabled is None else bool(enabled),
            review_status=new_status,
            details=details,
            updated_at=utc_now_iso(),
        )
        rows[candidate_id] = updated
        tombstones = self._tombstones()
        if enabled is True:
            tombstones.pop(candidate_id, None)
        self._write(rows.values(), tombstones=tombstones)
        return updated

    def set_status(self, candidate_id: str, status: str) -> GameKnowledgeCandidate:
        if status not in _REVIEW_VALUES:
            raise ValueError("unsupported review status")
        rows = {row.candidate_id: row for row in self.list()}
        row = rows[candidate_id]
        pending = row.details.get("_pending_external_update") if isinstance(row.details, dict) else None
        if status == "VERIFIED" and isinstance(pending, dict):
            incoming = GameKnowledgeCandidate.from_dict(dict(pending))
            updated = replace(
                incoming, review_status="VERIFIED", enabled=row.enabled,
                manual_name_ja=row.manual_name_ja, manual_name_en=row.manual_name_en,
                manual_aliases_ja=row.manual_aliases_ja, manual_image_path=row.manual_image_path,
                details={k: v for k, v in incoming.details.items() if k != "_pending_external_update"},
                updated_at=utc_now_iso(),
            )
        else:
            details = (
                {
                    k: v for k, v in row.details.items()
                    if k != "_pending_external_update" and not (status == "VERIFIED" and k == "_tombstone")
                }
                if status != "UPDATE_AVAILABLE" else row.details
            )
            updated = replace(row, review_status=status, enabled=status != "DISABLED", details=details, updated_at=utc_now_iso())
        rows[candidate_id] = updated
        tombstones = self._tombstones()
        if status == "VERIFIED":
            tombstones.pop(candidate_id, None)
        self._write(rows.values(), tombstones=tombstones)
        return updated

    @staticmethod
    def _contains_candidate_ref(value: object, candidate_id: str) -> bool:
        if isinstance(value, str):
            return value == candidate_id
        if isinstance(value, dict):
            return any(
                GameKnowledgeReviewCatalog._contains_candidate_ref(item, candidate_id)
                for item in value.values()
            )
        if isinstance(value, (list, tuple, set)):
            return any(
                GameKnowledgeReviewCatalog._contains_candidate_ref(item, candidate_id)
                for item in value
            )
        return False

    @staticmethod
    def _human_touched(row: GameKnowledgeCandidate) -> bool:
        return bool(
            row.review_status != "CANDIDATE"
            or row.manual_name_ja.strip()
            or row.manual_name_en.strip()
            or row.manual_aliases_ja
            or row.manual_image_path.strip()
        )

    def preview_delete(
        self,
        candidate_id: str,
        *,
        external_dependencies: Iterable[KnowledgeDependencyReference] = (),
    ) -> KnowledgeDeleteImpact:
        rows = self.list()
        target = next((row for row in rows if row.candidate_id == candidate_id), None)
        if target is None:
            raise KeyError(candidate_id)
        dependencies = list(external_dependencies)
        human_touched = self._human_touched(target)
        if human_touched:
            dependencies.append(KnowledgeDependencyReference(
                kind="HUMAN_REVIEW_STATE",
                reference_id=target.review_status,
                description="Human確認状態または手動overrideを保持",
                protected=True,
            ))
        if target.effective_image:
            dependencies.append(KnowledgeDependencyReference(
                kind="CACHED_ASSET_RETAINED",
                reference_id=target.candidate_id,
                description="画像assetは監査・再利用のため保持",
                protected=False,
            ))
        dependencies.extend(
            KnowledgeDependencyReference(
                kind="CATALOG_RELATION",
                reference_id=row.candidate_id,
                description=f"{row.effective_name_ja} の詳細情報から参照",
                protected=True,
            )
            for row in rows
            if row.candidate_id != candidate_id
            and self._contains_candidate_ref(row.details, candidate_id)
        )
        unique = {
            (item.kind, item.reference_id, item.description, item.protected): item
            for item in dependencies
        }
        ordered = tuple(sorted(unique.values(), key=lambda item: (item.kind, item.reference_id, item.description)))
        protected_count = sum(1 for item in ordered if item.protected)
        rebuildable_count = len(ordered) - protected_count
        action = "REMOVE_CANDIDATE" if not human_touched and protected_count == 0 else "TOMBSTONE"
        fingerprint_payload = {
            "candidate_id": candidate_id,
            "updated_at": target.updated_at,
            "review_status": target.review_status,
            "action": action,
            "dependencies": [
                {
                    "kind": item.kind,
                    "reference_id": item.reference_id,
                    "protected": item.protected,
                }
                for item in ordered
            ],
        }
        return KnowledgeDeleteImpact(
            candidate_id=candidate_id,
            action=action,
            review_status=target.review_status,
            human_touched=human_touched,
            dependencies=ordered,
            protected_count=protected_count,
            rebuildable_count=rebuildable_count,
            fingerprint=sha256_bytes(canonical_json_bytes(fingerprint_payload)),
        )

    def delete_safely(
        self,
        candidate_id: str,
        *,
        expected_fingerprint: str,
        external_dependencies: Iterable[KnowledgeDependencyReference] = (),
        reason: str = "owner_requested_from_training_studio",
    ) -> KnowledgeDeleteResult:
        dependencies = tuple(external_dependencies)
        impact = self.preview_delete(candidate_id, external_dependencies=dependencies)
        if impact.fingerprint != expected_fingerprint:
            raise ValueError("delete impact changed; preview again before deleting")
        rows = {row.candidate_id: row for row in self.list()}
        row = rows[candidate_id]
        tombstones = self._tombstones()
        tombstone = {
            "candidate_id": candidate_id,
            "source_revision_sha256": row.source_revision_sha256,
            "deleted_at": utc_now_iso(),
            "reason": reason.strip()[:256] or "owner_requested",
            "action": impact.action,
        }
        tombstones[candidate_id] = tombstone
        retained = impact.action == "TOMBSTONE"
        if retained:
            rows[candidate_id] = replace(
                row,
                review_status="DISABLED",
                enabled=False,
                details={**row.details, "_tombstone": tombstone},
                updated_at=utc_now_iso(),
            )
        else:
            rows.pop(candidate_id)
        self._write(rows.values(), tombstones=tombstones)
        return KnowledgeDeleteResult(
            candidate_id=candidate_id,
            action=impact.action,
            retained_catalog_row=retained,
            tombstone_recorded=True,
        )

    def search(self, query: str = "", *, kind: GameKnowledgeKind | None = None, status: str | None = None) -> tuple[GameKnowledgeCandidate, ...]:
        needle = query.strip().casefold()
        rows = self.list(kind=kind)
        out: list[GameKnowledgeCandidate] = []
        for row in rows:
            if status and row.review_status != status:
                continue
            hay = "\n".join((row.effective_name_ja, row.effective_name_en, *row.effective_aliases_ja, row.candidate_id)).casefold()
            if needle and needle not in hay:
                continue
            out.append(row)
        return tuple(out)


def candidate_from_normalized(row: dict[str, Any], kind: GameKnowledgeKind) -> GameKnowledgeCandidate:
    name = str(row.get("name_ja") or row.get("map_name_ja") or row.get("realm_name_ja") or "").strip()
    aliases = tuple(str(x).strip() for x in row.get("aliases_ja", ()) if str(x).strip())
    image_urls = tuple(str(x).strip() for x in row.get("image_urls", ()) if str(x).strip())
    source = str(row.get("detail_url") or row.get("source_page_url") or "kamigame://candidate")
    details = {k: v for k, v in row.items() if k not in {
        "candidate_id", "name_ja", "aliases_ja", "image_urls", "detail_url", "source_page_url", "review_status",
        "source_authority", "schema_version", "record_kind",
    }}
    source_hash = GameKnowledgeReviewCatalog._source_hash(row)
    return GameKnowledgeCandidate(
        candidate_id=str(row["candidate_id"]),
        knowledge_kind=kind,
        name_ja=name,
        name_en=str(row.get("name_en", "")),
        aliases_ja=aliases,
        image_urls=image_urls,
        source_page_url=source,
        review_status=str(row.get("review_status", "CANDIDATE")),
        details=details,
        source_revision_sha256=source_hash,
    )


__all__ = [
    "GameKnowledgeCandidate", "GameKnowledgeReviewCatalog", "KnowledgeDeleteImpact",
    "KnowledgeDeleteResult", "KnowledgeDependencyReference", "candidate_from_normalized",
]
