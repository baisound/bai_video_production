# TASK-052 — Design-to-Implementation Gap Audit / Recognition Completion Detailed Design

Status: `DESIGN_READY / IMPLEMENTATION_QUEUED_AFTER_TASK051_RELEASE`
Development depth: `DEV-3 HIGH ASSURANCE`
Date: `2026-08-21`

## 1. Goal

The legacy DbD designs describe a wider recognition and commentary system than the currently surfaced Training Studio workflows. TASK-052 will stop relying on memory or UI appearance and establish an evidence-backed requirement matrix from original design -> current source -> current tests -> Windows Human Acceptance -> remediation owner.

The Task has two inseparable outputs:

1. **Gap Audit** — prove what is implemented, partial, missing, superseded or intentionally deferred.
2. **Gap Remediation** — implement only the validated in-scope gaps in dependency order, with explicit Human/Production accuracy gates.

## 2. Authority sources and design basis

Audit inputs include:

- original `dbd_vision_ai_specification.md` design;
- the later Ver.2 DbD design that defines Tier 1 HUD/OCR, Tier 2 Temporal State Machine, Tier 3 Object/Scene Recognition, Tier 4 Selective Vision AI, Gold Dataset and Human correction flow;
- current TASK-049 Game Intelligence / CGEL contracts;
- TASK-050 Training Studio operational/data foundation;
- TASK-051 Human Acceptance and unified learning workflow;
- current source/tests as implementation truth;
- Owner Human Acceptance findings recorded during TASK-051.

The audit must preserve original terminology but must not assume an old implementation technology remains canonical. For example, an old EasyOCR/Demucs/Chroma/FAISS implementation detail may be `SUPERSEDED_BY_CANONICAL_OWNER` if the present Product already owns that responsibility through a different provider or store.

## 3. Mandatory traceability matrix

Every source requirement becomes one row with these fields:

| Field | Meaning |
|---|---|
| `requirement_id` | stable `DBD-GAP-###` identifier |
| `design_source` | original document / section / exact concept |
| `requirement` | normalized requirement without changing meaning |
| `current_symbols` | current module/class/function/schema/UI route |
| `current_tests` | tests that prove the implementation |
| `windows_evidence` | packaged/native Human Acceptance evidence |
| `canonical_owner` | TASK/domain that owns the responsibility now |
| `status` | classification below |
| `risk` | P0/P1/P2 |
| `dependencies` | exact predecessor requirements |
| `remediation_unit` | planned TASK-052 Atomic Unit |
| `acceptance` | measurable completion condition |

Allowed status values are closed:

- `IMPLEMENTED_VERIFIED`
- `IMPLEMENTED_UNVERIFIED`
- `PARTIAL`
- `STUB`
- `MISSING`
- `SUPERSEDED_BY_CANONICAL_OWNER`
- `INTENTIONALLY_DEFERRED`
- `CONFLICT_REQUIRES_OWNER_DECISION`

No requirement may disappear merely because it is inconvenient or because a current screen does not expose it.

## 4. Recognition architecture to audit and complete

### 4.1 Tier 1 — HUD / OCR

The legacy design explicitly expects low-cost HUD/OCR recognition before expensive Vision AI. TASK-052 must inventory and complete the following families.

#### A. Match progression / left-side HUD

- remaining generator count `0..5`;
- Survivor base state: `HEALTHY / INJURED / DOWNED / HOOKED / DEAD / ESCAPED / UNKNOWN`;
- hook state and hook/unhook transitions;
- hook count/stage where visually available, cross-checked against accumulated HOOK events rather than trusted as a single frame truth;
- UI-based chase signal.

TASK-051 establishes calibratable/training routes for generator count, hook count and chase-state crops. TASK-052 must audit the missing production logic around temporal voting, transition constraints and CGEL emission.

#### B. Survivor icon killer-specific overlays

A Survivor icon region is not semantically stable across killers. The same circular/noisy visual family can represent different killer mechanics. TASK-052 introduces a **Killer Capability Registry** instead of one global visual class.

Registry contract:

```text
killer_id
  -> hud_effect_id
  -> effect_family
  -> required_roi_family
  -> detector_type
  -> stage/progress semantics
  -> training label namespace
  -> hard-negative namespaces
  -> CGEL/state projection
```

Initial Owner-observed examples to model as concrete acceptance fixtures:

- killer-specific circular indicator around Survivor portrait (Owner example: "ファースト");
- Ghost Face mark/reveal progress and completed red circular state;
- The Onryo/Sadako Condemn accumulation ring/progress;
- Doctor madness progression and maximum-madness noise around the Survivor icon.

These examples are design fixtures, not a claim that the list is complete. The audit must enumerate current live killer HUD mechanics from the maintained Game Knowledge source before implementation breadth is declared complete.

Detector routing rule:

```text
identified killer with sufficient confidence
    -> common Survivor HUD detectors
    -> only that killer's registered killer-specific detectors
unknown killer
    -> common detectors only + killer-specific state UNKNOWN
```

This reduces false positives and avoids training Ghost Face / Sadako / Doctor visuals into one generic `circle` class.

#### C. Bottom-right perk and status-effect HUD

Treat the lower-right HUD as three independent semantic regions:

```text
bottom_right_perks
bottom_right_negative_effects   # above the perk icons
bottom_right_positive_effects   # left of the perk icons
```

The positive/negative regions are multi-object regions. One frame may contain zero, one, or several effects. The recognizer therefore needs:

1. icon segmentation/detection within the region;
2. effect identity classification;
3. polarity (`POSITIVE` / `NEGATIVE`);
4. temporal association so appearance/disappearance becomes start/end state;
5. provenance and confidence;
6. explicit UNKNOWN and hard negatives.

Recommended observation model:

```text
effect_id
effect_polarity
source_kind = PERK | KILLER_POWER | ITEM | ADDON | GAME_MECHANIC | UNKNOWN
stack_or_level
progress
is_active
confidence_milli
source_frame
survivor_slot? / player_scope?
```

A perk icon, positive status icon, negative status icon and killer-specific Survivor overlay are separate teacher-data namespaces and must not share a positive label solely because their artwork is similar.

#### D. Upper-right notification HUD

Audit the expanded notification taxonomy including TASK-051 `PERK` notification support, OCR vocabulary correction, Game Knowledge phrase matching and downstream meaning/event mapping.

### 4.2 Tier 2 — Temporal State Machine

Single-frame classifiers are Evidence, not final event truth.

The original Ver.2 design requires debounce, hysteresis and transition consistency. TASK-052 must implement/reconcile state machines for at least:

- chase start / active / end;
- generator remaining count temporal majority + impossible-increase handling;
- Survivor health/down/hook state transitions;
- hook count/stage accumulation and contradiction detection;
- killer-specific progress/stage effects;
- positive/negative status-effect appearance/disappearance.

Example chase state contract retained from the source design:

```text
NOT_CHASE
 -> CHASE_CANDIDATE
 -> CHASE_ACTIVE
 -> CHASE_END_CANDIDATE
 -> NOT_CHASE
```

Exact consecutive-frame thresholds are Profile/calibration parameters, not hard-coded global truths.

### 4.3 Tier 3 — Object / Scene Recognition

Inventory original targets and current implementation before adding code:

- pallets;
- windows;
- killer/survivor identity where visually supported;
- map features;
- main/unique building candidates;
- killer-power visual cues.

Each item may become `IMPLEMENTED_VERIFIED`, `PARTIAL`, `MISSING`, or `SUPERSEDED_BY_CANONICAL_OWNER`; do not presume missing from the old design alone.

### 4.4 Tier 4 — Selective Vision AI

Expensive Vision AI remains selective, not full-frame always-on processing. Audit whether the present Product has an equivalent bounded escalation route for:

- chase boundary ambiguity;
- pre-down moments;
- rescue;
- generator completion;
- major tactical decisions;
- contradictions between Tier 1–3 detectors.

If current BVP provider execution already owns this capability, route it through the existing provider boundary instead of creating a DbD-specific second provider stack.

## 5. Teacher-data and HUD Profile design

### 5.1 ROI families

TASK-052 must audit/add Profile ROIs without exploding to one ROI per killer when the physical screen region is shared.

Base families:

- generator counter;
- Survivor slot regions;
- hook stage/count region if distinct;
- chase indicator region;
- bottom-right perk slots;
- bottom-right positive-effect region;
- bottom-right negative-effect region;
- upper-right notification region;
- killer-power HUD;
- extensible `killer_specific_rois` only where a mechanic appears at a genuinely different screen location.

Every ROI stays normalized, versioned, resolution/UI-scale aware and backward readable.

### 5.2 Teacher labels

Teacher data is namespaced by domain:

```text
SURVIVOR_STATE
GENERATOR_REMAINING
HOOK_COUNT
CHASE_STATE
PERK_ICON
STATUS_EFFECT_POSITIVE
STATUS_EFFECT_NEGATIVE
KILLER_SPECIFIC_HUD/<killer_id>/<effect_id>
KILLER_POWER
ITEM_ICON
ADDON_ICON
```

Hard negatives are first-class. Examples:

- Ghost Face red ring != chase;
- Sadako Condemn ring != Ghost Face mark;
- Doctor noise != generic injured effect;
- status-effect icon != perk icon;
- positive status icon != negative status icon.

## 6. Canonical event/state projection

Detector outputs must not directly mutate Production Timeline.

```text
Exact Frame / Crop Evidence
 -> Detector Observation
 -> Temporal State Machine
 -> Cross-modal Fusion / contradiction gate
 -> Canonical Game Event or state Evidence
 -> Human Review when threshold/consistency requires
 -> Editing Intelligence / commentary consumers
```

Candidate mappings include `GENERATOR_COMPLETE`, `CHASE_START`, `CHASE_END`, `INJURY`, `DOWN`, `HOOK`, `UNHOOK` and other already canonical TASK-049 event types. New status-effect observations should remain state Evidence unless/until an explicit CGEL event type is justified.

## 7. Gold Dataset / Human correction

The legacy design requires a 5–10 match Pilot Gold Dataset containing at least generator changes, chase, injured/down/hook, speaker, transcript and tactical notes. TASK-052 must audit whether each Gold route is operational, not merely schematized.

Any Human correction must preserve original and corrected values plus reviewer/reason/provenance. Corrections are inputs to detector improvement; they do not silently overwrite historical Evidence.

Production accuracy is never inferred from synthetic/reference tests. Held-out Human Gold evaluation remains required.

## 8. Performance architecture

- run only relevant killer-specific detectors after killer routing;
- use exact calibrated ROIs rather than whole-frame matching;
- cache/reuse reference indexes;
- bound candidate counts and temporal windows;
- keep UI/background work off the Tk main loop;
- prefer incremental/rebuildable SQLite projections for search/derived indexes;
- do not duplicate canonical JSON/SQLite stores just for speed;
- record per-detector latency and UNKNOWN rate for regression.

## 9. Backup / migration

Any new SQLite projection, teacher-data manifest, HUD Profile field, Killer Capability Registry or detector calibration must be included in the existing Training Studio backup/restore boundary where appropriate.

Derived indexes must be either:

- safely backed up/restored and integrity-checked; or
- explicitly rebuildable from canonical data after restore.

Schema/Profile changes require backward-read tests and fail-closed newer-version behavior.

## 10. Atomic implementation order

### R0 — Requirement Corpus + Traceability Matrix

Build the complete `DBD-GAP-###` matrix from all known original designs and current canonical BVP docs. No production code changes.

### R1 — HUD Taxonomy / Profile Contract

Finalize Survivor/base/killer-specific/status-effect ROI and teacher namespaces; migration/backward-read tests.

### R2 — Tier 1 Core State Completion

Generator, Survivor state, hook state/count and chase detector wiring; exact Evidence and UNKNOWN semantics.

### R3 — Temporal State Machines

Debounce/hysteresis/transition constraints and CGEL projection for core signals.

### R4 — Killer Capability Registry / Survivor Overlays

Killer-conditioned detector registry, initial Owner-observed mechanic fixtures and hard-negative routing.

### R5 — Positive / Negative Status Effects

Bottom-right multi-icon segmentation, identity/polarity/state tracking and training/review UI.

### R6 — Tier 3 Object / Scene Gaps

Implement only rows classified PARTIAL/MISSING after R0; route superseded rows elsewhere.

### R7 — Selective Vision AI / Contradiction Escalation

Reuse canonical Provider execution boundary; no parallel provider framework.

### R8 — Gold / Correction / KPI Closure

Held-out dataset, per-domain metrics, UNKNOWN/false-positive analysis and Human correction feedback.

### R9 — Windows Packaged Human Acceptance / Performance / Backup

Real DbD media, multiple killers, multiple UI scales/resolutions, restore/reopen, packaged EXE, regression and closure evidence.

## 11. P0/P1/P2 priority policy

P0:

- a gap can create a wrong CGEL event/state rather than UNKNOWN;
- wrong killer-specific HUD interpretation contaminates another detector;
- backup/migration can lose teacher/reference data;
- current UI claims a learning route that does not feed recognition.

P1:

- missing recognition materially reduces commentary/editing intelligence but fails safely to UNKNOWN;
- status/effect context needed for tactical interpretation;
- measurable performance/operability blockers.

P2:

- low-frequency breadth, convenience, visualization or calibration assistance where core correctness already fails safely.

## 12. Completion criteria

TASK-052 cannot close from a list of implemented classes alone. Completion requires:

1. 100% of original-design requirements represented in the matrix;
2. no unexplained requirement rows;
3. every PARTIAL/MISSING in-scope row either remediated or Owner-deferred;
4. every superseded row names its canonical current owner;
5. relevant unit/integration/regression PASS;
6. backward Profile/data migration PASS;
7. backup/restore PASS;
8. packaged Windows Human Acceptance using real DbD media;
9. held-out Human Gold metrics for production-accuracy claims;
10. Critical/High Critic findings `0 / 0`.

## 13. Explicit sequencing boundary

TASK-052 design is created now, but implementation begins only after TASK-051 reaches its release checkpoint. This prevents the current Human Acceptance closure from expanding indefinitely while preserving all newly identified recognition requirements as a governed successor Task.

## 14. Owner-routed Human Acceptance defect backlog from TASK-051

Date recorded: `2026-08-21`

The Owner explicitly routed the following real-Windows Human Acceptance findings to TASK-052. These are not theoretical gap-audit rows. They are reproduced Product defects or data-quality failures that MUST enter the TASK-052 traceability matrix with stable defect IDs before remediation begins.

This routing does **not** mean TASK-051 proved these behaviors correct. TASK-051 closure/release evidence must describe them as Owner-deferred successor work rather than silently promoting them to PASS.

### 14.1 Defect register

| Defect ID | Finding | Risk | Primary remediation unit |
|---|---|---:|---|
| `DBD-HA-052-001` | Map preview can become `画像を表示できません` after a right 90-degree rotation even when the source image was previously displayable. | P0 | R1 |
| `DBD-HA-052-002` | Imported map/image assets can use opaque `.img` paths; image decoding/display must not depend on filename extension alone. | P1 | R1 |
| `DBD-HA-052-003` | Game Knowledge detail/edit UI still exposes technical/internal values such as raw field keys and `local_image_path` as ordinary editable detail. | P1 | R1 |
| `DBD-HA-052-004` | Source-detail extraction confuses page navigation/related links with entity facts; examples include `領域: 究極の武器` and `オファリング: 素早い残虐行為`, although both values are perk names. | P0 | R0/R1 |
| `DBD-HA-052-005` | Entity classification is materially corrupted: non-maps appear as maps, many Survivors are classified as maps, and legacy `キャラクター` is shown although the Product taxonomy should use `サバイバー`. | P0 | R0/R1 |
| `DBD-HA-052-006` | Game Knowledge edit/detail needs a safe delete operation, but deletion must preserve referential integrity for verified/referenced entities and linked training/evidence data. | P0 | R1 |
| `DBD-HA-052-007` | Hook count and chase state are currently treated too globally; both are Survivor-subject state and must bind to an individual Survivor slot. | P0 | R1/R2/R3 |
| `DBD-HA-052-008` | `画像学習データ > 発電機 残0 > 確認した画像を登録` can spawn a large number of black terminal windows, appear to hang, and force the operator to kill the app. | P0 | R2/R9 |

The following Owner observations remain part of the same TASK-052 P0 recognition scope and are cross-linked rather than duplicated as separate defects:

- killer-specific Survivor HUD overlays (Ghost Face mark ring, Sadako Condemn ring/progress, Doctor madness/noise and other killer-conditioned HUD effects);
- positive status-effect icons left of the bottom-right perk HUD;
- negative status-effect icons above the bottom-right perk HUD.

### 14.2 Map asset decode and rotation contract

`DBD-HA-052-001` and `DBD-HA-052-002` are one asset/rendering safety boundary.

Required behavior:

1. Decode image content by actual bytes/MIME where practical; a valid cached image MUST NOT fail only because its local filename uses `.img`.
2. Imported opaque assets may be normalized into a canonical cache representation such as PNG while retaining source URL, original cache path and checksum as provenance.
3. Rotation is a view/canonical-orientation transform. Do not destructively rewrite the source download.
4. The rotated preview MUST own a strong GUI image reference for the lifetime of the visible widget; garbage collection must not blank a valid preview.
5. `0 / 90 / 180 / 270` degrees must be deterministic and persist across detail reopen/application restart.
6. Rotation failure is fail-visible with the decode path, detected format and bounded diagnostic reason; it must not silently replace a previously valid preview with a generic unavailable state.
7. A real cached Kamigame map asset is required as a Windows regression fixture, including one asset whose stored suffix is `.img`.

Acceptance:

```text
open source image
 -> visible
rotate right 90
 -> visibly rotated pixels
close/reopen detail
 -> same orientation and visible pixels
restart Training Studio
 -> same orientation and visible pixels
```

### 14.3 Human-first Game Knowledge detail contract

`DBD-HA-052-003` changes the detail form from an arbitrary key/value dump to a schema-aware human form.

Normal edit view MUST be generated from an allowlisted human field registry per entity kind. Examples:

```text
Common:
  日本語名 / 英語名 / 別名
  種別
  効果・説明
  取得元
  画像
  Human review state

Killer:
  基本ステータス
  固有能力
  固有パーク
  評価・攻略
  アドオン関連

Item / Add-on:
  効果
  チャージ
  レア度
  所有/対象
  使用条件

Map:
  Realm
  面積
  広さ
  固有建築/特徴
  Offering relation when it is a real map fact
```

Technical values such as the following MUST NOT appear as ordinary editable fields:

```text
candidate_id
classification_source
classification_confidence
priority
role
canonical_*
local_image_path
source_revision_sha256
raw parser keys
```

They remain available only under a collapsed read-only `内部・診断情報` surface.

`source_sections` remains valuable provenance. Preserving unknown source data does not authorize exposing every raw key as a Product form field.

### 14.4 Source-detail semantic scoping

`DBD-HA-052-004` is a parser/provenance bug, not merely a bad label translation.

The Owner-provided Xenomorph screenshots are **range examples** showing what was meant by “the page area that constitutes detail information.” They are not a Xenomorph-specific schema, and they do not prove that every Killer page contains exactly the same headings or fields.

The implementation must therefore discover and validate the **HTML structural boundary** of the entity-detail content instead of hard-coding one Killer's displayed fields.

The collector/parser MUST distinguish:

```text
ENTITY_DETAIL_ROOT
ENTITY_FACT_SECTION
ENTITY_STAT_TABLE
UNIQUE_PERK_SECTION
EVALUATION_SECTION
ADDON_EVALUATION_SECTION
TACTICAL_TEXT
RELATED_ARTICLE_LINK
NAVIGATION
SIDEBAR
FOOTER
ADVERTISEMENT_OR_OTHER
UNKNOWN_SECTION
```

Only sections proven to be descendants of the current entity's `ENTITY_DETAIL_ROOT` may populate typed entity facts.

Structural discovery contract:

1. Inspect multiple pages of the same entity kind before declaring one selector/template canonical.
2. Prefer stable DOM ancestry, section containers, table structure, heading hierarchy and semantic attributes/classes over Japanese visible-text matching.
3. If multiple Killer pages share the same main-detail DOM structure, define one reusable Killer page-template profile from that structure.
4. If structures differ, create bounded page-template profiles and select by validated structure fingerprint; do not force all pages through one selector.
5. Unknown/unrecognized page structure fails closed to `UNKNOWN_SECTION` / Human Review rather than promoting nearby text into typed fields.
6. Record the source structure/template identity in provenance so parser regressions can be reproduced after site changes.

The Owner screenshots suggest that, on the shown example page, the intended detail range includes the central entity-content sections such as the displayed status area, unique-perk area, evaluation area and evaluation-point text. This is **evidence about the intended extraction boundary**, not a guarantee that these exact sections exist on every Killer page.

Rules:

- DOM extraction must remain inside the validated current entity detail root and its allowed descendant sections.
- Related-article cards, navigation labels, ranking links, recommendation links and sidebar text must never become fields such as `realm`, `offering`, `perk`, `owner` or `category`.
- A field name or nearby visible string alone is not evidence. The parser must retain section provenance, DOM ancestry and entity-kind compatibility.
- Cross-domain values are rejected from typed facts and retained only as raw/diagnostic source evidence when useful.
- Section headings and table labels should be preserved as source facts first; Product normalization happens only when a mapping is valid for that entity kind.
- Parser changes require fixtures from multiple Killer pages before “all Killer pages” support is claimed.
- Parser changes also require regression fixtures proving `究極の武器` and `素早い残虐行為` cannot be promoted to Realm/Offering facts merely because those strings appear in related/navigation content.

Acceptance for Killer detail extraction:

```text
sample multiple Killer pages
 -> identify validated detail root/template for each
 -> extract only descendant detail sections
 -> preserve source section/label/value provenance
 -> normalize only entity-compatible fields
 -> exclude navigation/related/sidebar content
 -> unknown template => fail closed / Human Review
```

The Xenomorph page may remain one regression sample because the Owner supplied it, but it has no special canonical status beyond being one observed example of the intended detail-content boundary.


### 14.5 Canonical taxonomy and classification repair

`DBD-HA-052-005` requires both future classification correction and existing-data repair.

Canonical operator taxonomy MUST NOT expose `キャラクター`.

At minimum, the relevant identity categories are:

```text
SURVIVOR
KILLER
PERK
ITEM
ADDON
MAP
REALM
OFFERING
KNOWLEDGE
UNKNOWN
```

Rules:

1. Known Survivor entities such as トーリー, ドワイト, ナンシー and ネア classify as `SURVIVOR`.
2. A page is not `MAP` merely because weak fallback/source-category evidence mentions a map-like term.
3. Explicit entity master / verified canonical identity outranks weak source-kind fallback.
4. Article semantics and scoped page structure outrank navigation/sidebar labels.
5. Legacy `CHARACTER` records are migration input, not a supported final UI category.
6. Do not blindly convert every legacy `CHARACTER` to `SURVIVOR`. Known Survivor master matches become `SURVIVOR`; unresolved legacy rows become `UNKNOWN`/Human Review.
7. Existing manual corrections and Human-verified decisions must be preserved unless an explicit migration conflict is presented for review.

Data repair procedure:

```text
create safety backup
 -> inventory counts by old kind/source/status
 -> dry-run reclassification report
 -> show changed IDs + old/new kind + reason
 -> Owner-approved migration
 -> rebuild derived SQLite search index
 -> verify record counts / manual overrides / source provenance
```

No destructive bulk repair runs without the dry-run report.

### 14.6 Safe delete / tombstone policy

`DBD-HA-052-006` adds a visible `削除` action to Game Knowledge detail/edit, but deletion semantics depend on references.

The UI first shows an impact preview:

```text
candidate/review references
canonical entity/revision references
training samples
reference indexes
CGEL/evidence references
map/killer/perk relations
cached assets
```

Default policy:

- unverified import candidate + zero inbound semantic references: allow physical candidate-row removal;
- verified/canonical or referenced entity: default to tombstone/disable, removing it from normal search/recognition while preserving referential integrity;
- raw source snapshots/provenance are retained for audit and to prevent accidental re-import loops;
- hard purge is available only when the dependency graph reports zero protected inbound references and the operator confirms a second destructive action;
- derived SQLite/search/reference indexes are rebuilt or incrementally invalidated after delete/tombstone;
- a tombstoned exact source revision must not silently reappear on the next fetch. A genuinely newer external revision becomes review evidence, not automatic resurrection.

### 14.7 Survivor-subject hook/chase model

`DBD-HA-052-007` corrects the subject model.

`GENERATOR_REMAINING` is match-scoped. `HOOK_COUNT` and `CHASE_STATE` are Survivor-scoped.

Required observation identity:

```text
match_id
survivor_slot = 0..3
signal_kind = HOOK_COUNT | CHASE_STATE | SURVIVOR_STATE
value
confidence
source_frame
hud_profile_id
```

HUD/Profile and teacher-data implications:

- expose/calibrate Survivor-slot regions rather than one global hook/chase crop where the game HUD is slot-specific;
- video batch/single/manual registration requires or derives the target `survivor_slot` for hook/chase samples;
- reference-index records retain `survivor_slot`/subject scope;
- temporal state is maintained independently per Survivor slot;
- accumulated `HOOK` events cross-check visual hook count/stage for the same Survivor;
- one Survivor entering chase must never mark all Survivors as `CHASE_ACTIVE`;
- unknown/ambiguous slot association fails to `UNKNOWN`, not a guessed player.

### 14.8 Batch registration process-storm and UI-freeze contract

`DBD-HA-052-008` is a P0 operability defect because a valid learning action can create an uncontrolled process storm and effectively hang the application.

The `確認した画像を登録` phase MUST be architecturally separated from extraction.

Required pipeline:

```text
EXTRACT / PREVIEW
  -> bounded background crop generation
  -> staged receipts
HUMAN REVIEW
  -> selected staged IDs
CONFIRM
  -> filesystem/manifest commit only
  -> one bounded reference-index rebuild per affected domain
```

`CONFIRM` MUST NOT:

- start one FFmpeg/ffprobe process per registered sample;
- re-extract already staged frames;
- rebuild the complete reference index after every individual row;
- execute long work on the Tk main thread;
- open visible console windows.

Windows subprocess policy:

- use the shared persistent decoder where suitable;
- remaining CLI subprocesses run with the Product's no-console-window creation policy;
- child-process count is bounded;
- stale work is cancellable/coalesced where applicable.

Operator UX:

- progress shows `processed / total`, current phase and affected domain;
- Cancel is available before irreversible commit;
- large operations are chunked/bounded by the existing sample limit;
- failure preserves a receipt sufficient to retry or clean staging;
- closing/killing the app must not leave a partial registered set presented as complete;
- index rebuild happens once after the batch transaction and reports completion separately.

Performance Evidence MUST record at least:

```text
stage_count
confirm_count
subprocess_count
extract_seconds
commit_seconds
index_rebuild_seconds
total_seconds
cancelled
```

Windows acceptance uses the exact reproduced flow:

```text
画像学習データ
 -> 学習対象: 発電機 残0
 -> 確認した画像を登録
```

Pass requires no terminal-window storm, responsive UI/progress, bounded process count and a deterministically completed or cancelled result.

### 14.9 Atomic-unit mapping for the new defect backlog

The existing R0-R9 order remains authoritative. The new defects are inserted as bounded sub-units rather than renumbering the Task:

```text
R0A  Human Acceptance defect baseline + classification/source-detail inventory
R1A  Canonical entity taxonomy + source-section parser contract + migration dry-run
R1B  Human-first detail fields + safe delete/tombstone dependency policy
R1C  Map asset content-sniff/normalization + rotation rendering persistence
R2A  Survivor-scoped HUD/teacher contract for hook/chase
R2B  Batch visual registration worker/progress/no-console/index-rebuild hardening
R3   Temporal state machines consuming the corrected Survivor-scoped observations
R4+  Existing killer-specific/status-effect/Tier 3/4 roadmap
R9   Real Windows data repair + packaged Human Acceptance + backup/restore/performance
```

R0A/R1A data-quality repair MUST precede broad new recognition training so corrupted classifications and parser pollution are not amplified into reference indexes or Gold data.

### 14.10 Additional completion criteria

In addition to Section 12, TASK-052 cannot close until:

11. `DBD-HA-052-001` through `DBD-HA-052-008` each have source-level regression evidence and Windows Human Acceptance evidence;
12. existing Game Knowledge classification repair has a reviewed dry-run report and a post-migration count/provenance report;
13. no supported UI exposes `CHARACTER` as an operator entity category;
14. Survivor hook/chase state is demonstrably independent across all four Survivor slots;
15. the reproduced `発電機 残0` registration flow completes/cancels without visible terminal-window storm or Tk freeze;
16. map rotation regression includes both a normal image suffix and an opaque cached-image suffix;
17. delete/tombstone regression proves referenced data cannot be silently orphaned;
18. source-detail fixtures prove related navigation/perk links cannot populate unrelated Realm/Offering/entity facts.
