# TASK-047 P-OBS Release installer Integration Lock Evidence

## Outcome

TASK-047のOBS Plugin installerを今後のGitHub Releaseへ必ず同梱し、READMEから
Plugin、runtime package、installerまでの再現build手順を確認できるようにするため、
`.github/workflows/release.yml`と`CHANGELOG.md`のshared writeを短期Integration Lockで
直列化する。

## Exact scope

- base/main: `c88d932dc1a91b7edcb810d43fb7393b0a6c7fc5`
- Registry: `15 -> 16`
- Lock: `BVP-INTEGRATION-LOCK-TASK047-POBS-RELEASE-INSTALLER-20260816`
- shared Allowed Files: `.github/workflows/release.yml`, `CHANGELOG.md`
- target branch: `codex/task-047-pobs-release-installer-inclusion`
- target pre-integration head: `c88d932dc1a91b7edcb810d43fb7393b0a6c7fc5`
- roadmap delta: none

The implementation unit may also change only its exact TASK-047-owned README, Evidence,
release-asset and focused-test paths recorded in the Registry. This Lock does not authorize
a Tag, GitHub Release, Deploy, OBS launch, Plugin load, capture or Owner voice recording.

## Critic self-pass 1

Finding: adding the installer only to documentation would not ensure that `gh release create`
uploads it. Correction: reserve the release workflow and require a fail-closed SHA-256 check
before the existing release command receives the installer, runtime and source assets.

## Critic self-pass 2 / Judge

- active Lock/path overlap: 0
- unrelated Registry/root/roadmap mutation: 0
- unverified artifact fallback: 0
- Release/Deploy authority inflation: 0
- unresolved Critical/High/Medium: `0 / 0 / 0`

Judge: `PASS_EXACT2_LOCK_HOST_DRAFT_PR_READY`.
