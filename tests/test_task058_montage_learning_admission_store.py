from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

import ai_video_production.montage_learning_admission_store as store_module
from ai_video_production.errors import ProductError
from ai_video_production.montage_learning_admission_store import (
    DUPLICATE_STAGED,
    STAGED,
    ENTRY_DOMAIN,
    LEDGER_DOMAIN,
    MontageLearningAdmissionLedger,
    MontageLearningAdmissionStore,
)
from ai_video_production.montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
    GENERIC_CONTRACT_PROFILE,
)
from ai_video_production.montage_learning_receipt_contracts import (
    derive_montage_learning_idempotency_key_sha256,
)


ROOT = Path(__file__).resolve().parents[1]
SCOPE = "sha256:" + "a" * 64


def _root(tmp_path: Path, name: str = "project") -> Path:
    result = tmp_path / name
    result.mkdir()
    return result


def _values(number: int = 1, **overrides: object) -> dict[str, object]:
    source = f"sha256:{number:064x}"
    values: dict[str, object] = {
        "store_id": "montage-learning-primary",
        "owner_scope_hash": SCOPE,
        "source_contract_profile": EXACT_CONTRACT_PROFILE,
        "source_record_id": f"record-{number}",
        "source_sha256": source,
        "idempotency_key_sha256": (
            derive_montage_learning_idempotency_key_sha256(
                source_contract_profile=EXACT_CONTRACT_PROFILE,
                source_record_id=f"record-{number}",
                source_sha256=source,
                owner_scope_hash=SCOPE,
            )
        ),
        "canonical_evidence_id": f"evidence-{number}",
        "canonical_evidence_sha256": f"sha256:{number + 100:064x}",
        "human_binding_sha256": f"sha256:{number + 200:064x}",
        "committed_at": f"2026-08-26T00:00:0{number}Z",
        "expected_revision": number - 1,
    }
    values.update(overrides)
    return values


def _append(
    store: MontageLearningAdmissionStore,
    number: int = 1,
    **overrides: object,
):
    return store.append(**_values(number, **overrides))  # type: ignore[arg-type]


def _error_code(exc: pytest.ExceptionInfo[ProductError]) -> str:
    return exc.value.code


def test_schema_mirror_meta_schema_and_positive_ledger(tmp_path: Path) -> None:
    public = ROOT / "schemas/montage-learning-admission-ledger.schema.json"
    mirror = (
        ROOT / "src/ai_video_production/schema_resources"
        / "montage-learning-admission-ledger.schema.json"
    )
    assert public.read_bytes() == mirror.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    store = MontageLearningAdmissionStore(_root(tmp_path))
    empty = store.load_or_empty(
        store_id="montage-learning-primary", owner_scope_hash=SCOPE
    )
    Draft202012Validator(schema).validate(empty.to_dict())
    result = _append(store)
    Draft202012Validator(schema).validate(result.ledger.to_dict())


def test_first_append_two_entry_chain_and_restart_readback(tmp_path: Path) -> None:
    project = _root(tmp_path)
    store = MontageLearningAdmissionStore(project)
    assert store.load_or_empty(
        store_id="montage-learning-primary", owner_scope_hash=SCOPE
    ).revision == 0

    first = _append(store)
    second = _append(store, 2)
    assert first.outcome == STAGED and first.write is not None
    assert second.outcome == STAGED and second.write is not None
    assert first.durability_state == "DIRECTORY_DURABILITY_NOT_CONFIRMED"
    assert first.path_security_state == "HOSTILE_PATH_RACE_PROTECTION_NOT_CONFIRMED"
    entry_body = first.entry.to_dict()
    assert entry_body["staging_store_written"] is True
    assert entry_body["exact_evidence_coordinates_structurally_verified"] is False
    assert entry_body["canonical_store_written"] is False
    assert entry_body["canonical_admission_authority_created"] is False
    ledger_body = first.ledger.to_dict()
    assert ledger_body["canonical_store_write_authorized"] is False
    assert ledger_body["monotonic_head_anchored"] is False
    assert ledger_body["rollback_detection_authority_created"] is False
    assert ledger_body["receipt_mint_authorized"] is False
    assert ledger_body["path_security_model"] == "COOPERATIVE_LOCAL_WRITER_ONLY"
    assert ledger_body["hostile_path_race_protection_verified"] is False
    assert ledger_body["handle_bound_canonical_promotion_required"] is True

    assert second.ledger.revision == 2
    assert (
        second.entry.previous_entry_sha256
        == first.entry.to_dict()["entry_sha256"]
    )
    assert first.entry.to_dict()["entry_sha256"].startswith("sha256:")
    assert second.ledger.to_dict()["ledger_sha256"].startswith("sha256:")

    restarted = MontageLearningAdmissionStore(project).load()
    assert restarted.to_dict() == second.ledger.to_dict()
    assert MontageLearningAdmissionLedger.from_dict(
        restarted.to_dict()
    ).to_dict() == restarted.to_dict()


def test_exact_resend_is_duplicate_with_stale_cas_and_no_write(tmp_path: Path) -> None:
    store = MontageLearningAdmissionStore(_root(tmp_path))
    first = _append(store)
    before = store.path.read_bytes()

    duplicate = _append(
        store,
        committed_at="2026-08-26T00:09:00Z",
        expected_revision=0,
    )
    assert duplicate.outcome == DUPLICATE_STAGED
    assert duplicate.write is None
    assert duplicate.durability_state == "NO_WRITE"
    assert duplicate.entry.to_dict() == first.entry.to_dict()
    assert duplicate.ledger.revision == 1
    assert store.path.read_bytes() == before


def test_idempotency_record_evidence_id_and_digest_collisions_fail_closed(
    tmp_path: Path,
) -> None:
    store = MontageLearningAdmissionStore(_root(tmp_path))
    first = _append(store)

    with pytest.raises(ProductError) as mismatch:
        _append(
            store,
            human_binding_sha256="sha256:" + "f" * 64,
            expected_revision=1,
        )
    assert _error_code(mismatch) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"

    source2 = "sha256:" + "2" * 64
    key2 = derive_montage_learning_idempotency_key_sha256(
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id="record-1",
        source_sha256=source2,
        owner_scope_hash=SCOPE,
    )
    with pytest.raises(ProductError) as record_collision:
        _append(
            store,
            2,
            source_record_id="record-1",
            source_sha256=source2,
            idempotency_key_sha256=key2,
            expected_revision=1,
        )
    assert _error_code(record_collision) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"

    with pytest.raises(ProductError) as evidence_id_collision:
        _append(store, 2, canonical_evidence_id="evidence-1", expected_revision=1)
    assert _error_code(evidence_id_collision) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"

    with pytest.raises(ProductError) as digest_replay:
        _append(
            store,
            2,
            canonical_evidence_sha256=first.entry.canonical_evidence_sha256,
            expected_revision=1,
        )
    assert _error_code(digest_replay) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"

    same_source = _values(
        2,
        source_sha256=first.entry.source_sha256,
        expected_revision=1,
    )
    same_source["idempotency_key_sha256"] = derive_montage_learning_idempotency_key_sha256(
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id="record-2",
        source_sha256=first.entry.source_sha256,

        owner_scope_hash=SCOPE,
    )
    with pytest.raises(ProductError) as source_replay:
        store.append(**same_source)  # type: ignore[arg-type]
    assert _error_code(source_replay) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"


def test_generic_unknown_profile_and_bad_idempotency_never_write(tmp_path: Path) -> None:
    store = MontageLearningAdmissionStore(_root(tmp_path))
    for profile, expected in (
        (GENERIC_CONTRACT_PROFILE, "ERR_TASK058_MONTAGE_STORE_GENERIC_FORBIDDEN"),
        ("unknown-profile", "ERR_TASK058_MONTAGE_STORE_INTEGRITY"),
    ):
        with pytest.raises(ProductError) as exc:
            _append(store, source_contract_profile=profile)
        assert _error_code(exc) == expected
        assert not store.path.exists()

    with pytest.raises(ProductError) as bad_key:
        _append(store, idempotency_key_sha256="sha256:" + "f" * 64)
    assert _error_code(bad_key) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"
    assert not store.path.exists()


def test_scope_store_and_cas_mismatch_fail_closed(tmp_path: Path) -> None:
    store = MontageLearningAdmissionStore(_root(tmp_path))
    _append(store)
    before = store.path.read_bytes()

    with pytest.raises(ProductError) as cas:
        _append(store, 2, expected_revision=0)
    assert _error_code(cas) == "ERR_TASK058_MONTAGE_STORE_CONFLICT"

    for overrides in (
        {"store_id": "another-store"},
        {"owner_scope_hash": "sha256:" + "b" * 64},
    ):
        values = _values(2, expected_revision=1, **overrides)
        if "owner_scope_hash" in overrides:
            values["idempotency_key_sha256"] = (
                derive_montage_learning_idempotency_key_sha256(
                    source_contract_profile=EXACT_CONTRACT_PROFILE,
                    source_record_id=str(values["source_record_id"]),
                    source_sha256=str(values["source_sha256"]),
                    owner_scope_hash=str(values["owner_scope_hash"]),
                )
            )
        with pytest.raises(ProductError) as scope:
            store.append(**values)  # type: ignore[arg-type]
        assert _error_code(scope) == "ERR_TASK058_MONTAGE_STORE_SCOPE"
    assert store.path.read_bytes() == before


@pytest.mark.parametrize(
    ("location", "field", "value"),
    [
        ("ledger", "schema_version", "2.0.0"),
        ("ledger", "path_security_model", "HOSTILE_RACE_SAFE"),
        ("ledger", "hostile_path_race_protection_verified", True),
        ("ledger", "handle_bound_canonical_promotion_required", False),
        ("ledger", "unexpected", False),
        ("ledger", "generic_observation_admission_authorized", True),
        ("entry", "entry_sha256", "sha256:" + "f" * 64),
        ("entry", "source_contract_profile", GENERIC_CONTRACT_PROFILE),
        ("entry", "receipt_minted", True),
        ("entry", "previous_entry_sha256", "sha256:" + "f" * 64),
    ],
)
def test_corruption_unknown_fields_versions_flags_and_chain_fail_closed(
    tmp_path: Path,
    location: str,
    field: str,
    value: object,
) -> None:
    store = MontageLearningAdmissionStore(_root(tmp_path))
    _append(store)
    document = json.loads(store.path.read_text(encoding="utf-8"))
    target = document if location == "ledger" else document["entries"][0]
    target[field] = value
    store.path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        store.load()
    assert _error_code(exc) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"


@pytest.mark.parametrize("phase", ["after_fsync", "after_validation", "before_replace"])
def test_failure_injection_preserves_prior_canonical_state(
    tmp_path: Path,
    phase: str,
) -> None:
    store = MontageLearningAdmissionStore(_root(tmp_path))
    _append(store)
    before = store.path.read_bytes()

    def fail(actual: str, temp: Path) -> None:
        assert temp.parent == store.path.parent
        if actual == phase:
            raise RuntimeError(phase)

    with pytest.raises(RuntimeError, match=phase):
        store.append(**_values(2), failure_injector=fail)  # type: ignore[arg-type]
    assert store.path.read_bytes() == before
    assert MontageLearningAdmissionStore(store.project_root).load().revision == 1


def test_abandoned_temp_is_ignored_and_corrupt_canonical_never_falls_back(
    tmp_path: Path,
) -> None:
    project = _root(tmp_path)
    store = MontageLearningAdmissionStore(project)
    orphan = store.path.parent / f".{store.path.name}.orphan.tmp"
    orphan.write_text('{"revision":999}', encoding="utf-8")
    assert store.load_or_empty(
        store_id="montage-learning-primary", owner_scope_hash=SCOPE
    ).revision == 0

    good = _append(store)
    orphan.write_text(json.dumps(good.ledger.to_dict()), encoding="utf-8")
    assert MontageLearningAdmissionStore(project).load().revision == 1

    store.path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        MontageLearningAdmissionStore(project).load()
    assert _error_code(exc) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"


def test_malformed_utf8_size_guard_missing_load_and_target_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _root(tmp_path)
    store = MontageLearningAdmissionStore(project)
    with pytest.raises(ProductError) as missing:
        store.load()
    assert _error_code(missing) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"

    store.path.write_bytes(b"\xff")
    with pytest.raises(ProductError) as utf8:
        store.load()
    assert _error_code(utf8) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"

    store.path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(store_module, "_MAX_STORE_BYTES", 1)
    with pytest.raises(ProductError) as size:
        store.load()
    assert _error_code(size) == "ERR_TASK058_MONTAGE_STORE_INTEGRITY"

    store.path.unlink()
    target = project / "outside.json"
    target.write_text("{}", encoding="utf-8")
    try:
        store.path.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ProductError) as unsafe:
        MontageLearningAdmissionStore(project)
    assert _error_code(unsafe) == "ERR_TASK058_MONTAGE_STORE_PATH_UNSAFE"


def test_domains_and_public_surface_do_not_leak_p1c_or_external_capabilities() -> None:
    assert ENTRY_DOMAIN == b"TASK058_MONTAGE_LEARNING_ADMISSION_ENTRY_V1\0"
    assert LEDGER_DOMAIN == b"TASK058_MONTAGE_LEARNING_ADMISSION_LEDGER_V1\0"
    assert all(
        part not in name.lower()
        for name in store_module.__all__
        for part in ("receipt", "importer", "delete", "repair", "timeline", "resolve")
    )
    tree = ast.parse(
        (ROOT / "src/ai_video_production/montage_learning_admission_store.py")
        .read_text(encoding="utf-8")
    )
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imports.isdisjoint(
        {"socket", "sqlite3", "subprocess", "urllib", "requests"}
    )
def test_reparse_guard_runs_even_when_exists_is_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _root(tmp_path)
    store = MontageLearningAdmissionStore(project)
    target = store.path
    real_is_reparse = store_module._is_reparse
    monkeypatch.setattr(
        store_module,
        "_is_reparse",
        lambda path: path == target or real_is_reparse(path),

    )
    with pytest.raises(ProductError) as unsafe:
        store.load_or_empty(store_id="montage-learning-primary", owner_scope_hash=SCOPE)
    assert _error_code(unsafe) == "ERR_TASK058_MONTAGE_STORE_PATH_UNSAFE"

def test_size_preflight_preserves_old_bytes_before_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MontageLearningAdmissionStore(_root(tmp_path))
    _append(store)
    before = store.path.read_bytes()
    monkeypatch.setattr(store_module, "_MAX_STORE_BYTES", len(before))
    with pytest.raises(ProductError) as too_large:
        _append(store, 2)
    assert _error_code(too_large) == "ERR_TASK058_MONTAGE_STORE_SIZE"
    assert store.path.read_bytes() == before
    assert store.load().revision == 1


def test_unsafe_state_is_rejected_before_root_lock_creation(tmp_path: Path) -> None:
    project = _root(tmp_path)
    outside = _root(tmp_path, "outside")
    state = project / "state"
    try:
        state.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")
    lock_path = project / ".task058-montage-learning-admission-staging.lock"
    with pytest.raises(ProductError) as unsafe:
        MontageLearningAdmissionStore(project)
    assert _error_code(unsafe) == "ERR_TASK058_MONTAGE_STORE_PATH_UNSAFE"
    assert not lock_path.exists()


def test_root_identity_change_fails_before_lock_or_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _root(tmp_path)
    store = MontageLearningAdmissionStore(project)
    lock_path = project / ".task058-montage-learning-admission-staging.lock"
    identity = store._root_identity
    assert identity is not None
    monkeypatch.setattr(
        store,
        "_directory_identity",
        lambda: (identity[0], identity[1] + 1),
    )
    with pytest.raises(ProductError) as unsafe:
        _append(store)
    assert _error_code(unsafe) == "ERR_TASK058_MONTAGE_STORE_PATH_UNSAFE"
    assert not lock_path.exists()
    assert not store.path.exists()



def test_state_disappearance_after_construction_is_not_recreated_before_lock(
    tmp_path: Path,
) -> None:
    project = _root(tmp_path)
    store = MontageLearningAdmissionStore(project)
    store.path.parent.rmdir()
    lock_path = project / ".task058-montage-learning-admission-staging.lock"
    with pytest.raises(ProductError) as unsafe:
        _append(store)
    assert _error_code(unsafe) == "ERR_TASK058_MONTAGE_STORE_PATH_UNSAFE"
    assert not store.path.parent.exists()
    assert not lock_path.exists()


def test_valid_old_snapshot_and_deletion_never_create_rollback_authority(
    tmp_path: Path,
) -> None:
    store = MontageLearningAdmissionStore(_root(tmp_path))
    first = _append(store)
    old_snapshot = store.path.read_bytes()
    _append(store, 2)
    store.path.write_bytes(old_snapshot)
    rolled_back = store.load()
    assert rolled_back.revision == 1
    assert rolled_back.to_dict()["monotonic_head_anchored"] is False
    assert rolled_back.to_dict()["rollback_detection_authority_created"] is False
    assert first.entry.to_dict()["canonical_store_written"] is False

    store.path.unlink()
    reset = store.load_or_empty(
        store_id="montage-learning-primary",
        owner_scope_hash=SCOPE,
    )
    assert reset.revision == 0
    assert reset.to_dict()["monotonic_head_anchored"] is False
    assert reset.to_dict()["rollback_detection_authority_created"] is False
