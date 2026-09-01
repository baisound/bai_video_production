# TASK-073 Voice Studio Successor Mock Manifest

- Mock revision: `VOICE_STUDIO_SUCCESSOR_MOCK_D4_R4`
- Governing requirement: `TASK-046 P-VS-1B successor-mock gate`
- Source design: `TASK-073 D4-R4 UX closure`
- Artifact: `p0v-voice-studio-successor-mock.html`
- Artifact SHA-256: `1E70C7FC3CF7BCDF63A3C409F8CDDC3FA7DB29FDEC7F1F7B8C5F0567BE9683ED`
- Owner check: `PENDING`
- Product source mutation: `0`
- Runtime/model/audio/private-data effect: `0`

## Design system

The mock deliberately preserves BAI Video Production V6.1.1.

- Core palette: `#0a0d11`, `#090c10`, `#12171d`, `#2a333d`, `#edf2f6`,
  `#4d8fd1`.
- Semantic status: `#59c792` verified, `#dfa654` Human/wait,
  `#dd6868` blocked.
- Typography: `Segoe UI`, `Noto Sans JP`, `Yu Gothic UI`, system fallback.
- Density: desktop production-tool density; no marketing hero, decorative
  illustration, floating pill system or unrelated new navigation.
- Signature element: `Voice Signal Rail`。It is a compact five-stage receipt
  relationship (`参照 → モデル → 生成 → QA → 試聴`), not a generic decorative
  stepper.  Each state names the producing Product responsibility.
- Stage navigation: all canonical V6.1.1 destinations are retained with the
  exact labels and numbers `H, 1..11, A, Q`; `音声制作` remains `7`.  Every
  visible stage destination has an in-memory route, active state, return action
  and focus transfer.  Settings has the same route/current-state contract.
  Non-Voice destinations explicitly identify themselves as transition-contract
  placeholders rather than implemented Product screens.
- Model selection has one location: `設定 > AIモデル`.  Planning, image,
  video and audio selectors exist only there.  Voice Studio displays the
  current audio-model receipt and links back to that central setting; it has
  no editable model selector of its own.

## Layout

```text
existing app chrome
existing stage navigation
┌ left: Voice route/reference ┬ center: signal/result/waveform ┬ right: facts/actions ┐
└ current durable job strip and public-safe guidance                                  ┘
```

The mock demonstrates reference preparation, central model selection and
Voice Studio readback, CPU/GPU/AUTO preference,
readiness, generation confirmation, progress, technical facts, private
play/stop controls and accept/reject/retest/regenerate decisions.  Retest keeps
the same candidate; regenerate prepares a different operation.  All interactions
are in-memory mock transitions.  It opens no file, starts no process, loads no
model and writes no data.

## Genericness self-critique

- Avoided a dashboard of interchangeable rounded cards; the central rail and
  waveform are specific to the Voice workflow.
- Avoided oversized title/marketing copy; content density matches V6.1.1.
- Avoided new fonts, gradients as decoration and ornamental animation.
- Status is not communicated by color alone; every state has text and owner.
- Internal hashes, paths, revisions, PIDs and capability tokens are absent.
- The settings receipt is an in-memory UX demonstration.  It cannot be
  mistaken for persisted Product authority or runtime/model verification.

## Accessibility

- keyboard-reachable controls and visible `:focus-visible` outline;
- semantic buttons, selects, headings, labels and `aria-live` status;
- every route transfers focus to its destination and offers a visible back or
  Voice Studio return action;
- disabled state has textual explanation;
- `prefers-reduced-motion` removes status transitions;
- minimum contrast follows the existing dark Product palette.

## Owner check questions

1. Is `音声制作 > Voice Studio` the expected destination?
2. Is selecting each free/local model only in `設定 > AIモデル`, then seeing
   the audio-model receipt in Voice Studio, the expected flow?
3. Does the difference between preferred compute and effective backend read
   clearly?
4. Are failure/wait messages actionable without exposing technical internals?
5. Are accept/reject/retest and regenerate clearly distinct from one another
   and from Asset adoption/Export?
6. Do all 14 stage destinations and Settings make their transition and return
   path clear, without making placeholder content look implemented?
7. Is the amount of information suitable for normal Owner operation?

## Gate

Only the new P0-V Voice Studio successor / P-VS-1B TASK-036 amendment remains
`START0`; unrelated TASK-036 work is not blocked.  The amendment cannot start
until this exact D4-R4/mock/manifest identity is merged to canonical main,
hosted checks succeed, a fresh-main readback matches the accepted hashes, a
separate `TASK073_OWNER_MOCK_CHECK_RECEIPT_V1` binds those exact identities and
the accepted D4-R4 bundle with `OWNER_CHECK_PASS`, and a separate TASK-036 P0-V
Atomic Unit with exact Allowed Files and lock is authorized.  This manifest
remains immutable with `Owner check: PENDING`; it is never edited to record the
decision.  Any visual or flow change after the separate check creates a new
revision and requires a new exact check.
