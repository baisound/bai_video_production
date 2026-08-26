from __future__ import annotations

import ast
import base64
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
import textwrap

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.owner_signing_key_ppk_preflight import (
    MAX_PPK_BYTES,
    PREFLIGHT_STATE,
    PpkImportPreflight,
    admit_ppk_import_preflight,
    inspect_ppk_import_preflight,
)
from ai_video_production.serialization import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = bytes(range(32))
OTHER_PUBLIC = bytes(reversed(range(32)))
PRIVATE_CIPHERTEXT = b"encrypted-block!" * 2
OBSERVED_AT = 1_777_000_000_000


def _ssh_string(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def _public_blob(public: bytes = PUBLIC) -> bytes:
    return _ssh_string(b"ssh-ed25519") + _ssh_string(public)


def _b64_lines(value: bytes) -> list[str]:
    return textwrap.wrap(base64.b64encode(value).decode("ascii"), 64)


def _fingerprint(public: bytes = PUBLIC) -> str:
    digest = hashlib.sha256(_public_blob(public)).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def _rfc4716(public: bytes = PUBLIC) -> bytes:
    lines = [
        "---- BEGIN SSH2 PUBLIC KEY ----",
        'Comment: "owner-public"',
        *_b64_lines(_public_blob(public)),
        "---- END SSH2 PUBLIC KEY ----",
    ]
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def _ppk(
    public: bytes = PUBLIC,
    *,
    version: int = 3,
    algorithm: str = "ssh-ed25519",
    encryption: str = "aes256-cbc",
    key_derivation: str = "Argon2id",
    memory: str = "8192",
    passes: str = "34",
    parallelism: str = "1",
    salt: str = "ab" * 16,
    private_ciphertext: bytes = PRIVATE_CIPHERTEXT,
    private_mac: str = "c" * 64,
    trailing: tuple[str, ...] = (),
) -> bytes:
    public_lines = _b64_lines(_public_blob(public))
    private_lines = _b64_lines(private_ciphertext)
    lines = [
        f"PuTTY-User-Key-File-{version}: {algorithm}",
        f"Encryption: {encryption}",
        "Comment: eddsa-key-20260826",
        f"Public-Lines: {len(public_lines)}",
        *public_lines,
        f"Key-Derivation: {key_derivation}",
        f"Argon2-Memory: {memory}",
        f"Argon2-Passes: {passes}",
        f"Argon2-Parallelism: {parallelism}",
        f"Argon2-Salt: {salt}",
        f"Private-Lines: {len(private_lines)}",
        *private_lines,
        f"Private-MAC: {private_mac}",
        *trailing,
    ]
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def _inspect(ppk: bytes | None = None, public: bytes | None = None) -> PpkImportPreflight:
    return inspect_ppk_import_preflight(
        ppk if ppk is not None else _ppk(),
        public if public is not None else _rfc4716(),
        expected_openssh_sha256_fingerprint=_fingerprint(),
        observed_at_epoch_ms=OBSERVED_AT,
    )


def test_exact_encrypted_ppk_public_coordinates_produce_body_free_preflight() -> None:
    ppk = _ppk()
    public = _rfc4716()
    result = _inspect(ppk, public)

    assert result.ppk_format_version == 3
    assert result.algorithm == "ssh-ed25519"
    assert result.encryption == "aes256-cbc"
    assert result.key_derivation == "Argon2id"
    assert result.ppk_file_sha256 == sha256_bytes(ppk)
    assert result.public_key_file_sha256 == sha256_bytes(public)
    assert result.signer_key_id_sha256 == sha256_bytes(PUBLIC)
    assert result.openssh_sha256_fingerprint == _fingerprint()
    assert result.private_ciphertext_sha256 == sha256_bytes(PRIVATE_CIPHERTEXT)
    assert result.public_coordinates_match is True
    assert result.expected_fingerprint_match is True
    assert result.passphrase_received is False
    assert result.private_mac_verified is False
    assert result.private_key_decrypted is False
    assert result.custody_import_authorized is False
    assert result.custody_import_started is False
    assert result.signing_authorized is False
    assert result.external_effect_authorized is False
    assert result.state == PREFLIGHT_STATE
    assert admit_ppk_import_preflight(result.to_dict()) == result

    public_record = json.dumps(result.to_dict())
    assert base64.b64encode(PRIVATE_CIPHERTEXT).decode("ascii") not in public_record
    assert base64.b64encode(PUBLIC).decode("ascii") not in public_record
    assert "eddsa-key-20260826" not in public_record
    assert "comment_sha256" not in result.to_dict()


def test_schema_mirror_and_record_validation() -> None:
    canonical = ROOT / "schemas" / "owner-signing-key-ppk-import-preflight.schema.json"
    mirror = (
        ROOT
        / "src"
        / "ai_video_production"
        / "schema_resources"
        / canonical.name
    )
    assert canonical.read_bytes() == mirror.read_bytes()
    schema = json.loads(canonical.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_inspect().to_dict())


def test_public_key_and_owner_fingerprint_must_both_match() -> None:
    with pytest.raises(ValueError, match="do not match"):
        _inspect(public=_rfc4716(OTHER_PUBLIC))
    with pytest.raises(ValueError, match="expected Owner fingerprint"):
        inspect_ppk_import_preflight(
            _ppk(),
            _rfc4716(),
            expected_openssh_sha256_fingerprint=_fingerprint(OTHER_PUBLIC),
            observed_at_epoch_ms=OBSERVED_AT,
        )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"version": 2}, "PuTTY-User-Key-File-3"),
        ({"algorithm": "ssh-rsa"}, "algorithm"),
        ({"encryption": "none"}, "aes256-cbc"),
        ({"key_derivation": "Argon2d"}, "Argon2id"),
        ({"memory": "8191"}, "security floor"),
        ({"memory": "262145"}, "ceiling"),
        ({"passes": "2"}, "security floor"),
        ({"passes": "0"}, "canonical positive decimal"),
        ({"parallelism": "01"}, "canonical positive decimal"),
        ({"parallelism": "17"}, "ceiling"),
        ({"salt": "xyz"}, "Salt"),
        ({"private_mac": "d" * 40}, "Private-MAC"),
        ({"private_ciphertext": b"not-aligned"}, "AES block aligned"),
        ({"trailing": ("Unexpected: value",)}, "trailing"),
    ],
)
def test_unsupported_or_unsafe_ppk_metadata_fails_closed(
    kwargs: dict[str, object], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        _inspect(ppk=_ppk(**kwargs))


@pytest.mark.parametrize(
    "ppk",
    [
        b"",
        b"\x00bad",
        b"\xffbad",
        b"PuTTY-User-Key-File-3: ssh-ed25519\n",
        b"x" * (MAX_PPK_BYTES + 1),
    ],
)
def test_malformed_truncated_or_oversized_ppk_is_value_error(ppk: bytes) -> None:
    with pytest.raises(ValueError):
        _inspect(ppk=ppk)


def test_rfc4716_boundary_and_blob_are_strict() -> None:
    with pytest.raises(ValueError, match="boundary"):
        _inspect(public=b"ssh-ed25519 AAAA\n")
    with pytest.raises(ValueError, match="unsupported headers"):
        value = _rfc4716().replace(b"Comment: ", b"Unknown: ")
        _inspect(public=value)
    with pytest.raises(ValueError, match="Ed25519"):
        malformed = _ssh_string(b"ssh-ed25519") + _ssh_string(b"short")
        lines = [
            "---- BEGIN SSH2 PUBLIC KEY ----",
            *_b64_lines(malformed),
            "---- END SSH2 PUBLIC KEY ----",
        ]
        _inspect(public=("\n".join(lines) + "\n").encode("ascii"))


def test_exact_admission_rejects_tamper_unknown_fields_and_effect_flags() -> None:
    record = _inspect().to_dict()
    record["custody_import_authorized"] = True
    with pytest.raises(ValueError):
        admit_ppk_import_preflight(record)

    record = _inspect().to_dict()
    record["ppk_file_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="canonical"):
        admit_ppk_import_preflight(record)

    record = _inspect().to_dict()
    record["private_key_seed_b64"] = "forbidden"
    with pytest.raises(ValueError, match="shape"):
        admit_ppk_import_preflight(record)


def test_preflight_constructor_cannot_claim_secret_or_external_effect() -> None:
    value = _inspect()
    for field in (
        "passphrase_received",
        "private_mac_verified",
        "private_key_decrypted",
        "custody_import_authorized",
        "custody_import_started",
        "signing_authorized",
        "external_effect_authorized",
    ):
        with pytest.raises(ValueError, match="cannot grant"):
            replace(value, **{field: True})


def test_module_has_no_secret_input_filesystem_subprocess_network_or_custody_effect() -> None:
    source_path = ROOT / "src" / "ai_video_production" / "owner_signing_key_ppk_preflight.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imports.isdisjoint({"ctypes", "os", "pathlib", "requests", "httpx", "socket", "subprocess"})
    parameters = inspect.signature(inspect_ppk_import_preflight).parameters
    assert "passphrase" not in parameters
    assert "private_key_seed" not in parameters
    assert "custody_store" not in parameters
    assert "OwnerSigningKeyCustodyStore" not in source
    assert "WindowsDpapiOwnerSigningKeyCipher" not in source
