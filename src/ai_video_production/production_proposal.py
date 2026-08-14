"""TASK-027 Slice A2 proposal revision and explicit Human GO foundation.

This module is deliberately provider-neutral.  It versions user intent and
production proposals, then creates an immutable Approved Production Plan only
through a one-shot Human GO confirmation.  It never executes a provider,
mutates Resolve, publishes output, or authorizes paid execution by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
import secrets
from typing import Any, Callable, Iterable

from .errors import ProductError, ProductErrorCategory
from .production_blueprint import (
    BlueprintReference,
    ProductionBlueprint,
    ReferenceStatus,
)
from .production_blueprint_v2 import ProductionBlueprintV2
from .serialization import canonical_json_bytes, sha256_bytes


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Z][A-Z0-9._-]{2,63}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_ASPECT_RE = re.compile(r"^[1-9][0-9]{0,3}:[1-9][0-9]{0,3}$")
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")

TokenFactory = Callable[[], str]
BlueprintContract = ProductionBlueprint | ProductionBlueprintV2


def _decimal(value: Decimal | str | int | float, *, field: str, minimum: Decimal = Decimal("0")) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite() or result < minimum:
        raise ValueError(f"{field} is outside the allowed range")
    return result


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    # Avoid scientific notation in canonical user-facing financial records.
    return format(normalized, "f")


def _require_sha(value: str, *, field: str) -> None:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be a canonical sha256 identity")


def _nonempty_text(value: str, *, field: str, limit: int) -> str:
    text = value.strip()
    if not text or len(text) > limit or "\x00" in text:
        raise ValueError(f"{field} is invalid")
    return text


@dataclass(frozen=True, slots=True)
class CreationIntent:
    intent_id: str
    revision: int
    purpose: str
    audience: str
    platform: str
    aspect_ratio: str
    target_duration_seconds: Decimal
    style_tone: str
    story_message: str
    language: str
    free_text: str = ""
    budget_ceiling: Decimal | None = None
    currency: str = "USD"
    rights_constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.intent_id):
            raise ValueError("intent_id is invalid")
        if self.revision < 1:
            raise ValueError("intent revision must be >= 1")
        for field, value, limit in (
            ("purpose", self.purpose, 512),
            ("audience", self.audience, 512),
            ("platform", self.platform, 128),
            ("style_tone", self.style_tone, 512),
            ("story_message", self.story_message, 4000),
        ):
            _nonempty_text(value, field=field, limit=limit)
        if not _ASPECT_RE.fullmatch(self.aspect_ratio):
            raise ValueError("aspect_ratio must use width:height form")
        duration = _decimal(self.target_duration_seconds, field="target_duration_seconds", minimum=Decimal("0.001"))
        object.__setattr__(self, "target_duration_seconds", duration)
        if not _LANGUAGE_RE.fullmatch(self.language):
            raise ValueError("language is invalid")
        if self.free_text and (len(self.free_text) > 16000 or "\x00" in self.free_text):
            raise ValueError("free_text is invalid")
        if not _CURRENCY_RE.fullmatch(self.currency):
            raise ValueError("currency must be a three-letter uppercase code")
        if self.budget_ceiling is not None:
            object.__setattr__(self, "budget_ceiling", _decimal(self.budget_ceiling, field="budget_ceiling"))
        if len(set(self.rights_constraints)) != len(self.rights_constraints):
            raise ValueError("rights_constraints must be unique")
        for item in self.rights_constraints:
            _nonempty_text(item, field="rights_constraint", limit=1000)

    @property
    def key(self) -> str:
        return f"{self.intent_id}@{self.revision}"

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "intent_version": "1.0.0",
            "task_owner": "TASK-027",
            "intent_id": self.intent_id,
            "revision": self.revision,
            "purpose": self.purpose,
            "audience": self.audience,
            "platform": self.platform,
            "aspect_ratio": self.aspect_ratio,
            "target_duration_seconds": _decimal_text(self.target_duration_seconds),
            "style_tone": self.style_tone,
            "story_message": self.story_message,
            "language": self.language,
            "free_text": self.free_text,
            "budget_ceiling": None if self.budget_ceiling is None else _decimal_text(self.budget_ceiling),
            "currency": self.currency,
            "rights_constraints": list(self.rights_constraints),
            "credential_values_embedded": False,
            "provider_execution_started": False,
        }
        body["intent_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class ProposalSection:
    section_id: str
    kind: str
    title: str
    body: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{1,63}", self.section_id):
            raise ValueError("proposal section_id is invalid")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", self.kind):
            raise ValueError("proposal section kind is invalid")
        _nonempty_text(self.title, field="proposal section title", limit=256)
        _nonempty_text(self.body, field="proposal section body", limit=64000)

    def to_dict(self) -> dict[str, str]:
        return {
            "section_id": self.section_id,
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
        }


@dataclass(frozen=True, slots=True)
class ProviderPolicyBinding:
    policy_id: str
    policy_version: str
    policy_sha256: str

    def __post_init__(self) -> None:
        _nonempty_text(self.policy_id, field="policy_id", limit=128)
        _nonempty_text(self.policy_version, field="policy_version", limit=64)
        _require_sha(self.policy_sha256, field="policy_sha256")

    def to_dict(self) -> dict[str, str]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_sha256": self.policy_sha256,
        }


@dataclass(frozen=True, slots=True)
class ReferenceAssetBinding:
    reference_id: str
    asset_id: str
    asset_sha256: str

    def __post_init__(self) -> None:
        _nonempty_text(self.reference_id, field="reference_id", limit=128)
        _nonempty_text(self.asset_id, field="asset_id", limit=256)
        _require_sha(self.asset_sha256, field="asset_sha256")

    def to_dict(self) -> dict[str, str]:
        return {
            "reference_id": self.reference_id,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
        }


@dataclass(frozen=True, slots=True)
class ProductionProposalRevision:
    proposal_id: str
    revision: int
    intent_sha256: str
    blueprint: BlueprintContract
    sections: tuple[ProposalSection, ...]
    provider_policy: ProviderPolicyBinding
    estimated_cost_min: Decimal = Decimal("0")
    estimated_cost_max: Decimal = Decimal("0")
    currency: str = "USD"
    rights_warnings: tuple[str, ...] = ()
    parent_proposal_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.blueprint, (ProductionBlueprint, ProductionBlueprintV2)):
            raise ValueError("blueprint must be an exact ProductionBlueprint v1 or v2")
        if not _ID_RE.fullmatch(self.proposal_id):
            raise ValueError("proposal_id is invalid")
        if self.revision < 1:
            raise ValueError("proposal revision must be >= 1")
        _require_sha(self.intent_sha256, field="intent_sha256")
        if self.revision == 1 and self.parent_proposal_sha256 is not None:
            raise ValueError("proposal revision 1 cannot have a parent hash")
        if self.revision > 1:
            if self.parent_proposal_sha256 is None:
                raise ValueError("proposal revisions after 1 require parent_proposal_sha256")
            _require_sha(self.parent_proposal_sha256, field="parent_proposal_sha256")
        section_ids = [item.section_id for item in self.sections]
        if not self.sections or len(section_ids) != len(set(section_ids)):
            raise ValueError("proposal sections must be non-empty and unique")
        minimum = _decimal(self.estimated_cost_min, field="estimated_cost_min")
        maximum = _decimal(self.estimated_cost_max, field="estimated_cost_max")
        if maximum < minimum:
            raise ValueError("estimated_cost_max must be >= estimated_cost_min")
        object.__setattr__(self, "estimated_cost_min", minimum)
        object.__setattr__(self, "estimated_cost_max", maximum)
        if not _CURRENCY_RE.fullmatch(self.currency):
            raise ValueError("currency must be a three-letter uppercase code")
        if len(set(self.rights_warnings)) != len(self.rights_warnings):
            raise ValueError("rights_warnings must be unique")
        for item in self.rights_warnings:
            _nonempty_text(item, field="rights_warning", limit=1000)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "proposal_version": "1.0.0",
            "task_owner": "TASK-027",
            "proposal_id": self.proposal_id,
            "revision": self.revision,
            "parent_proposal_sha256": self.parent_proposal_sha256,
            "intent_sha256": self.intent_sha256,
            "blueprint": self.blueprint.to_dict(),
            "sections": [item.to_dict() for item in self.sections],
            "provider_policy": self.provider_policy.to_dict(),
            "estimated_cost_range": {
                "min": _decimal_text(self.estimated_cost_min),
                "max": _decimal_text(self.estimated_cost_max),
                "currency": self.currency,
            },
            "rights_warnings": list(self.rights_warnings),
            "human_editable": True,
            "go_approved": False,
            "provider_execution_started": False,
        }
        body["proposal_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class ApprovedProductionPlan:
    plan_id: str
    proposal_id: str
    proposal_revision: int
    proposal_sha256: str
    intent_sha256: str
    blueprint_id: str
    blueprint_sha256: str
    provider_policy: ProviderPolicyBinding
    reference_bindings: tuple[ReferenceAssetBinding, ...]
    cost_ceiling: Decimal
    currency: str
    approved_by: str
    rights_warnings_acknowledged: bool

    def __post_init__(self) -> None:
        if not re.fullmatch(r"PLAN-[A-F0-9]{16}", self.plan_id):
            raise ValueError("plan_id is invalid")
        if self.proposal_revision < 1:
            raise ValueError("proposal_revision must be >= 1")
        for field, value in (
            ("proposal_sha256", self.proposal_sha256),
            ("intent_sha256", self.intent_sha256),
            ("blueprint_sha256", self.blueprint_sha256),
        ):
            _require_sha(value, field=field)
        reference_ids = [item.reference_id for item in self.reference_bindings]
        if len(reference_ids) != len(set(reference_ids)):
            raise ValueError("reference_bindings must contain unique reference IDs")
        object.__setattr__(self, "cost_ceiling", _decimal(self.cost_ceiling, field="cost_ceiling"))
        if not _CURRENCY_RE.fullmatch(self.currency):
            raise ValueError("currency is invalid")
        _nonempty_text(self.approved_by, field="approved_by", limit=256)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "approved_plan_version": "1.0.0",
            "task_owner": "TASK-027",
            "plan_id": self.plan_id,
            "proposal_id": self.proposal_id,
            "proposal_revision": self.proposal_revision,
            "proposal_sha256": self.proposal_sha256,
            "intent_sha256": self.intent_sha256,
            "blueprint_id": self.blueprint_id,
            "blueprint_sha256": self.blueprint_sha256,
            "provider_policy": self.provider_policy.to_dict(),
            "reference_bindings": [item.to_dict() for item in self.reference_bindings],
            "cost_ceiling": _decimal_text(self.cost_ceiling),
            "currency": self.currency,
            "approved_by": self.approved_by,
            "rights_warnings_acknowledged": self.rights_warnings_acknowledged,
            "human_go_approved": True,
            "provider_execution_started": False,
            "resolve_mutation_started": False,
            "publish_authorized": False,
        }
        body["approved_plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class ProductionProposalRegistry:
    def __init__(self) -> None:
        self.intents: dict[str, CreationIntent] = {}
        self.proposals: dict[str, list[ProductionProposalRevision]] = {}
        self.approved_plans: dict[str, ApprovedProductionPlan] = {}

    def add_intent(self, intent: CreationIntent) -> None:
        key = intent.key
        if key in self.intents:
            raise ProductError("ERR_CREATION_INTENT_CONFLICT", "Creation Intent revision already exists", ProductErrorCategory.STATE)
        prior = [item for item in self.intents.values() if item.intent_id == intent.intent_id]
        expected_revision = 1 if not prior else max(item.revision for item in prior) + 1
        if intent.revision != expected_revision:
            raise ProductError(
                "ERR_CREATION_INTENT_REVISION_GAP",
                "Creation Intent revisions must be appended sequentially",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"expected_revision": expected_revision},
            )
        self.intents[key] = intent

    def add_proposal(self, proposal: ProductionProposalRevision) -> None:
        if proposal.intent_sha256 not in {item.to_dict()["intent_sha256"] for item in self.intents.values()}:
            raise ProductError(
                "ERR_PRODUCTION_PROPOSAL_INTENT_UNKNOWN",
                "Production Proposal must bind a registered exact Creation Intent revision",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        revisions = self.proposals.setdefault(proposal.proposal_id, [])
        expected_revision = len(revisions) + 1
        if proposal.revision != expected_revision:
            raise ProductError(
                "ERR_PRODUCTION_PROPOSAL_REVISION_GAP",
                "Production Proposal revisions must be appended sequentially",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"expected_revision": expected_revision},
            )
        if revisions:
            expected_parent = revisions[-1].to_dict()["proposal_sha256"]
            if proposal.parent_proposal_sha256 != expected_parent:
                raise ProductError(
                    "ERR_PRODUCTION_PROPOSAL_PARENT_MISMATCH",
                    "Production Proposal revision must bind the exact previous revision hash",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        revisions.append(proposal)

    def latest_proposal(self, proposal_id: str) -> ProductionProposalRevision:
        revisions = self.proposals.get(proposal_id)
        if not revisions:
            raise ProductError("ERR_PRODUCTION_PROPOSAL_NOT_FOUND", "Production Proposal does not exist", ProductErrorCategory.STATE)
        return revisions[-1]

    def add_approved_plan(self, plan: ApprovedProductionPlan) -> None:
        if plan.plan_id in self.approved_plans:
            raise ProductError("ERR_APPROVED_PLAN_CONFLICT", "Approved Production Plan already exists", ProductErrorCategory.STATE)
        self.approved_plans[plan.plan_id] = plan

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "registry_version": "1.0.0",
            "task_owner": "TASK-027",
            "intents": [self.intents[key].to_dict() for key in sorted(self.intents)],
            "proposals": [
                revision.to_dict()
                for proposal_id in sorted(self.proposals)
                for revision in self.proposals[proposal_id]
            ],
            "approved_plans": [self.approved_plans[key].to_dict() for key in sorted(self.approved_plans)],
            "provider_execution_started": False,
        }
        body["registry_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(slots=True)
class _GoConfirmation:
    confirmation_id: str
    proposal_id: str
    proposal_revision: int
    proposal_sha256: str
    reference_bindings: tuple[ReferenceAssetBinding, ...]
    cost_ceiling: Decimal
    rights_warnings_acknowledged: bool
    consumed: bool = False


class ProductionGoApprovalService:
    """One-shot Human GO boundary for immutable Approved Production Plans."""

    def __init__(self, registry: ProductionProposalRegistry, *, token_factory: TokenFactory | None = None) -> None:
        self.registry = registry
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _GoConfirmation] = {}

    @staticmethod
    def _required_reference_bindings(blueprint: BlueprintContract) -> dict[str, tuple[str, str] | None]:
        if isinstance(blueprint, ProductionBlueprint):
            return {
                item.reference_id: None
                for item in blueprint.references
                if item.status in {ReferenceStatus.AVAILABLE, ReferenceStatus.LOCKED}
            }
        required: dict[str, tuple[str, str]] = {}
        for scene in blueprint.scenes:
            for frame_name, intent in (
                ("START", scene.start_frame_intent),
                ("END", scene.end_frame_intent),
            ):
                prefix = f"{scene.scene_id}:{frame_name}"
                for index, item in enumerate(intent.binding.character_locks):
                    required[f"{prefix}:CHARACTER:{index}"] = (item.asset_id, item.asset_sha256)
                if intent.binding.space_lock is not None:
                    item = intent.binding.space_lock
                    required[f"{prefix}:SPACE"] = (item.asset_id, item.asset_sha256)
                if intent.binding.composition_lock is not None:
                    item = intent.binding.composition_lock
                    required[f"{prefix}:COMPOSITION"] = (item.asset_id, item.asset_sha256)
        return required

    @classmethod
    def _validate_reference_bindings(
        cls,
        blueprint: BlueprintContract,
        bindings: tuple[ReferenceAssetBinding, ...],
    ) -> None:
        ids = [item.reference_id for item in bindings]
        if len(ids) != len(set(ids)):
            raise ProductError("ERR_PRODUCTION_GO_REFERENCE_DUPLICATE", "GO reference bindings contain duplicate reference IDs", ProductErrorCategory.DATA_INTEGRITY)
        expected_bindings = cls._required_reference_bindings(blueprint)
        expected = set(expected_bindings)
        actual = set(ids)
        if actual != expected:
            raise ProductError(
                "ERR_PRODUCTION_GO_REFERENCE_BINDING_MISMATCH",
                "GO must bind every existing canonical Blueprint reference and no undeclared reference",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"missing": sorted(expected - actual), "unexpected": sorted(actual - expected)},
            )
        if isinstance(blueprint, ProductionBlueprintV2):
            actual_bindings = {item.reference_id: (item.asset_id, item.asset_sha256) for item in bindings}
            mismatched = sorted(
                reference_id
                for reference_id, identity in expected_bindings.items()
                if actual_bindings[reference_id] != identity
            )
            if mismatched:
                raise ProductError(
                    "ERR_PRODUCTION_GO_FRAME_BINDING_IDENTITY_MISMATCH",
                    "GO frame bindings must match every exact Blueprint v2 Asset identity and checksum",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                    details={"mismatched": mismatched},
                )

    def prepare_go(
        self,
        *,
        proposal_id: str,
        proposal_revision: int,
        reference_bindings: Iterable[ReferenceAssetBinding],
        cost_ceiling: Decimal | str | int | float,
        rights_warnings_acknowledged: bool,
    ) -> dict[str, Any]:
        latest = self.registry.latest_proposal(proposal_id)
        if latest.revision != proposal_revision:
            raise ProductError(
                "ERR_PRODUCTION_GO_PROPOSAL_NOT_LATEST",
                "GO may only be prepared for the latest Production Proposal revision",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"latest_revision": latest.revision},
            )
        bindings = tuple(sorted(reference_bindings, key=lambda item: item.reference_id))
        self._validate_reference_bindings(latest.blueprint, bindings)
        ceiling = _decimal(cost_ceiling, field="cost_ceiling")
        if ceiling < latest.estimated_cost_max:
            raise ProductError(
                "ERR_PRODUCTION_GO_COST_CEILING_TOO_LOW",
                "GO cost ceiling is below the Proposal estimated maximum",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={
                    "estimated_cost_max": _decimal_text(latest.estimated_cost_max),
                    "currency": latest.currency,
                },
            )
        if latest.rights_warnings and not rights_warnings_acknowledged:
            raise ProductError(
                "ERR_PRODUCTION_GO_RIGHTS_ACKNOWLEDGEMENT_REQUIRED",
                "GO requires explicit Human acknowledgement of current rights warnings",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"warning_count": len(latest.rights_warnings)},
            )
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError("ERR_PRODUCTION_GO_CONFIRMATION_TOKEN_INVALID", "GO confirmation token is invalid", ProductErrorCategory.INTERNAL)
        proposal_sha = latest.to_dict()["proposal_sha256"]
        self._confirmations[token] = _GoConfirmation(
            token,
            latest.proposal_id,
            latest.revision,
            proposal_sha,
            bindings,
            ceiling,
            rights_warnings_acknowledged,
        )
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-027",
            "confirmation_id": token,
            "proposal_id": latest.proposal_id,
            "proposal_revision": latest.revision,
            "proposal_sha256": proposal_sha,
            "blueprint_id": latest.blueprint.blueprint_id,
            "blueprint_sha256": latest.blueprint.to_dict()["blueprint_sha256"],
            "reference_bindings": [item.to_dict() for item in bindings],
            "cost_ceiling": _decimal_text(ceiling),
            "currency": latest.currency,
            "rights_warning_count": len(latest.rights_warnings),
            "human_go_required": True,
            "provider_execution_started": False,
            "resolve_mutation_started": False,
        }

    def approve_go(self, *, confirmation_id: str, approved_by: str) -> ApprovedProductionPlan:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_PRODUCTION_GO_CONFIRMATION_INVALID", "GO confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        latest = self.registry.latest_proposal(pending.proposal_id)
        if (
            latest.revision != pending.proposal_revision
            or latest.to_dict()["proposal_sha256"] != pending.proposal_sha256
        ):
            raise ProductError(
                "ERR_PRODUCTION_GO_CONFIRMATION_STALE",
                "Production Proposal changed after GO confirmation was prepared",
                ProductErrorCategory.AUTHORIZATION,
            )
        approver = _nonempty_text(approved_by, field="approved_by", limit=256)
        pending.consumed = True
        seed = {
            "proposal_sha256": pending.proposal_sha256,
            "reference_bindings": [item.to_dict() for item in pending.reference_bindings],
            "cost_ceiling": _decimal_text(pending.cost_ceiling),
            "currency": latest.currency,
            "approved_by": approver,
        }
        plan_id = "PLAN-" + sha256_bytes(canonical_json_bytes(seed)).split(":", 1)[1][:16].upper()
        plan = ApprovedProductionPlan(
            plan_id=plan_id,
            proposal_id=latest.proposal_id,
            proposal_revision=latest.revision,
            proposal_sha256=pending.proposal_sha256,
            intent_sha256=latest.intent_sha256,
            blueprint_id=latest.blueprint.blueprint_id,
            blueprint_sha256=latest.blueprint.to_dict()["blueprint_sha256"],
            provider_policy=latest.provider_policy,
            reference_bindings=pending.reference_bindings,
            cost_ceiling=pending.cost_ceiling,
            currency=latest.currency,
            approved_by=approver,
            rights_warnings_acknowledged=pending.rights_warnings_acknowledged,
        )
        self.registry.add_approved_plan(plan)
        return plan
