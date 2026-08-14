# BAI VIDEO PRODUCTION — V6.1.1 UX / Interaction Requirement Contract
Status: `HANDOFF_REQUIREMENT_INPUT / REVALIDATE_BEFORE_CANONICAL`
Date: `2026-08-14`

This file records the known UX requirements that must not be lost during detailed design.

---

# 1. Scene Design / Start-End

Lock bindings are per Start and End.

Start and End each have:

- Character Lock: multiple
- Space Lock: one
- Composition Lock: one

Start and End may be different.

Examples:
- 1 person -> 4 people
- indoor -> outdoor
- door-facing camera -> exterior-view camera

Scene-level Narration / Music Direction / SE Intent / Ambience Intent feed AI Video prompt composition where applicable.

---

# 2. AI Video

Order:

```text
BGM生成 | SE生成 | 環境音生成
AI校正
Prompt
```

Reason: checkbox state affects the generated runtime Prompt.

AI Proofreading ON:

```text
Japanese Source
→ normalized Japanese
→ English runtime prompt
```

The English prompt is normally submitted to the model.

Provider and Model are dependent selectors.

---

# 3. Edit

Left and right panel headers must never start clipped.

Timeline:
- Ruler click moves Playhead.
- Ruler drag scrubs Playhead.
- Playhead can be dragged.
- Empty lane click can seek.
- horizontal scroll moves the viewed time range.
- generic Clip click selects Clip but does not move Playhead.

Do not blindly apply generic Clip semantics to the existing Cut Candidate review overlay.

---

# 4. Export

Export Queue exists.

Each item:
- progress bar
- percentage
- state
- execute

Global:
- Execute All Queue

Detailed design adds safe stop/cancel/remove/recovery/STALE semantics.

---

# 5. Quick Generate

Tabs:
- Image
- Start/End
- Video
- Audio

Image:
- multiple reference images

Start/End:
- multiple reference images
- Character/Space/Composition Lock controls

Video:
- Start image 1
- End image 1
- Negative Prompt

Audio:
- Negative Prompt
- reference input where supported

Reference input sources:
- File
- Asset Library
- Generation Results

Lock controls exist only in Start/End Quick mode.

---

# 6. Settings

AI Model:
- Provider selector
- Model selector
- only compatible models shown

Secret:
- all supported adapters listed vertically
- show registration/readiness state
- secret values are not redisplayed

---

# 7. Top menu

Must have concrete commands rather than empty headings.

Menu groups:
- File
- Edit
- View
- Project
- Generate
- Export

The exact command IDs and authority are detailed-design outputs.

---

# 8. Mock limitations

The included V6.1.1 HTML is an interaction/reference artifact.

Previous mock work demonstrated that:
- syntax PASS can coexist with runtime scope defects;
- layout math can still clip tab headers;
- Playhead can visually exist while using incorrect coordinate math;
- scroll/ruler synchronization can be wrong.

Therefore no mock audit replaces actual browser/native acceptance.
