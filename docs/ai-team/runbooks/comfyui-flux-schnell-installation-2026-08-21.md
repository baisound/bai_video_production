# ComfyUI + FLUX.1 Schnell local image runtime installation

Date: 2026-08-21
Owner state: `OWNER_SLEEPING=YES / SLEEP_WINDOW_ACTIVE=YES`
Purpose: restore the free/local image Provider required by the BAI VIDEO
PRODUCTION end-to-end workflow. This procedure does not install a cloud or paid
Provider and does not authorize Product generation by itself.

## Authorized boundary

- Use the official ComfyUI NVIDIA portable release only.
- Use the Apache-2.0 FLUX.1 Schnell FP8 checkpoint published by Comfy-Org only.
- Do not install custom nodes, API partner nodes or credentials.
- Do not enable a public/listen-all endpoint, automatic Provider execution,
  paid APIs, model pull from the Product, Human ACCEPT, Asset LOCK, Resolve,
  publication, deployment or release.
- Bind the runtime only to `127.0.0.1:8188`.
- Keep runtime, model, input, output and Product source roots separate.

## Verified sources and identities

1. ComfyUI portable
   - Release: `v0.33.1`
   - Asset: `ComfyUI_windows_portable_nvidia.7z`
   - Size: `2,133,107,036` bytes
   - SHA-256: `4a221588979b96b8244e0e50b2edca03af732acae1deba69d60aa3b4d60b9dba`
   - URL: `https://github.com/Comfy-Org/ComfyUI/releases/download/v0.33.1/ComfyUI_windows_portable_nvidia.7z`
2. FLUX.1 Schnell FP8
   - Asset: `flux1-schnell-fp8.safetensors`
   - License: Apache-2.0
   - Reported size: `17.2 GB`
   - SHA-256: `ead426278b49030e9da5df862994f25ce94ab2ee4df38b556ddddb3db093bf72`
   - URL: `https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors`

Primary references:

- `https://docs.comfy.org/installation/system_requirements`
- `https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.33.1`
- `https://docs.comfy.org/tutorials/flux/flux-1-text-to-image`
- `https://huggingface.co/Comfy-Org/flux1-schnell/blob/main/flux1-schnell-fp8.safetensors`

## Fixed local layout

- Download archive:
  `E:\BAI_AI\downloads\ComfyUI_windows_portable_nvidia-v0.33.1.7z`
- Runtime root:
  `E:\BAI_AI\runtimes\ComfyUI-v0.33.1\ComfyUI_windows_portable`
- Checkpoint:
  `E:\BAI_AI\runtimes\ComfyUI-v0.33.1\ComfyUI_windows_portable\ComfyUI\models\checkpoints\flux1-schnell-fp8.safetensors`
- Product-owned input:
  `E:\BAI_AI\datasets\task036-comfy-input`
- Product-owned output:
  `E:\BAI_AI\outputs\task036-comfy-output`
- Product-owned temp:
  `E:\BAI_AI\cache\task036-comfy-temp`

## Procedure

1. Confirm the exact release asset metadata and at least 30 GB free on E:.
2. Download the release archive to the fixed download path. Resume is allowed;
   do not execute a partial file.
3. Verify archive byte size and SHA-256 before extraction.
4. Create the versioned runtime parent and extract the archive there. Do not
   overwrite or delete another runtime.
5. Verify the embedded Python and `ComfyUI/main.py` are regular files.
6. Download the FLUX checkpoint directly to a `.partial` sibling under the
   checkpoint directory. Resume is allowed only against that exact URL.
7. Verify the model SHA-256, then rename `.partial` to the final filename.
8. Create the three Product-owned input/output/temp directories as regular,
   non-symlink directories.
9. Start ComfyUI with the embedded Python and fixed arguments:

   ```text
   python_embeded\python.exe -s ComfyUI\main.py
     --listen 127.0.0.1 --port 8188 --disable-auto-launch
     --input-directory E:\BAI_AI\datasets\task036-comfy-input
     --output-directory E:\BAI_AI\outputs\task036-comfy-output
     --temp-directory E:\BAI_AI\cache\task036-comfy-temp
   ```

10. Read only `/system_stats` and `/object_info`. Confirm exact loopback,
    NVIDIA runtime, checkpoint inventory and required core node classes. Do not
    queue a workflow during installation verification.
11. Record the observed ComfyUI/frontend/Python/PyTorch/device versions and
    model hash. Product source may bind the runtime only after these checks.

## Failure and rollback

- Network interruption: keep only the named `.partial` download and resume the
  same exact URL; never execute or load it.
- Hash mismatch: quarantine the mismatched file under
  `E:\BAI_AI\diagnostics` and stop. Do not retry from another source.
- Extraction/start failure: preserve logs, stop the process and leave the
  versioned runtime isolated. Do not modify system Python, CUDA or drivers.
- Rollback is performed by stopping the exact ComfyUI process and renaming the
  versioned runtime directory to an inactive sibling. Deletion is not part of
  this procedure.
- No Product Project, canonical Asset, Candidate, Timeline or Export state is
  created by the installation procedure.

## Verification record template

- Archive SHA-256:
  `4a221588979b96b8244e0e50b2edca03af732acae1deba69d60aa3b4d60b9dba`
- Model byte size: `17,236,328,572`
- Model SHA-256:
  `ead426278b49030e9da5df862994f25ce94ab2ee4df38b556ddddb3db093bf72`
- ComfyUI version: `0.33.1`
- Python/PyTorch/CUDA: `3.13.14 / 2.13.0+cu130 / CUDA 13.0 runtime`
- GPU and free VRAM:
  `NVIDIA GeForce RTX 4070 SUPER / 11,606,687,744 bytes`
- Required node classes:
  `CheckpointLoaderSimple, CLIPTextEncode, EmptyLatentImage, KSampler,
  VAEDecode, SaveImage — PASS`
- Checkpoint inventory: `flux1-schnell-fp8.safetensors — PASS`
- Endpoint: `http://127.0.0.1:8188 — PASS`
- Provider dispatch count: `0`
- Paid/cloud call count: `0`
