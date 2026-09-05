from __future__ import annotations

from collections.abc import Iterator, Mapping
import hashlib
import json

import pytest

from ai_video_production.task046_q2_q3_handoff_contract import (
    AUTHORITY_KIND,
    BLOCKING_REASON_CODES,
    CONTRACT_VERSION,
    DATA_PREPARATION_SCOPE,
    PRODUCT_BINDING_STATE,
    PUBLIC_RECORD_TYPE,
    Q3_ADMISSION_STATE,
    Task046Q2Q3HandoffFixture,
    public_projection,
)


def digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("ascii")).hexdigest()


def fixture() -> Task046Q2Q3HandoffFixture:
    return Task046Q2Q3HandoffFixture.create(
        fixture_id="fixture:q2-q3:1",
        project_id="project:owner-voice",
        owner_subject_binding_sha256=digest("owner-subject"),
        data_preparation_consent_sha256=digest("data-preparation-consent"),
        q1_capture_chain_terminal_receipt_sha256=digest("q1-terminal"),
        q2_operation_id="operation:q2-finish:1",
        q2_idempotency_key="idempotency:q2-finish:1",
        processed_asset_ref="asset:processed:1",
        processed_asset_revision_sha256=digest("processed-revision"),
        processed_asset_checksum_sha256=digest("processed-checksum"),
        processed_sample_count=96_000,
        processed_custody_receipt_sha256=digest("processed-custody"),
        processed_task003_adoption_receipt_sha256=digest("processed-adoption"),
        processed_task003_current_readback_sha256=digest("processed-readback"),
        training_copy_asset_ref="asset:training-copy:1",
        training_copy_asset_revision_sha256=digest("training-revision"),
        training_copy_asset_checksum_sha256=digest("training-checksum"),
        training_copy_sample_count=96_000,
        training_copy_custody_receipt_sha256=digest("training-custody"),
        training_copy_task003_adoption_receipt_sha256=digest("training-adoption"),
        training_copy_task003_current_readback_sha256=digest("training-readback"),
        quality_receipt_sha256=digest("quality"),
        speech_continuous_receipt_sha256=digest("speech-continuous"),
        range_map_receipt_sha256=digest("range-map"),
        sample_map_receipt_sha256=digest("sample-map"),
        policy_sha256=digest("policy"),
        analyzer_sha256=digest("analyzer"),
        producer_code_sha256=digest("producer-code"),
        runtime_sha256=digest("runtime"),
        created_at="2026-09-05T00:00:00Z",
    )


def test_positive_fixture_is_canonical_immutable_and_round_trips() -> None:
    value = fixture()
    raw = value.to_dict()

    assert raw["contract_version"] == CONTRACT_VERSION
    assert raw["authority_kind"] == AUTHORITY_KIND
    assert raw["data_preparation_scope"] == DATA_PREPARATION_SCOPE
    assert raw["q2_durable_owner_binding_state"] == PRODUCT_BINDING_STATE
    assert raw["q2_product_terminal_state"] == PRODUCT_BINDING_STATE
    assert raw["q3_admission_state"] == Q3_ADMISSION_STATE
    assert raw["reason_codes"] == list(BLOCKING_REASON_CODES)
    assert raw["owner_audio_used"] is False
    assert raw["external_effect_count"] == 0
    assert raw["product_authority"] is False
    assert raw["canonical_producer_receipt"] is False
    assert raw["q2_product_terminal_receipt_sha256"] is None
    assert raw["q2_publication_readback_sha256"] is None
    assert raw["q2_currentness_readback_sha256"] is None
    assert Task046Q2Q3HandoffFixture.from_dict(raw).to_dict() == raw
    assert json.loads(value.canonical_bytes()) == raw

    with pytest.raises(TypeError):
        value._data["project_id"] = "project:changed"  # type: ignore[index]


def test_direct_and_subclass_construction_are_forbidden() -> None:
    with pytest.raises(TypeError, match="create/from_dict"):
        Task046Q2Q3HandoffFixture({})

    class PromotedFixture(Task046Q2Q3HandoffFixture):
        pass

    with pytest.raises(TypeError, match="subclass"):
        PromotedFixture.from_dict(fixture().to_dict())


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("authority_kind", "OWNER_HUMAN_GATE"),
        ("intended_q2_owner", "TASK-046"),
        ("intended_q3_owner", "TASK-048"),
        ("synthetic_input_only", False),
        ("synthetic_input_only", 1),
        ("owner_audio_used", True),
        ("owner_audio_used", 0),
        ("external_effect_count", 1),
        ("external_effect_count", False),
        ("product_authority", True),
        ("product_authority", 0),
        ("canonical_producer_receipt", True),
        ("q2_durable_owner_binding_state", "BOUND_VERIFIED"),
        ("q2_product_terminal_state", "BOUND_VERIFIED"),
        ("replay", True),
        ("q3_admission_state", "READY_FOR_Q3"),
        ("host_path_present", True),
        ("filename_present", True),
        ("audio_body_present", True),
        ("transcript_body_present", True),
        ("prompt_body_present", True),
        ("secret_present", True),
        ("device_identity_present", True),
        ("voice_fingerprint_present", True),
    ],
)
def test_authority_effect_and_privacy_markers_fail_closed(
    field: str,
    replacement: object,
) -> None:
    raw = fixture().to_dict()
    raw[field] = replacement
    with pytest.raises(ValueError):
        Task046Q2Q3HandoffFixture.from_dict(raw)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("data_preparation_scope", "OWNER_VOICE_CAPTURE"),
        ("data_preparation_decision", "DENY"),
        ("training_copy_format", "FLOAT32_48000_MONO"),
        ("training_copy_sample_rate_hz", 44_100),
        ("training_copy_sample_rate_hz", False),
        ("training_copy_channel_count", 2),
        ("training_copy_channel_count", True),
        ("training_copy_bit_depth", 16),
        ("processed_sample_count", 0),
        ("training_copy_sample_count", True),
        ("created_at", "2026-09-05 00:00:00Z"),
        ("created_at", "2026-09-05T00:00:00+09:00"),
    ],
)
def test_consent_format_sample_and_time_mismatch_fail_closed(
    field: str,
    replacement: object,
) -> None:
    raw = fixture().to_dict()
    raw[field] = replacement
    with pytest.raises(ValueError):
        Task046Q2Q3HandoffFixture.from_dict(raw)


@pytest.mark.parametrize(
    "field",
    [
        "q2_product_terminal_receipt_sha256",
        "q2_publication_readback_sha256",
        "q2_currentness_readback_sha256",
    ],
)
def test_unbound_fixture_cannot_invent_product_receipts(field: str) -> None:
    raw = fixture().to_dict()
    raw[field] = digest("6")
    with pytest.raises(ValueError, match="cannot invent Product receipts"):
        Task046Q2Q3HandoffFixture.from_dict(raw)


def test_processed_and_training_asset_identity_cannot_collapse() -> None:
    raw = fixture().to_dict()
    raw["training_copy_asset_ref"] = raw["processed_asset_ref"]
    with pytest.raises(ValueError, match="identities must differ"):
        Task046Q2Q3HandoffFixture.from_dict(raw)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("processed_asset_ref", "C:/private/owner.wav"),
        ("processed_asset_ref", "C:private\\owner.wav"),
        ("processed_asset_ref", "owner.wav"),
        ("processed_asset_ref", "file:/private/owner.wav"),
        ("processed_asset_ref", "asset:processed:C:/private/owner.wav"),
        ("processed_asset_ref", "asset:processed:owner.wav"),
        ("training_copy_asset_ref", "../private.wav"),
        ("q2_operation_id", "https://private.example/operation"),
        ("project_id", "/absolute/private"),
    ],
)
def test_host_or_private_path_shaped_identifiers_are_rejected(
    field: str,
    replacement: str,
) -> None:
    raw = fixture().to_dict()
    raw[field] = replacement
    with pytest.raises(ValueError, match="logical identifier"):
        Task046Q2Q3HandoffFixture.from_dict(raw)


def test_missing_unknown_bad_digest_and_receipt_tamper_are_rejected() -> None:
    raw = fixture().to_dict()
    raw.pop("quality_receipt_sha256")
    with pytest.raises(ValueError, match="incomplete or unknown"):
        Task046Q2Q3HandoffFixture.from_dict(raw)

    raw = fixture().to_dict()
    raw["unknown"] = False
    with pytest.raises(ValueError, match="incomplete or unknown"):
        Task046Q2Q3HandoffFixture.from_dict(raw)

    raw = fixture().to_dict()
    raw["runtime_sha256"] = "not-a-digest"
    with pytest.raises(ValueError, match="runtime_sha256"):
        Task046Q2Q3HandoffFixture.from_dict(raw)

    raw = fixture().to_dict()
    raw["fixture_receipt_sha256"] = digest("7")
    with pytest.raises(ValueError, match="fixture_receipt_sha256 mismatch"):
        Task046Q2Q3HandoffFixture.from_dict(raw)


def test_typed_receipt_digest_relabel_is_rejected() -> None:
    raw = fixture().to_dict()
    raw["processed_custody_receipt_sha256"] = raw[
        "processed_task003_adoption_receipt_sha256"
    ]
    with pytest.raises(ValueError, match="must not alias"):
        Task046Q2Q3HandoffFixture.from_dict(raw)


def test_reason_codes_are_exact_and_cannot_claim_partial_unblock() -> None:
    raw = fixture().to_dict()
    raw["reason_codes"] = list(reversed(BLOCKING_REASON_CODES))
    with pytest.raises(ValueError, match="exact blocked state"):
        Task046Q2Q3HandoffFixture.from_dict(raw)

    raw = fixture().to_dict()
    raw["reason_codes"] = list(BLOCKING_REASON_CODES[1:])
    with pytest.raises(ValueError, match="exact blocked state"):
        Task046Q2Q3HandoffFixture.from_dict(raw)


def test_public_projection_is_body_free_and_always_blocked() -> None:
    projection = public_projection(fixture())

    assert projection == {
        "record_type": PUBLIC_RECORD_TYPE,
        "contract_version": CONTRACT_VERSION,
        "authority_kind": AUTHORITY_KIND,
        "intended_q2_owner": "TASK-048",
        "intended_q3_owner": "TASK-046",
        "q2_durable_owner_binding_state": PRODUCT_BINDING_STATE,
        "q2_product_terminal_state": PRODUCT_BINDING_STATE,
        "q3_admission_state": Q3_ADMISSION_STATE,
        "reason_codes": list(BLOCKING_REASON_CODES),
        "owner_audio_used": False,
        "external_effect_count": 0,
        "product_authority": False,
        "canonical_producer_receipt": False,
        "host_path_present": False,
        "audio_body_present": False,
        "transcript_body_present": False,
    }
    forbidden = {
        "fixture_id",
        "project_id",
        "processed_asset_ref",
        "training_copy_asset_ref",
        "owner_subject_binding_sha256",
        "data_preparation_consent_sha256",
        "fixture_receipt_sha256",
        "created_at",
    }
    assert forbidden.isdisjoint(projection)


def test_public_projection_revalidates_mapping_input() -> None:
    raw = fixture().to_dict()
    raw["product_authority"] = True
    with pytest.raises(ValueError):
        public_projection(raw)


def test_stateful_mapping_cannot_change_authority_after_validation() -> None:
    class FlippingMapping(Mapping[str, object]):
        def __init__(self, value: dict[str, object]) -> None:
            self._value = value
            self.product_authority_reads = 0

        def __getitem__(self, key: str) -> object:
            if key == "product_authority":
                self.product_authority_reads += 1
                return self.product_authority_reads != 1
            return self._value[key]

        def __iter__(self) -> Iterator[str]:
            return iter(self._value)

        def __len__(self) -> int:
            return len(self._value)

    source = FlippingMapping(fixture().to_dict())
    accepted = Task046Q2Q3HandoffFixture.from_dict(source)

    assert source.product_authority_reads == 1
    assert accepted.to_dict()["product_authority"] is False
