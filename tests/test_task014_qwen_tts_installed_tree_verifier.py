from __future__ import annotations

from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import zipfile

import pytest
from jsonschema import Draft202012Validator, ValidationError

import ai_video_production.qwen_tts_installed_tree_verifier as verifier


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "qwen-tts-installed-tree-verification.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name


def _positive() -> dict[str, object]:
    inventory = {"qwen_tts/__init__.py": ("sha256:" + "a" * 64, 1)}
    value = verifier._private_body(
        evaluated_at="2026-08-21T00:00:00Z", decision="QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE", reasons=(),
        wheel_path=Path("/private/wheel/qwen_tts-0.1.1-py3-none-any.whl"), runtime_root=Path("/private/runtime"),
        inventory=inventory, generated_digest="sha256:" + "b" * 64,
    )
    value["trusted_inventory_digest"] = verifier.TRUSTED_PAYLOAD_INVENTORY_SHA256
    value["receipt_sha256"] = verifier._digest(value, "receipt_sha256")
    return value


def _record_hash(value: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(value).digest()).decode("ascii").rstrip("=")


def _record(rows: dict[str, bytes], *, unhashed: set[str]) -> bytes:
    return "".join(f"{name},{'' if name in unhashed else _record_hash(value)},{'' if name in unhashed else len(value)}\n" for name, value in sorted(rows.items())).encode("utf-8")


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, dict[str, bytes]]:
    """A complete 24/23 wheel and 45-row installed tree; no target package is imported."""
    dist = verifier.DIST_INFO
    payload: dict[str, bytes] = {"qwen_tts/__init__.py": b"", "qwen_tts/cli/__init__.py": b"", "qwen_tts/cli/demo.py": b"def main(): pass\n"}
    payload.update({f"qwen_tts/module_{index}.py": f"# {index}\n".encode() for index in range(14)})
    payload.update({
        f"{dist}/METADATA": b"Metadata-Version: 2.1\nName: qwen-tts\nVersion: 0.1.1\n",
        f"{dist}/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
        f"{dist}/entry_points.txt": b"[console_scripts]\nqwen-tts-demo = qwen_tts.cli.demo:main\n",
        f"{dist}/top_level.txt": b"qwen_tts\n",
        f"{dist}/LICENSE": b"synthetic\n",
        f"{dist}/AUTHORS": b"synthetic\n",
        f"{dist}/RECORD": b"",  # replaced below after the other 23 rows are fixed
    })
    assert len(payload) == 24 and sum(name.endswith(".py") for name in payload) == 17
    payload[f"{dist}/RECORD"] = _record(payload, unhashed={f"{dist}/RECORD"})
    wheel = tmp_path / verifier.WHEEL_FILENAME
    with zipfile.ZipFile(wheel, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, body in payload.items(): archive.writestr(name, body)
    monkeypatch.setattr(verifier, "WHEEL_BYTES", wheel.stat().st_size)
    monkeypatch.setattr(verifier, "WHEEL_SHA256", "sha256:" + hashlib.sha256(wheel.read_bytes()).hexdigest())
    trusted = {name: ("sha256:" + hashlib.sha256(body).hexdigest(), len(body)) for name, body in payload.items() if name != f"{dist}/RECORD"}
    monkeypatch.setattr(verifier, "TRUSTED_PAYLOAD_INVENTORY_SHA256", verifier._sha(verifier.canonical_json_bytes(trusted)))
    runtime = tmp_path / "runtime"; site = runtime / "Lib" / "site-packages"
    for name, body in payload.items():
        destination = site / name; destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(body)
    generated = {
        "../../Scripts/qwen-tts-demo.exe": b"MZ synthetic launcher",
        f"{dist}/INSTALLER": b"pip\n", f"{dist}/REQUESTED": b"",
        f"{dist}/direct_url.json": json.dumps({"archive_info": {"hash": "sha256=" + verifier.WHEEL_SHA256.removeprefix("sha256:"), "hashes": {"sha256": verifier.WHEEL_SHA256.removeprefix("sha256:")}}, "url": "file:///private/qwen_tts-0.1.1-py3-none-any.whl"}, separators=(",", ":")).encode("utf-8"),
    }
    for name, body in generated.items():
        destination = runtime / "Scripts" / "qwen-tts-demo.exe" if name.startswith("../") else site / name
        destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(body)
    cache: dict[str, bytes] = {}
    for name in payload:
        if name.endswith(".py"):
            cache_name = verifier._cache_path(name); cache[cache_name] = b"PYC:" + name.encode("ascii")
            destination = site / cache_name; destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(cache[cache_name])
    installed_rows = dict(payload) | generated | cache
    (site / dist / "RECORD").write_bytes(_record(installed_rows, unhashed={f"{dist}/RECORD", *cache}))
    return wheel, runtime, generated


def _rewrite_installed_record(runtime: Path) -> None:
    """Rebind the synthetic installed RECORD after an intentional body edit."""
    site = runtime / "Lib" / "site-packages"
    rows = {
        path.relative_to(site).as_posix(): path.read_bytes()
        for path in site.rglob("*")
        if path.is_file()
    }
    rows["../../Scripts/qwen-tts-demo.exe"] = (runtime / "Scripts" / "qwen-tts-demo.exe").read_bytes()
    cache = {name for name in rows if "/__pycache__/" in name}
    record_name = f"{verifier.DIST_INFO}/RECORD"
    (site / record_name).write_bytes(_record(rows, unhashed={record_name, *cache}))


def test_private_success_is_bounded_and_does_not_authorize_runtime_reuse() -> None:
    result = verifier.parse_qwen_tts_011_installed_tree_verification(_positive()).to_private_dict()
    assert result["decision"] == "QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE"
    assert (result["wheel_record_rows"], result["trusted_payload_files"], result["installed_record_rows"]) == (24, 23, 45)
    assert (result["pip_generated_files"], result["generated_cache_files"], result["untrusted_generated_rows"]) == (4, 17, 21)
    assert result["runtime_reuse_authorized"] is False


@pytest.mark.parametrize("field, value", [("runtime_reuse_authorized", True), ("target_package_imported", True), ("direct_url_redacted", False), ("wheel_member_count", 25)])
def test_parser_rejects_authority_or_success_coordinate_tamper(field: str, value: object) -> None:
    payload = _positive(); payload[field] = value
    with pytest.raises(ValueError):
        verifier.parse_qwen_tts_011_installed_tree_verification(payload)


def test_parser_rejects_receipt_tamper_and_unknown_fields() -> None:
    payload = _positive(); payload["receipt_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="receipt_sha256"):
        verifier.parse_qwen_tts_011_installed_tree_verification(payload)
    payload = _positive(); payload["direct_url"] = "must never persist"
    with pytest.raises(ValueError, match="unknown"):
        verifier.parse_qwen_tts_011_installed_tree_verification(payload)


def test_public_projection_redacts_private_path_and_observation_fingerprints() -> None:
    public = verifier.parse_qwen_tts_011_installed_tree_verification(_positive()).to_public_dict()
    rendered = json.dumps(public, sort_keys=True)
    assert "fingerprint" not in rendered and "observation_digest" not in rendered and "receipt_sha256" not in rendered
    assert public["direct_url_redacted"] is True


def test_unsafe_relative_roots_are_rejected_before_any_file_io() -> None:
    result = verifier.verify_qwen_tts_011_installed_tree(Path("relative.whl"), Path("relative-runtime"), "2026-08-21T00:00:00Z")
    assert result.to_private_dict()["decision"] == "BLOCKED"
    assert result.to_private_dict()["reason_codes"] == ["UNSAFE_RUNTIME_ROOT"]


def test_wrong_wheel_pin_stops_before_runtime_enumeration(tmp_path: Path) -> None:
    wheel = tmp_path / verifier.WHEEL_FILENAME
    wheel.write_bytes(b"not the pinned wheel")
    result = verifier.verify_qwen_tts_011_installed_tree(wheel, tmp_path / "missing-runtime", "2026-08-21T00:00:00Z")
    assert result.to_private_dict()["decision"] == "BLOCKED"
    assert result.to_private_dict()["reason_codes"] == ["WHEEL_PIN_MISMATCH"]


def test_complete_synthetic_tree_is_verified_but_never_authorizes_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wheel, runtime, _ = _fixture(tmp_path, monkeypatch)
    receipt = verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z").to_private_dict()
    assert receipt["decision"] == "QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE"
    assert receipt["runtime_reuse_authorized"] is False
    assert receipt["trusted_payload_files"] == 23 and receipt["pip_generated_files"] == 4 and receipt["generated_cache_files"] == 17


@pytest.mark.parametrize("generated_name", ["../../Scripts/qwen-tts-demo.exe", f"{verifier.DIST_INFO}/INSTALLER", f"{verifier.DIST_INFO}/REQUESTED", f"{verifier.DIST_INFO}/direct_url.json"])
def test_generated_body_change_with_stale_record_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, generated_name: str) -> None:
    wheel, runtime, _ = _fixture(tmp_path, monkeypatch)
    target = runtime / "Scripts" / "qwen-tts-demo.exe" if generated_name.startswith("../") else runtime / "Lib" / "site-packages" / generated_name
    target.write_bytes(target.read_bytes() + b"changed")
    assert verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z").to_private_dict()["decision"] == "BLOCKED"


def test_rehashed_generated_observation_stays_untrusted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wheel, runtime, _ = _fixture(tmp_path, monkeypatch)
    before = verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z").to_private_dict()
    site = runtime / "Lib" / "site-packages"; name = f"{verifier.DIST_INFO}/INSTALLER"; (site / name).write_bytes(b"other-pip\n")
    rows: dict[str, bytes] = {}
    for path in site.rglob("*"):
        if path.is_file(): rows[path.relative_to(site).as_posix()] = path.read_bytes()
    rows["../../Scripts/qwen-tts-demo.exe"] = (runtime / "Scripts" / "qwen-tts-demo.exe").read_bytes()
    cache = {name for name in rows if "/__pycache__/" in name}
    (site / verifier.DIST_INFO / "RECORD").write_bytes(_record(rows, unhashed={f"{verifier.DIST_INFO}/RECORD", *cache}))
    after = verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z").to_private_dict()
    assert after["decision"] == "QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE"
    assert after["trusted_inventory_digest"] == before["trusted_inventory_digest"]
    assert after["untrusted_generated_observation_digest"] != before["untrusted_generated_observation_digest"]


@pytest.mark.parametrize("target", ["qwen_tts/module_0.py", f"{verifier.DIST_INFO}/RECORD", f"{verifier.DIST_INFO}/entry_points.txt"])
def test_distribution_owned_body_tamper_is_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    wheel, runtime, _ = _fixture(tmp_path, monkeypatch)
    path = runtime / "Lib" / "site-packages" / target
    path.write_bytes(path.read_bytes() + b"tamper")
    assert verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z").to_private_dict()["decision"] == "BLOCKED"


def test_pyc_change_is_untrusted_observation_not_runtime_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wheel, runtime, _ = _fixture(tmp_path, monkeypatch)
    before = verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z").to_private_dict()
    cache = runtime / "Lib" / "site-packages" / "qwen_tts" / "__pycache__" / "module_0.cpython-312.pyc"
    cache.write_bytes(cache.read_bytes() + b"different-untrusted-bytecode")
    after = verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z").to_private_dict()
    assert after["decision"] == "QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE"
    assert after["untrusted_generated_observation_digest"] != before["untrusted_generated_observation_digest"]
    for field in ("authoritative_runtime_gate", "immutable_snapshot_verified", "locked_handles_held_through_consumer", "runtime_reuse_authorized"):
        assert after[field] is False


def test_post_terminal_read_swap_is_only_a_mutable_point_in_time_observation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wheel, runtime, _ = _fixture(tmp_path, monkeypatch)
    target = runtime / "Lib" / "site-packages" / "qwen_tts" / "module_0.py"
    original_stream = verifier._stream_file
    reads = 0

    def late_swap(path: Path, *, maximum: int = verifier.MAX_EXPANDED_BYTES) -> tuple[str, int]:
        nonlocal reads
        result = original_stream(path, maximum=maximum)
        if path == target:
            reads += 1
            if reads == 2:  # immediately after the terminal trusted-body read
                target.write_bytes(target.read_bytes() + b"late-after-terminal-read")
        return result

    monkeypatch.setattr(verifier, "_stream_file", late_swap)
    first = verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z").to_private_dict()
    assert first["decision"] == "QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE"
    assert first["tree_mutability"] == "MUTABLE_UNLOCKED"
    for field in ("post_return_state_guaranteed", "authoritative_runtime_gate", "immutable_snapshot_verified", "locked_handles_held_through_consumer", "runtime_reuse_authorized"):
        assert first[field] is False
    assert first["consumer_revalidation_required"] is True
    monkeypatch.setattr(verifier, "_stream_file", original_stream)
    second = verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z").to_private_dict()
    assert second["decision"] == "BLOCKED"


@pytest.mark.parametrize("url", [
    "file:///private/qwen_tts-0.1.1-py3-none-any.whl?q=1",
    "file:///private/qwen_tts-0.1.1-py3-none-any.whl#fragment",
    "file://host/private/qwen_tts-0.1.1-py3-none-any.whl",
])
def test_direct_url_private_shape_rejects_route_leakage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    wheel, runtime, _ = _fixture(tmp_path, monkeypatch)
    direct = runtime / "Lib" / "site-packages" / verifier.DIST_INFO / "direct_url.json"
    raw = json.loads(direct.read_text(encoding="utf-8")); raw["url"] = url
    direct.write_text(json.dumps(raw), encoding="utf-8")
    _rewrite_installed_record(runtime)
    receipt = verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z")
    private = receipt.to_private_dict()
    assert private["decision"] == "BLOCKED"
    assert private["reason_codes"] == ["DIRECT_URL_JSON_INVALID"]
    serialized = json.dumps(private) + json.dumps(receipt.to_public_dict())
    assert url not in serialized and "file://" not in serialized


@pytest.mark.parametrize("kind", ["duplicate", "nonfinite"])
def test_direct_url_json_parser_is_reached_and_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    wheel, runtime, _ = _fixture(tmp_path, monkeypatch)
    direct = runtime / "Lib" / "site-packages" / verifier.DIST_INFO / "direct_url.json"
    bare = verifier.WHEEL_SHA256.removeprefix("sha256:")
    if kind == "duplicate":
        body = (f'{{"archive_info":{{"hash":"sha256={bare}","hashes":{{"sha256":"{bare}"}}}},'
                '"url":"file:///private/qwen_tts-0.1.1-py3-none-any.whl",'
                '"url":"file:///private/qwen_tts-0.1.1-py3-none-any.whl"}').encode("utf-8")
    else:
        body = b'{"archive_info":NaN,"url":"file:///private/qwen_tts-0.1.1-py3-none-any.whl"}'
    direct.write_bytes(body)
    _rewrite_installed_record(runtime)
    receipt = verifier.verify_qwen_tts_011_installed_tree(wheel, runtime, "2026-08-21T00:00:00Z")
    assert receipt.to_private_dict()["reason_codes"] == ["DIRECT_URL_JSON_INVALID"]
    assert "file://" not in json.dumps(receipt.to_private_dict()) + json.dumps(receipt.to_public_dict())


def test_record_parser_rejects_zip_slip_and_malformed_generated_record() -> None:
    with pytest.raises(verifier._Blocked):
        verifier._parse_record(b"../escape,sha256=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,1\n", wheel=True)
    with pytest.raises(verifier._Blocked):
        verifier._parse_record(b"qwen_tts/a.py,sha256=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,\n", wheel=True)
    with pytest.raises(verifier._Blocked):
        verifier._parse_record(b"../../Scripts/not-qwen.exe,sha256=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,1\n", wheel=False)


def test_schema_is_draft_2020_12_byte_exact_and_fail_closed() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8")); Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(_positive())
    invalid = deepcopy(_positive()); invalid["target_python_executed"] = True
    with pytest.raises(ValidationError): validator.validate(invalid)

    for field in ("tree_mutability", "post_return_state_guaranteed", "authoritative_runtime_gate", "immutable_snapshot_verified", "locked_handles_held_through_consumer", "consumer_revalidation_required"):
        missing = deepcopy(_positive()); del missing[field]
        with pytest.raises(ValidationError): validator.validate(missing)

    blocked = verifier._private_body(evaluated_at="2026-08-21T00:00:00Z", decision="BLOCKED", reasons=("WHEEL_PIN_MISMATCH",), wheel_path=Path("/w"), runtime_root=Path("/r"))
    blocked["receipt_sha256"] = verifier._digest(blocked, "receipt_sha256")
    unknown = verifier._private_body(evaluated_at="2026-08-21T00:00:00Z", decision="UNKNOWN", reasons=("IO_UNAVAILABLE",), wheel_path=Path("/w"), runtime_root=Path("/r"))
    unknown["receipt_sha256"] = verifier._digest(unknown, "receipt_sha256")
    validator.validate(blocked); validator.validate(unknown)

    invalid_failures = []
    bad = deepcopy(blocked); bad["reason_codes"] = ["IO_UNAVAILABLE"]; invalid_failures.append(bad)
    bad = deepcopy(unknown); bad["reason_codes"] = ["WHEEL_PIN_MISMATCH"]; invalid_failures.append(bad)
    bad = deepcopy(blocked); bad["reason_codes"] = []; invalid_failures.append(bad)
    bad = deepcopy(unknown); bad["reason_codes"] = ["IO_UNAVAILABLE", "IO_UNAVAILABLE"]; invalid_failures.append(bad)
    bad = deepcopy(blocked); bad["wheel_member_count"] = 24; bad["archive_enumerated"] = True; bad["trusted_inventory_digest"] = verifier.TRUSTED_PAYLOAD_INVENTORY_SHA256; invalid_failures.append(bad)
    for payload in invalid_failures:
        payload["receipt_sha256"] = verifier._digest(payload, "receipt_sha256")
        with pytest.raises(ValidationError): validator.validate(payload)
        with pytest.raises(ValueError): verifier.parse_qwen_tts_011_installed_tree_verification(payload)


def test_private_projection_is_deep_copy_and_closed_reason_vocabulary_is_strict() -> None:
    receipt = verifier.parse_qwen_tts_011_installed_tree_verification(_positive())
    exported = receipt.to_private_dict(); exported["reason_codes"].append("IO_UNAVAILABLE")
    assert receipt.to_private_dict()["reason_codes"] == []
    blocked = verifier._private_body(evaluated_at="2026-08-21T00:00:00Z", decision="BLOCKED", reasons=("WHEEL_PIN_MISMATCH",), wheel_path=Path("/w"), runtime_root=Path("/r"))
    blocked["receipt_sha256"] = verifier._digest(blocked, "receipt_sha256")
    assert verifier.parse_qwen_tts_011_installed_tree_verification(blocked).to_private_dict()["decision"] == "BLOCKED"
    blocked["reason_codes"] = ["NOT_A_REASON"]; blocked["receipt_sha256"] = verifier._digest(blocked, "receipt_sha256")
    with pytest.raises(ValueError, match="decision or reasons"):
        verifier.parse_qwen_tts_011_installed_tree_verification(blocked)


@pytest.mark.parametrize("field, value", [("authoritative_runtime_gate", True), ("immutable_snapshot_verified", True), ("locked_handles_held_through_consumer", True), ("post_return_state_guaranteed", True), ("consumer_revalidation_required", False)])
def test_observation_receipt_rejects_authority_or_guarantee_tamper(field: str, value: object) -> None:
    payload = _positive(); payload[field] = value; payload["receipt_sha256"] = verifier._digest(payload, "receipt_sha256")
    with pytest.raises(ValueError):
        verifier.parse_qwen_tts_011_installed_tree_verification(payload)


@pytest.mark.parametrize("timestamp", ["20260821T000000Z", "2026-08-21 00:00:00Z", "2026-08-21T00:00Z", "2026-08-21T00:00:00+00:00"])
def test_timestamp_is_canonical_utc_only(timestamp: str) -> None:
    value = _positive(); value["evaluated_at"] = timestamp; value["receipt_sha256"] = verifier._digest(value, "receipt_sha256")
    with pytest.raises(ValueError, match="RFC3339 UTC"):
        verifier.parse_qwen_tts_011_installed_tree_verification(value)
