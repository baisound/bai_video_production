# Voice Studio Requirements-to-TASK Crosswalk

Date: 2026-08-15
Canonical input SHA-256: `82533ef5b87f352f06a950a5640d6de92bee13aa2f0bfff696dca14538c17ae5`

Status codes: `EXISTING` = current implementation/contract is reused;
`EXTEND` = existing Task keeps ownership and receives a later bounded unit;
`NEW` = newly allocated Task; `GOV` = design/governance trace only.

## Original requirements OR-01 through OR-32

| ID | Requirement | Owner / classification |
|---|---|---|
| OR-01 | Explain P-NLE-3 | TASK-044 `EXISTING`; no new implementation |
| OR-02 | Explain TASK-044 scope | TASK-044 `EXISTING`; completion preserved |
| OR-03 | Trace free/local AI route | TASK-004/013/027/028/003/037/041/026/044 `EXISTING+EXTEND` |
| OR-04 | Local prerequisites and missing AI lanes | TASK-020/043/045 `EXTEND`; TASK-004 remains complete |
| OR-05 | Owner-voice learning technology | TASK-046 `NEW`; TASK-014 `EXTEND` |
| OR-06 | 30 min–2 h teleprompter, stop/resume | TASK-046 `NEW` |
| OR-07 | Zero-shot and fine-tuning | TASK-046 `NEW` |
| OR-08 | SRT-to-WAV, exclusive processing, Asset use | TASK-014/020/043/003 `EXTEND` |
| OR-09 | RX 8/9/10/12 technical/license integration | TASK-035 `EXTEND`; exact RX 12 probe required |
| OR-10 | Emotion/style controls | TASK-046/014 `NEW+EXTEND` |
| OR-11 | Gain/noise preflight and truthful quality | TASK-046/048 `NEW` |
| OR-12 | Emotion-aware cuts/tracks/placement | TASK-014/026/022/041 `EXTEND` |
| OR-13 | Whisper and soft-whisper | TASK-046/014 `NEW+EXTEND` |
| OR-14 | Quality/readiness/additional-time indicator | TASK-048/046 `NEW` |
| OR-15 | Readable subtitle splitting | TASK-006 `EXTEND` |
| OR-16 | Scene-aware fast-speech correction | TASK-006/014/022/044 `EXTEND` |
| OR-17 | Style-coverage AI recording coach | TASK-046 `NEW` |
| OR-18 | OBS plugin and meeting/live capture | TASK-047 P-OBS-0 exact probe + P-OBS-1 minimum production capture `P0 NEW`; P-OBS-2 meeting/live breadth `LATER` |
| OR-19 | Complete append-only design and “清書して” rule | imported Ver.1.2 `GOV` |
| OR-20 | BaiVoice synergy intake | PRODUCT-ARCH-002 and this Crosswalk `GOV` |
| OR-21 | Balanced question review | Ver.1.2 Decision Register `GOV` |
| OR-22 | Q1–Q20 recommended decisions | Q1–Q20 rows below |
| OR-23 | RX 12 purchase decision | TASK-035 `EXTEND`; RX 12 Primary, old versions fallback |
| OR-24 | Blue Baby Bottle SL | TASK-046 capture preflight `NEW` |
| OR-25 | OBS E-drive install baseline | TASK-047 P-OBS-0 exact root `E:\SteamLibrary\steamapps\common\OBS Studio\bin` and `bin\64bit\obs64.exe` installed-target inventory/build/ABI probe; official SDK/Plugin Template source/headers/license are separately identified `P0 NEW` |
| OR-26 | Re-display Q1–Q20 | Ver.1.2 history `GOV` |
| OR-27 | Confirm under-discussed sections | Ver.1.2 audit and this Crosswalk `GOV` |
| OR-28 | Q21–Q28 decisions | Q21–Q28 rows below |
| OR-29 | Two Critic passes with corrections | P-VS-0 design review Evidence `GOV` |
| OR-30 | Final Judge | P-VS-0 Judge Evidence `GOV` |
| OR-31 | Q29–Q44 and staged locales | Q29–Q44; TASK-046 locale gates |
| OR-32 | Final clean rewrite | imported byte-exact Ver.1.2 plus checksum `GOV` |

## Decision Register Q1 through Q44

| ID | Decision | Owner / route |
|---|---|---|
| Q1 | AI scroll recommendation + manual trim | TASK-046 |
| Q2 | paused segment incomplete; restart sentence | TASK-046/043 |
| Q3 | Draft/YouTube/Professional presets | TASK-046/048 |
| Q4 | gain changes only before recording | TASK-046 |
| Q5 | 30/60/90/120 min + shortage correction | TASK-046 |
| Q6 | proposed extra scripts need approval | TASK-046/027 |
| Q7 | confirm exclusive-job impact/time/recovery | TASK-020/043/014 |
| Q8 | only user-selected jobs resume | TASK-020/043 |
| Q9 | Japanese ~18 chars/line, max 2 | TASK-006 |
| Q10 | shared ID, separate subtitle/narration revisions | TASK-006/014 |
| Q11 | Voice Studio top-level destination | TASK-036 successor mock + TASK-046 |
| Q12 | basic view + advanced settings | TASK-036 successor mock + TASK-046 |
| Q13 | project retention; no default auto-delete | TASK-046/017 |
| Q14 | encrypt private voice data | TASK-046/043/045 |
| Q15 | max two retries only for known local failures | TASK-043/014 |
| Q16 | staging until whole-output QA | TASK-014/003/043 |
| Q17 | device ETA + error range | TASK-020/043 |
| Q18 | crash loss max one segment | TASK-046/043 |
| Q19 | use exact target-machine probe baseline | TASK-047 P-OBS-0 owns OBS exact-path/build/ABI probe; TASK-046/035/020 retain their own exact probes |
| Q20 | Owner monetized video is first commercial scope | TASK-046/014/028 |
| Q21 | Qwen3 8B + Ollama planning candidate | TASK-027/028 `EXTEND` |
| Q22 | Character consistency from initial version | TASK-013/037/041 `EXTEND` |
| Q23 | freeze H3; isolate Wan2.2 evaluation | TASK-013/020/043 `EXTEND` |
| Q24 | evaluate ACE-Step; MusicGen not commercial default | TASK-013/026/028 `EXTEND` |
| Q25 | evaluate Stable Audio for SFX/ambience | TASK-013/026/028 `EXTEND`; independent of P-OBS-0/1/2 and neither authorizes nor blocks production recording |
| Q26 | keep small; add large-v3-turbo choice | TASK-006/023 `EXTEND` |
| Q27 | noncommercial artifacts blocked from commercial route | TASK-028/003/037/044 `EXTEND` |
| Q28 | separated E-drive runtimes/models/outputs | TASK-020/043/045 `EXTEND` |
| Q29 | RX 12 Standard Primary | TASK-035 `EXTEND` |
| Q30 | multiple Character Profiles and revisioned copy | TASK-013/037 `EXTEND` |
| Q31 | identity anchors vs scene variables | TASK-013/037/041 `EXTEND` |
| Q32 | YouTube 16:9/1080p + Shorts 9:16 | TASK-044/045 `EXTEND` |
| Q33 | initial video generation in 3–10 s shots | TASK-013/027 `EXTEND` |
| Q34 | Instrumental BGM formal; vocals experimental | TASK-013/026/028 `EXTEND` |
| Q35 | one-shot SFX + loop ambience bed | TASK-013/026 `EXTEND` |
| Q36 | Local normal mode; explicit Research Mode | TASK-027/028/032 `EXTEND` |
| Q37 | Local Primary; per-project/per-job Cloud GO | TASK-028/032/043 `EXTEND` |
| Q38 | model information before individual install | TASK-033/043/045 `EXTEND` |
| Q39 | E-drive free floor=max(15%,200 GB) | TASK-020/043 `EXTEND` |
| Q40 | envelope encryption + password recovery package | TASK-046/043/045 `NEW+EXTEND` |
| Q41 | Owner review + consented blind release review | TASK-048 `NEW` |
| Q42 | use-case presets; YouTube -14 LUFS-I/-1 dBTP target | TASK-011/026/035 `EXTEND` |
| Q43 | Japanese, English, Simplified Chinese, Korean, Taiwan Traditional Chinese | TASK-046 staged locale gates |
| Q44 | first complete 60–90 s work | TASK-046/014/003/037/041/026/022/044 |

## No-duplicate ownership decision

TASK-046/047/048 add only missing Voice Dataset, OBS capture and Calibration
truth. Existing Asset, Candidate, Human decision, Timeline, Export, Provider,
Credential and recovery owners remain authoritative. TASK-004 and TASK-044 are
not reopened, and no second launcher, Queue, Asset registry or Timeline store
is created.
