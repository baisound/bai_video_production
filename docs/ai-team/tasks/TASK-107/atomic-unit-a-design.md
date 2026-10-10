# TASK-107 Atomic Unit A — Settings modal reachability design

## Observed failure

At 1909 x 1074 the packaged V6.1.1 Settings modal visibly rendered the central
AI-model workloads, but its lower content was clipped and the Owner could not
reach `AIモデル設定を保存`.

The accepted screenshot and Owner read-back distinguish this from a missing
handler or model-Catalog failure: upper model rows rendered and the modal itself
was open, but the bottom action was outside the reachable viewport.

## Root cause

The current CSS combines:

- `.modal { max-height: 90vh; overflow: hidden; }`;
- `.settings-layout { min-height: 520px; }`;
- `.settings-content { overflow: auto; }`.

The modal clips overflow but does not establish a definite grid/body height.
The fixed Settings minimum height and intrinsic content therefore expand below
the modal's maximum height instead of giving `.settings-content` a smaller
scrollport. `overflow: auto` alone cannot scroll without a constrained height.

## Repair

The modal becomes a two-row grid:

```text
40px header
minmax(0, 1fr) Settings body
```

Its height is the smaller of the accepted desktop height and `90vh`. The
Settings layout consumes exactly that body, uses `min-height: 0`, and keeps
outer overflow clipped. Both navigation and content panes may shrink and own
their own vertical scroll. The narrow layout explicitly changes to an
auto-sized navigation row plus a shrinkable content row.

No JavaScript, model selection, save RPC, Provider, credential or Planning
state-machine change is required.

## Verification boundary

Static tests lock the height/overflow invariants and existing Settings
accessibility markup. Focused regression confirms the generated Shell contract.
Only a freshly integrated packaged-native run at the accepted viewport may
convert the Owner's F3 reachability result from FAIL to PASS.
