"""TASK-058 immutable advisory Profile transport and readiness evidence."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Mapping

from .montage_learning_file_bridge import (
    BridgeLayout,
    load_bridge_owner,
    publish_current_profile,
)
from .serialization import sha256_json


_BINDING_TOKEN = object()
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_CONTEXT_MARKER_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:transcript|password|secret|api[_ ]key|access[_ ]token)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
_ALLOWED_BRIDGE_STATES = frozenset(
    {"NOT_PROVISIONED", "OWNERSHIP_UNVERIFIED", "AVAILABLE"}
)
_ALLOWED_IMPORT_STATES = frozenset(
    {
        "NO_DELIVERY",
        "PENDING",
        "OBSERVATION_RECORDED",
        "EXACT_ACCEPTED",
        "DUPLICATE",
        "REJECTED",
        "RECOVERY_REQUIRED",
    }
)
_ALLOWED_PROFILE_STATES = frozenset(
    {"SOURCE_NOT_BOUND", "PUBLISHED", "LOAD_PASS", "STALE", "INVALID"}
)
_ALLOWED_ADAPTER_STATES = frozenset(
    {
        "NOT_RUN",
        "CONNECTOR_READY",
        "PUBLISH_STAGED",
        "MATCHING_RECEIPT_PASS",
        "LOAD_PROFILE_PASS",
        "FAIL",
    }
)
_DELIVERY_FIELDS = {
    "schema_version",
    "message_type",
    "contract_profile",
    "profile_contract",
    "profile_id",
    "profile_version",
    "owner_scope_hash",
    "source_record_count",
    "profile_sha256",
    "advisory_only",
    "canonical_timeline",
    "auto_apply_authorized",
    "payload",
}
_PREFERENCE_FIELDS = {
    "preference_id",
    "decision",
    "target",
    "contexts",
    "confidence",
    "confirmation_count",
    "reason_codes",
    "ranking_bias",
}


class MontageLearningConnectorReadinessError(ValueError):
    """Raised when Profile transport or readiness claims are invalid."""


class ProfileSourceBinding:
    """Sealed capability separating fixture compatibility from production source."""

    __slots__ = ("source_id", "production_profile_source_bound", "isolated_fixture")

    def __init__(
        self,
        *,
        source_id: str | None,
        production_profile_source_bound: bool,
        isolated_fixture: bool,
        _token: object | None = None,
    ) -> None:
        if _token is not _BINDING_TOKEN:
            raise TypeError("ProfileSourceBinding must use a sealed constructor")
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(
            self,
            "production_profile_source_bound",
            production_profile_source_bound,
        )
        object.__setattr__(self, "isolated_fixture", isolated_fixture)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ProfileSourceBinding is immutable")

    @classmethod
    def unbound_production(cls) -> "ProfileSourceBinding":
        return cls(
            source_id=None,
            production_profile_source_bound=False,
            isolated_fixture=False,
            _token=_BINDING_TOKEN,
        )

    @classmethod
    def bound_isolated_fixture(
        cls,
        *,
        source_id: str = "canonical-prebuilt-advisory-fixture",
    ) -> "ProfileSourceBinding":
        _require_id(source_id, "source_id")
        return cls(
            source_id=source_id,
            production_profile_source_bound=False,
            isolated_fixture=True,
            _token=_BINDING_TOKEN,
        )


@dataclass(frozen=True, slots=True)
class ProfilePublishResult:
    status: str
    profile_id: str | None
    profile_sha256: str | None
    written: bool
    production_profile_source_bound: bool
    semantic_projection_generated: bool = False
    timeline_mutation_authorized: bool = False
    resolve_write_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "profile_id": self.profile_id,
            "profile_sha256": self.profile_sha256,
            "written": self.written,
            "production_profile_source_bound": self.production_profile_source_bound,
            "semantic_projection_generated": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }


@dataclass(frozen=True, slots=True)
class ConnectorReadinessEvidence:
    bridge_state: str
    import_state: str
    profile_state: str
    adapter_state: str
    production_profile_source_bound: bool
    adapter_contract_e2e_pass: bool
    default_skill_config_unchanged: bool
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field, allowed in (
            ("bridge_state", _ALLOWED_BRIDGE_STATES),
            ("import_state", _ALLOWED_IMPORT_STATES),
            ("profile_state", _ALLOWED_PROFILE_STATES),
            ("adapter_state", _ALLOWED_ADAPTER_STATES),
        ):
            value = getattr(self, field)
            if type(value) is not str or value not in allowed:
                raise MontageLearningConnectorReadinessError(
                    f"{field} is invalid"
                )
        for field in (
            "production_profile_source_bound",
            "adapter_contract_e2e_pass",
            "default_skill_config_unchanged",
        ):
            if type(getattr(self, field)) is not bool:
                raise MontageLearningConnectorReadinessError(
                    f"{field} must be a built-in bool"
                )
        if self.production_profile_source_bound is not False:
            raise MontageLearningConnectorReadinessError(
                "production profile source must be exactly false (SOURCE_NOT_BOUND)"
            )
        if self.profile_state != "SOURCE_NOT_BOUND":
            raise MontageLearningConnectorReadinessError(
                "profile_state must be SOURCE_NOT_BOUND"
            )
        if type(self.reason_codes) is not tuple:
            raise MontageLearningConnectorReadinessError(
                "reason_codes must be a tuple"
            )
        for reason in self.reason_codes:
            _require_token(reason, "reason_code")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "message_type": "BvpMontageLearningConnectorReadiness",
            "task_id": "TASK-058",
            "bridge_state": self.bridge_state,
            "import_state": self.import_state,
            "profile_state": (
                self.profile_state
                if self.production_profile_source_bound
                else "SOURCE_NOT_BOUND"
            ),
            "adapter_state": self.adapter_state,
            "activation_state": "BLOCKED",
            "connector_enabled": False,
            "activation_authorized": False,
            "production_profile_source_bound": self.production_profile_source_bound,
            "adapter_contract_e2e_pass": self.adapter_contract_e2e_pass,
            "default_skill_config_unchanged": self.default_skill_config_unchanged,
            "learning_adoption_authorized": False,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "reason_codes": list(self.reason_codes),
        }


def publish_prebuilt_advisory_profile(
    layout: BridgeLayout,
    envelope: Mapping[str, object],
    *,
    source_binding: ProfileSourceBinding,
    expected_previous_profile_sha256: str | None = None,
) -> ProfilePublishResult:
    """Revalidate and copy a prebuilt SKILL v1 envelope without derivation."""

    load_bridge_owner(layout)
    if source_binding.production_profile_source_bound is False and not (
        source_binding.isolated_fixture and not layout.production_path
    ):
        return ProfilePublishResult(
            status="SOURCE_NOT_BOUND",
            profile_id=None,
            profile_sha256=None,
            written=False,
            production_profile_source_bound=False,
        )
    if layout.production_path and source_binding.isolated_fixture:
        raise MontageLearningConnectorReadinessError(
            "isolated fixture binding cannot publish to production layout"
        )
    value = validate_prebuilt_advisory_profile(envelope)
    status = publish_current_profile(
        layout,
        value,
        expected_previous_profile_sha256=expected_previous_profile_sha256,
    )
    return ProfilePublishResult(
        status=status,
        profile_id=value["profile_id"],
        profile_sha256=value["profile_sha256"],
        written=status == "PUBLISHED",
        # Fixture PASS is transport compatibility, never a production binding.
        production_profile_source_bound=source_binding.production_profile_source_bound,
    )


def validate_prebuilt_advisory_profile(
    envelope: Mapping[str, object],
) -> dict[str, Any]:
    """Strict independent mirror of the SKILL v1 Profile delivery contract."""

    value = _plain_snapshot(envelope, path="$", max_depth=16)
    if type(value) is not dict or set(value) != _DELIVERY_FIELDS:
        raise MontageLearningConnectorReadinessError("profile delivery fields mismatch")
    constants = {
        "schema_version": "1.0.0",
        "message_type": "BvpMontagePreferenceProfileDelivery",
        "contract_profile": "bvp-task029-file-bridge-v1",
        "profile_contract": "bvp-task029-montage-preference-projection-v1",
        "advisory_only": True,
        "canonical_timeline": False,
        "auto_apply_authorized": False,
    }
    for field, expected in constants.items():
        if value[field] != expected or type(value[field]) is not type(expected):
            raise MontageLearningConnectorReadinessError(
                f"profile delivery {field} mismatch"
            )
    _require_id(value["profile_id"], "profile_id")
    version = value["profile_version"]
    if isinstance(version, bool) or not (
        (type(version) is int and version >= 0)
        or (type(version) is str and bool(version.strip()))
    ):
        raise MontageLearningConnectorReadinessError("profile_version is invalid")
    _require_sha(value["owner_scope_hash"], "owner_scope_hash")
    count = value["source_record_count"]
    if isinstance(count, bool) or type(count) is not int or count < 0:
        raise MontageLearningConnectorReadinessError(
            "source_record_count is invalid"
        )
    supplied_hash = _require_sha(value["profile_sha256"], "profile_sha256")
    payload = _validate_projection(value["payload"])
    if sha256_json(payload) != supplied_hash:
        raise MontageLearningConnectorReadinessError("profile_sha256 mismatch")
    value["payload"] = payload
    return value


def production_readiness_evidence(
    *,
    bridge_state: str,
    import_state: str,
    adapter_state: str,
    adapter_contract_e2e_pass: bool,
    default_skill_config_unchanged: bool,
) -> ConnectorReadinessEvidence:
    """Return honest Batch evidence while the production producer is unbound."""

    return ConnectorReadinessEvidence(
        bridge_state=bridge_state,
        import_state=import_state,
        profile_state="SOURCE_NOT_BOUND",
        adapter_state=adapter_state,
        production_profile_source_bound=False,
        adapter_contract_e2e_pass=adapter_contract_e2e_pass,
        default_skill_config_unchanged=default_skill_config_unchanged,
        reason_codes=("SOURCE_NOT_BOUND",),
    )


def _validate_projection(value: object) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"projection_version", "preferences"}:
        raise MontageLearningConnectorReadinessError("projection fields mismatch")
    if value["projection_version"] != "1.0.0":
        raise MontageLearningConnectorReadinessError("projection version mismatch")
    preferences = value["preferences"]
    if type(preferences) is not list or len(preferences) > 1000:
        raise MontageLearningConnectorReadinessError("preferences are invalid")
    seen: set[str] = set()
    for index, item in enumerate(preferences):
        if type(item) is not dict or set(item) != _PREFERENCE_FIELDS:
            raise MontageLearningConnectorReadinessError(
                f"preference {index} fields mismatch"
            )
        preference_id = _require_id(item["preference_id"], "preference_id")
        if preference_id in seen:
            raise MontageLearningConnectorReadinessError(
                "duplicate preference_id"
            )
        seen.add(preference_id)
        if item["decision"] not in {"PREFER", "AVOID", "PROTECT", "DEPRIORITIZE"}:
            raise MontageLearningConnectorReadinessError("decision is invalid")
        _require_token(item["target"], "target")
        contexts = item["contexts"]
        if type(contexts) is not list or not 1 <= len(contexts) <= 16:
            raise MontageLearningConnectorReadinessError("contexts are invalid")
        for context in contexts:
            _validate_preference_context(context)
        for field, low, high in (
            ("confidence", 0.0, 1.0),
            ("ranking_bias", -1.0, 1.0),
        ):
            number = item[field]
            if isinstance(number, bool) or type(number) not in {int, float}:
                raise MontageLearningConnectorReadinessError(f"{field} is invalid")
            if not math.isfinite(float(number)) or not low <= number <= high:
                raise MontageLearningConnectorReadinessError(f"{field} is invalid")
        confirmation_count = item["confirmation_count"]
        if (
            isinstance(confirmation_count, bool)
            or type(confirmation_count) is not int
            or confirmation_count < 1
        ):
            raise MontageLearningConnectorReadinessError(
                "confirmation_count is invalid"
            )
        reasons = item["reason_codes"]
        if type(reasons) is not list or not 1 <= len(reasons) <= 16:
            raise MontageLearningConnectorReadinessError("reason_codes are invalid")
        for reason in reasons:
            _require_token(reason, "reason_code")
    return value


def _plain_snapshot(value: object, *, path: str, max_depth: int) -> Any:
    if max_depth < 0:
        raise MontageLearningConnectorReadinessError("profile nesting is too deep")
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise MontageLearningConnectorReadinessError(f"{path} is not finite")
        return value
    if type(value) is list:
        return [
            _plain_snapshot(item, path=f"{path}[{index}]", max_depth=max_depth - 1)
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise MontageLearningConnectorReadinessError(f"{path} has invalid key")
        return {
            key: _plain_snapshot(
                child,
                path=f"{path}.{key}",
                max_depth=max_depth - 1,
            )
            for key, child in value.items()
        }
    raise MontageLearningConnectorReadinessError(
        f"{path} must contain built-in JSON values only"
    )


def _require_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise MontageLearningConnectorReadinessError(f"{field} is invalid")
    return value


def _require_sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise MontageLearningConnectorReadinessError(f"{field} is invalid")
    return value


def _require_token(value: object, field: str) -> str:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None:
        raise MontageLearningConnectorReadinessError(f"{field} is invalid")
    return value


def _validate_preference_context(value: object) -> str:
    """Validate private/free-form source material used as a preference context."""

    if type(value) is not str or not 1 <= len(value) <= 128:
        raise MontageLearningConnectorReadinessError("context is invalid")
    if any(char in value for char in "/\\@") or any(
        ord(char) < 32 or ord(char) == 127 for char in value
    ):
        raise MontageLearningConnectorReadinessError(
            "context contains invalid private/free-form source material"
        )
    if _CONTEXT_MARKER_RE.search(value) is not None:
        raise MontageLearningConnectorReadinessError(
            "context contains restricted private/free-form source material"
        )
    return value


__all__ = [
    "ConnectorReadinessEvidence",
    "MontageLearningConnectorReadinessError",
    "ProfilePublishResult",
    "ProfileSourceBinding",
    "production_readiness_evidence",
    "publish_prebuilt_advisory_profile",
    "validate_prebuilt_advisory_profile",
]
