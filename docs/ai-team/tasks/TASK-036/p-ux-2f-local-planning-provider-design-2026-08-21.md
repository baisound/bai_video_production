# TASK-036 P-UX-2F local planning provider design

Status: `UNIT_A_IMPLEMENTED / NOT_YET_SHELL_BOUND`

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
