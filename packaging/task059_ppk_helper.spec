"""One-file internal helper for the TASK-059 PPK import boundary."""

from pathlib import Path


repository = Path(SPECPATH).parent
schema_directory = repository / "src" / "ai_video_production" / "schema_resources"
product_data = [
    (str(path), "ai_video_production/schema_resources")
    for path in schema_directory.glob("*.json")
]

analysis = Analysis(
    [str(repository / "packaging" / "task059_ppk_helper_windows_entry.py")],
    pathex=[str(repository / "src")],
    binaries=[],
    datas=product_data,
    hiddenimports=[],
    noarchive=False,
)
python_archive = PYZ(analysis.pure)
executable = EXE(
    python_archive,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="BAI Video Production Key Helper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)
