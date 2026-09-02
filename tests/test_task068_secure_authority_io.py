from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import get_type_hints, NoReturn

import pytest

from ai_video_production.secure_authority_io import (
    ArtifactIdentity,
    ImmutableGraphInspectionReceipt,
    ImmutablePublishReceipt,
    SecureAuthorityIO,
    SecureAuthorityIOError,
    TrustedImmutablePlan,
)


def _assert_code(exc: pytest.ExceptionInfo[SecureAuthorityIOError], code: str) -> None:
    assert exc.value.code == code
    assert str(exc.value) == code
    assert "secret" not in repr(exc.value).lower()
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


@contextmanager
def _writer(authority: SecureAuthorityIO, root: Path):
    mode = "existing" if (root / ".writer.lock").exists() else "initial"
    with authority.lock(".writer.lock", mode=mode) as lease:
        yield lease


def _publish(authority: SecureAuthorityIO, root: Path, path: str, document: object):
    with _writer(authority, root) as lease:
        return authority.publish_json_noreplace(path, document, lease=lease)


def _replace(
    authority: SecureAuthorityIO,
    root: Path,
    path: str,
    document: object,
    *,
    expected_identity: ArtifactIdentity,
    expected_sha256: str,
):
    with _writer(authority, root) as lease:
        return authority.replace_json_cas(
            path,
            document,
            lease=lease,
            expected_identity=expected_identity,
            expected_sha256=expected_sha256,
        )


def _cleanup(
    authority: SecureAuthorityIO,
    root: Path,
    path: str,
    *,
    expected_identity: ArtifactIdentity,
    expected_sha256: str,
) -> None:
    with _writer(authority, root) as lease:
        authority.cleanup_owned_file(
            path,
            lease=lease,
            expected_identity=expected_identity,
            expected_sha256=expected_sha256,
        )


def _trusted_plan(
    document: object,
    *,
    relative_path: str = ".immutable-authority/generation-1.json",
    operation_id: str = "0123456789abcdef0123456789abcdef",
    revision: int = 1,
    predecessor_sha256: str = "sha256:" + "0" * 64,
    instance_id: str = "authority-instance-1",
    authorization: str = "authorized-plan-token",
    action: str = "GENERATION",
) -> TrustedImmutablePlan:
    payload = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return TrustedImmutablePlan(
        relative_path=relative_path,
        operation_id=operation_id,
        revision=revision,
        body_sha256="sha256:" + hashlib.sha256(payload).hexdigest(),
        expected_predecessor_sha256=predecessor_sha256,
        action=action,  # type: ignore[arg-type]
        build_id="build-1",
        backend_id="backend-1",
        session_id="session-1",
        instance_id=instance_id,
        authorization=authorization,
    )


def _plan_fingerprint(plan: TrustedImmutablePlan) -> str:
    payload = json.dumps(
        {
            "action": plan.action,
            "authorization_sha256": "sha256:"
            + hashlib.sha256(plan.authorization.encode("ascii")).hexdigest(),
            "backend_id": plan.backend_id,
            "body_sha256": plan.body_sha256,
            "build_id": plan.build_id,
            "expected_predecessor_sha256": plan.expected_predecessor_sha256,
            "instance_id": plan.instance_id,
            "operation_id": plan.operation_id,
            "relative_path": plan.relative_path.replace("\\", "/"),
            "revision": plan.revision,
            "session_id": plan.session_id,
            "version": "TASK068_IMMUTABLE_PLAN_V1",
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _exact_plan_verifier(*plans: TrustedImmutablePlan):
    allowed = {
        (plan.authorization, _plan_fingerprint(plan))
        for plan in plans
    }
    return lambda candidate, fingerprint: (
        candidate.authorization,
        fingerprint,
    ) in allowed


def _graph_fingerprint(*plans: TrustedImmutablePlan) -> str:
    payload = "\n".join(sorted(_plan_fingerprint(plan) for plan in plans)).encode("ascii")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class _ReceiptTrust:
    def __init__(self) -> None:
        self.allowed: set[str] = set()

    def verify(self, fingerprint: str) -> bool:
        return fingerprint in self.allowed

    def accept(self, *receipts: ImmutablePublishReceipt) -> None:
        self.allowed.update(receipt.receipt_fingerprint for receipt in receipts)


class _GraphTrust:
    def __init__(self) -> None:
        self.allowed: set[tuple[str, str]] = set()

    def verify(self, aggregate: str, specified: str) -> bool:
        return (aggregate, specified) in self.allowed

    def accept(
        self,
        *receipts: ImmutablePublishReceipt,
        specified: ImmutablePublishReceipt,
    ) -> None:
        aggregate = "sha256:" + hashlib.sha256(
            "\n".join(
                sorted(receipt.receipt_fingerprint for receipt in receipts)
            ).encode("ascii")
        ).hexdigest()
        self.allowed.add((aggregate, specified.receipt_fingerprint))


def _receipt_fingerprint(receipt: ImmutablePublishReceipt) -> str:
    identity = receipt.identity
    payload = json.dumps(
        {
            "byte_count": receipt.byte_count,
            "identity": {
                "device": identity.device,
                "inode": identity.inode,
                "mode": identity.mode,
                "nlink": identity.nlink,
                "size": identity.size,
                "mtime_ns": identity.mtime_ns,
                "reparse_point": identity.reparse_point,
            },
            "plan_fingerprint": receipt.plan_fingerprint,
            "predecessor_sha256": receipt.predecessor_sha256,
            "security_sha256": receipt.security_sha256,
            "sha256": receipt.sha256,
            "version": receipt.version,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _untrusted_receipt(
    plan: TrustedImmutablePlan,
    identity: ArtifactIdentity,
) -> ImmutablePublishReceipt:
    return ImmutablePublishReceipt(
        sha256=plan.body_sha256,
        predecessor_sha256=plan.expected_predecessor_sha256,
        byte_count=identity.size,
        identity=identity,
        plan_fingerprint=_plan_fingerprint(plan),
        security_sha256="sha256:" + "0" * 64,
        receipt_fingerprint="sha256:" + "0" * 64,
        version="TASK068_IMMUTABLE_RECEIPT_V1",
    )


def _exact_graph_verifier(*plans: TrustedImmutablePlan, specified: TrustedImmutablePlan):
    expected = (_graph_fingerprint(*plans), _plan_fingerprint(specified))
    return lambda graph_fingerprint, specified_fingerprint: (
        graph_fingerprint,
        specified_fingerprint,
    ) == expected


def test_read_json_binds_regular_single_link_file_without_exposing_body(tmp_path: Path) -> None:
    payload = b'{"kind":"authority","value":1}'
    (tmp_path / "receipt.json").write_bytes(payload)

    result = SecureAuthorityIO(tmp_path).read_json("receipt.json")

    assert result.document == {"kind": "authority", "value": 1}
    assert result.sha256.startswith("sha256:")
    assert result.byte_count == len(payload)
    assert "'kind'" not in repr(result)
    assert result.identity.nlink == 1
    assert result.identity.size == len(payload)
    assert result.identity.reparse_point is False
    assert result.authority_created is False
    assert result.currentness_selected is False
    assert result.status_code == "CURRENT_HEAD_AUTHORITY_NOT_CREATED"
    assert result.directory_tree_status_code == "DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED"
    assert result.mutable_phase_status_code == "MUTABLE_PHASE_ADVANCE_UNAVAILABLE"
    assert (
        result.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )


def test_read_close_failure_is_body_free_and_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ai_video_production.secure_authority_io as secure_io

    (tmp_path / "receipt.json").write_text("{}", encoding="utf-8")
    authority = SecureAuthorityIO(tmp_path)
    real_open_target = authority._open_target
    real_close = secure_io.os.close
    target_fds: list[int] = []

    def capture_target(*args: object, **kwargs: object) -> int:
        fd = real_open_target(*args, **kwargs)  # type: ignore[arg-type]
        target_fds.append(fd)
        return fd

    def close_then_fail(fd: int) -> None:
        real_close(fd)
        if target_fds and fd == target_fds[-1]:
            raise OSError

    monkeypatch.setattr(authority, "_open_target", capture_target)
    monkeypatch.setattr(secure_io.os, "close", close_then_fail)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_json("receipt.json")

    _assert_code(exc, "HANDLE_CLOSE_FAILED")
    assert exc.value.authority_created is False


@pytest.mark.parametrize(
    "relative",
    [
        "../escape.json",
        "/absolute.json",
        "",
        ".",
        "private\nreceipt.json",
        "a" * 256,
        "/".join(["a"] * 33),
    ],
)
def test_path_must_be_bounded_relative(relative: str, tmp_path: Path) -> None:
    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json(relative)
    _assert_code(exc, "RELATIVE_PATH_REJECTED")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_bytes": 1024 * 1024 + 1},
        {"max_json_depth": 65},
        {"max_json_nodes": 100_001},
        {"max_bytes": True},
        {"max_json_depth": 1.5},
    ],
)
def test_constructor_bounds_cannot_be_disabled_by_caller(
    kwargs: dict[str, object], tmp_path: Path
) -> None:
    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path, **kwargs)  # type: ignore[arg-type]

    _assert_code(exc, "BOUND_REJECTED")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "relative", ["file:stream", "CON", "aux.txt", "trailing.", "trailing "]
)
def test_path_rejects_windows_ads_devices_and_ambiguous_suffixes(
    relative: str, tmp_path: Path
) -> None:
    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json(relative)
    _assert_code(exc, "RELATIVE_PATH_REJECTED")


@pytest.mark.parametrize(
    "relative",
    [
        "cOm¹.TxT",
        "COM².json",
        "com³.ext",
        "lPt¹.TxT",
        "LPT².json",
        "lpt³.ext",
    ],
)
def test_path_rejects_windows_superscript_device_aliases_without_effect(
    relative: str, tmp_path: Path
) -> None:
    unrelated = tmp_path / "unrelated.json"
    unrelated.write_bytes(b'{"preserve":true}')
    before = {entry.name: entry.read_bytes() for entry in tmp_path.iterdir()}

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json(relative)

    _assert_code(exc, "RELATIVE_PATH_REJECTED")
    assert exc.value.authority_created is False
    assert exc.value.currentness_selected is False
    assert {entry.name: entry.read_bytes() for entry in tmp_path.iterdir()} == before


def test_read_rejects_symlink_without_following_it(tmp_path: Path) -> None:
    target = tmp_path / "secret.json"
    target.write_text('{"secret":"do-not-leak"}', encoding="utf-8")
    link = tmp_path / "receipt.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("receipt.json")

    assert exc.value.code in {"OPEN_FAILED", "NOT_REGULAR_FILE", "REPARSE_POINT_REJECTED"}
    assert "do-not-leak" not in str(exc.value)


def test_read_rejects_hardlinked_file(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    linked = tmp_path / "linked.json"
    os.link(source, linked)

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("linked.json")

    _assert_code(exc, "LINK_COUNT_REJECTED")


def test_read_rejects_nonregular_target(tmp_path: Path) -> None:
    (tmp_path / "receipt.json").mkdir()
    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("receipt.json")
    _assert_code(exc, "NOT_REGULAR_FILE")


def test_read_rejects_ancestor_symlink(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "receipt.json").write_text("{}", encoding="utf-8")
    link = tmp_path / "alias"
    try:
        link.symlink_to(actual, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("alias/receipt.json")

    assert exc.value.code in {"ANCESTOR_NOT_DIRECTORY", "REPARSE_POINT_REJECTED"}


@pytest.mark.skipif(os.name == "nt", reason="Windows pinned read handle denies replacement")
def test_read_detects_file_substitution_after_payload_read(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    target.write_text('{"version":1}', encoding="utf-8")

    def hook(stage: str) -> None:
        if stage == "read_complete":
            replacement = tmp_path / "replacement.json"
            replacement.write_text('{"version":2}', encoding="utf-8")
            os.replace(replacement, target)

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path, _stage_hook=hook).read_json("receipt.json")

    _assert_code(exc, "FILE_IDENTITY_CHANGED")


@pytest.mark.parametrize(
    "seam,expected",
    [
        ("target_lstat_complete", "FILE_BINDING_MISMATCH"),
        ("target_open_complete", "LINK_COUNT_REJECTED"),
        ("post_fstat_complete", "FILE_IDENTITY_CHANGED"),
    ],
)
def test_pinned_read_rejects_same_bytes_different_inode_at_each_seam(
    seam: str, expected: str, tmp_path: Path
) -> None:
    if os.name == "nt" and seam != "target_lstat_complete":
        pytest.skip("Windows pinned read handle denies replacement after open")
    target = tmp_path / "receipt.json"
    target.write_text('{"same":true}', encoding="utf-8")

    def hook(stage: str) -> None:
        if stage == seam:
            replacement = tmp_path / "replacement.json"
            replacement.write_text('{"same":true}', encoding="utf-8")
            os.replace(replacement, target)

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path, _stage_hook=hook).read_json("receipt.json")

    _assert_code(exc, expected)
    assert target.read_text(encoding="utf-8") == '{"same":true}'


@pytest.mark.skipif(os.name == "nt", reason="Windows pinned ancestor handle denies rename")
def test_read_detects_ancestor_substitution(tmp_path: Path) -> None:
    parent = tmp_path / "authority"
    parent.mkdir()
    (parent / "receipt.json").write_text("{}", encoding="utf-8")

    def hook(stage: str) -> None:
        if stage == "read_complete":
            parent.rename(tmp_path / "old-authority")
            parent.mkdir()

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path, _stage_hook=hook).read_json("authority/receipt.json")

    assert exc.value.code in {"ANCESTOR_IDENTITY_CHANGED", "ANCESTOR_POST_IDENTITY_FAILED"}


def test_read_rejects_byte_bound_before_decode(tmp_path: Path) -> None:
    (tmp_path / "receipt.json").write_bytes(b'{"secret":"0123456789"}')

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path, max_bytes=8).read_json("receipt.json")

    _assert_code(exc, "BYTE_BOUND_EXCEEDED")


@pytest.mark.parametrize(
    "payload",
    [
        b"\xff",
        b"\xef\xbb\xbf{}",
        b'{"duplicate":1,"duplicate":2}',
        b'{"number":NaN}',
        b'{"number":Infinity}',
        b'{"number":-Infinity}',
        b'{"nested":{"duplicate":1,"duplicate":1}}',
        b"{} trailing",
        b'{"unterminated":',
    ],
)
def test_strict_json_rejects_ambiguous_or_invalid_documents(payload: bytes, tmp_path: Path) -> None:
    (tmp_path / "receipt.json").write_bytes(payload)

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("receipt.json")

    _assert_code(exc, "STRICT_JSON_REJECTED")


@pytest.mark.parametrize(
    "payload,code",
    [
        (b'{"number":1e999}', "JSON_NONFINITE_REJECTED"),
        (b'{"control":"\\u0000"}', "JSON_CONTROL_CHARACTER_REJECTED"),
    ],
)
def test_strict_json_rejects_decoded_nonfinite_and_control_values(
    payload: bytes, code: str, tmp_path: Path
) -> None:
    (tmp_path / "receipt.json").write_bytes(payload)
    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("receipt.json")
    _assert_code(exc, code)


def test_publish_rejects_non_builtin_json_before_filesystem_effect(tmp_path: Path) -> None:
    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(SecureAuthorityIO(tmp_path), tmp_path, "receipt.json", {"x": object()})

    _assert_code(exc, "JSON_VALUE_REJECTED")
    assert [path.name for path in tmp_path.iterdir()] == [".writer.lock"]


def test_strict_json_applies_depth_and_node_bounds(tmp_path: Path) -> None:
    (tmp_path / "deep.json").write_text('{"a":{"b":{"c":1}}}', encoding="utf-8")
    (tmp_path / "wide.json").write_text("[1,2,3,4]", encoding="utf-8")

    with pytest.raises(SecureAuthorityIOError) as depth:
        SecureAuthorityIO(tmp_path, max_json_depth=2).read_json("deep.json")
    with pytest.raises(SecureAuthorityIOError) as nodes:
        SecureAuthorityIO(tmp_path, max_json_nodes=4).read_json("wide.json")

    _assert_code(depth, "JSON_DEPTH_BOUND_EXCEEDED")
    _assert_code(nodes, "JSON_NODE_BOUND_EXCEEDED")


def test_existing_and_initial_lock_are_exclusive_and_durable(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with authority.lock("authority.lock", mode="initial") as first:
        assert first.identity is not None
        assert first.identity.nlink == 1
        with pytest.raises(SecureAuthorityIOError) as busy:
            with authority.lock("authority.lock", mode="existing"):
                pass
        _assert_code(busy, "LOCK_BUSY")

    assert (tmp_path / "authority.lock").read_bytes() == b"\0"
    with authority.lock("authority.lock", mode="existing") as reopened:
        assert reopened.identity is not None


def test_writer_lease_is_owner_bound_and_inactive_after_exit(tmp_path: Path) -> None:
    owner = SecureAuthorityIO(tmp_path)
    foreign_owner = SecureAuthorityIO(tmp_path)
    capability = owner.lock("authority.lock", mode="initial")

    with capability as lease:
        with pytest.raises(SecureAuthorityIOError) as wrong_owner:
            foreign_owner.publish_json_noreplace("receipt.json", {}, lease=lease)
        _assert_code(wrong_owner, "WRITER_LEASE_REQUIRED")

    with pytest.raises(SecureAuthorityIOError) as inactive:
        owner.publish_json_noreplace("receipt.json", {}, lease=lease)
    _assert_code(inactive, "WRITER_LEASE_REQUIRED")
    assert not (tmp_path / "receipt.json").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX namespace swap")
def test_writer_lease_root_inode_is_bound_to_publish_effect(tmp_path: Path) -> None:
    root = tmp_path / "authority"
    moved_root = tmp_path / "authority-moved"
    root.mkdir()
    authority = SecureAuthorityIO(root)

    with authority.lock(".writer.lock", mode="initial") as lease:
        os.rename(root, moved_root)
        root.mkdir()
        os.rename(moved_root / ".writer.lock", root / ".writer.lock")
        try:
            with pytest.raises(SecureAuthorityIOError) as exc:
                authority.publish_json_noreplace("receipt.json", {}, lease=lease)
            _assert_code(exc, "ANCESTOR_IDENTITY_CHANGED")
            assert not (root / "receipt.json").exists()
            assert not (moved_root / "receipt.json").exists()
        finally:
            os.rename(root / ".writer.lock", moved_root / ".writer.lock")
            root.rmdir()
            os.rename(moved_root, root)


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor open")
def test_posix_ancestor_inheritance_failure_closes_opened_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[int] = []
    real_open = os.open

    def capture_open(*args: object, **kwargs: object) -> int:
        fd = real_open(*args, **kwargs)  # type: ignore[arg-type]
        opened.append(fd)
        return fd

    def reject(_: int) -> None:
        raise SecureAuthorityIOError("HANDLE_INHERITANCE_REJECTED")

    monkeypatch.setattr("ai_video_production.secure_authority_io.os.open", capture_open)
    monkeypatch.setattr(
        "ai_video_production.secure_authority_io._set_noninheritable", reject
    )

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("missing.json")

    _assert_code(exc, "HANDLE_INHERITANCE_REJECTED")
    assert opened
    with pytest.raises(OSError):
        os.fstat(opened[-1])


@pytest.mark.skipif(os.name == "nt", reason="POSIX unnamed temporary file")
def test_posix_unnamed_temp_inheritance_failure_closes_opened_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[int] = []
    real_set = os.set_inheritable

    def reject_unnamed(fd: int) -> None:
        if os.fstat(fd).st_nlink == 0:
            captured.append(fd)
            raise SecureAuthorityIOError("HANDLE_INHERITANCE_REJECTED")
        real_set(fd, False)

    monkeypatch.setattr(
        "ai_video_production.secure_authority_io._set_noninheritable", reject_unnamed
    )
    capability = SecureAuthorityIO(tmp_path).lock(".writer.lock", mode="initial")

    with pytest.raises(SecureAuthorityIOError) as exc:
        with capability:
            pass

    _assert_code(exc, "HANDLE_INHERITANCE_REJECTED")
    assert captured
    with pytest.raises(OSError):
        os.fstat(captured[-1])


@pytest.mark.skipif(os.name == "nt", reason="POSIX unnamed temporary file")
def test_posix_unnamed_temp_close_fault_is_cleanup_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ai_video_production.secure_authority_io as secure_io

    captured: list[int] = []
    real_set = os.set_inheritable
    real_close = secure_io.os.close

    def reject_unnamed(fd: int) -> None:
        if os.fstat(fd).st_nlink == 0:
            captured.append(fd)
            raise SecureAuthorityIOError("HANDLE_INHERITANCE_REJECTED")
        real_set(fd, False)

    def close_then_fail(fd: int) -> None:
        real_close(fd)
        if captured and fd == captured[-1]:
            raise OSError

    monkeypatch.setattr(secure_io, "_set_noninheritable", reject_unnamed)
    monkeypatch.setattr(secure_io.os, "close", close_then_fail)

    with pytest.raises(SecureAuthorityIOError) as exc:
        with SecureAuthorityIO(tmp_path).lock(".writer.lock", mode="initial"):
            pass

    _assert_code(exc, "HANDLE_CLEANUP_UNKNOWN")
    assert exc.value.completion_unknown is True
    assert captured
    with pytest.raises(OSError):
        os.fstat(captured[-1])


def test_posix_ancestor_post_open_validation_failure_closes_untransferred_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ai_video_production.secure_authority_io as secure_io

    authority = SecureAuthorityIO(tmp_path)
    real_open = authority._open_directory
    real_require = secure_io._require_directory
    captured: list[int] = []
    checks = 0

    def capture_open(*args: object, **kwargs: object) -> int:
        fd = real_open(*args, **kwargs)  # type: ignore[arg-type]
        captured.append(fd)
        return fd

    def reject_opened(value: object) -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            raise SecureAuthorityIOError("ANCESTOR_REJECTED")
        real_require(value)  # type: ignore[arg-type]

    monkeypatch.setattr(authority, "_open_directory", capture_open)
    monkeypatch.setattr(secure_io, "_require_directory", reject_opened)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_json("missing.json")

    _assert_code(exc, "ANCESTOR_REJECTED")
    assert captured
    with pytest.raises(OSError):
        os.fstat(captured[-1])
    assert list(tmp_path.iterdir()) == []


def test_posix_ancestor_validation_close_fault_is_cleanup_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ai_video_production.secure_authority_io as secure_io

    authority = SecureAuthorityIO(tmp_path)
    real_open = authority._open_directory
    real_require = secure_io._require_directory
    real_close = secure_io.os.close
    captured: list[int] = []
    checks = 0

    def capture_open(*args: object, **kwargs: object) -> int:
        fd = real_open(*args, **kwargs)  # type: ignore[arg-type]
        captured.append(fd)
        return fd

    def reject_opened(value: object) -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            raise SecureAuthorityIOError("ANCESTOR_REJECTED")
        real_require(value)  # type: ignore[arg-type]

    def close_then_fail(fd: int) -> None:
        real_close(fd)
        if captured and fd == captured[-1]:
            raise OSError

    monkeypatch.setattr(authority, "_open_directory", capture_open)
    monkeypatch.setattr(secure_io, "_require_directory", reject_opened)
    monkeypatch.setattr(secure_io.os, "close", close_then_fail)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_json("missing.json")

    _assert_code(exc, "HANDLE_CLEANUP_UNKNOWN")
    assert exc.value.completion_unknown is True
    assert captured
    with pytest.raises(OSError):
        os.fstat(captured[-1])
    assert list(tmp_path.iterdir()) == []


def test_lock_capability_type_is_not_publicly_exported() -> None:
    from ai_video_production import secure_authority_io

    assert "SecureFileLock" not in secure_authority_io.__all__
    assert not hasattr(secure_authority_io, "SecureFileLock")


def test_lock_capability_has_no_public_mutable_reset_state(tmp_path: Path) -> None:
    capability = SecureAuthorityIO(tmp_path).lock("authority.lock", mode="initial")

    assert not hasattr(capability, "__dict__")
    with pytest.raises(AttributeError):
        capability._used = False  # type: ignore[attr-defined]

    with capability:
        pass
    with pytest.raises(SecureAuthorityIOError) as burned:
        with capability:
            pass

    _assert_code(burned, "CAPABILITY_BURNED")


def test_initial_lock_collision_does_not_retry_and_burns_capability(tmp_path: Path) -> None:
    target = tmp_path / "authority.lock"

    def hook(stage: str) -> None:
        if stage == "before_lock_open":
            target.write_bytes(b"competitor")

    capability = SecureAuthorityIO(tmp_path, _stage_hook=hook).lock(
        "authority.lock", mode="initial"
    )
    with pytest.raises(SecureAuthorityIOError) as collision:
        with capability:
            pass
    with pytest.raises(SecureAuthorityIOError) as burned:
        with capability:
            pass

    _assert_code(collision, "LOCK_CREATE_COLLISION")
    _assert_code(burned, "CAPABILITY_BURNED")
    assert target.read_bytes() == b"competitor"


def test_initial_lock_publish_race_is_classified_and_preserves_competitor(
    tmp_path: Path,
) -> None:
    target = tmp_path / "authority.lock"

    def hook(stage: str) -> None:
        if stage == "before_initial_lock_publish":
            target.write_bytes(b"competitor")

    capability = SecureAuthorityIO(tmp_path, _stage_hook=hook).lock(
        "authority.lock", mode="initial"
    )
    with pytest.raises(SecureAuthorityIOError) as collision:
        with capability:
            pass
    with pytest.raises(SecureAuthorityIOError) as burned:
        with capability:
            pass

    _assert_code(collision, "LOCK_CREATE_COLLISION")
    _assert_code(burned, "CAPABILITY_BURNED")
    assert target.read_bytes() == b"competitor"
    assert list(tmp_path.glob(".authority-*.tmp")) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX durability classification")
def test_posix_initial_lock_durability_failure_is_completion_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    original = authority._directory_durable
    calls = 0

    def fail_first(parent: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SecureAuthorityIOError("DIRECTORY_DURABILITY_FAILED")
        original(parent)  # type: ignore[arg-type]

    monkeypatch.setattr(authority, "_directory_durable", fail_first)
    capability = authority.lock("authority.lock", mode="initial")

    with pytest.raises(SecureAuthorityIOError) as exc:
        with capability:
            pass
    with pytest.raises(SecureAuthorityIOError) as burned:
        with capability:
            pass

    _assert_code(exc, "LOCK_INITIALIZATION_UNKNOWN")
    assert exc.value.completion_unknown is True
    _assert_code(burned, "CAPABILITY_BURNED")
    assert (tmp_path / "authority.lock").read_bytes() == b"\0"
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_initial_lock_rollback_durability_failure_is_completion_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = SecureAuthorityIO(tmp_path)

    def always_fail(_: object) -> None:
        raise SecureAuthorityIOError("DIRECTORY_DURABILITY_FAILED")

    monkeypatch.setattr(authority, "_directory_durable", always_fail)
    capability = authority.lock("authority.lock", mode="initial")

    with pytest.raises(SecureAuthorityIOError) as exc:
        with capability:
            pass

    _assert_code(exc, "LOCK_INITIALIZATION_UNKNOWN")
    assert exc.value.completion_unknown is True
    assert exc.value.authority_created is False


def test_existing_lock_missing_is_not_created(tmp_path: Path) -> None:
    with pytest.raises(SecureAuthorityIOError) as exc:
        with SecureAuthorityIO(tmp_path).lock("authority.lock", mode="existing"):
            pass
    _assert_code(exc, "LOCK_NOT_FOUND")
    assert list(tmp_path.iterdir()) == []


def test_existing_lock_rejects_unknown_marker_without_mutation(tmp_path: Path) -> None:
    target = tmp_path / "authority.lock"
    target.write_bytes(b"foreign")
    with pytest.raises(SecureAuthorityIOError) as exc:
        with SecureAuthorityIO(tmp_path).lock("authority.lock", mode="existing"):
            pass
    _assert_code(exc, "LOCK_MARKER_REJECTED")
    assert target.read_bytes() == b"foreign"


@pytest.mark.skipif(os.name == "nt", reason="Windows live lock handle denies replacement")
def test_existing_lock_rejects_same_bytes_different_inode_swap(tmp_path: Path) -> None:
    target = tmp_path / "authority.lock"
    target.write_bytes(b"\0")

    def hook(stage: str) -> None:
        if stage == "lock_acquired":
            replacement = tmp_path / "replacement.lock"
            replacement.write_bytes(b"\0")
            os.replace(replacement, target)

    with pytest.raises(SecureAuthorityIOError) as exc:
        with SecureAuthorityIO(tmp_path, _stage_hook=hook).lock(
            "authority.lock", mode="existing"
        ):
            pass
    _assert_code(exc, "LOCK_IDENTITY_CHANGED")


def test_existing_lock_failure_close_error_is_cleanup_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ai_video_production.secure_authority_io as secure_io

    target = tmp_path / "authority.lock"
    target.write_bytes(b"\0")
    authority = SecureAuthorityIO(
        tmp_path,
        _stage_hook=lambda stage: (
            (_ for _ in ()).throw(SecureAuthorityIOError("INJECTED_LOCK_FAILURE"))
            if stage == "lock_acquired"
            else None
        ),
    )
    real_open_target = authority._open_target
    real_close = secure_io.os.close
    captured: list[int] = []

    def capture_target(*args: object, **kwargs: object) -> int:
        fd = real_open_target(*args, **kwargs)  # type: ignore[arg-type]
        captured.append(fd)
        return fd

    def close_then_fail(fd: int) -> None:
        real_close(fd)
        if captured and fd == captured[-1]:
            raise OSError

    monkeypatch.setattr(authority, "_open_target", capture_target)
    monkeypatch.setattr(secure_io.os, "close", close_then_fail)

    with pytest.raises(SecureAuthorityIOError) as exc:
        with authority.lock("authority.lock", mode="existing"):
            pass

    _assert_code(exc, "LOCK_CLEANUP_UNKNOWN")
    assert exc.value.completion_unknown is True
    assert target.read_bytes() == b"\0"


def test_lock_rejects_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source.lock"
    source.write_bytes(b"\0")
    link = tmp_path / "authority.lock"
    try:
        link.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(SecureAuthorityIOError) as exc:
        with SecureAuthorityIO(tmp_path).lock("authority.lock", mode="existing"):
            pass

    assert exc.value.code in {"OPEN_FAILED", "NOT_REGULAR_FILE", "REPARSE_POINT_REJECTED"}


def test_publish_json_noreplace_has_canonical_exact_receipt(tmp_path: Path) -> None:
    receipt = _publish(
        SecureAuthorityIO(tmp_path), tmp_path, "receipt.json", {"z": 2, "a": "日本語"}
    )

    expected = json.dumps(
        {"z": 2, "a": "日本語"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert (tmp_path / "receipt.json").read_bytes() == expected
    assert receipt.byte_count == len(expected)
    assert receipt.identity.nlink == 1
    assert receipt.identity.size == len(expected)
    assert receipt.authority_created is False
    assert receipt.currentness_selected is False
    assert receipt.status_code == "CURRENT_HEAD_AUTHORITY_NOT_CREATED"
    assert receipt.directory_tree_status_code == "DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED"
    assert receipt.mutable_phase_status_code == "MUTABLE_PHASE_ADVANCE_UNAVAILABLE"
    assert (
        receipt.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_immutable_publish_requires_verified_exact_plan_and_never_selects_currentness(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        authority_instance_id="authority-instance-1",
    )

    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)

    assert isinstance(receipt, ImmutablePublishReceipt)
    assert receipt.sha256 == plan.body_sha256
    assert receipt.predecessor_sha256 == plan.expected_predecessor_sha256
    assert receipt.identity.nlink == 1
    assert receipt.authority_created is False
    assert receipt.currentness_selected is False
    assert receipt.status_code == "CURRENT_HEAD_AUTHORITY_NOT_CREATED"
    assert (
        receipt.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    assert (
        plan.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    assert "generation-1.json" not in repr(receipt)
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"generation":1}'


@pytest.mark.parametrize(
    "reserved_path",
    [
        ".immutable-authority/unbound.json",
        ".IMMUTABLE-AUTHORITY/unbound.json",
        ".Immutable-Authority/unbound.json",
    ],
)
def test_immutable_namespace_rejects_unbound_raw_publish(
    tmp_path: Path, reserved_path: str
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    authority = SecureAuthorityIO(tmp_path)

    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_json_noreplace(
                reserved_path, {"x": 1}, lease=lease
            )

    _assert_code(exc, "TRUSTED_GENERATION_PLAN_REQUIRED")
    assert exc.value.authority_created is False
    assert exc.value.currentness_selected is False
    assert exc.value.status_code == "CURRENT_HEAD_AUTHORITY_NOT_CREATED"
    assert (
        exc.value.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


@pytest.mark.parametrize(
    "plan_update",
    [
        {"relative_path": ".immutable-authority/other.json"},
        {"operation_id": "fedcba9876543210fedcba9876543210"},
        {"revision": 2},
        {"body_sha256": "sha256:" + "1" * 64},
        {"expected_predecessor_sha256": "sha256:" + "2" * 64},
        {"action": "TOMBSTONE"},
        {"build_id": "build-2"},
        {"backend_id": "backend-2"},
        {"session_id": "session-2"},
        {"instance_id": "authority-instance-2"},
        {"authorization": "other-authorized-token"},
    ],
)
def test_complete_plan_fingerprint_verifier_rejects_every_field_rebinding(
    tmp_path: Path, plan_update: dict[str, object]
) -> None:
    from dataclasses import replace

    document = {"generation": 1}
    (tmp_path / ".immutable-authority").mkdir()
    exact_plan = _trusted_plan(document)
    changed_plan = replace(exact_plan, **plan_update)
    seen: list[str] = []

    def verifier(candidate: TrustedImmutablePlan, fingerprint: str) -> bool:
        seen.append(fingerprint)
        return (
            candidate.authorization == exact_plan.authorization
            and fingerprint == _plan_fingerprint(exact_plan)
        )

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=verifier,
        authority_instance_id=changed_plan.instance_id,
    )
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_immutable_json(
                document,
                plan=changed_plan,
                lease=lease,
            )

    _assert_code(exc, "TRUSTED_GENERATION_PLAN_REJECTED")
    assert seen == [_plan_fingerprint(changed_plan)]
    assert seen[0] != _plan_fingerprint(exact_plan)
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


@pytest.mark.parametrize(
    ("plan_update", "expected_code"),
    [
        ({"authorization": "forged-plan-token"}, "TRUSTED_GENERATION_PLAN_REJECTED"),
        ({"instance_id": "other-instance"}, "TRUSTED_GENERATION_PLAN_REQUIRED"),
        ({"operation_id": "not-random"}, "IMMUTABLE_OPERATION_ID_REJECTED"),
        ({"revision": True}, "IMMUTABLE_REVISION_REJECTED"),
        ({"revision": 0}, "IMMUTABLE_REVISION_REJECTED"),
        ({"revision": 1_000_001}, "IMMUTABLE_REVISION_REJECTED"),
        ({"relative_path": "outside.json"}, "IMMUTABLE_COORDINATE_REJECTED"),
    ],
)
def test_immutable_publish_rejects_untrusted_or_unbound_coordinate_effect_zero(
    tmp_path: Path, plan_update: dict[str, object], expected_code: str
) -> None:
    from dataclasses import replace

    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = replace(_trusted_plan(document), **plan_update)
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=lambda candidate, _: candidate.authorization
        == "authorized-plan-token",
        authority_instance_id="authority-instance-1",
    )

    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_immutable_json(document, plan=plan, lease=lease)

    _assert_code(exc, expected_code)
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


def test_immutable_publish_digest_mismatch_and_collision_preserve_all_objects(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=lambda _plan, _fingerprint: True,
        authority_instance_id="authority-instance-1",
    )
    valid_plan = _trusted_plan({"generation": 1})

    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as mismatch:
            authority.publish_immutable_json({"generation": 2}, plan=valid_plan, lease=lease)
    _assert_code(mismatch, "IMMUTABLE_BODY_DIGEST_MISMATCH")
    assert list((tmp_path / ".immutable-authority").iterdir()) == []

    target = tmp_path / valid_plan.relative_path
    target.write_bytes(b"FOREIGN")
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as collision:
            authority.publish_immutable_json(
                {"generation": 1}, plan=valid_plan, lease=lease
            )
    _assert_code(collision, "DESTINATION_EXISTS")
    assert target.read_bytes() == b"FOREIGN"


def test_exact_terminal_republish_never_creates_duplicate_currentness_authority(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"terminal": "complete"}
    plan = _trusted_plan(document, action="COMMIT")
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as duplicate:
            authority.publish_immutable_json(document, plan=plan, lease=lease)

    _assert_code(duplicate, "DESTINATION_EXISTS")
    assert (
        duplicate.value.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    assert receipt.authority_created is False
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"terminal":"complete"}'
    assert not any(
        hasattr(authority, name)
        for name in ("derive_duplicate", "resolve_duplicate", "select_duplicate")
    )


def test_exact_immutable_read_never_scans_or_selects_highest_generation(tmp_path: Path) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    receipt_trust = _ReceiptTrust()
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=lambda _plan, _fingerprint: True,
        immutable_receipt_verifier=receipt_trust.verify,
        authority_instance_id="authority-instance-1",
    )
    first_plan = _trusted_plan(
        {"generation": 1}, relative_path=".immutable-authority/generation-1.json"
    )
    second_plan = _trusted_plan(
        {"generation": 2},
        relative_path=".immutable-authority/generation-2.json",
        revision=2,
        predecessor_sha256=first_plan.body_sha256,
    )
    with _writer(authority, tmp_path) as lease:
        first_receipt = authority.publish_immutable_json(
            {"generation": 1}, plan=first_plan, lease=lease
        )
    receipt_trust.accept(first_receipt)
    with _writer(authority, tmp_path) as lease:
        authority.publish_immutable_json({"generation": 2}, plan=second_plan, lease=lease)

    exact = authority.read_immutable_json(
        plan=first_plan, receipt=first_receipt
    )

    assert exact.document == {"generation": 1}
    assert exact.currentness_selected is False
    assert not any(
        hasattr(authority, name)
        for name in ("resolve_current", "select_head", "latest", "scan_highest")
    )


def test_immutable_graph_inspection_is_exact_and_non_authoritative(tmp_path: Path) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    first_plan = _trusted_plan(
        {"generation": 1}, relative_path=".immutable-authority/generation-1.json"
    )
    second_plan = _trusted_plan(
        {"generation": 2},
        relative_path=".immutable-authority/generation-2.json",
        revision=2,
        predecessor_sha256=first_plan.body_sha256,
    )
    receipt_trust = _ReceiptTrust()
    graph_trust = _GraphTrust()
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(first_plan, second_plan),
        immutable_receipt_verifier=receipt_trust.verify,
        immutable_graph_verifier=graph_trust.verify,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        first = authority.publish_immutable_json(
            {"generation": 1}, plan=first_plan, lease=lease
        )
    with _writer(authority, tmp_path) as lease:
        second = authority.publish_immutable_json(
            {"generation": 2}, plan=second_plan, lease=lease
        )
    receipt_trust.accept(first, second)
    graph_trust.accept(first, second, specified=second)

    inspection = authority.inspect_immutable_graph(
        plans=[first_plan, second_plan],
        expected_receipts={
            first_plan.relative_path: first,
            second_plan.relative_path: second,
        },
        specified_plan=second_plan,
    )
    repeated_inspection = authority.inspect_immutable_graph(
        plans=[first_plan, second_plan],
        expected_receipts={
            first_plan.relative_path: first,
            second_plan.relative_path: second,
        },
        specified_plan=second_plan,
    )

    assert isinstance(inspection, ImmutableGraphInspectionReceipt)
    assert inspection.inspected_count == 2
    assert inspection.authority_created is False
    assert inspection.currentness_selected is False
    assert inspection.status_code == "CURRENT_HEAD_AUTHORITY_NOT_CREATED"
    assert (
        inspection.duplicate_currentness_status_code
        == repeated_inspection.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    assert not hasattr(inspection, "head")
    assert not hasattr(inspection, "current")


def test_consumer_bound_graph_verifier_stops_replayed_tombstone_and_resume(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    root_plan = _trusted_plan(
        {"generation": 1}, relative_path=".immutable-authority/root.json"
    )
    tombstone_plan = _trusted_plan(
        {"tombstone": True},
        relative_path=".immutable-authority/tombstone.json",
        revision=2,
        predecessor_sha256=root_plan.body_sha256,
        action="TOMBSTONE",
    )
    resumed_plan = _trusted_plan(
        {"generation": 2},
        relative_path=".immutable-authority/resumed.json",
        revision=3,
        predecessor_sha256=tombstone_plan.body_sha256,
    )
    receipt_trust = _ReceiptTrust()
    expected_graph: str | None = None
    expected_specified: str | None = None
    graph_checks = 0

    def one_shot_graph_verifier(
        graph_fingerprint: str, specified_fingerprint: str
    ) -> bool:
        nonlocal graph_checks
        graph_checks += 1
        return (
            graph_checks == 1
            and graph_fingerprint == expected_graph
            and specified_fingerprint == expected_specified
        )

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(root_plan, tombstone_plan),
        immutable_receipt_verifier=receipt_trust.verify,
        immutable_graph_verifier=one_shot_graph_verifier,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        root = authority.publish_immutable_json(
            {"generation": 1}, plan=root_plan, lease=lease
        )
    with _writer(authority, tmp_path) as lease:
        tombstone = authority.publish_immutable_json(
            {"tombstone": True}, plan=tombstone_plan, lease=lease
        )
    receipt_trust.accept(root, tombstone)
    expected_graph = "sha256:" + hashlib.sha256(
        "\n".join(
            sorted((root.receipt_fingerprint, tombstone.receipt_fingerprint))
        ).encode("ascii")
    ).hexdigest()
    expected_specified = tombstone.receipt_fingerprint
    receipts = {
        root_plan.relative_path: root,
        tombstone_plan.relative_path: tombstone,
    }

    authority.inspect_immutable_graph(
        plans=[root_plan, tombstone_plan],
        expected_receipts=receipts,
        specified_plan=tombstone_plan,
    )
    with pytest.raises(SecureAuthorityIOError) as replay:
        authority.inspect_immutable_graph(
            plans=[root_plan, tombstone_plan],
            expected_receipts=receipts,
            specified_plan=tombstone_plan,
        )
    _assert_code(replay, "TRUSTED_IMMUTABLE_GRAPH_REJECTED")

    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as resumed:
            authority.publish_immutable_json(
                {"generation": 2}, plan=resumed_plan, lease=lease
            )
    _assert_code(resumed, "TRUSTED_GENERATION_PLAN_REJECTED")
    assert sorted(path.name for path in (tmp_path / ".immutable-authority").iterdir()) == [
        "root.json",
        "tombstone.json",
    ]


def test_immutable_graph_unknown_artifact_stops_and_preserves_everything(tmp_path: Path) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    plan = _trusted_plan({"generation": 1})
    receipt_trust = _ReceiptTrust()
    graph_trust = _GraphTrust()
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        immutable_receipt_verifier=receipt_trust.verify,
        immutable_graph_verifier=graph_trust.verify,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(
            {"generation": 1}, plan=plan, lease=lease
        )
    receipt_trust.accept(receipt)
    graph_trust.accept(receipt, specified=receipt)
    unknown = tmp_path / ".immutable-authority" / "unknown.json"
    unknown.write_bytes(b"FOREIGN")

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.inspect_immutable_graph(
            plans=[plan],
            expected_receipts={plan.relative_path: receipt},
            specified_plan=plan,
        )

    _assert_code(exc, "IMMUTABLE_UNKNOWN_ARTIFACT")
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"generation":1}'
    assert unknown.read_bytes() == b"FOREIGN"


def test_immutable_graph_scan_race_stops_without_adopting_new_entry(tmp_path: Path) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    scans = 0
    plan = _trusted_plan({"generation": 1})
    receipt_trust = _ReceiptTrust()
    graph_trust = _GraphTrust()

    def hook(stage: str) -> None:
        nonlocal scans
        if stage == "immutable_scan_before":
            scans += 1
            if scans == 2:
                (tmp_path / ".immutable-authority" / "raced.json").write_bytes(b"FOREIGN")

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        immutable_receipt_verifier=receipt_trust.verify,
        immutable_graph_verifier=graph_trust.verify,
        authority_instance_id="authority-instance-1",
        _stage_hook=hook,
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(
            {"generation": 1}, plan=plan, lease=lease
        )
    receipt_trust.accept(receipt)
    graph_trust.accept(receipt, specified=receipt)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.inspect_immutable_graph(
            plans=[plan],
            expected_receipts={plan.relative_path: receipt},
            specified_plan=plan,
        )

    _assert_code(exc, "IMMUTABLE_SCAN_CHANGED")
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"generation":1}'
    assert (tmp_path / ".immutable-authority" / "raced.json").read_bytes() == b"FOREIGN"


def test_immutable_read_rejects_same_body_different_inode(tmp_path: Path) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    receipt_trust = _ReceiptTrust()
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=lambda _plan, _fingerprint: True,
        immutable_receipt_verifier=receipt_trust.verify,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)
    receipt_trust.accept(receipt)
    replacement = tmp_path / ".immutable-authority" / "replacement.json"
    replacement.write_bytes((tmp_path / plan.relative_path).read_bytes())
    os.replace(replacement, tmp_path / plan.relative_path)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_immutable_json(plan=plan, receipt=receipt)

    _assert_code(exc, "IMMUTABLE_BINDING_MISMATCH")
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"generation":1}'


def test_immutable_graph_fork_and_missing_predecessor_stop_without_winner(
    tmp_path: Path,
) -> None:
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=lambda _plan, _fingerprint: True,
        authority_instance_id="authority-instance-1",
    )
    root = _trusted_plan(
        {"generation": 1}, relative_path=".immutable-authority/root.json"
    )
    left = _trusted_plan(
        {"generation": 2},
        relative_path=".immutable-authority/left.json",
        revision=2,
        predecessor_sha256=root.body_sha256,
    )
    right = _trusted_plan(
        {"generation": 3},
        relative_path=".immutable-authority/right.json",
        revision=3,
        predecessor_sha256=root.body_sha256,
    )
    identities = {
        plan.relative_path: _untrusted_receipt(
            plan,
            ArtifactIdentity(1, index, stat.S_IFREG, 1, 1, 1, False),
        )
        for index, plan in enumerate((root, left, right), start=1)
    }

    with pytest.raises(SecureAuthorityIOError) as fork:
        authority.inspect_immutable_graph(
            plans=[root, left, right],
            expected_receipts=identities,
            specified_plan=left,
        )
    _assert_code(fork, "IMMUTABLE_FORK_STOP")

    missing = _trusted_plan(
        {"generation": 4},
        relative_path=".immutable-authority/missing.json",
        revision=4,
        predecessor_sha256="sha256:" + "f" * 64,
    )
    with pytest.raises(SecureAuthorityIOError) as predecessor:
        authority.inspect_immutable_graph(
            plans=[root, missing],
                expected_receipts={
                    root.relative_path: identities[root.relative_path],
                    missing.relative_path: _untrusted_receipt(
                        missing,
                        ArtifactIdentity(1, 4, stat.S_IFREG, 1, 1, 1, False),
                    ),
            },
            specified_plan=missing,
        )
    _assert_code(predecessor, "IMMUTABLE_PREDECESSOR_MISSING")


def test_immutable_graph_orphan_cycle_and_cross_operation_are_effect_zero(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=lambda _plan, _fingerprint: True,
        authority_instance_id="authority-instance-1",
    )
    root = _trusted_plan(
        {"generation": 1}, relative_path=".immutable-authority/root.json"
    )
    child = _trusted_plan(
        {"generation": 2},
        relative_path=".immutable-authority/child.json",
        revision=2,
        predecessor_sha256=root.body_sha256,
    )
    identities = {
        root.relative_path: _untrusted_receipt(
            root,
            ArtifactIdentity(1, 1, stat.S_IFREG, 1, 1, 1, False),
        ),
        child.relative_path: _untrusted_receipt(
            child,
            ArtifactIdentity(1, 2, stat.S_IFREG, 1, 1, 1, False),
        ),
    }

    with pytest.raises(SecureAuthorityIOError) as orphan:
        authority.inspect_immutable_graph(
            plans=[root, child],
            expected_receipts=identities,
            specified_plan=root,
        )
    _assert_code(orphan, "IMMUTABLE_ORPHAN_STOP")

    cross_operation = replace(
        child,
        operation_id="fedcba9876543210fedcba9876543210",
    )
    with pytest.raises(SecureAuthorityIOError) as cross:
        authority.inspect_immutable_graph(
            plans=[root, cross_operation],
            expected_receipts={
                root.relative_path: identities[root.relative_path],
                cross_operation.relative_path: identities[child.relative_path],
            },
            specified_plan=cross_operation,
        )
    _assert_code(cross, "IMMUTABLE_CROSS_BINDING_REJECTED")

    cycle_left = replace(
        child,
        relative_path=".immutable-authority/cycle-left.json",
        body_sha256="sha256:" + "a" * 64,
        expected_predecessor_sha256="sha256:" + "b" * 64,
    )
    cycle_right = replace(
        child,
        relative_path=".immutable-authority/cycle-right.json",
        revision=3,
        body_sha256="sha256:" + "b" * 64,
        expected_predecessor_sha256="sha256:" + "a" * 64,
    )
    with pytest.raises(SecureAuthorityIOError) as cycle:
        authority.inspect_immutable_graph(
            plans=[root, cycle_left, cycle_right],
                expected_receipts={
                    root.relative_path: identities[root.relative_path],
                    cycle_left.relative_path: _untrusted_receipt(
                        cycle_left,
                        ArtifactIdentity(1, 3, stat.S_IFREG, 1, 1, 1, False),
                    ),
                    cycle_right.relative_path: _untrusted_receipt(
                        cycle_right,
                        ArtifactIdentity(1, 4, stat.S_IFREG, 1, 1, 1, False),
                    ),
            },
            specified_plan=cycle_left,
        )
    _assert_code(cycle, "IMMUTABLE_CYCLE_STOP")


def test_immutable_publish_uses_private_plan_snapshot_after_verifier_mutates_inputs(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    approved_path = plan.relative_path
    approved_body = plan.body_sha256
    approved_predecessor = plan.expected_predecessor_sha256
    approved_fingerprint = _plan_fingerprint(plan)
    seen: list[TrustedImmutablePlan] = []

    def verifier(candidate: TrustedImmutablePlan, fingerprint: str) -> bool:
        seen.append(candidate)
        document["generation"] = 2
        object.__setattr__(
            candidate,
            "relative_path",
            ".immutable-authority/verifier-foreign.json",
        )
        object.__setattr__(candidate, "body_sha256", "sha256:" + "d" * 64)
        object.__setattr__(
            candidate,
            "expected_predecessor_sha256",
            "sha256:" + "c" * 64,
        )
        object.__setattr__(candidate, "authorization", "verifier-mutated-token")
        object.__setattr__(plan, "relative_path", ".immutable-authority/foreign.json")
        object.__setattr__(plan, "body_sha256", "sha256:" + "f" * 64)
        object.__setattr__(plan, "expected_predecessor_sha256", "sha256:" + "e" * 64)
        object.__setattr__(plan, "authorization", "mutated-token")
        return fingerprint == approved_fingerprint

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=verifier,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)

    assert len(seen) == 1
    assert seen[0] is not plan
    assert receipt.sha256 == approved_body
    assert receipt.predecessor_sha256 == approved_predecessor
    assert receipt.plan_fingerprint == approved_fingerprint
    assert (tmp_path / approved_path).read_bytes() == b'{"generation":1}'
    assert not (tmp_path / ".immutable-authority" / "foreign.json").exists()
    assert not (
        tmp_path / ".immutable-authority" / "verifier-foreign.json"
    ).exists()


def test_immutable_publish_rejects_plan_subclass_before_verifier_or_effect(
    tmp_path: Path,
) -> None:
    class PlanSubclass(TrustedImmutablePlan):
        pass

    document = {"generation": 1}
    (tmp_path / ".immutable-authority").mkdir()
    exact = _trusted_plan(document)
    plan = PlanSubclass(
        exact.relative_path,
        exact.operation_id,
        exact.revision,
        exact.body_sha256,
        exact.expected_predecessor_sha256,
        exact.action,
        exact.build_id,
        exact.backend_id,
        exact.session_id,
        exact.instance_id,
        exact.authorization,
    )
    calls = 0

    def verifier(_: TrustedImmutablePlan, __: str) -> bool:
        nonlocal calls
        calls += 1
        return True

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=verifier,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_immutable_json(document, plan=plan, lease=lease)

    _assert_code(exc, "TRUSTED_GENERATION_PLAN_REQUIRED")
    assert calls == 0
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


def test_immutable_publish_canonicalizes_body_once_and_publishes_that_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai_video_production import secure_authority_io as secure_io

    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        authority_instance_id="authority-instance-1",
    )
    real_canonical = secure_io._canonical_json_bytes
    calls = 0

    def canonical_once(value: object, **kwargs: int) -> bytes:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise AssertionError("caller document was canonicalized twice")
        payload = real_canonical(value, **kwargs)
        document["generation"] = 2
        return payload

    monkeypatch.setattr(secure_io, "_canonical_json_bytes", canonical_once)
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)

    assert calls == 1
    assert receipt.sha256 == plan.body_sha256
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"generation":1}'


def test_trusted_receipt_rejects_self_rehashed_same_body_replacement_identity(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    trust = _ReceiptTrust()
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        immutable_receipt_verifier=trust.verify,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)
    trust.accept(receipt)

    target = tmp_path / plan.relative_path
    replacement = target.with_name("replacement.json")
    replacement.write_bytes(target.read_bytes())
    os.replace(replacement, target)
    replacement_read = SecureAuthorityIO(tmp_path).read_json(plan.relative_path)
    forged = replace(
        receipt,
        identity=replacement_read.identity,
        security_sha256=replacement_read.security_sha256,
        receipt_fingerprint="sha256:" + "0" * 64,
    )
    forged = replace(forged, receipt_fingerprint=_receipt_fingerprint(forged))

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_immutable_json(plan=plan, receipt=forged)

    _assert_code(exc, "TRUSTED_IMMUTABLE_RECEIPT_REJECTED")
    assert target.read_bytes() == b'{"generation":1}'


@pytest.mark.parametrize("subclass_target", ["receipt", "identity"])
def test_immutable_read_rejects_receipt_and_identity_subclasses(
    tmp_path: Path,
    subclass_target: str,
) -> None:
    from dataclasses import replace

    class ReceiptSubclass(ImmutablePublishReceipt):
        pass

    class IdentitySubclass(ArtifactIdentity):
        pass

    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    trust = _ReceiptTrust()
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        immutable_receipt_verifier=trust.verify,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)
    trust.accept(receipt)
    if subclass_target == "receipt":
        candidate = ReceiptSubclass(
            receipt.sha256,
            receipt.predecessor_sha256,
            receipt.byte_count,
            receipt.identity,
            receipt.plan_fingerprint,
            receipt.security_sha256,
            receipt.receipt_fingerprint,
            receipt.version,
        )
        expected_code = "TRUSTED_IMMUTABLE_RECEIPT_REQUIRED"
    else:
        identity = receipt.identity
        candidate = replace(
            receipt,
            identity=IdentitySubclass(
                identity.device,
                identity.inode,
                identity.mode,
                identity.nlink,
                identity.size,
                identity.mtime_ns,
                identity.reparse_point,
            ),
        )
        expected_code = "IMMUTABLE_IDENTITY_REQUIRED"

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_immutable_json(plan=plan, receipt=candidate)

    _assert_code(exc, expected_code)
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"generation":1}'


@pytest.mark.skipif(os.name == "nt", reason="POSIX security commitment test")
def test_immutable_read_rejects_stable_ancestor_security_drift(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    trust = _ReceiptTrust()
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        immutable_receipt_verifier=trust.verify,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)
    trust.accept(receipt)
    os.chmod(tmp_path, stat.S_IMODE(tmp_path.stat().st_mode) ^ stat.S_IRGRP)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_immutable_json(plan=plan, receipt=receipt)

    _assert_code(exc, "IMMUTABLE_BINDING_MISMATCH")
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"generation":1}'


def test_immutable_graph_uses_internal_snapshots_after_verifier_mutates_callers(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    first_plan = _trusted_plan(
        {"generation": 1}, relative_path=".immutable-authority/generation-1.json"
    )
    second_plan = _trusted_plan(
        {"generation": 2},
        relative_path=".immutable-authority/generation-2.json",
        revision=2,
        predecessor_sha256=first_plan.body_sha256,
    )
    receipt_trust = _ReceiptTrust()
    plans = [first_plan, second_plan]
    receipts: dict[str, ImmutablePublishReceipt] = {}
    expected_graph: str | None = None
    expected_specified: str | None = None
    graph_calls = 0

    def graph_verifier(aggregate: str, specified: str) -> bool:
        nonlocal graph_calls
        graph_calls += 1
        plans.clear()
        receipts.clear()
        object.__setattr__(first, "receipt_fingerprint", "sha256:" + "a" * 64)
        object.__setattr__(second, "receipt_fingerprint", "sha256:" + "b" * 64)
        object.__setattr__(
            second_plan,
            "relative_path",
            ".immutable-authority/untrusted.json",
        )
        return aggregate == expected_graph and specified == expected_specified

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(first_plan, second_plan),
        immutable_receipt_verifier=receipt_trust.verify,
        immutable_graph_verifier=graph_verifier,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        first = authority.publish_immutable_json(
            {"generation": 1}, plan=first_plan, lease=lease
        )
        second = authority.publish_immutable_json(
            {"generation": 2}, plan=second_plan, lease=lease
        )
    receipt_trust.accept(first, second)
    receipts.update(
        {
            first_plan.relative_path: first,
            second_plan.relative_path: second,
        }
    )
    expected_graph = "sha256:" + hashlib.sha256(
        "\n".join(
            sorted((first.receipt_fingerprint, second.receipt_fingerprint))
        ).encode("ascii")
    ).hexdigest()
    expected_specified = second.receipt_fingerprint

    inspection = authority.inspect_immutable_graph(
        plans=plans,
        expected_receipts=receipts,
        specified_plan=second_plan,
    )

    assert inspection.inspected_count == 2
    assert graph_calls == 1
    assert not (tmp_path / ".immutable-authority" / "untrusted.json").exists()


def test_immutable_graph_snapshots_every_plan_and_receipt_before_any_callback(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    first_plan = _trusted_plan(
        {"generation": 1}, relative_path=".immutable-authority/generation-1.json"
    )
    second_plan = _trusted_plan(
        {"generation": 2},
        relative_path=".immutable-authority/generation-2.json",
        revision=2,
        predecessor_sha256=first_plan.body_sha256,
    )
    receipts: dict[str, ImmutablePublishReceipt] = {}
    allowed_plans = {
        _plan_fingerprint(first_plan),
        _plan_fingerprint(second_plan),
    }
    receipt_trust = _ReceiptTrust()
    graph_trust = _GraphTrust()
    plan_calls = 0

    def plan_verifier(_: TrustedImmutablePlan, fingerprint: str) -> bool:
        nonlocal plan_calls
        plan_calls += 1
        if plan_calls == 1 and receipts:
            object.__setattr__(
                second_plan,
                "relative_path",
                ".immutable-authority/untrusted.json",
            )
            object.__setattr__(
                receipts[".immutable-authority/generation-2.json"],
                "receipt_fingerprint",
                "sha256:" + "f" * 64,
            )
        return fingerprint in allowed_plans

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=plan_verifier,
        immutable_receipt_verifier=receipt_trust.verify,
        immutable_graph_verifier=graph_trust.verify,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        first = authority.publish_immutable_json(
            {"generation": 1}, plan=first_plan, lease=lease
        )
        second = authority.publish_immutable_json(
            {"generation": 2}, plan=second_plan, lease=lease
        )
    receipt_trust.accept(first, second)
    graph_trust.accept(first, second, specified=second)
    receipts.update(
        {
            first_plan.relative_path: first,
            second_plan.relative_path: second,
        }
    )
    plan_calls = 0

    inspection = authority.inspect_immutable_graph(
        plans=[first_plan, second_plan],
        expected_receipts=receipts,
        specified_plan=second_plan,
    )

    assert inspection.inspected_count == 2
    assert plan_calls == 2
    assert not (tmp_path / ".immutable-authority" / "untrusted.json").exists()


@pytest.mark.parametrize("oversized_input", ["plans", "receipts"])
def test_immutable_graph_rejects_oversized_containers_before_callbacks(
    tmp_path: Path,
    oversized_input: str,
) -> None:
    plan = _trusted_plan({"generation": 1})
    calls = 0

    def verifier(_: TrustedImmutablePlan, __: str) -> bool:
        nonlocal calls
        calls += 1
        return True

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=verifier,
        immutable_receipt_verifier=lambda _: True,
        immutable_graph_verifier=lambda _aggregate, _specified: True,
        authority_instance_id="authority-instance-1",
    )
    plans = [plan] * (1025 if oversized_input == "plans" else 1)
    receipts = (
        {f"key-{index}": object() for index in range(1025)}
        if oversized_input == "receipts"
        else {plan.relative_path: object()}
    )

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.inspect_immutable_graph(
            plans=plans,
            expected_receipts=receipts,  # type: ignore[arg-type]
            specified_plan=plan,
        )

    _assert_code(
        exc,
        "IMMUTABLE_GRAPH_BOUND_REJECTED"
        if oversized_input == "plans"
        else "IMMUTABLE_GRAPH_BINDINGS_REJECTED",
    )
    assert calls == 0
    assert list(tmp_path.iterdir()) == []


def test_direct_private_lock_construction_cannot_self_register_even_with_nonce(
    tmp_path: Path,
) -> None:
    from ai_video_production import secure_authority_io as secure_io

    authority = SecureAuthorityIO(tmp_path)
    nonce = authority._SecureAuthorityIO__lease_issuer_nonce
    forged = secure_io._SecureFileLock(
        authority,
        ".writer.lock",
        "initial",
        nonce,
    )

    with pytest.raises(SecureAuthorityIOError) as exc:
        with forged:
            pass

    _assert_code(exc, "WRITER_LEASE_REQUIRED")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("method_name", "expected_code"),
    [
        ("replace_json_cas", "CAS_ATOMIC_UNAVAILABLE"),
        ("commit_directory_tree", "DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED"),
        ("advance_mutable_phase", "MUTABLE_PHASE_ADVANCE_UNAVAILABLE"),
        ("cleanup_owned_file", "CLEANUP_ATOMIC_UNAVAILABLE"),
    ],
)
def test_unavailable_effect_burns_lease_before_same_context_reuse(
    tmp_path: Path,
    method_name: str,
    expected_code: str,
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    identity = ArtifactIdentity(1, 1, stat.S_IFREG, 1, 2, 1, False)
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as unavailable:
            if method_name == "replace_json_cas":
                authority.replace_json_cas(
                    "target.json",
                    {"x": 1},
                    lease=lease,
                    expected_identity=identity,
                    expected_sha256="sha256:" + "0" * 64,
                )
            elif method_name == "cleanup_owned_file":
                authority.cleanup_owned_file(
                    "target.json",
                    lease=lease,
                    expected_identity=identity,
                    expected_sha256="sha256:" + "0" * 64,
                )
            else:
                getattr(authority, method_name)(
                    "target.json",
                    {"x": 1},
                    lease=lease,
                )
        with pytest.raises(SecureAuthorityIOError) as burned:
            authority.publish_json_noreplace(
                "after-burn.json",
                {"secret": "must-not-be-read"},
                lease=lease,
            )

    _assert_code(unavailable, expected_code)
    _assert_code(burned, "CAPABILITY_BURNED")
    assert not (tmp_path / "target.json").exists()
    assert not (tmp_path / "after-burn.json").exists()


@pytest.mark.parametrize(
    "method_name",
    [
        "replace_json_cas",
        "commit_directory_tree",
        "advance_mutable_phase",
        "cleanup_owned_file",
    ],
)
def test_unavailable_effect_validation_failure_still_burns_active_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
) -> None:
    from ai_video_production import secure_authority_io as secure_io

    authority = SecureAuthorityIO(tmp_path)
    identity = ArtifactIdentity(1, 1, stat.S_IFREG, 1, 2, 1, False)
    real_security_digest = secure_io._fd_security_digest
    calls = 0

    def fail_once(fd: int) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SecureAuthorityIOError("SECURITY_DESCRIPTOR_READ_FAILED")
        return real_security_digest(fd)

    with _writer(authority, tmp_path) as lease:
        monkeypatch.setattr(secure_io, "_fd_security_digest", fail_once)
        with pytest.raises(SecureAuthorityIOError) as validation_failure:
            if method_name == "replace_json_cas":
                authority.replace_json_cas(
                    "target.json",
                    {},
                    lease=lease,
                    expected_identity=identity,
                    expected_sha256="sha256:" + "0" * 64,
                )
            elif method_name == "cleanup_owned_file":
                authority.cleanup_owned_file(
                    "target.json",
                    lease=lease,
                    expected_identity=identity,
                    expected_sha256="sha256:" + "0" * 64,
                )
            else:
                getattr(authority, method_name)("target.json", {}, lease=lease)
        with pytest.raises(SecureAuthorityIOError) as burned:
            authority.publish_json_noreplace("after.json", {}, lease=lease)

    _assert_code(validation_failure, "SECURITY_DESCRIPTOR_READ_FAILED")
    _assert_code(burned, "CAPABILITY_BURNED")
    assert not (tmp_path / "target.json").exists()
    assert not (tmp_path / "after.json").exists()


@pytest.mark.parametrize("effect_kind", ["immutable_body", "raw_path"])
def test_failed_public_publish_burns_lease_before_same_context_reuse(
    tmp_path: Path,
    effect_kind: str,
) -> None:
    document = {"generation": 1}
    plan = _trusted_plan(document)
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        authority_instance_id=plan.instance_id,
    )

    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as rejected:
            if effect_kind == "immutable_body":
                authority.publish_immutable_json(
                    {"generation": 2},
                    plan=plan,
                    lease=lease,
                )
            else:
                authority.publish_json_noreplace(
                    "../outside.json",
                    {"secret": "must-not-be-read"},
                    lease=lease,
                )
        with pytest.raises(SecureAuthorityIOError) as burned:
            authority.publish_json_noreplace(
                "after-rejection.json",
                {"secret": "must-not-be-read"},
                lease=lease,
            )

    _assert_code(
        rejected,
        "IMMUTABLE_BODY_DIGEST_MISMATCH"
        if effect_kind == "immutable_body"
        else "RELATIVE_PATH_REJECTED",
    )
    _assert_code(burned, "CAPABILITY_BURNED")
    assert not (tmp_path / ".immutable-authority" / "generation-1.json").exists()
    assert not (tmp_path / "after-rejection.json").exists()
    assert not (tmp_path.parent / "outside.json").exists()


def test_writer_validation_failure_burns_active_lease_before_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai_video_production import secure_authority_io as secure_io

    authority = SecureAuthorityIO(tmp_path)
    real_security_digest = secure_io._fd_security_digest
    calls = 0

    def fail_once(fd: int) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SecureAuthorityIOError("SECURITY_DESCRIPTOR_READ_FAILED")
        return real_security_digest(fd)

    with _writer(authority, tmp_path) as lease:
        monkeypatch.setattr(secure_io, "_fd_security_digest", fail_once)
        with pytest.raises(SecureAuthorityIOError) as validation_failure:
            authority.publish_json_noreplace("first.json", {}, lease=lease)
        with pytest.raises(SecureAuthorityIOError) as burned:
            authority.publish_json_noreplace("second.json", {}, lease=lease)

    _assert_code(validation_failure, "SECURITY_DESCRIPTOR_READ_FAILED")
    _assert_code(burned, "CAPABILITY_BURNED")
    assert not (tmp_path / "first.json").exists()
    assert not (tmp_path / "second.json").exists()


def test_publish_combined_cleanup_failures_are_completion_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with SecureAuthorityIO(tmp_path).lock(".writer.lock", mode="initial"):
        pass

    def inject(stage: str) -> None:
        if stage == "before_noreplace":
            raise RuntimeError("injected")

    authority = SecureAuthorityIO(tmp_path, _stage_hook=inject)
    real_write_temp = authority._write_temp
    real_pin_parent = authority._pin_parent

    def wrap_temp(*args: object, **kwargs: object):
        lease = real_write_temp(*args, **kwargs)  # type: ignore[arg-type]
        real_close = lease.close

        def close_then_fail() -> None:
            real_close()
            raise SecureAuthorityIOError("TEMP_CLOSE_INJECTED")

        lease.close = close_then_fail  # type: ignore[method-assign]
        return lease

    def wrap_parent(*args: object, **kwargs: object):
        parent = real_pin_parent(*args, **kwargs)  # type: ignore[arg-type]
        if parent.name == "receipt.json":
            real_close = parent.close

            def close_then_fail() -> None:
                real_close()
                raise SecureAuthorityIOError("PARENT_CLOSE_INJECTED")

            parent.close = close_then_fail  # type: ignore[method-assign]
        return parent

    monkeypatch.setattr(authority, "_write_temp", wrap_temp)
    monkeypatch.setattr(authority, "_pin_parent", wrap_parent)
    monkeypatch.setattr(
        authority,
        "_cleanup_temp",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SecureAuthorityIOError("TEMP_CLEANUP_INJECTED")
        ),
    )

    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(authority, tmp_path, "receipt.json", {"x": 1})

    _assert_code(exc, "HANDLE_CLEANUP_UNKNOWN")
    assert exc.value.completion_unknown is True
    assert not (tmp_path / "receipt.json").exists()


def test_publish_never_overwrites_existing_destination(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    target.write_bytes(b"ORIGINAL")

    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(SecureAuthorityIO(tmp_path), tmp_path, "receipt.json", {"new": True})

    _assert_code(exc, "DESTINATION_EXISTS")
    assert target.read_bytes() == b"ORIGINAL"


def test_publish_loses_destination_race_without_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"

    def hook(stage: str) -> None:
        if stage == "before_noreplace":
            target.write_bytes(b"RACE-WINNER")

    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(
            SecureAuthorityIO(tmp_path, _stage_hook=hook),
            tmp_path,
            "receipt.json",
            {"new": True},
        )

    _assert_code(exc, "DESTINATION_EXISTS")
    assert target.read_bytes() == b"RACE-WINNER"
    assert list(tmp_path.glob(".authority-*.tmp")) == []


@pytest.mark.skipif(os.name == "nt", reason="Windows live handle denies replacement")
def test_publish_detects_post_readback_swap(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"

    def hook(stage: str) -> None:
        if stage == "published_readback_complete":
            replacement = tmp_path / "replacement.json"
            replacement.write_bytes(b"FOREIGN")
            os.replace(replacement, target)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(
            SecureAuthorityIO(tmp_path, _stage_hook=hook),
            tmp_path,
            "receipt.json",
            {"new": True},
        )

    _assert_code(exc, "PUBLISH_COMMIT_UNKNOWN")
    assert exc.value.completion_unknown is True
    assert target.read_bytes() == b"FOREIGN"


@pytest.mark.skipif(os.name == "nt", reason="POSIX unnamed temporary file")
def test_posix_unnamed_temp_ignores_foreign_random_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    foreign = tmp_path / (".authority-" + "a" * 32 + ".tmp")
    foreign.write_bytes(b"FOREIGN")
    monkeypatch.setattr(
        "ai_video_production.secure_authority_io.secrets.token_hex", lambda _: "a" * 32
    )

    receipt = _publish(SecureAuthorityIO(tmp_path), tmp_path, "receipt.json", {"new": True})

    assert foreign.read_bytes() == b"FOREIGN"
    assert receipt.identity.nlink == 1
    assert (tmp_path / "receipt.json").read_text(encoding="utf-8") == '{"new":true}'


def test_publish_file_fsync_failure_cleans_only_owned_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with authority.lock(".writer.lock", mode="initial"):
        pass

    def fail_fsync(_: int) -> None:
        raise OSError("private path and body must not escape")

    monkeypatch.setattr("ai_video_production.secure_authority_io.os.fsync", fail_fsync)
    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(authority, tmp_path, "receipt.json", {"x": 1})

    _assert_code(exc, "FILE_DURABILITY_FAILED")
    assert [path.name for path in tmp_path.iterdir()] == [".writer.lock"]


def test_publish_cleanup_failure_still_closes_temp_and_parent_handles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def inject(stage: str) -> None:
        if stage == "before_noreplace":
            raise RuntimeError("injected")

    authority = SecureAuthorityIO(tmp_path, _stage_hook=inject)
    with SecureAuthorityIO(tmp_path).lock(".writer.lock", mode="initial"):
        pass
    captured_temp: list[int] = []
    captured_parent: list[int] = []
    real_write_temp = authority._write_temp
    real_pin_parent = authority._pin_parent

    def capture_temp(*args: object, **kwargs: object):
        lease = real_write_temp(*args, **kwargs)  # type: ignore[arg-type]
        captured_temp.append(lease.fd)
        return lease

    def capture_parent(*args: object, **kwargs: object):
        parent = real_pin_parent(*args, **kwargs)  # type: ignore[arg-type]
        captured_parent.extend(fd for _, fd, _, _ in parent.pinned)
        return parent

    def reject_cleanup(*_: object, **__: object) -> None:
        raise SecureAuthorityIOError("TEMP_CLEANUP_INJECTED")

    monkeypatch.setattr(authority, "_write_temp", capture_temp)
    monkeypatch.setattr(authority, "_pin_parent", capture_parent)
    monkeypatch.setattr(authority, "_cleanup_temp", reject_cleanup)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(authority, tmp_path, "receipt.json", {"x": 1})

    _assert_code(exc, "TEMP_CLEANUP_INJECTED")
    assert captured_temp and captured_parent
    for fd in (*captured_temp, *captured_parent):
        with pytest.raises(OSError):
            os.fstat(fd)
    assert not (tmp_path / "receipt.json").exists()


def test_publish_post_commit_parent_close_failure_is_completion_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with authority.lock(".writer.lock", mode="initial"):
        pass
    real_pin_parent = authority._pin_parent

    def inject_close_failure(relative_path: object):
        parent = real_pin_parent(relative_path)  # type: ignore[arg-type]
        if str(relative_path) == "receipt.json":
            real_close = parent.close

            def close_then_fail() -> None:
                real_close()
                raise SecureAuthorityIOError("ANCESTOR_CLOSE_INJECTED")

            parent.close = close_then_fail  # type: ignore[method-assign]
        return parent

    monkeypatch.setattr(authority, "_pin_parent", inject_close_failure)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(authority, tmp_path, "receipt.json", {"x": 1})

    _assert_code(exc, "PUBLISH_COMMIT_UNKNOWN")
    assert exc.value.completion_unknown is True
    assert (tmp_path / "receipt.json").read_text(encoding="utf-8") == '{"x":1}'


@pytest.mark.skipif(os.name == "nt", reason="POSIX durability classification")
def test_posix_publish_directory_fsync_failure_is_completion_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with authority.lock(".writer.lock", mode="initial"):
        pass

    real_fsync = os.fsync
    failed = False

    def fail_first_directory(fd: int) -> None:
        nonlocal failed
        if stat.S_ISDIR(os.fstat(fd).st_mode) and not failed:
            failed = True
            raise OSError("private path and body must not escape")
        real_fsync(fd)

    monkeypatch.setattr(
        "ai_video_production.secure_authority_io.os.fsync", fail_first_directory
    )
    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(authority, tmp_path, "receipt.json", {"x": 1})

    _assert_code(exc, "PUBLISH_ROLLBACK_UNAVAILABLE")
    assert exc.value.completion_unknown is True
    assert (tmp_path / "receipt.json").read_text(encoding="utf-8") == '{"x":1}'
    assert sorted(path.name for path in tmp_path.iterdir()) == [".writer.lock", "receipt.json"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX unnamed temporary file")
def test_posix_unnamed_temp_has_no_substitutable_namespace_entry(tmp_path: Path) -> None:
    base = SecureAuthorityIO(tmp_path)
    with base.lock(".writer.lock", mode="initial"):
        pass

    def hook(stage: str) -> None:
        if stage == "temp_durable":
            assert list(tmp_path.glob(".authority-*.tmp")) == []
            raise RuntimeError("injected")

    with pytest.raises(RuntimeError, match="injected"):
        _publish(
            SecureAuthorityIO(tmp_path, _stage_hook=hook),
            tmp_path,
            "receipt.json",
            {"new": True},
        )

    assert list(tmp_path.glob(".authority-*.tmp")) == []
    assert not (tmp_path / "receipt.json").exists()


def test_posix_cas_is_fail_closed_before_effect(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    target.write_text('{"version":1}', encoding="utf-8")
    authority = SecureAuthorityIO(tmp_path)
    current = authority.read_json("receipt.json")

    with pytest.raises(SecureAuthorityIOError) as exc:
        _replace(
            authority,
            tmp_path,
            "receipt.json",
            {"version": 2},
            expected_identity=current.identity,
            expected_sha256=current.sha256,
        )

    _assert_code(exc, "CAS_ATOMIC_UNAVAILABLE")
    assert exc.value.completion_unknown is False
    assert exc.value.authority_created is False
    assert target.read_text(encoding="utf-8") == '{"version":1}'
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_cas_unavailable_precedes_payload_traversal_and_hook_seams(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    target.write_text('{"version":1}', encoding="utf-8")
    baseline = SecureAuthorityIO(tmp_path).read_json("receipt.json")
    with SecureAuthorityIO(tmp_path).lock(".writer.lock", mode="initial"):
        pass
    cyclic: list[object] = []
    cyclic.append(cyclic)
    observed: list[str] = []
    authority = SecureAuthorityIO(tmp_path, _stage_hook=observed.append)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _replace(
            authority,
            tmp_path,
            "receipt.json",
            cyclic,
            expected_identity=baseline.identity,
            expected_sha256=baseline.sha256,
        )

    _assert_code(exc, "CAS_ATOMIC_UNAVAILABLE")
    assert observed == ["before_lock_open", "lock_acquired"]
    assert target.read_text(encoding="utf-8") == '{"version":1}'
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_cas_rejects_wrong_bytes_without_mutation(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    target.write_text('{"version":1}', encoding="utf-8")
    authority = SecureAuthorityIO(tmp_path)
    current = authority.read_json("receipt.json")

    with pytest.raises(SecureAuthorityIOError) as exc:
        _replace(
            authority,
            tmp_path,
            "receipt.json",
            {"version": 2},
            expected_identity=current.identity,
            expected_sha256="sha256:" + "0" * 64,
        )

    _assert_code(exc, "CAS_ATOMIC_UNAVAILABLE")
    assert target.read_text(encoding="utf-8") == '{"version":1}'


def test_cas_rejects_same_bytes_from_different_inode(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path)
    (tmp_path / "first.json").write_text('{"same":true}', encoding="utf-8")
    (tmp_path / "second.json").write_text('{"same":true}', encoding="utf-8")
    first = authority.read_json("first.json")
    second = authority.read_json("second.json")
    assert first.sha256 == second.sha256
    assert first.identity.inode != second.identity.inode

    with pytest.raises(SecureAuthorityIOError) as exc:
        _replace(
            authority,
            tmp_path,
            "second.json",
            {"new": True},
            expected_identity=first.identity,
            expected_sha256=first.sha256,
        )

    _assert_code(exc, "CAS_ATOMIC_UNAVAILABLE")
    assert (tmp_path / "second.json").read_text(encoding="utf-8") == '{"same":true}'


def test_cas_detects_substitution_before_commit(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    target.write_text('{"version":1}', encoding="utf-8")
    baseline = SecureAuthorityIO(tmp_path).read_json("receipt.json")

    def hook(stage: str) -> None:
        if stage == "before_cas_recheck":
            replacement = tmp_path / "replacement.json"
            replacement.write_text('{"attacker":true}', encoding="utf-8")
            os.replace(replacement, target)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _replace(
            SecureAuthorityIO(tmp_path, _stage_hook=hook),
            tmp_path,
            "receipt.json",
            {"version": 2},
            expected_identity=baseline.identity,
            expected_sha256=baseline.sha256,
        )

    _assert_code(exc, "CAS_ATOMIC_UNAVAILABLE")
    assert target.read_text(encoding="utf-8") == '{"version":1}'
    assert not (tmp_path / "replacement.json").exists()


def test_cas_detects_last_seam_substitution_without_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    target.write_text('{"version":1}', encoding="utf-8")
    baseline = SecureAuthorityIO(tmp_path).read_json("receipt.json")

    def hook(stage: str) -> None:
        if stage == "before_cas_replace":
            replacement = tmp_path / "replacement.json"
            replacement.write_text('{"foreign":true}', encoding="utf-8")
            os.replace(replacement, target)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _replace(
            SecureAuthorityIO(tmp_path, _stage_hook=hook),
            tmp_path,
            "receipt.json",
            {"version": 2},
            expected_identity=baseline.identity,
            expected_sha256=baseline.sha256,
        )

    _assert_code(exc, "CAS_ATOMIC_UNAVAILABLE")
    assert target.read_text(encoding="utf-8") == '{"version":1}'
    assert not (tmp_path / "replacement.json").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX exact cleanup is unavailable")
def test_posix_owned_cleanup_is_fail_closed_and_preserves_target(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path)
    published = _publish(authority, tmp_path, "pending.json", {"pending": True})

    with pytest.raises(SecureAuthorityIOError) as exc:
        _cleanup(
            authority,
            tmp_path,
            "pending.json",
            expected_identity=published.identity,
            expected_sha256=published.sha256,
        )

    _assert_code(exc, "CLEANUP_ATOMIC_UNAVAILABLE")
    assert exc.value.completion_unknown is False
    assert exc.value.authority_created is False
    assert (tmp_path / "pending.json").read_text(encoding="utf-8") == '{"pending":true}'


def test_immutable_only_discovery_methods_are_typed_never_return() -> None:
    cas_hints = get_type_hints(SecureAuthorityIO.replace_json_cas)
    cleanup_hints = get_type_hints(SecureAuthorityIO.cleanup_owned_file)
    tree_hints = get_type_hints(SecureAuthorityIO.commit_directory_tree)
    phase_hints = get_type_hints(SecureAuthorityIO.advance_mutable_phase)

    assert cas_hints["return"] is NoReturn
    assert cleanup_hints["return"] is NoReturn
    assert tree_hints["return"] is NoReturn
    assert phase_hints["return"] is NoReturn


@pytest.mark.parametrize(
    ("method_name", "expected_code"),
    [
        ("commit_directory_tree", "DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED"),
        ("advance_mutable_phase", "MUTABLE_PHASE_ADVANCE_UNAVAILABLE"),
    ],
)
def test_out_of_scope_authority_discovery_is_effect_zero_before_body_or_path(
    tmp_path: Path, method_name: str, expected_code: str
) -> None:
    observed: list[str] = []
    authority = SecureAuthorityIO(tmp_path, _stage_hook=observed.append)
    cyclic: list[object] = []
    cyclic.append(cyclic)

    with _writer(authority, tmp_path) as lease:
        stages_before_discovery = list(observed)
        method = getattr(authority, method_name)
        with pytest.raises(SecureAuthorityIOError) as exc:
            method("../private-tree", cyclic, lease=lease)
        assert observed == stages_before_discovery

    _assert_code(exc, expected_code)
    assert exc.value.authority_created is False
    assert exc.value.currentness_selected is False
    assert exc.value.directory_tree_status_code == "DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED"
    assert exc.value.mutable_phase_status_code == "MUTABLE_PHASE_ADVANCE_UNAVAILABLE"
    assert (
        exc.value.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == [".writer.lock"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX exact cleanup is unavailable")
def test_owned_cleanup_detects_substitution_and_preserves_it(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path)
    published = _publish(authority, tmp_path, "pending.json", {"pending": True})
    target = tmp_path / "pending.json"

    def hook(stage: str) -> None:
        if stage == "before_owned_cleanup":
            replacement = tmp_path / "replacement.json"
            replacement.write_text('{"owned":false}', encoding="utf-8")
            os.replace(replacement, target)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _cleanup(
            SecureAuthorityIO(tmp_path, _stage_hook=hook),
            tmp_path,
            "pending.json",
            expected_identity=published.identity,
            expected_sha256=published.sha256,
        )

    _assert_code(exc, "CLEANUP_ATOMIC_UNAVAILABLE")
    assert target.read_text(encoding="utf-8") == '{"pending":true}'
    assert not (tmp_path / "replacement.json").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX exact cleanup is unavailable")
def test_owned_cleanup_detects_last_seam_substitution(tmp_path: Path) -> None:
    published = _publish(SecureAuthorityIO(tmp_path), tmp_path, "pending.json", {"x": 1})
    target = tmp_path / "pending.json"

    def hook(stage: str) -> None:
        if stage == "owned_cleanup_rechecked":
            replacement = tmp_path / "replacement.json"
            replacement.write_bytes(b"FOREIGN")
            os.replace(replacement, target)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _cleanup(
            SecureAuthorityIO(tmp_path, _stage_hook=hook),
            tmp_path,
            "pending.json",
            expected_identity=published.identity,
            expected_sha256=published.sha256,
        )

    _assert_code(exc, "CLEANUP_ATOMIC_UNAVAILABLE")
    assert target.read_bytes() == b'{"x":1}'
    assert not (tmp_path / "replacement.json").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX exact cleanup is unavailable")
def test_owned_cleanup_rejects_unknown_expected_identity(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path)
    first = _publish(authority, tmp_path, "first.json", {"x": 1})
    _publish(authority, tmp_path, "unknown.json", {"x": 1})

    with pytest.raises(SecureAuthorityIOError) as exc:
        _cleanup(
            authority,
            tmp_path,
            "unknown.json",
            expected_identity=first.identity,
            expected_sha256=first.sha256,
        )

    _assert_code(exc, "CLEANUP_ATOMIC_UNAVAILABLE")
    assert (tmp_path / "unknown.json").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX exact cleanup is unavailable")
def test_owned_cleanup_rejects_hardlink_without_unlink(tmp_path: Path) -> None:
    target = tmp_path / "pending.json"
    target.write_text("{}", encoding="utf-8")
    os.link(target, tmp_path / "other.json")
    authority = SecureAuthorityIO(tmp_path)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _cleanup(
            authority,
            tmp_path,
            "pending.json",
            expected_identity=ArtifactIdentity(0, 0, 0, 0, 0, 0, False),
            expected_sha256="sha256:" + "0" * 64,
        )

    _assert_code(exc, "CLEANUP_ATOMIC_UNAVAILABLE")
    assert target.exists()
    assert (tmp_path / "other.json").exists()


def test_errors_do_not_include_path_or_document_body(tmp_path: Path) -> None:
    private_name = "private-owner-path.json"
    private_body = "private-body-secret"
    (tmp_path / private_name).write_text(private_body, encoding="utf-8")

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json(private_name)

    rendered = f"{exc.value!s} {exc.value!r}"
    assert private_name not in rendered
    assert private_body not in rendered
    assert rendered.count("STRICT_JSON_REJECTED") == 2


def test_os_error_filename_is_detached_at_public_read_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai_video_production import secure_authority_io as secure_io

    private_name = "private-os-owner-path.json"
    private_target = tmp_path / private_name
    real_lstat = secure_io.os.lstat

    def rejecting_lstat(path: object, *args: object, **kwargs: object):
        if os.path.abspath(os.fspath(path)) == os.path.abspath(os.fspath(private_target)):
            raise OSError(5, "private-os-error-text", os.fspath(private_target))
        return real_lstat(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(secure_io.os, "lstat", rejecting_lstat)
    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json(private_name)

    _assert_code(exc, "FILE_LSTAT_FAILED")
    assert private_name not in repr(exc.value)


def test_plan_verifier_exception_is_detached_at_public_publish_boundary(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)

    def exploding_verifier(candidate: TrustedImmutablePlan, fingerprint: str) -> bool:
        raise RuntimeError("private-plan-verifier-token")

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=exploding_verifier,
        authority_instance_id=plan.instance_id,
    )
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_immutable_json(document, plan=plan, lease=lease)

    _assert_code(exc, "TRUSTED_GENERATION_PLAN_REJECTED")
    assert "private-plan-verifier-token" not in repr(exc.value)
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


def test_receipt_verifier_exception_is_detached_at_public_read_boundary(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)

    def exploding_receipt_verifier(fingerprint: str) -> bool:
        raise RuntimeError("private-receipt-verifier-token")

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        immutable_receipt_verifier=exploding_receipt_verifier,
        authority_instance_id=plan.instance_id,
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_immutable_json(plan=plan, receipt=receipt)

    _assert_code(exc, "TRUSTED_IMMUTABLE_RECEIPT_REJECTED")
    assert "private-receipt-verifier-token" not in repr(exc.value)


def test_graph_verifier_exception_is_detached_at_public_inspection_boundary(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    receipt_trust = _ReceiptTrust()

    def exploding_graph_verifier(aggregate: str, specified: str) -> bool:
        raise RuntimeError("private-graph-verifier-token")

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        immutable_receipt_verifier=receipt_trust.verify,
        immutable_graph_verifier=exploding_graph_verifier,
        authority_instance_id=plan.instance_id,
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)
    receipt_trust.accept(receipt)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.inspect_immutable_graph(
            plans=[plan],
            expected_receipts={plan.relative_path: receipt},
            specified_plan=plan,
        )

    _assert_code(exc, "TRUSTED_IMMUTABLE_GRAPH_REJECTED")
    assert "private-graph-verifier-token" not in repr(exc.value)


def test_public_error_detaches_caller_ambient_exception(tmp_path: Path) -> None:
    (tmp_path / "receipt.json").write_text("private-json-body", encoding="utf-8")

    try:
        raise RuntimeError("private-ambient-token")
    except RuntimeError:
        with pytest.raises(SecureAuthorityIOError) as exc:
            SecureAuthorityIO(tmp_path).read_json("receipt.json")

    _assert_code(exc, "STRICT_JSON_REJECTED")
    assert "private-ambient-token" not in repr(exc.value)


def test_lock_cleanup_error_detaches_private_body_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    real_unlock = authority._unlock_fd

    def unlock_then_fail(fd: int) -> None:
        real_unlock(fd)
        raise SecureAuthorityIOError("private-lock-cleanup-token")

    monkeypatch.setattr(authority, "_unlock_fd", unlock_then_fail)
    with pytest.raises(SecureAuthorityIOError) as exc:
        with authority.lock(".writer.lock", mode="initial"):
            raise RuntimeError("private-lock-body-token")

    _assert_code(exc, "LOCK_CLEANUP_UNKNOWN")
    assert exc.value.completion_unknown is True
    rendered = repr(exc.value)
    assert "private-lock-cleanup-token" not in rendered
    assert "private-lock-body-token" not in rendered


def test_read_json_returns_deep_immutable_non_authority_snapshot(tmp_path: Path) -> None:
    (tmp_path / "receipt.json").write_text(
        '{"nested":{"items":[1,2]}}', encoding="utf-8"
    )

    result = SecureAuthorityIO(tmp_path).read_json("receipt.json")

    assert result.authority_created is False
    assert result.identity.authority_created is False
    assert result.identity.currentness_selected is False
    assert result.identity.status_code == "CURRENT_HEAD_AUTHORITY_NOT_CREATED"
    assert (
        result.identity.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    with pytest.raises(TypeError):
        result.document["nested"]["items"][0] = 9
    with pytest.raises(Exception) as exc:
        result.document["nested"]._items = ()
    assert type(exc.value).__name__ == "FrozenInstanceError"
    assert result.document == {"nested": {"items": [1, 2]}}


def test_publish_rejects_cyclic_caller_value_before_temp_creation(tmp_path: Path) -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    authority = SecureAuthorityIO(tmp_path)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(authority, tmp_path, "receipt.json", cyclic)

    _assert_code(exc, "JSON_CYCLE_REJECTED")
    assert not (tmp_path / "receipt.json").exists()
    assert not any(path.name.startswith(".authority-") for path in tmp_path.iterdir())


def test_publish_rejects_wide_caller_value_before_copy_or_temp(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path, max_json_nodes=4)

    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(authority, tmp_path, "receipt.json", [1] * 100_000)

    _assert_code(exc, "JSON_NODE_BOUND_EXCEEDED")
    assert not (tmp_path / "receipt.json").exists()
    assert not any(path.name.startswith(".authority-") for path in tmp_path.iterdir())


def test_publish_rejects_non_builtin_container_without_repr_leak(tmp_path: Path) -> None:
    class SensitiveList(list):
        def __repr__(self) -> str:
            return "private-body-secret"

    authority = SecureAuthorityIO(tmp_path)
    with pytest.raises(SecureAuthorityIOError) as exc:
        _publish(authority, tmp_path, "receipt.json", SensitiveList([1]))

    _assert_code(exc, "JSON_VALUE_REJECTED")
    assert "private-body-secret" not in repr(exc.value)
    assert not (tmp_path / "receipt.json").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX unnamed temporary file")
def test_posix_publish_has_no_live_temp_unlink_seam(tmp_path: Path) -> None:
    base = SecureAuthorityIO(tmp_path)
    with base.lock(".writer.lock", mode="initial"):
        pass
    seam_seen: list[bool] = []

    def hook(stage: str) -> None:
        if stage == "before_live_unlink":
            seam_seen.append(True)

    authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
    with authority.lock(".writer.lock", mode="existing") as lease:
        authority.publish_json_noreplace("receipt.json", {"x": 1}, lease=lease)

    assert seam_seen == []
    assert list(tmp_path.glob(".authority-*.tmp")) == []
    assert (tmp_path / "receipt.json").read_text(encoding="utf-8") == '{"x":1}'


@pytest.mark.skipif(os.name == "nt", reason="POSIX exact cleanup is unavailable")
def test_owned_cleanup_live_unlink_swap_preserves_foreign_target(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path)
    published = _publish(authority, tmp_path, "pending.json", {"x": 1})
    swapped = False

    def hook(stage: str) -> None:
        nonlocal swapped
        if stage != "before_live_unlink" or swapped:
            return
        foreign = tmp_path / "foreign.json"
        foreign.write_bytes(b"FOREIGN")
        os.replace(foreign, tmp_path / "pending.json")
        swapped = True

    authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
    with pytest.raises(SecureAuthorityIOError) as exc:
        _cleanup(
            authority,
            tmp_path,
            "pending.json",
            expected_identity=published.identity,
            expected_sha256=published.sha256,
        )

    _assert_code(exc, "CLEANUP_ATOMIC_UNAVAILABLE")
    assert swapped is False
    assert (tmp_path / "pending.json").read_bytes() == b'{"x":1}'


@pytest.mark.skipif(os.name == "nt", reason="POSIX native no-replace fault")
def test_posix_publish_classifies_helper_fault_after_real_noreplace_as_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with authority.lock(".writer.lock", mode="initial"):
        pass
    real_rename = authority._rename_noreplace

    def publish_then_fail(parent: object, lease: object) -> None:
        real_rename(parent, lease)  # type: ignore[arg-type]
        raise RuntimeError("private-after-publish")

    monkeypatch.setattr(authority, "_rename_noreplace", publish_then_fail)
    with authority.lock(".writer.lock", mode="existing") as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_json_noreplace(
                "receipt.json",
                {"x": 1},
                lease=lease,
            )

    _assert_code(exc, "PUBLISH_COMMIT_UNKNOWN")
    assert exc.value.completion_unknown is True
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None
    assert (tmp_path / "receipt.json").read_bytes() == b'{"x":1}'


@pytest.mark.skipif(os.name == "nt", reason="POSIX native no-replace fault")
def test_posix_initial_lock_classifies_helper_fault_after_real_noreplace_as_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    real_rename = authority._rename_noreplace

    def publish_then_fail(parent: object, lease: object) -> None:
        real_rename(parent, lease)  # type: ignore[arg-type]
        raise RuntimeError("private-after-lock-publish")

    monkeypatch.setattr(authority, "_rename_noreplace", publish_then_fail)
    with pytest.raises(SecureAuthorityIOError) as exc:
        with authority.lock(".writer.lock", mode="initial"):
            pass

    _assert_code(exc, "LOCK_INITIALIZATION_UNKNOWN")
    assert exc.value.completion_unknown is True
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None
    assert (tmp_path / ".writer.lock").read_bytes() == b"\0"


@pytest.mark.parametrize(
    "filename",
    ["generation with space.json", "generation-é.json", "g" * 129],
)
def test_immutable_plan_rejects_names_graph_scan_cannot_admit(
    tmp_path: Path,
    filename: str,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(
        document,
        relative_path=f".immutable-authority/{filename}",
    )
    verifier_calls = 0

    def verifier(_: TrustedImmutablePlan, __: str) -> bool:
        nonlocal verifier_calls
        verifier_calls += 1
        return True

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=verifier,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_immutable_json(document, plan=plan, lease=lease)

    _assert_code(exc, "IMMUTABLE_COORDINATE_REJECTED")
    assert verifier_calls == 0
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


def test_immutable_plan_filename_grammar_round_trips_through_graph_scan(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(
        document,
        relative_path=".immutable-authority/generation-1_OK.json",
    )
    receipt_trust = _ReceiptTrust()
    graph_trust = _GraphTrust()
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        immutable_receipt_verifier=receipt_trust.verify,
        immutable_graph_verifier=graph_trust.verify,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)
    receipt_trust.accept(receipt)
    graph_trust.accept(receipt, specified=receipt)

    result = authority.inspect_immutable_graph(
        plans=[plan],
        expected_receipts={plan.relative_path: receipt},
        specified_plan=plan,
    )

    assert result.inspected_count == 1


@pytest.mark.parametrize(
    ("kind", "expected_code"),
    [
        ("oversized_body", "IMMUTABLE_RECEIPT_REJECTED"),
        ("oversized_identity", "IMMUTABLE_IDENTITY_REQUIRED"),
    ],
)
def test_immutable_receipt_integer_bounds_precede_fingerprint_canonicalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    expected_code: str,
) -> None:
    from dataclasses import replace
    from ai_video_production import secure_authority_io as secure_io

    document = {"generation": 1}
    plan = _trusted_plan(document)
    base = _untrusted_receipt(
        plan,
        ArtifactIdentity(1, 1, stat.S_IFREG, 1, 1, 1, False),
    )
    if kind == "oversized_body":
        size = 1024 * 1024 + 1
        receipt = replace(
            base,
            byte_count=size,
            identity=replace(base.identity, size=size),
        )
    else:
        receipt = replace(
            base,
            identity=replace(base.identity, inode=1 << 100_000),
        )
    receipt_verifier_calls = 0

    def receipt_verifier(_: str) -> bool:
        nonlocal receipt_verifier_calls
        receipt_verifier_calls += 1
        return True

    def forbidden_fingerprint(**_: object) -> str:
        raise AssertionError("unbounded receipt reached canonicalization")

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(plan),
        immutable_receipt_verifier=receipt_verifier,
        authority_instance_id="authority-instance-1",
    )
    monkeypatch.setattr(
        secure_io,
        "_immutable_receipt_fingerprint",
        forbidden_fingerprint,
    )
    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_immutable_json(plan=plan, receipt=receipt)

    _assert_code(exc, expected_code)
    assert receipt_verifier_calls == 0


def test_custom_pathlike_exception_is_normalized_without_body_leak(tmp_path: Path) -> None:
    class ExplodingPath:
        def __fspath__(self) -> str:
            raise RuntimeError("private-path-body")

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json(ExplodingPath())  # type: ignore[arg-type]

    _assert_code(exc, "RELATIVE_PATH_REJECTED")
    assert "private-path-body" not in repr(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None
