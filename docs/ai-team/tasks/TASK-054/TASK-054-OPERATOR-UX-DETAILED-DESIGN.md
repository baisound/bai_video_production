# TASK-054 — DbD Tuned LLM Operator UX Detailed Design

Status: `DESIGN COMPLETE / IMPLEMENTATION GATED`

## 1. UX principle

The UI is not a generic ML dashboard. It is a DbD commentary-improvement
workspace embedded in the existing BAI Video Production Game Intelligence and
Training Studio experience.

Reuse the Product's proven patterns:

- Japanese Human language;
- browse/search/filter and scrollable forms;
- explicit workspace and revision identity;
- preview before commit;
- progress, elapsed/remaining estimate and safe Cancel;
- unified review counts and Approve/Correct/Reject;
- Backup/Restore and credential exclusion;
- read-only diagnostics collapsed by default;
- no terminal-window storm and no frozen Tk UI.

Specialize them for model work so the Operator thinks in `解説を良くする` rather
than optimizer/library jargon.

## 2. Information architecture

```text
Game Intelligence / DbD
├── イベント
├── 解説候補
│   ├── 候補を作る
│   ├── 根拠と判定
│   └── 採用・修正・却下
└── 解説AI設定
    ├── はじめに（Setup Wizard）
    ├── モデル
    ├── 学習素材
    ├── 学習ジョブ
    ├── モデル比較
    ├── 運用設定
    └── 履歴・復旧
```

Training Studio links directly to `学習素材` and `モデル比較`. Runtime review
links directly to `解説候補`. Users never navigate through unrelated Planning,
Image, Video or Provider screens to complete a DbD commentary task.

`学習素材` has a dedicated `動画の実況・解説から追加` entry. Narration learning
is not hidden inside generic file import.

### Primary journeys and navigation budget

| Goal | Start | Required route | Target interaction budget |
|---|---|---|---:|
| Evaluate without training | 解説AI設定 | Wizard -> 事前チェック -> baseline evaluation | 7 primary actions |
| Add reviewed learning material | Training Studio review | `学習素材へ追加` -> preview -> confirm | 3 primary actions |
| Start authorized training | 学習ジョブ | plan -> preflight -> Gate summary -> execute | 4 primary actions |
| Review model quality | notification/dashboard | model comparison -> rubric -> submit | 2 + scoring |
| Generate commentary | reviewed Event | 解説候補を作る -> execute -> review | 3 primary actions |
| Roll back | 運用設定 | current binding -> previous/baseline -> verify | 3 primary actions |

The budget excludes optional details and mandatory Gate confirmation. No journey
requires copying an ID/path between screens. Deep links carry workspace/entity/
revision identity and revalidate it on arrival.

### Navigation context contract

```json
{
  "workspace_id": "...",
  "screen": "MODEL|DATASET|JOB|COMPARE|RUNTIME|RECOVERY",
  "entity_id": "...",
  "expected_revision": 1,
  "return_route": "...",
  "filter_state": {},
  "selection_ids": []
}
```

Secrets, raw paths and uncommitted form bodies are excluded. Stale deep links open
read-only comparison (`表示時の版` vs `現在の版`) before any action.

## 3. Persistent header

Every TASK-054 screen shows a compact status strip:

```text
Workspace: DbD Training
運用モデル: ベースライン
候補モデル: dbd-commentary-ja-v1 r1（評価済み・未承認）
学習素材: dbd-ja-001 r3 / 1,248件
Gate: 学習実行の承認待ち
```

Above it, a two-option mode control is always visible:

```text
[確認モード（学習しない）]   [学習モード]
```

Confirmation mode uses blue/read-only treatment and states `この操作ではモデルも
学習素材も変更されません`. Learning mode uses amber treatment and states the
current Dataset/training Gate. Color is not the only distinction. Mode cannot
change while analysis/training is running.

Color is supplementary: status always has text/icon. Clicking a status opens the
exact receipt/revision. No raw hash dominates normal UI; `詳細` reveals it.

## 4. First-run Setup Wizard

Entry button: `解説AIの準備を始める`.

Steps:

1. **目的** — `まず評価だけ` (recommended), `既存モデルを使う`, `学習を準備`;
2. **実行環境** — GPU/RAM/storage/runtime cards with `利用可能`, `不足`, `未確認`;
3. **ベースモデル** — Japanese quality, rights, estimated resource, JSON score;
4. **学習素材** — admitted revision, rights, split/leakage/unknown coverage;
5. **安全確認** — what will/will not happen and current Human Gates;
6. **実行計画** — exact duration/storage/cost estimate and output location;
7. **確認** — `事前チェックのみ` remains the default action.

The Wizard may save a draft plan without performing a download, Provider call or
training. Returning later resumes at the first incomplete safe step.

`まず評価だけ` configures `確認モード（学習しない）`. `学習を準備` configures
`学習モード` but stops at Gate/preflight until separately authorized.

Wireframe:

```text
┌ 解説AIの準備 ─────────────────────────────────────────────┐
│ 1 目的 ●─ 2 環境 ●─ 3 モデル ○─ 4 素材 ○─ 5 安全 ○─ 6 計画 ○ │
├───────────────────────────────────────────────────────────┤
│ [おすすめ] まず評価だけ                                   │
│   ダウンロード: なし  学習: なし  外部送信: なし          │
│                                                           │
│ [ ] 既存の承認済みモデルを使う                            │
│ [ ] 学習を準備する（実行には別承認が必要）                │
├───────────────────────────────────────────────────────────┤
│ 詳細は保存済みです                      [戻る] [次へ]      │
└───────────────────────────────────────────────────────────┘
```

## 5. Model screen

List columns visible by default:

```text
表示名 | 役割 | 状態 | 日本語 | JSON安定性 | 必要GPU | 権利 | 最終評価
```

Primary actions:

- `比較に追加`;
- `詳細を見る`;
- `事前チェック`;
- `承認を申請` (creates proposal only);
- `一時停止` / `失効` for authorized maintainers.

Advanced fields—base model ref, adapter digest, tokenizer, quantization, route,
schema versions—live under collapsed `技術詳細`. There is no ambiguous `Use`
button. Runtime selection says `この承認済みモデルを解説候補で使用` and shows
the rollback target before commit.

## 6. Learning-material screen

### Narration/commentary intake journey

```text
動画の実況・解説から追加
 -> source video and rights status
 -> audio/ASR/speaker extraction preview
 -> Event Timeline alignment
 -> segment transcript correction
 -> 実況/解説/戦術/反応/つなぎ/雑談/不明 tagging
 -> privacy/person-specific-style check
 -> Dataset candidate preview
 -> Human confirm
```

The review screen synchronizes video, waveform, transcript and Event Timeline.
Selecting a transcript segment seeks the video; moving the playhead highlights the
speaker turn and aligned Event. The Operator can drag segment boundaries and mark
`重なり発話`, `聞き取れない`, `Event不明` without inventing content.

Primary controls:

- `実況` (what is happening), `解説` (why it matters), `戦術`, `反応`, `つなぎ`,
  `雑談/除外`, `不明/要確認`;
- `文字を修正` preserves original ASR and correction provenance;
- `Eventを選び直す` shows only temporally nearby Events;
- `話さない例として採用` stores a timing-negative candidate;
- `学習候補へ追加` never mutates a frozen Dataset revision directly.

Speakers display as `話者A/B/...` or approved pseudonyms. Voiceprint, real
identity and voice-clone controls are absent from TASK-054.

DbD-oriented filters:

- patch, Killer, Map, Event, locale;
- `実況寄り / 解説寄り / 戦術寄り`;
- `確定情報 / 推定を含む / 正しい棄権`;
- rights/reviewer status;
- Train/Validation/Test and source group;
- rejection reason and hard-negative class.
- source kind: Human authored / narration実況 / narration解説 / silence negative;
- speaker/ASR/alignment review state.

Row preview has five side-by-side sections:

```text
映像・Eventの根拠
Canonical Knowledge / RAG
人が期待した判断
期待する解説
権利・Review履歴
```

Test rows are visually locked. The UI never reveals held-out target text during
tuning. Duplicate/leakage warnings link both conflicting source groups and offer
`修正候補を作る`, not silent reassignment.

## 7. Training-job screen

Normal view:

```text
準備 100% -> Dataset監査 100% -> 学習 42% -> 評価 待機 -> 隔離保存 待機

経過 00:37:12 / 推定残り 00:51:00
GPU 18.2/24 GB | Disk +31 GB / ceiling 60 GB
現在: Epoch 1 / 2, Step 820 / 1950
```

Primary actions: `安全にキャンセル`, `詳細を表示`. Pause appears only if the
runtime supports atomic checkpoint pause. Cancel explains what is kept and what
is discarded before confirmation.

Advanced view contains loss, LR, gradient norm, checkpoint and device details.
Warnings translate into an operator action:

- `GPUメモリ不足 — バッチを小さくした新計画を作成できます`;
- `Datasetの権利確認が失効 — 学習は開始していません`;
- `保存容量の上限に到達 — 安全に停止しました`.

No automatic retry changes a hyperparameter or budget.

### Background action contract

Every long action sends an immutable request with:

```text
action_id / idempotency_key
workspace_id
expected_dataset_revision
expected_binding_revision
plan_sha256
authorization_ref (reference only)
resource_ceiling
cancel_policy
```

The worker emits `QUEUED/RUNNING/CHECKPOINTING/CANCELLING/COMPLETED/FAILED` plus
bounded phase/current/total/elapsed/estimated-remaining. Repeated clicks reuse the
same idempotency key and never start a second job.

## 8. Blind comparison screen

The central TASK-054 decision screen shows one Event/context and candidates A/B/C.
Model identity remains hidden until submission.

Reviewer controls:

```text
事実: 正しい / 誤り / 判断不能
推定の慎重さ: 適切 / 強すぎる / 弱すぎる
役立ち度: 1..5
自然さ: 1..5
テンポ・長さ: 短い / 適切 / 長い
採用: A / B / C / すべて不採用
理由（必須条件に応じて）
```

Keyboard: `1/2/3` choose candidate, `R` reject all, `Space` media play/pause,
`[`/`]` previous/next Event. Shortcuts never submit without a visible confirmation
state. Screen reader labels include candidate and rubric context.

After submit, reveal route identity and show why the choice matters. Reviewer
cannot edit an earlier decision; correction creates a new review revision.

## 9. Runtime commentary screen

### Ordinary-video confirmation mode

The primary mode-specific flow is:

```text
確認モード（学習しない）
 -> 動画を選ぶ
 -> 現在の実況・解説を確認
 -> analysis progress
 -> time-aligned Commentary Preview
```

Preview layout combines the video player, Event Timeline and commentary lane.
Commentary blocks display intended start/end, `実況|解説|戦術|反応`, text,
confidence and validation. Selecting a block seeks the video. The Operator can
play `前後10秒`, `解説あり`, and `解説なし` for comparison. Optional TTS preview
is a separate existing Voice/TTS Gate; text/timing preview works without it.

The footer continuously states:

```text
学習データ: 変更なし
モデル: 変更なし
この確認結果から自動学習: しない
```

No `学習する` action exists in this mode. To learn, the Operator must end Preview,
select `学習モード`, and enter the separate reviewed intake flow.

### Learning mode

The same video/timeline layout adds an amber `学習候補` lane. Generated text is
visually marked `AI候補・まだ教師データではありません`. Only after Human
correction/approval can a segment move to Dataset staging. A staged count and
target Dataset revision are always visible. Training starts from the dedicated
Job screen, producing a new adapter revision rather than changing the active one.

For a reviewed Event:

```text
[解説候補を作る]
Model: ベースライン ▼
Expected: 約4秒 / free local
Context: 8 facts, 5 Evidence, 3 Knowledge, 2 RAG
```

Before execution, a one-panel summary shows model/binding approval, Provider/local,
cost ceiling, data leaving the machine, expected duration and fallback. The action
label distinguishes `ローカルで実行` and `Providerへ送信して実行`.

Result tabs:

- `解説` — clean proposed wording;
- `根拠` — Evidence/Knowledge/RAG citations;
- `判断の区分` — Observed/Canonical/Inferred/Tactical;
- `検証` — PASS/errors/uncertainty;
- `実行詳細` — route/tokens/latency/digests.

Primary decision row: `採用`, `修正して新候補`, `却下`. Production adoption is a
separate downstream action and is never combined with `採用`.

Wireframe:

```text
┌ Event: HOOK / revision 3 ─────────────── Model: ベースライン ▼ ┐
│ 根拠 5件 / Knowledge 3件 / RAG 2件  約4秒  ローカル・無料      │
│                                     [解説候補を作る]           │
├───────────────────────────────────────────────────────────────┤
│ 解説 | 根拠 | 判断の区分 | 検証 | 実行詳細                     │
│                                                               │
│ 「ここは救助タイミングを遅らせ、発電機の進行を優先しています」│
│                                                               │
│ 検証: PASS   推定: LIKELY   引用: 3/3                          │
├───────────────────────────────────────────────────────────────┤
│ [却下] [修正して新候補]                         [採用]          │
└───────────────────────────────────────────────────────────────┘
```

## 10. Failure and recovery UX

Every failure panel answers:

1. 何が起きたか;
2. データは安全か;
3. 何が保存されたか;
4. 次にできる安全な操作;
5. 再試行で費用/外部送信が発生するか.

Examples:

- stale context: `Eventが更新されました。新しい根拠で候補を作り直す`;
- malformed output: `モデル出力を採用しませんでした。費用を確認して1回だけ再試行`;
- missing runtime: `ベースラインへ切替` only if approved fallback exists;
- revoked model: `このモデルは使用停止です。過去の候補は履歴で確認できます`;
- interrupted training: `検証済みCheckpointから再開計画を作る`.

Raw traceback is under copyable `技術詳細`; the main message uses Japanese Human
language and a stable error code.

## 11. Safety interaction design

- destructive-looking actions say exact target/revision and consequence;
- training/download/paid/external actions require current Gate summary;
- credentials are configured in the existing Connections UI and never shown here;
- `承認` and `有効化` are different actions on different screens;
- default runtime remains baseline/disabled;
- revoked/suspended models cannot be selected;
- fallback is opt-in and always displayed;
- Dataset Test split cannot be moved/edited from normal UI;
- Review correction never overwrites original output.

### Action severity

| Level | Examples | Confirmation |
|---|---|---|
| L0 read | browse/filter/open receipt | none |
| L1 reversible local | save draft/filter preset | immediate + undo where useful |
| L2 compute/no external | local preflight/evaluation | resource summary |
| L3 gated external/expensive | download/train/Provider call | Gate + cost/data summary + explicit action |
| L4 authority/state | approve/activate/revoke/adopt | exact revision, impact, rollback and separate confirmation |

Buttons never share an ambiguous label across severity levels.

## 12. Accessibility and responsive layout

- minimum supported 1280×720 plus repository-supported scale settings;
- scrollable content, sticky primary action/footer and no clipped Gate summary;
- logical tab order, visible focus, complete UI Automation names/roles;
- no color-only state; 200% text zoom and Narrator acceptance;
- long model/dataset IDs wrap or copy without expanding the whole layout;
- media keeps a usable minimum height while forms scroll independently;
- background jobs never block window movement, navigation or Cancel.

## 13. UX acceptance scenarios

1. new Operator reaches `事前チェックPASS` without opening technical details;
2. Operator can explain whether an action downloads, trains, pays or uploads;
3. admitted Dataset revision and held-out lock are visible;
4. long training stays responsive and safely cancels;
5. blind comparison completes by mouse and keyboard;
6. reviewer distinguishes observed fact, canonical fact, hypothesis and expression;
7. invalid model output cannot expose an active `採用` action;
8. stale/revoked/missing-runtime states offer only safe next actions;
9. rollback to baseline is understandable and verified after restart;
10. 1280×720, increased scale and Narrator have no hidden primary action;
11. no console windows appear during model/Dataset/background operations;
12. Operator can reach receipt/diagnostic details without those details dominating
    the normal DbD-specific workflow.
13. Operator can extract narration, correct ASR, distinguish実況 from解説, align
    it to an Event and create a Dataset candidate without using a CLI;
14. overlapping/uncertain/private/person-specific narration cannot be silently
    adopted, and no voice-clone control appears in this LLM workflow.
15. Confirmation mode generates time-aligned実況/解説 from an ordinary video while
    Dataset/model/binding/job state remains byte-for-byte/revision-for-revision
    unchanged;
16. Learning mode visibly stages only Human-approved targets and creates new
    Dataset/adapter revisions without online self-learning or in-place overwrite.
