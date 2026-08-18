"""TASK-049 recorded-video HUD recognition orchestration.

This module connects the reusable ROI/slice baselines to one bounded exact-frame
recognition flow.  It is intentionally accuracy-neutral: discovery ROIs and
reference dHash matching are replaceable baselines, and all weak/ambiguous
results remain UNKNOWN or require review until real-media Human Gold calibration
establishes production thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Iterable, Protocol

from .canonical_game_event import GameEnvironment, GameEventType, GameKnowledgeRef
from .dbd_cross_modal_fusion import DBDCrossModalFusion, FusionDecision, FusionModality, FusionObservation
from .dbd_hud_detectors import (
    DBDNotificationTextDetector,
    NotificationTextObservation,
    PerkIconDetector,
    PerkSlotObservation,
    SurvivorHudState,
    SurvivorHudStateDetector,
    SurvivorSlotObservation,
)
from .dbd_killer_knowledge import DbDKillerKnowledgeStore, KillerPowerVisualObservation, KillerPowerVisualRecognizer
from .dbd_loadout_knowledge import (
    DbDLoadoutKnowledgeStore, LoadoutKnowledgeKind, LoadoutVisualObservation, LoadoutVisualRecognizer,
)
from .dbd_perk_knowledge import DbDPerkKnowledgeStore, PerkEnvironment
from .dbd_vision_slices import DBDHudRoiProfile, FFmpegSliceExtractor, GrayImage, NormalizedROI
from .dbd_hud_calibration import DBDHudVideoProfileResolver, FFmpegFrameInspector, HudAnchorAligner
from .game_event_evidence import SourceFrameRange
from .serialization import sha256_bytes


class SliceExtractor(Protocol):
    def extract_frame_roi(
        self, *, video_path: str | Path, frame_index: int, roi: NormalizedROI,
        output_path: str | Path, width: int = 64, height: int = 64,
    ) -> Path: ...


@dataclass(frozen=True, slots=True)
class SliceArtifact:
    roi_id: str
    frame_index: int
    sha256: str


@dataclass(frozen=True, slots=True)
class DBDFrameRecognition:
    frame_index: int
    survivor_slots: tuple[SurvivorSlotObservation, ...]
    perk_slots: tuple[PerkSlotObservation, ...]
    notification: NotificationTextObservation | None
    killer_power: KillerPowerVisualObservation | None
    slice_artifacts: tuple[SliceArtifact, ...]
    item: LoadoutVisualObservation | None = None
    addons: tuple[LoadoutVisualObservation, ...] = ()

    def __post_init__(self) -> None:
        if self.frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        if self.survivor_slots and len(self.survivor_slots) != 4:
            raise ValueError("survivor_slots must contain four observations when enabled")
        if self.perk_slots and len(self.perk_slots) != 4:
            raise ValueError("perk_slots must contain four observations when enabled")
        if self.addons and len(self.addons) != 2:
            raise ValueError("addons must contain two observations when enabled")


_NOTIFICATION_EVENT_MAP = {
    "WINDOW_VAULT": GameEventType.WINDOW_VAULT,
    "HOOK": GameEventType.HOOK,
    "UNHOOK": GameEventType.UNHOOK,
}


def _transition_event(old: SurvivorHudState, new: SurvivorHudState) -> GameEventType | None:
    if old is SurvivorHudState.HEALTHY and new is SurvivorHudState.INJURED:
        return GameEventType.INJURY
    if new is SurvivorHudState.DOWNED and old in {SurvivorHudState.HEALTHY, SurvivorHudState.INJURED}:
        return GameEventType.DOWN
    if new is SurvivorHudState.HOOKED and old is not SurvivorHudState.HOOKED:
        return GameEventType.HOOK
    if old is SurvivorHudState.HOOKED and new in {SurvivorHudState.HEALTHY, SurvivorHudState.INJURED}:
        return GameEventType.UNHOOK
    if new is SurvivorHudState.DEAD and old is not SurvivorHudState.DEAD:
        return GameEventType.KILL
    if new is SurvivorHudState.ESCAPED and old is not SurvivorHudState.ESCAPED:
        return GameEventType.ESCAPE
    return None


@dataclass(frozen=True, slots=True)
class DBDRecognitionKnowledgeResolution:
    knowledge_refs: tuple[GameKnowledgeRef, ...]
    unresolved: tuple[str, ...]


class DbDRecognitionKnowledgeResolver:
    """Resolve visual identity candidates to patch-compatible canonical knowledge refs."""

    def __init__(self, *, perk_store: DbDPerkKnowledgeStore | None = None, killer_store: DbDKillerKnowledgeStore | None = None, loadout_store: DbDLoadoutKnowledgeStore | None = None) -> None:
        self.perk_store = perk_store
        self.killer_store = killer_store
        self.loadout_store = loadout_store

    def resolve(self, recognition: DBDFrameRecognition, *, game_version: str, environment: GameEnvironment) -> DBDRecognitionKnowledgeResolution:
        refs: list[GameKnowledgeRef] = []
        unresolved: list[str] = []
        perk_environment = PerkEnvironment(environment.value)
        for item in recognition.perk_slots:
            if item.perk_id is None:
                unresolved.append(f"perk_slot_{item.slot}:{item.visibility.value}")
                continue
            if self.perk_store is None:
                unresolved.append(f"perk_slot_{item.slot}:STORE_UNAVAILABLE")
                continue
            try:
                refs.append(self.perk_store.lookup(item.perk_id, game_version=game_version, environment=environment).to_knowledge_ref())
            except Exception:
                unresolved.append(f"perk_slot_{item.slot}:{item.perk_id}:UNRESOLVED")
        loadout_rows = (() if recognition.item is None else (recognition.item,)) + recognition.addons
        for item in loadout_rows:
            prefix = "item" if item.kind is LoadoutKnowledgeKind.ITEM else f"addon_slot_{item.slot}"
            if item.entity_id is None:
                unresolved.append(f"{prefix}:{item.visibility.value}")
                continue
            if self.loadout_store is None:
                unresolved.append(f"{prefix}:{item.entity_id}:STORE_UNAVAILABLE")
                continue
            try:
                refs.append(self.loadout_store.lookup(item.entity_id, game_version=game_version, environment=perk_environment).to_knowledge_ref())
            except Exception:
                unresolved.append(f"{prefix}:{item.entity_id}:UNRESOLVED")

        if recognition.killer_power is not None and recognition.killer_power.entity_id is not None:
            if self.killer_store is None:
                unresolved.append(f"{recognition.killer_power.entity_id}:STORE_UNAVAILABLE")
            else:
                try:
                    refs.append(self.killer_store.lookup(recognition.killer_power.entity_id, game_version=game_version, environment=perk_environment).to_knowledge_ref())
                except Exception:
                    unresolved.append(f"{recognition.killer_power.entity_id}:UNRESOLVED")
        unique = {ref.to_dict()["knowledge_ref_sha256"]: ref for ref in refs}
        return DBDRecognitionKnowledgeResolution(
            tuple(sorted(unique.values(), key=lambda x: (x.knowledge_kind.value, x.entity_id, x.revision_id))),
            tuple(sorted(set(unresolved))),
        )


class DbDRecordedVideoRecognizer:
    """Run configured lower-left/upper-right/bottom-right recognition on exact frames.

    The caller decides which recognizers are available.  Missing recognizers do
    not become fake negative evidence; their output collections remain empty.
    """

    def __init__(
        self,
        *,
        roi_profile: DBDHudRoiProfile = DBDHudRoiProfile(),
        extractor: SliceExtractor | None = None,
        survivor_detector: SurvivorHudStateDetector | None = None,
        perk_detector: PerkIconDetector | None = None,
        notification_detector: DBDNotificationTextDetector | None = None,
        killer_power_recognizer: KillerPowerVisualRecognizer | None = None,
        item_recognizer: LoadoutVisualRecognizer | None = None,
        addon_recognizer: LoadoutVisualRecognizer | None = None,
        fusion: DBDCrossModalFusion | None = None,
        profile_resolver: DBDHudVideoProfileResolver | None = None,
        anchor_aligner: HudAnchorAligner | None = None,
        frame_inspector: FFmpegFrameInspector | None = None,
        ui_scale_percent: int | None = None,
        game_version: str | None = None,
    ) -> None:
        self.roi_profile = roi_profile
        self.extractor = extractor or FFmpegSliceExtractor()
        self.survivor_detector = survivor_detector
        self.perk_detector = perk_detector
        self.notification_detector = notification_detector
        self.killer_power_recognizer = killer_power_recognizer
        self.item_recognizer = item_recognizer
        self.addon_recognizer = addon_recognizer
        self.fusion = fusion or DBDCrossModalFusion()
        self.profile_resolver = profile_resolver
        self.anchor_aligner = anchor_aligner
        self.frame_inspector = frame_inspector or FFmpegFrameInspector()
        self.ui_scale_percent = ui_scale_percent
        self.game_version = game_version

    def _slice(
        self,
        *,
        video_path: str | Path,
        frame_index: int,
        roi: NormalizedROI,
        target: Path,
        width: int = 96,
        height: int = 96,
    ) -> tuple[GrayImage, SliceArtifact]:
        path = self.extractor.extract_frame_roi(
            video_path=video_path,
            frame_index=frame_index,
            roi=roi,
            output_path=target,
            width=width,
            height=height,
        )
        raw = Path(path).read_bytes()
        return GrayImage.read_pgm(path), SliceArtifact(roi.roi_id, frame_index, sha256_bytes(raw))

    def recognize_frame(
        self,
        *,
        video_path: str | Path,
        frame_index: int,
        working_directory: str | Path | None = None,
    ) -> DBDFrameRecognition:
        if frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        temporary = None
        if working_directory is None:
            temporary = tempfile.TemporaryDirectory(prefix="bvp-dbd-roi-")
            root = Path(temporary.name)
        else:
            root = Path(working_directory)
            root.mkdir(parents=True, exist_ok=True)

        profile = self.roi_profile
        if self.profile_resolver is not None:
            profile = self.profile_resolver.resolve_video(
                video_path=video_path, frame_index=frame_index,
                ui_scale_percent=self.ui_scale_percent, game_version=self.game_version,
            ).profile
        if self.anchor_aligner is not None:
            geometry = self.frame_inspector.probe_geometry(video_path)
            profile = self.anchor_aligner.align(
                video_path=video_path, frame_index=frame_index, profile=profile,
                frame_width=geometry.width, frame_height=geometry.height,
                working_directory=root / "anchor-alignment",
            ).profile

        artifacts: list[SliceArtifact] = []
        survivors: list[SurvivorSlotObservation] = []
        perks: list[PerkSlotObservation] = []
        item_observation: LoadoutVisualObservation | None = None
        addon_observations: list[LoadoutVisualObservation] = []
        notification: NotificationTextObservation | None = None
        killer_power: KillerPowerVisualObservation | None = None
        try:
            if self.survivor_detector is not None:
                for slot in range(4):
                    roi = profile.survivor_slot_roi(slot)
                    image, artifact = self._slice(
                        video_path=video_path, frame_index=frame_index, roi=roi,
                        target=root / f"survivor-{slot}.pgm",
                    )
                    artifacts.append(artifact)
                    survivors.append(self.survivor_detector.detect_slot(image, slot=slot))

            if self.perk_detector is not None:
                for slot in range(4):
                    roi = profile.perk_slot_roi(slot)
                    image, artifact = self._slice(
                        video_path=video_path, frame_index=frame_index, roi=roi,
                        target=root / f"perk-{slot}.pgm",
                    )
                    artifacts.append(artifact)
                    perks.append(self.perk_detector.detect_slot(image, slot=slot))

            if self.item_recognizer is not None:
                roi = profile.item_slot_roi()
                image, artifact = self._slice(
                    video_path=video_path, frame_index=frame_index, roi=roi,
                    target=root / "item.pgm",
                )
                artifacts.append(artifact)
                item_observation = self.item_recognizer.recognize(image)

            if self.addon_recognizer is not None:
                for slot in range(2):
                    roi = profile.addon_slot_roi(slot)
                    image, artifact = self._slice(
                        video_path=video_path, frame_index=frame_index, roi=roi,
                        target=root / f"addon-{slot}.pgm",
                    )
                    artifacts.append(artifact)
                    addon_observations.append(self.addon_recognizer.recognize(image, slot=slot))

            if self.notification_detector is not None:
                roi = profile.upper_right_notifications
                _, artifact = self._slice(
                    video_path=video_path, frame_index=frame_index, roi=roi,
                    target=root / "notification.pgm", width=512, height=256,
                )
                artifacts.append(artifact)
                notification = self.notification_detector.detect(root / "notification.pgm")

            if self.killer_power_recognizer is not None and profile.killer_power_hud is not None:
                roi = profile.killer_power_hud
                image, artifact = self._slice(
                    video_path=video_path, frame_index=frame_index, roi=roi,
                    target=root / "killer-power.pgm",
                )
                artifacts.append(artifact)
                killer_power = self.killer_power_recognizer.recognize(image)

            return DBDFrameRecognition(
                frame_index=frame_index,
                survivor_slots=tuple(survivors),
                perk_slots=tuple(perks),
                item=item_observation,
                addons=tuple(addon_observations),
                notification=notification,
                killer_power=killer_power,
                slice_artifacts=tuple(sorted(artifacts, key=lambda x: x.roi_id)),
            )
        finally:
            if temporary is not None:
                temporary.cleanup()

    @staticmethod
    def event_observations(
        before: DBDFrameRecognition,
        after: DBDFrameRecognition,
    ) -> tuple[FusionObservation, ...]:
        if after.frame_index <= before.frame_index:
            raise ValueError("after frame must be later than before frame")
        source_range = SourceFrameRange(before.frame_index, after.frame_index + 1)
        rows: list[FusionObservation] = []

        if before.survivor_slots and after.survivor_slots:
            left = {item.slot: item for item in before.survivor_slots}
            right = {item.slot: item for item in after.survivor_slots}
            for slot in sorted(set(left) & set(right)):
                old, new = left[slot], right[slot]
                if old.state is SurvivorHudState.UNKNOWN or new.state is SurvivorHudState.UNKNOWN or old.state is new.state:
                    continue
                event_type = _transition_event(old.state, new.state)
                if event_type is None:
                    continue
                rows.append(FusionObservation(
                    event_type=event_type,
                    modality=FusionModality.HUD,
                    confidence_milli=min(old.confidence_milli, new.confidence_milli),
                    source_range=source_range,
                    evidence_ref=f"recognition://survivor-hud/slot-{slot}/{before.frame_index}-{after.frame_index}",
                ))

        notification = after.notification
        if notification is not None and notification.signal_id in _NOTIFICATION_EVENT_MAP:
            rows.append(FusionObservation(
                event_type=_NOTIFICATION_EVENT_MAP[notification.signal_id],
                modality=FusionModality.OCR,
                confidence_milli=notification.confidence_milli,
                source_range=SourceFrameRange(after.frame_index, after.frame_index + 1),
                evidence_ref=f"recognition://upper-right-ocr/{after.frame_index}/{notification.signal_id}",
            ))
        return tuple(rows)

    def fuse_frame_pair(
        self,
        before: DBDFrameRecognition,
        after: DBDFrameRecognition,
        *,
        additional_observations: Iterable[FusionObservation] = (),
    ) -> FusionDecision:
        return self.fusion.fuse(self.event_observations(before, after) + tuple(additional_observations))


__all__ = [
    "DBDFrameRecognition", "DBDRecognitionKnowledgeResolution", "DbDRecognitionKnowledgeResolver",
    "DbDRecordedVideoRecognizer", "SliceArtifact", "SliceExtractor",
]
