from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import subprocess

import pytest

from ai_video_production.montage_learning_bridge_security import (
    BridgeAce,
    BridgeSecurityAttestation,
    BridgeSecurityDescriptor,
    BridgeSecurityState,
    attest_bridge_security,
)
from ai_video_production.schema_contracts import validate_instance


ROOT = Path(__file__).resolve().parents[1]
CURRENT = "S-1-5-21-100-200-300-1001"
SYSTEM = "S-1-5-18"
ADMINISTRATORS = "S-1-5-32-544"
USERS = "S-1-5-32-545"
EVERYONE = "S-1-1-0"


class SyntheticBackend:
    def __init__(
        self,
        *,
        owner: str = CURRENT,
        current: str = CURRENT,
        aces: tuple[BridgeAce, ...] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.owner = owner
        self.current = current
        self.aces = aces or (
            BridgeAce(0, 0, 0x1F01FF, CURRENT),
            BridgeAce(0, 0, 0x1F01FF, SYSTEM),
            BridgeAce(0, 0, 0x1200A9, USERS),
        )
        self.error = error

    def inspect(self, path: Path) -> BridgeSecurityDescriptor:
        if self.error:
            raise self.error
        return BridgeSecurityDescriptor(self.owner, self.current, True, self.aces)


def _attest(path: Path, backend: SyntheticBackend | None = None):
    return attest_bridge_security(
        path,
        attestation_id="bridge-security.attestation.001",
        backend=backend,
    )


def test_synthetic_secure_round_trip_closed_schema_and_effect_zero(tmp_path: Path) -> None:
    root = tmp_path / "bridge"
    root.mkdir()
    attestation = _attest(root, SyntheticBackend())
    assert attestation.state is BridgeSecurityState.SECURE
    document = attestation.to_dict()
    assert BridgeSecurityAttestation.from_dict(document).to_dict() == document
    validate_instance("montage-learning-bridge-security-attestation.schema.json", document)
    assert document["all_ancestors_revalidated"] is True
    assert document["repair_performed"] is False
    assert document["migration_started"] is False
    for field in (
        "connector_config_write_authorized", "activation_authorized",
        "timeline_mutation_authorized", "resolve_write_authorized",
        "external_effect_authorized",
    ):
        assert document[field] is False
    assert CURRENT not in str(document)
    assert str(root) not in str(document)


@pytest.mark.parametrize(
    "backend,reason",
    (
        (SyntheticBackend(owner=ADMINISTRATORS), "WRONG_OWNER"),
        (
            SyntheticBackend(
                aces=(BridgeAce(0, 0, 0x1F01FF, CURRENT), BridgeAce(0, 0, 0x1200A9, "S-1-5-20"))
            ),
            "UNKNOWN_ACE_SID",
        ),
        (
            SyntheticBackend(
                aces=(BridgeAce(5, 0, 0x1200A9, CURRENT),)
            ),
            "UNKNOWN_ACE_TYPE",
        ),
        (
            SyntheticBackend(
                aces=(BridgeAce(1, 0, 0x00000002, CURRENT),)
            ),
            "DENY_ACE_UNSUPPORTED",
        ),
        (
            SyntheticBackend(
                aces=(BridgeAce(0, 0, 0x00000002, EVERYONE),)
            ),
            "SHARED_WRITER_ACE",
        ),
        (
            SyntheticBackend(
                aces=(BridgeAce(0, 0, 0x00000004, USERS),)
            ),
            "SHARED_WRITER_ACE",
        ),
    ),
)
def test_owner_unknown_ace_deny_and_shared_writer_fail_closed(
    tmp_path: Path, backend: SyntheticBackend, reason: str,
) -> None:
    root = tmp_path / "bridge"
    root.mkdir()
    result = _attest(root, backend)
    assert result.state is BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
    assert reason in result.reason_codes
    assert result.to_dict()["repair_performed"] is False


def test_missing_privilege_is_repair_required_without_partial_repair(tmp_path: Path) -> None:
    root = tmp_path / "bridge"
    root.mkdir()
    result = _attest(root, SyntheticBackend(error=PermissionError("denied")))
    assert result.state is BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
    assert result.reason_codes == ("SECURITY_DESCRIPTOR_ACCESS_DENIED",)
    assert result.root_identity_sha256 is None
    assert result.to_dict()["repair_performed"] is False
    assert list(root.iterdir()) == []


def test_shared_writer_on_an_ancestor_is_independently_rejected(tmp_path: Path) -> None:
    root = tmp_path / "bridge"
    root.mkdir()

    class AncestorBackend:
        def inspect(self, path: Path) -> BridgeSecurityDescriptor:
            aces = (
                (BridgeAce(0, 0, 0x1F01FF, CURRENT),)
                if path == root
                else (BridgeAce(0, 0, 0x00000040, EVERYONE),)
            )
            return BridgeSecurityDescriptor(CURRENT, CURRENT, True, aces)

    result = attest_bridge_security(
        root,
        attestation_id="bridge-security.attestation.ancestor-writer",
        backend=AncestorBackend(),
    )
    assert result.state is BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
    assert "SHARED_WRITER_ANCESTOR" in result.reason_codes


def test_reparse_and_ancestor_identity_replacement_fail_closed(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "bridge-link"
    try:
        link.symlink_to(actual, target_is_directory=True)
    except OSError:
        pass
    else:
        result = _attest(link, SyntheticBackend())
        assert result.state is BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
        assert result.reason_codes == ("REPARSE_POINT_REJECTED",)

    parent = tmp_path / "parent"
    root = parent / "bridge"
    root.mkdir(parents=True)
    moved = tmp_path / "parent-before"

    def substitute(stage: str, _path: Path) -> None:
        if stage == "after_descriptor":
            os.replace(parent, moved)
            root.mkdir(parents=True)

    result = attest_bridge_security(
        root,
        attestation_id="bridge-security.attestation.replaced",
        backend=SyntheticBackend(),
        hook=substitute,
    )
    assert result.state is BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
    assert result.reason_codes == ("ANCESTOR_IDENTITY_CHANGED",)


def test_ancestor_directory_metadata_churn_is_not_path_substitution(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    root = parent / "bridge"
    root.mkdir(parents=True)

    def add_unrelated_sibling(stage: str, _path: Path) -> None:
        if stage == "after_descriptor":
            (parent / "unrelated-sibling").mkdir()

    result = attest_bridge_security(
        root,
        attestation_id="bridge-security.attestation.metadata-churn",
        backend=SyntheticBackend(),
        hook=add_unrelated_sibling,
    )
    assert result.state is BridgeSecurityState.SECURE
    assert result.reason_codes == ()


def test_corrupt_unknown_and_hash_tamper_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "bridge"
    root.mkdir()
    document = _attest(root, SyntheticBackend()).to_dict()
    unknown = deepcopy(document)
    unknown["unknown"] = False
    with pytest.raises(ValueError, match="incomplete or unknown"):
        BridgeSecurityAttestation.from_dict(unknown)
    tampered = deepcopy(document)
    tampered["ancestor_count"] += 1
    with pytest.raises(ValueError, match="hash"):
        BridgeSecurityAttestation.from_dict(tampered)
    authority = deepcopy(document)
    authority["activation_authorized"] = True
    with pytest.raises(ValueError, match="remain false"):
        BridgeSecurityAttestation.from_dict(authority)
    assert ROOT.joinpath("schemas/montage-learning-bridge-security-attestation.schema.json").read_bytes() == ROOT.joinpath(
        "src/ai_video_production/schema_resources/montage-learning-bridge-security-attestation.schema.json"
    ).read_bytes()


@pytest.mark.skipif(os.name != "nt", reason="real Windows owner/DACL parser")
def test_real_windows_temporary_directory_owner_dacl_and_ace_parsing(tmp_path: Path) -> None:
    root = tmp_path / "bridge"
    root.mkdir()
    result = attest_bridge_security(
        root,
        attestation_id="bridge-security.attestation.windows.001",
    )
    if result.reason_codes == ("WRONG_OWNER",):
        assert result.state is BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
        pytest.skip(
            "host temporary directory is not owned by the current Windows user"
        )
    assert result.state is BridgeSecurityState.SECURE
    assert result.owner_sid_sha256 == result.current_user_sid_sha256
    assert result.dacl_sha256 is not None


@pytest.mark.skipif(os.name != "nt", reason="real Windows ACL mutation fixture")
@pytest.mark.parametrize("sid", (EVERYONE, USERS))
def test_real_windows_inherited_shared_writer_ace_is_rejected(
    tmp_path: Path, sid: str,
) -> None:
    parent = tmp_path / f"parent-{sid.rsplit('-', 1)[-1]}"
    parent.mkdir()
    command = ["icacls", str(parent), "/grant", f"*{sid}:(OI)(CI)(M)", "/Q"]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        pytest.skip("icacls shared-writer fixture unavailable")
    root = parent / "bridge"
    root.mkdir()
    result = attest_bridge_security(
        root,
        attestation_id=f"bridge-security.attestation.windows.shared-{sid.rsplit('-', 1)[-1]}",
    )
    assert result.state is BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
    assert "SHARED_WRITER_ACE" in result.reason_codes
    assert result.to_dict()["repair_performed"] is False


@pytest.mark.skipif(os.name != "nt", reason="real Windows ACL mutation fixture")
def test_real_windows_unknown_ace_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "bridge"
    root.mkdir()
    completed = subprocess.run(
        ["icacls", str(root), "/grant", "*S-1-5-20:(RX)", "/Q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("icacls unknown-ACE fixture unavailable")
    result = attest_bridge_security(
        root,
        attestation_id="bridge-security.attestation.windows.unknown",
    )
    assert result.state is BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
    assert "UNKNOWN_ACE_SID" in result.reason_codes


def test_non_windows_default_is_honest_not_supported(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("non-Windows contract")
    root = tmp_path / "bridge"
    root.mkdir()
    result = _attest(root)
    assert result.state is BridgeSecurityState.NOT_SUPPORTED
    assert result.reason_codes == ("WINDOWS_SECURITY_API_UNAVAILABLE",)
