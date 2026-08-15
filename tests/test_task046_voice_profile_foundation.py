from __future__ import annotations

import importlib.resources as resources
import json
from pathlib import Path

import jsonschema
import pytest

from ai_video_production.errors import ProductError
from ai_video_production.owner_narration import VoiceProfile
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
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
from ai_video_production.voice_profile_store import VoiceProfileRevisionStore
from ai_video_production.voice_studio_application import (
    VoiceStudioPreflightService,
    VoiceStudioPreflightStatus,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def revision(
    number: int = 1,
    *,
    parent: str | None = None,
    ready: bool = True,
    canonical_narration_profile_sha256: str = SHA_C,
) -> VoiceProfileRevision:
    if ready:
        consent = ConsentReference(
            "OWNER-LOCAL-01",
            "Owner narration in owned commercial video projects",
            ("COMMERCIAL_OWNER_VIDEO",),
            ConsentState.ACTIVE,
            True,
            "CONSENT-EVIDENCE-01",
            SHA_A,
        )
        license_ref = LicenseReference(
            "MODEL-ARTIFACT-01",
            "exact-model-1.0",
            SHA_B,
            "LOCAL-RUNTIME-01",
            ModelLicenseClass.COMMERCIAL_ALLOWED,
            ArtifactAdmissionState.APPROVED,
            True,
            "LICENSE-EVIDENCE-01",
            SHA_C,
        )
        capability = LocalVoiceCapabilityDescription(
            "LOCAL-TTS",
            "LOCAL-TTS-ENGINE-01",
            ("ja-JP",),
            ("ZERO_SHOT_CLONE", "CHARACTER_TIMING"),
            True,
            CapabilityProbeState.VERIFIED,
            SHA_A,
        )
    else:
        consent = ConsentReference(
            "OWNER-LOCAL-01",
            "Unverified scope",
            ("PERSONAL_RESEARCH",),
            ConsentState.UNKNOWN,
            False,
        )
        license_ref = LicenseReference(
            "MODEL-ARTIFACT-01",
            "candidate-model",
            SHA_B,
            "LOCAL-RUNTIME-01",
            ModelLicenseClass.UNKNOWN,
            ArtifactAdmissionState.CATALOG_ONLY,
            False,
        )
        capability = LocalVoiceCapabilityDescription(
            "LOCAL-TTS",
            "LOCAL-TTS-ENGINE-01",
            ("en-US",),
            ("CATALOG_DESCRIPTION",),
            False,
        )
    return VoiceProfileRevision(
        "OWNER-VOICE-01",
        canonical_narration_profile_sha256,
        number,
        parent,
        f"2026-08-15T00:00:0{number}Z",
        consent,
        license_ref,
        capability,
    )


def _rewrite_store(path: Path, document: dict[str, object]) -> None:
    body = {key: value for key, value in document.items() if key != "store_sha256"}
    document["store_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_bytes(canonical_json_bytes(document) + b"\n")


def test_task014_voice_profile_remains_the_only_narration_identity_class() -> None:
    import ai_video_production.voice_profile_revision as metadata

    canonical = VoiceProfile(
        "OWNER-VOICE-01",
        "ELEVENLABS",
        "credential://owner/elevenlabs",
        "private-provider-voice-id",
        True,
        True,
        ("ja-JP",),
        ("eleven-multilingual-v2",),
        "OWNER-LOCAL-01",
        "Owner narration",
    )
    attached = revision(canonical_narration_profile_sha256=canonical.profile_digest)
    assert canonical.voice_profile_id == attached.voice_profile_id
    assert canonical.profile_digest == attached.canonical_narration_profile_sha256
    assert not hasattr(metadata, "VoiceProfile")


def test_schema_mirror_and_revision_validation() -> None:
    canonical = Path("schemas/voice-profile-revision.schema.json")
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "voice-profile-revision.schema.json"
    )
    assert packaged.read_bytes() == canonical.read_bytes()
    schema = json.loads(canonical.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(revision().to_private_dict())


def test_public_projection_is_deterministic_and_redacts_private_references() -> None:
    item = revision()
    assert item.to_public_dict() == item.to_public_dict()
    public_text = json.dumps(item.to_public_dict(), ensure_ascii=False, sort_keys=True)
    for secret in (
        "OWNER-LOCAL-01",
        "Owner narration in owned commercial video projects",
        "CONSENT-EVIDENCE-01",
        "LICENSE-EVIDENCE-01",
    ):
        assert secret not in public_text
    assert item.to_public_dict()["voice_profile_id"] == "OWNER-VOICE-01"
    assert item.to_public_dict()["execution_authorized"] is False


def test_project_local_create_append_restart_and_exact_revision_binding(tmp_path: Path) -> None:
    first = revision()
    VoiceProfileRevisionStore.create(tmp_path, first)
    loaded = VoiceProfileRevisionStore.load(tmp_path)
    second = revision(2, parent=loaded.latest.voice_profile_revision_sha256)
    VoiceProfileRevisionStore.append(
        tmp_path,
        second,
        expected_previous_store_sha256=loaded.store_sha256,
    )

    restarted = VoiceProfileRevisionStore.load(tmp_path)
    assert restarted.voice_profile_id == "OWNER-VOICE-01"
    assert tuple(item.revision for item in restarted.revisions) == (1, 2)
    assert restarted.latest.parent_revision_sha256 == first.voice_profile_revision_sha256
    assert VoiceProfileRevisionStore.path(tmp_path) == tmp_path.resolve() / ".bai-project" / "voice-profile-revisions.json"


def test_append_requires_exact_cas_and_preserves_identity(tmp_path: Path) -> None:
    first = revision()
    VoiceProfileRevisionStore.create(tmp_path, first)
    second = revision(2, parent=first.voice_profile_revision_sha256)

    with pytest.raises(ProductError) as missing:
        VoiceProfileRevisionStore.append(tmp_path, second, expected_previous_store_sha256=None)
    assert missing.value.code == "ERR_VOICE_PROFILE_STORE_CAS_REQUIRED"

    with pytest.raises(ProductError) as stale:
        VoiceProfileRevisionStore.append(tmp_path, second, expected_previous_store_sha256=SHA_B)
    assert stale.value.code == "ERR_VOICE_PROFILE_STORE_REVISION_CONFLICT"
    assert VoiceProfileRevisionStore.load(tmp_path).latest.revision == 1


def test_append_to_missing_store_fails_without_creating_a_snapshot(tmp_path: Path) -> None:
    with pytest.raises(ProductError) as missing:
        VoiceProfileRevisionStore.append(
            tmp_path,
            revision(2, parent=SHA_A),
            expected_previous_store_sha256=SHA_B,
        )
    assert missing.value.code == "ERR_VOICE_PROFILE_STORE_PREVIOUS_MISSING"
    assert not VoiceProfileRevisionStore.path(tmp_path).exists()


def test_append_rejects_wrong_parent_and_revision_gap(tmp_path: Path) -> None:
    first = revision()
    VoiceProfileRevisionStore.create(tmp_path, first)
    loaded = VoiceProfileRevisionStore.load(tmp_path)
    with pytest.raises(ProductError) as wrong_parent:
        VoiceProfileRevisionStore.append(
            tmp_path,
            revision(2, parent=SHA_C),
            expected_previous_store_sha256=loaded.store_sha256,
        )
    assert wrong_parent.value.code == "ERR_VOICE_PROFILE_PARENT_CONFLICT"

    with pytest.raises(ProductError) as gap:
        VoiceProfileRevisionStore.append(
            tmp_path,
            revision(3, parent=first.voice_profile_revision_sha256),
            expected_previous_store_sha256=loaded.store_sha256,
        )
    assert gap.value.code == "ERR_VOICE_PROFILE_REVISION_INVALID"


def test_nested_tamper_fails_even_when_outer_checksum_is_recomputed(tmp_path: Path) -> None:
    VoiceProfileRevisionStore.create(tmp_path, revision())
    path = VoiceProfileRevisionStore.path(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["revisions"][0]["consent"]["consent_scope"] = "tampered scope"
    _rewrite_store(path, document)
    with pytest.raises(ProductError) as exc:
        VoiceProfileRevisionStore.load(tmp_path)
    assert exc.value.code == "ERR_VOICE_PROFILE_STORE_INTEGRITY"


def test_history_reordering_fails_even_with_valid_revision_and_store_checksums(tmp_path: Path) -> None:
    first = revision()
    VoiceProfileRevisionStore.create(tmp_path, first)
    loaded = VoiceProfileRevisionStore.load(tmp_path)
    VoiceProfileRevisionStore.append(
        tmp_path,
        revision(2, parent=first.voice_profile_revision_sha256),
        expected_previous_store_sha256=loaded.store_sha256,
    )
    path = VoiceProfileRevisionStore.path(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["revisions"].reverse()
    _rewrite_store(path, document)
    with pytest.raises(ProductError) as exc:
        VoiceProfileRevisionStore.load(tmp_path)
    assert exc.value.code == "ERR_VOICE_PROFILE_STORE_INTEGRITY"


def test_failure_before_replace_preserves_previous_revision(tmp_path: Path) -> None:
    first = revision()
    VoiceProfileRevisionStore.create(tmp_path, first)
    loaded = VoiceProfileRevisionStore.load(tmp_path)

    def fail(stage: str, _path: Path) -> None:
        if stage == "before_replace":
            raise RuntimeError("synthetic interruption")

    with pytest.raises(RuntimeError, match="synthetic interruption"):
        VoiceProfileRevisionStore.append(
            tmp_path,
            revision(2, parent=first.voice_profile_revision_sha256),
            expected_previous_store_sha256=loaded.store_sha256,
            failure_injector=fail,
        )
    after = VoiceProfileRevisionStore.load(tmp_path)
    assert after.store_sha256 == loaded.store_sha256
    assert after.latest.revision == 1
    assert not list(VoiceProfileRevisionStore.path(tmp_path).parent.glob("*.tmp"))


def test_store_rejects_symlink_target(tmp_path: Path) -> None:
    VoiceProfileRevisionStore.create(tmp_path, revision())
    real = VoiceProfileRevisionStore.path(tmp_path)
    alternate = tmp_path / "alternate"
    alternate.mkdir()
    control = alternate / ".bai-project"
    control.mkdir()
    link = control / "voice-profile-revisions.json"
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ProductError) as exc:
        VoiceProfileRevisionStore.load(alternate)
    assert exc.value.code == "ERR_VOICE_PROFILE_STORE_FILE_INVALID"


def test_ready_preflight_still_never_authorizes_or_starts_execution() -> None:
    report = VoiceStudioPreflightService.evaluate(
        revision(),
        requested_language="ja-JP",
        requested_usage_class="COMMERCIAL_OWNER_VIDEO",
        requested_capability="ZERO_SHOT_CLONE",
        commercial_use_required=True,
    )
    document = report.to_dict()
    assert report.status is VoiceStudioPreflightStatus.READY
    assert report.reason_codes == ()
    assert document["metadata_ready"] is True
    assert document["execution_authorized"] is False
    assert document["runtime_probe_started"] is False
    assert document["model_load_started"] is False
    assert document["network_egress_started"] is False


def test_unknown_consent_license_and_capability_fail_closed() -> None:
    report = VoiceStudioPreflightService.evaluate(
        revision(ready=False),
        requested_language="ja-JP",
        requested_usage_class="COMMERCIAL_OWNER_VIDEO",
        requested_capability="ZERO_SHOT_CLONE",
        commercial_use_required=True,
    )
    assert report.status is VoiceStudioPreflightStatus.BLOCKED
    assert report.reason_codes == (
        "CONSENT_NOT_ACTIVE",
        "CONSENT_SUBJECT_NOT_VERIFIED",
        "CONSENT_EVIDENCE_MISSING",
        "CONSENT_USAGE_NOT_ALLOWED",
        "MODEL_ARTIFACT_NOT_APPROVED",
        "MODEL_LICENSE_UNKNOWN",
        "MODEL_LICENSE_EVIDENCE_MISSING",
        "COMMERCIAL_USE_NOT_ALLOWED",
        "CAPABILITY_PROBE_NOT_VERIFIED",
        "CAPABILITY_PROBE_EVIDENCE_MISSING",
        "OFFLINE_ONLY_NOT_DECLARED",
        "LANGUAGE_NOT_SUPPORTED",
        "CAPABILITY_NOT_SUPPORTED",
    )
    assert report.to_dict()["execution_authorized"] is False


def test_cross_field_invariants_reject_fabricated_approval() -> None:
    with pytest.raises(ValueError, match="ACTIVE Consent"):
        ConsentReference(
            "OWNER-LOCAL-01",
            "scope",
            ("COMMERCIAL_OWNER_VIDEO",),
            ConsentState.ACTIVE,
            False,
        )
    with pytest.raises(ValueError, match="commercial use"):
        LicenseReference(
            "MODEL-ARTIFACT-01",
            "model",
            SHA_A,
            "runtime",
            ModelLicenseClass.NONCOMMERCIAL_ONLY,
            ArtifactAdmissionState.APPROVED,
            True,
            "LICENSE-EVIDENCE-01",
            SHA_B,
        )
    with pytest.raises(ValueError, match="VERIFIED capability"):
        LocalVoiceCapabilityDescription(
            "LOCAL-TTS",
            "engine",
            ("ja-JP",),
            ("ZERO_SHOT_CLONE",),
            True,
            CapabilityProbeState.VERIFIED,
        )


def test_restricted_license_and_untyped_state_fail_closed() -> None:
    base = revision()
    restricted = VoiceProfileRevision(
        base.voice_profile_id,
        base.canonical_narration_profile_sha256,
        1,
        None,
        base.created_at,
        base.consent,
        LicenseReference(
            "MODEL-ARTIFACT-01",
            "exact-model-1.0",
            SHA_B,
            "LOCAL-RUNTIME-01",
            ModelLicenseClass.RESTRICTED,
            ArtifactAdmissionState.APPROVED,
            False,
            "LICENSE-EVIDENCE-01",
            SHA_C,
        ),
        base.capability,
    )
    report = VoiceStudioPreflightService.evaluate(
        restricted,
        requested_language="ja-JP",
        requested_usage_class="COMMERCIAL_OWNER_VIDEO",
        requested_capability="ZERO_SHOT_CLONE",
        commercial_use_required=False,
    )
    assert "MODEL_LICENSE_RESTRICTED" in report.reason_codes
    with pytest.raises(ValueError, match="ConsentState"):
        ConsentReference(
            "OWNER-LOCAL-01",
            "scope",
            ("PERSONAL_RESEARCH",),
            "UNKNOWN",  # type: ignore[arg-type]
            False,
        )
