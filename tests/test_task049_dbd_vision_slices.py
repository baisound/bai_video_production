from pathlib import Path
from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, GrayImage, ReferenceSliceIndex, TemporalConsensus


def _pgm(path: Path, rows: list[list[int]]) -> Path:
    h, w = len(rows), len(rows[0])
    path.write_bytes(f"P5\n{w} {h}\n255\n".encode() + bytes(x for row in rows for x in row))
    return path


def test_reference_slice_index_round_trip_and_match(tmp_path):
    a = _pgm(tmp_path/'a.pgm', [[0,0,255,255],[0,0,255,255],[0,0,255,255],[0,0,255,255]])
    b = _pgm(tmp_path/'b.pgm', [[255,255,0,0],[255,255,0,0],[255,255,0,0],[255,255,0,0]])
    index = ReferenceSliceIndex.train_from_pgm(index_id='perk-index', samples=[('perk_a', a), ('perk_b', b)])
    assert index.match(GrayImage.read_pgm(a))[0].label == 'perk_a'
    target = index.save(tmp_path/'index.json')
    loaded = ReferenceSliceIndex.load(target)
    assert loaded.match(GrayImage.read_pgm(b))[0].label == 'perk_b'


def test_temporal_consensus_requires_repeated_confident_result():
    assert TemporalConsensus.vote([('A', 900), ('A', 850), ('B', 920)], minimum_frames=2) == ('A', 875)
    assert TemporalConsensus.vote([('A', 600), ('A', 620)], minimum_frames=2, minimum_confidence_milli=650) is None


def test_hud_roi_profile_round_trips_explicit_slot_rois():
    profile = DBDHudRoiProfile()
    loaded = DBDHudRoiProfile.from_dict(profile.to_dict())
    assert loaded.profile_id == profile.profile_id
    assert loaded.survivor_slots == profile.survivor_slots
    assert loaded.perk_slots == profile.perk_slots


def test_reference_index_preserves_per_sample_visual_group(tmp_path):
    normal = _pgm(tmp_path/'normal.pgm', [[0,0,255,255],[0,0,255,255],[0,0,255,255],[0,0,255,255]])
    active = _pgm(tmp_path/'active.pgm', [[255,0,255,0],[255,0,255,0],[255,0,255,0],[255,0,255,0]])
    index = ReferenceSliceIndex.train_from_pgm(
        index_id='perk-visual-states',
        samples=[('perk_a', normal, 'normal'), ('perk_a', active, 'active')],
    )
    assert {item.group for item in index.references} == {'normal', 'active'}
