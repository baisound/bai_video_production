# TASK-051 R7N — End-to-End Knowledge / Map Intelligence / Editing Export

## Status

`IMPLEMENTED / WINDOWS_HUMAN_ACCEPTANCE_PENDING`

## Baseline and patch delivery rule

R7N is based on the Owner's applied R7L state. The Owner has **not** applied R7M. Therefore the R7N delivery patch is intentionally cumulative from R7L and includes the complete R7M implementation plus R7N. Applying the older standalone R7M patch first is not required and must not be mixed with this cumulative patch.

## Product correction

The DbD Training Studio is the data/knowledge/calibration authoring utility. It is not the final product goal. The downstream goal remains:

```text
source video
  -> observable Evidence
  -> game/entity/state understanding
  -> Canonical Game Event Timeline when evidence is strong enough
  -> Editing Intelligence
  -> Human review
  -> BAI VIDEO PRODUCTION / generic editing interchange
```

R7N restores a visible product path for using the trained data: `動画を解析・編集情報を出力`.

## R7M included capabilities

The cumulative R7N patch includes the unapplied R7M changes:

- dynamic Shared Media Fit-to-View instead of the 720x405 decode ceiling;
- packaged FasterWhisper Silero VAD assets and packaged-smoke checks;
- image-group presets/help (`normal`, `active`, `greyed`, `hard-negative`);
- 1024x512 upper-right OCR with PSM 7/6/11 multi-pass candidates.

## 1. Registered image/Crop review UX

`学習・登録データを確認 > 画像・Crop学習` is an image-review surface, not an ID-management table.

Required behavior:

- render a bounded thumbnail when the source image exists;
- open a larger aspect-ratio-preserving preview;
- filter by learning target;
- keyword-search target, label/name, ID, group, note, source and filename;
- replace raw label-ID editing with the shared visual/name search selector;
- correct-label selectors use Human-verified aliases only;
- rename ambiguous `すべて更新` semantics to `全タブを再読み込み`, and per-tab refresh to `この一覧を再読み込み`.

The reload buttons reread the current workspace. They do not fetch the web or retrain a model.

## 2. Game Knowledge review governance

External guide data is evidence/reference, not product truth.

UI vocabulary:

| Internal | Japanese UI |
|---|---|
| COMMUNITY_REFERENCE | 外部参考情報 |
| CANDIDATE | 取込候補 |
| VERIFIED | 確認済み |
| UPDATE_AVAILABLE | 更新候補あり |
| NEEDS_REVIEW | 要再確認 |
| DISABLED | 無効 |

A candidate cannot silently become a training correct-label. Visual correct-label selectors search verified aliases only.

### External refresh safety

A changed web record must not overwrite the last verified source data. If a verified record changes externally:

1. the verified source record stays active;
2. the new source snapshot is kept as `_pending_external_update`;
3. UI state becomes `更新候補あり`;
4. explicit Human verification accepts the pending source revision;
5. manual name/alias/image overrides survive the update.

Editing a verified record changes it to `要再確認`.

### Direct edit modal

A selected Game Knowledge row can be edited through a modal. The operator can change:

- Japanese official/display name;
- English name;
- aliases/nicknames as a comma-separated variable-length list;
- image override;
- enabled/disabled state.

The searchable Alias index is synchronized to the reviewed entity state so `確認済み` is usable in verified-only correct-label selectors.

## 3. Kamigame collection expansion

One `ゲーム情報を取得` operation collects the existing perk/killer information plus:

- Item list;
- Add-on list;
- Map list;
- Map detail pages and representative images when enabled.

Requested source pages are kept as bounded community-reference inputs. Raw HTML remains evidence; normalized JSONL remains review data.

### Item model

Item candidates retain category, rarity/descriptor, charge text, effect, aliases and image references.

### Add-on model

Add-on candidates retain owner-killer name, rarity/effect and image references. When the referenced killer exists in the same candidate corpus, the bridge also stores `owner_killer_candidate_id`. This keeps killer-specific add-ons, such as Hillbilly add-ons, relational instead of name-only.

### Map / Realm / Offering

Map detail extraction supplies map image candidates, Realm, Offering, feature text, favorability, pallet text, area and size. Realm and Offering are also derived into independent Game Knowledge candidates, giving them their own review/edit/verification lifecycle.

Downloaded representative images are cached under the import root. The raw web URL remains provenance; cached files are a local review convenience, not a new authority source.

## 4. Map Intelligence foundation

Map data is not stored as a simple label. R7N establishes a localization-ready schema.

### Canonical orientation

The source map image is never destructively rotated. The record stores:

- `rotation_deg`: 0/90/180/270;
- `orientation_locked`;
- `orientation_basis=USER_CANONICAL`;
- optional orientation note.

The Map Detail UI can toggle orientation editing and rotate right by 90 degrees. With Pillow available in the Windows build, the preview rotates visibly; the source image stays unchanged. Saving with editing OFF locks the displayed direction as Canonical Up.

### Location/training schema

Map Image Training foundation supports:

- Floor definitions;
- Region polygons using normalized UV coordinates;
- Landmark positions using normalized UV coordinates;
- exact training captures with source frame, floor, normalized `u/v`, heading and landmarks;
- viewpoint roles `SURVIVOR_1`, `SURVIVOR_2`, `SURVIVOR_3`, `SURVIVOR_4`, `KILLER`;
- persistent Map Training Dataset storage;
- future `MapLocalizationResult` with map/floor/u/v/heading/region/nearest-landmark/confidence and alternate candidate positions.

This is a data-contract/readiness implementation. R7N does **not** claim a trained real-time localization model.

## 5. Video analysis -> Editing Intelligence

A new `動画を解析・編集情報を出力` surface uses the shared media player and provides a real operator path from a DbD video to portable editing information.

### Current bounded runtime analysis

The surface performs:

- ffprobe video metadata;
- FasterWhisper transcription;
- upper-right OCR sampling with the current trained OCR vocabulary;
- reviewable `SPEECH` and `HUD_NOTIFICATION` findings;
- basic highlight scoring;
- generic marker CSV;
- transcript SRT;
- BAI VIDEO PRODUCTION handoff JSON;
- analysis manifest/JSON.

Weak ASR/OCR observations do not fabricate canonical game events. When a canonical Game Intelligence store already contains approved events, `DbDVideoEditingExportService` converts those canonical events into editing markers/highlights separately.

### Editing Intelligence contract

Canonical events may become:

- normal markers;
- highlights with pre/post roll;
- review-required markers for weak/uncertain canonical state.

The output includes highlight score, confidence and Human-review requirement.

### BAI VIDEO PRODUCTION handoff

`bai-video-production-handoff.json` is a portable, non-mutating handoff. It contains source timing and reviewable marker/suggested-clip information. Export never writes directly into a Human-owned production timeline.

## 6. Windows packaging

The Windows build extras now include Pillow for JPEG/WebP/PNG map/game image review. The Training Studio spec explicitly includes PIL modules. R7M's FasterWhisper package-data collection remains included.

## 7. Acceptance floors

R7N is not complete until Windows Human Acceptance verifies at least:

1. all Shared Media surfaces use the available viewport without large avoidable black unused areas;
2. FasterWhisper packaged transcription no longer fails because Silero VAD data is absent;
3. OCR multi-pass candidates are reviewable;
4. image-group help is understandable without internal knowledge;
5. image/Crop review shows thumbnails, filter/search and selector-based relabeling;
6. Game Knowledge can collect Item/Add-on/Map, show friendly states, edit aliases/image and verify a candidate;
7. a verified entity appears in verified-only correct-label search;
8. verified external data is not overwritten by a later changed fetch until Human acceptance;
9. Map Detail shows the map image when cached/overridden and visual 90-degree rotation works without rewriting the source file;
10. a DbD video can produce `analysis.json`, `editing-markers.csv`, `transcript.srt`, `bai-video-production-handoff.json` and `manifest.json`.
