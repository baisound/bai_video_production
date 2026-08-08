# Windows Live Attempt 03 — Original Evidence

This directory preserves the Owner-returned TASK-002 final live evidence without rewriting the original JSON payloads.

Observed target:

- Windows 11 / Python 3.12.4
- DaVinci Resolve Studio 21.0.2.4
- Resolve bridge: WINDOWS_PROGRAMDATA
- Sandbox mutation: executed only inside `BAI_CAPABILITY_PROBE_MANUAL`
- Sandbox matrix: 15 SUPPORTED / 1 LIMITED / 7 PROBE_REQUIRED / 0 UNSUPPORTED
- WSL2 -> Windows HTTP/JSON: auth rejection PASS, authenticated roundtrip PASS, same-endpoint restart PASS
- WSL2 latency: p50 1.255 ms / p95 1.699 ms across 16 round trips

The screenshot records the operator observation that the generated WAV became offline/red after the 0.2.3 process ended. Review traced this to the temporary probe asset directory cleanup. Package 0.2.4 retains probe assets under the Evidence directory. Per Owner direction, another live run solely to confirm the visual post-run state is not a TASK-002 completion requirement.

See `SHA256SUMS.txt` for intake integrity hashes.
