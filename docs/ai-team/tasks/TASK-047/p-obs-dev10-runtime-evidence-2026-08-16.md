# TASK-047 / P-OBS dev10 runtime Evidence — 2026-08-16

## Scope and authority

- Task: `TASK-047/P-OBS-DEV10-UX-RUNTIME`
- Active Lock: `BVP-LOCK-TASK047-POBS-DEV10-UX-RUNTIME`
- Implementation authority: Owner-authorized autonomous TASK-047 lane
- Base after Lock hosting: `main@79ec54eeea9c14ddde488f861547acf541d9382b`
- Production admission, Dataset adoption and Training effects: not granted

This slice makes the Plugin and Controller source reviewable, retains the bounded
OBS callback, and adds the Owner-requested operational UX. It does not contain
audio, a host absolute path, a credential, or a recording-body digest.

## Owner-requested UX fixed in source

- OBS 32.2.1 may remain running for gain check, start, pause, resume and stop.
- One exact OBS executable and process ID are fixed at start. Pause, resume and
  stop fail closed if that identity changes.
- The Controller shows a live Peak/RMS GAIN meter with peak hold and clipping red.
- `学習データ録音中` and `学習データ録音 一時停止中` remain visibly distinct.
- The destination, maximum duration and free-space floor are user-selectable.
- Pause checkpoints the partial WAV and disconnects transport without ending OBS;
  resume reconnects with the same in-memory session key and exact OBS identity.

## Security and callback boundary

- Session hello: fixed 40-byte `BCH2`, protocol version `2`.
- Session key: controller-generated, in-memory only; no environment key.
- Pipe server: current-user-only ACL.
- Controller verifies the connecting pipe client PID and exact selected OBS path.
- Plugin verifies the pipe server belongs to the same Windows user.
- Session nonce is stable and sequence remains monotonic through reconnect.
- Real-time callback only forwards bounded planes/frame metadata to `CaptureCore`;
  file I/O, JSON, GAIN analysis and network work are absent from the callback.

## Build and package read-back

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Plugin DLL | 24064 | `9b8a603d6515c0735f776867c7079c0600990ebebaf8b9609d81d0f0f265bcdb` |
| Controller EXE | 37376 | `e715fd0a3eff137f405b1f8da33ba5f9232e57d7c1c4d1694069ebdba3b3fc67` |
| Runtime ZIP | 40670 | `03286e9efbf5dd5af38230dcf7fee4bf53eb3fcc7d7a6d014833b9996bc1f558` |
| Runtime manifest | 1457 | `4958d963f9dde1c82cf9e1110ada37019e276961df9cd97135b3e73b8b84a232` |
| Source ZIP | 45715 | `0ad4c83a957b37b455b38829f842f8318116c522cb542de0a9c5849567b29e72` |
| Source manifest | 4839 | `1e178f8ebf27ffcb5a0a2bb2343cbd7c76a74aaf3b98558c9189dfba112ebd66` |
| Installer | 2140146 | `5eb7b00aa3830f880c724538023c6f7b0b52a032e2c1ed880d497cdd8cce1908` |

- Runtime package manifest: 7 payload files, independently re-read from ZIP.
- Source package manifest: 28 source files, independently re-read from ZIP.
- Installer compiler: Inno Setup `7.1.0`; `ISCC.exe` signature valid and SHA-256
  `d06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a`.
- Installer build performed no OBS mutation and started no recording.

## Tests

- Controller compile and self-test: PASS.
- Standalone queue/capture/security suites: PASS (`3 / 3`).
- Same-user pipe disconnect/reconnect integration: PASS.
- Plugin DLL and core test Release compilation through existing VS18 graph: PASS.
- Reviewable-source, installer and release focused contracts: PASS (`20 / 20`).
- Runtime/source ZIP entry, CRC, byte, SHA and manifest read-back: PASS.
- Isolated Windows installer execution: clean install, repair, collision refusal,
  uninstall, exact3 adoption/restore and append-only journal chain all PASS.
- Real OBS 32.2.1 install/update: PASS. Exact Plugin DLL, locales, Controller,
  predecessor backup and six-entry install/update journal were read back.
- Real OBS module load and existing `MIC` filter arm: PASS.
- Running-OBS GAIN check: `500 packets`, `gap 0`, `HMAC 0`, `reconnect 0`.
  Measurement receipt recorded `480000` sample values, clipping `0`, persisted
  audio body `false` and hardware setting changed `false`.
- Owner-voice running-OBS Acceptance: PASS. The accepted session ended by explicit
  user stop after `10139 packets`, with `gap 0`, `HMAC 0`, `reconnect 0`, one
  pause, `5.426 s` paused duration and `VERIFIED_SAME_PROCESS` pause/resume PID
  stability. A second short session also ended by explicit user stop with
  `gap 0`, `HMAC 0` and `reconnect 0`; no `.partial.wav` remained. Audio body,
  private destination, filename, device identity and audio digest are excluded
  from repository Evidence.
- Lock-host PR #128 hosted checks: `9 / 9` SUCCESS.
- Lock-host post-merge Security and CI: SUCCESS.
- Windows full regression after real Owner-voice Acceptance and normal OBS exit:
  `1282 passed / 1 skipped`; the skip is the non-Windows credential-vault contract.
- WSL2 full regression with Linux-native dependencies: `1282 passed / 1 skipped`;
  the skip is the Windows-only installer execution.

## Exact limitations and next Gates

- CMake `3.30.5` does not recognize the available Visual Studio 18 generator.
  Therefore a fresh CMake configure is not reported as PASS. The existing VS18
  graph was recompiled, but official-recipe existence or a short build is not a
  substitute for fresh-toolchain compatibility.
- The installer correctly refused to run while OBS was active, then passed the
  full isolated acceptance after OBS was closed. It also upgrades only the exact
  known predecessor DLL; unknown content remains a collision failure.
- Dev10 exact3 install, module load, MIC filter arm, body-free running-OBS GAIN,
  Owner-voice start/pause/resume/stop and completed-WAV receipt are established.
  This technical Acceptance does not adopt the recording into an Asset or Dataset
  and does not authorize Training or Production use.
- Installer and ZIP assets are unsigned Technical Preview candidates. A public
  Release must be created and independently read back before publication is PASS.

## Critic self-pass 1

Initial High: earlier documentation could imply that gain check and pause/resume
required restarting OBS. Corrected to require one continuously running, exact OBS
process and to expose a persistent meter and state banner.

Initial High: environment-key transport allowed inherited secret exposure and
ambiguous reconnect. Corrected to a same-user duplex handshake with a memory-only
key, exact client/server identity checks, stable nonce and monotonic sequence.

Initial Medium: package output defaults could overwrite an earlier evidence
directory. Corrected with explicit stage/artifact/controller inputs and operation-
root containment.

Initial Medium: the first Controller connection compared the Plugin's already
advanced sequence against zero, and terminal shutdown could be shown as a
reconnect. Corrected by anchoring the first authenticated frame and excluding an
explicit terminal stop from reconnect accounting; real GAIN read-back is now
`gap 0 / reconnect 0`.

Residual Critical/High: `0 / 0`.

## Critic self-pass 2

- No generated EXE/DLL/OBJ/PDB is stored under the reviewable source tree.
- Public docs and checksums contain no private workspace/audio root.
- The bounded callback has no filesystem, JSON, network, sleep or model work.
- Build PASS, install PASS, load PASS, Owner voice PASS and public Release PASS
  remain separate; unknown runtime states are not converted to success.
- No automatic hardware GAIN, device, OBS scene/profile, Dataset or Training effect.

Residual Critical/High: `0 / 0`.

## Read-only Judge before runtime Gates

- Reviewable source and exact frozen package candidate: `PASS`
- Owner-requested running-OBS UX represented and regression-tested: `PASS`
- Fresh CMake 3.30.5 configure: `NOT_ESTABLISHED`
- Dev10 real install/load/running-OBS GAIN: `PASS`
- Dev10 start/pause/resume/stop with new Owner voice: `PASS`
- Public GitHub Technical Preview: `NOT_ESTABLISHED` until exact Release read-back
- Production Recording/Dataset/Training: `BLOCKED / NOT AUTHORIZED`
