# TASK-025 Premiere FCP7 XML Adapter Spike

- Status: `R0 FOUNDATION IMPLEMENTED / HOSTING PENDING`
- Owner: 開発担当
- Dependency: TASK-001 Adapter boundary、TASK-022 Timeline Mapping Service
- Next Gate: Golden Fixture import in an explicitly selected Premiere environment

## R0 scope

R0は、canonical TASK-022 `TimelineMappingPlan`、closed FCP7 sequence profile、exact Asset/SHA/private file URI bindingを入力にし、FCP7 `xmeml` v5 bytesとpublic-safe package receiptを決定的に生成するno-effect adapterである。

24/23.976/25/30/29.97/50/60/59.94のclosed frame-rate matrix、end-exclusive source/timeline frame、gap、単一video track、1x playbackをexactに扱う。R0で未対応のretime、non-zero origin、rate mismatchはfail closedする。

## Boundaries

- media URIはprivate input。public receiptにはSHA-256だけを記録する。
- Media/filesystemを読まず、XML fileを書かず、Premiereを起動・import・操作しない。
- XML生成成功はPremiere import互換性やAsset/Timeline mutationのEvidenceではない。
- Audio/subtitle/multitrack/retime、actual file materialization、Golden Fixture import、Human review、Release/Deployは別Gate。

## Verification

- exact golden xmeml bytes and deterministic SHA
- TASK-022 plan/rate/range/gap reuse
- closed frame-rate matrix and private URI validation
- missing/extra Asset, rate, duration, origin, retime, traversal negative matrix
- schema mirror/public receipt privacy/no-effect surface
- Critic/Judge residual C/H/M=`0/0/0`
