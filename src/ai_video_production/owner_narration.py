"""TASK-014 owner narration planning / paid-execution admission foundation.

The module never contacts a provider. It keeps the private cloned voice identifier
out of public reports and requires an explicit paid-execution gate before a higher
layer may call the existing ElevenLabs adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes
from .subtitle_workspace import NarrationCue


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _digest_private(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


class NarrationGenerationMode(str, Enum):
    PREVIEW = "PREVIEW"
    FULL_RENDER = "FULL_RENDER"


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    voice_profile_id: str
    provider_family: str
    credential_ref: str
    private_voice_id: str
    ownership_verified: bool
    fine_tuned: bool
    approved_languages: tuple[str, ...]
    approved_model_ids: tuple[str, ...]
    consent_subject_ref: str
    consent_scope: str
    revoked: bool = False

    def __post_init__(self) -> None:
        _id(self.voice_profile_id, "voice_profile_id")
        _id(self.provider_family, "provider_family")
        if not self.credential_ref.startswith("credential://"):
            raise ValueError("credential_ref must be an indirect credential:// reference")
        if not self.private_voice_id.strip() or len(self.private_voice_id) > 200 or "\x00" in self.private_voice_id:
            raise ValueError("private_voice_id is invalid")
        _id(self.consent_subject_ref, "consent_subject_ref")
        if not self.consent_scope.strip() or len(self.consent_scope) > 1000:
            raise ValueError("consent_scope is invalid")
        if not self.approved_languages or not self.approved_model_ids:
            raise ValueError("approved language/model sets must not be empty")
        for value in self.approved_languages + self.approved_model_ids:
            _id(value, "approved value")

    @property
    def profile_digest(self) -> str:
        private_identity = {
            "voice_profile_id": self.voice_profile_id,
            "provider_family": self.provider_family,
            "credential_ref": self.credential_ref,
            "private_voice_id_digest": _digest_private(self.private_voice_id),
            "ownership_verified": self.ownership_verified,
            "fine_tuned": self.fine_tuned,
            "approved_languages": list(self.approved_languages),
            "approved_model_ids": list(self.approved_model_ids),
            "consent_subject_ref": self.consent_subject_ref,
            "consent_scope": self.consent_scope,
            "revoked": self.revoked,
        }
        return sha256_bytes(canonical_json_bytes(private_identity))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "voice_profile_id": self.voice_profile_id,
            "provider_family": self.provider_family,
            "profile_digest": self.profile_digest,
            "ownership_verified": self.ownership_verified,
            "fine_tuned": self.fine_tuned,
            "approved_languages": list(self.approved_languages),
            "approved_model_ids": list(self.approved_model_ids),
            "revoked": self.revoked,
            "credential_ref_persisted": False,
            "raw_voice_id_persisted": False,
        }


@dataclass(frozen=True, slots=True)
class NarrationScript:
    script_id: str
    text: str
    approved_by: str

    def __post_init__(self) -> None:
        _id(self.script_id, "script_id")
        _id(self.approved_by, "approved_by")
        normalized = self.text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized or len(normalized) > 200_000 or "\x00" in normalized:
            raise ValueError("script text is invalid")
        object.__setattr__(self, "text", normalized)

    @property
    def script_sha256(self) -> str:
        return sha256_bytes(self.text.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class NarrationChunk:
    chunk_id: str
    text: str
    text_sha256: str
    order: int

    def __post_init__(self) -> None:
        _id(self.chunk_id, "chunk_id")
        if self.order < 1:
            raise ValueError("chunk order must be >= 1")
        if not self.text.strip():
            raise ValueError("chunk text must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {"chunk_id": self.chunk_id, "text_sha256": self.text_sha256, "order": self.order, "text_persisted": False}


@dataclass(frozen=True, slots=True)
class NarrationGenerationPlan:
    plan_id: str
    mode: NarrationGenerationMode
    script_id: str
    script_sha256: str
    voice_profile_id: str
    voice_profile_digest: str
    model_id: str
    language_code: str
    chunks: tuple[NarrationChunk, ...]

    def to_dict(self) -> dict[str, Any]:
        body = {
            "plan_version": "1.0.0",
            "task_owner": "TASK-014",
            "plan_id": self.plan_id,
            "mode": self.mode.value,
            "script_id": self.script_id,
            "script_sha256": self.script_sha256,
            "voice_profile_id": self.voice_profile_id,
            "voice_profile_digest": self.voice_profile_digest,
            "model_id": self.model_id,
            "language_code": self.language_code,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "paid_provider_call_started": False,
            "raw_voice_id_persisted": False,
        }
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class NarrationPlanningService:
    @staticmethod
    def _chunk_text(text: str, *, max_chars: int) -> tuple[str, ...]:
        if not 100 <= max_chars <= 20_000:
            raise ValueError("max_chars must be 100..20000")
        paragraphs = [item.strip() for item in text.split("\n") if item.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(paragraph) > max_chars:
                # Bounded fallback for a single unusually long paragraph. This is
                # deterministic planning only; provider execution remains gated.
                if current:
                    chunks.append(current)
                    current = ""
                for start in range(0, len(paragraph), max_chars):
                    chunks.append(paragraph[start : start + max_chars])
                continue
            proposed = paragraph if not current else current + "\n" + paragraph
            if len(proposed) <= max_chars:
                current = proposed
            else:
                chunks.append(current)
                current = paragraph
        if current:
            chunks.append(current)
        return tuple(chunks)

    @classmethod
    def compile(
        cls,
        script: NarrationScript,
        profile: VoiceProfile,
        *,
        mode: NarrationGenerationMode,
        model_id: str,
        language_code: str,
        max_chars_per_chunk: int = 3000,
    ) -> NarrationGenerationPlan:
        _id(model_id, "model_id")
        _id(language_code, "language_code")
        if profile.revoked:
            raise ProductError("ERR_VOICE_PROFILE_REVOKED", "Voice Profile is revoked for new generation", ProductErrorCategory.AUTHORIZATION)
        if not profile.ownership_verified or not profile.fine_tuned:
            raise ProductError("ERR_VOICE_PROFILE_NOT_VERIFIED", "Voice Profile is not verified/fine-tuned for generation", ProductErrorCategory.AUTHORIZATION)
        if language_code not in profile.approved_languages:
            raise ProductError("ERR_VOICE_LANGUAGE_NOT_APPROVED", "Narration language is not approved by the Voice Profile", ProductErrorCategory.AUTHORIZATION)
        if model_id not in profile.approved_model_ids:
            raise ProductError("ERR_VOICE_MODEL_NOT_APPROVED", "Narration model is not approved by the Voice Profile", ProductErrorCategory.AUTHORIZATION)
        chunks = tuple(
            NarrationChunk(
                chunk_id=f"narration-chunk-{index:04d}",
                text=text,
                text_sha256=sha256_bytes(text.encode("utf-8")),
                order=index,
            )
            for index, text in enumerate(cls._chunk_text(script.text, max_chars=max_chars_per_chunk), 1)
        )
        seed = canonical_json_bytes({
            "script": script.script_sha256,
            "voice": profile.profile_digest,
            "mode": mode.value,
            "model": model_id,
            "language": language_code,
            "chunks": [item.text_sha256 for item in chunks],
        })
        plan_id = "narration-plan-" + sha256_bytes(seed).split(":", 1)[1][:16]
        return NarrationGenerationPlan(
            plan_id,
            mode,
            script.script_id,
            script.script_sha256,
            profile.voice_profile_id,
            profile.profile_digest,
            model_id,
            language_code,
            chunks,
        )

    @staticmethod
    def require_paid_execution_authorized(
        plan: NarrationGenerationPlan,
        *,
        explicit_paid_execution_authorization: bool,
    ) -> None:
        if explicit_paid_execution_authorization:
            return
        raise ProductError(
            "ERR_NARRATION_PAID_EXECUTION_NOT_AUTHORIZED",
            "Narration provider execution requires explicit paid authorization",
            ProductErrorCategory.AUTHORIZATION,
            details={"plan_id": plan.plan_id, "mode": plan.mode.value},
        )


@dataclass(frozen=True, slots=True)
class CharacterAlignment:
    character: str
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        if len(self.character) != 1:
            raise ValueError("alignment character must contain exactly one character")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("alignment timing is invalid")


class NarrationAlignmentService:
    @staticmethod
    def to_narration_cues(
        text: str,
        alignment: Iterable[CharacterAlignment],
        *,
        max_gap_ms: int = 700,
    ) -> tuple[NarrationCue, ...]:
        if max_gap_ms < 0:
            raise ValueError("max_gap_ms must be non-negative")
        rows = tuple(alignment)
        if "".join(item.character for item in rows) != text:
            raise ProductError("ERR_NARRATION_ALIGNMENT_TEXT_MISMATCH", "Alignment characters do not match narration text", ProductErrorCategory.DATA_INTEGRITY)
        if not rows:
            return ()
        cues: list[NarrationCue] = []
        start = rows[0].start_ms
        current_text = rows[0].character
        previous_end = rows[0].end_ms
        for item in rows[1:]:
            boundary = item.start_ms - previous_end > max_gap_ms or current_text.endswith(("。", "！", "？", "\n"))
            if boundary:
                cues.append(NarrationCue(start, previous_end, current_text))
                start = item.start_ms
                current_text = item.character
            else:
                current_text += item.character
            previous_end = item.end_ms
        cues.append(NarrationCue(start, previous_end, current_text))
        return tuple(cues)
