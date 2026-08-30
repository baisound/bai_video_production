# TASK-054 R6C Quarantined Artifact Seal Design

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `CONTRACT_IMPLEMENTED / REAL_ARTIFACT_NOT_AVAILABLE`

## Boundary

R6C seals a future R6B output into body-free immutable Evidence only after exact public re-admission of a PASS TUNED R4D offline report. It neither downloads/trains nor registers/approves/activates a Binding. Current tests use synthetic file Evidence; no model artifact is read.

## Manifest

The canonical manifest binds quarantine identity, base-model ref/digest, adapter ref/aggregate digest, sorted logical file inventory with roles/sizes/digests, total bytes, training Dataset/recipe, R4D evaluation, rights manifest, held-out TEST sample set, TUNED binding digest and seal time.

At least one ADAPTER role is required. Single or sharded adapters use the canonical aggregate digest of the ordered ADAPTER file Evidence list, so the Binding digest never ambiguously means one arbitrary shard. Logical paths are ASCII relative, unique, traversal-free and bounded. Total sealed bytes are capped at 1 GiB for this pilot contract.

## Fail closed

- R4D TUNED status other than PASS: reject
- adapter aggregate mismatch or empty ADAPTER role: reject
- duplicate/unsorted/traversing file path: reject
- quarantine/adapter identity crossing: reject
- total size/checksum/lineage/state tamper: reject
- any `APPROVED` or activation state: reject

Schema and packaged mirror are exact. Public admission reconstructs invariants and recomputes the manifest digest.

## Remaining authority

A sealed fixture remains `QUARANTINED_EVALUATED_NO_APPROVAL_OR_ACTIVATION`. Real R6B output, file hashing, license/rights Evidence and resource receipts are unavailable. R6D may only propose an EVALUATED Binding against exact real Evidence; APPROVED/default route/promotion remain separate Human actions.
