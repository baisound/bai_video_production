"""PyInstaller one-dir definition for the TASK-049 DbD Training Studio."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files
repository = Path(SPECPATH).parent
jsonschema_specification_data = collect_data_files("jsonschema_specifications")
faster_whisper_data = collect_data_files("faster_whisper")
analysis = Analysis(
    [str(repository / "packaging" / "task049_training_studio_windows_entry.py")],
    pathex=[str(repository / "src")], binaries=[],
    datas=jsonschema_specification_data + faster_whisper_data,
    hiddenimports=["tkinter","tkinter.ttk","tkinter.messagebox","tkinter.filedialog","faster_whisper","av","PIL","PIL.Image","PIL.ImageTk"], noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="BAI DbD Training Studio", console=False, debug=False, strip=False, upx=True)
bundle = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=True, name="BAI DbD Training Studio")
