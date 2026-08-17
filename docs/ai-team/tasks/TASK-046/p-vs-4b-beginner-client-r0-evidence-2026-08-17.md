# TASK-046 / P-VS-4B Beginner Client R0 — Design, Critic and Evidence

## Outcome

R0 implements a standalone beginner-facing presentation client over the hosted
`VerticalSliceWorkflowRevision`.  It shows the complete twelve-step route from
reviewed OBS recordings to a separately admitted narration model/Master WAV.
It is intentionally display-only: it cannot read audio, select arbitrary WAV
folders, adopt a Dataset, dispatch a Job, train or load a model, render audio,
approve a candidate, publish, Release or Deploy.

The synthetic preview is available with:

```powershell
python -m ai_video_production.voice_model_builder_beginner_client --demo --locale ja
```

The preview contains no Owner voice and exposes no action button.  It is the
client identity and presentation foundation for the separately governed
Windows installer slice.

## Canonical boundary

- Input truth remains `TASK-047`, `TASK-048`, `TASK-003`, `P-VS-3B`,
  `P-VS-4A` and `TASK-014` through the existing workflow contract.
- `BeginnerClientSnapshot` is a deterministic projection, not a second
  Dataset/Job/Model/Consent/Asset truth.
- `UNKNOWN` and failed states become `BLOCKED`; future steps remain
  `NOT_CHECKED`.  No zero, 95%, 100%, ready or success value is fabricated.
- All twelve steps carry `operation_effect_authorized=false` and the snapshot
  fixes every effect-started flag to false.
- Public projection removes workflow/source hashes and coordinates.
- Japanese and English labels are closed and tested.

## Acceptance

- exact twelve-step order and localized labels;
- deterministic canonical JSON/digest and schema/runtime parity;
- schema mirror byte equality;
- forged effect flag, reordered step, unknown field and digest tamper rejection;
- public coordinate/private-path suppression;
- HTML escaping and absence of action buttons;
- `UNKNOWN` cannot be projected as complete;
- no subprocess/network/provider/model/audio/filesystem runtime import surface.

## Critic pass 1

- Builder: an unrestricted GUI button could bypass the structured external
  operation contracts. Correction: R0 is display-only and has no action API.
- Security: a friendly screen could leak canonical source coordinates.
  Correction: the public projection includes labels/state only.
- Compatibility: client state could become new workflow truth. Correction:
  every snapshot binds and validates the hosted workflow revision/hash.

## Critic pass 2 / Judge

- Builder: twelve ordered steps, deterministic digest, schema/runtime parity — PASS.
- Security/privacy: body/path/credential suppression and effect flags false — PASS.
- Compatibility: existing workflow and all canonical owners remain immutable — PASS.
- Installer readiness: stable module/client identity exists; packaging is a
  separate next slice and is not claimed by R0.
- Residual Critical / High / Medium: `0 / 0 / 0`.
- Dataset / Job / Training / Model / Audio / Release / Deploy effect: `0`.

## Validation receipt

- Focused client/schema/security tests: `15 passed`.
- Schema mirror SHA-256:
  `52d12268a7045ded6bfb114afd3088d0b9a910c1f4ed0da97233e653f0d729da`;
  public/mirror bytes are exact.
- Python compileall: PASS.
- Windows Python 3.13.14 full regression: `1909 passed, 1 skipped` in
  `66.04s`; the skip is the existing non-Windows credential-vault contract.
- WSL2 Ubuntu Python 3.12.3 full regression: `1909 passed, 1 skipped` in
  `84.11s`; the skip is the Windows-only Inno Setup acceptance.
- The stale Python 3.12 validation launcher was not treated as Product
  failure.  A contained Python 3.13.14 validation environment was installed
  without changing system PATH; its official installer content SHA-256 is
  `c54d9b9bbb8a36e6489363ddd01139707fd781d72f1f9e90c7ec65d0061368e0`.
