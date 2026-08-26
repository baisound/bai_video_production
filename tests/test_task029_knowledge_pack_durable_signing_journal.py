from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.errors import ProductError
from ai_video_production.knowledge_pack_durable_signing_journal import (
    DurableSigningCeremonyJournal,
    DurableSigningJournalReceipt,
    DurableSigningJournalState,
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


def test_exact_ceremony_is_reserved_then_committed_body_free(tmp_path: Path) -> None:
    values, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")
    receipt, result = journal.execute_once(**arguments)
    payload = receipt.to_dict()

    assert receipt.state is DurableSigningJournalState.SIGNED_AND_VERIFIED
    assert payload["persistent_replay_prevention_present"] is True
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

    def fail(**_: object):
        raise RuntimeError("synthetic failure")

    with pytest.raises(ProductError) as error:
        journal.execute_once(**arguments, ceremony_executor=fail)
    assert error.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_RECOVERY_REQUIRED"
    assert journal.read_receipt().state is DurableSigningJournalState.RECOVERY_REQUIRED

    called = False

    def must_not_run(**_: object):
        nonlocal called
        called = True
        raise AssertionError("must not execute")

    with pytest.raises(ProductError) as duplicate:
        journal.execute_once(**arguments, ceremony_executor=must_not_run)
    assert duplicate.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_ALREADY_FINAL"
    assert called is False


def test_process_interruption_leaves_reservation_then_recovers_without_replay(tmp_path: Path) -> None:
    _, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")

    def interrupt(**_: object):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        journal.execute_once(**arguments, ceremony_executor=interrupt)
    assert journal.read_receipt().state is DurableSigningJournalState.SIGNING_RESERVED

    called = False

    def must_not_run(**_: object):
        nonlocal called
        called = True
        raise AssertionError("must not execute")

    retry = dict(arguments)
    retry["recovery_observed_at_epoch_ms"] = 400
    with pytest.raises(ProductError) as error:
        journal.execute_once(**retry, ceremony_executor=must_not_run)
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


def test_current_custody_drift_fails_before_reservation(tmp_path: Path) -> None:
    _, arguments = kwargs(tmp_path)
    other = case(tmp_path / "other")

    class DriftedCustodyStore:
        def read_receipt(self):
            return other[2]

    arguments["custody_store"] = DriftedCustodyStore()
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")
    with pytest.raises(ValueError, match="current encrypted custody"):
        journal.execute_once(**arguments)
    assert not (tmp_path / "journal.json").exists()


def test_conflicting_request_cannot_mutate_interrupted_reservation(tmp_path: Path) -> None:
    _, arguments = kwargs(tmp_path)
    journal = DurableSigningCeremonyJournal(tmp_path / "journal.json")

    def interrupt(**_: object):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        journal.execute_once(**arguments, ceremony_executor=interrupt)
    reserved = journal.read_receipt()

    conflicting = dict(arguments)
    conflicting["journal_id"] = "journal.other"
    with pytest.raises(ProductError) as error:
        journal.execute_once(**conflicting)
    assert error.value.code == "ERR_KNOWLEDGE_PACK_SIGNING_JOURNAL_CONFLICT"
    assert journal.read_receipt() == reserved


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
