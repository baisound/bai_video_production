# TASK-054 R5C Model Status / Execute / Review Panel Design

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `IMPLEMENTED / LOCAL EVIDENCE`

## Atomic Unit

Project the existing tuned-model Registry and R3B Route decision into a
Japanese Operator panel with explicit preflight, execute and review states.

## Canonical boundary

- R3A remains owner of immutable Binding lifecycle and latest-state resolution.
- R3B remains owner of connection-profile Route capability and binding pinning.
- R5C is a read-only view/application projection. It does not persist another
  model registry, choose a hidden fallback or hold credentials/settings.
- Every current R3B decision is `NOT_AUTHORIZED_R3D_REQUIRED`. R5C therefore
  fixes execution disabled and cannot be forged to enable it.
- R3D must introduce a separate execution-authority contract before any execute
  callback may be connected. Preflight success is never execution approval.

## Operator behavior

The panel shows display identity/revision, role, lifecycle state, Japanese
support, JSON compatibility, GPU status, rights Evidence and evaluation
Evidence. GPU remains `未確認` because Registry data does not prove runtime
capacity. No inferred hardware claim is shown.

Primary controls are unambiguous:

- `事前チェック` resolves current Registry/Profile/availability state;
- `現在の実況・解説を確認` remains disabled without R3D authority;
- `生成結果をレビュー` is enabled only when a pending-review count is positive;
- `詳細を見る` explains route identity and the execution block.

No generic `Use` button exists. Failure states distinguish no approved model,
unavailable route and invalid configuration with stable codes and Japanese next
actions.

## Safety and acceptance

- revoked/suspended/unapproved or ambiguous Bindings remain unavailable through
  existing R3A resolution;
- missing capability, unavailable route or binding-pin mismatch cannot fallback;
- preflight success retains `R3D_EXECUTION_AUTHORITY_REQUIRED`;
- row/status/review/execution flags have constructor invariants;
- GPU, execution and review availability cannot be invented by UI data;
- R5C/R3B/R5B focused tests and targeted regression pass;
- no Provider call, model load, Dataset/training, TTS, Timeline or Resolve write
  occurs.
