"""Pure, provider-neutral inventory for selectable local audio models.

The module never starts a runtime, downloads a model, reads media, or stores a
host path.  Callers provide bounded read-only observations and receive a public
snapshot plus the exact routes/ports that are safe to expose to TASK-036.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable, Mapping

from .ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProviderFamily,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_profile_revision import (
    ArtifactAdmissionState,
    CapabilityProbeState,
    ConsentState,
    ModelLicenseClass,
)
from .voice_profile_store import VoiceProfileRevisionHistory


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:-]{0,127}$")
_LOCAL_FAMILIES = {ProviderFamily.AUDACITY_OPENVINO, ProviderFamily.LOCAL_OPEN_SOURCE}


class AudioModelPurpose(str, Enum):
    SFX = "SFX"
    MUSIC = "MUSIC"
    NARRATION = "NARRATION"


class InstalledState(str, Enum):
    INSTALLED = "INSTALLED"
    NOT_INSTALLED = "NOT_INSTALLED"
    UNKNOWN = "UNKNOWN"


class RuntimeReadiness(str, Enum):
    READY = "READY"
    STOPPED = "STOPPED"
    UNKNOWN = "UNKNOWN"


class InventoryCurrentness(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class LocalFreeLicenseState(str, Enum):
    CONFIRMED = "CONFIRMED"
    UNKNOWN = "UNKNOWN"


class AutomationReadiness(str, Enum):
    SCRIPTABLE = "SCRIPTABLE"
    DISPLAY_ONLY = "DISPLAY_ONLY"
    UNSUPPORTED = "UNSUPPORTED"


class InventorySource(str, Enum):
    FRESH_RUNTIME_PROBE = "FRESH_RUNTIME_PROBE"
    HISTORICAL_EVIDENCE = "HISTORICAL_EVIDENCE"
    PINNED_CONTRACT = "PINNED_CONTRACT"


_PURPOSE_CONTRACT = {
    AudioModelPurpose.SFX: (AiWorkload.AUDIO, "SFX"),
    AudioModelPurpose.MUSIC: (AiWorkload.MUSIC, "MUSIC_GENERATION"),
    AudioModelPurpose.NARRATION: (None, "NARRATION"),
}


def _public_identifier(value: str, name: str, pattern: re.Pattern[str] = _SAFE_ID) -> str:
    if isinstance(value, str) and (
        "\\" in value or "://" in value or value.startswith("/") or ".." in value.split("/")
    ):
        raise ValueError(f"{name} contains a private or unsafe path")
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


@dataclass(frozen=True, slots=True)
class AudacityMusicGenerationCapabilityAudit:
    runtime_readiness: RuntimeReadiness
    currentness: InventoryCurrentness
    command_available: bool
    command_id: str | None
    disabled_reasons: tuple[str, ...]
    evidence_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_readiness, RuntimeReadiness):
            raise ValueError("runtime_readiness is invalid")
        if not isinstance(self.currentness, InventoryCurrentness):
            raise ValueError("currentness is invalid")
        if type(self.command_available) is not bool:
            raise ValueError("command_available must be a boolean")
        if self.command_available and self.command_id != "OpenvinoMusicGeneration":
            raise ValueError("available MusicGen command identity is invalid")
        if not self.command_available and self.command_id is not None:
            raise ValueError("unavailable MusicGen command must not expose an identity")
        if not self.disabled_reasons or len(self.disabled_reasons) != len(set(self.disabled_reasons)):
            raise ValueError("disabled_reasons must be non-empty and unique")
        validate_sha256(self.evidence_sha256, field_name="evidence_sha256")

    def to_public_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "purpose": AudioModelPurpose.MUSIC.value,
            "workload": AiWorkload.MUSIC.value,
            "capability": "MUSIC_GENERATION",
            "provider_family": ProviderFamily.AUDACITY_OPENVINO.value,
            "provider_id": "audacity-openvino",
            "runtime_readiness": self.runtime_readiness.value,
            "currentness": self.currentness.value,
            "command_available": self.command_available,
            "command_id": self.command_id,
            "model_inventory_available": False,
            "installed_model_count": None,
            "candidate_count": 0,
            "route_id": None,
            "model_id": None,
            "execution_port_id": None,
            "selectable": False,
            "disabled_reasons": list(self.disabled_reasons),
            "evidence_sha256": self.evidence_sha256,
            "credential_required": False,
            "cloud_fallback_allowed": False,
            "automatic_download_allowed": False,
            "runtime_start_requested": False,
            "private_path_persisted": False,
            "media_body_persisted": False,
        }
        body["audit_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def audit_audacity_music_generation_capability(
    report: Mapping[str, object],
    *,
    evidence_sha256: str,
    currentness: InventoryCurrentness = InventoryCurrentness.CURRENT,
) -> AudacityMusicGenerationCapabilityAudit:
    """Translate bounded Help evidence without inventing an installed model."""
    if not isinstance(report, Mapping):
        raise ValueError("Audacity capability report must be a mapping")
    connected = report.get("connected")
    if type(connected) is not bool:
        raise ValueError("Audacity capability connected state must be a boolean")
    features = report.get("features")
    if not isinstance(features, Mapping):
        raise ValueError("Audacity capability features must be a mapping")
    music = features.get("MUSIC_GENERATION")
    if not isinstance(music, Mapping):
        raise ValueError("Audacity MusicGen capability row is missing")
    available = music.get("available")
    if type(available) is not bool:
        raise ValueError("Audacity MusicGen availability must be a boolean")
    command_id = music.get("command_id")
    if command_id is not None and not isinstance(command_id, str):
        raise ValueError("Audacity MusicGen command_id must be text or null")
    if available and command_id != "OpenvinoMusicGeneration":
        raise ValueError("available MusicGen command identity is invalid")
    if not available and command_id is not None:
        raise ValueError("unavailable MusicGen command must not expose an identity")
    if available and not connected:
        raise ValueError("disconnected Audacity runtime cannot expose an available MusicGen command")
    if available and not isinstance(music.get("descriptor"), Mapping):
        raise ValueError("available MusicGen command requires a descriptor mapping")

    reasons: list[str] = []
    if currentness is InventoryCurrentness.STALE:
        reasons.append("STALE_INVENTORY")
    elif currentness is InventoryCurrentness.UNKNOWN:
        reasons.append("INVENTORY_CURRENTNESS_UNKNOWN")
    if not connected:
        reasons.append("RUNTIME_STOPPED")
    if not available:
        reasons.append("MUSIC_GENERATION_COMMAND_UNAVAILABLE")
    reasons.extend(("MODEL_INVENTORY_UNAVAILABLE", "AUTOMATION_API_NOT_SCRIPTABLE"))
    return AudacityMusicGenerationCapabilityAudit(
        runtime_readiness=RuntimeReadiness.READY if connected else RuntimeReadiness.STOPPED,
        currentness=currentness,
        command_available=available,
        command_id=command_id,
        disabled_reasons=tuple(reasons),
        evidence_sha256=evidence_sha256,
    )


@dataclass(frozen=True, slots=True)
class LocalAudioModelObservation:
    candidate_id: str
    purpose: AudioModelPurpose
    workload: AiWorkload | None
    provider_family: ProviderFamily
    provider_id: str
    model_id: str
    route_id: str | None
    installed_state: InstalledState
    runtime_readiness: RuntimeReadiness
    currentness: InventoryCurrentness
    license_state: LocalFreeLicenseState
    automation_readiness: AutomationReadiness
    source: InventorySource
    runtime_instance_id: str | None = None
    execution_port_id: str | None = None
    evidence_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.purpose, AudioModelPurpose):
            raise ValueError("purpose is invalid")
        expected_workload, _ = _PURPOSE_CONTRACT[self.purpose]
        if self.workload is not expected_workload:
            raise ValueError("purpose/workload media identity mismatch")
        if not isinstance(self.provider_family, ProviderFamily) or self.provider_family not in _LOCAL_FAMILIES:
            raise ValueError("provider_family must be a supported local provider")
        for value, name in ((self.candidate_id, "candidate_id"), (self.provider_id, "provider_id")):
            _public_identifier(value, name)
        _public_identifier(self.model_id, "model_id", _MODEL_ID)
        if self.route_id is not None:
            _public_identifier(self.route_id, "route_id")
        if self.purpose is AudioModelPurpose.NARRATION and self.route_id is not None:
            raise ValueError("narration profiles must not become SFX/MUSIC routes")
        if self.purpose is not AudioModelPurpose.NARRATION and self.route_id is None:
            raise ValueError("SFX/MUSIC observations require a route_id")
        for value, enum_type, name in (
            (self.installed_state, InstalledState, "installed_state"),
            (self.runtime_readiness, RuntimeReadiness, "runtime_readiness"),
            (self.currentness, InventoryCurrentness, "currentness"),
            (self.license_state, LocalFreeLicenseState, "license_state"),
            (self.automation_readiness, AutomationReadiness, "automation_readiness"),
            (self.source, InventorySource, "source"),
        ):
            if not isinstance(value, enum_type):
                raise ValueError(f"{name} is invalid")
        if self.runtime_instance_id is not None:
            _public_identifier(self.runtime_instance_id, "runtime_instance_id")
        if self.runtime_readiness is RuntimeReadiness.READY and self.runtime_instance_id is None:
            raise ValueError("READY runtime requires an exact runtime_instance_id")
        if self.execution_port_id is not None:
            _public_identifier(self.execution_port_id, "execution_port_id")
        if self.automation_readiness is not AutomationReadiness.SCRIPTABLE and self.execution_port_id is not None:
            raise ValueError("a non-scriptable candidate cannot bind an execution port")
        if self.evidence_sha256 is not None:
            validate_sha256(self.evidence_sha256, field_name="evidence_sha256")

    @property
    def capability(self) -> str:
        return _PURPOSE_CONTRACT[self.purpose][1]


def _disabled_reasons(observation: LocalAudioModelObservation) -> tuple[str, ...]:
    reasons: list[str] = []
    if observation.currentness is InventoryCurrentness.STALE:
        reasons.append("STALE_INVENTORY")
    elif observation.currentness is InventoryCurrentness.UNKNOWN:
        reasons.append("INVENTORY_CURRENTNESS_UNKNOWN")
    if observation.installed_state is InstalledState.NOT_INSTALLED:
        reasons.append("MODEL_NOT_INSTALLED")
    elif observation.installed_state is InstalledState.UNKNOWN:
        reasons.append("MODEL_INSTALLATION_UNKNOWN")
    if observation.runtime_readiness is RuntimeReadiness.STOPPED:
        reasons.append("RUNTIME_STOPPED")
    elif observation.runtime_readiness is RuntimeReadiness.UNKNOWN:
        reasons.append("RUNTIME_READINESS_UNKNOWN")
    if observation.license_state is LocalFreeLicenseState.UNKNOWN:
        reasons.append("LICENSE_NOT_CONFIRMED")
    if observation.automation_readiness is AutomationReadiness.DISPLAY_ONLY:
        reasons.append("AUTOMATION_API_NOT_SCRIPTABLE")
    elif observation.automation_readiness is AutomationReadiness.UNSUPPORTED:
        reasons.append("UNSUPPORTED_CAPABILITY")
    if observation.automation_readiness is AutomationReadiness.SCRIPTABLE and observation.execution_port_id is None:
        reasons.append("EXECUTION_PORT_NOT_BOUND")
    if observation.evidence_sha256 is None:
        reasons.append("EVIDENCE_NOT_BOUND")
    return tuple(reasons)


@dataclass(frozen=True, slots=True)
class LocalAudioModelCandidate:
    observation: LocalAudioModelObservation
    disabled_reasons: tuple[str, ...]

    @property
    def selectable(self) -> bool:
        return not self.disabled_reasons

    def _body(self) -> dict[str, object]:
        row = self.observation
        return {
            "candidate_id": row.candidate_id,
            "purpose": row.purpose.value,
            "workload": row.workload.value if row.workload else None,
            "capability": row.capability,
            "provider_family": row.provider_family.value,
            "provider_id": row.provider_id,
            "model_id": row.model_id,
            "route_id": row.route_id,
            "cost_class": CostClass.LOCAL_FREE_AI.value,
            "installed_state": row.installed_state.value,
            "runtime_readiness": row.runtime_readiness.value,
            "currentness": row.currentness.value,
            "license_state": row.license_state.value,
            "automation_readiness": row.automation_readiness.value,
            "inventory_source": row.source.value,
            "runtime_instance_id": row.runtime_instance_id,
            "execution_port_id": row.execution_port_id,
            "evidence_sha256": row.evidence_sha256,
            "selectable": self.selectable,
            "disabled_reasons": list(self.disabled_reasons),
            "credential_required": False,
            "cloud_fallback_allowed": False,
            "automatic_download_allowed": False,
            "runtime_start_requested": False,
            "private_path_persisted": False,
            "media_body_persisted": False,
        }

    def to_public_dict(self) -> dict[str, object]:
        body = self._body()
        body["candidate_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class LocalAudioModelInventory:
    candidates: tuple[LocalAudioModelCandidate, ...]

    def to_public_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": "1.0.0",
            "task_owner": "TASK-013",
            "provider_neutral": True,
            "local_free_only": True,
            "cloud_fallback_allowed": False,
            "automatic_download_allowed": False,
            "runtime_start_requested": False,
            "candidates": [item.to_public_dict() for item in self.candidates],
        }
        body["inventory_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def compile_local_audio_model_inventory(
    observations: Iterable[LocalAudioModelObservation],
) -> LocalAudioModelInventory:
    rows = tuple(observations)
    candidate_ids = [item.candidate_id for item in rows]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("duplicate audio candidate_id")
    route_ids = [item.route_id for item in rows if item.route_id is not None]
    if len(route_ids) != len(set(route_ids)):
        raise ValueError("duplicate audio route_id")
    ready_instances: dict[ProviderFamily, str] = {}
    for item in rows:
        if item.runtime_readiness is not RuntimeReadiness.READY:
            continue
        prior = ready_instances.setdefault(item.provider_family, item.runtime_instance_id or "")
        if prior != item.runtime_instance_id:
            raise ValueError("multiple ready runtime instances for one provider family")
    candidates = tuple(
        LocalAudioModelCandidate(item, _disabled_reasons(item))
        for item in sorted(rows, key=lambda x: (x.purpose.value, x.candidate_id))
    )
    return LocalAudioModelInventory(candidates)


def verify_local_audio_inventory_public_snapshot(document: Mapping[str, object]) -> None:
    """Fail closed when a public candidate or inventory digest no longer matches."""
    if not isinstance(document, Mapping):
        raise ValueError("audio inventory snapshot must be a mapping")
    if document.get("schema_version") != "1.0.0":
        raise ValueError("audio inventory schema_version is unsupported")
    candidates = document.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("audio inventory candidates must be a list")
    candidate_ids: set[str] = set()
    route_ids: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("audio inventory candidate must be a mapping")
        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str):
            raise ValueError("audio inventory candidate_id is missing")
        if candidate_id in candidate_ids:
            raise ValueError("duplicate audio candidate_id in public snapshot")
        candidate_ids.add(candidate_id)
        route_id = candidate.get("route_id")
        if route_id is not None:
            if not isinstance(route_id, str):
                raise ValueError("audio inventory route_id must be text or null")
            if route_id in route_ids:
                raise ValueError("duplicate audio route_id in public snapshot")
            route_ids.add(route_id)
        candidate_sha256 = candidate.get("candidate_sha256")
        if not isinstance(candidate_sha256, str):
            raise ValueError("audio inventory candidate_sha256 is missing")
        validate_sha256(candidate_sha256, field_name="candidate_sha256")
        candidate_body = dict(candidate)
        candidate_body.pop("candidate_sha256", None)
        if sha256_bytes(canonical_json_bytes(candidate_body)) != candidate_sha256:
            raise ValueError("audio inventory candidate hash mismatch")

    inventory_sha256 = document.get("inventory_sha256")
    if not isinstance(inventory_sha256, str):
        raise ValueError("audio inventory inventory_sha256 is missing")
    validate_sha256(inventory_sha256, field_name="inventory_sha256")
    inventory_body = dict(document)
    inventory_body.pop("inventory_sha256", None)
    if sha256_bytes(canonical_json_bytes(inventory_body)) != inventory_sha256:
        raise ValueError("audio inventory hash mismatch")


def apply_selectable_local_audio_routes(
    profile: AiConnectionProfile,
    inventory: LocalAudioModelInventory,
) -> AiConnectionProfile:
    """Add only executable SFX/MUSIC routes; never rewrite an existing choice."""
    routes = list(profile.routes)
    existing = {item.route_id: item for item in routes}
    for candidate in inventory.candidates:
        row = candidate.observation
        if not candidate.selectable or row.purpose is AudioModelPurpose.NARRATION:
            continue
        assert row.route_id is not None and row.workload is not None and row.execution_port_id is not None
        proposed = ModelRoute(
            route_id=row.route_id,
            workload=row.workload,
            provider_family=row.provider_family,
            provider_id=row.provider_id,
            model_id=row.model_id,
            cost_class=CostClass.LOCAL_FREE_AI,
            capabilities=(row.capability,),
        )
        current = existing.get(proposed.route_id)
        if current is None:
            routes.append(proposed)
            existing[proposed.route_id] = proposed
            continue
        identity = (
            current.workload,
            current.provider_family,
            current.provider_id,
            current.model_id,
            current.cost_class,
            current.capabilities,
            current.credential_ref,
            current.endpoint_ref,
            current.settings,
        )
        expected = (
            proposed.workload,
            proposed.provider_family,
            proposed.provider_id,
            proposed.model_id,
            proposed.cost_class,
            proposed.capabilities,
            None,
            None,
            {},
        )
        if identity != expected:
            raise ValueError("existing route identity conflicts with current audio inventory")
    return AiConnectionProfile(
        profile.profile_id,
        profile.profile_version,
        profile.default_mode,
        tuple(routes),
        profile.workload_modes,
    )


def availability_from_local_audio_inventory(
    inventory: LocalAudioModelInventory,
    base: ConnectionAvailability | None = None,
) -> ConnectionAvailability:
    available_route_ids = set(base.available_route_ids if base is not None else ())
    available_route_ids.update(
        item.observation.route_id
        for item in inventory.candidates
        if item.selectable and item.observation.route_id is not None
    )
    return ConnectionAvailability(
        frozenset(available_route_ids),
        base.available_credential_refs if base is not None else frozenset(),
    )


def execution_ports_from_local_audio_inventory(
    inventory: LocalAudioModelInventory,
) -> dict[str, str]:
    return {
        item.observation.route_id: item.observation.execution_port_id
        for item in inventory.candidates
        if item.selectable
        and item.observation.route_id is not None
        and item.observation.execution_port_id is not None
    }


def project_public_voice_profile_models(
    histories: Iterable[VoiceProfileRevisionHistory],
    inventory: LocalAudioModelInventory,
) -> tuple[dict[str, object], ...]:
    """Project TASK-046 profiles without turning them into SFX/MUSIC routes."""
    narration = [item for item in inventory.candidates if item.observation.purpose is AudioModelPurpose.NARRATION]
    by_model: dict[str, LocalAudioModelCandidate] = {}
    for item in narration:
        model_id = item.observation.model_id
        if model_id in by_model:
            raise ValueError("duplicate narration model identity")
        by_model[model_id] = item
    result: list[dict[str, object]] = []
    seen_profiles: set[str] = set()
    for history in histories:
        if history.voice_profile_id in seen_profiles:
            raise ValueError("duplicate voice_profile_id")
        seen_profiles.add(history.voice_profile_id)
        revision = history.latest
        reasons: list[str] = []
        if revision.consent.state is not ConsentState.ACTIVE or not revision.consent.subject_verified:
            reasons.append("VOICE_CONSENT_NOT_ACTIVE")
        if (
            revision.license.license_class is not ModelLicenseClass.COMMERCIAL_ALLOWED
            or revision.license.artifact_state is not ArtifactAdmissionState.APPROVED
            or not revision.license.commercial_use_allowed
        ):
            reasons.append("VOICE_MODEL_LICENSE_OR_ARTIFACT_NOT_APPROVED")
        if not revision.capability.offline_only:
            reasons.append("VOICE_RUNTIME_NOT_OFFLINE_ONLY")
        if revision.capability.probe_state is not CapabilityProbeState.VERIFIED:
            reasons.append("VOICE_CAPABILITY_NOT_VERIFIED")
        runtime = by_model.get(revision.license.exact_model_id)
        if runtime is None:
            reasons.append("NARRATION_RUNTIME_NOT_INVENTORIED")
        else:
            reasons.extend(runtime.disabled_reasons)
        body: dict[str, object] = {
            "voice_profile_id": history.voice_profile_id,
            "voice_profile_revision": revision.revision,
            "voice_profile_revision_sha256": revision.voice_profile_revision_sha256,
            "model_artifact_id": revision.license.model_artifact_id,
            "exact_model_id": revision.license.exact_model_id,
            "runtime_id": revision.license.runtime_id,
            "supported_languages": list(revision.capability.supported_languages),
            "capabilities": list(revision.capability.capabilities),
            "installed_state": runtime.observation.installed_state.value if runtime else InstalledState.UNKNOWN.value,
            "runtime_readiness": runtime.observation.runtime_readiness.value if runtime else RuntimeReadiness.UNKNOWN.value,
            "currentness": runtime.observation.currentness.value if runtime else InventoryCurrentness.UNKNOWN.value,
            "profile_selectable": not reasons,
            "generation_ready": not reasons,
            "disabled_reasons": reasons,
            "execution_authorized": False,
            "private_provider_voice_id_persisted": False,
            "host_path_persisted": False,
            "media_body_persisted": False,
        }
        body["candidate_sha256"] = sha256_bytes(canonical_json_bytes(body))
        result.append(body)
    return tuple(sorted(result, key=lambda item: str(item["voice_profile_id"])))
