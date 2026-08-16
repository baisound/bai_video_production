# TASK-047 P-OBS installer dev9 technical Evidence

## Outcome

`bai-voice-capture 0.1.0-dev.8` を OBS Studio 32.2.1 へ導入する、日本語・英語対応の
Windows installer candidate `installer.4` を実装した。これはローカル技術候補であり、
GitHub Release、一般配布、Production admissionを意味しない。

## Fixed inputs

- runtime ZIP SHA-256:
  `4e8fcdf6f697da059ef3aa9ae703a400d0f85e9ed89d77ace9f624dc2783e20f`
- Plugin DLL SHA-256:
  `14839bcad60fe47583a97729e3dc41c23b9f6c06012d5a83a38d8fc04b435b38`
- Controller SHA-256:
  `273fe96a952b1120b422785ee4c70a9612ba6f44c6d95f06447497abb52afb3f`
- Inno Setup compiler: `7.1.0`
- ISCC SHA-256:
  `d06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a`
- installer.4 SHA-256:
  `7f1dff48059f3eb292bae32185080d26a50303313e1128ee1286666bc9faabd6`
- installer Authenticode: `NOT_SIGNED`
- private synthetic acceptance receipt SHA-256:
  `bf17b36e5aeecf28496305325120b4944e9df6894bffa261993776266f41da29`
- private installer.4 real install/load receipt SHA-256:
  `5ca3df53d9b49834dca5da42d66bef8a9865b0c5919f077e8521d4881095b157`

Private operation root、OBS absolute path、Owner audio bodyはRepositoryへ記録しない。

## Implemented behavior

- OwnerがOBS rootを選択可能。public sourceへ固有machine pathを埋め込まない。
- OBS `32.2.1`、local path、OBS非起動、reparse、書込可能性、16 MB disk floor、
  existing exact3 SHAをinstall前に検証する。
- 内容が異なる既存Plugin fileは変更せず拒否する。
- Plugin exact3とControllerを別destinationへ導入し、OBSを自動起動しない。
- 初回のexisting/absent ownershipを保持し、Repair/Updateで上書きしない。
- install/repair journalはJSONL + SHA-256 predecessor chainで追記する。
- post-copy exact3 read-backが一致した場合だけverified completionとする。
- Uninstallはinstaller-owned exact3だけを除去し、preexisting exact3はbackupから復元する。
- OBS processはToolhelp snapshotで列挙し、probe失敗もfail closedにする。起動中の実OBSを
  用いたnegative testで配置前拒否とtarget不変を確認した。
- publish後に結果不明となった場合は`FAILED_PARTIAL_PUBLISH / UNKNOWN`としてauto rollbackせず、
  exact3とjournalをread/reconcileしてから別rollback transactionを判断する。

## Acceptance

Synthetic fake OBS root（real `obs64.exe` version resourceのみ複製）で以下を実測した。

- clean install: `PASS`
- same-version repair: `PASS`
- exact3 read-back: `PASS`
- append-only journal JSON/hash/predecessor chain: `PASS`
- collision refusal / foreign file unchanged: `PASS`
- verified uninstall: `PASS`
- preexisting exact3 adoption and restore: `PASS`
- real OBS mutation during synthetic test: `false`
- Owner voice recording: `false`

Exact targetでは、manual-installed exact3とpayloadが3/3一致することを確認してから
installer.4管理へ移行した。移行後もOBS 32.2.1 logに
`bai-voice-capture.dll`とPlugin log markerが現れ、通常終了後のOBS processは0だった。
録音、Source/Filter/device/gain変更は行っていない。

無人更新の初回呼出しではcallerが空白を含む`/OBSROOT`を分割し、installerは配置前に
安全停止した。target 3 file不変をread-back後、quoted argumentで実行して成功した。
これはinstaller preflightの失敗ではなくcaller contractの検証結果であり、例示commandでは
空白を含むpath全体を引用する。

Repository validation:

- focused installer contract: Windows `7 PASS`, WSL2 `7 PASS`
- exact runtime/ISCC hash build: `PASS`; installer SHA-256 reproduced exactly
- Windows full regression: `1269 PASS / 1 SKIP`
- WSL2 full regression: `1270 PASS`

## Remaining gates

- Authenticode code signing、publisher identity、public distribution: `OWNER/RELEASE_GATE`
- recording destination、visible recording state、gain checkのOwner voice実測:
  `OWNER_RECORDING_GATE`
- interrupted publishを強制発生させるdestructive test: `SEPARATE_TEST_GATE`
- `P_OBS_PLUGIN_DEVELOPMENT_COMPLETE`: `NOT_ESTABLISHED`

## Critic self-pass 1

Initial findings:

1. Repairがinstaller-owned exact3をpreexistingと誤認した。
2. journal内Windows pathがJSON escapeされず、parserで再検証不能だった。
3. 初期OBS候補に開発機固有pathが残っていた。

Corrections:

1. 初回ownership stateをRepair/Updateへ継承し、uninstallを再試験した。
2. JSON escapingとpersistent journal headを追加し、install+repairの6-entry chainを再計算した。
3. defaultをportableなProgram Files候補へ変更し、`/OBSROOT`またはwizard選択を正本にした。

## Critic self-pass 2 / Judge

- private path/public leak: 0
- unrelated Repository path mutation: 0
- synthetic acceptance unresolved Critical/High: 0/0
- real target Plugin load after installer migration: `PASS`
- Production/Release/Owner voice authority inflation: 0

Judge: `PASS_LOCAL_TECHNICAL_INSTALLER_CANDIDATE`.
