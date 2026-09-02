"""Installer-relative montage-learning bridge discovery and provisioning.

The active bridge is never derived from a machine-global fixed directory.  The
installer-selected application root is the only coordinate accepted here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
from typing import Callable
import uuid

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .montage_learning_file_bridge import (
    BRIDGE_CONTRACT_PROFILE,
    BridgeLayout,
    MontageLearningFileBridgeError,
    load_bridge_owner,
    provision_bridge,
)
from .secure_authority_io import SecureAuthorityIO, SecureAuthorityIOError
from .serialization import canonical_json_bytes, sha256_json


DESCRIPTOR_FILENAME = "bridge-instance.json"
DESCRIPTOR_MESSAGE_TYPE = "BvpMontageLearningBridgeInstance"
DESCRIPTOR_SCHEMA_VERSION = "1.0.0"
PRODUCT_ID = "BAI_VIDEO_PRODUCTION"
BRIDGE_RELATIVE_PATH = "data/montage-learning-bridge"
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_INSTANCE_RE = re.compile(r"^bvp-install-[0-9a-f]{32}$")
_MAX_DESCRIPTOR_BYTES = 64 * 1024
INSTALLER_READBACK_FILENAME = "installer-readback.json"
_MAX_INSTALLER_READBACK_BYTES = 64 * 1024
_WINDOWS_REPARSE_POINT = 0x400

ReceiptFailureInjector = Callable[[str, Path], None]
_PRIVATE_COMPOSITION_REQUIRED = "TASK063_PRIVATE_COMPOSITION_REQUIRED"
_ROOT_PLAN_REJECTED = "TASK063_ROOT_PLAN_REJECTED"
_PAIR_READBACK_REJECTED = "TASK063_PAIR_READBACK_REJECTED"
_PAIR_READBACK_REUSED = "TASK063_PAIR_READBACK_REUSED"
_INSTALLED_READBACK_REJECTED = "TASK063_INSTALLED_READBACK_REJECTED"
_INSTALLED_READBACK_REUSED = "TASK063_INSTALLED_READBACK_REUSED"
_LIFECYCLE_REJECTED = "TASK063_LIFECYCLE_REJECTED"
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_DIRECTORY_RELATIVE_PATHS = (
    "data",
    "data/montage-learning-bridge",
    "data/montage-learning-bridge/.immutable-authority",
    "data/montage-learning-bridge/learning-inbox",
    "data/montage-learning-bridge/learning-processing",
    "data/montage-learning-bridge/learning-quarantine",
    "data/montage-learning-bridge/learning-receipts",
    "data/montage-learning-bridge/preference",
    "data/montage-learning-bridge/preference/profiles",
    "data/montage-learning-bridge/state",
    "data/montage-learning-bridge/migration",
)


class MontageLearningInstallationError(ValueError):
    """Raised when an installer instance or descriptor is not trustworthy."""


class _InstallationAction(Enum):
    FIRST_PROVISION = "FIRST_PROVISION"
    ADOPT_EXISTING = "ADOPT_EXISTING"
    VERIFY_REPAIR = "VERIFY_REPAIR"
    PUBLISH_INSTALL_REVISION = "PUBLISH_INSTALL_REVISION"
    PORTABLE_REBIND = "PORTABLE_REBIND"


_PAIR_ACTION_BY_INSTALL_ACTION = {
    _InstallationAction.FIRST_PROVISION: "PAIR_GENESIS",
    _InstallationAction.ADOPT_EXISTING: "PAIR_ADOPTION",
    _InstallationAction.VERIFY_REPAIR: "NO_PAIR_SUCCESSOR",
    _InstallationAction.PUBLISH_INSTALL_REVISION: "REVISION",
    _InstallationAction.PORTABLE_REBIND: "REBIND",
}


@dataclass(frozen=True, repr=False, slots=True)
class _SelectedInstallRootPlanFixture:
    action: _InstallationAction
    selected_root: Path
    directory_paths: tuple[Path, ...]
    selected_root_security_sha256: str
    directory_set_sha256: str
    expected_pair_action: str
    predecessor_bound: bool
    fixture_only: bool = True
    authority_created: bool = False
    native_effect_executed: bool = False

    def public_projection(self) -> dict[str, object]:
        return {
            "schema_version": "TASK063_ROOT_PLAN_FIXTURE_V1",
            "action": self.action.value,
            "directory_set_sha256": self.directory_set_sha256,
            "expected_pair_action": self.expected_pair_action,
            "connector_enabled": False,
            "activation_authorized": False,
            "preserve_learning_data": True,
            "fixture_only": True,
            "authority_created": False,
            "native_effect_executed": False,
        }

    def __repr__(self) -> str:
        return "<_SelectedInstallRootPlanFixture redacted>"

    def __copy__(self):
        raise TypeError("TASK063_ROOT_PLAN_FIXTURE_NONCOPYABLE")

    def __deepcopy__(self, memo: object):
        raise TypeError("TASK063_ROOT_PLAN_FIXTURE_NONCOPYABLE")

    def __reduce_ex__(self, protocol: int):
        raise TypeError("TASK063_ROOT_PLAN_FIXTURE_NONSERIALIZABLE")


@dataclass(frozen=True, repr=False, slots=True)
class _InstallationPairReadbackFixture:
    action: _InstallationAction
    operation_id: str
    ticket_event_sha256: str
    install_instance_id: str
    descriptor_items: tuple[tuple[str, object], ...]
    owner_instance_id: str
    owner_contract_profile: str
    pair_action: str
    pair_generation_sha256: str
    descriptor_generation_sha256: str
    owner_generation_sha256: str
    pair_terminal_sha256: str
    predecessor_terminal_sha256: str
    successor_reservation_sha256: str
    installation_revision: int
    descriptor_identity_sha256: str
    owner_identity_sha256: str
    descriptor_sha256: str
    owner_manifest_sha256: str
    selected_root_security_sha256: str
    directory_set_sha256: str
    package_manifest_sha256: str
    payload_tree_sha256: str
    product_build_sha256: str
    installer_build_sha256: str
    backend_sha256: str
    session_sha256: str
    observed_at_utc: str
    simultaneous_current: bool
    fixture_only: bool = True
    authority_created: bool = False
    native_effect_executed: bool = False

    def __repr__(self) -> str:
        return "<_InstallationPairReadbackFixture redacted>"

    def __copy__(self):
        raise TypeError("TASK063_PAIR_READBACK_FIXTURE_NONCOPYABLE")

    def __deepcopy__(self, memo: object):
        raise TypeError("TASK063_PAIR_READBACK_FIXTURE_NONCOPYABLE")

    def __reduce_ex__(self, protocol: int):
        raise TypeError("TASK063_PAIR_READBACK_FIXTURE_NONSERIALIZABLE")


@dataclass(frozen=True, repr=False, slots=True)
class _InstallationReadbackFixture:
    action: _InstallationAction
    operation_id: str
    install_instance_id: str
    pair_terminal_sha256: str
    installation_revision: int
    descriptor_sha256: str
    owner_manifest_sha256: str
    package_manifest_sha256: str
    payload_tree_sha256: str
    product_build_sha256: str
    installer_build_sha256: str
    directory_set_sha256: str
    consumer_operation_key: str
    observed_at_utc: str
    fixture_only: bool = True
    authority_created: bool = False
    native_effect_executed: bool = False

    def public_projection(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": "2.0.0",
            "message_type": "BvpInstallationReadbackAudit",
            "task_id": "TASK-063",
            "action": self.action.value,
            "operation_commitment_sha256": sha256_json(
                {"operation_id": self.operation_id}
            ),
            "install_instance_commitment_sha256": sha256_json(
                {"install_instance_id": self.install_instance_id}
            ),
            "pair_terminal_sha256": self.pair_terminal_sha256,
            "installation_revision": self.installation_revision,
            "descriptor_sha256": self.descriptor_sha256,
            "owner_manifest_sha256": self.owner_manifest_sha256,
            "package_manifest_sha256": self.package_manifest_sha256,
            "payload_tree_sha256": self.payload_tree_sha256,
            "product_build_sha256": self.product_build_sha256,
            "installer_build_sha256": self.installer_build_sha256,
            "directory_set_sha256": self.directory_set_sha256,
            "observed_at_utc": self.observed_at_utc,
            "status": "VERIFIED_DISABLED",
            "reason_codes": ["FIXTURE_ONLY", "NATIVE_NOT_EXECUTED"],
            "connector_enabled": False,
            "activation_authorized": False,
            "native_install_observed": False,
            "fixture_only": True,
            "authority_created": False,
            "currentness_selected": False,
        }
        body["audit_self_hash"] = sha256_json(body)
        return body

    def __repr__(self) -> str:
        return "<_InstallationReadbackFixture redacted>"

    def __copy__(self):
        raise TypeError("TASK063_INSTALLED_READBACK_FIXTURE_NONCOPYABLE")

    def __deepcopy__(self, memo: object):
        raise TypeError("TASK063_INSTALLED_READBACK_FIXTURE_NONCOPYABLE")

    def __reduce_ex__(self, protocol: int):
        raise TypeError("TASK063_INSTALLED_READBACK_FIXTURE_NONSERIALIZABLE")


@dataclass(frozen=True, repr=False, slots=True)
class _InstallationLifecycleStateFixture:
    action: _InstallationAction
    install_instance_id: str
    pair_generation_sha256: str
    pair_terminal_sha256: str
    installation_revision: int
    selected_root_security_sha256: str
    package_manifest_sha256: str
    payload_tree_sha256: str
    product_build_sha256: str
    installer_build_sha256: str
    fixture_only: bool = True
    authority_created: bool = False
    native_effect_executed: bool = False

    def public_projection(self) -> dict[str, object]:
        return {
            "schema_version": "TASK063_LIFECYCLE_FIXTURE_V1",
            "action": self.action.value,
            "install_instance_commitment_sha256": sha256_json(
                {"install_instance_id": self.install_instance_id}
            ),
            "pair_generation_sha256": self.pair_generation_sha256,
            "pair_terminal_sha256": self.pair_terminal_sha256,
            "installation_revision": self.installation_revision,
            "package_manifest_sha256": self.package_manifest_sha256,
            "payload_tree_sha256": self.payload_tree_sha256,
            "product_build_sha256": self.product_build_sha256,
            "installer_build_sha256": self.installer_build_sha256,
            "connector_enabled": False,
            "activation_authorized": False,
            "preserve_learning_data": True,
            "fixture_only": True,
            "authority_created": False,
            "native_effect_executed": False,
        }

    def __repr__(self) -> str:
        return "<_InstallationLifecycleStateFixture redacted>"

    def __copy__(self):
        raise TypeError("TASK063_LIFECYCLE_FIXTURE_NONCOPYABLE")

    def __deepcopy__(self, memo: object):
        raise TypeError("TASK063_LIFECYCLE_FIXTURE_NONCOPYABLE")

    def __reduce_ex__(self, protocol: int):
        raise TypeError("TASK063_LIFECYCLE_FIXTURE_NONSERIALIZABLE")


_PAIR_FIXTURE_REGISTRY_LOCK = threading.Lock()
_PAIR_FIXTURE_REGISTRY: dict[int, _InstallationPairReadbackFixture] = {}
_PAIR_FIXTURE_BURNED_IDS: set[int] = set()
_INSTALLED_FIXTURE_REGISTRY_LOCK = threading.Lock()
_INSTALLED_FIXTURE_REGISTRY: dict[int, _InstallationReadbackFixture] = {}
_INSTALLED_FIXTURE_BURNED_IDS: set[int] = set()


@dataclass(frozen=True, slots=True)
class BridgeInstanceDescriptor:
    install_instance_id: str
    bridge_relative_path: str
    installer_manifest_sha256: str
    created_at: str
    updated_at: str
    descriptor_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": DESCRIPTOR_SCHEMA_VERSION,
            "message_type": DESCRIPTOR_MESSAGE_TYPE,
            "product_id": PRODUCT_ID,
            "install_instance_id": self.install_instance_id,
            "bridge_relative_path": self.bridge_relative_path,
            "installer_manifest_sha256": self.installer_manifest_sha256,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "descriptor_sha256": self.descriptor_sha256,
        }


@dataclass(frozen=True, slots=True)
class InstalledBridgeDiscovery:
    install_root: Path
    layout: BridgeLayout
    descriptor: BridgeInstanceDescriptor
    owner_manifest_sha256: str

    def public_receipt(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "message_type": "BvpMontageLearningBridgeDiscoveryReceipt",
            "product_id": PRODUCT_ID,
            "install_instance_id": self.descriptor.install_instance_id,
            "bridge_relative_path": self.descriptor.bridge_relative_path,
            "descriptor_sha256": self.descriptor.descriptor_sha256,
            "owner_manifest_sha256": self.owner_manifest_sha256,
            "capability": "INSTALL_RELATIVE_BRIDGE_DISCOVERY",
            "status": "READY_DISABLED_BY_DEFAULT",
            "connector_enabled": False,
            "activation_authorized": False,
        }


_RootPlanFaultPort = Callable[[str], None]


def _fixture_only_build_selected_root_plan(
    *,
    action: _InstallationAction,
    selected_root: str | Path,
    predecessor_bound: bool,
    existing_relative_directories: tuple[str, ...],
    selected_root_security_sha256: str,
    fault_port: _RootPlanFaultPort | None = None,
) -> _SelectedInstallRootPlanFixture:
    """Build an effect-free fixture projection of the closed root plan."""

    if type(action) is not _InstallationAction:
        _reject_root_plan()
    _call_root_plan_fault(fault_port, "after_action_validation")

    if type(predecessor_bound) is not bool:
        _reject_root_plan()
    try:
        _require_sha(
            selected_root_security_sha256,
            "selected_root_security_sha256",
        )
    except MontageLearningInstallationError:
        _reject_root_plan()
    if not (type(selected_root) is str or isinstance(selected_root, Path)):
        _reject_root_plan()
    root = Path(selected_root)
    if not root.is_absolute() or ".." in root.parts:
        _reject_root_plan()
    _call_root_plan_fault(fault_port, "after_root_validation")

    if type(existing_relative_directories) is not tuple or any(
        type(value) is not str for value in existing_relative_directories
    ):
        _reject_root_plan()
    if len(existing_relative_directories) != len(set(existing_relative_directories)):
        _reject_root_plan()
    planned = frozenset(_DIRECTORY_RELATIVE_PATHS)
    existing = frozenset(existing_relative_directories)
    if not existing.issubset(planned):
        _reject_root_plan()

    if action is _InstallationAction.FIRST_PROVISION:
        if predecessor_bound or existing:
            _reject_root_plan()
    elif action is _InstallationAction.PORTABLE_REBIND:
        if not predecessor_bound or existing:
            _reject_root_plan()
    elif not predecessor_bound or existing != planned:
        _reject_root_plan()

    directories = tuple(
        root.joinpath(*relative_path.split("/"))
        for relative_path in _DIRECTORY_RELATIVE_PATHS
    )
    root_parts = root.parts
    if any(path.parts[: len(root_parts)] != root_parts for path in directories):
        _reject_root_plan()
    _call_root_plan_fault(fault_port, "after_directory_derivation")

    directory_set_sha256 = sha256_json(
        {"relative_directories": list(_DIRECTORY_RELATIVE_PATHS)}
    )
    _call_root_plan_fault(fault_port, "before_fixture_projection")
    return _SelectedInstallRootPlanFixture(
        action=action,
        selected_root=root,
        directory_paths=directories,
        selected_root_security_sha256=selected_root_security_sha256,
        directory_set_sha256=directory_set_sha256,
        expected_pair_action=_PAIR_ACTION_BY_INSTALL_ACTION[action],
        predecessor_bound=predecessor_bound,
    )


def _call_root_plan_fault(
    fault_port: _RootPlanFaultPort | None,
    stage: str,
) -> None:
    if fault_port is not None:
        fault_port(stage)


def _reject_root_plan() -> None:
    raise MontageLearningInstallationError(_ROOT_PLAN_REJECTED) from None


def _fixture_only_issue_pair_readback(
    *,
    action: _InstallationAction,
    operation_id: str,
    ticket_event_sha256: str,
    install_instance_id: str,
    descriptor_document: dict[str, object],
    owner_instance_id: str,
    owner_contract_profile: str,
    pair_action: str,
    pair_generation_sha256: str,
    descriptor_generation_sha256: str,
    owner_generation_sha256: str,
    pair_terminal_sha256: str,
    predecessor_terminal_sha256: str,
    successor_reservation_sha256: str,
    installation_revision: int,
    descriptor_identity_sha256: str,
    owner_identity_sha256: str,
    owner_manifest_sha256: str,
    selected_root_security_sha256: str,
    directory_set_sha256: str,
    package_manifest_sha256: str,
    payload_tree_sha256: str,
    product_build_sha256: str,
    installer_build_sha256: str,
    backend_sha256: str,
    session_sha256: str,
    observed_at_utc: str,
    simultaneous_current: bool,
) -> _InstallationPairReadbackFixture:
    """Issue a registered data-only TASK-070 pair fixture with no authority."""

    try:
        descriptor = _validated_v2_descriptor_fixture(descriptor_document)
        _require_opaque_id(operation_id)
        if (
            type(action) is not _InstallationAction
            or type(install_instance_id) is not str
            or _INSTANCE_RE.fullmatch(install_instance_id) is None
            or type(owner_instance_id) is not str
            or type(owner_contract_profile) is not str
            or type(pair_action) is not str
            or type(installation_revision) is not int
            or installation_revision < 0
            or type(simultaneous_current) is not bool
        ):
            raise MontageLearningInstallationError(_PAIR_READBACK_REJECTED)
        for value in (
            ticket_event_sha256,
            pair_generation_sha256,
            descriptor_generation_sha256,
            owner_generation_sha256,
            pair_terminal_sha256,
            predecessor_terminal_sha256,
            successor_reservation_sha256,
            descriptor_identity_sha256,
            owner_identity_sha256,
            owner_manifest_sha256,
            selected_root_security_sha256,
            directory_set_sha256,
            package_manifest_sha256,
            payload_tree_sha256,
            product_build_sha256,
            installer_build_sha256,
            backend_sha256,
            session_sha256,
        ):
            _require_sha(value, "pair fixture commitment")
        _require_timestamp(observed_at_utc, "observed_at_utc")
    except (MontageLearningInstallationError, TypeError, ValueError):
        raise MontageLearningInstallationError(_PAIR_READBACK_REJECTED) from None

    fixture = _InstallationPairReadbackFixture(
        action=action,
        operation_id=operation_id,
        ticket_event_sha256=ticket_event_sha256,
        install_instance_id=install_instance_id,
        descriptor_items=tuple(descriptor.items()),
        owner_instance_id=owner_instance_id,
        owner_contract_profile=owner_contract_profile,
        pair_action=pair_action,
        pair_generation_sha256=pair_generation_sha256,
        descriptor_generation_sha256=descriptor_generation_sha256,
        owner_generation_sha256=owner_generation_sha256,
        pair_terminal_sha256=pair_terminal_sha256,
        predecessor_terminal_sha256=predecessor_terminal_sha256,
        successor_reservation_sha256=successor_reservation_sha256,
        installation_revision=installation_revision,
        descriptor_identity_sha256=descriptor_identity_sha256,
        owner_identity_sha256=owner_identity_sha256,
        descriptor_sha256=str(descriptor["descriptor_sha256"]),
        owner_manifest_sha256=owner_manifest_sha256,
        selected_root_security_sha256=selected_root_security_sha256,
        directory_set_sha256=directory_set_sha256,
        package_manifest_sha256=package_manifest_sha256,
        payload_tree_sha256=payload_tree_sha256,
        product_build_sha256=product_build_sha256,
        installer_build_sha256=installer_build_sha256,
        backend_sha256=backend_sha256,
        session_sha256=session_sha256,
        observed_at_utc=observed_at_utc,
        simultaneous_current=simultaneous_current,
    )
    with _PAIR_FIXTURE_REGISTRY_LOCK:
        _PAIR_FIXTURE_REGISTRY[id(fixture)] = fixture
    return fixture


def _fixture_only_consume_pair_readback(
    pair_readback: _InstallationPairReadbackFixture,
    *,
    root_plan: _SelectedInstallRootPlanFixture,
    expected_operation_id: str,
    expected_ticket_event_sha256: str,
    expected_install_instance_id: str,
    expected_descriptor_document: dict[str, object],
    expected_predecessor_terminal_sha256: str,
    expected_successor_reservation_sha256: str,
    expected_installation_revision: int,
    expected_package_manifest_sha256: str,
    expected_payload_tree_sha256: str,
    expected_product_build_sha256: str,
    expected_installer_build_sha256: str,
    expected_backend_sha256: str,
    expected_session_sha256: str,
    consumer_operation_key: str,
) -> _InstallationReadbackFixture:
    """Consume one registered pair fixture and issue one data-only readback."""

    _take_pair_fixture(pair_readback)
    try:
        descriptor = _validated_v2_descriptor_fixture(expected_descriptor_document)
        _require_opaque_id(expected_operation_id)
        _require_opaque_id(consumer_operation_key)
        if (
            type(root_plan) is not _SelectedInstallRootPlanFixture
            or root_plan.authority_created
            or not root_plan.fixture_only
            or pair_readback.action is not root_plan.action
            or pair_readback.pair_action != root_plan.expected_pair_action
            or pair_readback.operation_id != expected_operation_id
            or pair_readback.ticket_event_sha256 != expected_ticket_event_sha256
            or pair_readback.install_instance_id != expected_install_instance_id
            or pair_readback.owner_instance_id != expected_install_instance_id
            or dict(pair_readback.descriptor_items) != descriptor
            or descriptor["install_instance_id"] != expected_install_instance_id
            or pair_readback.owner_contract_profile != BRIDGE_CONTRACT_PROFILE
            or pair_readback.selected_root_security_sha256
            != root_plan.selected_root_security_sha256
            or pair_readback.directory_set_sha256 != root_plan.directory_set_sha256
            or pair_readback.predecessor_terminal_sha256
            != expected_predecessor_terminal_sha256
            or pair_readback.successor_reservation_sha256
            != expected_successor_reservation_sha256
            or pair_readback.installation_revision != expected_installation_revision
            or pair_readback.package_manifest_sha256
            != expected_package_manifest_sha256
            or pair_readback.payload_tree_sha256 != expected_payload_tree_sha256
            or pair_readback.product_build_sha256 != expected_product_build_sha256
            or pair_readback.installer_build_sha256
            != expected_installer_build_sha256
            or pair_readback.backend_sha256 != expected_backend_sha256
            or pair_readback.session_sha256 != expected_session_sha256
            or pair_readback.descriptor_generation_sha256
            != pair_readback.pair_generation_sha256
            or pair_readback.owner_generation_sha256
            != pair_readback.pair_generation_sha256
            or pair_readback.descriptor_identity_sha256
            == pair_readback.owner_identity_sha256
            or pair_readback.simultaneous_current is not True
        ):
            _reject_pair_readback()
    except (MontageLearningInstallationError, TypeError, ValueError):
        _reject_pair_readback()

    readback = _InstallationReadbackFixture(
        action=pair_readback.action,
        operation_id=pair_readback.operation_id,
        install_instance_id=pair_readback.install_instance_id,
        pair_terminal_sha256=pair_readback.pair_terminal_sha256,
        installation_revision=pair_readback.installation_revision,
        descriptor_sha256=pair_readback.descriptor_sha256,
        owner_manifest_sha256=pair_readback.owner_manifest_sha256,
        package_manifest_sha256=pair_readback.package_manifest_sha256,
        payload_tree_sha256=pair_readback.payload_tree_sha256,
        product_build_sha256=pair_readback.product_build_sha256,
        installer_build_sha256=pair_readback.installer_build_sha256,
        directory_set_sha256=pair_readback.directory_set_sha256,
        consumer_operation_key=consumer_operation_key,
        observed_at_utc=pair_readback.observed_at_utc,
    )
    with _INSTALLED_FIXTURE_REGISTRY_LOCK:
        _INSTALLED_FIXTURE_REGISTRY[id(readback)] = readback
    return readback


def _fixture_only_consume_installed_readback(
    installed_readback: _InstallationReadbackFixture,
    *,
    consumer_operation_key: str,
) -> dict[str, object]:
    """Consume one installed-readback fixture into its audit projection."""

    _take_installed_fixture(installed_readback)
    try:
        _require_opaque_id(consumer_operation_key)
        if installed_readback.consumer_operation_key != consumer_operation_key:
            _reject_installed_readback()
        return installed_readback.public_projection()
    except (MontageLearningInstallationError, TypeError, ValueError):
        _reject_installed_readback()


def _fixture_only_plan_lifecycle_transition(
    *,
    root_plan: _SelectedInstallRootPlanFixture,
    current: _InstallationLifecycleStateFixture | None,
    expected_install_instance_id: str,
    expected_pair_generation_sha256: str,
    expected_pair_terminal_sha256: str,
    package_manifest_sha256: str,
    payload_tree_sha256: str,
    product_build_sha256: str,
    installer_build_sha256: str,
) -> _InstallationLifecycleStateFixture:
    """Model one effect-free lifecycle transition for negative verification."""

    try:
        if (
            type(root_plan) is not _SelectedInstallRootPlanFixture
            or root_plan.authority_created
            or not root_plan.fixture_only
            or type(expected_install_instance_id) is not str
            or _INSTANCE_RE.fullmatch(expected_install_instance_id) is None
        ):
            _reject_lifecycle()
        for value in (
            expected_pair_generation_sha256,
            expected_pair_terminal_sha256,
            package_manifest_sha256,
            payload_tree_sha256,
            product_build_sha256,
            installer_build_sha256,
        ):
            _require_sha(value, "lifecycle commitment")

        action = root_plan.action
        if action is _InstallationAction.FIRST_PROVISION:
            if current is not None:
                _reject_lifecycle()
            revision = 1
        else:
            if (
                type(current) is not _InstallationLifecycleStateFixture
                or current.authority_created
                or not current.fixture_only
                or current.install_instance_id != expected_install_instance_id
            ):
                _reject_lifecycle()

            if action is _InstallationAction.PORTABLE_REBIND:
                if (
                    root_plan.selected_root_security_sha256
                    == current.selected_root_security_sha256
                    or expected_pair_generation_sha256
                    == current.pair_generation_sha256
                    or expected_pair_terminal_sha256
                    == current.pair_terminal_sha256
                    or not _same_lifecycle_package(
                        current,
                        package_manifest_sha256=package_manifest_sha256,
                        payload_tree_sha256=payload_tree_sha256,
                        product_build_sha256=product_build_sha256,
                        installer_build_sha256=installer_build_sha256,
                    )
                ):
                    _reject_lifecycle()
                revision = current.installation_revision
            else:
                if (
                    root_plan.selected_root_security_sha256
                    != current.selected_root_security_sha256
                    or expected_pair_generation_sha256
                    != current.pair_generation_sha256
                ):
                    _reject_lifecycle()
                same_package = _same_lifecycle_package(
                    current,
                    package_manifest_sha256=package_manifest_sha256,
                    payload_tree_sha256=payload_tree_sha256,
                    product_build_sha256=product_build_sha256,
                    installer_build_sha256=installer_build_sha256,
                )
                if action is _InstallationAction.VERIFY_REPAIR:
                    if (
                        not same_package
                        or expected_pair_terminal_sha256
                        != current.pair_terminal_sha256
                    ):
                        _reject_lifecycle()
                    revision = current.installation_revision
                elif action is _InstallationAction.ADOPT_EXISTING:
                    if (
                        not same_package
                        or expected_pair_terminal_sha256
                        == current.pair_terminal_sha256
                    ):
                        _reject_lifecycle()
                    revision = current.installation_revision
                elif action is _InstallationAction.PUBLISH_INSTALL_REVISION:
                    if (
                        same_package
                        or expected_pair_terminal_sha256
                        == current.pair_terminal_sha256
                    ):
                        _reject_lifecycle()
                    revision = current.installation_revision + 1
                else:
                    _reject_lifecycle()
    except (MontageLearningInstallationError, TypeError, ValueError):
        _reject_lifecycle()

    return _InstallationLifecycleStateFixture(
        action=root_plan.action,
        install_instance_id=expected_install_instance_id,
        pair_generation_sha256=expected_pair_generation_sha256,
        pair_terminal_sha256=expected_pair_terminal_sha256,
        installation_revision=revision,
        selected_root_security_sha256=root_plan.selected_root_security_sha256,
        package_manifest_sha256=package_manifest_sha256,
        payload_tree_sha256=payload_tree_sha256,
        product_build_sha256=product_build_sha256,
        installer_build_sha256=installer_build_sha256,
    )


def _fixture_only_uninstall_preservation_projection() -> dict[str, object]:
    """Return the static TASK-063 uninstall contract with no delete operation."""

    return {
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


def _same_lifecycle_package(
    current: _InstallationLifecycleStateFixture,
    *,
    package_manifest_sha256: str,
    payload_tree_sha256: str,
    product_build_sha256: str,
    installer_build_sha256: str,
) -> bool:
    return (
        current.package_manifest_sha256 == package_manifest_sha256
        and current.payload_tree_sha256 == payload_tree_sha256
        and current.product_build_sha256 == product_build_sha256
        and current.installer_build_sha256 == installer_build_sha256
    )


def _take_pair_fixture(value: object) -> None:
    if type(value) is not _InstallationPairReadbackFixture:
        _reject_pair_readback()
    with _PAIR_FIXTURE_REGISTRY_LOCK:
        registered = _PAIR_FIXTURE_REGISTRY.pop(id(value), None)
        if registered is value:
            _PAIR_FIXTURE_BURNED_IDS.add(id(value))
            return
        if id(value) in _PAIR_FIXTURE_BURNED_IDS:
            raise MontageLearningInstallationError(_PAIR_READBACK_REUSED) from None
    _reject_pair_readback()


def _take_installed_fixture(value: object) -> None:
    if type(value) is not _InstallationReadbackFixture:
        _reject_installed_readback()
    with _INSTALLED_FIXTURE_REGISTRY_LOCK:
        registered = _INSTALLED_FIXTURE_REGISTRY.pop(id(value), None)
        if registered is value:
            _INSTALLED_FIXTURE_BURNED_IDS.add(id(value))
            return
        if id(value) in _INSTALLED_FIXTURE_BURNED_IDS:
            raise MontageLearningInstallationError(
                _INSTALLED_READBACK_REUSED
            ) from None
    _reject_installed_readback()


def _validated_v2_descriptor_fixture(value: object) -> dict[str, object]:
    expected_fields = {
        "schema_version",
        "message_type",
        "product_id",
        "install_instance_id",
        "bridge_relative_path",
        "initial_installer_manifest_sha256",
        "initial_product_build_sha256",
        "created_at_utc",
        "descriptor_sha256",
    }
    if type(value) is not dict or set(value) != expected_fields:
        _reject_pair_readback()
    document = dict(value)
    if (
        document["schema_version"] != DESCRIPTOR_SCHEMA_VERSION
        or document["message_type"] != DESCRIPTOR_MESSAGE_TYPE
        or document["product_id"] != PRODUCT_ID
        or document["bridge_relative_path"] != BRIDGE_RELATIVE_PATH
        or type(document["install_instance_id"]) is not str
        or _INSTANCE_RE.fullmatch(str(document["install_instance_id"])) is None
    ):
        _reject_pair_readback()
    _require_sha(
        document["initial_installer_manifest_sha256"],
        "initial_installer_manifest_sha256",
    )
    _require_sha(
        document["initial_product_build_sha256"],
        "initial_product_build_sha256",
    )
    _require_timestamp(document["created_at_utc"], "created_at_utc")
    _require_sha(document["descriptor_sha256"], "descriptor_sha256")
    body = dict(document)
    supplied = body.pop("descriptor_sha256")
    if sha256_json(body) != supplied:
        _reject_pair_readback()
    return document


def _require_opaque_id(value: object) -> str:
    if type(value) is not str or _OPAQUE_ID_RE.fullmatch(value) is None:
        raise MontageLearningInstallationError(_PAIR_READBACK_REJECTED)
    return value


def _reject_pair_readback() -> None:
    raise MontageLearningInstallationError(_PAIR_READBACK_REJECTED) from None


def _reject_installed_readback() -> None:
    raise MontageLearningInstallationError(_INSTALLED_READBACK_REJECTED) from None


def _reject_lifecycle() -> None:
    raise MontageLearningInstallationError(_LIFECYCLE_REJECTED) from None


def provision_installed_bridge(
    install_root: str | Path,
    *,
    installer_manifest_sha256: str,
    now: str | None = None,
) -> InstalledBridgeDiscovery:
    """Fail closed until the private Product installation composition is bound."""

    raise MontageLearningInstallationError(_PRIVATE_COMPOSITION_REQUIRED)


def _legacy_test_only_provision_installed_bridge(
    install_root: str | Path,
    *,
    installer_manifest_sha256: str,
    now: str | None = None,
) -> InstalledBridgeDiscovery:
    """Exercise the historical fixture path; never a Product authority surface."""

    _require_sha(installer_manifest_sha256, "installer_manifest_sha256")
    layout = BridgeLayout.production(install_root)
    _ensure_installer_data_root(layout)
    descriptor_path = layout.root / DESCRIPTOR_FILENAME
    existing: BridgeInstanceDescriptor | None = None
    if descriptor_path.exists() or descriptor_path.is_symlink():
        existing = _read_descriptor(descriptor_path)

    owner_path = layout.owner_manifest
    if existing is not None:
        instance_id = existing.install_instance_id
        created_at = existing.created_at
    elif owner_path.exists() or owner_path.is_symlink():
        owner = load_bridge_owner(layout)
        instance_id = owner.bridge_instance_id
        created_at = _timestamp(now)
    else:
        instance_id = f"bvp-install-{uuid.uuid4().hex}"
        created_at = _timestamp(now)

    owner = provision_bridge(layout, bridge_instance_id=instance_id)
    updated_at = _timestamp(now)
    body = {
        "schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "message_type": DESCRIPTOR_MESSAGE_TYPE,
        "product_id": PRODUCT_ID,
        "install_instance_id": instance_id,
        "bridge_relative_path": BRIDGE_RELATIVE_PATH,
        "installer_manifest_sha256": installer_manifest_sha256,
        "created_at": created_at,
        "updated_at": updated_at,
    }
    document = dict(body)
    document["descriptor_sha256"] = sha256_json(body)
    AtomicJsonWriter.write(
        descriptor_path,
        document,
        validator=_validate_descriptor_document,
    )
    return discover_installed_bridge(install_root)


def discover_installed_bridge(install_root: str | Path) -> InstalledBridgeDiscovery:
    """Read back one exact installer instance without creating or repairing it."""

    root = Path(install_root)
    layout = BridgeLayout.production(root)
    descriptor = _read_descriptor(layout.root / DESCRIPTOR_FILENAME)
    owner = load_bridge_owner(layout)
    if owner.bridge_instance_id != descriptor.install_instance_id:
        raise MontageLearningInstallationError(
            "bridge descriptor and owner instance mismatch"
        )
    return InstalledBridgeDiscovery(
        install_root=root,
        layout=layout,
        descriptor=descriptor,
        owner_manifest_sha256=owner.manifest_sha256,
    )


def provision_and_write_installer_readback(
    install_root: str | Path,
    *,
    installer_manifest_sha256: str,
    now: str | None = None,
    failure_injector: ReceiptFailureInjector | None = None,
) -> tuple[InstalledBridgeDiscovery, Path]:
    """Fail closed until the private Product installation composition is bound."""

    raise MontageLearningInstallationError(_PRIVATE_COMPOSITION_REQUIRED)


def _legacy_test_only_provision_and_write_installer_readback(
    install_root: str | Path,
    *,
    installer_manifest_sha256: str,
    now: str | None = None,
    failure_injector: ReceiptFailureInjector | None = None,
) -> tuple[InstalledBridgeDiscovery, Path]:
    """Exercise the historical fixture path; never a Product authority surface."""

    root = Path(install_root)
    layout = BridgeLayout.production(root)
    descriptor_path = layout.root / DESCRIPTOR_FILENAME
    if not (descriptor_path.exists() or descriptor_path.is_symlink()):
        discovery = _legacy_test_only_provision_installed_bridge(
            root,
            installer_manifest_sha256=installer_manifest_sha256,
            now=now,
        )
        try:
            return discovery, _legacy_test_only_write_installer_readback(
                discovery,
                failure_injector=failure_injector,
            )
        except Exception:
            _rollback_fresh_installer_publication(discovery)
            raise

    previous = discover_installed_bridge(root)
    target, _ = _installer_readback_coordinates(previous)
    try:
        with exclusive_file_update_lock(target):
            previous = _capture_discovery_source_binding(previous)
            previous_descriptor_bytes = _read_stable_regular_bytes(descriptor_path)
            existing_bytes = _read_stable_regular_bytes(target)
            _validate_existing_installer_readback(
                existing_bytes,
                previous,
                allowed_descriptor_sha256={previous.descriptor.descriptor_sha256},
            )
            discovery = _legacy_test_only_provision_installed_bridge(
                root,
                installer_manifest_sha256=installer_manifest_sha256,
                now=now,
            )
            try:
                return discovery, _write_installer_readback_locked(
                    discovery,
                    allowed_existing_descriptor_sha256={
                        previous.descriptor.descriptor_sha256,
                        discovery.descriptor.descriptor_sha256,
                    },
                    failure_injector=failure_injector,
                )
            except Exception:
                _rollback_installer_update(
                    previous,
                    descriptor_bytes=previous_descriptor_bytes,
                    receipt_bytes=existing_bytes,
                )
                raise
    except ValueError as exc:
        if isinstance(exc, MontageLearningInstallationError):
            raise
        raise MontageLearningInstallationError(
            "installer readback update lock failed"
        ) from exc


def _rollback_fresh_installer_publication(
    discovery: InstalledBridgeDiscovery,
) -> None:
    target, _ = _installer_readback_coordinates(discovery)
    descriptor_path = discovery.layout.root / DESCRIPTOR_FILENAME
    try:
        if _safe_receipt_identity(target) is not None:
            target.unlink()
        current = _capture_discovery_source_binding(discovery)
        if current != discovery:
            raise MontageLearningInstallationError(
                "fresh installer discovery changed before rollback"
            )
        descriptor_path.unlink()
        _directory_fsync(target.parent)
        _directory_fsync(descriptor_path.parent)
    except Exception as rollback_exc:
        raise MontageLearningInstallationError(
            "fresh installer publication rollback requires recovery"
        ) from rollback_exc


def _rollback_installer_update(
    previous: InstalledBridgeDiscovery,
    *,
    descriptor_bytes: bytes,
    receipt_bytes: bytes,
) -> None:
    target, _ = _installer_readback_coordinates(previous)
    descriptor_path = previous.layout.root / DESCRIPTOR_FILENAME
    try:
        current_receipt = (
            None
            if _safe_receipt_identity(target) is None
            else _read_stable_regular_bytes(target)
        )
        if current_receipt != receipt_bytes:
            receipt_document = json.loads(receipt_bytes.decode("utf-8"))
            AtomicJsonWriter.write(target, receipt_document)
        descriptor_document = json.loads(descriptor_bytes.decode("utf-8"))
        _validate_descriptor_document(descriptor_document)
        AtomicJsonWriter.write(
            descriptor_path,
            descriptor_document,
            validator=_validate_descriptor_document,
        )
        _capture_discovery_source_binding(previous)
        restored_receipt = _read_stable_regular_bytes(target)
        _validate_existing_installer_readback(
            restored_receipt,
            previous,
            allowed_descriptor_sha256={previous.descriptor.descriptor_sha256},
        )
    except Exception as rollback_exc:
        raise MontageLearningInstallationError(
            "installer update rollback requires recovery"
        ) from rollback_exc


def write_installer_readback(
    discovery: InstalledBridgeDiscovery,
    *,
    failure_injector: ReceiptFailureInjector | None = None,
) -> Path:
    """Fail closed until the private Product installation composition is bound."""

    raise MontageLearningInstallationError(_PRIVATE_COMPOSITION_REQUIRED)


def _legacy_test_only_write_installer_readback(
    discovery: InstalledBridgeDiscovery,
    *,
    failure_injector: ReceiptFailureInjector | None = None,
) -> Path:
    """Exercise the historical fixture path; never a Product authority surface."""

    target, _ = _installer_readback_coordinates(discovery)
    try:
        with exclusive_file_update_lock(target):
            return _write_installer_readback_locked(
                discovery,
                allowed_existing_descriptor_sha256={
                    discovery.descriptor.descriptor_sha256
                },
                failure_injector=failure_injector,
            )
    except ValueError as exc:
        if isinstance(exc, MontageLearningInstallationError):
            raise
        raise MontageLearningInstallationError(
            "installer readback update lock failed"
        ) from exc


def _write_installer_readback_locked(
    discovery: InstalledBridgeDiscovery,
    *,
    allowed_existing_descriptor_sha256: set[str],
    failure_injector: ReceiptFailureInjector | None,
) -> Path:
    discovery = _capture_discovery_source_binding(discovery)
    target, directories = _installer_readback_coordinates(discovery)
    ancestor_identities = tuple(_safe_directory_identity(path) for path in directories)
    existing_identity = _safe_receipt_identity(target)
    existing_digest: bytes | None = None
    if existing_identity is not None:
        existing_bytes = _read_stable_regular_bytes(target)
        _validate_existing_installer_readback(
            existing_bytes,
            discovery,
            allowed_descriptor_sha256=allowed_existing_descriptor_sha256,
        )
        existing_digest = sha256(existing_bytes).digest()
    data = canonical_json_bytes(discovery.public_receipt()) + b"\n"
    if len(data) > _MAX_INSTALLER_READBACK_BYTES:
        raise MontageLearningInstallationError("installer readback is too large")

    fd, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    replaced = False
    try:
        _verify_directory_identities(directories, ancestor_identities)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _require_safe_regular_file(temporary, expected_size=len(data))
        if _read_stable_regular_bytes(temporary) != data:
            raise MontageLearningInstallationError(
                "installer readback temporary verification failed"
            )
        _call_receipt_failure(failure_injector, "after_temp_fsync", temporary)

        _call_receipt_failure(failure_injector, "before_replace", target)
        discovery = _capture_discovery_source_binding(discovery)
        _verify_directory_identities(directories, ancestor_identities)
        if _safe_receipt_identity(target) != existing_identity:
            raise MontageLearningInstallationError(
                "installer readback target identity changed"
            )
        if existing_identity is not None:
            current_bytes = _read_stable_regular_bytes(target)
            _validate_existing_installer_readback(
                current_bytes,
                discovery,
                allowed_descriptor_sha256=allowed_existing_descriptor_sha256,
            )
            if sha256(current_bytes).digest() != existing_digest:
                raise MontageLearningInstallationError(
                    "installer readback target bytes changed"
                )
        if existing_identity is None:
            try:
                os.link(temporary, target, follow_symlinks=False)
            except FileExistsError as exc:
                raise MontageLearningInstallationError(
                    "installer readback target appeared concurrently"
                ) from exc
            try:
                temporary.unlink()
            except OSError as exc:
                try:
                    target.unlink()
                except OSError as rollback_exc:
                    raise MontageLearningInstallationError(
                        "installer readback new-target cleanup requires recovery"
                    ) from rollback_exc
                raise MontageLearningInstallationError(
                    "installer readback new-target cleanup failed"
                ) from exc
        else:
            os.replace(temporary, target)
        replaced = True
        _directory_fsync(target.parent)

        _verify_directory_identities(directories, ancestor_identities)
        _call_receipt_failure(failure_injector, "before_readback", target)
        _require_safe_regular_file(target, expected_size=len(data))
        readback = _read_stable_regular_bytes(target)
        if readback != data or sha256(readback).digest() != sha256(data).digest():
            raise MontageLearningInstallationError(
                "installer readback byte verification failed"
            )
        _capture_discovery_source_binding(discovery)
        return target
    finally:
        if not replaced:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _installer_readback_coordinates(
    discovery: InstalledBridgeDiscovery,
) -> tuple[Path, tuple[Path, ...]]:
    install_root = discovery.install_root
    if not install_root.is_absolute():
        raise MontageLearningInstallationError("install root must be absolute")
    expected_layout = BridgeLayout.production(install_root)
    if expected_layout.root != discovery.layout.root:
        raise MontageLearningInstallationError("discovery layout mismatch")
    data_root = install_root / "data"
    bridge_root = data_root / "montage-learning-bridge"
    migration_root = bridge_root / "migration"
    if (
        data_root.parent != install_root
        or bridge_root.parent != data_root
        or migration_root.parent != bridge_root
        or discovery.layout.migration != migration_root
    ):
        raise MontageLearningInstallationError("installer readback path mismatch")
    target = migration_root / INSTALLER_READBACK_FILENAME
    if target.parent != discovery.layout.migration:
        raise MontageLearningInstallationError("installer readback target escaped")
    return target, _complete_directory_chain(migration_root)


def _complete_directory_chain(path: Path) -> tuple[Path, ...]:
    if not path.is_absolute():
        raise MontageLearningInstallationError(
            "installer readback ancestor chain must be absolute"
        )
    return tuple(reversed(path.parents)) + (path,)


def _capture_discovery_source_binding(
    expected: InstalledBridgeDiscovery,
) -> InstalledBridgeDiscovery:
    descriptor_path = expected.layout.root / DESCRIPTOR_FILENAME
    owner_path = expected.layout.owner_manifest
    before = (
        _safe_receipt_identity(descriptor_path),
        _safe_receipt_identity(owner_path),
    )
    if None in before:
        raise MontageLearningInstallationError(
            "installer discovery source is unavailable"
        )
    current = discover_installed_bridge(expected.install_root)
    after = (
        _safe_receipt_identity(descriptor_path),
        _safe_receipt_identity(owner_path),
    )
    if before != after or current != expected:
        raise MontageLearningInstallationError(
            "installer discovery source identity changed"
        )
    return current


def _safe_directory_identity(path: Path) -> tuple[int, int, str]:
    if path.is_symlink():
        raise MontageLearningInstallationError(
            "installer readback ancestor must not be a symlink"
        )
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback ancestor is unavailable"
        ) from exc
    if not stat.S_ISDIR(metadata.st_mode) or _stat_is_reparse(metadata):
        raise MontageLearningInstallationError(
            "installer readback ancestor must be a safe directory"
        )
    if os.name == "nt" and not hasattr(metadata, "st_file_attributes"):
        raise MontageLearningInstallationError(
            "installer readback ancestor safety is not observable"
        )
    if metadata.st_dev < 0 or metadata.st_ino <= 0:
        raise MontageLearningInstallationError(
            "installer readback ancestor identity is unavailable"
        )
    try:
        resolved = str(path.resolve(strict=True))
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback ancestor cannot be resolved"
        ) from exc
    return metadata.st_dev, metadata.st_ino, resolved


def _verify_directory_identities(
    paths: tuple[Path, ...],
    expected: tuple[tuple[int, int, str], ...],
) -> None:
    current = tuple(_safe_directory_identity(path) for path in paths)
    if current != expected:
        raise MontageLearningInstallationError(
            "installer readback ancestor identity changed"
        )


def _safe_receipt_identity(path: Path) -> tuple[int, int, int, int, int] | None:
    try:
        metadata = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback target is unavailable"
        ) from exc
    _require_safe_regular_metadata(path, metadata)
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_nlink,
    )


def _require_safe_regular_file(path: Path, *, expected_size: int) -> None:
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback file is unavailable"
        ) from exc
    _require_safe_regular_metadata(path, metadata)
    if metadata.st_size != expected_size:
        raise MontageLearningInstallationError(
            "installer readback file size mismatch"
        )


def _require_safe_regular_metadata(path: Path, metadata: os.stat_result) -> None:
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or _stat_is_reparse(metadata)
    ):
        raise MontageLearningInstallationError(
            "installer readback target must be a safe regular file"
        )
    if metadata.st_nlink != 1:
        raise MontageLearningInstallationError(
            "installer readback target must not be hard linked"
        )
    if os.name == "nt" and not hasattr(metadata, "st_file_attributes"):
        raise MontageLearningInstallationError(
            "installer readback target safety is not observable"
        )


def _read_stable_regular_bytes(path: Path) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback cannot be inspected"
        ) from exc
    _require_safe_regular_metadata(path, before)
    if not 1 <= before.st_size <= _MAX_INSTALLER_READBACK_BYTES:
        raise MontageLearningInstallationError("installer readback size is invalid")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback cannot be read"
        ) from exc
    try:
        opened = os.fstat(descriptor)
        _require_safe_regular_metadata(path, opened)
        if _regular_identity(opened) != _regular_identity(before):
            raise MontageLearningInstallationError(
                "installer readback changed before open"
            )
        chunks: list[bytes] = []
        remaining = _MAX_INSTALLER_READBACK_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback cannot be re-inspected"
        ) from exc
    _require_safe_regular_metadata(path, after)
    if (
        _regular_identity(before) != _regular_identity(after_open)
        or _regular_identity(after_open) != _regular_identity(after)
        or len(data) != after.st_size
    ):
        raise MontageLearningInstallationError("installer readback is unstable")
    return data


def _regular_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_nlink,
    )


def _validate_existing_installer_readback(
    data: bytes,
    discovery: InstalledBridgeDiscovery,
    *,
    allowed_descriptor_sha256: set[str],
) -> None:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_receipt_keys,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MontageLearningInstallationError(
            "existing installer readback JSON is invalid"
        ) from exc
    expected = discovery.public_receipt()
    if type(value) is not dict or set(value) != set(expected):
        raise MontageLearningInstallationError(
            "existing installer readback fields mismatch"
        )
    for field in (
        "schema_version",
        "message_type",
        "product_id",
        "install_instance_id",
        "bridge_relative_path",
        "owner_manifest_sha256",
        "capability",
        "status",
        "connector_enabled",
        "activation_authorized",
    ):
        if value[field] != expected[field]:
            raise MontageLearningInstallationError(
                "existing installer readback ownership mismatch"
            )
    descriptor_sha256 = _require_sha(
        value["descriptor_sha256"], "descriptor_sha256"
    )
    if descriptor_sha256 not in allowed_descriptor_sha256:
        raise MontageLearningInstallationError(
            "existing installer readback descriptor transition mismatch"
        )


def _reject_duplicate_receipt_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise MontageLearningInstallationError(
                "existing installer readback has duplicate fields"
            )
        result[key] = value
    return result


def _stat_is_reparse(metadata: os.stat_result) -> bool:
    return bool(getattr(metadata, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT)


def _directory_fsync(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _call_receipt_failure(
    failure_injector: ReceiptFailureInjector | None,
    phase: str,
    path: Path,
) -> None:
    if failure_injector is not None:
        failure_injector(phase, path)


def _read_descriptor(path: Path) -> BridgeInstanceDescriptor:
    try:
        snapshot = SecureAuthorityIO(
            path.parent,
            max_bytes=_MAX_DESCRIPTOR_BYTES,
            max_json_depth=2,
            max_json_nodes=32,
        ).read_json(path.name)
    except SecureAuthorityIOError:
        raise MontageLearningInstallationError(
            "descriptor secure read rejected"
        ) from None
    if not isinstance(snapshot.document, Mapping):
        raise MontageLearningInstallationError(
            "descriptor secure read rejected"
        ) from None
    value = dict(snapshot.document)
    _validate_descriptor_document(value)
    return BridgeInstanceDescriptor(
        install_instance_id=value["install_instance_id"],
        bridge_relative_path=value["bridge_relative_path"],
        installer_manifest_sha256=value["installer_manifest_sha256"],
        created_at=value["created_at"],
        updated_at=value["updated_at"],
        descriptor_sha256=value["descriptor_sha256"],
    )


def _ensure_installer_data_root(layout: BridgeLayout) -> None:
    install_root = layout.root.parent.parent
    data_root = layout.root.parent
    for path in (install_root,):
        if path.is_symlink() or not path.is_dir():
            raise MontageLearningInstallationError(
                "installer-selected root must be an existing non-symlink directory"
            )
        metadata = path.stat(follow_symlinks=False)
        if getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise MontageLearningInstallationError(
                "installer-selected root must not be a reparse point"
            )
    if data_root.exists() or data_root.is_symlink():
        if data_root.is_symlink() or not data_root.is_dir():
            raise MontageLearningInstallationError(
                "installer data root must be a non-symlink directory"
            )
        metadata = data_root.stat(follow_symlinks=False)
        if getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise MontageLearningInstallationError(
                "installer data root must not be a reparse point"
            )
    else:
        data_root.mkdir(mode=0o700)


def _validate_descriptor_document(value: object) -> None:
    expected = {
        "schema_version",
        "message_type",
        "product_id",
        "install_instance_id",
        "bridge_relative_path",
        "installer_manifest_sha256",
        "created_at",
        "updated_at",
        "descriptor_sha256",
    }
    if type(value) is not dict or set(value) != expected:
        raise MontageLearningInstallationError("descriptor fields mismatch")
    if value["schema_version"] != DESCRIPTOR_SCHEMA_VERSION:
        raise MontageLearningInstallationError("descriptor version mismatch")
    if value["message_type"] != DESCRIPTOR_MESSAGE_TYPE:
        raise MontageLearningInstallationError("descriptor type mismatch")
    if value["product_id"] != PRODUCT_ID:
        raise MontageLearningInstallationError("descriptor product mismatch")
    if (
        type(value["install_instance_id"]) is not str
        or _INSTANCE_RE.fullmatch(value["install_instance_id"]) is None
    ):
        raise MontageLearningInstallationError("install instance id is invalid")
    if value["bridge_relative_path"] != BRIDGE_RELATIVE_PATH:
        raise MontageLearningInstallationError("bridge relative path mismatch")
    _require_sha(value["installer_manifest_sha256"], "installer_manifest_sha256")
    _require_timestamp(value["created_at"], "created_at")
    _require_timestamp(value["updated_at"], "updated_at")
    _require_sha(value["descriptor_sha256"], "descriptor_sha256")
    body = dict(value)
    supplied = body.pop("descriptor_sha256")
    if sha256_json(body) != supplied:
        raise MontageLearningInstallationError("descriptor hash mismatch")


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        )
    _require_timestamp(value, "timestamp")
    return value


def _require_timestamp(value: object, field: str) -> None:
    if type(value) is not str or not value.endswith("Z"):
        raise MontageLearningInstallationError(f"{field} is invalid")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise MontageLearningInstallationError(f"{field} is invalid") from exc


def _require_sha(value: object, field: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise MontageLearningInstallationError(f"{field} is invalid")
    return value


__all__ = [
    "BRIDGE_RELATIVE_PATH",
    "BridgeInstanceDescriptor",
    "INSTALLER_READBACK_FILENAME",
    "InstalledBridgeDiscovery",
    "MontageLearningInstallationError",
    "discover_installed_bridge",
    "provision_and_write_installer_readback",
    "provision_installed_bridge",
    "write_installer_readback",
]
