from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import pickle
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "src" / "ai_video_production"
if "ai_video_production" not in sys.modules:
    package = types.ModuleType("ai_video_production")
    package.__path__ = [str(PACKAGE_DIR)]  # type: ignore[attr-defined]
    sys.modules["ai_video_production"] = package

import ai_video_production.product_operation_config as config
from ai_video_production import product_operation_broker as broker


def _sha(character: str) -> str:
    return "sha256:" + character * 64


def _bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _config_body(**changes: object) -> dict[str, object]:
    body: dict[str, object] = {
        "adapter_build_sha256": _sha("8"),
        "authority_created": False,
        "command": "SKILL_D2S_ADAPTER_V1",
        "config_projection_build_sha256": _sha("9"),
        "contract_profile": "D2S_VALIDATE",
        "deadline_monotonic_ms": 2000,
        "distribution_config_mutated": False,
        "expected_delivery_sha256": _sha("4"),
        "expected_input_sha256": _sha("1"),
        "expected_profile_sha256": _sha("3"),
        "expected_record_sha256": _sha("2"),
        "expected_result_sha256": _sha("5"),
        "expiry_utc": "2026-09-03T12:30:00Z",
        "install_instance_id": "install-instance-001",
        "invocation_budget": 1,
        "issue_monotonic_ms": 1000,
        "message_type": "BvpOperationSpecificConfig",
        "operation_id": "a" * 32,
        "product_build_sha256": _sha("7"),
        "schema_version": "2.0.0",
        "subcommand": "validate",
        "ticket_id": "b" * 32,
        "upstream_receipt_sha256": [_sha("0"), _sha("6")],
    }
    body.update(changes)
    body["config_sha256"] = broker._sha256_json(body)
    return body


def test_public_exports_are_exact_and_effect_free() -> None:
    assert config.__all__ == (
        "OperationConfigAuditV2",
        "validate_operation_config_audit",
    )


def test_public_config_audit_type_is_final_against_post_init_bypass() -> None:
    with pytest.raises(TypeError, match="^TASK072_CONFIG_REJECTED$"):
        type(
            "ForgedOperationConfigAudit",
            (config.OperationConfigAuditV2,),
            {"__post_init__": lambda self: None},
        )
    assert not any(
        name in config.__all__
        for name in (
            "_publish_operation_config_v2",
            "_readback_operation_config_v2",
            "_ConfigParentBindingV1",
        )
    )


def test_config_audit_strict_parse_is_immutable_and_authority_zero() -> None:
    audit = config.validate_operation_config_audit(_bytes(_config_body()))
    assert audit.contract_profile == "D2S_VALIDATE"
    assert audit.upstream_receipt_sha256 == (_sha("0"), _sha("6"))
    assert audit.invocation_budget == 1
    assert audit.distribution_config_mutated is False
    assert audit.authority_created is False
    assert not hasattr(audit, "publish")
    assert not hasattr(audit, "redeem")
    with pytest.raises(FrozenInstanceError):
        audit.authority_created = True  # type: ignore[misc]


def test_config_copy_deepcopy_and_pickle_remain_authority_zero() -> None:
    audit = config.validate_operation_config_audit(_bytes(_config_body()))
    for recreated in (copy.copy(audit), copy.deepcopy(audit), pickle.loads(pickle.dumps(audit))):
        assert recreated.authority_created is False
        assert not hasattr(recreated, "publish")
        assert not hasattr(recreated, "redeem")


def test_command_registry_global_rebind_cannot_admit_an_unconfirmed_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert type(config._COMMAND_BINDINGS) is tuple
    assert all(type(binding) is tuple for binding in config._COMMAND_BINDINGS)
    monkeypatch.setattr(
        config,
        "_COMMAND_BINDINGS",
        (("D2S_VALIDATE", "unconfirmed-command", "unconfirmed-subcommand"),),
    )
    malicious = _config_body(
        command="unconfirmed-command", subcommand="unconfirmed-subcommand"
    )
    with pytest.raises(ValueError, match="^TASK072_CONFIG_REJECTED$"):
        config.validate_operation_config_audit(_bytes(malicious))
    assert config.validate_operation_config_audit(_bytes(_config_body())).subcommand == "validate"


@pytest.mark.parametrize(
    "changes",
    [
        {"authority_created": True},
        {"distribution_config_mutated": True},
        {"invocation_budget": 2},
        {"command": "product-broker"},
        {"subcommand": "emit-proposal"},
        {"contract_profile": "INSTALL_AUTHORITY_PAIR_WRITE"},
        {"operation_id": "A" * 32},
        {"ticket_id": "b" * 31},
        {"install_instance_id": "C:\\foreign"},
        {"install_instance_id": "https://example.invalid"},
        {"issue_monotonic_ms": 2000},
        {"deadline_monotonic_ms": 1000},
        {"expiry_utc": "2026-02-31T12:30:00Z"},
        {"upstream_receipt_sha256": [_sha("0"), _sha("0")]},
        {"expected_input_sha256": "bad"},
        {"message_type": "Other"},
        {"schema_version": "1.0.0"},
        {"unknown": False},
    ],
)
def test_config_rejects_tamper_and_cross_action_rebinding(changes: dict[str, object]) -> None:
    value = _config_body(**changes)
    with pytest.raises(ValueError) as exc:
        config.validate_operation_config_audit(_bytes(value))
    assert str(exc.value) == "TASK072_CONFIG_REJECTED"
    assert "foreign" not in str(exc.value)


def test_config_rejects_self_hash_mismatch() -> None:
    value = _config_body()
    value["expected_result_sha256"] = _sha("a")
    with pytest.raises(ValueError, match="^TASK072_CONFIG_REJECTED$"):
        config.validate_operation_config_audit(_bytes(value))


@pytest.mark.parametrize("bad_value", [None, {}, "not-an-array", 1, True])
def test_config_rejects_wrong_receipt_collection_types_with_stable_code(
    bad_value: object,
) -> None:
    value = _config_body(upstream_receipt_sha256=bad_value)
    with pytest.raises(ValueError, match="^TASK072_CONFIG_REJECTED$"):
        config.validate_operation_config_audit(_bytes(value))


@pytest.mark.parametrize(
    "payload",
    [
        (
            b'{"message_type":"BvpOperationSpecificConfig",'
            b'"message_type":"BvpOperationSpecificConfig"}'
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
def test_config_strict_json_failures_are_body_free(payload: bytes) -> None:
    with pytest.raises(ValueError) as exc:
        config.validate_operation_config_audit(payload)
    assert str(exc.value) == "TASK072_CONFIG_REJECTED"
    assert "message_type" not in str(exc.value)


@pytest.mark.parametrize("payload", [{}, bytearray(b"{}"), memoryview(b"{}"), "{}"])
def test_config_rejects_mapping_and_mutable_byte_inputs(payload: object) -> None:
    with pytest.raises(ValueError, match="^TASK072_CONFIG_REJECTED$"):
        config.validate_operation_config_audit(payload)  # type: ignore[arg-type]


def test_config_rejects_depth_width_nodes_and_strings_before_hash_use() -> None:
    deep: object = 0
    for _ in range(9):
        deep = {"x": deep}
    values = (
        deep,
        {f"k{index}": index for index in range(65)},
        {"groups": [list(range(64)) for _ in range(8)]},
        {"value": "x" * 4097},
    )
    for value in values:
        with pytest.raises(ValueError, match="^TASK072_CONFIG_REJECTED$"):
            config.validate_operation_config_audit(_bytes(value))


def test_config_schema_is_closed_and_command_pair_is_exactly_bound() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    public = ROOT / "schemas/product-operation-config.schema.json"
    packaged = (
        ROOT
        / "src/ai_video_production/schema_resources/product-operation-config.schema.json"
    )
    assert public.read_bytes() == packaged.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    portable_validator = jsonschema.Draft202012Validator(schema)
    value = _config_body()
    assert not list(validator.iter_errors(value))
    assert not list(
        portable_validator.iter_errors(
            {**value, "expiry_utc": "2000-02-29T23:59:59Z"}
        )
    )
    assert list(
        portable_validator.iter_errors(
            {**value, "expiry_utc": "2026-02-31T12:30:00Z"}
        )
    )
    assert list(
        portable_validator.iter_errors(
            {**value, "expiry_utc": "1900-02-29T12:30:00Z"}
        )
    )
    assert list(validator.iter_errors({**value, "unknown": False}))
    assert list(validator.iter_errors({**value, "authority_created": True}))
    schema_only_cross_pair = {**value, "subcommand": "emit-proposal"}
    schema_only_cross_pair["config_sha256"] = broker._sha256_json(
        {key: item for key, item in schema_only_cross_pair.items() if key != "config_sha256"}
    )
    assert list(validator.iter_errors(schema_only_cross_pair))
    with pytest.raises(ValueError, match="^TASK072_CONFIG_REJECTED$"):
        config.validate_operation_config_audit(_bytes(schema_only_cross_pair))


def test_receipt_schema_is_byte_identical_and_closed() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    public = ROOT / "schemas/product-operation-receipt.schema.json"
    packaged = (
        ROOT
        / "src/ai_video_production/schema_resources/product-operation-receipt.schema.json"
    )
    assert public.read_bytes() == packaged.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    portable_validator = jsonschema.Draft202012Validator(schema)
    audit_receipt = {
        "message_type": "BvpProductOperationAuditReceipt",
        "schema_version": "1.0.0",
        "action_profile": "D2S_VALIDATE",
        "terminal_state": "COMMITTED",
        "stable_code": None,
        "event_revision": 1,
        "event_utc": "2026-09-03T12:30:01Z",
        "operation_commitment_sha256": _sha("1"),
        "ticket_commitment_sha256": _sha("2"),
        "event_commitment_sha256": _sha("3"),
        "config_commitment_sha256": _sha("4"),
        "result_sha256": _sha("5"),
        "upstream_receipt_count": 1,
        "downstream_receipt_count": 1,
        "consumer_effect_observed": True,
        "authority_created": False,
        "receipt_sha256": _sha("6"),
    }
    assert not list(validator.iter_errors(audit_receipt))
    assert not list(
        portable_validator.iter_errors(
            {**audit_receipt, "event_utc": "2000-02-29T23:59:59Z"}
        )
    )
    assert list(
        validator.iter_errors(
            {**audit_receipt, "message_type": "BvpProductOperationRedemptionReceipt"}
        )
    )
    assert list(
        validator.iter_errors(
            {**audit_receipt, "consumer_effect_observed": False}
        )
    )
    assert list(
        portable_validator.iter_errors(
            {**audit_receipt, "event_utc": "2026-02-31T12:30:01Z"}
        )
    )
    assert list(
        portable_validator.iter_errors(
            {**audit_receipt, "event_utc": "1900-02-29T12:30:01Z"}
        )
    )
    assert list(
        validator.iter_errors(
            {
                **audit_receipt,
                "terminal_state": "REJECTED",
                "stable_code": "TASK072_AUTHORIZATION_REJECTED",
                "consumer_effect_observed": True,
            }
        )
    )

    resolution = {
        "message_type": "BvpProductOperationAuthorizationResolution",
        "schema_version": "1.0.0",
        "request_id": "request-fixture",
        "action_profile": "D2S_VALIDATE",
        "resolution": "NOT_CONFIRMED",
        "stable_code": "TASK072_AUTHORIZATION_NC",
        "reservation_created": False,
        "ticket_created": False,
        "authority_created": False,
        "resolution_sha256": _sha("7"),
    }
    assert not list(validator.iter_errors(resolution))
    assert list(
        validator.iter_errors(
            {**resolution, "stable_code": "TASK072_AUTHORIZATION_REJECTED"}
        )
    )

    status = {
        "message_type": "BvpProductOperationTerminalStatus",
        "schema_version": "1.0.0",
        "operation_commitment_sha256": _sha("1"),
        "durable_state": "REQUESTED",
        "stable_code": None,
        "terminal": False,
        "committed": False,
        "effect_confirmed": False,
        "authority_created": False,
        "status_sha256": _sha("8"),
    }
    assert not list(validator.iter_errors(status))
    assert list(validator.iter_errors({**status, "terminal": True}))
    assert not list(
        validator.iter_errors(
            {
                **status,
                "durable_state": "COMMITTED",
                "terminal": True,
                "committed": True,
                "effect_confirmed": True,
            }
        )
    )
