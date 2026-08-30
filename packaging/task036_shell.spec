"""Reproducible PyInstaller one-dir definition for the TASK-036 W0 gate."""

import hashlib
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
    datas=webview_data + asr_data + product_data,
    hiddenimports=(
        webview_hiddenimports
        + asr_hiddenimports
        + [PACKAGED_HELPER_IDENTITY_MODULE]
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
