from __future__ import annotations

import os
from pathlib import Path

import pytest

from ai_video_production.task102_windows_feasibility import (
    FeasibilityError,
    RUN_PREFIX,
    classify_recovery,
    validate_run_root,
)


PRED = "sha256:" + "1" * 64
SUCC = "sha256:" + "2" * 64


def test_validate_run_root_accepts_new_exact_temp_child(tmp_path: Path) -> None:
    root = tmp_path / f"{RUN_PREFIX}0123456789abcdef"

    assert validate_run_root(root, tmp_path) == root.absolute()


@pytest.mark.parametrize(
    ("candidate", "code"),
    [
        ("foreign-name", "RUN_ROOT_NAME_REJECTED"),
        (f"nested/{RUN_PREFIX}run", "RUN_ROOT_NOT_DIRECT_TEMP_CHILD"),
    ],
)
def test_validate_run_root_rejects_unsafe_shape(
    tmp_path: Path, candidate: str, code: str
) -> None:
    root = tmp_path / candidate
    if "/" in candidate:
        root.parent.mkdir()

    with pytest.raises(FeasibilityError, match=code):
        validate_run_root(root, tmp_path)


def test_validate_run_root_rejects_existing_path(tmp_path: Path) -> None:
    root = tmp_path / f"{RUN_PREFIX}existing"
    root.mkdir()

    with pytest.raises(FeasibilityError, match="RUN_ROOT_ALREADY_EXISTS"):
        validate_run_root(root, tmp_path)


def test_validate_run_root_rejects_outside_temp(tmp_path: Path) -> None:
    other = tmp_path.parent / f"{RUN_PREFIX}outside"

    with pytest.raises(FeasibilityError, match="RUN_ROOT_OUTSIDE_SYSTEM_TEMP"):
        validate_run_root(other, tmp_path)


@pytest.mark.parametrize(
    ("witness", "observed", "excluded", "expected"),
    [
        ("PREPARED", PRED, True, "NOT_COMMITTED_PROVEN"),
        ("PREPARED", SUCC, True, "COMMITTED_WITH_READBACK"),
        ("TERMINAL_COMMITTED", SUCC, False, "COMMITTED_WITH_READBACK"),
        ("PREPARED", PRED, False, "COMMIT_OUTCOME_UNKNOWN"),
        (None, PRED, True, "COMMIT_OUTCOME_UNKNOWN"),
        ("PREPARED", "sha256:" + "3" * 64, True, "COMMIT_OUTCOME_UNKNOWN"),
        ("CORRUPT", SUCC, True, "COMMIT_OUTCOME_UNKNOWN"),
    ],
)
def test_classify_recovery_is_closed(
    witness: str | None, observed: str, excluded: bool, expected: str
) -> None:
    assert (
        classify_recovery(
            witness_state=witness,
            observed_sha256=observed,
            predecessor_sha256=PRED,
            successor_sha256=SUCC,
            continuous_exclusion=excluded,
        )
        == expected
    )


def test_windows_native_entrypoint_is_windows_only() -> None:
    if os.name == "nt":
        pytest.skip("negative platform test")
    from ai_video_production.task102_windows_feasibility import run_n1a

    with pytest.raises(FeasibilityError, match="WINDOWS_REQUIRED"):
        run_n1a(Path("unused"))
