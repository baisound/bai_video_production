from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import fields, replace
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.montage_learning_production_linkage import (
    MontageLearningProductionLinkageError,
    PreactivationChainConsumerPort,
    PreactivationChainPlan,
    PreactivationFixtureValidation,
    TASK072_DESIGN_SHA256,
)
from ai_video_production.serialization import sha256_bytes


def _sha(label: str) -> str:
    return sha256_bytes(label.encode("ascii"))


def _plan() -> PreactivationChainPlan:
    return PreactivationChainPlan(
        operation_id="op_00000000000000000000000000000001",
        install_instance_id="inst_00000000000000000000000000000001",
        record_id="rec_00000000000000000000000000000001",
        learning_sha256=_sha("learning"),
        config_sha256=_sha("config"),
        adapter_build_sha256=_sha("adapter-build"),
        adapter_stage_receipt_sha256=_sha("adapter-stage"),
        task036_import_receipt_sha256=_sha("task036-import"),
        task036_completion_receipt_sha256=_sha("task036-completion"),
        task061b_completion_receipt_sha256=_sha("task061b-completion"),
        public_receipt_id="rcpt_00000000000000000000000000000001",
        public_receipt_sha256=_sha("public-receipt"),
        hidden_correlation_sha256=_sha("hidden-correlation"),
        canonical_readback_sha256=_sha("canonical-readback"),
        profile_id="prof_00000000000000000000000000000001",
        profile_sha256=_sha("profile"),
        profile_readback_sha256=_sha("profile-readback"),
    )


def _fixture(plan: PreactivationChainPlan | None = None) -> dict[str, object]:
    plan = plan or _plan()
    plan_value = plan.to_dict()
    return {
        "schema_version": "1.0.0",
        "message_type": "Task065PreactivationChainFixture",
        "phase": "PREACTIVATION",
        "evidence_mode": "SYNTHETIC_PUBLIC_SAFE_FIXTURE",
        "task072_design_sha256": TASK072_DESIGN_SHA256,
        "plan_sha256": plan_value["plan_sha256"],
        "operation_id": plan.operation_id,
        "install_instance_id": plan.install_instance_id,
        "task036_completion_receipt_sha256": plan.task036_completion_receipt_sha256,
        "task061b_completion_receipt_sha256": plan.task061b_completion_receipt_sha256,
        "adapter_stage": {
            "operation_id": plan.operation_id,
            "record_id": plan.record_id,
            "learning_sha256": plan.learning_sha256,
            "config_sha256": plan.config_sha256,
            "adapter_build_sha256": plan.adapter_build_sha256,
            "invocation_count": 1,
            "status": "STAGED",
            "receipt_sha256": plan.adapter_stage_receipt_sha256,
        },
        "task036_import": {
            "operation_id": plan.operation_id,
            "record_id": plan.record_id,
            "learning_sha256": plan.learning_sha256,
            "invocation_count": 1,
            "status": "ACCEPTED",
            "receipt_sha256": plan.task036_import_receipt_sha256,
        },
        "public_receipt": {
            "receipt_id": plan.public_receipt_id,
            "record_id": plan.record_id,
            "learning_sha256": plan.learning_sha256,
            "status": "ACCEPTED",
            "receipt_sha256": plan.public_receipt_sha256,
            "authority_created": False,
        },
        "hidden_correlation": {
            "operation_id": plan.operation_id,
            "install_instance_id": plan.install_instance_id,
            "config_sha256": plan.config_sha256,
            "record_id": plan.record_id,
            "learning_sha256": plan.learning_sha256,
            "public_receipt_sha256": plan.public_receipt_sha256,
            "canonical_readback_sha256": plan.canonical_readback_sha256,
            "profile_readback_sha256": plan.profile_readback_sha256,
            "correlation_sha256": plan.hidden_correlation_sha256,
        },
        "canonical_readback": {
            "record_id": plan.record_id,
            "learning_sha256": plan.learning_sha256,
            "canonical_revision": 1,
            "readback_sha256": plan.canonical_readback_sha256,
            "durable_readback_verified": True,
            "authority_created": False,
        },
        "profile_readback": {
            "profile_id": plan.profile_id,
            "profile_sha256": plan.profile_sha256,
            "source_record_id": plan.record_id,
            "source_learning_sha256": plan.learning_sha256,
            "readback_sha256": plan.profile_readback_sha256,
            "advisory_only": True,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
            "durable_readback_verified": True,
            "authority_created": False,
        },
        "evidence_complete": True,
        "authority_created": False,
    }


def _schemas() -> tuple[Path, Path, dict[str, object]]:
    root = Path(__file__).resolve().parents[1]
    public = root / "schemas" / "montage-learning-production-linkage.schema.json"
    mirror = (
        root
        / "src"
        / "ai_video_production"
        / "schema_resources"
        / public.name
    )
    return public, mirror, json.loads(public.read_text(encoding="utf-8"))


def _set(fixture: dict[str, object], path: tuple[str, ...], value: object) -> None:
    target: dict[str, object] = fixture
    for name in path[:-1]:
        child = target[name]
        assert type(child) is dict
        target = child
    target[path[-1]] = value


def test_valid_fixture_is_joined_without_any_task065_effect() -> None:
    plan = _plan()
    plan_projection = plan.to_dict()
    assert plan_projection["authority_created"] is False
    assert plan_projection["local_effects_authorized"] is False
    assert plan.hidden_correlation_sha256 not in json.dumps(plan_projection, sort_keys=True)
    fixture = _fixture(plan)
    before = deepcopy(fixture)
    port = PreactivationChainConsumerPort(plan)

    result = port.validate(fixture).to_dict()

    assert fixture == before
    assert port.state == "COMPLETED"
    assert result["message_type"] == "Task065PreactivationFixtureValidation"
    assert result["status"] == "SYNTHETIC_FIXTURE_VALIDATED"
    assert result["evidence_mode"] == "SYNTHETIC_PUBLIC_SAFE_FIXTURE"
    assert result["historical_stage_invocation_count"] == 1
    assert result["historical_import_invocation_count"] == 1
    for field in (
        "task065_adapter_call_count",
        "task065_task036_call_count",
        "project_delta_count",
        "bridge_delta_count",
        "profile_delta_count",
        "config_delta_count",
        "history_delta_count",
    ):
        assert result[field] == 0
    for field in (
        "authority_created",
        "activation_authorized",
        "steady_state_authorized",
        "real_installed_adapter_verified",
        "activation_prerequisite_satisfied",
        "production_chain_complete",
        "task072_implementation_receipt_verified",
    ):
        assert result[field] is False
    assert result["hidden_correlation_fixture_matched"] is True
    assert result["task072_design_sha256"] == TASK072_DESIGN_SHA256
    rendered = json.dumps(result, sort_keys=True)
    assert plan.hidden_correlation_sha256 not in rendered
    assert "C:\\" not in rendered
    assert "ProgramData" not in rendered


def test_fixture_and_public_validation_use_closed_mirrored_schema() -> None:
    public, mirror, schema = _schemas()
    assert public.read_bytes() == mirror.read_bytes()
    validator = Draft202012Validator(schema)
    fixture = _fixture()
    validation = PreactivationChainConsumerPort(_plan()).validate(fixture).to_dict()
    validator.validate(fixture)
    validator.validate(validation)

    extra = deepcopy(fixture)
    extra["canonical_store_written"] = True
    assert not validator.is_valid(extra)


def test_direct_or_copied_validation_cannot_mint_final_admission() -> None:
    plan = _plan()
    original = PreactivationChainConsumerPort(plan).validate(_fixture(plan))
    direct = PreactivationFixtureValidation(
        **{field.name: getattr(original, field.name) for field in fields(original)}
    )
    copied = replace(direct, public_receipt_id="rcpt_ffffffffffffffffffffffffffffffff")
    validator = Draft202012Validator(_schemas()[2])

    for value in (direct.to_dict(), copied.to_dict()):
        validator.validate(value)
        assert value["message_type"] == "Task065PreactivationFixtureValidation"
        assert value["status"] == "SYNTHETIC_FIXTURE_VALIDATED"
        assert value["authority_created"] is False
        assert value["activation_prerequisite_satisfied"] is False
        assert "PREACTIVATION_CHAIN_ADMITTED" not in json.dumps(value, sort_keys=True)
        assert "hidden_correlation_verified" not in value

        forged_final = dict(value)
        forged_final["message_type"] = "Task065PreactivationChainAdmission"
        forged_final["status"] = "PREACTIVATION_CHAIN_ADMITTED"
        assert not validator.is_valid(forged_final)

    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_VALIDATION_ID$",
    ):
        replace(direct, record_id="owner@example.com")


def test_schema_and_code_share_signed_64_bit_revision_ceiling() -> None:
    fixture = _fixture()
    _set(fixture, ("canonical_readback", "canonical_revision"), 2**63)
    validator = Draft202012Validator(_schemas()[2])
    assert not validator.is_valid(fixture)
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_FIXTURE_BOUNDS$",
    ):
        PreactivationChainConsumerPort(_plan()).validate(fixture)


def test_public_receipt_id_is_bound_to_the_plan_and_private_join() -> None:
    fixture = _fixture()
    _set(
        fixture,
        ("public_receipt", "receipt_id"),
        "rcpt_ffffffffffffffffffffffffffffffff",
    )
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_PUBLIC_RECEIPT_ID_MISMATCH$",
    ):
        PreactivationChainConsumerPort(_plan()).validate(fixture)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("record_id", "player_account"),
        ("operation_id", "token_sk_live_secret"),
        ("install_instance_id", "C:\\Users\\owner\\bridge"),
        ("profile_id", "player＠example.com"),
        ("record_id", "rec_0000000000000000000000000000000g"),
        ("record_id", "op_00000000000000000000000000000001"),
    ],
)
def test_plan_rejects_nonopaque_or_sensitive_identifier_values(
    field: str, value: str
) -> None:
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_PLAN_ID$",
    ):
        replace(_plan(), **{field: value})


def test_schema_rejects_sensitive_fixture_identifier_before_validation() -> None:
    fixture = _fixture()
    _set(fixture, ("public_receipt", "receipt_id"), "owner@example.com")
    validator = Draft202012Validator(_schemas()[2])
    assert not validator.is_valid(fixture)
    port = PreactivationChainConsumerPort(_plan())
    with pytest.raises(MontageLearningProductionLinkageError) as raised:
        port.validate(fixture)
    assert str(raised.value) == "ERR_TASK065_PUBLIC_RECEIPT_ID"
    assert "owner@example.com" not in str(raised.value)


@pytest.mark.parametrize(
    ("path", "wrong_prefix_id"),
    [
        (("operation_id",), "rec_00000000000000000000000000000001"),
        (("install_instance_id",), "op_00000000000000000000000000000001"),
        (("adapter_stage", "record_id"), "prof_00000000000000000000000000000001"),
        (("public_receipt", "receipt_id"), "op_00000000000000000000000000000001"),
        (("profile_readback", "profile_id"), "rec_00000000000000000000000000000001"),
    ],
)
def test_schema_rejects_cross_kind_identifier_prefixes(
    path: tuple[str, ...], wrong_prefix_id: str
) -> None:
    fixture = _fixture()
    _set(fixture, path, wrong_prefix_id)
    assert not Draft202012Validator(_schemas()[2]).is_valid(fixture)


def test_consumer_is_one_shot_after_success() -> None:
    port = PreactivationChainConsumerPort(_plan())
    port.validate(_fixture())
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_CONSUMER_ALREADY_USED$",
    ):
        port.validate(_fixture())
    assert port.state == "COMPLETED"


def test_failure_burns_consumer_and_error_is_body_free() -> None:
    fixture = _fixture()
    fixture["phase"] = "POST_ACTIVATION:C:\\private\\owner"
    port = PreactivationChainConsumerPort(_plan())
    with pytest.raises(MontageLearningProductionLinkageError) as raised:
        port.validate(fixture)
    assert str(raised.value) == "ERR_TASK065_FIXTURE_CONTRACT"
    assert "private" not in str(raised.value)
    assert port.state == "FAILED_CLOSED"
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_CONSUMER_ALREADY_USED$",
    ):
        port.validate(_fixture())


@pytest.mark.parametrize(
    ("path", "value", "code"),
    [
        (("adapter_stage", "invocation_count"), 2, "ERR_TASK065_STAGE_COUNT"),
        (("task036_import", "invocation_count"), 0, "ERR_TASK065_IMPORT_COUNT"),
        (("task036_import", "status"), "REJECTED", "ERR_TASK065_IMPORT_STATUS"),
        (("public_receipt", "status"), "DUPLICATE", "ERR_TASK065_RECEIPT_STATUS"),
        (("adapter_stage", "operation_id"), "wrong-op", "ERR_TASK065_OPERATION_MISMATCH"),
        (("adapter_stage", "config_sha256"), _sha("wrong"), "ERR_TASK065_CONFIG_MISMATCH"),
        (("adapter_stage", "adapter_build_sha256"), _sha("wrong"), "ERR_TASK065_ADAPTER_BUILD_MISMATCH"),
        (("adapter_stage", "receipt_sha256"), _sha("wrong"), "ERR_TASK065_STAGE_RECEIPT_MISMATCH"),
        (("task036_import", "receipt_sha256"), _sha("wrong"), "ERR_TASK065_IMPORT_RECEIPT_MISMATCH"),
        (("task061b_completion_receipt_sha256",), _sha("wrong"), "ERR_TASK065_RECEIPT_MISMATCH"),
        (("public_receipt", "receipt_sha256"), _sha("wrong"), "ERR_TASK065_PUBLIC_RECEIPT_MISMATCH"),
        (("hidden_correlation", "correlation_sha256"), _sha("wrong"), "ERR_TASK065_CORRELATION_MISMATCH"),
        (("canonical_readback", "readback_sha256"), _sha("wrong"), "ERR_TASK065_CANONICAL_MISMATCH"),
        (("profile_readback", "profile_sha256"), _sha("wrong"), "ERR_TASK065_PROFILE_MISMATCH"),
        (("canonical_readback", "durable_readback_verified"), False, "ERR_TASK065_CANONICAL_NOT_DURABLE"),
        (("profile_readback", "durable_readback_verified"), False, "ERR_TASK065_PROFILE_NOT_DURABLE"),
        (("profile_readback", "advisory_only"), False, "ERR_TASK065_PROFILE_AUTHORITY"),
        (("profile_readback", "auto_apply_authorized"), True, "ERR_TASK065_PROFILE_AUTHORITY"),
        (("evidence_complete",), False, "ERR_TASK065_EVIDENCE_INCOMPLETE"),
        (("authority_created",), True, "ERR_TASK065_AUTHORITY_CLAIM"),
        (("task072_design_sha256",), _sha("wrong-task072-design"), "ERR_TASK065_FIXTURE_CONTRACT"),
    ],
)
def test_mismatch_matrix_fails_closed(
    path: tuple[str, ...], value: object, code: str
) -> None:
    fixture = _fixture()
    _set(fixture, path, value)
    port = PreactivationChainConsumerPort(_plan())
    with pytest.raises(MontageLearningProductionLinkageError, match=f"^{code}$"):
        port.validate(fixture)
    assert port.state == "FAILED_CLOSED"


def test_receipt_only_or_status_only_fixture_is_ineligible() -> None:
    fixture = _fixture()
    fixture.pop("hidden_correlation")
    fixture.pop("canonical_readback")
    fixture.pop("profile_readback")
    fixture["canonical_store_written"] = True
    port = PreactivationChainConsumerPort(_plan())
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_FIXTURE_SHAPE$",
    ):
        port.validate(fixture)
    assert port.state == "FAILED_CLOSED"


def test_bounded_snapshot_rejects_before_hashing() -> None:
    fixture = _fixture()
    fixture["extra"] = "x" * 4096
    port = PreactivationChainConsumerPort(_plan())
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_FIXTURE_BOUNDS$",
    ):
        port.validate(fixture)
    assert port.state == "FAILED_CLOSED"


def test_mapping_subclass_is_rejected() -> None:
    class FixtureDict(dict[str, object]):
        pass

    port = PreactivationChainConsumerPort(_plan())
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_FIXTURE_TYPE$",
    ):
        port.validate(FixtureDict(_fixture()))
    assert port.state == "FAILED_CLOSED"


def test_concurrent_double_call_has_one_validation() -> None:
    port = PreactivationChainConsumerPort(_plan())

    def call() -> str:
        try:
            return port.validate(_fixture()).to_dict()["status"]  # type: ignore[return-value]
        except MontageLearningProductionLinkageError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(lambda _item: call(), range(2)))

    assert results == [
        "ERR_TASK065_CONSUMER_ALREADY_USED",
        "SYNTHETIC_FIXTURE_VALIDATED",
    ]
    assert port.state == "COMPLETED"
