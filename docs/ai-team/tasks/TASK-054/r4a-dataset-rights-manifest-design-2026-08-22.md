# TASK-054 R4A Dataset Rights/Provenance Manifest Design

Date: 2026-08-22

Status: `BOUND_FOR_IMPLEMENTATION`

Development depth: `DEV-3 HIGH ASSURANCE`

R4A owns only a body-free, immutable manifest of Dataset candidate coordinates,
rights, consent and provenance. It reuses R2D `CAND-R2D` Candidate identity and
the canonical Game Match identity. It does not own transcript/media bodies,
Dataset storage/adoption, split generation, training, evaluation or Provider use.

Every source, rights, consent, provenance and Human review reference is a fixed
namespace plus SHA-256 opaque identity. Public availability is not training
permission. An entry is eligible only when rights are explicitly admitted and
consent is explicit or canonically not required for non-personal material.
Unknown states need review; rejected or revoked states are rejected.

The manifest state is permanently `CANDIDATE_ONLY_NO_ADOPTION`. The digest is
Evidence, not adoption authority. Entries are sorted and unique by Candidate;
all entries from one source group must remain in one split. R4A performs no I/O
and retains no commentary, transcript, PII, credentials or media body.

Allowed files are the R4A module, canonical schema and byte-exact resource mirror,
focused tests, this design, and bounded TASK-054 current summaries. Dataset
adoption, R4B narration intake, training and Product activation remain Human-Gated.
