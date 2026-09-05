from __future__ import annotations

import copy
import json
import pickle
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ai_video_production.human_authorization import (
    HUMAN_BROKER_CORE_FIXTURE_V1,
    HumanAction,
    decode_effect_zero_fixture_json,
    project_fixture_chain_for_audit,
    project_human_action_for_audit,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "task071"
SCHEMAS = ROOT / "schemas"
RESOURCE_SCHEMAS = ROOT / "src" / "ai_video_production" / "schema_resources"
SCHEMA_NAMES = (
    "human-authorization-reservation.schema.json",
    "human-authorization-decision-event.schema.json",
    "human-authorization-audit-receipt.schema.json",
)


def _schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _canonical_sha256(document: dict[str, object]) -> str:
    encoded = json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def test_closed_action_catalog_and_every_projection_are_effect_zero() -> None:
    assert [action.value for action in HumanAction] == [
        "PREFERENCE_PROMOTE",
        "PREFERENCE_ROLLBACK",
        "CONNECTOR_ACTIVATE",
        "CONNECTOR_DEACTIVATE",
    ]
    for action in HumanAction:
        projection = dict(project_human_action_for_audit(action))
        assert projection["fixture_version"] == HUMAN_BROKER_CORE_FIXTURE_V1
        assert projection["action"] == action.value
        assert projection["authority_created"] is False
        assert projection["effect_performed"] is False
        assert projection["native_user_presence_verified"] is False


@pytest.mark.parametrize("forged", ["PREFERENCE_PROMOTE", object(), 1])
def test_public_values_cannot_select_an_action_or_create_authority(forged: object) -> None:
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        project_human_action_for_audit(forged)  # type: ignore[arg-type]


def test_projection_copy_pickle_and_reconstruction_remain_data_only() -> None:
    projection = dict(project_human_action_for_audit(HumanAction.CONNECTOR_ACTIVATE))
    for variant in (
        copy.copy(projection),
        copy.deepcopy(projection),
        pickle.loads(pickle.dumps(projection)),
        dict(projection),
    ):
        assert variant["authority_created"] is False
        assert variant["effect_performed"] is False
        assert "ticket" not in variant
        assert "capability" not in variant


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b'{"a":1e309}',
        b'{"a":-1e309}',
        b'\xef\xbb\xbf{"a":1}',
        b'{"a":1} trailing',
        b'{"a":"bad\x01control"}',
        b'{"a":"\\ud800"}',
        b'{"a":"\\udc00"}',
        b'{"\\ud800":1}',
        b'["not-an-object"]',
    ],
)
def test_strict_fixture_decoder_rejects_ambiguous_or_non_object_json(raw: bytes) -> None:
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        decode_effect_zero_fixture_json(raw)


def test_strict_fixture_decoder_rejects_non_utf8_string() -> None:
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        decode_effect_zero_fixture_json("\ud800")


def test_strict_fixture_decoder_rejects_duplicate_fixture_and_freezes_valid_input() -> None:
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        decode_effect_zero_fixture_json((FIXTURES / "invalid-duplicate-key.json").read_bytes())
    decoded = decode_effect_zero_fixture_json((FIXTURES / "valid-reservation.json").read_bytes())
    assert decoded["authority_created"] is False
    assert decoded["effect_performed"] is False
    with pytest.raises(TypeError):
        decoded["authority_created"] = True  # type: ignore[index]


def test_schema_resource_mirrors_are_byte_identical_and_valid() -> None:
    for name in SCHEMA_NAMES:
        root_bytes = (SCHEMAS / name).read_bytes()
        assert root_bytes == (RESOURCE_SCHEMAS / name).read_bytes()
        Draft202012Validator.check_schema(json.loads(root_bytes))


def test_valid_public_fixtures_validate_but_remain_effect_zero() -> None:
    reservation = _fixture("valid-reservation.json")
    decision = _fixture("valid-decision-event.json")
    _validator("human-authorization-reservation.schema.json").validate(reservation)
    _validator("human-authorization-decision-event.schema.json").validate(decision)
    for document in (reservation, decision):
        assert document["authority_created"] is False
        assert document["effect_performed"] is False
        assert document["native_user_presence_verified"] is False


def test_fixture_chain_rejects_cross_action_or_expiry_and_is_replay_safe_data_only() -> None:
    reservation = _fixture("valid-reservation.json")
    decision = _fixture("valid-decision-event.json")
    audit = {
        "schema_version": "1.0.0",
        "record_kind": "HUMAN_AUTHORIZATION_AUDIT_RECEIPT_V1",
        "audit_receipt_id": "harc-0123456789abcdef0123456789abcdef",
        "reservation_id": reservation["reservation_id"],
        "reservation_sha256": _canonical_sha256(reservation),
        "decision_event_id": decision["decision_event_id"],
        "decision_event_sha256": _canonical_sha256(decision),
        "action": reservation["action"],
        "outcome": "AUDIT_ONLY",
        "authority_created": False,
        "effect_performed": False,
        "native_user_presence_verified": False,
    }
    _validator("human-authorization-audit-receipt.schema.json").validate(audit)
    first = project_fixture_chain_for_audit(reservation, decision, audit)
    assert first == project_fixture_chain_for_audit(reservation, decision, audit)
    assert dict(first)["effect_performed"] is False
    cross_action = dict(decision)
    cross_action["action"] = "CONNECTOR_ACTIVATE"
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        project_fixture_chain_for_audit(reservation, cross_action, audit)
    expired = dict(decision)
    expired["occurred_at"] = "2026-09-05T00:06:00Z"
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        project_fixture_chain_for_audit(reservation, expired, audit)
    offset_time = dict(decision)
    offset_time["occurred_at"] = "2026-09-05T00:04:59-01:00"
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        project_fixture_chain_for_audit(reservation, offset_time, audit)
    replay_bypass = dict(decision)
    replay_bypass["replay_attempt"] = True
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        project_fixture_chain_for_audit(reservation, replay_bypass, audit)
    missing_audit_field = dict(audit)
    del missing_audit_field["decision_event_sha256"]
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        project_fixture_chain_for_audit(reservation, decision, missing_audit_field)
    digest_mismatch = dict(decision)
    digest_mismatch["reservation_sha256"] = "sha256:" + "d" * 64
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        project_fixture_chain_for_audit(reservation, digest_mismatch, audit)
    type_forged = dict(decision)
    type_forged["action"] = ["PREFERENCE_PROMOTE"]
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        project_fixture_chain_for_audit(reservation, type_forged, audit)
    decision_type_forged = dict(decision)
    decision_type_forged["decision"] = ["AUDIT_ONLY"]
    with pytest.raises(ValueError, match="REJECTED_EFFECT0"):
        project_fixture_chain_for_audit(reservation, decision_type_forged, audit)


def test_unknown_cross_action_replay_expiry_and_effect_flags_are_schema_rejected() -> None:
    decision_validator = _validator("human-authorization-decision-event.schema.json")
    invalid_replay = _fixture("invalid-replay.json")
    with pytest.raises(ValidationError):
        decision_validator.validate(invalid_replay)
    valid = _fixture("valid-decision-event.json")
    for field, value in (
        ("action", "UNKNOWN"),
        ("decision", "VERIFIED"),
        ("authority_created", True),
        ("effect_performed", True),
        ("native_user_presence_verified", True),
    ):
        changed = dict(valid)
        changed[field] = value
        with pytest.raises(ValidationError):
            decision_validator.validate(changed)
    newline_identifier = dict(valid)
    newline_identifier["decision_event_id"] += "\n"
    with pytest.raises(ValidationError):
        decision_validator.validate(newline_identifier)
    expired = dict(valid)
    expired["decision"] = "EXPIRED"
    decision_validator.validate(expired)


def test_concurrent_safe_projection_has_no_ticket_or_runtime_factory() -> None:
    with ThreadPoolExecutor(max_workers=8) as executor:
        projections = list(
            executor.map(
                lambda _: project_human_action_for_audit(HumanAction.PREFERENCE_ROLLBACK),
                range(128),
            )
        )
    assert len(set(projections)) == 1
    assert all(dict(projection)["authority_created"] is False for projection in projections)
    exported = set(__import__("ai_video_production.human_authorization", fromlist=["*"]).__all__)
    assert exported == {
        "HUMAN_ACTION_ABI_V1",
        "HUMAN_BROKER_CORE_FIXTURE_V1",
        "HUMAN_DISPLAY_PROJECTION_V1",
        "HumanAction",
        "decode_effect_zero_fixture_json",
        "project_fixture_chain_for_audit",
        "project_human_action_for_audit",
    }
