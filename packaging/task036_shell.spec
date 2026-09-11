"""Reproducible PyInstaller one-dir definition for the TASK-036 W0 gate."""

import hashlib
import json
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


PACKAGED_HELPER_FILENAME = "BAI Video Production Key Helper.exe"
PACKAGED_HELPER_IDENTITY_MODULE = "_bvp_task059_packaged_helper_identity"
PACKAGED_HELPER_DIGEST_ATTRIBUTE = "EXPECTED_PACKAGED_HELPER_SHA256"
MAX_PACKAGED_HELPER_BYTES = 128 * 1024 * 1024

repository = Path(SPECPATH).parent
helper_source = os.environ.get("BVP_TASK059_HELPER_EXE")
if not helper_source:
    raise ValueError("BVP_TASK059_HELPER_EXE is required")
helper_path = Path(helper_source)
if (
    not helper_path.is_absolute()
    or helper_path.name.casefold() != PACKAGED_HELPER_FILENAME.casefold()
    or helper_path.is_symlink()
    or not helper_path.is_file()
    or not 1 <= helper_path.stat().st_size <= MAX_PACKAGED_HELPER_BYTES
):
    raise ValueError("TASK-059 packaged helper identity is invalid")
helper_digest = "sha256:" + hashlib.sha256(helper_path.read_bytes()).hexdigest()
generated_root = Path(workpath) / "task059-generated"
generated_root.mkdir(parents=True, exist_ok=True)
generated_module = generated_root / f"{PACKAGED_HELPER_IDENTITY_MODULE}.py"
generated_module.write_text(
    f'{PACKAGED_HELPER_DIGEST_ATTRIBUTE} = "{helper_digest}"\n',
    encoding="ascii",
)

# Controller + entire private worker closure are authenticated before collection.
# DATA avoids PyInstaller rewriting a pinned DLL/PYD or UPX-transforming its bytes.
meter_controller_source = os.environ.get("BVP_TASK048_CONTROLLER_EXE")
meter_worker_source = os.environ.get("BVP_TASK048_WORKER_BUNDLE")
if not meter_controller_source or not meter_worker_source:
    raise ValueError("TASK-048 same-build inputs are required")


def checked_meter_path(raw):
    path = Path(raw)
    if not path.is_absolute() or path.parent == Path(path.anchor):
        raise ValueError("TASK-048 invalid build path")
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or getattr(ancestor, "is_junction", lambda: False)():
            raise ValueError("TASK-048 reparse build path")
    if not path.resolve().is_relative_to(repository.resolve()):
        raise ValueError("TASK-048 input outside build workspace")
    return path


meter_controller = checked_meter_path(meter_controller_source)
meter_worker = checked_meter_path(meter_worker_source)
if meter_controller.name != "bai-voice-capture-controller.exe" or not meter_worker.is_dir():
    raise ValueError("TASK-048 invalid build closure")
meter_receipt_path = checked_meter_path(str(meter_controller.parent / "meter-build-identity.json"))
if meter_receipt_path.stat().st_size > 1024 * 1024:
    raise ValueError("TASK-048 oversized build receipt")
meter_receipt = json.loads(meter_receipt_path.read_text(encoding="utf-8-sig"))
if meter_receipt.get("task") != "TASK-048" or meter_receipt.get("result") != "PASS":
    raise ValueError("TASK-048 unverified Controller build")
meter_data = []
meter_identity = []


def add_meter_file(path, relative):
    checked_meter_path(str(path))
    if not path.is_file() or not 1 <= path.stat().st_size <= 512 * 1024 * 1024:
        raise ValueError("TASK-048 invalid closure file")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    destination = "_meter/" + relative.replace("\\", "/")
    meter_data.append((str(path), str(Path(destination).parent)))
    meter_identity.append(("_internal\\" + destination.replace("/", "\\"), digest))
    return digest


controller_digest = add_meter_file(meter_controller, meter_controller.name)
if controller_digest != meter_receipt.get("controller_sha256"):
    raise ValueError("TASK-048 Controller identity changed")
worker_expected = meter_receipt.get("worker_files")
if type(worker_expected) is not list or not 2 <= len(worker_expected) <= 4095:
    raise ValueError("TASK-048 invalid worker identity")
worker_actual = []
pending_directories = [meter_worker]
meter_entry_count = 0
while pending_directories:
    for path in sorted(pending_directories.pop().iterdir()):
        checked_meter_path(str(path))
        meter_entry_count += 1
        if meter_entry_count > 8192:
            raise ValueError("TASK-048 closure entry limit")
        if path.is_dir():
            pending_directories.append(path)
        else:
            relative = "worker\\" + str(path.relative_to(meter_worker)).replace("/", "\\")
            worker_actual.append({"path": relative, "sha256": add_meter_file(path, relative)})
if sorted(worker_actual, key=lambda item: item["path"].casefold()) != sorted(worker_expected, key=lambda item: item["path"].casefold()):
    raise ValueError("TASK-048 worker closure differs from compiled identity")
meter_identity_module = "_bvp_task048_meter_identity"
(generated_root / (meter_identity_module + ".py")).write_text(
    "METER_FILES = " + repr(tuple(sorted(meter_identity))) + "\n", encoding="ascii")

webview_data, webview_binaries, webview_hiddenimports = collect_all("webview")
asr_data, asr_binaries, asr_hiddenimports = collect_all("faster_whisper")
schema_directory = repository / "src" / "ai_video_production" / "schema_resources"
product_data = [
    (str(path), "ai_video_production/schema_resources")
    for path in schema_directory.glob("*.json")
]

analysis = Analysis(
    [str(repository / "packaging" / "task036_windows_entry.py")],
    pathex=[str(generated_root), str(repository / "src")],
    binaries=webview_binaries + asr_binaries,
    datas=webview_data + asr_data + product_data + meter_data,
    hiddenimports=(
        webview_hiddenimports
        + asr_hiddenimports
        + [PACKAGED_HELPER_IDENTITY_MODULE]
        + [meter_identity_module]
    ),
    noarchive=False,
)
python_archive = PYZ(analysis.pure)
executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="BAI Video Production",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
packaged_helper = [
    (PACKAGED_HELPER_FILENAME, str(helper_path), "EXECUTABLE"),
]
bundle = COLLECT(
    executable,
    packaged_helper,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="BAI Video Production",
)
