from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.task011_native_render_gate import (
    Task011NativeRenderGateRunner,
    Task011NativeRenderRequest,
)


TIMELINE = "BAI_AUTO_0123456789AB"


class FakeTimeline:
    def __init__(self, name: str):
        self.name = name

    def GetName(self):
        return self.name


class FakeProject:
    def __init__(self, artifact_factory, *, name="BAI_CAPABILITY_PROBE_TASK011_TEST", timelines=None, job_status="Complete"):
        self.name = name
        self.timelines = timelines or [FakeTimeline(TIMELINE)]
        self.artifact_factory = artifact_factory
        self.render_settings = None
        self.selected = None
        self.started = False
        self.stopped = False
        self.job_status = job_status

    def GetName(self):
        return self.name

    def GetTimelineCount(self):
        return len(self.timelines)

    def GetTimelineByIndex(self, index):
        return self.timelines[index - 1]

    def GetSetting(self, key):
        return "29.97" if key == "timelineFrameRate" else None

    def SetCurrentTimeline(self, timeline):
        self.selected = timeline
        return True

    def SetRenderSettings(self, settings):
        self.render_settings = dict(settings)
        return True

    def AddRenderJob(self):
        return "job-uuid-1"

    def StartRendering(self, job_id):
        assert job_id == "job-uuid-1"
        self.started = True
        target = Path(self.render_settings["TargetDir"])
        self.artifact_factory(target)
        return True

    def IsRenderingInProgress(self):
        return False

    def GetRenderJobStatus(self, job_id):
        return {"JobStatus": self.job_status, "CompletionPercentage": 100}

    def StopRendering(self):
        self.stopped = True
        return None


class FakeManager:
    def __init__(self, project):
        self.project = project

    def GetCurrentProject(self):
        return self.project


class FakeResolve:
    def __init__(self, project):
        self.project = project

    def GetProjectManager(self):
        return FakeManager(self.project)


class FakeLoader:
    def __init__(self, project):
        self.project = project

    def connect(self):
        return FakeResolve(self.project), "FAKE"


class FakeQAReport:
    status = "PASS"

    def to_dict(self):
        return {
            "report_version": "1.0.0",
            "status": "PASS",
            "artifact_sha256": "sha256:" + "a" * 64,
            "artifact_size_bytes": 12,
            "render_path_persisted": False,
            "report_sha256": "sha256:" + "b" * 64,
        }


class FakeQA:
    def __init__(self):
        self.calls = []

    def verify(self, path, **kwargs):
        self.calls.append((Path(path), kwargs))
        return FakeQAReport()


def one_artifact(target: Path):
    target.mkdir(parents=True, exist_ok=True)
    (target / "BAI_TASK011_NATIVE_RENDER.mp4").write_bytes(b"render-bytes")


def two_artifacts(target: Path):
    target.mkdir(parents=True, exist_ok=True)
    (target / "one.mov").write_bytes(b"1")
    (target / "two.wav").write_bytes(b"2")


def request(tmp_path: Path):
    return Task011NativeRenderRequest(
        sandbox_project="BAI_CAPABILITY_PROBE_TASK011_TEST",
        timeline_name=TIMELINE,
        expected_duration_frames=90,
        evidence_root=tmp_path / "evidence",
    )


def test_task011_native_gate_requires_explicit_authorization(tmp_path: Path):
    project = FakeProject(one_artifact)
    gate = Task011NativeRenderGateRunner(request(tmp_path), loader=FakeLoader(project), qa_service=FakeQA())
    with pytest.raises(ProductError) as exc:
        gate.run(explicit_external_write_authorization=False, output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK011_NATIVE_RENDER_NOT_AUTHORIZED"
    assert project.render_settings is None


def test_task011_native_gate_rejects_wrong_project_before_render_mutation(tmp_path: Path):
    project = FakeProject(one_artifact, name="OTHER_PROJECT")
    gate = Task011NativeRenderGateRunner(request(tmp_path), loader=FakeLoader(project), qa_service=FakeQA())
    with pytest.raises(ProductError) as exc:
        gate.run(explicit_external_write_authorization=True, output_path=tmp_path / "report.json")
    assert exc.value.code in {"ERR_RESOLVE_MUTATION_SANDBOX_MISMATCH", "ERR_RESOLVE_EXISTING_PROJECT_PROTECTED", "ERR_TASK011_NATIVE_SANDBOX_MISMATCH"}
    assert project.render_settings is None


def test_task011_native_gate_requires_exact_unique_automation_timeline(tmp_path: Path):
    project = FakeProject(one_artifact, timelines=[FakeTimeline("OTHER")])
    gate = Task011NativeRenderGateRunner(request(tmp_path), loader=FakeLoader(project), qa_service=FakeQA())
    with pytest.raises(ProductError) as exc:
        gate.run(explicit_external_write_authorization=True, output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK011_NATIVE_TIMELINE_NOT_FOUND"


def test_task011_native_gate_renders_single_artifact_and_runs_qa(tmp_path: Path):
    project = FakeProject(one_artifact)
    qa = FakeQA()
    gate = Task011NativeRenderGateRunner(request(tmp_path), loader=FakeLoader(project), qa_service=qa)
    report = gate.run(explicit_external_write_authorization=True, output_path=tmp_path / "report.json")
    assert report["status"] == "PASS"
    assert report["project_timeline_rate"] == {"numerator": 30000, "denominator": 1001}
    assert report["render_artifact"]["path_persisted"] is False
    assert report["render_job"]["id_persisted"] is False
    assert len(qa.calls) == 1
    assert qa.calls[0][1]["expected_duration_frames"] == 90
    assert (tmp_path / "report.json").is_file()


def test_task011_native_gate_fails_closed_on_ambiguous_artifacts(tmp_path: Path):
    project = FakeProject(two_artifacts)
    gate = Task011NativeRenderGateRunner(request(tmp_path), loader=FakeLoader(project), qa_service=FakeQA())
    with pytest.raises(ProductError) as exc:
        gate.run(explicit_external_write_authorization=True, output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK011_NATIVE_RENDER_ARTIFACT_AMBIGUOUS"


def test_task011_native_gate_refuses_nonempty_render_directory_before_queue_mutation(tmp_path: Path):
    req = request(tmp_path)
    render_dir = req.evidence_root / "render-output"
    render_dir.mkdir(parents=True)
    (render_dir / "old.mov").write_bytes(b"old")
    project = FakeProject(one_artifact)
    gate = Task011NativeRenderGateRunner(req, loader=FakeLoader(project), qa_service=FakeQA())
    with pytest.raises(ProductError) as exc:
        gate.run(explicit_external_write_authorization=True, output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK011_NATIVE_RENDER_DIR_NOT_EMPTY"
    assert project.render_settings is None


def test_task011_native_request_can_be_bound_to_task010_assembly_plan(tmp_path: Path):
    from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
    import json

    plan = tmp_path / "assembly.json"
    body = {
        "task_owner": "TASK-010",
        "timeline_name": "BAI_AUTO_0123456789AB",
        "expected_duration_frames": 123,
    }
    body["assembly_sha256"] = sha256_bytes(canonical_json_bytes(body))
    plan.write_text(json.dumps(body), encoding="utf-8")
    req = Task011NativeRenderRequest.from_assembly_plan(
        plan,
        sandbox_project="BAI_CAPABILITY_PROBE_TASK011_TEST",
        evidence_root=tmp_path / "evidence",
    )
    assert req.timeline_name == TIMELINE
    assert req.expected_duration_frames == 123
    assert req.assembly_sha256 == body["assembly_sha256"]


def test_task011_native_gate_preflights_status_api_before_any_render_mutation(tmp_path: Path):
    project = FakeProject(one_artifact)
    project.GetRenderJobStatus = None
    gate = Task011NativeRenderGateRunner(request(tmp_path), loader=FakeLoader(project), qa_service=FakeQA())
    with pytest.raises(ProductError) as exc:
        gate.run(explicit_external_write_authorization=True, output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK011_NATIVE_RENDER_STATUS_API_UNAVAILABLE"
    assert project.selected is None
    assert project.render_settings is None
    assert project.started is False


def test_task011_native_gate_rejects_report_inside_render_directory_before_mutation(tmp_path: Path):
    project = FakeProject(one_artifact)
    req = request(tmp_path)
    gate = Task011NativeRenderGateRunner(req, loader=FakeLoader(project), qa_service=FakeQA())
    with pytest.raises(ProductError) as exc:
        gate.run(
            explicit_external_write_authorization=True,
            output_path=req.evidence_root / "render-output" / "report.json",
        )
    assert exc.value.code == "ERR_TASK011_NATIVE_REPORT_LOCATION_INVALID"
    assert project.selected is None
    assert project.render_settings is None
    assert project.started is False


def test_task011_native_gate_best_effort_stops_if_progress_query_fails_after_dispatch(tmp_path: Path):
    project = FakeProject(one_artifact)

    def fail_progress():
        raise RuntimeError("bridge failure")

    project.IsRenderingInProgress = fail_progress
    gate = Task011NativeRenderGateRunner(request(tmp_path), loader=FakeLoader(project), qa_service=FakeQA())
    with pytest.raises(ProductError) as exc:
        gate.run(explicit_external_write_authorization=True, output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK011_NATIVE_RENDER_PROGRESS_FAILED"
    assert project.started is True
    assert project.stopped is True


def test_task011_native_gate_accepts_cp932_status_mojibake_from_localized_resolve(tmp_path: Path):
    # CP932 bytes for Japanese "完了" decoded through CP1250 by the bridge.
    project = FakeProject(one_artifact, job_status="Š®—ą")
    qa = FakeQA()
    gate = Task011NativeRenderGateRunner(request(tmp_path), loader=FakeLoader(project), qa_service=qa)
    report = gate.run(explicit_external_write_authorization=True, output_path=tmp_path / "report.json")
    assert report["status"] == "PASS"
    assert report["render_job"]["status"] == "Complete"
    assert len(qa.calls) == 1
