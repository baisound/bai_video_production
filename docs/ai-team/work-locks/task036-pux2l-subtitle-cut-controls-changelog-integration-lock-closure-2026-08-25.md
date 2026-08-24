# TASK-036 P-UX-2L CHANGELOG Integration Lock Closure

Date: 2026-08-25

Lock: BVP-INTEGRATION-LOCK-TASK036-PUX2L-SUBTITLE-CUT-CONTROLS-CHANGELOG-20260825

Status: HOSTED_CLOSED_RELEASED (authoritative only after merged-main read-back)

## Hosted transaction

- lock-host PR: #308
- lock-host head: ea206e387d0793e9db33d84e4860117e9ecf3096
- lock-host merge: 497de9803adff384ef48a4acfddba6023e3fad2a
- lock-host hosted checks: 9 / 9 PASS
- lock-host post-main CI: 32766000548 / PASS / 6 of 6
- lock-host post-main Security: 32766000563 / PASS
- target PR: #306
- target pre-integration head: 5fff7aed46c499e7b357d419968eb82e2c9a90c5
- target final head: e1479cfdb3442a14c838181149d1eb39174d7c20
- target merge: 0197c0c7ac1428a19bd08261fd410baa63675632
- target hosted checks: 9 / 9 PASS
- target pre-merge CI: 32767301407 / PASS
- target pre-merge release metadata: 32767301424 / PASS
- target pre-merge Security: 32767301441 / PASS
- target post-main CI: 32767840161 / FAIL / Windows 3.12 Node harness timeout only
- target post-main Security: 32767840260 / PASS

## Approved CI repair

- repair PR: #310
- repair head: 4cb38661510f1fc263164817e7e2b9f20a6d41e3
- repair merge / closure preimage main: d090973ff9f3d5f3a6aae7ff49059bc9498e6461
- repair scope: exact test-local Node timeout boundary plus TASK-036 Evidence; Product and workflow unchanged
- repair hosted checks: 9 / 9 PASS
- repair pre-merge CI: 32771058908 / PASS / Windows 3.12 PASS
- repair pre-merge release metadata: 32771058942 / PASS
- repair pre-merge Security: 32771058927 / PASS
- repair post-main CI: 32771823377 / PASS / 6 of 6
- repair post-main Security: 32771823235 / PASS
- unchanged-head retry: not performed

## Exact read-back

- target changed files: exactly 16 (15 implementation/test/Evidence paths plus one approved CHANGELOG file)
- approved TASK-036 P-UX-2L CHANGELOG bullet: exact 1
- original immutable target blobs: 14 of 15 exact pre-integration blobs preserved
- controlled successor: one test harness blob was intentionally superseded by approved repair PR #310 and is post-main green
- Product implementation blob drift: 0
- registry revision: 69 -> 70
- registry status: HOSTED_CLOSED_RELEASED
- integration effect authority: AUTHORIZED_SCOPE_CONSUMED_CLOSED
- target merge authority: OWNER_MERGE_COMPLETED_CLOSED
- target PR state: MERGED_POST_MERGE_GREEN_AFTER_PR310_CI_REPAIR
- open PR #270/#273/#307/#311 CHANGELOG or Registry overlap: 0
- nonclosed integration locks after closure: 0

Original target blob read-back:

| Path | Pre-integration blob | Closure-main blob | Result |
|---|---|---|---|
| docs/ai-team/tasks/TASK-036/p-ux-2l-recovery-checkpoint-2026-08-24.md | 3d541b7d00b78f00f2d20afaa89c25fef46fddcf | 3d541b7d00b78f00f2d20afaa89c25fef46fddcf | PRESERVED |
| docs/ai-team/tasks/TASK-036/p-ux-2l-recovery-completion-2026-08-25.md | 628d712d0b95a01da96d341f96a56c4ee09dc59c | 628d712d0b95a01da96d341f96a56c4ee09dc59c | PRESERVED |
| docs/ai-team/tasks/TASK-036/p-ux-2l-subtitle-cut-controls-design-2026-08-24.md | 0c77d8cbf35603756f280bcdccc242aacc763f78 | 0c77d8cbf35603756f280bcdccc242aacc763f78 | PRESERVED |
| src/ai_video_production/desktop_editing_application.py | deeb8c9405d005e7530dbbcbbe9c57246ba5cf6b | deeb8c9405d005e7530dbbcbbe9c57246ba5cf6b | PRESERVED |
| src/ai_video_production/desktop_editing_coordinator.py | cc076a27c9b8c78013ced41b77fa2cfb5d15b5b6 | cc076a27c9b8c78013ced41b77fa2cfb5d15b5b6 | PRESERVED |
| src/ai_video_production/desktop_pre_edit_binding.py | 114d2fdaed5b37810bc9becaae6103f19edb8a9b | 114d2fdaed5b37810bc9becaae6103f19edb8a9b | PRESERVED |
| src/ai_video_production/desktop_shell.py | bcc4d633fa25adc1f1f0a65d860ba1ac1aa27c7a | bcc4d633fa25adc1f1f0a65d860ba1ac1aa27c7a | PRESERVED |
| src/ai_video_production/task036_pre_edit_runtime.py | a7514f05c25ce6b6ac53779c54dba187f81b2b15 | a7514f05c25ce6b6ac53779c54dba187f81b2b15 | PRESERVED |
| src/ai_video_production/task036_shell_ui.py | 21b878f3c8adda5bfce0d3bb2b4b49d5744691dd | 21b878f3c8adda5bfce0d3bb2b4b49d5744691dd | PRESERVED |
| src/ai_video_production/task036_shell_v611.py | 56603441b05b5c3ebb488ae38117f12b39a9c80c | 56603441b05b5c3ebb488ae38117f12b39a9c80c | PRESERVED |
| src/ai_video_production/task036_trusted_launcher.py | 8dbbc4c13a430dea6540e613d8c2d0b75357a9a5 | 8dbbc4c13a430dea6540e613d8c2d0b75357a9a5 | PRESERVED |
| tests/test_task036_pre_edit_runtime.py | a0273a19fb407899bdc6780075fe515ef8bfc4a7 | a0273a19fb407899bdc6780075fe515ef8bfc4a7 | PRESERVED |
| tests/test_task036_shell_ui.py | a65c7f81bb463f394b5e4f0cde8f91fb7e6ca9f0 | a65c7f81bb463f394b5e4f0cde8f91fb7e6ca9f0 | PRESERVED |
| tests/test_task036_trusted_launcher.py | 967dfe73d19a0d75311dcc74010af7884620cbe3 | 967dfe73d19a0d75311dcc74010af7884620cbe3 | PRESERVED |
| tests/test_task036_v611_interaction_contract.py | 921b6a4f85cab18138238bc92007345a0f84e078 | 0c00ed72b2d92aaf040d48dc4a2c1b83e931a23d | CONTROLLED_PR310_TEST_HARNESS_SUPERSESSION |

## Closure boundary

The shared CHANGELOG reservation is released after this closure is merged and read back from main. The timeout repair does not mint Product truth or weaken behavioral assertions; a non-terminating Node process still fails closed at the bounded 30-second test-local boundary and before the outer 120-second pytest timeout.

No Provider, model download, paid or Cloud call, media operation, Resolve mutation, render, native GUI, Owner media use, external Export dispatch, Release, Deploy, or Production effect occurred.

Unresolved Critical/High/Medium/Low findings: 0 / 0 / 0 / 0.

Judge: ACCEPT_CLOSURE_PROPOSAL_PENDING_HOST_MAIN_READBACK.
