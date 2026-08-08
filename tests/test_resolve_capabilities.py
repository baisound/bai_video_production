from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.resolve_capabilities import (
    CAPABILITY_SPECS,
    CapabilityStatus,
    ResolveCapabilityProbe,
    authorize_mutation_probe,
)
from ai_video_production.schema_contracts import validate_instance

ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "resolve-capability-report.schema.json"


class FakeTimeline:
    def AddMarker(self, *args):
        return True


class FakeMediaPool:
    def ImportMedia(self, *args):
        return []

    def RelinkClips(self, *args):
        return True

    def AddSubFolder(self, *args):
        return object()

    def CreateEmptyTimeline(self, *args):
        return FakeTimeline()

    def AppendToTimeline(self, *args):
        return []


class FakeProject:
    def __init__(self, *, fail_media_pool=False):
        self._fail_media_pool = fail_media_pool

    def GetMediaPool(self):
        if self._fail_media_pool:
            raise RuntimeError("probe fixture failure")
        return FakeMediaPool()

    def GetCurrentTimeline(self):
        return FakeTimeline()

    def SetRenderSettings(self, *args):
        return True

    def AddRenderJob(self, *args):
        return "job"

    def StartRendering(self, *args):
        return True

    def GetRenderJobStatus(self, *args):
        return {}

    def StopRendering(self, *args):
        return True


class FakeProjectManager:
    def __init__(self, project=None):
        self.project = project

    def GetCurrentProject(self):
        return self.project

    def CreateProject(self, *args):
        return self.project

    def LoadProject(self, *args):
        return self.project

    def SaveProject(self):
        return True

    def ExportProject(self, *args):
        return True


class FakeResolve:
    def __init__(self, project=None):
        self.pm = FakeProjectManager(project)

    def GetVersionString(self):
        return "21.0.3"

    def GetVersion(self):
        return [21, 0, 3, 0, ""]

    def GetProductName(self):
        return "DaVinci Resolve Studio"

    def GetProjectManager(self):
        return self.pm


def by_id(report):
    return {row["capability_id"]: row for row in report["capabilities"]}


def test_read_only_fake_resolve_supports_only_executed_safe_queries():
    report = ResolveCapabilityProbe(FakeResolve(FakeProject()), module_source_kind="TEST").run()
    validate_instance(report, SCHEMA)
    caps = by_id(report)
    assert caps["resolve.connection"]["status"] == CapabilityStatus.SUPPORTED.value
    assert caps["resolve.version"]["status"] == CapabilityStatus.SUPPORTED.value
    assert caps["project_manager.access"]["status"] == CapabilityStatus.SUPPORTED.value
    assert caps["project.current"]["status"] == CapabilityStatus.SUPPORTED.value
    assert caps["media_pool.access"]["status"] == CapabilityStatus.SUPPORTED.value
    assert caps["timeline.current"]["status"] == CapabilityStatus.SUPPORTED.value
    assert caps["project.save"]["status"] == CapabilityStatus.PROBE_REQUIRED.value
    assert caps["timeline.create"]["status"] == CapabilityStatus.PROBE_REQUIRED.value
    assert report["summary"]["mutation_probe_executed"] is False


def test_no_current_project_is_valid_but_dependent_capabilities_remain_unresolved():
    report = ResolveCapabilityProbe(FakeResolve(None), module_source_kind="TEST").run()
    caps = by_id(report)
    assert caps["project.current"]["status"] == "SUPPORTED"
    assert caps["project.current"]["return_kind"] == "NONE"
    assert caps["media_pool.access"]["status"] == "PROBE_REQUIRED"
    assert caps["timeline.current"]["status"] == "PROBE_REQUIRED"
    assert caps["timeline.create"]["status"] == "PROBE_REQUIRED"


def test_failing_safe_accessor_does_not_promote_capability():
    report = ResolveCapabilityProbe(FakeResolve(FakeProject(fail_media_pool=True)), module_source_kind="TEST").run()
    caps = by_id(report)
    assert caps["media_pool.access"]["status"] == "PROBE_REQUIRED"
    assert caps["media_pool.access"]["error_type"] == "RuntimeError"
    assert caps["timeline.current"]["status"] == "SUPPORTED"


def test_disconnected_report_is_schema_valid_and_not_false_supported():
    report = ResolveCapabilityProbe(None, module_source_kind="NOT_FOUND").run()
    validate_instance(report, SCHEMA)
    caps = by_id(report)
    assert caps["resolve.connection"]["status"] == "PROBE_REQUIRED"
    assert report["summary"]["live_resolve_connected"] is False


def test_mutation_guard_requires_explicit_permission_and_sandbox():
    with pytest.raises(ProductError) as exc:
        authorize_mutation_probe(allow_mutation=False, sandbox_project="BAI_CAPABILITY_PROBE_X", current_project_name=None)
    assert exc.value.code == "ERR_RESOLVE_MUTATION_NOT_AUTHORIZED"

    with pytest.raises(ProductError) as exc:
        authorize_mutation_probe(allow_mutation=True, sandbox_project="MY_REAL_PROJECT", current_project_name=None)
    assert exc.value.code == "ERR_RESOLVE_SANDBOX_REQUIRED"

    with pytest.raises(ProductError) as exc:
        authorize_mutation_probe(allow_mutation=True, sandbox_project="BAI_CAPABILITY_PROBE_X", current_project_name="CLIENT_PROJECT")
    assert exc.value.code == "ERR_RESOLVE_EXISTING_PROJECT_PROTECTED"

    assert authorize_mutation_probe(
        allow_mutation=True,
        sandbox_project="BAI_CAPABILITY_PROBE_X",
        current_project_name="BAI_CAPABILITY_PROBE_OLD",
    ) == "BAI_CAPABILITY_PROBE_X"


def test_capability_contract_has_unique_ids_and_manual_fallbacks():
    ids = [spec.capability_id for spec in CAPABILITY_SPECS]
    assert len(ids) == len(set(ids))
    assert {"project.create", "media.import", "timeline.build", "timeline.markers", "timeline.subtitles", "render.submit"} <= set(ids)
    assert all(spec.fallback for spec in CAPABILITY_SPECS)


def test_absent_candidate_method_does_not_false_classify_unsupported():
    class MinimalProjectManager:
        def GetCurrentProject(self):
            return None

    class MinimalResolve:
        def GetProjectManager(self):
            return MinimalProjectManager()

    report = ResolveCapabilityProbe(MinimalResolve(), module_source_kind="TEST").run()
    caps = by_id(report)
    assert caps["resolve.version"]["status"] == "PROBE_REQUIRED"
    assert caps["project.create"]["status"] == "PROBE_REQUIRED"
    assert caps["project.create"]["observed_methods"] == []
    assert report["summary"]["unsupported"] == 0
