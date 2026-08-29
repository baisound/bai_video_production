from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from ai_video_production.montage_contracts import admit_montage_resolve_handoff
from ai_video_production.montage_learning_bridge_application import (
    MontageLearningBridgeApplication,
)
from ai_video_production.montage_learning_bridge_contracts import (
    EXACT_LINEAGE_VERIFIED,
    REVIEW_REQUIRED,
    validate_exact_evidence_delivery,
)
from ai_video_production.montage_learning_connector_readiness import (
    ProfileSourceBinding,
    publish_prebuilt_advisory_profile,
    validate_prebuilt_advisory_profile,
)
from ai_video_production.montage_learning_file_bridge import recover_current_profile
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.subtitles import (
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
)
from ai_video_production.task056_product_integration import (
    Task056SpeechCueProductApplication,
)
from ai_video_production.timebase import FrameRate
from test_task055_montage_contract_recovery import _handoff
from test_task058_montage_learning_adapter_e2e import _profile
from test_task058_montage_learning_bridge_contracts import OWNER_SCOPE_HASH
from test_task058_montage_learning_file_bridge import (
    _canonical_store,
    _exact_fixture,
    _layout,
)


def _task056_transcript() -> TranscriptManifest:
    return TranscriptManifest(
        "ASSET-00000000000000000000000000",
        "ja",
        "fixture-asr",
        "fixture-model",
        (
            TranscriptSegment(
                "segment-001",
                0,
                2_000_000,
                "チェイス、チェイス",
                words=(
                    TranscriptWord(100_000, 400_000, "チェイス", 0.93),
                    TranscriptWord(1_100_000, 1_400_000, "チェイス", 0.40),
                ),
            ),
        ),
        True,
    )


def test_task055_task056_bridge_receipt_profile_and_resolve_handoff_fixture_e2e(
    tmp_path: Path,
) -> None:
    canonical_store = _canonical_store(tmp_path)
    project_root = canonical_store.project_root

    cue_application = Task056SpeechCueProductApplication(
        project_root=project_root,
        project_id="proj-test",
        output_directory=project_root / "private" / "transcription" / "semantic-cues",
        source_frame_rate=FrameRate(30, 1),
    )
    cue_result = cue_application.generate(
        project_id="proj-test",
        transcript=_task056_transcript(),
    )
    assert cue_result["confirmed_count"] == 1
    assert cue_result["review_count"] == 1
    assert cue_result["transcript_text_exposed"] is False
    assert cue_result["canonical_timeline"] is False
    assert cue_result["auto_apply_authorized"] is False
    cue_projection_path = (
        project_root
        / "private"
        / "transcription"
        / "semantic-cues"
        / "montage-semantic-audio-cues.json"
    )
    cue_projection = json.loads(cue_projection_path.read_text(encoding="utf-8"))
    assert cue_projection["projection_version"] == "1.0.0"
    assert cue_projection["source_asset_id"] == _task056_transcript().source_asset_id
    assert cue_projection["confirmed_count"] == 1
    assert cue_projection["review_count"] == 1
    assert cue_projection["projection_mode"] == "CONFIRMED_ONLY"
    assert cue_projection["canonical_timeline"] is False
    assert cue_projection["auto_apply_authorized"] is False

    layout = _layout(tmp_path / "bridge-case")
    staged_path, exact_delivery, coordinates = _exact_fixture(layout, canonical_store)
    delivery_before = deepcopy(exact_delivery)
    exact_candidate = validate_exact_evidence_delivery(
        exact_delivery,
        expected_owner_scope_hash=OWNER_SCOPE_HASH,
    )
    assert exact_candidate.validation_state == EXACT_LINEAGE_VERIFIED
    assert exact_candidate.review_state == REVIEW_REQUIRED
    candidate_projection = exact_candidate.to_dict()
    assert candidate_projection["canonical_admission_authorized"] is False
    assert candidate_projection["canonical_store_write_authorized"] is False

    imported = MontageLearningBridgeApplication(
        layout=layout,
        canonical_port=canonical_store,
    ).import_path(staged_path, exact_coordinates=coordinates)
    assert imported.status == "ACCEPTED"
    assert imported.receipt_path.is_file()
    receipt = json.loads(imported.receipt_path.read_text(encoding="utf-8"))
    assert receipt["source_record_id"] == exact_delivery["record_id"]
    assert receipt["source_sha256"] == exact_delivery["evidence_sha256"]
    verified_receipt = canonical_store.get_verified_receipt(
        receipt_sha256=receipt["receipt_sha256"]
    )
    assert verified_receipt.to_public_projection()["canonical_currentness_verified"] is True

    published_profile = publish_prebuilt_advisory_profile(
        layout,
        _profile(),
        source_binding=ProfileSourceBinding.bound_isolated_fixture(),
    )
    assert published_profile.status == "PUBLISHED"
    assert published_profile.written is True
    assert published_profile.production_profile_source_bound is False
    assert published_profile.semantic_projection_generated is False
    assert published_profile.timeline_mutation_authorized is False
    assert published_profile.resolve_write_authorized is False
    recover_current_profile(layout)
    loaded_profile = validate_prebuilt_advisory_profile(
        json.loads(layout.current_profile.read_text(encoding="utf-8"))
    )
    assert loaded_profile["advisory_only"] is True
    assert loaded_profile["canonical_timeline"] is False
    assert loaded_profile["auto_apply_authorized"] is False
    assert loaded_profile["profile_sha256"] == published_profile.profile_sha256

    proposal = exact_delivery["proposal"]
    approved_plan = exact_delivery["approved_plan"]
    assert isinstance(proposal, dict)
    assert isinstance(approved_plan, dict)
    resolve_handoff = _handoff(proposal, approved_plan)
    admitted_handoff = admit_montage_resolve_handoff(
        proposal,
        approved_plan,
        resolve_handoff,
    )
    handoff_body = admitted_handoff.to_dict()
    assert handoff_body["task_owner"] == "TASK-055"
    assert handoff_body["resolve_write_authorized"] is False
    assert handoff_body["runtime_qa_status"] == "NOT_RUN"
    assert handoff_body["source_proposal_sha256"] == proposal["proposal_sha256"]
    assert handoff_body["source_approved_plan_sha256"] == approved_plan["plan_sha256"]
    handoff_unsigned = {
        key: value
        for key, value in handoff_body.items()
        if key != "handoff_sha256"
    }
    assert handoff_body["handoff_sha256"] == sha256_bytes(
        canonical_json_bytes(handoff_unsigned)
    )

    assert exact_delivery == delivery_before
    assert cue_result["canonical_timeline"] is False
    assert cue_result["auto_apply_authorized"] is False
    assert handoff_body["resolve_write_authorized"] is False
