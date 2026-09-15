"""Installer-managed Qwen3-TTS runtime validation and model acquisition."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence
import argparse
import hashlib
import importlib
import json
import os
import subprocess


MODEL_REPO_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
MODEL_REVISION = "5d83992436eae1d760afd27aff78a71d676296fc"
MODEL_FILES = {
    "config.json": (4494, "2e714c787c8edb98b05432685cddb634add2de4d4e645f653d68251ef72ba011"),
    "model.safetensors": (1_829_344_272, "180b3b10eb1c9f1b4db7806d5475bae3071c0243c299d49926bab1da3b6946f6"),
    "speech_tokenizer/model.safetensors": (
        682_293_092,
        "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ModelFileCheck:
    path: str
    expected_bytes: int
    observed_bytes: int | None
    expected_sha256: str
    observed_sha256: str | None
    passed: bool


def verify_model_root(model_root: str | Path) -> dict[str, Any]:
    root = Path(model_root).resolve()
    checks: list[ModelFileCheck] = []
    for relative, (expected_bytes, expected_sha256) in MODEL_FILES.items():
        candidate = root / Path(relative)
        observed_bytes = candidate.stat().st_size if candidate.is_file() else None
        observed_sha256 = _sha256(candidate) if observed_bytes == expected_bytes else None
        checks.append(
            ModelFileCheck(
                path=relative,
                expected_bytes=expected_bytes,
                observed_bytes=observed_bytes,
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                passed=observed_bytes == expected_bytes and observed_sha256 == expected_sha256,
            )
        )
    return {
        "schema_version": 1,
        "model_repo_id": MODEL_REPO_ID,
        "model_revision": MODEL_REVISION,
        "model_root": str(root),
        "files": [asdict(item) for item in checks],
        "result": "PASS" if all(item.passed for item in checks) else "FAIL",
        "model_loaded": False,
        "generation_started": False,
    }


def download_model(model_root: str | Path) -> dict[str, Any]:
    destination = Path(model_root).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    hub = importlib.import_module("huggingface_hub")
    hub.snapshot_download(
        repo_id=MODEL_REPO_ID,
        revision=MODEL_REVISION,
        local_dir=str(destination),
    )
    return verify_model_root(destination)


def verify_runtime(
    model_root: str | Path,
    *,
    ffmpeg: str | Path,
    load_model: bool = True,
) -> dict[str, Any]:
    model = verify_model_root(model_root)
    ffmpeg_path = Path(ffmpeg).resolve()
    package_versions: dict[str, str] = {}
    error: str | None = None
    cuda_available = False
    gpu_name: str | None = None
    loaded = False
    ffmpeg_ok = False
    try:
        metadata = importlib.import_module("importlib.metadata")
        for distribution in ("torch", "torchaudio", "qwen-tts", "imageio-ffmpeg", "ai-video-production"):
            package_versions[distribution] = metadata.version(distribution)
        torch = importlib.import_module("torch")
        importlib.import_module("qwen_tts")
        importlib.import_module("soundfile")
        cuda_available = bool(torch.cuda.is_available())
        gpu_name = torch.cuda.get_device_name(0) if cuda_available else None
        ffmpeg_proc = subprocess.run(
            [str(ffmpeg_path), "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=30,
            shell=False,
        )
        ffmpeg_ok = ffmpeg_path.is_file() and ffmpeg_proc.returncode == 0
        if load_model and model["result"] == "PASS" and cuda_available:
            qwen = importlib.import_module("qwen_tts")
            cls = getattr(qwen, "Qwen3TTSModel")
            loaded_model = cls.from_pretrained(
                str(Path(model_root).resolve()),
                device_map="cuda:0",
                dtype=torch.bfloat16,
                attn_implementation="sdpa",
                local_files_only=True,
            )
            del loaded_model
            torch.cuda.empty_cache()
            loaded = True
    except Exception as exc:  # reported without a traceback or secret-bearing environment
        error = f"{type(exc).__name__}: {exc}"
    passed = model["result"] == "PASS" and cuda_available and ffmpeg_ok and (loaded or not load_model) and error is None
    return {
        "schema_version": 1,
        "result": "PASS" if passed else "FAIL",
        "model_revision": MODEL_REVISION,
        "model_root": str(Path(model_root).resolve()),
        "ffmpeg": str(ffmpeg_path),
        "ffmpeg_pass": ffmpeg_ok,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "model_loaded": loaded,
        "load_model_requested": load_model,
        "generation_started": False,
        "package_versions": package_versions,
        "model_files": model["files"],
        "error": error,
    }


def _write_report(path: str | Path | None, value: dict[str, Any]) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    model_parser = sub.add_parser("model")
    model_parser.add_argument("--model-root", required=True)
    model_parser.add_argument("--download", action="store_true")
    model_parser.add_argument("--report")
    runtime_parser = sub.add_parser("runtime")
    runtime_parser.add_argument("--model-root", required=True)
    runtime_parser.add_argument("--ffmpeg", required=True)
    runtime_parser.add_argument("--skip-model-load", action="store_true")
    runtime_parser.add_argument("--report")
    args = parser.parse_args(argv)
    if args.command == "model":
        value = download_model(args.model_root) if args.download else verify_model_root(args.model_root)
    else:
        value = verify_runtime(
            args.model_root,
            ffmpeg=args.ffmpeg,
            load_model=not args.skip_model_load,
        )
    _write_report(args.report, value)
    return 0 if value["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
