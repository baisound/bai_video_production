"""TASK-009 deterministic DBD profile plugin contract.

This module declares how exact upstream feature coordinates may be scored and
classified.  It performs no HUD/event detection, media I/O, game integration,
provider call, filesystem access, subprocess execution, or edit mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from .multimodal_scoring import FeatureRule, ScoringProfile
from .profile import PluginDescriptor
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_MAX_SIGNALS = 64


class DBDSignalFamily(str, Enum):
    HUD_STATE = "HUD_STATE"
    CHASE = "CHASE"
    EVENT = "EVENT"


class DBDSignalKind(str, Enum):
    HUD_SURVIVOR_HEALTH = "HUD_SURVIVOR_HEALTH"
    HUD_GENERATOR_PROGRESS = "HUD_GENERATOR_PROGRESS"
    CHASE_INTENSITY = "CHASE_INTENSITY"
    EVENT_HOOK = "EVENT_HOOK"
    EVENT_RESCUE = "EVENT_RESCUE"
    EVENT_EXIT_GATE = "EVENT_EXIT_GATE"
    EVENT_MATCH_OUTCOME = "EVENT_MATCH_OUTCOME"


_SIGNAL_FAMILY = {
    DBDSignalKind.HUD_SURVIVOR_HEALTH: DBDSignalFamily.HUD_STATE,
    DBDSignalKind.HUD_GENERATOR_PROGRESS: DBDSignalFamily.HUD_STATE,
    DBDSignalKind.CHASE_INTENSITY: DBDSignalFamily.CHASE,
    DBDSignalKind.EVENT_HOOK: DBDSignalFamily.EVENT,
    DBDSignalKind.EVENT_RESCUE: DBDSignalFamily.EVENT,
    DBDSignalKind.EVENT_EXIT_GATE: DBDSignalFamily.EVENT,
    DBDSignalKind.EVENT_MATCH_OUTCOME: DBDSignalFamily.EVENT,
}


@dataclass(frozen=True, slots=True)
class DBDSignalRule:
    signal_kind: DBDSignalKind
    family: DBDSignalFamily
    feature_rule: FeatureRule

    def __post_init__(self) -> None:
        if not isinstance(self.signal_kind, DBDSignalKind):
            raise ValueError("signal_kind must be a DBDSignalKind")
        if not isinstance(self.family, DBDSignalFamily):
            raise ValueError("family must be a DBDSignalFamily")
        if _SIGNAL_FAMILY[self.signal_kind] is not self.family:
            raise ValueError("signal kind does not belong to the declared family")
        if not isinstance(self.feature_rule, FeatureRule):
            raise ValueError("feature_rule must be a TASK-008 FeatureRule")

    @property
    def key(self) -> tuple[str, str]:
        return (self.feature_rule.feature_key, self.signal_kind.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_kind": self.signal_kind.value,
            "family": self.family.value,
            "feature_key": self.feature_rule.feature_key,
        }


@dataclass(frozen=True, slots=True)
class DBDProfilePluginSnapshot:
    plugin_version: str
    scoring_profile: ScoringProfile
    signal_rules: tuple[DBDSignalRule, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.plugin_version, str) or not _SEMVER_RE.fullmatch(self.plugin_version):
            raise ValueError("plugin_version must be semantic version x.y.z")
        if not isinstance(self.scoring_profile, ScoringProfile):
            raise ValueError("scoring_profile must be a TASK-008 ScoringProfile")
        if not 3 <= len(self.signal_rules) <= _MAX_SIGNALS:
            raise ValueError("signal_rules must contain 3-64 rows")
        if any(not isinstance(item, DBDSignalRule) for item in self.signal_rules):
            raise ValueError("signal_rules must contain DBDSignalRule rows")
        keys = tuple(item.key for item in self.signal_rules)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("signal_rules must be unique and canonically sorted")
        if {item.family for item in self.signal_rules} != set(DBDSignalFamily):
            raise ValueError("signal_rules must cover HUD_STATE, CHASE, and EVENT")
        if tuple(item.feature_rule for item in self.signal_rules) != self.scoring_profile.rules:
            raise ValueError("signal-rule projection must exactly equal scoring-profile rules")

    @property
    def descriptor(self) -> PluginDescriptor:
        descriptor = PluginDescriptor(
            "dbd.multimodal-profile",
            self.plugin_version,
            ("DECLARE_MULTIMODAL_SCORING_PROFILE", "MAP_DBD_SIGNAL_TAXONOMY"),
            ("task008.feature-coordinate.v1",),
            ("task008.scoring-profile.v1", "task009.dbd-profile-snapshot.v1"),
            ("ERR_DBD_PROFILE_INVALID", "ERR_FEATURE_EVIDENCE_MISSING", "ERR_FEATURE_EVIDENCE_UNKNOWN"),
        )
        descriptor.validate_boundary()
        return descriptor

    def to_dict(self) -> dict[str, Any]:
        descriptor = self.descriptor
        body: dict[str, Any] = {
            "snapshot_version": "1.0.0",
            "task_owner": "TASK-009",
            "plugin": {
                "plugin_id": descriptor.plugin_id,
                "version": descriptor.version,
                "capabilities": list(descriptor.capabilities),
                "input_schema_ids": list(descriptor.input_schema_ids),
                "output_schema_ids": list(descriptor.output_schema_ids),
                "failure_codes": list(descriptor.failure_codes),
            },
            "game_profile_identity": "DEAD_BY_DAYLIGHT",
            "scoring_profile": self.scoring_profile.to_dict(),
            "signal_taxonomy": [item.to_dict() for item in self.signal_rules],
            "runtime_feature_producer_state": "NOT_SELECTED",
            "human_review_required": True,
            "media_read_performed": False,
            "hud_detection_performed": False,
            "game_process_accessed": False,
            "automatic_edit_plan_mutation_authorized": False,
            "timeline_mutation_authorized": False,
            "external_effect_authorized": False,
        }
        return {**body, "snapshot_sha256": sha256_bytes(canonical_json_bytes(body))}


def compile_dbd_profile_plugin(
    plugin_version: str,
    profile_version: str,
    signal_rules: Iterable[DBDSignalRule],
) -> DBDProfilePluginSnapshot:
    """Compile authored profile rows into the existing TASK-008 contract."""

    rows = tuple(signal_rules)
    if not 3 <= len(rows) <= _MAX_SIGNALS:
        raise ValueError("signal_rules must contain 3-64 rows")
    if any(not isinstance(item, DBDSignalRule) for item in rows):
        raise ValueError("signal_rules must contain DBDSignalRule rows")
    keys = tuple(item.key for item in rows)
    if keys != tuple(sorted(set(keys))):
        raise ValueError("signal_rules must be unique and canonically sorted")
    profile = ScoringProfile("dbd.multimodal-advisory", profile_version, tuple(item.feature_rule for item in rows))
    return DBDProfilePluginSnapshot(plugin_version, profile, rows)


def verify_dbd_profile_snapshot_hash(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    body = dict(payload)
    claimed = body.pop("snapshot_sha256", None)
    validate_sha256(claimed, field_name="snapshot_sha256")
    profile = body.get("scoring_profile")
    if not isinstance(profile, Mapping):
        raise ValueError("scoring_profile must be a mapping")
    profile_body = dict(profile)
    profile_claimed = profile_body.pop("profile_sha256", None)
    validate_sha256(profile_claimed, field_name="scoring_profile.profile_sha256")
    if profile_claimed != sha256_bytes(canonical_json_bytes(profile_body)):
        raise ValueError("scoring_profile.profile_sha256 does not match its canonical body")
    if claimed != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("snapshot_sha256 does not match the canonical snapshot body")


__all__ = [
    "DBDProfilePluginSnapshot",
    "DBDSignalFamily",
    "DBDSignalKind",
    "DBDSignalRule",
    "compile_dbd_profile_plugin",
    "verify_dbd_profile_snapshot_hash",
]
