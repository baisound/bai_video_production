from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path

import pytest

from ai_video_production.secure_authority_io import (
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
            "backend_id": plan.backend_id,
            "body_sha256": plan.body_sha256,
            "build_id": plan.build_id,
            "expected_predecessor_sha256": plan.expected_predecessor_sha256,
            "instance_id": plan.instance_id,
            "operation_id": plan.operation_id,
            "relative_path": plan.relative_path.replace("\\", "/"),
            "revision": plan.revision,
            "session_id": plan.session_id,
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


def test_windows_read_rejects_security_descriptor_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "receipt.json"
    target.write_text("{}", encoding="utf-8")
    observations = iter(["sha256:" + "1" * 64, "sha256:" + "2" * 64])
    monkeypatch.setattr(
        "ai_video_production.secure_authority_io._windows_security_digest",
        lambda _: next(observations),
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
    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(first_plan, second_plan),
        immutable_graph_verifier=_exact_graph_verifier(
            first_plan, second_plan, specified=second_plan
        ),
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

    inspection = authority.inspect_immutable_graph(
        plans=[first_plan, second_plan],
        expected_identities={
            first_plan.relative_path: first.identity,
            second_plan.relative_path: second.identity,
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
    expected_graph = "sha256:" + hashlib.sha256(
        "\n".join(
            sorted((_plan_fingerprint(root_plan), _plan_fingerprint(tombstone_plan)))
        ).encode("ascii")
    ).hexdigest()
    graph_checks = 0

    def one_shot_graph_verifier(graph: str, specified: str) -> bool:
        nonlocal graph_checks
        graph_checks += 1
        return (
            graph_checks == 1
            and graph == expected_graph
            and specified == _plan_fingerprint(tombstone_plan)
        )

    authority = SecureAuthorityIO(
        tmp_path,
        immutable_plan_verifier=_exact_plan_verifier(root_plan, tombstone_plan),
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
    identities = {
        root_plan.relative_path: root.identity,
        tombstone_plan.relative_path: tombstone.identity,
    }

    authority.inspect_immutable_graph(
        plans=[root_plan, tombstone_plan],
        expected_identities=identities,
        specified_plan=tombstone_plan,
    )
    with pytest.raises(SecureAuthorityIOError) as replay:
        authority.inspect_immutable_graph(
            plans=[root_plan, tombstone_plan],
            expected_identities=identities,
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
    with _writer(authority, tmp_path) as lease:
        for relative_path in (
            f"{alias}/unbound.json",
            f"{alias}/nested/unbound.json",
        ):
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
    with pytest.raises(SecureAuthorityIOError) as exc:
        authority.publish_immutable_json(
            document,
            plan=changed_plan,
            lease=object(),  # type: ignore[arg-type]
        )

    assert exc.value.code == "TRUSTED_GENERATION_PLAN_REJECTED"
    assert seen == [_plan_fingerprint(changed_plan)]
    if "authorization" not in plan_update:
        assert seen[0] != _plan_fingerprint(exact_plan)
    assert list(tmp_path.iterdir()) == []


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
    observations = iter(["sha256:" + "1" * 64, "sha256:" + "2" * 64])
    monkeypatch.setattr(
        "ai_video_production.secure_authority_io._windows_security_digest",
        lambda _: next(observations),
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
