from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import fields, replace
import json
from pathlib import Path
import re

import pytest
from jsonschema import Draft202012Validator

import ai_video_production.montage_learning_production_linkage as production_linkage
from ai_video_production.montage_learning_production_linkage import (
    COMMON_INSTALLED_CONTRACT,
    COMMON_INSTALLED_MODE,
    COMMON_INSTALLED_VALIDATED_STATUS,
    COMMON_INSTALLED_VALIDATION_MESSAGE_TYPE,
    CommonInstalledDiscoveryFixtureConsumerPort,
    CommonInstalledDiscoveryFixturePlan,
    MontageLearningProductionLinkageError,
    PreactivationChainConsumerPort,
    PreactivationChainPlan,
    PreactivationFixtureValidation,
    TASK072_DESIGN_SHA256,
)
from ai_video_production.serialization import sha256_bytes


def _sha(label: str) -> str:
    return sha256_bytes(label.encode("ascii"))


def _common_fixture() -> dict[str, object]:
    path = (
        Path(__file__).parents[1]
        / "docs"
        / "ai-team"
        / "tasks"
        / "TASK-065"
        / "p0l-common-installed-discovery-receipt-fixture-v1.json"
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def _d2s_handoff_fixture() -> dict[str, object]:
    """Read the task-local D2S placeholder strictly as non-authoritative data."""
    path = (
        Path(__file__).parents[1]
        / "docs"
        / "ai-team"
        / "tasks"
        / "TASK-065"
        / "d2s-001-completion-handoff-fixture-v1.json"
    )
    raw = path.read_bytes()
    assert raw.startswith(b"{")

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate fixture key")
            value[key] = item
        return value

    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_duplicates,
        parse_constant=lambda _item: (_ for _ in ()).throw(
            ValueError("non-finite fixture number")
        ),
    )
    assert type(value) is dict
    return value


def _l3_crosswalk() -> str:
    path = (
        Path(__file__).parents[1]
        / "docs"
        / "ai-team"
        / "tasks"
        / "TASK-065"
        / "l3-one-way-receipt-crosswalk-2026-09-02.md"
    )
    return path.read_text(encoding="utf-8")


def _common_plan(
    fixture: dict[str, object] | None = None,
) -> CommonInstalledDiscoveryFixturePlan:
    source = _common_fixture() if fixture is None else fixture
    coordinates = source["expected_coordinates"]
    assert type(coordinates) is dict
    return CommonInstalledDiscoveryFixturePlan(**coordinates)


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
        "fixture_only": True,
        "native_broker_executed": False,
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
    assert result["fixture_only"] is True
    assert result["native_broker_executed"] is False
    rendered = json.dumps(result, sort_keys=True)
    assert plan.hidden_correlation_sha256 not in rendered
    assert "C:\\" not in rendered
    assert "ProgramData" not in rendered


def test_d2s_handoff_placeholder_requires_separate_v2_receipt_and_has_no_effect() -> None:
    fixture = _d2s_handoff_fixture()
    placeholder = fixture["d2s_interface_rebind_placeholder"]
    join = fixture["expected_preactivation_join"]
    assert type(placeholder) is dict
    assert type(join) is dict

    assert fixture["fixture_only"] is True
    assert fixture["authority_created"] is False
    assert fixture["real_stage_started"] is False
    assert fixture["task036_import_started"] is False
    assert fixture["terminal_query_started"] is False
    assert fixture["interface_completion_readback_verified"] is False
    assert fixture["operation_terminal_handoff_verified"] is False
    assert fixture["task069_canonical_task_present"] is False
    assert fixture["task069_completion_receipt_present"] is False
    assert fixture["task067_canonical_task_present"] is False
    assert fixture["task067_completion_receipt_present"] is False
    assert fixture["pl_a_effect_authorized"] is False
    assert fixture["pl_b_source_started"] is False
    assert fixture["pl_c_source_started"] is False
    assert fixture["pl_d_source_started"] is False

    assert placeholder["required_issuer"] == "CANONICAL_SKILL_D2S_OWNER"
    assert placeholder["required_message_type"] == (
        "D2S_001_INTERFACE_COMPLETION_READBACK_V1"
    )
    assert placeholder["required_schema_version"] == "1.0.0"
    assert placeholder["final_source_commit"] is None
    assert placeholder["canonical_source_tree_sha256"] is None
    assert placeholder["installed_bytes_sha256"] is None
    assert placeholder["rebind_required"] is True
    assert placeholder["fixture_never_rebound"] is True
    assert placeholder["placeholder_is_completion_receipt"] is False
    assert placeholder["placeholder_is_effect_authority"] is False

    observed = fixture["observed_canonical_source"]
    assert type(observed) is dict
    assert observed == {
        "canonical_main_head": "1646a2e9f3f0cb0a468dd52e564093bde04f49de",
        "canonical_skill_tree_sha256": (
            "4c3269e00bb934edc15cd58b73eca06c8846b2ed7104e3fa8573e6441ad47dc2"
        ),
        "source_to_main_diff": "NONE",
        "pl_a_source_identity_only": True,
        "read_only_observation": True,
        "installed_bytes_current_verified": False,
        "interface_completion_receipt_present": False,
        "operation_terminal_handoff_present": False,
        "observation_is_effect_authority": False,
    }

    task067 = fixture["task067_completion_receipt_placeholder"]
    assert type(task067) is dict
    assert task067 == {
        "required_issuer": "TASK067_CANONICAL_OWNER",
        "required_message_type": "TASK067_GENERIC_FACADE_COMPLETION_V1",
        "required_schema_version": "1.0.0",
        "canonical_task_main_head": None,
        "generic_facade_abi_sha256": None,
        "generic_manifest_snapshot_sha256": None,
        "journal_terminal_snapshot_sha256": None,
        "task061a_prepare_receipt_sha256": None,
        "task067_completion_receipt_sha256": None,
        "rebind_required": True,
        "canonical_task_absent": True,
        "placeholder_is_completion_receipt": False,
        "placeholder_is_effect_authority": False,
    }

    upstream = fixture["upstream_receipt_placeholders"]
    assert type(upstream) is dict
    assert upstream == {
        "task061a_prepare": {
            "required_issuer": "TASK061_CANONICAL_OWNER",
            "required_message_type": "TASK061_PREACTIVATION_PREPARE_V1",
            "required_schema_version": "1.0.0",
            "receipt_sha256": None,
            "enabled_must_remain_false": True,
            "placeholder_is_effect_authority": False,
        },
        "task036_private_dispatch_handoff": {
            "required_issuer": "TASK036_CANONICAL_OWNER",
            "required_message_type": "TASK036_D2S_EXECUTION_HANDOFF_V1",
            "required_schema_version": "1.0.0",
            "receipt_sha256": None,
            "consumer_readable": False,
            "placeholder_is_completion_receipt": False,
            "placeholder_is_effect_authority": False,
        },
        "d2s_operation_terminal_handoff": {
            "required_issuer": "CANONICAL_SKILL_D2S_OWNER",
            "required_message_type": "D2S_001_OPERATION_TERMINAL_HANDOFF_V1",
            "required_schema_version": "1.0.0",
            "receipt_sha256": None,
            "consumer_readable": True,
            "placeholder_is_completion_receipt": False,
            "placeholder_is_effect_authority": False,
        },
        "task061b_final": {
            "required_issuer": "TASK061_CANONICAL_OWNER",
            "required_message_type": "TASK061_FINAL_CA_C_COMPLETION_V1",
            "required_schema_version": "1.0.0",
            "receipt_sha256": None,
            "enabled_must_remain_false": True,
            "placeholder_is_effect_authority": False,
        },
        "task069_terminal": {
            "required_issuer": "TASK069_CANONICAL_OWNER",
            "required_message_type": "TASK069_D2S_TERMINAL_READBACK_V1",
            "required_schema_version": "1.0.0",
            "receipt_sha256": None,
            "canonical_task_absent": True,
            "placeholder_is_effect_authority": False,
        },
    }

    m1 = fixture["m1_import_consumer_placeholder"]
    assert type(m1) is dict
    assert m1 == {
        "required_message_type": "TASK065_M1_IMPORT_CONSUMER_VALIDATION_V1",
        "required_schema_version": "1.0.0",
        "task067_receipt_sha256": None,
        "d2s_terminal_handoff_sha256": None,
        "task061b_receipt_sha256": None,
        "task069_receipt_sha256": None,
        "canonical_task067_allocation_present": False,
        "consumer_execution_started": False,
        "authority_created": False,
    }

    v2 = placeholder["required_operation_config_v2"]
    assert type(v2) is dict
    assert v2 == {
        "schema_version": "2.0.0",
        "sealed_snapshot_required": True,
        "raw_bytes_sha256": None,
        "canonical_bytes_sha256": None,
        "physical_identity_digest": None,
        "raw_path_or_capability_present": False,
    }
    assert join["d2s_interface_completion_receipt"] == (
        "REQUIRED_SEPARATE_PINNED_INPUT"
    )
    assert join["task067_completion_receipt"] == (
        "NOT_AVAILABLE_CANONICAL_TASK_ABSENT"
    )
    assert join["task069_completion_receipt"] == (
        "NOT_AVAILABLE_CANONICAL_TASK_ABSENT"
    )
    assert join["operation_config_v2_snapshot"] == (
        "REQUIRED_SEPARATE_PINNED_INPUT"
    )
    assert join["task036_private_dispatch_handoff"] == (
        "NOT_A_TASK065_CONSUMER_INPUT"
    )
    assert join["d2s_operation_terminal_handoff"] == "REQUIRED_CURRENT"
    assert join["task065_invokes_adapter"] is False
    assert join["task065_invokes_task036"] is False
    assert join["fixture_participates_in_runtime_join"] is False
    assert join["acceptance_status_before_rebind"] == "PREACTIVATION_CHAIN.N.C."


def test_l3_crosswalk_preserves_one_way_receipt_consumption_and_effect_zero() -> None:
    crosswalk = _l3_crosswalk()
    for required in (
        "TASK-068 -> {TASK-069 U1a-c, TASK-063} -> TASK-060",
        "TASK-061-A prepare (enabled:false) -> TASK-067",
        "TASK-036 private exact-one operation",
        "D2S operation terminal handoff -> TASK-061-B final CA-C (enabled:false)",
        "TASK-065 PL-A validation reader",
        "TASK069_U1A_C.N.C. / EFFECT0",
        "TASK067_CANONICAL_ALLOCATION.N.C. / EFFECT0",
        "TASK036_HANDOFF.N.C. / EFFECT0",
        "PREACTIVATION_CHAIN.N.C. / EFFECT0",
        "TASK065_M1_IMPORT_CONSUMER_VALIDATION_V1",
    ):
        assert required in crosswalk
    assert "`TASK036_D2S_EXECUTION_HANDOFF_V1` never crosses" in crosswalk
    assert "do not read, compare, copy or deserialize the private dispatch handoff" in crosswalk
    assert "no additional design pr may be created" in crosswalk.lower()
    assert "PR #467 is the only carrier, and it is not merge authority" in crosswalk
    assert "`authority_created:false`" in crosswalk
    assert "Read/join only: adapter, TASK-036, install, config, Profile, history and Activation deltas are all zero." in crosswalk
    assert (
        "src/ai_video_production/montage_learning_canonical_admission_transaction.py"
        in crosswalk
    )
    assert "no other TASK-058 path is allowed" in crosswalk


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

    common_fixture = _common_fixture()
    common_validation = CommonInstalledDiscoveryFixtureConsumerPort(
        _common_plan(common_fixture)
    ).validate(common_fixture).to_dict()
    validator.validate(common_fixture)
    validator.validate(common_validation)

    authority_claim = deepcopy(common_fixture)
    _set(authority_claim, ("effects", "installed_discovery_started"), True)
    assert not validator.is_valid(authority_claim)

    forged_lease = dict(common_validation)
    forged_lease["currentness_lease_created"] = True
    assert not validator.is_valid(forged_lease)


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
        (("fixture_only",), False, "ERR_TASK065_NOT_FIXTURE"),
        (("native_broker_executed",), True, "ERR_TASK065_NATIVE_BROKER_CLAIM"),
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


def test_common_installed_fixture_port_validates_without_creating_authority() -> None:
    fixture = _common_fixture()
    before = deepcopy(fixture)
    plan = _common_plan(fixture)
    plan_projection = plan.to_dict()
    port = CommonInstalledDiscoveryFixtureConsumerPort(plan)

    result = port.validate(fixture).to_dict()

    assert fixture == before
    assert port.state == "COMPLETED"
    assert plan_projection["contract"] == COMMON_INSTALLED_CONTRACT
    assert plan_projection["mode"] == COMMON_INSTALLED_MODE
    assert plan_projection["authority_created"] is False
    assert plan_projection["currentness_selected"] is False
    assert plan_projection["local_effects_authorized"] is False
    assert result["message_type"] == COMMON_INSTALLED_VALIDATION_MESSAGE_TYPE
    assert result["status"] == COMMON_INSTALLED_VALIDATED_STATUS
    assert result["fixture_only"] is True
    for field in (
        "authority_created",
        "currentness_selected",
        "currentness_lease_created",
        "lane_effect_authority_created",
        "task063_completion_receipt_present",
        "task072_implementation_receipt_verified",
        "installed_snapshot_verified",
        "native_broker_executed",
        "installed_discovery_started",
        "packaged_exe_started",
        "adapter_stage_started",
        "task036_import_started",
        "wav_body_read",
        "provider_started",
        "install_started",
        "release_started",
        "deploy_started",
        "production_activation_started",
    ):
        assert result[field] is False
    assert result["p0_l_status"] == "NOT_CONFIRMED"
    assert result["p0_e_status"] == "NOT_CONFIRMED"
    assert result["p0_v_status"] == "NOT_CONFIRMED"
    rendered = json.dumps(result, sort_keys=True)
    assert "INSTALLED_STARTUP_CONTEXT_V1" not in rendered
    assert "C:\\" not in rendered
    assert "ProgramData" not in rendered


@pytest.mark.parametrize(
    ("path", "value", "code"),
    [
        (("authority_created",), True, "ERR_TASK065_COMMON_AUTHORITY_CLAIM"),
        (("currentness_selected",), True, "ERR_TASK065_COMMON_AUTHORITY_CLAIM"),
        (("installed_snapshot_verified",), True, "ERR_TASK065_COMMON_AUTHORITY_CLAIM"),
        (("effects", "packaged_exe_started"), True, "ERR_TASK065_COMMON_EFFECT_CLAIM"),
        (("lanes", "P0_L", "task065_adapter_call_count"), False, "ERR_TASK065_COMMON_LANE_CLAIM"),
        (("lanes", "P0_E", "packaged_exe_started"), True, "ERR_TASK065_COMMON_LANE_CLAIM"),
        (("lanes", "P0_V", "wav_body_read"), True, "ERR_TASK065_COMMON_LANE_CLAIM"),
        (("public_diagnostics", "secret_count"), 1, "ERR_TASK065_COMMON_DIAGNOSTIC_CLAIM"),
        (("expected_coordinates", "product_exe_sha256"), "https://invalid", "ERR_TASK065_COMMON_COORDINATE_DIGEST"),
        (("expected_coordinates", "install_instance_id"), "inst_ffffffffffffffffffffffffffffffff", "ERR_TASK065_COMMON_COORDINATE_MISMATCH"),
    ],
)
def test_common_installed_fixture_port_rejects_claims_and_mismatches(
    path: tuple[str, ...], value: object, code: str
) -> None:
    fixture = _common_fixture()
    plan = _common_plan(fixture)
    _set(fixture, path, value)
    port = CommonInstalledDiscoveryFixtureConsumerPort(plan)
    with pytest.raises(MontageLearningProductionLinkageError, match=f"^{code}$"):
        port.validate(fixture)
    assert port.state == "FAILED_CLOSED"


@pytest.mark.parametrize(
    ("path", "value", "code"),
    [
        (
            ("lanes", "P0_L", "expected_historical_adapter_stage_count"),
            1.0,
            "ERR_TASK065_FIXTURE_TYPE",
        ),
        (
            ("lanes", "P0_L", "task065_adapter_call_count"),
            0.0,
            "ERR_TASK065_FIXTURE_TYPE",
        ),
        (
            ("public_diagnostics", "absolute_path_count"),
            0.0,
            "ERR_TASK065_FIXTURE_TYPE",
        ),
    ],
)
def test_common_installed_schema_and_source_both_reject_float_counts(
    path: tuple[str, ...], value: object, code: str
) -> None:
    fixture = _common_fixture()
    plan = _common_plan(fixture)
    _set(fixture, path, value)
    assert not Draft202012Validator(_schemas()[2]).is_valid(fixture)
    port = CommonInstalledDiscoveryFixtureConsumerPort(plan)
    with pytest.raises(MontageLearningProductionLinkageError, match=f"^{code}$"):
        port.validate(fixture)
    assert port.state == "FAILED_CLOSED"


def test_common_installed_snapshot_never_recanonicalizes_mutable_original(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _common_fixture()
    plan = _common_plan(fixture)
    canonical_json_bytes = production_linkage.canonical_json_bytes

    def reject_original(value: object) -> bytes:
        if value is fixture:
            raise AssertionError("mutable caller tree was canonicalized")
        return canonical_json_bytes(value)

    monkeypatch.setattr(production_linkage, "canonical_json_bytes", reject_original)
    result = CommonInstalledDiscoveryFixtureConsumerPort(plan).validate(fixture)
    assert result.to_dict()["status"] == COMMON_INSTALLED_VALIDATED_STATUS


def test_common_installed_fixture_port_is_one_shot_and_failure_burns() -> None:
    fixture = _common_fixture()
    port = CommonInstalledDiscoveryFixtureConsumerPort(_common_plan(fixture))
    port.validate(fixture)
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_COMMON_CONSUMER_ALREADY_USED$",
    ):
        port.validate(fixture)

    failed_fixture = _common_fixture()
    failed_fixture["contract"] = "wrong"
    failed = CommonInstalledDiscoveryFixtureConsumerPort(_common_plan())
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_COMMON_FIXTURE_CONTRACT$",
    ):
        failed.validate(failed_fixture)
    assert failed.state == "FAILED_CLOSED"
    with pytest.raises(
        MontageLearningProductionLinkageError,
        match="^ERR_TASK065_COMMON_CONSUMER_ALREADY_USED$",
    ):
        failed.validate(_common_fixture())


def test_common_installed_fixture_port_concurrent_use_validates_once() -> None:
    fixture = _common_fixture()
    port = CommonInstalledDiscoveryFixtureConsumerPort(_common_plan(fixture))

    def call() -> str:
        try:
            return port.validate(deepcopy(fixture)).to_dict()["status"]  # type: ignore[return-value]
        except MontageLearningProductionLinkageError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(lambda _item: call(), range(2)))
    assert results == [
        "ERR_TASK065_COMMON_CONSUMER_ALREADY_USED",
        COMMON_INSTALLED_VALIDATED_STATUS,
    ]
    assert port.state == "COMPLETED"


def test_common_installed_discovery_receipt_fixture_is_closed_effect_zero() -> None:
    fixture_path = (
        Path(__file__).parents[1]
        / "docs"
        / "ai-team"
        / "tasks"
        / "TASK-065"
        / "p0l-common-installed-discovery-receipt-fixture-v1.json"
    )
    raw_bytes = fixture_path.read_bytes()

    def parse_fixture(data: bytes) -> dict[str, object]:
        if len(data) > 8192:
            raise ValueError("fixture byte bounds")
        if data.startswith(b"\xef\xbb\xbf"):
            raise ValueError("fixture BOM")
        try:
            body = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("fixture UTF-8") from exc

        def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate fixture key")
                result[key] = value
            return result

        parsed = json.loads(
            body,
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite fixture number")
            ),
        )
        if type(parsed) is not dict:
            raise ValueError("fixture root type")

        item_count = 0

        def visit(value: object, depth: int) -> None:
            nonlocal item_count
            item_count += 1
            if item_count > 128 or depth > 5:
                raise ValueError("fixture tree bounds")
            if type(value) is dict:
                if len(value) > 24:  # type: ignore[arg-type]
                    raise ValueError("fixture tree bounds")
                for key, child in value.items():  # type: ignore[union-attr]
                    if type(key) is not str or len(key) > 64:
                        raise ValueError("fixture key bounds")
                    visit(child, depth + 1)
            elif type(value) is str:
                if len(value) > 128 or len(value.encode("utf-8")) > 256:
                    raise ValueError("fixture string bounds")
                if any(ord(character) < 32 for character in value):
                    raise ValueError("fixture string control")
            elif type(value) not in {bool, int}:
                raise ValueError("fixture value type")

        visit(parsed, 0)
        return parsed

    fixture = parse_fixture(raw_bytes)
    with pytest.raises(ValueError, match="^duplicate fixture key$"):
        parse_fixture(b'{"mode":"safe","mode":"unsafe"}')
    with pytest.raises(ValueError, match="^non-finite fixture number$"):
        parse_fixture(b'{"effect":NaN}')
    with pytest.raises(ValueError, match="^fixture BOM$"):
        parse_fixture(b"\xef\xbb\xbf{}")
    with pytest.raises(ValueError, match="^fixture byte bounds$"):
        parse_fixture(b'{"value":"' + (b"x" * 8192) + b'"}')
    deep: dict[str, object] = {"leaf": 0}
    for _index in range(7):
        deep = {"child": deep}
    with pytest.raises(ValueError, match="^fixture tree bounds$"):
        parse_fixture(json.dumps(deep).encode("utf-8"))

    assert set(fixture) == {
        "fixture_version",
        "contract",
        "mode",
        "fixture_only",
        "authority_created",
        "currentness_selected",
        "task063_completion_receipt_present",
        "task072_design_receipt_sha256",
        "task072_implementation_receipt_verified",
        "installed_snapshot_verified",
        "native_broker_executed",
        "expected_coordinates",
        "effects",
        "lanes",
        "public_diagnostics",
    }
    assert fixture["fixture_version"] == "1.0"
    assert fixture["contract"] == (
        "TASK065-P0L-COMMON-INSTALLED-DISCOVERY-RECEIPT-V1"
    )
    assert fixture["mode"] == "SYNTHETIC_EXPECTED_COORDINATES"
    assert fixture["task072_design_receipt_sha256"] == TASK072_DESIGN_SHA256

    coordinates = fixture["expected_coordinates"]
    assert type(coordinates) is dict
    assert set(coordinates) == {
        "install_instance_id",
        "descriptor_generation_id",
        "product_build_sha256",
        "package_payload_sha256",
        "product_exe_sha256",
        "owner_manifest_sha256",
        "task036_receipt_id",
        "task061b_receipt_id",
    }
    assert re.fullmatch(r"inst_[0-9a-f]{32}", coordinates["install_instance_id"])
    assert re.fullmatch(
        r"desc_[0-9a-f]{32}", coordinates["descriptor_generation_id"]
    )
    for field in (
        "product_build_sha256",
        "package_payload_sha256",
        "product_exe_sha256",
        "owner_manifest_sha256",
    ):
        assert re.fullmatch(r"[0-9a-f]{64}", coordinates[field])
    for field in ("task036_receipt_id", "task061b_receipt_id"):
        assert re.fullmatch(r"receipt_[0-9a-f]{32}", coordinates[field])

    for field in (
        "authority_created",
        "currentness_selected",
        "task063_completion_receipt_present",
        "task072_implementation_receipt_verified",
        "installed_snapshot_verified",
        "native_broker_executed",
    ):
        assert fixture[field] is False
    assert fixture["fixture_only"] is True
    effects = fixture["effects"]
    assert type(effects) is dict
    assert set(effects) == {
        "installed_discovery_started",
        "packaged_exe_started",
        "adapter_stage_started",
        "task036_import_started",
        "wav_body_read",
        "provider_started",
        "install_started",
        "release_started",
        "deploy_started",
        "production_activation_started",
    }
    assert all(type(value) is bool and value is False for value in effects.values())

    lanes = fixture["lanes"]
    assert type(lanes) is dict
    assert set(lanes) == {"P0_L", "P0_E", "P0_V"}
    assert set(lanes["P0_L"]) == {
        "status",
        "expected_historical_adapter_stage_count",
        "expected_historical_task036_import_count",
        "task065_adapter_call_count",
        "task065_task036_call_count",
        "task065_project_delta",
        "task065_bridge_delta",
        "task065_profile_delta",
        "task065_config_history_delta",
    }
    assert set(lanes["P0_E"]) == {
        "status",
        "installed_package_readback_verified",
        "packaged_exe_started",
        "first_run_readback_verified",
        "startup_settings_readback_verified",
    }
    assert set(lanes["P0_V"]) == {
        "status",
        "wav_receipt_verified",
        "wav_body_read",
        "media_qa_executed",
        "provider_started",
    }
    assert all(lane["status"] == "NOT_CONFIRMED" for lane in lanes.values())
    assert lanes["P0_L"]["expected_historical_adapter_stage_count"] == "1"
    assert lanes["P0_L"]["expected_historical_task036_import_count"] == "1"
    assert all(
        lanes["P0_L"][field] == "0"
        for field in (
            "task065_adapter_call_count",
            "task065_task036_call_count",
            "task065_project_delta",
            "task065_bridge_delta",
            "task065_profile_delta",
            "task065_config_history_delta",
        )
    )
    assert lanes["P0_E"]["packaged_exe_started"] is False
    assert all(
        type(value) is bool and value is False
        for field, value in lanes["P0_E"].items()
        if field != "status"
    )
    assert lanes["P0_V"]["wav_body_read"] is False
    assert lanes["P0_V"]["provider_started"] is False
    assert all(
        type(value) is bool and value is False
        for field, value in lanes["P0_V"].items()
        if field != "status"
    )

    string_values: list[str] = []

    def collect_strings(value: object) -> None:
        if type(value) is dict:
            for child in value.values():
                collect_strings(child)
        elif type(value) is str:
            string_values.append(value)

    collect_strings(fixture)
    for value in string_values:
        assert not re.search(r"[A-Za-z]:[\\/]", value)
        assert not value.startswith("\\\\")
        assert not re.search(r"(?:https?|file)://", value, re.IGNORECASE)
        assert not re.search(r"\bS-\d-", value, re.IGNORECASE)
        assert not re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+", value)
        assert not re.search(
            r"(?:account|secret|token|correlation_sha256|transcript)",
            value,
            re.IGNORECASE,
        )

    diagnostics = fixture["public_diagnostics"]
    assert type(diagnostics) is dict
    assert set(diagnostics) == {
        "code",
        "absolute_path_count",
        "private_body_count",
        "secret_count",
        "os_detail_count",
    }
    assert diagnostics["code"] == "NOT_CONFIRMED"
    assert all(
        diagnostics[field] == "0"
        for field in (
            "absolute_path_count",
            "private_body_count",
            "secret_count",
            "os_detail_count",
        )
    )

    def validate_negative_candidate(candidate: dict[str, object]) -> None:
        candidate_effects = candidate["effects"]
        candidate_lanes = candidate["lanes"]
        candidate_coordinates = candidate["expected_coordinates"]
        candidate_diagnostics = candidate["public_diagnostics"]
        assert type(candidate_effects) is dict
        assert type(candidate_lanes) is dict
        assert type(candidate_coordinates) is dict
        assert type(candidate_diagnostics) is dict
        assert set(candidate_effects) == set(effects)
        assert all(
            type(value) is bool and value is False
            for value in candidate_effects.values()
        )
        assert set(candidate_lanes) == set(lanes)
        for lane_name in lanes:
            assert set(candidate_lanes[lane_name]) == set(lanes[lane_name])
        assert (
            candidate_lanes["P0_L"]["expected_historical_adapter_stage_count"]
            == "1"
        )
        assert (
            candidate_lanes["P0_L"]["expected_historical_task036_import_count"]
            == "1"
        )
        assert all(
            candidate_lanes["P0_L"][field] == "0"
            for field in (
                "task065_adapter_call_count",
                "task065_task036_call_count",
                "task065_project_delta",
                "task065_bridge_delta",
                "task065_profile_delta",
                "task065_config_history_delta",
            )
        )
        assert all(
            type(value) is bool and value is False
            for field, value in candidate_lanes["P0_E"].items()
            if field != "status"
        )
        assert all(
            type(value) is bool and value is False
            for field, value in candidate_lanes["P0_V"].items()
            if field != "status"
        )
        for field in (
            "product_build_sha256",
            "package_payload_sha256",
            "product_exe_sha256",
            "owner_manifest_sha256",
        ):
            assert re.fullmatch(r"[0-9a-f]{64}", candidate_coordinates[field])
        assert candidate_diagnostics["code"] == "NOT_CONFIRMED"
        assert all(
            candidate_diagnostics[field] == "0"
            for field in (
                "absolute_path_count",
                "private_body_count",
                "secret_count",
                "os_detail_count",
            )
        )

    bad = deepcopy(fixture)
    bad["effects"]["unknown_effect"] = False
    with pytest.raises(AssertionError):
        validate_negative_candidate(bad)
    bad = deepcopy(fixture)
    bad["lanes"]["P0_V"]["hidden_correlation"] = "opaque"
    with pytest.raises(AssertionError):
        validate_negative_candidate(bad)
    bad = deepcopy(fixture)
    bad["lanes"]["P0_E"]["packaged_exe_started"] = True
    with pytest.raises(AssertionError):
        validate_negative_candidate(bad)
    bad = deepcopy(fixture)
    bad["lanes"]["P0_L"]["task065_adapter_call_count"] = False
    with pytest.raises(AssertionError):
        validate_negative_candidate(bad)
    for sensitive in (
        "C:\\private\\product.exe",
        "\\\\host\\share",
        "https://invalid.example",
        "owner@example.invalid",
        "S-1-5-21-0000",
        "secret-token-value",
        "correlation_sha256",
        "transcript body",
    ):
        bad = deepcopy(fixture)
        bad["expected_coordinates"]["product_exe_sha256"] = sensitive
        with pytest.raises(AssertionError):
            validate_negative_candidate(bad)
    bad = deepcopy(fixture)
    bad["public_diagnostics"]["code"] = 0
    bad["public_diagnostics"]["absolute_path_count"] = "NOT_CONFIRMED"
    with pytest.raises(AssertionError):
        validate_negative_candidate(bad)
