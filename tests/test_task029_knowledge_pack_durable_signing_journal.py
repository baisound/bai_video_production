from __future__ import annotations

import base64
from dataclasses import replace
import inspect
import json
import multiprocessing as mp
import time
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.errors import ProductError
from ai_video_production.knowledge_pack_durable_signing_journal import (
    DurableSigningCeremonyJournal,
    DurableSigningJournalReceipt,
    DurableSigningJournalState,
)
from ai_video_production.knowledge_pack_local_signing_ceremony import (
    LocalSigningCeremonyReceipt,
    LocalSigningCeremonyResult,
)
from ai_video_production.knowledge_pack_signature_verification import (
    KnowledgePackSignatureVerificationReceipt,
)
from test_task029_knowledge_pack_local_signing_ceremony import case


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "knowledge-pack-durable-signing-journal-receipt.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name


def kwargs(tmp_path: Path):
    values = case(tmp_path / "case")
    store, _, custody, request, request_kwargs, policy, confirmation, _, _ = values
    return values, {
        "journal_id": "journal.r9d",
        "reserved_at_epoch_ms": 300,
        "recovery_observed_at_epoch_ms": 302,
        "receipt_id": "ceremony-receipt.r9d",
        "verification_receipt_id": "verification-receipt.r9d",
        "custody_store": store,
        "custody_receipt_payload": custody.to_dict(),
        "signature_request_payload": request.to_dict(),
        "signature_request_compile_kwargs": request_kwargs,
        "trusted_signer_policy_payload": policy.to_dict(),
        "confirmation": confirmation,
        "completed_at_epoch_ms": 301,
    }


def _multiprocess_execute(queue: object, journal_path: str, arguments: dict[str, object]) -> None:
    try:
        receipt, _ = DurableSigningCeremonyJournal(journal_path).execute_once(**arguments)
        queue.put(("success", receipt.state.value))
    except ProductError as exc:
        queue.put(("error", exc.code))

def _cleanup_processes(
    processes: list[mp.Process], *, join_timeout: float
) -> list[int | None]:
    errors: list[BaseException] = []

    def attempt(action: object) -> None:
        try:
            action()
        except BaseException as exc:  # cleanup must continue for every resource
            errors.append(exc)

    for process in processes:
        attempt(lambda process=process: process.join(join_timeout))
    for process in processes:
        try:
            alive = process.is_alive()
        except BaseException as exc:
            errors.append(exc)
            alive = True
        if alive:
            attempt(process.terminate)
    for process in processes:
        attempt(lambda process=process: process.join(5))
    for process in processes:
        try:
            alive = process.is_alive()
        except BaseException as exc:
            errors.append(exc)
            alive = True
        if alive:
            attempt(process.kill)
    for process in processes:
        attempt(lambda process=process: process.join(5))

    exitcodes: list[int | None] = []
    for process in processes:
        try:
            alive = process.is_alive()
            exitcode = process.exitcode
            if alive:
                errors.append(AssertionError("multiprocess child remained alive after kill"))
            exitcodes.append(exitcode)
        except BaseException as exc:
            errors.append(exc)
            exitcodes.append(None)
        finally:
            attempt(process.close)
    if errors:
        raise AssertionError(
            f"multiprocess cleanup encountered {len(errors)} error(s)"
        ) from errors[0]
    return exitcodes

def test_exact_ceremony_is_reserved_then_committed_body_free(tmp_path: Path) -> None:
    values, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")
    receipt, result = journal.execute_once(**arguments)
    payload = receipt.to_dict()

    assert receipt.state is DurableSigningJournalState.SIGNED_AND_VERIFIED
    assert payload["persistent_replay_prevention_present"] is False
    assert payload["path_local_replay_prevention_present"] is True
    assert payload["canonical_project_binding_present"] is False
    assert payload["journal_deletion_detection_present"] is False
    assert payload["reservation_directory_durability_confirmed"] is False
    assert payload["power_loss_replay_prevention_confirmed"] is False
    assert payload["path_security_model"] == "COOPERATIVE_PROTECTED_LOCAL_WRITER_ONLY"
    assert payload["hostile_path_race_protection_verified"] is False
    assert payload["symlink_path_rejection_present"] is True
    assert payload["automatic_replay_authorized"] is False
    assert payload["ceremony_receipt_sha256"] == result.receipt.to_dict()["ceremony_receipt_sha256"]
    assert payload["verification_receipt_sha256"] == result.verification_receipt.to_dict()["verification_receipt_sha256"]
    assert result.receipt.to_dict()["persistent_replay_prevention_present"] is False
    for field in (
        "signature_bytes_included",
        "public_key_material_included",
        "private_key_material_included",
        "knowledge_pack_write_authorized",
        "knowledge_pack_promotion_authorized",
        "automatic_promotion_authorized",
        "runtime_profile_apply_authorized",
        "rollback_execution_authorized",
        "release_authorized",
        "external_effect_authorized",
    ):
        assert payload[field] is False
    raw = (tmp_path / "journal.json").read_bytes()
    assert values[7] not in raw and values[8] not in raw
    assert base64.b64encode(values[7]) not in raw
    assert base64.b64encode(values[8]) not in raw
    assert DurableSigningJournalReceipt.from_dict(payload) == receipt
    assert journal.read_receipt() == receipt


def test_terminal_receipt_blocks_duplicate_without_key_access(tmp_path: Path) -> None:
    values, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")
    journal.execute_once(**arguments)
    decrypt_count = values[1].decrypt_count
    with pytest.raises(ProductError) as error:
        journal.execute_once(**arguments)
    assert error.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_ALREADY_FINAL"
    assert values[1].decrypt_count == decrypt_count


def test_known_executor_failure_becomes_terminal_recovery_required(tmp_path: Path) -> None:
    _, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")

    def fail():
        raise RuntimeError("synthetic failure")

    with pytest.raises(ProductError) as error:
        journal.execute_once(**arguments, after_reservation_fault_hook=fail)
    assert error.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_RECOVERY_REQUIRED"
    assert journal.read_receipt().state is DurableSigningJournalState.RECOVERY_REQUIRED

    called = False

    def must_not_run():
        nonlocal called
        called = True
        raise AssertionError("must not execute")

    with pytest.raises(ProductError) as duplicate:
        journal.execute_once(**arguments, after_reservation_fault_hook=must_not_run)
    assert duplicate.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_ALREADY_FINAL"
    assert called is False


def test_process_interruption_leaves_reservation_then_recovers_without_replay(tmp_path: Path) -> None:
    _, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")

    def interrupt():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        journal.execute_once(**arguments, after_reservation_fault_hook=interrupt)
    assert journal.read_receipt().state is DurableSigningJournalState.SIGNING_RESERVED

    called = False

    def must_not_run():
        nonlocal called
        called = True
        raise AssertionError("must not execute")

    retry = dict(arguments)
    retry["recovery_observed_at_epoch_ms"] = 400
    with pytest.raises(ProductError) as error:
        journal.execute_once(**retry, after_reservation_fault_hook=must_not_run)
    assert error.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_RECOVERY_REQUIRED"
    assert called is False
    assert journal.read_receipt().state is DurableSigningJournalState.RECOVERY_REQUIRED


def test_final_atomic_failure_keeps_reservation_and_blocks_replay(tmp_path: Path) -> None:
    _, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")

    def stop(stage: str, _: Path) -> None:
        if stage == "before_replace":
            raise RuntimeError("injected final write failure")

    with pytest.raises(RuntimeError, match="final write"):
        journal.execute_once(**arguments, final_failure_injector=stop)
    assert journal.read_receipt().state is DurableSigningJournalState.SIGNING_RESERVED
    with pytest.raises(ProductError) as error:
        journal.execute_once(**arguments)
    assert error.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_RECOVERY_REQUIRED"


def test_stale_request_fails_before_journal_or_key_access(tmp_path: Path) -> None:
    values, arguments = kwargs(tmp_path)
    tampered = dict(arguments["signature_request_payload"])
    tampered["pack_version"] = "9.9.9"
    arguments["signature_request_payload"] = tampered
    before = values[1].decrypt_count
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")
    with pytest.raises(ValueError):
        journal.execute_once(**arguments)
    assert not (tmp_path / "journal.json").exists()
    assert values[1].decrypt_count == before


def test_current_custody_drift_after_reservation_becomes_recovery_required(tmp_path: Path) -> None:
    _, arguments = kwargs(tmp_path)
    other = case(tmp_path / "other")

    class DriftedCustodyStore:
        def read_receipt(self):
            return other[2]

    arguments["custody_store"] = DriftedCustodyStore()
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")
    with pytest.raises(ProductError) as error:
        journal.execute_once(**arguments)
    assert error.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_RECOVERY_REQUIRED"
    assert journal.read_receipt().state is DurableSigningJournalState.RECOVERY_REQUIRED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("journal_id", "journal.other"),
        ("ceremony_id", "ceremony.other"),
        ("custody_receipt_sha256", "sha256:" + "1" * 64),
        ("signature_request_sha256", "sha256:" + "2" * 64),
        ("confirmation_sha256", "sha256:" + "3" * 64),
    ],
)
def test_every_exact_identity_coordinate_conflict_is_terminal(
    tmp_path: Path, field: str, value: str
) -> None:
    _, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")

    def interrupt():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        journal.execute_once(**arguments, after_reservation_fault_hook=interrupt)
    conflicting_receipt = replace(journal.read_receipt(), **{field: value})
    journal._write(conflicting_receipt)

    with pytest.raises(ProductError) as error:
        journal.execute_once(**arguments)
    assert error.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_JOURNAL_CONFLICT"
    assert journal.read_receipt() == conflicting_receipt


def test_schema_mirror_receipt_and_tamper_validation(tmp_path: Path) -> None:
    _, arguments = kwargs(tmp_path)
    receipt, _ = DurableSigningCeremonyJournal(tmp_path / "journal.json").execute_once(**arguments)
    payload = receipt.to_dict()
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)

    payload["automatic_replay_authorized"] = True
    with pytest.raises(ValueError):
        DurableSigningJournalReceipt.from_dict(payload)
    payload = receipt.to_dict()
    payload["unknown"] = "x"
    with pytest.raises(ValueError):
        DurableSigningJournalReceipt.from_dict(payload)


def test_alternate_path_and_deletion_are_explicitly_outside_replay_boundary(tmp_path: Path) -> None:
    values, arguments = kwargs(tmp_path)
    first = DurableSigningCeremonyJournal(tmp_path / "journal-a.json")
    second = DurableSigningCeremonyJournal(tmp_path / "journal-b.json")

    first_receipt, _ = first.execute_once(**arguments)
    after_first = values[1].decrypt_count
    second_receipt, _ = second.execute_once(**arguments)
    assert values[1].decrypt_count > after_first
    assert first_receipt.to_dict()["persistent_replay_prevention_present"] is False
    assert second_receipt.to_dict()["canonical_project_binding_present"] is False

    second.path.unlink()
    after_second = values[1].decrypt_count
    replayed_receipt, _ = second.execute_once(**arguments)
    assert values[1].decrypt_count > after_second
    assert replayed_receipt.to_dict()["journal_deletion_detection_present"] is False


def test_fully_forged_typed_success_has_no_public_injection_path(tmp_path: Path) -> None:
    values, arguments = kwargs(tmp_path)
    _, cipher, custody, request, _, _, confirmation, _, _ = values
    request_payload = request.to_dict()
    detached_sha = "sha256:" + "a" * 64
    verification = KnowledgePackSignatureVerificationReceipt(
        arguments["verification_receipt_id"],
        request.request_id,
        request_payload["signature_request_sha256"],
        request.signing_candidate_sha256,
        request.pack_id,
        request.pack_version,
        request.trusted_signer_policy_sha256,
        request.signer_key_id_sha256,
        request_payload["signature_message_sha256"],
        detached_sha,
    )
    ceremony = LocalSigningCeremonyReceipt(
        arguments["receipt_id"],
        confirmation.ceremony_id,
        custody.to_dict()["custody_receipt_sha256"],
        request_payload["signature_request_sha256"],
        custody.signer_key_id_sha256,
        detached_sha,
        verification.to_dict()["verification_receipt_sha256"],
        confirmation.to_dict()["confirmation_sha256"],
        arguments["completed_at_epoch_ms"],
    )
    forged = LocalSigningCeremonyResult(ceremony, verification)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")
    before = cipher.decrypt_count

    assert "ceremony_executor" not in inspect.signature(journal.execute_once).parameters
    with pytest.raises(TypeError, match="ceremony_executor"):
        journal.execute_once(**arguments, ceremony_executor=lambda **_: forged)
    assert cipher.decrypt_count == before
    assert not journal.path.exists()


def test_completed_time_type_is_rejected_before_journal_and_key_access(tmp_path: Path) -> None:
    values, arguments = kwargs(tmp_path)
    arguments["completed_at_epoch_ms"] = 301.5
    before = values[1].decrypt_count
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")

    with pytest.raises(ValueError, match="integer"):
        journal.execute_once(**arguments)
    assert values[1].decrypt_count == before
    assert not journal.path.exists()


def test_unknown_corrupt_and_symlink_journals_fail_closed(tmp_path: Path) -> None:
    journal_path = tmp_path / "journal.json"
    journal = DurableSigningCeremonyJournal(journal_path)
    journal_path.write_text('{"unknown":true}', encoding="utf-8")
    with pytest.raises(ProductError) as unknown:
        journal.read_receipt()
    assert unknown.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_JOURNAL_INTEGRITY"

    journal_path.write_bytes(b"not-json")
    with pytest.raises(ProductError) as corrupt:
        journal.read_receipt()
    assert corrupt.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_JOURNAL_INTEGRITY"

    journal_path.unlink()
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    try:
        journal_path.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ProductError) as symlink:
        journal.read_receipt()
    assert symlink.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_JOURNAL_INTEGRITY"

def test_reserve_write_failure_never_calls_fault_hook_or_key(tmp_path: Path) -> None:
    values, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")
    called = False

    def after_reservation() -> None:
        nonlocal called
        called = True

    def stop(stage: str, _: Path) -> None:
        if stage == "before_replace":
            raise RuntimeError("reserve write failure")

    before = values[1].decrypt_count
    with pytest.raises(RuntimeError, match="reserve write"):
        journal.execute_once(
            **arguments,
            reserve_failure_injector=stop,
            after_reservation_fault_hook=after_reservation,
        )
    assert called is False
    assert values[1].decrypt_count == before
    assert not journal.path.exists()


def test_actual_multiprocess_same_path_serializes_one_success(tmp_path: Path) -> None:
    _, arguments = kwargs(tmp_path)
    journal_path = str(tmp_path / "journal.json")
    context = mp.get_context("spawn")
    queue = context.Queue()
    processes = [
        context.Process(target=_multiprocess_execute, args=(queue, journal_path, arguments))
        for _ in range(2)
    ]
    started: list[mp.Process] = []
    try:
        for process in processes:
            process.start()
            started.append(process)
        for process in started:
            process.join(30)
        assert all(not process.is_alive() and process.exitcode == 0 for process in started)
        results = sorted(queue.get(timeout=5) for _ in started)
        assert results == [
            ("error", "ERR_KNOWLEDGE_PACK_SIGNING_ALREADY_FINAL"),
            ("success", "SIGNED_AND_VERIFIED"),
        ]
    finally:
        try:
            _cleanup_processes(started, join_timeout=0)
        finally:
            try:
                queue.close()
            finally:
                queue.join_thread()


def test_multiprocess_cleanup_helper_terminates_live_child() -> None:
    context = mp.get_context("spawn")
    process = context.Process(target=time.sleep, args=(30,))
    process.start()
    exitcodes: list[int | None] | None = None
    try:
        exitcodes = _cleanup_processes([process], join_timeout=0.01)
    finally:
        # Independent fallback: even a cleanup-helper regression must not leak
        # the deliberately live 30-second child or its Windows process handle.
        try:
            try:
                alive = process.is_alive()
            except ValueError:  # handle was already closed by the helper
                alive = False
            if alive:
                process.terminate()
                process.join(5)
                if process.is_alive():
                    process.kill()
                    process.join(5)
        finally:
            try:
                process.close()
            except ValueError:  # already closed
                pass
    assert exitcodes is not None and exitcodes[0] is not None