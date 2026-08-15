# TASK-036 P-UX-1A Shell Composition Implementation and Native Evidence

Date: 2026-08-15
Task: `TASK-036 / P-UX-1A`
DEV Profile: `DEV-4 FOUNDATION CRITICAL`
Exact base main: `b771b9acae67fcd0ee41218d70a011e387beb300`
Branch: `codex/task-036-v611-shell-composition-implementation`

## Decision

The checked-in `BVP-UI-MOCK-V6.1.1.html` remains the absolute visual and
interaction-intent authority. P-UX-1A replaces the packaged runtime view with a
Product-owned V6.1.1 composition while retaining the existing
`Task036ShellBridge`, Application Services and durable stores as the only
runtime truth.

P-UX-1A is `LOCAL_PASS`. This is a composition checkpoint, not the final
`V6.1.1_VISUAL_PARITY_PASS`. Controls whose Product action is scheduled for
P-UX-1B are visibly disabled with a specific reason. No mock demo record,
random progress timer, front-end-only success, Provider dispatch or external
write was introduced.

## Implemented composition

- canonical File / Edit / View / Project / Generate / Export top menus;
- canonical H, 1..11, A and Q stage navigation;
- Home route cards plus Recent/Direct lower composition using the actual
  current Project instead of mock sample Projects;
- canonical Planning, Scene, WORLD LOCK, Scene Design, Start/End, AI Video,
  Audio, Asset Review, Edit, Final Review, Export, Asset and Quick surfaces;
- Edit Asset/Viewer/Inspector three-pane geometry and bounded real Timeline;
- Export settings, External Editing and per-job Export Queue composition;
- Settings dialog with all nine canonical navigation categories;
- Background Job panel and real Application Service snapshot projections;
- Project technical identity hidden behind an explicit disclosure instead of
  overwhelming the Home workspace.

## Native packaged acceptance

The Windows one-dir build completed with the repository build batch. Launch
from the long development checkout failed closed with the existing
`ERR_TASK036_INSTALL_PATH_TOO_LONG` policy. The same owned build was copied to
the dedicated short test path `C:\bvp-pux1a-native` and launched successfully
at 1600 x 900 on the current 125% Windows display scale.

Non-mutating native navigation was exercised through the WebView2 child window.
Visual inspection passed for:

- Home route / Recent / Direct composition;
- Edit Asset/Viewer/Inspector/Timeline composition with the actual Project
  projection (`3/3 Track`, `4/4 Clip`, `durable_state_in_javascript=false`);
- Export settings / External Editing / empty Queue composition;
- Settings nine-category layout and secret non-redisplay boundary.

Local capture hashes:

| Capture | SHA-256 |
|---|---|
| `p-ux-1a-home-converged.png` | `c60c2b668ab595eefe57ea2e5513d11645e3c89a7d8aebe2a6cb4d7dd2f37064` |
| `p-ux-1a-edit-native.png` | `1f1b378c4a696fb58ee4219fa57bccf0ecfead4b1f71268442f16dcb1d38f468` |
| `p-ux-1a-export-converged-native.png` | `85a4dbdcfbdb2db596494e72e9c4dc5f692d5f085a8b2970521299eaef2c6bd5` |
| `p-ux-1a-settings-native.png` | `f2fff2d6eb0baae02a81cc602d64da8d572d18540c3c29734a404b7553fd6fe1` |
| final packaged EXE | `4d4bb642b44ad097c38dca4df88d4b74f9ef75540f54aa920b94548037638420` |

The in-app browser kernel could not be provisioned in this session. Therefore
browser-tool visual acceptance is not claimed. The canonical mock was rendered
locally with installed Microsoft Edge at 1600 x 900 and compared with the real
packaged EXE; native EXE inspection is the accepted P-UX-1A evidence route.

## Validation

- focused TASK-036/TASK-044/V6.1.1 Shell tests: `46 / 46 PASS`;
- V6.1.1 visual contract subset: `6 / 6 PASS`;
- embedded JavaScript `node --check`: PASS;
- Python compile: PASS;
- Windows full regression: `1162 passed, 1 intentional non-Windows skip`;
- Ubuntu WSL2 full regression: `1163 passed`;
- Windows one-dir EXE build: PASS;
- `git diff --check`: PASS.

## Critic review

The implementation review identified two material visual divergences during
native inspection: Home exposed raw snapshot fields instead of the canonical
Recent/Direct composition, and Export omitted the canonical Settings/External
panels. Both were corrected and revalidated in the final package. Settings was
also expanded from four placeholder categories to the canonical nine-category
composition. Unresolved Critical/High findings: `0 / 0`.

## Boundary and next action

P-UX-1B remains required for the currently disabled mock interactions,
selection details, playback/controller operations, settings category mutation,
Quick inputs and exact export-preset composition. P-UX-1C remains required for
the full supported viewport/DPI, keyboard, menu, focus, accessibility and
conversation-free packaged restart matrix. Overall visual parity remains
unclaimed until those gates pass.

Native H3 replay, paid Provider execution, Credentials, Human ACCEPT/LOCK,
Resolve/Cubase mutation, Production Deploy, version change, Tag and Release were
not performed.
