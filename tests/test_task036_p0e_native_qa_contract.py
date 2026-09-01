from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "windows" / "run-task036-p0e-native-qa.ps1"
FIXTURE = ROOT / "tests" / "test_task036_p0e_fixture_vertical_slice.py"
TASK063_FAULT_FIXTURE = (
    ROOT
    / "docs"
    / "ai-team"
    / "tasks"
    / "TASK-036"
    / "task063-l3-native-fault-fixture-v1.json"
)
SOURCE_COMMIT = "a" * 40
DIGESTS = (
    "sha256:" + "b" * 64,
    "sha256:" + "c" * 64,
    "sha256:" + "d" * 64,
)


def test_p0e_native_qa_projection_is_filesystem_and_effect_free() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    fixture_source = FIXTURE.read_text(encoding="utf-8")
    assert 'FIXTURE_CONTRACT_VERSION = "task036-p0e-fixture/v1"' in fixture_source
    for marker in (
        "task036-p0e-native-qa/v1",
        "task036-p0e-fixture/v1",
        "TASK036-P0E-AI-SETTINGS-STARTUP-INTEGRATION-V1",
        "state = 'PREPARED'",
        "technical_result = 'NOT_CONFIRMED'",
        "authority_created = $false",
        "source_commit_verified = $false",
        "fixture_snapshot_verified = $false",
        "package_snapshot_verified = $false",
        "receipt_persisted = $false",
        "task063_terminal_handoff_consumed = $false",
        "packaged_entry_binding_started = $false",
        "first_run_binding_started = $false",
        "single_instance_binding_started = $false",
        "startup_error_readback_started = $false",
        "model_setting_persistence_readback_started = $false",
        "native_execution_started = $false",
        "provider_execution_started = $false",
        "paid_execution_authorized = $false",
        "download_or_install_started = $false",
        "export_dispatch_started = $false",
        "resolve_mutation_started = $false",
        "release_or_deploy_started = $false",
        "production_activation_started = $false",
        "host_path_persisted = $false",
    ):
        assert marker in source

    for forbidden in (
        "Resolve-Path",
        "Get-FileHash",
        "Get-ChildItem",
        "New-Item",
        "Start-Process",
        "Remove-Item",
        "Invoke-",
        "Set-Content",
        "Out-File",
        "FileStream",
    ):
        assert forbidden not in source


def test_task063_l3_native_fault_fixture_is_closed_and_effect_free() -> None:
    fixture = json.loads(TASK063_FAULT_FIXTURE.read_text(encoding="utf-8"))
    assert set(fixture) == {
        "fixture_version",
        "task",
        "consumer",
        "synthetic",
        "authority_created",
        "native_execution_started",
        "install_or_update_started",
        "rollback_or_cleanup_started",
        "task063_completion_receipt_present",
        "scenarios",
    }
    assert fixture["fixture_version"] == "task063-l3-native-fault-fixture/v1"
    assert fixture["task"] == "TASK-063"
    assert fixture["consumer"] == "TASK-036-P0-E"
    assert fixture["synthetic"] is True
    for key in (
        "authority_created",
        "native_execution_started",
        "install_or_update_started",
        "rollback_or_cleanup_started",
        "task063_completion_receipt_present",
    ):
        assert fixture[key] is False

    scenarios = fixture["scenarios"]
    assert [scenario["id"] for scenario in scenarios] == [
        "I63-NQA-01",
        "I63-NQA-02",
        "I63-NQA-03",
        "I63-NQA-04",
        "I63-NQA-05",
        "I63-NQA-06",
        "I63-NQA-07",
        "I63-NQA-08",
        "I63-NQA-09",
    ]
    assert len({scenario["seam"] for scenario in scenarios}) == 9
    for scenario in scenarios:
        assert set(scenario) == {
            "id",
            "seam",
            "expected_results",
            "duplicate_requires_exact_committed_event",
            "authoritative_revision_delta",
            "target_state",
            "completion_receipt_authoritative",
            "unrelated_delta",
            "foreign_delete_or_overwrite",
        }
        assert scenario["expected_results"]
        assert scenario["authoritative_revision_delta"] in (None, 0, 1)
        assert type(scenario["duplicate_requires_exact_committed_event"]) is bool
        assert type(scenario["completion_receipt_authoritative"]) is bool
        assert type(scenario["target_state"]) is str
        assert scenario["unrelated_delta"] == 0
        assert scenario["foreign_delete_or_overwrite"] == 0

    by_id = {scenario["id"]: scenario for scenario in scenarios}
    assert by_id["I63-NQA-02"]["expected_results"] == [
        "ACCEPTED",
        "STALE_PREDECESSOR",
        "DUPLICATE",
    ]
    assert by_id["I63-NQA-02"]["duplicate_requires_exact_committed_event"] is True
    for scenario_id in ("I63-NQA-04", "I63-NQA-06", "I63-NQA-07"):
        assert by_id[scenario_id]["authoritative_revision_delta"] is None
        assert by_id[scenario_id]["completion_receipt_authoritative"] is False
    assert by_id["I63-NQA-05"]["authoritative_revision_delta"] == 1
    assert by_id["I63-NQA-05"]["completion_receipt_authoritative"] is False


def _powershell() -> str:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("Windows PowerShell unavailable")
    return powershell


def _command(*, source_commit: str = SOURCE_COMMIT, digests: tuple[str, str, str] = DIGESTS) -> list[str]:
    return [
        _powershell(),
        "-NoProfile",
        "-File",
        str(SCRIPT),
        "-ExpectedSourceCommit",
        source_commit,
        "-ExpectedFixtureSourceSha256",
        digests[0],
        "-ExpectedPackageExecutableSha256",
        digests[1],
        "-ExpectedPackageTreeSha256",
        digests[2],
    ]


@pytest.mark.skipif(os.name != "nt", reason="PowerShell behavior is Windows-only")
def test_p0e_native_qa_projection_is_deterministic_and_unverified() -> None:
    first = subprocess.run(_command(), check=True, capture_output=True, text=True)
    second = subprocess.run(_command(), check=True, capture_output=True, text=True)
    assert first.stderr == ""
    assert first.stdout == second.stdout

    projection = json.loads(first.stdout)
    expected_keys = {
        "receipt_version",
        "task",
        "unit",
        "startup_integration_contract",
        "state",
        "technical_result",
        "authority_created",
        "expected_source_commit",
        "source_commit_verified",
        "fixture_contract_version",
        "expected_fixture_source_sha256",
        "fixture_snapshot_verified",
        "expected_package_executable_sha256",
        "expected_package_tree_sha256",
        "package_snapshot_verified",
        "receipt_persisted",
        "task063_terminal_handoff_consumed",
        "packaged_entry_binding_started",
        "first_run_binding_started",
        "single_instance_binding_started",
        "startup_error_readback_started",
        "model_setting_persistence_readback_started",
        "native_execution_started",
        "provider_execution_started",
        "paid_execution_authorized",
        "download_or_install_started",
        "export_dispatch_started",
        "resolve_mutation_started",
        "release_or_deploy_started",
        "production_activation_started",
        "host_path_persisted",
    }
    assert set(projection) == expected_keys
    string_keys = {
        "receipt_version",
        "task",
        "unit",
        "startup_integration_contract",
        "state",
        "technical_result",
        "expected_source_commit",
        "fixture_contract_version",
        "expected_fixture_source_sha256",
        "expected_package_executable_sha256",
        "expected_package_tree_sha256",
    }
    assert all(type(projection[key]) is str for key in string_keys)
    assert all(type(projection[key]) is bool for key in expected_keys - string_keys)
    assert projection["state"] == "PREPARED"
    assert projection["technical_result"] == "NOT_CONFIRMED"
    assert projection["authority_created"] is False
    assert projection["expected_source_commit"] == SOURCE_COMMIT
    assert projection["source_commit_verified"] is False
    assert projection["expected_fixture_source_sha256"] == DIGESTS[0]
    assert projection["fixture_snapshot_verified"] is False
    assert projection["expected_package_executable_sha256"] == DIGESTS[1]
    assert projection["expected_package_tree_sha256"] == DIGESTS[2]
    assert projection["package_snapshot_verified"] is False
    assert projection["receipt_persisted"] is False
    assert projection["task063_terminal_handoff_consumed"] is False
    for key, value in projection.items():
        if key.endswith("_started") or key.endswith("_authorized") or key.endswith("_persisted"):
            assert value is False

    different_expected_commit = "f" * 40
    wrong_but_well_formed = subprocess.run(
        _command(source_commit=different_expected_commit),
        check=True,
        capture_output=True,
        text=True,
    )
    wrong_projection = json.loads(wrong_but_well_formed.stdout)
    assert wrong_projection["expected_source_commit"] == different_expected_commit
    assert wrong_projection["source_commit_verified"] is False


@pytest.mark.skipif(os.name != "nt", reason="PowerShell behavior is Windows-only")
def test_p0e_native_qa_projection_rejects_malformed_expected_coordinates() -> None:
    missing_coordinate = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(SCRIPT),
            "-ExpectedSourceCommit",
            SOURCE_COMMIT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert missing_coordinate.returncode != 0
    assert missing_coordinate.stdout.strip() == "[ERROR] ERR_TASK036_P0E_EXPECTED_DIGEST_INVALID"
    assert missing_coordinate.stderr == ""
    assert str(ROOT) not in missing_coordinate.stdout

    invalid_commit = subprocess.run(
        _command(source_commit="not-a-commit"),
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid_commit.returncode != 0
    assert invalid_commit.stdout.strip() == "[ERROR] ERR_TASK036_P0E_EXPECTED_SOURCE_COMMIT_INVALID"
    assert invalid_commit.stderr == ""

    malformed = ("sha256:" + "b" * 63, DIGESTS[1], DIGESTS[2])
    invalid_digest = subprocess.run(
        _command(digests=malformed),
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid_digest.returncode != 0
    assert invalid_digest.stdout.strip() == "[ERROR] ERR_TASK036_P0E_EXPECTED_DIGEST_INVALID"
    assert invalid_digest.stderr == ""
