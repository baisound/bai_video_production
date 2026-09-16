from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "tools/windows/install-owner-voice-runtime.ps1"
INSTALLER = ROOT / "packaging/task093_owner_voice_runtime_installer.iss"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_application_and_private_data_roots_have_distinct_safety_rules() -> None:
    text = _text(BOOTSTRAP)
    assert "function Resolve-SafeInstallRoot" in text
    assert "$safeInstallRoot = Resolve-SafeInstallRoot $InstallRoot" in text
    assert "$safeDataRoot = Resolve-SafeRoot $DataRoot 'DataRoot'" in text
    assert "$safeConfigRoot = Resolve-SafeRoot $ConfigRoot 'ConfigRoot'" in text
    install_function = text.split("function Resolve-SafeInstallRoot", 1)[1].split(
        "function Invoke-Checked", 1
    )[0]
    assert "InstallRoot cannot be a drive root" in install_function
    assert "direct child" not in install_function
    data_function = text.split("function Resolve-SafeRoot", 1)[1].split(
        "function Resolve-SafeInstallRoot", 1
    )[0]
    assert "cannot be a drive root or direct child" in data_function


def test_bootstrap_diagnostics_are_available_before_install_root_validation() -> None:
    text = _text(BOOTSTRAP)
    assert text.index("$script:BootstrapErrorPath =") < text.index(
        "$safeInstallRoot = Resolve-SafeInstallRoot"
    )
    installer = _text(INSTALLER)
    assert "bootstrap-last-error.json" in installer
    assert "Owner Voice runtime bootstrap failed: exit_code=%d" in installer
