from pathlib import Path
from ai_video_production.dbd_hud_detectors import (
    DBDNotificationTextDetector, HudVisibility, PerkIconDetector, PerkSlotObservation, SurvivorHudState,
    SurvivorHudStateDetector,
)
from ai_video_production.dbd_vision_slices import GrayImage, ReferenceSliceIndex


def _pgm(path: Path, invert=False):
    pixels=[]
    for y in range(8):
        for x in range(9):
            value = 255 if x > 3 else 0
            pixels.append(255-value if invert else value)
    path.write_bytes(b'P5\n9 8\n255\n'+bytes(pixels)); return path

class FakeOcr:
    def __init__(self, text): self.text=text
    def read(self, image_path, *, language='jpn+eng'): return self.text


def test_perk_and_survivor_reference_detectors(tmp_path):
    healthy=_pgm(tmp_path/'healthy.pgm'); injured=_pgm(tmp_path/'injured.pgm', True)
    hud=ReferenceSliceIndex.train_from_pgm(index_id='hud', samples=[('HEALTHY',healthy),('INJURED',injured)])
    detector=SurvivorHudStateDetector(hud, acceptance_milli=700)
    assert detector.detect_slot(GrayImage.read_pgm(healthy), slot=0).state is SurvivorHudState.HEALTHY
    before=[detector.detect_slot(GrayImage.read_pgm(healthy), slot=0)]
    after=[detector.detect_slot(GrayImage.read_pgm(injured), slot=0)]
    assert detector.detect_transition(before, after)[0][1:] == (SurvivorHudState.HEALTHY, SurvivorHudState.INJURED, 1000)

    perks=ReferenceSliceIndex.train_from_pgm(index_id='perks', samples=[('perk_a',healthy),('perk_b',injured)])
    p=PerkIconDetector(perks, acceptance_milli=700)
    assert p.detect_slot(GrayImage.read_pgm(healthy), slot=2).perk_id == 'perk_a'


def test_upper_right_ocr_vocabulary_resolution(tmp_path):
    image=tmp_path/'x.png'; image.write_bytes(b'x')
    result=DBDNotificationTextDetector(FakeOcr('追跡 +125')).detect(image)
    assert result.signal_id == 'CHASE'
    assert result.confidence_milli >= 650

from ai_video_production.dbd_hud_detectors import ReferenceSliceClassifier
from ai_video_production.dbd_vision_slices import SliceMatch


class _RepeatedReferenceIndex:
    references = (object(), object(), object())
    def match(self, image, *, top_k=3):
        rows = (
            SliceMatch('perk_a', 920, 5, 'a-normal'),
            SliceMatch('perk_a', 915, 6, 'a-active'),
            SliceMatch('perk_b', 890, 7, 'b-normal'),
        )
        return rows[:top_k]


def test_classifier_compares_unique_labels_not_duplicate_references():
    result = ReferenceSliceClassifier(_RepeatedReferenceIndex(), acceptance_milli=800, ambiguity_margin_milli=60).classify(
        GrayImage(1, 1, b'\x00')
    )
    assert result.unknown is True
    assert [item.label for item in result.candidates] == ['perk_a', 'perk_b']


def test_perk_hidden_is_distinct_from_unknown_identity(tmp_path):
    visible = _pgm(tmp_path/'visible.pgm')
    hidden = _pgm(tmp_path/'hidden.pgm', True)
    index = ReferenceSliceIndex.train_from_pgm(
        index_id='perk-hidden',
        samples=[('perk_a', visible), ('PERK_HIDDEN', hidden)],
    )
    detector = PerkIconDetector(index, acceptance_milli=700)
    result = detector.detect_slot(GrayImage.read_pgm(hidden), slot=0)
    assert result.perk_id is None
    assert result.visibility is HudVisibility.HIDDEN


def test_perk_partial_occlusion_abstains_from_identity(tmp_path):
    visible = _pgm(tmp_path/'visible.pgm')
    partial = _pgm(tmp_path/'partial.pgm', True)
    index = ReferenceSliceIndex.train_from_pgm(
        index_id='perk-partial',
        samples=[('perk_a', visible), ('PERK_PARTIALLY_OCCLUDED', partial)],
    )
    detector = PerkIconDetector(index, acceptance_milli=700)
    result = detector.detect_slot(GrayImage.read_pgm(partial), slot=3)
    assert result.perk_id is None
    assert result.visibility is HudVisibility.PARTIALLY_OCCLUDED


def test_perk_temporal_vote_preserves_hidden_state():
    detector = PerkIconDetector.__new__(PerkIconDetector)
    detector.temporal_minimum_frames = 2
    observations = [
        PerkSlotObservation(1, None, 900, (), HudVisibility.HIDDEN),
        PerkSlotObservation(1, None, 880, (), HudVisibility.HIDDEN),
    ]
    result = detector.temporal_vote(observations)
    assert result.perk_id is None
    assert result.visibility is HudVisibility.HIDDEN
