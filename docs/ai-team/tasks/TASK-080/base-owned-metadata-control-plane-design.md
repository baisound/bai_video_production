# TASK-080 Base-owned Metadata Control Plane Design

Status: `R1 DESIGN ACCEPTED_C_H0 / DOCS_PR_PENDING / EFFECT0`

## 1. Decision

The trusted control plane is a three-layer composition:

1. **external admission layer** — an organization ruleset's
   `Require workflows to pass before merging` rule selects the exact source
   repository, source branch, and workflow file, plus expected-head merge
   policy;
2. **base-owned execution layer** — the launcher, verifier, schemas, and
   receipt rules are loaded only from a commit already read back from canonical
   `main`;
3. **task consumer layer** — TASK-064 implements the launcher/verifier and
   TASK-079 later consumes only its sealed transition receipt.

A pull request cannot establish any of these facts about itself. A PR run is
Evidence until the relevant bytes are merged, canonical `main` is read back,
and the external admission layer requires the exact base-owned check.

## 2. Threat model

The design fails closed against:

- a PR changing the workflow or verifier that evaluates that same PR;
- `pull_request` checkout ambiguity or use of head-controlled scripts;
- a historical PR head, local worktree, shallow object database, environment
  value, caller base/head, or test fixture becoming Authority;
- workflow-name/check-name collision from an untrusted workflow;
- action-tag drift or third-party action replacement;
- missing base objects followed by fetch/network repair;
- CRLF or checkout normalization changing hashed source semantics;
- predecessor and successor hashes being accepted at the same time without a
  one-shot transition state;
- transition replay, second successor, epoch skip/backslide, or coordinate
  substitution;
- merge between transition consume and terminal readback;
- receipt JSON ambiguity, unknown fields, duplicate paths, reordered arrays,
  mode-only drift, or caller-supplied hashes;
- an external ruleset reported as configured without an independent readback.

## 3. Bootstrap rule

### 3.1 Platform facts and admitted policy mode

GitHub documents that `pull_request` runs workflow code from the pull request
merge branch, while `pull_request_target` runs the workflow from the base
repository default branch. GitHub also warns that a privileged
`pull_request_target` workflow becomes unsafe when it checks out and then
executes pull-request code. The TASK-080 launcher therefore uses the
base-owned `pull_request_target` workflow only and treats head objects as data;
it never checks out or executes them. See
[Securely using pull_request_target](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target).

GitHub organization rulesets can require a workflow selected by source
repository, source branch, and workflow file. That is the only admitted
required-workflow mechanism for TASK-080. A normal required status-check name
is not admitted because GitHub states that required status checks do not take
workflow or event trigger types into account. See
[Available rules for rulesets](https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
and
[Troubleshooting required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/troubleshooting-rules#troubleshooting-required-status-checks).

The ruleset readback must bind exact organization/ruleset IDs, enforcement
state, target repository/branch, source repository, source branch, workflow
path, bypass actors, and current workflow blob. A check name, branch-protection
status context, PR comment, workflow badge, or successful run without that
ruleset readback is not a substitute. If the organization plan or permissions
cannot provide the required-workflow rule, TASK-080 remains dependency N.C.;
it does not downgrade to a name-only status check.

The base-owned workflow does not read this policy with its `GITHUB_TOKEN`.
GitHub's organization-ruleset endpoint requires Organization Administration
permission, and complete `bypass_actors` data is returned only to a caller with
ruleset write access. A separately gated privileged Policy Auditor therefore
performs a GET-only observation outside the workflow. See
[REST API endpoints for organization rules](https://docs.github.com/en/rest/orgs/rules).

The Policy Auditor is TASK-080 R1A and remains
`EXTERNAL_ACCOUNT_GATE_NC`. Its credential has the minimum GitHub permission
needed for the complete read but is used only for GET operations. Its private
Ed25519 signing key is held outside the repository, Actions, logs, artifacts,
and caller input. The base-owned verifier pins the corresponding public key and
its lowercase SHA-256 key ID in canonical source.

`TASK080_POLICY_AUDITOR_RECEIPT_V1` is a signed envelope. Its canonical payload
uses the section 6.1 JSON rules and has exactly:

- `schema_version` = `TASK080_POLICY_AUDITOR_RECEIPT_V1`;
- `issuer_key_id` = lowercase `[0-9a-f]{64}` pinned key ID;
- `github_app_id` and `github_app_installation_id` = positive JSON integers;
- `issued_at_utc` and `expires_at_utc` = canonical RFC3339 UTC `Z` strings,
  with a maximum five-minute lifetime;
- `organization_id`, `organization_login`, `ruleset_id`, and
  `ruleset_updated_at_utc`;
- `enforcement` = `active`;
- `target_repository_id`, `target_ref` = `refs/heads/main`;
- `source_repository_id`, `source_ref` = `refs/heads/main`, and exact
  `workflow_path` and `workflow_blob_oid`;
- `do_not_enforce_on_create` = JSON `false`;
- `bypass_actors` = exact empty JSON array;
- `merge_queue_enabled`, `required_events`, and `raw_response_sha256`;
- `http_method` = `GET`, `request_path_sha256`, `response_status` = JSON
  integer `200`, `egress_policy_sha256`, and `audit_record_sha256`.

The auditor runtime is confined by an enforced method and egress allowlist to
the one organization-ruleset GET endpoint, follows no redirect, exports no
credential, and produces no receipt unless its private audit record proves
that exact request and response. `POST`, `PUT`, `PATCH`, `DELETE`, redirect,
alternate host/path, or missing audit readback fails closed.

`required_events` is ASCII lexicographically sorted and unique. It is exactly
`["pull_request_target"]` when merge queue is disabled and exactly
`["merge_group","pull_request_target"]` when enabled. The signature is an
Ed25519 64-byte signature encoded as unpadded base64url over the canonical
payload bytes. `TASK080_POLICY_AUDITOR_ENVELOPE_V1` has exactly `payload` and
`signature` and is itself encoded by the section 6.1 canonical JSON rules.
`policy_receipt_sha256` is the lowercase SHA-256 of those exact canonical
envelope bytes, not of a reparsed payload or alternate serialization. Duplicate
keys, unknown fields, a nonempty bypass list, a bypass-capable Main Merge
actor, stale/expired receipt, wrong key, signature, permission identity, or
ruleset coordinate fails closed.

Key bootstrap is one-way: an Owner-gated external custody unit first generates
the key, retains the private half outside GitHub/repository/Actions/logs, and
hands only the public key and derived key ID to R0A. R0A pins those public bytes
in canonical source and completes post-main blob readback before the auditor is
activated with the private key. Ruleset selection and auditor activation occur
only after that readback. Rotation repeats generate -> public-only canonical
pin -> post-main readback -> new service activation -> old-key revocation. An
unpinned, pre-activated, revoked, or silently dual-active key is rejected; an
old signed receipt cannot cross the rotation boundary.

The privileged auditor issues a fresh receipt at R0A policy admission and again
immediately before every later merge admission. The workflow accepts no caller
JSON as policy truth; it validates the signed envelope and freshness against
its pinned public key. Without this auditor, R0A cannot terminalize and R0B
remains `START0`. R1A is implemented only after the R0A workflow bytes exist
on canonical `main` and the external ruleset selects that exact workflow; it
is not deferred until after R0C.

If merge queue is enabled, the required workflow must also support the
`merge_group` event and bind that setting in the policy readback. GitHub notes
that required workflows need this trigger for merge-queue checks. See
[Troubleshooting ruleset workflows](https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/troubleshooting-rules#using-the-merge_group-trigger).

### 3.2 No self-bootstrap

The first PR that introduces or changes the base-owned launcher/verifier cannot
be certified by that launcher/verifier. Its checks are non-authoritative
Evidence. Bootstrap admission requires all of:

- independent frozen-source Critic and Judge Critical/High `0/0`;
- expected-head review by Main Merge;
- no merge conflict and exact current base;
- merge without treating the new check as a predecessor requirement;
- post-merge canonical `main` OID/tree/blob readback;
- Owner/organization-administrator admission for the external required-workflow
  ruleset only after that workflow is present on canonical `main`;
- separate readback that the organization ruleset now requires the exact
  source repository, source branch, and base-owned workflow file.

If external repository-policy mutation is necessary, it remains an explicit
Human/external-account Gate. This design authorizes specification and
read-only verification only.

### 3.3 Trusted execution identity

After bootstrap, every trusted run binds:

- exact base `main` OID and tree OID;
- exact launcher workflow path and Git blob OID;
- exact verifier path and Git blob OID;
- exact closed schema/contract blob OIDs;
- exact event, repository, base ref, base OID, head OID, and run attempt;
- exact organization-ruleset required-workflow readback identity;
- GitHub OIDC jobs use exactly `contents: read` and `id-token: write`; every
  other GitHub permission is `none`, secrets are zero, and no repository or
  account write token or head script is available;
- every third-party action by immutable full commit OID;
- a hermetic Git configuration with hooks, filters, attributes, submodules,
  LFS smudge, credential helpers, alternates, replace refs, and object fetch
disabled unless a later reviewed contract explicitly requires one.

`id-token: write` is used only to mint the short-lived GitHub OIDC JWT and does
not authorize GitHub resource mutation. Its audience is the one immutable
broker audience. The token-request endpoint, bearer token, and related runtime
values are never logged, cached, artifacted, echoed, or exported. Missing
`id-token: write` leaves the OIDC role dependency N.C.; any additional GitHub
write permission, secret, alternate audience, or token disclosure rejects the
run before broker access.

The trusted workflow may inspect untrusted Git objects only as data through a
fixed base-owned verifier. Head OIDs come only from the typed event payload.
The base-owned launcher may use read-only GitHub object APIs to obtain exact
trees/blobs and must verify every returned OID; it never runs `git fetch` for
head materialization. It never checks out, imports, sources, or executes
head-controlled code. Missing required objects are a stable failure; no fetch
or alternate network fallback is allowed.

## 4. R0A-R0C rollout

| Unit | Purpose | Issue | Consume | Required terminal evidence |
| --- | --- | --- | --- | --- |
| `R0A` | bootstrap a base-owned launcher, then admit it into the organization ruleset | `false` | `false` | post-main launcher/workflow/verifier blobs followed by a fresh signed R1A Policy Auditor receipt |
| `R0B` | install the transition verifier in disabled/report-only mode | `false` | `false` | negative vectors and disabled-state readback; no acceptance change |
| `R0C` | execute one body-free canary through the required base-owned check | canary receipt only | `false` | canary expected-head/current-base/run identity and canonical main readback |

The R0A PR is merged without claiming that its new workflow was already a
required predecessor check. After post-main blob readback, the separately
authorized organization administrator selects that exact workflow in the
ruleset. R1A then admits the privileged GET-only auditor and its fresh signed
policy receipt closes R0A. R0B and R0C do not start before that receipt.

R0A-R0C never issue or consume the real TASK-079 transition. The separate
post-R0C unit is TASK-080 R1B; TASK-079 implementation remains N.C. until R1B
is admitted and its readiness receipt is independently accepted at C/H0.

The current preserved TASK-064 exact-two-file NO-GO candidate may be used only
as review input. No hunk, hash, status, or local run from it is grandfathered.

## 5. Base-owned verifier input

The verifier accepts a closed, typed request assembled by the base-owned
launcher. Public or caller text cannot select mode or authority coordinates.

`TASK080_BASE_VERIFIER_REQUEST_V1` uses the section 6.1 canonical JSON rules
and has exactly:

- `schema_version` = exact JSON string `TASK080_BASE_VERIFIER_REQUEST_V1`;
- `repository_id` = positive JSON integer and `repository_full_name` matching
  ASCII `[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+`;
- `base_ref` = exact `refs/heads/main`;
- `base_oid`, `base_tree_oid`, and `expected_head_oid` = lowercase
  `[0-9a-f]{40}`;
- `event_name` = `pull_request_target` or `merge_group`;
- `merge_group_oid` = JSON `null` for `pull_request_target`, otherwise
  lowercase `[0-9a-f]{40}`;
- exact repository-relative `workflow_path`, `launcher_path`, `verifier_path`,
  and their lowercase 40-hex Git blob OIDs;
- `contract_blobs` = an ASCII path-ascending, unique, nonempty array whose
  items have exactly `path` and lowercase 40-hex `blob_oid`;
- `policy_receipt_sha256` = JSON `null` only for `BOOTSTRAP_READBACK`, otherwise
  lowercase `[0-9a-f]{64}` for the freshly verified signed Policy Auditor
  envelope;
- `operation_kind` from the closed enum `BOOTSTRAP_READBACK`,
  `DISABLED_VERIFY`, `CANARY`, `TASK079_PREDECESSOR`, `TASK079_SUCCESSOR`, or
  `TASK079_TERMINAL_READBACK`;
- `prospective_manifest_id` = JSON `null` for the first three operations and
  the exact TASK-079 V3 64-hex identity for the last three;
- `run_id` = positive JSON integer and `run_attempt` = JSON integer `1..20`.

`request_sha256` is not in the preimage. It is the issuer-derived lowercase
64-hex SHA-256 of the canonical request bytes. Duplicate keys are rejected
during decoding. Reordered `contract_blobs`, duplicate paths, unknown fields,
wrong null combinations, alternate numeric/string types, noncanonical JSON,
or a caller-provided request hash fails closed.

Unknown, absent, empty, duplicate, alternate-type, noncanonical, stale, or
caller-supplied authority fields fail before task evaluation.

## 6. TASK-079 transition state

TASK-080 is the sole issuer of the dynamic transition receipt. TASK-079's
`TASK079_PROSPECTIVE_REPLAY_MANIFEST_V3` is historical evidence and contains no
current base, eligibility, state, or consume authority.

### 6.1 Canonical encoding

All transition preimages use UTF-8 JSON with `ensure_ascii=true`, object keys
sorted, separators `,` and `:`, and no terminal newline. Unknown fields and
alternate types are invalid. Hashes are lowercase hex strings of their stated
length and are issuer-derived.

The transition receipt preimage contains exactly:

- `schema_version` = exact JSON string
  `TASK080_TASK079_TRANSITION_RECEIPT_V1`;
- `state_id`;
- `state_epoch`;
- `phase`;
- `prospective_manifest_id`;
- `authorized_base_main_oid`;
- `authorized_base_tree_oid`;
- `expected_successor_head_oid`;
- `consumed_transition_id`;
- `terminal_main_oid`.

`receipt_sha256` is not part of the preimage. It is the issuer-derived SHA-256
of the exact canonical preimage bytes and is represented as lowercase
`[0-9a-f]{64}`. Caller-supplied or recomputed mappings are Evidence only.

### 6.2 Phase table

| Phase | Epoch | successor | consume ID | terminal main |
| --- | ---: | --- | --- | --- |
| `PREDECESSOR_ACTIVE` | `0` | JSON `null` | JSON `null` | JSON `null` |
| `TRANSITION_CONSUMED` | `1` | exact expected-head OID | exact issuer consume ID | JSON `null` |
| `TERMINAL` | `2` | retained epoch-1 OID | retained epoch-1 ID | exact main OID |

`schema_version`, `state_id`, `prospective_manifest_id`, authorized base OID,
and authorized base tree OID remain identical across phases. Only CAS `0 -> 1`
and `1 -> 2` are legal. A skip, repeat, backslide, or retained-coordinate drift
is terminal failure.

The consume ID is SHA-256 of canonical UTF-8 JSON with exactly:

- `version` = `TASK080_TASK079_CONSUME_V1`;
- `state_id`;
- `prior_state_epoch` = JSON number `0`;
- `prospective_manifest_id`;
- `authorized_base_main_oid`;
- `authorized_base_tree_oid`;
- `expected_successor_head_oid`.

Only the base-owned issuer supplies these fields.

## 7. Merge fence and monotonic consume

The transition is accepted once:

```text
PREDECESSOR_ACTIVE
  -- expected-head verified, CAS and predecessor invalidation -->
TRANSITION_CONSUMED
  -- expected-head merge and canonical main readback -->
TERMINAL
```

The external admission layer and Main Merge jointly enforce a fence:

1. no successor merge begins without the exact epoch-0 receipt;
2. consume binds the expected successor head and invalidates predecessor
   acceptance before any unrelated merge may pass;
3. Main Merge merges only that head;
4. no other main merge occurs until terminal main readback succeeds;
5. terminal state accepts the one current successor result only.

If the platform cannot make predecessor invalidation atomic with merge
admission, the exclusive merge fence remains held from consume through
terminal readback. A timeout or uncertain merge/readback does not reopen the
predecessor or permit another candidate.

## 8. Receipt classes

| Receipt | Authority | Notes |
| --- | --- | --- |
| design review receipt | none | byte-exact C/H0 design evidence only |
| bootstrap post-main readback | enables next rollout gate only | proves base-owned blobs, not transition eligibility |
| organization-ruleset required-workflow readback | enables workflow-admission gate only | external configuration evidence; no source authority |
| signed R1A Policy Auditor receipt | admits the exact current required-workflow policy for one bounded operation | five-minute expiry; cannot issue or consume transition state |
| R0B disabled receipt | none | proves issue/consume remain false |
| R0C canary receipt | enables later implementation review only | not a TASK-079 receipt |
| signed R1B Broker Readiness receipt | enables TASK-079 implementation review only | proves a disposable broker canary; cannot stand in for a transition phase receipt |
| signed `PREDECESSOR_INITIALIZED` receipt | creates the sole epoch-0 transition authority | only after TASK-079 main readback and a separate one-use initialization Gate |
| TASK-079 phase receipt | phase-bound one-use authority | issued only after separately authorized implementation |
| terminal main readback | closes one transition | cannot authorize a second successor |

Serialized JSON is audit/readback Evidence. Live in-process capability or
external policy custody, where required, is not reconstructible from JSON.

## 8.1 R1B durable Transition Broker

R0A-R0C do not implement live transition authority. TASK-080 R1B is a separate
DEV-4 Atomic Unit and External Account/Secret/Store Gate inserted before
TASK-079 implementation. Its implementation owner, Allowed Files, external
service, credential installation, and deployment require a later exact Owner
gate. Until R1 is complete, TASK-079 remains dependency N.C.

The sole trusted issuer is `TASK080_TRANSITION_BROKER_V1`, identified by exact
GitHub App ID/installation ID, service build digest, pinned Ed25519 public-key
ID, and authenticated service endpoint. Its private key, GitHub credential, and
durable store are never provided to pull-request workflows or Main Merge.

Before real initialization the authoritative store contains no TASK-079 state
record. After initialization it contains exactly one record with state/phase fields from
section 6 plus `store_generation`, `compare_token`, `fence_owner`,
`fence_expected_head_oid`, `fence_acquired_at_utc`, `fence_heartbeat_at_utc`,
`audit_sequence`, and predecessor/candidate acceptance booleans. Store updates
are serializable transactions; a signed receipt is formed only from the
committed readback. Public self-hashed JSON, a caller mapping, or a test fixture
cannot create store state or issuer authority.

The authenticated API is closed to:

1. `initialize_predecessor` — under a separately Owner/Main-Merge-gated,
   broker-side one-use initialization plan, performs an absent-state CAS and
   creates the sole epoch-0 `PREDECESSOR_ACTIVE` record;
2. `read_current` — returns a signed current readback; no mutation and no
   implicit initialization;
3. `consume_and_acquire_fence` — compares epoch-0 token, fresh signed policy
   receipt, exact base/tree/manifest and expected head; atomically changes
   epoch `0 -> 1`, predecessor accepted `true -> false`, candidate accepted
   `false -> true`, increments generation/audit sequence, and acquires the
   exclusive fence for that head;
4. `heartbeat_fence` — renews only the exact epoch-1 owner/head session;
5. `read_merge_admission` — admits only the fenced expected head and denies
   every unrelated merge while epoch 1 is current;
6. `terminalize` — after exact canonical main readback proves the expected head
   is contained, atomically changes epoch `1 -> 2` and releases the fence;
7. `recover_epoch1` — re-reads GitHub and store truth. If the expected head is
   merged it terminalizes; if not, it reissues custody only for the same head.
   It never reactivates the predecessor or selects a new candidate.

The initialization plan is a committed broker-side record created only by a
separate external-account Human Gate; caller JSON cannot create it. Its
canonical payload has exactly `schema_version` =
`TASK080_PREDECESSOR_INITIALIZATION_PLAN_V1`, broker-generated `plan_id`,
target repository ID, exact TASK-079 canonical implementation/blob readback,
V3 manifest ID, authorized current main OID/tree OID, fresh R1A policy receipt
hash, initializer caller identity, issued/expiry time, and `consumed=false`.
`initialize_predecessor` atomically compares state absence and this unconsumed
plan, generates state ID/store generation/compare token/audit sequence, writes
epoch 0 with predecessor accepted true, candidate accepted false, all
successor/consume/terminal/fence fields null, consumes the plan, and returns a
signed `PREDECESSOR_INITIALIZED` receipt. Existing state, second/concurrent
initialization, replay, wrong base/manifest/policy, or a readiness envelope in
place of the broker-side plan has store delta 0.

Every mutating request uses authenticated mTLS or equivalent App identity,
one-use nonce, current signed policy receipt, exact compare token, body hash,
and bounded trusted time. A compare failure, expired policy receipt, wrong
caller/head, concurrent request, stale generation, or uncertain commit creates
no second mutation. On crash or timeout, epoch 1 remains locked; lease timeout
does not release the fence or reactivate epoch 0. Recovery reads authoritative
state and can continue only the same expected head. A permanently abandoned
epoch-1 transition requires a separately designed Owner recovery Task and does
not silently unlock merges.

### 8.2 R1B request and signed receipt wire contract

R1B first pins `TASK080_TRUSTED_CALLER_REGISTRY_V1` in canonical main and
reads back its blob. The registry is canonical JSON with exactly
`schema_version` = `TASK080_TRUSTED_CALLER_REGISTRY_V1` and `entries`.
Its SHA-256 is over those exact canonical bytes. Entries are ASCII role-sorted
and have exactly `role`,
`peer_kind`, `peer_binding`, `peer_identity_sha256`, `caller_identity_sha256`,
`allowed_operations`, `allowed_audience`, `credential_revision`,
`not_before_utc`, and `not_after_utc`. Roles are exactly
`TRANSITION_INITIALIZER`, `TASK079_PRODUCT_OPERATION`,
`BASE_REQUIRED_WORKFLOW`, and `MAIN_MERGE`.
`peer_kind` is `MTLS_SPKI_SHA256` or `GITHUB_OIDC_CLAIMS_V1`.
`TRANSITION_INITIALIZER` and `MAIN_MERGE` require distinct mTLS identities;
`TASK079_PRODUCT_OPERATION` and `BASE_REQUIRED_WORKFLOW` require distinct
GitHub OIDC identities. No role may switch peer kind at request time.
For mTLS, `peer_binding` has exactly `spki_sha256`. For GitHub OIDC it has
exactly `issuer`, `audience`, `repository_id`, `repository_owner_id`,
`workflow_ref`, `workflow_blob_oid`, `job_workflow_ref`,
`job_workflow_blob_oid`,
`allowed_events`, and `base_ref`. Issuer is exactly
`https://token.actions.githubusercontent.com`; audience is the broker-specific
immutable audience; IDs are positive JSON integers; workflow refs bind exact
repository/workflow path and `refs/heads/main`; workflow blob OIDs are
lowercase 40-hex. Job-workflow fields are both null for a non-reusable workflow and both
exact/non-null for a pinned reusable workflow. `allowed_events` is the same
ASCII-sorted exact event array as the current signed R1A policy receipt, and
`base_ref` is exact `refs/heads/main`. Concrete event name, event ref, and
event SHA are deliberately not part of the static registry identity. A default `sub` is never
sufficient and is not an authority field.
Hash fields are lowercase 64-hex, `credential_revision` is a positive JSON
integer, times are canonical RFC3339 UTC `Z`, and operation arrays are
ASCII-sorted, unique, and exactly match the closed role table below.
`peer_identity_sha256` is broker-derived from canonical JSON with exactly
`peer_kind` and `peer_binding`. `caller_identity_sha256` is broker-derived
from canonical JSON with exactly `role`, `peer_kind`, `peer_identity_sha256`,
and `credential_revision`.
Each role has a distinct peer identity; one credential cannot occupy two
roles.

For each GitHub call the broker additionally validates exact `iss`, `aud`,
immutable repository/owner IDs, workflow/job-workflow refs and SHAs, bounded
`iat`/`nbf`/`exp`, unique `jti`, `run_id`, and `run_attempt` from the signed
JWT. It also binds the concrete signed event name/ref/event SHA. For
`pull_request_target`, the event is allowed only for base `refs/heads/main` and
the authenticated base commit. For `merge_group`, action is exactly
`checks_requested`, the signed base target is `refs/heads/main`, the ref is a
temporary `refs/heads/gh-readonly-queue/main/` descendant with no traversal or
alternate-base alias, and the event SHA equals the signed merge-group head
SHA. The event must occur in the registry's closed `allowed_events` set.
The dynamic `workflow_sha` and, when present, `job_workflow_sha` claims are
session fields rather than static registry identities. The broker reads the
exact workflow path as a raw Git blob at each claimed commit and requires its
OID to equal the registry's pinned workflow/job-workflow blob OID. It performs
no checkout or head-controlled execution.
`authenticated_session_sha256` is broker-derived from the
canonical exact claims bundle and is replay-cached through expiry. For mTLS it
is broker-derived from canonical JSON with exact `peer_kind`, peer SPKI hash,
TLS-exporter hash, and request nonce hash; the caller cannot supply the TLS
exporter value.

The broker authenticates the channel and derives peer identity, role, caller
identity, audience, authenticated session, and registry blob hash server-side. Request fields are
match-only and cannot select or relabel authority. Unknown, cross-role,
cross-audience, expired, revoked, unpinned, or rotated credentials fail before
store access. Rotation pins and reads back the new canonical registry revision
before activation, then revokes the prior peer without silent overlap.

`TASK080_TRANSITION_BROKER_REQUEST_V1` is a closed canonical JSON object with
exactly: `schema_version`, `operation`, `audience`, `caller_identity_sha256`,
`authenticated_session_sha256`,
`trusted_caller_registry_sha256`, `one_use_nonce_sha256`,
`policy_receipt_sha256`, `initialization_plan_sha256`,
`expected_store_generation`,
`expected_compare_token_sha256`, `authorized_base_main_oid`,
`authorized_base_tree_oid`, `prospective_manifest_id`,
`expected_successor_head_oid`, and `body_sha256`. `schema_version` is the exact
JSON string `TASK080_TRANSITION_BROKER_REQUEST_V1`.
`operation` is one of `INITIALIZE_PREDECESSOR`, `READ_CURRENT`,
`CONSUME_AND_ACQUIRE_FENCE`,
`HEARTBEAT_FENCE`, `READ_MERGE_ADMISSION`, `TERMINALIZE`, or
`RECOVER_EPOCH1`. `audience` is exactly `TRANSITION_INITIALIZER`,
`TASK079_PRODUCT_OPERATION`, `BASE_REQUIRED_WORKFLOW`, or `MAIN_MERGE`, as
allowed by the operation table below. Hashes are lowercase 64-hex; Git OIDs
are lowercase 40-hex; generation is a nonnegative JSON integer when non-null.
`initialization_plan_sha256` is non-null only
for `INITIALIZE_PREDECESSOR`; `expected_store_generation` and
`expected_compare_token_sha256` are null only for that operation and non-null
otherwise. `prospective_manifest_id` is non-null for initialization and every
post-initialization operation. `expected_successor_head_oid` is null for
initialization and epoch-0 `READ_CURRENT`, and non-null after a candidate is
selected. No request carries `terminal_main_oid` or other
caller-observed main truth. `TERMINALIZE` and `RECOVER_EPOCH1` derive canonical
main OID/tree/containment exclusively through the broker's authenticated
readback. Unmerged recovery therefore needs no fabricated terminal OID.

`body_sha256` is the lowercase SHA-256 of canonical JSON containing exactly all
request fields except `schema_version` and `body_sha256`; the broker recomputes
it from validated fields. The request contains no `request_sha256`; the broker
derives that separate hash from the final exact canonical request bytes. Thus
neither hash is self-referential and wrong version or body drift fails before
store evaluation.

| Operation | Allowed audience | Required committed outcome |
| --- | --- | --- |
| `INITIALIZE_PREDECESSOR` | `TRANSITION_INITIALIZER` | `PREDECESSOR_INITIALIZED` |
| `READ_CURRENT` | `TASK079_PRODUCT_OPERATION` or `BASE_REQUIRED_WORKFLOW` | `CURRENT` |
| `CONSUME_AND_ACQUIRE_FENCE` | `TASK079_PRODUCT_OPERATION` | `CONSUMED` |
| `HEARTBEAT_FENCE` | `MAIN_MERGE` | `FENCE_RENEWED` |
| `READ_MERGE_ADMISSION` | `BASE_REQUIRED_WORKFLOW` or `MAIN_MERGE` | `MERGE_ADMITTED` |
| `TERMINALIZE` | `MAIN_MERGE` | `TERMINALIZED` |
| `RECOVER_EPOCH1` | `MAIN_MERGE` | `FENCE_RECOVERED` or `TERMINALIZED` |

The role mapping is closed: `TRANSITION_INITIALIZER` may call only
`INITIALIZE_PREDECESSOR`; `TASK079_PRODUCT_OPERATION` may call only
`READ_CURRENT` and `CONSUME_AND_ACQUIRE_FENCE`;
`BASE_REQUIRED_WORKFLOW` may call only `READ_CURRENT` and
`READ_MERGE_ADMISSION`; `MAIN_MERGE` may call only `HEARTBEAT_FENCE`,
`READ_MERGE_ADMISSION`, `TERMINALIZE`, and `RECOVER_EPOCH1`.

Every successful call returns
`TASK080_TRANSITION_BROKER_ENVELOPE_V1`, encoded by the section 6.1 canonical
rules with exactly `payload` and `signature`. `signature` is the broker's
Ed25519 64-byte signature encoded as unpadded base64url over the canonical
payload bytes. The payload has exactly:

- `schema_version` = `TASK080_TRANSITION_BROKER_RECEIPT_V1`;
- `operation`, `outcome`, and `audience` from the table above;
- `issuer_key_id`, `service_build_sha256`, `broker_instance_sha256`, and
  `service_endpoint_sha256` as lowercase 64-hex;
- `github_app_id` and `github_app_installation_id` as positive JSON integers;
- `issued_at_utc` and `expires_at_utc` as canonical RFC3339 UTC `Z`, with a
  maximum two-minute lifetime and a maximum 30-second lifetime for
  `MERGE_ADMITTED`;
- `request_sha256`, `caller_identity_sha256`, `authenticated_session_sha256`,
  `trusted_caller_registry_sha256`, `one_use_nonce_sha256`,
  `policy_receipt_sha256`, `initialization_plan_sha256`, and `body_sha256`
  copied from or derived from the
  validated authenticated request;
- `state_id`, `transition_receipt_sha256`, `store_generation`,
  `compare_token_sha256`, and `audit_sequence` from one committed store
  readback;
- `state_epoch`, `phase`, `prospective_manifest_id`,
  `authorized_base_main_oid`, `authorized_base_tree_oid`,
  `expected_successor_head_oid`, `consumed_transition_id`, and
  `terminal_main_oid` exactly matching the section 6 phase table;
- `predecessor_accepted`, `candidate_accepted`, `fence_owner_sha256`,
  `fence_expected_head_oid`, `fence_acquired_at_utc`, and
  `fence_heartbeat_at_utc`.

The section 6 phase table closes the transition null combinations.
`fence_owner_sha256`, expected head, acquired time, and heartbeat time are
non-null only at epoch 1; they are all null at epochs 0 and 2. Epoch 0 has
`predecessor_accepted=true` and `candidate_accepted=false`; epochs 1 and 2
have the inverse. `transition_receipt_sha256` is the issuer-derived hash of the
exact section 6.1 transition preimage from that same committed snapshot. The
broker envelope SHA-256 is the hash of the exact canonical envelope bytes.
Unknown/duplicate fields, wrong operation/outcome/audience/null combination,
alternate serialization, caller-provided hash, wrong App/install/build/key or
endpoint, stale policy, replayed nonce, expired receipt, or store/readback drift
fails closed. A deserialized or rehashed envelope never recreates a live
broker capability.

Broker key bootstrap and rotation use the same generate -> public-only
canonical pin -> post-main readback -> service activation -> old-key
revocation order as R1A. TASK-079, the required workflow, and Main Merge accept
only a key/build/App/install/endpoint identity pinned in canonical source and
reject a pre-activated, revoked, or dual-active identity.

### 8.3 Distinct R1B readiness receipt

Before TASK-079 implementation, R1B executes a disposable namespace canary
that proves durable CAS, one-use nonce, exclusive fence denial, epoch-1 crash
recovery, terminal readback, and unrelated-state isolation without creating a
TASK-079 manifest, transition receipt, or accepted source. It returns
`TASK080_BROKER_READINESS_ENVELOPE_V1`, a canonical `{payload,signature}`
Ed25519 envelope. Its payload has exactly:

- `schema_version` = `TASK080_BROKER_READINESS_RECEIPT_V1`;
- the same broker key/build/instance/endpoint/App/install identity fields;
- `admission_plan_sha256`, `policy_receipt_sha256`, canonical current main OID
  and tree OID, `canary_namespace_sha256`, start/terminal store generation,
  start/terminal audit sequence, and `canary_transcript_sha256`;
- `passed_checks` exactly the ASCII-sorted unique array
  `["CAS","CRASH_RECOVERY","FENCE_EXCLUSION","NONCE_REPLAY","TERMINAL_READBACK","UNRELATED_ISOLATION"]`;
- `transition_authority_created` = JSON `false`;
- canonical issued/expiry times with a maximum five-minute lifetime.

Its canonical encoding, unpadded-base64url Ed25519 signature, exact pinned
issuer verification, and envelope SHA-256 rules are identical to section 8.2.
The readiness hash covers its exact canonical envelope bytes.

The readiness envelope is issued only after committed canary cleanup/readback
shows no live fence or TASK-079 state and is independently reviewed at C/H0.
It enables only the TASK-079 implementation review. It is not the section 6
transition receipt, cannot satisfy epoch `PREDECESSOR_ACTIVE`,
`TRANSITION_CONSUMED`, or `TERMINAL`, and cannot authorize issue, consume,
merge, release, deploy, or Production effects. Canary failure or ambiguous
cleanup yields no readiness receipt and leaves TASK-079 dependency N.C.

Main Merge does not hold the lock by convention. Immediately before merging it
obtains a fresh signed `read_merge_admission` bound to exact expected head,
store generation, fence owner, policy receipt, and short expiry. The
organization required workflow also consults that same broker state. A signed
receipt is independently verifiable with the pinned key, but cannot be issued,
renewed, consumed, or recovered from public JSON.

## 9. TASK-064 Phase-B amendment

TASK-064 owns implementation only after TASK-080 design is merged and read
back. Its exact duties are:

- implement R0A-R0C within a fresh dedicated worktree and separately approved
  Allowed Files;
- bind all control-plane code to canonical base bytes;
- supply focused, negative, fault, and regression tests;
- obtain independent Critic/Tester/Judge C/H0;
- create no real transition receipt, consume, merge, Release, Deploy, or
  Production effect.

TASK-064 does not own external GitHub policy, TASK-079 semantics, GF-D source,
CHANGELOG/version, or Main Merge.

## 10. Failure and recovery

- A failed or ambiguous bootstrap preserves current behavior and emits no
  trusted receipt.
- A failed R0B/R0C preserves issue=false and consume=false.
- A failure before consume leaves epoch 0 current.
- A failure after consume leaves epoch 1 current and the merge fence held;
  it never reactivates the predecessor automatically.
- A failure after merge but before terminal readback leaves status unknown and
  holds the fence until an exact readback or separately authorized recovery.
- Recovery reads authoritative base/policy/main state anew. It does not reuse
  a prior process object, environment field, workflow output, or public JSON as
  live authority.
- No failure path fetches objects, rewrites history, deletes unknown state,
  force-pushes, or changes external repository policy.

## 11. Progress accounting

Progress is recorded independently as design, implementation, verification,
PR, main integration, and post-main/external readback. A local diff or design
receipt never increments implementation or integration. An unmerged PR never
increments canonical progress. A post-main readback is not native/Product
runtime proof.
