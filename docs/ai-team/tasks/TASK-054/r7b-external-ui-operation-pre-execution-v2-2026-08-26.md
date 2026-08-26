# TASK-054 R7B External UI Operation Pre-execution V2

Date: 2026-08-26
State: PRE-EXECUTION / NOT_STARTED
Supersedes for execution: r7b-external-ui-operation-pre-execution-2026-08-26.md
Development depth: DEV-3 HIGH ASSURANCE

## Reason for revision

The prior accepted packaged executable was not present at its recorded output
path. No application was launched. The V2 procedure therefore performs a
bounded rebuild from fresh main before selecting the exact executable identity.

## Authority and boundaries

Owner AUTONOMY continuation permits existing-authority build and application
launch/operation. This unit does not install or configure software, acquire a
model, load private media, execute a Provider, train, mutate Dataset/Binding/
Timeline/Resolve, promote a model, release, deploy, or activate Production.

## Source and build

- source main: a190d8663e848414ade7acc08e3bea1275b60da6
- entry: packaging/task049_training_studio_windows_entry.py
- spec: packaging/task049_training_studio.spec
- build command: Python -m PyInstaller --clean --noconfirm --distpath builds/task049-dist --workpath builds/work/task054-r7b packaging/task049_training_studio.spec
- expected output: builds/task049-dist/BAI DbD Training Studio/BAI DbD Training Studio.exe

The build must return exit 0. The new executable size and SHA-256 are recorded
before launch and become the sole R7B target identity.

## Operation procedure

1. Confirm the R7B worktree is clean except for these Evidence documents.
2. Read back Python and PyInstaller versions without changing them.
3. Run the bounded build command from the fresh-main R7B worktree.
4. Hash the exact output and record its size.
5. Launch that exact existing output without installer or settings mutation.
6. Select exactly one returned BAI DbD Training Studio window.
7. Capture screenshot and accessibility state.
8. Exercise the 実況・解説AI outer tab and four nested panels with external
   click or keyboard input, refreshing state after each action.
9. Observe scroll behavior and disabled/safe-state controls.
10. Close gracefully and verify the window disappears.

## Safety and recovery

- No credential, private media, Dataset body, transcript, or secret is entered.
- No confirmation dialog that changes settings or permissions is accepted.
- No stale screenshot ID, coordinate, handle, or accessibility index is reused.
- Helper enumeration/capture failure is retried only as allowed by the
  computer-use recovery rule, then recorded as NOT_CONFIRMED.
- Build failure leaves no accepted executable identity and prevents launch.
- Rollback is graceful application close; generated build output is retained as
  Evidence and is not installed or promoted.
