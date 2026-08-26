from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.montage_learning_admission_store import (
    MontageLearningAdmissionStore,
)
from ai_video_production import montage_learning_durable_staging_readback as module
from ai_video_production.montage_learning_canonical_preflight import (
    derive_canonical_evidence_id,
    derive_human_binding_sha256,
)
from ai_video_production.montage_learning_durable_staging_readback import (
    READBACK_DOMAIN,
    MontageLearningDurableStagingReadback,
    MontageLearningDurableStagingReadbackError,
    verify_montage_learning_durable_staging_readback,
)
from ai_video_production.montage_learning_receipt_contracts import (
    derive_montage_learning_idempotency_key_sha256,
)
from ai_video_production.montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_task058_montage_learning_bridge_contracts import (
    OWNER_SCOPE_HASH,
    _exact_delivery,
    _generic_delivery,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "montage-learning-durable-staging-readback.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name
STORE_ID = "task058-test-staging"


def _stage(project_root: Path, delivery: dict[str, object] | None = None):
    source = _exact_delivery() if delivery is None else delivery
    source_sha = str(source["evidence_sha256"])
    source_record_id = str(source["record_id"])
    evidence_id = derive_canonical_evidence_id(source_sha)
    binding = derive_human_binding_sha256(
        project_id=str(source["proposal"]["project_id"]),
        source_record_id=source_record_id,
        owner_scope_hash=OWNER_SCOPE_HASH,
        proposal_sha256=str(source["proposal_sha256"]),
        approved_plan_sha256=str(source["approved_plan_sha256"]),
        evidence_sha256=source_sha,
    )
    key = derive_montage_learning_idempotency_key_sha256(
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id=source_record_id,
        source_sha256=source_sha,
        owner_scope_hash=OWNER_SCOPE_HASH,
    )
    store = MontageLearningAdmissionStore(project_root)
    result = store.append(
        store_id=STORE_ID,
        owner_scope_hash=OWNER_SCOPE_HASH,
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id=source_record_id,
        source_sha256=source_sha,
        idempotency_key_sha256=key,
        canonical_evidence_id=evidence_id,
        canonical_evidence_sha256=source_sha,
        human_binding_sha256=binding,
        committed_at="2026-08-26T00:00:01Z",
        expected_revision=0,
    )
    return source, result


def _verify(project_root: Path, delivery: dict[str, object], result):
    return verify_montage_learning_durable_staging_readback(
        delivery,
        project_root=project_root,
        store_id=STORE_ID,
        expected_owner_scope_hash=OWNER_SCOPE_HASH,
        expected_revision=result.ledger.revision,
        expected_staging_entry_sha256=result.entry.to_dict()["entry_sha256"],
    )


def _resign(document: dict[str, object], field: str) -> dict[str, object]:
    body = deepcopy(document)
    body.pop(field)
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def test_real_host_handle_read_recompiles_raw_delivery_and_proves_membership(
    tmp_path: Path,
) -> None:
    delivery, staged = _stage(tmp_path)
    result = _verify(tmp_path, delivery, staged)
    body = result.to_dict()

    assert result.runtime_attested is True
    assert body["admission_state"] == (
        "NONAUTHORITATIVE_DURABLE_STAGING_READBACK_PROJECTION"
    )
    assert body["raw_delivery_recompiled"] is True
    assert body["handle_bound_file_read_verified"] is True
    assert body["staging_membership_verified"] is True
    assert body["staging_store_path_identity_verified"] is True
    assert body["store_revision"] == 1
    assert body["ledger_sha256"] == staged.ledger.to_dict()["ledger_sha256"]
    assert body["staging_entry_sha256"] == staged.entry.to_dict()["entry_sha256"]
    assert body["platform_security_model"] in {
        "WINDOWS_PINNED_HANDLE_READ_V1",
        "POSIX_OPENAT_NOFOLLOW_READ_V1",
    }
    for field in (
        "staging_store_origin_verified",
        "project_root_canonical_ownership_verified",
        "source_lineage_origin_verified",
        "human_binding_origin_verified",
        "hostile_ancestor_namespace_race_protection_verified",
        "post_return_state_guaranteed",
        "monotonic_project_anchor_verified",
        "rollback_detection_authority_created",
        "canonical_store_written",
        "receipt_minted",
        "canonical_admission_authority_created",
        "automatic_learning_promotion_authorized",
        "timeline_mutation_authorized",
        "resolve_write_authorized",
        "external_effect_authorized",
    ):
        assert body[field] is False
    assert body["point_in_time_readback_only"] is True
    assert body["canonical_store_commit_sha256"] is None
    raw = canonical_json_bytes(body)
    for forbidden in (
        b'"proposal"', b'"approved_plan"', b'"human_edit_evidence"',
        b'"placements"', b"transcript", str(tmp_path).encode(),
    ):
        assert forbidden not in raw


def test_schema_mirror_meta_schema_runtime_and_domain_hash(tmp_path: Path) -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    delivery, staged = _stage(tmp_path)
    body = _verify(tmp_path, delivery, staged).to_dict()
    Draft202012Validator(schema).validate(body)
    unsigned = dict(body)
    supplied = unsigned.pop("readback_sha256")
    assert supplied == sha256_bytes(READBACK_DOMAIN + canonical_json_bytes(unsigned))


def test_deleted_human_edit_is_preserved_as_negative_feedback(tmp_path: Path) -> None:
    delivery = _exact_delivery()
    evidence = deepcopy(delivery["human_edit_evidence"])
    assert isinstance(evidence, dict)
    evidence.update({
        "disposition": "DELETED",
        "final_target_timeline_frame": None,
        "delta_from_proposal_frames": None,
        "delta_from_review_frames": None,
        "do_not_learn": False,
    })
    evidence = _resign(evidence, "evidence_sha256")
    delivery["human_edit_evidence"] = evidence
    delivery["evidence_sha256"] = evidence["evidence_sha256"]
    source, staged = _stage(tmp_path, delivery)
    body = _verify(tmp_path, source, staged).to_dict()
    assert body["negative_feedback_preserved"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("store_id", "other-store"),
        ("expected_owner_scope_hash", "sha256:" + "1" * 64),
        ("expected_revision", 2),
        ("expected_staging_entry_sha256", "sha256:" + "2" * 64),
    ],
)
def test_every_expected_staging_coordinate_mismatch_fails_closed(
    tmp_path: Path, field: str, value: object,
) -> None:
    delivery, staged = _stage(tmp_path)
    arguments = {
        "project_root": tmp_path,
        "store_id": STORE_ID,
        "expected_owner_scope_hash": OWNER_SCOPE_HASH,
        "expected_revision": 1,
        "expected_staging_entry_sha256": staged.entry.to_dict()["entry_sha256"],
    }
    arguments[field] = value
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        verify_montage_learning_durable_staging_readback(delivery, **arguments)


def test_raw_delivery_is_recompiled_and_serialized_preflight_is_not_an_input(
    tmp_path: Path,
) -> None:
    delivery, staged = _stage(tmp_path)
    changed = deepcopy(delivery)
    changed["proposal_sha256"] = "sha256:" + "3" * 64
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        _verify(tmp_path, changed, staged)
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        _verify(tmp_path, _generic_delivery(), staged)


def test_noncanonical_or_hash_invalid_ledger_bytes_fail_closed(tmp_path: Path) -> None:
    delivery, staged = _stage(tmp_path)
    ledger_path = tmp_path / "state" / "montage-learning-admission-staging-ledger.json"
    document = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        _verify(tmp_path, delivery, staged)

    ledger_path.write_bytes(canonical_json_bytes(staged.ledger.to_dict()) + b"\n")
    changed = staged.ledger.to_dict()
    changed["revision"] = 9
    ledger_path.write_bytes(canonical_json_bytes(changed) + b"\n")
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        _verify(tmp_path, delivery, staged)


def test_missing_relative_and_empty_paths_fail_closed(tmp_path: Path) -> None:
    delivery = _exact_delivery()
    kwargs = {
        "project_root": tmp_path,
        "store_id": STORE_ID,
        "expected_owner_scope_hash": OWNER_SCOPE_HASH,
        "expected_revision": 1,
        "expected_staging_entry_sha256": "sha256:" + "4" * 64,
    }
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        verify_montage_learning_durable_staging_readback(delivery, **kwargs)
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "montage-learning-admission-staging-ledger.json").write_bytes(b"")
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        verify_montage_learning_durable_staging_readback(delivery, **kwargs)


def test_relative_project_root_and_non_builtin_delivery_fail_before_read(tmp_path: Path) -> None:
    class MappingSubclass(dict):
        pass

    kwargs = {
        "project_root": Path("relative"),
        "store_id": STORE_ID,
        "expected_owner_scope_hash": OWNER_SCOPE_HASH,
        "expected_revision": 1,
        "expected_staging_entry_sha256": "sha256:" + "5" * 64,
    }
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        verify_montage_learning_durable_staging_readback(_exact_delivery(), **kwargs)
    kwargs["project_root"] = tmp_path
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        verify_montage_learning_durable_staging_readback(
            MappingSubclass(_exact_delivery()), **kwargs
        )


def test_runtime_attested_projection_has_no_public_constructor() -> None:
    with pytest.raises(TypeError):
        MontageLearningDurableStagingReadback()  # type: ignore[call-arg]
    forged = object.__new__(MontageLearningDurableStagingReadback)
    object.__setattr__(forged, "_token", object())
    assert forged.runtime_attested is False
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        forged.to_dict()


def test_windows_private_port_closes_every_handle_in_reverse_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = canonical_json_bytes({"not": "used"}) + b"\n"

    class FakePort:
        def __init__(self) -> None:
            self.next_handle = 10
            self.closed: list[int] = []

        def open(self, path: Path, *, directory: bool) -> int:
            handle = self.next_handle
            self.next_handle += 1
            return handle

        def identity(self, handle: int, expected_path: Path, *, directory: bool):
            return module._WindowsIdentity(
                str(expected_path), 7, handle.to_bytes(16, "little"), directory
            )

        def read(self, handle: int) -> bytes:
            return raw

        def close(self, handle: int) -> bool:
            self.closed.append(handle)
            return True

    port = FakePort()
    monkeypatch.setattr(module, "_WINDOWS_PORT_FACTORY", lambda: port)
    result = module._read_windows(Path("C:/project"))
    assert result.raw == raw
    assert port.closed == [12, 11, 10]


def test_windows_close_failure_overrides_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CloseFailurePort:
        def open(self, path: Path, *, directory: bool) -> int:
            return 10 if path.name == "project" else 11 if directory else 12

        def identity(self, handle: int, expected_path: Path, *, directory: bool):
            return module._WindowsIdentity(
                str(expected_path), 7, handle.to_bytes(16, "little"), directory
            )

        def read(self, handle: int) -> bytes:
            return b"{}\n"

        def close(self, handle: int) -> bool:
            return handle != 11

    monkeypatch.setattr(module, "_WINDOWS_PORT_FACTORY", CloseFailurePort)
    with pytest.raises(MontageLearningDurableStagingReadbackError, match="close"):
        module._read_windows(Path("C:/project"))


def test_oversized_pinned_bytes_fail_before_json_parse() -> None:
    with pytest.raises(MontageLearningDurableStagingReadbackError, match="byte count"):
        module._parse_exact_ledger(b"x" * (module._MAX_STORE_BYTES + 1))


def test_project_root_symlink_or_reparse_is_rejected(tmp_path: Path) -> None:
    real_root = tmp_path / "real-project"
    real_root.mkdir()
    delivery, staged = _stage(real_root)
    alias = tmp_path / "project-alias"
    try:
        alias.symlink_to(real_root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"host cannot create a directory symlink: {exc}")
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        _verify(alias, delivery, staged)


def test_custom_nested_json_type_fails_without_invoking_hooks(tmp_path: Path) -> None:
    hooks: list[str] = []

    class ChameleonDict(dict[str, object]):
        def items(self):  # type: ignore[no-untyped-def]
            hooks.append("items")
            return super().items()

    delivery = _exact_delivery()
    delivery["proposal"] = ChameleonDict(delivery["proposal"])
    with pytest.raises(MontageLearningDurableStagingReadbackError):
        verify_montage_learning_durable_staging_readback(
            delivery,
            project_root=tmp_path,
            store_id=STORE_ID,
            expected_owner_scope_hash=OWNER_SCOPE_HASH,
            expected_revision=1,
            expected_staging_entry_sha256="sha256:" + "6" * 64,
        )
    assert hooks == []


def test_windows_port_exception_still_closes_all_started_handles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ReadFailurePort:
        def __init__(self) -> None:
            self.handles: list[int] = []
            self.closed: list[int] = []

        def open(self, path: Path, *, directory: bool) -> int:
            handle = 20 + len(self.handles)
            self.handles.append(handle)
            return handle

        def identity(self, handle: int, expected_path: Path, *, directory: bool):
            return module._WindowsIdentity(
                str(expected_path), 7, handle.to_bytes(16, "little"), directory
            )

        def read(self, handle: int) -> bytes:
            raise OSError("injected read failure")

        def close(self, handle: int) -> bool:
            self.closed.append(handle)
            return True

    port = ReadFailurePort()
    monkeypatch.setattr(module, "_WINDOWS_PORT_FACTORY", lambda: port)
    with pytest.raises(MontageLearningDurableStagingReadbackError, match="pinned read"):
        module._read_windows(Path("C:/project"))
    assert port.closed == [22, 21, 20]


def test_source_has_no_success_callback_or_mutating_api() -> None:
    source = (
        ROOT / "src" / "ai_video_production" /
        "montage_learning_durable_staging_readback.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    public_functions = {
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    assert public_functions == {"verify_montage_learning_durable_staging_readback"}
    assert "callback" not in source
    assert "AtomicJsonWriter" not in source
    assert "receipt_minted\": True" not in source
