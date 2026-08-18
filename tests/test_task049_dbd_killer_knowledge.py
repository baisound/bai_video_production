from pathlib import Path
import hashlib
from ai_video_production.dbd_killer_knowledge import (
    DbDKillerKnowledgeStore, KillerKnowledgeKind, KillerKnowledgeRevision,
    KillerKnowledgeSource, KillerKnowledgeStatus, KillerPowerVisualRecognizer,
)
from ai_video_production.dbd_perk_knowledge import PerkEnvironment
from ai_video_production.dbd_vision_slices import GrayImage, ReferenceSliceIndex


def _pgm(path: Path):
    path.write_bytes(b'P5\n9 8\n255\n'+bytes([0,0,0,0,255,255,255,255,255]*8)); return path


def test_killer_power_store_requires_provenance_and_resolves_patch(tmp_path):
    store=DbDKillerKnowledgeStore(tmp_path/'killer.sqlite3')
    src=KillerKnowledgeSource('src-bhvr','BHVR_OFFICIAL','https://example.invalid/killer', hashlib.sha256(b'k').hexdigest())
    store.put_source(src)
    rev=KillerKnowledgeRevision('killer_example','KREV-1',KillerKnowledgeKind.KILLER,'例','Example Killer',PerkEnvironment.LIVE,'9.0.0',None,KillerKnowledgeStatus.VERIFIED,src.source_id)
    store.put_revision(rev)
    store.add_alias('killer_example','例')
    assert store.resolve_alias('例') == 'killer_example'
    assert store.lookup('killer_example',game_version='9.1.0').revision_id == 'KREV-1'


def test_killer_visual_recognizer_uses_reference_index(tmp_path):
    image=_pgm(tmp_path/'killer.pgm')
    index=ReferenceSliceIndex.train_from_pgm(index_id='killer', samples=[('killer_example',image)])
    result=KillerPowerVisualRecognizer(index,acceptance_milli=700).recognize(GrayImage.read_pgm(image))
    assert result.entity_id == 'killer_example'
    assert result.kind is KillerKnowledgeKind.KILLER

from ai_video_production.canonical_game_event import CanonicalGameEvent, EventConfirmationState, EventReviewStatus, GameEnvironment, GameEventType, GamePerspective
from ai_video_production.game_commentary import CommentaryClaimKind, CommentaryPlanner
from ai_video_production.game_event_evidence import SourceFrameRange
from ai_video_production.ids import IdKind, generate_id


def test_commentary_planner_resolves_killer_knowledge_ref(tmp_path):
    store=DbDKillerKnowledgeStore(tmp_path/'killer-commentary.sqlite3')
    src=KillerKnowledgeSource('src-bhvr-2','BHVR_OFFICIAL','https://example.invalid/killer2', hashlib.sha256(b'k2').hexdigest())
    store.put_source(src)
    rev=KillerKnowledgeRevision('killer_example','KREV-2',KillerKnowledgeKind.KILLER,'例のキラー','Example Killer',PerkEnvironment.LIVE,'9.0.0',None,KillerKnowledgeStatus.VERIFIED,src.source_id,description_ja='罠を使うキラーです。')
    store.put_revision(rev)
    event=CanonicalGameEvent(
        match_id=generate_id(IdKind.GAME_MATCH), revision=1, event_type=GameEventType.HOOK,
        source_range=SourceFrameRange(10,20), game_version='9.1.0', environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR, state={}, evidence_refs=(generate_id(IdKind.GAME_EVIDENCE),),
        knowledge_refs=(rev.to_knowledge_ref(),), confidence_milli=950,
        confirmation_state=EventConfirmationState.CONFIRMED, review_status=EventReviewStatus.HUMAN_APPROVED,
    )
    plan=CommentaryPlanner().plan(event,killer_store=store)
    kinds={fact.kind for fact in plan.facts}
    assert CommentaryClaimKind.KILLER_NAME in kinds
    assert CommentaryClaimKind.KILLER_DESCRIPTION in kinds

import json
import sqlite3
import pytest
from ai_video_production.errors import ProductError


def test_killer_knowledge_source_and_revision_ids_are_immutable(tmp_path):
    store = DbDKillerKnowledgeStore(tmp_path / 'immutable.sqlite3')
    source = KillerKnowledgeSource('src-immutable', 'BHVR_OFFICIAL', 'https://example.invalid/a', hashlib.sha256(b'a').hexdigest())
    store.put_source(source)
    with pytest.raises(ProductError) as source_error:
        store.put_source(KillerKnowledgeSource('src-immutable', 'BHVR_OFFICIAL', 'https://example.invalid/b', hashlib.sha256(b'b').hexdigest()))
    assert source_error.value.code == 'ERR_KILLER_KNOWLEDGE_SOURCE_IMMUTABLE'

    revision = KillerKnowledgeRevision('killer_example', 'KREV-IMMUTABLE', KillerKnowledgeKind.KILLER, '例', 'Example Killer', PerkEnvironment.LIVE, '9.0.0', None, KillerKnowledgeStatus.VERIFIED, source.source_id)
    store.put_revision(revision)
    changed = KillerKnowledgeRevision('killer_example', 'KREV-IMMUTABLE', KillerKnowledgeKind.KILLER, '変更', 'Changed Killer', PerkEnvironment.LIVE, '9.0.0', None, KillerKnowledgeStatus.VERIFIED, source.source_id)
    with pytest.raises(ProductError) as revision_error:
        store.put_revision(changed)
    assert revision_error.value.code == 'ERR_KILLER_KNOWLEDGE_REVISION_IMMUTABLE'


def test_killer_knowledge_lookup_detects_payload_tamper(tmp_path):
    store = DbDKillerKnowledgeStore(tmp_path / 'tamper.sqlite3')
    source = KillerKnowledgeSource('src-tamper', 'BHVR_OFFICIAL', 'https://example.invalid/tamper', hashlib.sha256(b't').hexdigest())
    store.put_source(source)
    revision = KillerKnowledgeRevision('killer_example', 'KREV-TAMPER', KillerKnowledgeKind.KILLER, '例', 'Example Killer', PerkEnvironment.LIVE, '9.0.0', None, KillerKnowledgeStatus.VERIFIED, source.source_id)
    store.put_revision(revision)
    with sqlite3.connect(store.path) as conn:
        payload = json.loads(conn.execute("SELECT payload_json FROM revision WHERE revision_id='KREV-TAMPER'").fetchone()[0])
        payload['name_en'] = 'Tampered'
        conn.execute("UPDATE revision SET payload_json=? WHERE revision_id='KREV-TAMPER'", (json.dumps(payload, ensure_ascii=False, separators=(',', ':')),))
    with pytest.raises(ProductError) as error:
        store.lookup('killer_example', game_version='9.1.0')
    assert error.value.code == 'ERR_KILLER_KNOWLEDGE_INTEGRITY'
