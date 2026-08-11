"""Create a local Transcript and SRT from an audio or video file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .errors import ProductError
from .faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider, LocalTranscriptionService
from .large_media_transcription import ChunkedTranscriptionConfig, ResumableTranscriptionService
from .timebase import FrameRate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path, help="Input audio or video file")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-asset-id")
    parser.add_argument("--language", help="BCP-47 language such as ja; omit for detection")
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--no-vad", action="store_true")
    parser.add_argument("--allow-model-download", action="store_true", help="Authorize network model download when not cached")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--chunk-seconds", type=int, help="Enable resumable bounded large-media transcription")
    parser.add_argument("--chunk-overlap-seconds", type=int, default=2)
    parser.add_argument("--resume", action="store_true", help="Resume verified unfinished chunk state")
    parser.add_argument("--restart", action="store_true", help="Explicitly discard unfinished chunk state")
    parser.add_argument("--ffmpeg-executable", default="ffmpeg")
    parser.add_argument("--ffprobe-executable", default="ffprobe")
    parser.add_argument("--timeline-rate", default="30000/1001")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = FasterWhisperConfig(
            model=args.model, device=args.device, compute_type=args.compute_type,
            beam_size=args.beam_size, vad_filter=not args.no_vad,
            allow_model_download=args.allow_model_download,
            cache_directory=str(args.cache_dir) if args.cache_dir else None,
        )
        provider = FasterWhisperProvider(config)
        timeline_rate = FrameRate.parse(args.timeline_rate)
        if args.chunk_seconds is None:
            if args.resume or args.restart:
                raise ValueError("--resume/--restart require --chunk-seconds")
            result = LocalTranscriptionService.run(
                args.media,
                args.output_dir,
                provider=provider,
                source_asset_id=args.source_asset_id,
                language=args.language,
                timeline_rate=timeline_rate,
            )
        else:
            chunk_config = ChunkedTranscriptionConfig(
                chunk_seconds=args.chunk_seconds,
                overlap_seconds=args.chunk_overlap_seconds,
                ffmpeg_executable=args.ffmpeg_executable,
                ffprobe_executable=args.ffprobe_executable,
            )
            result = ResumableTranscriptionService.run(
                args.media,
                args.output_dir,
                provider=provider,
                config=chunk_config,
                source_asset_id=args.source_asset_id,
                language=args.language,
                timeline_rate=timeline_rate,
                resume=args.resume,
                restart=args.restart,
            )
        print(json.dumps({
            "ok": True,
            "output_directory": str(result.output_directory),
            "transcript": str(result.transcript_path),
            "srt": str(result.subtitle_path),
            "report": str(result.report_path),
            "segments": len(result.transcript.segments),
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (ProductError, ValueError) as exc:
        if isinstance(exc, ProductError):
            payload = exc.to_envelope()
        else:
            payload = {"error": {"code": "ERR_ASR_INPUT", "message": str(exc)}}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
