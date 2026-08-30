"""TASK-059 body-free PuTTY PPK v3 import preflight.

This module inspects only encrypted-container metadata and public coordinates.
It accepts no passphrase, performs no private-key decryption, and creates no
custody, signing, filesystem, subprocess, or external effect.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
RECORD_KIND = "OWNER_SIGNING_KEY_PPK_IMPORT_PREFLIGHT"
PREFLIGHT_STATE = "READY_FOR_PASSPHRASE_MAC_GATE_NO_CUSTODY_IMPORT"
MAX_PPK_BYTES = 64 * 1024
MAX_PUBLIC_KEY_FILE_BYTES = 16 * 1024
MAX_LINE_BYTES = 4096
MAX_PRIVATE_CIPHERTEXT_BYTES = 16 * 1024
MIN_ARGON2_MEMORY_KIB = 8192
MAX_ARGON2_MEMORY_KIB = 262_144
MIN_ARGON2_PASSES = 3
MAX_ARGON2_PASSES = 128
MAX_ARGON2_PARALLELISM = 16
_FINGERPRINT = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
_HEX = re.compile(r"^[0-9a-f]+$")
_PRIVATE_MAC = re.compile(r"^[0-9a-f]{64}$")


def _positive(
    value: object, *, field_name: str, minimum: int = 1, maximum: int
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value > maximum
    ):
        raise ValueError(f"{field_name} is outside the supported ceiling")
    if value < minimum:
        raise ValueError(f"{field_name} is below the supported security floor")
    return value


def _ascii_lines(value: bytes, *, field_name: str, maximum: int) -> list[str]:
    if not isinstance(value, bytes) or not value or len(value) > maximum:
        raise ValueError(f"{field_name} size is invalid")
    if b"\x00" in value:
        raise ValueError(f"{field_name} contains NUL")
    try:
        text = value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{field_name} must be ASCII") from exc
    lines = text.splitlines()
    if not lines or any(not line or len(line.encode("ascii")) > MAX_LINE_BYTES for line in lines):
        raise ValueError(f"{field_name} lines are invalid")
    return lines


def _header(line: str, name: str) -> str:
    prefix = f"{name}: "
    if not line.startswith(prefix):
        raise ValueError(f"expected {name} header")
    value = line[len(prefix) :]
    if not value:
        raise ValueError(f"{name} header is empty")
    return value


def _decimal(
    value: str,
    *,
    field_name: str,
    minimum: int = 1,
    maximum: int,
) -> int:
    if not value.isascii() or not value.isdecimal() or value.startswith("0"):
        raise ValueError(f"{field_name} must be canonical positive decimal")
    return _positive(
        int(value),
        field_name=field_name,
        minimum=minimum,
        maximum=maximum,
    )


def _decode_b64_lines(lines: list[str], *, field_name: str, maximum: int) -> bytes:
    if not lines or any(not re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", line) for line in lines):
        raise ValueError(f"{field_name} base64 lines are invalid")
    try:
        decoded = base64.b64decode("".join(lines), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{field_name} base64 is invalid") from exc
    if not decoded or len(decoded) > maximum:
        raise ValueError(f"{field_name} decoded size is invalid")
    return decoded


def _read_ssh_string(blob: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 4 > len(blob):
        raise ValueError("SSH public blob is truncated")
    size = int.from_bytes(blob[offset : offset + 4], "big")
    offset += 4
    if size < 1 or offset + size > len(blob):
        raise ValueError("SSH public blob string is invalid")
    return blob[offset : offset + size], offset + size


def _ed25519_public_from_blob(blob: bytes) -> bytes:
    algorithm, offset = _read_ssh_string(blob, 0)
    public_key, offset = _read_ssh_string(blob, offset)
    if algorithm != b"ssh-ed25519" or len(public_key) != 32 or offset != len(blob):
        raise ValueError("SSH public blob must contain one exact Ed25519 key")
    return public_key


def _openssh_fingerprint(public_blob: bytes) -> str:
    digest = hashlib.sha256(public_blob).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def _parse_rfc4716_public(value: bytes) -> bytes:
    lines = _ascii_lines(
        value, field_name="RFC4716 public key", maximum=MAX_PUBLIC_KEY_FILE_BYTES
    )
    if lines[0] != "---- BEGIN SSH2 PUBLIC KEY ----" or lines[-1] != "---- END SSH2 PUBLIC KEY ----":
        raise ValueError("RFC4716 public key boundary is invalid")
    body = lines[1:-1]
    while body and (body[0].startswith("Comment: ") or body[0].startswith("Subject: ")):
        body.pop(0)
    if any(":" in line for line in body):
        raise ValueError("RFC4716 public key contains unsupported headers")
    blob = _decode_b64_lines(
        body, field_name="RFC4716 public key", maximum=MAX_PUBLIC_KEY_FILE_BYTES
    )
    _ed25519_public_from_blob(blob)
    return blob


@dataclass(frozen=True, slots=True)
class PpkImportPreflight:
    observed_at_epoch_ms: int
    ppk_file_sha256: str
    public_key_file_sha256: str
    ppk_public_blob_sha256: str
    private_ciphertext_sha256: str
    signer_key_id_sha256: str
    openssh_sha256_fingerprint: str
    argon2_memory_kib: int
    argon2_passes: int
    argon2_parallelism: int
    ppk_format_version: int = 3
    algorithm: str = "ssh-ed25519"
    encryption: str = "aes256-cbc"
    key_derivation: str = "Argon2id"
    public_coordinates_match: bool = True
    expected_fingerprint_match: bool = True
    passphrase_received: bool = False
    private_mac_verified: bool = False
    private_key_decrypted: bool = False
    custody_import_authorized: bool = False
    custody_import_started: bool = False
    signing_authorized: bool = False
    external_effect_authorized: bool = False
    state: str = PREFLIGHT_STATE

    def __post_init__(self) -> None:
        _positive(
            self.observed_at_epoch_ms,
            field_name="observed_at_epoch_ms",
            maximum=9_999_999_999_999,
        )
        for name in (
            "ppk_file_sha256",
            "public_key_file_sha256",
            "ppk_public_blob_sha256",
            "private_ciphertext_sha256",
            "signer_key_id_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        if not isinstance(self.openssh_sha256_fingerprint, str) or not _FINGERPRINT.fullmatch(
            self.openssh_sha256_fingerprint
        ):
            raise ValueError("openssh_sha256_fingerprint is invalid")
        _positive(
            self.argon2_memory_kib,
            field_name="argon2_memory_kib",
            minimum=MIN_ARGON2_MEMORY_KIB,
            maximum=MAX_ARGON2_MEMORY_KIB,
        )
        _positive(
            self.argon2_passes,
            field_name="argon2_passes",
            minimum=MIN_ARGON2_PASSES,
            maximum=MAX_ARGON2_PASSES,
        )
        _positive(
            self.argon2_parallelism,
            field_name="argon2_parallelism",
            maximum=MAX_ARGON2_PARALLELISM,
        )
        if (
            self.ppk_format_version != 3
            or self.algorithm != "ssh-ed25519"
            or self.encryption != "aes256-cbc"
            or self.key_derivation != "Argon2id"
            or self.public_coordinates_match is not True
            or self.expected_fingerprint_match is not True
            or self.passphrase_received is not False
            or self.private_mac_verified is not False
            or self.private_key_decrypted is not False
            or self.custody_import_authorized is not False
            or self.custody_import_started is not False
            or self.signing_authorized is not False
            or self.external_effect_authorized is not False
            or self.state != PREFLIGHT_STATE
        ):
            raise ValueError("PPK preflight cannot grant or claim secret-bearing effects")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": RECORD_KIND,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "preflight_sha256": sha256_bytes(canonical_json_bytes(body))}


def inspect_ppk_import_preflight(
    ppk_document: bytes,
    rfc4716_public_key: bytes,
    *,
    expected_openssh_sha256_fingerprint: str,
    observed_at_epoch_ms: int,
) -> PpkImportPreflight:
    if not isinstance(expected_openssh_sha256_fingerprint, str) or not _FINGERPRINT.fullmatch(
        expected_openssh_sha256_fingerprint
    ):
        raise ValueError("expected OpenSSH SHA-256 fingerprint is invalid")
    _positive(
        observed_at_epoch_ms,
        field_name="observed_at_epoch_ms",
        maximum=9_999_999_999_999,
    )
    lines = _ascii_lines(ppk_document, field_name="PPK document", maximum=MAX_PPK_BYTES)
    if len(lines) < 13:
        raise ValueError("PPK document is truncated")
    index = 0

    algorithm = _header(lines[index], "PuTTY-User-Key-File-3")
    index += 1
    if algorithm != "ssh-ed25519":
        raise ValueError("PPK algorithm must be ssh-ed25519")
    encryption = _header(lines[index], "Encryption")
    index += 1
    if encryption != "aes256-cbc":
        raise ValueError("PPK must use aes256-cbc encryption")
    _header(lines[index], "Comment")
    index += 1
    public_line_count = _decimal(
        _header(lines[index], "Public-Lines"), field_name="Public-Lines", maximum=64
    )
    index += 1
    public_end = index + public_line_count
    if public_end > len(lines):
        raise ValueError("PPK public block is truncated")
    ppk_public_blob = _decode_b64_lines(
        lines[index:public_end], field_name="PPK public block", maximum=MAX_PUBLIC_KEY_FILE_BYTES
    )
    index = public_end

    key_derivation = _header(lines[index], "Key-Derivation")
    index += 1
    if key_derivation != "Argon2id":
        raise ValueError("PPK must use Argon2id key derivation")
    argon2_memory = _decimal(
        _header(lines[index], "Argon2-Memory"),
        field_name="Argon2-Memory",
        minimum=MIN_ARGON2_MEMORY_KIB,
        maximum=MAX_ARGON2_MEMORY_KIB,
    )
    index += 1
    argon2_passes = _decimal(
        _header(lines[index], "Argon2-Passes"),
        field_name="Argon2-Passes",
        minimum=MIN_ARGON2_PASSES,
        maximum=MAX_ARGON2_PASSES,
    )
    index += 1
    argon2_parallelism = _decimal(
        _header(lines[index], "Argon2-Parallelism"),
        field_name="Argon2-Parallelism",
        maximum=MAX_ARGON2_PARALLELISM,
    )
    index += 1
    salt = _header(lines[index], "Argon2-Salt")
    index += 1
    if not _HEX.fullmatch(salt) or len(salt) % 2 or not 16 <= len(bytes.fromhex(salt)) <= 64:
        raise ValueError("Argon2-Salt is invalid")

    private_line_count = _decimal(
        _header(lines[index], "Private-Lines"), field_name="Private-Lines", maximum=256
    )
    index += 1
    private_end = index + private_line_count
    if private_end + 1 != len(lines):
        raise ValueError("PPK private block or trailing fields are invalid")
    private_ciphertext = _decode_b64_lines(
        lines[index:private_end],
        field_name="PPK private ciphertext",
        maximum=MAX_PRIVATE_CIPHERTEXT_BYTES,
    )
    if len(private_ciphertext) % 16:
        raise ValueError("PPK private ciphertext is not AES block aligned")
    private_mac = _header(lines[private_end], "Private-MAC")
    if not _PRIVATE_MAC.fullmatch(private_mac):
        raise ValueError("PPK Private-MAC is invalid")

    raw_public = _ed25519_public_from_blob(ppk_public_blob)
    external_public_blob = _parse_rfc4716_public(rfc4716_public_key)
    if external_public_blob != ppk_public_blob:
        raise ValueError("PPK and RFC4716 public keys do not match")
    fingerprint = _openssh_fingerprint(ppk_public_blob)
    if fingerprint != expected_openssh_sha256_fingerprint:
        raise ValueError("PPK public key does not match the expected Owner fingerprint")

    return PpkImportPreflight(
        observed_at_epoch_ms=observed_at_epoch_ms,
        ppk_file_sha256=sha256_bytes(ppk_document),
        public_key_file_sha256=sha256_bytes(rfc4716_public_key),
        ppk_public_blob_sha256=sha256_bytes(ppk_public_blob),
        private_ciphertext_sha256=sha256_bytes(private_ciphertext),
        signer_key_id_sha256=sha256_bytes(raw_public),
        openssh_sha256_fingerprint=fingerprint,
        argon2_memory_kib=argon2_memory,
        argon2_passes=argon2_passes,
        argon2_parallelism=argon2_parallelism,
    )


def admit_ppk_import_preflight(record: Mapping[str, Any]) -> PpkImportPreflight:
    if not isinstance(record, Mapping):
        raise ValueError("PPK import preflight must be a mapping")
    expected = {
        "schema_version",
        "record_kind",
        *PpkImportPreflight.__dataclass_fields__,
        "preflight_sha256",
    }
    if (
        set(record) != expected
        or record.get("schema_version") != SCHEMA_VERSION
        or record.get("record_kind") != RECORD_KIND
    ):
        raise ValueError("PPK import preflight shape is invalid")
    values = {name: record[name] for name in PpkImportPreflight.__dataclass_fields__}
    preflight = PpkImportPreflight(**values)
    if preflight.to_dict() != dict(record):
        raise ValueError("PPK import preflight is not exact canonical form")
    return preflight


__all__ = [
    "MAX_PPK_BYTES",
    "MAX_PUBLIC_KEY_FILE_BYTES",
    "PREFLIGHT_STATE",
    "PpkImportPreflight",
    "admit_ppk_import_preflight",
    "inspect_ppk_import_preflight",
]
