from __future__ import annotations

import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import pickle
import threading

import pytest

import ai_video_production.montage_learning_installation as installation
import task063_legacy_installation_fixture as legacy_installation
from ai_video_production.montage_learning_installer_cli import main as installer_main
from ai_video_production.montage_learning_installation import (
    BRIDGE_RELATIVE_PATH,
    INSTALLER_READBACK_FILENAME,
    MontageLearningInstallationError,
    discover_installed_bridge,
    provision_and_write_installer_readback as public_provision_and_write,
    provision_installed_bridge as public_provision,
    write_installer_readback as public_write_readback,
)


MANIFEST_SHA = "sha256:" + "a" * 64
ROOT_SECURITY_SHA = "sha256:" + "b" * 64
provision_and_write_installer_readback = (
    legacy_installation.provision_and_write_installer_readback
)
provision_installed_bridge = legacy_installation.provision_installed_bridge
write_installer_readback = legacy_installation.write_installer_readback


def _commitment(seed: str) -> str:
    return installation.sha256_json({"seed": seed})


def _v2_descriptor_fixture(
    instance_id: str = "bvp-install-" + "1" * 32,
) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": installation.DESCRIPTOR_SCHEMA_VERSION,
        "message_type": installation.DESCRIPTOR_MESSAGE_TYPE,
        "product_id": installation.PRODUCT_ID,
        "install_instance_id": instance_id,
        "bridge_relative_path": installation.BRIDGE_RELATIVE_PATH,
        "initial_installer_manifest_sha256": _commitment("initial-manifest"),
        "initial_product_build_sha256": _commitment("initial-product"),
        "created_at_utc": "2026-09-03T00:00:00Z",
    }
    document = dict(body)
    document["descriptor_sha256"] = installation.sha256_json(body)
    return document


def _fixture_root_snapshot(tmp_path: Path):
    selected_root = tmp_path / "selected"
    selected_root.mkdir()
    plan = installation._fixture_only_build_selected_root_semantic_snapshot(
        action=installation._InstallationAction.FIRST_PROVISION,
        selected_root=selected_root,
        predecessor_bound=False,
        existing_relative_directories=(),
        selected_root_security_sha256=ROOT_SECURITY_SHA,
    )
    return selected_root, plan


def _lifecycle_root_snapshot(
    tmp_path: Path,
    action_name: str,
    security_sha256: str,
):
    selected_root = tmp_path / f"selected-{security_sha256[-8:]}"
    selected_root.mkdir(exist_ok=True)
    existing = (
        ()
        if action_name in {"FIRST_PROVISION", "PORTABLE_REBIND"}
        else installation._DIRECTORY_RELATIVE_PATHS
    )
    return installation._fixture_only_build_selected_root_semantic_snapshot(
        action=installation._InstallationAction[action_name],
        selected_root=selected_root,
        predecessor_bound=action_name != "FIRST_PROVISION",
        existing_relative_directories=existing,
        selected_root_security_sha256=security_sha256,
    )


def _plan_lifecycle(**provided: object):
    values = dict(provided)
    root_snapshot = values["root_snapshot"]
    current = values["current"]
    terminal = str(values["expected_pair_terminal_sha256"])
    action_name = root_snapshot.action.value
    current_revision = current.installation_revision if current is not None else 0
    values.setdefault(
        "operation_id",
        f"operation-{action_name.lower()}-{current_revision}",
    )
    values.setdefault("session_sha256", _commitment("lifecycle-session"))
    values.setdefault(
        "expected_predecessor_terminal_sha256",
        current.pair_terminal_sha256
        if current is not None
        else _commitment("no-predecessor"),
    )
    values.setdefault(
        "successor_reservation_sha256",
        None
        if action_name == "VERIFY_REPAIR"
        else _commitment(f"reservation-{action_name}-{terminal}"),
    )
    values.setdefault(
        "revision_terminal_sha256",
        _commitment(f"revision-{action_name}-{terminal}")
        if current is None or action_name == "PUBLISH_INSTALL_REVISION"
        else current.revision_terminal_sha256,
    )
    values.setdefault(
        "predecessor_revision_terminal_sha256",
        current.revision_terminal_sha256
        if current is not None and action_name == "PUBLISH_INSTALL_REVISION"
        else None,
    )
    values.setdefault(
        "currentness_sha256",
        _commitment(f"currentness-{action_name}-{terminal}"),
    )
    values.setdefault(
        "requested_revision",
        current_revision + 1
        if action_name == "PUBLISH_INSTALL_REVISION"
        else max(1, current_revision),
    )
    return installation._fixture_only_plan_lifecycle_transition(**values)


def _issue_pair_fixture(
    snapshot: object,
    descriptor: dict[str, object],
    **overrides: object,
):
    values: dict[str, object] = {
        "action": installation._InstallationAction.FIRST_PROVISION,
        "operation_id": "operation-1",
        "consumer_operation_key": "c1",
        "ticket_event_sha256": _commitment("ticket"),
        "install_instance_id": descriptor["install_instance_id"],
        "descriptor_document": descriptor,
        "owner_instance_id": descriptor["install_instance_id"],
        "owner_contract_profile": installation.BRIDGE_CONTRACT_PROFILE,
        "pair_action": "PAIR_GENESIS",
        "pair_generation_sha256": _commitment("pair-generation"),
        "descriptor_generation_sha256": _commitment("pair-generation"),
        "owner_generation_sha256": _commitment("pair-generation"),
        "pair_terminal_sha256": _commitment("pair-terminal"),
        "predecessor_terminal_sha256": _commitment("no-predecessor"),
        "successor_reservation_sha256": _commitment("reservation"),
        "installation_revision": 1,
        "descriptor_identity_sha256": _commitment("descriptor-identity"),
        "owner_identity_sha256": _commitment("owner-identity"),
        "owner_manifest_sha256": _commitment("owner-manifest"),
        "selected_root_security_sha256": snapshot.selected_root_security_sha256,
        "directory_set_sha256": snapshot.directory_set_sha256,
        "package_manifest_sha256": _commitment("package-manifest"),
        "payload_tree_sha256": _commitment("payload-tree"),
        "product_build_sha256": _commitment("product-build"),
        "installer_build_sha256": _commitment("installer-build"),
        "backend_sha256": _commitment("backend"),
        "session_sha256": _commitment("session"),
        "observed_at_utc": "2026-09-03T00:01:00Z",
        "simultaneous_current": True,
    }
    values.update(overrides)
    return installation._fixture_only_issue_pair_readback(**values)


def _consume_pair_fixture(
    pair: object,
    snapshot: object,
    descriptor: dict[str, object],
    **overrides: object,
):
    values: dict[str, object] = {
        "root_snapshot": snapshot,
        "expected_operation_id": "operation-1",
        "expected_ticket_event_sha256": _commitment("ticket"),
        "expected_install_instance_id": descriptor["install_instance_id"],
        "expected_descriptor_document": descriptor,
        "expected_predecessor_terminal_sha256": _commitment("no-predecessor"),
        "expected_successor_reservation_sha256": _commitment("reservation"),
        "expected_installation_revision": 1,
        "expected_package_manifest_sha256": _commitment("package-manifest"),
        "expected_payload_tree_sha256": _commitment("payload-tree"),
        "expected_product_build_sha256": _commitment("product-build"),
        "expected_installer_build_sha256": _commitment("installer-build"),
        "expected_backend_sha256": _commitment("backend"),
        "expected_session_sha256": _commitment("session"),
        "consumer_operation_key": "c1",
    }
    values.update(overrides)
    return installation._fixture_only_consume_pair_readback(pair, **values)


def test_installer_cli_mutation_fails_closed_without_private_composition(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    sentinel = install_root / "preserve.txt"
    sentinel.write_bytes(b"preserve")

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PRIVATE_COMPOSITION_REQUIRED$",
    ):
        installer_main(
            [
                "provision-readback",
                "--install-root",
                str(install_root),
                "--installer-manifest-sha256",
                MANIFEST_SHA,
            ]
        )

    assert sentinel.read_bytes() == b"preserve"
    assert sorted(path.name for path in install_root.iterdir()) == ["preserve.txt"]


def test_public_mutation_surfaces_fail_before_arguments_hooks_or_filesystem(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "selected"
    hook_calls: list[tuple[str, Path]] = []

    def hook(stage: str, path: Path) -> None:
        hook_calls.append((stage, path))

    calls = (
        lambda: public_provision(
            install_root,
            installer_manifest_sha256="caller-controlled",
            now="caller-controlled",
        ),
        lambda: public_provision_and_write(
            install_root,
            installer_manifest_sha256="caller-controlled",
            now="caller-controlled",
            failure_injector=hook,
        ),
        lambda: public_write_readback(object(), failure_injector=hook),
    )
    for call in calls:
        with pytest.raises(
            MontageLearningInstallationError,
            match="^TASK063_PRIVATE_COMPOSITION_REQUIRED$",
        ) as caught:
            call()
        assert str(install_root) not in str(caught.value)

    assert hook_calls == []
    assert not install_root.exists()
    assert not {
        "_legacy_test_only_provision_installed_bridge",
        "_legacy_test_only_provision_and_write_installer_readback",
        "_legacy_test_only_write_installer_readback",
    }.intersection(vars(installation))


@pytest.mark.parametrize(
    ("action_name", "predecessor_bound", "existing", "pair_action"),
    [
        ("FIRST_PROVISION", False, (), "PAIR_GENESIS"),
        (
            "ADOPT_EXISTING",
            True,
            installation._DIRECTORY_RELATIVE_PATHS,
            "PAIR_ADOPTION",
        ),
        (
            "VERIFY_REPAIR",
            True,
            installation._DIRECTORY_RELATIVE_PATHS,
            "NO_PAIR_SUCCESSOR",
        ),
        (
            "PUBLISH_INSTALL_REVISION",
            True,
            installation._DIRECTORY_RELATIVE_PATHS,
            "REVISION",
        ),
        ("PORTABLE_REBIND", True, (), "REBIND"),
    ],
)
def test_fixture_root_semantic_snapshot_is_data_only_without_effect(
    tmp_path: Path,
    action_name: str,
    predecessor_bound: bool,
    existing: tuple[str, ...],
    pair_action: str,
) -> None:
    selected_root = tmp_path / "Product root 日本語"
    selected_root.mkdir()
    sentinel = selected_root / "preserve.txt"
    sentinel.write_bytes(b"preserve")

    snapshot = installation._fixture_only_build_selected_root_semantic_snapshot(
        action=installation._InstallationAction[action_name],
        selected_root=selected_root,
        predecessor_bound=predecessor_bound,
        existing_relative_directories=existing,
        selected_root_security_sha256=ROOT_SECURITY_SHA,
    )

    assert snapshot.directory_paths == tuple(
        selected_root.joinpath(*relative_path.split("/"))
        for relative_path in installation._DIRECTORY_RELATIVE_PATHS
    )
    assert snapshot.expected_pair_action == pair_action
    assert snapshot.fixture_only is True
    assert snapshot.authority_created is False
    assert snapshot.native_effect_executed is False
    assert not {
        "_InstallationAction",
        "_SelectedInstallRootSemanticSnapshotFixture",
        "_fixture_only_build_selected_root_semantic_snapshot",
    }.intersection(installation.__all__)
    projection = snapshot.public_projection()
    assert projection["authority_created"] is False
    assert projection["connector_enabled"] is False
    assert projection["activation_authorized"] is False
    assert str(selected_root) not in json.dumps(projection, ensure_ascii=False)
    assert sorted(path.name for path in selected_root.iterdir()) == ["preserve.txt"]

    with pytest.raises(TypeError, match="NONCOPYABLE"):
        copy.copy(snapshot)
    with pytest.raises(TypeError, match="NONCOPYABLE"):
        copy.deepcopy(snapshot)
    with pytest.raises(TypeError, match="NONSERIALIZABLE"):
        pickle.dumps(snapshot)


def test_root_semantic_snapshot_forgery_never_creates_consumer_authority(
    tmp_path: Path,
) -> None:
    _, snapshot = _fixture_root_snapshot(tmp_path)
    descriptor = _v2_descriptor_fixture()

    authority_forgery = replace(snapshot, authority_created=True)
    pair = _issue_pair_fixture(snapshot, descriptor)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _consume_pair_fixture(pair, authority_forgery, descriptor)

    semantic_forgery = replace(
        snapshot,
        directory_set_sha256=_commitment("forged-directory-set"),
    )
    fresh_pair = _issue_pair_fixture(snapshot, descriptor)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _consume_pair_fixture(fresh_pair, semantic_forgery, descriptor)

    mapping_pair = _issue_pair_fixture(snapshot, descriptor)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _consume_pair_fixture(mapping_pair, snapshot.public_projection(), descriptor)

    assert snapshot.authority_created is False
    assert snapshot.fixture_only is True


def test_fixture_root_snapshot_rejects_unknown_action_before_touching_root() -> None:
    class RootMustNotBeRead:
        def __fspath__(self) -> str:
            raise AssertionError("root must not be read for an unknown action")

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_ROOT_SNAPSHOT_REJECTED$",
    ):
        installation._fixture_only_build_selected_root_semantic_snapshot(
            action="FIRST_PROVISION",
            selected_root=RootMustNotBeRead(),
            predecessor_bound=False,
            existing_relative_directories=(),
            selected_root_security_sha256=ROOT_SECURITY_SHA,
        )


@pytest.mark.parametrize("selected_root", ["relative/root", "../escape"])
def test_fixture_root_snapshot_rejects_relative_or_traversing_root(
    selected_root: str,
) -> None:
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_ROOT_SNAPSHOT_REJECTED$",
    ):
        installation._fixture_only_build_selected_root_semantic_snapshot(
            action=installation._InstallationAction.FIRST_PROVISION,
            selected_root=selected_root,
            predecessor_bound=False,
            existing_relative_directories=(),
            selected_root_security_sha256=ROOT_SECURITY_SHA,
        )


@pytest.mark.parametrize(
    ("action_name", "predecessor_bound", "existing"),
    [
        ("FIRST_PROVISION", True, ()),
        ("FIRST_PROVISION", False, ("data",)),
        ("ADOPT_EXISTING", False, installation._DIRECTORY_RELATIVE_PATHS),
        ("ADOPT_EXISTING", True, ()),
        ("VERIFY_REPAIR", True, ("Data",)),
        ("PUBLISH_INSTALL_REVISION", True, ("data", "data")),
        ("PORTABLE_REBIND", True, ("data",)),
    ],
)
def test_fixture_root_snapshot_rejects_unbound_existing_or_case_alias_without_effect(
    tmp_path: Path,
    action_name: str,
    predecessor_bound: bool,
    existing: tuple[str, ...],
) -> None:
    selected_root = tmp_path / "selected"
    selected_root.mkdir()
    sentinel = selected_root / "preserve.txt"
    sentinel.write_bytes(b"preserve")

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_ROOT_SNAPSHOT_REJECTED$",
    ):
        installation._fixture_only_build_selected_root_semantic_snapshot(
            action=installation._InstallationAction[action_name],
            selected_root=selected_root,
            predecessor_bound=predecessor_bound,
            existing_relative_directories=existing,
            selected_root_security_sha256=ROOT_SECURITY_SHA,
        )

    assert sentinel.read_bytes() == b"preserve"
    assert sorted(path.name for path in selected_root.iterdir()) == ["preserve.txt"]


@pytest.mark.parametrize(
    "fault_stage",
    [
        "after_action_validation",
        "after_root_validation",
        "after_directory_derivation",
        "before_fixture_projection",
    ],
)
def test_fixture_root_snapshot_fault_ports_have_zero_filesystem_effect(
    tmp_path: Path,
    fault_stage: str,
) -> None:
    selected_root = tmp_path / "selected"
    selected_root.mkdir()
    sentinel = selected_root / "preserve.txt"
    sentinel.write_bytes(b"preserve")

    def fault(stage: str) -> None:
        if stage == fault_stage:
            raise RuntimeError("injected root-snapshot fixture fault")

    with pytest.raises(RuntimeError, match="injected root-snapshot fixture fault"):
        installation._fixture_only_build_selected_root_semantic_snapshot(
            action=installation._InstallationAction.FIRST_PROVISION,
            selected_root=selected_root,
            predecessor_bound=False,
            existing_relative_directories=(),
            selected_root_security_sha256=ROOT_SECURITY_SHA,
            fault_port=fault,
        )

    assert sentinel.read_bytes() == b"preserve"
    assert sorted(path.name for path in selected_root.iterdir()) == ["preserve.txt"]


def test_pair_consumer_issues_one_path_free_data_only_installed_readback(
    tmp_path: Path,
) -> None:
    selected_root, plan = _fixture_root_snapshot(tmp_path)
    sentinel = selected_root / "preserve.txt"
    sentinel.write_bytes(b"preserve")
    descriptor = _v2_descriptor_fixture()
    pair = _issue_pair_fixture(plan, descriptor)

    installed = _consume_pair_fixture(pair, plan, descriptor)

    assert installed.fixture_only is True
    assert installed.authority_created is False
    assert installed.native_effect_executed is False
    projection = installation._fixture_only_consume_installed_readback(
        installed,
        consumer_operation_key="c1",
    )
    assert projection["status"] == "VERIFIED_DISABLED"
    assert projection["authority_created"] is False
    assert projection["currentness_selected"] is False
    assert projection["connector_enabled"] is False
    assert projection["activation_authorized"] is False
    supplied_hash = projection.pop("audit_self_hash")
    assert supplied_hash == installation.sha256_json(projection)
    public_bytes = json.dumps(projection, ensure_ascii=False)
    assert str(selected_root) not in public_bytes
    assert str(descriptor["install_instance_id"]) not in public_bytes
    assert sentinel.read_bytes() == b"preserve"
    assert sorted(path.name for path in selected_root.iterdir()) == ["preserve.txt"]

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REUSED$",
    ):
        _consume_pair_fixture(pair, plan, descriptor)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_INSTALLED_READBACK_REUSED$",
    ):
        installation._fixture_only_consume_installed_readback(
            installed,
            consumer_operation_key="c1",
        )


def test_pair_repair_has_no_successor_and_revision_publish_keeps_pair_terminal(
    tmp_path: Path,
) -> None:
    descriptor = _v2_descriptor_fixture()
    stable_terminal = _commitment("stable-pair-terminal")
    repair_snapshot = _lifecycle_root_snapshot(
        tmp_path,
        "VERIFY_REPAIR",
        ROOT_SECURITY_SHA,
    )
    repair = _issue_pair_fixture(
        repair_snapshot,
        descriptor,
        action=installation._InstallationAction.VERIFY_REPAIR,
        pair_action="NO_PAIR_SUCCESSOR",
        pair_terminal_sha256=stable_terminal,
        predecessor_terminal_sha256=stable_terminal,
        successor_reservation_sha256=None,
    )
    installed = _consume_pair_fixture(
        repair,
        repair_snapshot,
        descriptor,
        expected_predecessor_terminal_sha256=stable_terminal,
        expected_successor_reservation_sha256=None,
    )
    assert installed.pair_terminal_sha256 == stable_terminal

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _issue_pair_fixture(
            repair_snapshot,
            descriptor,
            action=installation._InstallationAction.VERIFY_REPAIR,
            pair_action="NO_PAIR_SUCCESSOR",
            pair_terminal_sha256=stable_terminal,
            predecessor_terminal_sha256=stable_terminal,
            successor_reservation_sha256=_commitment("forbidden-reservation"),
        )
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _issue_pair_fixture(
            repair_snapshot,
            descriptor,
            action=installation._InstallationAction.VERIFY_REPAIR,
            pair_action="PAIR_ADOPTION",
            pair_terminal_sha256=stable_terminal,
            predecessor_terminal_sha256=stable_terminal,
            successor_reservation_sha256=None,
        )

    revision_snapshot = _lifecycle_root_snapshot(
        tmp_path,
        "PUBLISH_INSTALL_REVISION",
        ROOT_SECURITY_SHA,
    )
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _issue_pair_fixture(
            revision_snapshot,
            descriptor,
            action=installation._InstallationAction.PUBLISH_INSTALL_REVISION,
            pair_action="REVISION",
            pair_terminal_sha256=_commitment("changed-pair-terminal"),
            predecessor_terminal_sha256=stable_terminal,
        )


def test_installation_readback_schema_pair_is_byte_identical_and_closed() -> None:
    repository_root = Path(__file__).parents[1]
    root_schema = (
        repository_root
        / "schemas"
        / "montage-learning-installation-readback.schema.json"
    )
    packaged_schema = (
        repository_root
        / "src"
        / "ai_video_production"
        / "schema_resources"
        / "montage-learning-installation-readback.schema.json"
    )

    assert root_schema.read_bytes() == packaged_schema.read_bytes()
    schema = json.loads(root_schema.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["audit_self_hash"]["pattern"] == (
        "^sha256:[0-9a-f]{64}$"
    )


def test_installation_readback_projection_validates_hash_and_closed_schema(
    tmp_path: Path,
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    _, plan = _fixture_root_snapshot(tmp_path)
    descriptor = _v2_descriptor_fixture()
    installed = _consume_pair_fixture(
        _issue_pair_fixture(plan, descriptor),
        plan,
        descriptor,
    )
    projection = installation._fixture_only_consume_installed_readback(
        installed,
        consumer_operation_key="c1",
    )
    body = dict(projection)
    supplied_hash = body.pop("audit_self_hash")
    assert supplied_hash == installation.sha256_json(body)

    schema_path = (
        Path(__file__).parents[1]
        / "schemas"
        / "montage-learning-installation-readback.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    validator.validate(projection)

    with pytest.raises(jsonschema.ValidationError):
        validator.validate({**projection, "unknown": "rejected"})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({**projection, "audit_self_hash": "sha256:invalid"})


def test_pair_consumer_rejects_public_direct_copy_and_serialized_forgery(
    tmp_path: Path,
) -> None:
    _, plan = _fixture_root_snapshot(tmp_path)
    descriptor = _v2_descriptor_fixture()
    pair = _issue_pair_fixture(plan, descriptor)
    assert not {
        "_InstallationPairReadbackFixture",
        "_InstallationReadbackFixture",
        "_fixture_only_issue_pair_readback",
        "_fixture_only_consume_pair_readback",
        "_fixture_only_consume_installed_readback",
    }.intersection(installation.__all__)

    with pytest.raises(TypeError, match="NONCOPYABLE"):
        copy.copy(pair)
    with pytest.raises(TypeError, match="NONCOPYABLE"):
        copy.deepcopy(pair)
    with pytest.raises(TypeError, match="NONSERIALIZABLE"):
        pickle.dumps(pair)

    forged = replace(pair)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _consume_pair_fixture(forged, plan, descriptor)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _consume_pair_fixture(pair.__dict__ if hasattr(pair, "__dict__") else {}, plan, descriptor)

    installed = _consume_pair_fixture(pair, plan, descriptor)
    with pytest.raises(TypeError, match="NONCOPYABLE"):
        copy.copy(installed)
    with pytest.raises(TypeError, match="NONSERIALIZABLE"):
        pickle.dumps(installed)
    installed_forgery = replace(installed)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_INSTALLED_READBACK_REJECTED$",
    ):
        installation._fixture_only_consume_installed_readback(
            installed_forgery,
            consumer_operation_key="c1",
        )

    projection = installation._fixture_only_consume_installed_readback(
        installed,
        consumer_operation_key="c1",
    )
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_INSTALLED_READBACK_REJECTED$",
    ):
        installation._fixture_only_consume_installed_readback(
            projection,
            consumer_operation_key="c1",
        )


@pytest.mark.parametrize(
    "mutation",
    ["extra", "wrong_hash", "wrong_instance", "legacy_updated_at"],
)
def test_pair_fixture_rejects_noncanonical_descriptor_semantics_before_issue(
    tmp_path: Path,
    mutation: str,
) -> None:
    selected_root, plan = _fixture_root_snapshot(tmp_path)
    descriptor = _v2_descriptor_fixture()
    if mutation == "extra":
        descriptor["extra"] = "forged"
    elif mutation == "wrong_hash":
        descriptor["descriptor_sha256"] = _commitment("wrong-descriptor")
    elif mutation == "wrong_instance":
        descriptor["install_instance_id"] = "foreign"
    else:
        descriptor["updated_at"] = "2026-09-03T00:02:00Z"

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _issue_pair_fixture(plan, descriptor)

    assert list(selected_root.iterdir()) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"descriptor_generation_sha256": _commitment("other-generation")},
        {"owner_generation_sha256": _commitment("other-generation")},
        {"owner_instance_id": "bvp-install-" + "2" * 32},
        {"owner_contract_profile": "forged-profile"},
        {"simultaneous_current": False},
        {
            "owner_identity_sha256": _commitment("descriptor-identity"),
        },
        {"session_sha256": _commitment("wrong-session")},
    ],
)
def test_pair_consumer_burns_semantic_or_generation_mismatch(
    tmp_path: Path,
    overrides: dict[str, object],
) -> None:
    selected_root, plan = _fixture_root_snapshot(tmp_path)
    descriptor = _v2_descriptor_fixture()
    pair = _issue_pair_fixture(plan, descriptor, **overrides)

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _consume_pair_fixture(pair, plan, descriptor)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REUSED$",
    ):
        _consume_pair_fixture(pair, plan, descriptor)

    assert list(selected_root.iterdir()) == []


def test_pair_consumer_exception_and_wrong_installed_consumer_burn_once(
    tmp_path: Path,
) -> None:
    _, plan = _fixture_root_snapshot(tmp_path)
    descriptor = _v2_descriptor_fixture()
    pair = _issue_pair_fixture(plan, descriptor)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _consume_pair_fixture(
            pair,
            plan,
            descriptor,
            expected_package_manifest_sha256=_commitment("wrong-package"),
        )
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REUSED$",
    ):
        _consume_pair_fixture(pair, plan, descriptor)

    fresh_pair = _issue_pair_fixture(plan, descriptor)
    installed = _consume_pair_fixture(fresh_pair, plan, descriptor)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_INSTALLED_READBACK_REJECTED$",
    ):
        installation._fixture_only_consume_installed_readback(
            installed,
            consumer_operation_key="bad",
        )
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_INSTALLED_READBACK_REUSED$",
    ):
        installation._fixture_only_consume_installed_readback(
            installed,
            consumer_operation_key="c1",
        )


def test_pair_consumer_requires_issue_bound_exact_operation_key_and_burns(
    tmp_path: Path,
) -> None:
    _, plan = _fixture_root_snapshot(tmp_path)
    descriptor = _v2_descriptor_fixture()
    pair = _issue_pair_fixture(
        plan,
        descriptor,
        consumer_operation_key="ca",
    )

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REJECTED$",
    ):
        _consume_pair_fixture(
            pair,
            plan,
            descriptor,
            consumer_operation_key="cb",
        )
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_PAIR_READBACK_REUSED$",
    ):
        _consume_pair_fixture(
            pair,
            plan,
            descriptor,
            consumer_operation_key="ca",
        )


def test_pair_consumer_concurrent_double_call_has_one_success(
    tmp_path: Path,
) -> None:
    _, plan = _fixture_root_snapshot(tmp_path)
    descriptor = _v2_descriptor_fixture()
    pair = _issue_pair_fixture(plan, descriptor)
    barrier = threading.Barrier(2)
    results: list[str] = []

    def consume() -> None:
        barrier.wait()
        try:
            _consume_pair_fixture(pair, plan, descriptor)
        except MontageLearningInstallationError as exc:
            results.append(str(exc))
        else:
            results.append("SUCCESS")

    threads = [threading.Thread(target=consume) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(results) == ["SUCCESS", "TASK063_PAIR_READBACK_REUSED"]


def test_installed_readback_concurrent_double_call_has_one_success(
    tmp_path: Path,
) -> None:
    _, plan = _fixture_root_snapshot(tmp_path)
    descriptor = _v2_descriptor_fixture()
    installed = _consume_pair_fixture(
        _issue_pair_fixture(plan, descriptor),
        plan,
        descriptor,
    )
    barrier = threading.Barrier(2)
    results: list[str] = []

    def consume() -> None:
        barrier.wait()
        try:
            installation._fixture_only_consume_installed_readback(
                installed,
                consumer_operation_key="c1",
            )
        except MontageLearningInstallationError as exc:
            results.append(str(exc))
        else:
            results.append("SUCCESS")

    threads = [threading.Thread(target=consume) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(results) == ["SUCCESS", "TASK063_INSTALLED_READBACK_REUSED"]


def test_lifecycle_models_first_repair_revision_adoption_and_rebind_without_effect(
    tmp_path: Path,
) -> None:
    instance_id = "bvp-install-" + "1" * 32
    root_one = _commitment("root-one")
    root_two = _commitment("root-two")
    pair_one = _commitment("pair-one")
    package_one = _commitment("package-one")
    payload_one = _commitment("payload-one")
    product_one = _commitment("product-one")
    installer_one = _commitment("installer-one")

    first = _plan_lifecycle(
        root_snapshot=_lifecycle_root_snapshot(tmp_path, "FIRST_PROVISION", root_one),
        current=None,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=pair_one,
        expected_pair_terminal_sha256=_commitment("terminal-one"),
        package_manifest_sha256=package_one,
        payload_tree_sha256=payload_one,
        product_build_sha256=product_one,
        installer_build_sha256=installer_one,
    )
    repaired = _plan_lifecycle(
        root_snapshot=_lifecycle_root_snapshot(tmp_path, "VERIFY_REPAIR", root_one),
        current=first,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=pair_one,
        expected_pair_terminal_sha256=first.pair_terminal_sha256,
        package_manifest_sha256=package_one,
        payload_tree_sha256=payload_one,
        product_build_sha256=product_one,
        installer_build_sha256=installer_one,
    )
    revised = _plan_lifecycle(
        root_snapshot=_lifecycle_root_snapshot(
            tmp_path,
            "PUBLISH_INSTALL_REVISION",
            root_one,
        ),
        current=repaired,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=pair_one,
        expected_pair_terminal_sha256=repaired.pair_terminal_sha256,
        package_manifest_sha256=_commitment("package-two"),
        payload_tree_sha256=_commitment("payload-two"),
        product_build_sha256=_commitment("product-two"),
        installer_build_sha256=_commitment("installer-two"),
    )
    adopted = _plan_lifecycle(
        root_snapshot=_lifecycle_root_snapshot(tmp_path, "ADOPT_EXISTING", root_one),
        current=revised,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=pair_one,
        expected_pair_terminal_sha256=_commitment("terminal-three"),
        package_manifest_sha256=revised.package_manifest_sha256,
        payload_tree_sha256=revised.payload_tree_sha256,
        product_build_sha256=revised.product_build_sha256,
        installer_build_sha256=revised.installer_build_sha256,
    )
    rebound = _plan_lifecycle(
        root_snapshot=_lifecycle_root_snapshot(tmp_path, "PORTABLE_REBIND", root_two),
        current=adopted,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=_commitment("pair-two"),
        expected_pair_terminal_sha256=_commitment("terminal-four"),
        package_manifest_sha256=adopted.package_manifest_sha256,
        payload_tree_sha256=adopted.payload_tree_sha256,
        product_build_sha256=adopted.product_build_sha256,
        installer_build_sha256=adopted.installer_build_sha256,
    )

    assert first.installation_revision == 1
    assert repaired.installation_revision == 1
    assert repaired.pair_generation_sha256 == first.pair_generation_sha256
    assert revised.installation_revision == 2
    assert revised.pair_generation_sha256 == first.pair_generation_sha256
    assert revised.pair_terminal_sha256 == repaired.pair_terminal_sha256
    assert revised.revision_terminal_sha256 != repaired.revision_terminal_sha256
    assert (
        revised.predecessor_revision_terminal_sha256
        == repaired.revision_terminal_sha256
    )
    assert repaired.successor_reservation_sha256 is None
    assert adopted.installation_revision == 2
    assert adopted.install_instance_id == instance_id
    assert rebound.installation_revision == 2
    assert rebound.install_instance_id == instance_id
    assert rebound.pair_generation_sha256 != adopted.pair_generation_sha256
    assert rebound.selected_root_security_sha256 == root_two
    assert all(list(path.iterdir()) == [] for path in tmp_path.iterdir())

    projection = rebound.public_projection()
    assert projection["authority_created"] is False
    assert projection["preserve_learning_data"] is True
    assert instance_id not in json.dumps(projection)
    assert not {
        "_InstallationLifecycleStateFixture",
        "_fixture_only_plan_lifecycle_transition",
        "_fixture_only_uninstall_preservation_projection",
    }.intersection(installation.__all__)
    with pytest.raises(TypeError, match="NONCOPYABLE"):
        copy.copy(rebound)
    with pytest.raises(TypeError, match="NONSERIALIZABLE"):
        pickle.dumps(rebound)


@pytest.mark.parametrize(
    ("action_name", "changes"),
    [
        ("VERIFY_REPAIR", {"expected_install_instance_id": "bvp-install-" + "2" * 32}),
        ("VERIFY_REPAIR", {"expected_pair_generation_sha256": _commitment("wrong-pair")}),
        ("VERIFY_REPAIR", {"package_manifest_sha256": _commitment("changed-package")}),
        (
            "VERIFY_REPAIR",
            {"expected_pair_terminal_sha256": _commitment("changed-pair-terminal")},
        ),
        (
            "VERIFY_REPAIR",
            {"successor_reservation_sha256": _commitment("forbidden-reservation")},
        ),
        ("ADOPT_EXISTING", {"expected_pair_terminal_sha256": _commitment("terminal-one")}),
        ("ADOPT_EXISTING", {"payload_tree_sha256": _commitment("changed-payload")}),
        (
            "PUBLISH_INSTALL_REVISION",
            {"expected_pair_terminal_sha256": _commitment("changed-pair-terminal")},
        ),
        (
            "PUBLISH_INSTALL_REVISION",
            {
                "predecessor_revision_terminal_sha256": _commitment(
                    "wrong-revision-predecessor"
                )
            },
        ),
        (
            "PUBLISH_INSTALL_REVISION",
            {"revision_terminal_sha256": "CURRENT"},
        ),
    ],
)
def test_lifecycle_rejects_cross_instance_stale_pair_or_invalid_successor(
    tmp_path: Path,
    action_name: str,
    changes: dict[str, object],
) -> None:
    instance_id = "bvp-install-" + "1" * 32
    root_security = _commitment("root")
    pair_generation = _commitment("pair")
    current = _plan_lifecycle(
        root_snapshot=_lifecycle_root_snapshot(
            tmp_path,
            "FIRST_PROVISION",
            root_security,
        ),
        current=None,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=pair_generation,
        expected_pair_terminal_sha256=_commitment("terminal-one"),
        package_manifest_sha256=_commitment("package"),
        payload_tree_sha256=_commitment("payload"),
        product_build_sha256=_commitment("product"),
        installer_build_sha256=_commitment("installer"),
    )
    values: dict[str, object] = {
        "root_snapshot": _lifecycle_root_snapshot(tmp_path, action_name, root_security),
        "current": current,
        "expected_install_instance_id": instance_id,
        "expected_pair_generation_sha256": pair_generation,
        "expected_pair_terminal_sha256": (
            current.pair_terminal_sha256
            if action_name in {"VERIFY_REPAIR", "PUBLISH_INSTALL_REVISION"}
            else _commitment("terminal-two")
        ),
        "package_manifest_sha256": current.package_manifest_sha256,
        "payload_tree_sha256": current.payload_tree_sha256,
        "product_build_sha256": current.product_build_sha256,
        "installer_build_sha256": current.installer_build_sha256,
    }
    if action_name == "PUBLISH_INSTALL_REVISION":
        values["package_manifest_sha256"] = _commitment("package-two")
    values.update(changes)
    if values.get("revision_terminal_sha256") == "CURRENT":
        values["revision_terminal_sha256"] = current.revision_terminal_sha256

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_LIFECYCLE_REJECTED$",
    ):
        _plan_lifecycle(**values)

    assert all(list(path.iterdir()) == [] for path in tmp_path.iterdir())


@pytest.mark.parametrize(
    "changes",
    [
        {"selected_root": "same"},
        {"expected_pair_generation_sha256": _commitment("pair-one")},
        {"package_manifest_sha256": _commitment("changed-package")},
    ],
)
def test_lifecycle_portable_rebind_rejects_same_root_pair_or_changed_package(
    tmp_path: Path,
    changes: dict[str, object],
) -> None:
    instance_id = "bvp-install-" + "1" * 32
    root_one = _commitment("root-one")
    root_two = _commitment("root-two")
    current = _plan_lifecycle(
        root_snapshot=_lifecycle_root_snapshot(tmp_path, "FIRST_PROVISION", root_one),
        current=None,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=_commitment("pair-one"),
        expected_pair_terminal_sha256=_commitment("terminal-one"),
        package_manifest_sha256=_commitment("package"),
        payload_tree_sha256=_commitment("payload"),
        product_build_sha256=_commitment("product"),
        installer_build_sha256=_commitment("installer"),
    )
    target_root = root_one if changes.pop("selected_root", None) else root_two
    values: dict[str, object] = {
        "root_snapshot": _lifecycle_root_snapshot(
            tmp_path,
            "PORTABLE_REBIND",
            target_root,
        ),
        "current": current,
        "expected_install_instance_id": instance_id,
        "expected_pair_generation_sha256": _commitment("pair-two"),
        "expected_pair_terminal_sha256": _commitment("terminal-two"),
        "package_manifest_sha256": current.package_manifest_sha256,
        "payload_tree_sha256": current.payload_tree_sha256,
        "product_build_sha256": current.product_build_sha256,
        "installer_build_sha256": current.installer_build_sha256,
    }
    values.update(changes)

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_LIFECYCLE_REJECTED$",
    ):
        _plan_lifecycle(**values)


def test_lifecycle_first_provision_rejects_existing_state_without_effect(
    tmp_path: Path,
) -> None:
    instance_id = "bvp-install-" + "1" * 32
    root_security = _commitment("root")
    first_plan = _lifecycle_root_snapshot(
        tmp_path,
        "FIRST_PROVISION",
        root_security,
    )
    current = _plan_lifecycle(
        root_snapshot=first_plan,
        current=None,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=_commitment("pair"),
        expected_pair_terminal_sha256=_commitment("terminal"),
        package_manifest_sha256=_commitment("package"),
        payload_tree_sha256=_commitment("payload"),
        product_build_sha256=_commitment("product"),
        installer_build_sha256=_commitment("installer"),
    )

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_LIFECYCLE_REJECTED$",
    ):
        _plan_lifecycle(
            root_snapshot=first_plan,
            current=current,
            expected_install_instance_id=instance_id,
            expected_pair_generation_sha256=_commitment("other-pair"),
            expected_pair_terminal_sha256=_commitment("other-terminal"),
            package_manifest_sha256=current.package_manifest_sha256,
            payload_tree_sha256=current.payload_tree_sha256,
            product_build_sha256=current.product_build_sha256,
            installer_build_sha256=current.installer_build_sha256,
        )

    assert all(list(path.iterdir()) == [] for path in tmp_path.iterdir())


@pytest.mark.parametrize(
    "changes",
    [
        {"expected_predecessor_terminal_sha256": _commitment("stale-terminal")},
        {"requested_revision": 3},
        {"operation_id": "operation-first_provision-0"},
        {"successor_reservation_sha256": _commitment("same-reservation")},
    ],
)
def test_lifecycle_rejects_stale_predecessor_gap_and_reused_commitments(
    tmp_path: Path,
    changes: dict[str, object],
) -> None:
    instance_id = "bvp-install-" + "1" * 32
    root_security = _commitment("root")
    current = _plan_lifecycle(
        root_snapshot=_lifecycle_root_snapshot(tmp_path, "FIRST_PROVISION", root_security),
        current=None,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=_commitment("pair"),
        expected_pair_terminal_sha256=_commitment("terminal-one"),
        successor_reservation_sha256=_commitment("same-reservation"),
        package_manifest_sha256=_commitment("package"),
        payload_tree_sha256=_commitment("payload"),
        product_build_sha256=_commitment("product"),
        installer_build_sha256=_commitment("installer"),
    )
    values: dict[str, object] = {
        "root_snapshot": _lifecycle_root_snapshot(tmp_path, "VERIFY_REPAIR", root_security),
        "current": current,
        "expected_install_instance_id": instance_id,
        "expected_pair_generation_sha256": current.pair_generation_sha256,
        "expected_pair_terminal_sha256": current.pair_terminal_sha256,
        "package_manifest_sha256": current.package_manifest_sha256,
        "payload_tree_sha256": current.payload_tree_sha256,
        "product_build_sha256": current.product_build_sha256,
        "installer_build_sha256": current.installer_build_sha256,
    }
    values.update(changes)

    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_LIFECYCLE_REJECTED$",
    ):
        _plan_lifecycle(**values)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_LIFECYCLE_REUSED$",
    ):
        _plan_lifecycle(**values)


def test_lifecycle_rejects_dataclass_replace_and_concurrent_successor_fork(
    tmp_path: Path,
) -> None:
    instance_id = "bvp-install-" + "1" * 32
    root_security = _commitment("root")
    current = _plan_lifecycle(
        root_snapshot=_lifecycle_root_snapshot(tmp_path, "FIRST_PROVISION", root_security),
        current=None,
        expected_install_instance_id=instance_id,
        expected_pair_generation_sha256=_commitment("pair"),
        expected_pair_terminal_sha256=_commitment("terminal-one"),
        package_manifest_sha256=_commitment("package"),
        payload_tree_sha256=_commitment("payload"),
        product_build_sha256=_commitment("product"),
        installer_build_sha256=_commitment("installer"),
    )
    forged = replace(current)
    with pytest.raises(
        MontageLearningInstallationError,
        match="^TASK063_LIFECYCLE_REJECTED$",
    ):
        _plan_lifecycle(
            root_snapshot=_lifecycle_root_snapshot(tmp_path, "VERIFY_REPAIR", root_security),
            current=forged,
            expected_install_instance_id=instance_id,
            expected_pair_generation_sha256=current.pair_generation_sha256,
            expected_pair_terminal_sha256=current.pair_terminal_sha256,
            package_manifest_sha256=current.package_manifest_sha256,
            payload_tree_sha256=current.payload_tree_sha256,
            product_build_sha256=current.product_build_sha256,
            installer_build_sha256=current.installer_build_sha256,
        )

    barrier = threading.Barrier(2)
    results: list[str] = []

    def advance() -> None:
        barrier.wait()
        try:
            _plan_lifecycle(
                root_snapshot=_lifecycle_root_snapshot(
                    tmp_path,
                    "VERIFY_REPAIR",
                    root_security,
                ),
                current=current,
                expected_install_instance_id=instance_id,
                expected_pair_generation_sha256=current.pair_generation_sha256,
                expected_pair_terminal_sha256=current.pair_terminal_sha256,
                package_manifest_sha256=current.package_manifest_sha256,
                payload_tree_sha256=current.payload_tree_sha256,
                product_build_sha256=current.product_build_sha256,
                installer_build_sha256=current.installer_build_sha256,
            )
        except MontageLearningInstallationError as exc:
            results.append(str(exc))
        else:
            results.append("SUCCESS")

    threads = [threading.Thread(target=advance) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(results) == ["SUCCESS", "TASK063_LIFECYCLE_REUSED"]


def test_uninstall_projection_preserves_bridge_learning_and_history() -> None:
    projection = installation._fixture_only_uninstall_preservation_projection()

    assert projection == {
        "schema_version": "TASK063_UNINSTALL_PRESERVATION_FIXTURE_V1",
        "action": "UNINSTALL_PRESERVE",
        "bridge_data_preserved": True,
        "pair_history_preserved": True,
        "learning_data_preserved": True,
        "automatic_old_data_delete_count": 0,
        "fixed_programdata_fallback_count": 0,
        "fixture_only": True,
        "authority_created": False,
        "native_effect_executed": False,
    }


def test_custom_unicode_install_root_provisions_exact_relative_tree(tmp_path: Path) -> None:
    install_root = tmp_path / "BAI 動画 Production"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )

    assert discovery.layout.root == install_root / "data" / "montage-learning-bridge"
    assert discovery.descriptor.bridge_relative_path == BRIDGE_RELATIVE_PATH
    assert discovery.descriptor.install_instance_id.startswith("bvp-install-")
    for relative in (
        "learning-inbox",
        "learning-processing",
        "learning-quarantine",
        "learning-receipts",
        "preference",
        "preference/profiles",
        "state",
        "migration",
    ):
        assert (discovery.layout.root / relative).is_dir()
    assert not discovery.layout.current_profile.exists()
    assert discovery.public_receipt()["connector_enabled"] is False


def test_repair_preserves_instance_and_readback_detects_descriptor_tamper(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "app"
    install_root.mkdir()
    first = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )
    repaired = provision_installed_bridge(
        install_root,
        installer_manifest_sha256="sha256:" + "b" * 64,
        now="2026-08-30T01:00:00Z",
    )
    assert repaired.descriptor.install_instance_id == first.descriptor.install_instance_id
    assert repaired.descriptor.created_at == first.descriptor.created_at
    assert repaired.descriptor.updated_at == "2026-08-30T01:00:00Z"

    descriptor_path = repaired.layout.root / "bridge-instance.json"
    value = json.loads(descriptor_path.read_text(encoding="utf-8"))
    value["bridge_relative_path"] = "elsewhere"
    descriptor_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(MontageLearningInstallationError):
        discover_installed_bridge(install_root)


@pytest.mark.parametrize(
    "case",
    [
        "duplicate_equal",
        "duplicate_different",
        "nan",
        "infinity",
        "negative_infinity",
        "bom",
        "trailing",
        "control",
        "deep",
        "oversize",
        "array_pairs",
        "scalar",
    ],
)
def test_discovery_strict_descriptor_json_rejects_ambiguous_bytes_without_effect(
    tmp_path: Path,
    case: str,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )
    descriptor = discovery.layout.root / "bridge-instance.json"
    owner = discovery.layout.owner_manifest
    owner_before = owner.read_bytes()
    original = json.loads(descriptor.read_text(encoding="utf-8"))
    fields = ",".join(
        f"{json.dumps(key)}:{json.dumps(value)}"
        for key, value in original.items()
    )
    if case == "duplicate_equal":
        payload = (
            "{" + fields + ",\"install_instance_id\":"
            + json.dumps(original["install_instance_id"]) + "}"
        ).encode("utf-8")
    elif case == "duplicate_different":
        payload = (
            "{" + fields + ",\"install_instance_id\":\"bvp-install-"
            + "f" * 32 + "\"}"
        ).encode("utf-8")
    elif case == "nan":
        payload = b'{"value":NaN}'
    elif case == "infinity":
        payload = b'{"value":Infinity}'
    elif case == "negative_infinity":
        payload = b'{"value":-Infinity}'
    elif case == "bom":
        payload = b"\xef\xbb\xbf" + json.dumps(original).encode("utf-8")
    elif case == "trailing":
        payload = json.dumps(original).encode("utf-8") + b"\n{}"
    elif case == "control":
        payload = b'{"value":"unsafe\x00value"}'
    elif case == "deep":
        payload = b'{"value":' + (b"[" * 16) + b"0" + (b"]" * 16) + b"}"
    elif case == "oversize":
        payload = b" " * (installation._MAX_DESCRIPTOR_BYTES + 1)
    elif case == "array_pairs":
        payload = json.dumps(list(original.items())).encode("utf-8")
    else:
        payload = b"null"
    descriptor.write_bytes(payload)

    with pytest.raises(
        MontageLearningInstallationError,
        match="descriptor secure read rejected",
    ) as caught:
        discover_installed_bridge(install_root)

    assert descriptor.read_bytes() == payload
    assert owner.read_bytes() == owner_before
    assert str(descriptor) not in str(caught.value)
    assert repr(payload[:64]) not in str(caught.value)


def test_discovery_rejects_same_bytes_different_descriptor_identity_at_open_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    descriptor = discovery.layout.root / "bridge-instance.json"
    original_bytes = descriptor.read_bytes()
    original_identity = descriptor.stat(follow_symlinks=False).st_ino
    replacement = descriptor.with_name("replacement-descriptor.json")
    replacement.write_bytes(original_bytes)
    real_authority = installation.SecureAuthorityIO
    swapped = False

    def stage(name: str) -> None:
        nonlocal swapped
        if name == "target_lstat_complete" and not swapped:
            swapped = True
            os.replace(replacement, descriptor)

    def authority(root: object, **kwargs: object):
        return real_authority(root, **kwargs, _stage_hook=stage)

    monkeypatch.setattr(installation, "SecureAuthorityIO", authority)
    with pytest.raises(
        MontageLearningInstallationError,
        match="descriptor secure read rejected",
    ):
        discover_installed_bridge(install_root)

    assert swapped is True
    assert descriptor.read_bytes() == original_bytes
    assert descriptor.stat(follow_symlinks=False).st_ino != original_identity


def test_discovery_rejects_hardlinked_descriptor_without_mutating_pair(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    descriptor = discovery.layout.root / "bridge-instance.json"
    owner = discovery.layout.owner_manifest
    descriptor_before = descriptor.read_bytes()
    owner_before = owner.read_bytes()
    alias = tmp_path / "descriptor-alias.json"
    try:
        os.link(descriptor, alias)
    except OSError as exc:
        pytest.skip(f"hardlink creation unavailable: {exc}")

    with pytest.raises(
        MontageLearningInstallationError,
        match="descriptor secure read rejected",
    ):
        discover_installed_bridge(install_root)

    assert descriptor.read_bytes() == descriptor_before
    assert owner.read_bytes() == owner_before
    assert descriptor.stat(follow_symlinks=False).st_nlink == 2


def test_discovery_is_read_only_and_keeps_disabled_audit_projection(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    provisioned = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    descriptor = provisioned.layout.root / "bridge-instance.json"
    owner = provisioned.layout.owner_manifest
    before = {
        path: (path.read_bytes(), path.stat(follow_symlinks=False).st_ino)
        for path in (descriptor, owner)
    }

    discovered = discover_installed_bridge(install_root)

    assert discovered == provisioned
    assert discovered.public_receipt()["connector_enabled"] is False
    assert discovered.public_receipt()["activation_authorized"] is False
    assert {
        path: (path.read_bytes(), path.stat(follow_symlinks=False).st_ino)
        for path in (descriptor, owner)
    } == before


def test_packaged_installer_command_fails_closed_without_private_composition(
    tmp_path: Path,
) -> None:
    from ai_video_production.task036_packaged_entry import packaged_main

    install_root = tmp_path / "installed"
    install_root.mkdir()

    class ProbeMustNotRun:
        def require_ready(self):
            raise AssertionError("desktop probe must not run for installer operation")

    result = packaged_main(
        [
            "--bvp-installer-bridge",
            "provision",
            "--install-root",
            str(install_root),
            "--installer-manifest-sha256",
            MANIFEST_SHA,
        ],
        probe=ProbeMustNotRun(),
    )
    assert result == 3
    assert list(install_root.iterdir()) == []


def test_packaged_discover_cannot_publish_legacy_readback(
    tmp_path: Path,
) -> None:
    from ai_video_production.task036_packaged_entry import packaged_main

    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )

    result = packaged_main(
        [
            "--bvp-installer-bridge",
            "discover",
            "--install-root",
            str(install_root),
        ]
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    assert result == 3
    assert not target.exists()

    outside = tmp_path / "outside.json"
    rejected = packaged_main(
        [
            "--bvp-installer-bridge",
            "discover",
            "--install-root",
            str(install_root),
            "--receipt-output",
            str(outside),
        ]
    )
    assert rejected == 2
    assert not outside.exists()


def test_installer_readback_rejects_forged_layout_root(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    forged = replace(discovery, install_root=tmp_path / "other")

    with pytest.raises(MontageLearningInstallationError, match="layout mismatch"):
        write_installer_readback(forged)


@pytest.mark.parametrize("kind", ["directory", "symlink", "hardlink"])
def test_installer_readback_rejects_unsafe_existing_target(
    tmp_path: Path, kind: str
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    if kind == "directory":
        target.mkdir()
    elif kind == "symlink":
        source = tmp_path / "symlink-source"
        source.write_text("not a receipt", encoding="utf-8")
        try:
            target.symlink_to(source)
        except OSError as exc:
            pytest.skip(f"symlink creation unavailable: {exc}")
    else:
        source = tmp_path / "hardlink-source"
        source.write_text("not a receipt", encoding="utf-8")
        try:
            os.link(source, target)
        except OSError as exc:
            pytest.skip(f"hardlink creation unavailable: {exc}")

    with pytest.raises(MontageLearningInstallationError):
        write_installer_readback(discovery)


def test_installer_readback_rejects_ancestor_swap(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    migration = discovery.layout.migration
    outside = tmp_path / "outside"
    outside.mkdir()
    migration.rmdir()
    try:
        migration.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        migration.mkdir()
        pytest.skip(f"directory symlink creation unavailable: {exc}")

    with pytest.raises(MontageLearningInstallationError):
        write_installer_readback(discovery)
    assert not (outside / INSTALLER_READBACK_FILENAME).exists()


def test_installer_readback_replace_failure_preserves_existing_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    first = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )
    target = write_installer_readback(first)
    original = target.read_bytes()
    descriptor = first.layout.root / "bridge-instance.json"
    original_descriptor = descriptor.read_bytes()
    real_replace = legacy_installation.os.replace

    def fail_replace(source: object, destination: object) -> None:
        if Path(destination) == target:
            raise OSError("injected replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(legacy_installation.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256="sha256:" + "b" * 64,
            now="2026-08-30T01:00:00Z",
    )
    assert target.read_bytes() == original
    assert descriptor.read_bytes() == original_descriptor
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_installer_readback_rejects_unowned_existing_regular_file(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    original = b"not an installer receipt\n"
    target.write_bytes(original)

    with pytest.raises(MontageLearningInstallationError, match="JSON is invalid"):
        write_installer_readback(discovery)
    assert target.read_bytes() == original


def test_installer_readback_does_not_clobber_concurrent_new_target(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    concurrent = b"concurrent owner\n"

    def create_before_replace(phase: str, path: Path) -> None:
        if phase == "before_replace":
            path.write_bytes(concurrent)

    with pytest.raises(
        MontageLearningInstallationError,
        match="target identity changed",
    ):
        write_installer_readback(
            discovery,
            failure_injector=create_before_replace,
        )
    assert target.read_bytes() == concurrent
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_installer_readback_fails_on_post_write_readback_mismatch(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )

    def corrupt_before_readback(phase: str, path: Path) -> None:
        if phase == "before_readback":
            path.write_bytes(b"corrupt\n")

    with pytest.raises(MontageLearningInstallationError):
        write_installer_readback(
            discovery,
            failure_injector=corrupt_before_readback,
        )


def test_installer_readback_safe_update_is_exact_and_single_link(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    first = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )
    target = write_installer_readback(first)
    second, updated_target = provision_and_write_installer_readback(
        install_root,
        installer_manifest_sha256="sha256:" + "b" * 64,
        now="2026-08-30T01:00:00Z",
    )

    assert updated_target == target
    assert json.loads(target.read_text(encoding="utf-8")) == second.public_receipt()
    assert target.stat(follow_symlinks=False).st_nlink == 1
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_installer_readback_rejects_upper_ancestor_identity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    real_identity = legacy_installation._safe_directory_identity
    drift = False

    def identity(path: Path) -> tuple[int, int, str]:
        result = real_identity(path)
        if drift and path == tmp_path.parent:
            return result[0], result[1] + 1, result[2]
        return result

    def inject(phase: str, path: Path) -> None:
        nonlocal drift
        if phase == "after_temp_fsync":
            drift = True

    monkeypatch.setattr(legacy_installation, "_safe_directory_identity", identity)
    with pytest.raises(MontageLearningInstallationError, match="ancestor identity"):
        write_installer_readback(discovery, failure_injector=inject)
    assert not target.exists()


def test_installer_readback_rejects_forged_predecessor_descriptor(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = write_installer_readback(discovery)
    descriptor = discovery.layout.root / "bridge-instance.json"
    original_descriptor = descriptor.read_bytes()
    forged = json.loads(target.read_text(encoding="utf-8"))
    forged["descriptor_sha256"] = "sha256:" + "c" * 64
    target.write_text(json.dumps(forged), encoding="utf-8")
    original = target.read_bytes()

    with pytest.raises(MontageLearningInstallationError, match="transition mismatch"):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256="sha256:" + "b" * 64,
        )
    assert target.read_bytes() == original
    assert descriptor.read_bytes() == original_descriptor


def test_installer_readback_rejects_update_without_predecessor_receipt(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    descriptor = discovery.layout.root / "bridge-instance.json"
    original = descriptor.read_bytes()

    with pytest.raises(MontageLearningInstallationError):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256="sha256:" + "b" * 64,
        )
    assert descriptor.read_bytes() == original


def test_installer_readback_new_target_unlink_failure_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    real_unlink = Path.unlink
    injected = False

    def fail_once(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal injected
        if path.suffix == ".tmp" and not injected:
            injected = True
            raise OSError("injected temporary unlink failure")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_once)
    with pytest.raises(MontageLearningInstallationError, match="cleanup failed"):
        write_installer_readback(discovery)
    assert not target.exists()
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_unified_update_rolls_back_descriptor_and_receipt_on_readback_failure(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    first, target = provision_and_write_installer_readback(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )
    descriptor_path = first.layout.root / "bridge-instance.json"
    original_descriptor = descriptor_path.read_bytes()
    original_receipt = target.read_bytes()

    def corrupt(phase: str, path: Path) -> None:
        if phase == "before_readback":
            path.write_bytes(b"corrupt\n")

    with pytest.raises(MontageLearningInstallationError):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256="sha256:" + "b" * 64,
            now="2026-08-30T01:00:00Z",
            failure_injector=corrupt,
        )
    assert descriptor_path.read_bytes() == original_descriptor
    assert target.read_bytes() == original_receipt
    assert discover_installed_bridge(install_root) == first


def test_unified_fresh_failure_removes_unpublished_descriptor_and_receipt(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()

    def fail(phase: str, path: Path) -> None:
        if phase == "after_temp_fsync":
            raise OSError("injected publication failure")

    with pytest.raises(OSError, match="injected publication failure"):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256=MANIFEST_SHA,
            failure_injector=fail,
        )
    layout = installation.BridgeLayout.production(install_root)
    assert not (layout.root / "bridge-instance.json").exists()
    assert not (layout.migration / INSTALLER_READBACK_FILENAME).exists()


def test_active_source_has_no_programdata_bridge_literal() -> None:
    root = Path(__file__).resolve().parents[1]
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "src" / "ai_video_production").glob(
            "montage_learning*.py"
        )
    )
    assert r"C:\ProgramData\BAI Video Production\montage-learning-bridge" not in combined
