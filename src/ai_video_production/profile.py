from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import copy
import json

from .ids import IdKind, generate_id
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso

FORBIDDEN_OVERRIDE_KEYS = {
    "rights_status", "timeline_owner", "write_policy", "legal_hold",
    "voice_consent", "allowed_roots",
}


def _scan_forbidden(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            norm = str(key).lower()
            if norm in FORBIDDEN_OVERRIDE_KEYS:
                raise ValueError(f"override forbidden for {'.'.join(path + (str(key),))}")
            _scan_forbidden(child, path + (str(key),))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            _scan_forbidden(child, path + (str(i),))


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def merge_allowed_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    _scan_forbidden(overrides)
    return _deep_merge(base, overrides)

@dataclass(frozen=True, slots=True)
class ProfileSnapshot:
    profile_snapshot_id: str
    profile_id: str
    profile_version: str
    created_at: str
    checksum: str
    _config_json: str

    @classmethod
    def create(cls, profile_id: str, profile_version: str, config: dict[str, Any]) -> "ProfileSnapshot":
        frozen_bytes = canonical_json_bytes(copy.deepcopy(config))
        return cls(
            generate_id(IdKind.PROFILE_SNAPSHOT),
            profile_id,
            profile_version,
            utc_now_iso(),
            sha256_bytes(frozen_bytes),
            frozen_bytes.decode("utf-8"),
        )

    @property
    def config(self) -> dict[str, Any]:
        # Return a fresh value so callers cannot mutate the canonical snapshot.
        return json.loads(self._config_json)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_snapshot_id": self.profile_snapshot_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "created_at": self.created_at,
            "checksum": self.checksum,
            "config": self.config,
        }

@dataclass(frozen=True, slots=True)
class PluginDescriptor:
    plugin_id: str
    version: str
    capabilities: tuple[str, ...]
    input_schema_ids: tuple[str, ...]
    output_schema_ids: tuple[str, ...]
    failure_codes: tuple[str, ...]

    def validate_boundary(self) -> None:
        forbidden = {"MUTATE_JOB_STATE", "MUTATE_CORE_DB_SCHEMA", "DIRECT_NLE_WRITE"}
        overlap = forbidden.intersection(self.capabilities)
        if overlap:
            raise ValueError(f"plugin declares forbidden core capability: {sorted(overlap)}")
