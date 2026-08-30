from __future__ import annotations

import json

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    ProviderFamily,
    SelectionMode,
)
from ai_video_production.local_audio_model_inventory import (
    AudioModelPurpose,
    AutomationReadiness,
    InstalledState,
    InventoryCurrentness,
    InventorySource,
    LocalAudioModelObservation,
    LocalFreeLicenseState,
    RuntimeReadiness,
    apply_selectable_local_audio_routes,
    availability_from_local_audio_inventory,
    compile_local_audio_model_inventory,
    execution_ports_from_local_audio_inventory,
    project_public_voice_profile_models,
)
from ai_video_production.voice_profile_revision import (
    ArtifactAdmissionState,
    CapabilityProbeState,
    ConsentReference,
    ConsentState,
    LicenseReference,
    LocalVoiceCapabilityDescription,
    ModelLicenseClass,
    VoiceProfileRevision,
)
from ai_video_production.voice_profile_store import VoiceProfileRevisionHistory


SHA = "sha256:" + "1" * 64


def _observation(
    *,
    candidate_id: str = "audacity-musicgen-small-int8-stereo",
    purpose: AudioModelPurpose = AudioModelPurpose.MUSIC,
    workload: AiWorkload | None = AiWorkload.MUSIC,
    route_id: str | None = "audacity-musicgen-small-int8-stereo",
    model_id: str = "musicgen-small-int8-stereo",
    installed: InstalledState = InstalledState.INSTALLED,
    runtime: RuntimeReadiness = RuntimeReadiness.READY,
    currentness: InventoryCurrentness = InventoryCurrentness.CURRENT,
    license_state: LocalFreeLicenseState = LocalFreeLicenseState.CONFIRMED,
    automation: AutomationReadiness = AutomationReadiness.SCRIPTABLE,
    runtime_instance_id: str | None = "audacity-openvino-runtime",
    execution_port_id: str | None = "task013-audacity-musicgen-port",
) -> LocalAudioModelObservation:
    return LocalAudioModelObservation(
        candidate_id=candidate_id,
        purpose=purpose,
        workload=workload,
        provider_family=ProviderFamily.AUDACITY_OPENVINO,
        provider_id="audacity-openvino",
        model_id=model_id,
        route_id=route_id,
        installed_state=installed,
        runtime_readiness=runtime,
        currentness=currentness,
        license_state=license_state,
        automation_readiness=automation,
        source=InventorySource.FRESH_RUNTIME_PROBE,
        runtime_instance_id=runtime_instance_id,
        execution_port_id=execution_port_id,
        evidence_sha256=SHA,
    )


def _profile() -> AiConnectionProfile:
    return AiConnectionProfile(
        "local-audio-test",
        "1.0.0",
        SelectionMode.OFFLINE_ONLY,
        (),
        {
            AiWorkload.PLANNING: SelectionMode.DISABLED,
            AiWorkload.IMAGE: SelectionMode.DISABLED,
            AiWorkload.VIDEO: SelectionMode.DISABLED,
            AiWorkload.AUDIO: SelectionMode.OFFLINE_ONLY,
            AiWorkload.MUSIC: SelectionMode.OFFLINE_ONLY,
        },
    )


def test_musicgen_help_visibility_is_not_execution_readiness() -> None:
    observation = _observation(
        currentness=InventoryCurrentness.STALE,
        license_state=LocalFreeLicenseState.UNKNOWN,
        automation=AutomationReadiness.DISPLAY_ONLY,
        execution_port_id=None,
    )
    inventory = compile_local_audio_model_inventory((observation,))
    candidate = inventory.candidates[0]

    assert candidate.selectable is False
    assert candidate.disabled_reasons == (
        "STALE_INVENTORY",
        "LICENSE_NOT_CONFIRMED",
        "AUTOMATION_API_NOT_SCRIPTABLE",
    )
    assert apply_selectable_local_audio_routes(_profile(), inventory).routes == ()
    assert availability_from_local_audio_inventory(inventory).available_route_ids == frozenset()
    assert execution_ports_from_local_audio_inventory(inventory) == {}


def test_sfx_and_music_have_separate_route_capability_and_port_identity() -> None:
    music = _observation()
    sfx = _observation(
        candidate_id="local-sfx-model",
        purpose=AudioModelPurpose.SFX,
        workload=AiWorkload.AUDIO,
        route_id="local-sfx-route",
        model_id="local-sfx-v1",
        execution_port_id="task013-local-sfx-port",
    )
    inventory = compile_local_audio_model_inventory((music, sfx))
    profile = apply_selectable_local_audio_routes(_profile(), inventory)

    identities = {
        (route.workload.value, route.capabilities[0], route.route_id, route.model_id)
        for route in profile.routes
    }
    assert identities == {
        ("AUDIO", "SFX", "local-sfx-route", "local-sfx-v1"),
        ("MUSIC", "MUSIC_GENERATION", "audacity-musicgen-small-int8-stereo", "musicgen-small-int8-stereo"),
    }
    assert availability_from_local_audio_inventory(inventory).available_route_ids == {
        "local-sfx-route",
        "audacity-musicgen-small-int8-stereo",
    }
    assert execution_ports_from_local_audio_inventory(inventory) == {
        "local-sfx-route": "task013-local-sfx-port",
        "audacity-musicgen-small-int8-stereo": "task013-audacity-musicgen-port",
    }
    assert all(route.credential_ref is None and route.endpoint_ref is None and route.settings == {} for route in profile.routes)


def test_audio_availability_preserves_existing_routes_and_credentials() -> None:
    inventory = compile_local_audio_model_inventory((_observation(),))
    base = ConnectionAvailability(
        frozenset({"local-planning-route"}),
        frozenset({"existing-credential-ref"}),
    )

    availability = availability_from_local_audio_inventory(inventory, base)

    assert availability.available_route_ids == {
        "local-planning-route",
        "audacity-musicgen-small-int8-stereo",
    }
    assert availability.available_credential_refs == {"existing-credential-ref"}


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"installed": InstalledState.NOT_INSTALLED}, "MODEL_NOT_INSTALLED"),
        ({"runtime": RuntimeReadiness.STOPPED, "runtime_instance_id": None}, "RUNTIME_STOPPED"),
        ({"currentness": InventoryCurrentness.STALE}, "STALE_INVENTORY"),
        ({"license_state": LocalFreeLicenseState.UNKNOWN}, "LICENSE_NOT_CONFIRMED"),
        ({"automation": AutomationReadiness.UNSUPPORTED, "execution_port_id": None}, "UNSUPPORTED_CAPABILITY"),
        ({"execution_port_id": None}, "EXECUTION_PORT_NOT_BOUND"),
    ],
)
def test_unavailable_state_is_explicit(changes: dict[str, object], reason: str) -> None:
    candidate = compile_local_audio_model_inventory((_observation(**changes),)).candidates[0]
    assert candidate.selectable is False
    assert reason in candidate.disabled_reasons


def test_wrong_media_workload_is_rejected() -> None:
    with pytest.raises(ValueError, match="media identity mismatch"):
        _observation(purpose=AudioModelPurpose.SFX, workload=AiWorkload.MUSIC)


def test_duplicate_route_and_multiple_runtime_instances_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate audio route_id"):
        compile_local_audio_model_inventory((
            _observation(candidate_id="music-a"),
            _observation(candidate_id="music-b"),
        ))
    with pytest.raises(ValueError, match="multiple ready runtime instances"):
        compile_local_audio_model_inventory((
            _observation(candidate_id="music-a", route_id="music-a", runtime_instance_id="audacity-a"),
            _observation(candidate_id="music-b", route_id="music-b", runtime_instance_id="audacity-b"),
        ))


def test_private_path_and_body_surface_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="private or unsafe path"):
        _observation(model_id=r"C:\\private\\musicgen")
    document = compile_local_audio_model_inventory((_observation(),)).to_public_dict()
    serialized = json.dumps(document, sort_keys=True)
    assert "C:\\" not in serialized
    assert "media_body" in serialized
    assert document["runtime_start_requested"] is False
    candidate = document["candidates"][0]
    assert candidate["media_body_persisted"] is False
    assert candidate["private_path_persisted"] is False
    assert candidate["credential_required"] is False
    assert candidate["cloud_fallback_allowed"] is False
    assert candidate["automatic_download_allowed"] is False


def test_candidate_hash_binds_result_identity() -> None:
    left = compile_local_audio_model_inventory((_observation(),)).to_public_dict()["candidates"][0]
    right = compile_local_audio_model_inventory((_observation(model_id="musicgen-small-fp16-stereo"),)).to_public_dict()["candidates"][0]
    assert left["candidate_sha256"] != right["candidate_sha256"]


def test_narration_profile_is_public_safe_and_never_added_as_sfx_music_route() -> None:
    consent = ConsentReference("owner-subject", "narration", ("NARRATION",), ConsentState.ACTIVE, True, "consent-evidence", SHA)
    license_row = LicenseReference(
        "qwen3-tts-artifact",
        "Qwen3-TTS-12Hz-0.6B-Base",
        SHA,
        "qwen3-tts-runtime",
        ModelLicenseClass.COMMERCIAL_ALLOWED,
        ArtifactAdmissionState.APPROVED,
        True,
        "license-evidence",
        SHA,
    )
    capability = LocalVoiceCapabilityDescription(
        "QWEN3_TTS",
        "qwen3-tts-runtime",
        ("ja-JP",),
        ("NARRATION",),
        True,
        CapabilityProbeState.VERIFIED,
        SHA,
    )
    revision = VoiceProfileRevision("owner-voice", SHA, 1, None, "2026-08-30T00:00:00Z", consent, license_row, capability)
    history = VoiceProfileRevisionHistory("owner-voice", (revision,))
    narration = _observation(
        candidate_id="qwen3-tts-local",
        purpose=AudioModelPurpose.NARRATION,
        workload=None,
        route_id=None,
        model_id="Qwen3-TTS-12Hz-0.6B-Base",
        runtime_instance_id="qwen3-tts-runtime",
        execution_port_id="task014-qwen3-tts-port",
    )
    inventory = compile_local_audio_model_inventory((narration,))
    public = project_public_voice_profile_models((history,), inventory)[0]

    assert public["profile_selectable"] is True
    assert public["generation_ready"] is True
    assert public["disabled_reasons"] == []
    assert apply_selectable_local_audio_routes(_profile(), inventory).routes == ()
    assert public["execution_authorized"] is False
    assert public["host_path_persisted"] is False
    assert public["media_body_persisted"] is False


def test_historical_qwen_contract_stays_disabled_until_current_runtime_closure() -> None:
    observation = LocalAudioModelObservation(
        candidate_id="qwen3-tts-pinned-contract",
        purpose=AudioModelPurpose.NARRATION,
        workload=None,
        provider_family=ProviderFamily.LOCAL_OPEN_SOURCE,
        provider_id="qwen3-tts",
        model_id="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        route_id=None,
        installed_state=InstalledState.UNKNOWN,
        runtime_readiness=RuntimeReadiness.UNKNOWN,
        currentness=InventoryCurrentness.STALE,
        license_state=LocalFreeLicenseState.UNKNOWN,
        automation_readiness=AutomationReadiness.UNSUPPORTED,
        source=InventorySource.PINNED_CONTRACT,
        evidence_sha256=SHA,
    )
    candidate = compile_local_audio_model_inventory((observation,)).candidates[0]
    assert candidate.selectable is False
    assert candidate.disabled_reasons == (
        "STALE_INVENTORY",
        "MODEL_INSTALLATION_UNKNOWN",
        "RUNTIME_READINESS_UNKNOWN",
        "LICENSE_NOT_CONFIRMED",
        "UNSUPPORTED_CAPABILITY",
    )
