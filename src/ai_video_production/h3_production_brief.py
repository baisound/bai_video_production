from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re

from .ids import IdKind, validate_id


class H3ReferenceKind(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class H3ReferenceRole(str, Enum):
    FIRST_FRAME = "FIRST_FRAME"
    LAST_FRAME = "LAST_FRAME"
    KEYFRAME = "KEYFRAME"
    GENERAL_REFERENCE = "GENERAL_REFERENCE"


class H3VisibleRetention(str, Enum):
    FULLY_PRESERVED = "fully_preserved"
    PARTIALLY_PRESERVED = "partially_preserved"
    ATTRIBUTE_TRANSFER = "attribute_transfer"
    WEAK_REFERENCE = "weak_reference"


class H3AudioRetention(str, Enum):
    FULLY_COPY = "fully_copy"
    PARTIALLY_COPY = "partially_copy"
    REFERENCE = "reference"
    WEAK_REFERENCE = "weak_reference"


class H3BriefTemplate(str, Enum):
    T2VA = "T2VA"
    FULL_REFERENCE = "FULL_REFERENCE"


class H3DurationTier(str, Enum):
    STANDARD_1_15 = "STANDARD_1_15"
    EXPERIMENTAL_16_45 = "EXPERIMENTAL_16_45"


@dataclass(frozen=True, slots=True)
class H3ReferenceBinding:
    asset_id: str
    kind: H3ReferenceKind
    role: H3ReferenceRole = H3ReferenceRole.GENERAL_REFERENCE
    purpose: str = "reference"
    retention: H3VisibleRetention | H3AudioRetention | None = None

    def __post_init__(self) -> None:
        validate_id(self.asset_id, IdKind.ASSET)
        if not self.purpose.strip() or "\x00" in self.purpose:
            raise ValueError("purpose must be non-empty and contain no NUL")
        if re.search(r"<(?:Picture|Video|Audio)\s+[1-9][0-9]*>", self.purpose, re.IGNORECASE):
            raise ValueError("purpose must not inject reserved H3 reference tags")
        if self.role in {H3ReferenceRole.FIRST_FRAME, H3ReferenceRole.LAST_FRAME} and self.kind is not H3ReferenceKind.IMAGE:
            raise ValueError("FIRST_FRAME/LAST_FRAME roles require IMAGE references")
        if self.kind is H3ReferenceKind.AUDIO and isinstance(self.retention, H3VisibleRetention):
            raise ValueError("audio reference cannot use visible retention marker")
        if self.kind is not H3ReferenceKind.AUDIO and isinstance(self.retention, H3AudioRetention):
            raise ValueError("visible reference cannot use audio retention marker")


@dataclass(frozen=True, slots=True)
class H3Shot:
    index: int
    description: str
    start_ms: int | None = None
    camera_instruction: str = "Static Shot; no pan, no push-in, no reframing."
    observable_end_state: str = ""

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("shot index must be positive")
        if not self.description.strip() or "\x00" in self.description:
            raise ValueError("shot description must be non-empty and contain no NUL")
        if self.index == 1 and self.start_ms not in (None, 0):
            raise ValueError("shot 1 must start at zero/implicit")
        if self.index > 1 and (self.start_ms is None or self.start_ms <= 0):
            raise ValueError("later shots require a positive start_ms")
        for text in (self.camera_instruction, self.observable_end_state):
            if "\x00" in text:
                raise ValueError("shot fields cannot contain NUL")


@dataclass(frozen=True, slots=True)
class H3ProductionBriefPlan:
    template: H3BriefTemplate
    text: str
    sha256: str
    reference_tags: tuple[str, ...]
    target_duration_seconds: int
    target_aspect_ratio: str
    duration_tier: H3DurationTier

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "template": self.template.value,
            "text_sha256": self.sha256,
            "reference_tags": list(self.reference_tags),
            "target_duration_seconds": self.target_duration_seconds,
            "target_aspect_ratio": self.target_aspect_ratio,
            "duration_tier": self.duration_tier.value,
        }


class H3ProductionBriefBuilder:
    """Deterministic serializer for a structured MiniMax H3 production brief.

    This is an independent product implementation inspired by reviewed public
    prompt-planning material. It does not bundle/copy the external system prompt
    and intentionally requires upstream reasoning to provide the semantic shot
    content. The builder owns stable reference ordering, hard constraints and
    serialization only.
    """

    _ASPECT = re.compile(r"^[1-9][0-9]{0,3}:[1-9][0-9]{0,3}$")
    _RESERVED_TAG = re.compile(r"<(?:Picture|Video|Audio)\s+[1-9][0-9]*>", re.IGNORECASE)

    @classmethod
    def _assert_no_reserved_tags(cls, *values: str) -> None:
        if any(cls._RESERVED_TAG.search(value) for value in values):
            raise ValueError("free-text brief fields must not inject reserved H3 reference tags")

    @staticmethod
    def _tag(kind: H3ReferenceKind, ordinal: int) -> str:
        prefix = {H3ReferenceKind.IMAGE: "Picture", H3ReferenceKind.VIDEO: "Video", H3ReferenceKind.AUDIO: "Audio"}[kind]
        return f"<{prefix} {ordinal}>"

    @classmethod
    def _tagged_references(cls, references: tuple[H3ReferenceBinding, ...]) -> tuple[tuple[H3ReferenceBinding, str], ...]:
        counters = {kind: 0 for kind in H3ReferenceKind}
        tagged: list[tuple[H3ReferenceBinding, str]] = []
        for ref in references:
            counters[ref.kind] += 1
            tagged.append((ref, cls._tag(ref.kind, counters[ref.kind])))
        return tuple(tagged)

    @staticmethod
    def _validate_shots(shots: tuple[H3Shot, ...], duration_seconds: int) -> None:
        if not shots:
            raise ValueError("at least one shot is required")
        if [shot.index for shot in shots] != list(range(1, len(shots) + 1)):
            raise ValueError("shots must be sequentially numbered from 1")
        previous = -1
        max_ms = duration_seconds * 1000
        for shot in shots:
            start = 0 if shot.index == 1 else int(shot.start_ms or 0)
            if start <= previous:
                raise ValueError("shot start times must be strictly increasing")
            if start >= max_ms and shot.index > 1:
                raise ValueError("shot start time must fall within target duration")
            previous = start

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        minutes, remainder = divmod(milliseconds, 60_000)
        seconds, millis = divmod(remainder, 1000)
        return f"{minutes:02d}:{seconds:02d}.{millis:03d}"

    @classmethod
    def build(
        cls,
        *,
        user_intent: str,
        target_duration_seconds: int,
        target_aspect_ratio: str,
        references: tuple[H3ReferenceBinding, ...] = (),
        subject_definitions: tuple[str, ...] = (),
        retention_notes: tuple[str, ...] = (),
        shots: tuple[H3Shot, ...],
        overall_soundscape: str = "N/A",
        non_diegetic_music: str = "N/A",
    ) -> H3ProductionBriefPlan:
        if not user_intent.strip() or "\x00" in user_intent:
            raise ValueError("user_intent must be non-empty and contain no NUL")
        if target_duration_seconds < 1 or target_duration_seconds > 45:
            raise ValueError("target_duration_seconds must be in 1..45 for the TASK-004 H3 contract")
        if not cls._ASPECT.fullmatch(target_aspect_ratio):
            raise ValueError("target_aspect_ratio must be WIDTH:HEIGHT")
        cls._validate_shots(shots, target_duration_seconds)
        if references and all(ref.kind is H3ReferenceKind.AUDIO for ref in references):
            raise ValueError("audio-only full-reference request is not supported by the H3 reference contract")
        if any("\x00" in text for text in (*subject_definitions, *retention_notes, overall_soundscape, non_diegetic_music)):
            raise ValueError("brief content cannot contain NUL")
        cls._assert_no_reserved_tags(user_intent, *subject_definitions, *retention_notes, overall_soundscape, non_diegetic_music, *(shot.description for shot in shots), *(shot.camera_instruction for shot in shots), *(shot.observable_end_state for shot in shots))

        first_frames = [ref for ref in references if ref.role is H3ReferenceRole.FIRST_FRAME]
        last_frames = [ref for ref in references if ref.role is H3ReferenceRole.LAST_FRAME]
        if len(first_frames) > 1 or len(last_frames) > 1:
            raise ValueError("at most one FIRST_FRAME and one LAST_FRAME reference are allowed")
        if bool(first_frames) != bool(last_frames):
            raise ValueError("FIRST_FRAME and LAST_FRAME roles must be supplied as a pair")

        image_count = sum(ref.kind is H3ReferenceKind.IMAGE for ref in references)
        video_count = sum(ref.kind is H3ReferenceKind.VIDEO for ref in references)
        audio_count = sum(ref.kind is H3ReferenceKind.AUDIO for ref in references)
        if image_count > 9 or video_count > 3 or audio_count > 3:
            raise ValueError("H3 reference limits are 9 images, 3 videos and 3 standalone audio references")
        if len(references) > 15:
            raise ValueError("H3 reference count exceeds the TASK-004 bridge limit")
        tagged = cls._tagged_references(references)
        tags = tuple(tag for _ref, tag in tagged)
        template = H3BriefTemplate.FULL_REFERENCE if references else H3BriefTemplate.T2VA
        shot_parts: list[str] = []
        for shot in shots:
            prefix = f"[Shot {shot.index}]"
            if shot.index > 1:
                prefix += f" At {cls._format_time(int(shot.start_ms or 0))},"
            body = f"{prefix} {shot.description.strip()} Camera: {shot.camera_instruction.strip()}"
            if shot.observable_end_state.strip():
                body += f" End state: {shot.observable_end_state.strip()}"
            shot_parts.append(body)
        timeline = " ".join(shot_parts)
        hard_constraints = f"Target duration is exactly {target_duration_seconds}s; target aspect ratio is {target_aspect_ratio}."

        if template is H3BriefTemplate.T2VA:
            text = (
                f"integrated_multimodal_description: {hard_constraints} {user_intent.strip()} {timeline}\n"
                f"overall_soundscape: {overall_soundscape.strip()}\n"
                f"non_diegetic_music: {non_diegetic_music.strip()}"
            )
        else:
            definitions: list[str] = []
            for ref, tag in tagged:
                definitions.append(f"{tag}: role={ref.role.value}; purpose={ref.purpose.strip()}.")
            definitions.extend(text.strip() for text in subject_definitions if text.strip())
            retention: list[str] = []
            for ref, tag in tagged:
                marker = ref.retention.value if ref.retention is not None else "unspecified"
                retention.append(f"{tag}: {marker}.")
            retention.extend(text.strip() for text in retention_notes if text.strip())
            text = (
                "subject_definitions: " + " ".join(definitions) + "\n"
                "summary: " + hard_constraints + " " + user_intent.strip() + "\n"
                "retention_analysis: " + " ".join(retention) + "\n"
                "detailed_description: " + timeline + "\n"
                "overall_soundscape: " + overall_soundscape.strip() + "\n"
                "non_diegetic_music: " + non_diegetic_music.strip()
            )
        digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        tier = H3DurationTier.STANDARD_1_15 if target_duration_seconds <= 15 else H3DurationTier.EXPERIMENTAL_16_45
        return H3ProductionBriefPlan(template, text, digest, tags, target_duration_seconds, target_aspect_ratio, tier)
