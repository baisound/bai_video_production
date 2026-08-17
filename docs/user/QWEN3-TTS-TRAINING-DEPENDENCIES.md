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
3. このProjectのWindows実測環境には、現時点で`flash-attn`と`tensorboard`がありません。
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

```bash
python3.12 -m venv .venv-qwen3-tts-probe
source .venv-qwen3-tts-probe/bin/activate
python -m pip install --upgrade pip

# PyTorchは https://pytorch.org/get-started/locally/ で
# Linux / Pip / Python / 使用するCUDAを選んだexact commandを使う。
python -m pip install packaging psutil ninja
ninja --version

MAX_JOBS=4 python -m pip install flash-attn --no-build-isolation
python -c "import flash_attn, torch; print('flash_attn=', flash_attn.__version__); print('torch=', torch.__version__); print('cuda=', torch.version.cuda)"
```

`MAX_JOBS=4`はbuild時のRAM使用量を抑えるための上限例です。公式READMEも、RAMが
96 GB未満でCPU coreが多い環境ではjob数を制限するよう案内しています。

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

## 公式資料

- [Qwen3-TTS environment and fine-tuning](https://github.com/QwenLM/Qwen3-TTS)
- [Qwen3-TTS fine-tuning guide](https://github.com/QwenLM/Qwen3-TTS/blob/main/finetuning/README.md)
- [FlashAttention official installation requirements](https://github.com/Dao-AILab/flash-attention#installation-and-features)
- [PyTorch TensorBoard documentation](https://docs.pytorch.org/docs/stable/tensorboard)
- [PyTorch installation selector](https://pytorch.org/get-started/locally/)

## English quick guide

Install TensorBoard in the same isolated Python environment with
`python -m pip install tensorboard`, then verify `SummaryWriter` imports.
FlashAttention officially requires a CUDA/ROCm toolkit, PyTorch 2.2 or newer,
build helpers and Linux; its official README says Windows compilation still
needs more testing. Prefer a new Linux/WSL2 probe environment and bind the exact
Python, PyTorch, CUDA, compiler, FlashAttention source/wheel and hashes. Do not
install an unverified third-party Windows wheel and do not silently replace
`flash_attention_2` with SDPA in the official training recipe.

Dependency imports do not prove Qwen3-TTS 0.6B training feasibility. The
official current 0.6B recipe incompatibility, a synthetic representative step,
12 GB resource measurements, checkpoint recovery and the separate Owner
Training Gate must all be resolved first.
