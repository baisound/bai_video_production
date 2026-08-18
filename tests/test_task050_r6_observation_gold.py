from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_observation_envelope import DbDObservationEnvelope, DbDObservationType, ObservationProvenance
from ai_video_production.dbd_observation_gold import HudObservationGoldCase, HudObservationGoldEvaluator

def obs(frame, visibility, entity_id):
    return DbDObservationEnvelope(
        observation_id=f"obs-{frame}", observation_type=DbDObservationType.PERK,
        frame_start=frame, frame_end_exclusive=frame+1, confidence_milli=900,
        provenance=ObservationProvenance("dbdws-1","default","hud-v1",1,"perk_slot_0","perk-v1"),
        visibility=visibility, entity_id=entity_id)

def test_hidden_does_not_reduce_identity_accuracy():
    cases=(
      HudObservationGoldCase("visible","PERK",10,HudVisibility.VISIBLE,"perk_iron_will",False,"human://owner"),
      HudObservationGoldCase("hidden","PERK",20,HudVisibility.HIDDEN,None,True,"human://owner"),
    )
    r=HudObservationGoldEvaluator.evaluate(cases,(obs(10,HudVisibility.VISIBLE,"perk_iron_will"),obs(20,HudVisibility.HIDDEN,None)))
    assert r.visibility_accuracy_milli==1000
    assert r.identity_evaluable_count==1
    assert r.identity_accuracy_milli==1000
    assert r.hidden_detection_accuracy_milli==1000
