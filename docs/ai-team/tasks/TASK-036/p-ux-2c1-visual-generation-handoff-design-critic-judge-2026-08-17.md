# TASK-036 P-UX-2C1 Visual Generation Handoff

## Decision

- Unit: `P-UX-2C1 Visual Generation Handoff`
- canonical base: `43a5afc392b8c0f4e034d73db01af1ea79e4b182`
- owner: 開発担当
- scope: Visual only. Audio は開発担当2へ委譲し、集計対象を常に0件とする。
- effect: read-only projection only
- selected terminal: `TASK036_PUX2C1_VISUAL_HANDOFF_READY`

## Problem and non-duplication boundary

P-UX-1Cまでに Shot Feasibility、Prompt Evidence、Generation Queue、local
Execution、生成済みOutputの監査候補登録、Candidate Audit/Human Decision、
Production Controlの各操作は個別に接続済みだった。一方、Image/Video画面には
Scene/Slot単位でこれらのreceiptを一列に突合する表示がなく、後段receiptだけを
見て上流の欠落やSTALEを見落とす余地があった。

本Unitは既存Applicationやstoreを再実装しない。次のcanonical snapshotを
read-onlyに合成する。

1. TASK-037 Production Control Slot/Candidate
2. TASK-013 current Shot Feasibility
3. TASK-040 versioned Prompt Evidence
4. TASK-027 Generation Queue admission
5. TASK-013 local execution terminal
6. TASK-027 output adoption / audit-candidate receipt

## Deterministic contract

対象Slot kindは `START_FRAME / END_FRAME / CHARACTER_REFERENCE /
SPACE_REFERENCE / COMPOSITION_REFERENCE / VIDEO / VFX` のclosed setである。
`SE / BGM / AMBIENCE / NARRATION / OTHER` は対象外であり、Audio ownerは
`DEVELOPER2`、`audio_slot_counted=0` を出力する。

各sourceはexact `project_id` とcanonical snapshot SHA-256を持つ。Executionは
Queue snapshot SHAにも一致しなければならない。Slot、Safety Scene、Prompt
version、Queue prompt version、Execution queue identityのduplicate、unknown Slot、
cross Project/Scene/Slotはrejectする。Promptは同じSlotの最大versionだけをcurrent
とし、過去version件数は `stale_prompt_count` に残す。

上流優先の状態遷移は次のとおり。

```text
STALE
  -> FEASIBILITY_REQUIRED/BLOCKED
  -> PROMPT_REQUIRED
  -> PROMPT_READY
  -> QUEUED_NOT_EXECUTED
  -> EXECUTION_IN_PROGRESS/RECOVERY_REQUIRED/FAILED_KNOWN/UNKNOWN
  -> OUTPUT_READY_FOR_ADOPTION/OUTPUT_ADOPTION_BLOCKED
  -> READY_FOR_AUDIT
  -> ACCEPTED_ASSET
  -> LOCKED_ASSET
```

Required Visual Slotを閉じるのはexact1のcurrent Human `ACCEPTED` または `LOCKED`
Candidateだけである。`COMPLETED`、`READY_FOR_ADOPTION`、`READY_FOR_AUDIT` は
Asset adoption完了へ昇格しない。Required Slotが0件の場合もall-adoptedとはしない。

projectionはcanonical JSONからSHA-256を生成するが、新しいProduct truthや
永続状態を所有しない。Provider execution、Human Decision、Asset/Timeline mutation
のauthorityはいずれもfalseである。

## UI handoff

V6.1.1 Image GenerationはStart/End/reference kind、Video GenerationはVIDEO/VFXを
同じprojectionから表示する。各行は不足するcanonical画面へ移動するだけで、操作を
代行しない。

- Feasibility不足: Start/End画像生成
- Prompt不足: Scene Design / Prompt Evidence
- Queue/Execution/Adoption不足: AI動画 / Generation Queue
- Audit待ち: Asset Review
- Accepted/Locked: WORLD LOCK

## Verification

- focused: visual projection、Shell bridge、V6.1.1 visual contract
- regression: TASK-013/027/036関連、続いてrepository full suite
- static: Python compile、embedded JavaScript syntax、`git diff --check`
- negative: missing source、invalid SHA、cross project/scene/slot、duplicate、STALE、
  DISPATCHING、completed-without-adoption、audit-without-Human adoption
- path scope: exact8

## Critic

### Builder / Completeness

初稿は後段Queueが存在するとFeasibility欠落を隠した。上流Gateを先に評価するよう
修正した。またduplicate Safety Scene/Executionを上書きせずrejectし、Prompt
versionをpositive integerへ限定した。未解決 C/H/M=`0/0/0`。

### Security / Authority

project_id、queue snapshot、Scene/Slotのcross-scope borrowingを拒否するよう修正した。
AudioをVisual集計へ含めず、ProjectionからProvider/Human/Asset/Timeline authorityを
生成しない。秘密・path・raw bytes・runner/callback APIを追加していない。
未解決 C/H/M=`0/0/0`。

### Operations / Compatibility

既存6 Applicationのsnapshotだけを読み、新store、schema、export、dependencyを追加
しない。旧画面操作とBridge methodを変更せず、UIは不足段へのnavigationだけを行う。
STALE/UNKNOWN/RECOVERY_REQUIREDは自動retryしない。未解決 C/H/M=`0/0/0`。

## Independent Judge

`JUDGE=PASS_LOCAL_PENDING_HOSTED_EVIDENCE`

Local Evidence:

- focused regression: `104 passed`
- repository full regression: `1774 passed, 1 skipped`（Windows-only Inno Setup）
- embedded JavaScript syntax: `PASS`
- Python import/compile through full suite: `PASS`
- `git diff --check`: `PASS`

Acceptance predicates:

- exact8以外の変更0
- focused/full regression PASS
- deterministic hash and fail-closed negative matrix PASS
- hosted checks terminal SUCCESS
- fresh base/head/path/Lock equality
- unresolved Critic C/H/M=`0/0/0`

Real Provider、media、Audio、Human decision、Asset/Timeline mutation、Native H3、
Release/Deploy authorityは本結果から推定しない。
