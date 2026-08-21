# TASK-052 R0A — Human Acceptance Defect Baseline and Data Inventory

Status: `BASELINE_COMPLETE / REMEDIATION_NOT_YET_CLAIMED`
Date: `2026-08-21`
Branch baseline: `feature/task-052-dbd @ fdd4663`
Profile: `DEV-3 HIGH ASSURANCE`

## Scope and safety

This report records implementation truth and read-only inventory evidence before
TASK-052 remediation. The Owner's active Training Studio workspace was inspected
without mutation. No migration, canonical write, external fetch, asset rewrite,
index rebuild, EXE launch or user-data deletion occurred.

The repository report intentionally omits the private workspace path and source
data bodies. Counts and stable Product identifiers are retained where required.

## Repository and Pull Request health

- TASK worktree: confirmed at the Owner-designated TASK-052 worktree.
- Original local branch: clean `feature/task-052-dbd @ c9a56ee` with deleted
  remote tracking branch.
- PR #196: `MERGED`; all 9 observed CI/release/security checks `SUCCESS`.
- Remote branch: deleted after merge.
- Continuation recovery: the old local branch was preserved as
  `feature/task-052-dbd-pr196-merged`; a new clean `feature/task-052-dbd` was
  created from current `origin/main @ fdd4663`. No reset or history rewrite was
  used.

## Source regression baseline

Focused WSL2 source regression:

```text
70 passed in 22.37s
```

This PASS proves the current tests, not the Owner-routed behavior. Several tests
encode the pre-TASK-052 taxonomy and therefore pass while contradicting the new
canonical requirements.

## Owner workspace inventory

Read-only inventory of the default registered workspace:

| Item | Observed |
|---|---:|
| Game Knowledge candidates | 1,614 |
| `ADDON` | 904 |
| `ITEM` | 36 |
| `KILLER` | 48 |
| `KNOWLEDGE` | 24 |
| `MAP` | 140 |
| `OFFERING` | 67 |
| `PERK` | 321 |
| `REALM` | 69 |
| `SURVIVOR` | 1 |
| legacy `CHARACTER` | 4 |
| Human-touched (`VERIFIED`, `NEEDS_REVIEW`, `UPDATE_AVAILABLE`) | 0 |
| visual-training samples | 16 |
| visual-training domains | `PERK_ICON=16` only |
| Kamigame raw files | 177 |
| Kamigame normalized files | 8 |
| opaque `.img` files | 60 |

All 60 observed `.img` files begin with SVG XML bytes rather than a raster magic
number. This proves that suffix-based raster loading is invalid for the real
cache and that SVG/opaque-content handling needs a deliberate decode or
normalization path.

## Classification and parser corruption inventory

The four Owner-verified Survivor records exist as `CANDIDATE` rows with legacy
`CHARACTER` classification:

| Name | Current ID prefix | Current kind | Required kind |
|---|---|---|---|
| トーリー | `map_kamigame_` | `CHARACTER` | `SURVIVOR` |
| ドワイト | `map_kamigame_` | `CHARACTER` | `SURVIVOR` |
| ナンシー | `map_kamigame_` | `CHARACTER` | `SURVIVOR` |
| ネア | `map_kamigame_` | `CHARACTER` | `SURVIVOR` |

The observed contaminated source values are also present as correctly typed
Perks and as incorrectly promoted Knowledge candidates:

| Value | Correct row | Incorrect row |
|---|---|---|
| 究極の武器 | `PERK` | `REALM` |
| 素早い残虐行為 | `PERK` | `OFFERING` |

The derived map-intelligence store contains two rows whose Realm value is
`究極の武器`. This is current-data evidence, not only a synthetic parser risk.

## Defect baseline

### DBD-HA-052-001 — map rotation display

- Current code: `_knowledge_thumbnail()` uses Pillow then a Tk fallback;
  `show_map_detail()` stores a strong `image_ref` and rotates pixels in memory.
- Persistence: `MapIntelligenceStore` already persists `rotation_deg`.
- Gap: decode exceptions are swallowed; the UI reduces them to generic
  `画像を表示できません`. No real cached-image rotation regression or packaged
  reopen/restart evidence exists.
- Baseline result: `PARTIAL / WINDOWS NOT_CONFIRMED`.

### DBD-HA-052-002 — opaque `.img` assets

- Current collector chooses suffix from HTTP content type and falls back to
  `.img` for unknown types.
- Pillow performs byte sniffing for supported raster formats, but all 60 current
  opaque assets are SVG XML and are not covered by Pillow's raster decoder.
- No canonical PNG normalization receipt exists.
- Baseline result: `PARTIAL / REAL CACHE FAILURE RISK CONFIRMED`.

### DBD-HA-052-003 — internal metadata in normal UI

- `edit_knowledge_candidate()` renders every non-underscore `details` key,
  followed by `source_page_url` and `candidate_id`, in the normal detail panel.
- The image path is also displayed directly in the normal image panel.
- There is no collapsed `内部・診断情報` boundary or per-kind Human field
  registry.
- Baseline result: `MISSING`.

### DBD-HA-052-004 — HTML detail extraction contamination

- `_KamigameHTMLParser` collects page-global headings, links, images and text.
- `parse_killer_detail_page()` returns page-global excerpts/links and has no
  `ENTITY_DETAIL_ROOT`, template fingerprint or DOM ancestry boundary.
- `parse_map_detail_page()` infers Realm/Offering from the first suitable linked
  table row and searches page-global text with regular expressions.
- No fixture proves related/navigation/sidebar exclusion for the Owner examples.
- Baseline result: `MISSING / CURRENT-DATA CORRUPTION CONFIRMED`.

### DBD-HA-052-005 — Game Knowledge classification corruption

- `_KNOWN_ENTITY_KIND` explicitly maps トーリー/ドワイト/ナンシー/ネア to
  `CHARACTER`.
- headings containing `キャラクター` also return `CHARACTER`.
- `INVENTORY_KIND_JA` exposes `キャラクター` in the operator filter/list.
- Current tests assert the obsolete `CHARACTER` result.
- Baseline result: `MISSING / CURRENT-DATA CORRUPTION CONFIRMED`.

### DBD-HA-052-006 — safe delete

- The catalog supports status changes and disabling but has no dependency-impact
  model, tombstone provenance, protected-reference inspection or candidate
  physical removal API.
- The Game Knowledge UI has no visible delete action.
- Baseline result: `MISSING`.

### DBD-HA-052-007 — Survivor-scoped hook/chase

- `SurvivorSlotObservation` and four Survivor ROIs exist for base HUD state.
- The teacher namespace only has a generic `SURVIVOR_HUD`; it has no explicit
  `HOOK_COUNT` or `CHASE_STATE` domains and no required `match_id +
  survivor_slot + signal_kind` observation contract.
- Event resolver tests cover hook/chase transitions but not four independent
  Survivor subjects.
- Baseline result: `PARTIAL`.

### DBD-HA-052-008 — process storm / UI freeze

- Preview extraction runs off the Tk thread, but `preview_video_batch()` starts
  one FFmpeg process per frame/target pair.
- FFmpeg/ffprobe `subprocess.run()` calls do not set Windows
  `CREATE_NO_WINDOW`.
- Batch confirm runs on the Tk main thread and calls `manifest.append()` once
  per sample; each append rereads and atomically rewrites the full CSV.
- Confirm has no progress, Cancel, transaction receipt, batch manifest commit or
  bounded per-domain index rebuild report.
- Baseline result: `PARTIAL / P0 OPERABILITY GAP CONFIRMED BY SOURCE`.

## Required remediation order derived from evidence

1. `R1A`: canonical taxonomy, parser structural boundary, dry-run migration.
2. `R1B`: Human field registry and safe delete/tombstone dependency preview.
3. `R1C`: content-sniffed asset decode/normalization and persistent rotation.
4. `R2A`: Survivor-scoped hook/chase teacher and observation contracts.
5. `R2B`: no-console bounded extraction and transactional background confirm.

`R1A` precedes broad recognition training because current candidate data is
already polluted. No production-accuracy or Windows packaged PASS is claimed.
