# TASK-059 P1C-G2 Windows Build / Operation Procedure

Date: `2026-08-27`

Document identity:
`TASK-059-P1CG2-WINDOWS-BUILD-OPERATION-PROCEDURE-20260827`

Status: `EXECUTED_PASS`

## 目的

既存の統合Product `BAI Video Production.exe` と、署名鍵取込時だけ親
processから起動される内部helperを同じone-dir packageへ構成し、秘密値を
使わずにbuild identityと最小起動contractを確認する。

この手順は第2のユーザー向けProductを作らない。PPK、公開鍵、passphrase、
private key、seed、DPAPI custody、署名は扱わない。

## 実施前条件

1. 対象branchとHEAD、dirty stateを確認する。
2. Windows Python 3.12とPyInstaller 6.22.0を既存環境からread-backする。
3. `build-windows-exe.bat --help`がinstall、download、署名、Release、
   Deployを行わないことを確認する。
4. 実鍵、passphrase、Provider credentialを環境変数、argv、ログへ置かない。
5. Main UI、Project、Resolve、Cubaseを起動しない。

## 実行手順

repository rootで次だけを実行する。

```bat
build-windows-exe.bat
```

batchは次を順に実行する。

1. `packaging/task059_ppk_helper.spec`から内部one-file helperをbuildする。
2. helperの絶対pathをbuild process内だけの
   `BVP_TASK059_HELPER_EXE`へ設定する。
3. canonical `packaging/task036_shell.spec`を使いMain one-dirをbuildする。
4. Main specがhelper SHA-256を生成moduleへ固定し、同じhelper bytesを
   Main EXEの隣へ`EXECUTABLE`として収集する。
5. staging helper、bundle helper、生成moduleのdigest一致をbody-free
   verifierで検証する。
6. bundle helperをprotocol v1 + 空stdinで起動し、exit 0を確認する。
7. bundle helperを不正protocol versionで起動し、exit 64を確認する。
8. build process用環境変数をMain build直後に消去する。

## 期待出力

```text
builds/
  BAI Video Production/
    BAI Video Production.exe
    BAI Video Production Key Helper.exe
    _internal/
```

どちらか一方のEXEだけを移動しない。helperは利用者が直接操作する画面を
持たず、Main Productから固定argv・anonymous pipesでのみ使う。

## 実施結果

- Python: `3.12.4`
- PyInstaller: `6.22.0`
- helper one-file build: `PASS`
- canonical Main one-dir build: `PASS`
- generated identity module inclusion: `PASS`
- staging/bundle/generated identity three-way verification: `PASS`
- protocol v1 empty-input native smoke: `PASS / exit 0`
- invalid-version refusal: `PASS / exit 64`
- install: `NOT_EXECUTED`
- download: `NOT_EXECUTED`
- settings change: `NOT_EXECUTED`
- Main UI launch: `NOT_EXECUTED`

Observed non-secret identities:

- Main EXE: size `16,324,300`,
  `sha256:9cc7cae6d18b8cdab5e1e972231d4c84d820968fd1d066b4a5d800f457d23e89`
- bundled helper: size `17,229,081`,
  `sha256:296967c0a674eacddc7cc95a06de163d233d2f2a86d95d48281076218d068caa`
- staging helper: bundled helperとsize/SHA-256が一致

## Rollback

Rollbackは`NOT_REQUIRED / NOT_EXECUTED`。生成物はGit管理外の
`builds/BAI Video Production`、`builds/work/task036_shell`、
`builds/work/task059-helper-dist`、`builds/work/task059-helper-work`
だけである。rollbackが必要な場合は全EXE停止後にこの4 targetだけを
削除し、source、Evidence、Owner key、Project dataへ触れない。

秘密値、鍵本文、passphrase、seedは作成、読取、表示、記録、送信していない。
