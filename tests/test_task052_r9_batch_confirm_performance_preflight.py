from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "task052" / "run-r9-batch-confirm-performance-preflight.py"


def _run(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    authorized = tmp_path / "authorized" / "TASK-052" / "r9-batch-confirm"
    authorized.mkdir(parents=True, exist_ok=True)
    run_root = authorized / "run-001"
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--authorized-root",
            str(authorized),
            "--run-root",
            str(run_root),
            "--sample-count",
            "40",
            "--max-total-seconds",
            "30",
            *extra,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_synthetic_preflight_confirms_once_rebuilds_once_and_reads_back(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["result"] == "PASS"
    assert receipt["scope"] == "BATCH_CONFIRM_TRANSACTION_ONLY"
    assert receipt["sample_count"] == 40
    assert receipt["manifest_write_count"] == 1
    assert receipt["manifest_readback_count"] == 40
    assert receipt["metrics"]["stage_count"] == 40
    assert receipt["metrics"]["confirm_count"] == 40
    assert receipt["metrics"]["subprocess_count"] == 0
    assert len(receipt["metrics"]["index_paths"]) == 1
    assert all(receipt["checks"].values())


def test_receipt_is_explicitly_not_real_media_generator_or_accuracy_evidence(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["operator_flow_reference"].endswith("確認したCropを一括登録")
    assert receipt["surrogate_label"] == "generator_remaining_0_transaction_surrogate"
    assert receipt["exact_generator_teacher_contract_available"] is False
    for field in (
        "real_media",
        "human_gold",
        "production_performance_claim_authorized",
        "production_accuracy_claim_authorized",
        "provider_execution_started",
        "dataset_adoption_started",
        "training_started",
        "model_download_started",
        "native_application_started",
    ):
        assert receipt[field] is False


@pytest.mark.parametrize("stdio_encoding", ["cp1252:strict", "ascii:strict"])
def test_stdout_is_ascii_without_changing_the_utf8_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stdio_encoding: str
) -> None:
    monkeypatch.setenv("PYTHONIOENCODING", stdio_encoding)
    monkeypatch.setenv("PYTHONUTF8", "0")
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.isascii()
    receipt = json.loads(result.stdout)
    assert receipt["operator_flow_reference"].endswith("確認したCropを一括登録")

    receipt_path = (
        tmp_path
        / "authorized"
        / "TASK-052"
        / "r9-batch-confirm"
        / "run-001"
        / "task052-r9-batch-confirm-performance-preflight.json"
    )
    receipt_bytes = receipt_path.read_bytes()
    receipt_text = receipt_bytes.decode("utf-8")
    assert "画像学習データ" in receipt_text
    assert json.loads(receipt_text) == {
        key: value for key, value in receipt.items() if key != "receipt_sha256"
    }
    assert receipt["receipt_sha256"] == hashlib.sha256(receipt_bytes).hexdigest()


def test_preflight_refuses_existing_or_out_of_scope_run_root(tmp_path: Path) -> None:
    first = _run(tmp_path)
    assert first.returncode == 0, first.stderr
    repeated = _run(tmp_path)
    assert repeated.returncode != 0
    assert "refusing to reuse foreign or historical evidence" in repeated.stderr

    authorized = tmp_path / "second" / "TASK-052" / "r9-batch-confirm"
    authorized.mkdir(parents=True)
    outside = tmp_path / "outside" / "run-002"
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--authorized-root",
            str(authorized),
            "--run-root",
            str(outside),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "must be a new child of the authorized root" in result.stderr
