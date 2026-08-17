from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.voice_model_builder_beginner_client import (
    MAX_WORKFLOW_JSON_BYTES,
    BeginnerClientSnapshot,
    assert_no_forbidden_effect_surface,
    build_demo_snapshot,
    compile_beginner_snapshot_from_workflow_json,
    public_projection,
    render_beginner_html,
    validate_snapshot,
)
from ai_video_production.voice_model_builder_workflow import add_record_digest
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "voice-model-builder-beginner-client.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "voice-model-builder-beginner-client.schema.json"


def _workflow_json_bytes(
    *, training_started: bool = False, state: str = "RECORDINGS_REVIEW_REQUIRED",
) -> bytes:
    source = add_record_digest(
        {
            "record_type": "CanonicalSourceBinding",
            "contract_state": "CANONICAL_REF_NOT_PROVIDED",
            "source_kind": "OBS_CAPTURE_SESSION",
            "canonical_ref": None,
            "canonical_revision": None,
            "canonical_sha256": None,
            "current_valid": None,
            "evaluated_at": None,
        },
        "binding_sha256",
    )
    workflow = add_record_digest(
        {
            "record_type": "VerticalSliceWorkflowRevision",
            "workflow_id": "workflow:import-test",
            "revision": 1,
            "parent_workflow_sha256": None,
            "project_id": "project:import-test",
            "source_bindings": [source],
            "state": state,
            "ordered_cue_sha256": [],
            "master_candidate_sha256": None,
            "reason_codes": ["SYNTHETIC_TEST_ONLY"],
            "created_at": "2026-08-17T00:00:00Z",
            "dataset_effect_started": False,
            "training_started": training_started,
            "render_started": False,
        },
        "workflow_sha256",
    )
    return json.dumps(workflow, ensure_ascii=False, separators=(",", ":")).encode()


def test_demo_snapshot_matches_schema_and_is_deterministic() -> None:
    first = build_demo_snapshot().to_dict()
    second = build_demo_snapshot().to_dict()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(first)
    assert BeginnerClientSnapshot(first).canonical_json() == BeginnerClientSnapshot(second).canonical_json()
    assert len(first["steps"]) == 12
    assert first["current_step"] == 2


def test_bounded_workflow_json_compiles_to_the_same_deterministic_projection() -> None:
    kwargs = {
        "payload": _workflow_json_bytes(),
        "locale": "ja",
        "created_at": "2026-08-17T01:00:00Z",
    }
    first = compile_beginner_snapshot_from_workflow_json(**kwargs).to_dict()
    second = compile_beginner_snapshot_from_workflow_json(**kwargs).to_dict()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(first)
    assert first == second
    assert first["snapshot_id"].startswith("client-snapshot:workflow:")
    assert first["training_started"] is False
    assert first["audio_access_started"] is False


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"", "between 1 byte"),
        (b"x" * (MAX_WORKFLOW_JSON_BYTES + 1), "between 1 byte"),
        (b"\xff", "valid UTF-8"),
        (b"\xef\xbb\xbf{}", "byte-order mark"),
        (b"[]", "root must be an object"),
        (b'{"record_type":"one","record_type":"two"}', "duplicate key"),
    ],
    ids=("empty", "over-limit", "invalid-utf8", "bom", "non-object", "duplicate-key"),
)
def test_workflow_json_import_rejects_unbounded_ambiguous_or_noncanonical_input(
    payload: bytes, message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        compile_beginner_snapshot_from_workflow_json(
            payload=payload, locale="ja", created_at="2026-08-17T01:00:00Z",
        )


def test_workflow_json_import_cannot_turn_effect_flags_on() -> None:
    with pytest.raises(ValueError, match="training_started"):
        compile_beginner_snapshot_from_workflow_json(
            payload=_workflow_json_bytes(training_started=True),
            locale="ja",
            created_at="2026-08-17T01:00:00Z",
        )


def test_schema_mirror_is_byte_exact() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


def test_public_projection_hides_workflow_coordinates() -> None:
    value = public_projection(build_demo_snapshot().to_dict())
    rendered = json.dumps(value, ensure_ascii=False)
    assert "workflow_sha256" not in rendered
    assert "canonical_ref" not in rendered
    assert "workflow_state" not in rendered
    assert "未確認" not in rendered or "開始しません" in rendered
    assert all(step["operation_effect_authorized"] is False for step in value["steps"])
    assert value["progress_completed"] == 1
    assert value["progress_total"] == 12
    assert value["current_summary"] == "録音の確認が必要です"
    assert value["next_action"]
    assert value["client_state_label"] == "次の対応が必要です"


def test_html_is_beginner_friendly_and_has_no_action_surface() -> None:
    html = render_beginner_html(build_demo_snapshot().to_dict())
    assert "音声モデル作成ガイド" in html
    assert "学習・音声生成を開始しません" in html
    assert "録音の確認が必要です" in html
    assert "次にすること" in html
    assert "次の対応が必要です" in html
    assert "ACTION_REQUIRED" not in html
    assert html.count("<li class=") == 12
    assert "<button" not in html
    assert "C:\\" not in html and "E:\\" not in html


@pytest.mark.parametrize(
    "field",
    [
        "execution_started", "dataset_effect_started", "training_started",
        "model_inference_started", "audio_access_started", "publication_started",
    ],
)
def test_effect_flags_cannot_be_forged(field: str) -> None:
    value = build_demo_snapshot().to_dict()
    value[field] = True
    with pytest.raises(ValueError, match="no-effect boundary"):
        validate_snapshot(value)


def test_step_order_and_effect_authority_are_closed() -> None:
    value = build_demo_snapshot().to_dict()
    value["steps"][0]["step_key"] = "START_TRAINING"
    with pytest.raises(ValueError, match="order"):
        validate_snapshot(value)
    value = build_demo_snapshot().to_dict()
    value["steps"][0]["operation_effect_authorized"] = True
    with pytest.raises(ValueError, match="cannot authorize"):
        validate_snapshot(value)


def test_unknown_state_cannot_be_projected_as_complete() -> None:
    value = build_demo_snapshot().to_dict()
    value["workflow_state"] = "UNKNOWN"
    value["client_state"] = "COMPLETE"
    with pytest.raises(ValueError):
        validate_snapshot(value)


def test_tamper_and_unknown_fields_fail_closed() -> None:
    value = build_demo_snapshot().to_dict()
    value["current_step"] = 12
    with pytest.raises(ValueError, match="current_step does not match"):
        validate_snapshot(value)
    value = build_demo_snapshot().to_dict()
    value["raw_audio_path"] = "owner.wav"
    with pytest.raises(ValueError, match="incomplete or unknown"):
        validate_snapshot(value)


def test_rehashed_progress_or_unknown_workflow_state_cannot_forge_friendly_readiness() -> None:
    value = build_demo_snapshot().to_dict()
    value["steps"][-1]["state"] = "COMPLETE"
    value["steps"][-1]["reason_codes"] = []
    value["snapshot_sha256"] = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != "snapshot_sha256"})
    )
    with pytest.raises(ValueError, match="step state does not match"):
        public_projection(value)

    value = build_demo_snapshot().to_dict()
    value["workflow_state"] = "UNREVIEWED_VENDOR_STATE"
    value["snapshot_sha256"] = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != "snapshot_sha256"})
    )
    with pytest.raises(ValueError, match="workflow_state is invalid"):
        public_projection(value)


def test_english_projection_is_supported() -> None:
    value = public_projection(build_demo_snapshot(locale="en").to_dict())
    assert value["locale"] == "en"
    assert value["steps"][0]["label"] == "Choose recordings"
    assert value["steps"][1]["state_label"] == "Next action needed"
    assert value["current_summary"] == "Recordings need review"
    assert value["next_action"].startswith("Review the recording-quality")
    assert value["safety_notice"].startswith("This screen never")


@pytest.mark.parametrize(
    "workflow_state",
    [
        "RECORDINGS_REVIEW_REQUIRED",
        "DATASET_PROPOSAL_READY",
        "DATASET_ADOPTION_BLOCKED",
        "TRAINING_RECIPE_NOT_VERIFIED",
        "READY_FOR_OWNER_TRAINING_CONFIRMATION",
        "TRAINING_IN_PROGRESS",
        "TRAINING_COMPLETED_ARTIFACT_UNBOUND",
        "MODEL_CANDIDATE_REGISTERED",
        "EVALUATION_PENDING",
        "EVALUATED_CANDIDATE",
        "OWNER_APPROVED",
        "STYLE_CUES_PENDING",
        "MASTER_ASSEMBLY_PENDING",
        "MASTER_REVIEW_REQUIRED",
        "MASTER_ACCEPTED",
        "MASTER_REJECTED",
        "FAILED_KNOWN",
        "UNKNOWN",
    ],
)
@pytest.mark.parametrize("locale", ["ja", "en"])
def test_every_workflow_state_has_localized_summary_action_and_step_states(
    workflow_state: str, locale: str,
) -> None:
    snapshot = compile_beginner_snapshot_from_workflow_json(
        payload=_workflow_json_bytes(state=workflow_state),
        locale=locale,
        created_at="2026-08-17T01:00:00Z",
    ).to_dict()
    value = public_projection(snapshot)
    assert value["current_summary"].strip()
    assert value["next_action"].strip()
    assert value["client_state_label"].strip()
    assert all(step["state_label"].strip() for step in value["steps"])
    assert 0 <= value["progress_completed"] <= value["progress_total"] == 12
    if workflow_state in {"UNKNOWN", "FAILED_KNOWN"}:
        assert value["client_state"] == "BLOCKED"
        assert value["client_state_label"] in {"現在は進められません", "Cannot proceed now"}


def test_no_forbidden_effect_surface() -> None:
    assert_no_forbidden_effect_surface()
