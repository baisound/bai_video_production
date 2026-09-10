"""Synthetic-only P1 contract, transaction, fault and path-boundary evidence.

BOOTSTRAP may create exactly voice-quality inside the public Project commit
guard. Failure cleanup is empty-only and identity-bound under the same lock;
pending/committed/nonempty/replaced directories must be retained. Tests never
read real-user audio or Projects and never use fixture seals as live admission.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import copy, deepcopy
from dataclasses import replace
from datetime import datetime
import ast
import hashlib
from importlib import resources
import json
import math
import os
from pathlib import Path
import pickle
import subprocess
import sys
import uuid

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.product_project import ProductProjectManifest, ProjectChildBinding, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_save import ProductProjectSaveCoordinator, ProjectSaveJournalStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.voice_quality_meter_display_policy import MeterDisplayPolicyRevision, POLICY_DIGEST_DOMAIN, compile_fixture_meter_display_currentness
from ai_video_production import voice_quality_meter_policy_store as meter


CREATED = "2026-09-01T00:00:00.000Z"
PROJECT_ID = "meter-project"
ROOT = Path(__file__).resolve().parents[1]


def uid() -> str:
    return str(uuid.uuid4())


def rehash(document, domain, field):
    document[field] = sha256_bytes(domain + canonical_json_bytes({k: v for k, v in document.items() if k != field}))
    return document


def policy(revision=1, predecessor=None, *, floor=-24.0):
    return MeterDisplayPolicyRevision("meter-policy", revision, predecessor, floor, -12.0, -3.0, 0.0).to_dict()


def manifest(revision, bindings=(), *, updated=CREATED):
    return ProductProjectManifest.create(
        project_id=PROJECT_ID, project_revision=revision, product_version="0.23.0",
        timebase=ProjectTimebase(30, 1), child_bindings=bindings,
        created_at=CREATED, updated_at=updated,
    )


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "synthetic-project"
    root.mkdir()
    ProductProjectManifestStore.save(root, manifest(1))
    return root


def store(project, **kwargs):
    return meter.MeterPolicyProjectStore(project, PROJECT_ID, **kwargs)


def context(**changes):
    values = dict(project_id=PROJECT_ID, session_id=uid(), consumer_epoch=uid(), window_sequence=1, request_id=uid())
    values.update(changes)
    return meter.MeterPolicyQueryContext(**values)


def request(project, action, payload, *, operation_id=None):
    current = ProductProjectManifestStore.load(project)
    child = next((item for item in current.child_bindings if item.relative_path == meter.CHILD_PATH), None)
    document = dict(
        record_type="Task048MeterPolicyOperationRequestV1", schema_version=1,
        canonical_owner_task="TASK-048", project_id=PROJECT_ID,
        operation_id=operation_id or uid(), action=action,
        expected_project_revision=current.project_revision,
        expected_project_manifest_sha256=current.project_manifest_sha256,
        expected_child_sha256=None if child is None else child.content_sha256,
        payload=payload,
    )
    return rehash(document, meter.REQUEST_DOMAIN, "request_sha256")


def apply(project, writer, action, payload):
    command = request(project, action, payload)
    return writer.apply(command), command


def bootstrap(project, writer=None):
    writer = writer or store(project)
    result, command = apply(project, writer, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    return writer, result, command


def selected(project, writer=None):
    writer, _, _ = bootstrap(project, writer)
    document = policy()
    apply(project, writer, "PUBLISH_POLICY", {"policy_document": document})
    apply(project, writer, "SELECT_POLICY", {"policy_revision_sha256": document["policy_revision_sha256"]})
    return writer, document


def state(project):
    return meter.parse_meter_policy_state((project / meter.CHILD_PATH).read_bytes(), enclosing_manifest=ProductProjectManifestStore.load(project))


def file_snapshot(project):
    return {path.relative_to(project).as_posix(): path.read_bytes() for path in project.rglob("*") if path.is_file() and not path.is_symlink()}


def unrelated_save(project):
    before = ProductProjectManifestStore.load(project)
    target = ProductProjectManifest.create(
        project_id=before.project_id, project_revision=before.project_revision + 1,
        product_version=before.product_version, timebase=before.timebase,
        child_bindings=before.child_bindings, created_at=before.created_at,
        updated_at=before.updated_at,
    )
    ProductProjectSaveCoordinator().save(project, target, {}, expected_previous_manifest_sha256=before.project_manifest_sha256)
    return target


def write_fixture_state(project, document, *, revision=None):
    """Test-only tamper fixture; production module has no direct file writer."""
    current = ProductProjectManifestStore.load(project)
    data = canonical_json_bytes(document)
    (project / meter.CHILD_PATH).write_bytes(data)
    bound = ProjectChildBinding("TASK-048", meter.CHILD_PATH, meter.CHILD_FORMAT, meter.CHILD_VERSION, sha256_bytes(data), True)
    target = manifest(revision or current.project_revision, [bound], updated=current.updated_at)
    ProductProjectManifestStore.path(project).write_bytes(canonical_json_bytes(target.to_dict()))
    return target


def test_bootstrap_without_parent_read_only_then_transactional_parent(project):
    writer = store(project)
    before = file_snapshot(project)
    assert not (project / "voice-quality").exists()
    assert writer.read_snapshot(context()).status is meter.MeterPolicyReadStatus.NOT_BOUND
    assert file_snapshot(project) == before
    writer, receipt, _ = bootstrap(project, writer)
    assert receipt["observation"] == "APPLIED"
    assert receipt["committed_project_revision"] == 2
    assert state(project)["state_revision"] == 1
    assert state(project)["selected_policy_sha256"] is None
    assert writer.residuals == ()
    assert writer.read_snapshot(context()).status is meter.MeterPolicyReadStatus.NOT_BOUND


def test_publish_select_revoke_and_new_revision_recovery(project):
    writer, _, _ = bootstrap(project)
    first = policy()
    apply(project, writer, "PUBLISH_POLICY", {"policy_document": first})
    assert writer.read_snapshot(context()).status is meter.MeterPolicyReadStatus.NOT_BOUND
    apply(project, writer, "SELECT_POLICY", {"policy_revision_sha256": first["policy_revision_sha256"]})
    query = context()
    original = writer.read_snapshot(query)
    assert original.status is meter.MeterPolicyReadStatus.PROJECT_HEAD_MATCHED_SNAPSHOT
    assert original.snapshot.policy.to_dict() == first
    second = policy(2, first["policy_revision_sha256"], floor=-25.0)
    apply(project, writer, "PUBLISH_POLICY", {"policy_document": second})
    assert writer.read_snapshot(query).snapshot.policy.to_dict() == first
    assert writer.revalidate(original.snapshot, query).status is meter.MeterPolicyReadStatus.STALE
    apply(project, writer, "REVOKE_POLICY", {"policy_revision_sha256": first["policy_revision_sha256"]})
    assert writer.revalidate(original.snapshot, query).status is meter.MeterPolicyReadStatus.REVOKED
    assert writer.read_snapshot(query).status is meter.MeterPolicyReadStatus.REVOKED
    apply(project, writer, "SELECT_POLICY", {"policy_revision_sha256": second["policy_revision_sha256"]})
    assert writer.read_snapshot(query).snapshot.policy.to_dict() == second
    assert state(project)["revoked_policy_sha256s"] == [first["policy_revision_sha256"]]


def test_exact_retry_reconstructs_receipt_at_same_and_later_heads_without_writes(project):
    writer, original, command = bootstrap(project)
    before = file_snapshot(project)
    replay = writer.apply(command)
    assert file_snapshot(project) == before
    assert replay["observation"] == "ALREADY_APPLIED"
    assert replay["observed_project_manifest_sha256"] == original["observed_project_manifest_sha256"]
    assert replay["receipt_sha256"] != original["receipt_sha256"]
    for field in ("operation_id", "request_sha256", "event_sha256", "committed_state_revision", "committed_project_revision"):
        assert replay[field] == original[field]
    assert writer.read_operation_receipt(command["operation_id"], command) == replay
    later = unrelated_save(project)
    before = file_snapshot(project)
    later_receipt = writer.apply(command)
    assert file_snapshot(project) == before
    assert later_receipt["observed_project_revision"] == later.project_revision
    assert later_receipt["observed_project_manifest_sha256"] == later.project_manifest_sha256
    assert later_receipt["observed_child_sha256"] == replay["observed_child_sha256"]
    assert later_receipt["committed_project_revision"] == 2
    assert later_receipt["receipt_sha256"] != replay["receipt_sha256"]
    assert later_receipt["current_selection_proven"] is False
    assert not any("receipt_sha256" in event for event in state(project)["events"])


@pytest.mark.parametrize("mutation", ["payload", "head", "id_project"])
def test_same_operation_id_changed_request_is_conflict_and_zero_writes(project, mutation):
    writer, _, command = bootstrap(project)
    changed = deepcopy(command)
    if mutation == "payload":
        changed["payload"]["policy_ref"] = "different"
    elif mutation == "head":
        changed["expected_project_manifest_sha256"] = "sha256:" + "f" * 64
    else:
        changed["expected_project_revision"] += 1
    rehash(changed, meter.REQUEST_DOMAIN, "request_sha256")
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError, match="IDEMPOTENCY_CONFLICT"):
        writer.apply(changed)
    assert file_snapshot(project) == before


def test_schema_resource_and_all_five_local_entrypoints(project):
    public = (ROOT / "schemas" / meter.SCHEMA_NAME).read_bytes()
    assert public == resources.files("ai_video_production.schema_resources").joinpath(meter.SCHEMA_NAME).read_bytes()
    Draft202012Validator.check_schema(json.loads(public))
    writer, receipt, command = bootstrap(project)
    documents = {
        "state": state(project), "request": command, "policy": policy(),
        "operation_receipt": receipt, "readback_evidence": writer.read_snapshot(context()).to_dict(),
    }
    wrappers = meter._load_entrypoints()
    assert set(wrappers) == set(documents)
    for key, wrapper in wrappers.items():
        assert set(wrapper) == {"$schema", "$defs", "$ref"}
        assert wrapper["$ref"] == f"#/$defs/{key}"
        Draft202012Validator.check_schema(wrapper)
        meter.validate_instance(documents[key], wrapper)
        invalid = deepcopy(documents[key])
        invalid["unknown"] = True
        with pytest.raises(ValueError):
            meter.validate_instance(invalid, wrapper)
        wrong = deepcopy(documents[key])
        wrong["record_type"] = "WrongRecord"
        with pytest.raises(ValueError):
            meter.validate_instance(wrong, wrapper)
        for other in documents:
            if other != key:
                with pytest.raises(ValueError):
                    meter.validate_instance(documents[other], wrapper)


def test_all_public_serializers_and_parsers_round_trip(project):
    writer, receipt, command = bootstrap(project)
    current = ProductProjectManifestStore.load(project)
    data = meter.serialize_meter_policy_state(state(project), enclosing_manifest=current)
    assert data == (project / meter.CHILD_PATH).read_bytes()
    assert meter.parse_meter_policy_state(data, enclosing_manifest=current) == state(project)
    for parser, serializer, document in (
        (meter.parse_meter_policy_operation_request, meter.serialize_meter_policy_operation_request, command),
        (meter.parse_meter_policy_operation_receipt, meter.serialize_meter_policy_operation_receipt, receipt),
        (meter.parse_meter_policy_readback_evidence, meter.serialize_meter_policy_readback_evidence, writer.read_snapshot(context()).to_dict()),
    ):
        assert parser(serializer(document)) == document
        invalid = deepcopy(document)
        invalid["unknown"] = 0
        with pytest.raises(meter.MeterPolicyStoreError):
            serializer(invalid)
        with pytest.raises(meter.MeterPolicyStoreError):
            parser(canonical_json_bytes(invalid))


@pytest.mark.parametrize("raw", [b"", b"{} {}", b"\xef\xbb\xbf{}", b"\xff", b'{"x":1,"x":2}', b'{"x":{"y":1,"y":2}}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}', b'{"x":"\\ud800"}', b"[]"])
def test_strict_parser_rejects_bad_bytes(raw):
    with pytest.raises(meter.MeterPolicyStoreError):
        meter.parse_meter_policy_operation_request(raw)


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), float("-inf"), 0.1, 6.0, sys.float_info.max, 10**5000, 0], ids=["true", "false", "nan", "infinity", "negative-infinity", "positive", "six", "max-finite", "huge-int", "integer-zero"])
def test_policy_threshold_domain_rejected_without_effect(project, value):
    writer, _, _ = bootstrap(project)
    document = policy()
    document["true_clip_dbfs"] = value
    try:
        rehash(document, POLICY_DIGEST_DOMAIN, "policy_revision_sha256")
        command = request(project, "PUBLISH_POLICY", {"policy_document": document})
    except ValueError:
        return  # Huge integer cannot even be canonically serialized.
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError):
        writer.apply(command)
    assert file_snapshot(project) == before


@pytest.mark.parametrize("field", ["schema_version", "expected_project_revision"])
@pytest.mark.parametrize("value", [True, False, 1.0])
def test_exact_integer_wire_values(project, field, value):
    command = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    command[field] = value
    rehash(command, meter.REQUEST_DOMAIN, "request_sha256")
    with pytest.raises(meter.MeterPolicyStoreError):
        meter.parse_meter_policy_operation_request(canonical_json_bytes(command))


def test_binding_future_revision_rejected_without_prior_process_memory(project):
    bootstrap(project)
    document = state(project)
    current = ProductProjectManifestStore.load(project)
    assert meter.parse_meter_policy_state(canonical_json_bytes(document), enclosing_manifest=current) == document
    too_old = manifest(1, current.child_bindings)
    with pytest.raises(meter.MeterPolicyStoreError, match="FUTURE_PROJECT_REVISION"):
        meter.parse_meter_policy_state(canonical_json_bytes(document), enclosing_manifest=too_old)
    ProductProjectManifestStore.path(project).write_bytes(canonical_json_bytes(too_old.to_dict()))
    reader = store(project)
    assert reader.read_snapshot(context()).status is meter.MeterPolicyReadStatus.INVALID
    command = document["events"][0]["request"]
    with pytest.raises(meter.MeterPolicyStoreError):
        reader.read_operation_receipt(command["operation_id"], command)


@pytest.mark.parametrize("now,expected", [
    ("2026-08-01T00:00:00.000Z", CREATED),
    (CREATED, CREATED),
    ("2026-09-01T00:00:00Z", CREATED),
    ("2026-10-01T00:00:00.000Z", "2026-10-01T00:00:00.000Z"),
])
def test_clock_metadata_chronological_max(project, monkeypatch, now, expected):
    calls = []
    monkeypatch.setattr(meter, "utc_now_iso", lambda: calls.append(1) or now)
    bootstrap(project)
    current = ProductProjectManifestStore.load(project)
    assert current.updated_at == expected
    assert current.created_at == CREATED
    assert calls == [1]


@pytest.mark.parametrize("changes", [dict(window_sequence=2), dict(session_id="00000000-0000-4000-8000-000000000001"), dict(request_id="00000000-0000-4000-8000-000000000002"), dict(consumer_epoch="00000000-0000-4000-8000-000000000003"), dict(project_id="another-project")])
def test_context_revalidation_rejects_old_or_wrong_window(project, changes):
    writer, _ = selected(project)
    query = context()
    snapshot = writer.read_snapshot(query).snapshot
    assert writer.revalidate(snapshot, query).snapshot is not snapshot
    result = writer.revalidate(snapshot, replace(query, **changes))
    assert result.status is meter.MeterPolicyReadStatus.MISMATCH
    assert result.snapshot is None


def test_snapshot_cannot_be_copied_serialized_or_rehydrated(project):
    writer, document = selected(project)
    query = context()
    result = writer.read_snapshot(query)
    snapshot = result.snapshot
    for operation in (copy, deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            operation(snapshot)
    with pytest.raises(TypeError):
        snapshot.project_revision = 99
    with pytest.raises(TypeError):
        type("Subclass", (meter.MeterPolicySnapshot,), {})
    for fake in (result.to_dict(), document, object.__new__(meter.MeterPolicySnapshot), compile_fixture_meter_display_currentness(policy_document=document, current_head_document=document)):
        assert writer.revalidate(fake, query).status is meter.MeterPolicyReadStatus.MISMATCH
    other = store(project)
    assert other.revalidate(snapshot, query).status is meter.MeterPolicyReadStatus.MISMATCH
    writer.close()
    assert writer.revalidate(snapshot, query).status is meter.MeterPolicyReadStatus.MISMATCH
    assert writer.read_snapshot(query).snapshot is None


def test_unrelated_project_revision_stales_snapshot(project):
    writer, _ = selected(project)
    query = context()
    snapshot = writer.read_snapshot(query).snapshot
    unrelated_save(project)
    assert writer.revalidate(snapshot, query).status is meter.MeterPolicyReadStatus.STALE


def test_foreign_unbound_child_not_overwritten(project):
    parent = project / "voice-quality"
    parent.mkdir()
    (parent / "meter-policy-state.json").write_bytes(b"foreign")
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError, match="FOREIGN_CHILD"):
        bootstrap(project)
    assert file_snapshot(project) == before


def test_parent_creation_is_inside_public_guard_only(project, monkeypatch):
    original_save = ProductProjectSaveCoordinator.save
    entered = []
    original_mkdir = Path.mkdir

    def checked_save(self, root, target, documents, **kwargs):
        assert not (project / "voice-quality").exists()
        guard = kwargs["commit_guard"]

        @contextmanager
        def wrapper():
            entered.append(True)
            try:
                with guard():
                    yield
            finally:
                entered.pop()

        return original_save(self, root, target, documents, **{**kwargs, "commit_guard": wrapper})

    def checked_mkdir(path, *args, **kwargs):
        if path == project / "voice-quality":
            assert entered
            # Public save may redundantly ensure an already-created parent.
            # Only the actual absent-parent creation belongs to the P1 guard.
            if not path.exists():
                assert kwargs.get("parents", False) is False
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(ProductProjectSaveCoordinator, "save", checked_save)
    monkeypatch.setattr(Path, "mkdir", checked_mkdir)
    bootstrap(project)


FAULT_STAGES = (
    "after_staging_files", "after_journal_staged", "after_journal_validated",
    "after_child_replace", "before_manifest_commit", "after_manifest_commit",
)


@pytest.mark.parametrize("stage", FAULT_STAGES)
@pytest.mark.parametrize("recovery", ["complete", "rollback"])
def test_faults_never_issue_success_and_public_recovery_is_separate(project, stage, recovery):
    def fail(actual, root):
        if actual == stage:
            raise RuntimeError("synthetic failure")

    writer = store(project, coordinator=ProductProjectSaveCoordinator(failure_injector=fail))
    command = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    original_manifest = ProductProjectManifestStore.path(project).read_bytes()
    with pytest.raises(meter.MeterPolicyStoreError, match="COMMIT_NOT_CONFIRMED"):
        writer.apply(command)
    before = file_snapshot(project)
    assert writer.read_snapshot(context()).status is meter.MeterPolicyReadStatus.RECOVERY_REQUIRED
    with pytest.raises(meter.MeterPolicyStoreError, match="RECOVERY_REQUIRED"):
        writer.read_operation_receipt(command["operation_id"], command)
    with pytest.raises(meter.MeterPolicyStoreError, match="RECOVERY_REQUIRED"):
        writer.apply(command)
    assert file_snapshot(project) == before
    assert writer.residuals == ("VOICE_QUALITY_DIRECTORY_RETAINED_UNCERTAIN",)
    coordinator = ProductProjectSaveCoordinator()
    transaction_id = coordinator.recovery_status(project)["transaction_id"]
    if recovery == "rollback" and stage == "after_manifest_commit":
        with pytest.raises(meter.ProductError, match="Committed manifest cannot be rolled back"):
            coordinator.recover_rollback(project, transaction_id=transaction_id)
        coordinator.recover_complete(project, transaction_id=transaction_id)
    elif recovery == "rollback":
        coordinator.recover_rollback(project, transaction_id=transaction_id)
        assert ProductProjectManifestStore.path(project).read_bytes() == original_manifest
        assert not (project / meter.CHILD_PATH).exists()
        assert writer.read_snapshot(context()).status is meter.MeterPolicyReadStatus.NOT_BOUND
        with pytest.raises(meter.MeterPolicyStoreError, match="NOT_APPLIED_AT_READ_POINT"):
            writer.read_operation_receipt(command["operation_id"], command)
        return
    else:
        coordinator.recover_complete(project, transaction_id=transaction_id)
    before = file_snapshot(project)
    receipt = writer.read_operation_receipt(command["operation_id"], command)
    assert receipt["observation"] == "ALREADY_APPLIED"
    assert receipt["committed_project_revision"] == 2
    assert file_snapshot(project) == before
    assert writer.apply(command) == receipt


@pytest.mark.parametrize("residue", ["empty", "nonempty", "replaced"])
def test_prejournal_failure_cleanup_only_owned_empty_parent_under_lock(project, monkeypatch, residue):
    original_save = ProductProjectSaveCoordinator.save
    inside = []

    def wrapped_save(self, root, target, documents, **kwargs):
        guard = kwargs["commit_guard"]

        @contextmanager
        def fail_after_guard():
            inside.append(True)
            try:
                with guard():
                    directory = project / "voice-quality"
                    assert directory.is_dir()
                    if residue == "nonempty":
                        (directory / "synthetic-foreign-marker").write_bytes(b"retain")
                    elif residue == "replaced":
                        directory.rename(project / "operation-owned-parent-preserved")
                        directory.mkdir()
                    raise RuntimeError("before Project journal write")
                    yield  # pragma: no cover - context-manager protocol
            finally:
                inside.pop()

        return original_save(self, root, target, documents, **{**kwargs, "commit_guard": fail_after_guard})

    original_rmdir = Path.rmdir

    def checked_rmdir(path):
        if path == project / "voice-quality":
            assert inside
        return original_rmdir(path)

    monkeypatch.setattr(ProductProjectSaveCoordinator, "save", wrapped_save)
    monkeypatch.setattr(Path, "rmdir", checked_rmdir)
    writer = store(project)
    with pytest.raises(meter.MeterPolicyStoreError, match="COMMIT_NOT_CONFIRMED"):
        bootstrap(project, writer)
    assert (project / "voice-quality").exists() is (residue != "empty")
    assert bool(writer.residuals) is (residue != "empty")
    assert not ProjectSaveJournalStore.path(project).exists()
    assert ProductProjectManifestStore.load(project).project_revision == 1


@pytest.mark.parametrize("failure", [RuntimeError, TypeError, LookupError, AssertionError, TimeoutError, meter.MeterPolicyStoreError])
def test_lost_success_reply_lookup_and_retry_have_no_second_write(project, failure):
    class LostReply(ProductProjectSaveCoordinator):
        def save(self, *args, **kwargs):
            super().save(*args, **kwargs)
            # A coordinator-originated CAS label after commit is ambiguous too;
            # only the store's own pre-yield guard conflict is exempt.
            raise failure("CAS_CONFLICT" if failure is meter.MeterPolicyStoreError else "synthetic lost reply")

    writer = store(project, coordinator=LostReply())
    command = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    with pytest.raises(meter.MeterPolicyStoreError, match="COMMIT_NOT_CONFIRMED") as raised:
        writer.apply(command)
    assert raised.value.reason == "COMMIT_NOT_CONFIRMED"
    assert raised.value.operation_id == command["operation_id"]
    assert state(project)["events"][0]["request"] == command
    before = file_snapshot(project)
    observed = store(project).read_operation_receipt(command["operation_id"], command)
    assert writer.apply(command) == observed
    assert observed["observation"] == "ALREADY_APPLIED"
    assert file_snapshot(project) == before


def test_two_stores_same_predecessor_only_one_commit_no_retry(project):
    writer_one = store(project)
    command_one = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    command_two = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})

    class CompetingCommit(ProductProjectSaveCoordinator):
        def save(self, *args, **kwargs):
            writer_one.apply(command_one)
            return super().save(*args, **kwargs)

    loser = store(project, coordinator=CompetingCommit())
    with pytest.raises(meter.MeterPolicyStoreError, match="CAS_CONFLICT"):
        loser.apply(command_two)
    committed = state(project)
    assert len(committed["events"]) == 1
    assert committed["events"][0]["request"] == command_one
    assert ProductProjectManifestStore.load(project).project_revision == 2
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError, match="CAS_CONFLICT"):
        store(project).apply(command_two)
    assert file_snapshot(project) == before


@pytest.mark.parametrize("field", ["expected_project_revision", "expected_project_manifest_sha256", "expected_child_sha256"])
def test_cas_expectation_conflict_zero_effect(project, field):
    if field == "expected_child_sha256":
        bootstrap(project)
        command = request(project, "PUBLISH_POLICY", {"policy_document": policy()})
    else:
        command = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    command[field] = 2 if field == "expected_project_revision" else "sha256:" + "a" * 64
    rehash(command, meter.REQUEST_DOMAIN, "request_sha256")
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError, match="CAS_CONFLICT"):
        store(project).apply(command)
    assert file_snapshot(project) == before


@pytest.mark.parametrize("now", [None, "invalid", "2026-10-01T00:00:00+09:00", "2026-10-01T00:00:00+09:00Z"])
def test_invalid_clock_metadata_has_no_save(project, monkeypatch, now):
    monkeypatch.setattr(meter, "utc_now_iso", lambda: now)
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError):
        bootstrap(project)
    assert file_snapshot(project) == before


@pytest.mark.parametrize("seam", ["collection", "manifest", "journal"])
def test_interleaved_read_change_has_no_snapshot_or_retry(project, monkeypatch, seam):
    writer, _ = selected(project)
    if seam == "collection":
        original = writer._read_once
        calls = []

        def read_once():
            result = original()
            calls.append(1)
            if len(calls) == 1:
                unrelated_save(project)
            return result

        monkeypatch.setattr(writer, "_read_once", read_once)
    elif seam == "manifest":
        original = ProductProjectManifestStore.load
        calls = []

        def load(root):
            result = original(root)
            calls.append(1)
            if len(calls) == 1:
                return ProductProjectManifest.create(
                    project_id=result.project_id, project_revision=result.project_revision + 1,
                    product_version=result.product_version, timebase=result.timebase,
                    child_bindings=result.child_bindings, created_at=result.created_at, updated_at=result.updated_at,
                )
            return result

        monkeypatch.setattr(ProductProjectManifestStore, "load", load)
    else:
        original = writer._journal
        calls = []

        def journal():
            result = original()
            calls.append(1)
            return result if len(calls) == 1 else ("sha256:" + "f" * 64, result[1])

        monkeypatch.setattr(writer, "_journal", journal)
    result = writer.read_snapshot(context())
    assert result.status is meter.MeterPolicyReadStatus.STALE
    assert result.snapshot is None
    assert len(calls) <= 2


@pytest.mark.parametrize("corruption", ["child", "partial", "journal", "manifest", "missing"])
def test_corrupt_or_missing_read_source_never_matches(project, corruption):
    writer, _ = selected(project)
    paths = {
        "child": project / meter.CHILD_PATH, "partial": project / meter.CHILD_PATH,
        "journal": ProjectSaveJournalStore.path(project),
        "manifest": ProductProjectManifestStore.path(project), "missing": project / meter.CHILD_PATH,
    }
    target = paths[corruption]
    if corruption == "missing":
        target.rename(target.with_name("preserved-before-missing.json"))
    else:
        target.write_bytes(b"{" if corruption == "partial" else b"synthetic corrupt")
    before = file_snapshot(project)
    result = writer.read_snapshot(context())
    assert result.snapshot is None
    assert result.status in {meter.MeterPolicyReadStatus.INVALID, meter.MeterPolicyReadStatus.READBACK_FAILED}
    assert file_snapshot(project) == before


@pytest.mark.parametrize("kind", ["older", "same_revision_changed_hash"])
def test_store_high_water_rejects_observed_rollback_or_conflict(project, kind):
    writer, _ = selected(project)
    old = ProductProjectManifestStore.load(project)
    assert writer.read_snapshot(context()).snapshot is not None
    if kind == "older":
        unrelated_save(project)
        assert writer.read_snapshot(context()).snapshot is not None
        target = old
    else:
        target = ProductProjectManifest.create(
            project_id=old.project_id, project_revision=old.project_revision,
            product_version="0.23.1", timebase=old.timebase,
            child_bindings=old.child_bindings, created_at=old.created_at, updated_at=old.updated_at,
        )
    ProductProjectManifestStore.path(project).write_bytes(canonical_json_bytes(target.to_dict()))
    # Remove the old terminal journal only by moving this test-owned artifact.
    journal = ProjectSaveJournalStore.path(project)
    journal.rename(journal.with_name("preserved-terminal-journal.json"))
    assert writer.read_snapshot(context()).status is meter.MeterPolicyReadStatus.ROLLBACK_UNCERTAIN
    # A new process/store cannot claim knowledge of an otherwise valid disk rollback.
    assert store(project).read_snapshot(context()).snapshot is not None


@pytest.mark.parametrize("field,value", [
    ("selected_policy_sha256", "sha256:" + "f" * 64),
    ("published_policy_revision", 1), ("state_revision", 2),
    ("revoked_policy_sha256s", ["sha256:" + "e" * 64]),
])
def test_materialized_state_tamper_rejected_even_with_valid_outer_hash(project, field, value):
    bootstrap(project)
    document = state(project)
    document[field] = value
    rehash(document, meter.STATE_DOMAIN, "state_sha256")
    current = write_fixture_state(project, document)
    with pytest.raises(meter.MeterPolicyStoreError):
        meter.parse_meter_policy_state(canonical_json_bytes(document), enclosing_manifest=current)
    assert store(project).read_snapshot(context()).snapshot is None


@pytest.mark.parametrize("mutation", ["sequence", "predecessor", "request", "nested_policy", "omit", "duplicate", "reorder", "project", "revision", "child"])
def test_event_history_tamper_rejected_even_when_hashes_recomputed(project, mutation):
    selected(project)
    document = state(project)
    events = document["events"]
    if mutation == "sequence":
        events[-1]["sequence"] = 1
    elif mutation == "predecessor":
        events[-1]["previous_event_sha256"] = None
    elif mutation == "request":
        events[-1]["request"]["payload"]["policy_revision_sha256"] = "sha256:" + "c" * 64
    elif mutation == "nested_policy":
        events[1]["request"]["payload"]["policy_document"]["target_floor_dbfs"] = -25.0
    elif mutation == "omit":
        del events[1]
    elif mutation == "duplicate":
        events[-1]["request"]["operation_id"] = events[0]["request"]["operation_id"]
    elif mutation == "reorder":
        events[1], events[2] = events[2], events[1]
    elif mutation == "project":
        events[-1]["request"]["project_id"] = "different-project"
    elif mutation == "revision":
        events[-1]["request"]["expected_project_revision"] = 1
    else:
        events[-1]["request"]["expected_child_sha256"] = "sha256:" + "d" * 64
    for event in events:
        rehash(event["request"], meter.REQUEST_DOMAIN, "request_sha256")
        rehash(event, meter.EVENT_DOMAIN, "event_sha256")
    rehash(document, meter.STATE_DOMAIN, "state_sha256")
    current = write_fixture_state(project, document)
    with pytest.raises(meter.MeterPolicyStoreError):
        meter.parse_meter_policy_state(canonical_json_bytes(document), enclosing_manifest=current)


def test_policy_successor_history_selection_and_permanent_revocation(project):
    writer, first = selected(project)
    second = policy(2, first["policy_revision_sha256"], floor=-25.0)
    apply(project, writer, "PUBLISH_POLICY", {"policy_document": second})
    before = file_snapshot(project)
    for action, payload in (
        ("SELECT_POLICY", {"policy_revision_sha256": first["policy_revision_sha256"]}),
        ("BOOTSTRAP", {"policy_ref": "meter-policy"}),
        ("PUBLISH_POLICY", {"policy_document": first}),
    ):
        with pytest.raises(meter.MeterPolicyStoreError):
            apply(project, writer, action, payload)
        assert file_snapshot(project) == before
    apply(project, writer, "REVOKE_POLICY", {"policy_revision_sha256": second["policy_revision_sha256"]})
    assert writer.read_snapshot(context()).snapshot.policy.to_dict() == first
    before = file_snapshot(project)
    for action in ("SELECT_POLICY", "REVOKE_POLICY"):
        with pytest.raises(meter.MeterPolicyStoreError):
            apply(project, writer, action, {"policy_revision_sha256": second["policy_revision_sha256"]})
        assert file_snapshot(project) == before
    third = policy(3, second["policy_revision_sha256"])
    apply(project, writer, "PUBLISH_POLICY", {"policy_document": third})
    apply(project, writer, "SELECT_POLICY", {"policy_revision_sha256": third["policy_revision_sha256"]})
    assert writer.read_snapshot(context()).snapshot.policy.to_dict() == third
    assert state(project)["revoked_policy_sha256s"] == [second["policy_revision_sha256"]]


def test_new_id_already_selected_no_change_and_wrong_receipt_id(project):
    writer, document = selected(project)
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError, match="NO_CHANGE"):
        apply(project, writer, "SELECT_POLICY", {"policy_revision_sha256": document["policy_revision_sha256"]})
    command = state(project)["events"][0]["request"]
    with pytest.raises(meter.MeterPolicyStoreError, match="IDEMPOTENCY_CONFLICT"):
        writer.read_operation_receipt(uid(), command)
    assert file_snapshot(project) == before


@pytest.mark.parametrize("domain,expected", [
    (meter.REQUEST_DOMAIN, "d9eaaf7324dc9c2182dfe4a3c3648b23bf82a8bb993e72aae1503a78906c4fe3"),
    (meter.EVENT_DOMAIN, "4010722b7e9ceb123c310ed842ab84b5ef977e29963482ed5b900f449fbcb97c"),
    (meter.STATE_DOMAIN, "021c717f00c5959a115cd63e729d86b68b34580de6a37f5e8dbc326dc20f5c63"),
    (meter.RECEIPT_DOMAIN, "978df0304a44f5c6e9152b2accb1e4156e26bee4a30f2f662e4f138e446c7c8f"),
    (meter.READBACK_DOMAIN, "c8a815f9a6018102e76a5c7d678716caa1accf5ab4c30cc1d12813f027656b2a"),
])
def test_hash_domains_golden_preimages_and_nul_separator(domain, expected):
    assert domain[-1:] == b"\0"
    assert canonical_json_bytes({"x": 1}) == b'{"x":1}'
    assert meter._record_hash(domain, {"x": 1, "hash": "ignored"}, "hash") == "sha256:" + expected
    assert hashlib.sha256(domain + b'{"x":1}').hexdigest() == expected
    assert hashlib.sha256(domain[:-1] + b'{"x":1}').hexdigest() != expected
    assert expected != "5041bf1f713df204784353e82f6a4a535931cb64f1f4b4a5aeaffcb720918b22"


def test_state_prefix_hash_is_exact_bytes_not_state_digest(project):
    writer, _, _ = bootstrap(project)
    first_bytes = (project / meter.CHILD_PATH).read_bytes()
    assert sha256_bytes(first_bytes) != state(project)["state_sha256"]
    apply(project, writer, "PUBLISH_POLICY", {"policy_document": policy()})
    assert state(project)["events"][-1]["request"]["expected_child_sha256"] == sha256_bytes(first_bytes)


@pytest.mark.parametrize("kind", ["remote", "nested_id"])
def test_schema_reference_routes_reject_nonlocal_or_nested_id(kind):
    document = {"$defs": {"state": {"$ref": "https://invalid.example/not-called"}}} if kind == "remote" else {"$defs": {"state": {"$id": "nested"}}}
    with pytest.raises(meter.MeterPolicyStoreError, match="SCHEMA_REFERENCE"):
        meter._require_local_refs(document)


@pytest.mark.parametrize("mutation", ["missing", "extra", "action", "payload", "timestamp", "hash_domain", "newline_digest"])
def test_closed_request_unions_before_any_file_effect(project, mutation):
    command = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    if mutation == "missing":
        del command["payload"]
    elif mutation == "extra":
        command["extra"] = False
    elif mutation == "action":
        command["action"] = "UNREVOKE_POLICY"
    elif mutation == "payload":
        command["payload"] = {"policy_revision_sha256": "sha256:" + "a" * 64}
    elif mutation == "timestamp":
        command["created_at"] = CREATED
    elif mutation == "newline_digest":
        command["expected_project_manifest_sha256"] += "\n"
    rehash(command, meter.EVENT_DOMAIN if mutation == "hash_domain" else meter.REQUEST_DOMAIN, "request_sha256")
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError):
        store(project).apply(command)
    assert file_snapshot(project) == before


def test_json_resource_limits_exact_and_one_over():
    assert meter._strict_document(b"{}" + b" " * (meter.MAX_CHILD_BYTES - 2)) == {}
    with pytest.raises(meter.MeterPolicyStoreError, match="BYTE_LIMIT"):
        meter._strict_document(b"{}" + b" " * (meter.MAX_CHILD_BYTES - 1))
    assert meter._strict_document(b"{}" + b" " * (meter.MAX_REQUEST_BYTES - 2), limit=meter.MAX_REQUEST_BYTES) == {}
    with pytest.raises(meter.MeterPolicyStoreError, match="BYTE_LIMIT"):
        meter._strict_document(b"{}" + b" " * (meter.MAX_REQUEST_BYTES - 1), limit=meter.MAX_REQUEST_BYTES)
    assert meter._snapshot_json("a" * meter.MAX_STRING) == "a" * meter.MAX_STRING
    with pytest.raises(meter.MeterPolicyStoreError, match="JSON_LIMIT"):
        meter._snapshot_json("a" * (meter.MAX_STRING + 1))
    nested = None
    for _ in range(meter.MAX_DEPTH):
        nested = [nested]
    assert meter._snapshot_json(nested) == nested
    with pytest.raises(meter.MeterPolicyStoreError, match="JSON_LIMIT"):
        meter._snapshot_json([nested])
    assert len(meter._snapshot_json([None] * (meter.MAX_NODES - 1))) == meter.MAX_NODES - 1
    with pytest.raises(meter.MeterPolicyStoreError, match="JSON_LIMIT"):
        meter._snapshot_json([None] * meter.MAX_NODES)


def test_json_cycles_custom_types_and_non_string_keys_rejected_without_callbacks():
    cycle = []
    cycle.append(cycle)

    class Hostile(dict):
        def items(self):
            raise AssertionError("must never call caller serialization")

    for value in (cycle, Hostile(), {1: "x"}, (1, 2), Path("body"), b"body"):
        with pytest.raises(meter.MeterPolicyStoreError):
            meter._snapshot_json(value)


def test_integer_and_event_policy_limits_exact_and_one_over(project):
    assert meter._positive(meter.MAX_INTEGER) == meter.MAX_INTEGER
    assert meter._positive(meter.MAX_EVENTS, maximum=meter.MAX_EVENTS) == meter.MAX_EVENTS
    for value, maximum in ((meter.MAX_INTEGER + 1, meter.MAX_INTEGER), (meter.MAX_EVENTS + 1, meter.MAX_EVENTS)):
        with pytest.raises(meter.MeterPolicyStoreError):
            meter._positive(value, maximum=maximum)
    assert meter._policy(policy(meter.MAX_POLICIES, "sha256:" + "b" * 64)).policy_revision == meter.MAX_POLICIES
    with pytest.raises(meter.MeterPolicyStoreError):
        meter._policy(policy(meter.MAX_POLICIES + 1, "sha256:" + "b" * 64))
    command = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    command["expected_project_revision"] = meter.MAX_INTEGER
    rehash(command, meter.REQUEST_DOMAIN, "request_sha256")
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError, match="PROJECT_REVISION_OVERFLOW"):
        store(project).apply(command)
    assert file_snapshot(project) == before


def test_capacity_checks_before_append_without_pruning(project, monkeypatch):
    writer, _, _ = bootstrap(project)
    current = writer._collect()
    exhausted = deepcopy(current.state)
    exhausted["events"] = [deepcopy(exhausted["events"][0]) for _ in range(meter.MAX_EVENTS)]
    before = file_snapshot(project)
    # Isolated capacity seam: no claim that this repeated-event fixture is valid
    # history. It proves the pre-append branch, without bypassing public apply.
    with pytest.raises(meter.MeterPolicyStoreError, match="CAPACITY_EXHAUSTED"):
        writer._next_state(replace(current, state=exhausted), request(project, "PUBLISH_POLICY", {"policy_document": policy()}))
    # A bounded public-path capacity test uses the actual valid one-event head.
    monkeypatch.setattr(meter, "MAX_EVENTS", 1)
    with pytest.raises(meter.MeterPolicyStoreError, match="CAPACITY_EXHAUSTED"):
        apply(project, writer, "PUBLISH_POLICY", {"policy_document": policy()})
    assert file_snapshot(project) == before


@pytest.mark.parametrize("field", ["target_floor_dbfs", "target_ceiling_dbfs", "warning_dbfs", "true_clip_dbfs"])
def test_every_threshold_rejects_positive_and_schema_has_bound(field):
    schema = meter._load_entrypoints()["policy"]
    assert schema["$defs"]["policy"]["properties"][field]["maximum"] == 0
    document = policy()
    document[field] = 0.1
    rehash(document, POLICY_DIGEST_DOMAIN, "policy_revision_sha256")
    with pytest.raises(meter.MeterPolicyStoreError):
        meter._policy(document)


def test_policy_order_and_noncanonical_integer_thresholds():
    for field, value in (("target_floor_dbfs", -12.0), ("target_ceiling_dbfs", -3.0), ("warning_dbfs", 0.0), ("target_floor_dbfs", -24)):
        document = policy()
        document[field] = value
        rehash(document, POLICY_DIGEST_DOMAIN, "policy_revision_sha256")
        with pytest.raises(meter.MeterPolicyStoreError):
            meter._policy(document)


@pytest.mark.parametrize("relative", ["../outside", "/absolute", "voice-quality/../child", "//host/share", "voice-quality\\child", "voice-quality/C:child"])
def test_guard_rejects_traversal_absolute_unc_and_aliases(project, relative):
    before = file_snapshot(project)
    with pytest.raises(meter.MeterPolicyStoreError, match="PATH_INVALID"):
        meter._guard_path(project, relative)
    assert file_snapshot(project) == before


def test_root_and_direct_mount_child_rejected_without_writes(project, monkeypatch):
    with pytest.raises(meter.MeterPolicyStoreError, match="ROOT_INVALID"):
        store(Path("relative"))
    with pytest.raises(meter.MeterPolicyStoreError, match="ROOT_INVALID"):
        store(project / ".." / "synthetic-project")
    with pytest.raises(meter.MeterPolicyStoreError, match="DRIVE_ROOT_PLACEMENT"):
        store(Path(project.anchor))
    original = Path.is_mount
    monkeypatch.setattr(Path, "is_mount", lambda path: path == project.parent or original(path))
    with pytest.raises(meter.MeterPolicyStoreError, match="DRIVE_ROOT_PLACEMENT"):
        store(project)


@pytest.mark.parametrize("location", ["parent", "leaf", "control", "root"])
def test_symlink_paths_fail_closed_without_foreign_write(project, location):
    command = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    foreign = project.parent / "synthetic-foreign"
    foreign.mkdir()
    if location == "leaf":
        (project / "voice-quality").mkdir()
        (foreign / "body.json").write_bytes(b"untouched")
        target, destination = project / meter.CHILD_PATH, foreign / "body.json"
    elif location == "control":
        (project / ".bai-project").rename(project / "owned-control-preserved")
        target, destination = project / ".bai-project", foreign
    elif location == "root":
        target, destination = project.parent / "synthetic-root-alias", project
    else:
        target, destination = project / "voice-quality", foreign
    try:
        target.symlink_to(destination, target_is_directory=destination.is_dir())
    except OSError as exc:
        pytest.skip(f"OS symlink capability unavailable: {type(exc).__name__}")
    before = file_snapshot(foreign)
    if location == "root":
        with pytest.raises(meter.MeterPolicyStoreError, match="REPARSE_PATH"):
            store(target)
    else:
        reader = store(project)
        assert reader.read_snapshot(context()).snapshot is None
        with pytest.raises(meter.MeterPolicyStoreError):
            reader.apply(command)
    assert file_snapshot(foreign) == before


def test_hardlink_leaf_rejected_before_read_or_write(project):
    (project / "voice-quality").mkdir()
    foreign = project.parent / "synthetic-hardlink-body"
    foreign.write_bytes(b"do-not-overwrite")
    os.link(foreign, project / meter.CHILD_PATH)
    with pytest.raises(meter.MeterPolicyStoreError):
        bootstrap(project)
    assert foreign.read_bytes() == b"do-not-overwrite"


def test_case_collision_and_changed_root_physical_identity(project):
    (project / "Voice-Quality").mkdir()
    with pytest.raises(meter.MeterPolicyStoreError, match="CASE_ALIAS"):
        bootstrap(project)
    reader = store(project)
    project.rename(project.with_name("preserved-original-project"))
    project.mkdir()
    assert reader.read_snapshot(context()).status is meter.MeterPolicyReadStatus.MISMATCH
    assert list(project.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows junction runtime check NOT_EXECUTED on non-Windows Python")
def test_windows_junction_parent_rejected(project):
    foreign = project.parent / "synthetic-junction-target"
    foreign.mkdir()
    junction = project / "voice-quality"
    # Native PowerShell filesystem API; no cross-shell deletion and no cleanup
    # of foreign paths. Both operands are exact, task-owned pytest descendants.
    assert junction.parent.resolve(strict=True) == project.resolve(strict=True)
    assert foreign.resolve(strict=True).parent == project.parent.resolve(strict=True)
    quoted_junction = str(junction).replace("'", "''")
    quoted_foreign = str(foreign).replace("'", "''")
    command = f"New-Item -ItemType Junction -Path '{quoted_junction}' -Target '{quoted_foreign}' -ErrorAction Stop | Out-Null"
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert junction.lstat().st_file_attributes & 0x400
    with pytest.raises(meter.MeterPolicyStoreError, match="REPARSE_PATH"):
        bootstrap(project)
    assert list(foreign.iterdir()) == []


def test_bound_audio_shaped_bytes_only_integrity_hash_no_semantic_processing(project, monkeypatch):
    audio = project / "synthetic-assets" / "audio-shaped.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"RIFF\x00\x00\x00\x00WAVEsynth-not-real-audio")
    binding = ProjectChildBinding("TASK-024", "synthetic-assets/audio-shaped.wav", "synthetic.opaque", "1.0.0", sha256_bytes(audio.read_bytes()), True)
    ProductProjectManifestStore.path(project).write_bytes(canonical_json_bytes(manifest(1, [binding]).to_dict()))
    from ai_video_production import project_save

    original = project_save.sha256_file_exact
    hashes = []

    def observed_hash(path, *args, **kwargs):
        if Path(path) == audio:
            hashes.append(1)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(project_save, "sha256_file_exact", observed_hash)
    writer, receipt, _ = bootstrap(project)
    assert hashes
    assert binding in ProductProjectManifestStore.load(project).child_bindings
    documents = [state(project), receipt, writer.read_snapshot(context()).to_dict()]
    for document in documents:
        assert document["io_boundary"] == {
            "audio_semantic_decode_executed": False,
            "audio_used_as_policy_input": False,
            "project_integrity_hash_reads_possible": True,
        }
        serialized = canonical_json_bytes(document)
        assert b"RIFF" not in serialized and b"audio-shaped.wav" not in serialized
        assert b"audio_body_read" not in serialized
    assert all(value is False for value in documents[0]["authority"].values())
    audio.write_bytes(b"synthetic corrupt")
    assert writer.read_snapshot(context()).status is meter.MeterPolicyReadStatus.INVALID


def test_production_source_public_save_boundary_and_no_media_routes():
    source = (ROOT / "src/ai_video_production/voice_quality_meter_policy_store.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not imports.intersection({"wave", "soundfile", "numpy", "subprocess", "ctypes", "requests"})
    called = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not called.intersection({"write_bytes", "write_text", "unlink", "replace", "rename", "_save_unlocked", "_save_locked", "recover_complete", "recover_rollback"})
    assert {"save", "require_current_integrity", "mkdir", "rmdir"}.issubset(called)
    assert "compile_fixture_meter_display_currentness" not in source


def test_state_receipt_readback_authority_flags_cannot_be_changed(project):
    writer, receipt, _ = bootstrap(project)
    current = ProductProjectManifestStore.load(project)
    documents = [state(project), receipt, writer.read_snapshot(context()).to_dict()]
    serializers = [
        lambda doc: meter.serialize_meter_policy_state(doc, enclosing_manifest=current),
        meter.serialize_meter_policy_operation_receipt, meter.serialize_meter_policy_readback_evidence,
    ]
    for original, serializer in zip(documents, serializers):
        for key in ("audio_semantic_decode_executed", "audio_used_as_policy_input", "project_integrity_hash_reads_possible"):
            document = deepcopy(original)
            document["io_boundary"][key] = not document["io_boundary"][key]
            with pytest.raises(meter.MeterPolicyStoreError):
                serializer(document)
        document = deepcopy(original)
        document["audio_body_read"] = False
        with pytest.raises(meter.MeterPolicyStoreError):
            serializer(document)


def test_lost_parent_creation_reply_retains_uncertain_owned_directory(project, monkeypatch):
    original_mkdir = Path.mkdir

    def lost_mkdir_reply(path, *args, **kwargs):
        result = original_mkdir(path, *args, **kwargs)
        if path == project / "voice-quality":
            raise OSError("synthetic lost directory creation reply")
        return result

    monkeypatch.setattr(Path, "mkdir", lost_mkdir_reply)
    writer = store(project)
    before_manifest = ProductProjectManifestStore.path(project).read_bytes()
    with pytest.raises(meter.MeterPolicyStoreError, match="COMMIT_NOT_CONFIRMED"):
        bootstrap(project, writer)
    assert (project / "voice-quality").is_dir()
    assert list((project / "voice-quality").iterdir()) == []
    assert writer.residuals == ("VOICE_QUALITY_DIRECTORY_CREATION_UNCERTAIN",)
    assert ProductProjectManifestStore.path(project).read_bytes() == before_manifest
    assert not ProjectSaveJournalStore.path(project).exists()


@pytest.mark.parametrize("action,payload", [
    ("BOOTSTRAP", {"policy_ref": "meter-policy"}),
    ("PUBLISH_POLICY", {"policy_document": policy()}),
    ("SELECT_POLICY", {"policy_revision_sha256": "sha256:" + "e" * 64}),
    ("REVOKE_POLICY", {"policy_revision_sha256": "sha256:" + "e" * 64}),
])
def test_each_request_variant_has_closed_payload_and_public_roundtrip(project, action, payload):
    command = request(project, action, payload)
    if action != "BOOTSTRAP":
        command["expected_child_sha256"] = "sha256:" + "d" * 64
    rehash(command, meter.REQUEST_DOMAIN, "request_sha256")
    assert meter.parse_meter_policy_operation_request(meter.serialize_meter_policy_operation_request(command)) == command
    command["payload"]["extra"] = 0
    rehash(command, meter.REQUEST_DOMAIN, "request_sha256")
    with pytest.raises(meter.MeterPolicyStoreError, match="SCHEMA_INVALID"):
        meter.serialize_meter_policy_operation_request(command)


@pytest.mark.parametrize("changes", [
    {"domain_owner": "TASK-049"}, {"format_version": "2.0.0"},
    {"format_id": "synthetic.wrong"}, {"required": False},
    {"relative_path": "Voice-Quality/meter-policy-state.json"},
    {"relative_path": "voice-quality/other.json"},
    {"dependency_hashes": ("sha256:" + "a" * 64,)},
])
def test_binding_identity_fields_fail_closed(project, changes):
    writer, _, _ = bootstrap(project)
    current = ProductProjectManifestStore.load(project)
    bad = replace(current.child_bindings[0], **changes)
    new_manifest = manifest(current.project_revision, [bad], updated=current.updated_at)
    with pytest.raises(meter.MeterPolicyStoreError, match="BINDING_CONFLICT"):
        meter.parse_meter_policy_state((project / meter.CHILD_PATH).read_bytes(), enclosing_manifest=new_manifest)


@pytest.mark.parametrize("field", ["project_revision", "context", "policy"])
def test_low_level_snapshot_mutation_loses_local_admission(project, field):
    writer, _ = selected(project)
    query = context()
    snapshot = writer.read_snapshot(query).snapshot
    value = 999 if field == "project_revision" else context() if field == "context" else MeterDisplayPolicyRevision.from_dict(policy(floor=-25.0))
    object.__setattr__(snapshot, field, value)
    result = writer.revalidate(snapshot, query)
    assert result.status is meter.MeterPolicyReadStatus.MISMATCH
    assert result.snapshot is None


@pytest.mark.parametrize("seam", ["_collect", "_matching_event", "_receipt"])
@pytest.mark.parametrize("failure", [TypeError, LookupError, AssertionError])
def test_post_save_observation_exception_is_typed_commit_ambiguity(project, monkeypatch, seam, failure):
    committed = []

    class ObservedCommit(ProductProjectSaveCoordinator):
        def save(self, *args, **kwargs):
            result = super().save(*args, **kwargs)
            committed.append(True)
            return result

    writer = store(project, coordinator=ObservedCommit())
    original = getattr(writer, seam)

    def broken_after_save(*args, **kwargs):
        if committed:
            raise failure("synthetic post-save observation failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(writer, seam, broken_after_save)
    command = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    with pytest.raises(meter.MeterPolicyStoreError) as raised:
        writer.apply(command)
    assert raised.value.reason == "COMMIT_NOT_CONFIRMED"
    assert raised.value.operation_id == command["operation_id"]
    assert state(project)["events"][0]["request"] == command
    before = file_snapshot(project)
    fresh = store(project)
    receipt = fresh.read_operation_receipt(command["operation_id"], command)
    assert receipt["observation"] == "ALREADY_APPLIED"
    assert fresh.apply(command) == receipt
    assert file_snapshot(project) == before


@pytest.mark.parametrize("seam", ["save", "_collect", "_matching_event", "_receipt"])
@pytest.mark.parametrize("failure", [KeyboardInterrupt, SystemExit])
def test_post_commit_baseexception_is_not_swallowed(project, monkeypatch, seam, failure):
    committed = []
    interruption = failure("synthetic process interruption")

    class InterruptedCommit(ProductProjectSaveCoordinator):
        def save(self, *args, **kwargs):
            result = super().save(*args, **kwargs)
            committed.append(True)
            if seam == "save":
                raise interruption
            return result

    writer = store(project, coordinator=InterruptedCommit())
    if seam != "save":
        original = getattr(writer, seam)

        def interrupted_after_save(*args, **kwargs):
            if committed:
                raise interruption
            return original(*args, **kwargs)

        monkeypatch.setattr(writer, seam, interrupted_after_save)
    command = request(project, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    with pytest.raises(failure) as raised:
        writer.apply(command)
    assert raised.value is interruption
    assert state(project)["events"][0]["request"] == command
    before = file_snapshot(project)
    assert store(project).read_operation_receipt(command["operation_id"], command)["observation"] == "ALREADY_APPLIED"
    assert file_snapshot(project) == before


def test_store_copy_and_standard_serialization_cannot_share_admission(project):
    writer, _ = selected(project)
    query = context()
    snapshot = writer.read_snapshot(query).snapshot
    for operation in (copy, deepcopy, pickle.dumps, json.dumps):
        with pytest.raises(TypeError):
            operation(writer)
    for operation in (writer.__getstate__, writer.__reduce__):
        with pytest.raises(TypeError):
            operation()
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(TypeError):
            writer.__reduce_ex__(protocol)
        with pytest.raises(TypeError):
            pickle.dumps(writer, protocol=protocol)
    assert writer.revalidate(snapshot, query).snapshot is not None
    separate = store(project)
    assert separate.producer_epoch != writer.producer_epoch
    assert separate.revalidate(snapshot, query).status is meter.MeterPolicyReadStatus.MISMATCH
    writer.close()
    assert writer.revalidate(snapshot, query).status is meter.MeterPolicyReadStatus.MISMATCH
    assert store(project).revalidate(snapshot, query).status is meter.MeterPolicyReadStatus.MISMATCH
