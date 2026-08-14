"""Project-scoped prepare/apply boundary for TASK-042 Timeline Audio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Any, Callable

from .errors import ProductError, ProductErrorCategory
from .product_project import ProductProjectManifest, ProjectChildBinding
from .product_project_store import ProductProjectManifestStore
from .project_save import ProductProjectSaveCoordinator
from .production_control import CandidateLifecycle, ProductionControlRegistry, SlotKind
from .serialization import sha256_bytes, utc_now_iso
from .timeline_audio import AudioFitPolicy, TimelineAudioPlan, TimelineAudioRole
from .timeline_audio_store import FORMAT_ID, FORMAT_VERSION, RELATIVE_PATH, TimelineAudioHistory, TimelineAudioSnapshotStore

TokenFactory = Callable[[], str]
_ROLE_SLOT = {TimelineAudioRole.SE: SlotKind.SE, TimelineAudioRole.BGM: SlotKind.BGM,
              TimelineAudioRole.NARRATION: SlotKind.NARRATION, TimelineAudioRole.AMBIENCE: SlotKind.AMBIENCE}


@dataclass(slots=True)
class _Confirmation:
    confirmation_id: str
    expected_manifest_sha256: str
    plan: TimelineAudioPlan
    consumed: bool = False


class Task042TimelineAudioApplication:
    """Commits Timeline history through the TASK-043 aggregate save coordinator."""

    def __init__(self, *, project_root: str | Path, project_id: str,
                 token_factory: TokenFactory | None = None) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.project_id = project_id
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_id != project_id:
            raise ProductError("ERR_TIMELINE_AUDIO_PROJECT_MISMATCH", "Project Manifest identity differs", ProductErrorCategory.SECURITY)
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._pending: dict[str, _Confirmation] = {}

    @property
    def snapshot_path(self) -> Path:
        return self.project_root / RELATIVE_PATH

    def _load(self, manifest: ProductProjectManifest) -> TimelineAudioHistory:
        binding = next((item for item in manifest.child_bindings if item.identity == ("TASK-042", RELATIVE_PATH)), None)
        if binding is None:
            if self.snapshot_path.exists():
                raise ProductError("ERR_TIMELINE_AUDIO_UNBOUND_CHILD", "Unbound Timeline child exists", ProductErrorCategory.SECURITY)
            return TimelineAudioHistory(self.project_id)
        if binding.format_id != FORMAT_ID or binding.format_version != FORMAT_VERSION:
            raise ProductError("ERR_TIMELINE_AUDIO_FORMAT_MISMATCH", "Timeline child binding format is unsupported", ProductErrorCategory.NOT_SUPPORTED)
        history = TimelineAudioSnapshotStore.load(self.snapshot_path, expected_project_id=self.project_id)
        if sha256_bytes(TimelineAudioSnapshotStore.serialize(history)) != binding.content_sha256:
            raise ProductError("ERR_TIMELINE_AUDIO_BINDING_CHECKSUM", "Timeline child differs from its Project binding", ProductErrorCategory.DATA_INTEGRITY)
        return history

    @staticmethod
    def _execution_gaps(plan: TimelineAudioPlan) -> list[dict[str, str]]:
        gaps = []
        for item in plan.items:
            if getattr(item, "fit_policy", None) is AudioFitPolicy.STRETCH:
                gaps.append({"item_id": item.item_id, "code": "TASK026_STRETCH_NOT_SUPPORTED"})
            if getattr(item, "fade_in_frames", 0) or getattr(item, "fade_out_frames", 0):
                gaps.append({"item_id": item.item_id, "code": "TASK010_FADE_EXECUTION_GAP"})
        return gaps

    def _validate_plan(self, plan: TimelineAudioPlan, production: ProductionControlRegistry,
                       manifest: ProductProjectManifest) -> None:
        if plan.project_id != self.project_id:
            raise ProductError("ERR_TIMELINE_AUDIO_PROJECT_MISMATCH", "Plan belongs to another project", ProductErrorCategory.SECURITY)
        if (plan.timeline_rate.numerator, plan.timeline_rate.denominator) != (manifest.timebase.numerator, manifest.timebase.denominator):
            raise ProductError("ERR_TIMELINE_AUDIO_TIMEBASE_MISMATCH", "Timeline rate differs from Product Project", ProductErrorCategory.DATA_INTEGRITY)
        if not any(binding.content_sha256 == plan.blueprint_sha256 for binding in manifest.child_bindings):
            raise ProductError("ERR_TIMELINE_AUDIO_BLUEPRINT_STALE", "Blueprint checksum is not bound by current Product Project", ProductErrorCategory.STATE)
        for item in plan.items:
            source = item.source
            if not source.candidate_bound:
                continue
            slot = production.slots.get(source.slot_id)
            candidate = production.candidates.get(source.candidate_id or "")
            if slot is None or slot.project_id != self.project_id or slot.slot_kind is not _ROLE_SLOT[item.role]:
                raise ProductError("ERR_TIMELINE_AUDIO_SLOT_ROLE", "Timeline role does not match its project Slot", ProductErrorCategory.DATA_INTEGRITY,
                                   details={"item_id": item.item_id})
            if candidate is None or candidate.slot_id != slot.slot_id or candidate.lifecycle_state is not CandidateLifecycle.LOCKED:
                raise ProductError("ERR_TIMELINE_AUDIO_CANDIDATE_NOT_LOCKED", "Bound Candidate must be locked in the same Slot", ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                                   details={"item_id": item.item_id})
            if candidate.asset_id != source.asset_id or candidate.asset_sha256 != source.asset_sha256:
                raise ProductError("ERR_TIMELINE_AUDIO_CANDIDATE_STALE", "Bound Candidate identity or bytes changed", ProductErrorCategory.STATE,
                                   details={"item_id": item.item_id})

    def snapshot(self) -> dict[str, Any]:
        manifest = ProductProjectManifestStore.load(self.project_root); history = self._load(manifest)
        current = history.current_plan
        return {"application_version": "1.0.0", "task_owner": "TASK-042/P-V6-4", "project_id": self.project_id,
                "project_manifest_sha256": manifest.project_manifest_sha256,
                "timeline_snapshot": TimelineAudioSnapshotStore.snapshot(history),
                "execution_gaps": [] if current is None else self._execution_gaps(current),
                "provider_execution_started": False, "external_mutation_started": False}

    def prepare_plan(self, *, plan: TimelineAudioPlan, production: ProductionControlRegistry,
                     expected_project_manifest_sha256: str) -> dict[str, Any]:
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_manifest_sha256 != expected_project_manifest_sha256:
            raise ProductError("ERR_TIMELINE_AUDIO_PROJECT_CONFLICT", "Product Project changed; reload first", ProductErrorCategory.STATE)
        self._validate_plan(plan, production, manifest)
        history = self._load(manifest); current = history.current_plan
        if current is not None and (plan.plan_id != current.plan_id or plan.revision != current.revision + 1 or plan.previous_plan_sha256 != current.plan_sha256):
            raise ProductError("ERR_TIMELINE_AUDIO_HISTORY_FORK", "Plan does not append to current history", ProductErrorCategory.STATE)
        token = self._token_factory()
        if not isinstance(token, str) or not token or token in self._pending:
            raise ProductError("ERR_TIMELINE_AUDIO_CONFIRMATION_INVALID", "Confirmation identity is invalid", ProductErrorCategory.INTERNAL)
        self._pending[token] = _Confirmation(token, manifest.project_manifest_sha256, plan)
        return {"confirmation_id": token, "plan": plan.to_dict(), "execution_gaps": self._execution_gaps(plan),
                "human_confirmation_required": True, "provider_execution_started": False, "external_mutation_started": False}

    def apply_plan(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._pending.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_TIMELINE_AUDIO_CONFIRMATION_INVALID", "Confirmation is missing or consumed", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        manifest = ProductProjectManifestStore.load(self.project_root)
        if manifest.project_manifest_sha256 != pending.expected_manifest_sha256:
            raise ProductError("ERR_TIMELINE_AUDIO_PROJECT_CONFLICT", "Product Project changed after preparation", ProductErrorCategory.STATE)
        history = self._load(manifest); history.add_plan(pending.plan); data = TimelineAudioSnapshotStore.serialize(history)
        binding = ProjectChildBinding("TASK-042", RELATIVE_PATH, FORMAT_ID, FORMAT_VERSION, sha256_bytes(data), True,
                                      tuple(sorted({pending.plan.blueprint_sha256})))
        bindings = [item for item in manifest.child_bindings if item.identity != binding.identity] + [binding]
        target = ProductProjectManifest.create(project_id=manifest.project_id,
            project_revision=manifest.project_revision + 1, product_version=manifest.product_version,
            timebase=manifest.timebase, child_bindings=bindings, created_at=manifest.created_at,
            updated_at=max(manifest.updated_at, utc_now_iso()))
        ProductProjectSaveCoordinator().save(self.project_root, target, {RELATIVE_PATH: data},
            expected_previous_manifest_sha256=manifest.project_manifest_sha256)
        return self.snapshot()


__all__ = ["Task042TimelineAudioApplication"]
