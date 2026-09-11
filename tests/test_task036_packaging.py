from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _execute_meter_spec(tmp_path, monkeypatch, *, damage=None):
    import hashlib
    import json
    import sys
    from types import ModuleType, SimpleNamespace

    def put(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    repository = tmp_path / "synthetic-build-workspace"
    (repository / "packaging").mkdir(parents=True)
    helper = put(repository / "build/helper/BAI Video Production Key Helper.exe", b"helper")
    controller = put(repository / "build/controller/bai-voice-capture-controller.exe", b"controller")
    worker = repository / "build/worker"
    files = [
        put(worker / "BAI Meter Worker.exe", b"worker"),
        put(worker / "_internal/python313.dll", b"python-runtime"),
        put(worker / "_internal/schema/schema.json", b"{}"),
        put(worker / "_internal/jsonschema-4.26.0.dist-info/REQUESTED", b""),
    ]
    if damage == "empty_controller":
        controller.write_bytes(b"")
    if damage == "empty_worker":
        files[0].write_bytes(b"")
    receipt = {
        "task": "TASK-048", "result": "PASS",
        "controller_sha256": hashlib.sha256(controller.read_bytes()).hexdigest(),
        "worker_files": [{"path": "worker\\" + str(file.relative_to(worker)).replace("/", "\\"),
                          "sha256": hashlib.sha256(file.read_bytes()).hexdigest()} for file in files],
    }
    if damage == "controller":
        controller.write_bytes(b"tamper")
    if damage == "worker":
        files[-1].write_bytes(b"tamper")
    if damage == "extra":
        put(worker / "foreign.dll", b"foreign")
    if damage == "missing":
        receipt["worker_files"].append({"path": "worker\\missing.dll", "sha256": "0"*64})
    if damage == "result":
        receipt["result"] = "NOT_CONFIRMED"
    if damage == "count":
        receipt["worker_files"] *= 1024  # 4,096 declared files exceeds the 4,095 limit.
    if damage == "oversize":
        import os
        original_stat = Path.stat

        def oversized_stat(path, *args, **kwargs):
            observed = original_stat(path, *args, **kwargs)
            if path == files[-1]:
                fields = list(observed)
                fields[6] = 512 * 1024 * 1024 + 1
                return os.stat_result(fields)
            return observed

        monkeypatch.setattr(Path, "stat", oversized_stat)
    if damage == "reparse":
        original_is_symlink = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == files[-1] or original_is_symlink(path))
    put(controller.parent / "meter-build-identity.json", json.dumps(receipt).encode())
    monkeypatch.setenv("BVP_TASK059_HELPER_EXE", str(helper))
    monkeypatch.setenv("BVP_TASK048_CONTROLLER_EXE", str(controller))
    monkeypatch.setenv("BVP_TASK048_WORKER_BUNDLE", str(worker))
    if damage == "unset":
        monkeypatch.delenv("BVP_TASK048_WORKER_BUNDLE")
    if damage == "outside":
        outside = tmp_path / "outside-workspace-worker"
        outside.mkdir()
        monkeypatch.setenv("BVP_TASK048_WORKER_BUNDLE", str(outside))
    hooks = ModuleType("PyInstaller.utils.hooks")
    hooks.collect_all = lambda _: ([], [], [])
    monkeypatch.setitem(sys.modules, "PyInstaller.utils.hooks", hooks)
    captured = {}

    def analysis(*args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(pure=[], scripts=[], binaries=[], datas=kwargs["datas"])

    namespace = {
        "SPECPATH": str(repository / "packaging"), "workpath": str(repository / "build/work"),
        "Analysis": analysis, "PYZ": lambda *_: None,
        "EXE": lambda *args, **kwargs: None, "COLLECT": lambda *args, **kwargs: None,
    }
    exec(compile((ROOT / "packaging/task036_shell.spec").read_text(encoding="utf-8"),
                 "task036_shell.spec", "exec"), namespace)
    return namespace, captured


def test_main_spec_seals_complete_meter_closure_as_unmodified_data(tmp_path, monkeypatch):
    import ast
    namespace, captured = _execute_meter_spec(tmp_path, monkeypatch)
    identity_file = namespace["generated_root"] / "_bvp_task048_meter_identity.py"
    assignments = ast.parse(identity_file.read_text(encoding="ascii"))
    identities = ast.literal_eval(assignments.body[0].value)
    assert len(identities) == 5
    assert all(path.startswith("_internal\\_meter\\") for path, _ in identities)
    assert "_bvp_task048_meter_identity" in captured["hiddenimports"]
    assert len(namespace["meter_data"]) == 5
    assert captured["binaries"] == []
    empty_identity = next((path, digest) for path, digest in identities if path.endswith("\\REQUESTED"))
    assert empty_identity[1] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    empty_data = next(path for path, _ in namespace["meter_data"] if path.endswith("REQUESTED"))
    assert Path(empty_data).read_bytes() == b""


def test_main_spec_rejects_all_incomplete_or_changed_closures(tmp_path, monkeypatch):
    import pytest
    for case in ("controller", "worker", "extra", "missing", "result", "unset"):
        with pytest.raises(ValueError):
            _execute_meter_spec(tmp_path / case, monkeypatch, damage=case)


def test_main_spec_preserves_size_count_reparse_path_and_nonempty_image_gates(tmp_path, monkeypatch):
    import pytest
    for case in ("oversize", "count", "reparse", "outside", "empty_controller", "empty_worker"):
        with monkeypatch.context() as isolated:
            with pytest.raises(ValueError):
                _execute_meter_spec(tmp_path / case, isolated, damage=case)


def test_worker_spec_has_no_asr_model_bundle_or_second_user_entrypoint():
    source = (ROOT / "packaging/task048_meter_worker.spec").read_text(encoding="utf-8")
    assert 'name="BAI Meter Worker"' in source
    assert "console=True" in source
    assert "upx=False" in source
    assert "faster_whisper" not in source and "collect_all" not in source
    assert "COLLECT(" in source


def test_controller_build_preflights_unique_roots_and_does_not_install():
    source = (ROOT / "native/task047_obs_voice_capture/scripts/build-controller.ps1").read_text(encoding="utf-8")
    assert "Assert-ContainedPath" in source
    assert "Drive-root placement denied" in source
    assert "Existing runtime destination denied" in source
    assert "Foreign or previously used build destination denied" in source
    assert "BaiMeterRuntimeBridge.cs" in source
    assert "/define:BVP_METER_PACKAGED" in source
    assert "-WindowStyle Hidden" in source
    assert "Get-Content -Raw -LiteralPath" in source
    assert "meter-build-identity.json" in source
    assert "Invoke-WebRequest" not in source



def _execute_controller_closure_only(tmp_path, *, case="valid"):
    """Exercise the real PowerShell manifest block, never compiler/process code."""
    import hashlib
    import json
    import os
    import shutil
    import subprocess
    import pytest

    powershell = shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("Windows PowerShell manifest-only execution requires Windows")
    build = tmp_path / "build"
    worker = build / "worker"
    worker.mkdir(parents=True)
    (worker / "BAI Meter Worker.exe").write_bytes(b"" if case == "empty_image" else b"image")
    (worker / "payload.dat").write_bytes(b"payload")
    marker = worker / "_internal/jsonschema-4.26.0.dist-info/REQUESTED"
    marker.parent.mkdir(parents=True)
    marker.write_bytes(b"")
    before = {str(path.relative_to(worker)): path.read_bytes()
              for path in worker.rglob("*") if path.is_file()}
    source = (ROOT / "native/task047_obs_voice_capture/scripts/build-controller.ps1").read_text(encoding="utf-8")
    containment = source[source.index("function Assert-ContainedPath"):source.index("function Write-NewJson")]
    closure = source[source.index("$workerFiles = @()"):
                     source.index("New-Item -ItemType Directory -Path $controllerOutputRoot")]
    assert "$Compiler" not in closure and "Start-Process" not in closure
    assert "Remove-Item" not in closure and "Set-Content" not in closure
    assert "Get-FileHash -LiteralPath $entry.FullName -Algorithm SHA256" in closure
    assert "Sort-Object path" in closure

    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    overrides = ""
    if case in ("oversize", "max_size", "negative_size", "reparse", "unsupported_path"):
        lengths = {"oversize": 536870913, "max_size": 536870912, "negative_size": -1}
        length = str(lengths[case]) if case in lengths else "$entry.Length"
        attributes = "[IO.FileAttributes]::ReparsePoint" if case == "reparse" else "$entry.Attributes"
        full_name = "($entry.FullName + '#')" if case == "unsupported_path" else "$entry.FullName"
        overrides = """
function Get-ChildItem {
  param([switch]$Force, [string]$LiteralPath)
  foreach ($entry in Microsoft.PowerShell.Management\\Get-ChildItem -Force -LiteralPath $LiteralPath) {
    if (!$entry.PSIsContainer -and $entry.Name -eq 'payload.dat') {
      [pscustomobject]@{FullName=FULL_NAME; PSIsContainer=$false; Attributes=ATTRIBUTES; Length=ENTRY_LENGTH}
    } else { $entry }
  }
}
""".replace("FULL_NAME", full_name).replace("ATTRIBUTES", attributes).replace("ENTRY_LENGTH", length)
    if case in ("count_limit", "max_count"):
        count = 4096 if case == "count_limit" else 4095
        overrides = """
function Get-ChildItem {
  param([switch]$Force, [string]$LiteralPath)
  for ($index = 0; $index -lt ENTRY_COUNT; $index++) {
    $name = if ($index -eq 0) { 'BAI Meter Worker.exe' } else { ('file-{0:D4}.dat' -f $index) }
    [pscustomobject]@{FullName=($LiteralPath + '\\' + $name); PSIsContainer=$false; Attributes=0; Length=1}
  }
}
function Get-FileHash {
  param([string]$LiteralPath, [string]$Algorithm)
  [pscustomobject]@{Hash='SYNTHETIC_DIGEST'}
}
""".replace("ENTRY_COUNT", str(count)).replace("SYNTHETIC_DIGEST", hashlib.sha256(b"synthetic").hexdigest())
    chosen_worker = tmp_path / "outside-build" if case == "outside" else worker
    script = (
        "$ErrorActionPreference='Stop'\n"
        "Import-Module Microsoft.PowerShell.Management,Microsoft.PowerShell.Utility\n"
        + containment + overrides
        + "\n$resolvedBuildRoot=" + quote(build)
        + "\n$MeterWorkerBundle=" + quote(chosen_worker)
        + "\ntry {\n" + closure
        + "\n[ordered]@{ok=$true; files=@($workerFiles); sorted_paths=@($workerFiles | Sort-Object path | ForEach-Object {$_.path})} | ConvertTo-Json -Depth 5 -Compress"
        + "\n} catch { [ordered]@{ok=$false; error=$_.Exception.Message} | ConvertTo-Json -Compress }"
    )
    runtime = tmp_path / "powershell-runtime"
    runtime.mkdir()
    result = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        cwd=tmp_path, env={**os.environ, "TEMP": str(runtime), "TMP": str(runtime),
                           "PSModulePath": str(Path(powershell).parent / "Modules")},
        capture_output=True, text=True, timeout=40, check=False,
    )
    after = {str(path.relative_to(worker)): path.read_bytes()
             for path in worker.rglob("*") if path.is_file()}
    assert after == before, "Manifest generation must never mutate/delete closure files"
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_controller_real_manifest_hashes_zero_byte_requested_without_mutation(tmp_path):
    import hashlib
    result = _execute_controller_closure_only(tmp_path)
    assert result["ok"] is True, result
    files = result["files"]
    assert len(files) == 3
    assert [item["path"] for item in files] == result["sorted_paths"]
    empty = next(item for item in files if item["path"].endswith("\\REQUESTED"))
    assert empty["sha256"] == hashlib.sha256(b"").hexdigest()


def test_controller_manifest_preserves_count_size_reparse_and_path_refusals(tmp_path):
    failures = {
        "oversize": "Worker closure file size limit exceeded",
        "negative_size": "Worker closure file size limit exceeded",
        "count_limit": "Worker closure file count limit exceeded",
        "reparse": "Worker reparse entry denied",
        "unsupported_path": "Worker path unsupported",
        "outside": "Output escaped authorized root",
        "empty_image": "Worker executable empty",
    }
    for case, expected in failures.items():
        result = _execute_controller_closure_only(tmp_path / case, case=case)
        assert result == {"ok": False, "error": expected}, case


def test_controller_manifest_admits_exact_upper_limits(tmp_path):
    for case, expected in (("max_size", 3), ("max_count", 4095)):
        result = _execute_controller_closure_only(tmp_path / case, case=case)
        assert result["ok"] is True and len(result["files"]) == expected, result

def test_task036_windows_entry_uses_product_cli_without_duplicating_shell_logic():
    entry = (ROOT / "packaging" / "task036_windows_entry.py").read_text(encoding="utf-8")
    assert "from ai_video_production.task036_packaged_entry import packaged_main" in entry
    assert "run_native_layout_spike" not in entry


def test_task036_pyinstaller_definition_is_one_dir_and_path_portable():
    spec = (ROOT / "packaging" / "task036_shell.spec").read_text(encoding="utf-8")
    assert "COLLECT(" in spec
    assert 'name="BAI Video Production"' in spec
    assert "console=False" in spec
    assert 'collect_all("webview")' in spec
    assert 'collect_all("faster_whisper")' in spec
    assert "asr_binaries" in spec
    assert "asr_hiddenimports" in spec
    assert 'schema_directory.glob("*.json")' in spec
    assert "D:\\" not in spec
