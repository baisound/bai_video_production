from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import inspect
import json
from pathlib import Path
from threading import Event, Thread

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator
import pytest

import ai_video_production.knowledge_pack_trusted_signature_admission as admission_module
from ai_video_production.knowledge_pack_promotion_intent import (
    compile_knowledge_pack_promotion_intent,
)
from ai_video_production.knowledge_pack_signature_verification import (
    TrustedSignerPolicy,
    TrustedSignerPolicyState,
)
from ai_video_production.knowledge_pack_trusted_signature_admission import (
    KnowledgePackTrustedSignatureAdmission,
    KnowledgePackTrustedSignatureAdmissionState,
    compile_knowledge_pack_trusted_signature_admission,
    verify_knowledge_pack_trusted_signature_admission,
)
from test_task029_knowledge_pack_promotion_intent import case as promotion_case


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "knowledge-pack-trusted-signature-admission.schema.json"
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


class CausalityBypassInt(int):
    def __lt__(self, other: object) -> bool:
        return False


class ExactValueStrSubclass(str):
    pass


def signed_case(tmp_path: Path):
    values, ceremony_arguments, journal, result, intent_arguments = promotion_case(
        tmp_path
    )
    intent = compile_knowledge_pack_promotion_intent(**intent_arguments)
    private_key = Ed25519PrivateKey.from_private_bytes(values[7])
    signature = private_key.sign(
        intent_arguments["signature_request_payload"][
            "signature_message_sha256"
        ].encode("ascii")
    )
    arguments = {
        "admission_id": "trusted-signature-admission.r10b",
        "promotion_intent_payload": intent.to_dict(),
        "promotion_intent_compile_kwargs": intent_arguments,
        "signing_ceremony_receipt_payload": result.receipt.to_dict(),
        "trusted_signer_policy_payload": ceremony_arguments[
            "trusted_signer_policy_payload"
        ],
        "public_key_bytes": values[8],
        "detached_signature_bytes": signature,
        "verified_at_epoch_ms": 500,
    }
    assert result.verification_receipt.detached_signature_sha256 == intent.detached_signature_sha256
    return values, ceremony_arguments, journal, result, intent, arguments


def test_trusted_r9a_reverification_returns_body_free_admission(
    tmp_path: Path,
) -> None:
    values, _, journal, result, intent, arguments = signed_case(tmp_path)
    admission = compile_knowledge_pack_trusted_signature_admission(**arguments)
    payload = admission.to_dict()

    assert admission.state is (
        KnowledgePackTrustedSignatureAdmissionState.READY_FOR_INITIAL_SIGNATURE_ARTIFACT_CUSTODY
    )
    assert payload["promotion_intent_sha256"] == intent.to_dict()[
        "promotion_intent_sha256"
    ]
    assert payload["verification_receipt_sha256"] == result.verification_receipt.to_dict()[
        "verification_receipt_sha256"
    ]
    assert payload["signing_journal_receipt_sha256"] == journal.to_dict()[
        "journal_receipt_sha256"
    ]
    assert payload["r9a_verifier_executed_in_current_call"] is True
    assert payload["verification_claim_reproduced_exactly"] is True
    assert (
        payload["cryptographic_signature_verified_against_supplied_policy"] is True
    )
    assert payload["canonical_signer_origin_authenticated"] is False
    assert payload["owner_signer_binding_confirmed"] is False
    assert payload["standalone_admission_payload_authoritative"] is False
    assert payload["promotion_confirmation_eligible"] is False

    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    assert values[7] not in raw
    assert values[8] not in raw
    assert arguments["detached_signature_bytes"] not in raw
    assert KnowledgePackTrustedSignatureAdmission.from_dict(payload) == admission
    verify_knowledge_pack_trusted_signature_admission(payload, **arguments)


def test_schema_and_package_mirror_accept_exact_projection(tmp_path: Path) -> None:
    payload = compile_knowledge_pack_trusted_signature_admission(
        **signed_case(tmp_path)[5]
    ).to_dict()
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_all_effects_and_remaining_gates_are_machine_readable(tmp_path: Path) -> None:
    payload = compile_knowledge_pack_trusted_signature_admission(
        **signed_case(tmp_path)[5]
    ).to_dict()
    for field in (
        "signature_artifact_custody_confirmed",
        "canonical_latest_source_revalidated",
        "canonical_trusted_signer_policy_revalidated",
        "canonical_signer_origin_authenticated",
        "owner_signer_binding_confirmed",
        "standalone_admission_payload_authoritative",
        "canonical_receipt_minted",
        "promotion_confirmation_eligible",
        "owner_scope_coordinates_included",
        "project_scope_coordinates_included",
        "reviewer_coordinates_included",
        "raw_media_included",
        "text_body_included",
        "absolute_host_path_included",
        "credential_included",
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
    for field in (
        "caller_supplied_source_graph_recompiled",
        "r9a_verifier_executed_in_current_call",
        "verification_claim_reproduced_exactly",
        "cryptographic_signature_verified_against_supplied_policy",
        "caller_supplied_signer_policy_self_validated",
        "signature_artifact_observed_during_verification",
        "direct_recompile_required_for_downstream",
        "explicit_human_promotion_confirmation_required",
        "canonical_store_transaction_required",
        "runtime_compatibility_validation_required",
        "signature_artifact_custody_required",
        "in_memory_admission_only",
    ):
        assert payload[field] is True


@pytest.mark.parametrize("target", ["signature", "public_key", "policy", "intent"])
def test_tamper_fails_before_admission(tmp_path: Path, target: str) -> None:
    _, _, _, _, _, arguments = signed_case(tmp_path)
    changed = dict(arguments)
    if target == "signature":
        signature = changed["detached_signature_bytes"]
        changed["detached_signature_bytes"] = bytes([signature[0] ^ 1]) + signature[1:]
    elif target == "public_key":
        public_key = changed["public_key_bytes"]
        changed["public_key_bytes"] = bytes([public_key[0] ^ 1]) + public_key[1:]
    elif target == "policy":
        policy = dict(changed["trusted_signer_policy_payload"])
        policy["policy_id"] = "different-policy"
        changed["trusted_signer_policy_payload"] = policy
    else:
        intent = dict(changed["promotion_intent_payload"])
        intent["pack_version"] = "9.9.9"
        changed["promotion_intent_payload"] = intent
    with pytest.raises(ValueError):
        compile_knowledge_pack_trusted_signature_admission(**changed)


def test_forged_constructible_receipt_cannot_replace_journal_claim(
    tmp_path: Path,
) -> None:
    _, _, _, result, _, arguments = signed_case(tmp_path)
    forged = replace(result.verification_receipt, receipt_id="forged.receipt")
    compile_kwargs = dict(arguments["promotion_intent_compile_kwargs"])
    compile_kwargs["verification_receipt_payload"] = forged.to_dict()
    with pytest.raises(ValueError, match="verification receipt"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, promotion_intent_compile_kwargs=compile_kwargs)
        )


def test_revoked_policy_and_byte_subclasses_fail_closed(tmp_path: Path) -> None:
    _, _, _, _, _, arguments = signed_case(tmp_path)
    policy = TrustedSignerPolicy.from_dict(arguments["trusted_signer_policy_payload"])
    revoked = replace(policy, state=TrustedSignerPolicyState.REVOKED)
    with pytest.raises(ValueError, match="not active"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, trusted_signer_policy_payload=revoked.to_dict())
        )
    with pytest.raises(ValueError, match="exact bytes"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, public_key_bytes=bytearray(arguments["public_key_bytes"]))
        )


@pytest.mark.parametrize("field", ["promotion_intent_payload", "trusted_signer_policy_payload"])
def test_stateful_mappings_are_rejected_without_hook_reads(
    tmp_path: Path, field: str
) -> None:
    _, _, _, _, _, arguments = signed_case(tmp_path)
    first = dict(arguments[field])
    second = dict(first)
    second[next(iter(second))] = "mutated"
    chameleon = ChameleonMapping(first, second)
    with pytest.raises(ValueError, match="exact built-in dict"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, **{field: chameleon})
        )
    assert chameleon.read_count == 0


def test_nested_stateful_compile_mapping_is_rejected_without_hook_reads(
    tmp_path: Path,
) -> None:
    _, _, _, _, _, arguments = signed_case(tmp_path)
    compile_kwargs = dict(arguments["promotion_intent_compile_kwargs"])
    request_compile_kwargs = dict(compile_kwargs["signature_request_compile_kwargs"])
    first = dict(request_compile_kwargs["signing_candidate_compile_kwargs"])
    second = dict(first, pack_version="9.9.9")
    chameleon = ChameleonMapping(first, second)
    request_compile_kwargs["signing_candidate_compile_kwargs"] = chameleon
    compile_kwargs["signature_request_compile_kwargs"] = request_compile_kwargs

    with pytest.raises(ValueError, match="exact TASK-029"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, promotion_intent_compile_kwargs=compile_kwargs)
        )
    assert chameleon.read_count == 0

    cycle: dict[str, object] = {}
    cycle["self"] = cycle
    request_compile_kwargs["source_signing_candidate_payload"] = cycle
    request_compile_kwargs["signing_candidate_compile_kwargs"] = first
    with pytest.raises(ValueError, match="must not be cyclic"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, promotion_intent_compile_kwargs=compile_kwargs)
        )


def test_concurrent_request_mutation_cannot_switch_verified_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _, _, _, arguments = signed_case(tmp_path)
    compile_kwargs = dict(arguments["promotion_intent_compile_kwargs"])
    original = dict(compile_kwargs["signature_request_payload"])
    live = dict(original)
    compile_kwargs["signature_request_payload"] = live
    request_compile_kwargs = dict(compile_kwargs["signature_request_compile_kwargs"])
    original_candidate = dict(request_compile_kwargs["source_signing_candidate_payload"])
    live_candidate = dict(original_candidate)
    request_compile_kwargs["source_signing_candidate_payload"] = live_candidate
    compile_kwargs["signature_request_compile_kwargs"] = request_compile_kwargs
    verifier_entered = Event()
    mutation_done = Event()
    trusted_verifier = admission_module.verify_detached_knowledge_pack_signature

    def blocking_verifier(**kwargs):
        verifier_entered.set()
        assert mutation_done.wait(5)
        return trusted_verifier(**kwargs)

    def mutate() -> None:
        assert verifier_entered.wait(5)
        live.clear()
        live.update(dict(original, pack_version="9.9.9"))
        live_candidate.clear()
        live_candidate.update(dict(original_candidate, pack_version="9.9.9"))
        mutation_done.set()

    monkeypatch.setattr(
        admission_module, "verify_detached_knowledge_pack_signature", blocking_verifier
    )
    worker = Thread(target=mutate)
    worker.start()
    try:
        admission = compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, promotion_intent_compile_kwargs=compile_kwargs)
        )
    finally:
        worker.join(5)
    assert not worker.is_alive()
    assert live["pack_version"] == "9.9.9"
    assert live_candidate["pack_version"] == "9.9.9"
    assert admission.pack_version == original["pack_version"]
    assert admission.signature_request_sha256 == original["signature_request_sha256"]


def test_projection_tamper_unknown_fields_and_bool_time_fail_closed(
    tmp_path: Path,
) -> None:
    arguments = signed_case(tmp_path)[5]
    payload = compile_knowledge_pack_trusted_signature_admission(**arguments).to_dict()
    for field, value in (
        ("promotion_confirmation_eligible", True),
        ("standalone_admission_payload_authoritative", True),
        ("trusted_signature_admission_sha256", "sha256:" + "0" * 64),
    ):
        with pytest.raises(ValueError):
            KnowledgePackTrustedSignatureAdmission.from_dict(
                dict(payload, **{field: value})
            )
    with pytest.raises(ValueError, match="incomplete or unknown"):
        KnowledgePackTrustedSignatureAdmission.from_dict(
            dict(payload, unexpected=True)
        )
    with pytest.raises(ValueError, match="integer"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, verified_at_epoch_ms=True)
        )
    with pytest.raises(ValueError, match="integer"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, verified_at_epoch_ms=CausalityBypassInt(1))
        )
    with pytest.raises(ValueError, match="precedes signed Evidence"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, verified_at_epoch_ms=399)
        )
    with pytest.raises(ValueError, match="stable identifier"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(
                arguments,
                admission_id=ExactValueStrSubclass(
                    arguments["admission_id"]
                ),
            )
        )

    compile_kwargs = dict(arguments["promotion_intent_compile_kwargs"])
    compile_kwargs["intent_id"] = ExactValueStrSubclass(compile_kwargs["intent_id"])
    with pytest.raises(ValueError, match="stable identifier"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, promotion_intent_compile_kwargs=compile_kwargs)
        )

    compile_kwargs = dict(arguments["promotion_intent_compile_kwargs"])
    compile_kwargs["created_at_epoch_ms"] = CausalityBypassInt(
        compile_kwargs["created_at_epoch_ms"]
    )
    with pytest.raises(ValueError, match="integer"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(arguments, promotion_intent_compile_kwargs=compile_kwargs)
        )


def test_verification_time_must_follow_journal_and_ceremony(tmp_path: Path) -> None:
    arguments = signed_case(tmp_path)[5]
    compile_kwargs = dict(arguments["promotion_intent_compile_kwargs"])
    compile_kwargs["created_at_epoch_ms"] = 1
    early_intent = compile_knowledge_pack_promotion_intent(**compile_kwargs)
    with pytest.raises(ValueError, match="precedes signed Evidence"):
        compile_knowledge_pack_trusted_signature_admission(
            **dict(
                arguments,
                promotion_intent_payload=early_intent.to_dict(),
                promotion_intent_compile_kwargs=compile_kwargs,
                verified_at_epoch_ms=300,
            )
        )


@pytest.mark.parametrize("surface", ["from_dict", "verify"])
def test_public_admission_surfaces_reject_stateful_mapping_without_reads(
    tmp_path: Path, surface: str
) -> None:
    arguments = signed_case(tmp_path)[5]
    payload = compile_knowledge_pack_trusted_signature_admission(
        **arguments
    ).to_dict()
    chameleon = ChameleonMapping(payload, dict(payload, admission_id="mutated"))
    with pytest.raises(ValueError, match="exact built-in dict"):
        if surface == "from_dict":
            KnowledgePackTrustedSignatureAdmission.from_dict(chameleon)
        else:
            verify_knowledge_pack_trusted_signature_admission(
                chameleon, **arguments
            )
    assert chameleon.read_count == 0


def test_replacement_state_requires_exact_predecessor_rollback() -> None:
    base = KnowledgePackTrustedSignatureAdmission(
        admission_id="admission",
        promotion_intent_id="intent",
        promotion_intent_sha256="sha256:" + "0" * 64,
        pack_id="pack",
        pack_version="1.0.0",
        predecessor_pack_sha256=None,
        rollback_target_pack_sha256=None,
        signing_candidate_sha256="sha256:" + "1" * 64,
        signature_request_sha256="sha256:" + "2" * 64,
        signature_message_sha256="sha256:" + "3" * 64,
        trusted_signer_policy_sha256="sha256:" + "4" * 64,
        signer_key_id_sha256="sha256:" + "5" * 64,
        detached_signature_sha256="sha256:" + "6" * 64,
        verification_receipt_sha256="sha256:" + "7" * 64,
        signing_journal_receipt_sha256="sha256:" + "8" * 64,
        signing_ceremony_receipt_sha256="sha256:" + "9" * 64,
        verified_at_epoch_ms=1,
        state=KnowledgePackTrustedSignatureAdmissionState.READY_FOR_INITIAL_SIGNATURE_ARTIFACT_CUSTODY,
    )
    predecessor = "sha256:" + "a" * 64
    replacement = replace(
        base,
        predecessor_pack_sha256=predecessor,
        rollback_target_pack_sha256=predecessor,
        state=KnowledgePackTrustedSignatureAdmissionState.READY_FOR_REPLACEMENT_SIGNATURE_ARTIFACT_CUSTODY,
    )
    assert replacement.to_dict()["rollback_plan_required"] is True
    with pytest.raises(ValueError, match="stable identifier"):
        replace(base, admission_id=ExactValueStrSubclass(base.admission_id))
    with pytest.raises(ValueError, match="sha256"):
        replace(
            base,
            signer_key_id_sha256=ExactValueStrSubclass(
                base.signer_key_id_sha256
            ),
        )
    with pytest.raises(ValueError, match="semantic version"):
        replace(base, pack_version=ExactValueStrSubclass(base.pack_version))
    with pytest.raises(ValueError, match="rollback target"):
        replace(replacement, rollback_target_pack_sha256="sha256:" + "b" * 64)


def test_module_has_no_io_private_signing_or_persisted_artifact_surface() -> None:
    source = inspect.getsource(admission_module)
    assert "open(" not in source
    assert "Path" not in source
    assert "Ed25519PrivateKey" not in source
    assert "private_bytes" not in source
    assert "generate(" not in source
    fields = KnowledgePackTrustedSignatureAdmission.__dataclass_fields__
    assert "public_key_bytes" not in fields
    assert "detached_signature_bytes" not in fields
    assert "private_key_bytes" not in fields
