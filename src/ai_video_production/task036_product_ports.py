"""Product-service ports for the trusted TASK-036 pre-edit runtime."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Iterator, Protocol

from .assets import AssetType, AudioRightsStatus, PermissionState, RetentionClass, RightsStatus
from .cut_candidates import (
    CutCandidateAnalyzer,
    CutCandidateConfig,
    CutCandidateManifest,
    CutCandidatePublicationService,
    FfmpegSilenceDetector,
)
from .desktop_media_workflow import IngestedMediaIdentity
from .errors import ProductError, ProductErrorCategory
from .faster_whisper_asr import FasterWhisperProvider, LocalTranscriptionService
from .ingest import AssetIngestRequest, AssetIngestService
from .local_comfy_image_generation_port import _PinnedDirectory
from .serialization import canonical_json_bytes, sha256_bytes
from .store import SQLiteProductStore
from .subtitles import TranscriptManifest, TranscriptSegment
from .task036_pre_edit_runtime import LocalTranscriptionOutcome
from .timebase import FrameRate


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(slots=True)
class Task036AssetIngestPort:
    """Reuse TASK-003 ingest with trusted rights and Project bindings."""

    service: AssetIngestService
    production_job_id: str
    owner: str
    asset_type: AssetType = AssetType.VIDEO
    rights_status: RightsStatus = RightsStatus.OWNED
    retention_class: RetentionClass = RetentionClass.STANDARD
    commercial_use: PermissionState = PermissionState.UNKNOWN
    derivative_allowed: PermissionState = PermissionState.UNKNOWN
    reuse_allowed: PermissionState = PermissionState.ALLOWED
    audio_rights_status: AudioRightsStatus = AudioRightsStatus.NOT_APPLICABLE

    def ingest_local_media(self, source_path: Path) -> IngestedMediaIdentity:
        source = source_path.resolve()
        checksum = _file_sha256(source)
        result = self.service.ingest(
            AssetIngestRequest(
                production_job_id=self.production_job_id,
                source_path=source,
                asset_type=self.asset_type,
                rights_status=self.rights_status,
                owner=self.owner,
                idempotency_key=f"task036-media-{checksum}",
                retention_class=self.retention_class,
                commercial_use=self.commercial_use,
                derivative_allowed=self.derivative_allowed,
                reuse_allowed=self.reuse_allowed,
                audio_rights_status=self.audio_rights_status,
            )
        )
        canonical_source = self.service.resolver.resolve(result.asset.logical_uri)
        if not isinstance(canonical_source, Path):
            raise ProductError(
                "ERR_TASK036_CANONICAL_ASSET_PATH_INVALID",
                "TASK-003 canonical Asset did not resolve to a managed local file",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return IngestedMediaIdentity(result.asset.asset_id, result.asset.checksum, canonical_source)


@dataclass(slots=True)
class Task036LocalTranscriptionPort:
    """Reuse TASK-006 FasterWhisper publication with fixed local settings."""

    provider: FasterWhisperProvider
    output_directory: Path
    store: SQLiteProductStore
    production_job_id: str
    language: str | None = None
    timeline_rate: FrameRate = FrameRate(30000, 1001)

    _TRANSCRIPT_MAX_BYTES = 32 * 1024 * 1024
    _SRT_MAX_BYTES = 64 * 1024 * 1024
    _REPORT_MAX_BYTES = 64 * 1024
    _PUBLICATION_SET_MAX_BYTES = 16 * 1024

    def _authorize_provider(self) -> tuple[str, str, str]:
        provider_id = getattr(self.provider, "provider_id", None)
        model_id = getattr(self.provider, "model_id", None)
        config = getattr(self.provider, "config", None)
        model = getattr(config, "model", None)
        device = getattr(config, "device", None)
        compute_type = getattr(config, "compute_type", None)
        beam_size = getattr(config, "beam_size", None)
        vad_filter = getattr(config, "vad_filter", None)
        cache_directory = getattr(config, "cache_directory", None)
        if (
            provider_id != "faster-whisper"
            or not isinstance(model_id, str)
            or not model_id.strip()
            or not isinstance(model, str)
            or not model.strip()
            or device not in {"auto", "cpu", "cuda"}
            or not isinstance(compute_type, str)
            or not compute_type.strip()
            or not isinstance(beam_size, int)
            or isinstance(beam_size, bool)
            or not 1 <= beam_size <= 20
            or not isinstance(vad_filter, bool)
            or (cache_directory is not None and not isinstance(cache_directory, (str, Path)))
            or getattr(config, "allow_model_download", None) is not False
            or (self.language is not None and not isinstance(self.language, str))
        ):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PROVIDER_NOT_AUTHORIZED",
                "Local transcription requires fixed FasterWhisper with model download disabled",
                ProductErrorCategory.AUTHORIZATION,
            )
        cache_identity = (
            None
            if cache_directory is None
            else sha256_bytes(str(cache_directory).encode("utf-8"))
        )
        contract = {
            "contract_version": "1.0.0",
            "provider_id": provider_id,
            "model_id": model_id,
            "model_config_sha256": sha256_bytes(model.encode("utf-8")),
            "device": device,
            "compute_type": compute_type,
            "beam_size": beam_size,
            "vad_filter": vad_filter,
            "allow_model_download": False,
            "cache_directory_sha256": cache_identity,
            "language": self.language,
            "timeline_rate": {
                "numerator": self.timeline_rate.numerator,
                "denominator": self.timeline_rate.denominator,
            },
        }
        return provider_id, model_id, sha256_bytes(canonical_json_bytes(contract))

    def _operation_key(
        self,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> str:
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project_id must be non-empty")
        if not isinstance(source_asset_id, str) or not source_asset_id.strip():
            raise ValueError("source_asset_id must be non-empty")
        provider_id, model_id, execution_config_sha256 = self._authorize_provider()
        body = {
            "contract": "task036-local-transcription/1.0.0",
            "project_id": project_id,
            "source_asset_id": source_asset_id,
            "source_asset_sha256": source_asset_sha256,
            "provider_id": provider_id,
            "model_id": model_id,
            "execution_config_sha256": execution_config_sha256,
            "model_download_authorized": False,
        }
        return "task036-transcription-" + hashlib.sha256(canonical_json_bytes(body)).hexdigest()

    def _slot_key(self, project_id: str) -> str:
        body = {
            "contract": "task036-local-transcription-fixed-output-slot/1.0.0",
            "project_id": project_id,
            "production_job_id": self.production_job_id,
        }
        return "task036-transcription-slot-" + hashlib.sha256(canonical_json_bytes(body)).hexdigest()

    def _acquire_output_slot(
        self,
        project_id: str,
        operation_id: str,
        *,
        allow_existing_owner: bool = False,
    ):
        slot, _created = self.store.reserve_operation(
            self.production_job_id,
            "task036.local_transcription_output_slot",
            self._slot_key(project_id),
        )
        if (
            allow_existing_owner
            and slot.status == "IN_PROGRESS"
            and slot.result_ref == operation_id
        ):
            return slot
        acquired, changed = self.store.compare_and_set_operation_status(
            slot.operation_id,
            expected_statuses=("PENDING",),
            expected_result_refs=(slot.result_ref,),
            status="IN_PROGRESS",
            result_ref=operation_id,
            replace_result_ref=True,
        )
        if not changed or acquired.result_ref != operation_id:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OUTPUT_SLOT_BUSY",
                "Another transcription owns the fixed Product output slot",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        return acquired

    def _release_output_slot(self, slot_operation_id: str, operation_id: str) -> None:
        released, changed = self.store.compare_and_set_operation_status(
            slot_operation_id,
            expected_statuses=("IN_PROGRESS",),
            expected_result_refs=(operation_id,),
            status="PENDING",
            result_ref=operation_id,
            replace_result_ref=True,
        )
        if not changed or released.status != "PENDING":
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OUTPUT_SLOT_STALE",
                "Transcription output slot changed before binding completion",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )

    @staticmethod
    def _snapshot_source(source: Path, expected_sha256: str, destination: Path) -> Path:
        """Copy bytes from one stable source descriptor; Provider opens only the copy."""

        try:
            before = os.lstat(source)
            if not stat.S_ISREG(before.st_mode):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_SOURCE_INVALID",
                    "Canonical Asset source is unsafe",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            descriptor = os.open(
                source,
                os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or (
                    opened.st_dev, opened.st_ino
                ) != (before.st_dev, before.st_ino):
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_SOURCE_INVALID",
                        "Canonical Asset identity changed before snapshot",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                digest = hashlib.sha256()
                with os.fdopen(descriptor, "rb", closefd=False) as reader, destination.open("xb") as writer:
                    while True:
                        chunk = reader.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        digest.update(chunk)
                        writer.write(chunk)
                    writer.flush()
                    os.fsync(writer.fileno())
                after = os.fstat(descriptor)
                if (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
                ) != (
                    opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns
                ):
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_SOURCE_CHANGED",
                        "Canonical Asset changed while snapshotting",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_SOURCE_INVALID",
                "Canonical Asset could not be snapshotted",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if "sha256:" + digest.hexdigest() != expected_sha256:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_SOURCE_MISMATCH",
                "Canonical Asset bytes do not match the bound Asset SHA",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return destination

    @staticmethod
    @contextmanager
    def _provider_snapshot(
        source: Path,
        expected_sha256: str,
        destination: Path,
    ) -> Iterator[Path]:
        """Yield an immutable-by-authority Provider path for the copied Asset bytes."""

        snapshot = Task036LocalTranscriptionPort._snapshot_source(
            source, expected_sha256, destination,
        )
        if os.name == "nt":
            from ctypes import wintypes

            create_file = ctypes.windll.kernel32.CreateFileW
            create_file.argtypes = (
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.HANDLE,
            )
            create_file.restype = wintypes.HANDLE
            close_handle = ctypes.windll.kernel32.CloseHandle
            close_handle.argtypes = (wintypes.HANDLE,)
            close_handle.restype = wintypes.BOOL
            handle = create_file(
                str(snapshot),
                0x80000000,  # GENERIC_READ
                0x00000001,  # FILE_SHARE_READ only: no write/delete/rename
                None,
                3,  # OPEN_EXISTING
                0x00000080,  # FILE_ATTRIBUTE_NORMAL
                None,
            )
            if handle in (None, wintypes.HANDLE(-1).value):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_SOURCE_INVALID",
                    "Stable Provider snapshot could not be pinned",
                    ProductErrorCategory.DATA_INTEGRITY,
                )

            def hash_pinned_handle() -> str:
                set_pointer = ctypes.windll.kernel32.SetFilePointerEx
                set_pointer.argtypes = (
                    wintypes.HANDLE, ctypes.c_longlong,
                    ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD,
                )
                set_pointer.restype = wintypes.BOOL
                read_file = ctypes.windll.kernel32.ReadFile
                read_file.argtypes = (
                    wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                    ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
                )
                read_file.restype = wintypes.BOOL
                if not set_pointer(handle, 0, None, 0):
                    raise OSError("could not rewind pinned Provider snapshot")
                digest = hashlib.sha256()
                buffer = ctypes.create_string_buffer(4 * 1024 * 1024)
                while True:
                    count = wintypes.DWORD()
                    if not read_file(handle, buffer, len(buffer), ctypes.byref(count), None):
                        raise OSError("could not read pinned Provider snapshot")
                    if count.value == 0:
                        break
                    digest.update(buffer.raw[:count.value])
                return "sha256:" + digest.hexdigest()

            try:
                if hash_pinned_handle() != expected_sha256:
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_SOURCE_CHANGED",
                        "Stable Provider snapshot changed before inference",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                yield snapshot
                if hash_pinned_handle() != expected_sha256:
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_SOURCE_CHANGED",
                        "Stable Provider snapshot changed during inference",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
            finally:
                close_handle(handle)
            return

        descriptor = os.open(
            snapshot,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_SOURCE_INVALID",
                    "Stable Provider snapshot is not a regular file",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            descriptor_path = Path(f"/proc/{os.getpid()}/fd/{descriptor}")
            if not descriptor_path.exists():
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_STABLE_INPUT_UNAVAILABLE",
                    "This platform cannot expose a stable Provider input descriptor",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                )
            yield descriptor_path
            os.lseek(descriptor, 0, os.SEEK_SET)
            digest = hashlib.sha256()
            while True:
                chunk = os.read(descriptor, 4 * 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
            after = os.fstat(descriptor)
            if (
                "sha256:" + digest.hexdigest() != expected_sha256
                or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
            ):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_SOURCE_CHANGED",
                    "Stable Provider snapshot changed during inference",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        finally:
            os.close(descriptor)

    @staticmethod
    def _snapshot_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        return "sha256:" + digest.hexdigest()

    @contextmanager
    def _pinned_output_directory(self) -> Iterator[_PinnedDirectory]:
        """Pin Project root first, then open the fixed output child relative to it."""

        parent = self.output_directory.parent
        if parent.is_symlink() or not parent.is_dir():
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PRIVATE_PATH_INVALID",
                "Trusted Product root is unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            with _PinnedDirectory(parent) as project:
                with project.pin_child(self.output_directory.name) as output:
                    yield output
                    output.assert_current()
                project.assert_current()
        except ProductError as exc:
            if exc.code.startswith("ERR_GENERATION_COMFY_IMAGE_"):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_PRIVATE_PATH_INVALID",
                    "Trusted transcription directory identity is unsafe",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc
            raise

    @staticmethod
    def _load_completed_transcript(publication_root: Path, source_asset_id: str) -> TranscriptManifest:
        if publication_root.is_symlink() or not publication_root.is_dir():
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Transcription publication directory is invalid", ProductErrorCategory.DATA_INTEGRITY)
        transcript_path = publication_root / "transcript.json"
        report_path = publication_root / "transcription-report.json"
        if any(path.is_symlink() or not path.is_file() for path in (transcript_path, report_path)):
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Transcription publication is incomplete", ProductErrorCategory.STATE)
        try:
            raw = json.loads(transcript_path.read_text(encoding="utf-8"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Transcription publication is unreadable", ProductErrorCategory.STATE) from exc
        if not isinstance(raw, dict) or set(raw) != {"manifest_version", "source_asset_id", "language", "provider_id", "model_id", "segments", "manifest_sha256"}:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Transcript manifest schema is invalid", ProductErrorCategory.DATA_INTEGRITY)
        body = dict(raw)
        checksum = body.pop("manifest_sha256")
        if checksum != sha256_bytes(canonical_json_bytes(body)) or raw.get("source_asset_id") != source_asset_id:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Transcript manifest identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            segments = []
            for item in raw.get("segments", []):
                if not isinstance(item, dict) or set(item) != {"segment_id", "range_us", "text", "confidence", "speaker"} or not isinstance(item.get("range_us"), dict):
                    raise ValueError("Transcript segment schema is invalid")
                segments.append(TranscriptSegment(item["segment_id"], item["range_us"].get("start"), item["range_us"].get("end_exclusive"), item["text"], item["confidence"], item["speaker"]))
            transcript = TranscriptManifest(raw["source_asset_id"], raw["language"], raw["provider_id"], raw["model_id"], tuple(segments))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                "Transcript publication fields are invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if transcript.to_dict()["manifest_sha256"] != checksum:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Transcript manifest reconstruction failed", ProductErrorCategory.DATA_INTEGRITY)
        if (
            not isinstance(report, dict)
            or report.get("ok") is not True
            or report.get("source_asset_id") != source_asset_id
            or report.get("transcript_file") != "transcript.json"
            or report.get("model_download_authorized") is not False
            or report.get("network_used_for_inference") is not False
        ):
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Transcription report identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        return transcript

    def _publication_bytes(self) -> dict[str, bytes]:
        if self.output_directory.is_symlink() or not self.output_directory.is_dir():
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PRIVATE_PATH_INVALID",
                "Trusted transcription output root is unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            with self._pinned_output_directory() as output:
                values = {
                    "transcript.json": output.read(
                        "transcript.json", max_bytes=self._TRANSCRIPT_MAX_BYTES,
                    ),
                    "subtitles.srt": output.read(
                        "subtitles.srt", max_bytes=self._SRT_MAX_BYTES,
                    ),
                    "transcription-report.json": output.read(
                        "transcription-report.json", max_bytes=self._REPORT_MAX_BYTES,
                    ),
                }
                output.assert_current()
        except (OSError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PUBLICATION_INVALID",
                "Trusted transcription publication is unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return values

    def _preflight_output_targets(self) -> None:
        bounds = {
            "transcript.json": self._TRANSCRIPT_MAX_BYTES,
            "subtitles.srt": self._SRT_MAX_BYTES,
            "transcription-report.json": self._REPORT_MAX_BYTES,
        }
        if self.output_directory.is_symlink() or not self.output_directory.is_dir():
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PRIVATE_PATH_INVALID",
                "Trusted transcription output root is unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            with self._pinned_output_directory() as output:
                for name, maximum in bounds.items():
                    if output.child_exists(name):
                        output.read(name, max_bytes=maximum)
                if output.child_exists(".task036-publications"):
                    with output.pin_child(".task036-publications") as generations:
                        generations.assert_current()
                output.assert_current()
        except (OSError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PUBLICATION_INVALID",
                "Trusted transcription publication target is unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    def _preflight_generation_target(self, operation_id: str) -> None:
        """Create/pin the exact private generation directory before Provider use."""

        try:
            with self._pinned_output_directory() as output:
                output.mkdir(".task036-publications", exist_ok=True)
                with output.pin_child(".task036-publications") as generations:
                    generations.mkdir(operation_id, exist_ok=True)
                    with generations.pin_child(operation_id) as generation:
                        generation.assert_current()
                    generations.assert_current()
                output.assert_current()
        except (OSError, ValueError, ProductError) as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PUBLICATION_SET_INVALID",
                "Immutable transcription target is unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    def _validate_publication(
        self,
        values: dict[str, bytes],
        *,
        source_asset_id: str,
        provider_id: str,
        model_id: str,
    ) -> TranscriptManifest:
        with tempfile.TemporaryDirectory(prefix="bai-task036-publication-check-") as raw_temp:
            observed_root = Path(raw_temp) / "observed"
            observed_root.mkdir()
            for name, value in values.items():
                (observed_root / name).write_bytes(value)
            transcript = self._load_completed_transcript(observed_root, source_asset_id)
            if transcript.provider_id != provider_id or transcript.model_id != model_id:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                    "Transcript Provider identity differs from the durable operation",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            try:
                report = json.loads(values["transcription-report.json"].decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                    "Transcription report is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc
            exact_report_keys = {
                "report_version", "ok", "source_asset_id", "provider_id", "model_id",
                "language", "segment_count", "subtitle_cue_count", "transcript_file",
                "subtitle_file", "transcript_text_in_report", "network_used_for_inference",
                "model_download_authorized",
            }
            if (
                not isinstance(report, dict)
                or set(report) != exact_report_keys
                or report.get("report_version") != "1.0.0"
                or report.get("provider_id") != provider_id
                or report.get("model_id") != model_id
                or report.get("language") != transcript.language
                or report.get("segment_count") != len(transcript.segments)
                or report.get("transcript_text_in_report") is not False
            ):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                    "Transcription report and Transcript identities differ",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            expected = LocalTranscriptionService.publish(
                transcript,
                Path(raw_temp) / "expected",
                timeline_rate=self.timeline_rate,
                model_download_authorized=False,
            )
            expected_values = {
                "transcript.json": expected.transcript_path.read_bytes(),
                "subtitles.srt": expected.subtitle_path.read_bytes(),
                "transcription-report.json": expected.report_path.read_bytes(),
            }
            if values != expected_values:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                    "Transcription publication bytes are not canonical",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        return transcript

    @staticmethod
    def _publication_hashes(values: dict[str, bytes]) -> dict[str, str]:
        return {name: sha256_bytes(raw) for name, raw in sorted(values.items())}

    def _publication_set_body(
        self,
        values: dict[str, bytes],
        *,
        project_id: str,
        operation_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        provider_id: str,
        model_id: str,
        execution_config_sha256: str,
        transcript_manifest_sha256: str,
    ) -> dict[str, object]:
        return {
            "publication_set_version": "1.0.0",
            "project_id": project_id,
            "operation_id": operation_id,
            "source_asset_id": source_asset_id,
            "source_asset_sha256": source_asset_sha256,
            "provider_id": provider_id,
            "model_id": model_id,
            "execution_config_sha256": execution_config_sha256,
            "transcript_manifest_sha256": transcript_manifest_sha256,
            "files": self._publication_hashes(values),
        }

    def _store_immutable_publication_set(
        self,
        values: dict[str, bytes],
        *,
        project_id: str,
        operation_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        provider_id: str,
        model_id: str,
        execution_config_sha256: str,
        transcript_manifest_sha256: str,
    ) -> str:
        body = self._publication_set_body(
            values,
            project_id=project_id,
            operation_id=operation_id,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            provider_id=provider_id,
            model_id=model_id,
            execution_config_sha256=execution_config_sha256,
            transcript_manifest_sha256=transcript_manifest_sha256,
        )
        set_sha256 = sha256_bytes(canonical_json_bytes(body))
        document = {**body, "publication_set_sha256": set_sha256}
        bounds = {
            "transcript.json": self._TRANSCRIPT_MAX_BYTES,
            "subtitles.srt": self._SRT_MAX_BYTES,
            "transcription-report.json": self._REPORT_MAX_BYTES,
            "publication-set.json": self._PUBLICATION_SET_MAX_BYTES,
        }
        payloads = {**values, "publication-set.json": canonical_json_bytes(document)}
        try:
            with self._pinned_output_directory() as output:
                output.mkdir(".task036-publications", exist_ok=True)
                with output.pin_child(".task036-publications") as generations:
                    generations.mkdir(operation_id, exist_ok=True)
                    with generations.pin_child(operation_id) as generation:
                        for index, (name, raw) in enumerate(payloads.items()):
                            if generation.child_exists(name):
                                if generation.read(name, max_bytes=bounds[name]) != raw:
                                    raise ProductError(
                                        "ERR_TASK036_TRANSCRIPTION_PUBLICATION_SET_CONFLICT",
                                        "Immutable transcription publication differs",
                                        ProductErrorCategory.DATA_INTEGRITY,
                                    )
                            else:
                                generation.write_atomic(f".{index}.tmp", name, raw)
                        generation.assert_current()
                    generations.assert_current()
                output.assert_current()
        except (OSError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PUBLICATION_SET_INVALID",
                "Immutable transcription publication could not be stored",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return set_sha256

    def _load_immutable_publication_set(
        self,
        operation_id: str,
        expected_set_sha256: str,
        *,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        provider_id: str,
        model_id: str,
        execution_config_sha256: str,
    ) -> tuple[dict[str, bytes], TranscriptManifest]:
        bounds = {
            "transcript.json": self._TRANSCRIPT_MAX_BYTES,
            "subtitles.srt": self._SRT_MAX_BYTES,
            "transcription-report.json": self._REPORT_MAX_BYTES,
        }
        try:
            with self._pinned_output_directory() as output:
                with output.pin_child(".task036-publications") as generations:
                    with generations.pin_child(operation_id) as generation:
                        values = {
                            name: generation.read(name, max_bytes=maximum)
                            for name, maximum in bounds.items()
                        }
                        raw_document = generation.read(
                            "publication-set.json", max_bytes=self._PUBLICATION_SET_MAX_BYTES,
                        )
                        generation.assert_current()
                    generations.assert_current()
                output.assert_current()
        except (OSError, ValueError, ProductError) as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                "Immutable transcription publication is missing or unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        try:
            document = json.loads(raw_document.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                "Immutable transcription publication manifest is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        expected_keys = {
            "publication_set_version", "project_id", "operation_id", "source_asset_id",
            "source_asset_sha256", "provider_id", "model_id", "execution_config_sha256",
            "transcript_manifest_sha256", "files", "publication_set_sha256",
        }
        if not isinstance(document, dict) or set(document) != expected_keys:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                "Immutable transcription publication manifest schema is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        body = dict(document)
        actual_set_sha256 = body.pop("publication_set_sha256")
        transcript = self._validate_publication(
            values,
            source_asset_id=source_asset_id,
            provider_id=provider_id,
            model_id=model_id,
        )
        expected_body = self._publication_set_body(
            values,
            project_id=project_id,
            operation_id=operation_id,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            provider_id=provider_id,
            model_id=model_id,
            execution_config_sha256=execution_config_sha256,
            transcript_manifest_sha256=transcript.to_dict()["manifest_sha256"],
        )
        if (
            body != expected_body
            or actual_set_sha256 != expected_set_sha256
            or sha256_bytes(canonical_json_bytes(body)) != expected_set_sha256
        ):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                "Immutable transcription publication identity differs from the operation",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return values, transcript

    def _promote_publication(
        self,
        publication_root: Path,
        operation_id: str,
        *,
        source_asset_id: str,
        provider_id: str,
        model_id: str,
    ) -> dict[str, bytes]:
        bounds = {
            "transcript.json": self._TRANSCRIPT_MAX_BYTES,
            "subtitles.srt": self._SRT_MAX_BYTES,
            "transcription-report.json": self._REPORT_MAX_BYTES,
        }
        try:
            with _PinnedDirectory(publication_root) as publication:
                values = {
                    name: publication.read(name, max_bytes=maximum)
                    for name, maximum in bounds.items()
                }
                publication.assert_current()
        except (OSError, ValueError, ProductError) as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RESULT_INVALID",
                "Local transcription publication is incomplete or unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        self._validate_publication(
            values,
            source_asset_id=source_asset_id,
            provider_id=provider_id,
            model_id=model_id,
        )
        if self.output_directory.is_symlink() or not self.output_directory.is_dir():
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PRIVATE_PATH_INVALID",
                "Trusted transcription output root is unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            with self._pinned_output_directory() as output:
                for index, name in enumerate(
                    ("transcript.json", "subtitles.srt", "transcription-report.json")
                ):
                    output.write_atomic(f".{operation_id}-{index}.tmp", name, values[name])
                output.assert_current()
        except (OSError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PUBLICATION_INVALID",
                "Trusted transcription publication could not be promoted safely",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return self._publication_bytes()

    def transcribe_local_media(
        self,
        *,
        project_id: str,
        source_path: Path,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> LocalTranscriptionOutcome:
        provider_id, model_id, execution_config_sha256 = self._authorize_provider()
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", source_asset_sha256):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_SOURCE_MISMATCH",
                "Canonical Asset SHA is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if self.output_directory.is_symlink() or not self.output_directory.is_dir():
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PRIVATE_PATH_INVALID",
                "Trusted transcription output root is unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        self._preflight_output_targets()
        operation_key = self._operation_key(
            project_id, source_asset_id, source_asset_sha256,
        )
        with tempfile.TemporaryDirectory(prefix="bai-task036-transcribe-") as raw_temp:
            temporary = Path(raw_temp)
            validated_snapshot = self._snapshot_source(
                source_path, source_asset_sha256, temporary / "canonical-source.media",
            )
            operation, _created = self.store.reserve_operation(
                self.production_job_id, "task036.local_transcription", operation_key,
            )
            if operation.status != "PENDING":
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RECOVERY_REQUIRED",
                    "Durable transcription already exists; explicit recovery is required",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                )
            self._preflight_generation_target(operation.operation_id)
            operation, claimed = self.store.compare_and_set_operation_status(
                operation.operation_id,
                expected_statuses=("PENDING",),
                status="IN_PROGRESS",
                increment_attempt=True,
            )
            if not claimed:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RECOVERY_REQUIRED",
                    "Durable transcription already exists; explicit recovery is required",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                )
            try:
                slot = self._acquire_output_slot(project_id, operation.operation_id)
            except BaseException as exc:
                code = (
                    exc.code
                    if isinstance(exc, ProductError)
                    and re.fullmatch(r"ERR_[A-Z0-9_]{1,120}", exc.code)
                    else "ERR_TASK036_TRANSCRIPTION_OUTPUT_SLOT_BUSY"
                )
                self.store.compare_and_set_operation_status(
                    operation.operation_id,
                    expected_statuses=("IN_PROGRESS",),
                    expected_result_refs=(None,),
                    status="PENDING",
                    last_error_code=code,
                    result_ref=None,
                    replace_result_ref=True,
                )
                raise
            try:
                with self._provider_snapshot(
                    validated_snapshot,
                    source_asset_sha256,
                    temporary / "provider-source.media",
                ) as provider_source:
                    publication = LocalTranscriptionService.run(
                        provider_source,
                        temporary / "publication",
                        provider=self.provider,
                        source_asset_id=source_asset_id,
                        language=self.language,
                        timeline_rate=self.timeline_rate,
                        include_word_timestamps=True,
                    )
                if (
                    publication.transcript.provider_id != provider_id
                    or publication.transcript.model_id != model_id
                ):
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_RESULT_INVALID",
                        "Provider returned a foreign Transcript identity",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                values = {
                    "transcript.json": publication.transcript_path.read_bytes(),
                    "subtitles.srt": publication.subtitle_path.read_bytes(),
                    "transcription-report.json": publication.report_path.read_bytes(),
                }
                transcript = self._validate_publication(
                    values,
                    source_asset_id=source_asset_id,
                    provider_id=provider_id,
                    model_id=model_id,
                )
                transcript_sha = transcript.to_dict()["manifest_sha256"]
                publication_set_sha256 = self._store_immutable_publication_set(
                    values,
                    project_id=project_id,
                    operation_id=operation.operation_id,
                    source_asset_id=source_asset_id,
                    source_asset_sha256=source_asset_sha256,
                    provider_id=provider_id,
                    model_id=model_id,
                    execution_config_sha256=execution_config_sha256,
                    transcript_manifest_sha256=transcript_sha,
                )
                partial, bound = self.store.compare_and_set_operation_status(
                    operation.operation_id,
                    expected_statuses=("IN_PROGRESS",),
                    expected_result_refs=(None,),
                    status="PARTIAL",
                    result_ref=publication_set_sha256,
                    replace_result_ref=True,
                )
                if not bound or partial.result_ref != publication_set_sha256:
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_COMPLETION_UNCERTAIN",
                        "Immutable publication exists but its durable identity did not bind",
                        ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                    )
                promoted = self._promote_publication(
                    publication.output_directory,
                    operation.operation_id,
                    source_asset_id=source_asset_id,
                    provider_id=provider_id,
                    model_id=model_id,
                )
                if promoted != values:
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_PUBLICATION_INVALID",
                        "Fixed publication differs from the immutable generation",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                completed, changed = self.store.compare_and_set_operation_status(
                    operation.operation_id,
                    expected_statuses=("PARTIAL",),
                    expected_result_refs=(publication_set_sha256,),
                    status="COMPLETED",
                    result_ref=publication_set_sha256,
                    replace_result_ref=True,
                )
                if not changed or completed.result_ref != publication_set_sha256:
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_COMPLETION_UNCERTAIN",
                        "Transcript publication completed but durable operation did not",
                        ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                    )
                return LocalTranscriptionOutcome(
                    transcript, True, False,
                    operation.operation_id, slot.operation_id, publication_set_sha256,
                )
            except BaseException as exc:
                code = (
                    exc.code
                    if isinstance(exc, ProductError)
                    and re.fullmatch(r"ERR_[A-Z0-9_]{1,120}", exc.code)
                    else "ERR_TASK036_TRANSCRIPTION_UNCERTAIN"
                )
                self.store.compare_and_set_operation_status(
                    operation.operation_id,
                    expected_statuses=("IN_PROGRESS",),
                    status="PARTIAL",
                    last_error_code=code,
                )
                raise

    def recover_local_media(self, *, project_id: str, source_path: Path, source_asset_id: str, source_asset_sha256: str) -> LocalTranscriptionOutcome:
        provider_id, model_id, execution_config_sha256 = self._authorize_provider()
        operation_key = self._operation_key(
            project_id, source_asset_id, source_asset_sha256,
        )
        operation = self.store.find_operation(self.production_job_id, operation_key)
        if operation is None or operation.status not in {"PARTIAL", "COMPLETED"}:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RECOVERY_NOT_AVAILABLE",
                "No durable transcription is available for recovery",
                ProductErrorCategory.STATE,
            )
        if operation.command_type != "task036.local_transcription":
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
                "Durable operation belongs to a different Product command",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        with tempfile.TemporaryDirectory(prefix="bai-task036-recover-") as raw_temp:
            self._snapshot_source(
                source_path, source_asset_sha256, Path(raw_temp) / "canonical-source.media",
            )
        if not isinstance(operation.result_ref, str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", operation.result_ref,
        ):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                "Durable transcription has no bound immutable publication",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        slot = self._acquire_output_slot(
            project_id, operation.operation_id, allow_existing_owner=True,
        )
        values, transcript = self._load_immutable_publication_set(
            operation.operation_id,
            operation.result_ref,
            project_id=project_id,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            provider_id=provider_id,
            model_id=model_id,
            execution_config_sha256=execution_config_sha256,
        )
        if operation.status == "COMPLETED":
            promoted = self._publication_bytes()
        else:
            with tempfile.TemporaryDirectory(prefix="bai-task036-recovery-promotion-") as raw_temp:
                publication_root = Path(raw_temp)
                for name, raw in values.items():
                    (publication_root / name).write_bytes(raw)
                promoted = self._promote_publication(
                    publication_root,
                    operation.operation_id,
                    source_asset_id=source_asset_id,
                    provider_id=provider_id,
                    model_id=model_id,
                )
        if promoted != values:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                "Fixed publication differs from the durable immutable generation",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if operation.status == "PARTIAL":
            completed, changed = self.store.compare_and_set_operation_status(
                operation.operation_id,
                expected_statuses=("PARTIAL",),
                expected_result_refs=(operation.result_ref,),
                status="COMPLETED",
                result_ref=operation.result_ref,
                replace_result_ref=True,
            )
            if not changed and (
                completed.status != "COMPLETED" or completed.result_ref != operation.result_ref
            ):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                    "Concurrent recovery changed the durable operation",
                    ProductErrorCategory.STATE,
                )
        return LocalTranscriptionOutcome(
            transcript, False, True,
            operation.operation_id, slot.operation_id, operation.result_ref,
        )

    def finalize_local_media_binding(
        self,
        *,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        transcript_manifest_sha256: str,
        operation_id: str,
        slot_operation_id: str,
        publication_set_sha256: str,
    ) -> None:
        provider_id, model_id, execution_config_sha256 = self._authorize_provider()
        operation = self.store.find_operation(
            self.production_job_id,
            self._operation_key(project_id, source_asset_id, source_asset_sha256),
        )
        if (
            operation is None
            or operation.operation_id != operation_id
            or operation.status != "COMPLETED"
            or operation.result_ref != publication_set_sha256
        ):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
                "Durable transcription changed before binding completion",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        values, transcript = self._load_immutable_publication_set(
            operation_id,
            publication_set_sha256,
            project_id=project_id,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            provider_id=provider_id,
            model_id=model_id,
            execution_config_sha256=execution_config_sha256,
        )
        if transcript.to_dict()["manifest_sha256"] != transcript_manifest_sha256:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
                "Bound Transcript differs from the immutable publication",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if self._publication_bytes() != values:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PUBLICATION_INVALID",
                "Fixed publication changed before binding completion",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        self._release_output_slot(slot_operation_id, operation_id)

    def recovery_required(
        self,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> bool:
        self._authorize_provider()
        operation = self.store.find_operation(
            self.production_job_id,
            self._operation_key(project_id, source_asset_id, source_asset_sha256),
        )
        if operation is not None and operation.command_type != "task036.local_transcription":
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
                "Durable operation belongs to a different Product command",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return operation is not None and operation.status in {
            "IN_PROGRESS", "PARTIAL", "COMPLETED",
        }


class AnalysisAudioBinding(Protocol):
    def analysis_audio_for(self, source_path: Path) -> Path: ...


@dataclass(frozen=True, slots=True)
class FixedAnalysisAudioBinding:
    """Bind normalized analysis WAV to one canonical managed Asset digest."""

    source_sha256: str
    analysis_audio_path: Path

    def __post_init__(self) -> None:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.source_sha256):
            raise ValueError("source_sha256 is invalid")

    def analysis_audio_for(self, source_path: Path) -> Path:
        observed = source_path
        if (
            observed.is_symlink()
            or not observed.is_file()
            or "sha256:" + _file_sha256(observed) != self.source_sha256
        ):
            raise ValueError("analysis audio binding does not match the managed Asset bytes")
        return self.analysis_audio_path.resolve()


@dataclass(slots=True)
class Task036CutCandidatePort:
    """Reuse TASK-024 with a trusted normalized-audio binding."""

    analysis_audio: AnalysisAudioBinding
    output_directory: Path
    config: CutCandidateConfig = CutCandidateConfig()
    detector: FfmpegSilenceDetector | None = None

    def generate_cut_candidates(
        self,
        *,
        source_path: Path,
        transcript: TranscriptManifest,
    ) -> CutCandidateManifest:
        manifest = CutCandidateAnalyzer.analyze(
            self.analysis_audio.analysis_audio_for(source_path),
            source_asset_id=transcript.source_asset_id,
            transcript=transcript,
            config=self.config,
            detector=self.detector,
        )
        CutCandidatePublicationService.publish(manifest, self.output_directory)
        return manifest
