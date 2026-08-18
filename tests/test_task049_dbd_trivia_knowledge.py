from ai_video_production.canonical_game_event import GameEventType
from ai_video_production.dbd_commentary_knowledge import DbDTriviaStore, TriviaCandidateMiner, TriviaStatus
from ai_video_production.dbd_perk_knowledge import PerkEnvironment


def test_manual_trivia_candidate_verify_and_query(tmp_path):
    store=DbDTriviaStore(tmp_path/'trivia.sqlite3')
    entry=store.create_manual(title='窓枠', text='窓枠を使うとチェイス中に距離を作れる場面があります。', tags=('CHASE',), event_types=(GameEventType.WINDOW_VAULT,), verify=False)
    assert entry.status is TriviaStatus.CANDIDATE
    assert store.query_verified(game_version='9.0.0', environment=PerkEnvironment.LIVE, event_type=GameEventType.WINDOW_VAULT) == ()
    store.verify(entry.trivia_id)
    rows=store.query_verified(game_version='9.0.0', environment=PerkEnvironment.LIVE, event_type=GameEventType.WINDOW_VAULT, tags=('CHASE',))
    assert rows[0].trivia_id == entry.trivia_id


def test_commentary_miner_never_auto_verifies(tmp_path):
    store=DbDTriviaStore(tmp_path/'trivia.sqlite3')
    rows=TriviaCandidateMiner().capture(store,text='ちなみにこのパークは条件を満たすと便利です。普通の挨拶です。',source_ref='commentary://x')
    assert len(rows) == 1
    assert rows[0].status is TriviaStatus.CANDIDATE

from ai_video_production.game_commentary import CommentaryPlanner, CommentaryClaimKind
from ai_video_production.canonical_game_event import CanonicalGameEvent, EventConfirmationState, EventReviewStatus, GameEnvironment, GamePerspective
from ai_video_production.game_event_evidence import SourceFrameRange
from ai_video_production.ids import IdKind, generate_id


def test_commentary_planner_can_include_verified_contextual_trivia(tmp_path):
    store=DbDTriviaStore(tmp_path/'trivia.sqlite3')
    store.create_manual(title='vault tip', text='窓枠はチェイス中に距離を作る選択肢になります。', event_types=(GameEventType.WINDOW_VAULT,), verify=True)
    event=CanonicalGameEvent(
        match_id=generate_id(IdKind.GAME_MATCH), revision=1, event_type=GameEventType.WINDOW_VAULT, source_range=SourceFrameRange(10,20),
        game_version='9.0.0', environment=GameEnvironment.LIVE, perspective=GamePerspective.SURVIVOR, state={},
        evidence_refs=(generate_id(IdKind.GAME_EVIDENCE),), confidence_milli=950, confirmation_state=EventConfirmationState.CONFIRMED,
        review_status=EventReviewStatus.HUMAN_APPROVED,
    )
    plan=CommentaryPlanner().plan(event,trivia_store=store)
    assert any(f.kind is CommentaryClaimKind.TRIVIA for f in plan.facts)

from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment


def test_transcript_manifest_mines_candidate_with_segment_provenance(tmp_path):
    store = DbDTriviaStore(tmp_path / 'trivia.sqlite3')
    manifest = TranscriptManifest(
        source_asset_id=generate_id(IdKind.ASSET),
        language='ja-JP',
        provider_id='local-asr',
        model_id='test-model',
        segments=(
            TranscriptSegment('seg-000001', 0, 1_000_000, 'ちなみにフック救助の条件は場面によって確認が必要です。'),
            TranscriptSegment('seg-000002', 1_000_000, 2_000_000, 'よろしくお願いします。'),
        ),
    )
    rows = TriviaCandidateMiner().capture_transcript_manifest(store, manifest)
    assert len(rows) == 1
    assert rows[0].status is TriviaStatus.CANDIDATE
    assert rows[0].source_ref == f'transcript://{manifest.source_asset_id}/seg-000001'
