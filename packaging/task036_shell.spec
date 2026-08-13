"""Reproducible PyInstaller one-dir definition for the TASK-036 W0 gate."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


repository = Path(SPECPATH).parent
webview_data, webview_binaries, webview_hiddenimports = collect_all("webview")
asr_data, asr_binaries, asr_hiddenimports = collect_all("faster_whisper")
schema_directory = repository / "src" / "ai_video_production" / "schema_resources"
product_data = [
    (str(path), "ai_video_production/schema_resources")
    for path in schema_directory.glob("*.json")
]

analysis = Analysis(
    [str(repository / "packaging" / "task036_windows_entry.py")],
    pathex=[str(repository / "src")],
    binaries=webview_binaries + asr_binaries,
    datas=webview_data + asr_data + product_data,
    hiddenimports=webview_hiddenimports + asr_hiddenimports,
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
bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="BAI Video Production",
)
