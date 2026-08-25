# TASK-029 R9A Cryptography Development Dependency Installation Runbook

Date: 2026-08-26

## Purpose

TASK-029 R9AのEd25519 detached signature verificationを開発・テストするため、Python公式cryptography packageを開発環境へ追加する。秘密鍵、実Knowledge Pack、Provider、network upload、Release/Deployは扱わない。

## Approved package range

- Project constraint: cryptography version 46以上51未満
- Installed development version observed: 50.0.0
- Python observed: 3.12
- Source: Python Package Index
- License: Apache-2.0 OR BSD-3-Clause

## Installation

PowerShell command:

    python -m pip install "cryptography>=46,<51"

## Verification

    python -c "import cryptography; print(cryptography.__version__)"
    python -m pytest -q tests/test_task029_knowledge_pack_signature_verification.py tests/test_task029_knowledge_pack_signature_request.py

Expected: import成功、versionが46以上51未満、R8/R9 focused tests PASS。

## Optional Owner key creation with PuTTYgen

PuTTYgenはEd25519鍵を作成できる。ただし、この手順で作るSSH公開鍵または暗号化PPKは、R9Aの入力形式ではない。R9Aは鍵生成・PPK読取・秘密鍵保管を実装せず、検証時にはraw 32-byte Ed25519 public keyを必要とする。R9B以降で検証済みconverter/loaderとOwner鍵保管境界が用意されるまでは、作成した鍵をBVPへ登録・変換・使用しない。

PuTTY公式manual:

- https://www.puttyssh.org/0.83/htmldoc/Chapter8.html
- https://www.puttyssh.org/0.80/htmldoc/AppendixC.html

### GUI procedure

1. 公式配布元から入手済みの最新PuTTYgenを起動する。この文書はPuTTYのdownload/installを実行・承認しない。
2. `Parameters`で鍵種別を`EdDSA`、curveを`Ed25519`にする。`RSA`、`ECDSA`、`Ed448`は選ばない。
3. 鍵サイズ欄が表示される版では`255`を指定する。旧版で`256`のみ受け付ける場合も生成される鍵はEd25519だが、可能なら現行版を使う。
4. `Generate`を押し、画面の指示に従って空白領域上でマウスを動かす。
5. `Key comment`へ用途と日付を入れる。例: `BVP-TASK029-KNOWLEDGE-PACK-SIGNER-YYYYMMDD`
6. `Key passphrase`と`Confirm passphrase`へ、他用途で使っていない十分に強いpassphraseを入力する。
7. `Save private key`で、passphrase保護された`.ppk`をOwner専用のローカル保管場所へ保存する。repository、project/media directory、共有folder、同期cloud、添付、chatには保存しない。
8. 上部の`Public key for pasting into OpenSSH authorized_keys file`を公開鍵として別途保存するか、`Save public key`を使う。公開鍵だけを扱い、private key textをcopyしない。
9. 生成直後に秘密鍵の保存場所、Owner、用途、作成日を秘密値なしで記録する。passphraseそのもの、private key、seedは記録しない。

### Format and integration boundary

- `.ppk`はPuTTY private-key containerであり、BVP R9Aへ直接渡さない。
- OpenSSH形式の公開鍵文字列も、そのままではR9Aが要求するraw 32-byte public keyではない。
- 将来のR9B converter/loaderは、公開鍵からraw 32 bytesを厳密に抽出し、鍵種別と長さを検証し、`signer_key_id_sha256 = SHA-256(raw 32-byte public key)`を計算する必要がある。
- `Conversions > Export OpenSSH key`などによるprivate-key変換は、秘密鍵の露出面を増やすため通常は行わない。実行には別のOwner承認、専用手順、出力先検証、回収手順が必要。
- `.ppk`をpassphraseなしで保存しない。passphraseをprivate keyと同じ場所へ保存しない。
- private key、passphrase、seedをCodex、ChatGPT、Git、issue、PR、CI log、test fixture、手順書へ貼り付けない。
- 紛失または漏えいの疑いがある鍵は使用せず、revoke/replace対象として扱う。
- 必要な場合は暗号化済みoffline backupを1つだけ作り、Owner管理下で本体と別の安全な場所へ保管する。

### Execution state

この追記はPuTTYgenを使用可能な選択肢として説明するだけである。

- PuTTY/PuTTYgen installation: NOT EXECUTED
- Owner key generation: NOT EXECUTED
- PPK creation/import/conversion: NOT EXECUTED
- passphrase entry or custody: NOT EXECUTED
- BVP key registration: NOT EXECUTED
- real signing/verification: NOT EXECUTED

## Removal / recovery

R9A専用開発環境からpackageを除去する必要がある場合のみ、依存利用者がないことを確認して実行する。

    python -m pip uninstall cryptography

Project dependencyを残したまま除去するとR9A importはfail closedする。Production環境、別Python環境、OS certificate store、Windows machine-wide settingsは変更しない。

## Safety boundary

- private key generation: NOT EXECUTED
- private key storage: NOT EXECUTED
- real signature: NOT EXECUTED
- real Knowledge Pack verification: NOT EXECUTED
- key store access: NOT EXECUTED
- Release/Deploy/Production: NOT AUTHORIZED
