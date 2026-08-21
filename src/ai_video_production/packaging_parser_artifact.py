"""Pure verifier for the exact TASK-014 ``packaging`` parser wheel.

The module accepts immutable bytes only.  It performs no filesystem, network,
import, install, subprocess, model, or audio operation.  A serialized result is
diagnostic evidence; it is not a parser capability or resolver authority.
"""

from __future__ import annotations

import base64
import binascii
import csv
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
import io
import re
from pathlib import PurePosixPath
import stat
from types import MappingProxyType
from typing import Mapping
import zipfile

from .serialization import canonical_json_bytes, sha256_bytes


SCHEMA_VERSION = "bai.task014.packaging-parser-artifact-verification.v1"
VERIFIER_ID = "bai.task014.packaging-parser-artifact-verifier"
VERIFIER_REVISION = 1
PACKAGING_NAME = "packaging"
PACKAGING_VERSION = "25.0"
WHEEL_FILENAME = "packaging-25.0-py3-none-any.whl"
WHEEL_BYTES = 66_469
WHEEL_SHA256 = "sha256:29572ef2b1f17581046b3a2227d5c611fb25ec70ca1ba8554b24b0e69331a484"
METADATA_SHA256 = "sha256:5b611a609c38fefc3d616bf45d20aec98fb7d53f245daca9e2c30fc85c7ac282"
SOURCE_URL = (
    "https://files.pythonhosted.org/packages/20/12/38679034af332785aac8774540895e234f4d07f7545804097de4b666afd8/"
    "packaging-25.0-py3-none-any.whl"
)
DIST_INFO = "packaging-25.0.dist-info"

_MAX_MEMBERS = 256
_MAX_EXPANDED_BYTES = 4 * 1024 * 1024
_MAX_MEMBER_BYTES = 1024 * 1024
_MAX_RECORD_BYTES = 256 * 1024
_MAX_RECORD_FIELD_BYTES = 4096
_SHA_B64_PREFIX = "sha256="
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RECEIPT_KEYS = {
    "schema_version", "verifier_id", "verifier_revision", "decision", "reason_codes",
    "distribution_name", "distribution_version", "wheel_filename", "wheel_bytes", "wheel_sha256",
    "metadata_sha256", "source_url", "archive_members", "record_rows", "payload_files",
    "expanded_bytes", "payload_inventory_sha256", "diagnostic_only",
    "official_metadata_observation_accepted", "pin_acceptance_authorized",
    "persistent_receipt_is_capability", "parser_import_authorized", "resolver_use_authorized",
    "install_authorized", "post_return_state_guaranteed", "consumer_revalidation_required",
    "verifier_network_accessed", "verifier_artifact_downloaded", "verifier_package_installed",
    "verifier_parser_imported", "verifier_target_runtime_executed", "verifier_model_loaded",
    "verifier_audio_read", "receipt_sha256",
}
_CONSTRUCTION_TOKEN = object()


class PackagingArtifactError(ValueError):
    """Closed, body-free verifier failure."""


def _fail(reason: str) -> None:
    raise PackagingArtifactError(reason)


def _safe_member(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "//" in name:
        _fail("UNSAFE_ARCHIVE_PATH")
    try:
        name.encode("ascii")
    except UnicodeEncodeError:
        _fail("UNSAFE_ARCHIVE_PATH")
    if any(ord(char) < 33 or ord(char) > 126 for char in name):
        _fail("UNSAFE_ARCHIVE_PATH")
    raw_parts = name.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        _fail("UNSAFE_ARCHIVE_PATH")
    path = PurePosixPath(name)
    if path.is_absolute() or tuple(raw_parts) != path.parts:
        _fail("UNSAFE_ARCHIVE_PATH")
    reserved = {
        "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", "CLOCK$",
        *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10)),
    }
    for part in path.parts:
        stem = part.split(".", 1)[0].upper()
        if stem in reserved or part.endswith((".", " ")) or any(char in '<>"|?*' for char in part):
            _fail("UNSAFE_ARCHIVE_PATH")
    return name


def _parse_record(raw: bytes) -> dict[str, tuple[str | None, int | None]]:
    if len(raw) > _MAX_RECORD_BYTES:
        _fail("RECORD_BOUNDS_EXCEEDED")
    result: dict[str, tuple[str | None, int | None]] = {}
    casefolded: set[str] = set()
    try:
        rows = csv.reader(io.StringIO(raw.decode("utf-8", "strict"), newline=""), strict=True)
        for row_number, row in enumerate(rows, start=1):
            if row_number > _MAX_MEMBERS or len(row) != 3:
                _fail("MALFORMED_RECORD")
            if any(len(field.encode("utf-8")) > _MAX_RECORD_FIELD_BYTES for field in row):
                _fail("MALFORMED_RECORD")
            name = _safe_member(row[0])
            if name in result or name.casefold() in casefolded:
                _fail("DUPLICATE_RECORD_PATH")
            casefolded.add(name.casefold())
            encoded_hash, raw_size = row[1], row[2]
            if not encoded_hash and not raw_size:
                result[name] = (None, None)
                continue
            if not encoded_hash.startswith(_SHA_B64_PREFIX) or not raw_size.isascii() or not raw_size.isdecimal():
                _fail("MALFORMED_RECORD")
            if len(raw_size) > 7 or (len(raw_size) > 1 and raw_size.startswith("0")):
                _fail("MALFORMED_RECORD")
            size = int(raw_size)
            if size > _MAX_MEMBER_BYTES:
                _fail("RECORD_BOUNDS_EXCEEDED")
            encoded = encoded_hash.removeprefix(_SHA_B64_PREFIX)
            try:
                decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            except (ValueError, binascii.Error):
                _fail("MALFORMED_RECORD")
            if len(decoded) != 32 or base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != encoded:
                _fail("MALFORMED_RECORD")
            result[name] = ("sha256:" + decoded.hex(), size)
    except (UnicodeDecodeError, csv.Error, OverflowError) as exc:
        raise PackagingArtifactError("MALFORMED_RECORD") from exc
    if not result:
        _fail("MALFORMED_RECORD")
    return result


def _single_header(message: object, name: str, expected: str) -> None:
    values = message.get_all(name, [])  # type: ignore[attr-defined]
    if values != [expected]:
        _fail("METADATA_IDENTITY_MISMATCH")


def _validate_metadata(raw: bytes) -> None:
    if sha256_bytes(raw) != METADATA_SHA256:
        _fail("METADATA_DIGEST_MISMATCH")
    try:
        message = BytesParser(policy=policy.compat32).parsebytes(raw, headersonly=True)
    except (TypeError, ValueError) as exc:
        raise PackagingArtifactError("MALFORMED_METADATA") from exc
    if message.defects:
        _fail("MALFORMED_METADATA")
    _single_header(message, "Name", PACKAGING_NAME)
    _single_header(message, "Version", PACKAGING_VERSION)
    _single_header(message, "Requires-Python", ">=3.8")
    if message.get_all("Requires-Dist", []):
        _fail("UNEXPECTED_RUNTIME_DEPENDENCY")


def _validate_wheel(raw: bytes) -> None:
    try:
        message = BytesParser(policy=policy.compat32).parsebytes(raw, headersonly=True)
    except (TypeError, ValueError) as exc:
        raise PackagingArtifactError("MALFORMED_WHEEL_METADATA") from exc
    if message.defects:
        _fail("MALFORMED_WHEEL_METADATA")
    if message.get_all("Wheel-Version", []) != ["1.0"]:
        _fail("WHEEL_METADATA_MISMATCH")
    if [value.lower() for value in message.get_all("Root-Is-Purelib", [])] != ["true"]:
        _fail("WHEEL_METADATA_MISMATCH")
    if message.get_all("Tag", []) != ["py3-none-any"]:
        _fail("WHEEL_TAG_MISMATCH")


@dataclass(frozen=True, slots=True, init=False)
class _VerifiedPackagingArtifact:
    """Immutable verified payload and strict diagnostic receipt."""

    payload: Mapping[str, bytes]
    record: Mapping[str, tuple[str | None, int | None]]
    receipt: Mapping[str, object]
    _seal: object

    def __init__(
        self,
        *,
        payload: Mapping[str, bytes],
        record: Mapping[str, tuple[str | None, int | None]],
        receipt: Mapping[str, object],
        _token: object,
    ) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("private verifier construction token required")
        frozen_receipt = {key: tuple(value) if isinstance(value, list) else value for key, value in receipt.items()}
        object.__setattr__(self, "payload", MappingProxyType(dict(payload)))
        object.__setattr__(self, "record", MappingProxyType(dict(record)))
        object.__setattr__(self, "receipt", MappingProxyType(frozen_receipt))
        object.__setattr__(self, "_seal", _CONSTRUCTION_TOKEN)

    def to_private_dict(self) -> dict[str, object]:
        if self._seal is not _CONSTRUCTION_TOKEN:
            raise RuntimeError("unsealed packaging artifact")
        return {key: list(value) if isinstance(value, tuple) else value for key, value in self.receipt.items()}

    def __reduce__(self) -> object:
        raise TypeError("verified packaging artifacts are not serializable capabilities")


def _receipt(*, members: int, record_rows: int, payload_files: int, expanded_bytes: int, inventory: str) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "verifier_id": VERIFIER_ID,
        "verifier_revision": VERIFIER_REVISION,
        "decision": "PROPOSED_PACKAGING_ARTIFACT_BYTES_VERIFIED_DIAGNOSTIC",
        "reason_codes": (),
        "distribution_name": PACKAGING_NAME,
        "distribution_version": PACKAGING_VERSION,
        "wheel_filename": WHEEL_FILENAME,
        "wheel_bytes": WHEEL_BYTES,
        "wheel_sha256": WHEEL_SHA256,
        "metadata_sha256": METADATA_SHA256,
        "source_url": SOURCE_URL,
        "archive_members": members,
        "record_rows": record_rows,
        "payload_files": payload_files,
        "expanded_bytes": expanded_bytes,
        "payload_inventory_sha256": inventory,
        "diagnostic_only": True,
        "official_metadata_observation_accepted": False,
        "pin_acceptance_authorized": False,
        "persistent_receipt_is_capability": False,
        "parser_import_authorized": False,
        "resolver_use_authorized": False,
        "install_authorized": False,
        "post_return_state_guaranteed": False,
        "consumer_revalidation_required": True,
        "verifier_network_accessed": False,
        "verifier_artifact_downloaded": False,
        "verifier_package_installed": False,
        "verifier_parser_imported": False,
        "verifier_target_runtime_executed": False,
        "verifier_model_loaded": False,
        "verifier_audio_read": False,
    }
    body["receipt_sha256"] = sha256_bytes(b"TASK014_PACKAGING_ARTIFACT_RECEIPT_V1\0" + canonical_json_bytes(body))
    return body


def parse_pinned_packaging_250_wheel(raw: bytes) -> _VerifiedPackagingArtifact:
    """Verify the official pinned wheel from one immutable byte sequence."""
    if type(raw) is not bytes or len(raw) != WHEEL_BYTES or sha256_bytes(raw) != WHEEL_SHA256:
        _fail("WHEEL_PIN_MISMATCH")
    bodies: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            infos = archive.infolist()
            if not 1 <= len(infos) <= _MAX_MEMBERS or sum(info.file_size for info in infos) > _MAX_EXPANDED_BYTES:
                _fail("ARCHIVE_BOUNDS_EXCEEDED")
            casefolded: set[str] = set()
            for info in infos:
                name = _safe_member(info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if (
                    name.casefold() in casefolded or info.file_size < 0 or info.file_size > _MAX_MEMBER_BYTES
                    or info.compress_size < 0 or info.flag_bits & 0x1
                    or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                    or info.is_dir() or mode not in {0, stat.S_IFREG}
                ):
                    _fail("UNSAFE_ARCHIVE_MEMBER")
                casefolded.add(name.casefold())
                with archive.open(info, "r") as member:
                    body = member.read(_MAX_MEMBER_BYTES + 1)
                if len(body) != info.file_size or len(body) > _MAX_MEMBER_BYTES:
                    _fail("ARCHIVE_MEMBER_SIZE_MISMATCH")
                bodies[name] = body
    except PackagingArtifactError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise PackagingArtifactError("INVALID_WHEEL_ARCHIVE") from exc

    record_name = f"{DIST_INFO}/RECORD"
    metadata_name = f"{DIST_INFO}/METADATA"
    wheel_name = f"{DIST_INFO}/WHEEL"
    if not {record_name, metadata_name, wheel_name}.issubset(bodies):
        _fail("REQUIRED_WHEEL_MEMBER_MISSING")
    if any(name.casefold().endswith((".pth", ".pyd", ".dll", ".exe")) for name in bodies):
        _fail("UNSAFE_EXECUTABLE_MEMBER")
    if any(not (name.startswith("packaging/") or name.startswith(f"{DIST_INFO}/")) for name in bodies):
        _fail("UNEXPECTED_TOP_LEVEL_MEMBER")
    if not any(name.startswith("packaging/") and name.endswith(".py") for name in bodies):
        _fail("PACKAGING_PAYLOAD_MISSING")

    record = _parse_record(bodies[record_name])
    if set(record) != set(bodies) or record.get(record_name) != (None, None):
        _fail("RECORD_MEMBER_SET_MISMATCH")
    for name, expected in record.items():
        if name != record_name and expected != (sha256_bytes(bodies[name]), len(bodies[name])):
            _fail("RECORD_HASH_MISMATCH")
    _validate_metadata(bodies[metadata_name])
    _validate_wheel(bodies[wheel_name])

    payload = {name: body for name, body in bodies.items() if name != record_name}
    inventory = {name: [sha256_bytes(body), len(body)] for name, body in sorted(payload.items())}
    inventory_sha = sha256_bytes(b"TASK014_PACKAGING_PAYLOAD_INVENTORY_V1\0" + canonical_json_bytes(inventory))
    receipt = _receipt(
        members=len(bodies), record_rows=len(record), payload_files=len(payload),
        expanded_bytes=sum(len(body) for body in bodies.values()), inventory=inventory_sha,
    )
    return _VerifiedPackagingArtifact(payload=payload, record=record, receipt=receipt, _token=_CONSTRUCTION_TOKEN)


def parse_packaging_artifact_receipt(value: Mapping[str, object]) -> dict[str, object]:
    """Strictly parse the non-authoritative persisted receipt."""
    if not isinstance(value, Mapping) or set(value) != _RECEIPT_KEYS:
        raise ValueError("invalid packaging artifact receipt")
    body = dict(value)
    digest = body.pop("receipt_sha256", None)
    expected = sha256_bytes(b"TASK014_PACKAGING_ARTIFACT_RECEIPT_V1\0" + canonical_json_bytes(body))
    if digest != expected or not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ValueError("invalid packaging artifact receipt")
    consts = {
        "schema_version": SCHEMA_VERSION, "verifier_id": VERIFIER_ID, "verifier_revision": VERIFIER_REVISION,
        "decision": "PROPOSED_PACKAGING_ARTIFACT_BYTES_VERIFIED_DIAGNOSTIC", "reason_codes": [],
        "distribution_name": PACKAGING_NAME, "distribution_version": PACKAGING_VERSION,
        "wheel_filename": WHEEL_FILENAME, "wheel_bytes": WHEEL_BYTES, "wheel_sha256": WHEEL_SHA256,
        "metadata_sha256": METADATA_SHA256, "source_url": SOURCE_URL, "diagnostic_only": True,
        "official_metadata_observation_accepted": False, "pin_acceptance_authorized": False,
        "persistent_receipt_is_capability": False, "parser_import_authorized": False,
        "resolver_use_authorized": False, "install_authorized": False,
        "post_return_state_guaranteed": False, "consumer_revalidation_required": True,
        "verifier_network_accessed": False, "verifier_artifact_downloaded": False,
        "verifier_package_installed": False, "verifier_parser_imported": False,
        "verifier_target_runtime_executed": False, "verifier_model_loaded": False,
        "verifier_audio_read": False,
    }
    if any(body.get(key) != expected_value for key, expected_value in consts.items()):
        raise ValueError("invalid packaging artifact receipt")
    bounds = {
        "archive_members": (4, _MAX_MEMBERS),
        "record_rows": (4, _MAX_MEMBERS),
        "payload_files": (3, _MAX_MEMBERS - 1),
        "expanded_bytes": (1, _MAX_EXPANDED_BYTES),
    }
    for key, (minimum, maximum) in bounds.items():
        if type(body.get(key)) is not int or not minimum <= body[key] <= maximum:  # type: ignore[operator]
            raise ValueError("invalid packaging artifact receipt")
    if body["archive_members"] != body["record_rows"] or body["payload_files"] + 1 != body["archive_members"]:  # type: ignore[operator]
        raise ValueError("invalid packaging artifact receipt")
    if not isinstance(body.get("payload_inventory_sha256"), str) or not _SHA256_RE.fullmatch(body["payload_inventory_sha256"]):  # type: ignore[arg-type]
        raise ValueError("invalid packaging artifact receipt")
    body["receipt_sha256"] = digest
    return body
