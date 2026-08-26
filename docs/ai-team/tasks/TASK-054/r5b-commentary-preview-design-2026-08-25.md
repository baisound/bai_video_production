# TASK-054 R5B Time-aligned Commentary Preview Design

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `IMPLEMENTED / LOCAL EVIDENCE`

## Atomic Unit

Project already-validated Commentary Candidates from one canonical TASK-049
Game Intelligence analysis export into a read-only, time-aligned Operator
preview. Provide the reusable Japanese Tk presentation surface consumed by R5C.

## Responsibility boundary

- TASK-049 remains owner of Game Match, canonical Event frame ranges, exact
  source rate and validated Commentary Candidate storage/export.
- R5B converts admitted end-exclusive frames to display milliseconds using the
  exact rational source rate. It does not create or confirm an Event.
- The preview renders existing validated outputs only. It does not call a model,
  Provider, TTS or media analyzer. R5C owns the later status/execute/review
  connection to an approved or baseline path.
- `PREVIEW_NO_LEARNING` is fixed. Dataset, Binding, training, Provider,
  Production Timeline and Resolve mutation flags are all false.

## Admission and failure behavior

The compiler requires the exact TASK-049 analysis-export envelope, verifies its
canonical digest and side-effect flags, then verifies exact Match/Event fields,
nested canonical digests and each Commentary Candidate through the public
read-only Candidate admission boundary. Cross-Match data, duplicate Event
revisions, multiple Candidates for one Event revision, orphan Candidates,
unknown fields, oversized inputs and blocks outside video duration fail closed.

Only CONFIRMED Events with `AUTO_ACCEPTED`, `HUMAN_APPROVED` or
`HUMAN_CORRECTED` review status produce blocks. An empty result is explicitly
`NO_VALIDATED_COMMENTARY`, not success with hidden content.

## Operator presentation

The reusable panel displays:

- exact start/end time;
- `実況 / 解説 / 戦術 / 反応` category labels;
- Commentary text;
- Event confidence and `VALIDATED` state;
- previous/next and `前後10秒` navigation;
- `解説あり / 解説なし` text/timing comparison.

Selecting a row invokes a supplied media-seek callback. TTS is explicitly shown
as a separate Gate; R5B does not imply synthesized-audio playback. The footer is
permanent: learning data unchanged, model unchanged and no automatic learning.

If the Operator selected a local video without a canonical Asset binding, the
preview remains `NOT_CONFIRMED_MEDIA_IDENTITY`. It may assist review but cannot
be represented as identity-confirmed Evidence.

## Acceptance

- exact 30000/1001 frame-to-millisecond conversion is tested;
- canonical and packaged schemas are byte-identical and validate the report;
- nested tampering, unknown fields, orphan/duplicate Candidates and duration
  crossing fail closed;
- empty and unverified-media states are explicit;
- Japanese controls and safety footer are present;
- direct TASK-049/R5A focused tests and targeted regression pass;
- unresolved Critical/High findings are zero.
