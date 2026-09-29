"""Project-scoped prepare/apply boundary for TASK-026 placement history."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
import secrets
from typing import Any, Callable

from .audio_placement import BedMode
from .audio_placement_store import (
    AudioPlacementCompilationRecord,
    AudioPlacementHistory,
    AudioPlacementHistoryStore,
    FORMAT_ID,
    FORMAT_VERSION,
    RELATIVE_PATH,
)
from .audio_workspace import AudioWorkspaceRegistry, PlacementDecision, PlacementReview
from .audio_workspace_placement_binding import AudioWorkspacePlacementBinding
from .audio_workspace_store import AudioWorkspaceSnapshotStore
from .errors import ProductError, ProductErrorCategory
from .product_project import ProductProjectManifest, ProjectChildBinding
from .product_project_store import ProductProjectManifestStore
from .production_control import CandidateLifecycle, ProductionControlRegistry
from .production_control_application import Task037ProductionControlApplication
from .production_control_store import ProductionControlSnapshotStore
from .project_save import ProductProjectSaveCoordinator
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso, validate_sha256
from .task102_project_writer_migration import (
    DEFAULT_PMST_WRITER_MIGRATION_ROUTER,
    PmstWriterMigrationRouter,
)
from .timeline_audio_store import (
    FORMAT_ID as TIMELINE_FORMAT_ID,
    FORMAT_VERSION as TIMELINE_FORMAT_VERSION,
    RELATIVE_PATH as TIMELINE_RELATIVE_PATH,
    TimelineAudioHistory,
    TimelineAudioSnapshotStore,
)


TokenFactory = Callable[[], str]
_PROJECTION_LIMIT = 500
_COMPILATION_ID_RE = re.compile(r"audio-placement-[0-9a-f]{24}")
_OWNER_CURRENT_READ_SEAL = object()


class AudioPlacementCurrentState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True, slots=True)
class AudioPlacementCurrentRead:
    state: AudioPlacementCurrentState
    project_id: str
    compilation_id: str
    record: AudioPlacementCompilationRecord | None
    record_sha256: str | None
    project_manifest_sha256: str
    production_snapshot_sha256: str
    audio_snapshot_sha256: str
    timeline_snapshot_sha256: str
    history_snapshot_sha256: str
    reason_codes: tuple[str, ...]
    owner_application_read: bool
    owner_record_origin_authenticated: bool
    currentness_verified: bool
    _issuer_seal: object = field(repr=False, compare=False)
    provider_execution_started: bool = False
    paid_execution_authorized: bool = False
    media_write_started: bool = False
    task010_execution_started: bool = False
    resolve_mutation_started: bool = False
    cubase_mutation_started: bool = False

    def __post_init__(self) -> None:
        if self._issuer_seal is not _OWNER_CURRENT_READ_SEAL:
            raise ValueError("current placement read must be issued by the TASK-026 owner application")
        if any((
            self.provider_execution_started,
            self.paid_execution_authorized,
            self.media_write_started,
            self.task010_execution_started,
            self.resolve_mutation_started,
            self.cubase_mutation_started,
        )):
            raise ValueError("current placement read cannot carry effect authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "project_id": self.project_id,
            "compilation_id": self.compilation_id,
            "record_sha256": self.record_sha256,
            "project_manifest_sha256": self.project_manifest_sha256,
            "production_snapshot_sha256": self.production_snapshot_sha256,
            "audio_snapshot_sha256": self.audio_snapshot_sha256,
            "timeline_snapshot_sha256": self.timeline_snapshot_sha256,
            "history_snapshot_sha256": self.history_snapshot_sha256,
            "review_id": None if self.record is None else self.record.review_id,
            "candidate_id": None if self.record is None else self.record.candidate_id,
            "asset_id": None if self.record is None else self.record.asset_id,
            "track_index": None if self.record is None else self.record.track_index,
            "bed_mode": None if self.record is None else self.record.bed_mode.value,
            "task026_plan_sha256": None if self.record is None else self.record.to_dict()["task026_plan_sha256"],
            "reason_codes": list(self.reason_codes),
            "owner_application_read": self.owner_application_read,
            "owner_record_origin_authenticated": self.owner_record_origin_authenticated,
            "currentness_verified": self.currentness_verified,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "media_write_started": False,
            "task010_execution_started": False,
            "resolve_mutation_started": False,
            "cubase_mutation_started": False,
        }


@dataclass(slots=True)
class _CompilationConfirmation:
    confirmation_id: str
    expected_project_manifest_sha256: str
    expected_production_snapshot_sha256: str
    expected_audio_snapshot_sha256: str
    expected_timeline_snapshot_sha256: str
    expected_history_snapshot_sha256: str
    review_id: str
    track_index: int
    bed_mode: BedMode
    record: AudioPlacementCompilationRecord
    consumed: bool = False


@dataclass(frozen=True, slots=True)
class _LoadedState:
    manifest: ProductProjectManifest
    production: ProductionControlRegistry
    production_sha256: str
    audio: AudioWorkspaceRegistry
    audio_sha256: str
    timeline: TimelineAudioHistory
    timeline_sha256: str
    history: AudioPlacementHistory
    history_sha256: str
    recovery: dict[str, object]


class Task026AudioPlacementApplication:
    """Persist deterministic plans without Provider, media or NLE authority."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        production_control: Task037ProductionControlApplication | None = None,
        token_factory: TokenFactory | None = None,
        save_coordinator: ProductProjectSaveCoordinator | None = None,
        pmst_router: PmstWriterMigrationRouter | None = None,
    ) -> None:
        supplied = Path(project_root)
        if supplied.is_symlink() or not supplied.is_dir():
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_PROJECT_ROOT_INVALID",
                "TASK-026 project root must be an existing regular directory",
                ProductErrorCategory.VALIDATION,
            )
        root = supplied.resolve(strict=True)
        manifest = ProductProjectManifestStore.load(root)
        if manifest.project_id != project_id:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_PROJECT_MISMATCH",
                "TASK-026 Project Manifest identity differs",
                ProductErrorCategory.SECURITY,
            )
        if production_control is not None and (
            production_control.project_root.resolve(strict=True) != root
            or production_control.project_id != project_id
        ):
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_PRODUCTION_SCOPE_MISMATCH",
                "TASK-026 and Production Control must use the same Project scope",
                ProductErrorCategory.SECURITY,
            )
        self.project_root = root
        self.project_id = project_id
        self.production_control = production_control or Task037ProductionControlApplication(
            project_root=root, project_id=project_id
        )
        self.audio_path = root / "audio-workspace.json"
        self.timeline_path = root / TIMELINE_RELATIVE_PATH
        self.history_path = root / RELATIVE_PATH
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        if save_coordinator is not None:
            if pmst_router is not None and save_coordinator.pmst_router is not pmst_router:
                raise ProductError(
                    "ERR_PMST_ROUTER_COMPOSITION_MISMATCH",
                    "TASK-026 save coordinator and PMST router must share one boundary",
                    ProductErrorCategory.SECURITY,
                )
            self._pmst_router = save_coordinator.pmst_router
            self._save_coordinator = save_coordinator
        else:
            self._pmst_router = pmst_router or DEFAULT_PMST_WRITER_MIGRATION_ROUTER
            self._save_coordinator = ProductProjectSaveCoordinator(pmst_router=self._pmst_router)
        self._pending: dict[str, _CompilationConfirmation] = {}

    @staticmethod
    def _binding(
        manifest: ProductProjectManifest, owner: str, relative_path: str
    ) -> ProjectChildBinding | None:
        return next(
            (item for item in manifest.child_bindings if item.identity == (owner, relative_path)),
            None,
        )

    def _load_production(self) -> tuple[ProductionControlRegistry, str]:
        path = self.production_control.snapshot_path
        if path.is_symlink():
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_PRODUCTION_FILE_INVALID",
                "Production Control snapshot cannot be a symlink",
                ProductErrorCategory.SECURITY,
            )
        registry = ProductionControlSnapshotStore.load(path) if path.exists() else ProductionControlRegistry()
        foreign = sorted(
            slot.slot_id for slot in registry.slots.values() if slot.project_id != self.project_id
        )
        if foreign:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_PROJECT_MISMATCH",
                "Production Control contains foreign Project Slots",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"foreign_slot_ids": foreign},
            )
        return registry, str(ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"])

    def _load_audio(self) -> tuple[AudioWorkspaceRegistry, str]:
        if self.audio_path.is_symlink():
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_AUDIO_FILE_INVALID",
                "Audio Workspace snapshot cannot be a symlink",
                ProductErrorCategory.SECURITY,
            )
        registry = AudioWorkspaceSnapshotStore.load(self.audio_path) if self.audio_path.exists() else AudioWorkspaceRegistry()
        return registry, str(AudioWorkspaceSnapshotStore.snapshot(registry)["snapshot_sha256"])

    def _load_timeline(self, manifest: ProductProjectManifest) -> tuple[TimelineAudioHistory, str]:
        binding = self._binding(manifest, "TASK-042", TIMELINE_RELATIVE_PATH)
        if binding is None:
            if self.timeline_path.exists():
                raise ProductError(
                    "ERR_AUDIO_PLACEMENT_TIMELINE_UNBOUND",
                    "Unbound TASK-042 Timeline child exists",
                    ProductErrorCategory.SECURITY,
                )
            history = TimelineAudioHistory(self.project_id)
        else:
            if binding.format_id != TIMELINE_FORMAT_ID or binding.format_version != TIMELINE_FORMAT_VERSION:
                raise ProductError(
                    "ERR_AUDIO_PLACEMENT_TIMELINE_FORMAT",
                    "TASK-042 Timeline binding format is unsupported",
                    ProductErrorCategory.NOT_SUPPORTED,
                )
            history = TimelineAudioSnapshotStore.load(
                self.timeline_path, expected_project_id=self.project_id
            )
            if sha256_bytes(TimelineAudioSnapshotStore.serialize(history)) != binding.content_sha256:
                raise ProductError(
                    "ERR_AUDIO_PLACEMENT_TIMELINE_CHECKSUM",
                    "TASK-042 Timeline child differs from its Project binding",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        return history, str(TimelineAudioSnapshotStore.snapshot(history)["snapshot_sha256"])

    def _load_history(self, manifest: ProductProjectManifest) -> tuple[AudioPlacementHistory, str]:
        binding = self._binding(manifest, "TASK-026", RELATIVE_PATH)
        if binding is None:
            if self.history_path.exists():
                raise ProductError(
                    "ERR_AUDIO_PLACEMENT_HISTORY_UNBOUND",
                    "Unbound TASK-026 placement history exists",
                    ProductErrorCategory.SECURITY,
                )
            history = AudioPlacementHistory(self.project_id)
        else:
            if binding.format_id != FORMAT_ID or binding.format_version != FORMAT_VERSION:
                raise ProductError(
                    "ERR_AUDIO_PLACEMENT_HISTORY_FORMAT",
                    "TASK-026 history binding format is unsupported",
                    ProductErrorCategory.NOT_SUPPORTED,
                )
            history = AudioPlacementHistoryStore.load(
                self.history_path, expected_project_id=self.project_id
            )
            if sha256_bytes(AudioPlacementHistoryStore.serialize(history)) != binding.content_sha256:
                raise ProductError(
                    "ERR_AUDIO_PLACEMENT_HISTORY_BINDING_CHECKSUM",
                    "TASK-026 history differs from its Project binding",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        return history, str(AudioPlacementHistoryStore.snapshot(history)["snapshot_sha256"])

    def _load_state(self) -> _LoadedState:
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_id != self.project_id:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_PROJECT_MISMATCH",
                "Current Product Project identity differs",
                ProductErrorCategory.SECURITY,
            )
        production, production_sha = self._load_production()
        audio, audio_sha = self._load_audio()
        timeline, timeline_sha = self._load_timeline(manifest)
        history, history_sha = self._load_history(manifest)
        return _LoadedState(
            manifest, production, production_sha, audio, audio_sha,
            timeline, timeline_sha, history, history_sha,
            self._save_coordinator.recovery_status(self.project_root),
        )

    @staticmethod
    def _require_expected(actual: str, expected: str, kind: str) -> None:
        if not isinstance(expected, str) or actual != expected:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_SNAPSHOT_CONFLICT",
                f"{kind} changed; reload TASK-026 before continuing",
                ProductErrorCategory.STATE,
                details={"snapshot_kind": kind, "current_sha256": actual},
            )

    @staticmethod
    def _require_no_recovery(state: _LoadedState) -> None:
        if state.recovery.get("required") is True:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_PROJECT_RECOVERY_REQUIRED",
                "Complete or roll back the pending Product Project save before TASK-026",
                ProductErrorCategory.STATE,
                details={
                    "state": state.recovery.get("state"),
                    "transaction_id": state.recovery.get("transaction_id"),
                },
            )

    @staticmethod
    def _compile(
        state: _LoadedState, *, review_id: str, track_index: int, bed_mode: BedMode
    ):
        return AudioWorkspacePlacementBinding.compile_current_timeline_placement(
            review_id=review_id,
            workspace=state.audio,
            production=state.production,
            timeline=state.timeline,
            track_index=track_index,
            bed_mode=bed_mode,
        )

    @classmethod
    def _derive_record(
        cls,
        state: _LoadedState,
        *,
        review_id: str,
        track_index: int,
        bed_mode: BedMode,
    ) -> AudioPlacementCompilationRecord:
        plan = cls._compile(
            state, review_id=review_id, track_index=track_index, bed_mode=bed_mode
        )
        review = state.audio.placements[review_id]
        candidate = state.production.candidates[review.candidate_id]
        binding = review.timeline_binding
        current = state.timeline.current_plan
        if binding is None or current is None:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_TIMELINE_BINDING_REQUIRED",
                "Current TASK-042 Timeline proof is required",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        slot = state.production.slots.get(candidate.slot_id)
        if slot is None or slot.project_id != state.manifest.project_id:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_SLOT_SCOPE",
                "Audio Candidate Slot is outside the current Project",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        plan_sha = str(plan.to_dict()["plan_sha256"])
        identity = {
            "project_id": state.manifest.project_id,
            "review_id": review.review_id,
            "audio_snapshot_sha256": state.audio_sha256,
            "production_snapshot_sha256": state.production_sha256,
            "timeline_snapshot_sha256": state.timeline_sha256,
            "slot_id": slot.slot_id,
            "candidate_id": candidate.candidate_id,
            "asset_id": candidate.asset_id,
            "asset_sha256": candidate.asset_sha256,
            "timeline_plan_id": binding.plan_id,
            "timeline_revision": binding.plan_revision,
            "timeline_plan_sha256": binding.plan_sha256,
            "timeline_item_id": binding.item_id,
            "timeline_item_sha256": binding.item_sha256,
            "track_index": track_index,
            "bed_mode": bed_mode.value,
            "task026_plan_sha256": plan_sha,
        }
        record = AudioPlacementCompilationRecord(
            compilation_id=AudioPlacementCompilationRecord.derive_compilation_id(identity),
            project_id=state.manifest.project_id,
            source_project_revision=state.manifest.project_revision,
            source_project_manifest_sha256=state.manifest.project_manifest_sha256,
            review_id=review.review_id,
            placement_decision=PlacementDecision.ACCEPT.value,
            audio_snapshot_sha256=state.audio_sha256,
            production_snapshot_sha256=state.production_sha256,
            timeline_snapshot_sha256=state.timeline_sha256,
            slot_id=slot.slot_id,
            candidate_id=candidate.candidate_id,
            asset_id=candidate.asset_id,
            asset_sha256=candidate.asset_sha256,
            timeline_plan_id=binding.plan_id,
            timeline_revision=binding.plan_revision,
            timeline_plan_sha256=binding.plan_sha256,
            timeline_item_id=binding.item_id,
            timeline_item_sha256=binding.item_sha256,
            track_index=track_index,
            bed_mode=bed_mode,
            plan=plan,
        )
        existing = state.history.records.get(record.compilation_id)
        if existing is not None:
            if existing.identity_body() != record.identity_body():
                raise ProductError(
                    "ERR_AUDIO_PLACEMENT_IDENTITY_COLLISION",
                    "Existing TASK-026 identity has conflicting content",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            return existing
        return record

    @classmethod
    def _record_reasons(
        cls, record: AudioPlacementCompilationRecord, state: _LoadedState
    ) -> tuple[str, ...]:
        reasons: set[str] = set()
        if record.production_snapshot_sha256 != state.production_sha256:
            reasons.add("PRODUCTION_SNAPSHOT_CHANGED")
        if record.audio_snapshot_sha256 != state.audio_sha256:
            reasons.add("AUDIO_SNAPSHOT_CHANGED")
        if record.timeline_snapshot_sha256 != state.timeline_sha256:
            reasons.add("TIMELINE_SNAPSHOT_CHANGED")
        review = state.audio.placements.get(record.review_id)
        if review is None:
            reasons.add("REVIEW_MISSING")
        elif review.decision is not PlacementDecision.ACCEPT:
            reasons.add("HUMAN_ACCEPT_REVOKED")
        elif review.candidate_id != record.candidate_id:
            reasons.add("REVIEW_CANDIDATE_CHANGED")
        candidate = state.production.candidates.get(record.candidate_id)
        if candidate is None:
            reasons.add("CANDIDATE_MISSING")
        else:
            if candidate.slot_id != record.slot_id:
                reasons.add("CANDIDATE_SLOT_CHANGED")
            if candidate.lifecycle_state is not CandidateLifecycle.LOCKED:
                reasons.add("CANDIDATE_NOT_LOCKED")
            if candidate.asset_id != record.asset_id or candidate.asset_sha256 != record.asset_sha256:
                reasons.add("CANDIDATE_ASSET_CHANGED")
        current = state.timeline.current_plan
        if current is None:
            reasons.add("TIMELINE_MISSING")
        elif (
            current.plan_id != record.timeline_plan_id
            or current.revision != record.timeline_revision
            or current.plan_sha256 != record.timeline_plan_sha256
        ):
            reasons.add("TIMELINE_REVISION_CHANGED")
        else:
            try:
                item = current.item(record.timeline_item_id)
            except StopIteration:
                reasons.add("TIMELINE_ITEM_MISSING")
            else:
                if item.to_dict()["item_sha256"] != record.timeline_item_sha256:
                    reasons.add("TIMELINE_ITEM_CHANGED")
        if not reasons:
            try:
                derived = cls._compile(
                    state,
                    review_id=record.review_id,
                    track_index=record.track_index,
                    bed_mode=record.bed_mode,
                )
            except ProductError as exc:
                reasons.add(exc.code)
            else:
                if derived.to_dict() != record.plan.to_dict():
                    reasons.add("TASK026_PLAN_CHANGED")
        return tuple(sorted(reasons))

    @classmethod
    def _review_row(cls, review: PlacementReview, state: _LoadedState) -> dict[str, Any]:
        blockers: set[str] = set()
        if review.decision is not PlacementDecision.ACCEPT:
            blockers.add("HUMAN_ACCEPT_REQUIRED")
        try:
            cls._compile(state, review_id=review.review_id, track_index=1, bed_mode=BedMode.FULL)
        except ProductError as exc:
            blockers.add(exc.code)
        current_ids = []
        for record in state.history.records.values():
            if record.review_id == review.review_id and not cls._record_reasons(record, state):
                current_ids.append(record.compilation_id)
        return {
            "review_id": review.review_id,
            "candidate_id": review.candidate_id,
            "decision": review.decision.value,
            "track_role": review.track_role,
            "timeline_start_frame": review.timeline_start_frame,
            "duration_frames": review.duration_frames,
            "runnable": not blockers and state.recovery.get("required") is not True,
            "blocker_codes": sorted(blockers),
            "current_compilation_ids": sorted(current_ids),
            "available_bed_modes": [BedMode.PREVIEW.value, BedMode.FULL.value],
            "external_execution_authorized": False,
        }

    def snapshot(self) -> dict[str, Any]:
        state = self._load_state()
        records = []
        ordered = sorted(
            state.history.records.values(), key=lambda item: item.compilation_id
        )
        for record in ordered[:_PROJECTION_LIMIT]:
            reasons = self._record_reasons(record, state)
            records.append({
                "compilation_id": record.compilation_id,
                "review_id": record.review_id,
                "candidate_id": record.candidate_id,
                "asset_id": record.asset_id,
                "track_index": record.track_index,
                "bed_mode": record.bed_mode.value,
                "task026_plan_sha256": record.to_dict()["task026_plan_sha256"],
                "task010_structurally_compatible": record.plan.task010_compatible,
                "currentness": "CURRENT" if not reasons else "STALE",
                "reason_codes": list(reasons),
                "external_execution_authorized": False,
            })
        reviews = [
            self._review_row(state.audio.placements[key], state)
            for key in sorted(state.audio.placements)
        ]
        return {
            "application_version": FORMAT_VERSION,
            "task_owner": "TASK-026",
            "project_id": self.project_id,
            "project_revision": state.manifest.project_revision,
            "project_manifest_sha256": state.manifest.project_manifest_sha256,
            "production_snapshot_sha256": state.production_sha256,
            "audio_snapshot_sha256": state.audio_sha256,
            "timeline_snapshot_sha256": state.timeline_sha256,
            "history_snapshot_sha256": state.history_sha256,
            "project_recovery": state.recovery,
            "reviews": reviews,
            "records": records,
            "record_count": len(ordered),
            "records_truncated": len(ordered) > _PROJECTION_LIMIT,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "media_write_started": False,
            "task010_execution_started": False,
            "resolve_mutation_started": False,
            "cubase_mutation_started": False,
        }

    def read_current_compilation(
        self,
        *,
        compilation_id: str,
        expected_record_sha256: str,
    ) -> AudioPlacementCurrentRead:
        """Read one owner-persisted compilation and revalidate it against current Project state."""
        if not isinstance(compilation_id, str) or not _COMPILATION_ID_RE.fullmatch(compilation_id):
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_COMPILATION_ID_INVALID",
                "TASK-026 compilation_id is invalid",
                ProductErrorCategory.VALIDATION,
            )
        try:
            validate_sha256(expected_record_sha256, field_name="expected_record_sha256")
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_RECORD_SHA_INVALID",
                "TASK-026 expected record checksum is invalid",
                ProductErrorCategory.VALIDATION,
            ) from exc

        state = self._load_state()
        record = state.history.records.get(compilation_id)
        common = {
            "project_id": self.project_id,
            "compilation_id": compilation_id,
            "project_manifest_sha256": state.manifest.project_manifest_sha256,
            "production_snapshot_sha256": state.production_sha256,
            "audio_snapshot_sha256": state.audio_sha256,
            "timeline_snapshot_sha256": state.timeline_sha256,
            "history_snapshot_sha256": state.history_sha256,
            "owner_application_read": True,
            "_issuer_seal": _OWNER_CURRENT_READ_SEAL,
        }
        if record is None:
            reasons = {"COMPILATION_NOT_FOUND"}
            if state.recovery.get("required") is True:
                reasons.add("PROJECT_RECOVERY_REQUIRED")
            return AudioPlacementCurrentRead(
                state=AudioPlacementCurrentState.NOT_FOUND,
                record=None,
                record_sha256=None,
                reason_codes=tuple(sorted(reasons)),
                owner_record_origin_authenticated=False,
                currentness_verified=False,
                **common,
            )

        record_sha256 = sha256_bytes(canonical_json_bytes(record.to_dict()))
        reasons = set(self._record_reasons(record, state))
        if state.recovery.get("required") is True:
            reasons.add("PROJECT_RECOVERY_REQUIRED")
        if record_sha256 != expected_record_sha256:
            reasons.add("COMPILATION_RECORD_CHANGED")
        current = not reasons
        return AudioPlacementCurrentRead(
            state=(
                AudioPlacementCurrentState.CURRENT
                if current else AudioPlacementCurrentState.STALE
            ),
            record=record,
            record_sha256=record_sha256,
            reason_codes=tuple(sorted(reasons)),
            owner_record_origin_authenticated=True,
            currentness_verified=current,
            **common,
        )

    def prepare_compilation(
        self,
        *,
        review_id: str,
        track_index: int,
        bed_mode: str,
        expected_project_manifest_sha256: str,
        expected_production_snapshot_sha256: str,
        expected_audio_snapshot_sha256: str,
        expected_timeline_snapshot_sha256: str,
        expected_history_snapshot_sha256: str,
    ) -> dict[str, Any]:
        if isinstance(track_index, bool) or not isinstance(track_index, int) or not 1 <= track_index <= 999:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_TRACK_INVALID",
                "TASK-026 track_index must be an integer from 1 through 999",
                ProductErrorCategory.VALIDATION,
            )
        try:
            mode = BedMode(bed_mode)
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_BED_MODE_INVALID",
                "TASK-026 bed_mode must be PREVIEW or FULL",
                ProductErrorCategory.VALIDATION,
            ) from exc
        state = self._load_state()
        self._require_no_recovery(state)
        self._require_expected(
            state.manifest.project_manifest_sha256,
            expected_project_manifest_sha256,
            "Product Project",
        )
        self._require_expected(state.production_sha256, expected_production_snapshot_sha256, "Production")
        self._require_expected(state.audio_sha256, expected_audio_snapshot_sha256, "Audio")
        self._require_expected(state.timeline_sha256, expected_timeline_snapshot_sha256, "Timeline")
        self._require_expected(state.history_sha256, expected_history_snapshot_sha256, "TASK-026 history")
        record = self._derive_record(
            state, review_id=review_id, track_index=track_index, bed_mode=mode
        )
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._pending:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_CONFIRMATION_INVALID",
                "TASK-026 confirmation identity is invalid",
                ProductErrorCategory.INTERNAL,
            )
        self._pending[token] = _CompilationConfirmation(
            token,
            state.manifest.project_manifest_sha256,
            state.production_sha256,
            state.audio_sha256,
            state.timeline_sha256,
            state.history_sha256,
            review_id,
            track_index,
            mode,
            record,
        )
        plan = record.plan.to_dict()
        return {
            "confirmation_version": FORMAT_VERSION,
            "task_owner": "TASK-026",
            "confirmation_id": token,
            "compilation_id": record.compilation_id,
            "review_id": record.review_id,
            "candidate_id": record.candidate_id,
            "asset_id": record.asset_id,
            "timeline_item_id": record.timeline_item_id,
            "track_index": record.track_index,
            "bed_mode": record.bed_mode.value,
            "frame_range": {
                "start": plan["effective_start_frame"],
                "duration": plan["desired_duration_frames"],
            },
            "loop": plan["loop"],
            "fade_in_frames": plan["fade_in_frames"],
            "fade_out_frames": plan["fade_out_frames"],
            "gain_db": plan["gain_db"],
            "task026_plan_sha256": plan["plan_sha256"],
            "task010_structurally_compatible": record.plan.task010_compatible,
            "explicit_confirmation_required": True,
            "estimated_cost": 0,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "media_write_started": False,
            "task010_execution_started": False,
            "resolve_mutation_started": False,
            "cubase_mutation_started": False,
        }

    def apply_compilation(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._pending.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_CONFIRMATION_INVALID",
                "TASK-026 confirmation is missing or already consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        self._pmst_router.require_legacy_access(
            self.project_root,
            route_id="PMST-R012",
            access_kind="MUTATION",
        )
        pending.consumed = True
        state = self._load_state()
        self._require_no_recovery(state)
        self._require_expected(
            state.manifest.project_manifest_sha256,
            pending.expected_project_manifest_sha256,
            "Product Project",
        )
        self._require_expected(state.production_sha256, pending.expected_production_snapshot_sha256, "Production")
        self._require_expected(state.audio_sha256, pending.expected_audio_snapshot_sha256, "Audio")
        self._require_expected(state.timeline_sha256, pending.expected_timeline_snapshot_sha256, "Timeline")
        self._require_expected(state.history_sha256, pending.expected_history_snapshot_sha256, "TASK-026 history")
        current = self._derive_record(
            state,
            review_id=pending.review_id,
            track_index=pending.track_index,
            bed_mode=pending.bed_mode,
        )
        if current != pending.record:
            raise ProductError(
                "ERR_AUDIO_PLACEMENT_CONFIRMATION_STALE",
                "TASK-026 derivation changed after confirmation",
                ProductErrorCategory.AUTHORIZATION,
            )
        appended = state.history.append(current)
        if appended:
            data = AudioPlacementHistoryStore.serialize(state.history)
            binding = ProjectChildBinding(
                "TASK-026",
                RELATIVE_PATH,
                FORMAT_ID,
                FORMAT_VERSION,
                sha256_bytes(data),
                False,
                tuple(sorted({
                    state.production_sha256,
                    state.audio_sha256,
                    state.timeline_sha256,
                })),
            )
            bindings = [
                item for item in state.manifest.child_bindings if item.identity != binding.identity
            ] + [binding]
            target = ProductProjectManifest.create(
                project_id=state.manifest.project_id,
                project_revision=state.manifest.project_revision + 1,
                product_version=state.manifest.product_version,
                timebase=state.manifest.timebase,
                child_bindings=bindings,
                created_at=state.manifest.created_at,
                updated_at=max(state.manifest.updated_at, utc_now_iso()),
            )
            self._save_coordinator.save(
                self.project_root,
                target,
                {RELATIVE_PATH: data},
                expected_previous_manifest_sha256=state.manifest.project_manifest_sha256,
            )
        return {
            "apply_result": {
                "compilation_id": current.compilation_id,
                "appended": appended,
                "idempotent": not appended,
                "external_execution_started": False,
            },
            "snapshot": self.snapshot(),
        }


__all__ = [
    "AudioPlacementCurrentRead", "AudioPlacementCurrentState",
    "Task026AudioPlacementApplication",
]
