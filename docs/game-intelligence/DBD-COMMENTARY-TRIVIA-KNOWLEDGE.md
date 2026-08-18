# DbD Commentary Trivia Knowledge

TASK-049 includes a separate store for useful DbD commentary facts, practical tips, historical notes, and "豆知識".

## Why it is separate

`Perk/Killer/Power Knowledge` stores canonical game facts. `Trivia Knowledge` stores reusable commentary knowledge that may be useful but should not automatically become an official fact.

```text
Manual entry / past commentary / transcript
-> CANDIDATE
-> Human review
-> VERIFIED
-> patch-compatible retrieval
-> Commentary Planner
-> LLM draft
-> Fact Validator
```

Only VERIFIED trivia is automatically eligible for commentary reuse.

## Manual registration

Use the dedicated **BAI DbD Trivia Editor** Windows application. Build and usage instructions:

- [Build BAI DbD Trivia Editor EXE](../windows/BUILDING-DBD-TRIVIA-EDITOR-EXE.md)
- [BAI DbD Trivia Editor Usage](../user/DBD-TRIVIA-EDITOR-USAGE.md)

The broader [BAI DbD Training Studio](../user/DBD-TRAINING-STUDIO-USAGE.md) can also register one Trivia item, import CSV one/many, mine an existing TranscriptManifest, or transcribe an owned/permitted video locally with FasterWhisper and create conservative `CANDIDATE` entries. Video mining never auto-verifies Trivia.

Fields include:

- title;
- trivia text;
- category/tags;
- related event types;
- related entity refs such as `perk_*`, `killer_*`, `power_*`;
- LIVE/PTB/environment;
- game-version range;
- source reference;
- Candidate/Verified status.

If the user is personally asserting and reviewing a manual fact, the editor can register it as VERIFIED. Otherwise keep it CANDIDATE until reviewed.

## Automatic candidate capture from commentary

The `TriviaCandidateMiner` can scan existing commentary/transcript sentences for bounded trivia-like cues such as "ちなみに", "実は", "豆知識", Perk/Killer terms, etc.

Extracted statements are **always CANDIDATE**. They are never automatically promoted because a commentator can be mistaken or speaking about an old patch.

The same miner also accepts canonical ASR `TranscriptManifest` segments. Segment-level provenance is retained as `transcript://<asset-id>/<segment-id>`, so a reviewer can trace which utterance produced the candidate. The manual Trivia Editor can also import `.srt` directly.

## Commentary use

For a confirmed CGEL event, the planner can retrieve trivia by:

- event type;
- Perk/Killer/Power entity refs;
- tags;
- LIVE/PTB environment;
- patch-compatible version range.

Verified trivia becomes an allowed `TRIVIA` claim in the Commentary Plan. The LLM may phrase it naturally, but the deterministic Fact Validator rejects facts not present in the plan.

## Update and correction

Do not edit history in place. New review creates a new trivia revision.

Recommended flow:

```text
CANDIDATE r1
-> VERIFIED r2
-> later patch makes it obsolete
-> SUPERSEDED r3
-> new corrected trivia r1/new entry or revised source record
```

## What should not be stored as verified trivia

- unverified rumors;
- exact numeric effects with no patch/source evidence;
- player accusations;
- personal/private data;
- copyrighted long-form text copied wholesale;
- tactics stated as universal truth when they are situational.

Use wording that separates factual mechanics from tactical interpretation.
