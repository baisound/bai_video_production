# TASK-054 R5E Operation Progress / Recovery Design

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `IMPLEMENTED / COMMIT_READY`

## Responsibility

R5E owns an immutable presentation contract and accessible Japanese panel for long-running TASK-054 operations. It does not own worker execution, persistence or canonical transition authority; R5F is the lifecycle owner. UI requests carry exact `operation_id + state_revision`, so an application service can reject stale cancel/recovery clicks.

## Presentation states

`QUEUED / RUNNING / CHECKPOINTING / CANCELLING / COMPLETED / FAILED / CANCELLED / RECOVERY_REQUIRED`

Each snapshot contains bounded phase/current/total/elapsed/estimated-remaining and an optional opaque verified-checkpoint reference. Progress is 0..1000. QUEUED must be zero; COMPLETED must equal total; terminal stages cannot retain a stale remaining estimate.

`安全にキャンセル` is available only for QUEUED/RUNNING/CHECKPOINTING. CANCELLING disables repeat requests. `検証済みCheckpointから再開計画を作る` is available only for RECOVERY_REQUIRED with a valid checkpoint reference. It creates a plan request; it does not resume, download, train or dispatch by itself.

## Failure panel

FAILED and RECOVERY_REQUIRED require one validated failure view containing:

1. 何が起きたか
2. データは安全か
3. 何が保存されたか
4. 次にできる安全な操作
5. 再試行で費用/外部送信が発生するか

The main text is Japanese with stable `ERR_TASK054_*`; bounded `技術詳細` rejects common credential/secret material. No automatic retry exists.

## Operator flow and accessibility

The panel keeps status, phase, deterministic progress, elapsed and remaining estimate visible. Buttons have explicit severity-specific labels. Cancel requires a visible confirmation explaining that stopping occurs at a safe boundary and verified checkpoints are retained. Recovery has a separate explicit action. Normal UI does not display credential values.

## Fail-closed invariants

- invalid identity/revision/stage/counter/estimate: reject snapshot
- failure details absent or present in the wrong state: reject snapshot
- forged failure object: reject snapshot
- RECOVERY_REQUIRED without checkpoint: reject snapshot
- COMPLETED with incomplete progress: reject snapshot
- execution-authority field mutation: reject snapshot
- secret-like technical detail: reject snapshot

## Verification

Focused tests cover running progress, repeat-cancel blocking, recovery/checkpoint coupling, terminal counter/estimate rules, failure-stage coupling and forgery, secret rejection, fixed no-authority and required Japanese/stale-safe UI wiring.

## Preserved gates

R5E sends no cancel/resume to a real worker during tests and grants no execution authority. Model/runtime acquisition, actual Dataset intake/adoption, training, Provider inference, paid/external retry, promotion, TTS, Timeline/Resolve mutation, Product Activation, release and deploy remain Human-Gated.
