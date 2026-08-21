# TASK-036 P-UX-2K CHANGELOG Integration Lock Hosting

Date: 2026-08-22

Unit: `TASK-036/P-UX-2K-LOCAL-TRANSCRIPTION-CONTROLS-CHANGELOG-LOCK-HOSTING`

Authority: `OWNER_AUTONOMY_AND_ALL_GREEN_MERGE_DIRECTIVE_20260821`

Status: `PENDING_LOCK_HOST_PR`

## Target identity

- target PR: `#269`
- target branch: `codex/task-036-pux2k-transcription-controls`
- exact target head: `66226525ef7701a71b58ad2c4bfb2cce07578576`
- fresh main: `8ce0b081fd35245ff48b0ec86e071acb1ab345cc`
- immutable target paths: `19`
- hosted checks: `8 / 9 PASS`
- only failure: `changelog-and-version`
- other open PRs: `1` (`#270`, no `CHANGELOG.md` or Registry overlap)
- shared-path overlap: `0`
- prior nonclosed integration locks: `0`
- registry revision: `48 -> 49`

## Reserved effect

Only the following exact line may be added to `CHANGELOG.md` after this lock is
merged to main and its post-merge CI and Security are green:

> - TASK-036 P-UX-2Kとして、V6.1.1のローカル文字起こしをHuman prepare/apply/cancelへ接続し、TASK-003管理Assetのstable bytes、Product Operations CAS、Project固定出力slot、immutable publication setと明示recoveryによりcross-process exact-oneと固定Transcript/SRT/reportの耐障害promotionを実装しました。実FasterWhisper/model download、paid/cloud、Audio authority、Resolve/Export、公開、Release/Deployは引き続き別Gateです。

The target composition is the exact nineteen immutable implementation, design
and test paths plus this one integration-owned `CHANGELOG.md` effect. The
Registry must not be modified on the target branch during the effect.

## Verification boundary

- local fresh-main directly affected regression: `251 PASS`;
- target pre-integration regression: `277 PASS`;
- target Hosted CI: Ubuntu and Windows on Python 3.11, 3.12 and 3.13 all pass;
- target Hosted Security: dependency audit and secret scan both pass;
- real FasterWhisper, model download and native Provider execution: `0`;
- local full repository suite remains `NOT_CONFIRMED`; Hosted full matrix is the
  current executed broad regression evidence.

## Authority boundary

The durable lock/effect/closure authority is the existing Owner autonomy and
safe all-green merge directive. The current sleep window is not used to expand
FasterWhisper execution, model download, paid/cloud Provider, Audio authority,
Resolve, Export, publication, Release or Deploy authority.

No workflow exception, CI weakening, force push, rebase, retry of an unchanged
head, version, Tag, Release or Deploy is authorized.
