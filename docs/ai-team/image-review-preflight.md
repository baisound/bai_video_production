# Image Review Preflight

Status: `CURRENT`

## 1. Mandatory timing

This standard applies to every Codex task that inspects a screenshot, image attachment, rendered page, application window, visual QA artifact, or image sequence.

Before opening or evaluating the first image, Codex must:

1. read this document;
2. identify the exact screen, state, or claim the image is expected to prove;
3. identify which content and controls must be visible or reachable for that claim;
4. use the `PASS` / `FAIL` / `NOT_CONFIRMED` rules below.

Reading this standard after a visual verdict has already been issued does not satisfy the preflight.

## 2. Per-image inspection

Inspect and record each image independently before producing an aggregate result.

For every image:

1. Confirm whether the capture contains the full relevant application viewport or is cropped.
2. Inspect all four viewport edges for clipped text, cards, controls, dialogs, overlays, or continued content.
3. Check for overlap, truncation, hidden controls, blank regions, crash dialogs, and layout breakage.
4. If content continues beyond the viewport, verify an actually observed way to reach it, such as a visible scrollbar or a separately executed and observed scroll, keyboard, resize, or responsive-layout action.
5. Do not infer reachability from expected framework behavior, page length, another screen, or the presence of content above the fold.
6. Separate these conclusions:
   - content was rendered;
   - required content and controls are reachable;
   - the interaction was executed successfully;
   - safety, privacy, and authority state is correct.
7. Check for unintended exposure of secrets, private paths, internal-only identifiers, debug data, or unauthorized execution state.

A selected navigation item, correct title, or repeated safety label does not prove that the rest of the screen is complete or usable.

## 3. Result rules

Use only these top-level technical results:

- `PASS`: the image and any required observed interaction prove the exact claim, including reachability of all required content and controls.
- `FAIL`: the image proves a defect or contract violation. Clipped required content with no available or proven reachability mechanism is `FAIL`.
- `NOT_CONFIRMED`: the capture is incomplete, cropped, ambiguous, or does not prove reachability or the required interaction.

Never promote `NOT_CONFIRMED` to `PASS` by assumption. Never report an entire set of screens as `PASS` merely because their shared elements look consistent.

## 4. Multiple images

For an image batch:

1. assign findings and a result to each image;
2. compare common elements only after the per-image review;
3. give the batch the most conservative result required by the acceptance claim;
4. keep localized failures distinct so unrelated safe checks may continue.

A long or scrollable screen requires its own reachability proof even when shorter sibling screens pass.

## 5. Contradiction and correction

If the user or later Evidence identifies a visual problem that conflicts with an earlier verdict:

1. stop advancing the affected visual acceptance step;
2. reopen and reinspect the original image;
3. correct the verdict explicitly;
4. state the missed visible evidence and why it was missed;
5. apply the corrected inspection rule to the remaining images.

Do not defend or preserve an earlier `PASS` when the image does not support it.

## 6. Minimum review record

Keep a concise record containing:

- image identity;
- expected claim;
- viewport completeness;
- edge and overflow result;
- required-content reachability;
- safety/privacy result when applicable;
- technical result;
- findings and unresolved evidence gaps;
- next safe action.
