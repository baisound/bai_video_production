"""TASK-027 bounded production cost ledger.

The ledger is a provider-neutral safety primitive for an Approved Production
Plan cost ceiling.  It reserves/commits/release monetary budget but never buys
credits, invokes a provider, or changes account billing settings.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import Enum
import re
from typing import Any

from .errors import ProductError, ProductErrorCategory
from .production_proposal import ApprovedProductionPlan
from .serialization import canonical_json_bytes, sha256_bytes


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def _money(value: Decimal | str | int | float, *, name: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _text(value: Decimal) -> str:
    return format(value.normalize(), "f")


class BudgetReservationStatus(str, Enum):
    RESERVED = "RESERVED"
    COMMITTED = "COMMITTED"
    RELEASED = "RELEASED"


@dataclass(frozen=True, slots=True)
class BudgetReservation:
    operation_id: str
    reserved_amount: Decimal
    status: BudgetReservationStatus = BudgetReservationStatus.RESERVED
    actual_amount: Decimal | None = None

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.operation_id):
            raise ValueError("operation_id is invalid")
        object.__setattr__(self, "reserved_amount", _money(self.reserved_amount, name="reserved_amount"))
        if self.actual_amount is not None:
            object.__setattr__(self, "actual_amount", _money(self.actual_amount, name="actual_amount"))
        if self.status is BudgetReservationStatus.COMMITTED and self.actual_amount is None:
            raise ValueError("COMMITTED reservation requires actual_amount")
        if self.status is not BudgetReservationStatus.COMMITTED and self.actual_amount is not None:
            raise ValueError("actual_amount is allowed only for COMMITTED reservation")

    @property
    def active_amount(self) -> Decimal:
        if self.status is BudgetReservationStatus.RESERVED:
            return self.reserved_amount
        if self.status is BudgetReservationStatus.COMMITTED:
            assert self.actual_amount is not None
            return self.actual_amount
        return Decimal("0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "reserved_amount": _text(self.reserved_amount),
            "status": self.status.value,
            "actual_amount": None if self.actual_amount is None else _text(self.actual_amount),
        }


class ProductionBudgetLedger:
    def __init__(self, *, plan_id: str, cost_ceiling: Decimal | str | int | float, currency: str) -> None:
        if not _ID_RE.fullmatch(plan_id):
            raise ValueError("plan_id is invalid")
        if not _CURRENCY_RE.fullmatch(currency):
            raise ValueError("currency must be a three-letter uppercase code")
        self.plan_id = plan_id
        self.cost_ceiling = _money(cost_ceiling, name="cost_ceiling")
        self.currency = currency
        self.reservations: dict[str, BudgetReservation] = {}

    @classmethod
    def from_approved_plan(cls, plan: ApprovedProductionPlan) -> "ProductionBudgetLedger":
        return cls(plan_id=plan.plan_id, cost_ceiling=plan.cost_ceiling, currency=plan.currency)

    @property
    def used_or_reserved(self) -> Decimal:
        return sum((item.active_amount for item in self.reservations.values()), Decimal("0"))

    @property
    def committed(self) -> Decimal:
        return sum(
            (item.actual_amount or Decimal("0") for item in self.reservations.values() if item.status is BudgetReservationStatus.COMMITTED),
            Decimal("0"),
        )

    @property
    def remaining(self) -> Decimal:
        return self.cost_ceiling - self.used_or_reserved

    def reserve(self, *, operation_id: str, estimated_amount: Decimal | str | int | float) -> BudgetReservation:
        estimate = _money(estimated_amount, name="estimated_amount")
        current = self.reservations.get(operation_id)
        if current is not None:
            if current.status is BudgetReservationStatus.RESERVED and current.reserved_amount == estimate:
                return current
            raise ProductError(
                "ERR_PRODUCTION_BUDGET_OPERATION_CONFLICT",
                "Budget operation identity already exists with different/finalized state",
                ProductErrorCategory.STATE,
                details={"operation_id": operation_id, "status": current.status.value},
            )
        if self.used_or_reserved + estimate > self.cost_ceiling:
            raise ProductError(
                "ERR_PRODUCTION_BUDGET_CEILING_EXCEEDED",
                "Estimated production operation would exceed the Human-approved total cost ceiling",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
                details={
                    "cost_ceiling": _text(self.cost_ceiling),
                    "used_or_reserved": _text(self.used_or_reserved),
                    "requested": _text(estimate),
                    "currency": self.currency,
                },
            )
        reservation = BudgetReservation(operation_id, estimate)
        self.reservations[operation_id] = reservation
        return reservation

    def commit(self, *, operation_id: str, actual_amount: Decimal | str | int | float) -> BudgetReservation:
        current = self.reservations.get(operation_id)
        if current is None or current.status is not BudgetReservationStatus.RESERVED:
            raise ProductError(
                "ERR_PRODUCTION_BUDGET_RESERVATION_REQUIRED",
                "Committing cost requires an active reservation",
                ProductErrorCategory.STATE,
            )
        actual = _money(actual_amount, name="actual_amount")
        other_active = self.used_or_reserved - current.reserved_amount
        if other_active + actual > self.cost_ceiling:
            raise ProductError(
                "ERR_PRODUCTION_BUDGET_ACTUAL_CEILING_EXCEEDED",
                "Actual provider cost would exceed the Human-approved total cost ceiling",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
                details={
                    "cost_ceiling": _text(self.cost_ceiling),
                    "other_used_or_reserved": _text(other_active),
                    "actual": _text(actual),
                    "currency": self.currency,
                },
            )
        committed = replace(current, status=BudgetReservationStatus.COMMITTED, actual_amount=actual)
        self.reservations[operation_id] = committed
        return committed

    def release(self, *, operation_id: str) -> BudgetReservation:
        current = self.reservations.get(operation_id)
        if current is None or current.status is not BudgetReservationStatus.RESERVED:
            raise ProductError(
                "ERR_PRODUCTION_BUDGET_RELEASE_INVALID",
                "Only an active reservation may be released",
                ProductErrorCategory.STATE,
            )
        released = replace(current, status=BudgetReservationStatus.RELEASED)
        self.reservations[operation_id] = released
        return released

    def require_reserved(self, *, operation_id: str) -> BudgetReservation:
        current = self.reservations.get(operation_id)
        if current is None or current.status is not BudgetReservationStatus.RESERVED:
            raise ProductError(
                "ERR_PRODUCTION_BUDGET_RESERVATION_REQUIRED",
                "Paid provider execution requires an active budget reservation",
                ProductErrorCategory.AUTHORIZATION,
                details={"operation_id": operation_id},
            )
        return current

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "ledger_version": "1.0.0",
            "task_owner": "TASK-027",
            "plan_id": self.plan_id,
            "cost_ceiling": _text(self.cost_ceiling),
            "currency": self.currency,
            "used_or_reserved": _text(self.used_or_reserved),
            "committed": _text(self.committed),
            "remaining": _text(self.remaining),
            "reservations": [self.reservations[key].to_dict() for key in sorted(self.reservations)],
            "provider_execution_started": False,
            "credit_purchase_authorized": False,
            "automatic_topup_authorized": False,
        }
        body["ledger_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body
