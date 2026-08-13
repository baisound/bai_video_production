from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.production_budget import ProductionBudgetLedger
from ai_video_production.production_budget_store import ProductionBudgetSnapshotStore


def ledger() -> ProductionBudgetLedger:
    value = ProductionBudgetLedger(plan_id="PLAN-AAAAAAAAAAAAAAAA", cost_ceiling="10", currency="USD")
    value.reserve(operation_id="job-1", estimated_amount="3")
    value.commit(operation_id="job-1", actual_amount="2.5")
    value.reserve(operation_id="job-2", estimated_amount="1")
    return value


def test_budget_snapshot_roundtrip_and_cas(tmp_path: Path) -> None:
    source = ledger()
    path = tmp_path / "budget.json"
    ProductionBudgetSnapshotStore.save(path, source)
    loaded = ProductionBudgetSnapshotStore.load(path)
    assert loaded.to_dict() == source.to_dict()
    snap = ProductionBudgetSnapshotStore.snapshot(loaded)
    assert snap["credit_purchase_authorized"] is False
    assert snap["automatic_topup_authorized"] is False
    ProductionBudgetSnapshotStore.save(path, loaded, expected_previous_snapshot_sha256=snap["snapshot_sha256"])


def test_budget_snapshot_requires_cas(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    source = ledger()
    ProductionBudgetSnapshotStore.save(path, source)
    with pytest.raises(ProductError) as exc:
        ProductionBudgetSnapshotStore.save(path, source)
    assert exc.value.code == "ERR_PRODUCTION_BUDGET_SNAPSHOT_CAS_REQUIRED"


def test_budget_snapshot_rejects_tampered_derived_totals(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    ProductionBudgetSnapshotStore.save(path, ledger())
    doc = json.loads(path.read_text(encoding="utf-8"))
    # Rewrite both outer and inner hashes so the parser reaches derived-total validation.
    doc["ledger"]["remaining"] = "999"
    from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
    inner = {k: v for k, v in doc["ledger"].items() if k != "ledger_sha256"}
    doc["ledger"]["ledger_sha256"] = sha256_bytes(canonical_json_bytes(inner))
    outer = {k: v for k, v in doc.items() if k != "snapshot_sha256"}
    doc["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(outer))
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ProductionBudgetSnapshotStore.load(path)
    assert exc.value.code == "ERR_PRODUCTION_BUDGET_SNAPSHOT_DERIVED_MISMATCH"
