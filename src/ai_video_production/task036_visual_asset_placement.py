"""P-UX-2H placement-only composition for already locked generated IMAGE Assets.

The service consumes TASK-003/TASK-037 truth and delegates the only durable
Timeline mutation to TASK-044.  It never approves rights, accepts/locks a
Candidate, dispatches a Provider, or authorizes publication.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from typing import Any, ContextManager

from .assets import (
    AssetRecord,
    AssetType,
    AudioRightsStatus,
    PermissionState,
    RetentionClass,
    RightsStatus,
)
from .errors import ProductError, ProductErrorCategory
from .interactive_timeline import (
    InteractiveTimeline,
    InteractiveTimelineClip,
    TimelineMediaKind,
    TimelineTrack,
    TimelineTrackRole,
)
from .interactive_timeline_application import Task044TimelineEditApplication
from .interactive_timeline_edit import (
    TimelineEditCommand,
    TimelineEditKind,
    TimelineSourceBinding,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


ProductionSnapshotProvider = Callable[[], Mapping[str, object]]
ProductionGuardFactory = Callable[[str], ContextManager[Mapping[str, object]]]
AssetProvider = Callable[[str], AssetRecord]

_MAX_SLOTS = 256
_MAX_CANDIDATES = 1024
_PROVENANCE_FIELDS = {
    "kind", "execution_id", "queue_entry_id", "prompt_id", "prompt_version",
    "prompt_sha256", "provider_id", "model_id", "provider_operation_id",
    "output_sha256", "provider_execution_replayed", "paid_execution_authorized",
}
_RESTRICTIONS = (
    "HUMAN_RIGHTS_REVIEW_REQUIRED",
    "PUBLICATION_NOT_AUTHORIZED",
)


@dataclass(frozen=True, slots=True)
class _EligibleSource:
    snapshot_sha256: str
    slot: Mapping[str, object]
    candidate: Mapping[str, object]
    asset: AssetRecord
    binding: TimelineSourceBinding


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ProductError(
            "ERR_VISUAL_PLACEMENT_SOURCE_INVALID",
            f"{name} must be a mapping",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    return value


def _rows(value: object, name: str, maximum: int) -> Sequence[object]:
    if not isinstance(value, (list, tuple)) or len(value) > maximum:
        raise ProductError(
            "ERR_VISUAL_PLACEMENT_SOURCE_INVALID",
            f"{name} must be a bounded sequence",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 240 or "\x00" in value:
        raise ProductError(
            "ERR_VISUAL_PLACEMENT_SOURCE_INVALID",
            f"{name} is invalid",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    return value


class Task036VisualAssetPlacementApplication:
    """Compile and guard exact TASK-044 placement commands."""

    def __init__(
        self,
        *,
        project_id: str,
        product_job_id: str,
        production_snapshot_provider: ProductionSnapshotProvider,
        production_guard_factory: ProductionGuardFactory,
        asset_provider: AssetProvider,
        timeline_application: Task044TimelineEditApplication,
    ) -> None:
        self.project_id = _text(project_id, "project_id")
        self.product_job_id = _text(product_job_id, "product_job_id")
        self._production_snapshot_provider = production_snapshot_provider
        self._production_guard_factory = production_guard_factory
        self._asset_provider = asset_provider
        self._timeline_application = timeline_application

    def _production(self, source: Mapping[str, object] | None = None) -> tuple[Mapping[str, object], str]:
        snapshot = _mapping(
            self._production_snapshot_provider() if source is None else source,
            "production snapshot",
        )
        if snapshot.get("available", True) is not True:
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_PRODUCTION_UNAVAILABLE",
                "Production Control is unavailable",
                ProductErrorCategory.STATE,
            )
        if _text(snapshot.get("project_id"), "production project_id") != self.project_id:
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_PROJECT_MISMATCH",
                "Production Control belongs to another Project",
                ProductErrorCategory.SECURITY,
            )
        snapshot_sha = _text(snapshot.get("snapshot_sha256"), "production snapshot SHA")
        try:
            validate_sha256(snapshot_sha, field_name="production snapshot SHA")
        except ValueError as exc:
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_SOURCE_INVALID",
                "Production snapshot checksum is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return snapshot, snapshot_sha

    @staticmethod
    def _slots(snapshot: Mapping[str, object]) -> Sequence[object]:
        slots = snapshot.get("slots")
        if slots is None:
            slots = _mapping(snapshot.get("workspace", {}), "production workspace").get("slots", [])
        return _rows(slots, "production slots", _MAX_SLOTS)

    def _asset(self, asset_id: str) -> AssetRecord:
        asset = self._asset_provider(asset_id)
        if not isinstance(asset, AssetRecord):
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_ASSET_INVALID",
                "Asset provider returned an invalid record",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return asset

    def _eligible(
        self,
        candidate_id: str,
        *,
        source: Mapping[str, object] | None = None,
    ) -> _EligibleSource:
        snapshot, snapshot_sha = self._production(source)
        selected_slot: Mapping[str, object] | None = None
        selected_candidate: Mapping[str, object] | None = None
        seen_slots: set[str] = set()
        seen_candidates: set[str] = set()
        for raw_slot in self._slots(snapshot):
            slot = _mapping(raw_slot, "production slot")
            slot_id = _text(slot.get("slot_id"), "slot_id")
            if slot_id in seen_slots:
                raise ProductError(
                    "ERR_VISUAL_PLACEMENT_SOURCE_INVALID",
                    "Production snapshot has duplicate Slots",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            seen_slots.add(slot_id)
            if _text(slot.get("project_id"), "slot project_id") != self.project_id:
                raise ProductError(
                    "ERR_VISUAL_PLACEMENT_PROJECT_MISMATCH",
                    "Production Slot belongs to another Project",
                    ProductErrorCategory.SECURITY,
                )
            for raw_candidate in _rows(slot.get("candidates", []), "slot candidates", _MAX_CANDIDATES):
                candidate = _mapping(raw_candidate, "production candidate")
                row_id = _text(candidate.get("candidate_id"), "candidate_id")
                if row_id in seen_candidates:
                    raise ProductError(
                        "ERR_VISUAL_PLACEMENT_SOURCE_INVALID",
                        "Production snapshot has duplicate Candidates",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                seen_candidates.add(row_id)
                if row_id == candidate_id:
                    selected_slot, selected_candidate = slot, candidate
        if selected_slot is None or selected_candidate is None:
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_CANDIDATE_MISSING",
                "Locked visual Candidate is missing",
                ProductErrorCategory.STATE,
            )
        slot_id = _text(selected_slot.get("slot_id"), "slot_id")
        if (
            selected_slot.get("status") != "LOCKED"
            or selected_slot.get("stale_state") not in {None, "CURRENT"}
            or selected_slot.get("locked_candidate_id") != candidate_id
            or selected_candidate.get("slot_id") != slot_id
            or selected_candidate.get("lifecycle_state") != "LOCKED"
        ):
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_SOURCE_NOT_LOCKED",
                "Visual source is not the current locked Candidate",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        asset_id = _text(selected_candidate.get("asset_id"), "candidate asset_id")
        asset_sha = _text(selected_candidate.get("asset_sha256"), "candidate asset SHA")
        asset = self._asset(asset_id)
        provenance = asset.generation_provenance
        if set(provenance) != _PROVENANCE_FIELDS:
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_ASSET_PROFILE",
                "Generated IMAGE provenance is not exact",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        execution_id = _text(provenance.get("execution_id"), "generation execution_id")
        queue_entry_id = _text(provenance.get("queue_entry_id"), "queue_entry_id")
        if (
            asset.asset_id != asset_id
            or asset.checksum != asset_sha
            or asset.production_job_id != self.product_job_id
            or asset.asset_type is not AssetType.IMAGE
            or asset.source_project != self.project_id
            or asset.rights_status is not RightsStatus.UNKNOWN
            or asset.commercial_use is not PermissionState.UNKNOWN
            or asset.derivative_allowed is not PermissionState.UNKNOWN
            or asset.reuse_allowed is not PermissionState.UNKNOWN
            or asset.retention_class is not RetentionClass.STANDARD
            or asset.audio_rights_status is not AudioRightsStatus.NOT_APPLICABLE
            or asset.human_lock is not False
            or asset.publication_restrictions != _RESTRICTIONS
            or provenance.get("kind") != "TASK013_COMPLETED_LOCAL_GENERATION"
            or provenance.get("output_sha256") != asset.checksum
            or provenance.get("provider_execution_replayed") is not False
            or provenance.get("paid_execution_authorized") is not False
            or selected_candidate.get("generation_job_id") != execution_id
        ):
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_ASSET_PROFILE",
                "Asset is outside the exact placement-only generated IMAGE profile",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        binding = TimelineSourceBinding(
            project_id=self.project_id,
            production_snapshot_sha256=snapshot_sha,
            scene_id=_text(selected_slot.get("scene_id"), "scene_id"),
            slot_id=slot_id,
            candidate_id=candidate_id,
            asset_id=asset.asset_id,
            asset_sha256=asset.checksum,
            product_job_id=self.product_job_id,
            generation_execution_id=execution_id,
            queue_entry_id=queue_entry_id,
        )
        return _EligibleSource(snapshot_sha, selected_slot, selected_candidate, asset, binding)

    def commit_guard_for_command(self, command: TimelineEditCommand) -> Callable[[], ContextManager[object]]:
        binding = command.after_source_binding
        if binding is None:
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_BINDING_MISSING",
                "Placement command lacks its source binding",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        @contextmanager
        def guard() -> Any:
            with self._production_guard_factory(binding.production_snapshot_sha256) as guarded:
                current = self._eligible(binding.candidate_id, source=guarded)
                if current.binding != binding:
                    raise ProductError(
                        "ERR_VISUAL_PLACEMENT_SOURCE_STALE",
                        "Visual source changed before Project commit",
                        ProductErrorCategory.STATE,
                    )
                yield

        return guard

    @staticmethod
    def _visual_track(timeline: InteractiveTimeline, track_id: str) -> TimelineTrack:
        track = next((item for item in timeline.tracks if item.track_id == track_id), None)
        if (
            track is None
            or track.media_kind is not TimelineMediaKind.VIDEO
            or track.role not in {TimelineTrackRole.VIDEO, TimelineTrackRole.OVERLAY}
        ):
            raise ProductError(
                "ERR_VISUAL_PLACEMENT_TRACK_INVALID",
                "Target track is not a visual VIDEO/OVERLAY track",
                ProductErrorCategory.VALIDATION,
            )
        return track

    @staticmethod
    def _clip(source: _EligibleSource, *, clip_id: str, track_id: str,
              start_frame: int, end_frame: int) -> InteractiveTimelineClip:
        return InteractiveTimelineClip(
            clip_id=clip_id,
            track_id=track_id,
            start_frame=start_frame,
            end_frame=end_frame,
            source_owner="TASK-003",
            source_ref=source.asset.asset_id,
            source_sha256=source.asset.checksum,
            label=f"{source.binding.scene_id} / {source.slot['slot_kind']}",
            state="PLACED_LOCKED_ASSET",
            review_candidate_id=source.binding.candidate_id,
        )

    def prepare_insert(
        self,
        *,
        timeline: InteractiveTimeline,
        candidate_id: str,
        target_track_id: str,
        start_frame: int,
        end_frame: int,
        command_id: str,
        expected_project_manifest_sha256: str,
        expected_production_snapshot_sha256: str,
    ) -> dict[str, object]:
        if timeline.project_id != self.project_id:
            raise ProductError("ERR_VISUAL_PLACEMENT_PROJECT_MISMATCH", "Timeline belongs to another Project", ProductErrorCategory.SECURITY)
        self._visual_track(timeline, target_track_id)
        if isinstance(start_frame, bool) or isinstance(end_frame, bool) or not isinstance(start_frame, int) or not isinstance(end_frame, int) or start_frame < 0 or end_frame <= start_frame or end_frame > timeline.duration_frames:
            raise ProductError("ERR_VISUAL_PLACEMENT_RANGE_INVALID", "Placement range is invalid", ProductErrorCategory.VALIDATION)
        source = self._eligible(candidate_id)
        if source.snapshot_sha256 != expected_production_snapshot_sha256:
            raise ProductError("ERR_VISUAL_PLACEMENT_SOURCE_STALE", "Production Control changed; reload first", ProductErrorCategory.STATE)
        identity = canonical_json_bytes({
            "project_id": self.project_id,
            "candidate_id": candidate_id,
            "asset_id": source.asset.asset_id,
            "target_track_id": target_track_id,
            "start": start_frame,
            "end": end_frame,
        })
        clip_id = f"visual-{hashlib.sha256(identity).hexdigest()}"
        command = TimelineEditCommand(
            command_id=command_id,
            kind=TimelineEditKind.INSERT_CLIP,
            after_clip=self._clip(source, clip_id=clip_id, track_id=target_track_id,
                                  start_frame=start_frame, end_frame=end_frame),
            after_source_binding=source.binding,
        )
        return self._timeline_application.prepare_placement(
            timeline=timeline,
            command=command,
            expected_project_manifest_sha256=expected_project_manifest_sha256,
        )

    def prepare_replace(
        self,
        *,
        timeline: InteractiveTimeline,
        candidate_id: str,
        target_clip_id: str,
        command_id: str,
        expected_project_manifest_sha256: str,
        expected_production_snapshot_sha256: str,
    ) -> dict[str, object]:
        projected, _in_out, bindings, _manifest_sha = self._timeline_application.project_with_source_bindings(timeline)
        before = next((item for item in projected.clips if item.clip_id == target_clip_id), None)
        if before is None:
            raise ProductError("ERR_VISUAL_PLACEMENT_TARGET_MISSING", "Replacement target is missing", ProductErrorCategory.STATE)
        self._visual_track(projected, before.track_id)
        source = self._eligible(candidate_id)
        if source.snapshot_sha256 != expected_production_snapshot_sha256:
            raise ProductError("ERR_VISUAL_PLACEMENT_SOURCE_STALE", "Production Control changed; reload first", ProductErrorCategory.STATE)
        command = TimelineEditCommand(
            command_id=command_id,
            kind=TimelineEditKind.REPLACE_CLIP,
            before_clip=before,
            after_clip=self._clip(source, clip_id=before.clip_id, track_id=before.track_id,
                                  start_frame=before.start_frame, end_frame=before.end_frame),
            before_source_binding=bindings.get(before.clip_id),
            after_source_binding=source.binding,
        )
        return self._timeline_application.prepare_placement(
            timeline=timeline,
            command=command,
            expected_project_manifest_sha256=expected_project_manifest_sha256,
        )

    def apply(self, *, confirmation_id: str, timeline: InteractiveTimeline) -> dict[str, object]:
        return self._timeline_application.apply(confirmation_id=confirmation_id, timeline=timeline)

    def cancel(self, *, confirmation_id: str) -> dict[str, object]:
        return self._timeline_application.cancel(confirmation_id=confirmation_id)

    def recover_project_save(self, *, transaction_id: str, action: str) -> dict[str, object]:
        return self._timeline_application.recover_project_save(
            transaction_id=transaction_id,
            action=action,
        )

    def snapshot(self, *, timeline: InteractiveTimeline) -> dict[str, object]:
        production, production_sha = self._production()
        eligible: list[dict[str, object]] = []
        candidate_ids: list[str] = []
        for raw_slot in self._slots(production):
            slot = _mapping(raw_slot, "production slot")
            for raw_candidate in _rows(slot.get("candidates", []), "slot candidates", _MAX_CANDIDATES):
                candidate = _mapping(raw_candidate, "production candidate")
                candidate_ids.append(_text(candidate.get("candidate_id"), "candidate_id"))
        for candidate_id in sorted(set(candidate_ids)):
            try:
                source = self._eligible(candidate_id, source=production)
            except ProductError:
                continue
            eligible.append({
                "scene_id": source.binding.scene_id,
                "slot_id": source.binding.slot_id,
                "slot_kind": source.slot["slot_kind"],
                "candidate_id": source.binding.candidate_id,
                "asset_id": source.binding.asset_id,
                "asset_sha256": source.binding.asset_sha256,
                "production_snapshot_sha256": production_sha,
                "publication_authorized": False,
            })
        projected, _in_out, bindings, manifest_sha = self._timeline_application.project_with_source_bindings(timeline)
        placements: list[dict[str, object]] = []
        for clip in sorted(projected.clips, key=lambda item: item.clip_id):
            binding = bindings.get(clip.clip_id)
            if binding is None:
                continue
            state = "CURRENT"
            reason = None
            try:
                current = self._eligible(binding.candidate_id, source=production)
                if current.binding != binding or clip.source_ref != binding.asset_id or clip.source_sha256 != binding.asset_sha256:
                    raise ProductError("ERR_VISUAL_PLACEMENT_SOURCE_STALE", "Placement source changed", ProductErrorCategory.STATE)
            except ProductError as exc:
                state, reason = "STALE", exc.code
            placements.append({
                "clip_id": clip.clip_id,
                "candidate_id": binding.candidate_id,
                "asset_id": binding.asset_id,
                "asset_sha256": binding.asset_sha256,
                "state": state,
                "reason_code": reason,
                "publication_authorized": False,
            })
        body: dict[str, object] = {
            "projection_version": "1.0.0",
            "available": True,
            "project_id": self.project_id,
            "project_manifest_sha256": manifest_sha,
            "production_snapshot_sha256": production_sha,
            "projected_timeline_sha256": projected.timeline_sha256,
            "eligible_sources": eligible,
            "placements": placements,
            "placement_count": len(placements),
            "stale_placement_count": sum(row["state"] == "STALE" for row in placements),
            "project_save_recovery": self._timeline_application.project_save_recovery_status(),
            "rights_approved": False,
            "publication_authorized": False,
            "provider_execution_started": False,
            "external_mutation_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


__all__ = ["Task036VisualAssetPlacementApplication"]
