from __future__ import annotations

from pathlib import Path
from statistics import median
import time

import pytest

from ai_video_production.assets import AssetRecord, AssetType, RightsStatus
from ai_video_production.store import SQLiteProductStore


JOB_ID = "JOB-00000000000000000000000000"
PROFILE_ID = "PSN-00000000000000000000000000"


def asset(index: int) -> AssetRecord:
    asset_id = f"ASSET-{index:026d}"
    return AssetRecord(
        production_job_id=JOB_ID,
        asset_type=AssetType.VIDEO,
        logical_uri=f"asset://{JOB_ID}/library/{index:05d}.mp4",
        checksum="sha256:" + f"{index:064x}",
        rights_status=RightsStatus.OWNED,
        owner="task045-fixture",
        asset_id=asset_id,
    )


def populate_large_library(store: SQLiteProductStore, count: int = 10_000) -> None:
    rows = [store._asset_insert_values(asset(index)) for index in range(count)]
    with store._connect() as conn:
        conn.executemany(
            """
            INSERT INTO assets(
              asset_id,job_id,type,logical_uri,checksum,rights_status,owner,retention_class,human_lock,
              original_name,commercial_use,derivative_allowed,reuse_allowed,audio_rights_status,
              source_ref,source_project,attribution,territory_json,rights_valid_until,
              publication_restrictions_json,approved_segments_json,media_metadata_json,
              generation_provenance_json,evidence_refs_json,perceptual_hash,audio_fingerprint
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )


def test_ten_thousand_asset_library_uses_bounded_keyset_pages(tmp_path: Path) -> None:
    store = SQLiteProductStore(tmp_path / "product.db")
    store.create_job(PROFILE_ID, job_id=JOB_ID)
    populate_large_library(store)

    first_samples_ms: list[float] = []
    second_samples_ms: list[float] = []
    first = second = None
    for _ in range(7):
        started = time.perf_counter()
        first = store.list_assets_page(JOB_ID, limit=200)
        first_samples_ms.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        second = store.list_assets_page(JOB_ID, limit=200, after_asset_id=first.next_cursor)
        second_samples_ms.append((time.perf_counter() - started) * 1000)
    assert first is not None and second is not None

    assert len(first.items) == len(second.items) == 200
    assert first.next_cursor == "ASSET-00000000000000000000000199"
    assert second.items[0].asset_id == "ASSET-00000000000000000000000200"
    assert set(item.asset_id for item in first.items).isdisjoint(item.asset_id for item in second.items)
    assert first.has_more is second.has_more is True
    assert len(first.to_dict()["items"]) == 200
    assert median(first_samples_ms) <= 500
    assert median(second_samples_ms) <= 500

    seen: list[str] = []
    cursor = None
    while True:
        page = store.list_assets_page(JOB_ID, limit=200, after_asset_id=cursor)
        seen.extend(item.asset_id for item in page.items)
        if not page.has_more:
            break
        cursor = page.next_cursor
    assert len(seen) == 10_000
    assert len(set(seen)) == 10_000
    assert seen == sorted(seen)

    with store._connect() as conn:
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(assets)")}
    assert "idx_assets_job_asset_id" in indexes


@pytest.mark.parametrize("limit", [0, 201, True, 1.5])
def test_asset_page_rejects_unbounded_or_invalid_limit(tmp_path: Path, limit) -> None:
    store = SQLiteProductStore(tmp_path / "product.db")
    store.create_job(PROFILE_ID, job_id=JOB_ID)
    with pytest.raises(ValueError, match="limit"):
        store.list_assets_page(JOB_ID, limit=limit)
