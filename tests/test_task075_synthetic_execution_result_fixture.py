from __future__ import annotations

from copy import copy, deepcopy
from dataclasses import FrozenInstanceError, replace

import pytest

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task073_owner_voice_local_wav_composition import (
    OwnerVoiceLocalWavCompositionV4,
    RECEIPT_ALLOWLIST,
    RECEIPT_SLOTS,
)
import ai_video_production.task075_synthetic_execution_result_fixture as task075
from ai_video_production.task075_synthetic_execution_result_fixture import (
    PRODUCER_STATE,
    RECEIPT_FIELDS,
    RECEIPT_TYPE,
    SCHEMA_VERSION,
    TASK_OWNER,
    Task075SyntheticExecutionResultFixture,
)

NOW = "2026-09-06T01:00:00Z"
RECEIPT_OBSERVED_AT = "2026-09-06T00:30:00Z"


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def make_fixture() -> Task075SyntheticExecutionResultFixture:
    return Task075SyntheticExecutionResultFixture.create(
        opaque_ref="receipt.inference.synthetic.unknown.1",
        producer_build_sha256=digest("task075-build"),
        project_id="project.alpha",
        project_manifest_sha256=digest("manifest"),
        installed_session_sha256=digest("install"),
        operation_plan_sha256=digest("operation"),
        quick_clone_flow_sha256=digest("quick-head"),
        revision=1,
        head_sha256=digest("inference-head"),
        observed_at=RECEIPT_OBSERVED_AT,
    )


def generic_receipt(slot: str) -> dict[str, object]:
    owner, receipt_type, version = RECEIPT_ALLOWLIST[slot]
    states = {
        "installed_session": "READY",
        "quick_clone": "ACTIVE",
        "selection": "SELECTED",
        "reference": "PREPARED_VERIFIED",
        "call_profile": "READY_FOR_TASK075_DISPATCH",
        "compute_admission": "ADMITTED",
        "human_plan": "CONFIRMED",
        "operation_ticket": "ISSUED",
        "durable_job": "SUCCEEDED",
    }
    operation = None if slot in {"installed_session", "quick_clone", "selection", "reference"} else digest("operation")
    quick = None if slot == "installed_session" else digest("quick-head")
    expiry = "2026-09-06T02:00:00Z" if slot in {
        "reference",
        "call_profile",
        "compute_admission",
        "human_plan",
        "operation_ticket",
        "durable_job",
    } else None
    return {
        "owner_task": owner,
        "receipt_type": receipt_type,
        "schema_version": version,
        "opaque_ref": f"receipt.{slot}.1",
        "receipt_sha256": digest("receipt-" + slot),
        "producer_build_sha256": digest("build-" + slot),
        "producer_state": states[slot],
        "candidate_id": None,
        "candidate_sha256": None,
        "project_id": "project.alpha",
        "project_manifest_sha256": digest("manifest"),
        "installed_session_sha256": digest("install"),
        "operation_plan_sha256": operation,
        "quick_clone_flow_sha256": quick,
        "revision": 1,
        "head_sha256": digest("quick-head") if slot == "quick_clone" else digest("head-" + slot),
        "observed_at": RECEIPT_OBSERVED_AT,
        "expires_at": expiry,
        "current": True,
        "fixture_only": False,
        "authority_created": True,
        "production_eligible": True,
    }


def test_fixture_has_exact_body_free_unknown_identity_and_round_trips() -> None:
    fixture = make_fixture()
    value = fixture.to_dict()

    assert tuple(value) == RECEIPT_FIELDS
    assert (value["owner_task"], value["receipt_type"], value["schema_version"]) == (
        TASK_OWNER,
        RECEIPT_TYPE,
        SCHEMA_VERSION,
    )
    assert value["producer_state"] == PRODUCER_STATE == "UNKNOWN"
    assert value["candidate_id"] is None
    assert value["candidate_sha256"] is None
    assert value["expires_at"] is None
    assert value["current"] is True
    assert value["fixture_only"] is True
    assert value["authority_created"] is False
    assert value["production_eligible"] is False
    assert Task075SyntheticExecutionResultFixture.from_dict(value).to_dict() == value


def test_receipt_hash_is_domain_separated_and_tamper_evident() -> None:
    value = make_fixture().to_dict()
    payload = {field: value[field] for field in RECEIPT_FIELDS if field != "receipt_sha256"}
    assert value["receipt_sha256"] == sha256_bytes(
        canonical_json_bytes(
            {
                "domain": "TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1.receipt_sha256.v1",
                "receipt": payload,
            }
        )
    )

    for field, replacement in (
        ("opaque_ref", "receipt.inference.synthetic.unknown.2"),
        ("head_sha256", digest("other-head")),
        ("revision", 2),
    ):
        tampered = deepcopy(value)
        tampered[field] = replacement
        with pytest.raises(ValueError, match="receipt_sha256"):
            Task075SyntheticExecutionResultFixture.from_dict(tampered)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    (
        ("owner_task", "TASK-014", "identity"),
        ("receipt_type", "OTHER_RECEIPT", "identity"),
        ("schema_version", 2, "identity"),
        ("producer_state", "SUCCESS", "identity"),
        ("candidate_id", "candidate.alpha", "cannot identify"),
        ("candidate_sha256", digest("candidate"), "cannot identify"),
        ("expires_at", "2026-09-06T02:00:00Z", "cannot declare"),
        ("current", False, "must be current"),
        ("fixture_only", False, "fixture-only"),
        ("authority_created", True, "create authority"),
        ("production_eligible", True, "production eligible"),
    ),
)
def test_deserialized_receipt_cannot_change_fixed_state(field: str, replacement: object, message: str) -> None:
    value = make_fixture().to_dict()
    value[field] = replacement
    with pytest.raises(ValueError, match=message):
        Task075SyntheticExecutionResultFixture.from_dict(value)


def test_unknown_missing_and_reordered_fields_are_rejected() -> None:
    value = make_fixture().to_dict()
    value["private_audio_path"] = "private.wav"
    with pytest.raises(ValueError, match="unknown, or reordered"):
        Task075SyntheticExecutionResultFixture.from_dict(value)

    value = make_fixture().to_dict()
    value.pop("head_sha256")
    with pytest.raises(ValueError, match="incomplete"):
        Task075SyntheticExecutionResultFixture.from_dict(value)

    value = make_fixture().to_dict()
    reordered = {
        "receipt_type": value["receipt_type"],
        "owner_task": value["owner_task"],
        **{key: item for key, item in value.items() if key not in {"owner_task", "receipt_type"}},
    }
    with pytest.raises(ValueError, match="reordered"):
        Task075SyntheticExecutionResultFixture.from_dict(reordered)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    (
        ("opaque_ref", "C:/private/audio.wav", "location"),
        ("project_id", "../other-project", "location"),
        ("producer_build_sha256", "not-a-digest", "sha256"),
        ("installed_session_sha256", None, "invalid"),
        ("revision", True, "positive"),
        ("revision", 0, "positive"),
        ("observed_at", "2026-09-06T01:00:00+00:00", "RFC3339"),
    ),
)
def test_identifiers_coordinates_and_time_are_strict(field: str, replacement: object, message: str) -> None:
    value = make_fixture().to_dict()
    value[field] = replacement
    if field not in {"receipt_sha256"} and replacement is not None:
        value["receipt_sha256"] = digest("forged-rehash")
    with pytest.raises(ValueError, match=message):
        Task075SyntheticExecutionResultFixture.from_dict(value)


def test_frozen_model_and_defensive_copies_do_not_allow_promotion() -> None:
    fixture = make_fixture()
    with pytest.raises(FrozenInstanceError):
        fixture._value = {}  # type: ignore[misc]
    with pytest.raises(TypeError):
        fixture._value["authority_created"] = True  # type: ignore[index]
    with pytest.raises(ValueError, match="production eligible"):
        replace(fixture, _value={**fixture.to_dict(), "production_eligible": True})

    copied = copy(fixture)
    leaked = copied.to_dict()
    leaked["authority_created"] = True
    assert fixture.to_dict()["authority_created"] is False
    assert copied.to_dict()["authority_created"] is False


def test_task073_composition_derives_unknown_and_preserves_fixture_taint() -> None:
    receipts: dict[str, dict[str, object] | None] = {slot: None for slot in RECEIPT_SLOTS}
    for slot in (
        "installed_session",
        "quick_clone",
        "reference",
        "selection",
        "call_profile",
        "compute_admission",
        "human_plan",
        "operation_ticket",
        "durable_job",
    ):
        receipts[slot] = generic_receipt(slot)
    receipts["inference"] = make_fixture().to_dict()

    result = OwnerVoiceLocalWavCompositionV4.create(
        composition_id="task073.composition.synthetic-unknown.1",
        composition_revision=1,
        parent_composition_sha256=None,
        observed_at=NOW,
        project_id="project.alpha",
        project_manifest_revision=4,
        project_manifest_sha256=digest("manifest"),
        installed_session_sha256=digest("install"),
        operation_plan_sha256=digest("operation"),
        receipts=receipts,
        derived_state="UNKNOWN",
    ).to_dict()

    assert result["derived_state"] == "UNKNOWN"
    assert result["reason_codes"] == []
    assert result["receipts"]["inference"] == make_fixture().to_dict()
    assert result["fixture_lineage"]["fixture_only"] is True
    assert result["fixture_lineage"]["authority_created"] is False
    assert result["fixture_lineage"]["production_eligible"] is False
    assert result["fixture_lineage"]["producer_fixture_count"] == 1


def test_module_exposes_no_execution_or_private_payload_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    touched: list[str] = []
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: touched.append("open"))

    assert task075.__all__ == [
        "PRODUCER_STATE",
        "RECEIPT_FIELDS",
        "RECEIPT_TYPE",
        "SCHEMA_VERSION",
        "TASK_OWNER",
        "Task075SyntheticExecutionResultFixture",
    ]
    value = make_fixture().to_dict()
    Task075SyntheticExecutionResultFixture.from_dict(value)
    assert touched == []
    assert not any(
        token in key.lower()
        for key in value
        for token in ("path", "audio", "waveform", "transcript", "secret", "provider")
    )
