"""Generate review-only silence/filler/disfluency cut candidates (TASK-024)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cut_candidates import (
    CutCandidateAnalyzer,
    CutCandidateConfig,
    CutCandidatePublicationService,
    FfmpegSilenceDetector,
    load_transcript_manifest,
)
from .errors import ProductError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis_audio", type=Path, help="Normalized 16-bit PCM analysis WAV")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-asset-id", required=True)
    parser.add_argument("--transcript", type=Path, help="Optional canonical TASK-006 transcript.json")
    parser.add_argument("--silence-threshold-dbfs", type=float, default=-45.0)
    parser.add_argument("--min-silence-ms", type=int, default=500)
    parser.add_argument("--min-cut-ms", type=int, default=180)
    parser.add_argument("--preserve-leading-ms", type=int, default=80)
    parser.add_argument("--preserve-trailing-ms", type=int, default=120)
    parser.add_argument("--transcript-guard-ms", type=int, default=80)
    parser.add_argument("--max-filler-ms", type=int, default=2500)
    parser.add_argument("--repeat-max-gap-ms", type=int, default=1500)
    parser.add_argument("--repeat-min-chars", type=int, default=4)
    parser.add_argument("--ffmpeg-executable", default="ffmpeg")
    parser.add_argument("--ffmpeg-timeout-seconds", type=int, default=1800)
    parser.add_argument(
        "--filler-term",
        action="append",
        dest="filler_terms",
        help="Replace the built-in filler dictionary with one or more exact filler terms",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        defaults = CutCandidateConfig()
        config = CutCandidateConfig(
            silence_threshold_dbfs=args.silence_threshold_dbfs,
            min_silence_ms=args.min_silence_ms,
            min_cut_ms=args.min_cut_ms,
            preserve_leading_ms=args.preserve_leading_ms,
            preserve_trailing_ms=args.preserve_trailing_ms,
            transcript_guard_ms=args.transcript_guard_ms,
            max_filler_ms=args.max_filler_ms,
            repeat_max_gap_ms=args.repeat_max_gap_ms,
            repeat_min_chars=args.repeat_min_chars,
            ffmpeg_timeout_seconds=args.ffmpeg_timeout_seconds,
            filler_terms=tuple(args.filler_terms) if args.filler_terms else defaults.filler_terms,
        )
        transcript = load_transcript_manifest(args.transcript) if args.transcript else None
        detector = FfmpegSilenceDetector(executable=args.ffmpeg_executable)
        manifest = CutCandidateAnalyzer.analyze(
            args.analysis_audio,
            source_asset_id=args.source_asset_id,
            transcript=transcript,
            config=config,
            detector=detector,
        )
        result = CutCandidatePublicationService.publish(manifest, args.output_dir)
        print(
            json.dumps(
                {
                    "ok": True,
                    "manifest": str(result.manifest_path),
                    "report": str(result.report_path),
                    "candidate_count": len(manifest.candidates),
                    "keep_block_count": len(manifest.keep_blocks),
                    "auto_apply_authorized": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (ProductError, ValueError) as exc:
        if isinstance(exc, ProductError):
            payload = exc.to_envelope()
        else:
            payload = {"error": {"code": "ERR_CUT_INPUT", "message": str(exc)}}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
