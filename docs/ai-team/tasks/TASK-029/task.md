# TASK-029 — Human Edit Learning / Federated Knowledge Evolution

- Status: `R0_R1_R2_R3_R4_R5_R6_R7_R8_R9A_R9B_R9C_R9D_HOSTED_CLOSED`
- Governance: `DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY`

## Owner priority routing — 2026-08-24

The Owner assigned this Task to the current developer lane and moved it ahead of the remaining general Learning & Operations queue. The exact lane order is:

```text
TASK-055 local lane recovery/integration audit
-> TASK-056 final BVP integration
-> TASK-029 Human Edit Learning R0
-> TASK-019 Profile Auto-Tuner hosting/integration
```

This routing authorizes bounded local implementation planning and implementation under DEV-4. It does not by itself authorize private production-data ingestion, Cloud telemetry, automatic Owner Profile or Knowledge Pack promotion, Release, Deploy, or Production effects.
## R0 implementation — canonical Evidence / Decision boundary

R0は、既存Product ownerのadmitted Human Evidenceをbody-freeな
`HumanActionEvidence`へ正規化し、複数記録と6つの独立評価軸から
`OwnerDecisionCandidate`を決定的に作るpure contractを実装する。

- TASK-055 Montage Human Edit Evidenceをexact Proposal/Plan/Evidence lineageでadmitする。
- do-not-learn、即時Undo、後工程再修正を学習対象から除外する。
- Safety/Rights FAILまたはUNKNOWNをHard Gateとして加重点で相殺しない。
- UNKNOWN / STALE / REVOKED / sample不足 / context混在 / axis regressionを別状態で保持する。
- quality、rework、time、QA、Human acceptance、sample confidenceを別軸で保持する。
- raw media、本文、host path、credentialをrecordへ含めない。
- Profile write、Knowledge Pack promotion、Cloud telemetry、rollback、Edit Plan/Timeline、
  Resolve、external effect authorityをすべてfalseに固定する。

R0はfilesystem/database Storeを作らない。Owner Decision Storeのencrypted durable
persistence、Human adoption、Owner-wide Profile、TASK-019 bridge、Cloud、Knowledge Packは
後続のbounded Atomic Unitである。

R0はPR #286でmergeされ、closure PR #288、registry revision 57、post-main CI/Security PASSによりshared CHANGELOG lockを解放済み。

## R1 implementation — encrypted Owner Decision Store

R1は`READY_FOR_HUMAN_REVIEW` Candidateへの明示Human ADOPT/REJECTを、Windows Current User DPAPI既定の暗号化append-only historyへ保存する。cross-process CAS、chain/replay/scope検証、atomic replace、restart read-back、wrong-key/tamper/symlink/power-loss fail-closedを実装する。disk envelopeへOwner scope、Candidate、理由コードを平文保存しない。

R1はOwner Profile write、Knowledge Pack promotion、Cloud telemetry、rollback、plaintext export、physical delete、Timeline/Resolve、external effect authorityを生成しない。retention/purgeはTASK-017、Profile proposalはTASK-019、Profile materializationとPack promotionは後続Unitである。focused R0/R1は`27 PASS`。

R1はtarget PR #289、closure PR #291でhosted closedとなり、shared CHANGELOG reservationを解放済み。

## R2 implementation — pure Owner Profile materialization candidate

R2はhosted closed済みTASK-019 R1のexact Proposal/Owner Decision Bindingと、最新TASK-029 Owner Decision Historyを毎回再検証し、immutableな`OwnerProfileMaterializationCandidate`をin-memoryで決定的に生成する。

- 全adjustmentが相異なる明示ADOPTED decisionへexact bindされたREADY状態だけ、提案済み`ScoringProfile` snapshotを公開する。
- proposal非READYまたはselected REJECTED decisionを別stateに保ち、Profile snapshotを公開しない。
- history/proposal/binding/baseline/proposed/rollback hashとsource decision IDを固定し、payload/source driftをfail closedにする。
- Owner Profile Store、Model/Profile Registry、Knowledge Pack、automatic promotion、rollback execution、Timeline/Resolve、external effect authorityはすべてfalseに固定する。

R2はfilesystem/database/DPAPI/Store I/Oを持たない。target PR #300、closure PR #302、registry revision 66でhosted closedとなった。初回main CIの既存TASK-036 Windows 3.12 multiprocessing試験は固定10秒を超えてFAILしたが、同一commit failed-job再実行で6/6 matrix PASS、Security PASSとなり、shared CHANGELOG reservationを解放済み。

## R3 implementation — explicit-Human-confirmed encrypted Owner Profile Store

R3はR2候補を保存直前にexact sourceから再生成し、別recordの明示Human確認が候補hash、Owner scope、proposed Profile hashへ一致した場合だけ、Owner-local Profile revisionを暗号化appendする。

- Windows Current User DPAPIを既定とし、Owner Decision Storeとは別のentropy domainを使う。
- disk envelopeはciphertextとintegrity metadataだけを持ち、Owner scope、candidate/confirmation ID、Profile snapshotを平文保存しない。
- cross-process lock、expected-revision CAS、append-only hash chain、atomic replace、restart read-backを必須にする。
- 同一Owner scope/Profile identity、previous active Profileと次baselineの連続性、candidate/confirmation/Profile version非replayを検証する。
- wrong-key、tamper、plaintext、symlink、partial writeをfail closedにする。

R3の確認は1回のencrypted Store appendだけを許可する。runtime scoringへの適用、Model/Profile Registry write、Knowledge Pack promotion、automatic promotion、rollback execution、physical delete、Timeline/Resolve、Provider/Cloud、Release/Deployは許可しない。

R3 focused＋直接依存は`36 PASS`、TASK-019/029全体は`61 PASS`、全Product regressionは`3681 PASS / 6 SKIP / 0 FAIL`。target PR #303、lock-host PR #304、closure PR #305がmergeされ、fresh main `797feb073cf50d3a440b070265e2dbed7fc59cad`、registry revision 68、post-main CI/Security PASSでshared CHANGELOG lockを解放済み。

## R4 implementation — pure Owner Profile Registry admission candidate

R4はR3 encrypted Owner Profile Historyのlatest revisionを毎回exact再検証し、TASK-008 `ScoringProfile`へsemantic再構築した上で、Model/Profile Registry登録前のimmutable in-memory候補を生成する。

- history/revision/materialization/confirmation/proposal/binding/decision lineageをhashで固定する。
- callerの`expected_history_revision`とlatest revisionが一致しない場合はstaleとしてfail closedにする。
- rule、modality、weight、source selector、semantic version、Profile hashをTASK-008型で再検証する。
- compatibility contractは`TASK-008/SCORING_PROFILE/1.0.0`へ固定する。
- Owner scopeはbody-free SHA-256 coordinateだけを保持する。

R4はModel/Profile Registry write、runtime scoring apply、Knowledge Pack promotion、automatic promotion、rollback execution、Timeline/Resolve、Provider/Cloud、Release/Deploy authorityを生成しない。別の明示Human registry confirmationと後続Unitが必要である。

R4 focused＋R2/R3直接依存は`23 PASS`、TASK-019/029 chainは`68 PASS`、最終全Product regressionは`3688 PASS / 6 SKIP / 0 FAIL`。compileall、strict Schema validation、schema mirror、diff-checkもPASS。

## R5 implementation — explicit-Human-confirmed encrypted Owner Profile Registry Store

R5はR4候補とは別の明示Human registry confirmationを必須にし、R3 encrypted Owner Profile StoreとR5 Registry Storeを決定的path順で同時lockした上でsourceを再読込し、R4候補をexact再生成して1回だけ登録する。

- source history revision/hash、source Profile revision hash、Owner scope、candidate/Profile hashをconfirmationへ固定する。
- destinationはexpected registry revision CAS、append-only hash chain、strict source revision advance、Owner/source store/Profile identity、active Profile baseline continuityを検証する。
- candidate/confirmation/source Profile revision/Profile version replayを拒否する。
- Windows Current User DPAPIを既定とし、R1 Decision Store/R3 Owner Profile Storeとは別entropy domainを使う。
- disk envelopeはciphertextとintegrity metadataだけを持ち、Owner scope、candidate/confirmation ID、Profile snapshot、lineageを平文保存しない。
- source/destination同一path、symlink、wrong-key、tamper、plaintext、partial writeをfail closedにする。

R5の1 appendはModel/Profile Registryへの登録だけを行う。runtime scoring apply、Knowledge Pack promotion、automatic promotion、rollback execution、physical delete、Timeline/Resolve、Provider/Cloud、Release/Deployは許可しない。

R5 focused＋R4回帰は`14 PASS`、R2-R5直接依存は`30 PASS`、TASK-019/029 chainは`75 PASS`、全Product regressionは`3781 PASS / 6 SKIP / 0 FAIL`。Windows実DPAPI synthetic round-trip、compileall、strict Schema validation、schema mirror、diff-checkもPASS。

R5 Design/Critic/Judge: `owner-profile-registry-store-r5-design-critic-judge.md`。Residual Critical/High/Mediumは`0/0/0`。

R5はtarget PR #325、lock-host PR #326、closure PR #330でhosted closedとなり、fresh main `621e20f3b4e62f47b5fb131aba6c322ffaf916f9`、registry revision 74、active nonclosed integration locks 0、closure post-main CI 6/6とSecurity PASSでshared CHANGELOG reservationを解放済み。

## R6 implementation — pure cross-Owner Knowledge Pack promotion candidate

R6はR5 Owner Profile Registry Historyと、そのlatest revisionが固定したR1 Owner Decision History、選択済みADOPTED decision、exact R0 Human Action Evidenceを毎回再検証し、複数Owner・複数Projectで同じ仮説・条件・FeatureRuleが再現したかを評価するimmutable in-memory候補を作る。

- Owner/Project scope座標はdistinct countにだけ使い、候補へ保存しない。
- one-source-per-OwnerとEvidence hash replay拒否により、同一Ownerの水増しを防ぐ。
- quality、rework、time、QA、Human acceptance、sample confidenceを別軸のまま集約する。
- 平均ではなく各軸のminimum deltaとminimum Owner benefitを保持し、悪化を他Ownerの加点で隠さない。
- Owner不足、Project不足、sample不足、axis regression、効果不足を別stateにする。
- lineage、Evidence、hypothesis/context、active FeatureRule不一致はstate化せずfail closedにする。

R6はKnowledge Pack write/promotion、signature、automatic promotion、runtime Profile apply、rollback execution、Git release、Timeline/Resolve、Provider/Cloud、Release/Deployを実装・許可しない。Human review、independent Critic、signature、latest-source revalidationは後続Gateである。

R6 focusedは`5 PASS`、TASK-019/029 direct regressionは`80 PASS`、全Product regressionは`3786 PASS / 6 SKIP / 0 FAIL`。Design/Critic/Judgeは`knowledge-pack-promotion-candidate-r6-design-critic-judge.md`。Residual Critical/High/Mediumは`0/0/0`。target PR #332、closure PR #335、registry revision 76でhosted closedとなり、shared CHANGELOG reservationを解放済み。

## R7 implementation — Human/Critic-bound unsigned Knowledge Pack signing candidate

R7はR6候補をexact current R5/R1/R0 sourcesから毎回再生成し、同一候補hashへbindされた別々のHuman reviewとIndependent Critic reviewを結合して、外部署名Gate直前のbody-free immutable候補をpure in-memoryで生成する。

- Human/Critic review IDとreviewer coordinateを相異ならせる。
- Critic reviewはHuman reviewより後でなければならない。
- Criticの署名待ちACCEPTはunresolved Critical/Highが0の場合だけ許す。
- Human rejectionとCritic rejectionを別stateに保持する。
- Owner/Project/reviewer座標は出力へ含めず、exact review hashだけを保持する。
- candidate/feature rule/policy/predecessor Pack lineageをhashで固定する。

R7は署名鍵を受け取らず、signature create/verify、Knowledge Pack write/promotion、automatic promotion、runtime Profile apply、rollback execution、Git release、Timeline/Resolve、Provider/Cloud、Release/Deployを実装・許可しない。

R7 focusedは`6 PASS`、TASK-019/029 direct regressionは`86 PASS`、全Product regressionは`3792 PASS / 6 SKIP / 0 FAIL`。Design/Critic/Judgeは`knowledge-pack-signing-candidate-r7-design-critic-judge.md`。Residual Critical/High/Mediumは`0/0/0`。target PR #336、closure PR #338、registry revision 78、fresh main `a18ad35469d60583082cab4ffc09f74092c175e9`、post-main CI 6/6とSecurity PASSでhosted closedとなり、shared CHANGELOG reservationを解放済み。

## R8 implementation — body-free external signature verification request

R8はR7 signing candidateをexact compile inputsから毎回再生成し、Pack lineage、trusted signer policy SHA-256、signer key ID SHA-256、allowlist済みalgorithmをversioned canonical message hashへ束縛するimmutableな外部署名検証依頼をpure in-memoryで生成する。外部署名対象はversioned input contractにより、`sha256:`接頭辞を含むmessage hash文字列のASCII bytesへ固定する。

- R7 payloadとlatest recompile結果の完全一致を要求する。
- R7 stateが`READY_FOR_EXTERNAL_SIGNATURE`の場合だけrequestを生成する。
- algorithmは`ED25519`だけを許可する。
- requestはsignature bytes、public/private key material、credential本文を含めない。

R8は暗号署名・暗号検証、key store access、Knowledge Pack write/promotion、automatic promotion、runtime Profile apply、rollback execution、Git release、Timeline/Resolve、Provider/Cloud、Release/Deployを実装・許可しない。`signature_present=false`、`signature_verified=false`であり、外部暗号検証PASS authorityを生成しない。

R8 focusedは`5 PASS`、TASK-019/029 direct regressionは`91 PASS`、全Product regressionは`3797 PASS / 6 SKIP / 0 FAIL`。compile、strict Schema validation、schema mirror、no-I/O/no-crypto-import、diff/scopeもPASS。Design/Critic/Judgeは`knowledge-pack-signature-verification-request-r8-design-critic-judge.md`。Residual Critical/High/Mediumは`0/0/0`。hosted integrationはpending。

実署名、trusted public key解決、署名本文を用いた暗号検証、署名済みKnowledge Pack receiptおよびPack writeは別の明示Human Gateと後続Atomic Unitを必要とする。

## R9A implementation — Ed25519 verification with body-free receipt

R9A verifies an exact R8 request against a strict trusted-signer policy, raw 32-byte Ed25519 public key, and detached 64-byte signature. It returns only a body-free verification receipt and never stores key/signature bodies. target PR #347, repair PR #349, and closure PR #350 merged; fresh main `ee8ed50723ff2925ad3eb3da0c45b013b6237936`, registry revision 84, post-main CI/Security PASS, and shared CHANGELOG lock released.

## R9B implementation — one-shot encrypted Owner signing-key custody

R9B admits one raw 32-byte Ed25519 seed only after explicit Human confirmation bound to the exact custody ID, Owner-scope SHA-256, and public-key-derived signer key ID. Windows Current User DPAPI is the default with a dedicated entropy domain. The disk envelope contains ciphertext and integrity metadata only; validated atomic replace, cross-process lock, symlink rejection, and one-shot no-overwrite behavior fail closed.

The public read API returns a body-free custody receipt. There is no signing, export, replacement, rotation, PuTTY/OpenSSH conversion, Knowledge Pack write/promotion, runtime Profile apply, rollback, Release, Deploy, Production, Resolve/Timeline, provider, or Cloud authority. Tests use synthetic keys only; no real Owner secret is generated, printed, committed, or sent to CI.

Focused R9B is `13 PASS`, including Windows DPAPI synthetic round-trip, Schema mirror validation, tamper/wrong-cipher/plaintext/symlink/atomic-failure negatives, confirmation binding, and one-shot overwrite rejection. Design/Critic/Judge is `owner-signing-key-custody-r9b-design-critic-judge.md`. Residual Critical/High/Medium/Low is `0/0/0/0`. TASK-029全体は `94 PASS`、全Product回帰は `3865 PASS / 6 SKIP / 0 FAIL`。hosted integrationと独立reviewはpending。

R9Bはtarget PR #353、lock-host PR #357、closure PR #358でhosted closedとなり、fresh main `eea0296dbbd49c5dfe43fe46df6d2955dbd711fe`、registry revision 88、active nonclosed integration locks 0、closure post-main CI 6/6とSecurity PASSでshared CHANGELOG reservationを解放済み。

## R9C implementation — exact local signing ceremony with immediate verification

R9CはR8 exact sourceを鍵アクセス前に再検証し、ACTIVE trusted signer policy、fresh R9B custody receipt、exact Human confirmationを結合する。custody内部のseedでR8 sha256-prefixed ASCII messageだけを署名し、署名を外へ返さず同一呼出し内でR9A検証する。返却値はbody-free ceremony/verification receiptだけである。

永続ceremony journalは持たないためdurable one-shot replay preventionを主張せず、`persistent_replay_prevention_present=false`を固定する。signature export、Knowledge Pack write/promotion、automatic promotion、runtime apply、rollback、Release/Deploy/Production authorityは生成しない。focused synthetic testは`7 PASS`、R8-R9C directは`33 PASS`、TASK-029全体は`101 PASS`、full Product regressionは`3906 PASS / 6 SKIP / 0 FAIL`。Design/Critic/Judgeは`knowledge-pack-local-signing-ceremony-r9c-design-critic-judge.md`。real Owner key/signing executionは`NOT_EXECUTED`。
R9Cはtarget PR #359、lock-host PR #360、closure PR #362でhosted closedとなり、fresh main `931c7faabe3c7e6ea9af7066e2d3a7d5bd3480d7`、registry revision 90、active nonclosed integration locks 0、closure post-main CI 6/6とSecurity PASSでshared CHANGELOG reservationを解放済み。

## R9D implementation — path-local signing ceremony journal and no-replay recovery

R9DはR9Cの署名処理をcaller-selected local journal lock内で実行し、R9C署名前にexact ceremony identityを`SIGNING_RESERVED`としてatomic fileへ保存する。production success callbackは持たずtrusted `execute_local_signing_ceremony`を直呼びし、exact typed R9C/R9A resultを全coordinateでcross-bindしてからreceipt hashだけを`SIGNED_AND_VERIFIED`へcommitする。test seamは成功値を返せないafter-reservation fault hookだけとする。保持された同一path内の既知失敗またはprocess interruptionは`RECOVERY_REQUIRED`へ固定する。

journalはkey/public-key/signature bytesを保存せず、R9Cのbody-free境界を維持する。別path・削除・directory durability・power lossを越える保証はなく、`persistent_replay_prevention_present=false`、canonical binding/deletion detection/directory durability/power-loss flagsもfalse、`path_local_replay_prevention_present=true`を固定する。path security modelは`COOPERATIVE_PROTECTED_LOCAL_WRITER_ONLY`、hostile race protection=false、symlink rejection=trueとしてmachine-readableに固定する。signature export、Knowledge Pack write/promotion、automatic promotion、runtime Profile apply、rollback、Release/Deploy/Production authorityは生成しない。

shared metadata順序はOwner指示によりTASK-058 P1B closure、TASK-054、TASK-029 R9Dの順とする。R9D source Unitは`CHANGELOG.md`と`ACTIVE-WORK-LOCKS.json`を変更せず、R9D専用lockはTASK-054 canonical closure後にfresh mainから別transactionで取得する。

R9D third rework focusedは`20 PASS`、R8-R9D directは`59 PASS`、TASK-029全体は`121 PASS`。無除外full Product回帰は`3954 PASS / 6 SKIP / 0 FAIL`。multiprocess fixtureはcleanup例外を蓄積して全started childのbounded join→terminate→join→kill→final joinとdead handle closeを先に完了し、その後だけraise可能とする。queue close/join_threadはnested finallyでhelper失敗から独立し、forced-live-child fixture自身も外側fallback回収を持つ。

## Objective

人間の編集作業を盲目的に模倣せず、仮説、反証可能な評価、再現性および複数の品質指標に基づいて、有益と判断された操作だけをOwner Profileまたは製品共通知識へ昇格する。利用頻度に応じて各配布先オーナーへ適応し、明示同意がある場合だけ匿名化統計を製品改善へ利用する。

## Storage boundaries

| Store | Content | Git |
|---|---|---|
| Human Action Evidence | 操作前後、候補、採否、取り消し、作業時間の事実 | No |
| Owner Decision Store | オーナー固有の傾向、仮説、スコア、信頼度 | No; local encrypted by default |
| Optional Cloud Telemetry | 同意済み・最小化・匿名化した特徴量と評価値 | No |
| Dictionary | 固有語、字幕表記、NG語など明示語彙 | SchemaのみGit、値はOwner data |
| Knowledge Pack | 再現性確認済みの一般ルール、重み、適用条件 | Yes; signed and versioned |
| Model/Profile Registry | 昇格済みProfile、互換性、評価Evidence参照 | Metadata/version in Git |

## Learning gate

1. 操作を事実として記録するが、直ちに正解ラベルにしない。
2. `この変更は品質指標Xを条件Cで改善する`という仮説を作る。
3. 自動QA、人間の採否、再修正率、手戻り時間、公開後KPIなどを評価する。
4. ベースライン／対照候補と比較し、効果量、信頼区間、サンプル数を保持する。
5. 誤操作、即時Undo、後工程での再修正、単発外れ値、権利・安全違反を昇格対象から除く。
6. Owner固有の改善と製品共通化可能な改善を分離する。
7. 製品共通知識は複数Owner・複数案件で再現し、Reviewと署名を経てKnowledge Packとしてreleaseする。
8. 新Packは段階適用し、品質低下時は以前のGit versionへrollbackする。

## Real-production hypotheses registered for future evaluation

Owner提供の11制作資料から、次を「正解」ではなく検証対象の初期仮説として登録する。

- 実素材優先は、ブランド信頼性を上げつつ生成コストと再修正を減らす。
- 密な日本語UIをLocked／Static／post-compositeにすると文字化け再生成率が下がる。
- 仮ナレーション実尺からSRTと一本化WAVを作ると手動配置時間と同期ずれが減る。
- Scene末尾HoldはScene間接続の不安定さと視認不足を減らす。
- Full Mix／Stem候補を同条件で比較すると、単一手法固定より採用後の再修正が減る。
- RAW／処理後の比較と複数再生環境評価は、音響処理の過剰適用を減らす。

評価時は動画種別、文字密度、Provider、再生環境を条件として保持し、単一作品の成功だけでKnowledge Packへ昇格しない。

## Scoring model

単一の総合点だけで自動採用しない。候補スコアは少なくとも、品質改善、再修正削減、時間短縮、QA適合、ユーザー採用、権利・安全、サンプル信頼度を別軸で保持する。Safety/Rights違反は加重点で相殺できないHard Gateとする。重みは動画種別とOwner Profileごとにversion管理する。

## Cloud privacy floor

- Cloud learningは初期状態OFFで、目的別の明示Opt-inと撤回を提供する。
- 元動画、音声、画像、字幕本文、Prompt、個人情報、API credentialは既定で送信禁止。
- tenant分離、暗号化、retention、削除要求、export、監査、地域選択を契約化する。
- 少数集合、希少特徴、再識別可能な値は送信または集約結果から除外する。
- Cloud障害や不同意でもOwner-local learningは継続可能にする。

## Dependencies

TASK-003 Evidence/Asset、TASK-007 Cut Plan、TASK-010 Resolve Assembly、TASK-011 QA、TASK-012 Manual Handoff、TASK-019 Profile Auto-TunerおよびTASK-021 Dashboardと接続する。初回基本編集完成を妨げない後続機能とする。

## R9D hosted closure read-back — 2026-08-26

- target PR #364: merged at 4e698fd47c9308a696bdf43549f322f390a9b3fd; hosted checks 9 / 9 PASS; post-main CI 32937505491 PASS (6 / 6) and Security 32937505492 PASS.
- lock-host PR #371: merged at 563c72be100fb2b7c5bd786693a499d537314cd0.
- closure PR #373: merged at fresh main fc9398950b07759f82b91801f76f9f3eea195462; hosted checks 9 / 9 PASS; post-main CI 32939237218 PASS (6 / 6) and Security 32939237213 PASS.
- Registry revision 97 records HOSTED_CLOSED_RELEASED, AUTHORIZED_SCOPE_CONSUMED_CLOSED, target MERGED_POST_MERGE_GREEN, active nonclosed integration locks 0 and the approved CHANGELOG bullet exact 1.
- Real Owner key/signing, Knowledge Pack write/promotion, automatic promotion, runtime Profile apply, rollback execution, Release, Deploy and Production remain unexecuted or denied by their existing Gates.

## R10A implementation - body-free Knowledge Pack promotion preflight

R10A transitively recompiles the exact R8 signature request and its R6/R7
inputs, then cross-binds a body-free R9A verification receipt and a terminal
R9D signing-journal receipt. The output binds every Pack, predecessor, signer,
message, detached-signature digest, verification, journal and ceremony
coordinate without accepting key bytes, signature bytes, secrets or paths.
The request payload is copied once from an exact built-in dict before any
verification read; the verifier and typed read-back consume only that same
hook-free snapshot. Stateful Mapping hooks are rejected and concurrent caller
mutation cannot switch the request between validation phases.

R9A and R9D body-free receipt objects remain publicly constructible. Therefore
R10A records the upstream verification claim but does not authenticate its
cryptographic origin. The projection fixes signature origin authentication,
signature verification and promotion-confirmation eligibility to false.

The result is an in-memory preflight only. Explicit Human confirmation,
canonical storage, runtime compatibility validation and signature-artifact
custody remain later gates. Pack write/promotion, automatic promotion, runtime
apply, rollback execution, Release, Deploy and Production remain unauthorized.

## R10B implementation - trusted in-call signature admission

R10B re-runs the R9A Ed25519 verifier in the current call with the exact frozen
R8 request, caller-supplied self-validating signer policy, transient public key
and detached signature. The complete nested R6-R8 compile tree is rebuilt from
an explicit allowlist of exact Product enums and frozen dataclasses; every public
JSON surface requires one recursively frozen exact built-in tree before parsing.
Security-relevant scalar boundaries require exact built-in `str`, `int` and
`bytes`; same-value subclasses cannot override causality or survive projection.
The verifier result must reproduce the R10A verification claim exactly, after
which R10A is recompiled and matched to the supplied intent. This closes the
constructible verification-receipt execution gap for the current call without
trusting a caller-selected success object. The exact R9C ceremony receipt is
cross-bound to the terminal R9D journal, request, signer, signature and
verification coordinates. R10B verification time must be at or after the R10A
intent, R9C completion and R9D terminal journal update.

The public key and detached signature are not returned or persisted, and
private key material is not accepted. The body-free admission is itself public
constructible and therefore non-authoritative when detached from direct
recompilation. Because this Unit has no canonical Owner trust-root or latest
policy reader, it claims only mathematical verification against the supplied
policy. Canonical/latest source revalidation, canonical signer-origin
authentication, Owner signer binding and canonical trusted-policy revalidation
are fixed false. Signature-artifact custody, canonical receipt/store,
runtime-compatibility validation and explicit Human promotion confirmation
remain later Gates. Knowledge Pack write/promotion, automatic promotion,
runtime apply, rollback execution, Release, Deploy and Production remain
unauthorized.

## R10C implementation - body-free signature artifact custody candidate

R10C consumes R10B's exact next state and prepares a body-free, in-memory
candidate for a later Owner-local signature-artifact custody transaction. It
reconstructs exact R9B key-custody, R9C signing-ceremony and R10B trusted
signature admission payloads from bounded hook-free built-in JSON snapshots.
R9C must bind the exact R9B custody receipt, and its ceremony, request, signer,
detached-signature digest and verification receipt coordinates must equal R10B.
The Owner scope comes only from the R9B encrypted key-custody receipt, whose
signer must equal the R10B signer. Source causality is hard-gated: R9C cannot
complete before R9B custody, and R10B cannot verify before R9C completion.
Candidate creation cannot predate any of those exact source events. The
artifact store coordinate is a logical ID only; host paths and URI-like values
are rejected by both runtime validation and the public schema.

The output contains only stable identifiers and hashes. It requires a later
write boundary to direct-recompile R10B with transient public-key and detached
signature bytes, repeat cryptographic verification, receive explicit Human
custody confirmation, and use an Owner-local encrypted one-shot store. The
candidate itself remains publicly constructible and non-authoritative.

Artifact bytes, public/private key material, host paths and credentials are not
included. Artifact custody write/confirmation, canonical receipt, canonical
trust root, Owner signer binding, Knowledge Pack write/promotion, automatic
promotion, runtime apply, rollback, Release, Deploy and Production remain
unauthorized. Project/reviewer coordinates and actual artifact custody remain
later Gates.

## R10D implementation — encrypted signature artifact staging

R10D consumes the exact R10C candidate and performs one non-authoritative
encrypted staging write for a transient Ed25519 public key and detached signature. Before
writing, it directly recompiles R10B with those exact bytes, repeats
cryptographic verification, recompiles R10C from exact R9B/R9C/R10B Evidence,
and binds a caller intent attestation to the candidate, Owner scope,
artifact-store ID, request, signer, signature digest and time. This public
attestation does not authenticate Human origin and does not authorize custody.

The production constructor is fixed to Windows Current User DPAPI with an R10D-specific entropy
domain distinct from private-key custody. The disk envelope contains ciphertext
and integrity metadata only. The one-shot write rejects an existing destination
or symlink, uses validated atomic replace, and decrypts/validates the replaced
file before returning a body-free receipt. Public-key and signature bodies stay
inside encrypted local storage; no private key, seed, passphrase, credential,
host path, media, or Project content is accepted or returned.

Production callers cannot inject a cipher. Private test construction is always
marked test-only and cannot claim DPAPI or encryption at rest, even when the
test cipher round-trips. Prefix, byte-rotation, unauthenticated and DPAPI-suite
spoof ciphers therefore cannot mint production encryption/custody claims. Store
configuration is slots-backed and read-only, and the encrypt/decrypt/receipt
boundaries revalidate the exact production DPAPI type, suite, and mode so a
forced post-initialization replacement fails before write.

The path model remains `COOPERATIVE_PROTECTED_LOCAL_WRITER_ONLY`. Directory
durability, power-loss replay prevention, hostile ancestor/path races, deletion
recovery and alternate-path replay are not confirmed. Canonical Owner trust
root, Owner-signer identity binding, canonical Knowledge Pack receipt,
verified Owner-local path, Human confirmation origin, custody write authority,
custody completion, Knowledge Pack write/promotion, automatic promotion, runtime apply, rollback,
Timeline/Resolve, Release, Deploy, Production and external effects remain
unauthorized.

R10D source scope is exact six paths. Focused R10D after the independent High
finding rework is `19 PASS / 2 Windows-only DPAPI SKIP`; R9B-R10D direct is
`102 PASS / 3 SKIP`, and TASK-029 is `180 PASS / 6 SKIP`. Full Product is
NOT_CONFIRMED because the pre-existing WSL environment
has cryptography 41.0.7 and no `referencing`, while fresh-main TASK-059 requires
Argon2 support from cryptography >=46 and that package; collection stopped on
dependency import errors before tests ran. No dependency was installed.

TASK-059's target and closure are merged, Registry revision 115 records its
shared lock as `HOSTED_CLOSED_RELEASED`, and no active pending integration lock
remains. R10D will integrate fresh main after its exact6 commit-ready checkpoint
and obtain a separate exact CHANGELOG lock only after independent DEV-4 GO.
