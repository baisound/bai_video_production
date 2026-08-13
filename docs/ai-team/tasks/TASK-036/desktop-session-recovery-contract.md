# TASK-036 — Desktop Session Recovery / Checkpoint Contract Ver.1.0

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`
- Persistence: local crash-safe JSON checkpoint
- External mutation state restoration: explicitly out of scope

## 1. Objective

Allow `BAI Video Production.exe` to close and reopen without losing the canonical minimum-editing workflow identities already completed by the operator.

The checkpoint persists identity/state only. It does not duplicate source media, render bytes, secret values or one-shot authorization tokens.

## 2. Persisted state

- Product version;
- Project ID / display name;
- selected Asset ID;
- optional Resolve Project/Timeline presentation pointers;
- current Workspace;
- TASK-036 EditingSessionState identities and revision;
- next recommended action;
- deterministic checkpoint checksum.

## 3. Never persisted

- one-shot confirmation tokens;
- active background job objects;
- arbitrary host paths;
- Provider credentials;
- media bytes;
- external application “assumed running” state.

## 4. Quiescent checkpoint rule

A durable desktop checkpoint is refused while Shell background jobs are active.

This prevents restart from silently guessing whether ASR/render/external mutations completed. Worker-specific resumability remains owned by the corresponding TASK implementation.

## 5. Crash safety / stale writer protection

- Atomic JSON replace through existing `AtomicJsonWriter`;
- SHA-256 integrity check;
- regular non-symlink file requirement;
- bounded file size;
- existing checkpoint replacement requires exact compare-and-swap checksum;
- stale writers fail closed;
- Shell selected Asset must exactly match EditingSessionState source Asset.

## 6. Recovery

On reopen:

1. verify UTF-8 JSON + checksum;
2. verify security boundary flags;
3. reconstruct EditingSessionState;
4. create a fresh Shell service;
5. rebind Project/selected Asset/workspace;
6. restore stage-aware command policy;
7. **do not restore old confirmation tokens**;
8. **do not claim old background jobs are still running**.

## 7. Automated acceptance

Covered by `tests/test_task036_desktop_session_store.py`.

Status: `AUTOMATED_VALIDATED`.
