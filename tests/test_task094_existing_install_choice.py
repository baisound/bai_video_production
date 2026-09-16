from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "packaging" / "task094_existing_install_choice.iss"
INSTALLERS = (
    ROOT / "packaging" / "task063_main_installer.iss",
    ROOT / "packaging" / "task092_dbd_utility_installer.iss",
    ROOT / "packaging" / "task046_voice_model_builder_installer.iss",
    ROOT / "packaging" / "task047_obs_voice_capture_installer.iss",
    ROOT / "packaging" / "task093_owner_voice_runtime_installer.iss",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_all_six_installer_outputs_show_destination_and_share_choice_page() -> None:
    for installer in INSTALLERS:
        text = _text(installer)
        assert "DisableDirPage=no" in text, installer.name
        assert '#include "task094_existing_install_choice.iss"' in text, installer.name
        assert "Task094InitializeExistingInstallChoice" in text, installer.name
        assert "Task094ShouldSkipExistingInstallPage" in text, installer.name
        assert "Task094ExistingInstallChoiceNext" in text, installer.name
        assert "Task094PrepareExistingInstall" in text, installer.name
        assert "#ifndef AppIdValue" in text, installer.name
        assert "AppId={{{#AppIdValue}}" in text, installer.name
        assert "ja.ExistingInstallUpdate=" in text, installer.name
        assert "ja.ExistingInstallUninstall=" in text, installer.name
        assert "ja.ExistingInstallCancel=" in text, installer.name


def test_shared_choice_detects_registered_and_partial_installs() -> None:
    text = _text(SHARED)
    assert "RegQueryStringValue(HKCU" in text
    assert "InstallLocation" in text
    assert "unins000.exe" in text
    assert "Task094ExistingInstallMarker" in text
    assert "Task094RootContainsProduct(Task094RequestedInstallRoot)" in text
    assert "Task094RootContainsProduct(RegisteredRoot)" in text


def test_update_is_same_location_and_uninstall_is_explicit_one_shot() -> None:
    text = _text(SHARED)
    assert "WizardForm.DirEdit.Text := Task094DetectedInstallRoot" in text
    assert "Task094ExistingInstallAction := 1" in text
    assert "Task094UninstallCompleted" in text
    assert "ewWaitUntilTerminated" in text
    assert "ResultCode <> 0" in text
    assert "WizardSilent" in text
    assert "WizardForm.Close" in text


def test_main_installer_does_not_call_unavailable_bridge_mutation() -> None:
    text = _text(INSTALLERS[0])
    assert "--bvp-installer-bridge" not in text
    assert "TASK-063 private Bridge composition remains gated" in text


def test_obs_known_repository_locale_revision_is_safe_prior_input() -> None:
    text = _text(INSTALLERS[3])
    en = ROOT / "native/task047_obs_voice_capture/resources/locale/en-US.ini"
    ja = ROOT / "native/task047_obs_voice_capture/resources/locale/ja-JP.ini"
    import hashlib

    assert hashlib.sha256(en.read_bytes()).hexdigest() in text
    assert hashlib.sha256(ja.read_bytes()).hexdigest() in text
    assert "ExistingFileIsAllowed(Target2, '{#EnSha}', '{#PreviousEnSha}'" in text
    assert "ExistingFileIsAllowed(Target3, '{#JaSha}', '{#PreviousJaSha}'" in text
