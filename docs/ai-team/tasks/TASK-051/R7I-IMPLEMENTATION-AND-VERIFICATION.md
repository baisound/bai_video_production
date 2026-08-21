# TASK-051 R7I — Implementation and Verification Evidence

## Result

`IMPLEMENTED / LOCAL PASS / WINDOWS HUMAN ACCEPTANCE PENDING`

## Implemented scope

- canonical Shared Media naming (`TkTrainingMediaSession` / `TkTrainingMediaPlayer`) with backwards-compatible legacy aliases;
- audible 1x playback via bounded `FfplayAudioController`;
- volume and mute controls on standard Shared Media surfaces and HUD calibration;
- preserved canonical 12-button transport contract;
- minimum media-height layout guard and scrollable form containers;
- `動画から一括学習` two-column settings + lower Shared Media layout;
- range-aware safe batch Crop staging with a total candidate ceiling and explicit confirmation;
- `画像学習データ` three-tab workflow with search modal and registered-item edit modal;
- `右上通知を学習` three-tab workflow with media/OCR split and edit modal;
- trivia tab ordering and edit modal;
- additive unified visual registration provenance fields with legacy CSV compatibility;
- exact visual relabel now preserves R7I provenance fields;
- generic long-running UI jobs moved to Python outcome queue + Tk-owned polling;
- Fit-to-View media floor retained across all five media surfaces;
- R7H opt-in diagnostics retained and extended with audio lifecycle events.

## Local verification

Focused R7I tests cover audio command/state behavior, twelve controls, shared media ownership, tab/layout contracts, Fit-to-View guardrails, modal edit routes, batch range bounds and registration provenance preservation.

TASK-049/050/051 compatibility tests are re-based only where assertions referred to superseded R7G/R7H class/display names. No implementation was reverted to satisfy stale UI assertions.

The real Tk renderer test remains environment-sensitive and is skipped only when no display server exists. Windows packaged Human Acceptance remains the authoritative evidence for audible playback and final layout visibility.

## Exact local verification — 2026-08-20

- R7I/R7H/R7G/R7E focused media/workflow suite: `38 PASS / 1 Tk-display-only SKIP`.
- TASK-049/TASK-050/TASK-051 compatibility suite including R7A accepted-source gate: `317 PASS / 1 Tk-display-only SKIP`.
- Full repository, sharded to avoid the current container command-time ceiling: `2283 PASS / 2 environment-only SKIP` (`622 + 547 + 628 + 486`).
  - R7H real-Tk renderer test skip: no display server in the current Linux runtime.
  - TASK-047 Inno Setup acceptance skip: Windows-only.
- `py_compile`: PASS for every R7I-modified source module.
- `compileall src/ai_video_production`: PASS.
- `git diff --check`: PASS.
- R7A canonical LF-text SHA-256 synchronized to `6500ca40f72ffe32dcb0f75342923c5fb3f91d85548c56f46162de2224f46804`.

These are local/source regression results only. Audible Windows output, packaged Tk rendering, DPI behavior and real-video Fit-to-View remain Human Acceptance evidence.

## Residual boundary

Local tests cannot prove Windows audio device output, Windows DPI behavior or real packaged visual fit. Those remain R7I Human Acceptance gates. No Release or Task closure is claimed by this record.
