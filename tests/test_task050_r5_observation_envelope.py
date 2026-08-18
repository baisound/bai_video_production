from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_observation_envelope import (
    DbDObservationEnvelope,
    DbDObservationType,
    ObservationProvenance,
    heartbeat_to_observation,
    serialize_observations_csv,
    serialize_observations_jsonl,
)


def provenance():
    return ObservationProvenance(
        workspace_id="dbdws-123",
        runtime_profile_id="default",
        hud_profile_id="dbd-calibrated",
        hud_profile_version=3,
        roi_id="heartbeat_hud",
        detector_version="heartbeat-baseline-v1",
        anchor_offset_x_px=-2,
        anchor_offset_y_px=1,
        knowledge_revision_refs=("killer-rev-1",),
    )


def test_heartbeat_observation_keeps_fact_separate_from_distance():
    item = heartbeat_to_observation(
        observation_id="obs-heartbeat-1",
        frame_index=100,
        active=True,
        intensity_milli=840,
        trend="RISING",
        confidence_milli=930,
        provenance=provenance(),
    )
    payload = item.to_dict()
    assert payload["state"] == "ACTIVE"
    assert payload["intensity_milli"] == 840
    assert "distance" not in payload
    assert payload["provenance"]["anchor_offset_x_px"] == -2


def test_hidden_perk_is_not_empty_identity():
    item = DbDObservationEnvelope(
        observation_id="obs-perk-1",
        observation_type=DbDObservationType.PERK,
        frame_start=20,
        frame_end_exclusive=21,
        confidence_milli=980,
        provenance=ObservationProvenance(
            workspace_id="dbdws-123",
            runtime_profile_id="default",
            hud_profile_id="p",
            hud_profile_version=1,
            roi_id="perk_slot_0",
            detector_version="perk-v1",
        ),
        visibility=HudVisibility.HIDDEN,
        entity_id=None,
    )
    assert item.visibility is HudVisibility.HIDDEN
    assert item.entity_id is None


def test_csv_and_jsonl_include_provenance():
    item = heartbeat_to_observation(
        observation_id="obs-heartbeat-1",
        frame_index=100,
        active=True,
        intensity_milli=840,
        trend="RISING",
        confidence_milli=930,
        provenance=provenance(),
    )
    csv_text = serialize_observations_csv((item,))
    assert "workspace_id" in csv_text
    assert "heartbeat_hud" in csv_text
    jsonl = serialize_observations_jsonl((item,)).decode("utf-8")
    assert '"workspace_id":"dbdws-123"' in jsonl
    assert '"intensity_milli":840' in jsonl


def test_invalid_intensity_fails_closed():
    try:
        heartbeat_to_observation(
            observation_id="obs",
            frame_index=1,
            active=True,
            intensity_milli=1001,
            trend="RISING",
            confidence_milli=900,
            provenance=provenance(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid heartbeat intensity must fail")
