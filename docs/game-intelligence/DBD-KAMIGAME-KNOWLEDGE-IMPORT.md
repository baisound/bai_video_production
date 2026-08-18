# DbD Kamigame Knowledge Candidate Import

## Purpose

This guide describes the bounded Kamigame collector used by TASK-049 to create **reviewable DbD Knowledge Candidates** from the following user-approved source pages:

- Survivor Perks: `https://kamigame.jp/dbd/page/207150682694767780.html`
- Killer Perks: `https://kamigame.jp/dbd/page/207148601481152853.html`
- Killer list: `https://kamigame.jp/dbd/page/93384114123571207.html`

The collector is **not a canonical truth writer**. Kamigame is classified as `COMMUNITY_REFERENCE` and every normalized record is emitted as `CANDIDATE`.

```text
Kamigame HTML
  ↓
Raw snapshot + SHA-256
  ↓
Normalized Candidate
  ↓
Human/source review
  ↓
Canonical Perk / Killer / Power Knowledge only after explicit validation
```

## Normal GUI route

Build and open [BAI DbD Training Studio](../windows/BUILDING-DBD-TRAINING-STUDIO-EXE.md), then select **Knowledge Import**.

1. Choose the output directory.
2. Keep **Follow Killer detail pages** enabled when Killer detail evidence is required.
3. Keep the default safety limits unless there is a specific reason to change them.
4. Press **Collect Survivor / Killer / Killer details**.
5. Wait for the background collection job to finish.
6. Inspect `manifest.json` and the files under `normalized/`.
7. Review candidates before mapping them to canonical `perk_id`, `killer_id`, Patch revision, or VERIFIED status.

Network access occurs only after the operator presses **Collect**.

## Output

```text
<output>/
├─ manifest.json
├─ raw/
│  ├─ survivor-perks/
│  ├─ killer-perks/
│  ├─ killers/
│  └─ killer-details/
└─ normalized/
   ├─ survivor-perks.jsonl
   ├─ killer-perks.jsonl
   ├─ killers.jsonl
   ├─ aliases.csv
   └─ sources.jsonl
```

### Perk Candidate

The normalized Perk Candidate includes:

- role (`SURVIVOR` / `KILLER`);
- Japanese source name;
- source aliases when present;
- owner name;
- source priority rating;
- source effect text;
- source categories;
- source/detail URL;
- source image URL candidates when present;
- `COMMUNITY_REFERENCE` authority;
- `CANDIDATE` review status.

The collector intentionally leaves `canonical_perk_id` empty. A stable collector candidate ID is not a canonical DbD ID.

### Killer Candidate

The Killer Candidate includes:

- Japanese Killer name;
- movement-speed source text;
- terror-radius source text;
- height source text;
- unique Perk names;
- detail-page URL;
- optional bounded detail-page snapshot data;
- headings indicating whether the detail page contains Power/Add-on sections;
- `COMMUNITY_REFERENCE` authority;
- `CANDIDATE` review status.

The collector intentionally leaves `canonical_killer_id` empty.

## Pagination

The collector consumes all rows available on the initial HTML page and also follows same-page pagination links when the HTML exposes a bounded `next/page/p/offset` route.

This is deliberate: site UI pagination may be client-rendered while the HTML already contains all entities. Completeness is therefore measured by **deduplicated candidate counts**, not by assuming a particular number of clicks.

Defaults:

```text
max list pages = 20
max Killer detail pages = 128
minimum request delay = 0.75 seconds
maximum HTML response = 8 MiB
```

## Killer detail pages

When enabled, the collector follows Killer detail links under `kamigame.jp/dbd/` only. It stores the raw HTML and a bounded review-oriented representation containing:

- headings;
- a bounded page-text excerpt;
- Power-section presence;
- Add-on-section presence;
- bounded image URL candidates;
- bounded linked DbD page URLs.

Long guide prose is not auto-promoted to factual Knowledge. Strategy/opinion content belongs in Commentary/Trivia Candidate workflows when explicitly reviewed.

## Raw preservation and provenance

Every fetched page is preserved under `raw/` and receives SHA-256 provenance in `normalized/sources.jsonl`.

A source-content change therefore creates a different source hash and can be reviewed before canonical revision changes are accepted.

## Canonical boundary

Do **not** interpret these fields as automatically verified facts:

```text
Kamigame source effect
Priority rating
Strategy recommendation
Category
Killer assessment
Detail-page explanation
```

Canonical rules remain:

- official/current Patch compatibility must be established separately;
- LIVE/PTB must not be inferred from a community article alone;
- no scraped record becomes `VERIFIED` automatically;
- no candidate is allowed to overwrite an existing canonical revision by ID;
- Human review and source provenance are retained.

## CLI route

Advanced automation can use:

```powershell
ai-video-dbd-kamigame-collect `
  --output .\evidence\task049-kamigame
```

Without Killer detail traversal:

```powershell
ai-video-dbd-kamigame-collect `
  --output .\evidence\task049-kamigame `
  --no-killer-details
```

## Relationship to image training

Web/source images, if later downloaded and reviewed, should be treated as **master/reference candidates**, not Human Gold gameplay frames.

Recognition quality should still be trained/evaluated using real gameplay crops produced by [Training Studio](../user/DBD-TRAINING-STUDIO-USAGE.md) and the [Slice Dataset Guide](DBD-SLICE-DATASET-GUIDE.md).

## Related documents

- [DbD Recognition Accuracy and Training](DBD-RECOGNITION-ACCURACY-AND-TRAINING.md)
- [DbD Slice Dataset Guide](DBD-SLICE-DATASET-GUIDE.md)
- [DbD Commentary Trivia Knowledge](DBD-COMMENTARY-TRIVIA-KNOWLEDGE.md)
- [Training Studio Usage](../user/DBD-TRAINING-STUDIO-USAGE.md)
- [Windows Game Intelligence Environment](../windows/WINDOWS-GAME-INTELLIGENCE-ENVIRONMENT.md)
