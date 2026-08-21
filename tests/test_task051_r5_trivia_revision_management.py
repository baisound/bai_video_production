from ai_video_production.dbd_commentary_knowledge import (
    DbDTriviaStore,
    TriviaStatus,
)
from ai_video_production.dbd_perk_knowledge import PerkEnvironment

def test_revise_demotes_to_candidate_unless_human_verifies(tmp_path):
    store=DbDTriviaStore(tmp_path/"trivia.sqlite3")
    first=store.create_manual(title="A",text="本文です。",verify=True)
    revised=store.revise(
        first.trivia_id,
        title="A2",
        text="編集した本文です。",
        source_ref="manual://owner",
        category="GENERAL",
        environment=PerkEnvironment.LIVE,
        verify=False,
    )
    assert revised.revision==2
    assert revised.status is TriviaStatus.CANDIDATE
    assert revised.verified_at is None

def test_duplicate_is_new_candidate_and_supersede_preserves_history(tmp_path):
    store=DbDTriviaStore(tmp_path/"trivia.sqlite3")
    first=store.create_manual(title="A",text="本文です。",verify=True)
    dup=store.duplicate(first.trivia_id)
    assert dup.trivia_id!=first.trivia_id
    assert dup.status is TriviaStatus.CANDIDATE
    deleted=store.supersede(first.trivia_id)
    assert deleted.status is TriviaStatus.SUPERSEDED
    assert store.latest(first.trivia_id).revision==2
