# Qwen3-TTS 学習依存 — Windowsネイティブ環境の検証手順

[WSL2実測手順](QWEN3-TTS-WSL2-VERIFIED-ENVIRONMENT.md) |
[共通の学習依存ガイド](QWEN3-TTS-TRAINING-DEPENDENCIES.md) |
[0.6B Base本体](QWEN3-TTS-06B-BASE-SETUP.md)

このページはWindowsネイティブだけでQwen3-TTSの学習依存を構築できるか、対象PCで
実際に試して成功した手順です。PyTorch、Qwen-TTS、TensorBoard、SoX、CUDA compiler smokeに
加え、FlashAttentionの公式source distributionからWindows wheelをbuildし、RTX 4070 SUPERで
bf16 forward/backwardまで確認しました。

公式配布のWindows wheelを取得したのではありません。このPC上で公式sourceをcompileして
作ったローカルwheelです。別PCや別ABIへそのwheelを流用せず、同じ手順で再build・再検証します。

## 1. 実測した構成

| 項目 | 実測値 |
| --- | --- |
| OS | Windows x64 / build 26200 |
| GPU | NVIDIA GeForce RTX 4070 SUPER |
| Python | 3.12.4 |
| Visual Studio Build Tools | 2026 18.9 / MSVC 19.51.36256 |
| PyTorch / Torchaudio | 2.11.0+cu130 / 2.11.0+cu130 |
| Qwen-TTS | 0.1.1 |
| TensorBoard | 2.21.0 |
| NVIDIA pip CUDA compiler | 13.3.73 |
| NVIDIA pip CCCL | 13.3.3.4.1 |
| Ninja / psutil | 1.13.0 / 7.2.2 |
| SoX | 14.4.2 official Windows portable ZIP |
| FlashAttention | 2.8.3.post1 local Windows build |

CUDA runtimeはPyTorch wheelの13.0、source compilerはNVIDIA pip packageの13.3です。
この違いを同一versionとして表示しません。

## 2. 専用rootとvenvを作る

PowerShellで、`E:\BAI_AI`配下を用途ごとに分けます。この例は今回の実測配置に合わせています。
環境本体を`envs`、取得物とbuild Evidenceを`recovery`へ置き、録音WAVやRepositoryとは混ぜません。

```powershell
$BaiAiRoot = 'E:\BAI_AI'
$EnvRoot = Join-Path $BaiAiRoot 'envs\qwen3-tts-windows-native'
$RecoveryRoot = Join-Path $BaiAiRoot 'recovery\qwen3-tts-windows-native'
$ArtifactRoot = Join-Path $RecoveryRoot 'artifacts'
$SourceRoot = Join-Path $RecoveryRoot 'sources'
$WheelRoot = Join-Path $RecoveryRoot 'wheels'
$ReceiptRoot = Join-Path $RecoveryRoot 'receipts'

if (-not (Test-Path -LiteralPath 'E:\')) {
    throw 'E: driveが見つかりません。別driveへ読み替える場合は全変数を同じrootへ揃えてください。'
}
if (Test-Path -LiteralPath $EnvRoot) {
    throw "既存venvを上書きしません。内容を確認してください: $EnvRoot"
}
New-Item -ItemType Directory -Force `
  -Path $ArtifactRoot, $SourceRoot, $WheelRoot, $ReceiptRoot | Out-Null
py -3.12 -m venv $EnvRoot
$Python = Join-Path $EnvRoot 'Scripts\python.exe'
& $Python -m pip install --upgrade pip setuptools wheel
```

空き容量も記録します。

```powershell
Get-Volume -DriveLetter E | Select-Object DriveLetter, Size, SizeRemaining
```

## 3. PyTorch、Qwen-TTS、TensorBoardを入れる

```powershell
& $Python -m pip install torch==2.11.0 torchaudio==2.11.0 `
  --index-url https://download.pytorch.org/whl/cu130 `
  --report (Join-Path $ReceiptRoot 'torch-cu130-install-report.json')
& $Python -m pip install qwen-tts==0.1.1 tensorboard==2.21.0 `
  packaging psutil==7.2.2 ninja==1.13.0 `
  --report (Join-Path $ReceiptRoot 'qwen-build-dependencies-install-report.json')
& $Python -m pip check
```

確認します。

```powershell
& $Python -c "import torch; from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel; from torch.utils.tensorboard import SummaryWriter; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0)); print('QWEN_IMPORT_PASS'); print('TENSORBOARD_IMPORT_PASS')"
```

class importだけを行い、Modelはloadしません。

## 4. CUDA compilerを隔離venvへ入れる

対象PCでは既存のsystem CUDAやPATHを変更せず、NVIDIA公式pip packageを使いました。

```powershell
& $Python -m pip install `
  nvidia-cuda-nvcc==13.3.73 `
  nvidia-nvvm==13.3.73 `
  nvidia-cuda-runtime==13.3.29 `
  nvidia-cuda-crt==13.3.73 `
  nvidia-cuda-cccl==13.3.3.4.1 `
  --report (Join-Path $ReceiptRoot 'nvidia-cuda-toolchain-install-report.json')

$CudaHome = Join-Path $EnvRoot 'Lib\site-packages\nvidia\cu13'
$Nvcc = Join-Path $CudaHome 'bin\nvcc.exe'
& $Nvcc --version
```

この構成では`nv/target`を含むCCCL packageも必要です。CCCLなしではCUDA 13.3の
`cuda_fp16.h`をhost compilerが処理できません。

## 5. SoXを隔離配置する

Qwen-TTSはimport時にSoXを探します。公式SourceForgeの14.4.2 Windows ZIPを取得し、SHAを
確認して`$EnvRoot`配下へ展開します。system PATHは変更しません。

```powershell
$SoxZip = Join-Path $ArtifactRoot 'sox-14.4.2-win32.zip'
$SoxRoot = Join-Path $EnvRoot 'tools\sox-14.4.2'
curl.exe -fL --proto '=https' --tlsv1.2 -o $SoxZip `
  'https://sourceforge.net/projects/sox/files/sox/14.4.2/sox-14.4.2-win32.zip/download'
(Get-FileHash -Algorithm SHA256 -LiteralPath $SoxZip).Hash
Expand-Archive -LiteralPath $SoxZip -DestinationPath $SoxRoot
$SoxBin = Join-Path $SoxRoot 'sox-14.4.2'
$env:PATH = "$SoxBin;$env:PATH"
& (Join-Path $SoxBin 'sox.exe') --version
```

実測したZIPは2,651,143 bytes、SHA-256は
`8072cc147cf1a3b3713b8b97d6844bb9389e211ab9e1101e432193fad6ae6662`です。
`sox.exe`は213,624 bytes、SHA-256は
`e0e3cdc4bcdfbb5b91ac8f53b024964d092f89ba90130ba74b223a1df11b5439`でした。
再取得時は配布元の状態を再監査し、過去SHAを無条件で強制しません。

## 6. CUDA compiler smokeを行う

Visual Studio Developer Command Promptのx64環境を使い、1個の値を書き込む小さなCUDA
programを`sm_89`向けにcompile/runします。成功条件はexit code 0と結果42です。

```cpp
#include <cuda_runtime.h>
#include <cstdio>

__global__ void write_value(int* value) { *value = 42; }

int main() {
    int* device_value = nullptr;
    int host_value = 0;
    if (cudaMalloc(&device_value, sizeof(int)) != cudaSuccess) return 2;
    write_value<<<1, 1>>>(device_value);
    if (cudaDeviceSynchronize() != cudaSuccess) return 3;
    if (cudaMemcpy(&host_value, device_value, sizeof(int), cudaMemcpyDeviceToHost) != cudaSuccess) return 4;
    cudaFree(device_value);
    std::printf("cuda_smoke_result=%d\n", host_value);
    return host_value == 42 ? 0 : 5;
}
```

Developer Command Prompt内の要点は次です。Visual Studioの場所は`vswhere.exe`で確認し、
見つからないpathを推測しません。

```bat
call "<VS BuildTools>\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64
set "CUDA_HOME=<venv>\Lib\site-packages\nvidia\cu13"
set "PATH=%CUDA_HOME%\bin;%PATH%"
"%CUDA_HOME%\bin\nvcc.exe" -arch=sm_89 cuda-smoke.cu -o cuda-smoke.exe
cuda-smoke.exe
```

対象PCでは`cuda_smoke_result=42`が得られました。

## 7. Windows FlashAttentionをbuildする

FlashAttention v2.8.3の公式GitHub Release assetはLinux wheelのみで、Windows wheelは
確認できませんでした。第三者wheelを入れず、公式PyPI source distributionをcompileします。

- package: `flash-attn==2.8.3.post1`;
- source archive SHA-256:
  `55d5103ed846da8b56e0797acf4bde07dee4b1c7e8907fcfc6699c203030c348`;
- build parallelism: 少ないRAMでは`MAX_JOBS=1`から開始。実測PCはRAM監視後に8、
  `NVCC_THREADS=1`;
- target GPU arch: `TORCH_CUDA_ARCH_LIST=8.9`;
- MSVC: standard preprocessor `/Zc:preprocessor`。

```powershell
$env:CUDA_HOME = Join-Path $EnvRoot 'Lib\site-packages\nvidia\cu13'
$env:PATH = "$env:CUDA_HOME\bin;$env:PATH"
$env:MAX_JOBS = '8'
$env:NVCC_THREADS = '1'
$env:TORCH_CUDA_ARCH_LIST = '8.9'
$env:FLASH_ATTENTION_FORCE_BUILD = 'TRUE'
$env:CL = '/Zc:preprocessor'

& $Python -m pip download flash-attn==2.8.3.post1 --no-deps `
  --no-binary=:all: --no-build-isolation --dest $ArtifactRoot
```

SHAを検証し、安全な新規directoryへ展開してから、Developer Command Promptで
`setup.py bdist_wheel`を実行します。対象PCは約68.6 GB RAMで、8 CUDA compile jobs稼働中の
空きRAMを監視しながらbuildしました。RAMが少ないPCでは`MAX_JOBS=1`または2から始めます。

PyTorch 2.11はWindows compiler出力を`oem` codecで固定decodeするため、このWindows buildでは
VS 2026出力のdecodeに失敗しました。実測probeではbuild process内だけ
`torch.utils.cpp_extension.SUBPROCESS_DECODE_ARGS`を`("utf-8", "replace")`へ切り替えました。
PyTorch packageやflash-attn sourceのファイルは変更していません。

build結果:

- wheel: `flash_attn-2.8.3.post1-cp312-cp312-win_amd64.whl`;
- bytes: 57,016,766;
- SHA-256: `9190c93e0a62532ab42f390b0029e9862e277930caef77ef4de39ae4035b453a`;
- build log SHA-256:
  `ca5096d86a6c724f7d8439ed66dac8207693c3d94a19b2244f02f89d2b4a0a67`;
- source file change: 0;
- result: `PASS_LOCAL_WHEEL_CREATED`。

同じvenvへwheelを入れます。

```powershell
$Wheel = Join-Path $WheelRoot 'flash_attn-2.8.3.post1-cp312-cp312-win_amd64.whl'
& $Python -m pip install --no-deps $Wheel `
  --report (Join-Path $ReceiptRoot 'flash-attn-wheel-install-report.json')
& $Python -m pip check
```

ローカルwheelのSHAはこの実測buildのEvidenceです。公式署名済みWindows binaryのSHAではありません。

## 8. GPU forward/backwardを検査する

```powershell
& $Python -c "import torch; from flash_attn import flash_attn_func; s=(2,128,4,64); q=torch.randn(s,device='cuda',dtype=torch.bfloat16,requires_grad=True); k=torch.randn(s,device='cuda',dtype=torch.bfloat16,requires_grad=True); v=torch.randn(s,device='cuda',dtype=torch.bfloat16,requires_grad=True); o=flash_attn_func(q,k,v,dropout_p=0.0,causal=False); loss=o.float().square().mean(); loss.backward(); assert torch.isfinite(o).all() and all(torch.isfinite(x.grad).all() for x in (q,k,v)); print('PASS_FLASH_ATTN_FORWARD_BACKWARD',tuple(o.shape),float(loss.detach()))"
```

実測結果はshape `(2, 128, 4, 64)`、loss `0.020701097324490547`で、outputと
q/k/v gradientがすべてfiniteでした。runtime smoke receipt SHA-256は
`1f0c7600708b9bbdda3a78a329468f9ec0a1585b1f575090e0be2737533649e7`です。

## 9. TensorBoard writerを確認する

```powershell
$TbRoot = Join-Path $RecoveryRoot 'tensorboard-smoke'
$env:BAI_TB_SMOKE = $TbRoot
& $Python -c "import os; from torch.utils.tensorboard import SummaryWriter; w=SummaryWriter(os.environ['BAI_TB_SMOKE']); w.add_scalar('setup/smoke',1.0,0); w.close(); print('PASS_TENSORBOARD_WRITER')"
Get-ChildItem -LiteralPath $TbRoot -Filter 'events.out.tfevents.*'
```

表示が必要なときだけloopbackへbindします。

```powershell
$TensorBoard = Join-Path $EnvRoot 'Scripts\tensorboard.exe'
& $TensorBoard --logdir $TbRoot --host 127.0.0.1
```

## 10. 判定を分ける

| Gate | Windows native state |
| --- | --- |
| PyTorch CUDA import/device | `PASS` |
| Qwen-TTS class import | `PASS_IMPORT_ONLY` |
| TensorBoard writer | `PASS` |
| CUDA 13.3 compiler `sm_89` smoke | `PASS` |
| FlashAttention local wheel build | `PASS_FROM_OFFICIAL_SOURCE` |
| FlashAttention GPU forward/backward | `PASS_BOUNDED_COMPATIBILITY` |
| Qwen3-TTS 0.6B representative training step | `BLOCKED_BY_RECIPE_INCOMPATIBILITY` |
| Training/Model/audio effect | `NOT_STARTED` |

Windows nativeでも依存環境は完成しました。ただし公式0.6B training recipeの既知不整合は
解消していません。環境構築PASSを学習やModel採用のPASSへ自動昇格しません。
