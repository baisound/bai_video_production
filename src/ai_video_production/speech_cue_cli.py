"""Generate deterministic semantic speech cues from a canonical BVP Transcript."""

from __future__ import annotations

import argparse
from importlib import resources
import json
from pathlib import Path

from .cut_candidates import load_transcript_manifest
from .errors import ProductError
from .faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider
from .large_media_transcription import ChunkedTranscriptionConfig
from .speech_cue_application import SpeechCueApplicationService
from .semantic_audio_cues import (
    KeywordProfile,
    load_keyword_profile,
)
from .timebase import FrameRate


DEFAULT_PROFILE = "dbd-chase-call-ja-v1"


def _builtin_profile(profile_id: str) -> KeywordProfile:
    if profile_id != DEFAULT_PROFILE:
        raise ValueError(f"unknown built-in keyword profile: {profile_id}")
    resource = resources.files("ai_video_production").joinpath(
        "profile_resources", f"{profile_id}.json"
    )
    value = json.loads(resource.read_text(encoding="utf-8"))
    return KeywordProfile.from_dict(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "transcript", type=Path, nargs="?",
        help="Canonical BVP Transcript JSON. Omit when --media is used.",
    )
    parser.add_argument("--media", type=Path, help="Local media to transcribe with word timing")
    parser.add_argument("--source-asset-id", help="Existing BVP ASSET ID; required with --media")
    parser.add_argument("--language", help="BCP-47 language; defaults to the keyword profile language")
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--cache-directory", type=Path)
    parser.add_argument(
        "--allow-model-download", action="store_true",
        help="Explicitly allow FasterWhisper model download; default is local-cache-only",
    )
    parser.add_argument(
        "--resumable", action="store_true",
        help="Use bounded/resumable chunk transcription for long media",
    )
    parser.add_argument("--chunk-seconds", type=int, default=900)
    parser.add_argument("--overlap-seconds", type=int, default=2)
    parser.add_argument("--ffmpeg-executable", default="ffmpeg")
    parser.add_argument("--ffprobe-executable", default="ffprobe")
    resume_group = parser.add_mutually_exclusive_group()
    resume_group.add_argument("--resume", action="store_true")
    resume_group.add_argument("--restart", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--source-frame-rate",
        required=True,
        help="Exact rational source FPS such as 60000/1001; do not pass 59.94",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--profile", type=Path, help="Local keyword profile JSON")
    group.add_argument("--profile-id", default=DEFAULT_PROFILE, help="Built-in profile ID")
    parser.add_argument(
        "--include-review-in-projection",
        action="store_true",
        help="Include REVIEW cues in the non-canonical SKILL sidecar; never auto-applied",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if (args.transcript is None) == (args.media is None):
            raise ValueError("provide exactly one of transcript or --media")
        profile = load_keyword_profile(args.profile) if args.profile else _builtin_profile(args.profile_id)
        source_rate = FrameRate.parse(args.source_frame_rate)
        if args.transcript is not None and (args.resumable or args.resume or args.restart):
            raise ValueError("resumable controls are valid only with --media")
        if args.media is not None:
            if not args.source_asset_id:
                raise ValueError("--source-asset-id is required with --media")
            provider = FasterWhisperProvider(FasterWhisperConfig(
                model=args.model,
                device=args.device,
                compute_type=args.compute_type,
                allow_model_download=args.allow_model_download,
                cache_directory=args.cache_directory,
            ))
            language = args.language or profile.language
            if (args.resume or args.restart) and not args.resumable:
                raise ValueError("--resume/--restart require --resumable")
            if args.resumable:
                result = SpeechCueApplicationService.transcribe_resumable_and_detect(
                    args.media,
                    source_asset_id=args.source_asset_id,
                    source_frame_rate=source_rate,
                    keyword_profile=profile,
                    output_directory=args.output_dir,
                    provider=provider,
                    config=ChunkedTranscriptionConfig(
                        chunk_seconds=args.chunk_seconds,
                        overlap_seconds=args.overlap_seconds,
                        ffmpeg_executable=args.ffmpeg_executable,
                        ffprobe_executable=args.ffprobe_executable,
                    ),
                    language=language,
                    include_review_in_projection=args.include_review_in_projection,
                    resume=args.resume,
                    restart=args.restart,
                )
            else:
                result = SpeechCueApplicationService.transcribe_and_detect(
                    args.media,
                    source_asset_id=args.source_asset_id,
                    source_frame_rate=source_rate,
                    keyword_profile=profile,
                    output_directory=args.output_dir,
                    provider=provider,
                    language=language,
                    include_review_in_projection=args.include_review_in_projection,
                )
        else:
            transcript = load_transcript_manifest(args.transcript)
            result = SpeechCueApplicationService.detect_from_transcript(
                transcript,
                source_frame_rate=source_rate,
                keyword_profile=profile,
                output_directory=args.output_dir,
                include_review_in_projection=args.include_review_in_projection,
            )
        print(json.dumps(result.public_status(), ensure_ascii=False, sort_keys=True))
        return 0
    except (ProductError, ValueError, OSError, json.JSONDecodeError) as exc:
        if isinstance(exc, ProductError):
            payload = exc.to_envelope()
        else:
            payload = {"error": {"code": "ERR_SPEECH_CUE_INPUT", "message": str(exc)}}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
