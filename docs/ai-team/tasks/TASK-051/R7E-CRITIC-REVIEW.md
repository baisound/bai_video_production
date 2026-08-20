# TASK-051 R7E — Critic Review

## Review boundary

Reviewed the R7E detailed design, Product diff, concurrency boundaries, packaging changes and focused regression results after implementation.

A separate agent runtime was not available in this execution environment; therefore this is a distinct post-implementation Critic pass in the same session and is **not claimed as independent-agent evidence**. Windows Human Acceptance remains independent Owner-observed runtime evidence.

## Findings

### Critical

`0`

### High

`0`

### Medium

1. **Real PyAV native decode cannot be executed in the current Linux/container runtime.**
   - Mitigation: fake-PyAV behavioral tests cover persistent open/seek/ring logic; Windows build dependency and PyInstaller smoke are strengthened to require PyAV; real Windows DBD media remains a mandatory Human Acceptance gate.
   - Disposition: `ACCEPTED_PENDING_REQUIRED_WINDOWS_HA`; does not permit TASK-051 closure.

### Low / informational

- The UI's canonical frame model remains average-FPS based, as it was before R7E. Highly variable-frame-rate media may map PTS to nominal frame indices imperfectly. DBD recording acceptance must verify actual target media. This does not weaken ROI normalization or saved HUD geometry contracts.
- Hardware-specific decode acceleration is intentionally not introduced; CPU PyAV is the portable baseline and GPU decode remains a later optional optimization only if evidence requires it.

## Safety review

PASS:

- no network or paid-provider effect;
- no background installer or dependency auto-install;
- no schema/Knowledge mutation;
- no unbounded queue;
- bounded ring memory;
- stale source results fail closed at generation and UI-source checks;
- PyAV container ownership remains one worker thread;
- Tk UI mutation remains on Tk thread;
- worker shutdown is bound to root destruction;
- package smoke now detects missing PyAV runtime.

## Judgment

`PASS_WITH_WINDOWS_HUMAN_ACCEPTANCE_REQUIRED`

R7E is ready for patch delivery and Windows Human Acceptance. TASK-051 remains open.
