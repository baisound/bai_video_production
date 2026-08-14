"""TASK-027 crash-safe local persistence for intent/proposal/GO state.

The snapshot contains project-private proposal text and immutable hashes, but
never credential values, provider execution authorization, or host paths.
Replacing an existing snapshot requires exact compare-and-swap identity.
"""

from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .production_blueprint import ProductionBlueprint
from .production_blueprint_v2 import ProductionBlueprintV2, parse_production_blueprint_document
from .production_proposal import (
    ApprovedProductionPlan,
    CreationIntent,
    ProductionProposalRegistry,
    ProductionProposalRevision,
    ProposalSection,
    ProviderPolicyBinding,
    ReferenceAssetBinding,
)
from .serialization import canonical_json_bytes, sha256_bytes
from .production_control_store import _exclusive_snapshot_lock


_MAX_BYTES = 16 * 1024 * 1024


def _body(registry: ProductionProposalRegistry) -> dict[str, Any]:
    body: dict[str, Any] = {
        "snapshot_version": "1.0.0",
        "task_owner": "TASK-027",
        "registry": registry.to_dict(),
        "credential_values_embedded": False,
        "host_paths_embedded": False,
        "provider_execution_authorized": False,
        "resolve_mutation_authorized": False,
        "publish_authorized": False,
    }
    body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _blueprint(row: dict[str, Any]) -> ProductionBlueprint | ProductionBlueprintV2:
    return parse_production_blueprint_document(row)


def _parse(document: dict[str, Any]) -> ProductionProposalRegistry:
    if document.get("snapshot_version") != "1.0.0":
        raise ProductError("ERR_PROPOSAL_SNAPSHOT_VERSION", "Unsupported Production Proposal snapshot version", ProductErrorCategory.DATA_INTEGRITY)
    expected = document.get("snapshot_sha256")
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError("ERR_PROPOSAL_SNAPSHOT_CHECKSUM", "Production Proposal snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if (
        document.get("credential_values_embedded") is not False
        or document.get("host_paths_embedded") is not False
        or document.get("provider_execution_authorized") is not False
        or document.get("resolve_mutation_authorized") is not False
        or document.get("publish_authorized") is not False
    ):
        raise ProductError("ERR_PROPOSAL_SNAPSHOT_BOUNDARY", "Production Proposal snapshot violates execution/privacy boundaries", ProductErrorCategory.SECURITY)
    registry_row = document.get("registry")
    if not isinstance(registry_row, dict):
        raise ProductError("ERR_PROPOSAL_SNAPSHOT_INVALID", "Production Proposal snapshot registry is invalid", ProductErrorCategory.DATA_INTEGRITY)
    # Verify the embedded registry identity before rehydrating it.
    registry_expected = registry_row.get("registry_sha256")
    registry_body = {key: value for key, value in registry_row.items() if key != "registry_sha256"}
    if registry_expected != sha256_bytes(canonical_json_bytes(registry_body)):
        raise ProductError("ERR_PROPOSAL_SNAPSHOT_REGISTRY_CHECKSUM", "Embedded Production Proposal registry checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if registry_row.get("provider_execution_started") is not False:
        raise ProductError("ERR_PROPOSAL_SNAPSHOT_EXECUTION_BOUNDARY", "Proposal snapshot cannot authorize provider execution", ProductErrorCategory.SECURITY)

    try:
        registry = ProductionProposalRegistry()
        for row in sorted(registry_row["intents"], key=lambda item: (item["intent_id"], int(item["revision"]))):
            intent = CreationIntent(
                intent_id=row["intent_id"],
                revision=int(row["revision"]),
                purpose=row["purpose"],
                audience=row["audience"],
                platform=row["platform"],
                aspect_ratio=row["aspect_ratio"],
                target_duration_seconds=Decimal(row["target_duration_seconds"]),
                style_tone=row["style_tone"],
                story_message=row["story_message"],
                language=row["language"],
                free_text=row.get("free_text", ""),
                budget_ceiling=None if row.get("budget_ceiling") is None else Decimal(row["budget_ceiling"]),
                currency=row["currency"],
                rights_constraints=tuple(row.get("rights_constraints", [])),
            )
            if row.get("intent_sha256") != intent.to_dict()["intent_sha256"]:
                raise ValueError("intent checksum mismatch")
            registry.add_intent(intent)

        for row in sorted(registry_row["proposals"], key=lambda item: (item["proposal_id"], int(item["revision"]))):
            cost = row["estimated_cost_range"]
            policy = row["provider_policy"]
            proposal = ProductionProposalRevision(
                proposal_id=row["proposal_id"],
                revision=int(row["revision"]),
                parent_proposal_sha256=row.get("parent_proposal_sha256"),
                intent_sha256=row["intent_sha256"],
                blueprint=_blueprint(row["blueprint"]),
                sections=tuple(ProposalSection(item["section_id"], item["kind"], item["title"], item["body"]) for item in row["sections"]),
                provider_policy=ProviderPolicyBinding(policy["policy_id"], policy["policy_version"], policy["policy_sha256"]),
                estimated_cost_min=Decimal(cost["min"]),
                estimated_cost_max=Decimal(cost["max"]),
                currency=cost["currency"],
                rights_warnings=tuple(row.get("rights_warnings", [])),
            )
            if row.get("proposal_sha256") != proposal.to_dict()["proposal_sha256"]:
                raise ValueError("proposal checksum mismatch")
            registry.add_proposal(proposal)

        for row in registry_row["approved_plans"]:
            policy = row["provider_policy"]
            plan = ApprovedProductionPlan(
                plan_id=row["plan_id"],
                proposal_id=row["proposal_id"],
                proposal_revision=int(row["proposal_revision"]),
                proposal_sha256=row["proposal_sha256"],
                intent_sha256=row["intent_sha256"],
                blueprint_id=row["blueprint_id"],
                blueprint_sha256=row["blueprint_sha256"],
                provider_policy=ProviderPolicyBinding(policy["policy_id"], policy["policy_version"], policy["policy_sha256"]),
                reference_bindings=tuple(
                    ReferenceAssetBinding(item["reference_id"], item["asset_id"], item["asset_sha256"])
                    for item in row["reference_bindings"]
                ),
                cost_ceiling=Decimal(row["cost_ceiling"]),
                currency=row["currency"],
                approved_by=row["approved_by"],
                rights_warnings_acknowledged=bool(row["rights_warnings_acknowledged"]),
            )
            if row.get("approved_plan_sha256") != plan.to_dict()["approved_plan_sha256"]:
                raise ValueError("approved plan checksum mismatch")
            # An approved plan must still point at the exact Proposal revision in this snapshot.
            revisions = registry.proposals.get(plan.proposal_id, [])
            matching = [item for item in revisions if item.revision == plan.proposal_revision]
            if len(matching) != 1 or matching[0].to_dict()["proposal_sha256"] != plan.proposal_sha256:
                raise ValueError("approved plan proposal reference mismatch")
            if matching[0].blueprint.to_dict()["blueprint_sha256"] != plan.blueprint_sha256:
                raise ValueError("approved plan blueprint reference mismatch")
            registry.add_approved_plan(plan)
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise ProductError("ERR_PROPOSAL_SNAPSHOT_INVALID", "Production Proposal snapshot contains invalid records", ProductErrorCategory.DATA_INTEGRITY) from exc

    if registry.to_dict()["registry_sha256"] != registry_expected:
        raise ProductError("ERR_PROPOSAL_SNAPSHOT_ROUNDTRIP", "Production Proposal snapshot did not round-trip to the same registry identity", ProductErrorCategory.DATA_INTEGRITY)
    return registry


class ProductionProposalSnapshotStore:
    @staticmethod
    def snapshot(registry: ProductionProposalRegistry) -> dict[str, Any]:
        return _body(registry)

    @staticmethod
    def load(path: str | Path) -> ProductionProposalRegistry:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_PROPOSAL_SNAPSHOT_FILE_INVALID", "Production Proposal snapshot must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_PROPOSAL_SNAPSHOT_SIZE", "Production Proposal snapshot size is outside the allowed bound", ProductErrorCategory.VALIDATION, details={"size_bytes": size})
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PROPOSAL_SNAPSHOT_READ", "Production Proposal snapshot could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(document, dict):
            raise ProductError("ERR_PROPOSAL_SNAPSHOT_INVALID", "Production Proposal snapshot root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        return _parse(document)

    @staticmethod
    def save(
        path: str | Path,
        registry: ProductionProposalRegistry,
        *,
        expected_previous_snapshot_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = Path(path)
        with _exclusive_snapshot_lock(target):
            if target.is_symlink():
                raise ProductError("ERR_PROPOSAL_SNAPSHOT_FILE_INVALID", "Refusing to replace a symlink Production Proposal snapshot", ProductErrorCategory.SECURITY)
            if target.exists():
                if not target.is_file():
                    raise ProductError("ERR_PROPOSAL_SNAPSHOT_FILE_INVALID", "Production Proposal snapshot target must be a regular file", ProductErrorCategory.VALIDATION)
                if expected_previous_snapshot_sha256 is None:
                    raise ProductError("ERR_PROPOSAL_SNAPSHOT_CAS_REQUIRED", "Replacing a Production Proposal snapshot requires its exact previous checksum", ProductErrorCategory.AUTHORIZATION)
                current = _body(ProductionProposalSnapshotStore.load(target))["snapshot_sha256"]
                if current != expected_previous_snapshot_sha256:
                    raise ProductError("ERR_PROPOSAL_SNAPSHOT_REVISION_CONFLICT", "Production Proposal snapshot changed before save; reload before retry", ProductErrorCategory.STATE, details={"current_snapshot_sha256": current})
            elif expected_previous_snapshot_sha256 is not None:
                raise ProductError("ERR_PROPOSAL_SNAPSHOT_PREVIOUS_MISSING", "Expected previous Production Proposal snapshot does not exist", ProductErrorCategory.STATE)
            document = _body(registry)
            return AtomicJsonWriter.write(target, document, validator=lambda value: _parse(value))
