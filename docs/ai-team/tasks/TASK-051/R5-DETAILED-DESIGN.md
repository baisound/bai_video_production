# TASK-051 R5 — Trivia Candidate / Registered-data Management

Governance: `DEV-3 HIGH ASSURANCE`

## UI structure
`実況・豆知識を登録` is split into:
1. `手動で登録`
2. `動画から候補を作る`
3. `登録済み・候補一覧`

## Candidate mining
- reuses the shared R2 12-button transport for video inspection;
- FasterWhisper settings are Japanese-labelled while internal values remain unchanged;
- mined data remains `CANDIDATE`;
- source video/transcript segment time is stored in an additive operational sidecar.

## Human review
The list shows state, title, body, related game elements, event/scenes, source video/ref and time.
Actions:
- detail/edit;
- verify/formally register;
- duplicate;
- reject;
- delete from active use while preserving append-only revision history.

## Edit safety
Editing writes a new revision. An edited VERIFIED item becomes CANDIDATE unless Human explicitly
selects `確認済みとして登録`.

No historical trivia revision is physically deleted.
