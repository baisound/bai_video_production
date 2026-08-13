from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.task010_native_gate import (
    Task010NativeCase,
    Task010NativeGateRunner,
    build_task010_assembly_plan,
    build_task010_edit_plan,
    task010_native_cases,
)
from ai_video_production.timebase import FrameRate


def test_native_case_matrix_covers_30_60_and_fractional_source_rates():
    cases = task010_native_cases()
    assert [item.source_rate.to_rational() for item in cases] == [
        "30/1",
        "60/1",
        "30000/1001",
    ]
    assert len({item.asset_id for item in cases}) == len(cases)


def test_native_case_builds_approved_edit_and_deterministic_assembly():
    case = Task010NativeCase(
        "UNIT_SRC60_TL30",
        "ASSET-00000000000000000000000077",
        FrameRate(60),
    )
    edit = build_task010_edit_plan(case)
    edit2, assembly = build_task010_assembly_plan(case, timeline_rate=FrameRate(30))
    assert edit.to_dict() == edit2.to_dict()
    assert edit.ready_for_assembly is True
    assert [(row.start_us, row.end_us) for row in edit.keep_ranges] == [
        (0, 1_000_000),
        (2_000_000, 4_000_000),
    ]
    assert assembly.timeline_name.startswith("BAI_AUTO_")
    assert assembly.expected_duration_frames == 90


def test_native_gate_rejects_non_sandbox_name(tmp_path: Path):
    with pytest.raises(ValueError):
        Task010NativeGateRunner(
            sandbox_project="CLIENT_PROJECT",
            evidence_root=tmp_path,
        )


class _Project:
    def __init__(self, name: str):
        self.name = name
    def GetName(self):
        return self.name


class _Manager:
    def __init__(self, project):
        self.project = project
    def GetCurrentProject(self):
        return self.project


class _Resolve:
    def __init__(self, project):
        self.manager = _Manager(project)
    def GetProjectManager(self):
        return self.manager


class _Loader:
    def __init__(self, project_name: str):
        self.resolve = _Resolve(_Project(project_name))
    def connect(self):
        return self.resolve, "TEST"


def test_native_gate_requires_exact_current_sandbox(tmp_path: Path):
    runner = Task010NativeGateRunner(
        sandbox_project="BAI_CAPABILITY_PROBE_EXPECTED",
        evidence_root=tmp_path,
        loader=_Loader("BAI_CAPABILITY_PROBE_OTHER"),
    )
    with pytest.raises(ProductError) as exc:
        runner._project()
    assert exc.value.code == "ERR_TASK010_NATIVE_SANDBOX_MISMATCH"

def test_native_fixture_uses_explicit_default_qa_compatible_gain(tmp_path: Path):
    runner = Task010NativeGateRunner(
        sandbox_project="BAI_CAPABILITY_PROBE_FIXTURE_GAIN",
        evidence_root=tmp_path / "evidence",
    )
    observed: list[str] = []

    def fake_run(argv: list[str], *, timeout_seconds: int = 120):
        observed.extend(argv)
        Path(argv[-1]).write_bytes(b"fixture")
        return subprocess.CompletedProcess(argv, 0, "", "")

    runner._run = fake_run  # type: ignore[method-assign]
    target = tmp_path / "fixture.mp4"
    runner._generate_source(task010_native_cases()[0], target)

    filter_index = observed.index("-af")
    assert observed[filter_index + 1] == "volume=1.0dB"
    assert filter_index > observed.index("sine=frequency=1000:sample_rate=48000:duration=4.000000")
    assert target.read_bytes() == b"fixture"
