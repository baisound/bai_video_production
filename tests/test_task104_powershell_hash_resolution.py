from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "native/task047_obs_voice_capture/scripts/build-controller.ps1"


def _shells() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, binary in (("windows-powershell", "powershell.exe"), ("powershell-7", "pwsh.exe")):
        path = shutil.which(binary)
        if path is not None and os.path.normcase(path) not in seen:
            found.append((name, path))
            seen.add(os.path.normcase(path))
    return found


SHELLS = _shells()


def _quote(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _source() -> str:
    return CONTROLLER.read_text(encoding="utf-8")


def _hash_functions() -> str:
    source = _source()
    return source[
        source.index("function Import-ShellOwnedFileHashCommand") :
        source.index("$script:trustedFileHashCommand =")
    ]


def _hash_bootstrap() -> str:
    source = _source()
    return source[
        source.index("function Import-ShellOwnedFileHashCommand") :
        source.index("$pluginRoot =")
    ]


def _run(shell: str, script: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )


@pytest.mark.parametrize("shell_name,shell", SHELLS, ids=[item[0] for item in SHELLS])
@pytest.mark.parametrize("module_path_case", ["clean", "contaminated"])
def test_hash_bootstrap_uses_shell_owned_module_in_clean_child_process_and_ignores_psmodulepath(
    tmp_path: Path, shell_name: str, shell: str, module_path_case: str
):
    sample = tmp_path / "hash-input.bin"
    sample.write_bytes(b"TASK-104 deterministic hash bootstrap")
    env = os.environ.copy()
    if module_path_case == "clean":
        env.pop("PSModulePath", None)
    else:
        fake_root = tmp_path / "controlled-modules"
        fake_module = fake_root / "Microsoft.PowerShell.Utility"
        fake_module.mkdir(parents=True)
        (fake_module / "Microsoft.PowerShell.Utility.psd1").write_text(
            "@{ RootModule='Microsoft.PowerShell.Utility.psm1'; ModuleVersion='1.0.0'; "
            "GUID='f95a2a99-3cc1-4b78-a44f-8b202cdba211'; FunctionsToExport=@('Get-FileHash') }",
            encoding="utf-8",
        )
        (fake_module / "Microsoft.PowerShell.Utility.psm1").write_text(
            "function Get-FileHash { [pscustomobject]@{ Hash=('0' * 64) } }; "
            "Export-ModuleMember -Function Get-FileHash",
            encoding="utf-8",
        )
        env["PSModulePath"] = str(fake_root)
    script = (
        "$ErrorActionPreference='Stop'\n"
        + _hash_bootstrap()
        + "\n[ordered]@{hash=(Get-TrustedSha256 -LiteralPath "
        + _quote(sample)
        + "); module_path=$script:trustedFileHashCommand.Module.Path; shell_home=$PSHOME; "
        + "module_name=$script:trustedFileHashCommand.ModuleName} | ConvertTo-Json -Compress"
    )
    result = _run(shell, script, env=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["hash"] == hashlib.sha256(sample.read_bytes()).hexdigest()
    assert payload["module_name"] == "Microsoft.PowerShell.Utility"
    expected_root = Path(payload["shell_home"]) / "Modules" / "Microsoft.PowerShell.Utility"
    assert os.path.commonpath(
        [os.path.normcase(payload["module_path"]), os.path.normcase(str(expected_root))]
    ) == os.path.normcase(str(expected_root))


@pytest.mark.parametrize("shell_name,shell", SHELLS, ids=[item[0] for item in SHELLS])
@pytest.mark.parametrize("failure_case", ["missing", "invalid"])
def test_hash_bootstrap_fails_closed_for_missing_or_invalid_explicit_module(
    tmp_path: Path, shell_name: str, shell: str, failure_case: str
):
    fake_home = tmp_path / "controlled-shell-home"
    fake_home.mkdir()
    if failure_case == "invalid":
        module = fake_home / "Modules" / "Microsoft.PowerShell.Utility"
        module.mkdir(parents=True)
        (module / "Microsoft.PowerShell.Utility.psd1").write_text(
            "this is not a PowerShell module manifest",
            encoding="utf-8",
        )
    script = (
        "$ErrorActionPreference='Stop'\n"
        + _hash_functions()
        + "\ntry { $null = Import-ShellOwnedFileHashCommand -ShellHome "
        + _quote(fake_home)
        + "; Write-Output 'UNEXPECTED_SUCCESS'; exit 0 } "
        + "catch { Write-Output ('EXPECTED_FAILURE=' + $_.Exception.Message); exit 19 }"
    )
    result = _run(shell, script)
    assert result.returncode == 19
    assert "EXPECTED_FAILURE=" in result.stdout
    assert "UNEXPECTED_SUCCESS" not in result.stdout


@pytest.mark.parametrize("shell_name,shell", SHELLS, ids=[item[0] for item in SHELLS])
def test_hash_bootstrap_rejects_reparse_in_command_path_chain_when_available(
    tmp_path: Path, shell_name: str, shell: str
):
    fake_home = tmp_path / "controlled-shell-home"
    module = fake_home / "Modules" / "Microsoft.PowerShell.Utility"
    module.mkdir(parents=True)
    external = tmp_path / "external-command-body"
    external.mkdir()
    (external / "Microsoft.PowerShell.Utility.psm1").write_text(
        "function Get-FileHash { [pscustomobject]@{ Hash=('0' * 64) } }; "
        "Export-ModuleMember -Function Get-FileHash",
        encoding="utf-8",
    )
    nested = module / "nested"
    try:
        nested.symlink_to(external, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlink privilege unavailable: {error}")
    (module / "Microsoft.PowerShell.Utility.psd1").write_text(
        "@{ RootModule='nested\\Microsoft.PowerShell.Utility.psm1'; ModuleVersion='1.0.0'; "
        "GUID='213512c3-0699-4dd8-b654-49cad240ed84'; FunctionsToExport=@('Get-FileHash') }",
        encoding="utf-8",
    )
    script = (
        "$ErrorActionPreference='Stop'\n"
        + _hash_functions()
        + "\ntry { $null = Import-ShellOwnedFileHashCommand -ShellHome "
        + _quote(fake_home)
        + "; Write-Output 'UNEXPECTED_SUCCESS'; exit 0 } "
        + "catch { Write-Output ('EXPECTED_FAILURE=' + $_.Exception.Message); exit 23 }"
    )
    result = _run(shell, script)
    assert result.returncode == 23
    assert "EXPECTED_FAILURE=" in result.stdout
    assert "UNEXPECTED_SUCCESS" not in result.stdout


def test_controller_has_one_compiler_invocation_no_retry_and_only_trusted_hash_calls():
    source = _source()
    assert source.count("& $Compiler @arguments") == 1
    assert "Start-Process -FilePath $Compiler" not in source
    assert source.count("Import-ShellOwnedFileHashCommand -ShellHome $PSHOME") == 1
    assert "\nImport-Module Microsoft.PowerShell.Utility" not in source
    assert source.count("Get-FileHash -LiteralPath") == 0
    assert source.count("Get-TrustedSha256 -LiteralPath") == 4
    assert "Get-Command -Name 'Microsoft.PowerShell.Utility\\Get-FileHash' -All" in source
    assert "Test-Path -LiteralPath $commandPath -PathType Leaf" in source
    assert "$commandPathItem.Attributes -band [IO.FileAttributes]::ReparsePoint" in source
    assert "$commandPathCursor.Equals($moduleRoot, [StringComparison]::OrdinalIgnoreCase)" in source
    assert "Trusted Microsoft.PowerShell.Utility command escaped module root" in source


@pytest.mark.parametrize("shell_name,shell", SHELLS, ids=[item[0] for item in SHELLS])
def test_output_containment_guard_accepts_only_descendants_and_denies_drive_root_children(
    tmp_path: Path, shell_name: str, shell: str
):
    source = _source()
    containment = source[
        source.index("function Assert-ContainedPath") : source.index("function Write-NewJson")
    ]
    allowed = tmp_path / "authorized" / "root"
    allowed.mkdir(parents=True)
    inside = allowed / "operation" / "output"
    outside = tmp_path / "outside" / "output"
    drive_child = Path(allowed.anchor) / "task104-forbidden-direct-child"
    script = (
        "$ErrorActionPreference='Stop'\n"
        + containment
        + "\n$inside = Assert-ContainedPath "
        + _quote(inside)
        + " "
        + _quote(allowed)
        + "\n$outsideDenied=$false; try { $null=Assert-ContainedPath "
        + _quote(outside)
        + " "
        + _quote(allowed)
        + " } catch { $outsideDenied=$true }"
        + "\n$driveDenied=$false; try { $null=Assert-ContainedPath "
        + _quote(drive_child)
        + " "
        + _quote(allowed.anchor)
        + " } catch { $driveDenied=$true }"
        + "\n[ordered]@{inside=$inside; outside_denied=$outsideDenied; drive_denied=$driveDenied} | ConvertTo-Json -Compress"
    )
    result = _run(shell, script)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert Path(payload["inside"]) == inside
    assert payload["outside_denied"] is True
    assert payload["drive_denied"] is True
