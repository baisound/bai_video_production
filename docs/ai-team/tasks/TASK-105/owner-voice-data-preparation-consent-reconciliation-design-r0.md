# TASK-105 Consent reconciliation design R0

## 1. Claim and effect ceiling

This is an original architecture/responsibility reconciliation design under [TASK-105](task.md). It selects the minimum safe design route after the local TASK-088 adoption audit. Acceptance means the responsibility map, evidence distinctions, ordering and source gates are coherent; it does not mean old contracts are adopted, wire ABIs frozen, native producers available or implementation authorized.

All Product/private/native effects are zero. No existing candidate file is copied or changed. The old candidate's pure contracts are reference material only. A future version choice requires explicit design acceptance and allocation; the current choice is **NO_ADOPTION / NO_ABI_ALIAS**.

## 2. Bound facts and their limits

Base main: `53e4f0ea8e219b773a2976ba40b956830ff2e1df`. Audit report: `TASK-088/adoption-disposition-audit-20261010-0c4afdbfdbfe4e5bb3e081c034ddb1ea/audit.md` under canonical external Evidence; SHA-256 `fe6a3e0c4003992cd8016e17887b96d28b22a880ac6f48525f57f340572183e1`.

| Evidence | Established | Not established |
|---|---|---|
| Local TASK-088 HEAD `aab924e297c5354cb844a88d727bb971a249967a`; R4 design hash `a873681d41411889c1c1eb76243ceba6cd5e80931bf65c628c645a419d71755f` | Historical offline candidate and recorded review provenance exist | Canonical admission, fresh tests, installed live Consent |
| Merged [PR #551](https://github.com/baisound/bai_video_production/pull/551), commit `513c723c39d8c2775ab47f32c5ce3ac3bab180e0` | TASK-089 implementation/schema/tests and TASK-090 source/tests exist | Full live Asset/terminal boundary or current design authority |
| TASK-089 current task.md says pure pending, but source exists | Documentation/source discrepancy requires reconciliation | Permission to overwrite source, ignore governance, or treat source as absent |
| TASK-090 module emits `BOUND_VERIFIED` for a pure hash record | Structural record/roundtrip is implemented | Durable selector, current-read lease, authenticated producer, restart recovery |
| TASK-102 accepted PMST-I2, enrollment disabled | Generic writer migration boundary and explicit closed routing | Consent participant support or Product enrollment authority |
| TASK-099 JCV-I accepted | Project/Job Currentness V2 semantic owner | Dedicated Consent store or the old local allocation with same ID |
| TASK-101 accepted IMC-D R3 | Existing-model import design is separate | Preparation Consent, current native readiness or implementation permission |

Source and task records are pinned to the bound main. Independent native/installed status of 071/072/074/082 is NOT_CONFIRMED here. No missing Task directory proves an unused ID. No fixture flag/hash proves a live capability.

## 3. Target semantic boundary

The proposed dedicated Consent domain permits only four preparation uses: QUALITY_FINISHING, TRAINING_COPY_CREATION, TRANSCRIPT_DERIVATION and DATASET_CANDIDATE_PROPOSAL. It does not authorize capture, final Dataset adoption, training, existing-model import/load or inference. Copy creation and Dataset adoption must remain separate decisions. OwnerSubject/use-rights truth stays with TASK-046; rights and current Consent are independently required.

TASK-105 owns this reconciliation proposal, not an already installed semantic issuer. Any future successor semantic owner must be explicitly recorded in its accepted ABI; it cannot silently mint TASK-088 receipts or rename a foreign issuer.

| Concern | Existing responsibility retained | Proposed relationship |
|---|---|---|
| Consent purpose, issue/revoke/expiry semantics | Historical TASK-088 proposal; new allocation needed for successor implementation | Fresh versioned design with explicit old-to-new incompatibility policy |
| Subject, use-rights, Dataset/model approval | TASK-046 | Consume exact owner currentness; never issue approval by proxy |
| Human presence/one-use decision | TASK-071 | Accepted dedicated action, not generic JSON confirmation |
| Authenticated process/channel/ticket | TASK-072 | Exact consume and terminal handoff; no direct UI-to-store bypass |
| Trusted time | TASK-074 | Owner-bound clock/floor protocol; no caller clock |
| Protected manifest/control mutations | TASK-102 | Closed writer/lock/participant protocol; preserve canonical Project manifest |
| Project/Job currentness | TASK-099 | Only exact applicable Project/Job proof; not Consent-currentness substitution |
| Asset registry / successor adapter | TASK-003 / TASK-089 | Explicit successor issuer bridge; no second registry |
| Media custody/body lease | TASK-082 | Body-free currentness plus separately authorized lease |
| Q2 quality / Q2 terminal / Q3 | TASK-048 / existing TASK-090 source responsibility / TASK-046 | Distinct producer and terminal/currentness contracts |
| Existing-model import | TASK-101 | Separate route; neither substitute nor prerequisite for effect-zero Consent design |
| Product entrypoint | Existing TASK-036 composition | Future wiring inside BAI Video Production.exe; no new Consent EXE/daemon |

## 4. Compatibility and adoption disposition

Reuse is presently conceptual: bounded parser limits, closed operation universe, nonlive flags, UNKNOWN fencing, one-use decision, crash seams and digest-DAG checks are useful design inputs. Neither this document nor review PASS authorizes copying their implementation.

Explicit incompatible facts: old TASK-088 digests use bare lowercase hex and `asset:` references; TASK-089 fixtures use `sha256:` digests and ASSET/OP identifiers. A future adapter must validate the producer's own typed record/domain/owner/currentness before mapping semantic fields. Removing a prefix, relabeling issuer/task or recalculating a self-hash cannot promote evidence. The future ABI decision must choose either a preserved historical nonlive ABI with explicit bridge or a new version with separately reviewed migration. No in-place schema widening or mixed interpretation of the same version.

TASK-090's current record is usable only as a structural reference. Live consumption requires independently accepted Project/Consent/subject/quality/custody/Asset joins, selected head, predecessor/revision, exact operation, revocation/time and restart semantics. A new terminal ABI must reject copied/self-signed/foreign records. Governance reconciliation must preserve existing source and PR history; it is not removal or a fresh unused-ID allocation.

## 5. Store and recovery architecture decision

Keep the existing canonical Product Project manifest. Consent is a proposed domain child with semantic head selection owned by that manifest, not a parallel Project store. TASK-102 owns the secure physical commit, protected controls, route registration and same-operation witnesses; the Consent semantic owner owns policy/history relations. TASK-099 Job semantics are not adopted as Consent semantics.

Old LB-4's direct TASK-043 reservation/proof journals are **not an implementation route**. Current `project_save.py::_save_via_pmst` rejects participant/commit_guard use with `ERR_PMST_ENROLLED_PARTICIPANT_ADAPTER_REQUIRED`. Default unenrolled behavior cannot bypass this security design. A future TASK-102 owner amendment must approve exact closed operations/targets and the complete writer/lock matrix before a Consent writer exists. No generic path/callback/SQL/Protocol injection surface.

Required ordering constraints for that future design:

1. Establish exact current subject/rights/time and predecessor Project/Consent/coordination heads. Any persisted time-floor advancement completes before freezing the request.
2. Reserve one semantic operation identity without advancing the request's expected Project head; bind only already-fixed input identities. Reservation lives under the accepted protected transaction owner, not a caller side file.
3. Consume dedicated Human action through 071/072 exactly once, then revalidate all relevant predecessors/currentness. Lost/ambiguous consume outcomes permit reconciliation only.
4. Serialize semantic successor bytes and descriptors from fixed ancestors; perform an accepted atomic/CAS Project-child transaction. Do not include a post-commit proof in the generation it attests.
5. Publish the same-operation proof/witness outside the attested manifest through an accepted protected route. No positive issue/currentness until semantic successor, selected manifest and durable proof agree.
6. Recovery reuses the operation identity and authenticated owner result. Known committed knowledge cannot downgrade to no-write. Missing reply is not absence. Partial publication remains UNKNOWN/recovery-required; no second Human prompt or blind retry.

For revocation/expiry, preserve an explicit PENDING winner even with no active intents, settle/stop every outstanding consumer, close coordination, then append final event and current-generation readbacks in an acyclic order. The audit's Pp -> P1/CR1 -> P2/CR2/IR2 sequence is a constraint example, not adoption of its ABI: a final event can attest the prior close, while final current readback must join the same Project generation. Full field/nullability/digest preimages and protected journal placement must be frozen in the later owner design before any implementation allocation.

## 6. Admission and fail-closed outcomes

These are design-level classifications, not new executable record enums.

| Condition | Permitted design outcome | Forbidden inference |
|---|---|---|
| Unallocated owner, absent ABI, fixture only | UNBOUND; no effect | A matching name/hash is installed authority |
| Explicit false/stale/mismatched predecessor before effects | BLOCKED_NO_EFFECT | Silently refresh the immutable request |
| Authenticated proof establishes no commit | DEFINITELY_NOT_COMMITTED; exact retirement protocol | Missing file/reply proves absence |
| Manifest committed but proof/result lost | OUTCOME_UNKNOWN; same-operation reconciliation | Retry with random identity or issue another Human event |
| Revocation with unknown outstanding consumer | PENDING; no new grants/steps | Deadline alone proves stop/terminal |
| Complete matching semantic commit + selected head + durable owner proof | Eligible for later currentness verification | Past completion remains current forever |
| Restart | Burn process-local capability; reconcile durable identities | Deserialize JSON into live handles |

There is no live outcome in D0. Installed binding requires exact owner/version/build/session, private nominal capability and invocation budget under fixed Product composition. Public audit records remain body-free non-capabilities.

## 7. Dependency sequence and bounded next units

```text
D0 reconciliation (this exact2, review and Evidence)
  -> separately allocated owner-ABI detail design
       -> separately authorized pure implementation
       -> accepted 102 Consent transaction/route amendment
       -> accepted 046 subject/rights + 071/072 Human + 074 time contracts
  -> independently reconciled 089/090 owner/ABI design
accepted live dependencies -> separately authorized composition/native gates
```

The arrows describe prerequisites, not automatic authority. Pure/nonlive designs may proceed independently when expressly allocated. TASK-101 native import is not a dependency of D0 or pure preparation design. Q2/Q3 live use additionally waits for 082/048/089/090/fence obligations; missing terminal capability need not block independent semantic design.

Potential later pure payload is six files (pure module, nonlive port module, schema, package mirror and two test files), plus a Task status carrier only if explicitly allowed. No path set is authorized here. A later detailed design must name exact paths, owner, ABI/schema/digest grammar, negative vectors, review budget and completion criteria. TASK-102/089/090 changes require their owning scope; exact2 is not widened by dependency discovery.

Shared Task index/roadmap/lock admission, commit/push/PR/merge and live/product effects remain separately unapproved. No automatic source gate release follows D0 acceptance.

## 8. Design verification and future failure matrix

D0 checks: exact2 only; stable base/branch and clean prior state; collision observation; ASCII filenames and valid local task/design link; all scope/authority distinctions present; observed089/090 source acknowledged; no unused090/099 assumption; 102 coordinator incompatibility; no second store; dependency DAG without descendant preconditions; no native readiness from historical tests. Independent Critic reviews responsibility/security/recovery; independent Tester checks those assertions and table consistency without running Product code; Judge accepts/rejects exact design hash after their results. Two correction cycles maximum.

Future implementation acceptance must add strict malformed/extra-field/size/enum tests; wrong issuer/version/domain/ID tests; caller-time and forged receipt negatives; one-use consume and replay/concurrent winner tests; pre/post reservation/Human burn/child commit/manifest commit/proof publication crash seams; known-commit monotonicity; pending-empty and cross-generation readback joins; owner drift and reverse fence release; source policy rejection of unregistered protected writers; fixture/live separation and privacy scanning. These are required future tests, not claims of execution.

## 9. Completion boundary

D0 completes only as a reviewed reconciliation design with C/H0 and readback Evidence. Current wire ABI, runtime behavior and installed dependency readiness remain NOT_CONFIRMED. Implementation remains PARKED_NOT_AUTHORIZED even after acceptance. Next Human decision is whether to allocate a bounded detailed owner-ABI design or preserve the accepted reconciliation only; existing candidate adoption/source start/private/native effects need distinct explicit authorization and are not requested implicitly by this document.
