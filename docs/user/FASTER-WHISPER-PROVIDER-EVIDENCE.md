# FasterWhisper Provider Evidence

TASK-023 does not add a second ASR engine. It audits and exposes evidence for the existing
FasterWhisper provider created by TASK-006.

## Final user experience

Normal users will use transcription from **BAI Video Production.exe -> Subtitle Workspace**.

The command below is a developer/diagnostic interface, not the final product workflow.

## Evidence only

```powershell
ai-video-faster-whisper-evidence
```

This does not load the model, download anything, or run transcription.

## Build an identity from a real local media file

```powershell
ai-video-faster-whisper-evidence `
  --source-file .\sample.wav `
  --language ja
```

The command hashes the file but does not put the file path into JSON output.

## Build from an existing source checksum

```powershell
ai-video-faster-whisper-evidence `
  --source-sha256 sha256:<64hex> `
  --language ja
```

## Output privacy

Evidence contains provider/model settings, checksums and capability flags.

It does not contain:

- transcript text;
- subtitle text;
- source path;
- cache directory path;
- credentials.

TASK-023 evidence does not claim that inference ran. Actual ASR behavior remains the TASK-006
FasterWhisper flow.

## Integration status

- Backend provider: implemented by TASK-006.
- TASK-023 reconciliation/evidence: this slice.
- Unified Subtitle Workspace connection: designed here, not yet Shell-integrated.
