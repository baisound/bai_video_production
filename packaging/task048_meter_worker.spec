"""Private C1 worker closure. No ASR/models/network, console hidden by its parent."""
from pathlib import Path

repository = Path(SPECPATH).parent
schema_directory = repository / "src" / "ai_video_production" / "schema_resources"
product_data = [
    (str(path), "ai_video_production/schema_resources")
    for path in schema_directory.glob("*.json")
]
analysis = Analysis(
    [str(repository / "packaging" / "task048_meter_worker_windows_entry.py")],
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
    [],
    exclude_binaries=True,
    name="BAI Meter Worker",
    console=True,
    debug=False,
    strip=False,
    upx=False,
    contents_directory="_internal",
)
bundle = COLLECT(
    executable, analysis.binaries, analysis.datas,
    name="BAI Meter Worker",
    strip=False,
    upx=False,
)
