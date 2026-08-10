# TASK-030 — OSS Public Repository Readiness

- Status: `IMPLEMENTED_AWAITING_GITHUB_CI`
- Package: `0.6.6`
- Scope: public documentation, governance, community health, CI/security automation, packaging metadata, structural regression tests

## Outcome

The repository now has a truthful public entry point, MIT license, contribution and conduct rules, vulnerability reporting policy, governance/support/release records, third-party notices, citation metadata, GitHub issue/PR templates, cross-platform CI, dependency auditing, secret scanning and dependency update automation.

Package 0.6.5 corrects the canonical hosted repository URL to `https://github.com/baisound/bai_video_production` across badges, package metadata, citation and community links, and adds a regression test for that identity.

Package 0.6.6 corrects the first hosted CI run: all six Python/OS jobs reached pytest, but 66 media normalization tests failed because neither `ffmpeg` nor `ffprobe` existed on a fresh runner. CI now provisions and verifies both executables before installing and testing the package.

The README describes the intended public value: reducing the technical and financial barrier to safe video production while retaining human control, provider choice, rights/provenance and reproducibility. It explicitly labels this as an Alpha-stage objective rather than claiming demonstrated adoption.

## Non-goals

- This task does not make a GitHub repository public or change hosted repository settings.
- It does not claim Codex for OSS acceptance.
- It does not invent users, stars, usage, savings, or community impact.
- It does not complete the end-user GUI or production E2E route.

## Completion gates

- Local test suite and compileall pass.
- GitHub Actions pass after publication.
- Maintainer verifies public profile/repository, security reporting and branch rules.
- Application claims are backed by public, reproducible evidence.
