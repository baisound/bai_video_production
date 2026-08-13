from __future__ import annotations

from decimal import Decimal

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.production_budget import BudgetReservationStatus, ProductionBudgetLedger


def test_budget_reserve_commit_release_and_idempotent_reserve() -> None:
    ledger = ProductionBudgetLedger(plan_id="PLAN-AAAAAAAAAAAAAAAA", cost_ceiling="10", currency="USD")
    first = ledger.reserve(operation_id="job-1", estimated_amount="3")
    assert ledger.reserve(operation_id="job-1", estimated_amount="3") == first
    ledger.reserve(operation_id="job-2", estimated_amount="2")
    committed = ledger.commit(operation_id="job-1", actual_amount="2.5")
    assert committed.status is BudgetReservationStatus.COMMITTED
    released = ledger.release(operation_id="job-2")
    assert released.status is BudgetReservationStatus.RELEASED
    assert ledger.committed == Decimal("2.5")
    assert ledger.remaining == Decimal("7.5")
    body = ledger.to_dict()
    assert body["provider_execution_started"] is False
    assert body["credit_purchase_authorized"] is False
    assert body["automatic_topup_authorized"] is False


def test_budget_blocks_total_reserved_cost_above_human_ceiling() -> None:
    ledger = ProductionBudgetLedger(plan_id="PLAN-AAAAAAAAAAAAAAAA", cost_ceiling="5", currency="USD")
    ledger.reserve(operation_id="job-1", estimated_amount="4")
    with pytest.raises(ProductError) as exc:
        ledger.reserve(operation_id="job-2", estimated_amount="1.01")
    assert exc.value.code == "ERR_PRODUCTION_BUDGET_CEILING_EXCEEDED"
    assert ledger.used_or_reserved == Decimal("4")


def test_budget_blocks_actual_cost_that_would_cross_total_ceiling() -> None:
    ledger = ProductionBudgetLedger(plan_id="PLAN-AAAAAAAAAAAAAAAA", cost_ceiling="5", currency="USD")
    ledger.reserve(operation_id="job-1", estimated_amount="2")
    ledger.reserve(operation_id="job-2", estimated_amount="2")
    with pytest.raises(ProductError) as exc:
        ledger.commit(operation_id="job-1", actual_amount="3.5")
    assert exc.value.code == "ERR_PRODUCTION_BUDGET_ACTUAL_CEILING_EXCEEDED"
    assert ledger.reservations["job-1"].status is BudgetReservationStatus.RESERVED


def test_paid_execution_requires_active_reservation_and_finalized_ids_cannot_be_reused() -> None:
    ledger = ProductionBudgetLedger(plan_id="PLAN-AAAAAAAAAAAAAAAA", cost_ceiling="5", currency="USD")
    with pytest.raises(ProductError) as exc:
        ledger.require_reserved(operation_id="job-1")
    assert exc.value.code == "ERR_PRODUCTION_BUDGET_RESERVATION_REQUIRED"
    ledger.reserve(operation_id="job-1", estimated_amount="1")
    assert ledger.require_reserved(operation_id="job-1").status is BudgetReservationStatus.RESERVED
    ledger.commit(operation_id="job-1", actual_amount="0.8")
    with pytest.raises(ProductError) as exc:
        ledger.reserve(operation_id="job-1", estimated_amount="1")
    assert exc.value.code == "ERR_PRODUCTION_BUDGET_OPERATION_CONFLICT"
