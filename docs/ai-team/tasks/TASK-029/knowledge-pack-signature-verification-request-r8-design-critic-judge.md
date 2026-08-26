# TASK-029 R8 Knowledge Pack Signature Verification Request

Status: `LOCAL_VERIFIED_PENDING_HOSTED_INTEGRATION`

## 1. Atomic Unit

TASK-029 R8は、R7 Knowledge Pack Signing Candidateを外部の暗号検証境界へ安全に渡すための、本文を含まない決定的な依頼レコードを定義する。

DEV profile: `DEV-4 FOUNDATION CRITICAL`

このUnitが行うこと:

- R7 signing candidateを同じcompile inputsから再生成し、完全一致を確認する。
- Pack、predecessor、signing candidate、trusted signer policy、signer key ID、署名アルゴリズムを一つのcanonical message hashへ束縛する。
- 外部暗号検証が必要であることを明示する。

このUnitが行わないこと:

- signature bytes、public key、private key、credential本文の受領・保存・生成。
- key store、filesystem、network、provider、Resolve、native runtimeへのアクセス。
- 暗号署名または暗号検証の実行、成功主張。
- Knowledge Pack書込み、昇格、runtime apply、rollback、release、deploy。

## 2. Contract

入力はR7 signing candidate payloadと、そのcandidateを再生成できるexact compile kwargs、trusted signer policy SHA-256、signer key ID SHA-256、許可済み署名アルゴリズムである。

R8は次をfail-closedで要求する。

1. R7 candidateをexact inputsから再compileできること。
2. 提示されたR7 payloadと再compile結果が完全一致すること。
3. R7 stateが`READY_FOR_EXTERNAL_SIGNATURE`であること。
4. policy IDとkey IDは64文字のlowercase SHA-256であること。
5. algorithmはallowlistの`ED25519`であること。

出力stateは`READY_FOR_EXTERNAL_CRYPTOGRAPHIC_VERIFICATION`のみである。`signature_present`と`signature_verified`は常にfalseで、request生成をverification receiptとして扱うことを禁止する。

## 3. Canonical Signature Message

canonical message contractは`TASK-029/KNOWLEDGE_PACK/EXTERNAL_SIGNATURE_MESSAGE/1.0.0`である。message hashは少なくとも次を束縛する。

- signing candidate ID / SHA-256
- pack ID / version
- predecessor pack SHA-256
- trusted signer policy SHA-256
- signer key ID SHA-256
- signature algorithm

これにより、Pack、信頼ポリシー、鍵identity、algorithmの差替えは異なるmessage hashとなる。

外部署名・検証実装が扱うexact bytesは、`TASK-029/KNOWLEDGE_PACK/SIGNATURE_INPUT/SHA256-PREFIXED-ASCII/1.0.0`に従い、`sha256:`接頭辞を含む`signature_message_sha256`値そのもののASCII bytesとする。signature bytesはdetached inputであり、R8 requestには含めない。

## 4. Critic Review

### Finding C1: requestがverification receiptと誤認される

Severity: High

Resolution: 専用request型とrequest-only stateを使用し、`signature_present=false`、`signature_verified=false`、`external_cryptographic_verification_required=true`をschema constで固定した。

### Finding C2: hash-only signer metadataがtrust proofと誤認される

Severity: High

Resolution: policy/keyはidentity bindingに限定した。実鍵、署名本文、trust resolution、暗号検証は外部Human Gate配下であり、本UnitはPASS authorityを生成しない。

### Finding C3: signed messageの対象が曖昧になる

Severity: High

Resolution: versioned message contractとcanonical SHA-256を定義し、R7 candidate・Pack lineage・policy・key ID・algorithmを同じmessageへ束縛した。さらにversioned input contractで、`sha256:`接頭辞込みのhash文字列のASCII bytesをexact署名対象として固定した。

Unresolved Critical: `0`

Unresolved High: `0`

## 5. Tester Responsibility

必要な検証:

- deterministic compile / round-trip / schema validation
- R7 exact recompileとdrift拒否
- non-ready R7 source拒否
- algorithm allowlist拒否
- immutable record
- canonical schemaとpackage mirrorのbyte exact一致
- filesystem/network/subprocess/crypto library import不在
- TASK-019/TASK-029 targeted regression
- full repository regression

実行結果:

- focused: `5 PASS`
- TASK-019/029 direct regression: `91 PASS`
- full Product regression: `3797 PASS / 6 SKIP / 0 FAIL`

## 6. Judge Decision

Current decision: `ACCEPTED_LOCAL_PENDING_HOSTED_INTEGRATION`

R8は外部暗号処理を実装せず、R7から将来の署名検証へ渡すfail-closedな依頼境界だけを追加する。focused、targeted、full regressionとscope reviewはPASSした。Hosted integrationはR8専用CHANGELOG lockを取得し、既存lockを再利用しない。実署名・暗号検証・Pack writeは引き続き未許可である。
