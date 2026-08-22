"""Deterministic, text-free semantic audio cue extraction from canonical transcripts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping

from .atomic import AtomicJsonWriter
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, sha256_json, validate_sha256
from .subtitles import TranscriptManifest, TranscriptSegment, TranscriptWord
from .timebase import FrameRate, FrameRounding


_PROFILE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_KEYWORD_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
_MAX_PROFILE_BYTES = 256 * 1024
_MAX_KEYWORDS = 64
_MAX_ALIASES_PER_KEYWORD = 64
_MAX_ALIAS_LENGTH = 128
_MAX_PHRASE_WORDS = 8
_MAX_PHRASE_GAP_US = 750_000


class KeywordMatchMode(str, Enum):
    EXACT = "EXACT"
    PHRASE = "PHRASE"


class CueReviewState(str, Enum):
    CONFIRMED = "CONFIRMED"
    REVIEW = "REVIEW"
    REJECTED = "REJECTED"


class TimingGranularity(str, Enum):
    WORD = "WORD"
    SEGMENT_FALLBACK = "SEGMENT_FALLBACK"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    out: list[str] = []
    for char in normalized:
        category = unicodedata.category(char)
        if category.startswith("P") or category.startswith("Z") or char.isspace():
            out.append(" ")
        else:
            out.append(char)
    return " ".join("".join(out).split())


def _compact(value: str) -> str:
    return _normalize_text(value).replace(" ", "")


def _bounded_alias(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("keyword alias must be text")
    if "\x00" in value or not value.strip() or len(value) > _MAX_ALIAS_LENGTH:
        raise ValueError("keyword alias must be non-empty bounded text without NUL")
    if not _compact(value):
        raise ValueError("keyword alias normalizes to empty text")
    return value.strip()


@dataclass(frozen=True, slots=True)
class KeywordRule:
    keyword_id: str
    aliases: tuple[str, ...]
    match_mode: KeywordMatchMode = KeywordMatchMode.PHRASE
    minimum_confidence: float = 0.65

    def __post_init__(self) -> None:
        if not _KEYWORD_ID.fullmatch(self.keyword_id):
            raise ValueError("keyword_id is invalid")
        if not 1 <= len(self.aliases) <= _MAX_ALIASES_PER_KEYWORD:
            raise ValueError("aliases count is outside the accepted bound")
        aliases = tuple(_bounded_alias(value) for value in self.aliases)
        normalized = [_compact(value) for value in aliases]
        if len(set(normalized)) != len(normalized):
            raise ValueError("keyword aliases must be unique after normalization")
        object.__setattr__(self, "aliases", aliases)
        object.__setattr__(self, "match_mode", KeywordMatchMode(self.match_mode))
        if isinstance(self.minimum_confidence, bool) or not 0 <= float(self.minimum_confidence) <= 1:
            raise ValueError("minimum_confidence must be 0-1")
        object.__setattr__(self, "minimum_confidence", float(self.minimum_confidence))

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword_id": self.keyword_id,
            "aliases": sorted(self.aliases, key=lambda value: (_compact(value), value)),
            "match_mode": self.match_mode.value,
            "minimum_confidence": self.minimum_confidence,
        }


@dataclass(frozen=True, slots=True)
class KeywordProfile:
    profile_id: str
    language: str
    keywords: tuple[KeywordRule, ...]

    def __post_init__(self) -> None:
        if not _PROFILE_ID.fullmatch(self.profile_id):
            raise ValueError("profile_id is invalid")
        if not _LANGUAGE.fullmatch(self.language):
            raise ValueError("language must be a BCP-47 language tag")
        if not 1 <= len(self.keywords) <= _MAX_KEYWORDS:
            raise ValueError("keyword count is outside the accepted bound")
        ids: set[str] = set()
        alias_owners: dict[str, str] = {}
        for rule in self.keywords:
            if rule.keyword_id in ids:
                raise ValueError("duplicate keyword_id")
            ids.add(rule.keyword_id)
            for alias in rule.aliases:
                key = _compact(alias)
                owner = alias_owners.get(key)
                if owner is not None and owner != rule.keyword_id:
                    raise ValueError("normalized alias cannot belong to multiple keyword IDs")
                alias_owners[key] = rule.keyword_id

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KeywordProfile":
        if set(value) != {"profile_id", "language", "keywords"}:
            raise ValueError("keyword profile contains missing or unknown fields")
        raw_keywords = value["keywords"]
        if not isinstance(raw_keywords, list):
            raise ValueError("keywords must be a list")
        rules: list[KeywordRule] = []
        for raw in raw_keywords:
            if not isinstance(raw, Mapping):
                raise ValueError("keyword rule must be an object")
            allowed = {"keyword_id", "aliases", "match_mode", "minimum_confidence"}
            if set(raw) != allowed:
                raise ValueError("keyword rule contains missing or unknown fields")
            aliases = raw["aliases"]
            if not isinstance(aliases, list):
                raise ValueError("aliases must be a list")
            keyword_id = raw["keyword_id"]
            match_mode = raw["match_mode"]
            minimum_confidence = raw["minimum_confidence"]
            if not isinstance(keyword_id, str) or not isinstance(match_mode, str):
                raise ValueError("keyword_id and match_mode must be text")
            if (
                isinstance(minimum_confidence, bool)
                or not isinstance(minimum_confidence, (int, float))
            ):
                raise ValueError("minimum_confidence must be numeric")
            rules.append(
                KeywordRule(
                    keyword_id=keyword_id,
                    aliases=tuple(aliases),
                    match_mode=KeywordMatchMode(match_mode),
                    minimum_confidence=float(minimum_confidence),
                )
            )
        return cls(str(value["profile_id"]), str(value["language"]), tuple(rules))

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "language": self.language,
            "keywords": [
                rule.to_dict()
                for rule in sorted(self.keywords, key=lambda item: item.keyword_id)
            ],
        }

    @property
    def profile_sha256(self) -> str:
        return sha256_json(self.to_dict())


@dataclass(frozen=True, slots=True)
class SpeechCueHit:
    cue_id: str
    keyword_id: str
    source_start_us: int
    source_end_us: int
    source_start_frame: int
    source_end_frame_exclusive: int
    confidence: float | None
    timing_granularity: TimingGranularity
    review_state: CueReviewState
    source_segment_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"CUE-[0-9a-f]{24}", self.cue_id):
            raise ValueError("cue_id is invalid")
        if not _KEYWORD_ID.fullmatch(self.keyword_id):
            raise ValueError("keyword_id is invalid")
        if self.source_start_us < 0 or self.source_end_us <= self.source_start_us:
            raise ValueError("cue source microsecond range is invalid")
        if self.source_start_frame < 0 or self.source_end_frame_exclusive <= self.source_start_frame:
            raise ValueError("cue source frame range is invalid")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("cue confidence must be 0-1 when present")
        if self.review_state is CueReviewState.CONFIRMED and self.confidence is None:
            raise ValueError("confirmed cues require an observed confidence")
        if (
            self.review_state is CueReviewState.CONFIRMED
            and self.timing_granularity is not TimingGranularity.WORD
        ):
            raise ValueError("confirmed cues require canonical WORD timing")
        if not self.source_segment_ids or len(set(self.source_segment_ids)) != len(self.source_segment_ids):
            raise ValueError("source_segment_ids must be non-empty and unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "keyword_id": self.keyword_id,
            "source_range_us": {
                "start": self.source_start_us,
                "end_exclusive": self.source_end_us,
            },
            "source_range_frames": {
                "start": self.source_start_frame,
                "end_exclusive": self.source_end_frame_exclusive,
            },
            "confidence": self.confidence,
            "timing_granularity": self.timing_granularity.value,
            "review_state": self.review_state.value,
            "source_segment_ids": list(self.source_segment_ids),
        }


@dataclass(frozen=True, slots=True)
class SpeechCueManifest:
    manifest_id: str
    source_asset_id: str
    source_frame_rate: FrameRate
    transcript_manifest_sha256: str
    keyword_profile_id: str
    keyword_profile_sha256: str
    cues: tuple[SpeechCueHit, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"SCM-[0-9a-f]{32}", self.manifest_id):
            raise ValueError("manifest_id is invalid")
        validate_id(self.source_asset_id, IdKind.ASSET)
        validate_sha256(self.transcript_manifest_sha256, field_name="transcript_manifest_sha256")
        if not _PROFILE_ID.fullmatch(self.keyword_profile_id):
            raise ValueError("keyword_profile_id is invalid")
        validate_sha256(self.keyword_profile_sha256, field_name="keyword_profile_sha256")
        previous: tuple[int, int, str] | None = None
        ids: set[str] = set()
        for cue in self.cues:
            if cue.cue_id in ids:
                raise ValueError("duplicate cue_id")
            key = (cue.source_start_us, cue.source_end_us, cue.keyword_id)
            if previous is not None and key < previous:
                raise ValueError("cues must be deterministically ordered")
            ids.add(cue.cue_id)
            previous = key

    @property
    def counts(self) -> dict[str, int]:
        return {
            "confirmed": sum(cue.review_state is CueReviewState.CONFIRMED for cue in self.cues),
            "review": sum(cue.review_state is CueReviewState.REVIEW for cue in self.cues),
            "rejected": sum(cue.review_state is CueReviewState.REJECTED for cue in self.cues),
        }

    def to_body_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": "1.0.0",
            "manifest_id": self.manifest_id,
            "source_asset_id": self.source_asset_id,
            "source_frame_rate": {
                "numerator": self.source_frame_rate.numerator,
                "denominator": self.source_frame_rate.denominator,
            },
            "transcript_manifest_sha256": self.transcript_manifest_sha256,
            "keyword_profile_id": self.keyword_profile_id,
            "keyword_profile_sha256": self.keyword_profile_sha256,
            "counts": self.counts,
            "cues": [cue.to_dict() for cue in self.cues],
        }

    def to_dict(self) -> dict[str, Any]:
        body = self.to_body_dict()
        body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SpeechCueManifest":
        expected_root = {
            "manifest_version", "manifest_id", "source_asset_id", "source_frame_rate",
            "transcript_manifest_sha256", "keyword_profile_id", "keyword_profile_sha256",
            "counts", "cues", "manifest_sha256",
        }
        if set(value) != expected_root:
            raise ValueError("speech cue manifest contains missing or unknown fields")
        if value.get("manifest_version") != "1.0.0":
            raise ValueError("unsupported speech cue manifest version")
        claimed = value.get("manifest_sha256")
        if not isinstance(claimed, str):
            raise ValueError("manifest_sha256 is required")
        validate_sha256(claimed, field_name="manifest_sha256")
        body = dict(value)
        body.pop("manifest_sha256", None)
        if sha256_bytes(canonical_json_bytes(body)) != claimed:
            raise ValueError("speech cue manifest hash does not match its content")
        raw_counts = body.get("counts")
        raw_cues = body.get("cues")
        if (
            not isinstance(raw_counts, Mapping)
            or set(raw_counts) != {"confirmed", "review", "rejected"}
            or not isinstance(raw_cues, list)
            or len(raw_cues) > 10_000
        ):
            raise ValueError("speech cue manifest counts/cues are invalid")
        parsed_counts: dict[str, int] = {}
        for name in ("confirmed", "review", "rejected"):
            count = raw_counts.get(name)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("speech cue manifest counts must be non-negative integers")
            parsed_counts[name] = count
        rate_raw = body.get("source_frame_rate")
        if not isinstance(rate_raw, Mapping) or set(rate_raw) != {"numerator", "denominator"}:
            raise ValueError("source_frame_rate is invalid")
        numerator = rate_raw.get("numerator")
        denominator = rate_raw.get("denominator")
        if (
            isinstance(numerator, bool) or not isinstance(numerator, int) or numerator <= 0
            or isinstance(denominator, bool) or not isinstance(denominator, int) or denominator <= 0
        ):
            raise ValueError("source_frame_rate is invalid")
        expected_cue = {
            "cue_id", "keyword_id", "source_range_us", "source_range_frames",
            "confidence", "timing_granularity", "review_state", "source_segment_ids",
        }
        cues: list[SpeechCueHit] = []
        for raw in raw_cues:
            if not isinstance(raw, Mapping) or set(raw) != expected_cue:
                raise ValueError("cue contains missing or unknown fields")
            range_us = raw.get("source_range_us")
            range_frames = raw.get("source_range_frames")
            if (
                not isinstance(range_us, Mapping) or set(range_us) != {"start", "end_exclusive"}
                or not isinstance(range_frames, Mapping) or set(range_frames) != {"start", "end_exclusive"}
            ):
                raise ValueError("cue ranges are invalid")
            us_start, us_end = range_us.get("start"), range_us.get("end_exclusive")
            fr_start, fr_end = range_frames.get("start"), range_frames.get("end_exclusive")
            for item in (us_start, us_end, fr_start, fr_end):
                if isinstance(item, bool) or not isinstance(item, int):
                    raise ValueError("cue range values must be integers")
            confidence = raw.get("confidence")
            if confidence is not None and (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0 <= float(confidence) <= 1
            ):
                raise ValueError("cue confidence is invalid")
            segment_ids = raw.get("source_segment_ids")
            if (
                not isinstance(segment_ids, list)
                or not segment_ids
                or len(segment_ids) > 64
                or any(not isinstance(item, str) for item in segment_ids)
            ):
                raise ValueError("source_segment_ids must be a bounded text list")
            cues.append(
                SpeechCueHit(
                    cue_id=raw["cue_id"],
                    keyword_id=raw["keyword_id"],
                    source_start_us=us_start,
                    source_end_us=us_end,
                    source_start_frame=fr_start,
                    source_end_frame_exclusive=fr_end,
                    confidence=None if confidence is None else float(confidence),
                    timing_granularity=TimingGranularity(raw["timing_granularity"]),
                    review_state=CueReviewState(raw["review_state"]),
                    source_segment_ids=tuple(segment_ids),
                )
            )
        manifest = cls(
            manifest_id=body["manifest_id"],
            source_asset_id=body["source_asset_id"],
            source_frame_rate=FrameRate(numerator, denominator),
            transcript_manifest_sha256=body["transcript_manifest_sha256"],
            keyword_profile_id=body["keyword_profile_id"],
            keyword_profile_sha256=body["keyword_profile_sha256"],
            cues=tuple(cues),
        )
        if manifest.counts != parsed_counts:
            raise ValueError("speech cue manifest counts do not match cues")
        if manifest.to_dict()["manifest_sha256"] != claimed:
            raise ValueError("speech cue canonical reconstruction changed the manifest hash")
        return manifest


    def assert_bound_to(
        self,
        *,
        transcript: TranscriptManifest,
        keyword_profile: KeywordProfile,
    ) -> None:
        transcript_sha = str(transcript.to_dict()["manifest_sha256"])
        if self.source_asset_id != transcript.source_asset_id:
            raise ValueError("speech cue manifest source asset does not match transcript")
        if self.transcript_manifest_sha256 != transcript_sha:
            raise ValueError("speech cue manifest transcript hash mismatch")
        if self.keyword_profile_id != keyword_profile.profile_id:
            raise ValueError("speech cue manifest keyword profile ID mismatch")
        if self.keyword_profile_sha256 != keyword_profile.profile_sha256:
            raise ValueError("speech cue manifest keyword profile hash mismatch")


@dataclass(frozen=True, slots=True)
class _Candidate:
    keyword_id: str
    match_key: str
    start_us: int
    end_us: int
    confidence: float | None
    granularity: TimingGranularity
    state: CueReviewState
    source_segment_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _WordRef:
    word: TranscriptWord
    segment_id: str


def _confidence(words: Iterable[TranscriptWord]) -> float | None:
    values = [word.confidence for word in words]
    if not values or any(value is None for value in values):
        return None
    return min(float(value) for value in values if value is not None)


def _segment_ids(refs: Iterable[_WordRef]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(ref.segment_id for ref in refs))


def _word_candidates(transcript: TranscriptManifest, profile: KeywordProfile) -> list[_Candidate]:
    refs: list[_WordRef] = []
    for segment in transcript.segments:
        refs.extend(_WordRef(word, segment.segment_id) for word in segment.words)
    candidates: list[_Candidate] = []
    for rule in profile.keywords:
        aliases = { _compact(alias) for alias in rule.aliases }
        for index, ref in enumerate(refs):
            if rule.match_mode is KeywordMatchMode.EXACT:
                windows = ((ref,),)
            else:
                possible: list[tuple[_WordRef, ...]] = []
                current: list[_WordRef] = []
                previous_end: int | None = None
                for offset in range(index, min(len(refs), index + _MAX_PHRASE_WORDS)):
                    next_ref = refs[offset]
                    if previous_end is not None and next_ref.word.start_us - previous_end > _MAX_PHRASE_GAP_US:
                        break
                    current.append(next_ref)
                    possible.append(tuple(current))
                    previous_end = next_ref.word.end_us
                windows = tuple(possible)
            for window in windows:
                match_key = "".join(_compact(item.word.text) for item in window)
                if match_key not in aliases:
                    continue
                observed = _confidence(item.word for item in window)
                state = (
                    CueReviewState.CONFIRMED
                    if observed is not None and observed >= rule.minimum_confidence
                    else CueReviewState.REVIEW
                )
                candidates.append(
                    _Candidate(
                        keyword_id=rule.keyword_id,
                        match_key=match_key,
                        start_us=window[0].word.start_us,
                        end_us=window[-1].word.end_us,
                        confidence=observed,
                        granularity=TimingGranularity.WORD,
                        state=state,
                        source_segment_ids=_segment_ids(window),
                    )
                )
                # Prefer the shortest exact phrase window. Longer windows cannot be the same alias
                # without adding non-empty normalized text.
                break
    return candidates


def _segment_fallback_candidates(
    transcript: TranscriptManifest,
    profile: KeywordProfile,
    word_candidates: Iterable[_Candidate],
) -> list[_Candidate]:
    by_segment_keyword = {
        (segment_id, candidate.keyword_id)
        for candidate in word_candidates
        for segment_id in candidate.source_segment_ids
    }
    output: list[_Candidate] = []
    for segment in transcript.segments:
        normalized = _compact(segment.text)
        for rule in profile.keywords:
            if (segment.segment_id, rule.keyword_id) in by_segment_keyword:
                continue
            aliases = {_compact(alias) for alias in rule.aliases}
            matched = None
            if rule.match_mode is KeywordMatchMode.EXACT:
                if normalized in aliases:
                    matched = normalized
            else:
                for alias in sorted(aliases, key=lambda item: (len(item), item), reverse=True):
                    if alias in normalized:
                        matched = alias
                        break
            if matched is None:
                continue
            output.append(
                _Candidate(
                    keyword_id=rule.keyword_id,
                    match_key=matched,
                    start_us=segment.start_us,
                    end_us=segment.end_us,
                    confidence=segment.confidence,
                    granularity=TimingGranularity.SEGMENT_FALLBACK,
                    state=CueReviewState.REVIEW,
                    source_segment_ids=(segment.segment_id,),
                )
            )
    return output


def _overlap_iou(first: _Candidate, second: _Candidate) -> float:
    intersection = max(0, min(first.end_us, second.end_us) - max(first.start_us, second.start_us))
    if intersection <= 0:
        return 0.0
    union = max(first.end_us, second.end_us) - min(first.start_us, second.start_us)
    return intersection / union if union > 0 else 0.0


def _candidate_rank(candidate: _Candidate) -> tuple[int, int, float, int, int, tuple[str, ...]]:
    return (
        1 if candidate.granularity is TimingGranularity.WORD else 0,
        1 if candidate.state is CueReviewState.CONFIRMED else 0,
        candidate.confidence if candidate.confidence is not None else -1.0,
        -(candidate.end_us - candidate.start_us),
        -candidate.start_us,
        candidate.source_segment_ids,
    )


def _deduplicate(candidates: Iterable[_Candidate]) -> tuple[_Candidate, ...]:
    ordered = sorted(
        candidates,
        key=lambda item: (
            item.start_us,
            item.end_us,
            item.keyword_id,
            item.match_key,
            item.granularity.value,
            item.source_segment_ids,
        ),
    )
    groups: list[list[_Candidate]] = []
    for candidate in ordered:
        matching_group: list[_Candidate] | None = None
        for group in reversed(groups[-8:]):
            representative = max(group, key=_candidate_rank)
            if candidate.start_us >= max(item.end_us for item in group):
                continue
            if representative.keyword_id != candidate.keyword_id or representative.match_key != candidate.match_key:
                continue
            shared_provenance = bool(set(representative.source_segment_ids) & set(candidate.source_segment_ids))
            if shared_provenance or _overlap_iou(representative, candidate) >= 0.5:
                matching_group = group
                break
        if matching_group is None:
            groups.append([candidate])
        else:
            matching_group.append(candidate)

    merged: list[_Candidate] = []
    for group in groups:
        best = max(group, key=_candidate_rank)
        provenance = tuple(dict.fromkeys(
            segment_id
            for item in sorted(group, key=lambda candidate: (candidate.start_us, candidate.source_segment_ids))
            for segment_id in item.source_segment_ids
        ))
        merged.append(
            _Candidate(
                keyword_id=best.keyword_id,
                match_key=best.match_key,
                start_us=best.start_us,
                end_us=best.end_us,
                confidence=best.confidence,
                granularity=best.granularity,
                state=best.state,
                source_segment_ids=provenance,
            )
        )
    return tuple(sorted(merged, key=lambda item: (item.start_us, item.end_us, item.keyword_id)))


def _deterministic_id(prefix: str, value: Mapping[str, Any], length: int) -> str:
    digest = sha256_json(value).removeprefix("sha256:")
    return f"{prefix}-{digest[:length]}"


class SpeechCueDetectionService:
    @staticmethod
    def detect(
        transcript: TranscriptManifest,
        *,
        source_frame_rate: FrameRate,
        keyword_profile: KeywordProfile,
    ) -> SpeechCueManifest:
        if transcript.language != "und":
            transcript_primary = transcript.language.split("-", 1)[0]
            profile_primary = keyword_profile.language.split("-", 1)[0]
            if transcript_primary != profile_primary:
                raise ValueError("keyword profile language does not match transcript language")
        transcript_document = transcript.to_dict()
        transcript_sha = str(transcript_document["manifest_sha256"])
        profile_sha = keyword_profile.profile_sha256
        manifest_id = _deterministic_id(
            "SCM",
            {
                "source_asset_id": transcript.source_asset_id,
                "source_frame_rate": source_frame_rate.to_rational(),
                "transcript_manifest_sha256": transcript_sha,
                "keyword_profile_sha256": profile_sha,
            },
            32,
        )

        word_candidates = _word_candidates(transcript, keyword_profile)
        candidates = word_candidates + _segment_fallback_candidates(
            transcript,
            keyword_profile,
            word_candidates,
        )
        deduplicated = _deduplicate(candidates)
        if len(deduplicated) > 10_000:
            raise ValueError("speech cue count exceeds the accepted bound")
        cues: list[SpeechCueHit] = []
        for candidate in deduplicated:
            start_frame = source_frame_rate.us_to_frame(
                candidate.start_us,
                rounding=FrameRounding.FLOOR,
            )
            end_frame = source_frame_rate.us_to_frame(
                candidate.end_us,
                rounding=FrameRounding.CEIL,
            )
            end_frame = max(start_frame + 1, end_frame)
            cue_id = _deterministic_id(
                "CUE",
                {
                    "manifest_id": manifest_id,
                    "keyword_id": candidate.keyword_id,
                    "source_start_us": candidate.start_us,
                    "source_end_us": candidate.end_us,
                    "granularity": candidate.granularity.value,
                    "review_state": candidate.state.value,
                    "source_segment_ids": candidate.source_segment_ids,
                },
                24,
            )
            cues.append(
                SpeechCueHit(
                    cue_id=cue_id,
                    keyword_id=candidate.keyword_id,
                    source_start_us=candidate.start_us,
                    source_end_us=candidate.end_us,
                    source_start_frame=start_frame,
                    source_end_frame_exclusive=end_frame,
                    confidence=candidate.confidence,
                    timing_granularity=candidate.granularity,
                    review_state=candidate.state,
                    source_segment_ids=candidate.source_segment_ids,
                )
            )
        return SpeechCueManifest(
            manifest_id=manifest_id,
            source_asset_id=transcript.source_asset_id,
            source_frame_rate=source_frame_rate,
            transcript_manifest_sha256=transcript_sha,
            keyword_profile_id=keyword_profile.profile_id,
            keyword_profile_sha256=profile_sha,
            cues=tuple(cues),
        )


def parse_montage_semantic_audio_cues_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    expected_root = {
        "projection_version", "manifest_id", "manifest_sha256", "keyword_profile_id",
        "source_asset_id", "confirmed_count", "review_count", "projection_mode",
        "canonical_timeline", "auto_apply_authorized", "cues", "projection_sha256",
    }
    if set(value) != expected_root:
        raise ValueError("semantic audio cue projection contains missing or unknown fields")
    if value.get("projection_version") != "1.0.0":
        raise ValueError("unsupported semantic audio cue projection version")
    claimed = value.get("projection_sha256")
    if not isinstance(claimed, str):
        raise ValueError("projection_sha256 is required")
    validate_sha256(claimed, field_name="projection_sha256")
    body = dict(value)
    body.pop("projection_sha256", None)
    if sha256_bytes(canonical_json_bytes(body)) != claimed:
        raise ValueError("semantic audio cue projection hash mismatch")
    if body.get("canonical_timeline") is not False or body.get("auto_apply_authorized") is not False:
        raise ValueError("semantic audio cue projection cannot authorize canonical timeline mutation")
    manifest_id = body.get("manifest_id")
    if not isinstance(manifest_id, str) or not re.fullmatch(r"SCM-[0-9a-f]{32}", manifest_id):
        raise ValueError("projection manifest_id is invalid")
    manifest_sha = body.get("manifest_sha256")
    if not isinstance(manifest_sha, str):
        raise ValueError("projection manifest_sha256 is invalid")
    validate_sha256(manifest_sha, field_name="manifest_sha256")
    source_asset_id = body.get("source_asset_id")
    if not isinstance(source_asset_id, str):
        raise ValueError("projection source_asset_id is invalid")
    validate_id(source_asset_id, IdKind.ASSET)
    profile_id = body.get("keyword_profile_id")
    if not isinstance(profile_id, str) or not _PROFILE_ID.fullmatch(profile_id):
        raise ValueError("projection keyword_profile_id is invalid")
    confirmed_count = body.get("confirmed_count")
    review_count = body.get("review_count")
    for name, count in (("confirmed_count", confirmed_count), ("review_count", review_count)):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    cues = body.get("cues")
    if not isinstance(cues, list) or len(cues) > 10_000:
        raise ValueError("projection cues must be a bounded list")
    mode = body.get("projection_mode")
    if mode not in {"CONFIRMED_ONLY", "WITH_REVIEW"}:
        raise ValueError("projection_mode is invalid")
    expected_cue = {
        "cue_id", "keyword_id", "source_asset_id", "source_fps",
        "source_start_frame", "source_end_frame_exclusive", "confidence",
        "review_state", "timing_granularity",
    }
    seen: set[str] = set()
    previous_key: tuple[int, int, str] | None = None
    observed_confirmed = 0
    observed_review = 0
    for cue in cues:
        if not isinstance(cue, Mapping) or set(cue) != expected_cue:
            raise ValueError("projection cue contains missing or unknown fields")
        cue_id = cue.get("cue_id")
        if (
            not isinstance(cue_id, str)
            or not re.fullmatch(r"CUE-[0-9a-f]{24}", cue_id)
            or cue_id in seen
        ):
            raise ValueError("projection cue_id is invalid or duplicated")
        seen.add(cue_id)
        keyword_id = cue.get("keyword_id")
        if not isinstance(keyword_id, str) or not _KEYWORD_ID.fullmatch(keyword_id):
            raise ValueError("projection keyword_id is invalid")
        if cue.get("source_asset_id") != source_asset_id:
            raise ValueError("projection cue source asset does not match projection root")
        fps = cue.get("source_fps")
        if not isinstance(fps, Mapping) or set(fps) != {"numerator", "denominator"}:
            raise ValueError("projection cue source_fps is invalid")
        numerator = fps.get("numerator")
        denominator = fps.get("denominator")
        if (
            isinstance(numerator, bool) or not isinstance(numerator, int) or numerator <= 0
            or isinstance(denominator, bool) or not isinstance(denominator, int) or denominator <= 0
        ):
            raise ValueError("projection cue source_fps is invalid")
        start_frame = cue.get("source_start_frame")
        end_frame = cue.get("source_end_frame_exclusive")
        if (
            isinstance(start_frame, bool) or not isinstance(start_frame, int) or start_frame < 0
            or isinstance(end_frame, bool) or not isinstance(end_frame, int) or end_frame <= start_frame
        ):
            raise ValueError("projection cue frame range is invalid")
        key = (start_frame, end_frame, keyword_id)
        if previous_key is not None and key < previous_key:
            raise ValueError("projection cues must be deterministically ordered")
        previous_key = key
        state = cue.get("review_state")
        if state not in {"CONFIRMED", "REVIEW"}:
            raise ValueError("projection review_state is invalid")
        if mode == "CONFIRMED_ONLY" and state != "CONFIRMED":
            raise ValueError("confirmed-only projection cannot include review cues")
        confidence = cue.get("confidence")
        if confidence is not None and (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= float(confidence) <= 1
        ):
            raise ValueError("projection confidence is invalid")
        granularity = cue.get("timing_granularity")
        if granularity not in {"WORD", "SEGMENT_FALLBACK"}:
            raise ValueError("projection timing_granularity is invalid")
        if state == "CONFIRMED":
            observed_confirmed += 1
            if confidence is None or granularity != "WORD":
                raise ValueError("confirmed projection cue requires confidence and WORD timing")
        else:
            observed_review += 1
    if confirmed_count != observed_confirmed:
        raise ValueError("projection confirmed_count does not match projected confirmed cues")
    if mode == "WITH_REVIEW" and review_count != observed_review:
        raise ValueError("projection review_count does not match projected review cues")
    return dict(value)


def build_montage_semantic_audio_cues_projection(
    manifest: SpeechCueManifest,
    *,
    include_review: bool = False,
) -> dict[str, Any]:
    selected = [
        cue for cue in manifest.cues
        if cue.review_state is CueReviewState.CONFIRMED
        or (include_review and cue.review_state is CueReviewState.REVIEW)
    ]
    body: dict[str, Any] = {
        "projection_version": "1.0.0",
        "manifest_id": manifest.manifest_id,
        "manifest_sha256": manifest.to_dict()["manifest_sha256"],
        "keyword_profile_id": manifest.keyword_profile_id,
        "source_asset_id": manifest.source_asset_id,
        "confirmed_count": manifest.counts["confirmed"],
        "review_count": manifest.counts["review"],
        "projection_mode": "WITH_REVIEW" if include_review else "CONFIRMED_ONLY",
        "canonical_timeline": False,
        "auto_apply_authorized": False,
        "cues": [
            {
                "cue_id": cue.cue_id,
                "keyword_id": cue.keyword_id,
                "source_asset_id": manifest.source_asset_id,
                "source_fps": {
                    "numerator": manifest.source_frame_rate.numerator,
                    "denominator": manifest.source_frame_rate.denominator,
                },
                "source_start_frame": cue.source_start_frame,
                "source_end_frame_exclusive": cue.source_end_frame_exclusive,
                "confidence": cue.confidence,
                "review_state": cue.review_state.value,
                "timing_granularity": cue.timing_granularity.value,
            }
            for cue in selected
        ],
    }
    body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def load_keyword_profile(path: str | Path) -> KeywordProfile:
    source = Path(path).expanduser()
    if source.is_symlink():
        raise ProductError(
            "ERR_SPEECH_CUE_PROFILE_SYMLINK",
            "Keyword profile symlinks are not accepted",
            ProductErrorCategory.SECURITY,
        )
    source = source.resolve()
    if not source.is_file():
        raise ProductError(
            "ERR_SPEECH_CUE_PROFILE_NOT_FOUND",
            "Keyword profile must be an existing regular JSON file",
            ProductErrorCategory.VALIDATION,
        )
    size = source.stat().st_size
    if size <= 0 or size > _MAX_PROFILE_BYTES:
        raise ProductError(
            "ERR_SPEECH_CUE_PROFILE_SIZE",
            "Keyword profile size is outside the accepted bound",
            ProductErrorCategory.VALIDATION,
            details={"bytes": size, "max_bytes": _MAX_PROFILE_BYTES},
        )
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError("profile must be an object")
        return KeywordProfile.from_dict(value)
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_SPEECH_CUE_PROFILE_INVALID",
            "Keyword profile is not a valid bounded profile",
            ProductErrorCategory.VALIDATION,
        ) from exc


@dataclass(frozen=True, slots=True)
class SpeechCuePublication:
    output_directory: Path
    manifest_path: Path
    projection_path: Path
    report_path: Path
    manifest: SpeechCueManifest


class SpeechCuePublicationService:
    _REPORT_FIELDS = {
        "report_version", "ok", "source_asset_id", "manifest_id",
        "manifest_sha256", "projection_sha256", "keyword_profile_id",
        "confirmed_count", "review_count", "rejected_count",
        "projection_file", "manifest_file", "transcript_text_in_report",
        "host_path_in_report", "canonical_timeline",
        "auto_apply_authorized", "publication_complete",
    }

    @staticmethod
    def _read_object(path: Path, *, label: str) -> dict[str, Any]:
        if path.is_symlink() or not path.is_file():
            raise ProductError(
                "ERR_SPEECH_CUE_PUBLICATION_INCOMPLETE",
                f"{label} is missing or unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_SPEECH_CUE_PUBLICATION_INVALID",
                f"{label} is unreadable or invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not isinstance(value, dict):
            raise ProductError(
                "ERR_SPEECH_CUE_PUBLICATION_INVALID",
                f"{label} must be a JSON object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return value

    @classmethod
    def read_verified(cls, output_directory: str | Path) -> SpeechCuePublication:
        """Read a complete publication set and re-validate every binding.

        The report is written last and acts as the commit marker.  Consumers
        must use this reader (or equivalent checks) rather than trusting the
        presence of one of the private files independently.
        """
        output = Path(output_directory).expanduser().resolve()
        report_path = output / "speech-cue-report.json"
        report = cls._read_object(report_path, label="speech cue report")
        try:
            if set(report) != cls._REPORT_FIELDS:
                raise ValueError("report contains missing or unknown fields")
            if report["report_version"] != "1.0.0" or report["ok"] is not True:
                raise ValueError("report version/status is invalid")
            if report["publication_complete"] is not True:
                raise ValueError("publication is not complete")
            if (
                report["transcript_text_in_report"] is not False
                or report["host_path_in_report"] is not False
                or report["canonical_timeline"] is not False
                or report["auto_apply_authorized"] is not False
            ):
                raise ValueError("report authority/privacy flags are invalid")
            if report["manifest_file"] != "speech-cues.json":
                raise ValueError("manifest_file is invalid")
            if report["projection_file"] != "montage-semantic-audio-cues.json":
                raise ValueError("projection_file is invalid")
            for field in ("confirmed_count", "review_count", "rejected_count"):
                count = report[field]
                if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                    raise ValueError(f"{field} is invalid")
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_SPEECH_CUE_PUBLICATION_INVALID",
                "speech cue publication report failed validation",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

        manifest_path = output / report["manifest_file"]
        projection_path = output / report["projection_file"]
        manifest_document = cls._read_object(manifest_path, label="speech cue manifest")
        projection = cls._read_object(projection_path, label="semantic audio cue projection")
        try:
            manifest = SpeechCueManifest.from_dict(manifest_document)
            parsed_projection = parse_montage_semantic_audio_cues_projection(projection)
            manifest_sha = manifest_document["manifest_sha256"]
            projection_sha = parsed_projection["projection_sha256"]
            if report["manifest_sha256"] != manifest_sha:
                raise ValueError("report/manifest hash binding mismatch")
            if report["projection_sha256"] != projection_sha:
                raise ValueError("report/projection hash binding mismatch")
            if report["manifest_id"] != manifest.manifest_id:
                raise ValueError("report/manifest id binding mismatch")
            if report["source_asset_id"] != manifest.source_asset_id:
                raise ValueError("report/asset binding mismatch")
            if report["keyword_profile_id"] != manifest.keyword_profile_id:
                raise ValueError("report/profile binding mismatch")
            if parsed_projection["manifest_id"] != manifest.manifest_id:
                raise ValueError("projection/manifest id binding mismatch")
            if parsed_projection["manifest_sha256"] != manifest_sha:
                raise ValueError("projection/manifest hash binding mismatch")
            if parsed_projection["source_asset_id"] != manifest.source_asset_id:
                raise ValueError("projection/asset binding mismatch")
            if parsed_projection["keyword_profile_id"] != manifest.keyword_profile_id:
                raise ValueError("projection/profile binding mismatch")
            counts = manifest.counts
            if any(report[f"{name}_count"] != counts[name] for name in ("confirmed", "review", "rejected")):
                raise ValueError("report cue counts do not match manifest")

            by_id = {cue.cue_id: cue for cue in manifest.cues}
            for projected in parsed_projection["cues"]:
                cue = by_id.get(projected["cue_id"])
                if cue is None:
                    raise ValueError("projection references an unknown manifest cue")
                expected = {
                    "cue_id": cue.cue_id,
                    "keyword_id": cue.keyword_id,
                    "source_asset_id": manifest.source_asset_id,
                    "source_fps": {
                        "numerator": manifest.source_frame_rate.numerator,
                        "denominator": manifest.source_frame_rate.denominator,
                    },
                    "source_start_frame": cue.source_start_frame,
                    "source_end_frame_exclusive": cue.source_end_frame_exclusive,
                    "confidence": cue.confidence,
                    "review_state": cue.review_state.value,
                    "timing_granularity": cue.timing_granularity.value,
                }
                if dict(projected) != expected:
                    raise ValueError("projection cue does not match manifest evidence")
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_SPEECH_CUE_PUBLICATION_INVALID",
                "speech cue publication set failed integrity verification",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return SpeechCuePublication(output, manifest_path, projection_path, report_path, manifest)

    @staticmethod
    def publish(
        manifest: SpeechCueManifest,
        output_directory: str | Path,
        *,
        include_review_in_projection: bool = False,
    ) -> SpeechCuePublication:
        output = Path(output_directory).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        manifest_path = output / "speech-cues.json"
        projection_path = output / "montage-semantic-audio-cues.json"
        report_path = output / "speech-cue-report.json"
        manifest_document = manifest.to_dict()
        projection = build_montage_semantic_audio_cues_projection(
            manifest,
            include_review=include_review_in_projection,
        )
        AtomicJsonWriter.write(manifest_path, manifest_document)
        AtomicJsonWriter.write(projection_path, projection)
        AtomicJsonWriter.write(
            report_path,
            {
                "report_version": "1.0.0",
                "ok": True,
                "source_asset_id": manifest.source_asset_id,
                "manifest_id": manifest.manifest_id,
                "manifest_sha256": manifest_document["manifest_sha256"],
                "projection_sha256": projection["projection_sha256"],
                "keyword_profile_id": manifest.keyword_profile_id,
                "confirmed_count": manifest.counts["confirmed"],
                "review_count": manifest.counts["review"],
                "rejected_count": manifest.counts["rejected"],
                "projection_file": projection_path.name,
                "manifest_file": manifest_path.name,
                "transcript_text_in_report": False,
                "host_path_in_report": False,
                "canonical_timeline": False,
                "auto_apply_authorized": False,
                # Written last: this report is the publication-set commit marker.
                "publication_complete": True,
            },
        )
        # Do not return a publication that this process itself cannot re-read
        # as a complete, cross-bound set.
        return SpeechCuePublicationService.read_verified(output)
