# OSS Adoption and Impact Plan

## Objective

Convert intended social value into public, reproducible evidence without inflating users, downloads, savings, quality, or safety claims.

## Workstreams

| Workstream | Implemented now | Evidence gate |
|---|---|---|
| GitHub releases | Manual, tested Release workflow | Release URL and attached wheel/sdist |
| Architecture communication | Rendered README architecture and roadmap | README visible to signed-out visitor |
| Five-minute demo | Credential-free deterministic CLI | Fresh clone completes and JSON validates |
| Real video pilot | Measurement protocol | One completed non-sensitive video and before/after record |
| Early adopters | Consent-based anonymized template | 2–3 independent installations with no invented claims |
| Contributors | Good-first-issue form and guide | External issue/PR/review/merge history |
| PyPI | Trusted-publishing workflow | Maintainer configures PyPI environment and first release succeeds |
| Discussions | Maintainer enables GitHub Discussions | Public category links and moderation owner |
| Repository metadata | Canonical description/topic recommendation | Public settings verified |
| Monthly cadence | Monthly readiness issue automation | Maintainer-approved release or documented no-release decision |

## Real video measurement protocol

Record before work begins:

- input duration, format and rights status;
- intended output and quality acceptance criteria;
- operator experience and hardware/runtime versions;
- baseline manual steps and active human minutes.

Record after work completes:

- automated and manual elapsed time separately;
- proposals accepted, rejected and revised;
- generated/replaced assets and external cost;
- retries, resumptions, failed operations and recovery result;
- final human corrections and whether the output was publishable;
- privacy/rights exceptions and unresolved limitations.

Do not publish source media, personal data or provider credentials as Evidence.

## Anonymous adopter record

Each adopter must consent to publication of an anonymized aggregate. Record only:

- broad role (`creator`, `educator`, `nonprofit`, `small business`, `developer`);
- OS and installation outcome;
- workflow attempted and completion state;
- time/cost range rather than identifying detail;
- most valuable capability and blocking limitation;
- permission scope and withdrawal contact held privately.

Two or three records are a learning sample, not proof of broad adoption.

## Recommended repository metadata

Description:

> Provider-neutral, auditable automation for safe AI video production and DaVinci Resolve workflows.

Topics:

`ai-video`, `video-editing`, `davinci-resolve`, `ffmpeg`, `python`, `comfyui`, `openvino`, `generative-ai`, `media-pipeline`, `open-source`

## Release policy

A monthly check is mandatory; a monthly binary release is not. If no user-visible, safe, verified increment exists, close the readiness issue with a reason instead of manufacturing a release. Every release requires green CI/Security, synchronized version metadata, changelog, demo verification and explicit Maintainer approval.
