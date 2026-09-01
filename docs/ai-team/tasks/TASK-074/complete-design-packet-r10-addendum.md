# TASK-074 Complete Design Packet R10 Addendum

Status: `DESIGN_CANDIDATE_R10_ADDENDUM / DEV-4 / SOURCE_START0 / EFFECT0 / NOT_REVIEWED`

## 1. Frozen parent and precedence

This Owner-authorized controlled correction preserves the R9 task and packet as immutable history:

- `task.md` SHA-256: `265ECB0C95CF5459BB611FE5C4E50068C35EFB8DAF57BBE200EE42D1B08F7D65`;
- `complete-design-packet.md` SHA-256: `4F1B127F34C1B61D191F8E17485DCC38F08AC991544C554C0AC3AF346EC95CF0`;
- exact base/HEAD: `70ba9e369887d3d7ded59e7197d20d133b2b4d38`。

The effective R10 design is the frozen R9 packet plus this addendum. This addendum supersedes only R9's G11 zero-shot same-process capability/handoff clauses and extends the effective acceptance、negative and fault matrices with A36-A39、N50-N55 and F26-F32. Fine-tuned route semantics and every unrelated R9 clause remain unchanged. This file records no Critic、Tester or Judge PASS and creates no implementation、native、private-audio、commit or Production authority.

## 2. Decision

Zero-shot execution retains the isolated TASK-072/TASK-076 child. TASK-074 adds a producer-owned exact-worker delegation boundary; it does not relax process identity or pass private bodies through a command surface. R9 `OWNER_VOICE_REFERENCE_CAPABILITY_V1` and `TASK074_TO_TASK075_EXECUTION_INPUT_V1` cannot satisfy real child execution and are non-executable legacy design coordinates for G11 after R10. Real zero-shot child admission requires both `OWNER_VOICE_REFERENCE_CAPABILITY_V2` and `TASK074_TO_TASK075_EXECUTION_INPUT_V2`.

The canonical TASK-072/TASK-076 branches currently do not publish the Owner-voice-specific begin/process ABIs named below. They are required owner amendments, not inferred authority. Until their exact ABI hashes、completion receipts and owner acceptances are current, G11 remains `OPEN / NOT_CONFIRMED` and model/body effect is zero.

## 3. `OWNER_VOICE_REFERENCE_CAPABILITY_V2`

### 3.1 Closed lease graph

The V2 capability remains a private live broker object with no public constructor、schema、serialization or rehydration path. Its lease state is exactly:

```text
ISSUED
  -> IN_FLIGHT_PARENT_DELEGATION
  -> CHILD_TRANSFER_IN_FLIGHT
  -> CHILD_PAIR_READY
  -> BODY_READ_STARTED
  -> CONSUMED | BURNED | FAILED_CLOSED
```

Every nonterminal state may additionally transition directly to `BURNED | FAILED_CLOSED` under the exact failure rules below. `CONSUMED`、`BURNED` and `FAILED_CLOSED` are terminal and have no outgoing edge. Skipping、rewinding、re-entering or replaying any state is rejected. A new attempt requires a new capability、lease、TASK-072 begin、TASK-076 process readback and operation identity.

### 3.2 Exclusive body authority

| Lease state | Parent broker | Child broker | Body authority invariant |
|---|---|---|---|
| `ISSUED` | owns both pinned originals; delegation entry only | none | read/delivery zero |
| `IN_FLIGHT_PARENT_DELEGATION` | owns both originals for close/transfer only | authenticated handshake only | parent read zero; child read zero |
| `CHILD_TRANSFER_IN_FLIGHT` | owns originals for rollback close only | may hold zero、one or two duplicated handles behind a closed body gate | parent read zero; child read zero |
| `CHILD_PAIR_READY` | original handles are proven closed | owns both exact child-local handles | parent authority zero; child body entry is the sole possible next CAS |
| `BODY_READ_STARTED` | authority/handles zero | owns the only two readers under one shared lease | parent authority zero; exactly one child body budget |
| terminal | handles/authority zero | handles/authority zero after terminal close proof | simultaneous or replay authority zero |

Physical parent originals and child duplicates may coexist only during `CHILD_TRANSFER_IN_FLIGHT`, while both body gates are closed. They never coexist as body-read authorities. `CHILD_PAIR_READY` cannot publish until both child-local handle identities are verified and both parent originals have closed with exact readback. Parent close before complete child-pair verification、child body open before `CHILD_PAIR_READY`, or parent read after `IN_FLIGHT_PARENT_DELEGATION` burns the lease.

## 4. `TASK074_REFERENCE_WORKER_DELEGATION_V1`

### 4.1 Required producer amendments

Delegation starts only after both private producer facts are current:

1. TASK-072 owner-accepted `TASK072_OWNER_VOICE_WORKER_BEGIN_READBACK_V1`, binding the exact current ticket/operation、`JOB_CHILD_ARMED_READBACK_V2` lineage、begin nonce、consumer/build/protocol and `handshake_only=true`、`body_gate=CLOSED`、`model_load_started=false`、`body_read_started=false`;
2. TASK-076 owner-accepted `TASK076_OWNER_VOICE_WORKER_PROCESS_READBACK_V1`, binding the exact current Job/Project/installed context and the already-created child to the same TASK-072 begin lineage, with `handshake_only=true` and `body_gate=CLOSED`。

Copied receipt bytes are insufficient. TASK-074 receives a live private child-process handle from the accepted producer broker and independently pins/read-backs the process. No public PID or receipt can open、select or rebind a process.

### 4.2 Closed child binding

`TASK074_REFERENCE_WORKER_DELEGATION_V1` binds all of the following before either role is duplicated:

- exact Product、Project、VoiceProfile、Consent、selection、reference pair、operation and semantic operation key;
- exact `OWNER_VOICE_REFERENCE_CAPABILITY_V2` and shared lease identity;
- exact TASK-072 ticket、begin receipt ABI/hash、begin nonce and inherited private control-channel identity;
- exact TASK-076 Job、current Job/process readback ABI/hash and selected currentness;
- broker-held child process handle plus process creation identity/time, parent identity and expected child identity;
- fixed Windows Job object identity with `kill-on-close=true` and `breakaway_allowed=false`;
- installed instance/build identity、Windows user SID、session ID、logon LUID and exact access-token identity/integrity/elevation facts;
- packaged executable physical identity、publisher/signature verification receipt、image sha256、Product build and worker code sha256;
- fixed worker protocol version、private channel transcript head、challenge and begin nonce;
- exact consumer `TASK-075`、the two closed roles `REFERENCE_AUDIO_READ_HANDLE` and `REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`, and effect flags all false before pair readiness。

The record is private live broker state, noncopyable、nonserializable、nonpickleable、restart-invalid and one-use. It contains no caller-selected PID、process handle value、raw handle value、argv、environment variable、path、URI、base64、audio、transcript、key or secret. A hash/public mapping/dataclass cannot select the child or reconstruct delegation authority.

### 4.3 All-or-none transfer

The only valid transfer is:

1. CAS `ISSUED -> IN_FLIGHT_PARENT_DELEGATION`, permanently disabling parent body entry;
2. authenticate the already-created handshake-only/body-blocked child through the pinned process handle、TASK-072 begin and TASK-076 process readback;
3. CAS to `CHILD_TRANSFER_IN_FLIGHT` and duplicate the audio and transcript handles, in closed role order, directly into the exact child-local broker;
4. challenge/read back both child-local role identities without opening either body;
5. close both parent originals and prove both closures;
6. CAS once to `CHILD_PAIR_READY`; only then may the child broker CAS to `BODY_READ_STARTED` and open both readers under the shared lease。

The logical transfer is all-or-none even though the OS duplicates handles one at a time. There is no success receipt for one role. Duplicate order、numeric handle values and process identifiers never cross the private broker boundary.

If any step after delegation entry fails, TASK-074 requests the accepted TASK-072/TASK-076 abort route, closes the kill-on-close Job owner, terminates the exact child if still live, waits for exact process exit, obtains `TASK074_REFERENCE_WORKER_REMOTE_CLOSE_PROOF_V1` binding both remote roles absent/closed, closes any remaining parent originals, and ends `BURNED | FAILED_CLOSED`. Unknown terminate/wait/remote-close status is `FAILED_CLOSED / NOT_CONFIRMED`, never success or retry. No unrelated process is killed; mismatch or unavailable pinned identity stops without PID fallback.

Child exit at or after `CHILD_PAIR_READY` closes both child handles through the Job/process owner and burns the lease. Exit after `BODY_READ_STARTED` does not prove whether model effect occurred; TASK-072/TASK-076 terminal readback owns that truth, and the operation is never replayed.

## 5. `TASK074_TO_TASK075_EXECUTION_INPUT_V2`

V2 keeps R9's closed outer durability union and inner route union, but the zero-shot subvariant becomes `ZERO_SHOT_REFERENCE_INPUT_V2` and the fine-tuned subvariant becomes `FINE_TUNED_MODEL_INPUT_V2`.

### 5.1 Zero-shot

`ZERO_SHOT_REFERENCE_INPUT_V2` requires:

- every R9 zero-shot pair/media/transcript/currentness binding;
- exact V2 capability、shared lease and `TASK074_REFERENCE_WORKER_DELEGATION_V1` binding;
- exact TASK-072 Owner-voice begin ABI/hash/readback and begin nonce;
- exact TASK-076 Owner-voice worker-process ABI/hash/readback;
- exact child process/build/image/token/Job/channel binding digest;
- lease state `CHILD_PAIR_READY` for the exact TASK-075 child;
- ModelCandidate fields exact null。

TASK-075 may redeem it only in the bound child and only by the child-local broker transition to `BODY_READ_STARTED`. Missing delegation、wrong child or any V1 capability/input gives body/model effect zero.

### 5.2 Fine-tuned

`FINE_TUNED_MODEL_INPUT_V2` retains the R9 ModelCandidate-only contract. Capability、delegation、TASK-072 Owner-voice child begin、TASK-076 worker-process、reference pair、media、transcript、role set、lease and child-process binding fields are exact null/empty. Fine-tuned execution never enters the TASK-074 reference broker.

### 5.3 G11 replacement

R10 G11 closes only when all are exact and mutually bound:

- TASK-075 owner acceptance of `TASK074_TO_TASK075_EXECUTION_INPUT_V2` ABI hash、closed rejection enum and metadata-only positive/invalid fixture corpus;
- TASK-072 owner acceptance and canonical completion of `TASK072_OWNER_VOICE_WORKER_BEGIN_READBACK_V1`, bound to its exact child arm/start protocol;
- TASK-076 owner acceptance and canonical completion of `TASK076_OWNER_VOICE_WORKER_PROCESS_READBACK_V1`, bound to exact current Job/process readback;
- TASK-074 owner-reviewed implementation receipt for V2 capability/delegation and remote-close proof;
- exact installed Product build、consumer、protocol、channel and all producer currentness readbacks。

Absence、staleness、ABI drift or owner non-acceptance of any item leaves G11 `OPEN / NOT_CONFIRMED`; V1 cannot substitute and effect is zero.

## 6. Acceptance additions

| ID | Acceptance |
|---|---|
| A36 | `OWNER_VOICE_REFERENCE_CAPABILITY_V2` implements the exact closed delegation lease graph with terminal failure edges and no parent/child simultaneous body authority. |
| A37 | Delegation selects only an already-created handshake-only/body-blocked child through a broker-held process handle and exact TASK-072/TASK-076 current readbacks; caller PID/handle/path authority is zero. |
| A38 | Both role handles transfer all-or-none; partial transfer terminates/waits the exact no-breakaway kill-on-close child, proves remote close, closes originals and burns/fails closed. |
| A39 | `TASK074_TO_TASK075_EXECUTION_INPUT_V2` requires delegation/process bindings only for zero-shot, requires exact null/empty for fine-tuned, and cannot close G11 without all three owner acceptances. |

## 7. Negative additions

| ID | Condition | Required result |
|---|---|---|
| N50 | missing/stale/cross-operation TASK-072 begin or TASK-076 Job/worker-process readback | delegation and child body/model effect zero |
| N51 | caller-selected PID、raw/native handle value、argv/env/path/URI/base64/body used to select or feed the child | reject before transfer; leak test fail |
| N52 | wrong transfer order、one role only、duplicate role、partial child acceptance or pair-ready before both parent closes | exact child abort/terminate/wait/remote-close; lease burned/failed closed |
| N53 | parent body read after delegation entry、child body read before `CHILD_PAIR_READY` or concurrent parent/child entry | both reads rejected; lease burned; model call zero |
| N54 | missing kill-on-close、breakaway allowed、wrong process creation/token/user/session/logon/image/signature/hash/build/protocol/channel/nonce | delegation zero; no PID fallback or retry |
| N55 | V2 zero-shot lacks delegation/process/V2 capability or uses any ModelCandidate field; fine-tuned has any non-null reference/delegation/process field | TASK-075 body/model read zero |

## 8. Fault additions

| ID | Crash/fault seam | Required recovery truth |
|---|---|---|
| F26 | `PURGE_PENDING` is current but crash occurs before the first role key-revoke begins | append/read back `RL=PURGE_NOT_CONFIRMED / RO=PUBLISHED`; only the R9 exact non-foreign recovery edge plus a new Human purge action may retry |
| F27 | crash after `IN_FLIGHT_PARENT_DELEGATION` before child duplication | parent body stays disabled; close both originals、abort/wait child if created、burn/fail closed; child read/model call zero |
| F28 | first role duplicated but second duplication fails | terminate exact child、wait、prove both remote roles closed、close both originals、burn; pair-ready zero |
| F29 | both roles duplicated but child pair challenge/readback fails | body gate remains closed; exact abort/terminate/wait/remote-close and parent close; no `CHILD_PAIR_READY` |
| F30 | parent originals close, then broker crashes before `CHILD_PAIR_READY` CAS/readback | child remains body-blocked; restart cannot rehydrate; Job kill-on-close/abort、wait and remote-close proof; `FAILED_CLOSED` |
| F31 | child dies or channel closes after `CHILD_PAIR_READY` but before `BODY_READ_STARTED` | remote handles close, lease `BURNED|FAILED_CLOSED`, body/model call zero, replay zero |
| F32 | child/parent/broker dies after `BODY_READ_STARTED` before terminal receipt | terminate/wait and remote-close proof; no `CONSUMED`; TASK-072/TASK-076 exact terminal owns known/unknown effect truth; replay zero |

## 9. R10 verification and freeze gate

The effective matrix totals are A01-A39、N01-N55 and F01-F32, with no duplicate IDs. Implementation must add deterministic non-biometric tests for every new vector, including process-handle fakes that never use a real PID or private body. F28-F30 must assert body gate closed、model call count zero、both remote closes proven and parent originals closed. F31/F32 must distinguish pre-body known-zero from post-body effect-unknown without replay.

R10 design completion still requires fresh independent Tester、Critic and Judge over the exact R9 parent hashes plus this addendum hash, with C/H `0/0` and Judge PASS. TASK-075、TASK-072 and TASK-076 owner acceptances are separate required G11 evidence. This addendum itself performs source/schema/test/native/process/private-audio/model/commit/push/PR effects zero.
