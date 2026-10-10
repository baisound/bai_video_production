# TASK-106 Atomic Unit A — Failure Classification and Shell Recovery Design

## Observed boundary

The reported UI string proves that an exception escaped the bridge and was
rendered by the generic JavaScript RPC helper. It does not prove whether the
error happened before inference, before canonical replacement, or while a lock
context unwound after replacement. Therefore the repair must classify durable
state rather than retry or infer an outcome from the exception text.

The real Ollama transport already converts network `OSError` instances into a
typed external-dependency Product error. Raw `OSError` remains possible around
the Windows file-lock/store boundary. This unit does not change the shared lock
primitive without a reproduced helper defect.

## Backend state machine

```text
confirmation consumed
  -> ordinary guarded apply
     -> success: return new or already-existing exact Proposal
     -> ProductError: preserve existing typed failure
     -> OSError: no retry; perform read-only exact deterministic read-back
        -> exact Proposal: return RECOVERED_COMMITTED projection
        -> no Proposal: ERR_TASK036_PLANNING_APPLY_NOT_COMMITTED
        -> read-back conflict/error: ERR_TASK036_PLANNING_APPLY_STATE_UNKNOWN
```

The read-back revalidates the exact current Project manifest, connection
coordinate, route and policy bound by the consumed confirmation. Only the
existing `_existing` validator may establish an exact committed Proposal. The
original OS exception text and host path are never added to Product details or
returned to the WebView.

`provider_execution_started` changes to true only immediately before invoking
the adapter's `generate` method. Adapter construction and prompt compilation
remain pre-execution preparation; an `OSError` from either must report provider
execution as not started.

Both error results are non-retryable. A later Human may explicitly prepare a new
confirmation after reviewing refreshed canonical state, but neither Python nor
JavaScript automatically invokes the provider again.

`RECOVERED_COMMITTED` is not a claim that lock cleanup succeeded. It claims only
that, after the failed call unwound and its handles closed, the canonical
TASK-027 store read back the exact deterministic Proposal. The response records
that recovery classification so tests and UI do not mistake it for ordinary
execution.

## Shell state machine

```text
READY
  -> one user activation sets in-flight before prepare
  -> PREPARING / Human confirmation / APPLYING or CANCEL
  -> finally clears in-flight
  -> finally reloads Planning canonical state and readiness
```

While in-flight, repeated activation returns without a second bridge call and
the button/header display generation-in-progress. Planning-specific RPC calls
receive fixed Japanese public-safe copy. The generic RPC helper remains
unchanged for unrelated screens in this Atomic Unit.

The top header derives from the same Planning presentation as the pane:

- ready -> `企画AI: 設定済み`;
- active -> `企画AI: 生成中`;
- runtime starting -> `企画AI: 準備中`;
- configured but unavailable -> `企画AI: 要確認`;
- selection missing -> `企画AI: 未設定`.

Home initialization and Home refresh use a bounded read-only helper that reads
only Planning generation status, model selection, Ollama runtime and compute
settings. Both the primary `pywebviewready` path and the 350 ms fallback use
that lifecycle. It does not load or render the full Planning workspace. The
same helper runs after a successful central AI-model settings save, while
closing Settings refreshes the current page and therefore refreshes Home
through the same path. Every helper RPC uses fixed Japanese public-safe error
copy.

Only an actually missing/unselectable Planning selection maps to `未設定`. A
configured selection whose Planning application reports a connection, route or
model blocker maps to `要確認`; an unreadable or unknown selection snapshot also
maps to `要確認`, never `未設定`. Runtime startup, active generation and fully
ready states continue to map to `準備中`, `生成中` and `設定済み` respectively.

## Failure-mode tests

Focused tests use only fake adapters and pytest-owned temporary roots:

1. outer guarded operation raises before its body: zero provider calls, no
   Proposal, typed `NOT_COMMITTED`;
2. provider returns, canonical append raises before save: one provider call, no
   Proposal, typed `NOT_COMMITTED`, same confirmation cannot replay;
3. exact Proposal is saved and outer lock raises during unwind: one provider
   call, exact committed read-back, no second provider call;
4. read-back itself fails or conflicts: typed `STATE_UNKNOWN`, no raw OS text;
5. Project/connection/policy drift and deterministic identity conflict during
   recovery fail closed as typed `STATE_UNKNOWN` without a second adapter call;
6. an event-controlled slow first apply and contended second apply establish
   exactly one provider call and one complete Proposal, with the second caller
   recovering the exact committed Proposal as idempotent;
7. Node UI contract drives concurrent activations and verifies one prepare/apply,
   `finally` refresh, public-safe copy and cleared busy state;
8. Node lifecycle contract executes Home initialization, central model-settings
   save and Settings close, verifying the global header never remains stale.

No test invokes Ollama, a provider, a model, a native Product, build, package or
network endpoint.

## Residual boundary

This unit preserves current crash semantics: if the process terminates after
local inference and before TASK-027 publication, a later explicit Human attempt
may perform inference again. Durable cross-process exactly-once execution would
require a separately designed attempt journal and is not claimed here.
