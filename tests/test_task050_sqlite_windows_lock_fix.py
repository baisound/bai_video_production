from pathlib import Path
import sqlite3
import tempfile

import ai_video_production.dbd_entity_aliases as alias_module
from ai_video_production.canonical_game_event import GameKnowledgeKind

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "ai_video_production"

def test_video_and_trivia_ux_contracts_are_still_present():
    text = (SRC / "dbd_training_studio.py").read_text(encoding="utf-8")
    assert "学習スロットと正解ゲーム要素" in text
    assert "登録するスロットのゲーム要素を1件以上選択してください。" in text
    assert "1. 全スロットのCropを確認" in text
    assert 'title="豆知識に関連するゲーム要素を選択"' in text
    assert 'trivia_notebook.add(mining_tab, text="動画から候補を作る")' in text

def test_alias_catalog_functional_count_put_search():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "aliases.sqlite"
        catalog = alias_module.EntityAliasCatalog(path)
        assert catalog.count() == 0
        catalog.put(alias_module.EntityAliasRecord(
            entity_id="perk_iron_will",
            knowledge_kind=GameKnowledgeKind.PERK,
            alias_text="アイウィル",
            alias_type=alias_module.EntityAliasType.COMMUNITY_SHORT_NAME,
        ))
        assert catalog.count() == 1
        rows = catalog.search("アイウィル", knowledge_kind=GameKnowledgeKind.PERK, verified_only=False)
        assert len(rows) == 1 and rows[0].entity_id == "perk_iron_will"
    assert not path.exists()

def test_every_sqlite_connection_is_explicitly_closed(monkeypatch):
    real_connect = sqlite3.connect
    proxies = []
    class Proxy:
        def __init__(self, conn):
            self.conn=conn
            self.closed=False
        def __getattr__(self,name):
            return getattr(self.conn,name)
        def __enter__(self):
            self.conn.__enter__()
            return self
        def __exit__(self,exc_type,exc,tb):
            return self.conn.__exit__(exc_type,exc,tb)
        def close(self):
            self.closed=True
            self.conn.close()
    def tracked_connect(*args,**kwargs):
        proxy=Proxy(real_connect(*args,**kwargs))
        proxies.append(proxy)
        return proxy
    monkeypatch.setattr(alias_module.sqlite3,"connect",tracked_connect)
    with tempfile.TemporaryDirectory() as td:
        catalog=alias_module.EntityAliasCatalog(Path(td)/"aliases.sqlite")
        catalog.count()
        catalog.put(alias_module.EntityAliasRecord(
            entity_id="perk_iron_will",
            knowledge_kind=GameKnowledgeKind.PERK,
            alias_text="アイウィル",
            alias_type=alias_module.EntityAliasType.COMMUNITY_SHORT_NAME,
        ))
        catalog.search("アイウィル",verified_only=False)
        catalog.resolve_unique("アイウィル",verified_only=False)
    assert proxies and all(proxy.closed for proxy in proxies)
