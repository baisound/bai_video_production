"""TASK-049 R3 adapters from existing BVP canonical services into CGEL.

The adapters reference existing Asset/Normalization/Transcript contracts. They
never create a second Asset registry, invoke ASR, read media bytes, or mutate a
Production Timeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Iterable

from .assets import AssetRecord, AssetType
from .canonical_game_event import (
    GameEnvironment,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
)
from .errors import ProductError, ProductErrorCategory
from .game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from .normalization import NormalizationResult
from .subtitles import TranscriptManifest, TranscriptSegment
from .timebase import FrameRate, FrameRounding, TimingKind
from .timeline_mapping import AffineTimeMap


class TranscriptClockDomain(str, Enum):
    MATCH_CLOCK = "MATCH_CLOCK"
    UPSTREAM_SOURCE_CLOCK = "UPSTREAM_SOURCE_CLOCK"


def _validation(code: str, message: str, **details: object) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.VALIDATION, False, details=dict(details))


def _integrity(code: str, message: str, **details: object) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.DATA_INTEGRITY, False, details=dict(details))


def _video_rate_from_asset(asset: AssetRecord) -> FrameRate | None:
    streams = asset.media_metadata.get("streams")
    if not isinstance(streams, list):
        return None
    for stream in streams:
        if not isinstance(stream, dict) or stream.get("codec_type") != "video":
            continue
        value = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
        if value:
            try:
                return FrameRate.parse(str(value))
            except ValueError:
                return None
    return None


def _duration_from_asset(asset: AssetRecord) -> int | None:
    value = asset.media_metadata.get("duration_us")
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _lineage_root(asset: AssetRecord) -> str:
    source = asset.source_ref
    if isinstance(source, str) and source.startswith("ASSET-"):
        return source
    return asset.asset_id


@dataclass(frozen=True, slots=True)
class GameAnalysisMediaBinding:
    """Binds one admitted CFR BVP video Asset to the CGEL Match clock."""

    original_source_asset: AssetRecord
    analysis_video_asset: AssetRecord
    analysis_rate: FrameRate
    upstream_to_analysis_map: AffineTimeMap | None

    def __post_init__(self) -> None:
        if self.original_source_asset.production_job_id != self.analysis_video_asset.production_job_id:
            raise ValueError("original and analysis Assets must belong to the same Production Job")
        if self.original_source_asset.asset_type not in {AssetType.VIDEO, AssetType.GENERATED_VIDEO}:
            raise ValueError("original_source_asset must be a video Asset")
        if self.analysis_video_asset.asset_type not in {AssetType.VIDEO, AssetType.GENERATED_VIDEO}:
            raise ValueError("analysis_video_asset must be a video Asset")
        if not isinstance(self.analysis_rate, FrameRate):
            raise ValueError("analysis_rate must be an exact FrameRate")
        if self.analysis_video_asset.asset_id != self.original_source_asset.asset_id:
            if _lineage_root(self.analysis_video_asset) != self.original_source_asset.asset_id:
                raise ValueError("analysis video Asset must retain source Asset lineage")
            if self.upstream_to_analysis_map is None:
                raise ValueError("derived analysis video requires an upstream affine map")
        elif self.upstream_to_analysis_map is not None:
            raise ValueError("identity analysis video must not invent an affine normalization map")

    @property
    def production_job_id(self) -> str:
        return self.analysis_video_asset.production_job_id

    @property
    def original_source_asset_id(self) -> str:
        return self.original_source_asset.asset_id

    @property
    def analysis_video_asset_id(self) -> str:
        return self.analysis_video_asset.asset_id

    def analysis_clock_range(self, start_us: int, end_us: int) -> SourceFrameRange:
        if start_us < 0 or end_us <= start_us:
            raise ValueError("microsecond range must be positive and end-exclusive")
        start = self.analysis_rate.us_to_frame(start_us, rounding=FrameRounding.FLOOR)
        end = self.analysis_rate.us_to_frame(end_us, rounding=FrameRounding.CEIL)
        return SourceFrameRange(start, end)

    def upstream_source_clock_range(self, start_us: int, end_us: int) -> SourceFrameRange:
        if start_us < 0 or end_us <= start_us:
            raise ValueError("microsecond range must be positive and end-exclusive")
        if self.upstream_to_analysis_map is None:
            return self.analysis_clock_range(start_us, end_us)
        mapped_start = self.upstream_to_analysis_map.source_to_normalized(
            start_us, rounding=FrameRounding.FLOOR
        )
        mapped_end = self.upstream_to_analysis_map.source_to_normalized(
            end_us, rounding=FrameRounding.CEIL
        )
        return self.analysis_clock_range(mapped_start, mapped_end)

    def create_match(
        self,
        *,
        game_profile_id: str,
        game_profile_version: str,
        game_version: str,
        environment: GameEnvironment,
        perspective: GamePerspective,
        status: GameMatchStatus = GameMatchStatus.CREATED,
    ) -> GameMatch:
        return GameMatch(
            production_job_id=self.production_job_id,
            source_asset_id=self.analysis_video_asset_id,
            game_profile_id=game_profile_id,
            game_profile_version=game_profile_version,
            game_version=game_version,
            environment=environment,
            perspective=perspective,
            source_rate=self.analysis_rate,
            status=status,
        )


class GameIntelligenceNormalizationAdapter:
    """Admit the existing TASK-004 video reference as the exact CGEL clock."""

    @staticmethod
    def bind(result: NormalizationResult) -> GameAnalysisMediaBinding:
        if not isinstance(result, NormalizationResult):
            raise TypeError("result must be a TASK-004 NormalizationResult")
        original = result.source_asset
        analysis = result.video_reference_asset
        if analysis is None:
            raise _validation(
                "ERR_GAME_ANALYSIS_VIDEO_REQUIRED",
                "Game Intelligence requires a video reference Asset",
            )

        if result.proxy_asset is None:
            if analysis.asset_id != original.asset_id:
                raise _integrity(
                    "ERR_GAME_ANALYSIS_REFERENCE_UNEXPECTED",
                    "Normalization returned a derived video reference without proxy provenance",
                )
            if result.timing.kind is TimingKind.VFR:
                raise _validation(
                    "ERR_GAME_TIMEBASE_VFR_REQUIRES_NORMALIZED_CFR",
                    "VFR media must use the admitted TASK-004 CFR proxy before CGEL frame indexing",
                )
            if result.timing.kind is not TimingKind.CFR:
                raise _validation(
                    "ERR_GAME_TIMEBASE_CFR_REQUIRED",
                    "CGEL frame indexing requires an admitted CFR analysis video",
                )
            rate = result.timing.avg_frame_rate or result.timing.nominal_frame_rate
            if rate is None:
                raise _integrity(
                    "ERR_GAME_TIMEBASE_RATE_MISSING",
                    "CFR analysis video has no exact admitted frame rate",
                )
            return GameAnalysisMediaBinding(original, analysis, rate, None)

        if analysis.asset_id != result.proxy_asset.asset_id:
            raise _integrity(
                "ERR_GAME_ANALYSIS_PROXY_REFERENCE_MISMATCH",
                "TASK-004 proxy must be the admitted video reference when present",
            )
        rate = _video_rate_from_asset(analysis)
        if rate is None:
            raise _integrity(
                "ERR_GAME_ANALYSIS_PROXY_RATE_MISSING",
                "Normalized CFR proxy Asset lacks an exact video frame rate",
            )
        source_duration = result.timing.duration_us or _duration_from_asset(original)
        normalized_duration = _duration_from_asset(analysis)
        if source_duration is None or normalized_duration is None:
            raise _integrity(
                "ERR_GAME_TIME_MAPPING_DURATION_MISSING",
                "Source/proxy duration is required for the exact affine time handoff",
            )
        mapping = AffineTimeMap(0, source_duration, 0, normalized_duration)
        return GameAnalysisMediaBinding(original, analysis, rate, mapping)


class TranscriptEvidenceAdapter:
    """Project an existing BVP TranscriptManifest into text-free Game Evidence."""

    @staticmethod
    def _confidence_milli(segment: TranscriptSegment) -> int:
        if segment.confidence is None:
            return 0
        value = Decimal(str(segment.confidence)) * Decimal(1000)
        result = int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return max(0, min(1000, result))

    @staticmethod
    def compile(
        *,
        match: GameMatch,
        media_binding: GameAnalysisMediaBinding,
        transcript: TranscriptManifest,
        transcript_asset: AssetRecord,
        clock_domain: TranscriptClockDomain,
        producer_version: str,
        artifact_ref: str,
        bvp_evidence_id: str | None = None,
    ) -> tuple[GameEvidence, ...]:
        if not isinstance(clock_domain, TranscriptClockDomain):
            raise ValueError("clock_domain must be TranscriptClockDomain")
        if match.production_job_id != media_binding.production_job_id:
            raise _validation(
                "ERR_GAME_MATCH_JOB_MISMATCH",
                "Match and GameAnalysisMediaBinding belong to different Jobs",
            )
        if match.source_asset_id != media_binding.analysis_video_asset_id:
            raise _validation(
                "ERR_GAME_MATCH_CLOCK_ASSET_MISMATCH",
                "Match source Asset is not the admitted analysis video clock Asset",
            )
        if transcript.source_asset_id != transcript_asset.asset_id:
            raise _validation(
                "ERR_GAME_TRANSCRIPT_ASSET_MISMATCH",
                "Transcript source_asset_id does not match the supplied BVP transcript Asset",
            )
        if transcript_asset.production_job_id != match.production_job_id:
            raise _validation(
                "ERR_GAME_TRANSCRIPT_JOB_MISMATCH",
                "Transcript Asset belongs to another Production Job",
            )
        if _lineage_root(transcript_asset) != media_binding.original_source_asset_id and transcript_asset.asset_id != media_binding.analysis_video_asset_id:
            raise _validation(
                "ERR_GAME_TRANSCRIPT_LINEAGE_MISMATCH",
                "Transcript Asset does not share admitted source lineage with the Match",
            )
        if not artifact_ref or "\x00" in artifact_ref or len(artifact_ref) > 384:
            raise ValueError("artifact_ref must be a bounded stable reference")

        rows: list[GameEvidence] = []
        for segment in transcript.segments:
            if clock_domain is TranscriptClockDomain.MATCH_CLOCK:
                source_range = media_binding.analysis_clock_range(segment.start_us, segment.end_us)
            else:
                source_range = media_binding.upstream_source_clock_range(segment.start_us, segment.end_us)
            rows.append(
                GameEvidence(
                    production_job_id=match.production_job_id,
                    match_id=match.match_id,
                    source_asset_id=match.source_asset_id,
                    producer=f"{transcript.provider_id}:{transcript.model_id}",
                    producer_version=producer_version,
                    evidence_type=GameEvidenceType.ASR,
                    source_range=source_range,
                    confidence_milli=TranscriptEvidenceAdapter._confidence_milli(segment),
                    artifact_ref=f"{artifact_ref}#{segment.segment_id}",
                    bvp_evidence_id=bvp_evidence_id,
                )
            )
        return tuple(rows)


__all__ = [
    "GameAnalysisMediaBinding",
    "GameIntelligenceNormalizationAdapter",
    "TranscriptClockDomain",
    "TranscriptEvidenceAdapter",
]
