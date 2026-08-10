from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "tools" / "ci" / "check-release-metadata.py"
SPEC = spec_from_file_location("release_metadata", SCRIPT)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_product_change_classification() -> None:
    assert MODULE.is_product_change("src/ai_video_production/example.py")
    assert MODULE.is_product_change("tools/windows/run.ps1")
    assert not MODULE.is_product_change("docs/design/example.md")
    assert not MODULE.is_product_change("tests/test_example.py")
    assert not MODULE.is_product_change(".github/dependabot.yml")


def test_release_versions_are_consistent() -> None:
    values = MODULE.versions()
    assert len(set(values.values())) == 1
