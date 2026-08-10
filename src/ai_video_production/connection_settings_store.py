"""Safe persistence and GUI-neutral form projection for AI connections."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any, Mapping

from .ai_connections import AiConnectionProfile, AiWorkload, SelectionMode
from .atomic import AtomicJsonWriter, AtomicWriteResult, FailureInjector
from .connection_settings import SettingsPreflightReport
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


SETTINGS_STORE_SCHEMA_VERSION = "1.0.0"
FORM_SCHEMA_VERSION = "1.0.0"


def _document_checksum(body: Mapping[str, object]) -> str:
    return sha256_bytes(canonical_json_bytes(dict(body)))


@dataclass(frozen=True, slots=True)
class ConnectionSettingsRecord:
    revision: int
    profile: AiConnectionProfile
    migrated_from: str | None = None

    def __post_init__(self) -> None:
        if self.revision < 0:
            raise ValueError("settings revision must be non-negative")

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": SETTINGS_STORE_SCHEMA_VERSION,
            "revision": self.revision,
            "profile": self.profile.to_dict(),
        }
        body["document_sha256"] = _document_checksum(body)
        return body

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> "ConnectionSettingsRecord":
        if document.get("schema_version") != SETTINGS_STORE_SCHEMA_VERSION:
            raise ValueError("unsupported connection settings schema_version")
        expected = document.get("document_sha256")
        body = {key: value for key, value in document.items() if key != "document_sha256"}
        if expected != _document_checksum(body):
            raise ValueError("connection settings checksum mismatch")
        return cls(
            revision=document["revision"],
            profile=AiConnectionProfile.from_dict(document["profile"]),
        )


@dataclass(frozen=True, slots=True)
class ConnectionSettingsLoadResult:
    record: ConnectionSettingsRecord
    migrated_from: str | None = None


@dataclass(frozen=True, slots=True)
class ConnectionSettingsSaveResult:
    record: ConnectionSettingsRecord
    write: AtomicWriteResult


class ConnectionSettingsStore:
    """Persist settings without secrets and reject stale or damaged updates."""

    @staticmethod
    def load(path: str | Path) -> ConnectionSettingsLoadResult:
        source = Path(path)
        try:
            document = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("connection settings document must be an object")
            if "profile" in document:
                return ConnectionSettingsLoadResult(ConnectionSettingsRecord.from_dict(document))
            # 0.8.0 could persist the raw profile document. Read it once and
            # wrap it in the current envelope on the next explicit save.
            if document.get("schema_version") == "1.0.0" and "profile_id" in document:
                profile = AiConnectionProfile.from_dict(document)
                migrated_from = "ai-connection-profile/1.0.0"
                return ConnectionSettingsLoadResult(
                    ConnectionSettingsRecord(0, profile, migrated_from), migrated_from
                )
            raise ValueError("unrecognized connection settings document")
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_CONNECTION_SETTINGS_INTEGRITY",
                "AI connection settings could not be read safely",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"reason": type(exc).__name__},
            ) from exc

    @classmethod
    def save(
        cls,
        path: str | Path,
        profile: AiConnectionProfile,
        *,
        expected_revision: int | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> ConnectionSettingsSaveResult:
        target = Path(path)
        current_revision: int | None = None
        if target.exists():
            current_revision = cls.load(target).record.revision
            if expected_revision is None or expected_revision != current_revision:
                raise ProductError(
                    "ERR_CONNECTION_SETTINGS_CONFLICT",
                    "AI connection settings changed since the screen was opened",
                    ProductErrorCategory.STATE,
                    details={
                        "expected_revision": expected_revision,
                        "current_revision": current_revision,
                    },
                )
        elif expected_revision not in {None, 0}:
            raise ProductError(
                "ERR_CONNECTION_SETTINGS_CONFLICT",
                "AI connection settings do not exist at the expected revision",
                ProductErrorCategory.STATE,
                details={"expected_revision": expected_revision, "current_revision": None},
            )

        record = ConnectionSettingsRecord((current_revision or 0) + 1, profile)

        def validate(document: Any) -> None:
            if not isinstance(document, dict):
                raise ValueError("connection settings document must be an object")
            ConnectionSettingsRecord.from_dict(document)

        write = AtomicJsonWriter.write(
            target,
            record.to_dict(),
            validator=validate,
            failure_injector=failure_injector,
        )
        return ConnectionSettingsSaveResult(record, write)


class ConnectionSettingsFormBuilder:
    """Create a low-literacy UI contract without secret or machine details."""

    _LABELS = {
        AiWorkload.PLANNING: ("企画・台本", "Planning & script"),
        AiWorkload.VIDEO: ("動画", "Video"),
        AiWorkload.IMAGE: ("画像", "Image"),
        AiWorkload.AUDIO: ("音声・効果音", "Voice & sound effects"),
        AiWorkload.MUSIC: ("音楽", "Music"),
    }
    _MODE_HELP = {
        SelectionMode.AI: ("AIモデルだけを使います", "Use AI models only"),
        SelectionMode.FREE: ("無料で使える候補だけを使います", "Use free options only"),
        SelectionMode.AUTO: ("利用可能な候補から自動で選びます", "Choose automatically from available options"),
        SelectionMode.OFFLINE_ONLY: ("このパソコン内で動く候補だけを使います", "Use options that run on this computer only"),
        SelectionMode.DISABLED: ("この機能では外部素材を作りません", "Do not create assets for this workload"),
    }
    _STATUS_HELP = {
        "READY": ("準備できています", "Ready to use"),
        "DISABLED": ("使用しない設定です", "This workload is disabled"),
        "BLOCKED": ("設定が不足しています。詳細を確認してください", "Setup is incomplete; review the details"),
    }

    @classmethod
    def build(
        cls,
        profile: AiConnectionProfile,
        preflight: SettingsPreflightReport,
        *,
        revision: int = 0,
    ) -> dict[str, object]:
        if profile.profile_id != preflight.profile_id or profile.profile_version != preflight.profile_version:
            raise ValueError("profile and preflight do not match")
        statuses = {item.workload: item for item in preflight.workloads}
        workloads: list[dict[str, object]] = []
        for workload in AiWorkload:
            status = statuses[workload]
            ja, en = cls._LABELS[workload]
            status_ja, status_en = cls._STATUS_HELP[status.status.value]
            routes = []
            configured_routes = sorted(
                (item for item in profile.routes if item.workload is workload),
                key=lambda item: (item.priority, item.route_id),
            )
            for route in configured_routes:
                routes.append({
                    "route_id": route.route_id,
                    "provider_family": route.provider_family.value,
                    "provider_id": route.provider_id,
                    "model_id": route.model_id,
                    "cost_class": route.cost_class.value,
                    "reasoning_effort": route.reasoning_effort.value,
                    "capabilities": list(route.capabilities),
                    "credential_required": route.credential_ref is not None,
                    "enabled": route.enabled,
                })
            workloads.append({
                "workload": workload.value,
                "label": {"ja": ja, "en": en},
                "selection_mode": profile.mode_for(workload).value,
                "mode_options": [mode.value for mode in SelectionMode],
                "mode_help": {
                    mode.value: {"ja": cls._MODE_HELP[mode][0], "en": cls._MODE_HELP[mode][1]}
                    for mode in SelectionMode
                },
                "status": status.status.value,
                "status_message": {"ja": status_ja, "en": status_en},
                "error_code": status.error_code,
                "selected_route_id": status.selected_route_id,
                "preferred_route_id": configured_routes[0].route_id if configured_routes else None,
                "routes": routes,
            })
        return {
            "form_schema_version": FORM_SCHEMA_VERSION,
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "revision": revision,
            "save_does_not_authorize_generation": True,
            "workloads": workloads,
            "preflight_sha256": preflight.to_dict()["report_sha256"],
        }


class ConnectionSettingsEditor:
    """Apply the narrow set of edits authorized for the first settings screen."""

    @staticmethod
    def apply(
        profile: AiConnectionProfile,
        *,
        workload_modes: Mapping[str, str],
        preferred_route_ids: Mapping[str, str | None],
    ) -> AiConnectionProfile:
        known_workloads = {item.value: item for item in AiWorkload}
        if set(workload_modes) != set(known_workloads):
            raise ValueError("workload_modes must contain every workload exactly once")
        if not set(preferred_route_ids).issubset(known_workloads):
            raise ValueError("preferred_route_ids contains an unknown workload")

        modes = {
            known_workloads[key]: SelectionMode(value)
            for key, value in workload_modes.items()
        }
        preferred: dict[AiWorkload, str] = {}
        route_owners = {route.route_id: route.workload for route in profile.routes}
        for key, route_id in preferred_route_ids.items():
            workload = known_workloads[key]
            if route_id is None:
                continue
            if route_owners.get(route_id) is not workload:
                raise ValueError("preferred route does not belong to workload")
            preferred[workload] = route_id

        routes = []
        for route in profile.routes:
            selected = preferred.get(route.workload)
            if selected is None:
                routes.append(route)
            elif route.route_id == selected:
                routes.append(replace(route, priority=0))
            else:
                routes.append(replace(route, priority=max(1, route.priority)))
        return AiConnectionProfile(
            profile.profile_id,
            profile.profile_version,
            profile.default_mode,
            tuple(routes),
            modes,
        )
