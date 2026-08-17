# Changelog

??Project?Semantic Versioning????????????????????Git Tag?Commit log??????????

## [Unreleased]

- TASK-036 P-UX-2D3として、typed Final Review承認をProject単位のappend-only/CAS履歴へ永続化し、同一readinessの二重承認、確認後のstale化、改ざん、上限超過をfail-closedにするno-effect applicationを追加しました。Shell承認操作、Audio receipt生成、Export Job作成、dispatch、render、公開、Native H3、Release/Deployは別Gateです。
- TASK-046 P-VS-4B Gate 4 R0として、承認済み合成テストWAVだけをcontained root内で検査し、48 kHz・24-bit monoのstyle Cueを決定論的な順序と休止sampleでMaster候補へ結合する限定runtime adapter、body-free receipt、schema mirror、改ざん・symlink・既存出力のfail-closed検証を追加しました。Owner音声、Dataset採用、学習、Model推論、音質・style合格判定、Asset採用、公開、Release/Deployは別Gateです。
- TASK-036 P-UX-2D2として、P-UX-2D1のexact ready状態・全Product source・privacy/rights/resource/edit/開発担当2所有Audio完了Gateを束縛するtyped Human Final Review approval receiptを追加し、TASK-044 Export preparationへ必須bindしました。Export Job作成、dispatch、render、公開、Audio変更、Native H3、Release/Deployは別Gateです。
- TASK-046 P-VS-4Bとして、OBS録音からDataset・Training・承認済みModelを経て、同一話者/Model系譜の複数style Cueを順序付きで束縛し、48 kHz・24-bit monoの自然なMaster WAV候補へ接続するbody-free application-service契約を追加しました。Dataset採用、Job dispatch、学習・推論、音声render/assembly、Asset採用、公開、Release/Deployは別Gateです。
- TASK-036 P-UX-2D1として、Production・Audit・Visual Handoff・編集Timeline・Export Queueと、privacy・rights/license・resource・edit persistence・開発担当2所有のAudio完了receiptをexactに突合するread-only Final Review readinessを追加しました。最終承認、Export Job作成、render、公開、Audio変更、Native H3、Release/Deployは別Gateです。
- TASK-046 P-VS-4Aとして、body-freeなTraining Run、held-out EvaluationInputSnapshot、mode別Engine・Resource admission、Durable Job・checkpoint・GPU process reconciliation、full・adapter・merged ModelArtifact、ModelCandidate・Evaluation・Owner approvalのfail-closed契約を追加しました。Job作成、資源予約、学習・推論、artifact・merge、VoiceProfile・Production・Publication effectは別Gateです。
- TASK-036 P-UX-2C1として、既存のShot Feasibility・Prompt・Generation Queue・local execution・output adoption・Human Asset状態をScene/Visual Slot単位でfail-closedに突合するread-only handoffをImage/Video画面へ追加しました。Audioは開発担当2へ委譲し、Provider実行、Human判断、Asset/Timeline変更、Native H3、Release/Deployは別Gateです。
- TASK-036 P-UX-2B3として、現行Human GO済みTASK-027 Scene台帳をApproved Plan・Proposal・Blueprint・全Scene順序のexact hashへ束縛するappend-only確定receiptと、再改訂時のfresh GO/再確定Gateを追加しました。Scene追加/削除、実media・detector・Provider実行、Audio、Timeline/Resolve変更、Release/Deployは別Gateです。
- TASK-046 P-VS-3Bとして、body-freeなVoiceDatasetStore、CommitIntent→Revision→Receipt→Envelope DAG、初回/通常のcombined CAS、TrainingInputSnapshot、authoritative read-backのUNKNOWN/CORRUPT分類とcurrent canonical ancestor inclusion検証を追加しました。Dataset・Asset・store・Job・Training・Model effectは別Gateです。
- TASK-036 P-UX-2B2として、既存TASK-027 BlueprintのScene順序・IDと参照・Audio・FrameIntentを保持し、視覚・frame項目だけをHuman確認付きでappend-only改訂できるようにしました。Scene追加/削除、Timeline確定、Provider・生成・Resolve、Release/Deployは別Gateです。
- TASK-036 P-UX-2B1として、既存TASK-027 Proposalのsection見出し・本文だけをHuman確認付きでappend-only改訂し、Intent・Blueprint・Provider Policy・cost・rightsを保持したまま新しいGOを必須にするPlanning操作を追加しました。AI Proposal生成、Provider・課金・Budget予約、Production/Timeline/Resolve変更、Release/Deployは開始しません。
- TASK-036 P-UX-2A1として、既存TASK-028 Connection SettingsとTASK-040/042のScene・Quick正本から、Planning・Image・Video・QuickのProvider/Model選択を秘密非表示で決定論的に投影し、Project既定Routeを既存CASへ保存できるようにしました。Audioは開発担当2へ委譲し、権利/license・resourceはUNKNOWN、Provider実行・課金・生成は未許可のままです。
- TASK-036 P-UX-2A0として、V6.1.1 mock/runtimeのfield・select・card・list・tab・state・resultを含む決定論的な要素/選択契約inventory、既存ownerへのpage/service registry、cross-screen identityとfail-closed lifecycleを追加しました。Provider・Credential・課金・model取得/実行・media・Human決定・Timeline・Export・Release/Deployは開始しません。
- TASK-041 Audio Workspace Media Review / Handoff Foundation R0として、body-free音声source・試聴/波形capability・外部receipt・独立した音声/映像Human判断・非破壊派生Asset proposal・TASK-035 REAPER往復状態の決定論的契約を追加しました。音声読取・再生・波形生成・media処理・Asset登録・配置変更・DAW操作・Release/Deployは別Gateです。
- TASK-036 P-UX-2Aとして、既存TASK-028 Connection Settings正本をUnified DesktopのAIモデル設定へ接続し、workload modeと優先RouteをCAS保存できるようにしました。Secret本文・Catalog・endpoint・Provider実行・課金・生成・TASK-041音声・Release/Deployは変更しません。
- Added TASK-025 Premiere FCP7 XML Adapter R0 as a deterministic, video-only `xmeml` v5 compiler over exact TASK-022 Timeline Mapping plans, with a closed frame-rate matrix, strict private media-URI binding and public digest-only receipts. Media/file access, XML persistence, Premiere launch/import, audio/subtitle/retime, Asset/Timeline mutation, Release and Deploy remain separate.
- TASK-017 Storage Lifecycle / GC Foundation R0として、既存Asset保持区分を参照するbody-free保持policy、外部inventory観測、archive/delete提案、one-shot Human effect authorization、外部effect receipt bindingと公開projectionを追加しました。filesystem列挙、Asset/Job/Privacy正本変更、archive/delete実行、成功receipt発行、Release/Deploy/Productionは別Gateです。
- Added TASK-019 Profile Auto-Tuner as a deterministic, no-effect tuning-proposal contract over exact TASK-008 profiles and TASK-015 aggregate feedback, with bounded weight deltas, current-valid holdout evaluation, regression/UNKNOWN/stale gates and an immutable rollback coordinate. Profile writes, automatic promotion or rollback, Edit Plan mutation, YouTube API/Credential access, Release and Deploy remain separate.
- Added TASK-015 YouTube Feedback as a credential-free, deterministic aggregate analytics contract bound to exact publication/render and TASK-008 scoring receipts, with typed fixed-point metrics and fail-closed missing, UNKNOWN, stale and revoked states. Audience-level data, YouTube API/network access, automatic profile tuning, Edit Plan/publication mutation, Release and Deploy remain separate.
- TASK-014 Local Primary Narration Render Admission R0として、既存preflightをexact script・VoiceProfile・Resource・Durable Job・private staging・one-shot Owner Gateへbody-freeで束縛し、route/usage/expiry/idempotencyをfail-closed判定する実行前契約を追加しました。model取得・load、GPU予約、Job dispatch、audio render、48 kHz WAV保存、Asset公開、Release/Deployは別Gateです。
- TASK-009 DBDProfilePlugin R0として、TASK-008のcanonical FeatureRule/ScoringProfileを再利用し、DBDのHUD・chase・event taxonomyをclosed mappingとexact rule projectionで束縛するno-effect profile snapshot契約を追加しました。実media/HUD/OCR検出、game process、feature producer、Provider、Human decision、Edit Plan/Timeline変更、Release/Deployは別Gateです。
- TASK-018 Smart Reframe R0として、TASK-007のexact Edit Plan/keep rangesとTASK-005/008/Human Reviewのcurrent-valid行Evidenceを束縛し、source-contained・target-aspect-exact crop、gapless output ranges、provider-neutral target profileを決定論的に生成するno-effect契約を追加しました。実media解析、focus/OCR検出、Remotion・Resolve実行、Human承認、Asset/Timeline採用、Release/Deployは別Gateです。
- TASK-035 REAPER Audio Finishing Foundation R0として、canonical Asset・Timeline Audio・Audio Workspace・Resource Admissionを参照するbody-free DAW capability、Session Plan、project snapshot、one-shot Human authorization、external execution・QA・Human approval・Audio Round-trip manifest契約を追加しました。REAPER起動・project/audio mutation・plugin操作・render・Asset昇格・Resolve配置・Release/Deploy/Productionは別Gateです。
- TASK-008 Multimodal Scoring R0として、既存TASK-005/006/007/024のcanonical feature座標だけを参照するprovider-neutral固定小数点scoring contractを追加しました。required欠落、UNKNOWN、STALE/REVOKED、provenance不一致をfail-closedで分離し、Human review必須・Edit Plan自動変更なしを固定しています。実media/OCR/provider実行、Human decision、Release、Deployは別Gateです。
- TASK-021 Integrated Dashboard / Operations Foundation R0として、canonical Job・Evidence・Resource・Privacy・Audit・Checkpoint truthを複製せず参照するbody-free read model、staleness・alert・incident分類、operation proposal・Human confirmation・external receipt境界、public/private projectionを追加しました。DashboardからのJob・store・process・app・Provider・通知・Production effectは別Gateです。

- TASK-016 Privacy Guard Contract Foundation R0として、body-free入力座標、検出Evidence、policy評価、immutable redaction proposal、Human privacy review、notification/publication metadata、invalidation、public/private projectionを追加しました。実検出、redaction、通知送信、公開、保持・削除は別Gateです。
- TASK-020 Resource Admission / Monitoring Foundation R0として、CPU・RAM・VRAM・disk・network・process・applicationのbody-free測定事実と、Admission・Watermark・Incident・Operation Gateの決定論的分類、schema mirror、canonical digest、UNKNOWNのfail-closed処理を追加しました。OS情報収集・資源予約・scheduler・process/app操作、Provider・model・media、Release・Deployは別Gateです。
- TASK-013 Native H3 のComfyUI出力解決で、Windows形式の相対サブフォルダーを安全に正規化し、親移動・ドライブ指定・UNCパス・ファイル名内区切り文字を拒否するようにしました。実機再試験では最終MP4のbytes/SHA一致を確認済みです。Asset採用、timeline、Release、Deployは別Gateです。
- TASK-013に、既存Creative Generation・Asset・rights・capability/license/resource Evidenceの正本座標だけを参照し、UNKNOWNをfail-closedで保持しながら候補routeの除外・選択理由を決定論的に記録するbody-freeなSFX provider-neutral routing-plan compilerを追加しました。Provider呼出し、Credential解決、H3 Foley・SFX生成、Asset公開・配置、Resolve、Release/Deployは別Gateのままです。
- TASK-013に、既存Creative Generation・Asset・rights・Evidenceの正本座標だけを参照し、UNKNOWNをfail-closedで保持しながら候補routeの除外・選択理由を決定論的に記録するbody-freeなBGM provider-neutral routing-plan compilerを追加しました。Provider呼出し、Credential解決、BGM生成、Asset公開・配置、Resolve、Release/Deployは別Gateのままです。
- TASK-014 Local Primaryナレーション事前判定I1を追加し、body-freeテキストdigest、hosted VoiceProfileRevision、ZERO_SHOT_LOCAL/FINE_TUNED_LOCAL分離、engine/model/runtime/license/resource/rights/Consentの構造化binding、canonical digest、public/private projection、fail-closed評価と`execution_started=false`を固定。モデル取得、local render/GPU/audio、paid provider、48 kHz publication、録音・保存、Release/Deployは別Gateのままです。
- Added TASK-005 R1C0 data-only detector Evidence contracts for separate expected/observed artifact coordinates, exact current-valid comparison, license/provenance and contained-materialization receipts, bounded probe plans/results, typed normalized events and fail-closed one-to-one R1B1 claim projection. Acquisition, install, process/media execution, Human license acceptance, Native H3, Release and Deploy remain separate Gates.
- Added TASK-048 P-QC-1B body-free admission of exact TASK-047 local GAIN-check receipts into the hosted P-QC contract boundary, with deterministic hashes, strict known-field and cross-field validation, genuine measured-zero handling, structured canonical range/48 kHz 24-bit mono/capture-chain/analyzer/policy bindings, privacy projection and fail-closed clipping, non-finite, mismatch and UNKNOWN classification. It does not read or analyze audio, issue canonical P-QC receipts, change gain/OBS/hardware, or authorize recording, Asset/Dataset/Job/Training/Model/Production effects.
- Added TASK-005 R1B1 no-effect real-detector admission contracts with closed candidate/Evidence states, exact missing-Evidence classification, deterministic canonical digests and fail-closed runtime, license and acquisition Gates. It performs no real-media read, dependency acquisition/install, FFmpeg/OpenCV/PySceneDetect execution, Human license acceptance, Native H3, downstream edit/generation, Release or Deploy.
- Added TASK-047 P-OBS dev.10 reviewable Plugin source and a beginner-friendly Windows Controller/installer for OBS 32.2.1 with selectable recording destination, live Peak/RMS gain meter, persistent recording/paused banners and same-process start/pause/resume/stop. Owner-voice technical Acceptance passed with gap/HMAC/reconnect zero; Dataset adoption, Training, Production use and stable Release remain separate.
- Added TASK-005 R1A bounded synthetic Scene Boundary detector adapter for deterministic contract tests with exact source/profile binding, R0 compiler proposal validation and fail-closed no-effect guards. Real media reads, FFmpeg/ffprobe/OpenCV/PySceneDetect execution, detector accuracy, Human review, downstream editing, Native H3, Release and Deploy remain separate Gates.
- Added TASK-005 Scene Boundary Contract Foundation R0 with canonical Asset/checksum/frame-rate binding, deterministic gapless full-frame scene ranges, detector profile/configuration digests, byte-identical schemas and review-only no-effect guards. Real media analysis, detector runtime, generation, timeline mutation, Native H3 recovery, Release and Deploy remain separate.
- Added TASK-047 GitHub Release composition for the hash-verified OBS Voice Capture Windows installer, matching runtime/source archives and bilingual README build instructions. The Release workflow fails closed on missing or changed assets; this change creates no Tag, Release, Deploy, OBS, capture or recording effect.
- Completed the TASK-036 P-UX-1C packaged-native V6.1.1 parity matrix across Home, WORLD LOCK, Scene Design, Edit, Quick, Settings, Export and all six top menus, with exact disabled reasons, focus restoration, display/accessibility/restart Evidence and full regression. Product runtime and package bytes remain unchanged; Provider, paid, Credential, external NLE, Release and Deploy remain separate.
- Added TASK-047 P-OBS a bilingual local Windows installer candidate for BAI Voice Capture with selectable OBS 32.2.1 target, fail-closed process/version/path/reparse/disk/collision checks, exact3 backup/journal/read-back, Repair/Update/Uninstall recovery, reproducible Inno Setup build and beginner-friendly Japanese/English guidance from installation through destination, gain check, visible recording, stop and result verification. The candidate is unsigned and local-only; Owner voice recording, Dataset/Training/Production, Release and Deploy remain separate.
- Fixed TASK-036 P-UX-1C native closure validation by re-maximizing the WebView host after semantic readiness and rejecting uncovered bright client regions at the right and bottom boundaries. This changes only native validation tooling and its contract test; Product runtime and package bytes, Provider, paid, Credential, external NLE, Release and Deploy behavior remain unchanged.
- Improved TASK-036 P-UX-1C V6.1.1 desktop Shell by connecting existing typed Product snapshots and bounded actions for Planning, Scene and Timeline browsing, WORLD LOCK, Continuity, generation safety and Queue admission, generated-output adoption, Audio placement, Asset/Cut/Final Review, interactive editing, Export recovery and persisted Quick Intent projection. Provider, paid, Credential, external NLE, blanket Export, final Human authority, packaged native visual parity, Release and Deploy remain separate or unclaimed.
- Added TASK-048 P-QC-1A body-free voice-quality calibration metadata contracts with 23 canonical types, exact eight-stage capture-chain validation, declared/measured metric states, staging-versus-Asset separation, ordered single/SNR/before-after input bindings, interval-union readiness evidence, public/private projections and fail-closed P-VS-3A calibration binding. It records or analyzes no audio, changes no hardware/OBS/RX setting, performs no Asset/Dataset/Job/Training/Model/production effect, and adds no CMake/native/download/install/Release/Deploy operation.
- Added TASK-046 P-VS-3A body-free recording-session metadata contracts for immutable Session, Segment Attempt, Teleprompter Checkpoint, Dataset Candidate and separate Owner Review revisions, with exact VoiceProfile/Consent binding, append-only CAS/state validation, fail-closed unresolved capture/resource/quality/job dependencies, structured non-dispatching execution authorization, restart-safe sentence-level resume, and public/private projections. It records no audio, script, or transcript body and starts no OBS capture, Asset/Dataset mutation, Job/Queue, Training/Model, production recording, download/install, Release, or Deploy.
- Added TASK-046 P-VS-1A body-free `VoiceProfileRevision` metadata bound to the existing TASK-014 identity/digest, exact Model Artifact License and Consent references, public/private projections, append-only CAS persistence and a non-executing readiness preflight. It stores no voice/audio body and starts no Model download/load/inference, recording, Dataset adoption, Provider, Credential, Shell integration, version, Tag, Release or Deploy.
- Added the bounded TASK-036 P-UX-1C canonical Track correction: Video/Subtitle/Audio/SE/BGM add/remove with minimum-one-category protection, per-Track visibility/lock/remove, audio mute/solo, Python-owned Track height and packaged Windows interaction/display/restart Evidence. Whole-surface V6.1.1 parity and overall TASK-036 completion remain explicitly open.
- Elevated TASK-047 P-OBS-1 minimum OBS capture to the P0 dependency for P-VS-3 production training-material recording and P-VS-4 fine-tuning; split P-OBS-0 exact-path read/design/probe from P-OBS-1 selected-input/recoverable capture and later P-OBS-2 continuous/multi-source breadth. Existing P-UX-1C/P-VS-1A work continues unchanged, and this documentation-only decision starts no probe, Plugin load, recording, Dataset adoption or training.
- Hosted the TASK-036 P-UX-1C and TASK-046 P-VS-1A parallel-development Work Lock Registry, synchronized PR #90/P-VS-0 as hosted-closed, made P-UX-1C the active Consumer route, and split P-VS-1A body-free Backend from successor-mock-gated P-VS-1B Shell/TASK-014 integration. This documentation-only coordination starts no runtime, voice processing, Provider, external app or release operation.
- Allocated TASK-046 Voice Studio, TASK-047 OBS Voice Capture and TASK-048 Voice Quality Calibration from the checksum-verified Ver.1.2 Owner design; added the complete OR-01..32/Q1..44 Crosswalk, Local-Primary/privacy/license architecture and a 60–90 second Japanese vertical-slice route after TASK-036 P-UX-1C. This documentation-only intake starts no model download, voice processing, Provider, external app or release operation.
- Added TASK-036 P-UX-1B core interaction convergence: explicit command dispatch, menu/focus restoration, nine read-only Settings category tabs, real generation/export Background Jobs projection and controller-authoritative coalesced Timeline scrub. It adds no JavaScript durable truth, Provider authority or automatic replay; P-UX-1C still owns the complete native parity matrix.
- Added TASK-036 P-UX-1A Product-owned V6.1.1 packaged Shell composition: canonical menus/stage navigation, Home Recent/Direct, all primary workspaces, Edit three-pane/Timeline, Export settings/External/Queue and nine-category Settings, with real bridge projections and no mock demo state or synthetic success. Remaining disabled interactions and the full native parity matrix stay in P-UX-1B/1C.
- Added TASK-026 P-AUDIO-1 append-only Product Project placement-plan history, restart-derived CURRENT/STALE projection, exact upstream re-derivation, TASK-043 coordinated save and a narrow Audio Workspace plan-persistence action. It starts no Provider, paid work, media write, TASK-010, Resolve or Cubase operation; V6.1.1 mock-to-EXE visual convergence is the Owner-directed next P0 after hosted closure.
- Added TASK-027 P-ORCH-2 immutable regeneration Strategy/Parent binding across Prompt Registry, Generation Queue and completed-output adoption, with exact lineage validation, legacy read compatibility and fail-closed recovery; Provider execution, paid work, Human ACCEPT/LOCK, publication and NLE mutation remain unauthorized.
- Added TASK-027 P-ORCH-1 Human-confirmed adoption of an exact initial completed local generation output into canonical TASK-003 Asset, TASK-037 Candidate and TASK-040 PASS Attempt/`GENERATED_FROM` lineage, ending only at `READY_FOR_AUDIT` with checksum-closed restart recovery and unified Generation Queue UI. Provider replay, paid work, Human ACCEPT/LOCK, publication and NLE mutation remain false; regenerated Prompt output is parked until exact Strategy/Parent binding is persisted.

## [0.21.0] - 2026-08-15

- Finalized the exact `0.21.0 / v0.21.0 / stable` release candidate metadata, upgrade/migration guidance and bounded release notes after full Windows/WSL2 regression, wheel/source build, fresh wheel install and final one-dir packaged restart acceptance.
- Validated TASK-045 P-RC-2 on the final Windows package: owned v0.20.1 Project open/reopen without manifest rewrite, Narrator/UIA, three displays, Timeline interaction, native picker cancellation, conversation-free restart, wheel clean install and full Windows/WSL2 regression. Also made all rich TASK-036 Bridge bindings private after packaged Project acceptance exposed pywebview recursive API discovery.
- Added TASK-045 P-RC-1 explicit legacy Project discovery, code-registered lossless copy-on-write migration with exact backup/reopen proof, additive schema v3 bounded Asset keyset paging and a concurrent source-manifest latest-pointer corrective. It does not run ambiguous migration, Provider, paid, native, Tag, Release or Production Deploy operations.
- Closed TASK-044 P-NLE-4 through PR #72 at exact main `6703c42a` and activated TASK-045 release closure as three governed units: compatibility/migration/Asset paging, integrated native/clean-install/restart acceptance, and exact release finalization. This design checkpoint does not select a version or perform migration, Tag, Release or Deploy.
- Added TASK-044 P-NLE-4 dynamic Unified NLE composition in the existing TASK-036 Shell: bounded semantic clip DOM, distinct selection/seek/review, keyboard Fit/IN/OUT/trim flow, private typed pywebview bridge, per-job Export cancel/recovery controls, narrow/mixed-monitor behavior and packaged Windows acceptance. No blanket Execute All or external replay is authorized.
- Added TASK-044 P-NLE-3 checksum-bound durable Export Queue composition with logical-only output identities, exact stale preflight, per-job external confirmation, DISPATCHING-before-side-effect recovery, Render QA-bound success and no blanket Execute All authority.
- Added TASK-044 P-NLE-2 exact-frame trim/move/snap and checked track edits as append-only Product Project revisions, with compensating Undo/Redo and interruption-safe TASK-043 command-history finalization. It starts no provider, native or external mutation.
- Added TASK-044 P-NLE-1 frame-authoritative dynamic Timeline projection with strict selection/seek separation, rational viewport transforms and bounded 10,000-clip windowing. It is read/reversible only and starts no external mutation.
- Allocated TASK-044 implementation into four bounded units for frame-authoritative Timeline interaction, semantic editing/history, durable Export Queue composition and existing Shell/UI native acceptance. This design checkpoint adds no runtime, external execution or release authority.
- Added TASK-042 P-V6-4 frame-authoritative Timeline Audio: append-only plans, proposal-only SRT conflict handling, first-class AMBIENCE, exact TASK-037/041/026 proof binding and TASK-043 coordinated Product Project persistence. Provider, paid, native, media and release authority remain false.
- Added TASK-043 P-FND-4 durable Product-local Job/Export Queue foundation: deterministic operation identity, CAS state transitions, bounded cost truth, restart-to-UNKNOWN recovery without automatic replay, typed reconciliation and read-only TASK-036 Shell projection. It neither replaces TASK-027 Generation Queue nor authorizes Provider/paid/external execution.
- Added TASK-043 P-FND-3: append-only compensating Undo/Redo history with explicit STALE targets, quiescent/debounced Autosave, bounded verified Backup retention, restore preview and CAS-safe restore as a new Project revision. External replay, Evidence deletion and private credential/token capture remain prohibited.
- Added TASK-043 P-FND-2 coordinated save/recovery: transaction-scoped staging and backup, child-first/manifest-last CAS commit, interruption journal, deterministic COMPLETE/ROLLBACK/FINALIZE, and fail-closed pending-recovery behavior.
- Added TASK-043 P-FND-1: a closed versioned Product Project Manifest, exact child-store bindings, CAS persistence, compatibility inspection and deterministic read-only migration planning. Migration apply, external execution and release behavior remain unchanged.
- Rebuilt the post-v0.20.1 roadmap under the replacement `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE` Owner Directive: synchronized P-V6-4 Design PR #61 hosted closure, allocated TASK-043 Product Project/migration/recovery foundation, and split practical NLE/Export and native release closure into TASK-044/045. This checkpoint changes governance/design only and does not claim runtime capability or a new release.

- Allocated Owner-maximum TASK-042 and inserted the V6 Product Workflow route before TASK-013 Native H3 resume, with current-main audit, full migration/integration design and exact post-merge P-V6-1A authorization; no runtime, Provider, native or release behavior changes in this roadmap checkpoint.
- Added TASK-042 P-V6-1A as a standalone closed Production Blueprint v2/frame-binding contract and deterministic read-only v1 migration preview; v1 remains unchanged, and store/Proposal/GO/UI/Provider/native execution remains outside this slice.
- Recorded P-V6-1A hosted closure after PR #50 passed all nine checks and merged at exact main `694e9933`; no capability or release claim was widened.
- Integrated Blueprint v2 into exact Proposal/Human-GO/crash-safe snapshot handling while keeping v2 Production Control and generation fail-closed until P-V6-2; added the Owner-required Windows EXE build batch, ignored `builds/` output, Windows build guide and plain-language README AUTONOMY examples.
- Recorded P-V6-1B hosted closure after PR #53 passed all nine checks and merged at exact main `5413a85b`, with branch/clone cleanup and AUTONOMY reselection verified; P-V6-2 remains Design-only and waits for the bounded Closure Sync merge.
- Hosted the bounded Closure Sync through PR #54 at exact main `f5ad4cdf`, then used fresh-main AUTONOMY to select and complete the P-V6-2 WORLD LOCK current-main audit, DEV-4 design, exact Allowed Files and two-cycle Critic review; implementation, Provider/native execution and release remain unstarted.
- Hosted P-V6-2 Design through PR #55 at exact main `6a4a6a5e`, then implemented a TASK-037-backed WORLD LOCK projection, exact v2 Plan/Trace/Planning installation, transitive STALE/restart recovery and role/Slot/Candidate-bound Queue proof while preserving v1 behavior and all Provider/native/release boundaries.
- Recorded P-V6-2 hosted closure after PR #56 passed all nine checks and merged at exact main `4c77ad08`, removed its branch/clone, and used fresh-main AUTONOMY to select the bounded cadence-2/2 Closure Sync while P-V6-3 waits.
- Hosted P-V6-2 Closure Sync through PR #57 at exact main `92ff6938`, then used fresh-main AUTONOMY to select and complete the P-V6-3 immutable Prompt/Provider projection/Quick authority design, including a fail-closed v2 Queue persistence corrective; implementation remains not started.
- Hosted P-V6-3 Design through PR #58 at exact main `c78ed014`, then implemented immutable private-body-free Prompt compilation/TASK-040 binding, complete secret-free Provider/Model readiness, append-only Quick intent CAS/restart/read-only adoption and the v2 Queue persistence corrective without starting Provider/native/media/Candidate/Audit/Lock or release operations.
- Recorded P-V6-3 hosted closure after PR #59 passed all nine checks and merged at exact main `7ac291f1`, removed its branch/clone, and used fresh-main AUTONOMY to select the docs-only Closure Sync while P-V6-4 Design waits.
- Hosted the P-V6-3 Closure Sync through PR #60 at exact main `c6a5cb10`, then completed the P-V6-4 frame-authoritative Timeline Audio/SRT conflict/TASK-041 reuse design and two Critic cycles without starting implementation, Provider/native execution or a release.
- Promoted TASK-041 Audio Workspace into the unified Desktop Shell with project-scoped crash-safe placement review, exact Candidate/hash-bound one-shot Human decisions and trusted-launch composition, while keeping Provider, TASK-026, Resolve and Cubase execution separate.
- Added an explicit TASK-013 read-only ComfyUI runtime readiness preflight through the Product application and Shell bridge; it reuses exact node/model/resource/runtime checks while creating no dispatch, journal, output, execution authorization or Native Gate claim.
- Hardened the TASK-013 local ComfyUI pre-dispatch runtime guard to reject all memory flags observed in the Owner-confirmed force-restart attempt, including assignment forms, while keeping native H3 execution parked and non-replayable.
- Added a fail-closed TASK-013 local ComfyUI MiniMax H3 text-to-video adapter with a checksum-bound body-free workflow, exact local/free route and runtime-policy checks, durable no-replay dispatch journal, contained verified output publication and opt-in trusted-launch composition. The bounded native probe exposed a runtime failure/recovery boundary and does not claim a completed generation.
- Added TASK-013 restart-safe local generation execution control: exact current Queue re-derivation, private Prompt checksum verification, credential-free `LOCAL_FREE_AI` routing, durable pre-side-effect `DISPATCHING`, no automatic replay and optional unified Queue UI; live adapters, paid routes and Candidate publication remain excluded.
- Promoted TASK-027 Generation Queue admission into a durable unified Desktop workspace derived only from exact Approved Plan, Feasibility, LOCK/STALE, Continuity and Prompt/Profile Evidence.
- Added one-shot, append-only, restart-safe Queue records with unique required-input proof and invariant `EXECUTION_NOT_AUTHORIZED`; no Provider call, paid authorization, Budget reservation or Candidate creation is exposed.
- Promoted TASK-040 Prompt/Generation Evidence into a durable project-scoped Application and unified Desktop workspace with immutable Prompt versions, completed Attempt import and explicit Human-routed regeneration Prompt registration.
- Added strict Prompt persistence/CAS, exact parent/Profile/input/output lineage, recoverable PASS Prompt/Production binding and TASK-038 recovery interlock without Provider calls, paid execution, Candidate creation or NLE mutation.
- Promoted TASK-039 Continuity into the unified Desktop `連続性` workspace with exact locked END_FRAME -> START_FRAME identity, production-derived target inspection, non-overridable DIRECT_CONTINUATION and separate one-shot SOFT_CONTINUITY Human approval.
- Added serialized Continuity CAS, checksum-bound recoverable two-store Edge registration and coherent root/downstream STALE propagation while preserving prior Evidence and prohibiting automatic regeneration, physical deletion, Provider/paid execution and NLE mutation.
- Promoted TASK-013 Shot Feasibility into an exact Approved-Plan-bound durable `生成安全` workspace with deterministic identities, complete Promotion checks, one-shot Human review, atomic persistence and stale/concurrent-write rejection.
- Bound structured Visual Compliance Evidence to the durable TASK-038 Audit Application while preserving Human Candidate authority and prohibiting automatic ACCEPT/REJECT/regeneration, Provider execution, paid calls and NLE mutation.
- Promoted the TASK-027 persisted Planning Foundation into a unified Desktop `企画` workspace with complete Proposal/Scene Contract review, exact Human GO and a separate Approved Plan -> Production Control installation confirmation.
- Serialized cross-process Proposal CAS publication and preserved strict boundaries: GO starts no Provider, paid execution, Budget reservation, Resolve/Cubase mutation or publish operation.
- Promoted TASK-038 Audit Workspace into a durable project-scoped Application Service with exact Human decision confirmation, prepared two-store transactions and explicit fail-closed crash recovery.
- Added user-facing immutable Audit history, AI/Human identity, dimensions, findings, Failure Codes, alternate-use proposals and separate ACCEPT/REJECT/ALTERNATE_USE/NEEDS_REGENERATION actions to the unified `制作管理` workspace; Reject is not Delete and regeneration never starts automatically.
- Promoted the existing TASK-037 Asset Slot / Candidate / LOCK / STALE Foundation into the unified Desktop Shell through a durable project-scoped Production Control Application Service and `制作管理` workspace.
- Restricted Slot installation to Human-approved Plans, preserved TASK-038 Human ACCEPT/REJECT ownership, and added exact one-shot Candidate LOCK confirmation bound to snapshot, Slot revision and Asset SHA-256.
- Serialized Production Control compare-and-swap publication across local processes and added concurrency, stale-confirmation, tamper, project-scope and Shell regression coverage without adding Provider/NLE execution or physical deletion.
- Hardened Windows CI against Chocolatey search-index outages by downloading the pinned FFmpeg 8.1.2 package directly and verifying its exact SHA-256 before local installation.

## [0.20.1] - 2026-08-14

- Closed the TASK-036 H2 Windows runtime remainder with clean-profile packaged launch, actual three-monitor movement, Windows UI Automation and Narrator semantic-label smoke Evidence.
- Added a fail-closed packaged startup preflight with a native actionable WebView2 recovery dialog and an explicit maximum supported executable-path policy instead of an opaque frozen-app failure.
- Fixed the desktop renderer to EdgeChromium/WebView2, added visible keyboard focus, skip navigation, semantic editing/timeline labels and a narrow high-scale responsive layout.
- Added repeatable Windows gates for clean-profile/display/accessibility and isolated missing-WebView2 recovery without uninstalling or modifying the host runtime.

## [0.20.0] - 2026-08-14

- Formally parked the remaining TASK-036 clean-profile, missing-WebView2, long-path, full DPI/mixed-monitor and screen-reader cases to Phase H2 without promoting them to PASS; the bounded release environment and unsupported claims are explicit.
- Completed Phase G backend native Evidence: real Resolve assembly/linked A/V/edit-aware subtitle semantics, real Resolve render QA and real Cubase 13 48 kHz PCM round-trip pass without broadening external-write or paid-provider authority.
- Corrected Resolve Timeline-start-relative record placement, localized completed-render status handling and WebView2 runtime version discovery; assembly-plan contract is now `1.3.0` with an explicit record-frame basis.
- Completed the TASK-036 W2 packaged native route from trusted Project launch through ingest, cached local FasterWhisper, Subtitle, Human Cut Review/approval, exact Resolve apply, TASK-011 native Render QA and atomic TASK-012 EDITOR_WORK. Host paths, provider settings, analysis audio, adapters, Resolve targets and external-write authority remain Python-only launch bindings; overall Product completion remains unclaimed while W0/W1 and Phase G closure gates remain.
- Added exact one-shot TASK-011 native-render authorization bound to the applied Assembly, sandbox Project, Automation Timeline, duration/rate contract and Python-only Evidence destination; successful execution binds the exact QA identity without exposing the render path to JavaScript.
- Added strict private launch-config validation, frozen FasterWhisper/CTranslate2/ONNX/PyAV into the PyInstaller one-dir package, bound the required managed edit-aware SRT path and made EDITOR_WORK publication atomic after complete optional-source preflight.
- Latest Phase G regression: WSL2 Ubuntu `805 passed`; focused atomic handoff/launcher/runtime `25 passed`. The updated 461-file PyInstaller bundle passes trusted native launch, real W2 E2E and normal close; hosted PR CI remains required.

- Implemented the TASK-007 -> TASK-010 -> TASK-011 -> TASK-012 editing Technical MVP backend/application-service vertical slice: human-approved Edit Plan, Automation-owned Resolve assembly, rendered-artifact QA/loudness and deterministic EDITOR_WORK/Cubase round-trip.
- Added strict external-write/idempotency/partial-state gates for Resolve and require probed source/normalized media FPS instead of substituting Timeline FPS for source-frame conversion.
- Added canonical/package schemas and 17 focused regression tests; full automated regression is 462/462 PASS. All four capabilities remain `INTEGRATION_DESIGNED`; Unified Desktop and real Windows/Resolve/Cubase native validation remain future gates.

- Registered `PRODUCT-ARCH-001`: BAI Video Production final UX is one unified Desktop Application; CLI/localhost surfaces are internal/transitional and every future user-facing Task must define Shell integration.

- Registered `BVP-KNOWLEDGE-REFIMG-001` and the future TASK-013 Scene-Compatible Reference / Shot Feasibility Gate detailed design; documentation only, no runtime behavior change.

- Integrated end-user GUI and complete automatic editing workflow remain under development.

## [0.19.0] - 2026-08-12

- Reconciled TASK-023 with the existing TASK-006 FasterWhisper provider instead of creating a duplicate ASR implementation.
- Added deterministic source/config execution identity and path-minimized, text-free provider reconciliation evidence.
- Added model-free/network-free `ai-video-faster-whisper-evidence` as a developer/diagnostic CLI; final user entrypoint remains BAI Video Production.exe -> Subtitle Workspace.
- Registered TASK-023 as `INTEGRATION_DESIGNED` under PRODUCT-ARCH-001; no Shell integration is claimed by this slice.
- Explicitly deferred final transcript-result caching, word-level timestamp schema expansion and recognition-semantic retuning.
- Finalized TASK-023 validation for v0.19.0: 444 passed, 1 intentional skip; compileall/diff-check PASS; Windows real-media diagnostic evidence PASS with no model load, inference, network use, source/cache path leakage, or transcript-text leakage.

## [0.18.0] - 2026-08-12

- Added TASK-024 review-only silence/filler/disfluency cut-candidate analysis on normalized PCM audio and optional canonical Transcript input.
- Added fixed-argv FFmpeg `silencedetect`, transcript Keep Blocks, conservative filler-only and exact-adjacent-repeat candidates, and fail-closed overlap/integrity bounds.
- Added deterministic text-free Cut Candidate Manifest/report with explicit TASK-007 planning ownership, TASK-010 execution ownership, and `auto_apply_authorized=false`.
- Added `ai-video-cut-candidates`, canonical/package JSON Schema, user documentation, and focused privacy/integrity/CLI regression coverage.

## [0.17.0] - 2026-08-11

- Added resumable chunk/checkpoint transcription for large media with bounded overlap, explicit resume/restart semantics, source/config/plan integrity checks, and private local work state.
- Reused one FasterWhisper model instance across chunk calls while preserving the existing one-shot transcription path and explicit model-download gate.
- Added a deterministic, private Resolve subtitle-placement handoff plan with exact frame mapping, explicit timeline origin, approval readiness, collision fail-closed behavior, and TASK-010 execution ownership.
- Added focused regression coverage for resume integrity, private reports/checkpoints, model reuse, and Resolve handoff determinism.

## [0.16.4] - 2026-08-11

- Replaced the Windows native SRT dialog foreground-owner C# compilation path with a top-most cursor-monitor WinForms owner, avoiding the `System.Windows.Forms` `Add-Type -TypeDefinition` failure observed on native Windows.
- Added an ASCII/Base64 dialog result protocol and `-OutputFormat Text` boundary so PowerShell CLIXML and Windows code-page mojibake are never rendered into the browser status panel.
- Added regression coverage for Open/Save success, cancel, bounded PowerShell failure, malformed protocol data, and raw-CLIXML suppression.

## [0.16.3] - 2026-08-11

- Corrected Subtitle Workspace relative insertion so a cue placed between neighboring subtitles uses a strict 1 ms inner margin (for example `...300` / `...600` becomes `...301`–`...599`).
- Added prominent import/export/action feedback; successful SRT export now reports its resolved destination path and byte count.
- Added explicit local-server disconnect feedback so stale browser pages no longer make controls appear silently dead.
- Changed Windows Open/Save dialog launch to use the foreground window as the native owner with a top-most fallback for multi-monitor/fullscreen workflows.

## [0.16.2] - 2026-08-11

- Added Windows-native Open/Save dialogs to the Subtitle Workspace so operators can choose an SRT file and destination without typing filesystem paths.
- Kept manual path entry for advanced use, added a replacement confirmation before importing over an existing workspace, and preserved the loopback/CSRF boundary.
- Added deterministic dialog-service tests without opening a real native window during automated regression.

## [0.16.1] - 2026-08-10

- Corrected the SRT CRLF regression fixture to write exact UTF-8 BOM bytes on Windows, preventing text-mode newline translation from producing malformed `CRCRLF` test data.
- Confirmed that the production SRT parser was not the failure source; runtime behavior and the 0.16.0 Subtitle Workspace contract are unchanged.

## [0.16.0] - 2026-08-10

- Added a local Subtitle Workspace GUI for editing planned narration, ASR transcripts and imported SRT without provider execution.
- Added stable cue identity, immutable source wording, revisioned JSON persistence and insert/update/delete operations.
- Added bounded streaming SRT import, atomic SRT export and a default-off AI typo/omission permission gate that never calls an AI by itself.
- Added pull-request release-metadata checks requiring CHANGELOG updates for product changes and consistent package/GUI/citation versions.
- Documented truthful large-media limits: SRT text is streamed, while multi-GB media transcription still requires the future chunk/checkpoint slice.

## [0.15.1] - 2026-08-10

- Corrected adjacent NTSC SRT cues so millisecond floor/ceil conversion cannot create a 1 ms overlap at a shared end-exclusive frame boundary.
- Preserved safe ceil-end behavior for isolated/final cues and added native-Evidence-shaped regression fixtures.
- Recorded the successful Windows FasterWhisper run and designed immutable Raw Transcript, prioritized dictionaries, GUI review and a default-off AI typo/omission suggestion gate.
- Added TASK-014 owner-trained ElevenLabs narration design and TASK-035 REAPER/iZotope/Resolve audio round-trip design.

## [0.15.0] - 2026-08-10

- Added TASK-027 Slice A1 Production Blueprint and validated Scene Ledger contracts derived from 11 real production design documents.
- Added stable PERSON/SPACE/PROMPT/ASSET/AUDIO reference registration with explicit planned/available/locked state.
- Added real-capture-first asset strategy and complete frame-range coverage validation.
- Added A/B/C visual-generation risk classification and fail-closed dense-UI rules requiring locked references, static cameras and post-composited text.
- Added scene-level narration, dialogue, SFX, BGM, sound-logo and final-hold planning.
- Routed narration timing, mix comparison, continuity QA and hypothesis-based learning findings into their canonical future Tasks without copying private source documents.

## [0.14.0] - 2026-08-10

- Added the optional FasterWhisper local ASR adapter and end-user Transcript/SRT CLI.
- Added explicit model-download authorization with local-files-only default behavior.
- Added atomic private Transcript/SRT publication and a schema-validated text-free operational report.
- Added NTSC adjacent-cue normalization and failure cleanup regression coverage.
- Separated the product version from the AI Connection Settings revision in the local GUI footer.

## [0.13.0] - 2026-08-10

- Added the TASK-006 transcript and subtitle foundation with provider-neutral ASR contracts and checksummed canonical Manifests.
- Added exact cut-aware subtitle mapping through TASK-022 Timeline placements, including deterministic splitting and retiming across kept source ranges.
- Added NTSC-safe SRT rendering using rational frame conversion with floor-start/ceil-end boundaries and normalized multiline text.
- Added packaged JSON Schemas and regression fixtures for validation, overlap rejection, cut removal, split cues, empty plans and deterministic hashes.

## [0.12.2] - 2026-08-10

- Linked the Catalog and Secure credentials projections explicitly: enabled credential-required routes appear in the active key list, while other routes do not.
- Added a retained-key cleanup section for disabled routes instead of silently deleting secrets or presenting disabled Models as active.
- Prevented removing `Credential required` while a key remains stored, avoiding an unreachable orphaned Windows credential.
- Added visible Catalog credential status and end-to-end add/disable/delete/unrequire regression coverage.

## [0.12.1] - 2026-08-10

- Fixed API-key re-registration suggestions so every credential row has an independent password-manager section, ID, and name instead of only the first row being recognized.
- Changed the credential input hint from new-password suppression to route-scoped current-password lookup while retaining password masking and post-operation clearing.

## [0.12.0] - 2026-08-10

- Added API-key onboarding from the loopback settings screen into the current user's Windows Credential Manager.
- Added opaque hashed credential targets, UTF-8/size validation, save/read/status/delete operations, and fail-closed non-Windows behavior.
- Exposed registration state only; secret values and internal credential references remain absent from settings JSON and browser responses.
- Added bilingual safety copy and regression tests proving that credential mutations never start Provider calls, billing, generation, or editing.

## [0.11.0] - 2026-08-10

- Added a local Provider/Model Catalog editor for safe add, edit, and disable operations without JSON editing.
- Added truthful `IMPLEMENTED`, `LOCAL_RUNTIME`, and `PLANNED_ADAPTER` labels so configuration never implies execution support.
- Added generated internal credential references while excluding keys, tokens, references, endpoints, headers, and arbitrary settings from the browser contract.
- Reused atomic revision storage, CSRF, Host, CSP, and bounded-request protections and added Catalog regression coverage.

## [0.10.0] - 2026-08-10

- Added a responsive bilingual AI Connection settings screen served exclusively on local loopback.
- Added interactive mode and preferred configured-model selection across planning, video, image, audio, and music.
- Added a narrow mutation contract with revision conflict checks, random CSRF protection, Host validation, restrictive CSP, JSON/size limits, and no Provider execution path.
- Added a Windows launcher plus beginner and developer guides with diagrams, safety explanations, and truthful remaining gates.

## [0.9.0] - 2026-08-10

- Added atomic, checksummed AI Connection settings persistence with optimistic revision checks.
- Added safe migration from the 0.8 raw profile document and fail-closed handling for damaged or unsupported data.
- Added a bilingual GUI-neutral form contract with five workloads, plain-language mode/status help, exact safe model metadata, and no credential or endpoint references.
- Added power-loss rollback, stale-write, migration, integrity, schema-packaging, and secret-exclusion regression tests.

## [0.8.0] - 2026-08-10

- Added a GUI-safe, secret-free AI Connection settings preflight across planning, video, image, audio, and music.
- Reports selected exact model metadata, cost/locality class, credential readiness, disabled/blocked state, normalized errors, and a deterministic hash without executing a provider.
- Added a dated detailed design for persistence, interactive settings UI, and low-literacy usability review.

## [0.7.0] - 2026-08-10

- Added GitHub-rendered architecture and roadmap visuals plus a credential-free five-minute demo.
- Added complete Japanese/English public README navigation and equivalent English project, impact, safety and contribution guidance.
- Added guarded GitHub Release and PyPI Trusted Publishing workflows.
- Added monthly release-readiness automation, good-first-issue intake and measurable adoption/impact protocols.

## [0.6.7] - 2026-08-10

- Removed process-global `os.name` mutation from the Audacity Windows import regression test.
- Added an explicit OS-name seam so Linux/Python 3.11 pytest never attempts to instantiate `WindowsPath`.

## [0.6.6] - 2026-08-10

- Provisioned and verified FFmpeg/ffprobe on Linux and Windows GitHub-hosted CI runners.
- Corrected the six-job CI failure caused by missing media executables rather than a product regression.

## [0.6.5] - 2026-08-10

- Corrected every public repository URL to `baisound/bai_video_production`.
- Added a regression check that prevents the former repository URL from returning.

## [0.6.4] - 2026-08-10

- Added OSS public documentation, MIT license, governance, security and contribution policies.
- Added GitHub CI, security scanning, Dependabot, Issue forms and Pull Request template.
- Added public-package metadata and repository structure regression checks.

## [0.6.3] - 2026-08-10

- Replaced provider-purpose assumptions with exact model capability routing.

## [0.6.2] - 2026-08-10

- Added ElevenLabs TTS/SFX/music and SunoAPI.org asynchronous music adapters.

## [0.6.1] - 2026-08-10

- Added OpenAI, Anthropic and Google text execution adapters.

## [0.6.0] - 2026-08-10

- Added unified AI connection profiles and deterministic route resolution.

## [0.5.0] - 2026-08-10

- Added exact rational Timeline Mapping Service.

## [0.4.10] - 2026-08-09

- Completed Media Normalization and Local Visual/Audio AI Runtime foundation after native-Windows regression.

## [0.3.0] - 2026-08-08

- Added secure Asset ingest, rights/checksum and Logical Path Resolver.

## [0.2.4] - 2026-08-08

- Completed DaVinci Resolve capability spike.

## [0.1.0] - 2026-08-08

- Added Product domain, canonical manifest, state, evidence and persistence foundation.
