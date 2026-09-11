from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
import pickle

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task082_owner_voice_private_media_custody import (
    ArtifactClass,
    CompletionKind,
    CurrentnessState,
    GenerationEventKind,
    LeaseDecisionKind,
    LeaseCompletionReadback,
    LeaseState,
    PrivateMediaCustodyReceipt,
    PrivateMediaGenerationEvent,
    ReadPurpose,
    Task082ContractError,
    Task082Reason,
    WritePurpose,
    compile_fixture_read_lease_admission,
    compile_fixture_write_lease_admission,
    custody_staged_binding_sha256,
    derive_generation_currentness,
    mint_fixture_lease_sentinel,
    parse_custody_receipt,
    parse_generation_event,
    parse_strict_json,
    read_fixture_lease_state,
    transition_fixture_lease,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "task082-owner-voice-private-media-custody.schema.json"
MIRROR = (
    ROOT
    / "src"
    / "ai_video_production"
    / "schema_resources"
    / "task082-owner-voice-private-media-custody.schema.json"
)
T0 = "2026-09-06T00:00:00Z"
T1 = "2026-09-06T00:01:00Z"
T2 = "2026-09-06T00:02:00Z"
T9 = "2026-09-06T00:09:00Z"
T10 = "2026-09-06T00:10:00Z"


def h(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def published_event(
    *,
    event_revision: int = 1,
    generation_revision: int = 1,
    predecessor: str | None = None,
    artifact_class: ArtifactClass = ArtifactClass.RAW_CAPTURE,
    slot: str = "owner.voice.raw",
    subject: str | None = None,
    consent: str | None = None,
    purpose: str = "CAPTURE_RAW_PUBLISH",
    created_at: str = T0,
    observed_at: str = T1,
) -> PrivateMediaGenerationEvent:
    opaque_artifact_id = f"artifact.{generation_revision}"
    content_sha256 = h(f"content.{generation_revision}")
    media_metadata_sha256 = h(f"metadata.{generation_revision}")
    opened_physical_identity_sha256 = h(f"physical.{generation_revision}")
    cipher_backend_identity_sha256 = h("cipher")
    subject_sha256 = subject or h("subject")
    consent_sha256 = consent or h("consent")
    custody_binding = custody_staged_binding_sha256(
        opaque_artifact_id=opaque_artifact_id,
        logical_slot_ref=slot,
        generation_revision=generation_revision,
        owner_subject_revision_sha256=subject_sha256,
        purpose=purpose,
        artifact_class=artifact_class,
        content_sha256=content_sha256,
        media_metadata_sha256=media_metadata_sha256,
        opened_physical_identity_sha256=opened_physical_identity_sha256,
        cipher_backend_identity_sha256=cipher_backend_identity_sha256,
        consent_rights_revision_sha256=consent_sha256,
        observed_at=observed_at,
        fresh_until=T10,
    )
    return PrivateMediaGenerationEvent.create(
        event_kind=GenerationEventKind.GENERATION_PUBLISHED,
        logical_slot_ref=slot,
        artifact_class=artifact_class,
        event_revision=event_revision,
        predecessor_event_sha256=predecessor,
        owner_subject_revision_sha256=subject_sha256,
        purpose=purpose,
        consent_rights_revision_sha256=consent_sha256,
        created_at=created_at,
        observed_at=observed_at,
        fresh_until=T10,
        trusted_time_binding_sha256=h("time"),
        published_generation_revision=generation_revision,
        opaque_artifact_id=opaque_artifact_id,
        custody_binding_sha256=custody_binding,
        content_sha256=content_sha256,
        media_metadata_sha256=media_metadata_sha256,
        opened_physical_identity_sha256=opened_physical_identity_sha256,
        cipher_backend_identity_sha256=cipher_backend_identity_sha256,
        target_generation_revision=None,
        target_publish_event_sha256=None,
        tombstone_decision_sha256=None,
    )


def tombstone_event(
    published: PrivateMediaGenerationEvent,
    *,
    event_revision: int = 2,
    kind: GenerationEventKind = GenerationEventKind.GENERATION_REVOKED,
) -> PrivateMediaGenerationEvent:
    return PrivateMediaGenerationEvent.create(
        event_kind=kind,
        logical_slot_ref=published.logical_slot_ref,
        artifact_class=published.artifact_class,
        event_revision=event_revision,
        predecessor_event_sha256=published.event_sha256,
        owner_subject_revision_sha256=published.owner_subject_revision_sha256,
        purpose=published.purpose,
        consent_rights_revision_sha256=published.consent_rights_revision_sha256,
        created_at=T1,
        observed_at=T2,
        fresh_until=T10,
        trusted_time_binding_sha256=h("time.2"),
        published_generation_revision=None,
        opaque_artifact_id=None,
        custody_binding_sha256=None,
        content_sha256=None,
        media_metadata_sha256=None,
        opened_physical_identity_sha256=None,
        cipher_backend_identity_sha256=None,
        target_generation_revision=published.published_generation_revision,
        target_publish_event_sha256=published.event_sha256,
        tombstone_decision_sha256=h(kind.value),
    )


def custody_receipt(
    published: PrivateMediaGenerationEvent,
    *,
    predecessor_receipt: str | None = None,
) -> PrivateMediaCustodyReceipt:
    assert published.published_generation_revision is not None
    if predecessor_receipt is None and published.published_generation_revision > 1:
        predecessor_receipt = h(f"receipt.{published.published_generation_revision - 1}")
    return PrivateMediaCustodyReceipt.create(
        opaque_artifact_id=published.opaque_artifact_id,
        logical_slot_ref=published.logical_slot_ref,
        generation_revision=published.published_generation_revision,
        predecessor_receipt_sha256=predecessor_receipt,
        custody_binding_sha256=published.custody_binding_sha256,
        owner_subject_revision_sha256=published.owner_subject_revision_sha256,
        purpose=published.purpose,
        artifact_class=published.artifact_class,
        content_sha256=published.content_sha256,
        media_metadata_sha256=published.media_metadata_sha256,
        opened_physical_identity_sha256=published.opened_physical_identity_sha256,
        cipher_backend_identity_sha256=published.cipher_backend_identity_sha256,
        consent_rights_revision_sha256=published.consent_rights_revision_sha256,
        generation_event_sha256=published.event_sha256,
        event_head_sha256=published.event_sha256,
        observed_at=T1,
        fresh_until=T10,
    )


def derive_currentness(
    events: list[PrivateMediaGenerationEvent | dict[str, object]],
    *,
    observed_at: str = T2,
    expected_head: str | None = None,
    expected_count: int | None = None,
    expected_custody: str | None | object = ...,
):
    last = events[-1]
    last_mapping = last.as_dict() if isinstance(last, PrivateMediaGenerationEvent) else last
    if expected_head is None:
        expected_head = str(last_mapping["event_sha256"])
    if expected_count is None:
        expected_count = len(events)
    if expected_custody is ...:
        expected_custody = (
            last_mapping["custody_binding_sha256"]
            if last_mapping["event_kind"] == GenerationEventKind.GENERATION_PUBLISHED.value
            else None
        )
    return derive_generation_currentness(
        events,
        observed_at=observed_at,
        expected_event_head_sha256=expected_head,
        expected_event_count=expected_count,
        expected_current_custody_binding_sha256=expected_custody,
    )


def assert_effect_zero(value: object) -> None:
    mapping = value.as_dict()  # type: ignore[attr-defined]
    assert mapping["fixture_only"] is True
    assert mapping["authority_created"] is False
    assert mapping["body_access_granted"] is False
    assert mapping["production_backend_invoked"] is False
    assert mapping["private_media_effect_count"] == 0
    serialized = json.dumps(mapping, sort_keys=True)
    for forbidden in ("private_audio", "transcript_body", "C:\\", "/home/", "secret_value"):
        assert forbidden not in serialized


def write_kwargs(purpose: WritePurpose = WritePurpose.CAPTURE_RAW_PUBLISH) -> dict[str, object]:
    matrix = {
        WritePurpose.CAPTURE_RAW_PUBLISH: (
            "TASK-047",
            ArtifactClass.RAW_CAPTURE,
            "OWNER_VOICE_CAPTURE",
            "TASK047_RAW_CAPTURE_OUTPUT",
        ),
        WritePurpose.CAPTURE_CANONICAL_PUBLISH: (
            "TASK-047",
            ArtifactClass.CANONICAL_PCM,
            "OWNER_VOICE_CAPTURE",
            "TASK047_CANONICAL_PCM_OUTPUT",
        ),
        WritePurpose.QUALITY_SPEECH_CONTINUOUS_PUBLISH: (
            "TASK-048",
            ArtifactClass.PROCESSED_SPEECH_CONTINUOUS,
            "OWNER_VOICE_DATA_PREPARATION",
            "TASK048_SPEECH_CONTINUOUS_OUTPUT",
        ),
        WritePurpose.QUALITY_TRAINING_COPY_PUBLISH: (
            "TASK-048",
            ArtifactClass.TRAINING_COPY,
            "OWNER_VOICE_DATA_PREPARATION",
            "TASK048_TRAINING_COPY_OUTPUT",
        ),
        WritePurpose.DATASET_REVIEW_TRANSCRIPT_PUBLISH: (
            "TASK-046",
            ArtifactClass.REVIEW_TRANSCRIPT,
            "OWNER_VOICE_DATA_PREPARATION",
            "TASK046_REVIEW_TRANSCRIPT_OUTPUT",
        ),
    }
    producer, artifact, consent_scope, output_role = matrix[purpose]
    return {
        "purpose": purpose,
        "expected_purpose": purpose,
        "producer_task": producer,
        "producer_output_role": output_role,
        "artifact_class": artifact,
        "operation_id": "operation.write.1",
        "expected_operation_id": "operation.write.1",
        "logical_slot_ref": "owner.voice.slot",
        "generation_revision": 1,
        "expected_generation_revision": 1,
        "owner_subject_revision_sha256": h("subject"),
        "expected_owner_subject_revision_sha256": h("subject"),
        "consent_scope": consent_scope,
        "consent_rights_revision_sha256": h("consent"),
        "expected_consent_rights_revision_sha256": h("consent"),
        "current_event_head_sha256": None,
        "expected_event_head_sha256": None,
        "producer_output_record_type": {
            WritePurpose.CAPTURE_RAW_PUBLISH: "Task047RawCaptureOutputV1",
            WritePurpose.CAPTURE_CANONICAL_PUBLISH: "Task047CanonicalPcmOutputV1",
            WritePurpose.QUALITY_SPEECH_CONTINUOUS_PUBLISH: "Task048SpeechContinuousOutputV1",
            WritePurpose.QUALITY_TRAINING_COPY_PUBLISH: "Task048TrainingCopyOutputV1",
            WritePurpose.DATASET_REVIEW_TRANSCRIPT_PUBLISH: "Task046ReviewTranscriptOutputV1",
        }[purpose],
        "expected_producer_output_record_type": {
            WritePurpose.CAPTURE_RAW_PUBLISH: "Task047RawCaptureOutputV1",
            WritePurpose.CAPTURE_CANONICAL_PUBLISH: "Task047CanonicalPcmOutputV1",
            WritePurpose.QUALITY_SPEECH_CONTINUOUS_PUBLISH: "Task048SpeechContinuousOutputV1",
            WritePurpose.QUALITY_TRAINING_COPY_PUBLISH: "Task048TrainingCopyOutputV1",
            WritePurpose.DATASET_REVIEW_TRANSCRIPT_PUBLISH: "Task046ReviewTranscriptOutputV1",
        }[purpose],
        "producer_output_receipt_sha256": h("producer"),
        "expected_producer_output_receipt_sha256": h("producer"),
        "producer_output_currentness_sha256": h("producer.current"),
        "expected_producer_output_currentness_sha256": h("producer.current"),
        "producer_output_current": True,
        "issued_at": T0,
        "expires_at": T10,
        "observed_at": T1,
    }


def read_kwargs(
    purpose: ReadPurpose = ReadPurpose.QUALITY_PROCESSING,
) -> dict[str, object]:
    artifacts = {
        ReadPurpose.QUALITY_PROCESSING: ArtifactClass.RAW_CAPTURE,
        ReadPurpose.DATASET_INTAKE: ArtifactClass.PROCESSED_SPEECH_CONTINUOUS,
        ReadPurpose.DATASET_REVIEW: ArtifactClass.REVIEW_TRANSCRIPT,
        ReadPurpose.VOICE_MODEL_TRAINING: ArtifactClass.TRAINING_COPY,
    }
    write_purposes = {
        ReadPurpose.QUALITY_PROCESSING: "CAPTURE_RAW_PUBLISH",
        ReadPurpose.DATASET_INTAKE: "QUALITY_SPEECH_CONTINUOUS_PUBLISH",
        ReadPurpose.DATASET_REVIEW: "DATASET_REVIEW_TRANSCRIPT_PUBLISH",
        ReadPurpose.VOICE_MODEL_TRAINING: "QUALITY_TRAINING_COPY_PUBLISH",
    }
    event = published_event(artifact_class=artifacts[purpose], purpose=write_purposes[purpose])
    receipt = custody_receipt(event)
    currentness = derive_currentness([event])
    consumer = "TASK-048" if purpose is ReadPurpose.QUALITY_PROCESSING else "TASK-046"
    needs_asset = purpose is not ReadPurpose.DATASET_REVIEW
    values: dict[str, object] = {
        "receipt": receipt,
        "currentness": currentness,
        "purpose": purpose,
        "expected_purpose": purpose,
        "consumer_task": consumer,
        "operation_id": "operation.read.1",
        "expected_operation_id": "operation.read.1",
        "expected_owner_subject_revision_sha256": h("subject"),
        "expected_consent_rights_revision_sha256": h("consent"),
        "issued_at": T0,
        "expires_at": T10,
        "observed_at": T2,
        "asset_adoption_readback_sha256": h("asset") if needs_asset else None,
        "expected_asset_adoption_readback_sha256": h("asset") if needs_asset else None,
    }
    if purpose is ReadPurpose.VOICE_MODEL_TRAINING:
        values.update(
            dataset_snapshot_sha256=h("dataset"),
            expected_dataset_snapshot_sha256=h("dataset"),
            durable_job_head_sha256=h("job"),
            expected_durable_job_head_sha256=h("job"),
            run_recipe_binding_sha256=h("run.recipe"),
            expected_run_recipe_binding_sha256=h("run.recipe"),
            h3_authorization_sha256=h("h3"),
            expected_h3_authorization_sha256=h("h3"),
            training_compound_operation_sha256=h("compound"),
            expected_training_compound_operation_sha256=h("compound"),
        )
    elif purpose is ReadPurpose.DATASET_REVIEW:
        values.update(
            dataset_review_binding_sha256=h("review.operation"),
            expected_dataset_review_binding_sha256=h("review.operation"),
        )
    else:
        values.update(
            producer_output_receipt_sha256=h("source.output"),
            expected_producer_output_receipt_sha256=h("source.output"),
        )
    return values


def completion_for(decision: object) -> LeaseCompletionReadback:
    if decision.lease_kind.value == "WRITE":  # type: ignore[attr-defined]
        return LeaseCompletionReadback.create(
            lease_kind=decision.lease_kind,  # type: ignore[attr-defined]
            operation_id=decision.operation_id,  # type: ignore[attr-defined]
            completion_kind=CompletionKind.WRITE_PUBLISH_PINNED_READBACK,
            write_publish_pinned_readback_sha256=h("publish.readback"),
            read_close_handle_identity_sha256=None,
            read_completion_readback_sha256=None,
        )
    return LeaseCompletionReadback.create(
        lease_kind=decision.lease_kind,  # type: ignore[attr-defined]
        operation_id=decision.operation_id,  # type: ignore[attr-defined]
        completion_kind=CompletionKind.READ_CLOSE_IDENTITY_COMPLETION_READBACK,
        write_publish_pinned_readback_sha256=None,
        read_close_handle_identity_sha256=h("close.identity"),
        read_completion_readback_sha256=h("completion.readback"),
    )


def test_schema_mirror_is_byte_identical_and_records_validate() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    event = published_event()
    receipt = custody_receipt(event)
    decision = compile_fixture_write_lease_admission(**write_kwargs())
    completion = completion_for(decision)
    for record in (event.as_dict(), receipt.as_dict(), decision.as_dict(), completion.as_dict()):
        assert list(validator.iter_errors(record)) == []
    wrong_binding = receipt.as_dict()
    wrong_binding["artifact_class"] = ArtifactClass.CANONICAL_PCM.value
    assert list(validator.iter_errors(wrong_binding))
    bool_version = receipt.as_dict()
    bool_version["schema_version"] = True
    assert list(validator.iter_errors(bool_version))
    invalid_identifier = decision.as_dict()
    invalid_identifier["operation_id"] = "owner..secret"
    assert list(validator.iter_errors(invalid_identifier))
    for invalid_values in (
        {
            "state": LeaseState.CONSUMED.value,
            "decision": LeaseDecisionKind.BLOCKED.value,
            "reason_code": Task082Reason.WRONG_SUBJECT.value,
        },
        {
            "state": LeaseState.PREPARED.value,
            "decision": LeaseDecisionKind.BLOCKED.value,
            "reason_code": Task082Reason.REPLAY.value,
        },
        {
            "state": LeaseState.EXPIRED.value,
            "decision": LeaseDecisionKind.BLOCKED.value,
            "reason_code": Task082Reason.WRONG_SUBJECT.value,
        },
        {
            "state": LeaseState.FAILED_CLOSED.value,
            "decision": LeaseDecisionKind.BLOCKED.value,
            "reason_code": Task082Reason.STALE_BINDING.value,
        },
    ):
        invalid_tuple = {**decision.as_dict(), **invalid_values}
        invalid_tuple["decision_sha256"] = sha256_bytes(
            b"TASK082_PRIVATE_MEDIA_LEASE_DECISION_V2\0"
            + canonical_json_bytes(
                {key: value for key, value in invalid_tuple.items() if key != "decision_sha256"}
            )
        )
        assert list(validator.iter_errors(invalid_tuple))


def test_schema_accepts_every_source_generated_lease_state_tuple() -> None:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    initial = compile_fixture_write_lease_admission(**write_kwargs())

    success = mint_fixture_lease_sentinel(initial)
    issued = transition_fixture_lease(success, LeaseState.ISSUED)
    opened = transition_fixture_lease(success, LeaseState.OPEN_STARTED)
    completion = completion_for(initial)
    consumed = transition_fixture_lease(
        success,
        LeaseState.CONSUMED,
        completion_readback=completion,
        expected_completion_readback_sha256=completion.completion_sha256,
    )

    expired_sentinel = mint_fixture_lease_sentinel(initial)
    expired = transition_fixture_lease(expired_sentinel, LeaseState.EXPIRED)
    failed_sentinel = mint_fixture_lease_sentinel(initial)
    failed = transition_fixture_lease(failed_sentinel, LeaseState.FAILED_CLOSED)
    unknown_sentinel = mint_fixture_lease_sentinel(initial)
    transition_fixture_lease(unknown_sentinel, LeaseState.ISSUED)
    transition_fixture_lease(unknown_sentinel, LeaseState.OPEN_STARTED)
    unknown = transition_fixture_lease(
        unknown_sentinel,
        LeaseState.CONSUMED,
        lost_reply=True,
    )

    for decision in (initial, issued, opened, consumed, expired, failed, unknown):
        assert list(validator.iter_errors(decision.as_dict())) == []


def test_receipt_and_event_round_trip_are_body_free() -> None:
    event = published_event()
    receipt = custody_receipt(event)
    assert parse_generation_event(canonical_json_bytes(event.as_dict())) == event
    assert parse_custody_receipt(canonical_json_bytes(receipt.as_dict())) == receipt
    assert event.event_sha256.startswith("sha256:")
    assert receipt.receipt_sha256.startswith("sha256:")
    assert "custody_receipt_sha256" not in event.as_dict()
    assert event.custody_binding_sha256 == receipt.custody_binding_sha256
    assert event.custody_binding_sha256 != receipt.receipt_sha256


@pytest.mark.parametrize("field,value", [
    ("record_type", "Other"),
    ("schema_version", 1),
    ("schema_version", True),
    ("canonical_owner_task", "TASK-014"),
    ("receipt_role", "PRIVATE_MEDIA_GENERATION_EVENT"),
])
def test_receipt_rejects_wrong_discriminator(field: str, value: object) -> None:
    mapping = custody_receipt(published_event()).as_dict()
    mapping[field] = value
    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaCustodyReceipt.from_mapping(mapping)
    assert caught.value.reason is Task082Reason.RECORD_DISCRIMINATOR_INVALID


def test_receipt_rejects_digest_tamper_and_private_or_path_fields_without_echo() -> None:
    mapping = custody_receipt(published_event()).as_dict()
    mapping["content_sha256"] = h("tampered")
    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaCustodyReceipt.from_mapping(mapping)
    assert caught.value.reason is Task082Reason.CUSTODY_BINDING_MISMATCH

    mapping = custody_receipt(published_event()).as_dict()
    mapping["receipt_sha256"] = h("tampered.receipt")
    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaCustodyReceipt.from_mapping(mapping)
    assert caught.value.reason is Task082Reason.RECEIPT_DIGEST_MISMATCH

    mapping = custody_receipt(published_event()).as_dict()
    private_value = "owner private transcript body"
    mapping["private_audio_body"] = private_value
    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaCustodyReceipt.from_mapping(mapping)
    assert str(caught.value) == Task082Reason.RECORD_FIELDS_INVALID.value
    assert private_value not in str(caught.value)

    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaCustodyReceipt.create(
            **{
                **{k: v for k, v in custody_receipt(published_event()).as_dict().items() if k not in {
                    "record_type", "schema_version", "canonical_owner_task", "receipt_role", "receipt_sha256"
                }},
                "opaque_artifact_id": "C:\\owner\\voice.wav",
            }
        )
    assert caught.value.reason is Task082Reason.IDENTIFIER_INVALID


@pytest.mark.parametrize("field,value", [
    ("record_type", "Other"),
    ("schema_version", 1),
    ("schema_version", True),
    ("canonical_owner_task", "TASK-014"),
    ("receipt_role", "PRIVATE_MEDIA_CUSTODY"),
])
def test_event_rejects_wrong_discriminator(field: str, value: object) -> None:
    mapping = published_event().as_dict()
    mapping[field] = value
    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaGenerationEvent.from_mapping(mapping)
    assert caught.value.reason is Task082Reason.RECORD_DISCRIMINATOR_INVALID


@pytest.mark.parametrize(
    "payload,reason",
    [
        (b'{"a":1,"a":2}', Task082Reason.JSON_DUPLICATE_KEY),
        (b'{"a":NaN}', Task082Reason.JSON_NONFINITE),
        (b'{} trailing', Task082Reason.JSON_INVALID),
        (b"\xef\xbb\xbf{}", Task082Reason.JSON_INVALID),
        (b"\xff", Task082Reason.JSON_INVALID),
        (b"[]", Task082Reason.JSON_INVALID),
    ],
)
def test_strict_json_rejects_ambiguous_inputs(payload: bytes, reason: Task082Reason) -> None:
    with pytest.raises(Task082ContractError) as caught:
        parse_strict_json(payload)
    assert caught.value.reason is reason


def test_strict_json_rejects_oversize_and_excess_depth() -> None:
    with pytest.raises(Task082ContractError) as caught:
        parse_strict_json(b'{"x":"' + b"a" * 66_000 + b'"}')
    assert caught.value.reason is Task082Reason.JSON_OVERSIZE

    nested: object = 0
    for _ in range(17):
        nested = {"x": nested}
    with pytest.raises(Task082ContractError) as caught:
        parse_strict_json(json.dumps(nested))
    assert caught.value.reason is Task082Reason.JSON_DEPTH_EXCEEDED


def test_strict_json_translates_parser_recursion_to_body_free_depth_error() -> None:
    payload = b'{"x":' + (b"[" * 1_200) + b"0" + (b"]" * 1_200) + b"}"

    with pytest.raises(Task082ContractError) as caught:
        parse_strict_json(payload)

    assert caught.value.reason is Task082Reason.JSON_DEPTH_EXCEEDED
    assert str(caught.value) == Task082Reason.JSON_DEPTH_EXCEEDED.value


def test_mapping_inputs_are_single_snapshot_and_exceptions_are_body_free() -> None:
    class OneReadMapping(dict[str, object]):
        def __init__(self, source: dict[str, object]):
            super().__init__(source)
            self.reads: dict[str, int] = {}

        def items(self):  # type: ignore[override]
            for key in super().keys():
                self.reads[key] = self.reads.get(key, 0) + 1
                if self.reads[key] > 1:
                    raise RuntimeError("D:\\private\\owner-voice.wav")
                yield key, super().__getitem__(key)

    event = published_event()
    source = OneReadMapping(custody_receipt(event).as_dict())
    parsed = PrivateMediaCustodyReceipt.from_mapping(source)
    assert parsed.logical_slot_ref == event.logical_slot_ref
    assert set(source.reads.values()) == {1}

    class RaisingMapping(dict[str, object]):
        def items(self):  # type: ignore[override]
            raise RuntimeError("D:\\private\\owner-transcript.txt")

    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaCustodyReceipt.from_mapping(RaisingMapping({}))
    assert caught.value.reason is Task082Reason.REQUEST_INVALID
    assert "owner-transcript" not in str(caught.value)

    values = read_kwargs()
    values["receipt"] = RaisingMapping({})
    decision = compile_fixture_read_lease_admission(**values)
    assert decision.reason_code is Task082Reason.REQUEST_INVALID
    serialized = json.dumps(decision.as_dict())
    assert "owner-transcript" not in serialized
    assert "D:\\\\" not in serialized


def test_generation_chain_publish_tombstone_republish() -> None:
    first = published_event()
    revoked = tombstone_event(first)
    second = published_event(
        event_revision=3,
        generation_revision=2,
        predecessor=revoked.event_sha256,
        created_at=T2,
        observed_at=T2,
    )
    current = derive_currentness([first, revoked, second])
    assert current.state is CurrentnessState.CURRENT
    assert current.current_generation_revision == 2
    assert current.current_publish_event_sha256 == second.event_sha256
    assert_effect_zero(current)


@pytest.mark.parametrize(
    "kind",
    [
        GenerationEventKind.GENERATION_REVOKED,
        GenerationEventKind.GENERATION_QUARANTINED,
        GenerationEventKind.GENERATION_EXPIRED,
    ],
)
def test_all_tombstones_remove_current_generation(kind: GenerationEventKind) -> None:
    first = published_event()
    result = derive_currentness([first, tombstone_event(first, kind=kind)])
    assert result.state is CurrentnessState.NO_CURRENT_GENERATION
    assert result.current_generation_revision is None
    assert_effect_zero(result)


@pytest.mark.parametrize(
    "events,reason",
    [
        (
            lambda first: [
                first,
                published_event(event_revision=3, generation_revision=2, predecessor=first.event_sha256),
            ],
            Task082Reason.EVENT_REVISION_GAP,
        ),
        (
            lambda first: [
                first,
                published_event(event_revision=2, generation_revision=2, predecessor=h("wrong")),
            ],
            Task082Reason.EVENT_PREDECESSOR_MISMATCH,
        ),
        (
            lambda first: [
                first,
                published_event(event_revision=2, generation_revision=3, predecessor=first.event_sha256),
            ],
            Task082Reason.PUBLISH_GENERATION_GAP,
        ),
        (
            lambda first: [
                first,
                published_event(
                    event_revision=2,
                    generation_revision=2,
                    predecessor=first.event_sha256,
                    slot="other.slot",
                ),
            ],
            Task082Reason.EVENT_LINEAGE_MISMATCH,
        ),
    ],
)
def test_generation_chain_rejects_gap_fork_rollback_and_cross_slot(events: object, reason: Task082Reason) -> None:
    first = published_event()
    result = derive_currentness(events(first))  # type: ignore[operator]
    assert result.state is CurrentnessState.CURRENTNESS_NOT_CONFIRMED
    assert result.reason_code is reason
    assert_effect_zero(result)


def test_generation_chain_rejects_wrong_tombstone_target_and_stale_event() -> None:
    first = published_event()
    wrong = tombstone_event(first).as_dict()
    wrong["target_generation_revision"] = 2
    wrong["event_sha256"] = sha256_bytes(
        b"TASK082_PRIVATE_MEDIA_GENERATION_EVENT_V2\0"
        + canonical_json_bytes({k: v for k, v in wrong.items() if k != "event_sha256"})
    )
    result = derive_currentness([first, wrong])
    assert result.reason_code is Task082Reason.TOMBSTONE_TARGET_MISMATCH

    stale = derive_currentness([first], observed_at="2026-09-06T00:11:00Z")
    assert stale.reason_code is Task082Reason.STALE_BINDING


def test_generation_chain_rejects_observation_rollback() -> None:
    first = published_event(observed_at=T2)
    second = published_event(
        event_revision=2,
        generation_revision=2,
        predecessor=first.event_sha256,
        observed_at=T1,
    )
    result = derive_currentness([first, second])
    assert result.state is CurrentnessState.CURRENTNESS_NOT_CONFIRMED
    assert result.reason_code is Task082Reason.TIMESTAMP_INVALID


def test_generation_chain_materializes_one_bounded_sequence_snapshot() -> None:
    event = published_event()

    class DriftingSequence(Sequence[object]):
        def __len__(self) -> int:
            return 2

        def __getitem__(self, index: int) -> object:
            if index == 0:
                return event
            raise IndexError

    result = derive_generation_currentness(
        DriftingSequence(),
        observed_at=T2,
        expected_event_head_sha256=event.event_sha256,
        expected_event_count=2,
        expected_current_custody_binding_sha256=event.custody_binding_sha256,
    )
    assert result.state is CurrentnessState.CURRENTNESS_NOT_CONFIRMED
    assert result.reason_code is Task082Reason.EVENT_REVISION_GAP
    assert result.source_event_count == 1


def test_generation_chain_sequence_failure_is_body_free() -> None:
    private = "D:\\Owner Secret\\speaker-fingerprint.wav"

    class RaisingSequence(Sequence[object]):
        def __len__(self) -> int:
            raise RuntimeError(private)

        def __getitem__(self, index: int) -> object:
            raise RuntimeError(private)

    result = derive_generation_currentness(
        RaisingSequence(),
        observed_at=T2,
        expected_event_head_sha256=h("expected.head"),
        expected_event_count=1,
        expected_current_custody_binding_sha256=h("expected.binding"),
    )
    assert result.state is CurrentnessState.CURRENTNESS_NOT_CONFIRMED
    assert result.reason_code is Task082Reason.CURRENTNESS_NOT_CONFIRMED
    assert private not in json.dumps(result.as_dict(), sort_keys=True)


def test_currentness_requires_trusted_complete_head_count_and_custody_binding() -> None:
    first = published_event()
    second = published_event(
        event_revision=2,
        generation_revision=2,
        predecessor=first.event_sha256,
        created_at=T2,
        observed_at=T2,
    )
    prefix = derive_generation_currentness(
        [first],
        observed_at=T2,
        expected_event_head_sha256=second.event_sha256,
        expected_event_count=2,
        expected_current_custody_binding_sha256=second.custody_binding_sha256,
    )
    assert prefix.state is CurrentnessState.CURRENTNESS_NOT_CONFIRMED

    wrong_custody = derive_generation_currentness(
        [first],
        observed_at=T2,
        expected_event_head_sha256=first.event_sha256,
        expected_event_count=1,
        expected_current_custody_binding_sha256=h("wrong.custody"),
    )
    assert wrong_custody.state is CurrentnessState.CURRENTNESS_NOT_CONFIRMED
    assert wrong_custody.reason_code is Task082Reason.EVENT_LINEAGE_MISMATCH


def test_fresh_until_is_exclusive_for_currentness_and_read_admission() -> None:
    event = published_event()
    currentness = derive_currentness([event], observed_at=T10)
    assert currentness.reason_code is Task082Reason.STALE_BINDING

    values = read_kwargs()
    values["observed_at"] = T10
    decision = compile_fixture_read_lease_admission(**values)
    assert decision.reason_code is Task082Reason.STALE_BINDING


def test_event_rejects_published_tombstone_field_mixing_and_hash_tamper() -> None:
    mapping = published_event().as_dict()
    mapping["target_generation_revision"] = 1
    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaGenerationEvent.from_mapping(mapping)
    assert caught.value.reason is Task082Reason.EVENT_VARIANT_FIELDS_INVALID

    mapping = published_event().as_dict()
    mapping["trusted_time_binding_sha256"] = h("tampered")
    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaGenerationEvent.from_mapping(mapping)
    assert caught.value.reason is Task082Reason.EVENT_DIGEST_MISMATCH


def test_event_rejects_media_identity_inconsistent_with_staged_custody_binding() -> None:
    mapping = published_event().as_dict()
    mapping["content_sha256"] = h("different.event.content")
    mapping["event_sha256"] = sha256_bytes(
        b"TASK082_PRIVATE_MEDIA_GENERATION_EVENT_V2\0"
        + canonical_json_bytes({key: value for key, value in mapping.items() if key != "event_sha256"})
    )

    with pytest.raises(Task082ContractError) as caught:
        PrivateMediaGenerationEvent.from_mapping(mapping)

    assert caught.value.reason is Task082Reason.CUSTODY_BINDING_MISMATCH


@pytest.mark.parametrize("purpose", list(WritePurpose))
def test_write_purpose_matrix_positive_is_fixture_only(purpose: WritePurpose) -> None:
    decision = compile_fixture_write_lease_admission(**write_kwargs(purpose))
    assert decision.reason_code is Task082Reason.READY
    assert decision.decision is LeaseDecisionKind.READY_FIXTURE_ONLY
    assert decision.state is LeaseState.PREPARED
    assert_effect_zero(decision)


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"expected_purpose": WritePurpose.CAPTURE_CANONICAL_PUBLISH}, Task082Reason.WRONG_PURPOSE),
        ({"expected_generation_revision": 2}, Task082Reason.WRONG_GENERATION),
        ({"producer_task": "TASK-046"}, Task082Reason.WRONG_PRODUCER),
        ({"producer_output_role": "TASK047_CANONICAL_PCM_OUTPUT"}, Task082Reason.WRONG_OUTPUT_ROLE),
        ({"producer_output_record_type": "Task047CanonicalPcmOutputV1"}, Task082Reason.WRONG_OUTPUT_ROLE),
        ({"producer_output_receipt_sha256": h("other")}, Task082Reason.STALE_BINDING),
        ({"producer_output_currentness_sha256": h("other")}, Task082Reason.STALE_BINDING),
        ({"producer_output_current": False}, Task082Reason.STALE_BINDING),
        ({"artifact_class": ArtifactClass.CANONICAL_PCM}, Task082Reason.WRONG_ARTIFACT_CLASS),
        ({"consent_scope": "OWNER_VOICE_DATA_PREPARATION"}, Task082Reason.WRONG_CONSENT),
        ({"consent_rights_revision_sha256": h("other")}, Task082Reason.WRONG_CONSENT),
        ({"owner_subject_revision_sha256": h("other")}, Task082Reason.WRONG_SUBJECT),
        ({"operation_id": "operation.other"}, Task082Reason.WRONG_OPERATION),
        ({"current_event_head_sha256": h("other")}, Task082Reason.STALE_BINDING),
        ({"revoked": True}, Task082Reason.REVOKED),
        ({"receipt_as_capability": True}, Task082Reason.RECEIPT_AS_CAPABILITY),
        ({"observed_at": T10}, Task082Reason.STALE_BINDING),
    ],
)
def test_write_admission_negative_vectors(change: dict[str, object], reason: Task082Reason) -> None:
    decision = compile_fixture_write_lease_admission(**{**write_kwargs(), **change})
    assert decision.reason_code is reason
    assert decision.decision is LeaseDecisionKind.BLOCKED
    assert_effect_zero(decision)


@pytest.mark.parametrize("purpose", list(ReadPurpose))
def test_read_purpose_matrix_positive_is_fixture_only(purpose: ReadPurpose) -> None:
    decision = compile_fixture_read_lease_admission(**read_kwargs(purpose))
    assert decision.reason_code is Task082Reason.READY
    assert decision.decision is LeaseDecisionKind.READY_FIXTURE_ONLY
    assert_effect_zero(decision)


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"expected_purpose": ReadPurpose.DATASET_INTAKE}, Task082Reason.WRONG_PURPOSE),
        ({"consumer_task": "TASK-046"}, Task082Reason.WRONG_CONSUMER),
        ({"operation_id": "operation.other"}, Task082Reason.WRONG_OPERATION),
        ({"expected_owner_subject_revision_sha256": h("other")}, Task082Reason.WRONG_SUBJECT),
        ({"expected_consent_rights_revision_sha256": h("other")}, Task082Reason.WRONG_CONSENT),
        ({"asset_adoption_readback_sha256": h("other")}, Task082Reason.WRONG_ASSET_ADOPTION),
        ({"asset_adoption_readback_sha256": "not-a-digest", "expected_asset_adoption_readback_sha256": "not-a-digest"}, Task082Reason.WRONG_ASSET_ADOPTION),
        ({"revoked": True}, Task082Reason.REVOKED),
        ({"receipt_as_capability": True}, Task082Reason.RECEIPT_AS_CAPABILITY),
        ({"observed_at": T10}, Task082Reason.STALE_BINDING),
    ],
)
def test_read_admission_negative_vectors(change: dict[str, object], reason: Task082Reason) -> None:
    decision = compile_fixture_read_lease_admission(**{**read_kwargs(), **change})
    assert decision.reason_code is reason
    assert decision.decision is LeaseDecisionKind.BLOCKED
    assert_effect_zero(decision)


def test_read_admission_rejects_cross_generation_and_missing_training_bindings() -> None:
    values = read_kwargs()
    first = published_event()
    second = published_event(
        event_revision=2,
        generation_revision=2,
        predecessor=first.event_sha256,
        created_at=T2,
        observed_at=T2,
    )
    values["currentness"] = derive_currentness([first, second])
    decision = compile_fixture_read_lease_admission(**values)
    assert decision.reason_code is Task082Reason.WRONG_GENERATION

    training = read_kwargs(ReadPurpose.VOICE_MODEL_TRAINING)
    training["h3_authorization_sha256"] = None
    decision = compile_fixture_read_lease_admission(**training)
    assert decision.reason_code is Task082Reason.REQUIRED_BINDING_MISSING


def test_dataset_review_rejects_asset_substitution() -> None:
    values = read_kwargs(ReadPurpose.DATASET_REVIEW)
    values["asset_adoption_readback_sha256"] = h("asset")
    values["expected_asset_adoption_readback_sha256"] = h("asset")
    decision = compile_fixture_read_lease_admission(**values)
    assert decision.reason_code is Task082Reason.WRONG_ASSET_ADOPTION


def test_read_purpose_rejects_missing_and_cross_purpose_authority_fields() -> None:
    quality = read_kwargs()
    quality["producer_output_receipt_sha256"] = None
    assert (
        compile_fixture_read_lease_admission(**quality).reason_code
        is Task082Reason.REQUIRED_BINDING_MISSING
    )

    quality = read_kwargs()
    quality["dataset_snapshot_sha256"] = h("cross-purpose")
    assert compile_fixture_read_lease_admission(**quality).reason_code is Task082Reason.WRONG_PURPOSE

    review = read_kwargs(ReadPurpose.DATASET_REVIEW)
    review["dataset_review_binding_sha256"] = None
    assert (
        compile_fixture_read_lease_admission(**review).reason_code
        is Task082Reason.REQUIRED_BINDING_MISSING
    )

    training = read_kwargs(ReadPurpose.VOICE_MODEL_TRAINING)
    training["producer_output_receipt_sha256"] = h("cross-purpose")
    assert compile_fixture_read_lease_admission(**training).reason_code is Task082Reason.WRONG_PURPOSE


def test_fixture_lease_state_machine_is_one_use_and_lost_reply_is_unknown() -> None:
    decision = compile_fixture_write_lease_admission(**write_kwargs())
    sentinel = mint_fixture_lease_sentinel(decision)
    assert transition_fixture_lease(sentinel, LeaseState.ISSUED).state is LeaseState.ISSUED
    assert transition_fixture_lease(sentinel, LeaseState.OPEN_STARTED).state is LeaseState.OPEN_STARTED
    lost = transition_fixture_lease(sentinel, LeaseState.CONSUMED, lost_reply=True)
    assert lost.state is LeaseState.COMPLETION_UNKNOWN
    assert lost.reason_code is Task082Reason.COMPLETION_UNKNOWN
    assert read_fixture_lease_state(sentinel).state is LeaseState.COMPLETION_UNKNOWN
    with pytest.raises(Task082ContractError) as caught:
        transition_fixture_lease(sentinel, LeaseState.OPEN_STARTED)
    assert caught.value.reason is Task082Reason.REPLAY
    assert_effect_zero(lost)


def test_consumed_requires_completion_readback_and_direct_skip_is_rejected() -> None:
    sentinel = mint_fixture_lease_sentinel(compile_fixture_write_lease_admission(**write_kwargs()))
    with pytest.raises(Task082ContractError) as caught:
        transition_fixture_lease(sentinel, LeaseState.CONSUMED)
    assert caught.value.reason is Task082Reason.STATE_TRANSITION_INVALID

    transition_fixture_lease(sentinel, LeaseState.ISSUED)
    transition_fixture_lease(sentinel, LeaseState.OPEN_STARTED)
    completion = completion_for(decision := compile_fixture_write_lease_admission(**write_kwargs()))
    consumed = transition_fixture_lease(
        sentinel,
        LeaseState.CONSUMED,
        completion_readback=completion,
        expected_completion_readback_sha256=completion.completion_sha256,
    )
    assert consumed.state is LeaseState.CONSUMED
    with pytest.raises(Task082ContractError) as caught:
        transition_fixture_lease(
            sentinel,
            LeaseState.CONSUMED,
            completion_readback=completion,
            expected_completion_readback_sha256=completion.completion_sha256,
        )
    assert caught.value.reason is Task082Reason.REPLAY


def test_completion_readback_is_lease_kind_bound_and_boolean_spoof_is_rejected() -> None:
    decision = compile_fixture_write_lease_admission(**write_kwargs())
    sentinel = mint_fixture_lease_sentinel(decision)
    transition_fixture_lease(sentinel, LeaseState.ISSUED)
    transition_fixture_lease(sentinel, LeaseState.OPEN_STARTED)
    completion = completion_for(decision)
    unknown = transition_fixture_lease(
        sentinel,
        LeaseState.CONSUMED,
        completion_readback=completion,
        expected_completion_readback_sha256=h("wrong"),
    )
    assert unknown.state is LeaseState.COMPLETION_UNKNOWN

    other = mint_fixture_lease_sentinel(compile_fixture_write_lease_admission(**write_kwargs()))
    with pytest.raises(Task082ContractError) as caught:
        transition_fixture_lease(other, LeaseState.ISSUED, lost_reply=1)  # type: ignore[arg-type]
    assert caught.value.reason is Task082Reason.REQUEST_INVALID


def test_fixture_sentinel_cannot_be_rebuilt_from_receipt_or_serialized() -> None:
    decision = compile_fixture_write_lease_admission(**write_kwargs())
    with pytest.raises(Task082ContractError) as caught:
        mint_fixture_lease_sentinel(decision.as_dict())  # type: ignore[arg-type]
    assert caught.value.reason is Task082Reason.RECEIPT_AS_CAPABILITY

    sentinel = mint_fixture_lease_sentinel(decision)
    with pytest.raises(TypeError, match=Task082Reason.RECEIPT_AS_CAPABILITY.value):
        pickle.dumps(sentinel)
    with pytest.raises(TypeError, match=Task082Reason.RECEIPT_AS_CAPABILITY.value):
        pickle.dumps(decision)
    currentness = read_kwargs()["currentness"]
    with pytest.raises(TypeError, match=Task082Reason.RECEIPT_AS_CAPABILITY.value):
        pickle.dumps(currentness)

    with pytest.raises(Task082ContractError) as caught:
        transition_fixture_lease(decision.as_dict(), LeaseState.ISSUED)  # type: ignore[arg-type]
    assert caught.value.reason is Task082Reason.RECEIPT_AS_CAPABILITY


def test_fixture_authority_objects_reject_subclasses_and_state_rewind() -> None:
    decision = compile_fixture_write_lease_admission(**write_kwargs())
    currentness = read_kwargs()["currentness"]
    completion = completion_for(decision)

    for sealed_type in (type(decision), type(currentness), type(completion)):
        with pytest.raises(TypeError, match=Task082Reason.RECEIPT_AS_CAPABILITY.value):
            type("ForgedAuthority", (sealed_type,), {})

    sentinel = mint_fixture_lease_sentinel(decision)
    with pytest.raises(TypeError, match=Task082Reason.RECEIPT_AS_CAPABILITY.value):
        type("ForgedSentinel", (type(sentinel),), {})
    transition_fixture_lease(sentinel, LeaseState.EXPIRED)
    with pytest.raises(TypeError, match=Task082Reason.RECEIPT_AS_CAPABILITY.value):
        sentinel._state = LeaseState.PREPARED  # type: ignore[misc]
    assert sentinel.state is LeaseState.EXPIRED
    with pytest.raises(Task082ContractError) as caught:
        transition_fixture_lease(sentinel, LeaseState.ISSUED)
    assert caught.value.reason is Task082Reason.REPLAY


def test_public_failure_never_echoes_private_input() -> None:
    private = "D:\\Owner Secret\\speaker-fingerprint.wav"
    values = write_kwargs()
    values["operation_id"] = private
    decision = compile_fixture_write_lease_admission(**values)
    serialized = json.dumps(decision.as_dict(), sort_keys=True)
    assert private not in serialized
    assert decision.operation_id == "INVALID"
    assert decision.reason_code is Task082Reason.REQUEST_INVALID
