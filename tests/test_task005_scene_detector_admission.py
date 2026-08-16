from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from ai_video_production.scene_boundary import DetectorProfile
from ai_video_production.scene_detector_admission import (
    DetectorAdmissionDecision,
    DetectorAdmissionState,
    DetectorCandidateFamily,
    DetectorEvidenceClaim,
    DetectorEvidenceKind,
    DetectorEvidenceValidity,
    evaluate_detector_admission,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
REAL = DetectorCandidateFamily.FFMPEG_SCENE_FILTER_PROFILE_FAMILY


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


def claim(
    kind: DetectorEvidenceKind,
    *,
    candidate: DetectorCandidateFamily = REAL,
    bound_profile: DetectorProfile | None = None,
    validity: DetectorEvidenceValidity = DetectorEvidenceValidity.CURRENT_VALID_JUDGED,
) -> DetectorEvidenceClaim:
    ordinal = tuple(DetectorEvidenceKind).index(kind) + 1
    return DetectorEvidenceClaim(
        candidate,
        bound_profile or profile(),
        kind,
        "sha256:" + f"{ordinal:064x}",
        "sha256:" + f"{ordinal + 100:064x}",
        validity,
    )


def claims_for(*kinds: DetectorEvidenceKind) -> tuple[DetectorEvidenceClaim, ...]:
    selected = frozenset(kinds)
    return tuple(claim(kind) for kind in DetectorEvidenceKind if kind in selected)


def all_claims() -> tuple[DetectorEvidenceClaim, ...]:
    return tuple(claim(kind) for kind in DetectorEvidenceKind)


def test_closed_enums_are_exact():
    assert {item.value for item in DetectorCandidateFamily} == {
        "BOUNDED_SYNTHETIC",
        "FFMPEG_SCENE_FILTER_PROFILE_FAMILY",
        "FFPROBE_METADATA_ONLY",
        "PYSCENEDETECT_CONTENT_PROFILE_FAMILY",
        "OPENCV_CUSTOM_PROFILE_FAMILY",
        "FFMPEG_SILENCE_AUDIO_ONLY",
        "UNKNOWN",
    }
    assert {item.value for item in DetectorAdmissionState} == {
        "CONTRACT_READY_NO_RUNTIME",
        "ACQUISITION_GATE_REQUIRED",
        "LICENSE_REVIEW_REQUIRED",
        "CAPABILITY_EVIDENCE_REQUIRED",
        "NOT_ADMISSIBLE",
        "UNKNOWN",
        "ADMITTED",
    }
    assert len(tuple(DetectorEvidenceKind)) == 12
    assert len(tuple(DetectorEvidenceValidity)) == 5


def test_exact_config_vector_matches_r0_canonicalization():
    actual = DetectorProfile.from_config(
        "ffmpeg-scene-filter",
        "1.0.0",
        {
            "threshold_milli": 400,
            "frame_mapping": "integer_index_v1",
            "filter": "scene",
        },
    )
    assert actual == profile()


def test_synthetic_is_contract_ready_without_runtime_or_evidence():
    decision = evaluate_detector_admission(
        DetectorCandidateFamily.BOUNDED_SYNTHETIC, profile(), ()
    )
    payload = decision.to_dict()
    assert decision.admission_state is DetectorAdmissionState.CONTRACT_READY_NO_RUNTIME
    assert decision.missing_evidence == ()
    assert payload["selected_runtime_candidate"] is None
    assert payload["runtime_authorized"] is False
    assert payload["media_read_performed"] is False
    assert payload["external_effect_performed"] is False


@pytest.mark.parametrize(
    "candidate",
    [
        DetectorCandidateFamily.FFPROBE_METADATA_ONLY,
        DetectorCandidateFamily.FFMPEG_SILENCE_AUDIO_ONLY,
    ],
)
def test_metadata_and_audio_candidates_are_not_scene_detectors(candidate):
    decision = evaluate_detector_admission(candidate, profile(), ())
    assert decision.admission_state is DetectorAdmissionState.NOT_ADMISSIBLE
    assert decision.missing_evidence == ()


def test_unknown_candidate_fails_closed_without_placeholder_claims():
    decision = evaluate_detector_admission(DetectorCandidateFamily.UNKNOWN, profile(), ())
    assert decision.admission_state is DetectorAdmissionState.UNKNOWN
    assert decision.missing_evidence == tuple(DetectorEvidenceKind)


def test_real_candidate_without_claims_requires_license_review_first():
    decision = evaluate_detector_admission(REAL, profile(), ())
    assert decision.admission_state is DetectorAdmissionState.LICENSE_REVIEW_REQUIRED
    assert decision.missing_evidence == tuple(DetectorEvidenceKind)
    assert (
        decision.to_dict()["selected_contract_candidate"]
        == "FFMPEG_SCENE_FILTER_PROFILE_FAMILY"
    )
    assert decision.to_dict()["candidate_is_selected_contract"] is True


def test_missing_set_precedence_is_license_then_acquisition_then_capability():
    license_only = claims_for(
        DetectorEvidenceKind.LICENSE,
        DetectorEvidenceKind.DISTRIBUTION_POLICY,
    )
    assert (
        evaluate_detector_admission(REAL, profile(), license_only).admission_state
        is DetectorAdmissionState.ACQUISITION_GATE_REQUIRED
    )

    capability_missing = tuple(
        claim(kind)
        for kind in DetectorEvidenceKind
        if kind
        not in {
            DetectorEvidenceKind.RUNTIME_CAPABILITY,
            DetectorEvidenceKind.RESOURCE_BOUNDS,
            DetectorEvidenceKind.OUTPUT_NORMALIZATION,
        }
    )
    decision = evaluate_detector_admission(REAL, profile(), capability_missing)
    assert decision.admission_state is DetectorAdmissionState.CAPABILITY_EVIDENCE_REQUIRED
    assert decision.missing_evidence == (
        DetectorEvidenceKind.RUNTIME_CAPABILITY,
        DetectorEvidenceKind.RESOURCE_BOUNDS,
        DetectorEvidenceKind.OUTPUT_NORMALIZATION,
    )


@pytest.mark.parametrize(
    "candidate",
    [
        DetectorCandidateFamily.FFMPEG_SCENE_FILTER_PROFILE_FAMILY,
        DetectorCandidateFamily.PYSCENEDETECT_CONTENT_PROFILE_FAMILY,
        DetectorCandidateFamily.OPENCV_CUSTOM_PROFILE_FAMILY,
    ],
)
def test_full_current_valid_evidence_can_only_admit_the_contract(candidate):
    claims = tuple(
        claim(kind, candidate=candidate) for kind in DetectorEvidenceKind
    )
    decision = evaluate_detector_admission(candidate, profile(), claims)
    payload = decision.to_dict()
    assert decision.admission_state is DetectorAdmissionState.ADMITTED
    assert decision.missing_evidence == ()
    assert payload["runtime_authorized"] is False
    assert payload["selected_runtime_candidate"] is None


@pytest.mark.parametrize(
    "validity",
    [
        DetectorEvidenceValidity.STALE,
        DetectorEvidenceValidity.REVOKED,
        DetectorEvidenceValidity.CONFLICTED,
        DetectorEvidenceValidity.UNKNOWN,
    ],
)
def test_any_non_current_claim_blocks_admission(validity):
    claims = list(all_claims())
    claims[0] = claim(DetectorEvidenceKind.ARTIFACT_IDENTITY, validity=validity)
    decision = evaluate_detector_admission(REAL, profile(), tuple(claims))
    assert decision.admission_state is DetectorAdmissionState.UNKNOWN
    assert decision.missing_evidence == ()


def test_claims_reject_bad_sha_wrong_types_and_non_detector_families():
    with pytest.raises(ValueError, match="receipt_sha256"):
        DetectorEvidenceClaim(
            REAL,
            profile(),
            DetectorEvidenceKind.LICENSE,
            "sha256:bad",
            "sha256:" + "a" * 64,
            DetectorEvidenceValidity.CURRENT_VALID_JUDGED,
        )
    with pytest.raises(TypeError, match="detector_profile"):
        DetectorEvidenceClaim(  # type: ignore[arg-type]
            REAL,
            object(),
            DetectorEvidenceKind.LICENSE,
            "sha256:" + "a" * 64,
            "sha256:" + "b" * 64,
            DetectorEvidenceValidity.CURRENT_VALID_JUDGED,
        )
    with pytest.raises(ValueError, match="real detector"):
        claim(
            DetectorEvidenceKind.LICENSE,
            candidate=DetectorCandidateFamily.FFPROBE_METADATA_ONLY,
        )


def test_duplicate_noncanonical_cross_candidate_and_cross_profile_claims_reject():
    one = claim(DetectorEvidenceKind.LICENSE)
    with pytest.raises(ValueError, match="unique"):
        evaluate_detector_admission(REAL, profile(), (one, one))

    reversed_claims = (
        claim(DetectorEvidenceKind.LICENSE),
        claim(DetectorEvidenceKind.ARTIFACT_IDENTITY),
    )
    with pytest.raises(ValueError, match="canonical kind order"):
        evaluate_detector_admission(REAL, profile(), reversed_claims)

    wrong_candidate = claim(
        DetectorEvidenceKind.LICENSE,
        candidate=DetectorCandidateFamily.PYSCENEDETECT_CONTENT_PROFILE_FAMILY,
    )
    with pytest.raises(ValueError, match="candidate mismatch"):
        evaluate_detector_admission(REAL, profile(), (wrong_candidate,))

    wrong_profile = claim(
        DetectorEvidenceKind.LICENSE,
        bound_profile=profile(profile_version="2.0.0"),
    )
    with pytest.raises(ValueError, match="profile mismatch"):
        evaluate_detector_admission(REAL, profile(), (wrong_profile,))


def test_claim_array_is_exact_tuple_and_bounded_at_twelve():
    with pytest.raises(TypeError, match="exact tuple"):
        evaluate_detector_admission(REAL, profile(), list(all_claims()))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="maximum of 12"):
        evaluate_detector_admission(REAL, profile(), all_claims() + (all_claims()[0],))


def test_decision_canonical_digest_is_deterministic_and_non_self():
    left = evaluate_detector_admission(REAL, profile(), all_claims())
    right = evaluate_detector_admission(REAL, profile(), all_claims())
    assert left.canonical_bytes() == right.canonical_bytes()
    payload = left.to_dict()
    claimed = payload.pop("decision_sha256")
    assert claimed == sha256_bytes(canonical_json_bytes(payload))


def test_admission_decision_cannot_be_constructed_without_the_evaluator():
    with pytest.raises(TypeError, match="_construction_token"):
        DetectorAdmissionDecision(  # type: ignore[call-arg]
            REAL,
            profile(),
            (),
            (),
            DetectorAdmissionState.ADMITTED,
        )
    with pytest.raises(ValueError, match="created by the evaluator"):
        DetectorAdmissionDecision(
            REAL,
            profile(),
            (),
            (),
            DetectorAdmissionState.ADMITTED,
            _construction_token=object(),
        )


def test_api_and_import_surface_have_no_runtime_effects_or_r0_reimplementation():
    parameters = set(inspect.signature(evaluate_detector_admission).parameters)
    assert parameters == {"candidate_family", "detector_profile", "evidence_claims"}

    module_path = ROOT / "src" / "ai_video_production" / "scene_detector_admission.py"
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
    assert "build_scene_boundary_manifest" not in text
    assert "DetectedSceneRange" not in text
    assert not any(isinstance(node, (ast.With, ast.AsyncWith)) for node in ast.walk(tree))
