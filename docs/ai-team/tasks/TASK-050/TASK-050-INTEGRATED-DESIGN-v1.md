# TASK-050 Integrated Design v1

## 1. User workflow

Application startup:
1. Workspace selection/create
2. はじめに
3. 実行環境を設定
4. ゲーム情報を取得
5. HUD位置を設定
6. 動画から学習
7. 画像を追加登録
8. 右上通知を学習
9. 実況・豆知識を登録
10. 学習データを確認
11. バックアップ・復元

All ordinary user-visible strings are Japanese.

## 2. Workspace

Required:
- stable workspace_id
- editable display_name
- user-selected root path
- recent workspace registry
- default-workspace preference
- migration journal
- checksum-verified relocation
- no C-drive-only assumption

Suggested structure:
workspace.json
runtime-profiles/
hud-profiles/
training-data/
video-slices/
ocr/
trivia/
knowledge/
human-gold/
indexes/
receipts/
backups/

## 3. Runtime Environment Profile

Persist:
- profile_id / display_name
- Python executable
- FFmpeg executable
- FFprobe executable
- Tesseract executable
- FasterWhisper package/version
- model cache path
- default model
- device
- compute type
- OCR language

For each external tool show:
- configured/effective path
- source: AUTO_DETECTED / USER_OVERRIDE / PROFILE_SAVED
- detected version
- health
- last checked time

No secrets.

## 4. Japanese text catalog

User-visible text is centralized. Internal IDs remain English.
Raw enum names should not be shown in normal mode.

## 5. Contextual help

Nontrivial fields have:
- Japanese description
- examples
- allowed values
- multi/single information

Applies notably to:
- Category
- Tags
- Event Types
- Entity Refs
- Environment
- Runtime settings
- HUD parent/child regions

## 6. HUD Calibration

Video controls:
- -10 sec / -1 sec / -1 frame
- play/pause
- +1 frame / +1 sec / +10 sec
- timecode + frame index

ROI hierarchy:
- 左下：生存者状態 全体
  - 生存者1..4
- 左下：アイテム・アドオン 全体
  - アイテム
  - アドオン1
  - アドオン2
- 右下：パーク 全体
  - パーク1（上向き）
  - パーク2（右向き）
  - パーク3（下向き）
  - パーク4（左向き）
- 右上：通知
- サバイバー：心臓鼓動表示
- キラー能力表示エリア（任意）

Fine adjustment:
- whole ROI move 1px/5px
- each edge ±1px
- X/Y/W/H direct entry
- undo/redo/reset
- zoom preview

Persist normalized ROI with calibration source geometry.

## 7. Shared HUD visibility

VISIBLE
PARTIALLY_OCCLUDED
HIDDEN
UNREADABLE
UNKNOWN

Japanese:
通常表示
一部隠れている
完全に隠れている
読み取れない
判定できない

Used by Perk/Item/Add-on and where applicable other HUD observations.

## 8. Heartbeat

Calibration target: `heartbeat_hud`.

Observation:
- visible/visibility
- active
- intensity_milli 0..1000
- trend RISING/STABLE/FALLING/UNKNOWN
- confidence
- evidence
- provenance

Heartbeat evidence may feed proximity/chase/commentary/highlight inference but is not itself an exact killer-distance fact.

## 9. Video learning safety

Replace one-shot interactive mutation with:
Select -> Seek -> Source Preview -> ROI Preview -> Identity/Visibility -> Confirm -> Register -> Review

## 10. Visual training

Support:
- image picker
- drag & drop
- preview
- identity selector backed by Knowledge
- visibility selector
- optional notes
- advanced technical fields collapsed

## 11. Alias / reading

Generalized Knowledge Alias:
- official Japanese
- reading
- official English
- community short name
- nickname
- ASR variant
- common misspelling

Example:
鋼の意志 / はがねのいし / Iron Will / アイアンウィル / アイウィル

## 12. Trivia metadata UX

Category: selection
Tags: multi-token
Event Types: CGEL multi-select
Entity Refs: Knowledge search/multi-select
Environment: selection
All with persistent help.

## 13. Observation envelope

Every backend observation that may feed later logic must be able to carry:
- observation_id
- observation_type
- frame range/timecode
- visibility
- entity/state/intensity/trend
- confidence/candidates
- evidence_ref
- workspace_id
- runtime_profile_id
- hud_profile_id/version
- roi_id
- applied anchor offsets
- detector/model version
- knowledge revisions when resolved

Observation != Canonical Event.

## 14. Training data review

Provide counts, thumbnails, source frame/video, label, visibility, profile provenance.
Actions:
- relabel
- delete
- approve
- mark hard negative

## 15. Human Gold

Separate:
- identity correctness
- visibility correctness
- state correctness
- timing
- abstention

Metrics:
- Identity Precision/Recall/F1
- Visibility Accuracy
- Hidden Detection Accuracy
- Partial Occlusion Accuracy
- Unreadable Accuracy
- Abstention Correctness
- Timing Error
- Calibration Error

## 16. Error contract

Every user-facing failure has:
- Japanese title
- what failed
- likely cause if known
- next action
- stable error code
- copyable technical detail

No bare None.

## 17. Output

JSON/CSV/analysis exports can include:
frame/timecode
observation_type
entity_id
visibility
state
intensity_milli
trend
confidence
workspace_id
runtime_profile_id
hud_profile_id
roi_id
detector_version

## 18. Backup/Migration

Include:
Workspace metadata
Runtime Profiles without secrets
HUD Profiles/anchors
training data
indexes
OCR vocabulary
trivia
knowledge candidates
Human Gold
receipts

Restore is previewed and validated before mutation.

## 19. Implementation sequence

R1 Foundation:
Workspace + Runtime Profile + Japanese text catalog + ordered navigation + user error contract

R2 Calibration:
seek + ROI tree + pixel fine adjustment + zoom + heartbeat ROI

R3 Safe learning:
Preview/Confirm/Register + image preview + training data review

R4 Knowledge usability:
aliases/readings + trivia selectors/help

R5 Backend intelligence:
observation envelope + heartbeat trend + provenance + export

R6 Evaluation/migration:
Human Gold visibility metrics + Workspace migration + backup compatibility + packaged Windows regression
