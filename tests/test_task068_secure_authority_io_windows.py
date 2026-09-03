from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat

import pytest

from ai_video_production.secure_authority_io import (
    ImmutablePublishReceipt,
    SecureAuthorityIO,
    SecureAuthorityIOError,
    TrustedImmutablePlan,
)


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows-native authority I/O tests")


@contextmanager
def _writer(authority: SecureAuthorityIO, root: Path):
    mode = "existing" if (root / ".writer.lock").exists() else "initial"
    with authority.lock(".writer.lock", mode=mode) as lease:
        yield lease


def _trusted_plan(
    document: object, *, revision: int = 1, predecessor: str | None = None
) -> TrustedImmutablePlan:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return TrustedImmutablePlan(
        relative_path=f".immutable-authority/generation-{revision}.json",
        operation_id="0123456789abcdef0123456789abcdef",
        revision=revision,
        body_sha256="sha256:" + hashlib.sha256(payload).hexdigest(),
        expected_predecessor_sha256=predecessor or "sha256:" + "0" * 64,
        action="GENERATION",
        build_id="build-1",
        backend_id="backend-1",
        session_id="session-1",
        instance_id="authority-instance-1",
        authorization="authorized-plan-token",
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


def _exact_graph_verifier(
    *plans: TrustedImmutablePlan, specified: TrustedImmutablePlan
):
    graph = "sha256:" + hashlib.sha256(
        "\n".join(sorted(_plan_fingerprint(plan) for plan in plans)).encode("ascii")
    ).hexdigest()
    expected = (graph, _plan_fingerprint(specified))
    return lambda graph_fingerprint, specified_fingerprint: (
        graph_fingerprint,
        specified_fingerprint,
    ) == expected


class _ReceiptTrust:
    def __init__(self) -> None:
        self.allowed: set[str] = set()

    def verify(self, fingerprint: str) -> bool:
        return fingerprint in self.allowed

    def accept(self, *receipts: ImmutablePublishReceipt) -> None:
        self.allowed.update(receipt.receipt_fingerprint for receipt in receipts)


def _assert_detached_error(
    exc: pytest.ExceptionInfo[SecureAuthorityIOError],
    code: str,
    *private_values: str,
) -> None:
    assert exc.value.code == code
    assert str(exc.value) == code
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None
    rendered = repr(exc.value)
    assert all(value not in rendered for value in private_values)


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


def test_windows_read_handle_is_noninheritable_and_reparse_safe(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    target.write_text("{}", encoding="utf-8")
    observations: list[bool] = []

    def hook(stage: str) -> None:
        if stage == "read_bound":
            observations.append(True)

    result = SecureAuthorityIO(tmp_path, _stage_hook=hook).read_json("receipt.json")

    assert observations == [True]
    assert result.identity.reparse_point is False
    assert result.identity.nlink == 1
    assert result.identity.inode != 0


def test_windows_pinned_read_handle_blocks_target_replacement(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    target.write_text('{"version":1}', encoding="utf-8")
    attempted: list[bool] = []

    def hook(stage: str) -> None:
        if stage != "read_complete":
            return
        foreign = tmp_path / "foreign.json"
        foreign.write_text('{"version":2}', encoding="utf-8")
        with pytest.raises(PermissionError):
            os.replace(foreign, target)
        attempted.append(True)

    result = SecureAuthorityIO(tmp_path, _stage_hook=hook).read_json("receipt.json")

    assert attempted == [True]
    assert result.document["version"] == 1
    assert target.read_text(encoding="utf-8") == '{"version":1}'
    assert (tmp_path / "foreign.json").read_text(encoding="utf-8") == '{"version":2}'


def test_windows_pinned_read_ancestor_blocks_namespace_replacement(tmp_path: Path) -> None:
    parent = tmp_path / "authority"
    parent.mkdir()
    (parent / "receipt.json").write_text("{}", encoding="utf-8")
    attempted: list[bool] = []

    def hook(stage: str) -> None:
        if stage != "read_complete":
            return
        with pytest.raises(PermissionError):
            os.replace(parent, tmp_path / "moved-authority")
        attempted.append(True)

    result = SecureAuthorityIO(tmp_path, _stage_hook=hook).read_json(
        "authority/receipt.json"
    )

    assert attempted == [True]
    assert dict(result.document) == {}
    assert parent.is_dir()
    assert not (tmp_path / "moved-authority").exists()


def test_windows_live_existing_lock_handle_blocks_inode_replacement(tmp_path: Path) -> None:
    target = tmp_path / "authority.lock"
    target.write_bytes(b"\0")
    attempted: list[bool] = []

    def hook(stage: str) -> None:
        if stage != "lock_acquired":
            return
        foreign = tmp_path / "foreign.lock"
        foreign.write_bytes(b"\0")
        with pytest.raises(PermissionError):
            os.replace(foreign, target)
        attempted.append(True)

    with SecureAuthorityIO(tmp_path, _stage_hook=hook).lock(
        "authority.lock", mode="existing"
    ) as lease:
        assert lease.identity is not None

    assert attempted == [True]
    assert target.read_bytes() == b"\0"
    assert (tmp_path / "foreign.lock").read_bytes() == b"\0"


def test_windows_read_rejects_security_descriptor_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "receipt.json"
    target.write_text("{}", encoding="utf-8")
    target_calls = 0

    def drifting_digest(fd: int) -> str:
        nonlocal target_calls
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            return "sha256:" + "a" * 64
        target_calls += 1
        return "sha256:" + ("1" if target_calls == 1 else "2") * 64

    monkeypatch.setattr(
        "ai_video_production.secure_authority_io._fd_security_digest",
        drifting_digest,
    )

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("receipt.json")

    assert exc.value.code == "FILE_SECURITY_DRIFT"
    assert exc.value.authority_created is False
    assert exc.value.currentness_selected is False


def test_windows_path_component_policy_is_effect_zero(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path)

    for relative in (
        "file:stream",
        "CON",
        "aux.txt",
        "trailing.",
        "trailing ",
        "private\nreceipt.json",
        "a" * 256,
    ):
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.read_json(relative)
        assert exc.value.code == "RELATIVE_PATH_REJECTED"

    assert list(tmp_path.iterdir()) == []


def test_windows_superscript_device_aliases_are_body_free_and_effect_zero(
    tmp_path: Path,
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    unrelated = tmp_path / "unrelated.json"
    unrelated.write_bytes(b'{"preserve":true}')
    before = {entry.name: entry.read_bytes() for entry in tmp_path.iterdir()}

    for relative in (
        "cOm¹.TxT",
        "COM².json",
        "com³.ext",
        "lPt¹.TxT",
        "LPT².json",
        "lpt³.ext",
    ):
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.read_json(relative)
        assert exc.value.code == "RELATIVE_PATH_REJECTED"
        assert str(exc.value) == "RELATIVE_PATH_REJECTED"
        assert exc.value.authority_created is False
        assert exc.value.currentness_selected is False
        assert relative not in repr(exc.value)
        assert exc.value.__cause__ is None
        assert exc.value.__context__ is None

    assert {entry.name: entry.read_bytes() for entry in tmp_path.iterdir()} == before


def test_windows_junction_or_symlink_ancestor_is_rejected(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "receipt.json").write_text("{}", encoding="utf-8")
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("Developer Mode/symlink privilege unavailable")

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("alias/receipt.json")

    assert exc.value.code == "REPARSE_POINT_REJECTED"


def test_windows_target_symlink_is_rejected(tmp_path: Path) -> None:
    actual = tmp_path / "actual.json"
    actual.write_text("{}", encoding="utf-8")
    alias = tmp_path / "alias.json"
    try:
        alias.symlink_to(actual)
    except OSError:
        pytest.skip("Developer Mode/symlink privilege unavailable")

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("alias.json")

    assert exc.value.code == "REPARSE_POINT_REJECTED"
    assert actual.read_text(encoding="utf-8") == "{}"


def test_windows_hardlink_target_is_rejected(tmp_path: Path) -> None:
    actual = tmp_path / "actual.json"
    actual.write_text("{}", encoding="utf-8")
    alias = tmp_path / "alias.json"
    os.link(actual, alias)

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("alias.json")

    assert exc.value.code == "LINK_COUNT_REJECTED"
    assert actual.read_text(encoding="utf-8") == "{}"


def test_windows_noreplace_race_preserves_winner(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"

    def hook(stage: str) -> None:
        if stage == "before_noreplace":
            target.write_bytes(b"WINNER")

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
        with _writer(authority, tmp_path) as lease:
            authority.publish_json_noreplace("receipt.json", {"loser": True}, lease=lease)

    assert exc.value.code == "DESTINATION_EXISTS"
    assert target.read_bytes() == b"WINNER"


def test_windows_noreplace_final_symlink_cannot_redirect_outside_pinned_root(
    tmp_path: Path,
) -> None:
    target = tmp_path / "receipt.json"
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    escaped = outside / "escaped.json"

    def hook(stage: str) -> None:
        if stage != "before_noreplace":
            return
        try:
            target.symlink_to(escaped)
        except OSError:
            pytest.skip("Developer Mode/symlink privilege unavailable")

    authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_json_noreplace("receipt.json", {"x": 1}, lease=lease)

    assert exc.value.code == "DESTINATION_EXISTS"
    assert target.is_symlink()
    assert not escaped.exists()


def test_windows_initial_lock_publish_race_preserves_competitor(tmp_path: Path) -> None:
    target = tmp_path / "authority.lock"

    def hook(stage: str) -> None:
        if stage == "before_initial_lock_publish":
            target.write_bytes(b"COMPETITOR")

    capability = SecureAuthorityIO(tmp_path, _stage_hook=hook).lock(
        "authority.lock", mode="initial"
    )
    with pytest.raises(SecureAuthorityIOError) as exc:
        with capability:
            pass

    assert exc.value.code == "LOCK_CREATE_COLLISION"
    assert target.read_bytes() == b"COMPETITOR"
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_windows_initial_lock_locked_competitor_is_unknown_and_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sharing-blocked fresh observation is ambiguity, not a collision."""

    target = tmp_path / "authority.lock"

    def hook(stage: str) -> None:
        if stage == "before_initial_lock_publish":
            target.write_bytes(b"COMPETITOR")

    authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
    real_open_target = authority._open_target

    def block_competitor_observation(
        parent: object,
        *,
        writable: bool,
        **kwargs: object,
    ) -> int:
        if getattr(parent, "name", None) == "authority.lock" and not writable:
            raise SecureAuthorityIOError("WINDOWS_SHARING_VIOLATION")
        return real_open_target(parent, writable=writable, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(authority, "_open_target", block_competitor_observation)
    capability = authority.lock("authority.lock", mode="initial")
    with pytest.raises(SecureAuthorityIOError) as exc:
        with capability:
            pass

    assert exc.value.code == "LOCK_INITIALIZATION_UNKNOWN"
    assert exc.value.completion_unknown is True
    assert target.read_bytes() == b"COMPETITOR"
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_windows_initial_lock_case_collision_is_effect_zero(tmp_path: Path) -> None:
    competitor = tmp_path / "AUTHORITY.LOCK"
    competitor.write_bytes(b"COMPETITOR")

    with pytest.raises(SecureAuthorityIOError) as exc:
        with SecureAuthorityIO(tmp_path).lock("authority.lock", mode="initial"):
            pass

    assert exc.value.code == "LOCK_CREATE_COLLISION"
    assert competitor.read_bytes() == b"COMPETITOR"
    assert len(list(tmp_path.iterdir())) == 1


def test_windows_mutable_cas_is_fail_closed_without_atomic_identity_primitive(
    tmp_path: Path,
) -> None:
    target = tmp_path / "receipt.json"
    target.write_text('{"version":1}', encoding="utf-8")
    baseline = SecureAuthorityIO(tmp_path).read_json("receipt.json")

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority = SecureAuthorityIO(tmp_path)
        with _writer(authority, tmp_path) as lease:
            authority.replace_json_cas(
                "receipt.json",
                {"version": 2},
                lease=lease,
                expected_identity=baseline.identity,
                expected_sha256=baseline.sha256,
            )

    assert exc.value.code == "CAS_ATOMIC_UNAVAILABLE"
    assert exc.value.completion_unknown is False
    assert exc.value.authority_created is False
    assert target.read_text(encoding="utf-8") == '{"version":1}'
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_windows_immutable_plan_publish_and_graph_inspection_are_non_authoritative(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    first_plan = _trusted_plan({"generation": 1})
    second_plan = _trusted_plan(
        {"generation": 2}, revision=2, predecessor=first_plan.body_sha256
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

    assert inspection.inspected_count == 2
    assert inspection.authority_created is False
    assert inspection.currentness_selected is False
    assert inspection.status_code == "CURRENT_HEAD_AUTHORITY_NOT_CREATED"
    assert (
        inspection.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )


def test_windows_terminal_republish_does_not_create_duplicate_authority(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    (tmp_path / ".immutable-authority").mkdir()
    document = {"terminal": "complete"}
    plan = replace(_trusted_plan(document), action="COMMIT")
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

    assert duplicate.value.code == "DESTINATION_EXISTS"
    assert (
        duplicate.value.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    assert receipt.authority_created is False
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"terminal":"complete"}'


def test_windows_immutable_publish_uses_plan_and_body_snapshots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai_video_production import secure_authority_io as secure_io

    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    approved_path = plan.relative_path
    approved_fingerprint = _plan_fingerprint(plan)
    real_canonical = secure_io._canonical_json_bytes
    canonical_calls = 0

    def verifier(candidate: TrustedImmutablePlan, fingerprint: str) -> bool:
        assert candidate is not plan
        document["generation"] = 3
        object.__setattr__(
            candidate,
            "relative_path",
            ".immutable-authority/verifier-foreign.json",
        )
        object.__setattr__(candidate, "body_sha256", "sha256:" + "d" * 64)
        object.__setattr__(plan, "relative_path", ".immutable-authority/foreign.json")
        object.__setattr__(plan, "body_sha256", "sha256:" + "f" * 64)
        return fingerprint == approved_fingerprint

    def canonical_once(value: object, **kwargs: int) -> bytes:
        nonlocal canonical_calls
        canonical_calls += 1
        if canonical_calls > 1:
            raise AssertionError("body canonicalized twice")
        payload = real_canonical(value, **kwargs)
        document["generation"] = 2
        return payload

    monkeypatch.setattr(secure_io, "_canonical_json_bytes", canonical_once)
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=verifier,
        authority_instance_id="authority-instance-1",
    )
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_immutable_json(document, plan=plan, lease=lease)

    assert canonical_calls == 1
    assert receipt.plan_fingerprint == approved_fingerprint
    assert (tmp_path / approved_path).read_bytes() == b'{"generation":1}'
    assert not (tmp_path / ".immutable-authority" / "foreign.json").exists()
    assert not (
        tmp_path / ".immutable-authority" / "verifier-foreign.json"
    ).exists()


def test_windows_trusted_receipt_rejects_self_rehashed_replacement(
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
    observed = SecureAuthorityIO(tmp_path).read_json(plan.relative_path)
    forged = replace(
        receipt,
        identity=observed.identity,
        security_sha256=observed.security_sha256,
        receipt_fingerprint="sha256:" + "0" * 64,
    )
    forged = replace(forged, receipt_fingerprint=_receipt_fingerprint(forged))

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_immutable_json(plan=plan, receipt=forged)

    assert exc.value.code == "TRUSTED_IMMUTABLE_RECEIPT_REJECTED"
    assert target.read_bytes() == b'{"generation":1}'


def test_windows_immutable_read_rejects_stable_namespace_security_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai_video_production import secure_authority_io as secure_io

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

    def stable_drift(fd: int) -> str:
        marker = "a" if stat.S_ISDIR(os.fstat(fd).st_mode) else "b"
        return "sha256:" + marker * 64

    monkeypatch.setattr(secure_io, "_fd_security_digest", stable_drift)
    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_immutable_json(plan=plan, receipt=receipt)

    assert exc.value.code == "IMMUTABLE_BINDING_MISMATCH"
    assert (tmp_path / plan.relative_path).read_bytes() == b'{"generation":1}'


def test_windows_direct_private_lock_cannot_self_register_with_stolen_nonce(
    tmp_path: Path,
) -> None:
    from ai_video_production import secure_authority_io as secure_io

    authority = SecureAuthorityIO(tmp_path)
    forged = secure_io._SecureFileLock(
        authority,
        ".writer.lock",
        "initial",
        authority._SecureAuthorityIO__lease_issuer_nonce,
    )
    with pytest.raises(SecureAuthorityIOError) as exc:
        with forged:
            pass

    assert exc.value.code == "WRITER_LEASE_REQUIRED"
    assert list(tmp_path.iterdir()) == []


def test_windows_direct_private_lock_has_no_registration_issuer_with_nonce(
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

    assert not hasattr(authority, "_issue_writer_lease")
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
def test_windows_unavailable_effect_burns_same_context_lease(
    tmp_path: Path,
    method_name: str,
    expected_code: str,
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as unavailable:
            if method_name == "replace_json_cas":
                authority.replace_json_cas(
                    "target.json",
                    {},
                    lease=lease,
                    expected_identity=object(),  # type: ignore[arg-type]
                    expected_sha256="sha256:" + "0" * 64,
                )
            elif method_name == "cleanup_owned_file":
                authority.cleanup_owned_file(
                    "target.json",
                    lease=lease,
                    expected_identity=object(),  # type: ignore[arg-type]
                    expected_sha256="sha256:" + "0" * 64,
                )
            else:
                getattr(authority, method_name)("target.json", {}, lease=lease)
        with pytest.raises(SecureAuthorityIOError) as burned:
            authority.publish_json_noreplace("after.json", {}, lease=lease)

    assert unavailable.value.code == expected_code
    assert burned.value.code == "CAPABILITY_BURNED"
    assert not (tmp_path / "target.json").exists()
    assert not (tmp_path / "after.json").exists()


@pytest.mark.parametrize(
    "method_name",
    [
        "replace_json_cas",
        "commit_directory_tree",
        "advance_mutable_phase",
        "cleanup_owned_file",
    ],
)
def test_windows_unavailable_validation_failure_still_burns_active_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
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
            if method_name == "replace_json_cas":
                authority.replace_json_cas(
                    "target.json",
                    {},
                    lease=lease,
                    expected_identity=object(),  # type: ignore[arg-type]
                    expected_sha256="sha256:" + "0" * 64,
                )
            elif method_name == "cleanup_owned_file":
                authority.cleanup_owned_file(
                    "target.json",
                    lease=lease,
                    expected_identity=object(),  # type: ignore[arg-type]
                    expected_sha256="sha256:" + "0" * 64,
                )
            else:
                getattr(authority, method_name)("target.json", {}, lease=lease)
        with pytest.raises(SecureAuthorityIOError) as burned:
            authority.publish_json_noreplace("after.json", {}, lease=lease)

    assert validation_failure.value.code == "SECURITY_DESCRIPTOR_READ_FAILED"
    assert burned.value.code == "CAPABILITY_BURNED"
    assert not (tmp_path / "target.json").exists()
    assert not (tmp_path / "after.json").exists()


@pytest.mark.parametrize("effect_kind", ["immutable_body", "raw_path"])
def test_windows_failed_public_publish_burns_same_context_lease(
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

    assert rejected.value.code == (
        "IMMUTABLE_BODY_DIGEST_MISMATCH"
        if effect_kind == "immutable_body"
        else "RELATIVE_PATH_REJECTED"
    )
    assert burned.value.code == "CAPABILITY_BURNED"
    assert not (tmp_path / ".immutable-authority" / "generation-1.json").exists()
    assert not (tmp_path / "after-rejection.json").exists()
    assert not (tmp_path.parent / "outside.json").exists()


def test_windows_writer_validation_failure_burns_active_lease_before_retry(
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

    assert validation_failure.value.code == "SECURITY_DESCRIPTOR_READ_FAILED"
    assert burned.value.code == "CAPABILITY_BURNED"
    assert not (tmp_path / "first.json").exists()
    assert not (tmp_path / "second.json").exists()


def test_windows_graph_snapshots_every_plan_and_receipt_before_callbacks(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    first_plan = _trusted_plan({"generation": 1})
    second_plan = _trusted_plan(
        {"generation": 2},
        revision=2,
        predecessor=first_plan.body_sha256,
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
def test_windows_graph_rejects_oversized_containers_before_callbacks(
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

    assert exc.value.code == (
        "IMMUTABLE_GRAPH_BOUND_REJECTED"
        if oversized_input == "plans"
        else "IMMUTABLE_GRAPH_BINDINGS_REJECTED"
    )
    assert calls == 0
    assert list(tmp_path.iterdir()) == []


def test_windows_consumer_graph_verifier_stops_tombstone_replay_effect_zero(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    (tmp_path / ".immutable-authority").mkdir()
    root_plan = _trusted_plan({"generation": 1})
    tombstone_plan = replace(
        _trusted_plan(
            {"tombstone": True}, revision=2, predecessor=root_plan.body_sha256
        ),
        action="TOMBSTONE",
    )
    resumed_plan = _trusted_plan(
        {"generation": 2}, revision=3, predecessor=tombstone_plan.body_sha256
    )
    receipt_trust = _ReceiptTrust()
    expected_graph: str | None = None
    expected_specified: str | None = None
    graph_checks = 0

    def one_shot_graph_verifier(graph: str, specified: str) -> bool:
        nonlocal graph_checks
        graph_checks += 1
        return (
            graph_checks == 1
            and graph == expected_graph
            and specified == expected_specified
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
    assert replay.value.code == "TRUSTED_IMMUTABLE_GRAPH_REJECTED"

    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as resumed:
            authority.publish_immutable_json(
                {"generation": 2}, plan=resumed_plan, lease=lease
            )
    assert resumed.value.code == "TRUSTED_GENERATION_PLAN_REJECTED"
    assert sorted(path.name for path in (tmp_path / ".immutable-authority").iterdir()) == [
        "generation-1.json",
        "generation-2.json",
    ]


@pytest.mark.parametrize(
    "reserved_path",
    [
        ".immutable-authority/unbound.json",
        ".IMMUTABLE-AUTHORITY/unbound.json",
        ".Immutable-Authority/unbound.json",
    ],
)
def test_windows_raw_immutable_namespace_publish_is_rejected_effect_zero(
    tmp_path: Path, reserved_path: str
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    authority = SecureAuthorityIO(tmp_path)

    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_json_noreplace(
                reserved_path, {"x": 1}, lease=lease
            )

    assert exc.value.code == "TRUSTED_GENERATION_PLAN_REQUIRED"
    assert exc.value.authority_created is False
    assert exc.value.currentness_selected is False
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


def test_windows_short_name_alias_to_immutable_namespace_is_rejected_when_available(
    tmp_path: Path,
) -> None:
    import ctypes
    from ctypes import wintypes

    reserved = tmp_path / ".immutable-authority"
    reserved.mkdir()
    nested = reserved / "nested"
    nested.mkdir()
    get_short_path = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
    get_short_path.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    get_short_path.restype = wintypes.DWORD

    def short_path(path: Path) -> str | None:
        required = get_short_path(str(path), None, 0)
        if required == 0:
            return None
        buffer = ctypes.create_unicode_buffer(required)
        written = get_short_path(str(path), buffer, required)
        return buffer.value if written else None

    short_root = short_path(tmp_path)
    short_reserved = short_path(reserved)
    if not short_root or not short_reserved:
        return
    prefix = short_root.rstrip("\\/") + os.sep
    if not short_reserved.casefold().startswith(prefix.casefold()):
        return
    alias = short_reserved[len(prefix) :]
    if alias.casefold() == ".immutable-authority".casefold():
        return

    authority = SecureAuthorityIO(tmp_path)
    for relative_path in (
        f"{alias}/unbound.json",
        f"{alias}/nested/unbound.json",
    ):
        with _writer(authority, tmp_path) as lease:
            with pytest.raises(SecureAuthorityIOError) as exc:
                authority.publish_json_noreplace(
                    relative_path, {"x": 1}, lease=lease
                )
            assert exc.value.code == "TRUSTED_GENERATION_PLAN_REQUIRED"

    assert sorted(path.name for path in reserved.iterdir()) == ["nested"]
    assert list(nested.iterdir()) == []


@pytest.mark.parametrize(
    "race_stage", ["raw_parent_pinned", "before_reserved_namespace_pin"]
)
def test_windows_reserved_namespace_swap_after_raw_parent_pin_cannot_inject(
    tmp_path: Path, race_stage: str
) -> None:
    candidate = tmp_path / "candidate"
    displaced = tmp_path / "candidate-displaced"
    reserved = tmp_path / ".immutable-authority"
    candidate.mkdir()
    reserved.mkdir()
    swap_blocked = False

    def hook(stage: str) -> None:
        nonlocal swap_blocked
        if stage != race_stage:
            return
        try:
            os.replace(candidate, displaced)
            os.replace(reserved, candidate)
        except OSError:
            swap_blocked = True

    authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_json_noreplace(
            "candidate/unbound.json", {"x": 1}, lease=lease
        )

    assert swap_blocked is True
    assert receipt.authority_created is False
    assert (candidate / "unbound.json").read_bytes() == b'{"x":1}'
    assert list(reserved.iterdir()) == []
    assert displaced.exists() is False


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
def test_windows_complete_plan_fingerprint_rebinding_is_effect_zero(
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

    assert exc.value.code == "TRUSTED_GENERATION_PLAN_REJECTED"
    assert seen == [_plan_fingerprint(changed_plan)]
    assert seen[0] != _plan_fingerprint(exact_plan)
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


@pytest.mark.parametrize(
    ("method_name", "expected_code"),
    [
        ("commit_directory_tree", "DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED"),
        ("advance_mutable_phase", "MUTABLE_PHASE_ADVANCE_UNAVAILABLE"),
    ],
)
def test_windows_out_of_scope_authority_discovery_is_effect_zero(
    tmp_path: Path, method_name: str, expected_code: str
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    cyclic: list[object] = []
    cyclic.append(cyclic)

    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            getattr(authority, method_name)("../outside", cyclic, lease=lease)

    assert exc.value.code == expected_code
    assert exc.value.authority_created is False
    assert exc.value.currentness_selected is False
    assert exc.value.directory_tree_status_code == "DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED"
    assert exc.value.mutable_phase_status_code == "MUTABLE_PHASE_ADVANCE_UNAVAILABLE"
    assert (
        exc.value.duplicate_currentness_status_code
        == "DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED"
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == [".writer.lock"]


def test_windows_cleanup_is_fail_closed_before_effect(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with _writer(authority, tmp_path) as lease:
        published = authority.publish_json_noreplace("pending.json", {"x": 1}, lease=lease)
    target = tmp_path / "pending.json"

    replacement = tmp_path / "replacement.json"
    replacement.write_bytes(b"PRESERVE")
    observed: list[str] = []

    def hook(stage: str) -> None:
        if stage.startswith("before_owned_cleanup") or stage.startswith("before_live_unlink"):
            observed.append(stage)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
        with _writer(authority, tmp_path) as lease:
            authority.cleanup_owned_file(
                "pending.json",
                lease=lease,
                expected_identity=published.identity,
                expected_sha256=published.sha256,
            )

    assert exc.value.code == "CLEANUP_ATOMIC_UNAVAILABLE"
    assert exc.value.completion_unknown is False
    assert exc.value.authority_created is False
    assert observed == []
    assert target.read_bytes() == b'{"x":1}'
    assert replacement.read_bytes() == b"PRESERVE"


def test_windows_existing_lock_rejects_security_descriptor_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "authority.lock"
    target.write_bytes(b"\0")
    target_calls = 0

    def drifting_digest(fd: int) -> str:
        nonlocal target_calls
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            return "sha256:" + "a" * 64
        target_calls += 1
        return "sha256:" + ("1" if target_calls == 1 else "2") * 64

    monkeypatch.setattr(
        "ai_video_production.secure_authority_io._fd_security_digest",
        drifting_digest,
    )

    with pytest.raises(SecureAuthorityIOError) as exc:
        with SecureAuthorityIO(tmp_path).lock("authority.lock", mode="existing"):
            pass

    assert exc.value.code == "LOCK_SECURITY_DRIFT"


def test_windows_live_temp_handle_blocks_foreign_swap(tmp_path: Path) -> None:
    attempted: list[bool] = []

    def hook(stage: str) -> None:
        if stage != "temp_handle_live":
            return
        temp = next(path for path in tmp_path.iterdir() if path.name.startswith(".authority-"))
        foreign = tmp_path / "foreign.json"
        foreign.write_bytes(b"FOREIGN")
        with pytest.raises(PermissionError):
            os.replace(foreign, temp)
        attempted.append(True)

    authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_json_noreplace("receipt.json", {"x": 1}, lease=lease)

    assert attempted == [True]
    assert receipt.authority_created is False
    assert (tmp_path / "receipt.json").read_text(encoding="utf-8") == '{"x":1}'
    assert (tmp_path / "foreign.json").read_bytes() == b"FOREIGN"


def test_windows_pinned_ancestor_blocks_rename_before_publish(tmp_path: Path) -> None:
    authority_dir = tmp_path / "authority"
    authority_dir.mkdir()
    attempted: list[bool] = []

    def hook(stage: str) -> None:
        if stage != "before_noreplace":
            return
        with pytest.raises(PermissionError):
            os.replace(authority_dir, tmp_path / "moved")
        attempted.append(True)

    authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
    with _writer(authority, tmp_path) as lease:
        authority.publish_json_noreplace("authority/receipt.json", {}, lease=lease)

    assert attempted == [True]
    assert authority_dir.is_dir()
    assert not (tmp_path / "moved").exists()


def test_windows_cleanup_unavailable_preserves_foreign_and_current(tmp_path: Path) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_json_noreplace("pending.json", {"x": 1}, lease=lease)
    foreign = tmp_path / "foreign.json"
    foreign.write_bytes(b"FOREIGN")
    attempted: list[bool] = []

    def hook(stage: str) -> None:
        if stage == "before_live_unlink":
            attempted.append(True)

    authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.cleanup_owned_file(
                "pending.json",
                lease=lease,
                expected_identity=receipt.identity,
                expected_sha256=receipt.sha256,
            )

    assert exc.value.code == "CLEANUP_ATOMIC_UNAVAILABLE"
    assert exc.value.authority_created is False
    assert attempted == []
    assert (tmp_path / "pending.json").read_bytes() == b'{"x":1}'
    assert foreign.read_bytes() == b"FOREIGN"


def test_windows_cleanup_unavailable_never_reaches_hardlink_delete_seam(
    tmp_path: Path,
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_json_noreplace("pending.json", {"x": 1}, lease=lease)
    alias = tmp_path / "foreign-alias.json"

    def hook(stage: str) -> None:
        if stage == "before_live_unlink":
            os.link(tmp_path / "pending.json", alias)

    authority = SecureAuthorityIO(tmp_path, _stage_hook=hook)
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.cleanup_owned_file(
                "pending.json",
                lease=lease,
                expected_identity=receipt.identity,
                expected_sha256=receipt.sha256,
            )

    assert exc.value.code == "CLEANUP_ATOMIC_UNAVAILABLE"
    assert exc.value.authority_created is False
    assert (tmp_path / "pending.json").read_bytes() == b'{"x":1}'
    assert not alias.exists()


def test_windows_initial_lock_directory_failure_rolls_back_exact_inode(
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

    assert exc.value.code == "LOCK_INITIALIZE_FAILED"
    assert exc.value.completion_unknown is False
    assert not (tmp_path / "authority.lock").exists()
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_windows_publish_directory_failure_rolls_back_exact_inode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with _writer(authority, tmp_path):
        pass
    original = authority._directory_durable
    calls = 0

    def fail_first(parent: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SecureAuthorityIOError("DIRECTORY_DURABILITY_FAILED")
        original(parent)  # type: ignore[arg-type]

    monkeypatch.setattr(authority, "_directory_durable", fail_first)
    with pytest.raises(SecureAuthorityIOError) as exc:
        with _writer(authority, tmp_path) as lease:
            authority.publish_json_noreplace("receipt.json", {"x": 1}, lease=lease)

    assert exc.value.code == "DIRECTORY_DURABILITY_FAILED"
    assert exc.value.completion_unknown is False
    assert not (tmp_path / "receipt.json").exists()
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_windows_inheritance_rejection_closes_opened_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ai_video_production.secure_authority_io as secure_io

    real_open = secure_io._windows_open
    captured: list[int] = []

    def capture_open(*args: object, **kwargs: object) -> int:
        fd = real_open(*args, **kwargs)  # type: ignore[arg-type]
        captured.append(fd)
        return fd

    def reject(_: int) -> None:
        raise SecureAuthorityIOError("HANDLE_INHERITANCE_REJECTED")

    monkeypatch.setattr(secure_io, "_windows_open", capture_open)
    monkeypatch.setattr(secure_io, "_set_noninheritable", reject)

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("missing.json")

    assert exc.value.code == "HANDLE_INHERITANCE_REJECTED"
    assert captured
    with pytest.raises(OSError):
        os.fstat(captured[-1])


def test_windows_created_temp_inheritance_rejection_removes_owned_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ai_video_production.secure_authority_io as secure_io

    authority = SecureAuthorityIO(tmp_path)
    with _writer(authority, tmp_path):
        pass
    real_open = secure_io._windows_open
    real_noninheritable = secure_io._set_noninheritable
    temp_fds: list[int] = []

    def capture_open(*args: object, **kwargs: object) -> int:
        fd = real_open(*args, **kwargs)  # type: ignore[arg-type]
        if kwargs.get("create_new"):
            temp_fds.append(fd)
        return fd

    def reject_created(fd: int) -> None:
        if fd in temp_fds:
            raise SecureAuthorityIOError("HANDLE_INHERITANCE_REJECTED")
        real_noninheritable(fd)

    monkeypatch.setattr(secure_io, "_windows_open", capture_open)
    monkeypatch.setattr(secure_io, "_set_noninheritable", reject_created)

    with pytest.raises(SecureAuthorityIOError) as exc:
        with _writer(authority, tmp_path) as lease:
            authority.publish_json_noreplace("receipt.json", {"x": 1}, lease=lease)

    assert exc.value.code == "HANDLE_INHERITANCE_REJECTED"
    assert temp_fds
    with pytest.raises(OSError):
        os.fstat(temp_fds[-1])
    assert not (tmp_path / "receipt.json").exists()
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_windows_raw_created_handle_abandon_removes_exact_owned_name(tmp_path: Path) -> None:
    import msvcrt
    import ai_video_production.secure_authority_io as secure_io

    target = tmp_path / ".authority-raw.tmp"
    fd = secure_io._windows_open(
        target,
        writable=True,
        create_new=True,
        directory=False,
        delete_access=True,
    )
    raw_handle = int(msvcrt.get_osfhandle(fd))

    secure_io._windows_abandon_native_handle(raw_handle, delete_created=True)

    with pytest.raises(OSError):
        os.fstat(fd)
    assert not target.exists()


def test_windows_ancestor_post_open_validation_failure_closes_handle(
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

    def reject_directory(value: object) -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            raise SecureAuthorityIOError("ANCESTOR_REJECTED")
        real_require(value)  # type: ignore[arg-type]

    monkeypatch.setattr(authority, "_open_directory", capture_open)
    monkeypatch.setattr(secure_io, "_require_directory", reject_directory)

    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.read_json("missing.json")

    assert exc.value.code == "ANCESTOR_REJECTED"
    assert captured
    with pytest.raises(OSError):
        os.fstat(captured[-1])


def test_windows_temp_bind_failure_closes_and_removes_owned_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with _writer(authority, tmp_path):
        pass
    captured: list[int] = []

    def reject_bind(parent: object, fd: int):
        captured.append(fd)
        raise SecureAuthorityIOError("TEMP_BIND_REJECTED")

    with _writer(authority, tmp_path) as lease:
        monkeypatch.setattr(authority, "_bind_regular", reject_bind)
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_json_noreplace("receipt.json", {"x": 1}, lease=lease)

    assert exc.value.code == "TEMP_BIND_REJECTED"
    assert captured
    with pytest.raises(OSError):
        os.fstat(captured[-1])
    assert not (tmp_path / "receipt.json").exists()
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_windows_publish_rollback_durability_failure_is_completion_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    with _writer(authority, tmp_path):
        pass

    def reject_directory_durability(parent: object) -> None:
        raise SecureAuthorityIOError("DIRECTORY_DURABILITY_FAILED")

    monkeypatch.setattr(authority, "_directory_durable", reject_directory_durability)
    with pytest.raises(SecureAuthorityIOError) as exc:
        with _writer(authority, tmp_path) as lease:
            authority.publish_json_noreplace("receipt.json", {"x": 1}, lease=lease)

    assert exc.value.code == "PUBLISH_ROLLBACK_UNKNOWN"
    assert exc.value.completion_unknown is True
    assert not (tmp_path / "receipt.json").exists()
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_windows_cleanup_unavailable_precedes_open_and_close_seams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ai_video_production.secure_authority_io as secure_io

    authority = SecureAuthorityIO(tmp_path)
    with _writer(authority, tmp_path) as lease:
        receipt = authority.publish_json_noreplace("pending.json", {"x": 1}, lease=lease)
    captured: list[int] = []
    real_open_target = authority._open_target
    real_close = secure_io.os.close

    def capture_target(*args: object, **kwargs: object) -> int:
        fd = real_open_target(*args, **kwargs)  # type: ignore[arg-type]
        if kwargs.get("delete_access"):
            captured.append(fd)
        return fd

    with _writer(authority, tmp_path) as lease:
        monkeypatch.setattr(authority, "_open_target", capture_target)
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.cleanup_owned_file(
                "pending.json",
                lease=lease,
                expected_identity=receipt.identity,
                expected_sha256=receipt.sha256,
            )

    assert exc.value.code == "CLEANUP_ATOMIC_UNAVAILABLE"
    assert exc.value.completion_unknown is False
    assert exc.value.authority_created is False
    assert captured == []
    assert (tmp_path / "pending.json").read_bytes() == b'{"x":1}'


def test_windows_publish_classifies_helper_fault_after_real_noreplace_as_unknown(
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

    assert exc.value.code == "PUBLISH_COMMIT_UNKNOWN"
    assert exc.value.completion_unknown is True
    assert "private-after-publish" not in repr(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None
    assert (tmp_path / "receipt.json").read_bytes() == b'{"x":1}'
    assert list(tmp_path.glob(".authority-*.tmp")) == []


def test_windows_initial_lock_classifies_helper_fault_after_real_noreplace_as_unknown(
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

    assert exc.value.code == "LOCK_INITIALIZATION_UNKNOWN"
    assert exc.value.completion_unknown is True
    assert "private-after-lock-publish" not in repr(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None
    assert not (tmp_path / ".writer.lock").exists()
    assert list(tmp_path.glob(".authority-*.tmp")) == []


@pytest.mark.parametrize(
    "filename",
    ["generation with space.json", "generation-é.json", "g" * 129],
)
def test_windows_immutable_plan_rejects_names_graph_scan_cannot_admit(
    tmp_path: Path,
    filename: str,
) -> None:
    from dataclasses import replace

    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = replace(
        _trusted_plan(document),
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

    assert exc.value.code == "IMMUTABLE_COORDINATE_REJECTED"
    assert verifier_calls == 0
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


def test_windows_immutable_plan_filename_round_trips_through_graph_scan(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = replace(
        _trusted_plan(document),
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


def test_windows_malformed_json_context_is_detached_at_public_read_boundary(
    tmp_path: Path,
) -> None:
    private_body = "private-windows-json-body"
    (tmp_path / "receipt.json").write_text(private_body, encoding="utf-8")

    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json("receipt.json")

    _assert_detached_error(exc, "STRICT_JSON_REJECTED", private_body)


def test_windows_os_error_filename_is_detached_at_public_read_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai_video_production import secure_authority_io as secure_io

    private_name = "private-windows-os-owner-path.json"
    private_target = tmp_path / private_name
    real_lstat = secure_io.os.lstat

    def rejecting_lstat(path: object, *args: object, **kwargs: object):
        if os.path.abspath(os.fspath(path)) == os.path.abspath(os.fspath(private_target)):
            raise OSError(5, "private-windows-os-error", os.fspath(private_target))
        return real_lstat(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(secure_io.os, "lstat", rejecting_lstat)
    with pytest.raises(SecureAuthorityIOError) as exc:
        SecureAuthorityIO(tmp_path).read_json(private_name)

    _assert_detached_error(exc, "FILE_LSTAT_FAILED", private_name)


def test_windows_plan_verifier_exception_is_detached_at_public_publish_boundary(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)

    def exploding_verifier(candidate: TrustedImmutablePlan, fingerprint: str) -> bool:
        raise RuntimeError("private-windows-plan-verifier-token")

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=exploding_verifier,
        authority_instance_id=plan.instance_id,
    )
    with _writer(authority, tmp_path) as lease:
        with pytest.raises(SecureAuthorityIOError) as exc:
            authority.publish_immutable_json(document, plan=plan, lease=lease)

    _assert_detached_error(
        exc,
        "TRUSTED_GENERATION_PLAN_REJECTED",
        "private-windows-plan-verifier-token",
    )
    assert list((tmp_path / ".immutable-authority").iterdir()) == []


def test_windows_receipt_verifier_exception_is_detached_at_public_read_boundary(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)

    def exploding_receipt_verifier(fingerprint: str) -> bool:
        raise RuntimeError("private-windows-receipt-verifier-token")

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

    _assert_detached_error(
        exc,
        "TRUSTED_IMMUTABLE_RECEIPT_REJECTED",
        "private-windows-receipt-verifier-token",
    )


def test_windows_graph_verifier_exception_is_detached_at_public_inspection_boundary(
    tmp_path: Path,
) -> None:
    (tmp_path / ".immutable-authority").mkdir()
    document = {"generation": 1}
    plan = _trusted_plan(document)
    receipt_trust = _ReceiptTrust()

    def exploding_graph_verifier(aggregate: str, specified: str) -> bool:
        raise RuntimeError("private-windows-graph-verifier-token")

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

    _assert_detached_error(
        exc,
        "TRUSTED_IMMUTABLE_GRAPH_REJECTED",
        "private-windows-graph-verifier-token",
    )


def test_windows_public_error_detaches_caller_ambient_exception(tmp_path: Path) -> None:
    (tmp_path / "receipt.json").write_text("private-windows-json-body", encoding="utf-8")

    try:
        raise RuntimeError("private-windows-ambient-token")
    except RuntimeError:
        with pytest.raises(SecureAuthorityIOError) as exc:
            SecureAuthorityIO(tmp_path).read_json("receipt.json")

    _assert_detached_error(
        exc,
        "STRICT_JSON_REJECTED",
        "private-windows-ambient-token",
    )


def test_windows_lock_cleanup_error_detaches_private_body_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority = SecureAuthorityIO(tmp_path)
    real_unlock = authority._unlock_fd

    def unlock_then_fail(fd: int) -> None:
        real_unlock(fd)
        raise SecureAuthorityIOError("private-windows-lock-cleanup-token")

    monkeypatch.setattr(authority, "_unlock_fd", unlock_then_fail)
    with pytest.raises(SecureAuthorityIOError) as exc:
        with authority.lock(".writer.lock", mode="initial"):
            raise RuntimeError("private-windows-lock-body-token")

    _assert_detached_error(
        exc,
        "LOCK_CLEANUP_UNKNOWN",
        "private-windows-lock-cleanup-token",
        "private-windows-lock-body-token",
    )
    assert exc.value.completion_unknown is True
