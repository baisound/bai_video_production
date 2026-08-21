# TASK-051 R7Q-R7S — Data Quality / Performance Detailed Design

Status: `LOCAL_IMPLEMENTED / WINDOWS_HUMAN_ACCEPTANCE_AND_REAL_FETCH_BASELINE_PENDING`
Development depth: `DEV-3 HIGH ASSURANCE`

## Goal

Continue the same TASK-051 Game Knowledge responsibility after R7P without creating a parallel store or collector.

### R7Q — deterministic DBD classification

Priority is:

1. explicit source/override kind;
2. article semantics (`○○対策`, `○○攻略`);
3. Owner-verified known entity master;
4. strong source-section semantics;
5. existing source-kind fallback.

The fixed regression cases are:

- トーリー / ドワイト / ナンシー / ネア -> キャラクター
- ハグ / ヒルビリー / ピッグ -> キラー
- ハグ対策 / ヒルビリー対策 / ピッグ対策 -> ナレッジ系
- ハディ -> サバイバー

`GameKnowledgeKind` is extended with `CHARACTER`, `SURVIVOR`, and `KNOWLEDGE`; existing values and stored payload decoding remain backward compatible.

### R7R — fetch observability and bounded optimization

The existing Kamigame collector remains canonical. It now records:

- total
- source_index_fetch
- candidate_discovery
- detail_page_fetch
- parse
- image_fetch
- normalize
- db_upsert
- alias_index_update
- post_process

The collector also records actual HTML/image request counts and same-run cache hits.

Within a single collection run, the same exact URL is fetched at most once when `dedupe_within_run=True`. A second logical consumer receives a copied raw snapshot and the same content hash/provenance, so raw evidence paths remain available without a second network request. This does not create a cross-run stale cache and therefore does not hide remote updates on a later run.

Training Studio adds catalog-upsert and Alias-index timings to the same manifest after the collector returns and recomputes the manifest checksum.

### R7S — unknown source-field completeness

Known normalized fields remain structured. Every accepted source row additionally preserves its non-empty source cells under `source_sections`:

```json
{
  "heading": "source section heading",
  "label": "列3",
  "value": "source text",
  "order": 3
}
```

`candidate_from_normalized()` already preserves unknown normalized fields in `details`, so `source_sections` reaches the existing R7P detail/review surface without a second model or migration.

## Non-goals

- no cross-run TTL cache;
- no unbounded/concurrent crawling of the external site;
- no claim of 30% real-site improvement without the required Windows three-run before/after baseline;
- no canonical auto-verification of community data;
- no Release, merge, or TASK-051 closure claim.

## Acceptance

- all 11 fixed classification cases pass;
- `ハグ対策` cannot collapse into the `ハグ` killer entity;
- a known entity discovered through a legacy MAP path is reclassified before review-catalog insertion;
- performance manifest contains all required stages and request/cache counters;
- duplicate detail URLs generate one actual request but preserve both raw logical snapshots;
- unknown source columns survive normalization into `GameKnowledgeCandidate.details`;
- R7P/R7N/R7O/R7A focused regression passes;
- TASK-049/050/051 regression passes except environment-only Tk display skip.
