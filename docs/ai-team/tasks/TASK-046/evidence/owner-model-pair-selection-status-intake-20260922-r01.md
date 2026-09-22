# TASK-046 Owner Model-Pair Selection Status Intake Evidence R01

- Run identity: `TASK-046-OWNER-MODEL-SELECTION-20260922T135805+09:00`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-046 P-VS-4A / OWNER MODEL-PAIR SELECTION STATUS INTAKE`
- Development depth: `DEV-4 FOUNDATION CRITICAL`
- Branch: `codex/task-097-second-run-status-intake`
- Starting HEAD: `6e14ba4ea5962a164ebc450ffa2dd06eff35e63d`
- Base/current-main identity: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Result: `OWNER_SELECTED / PUBLIC_RELEASE_CONTRACT_PENDING / COMMIT_READY`

## Owner decision and exact selected identities

The Owner clarified directly on `2026-09-22` that model selection was already
completed and that the supplied information pack records it.

| Role | Selected source filename | Size | SHA-256 |
|---|---|---:|---|
| SoVITS | `BAISOUND_TASK097_V2_FRESH_e4_s192.pth` | 134946675 | `76a492931f97cd349c6d7d6f04bab4f2442fa9890a5a40708a1d49f919f8e0ff` |
| GPT | `BAISOUND_TASK097_V2_FRESH-e15.ckpt` | 155312966 | `4dd990db49d56bdaff6c4988635c46b58f73e1d719297570f0d361184fd60745` |

These sizes and hashes were independently read-only verified during the
preceding TASK-097 completion intake.

## Information-pack corroboration

- Pack schema: `baisound.voice-model.bvp-info-handoff.v1`.
- Pack is explicitly `information_only=true` and
  `implementation_request=false`.
- It identifies the same e4/e15 pair as the internal approved sources.
- It reports Public Repository modernization as `IN_PROGRESS`, planned public
  release `v2.0.0`, and no immediate BVP change required.
- All six files listed in its checksum set were independently verified `PASS`.
- The Owner's direct confirmation, not the information-only pack by itself, is
  the authority for the TASK-046 status change.

## Non-claims and gates

- Planned public names `baisound-voice-v2-sovits.pth` and
  `baisound-voice-v2-gpt.ckpt` remain provisional until the Public Repository
  completion commit/release contract.
- No model was copied, renamed, installed, loaded, inferred with, promoted into
  BVP, or published by this Unit.
- Public release, BVP Provider/Model registration, runtime admission, narration
  generation, Asset/Evidence integration and production use remain separate.
- No private audio/transcript/log body or private absolute path is present.

## Review and verification

- Status-intake design: 2697 bytes, SHA-256
  `75b0985d5d0b2d2924f9a26347727ecfea3711e75977dfe404066af94dd53461`.
- Documentation diff/private-path/status consistency checks: required before
  commit.
- Critic final findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- No Product source/schema/test, model, media, runtime, Provider, dependency,
  package, installer or Product version changed.
- No build/QA/runtime/temp output root was used.

## Next action

Wait for the BAISOUND_VOICE_MODEL Public Repository `v2.0.0` modernization to
finalize its public release contract. BVP consumer integration then requires a
fresh bounded design/authority review; selection alone does not activate it.
