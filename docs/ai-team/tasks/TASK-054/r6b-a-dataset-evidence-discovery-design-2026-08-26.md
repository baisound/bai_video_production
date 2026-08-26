# TASK-054 R6B-A Dataset Evidence Discovery Design

Date: 2026-08-26
Development depth: DEV-3 HIGH ASSURANCE
State: IMPLEMENTATION AUTHORIZED / LOCAL READ-ONLY UNIT

## Responsibility boundary

R6B-A discovers only exact `datasets/task054/<manifest-id>/<revision>/manifest.json`
coordinates under one caller-selected root and re-admits each record through the
existing R4A `admit_dbd_reasoning_dataset_rights_manifest` boundary. R4A remains
the only canonical Dataset rights/provenance manifest. R6B-A creates no Dataset
store, rights decision, Consent decision, adoption, training eligibility or
execution authority.

## Input and filesystem safety

- The root is read-only and never persisted as plaintext.
- Only files named `manifest.json` are read.
- Directory/file symlinks and junctions, unexpected manifest depth, revision/path
  mismatch, unreadable files and oversized files fail closed.
- Scanning is bounded to 4096 directories and 256 manifest coordinates.
  Each read is capped at the existing R4A 2 MiB canonical ceiling plus one
  sentinel byte, including a file-size race after the initial metadata check.
- No private media, transcript, narration body or arbitrary neighboring file is
  read.

## Body-free report

The report retains only observation/path digests, admitted manifest identity,
revision, R4A checksum and aggregate disposition/split counts. Invalid Evidence
retains no manifest identity or parsed content. Raw paths and JSON bodies are
never returned. Canonical report states are:

- `NO_MANIFEST_FOUND`;
- `DISCOVERED_CANDIDATE_ONLY`;
- `BLOCKED_INVALID_EVIDENCE`.

The fixed state is
`EVIDENCE_ONLY_NO_DATASET_ADOPTION_OR_TRAINING_AUTHORITY`. Exact report
re-admission recomputes the checksum and all cross-field invariants.

## Failure and authority matrix

| Condition | Result | Authority |
|---|---|---|
| root absent or no manifest | `NO_MANIFEST_FOUND` | none |
| every exact coordinate re-admits through R4A | `DISCOVERED_CANDIDATE_ONLY` | candidate Evidence only |
| malformed, crossed, duplicate, symlinked or oversized Evidence | `BLOCKED_INVALID_EVIDENCE` | none |
| any row remains NEEDS_REVIEW/REJECTED | aggregate counts remain visible | no training/adoption authority |

## Prohibited effects

R6B-A performs no write, Dataset build/adoption, source-material copy, model or
runtime acquisition, training, evaluation, Provider execution, Binding change,
Timeline/Resolve mutation, promotion, release, deploy or Production activation.
Real Dataset creation still requires Owner-controlled source material and exact
rights, Consent, provenance, retention, redaction and split Evidence.
