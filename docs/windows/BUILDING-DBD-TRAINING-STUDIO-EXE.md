# Build BAI DbD Training Studio EXE

`BAI DbD Training Studio.exe` is the Windows GUI for DbD-specific teacher-data, recognition-reference and commentary-knowledge intake used by TASK-049.

It is intentionally separate from the main `BAI Video Production.exe` entrypoint so dataset preparation can be performed without opening a production Project. Both applications use the same source contracts; the Training Studio does not create a second recognition format.

## What the EXE covers

The GUI supports:

- one visual training sample at a time;
- CSV import with **one row or many rows**;
- **video -> exact-frame ROI slice extraction -> registration** for:
  - lower-left Survivor HUD;
  - bottom-right Perk slots;
  - Killer / Power HUD when a calibrated ROI exists;
- upper-right OCR vocabulary:
  - one phrase;
  - CSV one/many;
  - video OCR candidate scan followed by explicit Human selection;
- Commentary Trivia:
  - one entry;
  - CSV one/many;
  - existing TranscriptManifest mining;
  - direct local FasterWhisper transcription from a video and conservative CANDIDATE mining;
- deterministic reference-index and OCR-vocabulary build.
- portable DbD data migration Backup / Preview / Restore for Project Game Intelligence, Training workspace and global Trivia Knowledge.

The current visual learner builds the deterministic reference-slice baseline. It is **not yet a neural-network training GUI**. The same manifests remain the input source when an embedding/CNN recognizer is introduced later.

## Requirements

- Windows 10/11;
- Python 3.11+;
- repository checkout;
- FFmpeg on `PATH` for still normalization and video ROI extraction;
- Tesseract on `PATH` only when upper-right video OCR scan is used;
- FasterWhisper model/cache only when video -> transcript -> trivia mining is used.

`windows-build` already includes the FasterWhisper Python dependency. Model download remains disabled by default in the UI; enabling it is an explicit network action.

## Install build dependencies

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[windows-build]"
```

Confirm optional external executables as needed:

```powershell
ffmpeg -version
tesseract --version
```

Tesseract is not required for Perk/Survivor/Killer reference learning. It is required only for the OCR video-scan path.

## Build

```powershell
.\build-dbd-training-studio-exe.bat
```

Expected output:

```text
builds\BAI DbD Training Studio\
├─ BAI DbD Training Studio.exe
└─ _internal\...
```

This is a PyInstaller **one-dir** package. Keep the complete `BAI DbD Training Studio` directory together.

The build script does not:

- install FFmpeg/Tesseract;
- download FasterWhisper models;
- sign the EXE;
- publish a Release;
- upload local training data.

## Run

```powershell
& ".\builds\BAI DbD Training Studio\BAI DbD Training Studio.exe"
```

Then follow [BAI DbD Training Studio Usage](../user/DBD-TRAINING-STUDIO-USAGE.md).

For moving DbD learning/knowledge/CGEL data to another PC, use the Training Studio **Backup / Restore** tab and follow [DbD Data Backup / Restore and PC Migration](../user/DBD-DATA-BACKUP-RESTORE.md).

## Verify without EXE packaging

```powershell
python -m pip install -e ".[dev,windows-build]"
python -m ai_video_production.dbd_training_studio
```

Focused tests:

```powershell
pytest -q `
  tests/test_task049_dbd_training_workspace.py `
  tests/test_task049_dbd_training_studio_packaging.py `
  tests/test_task049_dbd_vision_slices.py `
  tests/test_task049_dbd_hud_detectors.py
```

## Safety / data rules

- use only recordings/images you are allowed to process;
- keep private datasets outside the public repository;
- do not mix adjacent frames from one match into both train and test sets;
- video-derived OCR phrases require explicit Human selection before vocabulary mutation;
- video-derived trivia remains `CANDIDATE` until Human review;
- a reference index passing local examples is not Production-accuracy evidence.

## Related

- [Training Studio usage](../user/DBD-TRAINING-STUDIO-USAGE.md)
- [Recognition accuracy and training](../game-intelligence/DBD-RECOGNITION-ACCURACY-AND-TRAINING.md)
- [Slice Dataset guide](../game-intelligence/DBD-SLICE-DATASET-GUIDE.md)

## HUD Calibration runtime notes

The same `BAI DbD Training Studio.exe` build includes the **HUD Calibration** tab. No separate Calibration EXE is required.

Calibration uses the existing Windows prerequisites:

- `ffmpeg` for exact-frame preview/crop extraction;
- `ffprobe` for frame geometry;
- Tk/Tcl distributed with the supported Python Windows installation for the GUI.

Profile JSON and anchor clips are stored under the Training Studio workspace and can be moved with the built-in DbD Backup / Restore function. See [HUD Calibration / ROI Profile Guide](../game-intelligence/DBD-HUD-CALIBRATION-GUIDE.md).
