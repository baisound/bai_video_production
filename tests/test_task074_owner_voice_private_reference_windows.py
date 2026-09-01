from __future__ import annotations

import ast
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
import copy
from pathlib import Path
import pickle
from threading import Event, Lock as NativeLock
from typing import Any

import pytest

import ai_video_production.owner_voice_private_reference_windows as windows_fixture_module

from ai_video_production.owner_voice_authority import (
    CompletionClass,
    PersistenceState,
    PrivateReferenceState,
    Task074OwnerVoiceAuthorityCompletionReceipt,
)
from ai_video_production.owner_voice_private_reference import (
    OwnerVoiceReferenceMediaFacts,
    OwnerVoiceReferencePreparePlan,
    OwnerVoiceReferenceTranscriptFacts,
    ReferenceSourceClassification,
    RetentionPolicy,
    Task046OwnerReferenceTranscriptBindingFixture,
)
from ai_video_production.owner_voice_private_reference_windows import (
    EXPECTED_BODY_PROCESSING_MODE,
    EXPECTED_CONSUMER,
    EXPECTED_DACL_VERIFICATION_MODE,
    EXPECTED_ENCRYPTION_ALGORITHM,
    EXPECTED_KEY_WRAP_SCOPE,
    EXPECTED_PAIR_PUBLISH_MODE,
    FIXTURE_REQUEST_CONTRACT_VERSION,
    FIXTURE_RESULT_CONTRACT_VERSION,
    FIXTURE_SCOPE,
    PreparationDeliveryFault,
    PreparationFixtureOutcome,
    PreparationTraceFault,
    SimulatedLifecyclePublishState,
    SimulatedPairLedgerState,
    SimulatedReferenceLifecycleState,
    SimulatedRetainedObjectState,
    SimulatedRoleState,
    TRACE_ROW_BY_FAULT,
    WindowsPreparationTraceFixtureRequest,
    WindowsPreparationTraceFixtureResult,
    WindowsPreparationTraceFixtureRuntime,
)
from ai_video_production.serialization import (
    canonical_json_bytes,
    sha256_bytes,
    validate_sha256,
)
from ai_video_production.voice_profile_route_selection import RouteMode


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src"
    / "ai_video_production"
    / "owner_voice_private_reference_windows.py"
)
NOW = "2026-09-01T09:00:00Z"
RECONCILIATION_NOW = "2026-09-01T09:01:00Z"
FIXTURE_DOMAIN = sha256_bytes(b"windows-preparation-fixture-domain")
OTHER_FIXTURE_DOMAIN = sha256_bytes(
    b"windows-preparation-fixture-domain-other"
)
INITIAL_HEAD = sha256_bytes(b"windows-preparation-fixture-head")
REQUEST_HASH_DOMAIN = (
    b"TASK074_WINDOWS_PREPARATION_TRACE_REQUEST_FIXTURE_V1\0"
)
TRACE_HASH_DOMAIN = b"TASK074_WINDOWS_PREPARATION_TRACE_FIXTURE_V1\0"
HEAD_HASH_DOMAIN = b"TASK074_WINDOWS_PREPARATION_TRACE_HEAD_FIXTURE_V1\0"
RESULT_HASH_DOMAIN = (
    b"TASK074_WINDOWS_PREPARATION_TRACE_RESULT_FIXTURE_V1\0"
)
IDENTITY_HASH_DOMAIN = (
    b"TASK074_WINDOWS_PREPARATION_SYNTHETIC_IDENTITY_FIXTURE_V1\0"
)


class _ContentionProbeLock:
    """Real lock that proves the second entrant waited on the first holder."""

    def __init__(self) -> None:
        self._lock = NativeLock()
        self._counter_lock = NativeLock()
        self._first_holding = Event()
        self._second_attempted = Event()
        self.entry_attempts = 0

    @property
    def contention_observed(self) -> bool:
        return self._first_holding.is_set() and self._second_attempted.is_set()

    def __enter__(self) -> "_ContentionProbeLock":
        with self._counter_lock:
            self.entry_attempts += 1
            attempt = self.entry_attempts
        if attempt == 1:
            self._lock.acquire()
            self._first_holding.set()
            if not self._second_attempted.wait(timeout=5):
                self._lock.release()
                raise RuntimeError("second lock acquisition was not attempted")
            return self
        if attempt == 2:
            self._second_attempted.set()
        self._lock.acquire()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> bool:
        del exc_type, exc_value, traceback
        self._lock.release()
        return False


EFFECT_FLAGS = {
    "authority_created",
    "private_body_present",
    "path_present",
    "secret_present",
    "filesystem_read_performed",
    "filesystem_write_performed",
    "native_execution_performed",
    "encryption_performed",
    "key_wrap_performed",
    "dacl_observation_performed",
    "clock_read_performed",
    "model_loaded",
    "inference_started",
    "wav_created",
    "external_effect_started",
}
BOUNDARY_FIELDS = {
    "producer_binding_state",
    "fixture_only",
    "canonical_producer_readback",
    "execution_ready",
    "canonical_reference_snapshot_created",
    "private_capability_created",
    "prepared_verification_receipt_created",
    "revoke_api_available",
    "purge_api_available",
    "body_read_api_available",
}
REQUEST_FIELDS = {
    "contract_version",
    "record_type",
    "task_id",
    "expected_consumer",
    "fixture_scope",
    "operation_id",
    "fixture_domain_sha256",
    "expected_fixture_head_sha256",
    "prepare_plan_sha256",
    "media_facts_sha256",
    "transcript_facts_sha256",
    "transcript_binding_receipt_sha256",
    "trace_fault",
    "delivery_fault",
    "expected_encryption_algorithm",
    "expected_key_wrap_scope",
    "expected_body_processing_mode",
    "expected_pair_publish_mode",
    "expected_dacl_verification_mode",
    *EFFECT_FLAGS,
    *BOUNDARY_FIELDS,
    "request_sha256",
}
PRODUCER_GATES = {
    "G01_PROJECT_BOOTSTRAP": "NOT_CONFIRMED",
    "G02_INSTALLED_STARTUP": "NOT_CONFIRMED",
    "G03_VOICE_PROFILE": "NOT_CONFIRMED",
    "G04_CONSENT": "NOT_CONFIRMED",
    "G05_LOCAL_ROUTE": "NOT_CONFIRMED",
    "G06_HUMAN_ACTION": "NOT_CONFIRMED",
    "G07_OPERATION_TICKET": "NOT_CONFIRMED",
    "G08_PRIVATE_CUSTODY": "NOT_CONFIRMED",
    "G09_PURGE": "NOT_EVALUATED",
    "G10_TASK046_AMENDMENT": "NOT_CONFIRMED",
    "G11_TASK075_CONSUMER": "NOT_EVALUATED",
    "G12_TRUSTED_TIME": "NOT_CONFIRMED",
    "G13_EXECUTION_CURRENTNESS": "NOT_EVALUATED",
    "G14_REFERENCE_TRANSCRIPT": "NOT_CONFIRMED",
}


ExpectedRow = tuple[
    PreparationFixtureOutcome,
    SimulatedReferenceLifecycleState,
    SimulatedRetainedObjectState,
    SimulatedRoleState,
    SimulatedRoleState,
    SimulatedPairLedgerState,
    SimulatedLifecyclePublishState,
]
EXPECTED_ROWS: dict[PreparationTraceFault, ExpectedRow] = {
    PreparationTraceFault.NONE: (
        PreparationFixtureOutcome.PREPARED_SIMULATION_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARED_SIMULATION,
        SimulatedRetainedObjectState.PUBLISHED_SIMULATION,
        SimulatedRoleState.PUBLISHED_SIMULATION,
        SimulatedRoleState.PUBLISHED_SIMULATION,
        SimulatedPairLedgerState.PUBLISHED_SIMULATION,
        SimulatedLifecyclePublishState.COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.BEFORE_CHILD_CREATION: (
        PreparationFixtureOutcome.PREPARE_FAILED_NO_DERIVATIVE_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_NO_DERIVATIVE_SIMULATION,
        SimulatedRetainedObjectState.NONE_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.AUDIO_CHILD_BEFORE_IDENTITY_CAS: (
        PreparationFixtureOutcome.PREPARE_FAILED_FOREIGN_PRESERVED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.FOREIGN_PRESERVED_SIMULATION,
        SimulatedRoleState.FOREIGN_PRESERVED_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.TRANSCRIPT_CHILD_BEFORE_IDENTITY_CAS: (
        PreparationFixtureOutcome.PREPARE_FAILED_FOREIGN_PRESERVED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.FOREIGN_PRESERVED_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedRoleState.FOREIGN_PRESERVED_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.AUDIO_IDENTITY_RECORDED_BEFORE_WRITE: (
        PreparationFixtureOutcome.PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.RECONCILIATION_REQUIRED_SIMULATION,
        SimulatedRoleState.IDENTITY_RECORDED_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.TRANSCRIPT_IDENTITY_RECORDED_BEFORE_WRITE: (
        PreparationFixtureOutcome.PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.RECONCILIATION_REQUIRED_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedRoleState.IDENTITY_RECORDED_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.AUDIO_ENCRYPTED_BEFORE_READBACK: (
        PreparationFixtureOutcome.PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.RECONCILIATION_REQUIRED_SIMULATION,
        SimulatedRoleState.ENCRYPTED_UNPUBLISHED_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.TRANSCRIPT_ENCRYPTED_BEFORE_READBACK: (
        PreparationFixtureOutcome.PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.RECONCILIATION_REQUIRED_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedRoleState.ENCRYPTED_UNPUBLISHED_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.AUDIO_PUBLISHED_BEFORE_TRANSCRIPT: (
        PreparationFixtureOutcome.PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.RECONCILIATION_REQUIRED_SIMULATION,
        SimulatedRoleState.PUBLISHED_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.TRANSCRIPT_PUBLISHED_BEFORE_AUDIO: (
        PreparationFixtureOutcome.PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.RECONCILIATION_REQUIRED_SIMULATION,
        SimulatedRoleState.ABSENT_PROVEN_SIMULATION,
        SimulatedRoleState.PUBLISHED_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.BOTH_PUBLISHED_BEFORE_PAIR: (
        PreparationFixtureOutcome.PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.RECONCILIATION_REQUIRED_SIMULATION,
        SimulatedRoleState.PUBLISHED_SIMULATION,
        SimulatedRoleState.PUBLISHED_SIMULATION,
        SimulatedPairLedgerState.ABSENT_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
    PreparationTraceFault.PAIR_PUBLISHED_BEFORE_LIFECYCLE: (
        PreparationFixtureOutcome.PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE,
        SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION,
        SimulatedRetainedObjectState.RECONCILIATION_REQUIRED_SIMULATION,
        SimulatedRoleState.PUBLISHED_SIMULATION,
        SimulatedRoleState.PUBLISHED_SIMULATION,
        SimulatedPairLedgerState.PUBLISHED_SIMULATION,
        SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION,
    ),
}


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def media(label: str = "primary") -> OwnerVoiceReferenceMediaFacts:
    return OwnerVoiceReferenceMediaFacts.create(
        codec_name="pcm_s24le",
        valid_bits_per_sample=24,
        sample_rate_hz=48000,
        duration_ms=30000,
        decoded_frame_count=1440000,
        container_size_bytes=4320044,
        audio_sha256=digest(f"non-audio-sentinel:{label}"),
    )


def transcript(label: str = "primary") -> OwnerVoiceReferenceTranscriptFacts:
    return OwnerVoiceReferenceTranscriptFacts.create(
        transcript_utf8_sha256=digest(f"body-free-transcript:{label}"),
        unicode_scalar_count=120,
        utf8_byte_count=240,
    )


def binding(
    media_facts: OwnerVoiceReferenceMediaFacts,
    transcript_facts: OwnerVoiceReferenceTranscriptFacts,
    *,
    label: str = "primary",
    project_id: str = "project.alpha",
    voice_profile_id: str = "voice.owner",
    voice_profile_revision_sha256: str | None = None,
    consent_current_evaluation_sha256: str | None = None,
    audio_source_identity_sha256: str | None = None,
    audio_sha256: str | None = None,
    transcript_utf8_sha256: str | None = None,
    transcript_facts_sha256: str | None = None,
) -> Task046OwnerReferenceTranscriptBindingFixture:
    media_value = media_facts.to_dict()
    transcript_value = transcript_facts.to_dict()
    return Task046OwnerReferenceTranscriptBindingFixture.create(
        binding_id=f"task046.reference.binding.{label}",
        project_id=project_id,
        voice_profile_id=voice_profile_id,
        voice_profile_revision_sha256=(
            voice_profile_revision_sha256 or digest("voice-profile")
        ),
        consent_current_evaluation_sha256=(
            consent_current_evaluation_sha256 or digest("consent-current")
        ),
        audio_source_identity_sha256=(
            audio_source_identity_sha256 or digest("audio-source")
        ),
        audio_sha256=audio_sha256 or media_value["audio_sha256"],
        transcript_revision=3,
        transcript_utf8_sha256=(
            transcript_utf8_sha256
            or transcript_value["transcript_utf8_sha256"]
        ),
        transcript_facts_sha256=(
            transcript_facts_sha256
            or transcript_value["transcript_facts_sha256"]
        ),
        human_verification_receipt_sha256=digest(f"human-match:{label}"),
        verified_at=NOW,
    )


def plan(
    operation_id: str,
    media_facts: OwnerVoiceReferenceMediaFacts,
    transcript_facts: OwnerVoiceReferenceTranscriptFacts,
    transcript_binding: Task046OwnerReferenceTranscriptBindingFixture,
    *,
    label: str = "primary",
    project_id: str | None = None,
    voice_profile_id: str | None = None,
    voice_profile_revision_sha256: str | None = None,
    consent_current_evaluation_sha256: str | None = None,
    audio_source_identity_sha256: str | None = None,
    media_facts_sha256: str | None = None,
    transcript_facts_sha256: str | None = None,
    transcript_binding_receipt_sha256: str | None = None,
    route_selection_sha256: str | None = None,
) -> OwnerVoiceReferencePreparePlan:
    media_value = media_facts.to_dict()
    transcript_value = transcript_facts.to_dict()
    binding_value = transcript_binding.to_dict()
    return OwnerVoiceReferencePreparePlan.create(
        operation_id=operation_id,
        project_id=project_id or binding_value["project_id"],
        project_manifest_revision_sha256=digest("manifest"),
        installed_context_sha256=digest("installed-context"),
        voice_profile_id=voice_profile_id or binding_value["voice_profile_id"],
        voice_profile_revision_sha256=(
            voice_profile_revision_sha256
            or binding_value["voice_profile_revision_sha256"]
        ),
        consent_current_evaluation_sha256=(
            consent_current_evaluation_sha256
            or binding_value["consent_current_evaluation_sha256"]
        ),
        route_selection_sha256=(
            route_selection_sha256 or digest("route-selection")
        ),
        source_classification=(
            ReferenceSourceClassification.TASK046_PRIVATE_RECORDING_REFERENCE
        ),
        audio_source_identity_sha256=(
            audio_source_identity_sha256
            or binding_value["audio_source_identity_sha256"]
        ),
        transcript_source_identity_sha256=digest("transcript-source"),
        media_facts_sha256=(
            media_facts_sha256 or media_value["media_facts_sha256"]
        ),
        transcript_facts_sha256=(
            transcript_facts_sha256
            or transcript_value["transcript_facts_sha256"]
        ),
        transcript_binding_receipt_sha256=(
            transcript_binding_receipt_sha256
            or binding_value["transcript_binding_receipt_sha256"]
        ),
        retention_policy=RetentionPolicy.OWNER_SELECTED_EXPIRY,
        retention_policy_revision_sha256=digest("retention-policy"),
        expires_at="2026-10-01T09:00:00Z",
        expected_lifecycle_snapshot_sha256=digest("lifecycle-head"),
        human_action_receipt_sha256=digest("human-action"),
        task072_ticket_sha256=digest("task072-ticket"),
        created_at=NOW,
    )


Bundle = tuple[
    OwnerVoiceReferencePreparePlan,
    OwnerVoiceReferenceMediaFacts,
    OwnerVoiceReferenceTranscriptFacts,
    Task046OwnerReferenceTranscriptBindingFixture,
]


def make_bundle(
    operation_id: str = "reference.prepare.primary",
    *,
    label: str = "primary",
) -> Bundle:
    media_facts = media(label)
    transcript_facts = transcript(label)
    transcript_binding = binding(
        media_facts,
        transcript_facts,
        label=label,
    )
    prepare_plan = plan(
        operation_id,
        media_facts,
        transcript_facts,
        transcript_binding,
        label=label,
    )
    return (
        prepare_plan,
        media_facts,
        transcript_facts,
        transcript_binding,
    )


def fixture_runtime(
    *,
    fixture_domain_sha256: str = FIXTURE_DOMAIN,
) -> WindowsPreparationTraceFixtureRuntime:
    return WindowsPreparationTraceFixtureRuntime(
        expected_consumer=EXPECTED_CONSUMER,
        fixture_scope=FIXTURE_SCOPE,
        fixture_domain_sha256=fixture_domain_sha256,
        initial_fixture_head_sha256=INITIAL_HEAD,
        readback_at=NOW,
        reconciliation_readback_at=RECONCILIATION_NOW,
    )


def fixture_request(
    bundle_value: Bundle,
    *,
    fixture_domain_sha256: str = FIXTURE_DOMAIN,
    expected_fixture_head_sha256: str = INITIAL_HEAD,
    trace_fault: PreparationTraceFault = PreparationTraceFault.NONE,
    delivery_fault: PreparationDeliveryFault = PreparationDeliveryFault.NONE,
) -> WindowsPreparationTraceFixtureRequest:
    prepare_plan, media_facts, transcript_facts, transcript_binding = (
        bundle_value
    )
    return WindowsPreparationTraceFixtureRequest.create(
        operation_id=prepare_plan.to_dict()["operation_id"],
        fixture_domain_sha256=fixture_domain_sha256,
        expected_fixture_head_sha256=expected_fixture_head_sha256,
        plan=prepare_plan,
        media_facts=media_facts,
        transcript_facts=transcript_facts,
        transcript_binding=transcript_binding,
        trace_fault=trace_fault,
        delivery_fault=delivery_fault,
    )


def execute(
    runtime: WindowsPreparationTraceFixtureRuntime,
    request: WindowsPreparationTraceFixtureRequest,
    bundle_value: Bundle,
) -> WindowsPreparationTraceFixtureResult:
    return runtime.simulate_prepare(request, *bundle_value)


def rehash_request(value: dict[str, Any]) -> None:
    unsigned = {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key != "request_sha256"
    }
    value["request_sha256"] = sha256_bytes(
        REQUEST_HASH_DOMAIN + canonical_json_bytes(unsigned)
    )


def assert_effect_zero(value: Mapping[str, Any]) -> None:
    assert {name: value[name] for name in EFFECT_FLAGS} == {
        name: False for name in EFFECT_FLAGS
    }
    assert value["producer_binding_state"] == "NOT_BOUND"
    assert value["fixture_only"] is True
    assert value["canonical_producer_readback"] is False
    assert value["execution_ready"] is False
    assert value["canonical_reference_snapshot_created"] is False
    assert value["private_capability_created"] is False
    assert value["prepared_verification_receipt_created"] is False
    assert value["revoke_api_available"] is False
    assert value["purge_api_available"] is False
    assert value["body_read_api_available"] is False


def completion(
    reference_fields: Mapping[str, str | None],
) -> Task074OwnerVoiceAuthorityCompletionReceipt:
    return Task074OwnerVoiceAuthorityCompletionReceipt.create(
        completion_id="task074.completion.fixture.status",
        completion_class=CompletionClass.TASK074_IMPLEMENTATION_COMPLETE,
        project_id="project.alpha",
        project_manifest_revision_sha256=digest("manifest"),
        installed_startup_context_binding_sha256=digest("installed-context"),
        voice_profile_id="voice.owner",
        voice_profile_revision=7,
        voice_profile_revision_sha256=digest("voice-profile"),
        consent_current_evaluation_sha256=digest("consent-current"),
        route_mode=RouteMode.ZERO_SHOT_LOCAL,
        route_selection_revision=3,
        route_selection_sha256=digest("route-selection"),
        route_selection_store_receipt_sha256=digest(
            "route-selection-store-receipt"
        ),
        reference_lifecycle_snapshot_sha256=reference_fields[
            "reference_lifecycle_snapshot_sha256"
        ],
        reference_preparation_receipt_sha256=reference_fields[
            "reference_preparation_receipt_sha256"
        ],
        reference_capability_binding_sha256=reference_fields[
            "reference_capability_binding_sha256"
        ],
        reference_media_policy_sha256=reference_fields[
            "reference_media_policy_sha256"
        ],
        reference_transcript_binding_receipt_sha256=reference_fields[
            "reference_transcript_binding_receipt_sha256"
        ],
        model_candidate_revision_sha256=None,
        model_candidate_currentness_sha256=None,
        human_action_registry_receipt_sha256=digest("human-registry"),
        operation_profile_registry_receipt_sha256=digest(
            "operation-registry"
        ),
        persistence_state=PersistenceState.DURABLE_VERIFIED,
        private_reference_state=PrivateReferenceState.NOT_CONFIRMED,
        owner_reference_verified=False,
        issued_at=NOW,
        expires_at="2026-09-01T10:00:00Z",
    )


def test_source_is_fixture_only_and_has_no_native_product_or_canonical_port() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    called_names = {
        node.func.id
        if isinstance(node.func, ast.Name)
        else node.func.attr
        if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert imported_modules.isdisjoint(
        {
            "os",
            "pathlib",
            "subprocess",
            "ctypes",
            "win32api",
            "win32crypt",
            "cryptography",
            "soundfile",
            "wave",
            "torch",
        }
    )
    assert imported_names.isdisjoint(
        {
            "ReferenceDomainSnapshot",
            "CapabilityLeaseV1Current",
            "CapabilityLeaseV2Current",
        }
    )
    assert called_names.isdisjoint(
        {
            "open",
            "read_bytes",
            "read_text",
            "write_bytes",
            "write_text",
            "AESGCM",
            "CryptProtectData",
            "load_model",
            "infer",
        }
    )
    assert "owner_voice_authority" not in imported_modules
    assert "voice_studio_application" not in imported_modules
    assert "owner_narration_local_primary" not in imported_modules

    runtime = fixture_runtime()
    assert runtime.fixture_only is True
    assert runtime.canonical_port_compatible is False
    assert runtime.producer_binding_state == "NOT_BOUND"
    assert runtime.execution_ready is False
    for forbidden in (
        "validate_prepare_plan",
        "compare_and_transition",
        "revoke",
        "purge",
        "read_body",
        "issue_capability",
    ):
        assert not hasattr(runtime, forbidden)
    with pytest.raises(TypeError):
        TRACE_ROW_BY_FAULT[PreparationTraceFault.NONE] = TRACE_ROW_BY_FAULT[
            PreparationTraceFault.NONE
        ]


def test_request_is_exact_body_free_hashed_immutable_and_round_trips() -> None:
    bundle_value = make_bundle()
    request = fixture_request(bundle_value)
    value = request.to_dict()

    assert set(value) == REQUEST_FIELDS
    assert value["contract_version"] == FIXTURE_REQUEST_CONTRACT_VERSION
    assert value["record_type"] == "WindowsPreparationTraceFixtureRequest"
    assert value["task_id"] == EXPECTED_CONSUMER
    assert value["expected_consumer"] == EXPECTED_CONSUMER
    assert value["fixture_scope"] == FIXTURE_SCOPE
    assert value["expected_encryption_algorithm"] == (
        EXPECTED_ENCRYPTION_ALGORITHM
    )
    assert value["expected_key_wrap_scope"] == EXPECTED_KEY_WRAP_SCOPE
    assert value["expected_body_processing_mode"] == (
        EXPECTED_BODY_PROCESSING_MODE
    )
    assert value["expected_pair_publish_mode"] == EXPECTED_PAIR_PUBLISH_MODE
    assert value["expected_dacl_verification_mode"] == (
        EXPECTED_DACL_VERIFICATION_MODE
    )
    assert_effect_zero(value)
    request_sha256 = value.pop("request_sha256")
    assert request_sha256 == sha256_bytes(
        REQUEST_HASH_DOMAIN + canonical_json_bytes(value)
    )
    value["request_sha256"] = request_sha256
    assert WindowsPreparationTraceFixtureRequest.from_dict(value).to_dict() == (
        value
    )

    detached = request.to_dict()
    detached["operation_id"] = "detached.change"
    assert request.to_dict()["operation_id"] == "reference.prepare.primary"
    with pytest.raises(AttributeError):
        request._data = {}  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        del request._data  # type: ignore[attr-defined]
    with pytest.raises(ValueError, match="operation identities"):
        WindowsPreparationTraceFixtureRequest.create(
            operation_id="different.operation",
            fixture_domain_sha256=FIXTURE_DOMAIN,
            expected_fixture_head_sha256=INITIAL_HEAD,
            plan=bundle_value[0],
            media_facts=bundle_value[1],
            transcript_facts=bundle_value[2],
            transcript_binding=bundle_value[3],
        )
    with pytest.raises(TypeError):
        WindowsPreparationTraceFixtureRequest.create(
            operation_id="reference.prepare.primary",
            fixture_domain_sha256=FIXTURE_DOMAIN,
            expected_fixture_head_sha256=INITIAL_HEAD,
            plan=bundle_value[0],
            media_facts=bundle_value[1],
            transcript_facts=bundle_value[2],
            transcript_binding=bundle_value[3],
            simulated_audio_identity_sha256=digest("caller-controlled"),
        )


def test_request_tamper_body_path_policy_authority_type_and_hash_fail_closed() -> None:
    original = fixture_request(make_bundle()).to_dict()
    candidates: list[dict[str, Any]] = []
    for field, replacement in (
        ("task_id", "TASK-043"),
        ("expected_consumer", "TASK-075"),
        ("fixture_scope", "PRODUCT_RUNTIME"),
        ("operation_id", r"C:\private\owner.wav"),
        ("expected_encryption_algorithm", "NONE"),
        ("expected_key_wrap_scope", "WINDOWS_MACHINE"),
        ("trace_fault", "UNSUPPORTED_TRACE"),
        ("delivery_fault", "UNSUPPORTED_DELIVERY"),
        ("producer_binding_state", "BOUND"),
        ("fixture_only", False),
        ("fixture_only", 1),
        ("canonical_producer_readback", True),
        ("execution_ready", True),
        ("private_body_present", True),
        ("path_present", True),
        ("secret_present", True),
        ("filesystem_read_performed", True),
        ("native_execution_performed", True),
        ("encryption_performed", True),
        ("model_loaded", True),
        ("inference_started", True),
        ("wav_created", True),
    ):
        value = copy.deepcopy(original)
        value[field] = replacement
        rehash_request(value)
        candidates.append(value)

    extra_body = copy.deepcopy(original)
    extra_body["private_audio_body_base64"] = "raw-private-body"
    rehash_request(extra_body)
    candidates.append(extra_body)
    missing_binding = copy.deepcopy(original)
    del missing_binding["prepare_plan_sha256"]
    rehash_request(missing_binding)
    candidates.append(missing_binding)
    wrong_digest = copy.deepcopy(original)
    wrong_digest["request_sha256"] = digest("wrong-request-digest")
    candidates.append(wrong_digest)

    for value in candidates:
        with pytest.raises((TypeError, ValueError)):
            WindowsPreparationTraceFixtureRequest.from_dict(value)


def test_success_trace_has_exact_lineage_hashes_expected_policy_and_no_effect() -> None:
    bundle_value = make_bundle()
    runtime = fixture_runtime()
    request = fixture_request(bundle_value)
    result = execute(runtime, request, bundle_value)
    trace = result.fixture_trace()
    receipt = result.fixture_receipt()

    assert result.outcome is (
        PreparationFixtureOutcome.PREPARED_SIMULATION_FIXTURE
    )
    assert result.underlying_outcome is result.outcome
    assert result.fixture_only is True
    assert result.canonical_port_compatible is False
    assert result.producer_binding_state == "NOT_BOUND"
    assert result.execution_ready is False
    assert not isinstance(result, Mapping)
    assert trace["trace_truth"] == "SIMULATED_ONLY"
    assert trace["operation_id"] == bundle_value[0].to_dict()["operation_id"]
    assert trace["predecessor_fixture_head_sha256"] == INITIAL_HEAD
    assert trace["result_fixture_head_sha256"] == runtime.fixture_head_sha256
    assert trace["request_sha256"] == request.to_dict()["request_sha256"]
    assert trace["producer_gates"] == PRODUCER_GATES
    assert trace["actual_native_contract_coverage"] == "NOT_CONFIRMED"
    assert trace["task074_c_completion_state"] == "NOT_CONFIRMED"
    assert trace["task074_d_completion_state"] == "NOT_CONFIRMED"
    assert trace["encryption_observation"] == "NOT_EXECUTED"
    assert trace["key_wrap_observation"] == "NOT_EXECUTED"
    assert trace["streaming_observation"] == "NOT_EXECUTED"
    assert trace["native_observation"] == "NOT_EXECUTED"
    assert trace["dacl_observation"] == "NOT_CONFIRMED"
    assert trace["custody_observation"] == "NOT_CONFIRMED"
    assert trace["simulated_capability_issue_state"] == (
        "NOT_EXECUTED_SIMULATION"
    )
    assert_effect_zero(trace)

    identity_fields = {
        "simulated_reservation_identity_sha256",
        "simulated_intended_audio_identity_sha256",
        "simulated_intended_transcript_identity_sha256",
        "simulated_pair_ledger_identity_sha256",
    }
    identities = {trace[name] for name in identity_fields}
    assert len(identities) == 4
    for identity in identities:
        validate_sha256(identity, field_name="synthetic_identity")

    trace_body = {
        key: copy.deepcopy(value)
        for key, value in trace.items()
        if key not in {
            "simulated_trace_sha256",
            "result_fixture_head_sha256",
        }
    }
    assert trace["simulated_trace_sha256"] == sha256_bytes(
        TRACE_HASH_DOMAIN + canonical_json_bytes(trace_body)
    )
    assert trace["result_fixture_head_sha256"] == sha256_bytes(
        HEAD_HASH_DOMAIN
        + canonical_json_bytes(
            {
                "fixture_domain_sha256": FIXTURE_DOMAIN,
                "predecessor_fixture_head_sha256": INITIAL_HEAD,
                "request_sha256": request.to_dict()["request_sha256"],
                "simulated_trace_sha256": trace["simulated_trace_sha256"],
            }
        )
    )
    receipt_body = {
        key: copy.deepcopy(value)
        for key, value in receipt.items()
        if key != "result_receipt_sha256"
    }
    assert receipt["result_receipt_sha256"] == sha256_bytes(
        RESULT_HASH_DOMAIN + canonical_json_bytes(receipt_body)
    )
    assert receipt["contract_version"] == FIXTURE_RESULT_CONTRACT_VERSION
    assert receipt["delivery_state"] == "DELIVERED_SIMULATION"
    assert receipt["terminal_trace_disclosed"] is True
    assert receipt["automatic_retry_allowed"] is False
    assert receipt["replay"] is False
    assert_effect_zero(receipt)
    assert runtime.terminal_append_count == 1
    assert runtime.operation_count == 1

    detached_trace = result.fixture_trace()
    detached_trace["operation_id"] = "detached.change"
    detached_receipt = result.fixture_receipt()
    detached_receipt["delivery_state"] = "TAMPERED"
    assert result.fixture_trace()["operation_id"] == "reference.prepare.primary"
    assert result.fixture_receipt()["delivery_state"] == (
        "DELIVERED_SIMULATION"
    )
    with pytest.raises(AttributeError):
        result._trace = {}  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        del result._receipt  # type: ignore[attr-defined]


def test_status_only_composition_keeps_canonical_reference_unconfirmed() -> None:
    bundle_value = make_bundle()
    runtime = fixture_runtime()
    result = execute(runtime, fixture_request(bundle_value), bundle_value)
    reference_fields = result.status_only_completion_reference_fields()

    assert reference_fields == {
        "reference_lifecycle_snapshot_sha256": None,
        "reference_preparation_receipt_sha256": None,
        "reference_capability_binding_sha256": None,
        "reference_media_policy_sha256": None,
        "reference_transcript_binding_receipt_sha256": None,
    }
    completion_value = completion(reference_fields).to_dict()
    assert completion_value["private_reference_state"] == (
        PrivateReferenceState.NOT_CONFIRMED.value
    )
    assert completion_value["owner_reference_verified"] is False
    assert completion_value["receipt_authority_kind"] == "STATUS_ONLY"
    assert completion_value["producer_binding_state"] == "NOT_BOUND"
    assert completion_value["fixture_only"] is True
    assert completion_value["canonical_producer_readback"] is False
    assert completion_value["execution_ready"] is False
    for field in reference_fields:
        assert completion_value[field] is None

    elevated = dict(reference_fields)
    elevated["reference_preparation_receipt_sha256"] = (
        result.fixture_trace()["simulated_trace_sha256"]
    )
    with pytest.raises(ValueError):
        completion(elevated)


@pytest.mark.parametrize(
    ("fault", "expected"),
    list(EXPECTED_ROWS.items()),
)
def test_all_trace_faults_have_exact_simulation_state_and_one_head_append(
    fault: PreparationTraceFault,
    expected: ExpectedRow,
) -> None:
    bundle_value = make_bundle(
        operation_id=f"reference.prepare.{fault.value.lower()}"
    )
    runtime = fixture_runtime()
    result = execute(
        runtime,
        fixture_request(bundle_value, trace_fault=fault),
        bundle_value,
    )
    trace = result.fixture_trace()
    (
        expected_outcome,
        expected_lifecycle,
        expected_retained,
        expected_audio,
        expected_transcript,
        expected_pair,
        expected_publish,
    ) = expected

    assert result.outcome is expected_outcome
    assert result.underlying_outcome is expected_outcome
    assert trace["underlying_fixture_outcome"] == expected_outcome.value
    assert trace["simulated_reference_lifecycle_state"] == (
        expected_lifecycle.value
    )
    assert trace["simulated_retained_object_state"] == expected_retained.value
    assert trace["simulated_audio_role_state"] == expected_audio.value
    assert trace["simulated_transcript_role_state"] == (
        expected_transcript.value
    )
    assert trace["simulated_pair_ledger_state"] == expected_pair.value
    assert trace["simulated_lifecycle_publish_state"] == (
        expected_publish.value
    )
    assert trace["trace_truth"] == "SIMULATED_ONLY"
    assert runtime.fixture_head_sha256 == trace["result_fixture_head_sha256"]
    assert runtime.fixture_head_sha256 != INITIAL_HEAD
    assert runtime.terminal_append_count == 1
    assert runtime.operation_count == 1
    assert runtime.ambiguous_operation_id is None


@pytest.mark.parametrize(
    ("fault", "expected"),
    list(EXPECTED_ROWS.items()),
)
def test_all_trace_faults_reply_loss_require_exact_reconcile_without_reappend(
    fault: PreparationTraceFault,
    expected: ExpectedRow,
) -> None:
    operation_id = f"reference.loss.{fault.value.lower()}"
    bundle_value = make_bundle(operation_id=operation_id)
    runtime = fixture_runtime()
    request = fixture_request(
        bundle_value,
        trace_fault=fault,
        delivery_fault=PreparationDeliveryFault.AFTER_COMMIT_BEFORE_READBACK,
    )
    ambiguous = execute(runtime, request, bundle_value)
    committed_head = runtime.fixture_head_sha256

    assert ambiguous.outcome is (
        PreparationFixtureOutcome.OUTCOME_NOT_CONFIRMED_FIXTURE
    )
    assert ambiguous.underlying_outcome is None
    assert ambiguous.fixture_trace() is None
    assert ambiguous.fixture_receipt()["delivery_state"] == (
        "REPLY_LOST_SIMULATION"
    )
    assert ambiguous.fixture_receipt()["terminal_trace_disclosed"] is False
    assert ambiguous.fixture_receipt()["underlying_fixture_outcome"] is None
    assert ambiguous.fixture_receipt()["simulated_trace_sha256"] is None
    assert ambiguous.fixture_receipt()["result_fixture_head_sha256"] is None
    assert ambiguous.fixture_receipt()["automatic_retry_allowed"] is False
    assert runtime.ambiguous_operation_id == operation_id
    assert runtime.terminal_append_count == 1
    assert committed_head != INITIAL_HEAD

    blocked_bundle = make_bundle(
        operation_id=f"{operation_id}.blocked",
        label="blocked",
    )
    blocked_request = fixture_request(
        blocked_bundle,
        expected_fixture_head_sha256=committed_head,
    )
    with pytest.raises(RuntimeError, match="reconciled"):
        execute(runtime, blocked_request, blocked_bundle)

    wrong_fault = (
        PreparationTraceFault.BEFORE_CHILD_CREATION
        if fault is PreparationTraceFault.NONE
        else PreparationTraceFault.NONE
    )
    wrong_lineage = fixture_request(
        bundle_value,
        trace_fault=wrong_fault,
        delivery_fault=PreparationDeliveryFault.AFTER_COMMIT_BEFORE_READBACK,
    )
    with pytest.raises(ValueError, match="exact reconcilable"):
        runtime.simulate_reconcile_prepare_unknown(
            wrong_lineage,
            *bundle_value,
        )
    assert runtime.fixture_head_sha256 == committed_head
    assert runtime.terminal_append_count == 1
    assert runtime.ambiguous_operation_id == operation_id

    reconciled = runtime.simulate_reconcile_prepare_unknown(
        request,
        *bundle_value,
    )
    assert reconciled.outcome is expected[0]
    assert reconciled.underlying_outcome is expected[0]
    assert reconciled.fixture_trace() is not None
    assert reconciled.fixture_trace()["result_fixture_head_sha256"] == (
        committed_head
    )
    assert reconciled.fixture_receipt()["delivery_state"] == (
        "RECONCILED_SIMULATION"
    )
    assert reconciled.fixture_receipt()["terminal_trace_disclosed"] is True
    assert reconciled.fixture_receipt()["underlying_fixture_outcome"] == (
        expected[0].value
    )
    assert runtime.fixture_head_sha256 == committed_head
    assert runtime.terminal_append_count == 1
    assert runtime.operation_count == 1
    assert runtime.ambiguous_operation_id is None

    with pytest.raises(ValueError, match="exact reconcilable"):
        runtime.simulate_reconcile_prepare_unknown(request, *bundle_value)
    with pytest.raises(RuntimeError, match="terminal"):
        execute(runtime, blocked_request, blocked_bundle)
    assert runtime.fixture_head_sha256 == committed_head
    assert runtime.terminal_append_count == 1


def test_input_digest_and_cross_binding_failures_do_not_reserve_or_append() -> None:
    bundle_value = make_bundle()
    original_request = fixture_request(bundle_value)
    prepare_plan, media_facts, transcript_facts, transcript_binding = (
        bundle_value
    )
    wrong_media = media("wrong")
    wrong_transcript = transcript("wrong")
    wrong_binding = binding(
        media_facts,
        transcript_facts,
        label="wrong",
        audio_source_identity_sha256=digest("wrong-audio-source"),
    )
    wrong_plan = plan(
        "reference.prepare.wrong",
        media_facts,
        transcript_facts,
        transcript_binding,
        label="wrong",
        voice_profile_revision_sha256=digest("wrong-voice-profile"),
    )
    cases = [
        (
            original_request,
            (prepare_plan, wrong_media, transcript_facts, transcript_binding),
            "digest binding",
        ),
        (
            original_request,
            (prepare_plan, media_facts, wrong_transcript, transcript_binding),
            "digest binding",
        ),
        (
            original_request,
            (prepare_plan, media_facts, transcript_facts, wrong_binding),
            "digest binding",
        ),
        (
            fixture_request(
                (wrong_plan, media_facts, transcript_facts, transcript_binding)
            ),
            (wrong_plan, media_facts, transcript_facts, transcript_binding),
            "cross-binding",
        ),
        (
            fixture_request(
                (prepare_plan, media_facts, transcript_facts, wrong_binding)
            ),
            (prepare_plan, media_facts, transcript_facts, wrong_binding),
            "cross-binding",
        ),
        (
            fixture_request(
                (
                    prepare_plan,
                    wrong_media,
                    transcript_facts,
                    transcript_binding,
                )
            ),
            (
                prepare_plan,
                wrong_media,
                transcript_facts,
                transcript_binding,
            ),
            "cross-binding",
        ),
        (
            fixture_request(
                (
                    prepare_plan,
                    media_facts,
                    wrong_transcript,
                    transcript_binding,
                )
            ),
            (
                prepare_plan,
                media_facts,
                wrong_transcript,
                transcript_binding,
            ),
            "cross-binding",
        ),
    ]

    for request, supplied_bundle, error_match in cases:
        runtime = fixture_runtime()
        with pytest.raises(ValueError, match=error_match):
            execute(runtime, request, supplied_bundle)
        assert runtime.fixture_head_sha256 == INITIAL_HEAD
        assert runtime.terminal_append_count == 0
        assert runtime.operation_count == 0

    runtime = fixture_runtime()
    with pytest.raises(TypeError, match="request"):
        runtime.simulate_prepare(  # type: ignore[arg-type]
            object(),
            *bundle_value,
        )
    assert runtime.fixture_head_sha256 == INITIAL_HEAD
    assert runtime.terminal_append_count == 0
    assert runtime.operation_count == 0


def test_each_cross_binding_coordinate_fails_independently_without_state_delta() -> None:
    operation_id = "reference.prepare.coordinates"
    media_facts = media("coordinates")
    transcript_facts = transcript("coordinates")
    base_binding = binding(
        media_facts,
        transcript_facts,
        label="coordinates",
    )
    base_plan = plan(
        operation_id,
        media_facts,
        transcript_facts,
        base_binding,
    )
    base_bundle: Bundle = (
        base_plan,
        media_facts,
        transcript_facts,
        base_binding,
    )
    cases: list[
        tuple[str, WindowsPreparationTraceFixtureRequest, Bundle, str]
    ] = []

    base_request = fixture_request(base_bundle)
    for digest_field in (
        "prepare_plan_sha256",
        "media_facts_sha256",
        "transcript_facts_sha256",
        "transcript_binding_receipt_sha256",
    ):
        value = base_request.to_dict()
        value[digest_field] = digest(f"wrong:{digest_field}")
        rehash_request(value)
        cases.append(
            (
                f"request:{digest_field}",
                WindowsPreparationTraceFixtureRequest.from_dict(value),
                base_bundle,
                "digest binding",
            )
        )

    operation_value = base_request.to_dict()
    operation_value["operation_id"] = "reference.prepare.other"
    rehash_request(operation_value)
    cases.append(
        (
            "request:operation_id",
            WindowsPreparationTraceFixtureRequest.from_dict(operation_value),
            base_bundle,
            "cross-binding",
        )
    )

    coordinate_specs = [
        (
            "project_id",
            {
                "binding_kwargs": {"project_id": "project.beta"},
                "plan_kwargs": {"project_id": "project.alpha"},
            },
        ),
        (
            "voice_profile_id",
            {
                "binding_kwargs": {"voice_profile_id": "voice.other"},
                "plan_kwargs": {"voice_profile_id": "voice.owner"},
            },
        ),
        (
            "voice_profile_revision_sha256",
            {
                "binding_kwargs": {
                    "voice_profile_revision_sha256": digest(
                        "voice-profile-other"
                    )
                },
                "plan_kwargs": {
                    "voice_profile_revision_sha256": digest("voice-profile")
                },
            },
        ),
        (
            "consent_current_evaluation_sha256",
            {
                "binding_kwargs": {
                    "consent_current_evaluation_sha256": digest(
                        "consent-other"
                    )
                },
                "plan_kwargs": {
                    "consent_current_evaluation_sha256": digest(
                        "consent-current"
                    )
                },
            },
        ),
        (
            "audio_source_identity_sha256",
            {
                "binding_kwargs": {
                    "audio_source_identity_sha256": digest(
                        "audio-source-other"
                    )
                },
                "plan_kwargs": {
                    "audio_source_identity_sha256": digest("audio-source")
                },
            },
        ),
    ]
    for coordinate, spec in coordinate_specs:
        changed_binding = binding(
            media_facts,
            transcript_facts,
            label="coordinates",
            **spec["binding_kwargs"],
        )
        changed_plan = plan(
            operation_id,
            media_facts,
            transcript_facts,
            changed_binding,
            **spec["plan_kwargs"],
        )
        changed_bundle: Bundle = (
            changed_plan,
            media_facts,
            transcript_facts,
            changed_binding,
        )
        cases.append(
            (
                coordinate,
                fixture_request(changed_bundle),
                changed_bundle,
                "cross-binding",
            )
        )

    wrong_audio_binding = binding(
        media_facts,
        transcript_facts,
        label="coordinates",
        audio_sha256=digest("wrong-audio-sha"),
    )
    wrong_audio_plan = plan(
        operation_id,
        media_facts,
        transcript_facts,
        wrong_audio_binding,
    )
    wrong_audio_bundle: Bundle = (
        wrong_audio_plan,
        media_facts,
        transcript_facts,
        wrong_audio_binding,
    )
    cases.append(
        (
            "audio_sha256",
            fixture_request(wrong_audio_bundle),
            wrong_audio_bundle,
            "cross-binding",
        )
    )

    wrong_utf8_binding = binding(
        media_facts,
        transcript_facts,
        label="coordinates",
        transcript_utf8_sha256=digest("wrong-transcript-utf8"),
    )
    wrong_utf8_plan = plan(
        operation_id,
        media_facts,
        transcript_facts,
        wrong_utf8_binding,
    )
    wrong_utf8_bundle: Bundle = (
        wrong_utf8_plan,
        media_facts,
        transcript_facts,
        wrong_utf8_binding,
    )
    cases.append(
        (
            "transcript_utf8_sha256",
            fixture_request(wrong_utf8_bundle),
            wrong_utf8_bundle,
            "cross-binding",
        )
    )

    wrong_transcript_binding = binding(
        media_facts,
        transcript_facts,
        label="coordinates",
        transcript_facts_sha256=digest("wrong-transcript-facts"),
    )
    wrong_transcript_plan = plan(
        operation_id,
        media_facts,
        transcript_facts,
        wrong_transcript_binding,
    )
    wrong_transcript_bundle: Bundle = (
        wrong_transcript_plan,
        media_facts,
        transcript_facts,
        wrong_transcript_binding,
    )
    cases.append(
        (
            "binding:transcript_facts_sha256",
            fixture_request(wrong_transcript_bundle),
            wrong_transcript_bundle,
            "cross-binding",
        )
    )

    other_media = media("coordinates-other-media")
    other_media_binding = binding(
        other_media,
        transcript_facts,
        label="coordinates-media",
    )
    plan_with_old_media = plan(
        operation_id,
        media_facts,
        transcript_facts,
        other_media_binding,
    )
    media_bundle: Bundle = (
        plan_with_old_media,
        other_media,
        transcript_facts,
        other_media_binding,
    )
    cases.append(
        (
            "plan:media_facts_sha256",
            fixture_request(media_bundle),
            media_bundle,
            "cross-binding",
        )
    )

    other_transcript = transcript("coordinates-other-transcript")
    other_transcript_binding = binding(
        media_facts,
        other_transcript,
        label="coordinates-transcript",
    )
    plan_with_old_transcript = plan(
        operation_id,
        media_facts,
        transcript_facts,
        other_transcript_binding,
    )
    transcript_bundle: Bundle = (
        plan_with_old_transcript,
        media_facts,
        other_transcript,
        other_transcript_binding,
    )
    cases.append(
        (
            "plan:transcript_facts_sha256",
            fixture_request(transcript_bundle),
            transcript_bundle,
            "cross-binding",
        )
    )

    alternate_receipt_binding = binding(
        media_facts,
        transcript_facts,
        label="coordinates-alternate-receipt",
    )
    plan_with_old_binding_receipt = plan(
        operation_id,
        media_facts,
        transcript_facts,
        base_binding,
    )
    binding_receipt_bundle: Bundle = (
        plan_with_old_binding_receipt,
        media_facts,
        transcript_facts,
        alternate_receipt_binding,
    )
    cases.append(
        (
            "plan:transcript_binding_receipt_sha256",
            fixture_request(binding_receipt_bundle),
            binding_receipt_bundle,
            "cross-binding",
        )
    )

    for _coordinate, request, supplied_bundle, error_match in cases:
        runtime = fixture_runtime()
        with pytest.raises(ValueError, match=error_match):
            execute(runtime, request, supplied_bundle)
        assert runtime.fixture_head_sha256 == INITIAL_HEAD
        assert runtime.terminal_append_count == 0
        assert runtime.operation_count == 0


def test_stale_head_burns_operation_without_append_then_fresh_operation_commits() -> None:
    stale_bundle = make_bundle(operation_id="reference.prepare.stale")
    runtime = fixture_runtime()
    stale_request = fixture_request(
        stale_bundle,
        expected_fixture_head_sha256=digest("stale-head"),
    )
    with pytest.raises(ValueError, match="head conflict"):
        execute(runtime, stale_request, stale_bundle)
    assert runtime.fixture_head_sha256 == INITIAL_HEAD
    assert runtime.terminal_append_count == 0
    assert runtime.operation_count == 1

    with pytest.raises(ValueError, match="non-replayable"):
        execute(runtime, stale_request, stale_bundle)
    assert runtime.fixture_head_sha256 == INITIAL_HEAD
    assert runtime.terminal_append_count == 0
    assert runtime.operation_count == 1

    fresh_bundle = make_bundle(
        operation_id="reference.prepare.fresh",
        label="fresh",
    )
    fresh = execute(
        runtime,
        fixture_request(fresh_bundle),
        fresh_bundle,
    )
    assert fresh.outcome is (
        PreparationFixtureOutcome.PREPARED_SIMULATION_FIXTURE
    )
    assert runtime.fixture_head_sha256 != INITIAL_HEAD
    assert runtime.terminal_append_count == 1
    assert runtime.operation_count == 2


def test_fixture_domain_cross_binds_request_trace_head_and_all_identities() -> None:
    bundle_value = make_bundle()
    first_runtime = fixture_runtime(fixture_domain_sha256=FIXTURE_DOMAIN)
    second_runtime = fixture_runtime(
        fixture_domain_sha256=OTHER_FIXTURE_DOMAIN
    )
    first_request = fixture_request(
        bundle_value,
        fixture_domain_sha256=FIXTURE_DOMAIN,
    )
    second_request = fixture_request(
        bundle_value,
        fixture_domain_sha256=OTHER_FIXTURE_DOMAIN,
    )
    first = execute(
        first_runtime,
        first_request,
        bundle_value,
    ).fixture_trace()
    second = execute(
        second_runtime,
        second_request,
        bundle_value,
    ).fixture_trace()

    assert first_request.to_dict()["request_sha256"] != (
        second_request.to_dict()["request_sha256"]
    )
    assert first["simulated_trace_sha256"] != second[
        "simulated_trace_sha256"
    ]
    assert first["result_fixture_head_sha256"] != second[
        "result_fixture_head_sha256"
    ]
    identity_fields = {
        "simulated_reservation_identity_sha256",
        "simulated_intended_audio_identity_sha256",
        "simulated_intended_transcript_identity_sha256",
        "simulated_pair_ledger_identity_sha256",
    }
    assert {first[name] for name in identity_fields}.isdisjoint(
        {second[name] for name in identity_fields}
    )

    wrong_runtime = fixture_runtime(
        fixture_domain_sha256=FIXTURE_DOMAIN
    )
    with pytest.raises(ValueError, match="different fixture domain"):
        execute(wrong_runtime, second_request, bundle_value)
    assert wrong_runtime.fixture_head_sha256 == INITIAL_HEAD
    assert wrong_runtime.operation_count == 0
    assert wrong_runtime.terminal_append_count == 0


def test_synthetic_identities_bind_exact_role_and_request_preimage() -> None:
    identity_labels = {
        "simulated_reservation_identity_sha256": "RESERVATION",
        "simulated_intended_audio_identity_sha256": "REFERENCE_AUDIO",
        "simulated_intended_transcript_identity_sha256": (
            "REFERENCE_TRANSCRIPT_UTF8"
        ),
        "simulated_pair_ledger_identity_sha256": "PAIR_LEDGER",
    }
    first_bundle = make_bundle(
        operation_id="reference.identity.first",
        label="identity-first",
    )
    first_request = fixture_request(first_bundle)
    first_trace = execute(
        fixture_runtime(fixture_domain_sha256=FIXTURE_DOMAIN),
        first_request,
        first_bundle,
    ).fixture_trace()
    first_request_sha256 = first_request.to_dict()["request_sha256"]

    for field_name, label in identity_labels.items():
        assert first_trace[field_name] == sha256_bytes(
            IDENTITY_HASH_DOMAIN
            + label.encode("ascii")
            + b"\0"
            + canonical_json_bytes(
                {
                    "fixture_domain_sha256": FIXTURE_DOMAIN,
                    "request_sha256": first_request_sha256,
                }
            )
        )

    second_bundle = make_bundle(
        operation_id="reference.identity.second",
        label="identity-second",
    )
    second_request = fixture_request(second_bundle)
    second_trace = execute(
        fixture_runtime(fixture_domain_sha256=FIXTURE_DOMAIN),
        second_request,
        second_bundle,
    ).fixture_trace()
    assert first_request_sha256 != second_request.to_dict()["request_sha256"]
    for field_name in identity_labels:
        assert first_trace[field_name] != second_trace[field_name]


@pytest.mark.parametrize("same_request", [False, True])
def test_concurrent_first_writers_have_exactly_one_terminal_append(
    same_request: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_lock = _ContentionProbeLock()
    monkeypatch.setattr(windows_fixture_module, "Lock", lambda: probe_lock)
    runtime = fixture_runtime()
    first_bundle = make_bundle(
        operation_id="reference.concurrent.first",
        label="first",
    )
    first_request = fixture_request(first_bundle)
    if same_request:
        second_bundle = first_bundle
        second_request = first_request
    else:
        second_bundle = make_bundle(
            operation_id="reference.concurrent.second",
            label="second",
        )
        second_request = fixture_request(second_bundle)

    def invoke(
        item: tuple[WindowsPreparationTraceFixtureRequest, Bundle],
    ) -> tuple[str, object]:
        request, bundle_value = item
        try:
            return "result", execute(runtime, request, bundle_value)
        except Exception as exc:  # exact race winner is nondeterministic
            return "error", exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                invoke,
                (
                    (first_request, first_bundle),
                    (second_request, second_bundle),
                ),
            )
        )

    results = [value for kind, value in outcomes if kind == "result"]
    errors = [value for kind, value in outcomes if kind == "error"]
    assert probe_lock.contention_observed is True
    assert probe_lock.entry_attempts == 2
    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(results[0], WindowsPreparationTraceFixtureResult)
    assert isinstance(errors[0], RuntimeError)
    assert runtime.terminal_append_count == 1
    assert runtime.operation_count == 1
    assert runtime.fixture_head_sha256 != INITIAL_HEAD


def test_nominal_objects_and_atomic_internals_reject_forgery_copy_pickle_and_subclass() -> None:
    bundle_value = make_bundle()
    request = fixture_request(bundle_value)
    result = execute(fixture_runtime(), request, bundle_value)
    runtime = fixture_runtime()

    with pytest.raises(TypeError):
        WindowsPreparationTraceFixtureRequest({})
    with pytest.raises(TypeError):
        WindowsPreparationTraceFixtureResult({}, {})
    with pytest.raises(TypeError, match="atomic runtime"):
        WindowsPreparationTraceFixtureResult._from_runtime(
            trace={},
            outcome=PreparationFixtureOutcome.PREPARED_SIMULATION_FIXTURE,
            underlying_outcome=(
                PreparationFixtureOutcome.PREPARED_SIMULATION_FIXTURE
            ),
            delivery_fault=PreparationDeliveryFault.NONE,
            delivery_state="DELIVERED_SIMULATION",
            terminal_trace_disclosed=True,
            readback_at=NOW,
        )

    for value in (request, result, runtime):
        with pytest.raises(TypeError):
            copy.copy(value)
        with pytest.raises(TypeError):
            copy.deepcopy(value)
        with pytest.raises(TypeError):
            pickle.dumps(value)

    with pytest.raises(TypeError):
        class RequestChild(WindowsPreparationTraceFixtureRequest):
            pass

    with pytest.raises(TypeError):
        class ResultChild(WindowsPreparationTraceFixtureResult):
            pass

    with pytest.raises(TypeError):
        class RuntimeChild(WindowsPreparationTraceFixtureRuntime):
            pass

    prepare_internal = getattr(
        runtime,
        "_WindowsPreparationTraceFixtureRuntime__simulate_prepare_locked",
    )
    reconcile_internal = getattr(
        runtime,
        "_WindowsPreparationTraceFixtureRuntime__simulate_reconcile_prepare_unknown_locked",
    )
    with pytest.raises(RuntimeError, match="atomic public seam"):
        prepare_internal(request, *bundle_value)
    with pytest.raises(RuntimeError, match="atomic public seam"):
        reconcile_internal(request, *bundle_value)
    with pytest.raises(RuntimeError, match="atomic runtime"):
        runtime._build_trace_locked(
            request_value={},
            plan_value={},
            media_value={},
            transcript_value={},
            binding_value={},
        )
    assert runtime.fixture_head_sha256 == INITIAL_HEAD
    assert runtime.terminal_append_count == 0
    assert runtime.operation_count == 0


def test_result_and_public_values_have_no_body_path_secret_or_private_capability() -> None:
    bundle_value = make_bundle()
    runtime = fixture_runtime()
    request = fixture_request(bundle_value)
    result = execute(runtime, request, bundle_value)
    values = (
        request.to_dict(),
        result.fixture_trace(),
        result.fixture_receipt(),
    )
    forbidden_keys = {
        "audio_body",
        "transcript_body",
        "private_audio_body_base64",
        "plaintext",
        "ciphertext",
        "raw_key",
        "wrapped_key",
        "host_path",
        "absolute_path",
        "private_capability",
    }

    def strings(value: Any) -> list[str]:
        if isinstance(value, Mapping):
            result: list[str] = []
            for key, item in value.items():
                assert key not in forbidden_keys
                result.extend(strings(item))
            return result
        if isinstance(value, (list, tuple)):
            result = []
            for item in value:
                result.extend(strings(item))
            return result
        return [value] if isinstance(value, str) else []

    for value in values:
        for text in strings(value):
            assert not text.startswith(("/", "\\\\", "file://"))
            assert not (
                len(text) >= 3
                and text[0].isalpha()
                and text[1:3] in {":\\", ":/"}
            )


def test_runtime_constructor_rejects_wrong_scope_digest_and_time_order() -> None:
    valid = {
        "expected_consumer": EXPECTED_CONSUMER,
        "fixture_scope": FIXTURE_SCOPE,
        "fixture_domain_sha256": FIXTURE_DOMAIN,
        "initial_fixture_head_sha256": INITIAL_HEAD,
        "readback_at": NOW,
        "reconciliation_readback_at": RECONCILIATION_NOW,
    }
    cases = [
        {"expected_consumer": "TASK-075"},
        {"fixture_scope": "PRODUCT_RUNTIME"},
        {"fixture_domain_sha256": "not-a-digest"},
        {"initial_fixture_head_sha256": "not-a-digest"},
        {
            "readback_at": RECONCILIATION_NOW,
            "reconciliation_readback_at": NOW,
        },
    ]
    for changes in cases:
        with pytest.raises(ValueError):
            WindowsPreparationTraceFixtureRuntime(
                **{**valid, **changes},
            )
