# Qwen3-TTS 学習依存 — WSL2実測セットアップ

[Windowsネイティブ検証](QWEN3-TTS-WINDOWS-NATIVE-ENVIRONMENT.md) |
[共通の学習依存ガイド](QWEN3-TTS-TRAINING-DEPENDENCIES.md) |
[0.6B Base本体](QWEN3-TTS-06B-BASE-SETUP.md)

この手順は、RTX 4070 SUPERを接続したWSL2 Ubuntu 24.04上で実際に成功した
Qwen3-TTS依存環境を再現するためのものです。FlashAttentionはimportだけでなく、bf16の
forward/backwardとgradientの有限性まで確認しています。

この成功は「依存packageが動く」という意味です。Qwen3-TTS 0.6Bの学習成功、12 GB VRAMへの
適合、Owner音声の使用、Model承認、Narration生成を許可するものではありません。

## 1. 実測済みの組合せ

| 項目 | 固定値 |
| --- | --- |
| WSL | WSL2 / Ubuntu 24.04 |
| Python | 3.12.3 |
| GPU | NVIDIA GeForce RTX 4070 SUPER / compute capability 8.9 |
| PyTorch / Torchaudio | 2.8.0+cu128 / 2.8.0+cu128 |
| Qwen-TTS | 0.1.1 |
| Transformers | 4.57.3 |
| Accelerate | 1.12.0 |
| FlashAttention | 2.8.3 official Linux wheel |
| TensorBoard | 2.21.0 |
| Ninja / psutil | 1.13.0 / 7.2.2 |
| SoX | 14.4.2 |

別のPython、PyTorch、CUDA、CXX11 ABIへwheelを流用しないでください。

## 2. Windows側でGPUが見えることを確認する

PowerShellで次を実行します。

```powershell
wsl.exe --status
wsl.exe -d Ubuntu -- nvidia-smi
```

`nvidia-smi`にGPU名とdriverが出ない場合は、package installへ進みません。WSL内へLinux用
NVIDIA driverを別途入れないでください。WSLはWindows側driverのGPU連携を使います。

## 3. WSL内の基本packageを準備する

Ubuntu terminalで実行します。

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv curl sox libsox-fmt-all
```

このwheel routeではCUDA toolkitのsource compilerは不要です。`nvidia-smi`とPyTorchの
CUDA runtimeが動くことを先に確認します。

## 4. 隔離venvを作る

projectや録音WAVの中ではなく、専用rootを作ります。

```bash
export BAI_QWEN_ENV="$HOME/.local/share/bai/qwen3-tts-flash-probe/venv-cu128-torch28"
python3.12 -m venv "$BAI_QWEN_ENV"
source "$BAI_QWEN_ENV/bin/activate"
python -m pip install --upgrade pip setuptools wheel
```

既存環境へ上書きしません。同じpathが既にある場合は、その内容と由来を確認してから別名の
新規venvを使います。

## 5. PyTorchとQwen-TTS依存を入れる

```bash
python -m pip install torch==2.8.0 torchaudio==2.8.0 \
  --index-url https://download.pytorch.org/whl/cu128
python -m pip install qwen-tts==0.1.1 tensorboard==2.21.0 \
  packaging psutil==7.2.2 ninja==1.13.0
python -m pip check
```

次のように確認します。

```bash
python - <<'PY'
import torch
from importlib.metadata import version
from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
print("gpu", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
print("qwen-tts", version("qwen-tts"))
print("qwen_import", "PASS")
PY
```

ここではclass importだけを行い、Modelはloadしません。

## 6. 公式FlashAttention wheelを取得する

このファイルはFlashAttention公式GitHub Release v2.8.3のassetです。

```bash
mkdir -p "$HOME/.cache/bai/flash-attn"
cd "$HOME/.cache/bai/flash-attn"
curl -fL -o flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl \
  'https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl'
echo 'f25da18657a87fc83dc1bfb8b7751b82246e9db355510226b674fd437c34b5fb  flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl' \
  | sha256sum --check
python -m pip install --no-deps \
  ./flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl
python -m pip check
```

実測assetは256,040,057 bytesです。SHA不一致ならinstallせず削除・再取得の判断を別に行います。
第三者配布wheelへ自動的に切り替えません。

## 7. GPU forward/backwardを検査する

```bash
python - <<'PY'
import torch
from flash_attn import flash_attn_func

assert torch.cuda.is_available()
device = "cuda:0"
shape = (2, 128, 4, 64)
q = torch.randn(shape, device=device, dtype=torch.bfloat16, requires_grad=True)
k = torch.randn(shape, device=device, dtype=torch.bfloat16, requires_grad=True)
v = torch.randn(shape, device=device, dtype=torch.bfloat16, requires_grad=True)
out = flash_attn_func(q, k, v, dropout_p=0.0, causal=False)
loss = out.float().square().mean()
loss.backward()
assert torch.isfinite(out).all()
assert all(torch.isfinite(x.grad).all() for x in (q, k, v))
print("PASS_FLASH_ATTN_FORWARD_BACKWARD", tuple(out.shape), float(loss))
PY
```

実測時はshape `(2, 128, 4, 64)`、loss `0.020701097324490547`で、outputと
q/k/v gradientがすべてfiniteでした。lossの完全一致は要求しませんが、shape、finite、
forward/backward成功を要求します。

## 8. TensorBoard writerを検査する

```bash
export BAI_TB_SMOKE="$HOME/.local/share/bai/qwen3-tts-flash-probe/tensorboard-smoke"
mkdir -p "$BAI_TB_SMOKE"
python - <<'PY'
import os
from torch.utils.tensorboard import SummaryWriter

root = os.environ["BAI_TB_SMOKE"]
writer = SummaryWriter(root)
writer.add_scalar("setup/smoke", 1.0, 0)
writer.flush()
writer.close()
print("PASS_TENSORBOARD_WRITER")
PY
find "$BAI_TB_SMOKE" -maxdepth 1 -type f -name 'events.out.tfevents.*' -print
```

必要になったときだけloopbackで表示します。

```bash
tensorboard --logdir "$BAI_TB_SMOKE" --host 127.0.0.1
```

録音WAV、transcript本文、credentialをlog directoryへ置かないでください。

## 9. 失敗したsource-build route

同じ端末でFlashAttentionをsource buildした実測では、4ジョブが31 GB RAMと8 GB swapを
使い切りOOMになりました。`MAX_JOBS=1`と`NVCC_THREADS=1`ではOOMは避けましたが、WSL VMが
CUDAコンパイル中に利用不能となりwheelを生成できませんでした。公式互換wheelがあるため、
このsource-build routeを成功するまで繰り返しません。

## 10. この後も残るGate

- 現行公式0.6B recipeの2048/1024 embedding不整合の解消;
- synthetic Datasetによる代表1 step;
- 12 GB環境のVRAM/RAM/disk/thermal/所要時間計測;
- checkpoint roundtripとOOM-safe recovery;
- Dataset、Consent、rights、Job、output destination、Owner Training Gate。

この手順ではModel load、学習、音声生成、録音、Dataset変更を行いません。
