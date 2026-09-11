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
    ]
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
    put(controller.parent / "meter-build-identity.json", json.dumps(receipt).encode())
    monkeypatch.setenv("BVP_TASK059_HELPER_EXE", str(helper))
    monkeypatch.setenv("BVP_TASK048_CONTROLLER_EXE", str(controller))
    monkeypatch.setenv("BVP_TASK048_WORKER_BUNDLE", str(worker))
    if damage == "unset":
        monkeypatch.delenv("BVP_TASK048_WORKER_BUNDLE")
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
    assert len(identities) == 4
    assert all(path.startswith("_internal\\_meter\\") for path, _ in identities)
    assert "_bvp_task048_meter_identity" in captured["hiddenimports"]
    assert len(namespace["meter_data"]) == 4
    assert captured["binaries"] == []


def test_main_spec_rejects_all_incomplete_or_changed_closures(tmp_path, monkeypatch):
    import pytest
    for case in ("controller", "worker", "extra", "missing", "result", "unset"):
        with pytest.raises(ValueError):
            _execute_meter_spec(tmp_path / case, monkeypatch, damage=case)


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
