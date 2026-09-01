from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ai_video_production.owner_voice_authority import (
    CompletionClass,
    DurabilityVariant,
    HUMAN_ACTION_REGISTRY_VERSION,
    OPERATION_PROFILE_REGISTRY_VERSION,
    OwnerVoiceAuthorityPublicProjection,
    OwnerVoiceRegistryAmendmentProposal,
    PersistenceState,
    PrivateReferenceState,
    PublicReferenceStatus,
    Task074OwnerVoiceAuthorityCompletionReceipt,
    Task074ToTask075ExecutionInputV2,
)
from ai_video_production.owner_voice_private_reference import MEDIA_POLICY_SHA256
from ai_video_production.serialization import sha256_bytes
from ai_video_production.voice_profile_route_selection import ComputePreference, RouteMode


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "owner_voice_authority.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "owner_voice_authority.schema.json"
NOW = "2026-09-01T09:00:00Z"


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def completion(
    *,
    mode: RouteMode = RouteMode.ZERO_SHOT_LOCAL,
    completion_class: CompletionClass = CompletionClass.TASK074_IMPLEMENTATION_COMPLETE,
    persistence: PersistenceState = PersistenceState.DURABLE_VERIFIED,
    private_state: PrivateReferenceState | None = None,
    owner_verified: bool | None = None,
) -> Task074OwnerVoiceAuthorityCompletionReceipt:
    zero = mode is RouteMode.ZERO_SHOT_LOCAL
    if private_state is None:
        private_state = PrivateReferenceState.NOT_CONFIRMED if zero else PrivateReferenceState.NOT_REQUIRED
    if owner_verified is None:
        owner_verified = completion_class is CompletionClass.P0V_OWNER_REFERENCE_VERIFIED
    prepared = private_state is PrivateReferenceState.PREPARED_VERIFIED
    return Task074OwnerVoiceAuthorityCompletionReceipt.create(
        completion_id="task074.completion.1",
        completion_class=completion_class,
        project_id="project.alpha",
        project_manifest_revision_sha256=digest("manifest"),
        installed_startup_context_binding_sha256=digest("installed-context"),
        voice_profile_id="voice.owner",
        voice_profile_revision=7,
        voice_profile_revision_sha256=digest("voice-profile"),
        consent_current_evaluation_sha256=digest("consent-current"),
        route_mode=mode,
        route_selection_revision=3,
        route_selection_sha256=digest("route-selection"),
        route_selection_store_receipt_sha256=(
            digest("store-receipt") if persistence is PersistenceState.DURABLE_VERIFIED else None
        ),
        reference_lifecycle_snapshot_sha256=digest("reference-head") if prepared else None,
        reference_preparation_receipt_sha256=digest("prepare-receipt") if prepared else None,
        reference_capability_binding_sha256=digest("capability-binding") if prepared else None,
        reference_media_policy_sha256=MEDIA_POLICY_SHA256 if prepared else None,
        reference_transcript_binding_receipt_sha256=digest("transcript-binding") if prepared else None,
        model_candidate_revision_sha256=None if zero else digest("model-candidate"),
        model_candidate_currentness_sha256=None if zero else digest("model-current"),
        human_action_registry_receipt_sha256=digest("human-registry"),
        operation_profile_registry_receipt_sha256=digest("operation-registry"),
        persistence_state=persistence,
        private_reference_state=private_state,
        owner_reference_verified=owner_verified,
        issued_at=NOW,
        expires_at="2026-09-01T10:00:00Z",
    )


def zero_input() -> dict[str, object]:
    return {
        "variant": "ZERO_SHOT_REFERENCE_INPUT_V2",
        "reference_lifecycle_snapshot_sha256": digest("reference-head"),
        "pair_ledger_sha256": digest("pair-ledger"),
        "reference_capability_v2_binding_sha256": digest("capability-v2"),
        "media_policy_sha256": MEDIA_POLICY_SHA256,
        "transcript_binding_receipt_sha256": digest("transcript-binding"),
        "reference_roles": ["REFERENCE_AUDIO_READ_HANDLE", "REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE"],
        "worker_delegation_sha256": digest("worker-delegation"),
        "task072_begin_readback_sha256": digest("task072-begin"),
        "begin_nonce_binding_sha256": digest("begin-nonce"),
        "task076_worker_process_readback_sha256": digest("task076-worker"),
        "child_process_binding_sha256": digest("child-binding"),
        "lease_state": "CHILD_PAIR_READY",
        "model_candidate_revision_sha256": None,
        "model_candidate_currentness_sha256": None,
        "installed_route_binding_sha256": None,
        "model_license_evidence_sha256": None,
        "semantic_operation_key": "narration.operation.1",
        "owner_operation_id": "owner.reference.operation.1",
        "reference_domain_snapshot_sha256": digest("reference-domain-snapshot"),
        "reference_version_fence_sha256": digest("reference-version-fence"),
        "current_v2_lease_identity_sha256": digest("current-v2-lease"),
        "attachment_sha256": digest("attachment"),
        "task076_external_binding_slot_sha256": digest("task076-slot"),
        "task076_armed_vector_sha256": digest("task076-armed-vector"),
        "task076_bootstrap_waiting_readback_sha256": digest("task076-bootstrap-waiting"),
        "task076_job_object_custody_readback_sha256": digest("task076-job-custody"),
        "task076_external_input_bound_readback_sha256": digest("task076-external-bound"),
        "task076_external_input_validated_readback_sha256": digest("task076-external-validated"),
        "producer_binding_state": "NOT_BOUND",
        "executable": False,
    }


def fine_input() -> dict[str, object]:
    return {
        "variant": "FINE_TUNED_MODEL_INPUT_V2",
        "reference_lifecycle_snapshot_sha256": None,
        "pair_ledger_sha256": None,
        "reference_capability_v2_binding_sha256": None,
        "media_policy_sha256": None,
        "transcript_binding_receipt_sha256": None,
        "reference_roles": [],
        "worker_delegation_sha256": None,
        "task072_begin_readback_sha256": None,
        "begin_nonce_binding_sha256": None,
        "task076_worker_process_readback_sha256": None,
        "child_process_binding_sha256": None,
        "lease_state": None,
        "model_candidate_revision_sha256": digest("model-candidate"),
        "model_candidate_currentness_sha256": digest("model-current"),
        "installed_route_binding_sha256": digest("installed-route"),
        "model_license_evidence_sha256": digest("license"),
        "semantic_operation_key": "narration.operation.1",
        "owner_operation_id": None,
        "reference_domain_snapshot_sha256": None,
        "reference_version_fence_sha256": None,
        "current_v2_lease_identity_sha256": None,
        "attachment_sha256": None,
        "task076_external_binding_slot_sha256": None,
        "task076_armed_vector_sha256": None,
        "task076_bootstrap_waiting_readback_sha256": None,
        "task076_job_object_custody_readback_sha256": None,
        "task076_external_input_bound_readback_sha256": None,
        "task076_external_input_validated_readback_sha256": None,
        "producer_binding_state": "NOT_BOUND",
        "executable": False,
        "composite_child_lineage_sha256": None,
    }


def handoff(
    *,
    mode: RouteMode = RouteMode.ZERO_SHOT_LOCAL,
    durability: DurabilityVariant = DurabilityVariant.DURABLE_SELECTION_HANDOFF_V1,
) -> Task074ToTask075ExecutionInputV2:
    durable = durability is DurabilityVariant.DURABLE_SELECTION_HANDOFF_V1
    zero = mode is RouteMode.ZERO_SHOT_LOCAL
    return Task074ToTask075ExecutionInputV2.create(
        handoff_id="handoff.owner.voice.1",
        durability_variant=durability,
        route_mode=mode,
        semantic_operation_key="narration.operation.1",
        aggregate_currentness_lease_binding_sha256=digest("aggregate-lease"),
        expected_product_build_sha256=digest("product-build"),
        worker_protocol_version="owner.voice.worker.v2",
        durable_completion_receipt_sha256=digest("completion") if durable else None,
        durable_selection_sha256=digest("selection") if durable else None,
        durable_currentness_sha256=digest("currentness") if durable else None,
        live_route_plan_sha256=None if durable else digest("live-plan"),
        live_route_plan_lease_sha256=None if durable else digest("live-plan-lease"),
        task072_ticket_sha256=None if durable else digest("ticket"),
        live_currentness_fingerprint_sha256=None if durable else digest("live-currentness"),
        zero_shot_input=zero_input() if zero else None,
        fine_tuned_input=None if zero else fine_input(),
        task046_owner_acceptance_sha256=None,
        task072_owner_acceptance_sha256=None,
        task075_owner_acceptance_sha256=None,
        task076_owner_acceptance_sha256=None,
        created_at=NOW,
    )


def test_registry_amendment_is_closed_status_only_and_not_producer_acceptance() -> None:
    proposal = OwnerVoiceRegistryAmendmentProposal.create(
        amendment_id="task074.registry.amendment.1",
        design_receipt_sha256=digest("accepted-design-receipt"),
        created_at=NOW,
    )
    value = proposal.to_dict()
    assert value["human_action_registry_version"] == HUMAN_ACTION_REGISTRY_VERSION
    assert value["operation_profile_registry_version"] == OPERATION_PROFILE_REGISTRY_VERSION
    assert len(value["human_action_rows"]) == 6 and len(value["operation_profile_rows"]) == 8
    assert value["task071_producer_acceptance_state"] == "NOT_CONFIRMED"
    assert value["authority_created"] is False and value["operation_ticket_created"] is False
    assert OwnerVoiceRegistryAmendmentProposal.from_dict(value).to_dict() == value


def test_registry_amendment_cannot_claim_acceptance_or_add_unknown_action() -> None:
    value = OwnerVoiceRegistryAmendmentProposal.create(
        amendment_id="task074.registry.amendment.1",
        design_receipt_sha256=digest("accepted-design-receipt"),
        created_at=NOW,
    ).to_dict()
    value["task071_producer_acceptance_state"] = "PASS"
    with pytest.raises(ValueError, match="cannot claim"):
        OwnerVoiceRegistryAmendmentProposal.from_dict(value)
    value = OwnerVoiceRegistryAmendmentProposal.create(
        amendment_id="task074.registry.amendment.1",
        design_receipt_sha256=digest("accepted-design-receipt"),
        created_at=NOW,
    ).to_dict()
    value["human_action_rows"].append({"action_code": "UNKNOWN", "purpose": "UNKNOWN", "effect_ceiling": "UNBOUNDED"})
    with pytest.raises(ValueError, match="rows"):
        OwnerVoiceRegistryAmendmentProposal.from_dict(value)


def test_implementation_completion_truthfully_allows_real_reference_not_confirmed() -> None:
    receipt = completion()
    value = receipt.to_dict()
    assert value["completion_class"] == "TASK074_IMPLEMENTATION_COMPLETE"
    assert value["private_reference_state"] == "NOT_CONFIRMED"
    assert value["owner_reference_verified"] is False
    assert value["producer_binding_state"] == "NOT_BOUND"
    assert value["fixture_only"] is True
    assert value["canonical_producer_readback"] is False
    assert value["execution_ready"] is False
    assert all(
        value[name] is None
        for name in (
            "task046_owner_acceptance_sha256", "task071_owner_acceptance_sha256",
            "task072_owner_acceptance_sha256", "task075_owner_acceptance_sha256",
            "task076_owner_acceptance_sha256",
        )
    )
    for name in (
        "human_authorization_created", "operation_ticket_created", "execution_authorized",
        "model_loaded", "inference_started", "playback_started", "wav_created",
        "asset_adopted", "timeline_mutated", "export_started", "private_body_present",
        "path_present", "secret_present", "production_eligible",
    ):
        assert value[name] is False
    assert Task074OwnerVoiceAuthorityCompletionReceipt.from_dict(value).to_dict() == value


def test_task074_b_fixture_cannot_claim_real_owner_reference_class() -> None:
    with pytest.raises(ValueError, match="cannot claim P0V"):
        completion(
            completion_class=CompletionClass.P0V_OWNER_REFERENCE_VERIFIED,
            private_state=PrivateReferenceState.PREPARED_VERIFIED,
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("producer_binding_state", "BOUND"),
        ("fixture_only", False),
        ("canonical_producer_readback", True),
        ("execution_ready", True),
        ("task046_owner_acceptance_sha256", digest("fake-task046-acceptance")),
    ],
)
def test_completion_fixture_cannot_be_relabelled_canonical(
    field: str, replacement: object
) -> None:
    value = completion().to_dict()
    value[field] = replacement
    with pytest.raises(ValueError):
        Task074OwnerVoiceAuthorityCompletionReceipt.from_dict(value)


def test_fine_tuned_completion_has_model_only_and_zero_reference_fields() -> None:
    value = completion(mode=RouteMode.FINE_TUNED_LOCAL).to_dict()
    assert value["private_reference_state"] == "NOT_REQUIRED"
    assert value["model_candidate_revision_sha256"] == digest("model-candidate")
    assert value["reference_lifecycle_snapshot_sha256"] is None
    tampered = deepcopy(value)
    tampered["reference_media_policy_sha256"] = MEDIA_POLICY_SHA256
    with pytest.raises(ValueError, match="cannot carry reference"):
        Task074OwnerVoiceAuthorityCompletionReceipt.from_dict(tampered)


def test_completion_rejects_hash_effect_body_path_secret_and_unknown_fields() -> None:
    for field, replacement in (
        ("completion_sha256", digest("tampered")),
        ("execution_authorized", True),
        ("inference_started", True),
        ("wav_created", True),
        ("private_body_present", True),
        ("path_present", True),
        ("secret_present", True),
    ):
        value = completion().to_dict()
        value[field] = replacement
        with pytest.raises(ValueError):
            Task074OwnerVoiceAuthorityCompletionReceipt.from_dict(value)
    value = completion().to_dict()
    value["raw_audio_body"] = "forbidden"
    with pytest.raises(ValueError, match="unknown"):
        Task074OwnerVoiceAuthorityCompletionReceipt.from_dict(value)


def test_public_projection_is_allowlist_only_and_has_only_self_digest() -> None:
    projection = OwnerVoiceAuthorityPublicProjection.create(
        route_label="ローカル・ゼロショット",
        public_route_key="narration.qwen3.local",
        route_mode=RouteMode.ZERO_SHOT_LOCAL,
        compute_preference=ComputePreference.AUTO,
        saved=True,
        reference_status=PublicReferenceStatus.NOT_CONFIRMED,
        runnable_candidate=False,
        reason_codes=("REFERENCE_NOT_CONFIRMED",),
        profile_display_alias="Owner Voice",
    )
    value = projection.to_dict()
    digests = [key for key in value if key.endswith("sha256")]
    assert digests == ["public_projection_sha256"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for private in ("consent", "reference_lifecycle", "completion_sha256", "transcript", "capability"):
        assert private not in encoded.lower()
    assert OwnerVoiceAuthorityPublicProjection.from_dict(value).to_dict() == value


def test_public_projection_ready_matrix_is_route_specific_and_noncontradictory() -> None:
    zero = OwnerVoiceAuthorityPublicProjection.create(
        route_label="Local Zero Shot",
        public_route_key="narration.qwen3.local",
        route_mode=RouteMode.ZERO_SHOT_LOCAL,
        compute_preference=ComputePreference.AUTO,
        saved=True,
        reference_status=PublicReferenceStatus.READY,
        runnable_candidate=True,
        reason_codes=(),
        profile_display_alias="Owner Voice",
    ).to_dict()
    assert zero["runnable_candidate"] is True and zero["reason_codes"] == []
    fine = OwnerVoiceAuthorityPublicProjection.create(
        route_label="Local Fine Tuned",
        public_route_key="narration.fine.local",
        route_mode=RouteMode.FINE_TUNED_LOCAL,
        compute_preference=ComputePreference.CPU,
        saved=True,
        reference_status=PublicReferenceStatus.NOT_REQUIRED,
        runnable_candidate=True,
        reason_codes=(),
        profile_display_alias="Owner Fine Voice",
    ).to_dict()
    assert fine["reference_status"] == "NOT_REQUIRED"


@pytest.mark.parametrize(
    ("mode", "saved", "status", "runnable", "reasons", "message"),
    [
        (RouteMode.ZERO_SHOT_LOCAL, True, PublicReferenceStatus.NOT_REQUIRED, False, ("BLOCKED",), "cannot mark"),
        (RouteMode.FINE_TUNED_LOCAL, True, PublicReferenceStatus.READY, True, (), "requires reference"),
        (RouteMode.ZERO_SHOT_LOCAL, False, PublicReferenceStatus.READY, True, (), "requires saved ready"),
        (RouteMode.ZERO_SHOT_LOCAL, True, PublicReferenceStatus.READY, True, ("STALE",), "without reasons"),
        (RouteMode.ZERO_SHOT_LOCAL, True, PublicReferenceStatus.NOT_CONFIRMED, False, (), "requires at least one"),
    ],
)
def test_public_projection_rejects_contradictory_ready_state(
    mode: RouteMode,
    saved: bool,
    status: PublicReferenceStatus,
    runnable: bool,
    reasons: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        OwnerVoiceAuthorityPublicProjection.create(
            route_label="Owner Route",
            public_route_key="narration.owner.local",
            route_mode=mode,
            compute_preference=ComputePreference.AUTO,
            saved=saved,
            reference_status=status,
            runnable_candidate=runnable,
            reason_codes=reasons,
            profile_display_alias="Owner Voice",
        )


@pytest.mark.parametrize(
    ("field", "host_location"),
    [
        ("route_label", "C:\\private\\voice.wav"),
        ("profile_display_alias", "file://private/voice.wav"),
        ("profile_display_alias", "../private/voice"),
        ("route_label", "Owner C:/Users/Alice/private/ref.wav"),
        ("profile_display_alias", "source=https://host/private/ref.wav"),
        ("profile_display_alias", "Owner C：／Users／Alice／private／ref.wav"),
    ],
)
def test_public_projection_rejects_host_location_aliases(field: str, host_location: str) -> None:
    value = OwnerVoiceAuthorityPublicProjection.create(
        route_label="Local Zero Shot",
        public_route_key="narration.qwen3.local",
        route_mode=RouteMode.ZERO_SHOT_LOCAL,
        compute_preference=ComputePreference.AUTO,
        saved=True,
        reference_status=PublicReferenceStatus.NOT_CONFIRMED,
        runnable_candidate=False,
        reason_codes=("REFERENCE_NOT_CONFIRMED",),
        profile_display_alias="Owner Voice",
    ).to_dict()
    value[field] = host_location
    with pytest.raises(ValueError, match="host location"):
        OwnerVoiceAuthorityPublicProjection.from_dict(value)


@pytest.mark.parametrize(
    "path_like_key",
    (
        "C:private_voice.wav",
        "private/voice.wav",
        "file:private_voice.wav",
        "Ｃ：private_voice.wav",
        "private／voice.wav",
        "private_voice.wav",
    ),
)
def test_public_projection_route_key_rejects_path_like_values(path_like_key: str) -> None:
    value = OwnerVoiceAuthorityPublicProjection.create(
        route_label="Local Zero Shot",
        public_route_key="narration.qwen3.local",
        route_mode=RouteMode.ZERO_SHOT_LOCAL,
        compute_preference=ComputePreference.AUTO,
        saved=True,
        reference_status=PublicReferenceStatus.NOT_CONFIRMED,
        runnable_candidate=False,
        reason_codes=("REFERENCE_NOT_CONFIRMED",),
        profile_display_alias="Owner Voice",
    ).to_dict()
    value["public_route_key"] = path_like_key
    with pytest.raises(ValueError, match="host path|closed narration"):
        OwnerVoiceAuthorityPublicProjection.from_dict(value)


@pytest.mark.parametrize(
    "path_like_reason",
    (
        "C:private_voice.wav",
        "private/voice.wav",
        "file:private_voice.wav",
        "Ｃ：private_voice.wav",
        "private／voice.wav",
        "private_voice.wav",
    ),
)
def test_public_projection_reason_codes_reject_path_like_values(path_like_reason: str) -> None:
    value = OwnerVoiceAuthorityPublicProjection.create(
        route_label="Local Zero Shot",
        public_route_key="narration.qwen3.local",
        route_mode=RouteMode.ZERO_SHOT_LOCAL,
        compute_preference=ComputePreference.AUTO,
        saved=True,
        reference_status=PublicReferenceStatus.NOT_CONFIRMED,
        runnable_candidate=False,
        reason_codes=("REFERENCE_NOT_CONFIRMED",),
        profile_display_alias="Owner Voice",
    ).to_dict()
    value["reason_codes"] = [path_like_reason]
    with pytest.raises(ValueError, match="host path|closed public grammar"):
        OwnerVoiceAuthorityPublicProjection.from_dict(value)


def test_python_and_schema_bounds_are_aligned_for_authority_public_fields() -> None:
    with pytest.raises(ValueError, match="200 characters"):
        OwnerVoiceRegistryAmendmentProposal.create(
            amendment_id="a" * 201,
            design_receipt_sha256=digest("accepted-design-receipt"),
            created_at=NOW,
        )
    with pytest.raises(ValueError, match="200 characters"):
        OwnerVoiceAuthorityPublicProjection.create(
            route_label="Local Zero Shot",
            public_route_key=f"narration.{'a' * 201}.local",
            route_mode=RouteMode.ZERO_SHOT_LOCAL,
            compute_preference=ComputePreference.AUTO,
            saved=True,
            reference_status=PublicReferenceStatus.NOT_CONFIRMED,
            runnable_candidate=False,
            reason_codes=("REFERENCE_NOT_CONFIRMED",),
            profile_display_alias="Owner Voice",
        )
    with pytest.raises(ValueError, match="at most 64"):
        OwnerVoiceAuthorityPublicProjection.create(
            route_label="Local Zero Shot",
            public_route_key="narration.qwen3.local",
            route_mode=RouteMode.ZERO_SHOT_LOCAL,
            compute_preference=ComputePreference.AUTO,
            saved=True,
            reference_status=PublicReferenceStatus.NOT_CONFIRMED,
            runnable_candidate=False,
            reason_codes=tuple(f"REASON_{index:02d}" for index in range(65)),
            profile_display_alias="Owner Voice",
        )


@pytest.mark.parametrize("durability", list(DurabilityVariant))
def test_zero_shot_v2_handoff_covers_both_outer_variants(durability: DurabilityVariant) -> None:
    value = handoff(durability=durability).to_dict()
    assert value["zero_shot_input"]["lease_state"] == "CHILD_PAIR_READY"
    assert value["zero_shot_input"]["reference_roles"] == [
        "REFERENCE_AUDIO_READ_HANDLE", "REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE"
    ]
    assert value["fixture_only"] is True
    assert value["producer_binding_state"] == "NOT_BOUND"
    assert value["execution_ready"] is False
    assert value["g11_structurally_complete"] is False
    assert value["zero_shot_input"]["composite_child_lineage_sha256"]
    assert all(
        value[name] is None
        for name in (
            "task046_owner_acceptance_sha256",
            "task072_owner_acceptance_sha256",
            "task075_owner_acceptance_sha256",
            "task076_owner_acceptance_sha256",
        )
    )
    assert value["authority_created"] is False and value["execution_authorized"] is False
    assert Task074ToTask075ExecutionInputV2.from_dict(value).to_dict() == value


@pytest.mark.parametrize("durability", list(DurabilityVariant))
def test_fine_tuned_v2_handoff_never_enters_reference_broker(durability: DurabilityVariant) -> None:
    value = handoff(mode=RouteMode.FINE_TUNED_LOCAL, durability=durability).to_dict()
    inner = value["fine_tuned_input"]
    assert inner["reference_roles"] == []
    assert inner["reference_capability_v2_binding_sha256"] is None
    assert inner["worker_delegation_sha256"] is None
    assert value["task072_owner_acceptance_sha256"] is None
    assert value["task076_owner_acceptance_sha256"] is None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"fine_tuned_input": fine_input()}, "inner route union"),
        ({"zero_shot_input": None}, "inner route union"),
        ({"task072_owner_acceptance_sha256": digest("fake-acceptance")}, "cannot claim canonical producer"),
        ({"task076_owner_acceptance_sha256": digest("fake-acceptance")}, "cannot claim canonical producer"),
        ({"producer_binding_state": "BOUND"}, "producer-unbound fixture evidence"),
        ({"execution_ready": True}, "producer-unbound fixture evidence"),
        ({"g11_structurally_complete": True}, "producer-unbound fixture evidence"),
        ({"body_present": True}, "remain false"),
        ({"path_present": True}, "remain false"),
        ({"execution_authorized": True}, "remain false"),
    ],
)
def test_handoff_wrong_union_missing_acceptance_or_leak_fails_closed(
    mutation: dict[str, object], message: str
) -> None:
    value = handoff().to_dict()
    value.update(mutation)
    with pytest.raises(ValueError, match=message):
        Task074ToTask075ExecutionInputV2.from_dict(value)


def test_zero_shot_rejects_composite_child_lineage_tamper() -> None:
    value = handoff().to_dict()
    value["zero_shot_input"]["attachment_sha256"] = digest("cross-lineage-attachment")
    with pytest.raises(ValueError, match="composite child lineage digest mismatch"):
        Task074ToTask075ExecutionInputV2.from_dict(value)


def test_zero_shot_rejects_wrong_role_order_model_field_and_pre_ready_state() -> None:
    for inner_mutation in (
        {"reference_roles": ["REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE", "REFERENCE_AUDIO_READ_HANDLE"]},
        {"model_candidate_revision_sha256": digest("illegal-model")},
        {"lease_state": "CHILD_TRANSFER_IN_FLIGHT"},
        {"media_policy_sha256": digest("wrong-policy")},
    ):
        value = handoff().to_dict()
        value["zero_shot_input"].update(inner_mutation)
        with pytest.raises(ValueError):
            Task074ToTask075ExecutionInputV2.from_dict(value)


def test_outer_durable_live_fields_cannot_mix() -> None:
    value = handoff().to_dict()
    value["live_route_plan_sha256"] = digest("illegal-live")
    with pytest.raises(ValueError, match="outer union"):
        Task074ToTask075ExecutionInputV2.from_dict(value)
    value = handoff(durability=DurabilityVariant.TASK074_ONE_OPERATION_EXECUTION_HANDOFF_V1).to_dict()
    value["durable_completion_receipt_sha256"] = digest("illegal-durable")
    with pytest.raises(ValueError, match="outer union"):
        Task074ToTask075ExecutionInputV2.from_dict(value)


def test_schema_validates_authority_records_rejects_effect_and_is_mirrored() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    records = [
        OwnerVoiceRegistryAmendmentProposal.create(
            amendment_id="task074.registry.amendment.1",
            design_receipt_sha256=digest("accepted-design-receipt"),
            created_at=NOW,
        ).to_dict(),
        completion().to_dict(),
        OwnerVoiceAuthorityPublicProjection.create(
            route_label="Local Zero Shot",
            public_route_key="narration.qwen3.local",
            route_mode=RouteMode.ZERO_SHOT_LOCAL,
            compute_preference=ComputePreference.AUTO,
            saved=True,
            reference_status=PublicReferenceStatus.NOT_CONFIRMED,
            runnable_candidate=False,
            reason_codes=("REFERENCE_NOT_CONFIRMED",),
            profile_display_alias="Owner Voice",
        ).to_dict(),
        handoff().to_dict(),
        handoff(mode=RouteMode.FINE_TUNED_LOCAL).to_dict(),
    ]
    for record in records:
        validator.validate(record)
    invalid = completion().to_dict()
    invalid["wav_created"] = True
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid_projection = records[2].copy()
    invalid_projection["profile_display_alias"] = "Owner C:/Users/Alice/private/voice.wav"
    with pytest.raises(ValidationError):
        validator.validate(invalid_projection)
    for path_like in (
        "C:private_voice.wav",
        "private/voice.wav",
        "file:private_voice.wav",
        "Ｃ：private_voice.wav",
        "private／voice.wav",
        "private_voice.wav",
    ):
        invalid_projection = deepcopy(records[2])
        invalid_projection["public_route_key"] = path_like
        with pytest.raises(ValidationError):
            validator.validate(invalid_projection)
        invalid_projection = deepcopy(records[2])
        invalid_projection["reason_codes"] = [path_like]
        with pytest.raises(ValidationError):
            validator.validate(invalid_projection)
    invalid = deepcopy(records[0])
    invalid["amendment_id"] = "a" * 201
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid_projection = deepcopy(records[2])
    invalid_projection["public_route_key"] = f"narration.{'a' * 201}.local"
    with pytest.raises(ValidationError):
        validator.validate(invalid_projection)
    invalid_projection = deepcopy(records[2])
    invalid_projection["reason_codes"] = [f"REASON_{index:02d}" for index in range(65)]
    with pytest.raises(ValidationError):
        validator.validate(invalid_projection)
    invalid = completion().to_dict()
    invalid["task046_owner_acceptance_sha256"] = digest("fake-canonical-acceptance")
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = deepcopy(records[2])
    invalid["runnable_candidate"] = True
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = handoff().to_dict()
    invalid["producer_binding_state"] = "BOUND"
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = handoff().to_dict()
    del invalid["zero_shot_input"]["task076_job_object_custody_readback_sha256"]
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


def test_module_has_no_provider_private_body_model_or_execution_api() -> None:
    path = ROOT / "src" / "ai_video_production" / "owner_voice_authority.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint({"os", "pathlib", "subprocess", "socket", "wave", "requests", "openai"})
    names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    assert names.isdisjoint({"execute", "authorize", "issue_ticket", "infer", "render", "load_model", "open_audio"})
