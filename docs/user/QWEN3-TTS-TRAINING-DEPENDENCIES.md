# Qwen3-TTS 学習依存セットアップ — flash-attn / TensorBoard

[English quick guide](#english-quick-guide) | [0.6B Base本体の準備](QWEN3-TTS-06B-BASE-SETUP.md)

このページはQwen3-TTSの公式fine-tuning scriptが要求する`flash-attn`と
TensorBoardを、推測で成功扱いにせず準備するための手順です。dependencyのinstall成功は、
Qwen3-TTS 0.6Bの学習成功、12 GB VRAM適合、Model承認を意味しません。

## 現在の重要な制約

1. FlashAttention公式READMEはLinuxを要件としています。Windowsは「動く可能性があるが、
   compilationはさらにtestが必要」という扱いで、公式の安定Windows wheel手順ではありません。
2. Qwen3-TTS公式fine-tuning scriptは`attn_implementation="flash_attention_2"`と
   `Accelerator(..., log_with="tensorboard")`を指定します。
3. このProjectのWindows隔離環境にはTensorBoard 2.21.0を導入し、`SummaryWriter`の
   event file生成まで確認済みです。Windows native向けの公式`flash-attn` wheelは確認できず、
   Windows環境へは導入していません。
4. さらに、公式Qwen3-TTS `main@022e286b98fbec7e1e916cb940cdf532cd9f488e`の
   0.6B recipeには2048/1024 embedding不整合があります。open PR #336を勝手に
   取り込んで公式PASSとはしません。

したがって、Windowsで`pip install flash-attn`を繰り返すことや、第三者が配布するwheelを
出所・hash・互換性未確認で入れることは、このガイドの手順ではありません。

## 1. 使用する環境を確認する

[0.6B Baseセットアップ](QWEN3-TTS-06B-BASE-SETUP.md)で作った隔離環境を使います。

```powershell
$QwenRoot = Join-Path $env:LOCALAPPDATA 'BAI\Qwen3TTS-0.6B'
$EnvRoot = Join-Path $QwenRoot 'env'
$Python = Join-Path $EnvRoot 'Scripts\python.exe'

& $Python --version
& $Python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA_NOT_AVAILABLE')"
nvidia-smi
```

Python、PyTorch、CUDA、GPUが想定と違う場合はinstallを開始しません。結果をEvidenceへ
記録し、対応する組合せを選び直します。

## 2. TensorBoardを入れる

TensorBoardはPyTorch公式documentで案内されている通常のPython packageです。

```powershell
& $Python -m pip install tensorboard
& $Python -c "import tensorboard; from torch.utils.tensorboard import SummaryWriter; print('tensorboard=', tensorboard.__version__); print('SummaryWriter=PASS')"
```

学習logを表示するときは、対象runのtask-owned log directoryを明示します。

```powershell
$TensorBoard = Join-Path $EnvRoot 'Scripts\tensorboard.exe'
& $TensorBoard --logdir 'C:\path\to\one-authorized-run\logs' --host 127.0.0.1
```

- `--host 127.0.0.1`のままにし、外部networkへ公開しません。
- log directoryに録音WAV、transcript本文、credentialを置きません。
- TensorBoard画面が開いたことを学習成功やcheckpoint成功にしません。

## 3. flash-attnを準備する前の判定

公式FlashAttention 2の主なNVIDIA要件は、CUDA toolkit 12.0以上、PyTorch 2.2以上、
Ampere/Ada/Hopper GPU、fp16またはbf16、`packaging`、`psutil`、`ninja`、Linuxです。

```powershell
& $Python -c "import torch; print('torch=', torch.__version__); print('cuda=', torch.version.cuda); print('capability=', torch.cuda.get_device_capability(0) if torch.cuda.is_available() else None)"
```

RTX 40-seriesはAdaですが、GPU世代だけではWindows build、Python ABI、PyTorch/CUDA ABI、
backward passの成功を証明しません。

## 4. 推奨route: Linux / WSL2の新しい隔離環境

公式要件に近いのはLinuxです。Windows native環境へ無理に混ぜず、WSL2 Ubuntuなどの
新しいtask-owned環境でPython、PyTorch、CUDA visibilityを最初から確認します。

R4で実測PASSになった組合せは、Python 3.12、PyTorch/Torchaudio 2.8.0+cu128、
Qwen-TTS 0.1.1、FlashAttention 2.8.3公式Linux wheelです。別versionへ読み替えず、
必ず新しい隔離環境で作ります。

```bash
python3.12 -m venv .venv-qwen3-tts-cu128
source .venv-qwen3-tts-cu128/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install torch==2.8.0 torchaudio==2.8.0 \
  --index-url https://download.pytorch.org/whl/cu128
python -m pip install qwen-tts==0.1.1 tensorboard==2.21.0 \
  packaging psutil==7.2.2 ninja==1.13.0

curl -fL -o flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl \
  'https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl'
echo 'f25da18657a87fc83dc1bfb8b7751b82246e9db355510226b674fd437c34b5fb  flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl' \
  | sha256sum --check
python -m pip install --no-deps \
  ./flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl
python -m pip check
python -c "import flash_attn, torch; print('flash_attn=', flash_attn.__version__); print('torch=', torch.__version__); print('cuda=', torch.version.cuda)"
```

wheel名の`cp312`、`torch2.8`、`cu12`、`cxx11abiTRUE`は互換条件です。Python、PyTorch、
CUDA major、CXX11 ABIのいずれかが違う環境へ流用しません。公式wheelがない組合せでは
自動的に第三者wheelへ切り替えません。

source buildが本当に必要な場合だけ別Technical Probeに分け、まず`MAX_JOBS=1`と
`NVCC_THREADS=1`を使います。R4では31 GB RAM / 8 GB swap環境の4-job buildがOOMとなり、
CUDA 13.0 source buildもWSL VMを不安定化させました。公式互換wheelがある場合は
source buildを繰り返しません。

このrouteでも、次をexactに固定してから代表stepへ進みます。

- Linux/WSL distribution revision;
- NVIDIA driverとWSL GPU visibility;
- Python、PyTorch、CUDA toolkit、compiler、`ninja`、`flash-attn` version;
- package/wheel/source revision、bytes、SHA-256、license;
- Qwen3-TTS package、Model、official recipe revision;
- 出力、checkpoint、logのcontained rootと空き容量。

## 5. Windows native routeの扱い

FlashAttention公式READMEはWindows compilationを安定対応とはしていません。そのため、
このProjectでは以下を守ります。

- `pip install flash-attn --no-build-isolation`を成功するまでblind retryしない。
- 出所不明のprebuilt wheelを使わない。
- third-party wheelを使う提案は、source、release、Python ABI、PyTorch/CUDA ABI、GPU arch、
  bytes、SHA-256、license、security reviewを別Evidenceで固定する。
- `flash_attention_2`を黙って`sdpa`へ書き換え、公式recipeと同じだと表示しない。
- Visual Studio Build Tools、CUDA toolkit、PATH、Registryをこの手順から自動変更しない。

Windows native buildを将来採用する場合は、exact toolchainを別のTechnical Probeとして
構成し、import testだけでなくbf16 forward/backward、gradient、OOM-safe failure、再起動後
loadまで検証します。

## 6. TensorBoardとflash-attnの検査

対象環境で次を実行します。

```bash
python - <<'PY'
from importlib.metadata import version
import torch
from torch.utils.tensorboard import SummaryWriter
import flash_attn

print("tensorboard", version("tensorboard"))
print("flash-attn", version("flash-attn"))
print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("gpu", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NOT_AVAILABLE")
print("imports", "PASS")
PY
```

`imports=PASS`はpackage importの確認だけです。fine-tuning admissionには使えません。

R4実測ではRTX 4070 SUPER上でbf16、shape `(2, 128, 4, 64)`の
`flash_attn_func` forward/backwardを実行し、outputとq/k/v gradientがすべてfiniteでした。
TensorBoard 2.21.0の`SummaryWriter`もevent fileを生成しました。これはdependency互換性の
PASSであり、Qwen3-TTSの学習stepや12 GB適合のPASSではありません。

## 7. 0.6B学習を始めてよい条件

次がすべて揃うまでは開始しません。

- 0.6B次元不整合を解消した公式merged revisionまたはOwner承認済みexact recipe;
- synthetic/non-Owner Datasetとtokenizer出力;
- `flash-attn` forward/backwardとTensorBoard writerの互換性Evidence;
- 代表batch/sequenceの1 step成功;
- peak VRAM/RAM、optimizer、checkpoint、disk、温度、所要時間の実測;
- OOM時の安全停止、process/Job reconciliation、checkpoint roundtrip;
- FULL/PEFT/LoRAそれぞれ別のrecipeとAdmission;
- Dataset、Consent、rights、output destination、durable Job、Owner Training Gate。

Model loadだけ、短いforwardだけ、TensorBoard表示だけを12 GB training PASSへ変換しません。

## 8. よくある失敗

- `No module named tensorboard`: 同じ隔離環境の`$Python`でinstallしたか確認します。
- `flash_attn is not installed`: Windowsでは想定し得る状態です。推測wheelを入れず、Linux/WSL
  routeまたはexact toolchain Probeへ切り分けます。
- `CUDA_HOME` / `nvcc`がない: CUDA runtimeとCUDA toolkitは別です。PATHを書き換える前に
  exact toolchain計画を作ります。
- `ninja`が失敗する: `ninja --version`の終了codeを確認します。
- 2048と1024のshape mismatch: 現行公式main 0.6B recipeの既知境界です。open fixを
  official merged PASSとして扱いません。
- importは通るがstepでOOM: import/load PASSをresource feasibilityへ流用してはいけません。
- WSLがsource build中に停止する: 同じ構成をblind retryせず、公式releaseにexact ABIのwheelが
  あるか確認します。公式wheelがなければ`FAILED_KNOWN / PROBE_REQUIRED`として止めます。

## 公式資料

- [Qwen3-TTS environment and fine-tuning](https://github.com/QwenLM/Qwen3-TTS)
- [Qwen3-TTS fine-tuning guide](https://github.com/QwenLM/Qwen3-TTS/blob/main/finetuning/README.md)
- [FlashAttention official installation requirements](https://github.com/Dao-AILab/flash-attention#installation-and-features)
- [PyTorch TensorBoard documentation](https://docs.pytorch.org/docs/stable/tensorboard)
- [PyTorch installation selector](https://pytorch.org/get-started/locally/)

## English quick guide

Install TensorBoard in the same isolated Python environment and verify that
`SummaryWriter` creates an event file. The tested Linux/WSL2 matrix is Python
3.12, PyTorch/Torchaudio 2.8.0+cu128, Qwen-TTS 0.1.1 and the official
FlashAttention 2.8.3 `cu12torch2.8/cp312/cxx11abiTRUE` wheel whose SHA-256 is
shown above. Do not reuse that wheel with a different ABI, install an
unverified third-party Windows wheel, or silently replace
`flash_attention_2` with SDPA in the official training recipe.

Dependency imports do not prove Qwen3-TTS 0.6B training feasibility. The
official current 0.6B recipe incompatibility, a synthetic representative step,
12 GB resource measurements, checkpoint recovery and the separate Owner
Training Gate must all be resolved first.
