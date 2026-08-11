# Cut Candidates — 無音・フィラー・言い直し候補

BAI Video Production 0.18.0 candidate では、編集前の「切れそうな場所」を候補として抽出できます。

この機能は **自動で動画を切りません**。候補を作るだけです。

## 対応する候補

- 長い無音
- フィラーだけの短い発話（例: えっと）
- 近接した完全一致の言い直し

通常の発話はKeep Blockとして保護され、無音候補と重ならないようにします。

## 実行例

```powershell
ai-video-cut-candidates .\analysis.wav `
  --output-dir .\cut-analysis `
  --source-asset-id ASSET-... `
  --transcript .\transcript.json
```

Transcriptは任意です。指定しない場合は無音候補だけを生成します。

## 出力

- `cut-candidates.json`
- `cut-candidate-report.json`

どちらにもTranscript本文は保存しません。

`cut-candidates.json` の候補は常に:

```text
action = REVIEW_ONLY
auto_apply_authorized = false
```

です。

最終的なCut PlanはTASK-007、DaVinci Resolveへの実際の反映はTASK-010の責務です。
