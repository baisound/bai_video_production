# TASK-054 R4B Narration Intake Contract Design

R4B is a DEV-3 pure candidate contract. It binds one R4A rights-manifest
coordinate to exact media ranges, ASR/diarization revisions, pseudonymous speaker,
CGEL Event/Context coordinates, Human review and commentary role. It stores only
the Human-reviewed redacted transcript; the original transcript is retained by
digest, not duplicated as unreviewed text.

Roles are PLAY_BY_PLAY, ANALYSIS, TACTICAL, REACTION, TRANSITION, FILLER and
UNCERTAIN. Uncertain/quality issues remain NEEDS_REVIEW; rights, Consent, PII/secret
or unsupported tactical failures are REJECTED. State is permanently
`CANDIDATE_ONLY_NO_ADOPTION`. This unit performs no ASR, diarization, media I/O,
Dataset adoption, training, Provider execution or voice learning.
