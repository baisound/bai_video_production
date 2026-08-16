from __future__ import annotations

import ast
from dataclasses import fields
import inspect
from pathlib import Path

import pytest

from ai_video_production.scene_boundary import DetectorProfile, FrameRate, SceneSourceBinding
from ai_video_production.scene_detector_admission import (
    DetectorAdmissionState,
    DetectorCandidateFamily,
    DetectorEvidenceKind,
    DetectorEvidenceValidity,
    evaluate_detector_admission,
)
from ai_video_production.scene_detector_evidence import (
    DetectorArtifactArchitecture,
    DetectorArtifactComparisonReason,
    DetectorArtifactComparisonReceipt,
    DetectorArtifactComparisonState,
    DetectorArtifactKind,
    DetectorArtifactPlatform,
    DetectorEventKind,
    DetectorLicenseProvenanceReceipt,
    DetectorLicenseState,
    DetectorMaterializationReceipt,
    DetectorMaterializationState,
    DetectorOutputNormalizationReceipt,
    DetectorProbeDisposition,
    DetectorProbeKind,
    DetectorProbeInputMode,
    DetectorProbeOutcome,
    DetectorProbePlan,
    DetectorProbeReceipt,
    DetectorSignatureRequirement,
    ExpectedDetectorArtifact,
    NormalizedDetectorEvent,
    ObservedDetectorArtifact,
    compare_detector_artifacts,
    project_detector_evidence_claim,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
REAL = DetectorCandidateFamily.FFMPEG_SCENE_FILTER_PROFILE_FAMILY
CURRENT = DetectorEvidenceValidity.CURRENT_VALID_JUDGED


def digest(number: int) -> str:
    return "sha256:" + f"{number:064x}"


def profile(**overrides: object) -> DetectorProfile:
    values: dict[str, object] = {
        "profile_id": "ffmpeg-scene-filter",
        "profile_version": "1.0.0",
        "config_sha256": (
            "sha256:73b87e3c9ac24f183b12944ca57733e324994ca989042f4c2242fe57725a3162"
        ),
    }
    values.update(overrides)
    return DetectorProfile(**values)  # type: ignore[arg-type]


def expected(**overrides: object) -> ExpectedDetectorArtifact:
    values: dict[str, object] = {
        "candidate_family": REAL,
        "detector_profile": profile(),
        "artifact_coordinate_id": "ffmpeg-windows-x64-8.1.2",
        "artifact_kind": DetectorArtifactKind.ACQUISITION_ARCHIVE,
        "artifact_filename": "ffmpeg.8.1.2.nupkg",
        "version": "8.1.2",
        "platform": DetectorArtifactPlatform.WINDOWS,
        "architecture": DetectorArtifactArchitecture.X86_64,
        "byte_count": 123_456,
        "artifact_sha256": digest(1),
        "signature_requirement": DetectorSignatureRequirement.REQUIRED,
        "signature_sha256": digest(2),
        "publisher_identity_sha256": digest(3),
        "provenance_receipt_sha256": digest(4),
        "validity": CURRENT,
    }
    values.update(overrides)
    return ExpectedDetectorArtifact(**values)  # type: ignore[arg-type]


def observed(**overrides: object) -> ObservedDetectorArtifact:
    values: dict[str, object] = {
        "candidate_family": REAL,
        "detector_profile": profile(),
        "artifact_coordinate_id": "ffmpeg-windows-x64-8.1.2",
        "artifact_kind": DetectorArtifactKind.ACQUISITION_ARCHIVE,
        "artifact_filename": "ffmpeg.8.1.2.nupkg",
        "version": "8.1.2",
        "platform": DetectorArtifactPlatform.WINDOWS,
        "architecture": DetectorArtifactArchitecture.X86_64,
        "byte_count": 123_456,
        "artifact_sha256": digest(1),
        "signature_sha256": digest(2),
        "observation_receipt_sha256": digest(5),
        "validity": CURRENT,
    }
    values.update(overrides)
    return ObservedDetectorArtifact(**values)  # type: ignore[arg-type]


def comparison() -> DetectorArtifactComparisonReceipt:
    return compare_detector_artifacts(expected(), observed())


def source_binding(**overrides: object) -> SceneSourceBinding:
    values: dict[str, object] = {
        "source_asset_id": "ASSET-01J00000000000000000000000",
        "source_sha256": digest(7),
        "frame_rate": FrameRate(24, 1),
        "total_frames": 240,
    }
    values.update(overrides)
    return SceneSourceBinding(**values)  # type: ignore[arg-type]


def license_receipt(**overrides: object) -> DetectorLicenseProvenanceReceipt:
    values: dict[str, object] = {
        "candidate_family": REAL,
        "detector_profile": profile(),
        "artifact_comparison": comparison(),
        "spdx_identifier": "GPL-2.0-or-later",
        "license_text_sha256": digest(10),
        "provenance_receipt_sha256": digest(11),
        "distribution_policy_receipt_sha256": digest(12),
        "license_state": DetectorLicenseState.CLEARED,
        "validity": CURRENT,
    }
    values.update(overrides)
    return DetectorLicenseProvenanceReceipt(**values)  # type: ignore[arg-type]


def materialization_receipt(**overrides: object) -> DetectorMaterializationReceipt:
    values: dict[str, object] = {
        "candidate_family": REAL,
        "detector_profile": profile(),
        "artifact_comparison": comparison(),
        "dependency_graph_sha256": digest(20),
        "platform_arch_receipt_sha256": digest(21),
        "materialization_receipt_sha256": digest(22),
        "materialization_state": DetectorMaterializationState.VERIFIED_CONTAINED,
        "validity": CURRENT,
    }
    values.update(overrides)
    return DetectorMaterializationReceipt(**values)  # type: ignore[arg-type]


def probe_plan(**overrides: object) -> DetectorProbePlan:
    values: dict[str, object] = {
        "candidate_family": REAL,
        "detector_profile": profile(),
        "artifact_comparison": comparison(),
        "input_mode": DetectorProbeInputMode.SYNTHETIC_MEDIA,
        "source_binding": source_binding(),
        "probe_kinds": tuple(DetectorProbeKind),
        "timeout_ms": 30_000,
        "stdout_cap_bytes": 1_048_576,
        "stderr_cap_bytes": 1_048_576,
        "memory_cap_bytes": 536_870_912,
        "event_cap": 8,
    }
    values.update(overrides)
    return DetectorProbePlan(**values)  # type: ignore[arg-type]


def probe_receipt(**overrides: object) -> DetectorProbeReceipt:
    plan = overrides.pop("plan", probe_plan())
    assert isinstance(plan, DetectorProbePlan)
    outcomes = tuple(
        DetectorProbeOutcome(kind, DetectorProbeDisposition.PASS, digest(30 + index), digest(40 + index), None)
        for index, kind in enumerate(plan.probe_kinds)
    )
    values: dict[str, object] = {"plan": plan, "outcomes": outcomes, "validity": CURRENT}
    values.update(overrides)
    return DetectorProbeReceipt(**values)  # type: ignore[arg-type]


def normalized_receipt(**overrides: object) -> DetectorOutputNormalizationReceipt:
    probe = overrides.pop("probe_receipt", probe_receipt())
    assert isinstance(probe, DetectorProbeReceipt)
    events = (
        NormalizedDetectorEvent(
            REAL,
            profile(),
            probe.receipt_sha256,
            0,
            DetectorEventKind.SCENE_CANDIDATE,
            42,
            875,
            None,
            digest(50),
        ),
        NormalizedDetectorEvent(
            REAL,
            profile(),
            probe.receipt_sha256,
            1,
            DetectorEventKind.END,
            None,
            None,
            None,
            digest(51),
        ),
    )
    values: dict[str, object] = {"probe_receipt": probe, "events": events, "validity": CURRENT}
    values.update(overrides)
    return DetectorOutputNormalizationReceipt(**values)  # type: ignore[arg-type]


def test_closed_enums_and_caps_are_exact():
    assert {item.value for item in DetectorArtifactComparisonState} == {
        "MATCH",
        "MISMATCH",
        "NOT_OBSERVED",
        "OBSERVED_ONLY_UNBOUND",
        "UNKNOWN",
    }
    assert len(tuple(DetectorProbeKind)) == 5
    assert len(tuple(DetectorEventKind)) == 3
    assert len(tuple(DetectorLicenseState)) == 4
    assert len(tuple(DetectorMaterializationState)) == 4


def test_expected_and_observed_exact_match_is_current_and_deterministic():
    left = comparison()
    right = comparison()
    assert left.comparison_state is DetectorArtifactComparisonState.MATCH
    assert left.comparison_reason is DetectorArtifactComparisonReason.EXACT_IDENTITY_MATCH
    assert left.validity is CURRENT
    assert left.canonical_bytes() == right.canonical_bytes()
    payload = left.to_dict()
    claimed = payload.pop("receipt_sha256")
    assert claimed == sha256_bytes(canonical_json_bytes(payload))
    assert left.runtime_authorized is False
    assert left.external_effect_performed is False


def test_comparison_null_partition_is_total_and_both_null_rejects():
    not_observed = compare_detector_artifacts(expected(), None)
    assert not_observed.comparison_state is DetectorArtifactComparisonState.NOT_OBSERVED
    assert not_observed.comparison_reason is DetectorArtifactComparisonReason.OBSERVATION_ABSENT
    assert not_observed.validity is DetectorEvidenceValidity.UNKNOWN

    observed_only = compare_detector_artifacts(None, observed())
    assert observed_only.comparison_state is DetectorArtifactComparisonState.OBSERVED_ONLY_UNBOUND
    assert observed_only.comparison_reason is DetectorArtifactComparisonReason.EXPECTED_IDENTITY_ABSENT
    assert observed_only.validity is DetectorEvidenceValidity.UNKNOWN

    with pytest.raises(ValueError, match="both be null"):
        compare_detector_artifacts(None, None)


def test_mismatch_incomplete_and_noncurrent_are_machine_distinct():
    mismatch = compare_detector_artifacts(expected(), observed(byte_count=999))
    assert mismatch.comparison_state is DetectorArtifactComparisonState.MISMATCH
    assert mismatch.comparison_reason is DetectorArtifactComparisonReason.IDENTITY_FIELD_MISMATCH
    assert mismatch.validity is CURRENT

    incomplete = compare_detector_artifacts(
        expected(byte_count=None, artifact_sha256=None), observed()
    )
    assert incomplete.comparison_state is DetectorArtifactComparisonState.UNKNOWN
    assert incomplete.comparison_reason is DetectorArtifactComparisonReason.EXPECTED_IDENTITY_INCOMPLETE
    assert incomplete.validity is DetectorEvidenceValidity.UNKNOWN

    stale = compare_detector_artifacts(
        expected(validity=DetectorEvidenceValidity.STALE), observed()
    )
    assert stale.comparison_state is DetectorArtifactComparisonState.UNKNOWN
    assert stale.comparison_reason is DetectorArtifactComparisonReason.UNDERLYING_EVIDENCE_NOT_CURRENT


def test_cross_candidate_profile_and_coordinate_borrowing_rejects():
    with pytest.raises(ValueError, match="candidate binding mismatch"):
        compare_detector_artifacts(
            expected(),
            observed(candidate_family=DetectorCandidateFamily.PYSCENEDETECT_CONTENT_PROFILE_FAMILY),
        )
    with pytest.raises(ValueError, match="profile binding mismatch"):
        compare_detector_artifacts(observed=observed(detector_profile=profile(profile_version="2.0.0")), expected=expected())
    with pytest.raises(ValueError, match="borrowing"):
        compare_detector_artifacts(expected(), observed(artifact_coordinate_id="another-coordinate"))


def test_artifact_coordinates_reject_paths_bad_hashes_and_unknown_families():
    with pytest.raises(ValueError, match="basename"):
        expected(artifact_filename="bin/ffmpeg.exe")
    with pytest.raises(ValueError, match="artifact_sha256"):
        observed(artifact_sha256="sha256:bad")
    with pytest.raises(ValueError, match="real detector"):
        expected(candidate_family=DetectorCandidateFamily.UNKNOWN)
    with pytest.raises(ValueError, match="byte_count"):
        expected(byte_count=(1 << 63))


def test_comparison_receipt_cannot_be_claimed_or_constructed_directly():
    with pytest.raises(TypeError, match="_token"):
        DetectorArtifactComparisonReceipt(  # type: ignore[call-arg]
            expected(),
            observed(),
            DetectorArtifactComparisonState.MATCH,
            DetectorArtifactComparisonReason.EXACT_IDENTITY_MATCH,
            CURRENT,
        )
    with pytest.raises(ValueError, match="created by"):
        DetectorArtifactComparisonReceipt(
            expected(),
            observed(),
            DetectorArtifactComparisonState.MATCH,
            DetectorArtifactComparisonReason.EXACT_IDENTITY_MATCH,
            CURRENT,
            _token=object(),
        )


def test_license_and_materialization_states_fail_closed():
    with pytest.raises(ValueError, match="CLEARED"):
        license_receipt(validity=DetectorEvidenceValidity.UNKNOWN)
    with pytest.raises(ValueError, match="VERIFIED_CONTAINED"):
        materialization_receipt(validity=DetectorEvidenceValidity.REVOKED)
    review = license_receipt(
        license_state=DetectorLicenseState.REVIEW_REQUIRED,
        validity=DetectorEvidenceValidity.UNKNOWN,
    )
    with pytest.raises(ValueError, match="not current-valid"):
        project_detector_evidence_claim(DetectorEvidenceKind.LICENSE, review, digest(100))


def test_probe_plan_is_bounded_unique_and_canonical():
    assert probe_plan().to_dict()["execution_authorized"] is False
    assert probe_plan().to_dict()["media_input_authorized"] is False
    with pytest.raises(ValueError, match="1-5"):
        probe_plan(probe_kinds=())
    with pytest.raises(ValueError, match="unique and canonically ordered"):
        probe_plan(probe_kinds=(DetectorProbeKind.VERSION, DetectorProbeKind.VERSION))
    with pytest.raises(ValueError, match="timeout_ms"):
        probe_plan(timeout_ms=300_001)
    with pytest.raises(ValueError, match="event_cap"):
        probe_plan(event_cap=513)
    with pytest.raises(ValueError, match="memory_cap_bytes"):
        probe_plan(memory_cap_bytes=1_073_741_825)
    with pytest.raises(ValueError, match="null source_binding"):
        probe_plan(input_mode=DetectorProbeInputMode.NO_MEDIA)
    no_media = probe_plan(
        input_mode=DetectorProbeInputMode.NO_MEDIA,
        source_binding=None,
        probe_kinds=(DetectorProbeKind.VERSION,),
    )
    assert no_media.source_binding is None
    with pytest.raises(ValueError, match="cannot plan OUTPUT_NORMALIZATION"):
        probe_plan(
            input_mode=DetectorProbeInputMode.NO_MEDIA,
            source_binding=None,
            probe_kinds=(DetectorProbeKind.OUTPUT_NORMALIZATION,),
        )


def test_probe_receipt_requires_exact_plan_set_and_current_passes():
    plan = probe_plan(probe_kinds=(DetectorProbeKind.VERSION, DetectorProbeKind.RESOURCE_BOUNDS))
    only_one = (
        DetectorProbeOutcome(DetectorProbeKind.VERSION, DetectorProbeDisposition.PASS, digest(1), digest(2), None),
    )
    with pytest.raises(ValueError, match="exactly equal"):
        DetectorProbeReceipt(plan, only_one, CURRENT)

    failed = tuple(
        DetectorProbeOutcome(
            kind,
            DetectorProbeDisposition.FAIL if index == 0 else DetectorProbeDisposition.PASS,
            digest(110 + index),
            digest(120 + index),
            "PROBE_FAILED" if index == 0 else None,
        )
        for index, kind in enumerate(plan.probe_kinds)
    )
    with pytest.raises(ValueError, match="every planned outcome PASS"):
        DetectorProbeReceipt(plan, failed, CURRENT)


def test_probe_outcome_requires_typed_incident_boundary():
    with pytest.raises(ValueError, match="cannot carry"):
        DetectorProbeOutcome(
            DetectorProbeKind.VERSION,
            DetectorProbeDisposition.PASS,
            digest(1),
            digest(2),
            "INCIDENT",
        )
    with pytest.raises(ValueError, match="require an incident"):
        DetectorProbeOutcome(
            DetectorProbeKind.VERSION,
            DetectorProbeDisposition.UNKNOWN,
            digest(1),
            digest(2),
            None,
        )


def test_normalized_events_are_exact_bounded_and_terminal():
    receipt = normalized_receipt()
    assert receipt.events[-1].event_kind is DetectorEventKind.END
    assert receipt.manifest_compiled is False
    assert receipt.media_read_performed is False
    assert receipt.runtime_authorized is False

    probe = probe_receipt(plan=probe_plan(event_cap=1))
    with pytest.raises(ValueError, match="event cap"):
        normalized_receipt(probe_receipt=probe)

    good = normalized_receipt()
    reversed_ordinals = (
        good.events[1],
        good.events[0],
    )
    with pytest.raises(ValueError, match="ordinals"):
        DetectorOutputNormalizationReceipt(good.probe_receipt, reversed_ordinals, CURRENT)

    with pytest.raises(ValueError, match="final normalized"):
        DetectorOutputNormalizationReceipt(good.probe_receipt, good.events[:1], CURRENT)


def test_event_borrowing_and_nonincreasing_frames_reject():
    receipt = normalized_receipt()
    probe = receipt.probe_receipt
    wrong = NormalizedDetectorEvent(
        DetectorCandidateFamily.PYSCENEDETECT_CONTENT_PROFILE_FAMILY,
        profile(),
        probe.receipt_sha256,
        0,
        DetectorEventKind.SCENE_CANDIDATE,
        42,
        800,
        None,
        digest(1),
    )
    with pytest.raises(ValueError, match="candidate borrowing"):
        DetectorOutputNormalizationReceipt(probe, (wrong, receipt.events[-1]), CURRENT)

    first = receipt.events[0]
    duplicate_frame = NormalizedDetectorEvent(
        REAL,
        profile(),
        probe.receipt_sha256,
        1,
        DetectorEventKind.SCENE_CANDIDATE,
        42,
        700,
        None,
        digest(2),
    )
    terminal = NormalizedDetectorEvent(
        REAL,
        profile(),
        probe.receipt_sha256,
        2,
        DetectorEventKind.END,
        None,
        None,
        None,
        digest(3),
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        DetectorOutputNormalizationReceipt(probe, (first, duplicate_frame, terminal), CURRENT)


def test_exact_receipt_to_r1b1_mapping_covers_all_twelve_kinds():
    supports = {
        DetectorEvidenceKind.ARTIFACT_IDENTITY: comparison(),
        DetectorEvidenceKind.VERSION_PIN: comparison(),
        DetectorEvidenceKind.ARTIFACT_SHA256: comparison(),
        DetectorEvidenceKind.PROVENANCE: license_receipt(),
        DetectorEvidenceKind.LICENSE: license_receipt(),
        DetectorEvidenceKind.DISTRIBUTION_POLICY: license_receipt(),
        DetectorEvidenceKind.DEPENDENCY_GRAPH: materialization_receipt(),
        DetectorEvidenceKind.PLATFORM_ARCH: comparison(),
        DetectorEvidenceKind.OFFLINE_MATERIALIZATION: materialization_receipt(),
        DetectorEvidenceKind.RUNTIME_CAPABILITY: probe_receipt(),
        DetectorEvidenceKind.RESOURCE_BOUNDS: probe_receipt(),
        DetectorEvidenceKind.OUTPUT_NORMALIZATION: normalized_receipt(),
    }
    claims = tuple(
        project_detector_evidence_claim(kind, supports[kind], digest(200))
        for kind in DetectorEvidenceKind
    )
    decision = evaluate_detector_admission(REAL, profile(), claims)
    assert decision.admission_state is DetectorAdmissionState.ADMITTED
    assert decision.missing_evidence == ()
    assert decision.to_dict()["runtime_authorized"] is False


def test_mapping_rejects_strengthening_mismatch_and_missing_probe_kind():
    with pytest.raises(ValueError, match="cannot strengthen"):
        project_detector_evidence_claim(
            DetectorEvidenceKind.RUNTIME_CAPABILITY,
            comparison(),
            digest(1),
        )
    with pytest.raises(ValueError, match="exact expected/observed MATCH"):
        project_detector_evidence_claim(
            DetectorEvidenceKind.ARTIFACT_IDENTITY,
            compare_detector_artifacts(expected(), observed(byte_count=1)),
            digest(1),
        )
    version_only = probe_receipt(plan=probe_plan(probe_kinds=(DetectorProbeKind.VERSION,)))
    with pytest.raises(ValueError, match="required probe kind"):
        project_detector_evidence_claim(
            DetectorEvidenceKind.RUNTIME_CAPABILITY,
            version_only,
            digest(1),
        )

    probe = probe_receipt()
    incident = NormalizedDetectorEvent(
        REAL,
        profile(),
        probe.receipt_sha256,
        0,
        DetectorEventKind.INCIDENT,
        None,
        None,
        "OUTPUT_PARSE_FAILED",
        digest(5),
    )
    terminal = NormalizedDetectorEvent(
        REAL,
        profile(),
        probe.receipt_sha256,
        1,
        DetectorEventKind.END,
        None,
        None,
        None,
        digest(6),
    )
    normalization = DetectorOutputNormalizationReceipt(
        probe,
        (incident, terminal),
        CURRENT,
    )
    with pytest.raises(ValueError, match="INCIDENT"):
        project_detector_evidence_claim(
            DetectorEvidenceKind.OUTPUT_NORMALIZATION,
            normalization,
            digest(1),
        )


def test_normalized_event_frame_is_bounded_by_exact_r0_source():
    probe = probe_receipt(plan=probe_plan(source_binding=source_binding(total_frames=42)))
    out_of_range = NormalizedDetectorEvent(
        REAL,
        profile(),
        probe.receipt_sha256,
        0,
        DetectorEventKind.SCENE_CANDIDATE,
        42,
        900,
        None,
        digest(1),
    )
    terminal = NormalizedDetectorEvent(
        REAL,
        profile(),
        probe.receipt_sha256,
        1,
        DetectorEventKind.END,
        None,
        None,
        None,
        digest(2),
    )
    with pytest.raises(ValueError, match="source binding"):
        DetectorOutputNormalizationReceipt(probe, (out_of_range, terminal), CURRENT)


def test_contract_surface_has_no_path_bytes_runner_callback_or_effect_imports():
    public_record_types = (
        ExpectedDetectorArtifact,
        ObservedDetectorArtifact,
        DetectorArtifactComparisonReceipt,
        DetectorLicenseProvenanceReceipt,
        DetectorMaterializationReceipt,
        DetectorProbePlan,
        DetectorProbeReceipt,
        NormalizedDetectorEvent,
        DetectorOutputNormalizationReceipt,
    )
    forbidden_fields = {
        "path",
        "raw_bytes",
        "runner",
        "callback",
        "filesystem_handle",
        "command",
        "argv",
        "media",
    }
    assert all({field.name for field in fields(kind)}.isdisjoint(forbidden_fields) for kind in public_record_types)
    assert set(inspect.signature(compare_detector_artifacts).parameters) == {"expected", "observed"}
    assert set(inspect.signature(project_detector_evidence_claim).parameters) == {
        "evidence_kind",
        "support_receipt",
        "authority_scope_sha256",
    }

    module_path = ROOT / "src" / "ai_video_production" / "scene_detector_evidence.py"
    text = module_path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported_roots.isdisjoint(
        {
            "pathlib",
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "cv2",
            "opencv",
            "ffmpeg",
        }
    )
    assert not any(isinstance(node, (ast.With, ast.AsyncWith)) for node in ast.walk(tree))
    assert "build_scene_boundary_manifest" not in text
    assert "DetectedSceneRange" not in text
