from __future__ import annotations

from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path
import subprocess

import pytest
from jsonschema import Draft202012Validator

from ai_video_production import montage_learning_canonical_admission_transaction as module
from ai_video_production.montage_learning_admission_store import MontageLearningAdmissionStore
from ai_video_production.montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE, canonical_learning_sha256,
)
from ai_video_production.montage_learning_canonical_admission_transaction import (
    ANCHOR_FILE_NAME,
    CANONICAL_RELATIVE_PATH,
    JOURNAL_RELATIVE_PATH,
    MontageLearningCanonicalAdmissionError,
    MontageLearningCanonicalAdmissionTransactionStore,
    MontageLearningVerifiedAdmissionReceipt,
    ReviewObservationAdmissionResult,
    ReviewObservationCanonicalReadback,
)
from ai_video_production.montage_learning_canonical_preflight import (
    derive_canonical_evidence_id,
    derive_human_binding_sha256,
)
from ai_video_production.montage_learning_receipt_contracts import (
    derive_montage_learning_idempotency_key_sha256,
)
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.serialization import canonical_json_bytes
from test_task058_montage_learning_bridge_contracts import (
    OWNER_SCOPE_HASH, _exact_delivery, _generic_delivery,
)


STORE_ID = "task058-a-staging"
CANONICAL_STORE_ID = "task058-a-canonical"
ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/montage-learning-canonical-admission-transaction-state.schema.json"
MIRROR = ROOT / "src/ai_video_production/schema_resources" / SCHEMA.name


def _project(root: Path) -> None:
    manifest = ProductProjectManifest.create(
        project_id="proj-test",
        project_revision=1,
        product_version="0.1.0",
        timebase=ProjectTimebase(30, 1),
        child_bindings=(),
        created_at="2026-08-27T00:00:00Z",
        updated_at="2026-08-27T00:00:00Z",
    )
    ProductProjectManifestStore.save(root, manifest)


def _stage(root: Path, delivery: dict[str, object] | None = None):
    source = _exact_delivery() if delivery is None else delivery
    source_sha = str(source["evidence_sha256"])
    source_id = str(source["record_id"])
    evidence_id = derive_canonical_evidence_id(source_sha)
    binding = derive_human_binding_sha256(
        project_id=str(source["proposal"]["project_id"]),
        source_record_id=source_id,
        owner_scope_hash=OWNER_SCOPE_HASH,
        proposal_sha256=str(source["proposal_sha256"]),
        approved_plan_sha256=str(source["approved_plan_sha256"]),
        evidence_sha256=source_sha,
    )
    key = derive_montage_learning_idempotency_key_sha256(
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id=source_id,
        source_sha256=source_sha,
        owner_scope_hash=OWNER_SCOPE_HASH,
    )
    result = MontageLearningAdmissionStore(root).append(
        store_id=STORE_ID,
        owner_scope_hash=OWNER_SCOPE_HASH,
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id=source_id,
        source_sha256=source_sha,
        idempotency_key_sha256=key,
        canonical_evidence_id=evidence_id,
        canonical_evidence_sha256=source_sha,
        human_binding_sha256=binding,
        committed_at="2026-08-27T00:00:01Z",
        expected_revision=0,
    )
    return source, result


def _writer(root: Path, anchor: Path) -> MontageLearningCanonicalAdmissionTransactionStore:
    return MontageLearningCanonicalAdmissionTransactionStore(
        root, anchor,
        canonical_store_id=CANONICAL_STORE_ID,
        bridge_instance_id="task058-test-bridge",
    )


def _arguments(staged) -> dict[str, object]:
    return {
        "staging_store_id": STORE_ID,
        "expected_owner_scope_hash": OWNER_SCOPE_HASH,
        "expected_staging_revision": staged.ledger.revision,
        "expected_staging_entry_sha256": staged.entry.to_dict()["entry_sha256"],
        "expected_canonical_store_commit_sha256": None,
        "expected_external_anchor_document_sha256": None,
    }


def _concurrent_admit(project: str, anchor: str, delivery: dict[str, object],
                      arguments: dict[str, object], start, queue) -> None:
    start.wait(10)
    try:
        result = _writer(Path(project), Path(anchor)).admit_exact(delivery, **arguments)
        queue.put(("RESULT", result.status, result.receipt.to_dict()["receipt_sha256"]))
    except Exception as exc:  # child result is classified in the parent
        queue.put(("ERROR", type(exc).__name__, str(exc)))


def _concurrent_generic(project: str, anchor: str, delivery: dict[str, object],
                        start, queue) -> None:
    start.wait(10)
    try:
        result = _writer(Path(project), Path(anchor)).record_exact_generic_observation(
            delivery, expected_revision=0,
        )
        queue.put(("GENERIC", result.status, result.canonical_commit_sha256))
    except Exception as exc:
        queue.put(("GENERIC_ERROR", type(exc).__name__, str(exc)))


def _cleanup_processes(processes, queue) -> None:
    errors: list[BaseException] = []
    for process in processes:
        try:
            process.join(10)
        except BaseException as exc:
            errors.append(exc)
        try:
            if process.is_alive():
                process.terminate()
                process.join(5)
        except BaseException as exc:
            errors.append(exc)
        try:
            if process.is_alive():
                process.kill()
                process.join(5)
        except BaseException as exc:
            errors.append(exc)
        try:
            if process.is_alive():
                errors.append(AssertionError("spawn child remained alive"))
            else:
                process.close()
        except BaseException as exc:
            errors.append(exc)
    try:
        queue.close()
    except BaseException as exc:
        errors.append(exc)
    finally:
        try:
            queue.join_thread()
        except BaseException as exc:
            errors.append(exc)
    if errors:
        raise AssertionError(f"multiprocess cleanup failed: {errors!r}")


def test_accept_then_exact_duplicate_and_trusted_reader(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir()
    anchor.mkdir()
    _project(project)
    delivery, staged = _stage(project)
    writer = _writer(project, anchor)
    accepted = writer.admit_exact(delivery, **_arguments(staged))
    assert accepted.status == "ACCEPTED"
    assert not (project / JOURNAL_RELATIVE_PATH).exists()
    manifest = ProductProjectManifestStore.load(project)
    assert any(item.relative_path == CANONICAL_RELATIVE_PATH.as_posix()
               for item in manifest.child_bindings)
    anchor_document = json.loads((anchor / ANCHOR_FILE_NAME).read_text(encoding="utf-8"))
    assert anchor_document["external_snapshot_coordinate_only"] is True
    assert anchor_document["rollback_detection_authority_created"] is False
    verified = writer.get_verified_receipt(receipt_sha256=accepted.receipt.to_dict()["receipt_sha256"])
    assert isinstance(verified, MontageLearningVerifiedAdmissionReceipt)
    projection = verified.to_public_projection()
    assert projection["canonical_currentness_verified"] is True
    assert projection["automatic_learning_promotion_authorized"] is False

    duplicate = writer.admit_exact(delivery, **{
        **_arguments(staged),
        "expected_canonical_store_commit_sha256": accepted.canonical_store_commit_sha256,
        "expected_external_anchor_document_sha256": accepted.external_anchor_document_sha256,
    })
    assert duplicate.status == "DUPLICATE"
    assert duplicate.receipt.to_dict()["duplicate_of_receipt_sha256"] == accepted.receipt.to_dict()["receipt_sha256"]
    assert ProductProjectManifestStore.load(project).project_revision == 2


def test_crash_after_project_commit_republishes_exact_prepared_receipt(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    delivery, staged = _stage(project)
    writer = _writer(project, anchor)

    def fail(phase: str, path: Path) -> None:
        del path
        if phase == "after_project_save_committed":
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError, match="crash"):
        writer.admit_exact(delivery, failure_hook=fail, **_arguments(staged))
    prepared = json.loads((project / JOURNAL_RELATIVE_PATH).read_text(encoding="utf-8"))
    result = writer.admit_exact(delivery, **_arguments(staged))
    assert result.recovered is True
    assert result.receipt.to_dict()["receipt_sha256"] == prepared["receipt_sha256"]


def test_crash_after_anchor_write_before_participant_result_recovers(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    delivery, staged = _stage(project)
    writer = _writer(project, anchor)

    def fail(phase: str, path: Path) -> None:
        del path
        if phase == "after_anchor_write_before_participant_result":
            raise RuntimeError("participant-result-crash")

    with pytest.raises(RuntimeError, match="participant-result-crash"):
        writer.admit_exact(delivery, failure_hook=fail, **_arguments(staged))
    assert (anchor / ANCHOR_FILE_NAME).is_file()
    recovered = writer.admit_exact(delivery, **_arguments(staged))
    assert recovered.status == "ACCEPTED"
    assert recovered.recovered is True
    assert writer.get_verified_receipt().to_public_projection()["canonical_currentness_verified"] is True


def test_stale_cas_collision_and_forged_public_receipt_fail_closed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    delivery, staged = _stage(project)
    writer = _writer(project, anchor)
    accepted = writer.admit_exact(delivery, **_arguments(staged))
    with pytest.raises(MontageLearningCanonicalAdmissionError, match="stale"):
        writer.admit_exact(delivery, **_arguments(staged))
    with pytest.raises(TypeError):
        MontageLearningVerifiedAdmissionReceipt(
            accepted.receipt,
            "sha256:" + "1" * 64,
            "sha256:" + "2" * 64,
        )


def test_raw_mapping_snapshot_and_scalar_subclasses_fail_before_authority(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    delivery, staged = _stage(project)
    writer = _writer(project, anchor)

    class Evil(dict):
        pass

    with pytest.raises(MontageLearningCanonicalAdmissionError, match="exact JSON"):
        writer.admit_exact(Evil(delivery), **_arguments(staged))
    args = _arguments(staged)
    args["expected_staging_revision"] = True
    with pytest.raises(MontageLearningCanonicalAdmissionError):
        writer.admit_exact(delivery, **args)


def test_manifest_or_anchor_tamper_blocks_trusted_reader(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    delivery, staged = _stage(project)
    writer = _writer(project, anchor)
    writer.admit_exact(delivery, **_arguments(staged))
    path = anchor / ANCHOR_FILE_NAME
    value = json.loads(path.read_text(encoding="utf-8"))
    value["target_project_manifest_sha256"] = "sha256:" + "9" * 64
    path.write_bytes(canonical_json_bytes(value) + b"\n")
    with pytest.raises(MontageLearningCanonicalAdmissionError):
        writer.get_verified_receipt()


def test_generic_observation_namespace_accept_duplicate_and_collision(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    writer = _writer(project, anchor)
    delivery = _generic_delivery()
    accepted = writer.record_exact_generic_observation(
        delivery, expected_revision=0, owner_scope_hash=OWNER_SCOPE_HASH
    )
    assert isinstance(accepted, ReviewObservationAdmissionResult)
    assert isinstance(accepted.canonical_readback, ReviewObservationCanonicalReadback)
    with pytest.raises(TypeError):
        ReviewObservationAdmissionResult(b"{}")
    with pytest.raises(TypeError):
        ReviewObservationCanonicalReadback(b"{}")
    assert accepted.status == "ACCEPTED"
    body = accepted.to_dict()
    assert body["message_type"] == "ReviewObservationAdmissionResult"
    assert body["operation_outcome"] == "ACCEPTED"
    assert body["store_kind"] == "REVIEW_OBSERVATION"
    assert body["learning_adopted"] is False
    assert body["profile_promoted"] is False
    assert body["timeline_mutated"] is False
    readback = body["canonical_readback"]
    assert readback["message_type"] == "ReviewObservationCanonicalReadback"
    assert readback["store_kind"] == "REVIEW_OBSERVATION"
    assert readback["product_project_manifest_id"] == "proj-test"
    assert readback["owner_scope_hash"] == OWNER_SCOPE_HASH.removeprefix("sha256:")
    assert readback["store_revision"] == 1
    assert readback["anchor_coordinate"] is None
    assert readback["learning_adopted"] is False
    assert readback["profile_promoted"] is False
    assert readback["timeline_mutated"] is False
    manifest_before_duplicate = ProductProjectManifestStore.load(project)
    ledger_path = project / "state/montage-learning-generic-review-observations.json"
    ledger_before_duplicate = ledger_path.read_bytes()
    payload_path = project / (
        "state/montage-learning/review-observations/"
        f'{readback["payload_object_sha256"]}.json'
    )
    marker_path = project / (
        "state/montage-learning/review-observation-markers/"
        f'{readback["transaction_id"]}.json'
    )
    payload_before_duplicate = payload_path.read_bytes()
    marker_before_duplicate = marker_path.read_bytes()
    duplicate = writer.record_exact_generic_observation(
        delivery, expected_revision=1, owner_scope_hash=OWNER_SCOPE_HASH
    )
    assert duplicate.status == "DUPLICATE"
    duplicate_body = duplicate.to_dict()
    assert duplicate_body["canonical_readback"] == readback
    assert duplicate_body["current_store_revision"] == 1
    assert ProductProjectManifestStore.load(project) == manifest_before_duplicate
    assert ledger_path.read_bytes() == ledger_before_duplicate
    assert payload_path.read_bytes() == payload_before_duplicate
    assert marker_path.read_bytes() == marker_before_duplicate
    ledger = json.loads(ledger_before_duplicate)
    assert len(ledger["entries"]) == 1
    assert "source_delivery" not in ledger["entries"][0]
    assert payload_path.is_file()
    verified = writer.get_verified_generic_observation(
        record_id=readback["record_id"],
        learning_sha256="sha256:" + readback["source_digest_sha256"],
        canonical_commit_sha256="sha256:" + readback["canonical_commit_sha256"],
        owner_scope_hash=OWNER_SCOPE_HASH,
    )
    assert verified.status == "ACCEPTED"
    assert verified.to_dict()["canonical_readback"] == readback

    collision = deepcopy(delivery)
    collision["payload"]["proposal"]["timeline_frame"] = 601
    collision["payload"]["delta_frames"] = 3
    collision["learning_sha256"] = canonical_learning_sha256(collision["payload"])
    with pytest.raises(MontageLearningCanonicalAdmissionError, match="collision"):
        writer.record_exact_generic_observation(
            collision, expected_revision=1, owner_scope_hash=OWNER_SCOPE_HASH
        )

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["record_id"] = "relabelled-record"
    ledger_path.write_bytes(canonical_json_bytes(ledger) + b"\n")
    with pytest.raises(MontageLearningCanonicalAdmissionError):
        writer.record_exact_generic_observation(
            delivery, expected_revision=1, owner_scope_hash=OWNER_SCOPE_HASH
        )


@pytest.mark.parametrize("phase", [
    "after_generic_journal_write",
    "after_generic_project_commit",
    "after_generic_marker_write",
    "before_generic_journal_cleanup",
])
def test_generic_prepared_journal_recovers_to_byte_identical_accept(
    tmp_path: Path, phase: str,
) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    writer = _writer(project, anchor)
    delivery = _generic_delivery()

    def fail(current: str, path: Path) -> None:
        del path
        if current == phase:
            raise RuntimeError("fault")

    with pytest.raises(RuntimeError, match="fault"):
        writer.record_exact_generic_observation(
            delivery, expected_revision=0, failure_hook=fail
        )
    journal = project / "state/montage-learning/review-observation-admission-journal.json"
    assert journal.is_file()
    prepared_readback = json.loads(journal.read_text(encoding="utf-8"))["canonical_readback"]
    recovered = writer.recover_generic_observation(delivery)
    assert recovered.to_dict()["canonical_readback"] == prepared_readback
    assert not journal.exists()
    ledger = json.loads(
        (project / "state/montage-learning-generic-review-observations.json").read_text(
            encoding="utf-8"
        )
    )
    assert ledger["store_revision"] == 1


def test_pinned_read_rejects_equal_size_target_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    writer = _writer(project, anchor)
    writer.record_exact_generic_observation(_generic_delivery(), expected_revision=0)
    target = project / "state/montage-learning-generic-review-observations.json"
    original = module._require_pinned_path_unchanged
    called = False

    def substitute(path: Path, identity: object, ancestors: object) -> None:
        nonlocal called
        if path == target and not called:
            called = True
            replacement = path.with_name("equal-size-replacement.json")
            replacement.write_bytes(path.read_bytes())
            os.replace(replacement, path)
        original(path, identity, ancestors)

    monkeypatch.setattr(module, "_require_pinned_path_unchanged", substitute)
    with pytest.raises(MontageLearningCanonicalAdmissionError):
        module._read(target, module._parse_generic_ledger_v1)
    assert called


def test_pinned_read_is_non_inheritable_and_rejects_ancestor_identity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    writer = _writer(project, anchor)
    writer.record_exact_generic_observation(_generic_delivery(), expected_revision=0)
    target = project / "state/montage-learning-generic-review-observations.json"
    inheritable_calls: list[bool] = []
    original_set = os.set_inheritable

    def set_inheritable(descriptor: int, inheritable: bool) -> None:
        inheritable_calls.append(inheritable)
        original_set(descriptor, inheritable)

    monkeypatch.setattr(module.os, "set_inheritable", set_inheritable)
    assert module._read(target, module._parse_generic_ledger_v1)["store_revision"] == 1
    assert inheritable_calls and set(inheritable_calls) == {False}

    original_snapshot = module._ancestor_snapshot
    calls = 0

    def drift(path: Path):
        nonlocal calls
        calls += 1
        snapshot = original_snapshot(path)
        if calls == 2:
            ancestor, identity = snapshot[-1]
            changed = (identity[0], identity[1] + 1, identity[2], identity[3])
            return (*snapshot[:-1], (ancestor, changed))
        return snapshot

    monkeypatch.setattr(module, "_ancestor_snapshot", drift)
    with pytest.raises(MontageLearningCanonicalAdmissionError, match="ancestor"):
        module._read(target, module._parse_generic_ledger_v1)


def test_generic_trusted_reader_rejects_payload_object_substitution(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    writer = _writer(project, anchor)
    accepted = writer.record_exact_generic_observation(
        _generic_delivery(), expected_revision=0
    )
    ledger = json.loads(
        (project / "state/montage-learning-generic-review-observations.json").read_text(
            encoding="utf-8"
        )
    )
    object_path = project / (
        "state/montage-learning/review-observations/"
        f'{ledger["entries"][0]["payload_object_sha256"]}.json'
    )
    payload = json.loads(object_path.read_text(encoding="utf-8"))
    payload["timeline_mutated"] = True
    object_path.write_bytes(canonical_json_bytes(payload) + b"\n")
    with pytest.raises(MontageLearningCanonicalAdmissionError):
        writer.get_verified_generic_observation(
            record_id=accepted.canonical_readback.record_id,
            learning_sha256="sha256:" + accepted.canonical_readback.source_digest_sha256,
            canonical_commit_sha256="sha256:" + accepted.canonical_readback.canonical_commit_sha256,
        )


@pytest.mark.parametrize("artifact", ["payload", "marker"])
def test_generic_currentness_validates_every_historical_artifact(
    tmp_path: Path, artifact: str,
) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    writer = _writer(project, anchor)
    first = writer.record_exact_generic_observation(
        _generic_delivery(), expected_revision=0
    )
    second_delivery = deepcopy(_generic_delivery())
    second_delivery["record_id"] = "generic-record-2"
    second_delivery["payload"]["record_id"] = "generic-record-2"
    second_delivery["learning_sha256"] = canonical_learning_sha256(
        second_delivery["payload"]
    )
    second = writer.record_exact_generic_observation(
        second_delivery, expected_revision=1
    )
    if artifact == "payload":
        target = (
            project
            / "state/montage-learning/review-observations"
            / f"{first.canonical_readback.payload_object_sha256}.json"
        )
    else:
        target = (
            project
            / "state/montage-learning/review-observation-markers"
            / f"{first.canonical_readback.transaction_id}.json"
        )
    target.unlink()
    with pytest.raises(MontageLearningCanonicalAdmissionError):
        writer.get_verified_generic_observation(
            record_id=second.canonical_readback.record_id,
            learning_sha256="sha256:" + second.canonical_readback.source_digest_sha256,
            canonical_commit_sha256=(
                "sha256:" + second.canonical_readback.canonical_commit_sha256
            ),
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows junction fixture")
def test_windows_junction_root_is_rejected(tmp_path: Path) -> None:
    real_project = tmp_path / "real-project"
    project_link = tmp_path / "project-junction"
    anchor = tmp_path / "anchor"
    real_project.mkdir(); anchor.mkdir(); _project(real_project)
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(project_link), str(real_project)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("junction creation unavailable")
    with pytest.raises(MontageLearningCanonicalAdmissionError, match="safe root"):
        _writer(project_link, anchor)


def test_generic_child_commit_does_not_invalidate_exact_receipt(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    delivery, staged = _stage(project)
    writer = _writer(project, anchor)
    accepted = writer.admit_exact(delivery, **_arguments(staged))
    first = writer.get_verified_receipt(receipt_sha256=accepted.receipt.to_dict()["receipt_sha256"])
    anchored_manifest = first.to_public_projection()["project_manifest_sha256"]
    writer.record_exact_generic_observation(_generic_delivery(), expected_revision=0)
    current = ProductProjectManifestStore.load(project)
    assert current.project_revision == 3
    assert current.project_manifest_sha256 != anchored_manifest
    later = writer.get_verified_receipt(receipt_sha256=accepted.receipt.to_dict()["receipt_sha256"])
    assert later.to_public_projection()["canonical_currentness_verified"] is True


def test_generic_and_exact_namespaces_cannot_cross_replay(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    writer = _writer(project, anchor)
    delivery, staged = _stage(project)
    with pytest.raises(Exception):
        writer.record_exact_generic_observation(delivery, expected_revision=0)
    generic = _generic_delivery()
    with pytest.raises(Exception):
        writer.admit_exact(generic, **_arguments(staged))


def test_schema_mirror_and_runtime_documents(tmp_path: Path) -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    delivery, staged = _stage(project)
    writer = _writer(project, anchor)
    writer.admit_exact(delivery, **_arguments(staged))
    validator.validate(json.loads((project / CANONICAL_RELATIVE_PATH).read_text(encoding="utf-8")))
    validator.validate(json.loads((anchor / ANCHOR_FILE_NAME).read_text(encoding="utf-8")))
    generic = writer.record_exact_generic_observation(_generic_delivery(), expected_revision=0)
    validator.validate(generic.to_dict())
    ledger = json.loads(
        (project / "state/montage-learning-generic-review-observations.json").read_text(
            encoding="utf-8"
        )
    )
    validator.validate(ledger)
    validator.validate(json.loads(
        (
            project
            / "state/montage-learning/review-observation-markers"
            / f"{generic.canonical_readback.transaction_id}.json"
        ).read_text(
            encoding="utf-8"
        )
    ))
    validator.validate(json.loads(
        (
            project
            / "state/montage-learning/review-observations"
            / f"{generic.canonical_readback.payload_object_sha256}.json"
        ).read_text(
            encoding="utf-8"
        )
    ))
    extra = deepcopy(ledger)
    extra["entries"][0]["unexpected"] = False
    assert not validator.is_valid(extra)
    relabelled_generic = deepcopy(generic.to_dict())
    relabelled_generic["timeline_mutated"] = True
    assert not validator.is_valid(relabelled_generic)
    canonical_extra = json.loads(
        (project / CANONICAL_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    canonical_extra["ledger"]["entries"][0]["unexpected"] = False
    assert not validator.is_valid(canonical_extra)
    canonical_relabel = json.loads(
        (project / CANONICAL_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    canonical_relabel["ledger"]["canonical_state"] = "COMMITTED"
    assert not validator.is_valid(canonical_relabel)
    anchor_relabel = json.loads(
        (anchor / ANCHOR_FILE_NAME).read_text(encoding="utf-8")
    )
    anchor_relabel["anchor"]["anchor_state"] = "ESTABLISHED"
    assert not validator.is_valid(anchor_relabel)


def test_multiprocess_same_cas_has_one_accepted_winner(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    delivery, staged = _stage(project)
    ctx = multiprocessing.get_context("spawn")
    start = ctx.Event()
    queue = ctx.Queue()
    processes = [ctx.Process(
        target=_concurrent_admit,
        args=(str(project), str(anchor), delivery, _arguments(staged), start, queue),
    ) for _ in range(2)]
    started = []
    try:
        for process in processes:
            process.start()
            started.append(process)
        start.set()
        results = [queue.get(timeout=30) for _ in started]
    finally:
        _cleanup_processes(started, queue)
    assert sum(item[:2] == ("RESULT", "ACCEPTED") for item in results) == 1
    assert sum(item[0] == "ERROR" for item in results) == 1
    assert not (project / JOURNAL_RELATIVE_PATH).exists()


def test_multiprocess_generic_same_cas_has_one_accepted_and_cleans_journal(
    tmp_path: Path,
) -> None:
    for iteration in range(5):
        project = tmp_path / f"project-{iteration}"
        anchor = tmp_path / f"anchor-{iteration}"
        project.mkdir(); anchor.mkdir(); _project(project)
        delivery = _generic_delivery()
        ctx = multiprocessing.get_context("spawn")
        start = ctx.Event()
        queue = ctx.Queue()
        processes = [
            ctx.Process(
                target=_concurrent_generic,
                args=(str(project), str(anchor), delivery, start, queue),
            )
            for _ in range(2)
        ]
        started = []
        try:
            for process in processes:
                process.start()
                started.append(process)
            start.set()
            results = [queue.get(timeout=30) for _ in started]
        finally:
            _cleanup_processes(started, queue)
        assert sum(item[:2] == ("GENERIC", "ACCEPTED") for item in results) == 1
        assert sum(item[0] == "GENERIC_ERROR" for item in results) == 1
        writer = _writer(project, anchor)
        assert not writer.generic_journal_path.exists()
        accepted = next(item for item in results if item[0] == "GENERIC")
        verified = writer.get_verified_generic_observation(
            record_id=str(delivery["record_id"]),
            learning_sha256=str(delivery["learning_sha256"]),
            canonical_commit_sha256="sha256:" + accepted[2],
        )
        assert verified.status == "ACCEPTED"


def test_multiprocess_generic_and_exact_project_writes_serialize(tmp_path: Path) -> None:
    project = tmp_path / "project"
    anchor = tmp_path / "anchor"
    project.mkdir(); anchor.mkdir(); _project(project)
    exact, staged = _stage(project)
    generic = _generic_delivery()
    ctx = multiprocessing.get_context("spawn")
    start = ctx.Event(); queue = ctx.Queue()
    processes = [
        ctx.Process(target=_concurrent_admit,
                    args=(str(project), str(anchor), exact, _arguments(staged), start, queue)),
        ctx.Process(target=_concurrent_generic,
                    args=(str(project), str(anchor), generic, start, queue)),
    ]
    started = []
    try:
        for process in processes:
            process.start()
            started.append(process)
        start.set()
        results = [queue.get(timeout=30) for _ in started]
    finally:
        _cleanup_processes(started, queue)
    assert len(results) == 2
    assert sum(item[0] in {"RESULT", "ERROR"} for item in results) == 1
    assert sum(item[0] in {"GENERIC", "GENERIC_ERROR"} for item in results) == 1
    writer = _writer(project, anchor)
    if any(item[0] == "ERROR" for item in results):
        assert (project / JOURNAL_RELATIVE_PATH).is_file()
        writer.admit_exact(exact, **_arguments(staged))
    if any(item[0] == "GENERIC_ERROR" for item in results):
        assert writer.generic_journal_path.is_file()
        writer.recover_generic_observation(generic)
    assert writer.get_verified_receipt().to_public_projection()["canonical_currentness_verified"] is True
    assert (project / "state/montage-learning-generic-review-observations.json").is_file()
    assert not (project / JOURNAL_RELATIVE_PATH).exists()
    assert not writer.generic_journal_path.exists()
