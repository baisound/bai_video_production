"""TASK-041 Audio Workspace projection and Human placement-decision boundary.

The application surface remains non-destructive.  It can confirm placement
review decisions, but it never writes media, starts a DAW, compiles TASK-026,
or mutates Resolve by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Any, Callable

from .audio_workspace import AudioWorkspaceRegistry, PlacementDecision, PlacementReview
from .audio_workspace_store import AudioWorkspaceSnapshotStore
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry, SlotKind
from .production_control_application import Task037ProductionControlApplication
from .production_control_store import ProductionControlSnapshotStore, _exclusive_snapshot_lock
from .serialization import canonical_json_bytes, sha256_bytes


TokenFactory = Callable[[], str]


@dataclass(slots=True)
class _PlacementConfirmation:
    confirmation_id: str
    review_id: str
    candidate_id: str
    candidate_asset_sha256: str
    placement_sha256: str
    decision: PlacementDecision
    consumed: bool = False


@dataclass(slots=True)
class _PlacementRegistrationConfirmation:
    confirmation_id: str
    production_snapshot_sha256: str
    audio_snapshot_sha256: str
    placement: PlacementReview
    candidate_asset_sha256: str
    consumed: bool = False


@dataclass(slots=True)
class _DurableDecisionConfirmation:
    confirmation_id: str
    production_snapshot_sha256: str
    audio_snapshot_sha256: str
    review_id: str
    decision: str
    consumed: bool = False


def _placement_hash(review: PlacementReview) -> str:
    return sha256_bytes(canonical_json_bytes(review.to_dict()))


class Task041AudioWorkspaceProjection:
    @staticmethod
    def build(*, workspace: AudioWorkspaceRegistry, production: ProductionControlRegistry) -> dict[str, Any]:
        placements = []
        for review in sorted(workspace.placements.values(), key=lambda item: item.review_id):
            candidate = production.candidates.get(review.candidate_id)
            if candidate is None:
                raise ProductError(
                    "ERR_AUDIO_WORKSPACE_CANDIDATE_NOT_FOUND",
                    "Audio Workspace placement references a missing Production Candidate",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"review_id": review.review_id},
                )
            available = []
            if review.decision is PlacementDecision.REVIEW:
                if candidate.lifecycle_state is CandidateLifecycle.LOCKED:
                    available.append(PlacementDecision.ACCEPT.value)
                available += [PlacementDecision.REJECT.value, PlacementDecision.ALTERNATE_USE.value]
            placements.append({
                **review.to_dict(),
                "candidate_asset_id": candidate.asset_id,
                "candidate_asset_sha256": candidate.asset_sha256,
                "candidate_lifecycle_state": candidate.lifecycle_state.value,
                "available_human_actions": available,
                "task026_compile_started": False,
                "resolve_mutation_started": False,
            })
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "task_owner": "TASK-041",
            "placements": placements,
            "candidate_decisions": [workspace.decisions[key].to_dict() for key in sorted(workspace.decisions)],
            "derived_assets": [workspace.derived_assets[key].to_dict() for key in sorted(workspace.derived_assets)],
            "destructive_source_write_authority": False,
            "task026_compile_started": False,
            "resolve_mutation_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class Task041AudioWorkspaceService:
    def __init__(
        self,
        *,
        workspace: AudioWorkspaceRegistry,
        production: ProductionControlRegistry,
        token_factory: TokenFactory | None = None,
    ) -> None:
        self.workspace = workspace
        self.production = production
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _PlacementConfirmation] = {}

    def snapshot(self) -> dict[str, Any]:
        return Task041AudioWorkspaceProjection.build(workspace=self.workspace, production=self.production)

    def prepare_placement_decision(self, *, review_id: str, decision: str) -> dict[str, Any]:
        try:
            decision_kind = PlacementDecision(decision)
        except ValueError as exc:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_PLACEMENT_DECISION_INVALID",
                "Unknown Audio placement decision",
                ProductErrorCategory.VALIDATION,
            ) from exc
        if decision_kind is PlacementDecision.REVIEW:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_PLACEMENT_DECISION_INVALID",
                "REVIEW is an initial state, not a Human final placement action",
                ProductErrorCategory.VALIDATION,
            )
        review = self.workspace.placements.get(review_id)
        if review is None:
            raise ProductError("ERR_AUDIO_PLACEMENT_NOT_FOUND", "review_id does not exist", ProductErrorCategory.STATE)
        if review.decision is not PlacementDecision.REVIEW:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_PLACEMENT_ALREADY_DECIDED",
                "Audio placement already has a Human decision",
                ProductErrorCategory.STATE,
            )
        candidate = self.production.candidates.get(review.candidate_id)
        if candidate is None:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CANDIDATE_NOT_FOUND",
                "Audio placement Candidate does not exist in Production Control",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if decision_kind is PlacementDecision.ACCEPT and candidate.lifecycle_state is not CandidateLifecycle.LOCKED:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_ACCEPT_REQUIRES_LOCKED_CANDIDATE",
                "Human ACCEPT placement requires a locked Production Candidate",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"lifecycle_state": candidate.lifecycle_state.value},
            )
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CONFIRMATION_TOKEN_INVALID",
                "Audio placement confirmation token factory returned an invalid token",
                ProductErrorCategory.INTERNAL,
            )
        confirmation = _PlacementConfirmation(
            confirmation_id=token,
            review_id=review_id,
            candidate_id=candidate.candidate_id,
            candidate_asset_sha256=candidate.asset_sha256,
            placement_sha256=_placement_hash(review),
            decision=decision_kind,
        )
        self._confirmations[token] = confirmation
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-041",
            "confirmation_id": token,
            "review_id": review_id,
            "candidate_id": candidate.candidate_id,
            "candidate_asset_sha256": candidate.asset_sha256,
            "placement_sha256": confirmation.placement_sha256,
            "decision": decision_kind.value,
            "gain_db": review.gain_db,
            "timeline_start_frame": review.timeline_start_frame,
            "duration_frames": review.duration_frames,
            "human_final_authority_required": True,
            "task026_compile_started": False,
            "resolve_mutation_started": False,
        }

    def apply_placement_decision(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CONFIRMATION_INVALID",
                "Audio placement confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        review = self.workspace.placements.get(pending.review_id)
        candidate = self.production.candidates.get(pending.candidate_id)
        if (
            review is None
            or candidate is None
            or review.candidate_id != pending.candidate_id
            or review.decision is not PlacementDecision.REVIEW
            or _placement_hash(review) != pending.placement_sha256
            or candidate.asset_sha256 != pending.candidate_asset_sha256
            or (pending.decision is PlacementDecision.ACCEPT and candidate.lifecycle_state is not CandidateLifecycle.LOCKED)
        ):
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CONFIRMATION_STALE",
                "Audio placement or Candidate changed after Human confirmation was prepared",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        updated = self.workspace.replace_placement_decision(pending.review_id, pending.decision)
        return {
            "placement": updated.to_dict(),
            "workspace": self.snapshot(),
            "task026_compile_started": False,
            "resolve_mutation_started": False,
        }


class Task041AudioWorkspaceApplication:
    """Durable project-scoped TASK-041 Product application."""

    _SNAPSHOT_NAME = "audio-workspace.json"
    _ROLE_BY_SLOT = {
        SlotKind.SE: "SE",
        SlotKind.BGM: "BGM",
        SlotKind.NARRATION: "NARRATION",
    }

    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        production_control: Task037ProductionControlApplication | None = None,
        token_factory: TokenFactory | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_PROJECT_ROOT_INVALID",
                "Audio Workspace project root must be an existing regular directory",
                ProductErrorCategory.VALIDATION,
            )
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_PROJECT_ID_INVALID",
                "Audio Workspace project_id must be non-empty text",
                ProductErrorCategory.VALIDATION,
            )
        if production_control is not None and (
            production_control.project_root != root or production_control.project_id != project_id
        ):
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_PRODUCTION_SCOPE_MISMATCH",
                "Audio Workspace and Production Control must use the same project root/id",
                ProductErrorCategory.SECURITY,
            )
        self.project_root = root
        self.project_id = project_id
        self.production_control = production_control or Task037ProductionControlApplication(
            project_root=root,
            project_id=project_id,
        )
        self.snapshot_path = root / self._SNAPSHOT_NAME
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._placement_confirmations: dict[str, _PlacementRegistrationConfirmation] = {}
        self._decision_confirmations: dict[str, _DurableDecisionConfirmation] = {}

    @staticmethod
    def _audio_hash(registry: AudioWorkspaceRegistry) -> str:
        return str(AudioWorkspaceSnapshotStore.snapshot(registry)["snapshot_sha256"])

    @staticmethod
    def _production_hash(registry: ProductionControlRegistry) -> str:
        return str(ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"])

    def _load_audio(self) -> tuple[AudioWorkspaceRegistry, str, bool]:
        if self.snapshot_path.is_symlink():
            raise ProductError(
                "ERR_AUDIO_SNAPSHOT_FILE_INVALID",
                "Audio Workspace snapshot cannot be a symlink",
                ProductErrorCategory.SECURITY,
            )
        if self.snapshot_path.exists():
            registry = AudioWorkspaceSnapshotStore.load(self.snapshot_path)
            return registry, self._audio_hash(registry), True
        registry = AudioWorkspaceRegistry()
        return registry, self._audio_hash(registry), False

    def _load_production(self) -> tuple[ProductionControlRegistry, str, bool]:
        target = self.production_control.snapshot_path
        if target.is_symlink():
            raise ProductError(
                "ERR_PRODUCTION_SNAPSHOT_FILE_INVALID",
                "Production Control snapshot cannot be a symlink",
                ProductErrorCategory.SECURITY,
            )
        if target.exists():
            registry = ProductionControlSnapshotStore.load(target)
            foreign = sorted(
                slot.slot_id for slot in registry.slots.values() if slot.project_id != self.project_id
            )
            if foreign:
                raise ProductError(
                    "ERR_AUDIO_WORKSPACE_PROJECT_MISMATCH",
                    "Production Control contains foreign project Slots",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"foreign_slot_ids": foreign},
                )
            return registry, self._production_hash(registry), True
        registry = ProductionControlRegistry()
        return registry, self._production_hash(registry), False

    @staticmethod
    def _require_expected(actual: str, expected: str, kind: str) -> None:
        if not isinstance(expected, str) or expected != actual:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_SNAPSHOT_CONFLICT",
                f"{kind} snapshot changed; reload before applying the command",
                ProductErrorCategory.STATE,
                details={"snapshot_kind": kind, "current_snapshot_sha256": actual},
            )

    def _token(self) -> str:
        token = self._token_factory()
        if (
            not isinstance(token, str)
            or not token.strip()
            or token in self._placement_confirmations
            or token in self._decision_confirmations
        ):
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CONFIRMATION_TOKEN_INVALID",
                "Audio Workspace confirmation token is invalid",
                ProductErrorCategory.INTERNAL,
            )
        return token

    def _require_audio_candidate(
        self,
        production: ProductionControlRegistry,
        *,
        candidate_id: str,
        track_role: str,
    ) -> tuple[Any, Any]:
        candidate = production.candidates.get(candidate_id)
        if candidate is None:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CANDIDATE_NOT_FOUND",
                "Audio placement Candidate does not exist",
                ProductErrorCategory.STATE,
            )
        slot = production.slots.get(candidate.slot_id)
        if slot is None or slot.project_id != self.project_id:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CANDIDATE_SCOPE",
                "Audio placement Candidate is outside the current project",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        expected_role = self._ROLE_BY_SLOT.get(slot.slot_kind)
        if expected_role is None or track_role != expected_role:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_SLOT_ROLE",
                "Audio placement role does not match its Product Slot",
                ProductErrorCategory.VALIDATION,
                details={"slot_kind": slot.slot_kind.value},
            )
        if candidate.lifecycle_state not in {CandidateLifecycle.ACCEPTED, CandidateLifecycle.LOCKED}:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CANDIDATE_NOT_REVIEWABLE",
                "Audio placement requires an accepted or locked Candidate",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"lifecycle_state": candidate.lifecycle_state.value},
            )
        return candidate, slot

    def snapshot(self) -> dict[str, Any]:
        production, production_sha, production_persisted = self._load_production()
        audio, audio_sha, audio_persisted = self._load_audio()
        workspace = Task041AudioWorkspaceProjection.build(workspace=audio, production=production)
        referenced = {review.candidate_id for review in audio.placements.values()}
        candidates = []
        for candidate in sorted(production.candidates.values(), key=lambda item: item.candidate_id):
            slot = production.slots.get(candidate.slot_id)
            if (
                slot is None
                or slot.project_id != self.project_id
                or slot.slot_kind not in self._ROLE_BY_SLOT
                or candidate.lifecycle_state not in {CandidateLifecycle.ACCEPTED, CandidateLifecycle.LOCKED}
            ):
                continue
            candidates.append({
                "candidate_id": candidate.candidate_id,
                "asset_id": candidate.asset_id,
                "asset_sha256": candidate.asset_sha256,
                "slot_id": slot.slot_id,
                "scene_id": slot.scene_id,
                "track_role": self._ROLE_BY_SLOT[slot.slot_kind],
                "lifecycle_state": candidate.lifecycle_state.value,
                "placement_registered": candidate.candidate_id in referenced,
            })
        return {
            "application_version": "1.0.0",
            "task_owner": "TASK-041",
            "project_id": self.project_id,
            "production_snapshot_sha256": production_sha,
            "audio_snapshot_sha256": audio_sha,
            "production_persisted": production_persisted,
            "audio_persisted": audio_persisted,
            "available_audio_candidates": candidates,
            "workspace": workspace,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "derived_media_write_started": False,
            "task026_compile_started": False,
            "resolve_mutation_started": False,
            "cubase_mutation_started": False,
        }

    def prepare_placement(
        self,
        *,
        review_id: str,
        candidate_id: str,
        timeline_start_frame: int,
        duration_frames: int,
        track_role: str,
        gain_db: float | None,
        expected_production_snapshot_sha256: str,
        expected_audio_snapshot_sha256: str,
    ) -> dict[str, Any]:
        production, production_sha, _ = self._load_production()
        audio, audio_sha, _ = self._load_audio()
        self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
        self._require_expected(audio_sha, expected_audio_snapshot_sha256, "Audio")
        if review_id in audio.placements:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_CONFLICT",
                "review_id already exists",
                ProductErrorCategory.STATE,
            )
        placement = PlacementReview(
            review_id,
            candidate_id,
            timeline_start_frame,
            duration_frames,
            track_role,
            gain_db=gain_db,
        )
        candidate, _ = self._require_audio_candidate(
            production,
            candidate_id=candidate_id,
            track_role=track_role,
        )
        token = self._token()
        self._placement_confirmations[token] = _PlacementRegistrationConfirmation(
            token,
            production_sha,
            audio_sha,
            placement,
            candidate.asset_sha256,
        )
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-041",
            "confirmation_id": token,
            "placement": placement.to_dict(),
            "candidate_asset_sha256": candidate.asset_sha256,
            "human_confirmation_required": True,
            "task026_compile_started": False,
            "resolve_mutation_started": False,
        }

    def apply_placement(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._placement_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CONFIRMATION_INVALID",
                "Audio placement confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        with _exclusive_snapshot_lock(self.production_control.snapshot_path):
            with _exclusive_snapshot_lock(self.snapshot_path):
                production, production_sha, _ = self._load_production()
                audio, audio_sha, audio_persisted = self._load_audio()
                self._require_expected(production_sha, pending.production_snapshot_sha256, "Production")
                self._require_expected(audio_sha, pending.audio_snapshot_sha256, "Audio")
                candidate, _ = self._require_audio_candidate(
                    production,
                    candidate_id=pending.placement.candidate_id,
                    track_role=pending.placement.track_role,
                )
                if candidate.asset_sha256 != pending.candidate_asset_sha256:
                    raise ProductError(
                        "ERR_AUDIO_WORKSPACE_CONFIRMATION_STALE",
                        "Audio Candidate bytes changed after placement preparation",
                        ProductErrorCategory.AUTHORIZATION,
                    )
                audio.add_placement(pending.placement)
                AudioWorkspaceSnapshotStore.save(
                    self.snapshot_path,
                    audio,
                    expected_previous_snapshot_sha256=audio_sha if audio_persisted else None,
                )
        return self.snapshot()

    def prepare_placement_decision(
        self,
        *,
        review_id: str,
        decision: str,
        expected_production_snapshot_sha256: str,
        expected_audio_snapshot_sha256: str,
    ) -> dict[str, Any]:
        production, production_sha, _ = self._load_production()
        audio, audio_sha, _ = self._load_audio()
        self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
        self._require_expected(audio_sha, expected_audio_snapshot_sha256, "Audio")
        token = self._token()
        service = Task041AudioWorkspaceService(
            workspace=audio,
            production=production,
            token_factory=lambda: token,
        )
        prepared = service.prepare_placement_decision(review_id=review_id, decision=decision)
        self._decision_confirmations[token] = _DurableDecisionConfirmation(
            token,
            production_sha,
            audio_sha,
            review_id,
            decision,
        )
        return {
            **prepared,
            "project_id": self.project_id,
            "production_snapshot_sha256": production_sha,
            "audio_snapshot_sha256": audio_sha,
        }

    def apply_placement_decision(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._decision_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_AUDIO_WORKSPACE_CONFIRMATION_INVALID",
                "Audio decision confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        with _exclusive_snapshot_lock(self.production_control.snapshot_path):
            with _exclusive_snapshot_lock(self.snapshot_path):
                production, production_sha, _ = self._load_production()
                audio, audio_sha, audio_persisted = self._load_audio()
                self._require_expected(production_sha, pending.production_snapshot_sha256, "Production")
                self._require_expected(audio_sha, pending.audio_snapshot_sha256, "Audio")
                service = Task041AudioWorkspaceService(
                    workspace=audio,
                    production=production,
                    token_factory=lambda: confirmation_id,
                )
                service.prepare_placement_decision(
                    review_id=pending.review_id,
                    decision=pending.decision,
                )
                service.apply_placement_decision(confirmation_id=confirmation_id)
                AudioWorkspaceSnapshotStore.save(
                    self.snapshot_path,
                    audio,
                    expected_previous_snapshot_sha256=audio_sha if audio_persisted else None,
                )
        return self.snapshot()


__all__ = [
    "Task041AudioWorkspaceApplication",
    "Task041AudioWorkspaceProjection",
    "Task041AudioWorkspaceService",
]
