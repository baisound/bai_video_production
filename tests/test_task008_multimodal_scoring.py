from __future__ import annotations

import ast
from dataclasses import replace
import inspect

import pytest

from ai_video_production.multimodal_scoring import (
    CandidateFeatureInput,
    CandidateScoreState,
    EvidenceValidity,
    FeatureModality,
    FeatureObservation,
    FeaturePolarity,
    FeatureProvenance,
    FeatureRule,
    FeatureSourceSelector,
    ScoringProfile,
    compile_multimodal_scores,
    verify_multimodal_scoring_manifest_hash,
)


ASSET_ID = "ASSET-01ARZ3NDEKTSV4RRFFQ69G5FAV"
CANDIDATE_A = "CAND-01ARZ3NDEKTSV4RRFFQ69G5FAV"
CANDIDATE_B = "CAND-01ARZ3NDEKTSV4RRFFQ69G5FAW"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


VISUAL = FeatureSourceSelector("TASK-005", "scene-boundary-manifest.v1")
AUDIO = FeatureSourceSelector("TASK-024", "cut-candidate-manifest.v1")
OCR = FeatureSourceSelector("TASK-008", "future-canonical-ocr-feature.v1")


def profile() -> ScoringProfile:
    return ScoringProfile(
        "task008.synthetic.v1",
        "1.0.0",
        (
            FeatureRule("audio.silence", FeatureModality.AUDIO, 400, 0, 100, FeaturePolarity.INVERSE, True, None, (AUDIO,)),
            FeatureRule("ocr.salience", FeatureModality.OCR_TEXT, 200, 0, 100, FeaturePolarity.DIRECT, False, 500, (OCR,)),
            FeatureRule("visual.motion", FeatureModality.VISUAL, 400, 0, 100, FeaturePolarity.DIRECT, True, None, (VISUAL,)),
        ),
    )


def provenance(source: FeatureSourceSelector, state: EvidenceValidity = EvidenceValidity.CURRENT_VALID) -> FeatureProvenance:
    return FeatureProvenance(source, SHA_A, "row-000001", SHA_B, state)


def observations(*, visual_state: EvidenceValidity = EvidenceValidity.CURRENT_VALID):
    return (
        FeatureObservation("visual.motion", FeatureModality.VISUAL, 75, provenance(VISUAL, visual_state)),
        FeatureObservation("audio.silence", FeatureModality.AUDIO, 20, provenance(AUDIO)),
    )


def candidate(candidate_id: str = CANDIDATE_A, rows=None) -> CandidateFeatureInput:
    return CandidateFeatureInput(candidate_id, 0, 1_000_000, observations() if rows is None else tuple(rows))


def test_complete_score_is_fixed_point_deterministic_and_advisory_only():
    first = compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (candidate(),)).to_dict()
    second = compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (candidate(),)).to_dict()
    assert first == second
    assert first["candidate_scores"][0]["state"] == "COMPLETE"
    assert first["candidate_scores"][0]["composite_score_milli"] == 720
    assert first["candidate_scores"][0]["feature_evaluations"][1]["disposition"] == "DEFAULTED_OPTIONAL"
    assert first["review_state"] == "REVIEW_REQUIRED"
    assert first["downstream_edit_plan_use"] == "ADVISORY_ONLY"
    assert first["automatic_edit_plan_mutation_authorized"] is False
    assert first["media_read_performed"] is False
    assert first["ocr_execution_performed"] is False
    verify_multimodal_scoring_manifest_hash(first)


def test_candidate_input_order_does_not_change_manifest():
    left = candidate(CANDIDATE_A)
    right = CandidateFeatureInput(CANDIDATE_B, 1_000_000, 2_000_000, observations())
    first = compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (right, left)).to_dict()
    second = compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (left, right)).to_dict()
    assert first == second
    assert [row["candidate_id"] for row in first["candidate_scores"]] == [CANDIDATE_A, CANDIDATE_B]


def test_required_missing_is_not_unknown_or_a_score():
    rows = tuple(row for row in observations() if row.feature_key != "visual.motion")
    result = compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (candidate(rows=rows),)).scores[0]
    assert result.state is CandidateScoreState.MISSING_REQUIRED_FEATURE
    assert result.missing_required_feature_keys == ("visual.motion",)
    assert result.composite_score_milli is None


@pytest.mark.parametrize(
    ("validity", "expected"),
    [
        (EvidenceValidity.UNKNOWN, CandidateScoreState.UNKNOWN_EVIDENCE),
        (EvidenceValidity.STALE, CandidateScoreState.STALE_OR_REVOKED_EVIDENCE),
        (EvidenceValidity.REVOKED, CandidateScoreState.STALE_OR_REVOKED_EVIDENCE),
    ],
)
def test_non_current_evidence_never_produces_a_score(validity, expected):
    result = compile_multimodal_scores(
        ASSET_ID,
        SHA_C,
        profile(),
        (candidate(rows=observations(visual_state=validity)),),
    ).scores[0]
    assert result.state is expected
    assert result.composite_score_milli is None


def test_unknown_does_not_hide_stale_or_revoked_evidence():
    rows = (
        FeatureObservation("visual.motion", FeatureModality.VISUAL, 75, provenance(VISUAL, EvidenceValidity.UNKNOWN)),
        FeatureObservation("audio.silence", FeatureModality.AUDIO, 20, provenance(AUDIO, EvidenceValidity.REVOKED)),
    )
    result = compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (candidate(rows=rows),)).scores[0]
    assert result.state is CandidateScoreState.STALE_OR_REVOKED_EVIDENCE
    assert result.unknown_feature_keys == ("visual.motion",)
    assert result.stale_or_revoked_feature_keys == ("audio.silence",)


def test_profile_requires_exact_weight_multimodality_and_sorted_keys():
    rules = profile().rules
    with pytest.raises(ValueError, match="exactly 1000"):
        ScoringProfile("profile", "1.0.0", (replace(rules[0], weight_milli=399), rules[1], rules[2]))
    with pytest.raises(ValueError, match="at least two modalities"):
        ScoringProfile(
            "profile",
            "1.0.0",
            (
                replace(
                    rules[0],
                    feature_key="visual.alpha",
                    modality=FeatureModality.VISUAL,
                    weight_milli=500,
                    allowed_sources=(VISUAL,),
                ),
                replace(rules[2], feature_key="visual.beta", weight_milli=500),
            ),
        )
    with pytest.raises(ValueError, match="canonically sorted"):
        ScoringProfile("profile", "1.0.0", tuple(reversed(rules)))


def test_source_modality_range_extra_duplicate_and_candidate_duplicate_fail_closed():
    base = observations()[0]
    cases = (
        replace(base, modality=FeatureModality.AUDIO),
        replace(base, provenance=provenance(AUDIO)),
        replace(base, raw_value=101),
        replace(base, feature_key="visual.unregistered"),
    )
    for invalid in cases:
        with pytest.raises(ValueError):
            compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (candidate(rows=(invalid, observations()[1])),))
    with pytest.raises(ValueError, match="duplicate feature"):
        compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (candidate(rows=(base, base, observations()[1])),))
    with pytest.raises(ValueError, match="candidate_id values must be unique"):
        compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (candidate(), candidate()))


def test_enum_names_and_untyped_rows_cannot_launder_current_validity():
    with pytest.raises(ValueError, match="EvidenceValidity"):
        FeatureProvenance(VISUAL, SHA_A, "row-1", SHA_B, "CURRENT_VALID")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="FeatureModality"):
        replace(observations()[0], modality="VISUAL")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="FeaturePolarity"):
        replace(profile().rules[0], polarity="INVERSE")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="FeatureObservation"):
        CandidateFeatureInput(CANDIDATE_A, 0, 1, ("not-an-observation",))  # type: ignore[arg-type]


def test_caps_and_digest_tampering_fail_closed():
    with pytest.raises(ValueError, match="256-entry cap"):
        CandidateFeatureInput(CANDIDATE_A, 0, 1, tuple(observations()[0] for _ in range(257)))
    payload = compile_multimodal_scores(ASSET_ID, SHA_C, profile(), (candidate(),)).to_dict()
    payload["candidate_scores"][0]["composite_score_milli"] = 999
    with pytest.raises(ValueError, match="does not match"):
        verify_multimodal_scoring_manifest_hash(payload)


def test_public_contract_has_no_effectful_input_surface_or_imports():
    parameters = inspect.signature(compile_multimodal_scores).parameters
    assert set(parameters) == {"source_asset_id", "source_edit_plan_sha256", "profile", "candidates"}
    source = inspect.getsource(__import__("ai_video_production.multimodal_scoring", fromlist=["*"]))
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint({"subprocess", "pathlib", "requests", "urllib", "socket", "os"})
    assert set(parameters).isdisjoint({"path", "media_path", "raw_bytes", "callback", "runner", "handle"})
