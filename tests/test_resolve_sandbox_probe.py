from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.resolve_sandbox_probe import run_resolve_sandbox_probe
from ai_video_production.schema_contracts import validate_instance

ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "resolve-capability-report.schema.json"


class Timeline:
    def AddMarker(self, *args):
        return True


class MediaPool:
    def __init__(self):
        self.timeline = Timeline()
    def GetRootFolder(self):
        return object()
    def AddSubFolder(self, root, name):
        return object()
    def ImportMedia(self, paths):
        assert paths and paths[0].endswith('.wav')
        return [object()]
    def CreateEmptyTimeline(self, name):
        return self.timeline
    def AppendToTimeline(self, items):
        return [object()] if items else []


class Project:
    def __init__(self, name):
        self.name = name
        self.pool = MediaPool()
    def GetName(self):
        return self.name
    def GetMediaPool(self):
        return self.pool
    def GetCurrentTimeline(self):
        return self.pool.timeline
    def SetRenderSettings(self, *args):
        return True
    def AddRenderJob(self, *args):
        return 'job'
    def StartRendering(self, *args):
        return True
    def GetRenderJobStatus(self, *args):
        return {}
    def StopRendering(self, *args):
        return True


class ProjectManager:
    def __init__(self, current=None):
        self.current = current
    def GetCurrentProject(self):
        return self.current
    def CreateProject(self, name):
        self.current = Project(name)
        return self.current
    def LoadProject(self, name):
        return self.current if self.current and self.current.GetName() == name else None
    def SaveProject(self):
        return True
    def ExportProject(self, name, path):
        Path(path).write_bytes(b'fake-drp')
        return True


class Resolve:
    def __init__(self, current=None):
        self.pm = ProjectManager(current)
    def GetProjectManager(self):
        return self.pm
    def GetVersionString(self):
        return '21.0.2.4'
    def GetVersion(self):
        return [21, 0, 2, 4, '']
    def GetProductName(self):
        return 'DaVinci Resolve Studio'


def caps(report):
    return {r['capability_id']: r for r in report['capabilities']}


def test_sandbox_probe_executes_only_isolated_minimum_sequence(tmp_path):
    assets = tmp_path / "probe-assets"
    report = run_resolve_sandbox_probe(
        Resolve(),
        module_source_kind='TEST',
        sandbox_project='BAI_CAPABILITY_PROBE_UNIT',
        probe_assets_dir=assets,
    )
    validate_instance(report, SCHEMA)
    rows = caps(report)
    for cap in ('project.create','project.open','project.save','project.snapshot','bin.ensure','media.import','timeline.create','timeline.build','timeline.markers'):
        assert rows[cap]['status'] == 'SUPPORTED'
    assert rows['render.start']['status'] == 'PROBE_REQUIRED'
    assert rows['render.cancel']['status'] == 'PROBE_REQUIRED'
    assert rows['media.relink']['status'] == 'PROBE_REQUIRED'
    assert report['mode'] == 'SANDBOX_MUTATION'
    assert report['summary']['mutation_probe_executed'] is True
    assert report['mutation_gate']['executed'] is True
    assert (assets / 'task002_probe.wav').is_file()
    assert (assets / 'sandbox.drp').is_file()


def test_sandbox_probe_refuses_non_sandbox_current_project_before_mutation(tmp_path):
    with pytest.raises(ProductError) as exc:
        run_resolve_sandbox_probe(
            Resolve(Project('CLIENT_PROJECT')),
            module_source_kind='TEST',
            sandbox_project='BAI_CAPABILITY_PROBE_UNIT',
            probe_assets_dir=tmp_path / 'assets',
        )
    assert exc.value.code == 'ERR_RESOLVE_EXISTING_PROJECT_PROTECTED'

class UnnamedProject:
    def GetMediaPool(self):
        raise AssertionError("must not be called when current Project name is unverifiable")


def test_sandbox_probe_fails_closed_when_current_project_name_cannot_be_verified(tmp_path):
    with pytest.raises(ProductError) as exc:
        run_resolve_sandbox_probe(
            Resolve(UnnamedProject()),
            module_source_kind='TEST',
            sandbox_project='BAI_CAPABILITY_PROBE_UNIT',
            probe_assets_dir=tmp_path / 'assets',
        )
    assert exc.value.code == 'ERR_RESOLVE_CURRENT_PROJECT_NAME_UNVERIFIED'

class CreateUnnamedProjectManager(ProjectManager):
    def CreateProject(self, name):
        self.current = UnnamedProject()
        return self.current


class ResolveCreatesUnnamed(Resolve):
    def __init__(self):
        self.pm = CreateUnnamedProjectManager()


def test_sandbox_probe_stops_after_creation_if_created_project_identity_is_unverifiable(tmp_path):
    with pytest.raises(ProductError) as exc:
        run_resolve_sandbox_probe(
            ResolveCreatesUnnamed(),
            module_source_kind='TEST',
            sandbox_project='BAI_CAPABILITY_PROBE_UNIT',
            probe_assets_dir=tmp_path / 'assets',
        )
    assert exc.value.code == 'ERR_RESOLVE_SANDBOX_IDENTITY_UNVERIFIED'

def test_sandbox_probe_resolves_relative_asset_paths_before_resolve_api_calls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    observed: dict[str, str] = {}

    class AbsolutePathMediaPool(MediaPool):
        def ImportMedia(self, paths):
            assert paths
            observed["import"] = paths[0]
            assert Path(paths[0]).is_absolute()
            return [object()]

    class AbsolutePathProject(Project):
        def __init__(self, name):
            self.name = name
            self.pool = AbsolutePathMediaPool()

    class AbsolutePathProjectManager(ProjectManager):
        def CreateProject(self, name):
            self.current = AbsolutePathProject(name)
            return self.current

        def ExportProject(self, name, path):
            observed["export"] = path
            assert Path(path).is_absolute()
            Path(path).write_bytes(b"fake-drp")
            return True

    class AbsolutePathResolve(Resolve):
        def __init__(self):
            self.pm = AbsolutePathProjectManager()

    report = run_resolve_sandbox_probe(
        AbsolutePathResolve(),
        module_source_kind="TEST",
        sandbox_project="BAI_CAPABILITY_PROBE_RELATIVE_PATH",
        probe_assets_dir=Path("relative-probe-assets"),
    )

    rows = caps(report)

    assert rows["project.snapshot"]["status"] == "SUPPORTED"
    assert rows["media.import"]["status"] == "SUPPORTED"
    assert Path(observed["export"]).is_absolute()
    assert Path(observed["import"]).is_absolute()
    assert (tmp_path / "relative-probe-assets" / "sandbox.drp").is_file()
    assert (tmp_path / "relative-probe-assets" / "task002_probe.wav").is_file()
