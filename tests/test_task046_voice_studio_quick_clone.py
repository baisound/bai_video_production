from __future__ import annotations

from dataclasses import fields, replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.voice_studio_quick_clone import (
    ComputePreference,
    ComputeResolutionState,
    ExecutionState,
    ModelExecutionPolicy,
    OwnerListeningState,
    PreviewAssetAdoptionState,
    ProfileAdoptionState,
    QualityState,
    QuickCloneFlowRevision,
    QuickCloneFutureSemanticFixture,
    ReferenceRetentionState,
    ResultAdmissionState,
    RuntimeAggregateState,
    SetupState,
    SourceKind,
    assert_no_effect_surface,
    public_projection,
    readback_currentness_state,
    ui_guidance_ja,
    validate_flow_transition,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "voice-studio-quick-clone.schema.json"
MIRROR = (
    ROOT
    / "src"
    / "ai_video_production"
    / "schema_resources"
    / SCHEMA.name
)


def _sha(number: int) -> str:
    return f"sha256:{number:064x}"


def _draft(**changes: object) -> QuickCloneFlowRevision:
    values: dict[str, object] = {
        "flow_id": "quick-clone:flow-1",
        "revision": 1,
        "parent_revision_sha256": None,
        "created_at": "2026-09-01T00:00:00Z",
        "source_kind": SourceKind.TASK046_PRIVATE_REFERENCE,
        "setup_state": SetupState.NOT_INSTALLED,
        "execution_state": ExecutionState.DRAFT,
        "quality_state": QualityState.NOT_AVAILABLE,
        "owner_listening_state": OwnerListeningState.NOT_AVAILABLE,
        "profile_adoption_state": ProfileAdoptionState.NOT_AVAILABLE,
        "preview_asset_adoption_state": PreviewAssetAdoptionState.NOT_AVAILABLE,
        "reference_retention_state": ReferenceRetentionState.UNDECIDED,
        "compute_preference": ComputePreference.AUTO,
        "compute_resolution_state": ComputeResolutionState.NOT_RESOLVED,
        "model_execution_policy": ModelExecutionPolicy.CUDA_ONLY,
        "runtime_aggregate_state": RuntimeAggregateState.NOT_BOUND,
        "result_admission_state": ResultAdmissionState.NOT_BOUND,
        "source_binding_sha256": _sha(1),
        "consent_binding_sha256": _sha(2),
        "reference_transcript_sha256": _sha(3),
        "preview_text_sha256": _sha(4),
        "preview_text_code_points": 42,
        "preview_profile_revision_sha256": _sha(5),
        "model_selection_binding_sha256": _sha(6),
        "runtime_aggregate_binding_sha256": None,
    }
    values.update(changes)
    return QuickCloneFlowRevision(**values)  # type: ignore[arg-type]


def _fixture_draft(**changes: object) -> QuickCloneFutureSemanticFixture:
    production = _draft(**changes)
    values = {
        field.name: getattr(production, field.name)
        for field in fields(production)
    }
    return QuickCloneFutureSemanticFixture(**values)


def _ready(
    previous: QuickCloneFutureSemanticFixture | None = None,
) -> QuickCloneFutureSemanticFixture:
    old = previous or _fixture_draft()
    return replace(
        old,
        revision=old.revision + 1,
        parent_revision_sha256=old.flow_revision_sha256,
        created_at="2026-09-01T00:01:00Z",
        setup_state=SetupState.READY,
        execution_state=ExecutionState.READY_FOR_CONFIRMATION,
        compute_resolution_state=ComputeResolutionState.GPU_READY,
        runtime_aggregate_state=RuntimeAggregateState.BOUND_VERIFIED,
        runtime_aggregate_binding_sha256=_sha(70),
        preflight_sha256=_sha(7),
        one_shot_authorization_sha256=_sha(8),
    )


def _dispatching(
    previous: QuickCloneFutureSemanticFixture | None = None,
) -> QuickCloneFutureSemanticFixture:
    old = previous or _ready()
    return replace(
        old,
        revision=old.revision + 1,
        parent_revision_sha256=old.flow_revision_sha256,
        created_at="2026-09-01T00:02:00Z",
        execution_state=ExecutionState.DISPATCHING,
        durable_job_sha256=_sha(9),
        render_operation_identity_sha256=_sha(71),
    )


def _result(
    previous: QuickCloneFutureSemanticFixture | None = None,
) -> QuickCloneFutureSemanticFixture:
    old = previous or _dispatching()
    return replace(
        old,
        revision=old.revision + 1,
        parent_revision_sha256=old.flow_revision_sha256,
        created_at="2026-09-01T00:03:00Z",
        execution_state=ExecutionState.READY_FOR_QA_REVIEW,
        result_admission_state=ResultAdmissionState.BOUND_VERIFIED,
        result_receipt_sha256=_sha(10),
        result_admission_receipt_sha256=_sha(72),
        result_render_operation_identity_sha256=old.render_operation_identity_sha256,
        result_preview_profile_revision_sha256=old.preview_profile_revision_sha256,
        result_model_selection_binding_sha256=old.model_selection_binding_sha256,
        result_runtime_aggregate_binding_sha256=old.runtime_aggregate_binding_sha256,
        result_output_sha256=_sha(11),
        result_route="ZERO_SHOT",
        result_replay=False,
        staged_wav_ref="staged-narration:job-1/preview.wav",
        staged_wav_sha256=_sha(11),
        sample_count=48_000,
        duration_us=1_000_000,
        quality_state=QualityState.PENDING,
        owner_listening_state=OwnerListeningState.REQUIRED,
    )


def _accepted(
    previous: QuickCloneFutureSemanticFixture | None = None,
) -> QuickCloneFutureSemanticFixture:
    old = previous or _result()
    return replace(
        old,
        revision=old.revision + 1,
        parent_revision_sha256=old.flow_revision_sha256,
        created_at="2026-09-01T00:04:00Z",
        quality_state=QualityState.PASS,
        quality_receipt_sha256=_sha(12),
        owner_listening_state=OwnerListeningState.ACCEPTED,
        owner_listening_receipt_sha256=_sha(13),
        profile_adoption_state=ProfileAdoptionState.SAVE_DECISION_REQUIRED,
        preview_asset_adoption_state=PreviewAssetAdoptionState.PUBLISH_DECISION_REQUIRED,
        reference_retention_state=ReferenceRetentionState.RETAIN_PRIVATE_REFERENCE,
        reference_retention_decision_sha256=_sha(14),
    )


def _validator() -> Draft202012Validator:
    value = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return Draft202012Validator(value, format_checker=FormatChecker())


def test_draft_round_trip_schema_mirror_and_public_projection_are_body_free() -> None:
    draft = _draft()
    record = draft.to_dict()

    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    _validator().validate(record)
    assert QuickCloneFlowRevision.from_dict(record) == draft
    assert draft.flow_revision_sha256 == QuickCloneFlowRevision.from_dict(record).flow_revision_sha256

    projection = public_projection(draft)
    assert projection["setup_state"] == "NOT_INSTALLED"
    assert projection["execution_state"] == "DRAFT"
    assert projection["model_configuration_source"] == "CENTRAL_AI_SETTINGS"
    assert projection["model_configuration_access"] == "READ_ONLY"
    assert projection["voice_model_selector_present"] is False
    assert projection["execution_enabled"] is False
    assert projection["settings_cta_label_ja"] == "中央AI設定を開く"
    assert projection["settings_cta_target"] == "SETTINGS_AI"
    assert "未設定" in projection["status_message_ja"]
    assert projection["cancel_action_label_ja"] == "キャンセル"
    assert projection["retry_action_label_ja"] == "再試行"
    assert projection["retry_requires_confirmation"] is True
    assert projection["next_action_ja"]
    assert projection["effect_authorized"] is False
    assert projection["automatic_retry_authorized"] is False
    assert projection["audio_body_included"] is False
    assert projection["text_body_included"] is False
    assert projection["host_path_included"] is False
    assert "flow_id" not in projection
    assert "reason_codes" not in projection
    assert "sha256:" not in json.dumps(projection, sort_keys=True)
    assert_no_effect_surface()


def test_setup_and_currentness_states_are_distinct_and_have_japanese_guidance() -> None:
    verifying = public_projection(_draft(setup_state=SetupState.VERIFYING))
    failed = public_projection(
        _draft(
            setup_state=SetupState.FAILED,
            reason_codes=("MODEL_SETUP_FAILED",),
        )
    )
    ready = public_projection(
        _draft(
            setup_state=SetupState.READY,
            compute_resolution_state=ComputeResolutionState.GPU_READY,
            runtime_aggregate_state=RuntimeAggregateState.BOUND_VERIFIED,
            runtime_aggregate_binding_sha256=_sha(70),
        )
    )
    unknown = public_projection(
        _draft(runtime_aggregate_state=RuntimeAggregateState.UNKNOWN)
    )

    assert {verifying["setup_state"], failed["setup_state"], ready["setup_state"]} == {
        "VERIFYING", "FAILED", "READY",
    }
    assert "確認しています" in verifying["status_message_ja"]
    assert "失敗" in failed["status_message_ja"]
    assert "完了" in ready["status_message_ja"]
    accepted = _accepted()
    adopted = replace(
        accepted,
        revision=accepted.revision + 1,
        parent_revision_sha256=accepted.flow_revision_sha256,
        created_at="2026-09-01T00:05:00Z",
        profile_adoption_state=ProfileAdoptionState.SAVED_LOCAL_CANDIDATE,
        saved_profile_revision_sha256=_sha(74),
        profile_adoption_receipt_sha256=_sha(75),
    )
    stale = replace(
        adopted,
        revision=adopted.revision + 1,
        parent_revision_sha256=adopted.flow_revision_sha256,
        created_at="2026-09-01T00:06:00Z",
        profile_adoption_state=ProfileAdoptionState.STALE,
        profile_currentness_receipt_sha256=_sha(73),
        reference_retention_state=ReferenceRetentionState.EXPIRED,
        reference_retention_currentness_receipt_sha256=_sha(76),
    )
    assert unknown["canonical_receipt_currentness_state"] == "UNKNOWN"
    assert readback_currentness_state(_draft()) == "NOT_BOUND"
    assert readback_currentness_state(stale) == "STALE"

    success_copy = ui_guidance_ja(_result())
    failed_copy = ui_guidance_ja(
        replace(
            _dispatching(),
            execution_state=ExecutionState.FAILED_KNOWN,
            reason_codes=("RENDER_FAILED",),
        )
    )
    assert "完了" in success_copy["status_message_ja"]
    assert "失敗" in failed_copy["status_message_ja"]
    assert success_copy["cancel_action_label_ja"] == "キャンセル"
    assert failed_copy["retry_action_label_ja"] == "再試行"

    invalid = _draft().to_dict()
    invalid["model_configuration_access"] = "WRITE"
    with pytest.raises(ValueError, match="identity"):
        QuickCloneFlowRevision.from_dict(invalid)

    private_markers = public_projection(
        _draft(
            flow_id="quick-clone:OWNER_TARO_VOICE",
            reason_codes=("OWNER_TARO_VOICE",),
        )
    )
    encoded = json.dumps(private_markers, ensure_ascii=False, sort_keys=True)
    assert "OWNER_TARO_VOICE" not in encoded
    assert private_markers["reason_code_count"] == 1


def test_setup_fails_closed_for_unbound_runtime_and_unsupported_compute() -> None:
    with pytest.raises(ValueError, match="verified runtime aggregate"):
        _draft(
            setup_state=SetupState.READY,
            compute_resolution_state=ComputeResolutionState.GPU_READY,
        )
    with pytest.raises(ValueError, match="CUDA_ONLY"):
        _draft(compute_resolution_state=ComputeResolutionState.CPU_READY)
    with pytest.raises(ValueError, match="CPU preference"):
        _draft(
            compute_preference=ComputePreference.CPU,
            compute_resolution_state=ComputeResolutionState.GPU_READY,
        )

    invalid = _draft().to_dict()
    invalid["model_execution_policy"] = "REMOTE_ONLY"
    with pytest.raises(ValueError):
        QuickCloneFlowRevision.from_dict(invalid)
    invalid = _draft().to_dict()
    invalid["model_selection_binding_sha256"] = None
    with pytest.raises(ValueError):
        QuickCloneFlowRevision.from_dict(invalid)


def test_execution_bindings_and_immutable_voice_consent_profile_are_enforced() -> None:
    draft = _fixture_draft()
    ready = _ready(draft)
    validate_flow_transition(draft, ready)
    dispatching = _dispatching(ready)
    validate_flow_transition(ready, dispatching)

    with pytest.raises(ValueError, match="DRAFT"):
        replace(draft, preflight_sha256=_sha(30))
    with pytest.raises(ValueError, match="Job or operation"):
        replace(ready, render_operation_identity_sha256=_sha(30))

    for field in (
        "source_binding_sha256",
        "consent_binding_sha256",
        "preview_profile_revision_sha256",
        "model_selection_binding_sha256",
    ):
        changed = replace(
            dispatching,
            revision=dispatching.revision + 1,
            parent_revision_sha256=dispatching.flow_revision_sha256,
            created_at="2026-09-01T00:02:30Z",
            execution_state=ExecutionState.RUNNING,
            **{field: _sha(31)},
        )
        with pytest.raises(ValueError, match="immutable input"):
            validate_flow_transition(dispatching, changed)


def test_result_is_exact_bounded_pcm24_48k_mono_and_digest_protected() -> None:
    dispatching = _dispatching()
    result = _result(dispatching)
    validate_flow_transition(dispatching, result)
    record = result.to_dict()
    assert list(_validator().iter_errors(record))

    assert record["sample_rate_hz"] == 48_000
    assert record["channels"] == 1
    assert record["sample_format"] == "PCM_S24LE"
    assert record["intended_artifact"] == "STAGED_NARRATION_PCM_WAV_48000_MONO"

    with pytest.raises(ValueError, match="exact sample count"):
        replace(result, duration_us=result.duration_us + 1)  # type: ignore[operator]
    with pytest.raises(ValueError, match="bounded preview"):
        replace(result, sample_count=2_880_001, duration_us=60_000_021)

    for field, value in (
        ("sample_rate_hz", 44_100),
        ("channels", 2),
        ("sample_format", "PCM_S16LE"),
    ):
        invalid = dict(record)
        invalid[field] = value
        assert list(_validator().iter_errors(invalid))
        with pytest.raises(ValueError, match="WAV format"):
            QuickCloneFutureSemanticFixture.from_fixture_dict(invalid)

    hash_mismatch = dict(record)
    hash_mismatch["staged_wav_sha256"] = _sha(32)
    with pytest.raises(ValueError, match="result output hash mismatch"):
        QuickCloneFutureSemanticFixture.from_fixture_dict(hash_mismatch)


def test_result_admission_matches_operation_profile_model_runtime_output_and_replay() -> None:
    result = _result()
    invalid_changes = (
        {"result_admission_receipt_sha256": None},
        {"result_render_operation_identity_sha256": _sha(80)},
        {"result_preview_profile_revision_sha256": _sha(81)},
        {"result_model_selection_binding_sha256": _sha(82)},
        {"result_runtime_aggregate_binding_sha256": _sha(83)},
        {"result_output_sha256": _sha(84)},
        {"result_route": "REMOTE"},
        {"result_replay": True},
        {"result_admission_state": ResultAdmissionState.NOT_BOUND},
    )
    for changes in invalid_changes:
        with pytest.raises(ValueError):
            replace(result, **changes)


def test_unknown_requires_same_operation_reconciliation_and_never_replay() -> None:
    dispatching = _dispatching()
    unknown = replace(
        dispatching,
        revision=dispatching.revision + 1,
        parent_revision_sha256=dispatching.flow_revision_sha256,
        created_at="2026-09-01T00:03:00Z",
        execution_state=ExecutionState.UNKNOWN,
        reason_codes=("DISPATCH_AMBIGUOUS",),
    )
    validate_flow_transition(dispatching, unknown)

    reconciled = _result(unknown)
    with pytest.raises(ValueError, match="reconciliation"):
        validate_flow_transition(unknown, reconciled)

    reconciled = replace(reconciled, reconciliation_receipt_sha256=_sha(33))
    validate_flow_transition(unknown, reconciled)

    replayed_operation = replace(
        reconciled,
        revision=reconciled.revision + 1,
        parent_revision_sha256=reconciled.flow_revision_sha256,
        created_at="2026-09-01T00:04:00Z",
        render_operation_identity_sha256=_sha(34),
        result_render_operation_identity_sha256=_sha(34),
    )
    with pytest.raises(ValueError, match="render_operation_identity_sha256 cannot change"):
        validate_flow_transition(reconciled, replayed_operation)

    duplicate_revision = replace(
        reconciled,
        revision=unknown.revision,
        parent_revision_sha256=unknown.flow_revision_sha256,
    )
    with pytest.raises(ValueError, match="sequence"):
        validate_flow_transition(unknown, duplicate_revision)
    assert reconciled.to_dict()["automatic_retry_authorized"] is False


def test_post_bind_receipts_and_terminal_states_are_monotonic() -> None:
    unknown = replace(
        _dispatching(),
        revision=4,
        parent_revision_sha256=_dispatching().flow_revision_sha256,
        created_at="2026-09-01T00:03:00Z",
        execution_state=ExecutionState.UNKNOWN,
        reason_codes=("DISPATCH_AMBIGUOUS",),
    )
    reconciled = replace(
        _result(unknown),
        reconciliation_receipt_sha256=_sha(85),
    )
    validate_flow_transition(unknown, reconciled)
    accepted = _accepted(reconciled)
    validate_flow_transition(reconciled, accepted)

    changed_receipt = replace(
        accepted,
        revision=accepted.revision + 1,
        parent_revision_sha256=accepted.flow_revision_sha256,
        created_at="2026-09-01T00:05:00Z",
        result_receipt_sha256=_sha(86),
    )
    with pytest.raises(ValueError, match="result_receipt_sha256 cannot change"):
        validate_flow_transition(accepted, changed_receipt)

    cleared_reconciliation = replace(
        accepted,
        revision=accepted.revision + 1,
        parent_revision_sha256=accepted.flow_revision_sha256,
        created_at="2026-09-01T00:05:00Z",
        reconciliation_receipt_sha256=None,
    )
    with pytest.raises(ValueError, match="reconciliation_receipt_sha256 cannot change"):
        validate_flow_transition(accepted, cleared_reconciliation)

    retention_rewind = replace(
        accepted,
        revision=accepted.revision + 1,
        parent_revision_sha256=accepted.flow_revision_sha256,
        created_at="2026-09-01T00:05:00Z",
        reference_retention_state=ReferenceRetentionState.UNDECIDED,
        reference_retention_decision_sha256=None,
    )
    with pytest.raises(ValueError, match="reference_retention_state"):
        validate_flow_transition(accepted, retention_rewind)


def test_quality_and_owner_listening_gate_profile_and_asset_decisions() -> None:
    result = _result()
    with pytest.raises(ValueError, match="quality PASS"):
        replace(
            result,
            quality_state=QualityState.FAIL,
            quality_receipt_sha256=_sha(40),
            owner_listening_state=OwnerListeningState.ACCEPTED,
            owner_listening_receipt_sha256=_sha(41),
        )
    with pytest.raises(ValueError, match="positive adoption"):
        replace(result, profile_adoption_state=ProfileAdoptionState.SAVE_DECISION_REQUIRED)

    accepted = _accepted(result)
    validate_flow_transition(result, accepted)
    assert accepted.profile_adoption_state is ProfileAdoptionState.SAVE_DECISION_REQUIRED
    assert accepted.reference_retention_state is ReferenceRetentionState.RETAIN_PRIVATE_REFERENCE
    assert accepted.preview_asset_adoption_state is PreviewAssetAdoptionState.PUBLISH_DECISION_REQUIRED
    with pytest.raises(ValueError, match="fixture-only"):
        public_projection(accepted)


def test_failed_or_rejected_preview_can_record_explicit_no_adoption() -> None:
    result = _result()
    rejected = replace(
        result,
        revision=result.revision + 1,
        parent_revision_sha256=result.flow_revision_sha256,
        created_at="2026-09-01T00:04:00Z",
        quality_state=QualityState.FAIL,
        quality_receipt_sha256=_sha(90),
        owner_listening_state=OwnerListeningState.REJECTED,
        owner_listening_receipt_sha256=_sha(91),
        profile_adoption_state=ProfileAdoptionState.PROFILE_NOT_SAVED,
        profile_adoption_receipt_sha256=_sha(92),
        preview_asset_adoption_state=PreviewAssetAdoptionState.ASSET_NOT_PUBLISHED,
        asset_adoption_receipt_sha256=_sha(93),
        reference_retention_state=ReferenceRetentionState.DO_NOT_RETAIN_PRIVATE_REFERENCE,
        reference_retention_decision_sha256=_sha(94),
    )
    validate_flow_transition(result, rejected)
    assert rejected.profile_adoption_state is ProfileAdoptionState.PROFILE_NOT_SAVED
    assert rejected.preview_asset_adoption_state is PreviewAssetAdoptionState.ASSET_NOT_PUBLISHED
    assert rejected.to_dict()["physical_delete_authorized"] is False


def test_profile_save_and_preview_asset_publish_are_separate_decisions() -> None:
    accepted = _accepted()
    saved_profile = replace(
        accepted,
        revision=accepted.revision + 1,
        parent_revision_sha256=accepted.flow_revision_sha256,
        created_at="2026-09-01T00:05:00Z",
        profile_adoption_state=ProfileAdoptionState.SAVED_LOCAL_CANDIDATE,
        saved_profile_revision_sha256=_sha(50),
        profile_adoption_receipt_sha256=_sha(51),
    )
    validate_flow_transition(accepted, saved_profile)
    assert saved_profile.preview_asset_adoption_state is PreviewAssetAdoptionState.PUBLISH_DECISION_REQUIRED

    not_saved_but_published = replace(
        accepted,
        revision=accepted.revision + 1,
        parent_revision_sha256=accepted.flow_revision_sha256,
        created_at="2026-09-01T00:05:00Z",
        profile_adoption_state=ProfileAdoptionState.PROFILE_NOT_SAVED,
        profile_adoption_receipt_sha256=_sha(52),
        preview_asset_adoption_state=PreviewAssetAdoptionState.ASSET_PUBLISHED_RESTRICTED,
        preview_asset_ref="asset:restricted/preview-1",
        preview_asset_sha256=_sha(53),
        asset_adoption_receipt_sha256=_sha(54),
    )
    validate_flow_transition(accepted, not_saved_but_published)
    assert not_saved_but_published.profile_adoption_state is ProfileAdoptionState.PROFILE_NOT_SAVED
    assert (
        not_saved_but_published.preview_asset_adoption_state
        is PreviewAssetAdoptionState.ASSET_PUBLISHED_RESTRICTED
    )
    assert not_saved_but_published.to_dict()["physical_delete_authorized"] is False

    with pytest.raises(ValueError, match="reference retention"):
        replace(
            saved_profile,
            reference_retention_state=ReferenceRetentionState.DO_NOT_RETAIN_PRIVATE_REFERENCE,
        )


def test_stale_revoked_and_expired_states_require_fresh_currentness_receipts() -> None:
    accepted = _accepted()
    adopted = replace(
        accepted,
        revision=accepted.revision + 1,
        parent_revision_sha256=accepted.flow_revision_sha256,
        created_at="2026-09-01T00:05:00Z",
        profile_adoption_state=ProfileAdoptionState.SAVED_LOCAL_CANDIDATE,
        saved_profile_revision_sha256=_sha(110),
        profile_adoption_receipt_sha256=_sha(111),
        preview_asset_adoption_state=PreviewAssetAdoptionState.ASSET_PUBLISHED_RESTRICTED,
        preview_asset_ref="asset:restricted/preview-currentness",
        preview_asset_sha256=_sha(112),
        asset_adoption_receipt_sha256=_sha(113),
    )
    validate_flow_transition(accepted, adopted)

    with pytest.raises(ValueError, match="profile_currentness_receipt_sha256"):
        replace(
            adopted,
            profile_adoption_state=ProfileAdoptionState.STALE,
            reference_retention_state=ReferenceRetentionState.EXPIRED,
            reference_retention_currentness_receipt_sha256=_sha(114),
        )
    with pytest.raises(ValueError, match="preview_asset_currentness_receipt_sha256"):
        replace(
            adopted,
            preview_asset_adoption_state=PreviewAssetAdoptionState.STALE,
        )
    with pytest.raises(ValueError, match="reference_retention_currentness_receipt_sha256"):
        replace(
            adopted,
            profile_adoption_state=ProfileAdoptionState.STALE,
            profile_currentness_receipt_sha256=_sha(115),
            reference_retention_state=ReferenceRetentionState.EXPIRED,
        )

    stale = replace(
        adopted,
        revision=adopted.revision + 1,
        parent_revision_sha256=adopted.flow_revision_sha256,
        created_at="2026-09-01T00:06:00Z",
        profile_adoption_state=ProfileAdoptionState.STALE,
        profile_currentness_receipt_sha256=_sha(115),
        preview_asset_adoption_state=PreviewAssetAdoptionState.STALE,
        preview_asset_currentness_receipt_sha256=_sha(116),
        reference_retention_state=ReferenceRetentionState.EXPIRED,
        reference_retention_currentness_receipt_sha256=_sha(117),
    )
    validate_flow_transition(adopted, stale)


@pytest.mark.parametrize(
    "leaked_ref",
    [
        "C:/Users/owner/private.wav",
        "C:Users/owner/private.wav",
        "/home/owner/private.wav",
        r"\\server\private\voice.wav",
        "file:///C:/Users/owner/private.wav",
        "https://private.example/voice.wav",
        "private/voice.wav",
        "voice.wav",
    ],
)
def test_host_or_private_paths_are_rejected(
    leaked_ref: str,
) -> None:
    with pytest.raises(ValueError, match="invalid|logical identifier"):
        replace(_result(), staged_wav_ref=leaked_ref)


@pytest.mark.parametrize(
    "leaked_id",
    [
        "private/voice.wav",
        "voice.wav",
        "quick-clone:private/voice.wav",
        "asset:restricted/preview-1",
    ],
)
def test_public_flow_id_requires_the_closed_quick_clone_namespace(
    leaked_id: str,
) -> None:
    with pytest.raises(ValueError, match="flow_id is invalid"):
        _draft(flow_id=leaked_id)
    record = _draft().to_dict()
    record["flow_id"] = leaked_id
    assert list(_validator().iter_errors(record))


@pytest.mark.parametrize(
    "leaked_ref",
    ["private/preview.wav", "preview.wav", "asset:../preview", "staged-narration:job/preview.wav"],
)
def test_asset_ref_requires_the_closed_asset_namespace(leaked_ref: str) -> None:
    with pytest.raises(ValueError, match="preview_asset_ref is invalid"):
        replace(
            _accepted(),
            profile_adoption_state=ProfileAdoptionState.PROFILE_NOT_SAVED,
            profile_adoption_receipt_sha256=_sha(152),
            preview_asset_adoption_state=PreviewAssetAdoptionState.ASSET_PUBLISHED_RESTRICTED,
            preview_asset_ref=leaked_ref,
            preview_asset_sha256=_sha(153),
            asset_adoption_receipt_sha256=_sha(154),
        )


def test_current_contract_cannot_self_assert_task014_result_admission() -> None:
    with pytest.raises(ValueError, match="execution is blocked"):
        _draft(
            setup_state=SetupState.READY,
            execution_state=ExecutionState.READY_FOR_CONFIRMATION,
            compute_resolution_state=ComputeResolutionState.GPU_READY,
            runtime_aggregate_state=RuntimeAggregateState.BOUND_VERIFIED,
            runtime_aggregate_binding_sha256=_sha(70),
            preflight_sha256=_sha(7),
            one_shot_authorization_sha256=_sha(8),
        )

    future_record = _result().to_dict()
    assert list(_validator().iter_errors(future_record))
    with pytest.raises(ValueError, match="identity is invalid"):
        QuickCloneFlowRevision.from_dict(future_record)
    with pytest.raises(ValueError, match="fixture-only"):
        public_projection(_result())

    forged = dict(future_record)
    forged["task014_result_admission_producer_state"] = "NOT_BOUND"
    with pytest.raises(ValueError, match="producer is NOT_BOUND"):
        QuickCloneFlowRevision.from_dict(forged)

    projection = public_projection(_draft())
    assert projection["task014_result_admission_producer_state"] == "NOT_BOUND"
    assert projection["result_binding_verified"] is False
    assert projection["preview_ready_for_external_playback"] is False


def test_schema_rejects_structural_cross_field_drift_before_python_ingress() -> None:
    validator = _validator()
    draft = _draft().to_dict()
    ready = _ready().to_dict()

    structural_negatives = []
    changed = dict(draft)
    changed["created_at"] = "2026-09-01T09:00:00+09:00"
    structural_negatives.append(changed)
    changed = dict(draft)
    changed["preflight_sha256"] = _sha(100)
    structural_negatives.append(changed)
    changed = dict(ready)
    changed["one_shot_authorization_sha256"] = None
    structural_negatives.append(changed)
    changed = dict(ready)
    changed["runtime_aggregate_binding_sha256"] = None
    structural_negatives.append(changed)
    changed = dict(draft)
    changed["result_admission_state"] = "BOUND_VERIFIED"
    structural_negatives.append(changed)

    for invalid in structural_negatives:
        assert list(validator.iter_errors(invalid))


def test_python_ingress_enforces_future_semantics_json_schema_cannot_express() -> None:
    validator = _validator()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert "canonical semantic ingress" in schema["$comment"]

    duration_drift = _result().to_dict()
    duration_drift["duration_us"] += 1
    assert list(validator.iter_errors(duration_drift))
    with pytest.raises(ValueError, match="exact sample count"):
        QuickCloneFutureSemanticFixture.from_fixture_dict(duration_drift)

    digest_echo_drift = _result().to_dict()
    digest_echo_drift["result_preview_profile_revision_sha256"] = _sha(101)
    assert list(validator.iter_errors(digest_echo_drift))
    with pytest.raises(ValueError, match="VoiceProfile"):
        QuickCloneFutureSemanticFixture.from_fixture_dict(digest_echo_drift)

    blocked = _draft(
        execution_state=ExecutionState.PREFLIGHT_BLOCKED,
        preflight_sha256=_sha(102),
        reason_codes=("A_REASON", "Z_REASON"),
    ).to_dict()
    blocked["reason_codes"] = ["Z_REASON", "A_REASON"]
    assert not list(validator.iter_errors(blocked))
    with pytest.raises(ValueError, match="sorted"):
        QuickCloneFlowRevision.from_dict(blocked)


@pytest.mark.parametrize(
    "invalid_reason_codes",
    [
        {"A_REASON": None},
        {"A_REASON": "A_REASON"},
        ("A_REASON",),
        "A_REASON",
        True,
        [True],
    ],
)
def test_wire_reason_codes_require_a_json_string_array(
    invalid_reason_codes: object,
) -> None:
    record = _draft(
        execution_state=ExecutionState.PREFLIGHT_BLOCKED,
        preflight_sha256=_sha(103),
        reason_codes=("A_REASON",),
    ).to_dict()
    record["reason_codes"] = invalid_reason_codes
    assert list(_validator().iter_errors(record))
    with pytest.raises(ValueError, match="JSON array of strings"):
        QuickCloneFlowRevision.from_dict(record)


def test_raw_body_unknown_fields_and_effect_flags_fail_closed() -> None:
    record = _draft().to_dict()
    leaked = dict(record)
    leaked["raw_audio_body"] = "base64-private-audio"
    assert list(_validator().iter_errors(leaked))
    with pytest.raises(ValueError, match="incomplete or unknown"):
        QuickCloneFlowRevision.from_dict(leaked)

    for field in (
        "private_body_embedded",
        "host_path_persisted",
        "secret_persisted",
        "effect_authorized",
        "automatic_retry_authorized",
        "physical_delete_authorized",
    ):
        changed = dict(record)
        changed[field] = True
        assert list(_validator().iter_errors(changed))
        with pytest.raises(ValueError, match="no-effect boundary"):
            QuickCloneFlowRevision.from_dict(changed)


def test_reason_codes_and_revision_cas_fail_closed() -> None:
    with pytest.raises(ValueError, match="require reason_codes"):
        _draft(
            execution_state=ExecutionState.PREFLIGHT_BLOCKED,
            preflight_sha256=_sha(60),
        )
    with pytest.raises(ValueError, match="sorted"):
        _draft(reason_codes=("Z_REASON", "A_REASON"))
    with pytest.raises(ValueError, match="unique"):
        _draft(reason_codes=("A_REASON", "A_REASON"))

    draft = _fixture_draft()
    wrong_parent = replace(
        _ready(draft),
        parent_revision_sha256=_sha(61),
    )
    with pytest.raises(ValueError, match="parent CAS"):
        validate_flow_transition(draft, wrong_parent)

    backwards = replace(_ready(draft), created_at="2026-08-31T23:59:59Z")
    with pytest.raises(ValueError, match="created_at cannot move backwards"):
        validate_flow_transition(draft, backwards)
