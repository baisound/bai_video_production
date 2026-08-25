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
