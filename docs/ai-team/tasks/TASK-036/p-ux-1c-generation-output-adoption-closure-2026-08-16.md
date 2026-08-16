# P-UX-1C Generation Output Adoption closure

Date: 2026-08-16
Atomic unit: `GENERATION_OUTPUT_ADOPTION_CLOSURE_R0`

## Design and Critic

The V6.1.1 AI Video page displayed completed local execution receipts but did
not expose the existing TASK-027 boundary that verifies a completed output and
registers it as a Production/Audit Candidate. That operation is separate from
local Provider execution and from Human acceptance or WORLD LOCK.

This slice adds only Output Adoption. Preparation binds the current Execution,
Queue, Production, Prompt, and Adoption snapshots. Apply uses the existing
one-shot confirmation. An interrupted multi-product adoption is resumed from
its durable adoption ID without re-running the Provider.

Builder Critic: a completed execution is not necessarily adoption-ready.
Correction: every completed output projects its exact `adoption_status`; only
`READY` receives an enabled action, and an active recovery blocks new
adoptions. Security Critic: `READY_FOR_AUDIT` could be presented as Human
acceptance, LOCK, or publication. Correction: the confirmation and persistent
boundary text explicitly deny Provider replay, paid use, Human ACCEPT/LOCK,
publication, and NLE mutation. Local execution call sites remain absent.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- Eligible completed outputs project exact Execution ID, Slot, Prompt version,
  media kind, output SHA-256, and adoption status.
- Adoption prepare binds five current Product snapshots before confirmation.
- Apply registers only the existing verified output as an Audit Candidate.
- Durable active recovery rows expose only the exact remaining adoption work;
  they never replay Provider execution.
- Queue admission retains the explicit statement that it is not execution
  authority.
- No local Provider execution call site, paid action, Human ACCEPT/LOCK,
  publication, or NLE action was added.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `185 passed`.
- Full regression: `1254 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
