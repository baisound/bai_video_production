"""TASK-059 P1A isolated PPK v3 secret-authentication core.

This internal module authenticates synthetic or helper-local encrypted PPK
bytes. It performs no filesystem, process, UI, DPAPI, custody, or signing
effect. Callers must keep the returned secret inside the short-lived helper.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import hmac
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from .errors import ProductError, ProductErrorCategory
from .owner_signing_key_ppk_preflight import (
    admit_ppk_import_preflight,
    inspect_ppk_import_preflight,
)
from .serialization import sha256_bytes


_MAX_PASSPHRASE_BYTES = 1024
_AUTHENTICATION_ERROR_CODE = "ERR_PPK_SECRET_AUTHENTICATION_FAILED"


def _zero(value: bytearray | None) -> None:
    if value is not None:
        value[:] = b"\x00" * len(value)


def _header(line: str, name: str) -> str:
    prefix = f"{name}: "
    if not line.startswith(prefix):
        raise ValueError(f"expected {name}")
    value = line[len(prefix) :]
    if not value:
        raise ValueError(f"empty {name}")
    return value


def _positive_decimal(value: str, *, maximum: int) -> int:
    if not value.isascii() or not value.isdecimal() or value.startswith("0"):
        raise ValueError("noncanonical decimal")
    result = int(value)
    if result < 1 or result > maximum:
        raise ValueError("decimal outside bounds")
    return result


def _decode_b64(lines: list[str]) -> bytes:
    if not lines:
        raise ValueError("empty base64 block")
    return base64.b64decode("".join(lines), validate=True)


def _ssh_string(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def _read_ssh_string(value: bytes, offset: int = 0) -> tuple[bytes, int]:
    if offset + 4 > len(value):
        raise ValueError("truncated SSH string")
    size = int.from_bytes(value[offset : offset + 4], "big")
    offset += 4
    if size < 1 or offset + size > len(value):
        raise ValueError("invalid SSH string")
    return value[offset : offset + size], offset + size


def _raw_public_from_blob(value: bytes) -> bytes:
    algorithm, offset = _read_ssh_string(value)
    public_key, offset = _read_ssh_string(value, offset)
    if algorithm != b"ssh-ed25519" or len(public_key) != 32 or offset != len(value):
        raise ValueError("invalid Ed25519 public blob")
    return public_key


def _openssh_fingerprint(public_blob: bytes) -> str:
    digest = hashlib.sha256(public_blob).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


@dataclass(frozen=True, slots=True)
class _EncryptedPpkV3:
    algorithm: bytes
    encryption: bytes
    comment: bytes = field(repr=False)
    public_blob: bytes = field(repr=False)
    argon2_memory_kib: int
    argon2_passes: int
    argon2_parallelism: int
    salt: bytes = field(repr=False)
    private_ciphertext: bytes = field(repr=False)
    private_mac: bytes = field(repr=False)


def _parse_encrypted_ppk_v3(ppk_document: bytes) -> _EncryptedPpkV3:
    text = ppk_document.decode("ascii")
    lines = text.splitlines()
    if len(lines) < 13:
        raise ValueError("truncated PPK")
    index = 0
    algorithm_text = _header(lines[index], "PuTTY-User-Key-File-3")
    index += 1
    encryption_text = _header(lines[index], "Encryption")
    index += 1
    comment_text = _header(lines[index], "Comment")
    index += 1
    public_count = _positive_decimal(
        _header(lines[index], "Public-Lines"), maximum=64
    )
    index += 1
    public_end = index + public_count
    if public_end > len(lines):
        raise ValueError("truncated public block")
    public_blob = _decode_b64(lines[index:public_end])
    index = public_end
    key_derivation = _header(lines[index], "Key-Derivation")
    index += 1
    memory = _positive_decimal(_header(lines[index], "Argon2-Memory"), maximum=262_144)
    index += 1
    passes = _positive_decimal(_header(lines[index], "Argon2-Passes"), maximum=128)
    index += 1
    parallelism = _positive_decimal(
        _header(lines[index], "Argon2-Parallelism"), maximum=16
    )
    index += 1
    salt = bytes.fromhex(_header(lines[index], "Argon2-Salt"))
    index += 1
    private_count = _positive_decimal(
        _header(lines[index], "Private-Lines"), maximum=256
    )
    index += 1
    private_end = index + private_count
    if private_end + 1 != len(lines):
        raise ValueError("invalid private block shape")
    private_ciphertext = _decode_b64(lines[index:private_end])
    private_mac = bytes.fromhex(_header(lines[private_end], "Private-MAC"))
    if (
        algorithm_text != "ssh-ed25519"
        or encryption_text != "aes256-cbc"
        or key_derivation != "Argon2id"
        or memory < 8192
        or passes < 3
        or not 16 <= len(salt) <= 64
        or not private_ciphertext
        or len(private_ciphertext) % 16
        or len(private_mac) != 32
    ):
        raise ValueError("unsupported PPK secret parameters")
    _raw_public_from_blob(public_blob)
    return _EncryptedPpkV3(
        algorithm=algorithm_text.encode("ascii"),
        encryption=encryption_text.encode("ascii"),
        comment=comment_text.encode("ascii"),
        public_blob=public_blob,
        argon2_memory_kib=memory,
        argon2_passes=passes,
        argon2_parallelism=parallelism,
        salt=salt,
        private_ciphertext=private_ciphertext,
        private_mac=private_mac,
    )


def _seed_from_authenticated_private_blob(value: bytearray) -> bytearray:
    if len(value) < 5:
        raise ValueError("private blob is truncated")
    size = int.from_bytes(value[:4], "big")
    if size < 1 or size > 33 or 4 + size > len(value):
        raise ValueError("private exponent size is invalid")
    encoded = bytes(value[4 : 4 + size])
    if encoded[0] == 0:
        if len(encoded) == 1 or encoded[1] < 0x80:
            raise ValueError("private exponent has redundant sign byte")
        encoded = encoded[1:]
    elif encoded[0] >= 0x80:
        raise ValueError("private exponent is negative")
    if not encoded or len(encoded) > 32 or all(byte == 0 for byte in encoded):
        raise ValueError("private exponent is outside Ed25519 bounds")
    return bytearray(encoded.rjust(32, b"\x00"))


@dataclass(slots=True, repr=False)
class _AuthenticatedPpkSecret:
    _private_key_seed: bytearray
    preflight_sha256: str
    ppk_file_sha256: str
    signer_key_id_sha256: str
    openssh_sha256_fingerprint: str
    _cleared: bool = False

    def __repr__(self) -> str:
        return (
            "_AuthenticatedPpkSecret("
            f"preflight_sha256={self.preflight_sha256!r}, "
            f"signer_key_id_sha256={self.signer_key_id_sha256!r}, "
            f"cleared={self._cleared!r})"
        )

    @property
    def cleared(self) -> bool:
        return self._cleared

    def _consume_seed_for_r9b_once(self) -> bytes:
        if self._cleared:
            raise ValueError("authenticated PPK secret was already cleared")
        result = bytes(self._private_key_seed)
        self.clear()
        return result

    def clear(self) -> None:
        if not self._cleared:
            _zero(self._private_key_seed)
            self._cleared = True

    def __enter__(self) -> "_AuthenticatedPpkSecret":
        if self._cleared:
            raise ValueError("authenticated PPK secret was already cleared")
        return self

    def __exit__(self, *_: object) -> None:
        self.clear()


def _preflight_drift_error() -> ProductError:
    return ProductError(
        "ERR_PPK_PREFLIGHT_DRIFT",
        "PPK import inputs no longer match the exact preflight",
        ProductErrorCategory.DATA_INTEGRITY,
    )


def _authentication_error() -> ProductError:
    return ProductError(
        _AUTHENTICATION_ERROR_CODE,
        "Encrypted PPK authentication failed",
        ProductErrorCategory.SECURITY,
    )


def _authenticate_ppk_secret_for_r9b(
    ppk_document: bytes,
    rfc4716_public_key: bytes,
    *,
    passphrase_utf8: bytearray,
    expected_preflight_payload: Mapping[str, Any],
) -> _AuthenticatedPpkSecret:
    """Authenticate one exact PPK and return helper-local one-shot seed access."""

    if not isinstance(passphrase_utf8, bytearray):
        raise ValueError("passphrase_utf8 must be a non-empty bounded mutable buffer")
    if not 1 <= len(passphrase_utf8) <= _MAX_PASSPHRASE_BYTES or 0 in passphrase_utf8:
        _zero(passphrase_utf8)
        raise ValueError("passphrase_utf8 must be a non-empty bounded mutable buffer")

    key_material: bytearray | None = None
    plaintext: bytearray | None = None
    seed: bytearray | None = None
    try:
        try:
            expected = admit_ppk_import_preflight(expected_preflight_payload)
            fresh = inspect_ppk_import_preflight(
                ppk_document,
                rfc4716_public_key,
                expected_openssh_sha256_fingerprint=expected.openssh_sha256_fingerprint,
                observed_at_epoch_ms=expected.observed_at_epoch_ms,
            )
            if fresh.to_dict() != dict(expected_preflight_payload):
                raise _preflight_drift_error()
            parsed = _parse_encrypted_ppk_v3(ppk_document)
        except ProductError:
            raise
        except Exception:
            raise _preflight_drift_error() from None

        try:
            derived = Argon2id(
                salt=parsed.salt,
                length=80,
                iterations=parsed.argon2_passes,
                lanes=parsed.argon2_parallelism,
                memory_cost=parsed.argon2_memory_kib,
                ad=None,
                secret=None,
            ).derive(passphrase_utf8)
            key_material = bytearray(derived)
            del derived
            decryptor = Cipher(
                algorithms.AES(bytes(key_material[:32])),
                modes.CBC(bytes(key_material[32:48])),
            ).decryptor()
            plaintext = bytearray(
                decryptor.update(parsed.private_ciphertext) + decryptor.finalize()
            )
            mac_preimage = b"".join(
                _ssh_string(value)
                for value in (
                    parsed.algorithm,
                    parsed.encryption,
                    parsed.comment,
                    parsed.public_blob,
                    bytes(plaintext),
                )
            )
            calculated_mac = hmac.digest(bytes(key_material[48:80]), mac_preimage, "sha256")
            if not hmac.compare_digest(calculated_mac, parsed.private_mac):
                raise ValueError("PPK MAC mismatch")
            seed = _seed_from_authenticated_private_blob(plaintext)
            public = (
                Ed25519PrivateKey.from_private_bytes(bytes(seed))
                .public_key()
                .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            )
            public_blob = _ssh_string(b"ssh-ed25519") + _ssh_string(public)
            if (
                public_blob != parsed.public_blob
                or sha256_bytes(public) != expected.signer_key_id_sha256
                or _openssh_fingerprint(public_blob)
                != expected.openssh_sha256_fingerprint
            ):
                raise ValueError("PPK public/private key mismatch")
            result = _AuthenticatedPpkSecret(
                _private_key_seed=seed,
                preflight_sha256=expected.to_dict()["preflight_sha256"],
                ppk_file_sha256=expected.ppk_file_sha256,
                signer_key_id_sha256=expected.signer_key_id_sha256,
                openssh_sha256_fingerprint=expected.openssh_sha256_fingerprint,
            )
            seed = None
            return result
        except Exception:
            raise _authentication_error() from None
    finally:
        _zero(passphrase_utf8)
        _zero(key_material)
        _zero(plaintext)
        _zero(seed)


__all__: list[str] = []
