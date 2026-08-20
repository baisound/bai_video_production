# TASK-052 R2B — Batch Visual Registration Detailed Design

Status: `DESIGN_BOUND`
Profile: `DEV-3 HIGH ASSURANCE`
Defect: `DBD-HA-052-008`
Matrix: `DBD-GAP-031 / 063 / 067`

## Boundary

R2B changes the batch registration execution boundary. It does not change detector
accuracy, teacher labels or Owner data without an explicit Human confirm action.

```text
EXTRACT / PREVIEW (background, sequential bounded child process, cancellable)
  -> staged PGM + receipt
HUMAN REVIEW
  -> selected staged IDs
CONFIRM (background)
  -> verify every staged hash
  -> copy to temporary final-directory files
  -> cancellation checkpoint
  -> atomic file placement + one atomic manifest write
  -> one Reference Slice Index rebuild per affected domain
  -> performance receipt
```

## Transaction and recovery

No manifest row is written during preparation. Preparation failure/cancel removes all
temporary files and retains PREVIEWED receipts. A commit failure removes files already
placed and leaves the prior manifest authoritative. A process death before manifest
commit can leave only unreferenced derived files, never a partial manifest presented as
complete. Indexes are derived and rebuild after the canonical manifest commit.

## Process and UI policy

- extraction is sequential, so concurrent FFmpeg child count is at most one;
- FFmpeg extraction and still normalization share Windows `CREATE_NO_WINDOW` policy;
- Confirm never re-extracts staged PGM files;
- Tk polls progress emitted by workers (`EXTRACT / PREPARE / COMMIT / INDEX_REBUILD`);
- progress shows `processed / total` and current domain;
- Cancel is honored before irreversible commit and explicitly ignored after commit
  begins;
- the existing maximum sample bound remains active.

## Evidence receipt

The batch receipt records stage/confirm/duplicate/failure counts, subprocess count,
extract/commit/index/total seconds, cancellation, domains, index paths and errors.

## Acceptance

1. two or more staged samples produce one manifest write;
2. each affected domain rebuilds once;
3. pre-commit cancellation leaves manifest empty and receipts retryable;
4. manifest failure rolls back placed files;
5. preview cancellation is bounded and marks partial staging discarded;
6. no-console kwargs reach every FFmpeg subprocess route;
7. confirm runs through the background progress route, not a Tk-thread per-row loop;
8. source/affected tests pass; packaged generator-0 reproduction remains R9.
