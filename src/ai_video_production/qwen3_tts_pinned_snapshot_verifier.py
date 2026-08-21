"""Read-only verifier for the TASK-014 Qwen3-TTS pinned model snapshot.

This module deliberately has no provider, model, package, child-process, or network
integration.  It admits a manifest as data, inspects one already-present local
directory, and produces a body-free verification receipt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat as stat_module
from typing import Any, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


MANIFEST_SCHEMA_VERSION = "1.0.0"
VERIFICATION_SCHEMA_ID = "bai.task014.qwen3-tts-pinned-snapshot-verification.v1"
ACCEPTED_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
ACCEPTED_REVISION = "5d83992436eae1d760afd27aff78a71d676296fc"
ACCEPTED_ENTRIES_SHA256 = "8c40ca449eb8fcf1bd55c4b272d40a29dd6dd91d1c419120ae24795d0c9482a3"
ACCEPTED_SEMANTIC_SHA256 = "8ee07dcddf13d95aa225df9167d4695b42e245b431686d8acb26bbd4a5e80935"
ACCEPTED_FILE_COUNT = 13
ACCEPTED_TOTAL_BYTES = 2516106051
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_FILES = 64
_CHUNK_SIZE = 1024 * 1024
_ENTRIES_ALGORITHM = (
    "TASK014_PINNED_MODEL_ENTRIES_V1: SHA-256 over UTF-8 file records sorted by ASCII bytewise ascending path; "
    "reject non-ASCII paths, duplicates and ASCII-case-fold collisions; each record is path, NUL, decimal bytes, "
    "NUL, sha256, NUL, blob_id_sha1, NUL, digest_source, NUL, lowercase load_input, LF"
)
_MANIFEST_ALGORITHM = "TASK014_PINNED_MODEL_MANIFEST_V1 defined in the companion Evidence"
_REASON_CODES = frozenset({
    "UNACCEPTED_MODEL_ID", "UNACCEPTED_REVISION", "UNACCEPTED_ENTRIES_DIGEST",
    "UNACCEPTED_SEMANTIC_DIGEST", "UNACCEPTED_FILE_COUNT", "UNACCEPTED_TOTAL_BYTES",
    "SNAPSHOT_ROOT_NOT_ADMITTED", "SNAPSHOT_ROOT_ACCESS_UNKNOWN", "SNAPSHOT_REPARSE_POINT",
    "SNAPSHOT_EXTRA_DIRECTORY", "SNAPSHOT_EXTRA_ENTRY", "SNAPSHOT_FILE_MISSING",
    "SNAPSHOT_PATH_CASE_MISMATCH", "SNAPSHOT_FILE_SIZE_MISMATCH",
    "SNAPSHOT_FILE_DIGEST_MISMATCH", "SNAPSHOT_FILE_ACCESS_UNKNOWN",
    "SNAPSHOT_MODIFIED_DURING_VERIFICATION",
})
_BLOCKER_CODES = frozenset({
    "UNACCEPTED_MODEL_ID", "UNACCEPTED_REVISION", "UNACCEPTED_ENTRIES_DIGEST",
    "UNACCEPTED_SEMANTIC_DIGEST", "UNACCEPTED_FILE_COUNT", "UNACCEPTED_TOTAL_BYTES",
    "SNAPSHOT_ROOT_NOT_ADMITTED", "SNAPSHOT_REPARSE_POINT", "SNAPSHOT_EXTRA_DIRECTORY",
    "SNAPSHOT_EXTRA_ENTRY", "SNAPSHOT_FILE_MISSING", "SNAPSHOT_PATH_CASE_MISMATCH",
    "SNAPSHOT_FILE_SIZE_MISMATCH", "SNAPSHOT_FILE_DIGEST_MISMATCH",
})
_UNKNOWN_CODES = _REASON_CODES - _BLOCKER_CODES


class VerificationDecision(str, Enum):
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


def _strict_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value):
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp") from exc
    return value


def _plain_sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 digest")
    return validate_sha256(value, field_name=name)


def _path(value: Any) -> str:
    if not isinstance(value, str) or not value or any(ord(char) < 32 or ord(char) > 126 for char in value):
        raise ValueError("manifest path must be printable ASCII")
    if "\\" in value or ":" in value or value.startswith("/") or value.endswith("/"):
        raise ValueError("manifest path is not a relative POSIX file path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("manifest path traversal is not allowed")
    return value


def _entry_record(entry: Mapping[str, Any]) -> bytes:
    return (f"{entry['path']}\0{entry['bytes']}\0{entry['sha256']}\0{entry['blob_id_sha1']}\0"
            f"{entry['digest_source']}\0{str(entry['load_input']).lower()}\n").encode("ascii")


def _entries_digest(entries: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(b"".join(_entry_record(entry) for entry in entries)).hexdigest()


def _scalar_record(name: str, value: str | int | bool) -> bytes:
    rendered = str(value).lower() if isinstance(value, bool) else str(value)
    return f"{name}\0{rendered}\n".encode("utf-8")


def _canonical_manifest_digest(value: Mapping[str, Any], entries: Sequence[Mapping[str, Any]]) -> str:
    source = value["source"]
    stream = bytearray(b"TASK014_PINNED_MODEL_MANIFEST_V1\n")
    for name, scalar in (
        ("schema_version", value["schema_version"]), ("manifest_id", value["manifest_id"]),
        ("model_id", value["model_id"]), ("revision", value["revision"]),
        ("retrieved_at", value["retrieved_at"]), ("source.provider", source["provider"]),
        ("source.api", source["api"]), ("source.resolve_prefix", source["resolve_prefix"]),
        ("entries_sha256", value["entries_sha256"]),
    ):
        stream.extend(_scalar_record(name, scalar))
    for entry in entries:
        stream.extend(_entry_record(entry))
    for name in sorted(value["no_effect_flags"]):
        stream.extend(_scalar_record(f"no_effect_flags.{name}", value["no_effect_flags"][name]))
    return hashlib.sha256(stream).hexdigest()


@dataclass(frozen=True, slots=True)
class Qwen3TtsPinnedSnapshotManifest:
    manifest_id: str
    model_id: str
    revision: str
    retrieved_at: str
    source: Mapping[str, str]
    files: tuple[Mapping[str, Any], ...]
    total_bytes: int
    entries_sha256: str
    semantic_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": MANIFEST_SCHEMA_VERSION, "manifest_id": self.manifest_id,
            "model_id": self.model_id, "revision": self.revision, "retrieved_at": self.retrieved_at,
            "source": dict(self.source), "entries_sha256": self.entries_sha256,
            "entries_digest_algorithm": _ENTRIES_ALGORITHM,
            "canonical_manifest_sha256": self.semantic_sha256,
            "canonical_manifest_digest_algorithm": _MANIFEST_ALGORITHM,
            "files": [dict(item) for item in self.files],
            "no_effect_flags": {"model_weights_downloaded": False, "model_loaded": False,
                "package_installed": False, "owner_audio_read": False, "inference_executed": False,
                "firewall_changed": False},
        }


def parse_qwen3_tts_pinned_snapshot_manifest(value: Mapping[str, Any]) -> Qwen3TtsPinnedSnapshotManifest:
    """Parse the accepted AU2B1 artifact shape without admitting production use."""
    expected = {
        "schema_version", "manifest_id", "model_id", "revision", "retrieved_at", "source",
        "entries_sha256", "entries_digest_algorithm", "canonical_manifest_sha256",
        "canonical_manifest_digest_algorithm", "files", "no_effect_flags",
    }
    _strict_keys(value, expected, "Qwen3TtsPinnedSnapshotManifest")
    if value["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported snapshot manifest schema")
    if not isinstance(value["manifest_id"], str) or not value["manifest_id"].isascii() or not value["manifest_id"]:
        raise ValueError("manifest_id is invalid")
    if not isinstance(value["model_id"], str) or not value["model_id"]:
        raise ValueError("model_id is invalid")
    if not isinstance(value["revision"], str) or len(value["revision"]) != 40 or any(c not in "0123456789abcdef" for c in value["revision"]):
        raise ValueError("revision is invalid")
    retrieved_at = _timestamp(value["retrieved_at"], "retrieved_at")
    _strict_keys(value["source"], {"provider", "api", "resolve_prefix"}, "source")
    source: dict[str, str] = {}
    for name in ("provider", "api", "resolve_prefix"):
        scalar = value["source"][name]
        if not isinstance(scalar, str) or not scalar.isascii() or not scalar:
            raise ValueError("source is invalid")
        source[name] = scalar
    if value["entries_digest_algorithm"] != _ENTRIES_ALGORITHM or value["canonical_manifest_digest_algorithm"] != _MANIFEST_ALGORITHM:
        raise ValueError("manifest algorithm description is invalid")
    raw_files = value["files"]
    if not isinstance(raw_files, list) or len(raw_files) > _MAX_FILES or len(raw_files) != ACCEPTED_FILE_COUNT:
        raise ValueError("files is invalid")
    files: list[dict[str, Any]] = []
    paths: set[str] = set()
    folded: set[str] = set()
    total = 0
    for item in raw_files:
        _strict_keys(item, {"path", "bytes", "sha256", "blob_id_sha1", "digest_source", "load_input"}, "snapshot file")
        path = _path(item["path"])
        if len(PurePosixPath(path).parts) > 1 and PurePosixPath(path).parts[:-1] != ("speech_tokenizer",):
            raise ValueError("snapshot file parent is not admitted")
        if path in paths or path.casefold() in folded:
            raise ValueError("snapshot paths must be unique including casefold")
        size = item["bytes"]
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError("snapshot file size is invalid")
        digest = _plain_sha256(item["sha256"], "snapshot file sha256")
        blob_id = item["blob_id_sha1"]
        if not isinstance(blob_id, str) or not re.fullmatch(r"[0-9a-f]{40}", blob_id):
            raise ValueError("snapshot file blob_id_sha1 is invalid")
        if item["digest_source"] not in {"resolved_bytes", "official_lfs_sha256"}:
            raise ValueError("snapshot file digest_source is invalid")
        if not isinstance(item["load_input"], bool):
            raise ValueError("snapshot file load_input is invalid")
        files.append({"path": path, "bytes": size, "sha256": digest, "blob_id_sha1": blob_id,
                      "digest_source": item["digest_source"], "load_input": item["load_input"]})
        paths.add(path)
        folded.add(path.casefold())
        total += size
    if files != sorted(files, key=lambda item: item["path"].encode("ascii")):
        raise ValueError("snapshot files must use ASCII ordinal order")
    entries_sha256 = _plain_sha256(value["entries_sha256"], "entries_sha256")
    semantic_sha256 = _plain_sha256(value["canonical_manifest_sha256"], "canonical_manifest_sha256")
    _strict_keys(value["no_effect_flags"], {"model_weights_downloaded", "model_loaded", "package_installed", "owner_audio_read", "inference_executed", "firewall_changed"}, "no_effect_flags")
    if any(value["no_effect_flags"][name] is not False for name in value["no_effect_flags"]):
        raise ValueError("manifest no_effect_flags violate the read-only boundary")
    computed_entries = _entries_digest(files)
    if entries_sha256 != computed_entries:
        raise ValueError("entries_sha256 mismatch")
    computed_semantic = _canonical_manifest_digest(value, files)
    if semantic_sha256 != computed_semantic:
        raise ValueError("semantic_sha256 mismatch")
    return Qwen3TtsPinnedSnapshotManifest(
        manifest_id=value["manifest_id"], model_id=value["model_id"], revision=value["revision"],
        retrieved_at=retrieved_at, source=source, files=tuple(files), total_bytes=total,
        entries_sha256=entries_sha256, semantic_sha256=semantic_sha256,
    )


def _is_reparse(path: Path, metadata: os.stat_result | None = None) -> bool:
    try:
        metadata = metadata if metadata is not None else path.lstat()
        if stat_module.S_ISLNK(metadata.st_mode):
            return True
        attributes = getattr(metadata, "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat_module, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _stat_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    """Stable file identity used around one opened handle.

    Windows can update/change-report creation metadata while a directory is
    enumerated even when a file body is not modified.  Device/inode/type, byte
    length, and last-write timestamp are the stable observations relevant to a
    streaming content race; ctime is intentionally not a comparison input.
    """
    return (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_size,
            metadata.st_mtime_ns)


def _root_is_safe(root: Path) -> bool:
    raw = str(root)
    if raw.startswith(("\\\\", "//", "\\\\?\\", "\\\\.\\", "\\??\\")):
        return False
    drive, tail = os.path.splitdrive(raw)
    if drive and tail in {"", "\\", "/"}:
        return False
    if not root.is_absolute() or root.parent == root:
        return False
    if os.name == "nt":
        return _windows_drive_type(root) == 3  # DRIVE_FIXED only; remote/removable are not local snapshots.
    return True


def _windows_drive_type(root: Path) -> int | None:
    """Read-only Win32 locality classification; None is fail-closed by caller."""
    try:
        import ctypes
        anchor = root.anchor
        if not anchor:
            return None
        return int(ctypes.windll.kernel32.GetDriveTypeW(anchor))
    except (AttributeError, OSError):
        return None


def _admit_root_chain(root: Path) -> tuple[bool, bool]:
    """Return (blocked_reparse_or_invalid, unknown_access) for every component."""
    if not _root_is_safe(root):
        return True, False
    anchor = Path(root.anchor)
    current = root
    while True:
        try:
            if _is_reparse(current, current.lstat()):
                return True, False
        except OSError:
            return False, True
        if current == anchor:
            return False, False
        current = current.parent


def _receipt_body(
    *, manifest: Qwen3TtsPinnedSnapshotManifest, decision: VerificationDecision,
    reasons: Sequence[str], evaluated_at: str, root_fingerprint: str | None,
    file_bodies_hashed: bool, filesystem_enumerated: bool, snapshot_modified: bool,
) -> dict[str, Any]:
    return {
        "schema": VERIFICATION_SCHEMA_ID, "task_owner": "TASK-014",
        "model_id": manifest.model_id, "revision": manifest.revision,
        "manifest_entries_sha256": manifest.entries_sha256,
        "manifest_semantic_sha256": manifest.semantic_sha256,
        "file_count": len(manifest.files), "total_bytes": manifest.total_bytes,
        "evaluated_at": evaluated_at, "decision": decision.value,
        "reason_codes": list(reasons), "snapshot_root_fingerprint": root_fingerprint,
        "filesystem_enumerated": filesystem_enumerated, "file_bodies_hashed": file_bodies_hashed,
        "snapshot_modified": snapshot_modified, "diagnostic_only": True,
        "persistent_receipt_is_capability": False, "model_reuse_authorized": False,
        "model_load_authorized": False, "post_return_state_guaranteed": False,
        "consumer_revalidation_required": True,
        "model_weights_downloaded": False, "package_installed": False,
        "package_imported": False, "model_loaded": False, "owner_audio_read": False,
        "inference_executed": False, "firewall_changed": False,
    }


@dataclass(frozen=True, slots=True)
class Qwen3TtsPinnedSnapshotVerification:
    manifest: Qwen3TtsPinnedSnapshotManifest
    evaluated_at: str
    decision: VerificationDecision
    reason_codes: tuple[str, ...]
    snapshot_root_fingerprint: str | None
    filesystem_enumerated: bool
    file_bodies_hashed: bool
    snapshot_modified: bool
    receipt_sha256: str

    def to_private_dict(self) -> dict[str, Any]:
        body = _receipt_body(manifest=self.manifest, decision=self.decision,
                             reasons=self.reason_codes, evaluated_at=self.evaluated_at,
                             root_fingerprint=self.snapshot_root_fingerprint,
                             file_bodies_hashed=self.file_bodies_hashed,
                             filesystem_enumerated=self.filesystem_enumerated,
                             snapshot_modified=self.snapshot_modified)
        body["receipt_sha256"] = self.receipt_sha256
        return body

    def to_public_dict(self) -> dict[str, Any]:
        body = {
            "task_owner": "TASK-014",
            "model_id": self.manifest.model_id, "revision": self.manifest.revision,
            "manifest_entries_sha256": self.manifest.entries_sha256,
            "manifest_semantic_sha256": self.manifest.semantic_sha256,
            "file_count": len(self.manifest.files), "total_bytes": self.manifest.total_bytes,
            "evaluated_at": self.evaluated_at, "decision": self.decision.value,
            "reason_codes": list(self.reason_codes), "filesystem_enumerated": self.filesystem_enumerated,
            "file_bodies_hashed": self.file_bodies_hashed, "snapshot_modified": self.snapshot_modified,
            "snapshot_root_fingerprint_persisted": False, "diagnostic_only": True,
            "persistent_receipt_is_capability": False, "model_reuse_authorized": False,
            "model_load_authorized": False, "post_return_state_guaranteed": False,
            "consumer_revalidation_required": True, "model_weights_downloaded": False,
            "package_installed": False, "package_imported": False, "model_loaded": False,
            "owner_audio_read": False, "inference_executed": False, "firewall_changed": False,
        }
        body["public_projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def _make_receipt(manifest: Qwen3TtsPinnedSnapshotManifest, evaluated_at: str,
                  blocked: set[str], unknown: set[str], root_fingerprint: str | None,
                  *, hashed: bool, enumerated: bool) -> Qwen3TtsPinnedSnapshotVerification:
    reasons = tuple(sorted(blocked | unknown))
    decision = VerificationDecision.BLOCKED if blocked else (
        VerificationDecision.UNKNOWN if unknown else VerificationDecision.VERIFIED)
    body = _receipt_body(manifest=manifest, decision=decision, reasons=reasons,
                         evaluated_at=evaluated_at, root_fingerprint=root_fingerprint,
                         file_bodies_hashed=hashed, filesystem_enumerated=enumerated,
                         snapshot_modified="SNAPSHOT_MODIFIED_DURING_VERIFICATION" in unknown)
    receipt = Qwen3TtsPinnedSnapshotVerification(
        manifest=manifest, evaluated_at=evaluated_at, decision=decision, reason_codes=reasons,
        snapshot_root_fingerprint=root_fingerprint, filesystem_enumerated=enumerated,
        file_bodies_hashed=hashed, snapshot_modified="SNAPSHOT_MODIFIED_DURING_VERIFICATION" in unknown,
        receipt_sha256=sha256_bytes(canonical_json_bytes(body)),
    )
    return receipt


def _production_blockers(manifest: Qwen3TtsPinnedSnapshotManifest) -> set[str]:
    blockers: set[str] = set()
    if manifest.model_id != ACCEPTED_MODEL_ID:
        blockers.add("UNACCEPTED_MODEL_ID")
    if manifest.revision != ACCEPTED_REVISION:
        blockers.add("UNACCEPTED_REVISION")
    if manifest.entries_sha256 != ACCEPTED_ENTRIES_SHA256:
        blockers.add("UNACCEPTED_ENTRIES_DIGEST")
    if manifest.semantic_sha256 != ACCEPTED_SEMANTIC_SHA256:
        blockers.add("UNACCEPTED_SEMANTIC_DIGEST")
    if len(manifest.files) != ACCEPTED_FILE_COUNT:
        blockers.add("UNACCEPTED_FILE_COUNT")
    if manifest.total_bytes != ACCEPTED_TOTAL_BYTES:
        blockers.add("UNACCEPTED_TOTAL_BYTES")
    return blockers


def _verify_files(manifest: Qwen3TtsPinnedSnapshotManifest, root: Path) -> tuple[set[str], set[str], str | None, bool, bool]:
    """Return blocker/unknown codes, a private root fingerprint, and hash status."""
    blocked: set[str] = set()
    unknown: set[str] = set()
    root_fingerprint: str | None = None
    all_hashed = False
    enumerated = False
    try:
        if not _root_is_safe(root):
            return {"SNAPSHOT_ROOT_NOT_ADMITTED"}, unknown, None, False, False
        try:
            root_stat = root.lstat()
        except FileNotFoundError:
            return {"SNAPSHOT_ROOT_NOT_ADMITTED"}, unknown, None, False, False
        root_blocked, root_unknown = _admit_root_chain(root)
        if root_blocked:
            return {"SNAPSHOT_ROOT_NOT_ADMITTED"}, unknown, None, False, False
        if root_unknown:
            return blocked, {"SNAPSHOT_ROOT_ACCESS_UNKNOWN"}, None, False, False
        if not stat_module.S_ISDIR(root_stat.st_mode):
            return {"SNAPSHOT_ROOT_NOT_ADMITTED"}, unknown, None, False, False
        root_fingerprint = sha256_bytes(canonical_json_bytes({"signature": _stat_signature(root_stat)}))
        expected = {item["path"]: item for item in manifest.files}
        tokenizer_dir = root / "speech_tokenizer"
        try:
            tokenizer_before = tokenizer_dir.lstat()
        except FileNotFoundError:
            return {"SNAPSHOT_FILE_MISSING"}, unknown, root_fingerprint, False, False
        if _is_reparse(tokenizer_dir, tokenizer_before) or not stat_module.S_ISDIR(tokenizer_before.st_mode):
            return {"SNAPSHOT_REPARSE_POINT"}, unknown, root_fingerprint, False, False
        actual: dict[str, Path] = {}
        discovered = 0
        capped = False
        complete_traversal = True
        pending = [root]
        while pending and not capped:
            current_path = pending.pop()
            try:
                with os.scandir(current_path) as iterator:
                    for entry in iterator:
                        discovered += 1
                        if discovered > _MAX_FILES:
                            blocked.add("SNAPSHOT_EXTRA_ENTRY")
                            capped = True
                            complete_traversal = False
                            break
                        child = current_path / entry.name
                        metadata = child.lstat()
                        if _is_reparse(child, metadata):
                            blocked.add("SNAPSHOT_REPARSE_POINT")
                            complete_traversal = False
                            continue
                        relative = child.relative_to(root).as_posix()
                        if stat_module.S_ISDIR(metadata.st_mode):
                            if relative != "speech_tokenizer":
                                blocked.add("SNAPSHOT_EXTRA_DIRECTORY")
                                complete_traversal = False
                            else:
                                pending.append(child)
                        elif stat_module.S_ISREG(metadata.st_mode):
                            actual[relative] = child
                        else:
                            blocked.add("SNAPSHOT_REPARSE_POINT")
                            complete_traversal = False
            except OSError:
                unknown.add("SNAPSHOT_FILE_ACCESS_UNKNOWN")
                complete_traversal = False
        actual_names = set(actual)
        if actual_names != set(expected):
            expected_folded = {name.casefold() for name in expected}
            actual_folded = {name.casefold() for name in actual}
            if expected_folded == actual_folded:
                blocked.add("SNAPSHOT_PATH_CASE_MISMATCH")
            if set(expected) - actual_names:
                blocked.add("SNAPSHOT_FILE_MISSING")
            if actual_names - set(expected):
                blocked.add("SNAPSHOT_EXTRA_ENTRY")
        hashed_paths: set[str] = set()
        for relative in sorted(set(expected) & actual_names):
            path = actual[relative]
            expected_entry = expected[relative]
            try:
                before = path.lstat()
                if _is_reparse(path, before) or not stat_module.S_ISREG(before.st_mode):
                    blocked.add("SNAPSHOT_REPARSE_POINT")
                    continue
                if before.st_size != expected_entry["bytes"]:
                    blocked.add("SNAPSHOT_FILE_SIZE_MISMATCH")
                    continue
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    opened = os.fstat(handle.fileno())
                    if _stat_signature(opened) != _stat_signature(before):
                        unknown.add("SNAPSHOT_MODIFIED_DURING_VERIFICATION")
                        continue
                    for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
                        digest.update(chunk)
                after = path.lstat()
                if _stat_signature(after) != _stat_signature(before):
                    unknown.add("SNAPSHOT_MODIFIED_DURING_VERIFICATION")
                    continue
                if digest.hexdigest() != expected_entry["sha256"]:
                    blocked.add("SNAPSHOT_FILE_DIGEST_MISMATCH")
                hashed_paths.add(relative)
            except PermissionError:
                unknown.add("SNAPSHOT_FILE_ACCESS_UNKNOWN")
            except OSError:
                unknown.add("SNAPSHOT_FILE_ACCESS_UNKNOWN")
        try:
            if _stat_signature(root.lstat()) != _stat_signature(root_stat):
                unknown.add("SNAPSHOT_MODIFIED_DURING_VERIFICATION")
            tokenizer_after = tokenizer_dir.lstat()
            if _is_reparse(tokenizer_dir, tokenizer_after):
                blocked.add("SNAPSHOT_REPARSE_POINT")
            elif _stat_signature(tokenizer_after) != _stat_signature(tokenizer_before):
                unknown.add("SNAPSHOT_MODIFIED_DURING_VERIFICATION")
        except OSError:
            unknown.add("SNAPSHOT_ROOT_ACCESS_UNKNOWN")
        post_blocked, post_unknown = _admit_root_chain(root)
        if post_blocked:
            blocked.add("SNAPSHOT_REPARSE_POINT")
        if post_unknown:
            unknown.add("SNAPSHOT_ROOT_ACCESS_UNKNOWN")
        enumerated = complete_traversal and not unknown and not capped
        all_hashed = (hashed_paths == set(expected)
                      and "SNAPSHOT_REPARSE_POINT" not in blocked
                      and "SNAPSHOT_FILE_ACCESS_UNKNOWN" not in unknown
                      and "SNAPSHOT_ROOT_ACCESS_UNKNOWN" not in unknown
                      and "SNAPSHOT_MODIFIED_DURING_VERIFICATION" not in unknown)
    except PermissionError:
        unknown.add("SNAPSHOT_ROOT_ACCESS_UNKNOWN")
    except OSError:
        unknown.add("SNAPSHOT_ROOT_ACCESS_UNKNOWN")
    return blocked, unknown, root_fingerprint, all_hashed, enumerated


def _verify_manifest(manifest: Qwen3TtsPinnedSnapshotManifest, snapshot_root: Path,
                     evaluated_at: str, *, production: bool) -> Qwen3TtsPinnedSnapshotVerification:
    _timestamp(evaluated_at, "evaluated_at")
    blocked = _production_blockers(manifest) if production else set()
    if blocked:
        return _make_receipt(manifest, evaluated_at, blocked, set(), None, hashed=False, enumerated=False)
    fs_blocked, unknown, fingerprint, hashed, enumerated = _verify_files(manifest, snapshot_root)
    return _make_receipt(manifest, evaluated_at, fs_blocked, unknown, fingerprint, hashed=hashed, enumerated=enumerated)


def verify_qwen3_tts_pinned_snapshot(
    manifest: Qwen3TtsPinnedSnapshotManifest, snapshot_root: Path, evaluated_at: str,
) -> Qwen3TtsPinnedSnapshotVerification:
    """Verify only the accepted production pin against an already-local snapshot."""
    if not isinstance(manifest, Qwen3TtsPinnedSnapshotManifest) or not isinstance(snapshot_root, Path):
        raise ValueError("manifest and snapshot_root have invalid types")
    return _verify_manifest(parse_qwen3_tts_pinned_snapshot_manifest(manifest.to_dict()), snapshot_root, evaluated_at, production=True)


def parse_qwen3_tts_pinned_snapshot_verification(value: Mapping[str, Any]) -> Qwen3TtsPinnedSnapshotVerification:
    expected = {
        "schema", "task_owner", "model_id", "revision", "manifest_entries_sha256",
        "manifest_semantic_sha256", "file_count", "total_bytes", "evaluated_at", "decision",
        "reason_codes", "snapshot_root_fingerprint", "filesystem_enumerated", "file_bodies_hashed",
        "snapshot_modified", "diagnostic_only", "persistent_receipt_is_capability",
        "model_reuse_authorized", "model_load_authorized", "post_return_state_guaranteed",
        "consumer_revalidation_required", "model_weights_downloaded", "package_installed", "package_imported",
        "model_loaded", "owner_audio_read", "inference_executed", "firewall_changed", "receipt_sha256",
    }
    _strict_keys(value, expected, "Qwen3TtsPinnedSnapshotVerification")
    if value["schema"] != VERIFICATION_SCHEMA_ID or value["task_owner"] != "TASK-014":
        raise ValueError("unsupported snapshot verification identity")
    if (value["diagnostic_only"] is not True or value["persistent_receipt_is_capability"] is not False
            or value["model_reuse_authorized"] is not False or value["model_load_authorized"] is not False
            or value["post_return_state_guaranteed"] is not False
            or value["consumer_revalidation_required"] is not True):
        raise ValueError("snapshot verification cannot grant persistent or runtime authority")
    for field in ("model_weights_downloaded", "package_installed", "package_imported",
                  "model_loaded", "owner_audio_read", "inference_executed", "firewall_changed"):
        if value[field] is not False:
            raise ValueError(f"{field} violates the read-only boundary")
    if (not isinstance(value["filesystem_enumerated"], bool) or not isinstance(value["file_bodies_hashed"], bool)
            or not isinstance(value["snapshot_modified"], bool)):
        raise ValueError("verification observation flags are invalid")
    reasons = value["reason_codes"]
    if (not isinstance(reasons, list) or any(not isinstance(item, str) or item not in _REASON_CODES for item in reasons)
            or reasons != sorted(set(reasons))):
        raise ValueError("reason_codes must be closed and sorted")
    fingerprint = value["snapshot_root_fingerprint"]
    if fingerprint is not None:
        _digest(fingerprint, "snapshot_root_fingerprint")
    if (not isinstance(value["model_id"], str) or not value["model_id"] or not isinstance(value["revision"], str)
            or not re.fullmatch(r"[0-9a-f]{40}", value["revision"])
            or not isinstance(value["file_count"], int) or isinstance(value["file_count"], bool)
            or not 1 <= value["file_count"] <= _MAX_FILES
            or not isinstance(value["total_bytes"], int) or isinstance(value["total_bytes"], bool)
            or value["total_bytes"] <= 0):
        raise ValueError("verification scalar fields are invalid")
    manifest = Qwen3TtsPinnedSnapshotManifest(
        manifest_id="receipt-only", model_id=value["model_id"], revision=value["revision"],
        retrieved_at="1970-01-01T00:00:00Z", source={}, files=tuple({} for _ in range(value["file_count"])),
        total_bytes=value["total_bytes"], entries_sha256=_plain_sha256(value["manifest_entries_sha256"], "manifest_entries_sha256"),
        semantic_sha256=_plain_sha256(value["manifest_semantic_sha256"], "manifest_semantic_sha256"),
    )
    _timestamp(value["evaluated_at"], "evaluated_at")
    decision = VerificationDecision(value["decision"])
    reason_set = set(reasons)
    if decision is VerificationDecision.VERIFIED:
        if (reasons or value["model_id"] != ACCEPTED_MODEL_ID or value["revision"] != ACCEPTED_REVISION
                or manifest.entries_sha256 != ACCEPTED_ENTRIES_SHA256 or manifest.semantic_sha256 != ACCEPTED_SEMANTIC_SHA256
                or value["file_count"] != ACCEPTED_FILE_COUNT or value["total_bytes"] != ACCEPTED_TOTAL_BYTES
                or fingerprint is None or value["filesystem_enumerated"] is not True or value["file_bodies_hashed"] is not True
                or value["snapshot_modified"] is not False):
            raise ValueError("VERIFIED receipt violates accepted pin invariants")
    elif decision is VerificationDecision.BLOCKED:
        if not reason_set & _BLOCKER_CODES:
            raise ValueError("BLOCKED receipt requires a blocker reason")
    elif not reason_set or not reason_set <= _UNKNOWN_CODES:
        raise ValueError("UNKNOWN receipt requires only unknown reasons")
    if reason_set & _UNKNOWN_CODES and (value["filesystem_enumerated"] or value["file_bodies_hashed"]):
        raise ValueError("unknown observations cannot claim complete enumeration or body hashing")
    early_blockers = {
        "UNACCEPTED_MODEL_ID", "UNACCEPTED_REVISION", "UNACCEPTED_ENTRIES_DIGEST",
        "UNACCEPTED_SEMANTIC_DIGEST", "UNACCEPTED_FILE_COUNT", "UNACCEPTED_TOTAL_BYTES",
        "SNAPSHOT_ROOT_NOT_ADMITTED",
    }
    if reason_set & early_blockers and (fingerprint is not None
            or value["filesystem_enumerated"] or value["file_bodies_hashed"]):
        raise ValueError("pre-observation blockers cannot claim filesystem observations")
    if value["snapshot_modified"] is not ("SNAPSHOT_MODIFIED_DURING_VERIFICATION" in reason_set):
        raise ValueError("snapshot_modified does not match reason_codes")
    body = _receipt_body(manifest=manifest, decision=decision, reasons=reasons,
                         evaluated_at=value["evaluated_at"], root_fingerprint=fingerprint,
                         file_bodies_hashed=value["file_bodies_hashed"],
                         filesystem_enumerated=value["filesystem_enumerated"],
                         snapshot_modified=value["snapshot_modified"])
    if sha256_bytes(canonical_json_bytes(body)) != _digest(value["receipt_sha256"], "receipt_sha256"):
        raise ValueError("receipt_sha256 mismatch")
    return Qwen3TtsPinnedSnapshotVerification(
        manifest=manifest, evaluated_at=value["evaluated_at"], decision=decision,
        reason_codes=tuple(reasons), snapshot_root_fingerprint=fingerprint,
        filesystem_enumerated=value["filesystem_enumerated"], file_bodies_hashed=value["file_bodies_hashed"],
        snapshot_modified=value["snapshot_modified"],
        receipt_sha256=value["receipt_sha256"],
    )


__all__ = [
    "ACCEPTED_ENTRIES_SHA256", "ACCEPTED_FILE_COUNT", "ACCEPTED_MODEL_ID", "ACCEPTED_REVISION",
    "ACCEPTED_SEMANTIC_SHA256", "ACCEPTED_TOTAL_BYTES", "MANIFEST_SCHEMA_VERSION", "VERIFICATION_SCHEMA_ID",
    "Qwen3TtsPinnedSnapshotManifest", "Qwen3TtsPinnedSnapshotVerification", "VerificationDecision",
    "parse_qwen3_tts_pinned_snapshot_manifest", "parse_qwen3_tts_pinned_snapshot_verification",
    "verify_qwen3_tts_pinned_snapshot",
]
