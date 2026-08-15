# AI動画制作自動化システム

## Project ID

`ai-video-production`

## Project Status

`V0_21_0_RELEASED_TASK_046_P_VS_0_HOSTED_CLOSED_TASK_036_P_UX_1C_ACTIVE_PARALLEL_LOCKS_HOSTED_NATIVE_RUNTIME_PARKED`

## Purpose

元動画・音声・画像・字幕・AI生成素材を解析・計画・編集・検査し、DaVinci Resolveを中心に人間が安全に仕上げられる動画制作自動化基盤を構築する。

## Active Project Root

Consumer Project Repository root. Machine-specific absolute paths are not canonical project metadata.

## Source / Test / Documentation

- Source: `src/`
- Tests: `tests/`
- Schemas: `schemas/`
- Profiles: `profiles/`
- Documentation: `docs/`
- Project Task Evidence: `docs/ai-team/tasks/`

## BAI Development OS Integration

- Adapter compatibility baseline: `1.0.0`
- Historical migration baseline from Product `0.17.0`: `BAI Development OS 1.0.0 / Architecture Ver.2.28`
- Current post-`v0.20.1` R2-R4 development-governance authority: `BAI Development OS v1.1.0 / Architecture Ver.2.29`; this updates development procedure only and introduces no Product runtime dependency
- Adapter: `.bai-os/project.json`
- Bootstrap Governance Level: `Level A — Governance Only`
- TASK-001 decision: remain `Level A — Governance Only`; runtime-assisted BAI dependency is not justified for the product foundation
- BAI OS Core / shared Roles / OS-owned Tasks / Registry are not copied into this repository
- BAI Development OS is a development-time governance/tooling foundation only. It is not a Product runtime dependency.

### Ownership Boundary

Canonical invariant: `OWNERSHIP_NOT_PATH_BASED`

- `docs/ai-team/` というパス名だけでBAI Development OS所有とは判断しない。OwnershipはRepositoryと文書責務で判断する。
- このBAI Video Production repository内の `PROJECT.md`、`docs/ai-team/**`、Product Task / Design / Evidence、`src/**`、`tests/**` はProduct-ownedであり、Product実装結果と同期して必要に応じて更新する。
- BAI Development OS repository側のRegistry、OS Core、shared Roles、OS-owned Tasks、OS-owned Evidence等はOS-ownedであり、Consumer ProjectのProduct変更として勝手に編集・複製しない。
- BAI Development OS CoreをこのProduct repositoryへ丸ごとコピーしてOwnership境界を曖昧にしない。

## Non-Negotiable Product Goal — Standalone Application

Canonical invariant: `STANDALONE_APPLICATION_REQUIRED`

BAI Video Productionの最終成果物は、BAI Development OSから独立してインストール・起動・実行・更新・利用できる単体アプリケーションでなければならない。BAI Development OSは開発時に設計、Critic/Judge、Knowledge、Context/Cost Guard、Integration/Security/Release等の能力を必要に応じて利用するための共通開発基盤であり、完成Productの実行環境ではない。

- Product runtimeはBAI Development OS repository、package、Registry、Role、OS-owned Task、Evidence store、Context PackまたはOS内部Serviceの存在を要求してはならない。
- 開発中にBAI Development OSのSubsystemを利用しても、Product実行時に必要なCapabilityはProduct所有の実装・Adapter・明示的なProduct dependencyとして成立させる。
- BAI Development OSの更新・停止・削除・未接続によって、完成したBAI Video Productionの通常利用が停止してはならない。
- 0.17.0以降のOS差し替えは「開発方法の更新」であり、「Product runtimeへのOS組込み」ではない。
- 将来の設計、Refactor、Provider統合、配布方式の判断は、このStandalone Application要件を弱めてはならない。
- この要件と衝突する提案は、TASK認可の有無にかかわらず最終Product設計として採用しない。

## Product Design Baseline

`AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`

この設計書はProduct仕様のBaselineである。BAI Development OSの開発Governanceとは責任を分離する。

## Core Product Principles

1. Canonical ManifestをProduct Domainの正本とし、NLE Projectだけを正本にしない。
2. AI判断と決定論的実行を分離する。
3. 元素材を破壊せず、再生成可能・監査可能にする。
4. Automation-ownedとHuman-owned Timelineを分離する。
5. Windows/WSL2/Object StorageのPath差異をLogical URI/Path Resolverで吸収する。
6. Production Job StateはProduct Domain専用Serviceのみが変更する。
7. External Provider / NLE / AI ModelはAdapter境界を持つ。
8. Product JobはCheckpoint/Evidence/Idempotencyにより安全に再開可能にする。
9. 権利、プライバシー、費用、公開安全性をProduct要件として扱う。
10. 開発TaskのAuthorizationとProduct Jobの状態を混同しない。

## BAI OS / Product Domain Separation

- BAI LifecycleOS: 開発TASK用。
- Product Job State Machine: 動画制作案件用。
- BAI Lifecycle Recovery: 開発作業のSafe Stop/Resume用。
- Product Job Recovery: 動画処理の途中再開用。
- BAI Cost Guard: AI支援開発/Tooling予算用。
- Product Cost Ledger: 動画生成ジョブの費用用。
- BAI SecurityOS: 開発Tooling/Secret/Egress/Sandbox用。
- Product Privacy Guard: 動画内容のPII/権利/NG表現用。

## Adaptive Governance

各TASKをDEV-0〜DEV-4へ分類する。すべての変更へ固定の最大手続きを強制しない。

- TASK-001: `DEV-4 FOUNDATION CRITICAL` / score 25 / COMPLETED
- TASK-002: `DEV-4 FOUNDATION CRITICAL` / score 22 / COMPLETED
- TASK-003: `DEV-4 FOUNDATION CRITICAL` / score 33 / COMPLETED
- TASK-004: `DEV-4 FOUNDATION CRITICAL` / score 25 / completed on package 0.4.10 with accepted target behavioral Evidence and `255 / 255` native-Windows regression PASS

TASK-004はTimebaseだけでなく、ComfyUI画像/動画生成、Character Identity、MiniMax H3 Production Brief/SingleFrame/Spectrum/Foley、Audacity OpenVINO外部Runtime境界を含むためSafety Floorを下げない。

## Security / Privacy Constraints

- Secret値をManifest、prompt、log、evidenceへ保存しない。
- Product Path ResolverはAllowlist外Pathを拒否する。
- External inputから任意Shell/Pythonを直接実行しない。
- PII、Voice Model、Rights metadataはSensitivity/Retentionを定義する。
- External providerはlocal/private endpoint、explicit authorization、request-bound idempotency、output containmentを満たす。
- 外部GPL実装（Audacity OpenVINO / Spectrum等）はBAI CoreへコピーせずRuntime境界で扱う。

## Current Consumer Task State

- Last Completed Gate: `TASK-046 P-VS-0 documentation-only intake`; PR #90 exact head `664722d0fac8cc0e79f7c424c6911f4651ceb303` passed hosted `9 / 9`, merged at exact main `25e2e04fb3360af77017a4a42e868fc95b15ec80`, and passed post-merge main CI/Security
- Active Task: `TASK-036 / P-UX-1C V6.1.1 NATIVE PARITY CLOSURE / codex/task-036-v611-packaged-native-closure`; WIP is protected by `BVP-LOCK-TASK036-PUX1C` and resumes only after the hosted Lock Registry and exact `WIP_FILE_SHA256.txt` match are verified
- Parallel Reserved Task: `TASK-046 / P-VS-1A BODY-FREE VOICEPROFILE BACKEND / codex/task-046-p-vs-1a-body-free-backend`; implementation may start only from fresh main under `BVP-LOCK-TASK046-PVS1A`, and main merge waits for P-UX-1C hosted closure plus fresh-main rebase
- TASK-004: `COMPLETED`
- Package: `0.21.0`
- Release State: `FORMAL_RELEASE_COMPLETE`; stable GitHub Release `v0.21.0` targets exact release-code main SHA `c38187ed54e3601c44411d9b8a128348b0d8a7b7`
- Development Candidate: `NONE`; no post-0.21.0 candidate is selected
- Current release verification: PR #77 passed hosted `9 / 9`; annotated Tag object `93305adaa5b72c19d235264cd38e921c2ab81f62` dereferences to exact main `c38187ed54e3601c44411d9b8a128348b0d8a7b7`; Release workflow `31858212510` and published wheel/sdist digest plus clean-install verification pass.
- Target-machine Gate: `TASK-036 / M3B MINIMUM_EDITING_PRODUCT_MVP_PASS / FORMAL_RELEASE_COMPLETE`
- Project Roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` Ver.1.86 Addendum LXXX
- TASK-022: `COMPLETED`; package 0.5.0 native-Windows regression `263 / 263 PASS` and compileall PASS
- AI routing: package 0.6.2 native-Windows `293 / 293 PASS`; TASK-028 package 0.6.3 uses exact model capabilities rather than provider-purpose locking; GUI settings and remaining adapters are subsequent slices
- OSS readiness: package 0.6.4 adds public documentation, governance/community health files, cross-platform CI, dependency/secret scanning, packaging metadata and evidence-based impact guidance; the Repository is now public and hosted CI remains the final external gate
- Repository URL corrective: package 0.6.5 binds all public metadata and GitHub community links to `https://github.com/baisound/bai_video_production`; the first push and Security workflow succeeded
- CI corrective: package 0.6.6 provisions FFmpeg/ffprobe on every Ubuntu and Windows matrix runner before executing the media-dependent regression suite
- Python 3.11 CI corrective: package 0.6.7 replaces process-global OS mutation with explicit Audacity path-platform injection; five other matrix jobs already passed
- OSS adoption: package 0.7.0 adds truthful architecture/roadmap visuals, five-minute offline demo, guarded release/PyPI automation and Evidence gates for real video pilots, early adopters and contributors
- Connection settings: package 0.8.0 adds a secret-free five-workload preflight projection for the future low-literacy GUI; persistence and interactive UI have dated completion gates
- Settings persistence: package 0.9.0 adds atomic checksummed storage, revision-conflict protection, 0.8 migration and a bilingual GUI-neutral form; interactive UI remains due 2026-08-24
- Interactive settings: package 0.10.0 adds a loopback-only bilingual screen for five workload modes and preferred configured Models; native Windows screenshot and usability Evidence remain
- Native settings Evidence: package 0.10.0 Windows save/reload and stale revision 3 versus saved revision 4 conflict behavior accepted; multi-user usability review remains
- Catalog editor: package 0.11.0 adds safe Provider/Model candidate add/edit/disable with truthful implementation status and no Provider execution path
- Native Catalog Evidence: package 0.11.0 add/edit/disable behavior accepted on Windows
- Credential onboarding: package 0.12.2 links enabled credential-required Catalog candidates to active key rows, retains disabled-route keys in an explicit cleanup section, prevents orphaning, and provides per-Route password-manager lookup; Provider connectivity is not executed
- Native Credential Evidence: package 0.12.2 Catalog linkage, retained-key cleanup and per-row Password Manager behavior accepted on Windows
- Subtitle foundation: package 0.13.0 adds provider-neutral Transcript and Subtitle contracts, cut-aware exact frame mapping and deterministic SRT; real ASR and Resolve placement remain subsequent slices
- Subtitle Workspace release: package 0.16.4 completes the v0.16.x review-workspace line including local FasterWhisper/Transcript/SRT flow, revisioned subtitle editing, Windows-native Open/Save interaction corrective and runtime workspace privacy hygiene
- TASK-006 Slice D: v0.17.0 formal release completed with large-media chunk/checkpoint transcription and canonical Resolve subtitle-placement handoff; actual Resolve write remains TASK-010 ownership.
- Current bounded Product development: TASK-024 Slice A candidate `0.18.0` generates review-only silence/filler/exact-repeat Cut Candidates and protected Keep Blocks. It does not mutate media or Resolve; TASK-007 owns final Cut Plan and TASK-010 owns execution.
- R2/R3 route is complete. R4 TASK-013 now has a hosted-closed package-owned body-free local/free adapter, exact runtime-policy enforcement, no-replay recovery and opt-in trusted-launch composition. The current bounded unit adds an explicit read-only readiness preflight that checks node/model availability, resources and exact runtime identity while fixing dispatch, journal creation, execution authorization and Native Gate satisfaction to false. Native completion remains parked: attempt 01 failed in the real sampler path and attempt 02 was externally interrupted by the Owner-confirmed Windows force restart with durable `QUEUED / RECOVERY_REQUIRED`.
- R4 TASK-041 Audio Workspace Product promotion is hosted-closed: exact Production/audio snapshot binding, crash-safe CAS, one-shot Human placement decisions and the unified Desktop `音声` workspace passed PR #47 `9 / 9` and merged at exact main `8dd6434a`. It records review intent only and starts no Provider, paid call, derived-media write, TASK-026 compile, Resolve or Cubase operation.
- TASK-042 is the Owner-directed current highest-priority Product route. P-V6-0 merged through PR #49 at exact main `7be3de1a`; P-V6-1A passed PR #50 `9 / 9` and merged at exact main `694e9933`. P-V6-1B design PR #52 passed `9 / 9` and merged at exact main `cbf27b29`; its branch and design clone were removed before a fresh implementation clone was created.
- P-V6-1B implementation is hosted-closed. PR #53 exact head `c0df2e24eccf4ba4e854b73bbb3d711509199f35` passed all `9 / 9` checks and merged at exact main `5413a85bcbb0c66599a2650b281cb9f57b19d6a2`; its remote branch and dedicated implementation clone were removed. Proposal/GO/snapshot accept exact Blueprint v1/v2, the Windows EXE build contract and README AUTONOMY guide are on main. Closure Sync PR #54 exact head `89ce567503b22a5e851ad66407e0a57598e79d05` then passed `9 / 9`, merged at exact main `f5ad4cdfa564285e9fe7a5fcf4516f1b92cae0a4`, and completed branch/clone cleanup as cadence merge `1 / 2`.
- At the P-V6-2 design checkpoint, fresh-main Handoff Bootstrap and Autonomous Queue selected `BVP-TASK-042-P-V6-2-DESIGN / DESIGN_ONLY`; implementation was not started at that historical point. The current-main audit, DEV-4 re-decision, exact Allowed Files, Builder design and two Critic cycles completed before Design PR #55 became cadence merge `2 / 2`. The design reuses TASK-037 as the only Candidate/LOCK/STALE truth and keeps Native H3, Provider/paid execution and release operations parked.
- P-V6-2 Design PR #55 passed `9 / 9`, merged at exact main `6a4a6a5e28705950d0ba6457c38d9b8d119fe944`, and completed remote branch/dedicated clone cleanup. Fresh-main AUTONOMY selected `BVP-TASK-042-P-V6-2-IMPLEMENTATION / IMPLEMENTATION`. Exact TASK-037-backed WORLD LOCK projection, v2 Production Control/Planning/Trace, transitive STALE/restart recovery and v2 Queue proof passed Windows `960 / 960`; v1 remains compatible and implementation Critic is unresolved Critical/High `0 / 0`.
- P-V6-2 implementation is hosted-closed. PR #56 exact head `e3ab3dc3f32bfbad42f72a8d65c0d43b896f5fd3` passed `9 / 9` and merged at exact main `4c77ad08172de05cf07ba3374a879fafca4bf2fd`; its remote branch and dedicated implementation clone were removed. Fresh-main BAI Development OS Handoff Bootstrap selected the current checkout over the stale handoff, and Queue selected `BVP-TASK-042-P-V6-2-CLOSURE-SYNC / IMPLEMENTATION`. This documentation-only sync is cadence merge `2 / 2` when hosted; after cleanup control returns to AUTONOMY before P-V6-3. Stable release remains `v0.20.1`.
- Closure Sync PR #57 exact head `34bedb48591e713475b438f4b5074d581cd73fd2` passed `9 / 9`, merged at exact main `92ff6938b9def12161d8635048ad3714315ed9d4`, and completed branch/clone cleanup as cadence merge `2 / 2`. Fresh-main AUTONOMY then selected `BVP-TASK-042-P-V6-3-DESIGN / DESIGN_ONLY`. The current audit, DEV-4 re-decision, immutable Prompt/Provider projection/Quick authority design, P-V6-2 Queue persistence corrective, exact Allowed Files and two Critic cycles are local PASS. Implementation remains not started until this design is hosted-closed and reselected. Stable release remains `v0.20.1`.
- P-V6-3 Design PR #58 exact head `0067fcc8e306a1799ccc7afeeae2638b9bb19e3b` passed `9 / 9`, merged at exact main `c78ed0141b0849b3a5d1b2229b87c320697b4980`, and completed branch/clone cleanup as cadence merge `1 / 2`. Fresh-main AUTONOMY selected `BVP-TASK-042-P-V6-3-IMPLEMENTATION / IMPLEMENTATION`. Immutable Prompt compilation, secret-free Provider/Model readiness, append-only Quick intent CAS/restart/adoption projection and the v2 Queue persistence corrective are locally implemented with Critic unresolved Critical/High `0 / 0`; hosted implementation closure remains pending. No Provider/native/media/Candidate/Audit/Lock or release operation was started. Stable release remains `v0.20.1`.
- P-V6-3 Implementation PR #59 exact head `d33807287c7ccc86b5055bd6b4575c88b7e9d41b` passed `9 / 9`, merged at exact main `7ac291f1a572b5513ecb681d9c3e87ccc0e52f38`, and completed remote branch/dedicated clone cleanup as cadence merge `2 / 2`. Fresh-main AUTONOMY selected `BVP-TASK-042-P-V6-3-CLOSURE-SYNC / IMPLEMENTATION`; P-V6-4 Design is dependency-waiting until this docs-only sync is hosted. Stable release remains `v0.20.1`.
- P-V6-3 Closure Sync PR #60 merged at exact main `c6a5cb108032709615ab99856890d0a3709d7d5d` and completed remote branch/dedicated clone cleanup as cadence merge `1 / 2`. Fresh-main AUTONOMY selected `BVP-TASK-042-P-V6-4-DESIGN / DESIGN_ONLY`. The current-main audit, DEV-4 re-decision, Timeline-authoritative/SRT-conflict design, exact TASK-041 reuse, first-class ambience, Allowed Files and two Critic cycles are local PASS. Implementation remains not started until hosted design closure and fresh-main reselection. Stable release remains `v0.20.1`.
- P-V6-4 Design PR #61 merged at exact main `6784a44e6831daa2b3db8ff85e2abe7b197ba3de`. Under the replacement `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE` Directive, TASK-043 is now the prerequisite Project/migration/recovery foundation; TASK-042 P-V6-4 waits for it, TASK-044 owns practical NLE/Export Queue, and TASK-045 owns native compatibility/release closure. Stable release remains `v0.20.1`.
- TASK-043 P-FND-2 PR #64 passed hosted `9 / 9` and merged at exact main `3ba4df947ab2939ef7daed030a3ee69a3c31f07a`. P-FND-3 command history/Autosave/Backup now passes local focused `55 / 55`, full regression `1042 passed, 1 skipped` and compileall; hosted closure remains pending.
- TASK-043 P-FND-3 PR #65 passed hosted `9 / 9` and merged at exact main `19febe3e00de92b18948e93740a0e3080b63d1b1`. Final P-FND-4 durable Product Job/Export Queue foundation now passes local focused `90 / 90`, full regression `1061 passed, 1 skipped` and compileall; hosted closure remains pending.
- TASK-043 P-FND-4 PR #66 passed hosted `9 / 9`, merged at exact main `10eae32b2e6a2f9ad7080961fed7b3d2b39f423b` and completed branch cleanup. Fresh-main P-V6-4 implements frame-authoritative Timeline Audio, SRT conflicts, AMBIENCE, exact current TASK-037/041/026 proof and TASK-043 coordinated Project persistence. Focused `32 / 32` and full `1070 passed, 1 skipped` pass; hosted closure is pending.
- TASK-042 P-V6-4 PR #67 passed hosted `9 / 9`, merged at exact main `19f1a94f11a783f475141af015351f64aff1b7d8` and completed branch/checkout cleanup. Fresh-main TASK-044 audit/design splits practical NLE work into P-NLE-1 semantic projection, P-NLE-2 editing/history, P-NLE-3 Export Queue and P-NLE-4 Shell/UI/native acceptance; two Critic cycles close at `0 / 0` unresolved Critical/High. Design hosted closure is pending.
- TASK-044 Design PR #68 passed hosted `9 / 9`, merged at exact main `f8b901c143f6a4987cacb46429cf0caf85aa2ab7` and completed branch/checkout cleanup. Fresh-main P-NLE-1 implements frame-authoritative dynamic tracks/clips, exact selection/seek/Candidate-review separation, rational viewport projection and bounded 10,000-clip pages. Focused `42 / 42` and full `1083 passed, 1 skipped` pass; hosted closure is pending.
- TASK-044 P-NLE-1 PR #69 passed hosted `9 / 9`, merged at exact main `ab41b2105914488d1d96ca3b3f8997a09d53337a` and completed cleanup. P-NLE-2 exact-frame trim/snap/IN-OUT, append-only Timeline revision, CAS and compensating Undo/Redo then passed PR #70 `9 / 9` and merged at exact main `a6bb252f36f4d3a8aca0175eb35c0ab44a7b91e8`.
- TASK-044 P-NLE-4 PR #72 exact head `ac5b2956e0a0e881a4cf0a58f414eaab826c2fb2` passed hosted `9 / 9`, merged at exact main `6703c42a3aa06a563071f1a48dc7aab113f4dfe4` and completed remote branch/dedicated checkout cleanup. The dynamic Unified NLE Shell, per-job Export recovery, bounded 10,000-clip projection and packaged Windows interaction Evidence are hosted-closed. Browser automation remained unavailable and is not claimed.
- Fresh-main TASK-045 audit reclassified the release closure as three Atomic Units: P-RC-1 compatibility/migration/Asset paging, P-RC-2 integrated native/clean-install/restart acceptance, and P-RC-3 exact release finalization. Existing compatibility/recovery/NLE focused baseline is `94 / 94 PASS`; two Critic rounds close at unresolved Critical/High `0 / 0`. Exact SemVer remains undecided until P-RC-1/2 Evidence passes.
- TASK-045 Design PR #74 passed hosted `9 / 9` and merged at exact main `1ddc8ea39e45ee62590a443e3a67d8bb901b6062`. Fresh-main P-RC-1 implemented explicit legacy discovery, code-registered lossless copy-on-write migration with backup/reopen proof, additive schema v3 Asset keyset paging and a concurrent source-manifest pointer corrective; it was later hosted-closed by PR #75.
- TASK-045 P-RC-1 PR #75 passed hosted `9 / 9`, merged at exact main `402c8956a5f5f3ac485c43db2b3e35e667846a88`, and completed cleanup. P-RC-2 final candidate passes packaged synthetic Project open/reopen, Narrator/UIA, three displays, Timeline interaction, native picker cancel, conversation-free restart, clean install, Windows `1123 passed, 1 expected skip` and WSL2 `1124 / 1124`; exact release decision is `0.21.0 / v0.21.0 / stable`. It was hosted-closed by PR #76 as recorded next.
- TASK-045 P-RC-2 PR #76 final head `76644790b8e154014af7e46b5efeef49b3d58789` passed hosted `9 / 9`, merged at exact main `84837e34a42234e23a544f54c8fe0c49aab8cacb`, and completed branch/checkout cleanup. Fresh-main `release/0.21.0` now owns P-RC-3 metadata, regression, PR/main, exact SHA, annotated Tag and verified GitHub Release.
- TASK-045 P-RC-3 PR #77 final head `c5cdff27e7c0918efa37876c064dcfd5a3deae76` passed hosted `9 / 9`, merged at exact release-code main `c38187ed54e3601c44411d9b8a128348b0d8a7b7`, and completed remote release-branch/release-checkout cleanup. Annotated `v0.21.0`, formal stable GitHub Release, bounded Release notes, workflow `31858212510` and published-asset verification pass. Its later docs-only sync was hosted-closed by PR #78.
- TASK-045 post-release Evidence PR #78 head `8b3f59b0a966727c544a37465733659c6fb757d0` passed hosted `9 / 9`, merged at exact main `1956f6e04b0c6206f64333d719f41c567def0590`, and completed remote branch/dedicated checkout cleanup. Fresh-main AUTONOMY selected TASK-027 P-ORCH-1 output adoption design.
- TASK-027 P-ORCH-1 Design PR #79 passed hosted `9 / 9`, merged at exact main `4532bb29c0ace58c720016f7ec313bb2037788ea`, and completed remote branch/dedicated checkout cleanup. Fresh-main implementation now validates an exact initial completed local output, reuses TASK-003/037/040 canonical stores and ends at `READY_FOR_AUDIT`; focused Windows/WSL2 and full WSL2 regression pass locally. Provider replay, paid execution, Human ACCEPT/LOCK, publication and Native H3 remain false. Regenerated Prompt output remains parked until exact Strategy/Parent binding is persisted.
- TASK-027 P-ORCH-1 Implementation PR #80 exact head `0e3575a5bd11f8664409d03078b4ed0dc0b7e52b` passed hosted `9 / 9`, merged at exact main `66d97fd9d0bfbfebca339197fed2103011f56616`, and completed remote branch/dedicated checkout cleanup. Initial completed-output adoption is hosted-closed. The next safe audit candidate is the missing immutable regenerated-output Strategy/Parent Queue binding; it receives no implementation claim until fresh-main design/Critic authorization.
- TASK-027 P-ORCH-2 Design PR #82 passed hosted `9 / 9`, merged at exact main `1ed59286991ff70452b3f3602bc512b1fcd38ae4`, and completed cleanup. Implementation PR #83 exact head `633e85d7b0f817bfea4887a29c889bb2f2b98dcf` then passed hosted `9 / 9`, merged at exact main `a4d15f23d5781b515be6b2a228b491e696a5983f`, and completed remote implementation branch/dedicated checkout cleanup. Regenerated Strategy/Parent lineage is hosted-closed; this docs-only closure sync precedes fresh-main Product-wide AUTONOMY reselection.
- TASK-027 P-ORCH-2 hosted-closure PR #84 exact head `ab50e99261f05e3cf70211ee03cc77740ba901b6` passed `9 / 9`, merged at exact main `5e061fb5d7463c00ad893d28fdf0cbb9b480b1ba`, and completed cleanup. Fresh-main AUTONOMY selected TASK-026 P-AUDIO-1 after proving the compiler/binding foundation already exists but durable Product/Shell integration does not.
- OS-internal TASK-016 remains unrelated and untouched.

## Completion Rule

Taskは、選択DEV Profileの要求、実装、必要Test、blocking finding解消、内部文書同期、Completion Evidenceが揃った場合のみ完了する。

Local Test PASSやCapability PASSを、まだ未実施のBehavioral EvidenceまたはOwner Authorization for later TASKへ読み替えない。

## Registered Product Design Knowledge

- `BVP-KNOWLEDGE-REFIMG-001 — Scene-Compatible Reference Image Design Rule` is formally registered from the Product Promotion workflow.
- Remaining Scene-Compatible Reference slices remain owned by `TASK-013`; this registration does not authorize those unimplemented slices or reopen TASK-004. The separate R3 Shot Feasibility / Visual Compliance Product promotion is already complete.
- Required future Gate: `SHOT FEASIBILITY / SCENE-COMPATIBLE REFERENCE` before generated Start/End Frame production.
- `DIRECT_CONTINUATION` requires exact previous-End Asset reuse rather than perceptually similar regeneration.

## Non-Negotiable Product Goal — Unified Desktop Application

Canonical invariants:

- `UNIFIED_DESKTOP_APPLICATION_REQUIRED`
- `SINGLE_USER_FACING_ENTRYPOINT_REQUIRED`
- `CAPABILITY_UI_INTEGRATION_REQUIRED`

BAI Video Production の最終Productは、機能ごとに別々のアプリ・CLI・localhost Web UIをユーザーが個別起動する集合体ではない。

最終ユーザーは **BAI Video Production.exe** を1つのProduct entrypointとして起動し、Project / Media / Edit / Subtitle / Audio / Generative AI / Review / QA / Export / External NLE Integrationを同一Desktop Application Shellから横断して扱えること。

内部Service、Worker、Provider、CLI、local HTTP service、WebView、GPU worker、adapter processは許可する。ただし通常ユーザーにterminal、localhost URL、PID、port、Python environment、worker lifecycleの手動管理を要求してはならない。

CLI / localhost Web UI は `DEVELOPER_DIAGNOSTIC_INTERFACE` または `TRANSITIONAL_INTERNAL_UI` として残せるが、User-facing Capabilityの最終UXをそれだけで完了扱いしてはならない。

User-facing / Operator-facing Taskの詳細設計には `Unified Application Integration` を必須とし、User Entry Point、Shell/Workspace Location、Project/Asset context、progress/success/failure、Open/Save、review/approval、worker lifecycle、recovery、external app interaction、native Windows acceptanceを定義する。

Capability integration state:

- `BACKEND_CAPABILITY_ONLY`
- `INTEGRATION_DESIGNED`
- `SHELL_INTEGRATED`
- `NATIVE_VALIDATED`

Backend capability completionとUnified Desktop UX completionを混同しない。

Canonical details:

- `docs/ai-team/architecture/PRODUCT-ARCH-001-unified-desktop-application.md`
- `docs/ai-team/architecture/UNIFIED-APPLICATION-INTEGRATION-CONTRACT.md`

## TASK-007 / 010 / 011 / 012 Technical MVP Candidate

- TASK-007 compiles TASK-024 review-only candidates into a deterministic human-approved Edit Plan.
- TASK-010 compiles that plan through TASK-022 and can write only an Automation-owned `BAI_AUTO_*` Resolve Timeline after explicit external-write authorization; source/normalized FPS is mandatory for source-frame conversion.
- TASK-011 verifies rendered artifacts using checksum, media/duration checks and configurable loudness/true-peak policy.
- TASK-012 creates deterministic QA-gated `EDITOR_WORK_*` handoff packages and a bounded 48 kHz PCM Cubase return contract.
- The original backend slice reached `INTEGRATION_DESIGNED`; TASK-036 v0.20.1 now makes the accepted TASK-007/010/011/012 route `SHELL_INTEGRATED / NATIVE_VALIDATED`.
- Historical `0.20.0` release-candidate metadata completed its release route and was superseded by the formal stable `v0.20.1` release. Later R2-R4 development on current main is integrated development and does not claim a newer Product release.

## TASK-023 Completed Bounded Development

- Route: `DIRECT_FORWARD`.
- Existing TASK-006 `FasterWhisperProvider` remains the only canonical local ASR provider.
- TASK-023 adds deterministic execution identity and model-free/path-minimized reconciliation evidence only.
- `PRODUCT-ARCH-001` integration target is `BAI Video Production.exe -> Subtitle Workspace`.
- The original 0.19.0 slice was `INTEGRATION_DESIGNED`; TASK-036 v0.20.1 now integrates this accepted local ASR route into the Shell.
- The CLI is `DEVELOPER_DIAGNOSTIC_INTERFACE`, not final Product UX.
- Recognition output semantics, Transcript/SRT contracts, word timestamps and final transcript-result caching are unchanged.
- Final validation: `444 passed, 1 intentional skip`; compileall/diff-check PASS; Windows real-media diagnostic evidence PASS with no model load, inference, network use, source/cache path leakage, or transcript-text leakage.
- Final TASK-023 capability state remains `COMPLETE`; TASK-036 W2 supplies the later `SHELL_INTEGRATED / NATIVE_VALIDATED` Product Evidence.
