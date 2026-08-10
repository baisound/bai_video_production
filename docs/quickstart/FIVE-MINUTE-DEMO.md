# Five-minute demo

This demo proves three current core contracts without an API key, network call, paid provider, media upload, or NLE mutation:

1. an `OFFLINE_ONLY` profile selects an exact model route by capability;
2. two synthetic source ranges map to an exact NTSC `30000/1001` timeline;
3. the result is written as canonical, checksummed JSON.

## Run

```powershell
python -m pip install -e ".[dev]"
ai-video-quickstart --output .\quickstart-output.json
Get-Content .\quickstart-output.json
```

Or without the installed command:

```powershell
python -m ai_video_production.quickstart_cli --output .\quickstart-output.json
```

Expected terminal result:

```json
{"ok": true, "output": ".\\quickstart-output.json", "sha256": "sha256:..."}
```

The JSON must say that network, credentials and paid providers were not used. It contains the selected local route, two non-overlapping placements, an exact plan hash and a whole-document demo hash.

## What this does not prove

It does not generate or edit a real video. That requires the later ASR/Cut/Resolve assembly slices and an explicit live Evidence procedure. The quickstart intentionally demonstrates only implemented, deterministic foundations.
