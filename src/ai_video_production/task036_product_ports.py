"""Product-service ports for the trusted TASK-036 pre-edit runtime."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, Callable, Iterator, Protocol

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
from .faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider, LocalTranscriptionService
from .faster_whisper_reconciliation import build_execution_identity_for_config
from .faster_whisper_runtime_contract import (
    FasterWhisperRuntimeCapabilityObservationV1,
    FasterWhisperRuntimeDecisionV1,
    FasterWhisperRuntimeRequestV1,
    validate_runtime_pair,
)
from .faster_whisper_runtime_preflight import (
    FasterWhisperRuntimeCapabilityProbe,
    evaluate_runtime_preflight,
    resolve_runtime_decision,
)
from .ingest import AssetIngestRequest, AssetIngestService
from .local_comfy_image_generation_port import _PinnedDirectory
from .serialization import canonical_json_bytes, sha256_bytes
from .store import SQLiteProductStore
from .subtitles import TranscriptManifest, TranscriptSegment, TranscriptWord
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


@dataclass
class _Task036LocalTranscriptionOperationEngine:
    """One physical TASK-036 lifecycle, durable I/O, and publication engine."""

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

        snapshot = _Task036LocalTranscriptionOperationEngine._snapshot_source(
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
            version = raw.get("manifest_version")
            if version not in {"1.0.0", "1.1.0"} or not isinstance(raw.get("segments"), list):
                raise ValueError("Transcript manifest version is invalid")
            segments = []
            legacy_fields = {"segment_id", "range_us", "text", "confidence", "speaker"}
            timed_fields = legacy_fields | {"words"}
            for item in raw["segments"]:
                if (
                    not isinstance(item, dict)
                    or set(item) != (legacy_fields if version == "1.0.0" else timed_fields)
                    or not isinstance(item.get("range_us"), dict)
                    or set(item["range_us"]) != {"start", "end_exclusive"}
                ):
                    raise ValueError("Transcript segment schema is invalid")
                words: tuple[TranscriptWord, ...] = ()
                if version == "1.1.0":
                    if not isinstance(item["words"], list):
                        raise ValueError("Transcript words schema is invalid")
                    parsed_words = []
                    for word in item["words"]:
                        if (
                            not isinstance(word, dict)
                            or set(word) != {"range_us", "text", "confidence"}
                            or not isinstance(word["range_us"], dict)
                            or set(word["range_us"]) != {"start", "end_exclusive"}
                            or type(word["range_us"]["start"]) is not int
                            or type(word["range_us"]["end_exclusive"]) is not int
                            or not isinstance(word["text"], str)
                            or (
                                word["confidence"] is not None
                                and (
                                    type(word["confidence"]) not in {int, float}
                                    or not 0 <= word["confidence"] <= 1
                                )
                            )
                        ):
                            raise ValueError("Transcript word schema is invalid")
                        parsed_words.append(
                            TranscriptWord(
                                word["range_us"]["start"],
                                word["range_us"]["end_exclusive"],
                                word["text"],
                                word["confidence"],
                            )
                        )
                    words = tuple(parsed_words)
                segments.append(
                    TranscriptSegment(
                        item["segment_id"], item["range_us"]["start"],
                        item["range_us"]["end_exclusive"], item["text"],
                        item["confidence"], item["speaker"], words,
                    )
                )
            transcript = TranscriptManifest(
                raw["source_asset_id"], raw["language"], raw["provider_id"], raw["model_id"],
                tuple(segments), word_timestamps_included=(version == "1.1.0"),
            )

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

    def _write_immutable_publication_payloads(
        self,
        operation_id: str,
        payloads: dict[str, bytes],
    ) -> None:
        """Single physical immutable-publication writer for every codec."""

        bounds = {
            "transcript.json": self._TRANSCRIPT_MAX_BYTES,
            "subtitles.srt": self._SRT_MAX_BYTES,
            "transcription-report.json": self._REPORT_MAX_BYTES,
            "publication-set.json": self._PUBLICATION_SET_MAX_BYTES,
        }
        if set(payloads) != set(bounds) or any(
            not isinstance(raw, bytes) or len(raw) > bounds[name]
            for name, raw in payloads.items()
        ):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_PUBLICATION_SET_INVALID",
                "Immutable transcription publication payloads are invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
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

    def _read_immutable_publication_payloads(
        self,
        operation_id: str,
    ) -> tuple[dict[str, bytes], bytes]:
        """Single physical immutable-publication reader for every codec."""

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
        return values, raw_document

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
        payloads = {**values, "publication-set.json": canonical_json_bytes(document)}
        self._write_immutable_publication_payloads(operation_id, payloads)
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
        values, raw_document = self._read_immutable_publication_payloads(operation_id)
        transcript = self._decode_immutable_publication_set(
            values,
            raw_document,
            operation_id=operation_id,
            expected_set_sha256=expected_set_sha256,
            project_id=project_id,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            provider_id=provider_id,
            model_id=model_id,
            execution_config_sha256=execution_config_sha256,
        )
        return values, transcript

    def _decode_immutable_publication_set(
        self,
        values: dict[str, bytes],
        raw_document: bytes,
        *,
        operation_id: str,
        expected_set_sha256: str,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        provider_id: str,
        model_id: str,
        execution_config_sha256: str,
    ) -> TranscriptManifest:
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
        return transcript

    def _inspect_historical_publication_set(
        self,
        operation_id: str,
        expected_set_sha256: str,
    ) -> dict[str, object]:
        """Boundedly validate a foreign v1/v2 immutable set without recovery."""

        if re.fullmatch(r"sha256:[0-9a-f]{64}", expected_set_sha256) is None:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical publication reference is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            values, raw = self._read_immutable_publication_payloads(operation_id)
        except ProductError as exc:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical immutable publication is unavailable", ProductErrorCategory.DATA_INTEGRITY) from exc
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical immutable publication is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(document, dict) or not isinstance(document.get("files"), dict):
            raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical immutable publication schema is invalid", ProductErrorCategory.DATA_INTEGRITY)
        body = dict(document)
        actual_sha = body.pop("publication_set_sha256", None)
        if actual_sha != expected_set_sha256 or sha256_bytes(canonical_json_bytes(body)) != expected_set_sha256:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical immutable publication digest is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if set(document["files"]) != set(values) or document["files"] != self._publication_hashes(values):
            raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical immutable file identities are invalid", ProductErrorCategory.DATA_INTEGRITY)
        common = {
            "publication_set_version", "project_id", "operation_id", "source_asset_id",
            "source_asset_sha256", "provider_id", "model_id", "execution_config_sha256",
            "transcript_manifest_sha256", "files", "publication_set_sha256",
        }
        v2_only = {
            "runtime_request", "runtime_capability_observation", "runtime_decision",
            "runtime_admission_ref", "admission_evaluated_at", "task023_config_sha256",
            "task023_execution_sha256", "model_download_authorized",
        }
        version = document.get("publication_set_version")
        expected = common if version == "1.0.0" else common | v2_only if version == "2.0.0" else set()
        if set(document) != expected or document.get("operation_id") != operation_id:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical immutable publication coordinate is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if (
            not isinstance(document.get("project_id"), str)
            or not isinstance(document.get("source_asset_id"), str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", document.get("source_asset_sha256", "")) is None
            or not isinstance(document.get("provider_id"), str)
            or not isinstance(document.get("model_id"), str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", document.get("execution_config_sha256", "")) is None
            or re.fullmatch(r"sha256:[0-9a-f]{64}", document.get("transcript_manifest_sha256", "")) is None
        ):
            raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical immutable publication identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            transcript = self._validate_publication(
                values,
                source_asset_id=document["source_asset_id"],
                provider_id=document["provider_id"],
                model_id=document["model_id"],
            )
        except ProductError as exc:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT",
                "Historical Transcript publication is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if transcript.to_dict()["manifest_sha256"] != document["transcript_manifest_sha256"]:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical Transcript identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if version == "2.0.0":
            try:
                _request, _observation, _decision = _validate_v2_admission_chain(
                    document,
                    expected_source_sha256=document["source_asset_sha256"],
                )
            except (TypeError, ValueError) as exc:
                raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical runtime admission chain is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
            if (
                re.fullmatch(r"sha256:[0-9a-f]{64}", document.get("task023_config_sha256", "")) is None
                or re.fullmatch(r"sha256:[0-9a-f]{64}", document.get("task023_execution_sha256", "")) is None
            ):
                raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical runtime admission proof is invalid", ProductErrorCategory.DATA_INTEGRITY)
        return document

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

    def _cross_version_guard_key(
        self,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> str:
        body = {
            "coordination_version": "1.0.0",
            "project_id": project_id,
            "source_asset_id": source_asset_id,
            "source_asset_sha256": source_asset_sha256,
        }
        digest = hashlib.sha256(
            b"bvp.task098.task036-cross-version-guard.v1\0" + canonical_json_bytes(body),
        ).hexdigest()
        return "task036-transcription-cross-version-" + digest

    def _acquire_cross_version_lease(
        self,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        *,
        version: str,
    ) -> str:
        """Permanently assign one source coordinate to the v1 or v2 namespace.

        This is intentionally a conservative, store-only boundary.  It never
        creates a version operation before the neutral guard chooses a version,
        and it never attempts to repair an uncertain historic operation.
        """

        if version not in {"v1", "v2"}:
            raise ValueError("cross-version lease version is invalid")
        known = {
            "task036.local_transcription",
            "task036.local_transcription.v2",
            "task036.local_transcription.cross_version_guard.v1",
            "task036.local_transcription_output_slot",
        }
        try:
            rows = self.store.list_operations_by_command_prefix(
                self.production_job_id,
                command_type_prefix="task036.local_transcription",
                limit=256,
            )
        except ProductError:
            raise
        for row in rows:
            if row.job_id != self.production_job_id or row.command_type not in known or row.status not in {
                "PENDING", "IN_PROGRESS", "PARTIAL", "COMPLETED", "FAILED",
            }:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT",
                    "A historical transcription coordination record is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if row.command_type == "task036.local_transcription.cross_version_guard.v1" and (
                re.fullmatch(r"task036-transcription-cross-version-[0-9a-f]{64}", row.idempotency_key) is None
                or row.attempt != 0
                or (row.status == "PENDING" and row.result_ref is not None)
                or (
                    row.status == "IN_PROGRESS"
                    and (
                        not isinstance(row.result_ref, str)
                        or re.fullmatch(r"task098-runtime-owner:(?:v1|v2):[0-9a-f]{64}", row.result_ref) is None
                        or row.result_ref.rsplit(":", 1)[-1] != row.idempotency_key.rsplit("-", 1)[-1]
                    )
                )
                or row.status not in {"PENDING", "IN_PROGRESS"}
            ):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT",
                    "A historical source version lease is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            opposite = (
                version == "v1" and row.command_type == "task036.local_transcription.v2"
            ) or (
                version == "v2" and row.command_type == "task036.local_transcription"
            )
            if not opposite:
                continue
            # A typed v2 admission receipt safely proves only its source hash.
            # Everything else is opaque historical state and remains blocking.
            if (
                row.command_type == "task036.local_transcription.v2"
                and row.status in {"IN_PROGRESS", "PARTIAL", "FAILED"}
                and isinstance(row.result_ref, str)
                and re.fullmatch(
                    r"task098-runtime-admission:v2:[0-9a-f]{64}:[0-9a-f]{64}",
                    row.result_ref,
                )
                and row.result_ref.split(":")[2] != source_asset_sha256.removeprefix("sha256:")
            ):
                continue
            if isinstance(row.result_ref, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", row.result_ref):
                if row.status not in {"PARTIAL", "COMPLETED"}:
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT",
                        "Historical publication reference is bound to an invalid lifecycle state",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                document = self._inspect_historical_publication_set(row.operation_id, row.result_ref)
                version_value = document.get("publication_set_version")
                if row.command_type == "task036.local_transcription":
                    if version_value != "1.0.0":
                        raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical v1 publication version is invalid", ProductErrorCategory.DATA_INTEGRITY)
                    body = {
                        "contract": "task036-local-transcription/1.0.0",
                        "project_id": document["project_id"], "source_asset_id": document["source_asset_id"],
                        "source_asset_sha256": document["source_asset_sha256"], "provider_id": document["provider_id"],
                        "model_id": document["model_id"], "execution_config_sha256": document["execution_config_sha256"],
                        "model_download_authorized": False,
                    }
                    rebuilt_key = "task036-transcription-" + hashlib.sha256(canonical_json_bytes(body)).hexdigest()
                else:
                    if version_value != "2.0.0" or not isinstance(document.get("runtime_request"), dict):
                        raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical v2 publication version is invalid", ProductErrorCategory.DATA_INTEGRITY)
                    try:
                        request = FasterWhisperRuntimeRequestV1.from_dict(document["runtime_request"])
                    except (TypeError, ValueError) as exc:
                        raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical runtime request is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
                    body = {
                        "contract": "task036-local-transcription/2.0.0", "project_id": document["project_id"],
                        "source_asset_id": document["source_asset_id"], "source_asset_sha256": document["source_asset_sha256"],
                        "provider_id": document["provider_id"], "model_id": document["model_id"],
                        "execution_config_sha256": document["execution_config_sha256"],
                        "runtime_request_sha256": request.record_sha256, "model_download_authorized": False,
                    }
                    rebuilt_key = "task036-transcription-" + hashlib.sha256(b"bvp.task098.task036-runtime-operation.v2\0" + canonical_json_bytes(body)).hexdigest()
                if row.idempotency_key != rebuilt_key:
                    raise ProductError("ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT", "Historical operation key does not match its publication", ProductErrorCategory.DATA_INTEGRITY)
                if (
                    document["project_id"] != project_id
                    or document["source_asset_id"] != source_asset_id
                    or document["source_asset_sha256"] != source_asset_sha256
                ):
                    continue
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CONFLICT",
                "A different runtime-version transcription may own this source",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )

        key = self._cross_version_guard_key(
            project_id, source_asset_id, source_asset_sha256,
        )
        guard, _created = self.store.reserve_operation(
            self.production_job_id,
            "task036.local_transcription.cross_version_guard.v1",
            key,
        )
        digest = key.rsplit("-", 1)[-1]
        owner_ref = f"task098-runtime-owner:{version}:{digest}"
        if (
            guard.job_id != self.production_job_id
            or guard.command_type != "task036.local_transcription.cross_version_guard.v1"
            or guard.idempotency_key != key
            or guard.attempt != 0
        ):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT",
                "The source version lease coordinate is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if guard.status == "PENDING" and guard.result_ref is None:
            guard, changed = self.store.compare_and_set_operation_status(
                guard.operation_id,
                expected_statuses=("PENDING",),
                expected_result_refs=(None,),
                status="IN_PROGRESS",
                result_ref=owner_ref,
                replace_result_ref=True,
            )
            if (
                changed
                and guard.job_id == self.production_job_id
                and guard.command_type == "task036.local_transcription.cross_version_guard.v1"
                and guard.idempotency_key == key
                and guard.status == "IN_PROGRESS"
                and guard.attempt == 0
                and guard.result_ref == owner_ref
            ):
                return guard.operation_id
        if (
            guard.job_id == self.production_job_id
            and
            guard.status == "IN_PROGRESS"
            and guard.result_ref == owner_ref
            and guard.idempotency_key == key
            and guard.command_type == "task036.local_transcription.cross_version_guard.v1"
            and guard.attempt == 0
        ):
            return guard.operation_id
        if (
            guard.status == "IN_PROGRESS"
            and isinstance(guard.result_ref, str)
            and re.fullmatch(r"task098-runtime-owner:(?:v1|v2):[0-9a-f]{64}", guard.result_ref)
        ):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_OWNER_EXISTS",
                "The source is permanently leased to another runtime version",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        raise ProductError(
            "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT",
            "The source version lease is malformed or changed",
            ProductErrorCategory.DATA_INTEGRITY,
        )

    def _require_existing_v2_lease(
        self,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        *,
        error_code: str,
    ) -> Any:
        """Read and validate the permanent v2 lease without reserving or repairing it."""

        key = self._cross_version_guard_key(
            project_id, source_asset_id, source_asset_sha256,
        )
        lease = self.store.find_operation(self.production_job_id, key)
        expected_ref = "task098-runtime-owner:v2:" + key.rsplit("-", 1)[-1]
        if (
            lease is None
            or lease.job_id != self.production_job_id
            or lease.command_type != "task036.local_transcription.cross_version_guard.v1"
            or lease.idempotency_key != key
            or lease.status != "IN_PROGRESS"
            or type(lease.attempt) is not int
            or lease.attempt != 0
            or lease.result_ref != expected_ref
        ):
            raise ProductError(
                error_code,
                "The existing runtime-managed source lease is missing or invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return lease

    def _require_output_slot_owner(
        self,
        project_id: str,
        slot_operation_id: str,
        operation_id: str,
    ) -> None:
        slot = self.store.get_operation(slot_operation_id)
        if (
            slot.operation_id != slot_operation_id
            or slot.job_id != self.production_job_id
            or slot.command_type != "task036.local_transcription_output_slot"
            or slot.idempotency_key != self._slot_key(project_id)
            or slot.status != "IN_PROGRESS"
            or slot.result_ref != operation_id
        ):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OUTPUT_SLOT_STALE",
                "Transcription output slot identity changed before binding completion",
                ProductErrorCategory.DATA_INTEGRITY,
            )

    def _execute_admitted_lifecycle(
        self,
        *,
        snapshot: Path,
        temporary: Path,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        operation: Any,
        slot: Any,
        provider_id: str,
        model_id: str,
        admission_ref: str | None,
        provider_factory: Callable[[], FasterWhisperProvider],
        validate_provider: Callable[[FasterWhisperProvider], None],
        store_publication: Callable[[dict[str, bytes], TranscriptManifest, FasterWhisperProvider], str],
        build_outcome: Callable[[LocalTranscriptionOutcome], Any],
        language: str | None,
        timeline_rate: FrameRate,
        redact_unexpected: bool,
    ) -> Any:
        """One post-admission Provider/publication lifecycle for v1 and v2."""

        try:
            provider = provider_factory()
            validate_provider(provider)
            with self._provider_snapshot(
                snapshot, source_asset_sha256, temporary / "provider-source.media",
            ) as provider_source:
                publication = LocalTranscriptionService.run(
                    provider_source,
                    temporary / "publication",
                    provider=provider,
                    source_asset_id=source_asset_id,
                    language=language,
                    timeline_rate=timeline_rate,
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
            publication_set_sha256 = store_publication(values, transcript, provider)
            partial, bound = self.store.compare_and_set_operation_status(
                operation.operation_id,
                expected_statuses=("IN_PROGRESS",),
                expected_result_refs=(admission_ref,),
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
            return build_outcome(LocalTranscriptionOutcome(
                transcript, True, False,
                operation.operation_id, slot.operation_id, publication_set_sha256,
            ))
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
                expected_result_refs=(admission_ref,),
                status="PARTIAL",
                last_error_code=code,
            )
            if redact_unexpected and not isinstance(exc, ProductError):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_UNCERTAIN",
                    "Runtime-managed transcription stopped after durable admission",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                ) from None
            raise

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
            self._acquire_cross_version_lease(
                project_id, source_asset_id, source_asset_sha256, version="v1",
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
            def store_publication(
                values: dict[str, bytes],
                transcript: TranscriptManifest,
                _provider: FasterWhisperProvider,
            ) -> str:
                return self._store_immutable_publication_set(
                    values,
                    project_id=project_id,
                    operation_id=operation.operation_id,
                    source_asset_id=source_asset_id,
                    source_asset_sha256=source_asset_sha256,
                    provider_id=provider_id,
                    model_id=model_id,
                    execution_config_sha256=execution_config_sha256,
                    transcript_manifest_sha256=transcript.to_dict()["manifest_sha256"],
                )

            return self._execute_admitted_lifecycle(
                snapshot=validated_snapshot,
                temporary=temporary,
                project_id=project_id,
                source_asset_id=source_asset_id,
                source_asset_sha256=source_asset_sha256,
                operation=operation,
                slot=slot,
                provider_id=provider_id,
                model_id=model_id,
                admission_ref=None,
                provider_factory=lambda: self.provider,
                validate_provider=lambda _provider: None,
                store_publication=store_publication,
                build_outcome=lambda outcome: outcome,
                language=self.language,
                timeline_rate=self.timeline_rate,
                redact_unexpected=False,
            )

    def _recover_bound_publication(
        self,
        *,
        project_id: str,
        source_path: Path,
        source_asset_id: str,
        source_asset_sha256: str,
        command_type: str,
        operation_key: str,
        provider_id: str,
        model_id: str,
        lease_policy: Callable[[], None],
        lease_before_snapshot: bool,
        ref_before_lease: bool,
        slot_before_decode: bool,
        decode_publication: Callable[[dict[str, bytes], bytes, Any], tuple[TranscriptManifest, Any, str]],
        build_outcome: Callable[[LocalTranscriptionOutcome, Any], Any],
        missing_code: str,
        missing_message: str,
    ) -> Any:
        """Single Provider-zero immutable recovery lifecycle for v1 and v2."""

        operation = self.store.find_operation(self.production_job_id, operation_key)
        if operation is None or operation.status not in {"PARTIAL", "COMPLETED"}:
            raise ProductError(missing_code, missing_message, ProductErrorCategory.STATE)
        if operation.command_type != command_type or operation.idempotency_key != operation_key:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
                "Durable operation belongs to a different Product command",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        def require_publication_ref() -> None:
            if not isinstance(operation.result_ref, str) or re.fullmatch(
                r"sha256:[0-9a-f]{64}", operation.result_ref,
            ) is None:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                    "Durable transcription has no bound immutable publication",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                )

        if ref_before_lease:
            require_publication_ref()
        if lease_before_snapshot:
            lease_policy()
        with tempfile.TemporaryDirectory(prefix="bai-task036-recover-") as raw_temp:
            self._snapshot_source(
                source_path, source_asset_sha256, Path(raw_temp) / "canonical-source.media",
            )
        if not lease_before_snapshot:
            lease_policy()
        if not ref_before_lease:
            require_publication_ref()

        slot = None
        if slot_before_decode:
            slot = self._acquire_output_slot(
                project_id, operation.operation_id, allow_existing_owner=True,
            )
        values, raw_document = self._read_immutable_publication_payloads(operation.operation_id)
        transcript, context, state = decode_publication(values, raw_document, operation)
        if state not in {"RECOVERABLE_PUBLICATION", "VERIFICATION_ONLY"}:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_RECOVERY_NOT_AVAILABLE",
                "Durable publication cannot be recovered",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        if slot is None:
            slot = self._acquire_output_slot(
                project_id, operation.operation_id, allow_existing_owner=True,
            )
        if state == "VERIFICATION_ONLY":
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
        if state == "RECOVERABLE_PUBLICATION":
            completed, changed = self.store.compare_and_set_operation_status(
                operation.operation_id,
                expected_statuses=("PARTIAL",),
                expected_result_refs=(operation.result_ref,),
                status="COMPLETED",
                result_ref=operation.result_ref,
                replace_result_ref=True,
            )
            if not changed and (
                completed.status != "COMPLETED"
                or completed.result_ref != operation.result_ref
            ):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE",
                    "Concurrent recovery changed the durable operation",
                    ProductErrorCategory.STATE,
                )
        return build_outcome(
            LocalTranscriptionOutcome(
                transcript, False, True,
                operation.operation_id, slot.operation_id, operation.result_ref,
            ),
            context,
        )

    def _finalize_bound_publication(
        self,
        *,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        transcript_manifest_sha256: str,
        operation_id: str,
        slot_operation_id: str,
        publication_set_sha256: str,
        command_type: str,
        operation_key: str,
        lease_policy: Callable[[], None],
        decode_publication: Callable[[dict[str, bytes], bytes, Any], tuple[TranscriptManifest, Any, str]],
    ) -> None:
        """Single exact final-binding lifecycle for v1 and v2."""

        operation = self.store.find_operation(self.production_job_id, operation_key)
        if (
            operation is None
            or operation.operation_id != operation_id
            or operation.command_type != command_type
            or operation.idempotency_key != operation_key
            or operation.status != "COMPLETED"
            or operation.result_ref != publication_set_sha256
        ):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
                "Durable transcription changed before binding completion",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        lease_policy()
        values, raw_document = self._read_immutable_publication_payloads(operation_id)
        transcript, _context, state = decode_publication(values, raw_document, operation)
        if state != "VERIFICATION_ONLY":
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
                "Durable publication is not in the final verification state",
                ProductErrorCategory.DATA_INTEGRITY,
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
        self._require_output_slot_owner(project_id, slot_operation_id, operation_id)
        self._release_output_slot(slot_operation_id, operation_id)

    def recover_local_media(self, *, project_id: str, source_path: Path, source_asset_id: str, source_asset_sha256: str) -> LocalTranscriptionOutcome:
        provider_id, model_id, execution_config_sha256 = self._authorize_provider()
        operation_key = self._operation_key(
            project_id, source_asset_id, source_asset_sha256,
        )
        def decode(values: dict[str, bytes], raw: bytes, operation: Any):
            transcript = self._decode_immutable_publication_set(
                values, raw, operation_id=operation.operation_id,
                expected_set_sha256=operation.result_ref,
                project_id=project_id, source_asset_id=source_asset_id,
                source_asset_sha256=source_asset_sha256,
                provider_id=provider_id, model_id=model_id,
                execution_config_sha256=execution_config_sha256,
            )
            state = "RECOVERABLE_PUBLICATION" if operation.status == "PARTIAL" else "VERIFICATION_ONLY"
            return transcript, None, state

        return self._recover_bound_publication(
            project_id=project_id, source_path=source_path,
            source_asset_id=source_asset_id, source_asset_sha256=source_asset_sha256,
            command_type="task036.local_transcription", operation_key=operation_key,
            provider_id=provider_id, model_id=model_id,
            lease_policy=lambda: self._acquire_cross_version_lease(
                project_id, source_asset_id, source_asset_sha256, version="v1",
            ),
            lease_before_snapshot=False, ref_before_lease=False,
            slot_before_decode=True, decode_publication=decode,
            build_outcome=lambda outcome, _context: outcome,
            missing_code="ERR_TASK036_TRANSCRIPTION_RECOVERY_NOT_AVAILABLE",
            missing_message="No durable transcription is available for recovery",
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
        operation_key = self._operation_key(project_id, source_asset_id, source_asset_sha256)

        def decode(values: dict[str, bytes], raw: bytes, operation: Any):
            transcript = self._decode_immutable_publication_set(
                values, raw, operation_id=operation.operation_id,
                expected_set_sha256=operation.result_ref,
                project_id=project_id, source_asset_id=source_asset_id,
                source_asset_sha256=source_asset_sha256,
                provider_id=provider_id, model_id=model_id,
                execution_config_sha256=execution_config_sha256,
            )
            return transcript, None, "VERIFICATION_ONLY"

        self._finalize_bound_publication(
            project_id=project_id, source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            transcript_manifest_sha256=transcript_manifest_sha256,
            operation_id=operation_id, slot_operation_id=slot_operation_id,
            publication_set_sha256=publication_set_sha256,
            command_type="task036.local_transcription", operation_key=operation_key,
            lease_policy=lambda: None, decode_publication=decode,
        )

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

    def transcribe_runtime_managed(
        self,
        binding: Any,
        *,
        project_id: str,
        source_path: Path,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> Any:
        """Execute the v2 binding through this one durable physical engine."""

        if re.fullmatch(r"sha256:[0-9a-f]{64}", source_asset_sha256) is None:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_SOURCE_MISMATCH", "Canonical Asset SHA is invalid", ProductErrorCategory.DATA_INTEGRITY)
        provider_id, model_id, execution_config_sha256 = binding._execution_identity()
        operation_key = binding._operation_key(project_id, source_asset_id, source_asset_sha256)
        self._preflight_output_targets()
        with tempfile.TemporaryDirectory(prefix="bai-task036-v2-transcribe-") as raw_temp:
            temporary = Path(raw_temp)
            snapshot = self._snapshot_source(source_path, source_asset_sha256, temporary / "canonical-source.media")
            self._acquire_cross_version_lease(project_id, source_asset_id, source_asset_sha256, version="v2")
            operation, _created = self.store.reserve_operation(self.production_job_id, "task036.local_transcription.v2", operation_key)
            if operation.status != "PENDING" or operation.result_ref is not None:
                raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_REQUIRED", "Durable runtime transcription already exists; explicit recovery is required", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
            self._preflight_generation_target(operation.operation_id)
            observation, decision = evaluate_runtime_preflight(
                binding.runtime_request, binding.capability_probe, observed_at=binding._clock_text(), ttl_seconds=300,
            )
            if decision.outcome not in {"READY_CPU", "READY_CUDA"}:
                raise ProductError("ERR_TASK098_RUNTIME_ADMISSION_BLOCKED", "Runtime preflight is not READY", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
            admission_ref = binding._admission_ref(source_asset_sha256, decision)
            operation, admitted, evaluated_at = self.store.compare_and_set_operation_status_with_validity(
                operation.operation_id, expected_statuses=("PENDING",), status="IN_PROGRESS",
                valid_from=decision.issued_at, valid_until=decision.expires_at,
                expected_result_refs=(None,), result_ref=admission_ref,
                replace_result_ref=True, increment_attempt=True,
            )
            if not admitted or operation.result_ref != admission_ref:
                raise ProductError("ERR_TASK098_RUNTIME_ADMISSION_STALE", "Runtime decision was stale or operation changed before admission", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
            try:
                slot = self._acquire_output_slot(project_id, operation.operation_id)
            except BaseException as exc:
                code = exc.code if isinstance(exc, ProductError) and re.fullmatch(r"ERR_[A-Z0-9_]{1,120}", exc.code) else "ERR_TASK036_TRANSCRIPTION_OUTPUT_SLOT_BUSY"
                rolled_back, rolled = self.store.compare_and_set_operation_status(operation.operation_id, expected_statuses=("IN_PROGRESS",), expected_result_refs=(admission_ref,), status="PENDING", last_error_code=code, result_ref=None, replace_result_ref=True)
                if not rolled or rolled_back.status != "PENDING" or rolled_back.result_ref is not None:
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_COMPLETION_UNCERTAIN",
                        "Runtime admission could not be rolled back after output-slot contention",
                        ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                    ) from None
                if isinstance(exc, ProductError):
                    raise
                raise ProductError("ERR_TASK036_TRANSCRIPTION_OUTPUT_SLOT_BUSY", "Runtime transcription could not acquire the fixed output slot", ProductErrorCategory.HUMAN_REVIEW_REQUIRED) from None
            effective: dict[str, FasterWhisperConfig] = {}

            def make_provider() -> FasterWhisperProvider:
                config = binding._effective_config(decision)
                effective["config"] = config
                return binding.provider_factory(config)

            def validate_provider(provider: FasterWhisperProvider) -> None:
                binding._validate_provider(provider, effective["config"])

            def store_publication(
                values: dict[str, bytes],
                transcript: TranscriptManifest,
                _provider: FasterWhisperProvider,
            ) -> str:
                diagnostic = build_execution_identity_for_config(
                    effective["config"], provider_id=provider_id, model_id=model_id,
                    source_sha256=source_asset_sha256, requested_language=binding.language,
                )
                return binding._store_v2_publication_set(
                    self, values, project_id=project_id, operation_id=operation.operation_id,
                    source_asset_id=source_asset_id, source_asset_sha256=source_asset_sha256,
                    provider_id=provider_id, model_id=model_id,
                    execution_config_sha256=execution_config_sha256,
                    transcript_manifest_sha256=transcript.to_dict()["manifest_sha256"],
                    observation=observation, decision=decision, admission_ref=admission_ref,
                    admission_evaluated_at=evaluated_at,
                    task023_config_sha256=diagnostic.config_sha256,
                    task023_execution_sha256=diagnostic.execution_sha256,
                )

            return self._execute_admitted_lifecycle(
                snapshot=snapshot,
                temporary=temporary,
                project_id=project_id,
                source_asset_id=source_asset_id,
                source_asset_sha256=source_asset_sha256,
                operation=operation,
                slot=slot,
                provider_id=provider_id,
                model_id=model_id,
                admission_ref=admission_ref,
                provider_factory=make_provider,
                validate_provider=validate_provider,
                store_publication=store_publication,
                build_outcome=lambda outcome: binding._outcome(outcome, decision),
                language=binding.language,
                timeline_rate=binding.timeline_rate,
                redact_unexpected=True,
            )

    def recover_runtime_managed(
        self,
        binding: Any,
        *,
        project_id: str,
        source_path: Path,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> Any:
        operation_key = binding._operation_key(project_id, source_asset_id, source_asset_sha256)
        provider_id, model_id, _execution_sha = binding._execution_identity()

        def validate_lease() -> None:
            self._require_existing_v2_lease(
                project_id, source_asset_id, source_asset_sha256,
                error_code="ERR_TASK036_TRANSCRIPTION_RECOVERY_NOT_AVAILABLE",
            )

        def decode(values: dict[str, bytes], raw: bytes, operation: Any):
            transcript, decision = binding._decode_v2_publication_set(
                self, values, raw, operation.operation_id, operation.result_ref,
                project_id=project_id, source_asset_id=source_asset_id,
                source_asset_sha256=source_asset_sha256,
            )
            state = binding._classify_validated_runtime_recovery(
                operation, publication=decision, project_id=project_id,
                source_asset_id=source_asset_id, source_asset_sha256=source_asset_sha256,
            )
            return transcript, decision, state

        return self._recover_bound_publication(
            project_id=project_id, source_path=source_path,
            source_asset_id=source_asset_id, source_asset_sha256=source_asset_sha256,
            command_type="task036.local_transcription.v2", operation_key=operation_key,
            provider_id=provider_id, model_id=model_id,
            lease_policy=validate_lease, lease_before_snapshot=True,
            ref_before_lease=True, slot_before_decode=False,
            decode_publication=decode,
            build_outcome=lambda outcome, decision: binding._outcome(outcome, decision),
            missing_code="ERR_TASK036_TRANSCRIPTION_RECOVERY_NOT_AVAILABLE",
            missing_message="No runtime-managed transcription is available for recovery",
        )

    def finalize_runtime_managed(
        self,
        binding: Any,
        *,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        transcript_manifest_sha256: str,
        operation_id: str,
        slot_operation_id: str,
        publication_set_sha256: str,
    ) -> None:
        operation_key = binding._operation_key(project_id, source_asset_id, source_asset_sha256)

        def validate_lease() -> None:
            self._require_existing_v2_lease(
                project_id, source_asset_id, source_asset_sha256,
                error_code="ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
            )

        def decode(values: dict[str, bytes], raw: bytes, operation: Any):
            transcript, decision = binding._decode_v2_publication_set(
                self, values, raw, operation.operation_id, operation.result_ref,
                project_id=project_id, source_asset_id=source_asset_id,
                source_asset_sha256=source_asset_sha256,
            )
            state = binding._classify_validated_runtime_recovery(
                operation, publication=decision, project_id=project_id,
                source_asset_id=source_asset_id, source_asset_sha256=source_asset_sha256,
            )
            return transcript, decision, state

        self._finalize_bound_publication(
            project_id=project_id, source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            transcript_manifest_sha256=transcript_manifest_sha256,
            operation_id=operation_id, slot_operation_id=slot_operation_id,
            publication_set_sha256=publication_set_sha256,
            command_type="task036.local_transcription.v2", operation_key=operation_key,
            lease_policy=validate_lease, decode_publication=decode,
        )


class Task036LocalTranscriptionPort:
    """Compatibility façade retaining the exact v1 public constructor/API.

    The façade intentionally owns no operation lifecycle or physical output
    I/O.  Those operations are centralized in the internal engine so v1 and
    the runtime-managed successor share the same durable primitives.
    """

    # Retain the original v1 class-level resource-bound seam.  The facade
    # copies these values to its engine immediately before each public
    # lifecycle entry; this keeps legacy bounded-read tests observable without
    # reintroducing a second lifecycle or physical-I/O implementation.
    _TRANSCRIPT_MAX_BYTES = _Task036LocalTranscriptionOperationEngine._TRANSCRIPT_MAX_BYTES
    _SRT_MAX_BYTES = _Task036LocalTranscriptionOperationEngine._SRT_MAX_BYTES
    _REPORT_MAX_BYTES = _Task036LocalTranscriptionOperationEngine._REPORT_MAX_BYTES
    _PUBLICATION_SET_MAX_BYTES = _Task036LocalTranscriptionOperationEngine._PUBLICATION_SET_MAX_BYTES

    def __init__(
        self,
        provider: FasterWhisperProvider,
        output_directory: Path,
        store: SQLiteProductStore,
        production_job_id: str,
        language: str | None = None,
        timeline_rate: FrameRate = FrameRate(30000, 1001),
    ) -> None:
        self._engine = _Task036LocalTranscriptionOperationEngine(
            provider=provider,
            output_directory=output_directory,
            store=store,
            production_job_id=production_job_id,
            language=language,
            timeline_rate=timeline_rate,
        )

    def __getattr__(self, name: str) -> Any:
        # Existing test-only private helper calls remain thin engine delegates;
        # no independent v1 state machine survives on this facade.
        return getattr(self._engine, name)

    # Preserve the legacy mutable public surface while keeping the engine as
    # the sole owner of all operational state.
    @property
    def provider(self) -> FasterWhisperProvider:
        return self._engine.provider

    @provider.setter
    def provider(self, value: FasterWhisperProvider) -> None:
        self._engine.provider = value

    @property
    def output_directory(self) -> Path:
        return self._engine.output_directory

    @output_directory.setter
    def output_directory(self, value: Path) -> None:
        self._engine.output_directory = value

    @property
    def store(self) -> SQLiteProductStore:
        return self._engine.store

    @store.setter
    def store(self, value: SQLiteProductStore) -> None:
        self._engine.store = value

    @property
    def production_job_id(self) -> str:
        return self._engine.production_job_id

    @production_job_id.setter
    def production_job_id(self, value: str) -> None:
        self._engine.production_job_id = value

    @property
    def language(self) -> str | None:
        return self._engine.language

    @language.setter
    def language(self, value: str | None) -> None:
        self._engine.language = value

    @property
    def timeline_rate(self) -> FrameRate:
        return self._engine.timeline_rate

    @timeline_rate.setter
    def timeline_rate(self, value: FrameRate) -> None:
        self._engine.timeline_rate = value

    def _sync_legacy_resource_bounds(self) -> None:
        self._engine._TRANSCRIPT_MAX_BYTES = self._TRANSCRIPT_MAX_BYTES
        self._engine._SRT_MAX_BYTES = self._SRT_MAX_BYTES
        self._engine._REPORT_MAX_BYTES = self._REPORT_MAX_BYTES
        self._engine._PUBLICATION_SET_MAX_BYTES = self._PUBLICATION_SET_MAX_BYTES

    def transcribe_local_media(self, **kwargs: Any) -> LocalTranscriptionOutcome:
        self._sync_legacy_resource_bounds()
        return self._engine.transcribe_local_media(**kwargs)

    def recover_local_media(self, **kwargs: Any) -> LocalTranscriptionOutcome:
        self._sync_legacy_resource_bounds()
        return self._engine.recover_local_media(**kwargs)

    def finalize_local_media_binding(self, **kwargs: Any) -> None:
        self._sync_legacy_resource_bounds()
        self._engine.finalize_local_media_binding(**kwargs)

    def recovery_required(self, project_id: str, source_asset_id: str, source_asset_sha256: str) -> bool:
        self._sync_legacy_resource_bounds()
        return self._engine.recovery_required(project_id, source_asset_id, source_asset_sha256)


@dataclass(frozen=True, slots=True)
class FasterWhisperProviderSettingsV2:
    """Private static settings which deliberately contain no runtime authority."""

    model: str = "small"
    beam_size: int = 5
    vad_filter: bool = True
    cache_directory: str | Path | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model or "\x00" in self.model:
            raise ValueError("model must be non-empty text")
        symbolic = re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.model)
        absolute = Path(self.model).is_absolute()
        if not symbolic and not absolute:
            raise ValueError("model must be a symbolic name or absolute local locator")
        if type(self.beam_size) is not int or not 1 <= self.beam_size <= 20:
            raise ValueError("beam_size must be an integer in 1..20")
        if type(self.vad_filter) is not bool:
            raise ValueError("vad_filter must be a bool")
        if self.cache_directory is not None and "\x00" in str(self.cache_directory):
            raise ValueError("cache_directory is invalid")

    def normalized_cache_directory(self) -> Path | None:
        if self.cache_directory is None:
            return None
        return Path(self.cache_directory).expanduser().resolve(strict=False)

    @property
    def model_id(self) -> str:
        # V2 never exposes an absolute model locator as a public Provider ID.
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.model):
            return self.model
        return "local-model-" + hashlib.sha256(self.model.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True, slots=True, init=False)
class RuntimeManagedLocalTranscriptionOutcomeV2:
    """The v1 outcome plus projections derived from validated typed receipts.

    No caller may supply a public dictionary and no mutable dictionary is held
    by the outcome.  Each public projection is freshly derived from its typed,
    request-bound record, so later consumers cannot mutate stored truth.
    """

    transcript: TranscriptManifest
    provider_execution_started: bool
    recovered_from_durable_result: bool
    operation_id: str | None
    slot_operation_id: str | None
    publication_set_sha256: str | None
    _runtime_request: FasterWhisperRuntimeRequestV1
    _runtime_decision: FasterWhisperRuntimeDecisionV1

    def __init__(
        self,
        *,
        transcript: TranscriptManifest,
        provider_execution_started: bool,
        recovered_from_durable_result: bool,
        operation_id: str | None,
        slot_operation_id: str | None,
        publication_set_sha256: str | None,
        runtime_request: FasterWhisperRuntimeRequestV1,
        runtime_decision: FasterWhisperRuntimeDecisionV1,
    ) -> None:
        request, decision = validate_runtime_pair(runtime_request, runtime_decision)
        object.__setattr__(self, "transcript", transcript)
        object.__setattr__(self, "provider_execution_started", bool(provider_execution_started))
        object.__setattr__(self, "recovered_from_durable_result", bool(recovered_from_durable_result))
        object.__setattr__(self, "operation_id", operation_id)
        object.__setattr__(self, "slot_operation_id", slot_operation_id)
        object.__setattr__(self, "publication_set_sha256", publication_set_sha256)
        object.__setattr__(self, "_runtime_request", request)
        object.__setattr__(self, "_runtime_decision", decision)

    @property
    def runtime_request_public(self) -> dict[str, object]:
        return dict(self._runtime_request.to_public_dict())

    @property
    def runtime_decision_public(self) -> dict[str, object]:
        return dict(self._runtime_decision.to_public_dict())


_V2_ADMISSION_RE = re.compile(r"task098-runtime-admission:v2:([0-9a-f]{64}):([0-9a-f]{64})")


def _task036_parse_utc_timestamp(value: str) -> datetime:
    """Parse only the canonical TASK-036 historical-admission timestamp grammar."""

    if not isinstance(value, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value,
    ) is None and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.[0-9]{6}Z", value,
    ) is None:
        raise ValueError("timestamp must be canonical UTC Z text")
    if value.endswith(".000000Z"):
        raise ValueError("zero fractional timestamps must omit the fraction")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("timestamp must be canonical UTC Z text") from exc


def _validate_v2_admission_chain(
    document: dict[str, object],
    *,
    expected_source_sha256: str,
    expected_request: FasterWhisperRuntimeRequestV1 | None = None,
) -> tuple[
    FasterWhisperRuntimeRequestV1,
    FasterWhisperRuntimeCapabilityObservationV1,
    FasterWhisperRuntimeDecisionV1,
]:
    """Purely validate one complete persisted v2 admission proof."""

    request = FasterWhisperRuntimeRequestV1.from_dict(document["runtime_request"])
    observation = FasterWhisperRuntimeCapabilityObservationV1.from_dict(
        document["runtime_capability_observation"], request=request,
    )
    decision = FasterWhisperRuntimeDecisionV1.from_dict(
        document["runtime_decision"], request=request,
    )
    resolved = resolve_runtime_decision(request, observation)
    admitted_at = _task036_parse_utc_timestamp(document["admission_evaluated_at"])
    issued_at = _task036_parse_utc_timestamp(decision.issued_at)
    expires_at = _task036_parse_utc_timestamp(decision.expires_at)
    expected_ref = (
        "task098-runtime-admission:v2:"
        + expected_source_sha256.removeprefix("sha256:")
        + ":"
        + decision.record_sha256.removeprefix("sha256:")
    )
    if (
        re.fullmatch(r"sha256:[0-9a-f]{64}", expected_source_sha256) is None
        or (expected_request is not None and request.to_dict() != expected_request.to_dict())
        or resolved.to_dict() != decision.to_dict()
        or decision.capability_observation_sha256 != observation.record_sha256
        or decision.runtime_request_sha256 != request.record_sha256
        or decision.outcome not in {"READY_CPU", "READY_CUDA"}
        or document.get("runtime_admission_ref") != expected_ref
        or document.get("model_download_authorized") is not False
        or not issued_at <= admitted_at < expires_at
    ):
        raise ValueError("runtime admission chain is invalid")
    return request, observation, decision


class Task036RuntimeManagedLocalTranscriptionPortV2:
    """Fake-probe-only v2 TASK-036 facade with durable runtime admission.

    There is deliberately no default Provider adapter.  A trusted caller must
    inject a factory in tests (and a later Human-gated unit owns any native
    adapter), so construction cannot trigger an OS/GPU/model/network effect.
    """

    _TRANSCRIPT_MAX_BYTES = _Task036LocalTranscriptionOperationEngine._TRANSCRIPT_MAX_BYTES
    _SRT_MAX_BYTES = _Task036LocalTranscriptionOperationEngine._SRT_MAX_BYTES
    _REPORT_MAX_BYTES = _Task036LocalTranscriptionOperationEngine._REPORT_MAX_BYTES
    _PUBLICATION_SET_MAX_BYTES = _Task036LocalTranscriptionOperationEngine._PUBLICATION_SET_MAX_BYTES

    def __init__(
        self,
        *,
        settings: FasterWhisperProviderSettingsV2,
        runtime_request: FasterWhisperRuntimeRequestV1,
        capability_probe: FasterWhisperRuntimeCapabilityProbe,
        provider_factory: Callable[[FasterWhisperConfig], FasterWhisperProvider],
        clock: Callable[[], datetime | str],
        output_directory: Path,
        store: SQLiteProductStore,
        production_job_id: str,
        language: str | None = None,
        timeline_rate: FrameRate = FrameRate(30000, 1001),
    ) -> None:
        if not isinstance(settings, FasterWhisperProviderSettingsV2):
            raise TypeError("settings must be FasterWhisperProviderSettingsV2")
        if not isinstance(runtime_request, FasterWhisperRuntimeRequestV1):
            raise TypeError("runtime_request must be FasterWhisperRuntimeRequestV1")
        if not callable(provider_factory) or not callable(clock):
            raise TypeError("provider_factory and clock must be callable")
        if language is not None and not isinstance(language, str):
            raise ValueError("language must be text or null")
        self.settings = settings
        self.runtime_request = FasterWhisperRuntimeRequestV1.from_dict(runtime_request.to_dict())
        self.capability_probe = capability_probe
        self.provider_factory = provider_factory
        self.clock = clock
        self.output_directory = Path(output_directory)
        self.store = store
        self.production_job_id = production_job_id
        self.language = language
        self.timeline_rate = timeline_rate

    def _engine(self, provider: FasterWhisperProvider | None = None) -> _Task036LocalTranscriptionOperationEngine:
        # The engine methods used before factory entry never touch provider.
        engine = _Task036LocalTranscriptionOperationEngine(
            provider=provider,  # type: ignore[arg-type]
            output_directory=self.output_directory,
            store=self.store,
            production_job_id=self.production_job_id,
            language=self.language,
            timeline_rate=self.timeline_rate,
        )
        engine._TRANSCRIPT_MAX_BYTES = self._TRANSCRIPT_MAX_BYTES
        engine._SRT_MAX_BYTES = self._SRT_MAX_BYTES
        engine._REPORT_MAX_BYTES = self._REPORT_MAX_BYTES
        engine._PUBLICATION_SET_MAX_BYTES = self._PUBLICATION_SET_MAX_BYTES
        return engine

    def _clock_text(self) -> str:
        value = self.clock()
        if isinstance(value, str):
            # R1a observations are second precision by contract.
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value) is None:
                raise ValueError("runtime clock must return a second-precision UTC timestamp")
            _task036_parse_utc_timestamp(value)
            return value
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("runtime clock must return an aware UTC datetime")
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _effective_config(self, decision: FasterWhisperRuntimeDecisionV1) -> FasterWhisperConfig:
        if decision.outcome not in {"READY_CPU", "READY_CUDA"}:
            raise ProductError(
                "ERR_TASK098_RUNTIME_ADMISSION_BLOCKED",
                "Runtime decision is not ready for local transcription",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        cache = self.settings.normalized_cache_directory()
        return FasterWhisperConfig(
            model=self.settings.model,
            device=decision.effective_device or "auto",
            compute_type=decision.effective_compute_type or "int8",
            beam_size=self.settings.beam_size,
            vad_filter=self.settings.vad_filter,
            allow_model_download=False,
            cache_directory=cache,
        )

    def _execution_identity(self) -> tuple[str, str, str]:
        cache = self.settings.normalized_cache_directory()
        cache_sha = None if cache is None else sha256_bytes(str(cache).encode("utf-8"))
        model_sha = sha256_bytes(self.settings.model.encode("utf-8"))
        body = {
            "contract_version": "2.0.0",
            "provider_id": "faster-whisper",
            "model_id": self.settings.model_id,
            "model_config_sha256": model_sha,
            "beam_size": self.settings.beam_size,
            "vad_filter": self.settings.vad_filter,
            "cache_directory_sha256": cache_sha,
            "language": self.language,
            "timeline_rate": {
                "numerator": self.timeline_rate.numerator,
                "denominator": self.timeline_rate.denominator,
            },
            "runtime_request_sha256": self.runtime_request.record_sha256,
            "model_download_authorized": False,
        }
        execution_sha = sha256_bytes(
            b"bvp.task098.task036-runtime-execution-config.v2\0" + canonical_json_bytes(body),
        )
        return "faster-whisper", self.settings.model_id, execution_sha

    def _operation_key(self, project_id: str, source_asset_id: str, source_asset_sha256: str) -> str:
        if not isinstance(project_id, str) or not project_id.strip() or not isinstance(source_asset_id, str) or not source_asset_id.strip():
            raise ValueError("project_id and source_asset_id must be non-empty")
        provider_id, model_id, execution_sha = self._execution_identity()
        body = {
            "contract": "task036-local-transcription/2.0.0",
            "project_id": project_id,
            "source_asset_id": source_asset_id,
            "source_asset_sha256": source_asset_sha256,
            "provider_id": provider_id,
            "model_id": model_id,
            "execution_config_sha256": execution_sha,
            "runtime_request_sha256": self.runtime_request.record_sha256,
            "model_download_authorized": False,
        }
        return "task036-transcription-" + hashlib.sha256(
            b"bvp.task098.task036-runtime-operation.v2\0" + canonical_json_bytes(body),
        ).hexdigest()

    def _admission_ref(self, source_asset_sha256: str, decision: FasterWhisperRuntimeDecisionV1) -> str:
        return "task098-runtime-admission:v2:" + source_asset_sha256.removeprefix("sha256:") + ":" + decision.record_sha256.removeprefix("sha256:")

    def _validate_provider(self, provider: FasterWhisperProvider, config: FasterWhisperConfig) -> None:
        if (
            not isinstance(provider, FasterWhisperProvider)
            or provider.provider_id != "faster-whisper"
            or provider.model_id != self.settings.model_id
            or provider.config != config
            or provider.config.allow_model_download is not False
            or provider.model_loaded is not False
        ):
            raise ProductError(
                "ERR_TASK098_RUNTIME_PROVIDER_INVALID",
                "Runtime-managed provider factory returned an unauthorized Provider",
                ProductErrorCategory.AUTHORIZATION,
            )

    def _outcome(
        self,
        outcome: LocalTranscriptionOutcome,
        decision: FasterWhisperRuntimeDecisionV1,
    ) -> RuntimeManagedLocalTranscriptionOutcomeV2:
        request, checked = validate_runtime_pair(self.runtime_request, decision)
        return RuntimeManagedLocalTranscriptionOutcomeV2(
            transcript=outcome.transcript,
            provider_execution_started=outcome.provider_execution_started,
            recovered_from_durable_result=outcome.recovered_from_durable_result,
            operation_id=outcome.operation_id,
            slot_operation_id=outcome.slot_operation_id,
            publication_set_sha256=outcome.publication_set_sha256,
            runtime_request=request,
            runtime_decision=checked,
        )

    def _v2_publication_body(
        self,
        engine: _Task036LocalTranscriptionOperationEngine,
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
        observation: FasterWhisperRuntimeCapabilityObservationV1,
        decision: FasterWhisperRuntimeDecisionV1,
        admission_ref: str,
        admission_evaluated_at: str,
        task023_config_sha256: str,
        task023_execution_sha256: str,
    ) -> dict[str, object]:
        body = engine._publication_set_body(
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
        body["publication_set_version"] = "2.0.0"
        body.update({
            "runtime_request": self.runtime_request.to_dict(),
            "runtime_capability_observation": observation.to_dict(),
            "runtime_decision": decision.to_dict(),
            "runtime_admission_ref": admission_ref,
            "admission_evaluated_at": admission_evaluated_at,
            "task023_config_sha256": task023_config_sha256,
            "task023_execution_sha256": task023_execution_sha256,
            "model_download_authorized": False,
        })
        return body

    def _store_v2_publication_set(self, engine: _Task036LocalTranscriptionOperationEngine, values: dict[str, bytes], **kwargs: Any) -> str:
        body = self._v2_publication_body(engine, values, **kwargs)
        set_sha256 = sha256_bytes(canonical_json_bytes(body))
        document = {**body, "publication_set_sha256": set_sha256}
        # The immutable identity remains the canonical body digest.  The v2
        # document itself is ordinary deterministic JSON, matching the public
        # report spelling while keeping the legacy v1 byte path untouched.
        payloads = {
            **values,
            "publication-set.json": json.dumps(
                document, ensure_ascii=False, sort_keys=True,
            ).encode("utf-8"),
        }
        if len(payloads["publication-set.json"]) > self._PUBLICATION_SET_MAX_BYTES:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_PUBLICATION_SET_INVALID", "Runtime publication metadata is too large", ProductErrorCategory.DATA_INTEGRITY)
        engine._write_immutable_publication_payloads(kwargs["operation_id"], payloads)
        return set_sha256

    def transcribe_local_media(
        self,
        *,
        project_id: str,
        source_path: Path,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> RuntimeManagedLocalTranscriptionOutcomeV2:
        return self._engine().transcribe_runtime_managed(
            self,
            project_id=project_id,
            source_path=source_path,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
        )

    def _decode_v2_publication_set(
        self,
        engine: _Task036LocalTranscriptionOperationEngine,
        values: dict[str, bytes],
        raw: bytes,
        operation_id: str,
        expected_set_sha256: str,
        *,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> tuple[TranscriptManifest, FasterWhisperRuntimeDecisionV1]:
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Runtime publication manifest is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        required = {
            "publication_set_version", "project_id", "operation_id", "source_asset_id", "source_asset_sha256",
            "provider_id", "model_id", "execution_config_sha256", "transcript_manifest_sha256", "files",
            "runtime_request", "runtime_capability_observation", "runtime_decision", "runtime_admission_ref",
            "admission_evaluated_at", "task023_config_sha256", "task023_execution_sha256",
            "model_download_authorized", "publication_set_sha256",
        }
        if not isinstance(document, dict) or set(document) != required:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Runtime publication manifest schema is invalid", ProductErrorCategory.DATA_INTEGRITY)
        body = dict(document)
        observed_sha = body.pop("publication_set_sha256")
        if not isinstance(observed_sha, str) or observed_sha != expected_set_sha256 or sha256_bytes(canonical_json_bytes(body)) != expected_set_sha256:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Runtime publication set digest is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            request, observation, decision = _validate_v2_admission_chain(
                document,
                expected_source_sha256=source_asset_sha256,
                expected_request=self.runtime_request,
            )
        except (TypeError, ValueError) as exc:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Runtime admission chain is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        admission_ref = self._admission_ref(source_asset_sha256, decision)
        provider_id, model_id, execution_config_sha256 = self._execution_identity()
        config = self._effective_config(decision)
        diagnostic = build_execution_identity_for_config(config, provider_id=provider_id, model_id=model_id, source_sha256=source_asset_sha256, requested_language=self.language)
        if document["task023_config_sha256"] != diagnostic.config_sha256 or document["task023_execution_sha256"] != diagnostic.execution_sha256:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "TASK-023 diagnostic identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        transcript = engine._validate_publication(values, source_asset_id=source_asset_id, provider_id=provider_id, model_id=model_id)
        expected = self._v2_publication_body(
            engine, values, project_id=project_id, operation_id=operation_id,
            source_asset_id=source_asset_id, source_asset_sha256=source_asset_sha256,
            provider_id=provider_id, model_id=model_id, execution_config_sha256=execution_config_sha256,
            transcript_manifest_sha256=transcript.to_dict()["manifest_sha256"], observation=observation,
            decision=decision, admission_ref=admission_ref,
            admission_evaluated_at=document["admission_evaluated_at"],
            task023_config_sha256=diagnostic.config_sha256, task023_execution_sha256=diagnostic.execution_sha256,
        )
        if body != expected:
            raise ProductError("ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE", "Runtime publication identity differs from the operation", ProductErrorCategory.DATA_INTEGRITY)
        return transcript, decision

    def _runtime_lease(self, project_id: str, source_asset_id: str, source_asset_sha256: str):
        engine = self._engine()
        try:
            return engine._require_existing_v2_lease(
                project_id, source_asset_id, source_asset_sha256,
                error_code="ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
            )
        except ProductError:
            return None

    @staticmethod
    def classify_runtime_recovery(
        operation: Any | None,
        *,
        lease: Any | None,
        slot: Any | None,
        expected_operation_key: str,
        expected_owner_ref: str,
        expected_source_sha256: str,
        validated_publication_ref: str | None = None,
        validated_request: FasterWhisperRuntimeRequestV1 | None = None,
        validated_observation: FasterWhisperRuntimeCapabilityObservationV1 | None = None,
        validated_decision: FasterWhisperRuntimeDecisionV1 | None = None,
    ) -> str:
        """Pure classifier over concrete coordinates, never caller proof flags."""

        if operation is None:
            return "PENDING_ADMISSION"
        if (
            lease is None
            or getattr(lease, "status", None) != "IN_PROGRESS"
            or type(getattr(lease, "attempt", None)) is not int
            or getattr(lease, "attempt", None) != 0
            or getattr(lease, "result_ref", None) != expected_owner_ref
            or getattr(operation, "idempotency_key", None) != expected_operation_key
        ):
            return "CORRUPT_BLOCKED"
        status, ref, attempt = getattr(operation, "status", None), getattr(operation, "result_ref", None), getattr(operation, "attempt", None)
        if type(attempt) is not int or attempt < 0:
            return "CORRUPT_BLOCKED"
        typed = _V2_ADMISSION_RE.fullmatch(ref) if isinstance(ref, str) else None
        if status == "PENDING" and ref is None:
            return "PENDING_ADMISSION"
        if typed is not None:
            if typed.group(1) != expected_source_sha256.removeprefix("sha256:"):
                return "CORRUPT_BLOCKED"
            if status == "IN_PROGRESS" and attempt >= 1:
                return "ACTIVE_UNKNOWN"
            if status == "PARTIAL" and attempt >= 1:
                return "ADJUDICATION_REQUIRED_NO_PUBLICATION"
            if status == "FAILED" and attempt >= 1:
                if not (
                    isinstance(validated_request, FasterWhisperRuntimeRequestV1)
                    and isinstance(validated_observation, FasterWhisperRuntimeCapabilityObservationV1)
                    and isinstance(validated_decision, FasterWhisperRuntimeDecisionV1)
                ):
                    return "CORRUPT_BLOCKED"
                try:
                    request = FasterWhisperRuntimeRequestV1.from_dict(validated_request.to_dict())
                    observation = FasterWhisperRuntimeCapabilityObservationV1.from_dict(
                        validated_observation.to_dict(), request=request,
                    )
                    decision = FasterWhisperRuntimeDecisionV1.from_dict(
                        validated_decision.to_dict(), request=request,
                    )
                    resolved = resolve_runtime_decision(request, observation)
                except (TypeError, ValueError):
                    return "CORRUPT_BLOCKED"
                if (
                    resolved.to_dict() != decision.to_dict()
                    or decision.capability_observation_sha256 != observation.record_sha256
                    or decision.runtime_request_sha256 != request.record_sha256
                    or typed.group(2) != decision.record_sha256.removeprefix("sha256:")
                ):
                    return "CORRUPT_BLOCKED"
                return "FAILED_TERMINAL"
            return "CORRUPT_BLOCKED"
        if ref == validated_publication_ref and validated_decision is not None:
            if status == "PARTIAL" and attempt >= 1:
                return "RECOVERABLE_PUBLICATION"
            if status == "COMPLETED" and attempt >= 1:
                return "VERIFICATION_ONLY"
        if status == "FAILED" and ref is None and attempt == 0 and (
            slot is None or (
                getattr(slot, "status", None) == "PENDING"
                and getattr(slot, "result_ref", None) != getattr(operation, "operation_id", None)
            )
        ):
            return "FAILED_TERMINAL"
        return "CORRUPT_BLOCKED"

    def _classify_validated_runtime_recovery(
        self,
        operation: Any | None,
        *,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        publication: FasterWhisperRuntimeDecisionV1 | None = None,
    ) -> str:
        """Classify only concrete store coordinates and parsed immutable facts."""

        if operation is None:
            return "PENDING_ADMISSION"
        operation_key = self._operation_key(project_id, source_asset_id, source_asset_sha256)
        if (
            operation.job_id != self.production_job_id
            or operation.command_type != "task036.local_transcription.v2"
            or operation.idempotency_key != operation_key
        ):
            return "CORRUPT_BLOCKED"
        lease = self._runtime_lease(project_id, source_asset_id, source_asset_sha256)
        slot = self.store.find_operation(self.production_job_id, self._engine()._slot_key(project_id))
        if slot is not None and (
            slot.job_id != self.production_job_id
            or slot.command_type != "task036.local_transcription_output_slot"
            or slot.status not in {"PENDING", "IN_PROGRESS"}
        ):
            return "CORRUPT_BLOCKED"
        guard_key = self._engine()._cross_version_guard_key(project_id, source_asset_id, source_asset_sha256)
        return self.classify_runtime_recovery(
            operation,
            lease=lease,
            slot=slot,
            expected_operation_key=operation_key,
            expected_owner_ref="task098-runtime-owner:v2:" + guard_key.rsplit("-", 1)[-1],
            expected_source_sha256=source_asset_sha256,
            validated_publication_ref=(operation.result_ref if publication is not None else None),
            validated_decision=publication,
        )

    def recovery_state(
        self,
        *,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> str:
        operation = self.store.find_operation(self.production_job_id, self._operation_key(project_id, source_asset_id, source_asset_sha256))
        if operation is None:
            return "PENDING_ADMISSION"
        if isinstance(operation.result_ref, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", operation.result_ref):
            try:
                engine = self._engine()
                values, raw = engine._read_immutable_publication_payloads(operation.operation_id)
                _transcript, decision = self._decode_v2_publication_set(
                    engine, values, raw, operation.operation_id, operation.result_ref,
                    project_id=project_id, source_asset_id=source_asset_id,
                    source_asset_sha256=source_asset_sha256,
                )
            except ProductError:
                return "CORRUPT_BLOCKED"
            return self._classify_validated_runtime_recovery(
                operation, project_id=project_id, source_asset_id=source_asset_id,
                source_asset_sha256=source_asset_sha256, publication=decision,
            )
        return self._classify_validated_runtime_recovery(
            operation, project_id=project_id, source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
        )

    def recover_local_media(
        self,
        *,
        project_id: str,
        source_path: Path,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> RuntimeManagedLocalTranscriptionOutcomeV2:
        return self._engine().recover_runtime_managed(
            self,
            project_id=project_id,
            source_path=source_path,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
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
        self._engine().finalize_runtime_managed(
            self,
            project_id=project_id,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            transcript_manifest_sha256=transcript_manifest_sha256,
            operation_id=operation_id,
            slot_operation_id=slot_operation_id,
            publication_set_sha256=publication_set_sha256,
        )

    def recovery_required(self, project_id: str, source_asset_id: str, source_asset_sha256: str) -> bool:
        operation = self.store.find_operation(
            self.production_job_id,
            self._operation_key(project_id, source_asset_id, source_asset_sha256),
        )
        if operation is None or operation.command_type != "task036.local_transcription.v2":
            return False
        if not isinstance(operation.result_ref, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", operation.result_ref) is None:
            return False
        try:
            engine = self._engine()
            values, raw = engine._read_immutable_publication_payloads(operation.operation_id)
            _transcript, decision = self._decode_v2_publication_set(
                engine, values, raw, operation.operation_id, operation.result_ref,
                project_id=project_id, source_asset_id=source_asset_id,
                source_asset_sha256=source_asset_sha256,
            )
        except ProductError:
            return False
        return self._classify_validated_runtime_recovery(
            operation,
            project_id=project_id,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            publication=decision,
        ) == "RECOVERABLE_PUBLICATION"


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
