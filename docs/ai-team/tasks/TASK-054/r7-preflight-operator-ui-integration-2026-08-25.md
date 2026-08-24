# TASK-054 R7 Preflight Operator UI Integration

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `INTEGRATED / PACKAGED BUILD NEXT`

## Outcome

The existing TASK-049 Training Studio now exposes one top-level `実況・解説AI` tab directly after existing実況/豆知識 intake. It contains the R5B preview, R5C model/preflight, R5D Dataset/evaluation and R5E operation/recovery panels as four clear subtabs. R5A remains the global mode selector visible across every tab.

## Safe empty state

Opening the tab constructs presentation widgets only. It does not load private bodies, start inference/training/Provider/worker, change Dataset/Binding or create a second Product entrypoint. Until canonical loaders/application services are supplied, panels explain that Evidence/route/review is unavailable. Model preflight returns stable `ERR_TASK054_R3D_REQUIRED`; cancel/resume callbacks explicitly report `未送信` rather than pretending an action occurred.

## Operator route

```text
BAI DbD Training Studio
 -> 実況・解説AI
    -> 現在の実況・解説
    -> モデルと事前チェック
    -> Datasetと評価
    -> 処理状況と復旧
```

The existing packaged `task049_training_studio_windows_entry.py -> main()` and PyInstaller spec remain authoritative. Static imports ensure the panels enter the package without another EXE.

## Remaining acceptance

Focused tests prove source wiring, labels, existing packaged entrypoint and R5 panel contracts. Real Tk rendering, DPI/scroll behavior, button interaction and packaged startup are R7 native observations, not yet PASS. Real Evidence loading and execution stay blocked by their application-service/Human Gates.
