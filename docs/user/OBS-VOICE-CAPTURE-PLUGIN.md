# OBS Voice Capture Plugin 導入・利用・復旧ガイド

> **文書状態: PUBLIC TECHNICAL PREVIEW / DEV.10 SOURCE・BUILD・PACKAGE・INSTALLER EVIDENCE BOUND / DEV.10実機LOAD・OWNER音声は再確認待ち**
> `P_OBS_PLUGIN_DEVELOPMENT_COMPLETE`: `NOT_ESTABLISHED`

この文書は、BAI Video ProductionのOBS Voice Capture Pluginを安全に導入し、
録音操作と異常復旧を確認するための公開マニュアル案です。

Dev.10のPlugin source、build、runtime package、Windows installer、SHA-256は確認済みです。
Dev.8ではOBS 32.2.1へのexact 3-entry配置、合成音声と短いOwner音声によるload・GAIN測定・
開始・一時停止・再開・停止・WAV保存を確認しました。Dev.10の実機install/loadとOwner音声再試験は、
稼働中OBSを安全に通常終了できる時点で行います。公開後のインストーラー、runtime、source、SHA-256は
[GitHubの公開Technical Preview](https://github.com/baisound/bai_video_production/releases/tag/obs-voice-capture-v0.1.0-dev.10-installer.1)
から取得できます（公開前はlinkが未成立です）。正式RecordingSession、Dataset採用、Production利用は未確認です。

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

日本語・英語対応の`0.1.0-dev.10-installer.1`は技術候補として実装・検証され、公開Technical Previewへ
同梱する候補です。
OBS 32.2.1の選択、Version、停止状態、reparse、書込権限、空き容量、existing file hash、
backup、journal、read-backを検査します。現候補は未署名のPre-releaseです。Production installerや
BAI Video Production全体の安定版として表示せず、署名とPublisher表示は後続Gateで扱います。

## 初めて使う方へ（日本語）

### このガイドでできること

この章は項目数を覚えるための「10手順」ではありません。上から順に読むだけで、Pluginを安全に導入し、保存先と安全停止条件を決め、GAINを確認し、
録音を開始・一時停止・再開・停止して、最後に保存fileを確認できます。現在のdev.10は公開Technical Previewです。
[公式Release](https://github.com/baisound/bai_video_production/releases/tag/obs-voice-capture-v0.1.0-dev.10-installer.1)
のAssetsから`bai-voice-capture-0.1.0-dev.10-installer.1-windows-x64-setup.exe`を取得してください。
ZIPをOBSフォルダーへ手作業でコピーする必要はありません。

### 導入する前の準備

Windows 10/11の64-bit版と、OBS Studio 32.2.1（64-bit）を用意します。OBSで配信や録画をして
いる場合は先に終了し、OBSを通常のメニューから閉じます。作業中のSceneや設定は保存しておきます。

公式Releaseから入手し、VersionとSHA-256が一致することを確認します。現在のTechnical Previewは
未署名なので、Publisherが表示されない、またはWindowsの警告が表示される場合があります。
別サイト、転載、メール添付から取得せず、一致しないfileや想定外の警告ではそこで中止します。

### インストーラーで導入する

インストーラーが検出したOBSを確認します。OBSが複数ある場合は、普段使う32.2.1を選びます。
先へ進むと、インストーラーがOBS停止、32.2.1、空き容量、reparse、書込権限、既存fileのhashを
確認します。不合格なら理由を表示して配置前に停止します。既存の同一fileがある場合はbackupされ、
処理履歴が残ります。完了画面が出るまでPCやインストーラーを強制終了しないでください。

### Controllerを開いて保存先を決める

`BAI 学習データ録音コントローラ`を開きます。Plugin導入後はOBSを起動したままで構いません。
Controllerは選択したOBS 32.2.1の実行fileとprocess IDを照合し、別のOBSが動いている場合は停止します。
`保存先`の`参照...`を押し、空き容量が十分なフォルダーを選びます。保存先は録音のたびに変更
できます。続けて`最大録音時間`（1〜120分）と`停止する空き容量`を設定します。初めて試す時は、
短い最大時間にしてください。

### 録音前にGAINを確認する

OBSを起動したまま`録音前GAINチェック（5秒・保存なし）`を押し、案内された音量で発声します。この確認では
音声fileを保存せず、Peak、RMS、clippingだけを測定します。Pluginは物理GAIN、+48V、PAD、
HPFやOBS設定を自動変更しません。

画面のGAINバーはPeakとRMSをリアルタイム表示し、clipping時は赤くなります。clippingが表示された場合は録音を始めず、物理GAINを少し下げてからもう一度確認します。
Quality Policyが未設定の時は、数値が表示されても自動で`適正`とは判定しません。

### 録音を開始する

`録音開始（OBS起動中でも可）`を押します。Controllerは起動中の同一OBSへ、その録音だけに使う鍵をmemory上で安全に渡します。OBSがまだ起動していない場合だけControllerが起動します。
赤い`● 学習データ録音中`が表示されたことを必ず確認してから話してください。画面には経過時間、
保存量、保存先の空き容量、packet gap、認証失敗が表示されます。赤い表示がなければ録音中ではありません。

### 一時停止して再開する

話を中断する時は`一時停止`を押します。橙色の一時停止表示中はWAVへ追記せず、Pluginも音声copyを
停止します。OBSは終了しません。再び話す時は`再開`を押し、同じOBS processのまま赤い録音中表示へ戻ったことを確認してから続けます。

### 録音を停止してfileを確認する

終了時は`録音停止`を押します。`.partial.wav`が確定した`.wav`へ変わり、同名の
`.receipt.json`が作られるまで待ちます。保存先で両方を確認した後、OBSを通常終了します。
録音したWAVはDatasetやTrainingへ自動採用されません。採用、削除、公開は別のOwner確認で行います。

途中で困った場合は、まず`録音停止`を押し、Controllerに表示された停止理由を控えます。電源断、
file削除、上書きインストール、自動rollbackを先に行わず、[困ったとき](#困ったとき)を参照してください。

## Beginner guide (English)

### What this guide covers

This is not a fixed ten-step checklist to memorize. Read this section from top to bottom to install the Plugin, select a destination and safety limits, check gain,
record, pause, resume, stop, and verify the saved files. The current dev.10 build is a public Technical Preview.
Download `bai-voice-capture-0.1.0-dev.10-installer.1-windows-x64-setup.exe` from the
[official Release](https://github.com/baisound/bai_video_production/releases/tag/obs-voice-capture-v0.1.0-dev.10-installer.1).
It is not code-signed and must not be presented as a Production installer or the stable BAI Video Production release.

### Prepare the computer

Use 64-bit Windows 10/11 and 64-bit OBS Studio 32.2.1. Finish any stream or recording, save your work, and exit
OBS normally. Download only from the official Release and verify its version and SHA-256. The current Technical
Preview is unsigned, so Publisher information may be absent and Windows may show a warning. Do not run a copy
obtained from another site, a repost, or an email attachment. Stop when the file or security prompt is unexpected.

### Install the Plugin

Confirm the OBS installation detected by the installer. When several copies exist, select the 32.2.1 instance
you normally use. The installer checks that OBS is closed and compatible, then checks disk space, reparse points,
write access, and existing-file hashes. It stops before placement and explains the reason when a check fails.
Matching existing files are backed up and the transaction is journaled. Wait for the standard completion page;
do not force-close OBS, the installer, or Windows during this work.

### Open the Controller and select a destination

Open **BAI Learning Voice Capture Controller**. After installation, OBS may remain open. The Controller checks
the selected OBS 32.2.1 executable and process ID and fails closed when another OBS instance is running. Select
**Browse** beside **Destination** and choose a folder with enough free space. You may change this folder for each
session. Set **Maximum recording time** (1–120 minutes) and **Stop at free-space floor**; use a short limit first.

### Check gain before recording

With OBS still open, select **Pre-recording gain check (5 seconds, no audio saved)** and speak at the requested level. The check
measures peak, RMS, and clipping while saving no audio and changing no physical gain, +48 V, PAD, HPF, or OBS
setting. The live meter shows peak and RMS and turns red when clipping is detected. Do not record while it is red;
lower the physical gain slightly and check again. Without an
approved Quality Policy, measured values are not automatically labelled “good.”

### Start recording

Select **Start recording (OBS may remain open)**. The Controller attaches to the same running OBS process with an
ephemeral in-memory key used only for that session; it starts OBS only when OBS is not already running. Speak only
after the red **● Recording learning data** banner appears. The window shows elapsed time,
saved bytes, destination free space, packet gaps, and authentication failures. No red banner means no recording.

### Pause and resume

Select **Pause** when interrupted. While the amber paused banner is visible, the WAV does not grow and the Plugin
stops copying audio. OBS remains open. Select **Resume**, confirm the same OBS process is still used, wait for the red
banner to return, and then continue speaking.

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
| Plugin version | `0.1.0-dev.10` | `PASS` |
| Local installer candidate | `0.1.0-dev.10-installer.1` / SHA-256 `5eb7b00aa3830f880c724538023c6f7b0b52a032e2c1ed880d497cdd8cce1908` | `PASS` |
| 対応architecture | `windows-x64` | `PASS` |
| Runtime package名 | `bai-voice-capture-0.1.0-dev.10-windows-x64.zip` | `PASS` |
| Runtime package bytes | `40670` | `PASS` |
| Runtime package SHA-256 | `03286e9efbf5dd5af38230dcf7fee4bf53eb3fcc7d7a6d014833b9996bc1f558` | `PASS` |
| Package manifest SHA-256 | `4958d963f9dde1c82cf9e1110ada37019e276961df9cd97135b3e73b8b84a232` | `PASS` |
| Plugin DLL bytes / SHA-256 | `24064` / `9b8a603d6515c0735f776867c7079c0600990ebebaf8b9609d81d0f0f265bcdb` | `PASS` |
| Controller bytes / SHA-256 | `37376` / `e715fd0a3eff137f405b1f8da33ba5f9232e57d7c1c4d1694069ebdba3b3fc67` | `PASS` |
| Source ZIP filename | `bai-voice-capture-0.1.0-dev.10-source.zip` | `PASS` |
| Source ZIP bytes / SHA-256 | `45715` / `0ad4c83a957b37b455b38829f842f8318116c522cb542de0a9c5849567b29e72` | `PASS` |
| Source manifest SHA-256 | `1e178f8ebf27ffcb5a0a2bb2343cbd7c76a74aaf3b98558c9189dfba112ebd66` | `PASS` |
| Plugin implementation / build / test / package | Local build Evidence確認済み | `PASS` |
| CMake 3.30.5 configure | Visual Studio 18 generator非対応。PASSへ昇格しない | `未確認` |
| Existing VS18 graphでのRelease build | Plugin DLL / core testを再compile | `PASS` |
| Core/security synthetic suites | `3 / 3 PASS` | `PASS` |
| Controller self-test | package同梱binaryでPASS | `PASS` |
| License | `GPL-2.0-or-later` | `LEGAL_REVIEW_REQUIRED` |
| GitHub Technical Preview | `obs-voice-capture-v0.1.0-dev.10-installer.1`として公開予定 | `未確認` |
| Stable Release・Production・Deploy | 未実施 | 未確認 |
| Install先layout | Exact 3-entry OBS-root relative map | `PASS` |
| Exact 3-entry install | Dev.10 installer transactionとexact read-back確認済み | `PASS` |
| Dev.10 installer fake-OBS acceptance | 実OBS稼働を正しく検出して配置前停止 | `BLOCKED_BY_RUNNING_OBS` |
| Backup | Dev.7 exact3を別transactionへ保存 | `PASS` |
| Rollback結果 | 未確認 | 未確認 |
| OBS load結果 | Dev.10 module loadと既存`MIC` filterの有効化を確認 | `PASS` |
| 録音中・一時停止中の常時表示 | Owner実機Acceptanceで両表示を確認 | `PASS` |
| 保存先・最大時間・disk floor | Controllerから変更可能 | `PASS` |
| START/PAUSE/RESUME/STOP | Owner実機Acceptanceで同一OBS PIDを維持 | `PASS` |
| Recording receipt | body-free統計をprivate Evidenceから確認。音声・保存先・filename・digestは非公開 | `PASS` |
| 録音前GAINチェック | 5秒、音声body保存0、設定変更0 | `PASS` |
| GAIN receipt | `500 packets / gap 0 / HMAC 0 / reconnect 0 / clipping 0`、音声保存なし | `PASS` |
| Owner音声 | Dev.10で開始・一時停止・再開・停止、`gap 0 / HMAC 0 / reconnect 0`を確認 | `PASS` |
| 正式RecordingSession | 未実施 | `未確認` |
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
| 1 / 3 | `obs-plugins/64bit/bai-voice-capture.dll` | `obs-plugins/64bit/bai-voice-capture.dll` | `24064` / `9b8a603d6515c0735f776867c7079c0600990ebebaf8b9609d81d0f0f265bcdb` | `PASS` |
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

この章のうち、local dev.10と合成音声sceneで確認した項目だけを`PASS`にしています。

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

Dev.10 source/build/package/installerから、公開可能なexact値だけをbindingしています。Dev.8の実機
receiptは履歴として残しますが、Dev.10のinstall/load/Owner音声結果へ流用しません。

| Field | 確定値 | Evidence |
|---|---|---|
| Module / Package ID | `bai-voice-capture` | Package receipt |
| Version | `0.1.0-dev.10` | Dev.10 Evidence receipt |
| Target | `windows-x64 / OBS 32.2.1` | Package receipt |
| Runtime filename | `bai-voice-capture-0.1.0-dev.10-windows-x64.zip` | Dev.10 Evidence receipt |
| Runtime bytes / SHA-256 | `40670` / `03286e9efbf5dd5af38230dcf7fee4bf53eb3fcc7d7a6d014833b9996bc1f558` | Dev.10 package read-back |
| Runtime manifest SHA-256 | `4958d963f9dde1c82cf9e1110ada37019e276961df9cd97135b3e73b8b84a232` | Dev.10 package read-back |
| DLL bytes / SHA-256 | `24064` / `9b8a603d6515c0735f776867c7079c0600990ebebaf8b9609d81d0f0f265bcdb` | Dev.10 build/package read-back |
| Controller bytes / SHA-256 | `37376` / `e715fd0a3eff137f405b1f8da33ba5f9232e57d7c1c4d1694069ebdba3b3fc67` | Dev.10 build/package read-back |
| Local installer candidate / SHA-256 | `0.1.0-dev.10-installer.1` / `5eb7b00aa3830f880c724538023c6f7b0b52a032e2c1ed880d497cdd8cce1908` | Local technical installer read-back |
| Source artifact filename | `bai-voice-capture-0.1.0-dev.10-source.zip` | Dev.10 Evidence receipt |
| Source artifact bytes / SHA-256 | `45715` / `0ad4c83a957b37b455b38829f842f8318116c522cb542de0a9c5849567b29e72` | Dev.10 package read-back |
| Source manifest SHA-256 | `1e178f8ebf27ffcb5a0a2bb2343cbd7c76a74aaf3b98558c9189dfba112ebd66` | Dev.10 package read-back |
| Build/test | Existing VS18 graph Release build PASS / core-security 3 suites PASS / controller self-test PASS | Dev.10 local Evidence |
| Configure limitation | CMake 3.30.5はVisual Studio 18 generatorを認識しないためPASSを主張しない | Fail-closed Evidence |
| License | `GPL-2.0-or-later` | `LEGAL_REVIEW_REQUIRED` |
| Public Technical Preview Release | `obs-voice-capture-v0.1.0-dev.10-installer.1` | 公開後read-back必須 |
| Stable Release / Production / Deploy | 未実施 | 未確認 |
| Dev.8 install/load/gain receipts | 履歴Evidenceとして保持 | Dev.10 PASSへ流用しない |
| Dev.10 install/load/control/gain receipt | exact install、module load、GAIN、同一OBS PIDを確認 | Local technical Acceptance |
| Dev.10 Owner voice technical receipt | 開始・一時停止・再開・停止を確認。音声・保存先・digestは非公開 | Local technical Acceptance |
| Production Recording receipt | 未実施 | 未確認 |

値はcanonical成果物とreceiptから転記しています。Runtime filename、family名、
チャット文だけを根拠に別の値へ置き換えません。合成音声local acceptanceの`PASS`をOwner音声、
正式RecordingSession、Dataset、Training、Production、stable ReleaseまたはDeployの`PASS`へ昇格しません。

## 困ったとき

- PackageやSHAが不明: 導入しない
- 既存fileとのcollisionを検出: 上書きせず停止する
- OBSが起動中: 導入・復元を開始しない
- 導入結果が不明: retryや自動rollbackを行わずread/reconcileする
- Source、Profile、Scene、deviceが変わった: 録音を止めfresh preflightを行う
- 音声欠損、drop、overrunが不明: `0`にせず`UNKNOWN`として隔離する
- Stagingが残った: 自動削除・Asset化・Dataset採用を行わない
- Public Evidenceにprivate情報が疑われる: 公開せずSecurity/Privacy reviewへ送る

この公開ガイドとTechnical Previewの存在は、Owner音声の正式録音、Dataset採用、Training、
Production利用、stable ReleaseまたはDeployを自動で許可するものではありません。
