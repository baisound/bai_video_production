"""Deterministic style/emotion reference selection for local Owner Voice."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
from typing import Iterable

_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

@dataclass(frozen=True, slots=True)
class VoiceReferenceCandidate:
    candidate_id: str
    wav_path: Path
    transcript_path: Path
    content_sha256: str
    duration_samples: int
    style_id: str
    emotion_id: str
    quality_pass: bool
    owner_approved: bool
    transcript_verified: bool

    def __post_init__(self) -> None:
        if not self.candidate_id or len(self.candidate_id) > 200:
            raise ValueError("candidate_id is invalid")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.content_sha256):
            raise ValueError("content_sha256 is invalid")
        if not _ID.fullmatch(self.style_id) or not _ID.fullmatch(self.emotion_id):
            raise ValueError("style/emotion is invalid")
        if not 3 * 48_000 <= self.duration_samples <= 15 * 48_000:
            raise ValueError("reference duration must be 3-15 seconds")
        for name in ("quality_pass", "owner_approved", "transcript_verified"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")

    @property
    def eligible(self) -> bool:
        return self.quality_pass and self.owner_approved and self.transcript_verified

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "wav_path": str(self.wav_path),
            "transcript_path": str(self.transcript_path),
            "content_sha256": self.content_sha256,
            "duration_samples": self.duration_samples,
            "style_id": self.style_id,
            "emotion_id": self.emotion_id,
            "quality_pass": self.quality_pass,
            "owner_approved": self.owner_approved,
            "transcript_verified": self.transcript_verified,
        }


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return 'sha256:'+h.hexdigest()


def select_reference(
    candidates: Iterable[VoiceReferenceCandidate], *, style_id: str, emotion_id: str,
    allow_neutral_fallback: bool = False,
) -> VoiceReferenceCandidate:
    if not _ID.fullmatch(style_id) or not _ID.fullmatch(emotion_id):
        raise ValueError("style/emotion is invalid")
    eligible=[x for x in candidates if x.eligible]
    exact=[x for x in eligible if x.style_id==style_id and x.emotion_id==emotion_id]
    pool=exact
    if not pool and allow_neutral_fallback:
        pool=[x for x in eligible if x.style_id=="NORMAL" and x.emotion_id=="NORMAL"]
    if not pool:
        raise ValueError("NO_APPROVED_REFERENCE")
    # Prefer an 8-second reference, then stable candidate id.
    return min(pool, key=lambda x:(abs(x.duration_samples-8*48_000), x.candidate_id))


def build_reference_manifest(candidates: Iterable[VoiceReferenceCandidate]) -> dict[str, object]:
    values=tuple(x for x in candidates if x.eligible)
    ordered=sorted(values, key=lambda x:(x.style_id,x.emotion_id,abs(x.duration_samples-8*48_000),x.candidate_id))
    return {"manifest_version":"1.0.0","sample_rate_hz":48_000,"candidates":[x.to_dict() for x in ordered]}

__all__=["VoiceReferenceCandidate","build_reference_manifest","select_reference","sha256_file"]
