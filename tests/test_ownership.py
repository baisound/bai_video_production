import pytest
from ai_video_production import ActorKind, TimelineOwner, TimelineRef, TimelineWriteGuard
from ai_video_production.errors import ProductError

def test_automation_cannot_write_human_timeline():
    ref=TimelineRef("EDITOR_WORK",TimelineOwner.HUMAN,3)
    with pytest.raises(ProductError) as exc: TimelineWriteGuard.authorize(ref,actor=ActorKind.AUTOMATION,expected_revision=3)
    assert exc.value.code == "ERR_AUTH_TIMELINE_PROTECTED"

def test_stale_revision_fails_closed():
    ref=TimelineRef("AUTO_ASSEMBLY_v1",TimelineOwner.AUTOMATION,4)
    with pytest.raises(ProductError) as exc: TimelineWriteGuard.authorize(ref,actor=ActorKind.AUTOMATION,expected_revision=3)
    assert exc.value.code == "ERR_STATE_STALE_REVISION"

def test_shared_timeline_accepts_both_actors():
    ref=TimelineRef("REVIEW_STAGING",TimelineOwner.SHARED,1)
    for actor in ActorKind: TimelineWriteGuard.authorize(ref,actor=actor,expected_revision=1)
