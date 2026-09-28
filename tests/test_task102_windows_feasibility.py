from __future__ import annotations

import os
from pathlib import Path

import pytest

from ai_video_production.task102_windows_feasibility import (
    FeasibilityError,
    RUN_PREFIX,
    classify_recovery,
    protected_pipe_sddl,
    validate_run_root,
    validate_service_name,
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


def test_service_name_accepts_only_unique_bounded_hex_suffix() -> None:
    value = "BvpTask102PmstN1-0123456789abcdef"

    assert validate_service_name(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "Foreign-0123456789abcdef",
        "BvpTask102PmstN1-short",
        "BvpTask102PmstN1-0123456789abcdeg",
        "BvpTask102PmstN1-" + "0" * 33,
    ],
)
def test_service_name_rejects_foreign_or_unsafe_value(value: str) -> None:
    with pytest.raises(FeasibilityError, match="SERVICE_NAME_REJECTED"):
        validate_service_name(value)


def test_protected_pipe_sddl_is_closed_to_service_and_client_sids() -> None:
    value = protected_pipe_sddl("S-1-5-80-1234", "S-1-5-21-5678")

    assert value == (
        "D:P(A;;GA;;;SY)(A;;GA;;;BA)"
        "(A;;GA;;;S-1-5-80-1234)(A;;GRGW;;;S-1-5-21-5678)"
    )


def test_protected_pipe_sddl_rejects_non_sid_text() -> None:
    with pytest.raises(FeasibilityError, match="PIPE_SID_REJECTED"):
        protected_pipe_sddl("NT SERVICE\\example", "S-1-5-21-5678")
