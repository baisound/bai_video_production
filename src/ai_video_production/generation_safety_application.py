"""TASK-013 durable, Approved-Plan-bound Shot Feasibility Product application.

The application persists structured Human feasibility review only. It never
executes a Provider, creates a Candidate, spends Budget or mutates an NLE.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import secrets
from typing import Any, Callable, Mapping

from .atomic import AtomicJsonWriter
from .audit_application import Task038AuditApplication
from .errors import ProductError, ProductErrorCategory
from .planning_application import Task027PlanningApplication
from .production_control_store import _exclusive_snapshot_lock
from .serialization import canonical_json_bytes, sha256_bytes
from .shot_feasibility import (
    CheckState,
    ContinuityType,
    SceneGenerationReferenceSpec,
    ShotFeasibilityAssessment,
    ShotFeasibilityGate,
    StartFrameSource,
)
from .visual_compliance import VisualComplianceDecision
from .visual_compliance_audit import VisualComplianceAuditAdapter


TokenFactory = Callable[[], str]
_SNAPSHOT_NAME = "generation-safety.json"
_MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_HUMAN_CHECKS = (
    "subject_position_exists",
    "orientation_camera_compatible",
    "required_visible_coexists",
    "prohibited_change_not_required",
    "shot_reference_matches_final_camera",
    "task_axis_valid",
    "depth_order_valid",
    "occlusion_valid",
    "furniture_integrity_valid",
    "room_anchor_integrity_valid",
    "production_gear_absent",
    "character_identity_valid",
)
_ALL_CHECKS = _HUMAN_CHECKS + ("reference_roles_valid", "continuity_contract_valid")


@dataclass(slots=True)
class _PendingFeasibility:
    confirmation_id: str
    planning_snapshot_sha256: str
    safety_snapshot_sha256: str
    approved_plan_id: str
    approved_plan_sha256: str
    blueprint_sha256: str
    spec: SceneGenerationReferenceSpec
    assessment: ShotFeasibilityAssessment
    consumed: bool = False


def _body_without_hash(document: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key != "snapshot_sha256"}


def _with_hash(document: Mapping[str, Any]) -> dict[str, Any]:
    body = _body_without_hash(document)
    body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


class Task013GenerationSafetyApplication:
    """Exact project-scoped Human feasibility review facade."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        planning_application: Task027PlanningApplication | None = None,
        audit_application: Task038AuditApplication | None = None,
        token_factory: TokenFactory | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_GENERATION_SAFETY_PROJECT_ROOT_INVALID",
                "Generation Safety project root must be an existing regular directory",
                ProductErrorCategory.VALIDATION,
            )
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError(
                "ERR_GENERATION_SAFETY_PROJECT_ID_INVALID",
                "Generation Safety project_id must be non-empty text",
                ProductErrorCategory.VALIDATION,
            )
        if planning_application is not None and (
            planning_application.project_root != root or planning_application.project_id != project_id
        ):
            raise ProductError(
                "ERR_GENERATION_SAFETY_PLANNING_SCOPE_MISMATCH",
                "Generation Safety and Planning must use the same project root/id",
                ProductErrorCategory.SECURITY,
            )
        if audit_application is not None and (
            audit_application.project_root != root or audit_application.project_id != project_id
        ):
            raise ProductError(
                "ERR_GENERATION_SAFETY_AUDIT_SCOPE_MISMATCH",
                "Generation Safety and Audit must use the same project root/id",
                ProductErrorCategory.SECURITY,
            )
        self.project_root = root
        self.project_id = project_id
        self.snapshot_path = root / _SNAPSHOT_NAME
        self.planning_application = planning_application or Task027PlanningApplication(
            project_root=root,
            project_id=project_id,
        )
        self.audit_application = audit_application
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _PendingFeasibility] = {}

    def _empty(self) -> dict[str, Any]:
        return _with_hash({
            "generation_safety_version": "1.0.0",
            "task_owner": "TASK-013",
            "project_id": self.project_id,
            "revision": 0,
            "records": [],
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "candidate_created": False,
            "human_candidate_decision_recorded": False,
            "resolve_mutation_started": False,
        })

    def _validate_document(self, value: Any) -> None:
        if not isinstance(value, dict) or value.get("generation_safety_version") != "1.0.0":
            raise ProductError("ERR_GENERATION_SAFETY_SNAPSHOT_INVALID", "Generation Safety snapshot is invalid", ProductErrorCategory.DATA_INTEGRITY)
        expected_top = {
            "generation_safety_version", "task_owner", "project_id", "revision", "records",
            "provider_execution_started", "paid_execution_authorized", "candidate_created",
            "human_candidate_decision_recorded", "resolve_mutation_started", "snapshot_sha256",
        }
        if set(value) != expected_top or value.get("task_owner") != "TASK-013":
            raise ProductError("ERR_GENERATION_SAFETY_SNAPSHOT_INVALID", "Generation Safety snapshot fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("project_id") != self.project_id:
            raise ProductError("ERR_GENERATION_SAFETY_PROJECT_MISMATCH", "Generation Safety snapshot belongs to another project", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("snapshot_sha256") != _with_hash(value)["snapshot_sha256"]:
            raise ProductError("ERR_GENERATION_SAFETY_SNAPSHOT_CHECKSUM", "Generation Safety snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        if any(value.get(name) is not False for name in (
            "provider_execution_started", "paid_execution_authorized", "candidate_created",
            "human_candidate_decision_recorded", "resolve_mutation_started",
        )):
            raise ProductError("ERR_GENERATION_SAFETY_AUTHORITY_BOUNDARY", "Generation Safety snapshot claims prohibited authority", ProductErrorCategory.SECURITY)
        if isinstance(value.get("revision"), bool) or not isinstance(value.get("revision"), int) or value["revision"] < 0:
            raise ProductError("ERR_GENERATION_SAFETY_SNAPSHOT_INVALID", "Generation Safety revision is invalid", ProductErrorCategory.DATA_INTEGRITY)
        records = value.get("records")
        if not isinstance(records, list):
            raise ProductError("ERR_GENERATION_SAFETY_SNAPSHOT_INVALID", "Generation Safety records are invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value["revision"] != len(records):
            raise ProductError("ERR_GENERATION_SAFETY_REVISION_INVALID", "Generation Safety revision does not match append-only history", ProductErrorCategory.DATA_INTEGRITY)
        identities: set[str] = set()
        for expected_revision, row in enumerate(records, 1):
            if not isinstance(row, dict) or not isinstance(row.get("record_id"), str) or row["record_id"] in identities:
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_INVALID", "Generation Safety record identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
            identities.add(row["record_id"])
            required = {"record_id", "plan_id", "approved_plan_sha256", "blueprint_sha256", "planning_snapshot_sha256", "scene_id", "reference_spec", "assessment", "reviewed_by", "record_revision"}
            if set(row) != required or row["record_revision"] != expected_revision:
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_INVALID", "Generation Safety record fields are incomplete", ProductErrorCategory.DATA_INTEGRITY)
            if not all(isinstance(row[name], str) and _SHA_RE.fullmatch(row[name]) for name in ("approved_plan_sha256", "blueprint_sha256", "planning_snapshot_sha256")):
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_INVALID", "Generation Safety record hashes are invalid", ProductErrorCategory.DATA_INTEGRITY)
            if not isinstance(row["reviewed_by"], str) or not row["reviewed_by"].strip() or len(row["reviewed_by"]) > 256 or "\x00" in row["reviewed_by"]:
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_INVALID", "Generation Safety reviewer is invalid", ProductErrorCategory.DATA_INTEGRITY)
            spec = row["reference_spec"]
            assessment = row["assessment"]
            if not isinstance(spec, dict) or not isinstance(assessment, dict):
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_INVALID", "Generation Safety record bodies are invalid", ProductErrorCategory.DATA_INTEGRITY)
            if spec.get("reference_spec_sha256") != sha256_bytes(canonical_json_bytes({key: item for key, item in spec.items() if key != "reference_spec_sha256"})):
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_CHECKSUM", "Scene reference spec checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
            if assessment.get("assessment_sha256") != sha256_bytes(canonical_json_bytes({key: item for key, item in assessment.items() if key != "assessment_sha256"})):
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_CHECKSUM", "Shot Feasibility assessment checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
            if spec.get("reference_spec_sha256") != assessment.get("reference_spec_sha256"):
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_BINDING", "Feasibility assessment is detached from its reference spec", ProductErrorCategory.DATA_INTEGRITY)
            if spec.get("scene_id") != row["scene_id"] or assessment.get("scene_id") != row["scene_id"]:
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_BINDING", "Feasibility record Scene identity is inconsistent", ProductErrorCategory.DATA_INTEGRITY)
            check_values = assessment.get("checks")
            if not isinstance(check_values, dict) or set(check_values) != set(_ALL_CHECKS) or any(item not in {"PASS", "FAIL", "UNVERIFIED"} for item in check_values.values()):
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_INVALID", "Feasibility assessment check set is invalid", ProductErrorCategory.DATA_INTEGRITY)
            calculated_status = "FAIL" if "FAIL" in check_values.values() else ("REVIEW_REQUIRED" if "UNVERIFIED" in check_values.values() else "PASS")
            if assessment.get("status") != calculated_status or assessment.get("automatic_geometry_proof_claimed") is not False:
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_INVALID", "Feasibility assessment status is inconsistent", ProductErrorCategory.DATA_INTEGRITY)
            seed = {
                "project_id": self.project_id,
                "plan_id": row["plan_id"],
                "scene_id": row["scene_id"],
                "assessment_sha256": assessment.get("assessment_sha256"),
                "record_revision": expected_revision,
            }
            expected_id = "FEAS-" + sha256_bytes(canonical_json_bytes(seed)).split(":", 1)[1][:24].upper()
            if row["record_id"] != expected_id:
                raise ProductError("ERR_GENERATION_SAFETY_RECORD_IDENTITY", "Generation Safety record identity mismatch", ProductErrorCategory.DATA_INTEGRITY)

    def _load(self) -> dict[str, Any]:
        target = self.snapshot_path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ProductError("ERR_GENERATION_SAFETY_SNAPSHOT_FILE_INVALID", "Generation Safety snapshot must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        if not target.exists():
            return self._empty()
        size = target.stat().st_size
        if size <= 0 or size > _MAX_SNAPSHOT_BYTES:
            raise ProductError("ERR_GENERATION_SAFETY_SNAPSHOT_SIZE", "Generation Safety snapshot size is outside the allowed bound", ProductErrorCategory.DATA_INTEGRITY)
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_GENERATION_SAFETY_SNAPSHOT_READ", "Generation Safety snapshot could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc
        self._validate_document(value)
        return value

    @staticmethod
    def _require_expected(actual: str, expected: str, kind: str) -> None:
        if not isinstance(expected, str) or actual != expected:
            raise ProductError(
                "ERR_GENERATION_SAFETY_SNAPSHOT_CONFLICT",
                f"{kind} snapshot changed; reload before applying the review",
                ProductErrorCategory.STATE,
                details={"snapshot_kind": kind, "current_snapshot_sha256": actual},
            )

    @staticmethod
    def _current_plan(planning: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        workspace = planning.get("workspace")
        if not isinstance(workspace, dict) or workspace.get("go_status") != "APPROVED":
            raise ProductError("ERR_GENERATION_SAFETY_PLAN_NOT_APPROVED", "Shot Feasibility requires a current Human-approved Plan", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        plan = workspace.get("approved_plan")
        blueprint = workspace.get("blueprint")
        if not isinstance(plan, dict) or not isinstance(blueprint, dict):
            raise ProductError("ERR_GENERATION_SAFETY_PLAN_INVALID", "Approved Plan/Blueprint projection is invalid", ProductErrorCategory.DATA_INTEGRITY)
        return plan, blueprint

    @staticmethod
    def _spec(value: Mapping[str, Any]) -> SceneGenerationReferenceSpec:
        allowed = {
            "scene_id", "continuity_type", "character_required", "character_identity_profile_id",
            "character_reference_asset_ids", "room_master_asset_id", "room_shot_reference_asset_id",
            "style_reference_asset_id", "required_visible", "subject_orientation", "camera_semantic",
            "start_frame_source", "previous_end_asset_id", "previous_end_sha256", "start_asset_id",
            "start_asset_sha256", "prohibited_changes",
        }
        if set(value) != allowed:
            raise ProductError("ERR_GENERATION_SAFETY_SPEC_FIELDS", "Scene reference spec must contain the exact field set", ProductErrorCategory.VALIDATION)
        if not all(isinstance(value[name], list) for name in ("character_reference_asset_ids", "required_visible", "prohibited_changes")):
            raise ProductError("ERR_GENERATION_SAFETY_SPEC_INVALID", "Scene reference list fields are invalid", ProductErrorCategory.VALIDATION)
        if not isinstance(value["character_required"], bool):
            raise ProductError("ERR_GENERATION_SAFETY_SPEC_INVALID", "character_required must be a boolean", ProductErrorCategory.VALIDATION)
        try:
            return SceneGenerationReferenceSpec(
                scene_id=str(value["scene_id"]),
                continuity_type=ContinuityType(str(value["continuity_type"])),
                character_required=value["character_required"],
                character_identity_profile_id=value["character_identity_profile_id"],
                character_reference_asset_ids=tuple(value["character_reference_asset_ids"]),
                room_master_asset_id=value["room_master_asset_id"],
                room_shot_reference_asset_id=value["room_shot_reference_asset_id"],
                style_reference_asset_id=value["style_reference_asset_id"],
                required_visible=tuple(value["required_visible"]),
                subject_orientation=str(value["subject_orientation"]),
                camera_semantic=str(value["camera_semantic"]),
                start_frame_source=StartFrameSource(str(value["start_frame_source"])),
                previous_end_asset_id=value["previous_end_asset_id"],
                previous_end_sha256=value["previous_end_sha256"],
                start_asset_id=value["start_asset_id"],
                start_asset_sha256=value["start_asset_sha256"],
                prohibited_changes=tuple(value["prohibited_changes"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError("ERR_GENERATION_SAFETY_SPEC_INVALID", "Scene reference spec is invalid", ProductErrorCategory.VALIDATION) from exc

    @staticmethod
    def _checks(value: Mapping[str, Any]) -> dict[str, CheckState]:
        if set(value) != set(_HUMAN_CHECKS):
            raise ProductError(
                "ERR_GENERATION_SAFETY_CHECK_SET",
                "Human review must provide every Generation Safety check exactly once",
                ProductErrorCategory.VALIDATION,
                details={"missing": sorted(set(_HUMAN_CHECKS) - set(value)), "unexpected": sorted(set(value) - set(_HUMAN_CHECKS))},
            )
        try:
            checks = {name: CheckState(str(value[name])) for name in _HUMAN_CHECKS}
        except (TypeError, ValueError) as exc:
            raise ProductError("ERR_GENERATION_SAFETY_CHECK_STATE", "Human review check state is invalid", ProductErrorCategory.VALIDATION) from exc
        if CheckState.UNVERIFIED in checks.values():
            raise ProductError("ERR_GENERATION_SAFETY_CHECK_UNVERIFIED", "Durable Human review must explicitly PASS or FAIL every check", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        return checks

    @staticmethod
    def _scene(blueprint: Mapping[str, Any], scene_id: str) -> Mapping[str, Any]:
        scene = next((row for row in blueprint.get("scenes", ()) if row.get("scene_id") == scene_id), None)
        if scene is None:
            raise ProductError("ERR_GENERATION_SAFETY_SCENE_NOT_FOUND", "Scene does not belong to the current Approved Plan", ProductErrorCategory.DATA_INTEGRITY)
        return scene

    def snapshot(self) -> dict[str, Any]:
        planning = self.planning_application.snapshot()
        if len(planning.get("proposal_ids", ())) > 1:
            raise ProductError(
                "ERR_GENERATION_SAFETY_PROPOSAL_SELECTION_REQUIRED",
                "Generation Safety requires one explicit current Proposal; multiple implicit proposals are ambiguous",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"proposal_ids": planning["proposal_ids"]},
            )
        safety = self._load()
        result: dict[str, Any] = {
            "application_version": "1.0.0",
            "task_owner": "TASK-013",
            "project_id": self.project_id,
            "planning_snapshot_sha256": planning["snapshot_sha256"],
            "safety_snapshot_sha256": safety["snapshot_sha256"],
            "persisted": self.snapshot_path.exists(),
            "plan_status": "GO_REQUIRED",
            "plan": None,
            "scenes": [],
            "all_current_feasibility_pass": False,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "candidate_created": False,
            "human_candidate_decision_recorded": False,
            "visual_compliance_human_authority": "TASK-038",
            "visual_compliance_durable_audit_bound": self.audit_application is not None,
            "generation_admission_complete": False,
        }
        try:
            plan, blueprint = self._current_plan(planning)
        except ProductError as exc:
            if exc.code == "ERR_GENERATION_SAFETY_PLAN_NOT_APPROVED":
                return result
            raise
        plan_identity = (plan["plan_id"], plan["approved_plan_sha256"], plan["blueprint_sha256"], planning["snapshot_sha256"])
        current_records: dict[str, Mapping[str, Any]] = {}
        stale_counts: dict[str, int] = {}
        for row in safety["records"]:
            if (row["plan_id"], row["approved_plan_sha256"], row["blueprint_sha256"], row["planning_snapshot_sha256"]) == plan_identity:
                current_records[row["scene_id"]] = row
            else:
                stale_counts[row["scene_id"]] = stale_counts.get(row["scene_id"], 0) + 1
        scenes = []
        for scene in blueprint["scenes"]:
            record = current_records.get(scene["scene_id"])
            scenes.append({
                "scene": scene,
                "feasibility_status": "NOT_REVIEWED" if record is None else record["assessment"]["status"],
                "current_record": record,
                "stale_record_count": stale_counts.get(scene["scene_id"], 0),
            })
        result.update({
            "plan_status": "APPROVED",
            "plan": {
                "plan_id": plan["plan_id"],
                "approved_plan_sha256": plan["approved_plan_sha256"],
                "blueprint_id": plan["blueprint_id"],
                "blueprint_sha256": plan["blueprint_sha256"],
            },
            "scenes": scenes,
            "all_current_feasibility_pass": bool(scenes) and all(row["feasibility_status"] == "PASS" for row in scenes),
        })
        return result

    def prepare_feasibility(
        self,
        *,
        spec: Mapping[str, Any],
        human_reviewed_checks: Mapping[str, Any],
        blocking_reasons: tuple[str, ...],
        expected_planning_snapshot_sha256: str,
        expected_safety_snapshot_sha256: str,
    ) -> dict[str, Any]:
        if not isinstance(blocking_reasons, tuple) or not all(isinstance(item, str) for item in blocking_reasons):
            raise ProductError("ERR_GENERATION_SAFETY_BLOCKING_REASONS_INVALID", "Blocking reasons must be an exact tuple of codes", ProductErrorCategory.VALIDATION)
        planning = self.planning_application.snapshot()
        if len(planning.get("proposal_ids", ())) > 1:
            raise ProductError("ERR_GENERATION_SAFETY_PROPOSAL_SELECTION_REQUIRED", "Generation Safety cannot choose an implicit Proposal", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        safety = self._load()
        self._require_expected(planning["snapshot_sha256"], expected_planning_snapshot_sha256, "Planning")
        self._require_expected(safety["snapshot_sha256"], expected_safety_snapshot_sha256, "Generation Safety")
        plan, blueprint = self._current_plan(planning)
        reference_spec = self._spec(spec)
        self._scene(blueprint, reference_spec.scene_id)
        checks = self._checks(human_reviewed_checks)
        assessment = ShotFeasibilityGate.assess(reference_spec, human_reviewed_checks=checks, blocking_reasons=blocking_reasons)
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError("ERR_GENERATION_SAFETY_CONFIRMATION_TOKEN_INVALID", "Generation Safety confirmation token is invalid", ProductErrorCategory.INTERNAL)
        pending = _PendingFeasibility(
            token, planning["snapshot_sha256"], safety["snapshot_sha256"], plan["plan_id"],
            plan["approved_plan_sha256"], plan["blueprint_sha256"], reference_spec, assessment,
        )
        self._confirmations[token] = pending
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-013",
            "confirmation_id": token,
            "project_id": self.project_id,
            "plan_id": pending.approved_plan_id,
            "scene_id": reference_spec.scene_id,
            "reference_spec": reference_spec.to_dict(),
            "assessment": assessment.to_dict(),
            "human_final_authority_required": True,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
        }

    def apply_feasibility(self, *, confirmation_id: str, reviewed_by: str) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_GENERATION_SAFETY_CONFIRMATION_INVALID", "Generation Safety confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        reviewer = reviewed_by.strip() if isinstance(reviewed_by, str) else ""
        if not reviewer or len(reviewer) > 256 or "\x00" in reviewer:
            raise ProductError("ERR_GENERATION_SAFETY_REVIEWER_INVALID", "Generation Safety reviewer is invalid", ProductErrorCategory.VALIDATION)
        with _exclusive_snapshot_lock(self.snapshot_path):
            planning = self.planning_application.snapshot()
            safety = self._load()
            self._require_expected(planning["snapshot_sha256"], pending.planning_snapshot_sha256, "Planning")
            self._require_expected(safety["snapshot_sha256"], pending.safety_snapshot_sha256, "Generation Safety")
            plan, blueprint = self._current_plan(planning)
            self._scene(blueprint, pending.spec.scene_id)
            if (
                plan["plan_id"] != pending.approved_plan_id
                or plan["approved_plan_sha256"] != pending.approved_plan_sha256
                or plan["blueprint_sha256"] != pending.blueprint_sha256
            ):
                raise ProductError("ERR_GENERATION_SAFETY_CONFIRMATION_STALE", "Approved Plan changed after feasibility preparation", ProductErrorCategory.AUTHORIZATION)
            revision = safety["revision"] + 1
            record_seed = {
                "project_id": self.project_id,
                "plan_id": pending.approved_plan_id,
                "scene_id": pending.spec.scene_id,
                "assessment_sha256": pending.assessment.to_dict()["assessment_sha256"],
                "record_revision": revision,
            }
            record = {
                "record_id": "FEAS-" + sha256_bytes(canonical_json_bytes(record_seed)).split(":", 1)[1][:24].upper(),
                "plan_id": pending.approved_plan_id,
                "approved_plan_sha256": pending.approved_plan_sha256,
                "blueprint_sha256": pending.blueprint_sha256,
                "planning_snapshot_sha256": pending.planning_snapshot_sha256,
                "scene_id": pending.spec.scene_id,
                "reference_spec": pending.spec.to_dict(),
                "assessment": pending.assessment.to_dict(),
                "reviewed_by": reviewer,
                "record_revision": revision,
            }
            safety["revision"] = revision
            safety["records"].append(record)
            document = _with_hash(safety)
            AtomicJsonWriter.write(self.snapshot_path, document, validator=self._validate_document)
        return {"record": record, "application": self.snapshot()}

    def record_visual_compliance(
        self,
        decision: VisualComplianceDecision,
        *,
        audit_id: str,
        auditor_id: str,
        auditor_version: str | None,
        expected_production_snapshot_sha256: str,
        expected_audit_snapshot_sha256: str,
    ) -> dict[str, Any]:
        """Persist structured inspection as TASK-038 Evidence, never a Human decision."""

        if self.audit_application is None:
            raise ProductError(
                "ERR_GENERATION_SAFETY_AUDIT_NOT_BOUND",
                "Durable Visual Compliance requires the project Audit Application",
                ProductErrorCategory.STATE,
            )
        record = VisualComplianceAuditAdapter.to_audit(
            decision,
            audit_id=audit_id,
            auditor_id=auditor_id,
            auditor_version=auditor_version,
        )
        result = self.audit_application.record_audit(
            record=record,
            expected_production_snapshot_sha256=expected_production_snapshot_sha256,
            expected_audit_snapshot_sha256=expected_audit_snapshot_sha256,
        )
        return {
            "audit": result,
            "visual_decision": decision.to_dict(),
            "human_candidate_decision_recorded": False,
            "automatic_candidate_accept": False,
            "automatic_candidate_reject": False,
            "automatic_regeneration_started": False,
        }


__all__ = ["Task013GenerationSafetyApplication"]
