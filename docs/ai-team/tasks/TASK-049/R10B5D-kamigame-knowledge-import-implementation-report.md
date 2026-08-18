# TASK-049 R10B5D — Kamigame Knowledge Candidate Import Implementation Report

Date: 2026-08-18

## Scope

Implemented a bounded Community Reference collector for the Owner-approved Kamigame DbD pages:

- Survivor Perks
- Killer Perks
- Killer list
- optional Killer detail pages

The collector is a Knowledge Candidate intake path. It does not write VERIFIED canonical Perk/Killer/Power revisions.

## Implementation

- `dbd_kamigame_collector.py`
  - stdlib HTML parser and bounded HTTP client;
  - Kamigame `/dbd/` page allow-list;
  - minimum request delay;
  - 8 MiB HTML response cap;
  - bounded pagination discovery;
  - raw HTML preservation + SHA-256;
  - Survivor/Killer Perk candidate parsing;
  - Killer list candidate parsing;
  - optional Killer-detail evidence traversal;
  - normalized JSONL/CSV/source manifest generation;
  - `COMMUNITY_REFERENCE / CANDIDATE` only.
- `dbd_kamigame_cli.py`
  - advanced CLI automation entrypoint.
- `BAI DbD Training Studio.exe`
  - new **Knowledge Import** tab;
  - explicit Human Collect action;
  - configurable output/safety limits;
  - optional Killer detail traversal;
  - background execution.
- documentation
  - README direct route;
  - dedicated Knowledge Candidate Import guide;
  - Training Studio cross-link.

## Generated bundle

```text
manifest.json
raw/**.html
normalized/survivor-perks.jsonl
normalized/killer-perks.jsonl
normalized/killers.jsonl
normalized/aliases.csv
normalized/sources.jsonl
```

`canonical_perk_id` and `canonical_killer_id` are intentionally unset until later Human/source review.

## Authority boundary

The collector does not infer:

- official truth;
- LIVE/PTB truth;
- Patch compatibility;
- canonical IDs;
- VERIFIED status;
- Production accuracy.

Community priority/strategy/category data remains source interpretation, not canonical fact.

## Verification

Parser, pagination, Killer-detail, deterministic bundle generation, GUI contract, CLI registration and README link tests are automated with local fixtures. Live site collection is not claimed as executed by the current sandboxed development host.
