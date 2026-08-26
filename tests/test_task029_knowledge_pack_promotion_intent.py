from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import inspect
import json
from pathlib import Path
from threading import Event, Thread

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.knowledge_pack_durable_signing_journal import (
    DurableSigningCeremonyJournal,
    DurableSigningJournalState,
)
from ai_video_production.knowledge_pack_promotion_intent import (
    KnowledgePackPromotionIntent,
    KnowledgePackPromotionIntentState,
    compile_knowledge_pack_promotion_intent,
    verify_knowledge_pack_promotion_intent,
)
from test_task029_knowledge_pack_durable_signing_journal import kwargs as signing_kwargs


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "knowledge-pack-promotion-intent.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name


class ChameleonMapping(Mapping[str, object]):
    def __init__(self, first: dict[str, object], second: dict[str, object]) -> None:
        self.first = first
        self.second = second
        self.read_count = 0

    def _current(self) -> dict[str, object]:
        self.read_count += 1
        return self.first if self.read_count == 1 else self.second

    def __getitem__(self, key: str) -> object:
        return self._current()[key]

    def __iter__(self):
        return iter(self._current())

    def __len__(self) -> int:
        return len(self._current())


class BlockingCompileKwargs(Mapping[str, object]):
    def __init__(
        self,
        values: Mapping[str, object],
        snapshot_taken: Event,
        mutation_done: Event,
    ) -> None:
        self.values = dict(values)
        self.snapshot_taken = snapshot_taken
        self.mutation_done = mutation_done
        self.signalled = False

    def __getitem__(self, key: str) -> object:
        return self.values[key]

    def __iter__(self):
        if not self.signalled:
            self.signalled = True
            self.snapshot_taken.set()
            assert self.mutation_done.wait(5)
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)


def case(tmp_path: Path):
    values, ceremony_arguments = signing_kwargs(tmp_path / "signed")
    journal_receipt, result = DurableSigningCeremonyJournal(
        tmp_path / "journal.json"
    ).execute_once(**ceremony_arguments)
    arguments = {
        "intent_id": "promotion-intent.r10a",
        "signature_request_payload": ceremony_arguments["signature_request_payload"],
        "signature_request_compile_kwargs": ceremony_arguments[
            "signature_request_compile_kwargs"
        ],
        "verification_receipt_payload": result.verification_receipt.to_dict(),
        "signing_journal_receipt_payload": journal_receipt.to_dict(),
        "created_at_epoch_ms": 400,
    }
    return values, ceremony_arguments, journal_receipt, result, arguments


def test_exact_r6_through_r9d_evidence_compiles_body_free_intent(tmp_path: Path) -> None:
    values, _, journal, result, arguments = case(tmp_path)
    intent = compile_knowledge_pack_promotion_intent(**arguments)
    payload = intent.to_dict()

    assert intent.state is KnowledgePackPromotionIntentState.READY_FOR_INITIAL_PROMOTION_PREFLIGHT
    assert payload["predecessor_pack_sha256"] is None
    assert payload["rollback_target_pack_sha256"] is None
    assert payload["rollback_plan_required"] is False
    assert payload["upstream_signature_verification_claim_present"] is True
    assert payload["signature_origin_authenticated"] is False
    assert payload["signature_verified"] is False
    assert payload["promotion_confirmation_eligible"] is False
    assert payload["signature_artifact_present"] is False
    assert payload["promotion_execution_blocked_until_signature_artifact"] is True
    assert payload["verification_receipt_sha256"] == result.verification_receipt.to_dict()[
        "verification_receipt_sha256"
    ]
    assert payload["signing_journal_receipt_sha256"] == journal.to_dict()[
        "journal_receipt_sha256"
    ]
    assert payload["signing_ceremony_receipt_sha256"] == journal.ceremony_receipt_sha256

    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    assert values[7] not in raw
    assert values[8] not in raw
    assert KnowledgePackPromotionIntent.from_dict(payload) == intent
    verify_knowledge_pack_promotion_intent(payload, **arguments)


def test_schema_and_package_mirror_accept_exact_projection(tmp_path: Path) -> None:
    payload = compile_knowledge_pack_promotion_intent(**case(tmp_path)[4]).to_dict()
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(payload)


def test_every_effect_flag_remains_false_and_future_gates_are_explicit(tmp_path: Path) -> None:
    payload = compile_knowledge_pack_promotion_intent(**case(tmp_path)[4]).to_dict()
    for field in (
        "owner_scope_coordinates_included",
        "project_scope_coordinates_included",
        "reviewer_coordinates_included",
        "raw_media_included",
        "text_body_included",
        "signature_origin_authenticated",
        "signature_verified",
        "promotion_confirmation_eligible",
        "absolute_host_path_included",
        "credential_included",
        "signature_bytes_included",
        "public_key_material_included",
        "private_key_material_included",
        "signature_artifact_present",
        "knowledge_pack_write_authorized",
        "knowledge_pack_promotion_authorized",
        "automatic_promotion_authorized",
        "runtime_profile_apply_authorized",
        "rollback_execution_authorized",
        "release_authorized",
        "external_effect_authorized",
    ):
        assert payload[field] is False
    for field in (
        "latest_source_revalidated",
        "upstream_signature_verification_claim_present",
        "explicit_human_promotion_confirmation_required",
        "canonical_store_transaction_required",
        "runtime_compatibility_validation_required",
        "signature_artifact_required",
        "promotion_execution_blocked_until_signature_artifact",
        "in_memory_intent_only",
    ):
        assert payload[field] is True


def test_exact_source_recompile_drift_is_rejected_before_projection(tmp_path: Path) -> None:
    _, _, _, _, arguments = case(tmp_path)
    drifted = dict(arguments)
    request_payload = dict(drifted["signature_request_payload"])
    request_payload["pack_version"] = "9.9.9"
    drifted["signature_request_payload"] = request_payload
    with pytest.raises(ValueError, match="exact current sources"):
        compile_knowledge_pack_promotion_intent(**drifted)


def test_stateful_mapping_is_rejected_without_invoking_mapping_hooks(
    tmp_path: Path,
) -> None:
    _, _, _, _, arguments = case(tmp_path)
    first = dict(arguments["signature_request_payload"])
    second = dict(first, pack_version="9.9.9")
    chameleon = ChameleonMapping(first, second)

    with pytest.raises(ValueError, match="exact built-in dict"):
        compile_knowledge_pack_promotion_intent(
            **dict(arguments, signature_request_payload=chameleon)
        )
    assert chameleon.read_count == 0


def test_concurrent_mutation_cannot_change_the_frozen_request_snapshot(
    tmp_path: Path,
) -> None:
    _, _, _, _, arguments = case(tmp_path)
    original = dict(arguments["signature_request_payload"])
    live = dict(original)
    snapshot_taken = Event()
    mutation_done = Event()

    def mutate_original() -> None:
        assert snapshot_taken.wait(5)
        live.clear()
        live.update(dict(original, pack_version="9.9.9"))
        mutation_done.set()

    worker = Thread(target=mutate_original)
    worker.start()
    try:
        intent = compile_knowledge_pack_promotion_intent(
            **dict(
                arguments,
                signature_request_payload=live,
                signature_request_compile_kwargs=BlockingCompileKwargs(
                    arguments["signature_request_compile_kwargs"],
                    snapshot_taken,
                    mutation_done,
                ),
            )
        )
    finally:
        worker.join(5)
    assert not worker.is_alive()
    assert live["pack_version"] == "9.9.9"
    assert intent.pack_version == original["pack_version"]
    assert intent.to_dict()["signature_request_sha256"] == original[
        "signature_request_sha256"
    ]
    assert intent.to_dict()["latest_source_revalidated"] is True




def test_forged_typed_verification_receipt_is_cross_bound_and_rejected(tmp_path: Path) -> None:
    _, _, _, result, arguments = case(tmp_path)
    forged = replace(result.verification_receipt, pack_id="different-pack")
    drifted = dict(arguments, verification_receipt_payload=forged.to_dict())
    with pytest.raises(ValueError, match="does not bind the exact request"):
        compile_knowledge_pack_promotion_intent(**drifted)


def test_nonterminal_or_mismatched_journal_is_rejected(tmp_path: Path) -> None:
    _, _, journal, _, arguments = case(tmp_path)
    nonterminal = replace(
        journal,
        state=DurableSigningJournalState.RECOVERY_REQUIRED,
        ceremony_receipt_sha256=None,
        verification_receipt_sha256=None,
    )
    with pytest.raises(ValueError, match="not terminal"):
        compile_knowledge_pack_promotion_intent(
            **dict(arguments, signing_journal_receipt_payload=nonterminal.to_dict())
        )

    mismatched = replace(
        journal,
        verification_receipt_sha256="sha256:" + "f" * 64,
    )
    with pytest.raises(ValueError, match="exact verification receipt"):
        compile_knowledge_pack_promotion_intent(
            **dict(arguments, signing_journal_receipt_payload=mismatched.to_dict())
        )


def test_projection_tamper_unknown_fields_and_bool_timestamp_fail_closed(tmp_path: Path) -> None:
    arguments = case(tmp_path)[4]
    payload = compile_knowledge_pack_promotion_intent(**arguments).to_dict()

    for field, value in (
        ("knowledge_pack_promotion_authorized", True),
        ("signature_artifact_present", True),
        ("promotion_intent_sha256", "sha256:" + "0" * 64),
    ):
        tampered = dict(payload, **{field: value})
        with pytest.raises(ValueError):
            KnowledgePackPromotionIntent.from_dict(tampered)

    with pytest.raises(ValueError, match="incomplete or unknown"):
        KnowledgePackPromotionIntent.from_dict(dict(payload, unexpected=True))
    with pytest.raises(ValueError, match="integer"):
        compile_knowledge_pack_promotion_intent(
            **dict(arguments, created_at_epoch_ms=True)
        )


def test_replacement_state_requires_exact_predecessor_as_rollback_target(tmp_path: Path) -> None:
    initial = compile_knowledge_pack_promotion_intent(**case(tmp_path)[4])
    predecessor = "sha256:" + "a" * 64
    replacement = replace(
        initial,
        predecessor_pack_sha256=predecessor,
        rollback_target_pack_sha256=predecessor,
        state=KnowledgePackPromotionIntentState.READY_FOR_REPLACEMENT_PROMOTION_PREFLIGHT,
    )
    assert replacement.to_dict()["rollback_plan_required"] is True
    with pytest.raises(ValueError, match="rollback target"):
        replace(replacement, rollback_target_pack_sha256="sha256:" + "b" * 64)
    with pytest.raises(ValueError, match="state"):
        replace(
            replacement,
            state=KnowledgePackPromotionIntentState.READY_FOR_INITIAL_PROMOTION_PREFLIGHT,
        )


def test_module_has_no_io_or_cryptographic_execution_surface() -> None:
    import ai_video_production.knowledge_pack_promotion_intent as module

    source = inspect.getsource(module)
    assert "open(" not in source
    assert "Path" not in source
    assert "cryptography" not in source
    signature = inspect.signature(compile_knowledge_pack_promotion_intent)
    assert "public_key_bytes" not in signature.parameters
    assert "private_key_bytes" not in signature.parameters
    assert "detached_signature_bytes" not in signature.parameters
