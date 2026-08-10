# TASK-032 Native Windows UI Evidence

- Package version:
- Date/time and timezone:
- Windows version:
- Browser and version:
- Reviewer identifier (anonymous):

## Safety precondition

- [ ] No API key or secret is visible in the browser, terminal, screenshot or attached Evidence.
- [ ] Reviewer understands that Save does not start generation or billing.
- [ ] Synthetic/example Profile is used; private production media is unnecessary.

## Scripted tasks

| Task | Expected result | Result | Notes |
|---|---|---|---|
| Start with `run-ai-connection-settings.ps1` | loopback URL opens; safety notice visible |  |  |
| Set Planning to `OFFLINE_ONLY` and choose a local Model | explanation updates; selection is keyboard operable |  |  |
| Save | success says generation did not start; revision increases |  |  |
| Reload browser | saved values remain |  |  |
| Open a second tab, save the first, then save the stale second tab | conflict appears; newer settings are not overwritten |  |  |
| Stop with `Ctrl+C` | local server stops |  |  |

## Required screenshot set

1. Full settings screen with the safety notice and at least two workload cards.
2. Successful save message and increased revision.
3. Stale-tab conflict message.

Redact usernames, local paths, credential references and unrelated browser content before submission. Do not edit the Product UI itself to manufacture a passing result.

## Review outcome

- [ ] PASS
- [ ] PASS WITH FOLLOW-UP
- [ ] BLOCKED

Observed confusion or accessibility blockers:

Suggested improvement:
