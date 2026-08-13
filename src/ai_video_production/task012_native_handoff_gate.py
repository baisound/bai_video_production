"""TASK-012 EDITOR_WORK package and optional Cubase-return native acceptance gate."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import wave
from typing import Any

from .atomic import AtomicJsonWriter
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _json_object(path: Path, *, code: str, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise ProductError(code, f"{label} must be a non-empty regular non-symlink file", ProductErrorCategory.DATA_INTEGRITY)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductError(code, f"{label} is not valid UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
    if not isinstance(value, dict):
        raise ProductError(code, f"{label} root must be a JSON object", ProductErrorCategory.DATA_INTEGRITY)
    return value


def _verify_self_hash(payload: dict[str, Any], *, field: str, code: str, label: str) -> str:
    expected = payload.get(field)
    if not isinstance(expected, str) or not expected.startswith("sha256:"):
        raise ProductError(code, f"{label} is missing {field}", ProductErrorCategory.DATA_INTEGRITY)
    body = dict(payload)
    body.pop(field, None)
    observed = sha256_bytes(canonical_json_bytes(body))
    if observed != expected:
        raise ProductError(code, f"{label} self-hash is invalid", ProductErrorCategory.DATA_INTEGRITY)
    return expected




def _resolve_regular_under_root(root: Path, target: Path, *, code: str, label: str) -> Path:
    if target.is_symlink() or not target.is_file() or target.stat().st_size <= 0:
        raise ProductError(code, f"{label} must be a non-empty regular non-symlink file", ProductErrorCategory.DATA_INTEGRITY)
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ProductError(
            "ERR_TASK012_NATIVE_MANIFEST_PATH_ESCAPE",
            f"{label} escapes the EDITOR_WORK root",
            ProductErrorCategory.SECURITY,
        ) from exc
    return resolved

def _safe_relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ProductError(
            "ERR_TASK012_NATIVE_MANIFEST_PATH_INVALID",
            "EDITOR_WORK manifest paths must be non-empty POSIX relative paths",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductError(
            "ERR_TASK012_NATIVE_MANIFEST_PATH_INVALID",
            "EDITOR_WORK manifest contains an unsafe relative path",
            ProductErrorCategory.DATA_INTEGRITY,
            details={"relative_path": value},
        )
    return value


@dataclass(frozen=True, slots=True)
class Task012NativeHandoffRequest:
    editor_work_root: Path
    require_cubase_return: bool = False


class Task012NativeHandoffGate:
    """Verify durable EDITOR_WORK linkage and the bounded 48 kHz Cubase return contract."""

    def __init__(self, request: Task012NativeHandoffRequest) -> None:
        self.request = request

    def _root(self) -> Path:
        supplied = self.request.editor_work_root.expanduser()
        if supplied.is_symlink():
            raise ProductError(
                "ERR_TASK012_NATIVE_EDITOR_WORK_INVALID",
                "EDITOR_WORK root must not be a symlink",
                ProductErrorCategory.VALIDATION,
            )
        root = supplied.resolve()
        if not root.is_dir():
            raise ProductError(
                "ERR_TASK012_NATIVE_EDITOR_WORK_INVALID",
                "EDITOR_WORK root must be a regular directory",
                ProductErrorCategory.VALIDATION,
            )
        return root

    @staticmethod
    def _verify_file_record(root: Path, record: Any) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise ProductError(
                "ERR_TASK012_NATIVE_MANIFEST_FILE_INVALID",
                "EDITOR_WORK file record must be an object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        role = record.get("role")
        relative = _safe_relative(record.get("relative_path"))
        expected_sha = record.get("sha256")
        expected_size = record.get("size_bytes")
        if not isinstance(role, str) or not role:
            raise ProductError(
                "ERR_TASK012_NATIVE_MANIFEST_FILE_INVALID",
                "EDITOR_WORK file record role is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if not isinstance(expected_sha, str) or not expected_sha.startswith("sha256:") or not isinstance(expected_size, int):
            raise ProductError(
                "ERR_TASK012_NATIVE_MANIFEST_FILE_INVALID",
                "EDITOR_WORK file record checksum/size is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        target = root.joinpath(*PurePosixPath(relative).parts)
        if target.is_symlink() or not target.is_file() or target.stat().st_size <= 0:
            raise ProductError(
                "ERR_TASK012_NATIVE_HANDOFF_FILE_MISSING",
                "EDITOR_WORK manifest references a missing/non-regular file",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"role": role, "relative_path": relative},
            )
        try:
            resolved_target = target.resolve(strict=True)
            resolved_target.relative_to(root)
        except (OSError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK012_NATIVE_MANIFEST_PATH_ESCAPE",
                "EDITOR_WORK manifest path escapes the handoff root",
                ProductErrorCategory.SECURITY,
                details={"role": role, "relative_path": relative},
            ) from exc
        observed_size = resolved_target.stat().st_size
        observed_sha = _sha256_file(resolved_target)
        if observed_size != expected_size or observed_sha != expected_sha:
            raise ProductError(
                "ERR_TASK012_NATIVE_HANDOFF_FILE_CHANGED",
                "EDITOR_WORK file differs from its manifest identity",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"role": role, "relative_path": relative},
            )
        return {"role": role, "relative_path": relative, "sha256": observed_sha, "size_bytes": observed_size}

    @staticmethod
    def _verify_cross_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
        edit = _json_object(root / "MANIFESTS" / "edit-plan.json", code="ERR_TASK012_NATIVE_EDIT_PLAN_INVALID", label="Edit Plan")
        assembly = _json_object(root / "MANIFESTS" / "resolve-assembly-report.json", code="ERR_TASK012_NATIVE_ASSEMBLY_INVALID", label="Resolve assembly report")
        qa = _json_object(root / "MANIFESTS" / "render-qa.json", code="ERR_TASK012_NATIVE_RENDER_QA_INVALID", label="Render QA report")

        _verify_self_hash(edit, field="plan_sha256", code="ERR_TASK012_NATIVE_EDIT_PLAN_HASH", label="Edit Plan")
        _verify_self_hash(qa, field="report_sha256", code="ERR_TASK012_NATIVE_RENDER_QA_HASH", label="Render QA report")

        if edit.get("task_owner") != "TASK-007" or edit.get("approval_state") != "APPROVED" or edit.get("ready_for_assembly") is not True:
            raise ProductError(
                "ERR_TASK012_NATIVE_EDIT_PLAN_NOT_APPROVED",
                "EDITOR_WORK must contain an approved TASK-007 Edit Plan",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if assembly.get("task_owner") != "TASK-010" or assembly.get("status") not in {"APPLIED", "ALREADY_APPLIED"}:
            raise ProductError(
                "ERR_TASK012_NATIVE_ASSEMBLY_NOT_COMPLETE",
                "EDITOR_WORK must contain a completed TASK-010 assembly report",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if qa.get("task_owner") != "TASK-011" or qa.get("status") != "PASS":
            raise ProductError(
                "ERR_TASK012_NATIVE_RENDER_QA_NOT_PASS",
                "EDITOR_WORK must contain a passing TASK-011 Render QA report",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        links = {
            "edit_plan_sha256": edit.get("plan_sha256"),
            "assembly_sha256": assembly.get("assembly_sha256"),
            "render_qa_report_sha256": qa.get("report_sha256"),
        }
        for key, observed in links.items():
            expected = manifest.get(key)
            if expected != observed or not isinstance(observed, str) or not observed.startswith("sha256:"):
                raise ProductError(
                    "ERR_TASK012_NATIVE_MANIFEST_LINK_MISMATCH",
                    "EDITOR_WORK manifest does not match its embedded upstream report identities",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"field": key},
                )
        return links

    @staticmethod
    def _verify_cubase_return(root: Path, *, required: bool, enabled: bool) -> dict[str, Any]:
        record_path = root / "AUDIO_ROUNDTRIP" / "audio-roundtrip-return.json"
        wav_path = root / "AUDIO_ROUNDTRIP" / "RETURN" / "cubase-return.wav"

        if not record_path.exists() and not wav_path.exists():
            if required:
                raise ProductError(
                    "ERR_TASK012_NATIVE_CUBASE_RETURN_REQUIRED",
                    "native TASK-012 close requires an accepted Cubase return",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                )
            return {"status": "NOT_PRESENT", "required": False, "enabled": enabled}
        if not enabled:
            raise ProductError(
                "ERR_TASK012_NATIVE_CUBASE_RETURN_UNEXPECTED",
                "Cubase return exists although this EDITOR_WORK manifest did not enable audio round-trip",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if not record_path.exists() or not wav_path.exists():
            raise ProductError(
                "ERR_TASK012_NATIVE_CUBASE_RETURN_INCOMPLETE",
                "Cubase return record and WAV must both exist as regular files",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        record_path = _resolve_regular_under_root(
            root, record_path, code="ERR_TASK012_NATIVE_CUBASE_RETURN_INCOMPLETE", label="Cubase return record"
        )
        wav_path = _resolve_regular_under_root(
            root, wav_path, code="ERR_TASK012_NATIVE_CUBASE_RETURN_INCOMPLETE", label="Cubase return WAV"
        )
        record = _json_object(record_path, code="ERR_TASK012_NATIVE_CUBASE_RETURN_INVALID", label="Cubase return record")
        _verify_self_hash(
            record,
            field="record_sha256",
            code="ERR_TASK012_NATIVE_CUBASE_RETURN_RECORD_HASH",
            label="Cubase return record",
        )
        if record.get("task_owner") != "TASK-012" or record.get("daw") != "CUBASE" or record.get("status") != "ACCEPTED":
            raise ProductError(
                "ERR_TASK012_NATIVE_CUBASE_RETURN_INVALID",
                "Cubase return record does not represent an accepted TASK-012 return",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if record.get("relative_path") != "AUDIO_ROUNDTRIP/RETURN/cubase-return.wav":
            raise ProductError(
                "ERR_TASK012_NATIVE_CUBASE_RETURN_INVALID",
                "Cubase return record has a non-canonical path",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if record.get("sha256") != _sha256_file(wav_path) or record.get("size_bytes") != wav_path.stat().st_size:
            raise ProductError(
                "ERR_TASK012_NATIVE_CUBASE_RETURN_CHANGED",
                "Cubase return WAV changed after registration",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            with wave.open(str(wav_path), "rb") as wav:
                sample_rate = wav.getframerate()
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                frames = wav.getnframes()
        except (wave.Error, EOFError) as exc:
            raise ProductError(
                "ERR_TASK012_NATIVE_CUBASE_RETURN_INVALID",
                "Cubase return is not a readable PCM WAV",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        duration_us = int(frames * 1_000_000 / sample_rate) if sample_rate else 0
        expected_fields = {
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width_bytes": sample_width,
            "duration_us": duration_us,
        }
        if sample_rate != 48_000:
            raise ProductError(
                "ERR_TASK012_NATIVE_CUBASE_RETURN_SAMPLE_RATE",
                "native Cubase return must remain 48 kHz PCM WAV",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"sample_rate": sample_rate},
            )
        for key, value in expected_fields.items():
            if record.get(key) != value:
                raise ProductError(
                    "ERR_TASK012_NATIVE_CUBASE_RETURN_METADATA_MISMATCH",
                    "Cubase return record no longer matches the WAV metadata",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"field": key},
                )
        if record.get("automatic_cubase_project_conversion") is not False:
            raise ProductError(
                "ERR_TASK012_NATIVE_CUBASE_SCOPE_VIOLATION",
                "TASK-012 must not claim automatic Cubase project conversion",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return {
            "status": "PASS",
            "required": required,
            "enabled": enabled,
            "sha256": record.get("sha256"),
            "sample_rate": sample_rate,
            "channels": channels,
            "duration_us": duration_us,
            "path_persisted": False,
        }

    def run(self, *, output_path: str | Path) -> dict[str, Any]:
        root = self._root()
        manifest = _json_object(
            root / "editor-handoff-manifest.json",
            code="ERR_TASK012_NATIVE_MANIFEST_INVALID",
            label="EDITOR_WORK manifest",
        )
        _verify_self_hash(
            manifest,
            field="manifest_sha256",
            code="ERR_TASK012_NATIVE_MANIFEST_HASH",
            label="EDITOR_WORK manifest",
        )
        if manifest.get("task_owner") != "TASK-012" or manifest.get("handoff_id") != root.name:
            raise ProductError(
                "ERR_TASK012_NATIVE_MANIFEST_IDENTITY",
                "EDITOR_WORK directory identity does not match its TASK-012 manifest",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if manifest.get("absolute_paths_persisted") is not False or manifest.get("editor_work_root") != ".":
            raise ProductError(
                "ERR_TASK012_NATIVE_PATH_PRIVACY",
                "EDITOR_WORK manifest violates its relative-path-only contract",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        files = manifest.get("files")
        if not isinstance(files, list) or not files:
            raise ProductError(
                "ERR_TASK012_NATIVE_MANIFEST_FILES_INVALID",
                "EDITOR_WORK manifest must contain file records",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        verified: list[dict[str, Any]] = []
        seen: set[str] = set()
        for record in files:
            item = self._verify_file_record(root, record)
            if item["relative_path"] in seen:
                raise ProductError(
                    "ERR_TASK012_NATIVE_MANIFEST_PATH_DUPLICATE",
                    "EDITOR_WORK manifest contains a duplicate file path",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            seen.add(item["relative_path"])
            verified.append(item)

        required_roles = {"EDIT_PLAN", "RESOLVE_ASSEMBLY_REPORT", "RENDER_QA", "RENDER_MASTER"}
        observed_roles = {item["role"] for item in verified}
        if not required_roles.issubset(observed_roles):
            raise ProductError(
                "ERR_TASK012_NATIVE_REQUIRED_FILE_ROLE_MISSING",
                "EDITOR_WORK is missing a required canonical file role",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"missing_roles": sorted(required_roles - observed_roles)},
            )
        for role in sorted(required_roles):
            matches = [item for item in verified if item["role"] == role]
            if len(matches) != 1:
                raise ProductError(
                    "ERR_TASK012_NATIVE_REQUIRED_FILE_ROLE_AMBIGUOUS",
                    "EDITOR_WORK must contain exactly one file for each required canonical role",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"role": role, "count": len(matches)},
                )
        canonical_paths = {
            "EDIT_PLAN": "MANIFESTS/edit-plan.json",
            "RESOLVE_ASSEMBLY_REPORT": "MANIFESTS/resolve-assembly-report.json",
            "RENDER_QA": "MANIFESTS/render-qa.json",
        }
        for role, relative_path in canonical_paths.items():
            record = next(item for item in verified if item["role"] == role)
            if record["relative_path"] != relative_path:
                raise ProductError(
                    "ERR_TASK012_NATIVE_REQUIRED_FILE_ROLE_PATH",
                    "EDITOR_WORK canonical manifest role points to a non-canonical path",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"role": role, "relative_path": record["relative_path"]},
                )

        links = self._verify_cross_manifest(root, manifest)
        roundtrip = manifest.get("cubase_roundtrip")
        if not isinstance(roundtrip, dict):
            raise ProductError(
                "ERR_TASK012_NATIVE_ROUNDTRIP_CONTRACT_INVALID",
                "EDITOR_WORK is missing its Cubase round-trip contract",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        enabled = roundtrip.get("enabled") is True
        if roundtrip.get("automatic_project_conversion_promised") is not False:
            raise ProductError(
                "ERR_TASK012_NATIVE_CUBASE_SCOPE_VIOLATION",
                "TASK-012 must not promise automatic Cubase project conversion",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        cubase = self._verify_cubase_return(root, required=self.request.require_cubase_return, enabled=enabled)

        report: dict[str, Any] = {
            "report_version": "1.0.0",
            "task_owner": "TASK-012",
            "gate": "NATIVE_EDITOR_WORK_HANDOFF",
            "status": "PASS",
            "handoff_id": root.name,
            "editor_work_root_persisted": False,
            "manifest_sha256": manifest.get("manifest_sha256"),
            "upstream_links": links,
            "verified_file_count": len(verified),
            "verified_roles": sorted(observed_roles),
            "cubase_roundtrip": cubase,
        }
        report["report_sha256"] = sha256_bytes(canonical_json_bytes(report))
        AtomicJsonWriter.write(Path(output_path), report)
        return report
