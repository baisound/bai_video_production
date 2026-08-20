from __future__ import annotations

from copy import deepcopy
import base64
import hashlib
import inspect
import json
import pickle
from pathlib import Path
import zipfile

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ai_video_production import qwen_tts_locked_wheel_session as locked
from ai_video_production import qwen_tts_pinned_wheel as pinned


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "qwen-tts-locked-wheel-session-observation.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name


def _record_hash(body: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode("ascii").rstrip("=")


def _payload() -> dict[str, bytes]:
    value = {"qwen_tts/__init__.py": b"", "qwen_tts/cli/__init__.py": b"", "qwen_tts/cli/demo.py": b"def main(): pass\n"}
    value.update({f"qwen_tts/module_{index}.py": f"# {index}\n".encode() for index in range(14)})
    value.update({
        "qwen_tts-0.1.1.dist-info/METADATA": b"Metadata-Version: 2.1\nName: qwen-tts\nVersion: 0.1.1\n",
        "qwen_tts-0.1.1.dist-info/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
        "qwen_tts-0.1.1.dist-info/entry_points.txt": b"[console_scripts]\nqwen-tts-demo = qwen_tts.cli.demo:main\n",
        "qwen_tts-0.1.1.dist-info/top_level.txt": b"qwen_tts\n",
        "qwen_tts-0.1.1.dist-info/LICENSE": b"synthetic\n",
        "qwen_tts-0.1.1.dist-info/AUTHORS": b"synthetic\n",
    })
    assert len(value) == 23
    return value


def _wheel_bytes(tmp_path: Path, *, record_name: str = "qwen_tts-0.1.1.dist-info/RECORD", extra: tuple[str, bytes] | None = None) -> tuple[bytes, dict[str, bytes]]:
    payload = _payload(); rows = dict(payload); rows[record_name] = b""
    rows[record_name] = "".join(
        f"{name},{'' if name == record_name else _record_hash(body)},{'' if name == record_name else len(body)}\n"
        for name, body in sorted(rows.items())
    ).encode("utf-8")
    if extra is not None: rows[extra[0]] = extra[1]
    path = tmp_path / "synthetic.whl"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, body in rows.items(): archive.writestr(name, body)
    return path.read_bytes(), payload


def _admit(monkeypatch: pytest.MonkeyPatch, raw: bytes, payload: dict[str, bytes]) -> None:
    inventory = {name: ("sha256:" + hashlib.sha256(body).hexdigest(), len(body)) for name, body in payload.items()}
    monkeypatch.setattr(pinned, "_WHEEL_BYTES", len(raw))
    monkeypatch.setattr(pinned, "_WHEEL_SHA256", "sha256:" + hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(pinned, "_TRUSTED_PAYLOAD_INVENTORY_SHA256", pinned.sha256_bytes(pinned.canonical_json_bytes(inventory)))


class FakePort:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw; self.events: list[tuple[object, ...]] = []; self.next_handle = 1
        self.paths: dict[int, tuple[str, bool]] = {}; self.identity_calls: dict[int, int] = {}
        self.drive = locked._DRIVE_FIXED; self.fail_open_number: int | None = None
        self.swap_handle: int | None = None; self.identity_failure: str | None = None
        self.close_failure_handle: int | None = None; self.read_calls = 0

    def drive_type(self, root: str) -> int:
        self.events.append(("drive", root)); return self.drive

    def _open(self, kind: str, path: str) -> int:
        handle = self.next_handle; self.next_handle += 1
        if self.fail_open_number == handle: raise locked._Win32Blocked("HANDLE_OPEN_DENIED")
        self.paths[handle] = (path, kind == "directory"); self.events.append(("open", kind, path, handle)); return handle

    def open_directory(self, path: str) -> int: return self._open("directory", path)
    def open_wheel(self, path: str) -> int: return self._open("wheel", path)

    def identity(self, handle: int, expected_path: str, *, directory: bool) -> locked._HandleIdentity:
        if self.identity_failure is not None: raise locked._Win32Blocked(self.identity_failure)
        self.identity_calls[handle] = self.identity_calls.get(handle, 0) + 1
        suffix = 1 if handle == self.swap_handle and self.identity_calls[handle] > 1 else 0
        self.events.append(("identity", handle, expected_path, directory))
        return locked._HandleIdentity(expected_path, 700, bytes([handle + suffix]) * 16, directory)

    def read_exact(self, handle: int, byte_count: int) -> bytes:
        self.read_calls += 1; self.events.append(("read", handle, byte_count)); return self.raw

    def close(self, handle: int) -> bool:
        self.events.append(("close", handle)); return handle != self.close_failure_handle


class _NativeFaultKernel:
    def __init__(self, retry_close_succeeds: bool, *, readback_unsafe: bool = False) -> None:
        self.retry_close_succeeds = retry_close_succeeds
        self.readback_unsafe = readback_unsafe
        self.close_calls: list[int] = []
        self.get_handle_information_calls = 0

    def CreateFileW(self, *args: object) -> int: return 77
    def SetHandleInformation(self, *args: object) -> bool: return self.readback_unsafe
    def GetHandleInformation(self, handle: int, flags: object) -> bool:
        self.get_handle_information_calls += 1
        flags._obj.value = locked._HANDLE_FLAG_INHERIT  # type: ignore[attr-defined]
        return True
    def CloseHandle(self, handle: int) -> bool:
        self.close_calls.append(int(handle))
        return len(self.close_calls) > 1 and self.retry_close_succeeds


class _NativeInheritanceFaultPort:
    def __init__(self, retry_close_succeeds: bool, *, readback_unsafe: bool = False) -> None:
        self.kernel = _NativeFaultKernel(retry_close_succeeds, readback_unsafe=readback_unsafe)
        self.native = object.__new__(locked._CtypesWin32Port)
        self.native._kernel = self.kernel

    def drive_type(self, root: str) -> int: return locked._DRIVE_FIXED
    def open_directory(self, path: str) -> int: return self.native.open_directory(path)
    def open_wheel(self, path: str) -> int: raise AssertionError("wheel open must not be reached")
    def identity(self, handle: int, expected_path: str, *, directory: bool) -> locked._HandleIdentity:
        raise AssertionError("identity must not be reached")
    def read_exact(self, handle: int, byte_count: int) -> bytes: raise AssertionError("read must not be reached")
    def close(self, handle: int) -> bool: return bool(self.kernel.CloseHandle(handle))


def _success_receipt() -> dict[str, object]:
    body = locked._private_body(
        evaluated_at="2026-08-21T00:00:00Z", decision="LOCKED_SOURCE_VERIFIED_DIAGNOSTIC", reasons=(),
        directory_handles_opened=4, wheel_handle_opened=True, wheel_bytes_read=locked._WHEEL_BYTES,
        pinned_payload_files=23, source_fully_verified=True,
    )
    body["receipt_sha256"] = locked._digest(body, "receipt_sha256")
    return body


def test_pure_parser_accepts_exact_24_23_and_has_no_path_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel_bytes(tmp_path); _admit(monkeypatch, raw, payload)
    result = pinned.parse_pinned_qwen_tts_011_wheel(raw)
    assert len(result.record) == 24 and len(result.payload) == 23
    assert "qwen_tts-0.1.1.dist-info/RECORD" not in result.payload
    source = (ROOT / "src" / "ai_video_production" / "qwen_tts_pinned_wheel.py").read_text(encoding="utf-8")
    for forbidden in ("from pathlib import Path", ".lstat(", "path.open(", "os."):
        assert forbidden not in source


@pytest.mark.parametrize("value", [bytearray(b"x"), b"", b"wrong"])
def test_pure_parser_rejects_nonimmutable_or_wrong_pin(value: object) -> None:
    with pytest.raises(pinned.PinnedWheelError, match="WHEEL_PIN_MISMATCH"):
        pinned.parse_pinned_qwen_tts_011_wheel(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("mutation", ["traversal", "case-duplicate", "record-body", "entry-point"])
def test_pure_parser_rejects_adversarial_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    raw, payload = _wheel_bytes(tmp_path)
    wheel_path = tmp_path / "mutated.whl"
    with zipfile.ZipFile(Path(tmp_path / "source.whl"), "w") as unused: pass
    source = tmp_path / "synthetic.whl"
    with zipfile.ZipFile(source, "r") as archive: members = [(info.filename, archive.read(info)) for info in archive.infolist()]
    if mutation == "traversal": members.append(("../escape.py", b"x"))
    elif mutation == "case-duplicate": members.append(("QWEN_TTS/__init__.py", b""))
    elif mutation == "record-body":
        members = [(name, body + b"tamper" if name.endswith("/RECORD") else body) for name, body in members]
    else:
        members = [(name, b"wrong\n" if name.endswith("entry_points.txt") else body) for name, body in members]
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, body in members: archive.writestr(name, body)
    changed = wheel_path.read_bytes(); _admit(monkeypatch, changed, payload)
    with pytest.raises(pinned.PinnedWheelError): pinned.parse_pinned_qwen_tts_011_wheel(changed)


def test_session_opens_top_down_rechecks_identity_allows_second_read_and_closes_reverse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel_bytes(tmp_path); _admit(monkeypatch, raw, payload)
    port = FakePort(raw); monkeypatch.setattr(locked, "_WIN32_PORT_FACTORY", lambda: port)
    session = locked.open_locked_qwen_tts_wheel_session("2026-08-21T00:00:00Z")
    with session as active:
        active_receipt = active.receipt.to_private_dict()
        assert active.active and active_receipt["decision"] == "LOCKED_SOURCE_VERIFIED_DIAGNOSTIC"
        assert active_receipt["unreleased_handle_count"] == 5 and active_receipt["handle_release_confirmed"] is False
        assert len(active.read_verified_wheel().payload) == 23 and port.read_calls == 2
        with pytest.raises(TypeError): pickle.dumps(active)
    opens = [event for event in port.events if event[0] == "open"]
    assert [event[1] for event in opens] == ["directory"] * 4 + ["wheel"]
    assert [event[2] for event in opens] == ["E:\\", "E:\\BAI_AI", "E:\\BAI_AI\\downloads", "E:\\BAI_AI\\downloads\\TASK-014", "E:\\BAI_AI\\downloads\\TASK-014\\qwen_tts-0.1.1-py3-none-any.whl"]
    assert [event[1] for event in port.events if event[0] == "close"] == [5, 4, 3, 2, 1]
    assert session.active is False
    assert session.receipt.to_private_dict()["unreleased_handle_count"] == 0
    assert session.receipt.to_private_dict()["handle_release_confirmed"] is True
    with pytest.raises(RuntimeError, match="inactive"): session.read_verified_wheel()
    assert list(inspect.signature(locked.open_locked_qwen_tts_wheel_session).parameters) == ["evaluated_at"]


@pytest.mark.parametrize("reason", ["REPARSE_POINT_REJECTED", "CANONICAL_PATH_MISMATCH", "FILE_ID_INVALID"])
def test_identity_failures_block_and_close_every_open_handle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reason: str) -> None:
    raw, payload = _wheel_bytes(tmp_path); _admit(monkeypatch, raw, payload)
    port = FakePort(raw); port.identity_failure = reason; monkeypatch.setattr(locked, "_WIN32_PORT_FACTORY", lambda: port)
    with locked.open_locked_qwen_tts_wheel_session("2026-08-21T00:00:00Z") as session:
        assert session.receipt.to_private_dict()["reason_codes"] == [reason] and not session.active
    assert [event[1] for event in port.events if event[0] == "close"] == [1]


def test_remote_drive_and_preexisting_writer_open_fail_before_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel_bytes(tmp_path); _admit(monkeypatch, raw, payload)
    remote = FakePort(raw); remote.drive = 4; monkeypatch.setattr(locked, "_WIN32_PORT_FACTORY", lambda: remote)
    with locked.open_locked_qwen_tts_wheel_session("2026-08-21T00:00:00Z") as session:
        assert session.receipt.to_private_dict()["reason_codes"] == ["NON_FIXED_LOCAL_DRIVE"]
    writer = FakePort(raw); writer.fail_open_number = 5; monkeypatch.setattr(locked, "_WIN32_PORT_FACTORY", lambda: writer)
    with locked.open_locked_qwen_tts_wheel_session("2026-08-21T00:00:00Z") as session:
        assert session.receipt.to_private_dict()["reason_codes"] == ["HANDLE_OPEN_DENIED"] and writer.read_calls == 0
    assert [event[1] for event in writer.events if event[0] == "close"] == [4, 3, 2, 1]


def test_directory_or_wheel_identity_swap_blocks_and_closes_reverse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel_bytes(tmp_path); _admit(monkeypatch, raw, payload)
    for handle in (2, 5):
        port = FakePort(raw); port.swap_handle = handle; monkeypatch.setattr(locked, "_WIN32_PORT_FACTORY", lambda port=port: port)
        with locked.open_locked_qwen_tts_wheel_session("2026-08-21T00:00:00Z") as session:
            assert session.receipt.to_private_dict()["reason_codes"] == ["HANDLE_IDENTITY_CHANGED"]
        assert [event[1] for event in port.events if event[0] == "close"] == [5, 4, 3, 2, 1]


def test_close_failure_invalidates_capability_and_replaces_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel_bytes(tmp_path); _admit(monkeypatch, raw, payload)
    port = FakePort(raw); port.close_failure_handle = 3; monkeypatch.setattr(locked, "_WIN32_PORT_FACTORY", lambda: port)
    session = locked.open_locked_qwen_tts_wheel_session("2026-08-21T00:00:00Z")
    with session: assert session.active
    closed = session.receipt.to_private_dict()
    assert not session.active and closed["reason_codes"] == ["HANDLE_CLOSE_FAILED"]
    assert closed["unreleased_handle_count"] == 1 and closed["handle_release_confirmed"] is False


@pytest.mark.parametrize("retry_succeeds, reason", [(True, "HANDLE_INHERITANCE_UNSAFE"), (False, "HANDLE_CLOSE_FAILED")])
def test_native_noninherit_close_fault_registers_handle_and_retries_without_leak(
    monkeypatch: pytest.MonkeyPatch, retry_succeeds: bool, reason: str,
) -> None:
    port = _NativeInheritanceFaultPort(retry_succeeds)
    monkeypatch.setattr(locked, "_WIN32_PORT_FACTORY", lambda: port)
    with locked.open_locked_qwen_tts_wheel_session("2026-08-21T00:00:00Z") as session:
        private = session.receipt.to_private_dict()
        assert private["decision"] == "BLOCKED" and private["reason_codes"] == [reason]
        assert private["directory_handles_opened"] == 1
        assert private["unreleased_handle_count"] == (0 if retry_succeeds else 1)
        assert private["handle_release_confirmed"] is retry_succeeds
        rendered = json.dumps(private) + json.dumps(session.receipt.to_public_dict())
        assert "77" not in rendered and not session.active
    assert port.kernel.close_calls == ([77, 77] if retry_succeeds else [77, 77, 77, 77])


def test_native_noninherit_readback_rejects_inheritable_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    port = _NativeInheritanceFaultPort(True, readback_unsafe=True)
    monkeypatch.setattr(locked, "_WIN32_PORT_FACTORY", lambda: port)
    with locked.open_locked_qwen_tts_wheel_session("2026-08-21T00:00:00Z") as session:
        private = session.receipt.to_private_dict()
        assert private["reason_codes"] == ["HANDLE_INHERITANCE_UNSAFE"]
        assert private["directory_handles_opened"] == 1 and private["handle_release_confirmed"] is True
    assert port.kernel.get_handle_information_calls == 1 and port.kernel.close_calls == [77, 77]


def test_late_ancestor_swap_invalidates_live_capability_and_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _wheel_bytes(tmp_path); _admit(monkeypatch, raw, payload)
    port = FakePort(raw); monkeypatch.setattr(locked, "_WIN32_PORT_FACTORY", lambda: port)
    with locked.open_locked_qwen_tts_wheel_session("2026-08-21T00:00:00Z") as session:
        assert session.active
        port.swap_handle = 2
        with pytest.raises(RuntimeError, match="blocked"): session.read_verified_wheel()
        assert not session.active and session.receipt.to_private_dict()["reason_codes"] == ["HANDLE_IDENTITY_CHANGED"]
        assert [event[1] for event in port.events if event[0] == "close"] == [5, 4, 3, 2, 1]


def test_native_adapter_masks_forbid_write_delete_rename_sharing() -> None:
    source = (ROOT / "src" / "ai_video_production" / "qwen_tts_locked_wheel_session.py").read_text(encoding="utf-8")
    assert "_FILE_SHARE_READ | _FILE_SHARE_WRITE" in source
    assert "self._open(path, _GENERIC_READ, _FILE_SHARE_READ," in source
    assert "_FILE_SHARE_DELETE" not in source and "_GENERIC_WRITE" not in source


def test_receipt_schema_privacy_no_effect_and_tamper_rejection() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8")); Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema); value = _success_receipt(); validator.validate(value)
    receipt = locked.parse_locked_wheel_session_receipt(value)
    rendered = json.dumps(receipt.to_private_dict()) + json.dumps(receipt.to_public_dict())
    for forbidden in ("E:\\", "BAI_AI", '"file_id":', '"handle_id":', '"volume_serial":', '"canonical_path":', "SID", "SDDL"):
        assert forbidden not in rendered
    for field in ("persistent_receipt_is_capability", "runtime_reuse_authorized", "post_return_state_guaranteed", "consumer_execution_authorized", "target_python_executed", "target_package_imported", "model_loaded", "owner_audio_read", "inference_executed", "network_accessed", "subprocess_started", "archive_extracted", "filesystem_modified"):
        assert receipt.to_private_dict()[field] is False
    bad = deepcopy(value); bad["runtime_reuse_authorized"] = True; bad["receipt_sha256"] = locked._digest(bad, "receipt_sha256")
    with pytest.raises((ValidationError, ValueError)):
        validator.validate(bad); locked.parse_locked_wheel_session_receipt(bad)
    for decision, reason in (("BLOCKED", "HANDLE_OPEN_DENIED"), ("UNKNOWN", "WIN32_IO_UNAVAILABLE")):
        failure = locked._private_body(evaluated_at="2026-08-21T00:00:00Z", decision=decision, reasons=(reason,))
        failure["receipt_sha256"] = locked._digest(failure, "receipt_sha256")
        validator.validate(failure)
        assert locked.parse_locked_wheel_session_receipt(failure).to_private_dict()["decision"] == decision
    unhashable = deepcopy(value); unhashable["reason_codes"] = [[]]; unhashable["receipt_sha256"] = locked._digest(unhashable, "receipt_sha256")
    with pytest.raises(ValueError, match="decision or reasons"):
        locked.parse_locked_wheel_session_receipt(unhashable)
    mixed = locked._private_body(evaluated_at="2026-08-21T00:00:00Z", decision="BLOCKED", reasons=("HANDLE_OPEN_DENIED",))
    mixed["canonical_paths_verified"] = True; mixed["receipt_sha256"] = locked._digest(mixed, "receipt_sha256")
    with pytest.raises(ValidationError): validator.validate(mixed)
    with pytest.raises(ValueError, match="move together"): locked.parse_locked_wheel_session_receipt(mixed)


def test_static_no_effect_surface() -> None:
    sources = "".join((ROOT / "src" / "ai_video_production" / name).read_text(encoding="utf-8") for name in ("qwen_tts_pinned_wheel.py", "qwen_tts_locked_wheel_session.py"))
    for forbidden in ("import subprocess", "import pip", "extractall(", "extract(", "qwen_tts import", "torch import", "requests.", "urlopen(", "mkdir(", "unlink(", "rename("):
        assert forbidden not in sources
