# TASK-041 — Audio Workspace Application Service Contract Ver.1.0

- Date: 2026-08-13
- Status: `APPLICATION_SERVICE_FOUNDATION_PASS / USER_WORKSPACE_NATIVE_PENDING`
- UI direction: NLE Audio Workspace integrated into the same BAI Video Production.exe.

## Canonical layout

```text
Left                  Center / Bottom Timeline              Right
Audio Assets          Source / Narration / SE / BGM        Audio Inspector
Candidate versions    Waveforms + placement ranges         Gain / role / status
Derived Assets        Playhead / mute / solo               Human decision
```

## Projection

Placement rows expose:

- Candidate and exact Asset SHA-256;
- Production lifecycle state;
- timeline start/duration;
- track role;
- reviewed gain;
- Human decision;
- actions currently allowed.

`ACCEPT` is not offered unless the Production Candidate is `LOCKED`.

## Human placement decision

Placement decision uses an exact one-shot confirmation bound to:

- Placement record hash;
- Candidate ID;
- Candidate Asset SHA-256;
- requested decision.

If Placement timing/gain or Candidate bytes/lock state change, confirmation becomes stale.

Accepting a Placement does **not** automatically compile TASK-026 and does **not** mutate Resolve.

TASK-026 compilation remains an explicit next stage. Unsupported gain/fade semantics remain a visible TASK-010 feature gap rather than silently disappearing.

## Non-destructive audio policy

Embedded VFX/generated-media audio stripping creates a derived Asset. Original source bytes are never overwritten by an Audio Workspace decision.
