"""TASK-012 deterministic EDITOR_WORK handoff and Cubase audio round-trip."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import wave
from typing import Any, Iterable

from .atomic import AtomicJsonWriter
from .edit_plan import EditPlan
from .errors import ProductError, ProductErrorCategory
from .render_qa import RenderQAReport
from .resolve_assembly import ResolveAssemblyResult
from .serialization import canonical_json_bytes, sha256_bytes


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _safe_source(path: str | Path, *, label: str) -> Path:
    source = Path(path)
    if source.is_symlink() or not source.is_file() or source.stat().st_size <= 0:
        raise ProductError(
            "ERR_HANDOFF_SOURCE_INVALID",
            f"{label} must be a non-empty regular non-symlink file",
            ProductErrorCategory.VALIDATION,
        )
    return source.resolve()


@dataclass(frozen=True, slots=True)
class HandoffFile:
    role: str
    relative_path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class EditorHandoffManifest:
    handoff_id: str
    edit_plan_sha256: str
    assembly_sha256: str
    render_qa_report_sha256: str
    files: tuple[HandoffFile, ...]
    cubase_roundtrip_enabled: bool

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "handoff_version": "1.0.0",
            "task_owner": "TASK-012",
            "handoff_id": self.handoff_id,
            "editor_work_root": ".",
            "edit_plan_sha256": self.edit_plan_sha256,
            "assembly_sha256": self.assembly_sha256,
            "render_qa_report_sha256": self.render_qa_report_sha256,
            "files": [item.to_dict() for item in self.files],
            "cubase_roundtrip": {
                "enabled": self.cubase_roundtrip_enabled,
                "export_directory": "AUDIO_ROUNDTRIP/EXPORT",
                "return_directory": "AUDIO_ROUNDTRIP/RETURN",
                "canonical_return_manifest": "AUDIO_ROUNDTRIP/audio-roundtrip-return.json",
                "automatic_project_conversion_promised": False,
            },
            "absolute_paths_persisted": False,
        }
        body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class EditorHandoffService:
    @staticmethod
    def prepare(
        destination_root: str | Path,
        *,
        edit_plan: EditPlan,
        assembly_result: ResolveAssemblyResult,
        render_qa: RenderQAReport,
        render_path: str | Path,
        subtitle_srt_path: str | Path | None = None,
        resolve_project_snapshot_path: str | Path | None = None,
        audio_roundtrip_exports: Iterable[str | Path] = (),
    ) -> tuple[Path, EditorHandoffManifest]:
        if not edit_plan.ready_for_assembly:
            raise ProductError(
                "ERR_HANDOFF_EDIT_PLAN_NOT_APPROVED",
                "EDITOR_WORK handoff requires an approved TASK-007 Edit Plan",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        if assembly_result.status not in {"APPLIED", "ALREADY_APPLIED"}:
            raise ProductError(
                "ERR_HANDOFF_ASSEMBLY_NOT_COMPLETE",
                "EDITOR_WORK handoff requires a completed TASK-010 assembly",
                ProductErrorCategory.STATE,
            )
        if render_qa.status != "PASS":
            raise ProductError(
                "ERR_HANDOFF_RENDER_QA_FAILED",
                "EDITOR_WORK handoff requires a passing TASK-011 Render QA report",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )

        render = _safe_source(render_path, label="render")
        if _sha256_file(render) != render_qa.artifact_sha256:
            raise ProductError(
                "ERR_HANDOFF_RENDER_HASH_MISMATCH",
                "render file changed after TASK-011 QA",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        edit_dict = edit_plan.to_dict()
        qa_dict = render_qa.to_dict()
        seed = {
            "edit_plan_sha256": edit_dict["plan_sha256"],
            "assembly_sha256": assembly_result.assembly_sha256,
            "render_qa_report_sha256": qa_dict["report_sha256"],
        }
        handoff_id = "EDITOR_WORK_" + sha256_bytes(canonical_json_bytes(seed)).split(":", 1)[1][:12].upper()
        destination = Path(destination_root).resolve()
        root = destination / handoff_id
        if root.exists():
            raise ProductError(
                "ERR_HANDOFF_DESTINATION_EXISTS",
                "deterministic EDITOR_WORK destination already exists; choose another parent or inspect the existing handoff",
                ProductErrorCategory.STATE,
                details={"handoff_id": handoff_id},
            )
        subtitle = _safe_source(subtitle_srt_path, label="subtitle SRT") if subtitle_srt_path is not None else None
        snapshot = (
            _safe_source(resolve_project_snapshot_path, label="Resolve project snapshot")
            if resolve_project_snapshot_path is not None
            else None
        )
        exports = tuple(_safe_source(item, label="audio round-trip export") for item in audio_roundtrip_exports)

        destination.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{handoff_id}.", dir=destination))
        published = False
        try:
            (staging / "MANIFESTS").mkdir()
            (staging / "RENDER").mkdir()
            (staging / "SUBTITLES").mkdir()
            (staging / "RESOLVE").mkdir()
            (staging / "AUDIO_ROUNDTRIP" / "EXPORT").mkdir(parents=True)
            (staging / "AUDIO_ROUNDTRIP" / "RETURN").mkdir()

            AtomicJsonWriter.write(staging / "MANIFESTS" / "edit-plan.json", edit_dict)
            AtomicJsonWriter.write(staging / "MANIFESTS" / "resolve-assembly-report.json", assembly_result.to_dict())
            AtomicJsonWriter.write(staging / "MANIFESTS" / "render-qa.json", qa_dict)

            files: list[HandoffFile] = []

            def register_existing(role: str, relative: str) -> None:
                target = staging / relative
                files.append(HandoffFile(role, relative.replace("\\", "/"), _sha256_file(target), target.stat().st_size))

            register_existing("EDIT_PLAN", "MANIFESTS/edit-plan.json")
            register_existing("RESOLVE_ASSEMBLY_REPORT", "MANIFESTS/resolve-assembly-report.json")
            register_existing("RENDER_QA", "MANIFESTS/render-qa.json")

            render_target = staging / "RENDER" / render.name
            shutil.copy2(render, render_target)
            register_existing("RENDER_MASTER", f"RENDER/{render.name}")

            if subtitle is not None:
                target = staging / "SUBTITLES" / subtitle.name
                shutil.copy2(subtitle, target)
                register_existing("SUBTITLE_SRT", f"SUBTITLES/{subtitle.name}")

            if snapshot is not None:
                target = staging / "RESOLVE" / snapshot.name
                shutil.copy2(snapshot, target)
                register_existing("RESOLVE_PROJECT_SNAPSHOT", f"RESOLVE/{snapshot.name}")

            for index, audio in enumerate(exports, start=1):
                name = f"{index:02d}_{audio.name}"
                target = staging / "AUDIO_ROUNDTRIP" / "EXPORT" / name
                shutil.copy2(audio, target)
                register_existing("AUDIO_ROUNDTRIP_EXPORT", f"AUDIO_ROUNDTRIP/EXPORT/{name}")

            manifest = EditorHandoffManifest(
                handoff_id=handoff_id,
                edit_plan_sha256=edit_dict["plan_sha256"],
                assembly_sha256=assembly_result.assembly_sha256,
                render_qa_report_sha256=qa_dict["report_sha256"],
                files=tuple(files),
                cubase_roundtrip_enabled=bool(exports),
            )
            AtomicJsonWriter.write(staging / "editor-handoff-manifest.json", manifest.to_dict())
            staging.replace(root)
            published = True
        finally:
            if not published and staging.exists():
                shutil.rmtree(staging)
        return root, manifest

    @staticmethod
    def register_cubase_return(
        editor_work_root: str | Path,
        returned_wav_path: str | Path,
        *,
        expected_duration_us: int,
        duration_tolerance_ms: int = 100,
    ) -> dict[str, Any]:
        root = Path(editor_work_root).resolve()
        manifest_path = root / "editor-handoff-manifest.json"
        if not manifest_path.is_file():
            raise ProductError(
                "ERR_HANDOFF_MANIFEST_MISSING",
                "EDITOR_WORK manifest is missing",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_HANDOFF_MANIFEST_INVALID",
                "EDITOR_WORK manifest cannot be read",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not manifest.get("cubase_roundtrip", {}).get("enabled"):
            raise ProductError(
                "ERR_HANDOFF_AUDIO_ROUNDTRIP_NOT_ENABLED",
                "this handoff was not prepared for a Cubase audio round-trip",
                ProductErrorCategory.AUTHORIZATION,
            )
        source = _safe_source(returned_wav_path, label="Cubase return WAV")
        try:
            with wave.open(str(source), "rb") as wav:
                sample_rate = wav.getframerate()
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                frames = wav.getnframes()
        except (wave.Error, EOFError) as exc:
            raise ProductError(
                "ERR_HANDOFF_AUDIO_RETURN_NOT_PCM_WAV",
                "Cubase return must be a readable PCM WAV",
                ProductErrorCategory.VALIDATION,
            ) from exc
        if sample_rate != 48_000:
            raise ProductError(
                "ERR_HANDOFF_AUDIO_RETURN_SAMPLE_RATE",
                "Cubase return WAV must use 48 kHz sample rate",
                ProductErrorCategory.VALIDATION,
                details={"sample_rate": sample_rate},
            )
        if not 1 <= channels <= 32 or sample_width not in {2, 3, 4}:
            raise ProductError(
                "ERR_HANDOFF_AUDIO_RETURN_FORMAT",
                "Cubase return WAV has an unsupported PCM channel/sample-width layout",
                ProductErrorCategory.VALIDATION,
                details={"channels": channels, "sample_width_bytes": sample_width},
            )
        observed_duration_us = int(frames * 1_000_000 / sample_rate)
        delta_us = abs(observed_duration_us - expected_duration_us)
        if delta_us > duration_tolerance_ms * 1000:
            raise ProductError(
                "ERR_HANDOFF_AUDIO_RETURN_DURATION",
                "Cubase return WAV duration is outside the allowed round-trip tolerance",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"delta_us": delta_us, "tolerance_us": duration_tolerance_ms * 1000},
            )

        target = root / "AUDIO_ROUNDTRIP" / "RETURN" / "cubase-return.wav"
        if target.exists():
            raise ProductError(
                "ERR_HANDOFF_AUDIO_RETURN_EXISTS",
                "a Cubase return is already registered for this handoff",
                ProductErrorCategory.STATE,
            )
        shutil.copy2(source, target)
        record = {
            "roundtrip_version": "1.0.0",
            "task_owner": "TASK-012",
            "daw": "CUBASE",
            "relative_path": "AUDIO_ROUNDTRIP/RETURN/cubase-return.wav",
            "sha256": _sha256_file(target),
            "size_bytes": target.stat().st_size,
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width_bytes": sample_width,
            "duration_us": observed_duration_us,
            "duration_delta_us": delta_us,
            "status": "ACCEPTED",
            "automatic_cubase_project_conversion": False,
        }
        record["record_sha256"] = sha256_bytes(canonical_json_bytes(record))
        AtomicJsonWriter.write(root / "AUDIO_ROUNDTRIP" / "audio-roundtrip-return.json", record)
        return record
