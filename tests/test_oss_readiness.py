from pathlib import Path
import re

import ai_video_production


ROOT = Path(__file__).resolve().parents[1]


def test_public_repository_documents_exist_and_are_nonempty() -> None:
    required = {
        "README.md", "LICENSE.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
        "SECURITY.md", "GOVERNANCE.md", "SUPPORT.md", "CHANGELOG.md",
        "THIRD_PARTY_NOTICES.md", "CITATION.cff",
    }
    for name in required:
        assert (ROOT / name).stat().st_size > 100, name


def test_package_and_citation_versions_match() -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f'version: "{ai_video_production.__version__}"' in citation


def test_public_metadata_uses_canonical_repository_url() -> None:
    canonical = "https://github.com/baisound/bai_video_production"
    files = ["README.md", "pyproject.toml", "CITATION.cff", ".github/ISSUE_TEMPLATE/config.yml"]
    combined = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in files)
    assert canonical in combined
    assert "https://github.com/baisound/ai-video-production" not in combined


def test_license_and_project_metadata_are_public_ready() -> None:
    license_text = (ROOT / "LICENSE.md").read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert 'readme = "README.md"' in project
    assert 'license = { file = "LICENSE.md" }' in project
    assert f'version = "{ai_video_production.__version__}"' in project


def test_readme_local_markdown_links_resolve() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)
    local_links = [link for link in links if "://" not in link and not link.startswith("#")]
    assert local_links
    for link in local_links:
        assert (ROOT / link.split("#", 1)[0]).exists(), link


def test_github_community_health_files_exist() -> None:
    required = {
        ".github/CODEOWNERS",
        ".github/dependabot.yml",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/provider_request.yml",
    }
    assert all((ROOT / path).is_file() for path in required)


def test_ci_is_offline_first_and_cross_platform() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "ubuntu-latest" in ci and "windows-latest" in ci
    assert "python -m pytest -q" in ci
    assert "python -m compileall -q src tests" in ci
    assert "sudo apt-get update && sudo apt-get install --yes ffmpeg" in ci
    assert "choco install ffmpeg --yes --no-progress" in ci
    assert "ffprobe -version" in ci
    assert "behavior-probe" not in ci


def test_security_automation_is_present() -> None:
    workflow = (ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")
    assert "pip-audit" in workflow
    assert "gitleaks/gitleaks-action" in workflow
    assert "permissions:\n  contents: read" in workflow


def test_secret_and_runtime_output_patterns_are_ignored() -> None:
    patterns = set((ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
    assert {".env", ".env.*", "!.env.example", "*.log", "/task*-live-evidence*/"} <= patterns


def test_impact_claims_are_bounded_by_evidence() -> None:
    readiness = (ROOT / "docs/oss/CODEX-FOR-OSS-READINESS.md").read_text(encoding="utf-8")
    assert "intended impact, not a claim of demonstrated scale" in readiness
    assert "Never invent usage" in readiness
