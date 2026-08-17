# Qwen3-TTS 0.6B Base セットアップガイド

[English quick guide](#english-quick-guide) | [学習依存の準備](QWEN3-TTS-TRAINING-DEPENDENCIES.md)

このページは、Qwen3-TTS 0.6B BaseをほかのPython環境と混ぜずに準備し、
「packageが入った」「Modelがloadできた」「学習できる」を別々に確認するための
初心者向け手順です。ここまで完了しても、学習やナレーション生成が自動で始まる
ことはありません。

## 先に知っておくこと

- 対象Modelは `Qwen/Qwen3-TTS-12Hz-0.6B-Base` です。
- このProjectで実測したModel revisionは
  `5d83992436eae1d760afd27aff78a71d676296fc` です。
- Model本体とspeech tokenizerを合わせて約2.51 GBあります。download中の一時領域、
  Python環境、cacheを含め、少なくとも10 GBの空きを用意してください。
- NVIDIA GPUを使う場合も、Model load成功はfine-tuning成功を意味しません。
- 現在の公式fine-tuning `main`には0.6B固有の既知不整合があります。詳細は
  [R3 Technical Probe Evidence](../ai-team/tasks/TASK-046/p-vs-4b-qwen3-tts-06b-technical-probe-r3-evidence-2026-08-17.md)
  と[学習依存の準備](QWEN3-TTS-TRAINING-DEPENDENCIES.md)を確認してください。
- Owner音声、録音WAV、Dataset、API Keyをこの環境directoryへコピーしないでください。

## 1. 前提を確認する

Windows PowerShellを通常権限で開きます。管理者PowerShellは不要です。

```powershell
py -0p
nvidia-smi
```

確認するもの:

- Python 3.12が選べること。
- NVIDIA GPU、driver version、VRAMが表示されること。
- ほかの学習processがGPUを使用していないこと。不明なprocessがある場合は、
  新しい学習や再試行を開始しません。

`py`または`nvidia-smi`が見つからない場合は、そこで停止してください。別versionの
PythonやCUDAを推測でinstallすると、後で環境が再現できなくなります。

## 2. 保存先を決める

以下は例です。既存directoryを上書きしない新しいrootを使います。

```powershell
$QwenRoot = Join-Path $env:LOCALAPPDATA 'BAI\Qwen3TTS-0.6B'
$EnvRoot = Join-Path $QwenRoot 'env'
$ModelRoot = Join-Path $QwenRoot 'model\5d83992436eae1d760afd27aff78a71d676296fc'

if (Test-Path -LiteralPath $QwenRoot) {
    throw "保存先が既にあります。上書きせず、内容を確認してください: $QwenRoot"
}
New-Item -ItemType Directory -Path $QwenRoot | Out-Null
```

ProjectのRepository内、OBS Plugin directory、録音保存先にはModelを置かないで
ください。

## 3. Python隔離環境を作る

```powershell
py -3.12 -m venv $EnvRoot
$Python = Join-Path $EnvRoot 'Scripts\python.exe'
& $Python --version
& $Python -m pip install --upgrade pip
```

`$Python --version`が3.12でなければ、この環境を使用しません。

## 4. Qwen3-TTS packageを入れる

Projectで実測済みの再現用versionを固定します。

```powershell
& $Python -m pip install 'qwen-tts==0.1.1' 'huggingface_hub[cli]'
& $Python -m pip show qwen-tts torch torchaudio transformers accelerate
```

表示されたversionをEvidenceへ保存してください。将来versionを更新する場合は、既存環境を
上書きせず、新しい隔離環境で再Probeします。

## 5. Modelをexact revisionで取得する

`huggingface_hub`の公式CLIはfull commit hashを`--revision`へ指定できます。

```powershell
$Hf = Join-Path $EnvRoot 'Scripts\hf.exe'
& $Hf download Qwen/Qwen3-TTS-12Hz-0.6B-Base `
  --revision 5d83992436eae1d760afd27aff78a71d676296fc `
  --local-dir $ModelRoot
```

network errorや空き容量不足で中断した場合、完了を推測しません。同じ`--revision`と
`--local-dir`で再開すると、Hugging Faceのmetadataを使って不足分が確認されます。

## 6. 主要fileを検査する

```powershell
Get-Item -LiteralPath (Join-Path $ModelRoot 'config.json')
Get-Item -LiteralPath (Join-Path $ModelRoot 'model.safetensors')
Get-Item -LiteralPath (Join-Path $ModelRoot 'speech_tokenizer\model.safetensors')

Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $ModelRoot 'config.json')
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $ModelRoot 'model.safetensors')
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $ModelRoot 'speech_tokenizer\model.safetensors')
```

このProjectで実測した値:

| File | Bytes | SHA-256 |
|---|---:|---|
| `config.json` | 4,494 | `2e714c787c8edb98b05432685cddb634add2de4d4e645f653d68251ef72ba011` |
| `model.safetensors` | 1,829,344,272 | `180b3b10eb1c9f1b4db7806d5475bae3071c0243c299d49926bab1da3b6946f6` |
| `speech_tokenizer/model.safetensors` | 682,293,092 | `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258` |

1文字でも違う場合はloadや学習へ進まず、revisionとdownload結果を再確認します。

## 7. packageとCUDAを確認する

```powershell
& $Python -c "import torch, qwen_tts; print('torch=', torch.__version__); print('cuda=', torch.version.cuda); print('gpu=', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NOT_AVAILABLE')"
```

`NOT_AVAILABLE`の場合、GPU利用をPASSにしません。PyTorchの入れ直しは
[公式PyTorch selector](https://pytorch.org/get-started/locally/)でOS・package・CUDAを
選び、新しい隔離環境で行ってください。

## 8. 任意のload-only確認

この確認はModelをGPUへloadしますが、音声生成・推論・学習は行いません。十分な空き
VRAMを確認してから実行してください。

```powershell
& $Python -c "import torch; from qwen_tts import Qwen3TTSModel; m=Qwen3TTSModel.from_pretrained(r'$ModelRoot', device_map='cuda:0', dtype=torch.bfloat16, attn_implementation='sdpa'); print('PASS_MODEL_LOAD_ONLY', torch.cuda.max_memory_allocated()); del m; torch.cuda.empty_cache()"
```

SoXや`flash-attn`のwarningが出ても、無視して学習PASSにはしません。R3実測では
RTX 4070 SUPER上のload-only peak allocatedは2,175,147,520 bytesでした。

## 9. ここで完了する範囲

ここまでで確認できるのは次だけです。

- packageが隔離環境へ入った。
- exact revisionのModel fileが揃った。
- CUDAが見える（表示された場合）。
- Modelがloadできた（手順8を実行してPASSした場合）。

次は[flash-attn・TensorBoardの準備](QWEN3-TTS-TRAINING-DEPENDENCIES.md)、公式0.6B
recipe修正revision、synthetic representative step、12 GB資源Probe、checkpoint recoveryの
全てが必要です。OBS録音WAVやOwner音声を使うのは、その後の別Gateです。

## 困ったとき

- `py`がない: Python 3.12のinstall状態を確認します。
- `hf.exe`がない: 必ず同じ`$Python`で`huggingface_hub[cli]`を入れたか確認します。
- CUDAが見えない: `nvidia-smi`、driver、PyTorch buildの順で確認します。
- hashが違う: fileを利用せず、exact revisionと取得元を確認します。
- load時にVRAM不足: 再試行を繰り返さず、ほかのGPU processと実測Evidenceを確認します。
- 0.6B学習がshape mismatchで止まる: 現行公式mainの既知境界です。独自patchで成功扱いに
  せず、公式修正revisionの再監査を待ちます。

## 公式資料

- [Qwen3-TTS official repository](https://github.com/QwenLM/Qwen3-TTS)
- [Qwen3-TTS official fine-tuning guide](https://github.com/QwenLM/Qwen3-TTS/blob/main/finetuning/README.md)
- [Hugging Face `hf download` CLI](https://huggingface.co/docs/huggingface_hub/en/package_reference/cli)
- [PyTorch local installation selector](https://pytorch.org/get-started/locally/)

## English quick guide

Use a fresh Python 3.12 virtual environment, install the pinned
`qwen-tts==0.1.1` package, and download
`Qwen/Qwen3-TTS-12Hz-0.6B-Base` at full revision
`5d83992436eae1d760afd27aff78a71d676296fc`. Verify the three hashes in step 6
before loading the model. The optional command in step 8 is load-only: it does
not generate audio or prove training feasibility. Do not use Owner recordings
until the separate Dataset, Consent, training and acceptance gates are ready.

For training prerequisites and the current Windows limitation, continue to
[FlashAttention and TensorBoard setup](QWEN3-TTS-TRAINING-DEPENDENCIES.md).
