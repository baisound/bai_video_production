from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .dbd_reasoning_policy_admission import contains_unsafe_reasoning_free_text
from .dbd_reasoning_dataset_manifest import (
    DatasetRowDisposition,
    DbDReasoningDatasetRightsManifest,
    admit_dbd_reasoning_dataset_rights_manifest,
)
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
RECORD_KIND = "DBD_REASONING_NARRATION_INTAKE_CANDIDATE"
INTAKE_STATE = "CANDIDATE_ONLY_NO_ADOPTION"
MAX_REDACTED_TRANSCRIPT_CHARS = 4_000
_CAND_RE = re.compile(r"^CAND-R2D[0-9A-HJKMNP-TV-Z]{23}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9._+-]{0,63}$")
_HASH_REF_RE = re.compile(r"^(media|speaker|human-review)://sha256/[0-9a-f]{64}$")


class NarrationRole(str, Enum):
    PLAY_BY_PLAY = "PLAY_BY_PLAY"
    ANALYSIS = "ANALYSIS"
    TACTICAL = "TACTICAL"
    REACTION = "REACTION"
    TRANSITION = "TRANSITION"
    FILLER = "FILLER"
    UNCERTAIN = "UNCERTAIN"


class NarrationDisposition(str, Enum):
    ELIGIBLE_CANDIDATE = "ELIGIBLE_CANDIDATE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"


_REJECT_CODES = frozenset({"RIGHTS_REJECTED", "CONSENT_REJECTED", "PII_OR_SECRET", "UNSUPPORTED_TACTICAL_CLAIM"})


def _positive_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _hash_ref(value: str, scheme: str, name: str) -> None:
    if not isinstance(value, str) or not _HASH_REF_RE.fullmatch(value) or not value.startswith(f"{scheme}://"):
        raise ValueError(f"{name} must be a body-free {scheme} sha256 reference")


def _redacted_text(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_REDACTED_TRANSCRIPT_CHARS:
        raise ValueError("redacted_transcript must be bounded non-empty text")
    if any(ord(char) < 32 and char not in "\n\t" or 0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError("redacted_transcript contains unsafe Unicode")
    if contains_unsafe_reasoning_free_text(value):
        raise ValueError("redacted_transcript failed the canonical DLP policy")


def _expected_disposition(role: NarrationRole, issue_codes: tuple[str, ...]) -> NarrationDisposition:
    if any(code in _REJECT_CODES for code in issue_codes):
        return NarrationDisposition.REJECTED
    if role is NarrationRole.UNCERTAIN or issue_codes:
        return NarrationDisposition.NEEDS_REVIEW
    return NarrationDisposition.ELIGIBLE_CANDIDATE


@dataclass(frozen=True, slots=True)
class DbDReasoningNarrationIntakeCandidate:
    segment_id: str
    rights_candidate_id: str
    rights_manifest_sha256: str
    match_id: str
    event_ids: tuple[str, ...]
    context_sha256: str
    source_video_ref: str
    source_audio_ref: str
    source_start_us: int
    source_end_us_exclusive: int
    speaker_ref: str
    asr_revision: int
    asr_sha256: str
    diarization_revision: int
    diarization_sha256: str
    original_transcript_sha256: str
    corrected_transcript_sha256: str
    redacted_transcript: str
    role: NarrationRole
    patch_version: str
    human_review_ref: str
    human_review_sha256: str
    issue_codes: tuple[str, ...]
    disposition: NarrationDisposition
    intake_state: str = INTAKE_STATE

    def __post_init__(self) -> None:
        validate_id(self.segment_id, IdKind.SEGMENT)
        validate_id(self.match_id, IdKind.GAME_MATCH)
        if not isinstance(self.rights_candidate_id, str) or not _CAND_RE.fullmatch(self.rights_candidate_id):
            raise ValueError("rights_candidate_id must use the CAND-R2D namespace")
        if not isinstance(self.event_ids, tuple) or self.event_ids != tuple(sorted(set(self.event_ids))) or not self.event_ids:
            raise ValueError("event_ids must be a non-empty sorted unique tuple")
        if len(self.event_ids) > 128:
            raise ValueError("event_ids exceed the intake ceiling")
        for event_id in self.event_ids:
            validate_id(event_id, IdKind.GAME_EVENT)
        for name in ("rights_manifest_sha256", "context_sha256", "asr_sha256", "diarization_sha256",
                     "original_transcript_sha256", "corrected_transcript_sha256", "human_review_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        for value, scheme, name in ((self.source_video_ref, "media", "source_video_ref"),
                                    (self.source_audio_ref, "media", "source_audio_ref"),
                                    (self.speaker_ref, "speaker", "speaker_ref"),
                                    (self.human_review_ref, "human-review", "human_review_ref")):
            _hash_ref(value, scheme, name)
        if self.human_review_ref != "human-review://" + self.human_review_sha256.replace(":", "/", 1):
            raise ValueError("human review reference and digest do not match")
        if isinstance(self.source_start_us, bool) or not isinstance(self.source_start_us, int) or self.source_start_us < 0:
            raise ValueError("source_start_us must be a non-negative integer")
        if isinstance(self.source_end_us_exclusive, bool) or not isinstance(self.source_end_us_exclusive, int) or self.source_end_us_exclusive <= self.source_start_us:
            raise ValueError("source range must be positive and end-exclusive")
        _positive_int(self.asr_revision, "asr_revision")
        _positive_int(self.diarization_revision, "diarization_revision")
        _redacted_text(self.redacted_transcript)
        if sha256_bytes(self.redacted_transcript.encode("utf-8")) != self.corrected_transcript_sha256:
            raise ValueError("redacted transcript and corrected transcript digest do not match")
        if not isinstance(self.role, NarrationRole):
            raise ValueError("role must be NarrationRole")
        if not isinstance(self.patch_version, str) or not _VERSION_RE.fullmatch(self.patch_version):
            raise ValueError("patch_version is invalid")
        if not isinstance(self.issue_codes, tuple) or self.issue_codes != tuple(sorted(set(self.issue_codes))):
            raise ValueError("issue_codes must be a sorted unique tuple")
        if len(self.issue_codes) > 32 or any(not _CODE_RE.fullmatch(code) for code in self.issue_codes):
            raise ValueError("issue_codes contain an invalid stable code")
        if not isinstance(self.disposition, NarrationDisposition) or self.disposition is not _expected_disposition(self.role, self.issue_codes):
            raise ValueError("disposition does not match role and issue codes")
        if self.intake_state != INTAKE_STATE:
            raise ValueError("R4B cannot grant Dataset adoption")

    def _body(self) -> dict[str, object]:
        return {"schema_version": SCHEMA_VERSION, "record_kind": RECORD_KIND,
            "segment_id": self.segment_id, "rights_candidate_id": self.rights_candidate_id,
            "rights_manifest_sha256": self.rights_manifest_sha256, "match_id": self.match_id,
            "event_ids": list(self.event_ids), "context_sha256": self.context_sha256,
            "source_video_ref": self.source_video_ref, "source_audio_ref": self.source_audio_ref,
            "source_start_us": self.source_start_us, "source_end_us_exclusive": self.source_end_us_exclusive,
            "speaker_ref": self.speaker_ref, "asr_revision": self.asr_revision, "asr_sha256": self.asr_sha256,
            "diarization_revision": self.diarization_revision, "diarization_sha256": self.diarization_sha256,
            "original_transcript_sha256": self.original_transcript_sha256,
            "corrected_transcript_sha256": self.corrected_transcript_sha256,
            "redacted_transcript": self.redacted_transcript, "role": self.role.value,
            "patch_version": self.patch_version, "human_review_ref": self.human_review_ref,
            "human_review_sha256": self.human_review_sha256, "issue_codes": list(self.issue_codes),
            "disposition": self.disposition.value, "intake_state": self.intake_state}

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "intake_sha256": sha256_bytes(canonical_json_bytes(body))}


def admit_dbd_reasoning_narration_intake(record: Mapping[str, Any]) -> DbDReasoningNarrationIntakeCandidate:
    if not isinstance(record, Mapping):
        raise ValueError("intake record must be a mapping")
    expected = set(DbDReasoningNarrationIntakeCandidate.__dataclass_fields__) | {"schema_version", "record_kind", "intake_sha256"}
    if set(record) != expected or record.get("schema_version") != SCHEMA_VERSION or record.get("record_kind") != RECORD_KIND:
        raise ValueError("intake record shape or version is invalid")
    values = {key: record[key] for key in DbDReasoningNarrationIntakeCandidate.__dataclass_fields__}
    if not isinstance(values["event_ids"], list) or not isinstance(values["issue_codes"], list):
        raise ValueError("intake collections must be arrays")
    values["event_ids"] = tuple(values["event_ids"])
    values["issue_codes"] = tuple(values["issue_codes"])
    values["role"] = NarrationRole(values["role"])
    values["disposition"] = NarrationDisposition(values["disposition"])
    candidate = DbDReasoningNarrationIntakeCandidate(**values)
    if candidate.to_dict() != dict(record):
        raise ValueError("intake checksum or canonical representation is invalid")
    return candidate


def validate_narration_intake_rights(
    candidate: DbDReasoningNarrationIntakeCandidate,
    manifest: DbDReasoningDatasetRightsManifest,
) -> DbDReasoningNarrationIntakeCandidate:
    if not isinstance(candidate, DbDReasoningNarrationIntakeCandidate):
        raise ValueError("candidate type is invalid")
    candidate = admit_dbd_reasoning_narration_intake(candidate.to_dict())
    if not isinstance(manifest, DbDReasoningDatasetRightsManifest):
        raise ValueError("rights manifest type is invalid")
    manifest = admit_dbd_reasoning_dataset_rights_manifest(manifest.to_dict())
    if manifest.to_dict()["rights_manifest_sha256"] != candidate.rights_manifest_sha256:
        raise ValueError("rights manifest digest crossing")
    matches = tuple(entry for entry in manifest.entries if entry.candidate_id == candidate.rights_candidate_id)
    if len(matches) != 1:
        raise ValueError("rights candidate membership is invalid")
    entry = matches[0]
    if entry.disposition is not DatasetRowDisposition.ELIGIBLE_CANDIDATE:
        raise ValueError("rights candidate is not eligible")
    if entry.match_id != candidate.match_id or entry.source_ref != candidate.source_video_ref:
        raise ValueError("rights candidate coordinate crossing")
    if entry.human_review_sha256 != candidate.human_review_sha256 or entry.human_review_ref != candidate.human_review_ref:
        raise ValueError("Human review coordinate crossing")
    return candidate


__all__ = ["DbDReasoningNarrationIntakeCandidate", "INTAKE_STATE", "NarrationDisposition",
           "NarrationRole", "admit_dbd_reasoning_narration_intake", "validate_narration_intake_rights"]
