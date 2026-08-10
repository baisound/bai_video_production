# TASK-006 — v0.16.3 Native Windows UI Verification

- Candidate: `0.16.3`
- Scope: Subtitle Workspace interaction corrective
- Gate: required before creating or publishing any `v0.16.x` release tag

## 1. Preflight / full regression

Repository直下のPowerShellで実行します。

```powershell
python -m pip install -e .
python -c "import ai_video_production; print(ai_video_production.__version__)"
python -m pytest -q
python -m compileall -q src tests
git diff --check
```

期待値:

- Version: `0.16.3`
- **全件pytest: PASS**（限定テストだけではRelease Gateを満たさない）
- compileall: no error
- git diff --check: PASS

## 2. Safe sample SRT

```powershell
@"
1
00:00:00,000 --> 00:00:00,300
前字幕

2
00:00:00,600 --> 00:00:00,900
後字幕
"@ | Set-Content -Encoding UTF8 .\task006-ui-sample.srt
```

## 3. Launch

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-subtitle-workspace.ps1
```

ブラウザに `BAI Video Production v0.16.3` が表示されることを確認します。

## 4. Native dialog foreground acceptance

1. ブラウザをサブモニター等、実際に操作する画面へ置く。
2. 背景側にゲーム等のフルスクリーン／最大化ウィンドウがある実運用条件を再現する。
3. `ファイルを選択…`を押す。
4. Windowsのファイル選択ダイアログが操作中ウィンドウに関連付いて認識可能な前面位置へ表示されることを確認する。
5. `task006-ui-sample.srt`を選択して`SRTを読込`する。

## 5. Relative insertion timing acceptance

読み込んだ2 Cueの間で、1行目の`後に挿入`または2行目の`前に挿入`を押します。

期待値:

```text
前字幕終了: 00:00:00,300
挿入開始:   00:00:00,301
挿入終了:   00:00:00,599
後字幕開始: 00:00:00,600
```

隣接字幕の`300`や`600`を挿入字幕が再利用しないことを確認します。

## 6. Save As / export Evidence acceptance

1. `保存先を選択…`を押し、Save Asダイアログが認識可能な前面位置へ表示されることを確認する。
2. 任意のフォルダーと`task006-ui-edited.srt`を指定する。
3. `SRTを書出`を押す。
4. 画面上の緑色ステータス欄に次が表示されることを確認する。
   - `SRT書き出し成功`
   - 保存先フルパス
   - byte数
5. 実ファイルが存在し、編集内容が入っていることを確認する。

## 7. Server disconnect feedback

Workspace表示後にローカルサーバーを停止した状態で操作ボタンを押した場合、無反応に見えるのではなく、`ローカルサーバーに接続できません`という明示エラーがステータス欄へ表示されることを確認します。

## 8. Cancel / replacement safety

- Native dialogをキャンセルしても現在の字幕が変化しない。
- 別SRT取込時は置換確認が表示される。
- 置換確認をキャンセルすると現在の字幕が維持される。

## 9. Evidence to return

```text
Version: 0.16.3
Full regression: PASS / FAIL (xxx passed)
Open dialog foreground: PASS / FAIL
SRT import: PASS / FAIL
Relative insert 301-599: PASS / FAIL
Save As foreground: PASS / FAIL
Export success message + path + bytes: PASS / FAIL
Server disconnect message: PASS / FAIL
Cancel safety: PASS / FAIL
Replacement confirmation: PASS / FAIL
```
