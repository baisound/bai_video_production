# TASK-014 Local Primary Narration Preflight I1 Evidence

## 1. Authority and transaction

- Authorization: `BVP-AUTH-20260816-TASK014-LOCAL-PRIMARY-NARRATION-PREFLIGHT-I1-01`
- Unit: `TASK-014/LOCAL-PRIMARY-NARRATION-PREFLIGHT-I1`
- Base: `origin/main@edaa926a75c7584378579da2b7f8d1e3ef0bf2ff`
- Registry revision: `23`
- Branch: `codex/task-014-local-primary-narration-preflight`
- Worktree: isolated and clean before implementation
- Allowed Files: the five paths listed in section 2 only
- External/provider/audio/model/GPU/render/publication effects: `0`

TASK-047 and TASK-048 were read back as canonically completed prerequisites. This unit does not reinterpret their runtime receipts as narration execution authorization.

## 2. Exact implementation ownership

1. `docs/ai-team/tasks/TASK-014/local-primary-narration-preflight-evidence-2026-08-16.md`
2. `schemas/local-primary-narration-preflight.schema.json`
3. `src/ai_video_production/schema_resources/local-primary-narration-preflight.schema.json`
4. `src/ai_video_production/owner_narration_local_primary.py`
5. `tests/test_task014_local_primary_narration_preflight.py`

`owner_narration.py`, provider routing, shared `__init__.py`, Registry, roadmap, workflow and CHANGELOG are not changed by this implementation unit.

## 3. Hosted dependency read-back

| Dependency | Classification | Blob |
|---|---|---|
| VoiceProfileRevision schema | `HOSTED_CANONICAL` | `4901237b59243ac195da6f6b92ff878d68288d42` |
| VoiceProfileRevision module | `HOSTED_CANONICAL` | `c30e1bba7d8418ef5bfc2661fe1f6d855ef53ddd` |
| P-VS-3A schema | `HOSTED_CANONICAL` | `0515957d580571a09c12b80d9d93af32df94014a` |
| P-VS-3A module | `HOSTED_CANONICAL` | `6951f404d49dee4779a8ac540adb07c432c4831d` |
| P-QC-1A schema | `HOSTED_CANONICAL` | `14eb39636cf96e7e1a9f204607940ed17b5cac36` |
| P-QC-1A module | `HOSTED_CANONICAL` | `df9f5148c1cc33e4047c9014b67357463e42e515` |

The P-VS-1A `ConsentReference` field names are consumed without rename or alias. No independent ConsentRevision identity is invented.

## 4. Contract implemented

`LocalPrimaryNarrationPreflight` is a deterministic, body-free control-plane record. It supports two intentionally separate routes:

- `ZERO_SHOT_LOCAL`: exact Asset/AssetRevision mapping, reference profile, current Consent and rights evaluation are required.
- `FINE_TUNED_LOCAL`: exact DatasetRevision, TrainingInputSnapshot, ModelCandidateRevision, canonical artifact binding, Owner model approval, current Consent and rights evaluation are required.

The compiler validates structured bindings for approved text, VoiceProfileRevision, engine/model/runtime/license, resource feasibility, rights and the selected route dependency. `CANONICAL_REF_NOT_PROVIDED` and `UNKNOWN` remain unknown; `MISMATCH`, revoked rights/Consent, failed probe and failed resource admission are blocked.

The only successful metadata decision is `READY_FOR_OWNER_HUMAN_GATE`. It is not execution authority. All serialized execution/effect flags are fixed to `false`, including `execution_started`, `model_loaded`, `gpu_reserved` and `asset_published`. A raw `execution_authorized` input is rejected.

## 5. Privacy and integrity

- Private payload: exact body-free IDs/digests and current evaluation bindings.
- Public projection: state and decision only; script digest, Asset checksum, Consent evidence ID, model/runtime private references, credentials and absolute paths are absent.
- Canonical hash: SHA-256 over deterministic canonical JSON excluding the hash field itself.
- Parser: recomputes decision, ordered reason codes and checksum; caller-supplied success/tamper is rejected.
- Schema mirror: byte-identical public and package-resource files.

## 6. Validation receipt

| Gate | Result |
|---|---|
| Focused contract tests | `29 PASS` |
| Schema draft validation | `PASS` |
| Schema mirror byte equality | `PASS` |
| Python compile | `PASS` |
| Windows full regression | `1405 PASS / 1 ENVIRONMENT-BLOCKED` |
| WSL2 full regression | `1406 PASS / 1 Windows-only SKIP` |
| Forbidden surface scan | `PASS` |
| `git diff --check` | `PASS` |

The focused suite includes both routes, exact dependency separation, unresolved/mismatch/revoked/unknown fail-closed paths, mode and rights mismatch, schema exclusivity, public redaction, deterministic round-trip, checksum/classification tamper and raw authorization rejection.

The single Windows environment block is the existing TASK-047 installer acceptance. Its Inno Setup subprocess reached the Start Menu and `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall`, then the managed sandbox denied both with Win32 error 5. All other Windows tests passed. An unsandboxed unchanged retry was correctly rejected because it would repeat those external side effects. This is not converted to PASS; the hosted Windows runner remains the authoritative final regression Gate.

## 7. Critic pass 1 — domain and authority

Initial finding:

- `HIGH`: the first implementation required `parent_revision_sha256` for every `BOUND_VERIFIED` VoiceProfileRevision, contradicting canonical revision 1 where the parent is `null`.
- `HIGH`: resource feasibility was bound to the selected route, but engine admission was not; a probe for `ZERO_SHOT_LOCAL` could therefore be reused for `FINE_TUNED_LOCAL` or vice versa.

Correction:

- revision 1 now requires a null parent; revision greater than 1 requires the exact parent digest; all other verified identity/evidence fields remain mandatory.
- `EngineAdmissionBinding.route_mode` is now mandatory for a verified binding and must exactly match the preflight route. Cross-mode reuse is rejected and covered by a negative test.

Residual Critical/High/Medium: `0 / 0 / 0`.

## 8. Critic pass 2 — schema, privacy and no-effect surface

- ZERO_SHOT and FINE_TUNED dependencies cannot coexist or substitute for each other.
- Unresolved bindings cannot carry invented canonical IDs, digests, decisions or receipts.
- Script/audio bodies, credentials and absolute paths cannot be serialized.
- Public output contains no text digest, audio hash or private evidence reference.
- No provider/network/filesystem/audio/model/GPU/render/publish/dispatch API is exposed.
- This preflight cannot promote readiness to narration execution, Asset publication or production use.

Residual Critical/High/Medium: `0 / 0 / 0`.

## 9. Security Critic

- Strict key sets reject authority-smuggling properties.
- SHA-256 syntax and deterministic checksum verification reject silent metadata mutation.
- Canonical unresolved states must contain null canonical fields.
- Engine license, current Consent, rights and resource states are orthogonal and each fail closed.
- No credential resolver, absolute-path consumer, subprocess, socket, provider client or model loader is imported.

Security residual Critical/High/Medium: `0 / 0 / 0`.

## 10. Judge and remaining gates

Current local Judge: `READY_FOR_DRAFT_PR_WITH_HOSTED_WINDOWS_GATE`.

- Domain readiness: `PASS`
- Pure metadata/no-effect boundary: `PASS`
- Focused and WSL full regression: `PASS`
- Windows full regression: `CONDITIONAL` on the hosted runner because one unrelated installer acceptance is sandbox-blocked
- Residual Critical/High/Medium: `0 / 0 / 0`

Implementation execution remains false. Actual local synthesis, model download/load, resource reservation, audio rendering, 48 kHz publication, paid/provider/credential use and Release/Deploy require separate effect authority.

Because product source changed, CHANGELOG remains mandatory but is outside this exact-five unit. It is reserved to serialized sub-Gate `BVP-ILOCK-20260816-TASK014-I1-CHANGELOG-01` after the current shared CHANGELOG lane is proven free.
