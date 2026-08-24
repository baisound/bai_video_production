# TASK-036 P-UX-2L CHANGELOG Integration Lock Hosting

Date: 2026-08-25

Unit: `TASK-036/P-UX-2L-SUBTITLE-CUT-CONTROLS-CHANGELOG-LOCK-HOSTING`

Authority: `OWNER_EXPLICIT_AUTONOMY_RESUME_20260825`

Status: `PENDING_HOST_PR`

## Target identity

- target PR: `#306`
- target branch: `codex/task-036-pux2l-subtitle-cut-controls`
- exact target head: `5fff7aed46c499e7b357d419968eb82e2c9a90c5`
- fresh main: `797feb073cf50d3a440b070265e2dbed7fc59cad`
- immutable target paths: `15`
- hosted checks: `8 / 9 PASS`
- only failure: `changelog-and-version`
- local fresh-main directly impacted regression: `205 PASS`
- independent Tester regression: `222 PASS`
- independent Tester/Critic/Judge: `TECHNICAL GO`, C/H/M/L `0 / 0 / 0 / 0`
- other open PRs: `3` (`#270`, `#273`, `#307`); none changes `CHANGELOG.md` nor Registry
- shared-path overlap: `0`
- prior nonclosed integration locks: `0`
- registry revision: `68 -> 69`

## Reserved effect

Only the following exact line may be added to `CHANGELOG.md` after this lock is merged to main, read back exactly, and its post-main CI and Security are green:

> - TASK-036 P-UX-2Lとして、検証済みTranscriptから任意Subtitle生成と初回Cut候補生成をV6.1.1操作面へ接続し、Source/Transcript/Project/Shell/session CAS、single-flight、Human承認後の再生成拒否、fallible callbackを排除したatomic runtime promotion、exact promoted runtimeのExport identity fail-closedを実装しました。Provider、model download、paid service、Resolve、render、native GUI、Owner media、外部Export dispatch、Release/Deploy権限は付与しません。

The target composition is the exact fifteen immutable implementation, test, design, and Recovery Evidence paths plus this one integration-owned `CHANGELOG.md` effect. The Registry must not be modified on the target branch during the effect.

## Verification boundary

- target PR exact head, Draft state, and mergeability: PASS;
- target Hosted CI: Ubuntu and Windows on Python 3.11, 3.12, and 3.13 all pass;
- target Hosted Security: dependency audit and secret scan both pass;
- fresh-main Registry revision 68 and nonclosed integration lock count 0: PASS;
- open PR shared-path overlap: 0;
- target path count and immutable identity: 15 paths fixed at the exact pre-integration head;
- Provider, paid service, model download, Resolve, render, native GUI, Owner media, and external Export dispatch: 0;
- real WebView and real machine execution remain `NOT_CONFIRMED` and are not lock evidence.

## Critic

Risk: a fallible post-CAS publisher could previously leave Cut state advanced without an application/runtime.

Resolution: the reviewed implementation removes the publisher/cache contract. Application and workflow-runtime construction and identity validation occur before final CAS; after CAS only direct in-process reference assignments remain.

Risk: the trusted Export closure could dispatch through a missing or foreign application runtime.

Resolution: a direct trusted-launch fixture proves exact promoted-runtime dispatch and fail-closed rejection before dispatch for both missing runtime and application identity mismatch.

Risk: a concurrent shared writer could invalidate the reservation.

Resolution: fresh main revision 68 has zero nonclosed integration locks, and every other open PR was audited with no CHANGELOG or Registry overlap.

Unresolved Critical/High/Medium/Low findings: `0 / 0 / 0 / 0`.

## Judge

`ACCEPT_LOCK_PROPOSAL_PENDING_HOST_MAIN_READBACK`.

The lock becomes authoritative only after this exact two-file proposal is merged to main and read back exactly. Main, Registry, target-head, or overlap drift before the effect expires the transaction and requires a fresh audit. No retry, force update, workflow weakening, Provider/model/native/Resolve/Export effect, version, Tag, Release, or Deploy is authorized.
