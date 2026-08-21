# TASK-036 P-UX-2F local planning provider design

Status: `UNIT_C_IMPLEMENTED / LOCAL_FREE_PLANNING_SHELL_BOUND`

## Boundary

The adapter accepts only an enabled `PLANNING / LOCAL_OPEN_SOURCE / ollama /
LOCAL_FREE_AI / TEXT_GENERATION` route with no credential. Its entire network
surface is exact loopback `127.0.0.1:11434`: `GET /api/tags` proves that the
configured model already exists, then `POST /api/chat` performs one explicit
structured-output request. Redirects, model pull/create, cloud endpoints,
credentials, host paths and paid routes are outside the adapter.

The request uses `stream=false`, `think=false`, deterministic temperature and a
recursively closed JSON Schema both as Ollama's `format` and in the private
system instruction. Request, response, prompt and timeout values are bounded.

## Canonical mapping contract

The untrusted model may propose only content fields needed to construct the
existing TASK-027 v1 contracts: Creation Intent prose, Proposal sections,
Blueprint title/rate, a gap-free Scene ledger and audio intent flags. The parser
rechecks every field, enum, length, NUL, uniqueness, duration/frame equation,
gap/overlap, final hold and dense-UI invariant after the provider returns.

The model does not choose IDs, cost, route authority, provider policy, Human GO,
paths or execution rights. Unit B derives stable IDs from the bounded request
hash, fixes local cost to zero, creates the Provider Policy from the selected
current route, and publishes the typed records only through TASK-027 CAS.

Unit A never writes `production-proposal.json` and never claims an approved Plan,
Asset, generation Candidate, Timeline edit, audio completion or Export.

## Unit B canonical publication

Unit B adds a TASK-036 application boundary around the existing TASK-027 store.
Prepare binds the exact empty/current Planning snapshot, current local connection
coordinate, route and policy hash, performs model-inventory readiness only, and
returns a body-free one-shot Human confirmation. Apply consumes the confirmation,
rechecks every coordinate, calls the local adapter once, maps the validated
candidate to the existing typed TASK-027 v1 records, and publishes them through
the TASK-027 application lock and snapshot CAS.

Intent, Proposal and Blueprint IDs are derived from the canonical request hash;
the model cannot choose them. The existing Provider Policy keeps its canonical
meaning as the exact active AI Connection Profile. A separate reserved Proposal
section durably records the request, selected local route/model, cost class,
schema and prompt-contract provenance without storing the raw request. Cost is
Product-fixed to zero JPY and the new Proposal remains `GO_REQUIRED`.

The canonical Proposal snapshot format `1.1.0` binds its checksum-protected
collection to one immutable `project_id`; TASK-027 Product runtime rejects both
foreign scoped snapshots and legacy unscoped `1.0.0` snapshots. Legacy reads
remain available only to explicit offline tooling and do not migrate authority.
The local provenance binds the exact Project ID and origin manifest hash. A
later manifest revision intentionally produces a fresh authority coordinate;
an older deterministic record cannot be projected as current idempotent output.
Repeating the exact old request then fails as a deterministic identity conflict;
an explicit Human-edited request or future governed migration is required.

The current Product Project manifest ID/hash is required at prepare, apply and
final publication. A TASK-036 generation lock provides at-most-one concurrent
local call and exact-one CAS publication for identical live operations; restart
of a fully published request projects the exact request/provenance record with
no provider call. A process crash after side-effect-free local inference but
before TASK-027 publication may require another local inference on retry. This
unit does not claim an unconditional durable exactly-once dispatch journal.

## Unit C trusted Shell binding

The unified TASK-036 trusted launcher binds Unit B only when the Product Project
manifest and the canonical TASK-028 connection settings both exist. The current
connection callback reloads the canonical settings record for every prepare and
apply boundary. Unit B then admits only the exact enabled local-free Ollama
planning route; cloud, paid, credentialed and unsupported routes remain closed.

The Planning screen accepts one private vague request. `prepare` checks the
exact Planning snapshot and local model inventory but does not infer or persist.
The UI displays route, model, cost class and request hash, then asks for an
explicit Human confirmation. Confirmed `apply` performs one local inference and
publishes the resulting typed Proposal as `GO_REQUIRED`; cancel performs no
inference. Raw request text and host paths are not returned across the bridge.

Planning generation operations hold the trusted launch runtime operation lease
for the whole prepare/apply/cancel call. An old bridge retained after launcher
close therefore cannot call Ollama or mutate the Proposal store. This unit does
not perform Human GO, visual generation, Asset adoption, Timeline mutation,
audio completion, Final Review or Export.

## Unit C verification evidence

On 2026-08-21 the Windows Product path reused the already-installed Ollama
0.32.14 runtime and already-present `qwen3:8b` model. No runtime installation,
model pull or paid/cloud call occurred. A temporary Product Project completed
Shell status, prepare, explicit confirmation and apply through the production
adapter. The body-free result reported `LOCAL_FREE_AI`, provider execution true,
paid authorization false, two gap-free scenes and canonical TASK-027
`GO_REQUIRED`. The temporary Project was removed on process completion.

An initial real response violated the Scene frame invariant and was rejected as
`ERR_LOCAL_OLLAMA_CANDIDATE_INVALID` before canonical persistence. The system
instruction was then tightened to state every arithmetic bound and a concrete
two-second/30-fps example. The single bounded verification retry produced the
valid result above. Product validation remains authoritative; invalid model
output is never repaired silently or published.
