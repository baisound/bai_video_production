from pathlib import Path

from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_safe_visual_learning import SafeVisualLearningService, TrainingDataReviewService, TrainingReviewState
from ai_video_production.dbd_training_workspace import VisualTrainingDomain, VisualTrainingManifest, VisualTrainingSample
from ai_video_production.dbd_vision_slices import NormalizedROI


class FakeExtractor:
    def extract_frame_roi(self, *, video_path, frame_index, roi, output_path, width, height):
        Path(output_path).write_bytes(b"P5\n2 2\n255\n" + bytes([1, 2, 3, 4]))
        return Path(output_path)


def make_service(tmp_path):
    manifest = VisualTrainingManifest(tmp_path / "visual-training.csv")
    service = SafeVisualLearningService(workspace_root=tmp_path, manifest=manifest)
    service.extractor = FakeExtractor()
    return service, manifest


def test_preview_does_not_register(tmp_path):
    video = tmp_path / "match.mp4"; video.write_bytes(b"video")
    service, manifest = make_service(tmp_path)
    staged = service.preview_video_frame(
        domain=VisualTrainingDomain.PERK_ICON,
        label="perk_iron_will",
        visibility=HudVisibility.VISIBLE,
        video_path=video,
        frame_index=120,
        roi=NormalizedROI("perk_slot_0", 0.8, 0.7, 0.1, 0.1),
    )
    assert staged.state is TrainingReviewState.PREVIEWED
    assert Path(staged.image_path).is_file()
    assert manifest.list() == ()


def test_confirm_register_is_explicit_boundary(tmp_path):
    video = tmp_path / "match.mp4"; video.write_bytes(b"video")
    service, manifest = make_service(tmp_path)
    staged = service.preview_video_frame(
        domain=VisualTrainingDomain.PERK_ICON,
        label="perk_iron_will",
        visibility=HudVisibility.HIDDEN,
        video_path=video,
        frame_index=120,
        roi=NormalizedROI("perk_slot_0", 0.8, 0.7, 0.1, 0.1),
    )
    assert service.confirm_register(staged)
    rows = manifest.list()
    assert len(rows) == 1
    assert rows[0].label == "perk_iron_will"
    assert "visibility=HIDDEN" in rows[0].notes


def test_tampered_preview_fails_closed(tmp_path):
    video = tmp_path / "match.mp4"; video.write_bytes(b"video")
    service, manifest = make_service(tmp_path)
    staged = service.preview_video_frame(
        domain=VisualTrainingDomain.ITEM_ICON,
        label="item_medkit",
        visibility=HudVisibility.VISIBLE,
        video_path=video,
        frame_index=10,
        roi=NormalizedROI("item_slot", 0.1, 0.7, 0.1, 0.1),
    )
    Path(staged.image_path).write_bytes(b"tampered")
    try:
        service.confirm_register(staged)
    except ValueError:
        pass
    else:
        raise AssertionError("tampered preview must fail")
    assert manifest.list() == ()


def test_review_relabel_and_delete(tmp_path):
    manifest = VisualTrainingManifest(tmp_path / "visual-training.csv")
    image = tmp_path / "x.pgm"; image.write_bytes(b"x")
    manifest.append(VisualTrainingSample(domain=VisualTrainingDomain.PERK_ICON, label="old", image_path=str(image)))
    review = TrainingDataReviewService(manifest)
    assert review.relabel_exact(image_path=str(image), old_label="old", new_label="new")
    assert manifest.list()[0].label == "new"
    assert review.delete_exact(image_path=str(image), label="new")
    assert manifest.list() == ()
