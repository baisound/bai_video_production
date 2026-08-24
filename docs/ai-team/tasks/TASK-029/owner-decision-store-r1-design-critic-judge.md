# TASK-029 R1 Encrypted Owner Decision Store Design / Critic / Judge

Date: 2026-08-24

Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY

Status: IMPLEMENTED_LOCAL / HOSTING_PENDING

## Atomic Unit

R1はR0の`READY_FOR_HUMAN_REVIEW` Candidateに対する明示Human `ADOPTED` / `REJECTED`を、Owner-local encrypted append-only chainへ保存する。Windows本番既定暗号はOSのCurrent User DPAPIであり、鍵値を受け取らずdiskへ保存しない。

## Boundaries

- disk envelopeはcipher suite、ciphertext、ciphertext hash、document hashだけを保持し、Owner scope、Candidate、理由コードを平文にしない。
- CandidateはR0 canonical hashと`READY_FOR_HUMAN_REVIEW`を再検証する。
- decision/candidate replay、chain gap/fork、scope mismatch、stale revisionを拒否する。
- cross-process lock、temp fsync、validate-before-replace、atomic replaceを使用する。
- wrong key、ciphertext/outer/inner tamper、symlink、partial writeをfail closedにする。
- Profile write、Knowledge Pack promotion、Cloud telemetry、rollback、plaintext export、physical delete、Timeline/Resolve、external effectはfalseであり、TASK-017 retention/purge責任を侵食しない。

## Cryptographic decision

独自暗号を実装しない。Product既定はWindows DPAPI `CryptProtectData` / `CryptUnprotectData`、Current User scope、UI禁止、TASK-029 domain entropyを使用する。cipher port注入はCIと将来の正規platform portのためであり、呼出側が平文storeへfallbackすることを許可しない。非Windowsで既定cipherを要求した場合は`ERR_OWNER_DECISION_ENCRYPTION_UNAVAILABLE`で停止する。

## Critic

- Finding: clear envelopeのrevision/owner hashが相関情報を漏らす。Correction: revisionを含むhistory全体を暗号化し、clear envelopeを暗号metadataだけに限定。
- Finding: encrypted blobを入れ替えてもouter hashを再計算できる。Correction: DPAPI authenticationに加え、復号後のCandidate、entry chain、history hashを全層再検証。
- Finding:Human採用がProfile自動反映へ誤用される。Correction: persistenceのみをtrueとし、Profile/Pack/Cloud/rollback/effect authorityは全層false。
- Finding:物理deleteをTASK-029が実装するとTASK-017責任と競合する。Correction:R1はdelete authorityをfalseに固定し、retention/purgeを実装しない。

Residual Critical/High: 0 / 0

## Tester / Judge

- encrypted restart round-trip and no plaintext markers: PASS
- ADOPT/REJECT chain and CAS: PASS
- scope/replay/non-ready rejection: PASS
- envelope/inner/wrong-key/symlink tamper: PASS
- atomic failure preserves prior bytes: PASS
- R0 regression and schema mirror: PASS
- focused R0/R1: 27 PASS
- implementation authority: OWNER_DIRECTED_IMPLEMENTATION_2026_08_24
- local technical gate: PASS
- hosted integration: PENDING

## Deferred Units

- Owner-wide Profile materialization and explicit version adoption
- TASK-019 Profile Tuning Proposal bridge
- signed Knowledge Pack promotion/rollback
- TASK-017-governed retention, purge, recovery/export workflow
- optional Cloud consent/anonymization/withdrawal
