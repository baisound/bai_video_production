from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class ProductErrorCategory(str, Enum):
    VALIDATION = "VALIDATION"
    AUTHORIZATION = "AUTHORIZATION"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    TRANSIENT = "TRANSIENT"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    TIMEOUT = "TIMEOUT"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    DATA_INTEGRITY = "DATA_INTEGRITY"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    INTERNAL = "INTERNAL"
    STATE = "STATE"
    SECURITY = "SECURITY"

@dataclass(slots=True)
class ProductError(Exception):
    code: str
    message: str
    category: ProductErrorCategory = ProductErrorCategory.INTERNAL
    retryable: bool = False
    operation_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    evidence_uri: str | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)
        if not self.code.startswith("ERR_"):
            raise ValueError("product error code must start with ERR_")

    def to_envelope(self) -> dict[str, Any]:
        error = {
            "code": self.code,
            "category": self.category.value,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
        }
        if self.operation_id:
            error["operation_id"] = self.operation_id
        if self.evidence_uri:
            error["evidence_uri"] = self.evidence_uri
        return {"error": error}


def validation_error(code: str, message: str, **details: Any) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.VALIDATION, False, details=details)


def integrity_error(code: str, message: str, **details: Any) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.DATA_INTEGRITY, False, details=details)
