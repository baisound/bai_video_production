from pathlib import Path
import re

import ai_video_production


ROOT = Path(__file__).resolve().parents[1]


def test_public_repository_documents_exist_and_are_nonempty() -> None:
    required = {
        "README.md", "README.en.md", "LICENSE.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
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
    for name in ("README.md", "README.en.md"):
        readme = (ROOT / name).read_text(encoding="utf-8")
        links = re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)
        local_links = [link for link in links if "://" not in link and not link.startswith("#")]
        assert local_links
        for link in local_links:
            assert (ROOT / link.split("#", 1)[0]).exists(), f"{name}: {link}"


def test_japanese_and_english_readmes_link_to_each_other() -> None:
    japanese = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")
    assert "[English](README.en.md)" in japanese
    assert "[日本語](README.md)" in english
    for required in ("Expected public impact", "Architecture", "Five-minute"):
        assert required in english


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
    assert "timeout-minutes: 20" in ci
    assert "pytest-xdist==3.8.0 pytest-timeout==2.4.0" in ci
    assert "python -m pytest -q -n 2 --dist loadfile" in ci
    assert "--timeout=120 --max-worker-restart=0 --durations=20" in ci
    assert "python -m compileall -q src tests" in ci
    assert "sudo apt-get update && sudo apt-get install --yes ffmpeg" in ci
    assert "https://packages.chocolatey.org/ffmpeg.8.1.2.nupkg" in ci
    assert "6c5746c8f0da8334d367131012ec1280bdd490651e108c35e19933587b06aed8" in ci
    assert 'choco install ffmpeg --version=8.1.2 --source="$env:RUNNER_TEMP" --yes --no-progress' in ci
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

def test_every_windows_executable_or_installer_has_a_dedicated_build_guide() -> None:
    targets = {
        "build-windows-exe.bat": "docs/windows/BUILDING-WINDOWS-EXE.md",
        "build-dbd-training-studio-exe.bat": "docs/windows/BUILDING-DBD-TRAINING-STUDIO-EXE.md",
        "build-dbd-trivia-editor-exe.bat": "docs/windows/BUILDING-DBD-TRIVIA-EDITOR-EXE.md",
        "tools/windows/build-task046-voice-model-builder-installer.ps1": "docs/windows/BUILDING-VOICE-MODEL-BUILDER-INSTALLER.md",
        "tools/windows/build-task047-obs-installer.ps1": "docs/windows/BUILDING-OBS-VOICE-CAPTURE-INSTALLER.md",
    }
    for builder, guide in targets.items():
        assert (ROOT / builder).is_file(), builder
        assert (ROOT / guide).is_file(), guide
        assert (ROOT / guide).stat().st_size > 500, guide

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/windows/WINDOWS-EXE-BUILD-INDEX.md" in readme
    assert "docs/windows/WINDOWS-GAME-INTELLIGENCE-ENVIRONMENT.md" in readme

    index = (ROOT / "docs/windows/WINDOWS-EXE-BUILD-INDEX.md").read_text(encoding="utf-8")
    for guide in targets.values():
        assert Path(guide).name in index, guide
