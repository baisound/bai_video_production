from __future__ import annotations

import hashlib
from pathlib import Path

from ai_video_production.dbd_kamigame_collector import (
    ADDONS_URL,
    ITEMS_URL,
    KILLER_PERKS_URL,
    KILLERS_URL,
    MAPS_URL,
    SURVIVOR_PERKS_URL,
    FetchReceipt,
    KamigameDbDKnowledgeCollector,
)


_DUPLICATE_DETAIL = "https://kamigame.jp/dbd/page/shared-killer-detail.html"
_KILLERS = f"""
<html><body><table>
<tr><td><a href='{_DUPLICATE_DETAIL}'>ハグ</a></td><td>移動速度：4.6m/s 脅威範囲：24m 背の高さ：平均</td><td></td></tr>
<tr><td><a href='{_DUPLICATE_DETAIL}'>ヒルビリー</a></td><td>移動速度：4.6m/s 脅威範囲：32m 背の高さ：高い</td><td></td></tr>
</table></body></html>
"""


class CountingClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        blank = "<html><body></body></html>"
        self.pages = {
            SURVIVOR_PERKS_URL: blank,
            KILLER_PERKS_URL: blank,
            KILLERS_URL: _KILLERS,
            ITEMS_URL: blank,
            ADDONS_URL: blank,
            MAPS_URL: '<main id="main" class="article"><article><h1>全マップ一覧</h1></article></main>',
            _DUPLICATE_DETAIL: '<main id="main" class="article"><article><h1>ハグ</h1><h2>特殊能力</h2><p>detail</p></article></main>',
        }

    def fetch_html(self, url: str, *, output_path: Path) -> FetchReceipt:
        self.calls.append(url)
        body = self.pages[url].encode("utf-8")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(body)
        return FetchReceipt(
            url=url,
            path=output_path,
            content_sha256=hashlib.sha256(body).hexdigest(),
            retrieved_at="2026-08-20T00:00:00Z",
            content_type="text/html",
        )


def test_collector_records_stage_timings_and_dedupes_duplicate_detail_url(tmp_path: Path) -> None:
    client = CountingClient()
    manifest = KamigameDbDKnowledgeCollector(tmp_path, client=client, dedupe_within_run=True).collect(
        follow_killer_details=True,
        follow_map_details=False,
    )

    perf = manifest["performance"]
    elapsed = perf["elapsed_seconds"]
    counts = perf["counts"]
    assert elapsed["total"] >= 0
    for key in (
        "source_index_fetch", "candidate_discovery", "detail_page_fetch", "parse",
        "image_fetch", "normalize", "db_upsert", "alias_index_update", "post_process",
    ):
        assert key in elapsed
    assert counts["html_requests"] == 7  # six list pages + one shared detail
    assert counts["html_cache_hits"] == 1
    assert client.calls.count(_DUPLICATE_DETAIL) == 1
    assert counts["detail_pages"] == 2
    assert len(list((tmp_path / "raw" / "killer-details").glob("*.html"))) == 2


def test_dedupe_can_be_disabled_for_baseline_comparison(tmp_path: Path) -> None:
    client = CountingClient()
    manifest = KamigameDbDKnowledgeCollector(tmp_path, client=client, dedupe_within_run=False).collect(
        follow_killer_details=True,
        follow_map_details=False,
    )
    counts = manifest["performance"]["counts"]
    assert counts["html_requests"] == 8
    assert counts["html_cache_hits"] == 0
    assert client.calls.count(_DUPLICATE_DETAIL) == 2


def test_training_studio_surfaces_total_and_cache_metrics() -> None:
    text = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert 'elapsed["db_upsert"]' in text
    assert 'elapsed["alias_index_update"]' in text
    assert '"total_with_post_process"' in text
    assert "同一実行cache hit" in text


def test_cli_exposes_controlled_baseline_switches() -> None:
    text = Path("src/ai_video_production/dbd_kamigame_cli.py").read_text(encoding="utf-8")
    assert '"--disable-same-run-dedupe"' in text
    assert '"--max-map-details"' in text
    assert 'dedupe_within_run=not args.disable_same_run_dedupe' in text
