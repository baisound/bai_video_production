# TASK-052 R1A — Canonical Taxonomy / Entity Detail Root / Migration Dry-run

Status: `DESIGN_BOUND`
Profile: `DEV-3 HIGH ASSURANCE`
Atomic Unit: `R1A`
Defects: `DBD-HA-052-004`, `DBD-HA-052-005`

## 1. Goal

R1A prevents weak page context and legacy taxonomy from becoming canonical DbD facts.
It introduces one backward-readable but operator-hidden legacy category, a fail-closed
unknown category, a structurally bounded Kamigame article parser, and a read-only
migration planner. It does not mutate the Owner workspace.

## 2. Context and evidence boundary

The unit used only TASK-052 current authority/design, the TASK-049 Kamigame collector
contract, the current catalog/classifier/UI implementations, their focused tests, and
read-only samples from the current Owner workspace.

Observed current-data baseline:

- four known Survivor rows are stored as legacy `CHARACTER`;
- the map import contains unrelated page/article rows and derived Realm/Offering rows;
- `究極の武器` and `素早い残虐行為` occur as both correct Perk rows and incorrect
  Realm/Offering-derived candidates;
- all current review rows are `CANDIDATE`; nevertheless migration code must preserve
  Human overrides and review state for future datasets;
- multiple Killer and map/detail pages share the same article-root ancestry.

No current Workspace file is an implementation source of truth and no Workspace path
may be copied into repository evidence.

## 3. Canonical taxonomy contract

`GameKnowledgeKind` gains `UNKNOWN`.

`CHARACTER` remains readable only for backward compatibility. It is not a supported
operator category and must not be emitted by new classification decisions.

Classification priority remains:

```text
explicit/manual
 -> article semantics
 -> known entity master
 -> structurally scoped source metadata
 -> source-kind fallback
```

Additional constraints:

1. Known Survivor names including トーリー, ドワイト, ナンシー and ネア resolve to
   `SURVIVOR`.
2. Explicit legacy `CHARACTER` is migration input and resolves to `UNKNOWN`, unless a
   stronger known-entity rule proves `SURVIVOR`.
3. A `キャラクター`/`登場人物` source heading does not prove Survivor identity and
   resolves to `UNKNOWN`.
4. Absent source kind resolves to `UNKNOWN`, not `MECHANIC`.
5. UI label/filter dictionaries expose `UNKNOWN` as `未分類・要確認` and omit
   `CHARACTER` entirely. A legacy row that is displayed through a summary fallback uses
   the same review label rather than the removed operator taxonomy term.

## 4. Structural parser contract

### 4.1 Validated template

Read-only inspection of multiple current Killer and map/detail pages found one shared
template fingerprint:

```text
template_id = KAMIGAME_ARTICLE_MAIN_V1
ENTITY_DETAIL_ROOT = main#main.article > article
```

The parser accepts the template only when:

- the `main` element has `id=main` and class token `article`;
- its direct child is `article`;
- the accepted article contains a non-empty `h1`.

The central `article` descendant is the data boundary. Sibling `aside`/`nav` content is
outside the boundary even though it remains inside `main`.

### 4.2 Exclusion and termination

Within the accepted root, these structural descendants are excluded:

- `aside`, `nav`, `footer`;
- nested class/id tokens representing advertisements or inline-ad placement,
  information footer, recommendation/ranking/sidebar/navigation containers. The
  observed `article_inline_ad_target` wrapper itself remains in scope because it owns
  both article facts and nested ad placements;
- the terminal related-content marker `h2#関連リンク` and all subsequent article
  content.

Visible Japanese text is not used to discover the root. Heading semantics may classify
an already-scoped section, and the existing structural heading `id` may terminate the
fact region.

Unknown or changed root structure produces:

```text
template_id = UNKNOWN
structure_status = UNKNOWN_STRUCTURE
typed facts = empty
requires_human_review = true
```

### 4.3 Typed-fact rules

- Killer detail metadata is derived only from headings/rows/images captured inside the
  accepted root. Each heading is assigned one of the TASK-052 section kinds; unmatched
  headings remain `UNKNOWN_SECTION`.
- Map-list candidates are accepted only from the structurally scoped
  `各マップ個別一覧` section. Page-header quick links, unrelated article tables,
  related links, navigation and sidebars cannot become map candidates.
- Realm/Offering facts require an in-root two-column header row containing both
  `領域名` and `オファリング`, followed by the corresponding linked data row.
- Pallet/area/size facts require the scoped `板 / 面積 / 広さ` header followed by its
  data row.
- No generic “first two links in a table” fallback is allowed.
- Provenance includes `template_id`, `structure_status`, and the bounded section
  classification.

## 5. Migration dry-run contract

The migration planner is pure/read-only. It accepts catalog records and returns an
immutable report containing:

- counts by old kind and proposed kind;
- changed candidate ID, old kind, proposed kind and reason;
- unchanged and Human-protected counts;
- conflict/review-required rows;
- `apply_performed = false`.

Rules:

1. A legacy `CHARACTER` matching the known Survivor master proposes `SURVIVOR`.
2. Any other legacy `CHARACTER` proposes `UNKNOWN` with Human Review.
3. A non-`CHARACTER` row may be proposed for reclassification only when the
   deterministic classifier provides a stronger result than its weak current source
   kind.
4. Manual names/aliases/images, enabled state, review status, details, timestamps and
   provenance are never modified by dry-run planning.
5. `VERIFIED`, `UPDATE_AVAILABLE`, `NEEDS_REVIEW`, manual-override or otherwise
   Human-touched rows are reported as protected conflicts when the proposed kind
   differs; they are not silently migrated.
6. No deletion is proposed in R1A. Polluted derived Realm/Offering deletion/tombstone
   is governed by R1B dependency policy.

Actual repair remains gated by:

```text
safety backup
 -> reviewed dry-run report
 -> explicit Owner migration approval
 -> apply
 -> derived-index rebuild
 -> count / override / provenance verification
```

## 6. Allowed files

- canonical DbD knowledge enum/classifier;
- Kamigame collector/parser and candidate bridge;
- DbD operator label/filter mappings;
- a bounded R1A migration-planner module;
- focused TASK-049/TASK-051/TASK-052 tests;
- TASK-052/current-state/task-index evidence.

## 7. Prohibited side effects

- no Owner Workspace mutation;
- no external fetch or paid/provider call;
- no delete, tombstone application or index rebuild;
- no protected-main push, merge, release, deploy or Production Activation.

## 8. Acceptance

R1A passes when:

1. known Survivor regression cases classify as `SURVIVOR`;
2. new classification never emits `CHARACTER`;
3. supported operator UI does not expose `キャラクター`;
4. accepted structural fixtures exclude related/sidebar/adversarial facts;
5. unknown structure fails closed with no Realm/Offering fact;
6. map-list parsing excludes unrelated page tables;
7. migration dry-run reports old/new/reason and preserves Human-touched rows;
8. focused and affected regression tests pass;
9. Critical/High Critic findings are zero before commit-ready closure.
