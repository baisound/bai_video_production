# TASK-054 R7B External UI Operation Pre-execution

Date: 2026-08-26
State: PRE-EXECUTION / NOT_STARTED
Development depth: DEV-3 HIGH ASSURANCE

## Authority

Owner AUTONOMY continuation permits existing-authority application launch and
operation. This unit observes the already-built canonical TASK-049 Training
Studio package. It does not install or configure software, acquire a model,
load private media, execute a Provider, train, mutate Dataset/Binding/Timeline/
Resolve, promote a model, release, deploy, or activate Production.

## Target identity

- executable: builds/task049-dist/BAI DbD Training Studio/BAI DbD Training Studio.exe
- prior accepted SHA-256: 1873504D657DD216496BBE075C1E092FE1299CCD9E26E66144826E8222059903
- expected title: BAI DbD Training Studio
- canonical entry/spec: packaging/task049_training_studio_windows_entry.py and packaging/task049_training_studio.spec

The executable hash must be read back before launch. A mismatch stops the unit.

## Procedure

1. Confirm the R7B worktree is clean and fresh-main based.
2. Confirm the executable exists and its SHA-256 matches the prior R7 Evidence.
3. Launch the existing executable without installer or settings mutation.
4. Select exactly one returned BAI DbD Training Studio window.
5. Capture screenshot and accessibility state.
6. Exercise the 実況・解説AI outer tab and its four nested panels with external
   click or keyboard input, refreshing state after every action.
7. Observe scroll behavior and visible disabled/safe-state controls.
8. Close the application gracefully and confirm process/window disappearance.
9. Record exact PASS/FAIL/NOT_CONFIRMED observations in the result document.

## Safety and recovery

- No credential, private media, Dataset body, transcript, or secret is entered.
- No confirmation dialog that changes settings or permissions is accepted.
- No stale screenshot ID, coordinate, window handle, or accessibility index is
  reused after state changes.
- If helper enumeration or capture fails twice, stop UI input and record
  NOT_CONFIRMED.
- Rollback is graceful application close only; no persistent state is expected.
