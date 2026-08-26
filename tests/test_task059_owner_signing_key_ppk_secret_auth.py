from __future__ import annotations

import base64
import hashlib
import hmac
import inspect
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
import pytest

from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.owner_signing_key_ppk_preflight import (
    inspect_ppk_import_preflight,
)
from ai_video_production.owner_signing_key_ppk_secret_auth import (
    _AuthenticatedPpkSecret,
    _authenticate_ppk_secret_for_r9b,
)
from ai_video_production.serialization import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
SEED = bytes(range(1, 33))
PASSPHRASE = "synthetic-passphrase-雪".encode("utf-8")
OBSERVED_AT = 1_777_100_000_000
COMMENT = "task059-synthetic"


def _ssh_string(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def _public(seed: bytes = SEED) -> bytes:
    return (
        Ed25519PrivateKey.from_private_bytes(seed)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )


def _public_blob(seed: bytes = SEED) -> bytes:
    return _ssh_string(b"ssh-ed25519") + _ssh_string(_public(seed))


def _fingerprint(seed: bytes = SEED) -> str:
    digest = hashlib.sha256(_public_blob(seed)).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def _mpint(value: bytes) -> bytes:
    normalized = value.lstrip(b"\x00")
    if not normalized:
        normalized = b"\x00"
    if normalized[0] >= 0x80:
        normalized = b"\x00" + normalized
    return _ssh_string(normalized)


def _b64_lines(value: bytes) -> list[str]:
    encoded = base64.b64encode(value).decode("ascii")
    return [encoded[index : index + 64] for index in range(0, len(encoded), 64)]


def _rfc4716(seed: bytes = SEED) -> bytes:
    lines = [
        "---- BEGIN SSH2 PUBLIC KEY ----",
        'Comment: "task059-synthetic"',
        *_b64_lines(_public_blob(seed)),
        "---- END SSH2 PUBLIC KEY ----",
    ]
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def _ppk(
    *,
    seed: bytes = SEED,
    passphrase: bytes = PASSPHRASE,
    comment: str = COMMENT,
    private_plaintext: bytes | None = None,
    salt: bytes = bytes.fromhex("00112233445566778899aabbccddeeff"),
) -> bytes:
    public_blob = _public_blob(seed)
    if private_plaintext is None:
        encoded_seed = _mpint(seed)
        padding_size = (-len(encoded_seed)) % 16
        private_plaintext = encoded_seed + bytes(range(1, padding_size + 1))
    assert len(private_plaintext) % 16 == 0
    derived = Argon2id(
        salt=salt,
        length=80,
        iterations=3,
        lanes=1,
        memory_cost=8192,
        ad=None,
        secret=None,
    ).derive(passphrase)
    encryptor = Cipher(
        algorithms.AES(derived[:32]), modes.CBC(derived[32:48])
    ).encryptor()
    ciphertext = encryptor.update(private_plaintext) + encryptor.finalize()
    mac_preimage = b"".join(
        _ssh_string(value)
        for value in (
            b"ssh-ed25519",
            b"aes256-cbc",
            comment.encode("ascii"),
            public_blob,
            private_plaintext,
        )
    )
    private_mac = hmac.digest(derived[48:80], mac_preimage, "sha256").hex()
    public_lines = _b64_lines(public_blob)
    private_lines = _b64_lines(ciphertext)
    lines = [
        "PuTTY-User-Key-File-3: ssh-ed25519",
        "Encryption: aes256-cbc",
        f"Comment: {comment}",
        f"Public-Lines: {len(public_lines)}",
        *public_lines,
        "Key-Derivation: Argon2id",
        "Argon2-Memory: 8192",
        "Argon2-Passes: 3",
        "Argon2-Parallelism: 1",
        f"Argon2-Salt: {salt.hex()}",
        f"Private-Lines: {len(private_lines)}",
        *private_lines,
        f"Private-MAC: {private_mac}",
    ]
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def _preflight(ppk: bytes, public: bytes | None = None) -> dict[str, object]:
    return inspect_ppk_import_preflight(
        ppk,
        public if public is not None else _rfc4716(),
        expected_openssh_sha256_fingerprint=_fingerprint(),
        observed_at_epoch_ms=OBSERVED_AT,
    ).to_dict()


def _authenticate(
    ppk: bytes,
    *,
    passphrase: bytes = PASSPHRASE,
    preflight: dict[str, object] | None = None,
) -> tuple[_AuthenticatedPpkSecret, bytearray]:
    mutable = bytearray(passphrase)
    secret = _authenticate_ppk_secret_for_r9b(
        ppk,
        _rfc4716(),
        passphrase_utf8=mutable,
        expected_preflight_payload=preflight if preflight is not None else _preflight(ppk),
    )
    return secret, mutable


def test_authenticates_exact_ppk_and_clears_passphrase_and_seed_once() -> None:
    ppk = _ppk()
    secret, mutable = _authenticate(ppk)

    assert mutable == bytearray(len(PASSPHRASE))
    assert secret.ppk_file_sha256 == sha256_bytes(ppk)
    assert secret.signer_key_id_sha256 == sha256_bytes(_public())
    assert secret.openssh_sha256_fingerprint == _fingerprint()
    assert PASSPHRASE.decode("utf-8") not in repr(secret)
    assert base64.b64encode(SEED).decode("ascii") not in repr(secret)
    assert secret.cleared is False

    consumed = secret._consume_seed_for_r9b_once()
    assert consumed == SEED
    assert secret.cleared is True
    with pytest.raises(ValueError, match="already cleared"):
        secret._consume_seed_for_r9b_once()


def test_context_manager_clears_unconsumed_seed() -> None:
    secret, _ = _authenticate(_ppk())
    with secret as active:
        assert active.cleared is False
    assert secret.cleared is True


@pytest.mark.parametrize(
    "seed",
    [
        b"\x00" + bytes(range(1, 32)),
        b"\x80" + bytes(range(1, 32)),
    ],
)
def test_canonical_short_or_sign_prefixed_mpint_normalizes_to_exact_seed(
    seed: bytes,
) -> None:
    ppk = _ppk(seed=seed)
    public = _rfc4716(seed)
    expected = inspect_ppk_import_preflight(
        ppk,
        public,
        expected_openssh_sha256_fingerprint=_fingerprint(seed),
        observed_at_epoch_ms=OBSERVED_AT,
    ).to_dict()
    mutable = bytearray(PASSPHRASE)
    secret = _authenticate_ppk_secret_for_r9b(
        ppk,
        public,
        passphrase_utf8=mutable,
        expected_preflight_payload=expected,
    )
    assert secret._consume_seed_for_r9b_once() == seed
    assert mutable == bytearray(len(PASSPHRASE))

def test_wrong_passphrase_is_one_body_free_security_error_and_input_is_cleared() -> None:
    ppk = _ppk()
    mutable = bytearray(b"wrong-passphrase")
    with pytest.raises(ProductError) as caught:
        _authenticate_ppk_secret_for_r9b(
            ppk,
            _rfc4716(),
            passphrase_utf8=mutable,
            expected_preflight_payload=_preflight(ppk),
        )
    error = caught.value
    assert error.code == "ERR_PPK_SECRET_AUTHENTICATION_FAILED"
    assert error.category is ProductErrorCategory.SECURITY
    assert error.details == {}
    assert "wrong-passphrase" not in json.dumps(error.to_envelope())
    assert mutable == bytearray(len(b"wrong-passphrase"))


@pytest.mark.parametrize("field", ["comment", "ciphertext"])
def test_authenticated_file_tamper_collapses_to_same_public_error(field: str) -> None:
    original = _ppk()
    if field == "comment":
        tampered = original.replace(
            f"Comment: {COMMENT}".encode("ascii"), b"Comment: task059-tampered"
        )
    else:
        lines = original.decode("ascii").splitlines()
        private_header = next(index for index, line in enumerate(lines) if line.startswith("Private-Lines: "))
        data_index = private_header + 1
        first = "A" if lines[data_index][0] != "A" else "B"
        lines[data_index] = first + lines[data_index][1:]
        tampered = ("\r\n".join(lines) + "\r\n").encode("ascii")
    expected = _preflight(tampered)
    mutable = bytearray(PASSPHRASE)
    with pytest.raises(ProductError) as caught:
        _authenticate_ppk_secret_for_r9b(
            tampered,
            _rfc4716(),
            passphrase_utf8=mutable,
            expected_preflight_payload=expected,
        )
    assert caught.value.code == "ERR_PPK_SECRET_AUTHENTICATION_FAILED"
    assert mutable == bytearray(len(PASSPHRASE))


def test_preflight_or_file_drift_fails_before_authentication_claim() -> None:
    ppk = _ppk()
    expected = _preflight(ppk)
    expected["preflight_sha256"] = "sha256:" + "0" * 64
    mutable = bytearray(PASSPHRASE)
    with pytest.raises(ProductError) as caught:
        _authenticate_ppk_secret_for_r9b(
            ppk,
            _rfc4716(),
            passphrase_utf8=mutable,
            expected_preflight_payload=expected,
        )
    assert caught.value.code == "ERR_PPK_PREFLIGHT_DRIFT"
    assert caught.value.category is ProductErrorCategory.DATA_INTEGRITY
    assert mutable == bytearray(len(PASSPHRASE))


@pytest.mark.parametrize(
    "encoded",
    [
        b"\x00" + SEED,
        bytes([0x80]) + SEED[1:],
        b"\x00\x01" + SEED[1:],
        b"\x01" * 34,
    ],
)
def test_noncanonical_or_invalid_authenticated_mpint_fails_closed(encoded: bytes) -> None:
    private = _ssh_string(encoded)
    private += bytes(range(1, (-len(private)) % 16 + 1))
    assert len(private) % 16 == 0
    ppk = _ppk(private_plaintext=private)
    mutable = bytearray(PASSPHRASE)
    with pytest.raises(ProductError) as caught:
        _authenticate_ppk_secret_for_r9b(
            ppk,
            _rfc4716(),
            passphrase_utf8=mutable,
            expected_preflight_payload=_preflight(ppk),
        )
    assert caught.value.code == "ERR_PPK_SECRET_AUTHENTICATION_FAILED"
    assert mutable == bytearray(len(PASSPHRASE))


def test_internal_module_has_no_effectful_import_or_public_export() -> None:
    source = inspect.getsource(
        __import__(
            "ai_video_production.owner_signing_key_ppk_secret_auth",
            fromlist=["owner_signing_key_ppk_secret_auth"],
        )
    )
    for forbidden in (
        "subprocess",
        "requests",
        "socket",
        "pathlib",
        "OwnerSigningKeyCustodyStore",
        "WindowsDpapiOwnerSigningKeyCipher",
        "open(",
    ):
        assert forbidden not in source
    namespace: dict[str, object] = {}
    exec("from ai_video_production.owner_signing_key_ppk_secret_auth import *", namespace)
    assert set(namespace) == {"__builtins__"}


def test_invalid_passphrase_shape_is_rejected_without_secret_operation() -> None:
    ppk = _ppk()
    empty = bytearray()
    with pytest.raises(ValueError, match="bounded mutable"):
        _authenticate_ppk_secret_for_r9b(
            ppk,
            _rfc4716(),
            passphrase_utf8=empty,
            expected_preflight_payload=_preflight(ppk),
        )
    assert empty == bytearray()
    containing_nul = bytearray(b"contains\x00nul")
    with pytest.raises(ValueError, match="bounded mutable"):
        _authenticate_ppk_secret_for_r9b(
            ppk,
            _rfc4716(),
            passphrase_utf8=containing_nul,
            expected_preflight_payload=_preflight(ppk),
        )
    assert containing_nul == bytearray(len(b"contains\x00nul"))
