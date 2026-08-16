# TASK-036 P-UX-1C final native parity implementation Evidence

Date: 2026-08-16
Unit: `TASK-036 / P-UX-1C V6.1.1 NATIVE PARITY CLOSURE`
State: `LOCAL_FINAL_PASS / HOSTED_CLOSURE_PENDING`

## Scope

This unit closes the remaining packaged-native observation gap without changing
Product runtime or package bytes. The native gate now covers every V6.1.1
primary surface required by the accepted design and every top-level menu rather
than relying on a partial Home/File/Settings/Export/Edit sample.

The immutable Windows one-dir package under test is bound by executable SHA-256
`9d35016d94e1c5119ca3f2c38dc9b8e29b539bde39820495fcb30c6f1878d7fa`.
No runtime source changed after that package was built, so a package rebuild is
neither required nor claimed by this validation-only unit.

## Native matrix

The accepted machine-readable receipt is
`evidence/native/task036-pux1c-final-r0-01/task036-pux1c-native-closure.json`,
SHA-256
`dee4cbf045b5a62311ad98d3922d3cff59c02388dfc21638d2f1ce0a47e2b911`.

Observed PASS conditions:

- maximized WebView client coverage with no uncovered bright right/bottom edge;
- Home, WORLD LOCK, Scene Design, Edit, Quick, Settings and Export visible with
  required anchors inside the native client;
- File, Edit, View, Project, Generate and Export menu contracts, including
  enabled/disabled membership, concrete disabled reasons and Escape focus
  restoration;
- nine Settings categories and Settings Escape focus restoration;
- Timeline zoom, horizontal scroll and native pointer scrub;
- Track visibility, lock, mute and height round-trip through Python-owned state;
- native picker cancellation without process exit;
- three physical display moves, with monitor DPI and accessibility text scale
  recorded separately;
- semantic UI Automation controls and conversation-free private-mode restart;
- Provider, paid, Credential, Human ACCEPT/LOCK, Resolve, Cubase, Release and
  Deploy effects all remained `false`.

Capture SHA-256 receipts:

| Surface | SHA-256 |
|---|---|
| Home | `1f13fe6dca5d86870269fda3ed9af4cbb9ee01f867667da029e17002cba79958` |
| File menu | `c0c9b2aae7fe87da8194cfb750e4744776103136d1638e8326354ee797dbc7db` |
| Settings / Audio | `8f98fc047b651a093aec437e255d324a188e0b3af3e293337d1ade652f41fc0c` |
| WORLD LOCK | `c25cf82257b91a7580a56b05967edb4744f5f11493193d15d5f74496d86db62b` |
| Scene Design | `81f05372b0a06094339956fcf405efd54a350aea7e00c4ae669902ae17aaeb57` |
| Quick | `bc6b2d2d5d8af072bba309fe5c47b311bae7bc9c13b5b96aa645129619be7646` |
| Export | `f68ff3cb42be81d23be993f88f0f419f49347e595584ebcc1bcf8dca775d2cfd` |
| Edit after scrub | `0089d23a995158a10f7ea086338cc66894d1b44b2cf53c4246431fa183de71f4` |

Independent visual inspection found no Product clipping, uncovered client
region, fabricated success or enabled unauthorized effect. The IME toolbar
visible outside the app in the Settings capture is an OS-owned overlay and not
a Product layout defect.

## Truthful disabled boundaries

The accepted V6.1.1 convergence rule permits a control to be implemented,
truthfully disabled with a concrete dependency reason, or represented by the
explicit accepted replacement. The following controls therefore remain
disabled and do not block visual/native parity:

- missing proposal/Blueprint/Quick authoring services;
- Provider generation and generated-media execution;
- unbound Asset import/tag/subtitle and playback services;
- unbound Export preset/enqueue and external NLE execution;
- final approval and other Human authority gates.

This closure does not turn any of those boundaries into Product capability.

## Validation

- TASK-036 focused regression: `193 / 193 PASS`;
- full WSL2 Ubuntu regression: `1270 / 1270 PASS`;
- Windows Python `compileall`: PASS;
- embedded Desktop JavaScript syntax: PASS (`scripts=1`);
- PowerShell AST parse: PASS;
- `git diff --check`: PASS.

## Critic

Builder Critic:

- the previous native gate omitted three required primary surfaces and five
  top-level menu contracts;
- the corrected gate uses constituent UI Automation elements, explicit
  enabled/disabled sets and capture files rather than digest-only assertions;
- runtime/package identity is unchanged and no external effect is introduced.

Security/Completeness Critic:

- disabled actions require exact HelpText rather than inferred authority;
- every required surface has a committed image and SHA-bound receipt;
- native restart, display, accessibility and effect-zero predicates remain;
- no host path, Credential, private body or Provider result is published.

Residual Critic C/H/M: `0 / 0 / 0`.

## Provisional Judge

`JUDGE=P_UX_1C_LOCAL_FINAL_NATIVE_PARITY=PASS_FOR_HOSTING`

`V6.1.1_VISUAL_PARITY_PASS` becomes canonical only after this exact patch passes
all hosted checks, merges normally to `main`, and post-merge CI/Security pass.
No Tag, GitHub Release or Deploy is selected by this Evidence.
