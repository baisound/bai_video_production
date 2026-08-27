from __future__ import annotations

from copy import deepcopy
import json
import multiprocessing
from pathlib import Path

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
        queue.put(("GENERIC", result.status, result.receipt_sha256))
    except Exception as exc:
        queue.put(("GENERIC_ERROR", type(exc).__name__, str(exc)))


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
    accepted = writer.record_exact_generic_observation(delivery, expected_revision=0)
    assert accepted.status == "ACCEPTED"
    assert accepted.to_skill_v1_receipt() == {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageLearningAdmissionReceipt",
        "record_id": accepted.record_id,
        "learning_sha256": accepted.learning_sha256,
        "status": "ACCEPTED",
        "receipt_id": accepted.receipt_id,
        "timestamp": accepted.timestamp,
    }
    body = accepted.to_dict()
    assert body["namespace"] == "GENERIC_REVIEW_OBSERVATION_ONLY"
    assert body["learning_adoption_authorized"] is False
    duplicate = writer.record_exact_generic_observation(delivery, expected_revision=1)
    assert duplicate.status == "DUPLICATE"
    assert duplicate.duplicate_of_receipt_sha256 == accepted.receipt_sha256

    collision = deepcopy(delivery)
    collision["payload"]["proposal"]["timeline_frame"] = 601
    collision["payload"]["delta_frames"] = 3
    collision["learning_sha256"] = canonical_learning_sha256(collision["payload"])
    with pytest.raises(MontageLearningCanonicalAdmissionError, match="collision"):
        writer.record_exact_generic_observation(collision, expected_revision=2)

    ledger_path = project / "state/montage-learning-generic-review-observations.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    relabelled = ledger["entries"][0]["receipt"]
    relabelled["status"] = "DUPLICATE"
    relabelled["duplicate_of_receipt_sha256"] = relabelled["receipt_sha256"]
    relabelled["receipt_sha256"] = module._hash(
        module._GENERIC_RECEIPT_DOMAIN,
        module._without(relabelled, "receipt_sha256"),
    )
    ledger["ledger_sha256"] = module._hash(
        module._GENERIC_LEDGER_DOMAIN,
        module._without(ledger, "ledger_sha256"),
    )
    ledger_path.write_bytes(canonical_json_bytes(ledger) + b"\n")
    with pytest.raises(MontageLearningCanonicalAdmissionError):
        writer.record_exact_generic_observation(delivery, expected_revision=2)


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
    validator.validate(json.loads((project / "state/montage-learning-generic-review-observations.json").read_text(encoding="utf-8")))


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
    try:
        for process in processes:
            process.start()
        start.set()
        results = [queue.get(timeout=30) for _ in processes]
    finally:
        for process in processes:
            process.join(10)
            if process.is_alive():
                process.terminate(); process.join(5)
            if process.is_alive():
                process.kill(); process.join(5)
        queue.close(); queue.join_thread()
    assert sum(item[:2] == ("RESULT", "ACCEPTED") for item in results) == 1
    assert all(not process.is_alive() for process in processes)


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
    try:
        for process in processes:
            process.start()
        start.set()
        results = [queue.get(timeout=30) for _ in processes]
    finally:
        for process in processes:
            process.join(10)
            if process.is_alive():
                process.terminate(); process.join(5)
            if process.is_alive():
                process.kill(); process.join(5)
        queue.close(); queue.join_thread()
    if not any(item[0] == "RESULT" for item in results):
        _writer(project, anchor).admit_exact(exact, **_arguments(staged))
    if not any(item[0] == "GENERIC" for item in results):
        _writer(project, anchor).record_exact_generic_observation(generic, expected_revision=0)
    writer = _writer(project, anchor)
    assert writer.get_verified_receipt().to_public_projection()["canonical_currentness_verified"] is True
    assert (project / "state/montage-learning-generic-review-observations.json").is_file()
    assert not (project / JOURNAL_RELATIVE_PATH).exists()
    assert all(not process.is_alive() for process in processes)
