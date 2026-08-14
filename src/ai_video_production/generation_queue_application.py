"""TASK-027 durable Generation Queue admission Product application.

The application derives admission from exact persisted Product Evidence.  It
records queue intent only and never dispatches a Provider or grants paid work.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import secrets
from typing import Any, Callable, Mapping

from .atomic import AtomicJsonWriter
from .continuity_application import Task039ContinuityApplication
from .errors import ProductError, ProductErrorCategory
from .generation_safety_application import Task013GenerationSafetyApplication
from .planning_application import Task027PlanningApplication
from .production_control_application import Task037ProductionControlApplication
from .production_control_store import ProductionControlSnapshotStore, _exclusive_snapshot_lock
from .production_orchestrator import GenerationQueueAdmissionService
from .prompt_evidence_application import Task040PromptEvidenceApplication
from .serialization import canonical_json_bytes, sha256_bytes
from .shot_feasibility import CheckState, ShotFeasibilityAssessment


TokenFactory = Callable[[], str]
_QUEUE_NAME = "generation-queue.json"
_MAX_BYTES = 8 * 1024 * 1024
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_TOP_FIELDS = {
    "queue_version", "task_owner", "project_id", "revision", "entries",
    "provider_execution_authorized", "paid_execution_authorized",
    "candidate_creation_authorized", "queue_snapshot_sha256",
}
_ENTRY_FIELDS = {
    "entry_version", "task_owner", "queue_entry_id", "queue_revision", "project_id",
    "plan_id", "approved_plan_sha256", "scene_id", "slot_id", "prompt_id",
    "prompt_version", "prompt_sha256", "provider_profile_id",
    "provider_profile_version", "feasibility_record_id", "assessment_sha256",
    "input_bindings", "continuity_proof", "upstream_snapshots", "admission",
    "queue_status", "execution_status", "provider_execution_authorized",
    "paid_execution_authorized", "candidate_creation_authorized",
}
_UPSTREAM_FIELDS = {
    "planning", "generation_safety", "production", "continuity", "prompt", "audit",
}
_INPUT_FIELDS = {
    "asset_sha256", "proof_kind", "reference_id", "slot_id", "candidate_id", "asset_id",
}
_ADMISSION_FIELDS = {
    "scene_id", "slot_id", "status", "missing_locked_slot_ids", "feasibility_status",
    "cost_authorized", "cost_required", "provider_execution_started",
}
_CONTINUITY_FIELDS = {"edge_id", "boundary_type", "resolution"}


@dataclass(slots=True)
class _PendingEntry:
    confirmation_id: str
    queue_snapshot_sha256: str
    prompt_id: str
    prompt_version: int
    entry: dict[str, Any]
    consumed: bool = False


def _with_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != "queue_snapshot_sha256"}
    body["queue_snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


class Task027GenerationQueueApplication:
    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        production_control: Task037ProductionControlApplication,
        planning_application: Task027PlanningApplication,
        generation_safety_application: Task013GenerationSafetyApplication,
        continuity_application: Task039ContinuityApplication,
        prompt_evidence_application: Task040PromptEvidenceApplication,
        token_factory: TokenFactory | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError("ERR_QUEUE_PROJECT_ROOT_INVALID", "Generation Queue project root is invalid", ProductErrorCategory.VALIDATION)
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError("ERR_QUEUE_PROJECT_ID_INVALID", "Generation Queue project_id is invalid", ProductErrorCategory.VALIDATION)
        dependencies = (
            production_control, planning_application, generation_safety_application,
            continuity_application, prompt_evidence_application,
        )
        if any(item.project_root != root or item.project_id != project_id for item in dependencies):
            raise ProductError("ERR_QUEUE_APPLICATION_SCOPE_MISMATCH", "Generation Queue dependencies must share the exact project scope", ProductErrorCategory.SECURITY)
        self.project_root = root
        self.project_id = project_id
        self.queue_path = root / _QUEUE_NAME
        self.production_control = production_control
        self.planning_application = planning_application
        self.generation_safety_application = generation_safety_application
        self.continuity_application = continuity_application
        self.prompt_evidence_application = prompt_evidence_application
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _PendingEntry] = {}

    def _empty(self) -> dict[str, Any]:
        return _with_hash({
            "queue_version": "1.0.0", "task_owner": "TASK-027", "project_id": self.project_id,
            "revision": 0, "entries": [], "provider_execution_authorized": False,
            "paid_execution_authorized": False, "candidate_creation_authorized": False,
        })

    def _validate(self, value: Any) -> None:
        if not isinstance(value, dict) or set(value) != _TOP_FIELDS:
            raise ProductError("ERR_QUEUE_SNAPSHOT_INVALID", "Generation Queue snapshot fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("queue_version") != "1.0.0" or value.get("task_owner") != "TASK-027" or value.get("project_id") != self.project_id:
            raise ProductError("ERR_QUEUE_SNAPSHOT_INVALID", "Generation Queue snapshot identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("queue_snapshot_sha256") != _with_hash(value)["queue_snapshot_sha256"]:
            raise ProductError("ERR_QUEUE_SNAPSHOT_CHECKSUM", "Generation Queue snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        if any(value.get(name) is not False for name in (
            "provider_execution_authorized", "paid_execution_authorized", "candidate_creation_authorized",
        )):
            raise ProductError("ERR_QUEUE_AUTHORITY_BOUNDARY", "Generation Queue snapshot claims prohibited execution authority", ProductErrorCategory.SECURITY)
        revision, entries = value.get("revision"), value.get("entries")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0 or not isinstance(entries, list) or revision != len(entries):
            raise ProductError("ERR_QUEUE_REVISION_INVALID", "Generation Queue revision/history is invalid", ProductErrorCategory.DATA_INTEGRITY)
        seen: set[str] = set()
        for index, entry in enumerate(entries, 1):
            if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS or entry.get("queue_revision") != index:
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue entry fields/revision are invalid", ProductErrorCategory.DATA_INTEGRITY)
            if entry.get("project_id") != self.project_id or entry.get("task_owner") != "TASK-027" or entry.get("entry_version") != "1.0.0":
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue entry identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if not isinstance(entry.get("queue_entry_id"), str) or entry.get("queue_entry_id") in seen:
                raise ProductError("ERR_QUEUE_ENTRY_DUPLICATE", "Generation Queue entry identity is duplicated", ProductErrorCategory.DATA_INTEGRITY)
            seen.add(entry["queue_entry_id"])
            if set(entry.get("upstream_snapshots", {})) != _UPSTREAM_FIELDS:
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue upstream identities are invalid", ProductErrorCategory.DATA_INTEGRITY)
            if not all(isinstance(item, str) and _SHA_RE.fullmatch(item) for item in entry["upstream_snapshots"].values()):
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue upstream hashes are invalid", ProductErrorCategory.DATA_INTEGRITY)
            if not isinstance(entry.get("input_bindings"), list) or any(not isinstance(item, dict) or set(item) != _INPUT_FIELDS for item in entry["input_bindings"]):
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue input proofs are invalid", ProductErrorCategory.DATA_INTEGRITY)
            if any(
                not isinstance(item["asset_sha256"], str)
                or not _SHA_RE.fullmatch(item["asset_sha256"])
                or item["proof_kind"] not in {"HUMAN_GO_REFERENCE", "LOCKED_CURRENT_CANDIDATE"}
                for item in entry["input_bindings"]
            ):
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue input proof identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
            continuity = entry.get("continuity_proof")
            if continuity is not None and (not isinstance(continuity, dict) or set(continuity) != _CONTINUITY_FIELDS):
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue Continuity proof is invalid", ProductErrorCategory.DATA_INTEGRITY)
            admission = entry.get("admission")
            if (
                not isinstance(admission, dict) or set(admission) != _ADMISSION_FIELDS
                or admission.get("status") != "GENERATION_READY"
                or admission.get("missing_locked_slot_ids") != []
                or admission.get("feasibility_status") != "PASS"
                or admission.get("cost_authorized") is not False
                or admission.get("cost_required") is not False
                or admission.get("provider_execution_started") is not False
            ):
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue admission proof is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if not all(isinstance(entry.get(name), str) and _SHA_RE.fullmatch(entry[name]) for name in ("approved_plan_sha256", "prompt_sha256", "assessment_sha256")):
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue bound hashes are invalid", ProductErrorCategory.DATA_INTEGRITY)
            if entry.get("queue_status") != "ADMISSION_READY" or entry.get("execution_status") != "EXECUTION_NOT_AUTHORIZED":
                raise ProductError("ERR_QUEUE_ENTRY_INVALID", "Generation Queue status is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if any(entry.get(name) is not False for name in (
                "provider_execution_authorized", "paid_execution_authorized", "candidate_creation_authorized",
            )):
                raise ProductError("ERR_QUEUE_AUTHORITY_BOUNDARY", "Generation Queue entry claims prohibited authority", ProductErrorCategory.SECURITY)
            seed = {key: item for key, item in entry.items() if key != "queue_entry_id"}
            expected_id = "QUEUE-" + sha256_bytes(canonical_json_bytes(seed)).split(":", 1)[1][:24].upper()
            if entry["queue_entry_id"] != expected_id:
                raise ProductError("ERR_QUEUE_ENTRY_IDENTITY", "Generation Queue entry deterministic identity is invalid", ProductErrorCategory.DATA_INTEGRITY)

    def _load(self) -> dict[str, Any]:
        target = self.queue_path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ProductError("ERR_QUEUE_SNAPSHOT_FILE_INVALID", "Generation Queue snapshot must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        if not target.exists():
            return self._empty()
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_QUEUE_SNAPSHOT_SIZE", "Generation Queue snapshot size is outside the allowed bound", ProductErrorCategory.DATA_INTEGRITY)
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_QUEUE_SNAPSHOT_READ", "Generation Queue snapshot could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc
        self._validate(value)
        return value

    @staticmethod
    def _require_expected(actual: str, expected: str, kind: str) -> None:
        if not isinstance(expected, str) or actual != expected:
            raise ProductError("ERR_QUEUE_SNAPSHOT_CONFLICT", f"{kind} snapshot changed; reload before queue admission", ProductErrorCategory.STATE, details={"snapshot_kind": kind, "current_snapshot_sha256": actual})

    def _sources(self) -> dict[str, Any]:
        planning = self.planning_application.snapshot()
        production = self.production_control.snapshot()
        safety = self.generation_safety_application.snapshot()
        continuity = self.continuity_application.snapshot()
        prompts = self.prompt_evidence_application.snapshot()
        audit = self.prompt_evidence_application.audit_application.snapshot()
        production_sha = production["snapshot_sha256"]
        for name, value in (("Continuity", continuity["production_snapshot_sha256"]), ("Prompt", prompts["production_snapshot_sha256"]), ("Audit", audit["production_snapshot_sha256"])):
            self._require_expected(production_sha, value, f"{name}/Production")
        if continuity["recovery"]["required"]:
            raise ProductError("ERR_QUEUE_CONTINUITY_RECOVERY_REQUIRED", "Complete Continuity recovery before queue admission", ProductErrorCategory.STATE)
        if prompts["recovery"]["required"]:
            raise ProductError("ERR_QUEUE_PROMPT_RECOVERY_REQUIRED", "Complete Prompt recovery before queue admission", ProductErrorCategory.STATE)
        if audit["recovery"]["required"]:
            raise ProductError("ERR_QUEUE_AUDIT_RECOVERY_REQUIRED", "Complete Audit recovery before queue admission", ProductErrorCategory.STATE)
        return {"planning": planning, "production": production, "safety": safety, "continuity": continuity, "prompts": prompts, "audit": audit}

    @staticmethod
    def _assessment(record: Mapping[str, Any]) -> ShotFeasibilityAssessment:
        raw = record["assessment"]
        try:
            value = ShotFeasibilityAssessment(
                scene_id=raw["scene_id"], checks={name: CheckState(item) for name, item in raw["checks"].items()},
                decision_source=raw["decision_source"], blocking_reasons=tuple(raw["blocking_reasons"]),
                reference_spec_sha256=raw["reference_spec_sha256"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError("ERR_QUEUE_FEASIBILITY_INVALID", "Durable feasibility record is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        if value.to_dict()["assessment_sha256"] != raw.get("assessment_sha256"):
            raise ProductError("ERR_QUEUE_FEASIBILITY_INVALID", "Durable feasibility identity changed during recovery", ProductErrorCategory.DATA_INTEGRITY)
        return value

    @staticmethod
    def _v2_world_bindings(
        blueprint: Mapping[str, Any],
        plan: Mapping[str, Any],
        production: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        references = {
            row["reference_id"]: (row["asset_id"], row["asset_sha256"])
            for row in plan.get("reference_bindings", ())
        }
        slots = {row["slot_id"]: row for row in production["slots"]}
        requirements: list[dict[str, Any]] = []
        for scene in blueprint.get("scenes", ()):
            for frame_name, key in (("START", "start_frame_intent"), ("END", "end_frame_intent")):
                binding = scene[key]["binding"]
                prefix = f"{scene['scene_id']}:{frame_name}"
                rows = [
                    (f"{prefix}:CHARACTER:{index}", item, "CHARACTER_REFERENCE")
                    for index, item in enumerate(binding["character_locks"])
                ]
                if binding.get("space_lock") is not None:
                    rows.append((f"{prefix}:SPACE", binding["space_lock"], "SPACE_REFERENCE"))
                if binding.get("composition_lock") is not None:
                    rows.append((f"{prefix}:COMPOSITION", binding["composition_lock"], "COMPOSITION_REFERENCE"))
                for reference_id, expected, expected_slot_kind in rows:
                    slot = slots.get(expected["slot_id"])
                    candidate = None if slot is None else next(
                        (
                            row for row in slot["candidates"]
                            if row["candidate_id"] == expected["candidate_id"]
                        ),
                        None,
                    )
                    current = (
                        references.get(reference_id) == (expected["asset_id"], expected["asset_sha256"])
                        and slot is not None
                        and slot["slot_kind"] == expected_slot_kind
                        and slot["status"] == "LOCKED"
                        and slot["stale_state"] == "CURRENT"
                        and slot["locked_candidate_id"] == expected["candidate_id"]
                        and candidate is not None
                        and candidate["lifecycle_state"] == "LOCKED"
                        and candidate["asset_id"] == expected["asset_id"]
                        and candidate["asset_sha256"] == expected["asset_sha256"]
                    )
                    if not current:
                        raise ProductError(
                            "ERR_QUEUE_WORLD_LOCK_NOT_CURRENT",
                            "Blueprint v2 Queue admission requires each exact frame reference Candidate to be LOCKED/CURRENT",
                            ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                            details={"reference_id": reference_id},
                        )
                    requirements.append({
                        "reference_id": reference_id,
                        "slot_id": expected["slot_id"],
                        "candidate_id": expected["candidate_id"],
                        "asset_id": expected["asset_id"],
                        "asset_sha256": expected["asset_sha256"],
                    })
        if set(references) != {row["reference_id"] for row in requirements}:
            raise ProductError(
                "ERR_QUEUE_WORLD_LOCK_GO_REFERENCE_MISMATCH",
                "Blueprint v2 Approved Plan reference set differs from exact frame bindings",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return requirements

    @classmethod
    def _input_proofs(
        cls,
        prompt: Mapping[str, Any],
        plan: Mapping[str, Any],
        production: Mapping[str, Any],
        blueprint: Mapping[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
        if blueprint is not None and blueprint.get("blueprint_version") == "2.0.0":
            world = cls._v2_world_bindings(blueprint, plan, production)
            proofs: list[dict[str, Any]] = []
            required_slots: list[str] = []
            for asset_sha in prompt["input_asset_hashes"]:
                choices = [row for row in world if row["asset_sha256"] == asset_sha]
                if len(choices) != 1:
                    raise ProductError(
                        "ERR_QUEUE_INPUT_PROOF_AMBIGUOUS",
                        "Each Blueprint v2 Prompt input hash must resolve to exactly one typed WORLD LOCK frame binding",
                        ProductErrorCategory.AUTHORIZATION,
                        details={"asset_sha256": asset_sha, "match_count": len(choices)},
                    )
                row = choices[0]
                proofs.append({
                    "asset_sha256": asset_sha,
                    "proof_kind": "WORLD_LOCKED_CURRENT_CANDIDATE",
                    "reference_id": row["reference_id"],
                    "slot_id": row["slot_id"],
                    "candidate_id": row["candidate_id"],
                    "asset_id": row["asset_id"],
                })
                required_slots.append(row["slot_id"])
            return proofs, tuple(dict.fromkeys(required_slots))

        references = list(plan.get("reference_bindings", ()))
        locked = []
        for slot in production["slots"]:
            if slot["status"] != "LOCKED" or slot["stale_state"] != "CURRENT" or slot["locked_candidate_id"] is None:
                continue
            candidate = next((row for row in slot["candidates"] if row["candidate_id"] == slot["locked_candidate_id"]), None)
            if candidate is not None and candidate["lifecycle_state"] == "LOCKED":
                locked.append((slot, candidate))
        proofs: list[dict[str, Any]] = []
        required_slots: list[str] = []
        for asset_sha in prompt["input_asset_hashes"]:
            choices: list[dict[str, Any]] = []
            for item in references:
                if item["asset_sha256"] == asset_sha:
                    choices.append({"asset_sha256": asset_sha, "proof_kind": "HUMAN_GO_REFERENCE", "reference_id": item["reference_id"], "slot_id": None, "candidate_id": None, "asset_id": item["asset_id"]})
            for slot, candidate in locked:
                if candidate["asset_sha256"] == asset_sha:
                    choices.append({"asset_sha256": asset_sha, "proof_kind": "LOCKED_CURRENT_CANDIDATE", "reference_id": None, "slot_id": slot["slot_id"], "candidate_id": candidate["candidate_id"], "asset_id": candidate["asset_id"]})
            if len(choices) != 1:
                raise ProductError("ERR_QUEUE_INPUT_PROOF_AMBIGUOUS", "Each Prompt input hash must resolve to exactly one Human-GO reference or locked current Candidate", ProductErrorCategory.AUTHORIZATION, details={"asset_sha256": asset_sha, "match_count": len(choices)})
            proof = choices[0]
            proofs.append(proof)
            if proof["slot_id"] is not None:
                required_slots.append(proof["slot_id"])
        return proofs, tuple(required_slots)

    def _derive(self, *, prompt_id: str, prompt_version: int, queue_revision: int) -> dict[str, Any]:
        sources = self._sources()
        planning, production, safety = sources["planning"], sources["production"], sources["safety"]
        workspace = planning.get("workspace")
        installation = planning.get("installation")
        if not isinstance(workspace, dict) or workspace.get("go_status") != "APPROVED" or not isinstance(installation, dict) or installation.get("status") != "INSTALLED":
            raise ProductError("ERR_QUEUE_APPROVED_PLAN_REQUIRED", "Queue admission requires the exact installed Human-approved Plan", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        plan = workspace["approved_plan"]
        prompt = next((row for row in sources["prompts"]["prompts"] if row["prompt_id"] == prompt_id and row["prompt_version"] == prompt_version), None)
        if prompt is None:
            raise ProductError("ERR_QUEUE_PROMPT_NOT_FOUND", "Queue admission Prompt version does not exist", ProductErrorCategory.STATE)
        if prompt["provider_profile_id"] != plan["provider_policy"]["policy_id"] or prompt["provider_profile_version"] != plan["provider_policy"]["policy_version"]:
            raise ProductError("ERR_QUEUE_PROVIDER_POLICY_MISMATCH", "Prompt Provider Profile differs from the exact Human-approved policy", ProductErrorCategory.AUTHORIZATION)
        scene_id, slot_id = prompt["scene_id"], prompt["slot_id"]
        scene = next((row for row in safety["scenes"] if row["scene"]["scene_id"] == scene_id), None)
        if scene is None or scene["feasibility_status"] != "PASS" or scene["current_record"] is None:
            raise ProductError("ERR_QUEUE_FEASIBILITY_PASS_REQUIRED", "Queue admission requires current durable Feasibility PASS", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        record = scene["current_record"]
        assessment = self._assessment(record)
        proofs, required_slots = self._input_proofs(
            prompt,
            plan,
            production,
            workspace.get("blueprint"),
        )
        continuity_proof: dict[str, Any] | None = None
        continuity_type = record["reference_spec"]["continuity_type"]
        if continuity_type != "CUT":
            start_sha = record["reference_spec"].get("start_asset_sha256")
            start_proof = next((item for item in proofs if item["asset_sha256"] == start_sha and item["slot_id"] is not None), None)
            if start_proof is None:
                raise ProductError("ERR_QUEUE_CONTINUITY_INPUT_REQUIRED", "Non-CUT queue admission requires the exact locked Start Asset input", ProductErrorCategory.AUTHORIZATION)
            edges = sources["continuity"]["workspace"]["edges"]
            edge = next((item for item in edges if item["to_slot_id"] == start_proof["slot_id"] and item.get("generation_safe") is True), None)
            if edge is None:
                raise ProductError("ERR_QUEUE_CONTINUITY_NOT_SAFE", "Non-CUT queue admission requires exact generation-safe Continuity Evidence", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
            continuity_proof = {"edge_id": edge["edge_id"], "boundary_type": edge["boundary_type"], "resolution": edge["resolution"]}
        admission = GenerationQueueAdmissionService.require_ready(
            scene_id=scene_id, slot_id=slot_id, plan_approved=True, feasibility=assessment,
            required_input_slot_ids=required_slots,
            registry=ProductionControlSnapshotStore.load(self.production_control.snapshot_path),
            cost_authorized=False, cost_required=False,
        )
        upstream = {
            "planning": planning["snapshot_sha256"], "generation_safety": safety["safety_snapshot_sha256"],
            "production": production["snapshot_sha256"], "continuity": sources["continuity"]["continuity_snapshot_sha256"],
            "prompt": sources["prompts"]["prompt_snapshot_sha256"], "audit": sources["audit"]["audit_snapshot_sha256"],
        }
        entry: dict[str, Any] = {
            "entry_version": "1.0.0", "task_owner": "TASK-027", "queue_entry_id": "",
            "queue_revision": queue_revision, "project_id": self.project_id, "plan_id": plan["plan_id"],
            "approved_plan_sha256": plan["approved_plan_sha256"], "scene_id": scene_id, "slot_id": slot_id,
            "prompt_id": prompt_id, "prompt_version": prompt_version, "prompt_sha256": prompt["body_sha256"],
            "provider_profile_id": prompt["provider_profile_id"], "provider_profile_version": prompt["provider_profile_version"],
            "feasibility_record_id": record["record_id"], "assessment_sha256": record["assessment"]["assessment_sha256"],
            "input_bindings": proofs, "continuity_proof": continuity_proof, "upstream_snapshots": upstream,
            "admission": admission.to_dict(), "queue_status": "ADMISSION_READY",
            "execution_status": "EXECUTION_NOT_AUTHORIZED", "provider_execution_authorized": False,
            "paid_execution_authorized": False, "candidate_creation_authorized": False,
        }
        seed = {key: item for key, item in entry.items() if key != "queue_entry_id"}
        entry["queue_entry_id"] = "QUEUE-" + sha256_bytes(canonical_json_bytes(seed)).split(":", 1)[1][:24].upper()
        return entry

    def snapshot(self) -> dict[str, Any]:
        queue = self._load()
        upstream: dict[str, str] | None = None
        available_prompts: list[dict[str, Any]] = []
        admission_blocker: dict[str, str] | None = None
        try:
            sources = self._sources()
            upstream = {
                "planning": sources["planning"]["snapshot_sha256"],
                "generation_safety": sources["safety"]["safety_snapshot_sha256"],
                "production": sources["production"]["snapshot_sha256"],
                "continuity": sources["continuity"]["continuity_snapshot_sha256"],
                "prompt": sources["prompts"]["prompt_snapshot_sha256"],
                "audit": sources["audit"]["audit_snapshot_sha256"],
            }
            queued = {(item["prompt_id"], item["prompt_version"]) for item in queue["entries"]}
            available_prompts = [
                {"prompt_id": item["prompt_id"], "prompt_version": item["prompt_version"], "scene_id": item["scene_id"], "slot_id": item["slot_id"]}
                for item in sources["prompts"]["prompts"]
                if (item["prompt_id"], item["prompt_version"]) not in queued
            ]
        except ProductError as exc:
            admission_blocker = {"code": exc.code, "message": str(exc)}
        return {
            "application_version": "1.0.0", "task_owner": "TASK-027", "project_id": self.project_id,
            "queue_snapshot_sha256": queue["queue_snapshot_sha256"], "revision": queue["revision"],
            "entries": list(queue["entries"]), "entry_count": len(queue["entries"]),
            "upstream_snapshots": upstream, "available_prompts": available_prompts,
            "admission_blocker": admission_blocker,
            "provider_execution_started": False, "provider_execution_authorized": False,
            "paid_execution_authorized": False, "budget_reservation_created": False,
            "candidate_created": False, "resolve_mutation_started": False,
        }

    def require_current_entry(self, *, queue_entry_id: str) -> dict[str, Any]:
        """Re-derive one stored entry from every current upstream source.

        Queue Evidence is immutable, but execution consumers must not treat an
        old admission as current after LOCK/STALE, Feasibility, Continuity,
        Prompt/Profile or Approved Plan state changes.
        """
        queue = self._load()
        entry = next((item for item in queue["entries"] if item["queue_entry_id"] == queue_entry_id), None)
        if entry is None:
            raise ProductError("ERR_QUEUE_ENTRY_NOT_FOUND", "Generation Queue entry does not exist", ProductErrorCategory.STATE)
        current = self._derive(
            prompt_id=entry["prompt_id"],
            prompt_version=entry["prompt_version"],
            queue_revision=entry["queue_revision"],
        )
        if current != entry:
            raise ProductError(
                "ERR_QUEUE_ENTRY_STALE",
                "Generation Queue entry no longer matches current Product Evidence",
                ProductErrorCategory.AUTHORIZATION,
                details={"queue_entry_id": queue_entry_id},
            )
        return {
            "queue_snapshot_sha256": queue["queue_snapshot_sha256"],
            "entry": entry,
        }

    def prepare_enqueue(
        self, *, prompt_id: str, prompt_version: int, expected_queue_snapshot_sha256: str,
        expected_upstream_snapshots: Mapping[str, str],
    ) -> dict[str, Any]:
        queue = self._load()
        self._require_expected(queue["queue_snapshot_sha256"], expected_queue_snapshot_sha256, "Queue")
        entry = self._derive(prompt_id=prompt_id, prompt_version=prompt_version, queue_revision=queue["revision"] + 1)
        if set(expected_upstream_snapshots) != _UPSTREAM_FIELDS:
            raise ProductError("ERR_QUEUE_EXPECTED_SNAPSHOTS_INVALID", "Expected upstream snapshot set is invalid", ProductErrorCategory.VALIDATION)
        for name, actual in entry["upstream_snapshots"].items():
            self._require_expected(actual, expected_upstream_snapshots[name], name)
        if any(item["prompt_id"] == prompt_id and item["prompt_version"] == prompt_version for item in queue["entries"]):
            raise ProductError("ERR_QUEUE_PROMPT_ALREADY_ENQUEUED", "This exact Prompt version already has a queue admission record", ProductErrorCategory.STATE)
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError("ERR_QUEUE_CONFIRMATION_TOKEN_INVALID", "Generation Queue confirmation token is invalid", ProductErrorCategory.INTERNAL)
        self._confirmations[token] = _PendingEntry(token, queue["queue_snapshot_sha256"], prompt_id, prompt_version, entry)
        return {"confirmation_id": token, "entry": entry, "human_final_authority_required": True, "provider_execution_started": False, "paid_execution_authorized": False}

    def apply_enqueue(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_QUEUE_CONFIRMATION_INVALID", "Generation Queue confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        with _exclusive_snapshot_lock(self.queue_path):
            queue = self._load()
            self._require_expected(queue["queue_snapshot_sha256"], pending.queue_snapshot_sha256, "Queue")
            entry = self._derive(prompt_id=pending.prompt_id, prompt_version=pending.prompt_version, queue_revision=queue["revision"] + 1)
            if entry != pending.entry:
                raise ProductError("ERR_QUEUE_CONFIRMATION_STALE", "Queue admission Evidence changed after confirmation", ProductErrorCategory.AUTHORIZATION)
            queue["revision"] += 1
            queue["entries"].append(entry)
            document = _with_hash(queue)
            AtomicJsonWriter.write(self.queue_path, document, validator=self._validate)
        return self.snapshot()


__all__ = ["Task027GenerationQueueApplication"]
