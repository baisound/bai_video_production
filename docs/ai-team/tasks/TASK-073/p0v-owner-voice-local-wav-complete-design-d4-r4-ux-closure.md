# TASK-073 D4-R4 Owner-view UX Closure

## 1. Identity, cause and precedence

- Canonical predecessor: PR `#482`, merged as
  `efdcd77729732e3c50abb9e4a7e89ae2b7b37aa0`.
- Accepted parent D4-R3 hash:
  `146A30D68F625D264140C682CFB4162921800A8C3BFBADDF7F95CDCBC24459C0`.
- Parent D4-R3 bundle hash:
  `73FE6466B0DEE48BE3278B5ED2202F1334586D1456F108A7CCC425B38888C4EC`.
- State: `UX_CORRECTION_REVIEW_PENDING / TASK073_SOURCE_HOLD /
  TASK036_P0V_START0`.

The D4-R3 mechanical design remains immutable historical Evidence.  An
independent Owner-view mock QA performed after its merge found two High UX
contract gaps: Voice Studio exposed a second editable model selector, and the
visible Settings and fourteen stage destinations did not navigate.  Therefore
the old bundle is not eligible for TASK-073 implementation or TASK-036 P0-V
consumption.  This addendum supersedes only the mock UX/navigation contract,
mock/manifest identities, Owner-check binding and completion bundle references.

No Product source, model, file, GPU, audio, private data or external effect is
performed by this correction.

## 2. One authoritative model-selection location

The sole editable Product location is `設定 > AIモデル`.  Its closed categories
are `企画`, `画像`, `動画` and `音声`.  A feature page may display only a
read-only current selection and its Product-issued settings receipt.  It may
offer an action that routes to the relevant central selector, but it must not
duplicate that selector.

For the successor mock:

- Voice Studio contains no editable audio-model selector;
- `現在のローカル音声モデル` displays the central audio selection;
- `AIモデル設定を開く` routes to `設定 > AIモデル` and focuses `音声`;
- saving central settings advances the in-memory receipt revision, returns to
  Voice Studio and refreshes its readback;
- selecting `未設定` produces `AUDIO_MODEL_REQUIRED`, disables render and
  gives the exact corrective route;
- every central-model save closes any open generation confirmation, and both
  confirmation-open and generation-start revalidate `READY`, reference
  currentness and a non-empty audio model;
- a model change never relabels an already generated candidate as belonging to
  the new model.  The mock resets the visible candidate workflow before using
  the new receipt;
- a save attempt while generation is running is rejected without changing the
  current selection.
- saving the same audio selection may advance the central receipt and close an
  open confirmation, but must not alter `RESULT`, `PLAYING`, `LISTENED`,
  `RETEST` or terminal Voice state and must not create a second playback or
  render path.

The in-memory receipt is demonstrative UX state only.  It is not serialized,
self-minting authority, runtime verification or an implementation receipt.
TASK-036 must consume the future canonical settings/model-inventory owners.

## 3. Total visible-navigation contract

Every visible button in the canonical stage bar has one route and one label:

| marker | route | label |
|---|---|---|
| `H` | `home` | `ホーム` |
| `1` | `planning` | `企画` |
| `2` | `scene-split` | `シーン割` |
| `3` | `world-lock` | `WORLD LOCK` |
| `4` | `scene-design` | `Scene設計` |
| `5` | `start-end` | `Start / End` |
| `6` | `ai-video` | `AI動画` |
| `7` | `voice-studio` | `音声制作` |
| `8` | `asset-review` | `素材確認` |
| `9` | `editing` | `編集` |
| `10` | `final-review` | `最終レビュー` |
| `11` | `export` | `書き出し` |
| `A` | `asset-management` | `素材管理` |
| `Q` | `quick-generate` | `クイック生成` |

The top-right Settings button routes to `settings`.  Route activation is
in-memory and must:

1. update the sole active stage, or the Settings button for `settings`, and
   expose that current destination through `aria-current`;
2. transfer keyboard focus to the destination;
3. provide both a previous-route action and an explicit Voice Studio return;
4. preserve unrelated Voice Studio state while merely visiting a route;
5. never run a Product operation, scan a file or claim that a placeholder
   feature is implemented.

Because this is a TASK-073 Voice design artifact, non-Voice destinations use a
bounded transition-contract screen.  It explicitly states that their Product
content belongs to TASK-036 integration and the corresponding feature Task.
A non-working decorative control and a false implemented-state claim are both
forbidden.

The six top chrome menu names (`ファイル`, `編集`, `表示`, `プロジェクト`,
`生成`, `エクスポート`) are retained only as non-interactive static chrome in
this Voice-specific artifact.  They must not be semantic buttons until a
separately owned mock or Product integration supplies their actions.

## 4. Mock state interaction

The navigation layer and Voice generation layer have independent in-memory
state.  Visiting another route cannot start, retry, stop, accept, reject or
discard a Voice operation.  Central model save is the only exception and is
handled by section 2.

The existing D4 terminal-decision, Stop, Retest and Regenerate rules remain in
force.  The currently selected model label is injected into the generation
confirmation; a stale hard-coded model label is forbidden.

## 5. Closed static and interaction acceptance

The exact D4-R4 artifact must satisfy all of the following before review PASS:

1. JavaScript syntax PASS.
2. Exactly fourteen unique `data-route` stage destinations matching section 3.
3. Exactly one central audio-model selector and zero `voiceModel` feature-page
   selectors.
4. Settings, Voice Studio CTA and all stage buttons have registered handlers.
5. Settings audio focus, save, cancel, back and Voice Studio return are
   reachable by keyboard.
6. Central audio selection readback, receipt revision advance and
   `AUDIO_MODEL_REQUIRED` fail-closed state are observable.
7. A generated/listened/terminal candidate cannot survive an audio-model
   change as if it had been created by the new model.
8. Every non-Voice destination declares itself a transition-contract mock and
   contains no implementation-success wording.
9. Existing Voice render/listen/Stop/Accept/Reject/Retest/Regenerate handlers
   remain present; Regenerate re-enables the new operation's confirmation only
   when its retained reference and central audio model remain current, and
   clears the old candidate duration, technical metrics, decision help and
   effective-compute readback before showing `READY_TO_RENDER`.
10. Owner-view QA and independent DEV-4 Critic/Judge both report
    `Critical=0 / High=0`; neither a static hash nor this document can
    self-assert that result.

Required negatives include a second feature-page model selector, missing or
duplicate route, visible button without handler, settings save during running,
audio model unset, confirmation opened before the model becomes unset, stale
confirmation label, Regenerate with a permanently disabled confirmation,
Regenerate retaining old candidate facts, a same-audio save that rewinds or
duplicates a result/playback/terminal state, enabled chrome menu controls with
no handler, focus dead-end, and placeholder text that claims the Product
function is implemented.

## 6. D4-R4 design bundle

The replacement design bundle is the canonical compact UTF-8 JSON array in
this order:

```text
[
  ["task073_d4", "975A5ABBB4471FA3E618C47A35E5EFED02960A1524657AC910290C25CA5739A1"],
  ["task073_d4_r1", "A764C4DC49F51C198DFAAF6C038C0C7644BDB9B7B6AD1286326E49E3E5B409AA"],
  ["task073_d4_r2", "ED96216F3CF91B0AC10AC26D14A081268D02E233C1871A87B104716600C26020"],
  ["task073_d4_r3", "146A30D68F625D264140C682CFB4162921800A8C3BFBADDF7F95CDCBC24459C0"],
  ["task073_d4_r4", "SELF_SHA256_EXCLUDED_FROM_PREIMAGE"],
  ["voice_studio_mock", "1E70C7FC3CF7BCDF63A3C409F8CDDC3FA7DB29FDEC7F1F7B8C5F0567BE9683ED"],
  ["voice_studio_manifest", "1BA94AD93187E19B401AD86896F929DBBF6288C62F5F1BD36821DD323EECA17C"]
]
```

At freeze, the R4 row is replaced by this file's exact SHA-256 and the compact
array SHA-256 is recorded in `design-review-receipt.md`.  The placeholder is
never a runtime, schema, handoff or completion value.  D4-R3's old bundle is
historical only after this correction.

The separate `TASK073_OWNER_MOCK_CHECK_RECEIPT_V1` keeps its D4-R3 field order
and validation rules but must bind:

- `mock_revision=VOICE_STUDIO_SUCCESSOR_MOCK_D4_R4`;
- the exact D4-R4 mock, manifest and design-bundle digests;
- a new Owner action for this revision.

An Owner check for D4-R0 cannot be replayed or upgraded.

## 7. Completion and downstream hold

`TASK073_IMPLEMENTATION_PR_READY`, `TASK073_IMPLEMENTATION_COMPLETE` and the
TASK-036 P0-V consumer must bind the accepted D4 through D4-R4 bundle.  Until
this exact input receives fresh Owner-view mock QA `PASS`, independent
`C/H=0` and Judge `PASS`:

- TASK-073 implementation is held;
- TASK-036 P0-V implementation and packaged E2E are `START0`;
- the merged D4-R3 bundle must not be reused as an accepted dependency.

This correction does not authorize real Owner audio, model/runtime download,
paid/cloud execution, Asset adoption, Export, Release, Deploy or Production
Activation.
