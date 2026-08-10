# TASK-006 — v0.16.2 Native Windows UI Verification

- Candidate: `0.16.2`
- Scope: Subtitle Workspace Open / Save As dialogs
- Gate: required before creating or publishing tag `v0.16.2`

## 1. Preflight

Repository直下のPowerShellで実行します。

```powershell
python -m pip install -e .
python -c "import ai_video_production; print(ai_video_production.__version__)"
python -m pytest -q tests/test_native_file_dialog.py tests/test_task006_subtitle_workspace.py tests/test_release_metadata_check.py
python -m compileall -q src tests
```

期待値:

- Version: `0.16.2`
- targeted tests: PASS
- compileall: no error

## 2. Safe sample SRT

実案件SRTを使わない場合は、Repository直下へ短い確認用SRTを作成します。

```powershell
@"
1
00:00:00,000 --> 00:00:02,000
字幕UI確認

2
00:00:02,100 --> 00:00:04,000
保存先確認
"@ | Set-Content -Encoding UTF8 .\task006-ui-sample.srt
```

## 3. Launch

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-subtitle-workspace.ps1
```

ブラウザに `BAI Video Production v0.16.2` が表示されることを確認します。

## 4. Open dialog acceptance

1. `ファイルを選択…`を押す。
2. Windowsのファイル選択ダイアログが前面に開くことを確認する。
3. `task006-ui-sample.srt`を選択する。
4. 選択したパスが読み込み欄へ入ることを確認する。
5. `SRTを読込`を押す。
6. 2 Cueが画面へ表示されることを確認する。

PASS条件: パスを手入力せずSRTを選択・読込できる。

## 5. Save As acceptance

1. 1 Cueの本文を `字幕UI確認済み` に変更して`保存`する。
2. `保存先を選択…`を押す。
3. WindowsのSave Asダイアログが前面に開くことを確認する。
4. 任意のフォルダーを選び、ファイル名を `task006-ui-edited.srt` とする。
5. `SRTを書出`を押す。
6. Explorerで選択先にファイルが存在することを確認する。
7. ファイルをメモ帳等で開き、`字幕UI確認済み`が入っていることを確認する。

PASS条件: 保存フォルダーとファイル名をダイアログで選択し、編集済みSRTを書き出せる。

## 6. Cancel / replacement safety

- `ファイルを選択…`を押してキャンセルしても現在の字幕が変化しない。
- 字幕が表示済みの状態で別SRTを指定して`SRTを読込`すると、置換確認が表示される。
- 置換確認でキャンセルすると現在の字幕が維持される。

## 7. Evidence to return

次の結果だけで十分です。

```text
Version: 0.16.2
Targeted tests: PASS / FAIL
Open dialog: PASS / FAIL
SRT import: PASS / FAIL
Save As dialog: PASS / FAIL
SRT export: PASS / FAIL
Cancel safety: PASS / FAIL
Replacement confirmation: PASS / FAIL
```

FAILがある場合は、エラー文または画面スクリーンショットも添付します。
