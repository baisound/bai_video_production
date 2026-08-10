# 字幕Workspaceの使い方

Repository直下で次を実行します。

```powershell
python -m pip install -e .
python -c "import ai_video_production; print(ai_video_production.__version__)"
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-subtitle-workspace.ps1
```

版番号が`0.16.2`ならブラウザで字幕Workspaceが開きます。作業内容は既定でRepository直下の`subtitle-workspace.json`に保存されます。

1. 既存SRTは「ファイルを選択…」からWindowsのファイル選択ダイアログを開き、対象SRTを選びます。パスの手入力は通常不要です。
2. 「SRTを読込」を押します。すでに字幕があるWorkspaceを置き換える場合は確認が表示されます。
3. 開始・終了・本文を直して「保存」を押します。
4. 空き時間がある場所には「前に挿入」「後に挿入」で1行追加できます。空きがなければ、先に前後行の時刻を調整します。
5. 「削除」で行を除き、「＋末尾に追加」で最後へ追加できます。
6. 「保存先を選択…」からWindowsのSave Asダイアログを開き、保存フォルダーとファイル名を選びます。
7. 「SRTを書出」で編集版を保存します。

読み込み／書き出しのパス欄へ直接入力する方法も上級者向けに残しています。ボタン押下時にパスが空なら、対応するWindowsダイアログが自動的に開きます。

「AI誤字・脱字チェックを許可」は既定OFFです。0.16.2でもONにしただけではAI通信や課金は始まらず、設定を保存するだけです。
