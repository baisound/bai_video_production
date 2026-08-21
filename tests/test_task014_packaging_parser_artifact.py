from __future__ import annotations

import base64
import ast
import builtins
from copy import deepcopy
import hashlib
import json
import pickle
from pathlib import Path
import zipfile

from jsonschema import Draft202012Validator
import pytest

from ai_video_production import packaging_parser_artifact as artifact


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "packaging-parser-artifact-verification.schema.json"
MIRROR = ROOT / "src/ai_video_production/schema_resources" / SCHEMA.name


def _record_hash(body: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode("ascii").rstrip("=")


def _payload() -> dict[str, bytes]:
    return {
        "packaging/__init__.py": b"__version__ = '25.0'\n",
        "packaging/requirements.py": b"class Requirement: pass\n",
        "packaging/version.py": b"class Version: pass\n",
        "packaging/tags.py": b"class Tag: pass\n",
        "packaging-25.0.dist-info/METADATA": b"Metadata-Version: 2.4\nName: packaging\nVersion: 25.0\nRequires-Python: >=3.8\n\n",
        "packaging-25.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nGenerator: synthetic\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n",
        "packaging-25.0.dist-info/licenses/LICENSE": b"synthetic license\n",
    }


def _wheel(tmp_path: Path, mutate: str | None = None) -> tuple[bytes, dict[str, bytes]]:
    payload = _payload()
    if mutate == "unexpected-dependency":
        payload["packaging-25.0.dist-info/METADATA"] = payload["packaging-25.0.dist-info/METADATA"].replace(
            b"\n\n", b"\nRequires-Dist: evil\n\n"
        )
    if mutate == "tag":
        payload["packaging-25.0.dist-info/WHEEL"] = payload["packaging-25.0.dist-info/WHEEL"].replace(b"py3-none-any", b"cp312-cp312-win_amd64")
    if mutate == "metadata-name":
        payload["packaging-25.0.dist-info/METADATA"] = payload["packaging-25.0.dist-info/METADATA"].replace(b"Name: packaging", b"Name: packaging\nName: evil")
    if mutate == "metadata-python":
        payload["packaging-25.0.dist-info/METADATA"] = payload["packaging-25.0.dist-info/METADATA"].replace(b">=3.8", b">=3.9")
    if mutate == "wheel-version":
        payload["packaging-25.0.dist-info/WHEEL"] = payload["packaging-25.0.dist-info/WHEEL"].replace(b"1.0", b"1.1")
    if mutate == "wheel-purelib":
        payload["packaging-25.0.dist-info/WHEEL"] = payload["packaging-25.0.dist-info/WHEEL"].replace(b"true", b"false")
    if mutate == "wheel-duplicate-tag":
        payload["packaging-25.0.dist-info/WHEEL"] = payload["packaging-25.0.dist-info/WHEEL"].replace(
            b"\n\n", b"\nTag: py3-none-any\n\n"
        )
    rows = dict(payload)
    record_name = "packaging-25.0.dist-info/RECORD"
    rows[record_name] = b""
    rows[record_name] = "".join(
        f"{name},{'' if name == record_name else _record_hash(body)},{'' if name == record_name else len(body)}\n"
        for name, body in sorted(rows.items())
    ).encode()
    if mutate == "traversal": rows["../escape.py"] = b"x"
    if mutate == "case-duplicate": rows["PACKAGING/__init__.py"] = b"x"
    if mutate == "dot-alias": rows["packaging/./alias.py"] = b"x"
    if mutate == "executable": rows["packaging/native.dll"] = b"MZ"
    if mutate == "uppercase-executable": rows["packaging/native.DLL"] = b"MZ"
    if mutate == "unexpected-top-level": rows["other/file.py"] = b"x"
    if mutate == "missing-record": del rows[record_name]
    if mutate == "missing-metadata": del rows["packaging-25.0.dist-info/METADATA"]
    if mutate == "missing-wheel": del rows["packaging-25.0.dist-info/WHEEL"]
    if mutate == "record-hash": rows[record_name] = rows[record_name].replace(_record_hash(payload["packaging/__init__.py"]).encode(), b"sha256=" + b"A" * 43)
    if mutate == "record-size": rows[record_name] = rows[record_name].replace(b",21\n", b",22\n")
    if mutate == "record-duplicate": rows[record_name] += rows[record_name].splitlines(keepends=True)[0]
    if mutate == "record-extra-row": rows[record_name] += b"packaging/ghost.py,sha256=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,1\n"
    if mutate == "record-base64": rows[record_name] = rows[record_name].replace(b"sha256=", b"sha256=!", 1)
    if mutate == "record-self-hash":
        rows[record_name] = rows[record_name].replace(
            f"{record_name},,\n".encode(), f"{record_name},sha256=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,1\n".encode()
        )
    if mutate == "record-csv": rows[record_name] += b'"unterminated,sha256=AAAA,1\n'
    path = tmp_path / "synthetic.whl"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as wheel:
        for name, body in rows.items(): wheel.writestr(name, body)
    return path.read_bytes(), payload


def _admit(monkeypatch: pytest.MonkeyPatch, raw: bytes, payload: dict[str, bytes]) -> None:
    monkeypatch.setattr(artifact, "WHEEL_BYTES", len(raw))
    monkeypatch.setattr(artifact, "WHEEL_SHA256", artifact.sha256_bytes(raw))
    monkeypatch.setattr(artifact, "METADATA_SHA256", artifact.sha256_bytes(payload["packaging-25.0.dist-info/METADATA"]))


def test_exact_immutable_wheel_verifies_and_receipt_round_trips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel(tmp_path); _admit(monkeypatch, raw, payload)
    result = artifact.parse_pinned_packaging_250_wheel(raw)
    receipt = result.to_private_dict()
    assert receipt["decision"] == "PROPOSED_PACKAGING_ARTIFACT_BYTES_VERIFIED_DIAGNOSTIC"
    assert receipt["archive_members"] == receipt["record_rows"] == len(payload) + 1
    assert receipt["payload_files"] == len(payload)
    assert receipt["diagnostic_only"] is True
    assert receipt["official_metadata_observation_accepted"] is False
    assert receipt["pin_acceptance_authorized"] is False
    assert receipt["parser_import_authorized"] is False
    assert receipt["resolver_use_authorized"] is False
    assert artifact.parse_packaging_artifact_receipt(receipt) == receipt
    assert result.receipt["reason_codes"] == ()
    with pytest.raises(AttributeError):
        result.receipt["reason_codes"].append("tamper")  # type: ignore[union-attr]
    with pytest.raises(TypeError): pickle.dumps(result)
    assert not hasattr(artifact, "VerifiedPackagingArtifact")
    with pytest.raises(TypeError):
        artifact._VerifiedPackagingArtifact(payload={}, record={}, receipt={}, _token=object())


@pytest.mark.parametrize("value", [b"", b"wrong", bytearray(b"wrong")])
def test_wrong_or_mutable_bytes_fail_before_archive_parse(value: object, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(zipfile, "ZipFile", lambda *args, **kwargs: pytest.fail("archive parse reached"))
    with pytest.raises(artifact.PackagingArtifactError, match="WHEEL_PIN_MISMATCH"):
        artifact.parse_pinned_packaging_250_wheel(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "mutation",
    [
        "traversal", "case-duplicate", "dot-alias", "executable", "uppercase-executable",
        "unexpected-top-level", "missing-record", "missing-metadata", "missing-wheel",
        "record-hash", "record-size", "record-duplicate", "record-extra-row", "record-base64",
        "record-self-hash", "record-csv",
        "unexpected-dependency", "metadata-name", "metadata-python", "tag", "wheel-version",
        "wheel-purelib", "wheel-duplicate-tag",
    ],
)
def test_adversarial_wheel_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    raw, payload = _wheel(tmp_path, mutation); _admit(monkeypatch, raw, payload)
    with pytest.raises(artifact.PackagingArtifactError):
        artifact.parse_pinned_packaging_250_wheel(raw)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("unexpected-dependency", "UNEXPECTED_RUNTIME_DEPENDENCY"),
        ("metadata-name", "METADATA_IDENTITY_MISMATCH"),
        ("metadata-python", "METADATA_IDENTITY_MISMATCH"),
        ("tag", "WHEEL_TAG_MISMATCH"),
        ("wheel-version", "WHEEL_METADATA_MISMATCH"),
        ("wheel-purelib", "WHEEL_METADATA_MISMATCH"),
        ("wheel-duplicate-tag", "WHEEL_TAG_MISMATCH"),
    ],
)
def test_semantic_metadata_negatives_reach_the_intended_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str, reason: str
) -> None:
    raw, payload = _wheel(tmp_path, mutation); _admit(monkeypatch, raw, payload)
    with pytest.raises(artifact.PackagingArtifactError, match=reason):
        artifact.parse_pinned_packaging_250_wheel(raw)


@pytest.mark.parametrize("kind", ["directory", "symlink", "fifo", "unsupported-compression"])
def test_unsafe_zip_member_types_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    raw, payload = _wheel(tmp_path)
    source = tmp_path / "synthetic.whl"
    with zipfile.ZipFile(source, "r") as existing:
        rows = [(info.filename, existing.read(info)) for info in existing.infolist()]
    target = tmp_path / "unsafe.whl"
    with zipfile.ZipFile(target, "w") as wheel:
        for name, body in rows: wheel.writestr(name, body)
        info = zipfile.ZipInfo("packaging/unsafe/" if kind == "directory" else "packaging/unsafe.py")
        if kind == "symlink": info.external_attr = 0o120777 << 16
        elif kind == "fifo": info.external_attr = 0o010777 << 16
        elif kind == "unsupported-compression": info.compress_type = zipfile.ZIP_BZIP2
        wheel.writestr(info, b"x")
    changed = target.read_bytes(); _admit(monkeypatch, changed, payload)
    with pytest.raises(artifact.PackagingArtifactError): artifact.parse_pinned_packaging_250_wheel(changed)


def test_exact_duplicate_archive_name_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel(tmp_path)
    source = tmp_path / "synthetic.whl"
    with zipfile.ZipFile(source, "r") as existing:
        rows = [(info.filename, existing.read(info)) for info in existing.infolist()]
    target = tmp_path / "duplicate.whl"
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(target, "w") as wheel:
            for name, body in rows: wheel.writestr(name, body)
            wheel.writestr("packaging/__init__.py", b"duplicate")
    changed = target.read_bytes(); _admit(monkeypatch, changed, payload)
    with pytest.raises(artifact.PackagingArtifactError, match="UNSAFE_ARCHIVE_MEMBER"):
        artifact.parse_pinned_packaging_250_wheel(changed)


def test_corrupt_or_truncated_zip_and_bounds_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel(tmp_path)
    for changed in (raw[:32], raw[:-20]):
        _admit(monkeypatch, changed, payload)
        with pytest.raises(artifact.PackagingArtifactError, match="INVALID_WHEEL_ARCHIVE"):
            artifact.parse_pinned_packaging_250_wheel(changed)
    _admit(monkeypatch, raw, payload)
    monkeypatch.setattr(artifact, "_MAX_MEMBERS", 2)
    with pytest.raises(artifact.PackagingArtifactError, match="ARCHIVE_BOUNDS_EXCEEDED"):
        artifact.parse_pinned_packaging_250_wheel(raw)


def test_member_and_expanded_byte_bounds_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel(tmp_path); _admit(monkeypatch, raw, payload)
    monkeypatch.setattr(artifact, "_MAX_MEMBER_BYTES", 8)
    with pytest.raises(artifact.PackagingArtifactError): artifact.parse_pinned_packaging_250_wheel(raw)
    monkeypatch.setattr(artifact, "_MAX_MEMBER_BYTES", 1024 * 1024)
    monkeypatch.setattr(artifact, "_MAX_EXPANDED_BYTES", 8)
    with pytest.raises(artifact.PackagingArtifactError, match="ARCHIVE_BOUNDS_EXCEEDED"):
        artifact.parse_pinned_packaging_250_wheel(raw)


def test_record_bound_is_enforced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel(tmp_path); _admit(monkeypatch, raw, payload)
    monkeypatch.setattr(artifact, "_MAX_RECORD_BYTES", 8)
    with pytest.raises(artifact.PackagingArtifactError, match="RECORD_BOUNDS_EXCEEDED"):
        artifact.parse_pinned_packaging_250_wheel(raw)


def test_verifier_performs_no_path_io(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel(tmp_path); _admit(monkeypatch, raw, payload)
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: pytest.fail("path I/O attempted"))
    assert artifact.parse_pinned_packaging_250_wheel(raw).to_private_dict()["verifier_network_accessed"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("parser_import_authorized", True),
        ("resolver_use_authorized", True),
        ("persistent_receipt_is_capability", True),
        ("official_metadata_observation_accepted", True),
        ("pin_acceptance_authorized", True),
        ("verifier_artifact_downloaded", True),
        ("verifier_package_installed", True),
        ("receipt_sha256", "sha256:" + "0" * 64),
    ],
)
def test_receipt_authority_or_digest_tamper_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object) -> None:
    raw, payload = _wheel(tmp_path); _admit(monkeypatch, raw, payload)
    receipt = artifact.parse_pinned_packaging_250_wheel(raw).to_private_dict()
    receipt[field] = value
    with pytest.raises(ValueError): artifact.parse_packaging_artifact_receipt(receipt)


def test_schema_mirror_and_runtime_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    raw, payload = _wheel(tmp_path); _admit(monkeypatch, raw, payload)
    receipt = artifact.parse_pinned_packaging_250_wheel(raw).to_private_dict()
    schema_receipt = deepcopy(receipt)
    schema_receipt.update({
        "wheel_bytes": 66_469,
        "wheel_sha256": "sha256:29572ef2b1f17581046b3a2227d5c611fb25ec70ca1ba8554b24b0e69331a484",
        "metadata_sha256": "sha256:5b611a609c38fefc3d616bf45d20aec98fb7d53f245daca9e2c30fc85c7ac282",
    })
    body = {key: value for key, value in schema_receipt.items() if key != "receipt_sha256"}
    schema_receipt["receipt_sha256"] = artifact.sha256_bytes(
        b"TASK014_PACKAGING_ARTIFACT_RECEIPT_V1\0" + artifact.canonical_json_bytes(body)
    )
    assert not list(Draft202012Validator(schema).iter_errors(schema_receipt))
    for field in ("diagnostic_only", "parser_import_authorized", "resolver_use_authorized", "install_authorized"):
        changed = deepcopy(schema_receipt); changed[field] = not changed[field]
        assert list(Draft202012Validator(schema).iter_errors(changed))


@pytest.mark.parametrize(
    "field,value",
    [("archive_members", 257), ("record_rows", 257), ("payload_files", 256), ("expanded_bytes", 4_194_305)],
)
def test_receipt_parser_and_schema_reject_same_count_bounds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: int) -> None:
    raw, payload = _wheel(tmp_path); _admit(monkeypatch, raw, payload)
    receipt = artifact.parse_pinned_packaging_250_wheel(raw).to_private_dict()
    receipt[field] = value
    body = {key: item for key, item in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = artifact.sha256_bytes(
        b"TASK014_PACKAGING_ARTIFACT_RECEIPT_V1\0" + artifact.canonical_json_bytes(body)
    )
    with pytest.raises(ValueError): artifact.parse_packaging_artifact_receipt(receipt)
    schema_receipt = deepcopy(receipt)
    schema_receipt.update({
        "wheel_bytes": 66_469,
        "wheel_sha256": "sha256:29572ef2b1f17581046b3a2227d5c611fb25ec70ca1ba8554b24b0e69331a484",
        "metadata_sha256": "sha256:5b611a609c38fefc3d616bf45d20aec98fb7d53f245daca9e2c30fc85c7ac282",
    })
    assert list(Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).iter_errors(schema_receipt))


def test_static_surface_is_pure_and_does_not_claim_accepted_parser_use() -> None:
    source = (ROOT / "src/ai_video_production/packaging_parser_artifact.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imports.intersection({"os", "socket", "subprocess", "requests", "urllib", "importlib", "packaging"})
    assert "parser_import_authorized\": False" in source
    assert "resolver_use_authorized\": False" in source
