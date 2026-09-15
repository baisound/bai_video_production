from ai_video_production.voice_recording_coverage import *

def seg(i,seconds,style='NORMAL',emotion='NORMAL',q=True,a=True,sha=None):
    return RecordingCoverageSegment(f's{i}',sha or ('sha256:'+f'{i:064x}'),seconds*48_000,style,emotion,q,a,True)

def test_arbitrary_target_and_style_emotion_percentages():
    target=RecordingCoverageTarget.from_seconds(12*3600,style_target_seconds={'NORMAL':3600,'SPORTS_COMMENTARY':1800},emotion_target_seconds={'NORMAL':3600,'EXCITED':1800})
    cov=compute_recording_coverage([seg(1,1800),seg(2,900,'SPORTS_COMMENTARY','EXCITED')],target)
    assert cov.overall.percentage==6.25
    assert {x.axis_id:x.percentage for x in cov.styles}=={'NORMAL':50.0,'SPORTS_COMMENTARY':50.0}
    assert {x.axis_id:x.percentage for x in cov.emotions}=={'EXCITED':50.0,'NORMAL':50.0}

def test_quality_approval_and_content_dedup_drive_usable_samples():
    same='sha256:'+'a'*64
    cov=compute_recording_coverage([seg(1,10,sha=same),seg(2,10,sha=same),seg(3,10,q=False),seg(4,10,a=False)],RecordingCoverageTarget.from_seconds(100))
    assert cov.raw_samples==40*48_000
    assert cov.usable_samples==10*48_000
    assert cov.duplicate_samples==10*48_000
    assert cov.rejected_samples==10*48_000
    assert cov.unapproved_samples==10*48_000
    assert cov.overall.percentage==10.0
