# TASK-071 — Windows Human Authorization Broker

Status: `DESIGN_COMPLETE / DEV-4 / SOURCE_START0`

Design identity: `TASK071-PTD-WINDOWS-HUMAN-AUTHORIZATION-V1`

Historical design base: `origin/main@35cdf1ad475633dcf035e0616e979b5a8fde0c88`

Current review parent: `origin/main@74b85d7d3f5965cd515ff44bd5f4b7179185e578`

Owner allocation: `2026-09-01 / Platform Trust & Delivery / Design B`

## 1. Decision

TASK-071 owns one Product-private Windows Human Authorization Broker. It is the
only v1 Production boundary that may turn a fresh, action-specific Product plan
and an observed Windows user-presence event into a live one-use Human
authorization capability.

The capability is not a dataclass, JSON receipt, confirmation string, boolean,
hash, module token, timestamp, mouse click or Windows Hello result copied out of
the broker. It exists only as broker-side live state plus an authenticated
inherited channel handle, bound to one Product process, one Windows user/logon
session, one exact action plan and one deadline. First authenticated consume
enters `IN_FLIGHT` and burns the invocation budget on success or exception.

The broker presents a closed Product-owned Japanese confirmation window and
then invokes Windows user verification for that exact broker-owned `HWND`.
Only an in-process `Verified` return from the fixed native interop call is
accepted. The broker persists immutable audit/fork-fence events, but every
durable/public record has `authority_created=false`; copying one cannot
authorize an effect.

V1 supports exactly four Human actions:

- `PREFERENCE_PROMOTE`;
- `PREFERENCE_ROLLBACK`;
- `CONNECTOR_ACTIVATE`;
- `CONNECTOR_DEACTIVATE`.

Migration, Profile binding, D2S staging, GPU launch and read-only status are
non-Human Product operations owned by TASK-072 profiles. An emergency
fail-closed connector disable, if separately required, is a distinct TASK-061
safety action and must not reuse or manufacture TASK-071 activation authority.

## 2. Source-backed gap

Current `origin/main` does not contain a trusted Human authority boundary:

- `issue_human_activation_evidence` accepts caller-selected action, ID,
  issue/expiry timestamps and a predictable confirmation string;
- `HumanActivationEvidence` is a public dataclass guarded only by a reachable
  module object and a computable self-hash;
- activation apply accepts caller `now`, backend and hook seams;
- `confirm_preference_promotion` and `confirm_preference_rollback` accept a
  caller boolean, confirmation ID and timestamp;
- `PreferencePromotionConfirmation.from_dict` reconstructs the purported Human
  confirmation from public JSON;
- promotion/rollback consume public confirmation equality inside a generic file
  lock, rather than a live Human event;
- changing an ID/time creates another apparently valid evidence object.

These objects remain useful historical/audit projections, but they cannot be
Production authorization. Self-hash proves representation consistency, not who
approved an action or whether the approval was current and one-shot.

## 3. Responsibility and non-responsibility

TASK-071 owns:

- the closed v1 Human action registry and per-action display catalog;
- the private `HUMAN_ACTION_ABI_V1` verifier port;
- server-generated operation/challenge IDs, nonce and trusted deadlines;
- a stable semantic Human-operation key and immutable no-replace reservation;
- secure existing/initial Human-operation lease composition through TASK-068;
- a separate packaged Windows broker/UI process and authenticated local IPC;
- current Product/broker/UI image, process, token, SID, session, logon LUID and
  `HWND` attestation;
- availability check and exact Windows user-consent verification invocation;
- explicit Japanese pre-verification review, deny/cancel and no-fallback UX;
- immutable issued/decision/in-flight/terminal audit events;
- private live capability issue, one-use consume and burn semantics;
- trusted time, restart, suspend/resume and expiry policy;
- body/path/identity-free public status and non-authoritative audit receipts;
- versioned fixtures for TASK-060, TASK-061 and TASK-072 integration.

TASK-071 does not own:

- preference candidate, store, DPAPI, promotion or rollback semantics
  (TASK-060);
- migration, Profile binding, activation plan/config/history or emergency
  safety-disable semantics (TASK-061);
- installer instance/pair/root selection (TASK-063/TASK-070);
- generic secure file I/O, strict JSON or locking primitives (TASK-068);
- Profile publication/current-coordinate semantics (TASK-069/TASK-067);
- machine-operation ticket/config/child execution (TASK-072);
- real installed E2E or main Product navigation (TASK-036);
- Canonical SKILL, D2S, File Bridge, learning admission or PL orchestration;
- Windows credentials, PIN, biometric templates, account setup or recovery;
- authentication of a remote user, administrator override or unattended
  approval;
- Release, Deploy, Production Activation, paid Provider, real install, external
  account mutation, private-media upload or destructive cleanup.

## 4. One-way artifact/phase dependency graph

Task names alone would create false cycles because owning Tasks must describe an
action before TASK-071 can ask a Human, while the same Tasks need TASK-071 before
their effect. The graph therefore uses phase artifacts:

```text
TASK-068 IMMUTABLE_SECURE_IO_V1 canonical receipt
    -> TASK-071-A HUMAN_BROKER_CORE_FIXTURE_V1

TASK-070 private INSTALLATION_PAIR_READBACK_V2
TASK-063 INSTALLATION_READBACK_V2
TASK-071-A HUMAN_BROKER_CORE_FIXTURE_V1
    -> TASK-071-B INSTALLED_OPERATOR_BINDING_V1

TASK-060-A PREFERENCE_PROMOTION_HUMAN_ACTION_ABI_V1
TASK-060-A PREFERENCE_ROLLBACK_HUMAN_ACTION_ABI_V1
TASK-071-A/B
    -> TASK-071-P HUMAN_PROMOTION_ACTION_PROFILE_V1

TASK-061-A CONNECTOR_HUMAN_ACTION_ABI_V1
TASK-067 SEALED_CURRENT_COORDINATE_RECEIPT_V1
TASK-036 REAL_INSTALLED_E2E_RECEIPT_V2 [ACTIVATE only]
TASK-071-A/B
    -> TASK-071-C HUMAN_CONNECTOR_ACTION_PROFILE_V1

TASK-071-P/C private HUMAN_AUTHORIZATION_CAPABILITY_V1
TASK-072-A OP_TICKET_CORE_V1
owning Task fresh effect-currentness attestation
    -> TASK-072 Human-gated action ticket
    -> TASK-060-B or TASK-061-B effect

all exact completion receipts
    -> TASK-065 PL completion
```

`*_HUMAN_ACTION_ABI_V1` is a versioned design/fixture contract, not an effect
receipt. TASK-071-A fixtures can freeze before TASK-068 implementation is
canonical. TASK-071-P/C native authority remains `DEPENDENCY_NC` until the exact
producer receipts and packaged broker are present. TASK-060-A and TASK-061-A do
not wait for a Human event; only their effect phases do. This removes
TASK-060/TASK-061/TASK-071/TASK-072 completion cycles.

TASK-068 Draft PR `#472`, TASK-070 Draft PR `#477` and TASK-072 Draft PR `#475`
are design/noncanonical inputs until merged with their exact completion
receipts. This packet creates no authority from those PRs.

## 5. Design PR and future implementation scope

This design PR may change exactly:

- `docs/ai-team/tasks/TASK-071/complete-design-packet.md`

After independent Critic `C/H=0` and Judge `PASS`, a future TASK-071
implementation Task may change exactly:

- `src/ai_video_production/human_authorization.py`
- `src/ai_video_production/human_authorization_windows.py`
- `schemas/human-authorization-reservation.schema.json`
- `schemas/human-authorization-event.schema.json`
- `schemas/human-authorization-audit-receipt.schema.json`
- `src/ai_video_production/schema_resources/human-authorization-reservation.schema.json`
- `src/ai_video_production/schema_resources/human-authorization-event.schema.json`
- `src/ai_video_production/schema_resources/human-authorization-audit-receipt.schema.json`
- `native/task071_human_authorization_broker/CMakeLists.txt`
- `native/task071_human_authorization_broker/include/bvp_human_authorization/protocol.hpp`
- `native/task071_human_authorization_broker/include/bvp_human_authorization/user_consent_verifier.hpp`
- `native/task071_human_authorization_broker/src/main.cpp`
- `native/task071_human_authorization_broker/src/protocol.cpp`
- `native/task071_human_authorization_broker/src/user_consent_verifier.cpp`
- `native/task071_human_authorization_broker/tests/protocol_tests.cpp`
- `native/task071_human_authorization_broker/tests/user_consent_verifier_tests.cpp`
- `native/task071_human_authorization_broker/scripts/build.ps1`
- `native/task071_human_authorization_broker/scripts/test.ps1`
- `native/task071_human_authorization_broker/scripts/package.ps1`
- `tests/test_task071_human_authorization.py`
- `tests/test_task071_human_authorization_windows.py`
- `tests/test_task071_human_authorization_packaging.py`
- `tests/fixtures/task071/valid-reservation.json`
- `tests/fixtures/task071/valid-decision-event.json`
- `tests/fixtures/task071/invalid-duplicate-key.json`
- `tests/fixtures/task071/invalid-replay.json`
- `docs/ai-team/tasks/TASK-071/task.md`
- `docs/ai-team/tasks/TASK-071/implementation-completion-receipt.md`

Changes to TASK-036, TASK-060, TASK-061, TASK-063, TASK-065, TASK-067, TASK-068,
TASK-069, TASK-070, TASK-072, Canonical SKILL, main installer/spec,
`pyproject.toml`, shared current-state/task-index/roadmap, CHANGELOG or another
Task require that owner's separate exact amendment and fresh overlap/lock.

## 6. Threat and trust boundary

### 6.1 Trusted components

Production fixes and attests:

- the packaged BVP Product parent process/image/build;
- the packaged native TASK-071 broker image/build and protocol version;
- the native Windows token/process/window attestation implementation;
- the Windows user-consent interop implementation/version;
- TASK-068 secure immutable I/O implementation/version;
- the trusted clock/boot/session implementation;
- the closed action/display registry version;
- exact owning-Task action verifier versions;
- exact TASK-072 internal consumer port version.

No argv, config, JSON, public plan, environment, registry value, current working
directory, Python dependency injection, module monkeypatch, hook or failure
injector selects a Production backend, message, action or clock. Test doubles
are reachable only through a separately constructed non-Production fixture
composition whose receipts state `native_user_presence_verified=false`.

### 6.2 Protected attackers

V1 protects against:

- public Python/API callers and public-object reconstruction;
- copied/rehashed/deserialized receipts and module-token access;
- caller-selected action, ID, timestamp, expiry, message or window;
- direct CLI/helper invocation without the inherited channel;
- a separately launched same-user process that neither possesses the live
  broker channel nor has obtained rights/access to duplicate or steal it;
- replay, double/concurrent consume and new random request IDs;
- wrong Windows user, session, logon LUID, process, image, build or `HWND`;
- link/ancestor/DACL/file substitution of durable records;
- clock rollback, restart and stale-domain-currentness use;
- automation that clicks the Product review dialog but cannot produce the
  broker's direct verified user-presence result and live state.

### 6.3 Explicit non-goals

V1 does not claim resistance to administrator/kernel compromise, process
injection, debugger/memory access into the trusted Product/broker, replacement
of a legitimately signed/attested package by a compromised release process, or
social engineering performed by another trusted/compromised application.

A same-user process that obtains `OpenProcess(PROCESS_DUP_HANDLE)` access and
uses `DuplicateHandle`, obtains process VM/debug rights, or otherwise steals a
live duplex endpoint is also `NOT_SUPPORTED_V1`. An inherited anonymous-pipe
kernel object proves endpoint possession, not the actual writer PID for each
frame; nonce/transcript hashes do not repair that limitation. An exact
signed-image sibling holding a stolen endpoint is inside this unsupported set.
These attacks are recorded as threat-model exclusions and must never be counted
as passed security negatives. Protecting them requires a separately allocated
isolation design such as a service/AppContainer/PPL boundary with an IPC
mechanism that supplies enforceable peer identity.

Windows user verification proves presence of the current Windows user, not the
domain action by itself. Action consent exists only because the broker directly
couples that result to its already displayed, hash-bound, fixed action plan and
live challenge. A standalone `Verified` enum value is data, not authority.

## 7. Closed action ABI and registry

### 7.1 `HUMAN_ACTION_ABI_V1`

The owning Task supplies a private, nonserializable, already-current action
authorization plan over the authenticated Product channel. Common closed fields
bind:

- producer Task, action ABI type/version and verifier implementation digest;
- stable `human_operation_key` derived from the complete intended Human effect;
- exact action enum and invocation budget one;
- TASK-063 installation receipt and private TASK-070 pair readback identity;
- expected operator SID hash, session policy and owner/DPAPI scope where
  applicable;
- exact domain plan/body digest and expected current revision/head/state;
- exact target state, profile/candidate/rollback/config binding;
- exact prerequisite receipt/currentness set and build/backend identities;
- closed privacy-safe `HUMAN_DISPLAY_PROJECTION_V1` digest;
- expected TASK-072 action profile and eventual consumer operation key basis;
- fixed TASK-071 lifetime policy version.

The key excludes caller request ID, challenge ID, nonce, timestamp, broker boot
and random ticket. Reissuing the same semantic plan with a new ID therefore
collides with its durable reservation. A retry requires a fresh owning-Task
plan/currentness revision bound to the prior terminal; TASK-071 never invents
that revision.

Public plan objects, self-hashes, booleans or mappings are display/audit data
with `authority_created=false`. The broker invokes the internally fixed owning
verifier over the live private plan before any durable or UI effect.

### 7.2 Exact action matrix

| Action | Producer ABI | Required private binding | TASK-072 machine profile |
|---|---|---|---|
| `PREFERENCE_PROMOTE` | TASK-060-A `PREFERENCE_PROMOTION_HUMAN_ACTION_ABI_V1` | candidate digest; expected store revision/head; proposed profile/version; current DPAPI user/owner scope; TASK-063/070 installed instance | future versioned `PREFERENCE_PROMOTE_APPLY` |
| `PREFERENCE_ROLLBACK` | TASK-060-A `PREFERENCE_ROLLBACK_HUMAN_ACTION_ABI_V1` | expected store revision/head; exact rollback target revision/digest/profile; current DPAPI user/owner scope; TASK-063/070 instance | future versioned `PREFERENCE_ROLLBACK_APPLY` |
| `CONNECTOR_ACTIVATE` | TASK-061-A `CONNECTOR_HUMAN_ACTION_ABI_V1` | enabled-false config candidate/current revision; source/Profile/instance; TASK-067 coordinate; TASK-036 real E2E; installed D2S/build | `ACTIVATION_CONFIG_FINALIZE` |
| `CONNECTOR_DEACTIVATE` | TASK-061-A `CONNECTOR_HUMAN_ACTION_ABI_V1` | enabled-true current config/revision; source/Profile/instance; explicit deactivation plan; no adapter E2E substitute | versioned `DEACTIVATION_CONFIG_FINALIZE` |

Unknown actions, cross-action reuse, extra/missing producer receipts or a
producer/version not in this table fail before reservation/challenge/UI effect.
Promotion and rollback are separate actions; activation and deactivation are
separate actions. No action receipt is substitutable for another.

#### 7.2.1 Future owner-voice V2 amendment and TASK-074 G06

The four V1 actions above do not satisfy TASK-074 gate `G06` and cannot be
relabelled, wrapped or replayed as an owner-voice authorization. TASK-074-C/D
remain `DEPENDENCY_NC / GATED_MUTATION_ZERO` until TASK-071 V1 is canonical and
an overlap-free amendment separately freezes and implements
`HUMAN_ACTION_REGISTRY_V2`.

That V2 registry contains exactly these six additional actions:

- `OWNER_VOICE_REFERENCE_PREPARE_V1`;
- `OWNER_VOICE_LOCAL_INFERENCE_V1`;
- `OWNER_VOICE_LISTENING_DECISION_V1`;
- `OWNER_VOICE_REGENERATE_V1`;
- `OWNER_VOICE_REFERENCE_REVOKE_V1`;
- `OWNER_VOICE_REFERENCE_PURGE_V1`.

Each action has a separate producer ABI, fixed Japanese display projection,
stable semantic operation key, one-use live broker capability and exact
TASK-072 consumer profile. A V1 capability, a serialized/public V2 receipt or
any other V2 action is not a substitute. TASK-074 `G06` passes only when the
broker holds the live, nonserializable `TASK071_V2_LIVE_BROKER_RECEIPT` for the
exact requested action and the owning TASK-074/TASK-075 domain currentness is
freshly verified at the consume seam. The public projection remains audit data
with `authority_created=false`.

`OWNER_VOICE_REFERENCE_REVOKE_V1` closes new lease/body-read entry and drives
the exact active lease to a burned or closed terminal; it does not delete a
key, ciphertext or directory. `OWNER_VOICE_REFERENCE_PURGE_V1` is a separate
Human action and may be issued only after TASK-074 `G09` proves an exact
revoked prepared-reference head or retained-failure recovery head, exact-owned
physical identities, no nonterminal lease and the dedicated purge consumer
profile. A revoke decision never implies purge, and purge cannot reuse prepare,
inference, listening, regenerate or revoke authority.

The V2 amendment must bind Project, installed instance, Windows user/logon
session, VoiceProfile and consent revision, TASK-074 lifecycle head, TASK-046
reference/transcript binding where applicable, TASK-072 ticket/profile,
trusted deadline and one invocation. Wrong/cross action, copied receipt,
second/concurrent use, expiry, restart, exception, stale lifecycle head or
missing G06/G09 predecessor is effect zero. Real Owner audio, custody,
inference, listening, revoke and purge remain separate native Human Gates; this
V1 design packet performs none of them.

`CONNECTOR_ACTIVATE` challenge issuance occurs only after the real installed
E2E/current-coordinate prerequisite set exists. TASK-061-A can freeze its ABI
and enabled-false candidate earlier, but that earlier artifact cannot make the
Human prompt available or create a receipt.

### 7.3 Closed display projection

The projection contains only bounded typed fields selected by the action
catalog:

- Japanese action title and fixed explanation selected by enum, not caller text;
- opaque installation label and short Product-generated operation code;
- current and target state labels;
- profile/version or rollback version where applicable;
- one fixed warning that the action is one-shot and cannot be automatically
  retried;
- `private_data_included=false`, `path_included=false`,
  `credentials_requested_by_product=false`.

No free-form reason, absolute path, SID, account name, candidate body, prompt,
secret, token, OS error or caller-supplied message enters either the Product
window or Windows verification message.

## 8. Broker process, channel and Windows attestation

### 8.1 Process composition

The Product starts the packaged native broker with a restricted inherited
handle list. There is no named pipe, TCP socket, globally discoverable endpoint,
environment token, command-line action/config/nonce or reusable secret. The
broker accepts exactly one parent channel and exits after terminal/burn.

Before accepting the plan and again before challenge issue, verification result
acceptance and capability consume, the broker attests:

- Product parent PID/image path identity/build/signature manifest;
- broker image path identity/build/signature manifest;
- both process access-token user SIDs;
- `TokenSessionId`, token statistics authentication ID/logon LUID, elevation and
  integrity policy;
- parent relationship and inherited channel object identity;
- interactive desktop/session currentness;
- broker-owned top-level `HWND`, window thread/process owner, visibility and
  enabled/modal state;
- no handle inheritance beyond the closed allowlist.

Raw paths, SIDs, LUIDs, handles, PIDs and `HWND` values never appear in public
receipts or logs. Private records bind their hashes and implementation version.
These are launch-time/currentness and endpoint-possession checks within the
supported threat model. They do not claim per-frame writer-PID proof after an
attacker has duplicated or stolen the endpoint.

### 8.2 IPC protocol

IPC uses a closed 4-byte little-endian length-prefixed binary frame carrying
strict canonical UTF-8 JSON. Maximum frame size is 64 KiB and maximum complete
transcript is 256 KiB. Sequence is exact:

```text
HELLO -> HELLO_ACCEPTED
ACTION_PLAN -> PLAN_ACCEPTED
CHALLENGE_BOUND -> REVIEW_VISIBLE
REVIEW_DENIED | REVIEW_ACCEPTED
USER_VERIFICATION_STARTED
USER_VERIFICATION_FAILED | USER_VERIFICATION_VERIFIED
AUTHORIZATION_GRANTED
BEGIN_CONSUME -> IN_FLIGHT
COMMITTED | BURNED_UNKNOWN
```

Every frame binds protocol version, sequence, transcript hash, server nonce,
operation/challenge identity and channel object. Duplicate keys, noncanonical
JSON, unknown frame/field, wrong sequence, oversized/truncated frames, replayed
nonce and extra bytes close the channel and burn the operation. An unauthenticated
process that lacks the legitimate or a stolen/duplicated live endpoint cannot
identify, cancel or burn another operation. Here `authenticated channel` means
the launch-bound channel under the section 6.3 threat boundary, not a claim that
anonymous-pipe frames expose a kernel-authenticated sender PID.

The UI process never accepts a serialized Human receipt. The TASK-072 consumer
receives only a restricted duplicate of the exact live broker channel after the
owning Task has revalidated domain currentness.

## 9. Windows user-presence backend

### 9.1 Fixed API

Production uses the Win32 desktop interop
`IUserConsentVerifierInterop::RequestVerificationForWindowAsync` with the exact
broker-owned active `HWND`. Microsoft documents that this call performs
verification using Windows Hello/PIN/biometric and that the interop API is for a
specific app window on Windows build 22000 or later:

- https://learn.microsoft.com/windows/win32/api/userconsentverifierinterop/nf-userconsentverifierinterop-iuserconsentverifierinterop-requestverificationforwindowasync
- https://learn.microsoft.com/windows/apps/develop/ui/display-ui-objects

The broker checks `UserConsentVerifier.CheckAvailabilityAsync` immediately
before showing its review window. Only `Available` proceeds:

- https://learn.microsoft.com/uwp/api/windows.security.credentials.ui.userconsentverifier.checkavailabilityasync

Only the direct asynchronous result `UserConsentVerificationResult.Verified`
proceeds. `DeviceNotPresent`, `NotConfiguredForUser`, `DisabledByPolicy`,
`DeviceBusy`, `RetriesExhausted`, `Canceled`, unknown enum, HRESULT failure,
timeout or callback/thread mismatch burns the challenge and creates no
authorization:

- https://learn.microsoft.com/uwp/api/windows.security.credentials.ui.userconsentverificationresult

### 9.2 Platform gate

V1 Production Human authority requires Windows build 22000 or later and an
available verifier for the current interactive user. Older Windows, Server,
headless/RDP policy denial, unavailable/not-configured Hello or an unowned
window fails closed with stable guidance. There is no fallback to a plain
button, typed confirmation phrase, app password, UAC/admin elevation, custom PIN
collection, security question or caller assertion.

TASK-071 never receives a PIN, biometric sample, credential, recovery key or
authentication secret. Windows owns that UI and data. BVP observes only the
result in the trusted broker call.

### 9.3 Meaning of verification

The broker verifies its window owner/process/session before the call and again
after completion. It binds the review-projection digest, challenge nonce hash,
action and trusted process/session snapshot to the direct result. The result
enum cannot be passed into a public factory. A fake/custom backend or a
monkeypatched result is permitted only in fixture composition and always emits
`native_user_presence_verified=false`.

## 10. Durable artifacts and private capability

All durable records are strict immutable audit/fork-fence documents written and
read only through the fixed TASK-068 private port under the exact TASK-070
installer-authority parent. TASK-071 accepts no path. It never uses a generic
atomic writer as authority and never mutates, repairs or deletes a record.

Every phase coordinate is deterministically derived from the reservation plus a
closed phase slot. Mutually exclusive outcomes share one no-replace slot:
`DENIED/CANCELED/VERIFICATION_FAILED/VERIFIED` share `DECISION`, and
`COMMITTED/BURNED_UNKNOWN` share `TERMINAL`. `IN_FLIGHT` also has exactly one
slot. Competing identical/different outcomes therefore cannot both become
durable; a collision is preserved and stops without choosing a latest event.

### 10.1 `HUMAN_AUTHORIZATION_RESERVATION_V1`

Before any challenge or visible UI, the broker derives a coordinate solely from
the stable `human_operation_key`, action registry version and installed
instance. It publishes the reservation no-replace under a secure
existing/initial operation lease and pins its exact readback.

The reservation body binds the verified action-plan fingerprint, producer/
verifier versions, expected operator/session policy, display digest, random
server operation/challenge identities, broker/build/backend/clock identity and
expected first-event coordinate. Random IDs are in the body but never influence
the coordinate.

An existing reservation with a different body is `HUMAN_OPERATION_COLLISION`.
An identical reservation is not enough to reissue authority. Only an exact
already committed consumer terminal may be reported as audit `DUPLICATE`; a
reservation with no exact terminal is `BURNED_OR_RECOVERY_REQUIRED`. All records
are preserved.

### 10.2 `HUMAN_CHALLENGE_ISSUED_V1`

The broker generates at least 256 random nonce bits with the fixed Windows
system-preferred cryptographic RNG and generates opaque operation/challenge IDs.
The durable event binds nonce hash, reservation, action plan,
display digest, trusted issue/deadline coordinates, operator/session policy,
broker/UI/Product builds and expected decision coordinate. Raw nonce remains
only in live broker memory. The short display code derived from it is for Human
cross-check only and has `authority_created=false`.

### 10.3 `HUMAN_DECISION_EVENT_V1`

Exactly one no-replace event records `DENIED`, `CANCELED`, `VERIFICATION_FAILED`
or `VERIFIED`. A `VERIFIED` event binds both pre/post process-token-window
attestations, direct backend result, action/display/challenge, trusted time,
transcript hash and expected consumer profile. It remains audit evidence with
`authority_created=false`.

### 10.4 `HUMAN_AUTHORIZATION_CAPABILITY_V1`

After the verified event's pinned readback and a final process/session/clock/
plan currentness check, the broker creates one live server record. The private
capability is the identity of that server record plus the exact authenticated
channel object. It has:

- one action and one expected consumer profile;
- one installation/operator/session/logon identity;
- one action-plan/currentness fingerprint;
- one broker boot and deadline;
- invocation budget exactly one;
- state `GRANTED`, then `IN_FLIGHT`, then terminal/burned.

There is no public constructor, `from_dict`, pickle/copy support, self-hash
factory, module secret or serialized capability. Public audit projection cannot
be passed to an effect API.

### 10.5 consume events

On first authenticated `BEGIN_CONSUME`, the broker revalidates the exact
TASK-072 process/channel, consumer profile, owning Task fresh-currentness
attestation, Product/broker images, user/session/logon and deadline. It durably
publishes `HUMAN_AUTH_IN_FLIGHT_V1` before returning a private consumed handle.
The invocation budget is burned at method entry, including wrong command,
validation exception, timeout, cancellation, channel close or child failure.

An exact owning consumer terminal may then be bound by immutable
`HUMAN_AUTH_TERMINAL_V1` as `COMMITTED`. Any other post-entry outcome is
`BURNED_UNKNOWN`; absence of a terminal never restores authority. A read-only
status query may compare the exact committed terminal and return audit
`DUPLICATE`, but it cannot issue another capability.

## 11. Human review UX

The broker owns one modal window. The default/focused action is `キャンセル`.
Enter, Space, window activation, timeout or accessibility focus never approves.
The Human must deliberately select `内容を確認して続ける`, after which Windows
verification appears for the same broker-owned window.

Closed Japanese action copy:

| Action | Title | Primary explanation |
|---|---|---|
| `PREFERENCE_PROMOTE` | `学習設定を採用します` | `確認した候補を現在の編集支援設定として採用します。` |
| `PREFERENCE_ROLLBACK` | `学習設定を以前の版へ戻します` | `表示された版を新しい履歴として採用します。元の履歴は削除しません。` |
| `CONNECTOR_ACTIVATE` | `学習コネクターを有効にします` | `確認済みのインストールと接続結果に対して学習コネクターを有効にします。` |
| `CONNECTOR_DEACTIVATE` | `学習コネクターを無効にします` | `学習コネクターを無効にする履歴を追加します。学習データは削除しません。` |

The Windows verification message uses a separate closed short template with
the action title and operation display code. The caller cannot provide it.

Unavailable guidance is bounded:

- `Windows Helloを利用できないため、この操作を続けられません。`
- `Windowsのサインイン オプションでWindows Helloを設定してから、最新の内容でもう一度開始してください。`

TASK-071 returns a status/CTA code only. Opening Windows Settings belongs to the
Product UI owner and is not automatic. No dialog displays a path, SID, user
name, receipt body, hash, nonce, timestamp, backend or OS error.

Cancel, close, timeout and every non-Verified result burn the challenge. There
is no automatic retry. A Human-initiated retry requires the owning Task to
produce a fresh predecessor-bound plan/currentness revision.

## 12. Consumer transaction integration

### 12.1 Prepare

1. Owning Task pins and verifies all domain inputs and produces its private
   action ABI plus safe display projection.
2. TASK-071 verifies the ABI, installed/operator binding and stable operation
   key under the secure lease.
3. TASK-071 publishes/readbacks reservation and challenge before showing UI.
4. Broker revalidates process/token/session/window and checks verifier
   availability.
5. Human reviews the fixed Product window and explicitly continues or denies.
6. Broker invokes Windows verification for its exact `HWND`.
7. Only direct `Verified` plus post-call attestation publishes the verified
   decision and creates live capability.

### 12.2 Apply handoff

1. Owning Task reacquires its domain transaction/lease and freshly revalidates
   plan, store/config revision, source, install instance, security and all
   action-specific prerequisites.
2. It creates a private `HUMAN_EFFECT_CURRENTNESS_ATTESTATION_V1` bound to the
   same action-plan fingerprint and intended TASK-072 consumer operation key.
3. TASK-072 and TASK-071 mutually attest their fixed processes/builds/channels.
4. TASK-071 `BEGIN_CONSUME` durably enters `IN_FLIGHT` and burns Human authority.
5. TASK-072 durably enters its own ticket `IN_FLIGHT` before the owning effect.
6. Owning Task rechecks its commit seam and performs at most one exact effect.
7. Exact domain and TASK-072 terminal identities are returned to TASK-071 for
   the audit terminal. They never revive the capability.

The domain lease is held from step 1 through effect readback. Any domain drift
between Human verification and apply fails before Human consume where possible;
any drift after consume fails closed with the Human capability burned. This is
intentional: user presence is not reusable after an ambiguous attempt.

### 12.3 Action-specific rules

- Promote and rollback revalidate the exact strict pinned TASK-060 store,
  revision/head, DPAPI user/session/backend and candidate/target immediately
  before consume and again before store publication.
- Activate revalidates TASK-061-A plan/config candidate/current revision,
  TASK-063/070 instance, source/Profile, TASK-067 coordinate, installed D2S and
  TASK-036 real E2E before consume and at the activation commit seam.
- Deactivate binds the exact enabled current config/revision and adds a disabled
  history event. It cannot reuse activation E2E or activation capability.
- A future emergency fail-closed disable uses a different explicitly allocated
  action/profile and cannot report Human authorization.

## 13. Trusted clock, expiry and restart

Caller time never enters authority or persisted event timestamps. Production
uses one fixed native clock profile bound to Product/broker build, boot and
interactive logon session. It combines a monotonic boot clock proven by native
tests to advance across supported suspend/resume with precise UTC for bounded
audit. Authority remains current only while all clock/session predicates agree.

Fixed v1 policy:

- review challenge deadline: five minutes from durable issue;
- verified-to-consume deadline: sixty seconds;
- invocation budget: one;
- process/broker restart: all nonterminal live capabilities burned;
- boot, user, logon LUID or interactive session change: burned;
- wall-clock rollback or inconsistent clock relation: burned;
- large forward jump: expired/fail closed;
- suspend/resume crossing a deadline or uncertain clock support: expired;
- timezone/DST change: audit only and cannot extend deadline;
- concurrent expiry/consume: broker serialization produces one result.

The event `occurred_at` comes from the trusted broker after the OS event. A
caller-provided timestamp is never copied to history. A test clock is available
only in non-Production composition and cannot be selected from argv/config/
plan/receipt/environment or monkeypatch.

On restart, TASK-071 does not scan for a latest operation and does not recreate
live state from durable receipts. An exact status/recovery query may read
caller-independent known coordinates and classify the chain, but a prior
`GRANTED`/`IN_FLIGHT` without exact committed terminal is permanently
`BURNED_UNKNOWN` for authorization purposes. Fresh action-plan currentness is
required.

## 14. Strict parsing, secure I/O and durability

All authority/event JSON uses TASK-068 strict bounded UTF-8 parsing from the
same pinned no-follow opened handle before semantic validation or hashing. It
rejects:

- duplicate keys at any depth, equal or different;
- NaN, Infinity and negative Infinity;
- BOM, trailing non-whitespace, invalid UTF-8 and disallowed controls;
- non-built-in JSON values;
- unknown/missing fields and wrong exact types;
- oversized bytes/string/depth/member/item/node counts;
- noncanonical writer representation.

Raw bytes hash, canonical parsed hash, physical identity, ancestor/security
snapshot and exact coordinate stay bound in one private snapshot. Ambiguous
files are preserved and never repaired, rewritten or deleted.

The fixed operation lock uses TASK-068 secure initial/existing semantics under
the TASK-070 pinned parent: initial `CREATE_NEW`, no-follow/open-reparse,
one-byte regular file, `nlink==1`, non-inheritable handle and post-create
identity/DACL verification; existing open and lock on the same verified handle.
A create-race loser is freshly classified and fails; no automatic retry.

Every reservation/event is operation-owned, canonical, fsynced, no-replace,
directory-durable and pinned-read back through TASK-068. File or directory
durability failure is failure/completion-unknown, never PASS. TASK-071 performs
no temp cleanup, published cleanup, rollback, restore, overwrite, delete or GC.

## 15. State machine

```text
REQUESTED (public/status only)
  -> ACTION_PLAN_VERIFIED
  -> INSTALLED_OPERATOR_BOUND
  -> LEASED
  -> RESERVED (immutable stable human_operation_key fence)
  -> CHALLENGE_ISSUED (durable; live nonce)
  -> REVIEW_VISIBLE
       -> DENIED/CANCELED/BURNED
       -> REVIEW_ACCEPTED
  -> USER_VERIFICATION_IN_FLIGHT
       -> VERIFICATION_FAILED/BURNED
       -> VERIFIED_EVENT_DURABLE
  -> GRANTED (live capability only)
  -> IN_FLIGHT (first authenticated consume; budget burned)
       -> COMMITTED (audit terminal)
       -> BURNED_UNKNOWN
```

Rules:

1. Public requests/status cannot select action, plan, user, ID, time or backend.
2. Reservation is durable before challenge/UI and independent of random IDs.
3. Visible review starts only after reservation/challenge exact readback.
4. Default/cancel/non-Verified paths create no capability.
5. Verified audit data alone creates no capability.
6. The live capability expires/burns on channel/process/session/currentness loss.
7. `IN_FLIGHT` is durable before any owning effect and burns exactly once.
8. Success and exception both end authority; restart never restores it.
9. Only the same exact committed domain/TASK-072 terminal is audit
   `DUPLICATE`; different body/identity is collision STOP.
10. No Human event authorizes a different action, plan, instance or user.

## 16. Fault and recovery policy

| Seam | Result | Effect/recovery rule |
|---|---|---|
| ABI/operator/currentness invalid | `REJECTED` | durable/UI/capability/effect zero |
| Lock race/link/DACL drift | `SECURITY_STOP` | preserve all; retry zero |
| Reservation collision | `HUMAN_OPERATION_COLLISION` | winner preserved; challenge/UI zero |
| Crash after reservation | `BURNED_OR_RECOVERY_REQUIRED` | reservation preserved; no reissue/adopt/delete |
| Challenge fsync/readback failure | completion unknown | UI/capability zero; artifacts preserved |
| UI/window/process drift | `UI_SECURITY_STOP` | challenge burned; no Windows call/capability |
| Human deny/cancel/close/timeout | `NOT_AUTHORIZED` | decision audit only; capability/effect zero |
| Hello unavailable/non-Verified/error | `USER_VERIFICATION_FAILED` | challenge burned; no fallback/retry |
| Crash after Verified event | `BURNED_UNKNOWN` | event preserved; capability not reconstructed |
| Domain drift before consume | `STALE_ACTION` | capability burned or expires; effect zero |
| Consume event durability failure | `BURNED_UNKNOWN` | effect zero; no second consume |
| Exception after `IN_FLIGHT` | `BURNED_UNKNOWN` | owning state preserved/reconciled; no replay |
| Same committed terminal query | audit `DUPLICATE` | no new capability/effect |
| Different terminal/body/identity | `HUMAN_RECEIPT_COLLISION` | STOP; preserve all |
| Broker/Product restart | `BURNED_UNKNOWN` | all nonterminal live state gone; fresh plan required |
| Cleanup failure | stable warning only | cleanup never determines correctness |

## 17. Privacy and public diagnostics

Public status/audit receipt fields are closed to:

- schema/status/action code;
- opaque operation/challenge/display IDs;
- opaque plan/receipt hashes;
- stable reason code and retry policy;
- `human_review_displayed` / `user_verification_observed` audit booleans;
- `authority_created=false`, `effect_authorized=false`,
  `credentials_collected=false`.

They contain no absolute path, user/account name, SID/LUID, PID/HWND/handle,
DACL, OS error/HRESULT, action body, candidate/profile contents, source text,
nonce, deadline, credential, PIN, biometric data, secret or offending value.
Logs/stdout/stderr use the same body-free codes. Exceptions are translated at
the broker boundary; raw native error text is never sent to the Product UI.

Durable public receipts are audit projections only. `human_confirmed=true`,
`explicit_human_confirmation_received=true`, `safe_export=true` or any similar
boolean from a caller is ignored/rejected and never set by deserialization.

## 18. Negative matrix

Every negative separately asserts reservation/event delta, UI/verification
invocation count, live capability count, TASK-072 ticket count, owning
store/Profile/config/history delta, child/process effect and unrelated-file
overwrite/delete delta.

### T71-AUTH

- public dataclass/mapping/factory/from_dict/self-hash/module sentinel;
- copy/replace/subclass/duck type/pickle/deserialization;
- predictable confirmation string, `human_confirmed=True`, raw Verified enum;
- caller action, request/challenge/evidence ID, timestamp, expiry, message,
  backend, clock, window or hook;
- public TASK-060/TASK-061/TASK-070/TASK-072 receipt promoted to authority;
- direct native helper launch without inherited Product channel.

Expected: reservation/UI/Hello/capability/ticket/effect zero.

### T71-OPERATION

- new random request/challenge ID for the same semantic operation;
- wrong/cross action, producer ABI/version, plan, instance, profile, candidate,
  rollback target, config revision or consumer profile;
- stale/cross-build/cross-instance/cross-owner plan;
- action plan or display digest swap before/after visible review;
- same key with identical/different reservation body;
- reservation-only/decision-only/terminal-only replay.

Expected: at most one reservation and no authority from public/equal state;
collision/recovery preserves artifacts and has effect zero.

### T71-PROCESS

- wrong Product/broker image/build/signature manifest;
- wrong parent PID, token SID, session, logon LUID, integrity/elevation or
  inherited channel object;
- broker `HWND` owned by another process/thread, hidden/disabled/destroyed or
  replaced before/after verification;
- copied nonce/serialized handle value without the live kernel endpoint,
  different kernel object and spoofed PID/token fields;
- Product, broker or UI process restart/exit at every phase;
- process/backend implementation swap between prepare, verify and consume.

Expected: no live capability; challenge burned; effect zero.

### T71-UNSUPPORTED-CHANNEL-THEFT

- `OpenProcess(PROCESS_DUP_HANDLE)` followed by `DuplicateHandle` before/after
  verification or before consume;
- process VM/debug rights used to obtain broker/Product state;
- exact signed-image sibling holding a stolen duplex endpoint;
- theft of both Product/broker or broker/TASK-072 endpoints.

Expected classification: `NOT_SUPPORTED_V1`, not PASS/FAIL of the protected
boundary. Native evidence may demonstrate the limitation but cannot claim that
channel-object identity, nonce or transcript hash detects the actual writer.
Any future protection requires a separate isolation/peer-identity Task and a
versioned TASK-071 boundary revision.

### T71-UI-HELLO

- injected click/Enter/Space/default button/window activation;
- cancel/close/timeout, double click and concurrent prompts;
- caller/free-form or mismatched Windows verification message;
- availability states device absent/busy/not configured/policy disabled;
- result canceled/retries exhausted/unknown/HRESULT failure/callback mismatch;
- fake/custom/monkeypatched verifier in Production;
- Windows below build 22000, headless or unsupported remote session;
- user verified for one action followed by action/display/plan substitution.

Expected: only exact Product review plus direct broker `Verified` may create one
live capability; no plain-click/password/UAC fallback.

### T71-TIME

- backdated/future caller time and caller-selected expiry;
- issue then wall-clock rollback/large jump;
- suspend/resume across either deadline;
- timezone/DST change;
- boot/session/logon change and broker/Product restart;
- test clock or phase clock swap in Production;
- expiry-boundary double/concurrent consume.

Expected: expired/uncertain operation has capability/ticket/effect zero;
Product-authored event timestamp exact one only for accepted event.

### T71-IO-JSON

- lock symlink/reparse/hardlink/nonregular/wrong size and create race;
- authority ancestor/DACL/identity drift;
- reservation/event absent-to-appears identical/different;
- same bytes/different inode and stat-open/read-post swap;
- duplicate top/nested action/state/hash/identity keys equal/different;
- NaN/Infinity, BOM, trailing data, invalid UTF-8/control;
- deep/wide/huge/non-built-in/caller-preparsed value;
- temp/fsync/no-replace/directory durability/readback failure;
- foreign temp and attempted cleanup/delete/repair.

Expected: ambiguous input preserved; no false PASS/DUPLICATE; unrelated
overwrite/delete zero.

### T71-CONSUME

- wrong TASK-072 process/channel/action profile/consumer operation key;
- domain currentness missing, stale or changed after Human verification;
- double/concurrent consume and consume after deadline;
- exception before/after `IN_FLIGHT` durability and before/after owning effect;
- copied/serialized granted/consumed handle;
- same Human receipt used for promote/rollback or activate/deactivate;
- consumed activation reused for deactivation/emergency disable;
- same committed event versus different body/identity collision.

Expected: one Human grant produces at most one `IN_FLIGHT`; all entry paths burn;
owning store/config/history effect exact zero or one; replay effect zero.

### T71-PRIVACY

- absolute/UNC/home/repository path in display/status/error;
- username/SID/LUID/PID/HWND/handle/DACL/HRESULT/OS message leak;
- nonce, timestamp, token, candidate/profile/source body or credential leak;
- oversized/control/free-form display text and error echo;
- PIN/biometric/credential interception attempt.

Expected: public UI/receipt/log/stdout/stderr contains only closed body-free
projection; credential collection by BVP remains zero.

## 19. Acceptance criteria

Design acceptance requires:

1. One Task owner, responsibility, exact Allowed Files and prohibited paths are
   fixed.
2. Artifact/phase dependencies are acyclic; early ABI/fixtures are not effect
   completion.
3. Only the four closed actions exist and cross-action substitution is zero.
4. Public booleans, strings, dataclasses, mappings, hashes, module tokens,
   receipts, timestamps and Verified values create no authority.
5. A stable semantic reservation prevents new IDs/restarts from reissuing one
   unresolved Human operation.
6. Product/broker/UI process, image, token, SID/session/LUID, launch-bound
   channel possession and window are attested before/after every trust seam
   within the explicit section 6.3 endpoint-theft exclusion.
7. The fixed Windows interop is called only for the broker-owned active window;
   availability and every non-Verified result fail closed with no fallback.
8. Human review is explicit, Japanese, closed and action-bound; default,
   timeout, automation-only click and free-form text cannot approve.
9. Durable records are immutable audit evidence with
   `authority_created=false`; live broker state plus the launch-bound channel is
   the only capability under the supported threat model, and no per-frame
   sender-PID property is claimed.
10. Challenge IDs/nonces/time are server-generated; trusted deadline/session
    policy cannot be extended by caller clock, restart or suspend/resume.
11. First authenticated consume durably enters `IN_FLIGHT` and burns on success
    or exception; double/concurrent/replay effect is zero.
12. Owning domain currentness is revalidated immediately before Human consume
    and at the effect commit seam under its own transaction lease.
13. Same exact committed event alone may be audit `DUPLICATE`; different
    body/identity is collision STOP.
14. TASK-068 secure strict immutable I/O is used; generic atomic writer,
    replace, repair/delete/cleanup/latest scan and suppressed durability are
    zero.
15. Public UI/errors/receipts/logs are body/path/identity/credential free.
16. Fixture/static PASS is never promoted to native Windows user-presence,
    installed, E2E, activation or Production PASS.
17. Focused, negative, fault, packaging and protected-boundary native Windows
    matrices pass with unrelated overwrite/delete zero; endpoint-theft cases
    remain explicit `NOT_SUPPORTED_V1` evidence and are not counted as PASS.
18. Independent Critic reports `Critical=0 / High=0` and Judge returns `PASS`.

## 20. Verification plan

### Static/focused

- action ABI, action/display registry and state-transition exactness;
- strict schema/mirror equality and canonical fixture bytes;
- public constructor/copy/deserialize/forgery negatives;
- stable semantic reservation and replay/collision tests;
- fake-backend tests confined to non-Production composition;
- TASK-060/TASK-061/TASK-072 fixture consumer contract tests;
- body/path/identity/error leak scan and secret scan;
- compile/static checks, focused tests, diff/scope verification.

### Native Windows

- packaged Product/broker image and inherited-handle attestation;
- token SID/session/logon LUID/parent/integrity/elevation checks;
- exact broker-owned `HWND` before/after verification;
- Windows build and verifier availability matrix;
- real available Windows Hello/PIN/biometric `Verified` and Human cancel paths;
- device absent/not configured/policy disabled/busy/retries exhausted;
- injected UI input without successful system verification;
- broker/Product restart, channel close and expiry at every phase;
- concurrent prompts and double consume exact zero/one;
- wall-clock, boot/session and supported suspend/resume currentness;
- `OpenProcess(PROCESS_DUP_HANDLE)`/`DuplicateHandle`, VM/debug access and stolen
  endpoint demonstrations classified `NOT_SUPPORTED_V1`, with no false
  writer-PID detection claim;
- native error translation and public privacy readback.

Real Windows user-presence execution requires an explicit native Human Gate and
an eligible test account/device. When unavailable it is `NOT_EXECUTED`, never a
fixture-derived PASS. Tests do not capture PIN or biometric data.

### Packaging/integration

- broker helper exact manifest/hash included by a separately owned installer
  amendment;
- Product starts it only with the restricted inherited handle list;
- no public CLI action/nonce/config and no named/global endpoint;
- TASK-071/TASK-072 mutual process/channel/action-profile binding;
- Product shows Japanese unavailable guidance and no insecure fallback;
- distribution connector config remains byte-identical disabled;
- Release, real install, Product execution and Production Activation remain
  separate gates.

## 21. Independent completion receipt

The R2 independent Critic/Judge reviewed the current-main rebind and
owner-voice V2 amendment as technical-content SHA-256
`113C366945C9A1DD838BF36311D8863E085E7878523EF512E933CBE666C02F8E`
and returned `Critical=0 / High=0 / Medium=0 / Low=0` and
`PASS / TECHNICAL DESIGN FROZEN (R2)`. The external review receipt SHA-256 is
`8F35DE7F2F8AEC7A32EAA332940FA388ED73E2E5F3E6DAF38672A137AAE06DF4`.

```text
task: TASK-071
design_identity: TASK071-PTD-WINDOWS-HUMAN-AUTHORIZATION-V1
historical_design_base: origin/main@35cdf1ad475633dcf035e0616e979b5a8fde0c88
review_parent_main: origin/main@74b85d7d3f5965cd515ff44bd5f4b7179185e578
allowed_files: docs/ai-team/tasks/TASK-071/complete-design-packet.md
reviewed_content_sha256: 113C366945C9A1DD838BF36311D8863E085E7878523EF512E933CBE666C02F8E
review_receipt_sha256: 8F35DE7F2F8AEC7A32EAA332940FA388ED73E2E5F3E6DAF38672A137AAE06DF4
critic: C0/H0/M0/L0
judge: PASS_R2
source_effect: 0
schema_effect: 0
test_effect: 0
native_effect: 0
human_effect: 0
release_deploy_production_effect: 0
authority_created: false
next: fixture/source work in a fresh compliant worktree after dependency and overlap gates
```

This receipt freezes the technical design only. It creates no Human event,
implementation, install, ticket, Release, Deploy or Production authority.
