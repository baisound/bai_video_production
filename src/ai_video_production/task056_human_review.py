"""Durable Human review for TASK-056 speech cues.

Detection evidence remains immutable.  This module stores a separate Project-
bound Human decision record and never grants Timeline, Resolve, or auto-apply
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
import secrets
from typing import Any, Callable

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .semantic_audio_cues import CueReviewState, SpeechCueHit, SpeechCueManifest
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


_MAX_STORE_BYTES = 2 * 1024 * 1024
_ACTOR_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_DECISION_ID = re.compile(r"SCD-[0-9a-f]{24}")
_UTC_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")
TokenFactory = Callable[[], str]
Clock = Callable[[], str]


class SpeechCueHumanDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class SpeechCueHumanDecisionRecord:
    decision_id: str
    cue_id: str
    cue_sha256: str
    decision: SpeechCueHumanDecision
    actor_id: str
    decided_at: str

    def __post_init__(self) -> None:
        if not _DECISION_ID.fullmatch(self.decision_id):
            raise ValueError("speech cue decision_id is invalid")
        if not re.fullmatch(r"CUE-[0-9a-f]{24}", self.cue_id):
            raise ValueError("speech cue decision cue_id is invalid")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.cue_sha256):
            raise ValueError("speech cue decision hash is invalid")
        if not _ACTOR_ID.fullmatch(self.actor_id):
            raise ValueError("speech cue decision actor_id is invalid")
        if not _UTC_TIME.fullmatch(self.decided_at):
            raise ValueError("speech cue decision timestamp is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "cue_id": self.cue_id,
            "cue_sha256": self.cue_sha256,
            "decision": self.decision.value,
            "actor_id": self.actor_id,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SpeechCueHumanDecisionRecord":
        if set(value) != {
            "decision_id", "cue_id", "cue_sha256", "decision", "actor_id", "decided_at"
        }:
            raise ValueError("speech cue Human decision contains unknown fields")
        return cls(
            decision_id=value["decision_id"],
            cue_id=value["cue_id"],
            cue_sha256=value["cue_sha256"],
            decision=SpeechCueHumanDecision(value["decision"]),
            actor_id=value["actor_id"],
            decided_at=value["decided_at"],
        )


def _cue_sha256(cue: SpeechCueHit) -> str:
    return sha256_bytes(canonical_json_bytes(cue.to_dict()))


def _decision_id(
    *, manifest_sha256: str, cue_id: str, decision: SpeechCueHumanDecision,
    actor_id: str, decided_at: str,
) -> str:
    seed = {
        "manifest_sha256": manifest_sha256,
        "cue_id": cue_id,
        "decision": decision.value,
        "actor_id": actor_id,
        "decided_at": decided_at,
    }
    return "SCD-" + sha256_bytes(canonical_json_bytes(seed))[7:31]


class SpeechCueHumanReviewStore:
    """CAS-safe store with one immutable decision per REVIEW cue."""

    def __init__(self, *, output_directory: str | Path, project_id: str) -> None:
        self.output_directory = Path(output_directory)
        self.project_id = project_id

    def path_for(self, manifest: SpeechCueManifest) -> Path:
        if self.output_directory.is_symlink() or (
            self.output_directory.exists() and not self.output_directory.is_dir()
        ):
            raise ProductError(
                "ERR_TASK056_HUMAN_REVIEW_SCOPE_INVALID",
                "Speech cue output scope is no longer a safe directory",
                ProductErrorCategory.SECURITY,
            )
        review_root = self.output_directory / "human-review"
        if review_root.is_symlink() or (review_root.exists() and not review_root.is_dir()):
            raise ProductError(
                "ERR_TASK056_HUMAN_REVIEW_SCOPE_INVALID",
                "Speech cue Human review scope must be a regular directory",
                ProductErrorCategory.SECURITY,
            )
        return review_root / f"{manifest.manifest_id}.json"

    def _document(
        self,
        manifest: SpeechCueManifest,
        records: tuple[SpeechCueHumanDecisionRecord, ...],
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "review_store_version": "1.0.0",
            "task_owner": "TASK-056",
            "project_id": self.project_id,
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.to_dict()["manifest_sha256"],
            "source_asset_id": manifest.source_asset_id,
            "revision": len(records),
            "decisions": [record.to_dict() for record in records],
            "confirmation_tokens_persisted": False,
            "transcript_text_persisted": False,
            "host_paths_persisted": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }
        body["review_store_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    def _validate(
        self,
        value: dict[str, Any],
        manifest: SpeechCueManifest,
    ) -> tuple[SpeechCueHumanDecisionRecord, ...]:
        expected_fields = {
            "review_store_version", "task_owner", "project_id", "manifest_id",
            "manifest_sha256", "source_asset_id", "revision", "decisions",
            "confirmation_tokens_persisted", "transcript_text_persisted",
            "host_paths_persisted", "canonical_timeline", "auto_apply_authorized",
            "review_store_sha256",
        }
        if set(value) != expected_fields:
            raise ValueError("speech cue Human review store contains unknown fields")
        claimed = value["review_store_sha256"]
        body = dict(value)
        body.pop("review_store_sha256")
        if claimed != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("speech cue Human review store hash mismatch")
        if (
            value["review_store_version"] != "1.0.0"
            or value["task_owner"] != "TASK-056"
            or value["project_id"] != self.project_id
            or value["manifest_id"] != manifest.manifest_id
            or value["manifest_sha256"] != manifest.to_dict()["manifest_sha256"]
            or value["source_asset_id"] != manifest.source_asset_id
        ):
            raise ValueError("speech cue Human review store binding mismatch")
        for field in (
            "confirmation_tokens_persisted", "transcript_text_persisted",
            "host_paths_persisted", "canonical_timeline", "auto_apply_authorized",
        ):
            if value[field] is not False:
                raise ValueError("speech cue Human review store boundary is invalid")
        raw_records = value["decisions"]
        if not isinstance(raw_records, list) or len(raw_records) > 10_000:
            raise ValueError("speech cue Human review decisions are invalid")
        if value["revision"] != len(raw_records):
            raise ValueError("speech cue Human review revision mismatch")
        cues = {cue.cue_id: cue for cue in manifest.cues}
        records: list[SpeechCueHumanDecisionRecord] = []
        seen: set[str] = set()
        for raw in raw_records:
            if not isinstance(raw, dict):
                raise ValueError("speech cue Human decision must be an object")
            record = SpeechCueHumanDecisionRecord.from_dict(raw)
            cue = cues.get(record.cue_id)
            if cue is None or cue.review_state is not CueReviewState.REVIEW:
                raise ValueError("speech cue Human decision does not bind a REVIEW cue")
            if record.cue_sha256 != _cue_sha256(cue) or record.cue_id in seen:
                raise ValueError("speech cue Human decision cue binding is invalid")
            seen.add(record.cue_id)
            records.append(record)
        return tuple(records)

    def load(
        self,
        manifest: SpeechCueManifest,
    ) -> tuple[dict[str, Any], tuple[SpeechCueHumanDecisionRecord, ...]]:
        path = self.path_for(manifest)
        if path.is_symlink():
            raise ProductError(
                "ERR_TASK056_HUMAN_REVIEW_FILE_INVALID",
                "Speech cue Human review store must be a regular non-symlink file",
                ProductErrorCategory.SECURITY,
            )
        if not path.exists():
            document = self._document(manifest, ())
            return document, ()
        if not path.is_file():
            raise ProductError(
                "ERR_TASK056_HUMAN_REVIEW_FILE_INVALID",
                "Speech cue Human review store must be a regular non-symlink file",
                ProductErrorCategory.SECURITY,
            )
        size = path.stat().st_size
        if size <= 0 or size > _MAX_STORE_BYTES:
            raise ProductError(
                "ERR_TASK056_HUMAN_REVIEW_SIZE_INVALID",
                "Speech cue Human review store size is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("review store root must be an object")
            records = self._validate(value, manifest)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK056_HUMAN_REVIEW_INVALID",
                "Speech cue Human review store failed validation",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return value, records

    def append(
        self,
        manifest: SpeechCueManifest,
        record: SpeechCueHumanDecisionRecord,
    ) -> dict[str, Any]:
        path = self.path_for(manifest)
        with exclusive_file_update_lock(path):
            _, records = self.load(manifest)
            if any(item.cue_id == record.cue_id for item in records):
                raise ProductError(
                    "ERR_TASK056_HUMAN_DECISION_ALREADY_RECORDED",
                    "Speech cue already has an immutable Human decision",
                    ProductErrorCategory.STATE,
                )
            document = self._document(manifest, records + (record,))
            try:
                AtomicJsonWriter.write(
                    path,
                    document,
                    validator=lambda value: self._validate(value, manifest),
                )
            except ProductError:
                raise
            except (OSError, TypeError, ValueError) as exc:
                raise ProductError(
                    "ERR_TASK056_HUMAN_REVIEW_WRITE_FAILED",
                    "Speech cue Human decision could not be saved atomically",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc
            return document


@dataclass(slots=True)
class _PendingDecision:
    confirmation_id: str
    manifest_sha256: str
    cue_id: str
    cue_sha256: str
    decision: SpeechCueHumanDecision
    consumed: bool = False


class SpeechCueHumanReviewService:
    def __init__(
        self,
        store: SpeechCueHumanReviewStore,
        *,
        token_factory: TokenFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.store = store
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._clock = clock or utc_now_iso
        self._confirmations: dict[str, _PendingDecision] = {}

    def snapshot(self, manifest: SpeechCueManifest) -> dict[str, Any]:
        document, records = self.store.load(manifest)
        decisions = {record.cue_id: record for record in records}
        return {
            "review_store_sha256": document["review_store_sha256"],
            "review_revision": document["revision"],
            "human_accepted_count": sum(
                record.decision is SpeechCueHumanDecision.ACCEPT for record in records
            ),
            "human_rejected_count": sum(
                record.decision is SpeechCueHumanDecision.REJECT for record in records
            ),
            "pending_review_count": sum(
                cue.review_state is CueReviewState.REVIEW and cue.cue_id not in decisions
                for cue in manifest.cues
            ),
            "decisions": {
                cue_id: {
                    "decision_id": record.decision_id,
                    "decision": record.decision.value,
                }
                for cue_id, record in decisions.items()
            },
            "confirmation_tokens_persisted": False,
            "transcript_text_exposed": False,
            "host_path_exposed": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }

    def prepare(
        self,
        manifest: SpeechCueManifest,
        *,
        cue_id: str,
        decision: str,
    ) -> dict[str, Any]:
        try:
            decision_kind = SpeechCueHumanDecision(decision)
        except ValueError as exc:
            raise ProductError(
                "ERR_TASK056_HUMAN_DECISION_INVALID",
                "Speech cue Human decision must be ACCEPT or REJECT",
                ProductErrorCategory.VALIDATION,
            ) from exc
        cue = next((item for item in manifest.cues if item.cue_id == cue_id), None)
        if cue is None or cue.review_state is not CueReviewState.REVIEW:
            raise ProductError(
                "ERR_TASK056_REVIEW_CUE_NOT_FOUND",
                "Human decisions apply only to an existing REVIEW cue",
                ProductErrorCategory.STATE,
            )
        _, records = self.store.load(manifest)
        if any(record.cue_id == cue_id for record in records):
            raise ProductError(
                "ERR_TASK056_HUMAN_DECISION_ALREADY_RECORDED",
                "Speech cue already has an immutable Human decision",
                ProductErrorCategory.STATE,
            )
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError(
                "ERR_TASK056_CONFIRMATION_TOKEN_INVALID",
                "Speech cue confirmation token is invalid",
                ProductErrorCategory.INTERNAL,
            )
        manifest_sha = manifest.to_dict()["manifest_sha256"]
        pending = _PendingDecision(
            confirmation_id=token,
            manifest_sha256=manifest_sha,
            cue_id=cue.cue_id,
            cue_sha256=_cue_sha256(cue),
            decision=decision_kind,
        )
        self._confirmations[token] = pending
        return {
            "confirmation_version": "1.0.0",
            "task_owner": "TASK-056",
            "confirmation_id": token,
            "manifest_sha256": manifest_sha,
            "cue_id": cue.cue_id,
            "cue_sha256": pending.cue_sha256,
            "decision": decision_kind.value,
            "human_final_authority_required": True,
            "transcript_text_exposed": False,
            "host_path_exposed": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }

    def cancel(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_TASK056_CONFIRMATION_INVALID",
                "Speech cue confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        return {
            "task_owner": "TASK-056",
            "status": "HUMAN_DECISION_CANCELLED",
            "cue_id": pending.cue_id,
            "decision": pending.decision.value,
            "decision_persisted": False,
            "confirmation_token_persisted": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }
    def apply(
        self,
        manifest: SpeechCueManifest,
        *,
        confirmation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_TASK056_CONFIRMATION_INVALID",
                "Speech cue confirmation is missing or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending.consumed = True
        if not _ACTOR_ID.fullmatch(actor_id):
            raise ProductError(
                "ERR_TASK056_ACTOR_ID_INVALID",
                "Speech cue Human actor identity is invalid",
                ProductErrorCategory.VALIDATION,
            )
        cue = next((item for item in manifest.cues if item.cue_id == pending.cue_id), None)
        if (
            manifest.to_dict()["manifest_sha256"] != pending.manifest_sha256
            or cue is None
            or cue.review_state is not CueReviewState.REVIEW
            or _cue_sha256(cue) != pending.cue_sha256
        ):
            raise ProductError(
                "ERR_TASK056_CONFIRMATION_STALE",
                "Speech cue publication changed after Human confirmation was prepared",
                ProductErrorCategory.AUTHORIZATION,
            )
        decided_at = self._clock()
        record = SpeechCueHumanDecisionRecord(
            decision_id=_decision_id(
                manifest_sha256=pending.manifest_sha256,
                cue_id=pending.cue_id,
                decision=pending.decision,
                actor_id=actor_id,
                decided_at=decided_at,
            ),
            cue_id=pending.cue_id,
            cue_sha256=pending.cue_sha256,
            decision=pending.decision,
            actor_id=actor_id,
            decided_at=decided_at,
        )
        document = self.store.append(manifest, record)
        return {
            "task_owner": "TASK-056",
            "status": "HUMAN_DECISION_RECORDED",
            "decision_id": record.decision_id,
            "cue_id": record.cue_id,
            "decision": record.decision.value,
            "review_store_sha256": document["review_store_sha256"],
            "review_revision": document["revision"],
            "confirmation_token_persisted": False,
            "transcript_text_exposed": False,
            "host_path_exposed": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }