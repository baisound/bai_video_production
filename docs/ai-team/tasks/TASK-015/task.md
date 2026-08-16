# TASK-015 YouTube Feedback

- Status: `R0 FOUNDATION IMPLEMENTED / HOSTING PENDING`
- Owner: 開発担当
- Dependency: TASK-008 Multimodal Scoring、canonical publication/render receipts
- Downstream: TASK-019 Profile Auto-Tuner、Human-reviewed scoring/profile refinement

## R0 scope

R0は、すでに取得済みのYouTube公開集計値をcredential-freeなin-memory rowとして受け取り、公開動画・channel identity digest・Asset/Edit Plan/render receipt・TASK-008 scoring manifest・analytics windowへexact bindする決定的なFeedback Snapshot contractである。

Metricはclosed enumとunit/rangeを持ち、profileがrequired/optional集合を明示する。欠落、UNKNOWN、STALE/REVOKEDは別状態でfail closedし、canonical JSON/SHAを生成する。整数・fixed-pointだけを使用し、float由来の非決定性を持ち込まない。

## Boundaries

- 個人単位の視聴者行、contact、private account、credential/tokenを受け取らない。
- YouTube API、network、filesystem、media、provider、subprocessを実行しない。
- Platform video IDやdigestはpublication/current-valid Evidenceの代替ではない。
- 出力はHuman review用のadvisory Evidenceのみ。TASK-019 tuning、TASK-008 profile変更、Edit Plan/Timeline、再公開を自動化しない。
- 実analytics acquisition、credential consent、Human decision、Release/Deploy/Productionは別Gate。

## Verification

- deterministic canonical snapshot/hash and schema mirror
- exact TASK-008 scoring-manifest coordinate
- metric/unit/range/profile/window/cap closure
- missing/UNKNOWN/stale/revoked/tamper negative matrix
- privacy/no-effect import and API surface
- Critic/Judge residual C/H/M=`0/0/0`
