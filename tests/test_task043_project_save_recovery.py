from __future__ import annotations

from importlib import resources
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
import pytest

from ai_video_production.errors import ProductError
from ai_video_production.product_project import ProductProjectManifest, ProjectChildBinding, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_save import (
    ProductProjectSaveCoordinator,
    ProjectSaveParticipantOutcome,
    ProjectSaveParticipantPlan,
    ProjectSaveParticipantResult,
    ProjectSaveJournalStore,
    ProjectSaveState,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


CREATED = "2026-08-15T00:00:00.000Z"
UPDATED = "2026-08-15T00:01:00.000Z"


def binding(path: str, data: bytes, *, owner: str = "TASK-037", required: bool = True) -> ProjectChildBinding:
    return ProjectChildBinding(owner, path, "bai.test-child", "1.0.0", sha256_bytes(data), required)


def project_manifest(revision: int, *bindings: ProjectChildBinding) -> ProductProjectManifest:
    return ProductProjectManifest.create(
        project_id="project-1",
        project_revision=revision,
        product_version="0.20.1",
        timebase=ProjectTimebase(30, 1),
        child_bindings=bindings,
        created_at=CREATED,
        updated_at=CREATED if revision == 1 else UPDATED,
    )


def setup_project(root: Path, *, second_child: bool = False):
    first_path = root / "state/first.json"
    first_path.parent.mkdir()
    first_path.write_bytes(b"old-first")
    current_bindings = [binding("state/first.json", b"old-first")]
    target_bindings = [binding("state/first.json", b"new-first")]
    documents = {"state/first.json": b"new-first"}
    if second_child:
        second_path = root / "state/second.json"
        second_path.write_bytes(b"old-second")
        current_bindings.append(binding("state/second.json", b"old-second", owner="TASK-041"))
        target_bindings.append(binding("state/second.json", b"new-second", owner="TASK-041"))
        documents["state/second.json"] = b"new-second"
    current = project_manifest(1, *current_bindings)
    target = project_manifest(2, *target_bindings)
    ProductProjectManifestStore.save(root, current)
    return current, target, documents


def fail_once_at(stage_name: str):
    fired = False

    def inject(stage: str, _root: Path) -> None:
        nonlocal fired
        if stage == stage_name and not fired:
            fired = True
            raise RuntimeError(f"injected:{stage}")

    return inject


class _TestParticipant:
    participant_id = "TASK-043/TEST-PARTICIPANT"
    participant_version = "1.0.0"

    def __init__(self, target: bytes = b"participant-target", *, fail_reconcile_once: bool = False) -> None:
        self.target = target
        self.fail_reconcile_once = fail_reconcile_once
        self.prepare_calls = 0
        self.reconcile_calls: list[str] = []
        self.abort_calls = 0

    @staticmethod
    def _state(root: Path) -> Path:
        return root / ".bai-project" / "test-participant-state.bin"

    @staticmethod
    def _recovery(root: Path) -> Path:
        return root / ".bai-project" / "test-participant-recovery.json"

    def plan_locked(self, root: Path, source: ProductProjectManifest,
                    target: ProductProjectManifest) -> ProjectSaveParticipantPlan:
        state = self._state(root)
        source_sha = sha256_bytes(state.read_bytes()) if state.exists() else None
        return ProjectSaveParticipantPlan.create(
            participant_id=self.participant_id,
            participant_version=self.participant_version,
            project_id=source.project_id,
            source_manifest_sha256=source.project_manifest_sha256,
            target_manifest_sha256=target.project_manifest_sha256,
            source_content_sha256=source_sha,
            target_content_sha256=sha256_bytes(self.target),
        )

    def prepare_locked(self, root: Path, transaction_id: str,
                       plan: ProjectSaveParticipantPlan) -> str:
        self.prepare_calls += 1
        body = {
            "transaction_id": transaction_id,
            "binding_sha256": plan.binding_sha256,
            "project_id": plan.project_id,
            "source_manifest_sha256": plan.source_manifest_sha256,
        }
        receipt = sha256_bytes(canonical_json_bytes(body))
        self._recovery(root).write_text(json.dumps({**body, "receipt_sha256": receipt}), encoding="utf-8")
        return receipt

    def reconcile_locked(self, root: Path, transaction_id: str,
                         plan: ProjectSaveParticipantPlan, prepared_receipt_sha256: str,
                         outcome: ProjectSaveParticipantOutcome) -> ProjectSaveParticipantResult:
        self.reconcile_calls.append(outcome.value)
        if self.fail_reconcile_once:
            self.fail_reconcile_once = False
            raise RuntimeError("participant reconcile failed")
        recovery = self._recovery(root)
        state = self._state(root)
        expected = sha256_bytes(canonical_json_bytes({
            "transaction_id": transaction_id,
            "binding_sha256": plan.binding_sha256,
            "project_id": plan.project_id,
            "source_manifest_sha256": plan.source_manifest_sha256,
        }))
        if recovery.exists():
            document = json.loads(recovery.read_text(encoding="utf-8"))
            assert document == {
                "transaction_id": transaction_id,
                "binding_sha256": plan.binding_sha256,
                "project_id": plan.project_id,
                "source_manifest_sha256": plan.source_manifest_sha256,
                "receipt_sha256": expected,
            }
            assert prepared_receipt_sha256 == expected
            if outcome is ProjectSaveParticipantOutcome.COMPLETE:
                state.write_bytes(self.target)
            elif plan.source_content_sha256 is None:
                if state.exists():
                    state.unlink()
            recovery.unlink()
        observed = sha256_bytes(state.read_bytes()) if state.exists() else None
        expected_result = (
            plan.target_content_sha256
            if outcome is ProjectSaveParticipantOutcome.COMPLETE
            else plan.source_content_sha256
        )
        assert observed == expected_result
        return ProjectSaveParticipantResult.create(
            participant_id=self.participant_id,
            binding_sha256=plan.binding_sha256,
            transaction_id=transaction_id,
            outcome=outcome,
            result_content_sha256=observed,
        )

    def abort_prejournal_locked(self, root: Path, transaction_id: str,
                                plan: ProjectSaveParticipantPlan,
                                prepared_receipt_sha256: str) -> None:
        self.abort_calls += 1
        recovery = self._recovery(root)
        if recovery.exists():
            recovery.unlink()

    def reconcile_orphan_locked(self, root: Path,
                                current: ProductProjectManifest) -> str | None:
        recovery = self._recovery(root)
        if not recovery.exists():
            return None
        document = json.loads(recovery.read_text(encoding="utf-8"))
        body = {key: value for key, value in document.items() if key != "receipt_sha256"}
        assert document["project_id"] == current.project_id
        assert document["source_manifest_sha256"] == current.project_manifest_sha256
        assert document["receipt_sha256"] == sha256_bytes(canonical_json_bytes(body))
        recovery.unlink()
        return document["receipt_sha256"]


def test_journal_schema_is_valid_and_packaged_copy_is_exact() -> None:
    public = Path(__file__).parents[1] / "schemas/project-save-journal.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", public.name)
    assert public.read_bytes() == packaged.read_bytes()
    Draft202012Validator.check_schema(json.loads(public.read_text(encoding="utf-8")))


def journal_schema_validator() -> Draft202012Validator:
    schema_root = Path(__file__).parents[1] / "schemas"
    journal_schema = json.loads((schema_root / "project-save-journal.schema.json").read_text(encoding="utf-8"))
    manifest_schema = json.loads((schema_root / "product-project-manifest.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        manifest_schema["$id"],
        Resource.from_contents(manifest_schema),
    )
    return Draft202012Validator(journal_schema, registry=registry)


def test_coordinated_save_commits_children_before_manifest_and_is_reopenable(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path, second_child=True)
    result = ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    assert result == target
    assert (tmp_path / "state/first.json").read_bytes() == b"new-first"
    assert (tmp_path / "state/second.json").read_bytes() == b"new-second"
    assert ProductProjectManifestStore.load(tmp_path) == target
    journal = ProjectSaveJournalStore.load(tmp_path)
    assert journal.state is ProjectSaveState.COMMITTED
    assert all(entry.committed for entry in journal.entries)
    assert ProductProjectSaveCoordinator().recovery_status(tmp_path)["required"] is False


def test_failure_after_first_child_requires_recovery_and_keeps_old_manifest(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path, second_child=True)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError, match="injected"):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    assert ProductProjectManifestStore.load(tmp_path) == current
    status = coordinator.recovery_status(tmp_path)
    assert status["required"] is True
    assert set(status["available_actions"]) == {"COMPLETE", "ROLLBACK"}
    with pytest.raises(ProductError) as admission:
        ProductProjectSaveCoordinator().require_current_integrity(tmp_path, current)
    assert admission.value.code == "ERR_PROJECT_SAVE_RECOVERY_REQUIRED"


def test_current_integrity_rejects_manifest_bound_child_drift(tmp_path: Path) -> None:
    current, _target, _documents = setup_project(tmp_path)
    ProductProjectSaveCoordinator().require_current_integrity(tmp_path, current)
    (tmp_path / "state/first.json").write_bytes(b"tampered")
    with pytest.raises(ProductError) as rejected:
        ProductProjectSaveCoordinator().require_current_integrity(tmp_path, current)
    assert rejected.value.code == "ERR_PROJECT_SAVE_RECOVERY_TARGET_CONFLICT"


def test_recovery_complete_finishes_same_transaction_without_duplicate_write(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path, second_child=True)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    transaction_id = coordinator.recovery_status(tmp_path)["transaction_id"]
    result = ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id=transaction_id)
    assert result == target
    assert ProductProjectManifestStore.load(tmp_path) == target
    assert (tmp_path / "state/first.json").read_bytes() == b"new-first"
    assert (tmp_path / "state/second.json").read_bytes() == b"new-second"


def test_recovery_rollback_restores_every_previous_child(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path, second_child=True)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    transaction_id = coordinator.recovery_status(tmp_path)["transaction_id"]
    result = ProductProjectSaveCoordinator().recover_rollback(tmp_path, transaction_id=transaction_id)
    assert result == current
    assert ProductProjectManifestStore.load(tmp_path) == current
    assert (tmp_path / "state/first.json").read_bytes() == b"old-first"
    assert (tmp_path / "state/second.json").read_bytes() == b"old-second"
    assert ProjectSaveJournalStore.load(tmp_path).state is ProjectSaveState.ABANDONED


def test_failure_after_manifest_commit_offers_finalize_only(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_manifest_commit"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    status = coordinator.recovery_status(tmp_path)
    assert status["available_actions"] == ["FINALIZE"]
    assert ProductProjectManifestStore.load(tmp_path) == target
    ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id=status["transaction_id"])
    assert ProjectSaveJournalStore.load(tmp_path).state is ProjectSaveState.COMMITTED


def test_finalize_revalidates_every_target_child(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_manifest_commit"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    status = coordinator.recovery_status(tmp_path)
    (tmp_path / "state/first.json").write_bytes(b"changed-after-commit")
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id=status["transaction_id"])
    assert exc.value.code == "ERR_PROJECT_SAVE_RECOVERY_TARGET_CONFLICT"


def test_new_save_is_blocked_while_recovery_is_pending(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_journal_staged"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_RECOVERY_REQUIRED"


def test_preflight_rejects_unbound_child_without_creating_journal(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    documents["state/unbound.json"] = b"unbound"
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_UNBOUND_CHILD"
    assert not ProjectSaveJournalStore.path(tmp_path).exists()


def test_preflight_rejects_target_checksum_mismatch(tmp_path: Path) -> None:
    current, target, _documents = setup_project(tmp_path)
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            {"state/first.json": b"wrong"},
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_CHILD_CHECKSUM"


def test_preflight_rejects_source_child_drift(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    (tmp_path / "state/first.json").write_bytes(b"human-change")
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_SOURCE_CHILD_CONFLICT"


def test_removing_existing_binding_requires_explicit_migration(tmp_path: Path) -> None:
    current, _target, _documents = setup_project(tmp_path, second_child=True)
    target = project_manifest(2, binding("state/first.json", b"old-first"))
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            {},
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_BINDING_REMOVAL_REQUIRES_MIGRATION"


def test_recovery_rollback_removes_new_child_that_did_not_exist_before(tmp_path: Path) -> None:
    current, _target, _documents = setup_project(tmp_path)
    new_binding = binding("state/new.json", b"new-child", owner="TASK-041")
    target = project_manifest(2, *current.child_bindings, new_binding)
    documents = {"state/new.json": b"new-child"}
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    assert (tmp_path / "state/new.json").exists()
    status = coordinator.recovery_status(tmp_path)
    ProductProjectSaveCoordinator().recover_rollback(tmp_path, transaction_id=status["transaction_id"])
    assert not (tmp_path / "state/new.json").exists()
    assert ProductProjectManifestStore.load(tmp_path) == current


def test_tampered_staging_blocks_complete_but_valid_backup_allows_rollback(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_journal_validated"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    journal = ProjectSaveJournalStore.load(tmp_path)
    staged = tmp_path / ".bai-project" / journal.entries[0].staged_relative_path
    staged.write_bytes(b"tampered")
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id=journal.transaction_id)
    assert exc.value.code == "ERR_PROJECT_SAVE_STAGING_INVALID"
    ProductProjectSaveCoordinator().recover_rollback(tmp_path, transaction_id=journal.transaction_id)
    assert (tmp_path / "state/first.json").read_bytes() == b"old-first"


def test_wrong_recovery_identity_is_rejected(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_journal_staged"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id="save-" + "f" * 64)
    assert exc.value.code == "ERR_PROJECT_SAVE_RECOVERY_IDENTITY"


def test_journal_checksum_tampering_is_detected(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    path = ProjectSaveJournalStore.path(tmp_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    value["journal_revision"] += 1
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ProjectSaveJournalStore.load(tmp_path)
    assert exc.value.code == "ERR_PROJECT_SAVE_JOURNAL_INVALID"


def test_journal_cannot_redirect_staging_path_outside_transaction_scope(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    path = ProjectSaveJournalStore.path(tmp_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    value["entries"][0]["staged_relative_path"] = "save-journal.json"
    body = {key: item for key, item in value.items() if key != "journal_sha256"}
    value["journal_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ProjectSaveJournalStore.load(tmp_path)
    assert exc.value.code == "ERR_PROJECT_SAVE_JOURNAL_INVALID"


def test_retry_after_rollback_reuses_identical_staging_safely(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    status = coordinator.recovery_status(tmp_path)
    ProductProjectSaveCoordinator().recover_rollback(tmp_path, transaction_id=status["transaction_id"])
    ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    assert ProductProjectManifestStore.load(tmp_path) == target


def test_participant_save_uses_v1_1_and_reconciles_before_committed(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    participant = _TestParticipant()
    ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
        participant=participant,
    )
    journal = ProjectSaveJournalStore.load(tmp_path)
    assert journal.journal_version == "1.1.0"
    assert journal.state is ProjectSaveState.COMMITTED
    assert journal.participant_plan.participant_id == participant.participant_id
    assert journal.participant_result.outcome is ProjectSaveParticipantOutcome.COMPLETE
    assert participant.prepare_calls == 1
    assert participant.reconcile_calls == ["COMPLETE"]
    assert _TestParticipant._state(tmp_path).read_bytes() == participant.target


def test_runtime_v1_0_and_v1_1_journals_match_public_schema(tmp_path: Path) -> None:
    validator = journal_schema_validator()
    legacy_root = tmp_path / "legacy"
    legacy_root.mkdir()
    current, target, documents = setup_project(legacy_root)
    ProductProjectSaveCoordinator().save(
        legacy_root,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    legacy = ProjectSaveJournalStore.load(legacy_root).to_dict()
    validator.validate(legacy)

    participant_root = tmp_path / "participant"
    participant_root.mkdir()
    current, target, documents = setup_project(participant_root)
    ProductProjectSaveCoordinator().save(
        participant_root,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
        participant=_TestParticipant(),
    )
    participant = ProjectSaveJournalStore.load(participant_root).to_dict()
    validator.validate(participant)

    invalid_legacy = {**legacy, "participant_result": None}
    with pytest.raises(ValidationError):
        validator.validate(invalid_legacy)
    missing_plan = {key: value for key, value in participant.items() if key != "participant_plan"}
    with pytest.raises(ValidationError):
        validator.validate(missing_plan)
    wrong_outcome = json.loads(json.dumps(participant))
    wrong_outcome["participant_result"]["outcome"] = "ROLLBACK"
    with pytest.raises(ValidationError):
        validator.validate(wrong_outcome)


def test_participant_complete_requires_exact_runtime_and_is_restart_idempotent(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    participant = _TestParticipant()
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            participant=participant,
        )
    status = coordinator.recovery_status(tmp_path)
    assert status["participant_required"] is True
    assert status["participant_id"] == participant.participant_id
    with pytest.raises(ProductError) as missing:
        ProductProjectSaveCoordinator().recover_complete(
            tmp_path,
            transaction_id=status["transaction_id"],
        )
    assert missing.value.code == "ERR_PROJECT_SAVE_PARTICIPANT_REQUIRED"
    restarted = _TestParticipant()
    ProductProjectSaveCoordinator().recover_complete(
        tmp_path,
        transaction_id=status["transaction_id"],
        participant=restarted,
    )
    journal = ProjectSaveJournalStore.load(tmp_path)
    assert journal.state is ProjectSaveState.COMMITTED
    assert restarted.reconcile_calls == ["COMPLETE"]
    assert _TestParticipant._state(tmp_path).read_bytes() == restarted.target


def test_participant_rollback_reconciles_source_and_abandons_exact_transaction(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    state = _TestParticipant._state(tmp_path)
    state.write_bytes(b"participant-source")
    participant = _TestParticipant()
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            participant=participant,
        )
    status = coordinator.recovery_status(tmp_path)
    restarted = _TestParticipant()
    ProductProjectSaveCoordinator().recover_rollback(
        tmp_path,
        transaction_id=status["transaction_id"],
        participant=restarted,
    )
    journal = ProjectSaveJournalStore.load(tmp_path)
    assert journal.state is ProjectSaveState.ABANDONED
    assert journal.participant_result.outcome is ProjectSaveParticipantOutcome.ROLLBACK
    assert restarted.reconcile_calls == ["ROLLBACK"]
    assert state.read_bytes() == b"participant-source"
    assert (tmp_path / "state/first.json").read_bytes() == b"old-first"


def test_participant_failure_after_manifest_stays_finalize_only_and_retries(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    participant = _TestParticipant(fail_reconcile_once=True)
    with pytest.raises(RuntimeError, match="participant reconcile failed"):
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            participant=participant,
        )
    status = ProductProjectSaveCoordinator().recovery_status(tmp_path)
    assert status["available_actions"] == ["FINALIZE"]
    restarted = _TestParticipant()
    ProductProjectSaveCoordinator().recover_complete(
        tmp_path,
        transaction_id=status["transaction_id"],
        participant=restarted,
    )
    assert ProjectSaveJournalStore.load(tmp_path).state is ProjectSaveState.COMMITTED
    assert restarted.reconcile_calls == ["COMPLETE"]


def test_participant_prejournal_failure_aborts_only_prepared_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    current, target, documents = setup_project(tmp_path)
    participant = _TestParticipant()
    original = ProjectSaveJournalStore.save

    def fail_before_journal(root: Path, journal):
        raise OSError("journal unavailable")

    monkeypatch.setattr(ProjectSaveJournalStore, "save", staticmethod(fail_before_journal))
    with pytest.raises(OSError, match="journal unavailable"):
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            participant=participant,
        )
    monkeypatch.setattr(ProjectSaveJournalStore, "save", staticmethod(original))
    assert participant.prepare_calls == 1
    assert participant.abort_calls == 1
    assert not _TestParticipant._recovery(tmp_path).exists()


def test_participant_recovery_rejects_wrong_runtime_and_tampered_binding(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    participant = _TestParticipant()
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_journal_staged"))
    with pytest.raises(RuntimeError):
        coordinator.save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            participant=participant,
        )
    status = coordinator.recovery_status(tmp_path)

    class WrongParticipant(_TestParticipant):
        participant_id = "TASK-043/WRONG-PARTICIPANT"

    with pytest.raises(ProductError) as wrong:
        ProductProjectSaveCoordinator().recover_complete(
            tmp_path,
            transaction_id=status["transaction_id"],
            participant=WrongParticipant(),
        )
    assert wrong.value.code == "ERR_PROJECT_SAVE_PARTICIPANT_REQUIRED"

    path = ProjectSaveJournalStore.path(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["participant_plan"]["target_content_sha256"] = sha256_bytes(b"tampered")
    body = {key: value for key, value in document.items() if key != "journal_sha256"}
    document["journal_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as tampered:
        ProjectSaveJournalStore.load(tmp_path)
    assert tampered.value.code == "ERR_PROJECT_SAVE_JOURNAL_INVALID"


def test_v1_0_journal_projection_has_no_participant_fields(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    document = ProjectSaveJournalStore.load(tmp_path).to_dict()
    assert document["journal_version"] == "1.0.0"
    assert "participant_plan" not in document
    assert "participant_prepared_receipt_sha256" not in document
    assert "participant_result" not in document


def test_terminal_journal_write_failure_retains_participant_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    current, target, documents = setup_project(tmp_path)
    participant = _TestParticipant()
    original = ProjectSaveJournalStore.save
    failed = False

    def fail_committed_once(root: Path, journal):
        nonlocal failed
        if journal.state is ProjectSaveState.COMMITTED and not failed:
            failed = True
            raise OSError("terminal journal write failed")
        return original(root, journal)

    monkeypatch.setattr(ProjectSaveJournalStore, "save", staticmethod(fail_committed_once))
    with pytest.raises(OSError, match="terminal journal write failed"):
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            participant=participant,
        )
    status = ProductProjectSaveCoordinator().recovery_status(tmp_path)
    assert status["required"] is True
    assert status["available_actions"] == ["FINALIZE"]
    monkeypatch.setattr(ProjectSaveJournalStore, "save", staticmethod(original))
    ProductProjectSaveCoordinator().recover_complete(
        tmp_path,
        transaction_id=status["transaction_id"],
        participant=_TestParticipant(),
    )
    assert ProjectSaveJournalStore.load(tmp_path).state is ProjectSaveState.COMMITTED


def test_prejournal_process_crash_orphan_is_reconciled_under_project_lock(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    participant = _TestParticipant()
    plan = participant.plan_locked(tmp_path, current, target)
    transaction_id = ProductProjectSaveCoordinator._transaction_id(
        current,
        target,
        documents,
        participant_binding_sha256=plan.binding_sha256,
    )
    receipt = participant.prepare_locked(tmp_path, transaction_id, plan)
    assert _TestParticipant._recovery(tmp_path).exists()
    result = ProductProjectSaveCoordinator().reconcile_participant_orphan(
        tmp_path,
        participant=participant,
    )
    assert result == {
        "participant_id": participant.participant_id,
        "reconciled": True,
        "orphan_receipt_sha256": receipt,
    }
    assert not _TestParticipant._recovery(tmp_path).exists()
    assert ProductProjectManifestStore.load(tmp_path) == current
    assert (tmp_path / "state/first.json").read_bytes() == b"old-first"


def test_abandoned_terminal_write_failure_is_rollback_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    current, target, documents = setup_project(tmp_path)
    participant = _TestParticipant()
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            participant=participant,
        )
    transaction_id = coordinator.recovery_status(tmp_path)["transaction_id"]
    original = ProjectSaveJournalStore.save
    failed = False

    def fail_abandoned_once(root: Path, journal):
        nonlocal failed
        if journal.state is ProjectSaveState.ABANDONED and not failed:
            failed = True
            raise OSError("abandoned journal write failed")
        return original(root, journal)

    monkeypatch.setattr(ProjectSaveJournalStore, "save", staticmethod(fail_abandoned_once))
    with pytest.raises(OSError, match="abandoned journal write failed"):
        ProductProjectSaveCoordinator().recover_rollback(
            tmp_path,
            transaction_id=transaction_id,
            participant=_TestParticipant(),
        )
    status = ProductProjectSaveCoordinator().recovery_status(tmp_path)
    assert status["available_actions"] == ["ROLLBACK"]
    before_manifest = ProductProjectManifestStore.load(tmp_path)
    before_child = (tmp_path / "state/first.json").read_bytes()
    with pytest.raises(ProductError) as conflict:
        ProductProjectSaveCoordinator().recover_complete(
            tmp_path,
            transaction_id=transaction_id,
            participant=_TestParticipant(),
        )
    assert conflict.value.code == "ERR_PROJECT_SAVE_PARTICIPANT_OUTCOME_CONFLICT"
    assert ProductProjectManifestStore.load(tmp_path) == before_manifest == current
    assert (tmp_path / "state/first.json").read_bytes() == before_child == b"old-first"
    monkeypatch.setattr(ProjectSaveJournalStore, "save", staticmethod(original))
    ProductProjectSaveCoordinator().recover_rollback(
        tmp_path,
        transaction_id=transaction_id,
        participant=_TestParticipant(),
    )
    assert ProjectSaveJournalStore.load(tmp_path).state is ProjectSaveState.ABANDONED
