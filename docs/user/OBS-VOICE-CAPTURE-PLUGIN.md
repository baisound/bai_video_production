# OBS Voice Capture Plugin 導入・利用・復旧ガイド

> **文書状態: LOCAL DRAFT / DEV.8 PACKAGE + INSTALL + SYNTHETIC LOAD・CONTROL EVIDENCE BOUND / OWNER音声未確認**
> `P_OBS_PLUGIN_DEVELOPMENT_COMPLETE`: `NOT_ESTABLISHED`

この文書は、BAI Video ProductionのOBS Voice Capture Pluginを安全に導入し、
録音操作と異常復旧を確認するための公開マニュアル案です。

Local buildのPlugin package、Version、SHA-256、manifest、build/test Evidence、exact 3-entry
配置のinstall receipt、OBS 32.2.1での合成音声によるload・GAIN測定・開始・一時停止・再開・
停止・WAV保存Evidenceは確認済みです。Owner音声、正式RecordingSession、Dataset採用、Release、
Deploy、配布、Production利用は確認・認可していません。

## このPluginが行うこと

将来の正式版は、利用者がOBS上で明示的に選択した音声Sourceから、録音Sessionの
開始・一時停止・再開・停止を安全に扱うことを目的とします。

次の処理は別の判断・権限です。

- OBSの音声や配信信号を自動で変更すること
- 録音素材を自動でAssetやDatasetへ採用すること
- 学習、Fine-tuning、Model生成を自動で開始すること
- 録音、Dataset採用、学習、公開のHuman Gateを省略すること

## 最終導入形態

最終的なOwner向け配布形態は、ZIPを手作業でコピーする方式ではなく、署名・昇格方針を
Evidenceで固定したWindowsインストーラーとします。現在のZIPとexact 3-entry手順は、開発、
検証、復旧用artifactです。最終インストーラーはOBSの検出・選択、Version/architecture、
process停止、path containment、reparse/collision、disk floor、package hash、backup、journal、
staging、原子的配置、read-backを実施し、Install / Repair / Update / Uninstallを別transactionで
扱います。Scene、Profile、Source、device、GAIN、+48V、PAD、HPFは自動変更しません。

日本語・英語対応の`0.1.0-dev.8-installer.4`はローカル技術候補として実装・検証済みです。
OBS 32.2.1の選択、Version、停止状態、reparse、書込権限、空き容量、existing file hash、
backup、journal、read-backを検査します。現候補は未署名で一般配布していません。Production
installerやRelease/Deploy済み成果物として表示せず、署名とPublisher表示はRelease Gateで扱います。

## 初めて使う方へ（日本語）

### このガイドでできること

この章は項目数を覚えるための「10手順」ではありません。上から順に読むだけで、Pluginを安全に導入し、保存先と安全停止条件を決め、GAINを確認し、
録音を開始・一時停止・再開・停止して、最後に保存fileを確認できます。現在のdev.8は開発検証版で、
一般利用者向けの最終インストーラーはまだ未公開です。最終版ではZIPをOBSフォルダーへ手作業で
コピーする必要はありません。

### 導入する前の準備

Windows 10/11の64-bit版と、OBS Studio 32.2.1（64-bit）を用意します。OBSで配信や録画をして
いる場合は先に終了し、OBSを通常のメニューから閉じます。作業中のSceneや設定は保存しておきます。

一般配布版を入手したら、案内されたVersion、SHA-256、Publisherが一致することを確認します。
現在のローカル技術候補は未署名です。開発検証に参加していない方は、未署名候補を別経路から
入手して実行しないでください。一致しないfileや予期しないWindows警告ではそこで中止します。

### インストーラーで導入する

インストーラーが検出したOBSを確認します。OBSが複数ある場合は、普段使う32.2.1を選びます。
先へ進むと、インストーラーがOBS停止、32.2.1、空き容量、reparse、書込権限、既存fileのhashを
確認します。不合格なら理由を表示して配置前に停止します。既存の同一fileがある場合はbackupされ、
処理履歴が残ります。完了画面が出るまでPCやインストーラーを強制終了しないでください。

### Controllerを開いて保存先を決める

`BAI 学習データ録音コントローラ`を開きます。OBSが既に開いていたら、いったん通常終了します。
`保存先`の`参照...`を押し、空き容量が十分なフォルダーを選びます。保存先は録音のたびに変更
できます。続けて`最大録音時間`（1〜120分）と`停止する空き容量`を設定します。初めて試す時は、
短い最大時間にしてください。

### 録音前にGAINを確認する

`録音前GAINチェック（5秒・保存なし）`を押し、案内された音量で発声します。この確認では
音声fileを保存せず、Peak、RMS、clippingだけを測定します。Pluginは物理GAIN、+48V、PAD、
HPFやOBS設定を自動変更しません。

clippingが表示された場合は録音を始めず、物理GAINを少し下げてからもう一度確認します。
Quality Policyが未設定の時は、数値が表示されても自動で`適正`とは判定しません。

### 録音を開始する

`録音準備＋OBS起動`を押します。Controllerがその録音だけに使う鍵を安全に渡してOBSを起動します。
赤い`● 学習データ録音中`が表示されたことを必ず確認してから話してください。画面には経過時間、
保存量、保存先の空き容量、packet gap、認証失敗が表示されます。赤い表示がなければ録音中ではありません。

### 一時停止して再開する

話を中断する時は`一時停止`を押します。橙色の一時停止表示中はWAVへ追記せず、Pluginも音声copyを
停止します。再び話す時は`再開`を押し、赤い録音中表示へ戻ったことを確認してから続けます。

### 録音を停止してfileを確認する

終了時は`録音停止`を押します。`.partial.wav`が確定した`.wav`へ変わり、同名の
`.receipt.json`が作られるまで待ちます。保存先で両方を確認した後、OBSを通常終了します。
録音したWAVはDatasetやTrainingへ自動採用されません。採用、削除、公開は別のOwner確認で行います。

途中で困った場合は、まず`録音停止`を押し、Controllerに表示された停止理由を控えます。電源断、
file削除、上書きインストール、自動rollbackを先に行わず、[困ったとき](#困ったとき)を参照してください。

## Beginner guide (English)

### What this guide covers

This is not a fixed ten-step checklist to memorize. Read this section from top to bottom to install the Plugin, select a destination and safety limits, check gain,
record, pause, resume, stop, and verify the saved files. The current dev.8 build is for engineering validation.
The bilingual `0.1.0-dev.8-installer.4` is implemented and verified as a local technical candidate. It is not
code-signed or publicly distributed, and it must not be presented as a Production installer or Release/Deploy.

### Prepare the computer

Use 64-bit Windows 10/11 and 64-bit OBS Studio 32.2.1. Finish any stream or recording, save your work, and exit
OBS normally. When a public installer becomes available, verify its version, SHA-256, and Publisher. The current
local technical candidate is unsigned; do not run an unsigned copy obtained outside the controlled engineering
workflow. Stop when the file or Windows security prompt is unexpected.

### Install the Plugin

Confirm the OBS installation detected by the installer. When several copies exist, select the 32.2.1 instance
you normally use. The installer checks that OBS is closed and compatible, then checks disk space, reparse points,
write access, and existing-file hashes. It stops before placement and explains the reason when a check fails.
Matching existing files are backed up and the transaction is journaled. Wait for the standard completion page;
do not force-close OBS, the installer, or Windows during this work.

### Open the Controller and select a destination

Open **BAI Learning Voice Capture Controller**. If OBS is already running, exit it normally first. Select
**Browse** beside **Destination** and choose a folder with enough free space. You may change this folder for each
session. Set **Maximum recording time** (1–120 minutes) and **Stop at free-space floor**; use a short limit first.

### Check gain before recording

Select **Pre-recording gain check (5 seconds, no audio saved)** and speak at the requested level. The check
measures peak, RMS, and clipping while saving no audio and changing no physical gain, +48 V, PAD, HPF, or OBS
setting. If clipping is detected, do not record. Lower the physical gain slightly and check again. Without an
approved Quality Policy, measured values are not automatically labelled “good.”

### Start recording

Select **Prepare recording + start OBS**. The Controller starts OBS with an ephemeral key used only for that
session. Speak only after the red **● Recording learning data** banner appears. The window shows elapsed time,
saved bytes, destination free space, packet gaps, and authentication failures. No red banner means no recording.

### Pause and resume

Select **Pause** when interrupted. While the amber paused banner is visible, the WAV does not grow and the Plugin
stops copying audio. Select **Resume**, wait for the red banner to return, and then continue speaking.

### Stop and verify the result

Select **Stop recording**. Wait until the `.partial.wav` becomes a finalized `.wav` and a matching
`.receipt.json` appears. Verify both files in the destination, then exit OBS normally. The WAV is not automatically
adopted into a Dataset or Training run; adoption, deletion, and publication require separate decisions.

If something goes wrong, select **Stop recording**, note the reason shown by the Controller, and follow
[Troubleshooting](#困ったとき). Do not delete files, overwrite the installation, or attempt an automatic rollback first.

## 現在の確認状況

| 項目 | 値 | 状態 |
|---|---|---|
| Package target OBS build | `32.2.1` | `PASS` |
| Module ID | `bai-voice-capture` | `PASS` |
| Plugin version | `0.1.0-dev.8` | `PASS` |
| Local installer candidate | `0.1.0-dev.8-installer.4` / SHA-256 `7f1dff48059f3eb292bae32185080d26a50303313e1128ee1286666bc9faabd6` | `PASS` |
| 対応architecture | `windows-x64` | `PASS` |
| Runtime package名 | `bai-voice-capture-0.1.0-dev.8-windows-x64.zip` | `PASS` |
| Runtime package bytes | `36357` | `PASS` |
| Runtime package SHA-256 | `4e8fcdf6f697da059ef3aa9ae703a400d0f85e9ed89d77ace9f624dc2783e20f` | `PASS` |
| Package manifest SHA-256 | `5d76e81c233c0a8ec42b2c1075043c8b967e2ed353047768ce123859f709c351` | `PASS` |
| Dev.8 Evidence receipt SHA-256 | `980701cc2096bdda3455985d8d3dfa44d45a8e7ad3438dd665314fadbde7d02d` | `PASS` |
| Plugin DLL bytes / SHA-256 | `23040` / `14839bcad60fe47583a97729e3dc41c23b9f6c06012d5a83a38d8fc04b435b38` | `PASS` |
| Controller bytes / SHA-256 | `30208` / `273fe96a952b1120b422785ee4c70a9612ba6f44c6d95f06447497abb52afb3f` | `PASS` |
| Source ZIP filename | `bai-voice-capture-0.1.0-dev.8-source.zip` | `PASS` |
| Source ZIP bytes / SHA-256 | `41065` / `4dcd50f3aadaf95798a4d82ad511a66b14ad5a1e81a131a3bd65c0c5f933b0a4` | `PASS` |
| Source manifest SHA-256 | `1240807112913af15df53f5c14c125426d3a62c42f745592bd04aefb7c0bd1c8` | `PASS` |
| Plugin implementation / build / test / package | Local build Evidence確認済み | `PASS` |
| Configure | `PASS` | `PASS` |
| Release build | `PASS` | `PASS` |
| Core/security synthetic suites | `3 / 3 PASS` | `PASS` |
| CTest | `1 / 1 PASS` | `PASS` |
| License | `GPL-2.0-or-later` | `LEGAL_REVIEW_REQUIRED` |
| Release・Deploy・配布許可 | なし | `LEGAL_REVIEW_REQUIRED` |
| Install先layout | Exact 3-entry OBS-root relative map | `PASS` |
| Exact 3-entry install | `VERIFIED_INSTALLED` | `PASS` |
| Install receipt SHA-256 | `dbfa5c78ac87083357bfba28e4b9e82bfa1542aa2b7305a14ab5293d4143bf4f` | `PASS` |
| Backup | Dev.7 exact3を別transactionへ保存 | `PASS` |
| Rollback結果 | 未確認 | 未確認 |
| OBS load結果 | OBS 32.2.1 / 合成音声scene | `PASS` |
| 録音中の常時表示 | `● 学習データ録音中` | `PASS` |
| 保存先・最大時間・disk floor | Controllerから変更可能 | `PASS` |
| START/PAUSE/RESUME/STOP | 合成音声、Pause中WAV増加0 | `PASS` |
| Recording receipt SHA-256 | `f7dd39b2283c25553c0c3c2e648d5ddc5b94d73ab19b511fde1079fabdaecf64` | `PASS` |
| 録音前GAINチェック | 5秒、音声body保存0、設定変更0 | `PASS` |
| GAIN receipt SHA-256 | `80018c274ec911d5b7e12ba8c6d8f2a4ebd2c99575cdbe65073d3adfa9aa19c9` | `PASS` |
| Owner音声・正式RecordingSession | 未実施 | 未確認 |
| 異常終了・rollback・recovery | 一部未実施 | 未確認 |

`PASS`のartifact値はcanonical local build receiptへ、install値はexact transaction receiptへ
bindingした値です。Installの`PASS`をload、録音、保存、rollbackの`PASS`へ読み替えません。

## 判定語

各チェックは次のいずれかで記録します。

| 判定 | 意味 |
|---|---|
| `PASS` | 対象VersionとEvidenceを固定して確認済み |
| `FAIL` | 既知の不一致または失敗を確認済み |
| `UNKNOWN` | 処理結果や外部状態を確定できない |
| `未確認` | まだ確認を開始していない |
| `NOT_APPLICABLE` | 承認済みPolicy上、その項目が対象外 |
| `LEGAL_REVIEW_REQUIRED` | Licenseは識別済みだが、配布・公開等の法務判断が未完了 |

`UNKNOWN`や`未確認`を`PASS`へ読み替えないでください。件数や音声欠損が不明な場合も
`0`として扱いません。

## 1. 導入前チェックリスト

次の全項目が`PASS`になるまで、PluginファイルをOBSのフォルダーへコピーしません。

### 1.1 Authorityと対象

- [x] 導入作業に対する明示的な許可がある — 状態: `PASS`
- [x] 対象PC、OBS build、architectureが許可内容と一致する — 状態: `PASS`
- [x] OBSが停止し、対象OBS processが0件である — 状態: `PASS`
- [x] Scene Collection、Profile、Source設定を変更しない範囲が明確 — 状態: `PASS`
- [x] 録音・Source選択・device操作は導入作業と別Gateである — 状態: `PASS`

### 1.2 Package identity

- [ ] Package名、Version、SHA-256が正式なlocal build Evidenceと一致する — 状態: `PASS`
- [ ] ManifestとPackage receiptのSHA-256が固定されている — 状態: `PASS`
- [ ] Module ID、architecture、target OBS buildが固定されている — 状態: `PASS`
- [ ] Configure、Release build、synthetic tests、CTest Evidenceが固定されている — 状態: `PASS`
- [ ] License、Notice、source-offer、配布境界の法務確認を完了した — 状態: `LEGAL_REVIEW_REQUIRED`
- [x] Package内に絶対path、Credential、音声、個人情報がない — 状態: `PASS`

### 1.3 Install先とcollision

- [x] 対象rootが許可されたOBS install内に収まる — 状態: `PASS`
- [x] `..`、絶対path、junction、symlink、reparse traversalがない — 状態: `PASS`
- [x] 既存PluginとModule ID、filename、data/locale pathが衝突しない — 状態: `PASS`
- [x] 同名で内容が異なる既存fileを検出した場合は停止する — 状態: `PASS`
- [x] stagingとtargetが同一volumeである — 状態: `PASS`
- [x] 必要disk容量とrollback用容量を確保した — 状態: `PASS`

### 1.4 Exact 3-entry deployment map

Runtime packageの`PASS`だけでは配置先を確定しません。Leadのcanonical runtime ZIP、package
manifest、install-readiness handoffをread-onlyで照合し、OBS rootからの相対pathで次の3 entryを
固定しました。Host absolute pathは公開せず、一般的なOBS layoutから補完していません。

| Entry | Package内source relative path | OBS rootからのtarget relative path | Bytes / SHA-256 | 状態 |
|---|---|---|---|---|
| 1 / 3 | `obs-plugins/64bit/bai-voice-capture.dll` | `obs-plugins/64bit/bai-voice-capture.dll` | `23040` / `14839bcad60fe47583a97729e3dc41c23b9f6c06012d5a83a38d8fc04b435b38` | `PASS` |
| 2 / 3 | `data/obs-plugins/bai-voice-capture/locale/en-US.ini` | `data/obs-plugins/bai-voice-capture/locale/en-US.ini` | `478` / `066718cb394b9af07319f4bb4a0f6eb7cc50e45e73ffc76662c588ccbaa8ae8d` | `PASS` |
| 3 / 3 | `data/obs-plugins/bai-voice-capture/locale/ja-JP.ini` | `data/obs-plugins/bai-voice-capture/locale/ja-JP.ini` | `525` / `c55315f3973893bfe9303766df7ab824751e93a84a0a607224a3b465fbf63f4e` | `PASS` |

- [ ] canonical manifest上のdeployment entry数がexact 3である — 状態: `PASS`
- [ ] 3 entryすべてのsource/target relative path、bytes、SHA-256が固定されている — 状態: `PASS`
- [ ] sourceとtargetに絶対path、`..`、junction、symlink、reparse traversalがない — 状態: `PASS`
- [x] Backup/collision/read-back対象がこのexact 3 entryと一致する — 状態: `PASS`

ZIP rootの`LICENSE`、`NOTICE.md`、`package-manifest.json`、`UPSTREAM-OBS-COPYING.txt`は
OBS rootへ配置しません。entry数・path・digestのいずれかが不明または不一致なら導入を開始
しません。Public Evidenceへhost absolute pathを出さず、private Evidenceでもcanonical rootからの
containmentをoperation直前に再検証します。

## 2. Backupチェックリスト

Backupは導入前の状態を復元するためのものです。録音素材、Scene、Profileを無断で
収集する仕組みではありません。

- [x] Install operation IDを発行した — 状態: `PASS`
- [x] 対象fileの存在・非存在を含む旧manifestを保存した — 状態: `PASS`
- [x] 既存fileは0件で、exact 3 entryのabsent tombstoneを記録した — 状態: `PASS`
- [x] Backup manifestを対象root外のprivate transaction領域へ保存した — 状態: `PASS`
- [x] 必要disk容量を確認した — 状態: `PASS`
- [x] 旧manifestをread-backした — 状態: `PASS`
- [x] 公開マニュアルにCredential、host path、device fingerprintを記録しない — 状態: `PASS`

Backup manifestに最低限必要な項目:

```text
backup_operation_id
source_manifest_sha256
backup_manifest_sha256
relative_path
file_state = PRESENT | ABSENT
byte_size
sha256
created_at
retention_state
verification_state
```

## 3. 導入チェックリスト

Package identity、exact 3-entry deployment map、install transactionは固定済みです。初回の
最終validatorは`FINAL_DRIFT_1`で安全停止しましたが、各atomic publishの即時read-back、
journal hash-chain、現targetのbytes/SHA-256を再照合し、targetを再書込みせずreceiptを封印しました。
将来の導入・更新でも、次の順序を崩さないでください。

この章の手動手順は最終インストーラーが同じGateを実装・証跡化するためのreferenceです。
最終利用者へ手動コピーを要求する設計ではありません。

1. Packageを許可されたstaging領域へ展開する。
2. 展開後manifest、file size、SHA-256、containmentを検証する。
3. OBS processが0件であることをもう一度確認する。
4. Backup Evidenceが`PASS`であることを確認する。
5. Journalを作成し、publish前状態を`PENDING_STAGED`として記録する。
6. 同一volume上の承認済みpublish操作を開始する。
7. targetの全fileをread-backし、manifestと照合する。
8. 全項目一致時だけ`VERIFIED_INSTALLED`と記録する。

許可される状態遷移:

```text
PENDING_STAGED
  -> PUBLISHING
  -> VERIFIED_INSTALLED | FAILED_KNOWN | UNKNOWN | CORRUPT_OR_INCOMPLETE
```

Timeout、crash、partial visibilityでは成功を主張しません。結果不明時に同じ導入を自動
retryしたり、別の導入effectを発行したりしません。

### 導入結果

| 項目 | 証跡 | 判定 |
|---|---|---|
| Package read-back | Runtime bytes/SHA-256一致 | `PASS` |
| Target manifest一致 | Exact 3 / bytes・SHA-256一致 | `PASS` |
| Unexpected deployment file | 0件 | `PASS` |
| Journal terminal state | Sequence 5 / `VERIFIED_INSTALLED` | `PASS` |
| Journal head SHA-256 | `2c122375cb142218d387f105c1411c5bc8548008d5302e63824e145004efa839` | `PASS` |
| Install receipt SHA-256 | `dbfa5c78ac87083357bfba28e4b9e82bfa1542aa2b7305a14ab5293d4143bf4f` | `PASS` |
| Reconcile中のtarget再書込み | `false` | `PASS` |
| OBS load / 合成音声Controller録音 | Start/Pause/Resume/Stop + WAV receipt | `PASS` |

## 4. Rollback・復元チェックリスト

Rollbackは導入失敗時の自動処理ではなく、別の明示的なRecovery operationです。

- [ ] Recovery操作の明示的な許可がある — 状態: `未確認`
- [ ] 導入結果を`FAILED_KNOWN`、`UNKNOWN`、`CORRUPT_OR_INCOMPLETE`から区別した — 状態: `未確認`
- [ ] 正しいBackup operation IDとmanifestを選択した — 状態: `未確認`
- [ ] OBS processが0件である — 状態: `未確認`
- [ ] 現target manifestを復元前Evidenceとして固定した — 状態: `未確認`
- [ ] 旧fileを復元し、導入前に存在しなかったfileだけを対象どおり除外した — 状態: `未確認`
- [ ] 復元後の全fileをread-backした — 状態: `未確認`
- [ ] 旧manifestと完全一致した場合だけ`ROLLBACK_VERIFIED`にした — 状態: `未確認`
- [ ] 以前の`UNKNOWN`履歴を成功へ書き換えていない — 状態: `未確認`

復元後も、OBS load確認は別に実施します。復元成功だけでPlugin利用可能とは判断しません。

## 5. OBS読込確認チェックリスト

この章のうち、local dev.8と合成音声sceneで確認した項目だけを`PASS`にしています。

- [x] 対象OBS buildと実行architectureがmanifestに一致する — 状態: `PASS`
- [x] 読み込まれたModule IDとVersionが成果物に一致する — 状態: `PASS`
- [x] OBS logにload error、ABI mismatch、missing dependencyがない — 状態: `PASS`
- [ ] 想定外のPlugin、DLL search path、side-loadがない — 状態: `未確認`
- [ ] Scene、Profile、Source、Filter、Mixer設定に変更がない — 状態: `未確認`
- [x] Plugin/Controllerの録音中・一時停止・GAIN測定状態表示が確認できる — 状態: `PASS`
- [ ] 未選択Sourceで録音開始できない — 状態: `未確認`
- [x] OBS終了・再起動後もVersionとModule identityが一致する — 状態: `PASS`

Display nameだけをSource identityとして使いません。正式確認では、privateなProfile、
Scene Collection、Source UUID、graph digest、endpoint bindingを使用し、公開Evidenceでは
redactします。

## 6. 録音操作の受入チェックリスト

合成音声ではStart/Pause/Resume/Stop、WAV確定、receipt、常時表示を確認済みです。
Owner voiceを含む実録音には、別のConsent、Owner GO、保存先・暗号化・retention Gateが
必要であり、まだ実施していません。

### 6.1 共通Preflight

- [ ] exact Session revisionとcommand hashを固定した — 状態: `未確認`
- [ ] VoiceProfile/Consentのcurrent評価が`PASS`である — 状態: `未確認`
- [ ] 選択Sourceのprivate identityとcurrent graphが一致する — 状態: `未確認`
- [ ] capture adapter revision/hashがload済みModuleと一致する — 状態: `未確認`
- [ ] target formatとmeasured formatが一致する — 状態: `未確認`
- [ ] encrypted staging、disk floor、recovery、retentionが`PASS`である — 状態: `未確認`
- [ ] recording-specific Human Gateが有効期限内である — 状態: `未確認`

### 6.1a 録音前GAINチェック

1. 保存先とOBS実行ファイルを確認します。
2. `録音前GAINチェック（5秒・保存なし）`を押します。
3. 青い`● 録音前GAINチェック中（音声保存なし）`が表示されている間だけ、対象scenarioの
   音量で発声します。合成試験ではPeak、RMS、clip countを測定し、音声body保存0を確認済みです。
4. `clip > 0`ではhardware gainを下げる提案を表示できますが、Pluginはpreamp、OS、OBS、
   +48V、PAD、HPFを自動変更しません。
5. Quality Policyが未bindingの場合、Peak/RMSを測定できても`適正`とは表示しません。

最終的にはroom tone、通常声、大声、whisper、normal-intermediateを別scenarioとして測定し、
同じCaptureChain/Analyzer/Policy revisionへbindingします。短い通常声の結果を他scenarioや
30分〜2時間のDataset全体へ外挿しません。Owner音声による各scenario測定は未確認です。

### 6.2 START

- [ ] P-VSが発行したSession/Segment/Attempt identityを使用する — 状態: `未確認`
- [ ] Pluginがidentityを生成・置換しない — 状態: `未確認`
- [ ] `COMMAND_ACCEPTED`と`CAPTURE_STARTED`を別eventとして確認する — 状態: `未確認`
- [ ] ACKだけで録音成功を表示しない — 状態: `未確認`
- [x] 可視状態が`● 学習データ録音中`へ遷移する — 状態: `PASS`（合成音声）

### 6.3 PAUSE

- [ ] `PAUSE_ACKNOWLEDGED`を確認する — 状態: `未確認`
- [ ] bounded drain、最後のsource frame/sample rangeを固定する — 状態: `未確認`
- [ ] 未完文・partial captureをEvidenceへ記録する — 状態: `未確認`
- [x] PAUSE中にWAV byteが増加せず、Pluginがunauthorized fast-pathへ戻る — 状態: `PASS`（合成音声）
- [ ] PAUSEをSTOP成功として扱わない — 状態: `未確認`

### 6.4 RESUME

- [ ] 同じSegment、cue、sentence、text bindingを使用する — 状態: `未確認`
- [ ] P-VS発行の新Attempt identityを使用する — 状態: `未確認`
- [ ] `attempt_number = old + 1`とexact parent hashを確認する — 状態: `未確認`
- [ ] 未完文は文頭anchorから再録する — 状態: `未確認`
- [ ] Pluginが新SegmentやAttemptを勝手に作らない — 状態: `未確認`
- [ ] `RESUME_STARTED`を確認する — 状態: `未確認`
- [x] Controllerの再開表示、Pipe再接続、通常gap `0`を確認する — 状態: `PASS`（合成音声）

### 6.5 STOP

- [ ] `STOP_ACKNOWLEDGED`を確認する — 状態: `未確認`
- [ ] callback detach、in-flight zero、worker drainを確認する — 状態: `未確認`
- [ ] source frameとcanonical sample mappingを確定する — 状態: `未確認`
- [ ] staging receiptとretained Evidence ledgerを確認する — 状態: `未確認`
- [ ] 完全なCandidateと不完全・UNKNOWNを分離する — 状態: `未確認`
- [x] Dataset採用や学習を自動開始しない — 状態: `PASS`（local controller）

### 6.6 CANCEL

- [ ] `CANCEL_ACKNOWLEDGED`を確認する — 状態: `未確認`
- [ ] 外部work、staging、retained bytesの有無を確認する — 状態: `未確認`
- [ ] retained Evidenceがある場合にplain `CANCELLED`へ隠さない — 状態: `未確認`
- [ ] ACKや外部状態が不明なら`UNKNOWN`にする — 状態: `未確認`
- [ ] delete、Dataset review、adoptionを自動実行しない — 状態: `未確認`

## 7. 保存・Staging受入チェックリスト

- [x] Callback内ではbounded copyと最小metadata以外を行わない — 状態: `PASS`（source/test）
- [x] Disk I/O、JSON、GAIN analysisはreceiver/controller worker側で行う — 状態: `PASS`（source/test）
- [ ] Native rangeとcanonical `48 kHz / 24-bit integer PCM / mono` rangeの対応を保持する — 状態: `未確認`
- [ ] Conversion profile、delay、tail、remainderをEvidenceへ記録する — 状態: `未確認`
- [ ] Byte checksum、sample count、range hashをprivate Evidenceへ保存する — 状態: `未確認`
- [ ] Drop、overrun、discontinuityのknown flagとcountを保持する — 状態: `未確認`
- [ ] 不明なcountを`0`へ変換しない — 状態: `未確認`
- [ ] Stagingは暗号化され、recovery/retention policyへbindingされる — 状態: `未確認`
- [ ] Stagingを同一objectのstate変更でAssetへ昇格しない — 状態: `未確認`
- [ ] Asset化、Dataset採用、Training開始は別receipt/Human Gateである — 状態: `未確認`

## 8. 異常終了・Recovery受入チェックリスト

| Scenario | 必須結果 | 状態 |
|---|---|---|
| Source切断 | `SOURCE_LOST`、capture停止、UNKNOWN範囲の隔離 | 未確認 |
| Profile/Scene/graph変更 | `SOURCE_SCOPE_CHANGED`、自動rebind禁止 | 未確認 |
| Format変更 | `FORMAT_MISMATCH`、成功禁止 | 未確認 |
| Ring full/overrun | 既知drop facts、discontinuity、成功禁止 | 未確認 |
| Oversized callback | callback unit全体をdrop、partial publish禁止 | 未確認 |
| Reentrant callback | copy 0、`CAPTURE_UNKNOWN` | 未確認 |
| Disk不足 | write停止、partial staging隔離、状態UNKNOWN/FAILED | 未確認 |
| IPC切断 | command/event reconciliation、duplicate effect禁止 | 未確認 |
| Worker crash | journal/staging read-back、no auto replay | 未確認 |
| Plugin crash | OBS/process/moduleとreceiptをread-reconcile | 未確認 |
| OBS crash/restart | old Sessionを自動継続せず、fresh preflight | 未確認 |
| Detach timeout | memory解放・成功claim禁止 | 未確認 |
| Receipt timeout | authoritative read/reconcile、retry禁止 | 未確認 |

Recoveryでは次を守ります。

1. `FAILED_KNOWN`と`UNKNOWN`を区別する。
2. Processの有無だけで成功・失敗を決めない。
3. 同じoperation/idempotency identityのcanonical receiptを照合する。
4. 外部状態が不明なまま新しいSTARTや保存effectを発行しない。
5. Partial stagingをCandidate、Asset、Datasetへ自動昇格しない。
6. 完全性を確認できない範囲は隔離し、Owner reviewへ送らない。

## 9. Evidence記録テンプレート

実機確認では、公開Evidenceとprivate Evidenceを分離します。

```text
test_case_id:
tested_at:
operator_kind:
authorization_ref:
obs_build:
plugin_package_id:
plugin_version:
package_sha256:
manifest_sha256:
module_id:
operation_id:
expected_result:
actual_result:
result: PASS | FAIL | UNKNOWN | 未確認 | NOT_APPLICABLE
public_evidence_digest:
private_evidence_ref:
notes:
```

公開Evidenceへ次を含めません。

- 音声body、音声に直接結びつくhash
- Script、Transcript、Reference Audio
- Device fingerprint、Source UUID、Profile、Scene Collection、graph detail
- Host absolute path、Credential、key reference
- Consent subject、private scope、private Evidence ID

## 10. 誤完了表示scan

公開前に、文書、UI、Evidenceを次の観点で確認します。
この節の`PASS`はdraft本文の静的scan結果だけを示し、Pluginの実装・導入・load・録音の
成功を示しません。

- [ ] `P_OBS_PLUGIN_DEVELOPMENT_COMPLETE`は最終Judge前に`NOT_ESTABLISHED` — 状態: `PASS`
- [ ] Plugin implementation/build/test/packageの`PASS`をexact local build receiptへ限定している — 状態: `PASS`
- [ ] Local buildの`PASS`をinstall/load/実機録音/Release/Deployへ昇格していない — 状態: `PASS`
- [ ] Runtime packageの`PASS`からexact 3-entry deployment mapを推測していない — 状態: `PASS`
- [ ] Canonical receiptで未確認のartifact値を具体値で表示していない — 状態: `PASS`
- [ ] Design完成をPlugin実装・導入・利用可能と表示していない — 状態: `PASS`
- [ ] Package展開成功をOBS load成功と表示していない — 状態: `PASS`
- [ ] OBS load成功を録音成功・Production Readyと表示していない — 状態: `PASS`
- [ ] Command ACKをcapture/save成功と表示していない — 状態: `PASS`
- [ ] Synthetic test成功を実機互換・Production Readyと表示していない — 状態: `PASS`
- [ ] Backup作成をRollback成功と表示していない — 状態: `PASS`
- [ ] `UNKNOWN`、未計測count、未確認を`0`や`PASS`に変換していない — 状態: `PASS`
- [ ] Dataset採用・Training開始・公開を自動化済みと表示していない — 状態: `PASS`

次の表現は、exact Evidenceと最終Judgeが揃うまで使用しません。

```text
導入済み
動作確認済み
利用可能
録音できます
復旧確認済み
Production Ready
P_OBS_PLUGIN_DEVELOPMENT_COMPLETEの値をPASSとする表現
```

## 11. 最終受入Gate

Plugin開発完了を主張するには、少なくとも次のGateがすべて必要です。

1. Exact source、toolchain、build、package、manifest、SHA-256のEvidence
2. License・Notice・配布境界の確認
3. Exact 3-entry deployment map、Backup、containment、collision、journaled install、read-backのPASS
4. Separate rollback operationとread-backのPASS
5. Exact OBS buildでのModule/ABI/load PASS
6. START/PAUSE/RESUME/STOP/CANCELのcommand/event/Evidence PASS
7. Save、drop/overrun/discontinuity、crash/restart/recoveryのPASS
8. Public/private redactionとtamper確認のPASS
9. Production Recording、Consent、storage、Owner GOが別Gateのままであること
10. Criticで未解決Critical/Highが0、最終Judgeが明示的にPASS

いずれかが`未確認`、`UNKNOWN`、`FAIL`なら、
`P_OBS_PLUGIN_DEVELOPMENT_COMPLETE`は`NOT_ESTABLISHED`のままです。

## 12. 成果物bindingと未確認Gate

Dev.8 local build/install/synthetic acceptanceから、公開可能なexact値だけをbindingしています。

| Field | 確定値 | Evidence |
|---|---|---|
| Module / Package ID | `bai-voice-capture` | Package receipt |
| Version | `0.1.0-dev.8` | Dev.8 Evidence receipt |
| Target | `windows-x64 / OBS 32.2.1` | Package receipt |
| Runtime filename | `bai-voice-capture-0.1.0-dev.8-windows-x64.zip` | Dev.8 Evidence receipt |
| Runtime bytes / SHA-256 | `36357` / `4e8fcdf6f697da059ef3aa9ae703a400d0f85e9ed89d77ace9f624dc2783e20f` | Dev.8 Evidence receipt |
| Runtime manifest SHA-256 | `5d76e81c233c0a8ec42b2c1075043c8b967e2ed353047768ce123859f709c351` | Dev.8 Evidence receipt |
| Dev.8 Evidence receipt SHA-256 | `980701cc2096bdda3455985d8d3dfa44d45a8e7ad3438dd665314fadbde7d02d` | Body-free local Evidence |
| DLL bytes / SHA-256 | `23040` / `14839bcad60fe47583a97729e3dc41c23b9f6c06012d5a83a38d8fc04b435b38` | Dev.8 Evidence receipt |
| Controller bytes / SHA-256 | `30208` / `273fe96a952b1120b422785ee4c70a9612ba6f44c6d95f06447497abb52afb3f` | Dev.8 Evidence receipt |
| Local installer candidate / SHA-256 | `0.1.0-dev.8-installer.4` / `7f1dff48059f3eb292bae32185080d26a50303313e1128ee1286666bc9faabd6` | Local technical installer receipt |
| Source artifact filename | `bai-voice-capture-0.1.0-dev.8-source.zip` | Dev.8 Evidence receipt |
| Source artifact bytes / SHA-256 | `41065` / `4dcd50f3aadaf95798a4d82ad511a66b14ad5a1e81a131a3bd65c0c5f933b0a4` | Dev.8 Evidence receipt |
| Source manifest SHA-256 | `1240807112913af15df53f5c14c125426d3a62c42f745592bd04aefb7c0bd1c8` | Dev.8 Evidence receipt |
| Build/test | Release build PASS / core-security 3 suites PASS / CTest 1 of 1 PASS / controller self-test PASS | Dev.8 Evidence receipt |
| License | `GPL-2.0-or-later` | `LEGAL_REVIEW_REQUIRED` |
| Release / Deploy / distribution authorization | なし | `LEGAL_REVIEW_REQUIRED` |
| Install receipt SHA-256 | `dbfa5c78ac87083357bfba28e4b9e82bfa1542aa2b7305a14ab5293d4143bf4f` | Exact 3 atomic install receipt |
| Install state | `VERIFIED_INSTALLED` | Install receipt |
| Load/control receipt SHA-256 | `f7dd39b2283c25553c0c3c2e648d5ddc5b94d73ab19b511fde1079fabdaecf64` | Synthetic Start/Pause/Resume/Stop receipt |
| Gain check receipt SHA-256 | `80018c274ec911d5b7e12ba8c6d8f2a4ebd2c99575cdbe65073d3adfa9aa19c9` | Synthetic 5-second measurement receipt |
| Owner voice / Production receipt | 未確認 | 未確認 |

値はcanonical成果物とreceiptから転記しています。Runtime filename、family名、
チャット文だけを根拠に別の値へ置き換えません。合成音声local acceptanceの`PASS`をOwner音声、
正式RecordingSession、Dataset、Training、Production、Release、Deploy、配布の`PASS`へ昇格しません。

## 困ったとき

- PackageやSHAが不明: 導入しない
- 既存fileとのcollisionを検出: 上書きせず停止する
- OBSが起動中: 導入・復元を開始しない
- 導入結果が不明: retryや自動rollbackを行わずread/reconcileする
- Source、Profile、Scene、deviceが変わった: 録音を止めfresh preflightを行う
- 音声欠損、drop、overrunが不明: `0`にせず`UNKNOWN`として隔離する
- Stagingが残った: 自動削除・Asset化・Dataset採用を行わない
- Public Evidenceにprivate情報が疑われる: 公開せずSecurity/Privacy reviewへ送る

このdraftの存在は、Pluginの実装、導入、OBS起動、録音、ReleaseまたはDeployを許可する
ものではありません。
