from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import pickle
import re
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "src" / "ai_video_production"
if "ai_video_production" not in sys.modules:
    package = types.ModuleType("ai_video_production")
    package.__path__ = [str(PACKAGE_DIR)]  # type: ignore[attr-defined]
    sys.modules["ai_video_production"] = package

import ai_video_production.product_operation_broker as broker


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64


def _bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _status_body(*, state: str = "REQUESTED", stable_code: str | None = None) -> dict[str, object]:
    terminal = state in {
        "COMMITTED",
        "REJECTED",
        "BURNED",
        "BURNED_UNKNOWN",
        "BURNED_BY_SESSION_MISMATCH",
    }
    body: dict[str, object] = {
        "authority_created": False,
        "committed": state == "COMMITTED",
        "durable_state": state,
        "effect_confirmed": state == "COMMITTED",
        "message_type": "BvpProductOperationTerminalStatus",
        "operation_commitment_sha256": SHA_A,
        "schema_version": "1.0.0",
        "stable_code": stable_code,
        "terminal": terminal,
    }
    return {**body, "status_sha256": broker._sha256_json(body)}


def _authorization_body() -> dict[str, object]:
    body: dict[str, object] = {
        "action_profile": "INSTALL_AUTHORITY_PAIR_WRITE",
        "authority_created": False,
        "message_type": "BvpProductOperationAuthorizationResolution",
        "request_id": "request-fixture",
        "reservation_created": False,
        "resolution": "NOT_CONFIRMED",
        "schema_version": "1.0.0",
        "stable_code": "TASK072_AUTHORIZATION_NC",
        "ticket_created": False,
    }
    return {**body, "resolution_sha256": broker._sha256_json(body)}


def _receipt_body() -> dict[str, object]:
    body: dict[str, object] = {
        "action_profile": "INSTALL_AUTHORITY_PAIR_WRITE",
        "authority_created": False,
        "config_commitment_sha256": SHA_D,
        "consumer_effect_observed": True,
        "downstream_receipt_count": 1,
        "event_commitment_sha256": SHA_C,
        "event_revision": 1,
        "event_utc": "2026-09-03T12:30:01Z",
        "message_type": "BvpProductOperationAuditReceipt",
        "operation_commitment_sha256": SHA_A,
        "result_sha256": SHA_E,
        "schema_version": "1.0.0",
        "stable_code": None,
        "terminal_state": "COMMITTED",
        "ticket_commitment_sha256": SHA_B,
        "upstream_receipt_count": 2,
    }
    return {**body, "receipt_sha256": broker._sha256_json(body)}


def test_public_exports_are_exactly_the_authority_zero_surface() -> None:
    assert broker.__all__ == (
        "ProductOperationRequestV1",
        "ProductOperationAuthorizationResolutionV1",
        "ProductOperationAuditReceiptV1",
        "ProductOperationTerminalStatusV1",
        "create_product_operation_request",
        "read_product_operation_status",
    )


@pytest.mark.parametrize(
    ("public_type", "stable_code"),
    [
        (broker.ProductOperationRequestV1, "TASK072_AUTHORIZATION_REJECTED"),
        (
            broker.ProductOperationAuthorizationResolutionV1,
            "TASK072_AUTHORIZATION_REJECTED",
        ),
        (broker.ProductOperationAuditReceiptV1, "TASK072_COMPLETION_UNKNOWN"),
        (broker.ProductOperationTerminalStatusV1, "TASK072_COMPLETION_UNKNOWN"),
    ],
)
def test_public_audit_types_are_final_against_post_init_bypass(
    public_type: type[object], stable_code: str
) -> None:
    with pytest.raises(TypeError, match=f"^{stable_code}$"):
        type(
            "ForgedAuditProjection",
            (public_type,),
            {"__post_init__": lambda self: None},
        )
    assert not any(
        name in broker.__all__
        for name in (
            "_TrustedProductOperationBrokerV1",
            "_LiveOperationTicketV1",
            "_issue_operation_ticket_v1",
            "ProductOperationContractError",
        )
    )


def test_request_factory_creates_distinct_audit_only_requests() -> None:
    first = broker.create_product_operation_request(
        action_profile="INSTALL_AUTHORITY_PAIR_WRITE",
        upstream_receipt_sha256=(SHA_A, SHA_B),
    )
    second = broker.create_product_operation_request(
        action_profile="INSTALL_AUTHORITY_PAIR_WRITE",
        upstream_receipt_sha256=(SHA_A, SHA_B),
    )
    assert first.request_id != second.request_id
    assert first.authority_created is False
    assert first.requested_state == "REQUESTED"
    assert first.to_dict()["upstream_receipt_sha256"] == [SHA_A, SHA_B]
    assert not hasattr(first, "ticket_id")
    assert not hasattr(first, "operation_id")
    with pytest.raises(FrozenInstanceError):
        first.authority_created = True  # type: ignore[misc]


def test_fixture_action_matrix_is_closed_and_non_authoritative() -> None:
    path = ROOT / "tests/fixtures/task072/operation-port-v1/action-profiles.json"
    value = broker._strict_json_object(path.read_bytes())
    expected_profiles = (
        "INSTALL_AUTHORITY_PAIR_WRITE",
        "MIGRATION_CA_A_EXECUTE",
        "PROFILE_BIND_CA_B_EXECUTE",
        "GPU_REQUIRED_LAUNCH",
        "D2S_VALIDATE",
        "D2S_EMIT_PROPOSAL",
        "D2S_FEEDBACK_TO_LEARNING",
        "D2S_ROUND_TRIP",
        "D2S_CONVERT_FRAME",
        "D2S_VALIDATE_TASK056_SIDECAR",
        "D2S_CONNECTOR_STATUS",
        "D2S_PUBLISH_LEARNING",
        "PRODUCT_BROKER_TERMINAL_QUERY",
        "D2S_LOAD_PROFILE",
        "PRODUCT_D2S_ROUNDTRIP_E2E_VERIFY",
        "ACTIVATION_CONFIG_FINALIZE",
    )
    assert value["fixture_only"] is True
    assert value["authority_created"] is False
    assert value["native_broker_executed"] is False
    assert value["design_sha256"] == (
        "sha256:397bb12a8c6de72f5df691006f071314916d6bc2bd01d7db8d85798b74173dbc"
    )
    assert value["public_contract"] == {
        "request_message_type": "BvpProductOperationRequest",
        "audit_receipt_message_type": "BvpProductOperationAuditReceipt",
        "authority_created": False,
    }
    fixture_profiles = tuple(
        item["action_profile"] for item in value["profile_contracts"]
    )
    assert fixture_profiles == expected_profiles
    assert frozenset(expected_profiles) == broker._ACTION_PROFILES
    for item, profile in zip(value["profile_contracts"], expected_profiles, strict=True):
        assert item["request_message_type"] == "BvpProductOperationRequest"
        assert item["audit_receipt_message_type"] == (
            "BvpProductOperationAuditReceipt"
        )
        request = broker.create_product_operation_request(action_profile=profile)
        assert request.authority_created is False


def test_fixture_command_bindings_and_coordinate_vectors_are_independently_frozen() -> None:
    path = ROOT / "tests/fixtures/task072/operation-port-v1/action-profiles.json"
    value = broker._strict_json_object(path.read_bytes())
    expected_bindings = (
        ("D2S_VALIDATE", "SKILL_D2S_ADAPTER_V1", "validate"),
        ("D2S_EMIT_PROPOSAL", "SKILL_D2S_ADAPTER_V1", "emit-proposal"),
        (
            "D2S_FEEDBACK_TO_LEARNING",
            "SKILL_D2S_ADAPTER_V1",
            "feedback-to-learning",
        ),
        ("D2S_ROUND_TRIP", "SKILL_D2S_ADAPTER_V1", "round-trip"),
        ("D2S_CONVERT_FRAME", "SKILL_D2S_ADAPTER_V1", "convert-frame"),
        (
            "D2S_VALIDATE_TASK056_SIDECAR",
            "SKILL_D2S_ADAPTER_V1",
            "validate-task056-sidecar",
        ),
        ("D2S_CONNECTOR_STATUS", "SKILL_D2S_ADAPTER_V1", "connector-status"),
        ("D2S_PUBLISH_LEARNING", "SKILL_D2S_ADAPTER_V1", "publish-learning"),
        ("D2S_LOAD_PROFILE", "SKILL_D2S_ADAPTER_V1", "load-profile"),
    )
    actual_bindings = tuple(
        (
            item["action_profile"],
            item["config_binding"]["command"],
            item["config_binding"]["subcommand"],
        )
        for item in value["profile_contracts"]
        if item["config_binding"] is not None
    )
    assert actual_bindings == expected_bindings

    ticket_schema = json.loads(
        (ROOT / "schemas/product-operation-ticket.schema.json").read_text(
            encoding="utf-8"
        )
    )
    first_pattern = ticket_schema["$defs"]["firstEventCoordinate"]["pattern"]
    event_pattern = ticket_schema["$defs"]["eventCoordinate"]["pattern"]
    coordinates = value["coordinate_vectors"]
    assert re.fullmatch(first_pattern, coordinates["valid_first_event"])
    assert re.fullmatch(event_pattern, coordinates["valid_later_event"])
    assert all(
        re.fullmatch(event_pattern, candidate) is None
        for candidate in coordinates["invalid"]
    )


def test_ticket_schema_fixture_self_hashes_match_independent_canonical_bytes() -> None:
    path = ROOT / "tests/fixtures/task072/operation-port-v1/ticket-schema-vectors.json"
    vectors = json.loads(path.read_text(encoding="utf-8"))
    for document_name, hash_field in (
        ("valid_reservation", "reservation_sha256"),
        ("valid_first_event", "event_sha256"),
    ):
        document = dict(vectors[document_name])
        declared = document.pop(hash_field)
        canonical = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        assert declared == "sha256:" + hashlib.sha256(canonical).hexdigest()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"action_profile": "UNKNOWN", "upstream_receipt_sha256": ()},
        {"action_profile": "INSTALL_AUTHORITY_PAIR_WRITE", "upstream_receipt_sha256": ("bad",)},
        {
            "action_profile": "INSTALL_AUTHORITY_PAIR_WRITE",
            "upstream_receipt_sha256": (SHA_A, SHA_A),
        },
        {"action_profile": "INSTALL_AUTHORITY_PAIR_WRITE", "upstream_receipt_sha256": {SHA_A}},
    ],
)
def test_request_factory_rejects_unbound_or_noncanonical_inputs(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="^TASK072_AUTHORIZATION_REJECTED$"):
        broker.create_product_operation_request(**kwargs)  # type: ignore[arg-type]


def test_request_factory_rejects_oversized_receipt_sequences_before_iteration() -> None:
    for count in (33, 100_000):
        with pytest.raises(ValueError, match="^TASK072_AUTHORIZATION_REJECTED$"):
            broker.create_product_operation_request(
                action_profile="INSTALL_AUTHORITY_PAIR_WRITE",
                upstream_receipt_sha256=[SHA_A] * count,
            )


def test_public_resolution_and_receipt_are_self_hashed_audit_data_only() -> None:
    resolution = broker._authorization_resolution_from_bytes(_bytes(_authorization_body()))
    receipt = broker._audit_receipt_from_bytes(_bytes(_receipt_body()))
    assert resolution.authority_created is False
    assert resolution.reservation_created is False
    assert resolution.ticket_created is False
    assert receipt.authority_created is False
    assert receipt.message_type == "BvpProductOperationAuditReceipt"
    assert not hasattr(receipt, "redeem")
    assert not hasattr(resolution, "issue")


def test_authorization_resolution_code_cannot_be_cross_classified() -> None:
    value = _authorization_body()
    value["stable_code"] = "TASK072_AUTHORIZATION_REJECTED"
    body = dict(value)
    body.pop("resolution_sha256")
    value["resolution_sha256"] = broker._sha256_json(body)
    with pytest.raises(ValueError, match="^TASK072_AUTHORIZATION_REJECTED$"):
        broker._authorization_resolution_from_bytes(_bytes(value))


@pytest.mark.parametrize("bad_value", [None, [], {}, 1, True])
def test_contract_parsers_translate_wrong_semantic_types_to_stable_codes(
    bad_value: object,
) -> None:
    authorization = _authorization_body()
    authorization["resolution"] = bad_value
    with pytest.raises(ValueError, match="^TASK072_AUTHORIZATION_REJECTED$"):
        broker._authorization_resolution_from_bytes(_bytes(authorization))

    receipt = _receipt_body()
    receipt["terminal_state"] = bad_value
    with pytest.raises(ValueError, match="^TASK072_COMPLETION_UNKNOWN$"):
        broker._audit_receipt_from_bytes(_bytes(receipt))

    status = _status_body()
    status["durable_state"] = bad_value
    with pytest.raises(ValueError, match="^TASK072_COMPLETION_UNKNOWN$"):
        broker.read_product_operation_status(_bytes(status))


@pytest.mark.parametrize(
    ("state", "stable_code", "effect_observed"),
    [
        ("COMMITTED", "TASK072_COMPLETION_UNKNOWN", True),
        ("COMMITTED", None, False),
        ("REJECTED", None, False),
        ("REJECTED", "TASK072_AUTHORIZATION_REJECTED", True),
        ("BURNED_UNKNOWN", None, False),
        ("BURNED_UNKNOWN", "TASK072_COMPLETION_UNKNOWN", True),
    ],
)
def test_public_audit_receipt_state_effect_relationships_are_exact(
    state: str, stable_code: str | None, effect_observed: bool
) -> None:
    value = _receipt_body()
    value.update(
        terminal_state=state,
        stable_code=stable_code,
        consumer_effect_observed=effect_observed,
    )
    body = dict(value)
    body.pop("receipt_sha256")
    value["receipt_sha256"] = broker._sha256_json(body)
    with pytest.raises(ValueError, match="^TASK072_COMPLETION_UNKNOWN$"):
        broker._audit_receipt_from_bytes(_bytes(value))


@pytest.mark.parametrize(
    "change",
    [
        {"event_revision": 0},
        {"event_revision": True},
        {"event_revision": 2147483648},
        {"event_utc": "2026-02-31T12:30:01Z"},
        {"event_utc": "2026-09-03T12:30:01+00:00"},
        {"event_utc": []},
    ],
)
def test_public_audit_receipt_rejects_invalid_event_coordinates(
    change: dict[str, object],
) -> None:
    value = _receipt_body()
    value.update(change)
    body = dict(value)
    body.pop("receipt_sha256")
    value["receipt_sha256"] = broker._sha256_json(body)
    with pytest.raises(ValueError, match="^TASK072_COMPLETION_UNKNOWN$"):
        broker._audit_receipt_from_bytes(_bytes(value))


def test_recomputed_public_hash_does_not_create_an_authority_surface() -> None:
    forged = _receipt_body()
    forged["result_sha256"] = SHA_A
    body = dict(forged)
    body.pop("receipt_sha256")
    forged["receipt_sha256"] = broker._sha256_json(body)
    projection = broker._audit_receipt_from_bytes(_bytes(forged))
    assert projection.authority_created is False
    assert not any(
        name.startswith("issue") or name.startswith("redeem")
        for name in dir(projection)
    )


def test_copy_deepcopy_and_pickle_keep_public_values_authority_zero() -> None:
    values = (
        broker.create_product_operation_request(action_profile="INSTALL_AUTHORITY_PAIR_WRITE"),
        broker._authorization_resolution_from_bytes(_bytes(_authorization_body())),
        broker._audit_receipt_from_bytes(_bytes(_receipt_body())),
        broker.read_product_operation_status(_bytes(_status_body())),
    )
    for value in values:
        for recreated in (
            copy.copy(value),
            copy.deepcopy(value),
            pickle.loads(pickle.dumps(value)),
        ):
            assert recreated.authority_created is False
            assert not hasattr(recreated, "issue")
            assert not hasattr(recreated, "redeem")


def test_status_parser_returns_frozen_exact_self_hashed_projection() -> None:
    status = broker.read_product_operation_status(_bytes(_status_body()))
    assert status.durable_state == "REQUESTED"
    assert status.terminal is False
    assert status.committed is False
    assert status.effect_confirmed is False
    assert status.authority_created is False
    with pytest.raises(FrozenInstanceError):
        status.terminal = True  # type: ignore[misc]


@pytest.mark.parametrize(
    "state,code,terminal,committed,effect",
    [
        ("COMMITTED", None, True, True, True),
        ("REJECTED", "TASK072_AUTHORIZATION_REJECTED", True, False, False),
        ("BURNED", "TASK072_TICKET_CONSUMED", True, False, False),
        ("BURNED_UNKNOWN", "TASK072_COMPLETION_UNKNOWN", True, False, False),
    ],
)
def test_terminal_state_boolean_relationships_are_closed(
    state: str, code: str | None, terminal: bool, committed: bool, effect: bool
) -> None:
    value = _status_body(state=state, stable_code=code)
    status = broker.read_product_operation_status(_bytes(value))
    assert (status.terminal, status.committed, status.effect_confirmed) == (
        terminal,
        committed,
        effect,
    )


@pytest.mark.parametrize(
    "change",
    [
        {"authority_created": True},
        {"terminal": True},
        {"committed": True},
        {"effect_confirmed": True},
        {"stable_code": "TASK072_OK"},
        {"message_type": "Other"},
        {"schema_version": "2.0.0"},
        {"unknown": False},
    ],
)
def test_status_semantic_or_shape_tamper_is_body_free(change: dict[str, object]) -> None:
    value = _status_body()
    value.update(change)
    body = dict(value)
    body.pop("status_sha256", None)
    value["status_sha256"] = broker._sha256_json(body)
    with pytest.raises(ValueError) as exc:
        broker.read_product_operation_status(_bytes(value))
    assert str(exc.value) == "TASK072_COMPLETION_UNKNOWN"
    assert "request" not in str(exc.value).lower()


@pytest.mark.parametrize(
    "payload",
    [
        (
            b'{"message_type":"BvpProductOperationTerminalStatus",'
            b'"message_type":"BvpProductOperationTerminalStatus"}'
        ),
        b'{"outer":{"same":1,"same":1}}',
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":-Infinity}',
        b"\xef\xbb\xbf{}",
        b"{} trailing",
        b'{"value":"\\u0000"}',
        b"\xff",
        b"",
    ],
)
def test_strict_json_rejects_ambiguous_documents_before_contract_use(payload: bytes) -> None:
    with pytest.raises(ValueError, match="^TASK072_AUTHORIZATION_REJECTED$"):
        broker._strict_json_object(payload)


def test_strict_json_rejects_depth_width_nodes_and_strings() -> None:
    deep: object = 0
    for _ in range(9):
        deep = {"x": deep}
    wide = {f"k{index}": index for index in range(65)}
    nodes = {"groups": [list(range(64)) for _ in range(8)]}
    huge = {"value": "x" * 4097}
    huge_integer = {"value": 2**63}
    for value in (deep, wide, nodes, huge, huge_integer):
        with pytest.raises(ValueError, match="^TASK072_AUTHORIZATION_REJECTED$"):
            broker._strict_json_object(_bytes(value))


@pytest.mark.parametrize("payload", [{}, bytearray(b"{}"), memoryview(b"{}"), "{}"])
def test_strict_json_rejects_preparsed_or_mutable_inputs(payload: object) -> None:
    with pytest.raises(ValueError, match="^TASK072_AUTHORIZATION_REJECTED$"):
        broker._strict_json_object(payload)  # type: ignore[arg-type]


def test_schema_resources_are_byte_identical_and_closed() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    for name in (
        "product-operation-ticket.schema.json",
        "product-operation-config.schema.json",
        "product-operation-receipt.schema.json",
    ):
        public = ROOT / "schemas" / name
        packaged = ROOT / "src" / "ai_video_production" / "schema_resources" / name
        assert public.read_bytes() == packaged.read_bytes()
        schema = json.loads(public.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)


def test_ticket_schema_accepts_request_and_rejects_unknown_or_authority_true() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "schemas/product-operation-ticket.schema.json").read_text(
            encoding="utf-8"
        )
    )
    request = broker.create_product_operation_request(
        action_profile="INSTALL_AUTHORITY_PAIR_WRITE", upstream_receipt_sha256=(SHA_A,)
    ).to_dict()
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    assert not list(validator.iter_errors(request))
    assert list(validator.iter_errors({**request, "authority_created": True}))
    assert list(validator.iter_errors({**request, "unknown": False}))


def test_ticket_schema_accepts_exact_coordinates_and_rejects_invalid_vectors() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "schemas/product-operation-ticket.schema.json").read_text(
            encoding="utf-8"
        )
    )
    vectors = json.loads(
        (
            ROOT
            / "tests/fixtures/task072/operation-port-v1/ticket-schema-vectors.json"
        ).read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    portable_validator = jsonschema.Draft202012Validator(schema)
    assert not list(validator.iter_errors(vectors["valid_reservation"]))
    assert not list(validator.iter_errors(vectors["valid_first_event"]))
    assert not list(
        portable_validator.iter_errors(
            {**vectors["valid_reservation"], "expiry_utc": "2000-02-29T23:59:59Z"}
        )
    )
    assert list(
        portable_validator.iter_errors(
            {**vectors["valid_reservation"], "expiry_utc": "2026-02-31T12:30:00Z"}
        )
    )
    assert list(
        portable_validator.iter_errors(
            {**vectors["valid_first_event"], "event_utc": "2026-02-31T12:30:01Z"}
        )
    )
    assert list(
        portable_validator.iter_errors(
            {**vectors["valid_first_event"], "event_utc": "1900-02-29T12:30:01Z"}
        )
    )
    assert list(
        validator.iter_errors(
            {**vectors["valid_first_event"], "subcommand": "emit-proposal"}
        )
    )
    for coordinate in vectors["invalid_first_event_coordinates"]:
        candidate = {**vectors["valid_reservation"], "first_event_coordinate": coordinate}
        assert list(validator.iter_errors(candidate))
    for coordinate in vectors["invalid_event_coordinates"]:
        candidate = {**vectors["valid_first_event"], "next_event_coordinate": coordinate}
        assert list(validator.iter_errors(candidate))
