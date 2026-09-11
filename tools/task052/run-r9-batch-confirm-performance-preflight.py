"""Run a synthetic, no-media TASK-052 R9 batch-confirm performance preflight.

This tool intentionally exercises only the already-implemented R2B staged-file
commit and reference-index rebuild path.  It does not claim to reproduce the
missing GENERATOR_REMAINING teacher/detector route or real-video performance.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_safe_visual_learning import (
    SafeVisualLearningService,
    StagedTrainingSample,
)
from ai_video_production.dbd_training_workspace import (
    VisualTrainingDomain,
    VisualTrainingManifest,
)


UNIT = "R9-BATCH-CONFIRM-PERFORMANCE-PREFLIGHT"
SURROGATE_LABEL = "generator_remaining_0_transaction_surrogate"


def _resolved_new_run_root(*, authorized_root: Path, run_root: Path) -> tuple[Path, Path]:
    authorized = authorized_root.expanduser().resolve(strict=True)
    if not authorized.is_dir():
        raise ValueError("authorized root must be an existing directory")
    target = run_root.expanduser().resolve(strict=False)
    if target == authorized or not target.is_relative_to(authorized):
        raise ValueError("run root must be a new child of the authorized root")
    if target.exists():
        raise ValueError("run root already exists; refusing to reuse foreign or historical evidence")
    if target.drive:
        drive_root = Path(target.anchor)
        if target == drive_root or target.parent == drive_root:
            raise ValueError("run root must not be a drive root or its direct child")
        if authorized == drive_root or authorized.parent == drive_root:
            raise ValueError("authorized root must not be a drive root or its direct child")
    return authorized, target


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(raw_temp)
    try:
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _pgm_bytes(number: int) -> bytes:
    width = height = 16
    values = [((number * 17 + offset * 13) % 256) for offset in range(width * height)]
    # GrayImage.read_pgm intentionally skips header whitespace before the pixel
    # body, so the first fixture pixel must not itself be an ASCII whitespace byte.
    values[0] = 1
    pixels = bytes(values)
    return f"P5\n{width} {height}\n255\n".encode("ascii") + pixels


def _stage_synthetic_samples(
    service: SafeVisualLearningService,
    *,
    sample_count: int,
) -> tuple[StagedTrainingSample, ...]:
    staged: list[StagedTrainingSample] = []
    for number in range(sample_count):
        staging_id = f"synthetic-{number:05d}"
        directory = service.staging_root / staging_id
        directory.mkdir(parents=True, exist_ok=False)
        image = directory / f"frame-{number:09d}.pgm"
        raw = _pgm_bytes(number)
        image.write_bytes(raw)
        item = StagedTrainingSample(
            staging_id=staging_id,
            domain=VisualTrainingDomain.PERK_ICON,
            label=SURROGATE_LABEL,
            visibility=HudVisibility.VISIBLE,
            source_video="fixture://synthetic-no-media",
            source_frame=number,
            roi_id="transaction_surrogate",
            image_path=str(image),
            source_ref=f"fixture://task052-r9/batch-confirm/{number}",
            notes="Synthetic transaction surrogate; not detector or accuracy evidence.",
            registration_origin="VIDEO_BATCH",
            sha256=f"sha256:{hashlib.sha256(raw).hexdigest()}",
        )
        service._write_receipt(item)
        staged.append(item)
    return tuple(staged)


def run_preflight(
    *,
    authorized_root: Path,
    run_root: Path,
    sample_count: int,
    max_total_seconds: float,
) -> dict[str, object]:
    if not 1 <= sample_count <= 500:
        raise ValueError("sample count must be 1..500")
    if not 0.001 <= max_total_seconds <= 600.0:
        raise ValueError("max total seconds must be 0.001..600")
    authorized, target = _resolved_new_run_root(
        authorized_root=authorized_root,
        run_root=run_root,
    )
    target.mkdir(parents=True, exist_ok=False)
    workspace = target / "workspace"
    manifest = VisualTrainingManifest(workspace / "visual-training.csv")
    service = SafeVisualLearningService(workspace_root=workspace, manifest=manifest)
    staged = _stage_synthetic_samples(service, sample_count=sample_count)

    manifest_write_count = 0
    original_write = manifest._write

    def counted_write(values: Sequence[object]) -> None:
        nonlocal manifest_write_count
        manifest_write_count += 1
        original_write(values)

    manifest._write = counted_write
    report = service.confirm_batch(
        staged,
        rebuild_indexes=True,
        extract_seconds=0.0,
        stage_subprocess_count=0,
    )

    readback_manifest = VisualTrainingManifest(workspace / "visual-training.csv")
    readback_count = len(readback_manifest.list())
    index_paths = tuple(Path(value) for value in report.index_paths)
    indexes_readable = len(index_paths) == 1 and all(
        isinstance(json.loads(path.read_text(encoding="utf-8")), dict)
        for path in index_paths
    )
    batch_receipts = tuple((workspace / "staging" / "visual-learning" / "batches").glob("*.json"))
    batch_receipt_readable = len(batch_receipts) == 1 and isinstance(
        json.loads(batch_receipts[0].read_text(encoding="utf-8")), dict
    )
    checks = {
        "all_samples_confirmed": report.confirm_count == sample_count,
        "no_confirm_subprocess": report.subprocess_count == 0,
        "manifest_written_once": manifest_write_count == 1,
        "manifest_readback_exact": readback_count == sample_count,
        "one_reference_index": len(index_paths) == 1,
        "reference_index_readable": indexes_readable,
        "batch_receipt_readable": batch_receipt_readable,
        "no_operation_errors": report.failed_count == 0 and not report.errors,
        "bounded_total_seconds": report.total_seconds <= max_total_seconds,
    }
    result = "PASS" if all(checks.values()) else "FAIL"
    metrics = asdict(report)
    metrics["index_paths"] = [
        path.relative_to(target).as_posix()
        for path in index_paths
    ]
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "task": "TASK-052",
        "unit": UNIT,
        "operation_id": target.name,
        "result": result,
        "scope": "BATCH_CONFIRM_TRANSACTION_ONLY",
        "operator_flow_reference": "画像学習データ -> 発電機 残0 -> 確認したCropを一括登録",
        "surrogate_domain": VisualTrainingDomain.PERK_ICON.value,
        "surrogate_label": SURROGATE_LABEL,
        "exact_generator_teacher_contract_available": False,
        "real_media": False,
        "human_gold": False,
        "production_performance_claim_authorized": False,
        "production_accuracy_claim_authorized": False,
        "provider_execution_started": False,
        "dataset_adoption_started": False,
        "training_started": False,
        "model_download_started": False,
        "native_application_started": False,
        "authorized_root_sha256": hashlib.sha256(str(authorized).encode("utf-8")).hexdigest(),
        "run_root_sha256": hashlib.sha256(str(target).encode("utf-8")).hexdigest(),
        "sample_count": sample_count,
        "max_total_seconds": max_total_seconds,
        "manifest_write_count": manifest_write_count,
        "manifest_readback_count": readback_count,
        "checks": checks,
        "metrics": metrics,
    }
    receipt_path = target / "task052-r9-batch-confirm-performance-preflight.json"
    _write_json_atomic(receipt_path, receipt)
    readback = json.loads(receipt_path.read_text(encoding="utf-8"))
    if readback.get("operation_id") != target.name or readback.get("result") != result:
        raise RuntimeError("receipt read-back identity mismatch")
    receipt["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    if result != "PASS":
        raise RuntimeError("batch-confirm performance preflight failed")
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--sample-count", type=int, default=64)
    parser.add_argument("--max-total-seconds", type=float, default=30.0)
    return parser


def main() -> int:
    args = _parser().parse_args()
    receipt = run_preflight(
        authorized_root=args.authorized_root,
        run_root=args.run_root,
        sample_count=args.sample_count,
        max_total_seconds=args.max_total_seconds,
    )
    # stdout may be a legacy-encoded pipe on Windows. JSON escapes preserve
    # localized labels without changing the persisted UTF-8 receipt.
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
