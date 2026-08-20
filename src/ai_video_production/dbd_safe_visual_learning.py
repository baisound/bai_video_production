"""TASK-050 R3 safe visual learning workflow."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

from .dbd_hud_visibility import HudVisibility
from .dbd_training_workspace import VisualTrainingDomain, VisualTrainingManifest, VisualTrainingSample
from .dbd_vision_slices import FFmpegSliceExtractor, NormalizedROI


class TrainingReviewState(str, Enum):
    PREVIEWED = "PREVIEWED"
    REGISTERED = "REGISTERED"
    DISCARDED = "DISCARDED"


@dataclass(frozen=True, slots=True)
class StagedTrainingSample:
    staging_id: str
    domain: VisualTrainingDomain
    label: str
    visibility: HudVisibility
    source_video: str
    source_frame: int
    roi_id: str
    image_path: str
    source_ref: str
    group: str = "normal"
    notes: str = ""
    registration_origin: str = "VIDEO_SINGLE"
    state: TrainingReviewState = TrainingReviewState.PREVIEWED
    sha256: str = ""

@dataclass(frozen=True, slots=True)
class BatchVisualTarget:
    domain: VisualTrainingDomain
    label: str
    visibility: HudVisibility
    roi: NormalizedROI
    group: str = "normal"
    notes: str = ""


@dataclass(frozen=True, slots=True)
class BatchPreviewReport:
    frame_count: int
    target_count: int
    staged: tuple[StagedTrainingSample, ...]

    @property
    def total_samples(self) -> int:
        return len(self.staged)



class SafeVisualLearningService:
    def __init__(self, *, workspace_root: str | Path, manifest: VisualTrainingManifest, ffmpeg_executable: str = "ffmpeg") -> None:
        self.workspace_root = Path(workspace_root)
        self.manifest = manifest
        self.extractor = FFmpegSliceExtractor(ffmpeg_executable)
        self.staging_root = self.workspace_root / "staging" / "visual-learning"
        self.staging_root.mkdir(parents=True, exist_ok=True)

    def preview_video_frame(
        self, *, domain: VisualTrainingDomain, label: str, visibility: HudVisibility,
        video_path: str | Path, frame_index: int, roi: NormalizedROI,
        group: str = "normal", notes: str = "", registration_origin: str = "VIDEO_SINGLE",
    ) -> StagedTrainingSample:
        source = Path(video_path).expanduser().resolve()
        if not source.is_file():
            raise ValueError("動画ファイルが見つかりません。")
        if frame_index < 0:
            raise ValueError("フレーム位置は0以上で指定してください。")
        if not label.strip():
            raise ValueError("正解ラベルを選択してください。")

        staging_id = f"preview-{uuid4().hex}"
        directory = self.staging_root / staging_id
        directory.mkdir(parents=True, exist_ok=False)
        image_path = directory / f"frame-{frame_index:09d}-{roi.roi_id}.pgm"
        try:
            result = self.extractor.extract_frame_roi(
                video_path=source, frame_index=frame_index, roi=roi,
                output_path=image_path, width=192, height=192,
            )
            raw = Path(result).read_bytes()
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise

        staged = StagedTrainingSample(
            staging_id=staging_id,
            domain=domain,
            label=label.strip(),
            visibility=visibility,
            source_video=str(source),
            source_frame=frame_index,
            roi_id=roi.roi_id,
            image_path=str(Path(result)),
            source_ref=f"video://{source.as_posix()}#frame={frame_index}&roi={roi.roi_id}",
            group=group.strip() or "normal",
            notes=notes.strip(),
            registration_origin=registration_origin,
            sha256=f"sha256:{hashlib.sha256(raw).hexdigest()}",
        )
        self._write_receipt(staged)
        return staged

    def preview_video_batch(
        self, *, video_path: str | Path, start_frame: int, end_frame_exclusive: int,
        frame_step: int, targets: tuple[BatchVisualTarget, ...], max_samples: int = 500,
    ) -> BatchPreviewReport:
        if start_frame < 0 or end_frame_exclusive <= start_frame:
            raise ValueError("動画学習のフレーム抽出範囲が不正です。")
        if frame_step < 1:
            raise ValueError("フレーム抽出間隔は1以上で指定してください。")
        if not targets:
            raise ValueError("学習するゲーム要素を1件以上選択してください。")
        if not 1 <= int(max_samples) <= 10_000:
            raise ValueError("最大件数は1..10000で指定してください。")
        frames = tuple(range(int(start_frame), int(end_frame_exclusive), int(frame_step)))
        requested = len(frames) * len(targets)
        if requested > int(max_samples):
            raise ValueError(
                f"Crop候補 {requested}件は最大件数={max_samples}を超えます。"
                "フレーム間隔を広げるか範囲を分割してください。"
            )
        staged: list[StagedTrainingSample] = []
        try:
            for frame_index in frames:
                for target in targets:
                    staged.append(
                        self.preview_video_frame(
                            domain=target.domain, label=target.label,
                            visibility=target.visibility, video_path=video_path,
                            frame_index=frame_index, roi=target.roi,
                            group=target.group, notes=target.notes,
                            registration_origin="VIDEO_BATCH",
                        )
                    )
        except Exception:
            for item in staged:
                try:
                    self.discard(item.staging_id)
                except Exception:
                    pass
            raise
        return BatchPreviewReport(
            frame_count=len(frames), target_count=len(targets), staged=tuple(staged)
        )

    def confirm_register(self, staged: StagedTrainingSample) -> bool:
        current = self.load_staged(staged.staging_id)
        if current.state is not TrainingReviewState.PREVIEWED:
            raise ValueError("このプレビューは既に処理済みです。")
        source = Path(current.image_path)
        if not source.is_file():
            raise ValueError("プレビュー画像が見つかりません。")
        actual = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
        if actual != current.sha256:
            raise ValueError("プレビュー画像が確認後に変更されています。登録を中止しました。")

        final_dir = self.workspace_root / "training-data" / current.domain.value.lower() / current.label
        final_dir.mkdir(parents=True, exist_ok=True)
        final_path = final_dir / f"{current.staging_id}-{current.roi_id}.pgm"
        if final_path.exists():
            raise ValueError("同じ登録先ファイルが既に存在します。")
        shutil.copy2(source, final_path)

        notes = " | ".join(x for x in (current.notes, f"visibility={current.visibility.value}") if x)
        item = VisualTrainingSample(
            domain=current.domain, label=current.label, image_path=str(final_path),
            group=current.group, source_ref=current.source_ref, notes=notes,
            registration_origin=current.registration_origin, slot=current.roi_id,
            display_state=current.visibility.value, source_video=current.source_video,
            source_frame=current.source_frame,
        )
        if not self.manifest.append(item):
            final_path.unlink(missing_ok=True)
            return False
        self._write_receipt(self._with_state(current, TrainingReviewState.REGISTERED))
        return True

    def discard(self, staging_id: str) -> None:
        current = self.load_staged(staging_id)
        self._write_receipt(self._with_state(current, TrainingReviewState.DISCARDED))

    def load_staged(self, staging_id: str) -> StagedTrainingSample:
        path = self.staging_root / staging_id / "receipt.json"
        if not path.is_file():
            raise ValueError("プレビュー情報が見つかりません。")
        p = json.loads(path.read_text(encoding="utf-8"))
        return StagedTrainingSample(
            staging_id=p["staging_id"], domain=VisualTrainingDomain(p["domain"]),
            label=p["label"], visibility=HudVisibility(p["visibility"]),
            source_video=p["source_video"], source_frame=int(p["source_frame"]),
            roi_id=p["roi_id"], image_path=p["image_path"], source_ref=p["source_ref"],
            group=p.get("group", "normal"), notes=p.get("notes", ""),
            registration_origin=p.get("registration_origin", "VIDEO_SINGLE"),
            state=TrainingReviewState(p.get("state", "PREVIEWED")), sha256=p["sha256"],
        )

    def _with_state(self, current: StagedTrainingSample, state: TrainingReviewState) -> StagedTrainingSample:
        return StagedTrainingSample(
            staging_id=current.staging_id, domain=current.domain, label=current.label,
            visibility=current.visibility, source_video=current.source_video,
            source_frame=current.source_frame, roi_id=current.roi_id,
            image_path=current.image_path, source_ref=current.source_ref,
            group=current.group, notes=current.notes, registration_origin=current.registration_origin,
            state=state, sha256=current.sha256,
        )

    def _write_receipt(self, staged: StagedTrainingSample) -> None:
        directory = self.staging_root / staged.staging_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0.0", "staging_id": staged.staging_id,
            "domain": staged.domain.value, "label": staged.label,
            "visibility": staged.visibility.value, "source_video": staged.source_video,
            "source_frame": staged.source_frame, "roi_id": staged.roi_id,
            "image_path": staged.image_path, "source_ref": staged.source_ref,
            "group": staged.group, "notes": staged.notes,
            "registration_origin": staged.registration_origin, "state": staged.state.value,
            "sha256": staged.sha256,
        }
        target = directory / "receipt.json"
        fd, raw_temp = tempfile.mkstemp(prefix=".receipt.", suffix=".tmp", dir=directory)
        os.close(fd)
        temp = Path(raw_temp)
        try:
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()


class TrainingDataReviewService:
    def __init__(self, manifest: VisualTrainingManifest) -> None:
        self.manifest = manifest

    def delete_exact(self, *, image_path: str, label: str) -> bool:
        values = list(self.manifest.list())
        kept = [x for x in values if not (x.image_path == image_path and x.label == label)]
        if len(kept) == len(values):
            return False
        self.manifest._write(kept)
        return True

    def relabel_exact(self, *, image_path: str, old_label: str, new_label: str) -> bool:
        if not new_label.strip():
            raise ValueError("新しいラベルを入力してください。")
        values = list(self.manifest.list())
        out = []
        changed = False
        for item in values:
            if item.image_path == image_path and item.label == old_label:
                out.append(VisualTrainingSample(
                    domain=item.domain, label=new_label.strip(), image_path=item.image_path,
                    group=item.group, source_ref=item.source_ref, notes=item.notes,
                    registration_origin=item.registration_origin, slot=item.slot,
                    display_state=item.display_state, source_video=item.source_video,
                    source_frame=item.source_frame,
                ))
                changed = True
            else:
                out.append(item)
        if changed:
            self.manifest._write(out)
        return changed
