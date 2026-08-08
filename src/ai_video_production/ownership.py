from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import ProductError, ProductErrorCategory

class TimelineOwner(str, Enum):
    AUTOMATION = "AUTOMATION"
    HUMAN = "HUMAN"
    SHARED = "SHARED"

class ActorKind(str, Enum):
    AUTOMATION = "AUTOMATION"
    HUMAN = "HUMAN"

@dataclass(frozen=True, slots=True)
class TimelineRef:
    name: str
    owner: TimelineOwner
    revision: int

class TimelineWriteGuard:
    @staticmethod
    def authorize(ref: TimelineRef, *, actor: ActorKind, expected_revision: int) -> None:
        if ref.revision != expected_revision:
            raise ProductError(
                "ERR_STATE_STALE_REVISION", "timeline revision conflict",
                ProductErrorCategory.STATE, False,
                details={"expected": expected_revision, "actual": ref.revision},
            )
        if ref.owner is TimelineOwner.HUMAN and actor is ActorKind.AUTOMATION:
            raise ProductError("ERR_AUTH_TIMELINE_PROTECTED", "human-owned timeline is protected", ProductErrorCategory.AUTHORIZATION)
        if ref.owner is TimelineOwner.AUTOMATION and actor is ActorKind.HUMAN:
            raise ProductError(
                "ERR_AUTH_AUTOMATION_TIMELINE_IMMUTABLE",
                "edit a human-owned derivative instead of mutating automation assembly",
                ProductErrorCategory.AUTHORIZATION,
            )
