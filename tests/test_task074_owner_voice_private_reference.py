from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ai_video_production.owner_voice_private_reference import (
    CapabilityLeaseV1Current,
    CapabilityLeaseV2Current,
    EffectTruth,
    MEDIA_POLICY_SHA256,
    OwnerVoiceReferenceMediaFacts,
    OwnerVoiceReferencePreparePlan,
    OwnerVoiceReferenceTranscriptFacts,
    ReferenceChildAbortRecoveryReadback,
    ReferenceDomainSnapshot,
    ReferenceLifecycle,
    ReferenceSourceClassification,
    ReferenceTerminalRetireRequest,
    ReferenceTerminalRetireReadback,
    ReferenceV1RevokeFinalizeReadback,
    ReferenceTransition,
    ReferenceV2IssueOrRevokeReadback,
    RemoteRoleState,
    RetainedObject,
    RetentionPolicy,
    RevokeExpiryIntent,
    SpawnTruth,
    Task046OwnerReferenceTranscriptBindingFixture,
    TerminalKind,
    TerminalHistoryDisposition,
    TerminalRetireAction,
    TerminalRetireOutcome,
    V1RevokeFinalizeOutcome,
    V2IssueOrRevokeOutcome,
    owner_voice_reference_media_policy,
    validate_reference_transition,
    validate_terminal_retire_transaction,
    validate_v1_finalize_predecessor,
    validate_v2_mint_predecessor,
    validate_v2_terminal_retire_predecessor,
)
from ai_video_production.serialization import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "owner_voice_private_reference.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "owner_voice_private_reference.schema.json"
FIXTURE_MANIFEST = ROOT / "tests" / "fixtures" / "task074" / "fixture-manifest.json"
NOW = "2026-09-01T09:00:00Z"


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def test_task074_fixture_manifest_is_metadata_only_non_biometric_and_effect_zero() -> None:
    manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest == {
        "fixture_version": "TASK074_BODY_FREE_FIXTURE_MANIFEST_V1",
        "task_id": "TASK-074",
        "atomic_unit": "TASK074-B",
        "fixture_kind": "METADATA_ONLY_NON_BIOMETRIC",
        "contract_families": [
            "OWNER_VOICE_AUTHORITY",
            "OWNER_VOICE_PRIVATE_REFERENCE_BODY_FREE",
            "VOICE_PROFILE_ROUTE_SELECTION",
        ],
        "positive_vectors": [
            "DURABLE_ZERO_SHOT_SELECTION",
            "DURABLE_FINE_TUNED_SELECTION",
            "EPHEMERAL_NON_EXECUTABLE_SELECTION",
            "REFERENCE_LIFECYCLE_TYPED_SNAPSHOT",
            "TASK074_TO_TASK075_ZERO_SHOT_V2",
            "TASK074_TO_TASK075_FINE_TUNED_V2",
        ],
        "negative_vector_families": [
            "AUTHORITY_ESCALATION",
            "BODY_OR_HOST_PATH_LEAKAGE",
            "CAS_LINEAGE_MISMATCH",
            "CANONICAL_PRODUCER_FIXTURE_CONFUSION",
            "CROSS_ROUTE_UNION_MIX",
            "PRIVATE_REFERENCE_STATE_MISMATCH",
            "RETIREMENT_OPERATION_IDENTITY_REPLAY",
            "STALE_OR_NOT_CONFIRMED_PRODUCER",
            "TERMINAL_HISTORY_OR_EVENT_CROSS_BINDING",
            "TRUSTED_TIME_ROLLBACK",
            "WRONG_MEDIA_OR_TRANSCRIPT_POLICY",
        ],
        "contains_audio_body": False,
        "contains_pcm_or_wav": False,
        "contains_transcript_body": False,
        "contains_host_path": False,
        "contains_private_capability": False,
        "contains_secret_or_credential": False,
        "model_download_or_load_performed": False,
        "native_or_provider_effect_performed": False,
        "private_voice_upload_performed": False,
        "wav_generation_performed": False,
    }


def media() -> OwnerVoiceReferenceMediaFacts:
    return OwnerVoiceReferenceMediaFacts.create(
        codec_name="pcm_s24le",
        valid_bits_per_sample=24,
        sample_rate_hz=48000,
        duration_ms=30000,
        decoded_frame_count=1440000,
        container_size_bytes=4320044,
        audio_sha256=digest("synthetic-non-audio-sentinel-identity"),
    )


def transcript() -> OwnerVoiceReferenceTranscriptFacts:
    return OwnerVoiceReferenceTranscriptFacts.create(
        transcript_utf8_sha256=digest("body-free-transcript-binding"),
        unicode_scalar_count=120,
        utf8_byte_count=240,
    )


def transcript_binding() -> Task046OwnerReferenceTranscriptBindingFixture:
    return Task046OwnerReferenceTranscriptBindingFixture.create(
        binding_id="task046.reference.binding.1",
        project_id="project.alpha",
        voice_profile_id="voice.owner",
        voice_profile_revision_sha256=digest("voice-profile"),
        consent_current_evaluation_sha256=digest("consent-current"),
        audio_source_identity_sha256=digest("source-identity"),
        audio_sha256=media().to_dict()["audio_sha256"],
        transcript_revision=3,
        transcript_utf8_sha256=transcript().to_dict()["transcript_utf8_sha256"],
        transcript_facts_sha256=transcript().to_dict()["transcript_facts_sha256"],
        human_verification_receipt_sha256=digest("human-match"),
        verified_at=NOW,
    )


def snapshot(
    *,
    lifecycle: ReferenceLifecycle = ReferenceLifecycle.PREPARED,
    retained: RetainedObject = RetainedObject.PUBLISHED,
    retained_generation: int = 1,
    retained_revision: str | None = None,
    v1: CapabilityLeaseV1Current = CapabilityLeaseV1Current.NONE,
    v1_count: int = 0,
    v2: CapabilityLeaseV2Current = CapabilityLeaseV2Current.V2_ABSENT,
    v2_count: int = 0,
    intent: RevokeExpiryIntent = RevokeExpiryIntent.ABSENT,
    revision: int = 1,
    predecessor: str | None = None,
    fence_revision: int = 1,
    predecessor_fence: str | None = None,
    v1_history: str | None = None,
    v2_history: str | None = None,
    trusted_time: str | None = None,
    operation: str | None = "operation.reference.1",
    semantic_operation_key: str = "narration.operation.1",
    last_retired_operation: str | None = None,
    last_retired_semantic_operation_key: str | None = None,
    committed_event: str | None = None,
    purge_action: str | None = None,
    ownership_recovery: str | None = None,
) -> ReferenceDomainSnapshot:
    v1_identity = None if v1 is CapabilityLeaseV1Current.NONE else digest(f"v1-lease:{operation}")
    v2_identity = None if v2 is CapabilityLeaseV2Current.V2_ABSENT else digest(f"v2-lease:{operation}")
    if v1 in {CapabilityLeaseV1Current.CONSUMED, CapabilityLeaseV1Current.BURNED, CapabilityLeaseV1Current.FAILED_CLOSED}:
        v1_history = v1_history or digest(f"v1-history:{operation}")
    if v2 in {CapabilityLeaseV2Current.CONSUMED, CapabilityLeaseV2Current.BURNED, CapabilityLeaseV2Current.FAILED_CLOSED}:
        v2_history = v2_history or digest(f"v2-history:{operation}")
    return ReferenceDomainSnapshot.create(
        reference_id="reference.owner.1",
        reference_revision=revision,
        predecessor_snapshot_sha256=predecessor,
        project_id="project.alpha",
        project_manifest_revision_sha256=digest("project-manifest"),
        voice_profile_id="voice.owner",
        voice_profile_revision_sha256=digest("voice-profile"),
        consent_current_evaluation_sha256=digest("consent-current"),
        route_selection_sha256=digest("selection"),
        reference_pair_sha256=digest("reference-pair"),
        reference_lifecycle=lifecycle,
        retained_object=retained,
        retained_object_generation=retained_generation,
        retained_object_revision_sha256=(
            retained_revision or digest(f"retained:{retained.value}:{retained_generation}")
        ),
        v1_state=v1,
        v1_lease_identity_sha256=v1_identity,
        v1_live_handle_count=v1_count,
        v1_terminal_history_sha256=v1_history,
        v2_state=v2,
        v2_lease_identity_sha256=v2_identity,
        v2_live_handle_count=v2_count,
        v2_terminal_history_sha256=v2_history,
        revoke_or_expiry_intent=intent,
        revoke_or_expiry_event_sha256=(None if intent is RevokeExpiryIntent.ABSENT else digest(f"intent:{intent.value}")),
        purge_human_action_receipt_sha256=(
            purge_action or digest("purge-human-action")
            if lifecycle in {ReferenceLifecycle.PURGE_PENDING, ReferenceLifecycle.PURGED, ReferenceLifecycle.PURGE_NOT_CONFIRMED}
            else None
        ),
        ownership_recovery_readback_sha256=(
            ownership_recovery or digest("ownership-recovery")
            if lifecycle in {ReferenceLifecycle.PURGE_PENDING, ReferenceLifecycle.PURGED, ReferenceLifecycle.PURGE_NOT_CONFIRMED}
            and retained in {RetainedObject.RECOVERABLE_RETAINED, RetainedObject.FOREIGN_PRESERVED}
            else ownership_recovery
        ),
        broker_domain_sha256=digest("broker-domain"),
        broker_process_identity_sha256=digest("broker-process"),
        broker_session_sha256=digest("broker-session"),
        product_build_sha256=digest("product-build"),
        broker_protocol_version="owner.voice.broker.v2",
        trusted_time_domain_sha256=digest("trusted-time-domain"),
        trusted_time_receipt_sha256=trusted_time,
        currentness_readback_sha256=digest(f"currentness:{revision}"),
        semantic_operation_key=semantic_operation_key,
        current_operation_id=operation,
        last_retired_semantic_operation_key=last_retired_semantic_operation_key,
        last_retired_operation_id=last_retired_operation,
        committed_event_sha256=committed_event or digest(f"committed-event:{revision}"),
        fence_revision=fence_revision,
        predecessor_fence_sha256=predecessor_fence,
        observed_at=NOW,
    )


def next_snapshot(previous: ReferenceDomainSnapshot, **overrides: object) -> ReferenceDomainSnapshot:
    before = previous.to_dict()
    values: dict[str, object] = {
        "lifecycle": ReferenceLifecycle(before["reference_lifecycle"]),
        "retained": RetainedObject(before["retained_object"]),
        "retained_generation": before["retained_object_generation"],
        "retained_revision": before["retained_object_revision_sha256"],
        "v1": CapabilityLeaseV1Current(before["v1_state"]),
        "v1_count": before["v1_live_handle_count"],
        "v2": CapabilityLeaseV2Current(before["v2_state"]),
        "v2_count": before["v2_live_handle_count"],
        "intent": RevokeExpiryIntent(before["revoke_or_expiry_intent"]),
        "revision": before["reference_revision"] + 1,
        "predecessor": before["snapshot_sha256"],
        "fence_revision": before["fence_revision"] + 1,
        "predecessor_fence": before["fence_sha256"],
        "v1_history": before["v1_terminal_history_sha256"],
        "v2_history": before["v2_terminal_history_sha256"],
        "trusted_time": before["trusted_time_receipt_sha256"],
        "operation": before["current_operation_id"],
        "semantic_operation_key": before["semantic_operation_key"],
        "last_retired_operation": before["last_retired_operation_id"],
        "last_retired_semantic_operation_key": before["last_retired_semantic_operation_key"],
        "committed_event": digest(f"committed-event:{before['reference_revision'] + 1}"),
        "purge_action": before["purge_human_action_receipt_sha256"],
        "ownership_recovery": before["ownership_recovery_readback_sha256"],
    }
    values.update(overrides)
    return snapshot(**values)


def terminal_retire_request(
    *,
    terminal: TerminalKind,
    action: TerminalRetireAction = TerminalRetireAction.RETIRE,
) -> ReferenceTerminalRetireRequest:
    history = digest(f"terminal-history:{terminal.value}")
    lease = digest(f"terminal-lease:{terminal.value}")
    return ReferenceTerminalRetireRequest.create(
        operation_id=f"operation.retire.{terminal.value.lower()}",
        semantic_operation_key="narration.operation.terminal.retire",
        retired_operation_id=f"operation.terminal.{terminal.value.lower()}",
        retired_semantic_operation_key="narration.operation.terminal.source",
        requested_action=action,
        terminal_kind=terminal,
        retired_lease_identity_sha256=lease,
        terminal_readback_sha256=digest("terminal-readback"),
        consumer_two_role_close_readback_sha256=(
            digest("consumer-two-role-close") if terminal is TerminalKind.CONSUMED else None
        ),
        burn_abort_close_readback_sha256=(
            digest("burn-abort-close") if terminal is TerminalKind.BURNED else None
        ),
        failed_closed_gate_proof_sha256=(
            digest("failed-closed-gates") if terminal is TerminalKind.FAILED_CLOSED else None
        ),
        expected_fence_revision=5,
        expected_fence_sha256=digest("terminal-fence-before"),
        predecessor_snapshot_sha256=digest("terminal-snapshot-before"),
        expected_terminal_history_event_sha256=digest("terminal-history-event"),
        expected_terminal_history_sha256=history,
        trusted_time_receipt_sha256=digest("trusted-time"),
        broker_domain_sha256=digest("broker-domain"),
        broker_process_identity_sha256=digest("broker-process"),
        broker_session_sha256=digest("broker-session"),
        product_build_sha256=digest("product-build"),
        broker_protocol_version="owner.voice.broker.v2",
    )


def terminal_retire_readback(
    *,
    terminal: TerminalKind,
    outcome: TerminalRetireOutcome,
    action: TerminalRetireAction = TerminalRetireAction.RETIRE,
) -> ReferenceTerminalRetireReadback:
    request = terminal_retire_request(terminal=terminal, action=action)
    history = digest(f"terminal-history:{terminal.value}")
    lease = digest(f"terminal-lease:{terminal.value}")
    committed_outcomes = {
        TerminalRetireOutcome.CONSUMED_RETIRED,
        TerminalRetireOutcome.BURNED_RETIRED,
        TerminalRetireOutcome.FAILED_CLOSED_RETIRED_NOT_CONFIRMED,
        TerminalRetireOutcome.TERMINAL_REVOKE_COMMITTED,
        TerminalRetireOutcome.TERMINAL_EXPIRY_COMMITTED,
    }
    unknown = outcome is TerminalRetireOutcome.OUTCOME_NOT_CONFIRMED
    no_commit = outcome is TerminalRetireOutcome.NO_COMMIT_TERMINAL_STILL_CURRENT
    stale = outcome is TerminalRetireOutcome.STALE_OTHER_COMMIT
    if outcome in committed_outcomes:
        result_revision = 6
        result_fence = digest("terminal-fence-after")
        result_snapshot = digest("terminal-snapshot-after")
        committed_event = digest("terminal-commit-event")
        result_lifecycle = (
            ReferenceLifecycle.PREPARED
            if action is TerminalRetireAction.RETIRE
            else ReferenceLifecycle.REVOKED
        )
        result_v2 = CapabilityLeaseV2Current.V2_ABSENT
        result_v2_identity = None
        result_intent = {
            TerminalRetireAction.RETIRE: RevokeExpiryIntent.ABSENT,
            TerminalRetireAction.EXPLICIT_REVOKE: RevokeExpiryIntent.EXPLICIT_REVOKE,
            TerminalRetireAction.TRUSTED_TIME_EXPIRY: RevokeExpiryIntent.TRUSTED_TIME_EXPIRY,
        }[action]
    elif no_commit:
        result_revision = 5
        result_fence = digest("terminal-fence-before")
        result_snapshot = digest("terminal-snapshot-before")
        committed_event = None
        result_lifecycle = ReferenceLifecycle.PREPARED
        result_v2 = CapabilityLeaseV2Current(terminal.value)
        result_v2_identity = lease
        result_intent = RevokeExpiryIntent.ABSENT
    elif stale:
        result_revision = 7
        result_fence = digest("terminal-other-fence")
        result_snapshot = digest("terminal-other-snapshot")
        committed_event = digest("terminal-other-commit")
        result_lifecycle = ReferenceLifecycle.REVOKED
        result_v2 = CapabilityLeaseV2Current.V2_ABSENT
        result_v2_identity = None
        result_intent = RevokeExpiryIntent.EXPLICIT_REVOKE
    else:
        result_revision = None
        result_fence = None
        result_snapshot = None
        committed_event = None
        result_lifecycle = None
        result_v2 = None
        result_v2_identity = None
        result_intent = None
    body_effect = {
        TerminalKind.CONSUMED: EffectTruth.OBSERVED,
        TerminalKind.BURNED: EffectTruth.ZERO,
        TerminalKind.FAILED_CLOSED: EffectTruth.NOT_CONFIRMED,
    }[terminal]
    return ReferenceTerminalRetireReadback.create(
        request=request,
        result_fence_revision=result_revision,
        result_fence_sha256=result_fence,
        result_snapshot_sha256=result_snapshot,
        committed_event_sha256=committed_event,
        terminal_history_event_sha256=None if unknown else digest("terminal-history-event"),
        terminal_history_sha256=None if unknown else history,
        terminal_history_disposition=(
            TerminalHistoryDisposition.NOT_CONFIRMED
            if unknown
            else TerminalHistoryDisposition.EXACT_PRESENT
        ),
        history_append_count=0,
        outcome=outcome,
        result_lifecycle=result_lifecycle,
        result_retained_object=None if unknown else RetainedObject.PUBLISHED,
        result_v1_state=None if unknown else CapabilityLeaseV1Current.NONE,
        result_v1_lease_identity_sha256=None,
        result_v1_handle_count=None if unknown else 0,
        result_v1_terminal_history_sha256=None,
        result_v2_state=result_v2,
        result_v2_lease_identity_sha256=result_v2_identity,
        result_v2_handle_count=None if unknown else 0,
        result_v2_terminal_history_sha256=(
            None if unknown or stale else history
        ),
        result_revoke_or_expiry_intent=result_intent,
        result_revoke_or_expiry_event_sha256=(
            digest("terminal-revoke-event")
            if result_intent in {
                RevokeExpiryIntent.EXPLICIT_REVOKE,
                RevokeExpiryIntent.TRUSTED_TIME_EXPIRY,
            }
            else None
        ),
        body_effect=body_effect,
        model_effect=body_effect,
        readback_at=NOW,
    )


def transaction_retire_request(
    predecessor: ReferenceDomainSnapshot,
    terminal: TerminalKind,
    *,
    operation_id: str = "operation.retire.transaction",
    semantic_operation_key: str = "narration.operation.retire.transaction",
) -> ReferenceTerminalRetireRequest:
    before = predecessor.to_dict()
    return ReferenceTerminalRetireRequest.create(
        operation_id=operation_id,
        semantic_operation_key=semantic_operation_key,
        retired_operation_id=before["current_operation_id"],
        retired_semantic_operation_key=before["semantic_operation_key"],
        requested_action=TerminalRetireAction.RETIRE,
        terminal_kind=terminal,
        retired_lease_identity_sha256=before["v2_lease_identity_sha256"],
        terminal_readback_sha256=digest("transaction-terminal-readback"),
        consumer_two_role_close_readback_sha256=(
            digest("transaction-consumer-two-role-close")
            if terminal is TerminalKind.CONSUMED
            else None
        ),
        burn_abort_close_readback_sha256=(
            digest("transaction-burn-abort-close") if terminal is TerminalKind.BURNED else None
        ),
        failed_closed_gate_proof_sha256=(
            digest("transaction-failed-closed-gates")
            if terminal is TerminalKind.FAILED_CLOSED
            else None
        ),
        expected_fence_revision=before["fence_revision"],
        expected_fence_sha256=before["fence_sha256"],
        predecessor_snapshot_sha256=before["snapshot_sha256"],
        expected_terminal_history_event_sha256=digest("transaction-terminal-history-event"),
        expected_terminal_history_sha256=before["v2_terminal_history_sha256"],
        trusted_time_receipt_sha256=before["trusted_time_receipt_sha256"],
        broker_domain_sha256=before["broker_domain_sha256"],
        broker_process_identity_sha256=before["broker_process_identity_sha256"],
        broker_session_sha256=before["broker_session_sha256"],
        product_build_sha256=before["product_build_sha256"],
        broker_protocol_version=before["broker_protocol_version"],
    )


def terminal_retire_transaction(
    terminal: TerminalKind,
) -> tuple[
    ReferenceTerminalRetireRequest,
    ReferenceDomainSnapshot,
    ReferenceDomainSnapshot,
    ReferenceTerminalRetireReadback,
]:
    history = digest(f"transaction-history:{terminal.value}")
    before = snapshot(
        v2=CapabilityLeaseV2Current(terminal.value),
        v2_history=history,
        trusted_time=digest("trusted-time-transaction"),
        revision=5,
        predecessor=digest("transaction-snapshot-4"),
        fence_revision=5,
        predecessor_fence=digest("transaction-fence-4"),
        operation="operation.narration.transaction",
        semantic_operation_key="narration.operation.transaction",
    )
    request = transaction_retire_request(before, terminal)
    request_data = request.to_dict()
    after = next_snapshot(
        before,
        v2=CapabilityLeaseV2Current.V2_ABSENT,
        operation=request_data["operation_id"],
        semantic_operation_key=request_data["semantic_operation_key"],
        last_retired_operation=request_data["retired_operation_id"],
        last_retired_semantic_operation_key=request_data["retired_semantic_operation_key"],
        committed_event=digest("transaction-retire-commit"),
    )
    after_data = after.to_dict()
    outcome = {
        TerminalKind.CONSUMED: TerminalRetireOutcome.CONSUMED_RETIRED,
        TerminalKind.BURNED: TerminalRetireOutcome.BURNED_RETIRED,
        TerminalKind.FAILED_CLOSED: TerminalRetireOutcome.FAILED_CLOSED_RETIRED_NOT_CONFIRMED,
    }[terminal]
    effect = {
        TerminalKind.CONSUMED: EffectTruth.OBSERVED,
        TerminalKind.BURNED: EffectTruth.ZERO,
        TerminalKind.FAILED_CLOSED: EffectTruth.NOT_CONFIRMED,
    }[terminal]
    readback = ReferenceTerminalRetireReadback.create(
        request=request,
        result_fence_revision=after_data["fence_revision"],
        result_fence_sha256=after_data["fence_sha256"],
        result_snapshot_sha256=after_data["snapshot_sha256"],
        committed_event_sha256=after_data["committed_event_sha256"],
        terminal_history_event_sha256=request_data["expected_terminal_history_event_sha256"],
        terminal_history_sha256=history,
        terminal_history_disposition=TerminalHistoryDisposition.EXACT_PRESENT,
        history_append_count=0,
        outcome=outcome,
        result_lifecycle=ReferenceLifecycle(after_data["reference_lifecycle"]),
        result_retained_object=RetainedObject(after_data["retained_object"]),
        result_v1_state=CapabilityLeaseV1Current(after_data["v1_state"]),
        result_v1_lease_identity_sha256=after_data["v1_lease_identity_sha256"],
        result_v1_handle_count=after_data["v1_live_handle_count"],
        result_v1_terminal_history_sha256=after_data["v1_terminal_history_sha256"],
        result_v2_state=CapabilityLeaseV2Current(after_data["v2_state"]),
        result_v2_lease_identity_sha256=after_data["v2_lease_identity_sha256"],
        result_v2_handle_count=after_data["v2_live_handle_count"],
        result_v2_terminal_history_sha256=after_data["v2_terminal_history_sha256"],
        result_revoke_or_expiry_intent=RevokeExpiryIntent(
            after_data["revoke_or_expiry_intent"]
        ),
        result_revoke_or_expiry_event_sha256=after_data["revoke_or_expiry_event_sha256"],
        body_effect=effect,
        model_effect=effect,
        readback_at=NOW,
    )
    return request, before, after, readback


def v2_committed_readback(
    outcome: V2IssueOrRevokeOutcome,
    *,
    expected_v1_history: str | None = None,
    expected_v2_history: str | None = None,
) -> ReferenceV2IssueOrRevokeReadback:
    issue = outcome in {
        V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED,
        V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_NOT_CONFIRMED,
    }
    undelivered = outcome is V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_NOT_CONFIRMED
    if issue:
        lifecycle = ReferenceLifecycle.PREPARED
        v2 = CapabilityLeaseV2Current.BURNED if undelivered else CapabilityLeaseV2Current.ISSUED
        v2_identity = digest("v2-committed-lease")
        v2_count = 0 if undelivered else 2
        v2_history = (
            digest("v2-undelivered-burn-history")
            if undelivered
            else expected_v2_history
        )
        intent = RevokeExpiryIntent.ABSENT
        intent_event = None
        ack: bool | None = not undelivered
        issuance_effect = EffectTruth.OBSERVED
        handle_effect = EffectTruth.OBSERVED
    else:
        lifecycle = ReferenceLifecycle.REVOKED
        v2 = CapabilityLeaseV2Current.V2_ABSENT
        v2_identity = None
        v2_count = 0
        v2_history = expected_v2_history
        intent = (
            RevokeExpiryIntent.EXPLICIT_REVOKE
            if outcome is V2IssueOrRevokeOutcome.REVOKE_COMMITTED
            else RevokeExpiryIntent.TRUSTED_TIME_EXPIRY
        )
        intent_event = digest(f"intent-event:{intent.value}")
        ack = None
        issuance_effect = EffectTruth.ZERO
        handle_effect = EffectTruth.ZERO
    return ReferenceV2IssueOrRevokeReadback.create(
        operation_id=f"operation.v2.{outcome.value.lower()}",
        semantic_operation_key="narration.operation.v2.committed",
        request_sha256=digest(f"request:{outcome.value}"),
        outcome=outcome,
        expected_fence_revision=4,
        expected_fence_sha256=digest("v2-fence-before"),
        predecessor_snapshot_sha256=digest("v2-snapshot-before"),
        expected_v1_terminal_history_sha256=expected_v1_history,
        expected_v2_terminal_history_sha256=expected_v2_history,
        result_fence_revision=5,
        result_fence_sha256=digest("v2-fence-after"),
        result_snapshot_sha256=digest("v2-snapshot-after"),
        committed_event_sha256=digest(f"commit:{outcome.value}"),
        trusted_time_receipt_sha256=digest("trusted-time"),
        broker_domain_sha256=digest("broker-domain"),
        broker_process_identity_sha256=digest("broker-process"),
        broker_session_sha256=digest("broker-session"),
        product_build_sha256=digest("product-build"),
        broker_protocol_version="owner.voice.broker.v2",
        result_lifecycle=lifecycle,
        result_retained_object=RetainedObject.PUBLISHED,
        result_v1_state=CapabilityLeaseV1Current.NONE,
        result_v1_lease_identity_sha256=None,
        result_v1_handle_count=0,
        result_v1_terminal_history_sha256=expected_v1_history,
        result_v2_state=v2,
        result_v2_lease_identity_sha256=v2_identity,
        result_v2_handle_count=v2_count,
        result_v2_terminal_history_sha256=v2_history,
        result_revoke_or_expiry_intent=intent,
        result_revoke_or_expiry_event_sha256=intent_event,
        live_capability_delivery_acknowledged=ack,
        request_issuance_effect=issuance_effect,
        request_live_handle_effect=handle_effect,
        readback_at=NOW,
    )


def v1_finalize_readback(
    *,
    outcome: V1RevokeFinalizeOutcome,
    terminal: TerminalKind | None,
) -> ReferenceV1RevokeFinalizeReadback:
    lease = digest("v1-finalize-lease")
    history = digest(f"v1-history:{terminal.value if terminal else 'none'}")
    finalized = outcome in {
        V1RevokeFinalizeOutcome.V1_CONSUMED_REVOKE_FINALIZED,
        V1RevokeFinalizeOutcome.V1_BURNED_REVOKE_FINALIZED,
        V1RevokeFinalizeOutcome.V1_FAILED_CLOSED_REVOKE_FINALIZED_NOT_CONFIRMED,
    }
    awaiting = outcome is V1RevokeFinalizeOutcome.V1_TERMINAL_AWAITING_FINALIZE
    active = outcome is V1RevokeFinalizeOutcome.V1_ACTIVE_RECOVERY_REQUIRED
    stale = outcome is V1RevokeFinalizeOutcome.STALE_OTHER_COMMIT
    unknown = outcome is V1RevokeFinalizeOutcome.OUTCOME_NOT_CONFIRMED
    if finalized:
        result_revision = 8
        result_fence = digest("v1-fence-after")
        result_snapshot = digest("v1-snapshot-after")
        committed_event = digest("v1-finalize-event")
        result_lifecycle = ReferenceLifecycle.REVOKED
        result_v1 = CapabilityLeaseV1Current.NONE
        result_v1_identity = None
        result_v1_count = 0
        result_v1_history = history
    elif awaiting:
        result_revision = 7
        result_fence = digest("v1-fence-before")
        result_snapshot = digest("v1-snapshot-before")
        committed_event = None
        result_lifecycle = ReferenceLifecycle.REVOKE_PENDING
        result_v1 = CapabilityLeaseV1Current(terminal.value)  # type: ignore[union-attr]
        result_v1_identity = lease
        result_v1_count = 0
        result_v1_history = history
    elif active:
        result_revision = 7
        result_fence = digest("v1-fence-before")
        result_snapshot = digest("v1-snapshot-before")
        committed_event = None
        result_lifecycle = ReferenceLifecycle.REVOKE_PENDING
        result_v1 = CapabilityLeaseV1Current.ISSUED
        result_v1_identity = lease
        result_v1_count = 1
        result_v1_history = None
    elif stale:
        result_revision = 9
        result_fence = digest("v1-other-fence")
        result_snapshot = digest("v1-other-snapshot")
        committed_event = digest("v1-other-commit")
        result_lifecycle = ReferenceLifecycle.REVOKED
        result_v1 = CapabilityLeaseV1Current.NONE
        result_v1_identity = None
        result_v1_count = 0
        result_v1_history = None
    else:
        result_revision = None
        result_fence = None
        result_snapshot = None
        committed_event = None
        result_lifecycle = None
        result_v1 = None
        result_v1_identity = None
        result_v1_count = None
        result_v1_history = None
    terminal_known = terminal is not None
    body_effect = (
        EffectTruth.NOT_CONFIRMED
        if terminal is TerminalKind.FAILED_CLOSED or terminal is None
        else EffectTruth.OBSERVED if terminal is TerminalKind.CONSUMED else EffectTruth.ZERO
    )
    has_history = finalized or awaiting
    return ReferenceV1RevokeFinalizeReadback.create(
        operation_id=f"operation.v1.{outcome.value.lower()}",
        semantic_operation_key=".".join(("narration", "operation", "v1", "finalize")),
        request_sha256=digest(f"v1-request:{outcome.value}"),
        terminal_kind=terminal,
        v1_lease_identity_sha256=lease,
        terminal_readback_sha256=digest("v1-terminal-readback") if terminal_known else None,
        terminal_close_readback_sha256=(
            digest("v1-terminal-close")
            if terminal in {TerminalKind.CONSUMED, TerminalKind.BURNED}
            else None
        ),
        failed_closed_gate_proof_sha256=(
            digest("v1-failed-closed-gates") if terminal is TerminalKind.FAILED_CLOSED else None
        ),
        revoke_or_expiry_intent=RevokeExpiryIntent.EXPLICIT_REVOKE,
        revoke_or_expiry_event_sha256=digest("v1-revoke-event"),
        expected_fence_revision=7,
        expected_fence_sha256=digest("v1-fence-before"),
        predecessor_snapshot_sha256=digest("v1-snapshot-before"),
        result_fence_revision=result_revision,
        result_fence_sha256=result_fence,
        result_snapshot_sha256=result_snapshot,
        committed_event_sha256=committed_event,
        terminal_history_event_sha256=digest("v1-history-event") if has_history else None,
        terminal_history_sha256=history if has_history else None,
        terminal_history_disposition=(
            TerminalHistoryDisposition.EXACT_PRESENT
            if has_history
            else TerminalHistoryDisposition.NOT_CONFIRMED
        ),
        history_append_count=0,
        outcome=outcome,
        trusted_time_receipt_sha256=digest("trusted-time"),
        broker_domain_sha256=digest("broker-domain"),
        broker_process_identity_sha256=digest("broker-process"),
        broker_session_sha256=digest("broker-session"),
        product_build_sha256=digest("product-build"),
        broker_protocol_version="owner.voice.broker.v2",
        result_lifecycle=result_lifecycle,
        result_retained_object=None if unknown else RetainedObject.PUBLISHED,
        result_v1_state=result_v1,
        result_v1_lease_identity_sha256=result_v1_identity,
        result_v1_handle_count=result_v1_count,
        result_v1_terminal_history_sha256=result_v1_history,
        result_v2_state=None if unknown else CapabilityLeaseV2Current.V2_ABSENT,
        result_v2_lease_identity_sha256=None,
        result_v2_handle_count=None if unknown else 0,
        result_v2_terminal_history_sha256=None,
        result_revoke_or_expiry_intent=(
            None if unknown else RevokeExpiryIntent.EXPLICIT_REVOKE
        ),
        result_revoke_or_expiry_event_sha256=(
            None if unknown else digest("v1-revoke-event")
        ),
        body_effect=body_effect,
        model_effect=body_effect,
        readback_at=NOW,
    )


def test_media_policy_and_exact_pcm24_48k_mono_facts_are_deterministic() -> None:
    policy = owner_voice_reference_media_policy()
    assert policy["media_policy_sha256"] == MEDIA_POLICY_SHA256
    assert policy["channels"] == 1 and 48000 in policy["allowed_sample_rates_hz"]
    value = media().to_dict()
    assert value["codec_name"] == "pcm_s24le" and value["valid_bits_per_sample"] == 24
    assert value["sample_rate_hz"] == 48000 and value["channels"] == 1
    assert OwnerVoiceReferenceMediaFacts.from_dict(value).to_dict() == value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("audio_container_signature", "RF64/WAVE"),
        ("audio_stream_count", 2),
        ("video_stream_count", 1),
        ("codec_name", "pcm_f32le"),
        ("sample_format", "float"),
        ("valid_bits_per_sample", 32),
        ("sample_rate_hz", 96000),
        ("channels", 2),
        ("channel_layout", "stereo"),
        ("duration_ms", 999),
        ("duration_ms", 60001),
        ("decoded_frame_count", 0),
        ("decoded_frame_count", 2880001),
        ("container_size_bytes", 44),
        ("body_present", True),
        ("path_present", True),
    ],
)
def test_media_policy_negative_vectors_fail_closed(field: str, value: object) -> None:
    payload = media().to_dict()
    payload[field] = value
    with pytest.raises(ValueError):
        OwnerVoiceReferenceMediaFacts.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("strict_utf8_valid", False),
        ("bom_present", True),
        ("nfc_normalized", False),
        ("lf_only", False),
        ("nul_present", True),
        ("forbidden_control_present", True),
        ("post_admission_rewrite_performed", True),
        ("unicode_scalar_count", 0),
        ("unicode_scalar_count", 4001),
        ("utf8_byte_count", 0),
        ("utf8_byte_count", 16385),
        ("body_present", True),
    ],
)
def test_transcript_policy_negative_vectors_fail_closed(field: str, value: object) -> None:
    payload = transcript().to_dict()
    payload[field] = value
    with pytest.raises(ValueError):
        OwnerVoiceReferenceTranscriptFacts.from_dict(payload)


def test_task046_binding_fixture_is_exact_body_free_and_explicitly_unbound() -> None:
    value = transcript_binding().to_dict()
    assert value["semantic_owner"] == "TASK-074-FIXTURE"
    assert value["intended_semantic_owner"] == "TASK-046"
    assert value["producer_binding_state"] == "NOT_BOUND"
    assert value["fixture_only"] is True
    assert value["canonical_producer_receipt"] is False
    assert value["execution_ready"] is False
    assert value["task046_owner_acceptance_sha256"] is None
    assert value["speaker_profile_exact_match"] is True
    assert value["body_present"] is False and value["path_present"] is False
    assert Task046OwnerReferenceTranscriptBindingFixture.from_dict(value).to_dict() == value
    for field, replacement in (
        ("semantic_owner", "TASK-046"),
        ("producer_binding_state", "BOUND"),
        ("fixture_only", False),
        ("canonical_producer_receipt", True),
        ("execution_ready", True),
        ("task046_owner_acceptance_sha256", digest("fake-task046-acceptance")),
        ("speaker_profile_exact_match", False),
        ("transcript_audio_exact_match_human_verified", False),
        ("audio_sha256", digest("wrong-audio")),
    ):
        tampered = transcript_binding().to_dict()
        tampered[field] = replacement
        with pytest.raises(ValueError):
            Task046OwnerReferenceTranscriptBindingFixture.from_dict(tampered)


def test_prepare_plan_has_only_body_free_coordinates_and_expiry_is_closed() -> None:
    binding = transcript_binding()
    plan = OwnerVoiceReferencePreparePlan.create(
        operation_id="operation.prepare.1",
        project_id="project.alpha",
        project_manifest_revision_sha256=digest("manifest"),
        installed_context_sha256=digest("installed"),
        voice_profile_id="voice.owner",
        voice_profile_revision_sha256=digest("voice-profile"),
        consent_current_evaluation_sha256=digest("consent-current"),
        route_selection_sha256=digest("selection"),
        source_classification=ReferenceSourceClassification.TASK046_PRIVATE_RECORDING_REFERENCE,
        audio_source_identity_sha256=digest("audio-source"),
        transcript_source_identity_sha256=digest("transcript-source"),
        media_facts_sha256=media().to_dict()["media_facts_sha256"],
        transcript_facts_sha256=transcript().to_dict()["transcript_facts_sha256"],
        transcript_binding_receipt_sha256=binding.to_dict()["transcript_binding_receipt_sha256"],
        retention_policy=RetentionPolicy.OWNER_SELECTED_EXPIRY,
        retention_policy_revision_sha256=digest("retention"),
        expires_at="2026-10-01T09:00:00Z",
        expected_lifecycle_snapshot_sha256=digest("lifecycle-head"),
        human_action_receipt_sha256=digest("human-action"),
        task072_ticket_sha256=digest("ticket"),
        created_at=NOW,
    )
    value = plan.to_dict()
    assert value["private_body_present"] is False and value["path_present"] is False
    assert value["model_loaded"] is False and value["inference_started"] is False
    assert OwnerVoiceReferencePreparePlan.from_dict(value).to_dict() == value
    value["expires_at"] = None
    with pytest.raises(ValueError, match="requires expires_at"):
        OwnerVoiceReferencePreparePlan.from_dict(value)


@pytest.mark.parametrize(
    ("lifecycle", "retained", "v1", "v1_count", "v2", "v2_count", "intent"),
    [
        (ReferenceLifecycle.UNBOUND, RetainedObject.NONE, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.V2_ABSENT, 0, RevokeExpiryIntent.ABSENT),
        (ReferenceLifecycle.PREPARING, RetainedObject.ALLOCATED, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.V2_ABSENT, 0, RevokeExpiryIntent.ABSENT),
        (ReferenceLifecycle.PREPARE_FAILED_RETAINED, RetainedObject.RECONCILIATION_REQUIRED, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.V2_ABSENT, 0, RevokeExpiryIntent.ABSENT),
        (ReferenceLifecycle.PREPARED, RetainedObject.PUBLISHED, CapabilityLeaseV1Current.ISSUED, 1, CapabilityLeaseV2Current.V2_ABSENT, 0, RevokeExpiryIntent.ABSENT),
        (ReferenceLifecycle.PREPARED, RetainedObject.PUBLISHED, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.CHILD_TRANSFER_IN_FLIGHT, 3, RevokeExpiryIntent.ABSENT),
        (ReferenceLifecycle.PREPARED, RetainedObject.PUBLISHED, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.CONSUMED, 0, RevokeExpiryIntent.ABSENT),
        (ReferenceLifecycle.REVOKE_PENDING, RetainedObject.PUBLISHED, CapabilityLeaseV1Current.CONSUMED, 0, CapabilityLeaseV2Current.V2_ABSENT, 0, RevokeExpiryIntent.EXPLICIT_REVOKE),
        (ReferenceLifecycle.REVOKE_PENDING, RetainedObject.PUBLISHED, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.BODY_READ_STARTED, 2, RevokeExpiryIntent.TRUSTED_TIME_EXPIRY),
        (ReferenceLifecycle.REVOKED, RetainedObject.PUBLISHED, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.BURNED, 0, RevokeExpiryIntent.EXPLICIT_REVOKE),
        (ReferenceLifecycle.PURGE_PENDING, RetainedObject.KEY_REVOKED, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.V2_ABSENT, 0, RevokeExpiryIntent.EXPLICIT_REVOKE),
        (ReferenceLifecycle.PURGED, RetainedObject.PURGED, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.V2_ABSENT, 0, RevokeExpiryIntent.EXPLICIT_REVOKE),
        (ReferenceLifecycle.PURGE_NOT_CONFIRMED, RetainedObject.FOREIGN_PRESERVED, CapabilityLeaseV1Current.NONE, 0, CapabilityLeaseV2Current.V2_ABSENT, 0, RevokeExpiryIntent.ABSENT),
    ],
)
def test_joint_rl_v1_v2_ro_matrix_accepts_only_listed_typed_rows(
    lifecycle: ReferenceLifecycle,
    retained: RetainedObject,
    v1: CapabilityLeaseV1Current,
    v1_count: int,
    v2: CapabilityLeaseV2Current,
    v2_count: int,
    intent: RevokeExpiryIntent,
) -> None:
    value = snapshot(
        lifecycle=lifecycle,
        retained=retained,
        v1=v1,
        v1_count=v1_count,
        v2=v2,
        v2_count=v2_count,
        intent=intent,
    ).to_dict()
    assert ReferenceDomainSnapshot.from_dict(value).to_dict() == value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("v1_state", "ISSUED"),
        ("v1_live_handle_count", 1),
        ("v2_live_handle_count", 1),
        ("retained_object", "ALLOCATED"),
        ("revoke_or_expiry_intent", "EXPLICIT_REVOKE"),
        ("guard_current", False),
    ],
)
def test_exact_v2_mint_predecessor_rejects_every_missing_conjunct(field: str, value: object) -> None:
    base = snapshot(trusted_time=digest("trusted-time")).to_dict()
    base[field] = value
    with pytest.raises(ValueError):
        candidate = ReferenceDomainSnapshot.from_dict(base)
        validate_v2_mint_predecessor(candidate)


def test_v2_issue_transition_uses_fresh_joint_fence_and_no_v1() -> None:
    before = snapshot(trusted_time=digest("trusted-time"))
    validate_v2_mint_predecessor(before)
    after = next_snapshot(
        before,
        v2=CapabilityLeaseV2Current.ISSUED,
        v2_count=2,
    )
    validate_reference_transition(before, after, ReferenceTransition.V2_ISSUE)
    stale = after.to_dict()
    stale["predecessor_fence_sha256"] = digest("wrong-fence")
    with pytest.raises(ValueError):
        ReferenceDomainSnapshot.from_dict(stale)


def test_v2_active_transition_table_preserves_one_lease_and_operation_lineage() -> None:
    before = snapshot(trusted_time=digest("trusted-time"))
    issued = next_snapshot(before, v2=CapabilityLeaseV2Current.ISSUED, v2_count=2)
    validate_reference_transition(before, issued, ReferenceTransition.V2_ISSUE)
    steps = (
        (ReferenceTransition.V2_PARENT_DELEGATION_BEGIN, CapabilityLeaseV2Current.IN_FLIGHT_PARENT_DELEGATION, 2),
        (ReferenceTransition.V2_CHILD_TRANSFER_BEGIN, CapabilityLeaseV2Current.CHILD_TRANSFER_IN_FLIGHT, 3),
        (ReferenceTransition.V2_CHILD_PAIR_READY, CapabilityLeaseV2Current.CHILD_PAIR_READY, 2),
        (ReferenceTransition.V2_BODY_READ_BEGIN, CapabilityLeaseV2Current.BODY_READ_STARTED, 2),
        (ReferenceTransition.V2_CONSUME, CapabilityLeaseV2Current.CONSUMED, 0),
    )
    current = issued
    lease_identity = issued.to_dict()["v2_lease_identity_sha256"]
    for event, state, count in steps:
        following = next_snapshot(current, v2=state, v2_count=count)
        validate_reference_transition(current, following, event)
        assert following.to_dict()["v2_lease_identity_sha256"] == lease_identity
        current = following


def test_v2_active_edge_rejects_cross_semantic_lineage_and_child_ready_direct_revoke() -> None:
    issued = snapshot(v2=CapabilityLeaseV2Current.ISSUED, v2_count=2)
    cross_semantic = next_snapshot(
        issued,
        v2=CapabilityLeaseV2Current.IN_FLIGHT_PARENT_DELEGATION,
        v2_count=2,
        semantic_operation_key="narration.operation.cross-lineage",
    )
    with pytest.raises(ValueError, match="operation lineage mismatch"):
        validate_reference_transition(
            issued, cross_semantic, ReferenceTransition.V2_PARENT_DELEGATION_BEGIN
        )
    child_ready = snapshot(v2=CapabilityLeaseV2Current.CHILD_PAIR_READY, v2_count=2)
    revoked = next_snapshot(
        child_ready,
        lifecycle=ReferenceLifecycle.REVOKED,
        v2=CapabilityLeaseV2Current.BURNED,
        v2_count=0,
        intent=RevokeExpiryIntent.EXPLICIT_REVOKE,
    )
    with pytest.raises(ValueError):
        validate_reference_transition(child_ready, revoked, ReferenceTransition.REVOKE_DIRECT)


def test_v1_terminal_retirement_preserves_published_object_and_immutable_history() -> None:
    history = digest("v1-retired-history")
    terminal = snapshot(
        v1=CapabilityLeaseV1Current.CONSUMED,
        v1_history=history,
    )
    retired = next_snapshot(terminal, v1=CapabilityLeaseV1Current.NONE)
    validate_reference_transition(
        terminal,
        retired,
        ReferenceTransition.V1_TERMINAL_RETIRE,
    )
    assert retired.to_dict()["v1_terminal_history_sha256"] == history

    dropped = next_snapshot(
        terminal,
        lifecycle=ReferenceLifecycle.UNBOUND,
        retained=RetainedObject.NONE,
        v1=CapabilityLeaseV1Current.NONE,
        v1_history=None,
    )
    with pytest.raises(ValueError, match="retained_object|terminal_history"):
        validate_reference_transition(
            terminal,
            dropped,
            ReferenceTransition.V1_TERMINAL_RETIRE,
        )


def test_post_retirement_v2_issue_requires_fresh_operation_and_preserves_histories() -> None:
    history = digest("v2-retired-history")
    terminal = snapshot(
        v2=CapabilityLeaseV2Current.CONSUMED,
        v2_history=history,
        trusted_time=digest("trusted-time"),
    )
    retired = next_snapshot(
        terminal,
        v2=CapabilityLeaseV2Current.V2_ABSENT,
        operation="operation.retire.1",
        semantic_operation_key="narration.operation.retire.1",
        last_retired_operation=terminal.to_dict()["current_operation_id"],
        last_retired_semantic_operation_key=terminal.to_dict()["semantic_operation_key"],
    )
    validate_reference_transition(
        terminal,
        retired,
        ReferenceTransition.V2_TERMINAL_RETIRE,
    )

    replayed_semantic = next_snapshot(
        retired,
        v2=CapabilityLeaseV2Current.ISSUED,
        v2_count=2,
        operation="operation.reference.2",
    )
    with pytest.raises(ValueError, match="distinct from both retired and retirement"):
        validate_reference_transition(
            retired,
            replayed_semantic,
            ReferenceTransition.V2_ISSUE,
        )

    reissued = next_snapshot(
        retired,
        v2=CapabilityLeaseV2Current.ISSUED,
        v2_count=2,
        operation="operation.reference.2",
        semantic_operation_key="narration.operation.2",
    )
    validate_reference_transition(retired, reissued, ReferenceTransition.V2_ISSUE)
    assert reissued.to_dict()["v2_terminal_history_sha256"] == history

    for replayed_operation in (
        terminal.to_dict()["current_operation_id"],
        retired.to_dict()["current_operation_id"],
    ):
        replayed_identity = next_snapshot(
            retired,
            v2=CapabilityLeaseV2Current.ISSUED,
            v2_count=2,
            operation=replayed_operation,
            semantic_operation_key="narration.operation.fresh",
        )
        with pytest.raises(ValueError, match="distinct from both retired and retirement"):
            validate_reference_transition(
                retired,
                replayed_identity,
                ReferenceTransition.V2_ISSUE,
            )
    for replayed_semantic in (
        terminal.to_dict()["semantic_operation_key"],
        retired.to_dict()["semantic_operation_key"],
    ):
        replayed_identity = next_snapshot(
            retired,
            v2=CapabilityLeaseV2Current.ISSUED,
            v2_count=2,
            operation="operation.reference.fresh",
            semantic_operation_key=replayed_semantic,
        )
        with pytest.raises(ValueError, match="distinct from both retired and retirement"):
            validate_reference_transition(
                retired,
                replayed_identity,
                ReferenceTransition.V2_ISSUE,
            )

    changed_history = next_snapshot(
        reissued,
        v2=CapabilityLeaseV2Current.IN_FLIGHT_PARENT_DELEGATION,
        v2_count=2,
        v2_history=digest("forged-history"),
    )
    with pytest.raises(ValueError, match="v2_terminal_history_sha256 mismatch"):
        validate_reference_transition(
            reissued,
            changed_history,
            ReferenceTransition.V2_PARENT_DELEGATION_BEGIN,
        )


def test_failed_retained_purge_requires_human_and_ownership_recovery_lineage() -> None:
    retained = snapshot(
        lifecycle=ReferenceLifecycle.PREPARE_FAILED_RETAINED,
        retained=RetainedObject.RECOVERABLE_RETAINED,
        intent=RevokeExpiryIntent.ABSENT,
    )
    pending = next_snapshot(retained, lifecycle=ReferenceLifecycle.PURGE_PENDING)
    validate_reference_transition(retained, pending, ReferenceTransition.PURGE_BEGIN)
    value = pending.to_dict()
    assert value["revoke_or_expiry_intent"] == "ABSENT"
    assert value["purge_human_action_receipt_sha256"] is not None
    assert value["ownership_recovery_readback_sha256"] is not None

    purged = next_snapshot(
        pending,
        lifecycle=ReferenceLifecycle.PURGED,
        retained=RetainedObject.PURGED,
        retained_generation=pending.to_dict()["retained_object_generation"] + 1,
        retained_revision=digest("purged-retained-revision"),
    )
    validate_reference_transition(pending, purged, ReferenceTransition.PURGE_SUCCESS)

    wrong_recovery = next_snapshot(
        pending,
        lifecycle=ReferenceLifecycle.PURGED,
        retained=RetainedObject.PURGED,
        retained_generation=pending.to_dict()["retained_object_generation"] + 1,
        retained_revision=digest("purged-retained-revision"),
        ownership_recovery=digest("wrong-ownership-recovery"),
    )
    with pytest.raises(ValueError, match="purge success edge is invalid"):
        validate_reference_transition(
            pending,
            wrong_recovery,
            ReferenceTransition.PURGE_SUCCESS,
        )


@pytest.mark.parametrize("terminal", list(TerminalKind))
def test_r13_terminal_three_retirement_is_separate_and_preserves_history(terminal: TerminalKind) -> None:
    before = snapshot(
        v2=CapabilityLeaseV2Current(terminal.value),
        v2_history=digest(f"history-{terminal.value}"),
    )
    validate_v2_terminal_retire_predecessor(before)
    after = next_snapshot(
        before,
        v2=CapabilityLeaseV2Current.V2_ABSENT,
        v2_history=before.to_dict()["v2_terminal_history_sha256"],
        operation=f"operation.retire.{terminal.value.lower()}",
        semantic_operation_key=f"narration.operation.retire.{terminal.value.lower()}",
        last_retired_operation=before.to_dict()["current_operation_id"],
        last_retired_semantic_operation_key=before.to_dict()["semantic_operation_key"],
    )
    validate_reference_transition(before, after, ReferenceTransition.V2_TERMINAL_RETIRE)
    assert after.to_dict()["v2_state"] == "V2_ABSENT"


@pytest.mark.parametrize("terminal", list(TerminalKind))
def test_terminal_retire_transaction_cross_binds_request_fences_history_and_broker(
    terminal: TerminalKind,
) -> None:
    request, before, after, readback = terminal_retire_transaction(terminal)
    validate_terminal_retire_transaction(request, before, after, readback)
    request_data = request.to_dict()
    after_data = after.to_dict()
    assert after_data["current_operation_id"] == request_data["operation_id"]
    assert after_data["last_retired_operation_id"] == request_data["retired_operation_id"]


def test_terminal_retire_request_rejects_same_retired_or_semantic_identity() -> None:
    _, before, _, readback = terminal_retire_transaction(TerminalKind.CONSUMED)
    before_data = before.to_dict()
    with pytest.raises(ValueError, match="must be distinct"):
        transaction_retire_request(
            before,
            TerminalKind.CONSUMED,
            operation_id=before_data["current_operation_id"],
        )
    with pytest.raises(ValueError, match="must be distinct"):
        transaction_retire_request(
            before,
            TerminalKind.CONSUMED,
            semantic_operation_key=before_data["semantic_operation_key"],
        )
    relabeled = readback.to_dict()
    relabeled["retired_operation_id"] = relabeled["operation_id"]
    with pytest.raises(ValueError, match="must be distinct"):
        ReferenceTerminalRetireReadback.from_dict(relabeled)


def test_terminal_retire_transaction_rejects_request_or_result_cross_binding() -> None:
    request, before, after, readback = terminal_retire_transaction(TerminalKind.CONSUMED)
    foreign_request = transaction_retire_request(
        before,
        TerminalKind.CONSUMED,
        operation_id="operation.retire.foreign",
        semantic_operation_key="narration.operation.retire.foreign",
    )
    with pytest.raises(ValueError, match="request/readback lineage"):
        validate_terminal_retire_transaction(foreign_request, before, after, readback)

    wrong_result = next_snapshot(
        before,
        v2=CapabilityLeaseV2Current.V2_ABSENT,
        operation=request.to_dict()["operation_id"],
        semantic_operation_key=request.to_dict()["semantic_operation_key"],
        last_retired_operation=request.to_dict()["retired_operation_id"],
        last_retired_semantic_operation_key=request.to_dict()["retired_semantic_operation_key"],
        committed_event=digest("foreign-retire-commit"),
    )
    with pytest.raises(ValueError, match="readback/result snapshot tuple"):
        validate_terminal_retire_transaction(request, before, wrong_result, readback)


def test_r13_v1_revoke_pending_terminal_is_finalize_only() -> None:
    before = snapshot(
        lifecycle=ReferenceLifecycle.REVOKE_PENDING,
        v1=CapabilityLeaseV1Current.FAILED_CLOSED,
        intent=RevokeExpiryIntent.EXPLICIT_REVOKE,
        v1_history=digest("v1-terminal-history"),
    )
    validate_v1_finalize_predecessor(before)
    after = next_snapshot(
        before,
        lifecycle=ReferenceLifecycle.REVOKED,
        v1=CapabilityLeaseV1Current.NONE,
    )
    validate_reference_transition(before, after, ReferenceTransition.V1_REVOKE_FINALIZE)


def test_v2_issue_readback_distinguishes_commit_stale_and_unknown_without_replay() -> None:
    acknowledged = ReferenceV2IssueOrRevokeReadback.create(
        operation_id="operation.issue.1",
        semantic_operation_key="narration.operation.1",
        request_sha256=digest("issue-request"),
        outcome=V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED,
        expected_fence_revision=1,
        expected_fence_sha256=digest("fence-before"),
        predecessor_snapshot_sha256=digest("snapshot-before"),
        expected_v1_terminal_history_sha256=None,
        expected_v2_terminal_history_sha256=None,
        result_fence_revision=2,
        result_fence_sha256=digest("fence-after"),
        result_snapshot_sha256=digest("snapshot-after"),
        committed_event_sha256=digest("issue-event"),
        trusted_time_receipt_sha256=digest("trusted-time"),
        broker_domain_sha256=digest("broker-domain"),
        broker_process_identity_sha256=digest("broker-process"),
        broker_session_sha256=digest("broker-session"),
        product_build_sha256=digest("product-build"),
        broker_protocol_version="owner.voice.broker.v2",
        result_lifecycle=ReferenceLifecycle.PREPARED,
        result_retained_object=RetainedObject.PUBLISHED,
        result_v1_state=CapabilityLeaseV1Current.NONE,
        result_v1_lease_identity_sha256=None,
        result_v1_handle_count=0,
        result_v1_terminal_history_sha256=None,
        result_v2_state=CapabilityLeaseV2Current.ISSUED,
        result_v2_lease_identity_sha256=digest("v2-lease"),
        result_v2_handle_count=2,
        result_v2_terminal_history_sha256=None,
        result_revoke_or_expiry_intent=RevokeExpiryIntent.ABSENT,
        result_revoke_or_expiry_event_sha256=None,
        live_capability_delivery_acknowledged=True,
        request_issuance_effect=EffectTruth.OBSERVED,
        request_live_handle_effect=EffectTruth.OBSERVED,
        readback_at=NOW,
    )
    assert acknowledged.to_dict()["serialized_capability_present"] is False
    stale = ReferenceV2IssueOrRevokeReadback.create(
        operation_id="operation.issue.2",
        semantic_operation_key="narration.operation.2",
        request_sha256=digest("issue-request-2"),
        outcome=V2IssueOrRevokeOutcome.NO_COMMIT_STALE_PREDECESSOR,
        expected_fence_revision=1,
        expected_fence_sha256=digest("fence-old"),
        predecessor_snapshot_sha256=digest("snapshot-old"),
        expected_v1_terminal_history_sha256=None,
        expected_v2_terminal_history_sha256=None,
        result_fence_revision=2,
        result_fence_sha256=digest("fence-current"),
        result_snapshot_sha256=digest("snapshot-current"),
        committed_event_sha256=None,
        trusted_time_receipt_sha256=digest("trusted-time"),
        broker_domain_sha256=digest("broker-domain"),
        broker_process_identity_sha256=digest("broker-process"),
        broker_session_sha256=digest("broker-session"),
        product_build_sha256=digest("product-build"),
        broker_protocol_version="owner.voice.broker.v2",
        result_lifecycle=ReferenceLifecycle.PREPARED,
        result_retained_object=RetainedObject.PUBLISHED,
        result_v1_state=CapabilityLeaseV1Current.NONE,
        result_v1_lease_identity_sha256=None,
        result_v1_handle_count=0,
        result_v1_terminal_history_sha256=None,
        result_v2_state=CapabilityLeaseV2Current.V2_ABSENT,
        result_v2_lease_identity_sha256=None,
        result_v2_handle_count=0,
        result_v2_terminal_history_sha256=None,
        result_revoke_or_expiry_intent=RevokeExpiryIntent.ABSENT,
        result_revoke_or_expiry_event_sha256=None,
        live_capability_delivery_acknowledged=None,
        request_issuance_effect=EffectTruth.ZERO,
        request_live_handle_effect=EffectTruth.ZERO,
        readback_at=NOW,
    )
    assert stale.to_dict()["automatic_retry_started"] is False

    unknown = ReferenceV2IssueOrRevokeReadback.create(
        operation_id="operation.issue.3",
        semantic_operation_key="narration.operation.3",
        request_sha256=digest("issue-request-3"),
        outcome=V2IssueOrRevokeOutcome.OUTCOME_NOT_CONFIRMED,
        expected_fence_revision=3,
        expected_fence_sha256=digest("fence-unknown"),
        predecessor_snapshot_sha256=digest("snapshot-unknown"),
        expected_v1_terminal_history_sha256=None,
        expected_v2_terminal_history_sha256=None,
        result_fence_revision=None,
        result_fence_sha256=None,
        result_snapshot_sha256=None,
        committed_event_sha256=None,
        trusted_time_receipt_sha256=digest("trusted-time"),
        broker_domain_sha256=digest("broker-domain"),
        broker_process_identity_sha256=digest("broker-process"),
        broker_session_sha256=digest("broker-session"),
        product_build_sha256=digest("product-build"),
        broker_protocol_version="owner.voice.broker.v2",
        result_lifecycle=None,
        result_retained_object=None,
        result_v1_state=None,
        result_v1_lease_identity_sha256=None,
        result_v1_handle_count=None,
        result_v1_terminal_history_sha256=None,
        result_v2_state=None,
        result_v2_lease_identity_sha256=None,
        result_v2_handle_count=None,
        result_v2_terminal_history_sha256=None,
        result_revoke_or_expiry_intent=None,
        result_revoke_or_expiry_event_sha256=None,
        live_capability_delivery_acknowledged=None,
        request_issuance_effect=EffectTruth.NOT_CONFIRMED,
        request_live_handle_effect=EffectTruth.NOT_CONFIRMED,
        readback_at=NOW,
    )
    assert unknown.to_dict()["request_issuance_effect"] == "NOT_CONFIRMED"


@pytest.mark.parametrize(
    "outcome",
    [
        V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED,
        V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_NOT_CONFIRMED,
        V2IssueOrRevokeOutcome.REVOKE_COMMITTED,
        V2IssueOrRevokeOutcome.EXPIRY_COMMITTED,
    ],
)
def test_r12_v2_committed_outcome_matrix_keeps_exact_effect_truth(
    outcome: V2IssueOrRevokeOutcome,
) -> None:
    value = v2_committed_readback(outcome).to_dict()
    assert value["automatic_retry_started"] is False
    assert value["serialized_capability_present"] is False
    if outcome is V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_NOT_CONFIRMED:
        assert value["result_v2_state"] == "BURNED"
        assert value["live_capability_delivery_acknowledged"] is False
    if outcome in {
        V2IssueOrRevokeOutcome.REVOKE_COMMITTED,
        V2IssueOrRevokeOutcome.EXPIRY_COMMITTED,
    }:
        assert value["request_issuance_effect"] == "ZERO"
        assert value["result_v2_state"] == "V2_ABSENT"
    assert ReferenceV2IssueOrRevokeReadback.from_dict(value).to_dict() == value


def test_r13_repeated_issue_and_revoke_readbacks_preserve_prior_terminal_histories() -> None:
    v1_history = digest("prior-v1-history")
    v2_history = digest("prior-v2-history")
    acknowledged = v2_committed_readback(
        V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED,
        expected_v1_history=v1_history,
        expected_v2_history=v2_history,
    ).to_dict()
    assert acknowledged["result_v1_terminal_history_sha256"] == v1_history
    assert acknowledged["result_v2_terminal_history_sha256"] == v2_history

    revoked = v2_committed_readback(
        V2IssueOrRevokeOutcome.REVOKE_COMMITTED,
        expected_v1_history=v1_history,
        expected_v2_history=v2_history,
    ).to_dict()
    assert revoked["result_v1_terminal_history_sha256"] == v1_history
    assert revoked["result_v2_terminal_history_sha256"] == v2_history

    acknowledged["result_v2_terminal_history_sha256"] = digest("cross-history")
    with pytest.raises(ValueError, match="acknowledged V2 issue readback tuple"):
        ReferenceV2IssueOrRevokeReadback.from_dict(acknowledged)


@pytest.mark.parametrize(
    ("outcome", "terminal"),
    [
        (V1RevokeFinalizeOutcome.V1_CONSUMED_REVOKE_FINALIZED, TerminalKind.CONSUMED),
        (V1RevokeFinalizeOutcome.V1_TERMINAL_AWAITING_FINALIZE, TerminalKind.CONSUMED),
        (V1RevokeFinalizeOutcome.V1_ACTIVE_RECOVERY_REQUIRED, None),
    ],
)
def test_v1_finalize_binds_exact_request_and_result_revoke_event(
    outcome: V1RevokeFinalizeOutcome,
    terminal: TerminalKind | None,
) -> None:
    value = v1_finalize_readback(outcome=outcome, terminal=terminal).to_dict()
    value["result_revoke_or_expiry_event_sha256"] = digest("other-revoke-event")
    with pytest.raises(ValueError, match="tuple"):
        ReferenceV1RevokeFinalizeReadback.from_dict(value)


def test_exact_current_history_requires_event_identity_and_integer_duplicate_count() -> None:
    terminal = terminal_retire_readback(
        terminal=TerminalKind.CONSUMED,
        outcome=TerminalRetireOutcome.NO_COMMIT_TERMINAL_STILL_CURRENT,
    ).to_dict()
    terminal["terminal_history_event_sha256"] = None
    with pytest.raises(ValueError, match="unchanged predecessor"):
        ReferenceTerminalRetireReadback.from_dict(terminal)

    awaiting = v1_finalize_readback(
        outcome=V1RevokeFinalizeOutcome.V1_TERMINAL_AWAITING_FINALIZE,
        terminal=TerminalKind.CONSUMED,
    ).to_dict()
    awaiting["terminal_history_event_sha256"] = None
    with pytest.raises(ValueError, match="unchanged/current"):
        ReferenceV1RevokeFinalizeReadback.from_dict(awaiting)

    terminal = terminal_retire_readback(
        terminal=TerminalKind.CONSUMED,
        outcome=TerminalRetireOutcome.CONSUMED_RETIRED,
    ).to_dict()
    terminal["history_duplicate_count"] = False
    with pytest.raises(ValueError, match="duplicate history"):
        ReferenceTerminalRetireReadback.from_dict(terminal)

    finalized = v1_finalize_readback(
        outcome=V1RevokeFinalizeOutcome.V1_CONSUMED_REVOKE_FINALIZED,
        terminal=TerminalKind.CONSUMED,
    ).to_dict()
    finalized["history_duplicate_count"] = False
    with pytest.raises(ValueError, match="integer zero"):
        ReferenceV1RevokeFinalizeReadback.from_dict(finalized)


def test_all_task074_b_readbacks_are_explicit_noncanonical_fixtures() -> None:
    records_and_types = [
        (
            v2_committed_readback(
                V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED
            ).to_dict(),
            ReferenceV2IssueOrRevokeReadback,
        ),
        (
            terminal_retire_readback(
                terminal=TerminalKind.CONSUMED,
                outcome=TerminalRetireOutcome.CONSUMED_RETIRED,
            ).to_dict(),
            ReferenceTerminalRetireReadback,
        ),
        (
            v1_finalize_readback(
                outcome=V1RevokeFinalizeOutcome.V1_CONSUMED_REVOKE_FINALIZED,
                terminal=TerminalKind.CONSUMED,
            ).to_dict(),
            ReferenceV1RevokeFinalizeReadback,
        ),
        (
            ReferenceChildAbortRecoveryReadback.create(
                operation_id="operation.child.fixture-boundary",
                attachment_sha256=digest("attachment"),
                begin_lineage_sha256=digest("begin"),
                spawn_truth=SpawnTruth.PROVEN_FALSE,
                lifecycle_events=(),
                child_process_identity_sha256=None,
                body_gate_opened=False,
                audio_role_read_count=0,
                transcript_role_read_count=0,
                model_invocation_start_count=0,
                child_exited=False,
                no_surviving_child=True,
                audio_remote_role_state=RemoteRoleState.ABSENT_PROVEN,
                transcript_remote_role_state=RemoteRoleState.ABSENT_PROVEN,
                body_effect=EffectTruth.ZERO,
                model_effect=EffectTruth.ZERO,
                readback_at=NOW,
            ).to_dict(),
            ReferenceChildAbortRecoveryReadback,
        ),
    ]
    for value, record_type in records_and_types:
        assert value["producer_binding_state"] == "NOT_BOUND"
        assert value["fixture_only"] is True
        assert value["canonical_producer_acceptance_state"] == "NOT_CONFIRMED"
        assert value["canonical_producer_readback"] is False
        assert value["execution_ready"] is False
        value["canonical_producer_acceptance_state"] = "CURRENT"
        with pytest.raises(ValueError, match="canonical TASK074-C/D producer"):
            record_type.from_dict(value)


def test_terminal_retire_readback_rejects_kind_relabel_or_duplicate_history() -> None:
    request = ReferenceTerminalRetireRequest.create(
        operation_id="operation.retire.1",
        semantic_operation_key="narration.operation.retire.1",
        retired_operation_id="operation.source.1",
        retired_semantic_operation_key="narration.operation.source.1",
        requested_action=TerminalRetireAction.RETIRE,
        terminal_kind=TerminalKind.FAILED_CLOSED,
        retired_lease_identity_sha256=digest("lease"),
        terminal_readback_sha256=digest("terminal-readback"),
        consumer_two_role_close_readback_sha256=None,
        burn_abort_close_readback_sha256=None,
        failed_closed_gate_proof_sha256=digest("failed-closed-gates"),
        expected_fence_revision=5,
        expected_fence_sha256=digest("fence-before"),
        predecessor_snapshot_sha256=digest("before"),
        expected_terminal_history_event_sha256=digest("history-event"),
        expected_terminal_history_sha256=digest("history"),
        trusted_time_receipt_sha256=digest("trusted-time"),
        broker_domain_sha256=digest("broker"),
        broker_process_identity_sha256=digest("broker-process"),
        broker_session_sha256=digest("broker-session"),
        product_build_sha256=digest("product-build"),
        broker_protocol_version="owner.voice.broker.v2",
    )
    receipt = ReferenceTerminalRetireReadback.create(
        request=request,
        result_fence_revision=6,
        result_fence_sha256=digest("fence-after"),
        result_snapshot_sha256=digest("after"),
        committed_event_sha256=digest("retire-event"),
        terminal_history_event_sha256=digest("history-event"),
        terminal_history_sha256=digest("history"),
        terminal_history_disposition=TerminalHistoryDisposition.EXACT_PRESENT,
        history_append_count=0,
        outcome=TerminalRetireOutcome.FAILED_CLOSED_RETIRED_NOT_CONFIRMED,
        result_lifecycle=ReferenceLifecycle.PREPARED,
        result_retained_object=RetainedObject.PUBLISHED,
        result_v1_state=CapabilityLeaseV1Current.NONE,
        result_v1_lease_identity_sha256=None,
        result_v1_handle_count=0,
        result_v1_terminal_history_sha256=None,
        result_v2_state=CapabilityLeaseV2Current.V2_ABSENT,
        result_v2_lease_identity_sha256=None,
        result_v2_handle_count=0,
        result_v2_terminal_history_sha256=digest("history"),
        result_revoke_or_expiry_intent=RevokeExpiryIntent.ABSENT,
        result_revoke_or_expiry_event_sha256=None,
        body_effect=EffectTruth.NOT_CONFIRMED,
        model_effect=EffectTruth.NOT_CONFIRMED,
        readback_at=NOW,
    )
    assert receipt.to_dict()["new_lease_issued"] is False
    tampered = receipt.to_dict()
    tampered["outcome"] = TerminalRetireOutcome.CONSUMED_RETIRED.value
    with pytest.raises(ValueError, match="mismatch"):
        ReferenceTerminalRetireReadback.from_dict(tampered)


@pytest.mark.parametrize(
    ("terminal", "outcome", "action"),
    [
        (TerminalKind.CONSUMED, TerminalRetireOutcome.CONSUMED_RETIRED, TerminalRetireAction.RETIRE),
        (TerminalKind.BURNED, TerminalRetireOutcome.BURNED_RETIRED, TerminalRetireAction.RETIRE),
        (TerminalKind.FAILED_CLOSED, TerminalRetireOutcome.FAILED_CLOSED_RETIRED_NOT_CONFIRMED, TerminalRetireAction.RETIRE),
        (TerminalKind.CONSUMED, TerminalRetireOutcome.TERMINAL_REVOKE_COMMITTED, TerminalRetireAction.EXPLICIT_REVOKE),
        (TerminalKind.BURNED, TerminalRetireOutcome.TERMINAL_EXPIRY_COMMITTED, TerminalRetireAction.TRUSTED_TIME_EXPIRY),
        (TerminalKind.CONSUMED, TerminalRetireOutcome.NO_COMMIT_TERMINAL_STILL_CURRENT, TerminalRetireAction.RETIRE),
        (TerminalKind.BURNED, TerminalRetireOutcome.STALE_OTHER_COMMIT, TerminalRetireAction.RETIRE),
        (TerminalKind.FAILED_CLOSED, TerminalRetireOutcome.OUTCOME_NOT_CONFIRMED, TerminalRetireAction.RETIRE),
    ],
)
def test_r13_terminal_retire_outcome_matrix_is_exact_and_nonreplayable(
    terminal: TerminalKind,
    outcome: TerminalRetireOutcome,
    action: TerminalRetireAction,
) -> None:
    value = terminal_retire_readback(
        terminal=terminal,
        outcome=outcome,
        action=action,
    ).to_dict()
    assert value["automatic_retry_started"] is False
    assert value["new_lease_issued"] is False
    assert ReferenceTerminalRetireReadback.from_dict(value).to_dict() == value


def test_terminal_retire_rejects_cross_history_lineage() -> None:
    value = terminal_retire_readback(
        terminal=TerminalKind.CONSUMED,
        outcome=TerminalRetireOutcome.CONSUMED_RETIRED,
    ).to_dict()
    value["result_v2_terminal_history_sha256"] = digest("other-terminal-history")
    with pytest.raises(ValueError, match="history lineage mismatch"):
        ReferenceTerminalRetireReadback.from_dict(value)


def test_r13_v1_terminal_finalize_and_reply_loss_are_typed_and_nonreplayable() -> None:
    finalized = ReferenceV1RevokeFinalizeReadback.create(
        operation_id="operation.v1.finalize.1",
        semantic_operation_key="narration.operation.v1.1",
        request_sha256=digest("v1-finalize-request"),
        terminal_kind=TerminalKind.CONSUMED,
        v1_lease_identity_sha256=digest("v1-lease"),
        terminal_readback_sha256=digest("v1-terminal"),
        terminal_close_readback_sha256=digest("v1-close"),
        failed_closed_gate_proof_sha256=None,
        revoke_or_expiry_intent=RevokeExpiryIntent.EXPLICIT_REVOKE,
        revoke_or_expiry_event_sha256=digest("revoke-event"),
        expected_fence_revision=7,
        expected_fence_sha256=digest("fence-before"),
        predecessor_snapshot_sha256=digest("snapshot-before"),
        result_fence_revision=8,
        result_fence_sha256=digest("fence-after"),
        result_snapshot_sha256=digest("snapshot-after"),
        committed_event_sha256=digest("finalize-event"),
        terminal_history_event_sha256=digest("history-event"),
        terminal_history_sha256=digest("v1-history"),
        terminal_history_disposition=TerminalHistoryDisposition.EXACT_PRESENT,
        history_append_count=0,
        outcome=V1RevokeFinalizeOutcome.V1_CONSUMED_REVOKE_FINALIZED,
        trusted_time_receipt_sha256=digest("trusted-time"),
        broker_domain_sha256=digest("broker-domain"),
        broker_process_identity_sha256=digest("broker-process"),
        broker_session_sha256=digest("broker-session"),
        product_build_sha256=digest("product-build"),
        broker_protocol_version="owner.voice.broker.v2",
        result_lifecycle=ReferenceLifecycle.REVOKED,
        result_retained_object=RetainedObject.PUBLISHED,
        result_v1_state=CapabilityLeaseV1Current.NONE,
        result_v1_lease_identity_sha256=None,
        result_v1_handle_count=0,
        result_v1_terminal_history_sha256=digest("v1-history"),
        result_v2_state=CapabilityLeaseV2Current.V2_ABSENT,
        result_v2_lease_identity_sha256=None,
        result_v2_handle_count=0,
        result_v2_terminal_history_sha256=None,
        result_revoke_or_expiry_intent=RevokeExpiryIntent.EXPLICIT_REVOKE,
        result_revoke_or_expiry_event_sha256=digest("revoke-event"),
        body_effect=EffectTruth.OBSERVED,
        model_effect=EffectTruth.OBSERVED,
        readback_at=NOW,
    )
    value = finalized.to_dict()
    assert value["new_v1_or_v2_lease_issued"] is False
    assert value["automatic_retry_started"] is False
    assert ReferenceV1RevokeFinalizeReadback.from_dict(value).to_dict() == value
    tampered = deepcopy(value)
    tampered["result_v1_lease_identity_sha256"] = digest("replayed-v1")
    with pytest.raises(ValueError):
        ReferenceV1RevokeFinalizeReadback.from_dict(tampered)


def test_v1_failed_closed_awaiting_finalize_requires_terminal_readback() -> None:
    with pytest.raises(ValueError, match="terminal proof is incomplete"):
        ReferenceV1RevokeFinalizeReadback.create(
            operation_id="operation.v1.awaiting.1",
            semantic_operation_key="narration.operation.v1.awaiting",
            request_sha256=digest("v1-awaiting-request"),
            terminal_kind=TerminalKind.FAILED_CLOSED,
            v1_lease_identity_sha256=digest("v1-awaiting-lease"),
            terminal_readback_sha256=None,
            terminal_close_readback_sha256=None,
            failed_closed_gate_proof_sha256=digest("v1-failed-closed-gates"),
            revoke_or_expiry_intent=RevokeExpiryIntent.EXPLICIT_REVOKE,
            revoke_or_expiry_event_sha256=digest("v1-awaiting-revoke-event"),
            expected_fence_revision=7,
            expected_fence_sha256=digest("v1-awaiting-fence"),
            predecessor_snapshot_sha256=digest("v1-awaiting-snapshot"),
            result_fence_revision=7,
            result_fence_sha256=digest("v1-awaiting-fence"),
            result_snapshot_sha256=digest("v1-awaiting-snapshot"),
            committed_event_sha256=None,
            terminal_history_event_sha256=digest("v1-awaiting-history-event"),
            terminal_history_sha256=digest("v1-awaiting-history"),
            terminal_history_disposition=TerminalHistoryDisposition.EXACT_PRESENT,
            history_append_count=0,
            outcome=V1RevokeFinalizeOutcome.V1_TERMINAL_AWAITING_FINALIZE,
            trusted_time_receipt_sha256=digest("trusted-time"),
            broker_domain_sha256=digest("broker-domain"),
            broker_process_identity_sha256=digest("broker-process"),
            broker_session_sha256=digest("broker-session"),
            product_build_sha256=digest("product-build"),
            broker_protocol_version="owner.voice.broker.v2",
            result_lifecycle=ReferenceLifecycle.REVOKE_PENDING,
            result_retained_object=RetainedObject.PUBLISHED,
            result_v1_state=CapabilityLeaseV1Current.FAILED_CLOSED,
            result_v1_lease_identity_sha256=digest("v1-awaiting-lease"),
            result_v1_handle_count=0,
            result_v1_terminal_history_sha256=digest("v1-awaiting-history"),
            result_v2_state=CapabilityLeaseV2Current.V2_ABSENT,
            result_v2_lease_identity_sha256=None,
            result_v2_handle_count=0,
            result_v2_terminal_history_sha256=None,
            result_revoke_or_expiry_intent=RevokeExpiryIntent.EXPLICIT_REVOKE,
            result_revoke_or_expiry_event_sha256=digest("v1-awaiting-revoke-event"),
            body_effect=EffectTruth.NOT_CONFIRMED,
            model_effect=EffectTruth.NOT_CONFIRMED,
            readback_at=NOW,
        )


@pytest.mark.parametrize(
    ("outcome", "terminal"),
    [
        (V1RevokeFinalizeOutcome.V1_CONSUMED_REVOKE_FINALIZED, TerminalKind.CONSUMED),
        (V1RevokeFinalizeOutcome.V1_BURNED_REVOKE_FINALIZED, TerminalKind.BURNED),
        (V1RevokeFinalizeOutcome.V1_FAILED_CLOSED_REVOKE_FINALIZED_NOT_CONFIRMED, TerminalKind.FAILED_CLOSED),
        (V1RevokeFinalizeOutcome.V1_TERMINAL_AWAITING_FINALIZE, TerminalKind.BURNED),
        (V1RevokeFinalizeOutcome.V1_ACTIVE_RECOVERY_REQUIRED, None),
        (V1RevokeFinalizeOutcome.STALE_OTHER_COMMIT, None),
        (V1RevokeFinalizeOutcome.OUTCOME_NOT_CONFIRMED, None),
    ],
)
def test_r13_v1_finalize_outcome_matrix_is_typed_and_nonreplayable(
    outcome: V1RevokeFinalizeOutcome,
    terminal: TerminalKind | None,
) -> None:
    value = v1_finalize_readback(outcome=outcome, terminal=terminal).to_dict()
    assert value["new_v1_or_v2_lease_issued"] is False
    assert value["automatic_retry_started"] is False
    assert value["body_or_model_entry_started"] is False
    assert ReferenceV1RevokeFinalizeReadback.from_dict(value).to_dict() == value


def test_v1_finalized_rejects_cross_history_lineage() -> None:
    value = v1_finalize_readback(
        outcome=V1RevokeFinalizeOutcome.V1_CONSUMED_REVOKE_FINALIZED,
        terminal=TerminalKind.CONSUMED,
    ).to_dict()
    value["result_v1_terminal_history_sha256"] = digest("wrong-v1-history")
    with pytest.raises(ValueError, match="history lineage mismatch"):
        ReferenceV1RevokeFinalizeReadback.from_dict(value)


def test_f34_child_not_created_and_created_abort_have_distinct_truth() -> None:
    not_created = ReferenceChildAbortRecoveryReadback.create(
        operation_id="operation.child.1",
        attachment_sha256=digest("attachment"),
        begin_lineage_sha256=digest("begin"),
        spawn_truth=SpawnTruth.PROVEN_FALSE,
        lifecycle_events=(),
        child_process_identity_sha256=None,
        body_gate_opened=False,
        audio_role_read_count=0,
        transcript_role_read_count=0,
        model_invocation_start_count=0,
        child_exited=False,
        no_surviving_child=True,
        audio_remote_role_state=RemoteRoleState.ABSENT_PROVEN,
        transcript_remote_role_state=RemoteRoleState.ABSENT_PROVEN,
        body_effect=EffectTruth.ZERO,
        model_effect=EffectTruth.ZERO,
        readback_at=NOW,
    )
    assert not_created.to_dict()["spawn_truth"] == "PROVEN_FALSE"
    created = ReferenceChildAbortRecoveryReadback.create(
        operation_id="operation.child.2",
        attachment_sha256=digest("attachment-2"),
        begin_lineage_sha256=digest("begin-2"),
        spawn_truth=SpawnTruth.PROVEN_TRUE,
        lifecycle_events=(
            "SPAWN_COMMITTED", "ABORT_REQUESTED", "EXIT_WAIT_STARTED", "CHILD_EXITED",
            "REMOTE_CLOSE_VERIFIED", "ABORT_COMPLETE",
        ),
        child_process_identity_sha256=digest("pinned-child"),
        body_gate_opened=False,
        audio_role_read_count=0,
        transcript_role_read_count=0,
        model_invocation_start_count=0,
        child_exited=True,
        no_surviving_child=True,
        audio_remote_role_state=RemoteRoleState.CREATED_THEN_CLOSED_VERIFIED,
        transcript_remote_role_state=RemoteRoleState.ABSENT_PROVEN,
        body_effect=EffectTruth.ZERO,
        model_effect=EffectTruth.ZERO,
        readback_at=NOW,
    )
    assert created.to_dict()["unrelated_process_affected"] is False


def test_created_child_observed_effects_require_positive_observation_receipts() -> None:
    common = {
        "operation_id": "operation.child.observed.1",
        "attachment_sha256": digest("attachment-observed"),
        "begin_lineage_sha256": digest("begin-observed"),
        "spawn_truth": SpawnTruth.PROVEN_TRUE,
        "lifecycle_events": (
            "SPAWN_COMMITTED", "ABORT_REQUESTED", "EXIT_WAIT_STARTED", "CHILD_EXITED",
            "REMOTE_CLOSE_VERIFIED", "ABORT_COMPLETE",
        ),
        "child_process_identity_sha256": digest("pinned-observed-child"),
        "body_gate_opened": True,
        "audio_role_read_count": 1,
        "transcript_role_read_count": 1,
        "model_invocation_start_count": 1,
        "child_exited": True,
        "no_surviving_child": True,
        "audio_remote_role_state": RemoteRoleState.CREATED_THEN_CLOSED_VERIFIED,
        "transcript_remote_role_state": RemoteRoleState.CREATED_THEN_CLOSED_VERIFIED,
        "body_effect": EffectTruth.OBSERVED,
        "model_effect": EffectTruth.OBSERVED,
        "readback_at": NOW,
    }
    observed = ReferenceChildAbortRecoveryReadback.create(
        **common,
        body_observation_readback_sha256=digest("body-observation"),
        model_observation_readback_sha256=digest("model-observation"),
    ).to_dict()
    assert observed["body_observation_readback_sha256"] == digest("body-observation")
    with pytest.raises(ValueError, match="observed body effect"):
        ReferenceChildAbortRecoveryReadback.create(
            **common,
            body_observation_readback_sha256=None,
            model_observation_readback_sha256=digest("model-observation"),
        )
    with pytest.raises(ValueError, match="observed model effect"):
        ReferenceChildAbortRecoveryReadback.create(
            **common,
            body_observation_readback_sha256=digest("body-observation"),
            model_observation_readback_sha256=None,
        )


def test_zero_child_effect_cannot_carry_positive_observation_receipt() -> None:
    value = ReferenceChildAbortRecoveryReadback.create(
        operation_id="operation.child.zero.receipt",
        attachment_sha256=digest("attachment-zero-receipt"),
        begin_lineage_sha256=digest("begin-zero-receipt"),
        spawn_truth=SpawnTruth.PROVEN_FALSE,
        lifecycle_events=(),
        child_process_identity_sha256=None,
        body_gate_opened=False,
        audio_role_read_count=0,
        transcript_role_read_count=0,
        model_invocation_start_count=0,
        child_exited=False,
        no_surviving_child=True,
        audio_remote_role_state=RemoteRoleState.ABSENT_PROVEN,
        transcript_remote_role_state=RemoteRoleState.ABSENT_PROVEN,
        body_effect=EffectTruth.ZERO,
        model_effect=EffectTruth.ZERO,
        readback_at=NOW,
    ).to_dict()
    value["body_observation_readback_sha256"] = digest("contradictory-observation")
    with pytest.raises(ValueError, match="non-observed body effect"):
        ReferenceChildAbortRecoveryReadback.from_dict(value)


def test_created_child_cannot_claim_zero_with_missing_remote_close_or_model_readback() -> None:
    with pytest.raises(ValueError, match="zero effect"):
        ReferenceChildAbortRecoveryReadback.create(
            operation_id="operation.child.3",
            attachment_sha256=digest("attachment-3"),
            begin_lineage_sha256=digest("begin-3"),
            spawn_truth=SpawnTruth.PROVEN_TRUE,
            lifecycle_events=("SPAWN_COMMITTED", "ABORT_REQUESTED"),
            child_process_identity_sha256=digest("pinned-child"),
            body_gate_opened=False,
            audio_role_read_count=0,
            transcript_role_read_count=0,
            model_invocation_start_count=None,
            child_exited=None,
            no_surviving_child=None,
            audio_remote_role_state=RemoteRoleState.NOT_CONFIRMED,
            transcript_remote_role_state=RemoteRoleState.NOT_CONFIRMED,
            body_effect=EffectTruth.ZERO,
            model_effect=EffectTruth.ZERO,
            readback_at=NOW,
        )


def test_creation_not_confirmed_never_claims_effect_zero() -> None:
    readback = ReferenceChildAbortRecoveryReadback.create(
        operation_id="operation.child.4",
        attachment_sha256=digest("attachment-4"),
        begin_lineage_sha256=digest("begin-4"),
        spawn_truth=SpawnTruth.NOT_CONFIRMED,
        lifecycle_events=(),
        child_process_identity_sha256=None,
        body_gate_opened=None,
        audio_role_read_count=None,
        transcript_role_read_count=None,
        model_invocation_start_count=None,
        child_exited=None,
        no_surviving_child=None,
        audio_remote_role_state=RemoteRoleState.NOT_CONFIRMED,
        transcript_remote_role_state=RemoteRoleState.NOT_CONFIRMED,
        body_effect=EffectTruth.NOT_CONFIRMED,
        model_effect=EffectTruth.NOT_CONFIRMED,
        readback_at=NOW,
    )
    assert readback.to_dict()["replay_started"] is False


def test_unknown_body_path_handle_or_pid_fields_are_rejected() -> None:
    for field in ("raw_audio_body", "transcript_text", "absolute_path", "native_handle", "pid"):
        payload = media().to_dict()
        payload[field] = "forbidden"
        with pytest.raises(ValueError, match="unknown"):
            OwnerVoiceReferenceMediaFacts.from_dict(payload)


def test_schema_validates_body_free_records_rejects_leak_and_is_mirrored() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    records = [
        owner_voice_reference_media_policy(),
        media().to_dict(),
        transcript().to_dict(),
        transcript_binding().to_dict(),
        OwnerVoiceReferencePreparePlan.create(
            operation_id="operation.prepare.schema",
            project_id="project.alpha",
            project_manifest_revision_sha256=digest("manifest"),
            installed_context_sha256=digest("installed"),
            voice_profile_id="voice.owner",
            voice_profile_revision_sha256=digest("voice-profile"),
            consent_current_evaluation_sha256=digest("consent-current"),
            route_selection_sha256=digest("selection"),
            source_classification=ReferenceSourceClassification.TASK046_PRIVATE_RECORDING_REFERENCE,
            audio_source_identity_sha256=digest("audio-source"),
            transcript_source_identity_sha256=digest("transcript-source"),
            media_facts_sha256=media().to_dict()["media_facts_sha256"],
            transcript_facts_sha256=transcript().to_dict()["transcript_facts_sha256"],
            transcript_binding_receipt_sha256=transcript_binding().to_dict()["transcript_binding_receipt_sha256"],
            retention_policy=RetentionPolicy.OWNER_SELECTED_EXPIRY,
            retention_policy_revision_sha256=digest("retention"),
            expires_at="2026-10-01T09:00:00Z",
            expected_lifecycle_snapshot_sha256=digest("lifecycle-head"),
            human_action_receipt_sha256=digest("human-action"),
            task072_ticket_sha256=digest("ticket"),
            created_at=NOW,
        ).to_dict(),
        snapshot(trusted_time=digest("trusted-time")).to_dict(),
        v2_committed_readback(
            V2IssueOrRevokeOutcome.V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED
        ).to_dict(),
        terminal_retire_request(terminal=TerminalKind.FAILED_CLOSED).to_dict(),
        terminal_retire_readback(
            terminal=TerminalKind.FAILED_CLOSED,
            outcome=TerminalRetireOutcome.FAILED_CLOSED_RETIRED_NOT_CONFIRMED,
        ).to_dict(),
        v1_finalize_readback(
            outcome=V1RevokeFinalizeOutcome.V1_CONSUMED_REVOKE_FINALIZED,
            terminal=TerminalKind.CONSUMED,
        ).to_dict(),
        ReferenceChildAbortRecoveryReadback.create(
            operation_id="operation.child.schema",
            attachment_sha256=digest("attachment"),
            begin_lineage_sha256=digest("begin"),
            spawn_truth=SpawnTruth.PROVEN_FALSE,
            lifecycle_events=(),
            child_process_identity_sha256=None,
            body_gate_opened=False,
            audio_role_read_count=0,
            transcript_role_read_count=0,
            model_invocation_start_count=0,
            child_exited=False,
            no_surviving_child=True,
            audio_remote_role_state=RemoteRoleState.ABSENT_PROVEN,
            transcript_remote_role_state=RemoteRoleState.ABSENT_PROVEN,
            body_effect=EffectTruth.ZERO,
            model_effect=EffectTruth.ZERO,
            readback_at=NOW,
        ).to_dict(),
    ]
    for record in records:
        validator.validate(record)
    invalid = deepcopy(media().to_dict())
    invalid["path_present"] = True
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = deepcopy(transcript_binding().to_dict())
    invalid["binding_id"] = "source.https://host/private/reference"
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    for path_like in (
        "C:private_voice.wav",
        "private/voice.wav",
        "file:private_voice.wav",
        "Ｃ：private_voice.wav",
        "private／voice.wav",
    ):
        invalid = deepcopy(transcript_binding().to_dict())
        invalid["binding_id"] = path_like
        with pytest.raises(ValidationError):
            validator.validate(invalid)
    invalid = deepcopy(transcript_binding().to_dict())
    invalid["producer_binding_state"] = "BOUND"
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = snapshot(v2=CapabilityLeaseV2Current.ISSUED, v2_count=2).to_dict()
    invalid["v2_live_handle_count"] = 0
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = terminal_retire_readback(
        terminal=TerminalKind.FAILED_CLOSED,
        outcome=TerminalRetireOutcome.FAILED_CLOSED_RETIRED_NOT_CONFIRMED,
    ).to_dict()
    invalid["terminal_kind"] = "CONSUMED"
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = records[-1].copy()
    invalid["body_effect"] = "OBSERVED"
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    invalid = deepcopy(records[6])
    del invalid["expected_v2_terminal_history_sha256"]
    with pytest.raises(ValidationError):
        validator.validate(invalid)
    for index in (6, 7, 8, 9, 10):
        invalid = deepcopy(records[index])
        invalid["canonical_producer_acceptance_state"] = "CURRENT"
        with pytest.raises(ValidationError):
            validator.validate(invalid)
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


@pytest.mark.parametrize(
    "host_location",
    (
        "file://private/reference",
        "binding.C:/Users/Alice/private/reference",
        "source.https://host/private/reference",
        "C:private_voice.wav",
        "private/voice.wav",
        "file:private_voice.wav",
        "Ｃ：private_voice.wav",
        "private／voice.wav",
    ),
)
def test_private_identifiers_reject_embedded_host_locations(host_location: str) -> None:
    value = transcript_binding().to_dict()
    value["binding_id"] = host_location
    with pytest.raises(ValueError, match="host path"):
        Task046OwnerReferenceTranscriptBindingFixture.from_dict(value)


def test_private_identifier_python_and_schema_share_200_character_bound() -> None:
    value = transcript_binding().to_dict()
    value["binding_id"] = "a" * 201
    with pytest.raises(ValueError, match="200 characters"):
        Task046OwnerReferenceTranscriptBindingFixture.from_dict(value)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    with pytest.raises(ValidationError):
        validator.validate(value)


def test_module_has_no_live_capability_io_crypto_or_process_effect_surface() -> None:
    path = ROOT / "src" / "ai_video_production" / "owner_voice_private_reference.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint(
        {"os", "pathlib", "subprocess", "socket", "wave", "soundfile", "cryptography", "win32api", "ctypes"}
    )
    names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert "OwnerVoiceReferenceCapabilityV2" not in names
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint({"open", "remove", "unlink", "Popen", "run", "CreateProcess", "DuplicateHandle"})
