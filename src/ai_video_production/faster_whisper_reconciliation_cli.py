"""CLI for TASK-023 model-free FasterWhisper reconciliation evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider
from .faster_whisper_reconciliation import (
    build_execution_identity,
    build_reconciliation_report,
    sha256_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit model-free, text-free TASK-023 FasterWhisper provider evidence"
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--source-file", type=Path)
    source.add_argument("--source-sha256")
    parser.add_argument("--language")
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument(
        "--vad-filter",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--allow-model-download", action="store_true")
    parser.add_argument("--cache-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = FasterWhisperConfig(
            model=args.model,
            device=args.device,
            compute_type=args.compute_type,
            beam_size=args.beam_size,
            vad_filter=args.vad_filter,
            allow_model_download=args.allow_model_download,
            cache_directory=args.cache_dir,
        )
        provider = FasterWhisperProvider(config)
        payload = build_reconciliation_report(provider)

        source_sha256 = args.source_sha256
        if args.source_file is not None:
            source_sha256 = sha256_file(args.source_file)
        if source_sha256 is not None:
            payload["execution_identity"] = build_execution_identity(
                provider,
                source_sha256=source_sha256,
                requested_language=args.language,
            ).to_dict()

        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": {"code": "ERR_TASK023_EVIDENCE_INPUT", "message": str(exc)}},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
