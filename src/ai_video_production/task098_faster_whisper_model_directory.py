"""Pure TASK-098 contract for an offline FasterWhisper model directory.

The module has no filesystem, model, network, download, or inference behaviour.
It validates bounded observations supplied by a later trusted inspector and
produces a path-free public projection.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import json
from pathlib import Path
from typing import Any, ClassVar, Iterable, Mapping

from jsonschema import Draft202012Validator

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_NAME = "task098-faster-whisper-model-directory.schema.json"
SCHEMA_VERSION = "1.0.0"
RECORD_TYPE = "FasterWhisperModelDirectoryInspectionV1"
PUBLIC_RECORD_TYPE = "FasterWhisperModelDirectoryInspectionPublicV1"
RECORD_DOMAIN = b"bvp.task098.faster-whisper-model-directory.v1\0"
MANIFEST_DOMAIN = b"bvp.task098.faster-whisper-model-manifest.v1\0"

READY_REASON = "MODEL_DIRECTORY_VALID"
BLOCKED_REASONS = frozenset(
    {
        "PATH_NOT_DIRECTORY",
        "PATH_ALIAS_UNSAFE",
        "DIRECTORY_SCAN_FAILED",
        "DIRECTORY_ENTRY_LIMIT_EXCEEDED",
        "REQUIRED_FILE_MISSING",
        "FILE_NOT_REGULAR",
        "FILE_ALIAS_UNSAFE",
        "FILE_SIZE_INVALID",
        "FILE_HASH_INVALID",
        "VOCABULARY_SET_INVALID",
        "REQUIRED_JSON_INVALID",
    }
)

_FIXED_FILES = frozenset(
    {"config.json", "model.bin", "tokenizer.json", "preprocessor_config.json"}
)
_VOCABULARY_FILES = frozenset({"vocabulary.txt", "vocabulary.json"})
_ALLOWED_FILES = _FIXED_FILES | _VOCABULARY_FILES
_REQUIRED_FIXED = frozenset({"config.json", "model.bin", "tokenizer.json"})
_FILE_SIZE_LIMITS = {
    "config.json": 4 * 1024 * 1024,
    "model.bin": 32 * 1024 * 1024 * 1024,
    "tokenizer.json": 128 * 1024 * 1024,
    "vocabulary.txt": 128 * 1024 * 1024,
    "vocabulary.json": 128 * 1024 * 1024,
    "preprocessor_config.json": 4 * 1024 * 1024,
}
_PRIVATE_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "outcome",
        "reason_codes",
        "model_id",
        "required_files_present",
        "optional_preprocessor_config_present",
        "private_locator_sha256",
        "model_manifest_sha256",
        "files",
        "model_download_authorized",
        "model_load_started",
        "inference_started",
        "network_used",
        "execution_authorized",
        "record_sha256",
    }
)


def _exact(value: Mapping[str, Any], fields: frozenset[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _schema(definition: str, value: Mapping[str, Any]) -> None:
    try:
        with resources.files("ai_video_production.schema_resources").joinpath(
            SCHEMA_NAME
        ).open("r", encoding="utf-8") as source:
            document = json.load(source)
        validator = Draft202012Validator(
            {
                "$schema": document["$schema"],
                "$defs": document["$defs"],
                "$ref": f"#/$defs/{definition}",
            }
        )
        if next(validator.iter_errors(dict(value)), None) is not None:
            raise ValueError("schema validation failed")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("model directory schema validation failed") from exc


@dataclass(frozen=True, slots=True)
class FasterWhisperModelFileObservationV1:
    name: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        if self.name not in _ALLOWED_FILES:
            raise ValueError("file name is outside the closed model contract")
        if type(self.size_bytes) is not int or not 1 <= self.size_bytes <= _FILE_SIZE_LIMITS[self.name]:
            raise ValueError("file size is outside the allowed bound")
        validate_sha256(self.sha256, field_name="file sha256")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FasterWhisperModelFileObservationV1":
        _exact(value, frozenset({"name", "size_bytes", "sha256"}), "model file observation")
        _schema("file_observation", value)
        return cls(name=value["name"], size_bytes=value["size_bytes"], sha256=value["sha256"])

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "size_bytes": self.size_bytes, "sha256": self.sha256}


def _normalize_files(
    values: Iterable[FasterWhisperModelFileObservationV1],
) -> tuple[FasterWhisperModelFileObservationV1, ...]:
    files = tuple(values)
    if not files or any(type(item) is not FasterWhisperModelFileObservationV1 for item in files):
        raise ValueError("files must contain validated model file observations")
    names = [item.name for item in files]
    if len(names) != len(set(names)):
        raise ValueError("model file names must be unique")
    names_set = set(names)
    if not _REQUIRED_FIXED.issubset(names_set):
        raise ValueError("required model files are missing")
    if len(names_set & _VOCABULARY_FILES) != 1:
        raise ValueError("exactly one supported vocabulary file is required")
    return tuple(sorted(files, key=lambda item: item.name))


def _manifest_sha256(files: tuple[FasterWhisperModelFileObservationV1, ...]) -> str:
    return sha256_bytes(MANIFEST_DOMAIN + canonical_json_bytes([item.to_dict() for item in files]))


def _record_sha256(body: Mapping[str, Any]) -> str:
    return sha256_bytes(RECORD_DOMAIN + canonical_json_bytes(dict(body)))


@dataclass(frozen=True, slots=True, init=False)
class FasterWhisperModelDirectoryInspectionV1:
    outcome: str
    reason_codes: tuple[str, ...]
    model_id: str | None
    required_files_present: bool
    optional_preprocessor_config_present: bool
    private_locator_sha256: str | None
    model_manifest_sha256: str | None
    files: tuple[FasterWhisperModelFileObservationV1, ...]
    record_sha256: str

    record_type: ClassVar[str] = RECORD_TYPE
    schema_version: ClassVar[str] = SCHEMA_VERSION
    model_download_authorized: ClassVar[bool] = False
    model_load_started: ClassVar[bool] = False
    inference_started: ClassVar[bool] = False
    network_used: ClassVar[bool] = False
    execution_authorized: ClassVar[bool] = False

    @classmethod
    def ready(
        cls,
        *,
        private_locator_sha256: str,
        files: Iterable[FasterWhisperModelFileObservationV1],
    ) -> "FasterWhisperModelDirectoryInspectionV1":
        locator = validate_sha256(private_locator_sha256, field_name="private_locator_sha256")
        normalized = _normalize_files(files)
        return cls._build(
            outcome="READY",
            reason_codes=(READY_REASON,),
            model_id="local-model-" + locator.removeprefix("sha256:")[:12],
            required_files_present=True,
            optional_preprocessor_config_present=any(
                item.name == "preprocessor_config.json" for item in normalized
            ),
            private_locator_sha256=locator,
            model_manifest_sha256=_manifest_sha256(normalized),
            files=normalized,
        )

    @classmethod
    def blocked(cls, *reason_codes: str) -> "FasterWhisperModelDirectoryInspectionV1":
        reasons = tuple(sorted(reason_codes))
        if not reasons or len(reasons) != len(set(reasons)) or any(
            reason not in BLOCKED_REASONS for reason in reasons
        ):
            raise ValueError("blocked reason codes must be unique values from the closed contract")
        return cls._build(
            outcome="BLOCKED",
            reason_codes=reasons,
            model_id=None,
            required_files_present=False,
            optional_preprocessor_config_present=False,
            private_locator_sha256=None,
            model_manifest_sha256=None,
            files=(),
        )

    @classmethod
    def _build(
        cls,
        *,
        outcome: str,
        reason_codes: tuple[str, ...],
        model_id: str | None,
        required_files_present: bool,
        optional_preprocessor_config_present: bool,
        private_locator_sha256: str | None,
        model_manifest_sha256: str | None,
        files: tuple[FasterWhisperModelFileObservationV1, ...],
        record_sha256: str | None = None,
    ) -> "FasterWhisperModelDirectoryInspectionV1":
        body = {
            "record_type": RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "outcome": outcome,
            "reason_codes": list(reason_codes),
            "model_id": model_id,
            "required_files_present": required_files_present,
            "optional_preprocessor_config_present": optional_preprocessor_config_present,
            "private_locator_sha256": private_locator_sha256,
            "model_manifest_sha256": model_manifest_sha256,
            "files": [item.to_dict() for item in files],
            "model_download_authorized": False,
            "model_load_started": False,
            "inference_started": False,
            "network_used": False,
            "execution_authorized": False,
        }
        expected = _record_sha256(body)
        if record_sha256 is not None and validate_sha256(
            record_sha256, field_name="record_sha256"
        ) != expected:
            raise ValueError("model directory inspection digest mismatch")
        instance = object.__new__(cls)
        for name, value in (
            ("outcome", outcome),
            ("reason_codes", reason_codes),
            ("model_id", model_id),
            ("required_files_present", required_files_present),
            ("optional_preprocessor_config_present", optional_preprocessor_config_present),
            ("private_locator_sha256", private_locator_sha256),
            ("model_manifest_sha256", model_manifest_sha256),
            ("files", files),
            ("record_sha256", expected),
        ):
            object.__setattr__(instance, name, value)
        return instance

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FasterWhisperModelDirectoryInspectionV1":
        _exact(value, _PRIVATE_FIELDS, RECORD_TYPE)
        _schema("inspection", value)
        if value["record_type"] != RECORD_TYPE or value["schema_version"] != SCHEMA_VERSION:
            raise ValueError("model directory inspection identity/version is invalid")
        if any(
            value[field] is not False
            for field in (
                "model_download_authorized",
                "model_load_started",
                "inference_started",
                "network_used",
                "execution_authorized",
            )
        ):
            raise ValueError("model directory inspection cannot represent effects")
        if value["outcome"] == "READY":
            files = _normalize_files(
                FasterWhisperModelFileObservationV1.from_dict(item) for item in value["files"]
            )
            locator = validate_sha256(
                value["private_locator_sha256"], field_name="private_locator_sha256"
            )
            if tuple(value["reason_codes"]) != (READY_REASON,):
                raise ValueError("ready inspection reason is invalid")
            if value["model_id"] != "local-model-" + locator.removeprefix("sha256:")[:12]:
                raise ValueError("ready inspection model ID does not bind the locator")
            if value["required_files_present"] is not True:
                raise ValueError("ready inspection must confirm required files")
            optional = any(item.name == "preprocessor_config.json" for item in files)
            if value["optional_preprocessor_config_present"] is not optional:
                raise ValueError("optional preprocessor presence is inconsistent")
            manifest = _manifest_sha256(files)
            if value["model_manifest_sha256"] != manifest:
                raise ValueError("model manifest digest mismatch")
            return cls._build(
                outcome="READY",
                reason_codes=(READY_REASON,),
                model_id=value["model_id"],
                required_files_present=True,
                optional_preprocessor_config_present=optional,
                private_locator_sha256=locator,
                model_manifest_sha256=manifest,
                files=files,
                record_sha256=value["record_sha256"],
            )
        reasons = tuple(value["reason_codes"])
        if value["outcome"] != "BLOCKED" or reasons != tuple(sorted(set(reasons))) or any(
            reason not in BLOCKED_REASONS for reason in reasons
        ):
            raise ValueError("blocked inspection reasons are invalid")
        if any(
            (
                value["model_id"] is not None,
                value["required_files_present"] is not False,
                value["optional_preprocessor_config_present"] is not False,
                value["private_locator_sha256"] is not None,
                value["model_manifest_sha256"] is not None,
                value["files"] != [],
            )
        ):
            raise ValueError("blocked inspection cannot bind a model or private observation")
        return cls._build(
            outcome="BLOCKED",
            reason_codes=reasons,
            model_id=None,
            required_files_present=False,
            optional_preprocessor_config_present=False,
            private_locator_sha256=None,
            model_manifest_sha256=None,
            files=(),
            record_sha256=value["record_sha256"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "outcome": self.outcome,
            "reason_codes": list(self.reason_codes),
            "model_id": self.model_id,
            "required_files_present": self.required_files_present,
            "optional_preprocessor_config_present": self.optional_preprocessor_config_present,
            "private_locator_sha256": self.private_locator_sha256,
            "model_manifest_sha256": self.model_manifest_sha256,
            "files": [item.to_dict() for item in self.files],
            "model_download_authorized": False,
            "model_load_started": False,
            "inference_started": False,
            "network_used": False,
            "execution_authorized": False,
            "record_sha256": self.record_sha256,
        }

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "record_type": PUBLIC_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "outcome": self.outcome,
            "reason_codes": list(self.reason_codes),
            "model_id": self.model_id,
            "required_files_present": self.required_files_present,
            "optional_preprocessor_config_present": self.optional_preprocessor_config_present,
            "model_download_authorized": False,
            "model_load_started": False,
            "inference_started": False,
            "network_used": False,
            "execution_authorized": False,
        }


def parse_model_directory_inspection(
    value: Mapping[str, Any],
) -> FasterWhisperModelDirectoryInspectionV1:
    return FasterWhisperModelDirectoryInspectionV1.from_dict(value)


def validate_schema_mirror() -> None:
    root = Path(__file__).resolve().parents[2]
    canonical = root / "schemas" / SCHEMA_NAME
    packaged = resources.files("ai_video_production.schema_resources").joinpath(SCHEMA_NAME)
    if canonical.read_bytes() != packaged.read_bytes():
        raise ValueError("model directory schema mirror mismatch")
