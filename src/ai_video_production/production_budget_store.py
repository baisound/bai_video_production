"""Crash-safe TASK-027 production-budget persistence with CAS replacement."""

from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .production_budget import BudgetReservation, BudgetReservationStatus, ProductionBudgetLedger
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_BYTES = 4 * 1024 * 1024


def _body(ledger: ProductionBudgetLedger) -> dict[str, Any]:
    body: dict[str, Any] = {
        "snapshot_version": "1.0.0",
        "task_owner": "TASK-027",
        "ledger": ledger.to_dict(),
        "credential_values_embedded": False,
        "provider_execution_authorized": False,
        "credit_purchase_authorized": False,
        "automatic_topup_authorized": False,
    }
    body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse(document: dict[str, Any]) -> ProductionBudgetLedger:
    if document.get("snapshot_version") != "1.0.0":
        raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_VERSION", "Unsupported production budget snapshot version", ProductErrorCategory.DATA_INTEGRITY)
    expected = document.get("snapshot_sha256")
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_CHECKSUM", "Production budget snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if any(document.get(key) is not False for key in (
        "credential_values_embedded",
        "provider_execution_authorized",
        "credit_purchase_authorized",
        "automatic_topup_authorized",
    )):
        raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_BOUNDARY", "Production budget snapshot violates execution/billing boundaries", ProductErrorCategory.SECURITY)
    row = document.get("ledger")
    if not isinstance(row, dict):
        raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_INVALID", "Production budget ledger record is invalid", ProductErrorCategory.DATA_INTEGRITY)
    ledger_expected = row.get("ledger_sha256")
    ledger_body = {key: value for key, value in row.items() if key != "ledger_sha256"}
    if ledger_expected != sha256_bytes(canonical_json_bytes(ledger_body)):
        raise ProductError("ERR_PRODUCTION_BUDGET_LEDGER_CHECKSUM", "Embedded production budget ledger checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if (
        row.get("provider_execution_started") is not False
        or row.get("credit_purchase_authorized") is not False
        or row.get("automatic_topup_authorized") is not False
    ):
        raise ProductError("ERR_PRODUCTION_BUDGET_LEDGER_BOUNDARY", "Budget ledger cannot grant provider/billing authority", ProductErrorCategory.SECURITY)
    try:
        ledger = ProductionBudgetLedger(plan_id=row["plan_id"], cost_ceiling=Decimal(row["cost_ceiling"]), currency=row["currency"])
        for item in row["reservations"]:
            reservation = BudgetReservation(
                operation_id=item["operation_id"],
                reserved_amount=Decimal(item["reserved_amount"]),
                status=BudgetReservationStatus(item["status"]),
                actual_amount=None if item.get("actual_amount") is None else Decimal(item["actual_amount"]),
            )
            if reservation.operation_id in ledger.reservations:
                raise ValueError("duplicate operation_id")
            ledger.reservations[reservation.operation_id] = reservation
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_INVALID", "Production budget snapshot contains invalid records", ProductErrorCategory.DATA_INTEGRITY) from exc
    # Recompute every derived amount; never trust serialized totals.
    actual = ledger.to_dict()
    for field in ("used_or_reserved", "committed", "remaining", "ledger_sha256"):
        if row.get(field) != actual[field]:
            raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_DERIVED_MISMATCH", "Production budget derived totals/identity do not match reservation state", ProductErrorCategory.DATA_INTEGRITY, details={"field": field})
    if ledger.used_or_reserved > ledger.cost_ceiling:
        raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_OVER_CEILING", "Recovered production budget state exceeds approved cost ceiling", ProductErrorCategory.DATA_INTEGRITY)
    return ledger


class ProductionBudgetSnapshotStore:
    @staticmethod
    def snapshot(ledger: ProductionBudgetLedger) -> dict[str, Any]:
        return _body(ledger)

    @staticmethod
    def load(path: str | Path) -> ProductionBudgetLedger:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_FILE_INVALID", "Production budget snapshot must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_SIZE", "Production budget snapshot size is outside the allowed bound", ProductErrorCategory.VALIDATION, details={"size_bytes": size})
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_READ", "Production budget snapshot could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(document, dict):
            raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_INVALID", "Production budget snapshot root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        return _parse(document)

    @staticmethod
    def save(
        path: str | Path,
        ledger: ProductionBudgetLedger,
        *,
        expected_previous_snapshot_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = Path(path)
        if target.is_symlink():
            raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_FILE_INVALID", "Refusing to replace a symlink production budget snapshot", ProductErrorCategory.SECURITY)
        if target.exists():
            if not target.is_file():
                raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_FILE_INVALID", "Production budget snapshot target must be a regular file", ProductErrorCategory.VALIDATION)
            if expected_previous_snapshot_sha256 is None:
                raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_CAS_REQUIRED", "Replacing production budget state requires exact previous checksum", ProductErrorCategory.AUTHORIZATION)
            current = _body(ProductionBudgetSnapshotStore.load(target))["snapshot_sha256"]
            if current != expected_previous_snapshot_sha256:
                raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_REVISION_CONFLICT", "Production budget snapshot changed before save; reload before retry", ProductErrorCategory.STATE)
        elif expected_previous_snapshot_sha256 is not None:
            raise ProductError("ERR_PRODUCTION_BUDGET_SNAPSHOT_PREVIOUS_MISSING", "Expected previous production budget snapshot does not exist", ProductErrorCategory.STATE)
        document = _body(ledger)
        return AtomicJsonWriter.write(target, document, validator=lambda value: _parse(value))
