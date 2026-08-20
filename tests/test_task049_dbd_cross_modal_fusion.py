from ai_video_production.canonical_game_event import GameEventType
from ai_video_production.dbd_cross_modal_fusion import DBDCrossModalFusion, FusionModality, FusionObservation
from ai_video_production.game_event_evidence import SourceFrameRange


def test_cross_modal_fusion_rewards_independent_agreement():
    observations=[
        FusionObservation(GameEventType.INJURY,FusionModality.HUD,910,SourceFrameRange(100,110),'e1'),
        FusionObservation(GameEventType.INJURY,FusionModality.ASR,760,SourceFrameRange(105,112),'e2'),
        FusionObservation(GameEventType.INJURY,FusionModality.VISION,850,SourceFrameRange(103,111),'e3'),
    ]
    decision=DBDCrossModalFusion().fuse(observations)
    assert decision.event_type is GameEventType.INJURY
    assert decision.confidence_milli >= 850
    assert len(decision.modalities) == 3


def test_single_asr_is_not_auto_confirmed():
    decision=DBDCrossModalFusion().fuse([FusionObservation(GameEventType.HOOK,FusionModality.ASR,950,SourceFrameRange(1,2),'e')])
    assert 'SINGLE_WEAK_MODALITY_REQUIRES_REVIEW' in decision.reason_codes
