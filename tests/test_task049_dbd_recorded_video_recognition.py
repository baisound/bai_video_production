from pathlib import Path

from ai_video_production.canonical_game_event import GameEventType
from ai_video_production.dbd_cross_modal_fusion import FusionModality, FusionObservation
from ai_video_production.dbd_hud_detectors import DBDNotificationTextDetector, PerkIconDetector, SurvivorHudStateDetector
from ai_video_production.dbd_killer_knowledge import KillerPowerVisualRecognizer
from ai_video_production.dbd_loadout_knowledge import LoadoutKnowledgeKind, LoadoutVisualRecognizer
from ai_video_production.dbd_recorded_video_recognition import DbDRecordedVideoRecognizer
from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, NormalizedROI, ReferenceSliceIndex
from ai_video_production.game_event_evidence import SourceFrameRange


def _pgm(path: Path, seed: int) -> Path:
    # Different diagonal/check patterns create stable distinct dHash features.
    pixels = bytearray()
    for y in range(16):
        for x in range(16):
            pixels.append(255 if ((x * (seed + 1) + y * (seed + 3) + seed) % 11) < 5 else 0)
    path.write_bytes(b"P5\n16 16\n255\n" + bytes(pixels))
    return path


class _FakeExtractor:
    def __init__(self, mapping):
        self.mapping = mapping

    def extract_frame_roi(self, *, video_path, frame_index, roi, output_path, width=64, height=64):
        key = (frame_index, roi.roi_id)
        source = self.mapping.get(key) or self.mapping.get((None, roi.roi_id))
        if source is None:
            raise AssertionError(f"missing fake slice {key}")
        Path(output_path).write_bytes(Path(source).read_bytes())
        return Path(output_path)


class _FakeOcr:
    def read(self, image_path, *, language="jpn+eng"):
        return "窓越え"


def test_recorded_video_recognizer_connects_hud_perk_ocr_killer_and_fusion(tmp_path: Path) -> None:
    healthy = _pgm(tmp_path / "healthy.pgm", 1)
    injured = _pgm(tmp_path / "injured.pgm", 2)
    neutral = _pgm(tmp_path / "neutral.pgm", 3)
    perk_a = _pgm(tmp_path / "perk-a.pgm", 4)
    killer = _pgm(tmp_path / "killer.pgm", 5)
    item = _pgm(tmp_path / "item.pgm", 6)
    addon = _pgm(tmp_path / "addon.pgm", 7)

    survivor_index = ReferenceSliceIndex.train_from_pgm(index_id="survivor", samples=[("HEALTHY", healthy), ("INJURED", injured), ("DOWNED", neutral)])
    perk_index = ReferenceSliceIndex.train_from_pgm(index_id="perk", samples=[("perk_windows", perk_a), ("perk_other", neutral)])
    killer_index = ReferenceSliceIndex.train_from_pgm(index_id="killer", samples=[("killer_trapper", killer), ("power_other", neutral)])
    item_index = ReferenceSliceIndex.train_from_pgm(index_id="item", samples=[("item_medkit", item), ("item_other", neutral)])
    addon_index = ReferenceSliceIndex.train_from_pgm(index_id="addon", samples=[("addon_bandages", addon), ("addon_other", neutral)])

    profile = DBDHudRoiProfile(
        killer_power_hud=NormalizedROI("killer_power", 0.4, 0.8, 0.1, 0.1),
        lower_left_loadout_hud=NormalizedROI("lower_left_loadout_hud", 0.13, 0.74, 0.20, 0.24),
        item_slot=NormalizedROI("item_slot", 0.14, 0.80, 0.08, 0.12),
        addon_slots=(NormalizedROI("addon_slot_0", 0.225, 0.80, 0.045, 0.055), NormalizedROI("addon_slot_1", 0.275, 0.80, 0.045, 0.055)),
    )
    mapping = {}
    for frame in (10, 11):
        for slot in range(4):
            mapping[(frame, profile.survivor_slot_roi(slot).roi_id)] = healthy
            mapping[(frame, profile.perk_slot_roi(slot).roi_id)] = perk_a
        mapping[(frame, profile.upper_right_notifications.roi_id)] = neutral
        mapping[(frame, "killer_power")] = killer
        mapping[(frame, "item_slot")] = item
        mapping[(frame, "addon_slot_0")] = addon
        mapping[(frame, "addon_slot_1")] = addon
    mapping[(11, profile.survivor_slot_roi(0).roi_id)] = injured

    recognizer = DbDRecordedVideoRecognizer(
        roi_profile=profile,
        extractor=_FakeExtractor(mapping),
        survivor_detector=SurvivorHudStateDetector(survivor_index, acceptance_milli=500),
        perk_detector=PerkIconDetector(perk_index, acceptance_milli=500, temporal_minimum_frames=1),
        notification_detector=DBDNotificationTextDetector(_FakeOcr()),
        killer_power_recognizer=KillerPowerVisualRecognizer(killer_index, acceptance_milli=500),
        item_recognizer=LoadoutVisualRecognizer(item_index, kind=LoadoutKnowledgeKind.ITEM, acceptance_milli=500),
        addon_recognizer=LoadoutVisualRecognizer(addon_index, kind=LoadoutKnowledgeKind.ADDON, acceptance_milli=500),
    )

    before = recognizer.recognize_frame(video_path=tmp_path / "fake.mp4", frame_index=10, working_directory=tmp_path / "w0")
    after = recognizer.recognize_frame(video_path=tmp_path / "fake.mp4", frame_index=11, working_directory=tmp_path / "w1")
    assert before.survivor_slots[0].state.value == "HEALTHY"
    assert after.survivor_slots[0].state.value == "INJURED"
    assert all(item.perk_id == "perk_windows" for item in after.perk_slots)
    assert after.notification.signal_id == "WINDOW_VAULT"
    assert after.killer_power.entity_id == "killer_trapper"
    assert after.item.entity_id == "item_medkit"
    assert [row.entity_id for row in after.addons] == ["addon_bandages", "addon_bandages"]

    observations = recognizer.event_observations(before, after)
    assert {item.event_type for item in observations} == {GameEventType.INJURY, GameEventType.WINDOW_VAULT}
    # Strong HUD state evidence wins over a weaker OCR-only competing signal.
    decision = recognizer.fuse_frame_pair(before, after)
    assert decision.event_type is GameEventType.INJURY
    assert decision.confidence_milli == 1000

    # Independent support can be fused when the caller scopes a single event candidate.
    injury = next(item for item in observations if item.event_type is GameEventType.INJURY)
    decision = recognizer.fusion.fuse((
        injury,
        FusionObservation(GameEventType.INJURY, FusionModality.VISION, 900, SourceFrameRange(10, 12), "vision://injury"),
    ))
    assert decision.event_type is GameEventType.INJURY
    assert decision.confidence_milli >= 900

from ai_video_production.canonical_game_event import GameEnvironment, GameKnowledgeKind
from ai_video_production.dbd_hud_detectors import PerkSlotObservation
from ai_video_production.dbd_killer_knowledge import DbDKillerKnowledgeStore, KillerKnowledgeKind, KillerKnowledgeRevision, KillerKnowledgeSource, KillerKnowledgeStatus, KillerPowerVisualObservation
from ai_video_production.dbd_perk_knowledge import DbDPerkKnowledgeStore, PerkEnvironment, PerkIdentity, PerkKnowledgeSource, PerkLocalization, PerkRevision, PerkRevisionStatus, PerkRole, PerkSourceAuthority
from ai_video_production.dbd_recorded_video_recognition import DBDFrameRecognition, DbDRecognitionKnowledgeResolver
from ai_video_production.serialization import sha256_bytes, utc_now_iso
import hashlib


def test_recognition_knowledge_resolver_binds_perk_and_killer_revision(tmp_path: Path) -> None:
    perk_store = DbDPerkKnowledgeStore(tmp_path / "perk.sqlite3")
    perk_store.put_identity(PerkIdentity("perk_windows", "windows", PerkRole.SURVIVOR))
    perk_store.put_localization(PerkLocalization("perk_windows", "ja-JP", "ウィンドウズ"))
    psource = PerkKnowledgeSource("source-perk", "MANUAL", PerkSourceAuthority.MANUAL_VERIFIED, utc_now_iso(), sha256_bytes(b"perk"), environment=PerkEnvironment.LIVE)
    perk_store.put_source(psource)
    perk_store.put_revision(PerkRevision("PREV-1", "perk_windows", "9.0.0", PerkEnvironment.LIVE, PerkRevisionStatus.VERIFIED, (psource.source_id,), official_effect_ja="窓枠情報を表示します。"))

    killer_store = DbDKillerKnowledgeStore(tmp_path / "killer.sqlite3")
    ksource = KillerKnowledgeSource("source-killer", "BHVR_OFFICIAL", "manual://killer", hashlib.sha256(b"killer").hexdigest())
    killer_store.put_source(ksource)
    killer_store.put_revision(KillerKnowledgeRevision("killer_trapper", "KREV-1", KillerKnowledgeKind.KILLER, "トラッパー", "Trapper", PerkEnvironment.LIVE, "9.0.0", None, KillerKnowledgeStatus.VERIFIED, ksource.source_id))

    recognition = DBDFrameRecognition(
        100, (),
        (PerkSlotObservation(0, "perk_windows", 950, ()), PerkSlotObservation(1, None, 500, ()), PerkSlotObservation(2, None, 500, ()), PerkSlotObservation(3, None, 500, ())),
        None, KillerPowerVisualObservation("killer_trapper", 920, KillerKnowledgeKind.KILLER), (),
    )
    result = DbDRecognitionKnowledgeResolver(perk_store=perk_store, killer_store=killer_store).resolve(recognition, game_version="9.1.0", environment=GameEnvironment.LIVE)
    assert {ref.knowledge_kind for ref in result.knowledge_refs} == {GameKnowledgeKind.PERK, GameKnowledgeKind.KILLER}
    assert "perk_slot_1:UNKNOWN" in result.unresolved
