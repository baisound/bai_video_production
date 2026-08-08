from types import SimpleNamespace

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.resolve_loader import ResolveModuleDiscovery, ResolveModuleLoader


def test_loader_uses_existing_import_without_network(monkeypatch):
    fake = SimpleNamespace(scriptapp=lambda name: object() if name == "Resolve" else None)
    monkeypatch.setattr(ResolveModuleLoader, "_import_existing", staticmethod(lambda: fake))
    resolve, source = ResolveModuleLoader(platform_name="Linux", environ={}).connect()
    assert resolve is not None
    assert source == "PYTHON_IMPORT_PATH"


def test_loader_fails_closed_when_module_missing(monkeypatch):
    monkeypatch.setattr(ResolveModuleLoader, "_import_existing", staticmethod(lambda: None))
    monkeypatch.setattr(ResolveModuleLoader, "_candidate_dirs", lambda self: iter(()))
    with pytest.raises(ProductError) as exc:
        ResolveModuleLoader(platform_name="Linux", environ={}).discover()
    assert exc.value.code == "ERR_RESOLVE_SCRIPT_MODULE_NOT_FOUND"


def test_connect_rejects_module_without_scriptapp(monkeypatch):
    loader = ResolveModuleLoader(platform_name="Linux", environ={})
    monkeypatch.setattr(loader, "discover", lambda: ResolveModuleDiscovery(SimpleNamespace(), "TEST"))
    with pytest.raises(ProductError) as exc:
        loader.connect()
    assert exc.value.code == "ERR_RESOLVE_SCRIPTAPP_MISSING"


def test_connect_none_is_retryable_dependency_error(monkeypatch):
    loader = ResolveModuleLoader(platform_name="Linux", environ={})
    monkeypatch.setattr(loader, "discover", lambda: ResolveModuleDiscovery(SimpleNamespace(scriptapp=lambda _name: None), "TEST"))
    with pytest.raises(ProductError) as exc:
        loader.connect()
    assert exc.value.code == "ERR_RESOLVE_NOT_AVAILABLE"
    assert exc.value.retryable is True


def test_loader_does_not_hide_bridge_dependency_import_failure(monkeypatch):
    def fail_import():
        raise ModuleNotFoundError("missing bridge dependency", name="fusionscript")

    monkeypatch.setattr(ResolveModuleLoader, "_import_existing", staticmethod(fail_import))
    with pytest.raises(ProductError) as exc:
        ResolveModuleLoader(platform_name="Windows", environ={}).discover()
    assert exc.value.code == "ERR_RESOLVE_SCRIPT_MODULE_IMPORT_FAILED"
    assert exc.value.details["exception_type"] == "ModuleNotFoundError"
