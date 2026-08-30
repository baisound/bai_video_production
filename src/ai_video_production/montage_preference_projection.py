"""TASK-060 PP-A pure montage preference projection contracts.

This module revalidates already-authoritative TASK-019/TASK-029 in-memory
records and compiles an advisory-only candidate.  It performs no I/O and owns
no Human decision, promotion, transport, Timeline, or Resolve authority.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
import re
from typing import Any

from .human_edit_learning import OwnerDecisionState
from .owner_decision_store import HumanDecision, OwnerDecisionHistory
from .owner_profile_registry_store import OwnerProfileRegistryHistory
from .owner_profile_store import OwnerProfileHistory
from .profile_tuning import ProfileTuningProposal, TuningProposalState, verify_profile_tuning_proposal_hash
from .profile_tuning_owner_decision import OwnerDecisionBindingState, ProfileTuningOwnerDecisionBinding
from .serialization import canonical_json_bytes, sha256_bytes


POLICY_SCHEMA_VERSION = "1.0.0"
PROJECTION_VERSION = "1.0.0"
CONTRACT_PROFILE = "bvp-task029-file-bridge-v1"
PROFILE_CONTRACT = "bvp-task029-montage-preference-projection-v1"
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_STABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_TOKEN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _stable(value: object, field: str) -> str:
    if type(value) is not str or _STABLE_ID.fullmatch(value) is None:
        raise ValueError(f"{field} is invalid")
    return value


def _integer(value: object, field: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{field} must be an integer in {minimum}..{maximum}")
    return value


def _exact_tree(value: object) -> None:
    """Reject caller hooks and scalar subclasses before any serialization."""

    if value is None or type(value) in (str, int, bool):
        return
    if isinstance(value, Enum):
        if type(value.value) is not str:
            raise ValueError("enum value must be an exact string")
        return
    if type(value) in (tuple, list):
        for item in value:
            _exact_tree(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("object keys must be exact strings")
            _exact_tree(item)
        return
    if is_dataclass(value) and type(value).__module__.startswith("ai_video_production"):
        for field in fields(value):
            _exact_tree(getattr(value, field.name))
        return
    raise ValueError("custom containers, hooks, and scalar subclasses are forbidden")


class ChangeDirection(str, Enum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"


class ProjectionAction(str, Enum):
    UPSERT = "UPSERT"
    RETIRE = "RETIRE"


class PreferenceDecision(str, Enum):
    PREFER = "PREFER"
    AVOID = "AVOID"
    PROTECT = "PROTECT"
    DEPRIORITIZE = "DEPRIORITIZE"


class PreferenceProjectionCandidateState(str, Enum):
    SOURCE_NOT_BOUND = "SOURCE_NOT_BOUND"
    SOURCE_STALE = "SOURCE_STALE"
    SOURCE_INTEGRITY_FAILURE = "SOURCE_INTEGRITY_FAILURE"
    PROJECT_SCOPED_PROFILE_UNSUPPORTED_V1 = "PROJECT_SCOPED_PROFILE_UNSUPPORTED_V1"
    UNMAPPED_SOURCE_RULE = "UNMAPPED_SOURCE_RULE"
    INSUFFICIENT_CONFIRMATIONS = "INSUFFICIENT_CONFIRMATIONS"
    INSUFFICIENT_EFFECTIVE_STRENGTH = "INSUFFICIENT_EFFECTIVE_STRENGTH"
    NO_ACTIVE_PREFERENCES = "NO_ACTIVE_PREFERENCES"
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"


@dataclass(frozen=True, slots=True, order=True)
class ProjectionPolicyRow:
    feature_key: str
    change_direction: ChangeDirection
    projection_action: ProjectionAction
    decision: PreferenceDecision | None
    target: str | None
    contexts: tuple[str, ...]
    reason_codes: tuple[str, ...]
    minimum_confirmation_count: int
    maximum_absolute_ranking_bias_milli: int

    def __post_init__(self) -> None:
        _stable(self.feature_key, "feature_key")
        if type(self.change_direction) is not ChangeDirection:
            raise ValueError("change_direction is invalid")
        if type(self.projection_action) is not ProjectionAction:
            raise ValueError("projection_action is invalid")
        _integer(self.minimum_confirmation_count, "minimum_confirmation_count", 1, 32)
        _integer(self.maximum_absolute_ranking_bias_milli, "maximum_absolute_ranking_bias_milli", 0, 1000)
        for name, values, minimum in (("contexts", self.contexts, 0), ("reason_codes", self.reason_codes, 0)):
            if type(values) is not tuple or not minimum <= len(values) <= 16:
                raise ValueError(f"{name} must be a bounded tuple")
            if values != tuple(sorted(set(values))) or any(type(v) is not str or _TOKEN.fullmatch(v) is None for v in values):
                raise ValueError(f"{name} must contain sorted Product tokens")
        if self.projection_action is ProjectionAction.UPSERT:
            if type(self.decision) is not PreferenceDecision or type(self.target) is not str or _TOKEN.fullmatch(self.target) is None:
                raise ValueError("UPSERT requires a decision and Product target token")
            if not self.contexts or not self.reason_codes or self.maximum_absolute_ranking_bias_milli == 0:
                raise ValueError("UPSERT requires contexts, reasons, and a positive bias ceiling")
        elif any((self.decision is not None, self.target is not None, bool(self.contexts), bool(self.reason_codes), self.maximum_absolute_ranking_bias_milli != 0)):
            raise ValueError("RETIRE output fields must be null, empty, and zero")

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_key": self.feature_key,
            "change_direction": self.change_direction.value,
            "projection_action": self.projection_action.value,
            "decision": None if self.decision is None else self.decision.value,
            "target": self.target,
            "contexts": list(self.contexts),
            "reason_codes": list(self.reason_codes),
            "minimum_confirmation_count": self.minimum_confirmation_count,
            "maximum_absolute_ranking_bias_milli": self.maximum_absolute_ranking_bias_milli,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ProjectionPolicyRow":
        expected = {"feature_key", "change_direction", "projection_action", "decision", "target", "contexts", "reason_codes", "minimum_confirmation_count", "maximum_absolute_ranking_bias_milli"}
        if type(value) is not dict or set(value) != expected:
            raise ValueError("policy row fields are incomplete or unknown")
        if type(value["contexts"]) is not list or type(value["reason_codes"]) is not list:
            raise ValueError("policy row arrays are invalid")
        decision = None if value["decision"] is None else PreferenceDecision(value["decision"])
        return cls(value["feature_key"], ChangeDirection(value["change_direction"]), ProjectionAction(value["projection_action"]), decision, value["target"], tuple(value["contexts"]), tuple(value["reason_codes"]), value["minimum_confirmation_count"], value["maximum_absolute_ranking_bias_milli"])


@dataclass(frozen=True, slots=True)
class PreferenceProjectionPolicy:
    policy_id: str
    policy_version: str
    rows: tuple[ProjectionPolicyRow, ...]

    def __post_init__(self) -> None:
        _stable(self.policy_id, "policy_id")
        if type(self.policy_version) is not str or _SEMVER.fullmatch(self.policy_version) is None:
            raise ValueError("policy_version must be semantic version x.y.z")
        if type(self.rows) is not tuple or not 1 <= len(self.rows) <= 256 or any(type(row) is not ProjectionPolicyRow for row in self.rows):
            raise ValueError("rows must contain 1..256 exact ProjectionPolicyRow values")
        if self.rows != tuple(sorted(self.rows, key=lambda row: (row.feature_key, row.change_direction.value))):
            raise ValueError("rows must be canonically sorted")
        keys = [(row.feature_key, row.change_direction) for row in self.rows]
        if len(keys) != len(set(keys)):
            raise ValueError("policy rows must be unique by feature and direction")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": POLICY_SCHEMA_VERSION,
            "record_type": "BVP_MONTAGE_PREFERENCE_PROJECTION_POLICY",
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "scope_mode": "OWNER_GLOBAL",
            "rows": [row.to_dict() for row in self.rows],
            "automatic_learning_authorized": False,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }
        body["policy_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: object) -> "PreferenceProjectionPolicy":
        expected = {"schema_version", "record_type", "policy_id", "policy_version", "scope_mode", "rows", "automatic_learning_authorized", "automatic_promotion_authorized", "timeline_mutation_authorized", "resolve_write_authorized", "policy_sha256"}
        if type(value) is not dict or set(value) != expected or type(value.get("rows")) is not list:
            raise ValueError("projection policy fields are incomplete or unknown")
        if value["schema_version"] != POLICY_SCHEMA_VERSION or value["record_type"] != "BVP_MONTAGE_PREFERENCE_PROJECTION_POLICY" or value["scope_mode"] != "OWNER_GLOBAL":
            raise ValueError("projection policy identity is unsupported")
        for field in ("automatic_learning_authorized", "automatic_promotion_authorized", "timeline_mutation_authorized", "resolve_write_authorized"):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(value["policy_id"], value["policy_version"], tuple(ProjectionPolicyRow.from_dict(row) for row in value["rows"]))
        if result.to_dict() != value:
            raise ValueError("projection policy hash or derived fields mismatch")
        return result


@dataclass(frozen=True, slots=True)
class PreferenceProjectionSources:
    registry_history: OwnerProfileRegistryHistory
    owner_profile_histories: tuple[OwnerProfileHistory, ...]
    proposals: tuple[ProfileTuningProposal, ...]
    bindings: tuple[ProfileTuningOwnerDecisionBinding, ...]
    decision_histories: tuple[OwnerDecisionHistory, ...]

    def __post_init__(self) -> None:
        if type(self.registry_history) is not OwnerProfileRegistryHistory:
            raise ValueError("registry_history must be exact OwnerProfileRegistryHistory")
        checks = ((self.owner_profile_histories, OwnerProfileHistory), (self.proposals, ProfileTuningProposal), (self.bindings, ProfileTuningOwnerDecisionBinding), (self.decision_histories, OwnerDecisionHistory))
        for values, expected in checks:
            if type(values) is not tuple or any(type(value) is not expected for value in values):
                raise ValueError(f"source collection must contain exact {expected.__name__} values")
        _exact_tree(self)


@dataclass(frozen=True, slots=True, order=True)
class ProjectedPreference:
    preference_id: str
    decision: PreferenceDecision
    target: str
    contexts: tuple[str, ...]
    confidence_milli: int
    confirmation_count: int
    reason_codes: tuple[str, ...]
    ranking_bias_milli: int
    source_decision_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.preference_id) is not str or re.fullmatch(r"pref-[0-9a-f]{64}", self.preference_id) is None:
            raise ValueError("preference_id is invalid")
        if type(self.decision) is not PreferenceDecision or type(self.target) is not str or _TOKEN.fullmatch(self.target) is None:
            raise ValueError("preference decision or target is invalid")
        for name, values in (("contexts", self.contexts), ("reason_codes", self.reason_codes)):
            if type(values) is not tuple or not values or len(values) > 16 or values != tuple(sorted(set(values))) or any(type(value) is not str or _TOKEN.fullmatch(value) is None for value in values):
                raise ValueError(f"{name} must contain canonical Product tokens")
        _integer(self.confidence_milli, "confidence_milli", 0, 1000)
        _integer(self.confirmation_count, "confirmation_count", 1, 32)
        if type(self.ranking_bias_milli) is not int or self.ranking_bias_milli == 0 or abs(self.ranking_bias_milli) > 1000:
            raise ValueError("ranking_bias_milli must be a non-zero integer in -1000..1000")
        expected_positive = self.decision in (PreferenceDecision.PREFER, PreferenceDecision.PROTECT)
        if (self.ranking_bias_milli > 0) is not expected_positive:
            raise ValueError("ranking bias sign does not match decision")
        if type(self.source_decision_ids) is not tuple or not 1 <= len(self.source_decision_ids) <= 32 or self.source_decision_ids != tuple(sorted(set(self.source_decision_ids))):
            raise ValueError("source_decision_ids must contain 1..32 canonical IDs")
        for value in self.source_decision_ids:
            _stable(value, "source_decision_id")

    def public_dict(self) -> dict[str, Any]:
        return {
            "preference_id": self.preference_id,
            "decision": self.decision.value,
            "target": self.target,
            "contexts": list(self.contexts),
            "confidence": self.confidence_milli / 1000,
            "confirmation_count": self.confirmation_count,
            "reason_codes": list(self.reason_codes),
            "ranking_bias": self.ranking_bias_milli / 1000,
        }

    def private_dict(self) -> dict[str, Any]:
        return {**self.public_dict(), "confidence_milli": self.confidence_milli, "ranking_bias_milli": self.ranking_bias_milli, "source_decision_ids": list(self.source_decision_ids)}


@dataclass(frozen=True, slots=True)
class PreferenceProjectionCandidate:
    state: PreferenceProjectionCandidateState
    reason_codes: tuple[str, ...]
    owner_scope_sha256: str
    registry_id: str
    registry_revision: int
    registry_history_sha256: str
    current_profile_sha256: str | None
    current_profile_version: str | None
    policy_id: str
    policy_version: str
    policy_sha256: str
    previous_active_promotion_revision: int
    previous_active_promotion_sha256: str | None
    next_profile_version: int
    source_proposal_sha256s: tuple[str, ...]
    source_binding_sha256s: tuple[str, ...]
    source_decision_history_sha256s: tuple[str, ...]
    preferences: tuple[ProjectedPreference, ...] | None

    def __post_init__(self) -> None:
        if type(self.state) is not PreferenceProjectionCandidateState:
            raise ValueError("state is invalid")
        if type(self.reason_codes) is not tuple or self.reason_codes != tuple(sorted(set(self.reason_codes))) or any(type(value) is not str or _TOKEN.fullmatch(value) is None for value in self.reason_codes):
            raise ValueError("reason_codes must be canonical")
        _sha(self.owner_scope_sha256, "owner_scope_sha256")
        _stable(self.registry_id, "registry_id")
        _integer(self.registry_revision, "registry_revision", 0, 1_000_000_000)
        _sha(self.registry_history_sha256, "registry_history_sha256")
        if self.current_profile_sha256 is not None:
            _sha(self.current_profile_sha256, "current_profile_sha256")
        if self.current_profile_version is not None and (type(self.current_profile_version) is not str or _SEMVER.fullmatch(self.current_profile_version) is None):
            raise ValueError("current_profile_version is invalid")
        if (self.current_profile_sha256 is None) != (self.current_profile_version is None):
            raise ValueError("current profile coordinates must be present together")
        _stable(self.policy_id, "policy_id")
        if type(self.policy_version) is not str or _SEMVER.fullmatch(self.policy_version) is None:
            raise ValueError("policy_version is invalid")
        _sha(self.policy_sha256, "policy_sha256")
        _integer(self.previous_active_promotion_revision, "previous_active_promotion_revision", 0, 1_000_000_000)
        _integer(self.next_profile_version, "next_profile_version", 1, 1_000_000_000)
        if self.next_profile_version != self.previous_active_promotion_revision + 1:
            raise ValueError("next profile version must advance by one")
        if self.previous_active_promotion_revision == 0:
            if self.previous_active_promotion_sha256 is not None:
                raise ValueError("first candidate cannot bind a previous promotion")
        else:
            _sha(self.previous_active_promotion_sha256, "previous_active_promotion_sha256")
        for name, values in (("source_proposal_sha256s", self.source_proposal_sha256s), ("source_binding_sha256s", self.source_binding_sha256s), ("source_decision_history_sha256s", self.source_decision_history_sha256s)):
            if type(values) is not tuple or values != tuple(sorted(set(values))):
                raise ValueError(f"{name} must be canonical")
            for value in values:
                _sha(value, name)
        if self.state is PreferenceProjectionCandidateState.READY_FOR_HUMAN_REVIEW:
            if type(self.preferences) is not tuple or not self.preferences or any(type(value) is not ProjectedPreference for value in self.preferences):
                raise ValueError("ready candidate requires preferences")
            if self.preferences != tuple(sorted(self.preferences, key=lambda value: value.preference_id)):
                raise ValueError("preferences must be canonically sorted")
        elif self.preferences is not None:
            raise ValueError("non-ready candidate must remain body-free")

    def _envelope(self) -> dict[str, Any] | None:
        if self.preferences is None:
            return None
        public = [row.public_dict() for row in self.preferences]
        payload = {"projection_version": PROJECTION_VERSION, "preferences": public}
        profile_digest = sha256_bytes(canonical_json_bytes(payload))
        profile_id = _profile_id(self.owner_scope_sha256)
        decision_ids = {value for row in self.preferences for value in row.source_decision_ids}
        return {
            "schema_version": "1.0.0",
            "message_type": "BvpMontagePreferenceProfileDelivery",
            "contract_profile": CONTRACT_PROFILE,
            "profile_contract": PROFILE_CONTRACT,
            "profile_id": profile_id,
            "profile_version": self.next_profile_version,
            "owner_scope_hash": self.owner_scope_sha256,
            "source_record_count": len(decision_ids),
            "profile_sha256": profile_digest,
            "advisory_only": True,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
            "payload": payload,
        }

    def to_dict(self) -> dict[str, Any]:
        envelope = self._envelope()
        active_hash = None if self.preferences is None else sha256_bytes(canonical_json_bytes([row.private_dict() for row in self.preferences]))
        body: dict[str, Any] = {
            "schema_version": "1.0.0",
            "record_type": "BVP_MONTAGE_PREFERENCE_PROJECTION_CANDIDATE",
            "task_owner": "TASK-060",
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
            "owner_scope_sha256": self.owner_scope_sha256,
            "registry_id": self.registry_id,
            "registry_revision": self.registry_revision,
            "registry_history_sha256": self.registry_history_sha256,
            "current_profile_sha256": self.current_profile_sha256,
            "current_profile_version": self.current_profile_version,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_sha256": self.policy_sha256,
            "previous_active_promotion_revision": self.previous_active_promotion_revision,
            "previous_active_promotion_sha256": self.previous_active_promotion_sha256,
            "next_profile_version": self.next_profile_version,
            "source_proposal_sha256s": list(self.source_proposal_sha256s),
            "source_binding_sha256s": list(self.source_binding_sha256s),
            "source_decision_history_sha256s": list(self.source_decision_history_sha256s),
            "active_preference_map_sha256": active_hash,
            "proposed_envelope": envelope,
            "human_review_required": True,
            "automatic_learning_authorized": False,
            "automatic_promotion_authorized": False,
            "canonical_timeline": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }
        body["candidate_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def _profile_id(owner_scope_sha256: str) -> str:
    digest = sha256_bytes(canonical_json_bytes({"domain": "BVP_MONTAGE_PREFERENCE_PROFILE_ID_V1", "owner_scope_hash": owner_scope_sha256, "scope_mode": "OWNER_GLOBAL"}))
    return "profile-" + digest.removeprefix("sha256:")


def _preference_id(profile_id: str, feature_key: str, policy: PreferenceProjectionPolicy) -> str:
    digest = sha256_bytes(canonical_json_bytes({"domain": "BVP_MONTAGE_PREFERENCE_ID_V1", "profile_id": profile_id, "feature_key": feature_key, "policy_id": policy.policy_id, "policy_major": int(policy.policy_version.split(".")[0])}))
    return "pref-" + digest.removeprefix("sha256:")


def _candidate(state: PreferenceProjectionCandidateState, reasons: tuple[str, ...], *, sources: PreferenceProjectionSources, policy: PreferenceProjectionPolicy, previous_revision: int, previous_sha: str | None, next_version: int, current_profile: dict[str, Any] | None = None, proposal_hashes: tuple[str, ...] = (), binding_hashes: tuple[str, ...] = (), decision_hashes: tuple[str, ...] = (), preferences: tuple[ProjectedPreference, ...] | None = None) -> PreferenceProjectionCandidate:
    registry_payload = sources.registry_history.to_dict()
    return PreferenceProjectionCandidate(state, tuple(sorted(set(reasons))), sources.registry_history.owner_scope_sha256, sources.registry_history.registry_id, sources.registry_history.revision, registry_payload["history_sha256"], None if current_profile is None else current_profile["profile_sha256"], None if current_profile is None else current_profile["profile_version"], policy.policy_id, policy.policy_version, policy.to_dict()["policy_sha256"], previous_revision, previous_sha, next_version, proposal_hashes, binding_hashes, decision_hashes, preferences)


def compile_preference_projection_candidate(
    sources: PreferenceProjectionSources,
    policy: PreferenceProjectionPolicy,
    *,
    expected_owner_scope_sha256: str,
    expected_registry_revision: int,
    requested_scope_mode: str,
    previous_active_promotion_revision: int,
    previous_active_promotion_sha256: str | None,
    next_profile_version: int,
) -> PreferenceProjectionCandidate:
    """Compile one deterministic, no-effect PP-A candidate."""

    if type(sources) is not PreferenceProjectionSources or type(policy) is not PreferenceProjectionPolicy:
        raise ValueError("sources and policy must be exact typed records")
    _sha(expected_owner_scope_sha256, "expected_owner_scope_sha256")
    _integer(expected_registry_revision, "expected_registry_revision", 0, 1_000_000_000)
    _integer(previous_active_promotion_revision, "previous_active_promotion_revision", 0, 1_000_000_000)
    _integer(next_profile_version, "next_profile_version", 1, 1_000_000_000)
    if next_profile_version != previous_active_promotion_revision + 1:
        raise ValueError("next_profile_version must follow the previous promotion revision")
    if previous_active_promotion_revision == 0:
        if previous_active_promotion_sha256 is not None:
            raise ValueError("first projection cannot bind a previous promotion hash")
    else:
        _sha(previous_active_promotion_sha256, "previous_active_promotion_sha256")
    verified_policy = PreferenceProjectionPolicy.from_dict(policy.to_dict())
    if requested_scope_mode != "OWNER_GLOBAL":
        return _candidate(PreferenceProjectionCandidateState.PROJECT_SCOPED_PROFILE_UNSUPPORTED_V1, ("PROJECT_SCOPE_UNSUPPORTED",), sources=sources, policy=verified_policy, previous_revision=previous_active_promotion_revision, previous_sha=previous_active_promotion_sha256, next_version=next_profile_version)
    if sources.registry_history.owner_scope_sha256 != expected_owner_scope_sha256:
        return _candidate(PreferenceProjectionCandidateState.SOURCE_INTEGRITY_FAILURE, ("OWNER_SCOPE_MISMATCH",), sources=sources, policy=verified_policy, previous_revision=previous_active_promotion_revision, previous_sha=previous_active_promotion_sha256, next_version=next_profile_version)
    if sources.registry_history.revision == 0 or not all((sources.owner_profile_histories, sources.proposals, sources.bindings, sources.decision_histories)):
        return _candidate(PreferenceProjectionCandidateState.SOURCE_NOT_BOUND, ("REQUIRED_SOURCE_NOT_BOUND",), sources=sources, policy=verified_policy, previous_revision=previous_active_promotion_revision, previous_sha=previous_active_promotion_sha256, next_version=next_profile_version)
    if sources.registry_history.revision != expected_registry_revision:
        return _candidate(PreferenceProjectionCandidateState.SOURCE_STALE, ("REGISTRY_REVISION_STALE",), sources=sources, policy=verified_policy, previous_revision=previous_active_promotion_revision, previous_sha=previous_active_promotion_sha256, next_version=next_profile_version)

    try:
        _exact_tree(sources)
        registry = OwnerProfileRegistryHistory.from_dict(sources.registry_history.to_dict())
        profile_histories = {value.to_dict()["history_sha256"]: OwnerProfileHistory.from_dict(value.to_dict()) for value in sources.owner_profile_histories}
        proposals = {value.to_dict()["proposal_sha256"]: value for value in sources.proposals}
        bindings = {value.to_dict()["binding_sha256"]: value for value in sources.bindings}
        decision_histories = {value.to_dict()["history_sha256"]: OwnerDecisionHistory.from_dict(value.to_dict()) for value in sources.decision_histories}
        if any(len(mapping) != len(values) for mapping, values in ((profile_histories, sources.owner_profile_histories), (proposals, sources.proposals), (bindings, sources.bindings), (decision_histories, sources.decision_histories))):
            raise ValueError("duplicate source snapshots are forbidden")

        latest_changes: dict[str, tuple[Any, ProfileTuningProposal, ProfileTuningOwnerDecisionBinding, OwnerDecisionHistory, int]] = {}
        used_proposals: list[str] = []
        used_bindings: list[str] = []
        used_decisions: list[str] = []
        for registry_revision in registry.revisions:
            candidate = registry_revision.candidate
            profile_history = profile_histories[candidate.source_history_sha256]
            proposal = proposals[candidate.source_proposal_sha256]
            binding = bindings[candidate.source_binding_sha256]
            decision_history = decision_histories[candidate.source_decision_history_sha256]
            verify_profile_tuning_proposal_hash(proposal.to_dict())
            if profile_history.store_id != registry.source_store_id or profile_history.owner_scope_sha256 != expected_owner_scope_sha256 or profile_history.revision != candidate.source_history_revision:
                raise ValueError("Owner Profile source coordinate mismatch")
            source_revision = profile_history.revisions[-1]
            if source_revision.to_dict()["revision_sha256"] != candidate.source_profile_revision_sha256 or source_revision.candidate["materialization_sha256"] != candidate.source_materialization_sha256 or source_revision.confirmation.to_dict()["confirmation_sha256"] != candidate.source_confirmation_sha256:
                raise ValueError("Owner Profile source lineage mismatch")
            proposal_payload = proposal.to_dict()
            binding_payload = binding.to_dict()
            if proposal.state is not TuningProposalState.READY_FOR_HUMAN_REVIEW or binding.state is not OwnerDecisionBindingState.READY_FOR_HUMAN_REVIEW:
                raise ValueError("proposal and binding must be ready")
            if binding.proposal_sha256 != candidate.source_proposal_sha256 or binding.decision_history_sha256 != candidate.source_decision_history_sha256 or binding.owner_scope_sha256 != expected_owner_scope_sha256 or decision_history.owner_scope_sha256 != expected_owner_scope_sha256:
                raise ValueError("proposal, binding, decision history, or Owner scope mismatch")
            if (
                proposal_payload["baseline_profile"]["profile_sha256"] != candidate.baseline_profile_sha256
                or proposal_payload["proposed_profile"] != candidate.profile_snapshot.to_dict()
                or binding.baseline_profile_sha256 != proposal_payload["baseline_profile"]["profile_sha256"]
                or binding.proposed_profile_sha256 != candidate.profile_snapshot.to_dict()["profile_sha256"]
                or binding.rollback_profile_sha256 != proposal_payload["rollback_profile_sha256"]
            ):
                raise ValueError("registered profile does not match exact proposal")
            if {row.feature_key for row in binding.supports} != {row.feature_key for row in proposal.adjustments}:
                raise ValueError("binding support does not exactly cover proposal adjustments")
            support_ids = tuple(sorted(reference.decision_id for support in binding.supports for reference in support.decisions))
            if support_ids != candidate.source_decision_ids:
                raise ValueError("registered decision IDs do not match binding")
            entries = {entry.decision_id: entry for entry in decision_history.entries}
            for support in binding.supports:
                for reference in support.decisions:
                    entry = entries.get(reference.decision_id)
                    if entry is None or entry.decision is not HumanDecision.ADOPTED or entry.to_dict()["entry_sha256"] != reference.entry_sha256 or entry.candidate["state"] != OwnerDecisionState.READY_FOR_HUMAN_REVIEW.value:
                        raise ValueError("bound Owner decision is not current and adopted")
            baseline_weights = {row.feature_key: row.weight_milli for row in proposal.baseline_profile.rules}
            support_by_feature = {row.feature_key: row for row in binding.supports}
            for adjustment in proposal.adjustments:
                baseline_weight = baseline_weights[adjustment.feature_key]
                delta = adjustment.proposed_weight_milli - baseline_weight
                if delta == 0 or adjustment.feature_key not in support_by_feature:
                    raise ValueError("changed feature lineage is incomplete")
                latest_changes[adjustment.feature_key] = (registry_revision, proposal, binding, decision_history, delta)
            used_proposals.append(candidate.source_proposal_sha256)
            used_bindings.append(candidate.source_binding_sha256)
            used_decisions.append(candidate.source_decision_history_sha256)

        current_profile = registry.revisions[-1].candidate.profile_snapshot.to_dict()
        current_keys = {row["feature_key"] for row in current_profile["rules"]}
        policy_rows = {(row.feature_key, row.change_direction): row for row in verified_policy.rows}
        projected: list[ProjectedPreference] = []
        represented_ids: set[str] = set()
        insufficient_confirmation = False
        insufficient_strength = False
        unmapped = False
        profile_id = _profile_id(expected_owner_scope_sha256)
        for feature_key in sorted(current_keys & set(latest_changes)):
            _, proposal, binding, _, delta = latest_changes[feature_key]
            direction = ChangeDirection.INCREASE if delta > 0 else ChangeDirection.DECREASE
            row = policy_rows.get((feature_key, direction))
            if row is None:
                unmapped = True
                continue
            support = next(value for value in binding.supports if value.feature_key == feature_key)
            decision_ids = tuple(reference.decision_id for reference in support.decisions)
            if represented_ids.intersection(decision_ids):
                raise ValueError("Owner decision replay across preferences")
            represented_ids.update(decision_ids)
            if len(decision_ids) < row.minimum_confirmation_count:
                insufficient_confirmation = True
                continue
            if row.projection_action is ProjectionAction.RETIRE:
                continue
            tuning = proposal.policy
            if proposal.weighted_improvement_milli is None:
                raise ValueError("ready proposal requires weighted improvement")
            sample_strength = min(1000, (proposal.total_holdout_samples * 500 + tuning.minimum_holdout_samples // 2) // tuning.minimum_holdout_samples)
            improvement_strength = min(1000, (proposal.weighted_improvement_milli * 500 + tuning.minimum_improvement_milli // 2) // tuning.minimum_improvement_milli)
            confidence = min(sample_strength, improvement_strength)
            delta_strength = min(1000, (abs(delta) * 1000 + tuning.max_abs_weight_delta_milli // 2) // tuning.max_abs_weight_delta_milli)
            effective = min(confidence, delta_strength)
            absolute_bias = (row.maximum_absolute_ranking_bias_milli * effective + 500) // 1000
            if absolute_bias == 0:
                insufficient_strength = True
                continue
            sign = 1 if row.decision in (PreferenceDecision.PREFER, PreferenceDecision.PROTECT) else -1
            projected.append(ProjectedPreference(_preference_id(profile_id, feature_key, verified_policy), row.decision, row.target, row.contexts, confidence, len(decision_ids), row.reason_codes, sign * absolute_bias, decision_ids))

        hashes = (tuple(sorted(set(used_proposals))), tuple(sorted(set(used_bindings))), tuple(sorted(set(used_decisions))))
        common = dict(sources=sources, policy=verified_policy, previous_revision=previous_active_promotion_revision, previous_sha=previous_active_promotion_sha256, next_version=next_profile_version, current_profile=current_profile, proposal_hashes=hashes[0], binding_hashes=hashes[1], decision_hashes=hashes[2])
        if unmapped:
            return _candidate(PreferenceProjectionCandidateState.UNMAPPED_SOURCE_RULE, ("POLICY_ROW_NOT_FOUND",), **common)
        if insufficient_confirmation:
            return _candidate(PreferenceProjectionCandidateState.INSUFFICIENT_CONFIRMATIONS, ("MINIMUM_CONFIRMATIONS_NOT_MET",), **common)
        if insufficient_strength:
            return _candidate(PreferenceProjectionCandidateState.INSUFFICIENT_EFFECTIVE_STRENGTH, ("ZERO_EFFECTIVE_BIAS",), **common)
        if not projected:
            return _candidate(PreferenceProjectionCandidateState.NO_ACTIVE_PREFERENCES, ("NO_ACTIVE_PREFERENCES",), **common)
        preferences = tuple(sorted(projected, key=lambda value: value.preference_id))
        return _candidate(PreferenceProjectionCandidateState.READY_FOR_HUMAN_REVIEW, (), preferences=preferences, **common)
    except (KeyError, TypeError, ValueError):
        return _candidate(PreferenceProjectionCandidateState.SOURCE_INTEGRITY_FAILURE, ("SOURCE_REVALIDATION_FAILED",), sources=sources, policy=verified_policy, previous_revision=previous_active_promotion_revision, previous_sha=previous_active_promotion_sha256, next_version=next_profile_version)


def verify_preference_projection_candidate(candidate: PreferenceProjectionCandidate, sources: PreferenceProjectionSources, policy: PreferenceProjectionPolicy, **coordinates: Any) -> None:
    if type(candidate) is not PreferenceProjectionCandidate:
        raise ValueError("candidate must be exact PreferenceProjectionCandidate")
    expected = compile_preference_projection_candidate(sources, policy, **coordinates)
    if candidate.to_dict() != expected.to_dict():
        raise ValueError("candidate does not match exact source snapshots")


__all__ = [
    "ChangeDirection", "PreferenceDecision", "PreferenceProjectionCandidate",
    "PreferenceProjectionCandidateState", "PreferenceProjectionPolicy",
    "PreferenceProjectionSources", "ProjectedPreference", "ProjectionAction",
    "ProjectionPolicyRow", "compile_preference_projection_candidate",
    "verify_preference_projection_candidate",
]
