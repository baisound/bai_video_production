"""PyInstaller one-dir definition for the TASK-049 DbD Trivia Editor."""
from pathlib import Path
repository = Path(SPECPATH).parent
analysis = Analysis(
    [str(repository / "packaging" / "task049_trivia_editor_windows_entry.py")],
    pathex=[str(repository / "src")], binaries=[], datas=[], hiddenimports=["tkinter","tkinter.ttk","tkinter.messagebox"], noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="BAI DbD Trivia Editor", console=False, debug=False, strip=False, upx=True)
bundle = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=True, name="BAI DbD Trivia Editor")
