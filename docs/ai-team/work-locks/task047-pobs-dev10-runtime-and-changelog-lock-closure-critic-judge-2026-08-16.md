# TASK-047 P-OBS dev.10 Runtime / CHANGELOG Lock Closure Evidence

- 日付: 2026-08-16
- Closure base: `main@1bccded179dedba83226cb1228f53cc9dc775b81`
- Registry: revision `20 -> 21`
- 対象 implementation Lock: `BVP-LOCK-TASK047-POBS-DEV10-UX-RUNTIME`
- 対象 Integration Lock: `BVP-INTEGRATION-LOCK-TASK047-POBS-DEV10-CHANGELOG-20260816`
- closure authority: `OWNER_STANDING_AUTONOMOUS_DEVELOPMENT_MODE_20260816_DEVELOPER2`

## 1. Closure scope

このH2 transactionは、TASK-047 P-OBS dev.10のreviewable source、Windows Controller、installer、公開guide、技術Acceptance、CHANGELOG integration、公開Technical Preview Releaseがcanonical mainとGitHub上でread-backできたことを根拠に、2つのLockを同時に`HOSTED_CLOSED_RELEASED`へ移す。

変更対象は次のexact 2 pathsのみである。

1. `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`
2. `docs/ai-team/work-locks/task047-pobs-dev10-runtime-and-changelog-lock-closure-critic-judge-2026-08-16.md`

code、schema、test、CHANGELOG、workflow、roadmap、他Task recordは変更しない。

## 2. Canonical implementation receipt

| 項目 | read-back |
|---|---|
| Pull Request | `#132` |
| base | `488d12cbb8b3f932e2b50ccf39d25b52f286ff83` |
| reviewed head | `6f94e12e532238e9076e78cf53d1627b5e1ce631` |
| merge/main | `1bccded179dedba83226cb1228f53cc9dc775b81` |
| merge parents | exact base + exact head |
| merged at | `2026-08-16T13:11:37Z` |
| first-parent diff | exact 46 paths |
| implementation scope | exact 45 paths |
| CHANGELOG scope | approved one physical line only |
| immutable raw blob graph | `799dee555f8cb33e1458678154b308d0bb59d1a189da8c0143d5da3d522e732a` |
| blob invariant | `45/45 PASS` |

Pre-merge hosted checks:

- CI run `31948906216`: Windows 3.11/3.12/3.13 and Ubuntu 3.11/3.12/3.13 PASS
- Release metadata run `31948906071`: PASS
- Security run `31948906128`: dependency audit / secret scan PASS
- total: `9/9 terminal SUCCESS`

Post-merge checks:

- CI run `31949121753`: terminal SUCCESS
- Security run `31949121747`: terminal SUCCESS

Local validation:

- focused tests: `20 PASS`
- Windows full regression: `1282 PASS / 1 SKIP`
- WSL2 full regression: `1282 PASS / 1 SKIP`
- native queue / capture / security suites: `3/3 PASS`
- installer/controller self-test and exact package contract: PASS

## 3. Owner-voice technical Acceptance boundary

Owner本人の明示操作による技術Acceptanceは、同一OBS processに対するSTART / PAUSE / RESUME / STOP、保存終端、packet gap `0`、HMAC failure `0`、reconnect `0`を確認した。Private audio body、絶対path、voice-linkable hashはRepository、CHANGELOG、public manual、Release metadataへ公開していない。

このPASSは、Dataset adoption、Training、Production recording、商用利用、stable Releaseを認可しない。GAIN確認は現行live Peak/RMS meterとmanual proposalの範囲であり、hardware gain、phantom power、PAD、HPFを自動変更しない。

## 4. Public Technical Preview Release receipt

- Release URL: `https://github.com/baisound/bai_video_production/releases/tag/obs-voice-capture-v0.1.0-dev.10-installer.1`
- Release ID: `371329927`
- tag: `obs-voice-capture-v0.1.0-dev.10-installer.1`
- target commitish: `1bccded179dedba83226cb1228f53cc9dc775b81`
- state: public / non-draft / prerelease
- stable Release: false
- target: OBS Studio `32.2.1`, Windows x64
- signing: unsigned Technical Preview

GitHub asset read-back:

| Asset | Bytes | GitHub digest |
|---|---:|---|
| `bai-voice-capture-0.1.0-dev.10-installer.1-windows-x64-setup.exe` | 2140146 | `sha256:5eb7b00aa3830f880c724538023c6f7b0b52a032e2c1ed880d497cdd8cce1908` |
| `bai-voice-capture-0.1.0-dev.10-windows-x64.zip` | 40670 | `sha256:03286e9efbf5dd5af38230dcf7fee4bf53eb3fcc7d7a6d014833b9996bc1f558` |
| `bai-voice-capture-0.1.0-dev.10-source.zip` | 45715 | `sha256:0ad4c83a957b37b455b38829f842f8318116c522cb542de0a9c5849567b29e72` |
| `SHA256SUMS` | 352 | `sha256:8a911d1e1378ef6cb6dfc20a7b63ab2f9b3c50dbd8bb3a5a3dfaacfdaec55c92` |

全assetのname、size、digest、uploaded stateをGitHub APIでread-backし、main上のblobとlocal hashに一致した。

## 5. Integration Lock consumption

CHANGELOG Integration Lock hosting receipt:

- hosting PR: `#131`
- hosting head: `2d29fc4e9aca99c833d5818661a79ea45e55570c`
- hosting merge: `488d12cbb8b3f932e2b50ccf39d25b52f286ff83`
- hosted checks: `9/9 PASS`
- post-merge CI: `31948697772` SUCCESS
- post-merge Security: `31948697751` SUCCESS

Target compositionはexact 45 immutable implementation pathsとIntegration-ownerの`CHANGELOG.md` one lineだけであり、target PR #132のmerge/post-merge greenおよびpublic prerelease read-backをもってLock release conditionを満たした。PR #131 mergeだけをrelease根拠にはしていない。

## 6. Immutable-field preservation

両recordの次の原始fieldは変更しない。

- lock ID、owner、thread、host authority
- task/phase/branch/base/scope
- allowed files、denied paths/effects
- read-only dependencies、requirements、prerequisites
- workflow、expiry、release conditions
- approved CHANGELOG line
- immutable target count / graph digest / composition rule

append-only receipt、authority ID、canonical target result、release resultのみを追加し、`status`、`implementation_authority_state`、`implementation_state`を実績に同期する。

## 7. No-authority inflation

このclosureは次を認可しない。

- Production recording admission
- Dataset adoptionまたはAsset promotion
- Job dispatch、Training、Model effect
- hardware gain / phantom / PAD / HPF変更
- destructive delete、key destruction
- paid Cloud、Credential effect
- stable Release / Deploy
- workflow exception、CI weakening、force/reset/rebase/revert

公開prereleaseは配布可能なTechnical Previewのread-backであり、上記effectの成功または承認を示さない。

## 8. Critic pass 1

監査観点:

- Registry revision/audit baseのcontext一致
- 2 recordだけのlifecycle変更
- PR #132 exact46、implementation exact45、CHANGELOG exact1
- immutable graph、package hash、Release asset一致
- private data非公開
- TASK-005や他Taskへのauthority移譲を記録しない

結果:

- Critical: 0
- High: 0
- Medium: 0
- correction: なし

## 9. Critic pass 2

独立再検査:

- statusを削除ではなくappend-only closure receipt付きで更新
- Integration Lockをhosting mergeだけで早期releaseしていない
- post-merge CI/Securityとpublic Release asset read-backを要求
- other Locks、history、roadmap、merge order、global policyを不変維持
- UNKNOWN/failureをPASSへ変換しない

結果:

- Critical: 0
- High: 0
- Medium: 0
- correction: なし

## 10. Read-only Judge before hosting

- IMPLEMENTATION_HOSTED_AND_POSTMERGE_GREEN: PASS
- OWNER_VOICE_TECHNICAL_ACCEPTANCE: PASS_BOUNDED
- PUBLIC_TECHNICAL_PREVIEW_RELEASE: PASS
- CHANGELOG_INTEGRATION_CONSUMED: PASS
- EXACT_TWO_RECORD_SAME_TRANSACTION_CLOSURE: PASS
- PRIVATE_BODY_OR_PATH_LEAK: 0
- AUTHORITY_INFLATION: 0
- RESIDUAL_CRITICAL_HIGH_MEDIUM: `0 / 0 / 0`
- H2 closure transaction readiness: PASS

Canonical closureは、このexact 2-file PRがmainへmergeされ、Registry revision 21と両`HOSTED_CLOSED_RELEASED` recordをmainからread-backし、post-merge CI/Securityがterminal SUCCESSになった時だけ成立する。
