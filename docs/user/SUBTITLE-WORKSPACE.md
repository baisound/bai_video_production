# 字幕Workspaceの使い方

Repository直下で次を実行します。

```powershell
python -m pip install -e .
python -c "import ai_video_production; print(ai_video_production.__version__)"
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-subtitle-workspace.ps1
```

版番号が`0.16.0`ならブラウザで字幕Workspaceが開きます。作業内容は既定でRepository直下の`subtitle-workspace.json`に保存されます。

1. 既存SRTは「SRTを読込」にローカルファイルの絶対パスを入れます。
2. 開始・終了・本文を直して「保存」を押します。
3. 空き時間がある場所には「前に挿入」「後に挿入」で1行追加できます。空きがなければ、先に前後行の時刻を調整します。
4. 「削除」で行を除き、「＋末尾に追加」で最後へ追加できます。
5. 出力先を指定し「SRTを書出」で編集版を保存します。

「AI誤字・脱字チェックを許可」は既定OFFです。0.16.0ではONにしてもAI通信や課金は始まらず、設定を保存するだけです。
