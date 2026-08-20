"""Human-confirmed local planning generation into the canonical TASK-027 store."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import base64
import json
from pathlib import Path
import secrets
from threading import Lock
from typing import Any, Callable

from .ai_connections import AiConnectionProfile, AiConnectionResolver, AiWorkload, ConnectionAvailability, ModelRoute
from .errors import ProductError, ProductErrorCategory
from .local_ollama_planning import LOCAL_PLANNING_CANDIDATE_SCHEMA, LocalOllamaPlanningAdapter, LocalPlanningCandidate, validate_local_planning_route
from .planning_application import Task027PlanningApplication
from .production_blueprint import AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk, ProductionBlueprint, SceneAudioPlan
from .production_control_store import _exclusive_snapshot_lock
from .production_proposal import CreationIntent, ProductionProposalRevision, ProposalSection, ProviderPolicyBinding
from .product_project_store import ProductProjectManifestStore
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .timebase import FrameRate


ConnectionProvider = Callable[[], tuple[AiConnectionProfile, ConnectionAvailability]]
AdapterFactory = Callable[[ModelRoute], LocalOllamaPlanningAdapter]
TokenFactory = Callable[[], str]
_MAX_CONFIRMATIONS = 256
_PLANNING_PROMPT_CONTRACT = (
    "次の要望から、Human review前の動画制作企画を日本語中心で構成してください。"
    "ModelはID、費用、権限、host pathを決めません。Sceneはtarget durationを完全に覆ってください。"
)


@dataclass(slots=True)
class _Confirmation:
    confirmation_id: str
    request_text: str
    request_sha256: str
    planning_snapshot_sha256: str
    connection_sha256: str
    route_id: str
    policy_sha256: str
    project_manifest_sha256: str
    provenance_body: str


class Task036PlanningGenerationApplication:
    def __init__(
        self,
        *,
        planning_application: Task027PlanningApplication,
        connection_provider: ConnectionProvider,
        adapter_factory: AdapterFactory | None = None,
        token_factory: TokenFactory | None = None,
    ) -> None:
        if not isinstance(planning_application, Task027PlanningApplication) or not callable(connection_provider):
            raise ValueError("Planning generation dependencies are invalid")
        self.planning = planning_application
        self.project_root = planning_application.project_root
        self.project_id = planning_application.project_id
        self._connection_provider = connection_provider
        self._adapter_factory = adapter_factory or (lambda route: LocalOllamaPlanningAdapter(route))
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _Confirmation] = {}
        self._confirmation_lock = Lock()
        self._operation_lock = Path(self.project_root) / "task036-planning-generation.json"
        self._project_manifest()

    def _project_manifest(self) -> str:
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_id != self.project_id:
            raise ProductError("ERR_TASK036_PLANNING_PROJECT_SCOPE_MISMATCH", "Planning generation requires the exact canonical Product Project", ProductErrorCategory.SECURITY)
        return manifest.project_manifest_sha256

    @staticmethod
    def _request(value: Any) -> tuple[str, str]:
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise ProductError("ERR_TASK036_PLANNING_REQUEST_INVALID", "Planning request must be non-empty text", ProductErrorCategory.VALIDATION)
        text = value.strip()
        try:
            encoded = text.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ProductError("ERR_TASK036_PLANNING_REQUEST_INVALID", "Planning request must be valid Unicode text", ProductErrorCategory.VALIDATION) from exc
        if len(encoded) > 16 * 1024:
            raise ProductError("ERR_TASK036_PLANNING_REQUEST_INVALID", "Planning request exceeds the size bound", ProductErrorCategory.VALIDATION)
        return text, sha256_bytes(encoded)

    @staticmethod
    def _ids(request_sha256: str) -> tuple[str, str, str]:
        validate_sha256(request_sha256)
        suffix = base64.b32encode(bytes.fromhex(request_sha256.removeprefix("sha256:"))).decode("ascii").rstrip("=")
        return f"INTENT-AI-{suffix}", f"PROPOSAL-AI-{suffix}", f"BP-AI-{suffix}"

    @staticmethod
    def _connection_coordinate(profile: AiConnectionProfile, availability: ConnectionAvailability) -> str:
        body = {
            "profile_sha256": profile.to_dict()["profile_sha256"],
            "available_route_ids": sorted(availability.available_route_ids),
            "available_credential_refs": sorted(availability.available_credential_refs),
        }
        return sha256_bytes(canonical_json_bytes(body))

    @staticmethod
    def _select_route(profile: AiConnectionProfile, availability: ConnectionAvailability) -> ModelRoute:
        eligible: set[str] = set()
        for route in profile.routes:
            try:
                validate_local_planning_route(route)
            except ProductError:
                continue
            if route.route_id in availability.available_route_ids:
                eligible.add(route.route_id)
        restricted = ConnectionAvailability(frozenset(eligible), frozenset())
        route = AiConnectionResolver.resolve(profile, AiWorkload.PLANNING, restricted, required_capabilities=("TEXT_GENERATION",))
        validate_local_planning_route(route)
        return route

    @staticmethod
    def _policy(profile: AiConnectionProfile, route: ModelRoute) -> ProviderPolicyBinding:
        del route
        return ProviderPolicyBinding(
            profile.profile_id, profile.profile_version,
            profile.to_dict()["profile_sha256"],
        )

    @staticmethod
    def _provenance(
        profile: AiConnectionProfile,
        route: ModelRoute,
        request_sha256: str,
        *,
        project_id: str,
        project_manifest_sha256: str,
    ) -> str:
        body = {
            "provenance_version": "1.0.0", "task_owner": "TASK-036",
            "project_id": project_id,
            "origin_project_manifest_sha256": project_manifest_sha256,
            "profile_sha256": profile.to_dict()["profile_sha256"],
            "route_id": route.route_id, "provider_family": route.provider_family.value,
            "provider_id": route.provider_id, "model_id": route.model_id,
            "cost_class": route.cost_class.value,
            "candidate_schema_sha256": sha256_bytes(canonical_json_bytes(LOCAL_PLANNING_CANDIDATE_SCHEMA)),
            "request_sha256": request_sha256,
            "prompt_contract_sha256": sha256_bytes(
                _PLANNING_PROMPT_CONTRACT.encode("utf-8")
            ),
            "credential_required": False, "paid_execution_authorized": False,
        }
        return canonical_json_bytes(body).decode("utf-8")

    def _connection(self) -> tuple[AiConnectionProfile, ConnectionAvailability, ModelRoute, str, ProviderPolicyBinding]:
        profile, availability = self._connection_provider()
        if not isinstance(profile, AiConnectionProfile) or not isinstance(availability, ConnectionAvailability):
            raise ProductError("ERR_TASK036_PLANNING_CONNECTION_INVALID", "Planning connection snapshot is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            profile = AiConnectionProfile.from_dict(json.loads(canonical_json_bytes(profile.to_dict()).decode("utf-8")))
            availability = ConnectionAvailability(
                frozenset(availability.available_route_ids),
                frozenset(availability.available_credential_refs),
            )
        except (KeyError, TypeError, ValueError, UnicodeError) as exc:
            raise ProductError("ERR_TASK036_PLANNING_CONNECTION_INVALID", "Planning connection snapshot is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        route = self._select_route(profile, availability)
        return profile, availability, route, self._connection_coordinate(profile, availability), self._policy(profile, route)

    def _existing(self, *, proposal_id: str, intent_id: str, blueprint_id: str, policy: ProviderPolicyBinding, request_sha256: str, provenance_body: str) -> dict[str, Any] | None:
        snapshot = self.planning.snapshot()
        if proposal_id not in snapshot["proposal_ids"]:
            return None
        selected = self.planning.snapshot(proposal_id=proposal_id)
        workspace = selected["workspace"]
        request_bindings = [
            item for item in workspace["sections"]
            if item["section_id"] == "task036_request_binding"
        ]
        provenances = [
            item for item in workspace["sections"]
            if item["section_id"] == "task036_local_provenance"
        ]
        if (
            workspace["creation_intent"]["intent_id"] != intent_id
            or workspace["creation_intent"]["revision"] != 1
            or workspace["creation_intent"]["budget_ceiling"] != "0"
            or workspace["creation_intent"]["currency"] != "JPY"
            or workspace["blueprint"]["blueprint_id"] != blueprint_id
            or workspace["latest_revision"] != 1
            or workspace["provider_policy"] != policy.to_dict()
            or workspace["estimated_cost_range"] != {
                "min": "0", "max": "0", "currency": "JPY",
            }
            or len(request_bindings) != 1
            or request_bindings[0] != {
                "section_id": "task036_request_binding", "kind": "REQUEST_BINDING",
                "title": "TASK-036 request binding", "body": request_sha256,
            }
            or len(provenances) != 1
            or provenances[0] != {
                "section_id": "task036_local_provenance", "kind": "PROVIDER_PROVENANCE",
                "title": "TASK-036 local planning provenance", "body": provenance_body,
            }
        ):
            raise ProductError("ERR_TASK036_PLANNING_REQUEST_ID_CONFLICT", "Deterministic Planning identity conflicts with different canonical content", ProductErrorCategory.DATA_INTEGRITY)
        return selected

    def status(self) -> dict[str, Any]:
        self._project_manifest()
        _, _, route, _, _ = self._connection()
        return {
            "available": True,
            "route_id": route.route_id,
            "model_id": route.model_id,
            "cost_class": route.cost_class.value,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "human_confirmation_required": True,
        }

    def prepare(self, *, vague_request: str, expected_planning_snapshot_sha256: str) -> dict[str, Any]:
        request_text, request_sha = self._request(vague_request)
        project_manifest_sha = self._project_manifest()
        planning = self.planning.snapshot()
        if planning["snapshot_sha256"] != expected_planning_snapshot_sha256:
            raise ProductError("ERR_TASK036_PLANNING_SNAPSHOT_STALE", "Planning state changed before generation preparation", ProductErrorCategory.STATE)
        profile, _, route, connection_sha, policy = self._connection()
        intent_id, proposal_id, blueprint_id = self._ids(request_sha)
        provenance_body = self._provenance(
            profile,
            route,
            request_sha,
            project_id=self.project_id,
            project_manifest_sha256=project_manifest_sha,
        )
        existing = self._existing(proposal_id=proposal_id, intent_id=intent_id, blueprint_id=blueprint_id, policy=policy, request_sha256=request_sha, provenance_body=provenance_body)
        if existing is None and not self._adapter_factory(route).ready():
            raise ProductError("ERR_LOCAL_OLLAMA_MODEL_MISSING", "Configured Ollama model is not installed locally", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        token = self._token_factory()
        with self._confirmation_lock:
            if not isinstance(token, str) or not token.strip() or token in self._confirmations:
                raise ProductError("ERR_TASK036_PLANNING_CONFIRMATION_INVALID", "Planning confirmation token is invalid", ProductErrorCategory.INTERNAL)
            if len(self._confirmations) >= _MAX_CONFIRMATIONS:
                raise ProductError("ERR_TASK036_PLANNING_CONFIRMATION_CAPACITY", "Planning confirmation capacity is full", ProductErrorCategory.STATE)
            self._confirmations[token] = _Confirmation(token, request_text, request_sha, planning["snapshot_sha256"], connection_sha, route.route_id, policy.policy_sha256, project_manifest_sha, provenance_body)
        return {
            "confirmation_version": "1.0.0", "task_owner": "TASK-036", "confirmation_id": token,
            "project_id": self.project_id, "request_sha256": request_sha,
            "route_id": route.route_id, "model_id": route.model_id,
            "cost_class": route.cost_class.value, "already_generated": existing is not None,
            "request_text_exposed": False, "host_paths_exposed": False,
            "provider_execution_started": False, "paid_execution_authorized": False,
            "human_confirmation_required": True,
        }

    @staticmethod
    def _compile_prompt(request_text: str) -> str:
        return _PLANNING_PROMPT_CONTRACT + "\n\n" + request_text

    @staticmethod
    def _records(candidate: LocalPlanningCandidate, *, request_sha256: str, policy: ProviderPolicyBinding, provenance_body: str) -> tuple[CreationIntent, ProductionProposalRevision]:
        intent_id, proposal_id, blueprint_id = Task036PlanningGenerationApplication._ids(request_sha256)
        reserved = {"task036_request_binding", "task036_local_provenance"}
        if reserved.intersection(item.section_id for item in candidate.sections):
            raise ProductError("ERR_TASK036_PLANNING_RESERVED_SECTION", "Model candidate used a Product-reserved Proposal section", ProductErrorCategory.DATA_INTEGRITY)
        intent = CreationIntent(
            intent_id, 1, candidate.intent.purpose, candidate.intent.audience,
            candidate.intent.platform, candidate.intent.aspect_ratio, Decimal(candidate.intent.target_duration_seconds),
            candidate.intent.style_tone, candidate.intent.story_message, candidate.intent.language,
            candidate.intent.free_text, Decimal("0"), "JPY", candidate.intent.rights_constraints,
        )
        scenes = tuple(BlueprintScene(
            item.scene_id, item.start_frame, item.end_frame, item.narrative_role,
            AssetSourceStrategy(item.source_strategy), GenerationRisk(item.generation_risk), CameraMotion(item.camera_motion), (),
            SceneAudioPlan(item.narration, item.dialogue, item.sound_effects, item.bgm, item.sound_logo),
            item.locked_reference, item.post_composite_text, item.final_hold_frames,
        ) for item in candidate.scenes)
        blueprint = ProductionBlueprint(
            blueprint_id, candidate.proposal_title, FrameRate(candidate.timeline_fps),
            candidate.intent.target_duration_seconds * candidate.timeline_fps, (), scenes,
        )
        proposal = ProductionProposalRevision(
            proposal_id, 1, intent.to_dict()["intent_sha256"], blueprint,
            tuple(ProposalSection(item.section_id, item.kind, item.title, item.body) for item in candidate.sections)
            + (
                ProposalSection("task036_request_binding", "REQUEST_BINDING", "TASK-036 request binding", request_sha256),
                ProposalSection("task036_local_provenance", "PROVIDER_PROVENANCE", "TASK-036 local planning provenance", provenance_body),
            ),
            policy, Decimal("0"), Decimal("0"), "JPY", candidate.rights_warnings,
        )
        return intent, proposal

    def apply(self, *, confirmation_id: str) -> dict[str, Any]:
        with self._confirmation_lock:
            pending = self._confirmations.pop(confirmation_id, None)
        if pending is None:
            raise ProductError("ERR_TASK036_PLANNING_CONFIRMATION_INVALID", "Planning confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        with _exclusive_snapshot_lock(self._operation_lock):
            if self._project_manifest() != pending.project_manifest_sha256:
                raise ProductError("ERR_TASK036_PLANNING_PROJECT_STALE", "Product Project changed after confirmation", ProductErrorCategory.STATE)
            profile, _, route, connection_sha, policy = self._connection()
            if connection_sha != pending.connection_sha256 or route.route_id != pending.route_id or policy.policy_sha256 != pending.policy_sha256:
                raise ProductError("ERR_TASK036_PLANNING_CONNECTION_STALE", "Planning connection changed after confirmation", ProductErrorCategory.STATE)
            intent_id, proposal_id, blueprint_id = self._ids(pending.request_sha256)
            existing = self._existing(proposal_id=proposal_id, intent_id=intent_id, blueprint_id=blueprint_id, policy=policy, request_sha256=pending.request_sha256, provenance_body=pending.provenance_body)
            if existing is not None:
                return {"idempotent": True, "proposal_id": proposal_id, "application": existing, "provider_execution_started": False, "paid_execution_authorized": False}
            planning = self.planning.snapshot()
            if planning["snapshot_sha256"] != pending.planning_snapshot_sha256:
                raise ProductError("ERR_TASK036_PLANNING_SNAPSHOT_STALE", "Planning state changed after confirmation", ProductErrorCategory.STATE)
            candidate = self._adapter_factory(route).generate(self._compile_prompt(pending.request_text))
            _, _, route_after, connection_after, policy_after = self._connection()
            if self._project_manifest() != pending.project_manifest_sha256:
                raise ProductError("ERR_TASK036_PLANNING_PROJECT_STALE", "Product Project changed during local generation", ProductErrorCategory.STATE)
            if (
                connection_after != pending.connection_sha256
                or route_after.route_id != pending.route_id
                or policy_after.policy_sha256 != pending.policy_sha256
            ):
                raise ProductError("ERR_TASK036_PLANNING_CONNECTION_STALE", "Planning authority changed during local generation", ProductErrorCategory.STATE)
            intent, proposal = self._records(candidate, request_sha256=pending.request_sha256, policy=policy, provenance_body=pending.provenance_body)
            application = self.planning.append_initial_proposal(
                intent=intent, proposal=proposal,
                expected_snapshot_sha256=pending.planning_snapshot_sha256,
                expected_project_manifest_sha256=pending.project_manifest_sha256,
            )
        return {
            "idempotent": False, "proposal_id": proposal.proposal_id,
            "proposal_sha256": proposal.to_dict()["proposal_sha256"], "application": application,
            "provider_execution_started": True, "provider_family": route.provider_family.value,
            "model_id": route.model_id, "cost_class": route.cost_class.value,
            "paid_execution_authorized": False, "human_go_approved": False,
        }

    def cancel(self, *, confirmation_id: str) -> dict[str, Any]:
        with self._confirmation_lock:
            pending = self._confirmations.pop(confirmation_id, None)
        if pending is None:
            raise ProductError("ERR_TASK036_PLANNING_CONFIRMATION_INVALID", "Planning confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        return {
            "cancelled": True, "confirmation_id": pending.confirmation_id,
            "provider_execution_started": False, "paid_execution_authorized": False,
        }
