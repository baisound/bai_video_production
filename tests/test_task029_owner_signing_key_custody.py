from __future__ import annotations
import ast, json, os
from pathlib import Path
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator
from ai_video_production.errors import ProductError
from ai_video_production.owner_signing_key_custody import (
    OwnerSigningKeyCustodyConfirmation,
    OwnerSigningKeyCustodyReceipt,
    OwnerSigningKeyCustodyStore,
    WindowsDpapiOwnerSigningKeyCipher,
    confirm_owner_signing_key_custody,
)

ROOT = Path(__file__).resolve().parents[1]
SCOPE = "sha256:" + "1" * 64

class SyntheticCipher:
    cipher_suite = "TEST_OWNER_SIGNING_KEY_CUSTODY_V1"
    def __init__(self, key: int = 0x5A) -> None: self.key = key
    def encrypt(self, plaintext: bytes) -> bytes: return b"T1" + bytes(x ^ self.key for x in plaintext)
    def decrypt(self, ciphertext: bytes) -> bytes:
        if not ciphertext.startswith(b"T1"): raise ValueError("wrong ciphertext")
        return bytes(x ^ self.key for x in ciphertext[2:])

def material() -> tuple[bytes, bytes]:
    private = Ed25519PrivateKey.generate()
    seed = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return seed, public

def confirmation(public: bytes, **overrides: object) -> OwnerSigningKeyCustodyConfirmation:
    values = dict(
        confirmation_id="confirmation-1", custody_id="custody-1",
        owner_scope_sha256=SCOPE, signer_public_key=public,
        confirmed_at_epoch_ms=1_777_000_000_000,
        explicit_human_confirmation=True,
    )
    values.update(overrides)
    return confirm_owner_signing_key_custody(**values)

def provision(path: Path, cipher: SyntheticCipher | None = None):
    seed, public = material()
    store = OwnerSigningKeyCustodyStore(path, cipher or SyntheticCipher())
    result = store.provision(
        receipt_id="receipt-1", custody_id="custody-1",
        owner_scope_sha256=SCOPE, private_key_seed=seed,
        confirmation=confirmation(public),
        custodied_at_epoch_ms=1_777_000_000_001,
    )
    return seed, public, store, result

def test_round_trip_is_encrypted_and_receipt_is_body_free(tmp_path: Path) -> None:
    path = tmp_path / "custody.json"
    seed, public, store, result = provision(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    assert set(document) == {
        "schema_version", "record_type", "task_owner", "cipher_suite",
        "ciphertext_b64", "ciphertext_sha256", "plaintext_fields_present",
        "document_sha256",
    }
    assert document["plaintext_fields_present"] is False
    raw = path.read_bytes()
    assert seed not in raw and public not in raw
    assert result.receipt == store.read_receipt()
    receipt = result.receipt.to_dict()
    assert receipt["state"] == "CUSTODIED"
    assert receipt["encrypted_at_rest"] is True
    assert receipt["private_key_material_included"] is False
    assert receipt["public_key_material_included"] is False
    assert receipt["private_key_export_authorized"] is False
    assert receipt["signing_authorized"] is False
    assert "private_key_seed_b64" not in receipt
    assert "signer_public_key_b64" not in receipt
    assert OwnerSigningKeyCustodyReceipt.from_dict(receipt).to_dict() == receipt

def test_explicit_human_confirmation_is_required() -> None:
    _, public = material()
    with pytest.raises(ProductError) as error:
        confirmation(public, explicit_human_confirmation=False)
    assert error.value.code == "ERR_OWNER_SIGNING_KEY_CUSTODY_CONFIRMATION_REQUIRED"

@pytest.mark.parametrize("value", [b"", b"x" * 31, b"x" * 33, bytearray(b"x" * 32)])
def test_public_key_size_and_type_are_strict(value: object) -> None:
    with pytest.raises(ValueError):
        confirmation(value)  # type: ignore[arg-type]

def test_confirmation_must_bind_exact_key_scope_and_custody(tmp_path: Path) -> None:
    seed, public = material()
    wrong = confirmation(public, custody_id="custody-other")
    store = OwnerSigningKeyCustodyStore(tmp_path / "custody.json", SyntheticCipher())
    with pytest.raises(ValueError, match="does not match"):
        store.provision(
            receipt_id="receipt-1", custody_id="custody-1",
            owner_scope_sha256=SCOPE, private_key_seed=seed,
            confirmation=wrong, custodied_at_epoch_ms=1,
        )
    assert not store.path.exists()

def test_one_shot_store_rejects_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "custody.json"
    _, _, store, _ = provision(path)
    seed, public = material()
    with pytest.raises(ProductError) as error:
        store.provision(
            receipt_id="receipt-2", custody_id="custody-2",
            owner_scope_sha256=SCOPE, private_key_seed=seed,
            confirmation=confirmation(public, confirmation_id="confirmation-2", custody_id="custody-2"),
            custodied_at_epoch_ms=2,
        )
    assert error.value.code == "ERR_OWNER_SIGNING_KEY_CUSTODY_ALREADY_EXISTS"
    assert store.read_receipt().receipt_id == "receipt-1"

def test_tamper_and_wrong_cipher_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "custody.json"
    _, _, store, _ = provision(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["ciphertext_b64"] = document["ciphertext_b64"][:-4] + "AAAA"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as error:
        store.read_receipt()
    assert error.value.code == "ERR_OWNER_SIGNING_KEY_CUSTODY_INTEGRITY"

    other = tmp_path / "other.json"
    provision(other, SyntheticCipher(0x33))
    with pytest.raises(ProductError):
        OwnerSigningKeyCustodyStore(other, SyntheticCipher(0x44)).read_receipt()

def test_plaintext_symlink_and_atomic_failure_fail_closed(tmp_path: Path) -> None:
    plain = tmp_path / "plain.json"
    plain.write_text('{"private_key_seed_b64":"secret"}', encoding="utf-8")
    with pytest.raises(ProductError):
        OwnerSigningKeyCustodyStore(plain, SyntheticCipher()).read_receipt()

    target = tmp_path / "target.json"; target.write_text("{}", encoding="utf-8")
    link = tmp_path / "link.json"
    try: link.symlink_to(target)
    except OSError: pass
    else:
        seed, public = material()
        with pytest.raises(ProductError):
            OwnerSigningKeyCustodyStore(link, SyntheticCipher()).provision(
                receipt_id="r", custody_id="c", owner_scope_sha256=SCOPE,
                private_key_seed=seed, confirmation=confirmation(public, custody_id="c"),
                custodied_at_epoch_ms=1,
            )

    failed = tmp_path / "failed.json"
    seed, public = material()
    def stop(stage: str, _: Path) -> None:
        if stage == "before_replace": raise RuntimeError("injected")
    with pytest.raises(RuntimeError, match="injected"):
        OwnerSigningKeyCustodyStore(failed, SyntheticCipher()).provision(
            receipt_id="r", custody_id="c", owner_scope_sha256=SCOPE,
            private_key_seed=seed, confirmation=confirmation(public, custody_id="c"),
            custodied_at_epoch_ms=1, failure_injector=stop,
        )
    assert not failed.exists()

def test_schema_mirror_and_generated_envelope_validate(tmp_path: Path) -> None:
    public_schema = ROOT / "schemas/owner-signing-key-custody-store.schema.json"
    package_schema = ROOT / "src/ai_video_production/schema_resources/owner-signing-key-custody-store.schema.json"
    assert public_schema.read_bytes() == package_schema.read_bytes()
    schema = json.loads(public_schema.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    path = tmp_path / "custody.json"; provision(path)
    Draft202012Validator(schema).validate(json.loads(path.read_text(encoding="utf-8")))

def test_public_module_has_no_sign_export_generation_or_external_io() -> None:
    source_path = ROOT / "src/ai_video_production/owner_signing_key_custody.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert imports.isdisjoint({"requests", "httpx", "socket", "subprocess"})
    public_methods = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "sign" not in public_methods
    assert "export" not in public_methods
    assert "generate" not in public_methods
    assert "PUTTY" not in source.upper()
    assert "OPENSSH" not in source.upper()

@pytest.mark.skipif(os.name != "nt", reason="Windows Current User DPAPI only")
def test_windows_dpapi_round_trip_uses_synthetic_key_only(tmp_path: Path) -> None:
    seed, public = material()
    store = OwnerSigningKeyCustodyStore(tmp_path / "dpapi.json", WindowsDpapiOwnerSigningKeyCipher())
    result = store.provision(
        receipt_id="receipt-dpapi", custody_id="custody-dpapi",
        owner_scope_sha256=SCOPE, private_key_seed=seed,
        confirmation=confirmation(public, confirmation_id="confirmation-dpapi", custody_id="custody-dpapi"),
        custodied_at_epoch_ms=1,
    )
    assert store.read_receipt() == result.receipt
