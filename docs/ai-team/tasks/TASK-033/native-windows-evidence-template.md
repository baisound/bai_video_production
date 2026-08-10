# TASK-033 Native Windows Catalog Evidence

- Package version: `0.11.0`
- Date/time and timezone:
- Browser/version:

## Safety

- [ ] Use example identifiers only; do not enter an API key, token, password, endpoint URL, username, or private media.
- [ ] Confirm the page states Catalog registration does not imply an implemented Adapter.

## Script

1. Open `Provider・Model候補 / Provider & model catalog`.
2. Add `demo-video-route` for `VIDEO`, family `OTHER`, Provider `demo-provider`, Model `demo-model`, cost `LOCAL_FREE_AI`, Reasoning `none`, Capability `TEXT_TO_VIDEO`, Credential unchecked, Enabled checked.
3. Confirm it appears as `PLANNED_ADAPTER` and becomes available in the Video preferred-Model list.
4. Edit its Model to `demo-model-v2`; save and reload.
5. Edit it again, clear Enabled, save and reload; confirm the Catalog retains it as disabled.
6. Confirm every save says that execution/billing did not start.

## Required screenshots

1. Completed add/edit form before save, with no secret data.
2. Candidate list showing `PLANNED_ADAPTER` after save.
3. Same candidate retained with `DISABLED` after edit and reload.

## Result

- [ ] PASS
- [ ] PASS WITH FOLLOW-UP
- [ ] BLOCKED

Notes:
