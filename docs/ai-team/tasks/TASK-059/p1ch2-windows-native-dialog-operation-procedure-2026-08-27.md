# TASK-059 P1C-H2 Windows Native Dialog Operation Procedure

Document identity: `TASK-059-P1CH2-WINDOWS-NATIVE-DIALOG-OPERATION-PROCEDURE-20260827`

Version: `PRE-EXECUTION / 2026-08-27`

## 目的

P1C-H2が使用するWindows標準Credential UI境界について、秘密値を入力せず、
UIを開かないread-only native probeとsynthetic fixture testだけで、DLL
entrypoint、構造体、flag値、mutable buffer変換、zeroizationを確認する。

## 実施範囲

- Windows Python 3.12でfocused testを実行する。
- `credui.dll`をread-onlyでロードし、
  `CredUIPromptForCredentialsW` symbolの存在だけを確認する。
- `CREDUI_INFOW`の構造体sizeと固定flag値をread-backする。
- Windows Credential UI自体は起動しない。
- 実PPK、実公開鍵、実passphrase、実custody destinationを使用しない。
- DPAPI custody、署名、公開、昇格、Release、Deploy、Productionを実行しない。

## 手順

1. 対象worktree、branch、HEAD、dirty stateを確認する。
2. `PYTHONPATH`を対象worktreeの`src`へ限定する。
3. H2、既存native file dialog、H1のfocused testsを実行する。
4. Pythonから`credui.dll`をロードし、symbol有無、構造体size、flag値のみ出力する。
5. 出力にpath、鍵本文、passphrase、secret、private materialがないことを確認する。
6. Credential UIへの入力・クリックは行わない。
7. 結果を別result documentへ記録し、秘書へ原文送付する。

## Safety / Stop

- `computer-use` skillは認証ダイアログの自動操作を禁止しているため、自動入力・
  自動クリックを行わない。
- 認証ダイアログが予期せず表示された場合は入力せず閉じる。
- private key、passphrase、seedをconsole、文書、Git、PR、CIへ記載しない。
- install、download、settings変更を行わない。
- 実秘密値が必要になった時点で停止し、別Human Gateへ残す。

## Rollback

read-only probeとtestのみのため設定rollbackは不要。予期しないprocessが残った場合
は秘密値を入力せず終了し、結果を`NOT_CONFIRMED`として記録する。
